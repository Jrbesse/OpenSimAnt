"""screens_scenes: group F (the ant lion scene 9200..9203) and G (the spider scene 12000..12003).
Each scene is ONE drawing program, render(state); the base picture is a state rendered in full and every patch is
the crop of another state's render, so the edges match by construction."""
import math
import random

from screens_lib import Cv, ant, bayer, dither_rect, speckle, pebble, lp, ell_pts, bezier, tapered

# ---------------------------------------------------------------------------------------------------------------
# F. the ant lion
# ---------------------------------------------------------------------------------------------------------------
FW, FH = 200, 160
RIM = 44
PATCHES_F = {9201: (38, 39), 9202: (38, 52), 9203: (38, 52)}
PATCH_SIZE_F = {9201: (136, 121), 9202: (136, 108), 9203: (136, 108)}
STATE_F = {9200: 'rest', 9201: 'rear', 9202: 'left', 9203: 'right'}
PIVOT = (100, 148)


def xl(y):
    return 8 + (y - RIM) * 0.74


def xr(y):
    return 192 - (y - RIM) * 0.74


def sand_background():
    rnd = random.Random(9200)
    cv = Cv(FW, FH, 11)
    # the surface strip: low view of dry ground, darker far away, a few pebbles
    for y in range(0, RIM):
        for x in range(FW):
            c = 11
            if y < 14 and bayer(x, y) < (14 - y) / 14.0 * 0.9:
                c = 10
            v = rnd.random()
            if v < 0.05:
                c = 10
            elif v < 0.075:
                c = 12
            cv.px(x, y, c)
    for (x, y, rx, ry) in [(14, 22, 5, 3), (60, 30, 3, 2), (150, 18, 4, 3), (182, 34, 6, 4), (112, 38, 2.5, 2), (30, 38, 3, 2)]:
        pebble(cv, x, y, rx, ry)
    # a few grass-dry sticks
    cv.line((120, 26), (134, 30), 10, 1)
    cv.line((134, 30), (140, 28), 10, 1)
    # the cross-section: layers
    layers = [(RIM, 58, 11, 0.06), (58, 63, 10, 0.0), (63, 82, 11, 0.12), (82, 88, 14, 0.25), (88, 112, 10, 0.14),
              (112, 118, 13, 0.1), (118, 136, 11, 0.12), (136, 143, 10, 0.1), (143, FH, 14, 0.22)]
    for (ya, yb, c, p) in layers:
        for y in range(ya, yb):
            for x in range(FW):
                wob = int(round(1.4 * math.sin(x / 9.0 + ya) + math.sin(x / 3.1)))
                if ya <= y - wob < yb:
                    pass
                cv.px(x, y, c)
        speckle(cv, (0, ya, FW, yb), [12, 11, 13, 14] if c != 11 else [12, 10, 12], int(FW * (yb - ya) * p), ya, 1)
    # wavy joins between the layers
    for (ya, yb, c, p) in layers[1:]:
        for x in range(FW):
            wob = int(round(1.2 * math.sin(x / 7.0 + ya)))
            cv.px(x, ya + wob, 14 if c in (10, 11) else 15)
    # pebbles in the layers
    for (x, y, rx, ry) in [(12, 94, 6, 4), (26, 125, 5, 3), (172, 100, 7, 4), (186, 128, 4, 3), (20, 150, 8, 4), (168, 152, 6, 4),
                           (44, 76, 3, 2), (160, 72, 3, 2), (60, 100, 3, 2), (140, 124, 4, 2.5), (80, 156, 3, 2)]:
        pebble(cv, x, y, rx, ry)
    # the funnel cavity: far wall, lighter at the top, darker and cooler in the depth
    for y in range(RIM, FH):
        a, b = int(math.ceil(xl(y))), int(xr(y))
        for x in range(a, b + 1):
            t = (y - RIM) / 104.0
            c = 11
            if bayer(x, y) < t * 0.85:
                c = 10
            if t > 0.75 and bayer(x + 2, y + 1) < (t - 0.75) * 2.2:
                c = 14
            if t < 0.25 and bayer(x, y) < (0.25 - t) * 1.6:
                c = 12
            cv.px(x, y, c)
    # strata ripples on the far wall (smile-shaped arcs)
    for k, y0 in enumerate((58, 74, 92, 112, 130)):
        for x in range(10, 191):
            w = (xr(y0) - xl(y0)) / 2.0
            u = (x - 100.0) / max(w, 1)
            if abs(u) < 0.98:
                y = int(round(y0 + 9 * (u * u) * (1 + k * 0.3)))
                if xl(y) + 1 < x < xr(y) - 1:
                    cv.px(x, y, 10 if y < 120 else 14)
    speckle(cv, (30, 50, 170, 140), [12, 10], 140, 77, 1)
    # the funnel's edges: a thin dark lip on both walls
    for y in range(RIM, 149):
        for (xe, d) in ((xl(y), 1), (xr(y), -1)):
            cv.px(int(round(xe)), y, 14)
            cv.px(int(round(xe)) + d, y, 12)
    cv.line((0, RIM - 1), (FW - 1, RIM - 1), 14)
    return cv


