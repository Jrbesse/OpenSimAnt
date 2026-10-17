"""Run original SIMANT.EXE routines inside Unicorn (16-bit real mode) on build/flat.bin.

    emu = SimEmu()
    emu.call(0x0093, 0x01ab)          # far-call seg:off, returns AX
    emu.sim_bytes()                   # snapshot of the 0x3e1d sim segment

A minimal DOS layer is provided (memory blocks, file reads from the game directory, console output),
BIOS video/mouse/EMS calls are ignored. Every interrupt is logged in `ints`.
"""
import os
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR, UcError
from unicorn.x86_const import (UC_X86_REG_EFLAGS, UC_X86_REG_AX, UC_X86_REG_BX, UC_X86_REG_CX,
                               UC_X86_REG_DX, UC_X86_REG_SI, UC_X86_REG_DI, UC_X86_REG_BP, UC_X86_REG_SP,
                               UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_IP)

HERE = os.path.dirname(os.path.abspath(__file__))
DGROUP = 0x55b3
SIM = 0x3e1d
G = 0x50f6
T = 0x3d57
STACK_SEG = 0x7f00                  # scratch stack above the flat image (image ends at 0x7dbb0)
RET_SEG, RET_OFF = 0x7e00, 0x0000   # far return trap: contains `hlt`


