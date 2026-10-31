"""Groups D (Edit window strip 15000 + help 15001), E (Map window toolbar 14000, help 14001, population popup 14002)
and H (Status 13000, Game Over 16100)."""
from uilib import *
import pics
from pics import pic_button, TAN
from grp_abc import menu_frame


def place(o, rect, img):
    o.blit(img, rect[0], rect[1])


def bevel2(o, x0, y0, x1, y1, face=FACE):
    """2-px bevelled frame (white highlight top/left, dark 14 / 13 shadow bottom/right), flat face inside."""
    o.rect(x0, y0, x1, y1, face)
    o.rect(x0, y0, x1 - 1, y0 + 2, HI)
    o.rect(x0, y0, x0 + 2, y1 - 1, HI)
    o.rect(x0 + 1, y1 - 2, x1, y1 - 1, SH)
    o.rect(x0, y1 - 1, x1, y1, DSH)
    o.rect(x1 - 2, y0 + 1, x1 - 1, y1, SH)
    o.rect(x1 - 1, y0, x1, y1, DSH)


def label_button(o, rect, label, tri_right=False):
    x0, y0, x1, y1 = rect
    bevel(o, x0, y0, x1, y1, FACE)
    tw = LABEL.width(label) + (4 if tri_right else 0)
    sx = x0 + (x1 - x0 - tw) // 2
    ty = y0 + (y1 - y0 - 7) // 2
    end = text(o, sx, ty, label, LABEL, INK)
    if tri_right:
        tri(o, end + 3, ty + 3, 1, 'r', INK)
    assert sx >= x0 + 1 and (end + 4 if tri_right else end) <= x1 - 1, (label, sx, end)


