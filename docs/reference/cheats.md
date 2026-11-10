---
layout: default
title: "The cheat codes"
permalink: /reference/cheats/
---

# The cheat codes

*`cheats.py` — Typed keys, NOT-ed into a match buffer.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `cheats.py`]({{ site.baseurl }}/assets/reference/simant_ref/cheats.py)

`f_6a920` (overlay 10), called once per typed key through thunk `0x2f924`: typed keys are NOT-ed into `G:0B0A[T:06DE]`, and the table at `T:067E` holds 4-byte codes, also NOT-ed, terminated by a zero byte.

- A key that leaves no code with a matching prefix clears the buffer and is not retried as the start of a new code — the original's quirk, reproduced.
- A full match clears the buffer and runs the cheat.
- The codes themselves live in the original's tables, so this module carries machinery, not codes.

## At a glance

- **126** lines
- **5 top-level functions**, including `_toggle`, `_on_off_sound`, `_brood`, `cheat`, `run`
- **Original routines referenced:** `f_00ed8`, `f_277da`, `f_6a920`, `f_71b1a`, `f_74386`

## Source

{% raw %}
```python
"""The cheat codes (f_6a920, overlay 10): called once per typed key (via thunk 0x2f924 from f_74386).

Typed keys go NOT-ed into G:0B0A[T:06DE]; the table at T:067E holds 4-byte codes, also NOT-ed, ending at a 0
byte. A key that leaves no code with a matching prefix clears the buffer (and is not retried as the start
of a new code); a full match clears it and runs the cheat. See SIM_NOTES "Cheat codes".

Screen-only effects go to st.player.effect: 'sound' (f_00ed8(n, 0, 0x7E)), 'cheat' (f_277da("CHEAT %d")),
'message' (f_71b1a(0, id, 0)), 'joke' (the screen effects between its two messages), 'win_screen'.
"""
from .state import G, T
from . import nest
from . import newgame
from . import player
from .movement import s16

TABLE, LEN, BUF = 0x67e, 0x6de, 0xb0a
CODES = ('oops rand erad FUND joke hole HOLE qeen QEEN eggs EGGS heal HEAL zhea ZHEA just will mick jeff joel '
         'fred jenn susi').split()


def _toggle(st, seg, off):
    """X = (X == 0); sound 2 if now on, 1 if off. Returns the new value."""
    v = 1 if st.u16(seg, off) == 0 else 0
    st.set16(seg, off, v)
    return v


def _on_off_sound(st, on):
    st.player.effect(st, 'sound', 2 if on else 1)


def _brood(st, n, base):
    for _ in range(16):
        stage = st.crt_rand_mod(6) + base
        b = s16(st.u16(G, 0x48a)) + st.s8(T, 8 + st.rand8())
        a = s16(st.u16(G, 0x47c)) + st.s8(T, st.rand8())
        nest.spawn_brood(st, n, a, b, stage)


def cheat(st, key):
    """f_6a920(key)."""
    n = st.u16(T, LEN)
    st.set8(G, BUF + n, ~key & 0xff)
    n += 1
    st.set16(T, LEN, n)
    i = 0
    while st.u8(T, TABLE + 4 * i):
        if all(st.u8(T, TABLE + 4 * i + k) == st.u8(G, BUF + k) for k in range(n)):
            break
        i += 1
    if st.u8(T, TABLE + 4 * i) == 0 or n >= 4:
        st.set16(T, LEN, 0)
        for k in range(4):
            st.set8(G, BUF + k, 0)
    if st.u8(T, TABLE + 4 * i) == 0 or n < 4:
        return
    st.player.effect(st, 'cheat', i)
    run(st, i)


def run(st, i):
    """The switch on the matched code's index."""
    sound = lambda k: st.player.effect(st, 'sound', k)
    if i == 0:                                                   # oops
        sound(10)
        st.set16(G, 0x850, st.u16(G, 0x850) + 10)
    elif i in (1, 2):                                            # rand, erad
        sound(1)
        player.set_health(st, 100 if i == 1 else 1)
    elif i == 3:                                                 # FUND
        st.player.effect(st, 'message', 0x2724)
    elif i == 4:                                                 # joke
        st.player.effect(st, 'message', 0x2726)
        st.player.effect(st, 'joke', None)
        st.player.effect(st, 'message', 0x2728)
    elif i in (5, 6):                                            # hole, HOLE
        n = nest.BLACK if i == 5 else nest.RED
        for col in range(0x40):
            nest.make_surface_hole(st, n, col)
    elif i in (7, 8):                                            # qeen, QEEN
        n = nest.BLACK if i == 7 else nest.RED
        newgame._queen_chamber(st, n, s16(st.u16(G, 0x47c)) + 2, s16(st.u16(G, 0x48a)), 2)
    elif i == 9:                                                 # eggs
        _brood(st, nest.BLACK, 1)
    elif i == 10:                                                # EGGS
        _brood(st, nest.RED, 0x81)
    elif i == 11:                                                # heal
        st.set16(G, 0x10be, 100)
    elif i == 12:                                                # HEAL
        st.set16(G, 0x1fe, 100)
    elif i == 13:                                                # zhea
        st.set16(G, 0x1fe, 0)
    elif i == 14:                                                # ZHEA
        st.set16(T, 0xc18, 0)
        st.set16(G, 0x10be, 0)
    elif i == 15:                                                # just (NewColonyNoop does nothing)
        st.set16(G, 0x7c8, st.u16(G, 0x7c8) + 10)
        sound(0x29)
    elif i in (16, 17):                                          # will, mick
        _on_off_sound(st, _toggle(st, T, 0xc14 if i == 16 else 0xc12))
    elif i == 18:                                                # jeff
        sound(2)
        for cell in range(12 * 16):
            st.set8(T, 0xa4 + cell, st.u8(T, 0xa4 + cell) + 4)
            st.set16(G, 0xa90, st.u16(G, 0xa90) + 1)
    elif i == 19:                                                # joel
        sound(1)
        for cell in range(12 * 16):
            if st.rand2() == 0:
                st.set8(T, 0xa4 + cell, st.u8(T, 0xa4 + cell) + 1)
                st.set16(G, 0xa90, st.u16(G, 0xa90) + 1)
            else:
                st.set8(T, 0x164 + cell, st.u8(T, 0x164 + cell) + 1)
                st.set16(G, 0xac4, st.u16(G, 0xac4) + 1)
    elif i == 20:                                                # fred
        st.player.effect(st, 'win_screen', None)
    elif i == 21:                                                # jenn
        on = _toggle(st, T, 0xc16)
        if on:
            st.set16(G, 0xf78, 100)
        _on_off_sound(st, on)
    elif i == 22:                                                # susi
        on = _toggle(st, T, 0xc18)
        if on:
            st.set16(G, 0x10be, 100)
        _on_off_sound(st, on)
```
{% endraw %}
