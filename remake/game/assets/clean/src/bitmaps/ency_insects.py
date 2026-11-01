"""ency_insects.py - the other insects (termite, bee, wasp) and the small things the scenes share (larva, egg, pupa,
seed, aphid, leaf), all drawn in local units through the canvas transform like the ant model."""
import math

from ency_lib import (Cv, grad, W_, K_, LT, MD, DK, T1, H1, H2, HX, DOT, lvl, catmull)
import ency_ant as A


def place_fn(cv, fn, x0, y0, x1, y1, flip=False, anchor='c', Lmax=300):
    """fn(cv, L, ox, oy, flip) draws one subject; scale it up as far as it fits the rectangle; returns (L, ox, oy)"""
    def measure(L):
        sc = Cv(900, 900)
        fn(sc, L, 450, 450, flip)
        b = sc.bbox()
        return (b[0] - 450, b[1] - 450, b[2] - 450, b[3] - 450)
    bb = measure(100)
    L = int(100 * min((x1 - x0) / (bb[2] - bb[0]), (y1 - y0) / (bb[3] - bb[1])))
    L = min(L, Lmax)
    while L > 6:
        bb = measure(L)
        if bb[2] - bb[0] <= x1 - x0 and bb[3] - bb[1] <= y1 - y0:
            break
        L -= 1
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    if anchor == 'c':
        ox = x0 + (x1 - x0 - bw) // 2 - bb[0]
        oy = y0 + (y1 - y0 - bh) // 2 - bb[1]
    elif anchor == 'b':
        ox = x0 + (x1 - x0 - bw) // 2 - bb[0]
        oy = y1 - bh - bb[1]
    else:
        ox, oy = x0 - bb[0], y0 - bb[1]
    fn(cv, L, ox, oy, flip)
    return L, ox, oy


def ell_band(cv, cx, cy, rx, ry, x0, x1, tone, line=0):
    """the part of an ellipse between two x values (for stripes), as a polygon"""
    top, bot = [], []
    n = 8
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        t = max(0.0, 1 - ((x - cx) / rx) ** 2)
        h = ry * math.sqrt(t)
        top.append((x, cy - h))
        bot.append((x, cy + h))
    cv.poly(top + bot[::-1], tone, line)


def wing_poly(cv, base, tip, width, skew=0.35, veins=True, tone=W_, L=60, dash=None):
    """a translucent wing: an outlined leaf shape from base to tip with a few veins"""
    bx, by = base
    tx, ty = tip
    dx, dy = tx - bx, ty - by
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    w = width
    pts = [(bx, by),
           (bx + dx * 0.25 + nx * w * 0.9, by + dy * 0.25 + ny * w * 0.9),
           (bx + dx * 0.55 + nx * w * 1.0, by + dy * 0.55 + ny * w * 1.0),
           (bx + dx * 0.85 + nx * w * 0.55, by + dy * 0.85 + ny * w * 0.55),
           (tx, ty),
           (bx + dx * 0.85 - nx * w * 0.3, by + dy * 0.85 - ny * w * 0.3),
           (bx + dx * 0.55 - nx * w * 0.6, by + dy * 0.55 - ny * w * 0.6),
           (bx + dx * 0.25 - nx * w * 0.45, by + dy * 0.25 - ny * w * 0.45)]
    cv.poly(pts, tone, 1, smooth=4, dash=dash)
    if veins and L >= 40:
        cv.line((bx + dx * 0.05 + nx * w * 0.1, by + dy * 0.05 + ny * w * 0.1), (bx + dx * 0.80 + nx * w * 0.35, by + dy * 0.80 + ny * w * 0.35), 1, (3, 1))
        for u in (0.35, 0.52, 0.68):
            cv.line((bx + dx * u + nx * w * 0.25, by + dy * u + ny * w * 0.25), (bx + dx * (u + 0.04) - nx * w * 0.3, by + dy * (u + 0.04) - ny * w * 0.3), 1, (2, 2))


def jointed_leg(cv, hip, knee, foot, near=True, w=1, dash=None):
    cv.line(hip, knee, 1, dash, 2 if (near and w > 1) else 1)
    cv.line(knee, foot, 1, dash)


