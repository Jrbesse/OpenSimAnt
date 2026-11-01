"""ency_p5.py - pass 5: behaviour and the nest (510..560), the life cycles (710, 720) and the colony flowchart (880)."""
import math

from ency_lib import Cv, grad, W_, K_, LT, MD, DK, T1, H1, H2, H1W, HX, DOT, catmull
import ency_ant as A
import ency_insects as I
import ency_p2 as P2


# ------------------------------------------------------------------------------------------------- helpers
def bres(p0, p1):
    x0, y0 = int(round(p0[0])), int(round(p0[1]))
    x1, y1 = int(round(p1[0])), int(round(p1[1]))
    out = []
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return out


def head_pts(tip, frm):
    """the 3-px arrowhead (a small filled triangle) at `tip` for a line coming from `frm`"""
    dx, dy = tip[0] - frm[0], tip[1] - frm[1]
    n = math.hypot(dx, dy) or 1
    dx, dy = dx / n, dy / n
    nx, ny = -dy, dx
    return [(tip[0], tip[1]), (tip[0] - 3 * dx + 2 * nx, tip[1] - 3 * dy + 2 * ny), (tip[0] - 3 * dx - 2 * nx, tip[1] - 3 * dy - 2 * ny)]


def arrow(cv, pts, dash=None, head_end=True, head_start=False, w=1):
    """a raw polyline with an arrowhead at one or both ends; returns the set of pixels used"""
    pix = set()
    with cv.raw():
        for i in range(len(pts) - 1):
            for (x, y) in bres(pts[i], pts[i + 1]):
                pix.add((x, y))
            cv.line(pts[i], pts[i + 1], 1, dash, w)
        for flag, tip, frm in ((head_end, pts[-1], pts[-2]), (head_start, pts[0], pts[1])):
            if flag:
                hp = head_pts(tip, frm)
                cv.poly(hp, K_, 1)
                for p in hp:
                    pix.add((int(round(p[0])), int(round(p[1]))))
    return pix


def tube(cv, jobs):
    """soil tunnels and chambers: first every black outline, then every white inside, so the joins merge.
    jobs: ('seg', p0, p1, w) or ('ell', cx, cy, rx, ry)"""
    for job in jobs:
        if job[0] == 'seg':
            _, p0, p1, w = job
            poly = seg_poly(p0, p1, w / 2 + 1)
            cv.poly(poly, K_, None)
        else:
            _, cx, cy, rx, ry = job
            cv.ell(cx, cy, rx + 1, ry + 1, K_, None, n=40)
    for job in jobs:
        if job[0] == 'seg':
            _, p0, p1, w = job
            cv.poly(seg_poly(p0, p1, w / 2), W_, None)
        else:
            _, cx, cy, rx, ry = job
            cv.ell(cx, cy, rx, ry, W_, None, n=40)


def seg_poly(p0, p1, h):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy) or 1
    nx, ny = -dy / n * h, dx / n * h
    ex, ey = dx / n * h, dy / n * h
    return [(p0[0] - ex + nx, p0[1] - ey + ny), (p1[0] + ex + nx, p1[1] + ey + ny), (p1[0] + ex - nx, p1[1] + ey - ny),
            (p0[0] - ex - nx, p0[1] - ey - ny)]


def wave(cv, x0, y0, x1, amp, periods, v=1):
    n = int((x1 - x0) * 2)
    pts = [(x0 + (x1 - x0) * k / n, y0 + amp * math.sin(2 * math.pi * periods * k / n)) for k in range(n + 1)]
    cv.pline(pts, v)


def grass(cv, x, y, h=6):
    cv.line((x, y), (x - 2, y - h), 1)
    cv.line((x + 1, y), (x + 1, y - h - 2), 1)
    cv.line((x + 2, y), (x + 4, y - h + 1), 1)


WORKER = dict(leg=0.85, ant=0.85)


