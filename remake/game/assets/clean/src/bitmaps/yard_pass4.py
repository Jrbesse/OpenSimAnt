"""yard_pass4: pass 4 of the yard spec: the animals (group F: the dog 8500..8511, 8600..8603; group G: the cat 1300..1305,
1310..1312, 1320..1329 and the bird 1250, 1251) and their assertions.  `build(reg)` registers the pictures; the checks are
registered with `reg.check`.

Design (see README.md, yard section "pass 4-5"): the dog is a white dog with brown patches and ears, a yellow collar; the cat is a
ginger cat with brown stripes, a white chest, paws and muzzle, and a cyan collar; the bird is a small tan bird with a dark wing and an
orange beak.  The dog and the cat are 3-D sphere chains rendered by yard_sprite (so all headings and poses are one creature);
the bird is drawn by hand.
"""
import numpy as np

import yard_sprite as sp
from yard_sprite import Pose, Scene
from uilib import Img, T

# --------------------------------------------------------------------------------------------------- the tables
# (id, w, h, dx, dy)
DOG_WALK = {
    0: [(8500, 17, 18, 1, 0), (8501, 16, 17, 0, 1), (8502, 15, 16, 1, 0)],
    1: [(8503, 18, 16, 2, 1), (8504, 21, 16, 0, 2), (8505, 19, 15, 1, 1)],
    2: [(8506, 16, 16, 2, 2), (8507, 14, 19, 2, 0), (8508, 12, 17, 2, 0)],
    3: [(8509, 19, 15, 1, 1), (8510, 20, 16, 0, 2), (8511, 18, 16, 1, 1)],
}
DOG_REST = {4: [(8600, 17, 16, 2, 1), (8601, 19, 16, 0, 1)], 5: [(8602, 18, 15, 2, 3), (8603, 20, 15, 0, 3)]}
CAT_WALK = [(1300, 18, 11), (1301, 16, 13), (1302, 16, 12)]
CAT_START = [(1310, 39, 34, -10, -21), (1311, 37, 32, -9, -19), (1312, 39, 31, -10, -18)]
CAT_POUNCE = [(1320, 23, 16, 0, 0), (1321, 26, 26, 2, -16), (1322, 34, 33, 4, -23), (1323, 33, 34, 6, -24), (1324, 34, 33, 8, -22),
              (1325, 26, 26, 10, -18), (1326, 23, 16, 12, -10), (1327, 16, 23, 14, -10), (1328, 23, 16, 16, -4), (1329, 16, 23, 18, -2)]
POUNCE_ARC = [(11.5, 8), (15, -3), (21, -6.5), (22.5, -7), (25, -5.5), (23, -5), (23.5, -2), (22, 1.5), (27.5, 4), (26, 9.5)]
BIRD = {1250: (11, 6, -10, -3), 1251: (10, 7, -9, -1)}

HEADING_DEG = {0: 45.0, 1: 0.0, 2: 225.0, 3: 180.0}
DOG_COLOURS = (15, 12, 0, 10, 11, 1)
CAT_COLOURS = (15, 3, 2, 0, 12, 10, 4, 7)

# colours
COAT = [12, 0, 0]          # white dog, grey shade
PATCH = [10, 10, 11]       # brown patches, ears
NOSE = [15]
GINGER = [3, 2, 2]         # cat coat: red-orange shade, orange
CWHITE = [12, 0, 0]
STRIPE = [10, 10, 10]


def spots_decal(pose, spots):
    sp_ = [(np.array(s[:3], dtype=float), s[3], s[4]) for s in spots]

    def fn(loc):
        out = np.full(len(loc), -1, dtype=np.int16)
        for c, r, col in sp_:
            d = np.linalg.norm(loc - c, axis=1)
            out[(d < r) & (out < 0)] = col
        return out
    return (pose, fn)


# --------------------------------------------------------------------------------------------------- the dog
DOG_SPOTS = [(-4.2, 0.4, 9.4, 2.1, 10), (0.4, 3.0, 7.6, 1.9, 10), (-2.6, -3.0, 7.0, 1.9, 10), (2.6, 0.0, 10.4, 1.3, 10),
             (-5.4, 2.2, 6.2, 1.5, 10)]


