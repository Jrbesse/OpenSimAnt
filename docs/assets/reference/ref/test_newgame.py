"""Verify the new game (f_6b36b) and the patch setup (f_6ae20) against the original.

python test_newgame.py [name-substring ...]
python test_newgame.py play [ticks]     # new games started by each side, then SimStep side by side

New game: from every snapshot, both sides start a game in a chosen mode with a chosen C runtime rand()
state (DS:7BBE, which picks the yard's patch seeds), then compare all memory.
Patch setup: f_6ae20(seed, n_black, n_red, row, col) on the snapshot's world, with bigger colonies (their
nests are pre-dug) and other patches.
"""
import sys

from verify import Verifier
from simant_ref import newgame
from simant_ref import player
from simant_ref import sim
from simant_ref.state import G, DS, LO, HI
import test_sim

GL, DSL = G * 16, DS * 16
# screen-only state: the colony-behaviour panel's slider geometry and positions (InitColonySettings'
# f_20d09 / f_07a57 / f_07a19, left to the UI), the resource manager's counters those loads bump (DS:2F30,
# DS:3B88, written in f_18753 / f_19223 / f_1ac32), the dirty-cell map
SCREEN = ((GL + 0x358, GL + 0x35c), (GL + 0x22e, GL + 0x232), (GL + 0x37f2, GL + 0x37fa),
          (GL + 0x380e, GL + 0x3836), (DSL + 0x2f30, DSL + 0x2f32), (DSL + 0x3b88, DSL + 0x3b8a),
          (DSL + 0x15c4, DSL + 0x15c4 + 0x1000),
          # loading the house / yard tile graphics in f_02756 (all written inside it): the tiles pointer
          # G:37DE, resource manager and far heap state
          (GL + 0x37de, GL + 0x37e2), (GL + 0x3950, GL + 0x3958), (DSL + 0x2f40, DSL + 0x2f44),
          (DSL + 0x3b84, DSL + 0x3b90), (DSL + 0x8c60, DSL + 0x8c80), (DSL + 0x8e00, DSL + 0x8e10))


def port(st):
    st.player = player.Hooks()
    newgame.new_game(st)


def setup(mode, crt_seed, alarm=0):
    def pre(set16, args):
        set16(G, 0xeac, mode)
        set16(DS, 0x7bbe, crt_seed & 0xffff)
        set16(DS, 0x7bc0, crt_seed >> 16)
        set16(G, 0x104e, alarm)
    return pre


def port_patch(st, *args):
    st.player = player.Hooks()
    newgame.setup_patch(st, *args)


SEEDS = (0x00000001, 0x12345678, 0x0badf00d, 0x7fffffff, 0xdeadbeef)
CHECKS = [(f'mode {m} rand {s:#010x}', m, s, 0) for m in (1, 2, 3) for s in SEEDS]
CHECKS += [('mode 1 alarm trail on', 1, 0x2468ace, 1)]
# (seed, n_black, n_red, row, col)
PATCHES = [(0x1234, 4, 4, 11, 8), (0x0101, 10, 0, 5, 3), (0x7fff, 0, 10, 3, 9), (0x4321, 20, 30, 2, 6),
           (0x5555, 60, 60, 9, 15), (0x2aaa, 3, 1, 7, 0), (0x0f0f, 130, 2, 10, 4), (0x3333, 800, 900, 6, 6)]
PATCH_CHECKS = [(f'patch mode {m} {p[0]:#06x} b{p[1]} r{p[2]} ({p[3]}, {p[4]})', m, p) for m in (1, 2)
                for p in PATCHES]


def in_house(house):
    """pre hook: Full Game, standing in the yard (0) or in the house (1)."""
    def pre(set16, args):
        set16(G, 0xeac, 2)
        set16(G, 0xf24, house)
        set16(DS, 0x1a2e, house)
    return pre


# the 38 house patches, entered from the yard and from another house patch; then back out to the yard
HOUSE_CHECKS = [(f'house patch {i} from {"house" if h else "yard"}', h, (0x1111 * (i % 15 + 1), 3, i % 3, i // 16,
                                                                       i % 16))
                for h in (0, 1) for i in range(38)]
HOUSE_CHECKS += [('house: back to the yard', 1, (0x2468, 5, 5, 4, 9))]


def port_move(st):
    st.player = player.Hooks()
    newgame.move_to_patch(st)


def move(row, col, black=0, red=0, mode=2, g=()):
    """pre hook: the player picked patch (row, col) on the yard map, holding these colonies."""
    def pre(set16, args):
        set16(G, 0xeac, mode)
        set16(G, 0x7bc, row)
        set16(G, 0x7be, col)
        set16.byte(0x3d57, 0xa4 + row * 16 + col, black)
        set16.byte(0x3d57, 0x164 + row * 16 + col, red)
        for off, val in g:
            set16(G, off, val)
    return pre