# ------------------------------------------------------------------------------------------------------ 510
def nest510():
    cv = Cv(222, 101, 'SHARED_510')
    cv.rect(0, 16, 222, 101, H1W, None)
    cv.rect(0, 14, 222, 16, K_, None)
    for x in (6, 22, 40, 60, 80, 140, 160, 182, 204):
        grass(cv, x, 13, 5 + (x % 3))
    cv.poly([(94, 14), (100, 9), (111, 6), (122, 9), (128, 14)], H1, 1, smooth=3)
    jobs = [('seg', (111, 14), (111, 90), 5), ('seg', (111, 30), (136, 30), 4), ('seg', (111, 30), (98, 30), 4),
            ('seg', (164, 30), (178, 30), 4), ('seg', (111, 90), (96, 90), 4), ('seg', (111, 90), (121, 90), 4),
            ('seg', (153, 90), (160, 90), 4), ('seg', (160, 90), (160, 85), 4), ('seg', (160, 85), (171, 85), 4),
            ('ell', 66, 90, 30, 9), ('ell', 150, 30, 14, 8), ('ell', 88, 30, 10, 6), ('ell', 190, 30, 12, 7),
            ('ell', 137, 90, 16, 9), ('ell', 195, 85, 24, 11)]
    tube(cv, jobs)
    cv.ell(111, 10, 4, 2, K_, 1)                       # the entrance hole
    # the queen and her eggs
    q = A.on_ground(cv, P2.QUEEN, 26, 58, 97)
    for (x, y) in ((86, 96), (91, 95), (88, 92)):
        I.egg(cv, x, y, 2.4)
    # brood: eggs, larvae, pupae
    for (x, y) in ((143, 33), (148, 34), (153, 33), (158, 33), (146, 29), (152, 29), (157, 29)):
        I.egg(cv, x, y, 2.3)
    I.larva(cv, 131, 92, 1.5, False, 0.8)
    I.larva(cv, 141, 95, 1.4, True, 0.8)
    I.pupa(cv, 145, 88, 4.0, 0.0, True)
    for (x, y) in ((178, 92), (182, 94), (186, 92), (181, 89), (185, 89)):
        I.egg(cv, x, y, 2.3)
    I.larva(cv, 196, 91, 1.7, False, 0.8)
    I.larva(cv, 205, 94, 1.6, True, 0.8)
    I.pupa(cv, 211, 86, 4.0, 0.2, True)
    A.on_ground(cv, WORKER, 14, 198, 83)
    # stores: grains and crumbs
    for (x, y, rx, ry, r) in ((84, 33, 2.4, 1.6, 0.1), (89, 32, 2.4, 1.6, -0.3), (93, 33, 2.2, 1.5, 0.2), (86, 29, 2.2, 1.5, 0.0), (91, 28, 2.2, 1.5, 0.3)):
        I.seed(cv, x, y, rx, ry, r)
    for (x, y) in ((184, 33), (189, 34), (194, 33), (187, 29), (192, 29), (197, 31)):
        cv.ell(x, y, 2, 1.5, W_, 1, n=8)
    # boxes on the soil
    cv.box('qch', (1, 55, 42, 83), ["Queen's", 'chamber'])
    cv.box('queen', (56, 60, 84, 77), 'Queen')
    cv.box('brood1', (136, 40, 165, 55), 'Brood')
    cv.box('brood2', (122, 62, 152, 79), 'Brood')
    cv.box('nurseries', (173, 52, 222, 67), 'Nurseries')
    cv.leader('qch', (30, 83), [(30, 91)], (40, 91), (36, 81, 96, 100))
    tc = q['thorax_c']
    cv.leader('queen', (70, 77), [(70, tc[1] - 7)], (tc[0] - 1, tc[1] - 1), q['thorax'])
    cv.leader('brood1', (150, 39), [], (150, 31), (136, 22, 164, 38))
    cv.leader('brood2', (137, 79), [], (137, 90), (121, 81, 153, 99))
    cv.leader('nurseries', (197, 67), [], (197, 80), (171, 74, 219, 96))
    return cv, "a nest cut open: surface, shaft, tunnels, the queen's chamber, nurseries and stores (5 labels)"


