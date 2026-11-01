"""ency_ant.py - the one ant model: a side-view ant drawn from parameters, at any scale / rotation / mirrored.

Local coordinates are in body lengths (L), y down, the head front at x = 0, the ant faces LEFT.  draw_ant() maps them
with the canvas transform.  Small scales simplify (fewer details), they do not redesign.
"""
import math

import numpy as np

from ency_lib import (Cv, grad, K_, W_, MD, DK, LT, H1, H2, H1W, HX, DOT, lvl, catmull)

DEFAULT = dict(
    hs=1.0,        # head scale (soldier 1.8)
    hy=0.012,      # head centre height
    tl=1.0,        # thorax length factor
    ts=1.0,        # thorax thickness factor
    gl=1.0,        # gaster length factor
    gh=1.0,        # gaster height factor
    petl=0.07,     # waist length
    mand='closed',  # closed / open
    teeth=False,
    wings=None,    # None / 'alate'
    scars=False,
    leg=1.0,       # leg length factor
    pose='walk',   # walk / stand
    seg=0,         # gaster segment lines
    egg=False,
    ant=1.0,       # antenna length factor
    eye=True,
    head_tone=None,
    muscles=False,
    hair=False,
)


def _thorax_pts(sp, xt0):
    tl = 0.30 * sp['tl']
    ts = sp['ts']
    top = [(0.0, -0.030), (0.10, -0.066), (0.28, -0.080), (0.50, -0.060), (0.72, -0.070), (0.90, -0.046), (1.0, -0.018)]
    bot = [(1.0, 0.022), (0.82, 0.046), (0.5, 0.056), (0.18, 0.052), (0.0, 0.032)]
    pts = [(xt0 + u * tl, y * ts) for u, y in top + bot]
    return pts, tl


def _ik(hip, foot_ank, f, t, ks):
    hx, hy = hip
    ax, ay = foot_ank
    dx, dy = ax - hx, ay - hy
    d = math.hypot(dx, dy)
    if d > f + t - 1e-3:
        k = (f + t - 1e-3) / d
        ax, ay = hx + dx * k, hy + dy * k
        dx, dy = ax - hx, ay - hy
        d = math.hypot(dx, dy)
    d = max(d, abs(f - t) + 1e-3)
    a = (f * f - t * t + d * d) / (2 * d)
    b = math.sqrt(max(f * f - a * a, 0.0))
    ux, uy = dx / d, dy / d
    c1 = (hx + a * ux - b * uy, hy + a * uy + b * ux)
    c2 = (hx + a * ux + b * uy, hy + a * uy - b * ux)
    if abs(c1[1] - c2[1]) < 0.01:
        k = c1 if (c1[0] - c2[0]) * ks > 0 else c2
    else:
        k = c1 if c1[1] < c2[1] else c2
    return k, (ax, ay)


FEMUR_DIR = {  # (forward-facing: left is -x) femur direction for front / mid / hind, grounded and lifted
    (0, False): (-0.85, 0.40), (1, False): (0.20, 0.90), (2, False): (0.75, 0.66),
    (0, True): (-0.90, -0.05), (1, True): (0.45, 0.35), (2, True): (0.95, -0.05),
}


def draw_leg(cv, hip, foot, f, idx, lifted, tars, L, near=True):
    """hip, foot in local coordinates (foot = the toe tip); the femur leaves the hip in a fixed direction, the tibia joins
    its knee to the ankle, the tarsus runs ankle to toe"""
    dx, dy = FEMUR_DIR[(idx, lifted)]
    n = math.hypot(dx, dy)
    knee = (hip[0] + f * dx / n, hip[1] + f * dy / n)
    sgn = 1 if foot[0] >= hip[0] else -1
    ank = (foot[0] - 0.20 * tars * sgn, foot[1] - tars * 0.97)
    thick = 2 if (near and L >= 55) else 1
    dash = None if near else (2, 1)
    cv.line(hip, knee, 1, dash, thick)
    cv.line(knee, ank, 1, dash, 1)
    cv.line(ank, foot, 1, dash, 1)
    if L >= 70:
        cv.line(foot, (foot[0] - 0.012 * sgn, foot[1] + 0.008), 1)
    return knee, ank


