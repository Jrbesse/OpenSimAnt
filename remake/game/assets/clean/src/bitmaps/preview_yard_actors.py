"""preview_yard_actors: preview_yard_actors.png for passes 4 and 5 of the yard spec (the animals, the spider, the map-window actors).

    python preview_yard_actors.py          # builds passes 4 and 5 on their own and writes preview_yard_actors.png

Sections (the spec's preview items 2 to 5): (1) every animation as a strip in the game's cycle order, each frame drawn at its offset
from the actor's position (the small cross); (2) the spider composite: the eight bodies with legs and fangs drawn by this code as the
game does it (legs.json frame 0 for the right side, frame 4 for the left, the turn and flip rules); (3) the beaten frames;
(4) the Map window's actors on a grid of 4-px cells (the small spiders, the sneaker, the mower).  Everything at 3x.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from uilib import Reg, T  # noqa: E402
import yard_pass4  # noqa: E402
import yard_pass5  # noqa: E402

PAL = [(255, 255, 255), (252, 243, 5), (255, 100, 2), (221, 8, 6), (242, 8, 132), (70, 0, 165), (0, 0, 212), (2, 171, 234),
       (31, 183, 20), (0, 100, 17), (86, 44, 5), (144, 113, 58), (192, 192, 192), (128, 128, 128), (64, 64, 64), (0, 0, 0)]
SC = 3


class Canvas:
    def __init__(self, w, h, bg):
        self.a = np.full((h, w), bg, dtype=np.int16)

    def blit(self, img, x, y):
        a = img.a if hasattr(img, 'a') else img
        h, w = a.shape
        for j in range(h):
            for i in range(w):
                v = a[j, i]
                if v != T and 0 <= y + j < self.a.shape[0] and 0 <= x + i < self.a.shape[1]:
                    self.a[y + j, x + i] = v

    def set(self, x, y, c):
        if 0 <= y < self.a.shape[0] and 0 <= x < self.a.shape[1]:
            self.a[y, x] = c

    def cross(self, x, y, c=4):
        for d in (-1, 0, 1):
            self.set(x + d, y, c)
            self.set(x, y + d, c)

    def rect(self, x0, y0, x1, y1, c):
        self.a[y0:y1, x0:x1] = c


def strip(frames_offsets, anchor, cell, bg=8, order=None):
    """frames: list of (Img, dx, dy); cycle order given as indices."""
    order = order or list(range(len(frames_offsets)))
    cv = Canvas(cell[0] * len(order), cell[1], bg)
    for n, i in enumerate(order):
        img, dx, dy = frames_offsets[i]
        x0 = n * cell[0]
        cv.blit(img, x0 + anchor[0] + dx, anchor[1] + dy)
        cv.cross(x0 + anchor[0], anchor[1])
    return cv.a


def leg_polys(k):
    """The game's legs and fangs for heading k, relative to the thorax centre: (right legs, left legs, fang polylines)."""
    d = json.load(open(yard_pass5.LEGS_JSON))
    mirN = lambda p: (-p[0], p[1])
    mirE = lambda p: (-p[1], -p[0])
    if k in (0, 2, 4, 6):
        src, mir = d['north'], mirN
        f = {0: lambda p: p, 2: lambda p: (-p[1], p[0]), 4: lambda p: (-p[0], -p[1]), 6: lambda p: (p[1], -p[0])}[k]
    else:
        src, mir = d['north_east'], mirE
        f = {1: lambda p: p, 3: lambda p: (p[0], -p[1]), 5: lambda p: (-p[0], -p[1]), 7: lambda p: (-p[0], p[1])}[k]
    right = [[f(tuple(p)) for p in leg[0]] for leg in src['legs']]
    left = [[f(mir(tuple(p))) for p in leg[4]] for leg in src['legs']]
    fang0 = [f(tuple(p)) for p in src['fangs'][0]]
    fang1 = [f(mir(tuple(p))) for p in src['fangs'][0]]
    return right, left, [fang0, fang1]


def spider_composite(img, k, c, player=True):
    pad = 40
    h, w = img.h + 2 * pad, img.w + 2 * pad
    cv = Canvas(w, h, 10)
    for y in range(h):
        for x in range(w):
            if (x // 6 + y // 6) % 2:
                cv.a[y, x] = 8
    cv.blit(img, pad, pad)
    cx, cy = pad + c[0], pad + c[1]
    right, left, fangs = leg_polys(k)
    for poly in right + left:
        for p, q in zip(poly, poly[1:]):
            for (x, y) in yard_pass5.line_pts(cx + p[0], cy + p[1], cx + q[0], cy + q[1]):
                cv.set(x, y, 15)
    for poly in fangs:
        for p, q in zip(poly, poly[1:]):
            for (x, y) in yard_pass5.line_pts(cx + p[0], cy + p[1], cx + q[0], cy + q[1]):
                cv.set(x, y, 1 if player else 15)
    return cv.a


def to_image(a, scale=SC):
    rgb = np.zeros(a.shape + (3,), dtype=np.uint8)
    for i, c in enumerate(PAL):
        rgb[a == i] = c
    return Image.fromarray(rgb).resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST)


