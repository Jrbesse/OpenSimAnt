"""yard_scene: the drawing program of the yard window's scenery (spec yard_bitmaps.md, groups A and C, pass 1).

ONE program draws the lawn, the lattice, the back fence and the garden once (`draw_scenery`), and two functions draw the house on
top of it: `draw_house_outside` (picture 7000) and `draw_house_inside` (picture 7001).  `render_world` calls them and returns the
`World` (yardlib): 7000 / 7001 are its columns 0..280, 7003 its columns 281..513 (`pictures`).  The strips 7020..7022 come from
`strips` (the same `lattice` function).

Pass 3 (the door and room patches) imports this module: render the scene with the person drawn in through the hooks,
crop the rectangle, never paint a patch separately:

    w = render_world('outside', door=0.35, hooks={'behind': draw_person_fn})      # fn(world) draws in yard coordinates
    patch = w.pic(172, 198)[73:115]                                                # 8900 (26 x 42)
    w = render_world('inside', hooks={'chair': fn})                               # 8200 = rows 166..195, yard x 45..61
    w = render_world('inside', fridge_open=True, hooks={'fridge': fn})            # 8201 = rows 47..76, yard x 207..225

`door` is the opening 0.0 (closed) .. 1.0 (wide open); hooks: 'behind' (drawn in the doorway before the door leaf), 'front'
(after the leaf), 'chair', 'fridge' (after the furniture of the inside view).  Rectangles: DOOR_RECT, CHAIR_RECT, FRIDGE_RECT.
"""
import numpy as np

from yardlib import World, G, lattice, house_covers, polygon_mask, OX, WORLD_W, WORLD_H, W7000, W7003
from uilib import text, text_c, LABEL, LABEL_TALL, SMALL, Img, T

# ------------------------------------------------------------------------------------------------ fixed rectangles (yard)
DOOR_RECT = (172, 73, 198, 115)        # the niche: 26 x 42 (x1 / y1 exclusive); picture 7000 pixel x + 2
CHAIR_RECT = (45, 166, 62, 196)        # 17 x 30, picture 7001
FRIDGE_RECT = (207, 47, 226, 77)       # 19 x 30, picture 7001
MOWER_PARK = (98, 181, 113, 196)       # actors' places: kept free of detail
SIGN_PLACE = (170, 186, 224, 223)
PORCH_LAWN = (150, 100, 230, 160)
PERSON_PATH = [(53, 195), (100, 161), (163, 89), (198, 89)]     # his feet in the House view
NICHE_WALL = 0                          # the colour of the niche's outer ring (wall colour of the porch front)

# ------------------------------------------------------------------------------------------------ the house (ground s, rows y, heights z)
S_L, S_R = 212, 288                     # footprint of the main block in s (the right wall stands on x + y = 288)
Y_BACK = 65                             # its back wall; the block runs on beyond the picture's bottom
WALL_H = 50
RIDGE_S, RIDGE_Z, HIP_Y = 250, 60, 80
OVER = 3                                # eave overhang
FAR = 285                               # "far" y: beyond the bottom of the picture
P_S0, P_S1, P_Y0, P_Y1 = 286, 316, 65, 115     # the porch box (front face on y = 115, door in it)

# HOUSE_MASK: the house's outline with its roof overhang and the porch (yard coordinates), a little generous.  Both pictures
# 7000 and 7001 must be identical outside it.
HOUSE_MASK = [(145, 10), (231, 10), (260, 17), (260, 66), (254, 66), (204, 116), (173, 116), (62, 227), (-3, 227), (-3, 158)]
MASK = polygon_mask(HOUSE_MASK)


def in_house_mask(x, y):
    return bool(MASK[y, x + OX])


def porch_zt(s):                        # porch roof top surface
    return 49 - (s - P_S0) * 2.0 / 33.0


def porch_zu(s):                        # its underside = the top of the porch walls
    return porch_zt(s) - 2


def eave_z(s):                          # main roof surface height at ground s (right slope, s > RIDGE_S)
    return RIDGE_Z - (s - RIDGE_S) * (RIDGE_Z - 50.0) / (S_R + OVER - RIDGE_S)