# ------------------------------------------------------------------------------------------------------ 520
def talk520():
    cv = Cv(167, 149, 'SHARED_520')
    cv.cut_cols = list(range(34))
    g = 128
    cv.rect(36, g, 167, g + 2, K_, None)
    sp = dict(leg=0.85, ant=1.35, pose='stand')
    L = 56
    left = A.draw_ant(cv, sp, L, 66, 100, True, -0.22)
    right = A.draw_ant(cv, sp, L, 136, 100, False, 0.22)
    # chemical signals: short wavy lines and dots between and above the heads
    for (x0, y0, x1, amp) in ((90, 62, 116, 2.0), (86, 71, 118, 2.4), (90, 80, 116, 2.0)):
        wave(cv, x0, y0, x1, amp, 2.5)
    for (x, y) in ((100, 52), (108, 48), (94, 46), (116, 54), (86, 55), (120, 62), (82, 66), (104, 40)):
        cv.put(x, y, 1)
        cv.put(x + 1, y, 1)
    # a short trail of dots leading away
    for k in range(14):
        x = 88 + k * 5.5
        y = 140 + 2.5 * math.sin(k * 0.7)
        cv.put(x, y, 1)
        cv.put(x + 1, y, 1)
    cv.box('antennae', (107, 0, 156, 21), 'Antennae')
    tx, ty = right['ant_tip']
    tx, ty = tx - 1, ty - 1
    sx = min(max(tx, 112), 150)
    via = [(sx, max(ty - 14, 24))] if sx != tx else []
    cv.leader('antennae', (sx, 21), via, (tx, ty), (tx - 4, ty - 4, tx + 6, ty + 6))
    return cv, 'two workers meeting head to head touching antennae, chemical signals, a dotted trail (1 label)'


# ------------------------------------------------------------------------------------------------------ 530
def trail530():
    cv = Cv(218, 69, 'SHARED_530')
    g = 60
    cv.rect(0, g + 1, 218, g + 3, K_, None)
    for x in range(4, 218, 10):
        cv.put(x, g + 6 + (x % 4), 1)
    # nest entrance: a mound with a hole
    cv.poly([(2, g), (8, g - 7), (18, g - 11), (28, g - 7), (34, g)], H1, 1, smooth=3)
    cv.ell(18, g - 4, 5, 3, K_, 1)
    # the food: a crumb
    cv.ell(208, g - 4, 8, 4.5, MD, 1)
    cv.ell(204, g - 6, 2.5, 1.5, W_, None)
    # the dotted trail, from the lead ant's gaster tip back toward the food
    for x in range(78, 200, 4):
        cv.put(x, g + 1, 0)
        cv.put(x, g - 1, 1)
        cv.put(x + 1, g - 1, 1)
    # the lead ant: head up, gaster tip pressed on the ground
    sp = dict(leg=0.85, ant=0.85, pose='stand')
    lead = A.draw_ant(cv, sp, 38, 58, g - 9, False, 0.42)
    # followers, in file along the trail
    for cx in (104, 140, 176):
        A.on_ground(cv, WORKER, 34, cx, g - 1)
    cv.box('pher', (16, 2, 71, 25), 'Pheromone', face='b8')
    cv.leader('pher', (71, 13), [(96, 13)], (96, g - 1), (76, g - 4, 200, g + 2))
    return cv, 'a scent trail: the lead ant lays a dotted line from the food toward the nest, a file of ants follows (1 label)'


# ------------------------------------------------------------------------------------------------------ 540
def fight540():
    cv = Cv(111, 105, 'SHARED_540')
    g = 95
    cv.extra['ground540'] = g + 1
    cv.rect(0, g + 1, 111, g + 3, K_, None)
    for x in range(3, 111, 8):
        cv.put(x, g + 6 + (x % 3), 1)
    spA = dict(leg=0.85, ant=0.85, mand='open', hs=1.15)
    spB = dict(leg=0.85, ant=0.85, hs=1.15)
    L = 38
    rb = A.draw_ant(cv, spB, L, 68, g - 22, False, 0.28)                # B, facing left, rearing a little
    ra = A.draw_ant(cv, spA, L, 36, g - 22, True, -0.28)                # A, facing right, jaws on B's front leg
    mx, my = ra['mouth']
    hx, hy = rb['hip0']
    cv.pline([(hx, hy), ((hx + mx) / 2 - 1, hy + 4), (mx + 2, my + 1)], 1, None, 2)       # the gripped leg
    # the third ant rears up and sprays
    A.draw_ant(cv, dict(leg=0.8, ant=0.8, hs=1.1, pose='stand'), 30, 98, 66, False, -0.75)
    for (x, y) in ((106, 50), (101, 44), (96, 40), (90, 38), (104, 42), (98, 36), (93, 33), (87, 41), (108, 43), (100, 52)):
        cv.put(x, y, 1)
    cv.line((90, 46), (82, 48), 1, (2, 2))
    cv.line((84, 40), (76, 41), 1, (2, 2))
    # motion lines
    for (x0, y0, x1) in ((19, 70, 28), (21, 75, 30), (19, 80, 27), (85, 62, 93)):
        cv.line((x0, y0), (x1, y0), 1)
    return cv, 'a fight: one ant gripping the other\'s leg, a third rearing up to spray'


