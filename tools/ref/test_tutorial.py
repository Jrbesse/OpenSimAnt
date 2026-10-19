"""Verify the tutorial (f_0e425 with its steps f_0e4e4 / f_0e93e) against the original: every step shown and
checked from every snapshot, with the state each check looks at planted so both outcomes run.

python test_tutorial.py [name-substring ...]
"""
import sys

from verify import Verifier
from simant_ref import tutorial
from simant_ref.state import DS, G, T
import test_sim

# UI: thunk 0x2f6ea (f_71b1a, the message boxes)
STUBS = test_sim.STUBS + (0x2f6ea,)


def setter(step, shown, g=(), ds=()):
    def pre(set16, args):
        set16(G, 0xeac, 0)
        set16(T, 0x7a4, step)
        set16(T, 0x7a6, shown)
        set16(T, 0x7a2, 7)                       # the next call is an 8th one
        for off, val in g:
            set16(G, off, val)
        for off, val in ds:
            set16(DS, off, val)
    return pre


def run(st):
    st.player = test_sim.Player()
    tutorial.run(st)


# what makes each step's check pass (G offsets, DS offsets)
PASS = {
    3: dict(g=((0x224, 50), (0x204, 0), (0x206, 0), (0xaa0, 0))),
    4: dict(g=((0x224, 50), (0x204, 0), (0x206, 0), (0xaa0, 0))),
    5: dict(g=((0x48c, 1),)), 20: dict(g=((0x48c, 1),)), 18: dict(g=((0x48c, 2),)),
    7: dict(g=((0x1074, 0x7777), (0xb1e, 0), (0x204, 0), (0x206, 0))),
    26: dict(g=((0x1074, 0x7777), (0xb1e, 0), (0x204, 0), (0x206, 0))),
    9: dict(g=((0x1074, 0x7777),)),
    10: dict(ds=((0x5702, 0x100),)), 32: dict(ds=((0x5702, 0x100),)), 42: dict(ds=((0x5702, 0x100),)),
    12: dict(ds=((0x5702, 0),)), 49: dict(ds=((0x5702, 0),)),
    39: dict(ds=((0x5702, 0x1200),)), 47: dict(ds=((0x5702, 0x1300),)),
    13: dict(g=((0x48c, 1),)), 14: dict(g=((0xf78, 0x5b),)),
    16: dict(g=((0x4c2, 0x18),)), 19: dict(g=((0x4c2, 0x10),)), 21: dict(g=((0x4c2, 0x28),)),
    22: dict(g=((0x4c2, 0x10),)),
    24: dict(g=((0xb1c, 2),)), 52: dict(g=((0xb1c, 0x29),)),
    27: dict(g=((0x1074, 0x7777), (0x104e, 1), (0xb1e, 0))),
    30: dict(g=((0x104e, 1), (0x1074, 1))),
    33: dict(g=((0x32e, 0),)), 38: dict(g=((0x32e, 1),)), 36: dict(g=((0x35c, 1),)),
    41: dict(g=((0x1074, 0x7777),)),
    8: dict(g=((0x1074, 1),)), 43: dict(g=((0x1074, 1),)), 46: dict(g=((0x1074, 1),)), 50: dict(g=((0x1074, 1),)),
    54: dict(g=((0x48c, 3),)),
}
# the same steps failing; a late poll (G:10B8 > 15, the clock past G:0204) shows the message again
FAIL = dict(g=((0x10b8, 0x20), (0x204, 0), (0x206, 0), (0x224, 0), (0x1074, 0), (0xb1c, 0), (0x104e, 0),
               (0x4c2, 0x99), (0x48c, 4), (0xf78, 0x10)), ds=((0x5702, 0x700),))
WAIT = dict(g=((0x10b8, 3), (0x204, 0xffff), (0x206, 0x7fff), (0x4c2, 0x99), (0x48c, 4)), ds=((0x5702, 0x700),))

CASES = []
for step in range(0, 58):
    CASES.append((f'show {step}', setter(step, 0)))
    CASES.append((f'check {step} failing late', setter(step, 1, **FAIL)))
    CASES.append((f'check {step} failing early', setter(step, 1, **WAIT)))
    if step in PASS:
        CASES.append((f'check {step} passing', setter(step, 1, **PASS[step])))
CASES += [(f'check 54 view {v}', setter(54, 1, g=((0x48c, v),))) for v in (1, 2)]
CASES += [('show 55 after the red nest', setter(55, 0, g=((0x1074, 0),))),
          ('show 55 after the black nest', setter(55, 0, g=((0x1074, 1),))),
          ('counter wraps', lambda set16, a: (setter(5, 1)(set16, a), set16(T, 0x7a2, 0x400)))]


def main():
    filters = sys.argv[1:]
    v = Verifier()
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    ok = True
    for label, pre in CASES:
        if filters and not any(f in label for f in filters):
            continue
        # 9 calls: the first is an 8th one (show or check), the ninth the next
        ok &= v.check(0x0e425, run, args_fn=lambda st, i: (), label=label, pre=pre, repeat=9, pre_once=True,
                      ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