def dog_scene(heading, kind, ph, turn=0.0, tail=1.0, tailup=0.0):
    """kind 'walk' (ph 0, 1, 2), 'sit' (ph 0, 1), 'lie' (ph 0, 1).  heading in degrees.  turn: the head turned about the neck
    (degrees), tail: tail thickness factor, tailup: the tail raised by this much (frame tweaks that centre the mass)."""
    pose = Pose(heading=heading)
    ct, st = np.cos(np.radians(turn)), np.sin(np.radians(turn))
    pivot = {'walk': (3.6, 8.9), 'sit': (1.4, 11.2), 'lie': (4.5, 5.0)}[kind]

    def T_(p):        # turn a head point about the neck (in the ground plane)
        f, r, z = p
        df, dr = f - pivot[0], r
        return (pivot[0] + df * ct - dr * st, df * st + dr * ct, z)
    sc = Scene(ext=30.0, S=6)
    W = pose.w
    dec = spots_decal(pose, DOG_SPOTS)
    if kind == 'walk':
        sw = [0.0, 0.0, 0.0][ph]
        if ph == 0:
            off = dict(RF=2.6, LF=-2.0, RH=-2.4, LH=2.4)
            lift = dict(RF=0.0, LF=0.2, RH=0.2, LH=1.4)
        elif ph == 2:
            off = dict(RF=-2.0, LF=2.6, RH=2.4, LH=-2.4)
            lift = dict(RF=0.2, LF=0.0, RH=1.4, LH=0.2)
        else:
            off = dict(RF=0.7, LF=-0.7, RH=-0.7, LH=0.7)
            lift = dict(RF=0.0, LF=0.0, RH=0.0, LH=0.0)
        tail_up = [2.6, 4.6, 3.2][ph]
        tail_back = [-8.2, -9.6, -8.8][ph]
        # legs first (behind the body when seen from the far side, the z-buffer sorts the rest)
        for name, hipf, side in (('RH', -3.3, 1), ('LH', -3.3, -1), ('RF', 2.0, 1), ('LF', 2.0, -1)):
            hip = (hipf, side * 1.7, 5.0)
            foot = (hipf + off[name], side * 1.7, 0.6 + lift[name])
            sc.cap(W(hip), W(foot), 1.25, 1.0, COAT, pid=2)
            sc.sphere(W((foot[0] + 0.5, foot[1], foot[2] + 0.1)), 1.1, COAT, pid=2)
        sc.cap(W((-3.4, 0, 6.5)), W((1.9, 0, 6.9)), 3.5, 3.7, COAT, pid=1, decal=dec)
        sc.cap(W((1.9, 0, 6.9)), W((4.2, 0, 8.9)), 3.0, 2.6, COAT, pid=1)          # neck
        sc.sphere(W(T_((6.0, 0, 9.9))), 2.9, COAT, pid=3)                              # head
        sc.sphere(W(T_((8.5, 0, 9.1))), 1.7, COAT, pid=3)                              # snout
        sc.sphere(W(T_((9.9, 0, 9.3))), 0.9, NOSE, pid=3)                              # nose
        for side in (1, -1):
            sc.cap(W(T_((5.2, side * 2.4, 11.6))), W(T_((4.6, side * 3.0, 8.9))), 1.35, 1.1, PATCH, pid=5)   # ear
        sc.cap(W((-5.6, 0, 7.6)), W((tail_back, 0, 5.2 + tail_up + tailup)), 1.2 * tail, 0.85 * tail, COAT, pid=4)
        sc.mark(W(T_((7.4, 1.9, 10.9))), 15)
        sc.mark(W(T_((7.4, -1.9, 10.9))), 15)
    elif kind == 'sit':
        hx = [0.0, 0.7][ph]
        hz = [0.0, -0.5][ph]
        for side in (1, -1):
            sc.cap(W((1.0, side * 1.7, 7.6)), W((1.5, side * 1.7, 0.9)), 1.3, 1.0, COAT, pid=2)           # front legs
            sc.sphere(W((2.0, side * 1.7, 0.8)), 1.1, COAT, pid=2)
            sc.sphere(W((-1.3, side * 2.8, 3.1)), 2.7, COAT, pid=2)                                           # haunch
            sc.cap(W((-1.3, side * 2.9, 1.7)), W((1.6, side * 2.9, 0.9)), 1.2, 1.0, COAT, pid=2)             # hind foot
        sc.cap(W((-2.2, 0, 4.2)), W((0.1, 0, 8.4)), 3.9, 3.2, COAT, pid=1, decal=spots_decal(pose, [(-2.4, 0.2, 7.5, 2.1, 10), (-1.2, -3.0, 4.8, 1.8, 10)]))
        sc.cap(W((0.1, 0, 8.4)), W((1.6 + hx, 0, 11.2 + hz)), 3.0, 2.5, COAT, pid=1)
        sc.sphere(W(T_((2.4 + hx, 0, 13.4 + hz))), 2.8, COAT, pid=3)
        sc.sphere(W(T_((4.9 + hx, 0, 12.7 + hz))), 1.7, COAT, pid=3)
        sc.sphere(W(T_((6.3 + hx, 0, 12.9 + hz))), 0.9, NOSE, pid=3)
        for side in (1, -1):
            sc.cap(W(T_((1.6 + hx, side * 2.5, 15.2 + hz))), W(T_((1.0 + hx, side * 3.1, 12.2 + hz))), 1.35, 1.1, PATCH, pid=5)
        tail_end = [(-8.3, 0.2, 1.0), (-7.4, 3.2, 1.0)][ph]
        sc.cap(W((-5.0, 0, 1.6)), W((tail_end[0], tail_end[1], tail_end[2] + tailup)), 1.2 * tail, 0.85 * tail, COAT, pid=4)
        sc.mark(W(T_((3.7 + hx, 1.9, 14.4 + hz))), 15)
        sc.mark(W(T_((3.7 + hx, -1.9, 14.4 + hz))), 15)
    else:  # lie
        hz = [8.5, 0.0][ph]
        hf = [1.2, 0.4][ph]
        for side in (1, -1):
            sc.sphere(W((-3.0, side * 2.7, 3.0)), 3.0, COAT, pid=2)
            sc.cap(W((3.0, side * 1.7, 2.3)), W((9.0, side * 1.7, 0.9)), 1.3, 1.1, COAT, pid=2)
            sc.sphere(W((9.2, side * 1.7, 1.0)), 1.15, COAT, pid=2)
        sc.cap(W((-3.5, 0, 4.2)), W((2.6, 0, 4.6)), 4.2, 4.0, COAT, pid=1,
               decal=spots_decal(pose, [(-3.6, 0.3, 6.4, 2.0, 10), (0.4, 2.8, 4.6, 1.7, 10), (-1.4, -2.9, 4.6, 1.7, 10)]))
        sc.cap(W((2.6, 0, 3.9)), W((5.0 + hf, 0, 5.0 + hz * 0.6)), 3.0, 2.7, COAT, pid=1)
        sc.sphere(W(T_((6.2 + hf, 0, 4.6 + hz))), 2.8, COAT, pid=3)
        sc.sphere(W(T_((8.7 + hf, 0, 3.9 + hz))), 1.7, COAT, pid=3)
        sc.sphere(W(T_((10.0 + hf, 0, 4.0 + hz))), 0.9, NOSE, pid=3)
        for side in (1, -1):
            sc.cap(W(T_((5.4 + hf, side * 2.5, 6.4 + hz))), W(T_((4.8 + hf, side * 3.1, 3.7 + hz))), 1.35, 1.1, PATCH, pid=5)
        tail_end = [(-7.6, 0.3, 4.2), (-8.0, 3.4, 1.0)][ph]
        sc.cap(W((-5.8, 0, 2.0)), W((tail_end[0], tail_end[1], tail_end[2] + tailup)), 1.2 * tail, 0.85 * tail, COAT, pid=4)
        sc.mark(W(T_((7.5 + hf, 1.9, 6.0 + hz))), 15)
        sc.mark(W(T_((7.5 + hf, -1.9, 6.0 + hz))), 15)
    # the collar (1 to 3 pixels of colour 1; shows only where it faces the camera)
    if kind == 'walk':
        nf, nz = 3.9, 8.5
    elif kind == 'sit':
        nf, nz = 1.6 + [0, 0.7][ph], 11.6 + [0, -0.5][ph]
    else:
        nf, nz = 5.0 + [1.2, 0.4][ph], 5.2 + [8.5, 0.0][ph] * 0.6
    R = 2.65
    sc.mark(W((nf, R, nz - 0.3)), 1, 1.4)
    sc.mark(W((nf, R * 0.9, nz - 1.1)), 1, 1.4)
    sc.mark(W((nf, -R, nz - 0.3)), 1, 1.4)
    sc.mark(W((nf, -R * 0.9, nz - 1.1)), 1, 1.4)
    sc.mark(W((nf - 0.2, 0, nz + R * 0.95)), 1, 1.4)
    return sc


