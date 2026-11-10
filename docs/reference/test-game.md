---
layout: default
title: "test_game"
permalink: /reference/test-game/
---

# test_game

*`test_game.py` — Verify the game flow against the original: the rating (f_70fb0), the game-over screen (f_71d95) and*

[Reference index]({{ site.baseurl }}/reference/) · [Download `test_game.py`]({{ site.baseurl }}/assets/reference/ref/test_game.py)

Verify the game flow against the original: the rating (f_70fb0), the game-over screen (f_71d95) and
the start of a game from the new-game dialog (f_725b6 without its dialog).

python test_game.py [name-substring ...]

## At a glance

- **152** lines
- **Classes / hooks:** `Flow`
- **5 top-level functions**, including `setter`, `port_game_over`, `port_start`, `check_rating`, `main`
- **Original routines referenced:** `f_01aec`, `f_03de7`, `f_16b83`, `f_70fb0`, `f_71d95`, `f_725b6`

## Source

{% raw %}
```python
"""Verify the game flow against the original: the rating (f_70fb0), the game-over screen (f_71d95) and
the start of a game from the new-game dialog (f_725b6 without its dialog).

python test_game.py [name-substring ...]
"""
import sys

from unicorn.x86_const import UC_X86_REG_DX

from verify import Verifier
from simant_ref import game
from simant_ref.state import G, T, DS
import test_sim
import test_newgame

BUF = 0x9000                     # DS scratch for f_70fb0's eight parts
GL, DSL = G * 16, DS * 16
# the rating window's own state (rect G:48B2, text), written by the window / text library (0x2xxxx)
SCREEN = test_sim.SCREEN + ((GL + 0x392c, GL + 0x392e), (GL + 0x48b0, GL + 0x48c0), (DSL + 0x5b30, DSL + 0x5c00),
                            (DSL + 0x6768, DSL + 0x6778))


def setter(g=(), t=(), g32=(), t8=()):
    def pre(set16, args):
        for seg, items in ((G, g), (T, t)):
            for off, val in items:
                set16(seg, off, val)
        for off, val in g32:
            set16(G, off, val & 0xffff)
            set16(G, off + 2, (val >> 16) & 0xffff)
        for off, val in t8:
            set16.byte(T, off, val)
    return pre


YARD = tuple((0xa4 + r * 16 + c, (r * 7 + c * 3) % 5) for r in range(12) for c in range(16))
RATINGS = [
    ('rating', setter()),
    ('rating, no time yet', setter(g32=((0xc26, 0),))),
    ('rating, long game', setter(g32=((0xc26, 50000),))),
    ('rating, negative ticks', setter(g32=((0xc26, 0xfffffff0),))),
    ('rating, eggs and losses', setter(g32=((0xfc2, 4000), (0x1000, 1300)), g=((0x9fa, 30), (0xa00, 12)))),
    ('rating, eggs, none lost', setter(g32=((0xfc2, 77), (0x1000, 0)))),
    ('rating, a short history', setter(t=((0x828, 5),), g=((0x4f4, 2),))),
    ('rating, no history', setter(t=((0x828, 0),))),
    ('rating, Full Game', setter(g=((0xeac, 2), (0xa90, 9), (0xac4, 4), (0xa9e, 2)), t8=YARD)),
    ('rating, Full Game, early', setter(g=((0xeac, 2), (0xa90, 0), (0xac4, 0), (0xa9e, 0)),
                                        g32=((0xc26, 700),), t8=YARD)),
    ('rating, Full Game, late', setter(g=((0xeac, 2), (0xa90, 30)), g32=((0xc26, 90000),), t8=YARD)),
    ('rating, experimental', setter(g=((0xeac, 3),), t8=YARD)),
    ('rating, dead yellow ant', setter(g=((0xf78, 0),))),
]

GAME_OVER = [
    ('game over, lost', setter(g=((0x376, 1), (0x366, 0)))),
    ('game over, won', setter(g=((0x376, 1), (0x366, 1)))),
    ('game over, won, sound off', setter(g=((0x376, 1), (0x366, 1)), t=((0x7aa, 0),))),
    ('game over, Full Game won', setter(g=((0x376, 1), (0x366, 1), (0xeac, 2)), g32=((0xc26, 30000),), t8=YARD)),
]


class Flow(test_sim.Player):
    def new_game_dialog(self, st):
        return 0


def port_game_over(st):
    st.player = Flow()
    game.game_over_screen(st)


def port_start(mode):
    def run(st, *args):
        st.player = Flow()
        game.start_game(st, mode)
        return mode
    return run


# starting a game also sets up the views and windows: view state (f_01aec: G:0D70, G:0F36 = 0x40 - G:0FB6,
# rect G:10D2), the colony panel (G:37FA), the yard map window (G:3854.., G:38C0..), library state
START_SCREEN = SCREEN + test_newgame.SCREEN + (
    (GL + 0xd70, GL + 0xd72), (GL + 0xf36, GL + 0xf38), (GL + 0x10d2, GL + 0x10da), (GL + 0x37fa, GL + 0x37fe),
    (GL + 0x3850, GL + 0x38d0), (GL + 0x392e, GL + 0x3930), (GL + 0x3ba8, GL + 0x3bb0), (GL + 0x4a44, GL + 0x4a46),
    (DSL + 0x2992, DSL + 0x2994), (DSL + 0x3d20, DSL + 0x3da8), (DSL + 0x5ec0, DSL + 0x5ef0),
    (DSL + 0x688a, DSL + 0x688c), (DSL + 0x8ce0, DSL + 0x8d60),
    # more view state (clip rects G:10DE..10EE, tile cache rows to G:1550), the dialog's text, library state,
    # and in the experimental mode the editing view's buffer G:25C4..37B0 (drawn by f_16b83 from f_03de7)
    (GL + 0x10de, GL + 0x10ee), (GL + 0x1110, GL + 0x1560), (GL + 0x3c40, GL + 0x3c70), (GL + 0x25c4, GL + 0x37b0), (GL + 0x37da, GL + 0x37de),
    (DSL + 0x298e, DSL + 0x2990), (DSL + 0x8bc2, DSL + 0x8bc6),           # (a screen pen position)
    (DSL + 0x4380, DSL + 0x4440))                                         # sprite masks (f_320xx)

# (label, dialog button, mode)
STARTS = [('start: Quick Game', 0x202, 1), ('start: Full Game', 0x203, 2), ('start: experimental', 0x204, 3),
          ('start: tutorial', 0x206, 0)]


def check_rating(v, label, pre):
    ok = True
    b = v.e.base * 16
    for tick, mem in v.snaps:
        v.load(mem)
        st = v.state_from_emu()

        def set16(seg, off, val):
            v.e.set16(seg, off, val)
            st.set16(seg, off, val)

        def set8(seg, off, val):
            v.e.write(seg, off, bytes([val & 0xff]))
            st.set8(seg, off, val)
        set16.byte = set8
        pre(set16, ())
        ax = v.e.call_lin(0x70fb0, (BUF, DS + v.e.base))        # a far pointer: relocated segment
        dx = v.e.uc.reg_read(UC_X86_REG_DX)
        orig = ((dx << 16) | (ax & 0xffff)) & 0xffffffff
        parts = [v.e.w16(DS, BUF + 2 * i) for i in range(8)]
        score, p = game.rating(st)
        p = [x & 0xffff for x in p]
        if orig != score & 0xffffffff or parts != p:
            ok = False
            print(f'  [{label} @tick {tick}] original {orig:#x} {parts} port {score & 0xffffffff:#x} {p}')
    print(f'{label}: {"OK" if ok else "MISMATCH"} ({len(v.snaps)} snapshots)')
    return ok


def main():
    filters = sys.argv[1:]
    v = Verifier()
    test_sim.prepare(v)
    v.extra_stubs = v.extra_stubs + ((0x2f848, 0),)                   # the new-game dialog: "Quick Game"
    v.clock_neutral(0x71d95, 0x71f51)
    ok = True
    for label, pre in RATINGS:
        if not filters or any(f in label for f in filters):
            ok &= check_rating(v, label, pre)
    for label, pre in GAME_OVER:
        if not filters or any(f in label for f in filters):
            ok &= v.check(0x71d95, port_game_over, label=label, pre=pre, ignore=SCREEN)
    base = v.extra_stubs
    for label, button, mode in STARTS:
        if not filters or any(f in label for f in filters):
            v.extra_stubs = base + ((0x2f9ec, button),)                # the dialog's answer
            ok &= v.check(0x725b6, port_start(mode), args_fn=lambda st, i: (1,), label=label,
                          pre=setter(), ignore=START_SCREEN)
    v.extra_stubs = base
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
```
{% endraw %}
