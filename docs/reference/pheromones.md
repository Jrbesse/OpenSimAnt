---
layout: default
title: "Pheromone maps"
permalink: /reference/pheromones/
---

# Pheromone maps

*`pheromones.py` — 64 × 32 cells, one per 2 × 2 tiles, with four decay curves.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `pheromones.py`]({{ site.baseurl }}/assets/reference/simant_ref/pheromones.py)

The pheromone layers (`1496`): each map is addressed as `(segment, offset)` like the original, cell index `ca*32 + cb` with `ca = a>>1`, `cb = b>>1`. `decay_linear`, `decay_halving`, `diffuse_alarm`, `lay_max` and `wear_trail` reproduce the four different decays the game uses for food trails, alarm, nest markers and the red trail.

- The red food trail sits at `0x4da7:0000` (`SIM + 0xf8a0`), outside the 64 KB simulation segment.
- Decay runs on the tick counter's low bits, so a pause in the emulator changes pheromone strength if you get the phase wrong.
- `lay_max` is a maximum, not an add: two ants laying the same cell do not stack the value.

## At a glance

- **115** lines
- **15 top-level functions**, including `_cell`, `get`, `put`, `nest_markers`, `black_nest_markers`, `red_nest_markers`, `decay_linear`, `decay_black_nest` …
- **Original routines referenced:** `f_14966`, `f_149e9`, `f_14a6c`, `f_14ab3`, `f_14afa`, `f_14b5e`, `f_14bbe`, `f_14cf5`, `f_14d2c`, `f_14d9c`, `f_14e0c`

## Source

{% raw %}
```python
"""Pheromone maps (64 x 32, one cell per 2x2 surface tiles). Ported from SIMANT.EXE segment 1496 (flat 0x14966..).

Each map is addressed as (segment, offset) exactly like the original; cell index = ca*32 + cb, ca = a>>1, cb = b>>1.
The red food trail lives at 0x4da7:0000 (= SIM + 0xf8a0), past the 64 KB SIM segment.
"""
from .state import SIM, T

SIMHI = 0x4da7

SCRATCH = (SIM, 0xc89f)
ALARM = (SIM, 0xd09f)
P2 = (SIM, 0xd89f)
BLACK_NEST = (SIM, 0xe09f)
BLACK_TRAIL = (SIM, 0xe89f)
RED_NEST = (SIM, 0xf09f)
RED_TRAIL = (SIMHI, 0x0000)
SURFACE = 0x0180
ENTRANCE_A_BLACK = 0x0224   # T: surface a of the black entrance in column b (0 = none)
ENTRANCE_A_RED = 0x0264


def _cell(a, b):
    return (a & 0xfe) * 16 + (b >> 1)


def get(st, m, i):
    return st.u8(m[0], m[1] + i)


def put(st, m, i, v):
    st.set8(m[0], m[1] + i, v)


def nest_markers(st, entrance_table, nest_map):
    """f_14966 (black) / f_149e9 (red): pin entrance cells to 0xFF (0 if a rock 0x51 covers it)."""
    for b in range(64):
        a = st.u8(T, entrance_table + b)
        if a:
            blocked = st.grid(SURFACE, a, b) == 0x51
            put(st, nest_map, _cell(a, b), 0 if blocked else 0xff)


def black_nest_markers(st):
    nest_markers(st, ENTRANCE_A_BLACK, BLACK_NEST)


def red_nest_markers(st):
    nest_markers(st, ENTRANCE_A_RED, RED_NEST)


def decay_linear(st, m):
    """f_14a6c / f_14ab3: every cell -= 1 (floor 0). Nest-marker maps."""
    for i in range(64 * 32):
        v = get(st, m, i)
        if v:
            put(st, m, i, v - 1)


def decay_black_nest(st):
    decay_linear(st, BLACK_NEST)


def decay_red_nest(st):
    decay_linear(st, RED_NEST)


def decay_halving(st, m):
    """f_14afa / f_14b5e: v < 8 -> 0, else v -= v >> 1. Food-trail maps."""
    for i in range(64 * 32):
        v = get(st, m, i)
        put(st, m, i, 0 if v < 8 else v - (v >> 1))


def decay_black_trail(st):
    decay_halving(st, BLACK_TRAIL)


def decay_red_trail(st):
    decay_halving(st, RED_TRAIL)


def diffuse_alarm(st):
    """f_14bbe: copy alarm to scratch, then v = (v + (N+S+E+W)/4) / 2, cleared if <= 8."""
    for i in range(64 * 32):
        put(st, SCRATCH, i, get(st, ALARM, i))
    for ca in range(64):
        for cb in range(32):
            i = ca * 32 + cb
            s = 0
            if ca > 0:
                s = get(st, SCRATCH, i - 32)
            if cb > 0:
                s += get(st, SCRATCH, i - 1)
            if ca < 63:
                s += get(st, SCRATCH, i + 32)
            if cb < 31:
                s += get(st, SCRATCH, i + 1)
            v = (get(st, SCRATCH, i) + (s >> 2)) >> 1
            put(st, ALARM, i, v if v > 8 else 0)


def lay_max(st, m, a, b, strength):
    """f_14d2c/14d64 (nest marker), f_14d9c/14dd4 (food trail), f_14cf5 (alarm): cell = max(cell, strength)."""
    i = _cell(a, b)
    if get(st, m, i) < strength:
        put(st, m, i, strength)


def wear_trail(st, a, b, red):
    """f_14e0c: a step on the surface wears the colony's food trail by 1."""
    m = RED_TRAIL if red else BLACK_TRAIL
    i = (a >> 1) * 32 + (b >> 1)
    v = get(st, m, i)
    if v:
        put(st, m, i, v - 1)
```
{% endraw %}
