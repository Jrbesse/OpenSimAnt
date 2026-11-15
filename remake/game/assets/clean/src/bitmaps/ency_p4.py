"""ency_p4.py - pass 4: other insects (300, 320, 330, 340) and ant species (610, 620, 630, 640)."""
import math

from ency_lib import Cv, grad, W_, K_, LT, MD, DK, T1, H1, H2, H1W, HX, DOT, catmull
import ency_ant as A
import ency_insects as I

WORKER = dict(leg=0.85, ant=0.85)


# ------------------------------------------------------------------------------------------------------ 300
def social300():
    cv = Cv(137, 165, '300')
    A.place(cv, WORKER, 55, 2, 135, 44)
    I.place_fn(cv, I.draw_termite, 1, 48, 75, 88)
    I.place_fn(cv, I.draw_bee, 52, 86, 135, 134)
    I.place_fn(cv, I.draw_wasp, 1, 128, 78, 164)
    cv.box('ants', (15, 17, 50, 28), 'Ants')
    cv.box('termites', (79, 56, 136, 67), 'Termites')
    cv.box('bees', (12, 96, 49, 107), 'Bees')
    cv.box('wasps', (82, 142, 126, 153), 'Wasps')
    return cv, 'four portraits (ant, termite, bee, wasp) with four boxed labels in a zig-zag'


def termite320():
    cv = Cv(69, 22, '320')
    I.place_fn(cv, I.draw_termite, 0, 0, 69, 22)
    return cv, 'a termite worker, side view facing left: pale, no waist, straight beaded antennae'


def bee330():
    cv = Cv(108, 70, '330')
    I.place_fn(cv, I.draw_bee, 0, 0, 108, 70)
    return cv, 'a honeybee in flight, side view facing left, with the pollen basket on the hind leg'


def wasp340():
    cv = Cv(94, 66, '340')
    # a few cells of paper comb in the lower left corner
    for (cx, cy) in ((7, 60), (19, 60), (31, 60), (13, 50), (25, 50)):
        I.hexcell(cv, cx, cy, 7, W_)
    I.place_fn(cv, I.draw_wasp, 24, 0, 94, 46)
    return cv, 'a social paper wasp, side view facing left, banded abdomen, with cells of paper comb'


# ------------------------------------------------------------------------------------------------------ 610
def weaver610():
    cv = Cv(141, 117, '610')
    cv.cut_cols = list(range(7))
    T = [(12, 22), (30, 10), (70, 7), (110, 9), (136, 18), (137, 28), (130, 33), (100, 42), (70, 48), (40, 50), (24, 55), (14, 53)]
    B = [(12, 84), (40, 80), (70, 82), (100, 88), (130, 93), (137, 100), (132, 110), (100, 115), (60, 116), (24, 114), (13, 108), (12, 96)]
    I.leaf_shape(cv, T, [(13, 36), (50, 29), (90, 24), (131, 22)], [])
    I.leaf_shape(cv, B, [(13, 100), (60, 102), (100, 106), (133, 104)], [])
    for x in range(26, 126, 14):
        yt = 36 - (x - 13) * 0.12
        cv.line((x, yt + 1), (x + 8, yt - 11), 1)
        cv.line((x, yt + 1), (x + 9, yt + 9), 1)
        yb = 100 + (x - 13) * 0.04
        cv.line((x, yb + 1), (x + 8, yb - 12), 1)
        cv.line((x, yb + 1), (x + 9, yb + 11), 1)
    # the chain of workers, each holding the waist of the one in front (heads to the left)
    sp = dict(leg=0.85, ant=0.9, pose='stand')
    for cx in (85, 68, 51, 34):
        A.draw_ant(cv, sp, 34, cx, 66)
    # one worker holding a larva in its mandibles against the leaf edge, spinning silk
    L2 = 26
    wx, wy = 126, 80
    A.draw_ant(cv, dict(leg=0.8, ant=0.9, pose='stand', mand='open'), L2, wx, wy)
    mx, my = A.mouth(L2, wx, wy)
    I.larva(cv, mx - 6, my + 1, 1.8, False, 0.8)
    for k in range(0, 13):                  # silk: a line of dots up to the upper leaf's edge
        t = k / 12
        cv.put(mx - 7 + 11 * t, my - 4 - 33 * t, 1)
    cv.box('larvae', (89, 5, 124, 17), 'Larvae')
    cv.leader('larvae', (104, 17), [(104, 70)], (int(mx - 11), int(my - 2)), (int(mx - 20), int(my - 8), int(mx + 4), int(my + 8)))
    return cv, 'weaver ants: a chain of workers pulling two leaves together, one holding a larva that spins silk (1 label)'


