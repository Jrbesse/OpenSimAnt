---
layout: default
title: "The behaviour and caste triangles"
permalink: /reference/panels/
---

# The behaviour and caste triangles

*`panels.py` — Where the marker sits, and what a click means.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `panels.py`]({{ site.baseurl }}/assets/reference/simant_ref/panels.py)

Windows 18 and 19: the behaviour triangle (`G:049E`/`04A0`/`04A2` = forage apex, dig bottom-left, nurse bottom-right) and the caste triangle (`G:0482`/`0484`/`0486` = breeders, workers, soldiers). Each set sums to `0xFFFF`. `to_values` inverts a click position into the three weights; `to_point` places the marker.

- The triangles are the whole indirect-control interface in the original, and the reason the game is not an RTS.
- Barycentric conversion is integer-only and clamped; the sum staying at `0xFFFF` is the invariant.
- The weights persist in the save file, so a saved game keeps its policy.

## At a glance

- **77** lines
- **4 top-level functions**, including `triangle`, `_sdiv32`, `to_point`, `to_values`
- **Original routines referenced:** `f_07980`, `f_07a19`, `f_07a57`, `f_086a1`, `f_087c7`

## Source

{% raw %}
```python
"""The Behavior Control and Caste Control triangles (windows 18 / 19): where the marker sits for the colony's
three weights, and the weights a click in the triangle sets.

Behaviour weights G:049E / 04A0 / 04A2 = forage (apex), dig (bottom left), nurse (bottom right); caste weights
G:0482 / 0484 / 0486 = breeders (apex), workers (bottom left), soldiers (bottom right). Each set sums to
0xFFFF. The triangle is the rectangle of item 0x120D / 0x130D (f_07980), kept at G:3816 / G:3822 with its
sizes G:3814 (width), G:3810 = G:3812 (half width), G:380E (height) and G:382E (32-bit half width << 8 /
height); the marker point is G:0358 / G:022E (f_07a57 / f_07a19, also called from InitColonySettings).
"""
from .state import G


def triangle(st, rect, out):
    """f_07980(item, out): apex (left + w/2, top), bottom left (left, bottom), bottom right (right, bottom)."""
    left, top, right, bottom = rect
    w = (right - left) & 0xffff
    st.set16(G, 0x3814, w)
    st.set16(G, 0x3812, w >> 1)
    st.set16(G, 0x3810, w >> 1)
    h = (bottom - top) & 0xffff
    st.set16(G, 0x380e, h)
    st.set32(G, 0x382e, ((w >> 1) << 8) // h if h else 0)
    for i, v in enumerate((left + (w >> 1), top, left, bottom, right, bottom)):
        st.set16(G, out + 2 * i, v & 0xffff)


def _sdiv32(a, b):
    a = a - (1 << 32) if a & 0x80000000 else a
    b = b - (1 << 32) if b & 0x80000000 else b
    q = abs(a) // abs(b)
    return (q if (a >= 0) == (b >= 0) else -q) & 0xffffffff


def to_point(st, values, tri, out):
    """f_087c7: the marker for the weights at G:`values` (v0 apex, v1 bottom left, v2 bottom right)."""
    v0, v2 = st.u16(G, values), st.u16(G, values + 4)
    h = st.u16(G, 0x380e)
    y = ((0xffff - v0) * ((h - 2) & 0xffff)) // 0xffff + st.u16(G, tri + 2)
    st.set16(G, out + 2, y & 0xffff)
    k = (st.u16(G, 0x3810) * v0) // 0xffff & 0xffff
    m = (st.u16(G, 0x3814) - 2 * k) & 0xffff
    ms = m - 0x10000 if m & 0x8000 else m
    if v0 != 0xffff and ms >= 3:
        x = _sdiv32((v2 * ((ms - 3) & 0xffffffff)) & 0xffffffff, 0xffff - v0)
        x = (x + st.u16(G, tri + 4) + k) & 0xffff
    else:
        x = st.u16(G, tri)
    st.set16(G, out, (x + 2) & 0xffff)


def to_values(st, values, tri, point):
    """f_086a1: the weights a click at G:`point` sets."""
    dx = (st.u16(G, point) - st.u16(G, tri + 4)) & 0xffff
    dy = (st.u16(G, point + 2) - st.u16(G, tri + 2)) & 0xffff
    h = st.u16(G, 0x380e)
    if dy > ((h - 2) & 0xffff):
        v0 = 0
    else:
        v0 = _sdiv32((((h - dy - 2) & 0xffff) * 0xffff) & 0xffffffff, (h - 2) & 0xffff) & 0xffff
    st.set16(G, values, v0)
    k = (v0 * st.u16(G, 0x3810)) // 0xffff & 0xffff
    m = (st.u16(G, 0x3814) - 2 * k) & 0xffff
    ms = m - 0x10000 if m & 0x8000 else m
    if ms <= 2:
        st.set16(G, values + 2, 0)
        st.set16(G, values + 4, 0)
        return
    c = (dx - k) & 0xffff
    cs = c - 0x10000 if c & 0x8000 else c
    if ms - 2 <= cs:
        v2 = 0xffff - v0
    elif cs <= 2:
        v2 = 0
    else:
        v2 = _sdiv32(((0xffff - v0) * cs) & 0xffffffff, (ms - 2) & 0xffffffff) & 0xffff
    st.set16(G, values + 4, v2 & 0xffff)
    st.set16(G, values + 2, (0xffff - v2 - v0) & 0xffff)
```
{% endraw %}
