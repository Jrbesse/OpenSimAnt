"""Groups F (Behavior Control 4600 / Caste Control 4620 and their help overlays 4601 / 4621) and G (History window 16000
and its help overlay 16001).  See README.md."""
import math
from collections import deque
from uilib import *
from grp_deh import label_button


# =============================================================================================================
# F. Behavior Control and Caste Control
# =============================================================================================================
def _tri_geom(rect):
    """Apex and base corners of the control triangle, in continuous pixel coordinates (spec: apex at the middle of the
    top edge, base corners at (left + 2, bottom - 2) and (right - 2, bottom - 2))."""
    x0, y0, x1, y1 = rect
    return (x0 + (x1 - x0) / 2.0, float(y0)), (x0 + 2.0, y1 - 2.0), (x1 - 2.0, y1 - 2.0)


def _edge_dists(rect, x, y):
    """Signed distances (positive = inside) of the pixel centre to the left, right and bottom edges."""
    A, B, C = _tri_geom(rect)
    p = (x + 0.5, y + 0.5)
    out = []
    for P, Q in ((A, B), (C, A), (B, C)):          # left, right, bottom
        ex, ey = Q[0] - P[0], Q[1] - P[1]
        n = math.hypot(ex, ey)
        out.append((ex * (p[1] - P[1]) - ey * (p[0] - P[0])) / n)
    cen = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)
    s = 1.0
    P, Q = A, B
    if ((Q[0] - P[0]) * (cen[1] - P[1]) - (Q[1] - P[1]) * (cen[0] - P[0])) < 0:
        s = -1.0
    return [d * s for d in out]


def draw_triangle(o, rect):
    """White interior, 1-px black line, 3-px raised edge (white on the left side, grey 13 / 14 on the right and the
    bottom) outside the interior."""
    x0, y0, x1, y1 = rect
    for y in range(y0 - 12, y1 + 6):
        for x in range(x0 - 12, x1 + 12):
            d = _edge_dists(rect, x, y)
            m = min(d)
            if m >= 0:
                o.px(x, y, 0)
            elif m >= -1:
                o.px(x, y, INK)
            elif m >= -4:
                k = d.index(m)
                if k == 0:
                    o.px(x, y, 0 if m >= -3 else 12)
                else:
                    o.px(x, y, SH if m >= -3 else DSH)


def corner_box(o, hit, val, colour, label):
    """A framed box: 2-px frame in the bar's colour hugging the white value rectangle, label (white background) in its
    upper half.  The frame may lie 1-2 px outside the game's hit rectangle where the value rectangle touches its edge."""
    x0 = min(hit[0] + 2, val[0])
    x1 = max(hit[2] - 2, val[2])
    top = hit[1] - 1
    o.rect(x0 - 2, top, x1 + 2, val[3] + 2, colour)
    o.rect(x0, top + 2, x1, val[3], 0)
    ty = hit[1] + 1
    cx = (x0 + x1) // 2
    end = text_c(o, cx, ty, label, SMALL, INK)
    w = SMALL.width(label)
    assert cx - w // 2 >= x0 and end <= x1, (label, x0, x1, cx - w // 2, end)
    ink_rows = np.where((o.a[ty:val[1] + 3, x0:x1] == INK).any(axis=1))[0]
    assert ink_rows.max() + ty < val[1], ('label touches the value rectangle', label)
    return (x0 - 2, top, x1 + 2, val[3] + 2)