# ------------------------------------------------------------------------------------------------ the scenery shared by 7000 / 7001 / 7003
_rng = None


def _tree(w, cx, cy, rx, ry, trunk=0, shadow_y=None):
    if shadow_y is not None:
        w.ellipse(cx, shadow_y, rx * 0.8, 3, 14)
    if trunk:
        w.rect(cx - 2, cy + ry - 4, cx + 2, cy + ry + trunk, 10)
        w.rect(cx - 2, cy + ry - 4, cx - 1, cy + ry + trunk, 11)
        w.rect(cx - 2, cy + ry + trunk - 1, cx + 2, cy + ry + trunk, 15)
        w.rect(cx - 3, cy + ry - 4, cx - 2, cy + ry + trunk, 15)
        w.rect(cx + 2, cy + ry - 4, cx + 3, cy + ry + trunk, 15)
    px = w.ellipse(cx, cy, rx, ry, 9)
    w.ellipse(cx - rx * 0.28, cy - ry * 0.3, rx * 0.62, ry * 0.58, 8)
    for _ in range(int(rx * ry / 9)):                      # leaf specks
        a = _rng.uniform(0, 2 * np.pi)
        r = _rng.uniform(0.2, 0.85)
        x, y = int(cx + np.cos(a) * rx * r), int(cy + np.sin(a) * ry * r)
        if w.get(x, y) == 9:
            w.put(x, y, 8)
        elif w.get(x, y) == 8:
            w.put(x, y, 9)
    w.outline_pixels(px, 15)


def _bush(w, cx, cy, rx, ry):
    px = w.ellipse(cx, cy, rx, ry, 9)
    w.ellipse(cx - rx * 0.3, cy - ry * 0.3, rx * 0.55, ry * 0.5, 8)
    w.outline_pixels(px, 15)


def draw_garden(w):
    """Everything on the grey ground behind and beside the house and behind the fence (never on the lawn)."""
    global _rng
    _rng = np.random.RandomState(11)
    # left of / behind the house (x + y stays below the house's left eave, 159)
    _tree(w, 42, 50, 20, 17, trunk=12, shadow_y=82)
    _tree(w, 96, 31, 14, 12, trunk=8, shadow_y=54)
    _bush(w, 14, 74, 9, 6)
    _bush(w, 27, 80, 7, 5)
    # a raised flower bed
    w.obox(52, 66, 24, 5, 4, 9, 10, 10)
    for i, c in enumerate([3, 1, 4, 0, 3, 1, 3]):
        w.put(54 + i * 3, 62 + (i % 2), c)
        w.put(54 + i * 3, 63 + (i % 2), 8)
    # a dog house
    w.obox(10, 98, 16, 10, 6, 10, 11, 10)
    w.fill_poly([(8, 98), (28, 98), (34, 91), (14, 91)], 3)
    w.fill_poly([(28, 98), (34, 91), (34, 93), (28, 100)], 10)
    w.outline_pixels(w.poly_pixels([(8, 98), (28, 98), (34, 91), (14, 91)]), 15)
    w.rect(15, 101, 22, 108, 15)
    w.rect(15, 101, 22, 102, 15)
    # a coiled garden hose
    hp = w.ellipse(14, 120, 7, 3, 9)
    w.ellipse(14, 120, 3, 1.4, 13)
    w.outline_pixels(hp, 15)
    w.put(22, 121, 15)
    # behind the fence: trees and a shrub that rise above it
    _tree(w, 398, 21, 22, 16)
    _tree(w, 462, 24, 16, 13)
    _bush(w, 330, 33, 11, 6)
    _bush(w, 268, 34, 9, 6)


