"""yard_pass3: pass 3 of the yard spec (docs/clean_pack/yard_bitmaps.md): the person and the yard mower (group E: 8000..8011,
8020..8023, 8100..8111, 8800..8802) and the door / room patches that show him (group B: 8900..8903, 8905, 8200, 8201).

* The figure and the mower are drawn by `yard_fig.py` (one model, parts and poses).  A frame's sprite size is fixed by the spec's
  table, so each frame's pose parameters (stride, arm swing, body drop, ...) are FITTED once: `python yard_pass3.py --fit` searches
  the pose space for the nearest pose to a natural one whose tight picture has exactly the table's size and passes the alignment
  rule (spec "Alignment"), and writes the result to `yard_fit3.py` (`FIT`).  The normal build reads `FIT` and asserts everything.
* Heading 3 (walking, mowing, the narrow standing view) is the pixel mirror of heading 1 (frames in reverse order); the mower of
  heading 3 (8802) is the mirror of 8801.
* The patches are cropped from renders of `yard_scene.render_world` with the figure drawn in through its hooks, never painted separately.
"""
import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import yard_fig as yf  # noqa: E402
import yard_scene as ys  # noqa: E402
from uilib import Img, T  # noqa: E402
from yardlib import OX  # noqa: E402

# ------------------------------------------------------------------------------------------------------------ the tables
# bid: (w, h, dx, dy)
SIZES = {
    8000: (12, 30, 3, 2), 8001: (15, 30, 3, 0), 8002: (17, 30, 1, 2),
    8003: (18, 29, 0, 3), 8004: (10, 30, 3, 2), 8005: (17, 28, 0, 3),
    8006: (19, 30, 1, 2), 8007: (14, 30, 4, 0), 8008: (14, 29, 4, 2),
    8009: (17, 28, 3, 3), 8010: (10, 30, 7, 2), 8011: (18, 29, 2, 3),
    8020: (13, 30, 4, 0), 8021: (7, 29, 5, 2), 8022: (13, 31, 4, 0), 8023: (7, 29, 6, 2),
    8100: (19, 29, 0, 1), 8101: (16, 28, 3, 0), 8102: (17, 29, 2, 1),
    8103: (18, 28, 1, 1), 8104: (14, 28, 5, 0), 8105: (19, 28, 0, 1),
    8106: (22, 32, 0, 1), 8107: (19, 33, 0, 0), 8108: (21, 32, 0, 1),
    8109: (19, 28, 0, 1), 8110: (14, 28, 0, 0), 8111: (18, 28, 0, 1),
    8800: (14, 15, 0, 0), 8801: (15, 14, 0, 0), 8802: (15, 14, 0, 0),
}
MIRROR = {8009: 8005, 8010: 8004, 8011: 8003, 8023: 8021, 8109: 8105, 8110: 8104, 8111: 8103}   # heading 3 <- heading 1
FRAMES_E = [b for b in sorted(SIZES) if b < 8800]
SETS = [
    ('walk heading 0', (8000, 8001, 8002)), ('walk heading 1', (8003, 8004, 8005)), ('walk heading 2', (8006, 8007, 8008)),
    ('walk heading 3', (8009, 8010, 8011)), ('standing', (8020, 8021, 8022, 8023)),
    ('mowing heading 0', (8100, 8101, 8102)), ('mowing heading 1', (8103, 8104, 8105)),
    ('mowing heading 2', (8106, 8107, 8108)), ('mowing heading 3', (8109, 8110, 8111)),
]
# the leg that is forward in each frame of a walking / mowing set (+1 / 0 passing / -1)
PHASE = {8000: 1, 8001: 0, 8002: -1, 8003: 1, 8004: 0, 8005: -1, 8006: 1, 8007: 0, 8008: -1,
         8100: 1, 8101: 0, 8102: -1, 8103: 1, 8104: 0, 8105: -1, 8106: 1, 8107: 0, 8108: -1}