MOVE_CHECKS = [
    ('move: same patch', move(11, 8, 5, 5)),
    ('move: not in a Quick Game', move(10, 8, 5, 5, mode=1)),
    ('move: colony too small', move(10, 8, 5, 5, g=((0x3e2, 1), (0x330, 1)))),
    ('move: no colony there', move(10, 8, 0, 5)),
    ('move: no colony, a new queen', move(10, 8, 0, 5, g=((0x4c2, 0x40), (0x3e2, 3)))),
    ('move: to the next patch', move(10, 8, 7, 3, g=((0x3e2, 3),))),
    ('move: to a patch without reds', move(7, 13, 40, 0, g=((0x3e2, 3),))),
    ('move: to a big colony', move(5, 2, 250, 120, g=((0x3e2, 3),))),
    ('move: into the house', move(1, 4, 9, 2, g=((0x3e2, 3),))),
    ('move: into the kitchen', move(0, 0, 9, 0, g=((0x3e2, 3),))),
]


def play(v, ticks):
    """Start a game on both sides (each its own way), then run SimStep side by side; compare every 100
    ticks and at the end."""
    test_sim.prepare(v)
    ignore = SCREEN + test_sim.SCREEN
    stack_top = 0x55b3 * 16 + v.e.call_sp + 0x10
    ignore += ((stack_top - 0x800, stack_top),)
    b = v.e.base * 16
    ok = True
    # (mode, rand state, then move to (row, col) with (black, red) there)
    for mode, seed, dest in ((1, 0x2468ace, None), (2, 0x13579bd, None), (1, 0x0badf00d, None),
                             (2, 0x0badf00d, (1, 6, 6, 3)), (2, 0x7777777, (0, 2, 4, 0)),
                             (2, 0x5151515, (6, 12, 30, 20))):
        v.load(v.snaps[0][1])
        st = v.state_from_emu()
        st.player = test_sim.Player()
        for seg, off, val in ((G, 0xeac, mode), (DS, 0x7bbe, seed & 0xffff), (DS, 0x7bc0, seed >> 16)):
            v.e.set16(seg, off, val)
            st.set16(seg, off, val)
        v.e.call_lin(0x6b36b)
        newgame.new_game(st)
        label = f'mode {mode} rand {seed:#010x}, new game + SimStep x {ticks}'
        if dest:
            row, col, black, red = dest
            for seg, off, val in ((G, 0x7bc, row), (G, 0x7be, col)):
                v.e.set16(seg, off, val)
                st.set16(seg, off, val)
            for off, val in ((0xa4 + row * 16 + col, black), (0x164 + row * 16 + col, red)):
                v.e.write(0x3d57, off, bytes([val]))
                st.set8(0x3d57, off, val)
            v.e.call_lin(0x01d48)
            newgame.move_to_patch(st)
            label = f'mode {mode} rand {seed:#010x}, moved to ({row}, {col}) + SimStep x {ticks}'
        good = True
        for t in range(ticks + 1):
            if t % 100 == 0 or t == ticks:
                orig = bytes(v.e.uc.mem_read(LO + b, HI - LO))
                diffs = [i for i in range(HI - LO) if orig[i] != st.mem[i]
                         and not any(lo <= LO + i < hi for lo, hi in ignore)]
                if diffs:
                    print(f'  [{label}] tick {t}: {len(diffs)} bytes differ, first {[hex(LO + i) for i in diffs[:6]]}')
                    good = False
                    break
            if t == ticks or v.e.w16(G, 0x376):
                break
            v.e.call_lin(0x0894e)
            sim.sim_step(st)
        ok &= good
        print(f'{label}: {"OK" if good else "MISMATCH"} (ended at tick {t})')
    return ok


def main():
    filters = sys.argv[1:]
    v = Verifier()
    if filters and filters[0] == 'play':
        ok = play(v, int(filters[1]) if len(filters) > 1 else 2000)
        print('ALL OK' if ok else 'FAILURES')
        return ok
    ok = True
    for label, mode, seed, alarm in CHECKS:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x6b36b, port, label=label, pre=setup(mode, seed, alarm), ignore=SCREEN)
    for label, mode, args in PATCH_CHECKS:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x6ae20, port_patch, args_fn=lambda st, i, a=args: a, label=label, pre=setup(mode, 1),
                      ignore=SCREEN)
    for label, house, args in HOUSE_CHECKS:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x6ae20, port_patch, args_fn=lambda st, i, a=args: a, label=label,
                      pre=in_house(house), ignore=SCREEN)
    for label, pre in MOVE_CHECKS:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x01d48, port_move, label=label, pre=pre, ignore=SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
