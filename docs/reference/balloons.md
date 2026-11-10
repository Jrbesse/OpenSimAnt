---
layout: default
title: "Speech balloons"
permalink: /reference/balloons/
---

# Speech balloons

*`balloons.py` — The ants' remarks, timed off the real-time clock.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `balloons.py`]({{ site.baseurl }}/assets/reference/simant_ref/balloons.py)

`f_06a4d`, reached from the window draw (`f_038a6` via `f_07128`): a balloon appears at the spot a marker recorded, and is re-armed at clock + a random delay when its timer expires. It only runs while the patch is visible (`T:07B2`) and `T:07BE` is `-1`.

- Timing uses the engine's real-time clock, so the port needs the clock hook, not a frame counter.
- Each source latches its spot once and then reuses it — a balloon follows the last event, not the ant.
- The random delay is an LFSR draw, so balloons are part of the tick-for-tick stream.

## At a glance

- **62** lines
- **2 top-level functions**, including `_s32`, `balloons`
- **Original routines referenced:** `f_038a6`, `f_0696a`, `f_06a4d`, `f_07128`

## Source

{% raw %}
```python
"""Speech balloons (f_06a4d, from the window draw f_038a6 via f_07128): the ants' remarks at the spots the
event recorders (markers.py) found on screen. Runs only while the patch is visible (T:07B2) and T:07BE is -1.

Each source latches its recorded spot once (its gate becomes non-zero), then times its balloon with the
real-time clock: when a timer runs out it is re-armed at clock + a random delay and a coin decides whether
a balloon shows, each showing advancing to the next line of its string list. The line is drawn by
f_0696a(a, b, view, style, line), here st.player.effect(st, 'balloon', a, b, view, style, (list, index)).

The lists are STR#-style tables in the far heap (G:020A.. hold far pointers to them); only their lengths
matter here, where the index wraps (at the null entry).
"""
from .state import G, T
from .movement import s16

# (gate, recorded a / b / view, latched a / b / view, flags cleared on latching, balloons)
# balloon: (timer, delay draw, delay const, chance draw, shown flag, line index, list handle, lines, style)
SOURCES = (
    ('fight', 0xf06, (0x8ec, 0x8ee, 0xaea), (0x9f2, 0x9f4, 0xb06), (),
     ((0x50c, 'rand32', 0x3c, 'rand2', 0x1046, 0xf3c, 0x20a, 8, 0),           # the black ant's taunts
      (0x732, 'rand32', 0x3c, 'rand2', 0x1064, 0xff8, 0x218, 8, 1))),         # the red ant's
    ('brood', 0xef6, (0x852, 0x854, 0xaca), (0x8de, 0x8e0, 0xad8), (0x104a,),
     ((0x59a, 'rand32', 0xaa, 'rand4', 0x104a, 0xf7a, 0x21c, 15, 2),)),
    ('queen', 0xf10, (0xa02, 0xa04, 0xb08), (0xa8a, 0xa8c, 0xc3a), (0x1062,),
     ((0x620, 'rand32', 0xb4, 'rand4', 0x1062, 0xfc0, 0x234, 8, 2),)),
    ('rest', 0xf2e, (0xaa2, 0xaa4, 0xd68), (0xab2, 0xab4, 0xd9a), (0x107c,),
     ((0x7c4, 'rand64', 0x78, 'rand2', 0x107c, 0x103a, 0x23a, 8, 2),)),
)


def _s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


def balloons(st):
    """f_06a4d."""
    if st.u16(T, 0x7b2) == 0 or st.u16(T, 0x7be) != 0xffff:
        return
    for kind, gate, rec, lat, clear, timers in SOURCES:
        if st.u16(G, gate) == 0 and s16(st.u16(G, rec[0])) >= 0 and s16(st.u16(G, rec[1])) >= 0:
            for r, l in zip(rec, lat):
                st.set16(G, l, st.u16(G, r))
            st.set16(G, gate, st.u16(G, gate) + 1)
            for timer in timers:
                st.set32(G, timer[0], 0)
            for off in clear:
                st.set16(G, off, 0)
        if s16(st.u16(G, gate)) <= 0:
            continue
        if st.u16(G, 0x47e) == 0:
            for timer, delay, const, chance, shown, idx, table, lines, style in timers:
                if _s32(st.u32(G, timer)) < _s32(st.read_clock()):
                    st.set32(G, timer, (st.read_clock() + getattr(st, delay)() + const) & 0xffffffff)
                    if getattr(st, chance)() == 0:
                        st.set16(G, shown, 1)
                        i = st.u16(G, idx) + 1
                        st.set16(G, idx, 0 if s16(i) >= lines else i)
                    else:
                        st.set16(G, shown, 0)
        for timer, delay, const, chance, shown, idx, table, lines, style in timers:
            if st.u16(G, shown):
                a, b, view = (st.u16(G, off) for off in lat)
                st.player.effect(st, 'balloon', s16(a), s16(b), s16(view), style, (table, st.u16(G, idx)))
```
{% endraw %}
