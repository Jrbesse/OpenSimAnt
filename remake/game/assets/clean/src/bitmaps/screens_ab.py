"""screens_ab: group A (title 2000 / 2001), B (Select a Game 2500), C (About box 3000 / 3001)."""
import math
import random

import numpy as np

from screens_lib import (WM, Cv, ant, bayer, dither_rect, speckle, pebble, LETTERED, LABEL, LABEL_TALL, SMALL,
                         bezier, lp, ell_pts, tapered)
import uilib
from uilib import Face

W_T, H_T = 512, 372


class Tall9(Face):
    """Bold face with a 9-px capital height (the Select captions' title line)."""

    def __init__(self):
        super().__init__('tall9', bold=True, tall=True)
        self.cap = 9
        self.height = 11

    def glyph(self, ch):
        if ch not in self._c:
            g = Face.glyph(self, ch)
            r = 5 if (ch.islower() or ch in 'pgqyj') else 4
            g = np.vstack([g[:r + 1], g[r:r + 1], g[r + 1:]])
            self._c[ch] = g
        return self._c[ch]


TITLE9 = Tall9()


# ---- the wordmark --------------------------------------------------------------------------------------------------
def _shift(m, dx, dy):
    o = np.zeros_like(m)
    h, w = m.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    o[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return o


def wordmark(cv, pic, x, y, s, scale, main, shade, hi, outline, thick=2, face=WM, drop=None):
    """Lettering with an outline, a shaded lower part and a highlighted top edge.  Returns (ink w, ink h, x, y)."""
    LETTERED.append((pic, s))
    m = face.render(s, scale)
    pad = thick + 1
    h, w = m.shape
    big = np.zeros((h + 2 * pad, w + 2 * pad), dtype=bool)
    big[pad:pad + h, pad:pad + w] = m
    dil = np.zeros_like(big)
    for dy in range(-thick, thick + 1):
        for dx in range(-thick, thick + 1):
            if dx * dx + dy * dy <= thick * thick + 1:
                dil |= _shift(big, dx, dy)
    rows = np.arange(big.shape[0])[:, None] - pad
    frow = rows // scale
    low = big & (frow >= face.cap - 3)
    top = big & ~_shift(big, 0, scale)  # pixel whose neighbour `scale` rows above is not ink
    a = cv.arr()
    H, W = a.shape

    def paint(mask, c, ox=0, oy=0):
        ys, xs = np.nonzero(mask)
        for yy, xx in zip(ys, xs):
            px, py = x - pad + xx + ox, y - pad + yy + oy
            if 0 <= px < W and 0 <= py < H:
                a[py, px] = c

    if drop is not None:
        paint(dil, drop[2], drop[0], drop[1])
    paint(dil, outline)
    paint(big, main)
    paint(low, shade)
    paint(top & (frow <= 0 + 4), hi) if hi is not None else None
    cv.set_arr(a)
    ys, xs = np.nonzero(m)
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1), x + int(xs.min()), y + int(ys.min())


def text_mask_h(s, face, scale):
    m = face.render(s, scale)
    ys, _ = np.nonzero(m)
    return int(ys.max() - ys.min() + 1)


