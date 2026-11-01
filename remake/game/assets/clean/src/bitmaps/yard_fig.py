"""yard_fig: the figure model of the yard's person and the push mower (spec yard_bitmaps.md, groups E and B, pass 3).

ONE person (red jacket, charcoal trousers, white sneakers, brown hair, tan skin; about 30 px tall with its outline) drawn from
parts (head, jacket, two arms, two legs, two shoes) in three views:

    'P'  profile facing RIGHT (headings 1 / 3 and the narrow standing views; heading 3 is the pixel mirror)
    'B'  three-quarter back, travelling up-right   (heading 0)
    'F'  three-quarter front, travelling down-left (heading 2)

and ONE push mower (orange deck, dark engine cover, grey grass bag, black wheels and handle) in the views profile (8801 / 8802),
front (8800 and the baked mower of heading 2) and back (the baked mower of heading 0).

Every part is painted with its own 1-px outline (black 15; dark red 10 where an arm lies over the jacket), back to front.
`figure(p)` returns (Img, (gx, gy)): the tight sprite and its ground point (the point between the feet, bottom row of the
shoes = gy) inside it.  Parameters of a pose:

    view   'P' | 'B' | 'F'
    L      stride (px between the feet along the travel direction); ph = +1 / 0 / -1 which leg is forward (0 = passing)
    sw     arm swing (px of the hand along the travel direction, opposite to the leg on the same side)
    out    the hands' distance outwards (B / F; may be negative)
    bob    the body's drop (px): the hips and everything above sit this much lower
    lift   the back foot's lift (px)
    lean   the shoulders' forward shift (P: px right)
    arms   'swing' (default) | 'reach' (hands at `hand`, a point relative to the ground point)
    mower  None | 'B' | 'F': a mower in front of the person in the direction of travel at distance `md`
    sit    True: sitting (chair)
"""
import numpy as np

from uilib import T, Img

CW = CH = 80
OXc, GYc = 40, 60              # canvas position of the figure's axis (x) and of the ground line (y)

OUT = 15
SKIN, HAIR, HAIR_HI = 11, 10, 11
JACKET, JACKET_SH = 3, 10
PANTS, PANTS_HI = 14, 13
SHOE, SOLE, CAP = 0, 14, 3            # white sneaker, dark grey sole, red toe cap and heel tab, black laces (as 1200..1203)
DECK, RIM, DECK_SH, COVER, COVER_HI, BAG, BAG_SH, WHEEL, HUB = 3, 2, 10, 14, 13, 12, 13, 15, 13     # red deck, orange rim (as 1210 / 1211)

_Y, _X = np.mgrid[0:CH, 0:CW]
CXc = _X + 0.5
CYc = _Y + 0.5


# ----------------------------------------------------------------------------------------------- masks (local coordinates)
def m_ell(cx, cy, rx, ry):
    return ((CXc - (OXc + cx)) / rx) ** 2 + ((CYc - (GYc + cy)) / ry) ** 2 <= 1.0


def m_rect(x0, y0, x1, y1):
    return (CXc >= OXc + x0) & (CXc < OXc + x1) & (CYc >= GYc + y0) & (CYc < GYc + y1)


def m_seg(x0, y0, x1, y1, r):
    x0, y0, x1, y1 = OXc + x0, GYc + y0, OXc + x1, GYc + y1
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    t = np.zeros_like(CXc) if l2 == 0 else np.clip(((CXc - x0) * dx + (CYc - y0) * dy) / l2, 0, 1)
    return (CXc - (x0 + t * dx)) ** 2 + (CYc - (y0 + t * dy)) ** 2 <= r * r


def m_poly(pts):
    pts = [(OXc + x, GYc + y) for x, y in pts]
    inside = np.zeros((CH, CW), dtype=bool)
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        if ya == yb:
            continue
        cond = ((ya <= CYc) & (yb > CYc)) | ((yb <= CYc) & (ya > CYc))
        xint = xa + (CYc - ya) * (xb - xa) / (yb - ya)
        inside ^= cond & (CXc < xint)
    return inside