VIEW = {}
for b in range(8000, 8003): VIEW[b] = 'B'
for b in range(8003, 8006): VIEW[b] = 'P'
for b in range(8006, 8009): VIEW[b] = 'F'
VIEW.update({8020: 'B', 8021: 'P', 8022: 'F'})
for b in range(8100, 8103): VIEW[b] = 'B'
for b in range(8103, 8106): VIEW[b] = 'P'
for b in range(8106, 8109): VIEW[b] = 'F'
KIND = {b: ('walk' if b < 8020 else 'stand' if b < 8100 else 'mow') for b in FRAMES_E}


# ------------------------------------------------------------------------------------------------------------ the pose search
def centroid(a):
    ys_, xs_ = np.nonzero(a != T)
    return float(xs_.mean()), float(ys_.mean())


def r_ok(a, dx, dy):
    """The spec's alignment rule on one frame: R = centroid (mean of the pixel indices) + offset in x 6..12, y 13..18; the same with
    the pixel-centre convention (+0.5) must lie within 0.5 of that box."""
    cx, cy = centroid(a)
    rx, ry = cx + dx, cy + dy
    if not (6.0 <= rx <= 12.0 and 13.0 <= ry <= 18.0):
        return False
    rx, ry = rx + 0.5, ry + 0.5
    return 5.5 <= rx <= 12.5 and 12.5 <= ry <= 18.5


def r_cost(a, dx, dy):
    cx, cy = centroid(a)
    return abs(cx + 0.25 + dx - 9.0) + abs(cy + 0.25 + dy - 15.5)


def mirror_arr(a):
    return a[:, ::-1].copy()


def space(bid):
    """(nominal pose, {param: range}, weights) for the frame's search."""
    kind, view, ph = KIND[bid], VIEW[bid], PHASE.get(bid, 0)
    if kind == 'walk':
        if view == 'P':
            nom = dict(L=9 if ph else 1, sw=5 if ph else 2, bob=1 if ph else 0, lift=1, lean=0)
            rng = dict(L=range(0, 13), sw=range(0, 8), bob=range(0, 4), lift=range(0, 3), lean=range(0, 2))
        else:
            nom = dict(L=8 if ph else 1, sw=4 if ph else 2, out=1, bob=2 if ph else 0, outr=0)
            rng = dict(L=range(0, 15), sw=range(0, 8), out=range(-1, 4), bob=range(0, 5), outr=range(-1, 3))
        w = dict(L=0.5, sw=0.5, out=0.6, bob=0.5, lift=0.3, lean=0.6, outr=0.5)
    elif kind == 'stand':
        if view == 'P':
            nom = dict(L=0, bob=0, lean=0)
            rng = dict(L=range(0, 3), bob=range(0, 3), lean=range(0, 2))
        else:
            nom = dict(L=0, sw=0, out=1, bob=0, outr=0)
            rng = dict(L=range(0, 4), sw=range(0, 3), out=range(-1, 4), bob=range(-2, 3), outr=range(-1, 3))
        w = dict(L=0.5, sw=0.5, out=0.6, bob=0.5, lift=0.3, lean=0.6, outr=0.5)
    else:
        if view == 'P':
            nom = dict(L=5 if ph else 1, bob=1 if ph else 0, lean=2, lift=1, hx=11)
            rng = dict(L=range(0, 9), bob=range(0, 4), lean=range(0, 4), lift=range(0, 3), hx=range(7, 15))
        elif view == 'B':
            nom = dict(L=4 if ph else 1, bob=1 if ph else 0, mx=6, my=-4, lift=1, lean=0)
            rng = dict(L=range(0, 9), bob=range(0, 4), mx=range(3, 13), my=range(-9, 0), lift=range(1, 3), lean=range(0, 2))
        else:
            nom = dict(L=4 if ph else 1, bob=1 if ph else 0, mx=-5, my=3, lift=1, lean=0)
            rng = dict(L=range(0, 9), bob=range(0, 4), mx=range(-13, -2), my=range(0, 8), lift=range(1, 3), lean=range(0, 4))
        w = dict(L=0.5, bob=0.5, md=0.3, lift=0.3, lean=0.5, hx=0.2, mx=0.3, my=0.3)
    return nom, rng, w


