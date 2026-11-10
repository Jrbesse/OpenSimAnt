"""Tile all extracted bitmaps of an archive into one PNG (ordered by id) and print each tile's position."""
import os, sys, json, struct, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simres import read_archive
from bitmaps import decode
from png import write_png

def main(arch, out, maxw=1200, skip_big=True):
    game = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    pal_res = [e for e in read_archive(os.path.join(game, 'HCEGANT')) if e['type'] == 15 and e['id'] == 0][0]
    pal = [tuple(pal_res['data'][2 + i * 3:5 + i * 3]) for i in range(16)]
    tiles = []
    for e in read_archive(os.path.join(game, arch)):
        if e['type'] != 2: continue
        w, h, rows, _ = decode(e['data'], palette=pal)
        if skip_big and w * h > 40000: continue
        tiles.append((e['id'], w, h, rows))
    x = y = rowh = 0; place = []
    for tid, w, h, rows in tiles:
        if x + w + 4 > maxw: x = 0; y += rowh + 4; rowh = 0
        place.append((tid, x, y, w, h, rows)); x += w + 4; rowh = max(rowh, h)
    H = y + rowh
    canvas = [[((90, 90, 110, 255) if ((i // 4 + j // 4) % 2) else (120, 120, 140, 255)) for i in range(maxw)] for j in range(H)]
    for tid, px, py, w, h, rows in place:
        for j in range(h):
            for i in range(w):
                c = rows[j][i]
                if c[3]: canvas[py + j][px + i] = c
        print(tid, px, py, w, h)
    write_png(out, maxw, H, canvas)

main(sys.argv[1], sys.argv[2])
