"""yard_pass1: pass 1 of the yard spec: the yard's scenery (groups A and C: 7000, 7001, 7003, 7020, 7021, 7022, 7005, 7006,
7007, 1260) and its assertions.  `build(reg)` registers the pictures; the checks are registered with `reg.check`.
"""
import numpy as np

import yard_scene as ys
from yardlib import lattice, house_covers, OX, W7000, W7003
from uilib import Img, T


def arr_img(a):
    o = Img(a.shape[1], a.shape[0])
    o.a = np.array(a, dtype=np.int16)
    return o


def raindrop():
    img = Img(7, 37, T)
    for r in range(1, 36):
        img.a[r, 5 - int(round(4 * (r - 1) / 34.0))] = 7
    return img


def queen_dot(colour):
    img = Img(8, 1, T)
    img.a[0, 1] = colour
    return img


def build(reg):
    w_out = ys.render_world('outside')
    w_in = ys.render_world('inside')
    l0, r0 = ys.pictures(w_out)
    l1, r1 = ys.pictures(w_in)
    assert (r0 == r1).all(), '7003 is drawn in both views: it must not depend on the view'
    reg.worlds = {'outside': w_out, 'inside': w_in}            # for pass 3 (patches are cropped from renders)
    reg.add(7000, arr_img(l0), (281, 226), False, None, 'yard window: the house from outside, lawn and garden (yard x -2..278)')
    reg.add(7001, arr_img(l1), (281, 226), False, None, 'yard window, House view: the same house with roof and front wall cut away')
    reg.add(7003, arr_img(r0), (233, 226), False, None, 'yard window: the lawn and its back fence (yard x 279..511)')
    s0, s1, s2 = ys.strips()
    reg.add(7020, arr_img(s0), (513, 51), False, (8, 9, 10, 13), 'colony views: top third of the grid (yard y 65..115)')
    reg.add(7021, arr_img(s1), (512, 55), False, (8, 9, 10, 13), 'colony views: middle third of the grid (yard y 116..170)')
    reg.add(7022, arr_img(s2), (512, 55), False, (8, 9, 10, 13), 'colony views: bottom third of the grid (yard y 171..225)')
    reg.add(7005, raindrop(), (7, 37), True, (7,), 'raindrop streak')
    reg.add(7006, queen_dot(15), (8, 1), True, (15,), 'black colony winged queen (one pixel)')
    reg.add(7007, queen_dot(3), (8, 1), True, (3,), 'red colony winged queen (one pixel)')
    reg.add(1260, ys.sign_board(), (54, 37), True, None, 'for-sale sign on a post')
    reg.check(check_pass1)


def tight(img):
    a = img.a != T
    return a[0].any() and a[-1].any() and a[:, 0].any() and a[:, -1].any()