def make(reg, path):
    I = reg.img
    sections = []
    # ---- (1) the animals
    def frames(rows, ids):
        return [(I[b], dx, dy) for (b, w, h, dx, dy) in rows]
    for hd in range(4):
        rows = yard_pass4.DOG_WALK[hd]
        sections.append(strip(frames(rows, None), (12, 10), (30, 34), order=[0, 1, 2, 1, 0, 1, 2, 1]))
    for hd in (4, 5):
        rows = yard_pass4.DOG_REST[hd]
        sections.append(strip(frames(rows, None), (12, 10), (30, 34), order=[0, 1, 0, 1, 0, 1, 0, 1]))
    sections.append(strip([(I[b], 0, 0) for b in (1300, 1301, 1302)], (4, 4), (26, 20), bg=13, order=[0, 1, 2, 1, 2, 1]) )
    sections.append(strip([(I[b], 0, 0) for b in (1303, 1304, 1305)], (4, 4), (26, 20), bg=13, order=[0, 1, 2, 1, 2, 1]))
    sections.append(strip([(I[b], dx, dy) for (b, w, h, dx, dy) in yard_pass4.CAT_START], (24, 26), (50, 40), bg=13, order=[0, 1, 2, 1, 2]))
    sections.append(strip([(I[b], dx, dy) for (b, w, h, dx, dy) in yard_pass4.CAT_POUNCE[:5]], (6, 26), (46, 46), bg=13))
    sections.append(strip([(I[b], dx, dy) for (b, w, h, dx, dy) in yard_pass4.CAT_POUNCE[5:]], (6, 26), (46, 46), bg=13))
    sections.append(strip([(I[1250], -10, -3), (I[1251], -9, -1)], (14, 8), (30, 18), bg=7, order=[0, 1, 0, 1, 0, 1, 0, 1]))
    # ---- (2) the spider composite and (3) the beaten frames
    comps = []
    for k, (bid, w, h, c, A, B, F) in yard_pass5.BODY.items():
        comps.append(spider_composite(I[bid], k, c))
    hmax = max(c.shape[0] for c in comps)
    row = np.full((hmax, sum(c.shape[1] for c in comps)), 13, dtype=np.int16)
    x = 0
    for c in comps:
        row[:c.shape[0], x:x + c.shape[1]] = c
        x += c.shape[1]
    sections.append(row)
    cv = Canvas(sum(w for (_, w, h, c) in yard_pass5.BEATEN) + 20, max(h for (_, w, h, c) in yard_pass5.BEATEN) + 4, 10)
    x = 2
    for (bid, w, h, c) in yard_pass5.BEATEN:
        cv.blit(I[bid], x, 2)
        cv.cross(x + c[0], 2 + c[1])
        x += w + 5
    sections.append(cv.a)
    # ---- (4) the Map window's actors on 4-px cells (green, tan, brown, grey)
    cw, ch = 4, 4
    W4, H4 = 70, 40
    cv = Canvas(W4 * cw, H4 * ch, 8)
    cols = [8, 11, 10, 12]
    rs = np.random.RandomState(3)
    for j in range(H4):
        for i in range(W4):
            cv.rect(i * cw, j * ch, i * cw + cw, j * ch + ch, cols[(i // 6 + j // 5 + rs.randint(0, 2)) % 4])
    for k in range(8):
        cv.blit(I[1100 + k], 6 + k * 14, 4)
    cv.blit(I[1200], 6, 24 + 0)
    sections.append(cv.a)
    big = Canvas(290, 130, 8)
    for j in range(0, 130, 4):
        for i in range(0, 290, 4):
            big.rect(i, j, i + 4, j + 4, cols[((i // 24) + (j // 20)) % 4])
    big.blit(I[1200], 4, 4)
    big.blit(I[1202], 30, 4)
    big.blit(I[1201], 60, 4)
    big.blit(I[1203], 60, 36)
    big.blit(I[1210], 138, 4)
    big.blit(I[1400], 250, 10)
    sections.append(big.a)
    sec_imgs = [to_image(a) for a in sections]
    W = max(i.width for i in sec_imgs) + 8
    H = sum(i.height + 6 for i in sec_imgs) + 8
    out = Image.new('RGB', (W, H), (60, 60, 70))
    y = 4
    for im in sec_imgs:
        out.paste(im, (4, y))
        y += im.height + 6
    out.save(path)


if __name__ == '__main__':
    reg = Reg()
    yard_pass4.build(reg)
    yard_pass5.build(reg)
    make(reg, os.path.join(HERE, 'preview_yard_actors.png'))
    print('wrote preview_yard_actors.png')