# ------------------------------------------------------------------------------------------------------ 620
def harvest620():
    cv = Cv(139, 64, '620')
    g = 52
    # grass stems with seed heads at the back
    for (x, top) in ((9, 8), (47, 14), (100, 10), (131, 16)):
        cv.pline(catmull([(x, g), (x + 2, (g + top) / 2), (x - 1, top + 6)], False, 4), 1)
        for k in range(5):
            y = top + k * 3
            cv.line((x - 1, y + 5), (x - 4, y + 1), 1)
            cv.line((x - 1, y + 5), (x + 2, y + 1), 1)
        cv.line((x - 1, top + 5), (x - 1, top - 3), 1)
    # ground
    cv.rect(0, g + 1, 139, g + 3, K_, None)
    for x in range(3, 139, 11):
        cv.put(x, g + 6 + (x % 3), 1)
    cv.put(7, g + 5, 1)
    # loose seeds
    for (x, y, rx, ry, rot) in ((9, g - 2, 4, 2.4, 0.1), (48, g - 2, 3.5, 2.2, -0.2), (85, g - 2, 4, 2.4, 0.2), (130, g - 3, 3.5, 2.4, 0.5),
                                (60, g - 1, 2.8, 1.9, 0.0), (108, g - 1, 3, 2, 0.1)):
        I.seed(cv, x, y, rx, ry, rot)
    # three workers, each with a large seed in the mandibles
    for cx, sp, L in ((24, dict(hs=1.05, leg=0.9, ant=0.8), 34), (70, dict(hs=1.05, leg=0.9, ant=0.8, pose='stand'), 34), (115, dict(hs=1.05, leg=0.9, ant=0.8), 34)):
        A.on_ground(cv, sp, L, cx, g)
        ox, oy = cx, g - A.feet_y(sp, L)
        mx, my = A.mouth(L, ox, oy)
        I.seed(cv, mx - 3, my + 3.5, 7, 4.4, 0.5)
    return cv, 'harvester ants: three workers on the ground each carrying a seed, loose seeds, grass stems'


