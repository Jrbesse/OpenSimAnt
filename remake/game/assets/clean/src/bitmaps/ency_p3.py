"""ency_p3.py - pass 3: the parts of the ant: 210 head, 213 antennae, 220 thorax and legs, 230 inside of the body."""
import math

from ency_lib import (Cv, catmull, grad, W_, K_, LT, MD, DK, T1, H1, H2, HX, DOT, lvl, Tone, BAYER)


# ------------------------------------------------------------------------------------------------ shared helpers
def cap(cv, p0, p1, w, tone=W_, line=1, dash=None):
    """a capsule (rounded tube) between two points, w px wide"""
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    cv.ell(mx, my, ln / 2 + w * 0.35, w / 2, tone, line, rot=ang, dash=dash)


def resample(pts, step):
    """points along a polyline at (about) equal arclength"""
    out = [pts[0]]
    acc = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        d = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while d - t >= step - acc:
            t += step - acc
            acc = 0.0
            out.append((x0 + (x1 - x0) * t / d, y0 + (y1 - y0) * t / d))
        acc += d - t
    return out


def mirror(pts, axis):
    return [(2 * axis - x, y) for x, y in pts]


def shrink(pts, k, c=None):
    if c is None:
        c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return [(c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k) for x, y in pts]


def grape(cv, cx, cy, n=5, r=2.0, spread=4.0):
    """a small cluster of round gland cells"""
    pts = [(cx, cy)] + [(cx + spread * math.cos(2 * math.pi * k / (n - 1) + 0.5), cy + spread * 0.8 * math.sin(2 * math.pi * k / (n - 1) + 0.5))
                        for k in range(n - 1)]
    for (x, y) in pts:
        cv.ell(x, y, r, r, LT, 1, n=10)