def _wing(cv, base, scale, rise, L, dash=None):
    """a wing as an outline with veins: base on the thorax, sweeping back (right) and up"""
    bx, by = base
    s = scale
    lead = [(0.0, 0.0), (0.10 * s, -0.10 * rise), (0.32 * s, -0.17 * rise), (0.58 * s, -0.19 * rise), (0.80 * s, -0.13 * rise),
            (0.90 * s, -0.07 * rise)]
    trail = [(0.82 * s, -0.01 * rise), (0.62 * s, 0.02 * rise), (0.40 * s, 0.03 * rise), (0.18 * s, 0.025 * rise)]
    pts = [(bx + x, by + y) for x, y in lead + trail]
    cv.poly(pts, W_, 1, dash=dash, smooth=4)
    # darker leading edge
    for i in range(len(lead) - 1):
        a = (bx + lead[i][0], by + lead[i][1])
        b = (bx + lead[i + 1][0], by + lead[i + 1][1])
        cv.line((a[0], a[1] + 0.006), (b[0], b[1] + 0.006), 1)
    if L >= 50:
        # veins: a main vein from the base and a few cross veins
        cv.pline([(bx + 0.02 * s, by - 0.01 * rise), (bx + 0.30 * s, by - 0.07 * rise), (bx + 0.62 * s, by - 0.085 * rise),
                  (bx + 0.84 * s, by - 0.07 * rise)], 1, (3, 1) if L < 90 else None)
        for u, v0, v1 in ((0.30, -0.07, -0.15), (0.45, -0.075, -0.17), (0.62, -0.085, -0.16), (0.70, -0.08, 0.0)):
            cv.line((bx + u * s, by + v0 * rise), (bx + (u + 0.02) * s, by + v1 * rise), 1, (2, 2))
        cv.line((bx + 0.35 * s, by - 0.075 * rise), (bx + 0.32 * s, by + 0.025 * rise), 1, (2, 2))
    return pts