# ---------------------------------------------------------------------------------------------------- termite
def draw_termite(cv, L, ox, oy, flip=False):
    with cv.at(ox, oy, L, 0.0, flip, 0.5, 0.0):
        # far legs
        for hx in (0.19, 0.27, 0.33):
            cv.pline([(hx + 0.02, 0.09), (hx - 0.02, 0.17), (hx + 0.0, 0.245)], 1, (2, 1))
        # abdomen: a soft, long sac, banded
        cv.ell(0.66, 0.012, 0.35, 0.145, grad(0.66, 0.0, 0.3, 1, 5), 1)
        for k in range(1, 7):
            x = 0.38 + 0.085 * k
            h = 0.145 * math.sqrt(max(0.0, 1 - ((x - 0.66) / 0.35) ** 2))
            if L >= 40:
                cv.pline([(x - 0.004, -h * 0.9), (x + 0.012, 0.012), (x - 0.004, h * 0.95)], 1, (1, 1))
        # thorax joins the abdomen broadly (no waist)
        cv.ell(0.27, 0.008, 0.125, 0.108, grad(0.27, 0.0, 0.14, 2, 6), 1)
        # head, eye, mandibles
        cv.ell(0.085, 0.012, 0.085, 0.092, grad(0.085, 0.0, 0.09, 3, 7), 1)
        cv.dot(0.06, -0.015, 1, 0)
        cv.poly([(0.015, 0.045), (-0.012, 0.075), (0.03, 0.062)], K_, 1)
        # straight, beaded antennae
        tip = (-0.20, -0.12)
        base = (0.02, -0.055)
        cv.line(base, tip, 1, (1, 0))
        for k in range(1, 9):
            t = k / 8.0
            x, y = base[0] + (tip[0] - base[0]) * t, base[1] + (tip[1] - base[1]) * t
            cv.ell(x, y, max(0.013, 1.1 / L), max(0.013, 1.1 / L), W_, 1, n=8)
        # near legs, short and stubby
        for hx in (0.17, 0.25, 0.31):
            cv.pline([(hx, 0.09), (hx - 0.035, 0.165), (hx - 0.01, 0.245)], 1, None, 2 if L >= 45 else 1)
            cv.line((hx - 0.01, 0.245), (hx - 0.03, 0.25), 1)


# ------------------------------------------------------------------------------------------------------- bee
def draw_bee(cv, L, ox, oy, flip=False):
    with cv.at(ox, oy, L, 0.0, flip, 0.5, 0.0):
        # hind pair of wings (behind) and front pair, raised
        wing_poly(cv, (0.30, -0.10), (0.62, -0.30), 0.075, L=L)
        # abdomen with dark bands, narrow waist, stinger
        cv.ell(0.72, 0.03, 0.27, 0.145, grad(0.72, 0.03, 0.25, 1, 5), 1)
        for (a, b) in ((0.56, 0.64), (0.72, 0.81), (0.89, 0.97)):
            ell_band(cv, 0.72, 0.03, 0.27, 0.145, a, b, DK, 0)
        cv.ell(0.72, 0.03, 0.27, 0.145, None, 1)
        cv.line((0.985, 0.045), (1.07, 0.075), 1, None, 1)
        cv.poly([(0.455, 0.0), (0.50, -0.03), (0.50, 0.07), (0.455, 0.05)], MD, 1)
        # legs: three, the hind one with the pollen basket
        hips = [(0.22, 0.09), (0.29, 0.10), (0.37, 0.10)]
        feet = [(0.15, 0.38), (0.27, 0.40), (0.44, 0.46)]
        knees = [(0.17, 0.22), (0.30, 0.24), (0.49, 0.28)]
        for h, k, f in zip(hips, knees, feet):
            cv.pline([h, k, f], 1, None, 2 if L >= 50 else 1)
        # the pollen basket: a swollen, stippled bulge on the hind tibia
        cv.ell(0.475, 0.37, 0.048, 0.085, DK, 1, rot=0.12)
        for (px, py) in ((0.465, 0.33), (0.485, 0.36), (0.47, 0.40), (0.49, 0.43)):
            cv.dot(px, py, 0, 0)
        # thorax: fuzzy
        cv.ell(0.28, -0.01, 0.165, 0.135, grad(0.28, -0.01, 0.17, 3, 9), 1)
        if L >= 40:
            for k in range(11):
                a = math.pi * (0.1 + 0.8 * k / 10)
                x, y = 0.28 - 0.165 * math.cos(a), -0.01 - 0.135 * math.sin(a)
                cv.line((x, y), (x - 0.02 * math.cos(a) , y - 0.026 * math.sin(a)), 1)
        # head with a large eye, antennae
        cv.ell(0.085, 0.0, 0.085, 0.095, grad(0.085, 0.0, 0.09, 3, 8), 1)
        cv.ell(0.08, -0.015, 0.045, 0.062, K_, 1)
        cv.dot(0.065, -0.04, 0, 0)
        cv.poly([(0.01, 0.05), (-0.02, 0.085), (0.03, 0.075)], DK, 1)
        B = (0.03, -0.07)
        E = (-0.04, -0.20)
        cv.line(B, E, 1)
        cv.pline([E, (-0.09, -0.21), (-0.14, -0.17)], 1, None, 1)
        # the front wing on top
        wing_poly(cv, (0.24, -0.12), (0.80, -0.40), 0.095, L=L)
        cv.line((0.24, -0.12), (0.30, -0.105), 1)


