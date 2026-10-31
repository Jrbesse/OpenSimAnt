#!/usr/bin/env python3
"""make_yard.py - draws the clean-pack yard tile sheet procedurally.

Writes, next to this script:
  yard.pix     the 256 x 256 sheet (16 x 16 tiles of 16 x 16 px), one hex digit per pixel
  preview.png  the sheet at 3x with a grid and row / column numbers
  mockup.png   a small yard scene and a nest cross-section assembled from the tiles, at 2x

Deterministic: every random choice is seeded. Run: python make_yard.py
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

# palette indices (standard 16-colour Macintosh palette)
WHT, YEL, ORA, RED, MAG, PUR, BLU, CYA, GRN, DGN, BRN, TAN, LGR, MGR, DGY, BLK = range(16)
PALETTE = [(255, 255, 255), (252, 243, 5), (255, 100, 2), (221, 8, 6), (242, 8, 132), (70, 0, 165),
           (0, 0, 212), (2, 171, 234), (31, 183, 20), (0, 100, 17), (86, 44, 5), (144, 113, 58),
           (192, 192, 192), (128, 128, 128), (64, 64, 64), (0, 0, 0)]

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])

tiles = {}


def put(n, a):
    a = np.asarray(a)
    assert a.shape == (16, 16), (hex(n), a.shape)
    assert a.min() >= 0 and a.max() <= 15, hex(n)
    assert n not in tiles, hex(n)
    tiles[n] = a.astype(np.int16)


# ------------------------------------------------------------------ helpers

def grid(h, w):
    Y, X = np.mgrid[0:h, 0:w]
    return X + 0.5, Y + 0.5


def bayer(h, w):
    Y, X = np.mgrid[0:h, 0:w]
    return (BAYER4[Y % 4, X % 4] + 0.5) / 16.0


def checker(h, w):
    Y, X = np.mgrid[0:h, 0:w]
    return (X + Y) % 2 == 0


def plot(a, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= y < a.shape[0] and 0 <= x < a.shape[1]:
        a[y, x] = c


def line(a, x0, y0, x1, y1, c):
    x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        plot(a, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def polyline(a, pts, c):
    for p, q in zip(pts, pts[1:]):
        line(a, p[0], p[1], q[0], q[1], c)


def shift(m, dx, dy, fill=False):
    """r[y, x] = m[y - dy, x - dx] (content moved by +dx, +dy)."""
    h, w = m.shape
    r = np.full_like(m, fill)
    r[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = \
        m[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return r


def erode8(m, fill=False):
    r = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                r &= shift(m, dx, dy, fill)
    return r


def outline_cont(m, cont_h, cont_v):
    """Edge pixels of m (8-neighbour); the mask is taken to continue past the tile edge
    horizontally / vertically when cont_h / cont_v."""
    h, w = m.shape
    p = np.pad(m, 1, mode='edge')
    if not cont_v:
        p[0, :] = False
        p[-1, :] = False
    if not cont_h:
        p[:, 0] = False
        p[:, -1] = False
    e = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            e &= p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    return m & ~e


def paint_blob(a, m, base, light, dark, outline, cast=None):
    """Fill a mask as a rounded object lit from the top-left, with a cast shadow below-right."""
    if cast is not None:
        a[shift(m, 1, 1) & ~m] = cast
    a[m] = base
    inner = erode8(m)
    a[inner & ~shift(inner, -1, -1)] = dark
    a[inner & ~shift(inner, 1, 1)] = light
    a[m & ~inner] = outline


RAMP = [(0.0, BLK), (0.16, DGY), (0.38, BRN), (0.72, TAN), (1.0, LGR)]


def ramp(s, b):
    """Dithered colour for brightness s (0 dark .. 1 light), b = threshold array."""
    s = np.clip(s, 0.0, 1.0)
    out = np.full(s.shape, BLK, dtype=np.int16)
    for (p0, c0), (p1, c1) in zip(RAMP, RAMP[1:]):
        sel = (s >= p0) & (s <= p1)
        f = (s - p0) / (p1 - p0)
        out[sel] = np.where(b[sel] < f[sel], c1, c0)
    return out


# ------------------------------------------------------------------ textures

def ground(seed):
    """Bare sandy soil: tan with fine brown / grey grains. No structure crosses the tile edge."""
    r = random.Random(seed)
    a = np.full((16, 16), TAN, dtype=np.int16)
    for y in range(16):
        for x in range(16):
            v = r.random()
            if v < 0.07:
                a[y, x] = BRN
            elif v < 0.105:
                a[y, x] = MGR
            elif v < 0.115:
                a[y, x] = LGR
    for _ in range(r.randint(2, 4)):            # lit grains with a tiny shadow
        x, y = r.randint(0, 14), r.randint(0, 14)
        a[y, x] = LGR
        a[y + 1, x + 1] = BRN
    return a


def soil_tex(seed, wet=False):
    r = random.Random(seed)
    a = np.full((16, 16), BRN, dtype=np.int16)
    for y in range(16):
        for x in range(16):
            v = r.random()
            if v < 0.09:
                a[y, x] = TAN
            elif v < 0.15:
                a[y, x] = DGY
            elif v < 0.17:
                a[y, x] = BLK
            elif wet and v < 0.21:
                a[y, x] = BLU
    return a


def tunnel(seed):
    r = random.Random(seed)
    # Open nest space: a light tone (light grey 12 with light speckle), clearly lighter than the
    # brown packed soil, so dark-bodied ants with black outlines (and the yellow / red ones) stand out.
    a = np.full((16, 16), LGR, dtype=np.int16)
    for y in range(16):
        for x in range(16):
            v = r.random()
            if v < 0.07:
                a[y, x] = MGR
            elif v < 0.12:
                a[y, x] = WHT
            elif v < 0.15:
                a[y, x] = TAN
    return a


def water(seed):
    r = random.Random(seed)
    a = np.full((16, 16), BLU, dtype=np.int16)
    b = bayer(16, 16)
    a[b < 0.07] = CYA
    for _ in range(r.randint(4, 6)):
        x, y, n = r.randint(1, 10), r.randint(1, 14), r.randint(2, 4)
        a[y, x:x + n] = CYA
    for _ in range(2):
        a[r.randint(1, 14), r.randint(1, 14)] = WHT
    return a


# ------------------------------------------------------------------ small drawn things

def small_stone(a, x, y, r):
    """A tiny pebble on the ground (3 x 2 px + shadow)."""
    w = r.choice([2, 3])
    a[y, x:x + w] = LGR
    a[y + 1, x:x + w] = MGR
    a[y + 1, x] = LGR
    a[y + 2, x + 1:x + w + 1] = BRN
    a[y + 1, x + w] = BRN


def crumb(a, cx, cy, rad, seed, bites=(), outline=DGY, cast=BRN):
    rr = random.Random(seed)
    p1, p2 = rr.uniform(0, 6.3), rr.uniform(0, 6.3)
    X, Y = grid(*a.shape)
    dx, dy = X - cx, Y - cy
    d, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    rr_ = rad * (1 + 0.13 * np.sin(3 * th + p1) + 0.08 * np.sin(5 * th + p2))
    m = d <= rr_
    for bx, by, br in bites:
        m &= np.hypot(X - bx, Y - by) > br
    if cast is not None:
        a[shift(m, 1, 1) & ~m] = cast
    a[m] = WHT
    inner = erode8(m)
    ys, xs = np.nonzero(inner)
    for i in range(len(xs)):
        if rr.random() < 0.10:
            a[ys[i], xs[i]] = LGR
    a[inner & (~shift(inner, -1, -1) | ~shift(inner, -1, 0) | ~shift(inner, 0, -1))] = LGR
    a[inner & ~shift(inner, 1, 1)] = ORA
    a[m & ~inner] = outline
    return m


def ant(a, cx, cy, ang, body, hi, leg, dead=True, flip=False):
    """A small ant. Dead: legs curled in, smaller; live (mock-up only): legs out."""
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    s = -1 if flip else 1
    X, Y = grid(*a.shape)
    u = (X - cx) * ux + (Y - cy) * uy
    v = ((X - cx) * vx + (Y - cy) * vy) * s
    k = 1.0 if dead else 1.25
    gaster = ((u + 2.9 * k) / (2.6 * k)) ** 2 + (v / (2.0 * k)) ** 2 <= 1
    thorax = ((u - 0.4 * k) / (1.5 * k)) ** 2 + (v / (1.0 * k)) ** 2 <= 1
    head = ((u - 2.8 * k) / (1.4 * k)) ** 2 + (v / (1.3 * k)) ** 2 <= 1

    def P(uu, vv):
        vv *= s
        return (cx + uu * ux + vv * vx - 0.5, cy + uu * uy + vv * vy - 0.5)

    if dead:
        legs = [[(0.0, 0), (-0.8, 2.3), (0.2, 2.9)], [(0.5, 0), (0.9, 2.5), (1.8, 2.4)],
                [(1.0, 0), (2.2, 1.9), (2.6, 1.0)]]
        ants_ = [[(3.8, 0.4), (4.8, 1.2), (4.4, 2.0)]]
    else:
        legs = [[(0.0, 0), (-1.5, 3.4), (-3.4, 4.6)], [(0.5, 0), (0.6, 3.8), (0.2, 5.4)],
                [(1.0, 0), (2.6, 3.4), (4.0, 4.4)]]
        ants_ = [[(4.4, 0.5), (5.8, 1.6), (7.0, 1.3)]]
    for side in (1, -1):
        for lg in legs + ants_:
            polyline(a, [P(uu, vv * side) for uu, vv in lg], leg)
    m = gaster | thorax | head
    a[m] = body
    # one highlight pixel on the gaster and the head
    for hu, hv in ((-3.6 * k, -0.8 * k), (2.6 * k, -0.5 * k)):
        x, y = P(hu, hv)
        plot(a, x, y, hi)
    return m


# ------------------------------------------------------------------ surface: open ground 00..0F

def ground_variant(n):
    a = ground(100 + n)
    r = random.Random(900 + n)
    kind = ['', 'pebble', 'dark', '', 'stones', 'crack', '', 'light', 'pebble', '', 'dark',
            'root', '', 'pebble', 'grains', ''][n]
    if kind == 'pebble':
        small_stone(a, r.randint(3, 10), r.randint(3, 10), r)
    elif kind == 'stones':
        small_stone(a, r.randint(2, 5), r.randint(2, 5), r)
        small_stone(a, r.randint(9, 11), r.randint(8, 11), r)
    elif kind == 'dark':
        x0, y0 = r.randint(3, 9), r.randint(3, 9)
        for _ in range(7):
            plot(a, x0 + r.randint(0, 3), y0 + r.randint(0, 3), BRN)
        plot(a, x0 + 1, y0 + 1, DGY)
    elif kind == 'crack':
        x, y = r.randint(3, 7), r.randint(4, 8)
        for i in range(5):
            plot(a, x + i, y + (i // 2), BRN)
            plot(a, x + i, y + (i // 2) + 1, LGR if i % 2 else TAN)
    elif kind == 'light':
        x0, y0 = r.randint(3, 9), r.randint(3, 9)
        for _ in range(6):
            plot(a, x0 + r.randint(0, 3), y0 + r.randint(0, 3), LGR)
    elif kind == 'root':
        x, y = r.randint(3, 6), r.randint(4, 10)
        polyline(a, [(x, y), (x + 3, y - 1), (x + 6, y - 1), (x + 8, y + 1)], BRN)
    elif kind == 'grains':
        for _ in range(4):
            x, y = r.randint(2, 12), r.randint(2, 12)
            a[y, x] = LGR
            a[y + 1, x + 1] = BRN
    return a


for n in range(16):
    put(n, ground_variant(n))

# ------------------------------------------------------------------ dead ants 10..17
DEAD = [(8.2, 8.0, 0.35, False), (8.0, 8.4, 1.9, True), (7.8, 7.6, 3.6, False), (8.3, 8.2, 5.1, True)]
for i, (cx, cy, ang, fl) in enumerate(DEAD):
    a = ground(200 + i)
    ant(a, cx, cy, ang, BLK, DGY, BLK, dead=True, flip=fl)
    put(0x10 + i, a)
for i, (cx, cy, ang, fl) in enumerate(DEAD):
    a = ground(210 + i)
    ant(a, cx, cy, ang + 0.6, RED, ORA, BRN, dead=True, flip=not fl)
    put(0x14 + i, a)


# ------------------------------------------------------------------ composites on a 3 x 3 / 2 x 2 patch

def ground_patch(cols, rows, seed):
    A = np.zeros((rows * 16, cols * 16), dtype=np.int16)
    for j in range(rows):
        for i in range(cols):
            A[j * 16:(j + 1) * 16, i * 16:(i + 1) * 16] = ground(seed + j * cols + i)
    return A


def cut(A, cols, rows, numbers):
    k = 0
    for j in range(rows):
        for i in range(cols):
            put(numbers[k], A[j * 16:(j + 1) * 16, i * 16:(i + 1) * 16])
            k += 1


def nest_mound():
    A = ground_patch(3, 3, 300)
    rng = np.random.RandomState(31)
    X, Y = grid(48, 48)
    dx, dy = X - 24, Y - 24
    d, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    light = -(dx + dy) / (math.sqrt(2) * np.maximum(d, 0.5))        # +1 on the up-left side
    outer = 18.5 + 1.3 * np.sin(3 * th + 0.7) + 0.8 * np.sin(5 * th + 2.0)
    hole = 4.6 + 0.5 * np.sin(2 * th + 1.0)
    crest = 9.0
    L = np.where(d > crest, light, -light)                           # slope facing the light?
    H = np.where(d < crest, (d - hole) / (crest - hole), (outer - d) / (outer - crest))
    H = np.clip(H, 0, 1)
    b = bayer(48, 48)
    keep = rng.uniform(0, 1, (48, 48))
    # cast shadow of the heap on the ground, bottom-right
    sh = (d >= outer - 1) & (d < outer + 2.2) & (light < -0.15) & (b < 0.5)
    A[sh] = BRN
    base = (H > 0.12) | ((H > 0) & (keep < H * 6))
    s = 0.54 + 0.34 * L * np.clip(H * 2, 0, 1) + rng.uniform(-0.06, 0.06, (48, 48))
    A[base] = ramp(s, b)[base]
    # crumbly pellets of dug-out soil, lit from the top-left
    r = random.Random(318)
    for _ in range(420):
        x, y = r.randint(1, 45), r.randint(1, 45)
        if H[y, x] <= 0 or r.random() > H[y, x] * 0.9 + 0.1 or d[y, x] < hole[y, x] + 1:
            continue
        l = L[y, x] + r.uniform(-0.3, 0.3)
        if l > 0.35:
            c = (LGR, TAN, TAN, BRN)
        elif l > -0.25:
            c = (TAN, BRN, BRN, DGY)
        else:
            c = (BRN, DGY, DGY, BLK)
        A[y, x], A[y, x + 1], A[y + 1, x], A[y + 1, x + 1] = c
    rim = d < hole + 1.6
    A[rim] = ramp(0.20 - 0.25 * light + rng.uniform(-0.05, 0.05, (48, 48)), b)[rim]
    A[d < hole] = BLK
    A[(d < hole) & (d > hole - 1.0) & (light < -0.3)] = DGY
    mound = base | sh
    assert not mound[:2, :].any() and not mound[-2:, :].any() and not mound[:, :2].any() and not mound[:, -2:].any()
    return A


M = nest_mound()
cut(M, 3, 3, [0x18, 0x19, 0x1A, 0x1B, 0x50, 0x1C, 0x1D, 0x1E, 0x1F])


def leaf_patch():
    A = ground_patch(2, 2, 320)
    X, Y = grid(32, 32)
    ang = math.radians(-35)
    ux, uy = math.cos(ang), math.sin(ang)
    cx, cy = 16.0, 16.5
    u = (X - cx) * ux + (Y - cy) * uy
    v = -(X - cx) * uy + (Y - cy) * ux
    Lh = 12.0
    t = np.clip((u + Lh) / (2 * Lh), 0, 1)
    half = 6.6 * np.sin(np.pi * t) ** 0.7 * (1 - 0.18 * t) * (1 + 0.07 * np.sin(t * 46))
    m = (np.abs(v) <= half) & (u >= -Lh) & (u <= Lh)
    # stem
    stem = (u < -Lh + 0.5) & (u > -Lh - 3.5) & (np.abs(v) < 0.6)
    A[shift(m | stem, 1, 1) & ~(m | stem)] = BRN
    A[stem] = BRN
    A[m] = GRN
    b = bayer(32, 32)
    A[m & (v > 1.2) & (b < 0.35)] = DGN                                      # the shaded half
    vein = m & (np.abs(v) > 1.0) & (((u - np.abs(v) * 1.1) % 4.2) < 0.75)
    A[vein] = DGN
    A[m & (np.abs(v) < 0.55)] = DGN                                          # midrib
    A[m & ~erode8(m)] = DGN
    for p in [(10, 13), (21, 19), (14, 22)]:                                 # a few holes / blemishes
        if m[p[1], p[0]]:
            A[p[1], p[0]] = BRN
    assert not (m | stem)[0, :].any() and not (m | stem)[:, 0].any()
    assert not m[-1, :].any() and not m[:, -1].any()
    return A


cut(leaf_patch(), 2, 2, [0x20, 0x21, 0x22, 0x23])


def twig_patch():
    A = ground_patch(2, 1, 330)
    X, Y = grid(16, 32)
    yc = 8.6 + 1.2 * np.sin(X / 32 * np.pi * 1.4) - 0.05 * (X - 16)
    m = (np.abs(Y - yc) <= 2.1) & (X > 2) & (X < 30)
    # rounded ends
    m &= ~((X < 3.6) & (np.abs(Y - yc) > 1.2)) & ~((X > 29) & (np.abs(Y - yc) > 1.2))
    br = np.zeros_like(m)
    for (x0, y0, x1, y1) in [(19, 7, 24, 3), (20, 7, 25, 3), (9, 10, 12, 13)]:
        tmp = np.zeros((16, 32), dtype=np.int16)
        line(tmp, x0, y0, x1, y1, 1)
        br |= tmp.astype(bool)
    br = br | shift(br, 0, 1)
    full = m | br
    A[shift(full, 1, 1) & ~full] = BRN
    A[shift(full, 1, 2) & ~full & ~shift(full, 1, 1)] = BRN
    A[full] = BRN
    inner = erode8(full)
    A[inner & ~shift(inner, 0, 1)] = MGR
    A[inner & ~shift(inner, 0, -1)] = DGY
    A[full & ~inner] = BLK
    for x in (7, 15, 26):                                                    # knots
        y = int(yc[0, x])
        A[y, x] = DGY
        A[y, x + 1] = BLK
    return A


cut(twig_patch(), 2, 1, [0x24, 0x25])


def grass_patch():
    A = ground_patch(2, 1, 340)
    X, Y = grid(16, 32)
    yc = 10.5 - 4.0 * np.sin((X - 2) / 28 * np.pi * 0.6) + 0.002 * (X - 2) ** 2
    stem = (np.abs(Y - yc) <= 1.1) & (X > 2) & (X < 23)
    # seed head (spikelet) at the right end
    u, v = X - 26.0, Y - (yc - 0.0)
    head = (u / 4.6) ** 2 + (v / 2.2) ** 2 <= 1
    full = stem | head
    A[shift(full, 1, 1) & ~full] = BRN
    A[full] = LGR
    inner = erode8(full)
    A[stem & ~shift(stem, 0, 1)] = WHT
    A[full & ~inner] = MGR
    hs = head & inner
    A[hs] = TAN
    A[hs & (np.floor(u) % 3 == 0)] = BRN                                    # rows of husks
    A[hs & ~shift(hs, 1, 1)] = LGR
    A[head & ~inner] = DGY
    A[np.round(yc[0, 3]).astype(int) - 1, 2:4] = MGR
    return A


cut(grass_patch(), 2, 1, [0x26, 0x27])

# weed tuft 28
a = ground(350)
for x in range(5, 12):
    a[13, x] = BRN
blades = [((8, 12), (2, 5), DGN), ((8, 12), (13, 4), DGN), ((7, 12), (4, 2), DGN), ((9, 12), (11, 1), DGN),
          ((8, 12), (8, 1), GRN), ((7, 12), (3, 8), GRN), ((9, 12), (14, 8), GRN), ((8, 12), (6, 3), GRN),
          ((8, 12), (10, 3), GRN)]
for (x0, y0), (x1, y1), c in blades:
    line(a, x0, y0, x1, y1, c)
    line(a, x0 + 1, y0, (x0 + x1) / 2 + 1, (y0 + y1) / 2, c)
for x in (6, 7, 8, 9, 10):
    a[12, x] = DGN
a[12, 11] = BRN
put(0x28, a)


# ------------------------------------------------------------------ ant-lion pit 30..37, 38..3F

def antlion_patch():
    A = ground_patch(3, 3, 360)
    rng = np.random.RandomState(36)
    X, Y = grid(48, 48)
    dx, dy = X - 24, Y - 24
    d, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    light = -(dx + dy) / (math.sqrt(2) * np.maximum(d, 0.5))
    Rf = 20.0 + 0.8 * np.sin(4 * th + 1.1) + 0.5 * np.sin(7 * th)
    g = d / Rf
    gg = np.clip(g, 0, 1)
    # a smooth cone of loose sand, quantised so the dither stays clean: light (lit inner wall
    # bottom-right) at the rim, darkening steadily to a black throat
    s = 0.04 + 0.80 * gg ** 0.9 - 0.26 * light * np.sin(np.pi * gg) ** 0.6
    s = np.round(np.clip(s, 0, 0.86) * 10) / 10
    col = ramp(s, bayer(48, 48))
    col[gg < 0.13] = BLK
    lip = (g > 0.80) & (g < 0.90) & (light > 0.25)               # shadow under the rim, up-left
    col[lip & checker(48, 48)] = BRN
    rimz = (g >= 0.90) & (g < 1.0)                               # the rim of loose dry sand
    col[rimz] = TAN
    col[rimz & (bayer(48, 48) < 0.25)] = LGR
    gr = rng.uniform(0, 1, (48, 48))
    col[(gr < 0.03) & (g < 0.88) & (g > 0.3) & (light < 0)] = LGR  # a few rolling grains
    keep = rng.uniform(0, 1, (48, 48))
    funnel = (g < 1.0) | ((g < 1.06) & (keep < (1.06 - g) / 0.06))
    col[(g >= 1.0) & funnel] = TAN
    A[funnel] = col[funnel]
    assert not funnel[:2, :].any() and not funnel[-2:, :].any() and not funnel[:, :2].any() and not funnel[:, -2:].any()
    return A


AL = antlion_patch()
cut(AL, 3, 3, [0x30, 0x31, 0x32, 0x33, 0x38, 0x34, 0x35, 0x36, 0x37])
PIT = AL[16:32, 16:32].copy()


def jaws(a, open_, length, head=True):
    """Ant-lion head and sickle jaws rising from the pit centre (8, 8)."""
    if head:
        X, Y = grid(16, 16)
        hm = ((X - 8) / 2.4) ** 2 + ((Y - 9.4) / 1.9) ** 2 <= 1
        a[hm] = BRN
        a[hm & ~erode8(hm)] = BLK
        plot(a, 6.5, 8.5, BLK)
        plot(a, 8.5, 8.5, BLK)
        plot(a, 7, 9, TAN)
    for side in (-1, 1):
        if open_ >= 0.5:
            pts = [(0.8, 0), (2.4, -1.6), (3.0, -3.4), (2.4, -5.0), (1.2, -5.6)]
        elif open_ > 0:
            pts = [(0.8, 0), (1.9, -1.6), (2.0, -3.2), (1.2, -4.4), (0.2, -4.8)]
        else:
            pts = [(0.8, 0), (1.4, -1.6), (1.0, -3.0), (-0.4, -3.8), (-1.6, -3.9)]
        pts = [(8 + side * px * 1.2 - 0.5, 8.5 + py * length * 1.2) for px, py in pts]
        polyline(a, [(x + side, y) for x, y in pts[:4]], BRN)
        polyline(a, pts, TAN)
        polyline(a, [(x, y - 1) for x, y in pts[1:3]], LGR)
        tx, ty = pts[-1]
        plot(a, tx, ty, BLK)
        if length >= 0.9:
            mx, my = pts[2]
            plot(a, mx - side, my, LGR)                                      # a tooth


def spray(a, seed, n, rmin, rmax, cols=(LGR, WHT, LGR, TAN)):
    r = random.Random(seed)
    for _ in range(n):
        an = r.uniform(0, 2 * math.pi)
        rad = r.uniform(rmin, rmax)
        x, y = 7.5 + math.cos(an) * rad, 7.5 + math.sin(an) * rad * 0.9 - 1.0
        plot(a, x, y, r.choice(cols))
        if rad > 4 and r.random() < 0.5:                                     # motion streak
            plot(a, x - math.cos(an), y - math.sin(an), TAN)


FRAMES = [
    dict(sp=(6, 2, 5)),                                    # 39 the sand trembles
    dict(sp=(18, 3, 8)),                                   # 3A sand thrown up
    dict(sp=(14, 4, 8), jaw=(0.6, 0.6)),                   # 3B jaws break the surface
    dict(sp=(10, 5, 8), jaw=(1.0, 1.0)),                   # 3C jaws wide open
    dict(sp=(10, 2, 7), jaw=(0.0, 1.0)),                   # 3D jaws snap shut
    dict(sp=(6, 1, 4), jaw=(0.0, 0.5), cols=(TAN, LGR)),   # 3E sinking, sand slides back
    dict(sp=(3, 1, 3), cols=(TAN, LGR)),                   # 3F settling
]
for k, f in enumerate(FRAMES):
    a = PIT.copy()
    if 'jaw' in f:
        jaws(a, *f['jaw'])
    n, r0, r1 = f['sp']
    spray(a, 400 + k, n, r0, r1, f.get('cols', (LGR, WHT, LGR, TAN)))
    put(0x39 + k, a)

# ------------------------------------------------------------------ food crumbs 48..4B
CRUMBS = [(2.7, [], 0), (4.3, [(12.0, 4.6, 2.4), (3.6, 12.4, 2.0)], 1), (5.6, [(13.6, 4.2, 2.8)], 2),
          (6.6, [], 3)]
for i, (rad, bites, sd) in enumerate(CRUMBS):
    a = ground(440 + i)
    crumb(a, 8.0, 8.0, rad, 450 + sd, bites)
    put(0x48 + i, a)

# ------------------------------------------------------------------ pebble 51
a = ground(510)
X, Y = grid(16, 16)
th = np.arctan2(Y - 8, X - 7.6)
m = ((X - 7.6) / (6.6 * (1 + 0.06 * np.sin(3 * th)))) ** 2 + ((Y - 8.0) / 5.9) ** 2 <= 1
paint_blob(a, m, MGR, LGR, DGY, BLK, cast=BRN)
a[shift(m, 2, 2) & ~m & ~shift(m, 1, 1) & checker(16, 16)] = BRN
r = random.Random(51)
for _ in range(6):
    x, y = r.randint(4, 10), r.randint(5, 10)
    if erode8(erode8(m))[y, x]:
        a[y, x] = r.choice([LGR, DGY])
a[5, 5] = WHT
a[5, 6] = WHT
a[6, 5] = WHT
put(0x51, a)

# ------------------------------------------------------------------ boulders 54..5F (and nest soil, same method)
INS = {  # inset of the rock edge from the cell border, per pixel along that side (0 at both ends)
    'n': [0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0],
    'e': [0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 2, 1, 1, 0, 0, 0],
    's': [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 2, 1, 1, 0, 0, 0],
    'w': [0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
}


def cell_mask(n, e, s, w, R):
    Yi, Xi = np.mgrid[0:16, 0:16]
    m = np.ones((16, 16), bool)
    if not n:
        m &= Yi >= np.array(INS['n'])[Xi]
    if not s:
        m &= Yi <= 15 - np.array(INS['s'])[Xi]
    if not w:
        m &= Xi >= np.array(INS['w'])[Yi]
    if not e:
        m &= Xi <= 15 - np.array(INS['e'])[Yi]
    xc, yc = Xi + 0.5, Yi + 0.5

    def rnd(cx, cy, region):
        m[region & ((xc - cx) ** 2 + (yc - cy) ** 2 > R * R)] = False

    if not n and not w:
        rnd(R, R, (xc < R) & (yc < R))
    if not n and not e:
        rnd(16 - R, R, (xc > 16 - R) & (yc < R))
    if not s and not w:
        rnd(R, 16 - R, (xc < R) & (yc > 16 - R))
    if not s and not e:
        rnd(16 - R, 16 - R, (xc > 16 - R) & (yc > 16 - R))
    return m


def solid_tile(nb, style, seed, fill):
    """Draw the middle cell of a 3 x 3 neighbourhood of solid (True) / open cells, shading over
    the whole 48 x 48 patch so that edges agree with the neighbours' tiles."""
    Mk = np.zeros((48, 48), bool)

    def get(r, c):
        return nb[r][c] if 0 <= r < 3 and 0 <= c < 3 else True

    for r in range(3):
        for c in range(3):
            if nb[r][c]:
                Mk[r * 16:(r + 1) * 16, c * 16:(c + 1) * 16] = \
                    cell_mask(get(r - 1, c), get(r, c + 1), get(r + 1, c), get(r, c - 1), style['R'])
    rng = np.random.RandomState(seed)
    A = np.full((48, 48), style['base'], dtype=np.int16)
    noise = rng.uniform(0, 1, (48, 48))
    acc = 0.0
    for col, p in style['specks']:
        A[(noise >= acc) & (noise < acc + p)] = col
        acc += p
    edge = Mk & ~erode8(Mk, True)
    I = Mk & ~edge

    def g(dx, dy):
        return ~shift(Mk, -dx, -dy, True)

    hl2 = I & (g(-2, 0) | g(0, -2) | g(-2, -2) | g(-1, -2) | g(-2, -1))
    hl3 = I & (g(-3, 0) | g(0, -3) | g(-3, -3) | g(-3, -2) | g(-2, -3) | g(-3, -1) | g(-1, -3)) & ~hl2
    dk2 = I & (g(2, 0) | g(0, 2) | g(2, 2) | g(1, 2) | g(2, 1)) & ~hl2
    dk3 = I & (g(3, 0) | g(0, 3) | g(3, 3) | g(3, 2) | g(2, 3) | g(3, 1) | g(1, 3)) & ~hl2 & ~dk2 & ~hl3
    ch = checker(48, 48)
    A[dk3 & ch] = style['dark']
    A[dk2] = style['dark']
    A[hl3 & ch] = style['light']
    A[hl2] = style['light']
    A[edge] = style['outline']
    a = A[16:32, 16:32].copy()
    mc = Mk[16:32, 16:32]
    a[~mc] = fill[~mc]
    return a, mc


