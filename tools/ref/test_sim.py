"""Full-tick check: run SimStep (f_0894e) of the original and the port side by side from every snapshot
(python test_sim.py [ticks] [seed hex] [full])."""
import sys

from verify import Verifier, SNAP_TICKS
from simant_ref import sim
from simant_ref import player
from simant_ref import surface as sf
from simant_ref.state import DS, G

DSL, GL = DS * 16, G * 16
# screen-only state the port leaves to effect hooks: status-line message slots, the dirty-cell maps
SCREEN = ((DSL + 0x19c6, DSL + 0x19d0), (DSL + 0x299a, DSL + 0x29a4), (DSL + 0x15c4, DSL + 0x15c4 + 0x1000),
          (GL + 0x15c4, GL + 0x15c4 + 0x1000),
          # the player events' dialogs and animations (f_75d01), written by library code (0x17xxx..0x33xxx:
          # resource manager, input queue, far heap, drawing), never by the simulation's (traced):
          (GL + 0x3c00, GL + 0x3c40), (DSL + 0x2f30, DSL + 0x2f48), (DSL + 0x3dd0, DSL + 0x3df8),
          (DSL + 0x5ab0, DSL + 0x5b30), (DSL + 0x8c60, DSL + 0x8c80), (DSL + 0x8e00, DSL + 0x8e20),
          (GL + 0x37de, GL + 0x37e2), (GL + 0x3950, GL + 0x3958), (DSL + 0x3b84, DSL + 0x3c00),
          # window save-under buffers between the red trail map and G
          (0x4e270, GL),
          # the dialogs' windows (rect G:4962, window stack DS:5706..) and the view origin G:0508 redrawn
          # when they close
          (GL + 0x508, GL + 0x50c), (GL + 0x4960, GL + 0x4970), (DSL + 0x4340, DSL + 0x4360),
          (DSL + 0x5700, DSL + 0x5760), (DSL + 0x8dd0, DSL + 0x8de0), (DSL + 0x91a0, DSL + 0x91b0),
          # the patch view redrawn under a closing dialog when the game window is active (f_038a6: clip
          # rects G:10E6 / G:1104, tile cache G:1114.., G:37D2, G:3B60, ...)
          (GL + 0x10e6, GL + 0x10ea), (GL + 0x1104, GL + 0x110c), (GL + 0x1110, GL + 0x1460),
          (GL + 0x37d2, GL + 0x37da), (GL + 0x3b60, GL + 0x3b6c), (DSL + 0x6004, DSL + 0x6012),
          (DSL + 0x8bae, DSL + 0x8bb0), (DSL + 0x8cf4, DSL + 0x8cf6), (DSL + 0x94e4, DSL + 0x94e5))


# UI: scroll, redraw, menu marks, help box (thunk and f_7686d), win screen, game-over screen, the yard map
# (f_7650c), screen updates (f_03391 scrolls and redraws the view, f_0151c the whole screen), the
# animation timer (f_01277); a dialog's "clicked" (f_01572 returns 1)
STUBS = (0x01aa7, 0x03381, 0x22f65, 0x2f82a, 0x2f91a, 0x2f780, 0x7686d, 0x7650c, 0x03391, 0x01277, 0x0151c,
         (0x01572, 1))


def prepare(v):
    """Set up a Verifier for full ticks: the UI stubs, and a running clock for the animations and scenes
    that busy-wait on it (the fight f_7c149, AnimYellowInsane f_7c3b1, the queen scene f_758e0, f_75d01)."""
    v.extra_stubs = STUBS
    v.clock_neutral(0x7c149, 0x7c3b0)
    v.clock_neutral(0x7c3b1, 0x7c5aa)
    v.clock_neutral(0x758e0, 0x75d00)
    v.clock_neutral(0x75d01, 0x7650b)


class Player(player.Hooks):
    """The ported hooks; the UI ones do nothing, as the original's are stubbed in the emulator."""
    def game_over(self, st):
        pass

    def win_screen(self, st):
        pass

    def choose_patch(self, st):
        pass


def step(st):
    st.player = Player()
    sim.sim_step(st)


def give_action(mode, target):
    """pre hook: a pending player action (mode, cursor target view / a / b)."""
    def pre(set16, a):
        for off, val in ((0xaa0, 1), (0xa8e, mode), (0xaf8, target[0]), (0xad6, target[1]),
                         (0xae8, target[2]), (0xd6c, 0xfffe)):
            set16(G, off, val)
    return pre


def main():
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1234       # a Quick Game recorded with this seed
    mode = 2 if 'full' in sys.argv else 1                              # Quick Game, or a Full Game
    v = Verifier(ticks=(0, 300, 900, 1500, 2200) if mode == 2 else SNAP_TICKS, seed=seed, mode=mode)
    prepare(v)
    ok = v.check(0x0894e, step, label=f'SimStep x {ticks}', repeat=ticks, ignore=SCREEN)
    for label, mode, target in (('walks out to (70, 25)', 0, (1, 70, 25)), ('digs to (10, 40)', 2, (2, 10, 40))):
        ok &= v.check(0x0894e, step, label=f'SimStep x 400, the yellow ant {label}', repeat=400, ignore=SCREEN,
                      pre=give_action(mode, target), pre_once=True)
    def starving(set16, a):
        set16(G, 0xf78, 0)                                             # health 0: it dies within 100 ticks
        set16(0x3d57, 0xc16, 0)
    ok &= v.check(0x0894e, step, label='SimStep x 300, the yellow ant starves, the player takes over',
                  repeat=300, ignore=SCREEN, pre=starving, pre_once=True)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
