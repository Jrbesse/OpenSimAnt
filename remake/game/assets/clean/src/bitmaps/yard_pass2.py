"""yard_pass2: pass 2 of the yard spec: the yard toolbar 7010 (512 x 46, opaque) and its help overlay 7011 (512 x 47, masked),
the pictures of its buttons (drawn once each), the two crops for the tutorial (17006 / 17007) and the assertions.

Layout (picture coordinates; hit rectangles x1 / y1 exclusive).  A picture button's visible box is its hit rectangle grown by
1 px at the left and top and 2 px at the right and bottom (raised bevel outside the hit rectangle); the radio buttons and the
help button have their bevel inside the hit rectangle.  Labels are the interface batch's bold face (uilib.LABEL), cap height 7,
rows 35..41, centred under their buttons.
"""
import numpy as np

from uilib import (Img, T, LABEL, SMALL, text, text_c, text_r, bevel, groove, inv_ok, contrast, lum, FACE, HEX)

# ---------------------------------------------------------------------------------------------- the controls (hit rectangles)
HIT = {
    'patch': (7, 5, 40, 31), 'house': (47, 5, 80, 31), 'strat': (87, 5, 120, 31), 'graphic': (126, 5, 159, 31),
    'mate': (173, 5, 207, 32), 'queens': (215, 21, 249, 31), 'auto': (257, 6, 317, 17), 'manual': (257, 20, 317, 31),
    'place': (324, 5, 357, 32), 'help': (367, 25, 390, 43), 'black': (473, 7, 507, 17), 'red': (473, 27, 507, 37),
}
LABELS = [('patch', 'Patch'), ('house', 'House'), ('strat', 'Strat'), ('graphic', 'Graphic'), ('mate', 'MATE'), ('place', 'PLACE')]
PICTURE_BUTTONS = ('patch', 'house', 'strat', 'graphic', 'mate', 'place')
INVERTED = ('house', 'strat', 'graphic', 'place', 'auto', 'manual')     # shown inverted by the game while selected / active
TEXT_RECTS = ('queens', 'black', 'red')


def box_of(r):
    return (r[0] - 1, r[1] - 1, r[2] + 2, r[3] + 2)


def size_of(r):
    return (r[2] - r[0], r[3] - r[1])


# ---------------------------------------------------------------------------------------------- the button pictures (hit-rectangle size)
def _ring(im):
    im.frame(0, 0, im.w, im.h, 15)


def pic_patch(w, h):
    """The ground of a patch seen from above: tan soil with specks, crumbs of food and a few ants."""
    im = Img(w, h, 11)
    rs = np.random.RandomState(5)
    for _ in range(60):
        im.px(int(rs.randint(1, w - 1)), int(rs.randint(1, h - 1)), 10)
    for _ in range(14):
        im.px(int(rs.randint(1, w - 1)), int(rs.randint(1, h - 1)), 12)
    for (x, y) in ((6, 6), (22, 5), (9, 17), (25, 16)):                  # food: little heaps
        im.rect(x, y, x + 3, y + 2, 2)
        im.px(x, y, 1)
    for (x, y, d) in ((13, 10, 1), (17, 14, 1), (4, 12, 0), (20, 10, 0), (27, 21, 1)):   # ants: dot-sized, black
        im.rect(x, y, x + 2, y + 1, 15)
        im.px(x + (3 if d else -1), y, 15)
        im.px(x + d, y - 1, 15)
    im.ellipse(15, 20, 3, 2, 13)                                         # a pebble
    _ring(im)
    return im


def pic_house(w, h):
    """The house and its lawn, front view."""
    im = Img(w, h, 0)
    cx = w // 2
    im.rect(1, h - 6, w - 1, h - 5, 15)                                    # the ground line
    for x in range(2, w - 2, 3):                                           # grass tufts
        im.px(x, h - 4, 8)
        im.px(x + 1, h - 3, 8)
    im.rect(cx - 9, 12, cx + 9, h - 6, 15)                                 # walls: outline, grey face
    im.rect(cx - 8, 13, cx + 8, h - 6, 12)
    im.poly([(cx - 13, 12), (cx, 3), (cx + 13, 12)], 15)                   # the roof
    im.rect(cx + 4, 4, cx + 7, 9, 15)                                      # chimney
    im.rect(cx - 2, h - 13, cx + 2, h - 6, 15)                             # the door
    im.px(cx + 1, h - 10, 12)
    for wx in (cx - 7, cx + 4):                                            # windows
        im.rect(wx, 15, wx + 4, 19, 15)
        im.rect(wx + 1, 16, wx + 3, 18, 0)
    _ring(im)
    return im