ROCK = dict(R=7, base=MGR, light=LGR, dark=DGY, outline=BLK, specks=[(LGR, 0.05), (DGY, 0.07)])
ROCKS = {
    0x5B: [[0, 0, 0], [0, 1, 1], [0, 1, 1]], 0x54: [[0, 0, 0], [1, 1, 1], [1, 1, 1]],
    0x55: [[0, 0, 0], [1, 1, 0], [1, 1, 0]], 0x5A: [[0, 1, 1], [0, 1, 1], [0, 1, 1]],
    0x5C: [[1, 1, 1], [1, 1, 1], [1, 1, 1]], 0x56: [[1, 1, 0], [1, 1, 0], [1, 1, 0]],
    0x59: [[0, 1, 1], [0, 1, 1], [0, 0, 0]], 0x58: [[1, 1, 1], [1, 1, 1], [0, 0, 0]],
    0x57: [[1, 1, 0], [1, 1, 0], [0, 0, 0]], 0x5D: [[1, 1, 1], [1, 1, 1], [0, 1, 1]],
    0x5E: [[1, 1, 0], [1, 1, 1], [1, 1, 1]], 0x5F: [[1, 1, 1], [1, 1, 1], [1, 1, 0]],
}
for n, nb in ROCKS.items():
    nbb = [[bool(v) for v in row] for row in nb]
    a, mc = solid_tile(nbb, ROCK, 540 + n, ground(560 + n))
    if n == 0x5C:                                                            # a couple of cracks inside
        for pts in ([(3, 5), (5, 6), (7, 6), (8, 8)], [(10, 10), (12, 11), (13, 13)]):
            polyline(a, pts, DGY)
            polyline(a, [(x + 1, y + 1) for x, y in pts], LGR)
            polyline(a, pts, DGY)
    put(n, a)