# ------------------------------------------------------------------------------------------------------------ 210
def head210():
    cv = Cv(153, 137, 'SHARED_210')
    # --- the labels first (the head is drawn around them)
    # --- the head capsule (3/4 front view): broad at the top, narrowing to the mouth
    cap_pts = [(66, 26), (94, 19), (122, 26), (142, 44), (146, 68), (138, 92), (122, 104), (106, 108), (94, 110), (82, 108),
               (66, 104), (50, 92), (42, 68), (46, 44)]
    # the right antenna first (it lies behind the cheek on that side)
    def antenna(sock, elbow, tail, flip=False):
        cap(cv, sock, elbow, 4)
        seg = resample(catmull([elbow] + tail, closed=False, n=5), 4.6)
        cv.pline(seg, 1, None, 2)
        for (x, y) in seg[1::1]:
            pass
        # segment joints: short white gaps across the thick line, the last segment a club
        for k in range(1, len(seg) - 1):
            x, y = seg[k]
            px, py = seg[k + 1][0] - seg[k - 1][0], seg[k + 1][1] - seg[k - 1][1]
            n = math.hypot(px, py) or 1
            nx, ny = -py / n, px / n
            if k % 1 == 0:
                cv.put(x + nx * 0.6, y + ny * 0.6, 0)
        cv.ell(seg[-1][0], seg[-1][1], 2.5, 2.0, K_, 1, n=10)
    antenna((106, 72), (143, 76), [(149, 90), (147, 104), (141, 118)])
    cv.poly(cap_pts, grad(94, 64, 55, 2, 8), 1, smooth=6)
    # hairs round the outline
    P = catmull(cap_pts, True, 6)
    for k in range(0, len(P), 5):
        x, y = P[k]
        if y < 100:
            dx, dy = x - 94, y - 64
            n = math.hypot(dx, dy) or 1
            cv.line((x, y), (x + dx / n * 3, y + dy / n * 3), 1)
    # compound eyes: cross hatched ovals with a dark rim
    for (cx, cy, rot) in ((58, 46, -0.25), (130, 46, 0.25)):
        cv.ell(cx, cy, 14, 18, HX, 1, rot=rot)
        cv.ell(cx, cy, 14, 18, None, 1, rot=rot)
        cv.ell(cx - 4, cy - 7, 3, 4, W_, None, rot=rot, n=10)
    # ocelli
    for (x, y) in ((94, 30), (87, 38), (101, 38)):
        cv.ell(x, y, 3, 3, W_, 1, n=12)
        cv.put(x, y, 1)
    # frontal line and the clypeus
    cv.pline(catmull([(94, 40), (94, 56), (92, 70)], False, 4), 1, (3, 2))
    cv.ell(94, 87, 20, 8, LT, 1)
    cv.pline([(80, 87), (94, 91), (108, 87)], 1)
    # antenna sockets and the left antenna (it leaves the head on the left)
    for sx in (82, 106):
        cv.ell(sx, 72, 5, 4, W_, 1, n=12)
        cv.put(sx, 72, 1)
    cap(cv, (82, 72), (46, 76), 4)
    seg = resample(catmull([(46, 76), (34, 79), (22, 85), (14, 91), (9, 95)], closed=False, n=5), 4.6)
    cv.pline(seg, 1, None, 2)
    for k in range(1, len(seg) - 1):
        x, y = seg[k]
        px, py = seg[k + 1][0] - seg[k - 1][0], seg[k + 1][1] - seg[k - 1][1]
        n = math.hypot(px, py) or 1
        cv.put(x - py / n * 0.6, y + px / n * 0.6, 0)
    cv.ell(seg[-1][0], seg[-1][1], 2.5, 2.0, K_, 1, n=10)
    # maxillae (small, behind the mandibles) with their palps
    for (cx, cy, s) in ((68, 108, 1), (120, 108, -1)):
        cv.ell(cx, cy, 6, 5, LT, 1, rot=0.5 * s)
        for k in range(3):
            cv.line((cx - 5 * s + k * 2 * s, cy + 4), (cx - 7 * s + k * 3 * s, cy + 9), 1)
    # mandibles (toothed, slightly open, meeting below the clypeus)
    lm = [(70, 95), (92, 97), (94, 108), (92, 120), (86, 113), (84, 107), (76, 103)]
    for m, ax in ((lm, None), (mirror(lm, 94), None)):
        cv.poly(m, LT, 1)
    # teeth: small notches on the inner edge of each mandible
    for (x0, y0, x1, y1) in ((93, 100, 91, 120), ):
        for t in (0.15, 0.4, 0.65, 0.88):
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            cv.poly([(x, y - 2), (x - 4, y), (x, y + 2)], K_, 1)
            cv.poly([(2 * 94 - x, y - 2), (2 * 94 - x + 4, y), (2 * 94 - x, y + 2)], K_, 1)
    # boxes last (they erase what lies under them), then leaders
    cv.box('eyes', (6, 10, 40, 21), 'Eyes')
    cv.box('ocelli', (105, 1, 136, 14), 'Ocelli')
    cv.box('maxillae', (16, 98, 60, 113), 'Maxillae')
    cv.box('antennae', (3, 124, 52, 135), 'Antennae')
    cv.box('mouth', (80, 123, 129, 134), 'Mouth')
    cv.leader('eyes', (24, 21), [], (57, 42), (46, 28, 74, 66))
    cv.leader('ocelli', (110, 14), [(110, 22)], (100, 34), (82, 26, 106, 42))
    cv.leader('maxillae', (60, 106), [], (65, 107), (60, 102, 80, 116))
    cv.leader('antennae', (10, 123), [], (10, 94), (6, 76, 48, 98))
    cv.leader('mouth', (104, 122), [], (104, 113), (76, 100, 112, 124))
    return cv, 'the head of a worker, three-quarter front view: eyes, ocelli, antennae, mandibles, maxillae (5 labels)'


# ------------------------------------------------------------------------------------------------------------ 213
def antennae213():
    cv = Cv(235, 45, 'SHARED_213')
    cv.cut_rows = [0, 1]

    def one(sock, elbow, curve, off, behind):
        ox, oy = off
        s = (sock[0] + ox, sock[1] + oy)
        e = (elbow[0] + ox, elbow[1] + oy)
        cap(cv, s, e, 6)
        pts = catmull([e] + [(x + ox, y + oy) for x, y in curve], closed=False, n=8)
        seg = resample(pts, 15.0)
        n = len(seg)
        for k in range(n - 1):
            a, b = seg[k], seg[k + 1]
            w = 4.6 if k < n - 2 else 6.2
            if k == n - 2:
                b = (b[0] + (b[0] - a[0]) * 0.3, b[1] + (b[1] - a[1]) * 0.3)
            cap(cv, a, b, w, W_)
        # fine hairs and the small sense pits at the tip
        for k in range(1, n - 1):
            x, y = seg[k]
            px, py = seg[k + 1][0] - seg[k - 1][0], seg[k + 1][1] - seg[k - 1][1]
            m = math.hypot(px, py) or 1
            nx, ny = -py / m, px / m
            cv.line((x + nx * 3, y + ny * 3), (x + nx * 6 + px / m, y + ny * 6 + py / m), 1)
        tx, ty = seg[-1]
        for k in range(-1, 2):
            cv.put(tx + 2 + k * 2, ty - 1 + (k % 2), 1)
        return seg

    # the antenna behind first, a little lower and shorter
    one((13, 34), (62, 16), [(100, 21), (150, 30), (190, 38)], (6, 3), True)
    # the near antenna: scape, elbow, funiculus of 11 segments
    one((11, 27), (66, 7), [(108, 11), (156, 19), (196, 27), (226, 35)], (0, 0), False)
    # the piece of head at the left edge, drawn over the antenna roots
    cv.ell(-4, 31, 20, 20, grad(8, 30, 20, 3, 9), 1)
    for (sx, sy) in ((11, 27), (13, 37)):
        cv.ell(sx + 1, sy, 4, 3.5, W_, 1, n=12)
    for k in range(5):
        a = -1.2 + k * 0.5
        cv.line((16 * math.cos(a) - 4, 31 + 19 * math.sin(a)), (19 * math.cos(a) - 4 + 3, 31 + 22 * math.sin(a)), 1)
    return cv, 'the antennae: a piece of head at the left edge and two elbowed antennae (scape, elbow, 11-segment chain)'


