"""screens_icons: group E, the seven 32 x 32 death-cause icons (9150..9156).  Each: a 1-px black ring, a ground colour,
a bold comic symbol, no lettering."""
import math
import random

from screens_lib import Cv, ant, dither_rect, speckle, lp, ell_pts, pebble


def ringed(cv):
    cv.frame(0, 0, 32, 32, 15)
    return cv


def grass_ticks(cv, c, seed, n=30):
    r = random.Random(seed)
    for _ in range(n):
        x = r.randrange(2, 30)
        y = r.randrange(6, 30)
        cv.line((x, y), (x + r.choice((-1, 0, 1)), y - r.randrange(2, 4)), c)


def icon_9155():
    """stepped on: the sole of a shoe coming down on an ant"""
    cv = Cv(32, 32, 8)
    grass_ticks(cv, 9, 5)
    # the ant under the sole: only the legs stick out at the sides
    ant(cv, 16, 18, 0.0, 28, body=1, shade=2, legcol=15, legw=1, antennae=False)
    fore = [(10, 5), (14, 3), (18, 3), (22, 5), (23, 10), (22, 15), (19, 17), (13, 17), (10, 15), (9, 10)]
    heel = [(12, 20), (20, 20), (21, 24), (19, 27), (13, 27), (11, 24)]
    cv.poly(fore, fill=12, outline=15)
    cv.poly(heel, fill=12, outline=15)
    # tread marks on the ball of the foot, a heel block with a cross pattern, a shine on the toe
    for y in (7, 9, 11, 13, 15):
        cv.line((12, y), (20, y), 14)
    cv.px(11, 8, 0)
    cv.px(12, 5, 0)
    cv.px(13, 4, 0)
    cv.rect(13, 22, 19, 26, 14)
    cv.line((16, 22), (16, 25), 12)
    cv.line((13, 24), (18, 24), 12)
    # motion lines
    for x in (4, 7, 25, 28):
        cv.line((x, 2), (x, 5), 0)
    return ringed(cv)


def mower(flecks):
    cv = Cv(32, 32, 9)
    # a lighter mown stripe behind the machine, a few blade ticks of tall grass
    cv.rect(10, 1, 22, 11, 8)
    for x in range(10, 22, 2):
        cv.px(x, 3, 9)
        cv.px(x + 1, 7, 9)
    grass_ticks(cv, 8, 9, 22)
    # handle
    cv.line((13, 13), (11, 3), 14)
    cv.line((19, 13), (21, 3), 14)
    cv.line((10, 3), (22, 3), 15)
    cv.px(10, 4, 15)
    cv.px(22, 4, 15)
    # wheels at the sides
    for x0 in (4, 24):
        cv.rect(x0, 13, x0 + 4, 27, 15)
        cv.rect(x0 + 1, 14, x0 + 3, 26, 14)
        for y in range(15, 26, 3):
            cv.line((x0 + 1, y), (x0 + 2, y), 13)
    # deck, engine and the round shield
    cv.rect(8, 12, 24, 28, 15)
    cv.rect(9, 13, 23, 27, 3)
    cv.line((9, 13), (22, 13), 2)
    cv.line((9, 13), (9, 26), 2)
    cv.line((10, 27), (22, 27), 14)
    cv.rect(12, 14, 20, 17, 14)
    cv.rect(13, 14, 15, 15, 13)
    cv.ell(16, 22, 5.5, 5.5, fill=15)
    cv.ell(16, 22, 4.2, 4.2, fill=13)
    cv.ell(15, 21, 2, 1.6, fill=12)
    cv.px(17, 23, 14)
    if flecks:
        for (x, y, c) in [(2, 9, 8), (3, 11, 0), (6, 8, 8), (28, 8, 0), (29, 11, 8), (26, 6, 8), (30, 14, 0), (4, 5, 0),
                          (1, 13, 8), (27, 3, 8), (23, 9, 0), (8, 10, 8)]:
            cv.px(x, y, c)
            if c == 8:
                cv.px(x + 1, y, 8)
    return ringed(cv)


def icon_9150():
    """drowned: an ant on its back in the water, ripples"""
    cv = Cv(32, 32, 6)
    dither_rect(cv, 0, 0, 32, 32, 6, 7, 0.25)
    cv.ell(16, 17, 14, 11, outline=7)
    cv.ell(16, 17, 11, 8.5, fill=6, outline=0)
    cv.ell(16, 17, 8, 6, fill=7, outline=7)
    cv.ell(16, 17, 8, 6, outline=0)
    dither_rect(cv, 6, 12, 26, 22, 7, 0, 0.0)
    # the ant on its back: body along x, legs pointing up
    for dx, kx in ((-5, -2), (0, 0), (5, 3)):
        cv.path([(16 + dx, 16), (16 + dx + kx, 10), (16 + dx + kx * 2 + 1, 6)], 15, 1)
    ant(cv, 16, 18, 0.0, 17, body=1, shade=2, legcol=15, antennae=True, legs=False)
    cv.px(22, 17, 15)
    # small splash dots
    for (x, y) in [(5, 6), (27, 6), (4, 26), (28, 25)]:
        cv.px(x, y, 0)
        cv.px(x + 1, y, 0)
    return ringed(cv)