# ------------------------------------------------------------------------------------------------------ 550
def aphids550():
    cv = Cv(194, 103, 'SHARED_550')
    g = 80
    # a branch across the lower half with bark lines, a shoot rising on the right
    cv.poly([(0, g), (194, g), (194, g + 8), (0, g + 8)], LT, 1)
    for x in range(4, 194, 9):
        cv.line((x, g + 2), (x + 3, g + 6), 1)
    cv.poly([(166, g), (168, 46), (172, 40), (176, 46), (176, g)], LT, 1)
    cv.line((170, 78), (171, 48), 1, (2, 2))
    I.leaf_shape(cv, [(172, 40), (182, 32), (192, 36), (186, 44)], [(173, 40), (190, 36)], [])
    # the aphids: a cluster round the shoot and on the branch
    for (x, y, f) in ((157, 74, False), (181, 74, True), (158, 62, False), (182, 62, True), (159, 51, False), (183, 51, True),
                      (150, 75, False), (191, 76, True)):
        I.aphid(cv, x, y, 5, f)
    # the milked aphid with its honeydew drop
    I.aphid(cv, 90, 73, 6.5, False)
    cv.ell(101, 77, 2.6, 3.4, W_, 1, n=12)
    cv.put(100, 76, 1)
    # the ant stroking it with its antennae
    spa = dict(leg=0.85, ant=1.1, pose='stand')
    A.on_ground(cv, spa, 48, 46, g, True)
    # the ant drinking the drop
    A.on_ground(cv, dict(leg=0.85, ant=0.9, pose='stand', mand='open'), 40, 123, g)
    cv.box('honey', (91, 4, 143, 16), 'Honeydew')
    cv.box('aphids', (161, 16, 190, 30), 'Aphid')
    cv.leader('honey', (93, 16), [(93, 62)], (100, 73), (94, 70, 106, 82))
    cv.leader('aphids', (175, 30), [], (174, 52), (150, 46, 194, 84))
    return cv, 'ants tending aphids: stroking one, a honeydew drop drunk by a second ant, a cluster of aphids (2 labels)'


# ------------------------------------------------------------------------------------------------------ 560
def brood560():
    cv = Cv(135, 87, 'SHARED_560')
    cv.rect(0, 0, 135, 87, H1W, None)
    cv.ell(67, 46, 62, 33, W_, 1, n=60)
    fl = 70
    # eggs on the left
    k = 0
    for row, (n, y) in enumerate(((6, fl - 3), (5, fl - 9), (4, fl - 15), (2, fl - 21))):
        for i in range(n):
            I.egg(cv, 14 + 4 * row + i * 5.2, y, 2.6, 0.3 * (i % 2))
    # larvae and a pupa on the right
    I.larva(cv, 111, fl - 4, 2.4, False, 0.8)
    I.larva(cv, 121, fl - 2, 2.0, True, 0.8)
    I.pupa(cv, 116, fl - 21, 7, 0.0, True)
    # nurse one carries an egg toward the pile, nurse two licks a larva
    sp = dict(leg=0.85, ant=0.9, pose='stand')
    n1 = A.on_ground(cv, dict(sp, mand='open'), 36, 54, fl)
    mx, my = A.mouth(36, 54, fl - A.feet_y(sp, 36))
    I.egg(cv, mx - 3, my + 2, 3.4, 0.5)
    A.on_ground(cv, sp, 36, 86, fl, True)
    return cv, 'brood care in a nursery chamber: eggs, larvae, a pupa, one nurse carrying an egg, one licking a larva'