# ------------------------------------------------------------------------------------------------------------ 220
def leg220(cv, hip, chain, near=True):
    """chain: list of (angle in degrees, length) for coxa, trochanter, femur, tibia, then the tarsus direction/length;
    drawn as outlined tubes; returns the toe"""
    x, y = hip
    pts = [hip]
    for ang, ln in chain:
        a = math.radians(ang)
        x, y = x + ln * math.cos(a), y + ln * math.sin(a)
        pts.append((x, y))
    tone_f = LT if near else W_
    widths = (6.2, 4.0, 5.6, 4.2)
    dash = None
    tones = (MD, W_, tone_f, W_)
    for k in range(4):
        cap(cv, pts[k], pts[k + 1], widths[k], tones[k], 1, dash)
    # spurs at the end of the tibia
    ax, ay = pts[4]
    a = math.radians(chain[3][0])
    cv.line((ax, ay), (ax + 4 * math.cos(a + 1.0), ay + 4 * math.sin(a + 1.0)), 1)
    cv.line((ax, ay), (ax + 4 * math.cos(a - 1.0), ay + 4 * math.sin(a - 1.0)), 1)
    # tarsus: five small joints
    ang, ln = chain[4]
    a = math.radians(ang)
    seg_len = ln / 5.0
    px, py = ax, ay
    for k in range(5):
        qx, qy = px + seg_len * math.cos(a + 0.03 * k), py + seg_len * math.sin(a + 0.03 * k)
        w = 3.0 - 0.2 * k
        cap(cv, (px, py), (qx, qy), w, W_)
        px, py = qx, qy
    # foot: a small pad and two hooked claws
    cv.ell(px, py, 1.8, 1.8, W_, 1, n=8)
    for s in (-1, 1):
        cv.line((px, py), (px + 4 * math.cos(a + 0.6 * s), py + 4 * math.sin(a + 0.6 * s)), 1)
        cv.put(px + 5 * math.cos(a + 0.9 * s), py + 5 * math.sin(a + 0.9 * s), 1)
    return (px, py)


