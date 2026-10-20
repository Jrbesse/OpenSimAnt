"""A planar VGA (mode 12h, 640 x 480 x 16) for the Unicorn emulator, so the original's own drawing can be captured.

Attach it to a SimEmu before booting (`VGA(emu)`): it takes over the port I/O hooks for the sequencer (3C4/3C5),
the graphics controller (3CE/3CF), the DAC (3C7/3C8/3C9) and the input status (3DA), and hooks reads and writes to
A0000..AFFFF. Writes go through the VGA write modes 0..3 (rotate, function AND / OR / XOR, set / reset, bit mask, map
mask); reads load the latches and return read mode 0 (plane select) or 1 (colour compare). `png(path)` writes the
screen with the current DAC (6-bit values scaled to 8 bits).

Only what a 16-colour planar driver needs; no text modes, no chain-4, no scrolling registers.
"""
import struct
import os
import sys

from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


class VGA:
    W, H = 640, 480

    def __init__(self, emu):
        self.emu = emu
        uc = emu.uc
        self.planes = [bytearray(0x10000) for _ in range(4)]
        self.latch = [0, 0, 0, 0]
        self.seq_index = 0
        self.seq = [0] * 8
        self.seq[2] = 0x0f
        self.gc_index = 0
        self.gc = [0] * 9
        self.gc[8] = 0xff
        self.dac = [(0, 0, 0)] * 256
        self.attr = list(range(16))               # the attribute controller's palette registers
        self.dac_write = 0
        self.dac_read = 0
        self.dac_buf = []
        self.writes = 0
        emu.vga = self                            # SimEmu's port hooks hand the I/O to us
        uc.hook_add(UC_HOOK_MEM_WRITE, self._mem_write, None, 0xA0000, 0xAFFFF)
        uc.hook_add(UC_HOOK_MEM_READ, self._mem_read, None, 0xA0000, 0xAFFFF)
        self.retrace = 0

    # ------------------------------------------------------------------ ports
    def _on_in(self, uc, port, size, user):
        if port == 0x3da:
            self.retrace += 1
            self.emu.ticks += 1
            return 0x09 if self.retrace & 1 else 0x00
        if port == 0x3c5:
            return self.seq[self.seq_index & 7]
        if port == 0x3cf:
            return self.gc[self.gc_index] if self.gc_index < 9 else 0
        if port == 0x3c9:
            r, g, b = self.dac[self.dac_read]
            v = (r, g, b)[len(self.dac_buf) % 3]
            self.dac_buf.append(v)
            if len(self.dac_buf) == 3:
                self.dac_buf = []
                self.dac_read = (self.dac_read + 1) & 0xff
            return v
        return 0xff if size == 1 else 0xffff

    def _out_byte(self, port, v):
        v &= 0xff
        if port == 0x3c4:
            self.seq_index = v
        elif port == 0x3c5:
            self.seq[self.seq_index & 7] = v
        elif port == 0x3ce:
            self.gc_index = v
        elif port == 0x3cf:
            if self.gc_index < 9:
                self.gc[self.gc_index] = v
        elif port == 0x3c8:
            self.dac_write = v
            self.dac_buf = []
        elif port == 0x3c7:
            self.dac_read = v
            self.dac_buf = []
        elif port == 0x3c9:
            self.dac_buf.append(v & 0x3f)
            if len(self.dac_buf) == 3:
                self.dac[self.dac_write] = tuple(self.dac_buf)
                self.dac_buf = []
                self.dac_write = (self.dac_write + 1) & 0xff

    def _on_out(self, uc, port, size, value, user):
        if size == 2:                             # out dx, ax: index then data
            self._out_byte(port, value & 0xff)
            self._out_byte(port + 1, value >> 8)
        else:
            self._out_byte(port, value)

    def int10(self, uc, ax, bx, cx, dx, es):
        """INT 10h AH=10h, the palette functions; True if handled."""
        if ax >> 8 != 0x10:
            return False
        al = ax & 0xff
        if al == 0x00:                            # one palette register: BL = register, BH = value
            if (bx & 0xff) < 16:
                self.attr[bx & 0xff] = bx >> 8
        elif al == 0x02:                          # all 16 registers + overscan from ES:DX
            data = uc.mem_read(es * 16 + dx, 17)
            self.attr = list(data[:16])
        elif al == 0x10:                          # one DAC register BX: DH red, CH green, CL blue
            self.dac[bx & 0xff] = ((dx >> 8) & 0x3f, (cx >> 8) & 0x3f, cx & 0x3f)
        elif al == 0x12:                          # a block of DAC registers: BX first, CX count, ES:DX table
            data = uc.mem_read(es * 16 + dx, 3 * cx)
            for i in range(cx):
                self.dac[(bx + i) & 0xff] = tuple(c & 0x3f for c in data[3 * i:3 * i + 3])
        return True

    # ------------------------------------------------------------------ memory
    def _mem_read(self, uc, access, address, size, value, user):
        for k in range(size):
            off = (address + k - 0xA0000) & 0xffff
            self.latch = [p[off] for p in self.planes]
            if self.gc[5] & 8:                    # read mode 1: colour compare
                cc, dc = self.gc[2] & 15, self.gc[7] & 15
                r = 0xff
                for p in range(4):
                    if dc >> p & 1:
                        bits = self.latch[p] if cc >> p & 1 else ~self.latch[p] & 0xff
                        r &= bits
                v = r
            else:
                v = self.latch[self.gc[4] & 3]
            uc.mem_write(address + k, bytes([v]))

    def _mem_write(self, uc, access, address, size, value, user):
        for k in range(size):
            self._write_byte((address + k - 0xA0000) & 0xffff, (value >> (8 * k)) & 0xff)

    def _write_byte(self, off, v):
        self.writes += 1
        gc = self.gc
        mode = gc[5] & 3
        rot = gc[3] & 7
        func = (gc[3] >> 3) & 3
        mask = gc[8]
        mapmask = self.seq[2] & 15
        if mode in (0, 3):
            v = ((v >> rot) | (v << (8 - rot))) & 0xff
        for p in range(4):
            if not (mapmask >> p & 1):
                continue
            if mode == 0:
                d = (0xff if gc[0] >> p & 1 else 0) if gc[1] >> p & 1 else v
            elif mode == 1:
                self.planes[p][off] = self.latch[p]
                continue
            elif mode == 2:
                d = 0xff if v >> p & 1 else 0
            else:                                 # mode 3: set / reset through (rotated value & bit mask)
                d = 0xff if gc[0] >> p & 1 else 0
            m = mask if mode != 3 else mask & v
            l = self.latch[p]
            if func == 1:
                d &= l
            elif func == 2:
                d |= l
            elif func == 3:
                d ^= l
            self.planes[p][off] = (d & m) | (l & ~m & 0xff)

    # ------------------------------------------------------------------ output
    def pixels(self):
        """640 x 480 palette indices."""
        out = bytearray(self.W * self.H)
        pl = self.planes
        for y in range(self.H):
            row = y * 80
            for xb in range(80):
                b0, b1, b2, b3 = pl[0][row + xb], pl[1][row + xb], pl[2][row + xb], pl[3][row + xb]
                base = y * self.W + xb * 8
                for bit in range(8):
                    s = 7 - bit
                    out[base + bit] = (b0 >> s & 1) | (b1 >> s & 1) << 1 | (b2 >> s & 1) << 2 | (b3 >> s & 1) << 3
        return out

    def rgb(self):
        px = self.pixels()
        pal = [tuple(c * 255 // 63 for c in self.dac[self.attr[i] & 0x3f]) for i in range(16)]
        return px, pal

    def png(self, path):
        from png import write_png
        px, pal = self.rgb()
        rgba = [pal[i] + (255,) for i in range(16)]
        rows = [[rgba[i] for i in px[y * self.W:(y + 1) * self.W]] for y in range(self.H)]
        write_png(path, self.W, self.H, rows)
