"""yard_pass5: pass 5 of the yard spec: the spider and the map-window actors (group H: the bodies 1000..1007 and the beaten frames
1050..1053; group I: the small spiders 1100..1107, the sneaker 1200..1203, the Map window's mower 1210 / 1211, the marker 1400)
and their assertions.  `build(reg)` registers the pictures; the checks are registered with `reg.check`.

Design (README.md, yard section "pass 4-5"): the spider is a tan cephalothorax and a dark-brown abdomen with a pale highlight, drawn as
shaded spheres seen from straight above (yard_sprite.Scene with elev 90), one model rendered for the 8 headings; the beaten frames
carry the 1007 body untouched and four sets of black legs drawn only OUTSIDE the body.  The sneaker is white with a red toe cap and
heel tab, a dark sole and black laces; the Map window's mower has a red deck, a dark engine cover and black wheels on a dark-green mat.
"""
import json
import os

import numpy as np

import yard_mapactors as ma
import yard_sprite as sp
from yard_sprite import Pose, Scene
from uilib import Img, T

HERE = os.path.dirname(os.path.abspath(__file__))
LEGS_JSON = os.path.normpath(os.path.join(HERE, '..', 'spider', 'legs.json'))

# ------------------------------------------------------------------------------------------------ the spec's table
BODY = {      # heading: (id, w, h, thorax centre, A1..A4, B1..B4, F1, F2)
    0: (1000, 14, 36, (6, 10), [(11, 4), (11, 8), (11, 12), (11, 16)], [(1, 4), (1, 8), (1, 12), (1, 16)], [(10, 0), (2, 0)]),
    1: (1001, 28, 28, (20, 8), [(28, 7), (25, 10), (22, 13), (19, 16)], [(21, 0), (18, 3), (15, 6), (12, 9)], [(30, 5), (23, -2)]),
    2: (1002, 36, 14, (25, 6), [(31, 11), (27, 11), (23, 11), (19, 11)], [(31, 1), (27, 1), (23, 1), (19, 1)], [(35, 2), (35, 10)]),
    3: (1003, 28, 28, (20, 20), [(28, 21), (25, 18), (22, 15), (19, 12)], [(21, 28), (18, 25), (15, 22), (12, 19)], [(30, 23), (23, 30)]),
    4: (1004, 14, 36, (6, 26), [(1, 32), (1, 28), (1, 24), (1, 20)], [(11, 32), (11, 28), (11, 24), (11, 20)], [(10, 36), (2, 36)]),
    5: (1005, 28, 28, (8, 20), [(0, 21), (3, 18), (6, 15), (9, 12)], [(7, 28), (10, 25), (13, 22), (16, 19)], [(-2, 23), (5, 30)]),
    6: (1006, 36, 14, (10, 6), [(4, 1), (8, 1), (12, 1), (16, 1)], [(4, 11), (8, 11), (12, 11), (16, 11)], [(0, 2), (0, 10)]),
    7: (1007, 28, 28, (9, 9), [(1, 8), (4, 11), (7, 14), (10, 17)], [(8, 1), (11, 4), (14, 7), (17, 10)], [(-1, 6), (6, -1)]),
}
BEATEN = [(1050, 67, 67, (27, 25)), (1051, 62, 53, (21, 15)), (1052, 41, 37, (14, 10)), (1053, 41, 36, (14, 10))]
SMALL_TRANSP = {0: 84, 1: 91, 2: 84, 3: 91, 4: 84, 5: 91, 6: 84, 7: 91}


def table_from_legs():
    """Recompute the attach / fang table from legs.json by the spec's turn and flip rules; returns {heading: (A, B, F)} relative
    to the thorax centre, or None when the file is not there."""
    if not os.path.exists(LEGS_JSON):
        return None
    d = json.load(open(LEGS_JSON))
    nA = [tuple(l[0][0]) for l in d['north']['legs']]
    nF = tuple(d['north']['fangs'][0][0])
    eA = [tuple(l[0][0]) for l in d['north_east']['legs']]
    eF = tuple(d['north_east']['fangs'][0][0])
    mirN = lambda p: (-p[0], p[1])
    mirE = lambda p: (-p[1], -p[0])
    sets = {0: ([*nA], [mirN(p) for p in nA], [nF, mirN(nF)]),
            1: ([*eA], [mirE(p) for p in eA], [eF, mirE(eF)])}
    turn = {2: lambda p: (-p[1], p[0]), 4: lambda p: (-p[0], -p[1]), 6: lambda p: (p[1], -p[0])}
    flip = {3: lambda p: (p[0], -p[1]), 7: lambda p: (-p[0], p[1]), 5: lambda p: (-p[0], -p[1])}
    out = {0: sets[0], 1: sets[1]}
    for k, f in turn.items():
        out[k] = tuple([f(p) for p in s] for s in sets[0])
    for k, f in flip.items():
        out[k] = tuple([f(p) for p in s] for s in sets[1])
    return out