def draw_fence(w):
    """Back fence: top edge y = 38 from x = 250 to the right edge, posts every 28 px, foot at y 62..64."""
    x0, x1 = 250, 512
    w.rect(x0, 38, x1, 39, 12)          # the walking top: a light plank
    w.rect(x0, 39, x1, 41, 11)
    w.rect(x0, 41, x1, 42, 10)
    for x in range(x0, x1):
        k = (x - x0) % 7
        col = 11 if k < 5 else 10
        w.rect(x, 42, x + 1, 62, col)
    w.rect(x0, 54, x1, 56, 10)          # lower rail
    w.rect(x0, 54, x1, 55, 11)
    w.rect(x0, 62, x1, 64, 10)
    w.rect(x0, 64, x1, 65, 15)
    for px_ in range(x0, x1, 28):       # posts
        w.rect(px_, 38, px_ + 3, 64, 10)
        w.rect(px_, 38, px_ + 1, 64, 11)
        w.rect(px_, 38, px_ + 3, 39, 12)
    # a flower bed along the fence foot (above the lattice's top line: y <= 64)
    for gx in range(262, 505, 29):
        for j, c in enumerate([3, 1, 4, 3]):
            w.put(gx + j * 3, 59 + (j % 2), 8)
            w.put(gx + j * 3, 60 + (j % 2), 9)
            w.put(gx + j * 3 + 1, 58 + (j % 2), c)
            w.put(gx + j * 3 + 1, 59 + (j % 2), 9)


def draw_lawn(w):
    for y in range(65, 226):
        for x in range(232 - y, 569 - y):
            c = lattice(x, y)
            if c is not None and -2 <= x <= 511:
                w.put(x, y, c)


def draw_scenery(w):
    draw_garden(w)
    draw_fence(w)
    draw_lawn(w)


# ------------------------------------------------------------------------------------------------ the house, outside
def _quad(w, s0, s1, ya, yb, za, zb, colour, pattern=None):
    """A quad on the plane s = const: y in [ya, yb], z in [za, zb]; (s0 == s1) or on y = const when ya == yb."""
    pts = [G(s0, ya, za), G(s1, yb, za), G(s1, yb, zb), G(s0, ya, zb)]
    return w.fill_poly(pts, colour, pattern)


def _window_right(w, s, ya, yb, za, zb):
    """A window in a wall on the plane s = const (facing the lawn)."""
    w.fill_poly([G(s, ya, za), G(s, yb, za), G(s, yb, zb), G(s, ya, zb)], 0)
    w.poly_outline([G(s, ya, za), G(s, yb, za), G(s, yb, zb), G(s, ya, zb)], 15)
    ym = (ya + yb) / 2.0
    w.fill_poly([G(s, ya + 2, za + 2), G(s, yb - 2, za + 2), G(s, yb - 2, zb - 2), G(s, ya + 2, zb - 2)], 7)
    w.line(*G(s, ym, za + 2), *G(s, ym, zb - 2), 0)              # mullion
    w.line(*G(s, ya + 2, (za + zb) / 2), *G(s, yb - 2, (za + zb) / 2), 0)
    w.line(*G(s, ya + 3, zb - 3), *G(s, ya + 6, zb - 6), 0)       # a glint
    w.line(*G(s, ya, za - 1), *G(s, yb, za - 1), 13)             # sill