# ------------------------------------------------------------------------------------------------------ 710
def cycle710():
    cv = Cv(299, 68, 'SHARED_710')
    # stages
    I.egg(cv, 20, 31, 8)
    I.egg(cv, 10, 38, 5.5, 0.4)
    I.egg(cv, 28, 39, 5.5, -0.3)
    I.larva(cv, 96, 32, 4.6, False, 1.0)
    # the larva spinning its cocoon: a dashed oval being laid round it, thread dots
    I.larva(cv, 148, 37, 4.0, False, 1.0)
    cv.ell(146, 37, 22, 12, None, 1, dash=(3, 2))
    # the pupa inside its cocoon
    I.pupa(cv, 212, 36, 15, 0.0, True)
    # the adult emerging
    cv.ell(284, 38, 15, 9, T1, 1, rot=0.2)
    A.draw_ant(cv, dict(leg=0.8, ant=1.0, pose='stand'), 30, 270, 32)
    # arrows between the stages
    for (x0, x1, y) in ((38, 62, 31), (114, 124, 33), (176, 184, 36), (240, 252, 36)):
        arrow(cv, [(x0, y), (x1, y)])
    cv.box('egg', (7, 2, 30, 14), 'Egg')
    cv.box('larva', (80, 2, 115, 13), 'Larva')
    cv.box('pupa', (198, 1, 228, 14), 'Pupa')
    cv.box('spin', (124, 54, 159, 67), 'Spin')
    cv.box('hatch', (267, 51, 298, 66), 'Hatch')
    cv.leader('egg', (18, 14), [], (18, 21), (10, 18, 30, 36))
    cv.leader('larva', (96, 13), [], (96, 25), (80, 20, 112, 44))
    cv.leader('pupa', (212, 14), [], (212, 24), (192, 20, 234, 52))
    cv.leader('spin', (140, 53), [], (140, 46), (124, 24, 168, 50))
    cv.leader('hatch', (282, 50), [], (282, 46), (268, 24, 298, 50))
    return cv, "the ant's life cycle as a strip: egg, larva, spinning, pupa, emerging adult (5 labels)"


