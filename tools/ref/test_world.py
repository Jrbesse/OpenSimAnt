"""Verify the SimStep world updates against the original (python test_world.py [name-substring ...])."""
import sys

from verify import Verifier
from simant_ref import world
from simant_ref import surface as sf
from simant_ref.state import G, DS

DSL = DS * 16
# screen-only state the port leaves to effect hooks: status-line message slots, the dirty-cell map
SCREEN = ((DSL + 0x19c6, DSL + 0x19d0), (DSL + 0x299a, DSL + 0x29a4), (DSL + 0x15c4, DSL + 0x15c4 + 0x1000))


def with_player(fn):
    def run(st, *args):
        st.player = sf.NoPlayer()
        return fn(st, *args)
    return run


def setter(g=(), t=()):
    from simant_ref.state import T

    def pre(set16, a):
        for off, val in g:
            set16(G, off, val)
        for off, val in t:
            set16(T, off, val)
    return pre


CHECKS = [
    ('history', 0x798c8, world.history, 3, None),
    ('advisor', 0x0e2ea, world.advisor, 2, None),
    ('advisor shown', 0x0e2ea, world.advisor, 1, setter(t=[(0x7b0, 1)])),
    ('advisor hungry', 0x0e2ea, world.advisor, 1, setter(g=[(0xffe, 101)], t=[(0x7b0, 1)])),
    ('advisor crowded', 0x0e2ea, world.advisor, 1, setter(g=[(0x224, 1)], t=[(0x7b0, 1)])),
    ('advisor no nest', 0x0e2ea, world.advisor, 1, setter(g=[(0x224, 0)], t=[(0x7b0, 1)])),
    ('advisor yellow dying', 0x0e2ea, world.advisor, 1, setter(g=[(0xf78, 5)], t=[(0x7b0, 1)])),
    ('census+advisor', 0x0c20f, world.census_and_advise, 2, None),
] + [(f'slow phase {p}', 0x08a78, world.slow_phase, 1, setter(g=[(0xf08, p * 0x20)])) for p in range(4)] + [
    ('weather dry', 0x0c22c, world.weather, 20, None),
    ('weather rain', 0x0c22c, world.weather, 30, setter(g=[(0x352, 1)])),
    ('weather rain flooded', 0x0c22c, world.weather, 30, setter(g=[(0x352, 1), (0x242, 40)])),
    ('weather after rain', 0x0c22c, world.weather, 30, setter(g=[(0x242, 30)], t=[(0xc1e, 1)])),
    ('weather in house', 0x0c22c, world.weather, 5, setter(g=[(0x352, 1), (0xf24, 1)])),
]


def main():
    only = sys.argv[1:]
    v = Verifier()
    ok = True
    for label, lin, fn, repeat, pre in CHECKS:
        if only and not any(o in label for o in only):
            continue
        ok &= v.check(lin, with_player(fn), label=label, repeat=repeat, pre=pre, ignore=SCREEN)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