def draw_door(w, f=0.0, hooks=None):
    """The porch door in the niche DOOR_RECT.  f = how far it is open (0 closed .. 1 wide open).  The outer ring of the niche
    (1 px) is wall colour; the door, its frame and its step lie inside."""
    hooks = hooks or {}
    x0, y0, x1, y1 = DOOR_RECT
    w.rect(x0, y0, x1, y1, NICHE_WALL)
    w.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, 14)                  # frame / jamb 24 x 40
    ox0, oy0, ox1, oy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 4          # the opening: 22 x 36 (cols 174..195, rows 75..110)
    # the step (three rows under the opening)
    w.rect(x0 + 1, oy1, x1 - 1, oy1 + 1, 12)
    w.rect(x0 + 1, oy1 + 1, x1 - 1, oy1 + 2, 13)
    w.rect(x0 + 1, oy1 + 2, x1 - 1, oy1 + 3, 14)
    if f > 0:
        w.rect(ox0, oy0, ox1, oy1, 14)                           # the dark hall
        w.rect(ox0, oy1 - 11, ox1, oy1, 13)                      # its floor
        w.rect(ox0, oy1 - 11, ox1, oy1 - 10, 15)
        w.rect(ox0 + 11, oy0 + 6, ox1 - 3, oy0 + 22, 13)         # a pale window far inside
        w.rect(ox0 + 11, oy0 + 6, ox1 - 3, oy0 + 7, 12)
    if hooks.get('behind'):
        hooks['behind'](w)
    wl = int(round(22 * (1 - 0.9 * f)))
    wl = max(3, wl)
    k = int(round(5 * f))
    leaf = [(ox0, oy0), (ox0 + wl, oy0 + k), (ox0 + wl, oy1 - k), (ox0, oy1)]
    w.fill_poly(leaf, 10)
    if wl >= 10:                                                 # two inset panels
        px = ox0 + 3
        pw = wl - 6
        for (ya, yb) in ((oy0 + 4, oy0 + 16), (oy0 + 20, oy1 - 3)):
            ya2, yb2 = ya + int(k * 0.6), yb - int(k * 0.6)
            w.rect(px, ya2, px + pw, ya2 + 1, 15)
            w.rect(px, ya2, px + 1, yb2, 15)
            w.rect(px, yb2 - 1, px + pw, yb2, 11)
            w.rect(px + pw - 1, ya2, px + pw, yb2, 11)
        w.rect(ox0 + wl - 4, oy0 + 22, ox0 + wl - 2, oy0 + 24, 1)  # the knob
    w.rect(ox0, oy0, ox0 + 1, oy1, 11)                            # hinge edge, lit
    w.line(ox0 + wl, oy0 + k, ox0 + wl, oy1 - k, 15)
    if k:
        w.line(ox0, oy0, ox0 + wl, oy0 + k, 15)
        w.line(ox0, oy1 - 1, ox0 + wl, oy1 - k - 1, 15)
    if hooks.get('front'):
        hooks['front'](w)


