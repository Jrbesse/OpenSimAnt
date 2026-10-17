"""Render the game state with the game's own graphics, the way the original draws its map windows.

python render_view.py [snapshot index] [out_dir]

Per cell (f_03518): a background tile from the 256-tile sheet (HCEGANT type 9: id 10 the yard, 9 the
house): the surface tile, in the nests (dirt - 0x70) & 0xFF, or a pheromone level 0xF1..0xFF when a
scent view is on; and a foreground sprite: an ant's type byte (caste << 3 | heading) indexes a 128-sprite
sheet (type 9 id 14 the surface, 13 the nests, loaded by f_02b43; the yellow ant uses its type, its queen's tail type + 8).
Sprites are drawn in the yellow ant's colours and recoloured on the way (f_02c21 / f_34b0f): each 12-byte
sprite row is mask, recolour mask, 4 planes; black ants XOR all planes with the recolour mask, red ants
(type 0x80+) only plane 1, the yellow ant none. Reads the user's own extracted resources.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))           # tools/: tiles.py, png.py
import tiles                                  # noqa: E402
from png import write_png                     # noqa: E402
from simant_ref.state import G, T, SIM       # noqa: E402

SURFACE, OCC = 0x0180, 0x6180
NESTS = {2: (0x2180, 0x8180), 3: (0x3180, 0x9180)}
PHER = {0: 0xd09f, 1: 0xe09f, 2: 0xe89f, 3: 0xf09f}                   # T:07BE 0..3; 4 is the red trail (4DA7:0)


class Art:
    def __init__(self):
        self.pal = tiles.palette()
        self.sheets = {i: tiles.load_sheet(i) for i in (9, 10, 13, 14)}
        self._tiles, self._sprites = {}, {}

    def tile(self, house, t):
        key = (house, t)
        if key not in self._tiles:
            self._tiles[key] = tiles.tile_pixels(self.sheets[9 if house else 10], t)
        return self._tiles[key]

    def sprite(self, sheet, s, mode):
        """16x16 of colour indices, None where transparent."""
        key = (sheet, s, mode)
        if key not in self._sprites:
            data, rows = self.sheets[sheet], []
            for y in range(16):
                r = s * 192 + y * 12
                row = []
                for x in range(16):
                    bit = 7 - (x & 7)
                    if not (data[r + (x >> 3)] >> bit) & 1:
                        row.append(None)
                        continue
                    xor = (data[r + 2 + (x >> 3)] >> bit) & 1
                    c = 0
                    for p in range(4):
                        v = (data[r + 4 + 2 * p + (x >> 3)] >> bit) & 1
                        if mode == 0 or (mode == 3 and p == 1):
                            v ^= xor
                        c |= v << p
                    row.append(c)
                rows.append(row)
            self._sprites[key] = rows
        return self._sprites[key]


def colour_mode(st, fg):
    """f_02c21: the recolour mode, the low byte of the word at DS:1A58 + ((fg & 0xFFBF) >> 6)."""
    return st.u8(0x55b3, 0x1a58 + (((fg & 0xffbf) >> 6) & 0xffff))


def cell(st, view, a, b):
    """f_03518 for map cell (a, b): (background tile, foreground id or 0). Foreground ids as the original:
    surface ant 0x100 + type, nest ant 0x200 + type, the yellow ant 0x380 / 0x300 + type + G:049A + (its
    heading, or G:0502 for a queen's cocoon), a queen's tail 0x388 / 0x308 + type + heading + G:049A."""
    if view <= 1:
        bg = 0
        mode = st.u16(T, 0x7be)
        if mode < 5:
            v = (st.u8(0x4da7, (a >> 1) * 32 + (b >> 1)) if mode == 4
                 else st.pher(PHER[mode], a >> 1, b >> 1))
            if v > 0x10:
                bg = (((v >> 4) & 0x1f) - 0x10) & 0xff
        if bg == 0:
            bg = st.grid(SURFACE, a, b)
        o, base, yellow, tail = st.grid(OCC, a, b), 0x100, 0x380, 0x388
    else:
        dirt, cells = NESTS[view]
        bg = (st.grid(dirt, a, b) - 0x70) & 0xff
        o, base, yellow, tail = st.grid(cells, a, b), 0x200, 0x300, 0x308
    if o == 0:
        return bg, 0
    extra, t, h = st.u16(G, 0x49a), st.u16(G, 0x4c2), st.u16(G, 0x496)
    if o == 0xff:
        fg = extra + t + yellow + (st.u16(G, 0x502) if t < 8 else h)
    elif o == 0xfe:
        fg = extra + h + t + tail
    else:
        fg = o + base
    return bg, fg & 0xffff


def render(st, view, path, art=None, crop=None):
    """Write the whole map of `view` (1 surface, 2 black nest, 3 red nest), 16 px per cell; the screen's
    x is a, y is b. crop = (a0, b0, a1, b1)."""
    art = art or Art()
    w, h = (128, 64) if view <= 1 else (64, 64)
    a0, b0, a1, b1 = crop or (0, 0, w, h)
    house = view <= 1 and st.u16(G, 0xf24) != 0
    img = [[(0, 0, 0, 255)] * ((a1 - a0) * 16) for _ in range((b1 - b0) * 16)]
    for a in range(a0, a1):
        for b in range(b0, b1):
            bg, fg = cell(st, view, a, b)
            pix = [row[:] for row in art.tile(house, bg)]
            if fg:
                f = fg - (0x280 if fg >= 0x380 else 0x200 if fg >= 0x200 else 0x100)
                sheet = 13 if 0x200 <= fg < 0x380 else 14                 # f_02b43: nests 13, surface 14
                spr = art.sprite(sheet, f & 0x7f, colour_mode(st, f))
                for y in range(16):
                    for x in range(16):
                        if spr[y][x] is not None:
                            pix[y][x] = spr[y][x]
            ox, oy = (a - a0) * 16, (b - b0) * 16
            for y in range(16):
                row = img[oy + y]
                for x in range(16):
                    r, g, bb = art.pal[pix[y][x]]
                    row[ox + x] = (r, g, bb, 255)
    write_png(path, len(img[0]), len(img), img)


def main():
    from verify import Verifier
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', '..', 'extracted', 'render')
    os.makedirs(out, exist_ok=True)
    v = Verifier()
    v.load(v.snaps[idx][1])
    st = v.state_from_emu()
    art = Art()
    tick = v.snaps[idx][0]
    for view, name in ((1, 'surface'), (2, 'black_nest'), (3, 'red_nest')):
        p = os.path.join(out, f'{name}_{tick}.png')
        render(st, view, p, art)
        print('wrote', p)


if __name__ == '__main__':
    main()