# ------------------------------------------------------------------ player-built wall 60..67

def wall(conn, seed):
    a = ground(seed)
    lo, hi = 2, 12
    m = np.zeros((16, 16), bool)
    m[lo:hi + 1, lo:hi + 1] = True
    if 'N' in conn:
        m[0:hi + 1, lo:hi + 1] = True
    if 'S' in conn:
        m[lo:16, lo:hi + 1] = True
    if 'W' in conn:
        m[lo:hi + 1, 0:hi + 1] = True
    if 'E' in conn:
        m[lo:hi + 1, lo:16] = True
    for (y, x, d1, d2) in ((lo, lo, 'N', 'W'), (lo, hi, 'N', 'E'), (hi, lo, 'S', 'W'), (hi, hi, 'S', 'E')):
        if d1 not in conn and d2 not in conn:
            m[y, x] = False
    sh = shift(m, 1, 1) & ~m
    sh2 = shift(m, 2, 2) & ~m & ~sh
    a[sh] = BRN
    a[sh2 & (bayer(16, 16) < 0.5)] = BRN
    horiz = ('E' in conn or 'W' in conn)
    vert = ('N' in conn or 'S' in conn)
    corner = horiz and vert
    Yi, Xi = np.mgrid[0:16, 0:16]
    for y in range(16):
        for x in range(16):
            if not m[y, x]:
                continue
            in_sq = lo <= x <= hi and lo <= y <= hi
            if corner and in_sq:
                c, t, cap = None, None, True
            else:
                cap = False
                use_h = horiz if in_sq else (lo <= y <= hi and (x < lo or x > hi))
                c, t = ((y - lo), x) if use_h else ((x - lo), y)
            if cap:
                cx, cy = x - lo, y - lo
                col = LGR
                if cx == 1 or cy == 1:
                    col = WHT
                if cx == 9 or cy == 9:
                    col = MGR
                if ('N' in conn and cy == 0) or ('S' in conn and cy == 10) or \
                        ('W' in conn and cx == 0) or ('E' in conn and cx == 10):
                    col = DGY
                a[y, x] = col
                continue
            if c in (0, 10):
                a[y, x] = BLK
                continue
            if c == 5:
                a[y, x] = DGY
                continue
            course = 0 if c < 5 else 1
            cc = c - 1 if course == 0 else c - 6                  # 0..3 across the course
            j = 5 if course == 0 else 1
            tt = (t - j) % 8
            if tt == 0:
                col = DGY
            elif cc == 0 or tt == 1:
                col = WHT
            elif cc == 3 or tt == 7:
                col = MGR
            else:
                col = LGR
            a[y, x] = col
    # weathering specks (inside blocks only)
    r = random.Random(seed)
    for _ in range(4):
        x, y = r.randint(0, 15), r.randint(0, 15)
        if m[y, x] and a[y, x] == LGR:
            a[y, x] = MGR
    a[outline_cont(m, True, True)] = BLK
    return a