def draw_house_outside(w, door=0.0, hooks=None):
    w.clip = MASK
    sr = S_R
    # --- the long right wall (towards the lawn), its foundation, its windows
    _quad(w, sr, sr, Y_BACK, FAR, 0, WALL_H, 12)
    _quad(w, sr, sr, Y_BACK, FAR, 0, 4, 13)
    for (ya, yb) in ((130, 152), (176, 198), (222, 244)):
        _window_right(w, sr, ya, yb, 17, 39)
    for yy in range(115, 226):                                   # the foot of the wall (a pixel the polygon misses)
        w.put(287 - yy, yy, 13)
    # --- the roof: left slope (lit, red), right slope (shaded, brown), the hip at the back
    sl, sr_e = S_L - OVER, S_R + OVER
    left = [G(sl, 62, 50), G(RIDGE_S, HIP_Y, RIDGE_Z), G(RIDGE_S, FAR, RIDGE_Z), G(sl, FAR, 50)]
    right = [G(sr_e, 62, 50), G(RIDGE_S, HIP_Y, RIDGE_Z), G(RIDGE_S, FAR, RIDGE_Z), G(sr_e, FAR, 50)]
    hip = [G(sl, 62, 50), G(sr_e, 62, 50), G(RIDGE_S, HIP_Y, RIDGE_Z)]
    w.fill_poly(left, 3, lambda x, y: 10 if (x + y) % 4 == 0 else None)
    w.fill_poly(right, 10, lambda x, y: 14 if (x + y) % 4 == 0 else None)
    w.fill_poly(hip, 3, lambda x, y: 10 if y % 3 == 0 else None)
    # under-eave shadow on the wall and the roof edges
    w.line(*G(sr_e, 62, 48), *G(sr_e, FAR, 48), 14)
    w.line(*G(sr_e, 62, 49), *G(sr_e, FAR, 49), 15)
    for poly in (left, right, hip):
        w.poly_outline(poly, 15)
    # a skylight on the left slope and a chimney on the right
    zl = lambda s: 50 + (s - sl) * 10.0 / (RIDGE_S - sl)
    sky = [G(222, 170, zl(222)), G(236, 170, zl(236)), G(236, 184, zl(236)), G(222, 184, zl(222))]
    w.fill_poly(sky, 7)
    w.poly_outline(sky, 15)
    w.line(*G(222, 177, zl(222)), *G(236, 177, zl(236)), 0)
    w.gbox(266, 276, 104, 112, 53, 74, 14, 3, 10)
    w.fill_poly([G(268, 106, 74), G(274, 106, 74), G(274, 110, 74), G(268, 110, 74)], 15)
    for zz in (60, 66):
        w.line(*G(266, 112, zz), *G(276, 112, zz), 10)
    # --- the porch: right wall (shaded), front face (lit, the door), lean-to roof
    s0, s1, y0, y1 = P_S0, P_S1, P_Y0, P_Y1
    w.fill_poly([G(s1, y1, 0), G(s1, y0, 0), G(s1, y0, porch_zu(s1)), G(s1, y1, porch_zu(s1))], 12)
    w.fill_poly([G(s1, y1, 0), G(s1, y0, 0), G(s1, y0, 4), G(s1, y1, 4)], 13)
    _window_right(w, s1, 80, 100, 14, 34)
    for yy in range(65, 114):                                    # the foot of the porch wall (a pixel the polygon misses)
        w.put(315 - yy, yy, 13)
    w.put(201, 114, 13)
    w.fill_poly([G(s0, y1, 0), G(s1, y1, 0), G(s1, y1, porch_zu(s1)), G(s0, y1, porch_zu(s0))], 0)
    w.line(*G(s0, y1, 0), *G(s0, y1, porch_zu(s0)), 13)         # corner where the porch meets the long wall
    w.line(*G(s1, y1, 1), *G(s1, y1, porch_zu(s1)), 14)
    draw_door(w, door, hooks)
    # the lamp beside the door
    w.rect(199, 79, 201, 82, 1)
    w.rect(199, 78, 201, 79, 15)
    w.rect(199, 82, 201, 83, 15)
    # roof of the porch (top, front fascia, side fascia)
    yf, sf = y1 + 2, s1 + OVER
    top = [G(s0, 62, porch_zt(s0)), G(sf, 62, porch_zt(sf)), G(sf, yf, porch_zt(sf)), G(s0, yf, porch_zt(s0))]
    w.fill_poly(top, 3, lambda x, y: 10 if (x + y) % 4 == 0 else None)
    frontf = [G(s0, yf, porch_zt(s0)), G(sf, yf, porch_zt(sf)), G(sf, yf, porch_zt(sf) - 2.5), G(s0, yf, porch_zt(s0) - 2.5)]
    sidef = [G(sf, yf, porch_zt(sf)), G(sf, 62, porch_zt(sf)), G(sf, 62, porch_zt(sf) - 2.5), G(sf, yf, porch_zt(sf) - 2.5)]
    w.fill_poly(frontf, 10)
    w.fill_poly(sidef, 10)
    w.poly_outline(top, 15)
    w.line(*G(s0, yf, porch_zt(s0) - 2.5), *G(sf, yf, porch_zt(sf) - 2.5), 15)
    w.line(*G(sf, yf, porch_zt(sf) - 2.5), *G(sf, 62, porch_zt(sf) - 2.5), 15)
    w.clip = None


# ------------------------------------------------------------------------------------------------ the house, inside (roof and front wall cut away)
def _pattern_planks(x, y):
    s = x + y
    return 10 if (s - 214) % 9 == 0 else None