def _cell(c, r, x0=9, y0=4, cw=5, ch=5, sh=2):
    return (x0 + cw * c - sh * r, y0 + ch * r)


def _grid(w, h, kinds, bars=False):
    im = Img(w, h, 0)
    x0 = 11 if w >= 33 else 10
    for r in range(4):
        for c in range(5):
            tl, tr = _cell(c, r, x0), _cell(c + 1, r, x0)
            bl, br = _cell(c, r + 1, x0), _cell(c + 1, r + 1, x0)
            k = kinds.get((c, r))
            poly = [tl, tr, br, bl]
            if k in (15, 3, 8):
                im.poly(poly, k)
            elif k == 'chk':
                tmp = Img(w, h, T)
                tmp.poly(poly, 15)
                ys, xs = np.where(tmp.a == 15)
                for y, x in zip(ys, xs):
                    im.a[y, x] = 15 if (x + y) % 2 == 0 else 3
            elif k == 'bar15' or k == 'bar3':
                cxm, cym = tl[0] + 3 - 0, tl[1] + 4
                col = 15 if k == 'bar15' else 3
                im.rect(cxm - 1, cym - 3 - (c + r) % 2, cxm + 1, cym + 1, col)
    for r in range(5):                                                    # lines
        a, b = _cell(0, r, x0), _cell(5, r, x0)
        im.line(a[0], a[1], b[0], b[1], 15)
    for c in range(6):
        a, b = _cell(c, 0, x0), _cell(c, 4, x0)
        im.line(a[0], a[1], b[0], b[1], 15)
    _ring(im)
    return im


def pic_strat(w, h):
    kinds = {(1, 0): 15, (3, 0): 3, (0, 1): 3, (2, 1): 'chk', (1, 2): 8, (3, 2): 15, (4, 2): 15, (0, 3): 'chk', (2, 3): 3, (3, 3): 8, (4, 1): 15}
    return _grid(w, h, kinds)


def pic_graphic(w, h):
    kinds = {(1, 0): 'bar15', (3, 0): 'bar3', (0, 1): 'bar3', (2, 1): 'bar15', (4, 1): 'bar15', (1, 2): 'bar15', (3, 2): 'bar3',
             (2, 3): 'bar15', (4, 2): 'bar3', (0, 3): 'bar3'}
    return _grid(w, h, kinds)


def _winged(im, x, y):
    """A small winged ant in flight: wings (outlined pale), body black.  (x, y) = its body's centre."""
    for (dx, dy, ex, ey) in ((-1, -1, -5, -4), (1, -1, 5, -4)):
        im.line(x + dx, y + dy, x + ex, y + ey, 15)
        im.line(x + dx, y + dy + 1, x + ex, y + ey, 13)
    im.rect(x - 1, y - 1, x + 2, y + 2, 15)
    im.rect(x - 3, y, x - 1, y + 2, 15)                                    # abdomen
    im.px(x + 2, y - 1, 15)                                                # head
    im.px(x + 3, y - 2, 15)


def pic_mate(w, h):
    im = Img(w, h, 0)
    for (x, y) in ((9, 8), (23, 6), (17, 17)):
        _winged(im, x, y)
    im.rect(2, h - 5, 7, h - 4, 12)
    im.rect(26, h - 9, 31, h - 8, 12)
    _ring(im)
    return im


def pic_place(w, h):
    im = Img(w, h, 0)
    gy = h - 6
    im.rect(1, gy, w - 1, h - 1, 14)                                       # the ground
    for x in range(2, w - 2, 4):
        im.px(x, gy, 13)
    cx = w // 2
    _winged(im, cx, gy - 8)
    im.px(cx, gy - 3, 13)                                                  # the way down
    im.px(cx, gy - 1, 13)
    im.rect(cx - 2, gy, cx + 3, gy + 1, 15)                                # the spot where she will land
    _ring(im)
    return im