# ---- A: the title ---------------------------------------------------------------------------------------------------
def title_canvas():
    W, H = W_T, H_T
    rnd = random.Random(2000)
    cv = Cv(W, H, 5)
    # night sky: purple above, blue towards the horizon, dithered bands
    for y in range(H):
        t = y / 300.0
        for x in range(W):
            if t > 0.40 and bayer(x, y) < min(1.0, (t - 0.40) * 2.2):
                cv.px(x, y, 6)
    # moon with a halo
    mx, my = 430, 66
    for y in range(my - 44, my + 45):
        for x in range(mx - 44, mx + 45):
            d = math.hypot(x - mx, y - my)
            if 28 <= d < 44 and bayer(x, y) < (1 - (d - 28) / 16.0) * 0.55:
                cv.px(x, y, 6)
    cv.ell(mx, my, 26, 26, fill=0)
    cv.ell(mx + 9, my + 8, 22, 22, fill=12)          # shaded limb at the lower right
    cv.ell(mx - 3, my - 3, 23, 23, fill=0)
    cv.ell(mx - 10, my - 8, 4.5, 3.5, fill=12)
    cv.ell(mx + 8, my + 3, 6, 5, fill=12)
    cv.ell(mx - 4, my + 14, 3.5, 3, fill=12)
    # stars
    star_zone = lambda x, y: not (10 <= x <= 400 and 28 <= y <= 130) and not (385 <= x <= 480 and 25 <= y <= 110)
    for _ in range(70):
        x, y = rnd.randrange(8, W - 8), rnd.randrange(6, 190)
        if star_zone(x, y):
            cv.px(x, y, 0 if rnd.random() < 0.8 else 1)
    for (x, y) in [(60, 150), (250, 20), (340, 100), (500, 150), (130, 14)]:
        if star_zone(x, y):
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.px(x + dx, y + dy, 0)
    # the hill: a broad mound on a flat horizon
    def hill_y(x):
        return 306 - 124 * math.exp(-((x - 345) / 150.0) ** 2) - 12 * math.exp(-((x - 120) / 70.0) ** 2)
    for x in range(W):
        top = int(round(hill_y(x)))
        slope = hill_y(x + 2) - hill_y(x - 2)
        for y in range(top, H):
            c = 10
            depth = y - top
            if depth < 34:
                if slope < 0 and bayer(x, y) < min(0.6, -slope * 0.7) * (1 - depth / 34.0):
                    c = 11
                elif slope > 0 and bayer(x, y) < min(0.85, slope * 1.1) * (1 - depth / 40.0) + 0.0:
                    c = 14
            if depth == 0:
                c = 15
            elif depth == 1 and c == 10:
                c = 11 if slope < 0 else 14
            cv.px(x, y, c)
    # soil speckle
    speckle(cv, (0, 200, W, 306), [11, 14, 13], 500, 3, 1)
    for y in range(200, 306):
        for x in range(W):
            if cv.get(x, y) == 5 or cv.get(x, y) == 6:
                pass
    # re-clip: speckle only counts on the hill, so repaint the sky pixels that speckle hit above the hill line
    for y in range(190, 306):
        for x in range(W):
            if y < int(round(hill_y(x))) and cv.get(x, y) in (11, 13, 14):
                cv.px(x, y, 6 if bayer(x, y) < 0.7 else 5)
    # grass strip in front, dark green with lit blades
    gy = 300
    cv.rect(0, gy + 6, W, H, 9)
    dither_rect(cv, 0, gy, W, gy + 6, 9, 9, 1)
    for x in range(W):
        for y in range(gy, gy + 8):
            if y >= gy + 6 or bayer(x, y) < (y - gy) / 6.0:
                cv.px(x, y, 9)
    speckle(cv, (0, gy + 8, W, H), [8, 8, 15], 700, 4, 1)
    for _ in range(170):
        bx = rnd.randrange(0, W)
        by = gy + 8 + rnd.randrange(0, 40)
        bh = rnd.randrange(8, 26)
        lean = rnd.randrange(-3, 4)
        cv.line((bx, by), (bx + lean, by - bh), rnd.choice([8, 9, 8]), 1)
    # trails (tan) to the tunnel mouths and the ants
    mouths = [(300, 232), (372, 256), (432, 214)]
    trail1 = bezier((20, 330), (140, 318), (230, 284), (292, 244), 60)
    trail2 = bezier((500, 318), (470, 300), (420, 280), (378, 262), 40)
    trail3 = bezier((300, 340), (400, 300), (440, 262), (434, 226), 40)
    for tr in (trail1, trail2, trail3):
        for (x, y) in tr:
            cv.ell(x, y, 3.2, 2.4, fill=11)
        for (x, y) in tr[::2]:
            cv.px(x + 2, y + 3, 10)
    # tunnel mouths: warm light spilling out
    for (mx_, my_) in mouths:
        for y in range(my_ - 30, my_ + 18):
            for x in range(mx_ - 34, mx_ + 34):
                d = math.hypot((x - mx_) / 1.3, (y - my_ + 4))
                if d < 26 and bayer(x, y) < (1 - d / 26.0) * 0.8 and cv.get(x, y) in (10, 11, 14):
                    cv.px(x, y, 2)
        pts = [(mx_ + 15 * math.cos(math.pi * i / 24), my_ - 18 * math.sin(math.pi * i / 24)) for i in range(25)]
        cv.poly(pts + [(mx_ + 15, my_ + 6), (mx_ - 15, my_ + 6)], fill=11, outline=15)     # dirt lip
        pts2 = [(mx_ + 11 * math.cos(math.pi * i / 24), my_ - 14 * math.sin(math.pi * i / 24)) for i in range(25)]
        cv.poly(pts2 + [(mx_ + 11, my_ + 6), (mx_ - 11, my_ + 6)], fill=2, outline=15)
        pts3 = [(mx_ + 7 * math.cos(math.pi * i / 24), my_ - 9 * math.sin(math.pi * i / 24)) for i in range(25)]
        cv.poly(pts3 + [(mx_ + 7, my_ + 6), (mx_ - 7, my_ + 6)], fill=1)
        cv.rect(mx_ - 3, my_ - 4, mx_ + 4, my_ + 6, 0)
        cv.line((mx_ - 15, my_ + 6), (mx_ + 15, my_ + 6), 15, 1)
    # the marching ants (black colony, a few red), some carrying leaf pieces
    def ant_on(tr, i0, L, red=False, leaf=False):
        i1 = min(len(tr) - 1, i0 + 1)
        x, y = tr[i0]
        x2, y2 = tr[i1]
        ang = math.atan2(y2 - y, x2 - x)
        # walk toward the mouths (trails end at the mouths)
        ant(cv, x, y - 4, ang, L, body=3 if red else 14, shade=2 if red else 13, legcol=15, eyes=False, mand=0.2)
        if leaf:
            lx, ly = lp(x, y - 4, ang, 0.46 * L, 0)
            pts = ell_pts(lx, ly - 4, 0.17 * L, 0.11 * L, ang - 0.9)
            cv.poly(pts, fill=8, outline=9)
            cv.line((lx - 3, ly - 1), (lx + 3, ly - 7), 9, 1)
    for i in (4, 14, 25, 37, 48):
        ant_on(trail1, i, 24, leaf=(i % 2 == 0))
    ant_on(trail1, 31, 24, red=True)
    for i in (5, 16, 28):
        ant_on(trail2, i, 20, leaf=(i % 2 == 1))
    for i in (6, 20, 32):
        ant_on(trail3, i, 20, red=(i == 20), leaf=(i == 32))
    # fireflies / sparks
    for (x, y) in [(120, 240), (212, 205), (260, 150), (470, 190), (40, 262), (90, 300), (330, 150), (400, 160)]:
        cv.px(x, y, 1)
        dither_rect(cv, x - 2, y - 2, x + 3, y + 3, 5, 2, 0.15)
        cv.px(x, y, 1)
    # the wordmark (upper left) and the small line
    info = wordmark(cv, 2000, 28, 46, 'OpenSimAnt', 4, 1, 2, 0, 15, thick=1, drop=(5, 5, 14))
    tag = cv.text(2000, 31, 106, 'an open-source remake', SMALL, 0, scale=2, outline=15)
    # fade to black at the edges
    a = cv.arr()
    for y in range(H):
        for x in range(W):
            d = min(x, y, W - 1 - x, H - 1 - y)
            if d == 0:
                a[y, x] = 15
            elif d < 20 and bayer(x, y) < (1 - d / 20.0) ** 1.4:
                a[y, x] = 15
    cv.set_arr(a)
    return cv, info


