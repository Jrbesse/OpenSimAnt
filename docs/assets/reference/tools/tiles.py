"""Decode the EGA tile sheets (HCEGANT type 9 ids 9 house, 10 yard; 13..20 sprites) to PNG contact sheets.

python tools/tiles.py [out_dir]

A 16x16 cell takes 128 bytes: 16 rows of 8 bytes, each row the 4 bit planes' 2 bytes (most significant
bit = leftmost pixel). Colour index = p0 | p1<<1 | p2<<2 | p3<<3 in the type 15 palette. Reads the user's own extracted resources (extracted/hcegant).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from png import write_png               # noqa: E402

EXTRACTED = os.path.join(HERE, '..', 'extracted', 'hcegant')


def palette():
    d = open(os.path.join(EXTRACTED, 'palette', '00000.bin'), 'rb').read()
    n = struct.unpack('>H', d[:2])[0]
    return [tuple(d[2 + 3 * i:5 + 3 * i]) for i in range(n)]


def load_sheet(rid):
    return open(os.path.join(EXTRACTED, 'rects', f'{rid:05d}.bin'), 'rb').read()


def tile_pixels(sheet, t):
    """16x16 colour indices of cell t."""
    rows = []
    for y in range(16):
        row = []
        for x in range(16):
            byte, bit = t * 128 + y * 8 + (x >> 3), 7 - (x & 7)
            c = 0
            for p in range(4):
                c |= ((sheet[byte + 2 * p] >> bit) & 1) << p
            row.append(c)
        rows.append(row)
    return rows


def contact_sheet(sheet, pal, path, per_row=16, scale=2):
    n = len(sheet) // 128
    rows_n = (n + per_row - 1) // per_row
    w, h = per_row * 17 * scale, rows_n * 17 * scale
    img = [[(40, 40, 40, 255)] * w for _ in range(h)]
    for t in range(n):
        px = tile_pixels(sheet, t)
        ox, oy = (t % per_row) * 17 * scale, (t // per_row) * 17 * scale
        for y in range(16):
            for x in range(16):
                r, g, b = pal[px[y][x]]
                for dy in range(scale):
                    for dx in range(scale):
                        img[oy + y * scale + dy][ox + x * scale + dx] = (r, g, b, 255)
    write_png(path, w, h, img)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'extracted', 'tiles')
    os.makedirs(out, exist_ok=True)
    pal = palette()
    for rid in (9, 10, 13, 14, 15, 16, 17, 18, 19, 20):
        p = os.path.join(EXTRACTED, 'rects', f'{rid:05d}.bin')
        if os.path.exists(p):
            contact_sheet(load_sheet(rid), pal, os.path.join(out, f'sheet_{rid:02d}.png'))
            print('wrote', os.path.join(out, f'sheet_{rid:02d}.png'))


if __name__ == '__main__':
    main()
