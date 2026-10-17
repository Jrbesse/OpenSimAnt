"""Find where the reference port and the original diverge, by comparing the sequence of RNG *calls*
(which function, which argument) made by each side.

python rng_diff.py [seed]   - runs the terrain generator comparison
Use `original_calls()` and `RecordingLfsr` from other tests.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 're'))

import emu                                   # noqa: E402
from emu import DGROUP, SIM, G               # noqa: E402
from unicorn import UC_HOOK_CODE             # noqa: E402
from unicorn.x86_const import UC_X86_REG_SP, UC_X86_REG_SS   # noqa: E402
from simant_ref.rng import Lfsr              # noqa: E402

# flat entry points of the RNG routines (segment 0093)
RNG_FUNCS = {0x00a6d: 'rand', 0x00a99: 'bits1', 0x00aba: 'bits3', 0x00adb: 'bits7', 0x00afc: 'bits15',
             0x00b1d: 'bits31', 0x00b3e: 'bits63', 0x00b5f: 'bits127', 0x00b80: 'bits255', 0x0095b: 'rand_low'}


class RecordingLfsr(Lfsr):
    def __init__(self, seed):
        super().__init__(seed)
        self.calls = []
        self._depth = 0

    def rand(self, n):
        if not self._depth:
            self.calls.append(('rand', n))
        return super().rand(n)

    def bits(self, mask):
        self.calls.append((f'bits{mask}', None))
        return super().bits(mask)

    def rand_low(self, n):
        self.calls.append(('rand_low', n))
        self._depth += 1
        try:
            return super().rand_low(n)
        finally:
            self._depth -= 1


def original_calls(e, lin, seed, prepare=None):
    calls = []
    depth = [0]

    def hook(uc, address, size, user):
        name = RNG_FUNCS[address - e.base * 16]
        sp, ss = uc.reg_read(UC_X86_REG_SP), uc.reg_read(UC_X86_REG_SS)
        arg = struct.unpack('<H', bytes(uc.mem_read(ss * 16 + sp + 4, 2)))[0]
        if name == 'rand_low':
            calls.append((name, arg))
        elif name == 'rand':
            # rand_low calls rand twice; skip those (rand_low's caller frame is directly below)
            ret_off, ret_seg = struct.unpack('<HH', bytes(uc.mem_read(ss * 16 + sp, 4)))
            if (ret_seg - e.base) * 16 + ret_off not in range(0x0095b, 0x00984):
                calls.append((name, arg))
        else:
            calls.append((name, None))
    hooks = [e.uc.hook_add(UC_HOOK_CODE, hook, None, e.base * 16 + a, e.base * 16 + a) for a in RNG_FUNCS]
    if prepare:
        prepare(e)
    e.set16(DGROUP, 0x8ba2, seed)
    e.call_lin(lin)
    for h in hooks:
        e.uc.hook_del(h)
    return calls


def first_divergence(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


if __name__ == '__main__':
    from simant_ref.terrain import Patch, generic_patch
    seed = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x1234
    e = emu.SimEmu()

    def prep(e):
        e.write(SIM, 0x0180, bytes(0x2000))
        e.write(SIM, 0x6180, bytes(0x2000))
        e.set16(G, 0xf24, 0)
    orig = original_calls(e, 0x73c33, seed, prep)
    rng = RecordingLfsr(seed)
    generic_patch(Patch(), rng)
    i = first_divergence(orig, rng.calls)
    print('original calls', len(orig), 'port calls', len(rng.calls), 'first divergence at', i)
    if i is not None:
        lo = max(0, i - 4)
        print(' original:', orig[lo:i + 6])
        print(' port    :', rng.calls[lo:i + 6])