def check_table():
    t = table_from_legs()
    if t is None:
        print('WARNING: spider/legs.json not found: using the spec table for the attach points')
        return
    for k, (bid, w, h, c, A, B, F) in BODY.items():
        a, b, f = t[k]
        for got, want, ordered in ((a, A, True), (b, B, True), (f, F, False)):
            g = [(x + c[0], y + c[1]) for (x, y) in got]
            assert (g == want if ordered else sorted(g) == sorted(want)), (bid, 'table differs from legs.json', g, want)


# ------------------------------------------------------------------------------------------------ the body model
ABD = [10, 10, 12]        # abdomen: dark brown, pale highlight (top-left)
CEPH = [11, 11, 12]       # cephalothorax: tan, pale highlight
MARK = 14


def spider_scene(heading_k, su=1.0):
    """The one spider, seen from straight above.  heading_k 0 = north, clockwise.  Fill coordinates: u' = 0 at the head tip, 34 at the
    rear (the 1-px outline of the finished picture makes it 36)."""
    phi = 90.0 - 45.0 * heading_k
    pose = Pose(heading=phi, elev=90.0)
    sc = Scene(ext=30.0, S=8, elev=90.0, thr=(0.0, 0.93))
    W = pose.w
    U = lambda u, v=0.0: W((17.0 - (3.7 + (u - 3.7) * su), v, 0.0))   # a point u' along the body from the head tip, v to the right
    # (su stretches the body along its axis only: the widths stay, so the diagonal bodies keep their leg-carrying width)

    def abd_dec(loc):                               # a darker dorsal stripe and a pale pair of dots on the abdomen
        out = np.full(len(loc), -1, dtype=np.int16)
        f, r = loc[:, 0], loc[:, 1]
        u = 17.0 - f
        out[(np.abs(r) < 1.0) & (u > 21.0) & (u < 31.5)] = MARK
        return out
    dec = (pose, abd_dec)
    # cephalothorax (head and thorax in one)
    sc.sphere(U(3.7), 3.7, CEPH, pid=1)
    sc.cap(U(3.7), U(9.0), 3.7, 5.7, CEPH, pid=1)
    sc.cap(U(9.0), U(13.0), 5.7, 6.0, CEPH, pid=1)
    sc.cap(U(13.0), U(15.3), 6.0, 4.6, CEPH, pid=1)
    # the waist and the abdomen
    sc.sphere(U(19.6), 1.8, [10, 10, 10], pid=2)
    sc.cap(U(26.0), U(28.0), 5.0, 6.0, ABD, pid=3, decal=dec)
    sc.sphere(U(28.0), 6.0, ABD, pid=3, decal=dec)
    # eyes: a few small pale pixels on the head (the jaws are the game's fangs)
    for (u, v) in ((2.7, -1.0), (2.7, 1.0), (4.4, -2.1), (4.4, 2.1)):
        sc.mark(U(u, v), 12, 3.0)
    return sc


def fit_su(k, w, h):
    """The axis stretch that makes the rendered silhouette's box (w - 2) x (h - 2) wide: found by bisection."""
    sc0 = spider_scene(k, 1.0)
    if k % 2 == 0:
        return 1.0
    lo, hi = 0.8, 1.6
    for _ in range(14):
        mid = (lo + hi) / 2
        sc = spider_scene(k, mid)
        ys, xs = np.where(sc.col >= 0)
        ext = (xs.max() + 1 - xs.min()) / float(sc.S)
        if ext < w - 2:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def build_bodies(reg):
    check_table()
    imgs = {}
    for k, (bid, w, h, c, A, B, F) in BODY.items():
        img = spider_scene(k, fit_su(k, w, h)).finish(w, h, line_pids=None, thresh=0.5)
        imgs[bid] = img
        reg.add(bid, img, (w, h), True, (10, 11, 12, 13, 14, 15), 'spider body, heading %d (%s)' % (k, 'N NE E SE S SW W NW'.split()[k]))
    return imgs