def lion(cv, tilt, head, scale, jaws, neck=True, dome=True):
    """The ant lion: dome of body, neck column, flat wedge head with two eyes, two sickle jaws."""
    ca, sa = math.cos(tilt), math.sin(tilt)

    def T(p):
        dx, dy = p[0] - PIVOT[0], p[1] - PIVOT[1]
        return (PIVOT[0] + dx * ca - dy * sa, PIVOT[1] + dx * sa + dy * ca)

    hx, hy = head
    if dome:
        d = [T((100 + 27 * math.cos(t), 150 - 15 * math.sin(t))) for t in [math.pi * i / 20 for i in range(21)]]
        cv.poly(d, fill=10, outline=15)
        for k in range(3):
            a = T((76 + 6 * k + 3, 146 - 3 * k))
            cv.line(a, T((124 - 6 * k - 3, 146 - 3 * k)), 14, 1)
        dither_rect(cv, 80, 138, 124, 148, 10, 11, 0.12)
    if neck:
        ph = [T((84, 150)), T((hx - 13 * scale, hy + 8 * scale)), T((hx + 13 * scale, hy + 8 * scale)), T((116, 150))]
        cv.poly(ph, fill=10, outline=15)
        n = 7
        for i in range(1, n):
            f = i / n
            yy = 150 + (hy + 8 * scale - 150) * f
            hw = (16 + (13 * scale - 16) * f) * 0.96
            cv.line(T((100 - hw, yy)), T((100 + hw, yy)), 14, 1)
        lx0 = [T((86 + (hx - 13 * scale - 86) * f, 148 + (hy + 8 * scale - 148) * f)) for f in (0.1, 0.9)]
        cv.line(lx0[0], lx0[1], 11, 1)
        # bristles
        for f in (0.2, 0.4, 0.6, 0.8):
            for s in (-1, 1):
                b = T((100 + s * (16 + (13 * scale - 16) * f), 150 + (hy + 8 * scale - 150) * f))
                e = T((100 + s * (20 + (13 * scale - 16) * f), 150 + (hy + 8 * scale - 150) * f - 3))
                cv.line(b, e, 15, 1)
    # jaws first (their roots go under the head)
    for pts in jaws:
        q = bezier(*[T(p) for p in pts], n=22)
        for i, (x, y) in enumerate(q):
            w = 6.0 - 5.0 * i / len(q)
            r = w / 2 + 1
            cv.d.ellipse([x - r, y - r, x + r, y + r], fill=15)
        for i, (x, y) in enumerate(q):
            w = 6.0 - 5.0 * i / len(q)
            r = w / 2
            cv.d.ellipse([x - r, y - r, x + r, y + r], fill=10 if i < len(q) * 0.8 else 14)
        for i in range(2, len(q) - 4, 2):
            cv.px(q[i][0] - 1, q[i][1] - 1, 11)
        # a tooth on the inner edge
        i = len(q) // 2
        cv.px(q[i][0], q[i][1], 15)
    # the flat wedge head
    s = scale
    head_pts = [(hx - 17 * s, hy + 1 * s), (hx - 9 * s, hy - 7 * s), (hx + 9 * s, hy - 7 * s), (hx + 17 * s, hy + 1 * s),
                (hx + 11 * s, hy + 9 * s), (hx, hy + 12 * s), (hx - 11 * s, hy + 9 * s)]
    cv.poly([T(p) for p in head_pts], fill=10, outline=15)
    hl = [(hx - 12 * s, hy), (hx - 7 * s, hy - 5 * s), (hx + 2 * s, hy - 5 * s), (hx - 4 * s, hy + 2 * s)]
    cv.poly([T(p) for p in hl], fill=11)
    sh = [(hx + 17 * s, hy + 1 * s), (hx + 11 * s, hy + 9 * s), (hx, hy + 12 * s), (hx + 4 * s, hy + 3 * s)]
    cv.poly([T(p) for p in sh], fill=14)
    cv.poly([T(p) for p in head_pts], outline=15)
    for sx in (-1, 1):                              # the eyes: red, small, side by side
        e = T((hx + sx * 8 * s, hy - 1 * s))
        cv.ell(e[0], e[1], 2.2 * max(s, 0.8), 2.2 * max(s, 0.8), fill=3, outline=15)
    for sx in (-1, 1):                              # horns above the eyes
        b = T((hx + sx * 11 * s, hy - 6 * s))
        t = T((hx + sx * 16 * s, hy - 12 * s))
        cv.line(b, t, 15, 2)