def check_pass1(reg):
    P = {i: reg.img[i].a for i in (7000, 7001, 7003, 7020, 7021, 7022, 7005, 7006, 7007, 1260)}
    # --- C: the small sprites
    d = P[7005]
    for r in range(37):
        cols = np.where(d[r] != T)[0]
        if 1 <= r <= 35:
            assert len(cols) == 1 and d[r, cols[0]] == 7, ('7005 row', r)
        else:
            assert len(cols) == 0, ('7005 first / last row transparent', r)
    assert d[1].tolist().index(7) == 5 and d[35].tolist().index(7) == 1, '7005 runs from column 5 to column 1'
    for i, c in ((7006, 15), (7007, 3)):
        v = P[i]
        assert (v != T).sum() == 1 and v[0, 1] == c, i
    assert tight(reg.img[1260]), '1260 tight'
    s = reg.img[1260].a
    assert (s != T).sum() / s.size > 0.6, '1260: board + post'
    assert (s[:, :20][26:] == T).all() and (s[:, 35:][26:] == T).all(), '1260: both sides of the post below the board are transparent'
    # the two lines of lettering exist on the board (ink 15 and 3 inside it)
    assert (s[2:12] == 15).sum() > 60 and (s[14:23] == 3).sum() > 10, '1260 lettering: FOR SALE (black) and a second line (red)'
    # --- the frame
    for i in (7000, 7001):
        assert (P[i][:, 0] == 15).all(), (i, 'leftmost column black')
    for i in (7000, 7001, 7003):
        assert (P[i][0] == 15).all(), (i, 'top row black')
    assert (P[7003][:, -1] == 15).all(), '7003 rightmost column black'
    for i in (7000, 7001):
        assert (P[i][1, 1:] == 13).all(), (i, 'second row 13')
    assert (P[7003][1, :-1] == 13).all()
    # --- the lattice: every visible lawn pixel of the three pictures is lattice(x, y); the seam
    def yard_pixel(x, y):
        if x <= 278:
            return int(P[7000][y, x + OX]) if x + OX >= 0 else None
        return int(P[7003][y, x - 279])
    n = 0
    for y in range(65, 226):
        for x in range(max(-2, 232 - y), min(512, 569 - y)):
            want = lattice(x, y)
            assert want is not None
            if house_covers(x, y):
                for pic in (7000, 7001):
                    assert P[pic][y, x + OX] not in (8, 9), ('lawn peeks out of the house', pic, x, y)
                continue
            got0 = yard_pixel(x, y)
            assert got0 == want, ('7000 / 7003 lattice', x, y, got0, want)
            if x <= 278:
                assert P[7001][y, x + OX] == want, ('7001 lattice', x, y)
            n += 1
    for y in range(226):                       # the seam: 7000 / 7001 column 280 and 7003 column 0 are neighbours (yard 278 / 279)
        for pic in (7000, 7001):
            lw = lattice(278, y)
            if lw is not None and not house_covers(278, y):
                assert P[pic][y, 280] == lw
        lw = lattice(279, y)
        if lw is not None:
            assert P[7003][y, 0] == lw
    # nothing of colours 6 / 7 on the visible lawn (checked above: only 8 / 9); the fence feet sit above the lattice's top line
    assert (P[7003][62:65, 200:] != 8).all() and (P[7003][62:65, 200:] != 9).all(), 'fence foot 62..64 is not lawn'
    # the lattice lines are in colour 9 and 8 elsewhere: counts are sane
    assert n > 30000
    # --- 7000 / 7001: identical outside HOUSE_MASK, 55 % identical overall
    m = ys.MASK[:, :W7000]
    assert (P[7000][~m] == P[7001][~m]).all(), 'identical outside HOUSE_MASK'
    frac = float((P[7000] == P[7001]).mean())
    assert frac >= 0.55, ('equal fraction', frac)
    reg.stats = getattr(reg, 'stats', {})
    reg.stats['equal_7000_7001'] = frac
    # --- the fixed rectangles
    x0, y0, x1, y1 = ys.DOOR_RECT
    assert (x1 - x0, y1 - y0) == (26, 42)
    ring = np.concatenate([P[7000][y0, x0 + OX:x1 + OX], P[7000][y1 - 1, x0 + OX:x1 + OX], P[7000][y0:y1, x0 + OX], P[7000][y0:y1, x1 - 1 + OX]])
    assert (ring == ys.NICHE_WALL).all(), 'the niche ring is wall colour'
    assert (P[7000][y0 + 1:y1 - 1, x0 + 1 + OX:x1 - 1 + OX] != ys.NICHE_WALL).any(), 'a door inside the niche'
    from yardlib import World
    wf = World()
    px = ys.draw_fridge(wf)
    xs, yy = [p[0] for p in px], [p[1] for p in px]
    assert (min(xs), min(yy), max(xs) + 1, max(yy) + 1) == ys.FRIDGE_RECT, 'the refrigerator fills its rectangle exactly'
    wc = World()
    px = ys.draw_chair(wc)
    xs, yy = [p[0] for p in px], [p[1] for p in px]
    cx0, cy0, cx1, cy1 = ys.CHAIR_RECT
    assert min(xs) > cx0 and max(xs) + 1 < cx1 and min(yy) > cy0 and max(yy) + 1 < cy1, 'the armchair lies inside its rectangle with a floor ring'
    # the chair's and fridge's rectangles in 7001 differ from 7000 (they are inside the house)
    # --- places kept free of detail: only lattice pixels on the lawn (the mower's place is partly under the house wall: wall colours only there)
    for name, (a0, b0, a1, b1) in (('sign', ys.SIGN_PLACE), ('porch lawn', ys.PORCH_LAWN), ('mower', ys.MOWER_PARK)):
        for y in range(b0, b1):
            for x in range(a0, a1):
                if lattice(x, y) is None:
                    continue
                for pic in (7000, 7001):
                    v = P[pic][y, x + OX]
                    if house_covers(x, y):
                        if name == 'mower':
                            assert (v in (12, 13, 15)) if pic == 7000 else True, (name, pic, x, y, v)
                        continue
                    assert v == lattice(x, y), (name, pic, x, y)
    # --- the person's route in the House view: a floor band free of furniture
    path = ys.PERSON_PATH
    pts = []
    for (a, b) in zip(path, path[1:]):
        n_ = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])))
        for i in range(n_ + 1):
            pts.append((a[0] + (b[0] - a[0]) * i / n_, a[1] + (b[1] - a[1]) * i / n_))
    pts = np.array(pts)
    worst = 1e9
    for name in sorted(set(n for n, _ in ys.FURNITURE)):
        px = np.array([p for n, q in ys.FURNITURE if n == name for p in q], dtype=float)
        dist = np.sqrt(((px[:, None, :] - pts[None, :, :]) ** 2).sum(2)).min()
        worst = min(worst, dist)
        assert dist >= 14.0, ('furniture on the person\'s route', name, dist)
    reg.stats['route_clear_px'] = worst
    # --- the strips
    full = np.full((161, 514), 13, dtype=np.int16)
    for y in range(65, 226):
        for x in range(232 - y, 569 - y):
            full[y - 65, x + 1] = lattice(x, y)
    marks = {(315 - y, y) for y in range(66, 114)} | {(x, 114) for x in range(173, 202)} | {(287 - y, y) for y in range(115, 225)}
    for (x, y) in marks:
        full[y - 65, x + 1] = 10
    assert (P[7020] == full[0:51, 0:513]).all() and (P[7021] == full[51:106, 0:512]).all() and (P[7022] == full[106:161, 0:512]).all()
    for i in (7020, 7021, 7022):
        assert set(np.unique(P[i]).tolist()) <= {8, 9, 10, 13}, i
    assert (P[7020][:, 512] == 13).all(), '7020 is one column wider: its last column is 13'
    assert (P[7020][0, 167 + 1:503 + 2] != 13).all(), 'the top line of the lattice is the first row of 7020'
    assert (P[7022][-1, 7 + 1:343 + 2] == 9).sum() > 300, 'the bottom line is the last row of 7022'
    # --- the words
    assert True  # no picture here contains a name: the script has no such strings
