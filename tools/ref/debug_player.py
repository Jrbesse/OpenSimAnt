"""Debug helper: python debug_player.py <check label> [snapshot index].

Finds the first call where a test_player check diverges and shows its args and the RNG state."""
import sys

import test_player as tp
from verify import Verifier
from simant_ref.state import DS

label = sys.argv[1]
check = next(c for c in tp.CHECKS if c[0] == label)
_, lin, fn, repeat, pre, args_fn = check
v = tp.VER = Verifier()
tick, mem = v.snaps[int(sys.argv[2]) if len(sys.argv) > 2 else 0]
for n in range(1, repeat + 1):
    v.load(mem)
    st = v.state_from_emu()
    last = None
    for i in range(n):
        args = args_fn(st, i) if args_fn else ()
        if pre:
            def set16(seg, off, val):
                v.e.set16(seg, off, val)
                st.set16(seg, off, val)
            set16.byte = lambda seg, off, val: (v.e.write(seg, off, bytes([val & 0xff])), st.set8(seg, off, val))
            pre(set16, args)
        r0 = st.u16(DS, 0x8ba2)
        ro = v.e.call_lin(lin, args)
        rp = fn(st, *args)
        last = (args, r0)
    from simant_ref.state import LO, HI
    b = v.e.base * 16
    orig = bytes(v.e.uc.mem_read(LO + b, HI - LO))
    diffs = [i for i in range(HI - LO) if orig[i] != st.mem[i] and not any(lo <= LO + i < hi for lo, hi in tp.SCREEN)
             and not (0x55b3 * 16 + v.e.call_sp - 0x7f0 <= LO + i < 0x55b3 * 16 + v.e.call_sp + 0x10)]
    if diffs:
        print(f'first divergence at call {n - 1}: args {last[0]} lfsr before {last[1]:#06x}')
        print(f'  lfsr after: original {v.e.w16(0x55b3, 0x8ba2):#06x} port {st.u16(DS, 0x8ba2):#06x}')
        for i in diffs[:12]:
            from verify import describe
            print(f'  {describe(LO + i)}: original {orig[i]:#04x} port {st.mem[i]:#04x}')
        break