def draw_ant(cv, sp, L, ox, oy, flip=False, ang=0.0, pivot=0.5):
    """draw one ant; (ox, oy) is where local (pivot, 0) lands.  returns key regions in picture pixels"""
    s = dict(DEFAULT)
    s.update(sp)
    sp = s
    hs = sp['hs']
    hrx, hry = 0.085 * hs, 0.077 * hs
    hcx, hcy = hrx, sp['hy']
    xt0 = 2 * hrx - 0.02
    tpts, tl = _thorax_pts(sp, xt0)
    ts = sp['ts']
    xt1 = xt0 + tl
    petl = sp['petl']
    xg0 = xt1 + petl - 0.006
    gl = 0.40 * sp['gl']
    gh = 0.115 * sp['gh']
    gy = 0.014
    with cv.at(ox, oy, L, ang, flip, pivot, 0.0):
        sc = L
        # ---- far side first: legs and antenna (dashed)
        hipu = (0.22, 0.52, 0.80)
        hips = [(xt0 + u * tl, 0.046 * ts) for u in hipu]
        leg = sp['leg']
        fem = (0.17 * leg, 0.19 * leg, 0.22 * leg)
        tib = (0.19 * leg, 0.21 * leg, 0.26 * leg)
        tar = (0.075 * leg, 0.085 * leg, 0.10 * leg)
        gnd = 0.046 * ts + 0.27 * leg
        if sp['pose'] == 'walk':
            near = [(-0.13, 0), (0.05, 0.10), (0.20, 0)]
            far = [(-0.04, 0.10), (0.03, 0), (0.12, 0.10)]
        else:
            near = [(-0.10, 0), (0.0, 0), (0.15, 0)]
            far = [(-0.04, 0), (0.07, 0), (0.22, 0)]
        for i in range(3):
            fx = hips[i][0] + far[i][0] * leg + 0.02
            fy = gnd - far[i][1] * leg - 0.005
            draw_leg(cv, (hips[i][0] + 0.01, hips[i][1] - 0.01), (fx, fy), fem[i] * 0.95, i, far[i][1] > 0, tar[i], L, False)
        # antennae: far one first
        anl = sp['ant']
        bx, by = 0.28 * hrx * 2 * 0.5 + 0.0, hcy - 0.40 * hry

        def antenna(dx, dy, dash):
            B = (bx + dx, by + dy)
            scape = 0.15 * anl * max(1.0, hs ** 0.5)
            E = (B[0] - 0.5 * scape, B[1] - 0.87 * scape)
            f = 0.17 * anl
            pts = [E, (E[0] - 0.45 * f, E[1] - 0.03 * f), (E[0] - 0.82 * f, E[1] + 0.12 * f), (E[0] - 0.97 * f, E[1] + 0.40 * f)]
            w = 2 if L >= 110 else 1
            cv.line(B, E, 1, dash, w)
            cv.pline(catmull(pts, closed=False, n=3), 1, dash)
            if L >= 40 and dash is None:
                cv.line(pts[-1], (pts[-1][0] - 0.004, pts[-1][1] + 0.016), 1)
                cv.dot(E[0], E[1], 1, 0)
            return B, E, pts

        antenna(0.03, 0.01, (2, 1))
        # ---- wings behind (far / hind pair)
        W = sp['wings']
        wbase = (xt0 + 0.5 * tl, -0.068 * ts)
        # ---- gaster
        gp = []
        n = 14
        for k in range(n + 1):
            u = k / n
            hh = gh * (math.sin(math.pi * u ** 0.8) ** 0.55)
            gp.append((xg0 + gl * u, gy - hh))
        for k in range(n, -1, -1):
            u = k / n
            hh = gh * 1.06 * (math.sin(math.pi * u ** 0.8) ** 0.55)
            gp.append((xg0 + gl * u, gy + hh))
        gcx = xg0 + gl * 0.45
        tf_ = 1.0 if L >= 45 else 0.62
        gtone = grad(gcx, gy, gl * 0.55, 4 * tf_, 14 * tf_)
        cv.poly(gp[:], gtone, 1)
        if sp['seg']:
            for k in range(sp['seg']):
                u = 0.22 + 0.62 * (k + 0.5) / sp['seg']
                hh = gh * (math.sin(math.pi * u ** 0.8) ** 0.55)
                x = xg0 + gl * u
                cv.pline([(x - 0.004, gy - hh * 0.96), (x + 0.012, gy), (x - 0.004, gy + hh * 1.0)], 0)
        if sp['egg']:
            ex, ey = xg0 + gl + 0.0, gy + 0.01
            cv.ell(ex + 0.02, ey + 0.006, 0.026, 0.015, W_, 1)
        # ---- petiole (waist) with its node
        pt = [(xt1 - 0.014, -0.014), (xt1 + 0.010, -0.050), (xt1 + 0.034, -0.054), (xt1 + 0.056, -0.020), (xt1 + petl + 0.01, -0.012),
              (xg0 + 0.006, 0.014), (xt1 + 0.045, 0.024), (xt1 + 0.010, 0.020), (xt1 - 0.014, 0.014)]
        cv.poly(pt, DK if L >= 45 else MD, 1, smooth=3)
        # ---- thorax
        tc = (xt0 + 0.5 * tl, 0.0)
        cv.poly(tpts, grad(tc[0], 0.0, tl * 0.6, 4 * tf_, 13 * tf_), 1, smooth=5)
        if L >= 55:   # the sutures between the three thorax segments
            for u in (0.30, 0.64):
                x = xt0 + u * tl
                cv.line((x, -0.060 * ts), (x - 0.006, -0.012 * ts), 1, (2, 1))
        if sp['scars']:
            for u in (0.33, 0.62):
                r = max(0.012, 1.6 / L)
                cv.ell(xt0 + u * tl, -0.07 * ts, r, r, W_, 1)
        # ---- near legs
        for i in range(3):
            fx = hips[i][0] + near[i][0]
            fy = gnd - near[i][1] * leg
            draw_leg(cv, hips[i], (fx, fy), fem[i], i, near[i][1] > 0, tar[i], L, True)
        # ---- head
        ht = sp['head_tone'] or grad(hcx, hcy, hrx, 3 * tf_, 12 * tf_)
        cv.ell(hcx, hcy, hrx, hry, ht, 1)
        if sp['muscles']:
            # hatching on the cheek: muscles that close the mandibles
            for k in range(3):
                x = hcx + hrx * (0.15 + 0.22 * k)
                cv.pline([(x, hcy - hry * 0.15), (x + 0.10 * hrx, hcy + hry * 0.55)], 1, (1, 1))
        if sp['eye']:
            ex, ey = hcx - 0.05 * hrx, hcy - 0.30 * hry
            erx, ery = max(0.021 * hs ** 0.5, 0.9 / L), max(0.027 * hs ** 0.5, 0.9 / L)
            cv.ell(ex, ey, erx, ery, K_, 1)
            if L * hrx >= 9:
                cv.dot(ex - 0.12 * hrx, ey - 0.14 * hry, 0)
        # mandibles
        mx, my = 0.10 * hrx, hcy + 0.52 * hry
        ml = 0.042 * hs ** 0.9
        if sp['mand'] == 'closed':
            cv.poly([(mx + 0.02, my - 0.012), (mx - ml, my + 0.5 * ml), (mx - 0.5 * ml, my + 0.035 * hs + 0.012), (mx + 0.03, my + 0.02)],
                    K_, 1)
        else:
            # open: an upper and a lower jaw; the lower one drops, both toothed
            up = [(mx + 0.025, my - 0.045 * hs), (mx - 1.1 * ml, my - 0.10 * ml - 0.02 * hs), (mx - 0.45 * ml, my - 0.01 * hs)]
            lo = [(mx + 0.03, my + 0.00), (mx - 0.95 * ml, my + 0.75 * ml + 0.02 * hs), (mx - 0.3 * ml, my + 0.04 * hs)]
            cv.poly(up, K_, 1)
            cv.poly(lo, K_, 1)
            if sp['teeth']:
                for (a, b) in ((up[1], up[2]), (lo[1], lo[2])):
                    for t in (0.3, 0.55, 0.8):
                        px_ = a[0] + (b[0] - a[0]) * t
                        py_ = a[1] + (b[1] - a[1]) * t
                        sgn = 1 if a is up[1] else -1
                        # a tooth on the inner (facing) edge
                        cv.line((px_, py_), (px_, py_ + sgn * 0.012 * hs), 1)
        # antenna near
        nb, ne, npts = antenna(0.0, 0.0, None)
        # hairs
        if sp['hair']:
            for u in (0.1, 0.4, 0.7):
                x = xt0 + u * tl
                cv.line((x, -0.07 * ts), (x - 0.006, -0.09 * ts), 1)
        # ---- front wing over the body
        if W:
            _wing(cv, (wbase[0] + 0.07, wbase[1] + 0.012), 0.62, 0.72, L)
            _wing(cv, wbase, 0.82, 1.0, L)
        regions = {}
        def rect_of(pts):
            P = [cv._pt(p) for p in pts]
            xs = [p[0] for p in P]
            ys = [p[1] for p in P]
            return (int(math.floor(min(xs))), int(math.floor(min(ys))), int(math.ceil(max(xs))) + 1, int(math.ceil(max(ys))) + 1)
        regions['head'] = rect_of([(0, hcy - hry), (2 * hrx, hcy + hry)])
        regions['thorax'] = rect_of([(xt0 + 0.05 * tl, -0.07 * ts), (xt1, 0.05 * ts)])
        regions['gaster'] = rect_of([(xg0 + 0.05 * gl, gy - gh), (xg0 + gl * 0.95, gy + gh)])
        regions['waist'] = rect_of([(xt1 - 0.01, -0.05), (xg0 + 0.01, 0.02)])
        regions['gaster_c'] = tuple(int(round(v)) for v in cv._pt((gcx, gy)))
        regions['thorax_c'] = tuple(int(round(v)) for v in cv._pt(tc))
        regions['head_c'] = tuple(int(round(v)) for v in cv._pt((hcx, hcy)))
        regions['eye_c'] = tuple(int(round(v)) for v in cv._pt((hcx - 0.05 * hrx, hcy - 0.30 * hry)))
        regions['gnd'] = cv._pt((0, gnd))[1]
        regions['hip0'] = tuple(int(round(v)) for v in cv._pt(hips[0]))
        regions['ant_tip'] = tuple(int(round(v)) for v in cv._pt(npts[-1]))
        regions['ant_E'] = tuple(int(round(v)) for v in cv._pt(ne))
        regions['mouth'] = tuple(int(round(v)) for v in cv._pt((-0.02, hcy + 0.07)))
    return regions


