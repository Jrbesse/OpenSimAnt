"""screens_ants: group D, the four stills of the player's own ant (9100, 9101, 9110, 9111)."""
import math
import random

from screens_lib import Cv, ant, bayer, dither_rect, speckle, pebble, lp, ell_pts, bezier

PW, PH = 200, 161
PATCH_9111 = (72, 62, 152, 151)


def soil(cv, rect, seed, p10=0.13, p13=0.012, p14=0.006, base=11, alt=10):
    r = random.Random(seed)
    x0, y0, x1, y1 = rect
    for y in range(y0, y1):
        for x in range(x0, x1):
            v = r.random()
            if v < p14:
                cv.px(x, y, 14)
            elif v < p14 + p13:
                cv.px(x, y, 13)
            elif v < p14 + p13 + p10:
                cv.px(x, y, alt)
            else:
                cv.px(x, y, base)


def tufts(cv, rect, seed, n):
    """small clods of darker soil (2 px wide with a light top edge)"""
    r = random.Random(seed)
    x0, y0, x1, y1 = rect
    for _ in range(n):
        x, y = r.randrange(x0, x1), r.randrange(y0, y1)
        cv.rect(x, y, x + 3, y + 2, 10)
        cv.px(x, y, 11)
        cv.px(x + 2, y + 1, 14)


# ---- 9100: the ant lying on its back ------------------------------------------------------------------------------
def scene_9100():
    cv = Cv(PW, PH, 11)
    soil(cv, (0, 0, PW, PH), 9100)
    # the far ground: a darker, higher band with a lit ridge (low, three-quarter side view)
    cv.rect(0, 0, PW, 52, 10)
    soil(cv, (0, 0, PW, 52), 9101, p10=0.0, p13=0.02, p14=0.05, base=10, alt=10)
    for x in range(PW):
        ry = 50 + int(2 * math.sin(x / 13.0) + 1.5 * math.sin(x / 5.0))
        cv.px(x, ry, 11)
        cv.px(x, ry + 1, 11)
        for y in range(ry + 2, ry + 6):
            if bayer(x, y) < 0.35:
                cv.px(x, y, 10)
    # tufts and pebbles
    tufts(cv, (0, 56, PW, PH - 3), 4, 40)
    for (x, y, rx, ry) in [(14, 28, 6, 4), (176, 36, 5, 4), (60, 44, 3, 2), (150, 26, 4, 3)]:
        pebble(cv, x, y, rx, ry)
    for (x, y, rx, ry) in [(22, 132, 11, 7), (176, 140, 14, 9), (8, 100, 5, 4), (186, 96, 5, 4), (118, 150, 8, 5)]:
        pebble(cv, x, y, rx, ry)
    # a soft shadow under the ant
    sh = ell_pts(98, 130, 62, 10, 0.0)
    cv.poly(sh, fill=10)
    for y in range(120, 142):
        for x in range(34, 164):
            if cv.get(x, y) == 10 and ((x - 98) / 62.0) ** 2 + ((y - 130) / 10.0) ** 2 < 0.55 and bayer(x, y) < 0.7:
                cv.px(x, y, 14)
    # the ant on its back (head to the right), legs curled up
    cx, cy, L, ang = 98, 106, 118, -0.10
    leg_poses = [  # (attach u, v), knee, tip, curl  in units of L
        [(0.12, -0.04), (0.20, -0.27), (0.12, -0.35), (0.07, -0.29)],
        [(0.02, -0.05), (0.03, -0.30), (-0.06, -0.37), (-0.10, -0.31)],
        [(-0.07, -0.05), (-0.17, -0.26), (-0.28, -0.31), (-0.31, -0.23)],
    ]
    # far legs, behind the body, darker and partly hidden
    for pose in leg_poses:
        pts = [lp(cx, cy, ang, (u + 0.05) * L, v * 0.85 * L) for u, v in pose]
        cv.path(pts, 15, 6)
        cv.path(pts, 2, 3)
    # the body (legs off), antennae drawn here
    ant(cv, cx, cy, ang, L, body=1, shade=2, hi=0, out=15, legs=False, antennae=False, eyes=False)
    hu = 0.27 * L
    # belly bands on the abdomen (it lies on its back, the underside faces up)
    for u in (-0.43, -0.37, -0.31, -0.25, -0.19):
        a = lp(cx, cy, ang, u * L, -0.115 * L * (1 - ((u + 0.31) / 0.15) ** 2) ** 0.5 - 1)
        b = lp(cx, cy, ang, u * L, 0.09 * L * (1 - ((u + 0.31) / 0.15) ** 2) ** 0.5)
        cv.line(a, b, 2, 1)
    # near legs over the body
    for pose in leg_poses:
        pts = [lp(cx, cy, ang, u * L, v * L) for u, v in pose]
        cv.path(pts, 15, 7)
        cv.path(pts, 1, 4)
        cv.line(pts[0], pts[1], 2, 1)
    # head details: a closed eye (a dash), a dizzy mouth, mandibles a little apart
    e = lp(cx, cy, ang, hu + 0.02 * L, -0.055 * L)
    cv.line((e[0] - 3, e[1] - 1), (e[0] + 3, e[1] + 2), 15, 1)
    cv.line((e[0] - 3, e[1] + 2), (e[0] + 3, e[1] - 1), 15, 1)
    for s in (1, -1):
        b = lp(cx, cy, ang, hu + 0.10 * L, s * 0.04 * L)
        m = lp(cx, cy, ang, hu + 0.17 * L, s * 0.075 * L)
        t = lp(cx, cy, ang, hu + 0.21 * L, s * 0.04 * L)
        cv.path([b, m, t], 15, 5)
        cv.path([b, m, t], 2, 2)
    # one antenna bent up and over, one drooping to the ground
    a1 = [lp(cx, cy, ang, hu + 0.09 * L, -0.05 * L), lp(cx, cy, ang, hu + 0.16 * L, -0.20 * L),
          lp(cx, cy, ang, hu + 0.10 * L, -0.31 * L), lp(cx, cy, ang, hu + 0.02 * L, -0.30 * L)]
    cv.path(a1, 15, 3)
    a2 = [lp(cx, cy, ang, hu + 0.09 * L, 0.05 * L), lp(cx, cy, ang, hu + 0.22 * L, 0.11 * L),
          lp(cx, cy, ang, hu + 0.31 * L, 0.07 * L)]
    cv.path(a2, 15, 3)
    # a little dust puff and two flecks
    for (x, y, r) in [(30, 124, 5), (24, 130, 4), (38, 131, 4)]:
        cv.ell(x, y, r, r - 1, fill=12, outline=13)
    for (x, y) in [(15, 100), (186, 120), (130, 60)]:
        cv.px(x, y, 12)
        cv.px(x + 1, y, 0)
    return cv


