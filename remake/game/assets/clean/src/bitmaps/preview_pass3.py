"""preview_pass3: preview_yard3.png for pass 3 of the yard bitmaps: every animation of the person as a strip at 4x in the game's cycle order
(0, 1, 2, 1) with the frames drawn on their offsets round the actor's position (the small cross), the standing frames, the mower sprites, and
the patches 8900..8903, 8200, 8201 in place on 7000 / 7001.   python preview_pass3.py"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from uilib import T  # noqa: E402
import yard_pass3 as p3  # noqa: E402
from preview_yard import PAL  # noqa: E402

BG = (90, 90, 110)
K = 4


def rgb(a, bg=BG):
    out = np.zeros(a.shape + (3,), dtype=np.uint8)
    out[:] = bg
    m = a != T
    out[m] = np.array(PAL, dtype=np.uint8)[a[m]]
    return out


def cell(reg, bid, ox, oy, cw=62, ch=48, mower=None):
    c = np.full((ch, cw), T, dtype=np.int16)
    w, h, dx, dy = p3.SIZES[bid]

    def put(a, x, y):
        for yy in range(a.shape[0]):
            for xx in range(a.shape[1]):
                if a[yy, xx] != T and 0 <= x + xx < cw and 0 <= y + yy < ch:
                    c[y + yy, x + xx] = a[yy, xx]
    if mower:
        m = reg.img[mower].a
        put(m, ox + (19 if mower == 8801 else -15), oy + 15)
    put(reg.img[bid].a, ox + dx, oy + dy)
    c[oy, max(ox - 2, 0):ox + 3] = 13
    c[max(oy - 2, 0):oy + 3, ox] = 13
    return c


def make(reg, path):
    rows = []
    for name, ids in p3.SETS:
        order = list(ids[:3]) + [ids[1]] if len(ids) == 3 else list(ids)
        mower = 8801 if 'mowing heading 1' in name else 8802 if 'mowing heading 3' in name else None
        cells = [cell(reg, b, 22, 4, mower=mower) for b in order]
        rows.append(np.concatenate([rgb(x) for x in cells], axis=1).repeat(K, 0).repeat(K, 1))
    # mower sprites
    mw = np.full((20, 60), T, dtype=np.int16)
    for i, b in enumerate((8800, 8801, 8802)):
        m = reg.img[b].a
        mw[2:2 + m.shape[0], 2 + i * 20:2 + i * 20 + m.shape[1]] = m
    rows.append(rgb(mw).repeat(K, 0).repeat(K, 1))
    # patches in place
    pics = []
    base0, base1 = reg.img[7000].a, reg.img[7001].a
    for bid in (8900, 8901, 8902, 8903):
        a = base0[60:125, 150:230].copy()
        x0, y0, x1, y1 = p3.PATCH_RECT[bid]
        a[y0 - 60:y1 - 60, x0 - 148:x1 - 148] = reg.img[bid].a
        pics.append(rgb(a))
    for bid, base, x0, y0 in ((8200, base1, 45, 166), (8201, base1, 207, 47)):
        a = base[y0 - 10:y0 + 40, x0 - 10 + 2:x0 + 29 + 2].copy()
        h, w = reg.img[bid].a.shape
        a[10:10 + h, 10:10 + w] = reg.img[bid].a
        pics.append(rgb(a))
    H = max(p.shape[0] for p in pics)
    pics = [np.pad(p, ((0, H - p.shape[0]), (0, 3), (0, 0)), constant_values=0) for p in pics]
    rows.append(np.concatenate(pics, axis=1).repeat(3, 0).repeat(3, 1))
    W = max(r.shape[1] for r in rows) + 16
    H = sum(r.shape[0] + 8 for r in rows) + 8
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:] = BG
    y = 8
    for r in rows:
        img[y:y + r.shape[0], 8:8 + r.shape[1]] = r
        y += r.shape[0] + 8
    Image.fromarray(img).save(path)


if __name__ == '__main__':
    reg = p3.runner()
    make(reg, os.path.join(HERE, 'preview_yard3.png'))
    print('wrote preview_yard3.png')