WALLS = {0x60: 'EW', 0x61: 'NS', 0x62: 'S', 0x64: 'N', 0x65: 'E', 0x63: 'W', 0x66: 'NE', 0x67: 'WS'}
for n, conn in WALLS.items():
    put(n, wall(set(conn), 600 + n))


# ------------------------------------------------------------------ caterpillar 68..6F

def cat_body(a, hfun, legs, lo=-1.0, hi=17.0):
    X, Y = grid(16, 16)
    h = hfun(X)
    v = np.abs(Y - 8.0)
    m = (v <= h) & (X > lo) & (X < hi)
    if legs:
        for x in legs:
            for yy in (int(8 - h[0, x] - 1), int(8 + h[0, x])):
                a[yy, x] = BLK
                a[yy, x + 1] = BLK
    q = v / np.maximum(h, 0.1)
    a[m] = GRN
    a[m & (q > 0.62) & (bayer(16, 16) < 0.5)] = DGN
    a[m & (q > 0.8)] = DGN
    a[m & (q < 0.2) & (bayer(16, 16) < 0.25)] = DGN
    return m


def h69(X):
    return 4 + 3.0 * np.sin(np.pi * X / 16)


def h6a(X):
    return 4 + 2.0 * np.sin(np.pi * (X / 16) ** 0.8)


