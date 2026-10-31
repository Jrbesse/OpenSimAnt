"""Groups I (win screen 16200 + eyes 16210..16212), J (tutorial pictures 17000..17013), K (encyclopedia button strips
21004, 21005) and L (start-up cards 28000, 28003).  See README.md."""
import math
import random
from uilib import *
import pics
from pics import pic_button, TAN, SOIL


# =============================================================================================================
# I. The win screen: a person, a cat and a dog, in flight.  No ant in it.
# =============================================================================================================
def limb(o, pts, r, fill, outline=INK):
    """A thick stroke through the points: radius r, 1-px outline."""
    def stroke(rad, c):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            n = max(abs(xb - xa), abs(yb - ya), 1)
            for i in range(n + 1):
                t = i / n
                o.ellipse(xa + (xb - xa) * t + 0.5, ya + (yb - ya) * t + 0.5, rad, rad, c)
    if outline is not None:
        stroke(r + 1, outline)
    stroke(r, fill)


def tri_o(o, pts, fill, outline=INK):
    o.poly(pts, fill)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        o.line(int(round(a[0] - 0.01)), int(round(a[1] - 0.01)), int(round(b[0] - 0.01)), int(round(b[1] - 0.01)), outline)


# eye squares (x, y = top-left corner) per creature and the creature's face colour
EYES = {'person': [(72, 74), (87, 66)], 'cat': [(175, 64), (191, 66)], 'dog': [(159, 122), (179, 124)]}
FACES = {'person': 11, 'cat': 2, 'dog': 11}


def socket(o, x, y):
    o.ellipse_o(x + 6.5, y + 6.5, 5.3, 5.3, 0, INK)