def thorax220():
    cv = Cv(258, 93, 'SHARED_220')
    xt0, S = 93.0, 213.0
    top = [(0.0, -0.030), (0.10, -0.066), (0.28, -0.080), (0.50, -0.060), (0.72, -0.070), (0.90, -0.046), (1.0, -0.018)]
    bot = [(1.0, 0.022), (0.82, 0.046), (0.5, 0.056), (0.18, 0.052), (0.0, 0.032)]
    tl = 0.30
    cy = 30.0
    P = [(xt0 + u * tl * S, cy + y * S) for u, y in top + bot]
    hips = [(xt0 + u * tl * S, cy + 0.05 * S - 1) for u in (0.22, 0.52, 0.80)]
    # the far legs first (behind)
    far = [
        [(115, 6), (125, 4), (172, 20), (68, 22), (80, 12)],
        [(100, 6), (110, 4), (140, 20), (62, 21), (70, 11)],
        [(60, 6), (50, 4), (-25, 24), (62, 24), (80, 11)],
    ]
    # (angles measured with 0 = right, 90 = down)
    near = [
        [(130, 7), (140, 4), (185, 22), (105, 24), (110, 12)],
        [(95, 6), (120, 3), (165, 20), (60, 20), (75, 11)],
        [(60, 7), (50, 4), (10, 26), (85, 24), (95, 11)],
    ]
    far = [
        [(120, 6), (130, 4), (200, 20), (125, 22), (100, 11)],
        [(100, 6), (115, 4), (130, 19), (70, 21), (95, 10)],
        [(70, 6), (60, 4), (-18, 24), (60, 24), (78, 11)],
    ]
    for i in (0, 1, 2):
        h = (hips[i][0] + 3, hips[i][1] - 3)
        leg220(cv, h, far[i], False)
    # the thorax
    cv.poly(P, grad(xt0 + 32, cy, 40, 3, 9), 1, smooth=6)
    for u in (0.30, 0.64):          # sutures
        x = xt0 + u * tl * S
        cv.pline([(x, cy - 0.060 * S), (x - 2, cy - 0.02 * S), (x, cy + 0.03 * S)], 1, (2, 1))
    cv.ell(xt0 + 0.42 * tl * S, cy - 0.01 * S, 1.8, 1.4, K_, 1, n=8)      # a spiracle
    for u in (0.1, 0.35, 0.6, 0.85):                                      # a few hairs
        x = xt0 + u * tl * S
        yt = cy - 0.07 * S
        cv.line((x, yt + 1), (x - 1, yt - 3), 1)
    # near legs
    toes = []
    for i in (0, 1, 2):
        toes.append(leg220(cv, hips[i], near[i], True))
    # coxae: round sockets on the underside
    for h in hips:
        cv.ell(h[0], h[1] - 1, 4, 3.2, MD, 1, n=10)
    # neck at the left and the waist at the right, both cut across
    cv.poly([(xt0 + 1, cy - 5), (xt0 - 8, cy - 4), (xt0 - 8, cy + 6), (xt0 + 1, cy + 7)], LT, 1)
    cv.pline([(xt0 - 8, cy - 4), (xt0 - 10, cy), (xt0 - 8, cy + 2), (xt0 - 10, cy + 6)], 1)
    xe = xt0 + tl * S
    cv.poly([(xe - 2, cy - 2), (xe + 3, cy - 13), (xe + 11, cy - 14), (xe + 15, cy - 3), (xe + 18, cy + 0), (xe + 18, cy + 6),
             (xe + 10, cy + 8), (xe - 2, cy + 6)], DK, 1, smooth=3)
    cv.pline([(xe + 18, cy), (xe + 20, cy + 2), (xe + 18, cy + 4), (xe + 20, cy + 6)], 1)
    # ---- detail 1: the foot's two curved claws (a circle at the left)
    c1 = (30, 28)
    cv.ell(c1[0], c1[1], 22, 22, W_, 1, n=60)
    cap(cv, (c1[0] - 8, c1[1] - 18), (c1[0] - 1, c1[1] - 5), 7, W_)
    cap(cv, (c1[0] - 1, c1[1] - 5), (c1[0] + 3, c1[1] + 1), 6, W_)
    cv.ell(c1[0] + 3, c1[1] + 3, 4, 3, MD, 1, n=12)                 # the pad
    for s in (-1, 1):
        pts = [(c1[0] + 3 + 2 * s, c1[1] + 1), (c1[0] + 3 + 9 * s, c1[1] + 6), (c1[0] + 3 + 13 * s, c1[1] + 12), (c1[0] + 3 + 11 * s, c1[1] + 17)]
        cv.pline(catmull(pts, False, 5), 1, None, 2)
    # ---- detail 2: the foreleg's cleaning notch (a circle at the right)
    c2 = (228, 28)
    cv.ell(c2[0], c2[1], 22, 22, W_, 1, n=60)
    # the tibia end and its spur, the first tarsal joint with a notch lined with a comb of bristles
    cap(cv, (c2[0] - 17, c2[1] + 12), (c2[0] - 2, c2[1] - 2), 11, W_)
    cap(cv, (c2[0] + 1, c2[1] - 4), (c2[0] + 14, c2[1] - 15), 8, W_)
    cv.pline(catmull([(c2[0] - 4, c2[1] - 1), (c2[0] - 1, c2[1] + 7), (c2[0] + 4, c2[1] + 10)], False, 4), 1, None, 2)   # the spur
    cv.ell(c2[0] + 6, c2[1] - 4, 6, 6, W_, 1, rot=0, n=16)           # the notch
    for k in range(7):
        a = 0.2 + k * 0.5
        bx, by = c2[0] + 6 + 6 * math.cos(a), c2[1] - 4 + 6 * math.sin(a)
        cv.line((bx, by), (bx - 2.2 * math.cos(a), by - 2.2 * math.sin(a)), 1)
    # plain captions
    cv.caption(10, 54, 'claws')
    cv.caption(206, 54, 'notch')
    cv.extra['thorax'] = (xt0, cy)
    return cv, 'the thorax from the side with all six legs in detail; two circled details: the foot\'s claws and the cleaning notch'