a = ground(690)
m = cat_body(a, h69, None)
a[outline_cont(m, True, False)] = BLK
a[7, 8] = YEL
a[8, 8] = YEL
a[4, 7] = WHT
a[11, 9] = BLK
cat69 = a
a = ground(691)
m = cat_body(a, h6a, [6, 9])
a[outline_cont(m, True, False)] = BLK
a[7, 7] = YEL
a[8, 7] = YEL
a[5, 6] = WHT
cat6a = a

# head facing W
a = ground(692)
X, Y = grid(16, 16)
hb = 4 + 1.6 * np.sin(np.pi * np.clip((X - 6) / 10, 0, 1))
neck = (np.abs(Y - 8.0) <= hb) & (X > 6)
hd = ((X - 6.0) / 4.7) ** 2 + ((Y - 8.0) / 4.9) ** 2 <= 1
for (x0, y0, x1, y1) in ((3, 4, 1, 1), (3, 11, 1, 14)):                    # antennae
    line(a, x0, y0, x1, y1, BLK)
a[neck] = GRN
a[neck & (np.abs(Y - 8) / hb > 0.62) & (bayer(16, 16) < 0.5)] = DGN
a[neck & (np.abs(Y - 8) / hb > 0.8)] = DGN
a[hd] = DGN
a[hd & (((X - 5.0) / 3.2) ** 2 + ((Y - 6.5) / 2.6) ** 2 <= 1)] = GRN       # lit dome of the head
full = neck | hd
a[outline_cont(full, True, False) & ~(X < 0)] = BLK
a[full & ~neck & (X > 7.5) & (X < 8.6)] = BLK                              # head / body joint
for (x, y) in ((3, 6), (3, 9)):
    a[y, x] = WHT
    a[y, x - 1] = BLK
a[7, 1] = BLK
a[8, 1] = BLK
a[7, 12] = YEL
a[8, 12] = YEL
cat68 = a

put(0x68, cat68)
put(0x69, cat69)
put(0x6A, cat6a)
put(0x6B, np.fliplr(cat68))
put(0x6C, np.rot90(cat68, -1))        # W-facing turned clockwise: head at the top
put(0x6D, np.rot90(cat69, -1))
put(0x6E, np.rot90(cat6a, -1))
put(0x6F, np.rot90(cat68, 1))         # head at the bottom


# ------------------------------------------------------------------ bugs 70..73

def legs6(a, xs, col, spread=3):
    for (x0, y0, x1, y1) in xs:
        line(a, x0, y0, x1, y1, col)
        line(a, 15 - x0, y0, 15 - x1, y1, col)


# 70 pill bug (woodlouse), grey bands
a = ground(700)
X, Y = grid(16, 16)
m = ((X - 8) / 4.6) ** 2 + ((Y - 8.6) / 6.0) ** 2 <= 1
legs6(a, [(4, 6, 2, 5), (3, 9, 1, 9), (4, 12, 2, 13)], DGY)
line(a, 6, 3, 4, 1, BLK)
line(a, 9, 3, 11, 1, BLK)
paint_blob(a, m, MGR, LGR, DGY, BLK, cast=BRN)
inner = erode8(m)
for y in (4, 6, 8, 10, 12):
    a[y][inner[y]] = DGY
    a[y + 1][inner[y + 1] & (X[y + 1] < 8)] = LGR