# ---- B: Select a Game -----------------------------------------------------------------------------------------------
SEL = {
    'Tutorial': (5, 25, 68, 88),
    'Quick Game': (175, 25, 238, 88),
    'Full Game': (101, 94, 164, 157),
    'Experimental': (5, 163, 69, 226),
    'Load Game': (175, 163, 238, 226),
    'Cancel': (100, 232, 166, 249),
}
ZONES = {
    'Tutorial': (74, 27, 170, 88),
    'Quick Game': (244, 27, 320, 88),
    'Full Game': (170, 96, 320, 157),
    'Experimental': (75, 165, 172, 226),
    'Load Game': (244, 165, 320, 226),
}
DESC = {
    'Tutorial': ['learn to play with', 'a guided game'],
    'Quick Game': ['black vs red,', 'a small game'],
    'Full Game': ['every colony of the', 'yard and house; win'],
    'Experimental': ['a free sandbox,', 'no rules'],
    'Load Game': ['resume a', 'saved game'],
}
HEADING = 'Choose a Game'
HEADING_ROWS = (2, 23)


def tile_frame(cv):
    w, h = cv.w, cv.h
    cv.frame(0, 0, w, h, 15)
    cv.rect(1, 1, w - 2, 2, 0)
    cv.rect(1, 1, 2, h - 2, 0)
    cv.rect(1, h - 2, w - 1, h - 1, 13)
    cv.rect(w - 2, 2, w - 1, h - 1, 13)
    cv.px(w - 2, 1, 13)
    cv.px(1, h - 2, 13)