def render_F(state):
    cv = sand_background()
    bg = cv.copy()
    if state in ('rest', 'rear'):
        ant(cv, 100, 74, 0.15, 30, body=1, shade=2, hi=None, legcol=15, legw=1, antw=1, eyes=True)
    if state == 'rest':
        lion(cv, 0.0, (100, 140), 0.72, [
            [(90, 141), (80, 141), (75, 130), (84, 120)],
            [(110, 141), (120, 141), (125, 130), (116, 120)]], neck=False, dome=False)
    elif state == 'rear':
        lion(cv, 0.0, (100, 100), 1.0, [
            [(86, 98), (58, 98), (56, 72), (74, 62)],
            [(114, 98), (142, 98), (144, 72), (126, 62)]])
    else:
        tilt = -0.30 if state == 'left' else 0.30
        lion(cv, tilt, (100, 104), 1.0, [
            [(88, 99), (74, 86), (86, 72), (102, 66)],
            [(112, 99), (126, 86), (114, 72), (98, 66)]])
        # the caught ant: only a leg and an antenna stick out between the jaws
        ca, sa = math.cos(tilt), math.sin(tilt)

        def T(p):
            dx, dy = p[0] - PIVOT[0], p[1] - PIVOT[1]
            return (PIVOT[0] + dx * ca - dy * sa, PIVOT[1] + dx * sa + dy * ca)
        for pts in ([(100, 68), (95, 60), (90, 63)], [(100, 68), (106, 60), (111, 64)], [(100, 67), (102, 57), (106, 55)]):
            cv.path([T(p) for p in pts], 15, 1)
        t = T((100, 66))
        cv.px(t[0], t[1] + 1, 2)
    # the cross-section below the pit's floor is solid sand again (the body is buried)
    cv.im.paste(bg.im.crop((0, 148, FW, FH)), (0, 148))
    return cv


def render_F_all():
    r = {s: render_F(s) for s in ('rest', 'rear', 'left', 'right')}
    out = {9200: r['rest']}
    for pid, (px, py) in PATCHES_F.items():
        w, h = PATCH_SIZE_F[pid]
        out[pid] = r[STATE_F[pid]].crop(px, py, px + w, py + h)
    return out, r


# ---------------------------------------------------------------------------------------------------------------
# G. the spider
# ---------------------------------------------------------------------------------------------------------------
GW, GH = 189, 171
PATCH_G = (46, 77, 144, 157)
STATE_G = {12000: 'open', 12001: 'open', 12002: 'half', 12003: 'closed'}
SKY = 5


def mirror(pts, w=GW):
    return [(w - 1 - x, y) for x, y in pts]


def leg(cv, pts):
    n = len(pts)
    path = []
    for a, b in zip(pts, pts[1:]):
        for i in range(12):
            t = i / 12.0
            path.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    path.append(pts[-1])
    m = len(path)
    for i, (x, y) in enumerate(path):
        w = 6.0 - 3.5 * i / m
        r = w / 2 + 1
        cv.d.ellipse([x - r, y - r, x + r, y + r], fill=15)
    for i, (x, y) in enumerate(path):
        w = 6.0 - 3.5 * i / m
        r = w / 2
        cv.d.ellipse([x - r, y - r, x + r, y + r], fill=14)
    for i in range(0, m - 2, 3):          # a lit edge along the top
        cv.px(path[i][0], path[i][1] - 1, 13)
    for (x, y) in pts[1:-1]:              # brown joints
        cv.ell(x, y, 3.2, 3.2, fill=10, outline=15)
        cv.px(x - 1, y - 1, 11)