# per-frame tweaks that centre the mass (head turn in degrees, tail thickness, tail raised): found by a search so that the
# alignment rule of the spec holds with margin; every other frame uses the plain model
DOG_TWEAK = {8508: (30, 1.0, 4.0), 8602: (0, 1.5, 4.0)}


def build_dog(reg):
    for hd, rows in DOG_WALK.items():
        for ph, (bid, w, h, dx, dy) in enumerate(rows):
            img = dog_scene(HEADING_DEG[hd], 'walk', ph, *DOG_TWEAK.get(bid, ())).finish(w, h, line_pids={2, 5})
            reg.add(bid, img, (w, h), True, DOG_COLOURS, 'dog walking, heading %d, frame %d' % (hd, ph))
    for hd, rows in DOG_REST.items():
        for ph, (bid, w, h, dx, dy) in enumerate(rows):
            img = dog_scene(0.0, 'sit' if hd == 4 else 'lie', ph, *DOG_TWEAK.get(bid, ())).finish(w, h, line_pids={2, 5})
            reg.add(bid, img, (w, h), True, DOG_COLOURS, 'dog %s, frame %d' % ('sitting' if hd == 4 else 'lying', ph))


# --------------------------------------------------------------------------------------------------- the cat
def stripes_decal(pose, tail_rings=False):
    """Brown stripes across the back (bands along f), rings on the tail; below the back line the coat is plain."""
    def fn(loc):
        f, r, z = loc[:, 0], loc[:, 1], loc[:, 2]
        out = np.full(len(loc), -1, dtype=np.int16)
        band = (np.floor((f + 20.0) / 2.1) % 2) == 0
        out[band & (z > 4.3 + 1.4 * 0)] = 10
        return out
    return (pose, fn)


