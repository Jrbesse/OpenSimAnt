---
layout: default
title: "The tutorial"
permalink: /reference/tutorial/
---

# The tutorial

*`tutorial.py` — 56 steps, each with a box and a check.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `tutorial.py`]({{ site.baseurl }}/assets/reference/simant_ref/tutorial.py)

Game mode 0: `f_0e425`, run by the advisor every tick before its status line. Every eighth call it either shows the current step (`f_0e4e4`: a message box with `STR# 11000 + 2*(step-1)`, some with a picture) or polls the step's completion check (`f_0e93e`) — done advances the step, and a step that polls 16 times without success gets a nudge.

- Step 46 needs the population graphs held, which sets `G:1074`; without it the step can never advance — a bug the emulator walk caught.
- A message box blocks the tick in the original (`f_71b1a`), so `GameSession.Advance` ends its loop there.
- All 56 step boxes were checked against an emulator run of the original routine.

## At a glance

- **184** lines
- **11 top-level functions**, including `_s16`, `_s32`, `_target`, `_set_target`, `_front`, `_yellow_sum`, `_box`, `run` …
- **Original routines referenced:** `f_0e2ea`, `f_0e425`, `f_0e4e4`, `f_0e93e`, `f_12d43`, `f_23612`, `f_2f6cc`, `f_2f6ea`, `f_2f80c`, `f_6be50`, `f_71b1a`

## Source