# ------------------------------------------------------------------------------------------------------ 720
def cycle720():
    cv = Cv(302, 53, 'SHARED_720')
    g = 16
    for x0, x1 in ((0, 100), (102, 201), (203, 302)):
        cv.rect(x0, g + 1, x1, 44, H1W, None)
        cv.rect(x0, g - 1, x1, g + 1, K_, None)
    cv.line((101, 0), (101, 44), 1)
    cv.line((202, 0), (202, 44), 1)
    # (1) founding: a lone queen in a tiny sealed chamber, a few eggs and the first larvae
    tube(cv, [('ell', 50, 31, 16, 7), ('seg', (50, 17), (50, 26), 3)])
    A.on_ground(cv, P2.QUEEN, 11, 42, 36)
    for (x, y) in ((55, 35), (58, 34), (56, 31)):
        I.egg(cv, x, y, 1.6)
    I.larva(cv, 61, 33, 1.0, False, 0.8)
    for x in (12, 30, 78, 90):
        grass(cv, x, g - 2, 4)
    cv.put(50, g - 1, 1)
    # (2) growth: more tunnels and chambers, many workers, food carried in
    tube(cv, [('seg', (150, 17), (150, 40), 4), ('seg', (150, 26), (122, 26), 3), ('seg', (122, 26), (122, 34), 3), ('seg', (150, 32), (180, 32), 3),
              ('seg', (180, 32), (180, 38), 3), ('seg', (150, 40), (132, 40), 3), ('ell', 122, 36, 10, 5), ('ell', 180, 39, 11, 4), ('ell', 130, 41, 9, 3),
              ('ell', 150, 42, 12, 2)])
    for (cx, gy) in ((122, 38), (178, 41), (130, 42)):
        A.on_ground(cv, WORKER, 8, cx, gy)
    A.on_ground(cv, WORKER, 8, 150, 36)
    A.on_ground(cv, WORKER, 8, 150 + 8, 31)
    A.on_ground(cv, dict(leg=0.8, ant=0.8), 11, 190, g - 1, True)
    I.seed(cv, 186, g - 8, 2.5, 1.6, 0.4)
    A.on_ground(cv, dict(leg=0.8, ant=0.8), 11, 124, g - 1)
    for x in (110, 135, 168):
        grass(cv, x, g - 2, 4)
    # (3) reproduction: winged males and new queens fly up from the entrance
    tube(cv, [('seg', (252, 17), (252, 38), 4), ('seg', (252, 28), (228, 28), 3), ('seg', (252, 34), (278, 34), 3), ('ell', 224, 31, 9, 5),
              ('ell', 282, 37, 9, 4), ('ell', 252, 40, 10, 2)])
    for (cx, cy) in ((236, 8), (262, 5), (284, 9), (248, 12)):
        A.draw_ant(cv, dict(P2.ALATE, leg=0.5, ant=0.8), 15, cx, cy, cx > 255)
    for (x, y) in ((222, 6), (214, 12), (294, 4)):
        grass(cv, x, g - 2, 4) if y > 10 else None
    # captions under the panels
    for cx, word in ((50, 'founding'), (151, 'growth'), (252, 'spreading')):
        from ency_lib import text_w
        cv.caption(cx - text_w(word, 'r6') // 2, 46, word)
    return cv, "the colony's three stages in three panels: founding, growth, reproduction; captions founding, growth, spreading"


# ------------------------------------------------------------------------------------------------------ 880
FLOW = [
    ('F1', (4, 3, 74, 14), 'Foraging ants'), ('F2', (106, 3, 176, 14), 'Food collected'), ('F3', (79, 29, 142, 40), 'Food stored'),
    ('F4', (156, 29, 213, 40), 'Food eaten'), ('F5', (4, 52, 67, 63), 'Digging ants'), ('F6', (81, 52, 131, 63), 'Nest size'),
    ('F7', (143, 62, 222, 73), 'Colony health'), ('F8', (3, 90, 73, 101), 'Nursing ants'), ('F9', (121, 90, 194, 101), 'Egg production'),
    ('F10', (99, 123, 199, 134), 'Colony population'), ('F11', (231, 92, 290, 103), 'Starvation'), ('F12', (231, 111, 284, 122), 'Predation'),
    ('F13', (231, 130, 271, 141), 'Fights'),
]


def flow880():
    cv = Cv(290, 141, 'SHARED_880')

    def rec(src, dst, pts, **kw):
        pix = arrow(cv, pts, **kw)
        cv.arrows.append(dict(src=src, dst=dst, p0=pts[0], p1=pts[-1], pix=pix))
    # arrows first, boxes after (a box erases any stray pixel under it)
    rec('F1', 'F2', [(74, 8), (105, 8)])
    rec('F2', 'F3', [(125, 14), (125, 28)])
    rec('F2', 'F4', [(165, 14), (165, 28)])
    rec('F5', 'F6', [(67, 57), (80, 57)])
    rec('F6', 'F3', [(100, 51), (100, 40)])
    rec('F6', 'F9', [(125, 63), (125, 89)], dash=(2, 2))
    rec('F4', 'F7', [(185, 40), (185, 61)])
    rec('F3', 'F7', [(135, 40), (135, 67), (142, 67)], head_start=True)
    rec('F7', 'F9', [(165, 73), (165, 89)])
    rec('F8', 'F9', [(73, 95), (120, 95)])
    rec('F9', 'F10', [(150, 101), (150, 122)])
    rec('F7', 'F11', [(222, 67), (260, 67), (260, 91)])
    # the bar that gathers the three kinds of death, and one arrow from it to F10
    with cv.raw():
        for x in (223, 224):
            for y in range(97, 136):
                cv.put(x, y, 1)
        for y in (97, 116, 135):
            for x in range(225, 231):
                cv.put(x, y, 1)
    bar = set((x, y) for x in (223, 224) for y in range(97, 136))
    for (nm, y) in (('F11', 97), ('F12', 116), ('F13', 135)):
        cv.arrows.append(dict(src=nm, dst='F10', p0=(230, y), p1=(199, 128), pix=set((x, y) for x in range(225, 231)) | bar))
    pix = arrow(cv, [(222, 128), (199, 128)])
    cv.arrows.append(dict(src='bar', dst='F10', p0=(222, 128), p1=(199, 128), pix=pix))
    for nm, r, word in FLOW:
        cv.box(nm, r, word)
    cv.caption(3, 112, 'click a box for')
    cv.caption(3, 121, 'an explanation')
    return cv, 'the colony flowchart: 13 boxed labels (pop-up links) joined by cause-and-effect arrows, with a hint caption'


def build():
    return {510: nest510(), 520: talk520(), 530: trail530(), 540: fight540(), 550: aphids550(), 560: brood560(), 710: cycle710(),
            720: cycle720(), 880: flow880()}