def tile_tutorial():
    cv = Cv(63, 63, 7)
    cv.rect(0, 52, 63, 63, 10)
    dither_rect(cv, 0, 52, 63, 56, 10, 11, 0.4)
    cv.line((0, 52), (62, 52), 14)
    # the board
    cv.rect(7, 7, 47, 38, 10)
    cv.rect(9, 9, 45, 36, 9)
    cv.frame(9, 9, 45, 36, 14)
    cv.rect(8, 37, 46, 40, 11)
    cv.line((8, 40), (45, 40), 10)
    cv.px(14, 38, 0)
    cv.px(15, 38, 12)
    # chalk drawing: three dots, an arrow and a little ant
    for x in (13, 19, 25):
        cv.ell(x, 15, 1.5, 1.5, fill=0)
    cv.line((13, 21), (31, 21), 0)
    cv.poly([(31, 18), (35, 21), (31, 24)], fill=0)
    cv.ell(39, 16, 2, 1.5, fill=0)
    cv.ell(36, 16, 1.5, 1.2, fill=0)
    cv.line((36, 18), (35, 20), 0)
    cv.line((38, 18), (39, 20), 0)
    cv.line((12, 29), (22, 29), 12)
    cv.line((12, 32), (28, 32), 12)
    cv.px(41, 31, 0)
    cv.line((38, 30), (40, 33), 0)
    cv.line((40, 33), (44, 27), 0)
    # the pupil: a yellow ant, with a pointer
    ant(cv, 44, 49, math.pi, 28, body=1, shade=2, legcol=15, legw=1, eyes=True)
    cv.line((37, 44), (21, 27), 10, 1)
    cv.line((38, 44), (22, 27), 11, 1)
    cv.ell(21, 26, 1.7, 1.7, fill=3)
    return cv


def tile_quick():
    cv = Cv(63, 63, 11)
    dither_rect(cv, 0, 40, 63, 63, 11, 10, 0.35)
    speckle(cv, (2, 40, 61, 61), [10, 10, 13], 40, 7, 1)
    for (x, y, r) in [(8, 55, 3), (52, 56, 2.5), (30, 58, 2)]:
        pebble(cv, x, y, r, r * 0.8)
    # flags
    cv.line((6, 4), (6, 22), 10, 1)
    cv.poly([(7, 4), (18, 8), (7, 12)], fill=14, outline=15)
    cv.line((56, 4), (56, 22), 10, 1)
    cv.poly([(55, 4), (44, 8), (55, 12)], fill=3, outline=15)
    # the spark between
    sx, sy = 31, 36
    pts = []
    for i in range(16):
        r = 9 if i % 2 == 0 else 4
        t = math.pi * 2 * i / 16 - math.pi / 2
        pts.append((sx + r * math.cos(t), sy + r * math.sin(t)))
    cv.poly(pts, fill=2, outline=15)
    cv.ell(sx, sy, 3.2, 3.2, fill=1)
    # the ants face to face
    ant(cv, 14, 38, 0, 33, body=14, shade=13, hi=12, legcol=15, mand=0.9, eyes=True)
    ant(cv, 49, 38, math.pi, 33, body=3, shade=2, hi=2, legcol=15, mand=0.9, eyes=True)
    return cv