# ------------------------------------------------------------------------------------------------------ 630
def _army_ant(cv, ox, oy, s, pose, load):
    """one army-ant worker marching left, drawn straight in picture pixels (the shared ant model is too thin at this size):
    (ox, oy) = the body centre at the ground row, s = scale (1.0 = 50 px from the jaw tips to the gaster tip).  No eye; the head is
    the biggest part (a little wider than tall, white) with two long hooked black mandibles reaching well past it, a narrower and
    longer white thorax, a small black waist node, a black gaster with one white glint, five long walking legs (the far ones
    dashed); load = None / 'larva' / 'prey' held in the jaws, in front of the head."""
    def P(p, y=None):
        x, y = p if y is None else (p, y)
        return (ox + x * s, oy + y * s)

    def pl(pts, v=1, dash=None):
        cv.pline([P(p) for p in pts], v, dash)
    by = -19.0                                  # the body axis, above the ground row
    hip = by + 3.0
    if pose == 'a':
        near = [[(-5, hip), (-10, -9), (-13, 0)], [(-1, hip), (2, -9), (-1, 0)], [(3, hip), (9, -9), (12, 0)]]
        far = [[(-4, hip), (-7, -8), (-6, 0)], [(4, hip), (6, -8), (15, 0)]]
    else:
        near = [[(-5, hip), (-8, -9), (-8, 0)], [(-1, hip), (0, -9), (-5, 0)], [(3, hip), (7, -9), (14, 0)]]
        far = [[(-4, hip), (-11, -9), (-15, 0)], [(4, hip), (9, -9), (8, 0)]]
    for leg in far:                                 # far legs: dashed
        pl(leg + [(leg[-1][0] - 2, leg[-1][1])], 1, (2, 2))
    for leg in near:
        pl(leg + [(leg[-1][0] - 2, leg[-1][1])], 1)
    # back to front: gaster (black), waist and node, thorax, head, mandibles
    cv.ell(*P((13.5, by + 0.5)), 5.9 * s, 4.6 * s, K_, 1, n=20)
    cv.put(*P((11.5, by - 2)), 0)
    cv.put(*P((12.5, by - 2.5)), 0)
    pl([(4.5, by + 0.5), (8, by + 0.5)], 1)
    cv.ell(*P((6.2, by - 1.4)), 1.2 * s, 1.5 * s, K_, 1, n=8)           # the waist node
    cv.poly([P(p) for p in ((-6.5, by - 1.5), (-4.5, by - 3), (0, by - 3.2), (3, by - 2), (4.5, by + 0.3), (3, by + 2.5), (-3, by + 3), (-6, by + 2.2))],
            W_, 1, smooth=4)
    cv.ell(*P((-12.5, by + 0.3)), 6.6 * s, 5.4 * s, W_, 1, n=22)       # the head: biggest part, no eye
    # two long hooked black mandibles (sickles that cross at the tips: the upper hooks down, the lower hooks up)
    cv.poly([P(p) for p in ((-18, by - 1.2), (-23, by - 3.2), (-28, by - 1.2), (-30.5, by + 3.2), (-27.5, by + 1.6), (-23, by - 0.2), (-18, by + 1.5))], K_, 1)
    cv.poly([P(p) for p in ((-18, by + 3.4), (-23, by + 5.8), (-28, by + 4.4), (-30.5, by + 0.6), (-27.5, by + 2.6), (-23, by + 3.2), (-18, by + 1.8))], K_, 1)
    # short elbowed antennae
    pl([(-15, by - 5), (-18, by - 8.5), (-22, by - 8.5)])
    pl([(-12, by - 5.3), (-13.5, by - 9.5), (-17.5, by - 11.5)], 1, (2, 1))
    mx, my = P((-30, by + 3.2))
    if load == 'larva':                       # a pale grub: a white curved oval with its segment lines and a head dot
        lx, ly = mx - 3.2, my + 1.5
        cv.ell(lx, ly, 4.0, 2.5, W_, 1, rot=0.3, n=16)
        for k in (-1, 1):
            cv.line((lx + k * 1.3 - 0.4, ly - 1.8 + 0.3 * k), (lx + k * 1.3 + 0.2, ly + 1.8 + 0.3 * k), 1)
        cv.put(lx - 2.6, ly - 0.2, 1)
    elif load == 'prey':                      # a piece of prey: a mid-tone oval with a groove and dangling legs
        lx, ly = mx - 3.6, my + 1.2
        cv.ell(lx, ly, 4.2, 2.8, MD, 1, n=14)
        cv.line((lx - 3.6, ly), (lx + 3.6, ly), 0)
        for k in (-2, 0, 2):
            cv.line((lx + k, ly + 2.8), (lx + k - 1, ly + 5.5), 1)