def ant_go(w, h, kind):
    o = Img(w, h, TAN)
    import random
    r = random.Random(w + h)
    for _ in range(w * h // 12):
        o.px(r.randrange(w), r.randrange(h), 10)
    if kind == 'yellow':
        pics.ant_top(o, w // 2, h // 2 + 0, 1, 15, 15, 0.7)
    else:
        pics.spider_top(o, w // 2, h // 2 - 1, 0.8, 14)
    return o


# =============================================================================================================
# D. the Edit window strip
# =============================================================================================================
def group_d(reg):
    o = Img(48, 252, FACE)
    # --- top buttons
    label_button(o, (3, 3, 44, 14), 'MAP', True)
    reg.inverted(15000, (3, 3, 44, 14), FACE, INK, 'MAP')
    bevel(o, 3, 21, 22, 40, FACE)
    text_c(o, 12, 23, '?', LABEL, 9, scale=2)
    o.rect(25, 21, 44, 22, HI)                      # experimental button: the bevel lies OUTSIDE its flat rect
    o.rect(25, 21, 26, 40, HI)
    o.rect(26, 40, 45, 41, SH)
    o.rect(44, 22, 45, 41, SH)
    reg.spot(15000, (26, 22, 44, 40))
    # --- views
    place(o, (3, 47), pic_button(41, 19, lambda w, h: pics.surface(w, h)))
    place(o, (3, 69), pic_button(19, 19, pics.nest_cut, frame=15))
    place(o, (25, 69), pic_button(19, 19, pics.nest_cut, frame=3))
    for r in ((3, 47, 44, 66), (3, 69, 22, 88), (25, 69, 44, 88)):
        reg.inverted(15000, r, TAN, INK, 'view')
    # --- go-to buttons
    place(o, (3, 91), pic_button(19, 14, lambda w, h: ant_go(w, h, 'yellow')))
    place(o, (25, 91), pic_button(19, 14, lambda w, h: ant_go(w, h, 'spider')))
    place(o, (3, 108), pic_button(19, 14, lambda w, h: pics.queen_soil(w, h, 15)))
    place(o, (25, 108), pic_button(19, 14, lambda w, h: pics.queen_soil(w, h, 3)))
    # --- pause / scent
    label_button(o, (3, 129, 44, 140), 'PAUSE')
    label_button(o, (3, 147, 44, 158), 'SCENT', True)
    reg.inverted(15000, (3, 129, 44, 140), FACE, INK, 'PAUSE')
    reg.inverted(15000, (3, 147, 44, 158), FACE, INK, 'SCENT')
    # --- dividers
    for y in (43, 89, 125):
        groove(o, 0, y, 47, y + 2)
    o.hline(0, 47, 161, INK)
    # --- health
    text_c(o, 23, 164, 'Health', LABEL, INK)
    for x0 in (8, 21, 34):
        o.frame(x0 - 1, 175, x0 + 6, 240, INK)
        o.rect(x0, 176, x0 + 5, 239, FACE)
    reg.flat_rect(15000, (8, 176, 13, 239), FACE, 'yellow bar')
    reg.flat_rect(15000, (21, 176, 26, 239), FACE, 'black bar')
    reg.flat_rect(15000, (34, 176, 39, 239), FACE, 'red bar')
    text_c(o, 10, 243, 'Y', LABEL, PLAYER, outline=INK)
    text_c(o, 23, 243, 'B', LABEL, BLACKCOL)
    text_c(o, 36, 243, 'R', LABEL, REDCOL)
    o.vline(47, 0, 252, INK)
    reg.add(15000, o, (48, 252), what='Edit window tool strip')

    # --- 15001: the help overlay
    h = Img(174, 238, T)
    items = [  # (lines, tip)
        (['Click: overview map.', 'Drag: open the Map window.'], (30, 9), (-7, 4, 34, 15), 'MAP'),
        (['Experimental tool menu'], (26, 31), (16, 23, 34, 41), 'experimental'),
        (['Show the surface'], (20, 57), (-7, 48, 34, 67), 'surface'),
        (['Black nest view'], (6, 79), (-7, 70, 12, 89), 'black nest'),
        (['Red nest view'], (25, 79), (15, 70, 34, 89), 'red nest'),
        (['Go to the yellow ant'], (6, 99), (-7, 92, 12, 106), 'yellow'),
        (['Go to the spider'], (25, 99), (15, 92, 34, 106), 'spider'),
        (['Go to the black queen'], (6, 116), (-7, 109, 12, 123), 'black queen'),
        (['Go to the red queen'], (25, 116), (15, 109, 34, 123), 'red queen'),
        (['Pause or resume the game'], (14, 135), (-7, 130, 34, 141), 'pause'),
        (['Scent overlay menu'], (14, 153), (-7, 148, 34, 159), 'scent'),
        (["Yellow ant's health"], (1, 188), (-2, 177, 3, 240), 'yellow bar'),
        (['Level where yellow eats'], (1, 202), (-2, 177, 3, 240), 'yellow eats'),
        (["Black colony's health"], (13, 216), (11, 177, 16, 240), 'black bar'),
        (['Colony alert level'], (13, 228), (11, 177, 16, 240), 'alert'),
        (["Red colony's health"], (26, 234), (24, 177, 29, 240), 'red bar'),
    ]
    y = 0
    panels = []
    for lines, tip, target, name in items:
        r = callout(h, 40, y, lines)
        assert r[2] - r[0] <= 135, (name, r)
        panels.append(r)
        ymid = y + 6 if len(lines) == 1 else y + 11
        leader(h, reg, 15001, name, [(39, ymid), (tip[0], tip[1])], target)
        y = r[3] + 1
    reg.panels[15001] = panels
    reg.add(15001, h, (174, 238), masked=True, colours=(0, 6, 14), what='Edit window help overlay')

    @reg.check
    def _d0(reg):
        a = reg.img[15000].a
        assert (a[:, 47] == INK).all(), 'last column is the black edge'
        assert (a[251, :47] == FACE).all(), 'bottom edge ends in light grey'
        for x0 in (8, 21, 34):  # the bar wells: black frame outside, nothing inside
            assert (a[175, x0 - 1:x0 + 6] == INK).all() and (a[239, x0 - 1:x0 + 6] == INK).all()
            assert (a[175:240, x0 - 1] == INK).all() and (a[175:240, x0 + 5] == INK).all()

    @reg.check
    def _d(reg):
        a = reg.img[15001].a
        # panels at x >= 40, only leader lines (1 px thick, colour 6) left of 40
        left = a[:, :40]
        assert set(np.unique(left).tolist()) <= {T, 6}, 'non-leader pixels left of x=40'
        op = (left != T)
        for yy in range(op.shape[0] - 1):
            for xx in range(op.shape[1] - 1):
                assert not (op[yy, xx] and op[yy + 1, xx] and op[yy, xx + 1] and op[yy + 1, xx + 1]), ('leader thicker than 1px', xx, yy)
        pr = reg.panels[15001]
        for i, p in enumerate(pr):
            assert p[0] >= 40 and p[3] <= 238
            for q in pr[i + 1:]:
                assert p[3] <= q[1] or q[3] <= p[1], 'panels overlap'


# =============================================================================================================
# E. the Map window toolbar
# =============================================================================================================
def _tri_letter(w, h, letter, bar_cols):
    o = Img(w, h, FACE)
    o.poly([(7.5, 0.5), (0, h - 0.5), (15, h - 0.5)], 0)
    o.line(7, 0, 0, h - 1, INK)
    o.line(7, 0, 14, h - 1, INK)
    o.hline(0, 15, h - 1, INK)
    text_c(o, 7, 8, letter, SMALL, INK)
    hs = (7, 11, 5)
    for i, (hh, c) in enumerate(zip(hs, bar_cols)):
        x = 16 + i * 2
        o.rect(x, h - 1 - hh, x + 1, h - 1, c)
        o.px(x, h - 1, INK)
    return o


def _center_pic(w, h):
    o = Img(w, h, TAN)
    import random
    r = random.Random(5)
    for _ in range(w * h // 14):
        o.px(r.randrange(w), r.randrange(h), 10)
    pics.ant_top(o, w // 2, h // 2 + 1, 1, 15, 15, 0.75)
    for sx, sy in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)):  # marker: four corner ticks
        dx = 3 if sx == 1 else -3
        dy = 3 if sy == 1 else -3
        o.line(sx, sy, sx + dx, sy, INK)
        o.line(sx, sy, sx, sy + dy, INK)
    return o


def group_e(reg):
    o = Img(512, 46, FACE)

    def B(rect, content, frame=None, face=TAN, ink=INK, inverted=True):
        W, H = rect[2] - rect[0], rect[3] - rect[1]
        place(o, rect, pic_button(W, H, content, frame))
        if inverted:
            reg.inverted(14000, rect, face, ink, 'button %s' % (rect,))

    # views and labels
    B((5, 5, 42, 31), pics.house_yard, face=0)
    B((47, 5, 84, 31), lambda w, h: pics.surface(w, h, 8))
    B((89, 5, 114, 31), pics.nest_cut, 15)
    B((119, 5, 144, 31), pics.nest_cut, 3)
    for cx, s, c in ((23, 'Yard', INK), (65, 'Surface', INK), (101, 'Nest', INK), (131, 'Nest', REDCOL)):
        text_c(o, cx, 35, s, LABEL, c)
    # scents
    B((155, 3, 189, 21), lambda w, h: pics.scent_nest(w, h, False), 15)
    B((155, 25, 189, 43), lambda w, h: pics.scent_trail(w, h, False), 15)
    B((195, 3, 213, 43), pics.alarm, face=FACE)
    B((219, 3, 253, 21), lambda w, h: pics.scent_nest(w, h, True), 3)
    B((219, 25, 253, 43), lambda w, h: pics.scent_trail(w, h, True), 3)
    # the right-hand columns
    B((264, 3, 287, 21), pics.path_pic, inverted=False)
    B((264, 25, 287, 43), lambda w, h: _tri_letter(w, h, 'B', (8, 11, 7)), inverted=False)
    B((290, 3, 313, 22), _center_pic, inverted=False)
    B((290, 25, 313, 43), lambda w, h: _tri_letter(w, h, 'C', (4, 6, 2)), inverted=False)
    B((316, 3, 339, 21), lambda w, h: Img(w, h, FACE), inverted=False)
    B((316, 25, 339, 43), pics.graph_pic, inverted=False)
    B((342, 3, 365, 22), lambda w, h: pics.glyph_pic(w, h, '%', 6), inverted=False)
    B((342, 25, 365, 43), pics.card_pic, inverted=False)
    B((368, 25, 391, 43), lambda w, h: pics.glyph_pic(w, h, '?', 9), inverted=False)
    # experimental menu button: flat rect, bevel outside
    o.rect(368, 3, 391, 4, HI)
    o.rect(368, 3, 369, 21, HI)
    o.rect(369, 21, 392, 22, SH)
    o.rect(391, 4, 392, 22, SH)
    o.rect(369, 4, 391, 21, FACE)
    reg.spot(14000, (369, 4, 391, 21))
    # dividers
    for x in (149, 258):
        groove(o, x, 2, x + 2, 45)
    # population report panel
    bevel(o, 395, 1, 510, 45, FACE, raised=False)
    o.hline(397, 508, 23, SH)
    well(o, 398, 3, 432, 11, 0, INK)
    well(o, 398, 26, 432, 34, 0, REDCOL)
    text_c(o, 415, 14, 'BLACK', LABEL, INK)
    text_c(o, 415, 37, 'RED', LABEL, REDCOL)
    for (rect, col) in (((445, 3, 509, 11), INK), ((445, 15, 509, 20), INK),
                        ((445, 26, 509, 34), REDCOL), ((445, 38, 509, 43), REDCOL)):
        well(o, *rect, 0, col)
        reg.flat_rect(14000, rect, 0, 'gauge')
    for (ch, y) in (('P', 3), ('H', 14), ('P', 26), ('H', 37)):
        text(o, 436, y, ch, LABEL, 9)
    reg.flat_rect(14000, (398, 3, 432, 11), 0, 'black count')
    reg.flat_rect(14000, (398, 26, 432, 34), 0, 'red count')
    reg.add(14000, o, (512, 46), what='Map window toolbar')

    # ---- 14001 the help overlay (drawn at (0, -89))
    h = Img(512, 133, T)
    P = []

    def panel(x, y, lines, w=None, padx=3):
        r = callout(h, x, y, lines, w, padx=padx)
        P.append(r)
        return r

    def rot(x, bottom, s):
        tw = SMALL.width(s)
        ph = tw + 6
        r = callout_rot(h, x, bottom - ph, s, h=ph)
        assert r[1] >= 0, (s, r)
        P.append(r)
        return r

    LD = []

    def lead(name, pts, target, own=None):
        leader(h, reg, 14001, name, pts, target)
        LD.append((name, pts, own if own is not None else P[-1]))

    r = panel(5, 60, ['MAP VIEWS', 'Yard view'])
    lead('yard', [(20, r[3]), (20, 96)], (5, 94, 42, 120))
    r = panel(30, 42, ['Surface view'])
    lead('surface', [(75, r[3]), (75, 98)], (47, 94, 84, 120))
    r = panel(66, 24, ['Black nest'])
    lead('black nest', [(100, r[3]), (100, 98)], (89, 94, 114, 120))
    r = panel(96, 6, ['Red nest'])
    lead('red nest', [(130, r[3]), (130, 98)], (119, 94, 144, 120))
    r = panel(160, 24, ['SCENT LAYERS', 'Nest scents'], w=90)
    lead('nest scent 1', [(170, r[3]), (170, 96)], (155, 92, 189, 110))
    lead('nest scent 2', [(235, r[3]), (235, 96)], (219, 92, 253, 110))
    r = panel(176, 50, ['Food trails'], w=54)
    lead('trail 1', [(185, r[3]), (185, 118)], (155, 114, 189, 132))
    lead('trail 2', [(222, r[3]), (222, 118)], (219, 114, 253, 132))
    aw = callout_size(['Alarm'])[0]
    r = panel(204 - aw // 2, 68, ['Alarm'])
    lead('alarm', [(204, r[3]), (204, 100)], (195, 92, 213, 132))
    cols = [(264, 'Show trails', 'Behavior control', (264, 92, 287, 110), (264, 114, 287, 132)),
            (290, 'Center on yellow', 'Caste control', (290, 92, 313, 111), (290, 114, 313, 132)),
            (316, 'Mystery button', 'History display', (316, 92, 339, 110), (316, 114, 339, 132)),
            (342, 'Efficiency score', 'Ant info window', (342, 92, 365, 111), (342, 114, 365, 132))]
    for x0, up, low, tu, tl in cols:
        rl = rot(x0, 86, low)
        ru = rot(x0 + 12, 86, up)
        lead(low, [(x0 + 6, rl[3]), (x0 + 6, 120)], tl, rl)
        lead(up, [(x0 + 18, ru[3]), (x0 + 18, 98)], tu, ru)
    rr = rot(372, 86, 'Experimental menu')
    lead('experimental', [(378, rr[3]), (378, 98)], (369, 93, 391, 110))
    r = panel(396, 6, ['Hold down here for the', 'detailed population', 'report.'])
    lead('report', [(448, r[3]), (448, 91)], (395, 90, 510, 134))
    h.hline(398, 503, 91, 6)
    h.vline(398, 91, 94, 6)
    h.vline(502, 91, 94, 6)
    reg.tip(14001, 'report bracket left', (398, 91), (395, 90, 510, 134))
    reg.tip(14001, 'report bracket right', (502, 91), (395, 90, 510, 134))
    pw = callout_size(['Population'], padx=2)[0]
    r = panel(459, 44, ['Population'], w=pw + 0, padx=2)
    lead('population black', [(462, r[3]), (462, 96)], (445, 92, 509, 100))
    lead('population red', [(506, r[3]), (506, 119)], (445, 115, 509, 123))
    r = panel(470, 62, ['Health'], padx=2)
    lead('health black', [(480, r[3]), (480, 106)], (445, 104, 509, 109))
    lead('health red', [(495, r[3]), (495, 129)], (445, 127, 509, 132))
    reg.panels[14001] = P
    reg.leaders = getattr(reg, 'leaders', {})
    reg.leaders[14001] = LD
    reg.add(14001, h, (512, 133), masked=True, colours=(0, 6, 14), what='Map window help overlay')

    @reg.check
    def _e(reg):
        pr = reg.panels[14001]
        a = reg.img[14001].a
        for i, p in enumerate(pr):
            assert p[3] <= 89, ('panel reaches the toolbar rows', p)
            for q in pr[i + 1:]:
                assert p[2] <= q[0] or q[2] <= p[0] or p[3] <= q[1] or q[3] <= p[1], ('panels overlap', p, q)
        # a leader (axis-aligned segments) never crosses a panel that is not its own
        for name, pts, own in reg.leaders[14001]:
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                bx0, bx1, by0, by1 = min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb)
                for p in pr:
                    if p == own:
                        continue
                    assert bx1 < p[0] or bx0 >= p[2] or by1 < p[1] or by0 >= p[3], ('leader', name, 'crosses panel', p)
        # right-hand columns: panels no wider than 12, leaders stay inside their column
        for p in pr:
            if p[2] - p[0] <= 12:
                assert p[3] - p[1] >= 20

    # ---- 14002 the population popup
    o = Img(181, 142, FACE)
    menu_frame(o, 181, 142)
    rows = [('Larvae', 14), ('Workers', 38), ('Soldiers', 61), ('Males', 85), ('New Queens', 108), ('Queens', 131)]
    kinds = [None, 'worker', 'soldier', 'male', 'newq', 'queen']
    for (nm, yc), kd in zip(rows, kinds):
        text_r(o, 63, yc - 3, nm, LABEL, INK)
        if kd is None:
            pics.larva(o, 66, yc - 7)
        else:
            pics.ant_side(o, 66, yc - 7, kd)
    reg.add(14002, o, (181, 142), what='population popup')
    reg.flat_rect(14002, (88, 4, 177, 139), FACE, 'text / gauge area')


# =============================================================================================================
# H. Status and Game Over
# =============================================================================================================
def group_h(reg):
    o = Img(312, 180, FACE)
    text_c(o, 156, 3, 'STATUS', LABEL, 6, scale=2, shadow=INK)
    text_c(o, 74, 33, 'COLONY', LABEL, HEADING)
    text_c(o, 238, 33, 'UNIVERSE', LABEL, HEADING)
    left = [('Colony Health', (112, 47, 155, 63)), ('Foraging', (113, 63, 156, 79)),
            ('Eggs Hatched', (113, 80, 156, 96)), ('Fights Won', (113, 98, 156, 114))]
    right = [('Colonies Started', (272, 45, 310, 63)), ('Colonies Held', (272, 62, 310, 80)),
             ('Yard Filled', (272, 79, 310, 97)), ('House Filled', (272, 96, 310, 114))]
    for col, x, xe in ((left, 10, 110), (right, 168, 270)):
        for nm, r in col:
            yc = (r[1] + r[3]) // 2
            end = text(o, x, yc - 3, nm, LABEL, INK)
            for xx in range(end + 4, xe - 1, 2):
                o.px(xx, yc + 3, DSH)
            assert end + 4 < xe - 6, nm
            reg.flat_rect(13000, r, FACE, nm)
    bevel2(o, 10, 119, 304, 170)
    reg.flat_rect(13000, (13, 123, 299, 141), FACE, 'line 1')
    reg.flat_rect(13000, (13, 146, 299, 164), FACE, 'line 2')
    reg.flat_rect(13000, (10, 170, 305, 179), FACE, 'line 3')
    reg.add(13000, o, (312, 180), what='Status window')

    o = Img(321, 201, FACE)
    text_c(o, 160, 15, 'GAME OVER', LABEL, REDCOL, scale=2, shadow=INK)
    ant = Img(20, 14, T)
    pics.ant_side(ant, 0, 0, 'worker', 15)
    o.blit(ant, 62, 16)
    mir = Img(20, 14, T)
    mir.a = ant.a[:, ::-1].copy()
    o.blit(mir, 240, 16)
    for y, c in ((44, SH), (45, INK), (46, 0), (47, SH)):
        o.hline(20, 301, y, c)
    bevel2(o, 47, 61, 276, 189)
    text_c(o, 161, 75, 'FINAL SCORE', LABEL, REDCOL, shadow=DSH)
    o.hline(118, 205, 88, REDCOL)
    o.hline(118, 205, 89, INK)
    text_c(o, 161, 137, 'YOUR RATING', LABEL, 6, shadow=DSH)
    o.hline(118, 205, 150, 6)
    o.hline(118, 205, 151, INK)
    for r in ((49, 92, 270, 106), (49, 104, 270, 118), (50, 154, 268, 168)):
        reg.flat_rect(16100, r, FACE, 'text')
    reg.add(16100, o, (321, 201), what='Game Over window')