def pose(bid, prm):
    """The figure() parameters of a frame from its fitted free parameters."""
    kind, view, ph = KIND[bid], VIEW[bid], PHASE.get(bid, 0)
    p = dict(view=view, ph=ph)
    if kind != 'mow' and view != 'P':
        p['lift'] = 1 if (ph == 0 or prm.get('L', 0) >= 3) else 0
    p.update(prm)
    if kind == 'mow':
        w, h, dx, dy = SIZES[bid]
        if view == 'P':
            p['arms'] = 'reach'
            p['hand'] = (prm['hx'] - 0.5, 19.0 - dy - (h - 1) - 0.0)
            del p['hx']
        else:
            p['mower'] = view
    return p


def render(bid, prm):
    im, anchor = yf.figure(pose(bid, prm))
    return im, anchor


def extra_ok(bid, im):
    """Mowing, heading 1: the hands are at the picture's right edge, in its bottom half."""
    if KIND[bid] == 'mow' and VIEW[bid] == 'P':
        a = im.a
        h, w = a.shape
        cols = a[:, w - 3:]
        ys_, xs_ = np.nonzero(cols == yf.SKIN)
        return len(ys_) > 0 and (ys_ >= h // 2).all()
    return True


def fit_frame(bid):
    src = MIRROR.get(bid, bid)
    w, h, dx, dy = SIZES[src]
    mw, mh, mdx, mdy = SIZES[[k for k, v in MIRROR.items() if v == src][0]] if src in MIRROR.values() else (None,) * 4
    nom, rng, wt = space(src)
    keys = sorted(rng)
    best = None
    for vals in itertools.product(*[rng[k] for k in keys]):
        prm = dict(zip(keys, vals))
        im, _ = render(src, prm)
        if (im.w, im.h) != (w, h):
            continue
        if not r_ok(im.a, dx, dy) or not extra_ok(src, im):
            continue
        cost = r_cost(im.a, dx, dy)
        if mw is not None:
            if not r_ok(mirror_arr(im.a), mdx, mdy):
                continue
            cost += r_cost(mirror_arr(im.a), mdx, mdy)
        cost += sum(wt[k] * abs(prm[k] - nom[k]) for k in keys)
        if best is None or cost < best[0]:
            best = (cost, prm)
    return best


def fit_all(only=None):
    fit = {}
    try:
        import yard_fit3
        fit.update(yard_fit3.FIT)
    except ImportError:
        pass
    for bid in FRAMES_E:
        if bid in MIRROR or (only and bid not in only):
            continue
        r = fit_frame(bid)
        print(bid, 'FIT' if r else 'NO FIT', r, flush=True)
        if r is None:
            fit.pop(bid, None)
            continue
        fit[bid] = r[1]
    with open(os.path.join(HERE, 'yard_fit3.py'), 'w', newline='\n') as f:
        f.write('"""yard_fit3: the fitted pose parameters of the person frames (written by  python yard_pass3.py --fit [ids])."""' + '\n')
        f.write('FIT = {' + '\n')
        for bid in sorted(fit):
            f.write('    %d: %r,' % (bid, fit[bid]) + '\n')
        f.write('}' + '\n')
    return fit


# ------------------------------------------------------------------------------------------------------------ the sprites
def fit_table():
    import yard_fit3
    return yard_fit3.FIT


def frame_img(bid, fit=None):
    """The sprite of one frame of group E (heading 3 = the pixel mirror of heading 1)."""
    fit = fit or fit_table()
    if bid in MIRROR:
        src = frame_img(MIRROR[bid], fit)
        o = Img(src.w, src.h, T)
        o.a = mirror_arr(src.a)
        return o
    im, _ = render(bid, fit[bid])
    return im


def mower_imgs():
    cv = yf.mower_P_pic(-8, -14)
    m801, _ = yf.finish(cv)
    m802 = Img(m801.w, m801.h, T)
    m802.a = mirror_arr(m801.a)
    cv = yf.Cv()
    yf.mower_F(cv, -7, -15)
    m800, _ = yf.finish(cv)
    return {8800: m800, 8801: m801, 8802: m802}


def arr_img(a):
    o = Img(a.shape[1], a.shape[0])
    o.a = np.array(a, dtype=np.int16)
    return o


# ------------------------------------------------------------------------------------------------------------ the patches (group B)
class Pasted:
    def __init__(self):
        self.boxes = []

    def hook(self, img, cx, bottom):
        """A scene hook drawing `img` (a sprite) centred on world column cx with its bottom row on `bottom` (yard coordinates)."""
        left, top = cx - img.w // 2, bottom - img.h + 1
        self.boxes.append((left, top, left + img.w, bottom + 1))

        def fn(w):
            for iy in range(img.h):
                for ix in range(img.w):
                    v = int(img.a[iy, ix])
                    if v != T:
                        w.put(left + ix, top + iy, v)
        return fn


DOOR_STATES = {      # bid: (door opening, hook, person frame (fit key), pose overrides, centre x, bottom row)
    8900: (0.3, 'behind', 8022, {}, 189, 107),                       # just opening / closing: the person stands behind the leaf
    8901: (1.0, 'behind', 8008, {'bob': 1}, 186, 109),               # wide open, starting to step out (leaning forward)
    8902: (1.0, 'front', 8007, {}, 187, 113),                        # in the doorway, almost out: on the step
    8903: (1.0, 'front', 8020, {}, 187, 112),                        # on the threshold, back to us, about to go in
}
# the encoder (tools/clean_pack/build.py) wants 8902 to be 24 x 43, not 26 x 42 as the spec's table says: it is cropped from the same
# render at yard (174,73)-(198,116) (the build is authoritative; see README)
PATCH_RECT = {8900: ys.DOOR_RECT, 8901: ys.DOOR_RECT, 8902: (174, 73, 198, 116), 8903: ys.DOOR_RECT}
DOOR_INNER = (174, 75, 196, 114)       # the opening and its step (yard coordinates, x1 / y1 exclusive): the person never leaves it


def person_for(key, over, fit):
    p = pose(key, dict(fit[key], **over))
    im, _ = yf.figure(p)
    return im


def door_patches(fit, closed_outside):
    out, boxes, refs = {}, {}, {}
    for bid, (f, hk, key, over, cx, bottom) in DOOR_STATES.items():
        x0, y0, x1, y1 = PATCH_RECT[bid]
        ps = Pasted()
        w = ys.render_world('outside', door=f, hooks={hk: ps.hook(person_for(key, over, fit), cx, bottom)})
        crop = w.pic(x0, x1)[y0:y1].copy()
        base = closed_outside.pic(x0, x1)[y0:y1]
        if bid == 8902:       # the open leaf's corner lines touch 2 pixels of the ring of this (24 x 43) rectangle: restore the ring from 7000
            crop[0, :], crop[-1, :], crop[:, 0], crop[:, -1] = base[0, :], base[-1, :], base[:, 0], base[:, -1]
        out[bid] = crop
        boxes[bid] = ps.boxes[0]
        refs[bid] = ys.render_world('outside', door=f).pic(x0, x1)[y0:y1]
    return out, boxes, refs


def chair_patch():
    img, _ = yf.figure(dict(view='F', sit=True))
    ps = Pasted()
    w = ys.render_world('inside', hooks={'chair': ps.hook(img, 46 + img.w // 2, 194)})
    x0, y0, x1, y1 = ys.CHAIR_RECT
    return w.pic(x0, x1)[y0:y1], ps.boxes[0]


def fridge_patch(closed_inside):
    img, _ = yf.figure(dict(view='P', ph=0, L=1, bob=2, lean=2, lift=0, arms='reach', hand=(8.5, -14.0)))
    ps = Pasted()
    w = ys.render_world('inside', fridge_open=True, hooks={'fridge': ps.hook(img, 208 + img.w // 2, 75)})
    x0, y0, x1, y1 = ys.FRIDGE_RECT
    crop = w.pic(x0, x1)[y0:y1].copy()
    ref_open = ys.render_world('inside', fridge_open=True).pic(x0, x1)[y0:y1]
    closed = closed_inside.pic(x0, x1)[y0:y1]
    # the open door's edge-on leaf sits on the box's outermost column and the picture's ring must equal 7001's: restore the ring
    # (one pixel all round; the person never reaches it)
    crop[0, :] = closed[0, :]
    crop[-1, :] = closed[-1, :]
    crop[:, 0] = closed[:, 0]
    crop[:, -1] = closed[:, -1]
    return crop, ps.boxes[0], ref_open


# ------------------------------------------------------------------------------------------------------------ build and checks
def build(reg):
    fit = fit_table()
    for bid in FRAMES_E:
        im = frame_img(bid, fit)
        w, h, dx, dy = SIZES[bid]
        reg.add(bid, im, (w, h), True, None, 'the person (red jacket, charcoal trousers, white sneakers), %s' % (
            'walking' if KIND[bid] == 'walk' else 'standing' if KIND[bid] == 'stand' else 'mowing'))
    for bid, im in mower_imgs().items():
        reg.add(bid, im, SIZES[bid][:2], True, None, 'push mower (red deck, orange rim, dark engine cover, grey bag), %s' % (
            'parked' if bid == 8800 else 'pushed right' if bid == 8801 else 'pushed left'))
    door, boxes, refs = door_patches(fit, reg.worlds['outside'])
    for bid in sorted(door):
        reg.add(bid, arr_img(door[bid]), (door[bid].shape[1], door[bid].shape[0]), False, None, 'door patch: the person at the porch door (state %d)' % (bid - 8900))
    reg.add(8905, Img(19, 35, 15), (19, 35), False, (15,), 'spare: solid black')
    chair, cbox = chair_patch()
    reg.add(8200, arr_img(chair), (17, 30), False, None, 'the person sitting in the armchair')
    fridge, fbox, fref = fridge_patch(reg.worlds['inside'])
    reg.add(8201, arr_img(fridge), (19, 30), False, None, 'the person at the open refrigerator')
    reg.p3 = dict(door_refs=refs, door_boxes=boxes, chair_box=cbox, fridge_box=fbox, fridge_ref=fref)
    reg.check(check_pass3)


def ring(a):
    return np.concatenate([a[0], a[-1], a[1:-1, 0], a[1:-1, -1]])


def tight(a):
    m = a != T
    return m[0].any() and m[-1].any() and m[:, 0].any() and m[:, -1].any()


def check_pass3(reg):
    P = reg.p3
    A = {b: reg.img[b].a for b in reg.img}
    # --- E: tight, colours, alignment, spreads
    stats = {}
    for bid in FRAMES_E + [8800, 8801, 8802]:
        a = A[bid]
        assert (a == T).any() and tight(a), ('tight', bid)
        assert (a == 1).sum() == 0, ('colour 1 is the dog collar only', bid)
    for bid in FRAMES_E:
        w, h, dx, dy = SIZES[bid]
        assert A[bid].shape == (h, w), bid
        cx, cy = centroid(A[bid])
        rx, ry = cx + dx, cy + dy
        assert abs(rx - 9.0) <= 3.0 and abs(ry - 15.5) <= 2.5, ('alignment R', bid, rx, ry)
        stats[bid] = (rx, ry)
    for name, ids in SETS:
        xs = [stats[b][0] for b in ids]
        yy = [stats[b][1] for b in ids]
        assert max(xs) - min(xs) <= 3.0 and max(yy) - min(yy) <= 3.0, ('set spread', name, xs, yy)
    # heading 3 = mirrors of heading 1
    for b3, b1 in MIRROR.items():
        assert (A[b3] == A[b1][:, ::-1]).all(), (b3, b1)
    # the mowing rule: widths + dx, hands at the edge, the mower's touching edge and bottom
    for bid in (8103, 8104, 8105):
        w, h, dx, dy = SIZES[bid]
        assert w + dx == 19, bid
        a = A[bid]
        sk = np.argwhere(a[:, w - 3:] == yf.SKIN)
        assert len(sk) and (sk[:, 0] >= h // 2).all(), ('hands at the right edge, bottom half', bid)
        rows_abs = sk[:, 0] + dy
        assert ((rows_abs >= 17) & (rows_abs <= 21)).all(), ('hands on the handle rows', bid, rows_abs)
        assert abs((h - 1 + dy) - (15 + 14 - 1)) <= 1, ('mower bottom within 1 px of the persons bottom', bid)
        assert (a[:, w - 1] != T).any()
    for bid in (8109, 8110, 8111):
        w, h, dx, dy = SIZES[bid]
        assert dx == 0, bid
        assert abs((h - 1 + dy) - 28) <= 1, bid
    m801, m802 = A[8801], A[8802]
    assert (m801 != T)[:, 0].any() and (m802 != T)[:, -1].any()
    assert (m801[:, ::-1] == m802).all()
    hand_rows = np.where(m801[:6, 0] != T)[0] + 15
    assert len(hand_rows) >= 1
    assert ((hand_rows >= 17) & (hand_rows <= 21)).all(), ('8801 handle at the hands rows', hand_rows)
    # one machine: the mower colours
    mc = {15, 3, 2, 10, 14, 13, 12}
    for bid in (8800, 8801, 8802):
        assert set(np.unique(A[bid]).tolist()) - {T} <= mc, ('mower palette', bid)
        assert 3 in A[bid] and 2 in A[bid] and 14 in A[bid]
    for bid in (8100, 8101, 8102, 8106, 8107, 8108):
        assert (A[bid] == 2).any() and (A[bid] == 12).any(), ('baked mower colours', bid)
    # sneakers: white upper, red cap, dark sole
    for bid in (8003, 8020, 8022):
        assert (A[bid] == 0).any() and (A[bid] == 14).any(), bid
    # --- B
    base_in = reg.img[7001].a
    assert (A[8905] == 15).all() and A[8905].shape == (35, 19)
    for bid in (8900, 8901, 8902, 8903):
        a = A[bid]
        x0, y0, x1, y1 = PATCH_RECT[bid]
        assert a.shape == (y1 - y0, x1 - x0)
        assert (ring(a) == ring(reg.img[7000].a[y0:y1, x0 + OX:x1 + OX])).all(), ('door patch ring', bid)
        diff = int((a != P['door_refs'][bid]).sum())
        assert diff >= (6 if bid == 8900 else 60), ('the person is visible in', bid, diff)
        l, t, r, b = P['door_boxes'][bid]
        assert l >= DOOR_INNER[0] and t >= DOOR_INNER[1] and r <= DOOR_INNER[2] and b <= DOOR_INNER[3], ('person inside the opening', bid, (l, t, r, b))
    d900 = int((A[8900] != P['door_refs'][8900]).sum())
    assert d900 < 0.5 * int((A[8903] != P['door_refs'][8903]).sum()), 'mostly hidden in 8900'
    cx0, cy0, cx1, cy1 = ys.CHAIR_RECT
    r7001 = base_in[cy0:cy1, cx0 + OX:cx1 + OX]
    assert (ring(A[8200]) == ring(r7001)).all(), 'chair patch ring'
    assert int((A[8200] != r7001).sum()) >= 80
    l, t, r, b = P['chair_box']
    assert l > cx0 and t > cy0 and r < cx1 and b < cy1, ('seated person inside the ring', P['chair_box'])
    fx0, fy0, fx1, fy1 = ys.FRIDGE_RECT
    f7001 = base_in[fy0:fy1, fx0 + OX:fx1 + OX]
    assert (ring(A[8201]) == ring(f7001)).all(), 'fridge patch ring'
    assert int((A[8201] != P['fridge_ref']).sum()) >= 80, 'the person at the fridge is visible'
    l, t, r, b = P['fridge_box']
    assert l > fx0 and t > fy0 and r < fx1 and b < fy1, ('person at the fridge inside the ring', P['fridge_box'])
    reg.stats = getattr(reg, 'stats', {})
    reg.stats['p3_R'] = stats


def runner():
    """Passes 1-3 only (so this pass can be tested while the others are being written)."""
    from uilib import Reg, run_generic_checks
    import yard_pass1
    import yard_pass2
    reg = Reg()
    for mod in (yard_pass1, yard_pass2, sys.modules[__name__]):
        mod.build(reg)
    run_generic_checks(reg)
    return reg


if __name__ == '__main__':
    if '--fit' in sys.argv:
        fit_all([int(x) for x in sys.argv[1:] if x.isdigit()] or None)
    else:
        r = runner()
        print('passes 1-3 alone: all checks passed;', len([b for b in r.img if 8000 <= b < 9000]), 'pictures in 8000..8999')