def _nb(m, dx, dy):
    """out[y, x] = m[y + dy, x + dx] (False outside)."""
    o = np.zeros_like(m)
    ys0, ys1 = max(0, -dy), min(CH, CH - dy)
    xs0, xs1 = max(0, -dx), min(CW, CW - dx)
    o[ys0:ys1, xs0:xs1] = m[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    return o


def _dil(m):
    return m | _nb(m, 1, 0) | _nb(m, -1, 0) | _nb(m, 0, 1) | _nb(m, 0, -1)


# ----------------------------------------------------------------------------------------------- canvas
class Cv:
    def __init__(self):
        self.a = np.full((CH, CW), T, dtype=np.int16)

    def paint(self, m, fill, edge=OUT, edge_in=None, sh=None, hi=None):
        if not m.any():
            return
        if edge is not None:
            ring = _dil(m) & ~m
            occ = self.a != T
            if edge_in is None:
                self.a[ring] = edge
            else:
                self.a[ring & occ] = edge_in
                self.a[ring & ~occ] = edge
        self.a[m] = fill
        if sh is not None or hi is not None:
            right_bottom = m & ~(_nb(m, 1, 0) & _nb(m, 0, 1))
            left_top = m & ~right_bottom & ~(_nb(m, -1, 0) & _nb(m, 0, -1))
            if m.sum() >= 14 and right_bottom.sum() < 0.6 * m.sum():
                if sh is not None:
                    self.a[right_bottom] = sh
                if hi is not None:
                    self.a[left_top] = hi

    def dot(self, i, j, c):
        """Local pixel (column i, row j) of the figure's frame of reference."""
        x, y = int(OXc + i), int(GYc + j)
        if 0 <= x < CW and 0 <= y < CH:
            self.a[y, x] = c

    def line(self, x0, y0, x1, y1, c):
        """Bresenham in canvas pixel coordinates."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.a[y0, x0] = c
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy


def finish(cv, anchor=(0, 0)):
    """Tight sprite and the position of the local point `anchor` (default the ground point) inside it."""
    ys, xs = np.where(cv.a != T)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    o = Img(int(x1 - x0), int(y1 - y0), T)
    o.a = cv.a[y0:y1, x0:x1].copy()
    return o, (int(OXc + anchor[0] - x0), int(GYc + anchor[1] - y0))


# ----------------------------------------------------------------------------------------------- the pieces of the person
def head(cv, cx, cy, view, rx=3.3, ry=4.0):
    m = m_ell(cx, cy, rx, ry)
    cv.paint(m, SKIN)
    X, Y = CXc - (OXc + cx), CYc - (GYc + cy)
    if view == 'B':
        hair = m
    elif view == 'F':
        hair = m & ((Y < -1.0) | (np.abs(X) > rx - 0.7))
    else:
        hair = m & ((Y < -1.2) | (X < 0.0))
    cv.a[hair] = HAIR
    ys, xs = np.where(hair & ~_nb(hair, 0, -1))        # the topmost row of the hair: a lit pixel or two on the left
    if len(xs):
        order = np.argsort(xs)
        for k in order[:2]:
            cv.a[ys[k], xs[k]] = HAIR_HI
    ci, cj = int(np.floor(cx)), int(np.floor(cy))
    if view == 'F':
        cv.dot(ci - 2, cj, OUT)
        cv.dot(ci + 1, cj, OUT)
    elif view == 'P':
        cv.dot(ci + 1, cj, OUT)


def shoe(cv, ax, ay, view, lifted=0):
    """Sneaker with the ankle at (ax, ay): P: 4 x 2, toe to the right; B / F: 3 x 2.  White upper, red toe cap and heel tab,
    black laces, dark grey sole (the colours of the Map window's sneaker 1200..1203)."""
    if view == 'P':
        m = m_rect(ax - 1.5, ay, ax + 2.5, ay + 2)
    else:
        m = m_rect(ax - 1.5, ay, ax + 1.5, ay + 2)
    cv.paint(m, SHOE)
    ys, xs = np.where(m)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    cv.a[y1, x0:x1 + 1] = SOLE
    if view == 'P':
        cv.a[y0, x1] = CAP
        cv.a[y0, x0] = CAP
        cv.a[y0, x0 + 2] = OUT
    else:                                    # from the front: the toe cap; from behind: the heel tab
        cv.a[y0, x0 + 1] = CAP


def leg(cv, hx, hy, ax, ay, view, shade=False):
    """A leg from the hip (hx, hy) to the ankle (ax, ay): charcoal, 3 px wide (2 in profile)."""
    m = m_seg(hx, hy, ax, ay, 1.1 if view == 'P' else 1.5)
    cv.paint(m, PANTS, hi=None if shade else PANTS_HI, sh=None)
    shoe(cv, ax, ay, view)


def arm(cv, sx, sy, hx, hy, view, far=False, r=1.0):
    m = m_seg(sx, sy, hx, hy, r)
    cv.paint(m, JACKET_SH if far else JACKET, edge_in=JACKET_SH if not far else OUT)
    hm = m_ell(hx, hy + 0.3, 1.25, 1.25)
    cv.paint(hm, SKIN, edge_in=OUT)


# ----------------------------------------------------------------------------------------------- the person
def figure(p):
    view = p['view']
    cv = Cv()
    L, ph, sw, out = p.get('L', 0.0), p.get('ph', 0), p.get('sw', 0.0), p.get('out', 0.0)
    p.setdefault('outr', 0)
    bob, lift, lean = p.get('bob', 0), p.get('lift', 0), p.get('lean', 0.0)
    hipy, shy, hdy = -10.0 + bob, -20.0 + bob, -24.0 + bob
    mower = p.get('mower')
    md = p.get('md', 12)
    if p.get('sit'):
        _fig_sit(cv)
    elif view == 'P':
        _fig_P(cv, p, L, ph, sw, bob, lift, lean, hipy, shy, hdy)
    else:
        _fig_FB(cv, p, view, L, ph, sw, out, bob, lift, lean, hipy, shy, hdy, mower, md)
    return finish(cv)


def _fig_sit(cv):
    """Sitting, seen from the front (the armchair): lap and shins foreshortened, hands on the chair's arms; 28 rows high."""
    shy, hipy, hdy = -18.0, -10.0, -22.0
    for side in (-1, 1):
        leg(cv, side * 1.7, -7.0, side * 1.9, -3.0, 'F')
    cv.paint(m_poly([(-4.1, shy - 0.5), (4.1, shy - 0.5), (3.1, hipy), (-3.1, hipy)]), JACKET, sh=JACKET_SH)
    cv.paint(m_rect(-0.5, shy + 1.0, 0.5, hipy), JACKET_SH, edge=None)
    cv.paint(m_rect(-3.5, hipy, 3.5, hipy + 3.5), PANTS, hi=PANTS_HI)                  # the lap
    head(cv, 0.0, hdy, 'F')
    for side in (-1, 1):
        arm(cv, side * 3.9, shy + 1.5, side * 5.2, shy + 8.0, 'F')


def _fig_P(cv, p, L, ph, sw, bob, lift, lean, hipy, shy, hdy):
    reach = p.get('arms') == 'reach'
    # feet: near leg x = ph * L / 2, far leg the opposite; at ph = 0 the legs pass (near one slightly ahead)
    xn, xf = (ph * L / 2.0, -ph * L / 2.0) if ph else (0.5 * L, -0.5 * L)
    sx, sy = 0.5 + lean * 0.5, shy + 1.5           # shoulder joint
    if reach:
        hx, hy = p['hand']
        far_hand = (hx - 1.0, hy - 1.5)
    else:
        a = 8.4
        dn = -ph * sw if ph else 0.0
        far_hand = (sx + (sw * ph if ph else 0.0), sy + np.sqrt(max(a * a - (sw * ph) ** 2, 1)))
        hx, hy = sx + dn, sy + np.sqrt(max(a * a - dn * dn, 1))
    # far arm (behind everything)
    arm(cv, sx, sy, far_hand[0], far_hand[1], 'P', far=True)
    # legs: the back one lifted
    back_is_far = xf <= xn
    lf = lift if back_is_far else 0
    ln = lift if not back_is_far else 0
    leg(cv, 0.5 + xf * 0.15, hipy, 0.5 + xf, -2.0 - lf, 'P', shade=True)
    leg(cv, 0.5 + xn * 0.15, hipy, 0.5 + xn, -2.0 - ln, 'P')
    # jacket: a 4-wide box that leans forward at the shoulders
    t = [(-2.0 + lean * 0.5, shy - 0.5), (3.0 + lean * 0.5, shy - 0.5), (3.0, hipy), (-2.0, hipy)]
    cv.paint(m_poly(t), JACKET, sh=JACKET_SH)
    head(cv, 0.5 + lean, hdy, 'P', rx=2.6, ry=4.0)
    arm(cv, sx, sy, hx, hy, 'P')


def _fig_FB(cv, p, view, L, ph, sw, out, bob, lift, lean, hipy, shy, hdy, mower, md):
    ux, uy = (0.8, -0.5) if view == 'B' else (-0.8, 0.5)
    reach = p.get('arms') == 'reach' or bool(mower)
    # who is forward: leg A (screen-left, x = -1.5) when ph > 0, leg B (x = +1.5) when ph < 0; passing: both ~ 0
    if ph:
        oa, ob = ph * L / 2.0, -ph * L / 2.0
    else:
        oa, ob = 0.5 * L, -0.5 * L
    legs = []
    for x, o in ((-1.5, oa), (1.5, ob)):
        lf = lift if o <= min(oa, ob) else 0
        legs.append((-2.0 + uy * o - lf, x, x + ux * o, o))
    T_ = None
    if mower == 'B':                                       # further away than the person: drawn first
        mx, my = (p['mx'], p['my']) if 'mx' in p else (int(round(ux * md)), int(round(uy * md)))
        mower_B(cv, mx - 7, my - 13)
        T_ = (ux * 3.0, hipy + 0.5 + uy * 3.0)
        cv.line(int(OXc + mx - 7 + 4), int(GYc + my - 13 + 7), int(OXc + T_[0]), int(GYc + T_[1]), OUT)
    elif mower == 'F':
        mx, my = (p['mx'], p['my']) if 'mx' in p else (int(round(ux * md)), int(round(uy * md)))
        T_ = (mx + 5.0, my - 13.5)
    for ay, x, ax, o in sorted(legs, key=lambda t: t[0]):
        leg(cv, x, hipy, ax, ay, view, shade=(o < 0))
    cv.paint(m_poly([(-4.1 + lean, shy - 0.5), (4.1 + lean, shy - 0.5), (3.1, hipy), (-3.1, hipy)]), JACKET, sh=JACKET_SH)
    if view == 'F':
        cv.paint(m_rect(-0.5, shy + 1.0, 0.5, hipy), JACKET_SH, edge=None)       # the zip
    head(cv, 0.0 + lean * 0.5, hdy, view)
    for side in (-1, 1):
        jx, jy = side * 3.9 + lean, shy + 1.5
        if reach and T_:
            arm(cv, jx, jy, T_[0] + side * 0.7, T_[1], view)
        else:
            o = oa if side < 0 else ob
            s = -np.sign(o) * sw if o != 0 else 0.0
            if ph == 0:
                s = (-sw if side < 0 else sw) * 0.5
            arm(cv, jx, jy, side * (4.6 + out) + (p['outr'] if side > 0 else 0) + ux * s, jy + 8.2 + uy * s, view)
    if mower == 'F':
        mower_F(cv, mx - 7, my - 14)


# ----------------------------------------------------------------------------------------------- the mower
def _wheel(cv, x0, y0):
    m = m_rect(x0, y0, x0 + 3, y0 + 3)
    cv.paint(m, WHEEL)
    cv.dot(x0 + 1, y0 + 1, HUB)


def mower_P_pic(ox, oy):
    """Profile mower facing right, 15 x 14, as a Cv with its picture's top-left at local (ox, oy)."""
    cv = Cv()
    cv.paint(m_rect(ox + 1, oy + 7, ox + 5, oy + 11), BAG, sh=BAG_SH)                  # bag at the rear
    cv.paint(m_rect(ox + 5, oy + 7, ox + 14, oy + 11), DECK, sh=DECK_SH)               # deck
    cv.paint(m_rect(ox + 5, oy + 7, ox + 14, oy + 8), RIM, edge=None)
    cv.paint(m_rect(ox + 7, oy + 2, ox + 12, oy + 6), COVER, hi=COVER_HI)              # engine cover
    cv.paint(m_rect(ox + 7, oy + 6, ox + 12, oy + 7), RIM, edge=None)
    _wheel(cv, ox + 5, oy + 10)
    _wheel(cv, ox + 11, oy + 10)
    cv.line(OXc + ox + 0, GYc + oy + 3, OXc + ox + 4, GYc + oy + 6, OUT)               # handle
    cv.line(OXc + ox + 1, GYc + oy + 3, OXc + ox + 5, GYc + oy + 6, OUT)
    cv.line(OXc + ox + 0, GYc + oy + 4, OXc + ox + 3, GYc + oy + 6, OUT)
    cv.dot(ox + 9, oy + 0, OUT)                                                        # spark-plug cap
    return cv


def mower_F(cv, ox, oy):
    """Front view (travelling down-left, rear up-right), 14 x 15; (ox, oy) = local top-left of the picture."""
    cv.line(OXc + ox + 10, GYc + oy + 5, OXc + ox + 13, GYc + oy + 0, OUT)              # handle (behind the bag)
    cv.line(OXc + ox + 11, GYc + oy + 5, OXc + ox + 13, GYc + oy + 1, OUT)
    cv.paint(m_rect(ox + 9, oy + 3, ox + 13, oy + 9), BAG, sh=BAG_SH)                    # bag behind the deck
    cv.paint(m_poly([(ox + 1, oy + 7), (ox + 10, oy + 7), (ox + 10, oy + 4), (ox + 3, oy + 4)]), RIM)
    cv.paint(m_rect(ox + 1, oy + 7, ox + 10, oy + 11), DECK, sh=DECK_SH)
    cv.paint(m_rect(ox + 4, oy + 2, ox + 8, oy + 6), COVER, hi=COVER_HI)
    _wheel(cv, ox + 1, oy + 11)
    _wheel(cv, ox + 7, oy + 11)


def mower_B(cv, ox, oy):
    """Back view (travelling up-right; the bag and the handle towards the viewer), about 14 x 13."""
    cv.paint(m_poly([(ox + 2, oy + 5), (ox + 11, oy + 5), (ox + 13, oy + 2), (ox + 4, oy + 2)]), RIM)
    cv.paint(m_rect(ox + 2, oy + 5, ox + 11, oy + 9), DECK, sh=DECK_SH)
    cv.paint(m_rect(ox + 5, oy + 1, ox + 9, oy + 4), COVER, hi=COVER_HI)
    _wheel(cv, ox, oy + 8)
    _wheel(cv, ox + 10, oy + 8)
    cv.paint(m_rect(ox + 4, oy + 8, ox + 9, oy + 12), BAG, sh=BAG_SH)
