"""Groups A (window chrome 100..113), B (menus, palettes, help pages) and C (tool icons 5100..5107)."""
import math
from uilib import *
import pics


# =============================================================================================================
# A. window chrome icons
# =============================================================================================================
def _sym_x(o, c, t=2):
    o.line(4, 4, 9, 9, c, t)
    o.line(9, 4, 4, 9, c, t)


def _arrow_up(o, flip=False):
    # a solid up arrow on a 15 x 13 button
    cells = Img(15, 13, T)
    tri(cells, 7, 6, 4, 'u', 15)
    cells.rect(6, 9, 9, 11, 15)
    if flip:
        cells.a = cells.a[::-1].copy()
    for y in range(13):
        for x in range(15):
            if cells.a[y, x] != T:
                o.px(x, y, 15)


def _chrome(reg, bid, w, h, drawfn, what):
    o = chrome_button(w, h)
    drawfn(o)
    reg.add(bid, o, (w, h), what=what)


def group_a(reg):
    def close(o):
        _sym_x(o, 15)

    def close_warn(o):
        o.rect(2, 2, 13, 13, 1)
        bevel(o, 1, 1, 14, 14, 1)
        _sym_x(o, 3)

    def zoom(o):
        o.rect(3, 3, 12, 12, 0)
        o.frame(3, 3, 12, 12, 15)
        o.rect(4, 4, 8, 8, 6)

    def zoom_in(o):
        o.rect(3, 3, 12, 12, 0)
        o.frame(3, 3, 12, 12, 15)
        o.hline(5, 10, 7, 6)
        o.vline(7, 5, 10, 6)
        o.hline(5, 10, 8, 6)
        o.vline(8, 5, 10, 6)

    def doc(o):
        o.rect(4, 3, 11, 12, 0)
        o.frame(4, 3, 11, 12, 15)
        o.rect(9, 3, 11, 5, FACE)
        o.line(8, 3, 10, 5, 15)
        o.vline(10, 4, 5, 15)
        o.hline(5, 9, 6, 13)
        o.hline(5, 10, 8, 13)
        o.hline(5, 10, 10, 13)

    def move(o):
        o.rect(3, 3, 9, 9, 12)
        o.frame(3, 3, 9, 9, 14)
        o.rect(6, 6, 12, 12, 0)
        o.frame(6, 6, 12, 12, 15)
        o.hline(7, 11, 7, 6)

    def up_right(o):
        o.poly([(11, 3), (11, 8), (6, 3)], 15)
        o.line(4, 10, 9, 5, 15, 2)

    def down_left(o):
        o.poly([(3, 11), (3, 6), (8, 11)], 15)
        o.line(10, 4, 5, 9, 15, 2)

    def ruler(o):
        o.rect(2, 5, 13, 10, 0)
        o.frame(2, 5, 13, 10, 15)
        o.hline(3, 12, 6, 6)
        for x in (4, 6, 8, 10):
            o.vline(x, 7, 9 if x % 4 == 0 else 8, 15)
        o.vline(12, 7, 9, 15)

    def vdouble(o):
        o.poly([(7, 2), (3, 6), (11, 6)], 15)
        o.poly([(7, 12), (3, 8), (11, 8)], 15)
        o.vline(7, 5, 10, 15)

    _chrome(reg, 100, 15, 15, close, 'close box')
    _chrome(reg, 101, 15, 15, move, 'move / re-order window')
    _chrome(reg, 102, 15, 15, zoom_in, 'zoom box, zoom in')
    _chrome(reg, 103, 15, 15, zoom, 'zoom box')
    _chrome(reg, 104, 15, 15, up_right, 'corner arrow')
    _chrome(reg, 105, 15, 15, doc, 'document')
    _chrome(reg, 106, 15, 15, down_left, 'opposite corner arrow')
    _chrome(reg, 107, 15, 15, ruler, 'ruler')
    _chrome(reg, 108, 15, 15, vdouble, 'double vertical arrow')
    _chrome(reg, 109, 15, 13, lambda o: _arrow_up(o), 'scroll bar up arrow')
    _chrome(reg, 110, 15, 13, lambda o: (o.rect(4, 3, 11, 10, 0), o.frame(4, 3, 11, 10, 15), o.rect(5, 4, 10, 9, 6)),
            'scroll bar box')
    _chrome(reg, 111, 15, 13, lambda o: _arrow_up(o, True), 'scroll bar down arrow')
    # 112: the grow box, 16 x 16, over the map: black outline all round, two nested corners
    o = chrome_button(16, 16)
    o.vline(12, 5, 13, 15)
    o.hline(5, 13, 12, 15)
    o.vline(8, 9, 13, 15)
    o.hline(8, 13, 8 + 1, 15)
    reg.add(112, o, (16, 16), what='grow box')
    _chrome(reg, 113, 15, 15, close_warn, 'close box, warning variant')

    @reg.check
    def _a(reg):
        assert reg.img[109].w == reg.img[111].w == 15 and reg.img[109].h == reg.img[111].h == 13