a[3][m[3]] = DGY
a[3, 7] = BLK
a[3, 8] = BLK
put(0x70, a)

# 71 ground beetle, violet with a blue sheen
a = ground(710)
el = ((X - 8) / 4.0) ** 2 + ((Y - 10.2) / 4.6) ** 2 <= 1
pn = ((X - 8) / 3.0) ** 2 + ((Y - 4.8) / 1.9) ** 2 <= 1
hdm = ((X - 8) / 1.8) ** 2 + ((Y - 2.4) / 1.3) ** 2 <= 1
legs6(a, [(5, 5, 2, 3), (5, 8, 1, 9), (5, 11, 2, 14)], BLK)
line(a, 7, 1, 6, 0, BLK)
line(a, 8, 1, 9, 0, BLK)
mm = el | pn | hdm
a[shift(mm, 1, 1) & ~mm] = BRN
a[mm] = PUR
a[hdm] = BLK
inner = erode8(el)
a[inner & ~shift(inner, 1, 1)] = BLU
a[el & (np.abs(X - 8) < 0.6)] = BLK
a[mm & ~erode8(mm)] = BLK
a[8, 5] = CYA
a[4, 6] = BLU
put(0x71, a)

# 72 spotted beetle, orange with black spots
a = ground(720)
bd = ((X - 8) / 5.0) ** 2 + ((Y - 9.2) / 5.1) ** 2 <= 1
hdm = ((X - 8) / 3.0) ** 2 + ((Y - 4.2) / 1.8) ** 2 <= 1
legs6(a, [(4, 7, 2, 5), (3, 10, 1, 10), (4, 13, 2, 14)], BLK)
paint_blob(a, bd, ORA, YEL, RED, BLK, cast=BRN)
a[hdm & (Y > 2.5)] = BLK
a[bd & (np.abs(X - 8) < 0.6) & (Y > 5)] = BLK
for (x, y) in ((5, 8), (10, 8), (5, 12), (10, 12), (7, 10)):
    a[y, x] = BLK
    a[y, x + 1] = BLK if x != 7 else a[y, x + 1]
a[3, 6] = WHT
a[3, 9] = WHT
put(0x72, a)

# 73 shield bug, green
a = ground(730)
sh = (Y > 3.5) & (Y < 14.5) & (np.abs(X - 8) < np.where(Y < 8, 5.2, 5.2 - (Y - 8) * 0.75))
hdm = ((X - 8) / 1.6) ** 2 + ((Y - 2.8) / 1.4) ** 2 <= 1
legs6(a, [(4, 6, 2, 4), (4, 9, 1, 10), (5, 12, 3, 14)], DGN)
line(a, 7, 2, 5, 0, DGN)
line(a, 8, 2, 10, 0, DGN)
paint_blob(a, sh | hdm, GRN, GRN, DGN, BLK, cast=BRN)
tri = sh & (Y > 5) & (Y < 10) & (np.abs(X - 8) < (10 - Y) * 0.6)
a[tri & erode8(sh)] = DGN
a[5, 5] = WHT
a[11][erode8(sh)[11] & (bayer(16, 16)[11] < 0.5)] = DGN
put(0x73, a)

# ------------------------------------------------------------------ raindrop 74..77
X, Y = grid(16, 16)
d = np.hypot(X - 8, Y - 8.5)
th = np.arctan2(Y - 8.5, X - 8)
b = bayer(16, 16)

a = ground(740)
wet = d < 5.5 + 0.8 * np.sin(5 * th)
a[wet & (b < 0.6)] = BRN
pool = d < 3.0
a[pool] = BLU
a[(d < 3.0) & (d > 2.0)] = CYA
a[7, 6] = WHT
a[7, 7] = WHT
for (x, y) in ((2, 4), (13, 3), (14, 10), (3, 12), (8, 1), (11, 14)):
    a[y, x] = CYA
    plot(a, x + 1, y, BLU)
    plot(a, x, y + 1, BLU)
for (x, y) in ((4, 2), (12, 6), (1, 8)):
    a[y, x] = WHT
put(0x74, a)

a = ground(741)
wet = d < 5.8 + 0.9 * np.sin(3 * th + 1) + 0.5 * np.sin(5 * th)
a[wet] = BRN
a[wet & (b < 0.12)] = TAN
a[wet & ~erode8(wet) & (b < 0.5)] = TAN
pool = ((X - 8.4) / 3.0) ** 2 + ((Y - 8.8) / 2.2) ** 2 <= 1
a[pool] = BLU
a[pool & ~shift(pool, 1, 1)] = CYA
a[8, 7] = WHT
put(0x75, a)

a = ground(742)
wet = d < 4.8 + 0.8 * np.sin(3 * th + 2) + 0.4 * np.sin(5 * th + 1)
a[wet & (b < 0.75)] = BRN
a[(d < 1.6) & (b < 0.4)] = DGY
a[8, 8] = CYA
put(0x76, a)

a = ground(743)
wet = d < 3.8 + 0.7 * np.sin(3 * th + 0.4)
a[wet & (b < 0.38)] = BRN
put(0x77, a)

# ------------------------------------------------------------------ scent overlay F1..FF
for k in range(1, 16):
    a = np.full((16, 16), TAN, dtype=np.int16)
    a[bayer(16, 16) < k / 16.0] = MAG
    put(0xF0 + k, a)

# ------------------------------------------------------------------ nests: tunnels 90..97
for i in range(8):
    a = tunnel(900 + i)
    r = random.Random(950 + i)
    if i in (2, 5):                                    # a loose crumb of soil on the floor
        x, y = r.randint(3, 11), r.randint(4, 11)
        a[y, x:x + 2] = BRN
        a[y + 1, x:x + 2] = MGR
        a[y, x] = TAN
    if i == 6:                                         # a root hair hanging through
        polyline(a, [(4, 3), (6, 5), (6, 8), (8, 10)], BRN)
    assert not np.isin(a, (BLK, DGY)).any(), hex(0x90 + i)   # never dark: black-colony ants must show
    put(0x90 + i, a)

# stored food A0..A3
FOOD = [[(8.0, 12.2, 2.8)], [(5.5, 12.4, 2.9), (11.0, 12.8, 2.4)],
        [(5.0, 12.0, 3.3), (11.2, 12.4, 3.0), (8.2, 8.6, 2.6)],
        [(4.4, 11.6, 3.6), (11.6, 11.6, 3.6), (8.0, 7.4, 3.4), (2.2, 14.0, 1.6), (14.0, 14.0, 1.6)]]
for i, cr in enumerate(FOOD):
    a = tunnel(1000 + i)
    for j, (cx, cy, rad) in enumerate(cr):
        crumb(a, cx, cy, rad, 1010 + 7 * i + j, outline=BLK, cast=BLK)
    put(0xA0 + i, a)

# A4 hole into the other colony's nest
a = tunnel(1040)
X, Y = grid(16, 16)
ring = ((X - 8) / 6.4) ** 2 + ((Y - 8.2) / 6.8) ** 2 <= 1
hole = ((X - 8) / 4.4) ** 2 + ((Y - 8.6) / 4.9) ** 2 <= 1
a[ring] = ramp(0.62 - 0.25 * np.clip(-(X - 8 + Y - 8) / 6, -1, 1), bayer(16, 16))[ring]
a[ring & ~erode8(ring)] = BLK
a[hole] = BLK
a[hole & (Y > 10) & (bayer(16, 16) < 0.3)] = RED
a[hole & (Y > 12) & (bayer(16, 16) < 0.55)] = RED
a[hole & ~erode8(hole) & (Y < 8)] = DGY
put(0xA4, a)