CFG = {
    4600: dict(
        auto=(5, 5, 46, 16), manual=(4, 20, 46, 32), sets=[(4, 38, 46, 50), (4, 54, 46, 66), (4, 70, 47, 82)],
        help=(14, 88, 39, 100), tri=(48, 38, 159, 134), well=(167, 8, 199, 80), bars=(167, 179, 191),
        boxes=[((86, 6, 121, 26), (87, 16, 119, 25), 8, 'Forage'),
               ((21, 144, 56, 164), (22, 154, 54, 163), 11, 'Dig'),
               ((154, 144, 189, 164), (155, 153, 187, 162), 7, 'Nurse')],
        letters='FDN', ox=40, oy=2, size=(168, 168), lay=(164, 164)),
    4620: dict(
        auto=(4, 5, 46, 16), manual=(4, 21, 46, 32), sets=[(4, 39, 46, 50), (4, 55, 46, 66), (4, 71, 46, 82)],
        help=(14, 89, 39, 100), tri=(48, 37, 157, 133), well=(168, 8, 198, 81), bars=(168, 180, 192),
        boxes=[((80, 6, 127, 26), (82, 14, 124, 26), 4, 'Breeders'),
               ((15, 144, 62, 164), (17, 152, 59, 164), 6, 'Workers'),
               ((148, 144, 195, 164), (150, 152, 192, 164), 2, 'Soldiers')],
        letters='BWS', ox=-35, oy=1, size=(175, 175), lay=(169, 169)),
}
# NB: for 4620 the overlay origin is (+35, -1) relative to the panel: overlay = panel - (35, -1) -> ox = 35, oy = -1
CFG[4620]['ox'], CFG[4620]['oy'] = 35, -1