# =============================================================================================================
# B. pop-up menus, palettes, help pages
# =============================================================================================================
def menu_frame(o, vw, vh):
    """Black frame at the visible edge (a cut-off last column / row is black too), 1-px bevel ring inside."""
    o.rect(0, 0, o.w, o.h, FACE)
    o.rect(vw, 0, o.w, o.h, INK)
    o.rect(0, vh, o.w, o.h, INK)
    o.frame(0, 0, vw, vh, INK)
    o.rect(1, 1, vw - 2, 2, HI)
    o.rect(1, 1, 2, vh - 2, HI)
    o.rect(2, vh - 2, vw - 1, vh - 1, SH)
    o.rect(vw - 2, 2, vw - 1, vh - 1, SH)


BADGE = {'1': 7, '2': 8, '3': 1, '4': 2, 'X': 4}


def badge(o, x, y, ch, fill=None, ink=15):
    o.rect(x, y, x + 9, y + 10, fill if fill is not None else BADGE[ch])
    o.frame(x, y, x + 9, y + 10, 15)
    text_c(o, x + 4, y + 2, ch, SMALL, ink)


def help_badge(o, x, y):
    o.rect(x, y, x + 9, y + 10, 0)
    o.frame(x, y, x + 9, y + 10, 15)
    text_c(o, x + 4, y + 2, '?', SMALL, 9)


def _mc(colour):
    return colour if MENU_COLOURED else INK


def menu_entries(reg, bid, o, rects, labels, badges, text_x_off=12):
    for r, lab, b in zip(rects, labels, badges):
        x0, y0, x1, y1 = r
        by = y0 + (y1 - y0 - 10) // 2
        if b == '?':
            help_badge(o, x0 + 1, by)
        elif b:
            badge(o, x0 + 1, by, b)
        ty = y0 + (y1 - y0 - 7) // 2
        end = text(o, x0 + text_x_off, ty, lab, LABEL, INK)
        assert end <= x1 - 1, (bid, lab, end, x1)
        reg.inverted(bid, r, FACE, INK, lab)


def swatch_frame(c, w, h, colour):
    o = Img(w, h, FACE)
    o.frame(0, 0, w, h, colour)
    return o