# ------------------------------------------------------------------ surface strip AC..AF, shaft A8, plugs
def strip(seed, extra=None):
    r = random.Random(seed)
    a = np.full((16, 16), CYA, dtype=np.int16)
    b = bayer(16, 16)
    a[6:10][b[6:10] < 0.12] = WHT                      # haze near the horizon
    a[11:16] = soil_tex(seed + 1)[11:16]
    a[11][(b[11] < 0.5)] = DGY                         # dark topsoil line
    a[10, :] = DGN
    for x in range(16):
        h = r.choice([2, 3, 3, 4, 4, 5, 6])
        c = GRN if (x + r.randint(0, 1)) % 2 else DGN
        lean = r.choice([-1, 0, 0, 1])
        for k in range(h):
            xx = x + (lean if k >= h - 2 else 0)
            if 0 <= xx < 16:
                a[10 - k, xx] = c
    if extra == 'cloud':
        for (x0, x1, y) in ((4, 9, 2), (3, 11, 3), (5, 10, 1)):
            a[y, x0:x1] = WHT
        a[3, 10] = LGR
        a[3, 9] = LGR
    if extra == 'flower':
        x = 11
        for k in range(5):
            a[9 - k, x] = GRN
        for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            a[4 + dy, x + dx] = WHT
        a[4, x] = ORA
    if extra == 'pebble':
        a[9, 4:7] = MGR
        a[8, 5] = LGR
        a[8, 4] = MGR
        a[9, 6] = DGY
    return a


put(0xAC, strip(1100))
put(0xAD, strip(1110, 'cloud'))
put(0xAE, strip(1120, 'flower'))
put(0xAF, strip(1130, 'pebble'))


def shaft(seed):
    a = strip(seed)
    t = tunnel(seed + 5)
    X, Y = grid(16, 16)
    half = np.where(Y < 10, 0, 3.0 + np.clip(12.5 - Y, 0, 3) * 0.9)
    hole = (np.abs(X - 8) < half) & (Y > 9)
    # dug-out soil heaped on both sides at grass level
    heap = ((((X - 3.2) / 3.4) ** 2 + ((Y - 10.6) / 2.4) ** 2 <= 1) |
            (((X - 12.8) / 3.4) ** 2 + ((Y - 10.6) / 2.4) ** 2 <= 1)) & (Y < 11.5)
    a[heap] = ramp(0.55 - 0.3 * np.sign(X - 8) * 0 + 0.15 * np.where(X < 8, 1, -1) +
                   (bayer(16, 16) - 0.5) * 0.4, bayer(16, 16))[heap]
    a[hole] = t[hole]
    rim = shift(hole, 1, 0) | shift(hole, -1, 0)
    rim &= ~hole & (Y > 9)
    a[rim] = BLK
    a[shift(hole, 2, 0) & ~hole & ~rim & (Y > 10)] = TAN
    a[heap & ~erode8(heap) & (Y < 10)] = BRN
    return a, hole


A8, _shaft_hole = shaft(1150)
put(0xA8, A8)
a, hole = shaft(1150)
X, Y = grid(16, 16)
pb = ((X - 8) / 4.3) ** 2 + ((Y - 12.8) / 3.0) ** 2 <= 1
paint_blob(a, pb, MGR, LGR, DGY, BLK)
a[11, 6] = WHT
put(0xC1, a)

# C0 pebble plugging a tunnel
a = tunnel(1200)
th = np.arctan2(Y - 8.4, X - 8)
pb = ((X - 8) / (6.6 * (1 + 0.05 * np.sin(3 * th + 1)))) ** 2 + ((Y - 8.4) / 6.4) ** 2 <= 1
paint_blob(a, pb, MGR, LGR, DGY, BLK, cast=BLK)
r = random.Random(1201)
for _ in range(7):
    x, y = r.randint(4, 11), r.randint(5, 11)
    if erode8(erode8(pb))[y, x]:
        a[y, x] = r.choice([LGR, DGY])
a[4, 5] = WHT
a[4, 6] = WHT
a[5, 4] = WHT
put(0xC0, a)

# ------------------------------------------------------------------ packed soil B0..BE and flooded DF..ED
SOIL = dict(R=6, base=BRN, light=TAN, dark=DGY, outline=BLK, specks=[(TAN, 0.09), (DGY, 0.06), (BLK, 0.02)])
WETSOIL = dict(R=6, base=BRN, light=TAN, dark=DGY, outline=BLK,
               specks=[(TAN, 0.06), (DGY, 0.08), (BLK, 0.03), (BLU, 0.04)])


def soil_nb(mask):
    N, E, S, W = bool(mask & 1), bool(mask & 2), bool(mask & 4), bool(mask & 8)
    return [[N and W, N, N and E], [W, True, E], [S and W, S, S and E]]


for mask in range(1, 16):
    a, _ = solid_tile(soil_nb(mask), SOIL, 1300 + mask, tunnel(1330 + mask))
    put(0xAF + mask, a)
    a, mc = solid_tile(soil_nb(mask), WETSOIL, 1360 + mask, water(1390 + mask))
    # the soil's edge facing the water glints cyan
    put(0xDE + mask, a)

put(0xDE, water(1420))
a = water(1421)
for (x, y) in ((4, 11), (10, 6)):                      # rising bubbles
    a[y, x] = WHT
    a[y - 3, x + 1] = CYA
    a[y - 5, x] = WHT
put(0xEE, a)
a = water(1422)
a[12, 3:6] = BRN                                       # a drowned crumb of soil drifting
a[13, 4:6] = BLK
put(0xEF, a)

# ------------------------------------------------------------------ numbered placeholders
FONT = {
    '0': ["111", "101", "101", "101", "111"], '1': ["010", "110", "010", "010", "111"],
    '2': ["111", "001", "111", "100", "111"], '3': ["111", "001", "111", "001", "111"],
    '4': ["101", "101", "111", "001", "001"], '5': ["111", "100", "111", "001", "111"],
    '6': ["111", "100", "111", "101", "111"], '7': ["111", "001", "010", "010", "010"],
    '8': ["111", "101", "111", "101", "111"], '9': ["111", "101", "111", "001", "111"],
    'A': ["010", "101", "111", "101", "101"], 'B': ["110", "101", "110", "101", "110"],
    'C': ["011", "100", "100", "100", "011"], 'D': ["110", "101", "101", "101", "110"],
    'E': ["111", "100", "110", "100", "111"], 'F': ["111", "100", "110", "100", "100"],
}


def placeholder(n):
    a = np.full((16, 16), TAN, dtype=np.int16)
    s = '%02X' % n
    for k, ch in enumerate(s):
        x0 = 1 + k * 8
        for j, row in enumerate(FONT[ch]):
            for i, bit in enumerate(row):
                if bit == '1':
                    a[3 + 2 * j:5 + 2 * j, x0 + 2 * i:x0 + 2 * i + 2] = BLK
    return a


PLACEHOLDERS = [n for n in range(256) if n not in tiles]
EXPECTED = (list(range(0x29, 0x30)) + list(range(0x40, 0x48)) + list(range(0x4C, 0x50)) + [0x52, 0x53] +
            list(range(0x78, 0x90)) + list(range(0x98, 0xA0)) + list(range(0xA5, 0xA8)) +
            list(range(0xA9, 0xAC)) + [0xBF] + list(range(0xC2, 0xDE)) + [0xF0])
assert sorted(PLACEHOLDERS) == sorted(EXPECTED), sorted(set(PLACEHOLDERS) ^ set(EXPECTED))
for n in PLACEHOLDERS:
    put(n, placeholder(n))