# ---------------------------------------------------------------------------------------------- the question mark
def pic_help(w, h):
    im = Img(w, h, FACE)
    bevel(im, 0, 0, w, h, FACE, True)
    rows = ["..####..", ".##..##.", ".##..##.", ".....##.", "....##..", "...##...", "...##...", "........", "...##...", "...##..."]
    ox, oy = (w - 8) // 2, (h - 10) // 2
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch == '#':
                im.px(ox + x, oy + y, 9)
    return im


# ---------------------------------------------------------------------------------------------- the toolbar 7010
def build_toolbar():
    t = Img(512, 46, FACE)
    t.rect(0, 0, 512, 1, 0)                                                # top row white, left column white
    t.rect(0, 0, 1, 46, 0)
    t.rect(511, 1, 512, 46, 13)
    t.rect(1, 45, 512, 46, 15)                                             # bottom row black
    pics = {'patch': pic_patch, 'house': pic_house, 'strat': pic_strat, 'graphic': pic_graphic, 'mate': pic_mate, 'place': pic_place}
    for name in PICTURE_BUTTONS:
        r = HIT[name]
        bx = box_of(r)
        bevel(t, bx[0], bx[1], bx[2], bx[3], FACE, True, deep=True)
        w, h = size_of(r)
        t.blit(pics[name](w, h), r[0], r[1])
    for name, word in (('auto', 'AUTOMATIC'), ('manual', 'MANUAL')):
        r = HIT[name]
        bevel(t, r[0], r[1], r[2], r[3], FACE, True)
        if LABEL.width(word) > 56:
            word = 'AUTO'
        text_c(t, (r[0] + r[2]) // 2, r[1] + 2, word, LABEL, 15)
    r = HIT['help']
    t.blit(pic_help(*size_of(r)), r[0], r[1])
    # text rectangles: flat white, framed outside
    for name in TEXT_RECTS:
        r = HIT[name]
        t.rect(r[0], r[1], r[2], r[3], 0)
        t.frame(r[0] - 1, r[1] - 1, r[2] + 1, r[3] + 1, 15)
    text_c(t, (HIT['queens'][0] + HIT['queens'][2]) // 2, 9, 'Queens', LABEL, 15)
    r = HIT['black']
    text_r(t, 470, r[1] + 2, 'BLACK COLONIES', LABEL, 15)
    r = HIT['red']
    text_r(t, 470, r[1] + 2, 'RED COLONIES', LABEL, 3)
    # dividers between the groups
    groove(t, 165, 3, 167, 43)
    groove(t, 362, 3, 364, 43)
    # labels under the picture buttons
    for name, word in LABELS:
        r = HIT[name]
        text_c(t, (r[0] + r[2]) // 2, 35, word, LABEL, 15)
    return t


# ---------------------------------------------------------------------------------------------- the help overlay 7011
# (x0, x1, top row, lines); overlay x = toolbar x + 2; every box ends on row 46
BOXES = [
    (0, 45, 10, ['Back to', 'patch', 'view']),
    (45, 85, 10, ['Inside /', 'outside', 'view']),
    (85, 125, 10, ['Colour', 'grid by', 'colony']),
    (125, 168, 10, ['Colony', 'bars per', 'patch']),
    (168, 213, 10, ['Start', 'mating', 'flight']),
    (213, 255, 10, ['Queens', 'waiting', 'to land']),
    (255, 322, 10, ['Game places', 'queens, or', 'you place']),
    (322, 363, 10, ['Found a', 'colony']),
    (443, 512, 20, ['Colonies', 'alive now']),
]
BOX_COVERS = [(9, 42), (49, 82), (89, 122), (128, 161), (175, 209), (217, 251), (259, 319), (326, 359), (475, 509)]
TABS = [((10, 60), 'Views'), ((200, 250), 'Mating')]            # x0, x1 of the heading tabs (rows 0..10)


def build_overlay():
    o = Img(512, 47, T)
    for (x0, x1, top, lines) in BOXES:
        o.rect(x0, top, x1, 47, 0)
        o.frame(x0, top, x1, 47, 14)
        n = len(lines)
        y = top + 2 + (47 - top - 4 - (11 * (n - 1) + 7)) // 2
        for i, s in enumerate(lines):
            text_c(o, (x0 + x1) // 2, y + 11 * i, s, SMALL, 15)
    for ((x0, x1), word) in TABS:
        o.rect(x0, 0, x1, 11, 0)
        o.rect(x0, 0, x1, 1, 14)
        o.rect(x0, 0, x0 + 1, 11, 14)
        o.rect(x1 - 1, 0, x1, 11, 14)
        o.rect(x0 + 1, 10, x1 - 1, 11, 0)                                # joined to the band: no frame between tab and box
        text_c(o, (x0 + x1) // 2, 2, word, SMALL, 15)
    return o


# ---------------------------------------------------------------------------------------------- crops for the tutorial
CROPS = {17006: (45, 4, 82, 33), 17007: (4, 3, 45, 33)}          # x0, y0, x1, y1 of 7010; sizes 37 x 29 and 41 x 30


def crop_of(t7010, bid):
    x0, y0, x1, y1 = CROPS[bid]
    return t7010.crop(x0, y0, x1, y1)


# ---------------------------------------------------------------------------------------------- register + checks
def build(reg):
    t = build_toolbar()
    o = build_overlay()
    reg.add(7010, t, (512, 46), False, None, 'yard window toolbar')
    reg.add(7011, o, (512, 47), True, (0, 14, 15), 'yard window toolbar help overlay (masked)')
    for name in TEXT_RECTS:
        reg.flat_rect(7010, HIT[name], 0, 'text rectangle ' + name)
    reg.check(check_pass2)
    return t, o


def _dominants(sub):
    vals, cnt = np.unique(sub, return_counts=True)
    order = np.argsort(-cnt, kind='stable')
    top2 = [int(vals[i]) for i in order[:2]]
    light = [(int(c), int(v)) for v, c in zip(vals, cnt) if lum(int(v)) >= 0.18]
    dark = [(int(c), int(v)) for v, c in zip(vals, cnt) if lum(int(v)) < 0.18]
    return top2, (max(light)[1] if light else None), (max(dark)[1] if dark else None)


def contrast_report(t, name):
    r = HIT[name]
    sub = t.a[r[1]:r[3], r[0]:r[2]]
    top2, l, d = _dominants(sub)
    inv = _dominants(sub ^ 15)
    return top2, (l, d), inv


def check_pass2(reg):
    t = reg.img[7010]
    o = reg.img[7011]
    a = t.a
    # panel
    assert (a[0, :] == 0).all() and (a[45, 1:] == 15).all() or (a[45] == 15).all(), 'top row white, bottom row black'
    # every control's picture lies in its box; the text rectangles are flat white
    for name in TEXT_RECTS:
        r = HIT[name]
        assert (a[r[1]:r[3], r[0]:r[2]] == 0).all(), name
    # labels: ink only in rows 35..43 under the picture buttons, none in rows 33..34 and 44
    for name, word in LABELS:
        r = HIT[name]
        x0, x1 = r[0] - 4, r[2] + 4
        band = a[34:45, x0:x1]
        ink = np.argwhere(band == 15)
        assert len(ink) and ink[:, 0].min() + 34 == 35, ('label ink starts at row 35', name)
        assert ink[:, 0].max() + 34 <= 43, name
        assert (a[34, r[0]:r[2]] == 12).all(), ('row 34 under the button is panel', name)
    # labels do not run into each other
    spans = []
    for name, word in LABELS:
        r = HIT[name]
        wd = LABEL.width(word)
        cx = (r[0] + r[2]) // 2
        spans.append((cx - wd // 2, cx - wd // 2 + wd, word))
    spans.sort()
    for (a0, a1, w0), (b0, b1, w1) in zip(spans, spans[1:]):
        assert b0 - a1 >= 2, ('labels touch', w0, w1)
    # boxes: raised bevel outside the hit rectangle (highlight top / left, shadow bottom / right)
    for name in PICTURE_BUTTONS:
        r = HIT[name]
        bx = box_of(r)
        assert (a[bx[1], bx[0]:bx[2] - 1] == 0).all() and (a[bx[1]:bx[3] - 1, bx[0]] == 0).all(), ('bevel highlight', name)
        assert (a[bx[3] - 1, bx[0] + 1:bx[2]] == 14).all() and (a[bx[1] + 1:bx[3], bx[2] - 1] == 14).all(), ('bevel shadow', name)
        sub = a[r[1]:r[3], r[0]:r[2]]
        ring = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])
        assert set(np.unique(ring).tolist()) <= {0, 15}, ('the ring of the hit rectangle is black / white', name)
    # the 3 : 1 contrast of the inverted buttons, as drawn and with every pixel XOR-ed with 15
    rep = {}
    for name in INVERTED:
        r = HIT[name]
        sub = a[r[1]:r[3], r[0]:r[2]]
        for state, s in (('drawn', sub), ('inverted', sub ^ 15)):
            top2, ld, dd = _dominants(s)[0], _dominants(s)[1], _dominants(s)[2]
            c_top = contrast(top2[0], top2[1])
            assert c_top >= 3.0, (name, state, 'two most frequent colours', top2, round(c_top, 2))
            assert ld is not None and dd is not None and contrast(ld, dd) >= 3.0, (name, state, 'dominant light / dark', ld, dd)
        rep[name] = _dominants(sub)
    reg.stats = getattr(reg, 'stats', {})
    reg.stats['contrast'] = rep
    # the crops
    for bid, (x0, y0, x1, y1) in CROPS.items():
        assert (x1 - x0, y1 - y0) == ((37, 29) if bid == 17006 else (41, 30)), bid
        bx = box_of(HIT['house' if bid == 17006 else 'patch'])
        assert x0 <= bx[0] and y0 <= bx[1] and x1 >= bx[2] and y1 >= bx[3], ('the box lies inside its window', bid)
        assert y1 <= 35, ('the window ends above the label', bid)
        sub = a[y0:y1, x0:x1]
        assert not (sub == 15).all(), bid
        assert crop_of(t, bid).a.shape == (y1 - y0, x1 - x0)
    assert CROPS[17006][0] == box_of(HIT['house'])[0] - 1 and CROPS[17006][1] == box_of(HIT['house'])[1]
    assert CROPS[17007][1] == box_of(HIT['patch'])[1] - 1 and CROPS[17007][0] == box_of(HIT['patch'])[0] - 2 and CROPS[17007][2] == box_of(HIT['patch'])[2] + 3
    # the overlay: colours, boxes
    assert set(np.unique(o.a).tolist()) <= {T, 0, 14, 15}, 'overlay colours'
    for (x0, x1, top, lines), (c0, c1) in zip(BOXES, BOX_COVERS):
        assert (o.a[46, x0:x1] == 14).all(), ('every callout box ends on row 46', x0)
        mid0, mid1 = c0 + 0.2 * (c1 - c0), c1 - 0.2 * (c1 - c0)
        assert x0 <= mid0 and x1 >= mid1, ('a box covers the middle 60 % of its button', x0, x1, c0, c1)
        for ln in lines:
            assert SMALL.width(ln) <= (x1 - x0) - 4, ('text fits the box', ln, x0, x1)
    for (a0, a1, top, _), (b0, b1, top2, _) in zip(BOXES[:7], BOXES[1:8]):
        assert a1 == b0, 'the left group is without gaps or overlaps'
    assert BOXES[0][0] == 0 and BOXES[7][1] == 363
    assert BOXES[0][2] == 10 and all(b[2] == 10 for b in BOXES[:8]) and BOXES[8][2] == 20 and BOXES[8][0] == 443 and BOXES[8][1] == 512
    for ((tx0, tx1), _w) in TABS:
        assert 40 <= tx1 - tx0 <= 60
        assert (o.a[0:11, tx0:tx1] != T).all()
    assert 9 <= TABS[0][0][0] and TABS[0][0][1] <= 162 and 175 <= TABS[1][0][0] and TABS[1][0][1] <= 360
    # the toolbar rows 0..3 are covered by overlay rows 43..46 and the buttons (rows >= 5) never are
    assert (o.a[47 - 1:, :] != T).any()
    # row 46 of the overlay is the picture's last row: the foot of the band is one dark line
    assert (o.a[46, 0:363] == 14).all()