def render_G(state):
    cv = Cv(GW, GH, SKY)
    cv.rect(0, 162, GW, GH, 6)
    r = random.Random(12000)
    px0, py0, px1, py1 = PATCH_G
    for _ in range(26):
        x, y = r.randrange(2, GW - 2), r.randrange(2, 155)
        if not (px0 - 5 <= x < px1 + 5 and py0 - 5 <= y < py1 + 5) and cv.get(x, y) == SKY:
            cv.px(x, y, r.choice([0, 12, 12]))
    legsL = [
        [(62, 76), (38, 50), (22, 22), (6, 36)],
        [(58, 86), (28, 66), (8, 48), (3, 74)],
        [(58, 97), (22, 90), (6, 82), (4, 108)],
        [(62, 108), (32, 116), (16, 136), (8, 162)],
    ]
    for pts in legsL:
        leg(cv, pts)
        leg(cv, mirror(pts))
    # the abdomen peeking above the head: big, glossy, hairless
    cv.ell(94, 40, 35, 32, fill=15)
    cv.ell(94, 40, 33, 30, fill=14)
    cv.ell(87, 33, 25, 22, fill=15)
    cv.ell(86, 32, 23, 20, fill=14)
    cv.ell(81, 25, 11, 8, fill=13)
    cv.ell(78, 22, 4, 3, fill=12)
    cv.px(77, 21, 0)
    cv.px(78, 21, 0)
    for k, (y, wd) in enumerate([(44, 8), (54, 12), (63, 8)]):    # brown chevrons
        cv.path([(94 - wd, y - 4), (94, y), (94 + wd, y - 4)], 10, 2)
    # the head (cephalothorax)
    cv.ell(94, 90, 39, 31, fill=15)
    cv.ell(94, 89, 37, 29, fill=14)
    cv.ell(94, 91, 35, 27, fill=15)
    cv.ell(80, 74, 14, 8, fill=13)
    cv.ell(76, 72, 6, 3, fill=12)
    # eight small eyes in two rows
    for (x, y, rr) in [(74, 80, 2), (86, 79, 2), (102, 79, 2), (114, 80, 2)]:
        cv.ell(x, y, rr, rr, fill=12)
        cv.px(x - 1, y - 1, 0)
    for (x, y, rr) in [(68, 92, 2.5), (83, 92, 3.6), (105, 92, 3.6), (120, 92, 2.5)]:
        cv.ell(x, y, rr, rr, fill=12)
        cv.px(x - 1, y - 1, 0)
        cv.px(x, y - 1, 0)
    cv.line((88, 99), (100, 99), 13)
    # the jaws (chelicerae and fangs) in the state's pose
    spread = {'open': 8, 'half': 4, 'closed': 0}[state]
    for s in (-1, 1):
        cx0 = 94 + s * (6 + spread)
        cv.poly([(cx0 - 6, 112), (cx0 + 6, 112), (cx0 + 5 + s * 1, 134), (cx0 - 5 + s * 1, 134)], fill=14, outline=15)
        cv.line((cx0 - 4, 114), (cx0 - 4, 131), 13)
        cv.rect(cx0 - 3, 118, cx0 + 3, 120, 10)
    tip_off = {'open': 30, 'half': 15, 'closed': -4}[state]
    for s in (-1, 1):
        bx = 94 + s * (6 + spread) + s * 1
        tx = 94 + s * tip_off
        ctrl1 = (bx + s * 6, 142)
        ctrl2 = (tx + s * 8, 147)
        pts = bezier((bx, 133), ctrl1, ctrl2, (tx, 151), n=22)
        for i, (x, y) in enumerate(pts):
            w = 9.0 - 8.0 * i / len(pts)
            rr = w / 2 + 1
            cv.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=15)
        for i, (x, y) in enumerate(pts):
            w = 9.0 - 8.0 * i / len(pts)
            rr = max(0.6, w / 2)
            cv.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=14 if i < len(pts) * 0.42 else 2)
    return cv


def render_G_all():
    r = {s: render_G(s) for s in ('open', 'half', 'closed')}
    out = {12000: r['open']}
    for pid in (12001, 12002, 12003):
        out[pid] = r[STATE_G[pid]].crop(*PATCH_G)
    return out, r
