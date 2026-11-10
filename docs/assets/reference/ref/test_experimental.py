"""Verify the State changes of the Experimental menu handlers f_67010 / f_67a24 (ROADMAP B5).

python test_experimental.py [name-substring ...]

The handlers themselves are UI (pop-ups); what they do to the State is a sequence of verified routines, run here on
both sides from every snapshot, in the contexts the game can be in:
  enter: a Quick Game's "EXPERIMENTAL MODE": G:0EAC = 3, f_11918(yellow ant off the map), G:0A06 = 2, f_0cdb0;
  start: the tool palette's "Start Game": G:0EAC = 1, f_2f8ac (= f_6b7d0, the yellow ant placed again), and with the
         surface on screen (G:032E == 1) f_119b4(..., 0xFF); the tool G:104C = 7.
Both run in a row (enter, then start) as a player would, and the memory is compared after each step.
"""
import sys

from verify import Verifier
from simant_ref import newgame
from simant_ref import player
from simant_ref.state import G, DS, T, LO, HI
import test_newgame
import test_sim

IGNORE = test_newgame.SCREEN + test_sim.SCREEN


def contexts():
    """(label, G/T values set before the enter step): views on screen, the alarm trail, the yellow ant's place."""
    out = []
    for view in (0, 1, 2, 3):
        out.append((f'screen view {view}', {(G, 0x32e): view}))
    out.append(('alarm trail on', {(G, 0x104e): 1, (G, 0x32e): 1}))
    out.append(('yellow ant in the red nest', {(G, 0x48c): 3, (G, 0x32e): 3, (G, 0x4e2): 0x80}))
    out.append(('yellow ant on the surface', {(G, 0x48c): 1, (G, 0x47c): 70, (G, 0x48a): 20, (G, 0x32e): 1}))
    out.append(('tool 5 chosen before', {(G, 0x104c): 5, (G, 0x32e): 1}))
    return out


def check_sequence(v, label, preset):
    ok = True
    b = v.e.base * 16
    stack_top = 0x55b3 * 16 + v.e.call_sp + 0x10
    ignore = IGNORE + ((stack_top - 0x800, stack_top),)
    for tick, mem in v.snaps:
        v.load(mem)
        st = v.state_from_emu()
        st.player = player.Hooks()

        def set16(seg, off, val):
            v.e.set16(seg, off, val)
            st.set16(seg, off, val)

        set16(G, 0xeac, 1)                                        # a Quick Game
        for (seg, off), val in preset.items():
            set16(seg, off, val)

        def same(step):
            nonlocal ok
            orig = bytes(v.e.uc.mem_read(LO + b, HI - LO))
            diffs = [i for i in range(HI - LO) if orig[i] != st.mem[i]
                     and not any(lo <= LO + i < hi for lo, hi in ignore)]
            if diffs:
                ok = False
                print(f'  [{label} @tick {tick}] {step}: {len(diffs)} bytes differ, first {[hex(LO + i) for i in diffs[:6]]}')
            return not diffs

        def g(off):
            return v.e.w16(G, off)

        # enter (f_67010 / f_67a24, mode 1): f_67fe9(G:104C), G:0EAC = 3, f_11918, G:0A06 = 2, f_0cdb0
        set16(G, 0xeac, 3)
        args = (g(0x48c), g(0x47c), g(0x48a), g(0x4c2), g(0x496))
        v.e.call_lin(0x11918, args)
        player.take_yellow(st, *args)
        set16(G, 0xa06, 2)
        v.e.call_lin(0xcdb0)
        newgame.reset_patch_globals(st)
        if not same('enter'):
            continue
        # start (mode 3): G:0EAC = 1, f_2f8ac = f_6b7d0, then f_119b4 on the surface view, G:104C = 7
        set16(G, 0xeac, 1)
        v.e.call_lin(0x6b7d0)
        newgame.place_yellow(st)
        if not same('start: f_6b7d0'):
            continue
        if g(0x32e) == 1:
            args = (g(0x48c), g(0x47c), g(0x48a), g(0x4c2), g(0x496), 0xff)
            v.e.call_lin(0x119b4, args)
            player.put_yellow(st, *args)
        set16(G, 0x104c, 7)
        same('start: f_119b4')
    print(f'{label}: {"OK" if ok else "MISMATCH"} ({len(v.snaps)} snapshots)')
    return ok


def main():
    filters = sys.argv[1:]
    v = Verifier()
    ok = True
    for label, preset in contexts():
        if filters and not any(f in label for f in filters):
            continue
        ok &= check_sequence(v, label, preset)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
