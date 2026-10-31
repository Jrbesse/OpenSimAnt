#!/usr/bin/env python3
"""make_house.py - draws the clean-pack house tile sheet procedurally.

Writes, next to this script:
  house.pix           the 256 x 256 sheet (16 x 16 tiles of 16 x 16 px), one hex digit per pixel
  preview_house.png   the sheet at 3x with a grid and row / column numbers
  mockup_house.png    every multi-tile assembly of the spec put together from the tiles (enlarged)

Deterministic: every random choice is seeded. Run: python make_house.py
The helpers marked "from make_yard.py" are copies (that script writes files when imported).
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
STRUCT = {}      # n -> mask of the pixels that are drawn structure (not the floor / face texture beneath)


def reg(n, builder, face, outside=None):
    """put() a tile made by builder(face, outside) and remember which of its pixels are structure."""
    outside = face if outside is None else outside
    put(n, builder(face, outside))
    c1, c2 = np.full((16, 16), 1), np.full((16, 16), 2)
    STRUCT[n] = builder(c1, c1) == builder(c2, c2)


def put(n, a):
    a = np.asarray(a)
    assert a.shape == (16, 16), (hex(n), a.shape)
    assert a.min() >= 0 and a.max() <= 15, hex(n)
    assert n not in tiles, hex(n)
    tiles[n] = a.astype(np.int16).copy()


# ------------------------------------------------------------------ helpers (from make_yard.py)

def grid(h, w):
    Y, X = np.mgrid[0:h, 0:w]
    return X + 0.5, Y + 0.5


def bayer(h, w):
    Y, X = np.mgrid[0:h, 0:w]
    return (BAYER4[Y % 4, X % 4] + 0.5) / 16.0


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


def crumb(a, cx, cy, rad, seed, bites=(), outline=DGY, cast=BRN):
    """A food morsel: white, lit top-left, orange crust bottom-right (the yard sheet's look)."""
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


def ant(a, cx, cy, ang, body, hi, leg, flip=False):
    """A small dead ant: legs curled in."""
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    s = -1 if flip else 1
    X, Y = grid(*a.shape)
    u = (X - cx) * ux + (Y - cy) * uy
    v = ((X - cx) * vx + (Y - cy) * vy) * s
    k = 1.0
    gaster = ((u + 2.9 * k) / (2.6 * k)) ** 2 + (v / (2.0 * k)) ** 2 <= 1
    thorax = ((u - 0.4 * k) / (1.5 * k)) ** 2 + (v / (1.0 * k)) ** 2 <= 1
    head = ((u - 2.8 * k) / (1.4 * k)) ** 2 + (v / (1.3 * k)) ** 2 <= 1

    def P(uu, vv):
        vv *= s
        return (cx + uu * ux + vv * vx - 0.5, cy + uu * uy + vv * vy - 0.5)

    legs = [[(0.0, 0), (-0.8, 2.3), (0.2, 2.9)], [(0.5, 0), (0.9, 2.5), (1.8, 2.4)],
            [(1.0, 0), (2.2, 1.9), (2.6, 1.0)]]
    ants_ = [[(3.8, 0.4), (4.8, 1.2), (4.4, 2.0)]]
    for side in (1, -1):
        for lg in legs + ants_:
            polyline(a, [P(uu, vv * side) for uu, vv in lg], leg)
    m = gaster | thorax | head
    a[m] = body
    for hu, hv in ((-3.6 * k, -0.8 * k), (2.6 * k, -0.5 * k)):
        x, y = P(hu, hv)
        plot(a, x, y, hi)
    return m


# ------------------------------------------------------------------ the flat floors
# Every floor is a plain 16 x 16 tile used everywhere with no variants, so each is built from an 8 x 8
# cell repeated 2 x 2: no tile boundary shows, and edge columns / rows continue exactly.

def cd(a, b, period=8):
    d = abs(a - b) % period
    return min(d, period - d)


def scatter(seed, counts, period=8):
    """Non-touching (also across the wrap) marks: [(x, y, colour)]."""
    r = random.Random(seed)
    taken, out = [], []
    for c, n in counts:
        for _ in range(n):
            while True:
                x, y = r.randrange(period), r.randrange(period)
                if all(not (cd(x, tx) <= 1 and cd(y, ty) <= 1) for tx, ty in taken):
                    break
            taken.append((x, y))
            out.append((x, y, c))
    return out


def tile_cell(cell):
    return np.tile(cell, (2, 2)).astype(np.int16)


def cell_with(base, marks, hatch=None):
    cell = np.full((8, 8), base, dtype=np.int16)
    if hatch:
        hc, fn = hatch
        for y in range(8):
            for x in range(8):
                if fn(x, y):
                    cell[y, x] = hc
    for x, y, c in marks:
        if hatch is None or cell[y, x] == base:
            cell[y, x] = c
    return cell


# floor 0: a hard kitchen floor, tan with brown and light flecks
FLOOR0 = tile_cell(cell_with(TAN, scatter(1, [(BRN, 5), (LGR, 3)])))
# floor 1: a pale glazed tile, light grey with white flecks
FLOOR1 = tile_cell(cell_with(LGR, scatter(2, [(WHT, 5), (MGR, 1)])))
# floor 3: the carpet, mid grey with a fine pile of dark and light fibres
FLOOR3 = tile_cell(cell_with(MGR, scatter(3, [(DGY, 3), (LGR, 3)])))


def make_floor2():
    """The rug: the carpet's grey with a warm weave: a diagonal tan thread every 4th pixel, a few light threads."""
    cell = cell_with(MGR, [], hatch=(TAN, lambda x, y: (x + y) % 4 == 0))
    for x, y, c in scatter(4, [(LGR, 2), (BRN, 1)]):
        if cell[y, x] == MGR:
            cell[y, x] = c
    return tile_cell(cell)


FLOOR2 = make_floor2()
# the wall: near white with faint light-grey dots
WALL = tile_cell(cell_with(WHT, scatter(5, [(LGR, 4)])))
# the counter's face: glazed cyan, an occasional white glint
COUNTER = tile_cell(cell_with(CYA, scatter(6, [(WHT, 2)])))


def basin_tex(lo, hi):
    a = np.full((16, 16), lo, dtype=np.int16)
    a[BAYER4[np.mgrid[0:16, 0:16][0] % 4, np.mgrid[0:16, 0:16][1] % 4] < 4] = hi
    return a


BASIN_LIT = basin_tex(LGR, MGR)       # 0xC1: a little darker than floor 1
BASIN_SHADE = basin_tex(MGR, DGY)     # 0xC2: darker
METAL = tile_cell(cell_with(MGR, scatter(7, [(LGR, 3)])))   # the taps' flat face (0x4E)

# table leg: dark wood grain seen from above (period 4, seamless in every direction)
_Y, _X = np.mgrid[0:16, 0:16]
LEG = np.where(BAYER4[_Y % 4, _X % 4] < 6, BLK, DGY).astype(np.int16)
LEG[(_X % 8 == 3) & (_Y % 8 == 2)] = BRN

# ------------------------------------------------------------------ floors 0x00..0x07
put(0x00, FLOOR0)
put(0x01, FLOOR1)
put(0x02, FLOOR2)
put(0x03, FLOOR3)
for n in (0x04, 0x05, 0x06, 0x07):          # stray ground values: a plain copy of the carpet
    put(n, FLOOR3)

FLOORS = [FLOOR0, FLOOR1, FLOOR2, FLOOR3]

# ------------------------------------------------------------------ dead ants 0x08..0x17
DEAD = [(8.2, 8.0, 0.35, False), (8.0, 8.4, 1.9, True), (7.8, 7.6, 3.6, False), (8.3, 8.2, 5.1, True)]
for f in range(4):
    for i in range(2):                       # black ant, two poses
        a = FLOORS[f].copy()
        cx, cy, ang, fl = DEAD[i + 2 * (f % 2)]
        ant(a, cx, cy, ang, BLK, DGY, BLK, flip=fl)
        put(0x08 + 4 * f + i, a)
    for i in range(2):                       # red ant, two poses
        a = FLOORS[f].copy()
        cx, cy, ang, fl = DEAD[i + 1 + (f % 2)]
        ant(a, cx, cy, ang + 0.6, RED, ORA, BRN, flip=not fl)
        put(0x0A + 4 * f + i, a)

# ------------------------------------------------------------------ food crumb piles 0x18..0x27
PILES = [
    [(8.0, 8.0, 3.5)],
    [(5.2, 10.4, 3.5), (10.8, 5.4, 3.2)],
    [(4.4, 4.8, 3.1), (11.4, 6.2, 3.3), (7.6, 11.6, 3.4)],
    [(4.4, 4.6, 3.3), (11.6, 4.4, 3.4), (4.6, 11.4, 3.3), (11.4, 11.6, 3.4)],
]
CAST = [BRN, MGR, DGY, DGY]
for f in range(4):
    for k, pile in enumerate(PILES):
        a = FLOORS[f].copy()
        for j, (cx, cy, rad) in enumerate(pile):
            crumb(a, cx, cy, rad, 100 + 10 * f + 3 * k + j, outline=BLK, cast=CAST[f])
        put(0x18 + 4 * f + k, a)

# ------------------------------------------------------------------ the coin 0x28..0x30 (3 x 3, on the rug)


def rug_patch(cols, rows):
    return np.tile(FLOOR2, (rows, cols))


def coin_patch():
    A = rug_patch(3, 3)
    X, Y = grid(48, 48)
    dx, dy = X - 24, Y - 24
    d, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    light = -(dx + dy) / (math.sqrt(2) * np.maximum(d, 0.5))
    R = 19.6
    m = d <= R
    A[shift(m, 2, 2) & ~m] = DGY                     # cast shadow
    A[shift(m, 1, 1) & ~m & ~shift(m, 2, 2)] = DGY
    A[m] = LGR
    b = bayer(48, 48)
    # reeded rim: alternating ticks
    rim = (d > 16.4) & m
    tick = (np.floor((th + math.pi) / (2 * math.pi) * 72) % 2) == 0
    A[rim] = LGR
    A[rim & tick] = MGR
    A[rim & (light > 0.35) & tick] = LGR
    A[rim & (light > 0.35) & ~tick] = WHT
    A[rim & (light < -0.35) & ~tick] = MGR
    A[rim & (light < -0.35) & tick] = DGY
    groove = (d > 14.6) & (d <= 16.4)
    A[groove] = MGR
    A[groove & (light > 0) & (b < 0.5)] = DGY
    A[groove & (light < 0)] = LGR
    # the field: a gentle dish, lighter at the top-left
    field = d <= 14.6
    s = 0.5 + 0.35 * light * (d / 14.6)
    A[field] = np.where(b[field] < np.clip(s[field], 0, 1) - 0.1, WHT, LGR)
    A[field & (b < 0.12) & (s < 0.35)] = MGR
    # a raised star in the middle
    pts = []
    for i in range(10):
        rad = 10.5 if i % 2 == 0 else 4.6
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append((24 + rad * math.cos(ang), 24.3 + rad * math.sin(ang)))
    st = Image.new('L', (48, 48), 0)
    ImageDraw.Draw(st).polygon(pts, fill=255)
    star = np.array(st) > 0
    A[shift(star, 1, 1) & ~star] = DGY
    A[star] = LGR
    inner = erode8(star)
    A[star & ~inner] = WHT
    A[star & ~shift(star, -1, -1) & star] = WHT
    A[star & ~shift(star, 1, 1)] = MGR
    A[(np.hypot(X - 24, Y - 24.3) < 1.6)] = DGY
    A[m & ~erode8(m)] = BLK                          # outline
    assert not (m | shift(m, 2, 2))[:2].any() and not (m | shift(m, 2, 2))[:, :2].any()
    assert not (m | shift(m, 2, 2))[-2:].any() and not (m | shift(m, 2, 2))[:, -2:].any()
    return A, m


COIN, COIN_MASK = coin_patch()
for k, n in enumerate(range(0x28, 0x31)):
    j, i = divmod(k, 3)
    put(n, COIN[j * 16:j * 16 + 16, i * 16:i * 16 + 16])

# ------------------------------------------------------------------ the paper clip 0x31..0x37


def clip_draw():
    A = rug_patch(3, 3)
    X, Y = grid(48, 48)
    ux, uy = math.sqrt(0.5), -math.sqrt(0.5)
    vx, vy = math.sqrt(0.5), math.sqrt(0.5)

    def uv(u, v):
        return (24 + u * ux + v * vx, 24 + u * uy + v * vy)

    def arc(cu, cv, r, a0, a1, n=30):
        return [uv(cu + r * math.cos(a0 + (a1 - a0) * t / n), cv + r * math.sin(a0 + (a1 - a0) * t / n))
                for t in range(n + 1)]

    # a gem clip: an outer and an inner racetrack of wire (u along the clip, v across); the outer one is
    # opened on one side and the inner one at its far end, so it reads as one bent wire
    segs = []
    segs.append([uv(-19, 5.4), uv(19, 5.4)])                               # outer, one long side
    segs.append(arc(19, 0.0, 5.4, math.pi / 2, -math.pi / 2))             # outer right end
    segs.append([uv(19, -5.4), uv(2, -5.4)])                               # outer, other side (opened)
    segs.append(arc(-19, 0.0, 5.4, math.pi / 2, 3 * math.pi / 2))         # outer left end
    segs.append([uv(-19, -5.4), uv(-8, -5.4)])
    segs.append([uv(-12, 2.2), uv(12, 2.2)])                               # inner racetrack
    segs.append(arc(12, 0.0, 2.2, math.pi / 2, -math.pi / 2))
    segs.append([uv(12, -2.2), uv(-14, -2.2)])
    wire = np.zeros((48, 48), bool)
    for path in segs:
        for p, q in zip(path, path[1:]):
            for t in np.linspace(0, 1, 40):
                x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
                wire |= np.hypot(X - x, Y - y) <= 0.95
    shadow = shift(wire, 1, 1) & ~wire
    A[shadow] = DGY
    A[wire] = LGR
    A[wire & ~shift(wire, -1, -1)] = WHT
    A[wire & ~shift(wire, 1, 1)] = MGR
    return A, wire


CLIP, CLIP_WIRE = clip_draw()
# nothing may touch the two cells that stay bare (top-left and bottom-right)
_touch = CLIP_WIRE | shift(CLIP_WIRE, 1, 1)
assert not _touch[0:16, 0:16].any(), 'clip enters the top-left cell'
assert not _touch[32:48, 32:48].any(), 'clip enters the bottom-right cell'
assert not _touch[0:2].any() and not _touch[-2:].any() and not _touch[:, :2].any() and not _touch[:, -2:].any()
for n, (j, i) in {0x31: (0, 1), 0x32: (0, 2), 0x33: (1, 0), 0x34: (1, 1), 0x35: (1, 2), 0x36: (2, 0), 0x37: (2, 1)}.items():
    put(n, CLIP[j * 16:j * 16 + 16, i * 16:i * 16 + 16])

# ------------------------------------------------------------------ litter on the rug 0x38..0x3C
a = FLOOR2.copy()                                           # 38: two crossing threads
for pts, c in (([(1, 11), (4, 7), (8, 8), (11, 4), (14, 6)], WHT), ([(2, 3), (5, 5), (8, 10), (11, 11), (14, 9)], LGR)):
    polyline(a, [(x + 1, y + 1) for x, y in pts], DGY)
for pts, c in (([(1, 11), (4, 7), (8, 8), (11, 4), (14, 6)], WHT), ([(2, 3), (5, 5), (8, 10), (11, 11), (14, 9)], LGR)):
    polyline(a, pts, c)
put(0x38, a)

a = FLOOR2.copy()                                           # 39: a long hair in a loose curl
hair = []
for t in np.linspace(0, 1, 40):
    hair.append((2 + 12 * t, 9 - 4 * math.sin(t * math.pi * 1.6) + 2.5 * t))
polyline(a, [(x + 1, y + 1) for x, y in hair], DGY)
polyline(a, hair, LGR)
for t in (0.18, 0.58):
    plot(a, *hair[int(t * 39)], WHT)
put(0x39, a)

a = FLOOR2.copy()                                           # 3A: a few crumbs of biscuit (tiny, no outline)
for (x, y, w, c) in ((4, 5, 2, TAN), (9, 4, 1, LGR), (7, 9, 2, TAN), (11, 10, 1, WHT), (3, 11, 1, LGR), (12, 6, 1, TAN)):
    a[y + 1, x:x + w] = DGY
    a[y, x:x + w] = c
put(0x3A, a)

a = FLOOR2.copy()                                           # 3B: a scrap of paper
sc = Image.new('L', (16, 16), 0)
ImageDraw.Draw(sc).polygon([(3.5, 4.5), (10.5, 3.0), (12.5, 9.0), (6.0, 11.5), (3.0, 8.5)], fill=255)
scrap = np.array(sc) > 0
a[shift(scrap, 1, 1) & ~scrap] = DGY
a[scrap] = WHT
a[scrap & ~shift(scrap, 1, 1)] = LGR
for (x0, x1, y) in ((5, 9, 6), (5, 10, 8)):
    a[y, x0:x1][scrap[y, x0:x1]] = MGR
put(0x3B, a)

a = FLOOR2.copy()                                           # 3C: a coiled thread
cx, cy = 7.5, 8.0
coil = []
for t in np.linspace(0, 1, 60):
    ang = t * 3.5 * math.pi
    r = 0.8 + 4.3 * t
    coil.append((cx + r * math.cos(ang), cy + 0.85 * r * math.sin(ang)))
polyline(a, [(x + 1, y + 1) for x, y in coil], DGY)
polyline(a, coil, LGR)
polyline(a, coil[::3], WHT)
put(0x3C, a)

# ------------------------------------------------------------------ specks on the carpet 0x3E, 0x3F
a = FLOOR3.copy()                                           # lint
for (x, y, c) in ((6, 7, LGR), (7, 7, WHT), (8, 7, LGR), (7, 6, WHT), (7, 8, LGR), (5, 8, LGR), (9, 8, WHT), (8, 6, LGR)):
    a[y, x] = c
a[9, 8] = DGY
a[9, 7] = DGY
put(0x3E, a)
a = FLOOR3.copy()                                           # dust
for (x, y, c) in ((3, 4, LGR), (10, 3, LGR), (7, 7, LGR), (12, 9, DGY), (4, 11, LGR), (9, 12, LGR), (13, 5, LGR), (2, 8, DGY)):
    a[y, x] = c
put(0x3F, a)

# ------------------------------------------------------------------ bevelled tiles (frames, buttons, socket bodies)
FACE1 = FLOOR1


def corner_mask(sides, R):
    Yi, Xi = np.mgrid[0:16, 0:16]
    xc, yc = Xi + 0.5, Yi + 0.5
    m = np.ones((16, 16), bool)
    if R > 0:
        for (s1, s2, cx, cy, region) in (('n', 'w', R, R, (xc < R) & (yc < R)),
                                         ('n', 'e', 16 - R, R, (xc > 16 - R) & (yc < R)),
                                         ('s', 'w', R, 16 - R, (xc < R) & (yc > 16 - R)),
                                         ('s', 'e', 16 - R, 16 - R, (xc > 16 - R) & (yc > 16 - R))):
            if s1 in sides and s2 in sides:
                m[region & ((xc - cx) ** 2 + (yc - cy) ** 2 > R * R)] = False
    return m


def side_depths(m, sides):
    """Distance of every inside pixel from the shape's boundary on each outer side."""
    INF = 99
    d = {}
    Yi, Xi = np.mgrid[0:16, 0:16]
    big = np.full((16, 16), INF, dtype=int)
    if 'n' in sides:
        first = np.array([np.argmax(m[:, x]) if m[:, x].any() else 0 for x in range(16)])
        d['n'] = np.where(m, Yi - first[Xi], INF)
    if 's' in sides:
        last = np.array([15 - np.argmax(m[::-1, x]) if m[:, x].any() else 15 for x in range(16)])
        d['s'] = np.where(m, last[Xi] - Yi, INF)
    if 'w' in sides:
        first = np.array([np.argmax(m[y, :]) if m[y, :].any() else 0 for y in range(16)])
        d['w'] = np.where(m, Xi - first[Yi], INF)
    if 'e' in sides:
        last = np.array([15 - np.argmax(m[y, ::-1]) if m[y, :].any() else 15 for y in range(16)])
        d['e'] = np.where(m, last[Yi] - Xi, INF)
    return d


def bevel_tile(sides, face, outside, R=0, lit='nw', bw=2, outline=BLK, hi=WHT, lo=DGY):
    """A raised, bevelled piece lit from the top-left. `sides` are the sides facing the outside (they get the
    outline and the bevel); the other sides continue into the neighbouring tile."""
    m = corner_mask(sides, R)
    d = side_depths(m, sides)
    a = face.copy()
    a[~m] = outside[~m]
    best = np.full((16, 16), 99)
    who = np.full((16, 16), '', dtype='<U1')
    for s in 'sewn':                                  # the shaded sides first, so they win a tie
        if s in d:
            better = d[s] < best
            best = np.where(better, d[s], best)
            who = np.where(better, s, who)
    for y in range(16):
        for x in range(16):
            if not m[y, x]:
                continue
            if best[y, x] == 0:
                a[y, x] = outline
            elif best[y, x] <= bw:
                a[y, x] = hi if who[y, x] in lit else lo
    return a


# raised frame: lit top-left (the rim of the sink unit, the plate of a socket)
RAISED = {0x53: 'nw', 0x54: 'n', 0x55: 'ne', 0x5A: 'w', 0x5B: 'e', 0x50: 'sw', 0x51: 's', 0x52: 'se'}
for n, sd in RAISED.items():
    reg(n, lambda f, o, sd=sd: bevel_tile(set(sd), f, o), FACE1)


def sunken_corner(kind, face):
    """The corner of a sunken frame: where the two walls' dark / lit bands meet (mitre rule: the wall whose
    band is deeper at that pixel wins; a tie takes the shaded wall)."""
    a = face.copy()
    for y in range(16):
        for x in range(16):
            if kind == 'TL':
                u, v, hl, vl = 15 - x, 15 - y, False, False
            elif kind == 'TR':
                u, v, hl, vl = x, 15 - y, False, True
            elif kind == 'BL':
                u, v, hl, vl = 15 - x, y, True, False
            else:
                u, v, hl, vl = x, y, True, True
            # v: depth in the horizontal wall (top / bottom wall), u: depth in the vertical wall
            if u > 2 or v > 2:
                continue
            dep = max(u, v)
            if dep == 0:
                a[y, x] = BLK
                continue
            if v > u:
                lit = hl
            elif u > v:
                lit = vl
            else:
                lit = hl and vl
            a[y, x] = WHT if lit else DGY
    return a


for n, kind in ((0x56, 'TL'), (0x58, 'TR'), (0x57, 'BL'), (0x59, 'BR')):
    reg(n, lambda f, o, kind=kind: sunken_corner(kind, f), FACE1)

# 0x63: the socket plate's face (the same pale surface as floor 1), 0x64 the wall
put(0x63, FLOOR1)
put(0x64, WALL)

# ------------------------------------------------------------------ the counter
CF = COUNTER
SEAM_V, SEAM_H = (7, 8), (7, 8)


def seam_tile(base, vert=None, horiz=None):
    """vert / horiz: None, or the extent of the seam: (first, last) index along its length."""
    a = base.copy()
    dark = np.zeros((16, 16), bool)
    light = np.zeros((16, 16), bool)
    if vert:
        dark[vert[0]:vert[1] + 1, 7] = True
        light[vert[0]:vert[1] + 1, 8] = True
    if horiz:
        dark[7, horiz[0]:horiz[1] + 1] = True
        light[8, horiz[0]:horiz[1] + 1] = True
    light &= ~dark
    a[dark] = DGY
    a[light] = WHT
    return a


put(0x62, CF)
for n, kw in ((0x66, dict(vert=(0, 15))), (0x68, dict(horiz=(0, 15))), (0x67, dict(vert=(0, 15), horiz=(0, 15))),
              (0x69, dict(vert=(0, 8), horiz=(0, 15)))):
    reg(n, lambda f, o, kw=kw: seam_tile(f, **kw), CF)
STRUCT[0x62] = np.zeros((16, 16), bool)

# ------------------------------------------------------------------ the skirting board 0x7A, 0x7B


def skirting(finish_left):
    a = np.full((16, 16), TAN, dtype=np.int16)
    r = random.Random(77)
    for x in range(2, 14):                              # vertical wood grain, wraps top to bottom
        if x in (5, 10):
            continue
        if r.random() < 0.45:
            continue
        y = r.randrange(16)
        n = r.randint(3, 5)
        for k in range(n):
            a[(y + k) % 16, x] = BRN
    a[:, 5] = BRN                                       # moulding grooves
    a[:, 10] = BRN
    a[:, 6] = LGR if False else TAN
    a[:, 4] = TAN
    a[:, 0] = BRN
    a[:, 15] = BRN
    a[:, 1] = TAN
    a[:, 14] = TAN
    if finish_left:
        a[:, 0] = BLK
    return a


put(0x7A, skirting(True))
put(0x7B, skirting(False))

# ------------------------------------------------------------------ socket parts
BODY_FACE = WALL
PLATE = FLOOR1
BODY = {0x6B: 'nw', 0x6C: 'n', 0x6D: 'ne', 0x71: 'w', 0x72: 'e', 0x6E: 'sw', 0x6F: 's', 0x70: 'se'}
for n, sd in BODY.items():
    reg(n, lambda f, o, sd=sd: bevel_tile(set(sd), f, o, R=6 if len(sd) == 2 else 0, hi=WHT, lo=MGR, outline=DGY),
        BODY_FACE, PLATE)

# slots: a stadium 26 x 10 across two tiles (horizontal) or down two tiles (upright)


def stadium(w, h, cx0, cx1, cy, r):
    X, Y = grid(h, w)                                 # a (h rows x w cols) mask: a capsule
    nearest = np.clip(X, cx0, cx1)
    return np.hypot(X - nearest, Y - cy) <= r


def slot_tiles(vertical, danger, bar=(10, 22)):
    """The two tiles (first, second) of one slot opening, drawn on the wall-white socket body."""
    m = stadium(32, 16, 7.5, 24.5, 8.0, 5.0)           # 16 rows x 32 cols, drawn horizontally
    ring = (shift(m, 1, 0) | shift(m, -1, 0) | shift(m, 0, 1) | shift(m, 0, -1)) & ~m
    cv = np.full((16, 32), -1, dtype=np.int16)
    cv[ring] = RED if danger else DGY
    cv[m] = BLK
    lip = m & ~shift(m, 1, 1)                          # depth: a grey lip inside, lower right
    cv[lip] = DGY
    if danger:
        cv[7, bar[0]:bar[1]] = YEL                      # the live contact: a glowing bar
        cv[8, bar[0]:bar[1]] = ORA
        cv[7, bar[0] - 1] = ORA
        cv[7, bar[1]] = ORA
    if vertical:
        cv = np.rot90(cv, -1)                            # 32 rows x 16 cols
        halves = (cv[:16], cv[16:])
    else:
        halves = (cv[:, :16], cv[:, 16:])
    out = []
    for h in halves:
        t = BODY_FACE.copy()
        t[h >= 0] = h[h >= 0]
        out.append(t)
    return out[0], out[1]


s76, s77 = slot_tiles(False, True)
put(0x76, s76)
put(0x77, s77)
s78, _ = slot_tiles(True, True, bar=(5, 15))
_, s79 = slot_tiles(True, False)
put(0x78, s78)
put(0x79, s79)

# the vertical slot's two halves must continue each other: rebuild them from one image so the rings agree
# (0x78 is the dangerous top part, 0x79 the harmless lower end; only the ring colour and the contact change)

# 0x74: the round hole between the tall plate's sockets
a = BODY_FACE.copy()
X, Y = grid(16, 16)
hole = np.hypot(X - 8, Y - 8) <= 3.6
a[shift(hole, 1, 0) | shift(hole, -1, 0) | shift(hole, 0, 1) | shift(hole, 0, -1)] = DGY
a[hole] = BLK
a[hole & ~shift(hole, 1, 1)] = DGY
put(0x74, a)

# 0x65: a screw head on the plate face
a = PLATE.copy()
head = np.hypot(X - 8, Y - 8) <= 4.4
a[shift(head, 1, 1) & ~head] = MGR
a[head] = LGR
a[head & ~shift(head, -1, -1)] = WHT
a[head & ~shift(head, 1, 1)] = MGR
a[head & ~erode8(head)] = DGY
polyline(a, [(5.5, 10.5), (10.5, 5.5)], BLK)
polyline(a, [(6.5, 10.5), (10.5, 6.5)], DGY)
put(0x65, a)


def shock(slot_tile, seed):
    a = slot_tile.copy()
    r = random.Random(seed)
    X, Y = grid(16, 16)
    cx, cy = 8.0, 8.0
    d = np.hypot(X - cx, Y - cy)
    th = np.arctan2(Y - cy, X - cx)
    keep = (X > 1.0) & (X < 15.0) & (Y > 1.0) & (Y < 15.0)
    star = d <= 2.2 + 3.6 * np.abs(np.cos(2 * th)) ** 3 + 1.8 * np.abs(np.sin(2 * th)) ** 12
    star = (d <= 1.8 + 4.8 * np.abs(np.cos(4 * th + 0.0)) ** 5)
    a[star & keep] = YEL
    a[(d <= 3.6 + 0.2 * np.cos(4 * th) - 0.6) & keep & (d <= 3.0)] = WHT
    a[(d <= 1.6)] = WHT
    # jagged bolts reaching out towards the tile's edges (staying one pixel inside)
    for (x0, y0, dx, dy) in ((8, 8, -1, -1), (8, 8, 1, -1), (8, 8, -1, 1), (8, 8, 1, 1), (8, 8, 0, -1), (8, 8, 0, 1),
                             (8, 8, -1, 0), (8, 8, 1, 0)):
        x, y = x0, y0
        for _ in range(8):
            x += dx + (r.choice([-1, 0, 1]) if dx == 0 else 0)
            y += dy + (r.choice([-1, 0, 1]) if dy == 0 else 0)
            if x < 1 or x > 14 or y < 1 or y > 14:
                break
            if (x - 8) ** 2 + (y - 8) ** 2 > 7:
                a[y, x] = CYA if r.random() < 0.7 else WHT
    for _ in range(10):
        x, y = r.randint(1, 14), r.randint(1, 14)
        if (x - 8) ** 2 + (y - 8) ** 2 > 12 and a[y, x] in (BLK, WHT, DGY, MGR, LGR):
            a[y, x] = r.choice([YEL, WHT, CYA])
    return a


put(0x73, shock(s76, 73))
put(0x75, shock(s78, 75))

# ------------------------------------------------------------------ taps
BTN_R = 4
BTN = {0x40: 'nw', 0x41: 'n', 0x42: 'ne', 0x43: 'w', 0x44: 'e', 0x46: 'sw', 0x47: 's', 0x49: 'se'}
for n, sd in BTN.items():
    reg(n, lambda f, o, sd=sd: bevel_tile(set(sd), f, o, R=BTN_R if len(sd) == 2 else 0), METAL, FLOOR1)
put(0x4E, METAL)
# the spout's lower corners: more rounded, and sitting on the basin floor (0x45 lit, 0x48 in the spout's shadow)
reg(0x45, lambda f, o: bevel_tile({'s', 'w'}, f, o, R=6), METAL, BASIN_LIT)
reg(0x48, lambda f, o: bevel_tile({'s', 'e'}, f, o, R=6), METAL, BASIN_SHADE)

LETTERS = {
    'H': ["X...X", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    'C': [".XXX.", "X...X", "X....", "X....", "X....", "X...X", ".XXX."],
}


def label(letter, col):
    a = METAL.copy()
    a[2:14, 2:14] = BLK
    a[3:13, 3:13] = col
    for j, row in enumerate(LETTERS[letter]):
        for i, ch in enumerate(row):
            if ch == 'X':
                a[4 + j, 5 + i] = WHT
    return a


put(0x4C, label('H', RED))
put(0x4D, label('C', BLU))

# ------------------------------------------------------------------ the basin, the table leg
put(0xC0, LEG)
put(0xC1, BASIN_LIT)
put(0xC2, BASIN_SHADE)

# ------------------------------------------------------------------ the grout lines of the tiled floor
GROUT = DGY


def grout(base, top, left, _o=None):
    a = base.copy()
    if top:
        a[0:2, :] = GROUT
    if left:
        a[:, 0:2] = GROUT
    return a


for n, base, tp, lf in ((0x5D, FLOOR0, True, True), (0x5C, FLOOR1, True, True), (0x5E, FLOOR0, False, True),
                        (0x5F, FLOOR1, False, True), (0x60, FLOOR0, True, False), (0x61, FLOOR1, True, False)):
    reg(n, lambda f, o, tp=tp, lf=lf: grout(f, tp, lf), base)

# ------------------------------------------------------------------ the openings (the nest entrances)


def opening(base, seed=0.0):
    """A dark round hole in the tile with a chipped, darker rim and a few short cracks; the outermost ring of
    pixels is the base tile's, so the tile joins its neighbours exactly like the one it replaces."""
    a = base.copy()
    X, Y = grid(16, 16)
    cx, cy = 8.0, 8.0
    d = np.hypot(X - cx, Y - cy)
    th = np.arctan2(Y - cy, X - cx)
    R = 4.9 + 0.35 * np.sin(3 * th + seed)
    hole = d <= R
    rim = (d > R) & (d <= R + 1.7)
    inside = (X > 1) & (X < 15) & (Y > 1) & (Y < 15)
    lit = (-(X - cx) - (Y - cy)) > 1.5
    a[rim & inside] = DGY
    a[rim & inside & lit & (bayer(16, 16) < 0.5)] = LGR     # chipped, lit edge on the upper left
    a[hole] = BLK
    a[hole & ~erode8(hole) & ~lit & (d > R - 1.0)] = DGY    # a faint far wall on the lower right
    for k, ang in enumerate((0.8, 2.4, 3.9, 5.5)):          # four short cracks leaving the rim diagonally
        r0 = 6.3
        for t in range(3):
            x = cx + (r0 + t) * math.cos(ang + 0.15 * (k % 2))
            y = cy + (r0 + t) * math.sin(ang + 0.15 * (k % 2))
            if 1 <= x < 15 and 1 <= y < 15:
                a[int(y), int(x)] = BLK
    a[0, :], a[15, :], a[:, 0], a[:, 15] = base[0, :], base[15, :], base[:, 0], base[:, 15]
    return a


put(0x80, opening(tiles[0x5E], seed=0.3))
put(0x81, opening(tiles[0x5F], seed=1.1))
put(0x82, opening(tiles[0x60], seed=2.0))
put(0x83, opening(tiles[0x61], seed=2.7))
put(0x84, opening(tiles[0x68], seed=3.4))
put(0x85, opening(tiles[0x66], seed=4.1))
put(0x86, opening(tiles[0x00], seed=4.8))
put(0x8A, opening(tiles[0x03], seed=5.5))

# ------------------------------------------------------------------ the scent overlay (same look as the yard sheet)
for k in range(1, 16):
    a = np.full((16, 16), TAN, dtype=np.int16)
    a[bayer(16, 16) < k / 16.0] = MAG
    put(0xF0 + k, a)

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
    a = np.full((16, 16), MGR, dtype=np.int16)           # plain tile of the carpet's colour
    for k, ch in enumerate('%02X' % n):
        x0 = 1 + k * 8
        for j, row in enumerate(FONT[ch]):
            for i, bit in enumerate(row):
                if bit == '1':
                    a[3 + 2 * j:5 + 2 * j, x0 + 2 * i:x0 + 2 * i + 2] = WHT
    return a


EXPECTED_UNUSED = ([0x3D, 0x4A, 0x4B, 0x4F, 0x6A] + list(range(0x7C, 0x80)) + list(range(0x87, 0x8A)) +
                   list(range(0x8B, 0xC0)) + list(range(0xC3, 0xF1)))
PLACEHOLDERS = [n for n in range(256) if n not in tiles]
assert sorted(PLACEHOLDERS) == sorted(EXPECTED_UNUSED), sorted(set(PLACEHOLDERS) ^ set(EXPECTED_UNUSED))
for n in PLACEHOLDERS:
    put(n, placeholder(n))

# ================================================================== checks on the sheet


def assert_join(a, b, horizontal, base_a, base_b, what=''):
    """Two tiles that must join (b right of a / below a): wherever either carries structure on the shared
    edge both must, in the same colour."""
    sta = STRUCT.get(a, tiles[a] != base_a)
    stb = STRUCT.get(b, tiles[b] != base_b)
    if horizontal:
        ea, eb, sa, sb = tiles[a][:, 15], tiles[b][:, 0], sta[:, 15], stb[:, 0]
    else:
        ea, eb, sa, sb = tiles[a][15, :], tiles[b][0, :], sta[15, :], stb[0, :]
    assert (sa == sb).all(), (hex(a), hex(b), 'h' if horizontal else 'v', what, 'structure differs')
    assert (ea[sa] == eb[sb]).all(), (hex(a), hex(b), 'h' if horizontal else 'v', what, 'colour differs')


def assert_self_tiles(n, base, horizontal=True, vertical=True):
    if horizontal:
        assert_join(n, n, True, base, base)
    if vertical:
        assert_join(n, n, False, base, base)


assert len(tiles) == 256
for n, t in tiles.items():
    assert t.shape == (16, 16) and 0 <= t.min() and t.max() <= 15, hex(n)          # size, opaque

# plain floors: periodic by construction (period 8), so every edge continues exactly
for n, t in ((0x00, FLOOR0), (0x01, FLOOR1), (0x02, FLOOR2), (0x03, FLOOR3), (0x64, WALL), (0x62, COUNTER),
             (0xC1, BASIN_LIT), (0xC2, BASIN_SHADE), (0xC0, LEG), (0x4E, METAL)):
    assert (tiles[n] == t).all()
    assert (t[:, 0:8] == t[:, 8:16]).all() or n in (0xC0, 0xC1, 0xC2) and (t[:, 0:4] == t[:, 4:8]).all()
    assert (t[0:8] == t[8:16]).all() or n in (0xC0, 0xC1, 0xC2)
# floors that must sit side by side
assert (tiles[0x63] == tiles[0x01]).all()                       # the plate face is floor 1
assert (tiles[0x04] == tiles[0x03]).all() and (tiles[0x05] == tiles[0x03]).all()
assert (tiles[0x06] == tiles[0x03]).all() and (tiles[0x07] == tiles[0x03]).all()
# floor 2 stays close to floor 3 (so the carpet opening 0x8A serves both) yet differs
_same = (tiles[0x02] == tiles[0x03]).mean()
assert 0.55 < _same < 0.98, _same
# C1 / C2 share the dither lattice (seamless with each other)
assert ((BASIN_LIT == LGR) == (BASIN_SHADE == MGR)).all()

# grout: lines are the same colour and width on all six tiles, structure continues along each run
for n, base in ((0x5D, FLOOR0), (0x5E, FLOOR0), (0x60, FLOOR0), (0x5C, FLOOR1), (0x5F, FLOOR1), (0x61, FLOOR1)):
    t = tiles[n]
    diff = t != base
    assert set(np.unique(t[diff])) <= {GROUT}, hex(n)
for n, base in ((0x60, FLOOR0), (0x61, FLOOR1)):
    assert (tiles[n][0:2, :] == GROUT).all() and (tiles[n][2:, :] == base[2:, :]).all()
for n, base in ((0x5E, FLOOR0), (0x5F, FLOOR1)):
    assert (tiles[n][:, 0:2] == GROUT).all() and (tiles[n][:, 2:] == base[:, 2:]).all()
for n, base in ((0x5D, FLOOR0), (0x5C, FLOOR1)):
    assert (tiles[n][0:2, :] == GROUT).all() and (tiles[n][:, 0:2] == GROUT).all()
    assert (tiles[n][2:, 2:] == base[2:, 2:]).all()
assert_join(0x60, 0x60, True, FLOOR0, FLOOR0)
assert_join(0x61, 0x61, True, FLOOR1, FLOOR1)
assert_join(0x5E, 0x5E, False, FLOOR0, FLOOR0)
assert_join(0x5F, 0x5F, False, FLOOR1, FLOOR1)
assert_join(0x5D, 0x60, True, FLOOR0, FLOOR0)
assert_join(0x5C, 0x61, True, FLOOR1, FLOOR1)
assert_join(0x5D, 0x5E, False, FLOOR0, FLOOR0)
assert_join(0x5C, 0x5F, False, FLOOR1, FLOOR1)
assert_join(0x60, 0x00, False, FLOOR0, FLOOR0)                  # an edge tile's rows below: plain floor
assert_join(0x5E, 0x00, True, FLOOR0, FLOOR0)

# counter: seams at the same pixel positions in 0x66, 0x68, 0x67, 0x69
for n in (0x66, 0x67, 0x69):
    assert (tiles[n][0, 7], tiles[n][0, 8]) == (DGY, WHT), hex(n)
for n in (0x68, 0x67, 0x69):
    assert (tiles[n][7, 0], tiles[n][8, 0]) == (DGY, WHT), hex(n)
assert_self_tiles(0x66, CF, vertical=True, horizontal=True)
assert_self_tiles(0x68, CF, vertical=True, horizontal=True)
assert_join(0x66, 0x67, False, CF, CF)
assert_join(0x67, 0x66, False, CF, CF)
assert_join(0x66, 0x69, False, CF, CF)
assert_join(0x67, 0x68, True, CF, CF)
assert_join(0x68, 0x67, True, CF, CF)
assert_join(0x69, 0x68, True, CF, CF)
assert_join(0x68, 0x69, True, CF, CF)
assert_join(0x62, 0x66, True, CF, CF)
assert_join(0x66, 0x62, True, CF, CF)
assert_join(0x62, 0x68, False, CF, CF)
assert_join(0x68, 0x62, False, CF, CF)

# skirting board: joins itself and its neighbours vertically; 0x7B has the same pixels on both edge columns
for n in (0x7A, 0x7B):
    assert (tiles[n][:, 5] == BRN).all() and (tiles[n][:, 10] == BRN).all()
    assert (tiles[n][:, 15] == tiles[0x7B][:, 15]).all()
    for x in (0, 1, 14, 15):
        assert len(set(tiles[n][:, x])) == 1, (hex(n), x)       # edge columns are plain lines
    for x in (4, 5, 6, 10):
        assert len(set(tiles[n][:, x])) == 1, (hex(n), x)         # the moulding lines run the full height
assert (tiles[0x7B][:, 0] == tiles[0x7B][:, 15]).all()            # neutral and symmetric
assert (tiles[0x7A][:, 1:] == tiles[0x7B][:, 1:]).all()           # 0x7A is 0x7B finished on the left
assert (tiles[0x7B][:, 1] == tiles[0x7B][:, 14]).all()

# raised frame: straight edges repeat, corners join them; the face is exactly floor 1
for n in RAISED:
    face = tiles[n] == FACE1
    assert face.mean() > 0.4, hex(n)
assert_join(0x54, 0x54, True, FACE1, FACE1)
assert_join(0x51, 0x51, True, FACE1, FACE1)
assert_join(0x5A, 0x5A, False, FACE1, FACE1)
assert_join(0x5B, 0x5B, False, FACE1, FACE1)
for a_, b_ in ((0x53, 0x54), (0x54, 0x55), (0x50, 0x51), (0x51, 0x52)):
    assert_join(a_, b_, True, FACE1, FACE1)
for a_, b_ in ((0x53, 0x5A), (0x5A, 0x50), (0x55, 0x5B), (0x5B, 0x52)):
    assert_join(a_, b_, False, FACE1, FACE1)
# sunken frame (top 0x51, left 0x5B, right 0x5A, bottom 0x54 with the four corners)
for a_, b_ in ((0x56, 0x51), (0x51, 0x58), (0x57, 0x54), (0x54, 0x59)):
    assert_join(a_, b_, True, FACE1, FACE1)
for a_, b_ in ((0x56, 0x5B), (0x5B, 0x57), (0x58, 0x5A), (0x5A, 0x59)):
    assert_join(a_, b_, False, FACE1, FACE1)
# the lit edges (0x54, 0x5A) really are lighter than the shaded ones (0x51, 0x5B)
def _lum(t):
    return np.mean([[0.3 * PALETTE[v][0] + 0.6 * PALETTE[v][1] + 0.1 * PALETTE[v][2] for v in r] for r in t])
assert _lum(tiles[0x54][:3]) > _lum(tiles[0x51][-3:]) + 40
assert _lum(tiles[0x5A][:, :3]) > _lum(tiles[0x5B][:, -3:]) + 40

# buttons / spout: edges repeat, corners join; the spout's lower corners join 0x47
assert_join(0x41, 0x41, True, METAL, METAL)
assert_join(0x47, 0x47, True, METAL, METAL)
assert_join(0x43, 0x43, False, METAL, METAL)
assert_join(0x44, 0x44, False, METAL, METAL)
for a_, b_ in ((0x40, 0x41), (0x41, 0x42), (0x46, 0x47), (0x47, 0x49), (0x45, 0x47), (0x47, 0x48)):
    assert_join(a_, b_, True, METAL, METAL)
for a_, b_ in ((0x40, 0x43), (0x43, 0x46), (0x42, 0x44), (0x44, 0x49), (0x43, 0x45), (0x44, 0x48)):
    assert_join(a_, b_, False, METAL, METAL)
assert (tiles[0x4C][0, :] == METAL[0, :]).all() and (tiles[0x4C][:, 0] == METAL[:, 0]).all()
assert (tiles[0x4D][-1, :] == METAL[-1, :]).all() and (tiles[0x4D][:, -1] == METAL[:, -1]).all()
assert (tiles[0x4C] != tiles[0x4D]).sum() > 40

# socket body: edges repeat, corners join
for a_, b_ in ((0x6B, 0x6C), (0x6C, 0x6C), (0x6C, 0x6D), (0x6E, 0x6F), (0x6F, 0x6F), (0x6F, 0x70)):
    assert_join(a_, b_, True, WALL, WALL)
for a_, b_ in ((0x6B, 0x71), (0x71, 0x71), (0x71, 0x6E), (0x6D, 0x72), (0x72, 0x72), (0x72, 0x70)):
    assert_join(a_, b_, False, WALL, WALL)
# the slot halves continue each other
_sl, _sr = tiles[0x76][:, 15] != WALL[:, 15], tiles[0x77][:, 0] != WALL[:, 0]
assert (_sl == _sr).all() and (tiles[0x76][:, 15][_sl] == tiles[0x77][:, 0][_sr]).all()
_su, _sd = tiles[0x78][15, :] != WALL[15, :], tiles[0x79][0, :] != WALL[0, :]
assert (_su == _sd).all()

# the opening tiles keep their base tile's outer edges
for n, b in ((0x80, 0x5E), (0x81, 0x5F), (0x82, 0x60), (0x83, 0x61), (0x84, 0x68), (0x85, 0x66), (0x86, 0x00), (0x8A, 0x03)):
    for edge in ((0, slice(None)), (15, slice(None)), (slice(None), 0), (slice(None), 15)):
        assert (tiles[n][edge] == tiles[b][edge]).all(), (hex(n), hex(b))
    assert (tiles[n] != tiles[b]).sum() > 40, hex(n)
    assert (tiles[n][6:10, 6:10] == BLK).sum() >= 8, hex(n)          # a real dark hole
_m = (tiles[0x8A][0, :] == tiles[0x02][0, :]).mean()
assert _m > 0.5, _m
# the shock frames keep the outer edges of the slot tiles they replace and have a bright burst
for n, b in ((0x73, 0x76), (0x75, 0x78)):
    for edge in ((0, slice(None)), (15, slice(None)), (slice(None), 0), (slice(None), 15)):
        assert (tiles[n][edge] == tiles[b][edge]).all(), (hex(n), hex(b))
    mid = tiles[n][4:12, 4:12]
    assert ((mid == YEL) | (mid == WHT)).sum() >= 18, hex(n)
    assert (tiles[n] != tiles[b]).sum() > 30
# dead ants and food: the background is exactly the floor
for f in range(4):
    for k in range(4):
        n = 0x08 + 4 * f + k
        assert (tiles[n] == FLOORS[f]).mean() > 0.8, hex(n)          # the ant is small: the rest is the floor
        n = 0x18 + 4 * f + k
        assert (tiles[n] == FLOORS[f]).mean() > (0.2 if k == 3 else 0.4), hex(n)
        # whatever lies outside the piles' shapes is exactly the floor: the corners are untouched
        assert (tiles[n][:1, :1] == FLOORS[f][:1, :1]).all() or k == 3
# food: each pile covers more of the floor than the one before
for f in range(4):
    counts = [(tiles[0x18 + 4 * f + k] != FLOORS[f]).sum() for k in range(4)]
    assert counts == sorted(counts) and len(set(counts)) == 4, (f, counts)
# unused slots are numbered placeholders
for n in PLACEHOLDERS:
    assert (tiles[n] == placeholder(n)).all()
assert len(PLACEHOLDERS) == 111, len(PLACEHOLDERS)

# ================================================================== write the sheet
sheet = np.zeros((256, 256), dtype=np.int16)
for n, t in tiles.items():
    sheet[(n // 16) * 16:(n // 16) * 16 + 16, (n % 16) * 16:(n % 16) * 16 + 16] = t
assert sheet.shape == (256, 256)

lines = [
    "# house.pix - clean-pack house tile sheet: 256 x 256 px, 16 x 16 tiles of 16 x 16 px.",
    "# Tile n at column n % 16, row n / 16. One hex digit per pixel = standard Mac 16-colour palette index.",
    "# Generated by make_house.py (procedural, seeded); do not edit by hand.",
]
lines += [''.join('%x' % v for v in row) for row in sheet]
with open(os.path.join(HERE, 'house.pix'), 'w', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')

PAL = np.array(PALETTE, dtype=np.uint8)


def to_img(arr, scale):
    img = Image.fromarray(PAL[arr])
    return img.resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.NEAREST)


S, ML, MT = 48, 30, 18
prev = Image.new('RGB', (ML + 16 * (S + 1) + 1, MT + 16 * (S + 1) + 1), (40, 40, 48))
dr = ImageDraw.Draw(prev)
for n in range(256):
    r_, c_ = n // 16, n % 16
    prev.paste(to_img(tiles[n], 3), (ML + 1 + c_ * (S + 1), MT + 1 + r_ * (S + 1)))
for i in range(16):
    dr.text((ML + 1 + i * (S + 1) + S // 2 - 3, 3), '%X' % i, fill=(230, 230, 230))
    dr.text((4, MT + 1 + i * (S + 1) + S // 2 - 6), '%X0' % i, fill=(230, 230, 230))
prev.save(os.path.join(HERE, 'preview_house.png'))

# ================================================================== mock-ups of every assembly
H = lambda s: [int(v, 16) if v != '..' else None for v in s.split()]
WIDE = [H(r) for r in [
    "53 54 54 54 54 54 54 54 54 54 54 54 55",
    "5A 63 63 63 63 63 63 63 63 63 63 63 5B",
    "5A 63 6B 6C 6C 6D 63 6B 6C 6C 6D 63 5B",
    "5A 63 71 76 77 72 63 71 76 77 72 63 5B",
    "5A 63 71 64 64 72 65 71 64 64 72 63 5B",
    "5A 63 71 76 77 72 63 71 76 77 72 63 5B",
    "5A 63 6E 6F 6F 70 63 6E 6F 6F 70 63 5B",
    "5A 63 63 63 63 63 63 63 63 63 63 63 5B",
    "50 51 51 51 51 51 51 51 51 51 51 51 52"]]
TALL = [H(r) for r in [
    "53 54 54 54 54 54 54 54 55",
    "5A 63 63 63 63 63 63 63 5B",
    "5A 63 6B 6C 6C 6C 6D 63 5B",
    "5A 63 71 78 64 78 72 63 5B",
    "5A 63 71 79 74 79 72 63 5B",
    "5A 63 6E 6F 6F 6F 70 63 5B",
    "5A 63 63 63 65 63 63 63 5B",
    "5A 63 6B 6C 6C 6C 6D 63 5B",
    "5A 63 71 78 64 78 72 63 5B",
    "5A 63 71 79 74 79 72 63 5B",
    "5A 63 6E 6F 6F 6F 70 63 5B",
    "5A 63 63 63 63 63 63 63 5B",
    "50 51 51 51 51 51 51 51 52"]]
assert len(WIDE) == 9 and all(len(r) == 13 for r in WIDE)
assert len(TALL) == 13 and all(len(r) == 9 for r in TALL)


def new_grid(w, h, fill):
    return [[fill] * w for _ in range(h)]


def place(G, x, y, rows):
    for j, row in enumerate(rows):
        for i, t in enumerate(row):
            if t is not None:
                G[y + j][x + i] = t


def render(G):
    h, w = len(G), len(G[0])
    A = np.zeros((h * 16, w * 16), dtype=np.int16)
    for j in range(h):
        for i in range(w):
            A[j * 16:j * 16 + 16, i * 16:i * 16 + 16] = tiles[G[j][i]]
    return A


BASE_OF = {0x00: FLOOR0, 0x5E: FLOOR0, 0x60: FLOOR0, 0x5D: FLOOR0, 0x01: FLOOR1, 0x5F: FLOOR1, 0x61: FLOOR1,
           0x5C: FLOOR1, 0x62: CF, 0x66: CF, 0x67: CF, 0x68: CF, 0x69: CF}


def check_grid_joins(G, pairs_h, pairs_v, what):
    """In the mock-up grid G, every horizontally / vertically adjacent pair of tile numbers listed in pairs_h /
    pairs_v must join seamlessly (assert_join). Returns how many joins were checked."""
    n = 0
    for j in range(len(G)):
        for i in range(len(G[0])):
            a_ = G[j][i]
            if i + 1 < len(G[0]) and (a_, G[j][i + 1]) in pairs_h:
                b_ = G[j][i + 1]
                assert_join(a_, b_, True, BASE_OF.get(a_, WALL), BASE_OF.get(b_, WALL), what)
                n += 1
            if j + 1 < len(G) and (a_, G[j + 1][i]) in pairs_v:
                b_ = G[j + 1][i]
                assert_join(a_, b_, False, BASE_OF.get(a_, WALL), BASE_OF.get(b_, WALL), what)
                n += 1
    return n


# which neighbours must join, by tile pair (left, right) / (above, below)
FRAME_H = {(0x53, 0x54), (0x54, 0x54), (0x54, 0x55), (0x50, 0x51), (0x51, 0x51), (0x51, 0x52),          # raised frame
           (0x56, 0x51), (0x51, 0x58), (0x57, 0x54), (0x54, 0x59),                                       # sunken frame
           (0x6B, 0x6C), (0x6C, 0x6C), (0x6C, 0x6D), (0x6E, 0x6F), (0x6F, 0x6F), (0x6F, 0x70),          # socket body
           (0x40, 0x41), (0x41, 0x41), (0x41, 0x42), (0x46, 0x47), (0x47, 0x47), (0x47, 0x49),          # button
           (0x45, 0x47), (0x47, 0x48), (0x76, 0x77)}                                                     # spout, slot
FRAME_V = {(0x53, 0x5A), (0x5A, 0x5A), (0x5A, 0x50), (0x55, 0x5B), (0x5B, 0x5B), (0x5B, 0x52),
           (0x56, 0x5B), (0x5B, 0x57), (0x58, 0x5A), (0x5A, 0x59),
           (0x6B, 0x71), (0x71, 0x71), (0x71, 0x6E), (0x6D, 0x72), (0x72, 0x72), (0x72, 0x70),
           (0x40, 0x43), (0x43, 0x43), (0x43, 0x46), (0x42, 0x44), (0x44, 0x44), (0x44, 0x49),
           (0x43, 0x45), (0x44, 0x48)}
GROUT_H = {(0x60, 0x60), (0x61, 0x61), (0x5D, 0x60), (0x5C, 0x61)}
GROUT_V = {(0x5E, 0x5E), (0x5F, 0x5F), (0x5D, 0x5E), (0x5C, 0x5F)}
COUNTER_H = {(0x68, 0x68), (0x67, 0x68), (0x68, 0x67), (0x69, 0x68), (0x68, 0x69), (0x62, 0x66), (0x66, 0x62)}
COUNTER_V = {(0x66, 0x66), (0x66, 0x67), (0x67, 0x66), (0x66, 0x69), (0x62, 0x68), (0x68, 0x62)}


def grout_grid(nx, ny, size):
    """nx x ny checks of size x size cells (floor 1 in the top-left, as in the spec's drawing)."""
    G = new_grid(nx * size, ny * size, 0x00)
    for cj in range(ny):
        for ci in range(nx):
            f1 = (ci + cj) % 2 == 0
            corner, top, left, rest = (0x5C, 0x61, 0x5F, 0x01) if f1 else (0x5D, 0x60, 0x5E, 0x00)
            for j in range(size):
                for i in range(size):
                    t = rest
                    if j == 0 and i == 0:
                        t = corner
                    elif j == 0:
                        t = top
                    elif i == 0:
                        t = left
                    G[cj * size + j][ci * size + i] = t
    return G


panels = []   # (title, image array, scale)

# 1. grout checks (small checks of 5 x 5 cells for the picture; the spec's are 16 x 16), then openings in them
G = grout_grid(3, 3, 5)
n_ = check_grid_joins(G, GROUT_H, GROUT_V, 'grout')
assert n_ > 60, n_
for (x, y, new_t, old_t) in ((5, 2, 0x80, 0x5E), (0, 2, 0x81, 0x5F), (5, 7, 0x81, 0x5F), (2, 5, 0x82, 0x60),
                             (7, 5, 0x83, 0x61), (8, 3, 0x86, 0x00), (12, 8, 0x86, 0x00)):
    if G[y][x] == old_t:
        G[y][x] = new_t
    else:
        raise AssertionError((x, y, hex(G[y][x]), hex(old_t)))
panels.append(('Grout checks (5 x 5 cells here; 16 x 16 in the game), with openings 0x80 0x81 0x82 0x83 0x86',
               render(G), 3))

# 2. the counter (two blocks wide), the front edge, the floor below, a tall plate, openings 0x84 / 0x85
W_, H_ = 17, 28
G = new_grid(W_, H_, 0x00)
for r in range(24):
    for c in range(W_):
        if r in (0, 8, 16):
            G[r][c] = 0x67 if c % 8 == 0 else 0x68
        elif r == 23:
            G[r][c] = 0x69 if c % 8 == 0 else 0x68
        else:
            G[r][c] = 0x66 if c % 8 == 0 else 0x62
n_ = check_grid_joins(G, COUNTER_H, COUNTER_V, 'counter')
assert n_ > 250, n_
G[16][11] = 0x84
G[12][8] = 0x85
place(G, 4, 2, TALL)
n_ = check_grid_joins(G, FRAME_H, FRAME_V, 'tall plate')
assert n_ > 60, n_
panels.append(('Counter: seams, front edge, floor below, a tall socket plate, openings 0x84 / 0x85', render(G), 3))

# 3. frames and taps
G = new_grid(30, 9, 0x01)
place(G, 1, 1, [[0x53, 0x54, 0x54, 0x54, 0x55], [0x5A, None, None, None, 0x5B], [0x5A, None, None, None, 0x5B],
                [0x50, 0x51, 0x51, 0x51, 0x52]])
place(G, 8, 1, [[0x56, 0x51, 0x51, 0x51, 0x58], [0x5B, 0xC2, 0xC2, 0xC2, 0x5A], [0x5B, 0xC2, 0xC1, 0xC1, 0x5A],
                [0x57, 0x54, 0x54, 0x54, 0x59]])
BUTTON = [[0x40, 0x41, 0x41, 0x41, 0x42], [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x43, 0x4E, 0x4C, 0x4E, 0x44],
          [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x46, 0x47, 0x47, 0x47, 0x49]]
SPOUT = [[0x40, 0x41, 0x41, 0x41, 0x42]] + [[0x43, 0x4E, 0x4E, 0x4E, 0x44]] * 12 + [[0x45, 0x47, 0x47, 0x47, 0x48]]
place(G, 14, 1, BUTTON)
place(G, 21, 1, [[0x40, 0x41, 0x41, 0x41, 0x42], [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x43, 0x4E, 0x4D, 0x4E, 0x44],
                 [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x46, 0x47, 0x47, 0x47, 0x49]])
n_ = check_grid_joins(G, FRAME_H, FRAME_V, 'frames')
assert n_ > 30, n_
panels.append(('Raised frame, sunken frame (with 0xC2 / 0xC1 inside), tap buttons (0x4C hot, 0x4D cold)', render(G), 4))

# 4. the sink unit
UW, UH = 55, 31
U = new_grid(UW, UH, 0x01)
place(U, 0, 0, [[0x53] + [0x54] * 53 + [0x55]])
place(U, 0, 30, [[0x50] + [0x51] * 53 + [0x52]])
for r in range(1, 30):
    U[r][0] = 0x5A
    U[r][54] = 0x5B


def basin(U, x0, y0, w, h):
    place(U, x0, y0, [[0x56] + [0x51] * (w - 2) + [0x58]])
    place(U, x0, y0 + h - 1, [[0x57] + [0x54] * (w - 2) + [0x59]])
    for r in range(1, h - 1):
        U[y0 + r][x0] = 0x5B
        U[y0 + r][x0 + w - 1] = 0x5A
        for c in range(1, w - 1):
            ir = r - 1
            U[y0 + r][x0 + c] = 0xC2 if (ir < 2 or c == 1) else 0xC1


basin(U, 2, 6, 29, 22)
basin(U, 35, 6, 17, 22)
# taps across the top of the left basin: buttons at cols 4..8 and 24..28, the spout at 14..18
place(U, 4, 1, [[0x40, 0x41, 0x41, 0x41, 0x42], [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x43, 0x4E, 0x4C, 0x4E, 0x44],
                [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x46, 0x47, 0x47, 0x47, 0x49]])
place(U, 24, 1, [[0x40, 0x41, 0x41, 0x41, 0x42], [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x43, 0x4E, 0x4D, 0x4E, 0x44],
                 [0x43, 0x4E, 0x4E, 0x4E, 0x44], [0x46, 0x47, 0x47, 0x47, 0x49]])
# the spout's shadow (0xC2) on the basin floor first, then the spout over it
for r in range(9, 17):
    for c in (19, 20):
        U[r][c] = 0xC2
for c in range(16, 21):
    for r in (15, 16):
        U[r][c] = 0xC2
place(U, 14, 1, [[0x40, 0x41, 0x41, 0x41, 0x42]] + [[0x43, 0x4E, 0x4E, 0x4E, 0x44]] * 12 +
      [[0x45, 0x47, 0x47, 0x47, 0x48]])
n_ = check_grid_joins(U, FRAME_H, FRAME_V, 'sink')
assert n_ >= 400, n_
panels.append(('The sink unit (55 x 31 cells)', render(U), 2))

# 5. wide plate on the wall, tall plate on the counter are shown in the rooms and the counter; a close-up of each
G = new_grid(30, 9, 0x64)
place(G, 1, 0, WIDE)
G2 = new_grid(9, 13, 0x62)
place(G2, 0, 0, TALL)
assert check_grid_joins(G, FRAME_H, FRAME_V, 'wide plate') > 40
panels.append(('Wide socket plate on the wall (13 x 9 cells), 0x76 / 0x77 dangerous slots', render(G)[:, :16 * 15], 4))
assert check_grid_joins(G2, FRAME_H, FRAME_V, 'tall plate') > 60
panels.append(('Tall socket plate (9 x 13 cells)', render(G2), 4))

# 6. a carpeted room, wall on the left (wall, 7A, 7B, carpet): rug with coin and clip, table, litter
RW, RH = 34, 20
G = new_grid(RW, RH, 0x03)
for r in range(RH):
    for c in range(21):
        G[r][c] = 0x64
    G[r][21], G[r][22] = 0x7A, 0x7B
place(G, 2, 2, WIDE[:])
# rug 12 x 7 on the carpet with a coin and a clip
for r in range(11, 18):
    for c in range(24, 33):
        G[r][c] = 0x02
place(G, 25, 12, [[0x28, 0x29, 0x2A], [0x2B, 0x2C, 0x2D], [0x2E, 0x2F, 0x30]])
place(G, 29, 13, [[None, 0x31, 0x32], [0x33, 0x34, 0x35], [0x36, 0x37, None]])
for (c, r, t) in ((28, 17, 0x38), (24, 16, 0x39), (32, 12, 0x3A), (27, 16, 0x3B), (31, 17, 0x3C)):
    G[r][c] = t
# stray litter, food, ants, an opening, specks on the carpet
place(G, 26, 3, [[0x3E]])
place(G, 29, 5, [[0x3F]])
place(G, 24, 8, [[0x24, 0x25, 0x26, 0x27]])
place(G, 24, 9, [[0x14, 0x15, 0x16, 0x17]])
place(G, 31, 8, [[0x8A]])
place(G, 24, 2, [[0x04, 0x05, 0x06, 0x07]])
place(G, 26, 6, [[0x18, 0x19, 0x1A, 0x1B]])
panels.append(('Carpeted room, wall on the left: 7A / 7B skirting, wide plate, rug with coin and clip', render(G), 2))

# 7. a room with the wall on the right: 03, 7B, 7B, 64 (the plate sits 7 columns into the wall)
G = new_grid(36, 12, 0x03)
for r in range(12):
    G[r][12], G[r][13] = 0x7B, 0x7B
    for c in range(14, 36):
        G[r][c] = 0x64
place(G, 21, 1, WIDE)
place(G, 3, 5, [[0x1C, 0x1D, 0x1E, 0x1F]])
panels.append(('Wall on the right: 03, 7B, 7B, wall', render(G), 2))

# 8. a table-top with legs, litter, a coin and a clip, on the carpet
TW, TH = 21, 9
G = new_grid(TW + 4, TH + 4, 0x03)
for r in range(TH):
    for c in range(TW):
        G[2 + r][2 + c] = 0x02
for r in list(range(4)) + list(range(5, 9)):
    for c in list(range(4)) + list(range(17, 21)):
        G[2 + r][2 + c] = 0xC0
rr = random.Random(9)
for r in range(TH):
    for c in range(4, 17):
        if G[2 + r][2 + c] == 0x02 and rr.random() < 0.05:
            G[2 + r][2 + c] = 0x38 + rr.randrange(5)
place(G, 2 + 6, 2 + 3, [[0x28, 0x29, 0x2A], [0x2B, 0x2C, 0x2D], [0x2E, 0x2F, 0x30]])
place(G, 2 + 11, 2 + 3, [[None, 0x31, 0x32], [0x33, 0x34, 0x35], [0x36, 0x37, None]])
place(G, 0, 4, [[0x8A]])
place(G, 24, 11, [[0x3E]])
panels.append(('Table-top 21 x 9 cells with the four 4 x 4 legs (0xC0), litter, coin, clip, on the carpet', render(G), 3))

# 9. each dead ant / food pile on its floor, and the unused first rows of the sheet
G = [[0x08 + k + 4 * f for k in range(4)] + [0x18 + k + 4 * f for k in range(4)] for f in range(4)]
panels.append(('Dead ants (0x08..0x17) and food piles (0x18..0x27) on the four floors', render(G), 5))

# the openings next to their base tiles
G = [[0x5E, 0x80, 0x5F, 0x81, 0x60, 0x82, 0x61, 0x83], [0x68, 0x84, 0x66, 0x85, 0x00, 0x86, 0x03, 0x8A],
     [0x73, 0x76, 0x77, 0x78, 0x75, 0x79, 0x74, 0x65]]
panels.append(('Openings next to their base tiles; shock frames 0x73 / 0x75 next to 0x76 / 0x78', render(G), 5))

# compose
from PIL import ImageFont
pad = 14
imgs = []
for title, arr, sc in panels:
    im = to_img(arr, sc)
    imgs.append((title, im))
Wimg = max(im.width for _, im in imgs) + 2 * pad
Himg = sum(im.height + 30 for _, im in imgs) + pad
canvas = Image.new('RGB', (Wimg, Himg), (30, 30, 36))
dr = ImageDraw.Draw(canvas)
y = pad
for title, im in imgs:
    dr.text((pad, y + 6), title, fill=(235, 235, 235))
    canvas.paste(im, (pad, y + 24))
    y += im.height + 30
canvas.save(os.path.join(HERE, 'mockup_house.png'))
print('wrote house.pix, preview_house.png, mockup_house.png;', len(PLACEHOLDERS), 'placeholders;',
      len(panels), 'mock-up panels')