# ------------------------------------------------------------------------------------------------------ wasp
def draw_wasp(cv, L, ox, oy, flip=False):
    with cv.at(ox, oy, L, 0.0, flip, 0.5, 0.0):
        # far legs, long and thin
        for h, f in (((0.19, 0.07), (0.07, 0.44)), ((0.26, 0.08), (0.27, 0.46)), ((0.33, 0.07), (0.52, 0.42))):
            cv.pline([h, ((h[0] + f[0]) / 2 + 0.02, (h[1] + f[1]) / 2 - 0.02), f], 1, (2, 1))
        # abdomen: a smooth teardrop with dark and light bands, on a long narrow waist
        cv.pline([(0.37, 0.0), (0.46, 0.015), (0.52, 0.02)], 1, None, 2)
        ab = [(0.50, 0.015), (0.58, -0.07), (0.72, -0.105), (0.88, -0.07), (1.0, 0.0), (0.88, 0.075), (0.72, 0.11), (0.58, 0.085)]
        cv.poly(ab, LT, 1, smooth=5)
        # bands: dark hatched, between them white
        for (a, b) in ((0.60, 0.67), (0.73, 0.80), (0.86, 0.93)):
            top = []
            bot = []
            for k in range(7):
                x = a + (b - a) * k / 6
                t = max(0.0, 1 - ((x - 0.74) / 0.27) ** 2)
                hh = 0.108 * math.sqrt(t)
                top.append((x, 0.01 - hh * 0.95))
                bot.append((x, 0.01 + hh))
            cv.poly(top + bot[::-1], K_, 0)
        for (a, b) in ((0.67, 0.73), (0.80, 0.86)):
            top = []
            bot = []
            for k in range(7):
                x = a + (b - a) * k / 6
                t = max(0.0, 1 - ((x - 0.74) / 0.27) ** 2)
                hh = 0.108 * math.sqrt(t)
                top.append((x, 0.01 - hh * 0.95))
                bot.append((x, 0.01 + hh))
            cv.poly(top + bot[::-1], W_, 0)
        cv.poly(ab, None, 1, smooth=5)
        cv.line((1.0, 0.005), (1.07, 0.03), 1)
        cv.poly([(0.49, 0.0), (0.51, -0.01), (0.53, 0.02), (0.49, 0.025)], K_, 1)
        # thorax
        cv.ell(0.25, -0.005, 0.135, 0.09, grad(0.25, -0.005, 0.14, 4, 11), 1)
        # head
        cv.ell(0.075, 0.0, 0.075, 0.075, grad(0.075, 0.0, 0.08, 3, 8), 1)
        cv.ell(0.06, -0.015, 0.03, 0.04, K_, 1)
        cv.poly([(0.008, 0.035), (-0.015, 0.065), (0.025, 0.06)], K_, 1)
        # antennae
        B = (0.01, -0.045)
        E = (-0.07, -0.17)
        cv.line(B, E, 1)
        cv.pline(catmull([E, (-0.14, -0.17), (-0.21, -0.11)], False, 3), 1)
        # near legs
        for h, f in (((0.18, 0.08), (0.05, 0.43)), ((0.25, 0.085), (0.25, 0.47)), ((0.32, 0.08), (0.50, 0.44))):
            kx, ky = (h[0] + f[0]) / 2 + 0.035, (h[1] + f[1]) / 2 - 0.03
            cv.pline([h, (kx, ky), f], 1, None, 2 if L >= 55 else 1)
            cv.line(f, (f[0] - 0.012, f[1] + 0.012), 1)
        # wings: narrow, held back
        wing_poly(cv, (0.27, -0.075), (0.96, -0.23), 0.04, L=L)
        wing_poly(cv, (0.20, -0.08), (0.86, -0.13), 0.03, L=L)