def ring_decal(pose):
    def fn(loc):
        k = np.floor((loc[:, 0] * 0.55 + loc[:, 2] * 0.75 + 30.0) / 1.6)
        return np.where(k % 2 == 0, 10, -1).astype(np.int16)
    return (pose, fn)


def cat_scene(heading, pp, pitch=0.0, spin=0.0, roll=0.0, elev=35.0, ext=30.0):
    """pp: the skeleton preset (see CAT_POSES).  Returns the Scene."""
    pose = Pose(heading=heading, pitch=pitch, roll=roll, spin=spin, elev=elev)
    sc = Scene(ext=ext, S=6, elev=elev)
    W = pose.w
    H, C = pp['H'], pp['C']
    hd = pp['head']
    sdec, rdec = stripes_decal(pose), ring_decal(pose)
    for name in ('RF', 'LF', 'RH', 'LH'):
        side = 1 if name[0] == 'R' else -1
        hip = (C[0] - 0.4, side * 1.8, C[2] - 1.3) if name[1] == 'F' else (H[0] + 0.3, side * 1.9, H[2] - 1.3)
        paw = pp[name]
        sc.cap(W(hip), W(paw), 1.35, 1.0, GINGER, pid=2)
        sc.sphere(W((paw[0] + 0.5, paw[1], paw[2])), 1.2, CWHITE, pid=2)
        if pp.get('claws'):
            for dr in (-0.7, 0.0, 0.7):
                sc.cap(W((paw[0] + 1.0, paw[1] + dr, paw[2] + 0.2)), W((paw[0] + 2.6, paw[1] + dr * 1.8, paw[2] + 0.1)), 0.45, 0.25, [0], pid=2)
    sc.cap(W(H), W(C), pp.get('Hr', 3.0), pp.get('Cr', 3.1), GINGER, pid=1, decal=sdec)
    neck = (C[0] + 1.8, 0, C[2] + pp.get('neckz', 1.8))
    sc.cap(W(C), W(neck), 3.0, 2.7, GINGER, pid=1)
    sc.sphere(W(hd), 2.7, GINGER, pid=3)                                           # head
    sc.sphere(W((hd[0] + 1.9, 0, hd[2] - 0.9)), 1.45, CWHITE, pid=3)               # muzzle
    sc.sphere(W((hd[0] + 3.1, 0, hd[2] - 0.4)), 0.55, [4], pid=3)                  # nose
    for side in (1, -1):
        sc.cap(W((hd[0] - 0.5, side * 1.6, hd[2] + 1.8)), W((hd[0] - 0.5, side * 2.3, hd[2] + 4.2)), 1.15, 0.35, GINGER, pid=5)   # ear
    pts = pp['tail']
    for a, b, r0, r1 in zip(pts, pts[1:], pp.get('tailR', (1.1, 1.0, 0.9, 0.8))[:-1], pp.get('tailR', (1.1, 1.0, 0.9, 0.8))[1:]):
        sc.cap(W(a), W(b), r0, r1, GINGER, pid=4, decal=rdec)
    sc.mark(W((hd[0] + 1.3, 1.95, hd[2] + 0.8)), 15)
    sc.mark(W((hd[0] + 1.3, -1.95, hd[2] + 0.8)), 15)
    R = 2.6
    sc.mark(W((neck[0] - 0.3, R, neck[2] - 0.6)), 7, 1.4)
    sc.mark(W((neck[0] - 0.3, -R, neck[2] - 0.6)), 7, 1.4)
    sc.mark(W((neck[0] - 0.5, 0, neck[2] + R * 0.9)), 7, 1.4)
    return sc


