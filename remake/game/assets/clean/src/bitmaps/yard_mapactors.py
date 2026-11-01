"""yard_mapactors: the Map window's actors of the yard spec (group I, besides the small spiders): the sneaker 1200..1203, the mower
1210 / 1211 and the marker 1400.  Used by yard_pass5.  Colour scheme (shared with the person of pass 3 by the spec's words only):
sneakers white with a red toe cap and heel tab, a dark-grey sole and black laces; the mower red with an orange rim, a dark engine
cover and black wheels on a dark-green mat."""
import numpy as np

from uilib import Img, T


# ------------------------------------------------------------------------------------------------ the sneaker (1200..1203)
_HW = [(0, 3.2), (1, 5.0), (3, 7.4), (6, 9.4), (10, 10.8), (14, 11.5), (24, 11.2), (32, 10.4), (40, 8.9), (46, 8.7), (52, 9.4),
       (58, 10.0), (63, 9.2), (66, 6.8), (67.99, 4.0)]


def _hw(y):
    """Half-width of the sneaker's silhouette at row y (toe up, 23 x 68): round toe, ball, arch, heel."""
    for (y0, w0), (y1, w1) in zip(_HW, _HW[1:]):
        if y0 <= y <= y1:
            return w0 + (w1 - w0) * (y - y0) / (y1 - y0)
    return 0.0


def sneaker_up():
    W, H = 23, 68
    a = np.full((H, W), T, dtype=np.int16)
    cx = 11.5
    for y in range(H):
        hw = _hw(y + 0.5)
        for x in range(W):
            dx = abs(x + 0.5 - cx)
            if dx <= hw:
                edge = hw - dx                       # how far inside the silhouette
                depth = min(edge, (y + 0.5) * 1.3, H - (y + 0.5))
                if depth < 1.0:
                    v = 15
                elif depth < 3.0:
                    v = 14                           # the rubber sole, a ring round the foot
                elif depth < 4.0:
                    v = 15                           # the line between sole and upper
                else:
                    v = 0                            # the white upper
                a[y, x] = v
    img = Img(W, H, T)
    img.a = a
    # the red toe cap with its seam, the red heel tab
    for y in range(H):
        for x in range(W):
            if a[y, x] == 0:
                seam = 17.5 - 4.0 * ((abs(x + 0.5 - cx) / 11.0) ** 2)
                if y + 0.5 < seam - 1:
                    img.a[y, x] = 3
                elif y + 0.5 < seam:
                    img.a[y, x] = 15
                elif y + 0.5 > 62.5:
                    img.a[y, x] = 3
                elif y + 0.5 > 61.5:
                    img.a[y, x] = 15
    # the tongue and the laces
    for y in range(22, 44):
        for x in range(7, 16):
            if img.a[y, x] == 0:
                img.a[y, x] = 12
    for y in range(24, 44, 4):
        for x in range(5, 18):
            if img.a[y, x] in (0, 12):
                img.a[y, x] = 15
        for x in (4, 18):
            if img.a[y, x] == 0:
                img.a[y, x] = 3                      # the eyelets
        for x in (6, 8, 10, 12, 14, 16):
            if y + 1 < 44 and img.a[y + 1, x] == 12:
                img.a[y + 1, x] = 15
    # the heel opening: a padded collar and the dark mouth of the shoe
    for y in range(44, 62):
        for x in range(W):
            dx, dy = (x + 0.5 - cx) / 7.0, (y + 0.5 - 53.0) / 8.0
            r2 = dx * dx + dy * dy
            if r2 <= 1.0 and img.a[y, x] not in (T, 14):
                img.a[y, x] = 15 if r2 > 0.86 else (12 if r2 > 0.55 else 14)
    return img


def build_sneaker(reg):
    up = sneaker_up()
    arr = {1200: up.a, 1201: np.rot90(up.a, -1), 1202: np.rot90(up.a, 2), 1203: np.rot90(up.a, 1)}
    toe = {1200: 'up', 1201: 'right', 1202: 'down', 1203: 'left'}
    for bid, a in arr.items():
        im = Img(a.shape[1], a.shape[0], T)
        im.a = np.ascontiguousarray(a).astype(np.int16)
        reg.add(bid, im, (im.w, im.h), True, None, 'sneaker seen from above, toe %s (Map window foot print)' % toe[bid])


