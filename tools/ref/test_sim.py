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
          (GL + 0x15c4, GL + 0x15c4 + 0x1000))


# UI: scroll, redraw, menu marks, help box, player-event dialogs, win screen, game-over screen
STUBS = (0x01aa7, 0x03381, 0x22f65, 0x2f82a, 0x2f7d0, 0x2f91a, 0x2f780)


class Player(player.Hooks):
    """The ported hooks; the UI ones do nothing, as the original's are stubbed in the emulator."""
    def game_over(self, st):
        pass

    def game_event(self, st, n):
        pass

    def win_screen(self, st):
        pass


def step(st):
    st.player = Player()
    sim.sim_step(st)


def main():
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1234       # a Quick Game recorded with this seed
    mode = 2 if 'full' in sys.argv else 1                              # Quick Game, or a Full Game
    v = Verifier(ticks=(0, 300, 900, 1500, 2200) if mode == 2 else SNAP_TICKS, seed=seed, mode=mode)
    v.extra_stubs = STUBS
    v.clock_neutral(0x7c149, 0x7c3b0)          # the fight animation busy-waits on the clock
    ok = v.check(0x0894e, step, label=f'SimStep x {ticks}', repeat=ticks, ignore=SCREEN)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