def tile_full():
    cv = Cv(63, 63, 8)
    # lawn cells (mowing stripes) and the grid
    for r in range(3):
        for c in range(4):
            x0, y0 = 3 + 14 * c, 3 + 14 * r
            if (r + c) % 2:
                cv.rect(x0, y0, x0 + 14, y0 + 14, 9)
                dither_rect(cv, x0, y0, x0 + 14, y0 + 14, 9, 8, 0.45)
    for i in range(5):
        cv.line((3 + 14 * i, 3), (3 + 14 * i, 45), 9)
    for i in range(4):
        cv.line((3, 3 + 14 * i), (59, 3 + 14 * i), 9)
    # coloured cells
    def cell(c, r, col, inner):
        x0, y0 = 3 + 14 * c, 3 + 14 * r
        cv.rect(x0 + 1, y0 + 1, x0 + 14, y0 + 14, col)
        cv.frame(x0 + 1, y0 + 1, x0 + 14, y0 + 14, 15)
        cv.ell(x0 + 7, y0 + 7, 2, 1.5, fill=inner)
    cell(2, 0, 3, 2)
    cell(3, 1, 3, 2)
    cell(1, 2, 14, 13)
    cell(2, 1, 14, 13)
    cell(3, 2, 14, 13)
    # the house corner
    cv.rect(3, 3, 27, 31, 0)
    cv.rect(3, 3, 27, 14, 13)
    cv.poly([(3, 3), (27, 3), (27, 14), (3, 14)], fill=13)
    for y in range(4, 14, 3):
        cv.line((4, y), (26, y), 14)
    cv.rect(3, 14, 27, 16, 14)
    cv.rect(6, 19, 14, 27, 7)
    cv.frame(6, 19, 14, 27, 14)
    cv.line((10, 19), (10, 26), 14)
    cv.rect(18, 18, 25, 31, 10)
    cv.px(23, 25, 1)
    cv.frame(3, 3, 27, 31, 15)
    # the fence
    cv.rect(2, 50, 61, 61, 8)
    cv.line((2, 53), (61, 53), 10)
    cv.line((2, 53), (61, 53), 11)
    cv.line((2, 58), (61, 58), 10)
    for x in range(4, 61, 8):
        cv.rect(x, 48, x + 4, 61, 11)
        cv.line((x + 3, 48), (x + 3, 60), 10)
        cv.frame(x, 48, x + 4, 61, 15)
        cv.px(x + 1, 47, 15)
        cv.px(x + 2, 47, 15)
    cv.line((2, 53), (61, 53), 11)
    cv.line((2, 58), (61, 58), 10)
    return cv


def tile_exp():
    cv = Cv(64, 63, 1)
    dither_rect(cv, 0, 0, 64, 63, 1, 0, 0.12)
    # soil heap
    heap = [(6, 58), (14, 48), (24, 38), (33, 31), (42, 38), (52, 48), (60, 58)]
    cv.poly(heap, fill=11, outline=15)
    inner = [(33, 33), (42, 40), (51, 49), (58, 57), (40, 57), (36, 45)]
    cv.poly(inner, fill=10)
    dither_rect(cv, 30, 40, 58, 57, 11, 10, 0.3)
    speckle(cv, (10, 44, 56, 57), [10, 14], 25, 11, 1)
    cv.line((6, 58), (60, 58), 15)
    cv.rect(0, 59, 64, 63, 11)
    cv.line((0, 59), (63, 59), 15)
    # the spade stuck in the heap
    cv.line((44, 9), (38, 36), 10, 3)
    cv.line((44, 9), (38, 36), 11, 1)
    cv.rect(41, 6, 48, 9, 10)
    cv.frame(41, 6, 48, 9, 15)
    cv.poly([(33, 32), (43, 34), (41, 47), (35, 49), (31, 44)], fill=13, outline=15)
    cv.line((34, 34), (32, 43), 12)
    cv.line((36, 36), (35, 44), 14)
    # the magnifier
    cv.line((15, 31), (8, 45), 10, 4)
    cv.line((15, 31), (8, 45), 11, 2)
    cv.ell(17, 22, 11, 11, fill=14, outline=15)
    cv.ell(17, 22, 8, 8, fill=7)
    cv.ell(14, 19, 3, 2, fill=0)
    cv.px(19, 25, 14)
    ant(cv, 18, 24, -0.4, 11, body=14, shade=13, legcol=15)
    # ants around the heap
    ant(cv, 12, 56, 0.1, 13, body=14, shade=13)
    ant(cv, 55, 55, math.pi - 0.1, 13, body=3, shade=2)
    return cv