def preset(Hz, Cz, headz, legs, tail, **kw):
    pp = dict(H=(-4.4, 0, Hz), C=(2.6, 0, Cz), head=(6.4, 0, headz), tail=tail)
    for k, v in legs.items():
        pp[k] = v
    pp.update(kw)
    return pp


# walking right: ph 0 = the stretched pose, 1 and 2 the two stride poses
def cat_walk_pose(ph):
    if ph == 0:
        return preset(4.6, 4.9, 6.7, dict(RF=(8.2, 1.7, 1.0), LF=(6.4, -1.7, 1.6), RH=(-9.4, 1.9, 1.0), LH=(-7.6, -1.9, 1.7)),
                      [(-6.5, 0, 5.8), (-8.8, 0, 6.8), (-10.8, 0, 7.6), (-12.6, 0, 8.2)], tailR=(1.1, 1.0, 0.9, 0.8))
    if ph == 1:
        return preset(5.6, 5.8, 8.0, dict(RF=(5.8, 1.7, 0.9), LF=(2.2, -1.7, 1.0), RH=(-7.2, 1.9, 1.0), LH=(-3.6, -1.9, 1.8)),
                      [(-6.2, 0, 7.0), (-8.6, 0, 8.6), (-9.2, 0, 11.4), (-7.4, 0, 13.6)])
    return preset(5.4, 5.7, 7.9, dict(RF=(2.4, 1.7, 1.3), LF=(5.6, -1.7, 0.9), RH=(-3.2, 1.9, 1.5), LH=(-7.4, -1.9, 1.0)),
                  [(-6.2, 0, 6.9), (-8.8, 0, 8.4), (-9.6, 0, 11.0), (-8.0, 0, 13.0)])


def build_cat_walk(reg):
    right = {}
    for ph, (bid, w, h) in enumerate(CAT_WALK):
        img = cat_scene(0.0, cat_walk_pose(ph)).finish(w, h, line_pids={2, 5})
        right[ph] = img
        reg.add(bid, img, (w, h), True, CAT_COLOURS, 'cat walking right, frame %d' % ph)
    for ph, (bid, w, h) in enumerate(CAT_WALK):
        m = Img(w, h, T)
        m.a = right[ph].a[:, ::-1].copy()
        reg.add(bid + 3, m, (w, h), True, CAT_COLOURS, 'cat walking left (the mirror image of %d)' % bid)