def icon_9154():
    """starved: an empty gauge, the needle at the empty end (red mark)"""
    cv = Cv(32, 32, 12)
    cx, cy = 16, 17
    cv.ell(cx, cy, 13, 13, fill=15)
    cv.ell(cx, cy, 12, 12, fill=14)
    cv.ell(cx, cy, 10.5, 10.5, fill=0)
    dither_rect(cv, 4, 4, 28, 14, 0, 12, 0.0)
    # ticks over the upper arc
    for k in range(9):
        th = math.radians(150 + 30 * k)
        for r in (8, 9, 10):
            x = cx + r * math.cos(th)
            y = cy + r * math.sin(th)
            cv.px(round(x), round(y), 15)
    # the red empty zone
    for k in range(0, 26, 1):
        th = math.radians(150 + k)
        for r in (6, 7):
            cv.px(round(cx + r * math.cos(th)), round(cy + r * math.sin(th)), 3)
    th = math.radians(155)
    cv.line((cx, cy), (round(cx + 9 * math.cos(th)), round(cy + 9 * math.sin(th))), 15, 1)
    cv.line((cx, cy + 1), (round(cx + 9 * math.cos(th)), round(cy + 1 + 9 * math.sin(th))), 15, 1)
    cv.ell(cx, cy, 2.2, 2.2, fill=15)
    cv.px(cx - 1, cy - 1, 13)
    # a small drop mark, empty (outline only), and a base
    cv.rect(12, 26, 21, 29, 14)
    cv.line((13, 26), (20, 26), 13)
    cv.px(24, 8, 12)
    return ringed(cv)


def icon_9151():
    """poisoned: a spray can, a toxic cloud and an ant on its back"""
    cv = Cv(32, 32, 4)
    dither_rect(cv, 0, 0, 32, 32, 4, 3, 0.18)
    # the can
    cv.rect(5, 11, 15, 29, 15)
    cv.rect(6, 12, 14, 28, 12)
    cv.rect(6, 12, 8, 28, 0)
    cv.rect(12, 12, 14, 28, 13)
    cv.rect(6, 6, 14, 12, 15)
    cv.rect(7, 7, 13, 11, 14)
    cv.rect(7, 7, 9, 11, 13)
    cv.rect(14, 7, 17, 9, 15)
    cv.px(15, 7, 12)
    cv.rect(7, 16, 13, 24, 0)
    cv.frame(7, 16, 13, 24, 15)
    cv.poly([(10, 17), (12, 20), (10, 23), (8, 20)], fill=8, outline=9)
    # the cloud
    puffs = [(19, 14, 5, 4), (24, 9, 5, 4), (29, 12, 3, 3), (25, 16, 5, 3.5), (20, 8, 3.5, 3)]
    for (x, y, rx, ry) in puffs:
        cv.ell(x, y, rx + 1, ry + 1, fill=9)
    for (x, y, rx, ry) in puffs:
        cv.ell(x, y, rx, ry, fill=8)
    cv.ell(22, 8, 2, 1.5, fill=0)
    for (x, y) in [(26, 13), (20, 14), (23, 17)]:
        cv.px(x, y, 9)
        cv.px(x + 1, y, 9)
    for (x, y) in [(17, 5), (30, 6), (31, 17)]:
        cv.px(x, y, 8)
    # an ant on its back, legs up
    for dx in (-2, 0, 2):
        cv.line((23 + dx, 25), (23 + dx * 2, 21), 15)
    ant(cv, 23, 26, 0.0, 11, body=14, shade=13, legcol=15, legs=False, antennae=False)
    cv.px(27, 25, 0)
    return ringed(cv)


def icon_9156():
    """electrocuted: a bolt striking a small ant, on a dark purple ground"""
    cv = Cv(32, 32, 5)
    dither_rect(cv, 0, 0, 32, 32, 5, 14, 0.22)
    bolt = [(19, 2), (8, 17), (15, 17), (11, 29), (25, 12), (18, 12), (23, 2)]
    cv.poly(bolt, fill=15)
    bolt2 = [(19, 3), (10, 16), (16, 16), (13, 26), (23, 12), (17, 12), (21, 3)]
    cv.poly(bolt2, fill=2)
    bolt3 = [(19, 4), (11, 16), (15, 16), (14, 23), (21, 12), (16, 12), (19, 4)]
    cv.poly(bolt3, fill=1)
    # sparks and the ant
    for (a, b, c, d) in [(4, 24, 8, 22), (26, 21, 30, 19), (5, 16, 8, 15), (27, 28, 29, 26), (24, 24, 27, 24), (3, 28, 6, 27)]:
        cv.line((a, b), (c, d), 0)
    ant(cv, 22, 26, 0.0, 12, body=14, shade=13, legcol=15, legs=True, antennae=True)
    cv.px(26, 25, 0)
    return ringed(cv)


def make_icons():
    return {
        9155: icon_9155(),
        9152: mower(False),
        9153: mower(True),
        9150: icon_9150(),
        9154: icon_9154(),
        9151: icon_9151(),
        9156: icon_9156(),
    }