def _pattern_tiles(x, y):
    s = x + y
    return 12 if (((s - 214) // 7) + ((y - 65) // 7)) % 2 else 0


def _blue(w, s0, s1, y0, y1, z0, z1):
    return w.gbox(s0, s1, y0, y1, z0, z1, 7, 6, 5)


def draw_fridge(w, open_=False):
    x0, y0, x1, y1 = FRIDGE_RECT
    px = w.gbox(284, 299, 73, 77, 0, 26, 12, 0, 13)
    # front face: x 207..221, y 51..76
    if not open_:
        w.rect(208, 59, 221, 60, 13)                              # freezer seam
        w.rect(219, 53, 220, 57, 14)                              # handles
        w.rect(219, 62, 220, 69, 14)
    else:
        w.rect(209, 52, 221, 76, 0)                               # the cavity
        for yy in (58, 65, 72):
            w.rect(210, yy, 221, yy + 1, 12)
        w.rect(208, 51, 209, 77, 15)
        w.rect(207, 51, 208, 77, 12)                              # the door, edge on, at the left
    return px


def draw_chair(w):
    # armchair of 9 x 6 ground px: inside CHAIR_RECT with a margin of one floor pixel all round
    px = w.gbox(241, 250, 189, 195, 0, 8, 7, 6, 5)
    px += w.gbox(241, 250, 189, 191, 0, 22, 7, 6, 5)
    px += w.gbox(241, 243, 189, 195, 0, 13, 7, 6, 5)
    px += w.gbox(248, 250, 189, 195, 0, 13, 7, 6, 5)
    return px


FURNITURE = []        # (name, pixels) of the inside view's furniture, for the passage check (not the armchair, not the fridge)


def _furn(name, px):
    FURNITURE.append((name, px))
    return px


def draw_house_inside(w, hooks=None, fridge_open=False):
    hooks = hooks or {}
    del FURNITURE[:]
    w.clip = MASK
    sl = 214
    # --- floors
    w.fill_poly([G(sl, 120, 0), G(S_R, 120, 0), G(S_R, FAR, 0), G(sl, FAR, 0)], 11, _pattern_planks)
    w.fill_poly([G(sl, 65, 0), G(S_R, 65, 0), G(S_R, 120, 0), G(sl, 120, 0)], 0, _pattern_tiles)
    w.fill_poly([G(S_R - 2, 65, 0), G(P_S1, 65, 0), G(P_S1, 115, 0), G(S_R - 2, 115, 0)], 0, _pattern_tiles)
    w.line(*G(sl, 120, 0), *G(S_R, 120, 0), 13)
    # a rug
    rug = [G(226, 128, 0), G(272, 128, 0), G(272, 166, 0), G(226, 166, 0)]
    w.fill_poly(rug, 3)
    w.fill_poly([G(228, 130, 0), G(270, 130, 0), G(270, 164, 0), G(228, 164, 0)], 3, lambda x, y: 10 if (x + y) % 6 == 0 else None)
    w.poly_outline(rug, 15)
    # a door mat on the porch floor
    w.fill_poly([G(296, 100, 0), G(308, 100, 0), G(308, 113, 0), G(296, 113, 0)], 10)
    # the edge of the floor slab, along the footprint boundary
    for y in range(115, 226):
        w.put(287 - y, y, 13)
    for y in range(65, 115):
        w.put(315 - y, y, 13)
    for x in range(171, 202):
        w.put(x, 114, 13)
    # --- walls: left wall's inner face (shaded), back wall (lit), cut tops
    w.fill_poly([G(sl, 65, 0), G(sl, FAR, 0), G(sl, FAR, WALL_H), G(sl, 65, WALL_H)], 12)
    w.fill_poly([G(sl, 65, 0), G(sl, FAR, 0), G(sl, FAR, 4), G(sl, 65, 4)], 14)
    w.fill_poly([G(sl - 2, 65, WALL_H), G(sl, 65, WALL_H), G(sl, FAR, WALL_H), G(sl - 2, FAR, WALL_H)], 0)
    w.line(*G(sl - 2, 65, WALL_H), *G(sl - 2, FAR, WALL_H), 15)
    w.fill_poly([G(sl, 65, 0), G(S_R, 65, 0), G(S_R, 65, WALL_H), G(sl, 65, WALL_H)], 0)
    w.fill_poly([G(S_R, 65, 0), G(P_S1, 65, 0), G(P_S1, 65, 48), G(S_R, 65, 48)], 0)
    w.fill_poly([G(sl, 65, 0), G(P_S1, 65, 0), G(P_S1, 65, 3), G(sl, 65, 3)], 13)
    w.fill_poly([G(sl - 2, 63, WALL_H), G(S_R, 63, WALL_H), G(S_R, 65, WALL_H), G(sl - 2, 65, WALL_H)], 0)
    w.fill_poly([G(S_R, 63, 48), G(P_S1, 63, 48), G(P_S1, 65, 48), G(S_R, 65, 48)], 0)
    w.line(*G(sl - 2, 63, WALL_H), *G(S_R, 63, WALL_H), 15)
    w.line(*G(S_R, 63, 48), *G(P_S1, 63, 48), 15)
    w.line(*G(P_S1, 63, 48), *G(P_S1, 65, 1), 15)
    # a window in the left wall, a picture, a window in the back wall
    sx = sl
    w.fill_poly([G(sx, 96, 16), G(sx, 120, 16), G(sx, 120, 40), G(sx, 96, 40)], 0)
    w.fill_poly([G(sx, 98, 18), G(sx, 118, 18), G(sx, 118, 38), G(sx, 98, 38)], 7)
    w.line(*G(sx, 108, 18), *G(sx, 108, 38), 0)
    w.poly_outline([G(sx, 96, 16), G(sx, 120, 16), G(sx, 120, 40), G(sx, 96, 40)], 15)
    w.fill_poly([G(sx, 140, 24), G(sx, 152, 24), G(sx, 152, 38), G(sx, 140, 38)], 11)
    w.fill_poly([G(sx, 142, 26), G(sx, 150, 26), G(sx, 150, 36), G(sx, 142, 36)], 8)
    w.poly_outline([G(sx, 140, 24), G(sx, 152, 24), G(sx, 152, 38), G(sx, 140, 38)], 15)
    w.fill_poly([G(258, 65, 22), G(274, 65, 22), G(274, 65, 44), G(258, 65, 44)], 0)
    w.fill_poly([G(260, 65, 24), G(272, 65, 24), G(272, 65, 42), G(260, 65, 42)], 7)
    w.line(*G(266, 65, 24), *G(266, 65, 42), 0)
    w.poly_outline([G(258, 65, 22), G(274, 65, 22), G(274, 65, 44), G(258, 65, 44)], 15)
    # --- furniture, far to near
    # kitchen: wall cabinets, counter with a sink and a cooker, the fridge
    _furn('wall cabinets', w.gbox(232, 256, 66, 70, 28, 42, 11, 10, 10))
    _furn('counter', w.gbox(232, 280, 66, 74, 0, 14, 12, 0, 13))
    w.fill_poly([G(238, 68, 14), G(250, 68, 14), G(250, 73, 14), G(238, 73, 14)], 13)       # sink
    w.poly_outline([G(238, 68, 14), G(250, 68, 14), G(250, 73, 14), G(238, 73, 14)], 15)
    for (bx, by) in ((262, 68), (268, 68), (262, 71), (268, 71)):                          # burners
        w.fill_poly([G(bx, by, 14), G(bx + 3, by, 14), G(bx + 3, by + 2, 14), G(bx, by + 2, 14)], 15)
    draw_fridge(w, fridge_open)
    if hooks.get('fridge'):
        hooks['fridge'](w)
    # living room: bookcase and television at the left wall, the sofa, the armchair
    _furn('bookcase', w.gbox(sl, 222, 84, 100, 0, 30, 10, 10, 11))
    for zz in (8, 16, 24):
        w.line(*G(222, 85, zz), *G(222, 99, zz), 15)
    for (ya, yb, cc) in ((86, 90, 3), (91, 94, 6), (95, 99, 8)):
        w.fill_poly([G(222, ya, 9), G(222, yb, 9), G(222, yb, 15), G(222, ya, 15)], cc)
    _furn('tv stand', w.gbox(sl + 1, 228, 112, 130, 0, 9, 11, 10, 10))                       # television stand
    _furn('tv', w.gbox(sl + 3, 223, 116, 126, 9, 22, 13, 14, 14))
    w.fill_poly([G(223, 117, 11), G(223, 125, 11), G(223, 125, 20), G(223, 117, 20)], 7)
    w.line(*G(223, 118, 18), *G(223, 121, 15), 0)
    _furn('sofa', _blue(w, sl + 1, 226, 140, 176, 0, 9))                  # sofa: seat, back, arms
    _furn('sofa', _blue(w, sl + 1, sl + 5, 140, 176, 9, 22))
    _furn('sofa', _blue(w, sl + 1, 226, 140, 144, 9, 15))
    _furn('sofa', _blue(w, sl + 1, 226, 172, 176, 9, 15))
    draw_chair(w)
    if hooks.get('chair'):
        hooks['chair'](w)
    w.clip = None


# ------------------------------------------------------------------------------------------------ assembling
def seal(w):
    """Nothing of the lawn may peek out of the house: any lawn pixel that the house hides is painted over with its left neighbour."""
    n = 0
    for y in range(65, 226):
        for x in range(max(-2, 232 - y), 569 - y):
            if x > 511:
                break
            if house_covers(x, y) and w.get(x, y) in (8, 9):
                w.a[y, x + OX] = w.a[y, x + OX - 1] if x + OX - 1 >= 0 and w.a[y, x + OX - 1] not in (8, 9) else 13
                n += 1
    return n


def frame(w):
    w.a[0, :] = 15
    w.a[1, 1:WORLD_W - 1] = 13
    w.a[:, 0] = 15
    w.a[:, WORLD_W - 1] = 15


def render_world(view='outside', door=0.0, hooks=None, fridge_open=False):
    """view 'outside' (picture 7000) or 'inside' (picture 7001); 7003 is the same in both."""
    w = World()
    draw_scenery(w)
    if view == 'outside':
        draw_house_outside(w, door, hooks)
    else:
        draw_house_inside(w, hooks, fridge_open)
    seal(w)
    frame(w)
    return w


def pictures(w):
    """(left picture 281 x 226, right picture 233 x 226) as numpy arrays."""
    return w.a[:, :W7000].copy(), w.a[:, W7000:].copy()


def strips():
    """7020 (513 x 51), 7021 (512 x 55), 7022 (512 x 55): the lattice over colour 13, with the house's footprint line (colour 10)."""
    full = np.full((161, 514), 13, dtype=np.int16)          # yard y 65..225, columns x = -1 .. 512
    for y in range(65, 226):
        for x in range(232 - y, 569 - y):
            c = lattice(x, y)
            if c is not None:
                full[y - 65, x + 1] = c
    marks = [(315 - y, y) for y in range(66, 114)] + [(x, 114) for x in range(173, 202)] + [(287 - y, y) for y in range(115, 225)]
    for (x, y) in marks:
        full[y - 65, x + 1] = 10
    s0 = full[0:51, 0:513].copy()
    s1 = full[51:106, 0:512].copy()
    s2 = full[106:161, 0:512].copy()
    return s0, s1, s2


def sign_board():
    """1260: the for-sale sign, 54 x 37, masked (T = transparent)."""
    img = Img(54, 37, T)
    BH = 25                                                   # board height
    for y in range(BH):
        for x in range(54):
            img.a[y, x] = 0
    img.frame(0, 0, 54, BH, 15)
    img.rect(1, BH - 2, 53, BH - 1, 12)                       # a pale lower edge
    img.rect(53 - 1, 1, 53, BH - 1, 12)
    for x in (0, 53):                                         # cut corners
        for y in (0, BH - 1):
            img.a[y, x] = T
    text_c(img, 27, 3, 'FOR SALE', LABEL_TALL, 15)
    img.rect(6, 13, 48, 14, 12)
    text_c(img, 27, 15, 'CHEAP', SMALL, 3)
    img.rect(25, BH, 29, 36, 15)                              # the post: 4 px wide, outline 1 px, wood 2 px
    img.rect(26, BH, 28, 36, 10)
    img.rect(25, 36, 29, 37, 15)
    img.rect(26, BH, 27, 36, 11)
    return img