{% raw %}
```python
"""The tutorial (game mode G:0EAC = 0): f_0e425, run by the advisor f_0e2ea every tick before its status line.

Every 8th call (T:07A2 counts to 0x400) it either shows the current step T:07A4 (f_0e4e4: a message box with the
step's text, STR# 11000 + 2 (step - 1), some with a picture 17000.., and a little setup), or polls the step's
check (f_0e93e): done → the next step; not done after 16 polls (G:10B8) and past the clock target G:0204 → the
step's message again. T:07A6 says whether the step has been shown. Steps run 1..56; the last check passes and
step 57 does nothing. SIM_NOTES "The tutorial".

Screen-only effects: 'message_box' (f_2f6ea → f_71b1a(picture, STR# id, 1)), args (id, 1, picture).
"""
from .state import SIM, G, T, DS
from . import newgame
from . import player


def _s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def _s32(v):
    v &= 0xffffffff
    return v - 0x100000000 if v & 0x80000000 else v


def _target(st):
    return _s32(st.u32(G, 0x204))


def _set_target(st, v):
    st.set32(G, 0x204, v & 0xffffffff)


def _front(st, win):
    """f_23612(win): window `win` (layout << 8) is the active one, DS:5702."""
    return st.u16(DS, 0x5702) == win


def _yellow_sum(st):
    return (st.u16(G, 0x48a) + st.u16(G, 0x47c)) & 0xffff


def _box(st, text, picture=0):
    st.player.effect(st, 'message_box', text, 1, picture)


def run(st):
    """f_0e425."""
    st.set16(T, 0x7a2, st.u16(T, 0x7a2) + 1)
    if _s16(st.u16(T, 0x7a2)) > 0x400:
        st.set16(T, 0x7a2, 0)
    if st.u16(T, 0x7a2) & 7:
        return
    st.set16(G, 0x10b8, st.u16(G, 0x10b8) + 1)
    step = st.u16(T, 0x7a4)
    if st.u16(T, 0x7a6) == 0:
        show(st, step)
        st.set16(T, 0x7a6, 1)
        st.set16(G, 0x10b8, 0)
        return
    if done(st, step):
        st.set16(T, 0x7a4, step + 1)
    elif _s16(st.u16(G, 0x10b8)) <= 0xf or _target(st) >= _s32(st.clock3()):
        return
    st.set16(T, 0x7a6, 0)


# the steps' messages (STR# id, picture), steps 1..56; None where a step does more (see show)
_TEXT = {i + 1: (0x2af8 + 2 * i, 0) for i in range(0x38)}
_TEXT[0x38] = (0x2b68, 0)       # the closing box: f_0e4e4 case 56 pushes 0x2B68 (steps 55's two variants take 0x2B64 / 0x2B66)
_TEXT.update({2: (0x2afa, 0x4268), 5: (0x2b00, 0x4269), 11: (0x2b0c, 0x4276), 13: (0x2b10, 0x426a),
              14: (0x2b12, 0x426a), 17: (0x2b18, 0x4275), 18: (0x2b1a, 0x426b), 21: (0x2b20, 0x426c),
              33: (0x2b38, 0x426d), 36: (0x2b3e, 0x426e), 38: (0x2b42, 0x426f), 39: (0x2b44, 0x4270),
              40: (0x2b46, 0x4270), 41: (0x2b48, 0x4270), 43: (0x2b4c, 0x4271), 44: (0x2b4e, 0x4271),
              45: (0x2b50, 0x4272), 46: (0x2b52, 0x4272), 47: (0x2b54, 0x4273), 48: (0x2b56, 0x4273),
              50: (0x2b5a, 0x4274)})


def show(st, step):
    """f_0e4e4(step): the step's message box and setup."""
    if not 1 <= step <= 0x38:
        return
    if step == 23:
        newgame.add_surface_ants(st, 10, False)                         # f_2f6cc → f_6be50
    if step == 55:
        text = 0x2b64 if st.u16(G, 0x1074) == 0 else 0x2b66
        _box(st, text)
        return
    text, picture = _TEXT[step]
    _box(st, text, picture)
    if step in (3, 4):                                                 # dig: the nest must grow past this
        _set_target(st, _s16(st.u16(G, 0x224)) + (2 if step == 3 else 10))
    elif step in (7, 26):                                              # walk: from here, within ~10 s
        st.set16(G, 0x1074, _yellow_sum(st))
        _set_target(st, st.clock3() + 0x258)
    elif step in (8, 30, 43, 46, 50):
        st.set16(G, 0x1074, 0)
    elif step == 9:                                                    # scroll the view
        st.set16(G, 0x1074, st.u16(G, 0x50a) + st.u16(G, 0x508))
        _set_target(st, st.clock3() + 0x258)
    elif step == 14:
        player.set_health(st, 8)                                       # f_12d43: hungry, so it eats
    elif step == 27:
        st.set16(G, 0x1074, _yellow_sum(st))
    elif step == 41:                                                   # the behaviour triangle
        st.set16(G, 0x1074, st.u16(G, 0x4a0) + st.u16(G, 0x49e))
    elif step == 49:
        newgame.add_surface_ants(st, 0x50, False)                       # f_2f6cc(0x50)
        for i in range(0x40 * 0x20):                                    # clear the alarm scent map
            st.set8(SIM, 0xd09f + i, 0)


def _clock_passed(st):
    return _s32(st.clock3()) > _target(st)


def done(st, step):
    """f_0e93e(step): has the player done what the step asks?"""
    g = lambda off: st.u16(G, off)
    if step in (3, 4):
        return _s16(g(0x224)) > _target(st) and g(0xaa0) == 0
    if step in (5, 20):
        return g(0x48c) == 1
    if step in (7, 26):
        if _yellow_sum(st) == g(0x1074) or g(0xb1e) != 0:
            return False
        return _clock_passed(st)
    if step in (8, 43, 46, 50):
        return g(0x1074) != 0
    if step == 9:
        if (g(0x50a) + g(0x508)) & 0xffff != g(0x1074):
            return True
        return _clock_passed(st)
    if step in (10, 32, 42):
        return _front(st, 0x100)
    if step in (12, 49):
        return _front(st, 0)
    if step == 13:
        if g(0x48c) != 1:
            return False
        return st.u8(SIM, 0x180 + ((g(0x47c) << 6) + g(0x48a) & 0xffff)) > 0x47
    if step == 14:
        return _s16(g(0xf78)) > 0x5a
    if step == 16:
        return g(0x4c2) == 0x18
    if step == 18:
        return g(0x48c) == 2
    if step in (19, 22):
        return g(0x4c2) == 0x10
    if step == 21:
        return g(0x4c2) == 0x28
    if step == 24:
        return _s16(g(0xb1c)) > 1
    if step == 27:
        if _yellow_sum(st) == g(0x1074) or g(0x104e) == 0:
            return False
        return g(0xb1e) == 0
    if step == 30:
        if g(0x104e) != 0:
            player.alarm_mode(st, 0, 1)                                # f_2f80c(0, 1)
        return g(0x1074) != 0
    if step == 33:
        return g(0x32e) == 0
    if step == 36:
        return g(0x35c) == 1
    if step == 38:
        return g(0x32e) == 1
    if step == 39:
        return _front(st, 0x1200)
    if step == 41:
        return (g(0x4a0) + g(0x49e)) & 0xffff != g(0x1074)
    if step == 47:
        return _front(st, 0x1300)
    if step == 52:
        return _s16(g(0xb1c)) > 0x28
    if step == 54:
        if g(0x48c) == 3:
            st.set16(G, 0x1074, 0)
            return True
        if g(0x48c) == 2:
            st.set16(G, 0x1074, 1)
            return True
        return False
    return 1 <= step <= 0x38
```
{% endraw %}