def make_panel(reg, bid, what):
    c = CFG[bid]
    o = Img(210, 170, FACE)
    # buttons
    label_button(o, c['auto'], 'Auto')
    label_button(o, c['manual'], 'Manual')
    reg.inverted(bid, c['auto'], FACE, INK, 'Auto')
    reg.inverted(bid, c['manual'], FACE, INK, 'Manual')
    for i, r in enumerate(c['sets']):
        label_button(o, r, 'Set %d' % (i + 1))
    hx0, hy0, hx1, hy1 = c['help']
    bevel(o, hx0, hy0, hx1, hy1, FACE)
    text_c(o, (hx0 + hx1) // 2, hy0 + (hy1 - hy0 - 7) // 2, '?', LABEL, 9)
    groove(o, 4, c['manual'][3] + 3, 46, c['manual'][3] + 5)
    groove(o, 4, c['sets'][2][3] + 3, 46, c['sets'][2][3] + 5)
    # the triangle
    draw_triangle(o, c['tri'])
    # the bar well (white strip for the letters below the gauge, frame outside everything)
    gx0, gy0, gx1, gy1 = c['well']
    o.rect(gx0, gy0, gx1, 93, 0)
    o.frame(gx0 - 1, gy0 - 1, gx1 + 1, 94, INK)
    reg.flat_rect(bid, c['well'], 0, 'bar well')
    for bx, ch in zip(c['bars'], c['letters']):
        text_c(o, bx + 3, 84, ch, SMALL, INK)
    # corner boxes
    rings = []
    for hit, val, col, label in c['boxes']:
        rings.append((corner_box(o, hit, val, col, label), col))
        reg.flat_rect(bid, val, 0, 'value ' + label)
    reg.add(bid, o, (210, 170), what=what)

    @reg.check
    def _tri(reg, bid=bid, c=c):
        a = reg.img[bid].a
        rect = c['tri']
        x0, y0, x1, y1 = rect
        cx, cy = int((x0 + x1) / 2), int((y0 + y1) * 0.6)
        assert a[cy, cx] == 0
        seen = {(cx, cy)}
        dq = deque([(cx, cy)])
        while dq:
            x, y = dq.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen and 0 <= nx < 210 and 0 <= ny < 170 and a[ny, nx] == 0:
                    seen.add((nx, ny))
                    dq.append((nx, ny))
        assert len(seen) < 20000
        for (x, y) in seen:
            assert min(_edge_dists(rect, x, y)) >= -2, ('interior outside the triangle (+2 px)', bid, x, y)
        for y in range(y0, y1):
            for x in range(x0, x1):
                if min(_edge_dists(rect, x, y)) >= 2:
                    assert (x, y) in seen, ('triangle interior (-2 px) not flat white', bid, x, y)
        ys = [p[1] for p in seen]
        xs = [p[0] for p in seen]
        assert min(ys) <= y0 + 3 and max(ys) >= y1 - 4, (bid, min(ys), max(ys))
        assert min(xs) <= x0 + 4 and max(xs) >= x1 - 5, (bid, min(xs), max(xs))
        # the corner boxes' frame colours (check 8)
        want = [b[2] for b in c['boxes']]
        assert want == ([8, 11, 7] if bid == 4600 else [4, 6, 2]), want
        for (ring, col) in rings:
            assert a[ring[1], ring[0]] == col and a[ring[3] - 1, ring[2] - 1] == col, (bid, ring, col)
            assert a[ring[1] + 1, (ring[0] + ring[2]) // 2] == col
        # the well holds nothing but white (and the three letters below the gauge)
        gx0, gy0, gx1, gy1 = c['well']
        assert (a[gy0 - 1, gx0 - 1:gx1 + 1] == INK).all() and (a[gy0:93, gx0 - 1] == INK).all()
    return o


def arrow(img, tip, direction, color=6, n=3):
    """Small arrowhead at tip pointing 'left' or 'right' (1-px lines)."""
    d = -1 if direction == 'left' else 1
    img.line(tip[0], tip[1], tip[0] - d * n, tip[1] - n, color)
    img.line(tip[0], tip[1], tip[0] - d * n, tip[1] + n, color)


def dot(img, p, color=6):
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        img.px(p[0] + dx, p[1] + dy, color)


def make_overlay(reg, bid, pid, texts):
    c = CFG[pid]
    ox, oy = c['ox'], c['oy']
    W, H = c['size']
    LW, LH = c['lay']
    o = Img(W, H, T)

    def R(r):
        return (r[0] - ox, r[1] - oy, r[2] - ox, r[3] - oy)

    ar, mr = R(c['auto']), R(c['manual'])
    s1, s3 = R(c['sets'][0]), R(c['sets'][2])
    tri = R(c['tri'])
    bars = R(c['well'])
    bx_ = [R(b[0]) for b in c['boxes']]         # top, bottom-left, bottom-right (hit rectangles)
    btn_right = ar[2]
    P = []        # (name, rect) of all panels
    leaders = []  # (name, pts, own panel rect)

    def panel(name, x, y, lines, w=None):
        r = callout(o, x, y, lines, w)
        P.append((name, r))
        return r

    def lead(name, pts, target, own, tol=0):
        leader(o, reg, bid, name, pts, target, tol=tol)
        leaders.append((name, pts, own))

    # E: the bars (the panel overlaps the bar rectangle: no leader)
    E = panel('bars', bx_[0][2] + 4, 2, texts['bars'])
    # A: Auto / Manual (two short leaders)
    Ax = ar[2] + 8
    Ay = mr[3] - 5
    A = panel('auto/manual', Ax, Ay, texts['auto'])
    lead('manual', [(Ax, Ay + 3), (btn_right + 2, Ay + 3)], mr, A, tol=3)
    lead('auto', [(Ax + 8, Ay), (Ax + 8, ar[3] - 5), (btn_right + 2, ar[3] - 5)], ar, A, tol=3)
    # B: the three Set buttons (a bracket)
    By = A[3] + 4
    B = panel('sets', Ax, By, texts['sets'])
    bx = btn_right + 3
    tipx = btn_right + 1
    y1m = (s1[1] + s1[3]) // 2
    y3m = (s3[1] + s3[3]) // 2
    o.line(tipx, y1m, bx, y1m, 6)
    o.line(bx, y1m, bx, y3m, 6)
    o.line(bx, y3m, tipx, y3m, 6)
    reg.tip(bid, 'set 1', (tipx, y1m), s1, 3)
    reg.tip(bid, 'set 3', (tipx, y3m), s3, 3)
    ymid = By + 6
    o.line(bx, ymid, Ax, ymid, 6)
    # C: the triangle (a dot inside it)
    apex_x = int((tri[0] + tri[2]) / 2)
    Cy = tri[1] + 60
    C = panel('triangle', Ax, Cy, texts['tri'])
    tipy = tri[1] + 50
    lead('triangle', [(apex_x, Cy), (apex_x, tipy)], tri, C)
    dot(o, (apex_x, tipy))
    # D: the corner boxes, a panel between the two bottom boxes
    dw = callout_size(texts['boxes'])[0]
    mid = (bx_[1][2] + bx_[2][0]) // 2
    Dy = bx_[1][1] - 2
    D = panel('boxes', mid - dw // 2, Dy, texts['boxes'])
    ty = Dy + 17
    lead('box left', [(D[0], ty), (bx_[1][0] + 5, ty)], bx_[1], D)
    arrow(o, (bx_[1][0] + 5, ty), 'left')
    lead('box right', [(D[2] - 1, ty), (bx_[2][2] - 5, ty)], bx_[2], D)
    arrow(o, (bx_[2][2] - 5, ty), 'right')
    reg.panels[bid] = [r for _, r in P]
    reg.add(bid, o, (W, H), masked=True, colours=(0, 6, 14), what=what_of(pid))

    @reg.check
    def _ov(reg, bid=bid, P=P, leaders=leaders, bx_=bx_, E=E, bars=bars, LW=LW, LH=LH):
        a = reg.img[bid].a
        ys, xs = np.where(a != T)
        assert xs.max() < LW and ys.max() < LH, ('content outside the layout rectangle', bid, xs.max(), ys.max())
        rects = [r for _, r in P]
        for i, p in enumerate(rects):
            for q in rects[i + 1:]:
                assert p[2] + 1 <= q[0] or q[2] + 1 <= p[0] or p[3] + 1 <= q[1] or q[3] + 1 <= p[1], ('panels overlap / touch', bid, p, q)
            for bxr in bx_:
                assert p[2] <= bxr[0] or bxr[2] <= p[0] or p[3] <= bxr[1] or bxr[3] <= p[1], ('panel covers a corner box', bid, p, bxr)
        assert not (E[2] <= bars[0] or bars[2] <= E[0] or E[3] <= bars[1] or bars[3] <= E[1]), 'bar panel must overlap the bars'
        # left of x = 8: only 1-px leaders (no panel pixels)
        for name, pts, own in leaders:
            for (x, y) in pts[1:]:
                for nm, r in P:
                    if r == own:
                        continue
                    assert not (r[0] <= x < r[2] and r[1] <= y < r[3]), ('leader ends inside a foreign panel', name, nm)
        left = a[:, :min(r[0] for r in rects)]
        assert set(np.unique(left).tolist()) <= {T, 6}, 'non-leader pixels left of the panels'
    return o


def what_of(pid):
    return 'Behavior Control help overlay' if pid == 4600 else 'Caste Control help overlay'


def group_f(reg):
    make_panel(reg, 4600, 'Behavior Control panel')
    make_panel(reg, 4620, 'Caste Control panel')
    make_overlay(reg, 4601, 4600, dict(
        bars=['Bars: share of', 'each job.'],
        auto=['Auto or manual', 'control mode.'],
        sets=['Recall preset ratios.'],
        tri=['Move the pointer inside', 'the triangle to change', 'the current ratios.'],
        boxes=['Click a box to', 'switch the display.']))
    make_overlay(reg, 4621, 4620, dict(
        bars=['Bars: share of', 'each caste.'],
        auto=['Auto or manual', 'control mode.'],
        sets=['Recall preset ratios.'],
        tri=['Move the pointer inside', 'the triangle to change', 'the current ratios.'],
        boxes=['Click a box to', 'switch the display.']))


# =============================================================================================================
# G. The History window
# =============================================================================================================
def rot_panel(img, x, bottom, lines, face=SMALL):
    """Panel with 1 or 2 lines of text rotated 90 deg ccw, text starting at the bottom; 12 / 22 px wide.  Returns the rect."""
    n = len(lines)
    w = 2 + 10 * n
    tw = max(face.width(s) for s in lines)
    h = tw + 6
    y = bottom - h
    img.rect(x, y, x + w, y + h, 0)
    img.frame(x, y, x + w, y + h, 14)
    for k, s in enumerate(lines):
        text_rot(img, x + 2 + 10 * k, y + h - 3 - face.width(s), s, face, 14)
    return (x, y, x + w, y + h)


HIST = [  # name, label, rect (picture coordinates)
    ('pop b', 'Pop', (36, 138, 77, 153)), ('pop r', 'Pop', (36, 160, 77, 175)),
    ('food b', 'Food', (85, 138, 126, 153)), ('food r', 'Food', (84, 160, 125, 175)),
    ('health b', 'Health', (132, 138, 174, 152)), ('health r', 'Health', (132, 160, 174, 174)),
    ('s.food', 'S.Food', (187, 138, 229, 152)), ('starved', 'Hunger', (235, 138, 277, 152)),
    ('eaten', 'Eaten', (187, 160, 229, 174)), ('killed', 'Killed', (235, 160, 277, 174)),
]


def group_g(reg):
    o = Img(320, 179, FACE)
    well(o, 4, 4, 315, 131, 0, INK)
    reg.flat_rect(16000, (4, 4, 315, 131), 0, 'graph well')
    for name, lab, r in HIST:
        label_button(o, r, lab)
        reg.inverted(16000, r, FACE, INK, name)
    text_r(o, 35, 142, 'Black', LABEL, INK)
    text_r(o, 35, 164, 'Red', LABEL, REDCOL)
    groove(o, 180, 137, 182, 176)
    groove(o, 280, 137, 282, 176)
    bevel(o, 285, 151, 311, 163, FACE)
    text_c(o, 298, 153, '?', LABEL, 9)
    reg.add(16000, o, (320, 179), what='History window')

    @reg.check
    def _g0(reg):
        a = reg.img[16000].a
        # row labels clear of the buttons, graph well framed
        assert (a[3, 3:316] == INK).all() and (a[131, 3:316] == INK).all()
        for name, lab, r in HIST:
            assert r[2] - r[0] <= 43 and r[3] - r[1] >= 14

    # ---- 16001 the help overlay, drawn at (+45, +20)
    h = Img(247, 144, T)
    P = []
    r = callout(h, 42, 3, ['Hold the button down in the', 'white area to see current values.'])
    P.append(r)
    items = [
        (['Both colonies\'', 'population'], 12, (-9, 118, 32, 133), 118),
        (['Both colonies\' food', 'in the nest'], 59, (40, 118, 81, 133), 118),
        (['Both colonies\'', 'health'], 107, (87, 118, 129, 132), 118),
        (['Food on the', 'surface'], 151, (142, 118, 184, 132), 118),
        (['Black ants eaten', 'by predators'], 175, (142, 140, 184, 154), 140, 182),
        (['Black ants that', 'starved'], 200, (190, 118, 232, 132), 118),
        (['Black ants killed', 'by enemies'], 223, (190, 140, 232, 154), 140, 230),
    ]
    for it in items:
        lines, lx, target, ty = it[:4]
        px = it[4] if len(it) > 4 else lx      # x of the leader when it is not the panel's middle
        pr = rot_panel(h, lx - 11, 116, lines)
        assert pr[1] >= r[3] + 2 and pr[3] <= 117 + 1, ('rotated panel too tall', lines, pr, r)
        P.append(pr)
        leader(h, reg, 16001, lines[-1], [(px, 115), (px, ty)], target)
        assert ty == target[1]
    reg.panels[16001] = P
    reg.add(16001, h, (247, 144), masked=True, colours=(0, 6, 14), what='History window help overlay')

    @reg.check
    def _g1(reg):
        pr = reg.panels[16001]
        for i, p in enumerate(pr):
            assert p[3] <= 118, ('panel reaches the button rows', p)
            for q in pr[i + 1:]:
                assert p[2] <= q[0] or q[2] <= p[0] or p[3] <= q[1] or q[3] <= p[1], ('panels overlap', p, q)
        for p in pr[1:]:
            assert p[2] - p[0] <= 22
