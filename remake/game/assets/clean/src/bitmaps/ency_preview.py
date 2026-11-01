"""ency_preview.py - preview sheets.  python ency_preview.py sheet <out.png> <scale> <id> [<id> ...]
python ency_preview.py all   writes preview_ency.png (contact sheet of all 40 at 2x + the cards as the game shows them).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import ency_lib as L
import ency_check as C

HERE = os.path.dirname(os.path.abspath(__file__))


def pic(ident):
    a = L.read_pix(ident)
    return a


def to_img(a, s, bg=255):
    im = Image.fromarray(np.where(a > 0, 0, bg).astype(np.uint8), 'L')
    return im.resize((a.shape[1] * s, a.shape[0] * s), Image.NEAREST)


def sheet(ids, s, path, width=1500):
    pad = 14
    items = [(i, pic(i)) for i in ids]
    x, y, rowh = pad, pad, 0
    pos = []
    for i, a in items:
        w, h = a.shape[1] * s, a.shape[0] * s + 12
        if x + w + pad > width:
            x, y, rowh = pad, y + rowh + pad, 0
        pos.append((x, y))
        x += w + pad
        rowh = max(rowh, h)
    im = Image.new('L', (width, y + rowh + pad), 150)
    d = ImageDraw.Draw(im)
    for (i, a), (px, py) in zip(items, pos):
        d.text((px, py), '%d  %dx%d' % (i, a.shape[1], a.shape[0]), fill=0)
        im.paste(to_img(a, s), (px, py + 12))
    im.save(path)


# the placement table: (id, card topic, x, y, text rects)
PLACE = [
    (150, 'front page', 4, 29, [(176, 1, 320, 180)]), (400, 'castes', 27, 21, [(144, 4, 310, 176)]),
    (410, 'castes', 19, 124, []), (500, 'behaviour', 6, 28, [(130, 12, 309, 161)]),
    (600, 'species', 17, 62, [(138, 13, 304, 162)]), (410, 'species', 1, 15, []),
    (700, 'life cycle', 35, 9, [(0, 52, 320, 175)]), (850, 'strategy', 4, 32, [(147, 17, 310, 157)]),
    (170, 'bees', 276, 57, [(2, 76, 317, 177)]), (410, 'intro', 110, -1, [(4, 51, 316, 176)]),
    (420, 'soldier', 89, 0, [(1, 57, 322, 181)]), (440, 'male', 89, 12, [(29, 86, 288, 154)]),
    (440, 'new queen', 85, -4, [(0, 43, 322, 179)]), (460, 'queen', 71, -2, [(-1, 55, 319, 180)]),
    (200, 'body', 66, 90, [(0, 0, 319, 87)]), (210, 'head', 3, 18, [(167, 7, 312, 171)]),
    (213, 'antennae', 85, -2, [(13, 51, 307, 176)]), (220, 'thorax', 34, 85, [(0, 0, 319, 80)]),
    (230, 'abdomen', 37, 77, [(0, 0, 318, 78)]), (300, 'social', 0, 5, [(141, 3, 317, 176)]),
    (320, 'termites', 118, 4, [(1, 30, 319, 177)]), (330, 'bees', 100, 1, [(2, 76, 317, 177)]),
    (340, 'wasps', 204, 43, [(11, 15, 190, 165)]), (610, 'weavers', -7, 39, [(136, 3, 316, 176)]),
    (620, 'harvesters', 82, 3, [(13, 78, 307, 167)]), (630, 'army', 98, 6, [(4, 75, 315, 176)]),
    (640, 'leafcutters', 5, 35, [(135, 9, 308, 171)]), (510, 'nest', 53, 79, [(0, 0, 319, 77)]),
    (520, 'communication', -34, 13, [(139, 3, 312, 176)]), (530, 'trails', 45, 110, [(6, 3, 315, 102)]),
    (540, 'fighting', 1, 26, [(114, 3, 316, 176)]), (540, 'warfare', -16, 31, [(96, 4, 318, 178)]),
    (550, 'aphids', 51, 75, [(0, 0, 317, 75)]), (560, 'brood', 58, 2, [(94, 3, 319, 175)]),
    (710, 'ant cycle', 12, 93, [(-1, 0, 319, 91)]), (720, 'colony cycle', 9, 126, [(2, 1, 318, 125)]),
    (880, 'flowchart', 10, 16, []),
]


def card(ident, x, y, texts, s=2, rects=()):
    a = pic(ident)
    c = np.zeros((200, 320), np.uint8)
    for yy in range(a.shape[0]):
        for xx in range(a.shape[1]):
            cx, cy = x + xx, y + yy
            if 0 <= cx < 320 and 0 <= cy < 200:
                c[cy, cx] = a[yy, xx]
    im = to_img(c, s).convert('RGB')
    d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in texts:
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, 320), min(y1, 180)
        for k in range(y0 * s, y1 * s, 4):
            d.line([(x0 * s, k), (x1 * s, k)], fill=(205, 205, 205))
    for k in range(180 * s, 200 * s, 4):
        d.line([(0, k), (320 * s, k)], fill=(150, 150, 150))
    for (x0, y0, x1, y1) in rects:                # the link rectangles, red
        d.rectangle([(x + x0) * s, (y + y0) * s, (x + x1) * s - 1, (y + y1) * s - 1], outline=(220, 0, 0))
    return im


def cards_sheet(path, s=1, cols=4, boxes=None):
    boxes = boxes or {}
    ims = [card(i, x, y, t, s, boxes.get(i, ())) for (i, _, x, y, t) in PLACE]
    pad = 8
    cw, ch = 320 * s, 200 * s
    rows = (len(ims) + cols - 1) // cols
    im = Image.new('RGB', (cols * (cw + pad) + pad, rows * (ch + pad + 12) + pad), (120, 120, 120))
    d = ImageDraw.Draw(im)
    for k, ci in enumerate(ims):
        px = pad + (k % cols) * (cw + pad)
        py = pad + (k // cols) * (ch + pad + 12)
        d.text((px, py), '%d %s' % (PLACE[k][0], PLACE[k][1]), fill=(255, 255, 255))
        im.paste(ci, (px, py + 12))
    im.save(path)


def all_ids():
    return sorted(C.SIZES)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'sheet':
        sheet([int(v) for v in sys.argv[4:]], int(sys.argv[3]), sys.argv[2])
    elif cmd == 'cards':
        cards_sheet(sys.argv[2], 1)
    elif cmd == 'all':
        ids = [i for i in all_ids() if os.path.exists(os.path.join(HERE, 'SHARED_%d.pix' % i))]
        import make_ency_bitmaps as M
        built, _ = M.build_all()
        boxes = {i: [b['rect'] for b in cv.boxes.values()] + ([cv.extra['button']['rect']] if 'button' in cv.extra else [])
                 for i, cv in built.items()}
        sheet(ids, 2, os.path.join(HERE, '_ency_sheet.png'), 1900)
        cards_sheet(os.path.join(HERE, '_ency_cards.png'), 2, 4, boxes)
        a, b = Image.open(os.path.join(HERE, '_ency_sheet.png')), Image.open(os.path.join(HERE, '_ency_cards.png'))
        out = Image.new('RGB', (max(a.width, b.width), a.height + b.height), (120, 120, 120))
        out.paste(a.convert('RGB'), (0, 0))
        out.paste(b, (0, a.height))
        out.save(os.path.join(HERE, 'preview_ency.png'))
        os.remove(os.path.join(HERE, '_ency_sheet.png'))
        os.remove(os.path.join(HERE, '_ency_cards.png'))