# ------------------------------------------------------------------------------------------------ the beaten frames
def line_pts(x0, y0, x1, y1):
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    out = []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return out


def beaten(body, bw, bh, c, W, H, feet, bends, curls=None):
    """body = the 1007 picture (a 28 x 28 Img), its thorax centre (9, 9) goes to c.  feet: 8 feet relative to c, in the order
    A1..A4, B1..B4 (A = the lower-left side of the body, B = the upper-right side); bends: knee push per leg (px, positive = away
    from the body's axis).  Legs are black 1-px polylines drawn only OUTSIDE the body (so the body is untouched)."""
    img = Img(W, H, T)
    ox, oy = c[0] - 9, c[1] - 9
    bmask = np.zeros((H, W), dtype=bool)
    for y in range(body.h):
        for x in range(body.w):
            if body.a[y, x] != T:
                bmask[oy + y, ox + x] = True
    A = BODY[7][4]
    B = BODY[7][5]
    att = [(ox + p[0], oy + p[1]) for p in A + B]
    for i, (a, f) in enumerate(zip(att, feet)):
        fx, fy = c[0] + f[0], c[1] + f[1]
        mx, my = (a[0] + fx) / 2.0, (a[1] + fy) / 2.0
        # knee: pushed away from the body centre, perpendicular to the leg
        lx, ly = fx - a[0], fy - a[1]
        n = max(1e-6, np.hypot(lx, ly))
        px, py = -ly / n, lx / n
        cx, cy = mx - c[0], my - c[1]
        if px * cx + py * cy < 0:
            px, py = -px, -py
        kx, ky = mx + px * bends[i], my + py * bends[i]
        pts = [a, (kx, ky), (fx, fy)]
        if curls is not None and curls[i] is not None:
            pts = [a, (kx, ky), (fx, fy), (fx + curls[i][0], fy + curls[i][1])]
        for p, q in zip(pts, pts[1:]):
            for (x, y) in line_pts(p[0], p[1], q[0], q[1]):
                if 0 <= x < W and 0 <= y < H and not bmask[y, x]:
                    img.a[y, x] = 15
    for y in range(body.h):
        for x in range(body.w):
            if body.a[y, x] != T:
                img.a[oy + y, ox + x] = body.a[y, x]
    return img


# feet relative to the thorax centre (A1..A4 = lower-left side front to back, B1..B4 = upper-right side)
BEATEN_FEET = {
    1050: ([(-27, -9), (-25, 8), (-16, 22), (-4, 41), (3, -25), (21, -21), (33, -9), (39, 5)], [5, 5, 5, 5, 5, 5, 5, 5], None),
    1051: ([(-21, -4), (-19, 11), (-11, 25), (2, 37), (6, -15), (22, -11), (34, -2), (40, 9)], [9, 9, 9, 9, 9, 9, 9, 9], None),
    1052: ([(-14, 0), (-12, 14), (-6, 22), (6, 26), (-2, -10), (14, -8), (22, 0), (26, 12)], [6, 6, 6, 6, 6, 6, 6, 6],
           [(6, -5), (6, -6), (5, -6), (-6, -4), (-3, 5), (-5, 5), (-5, 4), (-7, 2)]),
    1053: ([(-14, 8), (-9, 18), (1, 25), (11, 25), (-5, -10), (10, -10), (21, -4), (26, 8)], [-6, -6, -6, -6, -6, -6, -6, -6],
           [(7, 1), (5, -7), (-6, -5), (-6, -4), (4, 5), (-3, 5), (-5, 5), (-6, -3)]),
}


def build_beaten(reg, body7):
    for (bid, w, h, c) in BEATEN:
        feet, bends, curls = BEATEN_FEET[bid]
        img = beaten(body7, 28, 28, c, w, h, feet, bends, curls)
        reg.add(bid, img, (w, h), True, (10, 11, 12, 13, 14, 15), 'spider beaten, frame %d' % (bid - 1050))