def scene(o):
    r = random.Random(16200)
    # sky and clouds
    o.rect(0, 0, 254, 110, 7)
    for cx, cy, rx in ((40, 18, 20), (110, 10, 24), (176, 24, 16)):
        o.ellipse(cx, cy + 2, rx, 7, 12)
        o.ellipse(cx, cy, rx, 7, 0)
        o.ellipse(cx - rx * 0.4, cy - 5, rx * 0.5, 6, 0)
        o.ellipse(cx + rx * 0.3, cy - 6, rx * 0.45, 6, 0)
    # fence behind everything
    o.rect(0, 100, 254, 152, 12)
    for x in range(0, 254, 16):
        top = 96 + (x // 16 % 2) * 2
        o.rect(x, top, x + 15, 152, 12)
        o.frame(x, top, x + 15, 152, 13)
        o.poly([(x, top), (x + 7.5, top - 5), (x + 15, top)], 12)
        o.line(x, top, x + 7, top - 5, 13)
        o.line(x + 8, top - 5, x + 14, top, 13)
        o.vline(x + 12, top + 3, 150, 0)
    o.rect(0, 112, 254, 115, 13)
    o.rect(0, 136, 254, 139, 13)
    o.hline(0, 254, 113, 0)
    o.hline(0, 254, 137, 0)
    # grass
    o.rect(0, 150, 254, 199, 8)
    o.rect(0, 150, 254, 153, 9)
    for _ in range(260):
        x, y = r.randrange(254), r.randrange(154, 199)
        o.px(x, y, 9)
        o.px(x, y - 1, 9)
    # the tree on the right
    o.rect(222, 0, 250, 152, SOIL)
    o.frame(222, 0, 250, 152, INK)
    o.vline(225, 0, 152, 11)
    o.vline(226, 0, 152, 11)
    for y in range(8, 150, 14):
        o.line(232, y, 236, y + 5, INK)
        o.line(240, y + 7, 244, y + 11, INK)
    o.ellipse(236, 12, 24, 14, 9)
    o.ellipse(214, 22, 14, 9, 9)
    o.ellipse(246, 26, 12, 8, 9)
    for _ in range(50):
        o.px(r.randrange(212, 254), r.randrange(0, 30), 8)
    o.ellipse(236, 152, 20, 3, 9)


def cat(o):
    # tail, body, legs (behind the head)
    limb(o, [(244, 100), (251, 76), (244, 52)], 4, 2)
    for y in (58, 70, 82, 94):
        o.line(241 + (y // 12) % 2, y, 249, y - 2, 3)
    o.ellipse_o(226, 102, 27, 19, 2, INK)
    for x in (216, 224, 232, 240):
        o.line(x, 86, x + 2, 93, 3)
    limb(o, [(214, 112), (216, 128)], 3, 2)
    limb(o, [(232, 116), (236, 130)], 3, 2)
    for p in ((214, 130), (217, 131), (235, 132), (238, 132)):
        o.line(p[0], p[1], p[0] - 1, p[1] + 3, INK)
    # head
    tri_o(o, [(167, 62), (163, 34), (184, 52)], 2)
    tri_o(o, [(208, 58), (216, 32), (195, 50)], 2)
    tri_o(o, [(168, 56), (167, 42), (177, 52)], 4)
    tri_o(o, [(206, 54), (211, 42), (199, 50)], 4)
    o.ellipse_o(189, 73, 25.5, 21.5, 2, INK)
    for x in (183, 189, 195):
        o.line(x, 52, x, 59 + (x == 189) * 2, 3)
    tri_o(o, [(186, 81), (193, 81), (189.5, 85)], 4)
    o.ellipse_o(189, 91, 8, 4, INK, INK)
    tri_o(o, [(183, 88), (186, 88), (184.5, 92)], 0)
    tri_o(o, [(193, 88), (196, 88), (194.5, 92)], 0)
    o.ellipse(189.5, 93.5, 3.5, 1.6, 3)
    for dy, dx in ((0, -18), (4, -16), (8, -17)):
        o.line(170, 82 + dy, 170 + dx, 79 + dy + (dy // 4) * 3, INK)
        o.line(208, 82 + dy, 208 - dx, 79 + dy + (dy // 4) * 3, INK)


def dog(o):
    # tail, body, legs, ears (behind the head)
    limb(o, [(254, 160), (252, 140), (246, 130)], 3, 11)
    o.ellipse_o(226, 168, 34, 20, 11, INK)
    o.ellipse(236, 164, 8, 6, 10)
    for pts in ([(206, 180), (196, 192), (186, 196)], [(216, 186), (222, 196), (212, 198)],
                [(240, 182), (250, 192), (254, 196)], [(250, 176), (256, 186)]):
        limb(o, pts, 4, 11)
    for p in ((186, 197), (212, 198), (254, 197)):
        o.ellipse_o(p[0], p[1], 5, 2, INK, INK)
    limb(o, [(153, 110), (145, 126), (141, 146)], 7, 10)
    limb(o, [(200, 108), (209, 124), (212, 144)], 7, 10)
    o.ellipse_o(176, 132, 30, 25, 11, INK)
    o.ellipse_o(176, 148, 13, 8.5, 12, INK)
    o.ellipse_o(176, 143, 5, 3, INK, INK)
    o.ellipse_o(176, 153, 8, 4.5, INK, INK)
    o.ellipse(178.5, 155.5, 4, 2.2, 3)
    limb(o, [(157, 117), (171, 119)], 1, 10, None)
    limb(o, [(181, 121), (195, 118)], 1, 10, None)


def person(o):
    # arms, flag, torso, legs (behind the head)
    o.line(130, 74, 130, 22, INK, 2)
    tri_o(o, [(132, 22), (168, 30), (132, 42)], 0)
    o.line(140, 27, 158, 31, 13)
    limb(o, [(110, 118), (130, 104), (131, 80)], 6, 6)
    o.ellipse_o(131, 74, 6, 6, 11, INK)
    limb(o, [(64, 120), (44, 104), (33, 82)], 6, 6)
    o.ellipse_o(33, 76, 6, 6, 11, INK)
    limb(o, [(78, 154), (60, 176), (44, 190)], 8, 14)
    limb(o, [(100, 154), (112, 174), (106, 190)], 8, 14)
    o.ellipse_o(40, 194, 10, 4.5, INK, INK)
    o.ellipse_o(104, 196, 10, 4, INK, INK)
    o.poly([(80, 102), (94, 100), (96, 116), (78, 118)], 11)
    tri_o(o, [(58, 112), (118, 106), (112, 156), (64, 160)], 6)
    o.line(86, 110, 88, 150, 5)
    o.ellipse(86, 112, 8, 4, 11)
    # head
    o.ellipse_o(55, 82, 5, 7, 11, INK)
    o.ellipse_o(117, 70, 5, 7, 11, INK)
    o.ellipse_o(86, 78, 31, 30, 11, INK)
    # hair: a cap above the brows with spikes
    for y in range(47, 57):
        for x in range(54, 120):
            if ((x + 0.5 - 86) / 31.8) ** 2 + ((y + 0.5 - 78) / 30.8) ** 2 <= 1.0:
                o.px(x, y, SOIL)
    o.hline(57, 116, 57, INK)
    for xa, xb, tip in ((58, 68, 30), (68, 78, 24), (78, 88, 28), (88, 99, 20), (99, 109, 30), (108, 117, 38)):
        tri_o(o, [(xa, 54), (xb, 54), ((xa + xb) / 2, tip)], SOIL)
    o.hline(58, 117, 54, SOIL)
    # brows, nose, mouth, cheeks
    o.line(71, 70, 84, 66, INK, 2)
    o.line(86, 63, 100, 58, INK, 2)
    o.ellipse_o(91, 88, 3.6, 3, 2, INK)
    o.ellipse(90, 101, 10, 7, INK)
    o.rect(83, 95, 98, 98, 0)
    o.ellipse(92, 105.5, 5.5, 2.5, 3)
    o.ellipse(66, 93, 4, 3, 3)
    o.ellipse(109, 90, 4, 3, 3)
    # sweat and fright marks
    for p in ((48, 58), (124, 56), (127, 84)):
        o.poly([(p[0], p[1] - 5), (p[0] - 3, p[1] + 1), (p[0] + 3, p[1] + 1)], 0)
        o.ellipse_o(p[0], p[1] + 1.5, 2.6, 2.6, 0, INK)
    for a, b in (((40, 62), (30, 56)), ((38, 74), (26, 74)), ((40, 88), (30, 94)),
                 ((124, 66), (136, 64)), ((126, 78), (138, 82))):
        o.line(a[0], a[1], b[0], b[1], INK)


def group_i(reg):
    o = Img(254, 199, 7)
    scene(o)
    cat(o)
    person(o)
    dog(o)
    # eye sockets: the neighbourhood of every eye square must be flat face colour (nothing drawn there yet)
    for who, sq in EYES.items():
        for (x, y) in sq:
            blk = o.a[y:y + 13, x:x + 13]
            assert (blk == FACES[who]).all(), ('something under the eye sprite', who, x, y,
                                               sorted(set(blk.flatten().tolist())))
            socket(o, x, y)
    reg.add(16200, o, (254, 199), what='win screen: a person, a cat and a dog in flight')

    @reg.check
    def _i(reg):
        a = reg.img[16200].a
        for who, sq in EYES.items():
            for (x, y) in sq:
                ref = Img(13, 13, FACES[who])
                socket(ref, 0, 0)
                assert (a[y:y + 13, x:x + 13] == ref.a).all(), ('eye square not face + socket', who, x, y)
        # the picture holds no ant: nothing yellow 1 / magenta 4 beyond the cat's inner ears, and no 6-legged shape check
        assert 1 not in set(np.unique(a).tolist()), 'yellow is the ant colour: not used on the win screen'

    # ---- the eyes
    mask = np.zeros((13, 13), dtype=bool)
    for y, (a0, a1) in {0: (3, 9), 1: (2, 10), 2: (1, 11)}.items():
        for yy in (y, 12 - y):
            mask[yy, a0:a1 + 1] = True
    mask[3:10, :] = True
    assert int((~mask).sum()) == 24

    def eye(frame):
        e = Img(13, 13, T)
        e.a[mask] = 0
        ring = np.zeros_like(mask)
        for y in range(13):
            for x in range(13):
                if mask[y, x]:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < 13 and 0 <= ny < 13) or not mask[ny, nx]:
                            ring[y, x] = True
        e.a[ring] = INK

        def pupil(cx, cy, n):
            if n == 5:
                cells = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3) if abs(dx) + abs(dy) < 4]
            else:
                cells = [(dx, dy) for dx in range(-1, 2) for dy in range(-1, 2)]
            for dx, dy in cells:
                e.px(cx + dx, cy + dy, INK)

        def dots(lst, c):
            for p in lst:
                e.px(p[0], p[1], c)
        if frame == 0:
            dots([(x, y) for y in range(1, 12) for x in range(1, 12)
                  if mask[y, x] and not ring[y, x] and x + y >= 17], 12)
            pupil(6, 6, 5)
            dots([(5, 5)], 0)
            dots([(2, 5), (3, 5), (3, 6), (10, 7), (9, 7), (6, 2), (6, 3)], 3)
        elif frame == 1:
            pupil(6, 6, 3)
            dots([(2, 4), (3, 4), (3, 5), (2, 8), (3, 8), (4, 7), (10, 4), (9, 4), (9, 5), (10, 8), (9, 8), (8, 7),
                  (5, 2), (5, 3), (7, 2), (7, 3), (5, 9), (5, 10), (7, 9), (7, 10)], 3)
        else:
            dots([(x, y) for y in range(1, 4) for x in range(1, 12) if mask[y, x] and not ring[y, x]], 12)
            pupil(7, 7, 5)
            dots([(7, 6)], 0)
            dots([(2, 6), (3, 6), (4, 6), (10, 6), (9, 6), (8, 10), (8, 9)], 3)
        return e
    for k in range(3):
        reg.add(16210 + k, eye(k), (13, 13), masked=True, colours=(0, 3, 12, 15), what='win screen eye, frame %d' % k)

    @reg.check
    def _eyes(reg):
        ms = [(reg.img[16210 + k].a == T) for k in range(3)]
        assert int(ms[0].sum()) == 24 and (ms[0] == ms[1]).all() and (ms[1] == ms[2]).all(), 'transparent pixels differ'
        assert not (reg.img[16210].a == reg.img[16211].a).all()
        assert not (reg.img[16211].a == reg.img[16212].a).all()
        assert not (reg.img[16212].a == reg.img[16210].a).all()


# =============================================================================================================
# J. Tutorial pictures
# =============================================================================================================
def framed(o, c=INK):
    o.frame(0, 0, o.w, o.h, c)
    return o


def speckle(o, seed, n, c=SOIL, base=TAN):
    r = random.Random(seed)
    for _ in range(n):
        x, y = r.randrange(1, o.w - 1), r.randrange(1, o.h - 1)
        if o.get(x, y) == base:
            o.px(x, y, c)


def group_j(reg):
    def add(bid, o, what):
        reg.add(bid, o, (o.w, o.h), what=what)

    # 17000 the player's ant on a sandy tile
    o = Img(22, 16, TAN)
    speckle(o, 1, 26)
    pics.ant_top(o, 11, 8.5, 1, INK, INK, 0.8)
    add(17000, framed(o), 'tutorial: the player\'s ant')

    # 17001 the surface strip: sky over grass over a thin soil line
    o = Img(53, 16, 7)
    for cx, cy, rx in ((12, 4, 6), (36, 3, 5)):
        o.ellipse(cx, cy, rx, 2, 0)
    o.rect(1, 9, 52, 13, 8)
    for x in range(1, 52, 3):
        o.px(x, 9, 9)
        o.px(x + 1, 10, 9)
    o.rect(1, 13, 52, 15, SOIL)
    add(17001, framed(o), 'tutorial: the surface strip at the top of the nest')

    # 17002 food
    o = Img(19, 18, TAN)
    speckle(o, 2, 22)
    o.ellipse(8, 12.6, 6, 2, SOIL)
    o.ellipse_o(6.5, 7.5, 3.8, 3.0, 8, 9)
    o.ellipse_o(12.5, 11, 3.3, 2.7, 8, 9)
    for p in ((5, 6), (6, 6), (11, 10), (12, 10)):
        o.px(p[0], p[1], 0)
    o.px(7, 9, 9)
    o.px(13, 12, 9)
    add(17002, framed(o), 'tutorial: food')

    # 17003 the nest entrance: a mound with a dark hole
    o = Img(53, 48, TAN)
    speckle(o, 3, 120)
    o.ellipse(27, 28, 23, 18, SOIL)
    o.ellipse(26, 26, 21, 16, TAN)
    o.ellipse(26, 27, 17, 13, SOIL)
    r = random.Random(33)
    for _ in range(70):
        x, y = r.randrange(5, 48), r.randrange(10, 42)
        if o.get(x, y) == TAN:
            o.px(x, y, SOIL)
    o.ellipse(26, 27, 14, 10.5, 14)
    o.ellipse(27, 28, 13, 9.5, INK)
    o.line(14, 24, 18, 20, 13)
    o.line(20, 19, 29, 17, 13)
    add(17003, framed(o), 'tutorial: the nest entrance')

    # 17004 a small rock
    o = Img(20, 18, TAN)
    speckle(o, 4, 22)
    o.ellipse(11, 15.5, 7, 1.6, SOIL)
    pts = [(4, 14), (2, 9), (5, 5), (10, 3), (15, 5), (18, 9), (17, 13), (12, 15)]
    o.poly(pts, 13)
    o.poly([(10, 15), (17, 12), (18, 9), (15, 9), (12, 12)], 14)
    o.poly([(3, 9), (5, 5), (10, 3), (13, 4), (8, 7), (5, 11)], 12)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        o.line(a[0], a[1], b[0], b[1], INK)
    o.line(9, 8, 8, 11, INK)
    add(17004, framed(o), 'tutorial: a small rock')

    # crops of the Map toolbar 14000 (copied, bevel included)
    t = reg.img[14000]
    add(17005, t.crop(2, 3, 43, 33), 'tutorial: Yard button (crop of 14000)')
    add(17008, t.crop(262, 24, 287, 44), 'tutorial: Behavior Control button (crop of 14000)')
    add(17009, t.crop(366, 24, 391, 44), 'tutorial: ? help button (crop of 14000)')
    add(17011, t.crop(288, 24, 313, 44), 'tutorial: Caste Control button (crop of 14000)')
    add(17012, t.crop(291, 5, 312, 21), 'tutorial: Center on Yellow face (crop of 14000)')

    # 17006 / 17007: plain 3-D buttons of the yard window's toolbar (a later batch may crop its own)
    add(17006, pic_button(37, 29, pics.house_yard), 'tutorial: yard window House button')
    add(17007, pic_button(41, 30, lambda w, h: pics.surface(w, h, 8)), 'tutorial: yard window Patch button')

    # 17010 the population gauges: P above H, black fill on white
    o = Img(75, 21, FACE)
    o.frame(0, 0, 75, 21, DSH)
    for (y0, y1, ch, fill) in ((3, 11, 'P', 22), (14, 19, 'H', 14)):
        o.rect(10, y0, 74, y1, 0)
        o.frame(9, y0 - 1, 75, y1 + 1, INK)
        o.rect(10, y0, 10 + fill, y1, INK)
        text(o, 2, y0 + (y1 - y0 - 7) // 2, ch, SMALL, 9)
    add(17010, o, 'tutorial: the population gauges')

    # 17013 the vertical health gauge
    o = Img(84, 65, FACE)
    o.frame(0, 0, 84, 65, DSH)
    o.rect(7, 5, 25, 53, 0)
    o.frame(6, 4, 26, 54, INK)
    o.rect(7, 24, 25, 53, PLAYER)
    o.hline(6, 30, 36, INK)
    o.rect(10, 54, 22, 63, INK)
    text_c(o, 16, 55, 'Y', LABEL, PLAYER)
    text(o, 32, 20, 'Health', LABEL, INK)
    o.hline(26, 31, 23, INK)
    o.hline(7, 26, 23, INK)
    text(o, 32, 33, 'Eat level', LABEL, INK)
    add(17013, o, 'tutorial: the vertical health gauge')

    @reg.check
    def _j(reg):
        t = reg.img[14000].a
        for bid, (x0, y0, x1, y1) in ((17005, (2, 3, 43, 33)), (17008, (262, 24, 287, 44)), (17009, (366, 24, 391, 44)),
                                      (17011, (288, 24, 313, 44)), (17012, (291, 5, 312, 21))):
            assert (reg.img[bid].a == t[y0:y1, x0:x1]).all(), bid
            assert (reg.img[bid].w, reg.img[bid].h) == (x1 - x0, y1 - y0)
        for bid in range(17000, 17014):
            assert not (reg.img[bid].a == T).any()
        # the crops cover their button: the button's own rectangle lies inside the window
        assert reg.img[17010].a[3, 10] == INK and reg.img[17010].a[10, 73] == 0


# =============================================================================================================
# K. Encyclopedia button strips (1 plane: only 0 and 15)
# =============================================================================================================
def strip(buttons):
    o = Img(320, 20, 0)
    for y in range(20):
        for x in range(320):
            o.a[y, x] = INK if (x + y) % 2 == 0 else 0
    o.hline(0, 320, 0, INK)
    for (x0, y0, x1, y1, label) in buttons:
        bx0, by0, bx1, by1 = x0 - 1, y0 - 1, x1 + 1, y1 + 1       # outline ring around the hit rectangle
        o.rect(bx0 + 1, by0 + 1, bx1 + 1, by1 + 1, INK)           # shadow, right and below
        o.rect(bx0, by0, bx1, by1, INK)
        o.rect(bx0 + 1, by0 + 1, bx1 - 1, by1 - 1, 0)
        text_c(o, (bx0 + bx1) // 2, by0 + (by1 - by0 - 7) // 2, label, LABEL, INK)
        w = LABEL.width(label)
        assert w <= bx1 - bx0 - 6, label
    return o


def group_k(reg):
    back, prev, top = (17, 4, 81, 17, 'BACK'), (128, 4, 192, 17, 'PREVIOUS'), (239, 4, 303, 17, 'TOP')
    reg.add(21004, strip([back, prev, top]), (320, 20), colours=(0, 15), what='encyclopedia buttons BACK PREVIOUS TOP')
    reg.add(21005, strip([prev]), (320, 20), colours=(0, 15), what='encyclopedia button PREVIOUS')

    @reg.check
    def _k(reg):
        for bid, hits in ((21004, [(17, 4, 81, 17), (128, 4, 192, 17), (239, 4, 303, 17)]), (21005, [(128, 4, 192, 17)])):
            a = reg.img[bid].a
            assert set(np.unique(a).tolist()) <= {0, 15}
            assert (a[0, :] == INK).all(), 'first row is a solid black divider'
            for (x0, y0, x1, y1) in hits:
                assert (a[y0 - 1, x0 - 1:x1 + 1] == INK).all() and (a[y1, x0 - 1:x1 + 1] == INK).all()
                assert (a[y0 - 1:y1 + 1, x0 - 1] == INK).all() and (a[y0 - 1:y1 + 1, x1] == INK).all()
                assert (a[y0, x0] == 0) and (a[y1 + 1, x0:x1 + 2] == INK).all() and (a[y0:y1 + 2, x1 + 1] == INK).all()
            # elsewhere the strip is the 50 % checkerboard
            m = np.ones((20, 320), dtype=bool)
            m[0, :] = False
            for (x0, y0, x1, y1) in hits:
                m[y0 - 1:y1 + 3, x0 - 1:x1 + 3] = False
            yy, xx = np.nonzero(m)
            assert all(a[y, x] == (INK if (x + y) % 2 == 0 else 0) for y, x in zip(yy, xx))
    # (nothing else)


# =============================================================================================================
# L. Start-up cards: a neutral emblem and one line of lettering
# =============================================================================================================
def hexagon(o, cx, cy, R, fill, outline):
    pts = [(cx + R * math.cos(math.radians(30 + 60 * k)), cy + R * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    o.poly(pts, fill)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        o.line(int(round(a[0] - 0.5)), int(round(a[1] - 0.5)), int(round(b[0] - 0.5)), int(round(b[1] - 0.5)), outline)


def card(w, h):
    o = Img(w, h, INK)
    R = int(h * 0.1)
    cx, cy = w / 2.0, h * 0.37
    d = math.sqrt(3) * R * 1.07
    hexagon(o, cx, cy, R, 1, 0)
    hexagon(o, cx, cy, R * 0.55, 2, 3)
    ring = [3, 4, 5, 6, 7, 8]
    for k in range(6):
        a = math.radians(60 * k - 30)
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        hexagon(o, x, y, R, ring[k], 0)
        hexagon(o, x, y, R * 0.5, 14, 15)
    # a small rule with a diamond under the emblem
    ry = int(cy + 2.6 * R + h * 0.045)
    o.hline(int(w * 0.25), int(w * 0.75), ry, 14)
    o.poly([(w / 2 - 4, ry), (w / 2, ry - 4), (w / 2 + 4, ry), (w / 2, ry + 4)], 1)
    # the single line of lettering: yellow face, orange and red shadow steps (display lettering, 2x)
    s = 'AN OPEN FAN PROJECT'
    tw = SMALL.width(s) * 2
    assert tw <= w - 20, (tw, w)
    tx, ty = (w - tw) // 2 - 1, int(h * 0.76)
    text(o, tx + 2, ty + 2, s, SMALL, 3, scale=2)
    text(o, tx + 1, ty + 1, s, SMALL, 2, scale=2)
    text(o, tx, ty, s, SMALL, 1, scale=2)
    return o


def group_l(reg):
    reg.add(28000, card(263, 204), (263, 204), what='start-up card (neutral)')
    reg.add(28003, card(257, 195), (257, 195), what='start-up card (neutral, smaller)')