# ---- 9101: a newborn ant next to its torn cocoon ----------------------------------------------------------------------
def scene_9101():
    cv = Cv(PW, PH, 11)
    soil(cv, (0, 0, PW, PH), 9102)
    tufts(cv, (0, 20, PW, PH - 3), 6, 45)
    for (x, y, rx, ry) in [(20, 40, 6, 4), (188, 52, 5, 4), (30, 148, 9, 6), (112, 152, 7, 5), (186, 30, 4, 3)]:
        pebble(cv, x, y, rx, ry)
    # shadows
    cv.poly(ell_pts(84, 140, 40, 8, 0.0), fill=10)
    cv.poly(ell_pts(166, 130, 36, 8, 0.0), fill=10)
    for y in range(128, 150):
        for x in range(40, 200):
            if cv.get(x, y) == 10 and bayer(x, y) < 0.45:
                cv.px(x, y, 14)
    # the torn cocoon (right): an ellipse tilted up to the left, a jagged opening facing the ant
    ccx, ccy, ca = 163, 112, -0.55
    body = ell_pts(ccx, ccy, 36, 21, ca)
    cv.poly(body, fill=12, outline=15)
    lit = ell_pts(ccx - 2, ccy - 3, 33, 17, ca)
    cv.poly(lit, fill=0)
    for k in (-0.55, -0.2, 0.15, 0.5):     # silk ridges across the cocoon
        a = lp(ccx, ccy, ca, 36 * k, -17 * (1 - k * k) ** 0.5)
        b = lp(ccx, ccy, ca, 36 * k, 17 * (1 - k * k) ** 0.5)
        cv.line(a, b, 12, 1)
    dither_rect(cv, ccx - 36, ccy - 10, ccx + 37, ccy + 26, 0, 12, 0.18)
    ox, oy = lp(ccx, ccy, ca, -30, 0)
    cv.poly(ell_pts(ox, oy, 9, 14, ca + math.pi / 2), fill=14, outline=15)
    cv.poly(ell_pts(ox + 1, oy + 2, 6, 10, ca + math.pi / 2), fill=15)
    for i in range(7):                      # torn petals round the opening
        t = 2 * math.pi * i / 7 + 0.3
        px, py = ox + 11 * math.cos(t) * 0.8, oy + 16 * math.sin(t)
        tip = (ox + 17 * math.cos(t) * 0.9, oy + 22 * math.sin(t))
        a = (ox + 11 * math.cos(t + 0.35) * 0.8, oy + 16 * math.sin(t + 0.35))
        b = (ox + 11 * math.cos(t - 0.35) * 0.8, oy + 16 * math.sin(t - 0.35))
        cv.poly([a, tip, b], fill=0, outline=15)
    # a loose scrap of shell on the ground
    cv.poly([(120, 146), (131, 142), (136, 147), (127, 151)], fill=0, outline=15)
    cv.px(126, 146, 12)
    # the ant, seen from the front and slightly above: abdomen up, then thorax, then the big head
    body_c, shade_c, hi_c = 1, 2, 0
    for s in (1, -1):    # legs splayed, drawn first
        for (a, k, t) in [((70, 86), (48, 92), (40, 120)), ((68, 78), (40, 72), (24, 102)), ((70, 72), (44, 56), (30, 78))]:
            pts = [(82 + s * (82 - px_), py_) for px_, py_ in (a, k, t)]
            cv.path(pts, 15, 5)
            cv.path(pts, 1, 3)
            cv.line(pts[0], pts[1], 2, 1)
    cv.poly(ell_pts(82, 52, 24, 28, 0.0), fill=2, outline=15)        # abdomen
    cv.poly(ell_pts(80, 50, 21, 25, 0.0), fill=1)
    cv.poly(ell_pts(76, 42, 11, 14, 0.0), fill=1)
    dither_rect(cv, 60, 30, 84, 56, 1, 0, 0.5)
    cv.poly(ell_pts(70, 40, 5, 9, 0.2), fill=0)
    for y in (58, 64, 70):                                            # bands
        cv.line((62, y), (100, y), 2)
    cv.poly(ell_pts(82, 80, 16, 14, 0.0), fill=2, outline=15)        # thorax
    cv.poly(ell_pts(80, 78, 14, 12, 0.0), fill=1)
    dither_rect(cv, 66, 68, 86, 82, 1, 0, 0.4)
    cv.poly(ell_pts(82, 108, 23, 20, 0.0), fill=2, outline=15)       # head
    cv.poly(ell_pts(80, 106, 21, 18, 0.0), fill=1)
    dither_rect(cv, 62, 92, 90, 112, 1, 0, 0.5)
    cv.poly(ell_pts(72, 99, 8, 5, 0.3), fill=0)
    for s in (1, -1):    # eyes looking up
        ex = 82 + s * 12
        cv.ell(ex, 103, 6, 7, fill=15)
        cv.ell(ex - 1, 101, 2.2, 2.6, fill=0)
    cv.px(82 - 1, 116, 15)
    cv.px(82 + 1, 116, 15)
    for s in (1, -1):    # mandibles, a little apart
        pts = [(82 + s * 5, 123), (82 + s * 9, 131), (82 + s * 4, 135)]
        cv.path(pts, 15, 4)
        cv.path(pts, 2, 2)
    for s in (1, -1):    # antennae, raised, curious
        pts = [(82 + s * 9, 91), (82 + s * 24, 78), (82 + s * 36, 60), (82 + s * 30, 53)]
        cv.path(pts, 15, 3)
    return cv