# ------------------------------------------------------------------------------------------------ the small spiders (12 x 12)
LEG_ANG = [32, 66, 104, 146]            # degrees from the heading, front leg to hind leg, both sides


def small_spider(k, body=1.0, leg=1.0, dist=0.0):
    """One spider turned: the body faces heading k (0 = north, clockwise 45 degrees); legs 15, body 14 with one 13 highlight."""
    th = np.radians(45.0 * k)
    d = np.array([np.sin(th), -np.cos(th)])            # screen direction (y down)
    n = np.array([-d[1], d[0]])
    c = np.array([5.5, 5.5]) + d * dist
    a = np.zeros((12, 12), dtype=np.int16) - 1
    # legs first (the body covers their roots)
    for side in (1, -1):
        for ang in LEG_ANG:
            ar = np.radians(ang)
            dirv = d * np.cos(ar) + n * np.sin(ar) * side
            # run until the leg reaches the 12 x 12 box: tip on the edge
            tt = min(5.5 / max(abs(dirv[0]), 1e-9), 5.5 / max(abs(dirv[1]), 1e-9)) * leg
            root = c + d * 0.6
            tip = c + dirv * tt
            for (x, y) in line_pts(root[0] - 0.5, root[1] - 0.5, tip[0] - 0.5, tip[1] - 0.5):
                if 0 <= x < 12 and 0 <= y < 12:
                    a[y, x] = 15
    # abdomen and head
    for y in range(12):
        for x in range(12):
            p = np.array([x + 0.5, y + 0.5]) - c
            al = p @ d + 1.7 * body
            ac = p @ n
            hd_ = p @ d - 1.9 * body
            if (al / (2.6 * body)) ** 2 + (ac / (2.2 * body)) ** 2 <= 1.0:
                a[y, x] = 14
            elif (hd_ / (1.5 * body)) ** 2 + (ac / (1.5 * body)) ** 2 <= 1.0:
                a[y, x] = 14
    img = Img(12, 12, T)
    img.a = a
    # a highlight on the abdomen, upper-left of its centre
    ys, xs = np.where(a == 14)
    best = None
    for y, x in zip(ys, xs):
        s = x + y
        if best is None or s < best[0]:
            best = (s, x, y)
    if best:
        hx, hy = best[1], best[2]
        for (x, y) in ((hx + 1, hy + 1),):
            if a[y, x] == 14:
                img.a[y, x] = 13
    return img


def build_small(reg):
    for k in range(8):
        best = None
        for body in (0.9, 1.0, 1.1, 1.2):
            for leg in (0.9, 1.0, 1.1):
                for dist in (-0.5, 0.0, 0.5):
                    im = small_spider(k, body, leg, dist)
                    a = im.a != T
                    if not sp.tight(im):
                        continue
                    nt = int((~a).sum())
                    cx, cy = sp.centroid(im)
                    err = abs(nt - SMALL_TRANSP[k]) / 6.0 + max(abs(cx - 5.5), abs(cy - 5.5)) / 1.0
                    if best is None or err < best[0]:
                        best = (err, im)
        assert best is not None, k
        reg.add(1100 + k, best[1], (12, 12), True, (13, 14, 15), 'small spider for the Map window, heading %d' % k)


# ------------------------------------------------------------------------------------------------ the build
def build(reg):
    imgs = build_bodies(reg)
    build_beaten(reg, imgs[1007])
    build_small(reg)
    ma.build_sneaker(reg)
    ma.build_mower(reg)
    ma.build_marker(reg)
    reg.check(check_pass5)


def opaque(img):
    return img.a != T


