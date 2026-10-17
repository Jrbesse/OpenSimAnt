"""Simulation state, laid out exactly like the original's memory so ports can be verified byte for byte.

The buffer covers flat linear 0x3d570..0x62000 of the original program image, which holds
  T   (seg 0x3d57)  constant tables + some variables
  SIM (seg 0x3e1d)  grids, ant arrays, pheromone maps (the red trail map runs past 64 KB into 0x4da7:0)
  G   (seg 0x50f6)  far globals
  DS  (seg 0x55b3)  DGROUP (strings, the LFSR at DS:8ba2, the C runtime's rand state)
Initial contents come from the user's own SIMANT.EXE (tools/re/build/flat.bin) or from an emulator snapshot.
"""
import os
import struct

T, SIM, G, DS = 0x3d57, 0x3e1d, 0x50f6, 0x55b3
LO, HI = 0x3d570, 0x62000

_HERE = os.path.dirname(os.path.abspath(__file__))
FLAT = os.path.join(_HERE, '..', '..', 're', 'build', 'flat.bin')


class State:
    def __init__(self, mem=None):
        if mem is None:
            mem = open(FLAT, 'rb').read()[LO:HI]
            mem = mem + bytes(HI - LO - len(mem))
        self.mem = bytearray(mem)
        # the game's real-time clock (f_1bc34: 32-bit counter at 1b73:0012, ~18.2 ticks/s, kept by its
        # INT 8 handler); the engine sets it, the sim only reads it
        self.clock = 0

    def read_clock(self):
        """f_1bc34."""
        return self.clock & 0xffffffff

    def clock3(self):
        """f_0123e: the clock x3 (about 1/60 s units, like Mac ticks)."""
        return (self.read_clock() * 3) & 0xffffffff

    # ---- raw access by (segment, offset)
    def _a(self, seg, off):
        return seg * 16 + (off & 0xffff) - LO

    def u8(self, seg, off):
        return self.mem[self._a(seg, off)]

    def s8(self, seg, off):
        v = self.mem[self._a(seg, off)]
        return v - 256 if v > 127 else v

    def set8(self, seg, off, v):
        self.mem[self._a(seg, off)] = v & 0xff

    def u16(self, seg, off):
        a = self._a(seg, off)
        return self.mem[a] | (self.mem[a + 1] << 8)

    def s16(self, seg, off):
        v = self.u16(seg, off)
        return v - 0x10000 if v & 0x8000 else v

    def set16(self, seg, off, v):
        a = self._a(seg, off)
        self.mem[a] = v & 0xff
        self.mem[a + 1] = (v >> 8) & 0xff

    def u32(self, seg, off):
        return self.u16(seg, off) | (self.u16(seg, off + 2) << 16)

    def set32(self, seg, off, v):
        self.set16(seg, off, v & 0xffff)
        self.set16(seg, off + 2, (v >> 16) & 0xffff)

    def inc16(self, seg, off, d=1):
        self.set16(seg, off, self.u16(seg, off) + d)

    def inc32(self, seg, off, d=1):
        self.set32(seg, off, (self.u32(seg, off) + d) & 0xffffffff)

    # ---- the game RNG (LFSR at DS:8ba2), stored in memory like the original
    def lfsr_step(self):
        x = self.u16(DS, 0x8ba2) << 1
        if x & 0x10000:
            x ^= 0x1bf5
        x &= 0xffff
        self.set16(DS, 0x8ba2, x)
        return x

    def rand(self, n):
        """0093:013d Rand(n) = x % n."""
        return self.lfsr_step() % n

    def rand2(self): return self.lfsr_step() & 1
    def rand4(self): return self.lfsr_step() & 3
    def rand8(self): return self.lfsr_step() & 7
    def rand16(self): return self.lfsr_step() & 15
    def rand32(self): return self.lfsr_step() & 31
    def rand64(self): return self.lfsr_step() & 63
    def rand128(self): return self.lfsr_step() & 127
    def rand256(self): return self.lfsr_step() & 255

    def crt_rand(self):
        """MSC runtime rand() (state DS:7bbe, 32-bit): s = s*0x343fd + 0x269ec3; (s >> 16) & 0x7fff."""
        s = (self.u32(DS, 0x7bbe) * 0x343fd + 0x269ec3) & 0xffffffff
        self.set32(DS, 0x7bbe, s)
        return (s >> 16) & 0x7fff

    def crt_rand_mod(self, n):
        """0093:0118 abs(rand()) % n."""
        return self.crt_rand() % n

    def rand_low(self, n):
        """0093:002b min(Rand(n), Rand(n))."""
        a = self.rand(n)
        b = self.rand(n)
        return b if b < a else a

    # ---- common sim-segment grids (index a*64 + b)
    def grid(self, base, a, b):
        return self.u8(SIM, base + a * 64 + b)

    def set_grid(self, base, a, b, v):
        self.set8(SIM, base + a * 64 + b, v)

    def pher(self, base, ca, cb):
        """Pheromone map cell (half resolution, index ca*32 + cb)."""
        return self.u8(SIM, base + ca * 32 + cb)

    def set_pher(self, base, ca, cb, v):
        self.set8(SIM, base + ca * 32 + cb, v)