def tile_load():
    cv = Cv(63, 63, 6)
    dither_rect(cv, 0, 0, 63, 63, 6, 5, 0.2)
    # the folder
    cv.poly([(7, 24), (27, 24), (31, 29), (56, 29), (56, 57), (7, 57)], fill=10, outline=15)
    # the sheet sliding out
    cv.rect(13, 8, 49, 44, 0)
    cv.frame(13, 8, 49, 44, 15)
    cv.rect(14, 9, 48, 10, 0)
    cv.line((49, 9), (49, 44), 13)
    for y in (24, 29, 34):
        cv.line((18, y), (44, y), 12)
    ant(cv, 31, 16, 0.0, 15, body=14, shade=13)
    # the folder's front
    cv.poly([(5, 35), (58, 35), (58, 59), (5, 59)], fill=11, outline=15)
    cv.line((6, 36), (57, 36), 0)
    cv.line((6, 36), (6, 58), 0)
    cv.line((7, 58), (57, 58), 10)
    cv.line((57, 37), (57, 58), 10)
    dither_rect(cv, 8, 44, 56, 57, 11, 10, 0.18)
    # a returning arrow
    pts = bezier((52, 22), (58, 10), (48, 4), (38, 4), 12)
    cv.path(pts, 7, 3)
    cv.poly([(34, 4), (41, 0), (41, 8)], fill=7)
    return cv