# the startled cat: upright, facing the viewer, bristling (frame 0 = 1310 once, then 1311 / 1312 alternate)
def cat_startled(var, leap=None, heading=270.0, pitch=0.0, roll=0.0, spin=0.0):
    """var 0, 1, 2 = 1310, 1311, 1312.  Local f points at the viewer; the cat stands on its hind legs, arched, mouth open.
    leap = (arm_r, arm_z, arm2_r, arm2_z, bristle): the same cat springing at the viewer (pounce frames 1322..1324): the front legs
    thrown out with the claws spread, the fur lying flat."""
    pose = Pose(heading=heading, pitch=pitch, roll=roll, spin=spin)
    sc = Scene(ext=34.0, S=6)
    W = pose.w
    def _fz(loc):
        out = np.full(len(loc), -1, dtype=np.int16)
        out[(np.floor(loc[:, 2] / 2.4) % 2 == 0) & (np.abs(loc[:, 1]) > 2.2) & (loc[:, 2] > 3.0)] = 10
        return out
    sdec = (pose, _fz)
    arms = [(9.5, 8.0), (8.4, 9.4), (9.8, 6.8)][var]          # front paws out to the sides (r, z)
    arms2 = arms
    bristle = 1.0
    if leap:
        arms, arms2, bristle = (leap[0], leap[1]), (leap[2], leap[3]), leap[4]
    tail_x = [1.0, -1.0, 1.0][var]
    tw = [2.0, 3.6, 0.6][var]                                   # how far the tail leans
    mouth = [3.0, 2.2, 2.6][var]
    # hind legs and feet
    for side in (1, -1):
        sc.cap(W((0.0, side * 5.2, 5.0)), W((1.6, side * 6.0, 1.2)), 3.0, 2.3, GINGER, pid=2)
        sc.cap(W((1.6, side * 6.0, 1.2)), W((3.2, side * 6.2, 1.0)), 2.2, 2.2, CWHITE, pid=2)
        ar_, az_ = arms if side == 1 else arms2
        sc.cap(W((1.5, side * 3.4, 12.0)), W((3.2, side * ar_, az_)), 2.0, 1.6, GINGER, pid=2)        # front legs out
        sc.sphere(W((3.8, side * (ar_ + 0.6), az_ - 0.2)), 1.9, CWHITE, pid=2)
        for dr in (-1.1, 0.0, 1.1):
            sc.cap(W((4.2, side * (ar_ + 0.6) + dr, az_ - 1.2)), W((5.8, side * (ar_ + 1.5) + dr * 1.6, az_ - 2.8)), 0.5, 0.3, [0], pid=2)
    sc.sphere(W((0.0, 0.0, 6.5)), 6.2, GINGER, pid=1, decal=sdec)                  # haunches
    sc.cap(W((0.4, 0, 7.0)), W((0.6, 0, 13.0)), 6.4, 5.6, GINGER, pid=1, decal=sdec)   # the arched body
    sc.sphere(W((1.0, 0, 13.0)), 5.4, CWHITE, pid=1)                                  # chest tuft
    # tail: a bottle brush behind
    sc.cap(W((-3.0, tail_x * 3.0, 4.0)), W((-3.2, tail_x * (6.0 + tw), 12.0)), 2.4, 2.9, GINGER, pid=4, decal=ring_decal(pose))
    sc.cap(W((-3.2, tail_x * (6.0 + tw), 12.0)), W((-3.4, tail_x * (4.0 + tw), 20.0)), 2.9, 2.0, GINGER, pid=4, decal=ring_decal(pose))
    # head
    sc.sphere(W((2.0, 0, 20.0)), 5.6, GINGER, pid=3)
    sc.sphere(W((4.4, 0, 18.4)), 3.0, CWHITE, pid=3)                                  # muzzle
    sc.sphere(W((6.8, 0, 17.0 - mouth * 0.4)), mouth, [3], pid=6)                     # open mouth (red)
    sc.sphere(W((7.0, 0, 18.6)), 0.8, [4], pid=6)                                     # nose
    for side in (1, -1):
        sc.cap(W((1.0, side * 3.4, 23.0)), W((1.0, side * 5.6, 27.8)), 2.3, 0.5, GINGER, pid=5)     # ears
        sc.sphere(W((5.4, side * 2.8, 21.2)), 1.7, [0], pid=6)                         # eyes
        sc.mark(W((7.1, side * 2.8, 21.2)), 15, 2.0)
    sc.mark(W((7.4, -1.0, 15.6)), 0, 2.0)
    sc.mark(W((7.4, 1.0, 15.6)), 0, 2.0)
    # the bristling fur: spikes on the body, the head and the tail
    spikes = [((0.0, 0, 6.5), 6.2, range(-125, 126, 21)), ((0.6, 0, 11.0), 6.2, range(-90, 91, 22)),
              ((2.0, 0, 20.0), 5.6, range(-80, 81, 24))]
    for (c, R, angs) in spikes:
        for i, a in enumerate(angs):
            ar = np.radians(a)
            d = np.array([0.15, np.sin(ar), np.cos(ar)])
            d /= np.linalg.norm(d)
            ln = (3.3 + (1.2 if (i + var) % 2 else 0.0)) * bristle
            P0 = np.array(c) + d * R * 0.8
            P1 = np.array(c) + d * (R + ln)
            sc.cap(W(P0), W(P1), 1.2, 0.35, GINGER, pid=7)
    return sc


def build_cat_startled(reg):
    for var, (bid, w, h, dx, dy) in enumerate(CAT_START):
        img = cat_startled(var).finish(w, h, line_pids={2, 5})
        reg.add(bid, img, (w, h), True, CAT_COLOURS, 'cat startled, frame %d' % var)