# ------------------------------------------------------------------ assemble and write
sheet = np.zeros((256, 256), dtype=np.int16)
for n, t in tiles.items():
    sheet[(n // 16) * 16:(n // 16) * 16 + 16, (n % 16) * 16:(n % 16) * 16 + 16] = t

lines = [
    "# yard.pix - clean-pack yard tile sheet: 256 x 256 px, 16 x 16 tiles of 16 x 16 px.",
    "# Tile n at column n % 16, row n / 16. One hex digit per pixel = standard Mac 16-colour palette index.",
    "# Generated by make_yard.py (procedural, seeded); do not edit by hand.",
]
lines += [''.join('%x' % v for v in row) for row in sheet]
with open(os.path.join(HERE, 'yard.pix'), 'w', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')

PAL = np.array(PALETTE, dtype=np.uint8)


def to_img(arr, scale):
    img = Image.fromarray(PAL[arr])
    return img.resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.NEAREST)


# preview: 3x, grid, row / column numbers
S, ML, MT = 48, 30, 18
prev = Image.new('RGB', (ML + 16 * (S + 1) + 1, MT + 16 * (S + 1) + 1), (40, 40, 48))
dr = ImageDraw.Draw(prev)
for n in range(256):
    r_, c_ = n // 16, n % 16
    prev.paste(to_img(tiles[n], 3), (ML + 1 + c_ * (S + 1), MT + 1 + r_ * (S + 1)))
for i in range(16):
    dr.text((ML + 1 + i * (S + 1) + S // 2 - 3, 3), '%X' % i, fill=(230, 230, 230))
    dr.text((4, MT + 1 + i * (S + 1) + S // 2 - 6), '%X0' % i, fill=(230, 230, 230))
prev.save(os.path.join(HERE, 'preview.png'))

# ------------------------------------------------------------------ mock-up
rng = random.Random(2024)
W_, H_ = 28, 16
surf = [[rng.randint(0, 15) for _ in range(W_)] for _ in range(H_)]
used = set()


def place(x, y, rows):
    for j, row in enumerate(rows):
        for i, t in enumerate(row):
            if t is None:
                continue
            assert (x + i, y + j) not in used, (x + i, y + j)
            used.add((x + i, y + j))
            surf[y + j][x + i] = t


place(2, 2, [[0x18, 0x19, 0x1A], [0x1B, 0x50, 0x1C], [0x1D, 0x1E, 0x1F]])
place(7, 1, [[0x20, 0x21], [0x22, 0x23]])
place(10, 3, [[0x24, 0x25]])
place(2, 7, [[0x26, 0x27]])
for p in ((6, 5), (13, 6), (25, 14), (1, 12), (21, 7)):
    place(*p, [[0x28]])
place(9, 6, [[0x4B, 0x4A]])
place(10, 7, [[0x49]])
place(12, 5, [[0x48]])
place(6, 9, [[0x51]])
place(20, 9, [[0x51]])
place(14, 1, [[None, 0x5B, 0x54, 0x55, None], [0x5B, 0x5C, 0x5C, 0x56, None], [0x5A, 0x5C, 0x5C, 0x5E, 0x55],
              [0x59, 0x5D, 0x5C, 0x5C, 0x56], [None, 0x59, 0x58, 0x58, 0x57]])
place(21, 1, [[0x5B, 0x54, 0x54, 0x54, 0x55], [0x59, 0x5D, 0x5C, 0x5F, 0x57], [None, 0x5A, 0x5C, 0x56, None],
              [0x5B, 0x5C, 0x5F, 0x57, None], [0x59, 0x58, 0x57, None, None]])
place(1, 13, [[0x5B, 0x54, 0x55], [0x59, 0x58, 0x57]])
place(25, 9, [[0x5B, 0x55, None], [0x59, 0x5E, 0x55], [None, 0x59, 0x57]])
place(7, 11, [[0x30, 0x31, 0x32], [0x33, 0x38, 0x34], [0x35, 0x36, 0x37]])
place(13, 8, [[0x65, 0x60, 0x60, 0x60, 0x67]])
place(17, 9, [[0x61], [0x61], [0x64]])
place(11, 10, [[0x62], [0x61], [0x66, 0x60, 0x63]])
place(12, 14, [[0x68, 0x69, 0x6A, 0x69]])
place(23, 11, [[0x6C], [0x6D], [0x6E], [0x6D]])
place(4, 10, [[0x70]])
place(20, 13, [[0x71]])
place(15, 12, [[0x72]])
place(10, 15, [[0x73]])
place(19, 6, [[0x74]])
place(5, 0, [[0x75]])
place(1, 5, [[0x76]])
place(26, 6, [[0x77]])
for i, p in enumerate(((5, 7), (12, 3), (8, 5), (3, 11), (17, 13), (19, 15), (27, 15), (0, 9))):
    place(*p, [[0x10 + i]])

A = np.zeros((H_ * 16, W_ * 16), dtype=np.int16)
for j in range(H_):
    for i in range(W_):
        A[j * 16:j * 16 + 16, i * 16:i * 16 + 16] = tiles[surf[j][i]]
# stand-in live ants (mock-up only, to check contrast; ants are not part of this sheet)
for (cx, cy, ang, body, hi, leg) in ((40, 120, 0.3, BLK, DGY, BLK), (60, 128, 2.6, BLK, DGY, BLK),
                                     (150, 104, 1.2, RED, ORA, BRN), (170, 90, 4.0, RED, ORA, BRN),
                                     (100, 230, 5.5, YEL, WHT, BRN), (330, 200, 0.9, YEL, WHT, BRN),
                                     (124, 26, 0.5, BLK, DGY, BLK), (300, 40, 3.3, RED, ORA, BRN)):
    sub = A[cy - 8:cy + 8, cx - 8:cx + 8]
    ant(sub, 8, 8, ang, body, hi, leg, dead=False)

NEST = [
    "####.################.######",
    "####.################.######",
    "##.......f##########.....###",
    "##.####.############.###.###",
    "#....##.##########.....h.###",
    "#.ff.##...p...####.##...####",
    "#....######.#####~~~~~######",
    "###########~~~~~~~~~~~~#####",
]
NW, NH = len(NEST[0]), len(NEST) + 1
assert all(len(r_) == NW for r_ in NEST)
nest = [[None] * NW for _ in range(NH)]
for i in range(NW):
    nest[0][i] = rng.choice([0xAC, 0xAC, 0xAD, 0xAE, 0xAF])
nest[0][4] = 0xA8
nest[0][21] = 0xC1


def is_open(i, j):
    if j <= 0 or j >= NH or i < 0 or i >= NW:
        return False
    return NEST[j - 1][i] != '#'


def is_flood(i, j):
    return 0 < j < NH and 0 <= i < NW and NEST[j - 1][i] == '~'


for j in range(1, NH):
    for i in range(NW):
        ch = NEST[j - 1][i]
        if ch == '#':
            mask = (0 if is_open(i, j - 1) else 1) | (0 if is_open(i + 1, j) else 2) | \
                   (0 if is_open(i, j + 1) else 4) | (0 if is_open(i - 1, j) else 8)
            assert mask, (i, j)
            opens = [(i, j - 1), (i + 1, j), (i, j + 1), (i - 1, j)]
            fl = [is_flood(*p) for p in opens if is_open(*p)]
            nest[j][i] = (0xDE if (fl and all(fl)) else 0xAF) + mask
        elif ch == '.':
            nest[j][i] = 0x90 + rng.randint(0, 7)
        elif ch == 'f':
            nest[j][i] = 0xA0 + rng.randint(0, 3)
        elif ch == 'h':
            nest[j][i] = 0xA4
        elif ch == 'p':
            nest[j][i] = 0xC0
        elif ch == '~':
            nest[j][i] = rng.choice([0xDE, 0xDE, 0xEE, 0xEF])
nest[6][2], nest[6][3] = 0xA2, 0xA3
B = np.zeros((NH * 16, NW * 16), dtype=np.int16)
for j in range(NH):
    for i in range(NW):
        B[j * 16:j * 16 + 16, i * 16:i * 16 + 16] = tiles[nest[j][i]]
for (cx, cy, ang, body, hi, leg) in ((90, 56, 0.0, BLK, DGY, BLK), (72, 88, 1.57, YEL, WHT, BRN),
                                     (130, 90, 3.14, RED, ORA, BRN), (350, 72, 0.2, BLK, DGY, BLK)):
    sub = B[cy - 8:cy + 8, cx - 8:cx + 8]
    ant(sub, 8, 8, ang, body, hi, leg, dead=False)

gap = 8
full = np.full((A.shape[0] + gap + B.shape[0], A.shape[1]), DGY, dtype=np.int16)
full[:A.shape[0]] = A
full[A.shape[0] + gap:] = B
to_img(full, 2).save(os.path.join(HERE, 'mockup.png'))
print('wrote yard.pix, preview.png, mockup.png;', len(PLACEHOLDERS), 'placeholders')
