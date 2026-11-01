"""preview_yard: preview_yard.png for the yard bitmaps (passes 1-2 so far): the yard window as the game shows it in four views
(Yard, House, Strat, Graphic; 2x), the toolbar with its help overlay, the toolbar's inverted buttons, and the small sprites."""
import numpy as np
from PIL import Image

from uilib import T
import yard_pass2

PAL = [(255, 255, 255), (252, 243, 5), (255, 100, 2), (221, 8, 6), (242, 8, 132), (70, 0, 165), (0, 0, 212), (2, 171, 234),
       (31, 183, 20), (0, 100, 17), (86, 44, 5), (144, 113, 58), (192, 192, 192), (128, 128, 128), (64, 64, 64), (0, 0, 0)]
BG = (90, 90, 110)
X0, Y0, X1, Y1 = 62, 62, 578, 386            # the yard window (screen)
OX_, OY_ = 65, 83                           # yard origin (screen)


def blit(canvas, a, x, y, clip=None):
    """Draw array a (T = transparent) with its top-left at screen (x, y) on canvas (screen coordinates), clipped to the window / clip."""
    h, w = a.shape
    cx0, cy0, cx1, cy1 = clip or (X0, Y0, X1, Y1)
    for yy in range(h):
        sy = y + yy
        if not (cy0 <= sy < cy1):
            continue
        for xx in range(w):
            sx = x + xx
            if cx0 <= sx < cx1 and a[yy, xx] != T:
                canvas[sy - Y0, sx - X0] = a[yy, xx]


def lattice_patches(canvas, view, rs):
    from yardlib import lattice
    kinds = [15, 3, 'chk', 8, 8, 15, 3, 8]
    for r in range(16):
        for c in range(12):
            k = kinds[(c * 3 + r * 5) % len(kinds)] if rs.rand() < 0.45 else 8
            x0 = 169 + 28 * c - 10 * r
            y0 = 67 + 10 * r
            if view == 'strat':
                for i in range(7):
                    for j in range(24):
                        v = k
                        if k == 'chk':
                            v = 15 if (i + j) % 2 == 0 else 3
                        canvas[OY_ + y0 + i - Y0, OX_ + x0 - i + j - X0] = v
            else:                                    # graphic: 9-px bars on the baseline y = 71 + 10 r at x offsets 168 and 180
                for off, col in ((168, 15), (180, 3)):
                    if rs.rand() < 0.5:
                        hgt = int(rs.randint(2, 8))
                        for j in range(9):
                            for i in range(hgt):
                                xx = 28 * c - 10 * r + off - 8 + j
                                yy = 71 + 10 * r - i
                                canvas[OY_ + yy - Y0, OX_ + xx - X0] = col


def window(reg, view, rs):
    canvas = np.full((Y1 - Y0, X1 - X0), 13, dtype=np.int16)
    blit(canvas, reg.img[7010].a, 64, 339)
    if view in ('yard', 'house'):
        blit(canvas, reg.img[7000 if view == 'yard' else 7001].a, 63, 83)
        blit(canvas, reg.img[7003].a, 344, 83)
        if view == 'yard':
            blit(canvas, reg.img[1260].a, OX_ + 170, OY_ + 186, (64, 83, 577, 339))
        for _ in range(15):
            blit(canvas, reg.img[7005].a, OX_ + int(rs.randint(50, 450)), OY_ + int(rs.randint(0, 150)), (64, 83, 577, 339))
        for k, qid in enumerate([7006, 7007] * 4):
            blit(canvas, reg.img[qid].a, OX_ + 120 + 9 * k + int(rs.randint(0, 2)), OY_ + 100 + int(rs.randint(0, 2)), (64, 83, 577, 339))
    else:
        blit(canvas, reg.img[7020].a, 64, 148)
        blit(canvas, reg.img[7021].a, 64, 199)
        blit(canvas, reg.img[7022].a, 64, 254)
        lattice_patches(canvas, view, rs)
    return canvas


def to_rgb(a):
    return np.array(PAL, dtype=np.uint8)[a]


def scale(a, k):
    return np.kron(a, np.ones((k, k), dtype=a.dtype)) if a.ndim == 2 else a.repeat(k, 0).repeat(k, 1)


def make(reg, path):
    rs = np.random.RandomState(3)
    views = [window(reg, v, rs) for v in ('yard', 'house', 'strat', 'graphic')]
    k = 2
    tiles = [to_rgb(scale(v, k)) for v in views]
    pad = 12
    th, tw = tiles[0].shape[:2]
    # row 3: the toolbar with its overlay (as in the game: overlay at screen (62, 296), toolbar at (64, 339)) and its inverted buttons
    t = reg.img[7010]
    bar = np.full((Y1 - 296, X1 - X0), 13, dtype=np.int16)
    bar[339 - 296:339 - 296 + 46, 64 - X0:64 - X0 + 512] = t.a
    o = reg.img[7011].a
    for yy in range(o.shape[0]):
        for xx in range(o.shape[1]):
            if o[yy, xx] != T:
                bar[yy, 62 - X0 + xx] = o[yy, xx]
    inv = t.a.copy()
    for name in yard_pass2.INVERTED:
        r = yard_pass2.HIT[name]
        inv[r[1]:r[3], r[0]:r[2]] ^= 15
    bar2 = np.full((46, 512), 13, dtype=np.int16)
    bar2[:] = inv
    row3a = to_rgb(scale(bar, k))
    row3b = to_rgb(scale(bar2, k))
    # small sprites at 4x
    sm_canvas = np.full((84, 300), 13, dtype=np.int16)
    for (a, x, y) in ((reg.img[1260].a, 4, 4), (reg.img[7005].a, 70, 4), (reg.img[7006].a, 90, 10), (reg.img[7007].a, 90, 20)):
        h, w = a.shape
        for yy in range(h):
            for xx in range(w):
                if a[yy, xx] != T:
                    sm_canvas[y + yy, x + xx] = a[yy, xx]
    row3c = to_rgb(scale(sm_canvas, 4))
    W = max(2 * tw + 3 * pad, row3a.shape[1] + 2 * pad)
    H = 2 * th + 3 * pad + row3a.shape[0] + pad + row3b.shape[0] + pad + row3c.shape[0] + pad
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:] = BG
    y = pad
    for i, tile in enumerate(tiles):
        img[y + (i // 2) * (th + pad):y + (i // 2) * (th + pad) + th, pad + (i % 2) * (tw + pad):pad + (i % 2) * (tw + pad) + tw] = tile
    y += 2 * (th + pad)
    img[y:y + row3a.shape[0], pad:pad + row3a.shape[1]] = row3a
    y += row3a.shape[0] + pad
    img[y:y + row3b.shape[0], pad:pad + row3b.shape[1]] = row3b
    y += row3b.shape[0] + pad
    img[y:y + row3c.shape[0], pad:pad + row3c.shape[1]] = row3c
    Image.fromarray(img).save(path)
    return path
