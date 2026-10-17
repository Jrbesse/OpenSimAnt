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


def lions(states, near_ants=True, cover=None, swarm=False):
    """pre hook: plant ant lions (state, frame, timer) next to surface ants (or on open ground)."""
    from simant_ref.state import SIM, T

    def pre(set16, a):
        set8 = set16.byte
        st = VER.state_from_emu()
        n = st.u16(G, 0xd6a)
        ants = [i for i in range(n) if st.u8(SIM, 0xad3b + i)]
        k = 0
        for j, (state, frame, timer) in enumerate(states):
            if near_ants and ants:
                ant = ants[(j * 37) % len(ants)]
                la, lb = st.u8(SIM, 0xa180 + ant) + 1, st.u8(SIM, 0xa569 + ant)
            else:
                la, lb = 10 + j * 9, 20 + j * 3
            la, lb = min(max(la, 1), 126), min(max(lb, 1), 62)
            set8(G, 0xa92 + k, la)
            set8(G, 0xaa8 + k, lb)
            set8(G, 0xaba + k, state)
            set8(G, 0xade + k, frame)
            set8(G, 0xacc + k, timer)
            if cover is not None:
                set8(SIM, 0x180 + la * 64 + lb, cover)
            if swarm:
                for d in range(8):
                    dx, dy = VER.e.read(T, d, 1)[0], VER.e.read(T, 8 + d, 1)[0]
                    dx, dy = dx - 256 if dx > 127 else dx, dy - 256 if dy > 127 else dy
                    set8(SIM, 0x6180 + (la + dx) * 64 + lb + dy, 0x10)
            k += 1
        set16(T, 0xc4a, k)
    return pre


def swarm_cat(n_occ):
    """pre hook: a caterpillar heading east at (40, 30), with n_occ of the 3x3 around its head occupied
    (always including the cell ahead)."""
    from simant_ref.state import SIM, T

    def pre(set16, a):
        set8 = set16.byte
        set16(T, 0xc4c, 1)
        set16(G, 0xc3c, 1)
        set16(T, 0xc4e, 40)
        set16(T, 0xc50, 30)
        set16(G, 0xc36, 3)
        cells = [(41, 30)] + [(x, y) for x in (39, 40, 41) for y in (29, 30, 31) if (x, y) != (41, 30)]
        for x, y in cells[:n_occ]:
            set8(SIM, 0x6180 + x * 64 + y, 0x10)
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
    ('new ant lion', 0x0b016, world.new_lion, 3, None),
    ('ant lions none', 0x0b163, world.ant_lions, 50, None),
    ('ant lions lurking', 0x0b163, world.ant_lions, 30, lions([(0, 0, 0)] * 6)),
    ('ant lions lurking open', 0x0b163, world.ant_lions, 30, lions([(0, 0, 0)] * 4, near_ants=False)),
    ('ant lions covered', 0x0b163, world.ant_lions, 1500, lions([(0, 0, 0)] * 5, near_ants=False, cover=0x49)),
    ('ant lions eating', 0x0b163, world.ant_lions, 60, lions([(1, 0, 5), (1, 4, 0), (1, 4, 9), (1, 2, 3)])),
    ('ant lions closing', 0x0b163, world.ant_lions, 20, lions([(2, 4, 0), (2, 0, 0), (2, 1, 0)])),
    ('ant lions swarmed', 0x0b163, world.ant_lions, 3, lions([(1, 2, 5), (0, 0, 0), (1, 1, 1)], swarm=True)),
    ('bugs', 0x0ae4c, world.bugs, 60, None),
    ('caterpillar', 0x0b6cc, world.caterpillar, 80, None),
    ('caterpillar long', 0x0b6cc, world.caterpillar, 700, None),
    ('caterpillar blocked', 0x0b6cc, world.caterpillar, 12, swarm_cat(4)),
    ('caterpillar swarmed', 0x0b6cc, world.caterpillar, 3, swarm_cat(9)),
    ('ant lions full', 0x0b163, world.ant_lions, 20, lions([(2, 0, 0)] * 9, near_ants=False)),
]


def main():
    global VER
    only = sys.argv[1:]
    v = VER = Verifier()
    ok = True
    for label, lin, fn, repeat, pre in CHECKS:
        if only and not any(o in label for o in only):
            continue
        ok &= v.check(lin, with_player(fn), label=label, repeat=repeat, pre=pre, ignore=SCREEN,
                      pre_once='lion' in label or 'caterpillar' in label)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