# the pounce: 1320 crouches, 1321..1325 leap towards the viewer (claws out), 1326..1329 tumble away
POUNCE_POSES = {
    'crouch': preset(4.2, 3.2, 4.8, dict(RF=(6.6, 1.7, 0.9), LF=(5.2, -1.7, 0.9), RH=(-3.2, 2.0, 1.1), LH=(-2.4, -2.0, 1.1)),
                     [(-6.0, 0, 4.6), (-9.0, 0, 5.6), (-11.6, 0, 4.4)]),
    'leap': preset(5.0, 6.0, 7.6, dict(RF=(11.5, 2.0, 7.8), LF=(10.8, -2.0, 6.6), RH=(-9.5, 2.0, 2.8), LH=(-9.0, -2.2, 4.0)),
                   [(-6.2, 0, 6.0), (-9.5, 0, 7.0), (-12.0, 0, 8.5), (-13.5, 0, 10.5)], claws=True),
    'tumble': preset(4.8, 4.8, 6.0, dict(RF=(3.6, 1.7, 1.6), LF=(3.0, -1.7, 2.4), RH=(-1.4, 2.0, 1.6), LH=(-2.2, -2.0, 2.6)),
                     [(-6.0, 0, 5.0), (-8.2, 0, 7.0), (-7.2, 0, 9.6), (-4.6, 0, 10.4)]),
}
# id -> (preset, heading, pitch, spin, roll)
POUNCE_CAMERA = {
    1320: ('crouch', 0.0, 0.0, 0.0, 0.0),
    1321: ('leap', 315.0, 25.0, 0.0, 0.0),
    1322: ('leap', 270.0, 0.0, 0.0, 0.0),
    1323: ('leap', 262.0, -8.0, 0.0, 0.0),
    1324: ('leap', 280.0, 6.0, 0.0, 14.0),
    1325: ('leap', 215.0, -30.0, 20.0, 0.0),
    1326: ('tumble', 0.0, 0.0, -20.0, 0.0),
    1327: ('tumble', 0.0, 0.0, 70.0, 0.0),
    1328: ('tumble', 180.0, 0.0, 165.0, 0.0),
    1329: ('tumble', 180.0, 0.0, 250.0, 0.0),
}


# 1322..1324: the head-on leap (the startled cat's model with the arms thrown out): (arm_r, arm_z, arm2_r, arm2_z, bristle)
POUNCE_FRONT = {1322: (12.5, 17.0, 12.5, 17.0, 0.4), 1323: (13.0, 12.0, 11.0, 18.0, 0.4), 1324: (11.5, 19.0, 13.5, 11.0, 0.4)}


def build_cat_pounce(reg):
    for (bid, w, h, dx, dy) in CAT_POUNCE:
        name, hd, pit, spin, roll = POUNCE_CAMERA[bid]
        if bid in POUNCE_FRONT:
            img = cat_startled(1, POUNCE_FRONT[bid], hd, pit, roll, spin).finish(w, h, line_pids={2, 5})
            reg.add(bid, img, (w, h), True, CAT_COLOURS, 'cat pouncing, frame %d' % (bid - 1320))
            continue
        img = cat_scene(hd, POUNCE_POSES[name], pitch=pit, spin=spin, roll=roll, ext=34.0).finish(w, h, line_pids={2, 5})
        reg.add(bid, img, (w, h), True, CAT_COLOURS, 'cat pouncing, frame %d' % (bid - 1320))


# --------------------------------------------------------------------------------------------------- the bird
BIRD_LEGEND = {'f': 15, 'b': 11, 'w': 10, 'k': 2, 'c': 12, 'e': 15, '.': T}
BIRD_ART = {
    1250: ["..f.....f..",
           "..fwf.fwf..",
           "...fwfwf...",
           ".ffbbbbbffk",
           "fbbbbbbbebk",
           ".ffccccfff."],
    1251: [".ffffff...",
           "fbbbbbbffk",
           "fwbbbbbbek",
           ".fwwwbbffk",
           "..fwwwfff.",
           "...fwwf...",
           "....ff...."],
}


def bird(bid):
    rows = BIRD_ART[bid]
    w, h = BIRD[bid][:2]
    assert len(rows) == h and all(len(r) == w for r in rows), bid
    img = Img(w, h, T)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            img.a[y, x] = BIRD_LEGEND[ch]
    return img


def build_bird(reg):
    for bid in (1250, 1251):
        reg.add(bid, bird(bid), BIRD[bid][:2], True, (15, 11, 10, 2, 12), 'small bird in flight to the right, wings %s' % ('up' if bid == 1250 else 'down'))