def select_card():
    cv = Cv(320, 256, 12)
    tiles = {'Tutorial': tile_tutorial(), 'Quick Game': tile_quick(), 'Full Game': tile_full(),
             'Experimental': tile_exp(), 'Load Game': tile_load()}
    for name, t in tiles.items():
        r = SEL[name]
        assert (t.w, t.h) == (r[2] - r[0], r[3] - r[1]), (name, t.w, t.h)
        tile_frame(t)
        cv.blit(t, r[0], r[1])
    # heading
    hw = LABEL_TALL.width(HEADING) * 2
    cv.text(2500, (320 - hw) // 2, 4, HEADING, LABEL_TALL, 15, scale=2)
    # captions
    ink_zones = {}
    for name, z in ZONES.items():
        lines = DESC[name]
        block = 11 + 4 + 10 * len(lines)
        y = z[1] + (z[3] - z[1] - block) // 2
        x = z[0] + 1
        assert TITLE9.width(name) + 1 <= z[2] - z[0], name
        cv.text(2500, x, y, name, TITLE9, 15)
        for i, ln in enumerate(lines):
            assert SMALL.width(ln) + 1 <= z[2] - z[0], (name, ln, SMALL.width(ln))
            cv.text(2500, x, y + 15 + 10 * i, ln, SMALL, 6)
        ink_zones[name] = z
    # Cancel
    r = SEL['Cancel']
    cv.rect(r[0], r[1], r[2], r[3], 12)
    cv.frame(r[0], r[1], r[2], r[3], 15)
    cv.rect(r[0] + 1, r[1] + 1, r[2] - 2, r[1] + 2, 0)
    cv.rect(r[0] + 1, r[1] + 1, r[0] + 2, r[3] - 2, 0)
    cv.rect(r[0] + 1, r[3] - 2, r[2] - 1, r[3] - 1, 13)
    cv.rect(r[2] - 2, r[1] + 2, r[2] - 1, r[3] - 1, 13)
    cv.text(2500, (r[0] + r[2]) // 2, r[1] + 5, 'Cancel', LABEL, 15, centre=True)
    return cv


# ---- C: About ------------------------------------------------------------------------------------------------------
R_ABOUT = (33, 61, 287, 171)
ABOUT_HEAD = 'About OpenSimAnt'
ABOUT_FOOT = 'A fan project. Not an official game.'


def about_bg():
    cv = Cv(320, 200, 12)
    # heading: bold blue with a darker outline
    hw = WM.width(ABOUT_HEAD) * 2
    x = (320 - hw) // 2
    wordmark(cv, 3000, x, 8, ABOUT_HEAD, 2, 6, 5, None, 5, thick=0)
    # separator
    cv.rect(10, 46, 310, 47, 13)
    cv.rect(10, 47, 310, 48, 0)
    # well: sunken bevel round R (dark first, white wins the two mitred corners)
    x0, y0, x1, y1 = R_ABOUT
    cv.rect(x1, y0 - 2, x1 + 1, y1 + 1, 13)
    cv.rect(x1 + 1, y0 - 2, x1 + 2, y1 + 2, 14)
    cv.rect(x0 - 2, y1, x1 + 1, y1 + 1, 13)
    cv.rect(x0 - 2, y1 + 1, x1 + 3, y1 + 2, 14)
    cv.rect(x0 - 2, y0 - 2, x1 + 2, y0, 0)
    cv.rect(x0 - 2, y0 - 2, x0, y1 + 2, 0)
    # footer
    fw = SMALL.width(ABOUT_FOOT)
    cv.text(3000, (320 - fw) // 2, 181, ABOUT_FOOT, SMALL, 15)
    return cv


def about_card():
    cv = Cv(254, 109, 12)
    # emblem: a round badge with a hill, a tunnel and an ant
    ex, ey, er = 40, 54, 28
    cv.ell(ex, ey, er, er, fill=15)
    cv.ell(ex, ey, er - 2, er - 2, fill=7)
    dither_rect(cv, ex - 26, ey - 26, ex + 27, ey - 4, 7, 0, 0.12)
    # hill
    for x in range(ex - er + 2, ex + er - 1):
        for y in range(ey - er + 2, ey + er - 1):
            if math.hypot(x - ex + 0.5, y - ey + 0.5) < er - 2.2:
                h = ey + 4 - 15 * math.exp(-((x - ex) / 17.0) ** 2) + 3 * (abs(x - ex) / 28.0)
                if y >= h:
                    cv.px(x, y, 10)
                    if y == int(h):
                        cv.px(x, y, 9)
    cv.ell(ex, ey + 9, 6, 7, fill=15)                 # the tunnel mouth
    cv.ell(ex, ey + 11, 4, 5, fill=2)
    dither_rect(cv, ex - 18, ey + 14, ex + 19, ey + 24, 10, 14, 0.35)
    ant(cv, ex - 1, ey - 12, 0.0, 22, body=14, shade=13, legcol=15, legw=1, eyes=True)
    cv.px(ex + 9, ey - 16, 0)
    # the lettering
    LETTERED_BLOCK = ('OpenSimAnt', 'an open-source remake', 'a fan project')
    tx = 82
    wordmark(cv, 3001, tx, 26, LETTERED_BLOCK[0], 2, 6, 5, None, 15, thick=0)
    cv.text(3001, tx + 2, 52, LETTERED_BLOCK[1], SMALL, 15)
    cv.text(3001, tx + 2, 66, LETTERED_BLOCK[2], SMALL, 14)
    # keep the margins and the last row flat 12
    a = cv.arr()
    a[0, :] = 12
    a[-1, :] = 12
    a[:, 0] = 12
    a[:, -1] = 12
    cv.set_arr(a)
    return cv
