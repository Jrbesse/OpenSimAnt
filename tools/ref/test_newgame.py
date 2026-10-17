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
          (DSL + 0x15c4, DSL + 0x15c4 + 0x1000))


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


def play(v, ticks):
    """Start a game on both sides (each its own way), then run SimStep side by side; compare every 100
    ticks and at the end."""
    v.extra_stubs = test_sim.STUBS
    v.clock_neutral(0x7c149, 0x7c3b0)
    ignore = SCREEN + test_sim.SCREEN
    stack_top = 0x55b3 * 16 + v.e.call_sp + 0x10
    ignore += ((stack_top - 0x800, stack_top),)
    b = v.e.base * 16
    ok = True
    for mode, seed in ((1, 0x2468ace), (2, 0x13579bd), (1, 0x0badf00d)):
        v.load(v.snaps[0][1])
        st = v.state_from_emu()
        st.player = test_sim.Player()
        for seg, off, val in ((G, 0xeac, mode), (DS, 0x7bbe, seed & 0xffff), (DS, 0x7bc0, seed >> 16)):
            v.e.set16(seg, off, val)
            st.set16(seg, off, val)
        v.e.call_lin(0x6b36b)
        newgame.new_game(st)
        label = f'mode {mode} rand {seed:#010x}, new game + SimStep x {ticks}'
        for t in range(ticks + 1):
            if t % 100 == 0 or t == ticks:
                orig = bytes(v.e.uc.mem_read(LO + b, HI - LO))
                diffs = [i for i in range(HI - LO) if orig[i] != st.mem[i]
                         and not any(lo <= LO + i < hi for lo, hi in ignore)]
                if diffs:
                    print(f'  [{label}] tick {t}: {len(diffs)} bytes differ, first {[hex(LO + i) for i in diffs[:6]]}')
                    ok = False
                    break
            if t == ticks or v.e.w16(G, 0x376):
                break
            v.e.call_lin(0x0894e)
            sim.sim_step(st)
        print(f'{label}: {"OK" if ok else "MISMATCH"} (ended at tick {t})')
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
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