def build(reg):
    build_dog(reg)
    build_cat_walk(reg)
    build_cat_startled(reg)
    build_cat_pounce(reg)
    build_bird(reg)
    reg.check(check_pass4)


def check_pass4(reg):
    I = reg.img
    ids = [b[0] for v in DOG_WALK.values() for b in v] + [b[0] for v in DOG_REST.values() for b in v]
    ids += [b[0] for b in CAT_WALK] + [b[0] + 3 for b in CAT_WALK] + [b[0] for b in CAT_START] + [b[0] for b in CAT_POUNCE] + [1250, 1251]
    assert len(ids) == 37 and len(set(ids)) == 37 and all(i in I for i in ids)
    for i in ids:
        assert sp.tight(I[i]), (i, 'tight')
    # --- F: the dog (R = centroid + offset: |R.x - 9.5| <= 1.5, |R.y - 9.2| <= 2.0; spreads in a set <= 2.0 / 2.5)
    for rows in list(DOG_WALK.values()) + list(DOG_REST.values()):
        Rs = []
        for (bid, w, h, dx, dy) in rows:
            cx, cy = sp.centroid(I[bid])
            R = (cx + dx, cy + dy)
            assert abs(R[0] - 9.5) <= 1.5 and abs(R[1] - 9.2) <= 2.0, (bid, 'dog alignment', R)
            Rs.append(R)
            n1 = int((I[bid].a == 1).sum())
            assert n1 <= 3, (bid, 'collar is 1 to 3 pixels', n1)
            profile = bid in (8503, 8504, 8505, 8509, 8510, 8511) or bid >= 8600
            assert n1 >= 1 or not profile, (bid, 'collar visible in profile / resting')
        assert max(r[0] for r in Rs) - min(r[0] for r in Rs) <= 2.0, ('dog x spread', rows[0][0])
        assert max(r[1] for r in Rs) - min(r[1] for r in Rs) <= 2.5, ('dog y spread', rows[0][0])
    # --- G: the cat
    for (bid, w, h) in CAT_WALK:
        for b in (bid, bid + 3):
            a = I[b].a
            cx, cy = sp.centroid(I[b])
            assert 7.0 <= cx <= 9.5 and 5.0 <= cy <= 7.0, (b, 'cat walking centroid', cx, cy)
            assert (a[0] != T).any(), (b, 'row 0 (the back line) is opaque')
            nb = int((a == 7).sum())
            assert 1 <= nb <= 3, (b, 'collar mark of colour 7', nb)
        assert (I[bid + 3].a == I[bid].a[:, ::-1]).all(), (bid + 3, 'mirror image')
    for (bid, w, h, dx, dy) in CAT_START:
        a = I[bid].a
        cx, cy = sp.centroid(I[bid])
        assert abs(cx - w // 2) <= 2.0, (bid, 'startled centroid x', cx, w // 2)
        feet = np.where((a[-3:] != T).any(axis=0))[0]
        assert len(feet) >= 8 and abs(feet.mean() - w // 2) <= 3.0, (bid, 'startled feet in the bottom 3 rows', len(feet))
        assert (a[-1] != T).sum() >= 4, (bid, 'bottom row')
    for k, (bid, w, h, dx, dy) in enumerate(CAT_POUNCE):
        cx, cy = sp.centroid(I[bid])
        assert abs(cx - w / 2.0) <= 3.0 and abs(cy - h / 2.0) <= 3.0, (bid, 'pounce centroid vs box centre', cx - w / 2.0, cy - h / 2.0)
        bc = (w / 2.0 + dx, h / 2.0 + dy)
        assert abs(bc[0] - POUNCE_ARC[k][0]) <= 0.51 and abs(bc[1] - POUNCE_ARC[k][1]) <= 0.51, (bid, 'pounce arc', bc)
    for i in ids:
        if 1300 <= i <= 1329 or i in (1250, 1251):
            assert not (I[i].a == 1).any(), (i, 'colour 1 is only the dog collar')
    # --- the bird: R = centroid + offset within 2.0 of (-4.7, 0.8)
    for bid in (1250, 1251):
        cx, cy = sp.centroid(I[bid])
        dx, dy = BIRD[bid][2:]
        assert np.hypot(cx + dx + 4.7, cy + dy - 0.8) <= 2.0, (bid, 'bird alignment', cx + dx, cy + dy)
