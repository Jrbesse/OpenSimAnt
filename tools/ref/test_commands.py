"""Verify the yellow ant's menu commands (f_76cb9) against the original.

python test_commands.py [name-substring ...]
"""
import sys

from verify import Verifier
from simant_ref import commands
from simant_ref.state import G
import test_sim

# UI: voice (f_00ea1), help (f_76eb5), pause (thunk 0x2f816), the animation timer (f_0125f)
STUBS = test_sim.STUBS + (0x00ea1, 0x76eb5, 0x2f816, 0x0125f)


def setter(g=()):
    def pre(set16, args):
        for off, val in g:
            set16(G, off, val)
    return pre


def port(st, cmd):
    st.player = test_sim.Player()
    commands.command(st, cmd)


CASES = [(f'command {c:#x}', [c], setter()) for c in (1, 2, 3, 4, 5, 7, 8, 9, 0xb, 0xc)] + [
    ('recruit all, then release half', [3, 4], setter()),
    ('recruit 5 twice, release all', [1, 1, 5], setter()),
    ('exchange mode on and off', [6, 6], setter()),
    ('chase mode on and off', [0xa, 0xa], setter()),
    ('exchange then chase mode', [6, 0xa], setter()),
    ('hunt as the spider', [0xb, 0xb, 0xc, 0xc], setter(g=((0xa06, 1),))),
    ('the spider hunting', [0xb, 0xc], setter(g=((0xa06, 1), (0x6ac, 7)))),
    ('no player (G:0A06 = 2)', [1, 0xb], setter(g=((0xa06, 2),))),
    ('dig hole on the surface', [8, 8], setter(g=((0x48c, 1),))),
    ('dig hole in the nest', [8], setter(g=((0x48c, 2),))),
    ('start brood on the surface', [9], setter(g=((0x48c, 1),))),
    ('start brood in the nest, shallow', [9], setter(g=((0x48c, 2), (0x48a, 2)))),
    ('alarm toggled', [7, 7], setter()),
]


def port_click(st, a, b, k):
    st.player = test_sim.Player()
    commands.spider_click(st, a, b, k)


def _surface_ant(k):
    def at(st, i):
        n = st.u16(G, 0xd6a)
        if not n:
            return None
        j = (i * 11) % n
        return st.u8(0x3e1d, 0xa180 + j), st.u8(0x3e1d, 0xa569 + j), k
    return at


CLICKS = [
    ('spider walks', lambda st, i: ((i * 17) % 128, (i * 7) % 64, 0), setter(g=((0xa06, 1),))),
    ('spider clicks with k = 1', lambda st, i: ((i * 17) % 128, (i * 7) % 64, 1), setter(g=((0xa06, 1),))),
    ('spider picks surface ants', _surface_ant(1), setter(g=((0xa06, 1),))),
    ('chase mode on ants', _surface_ant(0), setter(g=((0xa06, 1), (0x105e, 0xb)))),
    ('chase mode on empty cells', lambda st, i: (0, (i * 5) % 64, 0), setter(g=((0xa06, 1), (0x105e, 0xb)))),
]


def main():
    filters = sys.argv[1:]
    v = Verifier()
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    ok = True
    for label, where, pre in CLICKS:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x756a6, port_click, args_fn=where, repeat=10, label=label, pre=pre, ignore=test_sim.SCREEN)
    for label, cmds, pre in CASES:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x76cb9, port, args_fn=lambda st, i, cmds=cmds: (cmds[i],), repeat=len(cmds), label=label,
                      pre=pre, pre_once=True, ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