class SimEmu:
    def __init__(self, flat_path=os.path.join(HERE, 'build', 'flat.bin'), game_dir=os.path.join(HERE, '..', '..')):
        self.flat = open(flat_path, 'rb').read()
        self.uc = Uc(UC_ARCH_X86, UC_MODE_16)
        self.uc.mem_map(0, 0x100000)
        self.uc.mem_write(0, self.flat)
        self.uc.mem_write(RET_SEG * 16 + RET_OFF, b'\xf4')       # hlt
        self.ints = []
        self.console = []
        self.game_dir = game_dir
        self.files = {}
        self.next_handle = 5
        self.heap_next = 0x8000          # paragraphs handed out by INT 21h/48h
        self.heap_end = 0xF000
        self.uc.hook_add(UC_HOOK_INTR, self._on_int)

    # ---- minimal DOS / BIOS
    def _cf(self, uc, on):
        f = uc.reg_read(UC_X86_REG_EFLAGS)
        uc.reg_write(UC_X86_REG_EFLAGS, (f | 1) if on else (f & ~1))

    def _str(self, seg, off):
        b = bytearray()
        while True:
            c = self.uc.mem_read(seg * 16 + off + len(b), 1)[0]
            if c == 0:
                return b.decode('latin1')
            b.append(c)

    def _on_int(self, uc, intno, user):
        r, w = uc.reg_read, uc.reg_write
        ax, bx, cx, dx = r(UC_X86_REG_AX), r(UC_X86_REG_BX), r(UC_X86_REG_CX), r(UC_X86_REG_DX)
        ds = r(UC_X86_REG_DS)
        ah = ax >> 8
        self.ints.append((intno, ax, r(UC_X86_REG_CS), r(UC_X86_REG_IP)))
        if intno != 0x21:
            if intno == 0x67:                       # EMS: report "not installed"
                w(UC_X86_REG_AX, 0x8000)
            elif intno == 0x33:                     # mouse: none
                w(UC_X86_REG_AX, 0)
            return
        self._cf(uc, False)
        if ah == 0x02:
            self.console.append(chr(dx & 0xff))
        elif ah == 0x09:
            self.console.append(self._str(ds, dx).split('$')[0])
        elif ah == 0x30:
            w(UC_X86_REG_AX, 0x0005)
        elif ah in (0x25, 0x1a, 0x0e, 0x3b):
            pass
        elif ah == 0x35:
            w(UC_X86_REG_BX, 0)
            w(UC_X86_REG_ES, 0)
        elif ah == 0x19:
            w(UC_X86_REG_AX, (ax & 0xff00) | 2)     # drive C:
        elif ah == 0x47:
            uc.mem_write(ds * 16 + r(UC_X86_REG_SI), bytes(1))
        elif ah == 0x48:                            # allocate BX paragraphs
            if bx == 0xffff or self.heap_next + bx > self.heap_end:
                w(UC_X86_REG_BX, self.heap_end - self.heap_next)
                w(UC_X86_REG_AX, 8)
                self._cf(uc, True)
            else:
                seg = self.heap_next
                self.heap_next += bx
                w(UC_X86_REG_AX, seg)
        elif ah in (0x49, 0x4a):                    # free / resize: accept
            pass
        elif ah == 0x3d:                            # open (read-only)
            name = self._str(ds, dx).replace('/', chr(92)).split(chr(92))[-1].split(':')[-1]
            path = os.path.join(self.game_dir, name.upper())
            if os.path.exists(path):
                h = self.next_handle
                self.next_handle += 1
                self.files[h] = open(path, 'rb')
                w(UC_X86_REG_AX, h)
            else:
                self.console.append(f'[open fail {name}]')
                w(UC_X86_REG_AX, 2)
                self._cf(uc, True)
        elif ah == 0x3c:                            # create: refused (read-only harness)
            w(UC_X86_REG_AX, 5)
            self._cf(uc, True)
        elif ah == 0x3e:
            f = self.files.pop(bx, None)
            if f:
                f.close()
        elif ah == 0x3f:                            # read
            f = self.files.get(bx)
            if not f:
                w(UC_X86_REG_AX, 6)
                self._cf(uc, True)
            else:
                data = f.read(cx)
                uc.mem_write(ds * 16 + dx, data)
                w(UC_X86_REG_AX, len(data))
        elif ah == 0x40:                            # write: stdout/stderr go to console
            data = bytes(uc.mem_read(ds * 16 + dx, cx))
            if bx in (1, 2):
                self.console.append(data.decode('latin1'))
            w(UC_X86_REG_AX, cx)
        elif ah == 0x42:                            # seek
            f = self.files.get(bx)
            pos = f.seek((cx << 16) | dx, ax & 0xff)
            w(UC_X86_REG_AX, pos & 0xffff)
            w(UC_X86_REG_DX, pos >> 16)
        elif ah == 0x44:                            # ioctl: plain file
            w(UC_X86_REG_DX, 0)
        elif ah == 0x2c:
            w(UC_X86_REG_CX, 0x0c00)
            w(UC_X86_REG_DX, 0)
        elif ah == 0x2a:
            w(UC_X86_REG_CX, 1991)
            w(UC_X86_REG_DX, 0x0c06)
        elif ah == 0x4c:
            self.console.append(f'[exit {ax & 0xff}]')
            uc.emu_stop()
        else:
            self.console.append(f'[int21 ah={ah:02x}]')

    # ---- calls and memory
    def call(self, seg, off, args=(), max_insns=50_000_000):
        """Far-call seg:off with word args (cdecl, pushed right-to-left). Returns AX."""
        uc = self.uc
        sp = 0xfff0
        for a in reversed(args):
            sp -= 2
            uc.mem_write(STACK_SEG * 16 + sp, struct.pack('<H', a & 0xffff))
        sp -= 4
        uc.mem_write(STACK_SEG * 16 + sp, struct.pack('<HH', RET_OFF, RET_SEG))
        for reg, v in ((UC_X86_REG_SS, STACK_SEG), (UC_X86_REG_SP, sp), (UC_X86_REG_DS, DGROUP),
                       (UC_X86_REG_ES, DGROUP), (UC_X86_REG_BP, 0)):
            uc.reg_write(reg, v)
        uc.reg_write(UC_X86_REG_CS, seg)
        try:
            # Unicorn 16-bit: start/until are linear addresses (CS must also be set)
            uc.emu_start(seg * 16 + off, RET_SEG * 16 + RET_OFF + 1, count=max_insns)
        except UcError as e:
            cs, ip = uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)
            raise RuntimeError(f'emulation error {e} at {cs:04x}:{ip:04x}')
        return uc.reg_read(UC_X86_REG_AX)

    def read(self, seg, off, n):
        return bytes(self.uc.mem_read(seg * 16 + off, n))

    def write(self, seg, off, data):
        self.uc.mem_write(seg * 16 + off, bytes(data))

    def w16(self, seg, off):
        return struct.unpack('<H', self.read(seg, off, 2))[0]

    def set16(self, seg, off, v):
        self.write(seg, off, struct.pack('<H', v & 0xffff))

    def sim_bytes(self):
        return self.read(SIM, 0, 0x10000)


if __name__ == '__main__':
    e = SimEmu()
    e.set16(DGROUP, 0x8ba2, 1)
    seq = [e.call(0x0093, 0x01ab) for _ in range(16)]
    x, ref = 1, []
    for _ in range(16):
        c = x & 0x8000
        x = (x << 1) & 0xffff
        if c:
            x ^= 0x1bf5
        ref.append(x & 7)
    print('emulated Rand8:', seq)
    print('reference     :', ref, 'match' if seq == ref else 'MISMATCH')