# ------------------------------------------------------------------------------------------------------------ 230
def inside230():
    cv = Cv(252, 103, 'SHARED_230')
    cv.cut_rows = [0]
    cv.box('pouch', (1, 73, 54, 97), ['Mouth', 'pouch'])
    cv.box('crop', (104, 2, 130, 15), 'Crop')
    cv.box('midgut', (198, 3, 233, 17), 'Midgut')
    head = [(4, 50), (8, 34), (20, 26), (36, 28), (46, 38), (47, 56), (38, 66), (20, 68), (9, 62)]
    thorax = [(44, 38), (54, 30), (66, 28), (78, 32), (91, 40), (93, 50), (85, 58), (66, 62), (52, 60), (44, 56)]
    gaster = [(98, 42), (108, 30), (130, 21), (160, 18), (195, 20), (225, 28), (246, 42), (249, 50), (246, 58), (225, 70), (195, 76),
              (160, 78), (130, 76), (108, 66), (98, 54)]
    for pts, k in ((gaster, 0.95), (thorax, 0.88), (head, 0.86)):
        cv.poly(pts, MD, 1, smooth=5)
        c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        cv.poly(shrink(pts, k, c), W_, 1, smooth=5)
    # waist: a narrow tube with its node
    cv.poly([(91, 41), (95, 36), (99, 36), (101, 42), (101, 50), (96, 52), (91, 51)], MD, 1, smooth=3)
    # mandibles at the mouth
    cv.poly([(6, 54), (0, 62), (4, 70), (8, 62)], K_, 1)
    # the foregut: mouth cavity -> pharynx -> oesophagus through the thorax and the waist -> crop
    gut = catmull([(7, 57), (16, 53), (28, 46), (44, 44), (70, 45), (92, 46), (101, 46)], False, 5)
    up = [(x, y - 2) for x, y in gut]
    dn = [(x, y + 2) for x, y in gut]
    cv.pline(up, 1)
    cv.pline(dn, 1)
    # the mouth pouch (infrabuccal pocket), a small sac below the mouth opening
    cv.ell(17, 62, 6, 5, LT, 1, n=16)
    cv.pline([(14, 57), (15, 58)], 1)
    # head: brain and glands
    cv.ell(28, 36, 7, 6, DOT, 1, n=16)
    grape(cv, 36, 56, 5)
    # thorax: muscle blocks and a gland
    for (x, y, rx, ry) in ((60, 38, 9, 5), (78, 38, 7, 5), (66, 54, 12, 4)):
        cv.ell(x, y, rx, ry, H1, 1, n=16)
    grape(cv, 80, 55, 5)
    # the crop: a big thin-walled storage sac in the front of the gaster
    cv.ell(126, 47, 27, 21, LT, 1, n=40)
    cv.ell(126, 47, 27, 21, None, 1, n=40)
    cv.pline(catmull([(112, 38), (126, 34), (140, 38)], False, 4), 1, (1, 2))
    # the valve between crop and midgut, then the coiled midgut
    cv.ell(155, 47, 4, 4, W_, 1, n=12)
    coil = catmull([(158, 46), (168, 33), (180, 56), (190, 31), (202, 58), (213, 32), (224, 56), (234, 38), (238, 50)], False, 8)
    cv.pline(coil, 1, None, 3)
    sh = [(x, y) for x, y in coil]
    cv.pline(sh, 0, None, 1)
    # hindgut to the tail, a gland and the sting
    cv.pline(catmull([(238, 50), (242, 55), (244, 52), (247, 52)], False, 4), 1)
    grape(cv, 232, 66, 5, 2.0, 4)
    cv.poly([(246, 47), (251, 51), (246, 55)], K_, 1)
    # the dorsal vessel as a dotted line, and a few fine segment lines on the gaster wall
    cv.pline([(100, 27), (150, 24), (200, 25), (232, 31)], 1, (1, 3))
    # leaders
    cv.leader('pouch', (20, 72), [], (17, 63), (11, 57, 24, 68))
    cv.leader('crop', (117, 15), [], (117, 30), (99, 26, 154, 70))
    pk = min(coil, key=lambda p: abs(p[0] - 212) + abs(p[1] - 33))
    cv.leader('midgut', (212, 17), [(212, 24)], (int(round(pk[0])) - 1, int(round(pk[1])) - 1), (158, 24, 240, 62))
    return cv, 'lengthwise cut-away of the body: mouth pouch, foregut, crop, coiled midgut, glands, sting (3 labels)'


def build():
    return {210: head210(), 213: antennae213(), 220: thorax220(), 230: inside230()}