def check_pass5(reg):
    I = reg.img
    # --- H: the bodies
    for k, (bid, w, h, c, A, B, F) in BODY.items():
        im = I[bid]
        a = opaque(im)
        assert sp.tight(im), (bid, 'tight')
        assert a[c[1], c[0]], (bid, 'thorax centre opaque')
        used = set(int(v) for v in np.unique(im.a)) - {T}
        assert used <= {10, 11, 12, 13, 14, 15} and not (used & {7, 8, 9}), (bid, used)
        H_, W_ = a.shape
        # nearest transparent pixel / opaque pixel (Chebyshev), the outside of the picture counts as transparent
        def near(p, want_opaque, rmax):
            for r in range(0, rmax + 1):
                for yy in range(p[1] - r, p[1] + r + 1):
                    for xx in range(p[0] - r, p[0] + r + 1):
                        if max(abs(yy - p[1]), abs(xx - p[0])) != r:
                            continue
                        inside = 0 <= xx < W_ and 0 <= yy < H_
                        v = a[yy, xx] if inside else False
                        if v == want_opaque:
                            return r
            return 99
        for p in A + B:
            assert near(p, True, 1) <= 1, (bid, 'attach point', p, 'is more than 1 px from the body')
            assert near(p, False, 3) <= 3, (bid, 'attach point', p, 'is more than 3 px inside the body')
        lim = 2 if k % 2 == 0 else 3
        for p in F:
            assert near(p, True, lim) <= lim, (bid, 'fang base', p, 'too far from the head')
        # mirror symmetry about the heading's axis
        if k in (0, 4):
            fl = a[:, ::-1]
        elif k in (2, 6):
            fl = a[::-1, :]
        elif k in (1, 5):       # axis along the picture's anti-diagonal: reflect by transposing and rotating
            fl = a[::-1, ::-1].T
        else:
            fl = a.T
        agree = (a & fl).sum() / a.sum()
        assert agree >= 0.85, (bid, 'mirror symmetry', agree)
    # --- the beaten frames
    body7 = I[1007]
    b7 = opaque(body7)
    for (bid, w, h, c) in BEATEN:
        im = I[bid]
        assert sp.tight(im), (bid, 'tight')
        assert im.a[c[1], c[0]] != T, (bid, 'centre opaque')
        ox, oy = c[0] - 9, c[1] - 9
        sub = im.a[oy:oy + 28, ox:ox + 28]
        assert (sub[b7] == body7.a[b7]).all(), (bid, 'the body is the same picture in all four frames')
        used = set(int(v) for v in np.unique(im.a)) - {T}
        assert used <= {10, 11, 12, 13, 14, 15}, (bid, used)
    # --- I: the small spiders
    for k in range(8):
        im = I[1100 + k]
        a = opaque(im)
        assert sp.tight(im), (1100 + k, 'tight')
        nt = int((~a).sum())
        assert abs(nt - SMALL_TRANSP[k]) <= 6, (1100 + k, 'transparent pixels', nt, SMALL_TRANSP[k])
        cx, cy = sp.centroid(im)
        assert abs(cx - 5.5) <= 1.0 and abs(cy - 5.5) <= 1.0, (1100 + k, 'centroid', cx, cy)
    # --- the sneaker
    for bid, (w, h) in ((1200, (23, 68)), (1201, (68, 23)), (1202, (23, 68)), (1203, (68, 23))):
        im = I[bid]
        assert (im.w, im.h) == (w, h) and sp.tight(im), (bid, 'sneaker size / tight')
        assert {15, 0, 3}.issubset(set(int(v) for v in np.unique(im.a))), (bid, 'outline, white upper, red cap')
    # --- the mower: point-symmetric, 1211 = 1210 turned by 90 degrees, no transparent pixel, deck reaches all four edges
    m, m2 = I[1210].a, I[1211].a
    assert (m == m[::-1, ::-1]).mean() >= 0.98, '1210 point symmetric'
    assert (np.rot90(m, 1) == m2).mean() >= 0.95, '1211 is 1210 turned by 90 degrees'
    for edge in (m[0], m[-1], m[:, 0], m[:, -1]):
        assert (edge != 9).any(), 'the mower reaches the edge'
    # --- the marker
    mk = I[1400].a
    assert mk[7, 7] != T and int((mk == T).sum()) >= 40
    ys, xs = np.where(mk != T)
    assert (xs.min(), xs.max(), ys.min(), ys.max()) == (1, 13, 1, 13), 'marker fills (1,1)-(13,13)'


def fl_img(im, k):
    a = im.a
    if k in (0, 4):
        return a[:, ::-1]
    if k in (2, 6):
        return a[::-1, :]
    if k in (1, 5):
        return a[::-1, ::-1].T
    return a.T