# ---- 9110 / 9111: a nestmate feeds the player's ant ----------------------------------------------------------------------
def render_feed(state):
    """state: 'before' (the drop in the nestmate's mouth) or 'after' (the drop in the yellow ant's mouth)."""
    cv = Cv(PW, PH, 11)
    soil(cv, (0, 0, PW, PH), 9110)
    tufts(cv, (0, 0, PW, PH - 3), 8, 50)
    for (x, y, rx, ry) in [(14, 150, 8, 5), (186, 20, 6, 4), (183, 150, 9, 6), (14, 20, 5, 4), (60, 125, 3, 2)]:
        pebble(cv, x, y, rx, ry)
    cx = 112
    after = state == 'after'
    drop_y = 113 if after else 101
    if after:
        drop(cv, cx, drop_y, 8)
    # the big black nestmate, head down at the top (its body runs off the top of the picture)
    ant(cv, cx, -20, math.pi / 2, 230, body=14, shade=13, hi=12, out=15, legcol=15, legw=7, legfill=14,
        antw=3, mand=(0.85 if not after else 1.0), eyes=True)
    # the small yellow player's ant, head up, its body running off the bottom
    ant(cv, cx, 165, -math.pi / 2, 110, body=1, shade=2, hi=0, out=15, legcol=15, legw=3, legfill=1, antw=2,
        mand=(0.6 if not after else 0.2), eyes=True, head_shift=(0.07 if after else 0.0))
    if not after:
        drop(cv, cx, drop_y, 8)
    return cv


def drop(cv, x, y, r):
    cv.ell(x, y, r, r, fill=9)
    cv.ell(x - 1, y - 1, r - 2, r - 2, fill=8)
    cv.ell(x - r * 0.35, y - r * 0.4, 2.2, 2.2, fill=0)
    cv.px(x + 2, y + 3, 9)


def scene_9110():
    return render_feed('before')


def scene_9111():
    return render_feed('after').crop(*PATCH_9111)
