---
layout: default
title: "Game flow, rating and game over"
permalink: /reference/game/
---

# Game flow, rating and game over

*`game.py` — Starting a game, ending one, and the score.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `game.py`]({{ site.baseurl }}/assets/reference/simant_ref/game.py)

`f_70fb0` (the rating shown when a game ends), `f_71d95` (the game-over screen, via vector `f_2f780`) and `f_725b6` (starting from the new-game dialog, via `f_2f848`). The mode is `G:0EAC`.

- The rating is computed from integer parts (`_lmul`, `_ldiv`) because the original uses 32-bit scaled arithmetic, not floats.
- The game-over screen is a hook, not a state: what changes here is the mode and the counters.
- Tutorial, Quick Game, Full Game and experimental all enter through `start_game`.

## At a glance

- **143** lines
- **9 top-level functions**, including `_s32`, `_ldiv`, `_lmul`, `_window`, `rating_parts`, `rating`, `rank`, `game_over_screen` …
- **Original routines referenced:** `f_00f28`, `f_11aff`, `f_11b5f`, `f_2cd42`, `f_2cddc`, `f_2f780`, `f_2f816`, `f_2f848`, `f_2f942`, `f_6b36b`, `f_6e168`, `f_70fb0` …

## Source

{% raw %}
```python
"""Game flow around the simulation: the rating shown when a game ends (f_70fb0), the game-over screen
(f_71d95, via the vector f_2f780) and starting a game from the new-game dialog (f_725b6, via f_2f848).

Game modes G:0EAC: 0 tutorial, 1 Quick Game, 2 Full Game, 3 experimental. The screens themselves are UI
(st.player.effect); what they change in the game state is here.
"""
from .state import G, T, DS
from . import newgame
from . import player
from .movement import s16


def _s32(v):
    v &= 0xffffffff
    return v - 0x100000000 if v & 0x80000000 else v


def _ldiv(a, b):
    """C long division (f_2cd42): truncates toward zero."""
    a, b = _s32(a), _s32(b)
    q = abs(a) // abs(b)
    return _s32(q if (a >= 0) == (b >= 0) else -q)


def _lmul(a, b):
    """f_2cddc."""
    return _s32(a * b)


def _window(st):
    """The last T:0828 entries of the 64-entry history ring, ending at G:04F4."""
    n = s16(st.u16(T, 0x828))
    start = (st.u8(G, 0x4f4) - st.u8(T, 0x828)) & 0x3f
    return n, [(start + i) & 0x3f for i in range(max(n, 0))]


def rating_parts(st):
    """f_70fb0: the eight rating figures (signed words):
    0 average of history G:073C, 1 % of G:0626 in G:0626 + G:06AE (history), 2 % of eggs laid that were not
    lost (G:0FC2 / G:1000, 100 with none), 3 % G:09FA of G:09FA + G:0A00 (100 with none); Full Game and
    mode 3: 4 / 5 % of yard colonies G:0A90 against G:0AC4 / G:0A9E, 6 % of the 155 yard patches outside
    the house held by black colonies, 7 % of the 37 house patches."""
    p = [0] * 8
    n, idx = _window(st)
    if n > 0:
        total = 0
        for i in idx:
            total = (total + st.u16(G, 0x73c + 2 * i)) & 0xffff
        p[0] = s16(int(s16(total) / n))
    a = b = 0
    for i in idx:
        a = (a + st.u16(G, 0x626 + 2 * i)) & 0xffff
        b = (b + st.u16(G, 0x6ae + 2 * i)) & 0xffff
    tot = s16(a + b)
    p[1] = s16(_ldiv(100 * s16(a), tot)) if tot > 0 else 0
    eggs = _s32(st.u32(G, 0xfc2))
    if eggs > 0:
        p[2] = s16(_ldiv(_lmul(eggs - _s32(st.u32(G, 0x1000)), 100), eggs))
    else:
        p[2] = 100
    x = s16(st.u16(G, 0x9fa))
    tot = s16(x + st.u16(G, 0xa00))
    p[3] = s16(int(s16(100 * x) / tot)) if tot > 0 else 100
    mode = st.u16(G, 0xeac)
    if mode in (2, 3):
        black = s16(st.u16(G, 0xa90))
        for k, other in ((4, 0xac4), (5, 0xa9e)):
            tot = s16(black + st.u16(G, other))
            p[k] = s16(_ldiv(100 * black, tot)) if tot > 0 else 100
        yard = sum(1 for col in range(16) for row in range(3 if col < 5 else 2, 12)
                   if st.u8(T, 0xa4 + row * 16 + col))
        p[6] = s16(_ldiv(_lmul(yard, 100), 0x9b)) if yard > 0 else 0
        house = sum(1 for col in range(16) for row in range(3 if col < 5 else 2)
                    if st.u8(T, 0xa4 + row * 16 + col))
        p[7] = s16(_ldiv(_lmul(house, 100), 0x25)) if house > 0 else 0
    return p


def rating(st):
    """f_70fb0: the score (32-bit) and its parts: the yellow ant's health plus 51 x the weighted parts
    (weights DS:2AF8), scaled by the game's length G:0C26 (Quick Game: x 29 / 10, then x ticks/100 / 41
    if shorter than 4100 ticks; Full Game: x ticks/100 / 81 if shorter than 8100 ticks, then x 5), plus
    the ticks played."""
    p = rating_parts(st)
    score = s16(st.u16(G, 0xf78))
    for i in range(8):
        score = _s32(score + _lmul(_s32(p[i] * st.s8(DS, 0x2af8 + i)), 0x33))
    ticks = _s32(st.u32(G, 0xc26))
    if st.u16(G, 0xeac) != 2:
        score = _ldiv(_lmul(score, 0x1d), 10)
        if ticks < 0x1004:
            t = max(_ldiv(ticks, 100), 1)
            score = _ldiv(_lmul(t, score), 0x29)
    else:
        if ticks < 0x1fa4:
            t = max(_ldiv(ticks, 100), 1)
            score = _ldiv(_lmul(t, score), 0x51)
        score = _lmul(score, 5)
    return _s32(ticks + score), p


def rank(st, score):
    """f_71d95: the title shown, 0..4 by score (Full Game: score / 5), 5..9 when the game was lost."""
    if st.u16(G, 0xeac) == 2:
        score = _ldiv(score, 5)
    r = 4
    for i, limit in enumerate((0x344cc, 0x68998, 0x9ce64, 0xd1330)):
        if score < limit:
            r = i
            break
    return r if st.u16(G, 0x366) else r + 5


def game_over_screen(st):
    """f_71d95 (via f_2f780, when G:0376 is set): the rating window. Once the ending's sound has finished
    a fanfare plays (a Rand2 draw); the player closes the window, then picks the next game (f_725b6)."""
    if st.u16(T, 0x7aa):
        st.player.effect(st, 'sound', 0x2718 if st.u16(G, 0x366) else 0x271a)
    score, parts = rating(st)
    st.player.effect(st, 'game_over', rank(st, score), score, parts)
    if player.sound_done(st):                                         # f_00f28, polled with the window open
        st.player.effect(st, 'sound', st.rand2() + 0x2713)
    return st.player.new_game_dialog(st)


# the new-game dialog's buttons (f_725b6): game mode, or quit / load
BUTTONS = {0x202: 1, 0x203: 2, 0x204: 3, 0x206: 0, 0x205: 'quit', 0x207: 'load'}


def start_game(st, mode):
    """f_725b6 after the dialog: start a game in `mode` (0 tutorial, 1 Quick, 2 Full, 3 experimental)."""
    st.set16(G, 0xeac, mode)
    if st.u16(G, 0x105e) in (0xa, 0xb):                                # a pending yard map edit (f_11b5f / f_11aff)
        st.set16(G, 0x105e, 0xffff)
        st.player.effect(st, 'edit_tool', st.u16(G, 0x48e))           # f_2f816 → f_6e168
    st.player.effect(st, 'picture', 1)
    st.set16(G, 0x354, 1)
    st.set16(G, 0x7c8, 0)
    newgame.new_game(st)                                               # f_2f942 → f_6b36b
    if mode == 0:                                                      # the tutorial
        st.set16(T, 0x7a4, 1)
        st.set16(T, 0x7a6, 0)
    st.set16(T, 0x2c2, 0)
```
{% endraw %}