def army630():
    """a double file of five army ants marching left: a back rank of two smaller ants above a dotted ground line, a front rank of
    three on a solid 2 px ground line; every ant is a separate silhouette (3 px gaps); one ant carries prey, two carry a larva"""
    cv = Cv(112, 65, '630')
    gb, gf = 33, 60
    for x in range(1, 112, 4):
        cv.put(x, gb + 1, 1)
    _army_ant(cv, 44, gb, 0.6, 'b', 'larva')
    _army_ant(cv, 92, gb, 0.6, 'a', None)
    cv.rect(0, gf + 1, 112, gf + 3, K_, None)
    for x in (10, 33, 62, 85, 104):
        cv.put(x, gf + 4, 1)
    for cx, pose, load in ((20, 'a', None), (58, 'b', 'larva'), (99, 'a', 'prey')):
        _army_ant(cv, cx, gf, 0.62, pose, load)
    return cv, 'army ants on the march: a double file of five big-headed, long-legged workers, two carrying larvae, one carrying prey'


# ------------------------------------------------------------------------------------------------------ 640
def leafcutter640():
    cv = Cv(122, 110, '640')
    g = 61
    # the plant's leaf at the left, its right edge scalloped where it is being cut
    leaf = [(3, 6), (22, 2), (36, 12), (31, 20), (37, 28), (31, 36), (36, 44), (30, 52), (20, 60), (8, 56), (3, 40)]
    I.leaf_shape(cv, leaf, [(5, 54), (10, 34), (18, 16), (24, 6)], [], LT, 3)
    for (a, b) in (((9, 40), (3, 42)), ((12, 30), (4, 28)), ((15, 20), (5, 15)), ((9, 40), (20, 44)), ((12, 30), (26, 33)), ((15, 20), (28, 24))):
        cv.line(a, b, 1)
    # the cutter, running up the leaf edge, jaws at the cut
    A.draw_ant(cv, dict(leg=0.8, ant=0.8, mand='open'), 24, 44, 34, False, math.pi / 2)
    # ground
    cv.rect(38, g + 1, 122, g + 3, K_, None)
    for x in range(40, 122, 9):
        cv.put(x, g + 6 + (x % 3), 1)
    # carriers walking away to the right, each with a cut piece of leaf held upright over the back
    sp = dict(leg=0.85, ant=0.8)
    for cx in (54, 78, 102):
        L = 24
        A.on_ground(cv, sp, L, cx, g, flip=True)
        oy = g - A.feet_y(sp, L)
        mx, my = A.mouth(L, cx, oy, True)
        lx, ly = cx + 2, oy - 0.30 * L - 3
        cv.ell(lx, ly, 6, 9.5, MD, 1, rot=0.35, n=20)
        cv.line((lx - 3, ly + 8), (lx + 3, ly - 8), 1)
        for k in (-4, 0, 4):
            cv.line((lx + k * 0.3, ly - k), (lx + k * 0.3 + 3, ly - k - 1), 1)
        cv.line((mx - 1, my), (lx + 1, ly + 8), 1)
    # underground: the fungus garden in a rounded chamber, a tiny worker on it
    cv.pline(catmull([(6, 74), (14, 66), (30, 66), (61, 66), (92, 66), (108, 66), (116, 74), (118, 90), (110, 106), (61, 109), (12, 106), (4, 92)], True, 5), 1, None, 1, True) if False else None
    cv.ell(61, 90, 57, 19, None, 1)
    pts = []
    for k in range(48):
        a = 2 * math.pi * k / 48
        r = 1 + 0.10 * math.sin(7 * a) + 0.06 * math.sin(13 * a + 1)
        pts.append((61 + 46 * r * math.cos(a), 94 + 11 * r * math.sin(a) * 1.0))
    cv.poly(pts, LT, 1)
    for (x, y) in ((30, 93), (42, 100), (55, 96), (68, 101), (80, 95), (93, 99), (47, 90), (74, 91), (62, 86), (36, 98), (98, 93), (84, 102)):
        cv.ell(x, y, 2.2, 1.8, W_, 1, n=8)
    A.on_ground(cv, dict(leg=0.8, ant=0.8), 13, 62, 84)
    return cv, 'leafcutter ants: a cutter at a leaf edge, three carriers with leaf pieces, the fungus garden below'


def build():
    return {300: social300(), 320: termite320(), 330: bee330(), 340: wasp340(), 610: weaver610(), 620: harvest620(),
            630: army630(), 640: leafcutter640()}
