"""ency_p4.py - pass 4: other insects (300, 320, 330, 340) and ant species (610, 620, 630, 640)."""
import math

from ency_lib import Cv, grad, W_, K_, LT, MD, DK, T1, H1, H2, H1W, HX, DOT, catmull
import ency_ant as A
import ency_insects as I

WORKER = dict(leg=0.85, ant=0.85)


# ------------------------------------------------------------------------------------------------------ 300
def social300():
    cv = Cv(137, 165, 'SHARED_300')
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
    cv = Cv(69, 22, 'SHARED_320')
    I.place_fn(cv, I.draw_termite, 0, 0, 69, 22)
    return cv, 'a termite worker, side view facing left: pale, no waist, straight beaded antennae'


def bee330():
    cv = Cv(108, 70, 'SHARED_330')
    I.place_fn(cv, I.draw_bee, 0, 0, 108, 70)
    return cv, 'a honeybee in flight, side view facing left, with the pollen basket on the hind leg'


def wasp340():
    cv = Cv(94, 66, 'SHARED_340')
    # a few cells of paper comb in the lower left corner
    for (cx, cy) in ((7, 60), (19, 60), (31, 60), (13, 50), (25, 50)):
        I.hexcell(cv, cx, cy, 7, W_)
    I.place_fn(cv, I.draw_wasp, 24, 0, 94, 46)
    return cv, 'a social paper wasp, side view facing left, banded abdomen, with cells of paper comb'


# ------------------------------------------------------------------------------------------------------ 610
def weaver610():
    cv = Cv(141, 117, 'SHARED_610')
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
    cv = Cv(139, 64, 'SHARED_620')
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
def army630():
    cv = Cv(112, 65, 'SHARED_630')
    sp_n = dict(hs=1.25, leg=1.25, eye=False, mand='open', ant=0.6, gh=0.9, gl=0.9)
    gf, gn = 31, 60
    for x in range(0, 112, 6):
        cv.put(x, gf + 1, 1)
    for i in range(3):
        cx = 22 + i * 36
        A.on_ground(cv, sp_n, 20, cx, gf)
        if i == 1:
            ox, oy = cx, gf - A.feet_y(sp_n, 20)
            mx, my = A.mouth(20, ox, oy)
            I.larva(cv, mx - 3, my + 1, 1.2, False, 0.8)
    cv.rect(0, gn + 1, 112, gn + 3, K_, None)
    for i in range(4):
        cx = 20 + i * 25
        sp = dict(sp_n, pose='stand') if i % 2 else sp_n
        A.on_ground(cv, sp, 28, cx, gn)
        ox, oy = cx, gn - A.feet_y(sp, 28)
        mx, my = A.mouth(28, ox, oy)
        if i == 1:
            I.larva(cv, mx - 5, my + 1, 1.8, False, 0.8)
        if i == 3:
            cv.ell(mx - 5, my + 2, 5, 3.2, MD, 1, n=12)
            for k in (-3, 0, 3):
                cv.line((mx - 5 + k, my + 5), (mx - 5 + k - 1, my + 7), 1)
    return cv, 'army ants on the march: two files of big-headed, long-legged workers, some carrying larvae or prey'


# ------------------------------------------------------------------------------------------------------ 640
def leafcutter640():
    cv = Cv(122, 110, 'SHARED_640')
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