# ------------------------------------------------------------------------------------------------ the Map window mower (1210, 1211)
def _rr(dx, dy, hw, hh, r):
    qx, qy = dx - (hw - r), dy - (hh - r)
    if qx <= 0 or qy <= 0:
        return dx <= hw and dy <= hh
    return qx * qx + qy * qy <= r * r


def mower_map():
    """98 x 103, point-symmetric (the same after a 180-degree turn): a red deck with an orange rim, a dark engine cover, four wheels,
    slots and rivets, on a dark-green mat.  Every shape is a function of |dx|, |dy| from the centre."""
    W, H = 98, 103
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    a = np.full((H, W), 9, dtype=np.int16)
    for y in range(H):
        for x in range(W):
            dx, dy = abs(x - cx), abs(y - cy)
            v = None
            if _rr(dx, dy, 49.0, 51.5, 20):
                v = 15
                if _rr(dx, dy, 47.0, 49.5, 18):
                    v = 3
                    if _rr(dx, dy, 44.0, 46.5, 15.5):
                        v = 3 if _rr(dx, dy, 41.0, 43.5, 13.5) else 2
                    if 30 <= dy <= 32 and dx <= 30:
                        v = 15                       # the blade housing's slots
                    if 24 <= dx <= 26 and 33 >= dy >= 29:
                        v = 15
            # wheels, over the deck's corners
            if 37 <= dx <= 48.5 and 31 <= dy <= 51.5:
                v = 15 if (dx < 38.5 or dx > 47 or dy < 32.5 or dy > 50.5) else (14 if (int(dy) % 4 < 2) else 13)
            # the engine cover
            r = float(np.hypot(dx, dy * 0.92))
            if r <= 23.5:
                v = 15
                if r <= 21.5:
                    v = 14
                    if r <= 17.5:
                        v = 13 if (int(dx) // 3 + int(dy) // 3) % 2 == 0 else 14
                    if r <= 7.5:
                        v = 15 if r > 5.5 else 12
                    if dy <= 1.0 and 8 <= dx <= 15:
                        v = 15
                    if dx <= 1.0 and 8 <= dy <= 15:
                        v = 15
            if v is not None:
                a[y, x] = v
    for y in range(H):                                       # rivets (symmetric: tested on |dx|, |dy|)
        for x in range(W):
            dx, dy = abs(x - cx), abs(y - cy)
            for (rx, ry) in ((33.5, 42.0), (33.5, 36.0), (29.5, 44.0)):
                if abs(dx - rx) <= 0.6 and abs(dy - ry) <= 0.6 and a[y, x] in (3, 2):
                    a[y, x] = 15
    img = Img(W, H, T)
    img.a = a
    return img


def build_mower(reg):
    m = mower_map()
    assert (m.a == m.a[::-1, ::-1]).all(), 'the mower is point-symmetric'
    reg.add(1210, m, (98, 103), False, None, 'Map window mower, travelling up or down (point-symmetric)')
    m2 = Img(103, 98, T)
    m2.a = np.ascontiguousarray(np.rot90(m.a, 1)).astype(np.int16)
    reg.add(1211, m2, (103, 98), False, None, 'Map window mower, travelling left or right (1210 turned by 90 degrees)')


# ------------------------------------------------------------------------------------------------ the marker (1400)
def marker():
    img = Img(14, 14, T)
    for y in range(1, 14):
        for x in range(1, 14):
            r = float(np.hypot(x - 7.0, y - 7.0))
            if r <= 6.6:
                img.a[y, x] = 15 if r > 5.4 else (3 if r > 3.2 else 0)
    for k in range(3, 12):                          # the cross-hair
        img.a[7, k] = 15
        img.a[k, 7] = 15
    return img


def build_marker(reg):
    reg.add(1400, marker(), (14, 14), True, (0, 3, 15), 'round marker for the Behavior / Caste triangles: ring, red ring, cross-hair')