def group_b(reg):
    # ---- the three ant menus
    def ant_menu(bid, size, visible, rects, labels, badges):
        o = Img(*size)
        menu_frame(o, *visible)
        menu_entries(reg, bid, o, rects, labels, badges)
        reg.add(bid, o, size, what=' / '.join(labels))

    ant_menu(4500, (82, 102), (81, 102),
             [(3, 3 + 16 * i, 78, 19 + 16 * i) for i in range(5)] + [(3, 83, 78, 98)],
             ['Recruit 5', 'Recruit 10', 'Release 1/2', 'Release All', 'Exchange', 'Help'],
             ['1', '2', '3', '4', 'X', '?'])
    ant_menu(4502, (82, 54), (82, 53), [(3, 3, 78, 18), (3, 19, 78, 35), (3, 35, 78, 50)],
             ['Dig Hole', 'Start Brood', 'Help'], ['1', '2', '?'])
    ant_menu(4504, (82, 70), (82, 70), [(3, 3, 79, 19), (3, 19, 79, 35), (3, 35, 79, 51), (3, 51, 79, 67)],
             ['Chase', 'Hunt', 'Exchange', 'Help'], ['1', '2', 'X', '?'])

    # ---- 4510 the Ant Info card
    o = Img(81, 85)
    menu_frame(o, 81, 85)
    for r in ((3, 3, 78, 15), (3, 28, 78, 50), (3, 64, 78, 81)):
        o.rect(*r, FACE)
    o.hline(3, 78, 15, SH)
    o.hline(3, 78, 50, SH)
    text_c(o, 40, 18, 'Behavior', SMALL, HEADING)
    text_c(o, 40, 54, 'Carrying', SMALL, HEADING)
    reg.add(4510, o, (81, 85), what='Ant Info card')
    reg.flat_rect(4510, (3, 3, 78, 15), FACE, 'kind')
    reg.flat_rect(4510, (3, 28, 78, 50), FACE, 'doing')
    reg.flat_rect(4510, (3, 64, 78, 81), FACE, 'carrying')

    # ---- 6000 the scent-layer menu
    o = Img(85, 109)
    menu_frame(o, 85, 108)
    rows = [(3, 3 + 17 * k, 81, 20 + 17 * k) for k in range(6)]
    labels = ['Off', 'Alarm', 'B-Nest', 'B-Trail', 'R-Nest', 'R-Trail']
    cols = [BLACKCOL, REDCOL]
    sw = {1: (pics.alarm, 15), 2: (lambda w, h: pics.scent_nest(w, h, False), 15),
          3: (lambda w, h: pics.scent_trail(w, h, False), 15), 4: (lambda w, h: pics.scent_nest(w, h, True), 3),
          5: (lambda w, h: pics.scent_trail(w, h, True), 3)}
    for k, r in enumerate(rows):
        x0, y0, x1, y1 = r
        if k in sw:
            fn, fc = sw[k]
            o.rect(4, y0 + 1, 36, y0 + 16, fc)
            o.blit(fn(30, 13), 5, y0 + 2)
        ty = y0 + (y1 - y0 - 7) // 2
        col = INK
        if MENU_COLOURED:
            col = {0: 10, 1: 6, 2: 15, 3: 15, 4: 3, 5: 3}[k]
        end = text(o, 40, ty, labels[k], LABEL, col)
        assert end <= x1 - 1
        reg.inverted(6000, r, FACE, INK, labels[k])
    reg.add(6000, o, (85, 109), what='scent-layer menu')

    # ---- 5000 the tool palette (icons are copied in from group C by the script)
    o = Img(97, 143)      # the spec table says 96 x 142 (window 97 x 143); tools/clean_pack/build.py wants 97 x 143
    menu_frame(o, 97, 143)
    names = ['Ant Info', 'Barriers', 'Dig/Fill', 'Add Ants', 'Add Food', 'Drop Trails', 'Insecticide', 'Start Game']
    for k, nm in enumerate(names):
        r = (3, 3 + 17 * k, 93, 20 + 17 * k)
        if k < 7:
            o.blit(reg.img[5100 + k], 4, 4 + 17 * k)
            end = text(o, 24, r[1] + 4, nm, LABEL_TALL, INK)
            assert end <= r[2] - 1, nm
        else:
            text_c(o, 48, r[1] + 4, nm, LABEL_TALL, INK)
        reg.inverted(5000, r, FACE, INK, nm)
    reg.add(5000, o, (97, 143), what='tool palette')

    @reg.check
    def _icons_identical(reg):
        for k in range(7):
            sub = reg.img[5000].a[4 + 17 * k:20 + 17 * k, 4:20]
            assert (sub == reg.img[5100 + k].a).all(), ('5000 vs', 5100 + k)

    # ---- 5010 / 5011
    o = Img(129, 24)
    menu_frame(o, 129, 24)
    r = (3, 3, 125, 20)
    end = text_c(o, 64, 8, 'EXPERIMENTAL MODE', LABEL, INK)
    assert end < 124
    reg.add(5010, o, (129, 24), what='experimental mode switch')
    reg.inverted(5010, r, FACE, INK, 'switch')

    o = Img(110, 53)
    menu_frame(o, 110, 53)
    for i, s in enumerate(('Experimental mode', 'is not available in', 'the full game.')):
        text_c(o, 55, 12 + 11 * i, s, SMALL, HEADING)
    reg.add(5011, o, (110, 53), what='notice')

    # ---- the option palettes
    def palette(bid, size, rects, labels, dark=None):
        w, h = size
        o = Img(w, h)
        o.frame(0, 0, w, h, INK)
        for i, (r, lab) in enumerate(zip(rects, labels)):
            if i:
                o.hline(0, w, r[1], INK)
            cx = (r[0] + r[2]) // 2
            end = text_c(o, cx, r[1] + 4, lab, SMALL, INK)
            assert end <= r[2] - 2 and cx - SMALL.width(lab) // 2 >= r[0] + 2, (bid, lab)
            reg.inverted(bid, r, FACE, INK, lab)
        reg.add(bid, o, size, what=' / '.join(labels))

    two = [(0, 0, 48, 14), (0, 14, 48, 28)]
    palette(5001, (49, 29), two, ['Walls', 'Rocks'])
    palette(5002, (49, 29), two, ['Dig', 'Fill'])
    palette(5003, (49, 29), two, ['Black', 'Red'])
    palette(5004, (49, 29), two, ['1 piece', '20 pieces'])
    palette(5005, (64, 71), [(0, 14 * i, 63, 14 * i + 14) for i in range(5)],
            ['Black nest', 'Black trail', 'Red nest', 'Red trail', 'Alarm'])
    palette(5006, (43, 29), [(0, 0, 42, 14), (0, 14, 42, 28)], ['Spray', 'Stream'])

    # ---- B2 help pages (black and white)
    def page(bid, size, title, sections):
        w, h = size
        o = Img(w, h, 0)
        o.frame(0, 0, w, h, 13)
        o.frame(2, 2, w - 2, h - 2, 15)
        text_c(o, w // 2 - 1, 8, title, LABEL, 15)
        y = 8 + 22
        n = 2
        for name, body in sections:
            text(o, 8, y, name, LABEL, 15)
            o.hline(8, 8 + LABEL.width(name), y + 9, 15)
            y += 11
            n += 1
            for toks in wrap(body, 169):
                draw_line(o, 8, y, toks, 15)
                y += 11
                n += 1
            y += 11
            n += 1
        assert n - 1 <= 20 and y - 11 <= 227, (bid, n, y)
        inner = o.a[3:h - 3, 3:w - 3].copy()
        inner[5:224, 5:174] = 0   # the text area (8,8)-(177,227) in page coordinates
        assert (inner == 0).all(), (bid, 'ink outside the text area')
        reg.add(bid, o, size, colours=(0, 13, 15), what='help page: ' + title)

    mv = 'Click the ground to walk there. Click the yellow ant to bring the view back to it.'
    page(4501, (185, 235), 'YELLOW ANT', [
        ('Movement', mv + ' Double-click inside a nest to dig.'),
        ('Moving things', 'Double-click a pebble or a bit of food to pick it up, and double-click again to put it down.'),
        ('Commands', '**Recruit** calls ants to follow you. **Release** lets them go again. **Exchange** swaps you into another ant.'),
    ])
    page(4503, (185, 235), 'NEW QUEEN', [
        ('Movement', mv),
        ('Dig Hole', 'First walk to a clear area, then pick this. If it fails, try other places until the hole works.'),
        ('Start Brood', 'Begins egg laying. You become the first ant to hatch.'),
    ])
    page(4505, (184, 235), 'SPIDER', [
        ('Movement', 'Click to walk and double-click to run. Click the spider to bring the view back to it.'),
        ('Chase', 'Pick it, then click an ant to eat it.'),
        ('Hunt', 'The spider looks for ants and attacks them on its own.'),
        ('Exchange', 'Switch back into an ant.'),
    ])


# =============================================================================================================
# C. tool icons (16 x 16, light grey square)
# =============================================================================================================
def shape(o, pts, fill, outline, th=0.0, cx=8.0, cy=8.0, k=1.0):
    """Polygon given in local coordinates (y down, origin at the tool centre), rotated by th degrees clockwise."""
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    q = [(cx + (x * c - y * s) * k, cy + (x * s + y * c) * k) for x, y in pts]
    if fill is not None:
        o.poly(q, fill)
    if outline is not None:
        for a, b in zip(q, q[1:] + q[:1]):
            o.line(int(round(a[0] - .5)), int(round(a[1] - .5)), int(round(b[0] - .5)), int(round(b[1] - .5)), outline)


def spade(o, th, cx, cy, k=1.0):
    shape(o, [(-1, -6.5), (1, -6.5), (1, 0), (-1, 0)], 10, 15, th, cx, cy, k)       # shaft
    shape(o, [(-3.5, -8), (3.5, -8), (3.5, -6), (-3.5, -6)], 10, 15, th, cx, cy, k)  # grip
    shape(o, [(-3.2, -0.5), (3.2, -0.5), (3.2, 3.5), (0, 8), (-3.2, 3.5)], 13, 15, th, cx, cy, k)  # blade


def dropper(o, th, cx, cy, k=1.0):
    shape(o, [(-1.6, -8), (1.6, -8), (2.6, -6), (2.6, -4.5), (-2.6, -4.5), (-2.6, -6)], 6, 15, th, cx, cy, k)  # bulb
    shape(o, [(-2.2, -4.5), (2.2, -4.5), (2.2, -3), (-2.2, -3)], 14, 15, th, cx, cy, k)                        # collar
    shape(o, [(-1.5, -3), (1.5, -3), (1.5, 3), (0.5, 7), (-0.5, 7), (-1.5, 3)], 0, 15, th, cx, cy, k)       # glass
    shape(o, [(-0.7, 0), (0.7, 0), (0.7, 3), (0, 6), (-0.7, 3)], 3, None, th, cx, cy, k)                    # liquid


def group_c(reg):
    def mk(bid, fn, what):
        o = Img(16, 16, FACE)
        fn(o)
        reg.add(bid, o, (16, 16), what=what)

    def magnifier(o):
        o.line(9, 9, 13, 13, 15, 3)
        o.line(10, 10, 13, 13, 10, 1)
        o.ellipse_o(6, 6, 4.2, 4.2, 7, 15)
        for p in ((3, 4), (4, 3), (3, 3), (4, 4)):
            o.px(p[0] + 1, p[1], 0)
        o.px(4, 4, 0)
        o.px(5, 3, 0)
        o.px(3, 5, 0)

    def rock(o):
        pts = [(3, 13), (1, 9), (3, 5), (7, 2), (12, 3), (14, 7), (14, 11), (11, 14)]
        o.poly(pts, 13)
        o.poly([(8, 13), (13, 10), (13, 12), (11, 13)], 14)
        o.poly([(5, 8), (10, 8), (11, 12), (6, 12)], 13)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            o.line(a[0], a[1], b[0], b[1], 15)
        o.line(4, 7, 6, 4, 0)
        o.line(7, 3, 10, 4, 0)
        o.px(3, 9, 0)
        o.line(8, 6, 7, 9, 15)
        o.line(7, 9, 9, 11, 15)

    def spade_icon(o):
        spade(o, 28, 8, 7.5)

    def ant(o):
        pics.ant_top(o, 8, 8, 15, None, 15, 1.0)
        o.px(7, 5, 14)
        o.px(7, 11, 14)
        o.px(7, 12, 14)

    def food(o):
        o.ellipse(7, 12.5, 6, 2, 13)
        o.ellipse_o(5.5, 9.0, 4.2, 3.0, 8, 9)
        o.ellipse_o(11, 5.5, 3.3, 2.6, 8, 9)
        o.px(4, 7, 0)
        o.px(5, 7, 0)
        o.px(10, 4, 0)
        o.px(11, 4, 0)
        o.px(7, 10, 9)
        o.px(12, 6, 9)

    def trail(o):
        dropper(o, 18, 9, 5.5, 0.85)
        for x in range(1, 15):
            if x % 4 < 3:
                o.px(x, 14, 3)
        for x in range(2, 15, 4):
            o.px(x, 13, 4)
            o.px(x + 1, 13, 4)

    def spray(o):
        o.rect(3, 7, 10, 16, 0)
        o.frame(3, 7, 10, 16, 15)
        o.rect(4, 10, 9, 14, 3)
        o.hline(4, 9, 10, 15)
        o.hline(4, 9, 14, 15)
        o.vline(6, 11, 14, 0)
        o.hline(5, 8, 12, 0)
        o.rect(4, 5, 9, 7, 14)
        o.frame(4, 5, 9, 7, 15)
        o.rect(5, 3, 8, 5, 15)
        o.px(5, 3, 14)
        for p in ((9, 3), (11, 2), (13, 1), (11, 4), (13, 4), (15, 3), (12, 6), (14, 7), (10, 1), (14, 5)):
            o.px(p[0], p[1], 6 if (p[0] + p[1]) % 2 else 7)

    def tools(o):
        spade(o, 45, 8, 8, 0.92)
        dropper(o, -45, 8, 8, 0.92)

    mk(5100, magnifier, 'Ant Info')
    mk(5101, rock, 'Barriers')
    mk(5102, spade_icon, 'Dig/Fill')
    mk(5103, ant, 'Add Ants')
    mk(5104, food, 'Add Food')
    mk(5105, trail, 'Drop Trails')
    mk(5106, spray, 'Insecticide')
    mk(5107, tools, 'tools')

    @reg.check
    def _c(reg):
        for k in range(8):
            assert len(set(int(v) for v in set(reg.img[5100 + k].a.flatten().tolist()))) <= 8, 5100 + k