def hexcell(cv, cx, cy, r, tone=None):
    pts = [(cx + r * math.cos(math.pi / 6 + k * math.pi / 3), cy + r * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
    cv.poly(pts, tone, 1)


# ------------------------------------------------------------------------------------ small shared things
def larva(cv, cx, cy, s, flip=False, curl=1.0, tone=LT, spin=False):
    """a curved, legless, segmented grub; s is its body radius scale in px; head on the left (flip: right)"""
    n = 8
    R = 2.0 * s
    segs = []
    for i in range(n + 1):
        a = math.radians(40 + 200 * curl * i / n)       # from the tail up round to the head
        segs.append((R * math.cos(a), R * 0.55 * math.sin(a)))
    sg = -1 if flip else 1
    for i in range(n):
        x, y = segs[i]
        r = s * (0.42 + 0.5 * math.sin(math.pi * (i + 0.7) / (n + 0.4)))
        cv.ell(cx + sg * x * 0.9, cy + y, r * 1.0, r * 0.85, tone, 1, n=12)
    x, y = segs[n]
    cv.ell(cx + sg * x * 0.9, cy + y, s * 0.42, s * 0.40, W_, 1, n=10)
    cv.put(cx + sg * x * 0.9 - sg * 1, cy + y, 1)
    return (cx + sg * x * 0.9, cy + y)


def egg(cv, cx, cy, s, rot=0.0):
    cv.ell(cx, cy, s, s * 0.62, W_, 1, rot=rot, n=14)


def pupa(cv, cx, cy, s, rot=0.0, cocoon=True):
    """a pale adult form folded inside a cocoon's oval outline"""
    c, sn = math.cos(rot), math.sin(rot)

    def P(x, y):
        return (cx + c * x - sn * y, cy + sn * x + c * y)
    if cocoon:
        cv.ell(cx, cy, s * 1.25, s * 0.72, T1, 1, rot=rot, n=22)
    # the folded adult: head, thorax, gaster as three small ovals, legs as short strokes
    for (x, y, rx, ry) in ((-0.72 * s, 0, 0.30 * s, 0.30 * s), (-0.2 * s, 0, 0.38 * s, 0.34 * s), (0.5 * s, 0, 0.55 * s, 0.38 * s)):
        px, py = P(x, y)
        cv.ell(px, py, rx, ry, W_, 1, rot=rot, n=12)
    for k in range(3):
        a = P(-0.3 * s + k * 0.22 * s, 0.30 * s)
        b = P(-0.35 * s + k * 0.22 * s, 0.55 * s)
        cv.line(a, b, 1)


def seed(cv, cx, cy, rx, ry, rot=0.0):
    cv.ell(cx, cy, rx, ry, MD, 1, rot=rot, n=14)
    c, s = math.cos(rot), math.sin(rot)
    cv.line((cx - c * rx * 0.7, cy - s * rx * 0.7), (cx + c * rx * 0.7, cy + s * rx * 0.7), 1)


def aphid(cv, cx, cy, s, flip=False):
    """a small round soft insect with a short tube at the rear, head left"""
    sg = -1 if flip else 1
    cv.ell(cx, cy, s * 1.0, s * 0.8, LT, 1, n=16)
    cv.ell(cx - sg * s * 0.95, cy - s * 0.1, s * 0.42, s * 0.40, W_, 1, n=10)
    cv.put(cx - sg * s * 1.05, cy - s * 0.2, 1)
    cv.line((cx + sg * s * 0.6, cy + s * 0.35), (cx + sg * s * 1.2, cy + s * 0.65), 1)
    cv.line((cx + sg * s * 0.4, cy - s * 0.65), (cx + sg * s * 0.55, cy - s * 0.95), 1)
    for k in (-0.3, 0.1, 0.5):
        cv.line((cx + sg * s * k, cy + s * 0.7), (cx + sg * (s * k - 0.12 * s), cy + s * 1.3), 1)


def leaf_shape(cv, pts, midrib, veins, tone=T1, smooth=6):
    cv.poly(pts, tone, 1, smooth=smooth)
    cv.pline(catmull(midrib, False, 6), 1)
    for (a, b) in veins:
        cv.line(a, b, 1)