def measure(sp, L, flip=False, ang=0.0):
    """bbox (x0, y0, x1, y1) of what an ant of body length L draws, relative to the pivot point"""
    sc = Cv(900, 900)
    draw_ant(sc, sp, L, 450, 450, flip, ang)
    return sc.bbox()


def fit(sp, W, H, flip=False, ang=0.0, Lmax=400):
    """largest integer L whose drawing fits W x H; returns (L, bbox relative to the pivot)"""
    bb = measure(sp, 100, flip, ang)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    L = int(100 * min(W / bw, H / bh))
    L = min(L, Lmax)
    while L > 8:
        bb = measure(sp, L, flip, ang)
        if bb[2] - bb[0] <= W and bb[3] - bb[1] <= H:
            return L, (bb[0] - 450, bb[1] - 450, bb[2] - 450, bb[3] - 450)
        L -= 1
    raise ValueError('does not fit')


def place(cv, sp, x0, y0, x1, y1, flip=False, ang=0.0, anchor='c'):
    """draw the ant as large as fits the rectangle (x1, y1 exclusive); returns its regions and L"""
    L, bb = fit(sp, x1 - x0, y1 - y0, flip, ang)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    if anchor == 'c':
        ox = x0 + (x1 - x0 - bw) // 2 - bb[0]
        oy = y0 + (y1 - y0 - bh) // 2 - bb[1]
    elif anchor == 'bl':
        ox = x0 - bb[0]
        oy = y1 - bh - bb[1]
    else:
        ox = x0 - bb[0]
        oy = y0 - bb[1]
    reg = draw_ant(cv, sp, L, ox, oy, flip, ang)
    reg['L'] = L
    reg['ox'], reg['oy'] = ox, oy
    return reg


def draw_hint(sp, **kw):
    s = dict(sp)
    s.update(kw)
    return s


def feet_y(sp, L):
    """how far below the pivot line the toes of a standing / walking ant of body length L lie"""
    s = dict(DEFAULT)
    s.update(sp)
    return L * (0.046 * s['ts'] + 0.27 * s['leg'])


def on_ground(cv, sp, L, cx, ground, flip=False, ang=0.0):
    """draw an ant whose toes touch the row `ground`, body centre at x = cx"""
    return draw_ant(cv, sp, L, cx, ground - feet_y(sp, L), flip, ang)


def mouth(L, ox, oy, flip=False):
    """the point just in front of the mandibles of an unrotated ant drawn by draw_ant(ox, oy)"""
    return (ox + (0.5 * L if flip else -0.5 * L), oy + 0.07 * L)
