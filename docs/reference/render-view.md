---
layout: default
title: "render_view"
permalink: /reference/render-view/
---

# render_view

*`render_view.py` — Render the game state with the game's own graphics, the way the original draws its map windows.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `render_view.py`]({{ site.baseurl }}/assets/reference/ref/render_view.py)

Render the game state with the game's own graphics, the way the original draws its map windows.

python render_view.py [snapshot index] [out_dir]

Per cell (f_03518): a background tile from the 256-tile sheet (HCEGANT type 9: id 10 the yard, 9 the
house): the surface tile, in the nests (dirt - 0x70) & 0xFF, or a pheromone level 0xF1..0xFF when a
scent view is on; and a foreground sprite: an ant's type byte (caste << 3 | heading) indexes a 128-sprite
sheet (type 9 id 14 the surface, 13 the nests, loaded by f_02b43; the yellow ant uses its type, its queen's tail type + 8).
Sprites are drawn in the yellow ant's colours and recoloured on the way (f_02c21 / f_34b0f): each 12-byte
sprite row is mask, recolour mask, 4 planes; black ants XOR all planes with the recolour mask, red ants
(type 0x80+) only plane 1, the yellow ant none. Reads the user's own extracted resources.

Also: the spider with its legs and fangs (spider, spider_lines), the Map window (render_map) and the yard
window with its actors and colony views (render_yard). See SIM_NOTES "Rendering the map windows".

## At a glance

- **529** lines
- **Classes / hooks:** `Art`
- **19 top-level functions**, including `colour_mode`, `cell`, `render`, `spider_frame`, `_leg_programs`, `spider_lines`, `_line`, `spider` …
- **Original routines referenced:** `f_01823`, `f_02b43`, `f_02c21`, `f_03518`, `f_03de7`, `f_04666`, `f_04c44`, `f_16b58`, `f_1b4ed`, `f_1c62c`, `f_26968`, `f_26bbc` …

## Source

{% raw %}
```python
"""Render the game state with the game's own graphics, the way the original draws its map windows.

python render_view.py [snapshot index] [out_dir]

Per cell (f_03518): a background tile from the 256-tile sheet (HCEGANT type 9: id 10 the yard, 9 the
house): the surface tile, in the nests (dirt - 0x70) & 0xFF, or a pheromone level 0xF1..0xFF when a
scent view is on; and a foreground sprite: an ant's type byte (caste << 3 | heading) indexes a 128-sprite
sheet (type 9 id 14 the surface, 13 the nests, loaded by f_02b43; the yellow ant uses its type, its queen's tail type + 8).
Sprites are drawn in the yellow ant's colours and recoloured on the way (f_02c21 / f_34b0f): each 12-byte
sprite row is mask, recolour mask, 4 planes; black ants XOR all planes with the recolour mask, red ants
(type 0x80+) only plane 1, the yellow ant none. Reads the user's own extracted resources.

Also: the spider with its legs and fangs (spider, spider_lines), the Map window (render_map) and the yard
window with its actors and colony views (render_yard). See SIM_NOTES "Rendering the map windows".
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
    if view <= 1:
        spider(st, img, art, a0 * 16, b0 * 16)
    write_png(path, len(img[0]), len(img), img)


def spider_frame(st):
    """f_03de7: the spider's bitmap and its offset from its 1/16-cell position G:0F12 / G:0F34 (1 px at
    16 px per cell): walking frame 1000 + G:1004 (offsets T:09BC / T:09C4), or 1050 + G:1042 while its
    state G:0FB8 is 5 (T:09CC / T:09D0). The legs and fangs drawn after it are spider_lines."""
    if st.u16(G, 0xfb8) == 5:
        f = st.u16(G, 0x1042)
        return 1050 + f, st.s8(T, 0x9cc + f), st.s8(T, 0x9d0 + f)
    f = st.u16(G, 0x1004)
    return 1000 + f, st.s8(T, 0x9bc + f), st.s8(T, 0x9c4 + f)


LEGS_JSON = os.path.join(HERE, '..', 're', 'build', 'spider_legs.json')    # tools/re/polylines.py


def _leg_programs():
    """The move-to / line-to programs of f_04c44 (legs) and f_04666 (fangs), extracted from the user's EXE
    by tools/re/polylines.py into the git-ignored build directory (generated on first use)."""
    import json
    if not os.path.exists(LEGS_JSON):
        sys.path.insert(0, os.path.join(HERE, '..', 're'))
        import polylines
        sys.argv = [sys.argv[0]]
        polylines.main()
    return json.load(open(LEGS_JSON))


def spider_lines(st, jitter=0, programs=None):
    """f_04c44 + f_04666 as line segments ((x0, y0, x1, y1), colour) around the spider's position
    (G:0F12, G:0F34), drawn after the body unless the spider's state G:0FB8 is 5.
    Legs: 8 per heading G:1004, frame si = G:1042 & 7 for one side and di = (si + 4) & 7 for the other.
    Fangs: si = `jitter`, which the original draws as Rand(4) when G:0FB8 > 1 or G:06AC >= 6 (else 0).
    Colour 15; the fangs are colour 1 when the player is the spider (G:0A06 == 1)."""
    if st.u16(G, 0xfb8) == 5:
        return []
    programs = programs or _leg_programs()
    x, y, heading = st.s16(G, 0xf12), st.s16(G, 0xf34), st.u16(G, 0x1004) & 7
    frame = st.u16(G, 0x1042) & 7
    out = []
    for name, idx, colour in (('f_04c44', {'si': frame, 'di': (frame + 4) & 7}, 15),
                              ('f_04666', {'si': jitter}, 1 if st.u16(G, 0xa06) == 1 else 15)):
        pen = None

        def term(t):
            base, k, table, reg, sign = t
            v = (x if base == 'x' else y) + k
            if table is not None:
                v += sign * st.s8(T, table + (idx[reg] if reg else 0))
            return v
        for op, tx, ty in programs[name]['cases'][heading]:
            p = (term(tx), term(ty))
            if op == 'line' and pen is not None:
                out.append(((pen[0], pen[1], p[0], p[1]), colour))
            pen = p
    return out


def _line(img, x0, y0, x1, y1, rgb):
    """Bresenham, both ends included (the original draws with f_16b58; checked by eye)."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        if 0 <= y0 < len(img) and 0 <= x0 < len(img[0]):
            img[y0][x0] = rgb
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def spider(st, img, art, ox, oy, jitter=0):
    import bitmaps
    rid, dx, dy = spider_frame(st)
    path = os.path.join(tiles.EXTRACTED, 'bitmap', f'{rid:05d}.bin')
    if not os.path.exists(path):
        return
    w, h, rows, _ = bitmaps.decode(open(path, 'rb').read(), palette=art.pal)
    x0, y0 = st.s16(G, 0xf12) + dx - ox, st.s16(G, 0xf34) + dy - oy
    for y in range(h):
        for x in range(w):
            if rows[y][x][3] and 0 <= y0 + y < len(img) and 0 <= x0 + x < len(img[0]):
                img[y0 + y][x0 + x] = rows[y][x]
    for (xa, ya, xb, yb), colour in spider_lines(st, jitter):
        r, g, b = art.pal[colour]
        _line(img, xa - ox, ya - oy, xb - ox, yb - oy, (r, g, b, 255))


# ------------------------------------------------------------------------------------------- the map window
# The "Map" window (f_6efd6): one colour byte per cell in a 128 x 64 image (64 x 64 for a nest), stretched
# to G:3856 x G:3858 px per cell (4 x 4 on a 640-wide screen). Its content is T:07C8. The 16-colour tables
# are used when the video mode DS:5A97 has bit 0 clear (EGA/VGA 16 colours; the other tables are 256-colour).
PHER_MAP = {4: (SIM, 0xe09f), 5: (SIM, 0xe89f), 6: (SIM, 0xf09f), 7: (0x4da7, 0), 8: (SIM, 0xd09f)}


def map_cells(st, mode):
    """The map image as rows of colour indices (16-colour path).
    1 surface (f_6e892): occupant ? T:046E[occupant >> 3] : T:030E[tile] (house T:039E);
    2 / 3 black / red nest (f_6ec6e): the yellow ant 1, red ants 3, black ants 15, else T:04A6[dirt >> 2];
    4..8 a pheromone map (f_6eb66; black nest marker, black trail, red nest marker, red trail, alarm),
    64 x 32 cells of 2 x 2 px: v ? 0x10 + (v >> 5) : 0x0B. Colours 0x10..0x17 are drawn by the video
    driver's stretch blit (DS:914C), not decoded yet."""
    if mode == 1:
        ground = 0x39e if st.u16(G, 0xf24) == 1 else 0x30e
        return [[st.u8(T, 0x46e + (o >> 3)) if (o := st.grid(OCC, a, b)) else st.u8(T, ground + st.grid(SURFACE, a, b))
                 for a in range(128)] for b in range(64)]
    if mode in (2, 3):
        dirt, cells = NESTS[mode]
        rows = []
        for b in range(64):
            row = []
            for a in range(64):
                o = st.grid(cells, a, b)
                row.append(st.u8(T, 0x4a6 + (st.grid(dirt, a, b) >> 2)) if o == 0 else
                           1 if o >= 0xfe else 3 if o & 0x80 else 15)
            rows.append(row)
        return rows
    if mode in PHER_MAP:
        seg, base = PHER_MAP[mode]
        rows = [[0] * 128 for _ in range(64)]
        for y in range(32):
            for x in range(64):
                v = st.u8(seg, base + x * 32 + y)
                c = 0x10 + (v >> 5) if v else 0x0b
                for dy in (0, 1):
                    rows[2 * y + dy][2 * x] = rows[2 * y + dy][2 * x + 1] = c
        return rows
    return None                          # mode 0: the yard picture ("Draw map - yard", f_1c62c)


def _blit_bitmap(img, rid, x0, y0, art):
    import bitmaps
    path = os.path.join(tiles.EXTRACTED, 'bitmap', f'{rid:05d}.bin')
    if not os.path.exists(path):
        return
    w, h, rows, _ = bitmaps.decode(open(path, 'rb').read(), palette=art.pal)
    for y in range(h):
        for x in range(w):
            if rows[y][x][3] and 0 <= y0 + y < len(img) and 0 <= x0 + x < len(img[0]):
                img[y0 + y][x0 + x] = rows[y][x]


def render_map(st, mode, path, art=None, cell=4):
    """Write the map window's picture for content `mode` (T:07C8), `cell` px per map byte (4 at 640 x 480).
    On the surface map it also draws, as f_6efd6 does when the window shows the surface and DS:2994 is 0:
    the spider (f_6f505: bitmap 1100 + heading G:1004 at its cell * 4 - 3, while G:0F0C != 0) and the human
    (f_6f5e1: while T:0C3E, sneaker 1200 + T:0C30 at (G:03E0, G:046A) * 4, and while mowing (T:0C28 3 or 4)
    the mower 1210 + (T:0C30 & 1) at (G:0470, G:047A) * 4)."""
    art = art or Art()
    cells = map_cells(st, mode)
    if cells is None:
        return False
    # colours 0x10..0x17 (pheromone strength) are dithered by the driver: shown here as a plain ramp
    ramp = [art.pal[i] for i in (14, 13, 12, 11, 10, 9, 8, 15)]
    img = []
    for row in cells:
        line = []
        for c in row:
            r, g, b = art.pal[c] if c < 16 else ramp[(c - 0x10) & 7]
            line.extend([(r, g, b, 255)] * cell)
        img.extend([line] * cell)
    img = [list(r) for r in img]
    if mode == 1:
        k = cell
        if st.u16(G, 0xf0c):
            _blit_bitmap(img, 1100 + (st.u16(G, 0x1004) & 7), (st.s16(G, 0xf12) >> 4) * k - 3,
                         (st.s16(G, 0xf34) >> 4) * k - 3, art)
        if st.u16(T, 0xc3e):
            _blit_bitmap(img, 1200 + st.u16(T, 0xc30), st.s16(G, 0x3e0) * k, st.s16(G, 0x46a) * k, art)
            if st.u16(T, 0xc28) in (3, 4):
                _blit_bitmap(img, 1210 + (st.u16(T, 0xc30) & 1), st.s16(G, 0x470) * k, st.s16(G, 0x47a) * k, art)
    write_png(path, len(img[0]), len(img), img)
    return True


# ------------------------------------------------------------------------------------------- the yard window
# The yard picture (f_6fc36 → f_6fac7 → f_6fa6c → f_702f7, from the yard map f_7650c / f_01823 and the win
# screen): the background strips 7020..7022 (640-wide 16-colour screens; 7002 otherwise) and a sprite layer
# (G:10DA; f_26968 create, f_26f2d move, f_26bbc remove, f_272c2 composite) with the yard's actors, in yard
# pixels from the window's corner (G:10D2, G:10D4). Per-frame offset tables are signed bytes in DS.

def _ds8(st, off):
    v = st.u8(0x55b3, off)
    return v - 256 if v > 127 else v


def yard_sprites(st, human=True, rain_rng=None):
    """[(bitmap id, x, y)] in drawing order, as f_702f7 places them:
    cat (f_7004e, while G:0254): 1300 + frame G:0244 at (G:02BE, G:032C), frames 10..19 + DS:2AA4 / 2AA8[f],
      20.. + DS:2AA2 / 2AAC[f] (yard.py calls this actor the bird; the game draws it with the cat frames);
    dog (f_6feb3, while T:0C44 == 0): 8500 + G:04E4 at (G:04BE, G:04C6) + DS:2A8E / 2A9A[f] (f < 12) or
      DS:2A42 / 2A46[f];
    human (f_6fc6e, while T:0C32 >= 0, and T:0C28 != 0 unless `human`): 8000 + T:0C32 at (T:0C2C, T:0C2E) +
      DS:2A56 / 2A62[f] (f < 12), DS:2A5A / 2A5E[f] (< 24), DS:2A12 / 2A1E[f] (< 200);
    mower (f_701a5): 8800 parked at (0x62, 0xB5); mowing (T:0C28 3 or 4) 8801 at the human + (0x13, 0xF) on
      frames 0x67..0x69, 8802 at + (-0xF, 0xF) on 0x6D..0x6F, hidden on the others;
    bird crossing (f_6ff93, while G:10A0): 1250 + G:108C at (G:10AC - 10, G:10BA - 3), (+1, +2) on frame 1;
    "For Sale" sign (f_70126, while T:0C44): 1260 at (0xAA, 0xBA);
    while it rains (G:0352): 15 raindrops 7005 at (Rand(400) + 50, Rand(150)) (f_70601) and the mating-flight
      swarms (f_706d0): G:07C8 black queens (7006) and G:0850 red (7007) around the player's patch corner
      (28 col - 10 row + 0xB2, 10 row + 0x2E) + offsets G:0F46 / G:0F84 and G:0FC6 / G:1008 (each frame
      jittered by Rand(3) - 1; drawn here at their current offsets). The raindrops use `rain_rng`
      (random.Random) in place of the game's LFSR."""
    out = []
    s16 = lambda seg, off: st.s16(seg, off)
    if st.u16(G, 0x254):
        f = st.u16(G, 0x244)
        x, y = s16(G, 0x2be), s16(G, 0x32c)
        if 10 <= f < 20:
            x, y = x + _ds8(st, 0x2aa4 + f), y + _ds8(st, 0x2aa8 + f)
        elif f >= 20:
            x, y = x + _ds8(st, 0x2aa2 + f), y + _ds8(st, 0x2aac + f)
        out.append((1300 + f, x, y))
    if st.u16(T, 0xc44) == 0:
        f = st.u16(G, 0x4e4)
        dx, dy = (0x2a8e, 0x2a9a) if f < 12 else (0x2a42, 0x2a46)
        out.append((8500 + f, s16(G, 0x4be) + _ds8(st, dx + f), s16(G, 0x4c6) + _ds8(st, dy + f)))
    f = s16(T, 0xc32)
    mowing = st.u16(T, 0xc28) in (3, 4)
    hx, hy = s16(T, 0xc2c), s16(T, 0xc2e)
    if f >= 0 and (human or st.u16(T, 0xc28) != 0):
        x, y = hx, hy
        for lim, dx, dy in ((12, 0x2a56, 0x2a62), (24, 0x2a5a, 0x2a5e), (200, 0x2a12, 0x2a1e)):
            if f < lim:
                x, y = x + _ds8(st, dx + f), y + _ds8(st, dy + f)
                break
        out.append((8000 + f, x, y))
    if not mowing:
        out.append((8800, 0x62, 0xb5))
    elif 0x67 <= f <= 0x69:
        out.append((8801, hx + 0x13, hy + 0xf))
    elif 0x6d <= f <= 0x6f:
        out.append((8802, hx - 0xf, hy + 0xf))
    if st.u16(G, 0x10a0):
        f = st.u16(G, 0x108c)
        out.append((1250 + f, s16(G, 0x10ac) - 10 + (1 if f else 0), s16(G, 0x10ba) - 3 + (2 if f else 0)))
    if st.u16(T, 0xc44):
        out.append((1260, 0xaa, 0xba))
    if st.u16(G, 0x352):
        import random
        rng = rain_rng or random.Random(0)
        for _ in range(15):
            out.append((7005, rng.randrange(400) + 50, rng.randrange(150)))
        col, row = s16(G, 0x7ca), s16(G, 0x7cc)
        bx, by = 28 * col - 10 * row + 0xb2, 10 * row + 0x2e
        for count, ox, oy, rid in ((0x7c8, 0xf46, 0xf84, 7006), (0x850, 0xfc6, 0x1008, 7007)):
            for i in range(min(16, max(0, s16(G, count)))):
                out.append((rid, bx + st.s8(G, ox + i), by + st.s8(G, oy + i)))
    return out


def yard_colonies(st, view):
    """The colony views of the yard window (f_702f7 with mode >= 2), per patch (col 0..11, row 0..15), patch
    corner (28 col - 10 row, 10 row) from the window's corner; colours are codes for f_1b4ed (low nibble the
    palette colour, high nibble kept: a fill pattern, drawn solid here).
    'strat' (f_70b82, mode 2): the patch's parallelogram (vertices: corner + the words DS:2A42 / 2A44 + 4i)
    filled with DS:2AD2[k], outlined with DS:2ACA[k]; k = 0 black only, 1 both, 2 red only, 3 none.
    'graphic' (f_70cf5): bars of height (strength + 3) >> 2 standing on 10 row + 0x47, 9 px wide, black
    (code 0x0F) at x 28 col - 10 row + 168 and red (0x23) at + 180.
    Returns [('poly', points, fill, frame)] or [('rect', (l, t, r, b), fill)]."""
    out = []
    for col in range(12):
        for row in range(16):
            black, red = st.u8(T, 0xa4 + col * 16 + row), st.u8(T, 0x164 + col * 16 + row)
            x, y = 28 * col - 10 * row, 10 * row
            if view == 'strat':
                k = (0 if red == 0 else 1) if black else (3 if red == 0 else 2)
                pts = [(x + st.s16(0x55b3, 0x2a42 + 4 * i), y + st.s16(0x55b3, 0x2a44 + 4 * i)) for i in range(4)]
                out.append(('poly', pts, st.u16(0x55b3, 0x2ad2 + 2 * k), st.u16(0x55b3, 0x2aca + 2 * k)))
            else:
                for strength, dx, code in ((black, 168, 0x0f), (red, 180, 0x23)):
                    h = (strength + 3) >> 2
                    if h > 0:
                        out.append(('rect', (x + dx, y + 0x47 - h, x + dx + 9, y + 0x47), code))
    return out


def _fill_poly(img, pts, rgb):
    ys = [p[1] for p in pts]
    for yy in range(max(0, min(ys)), min(len(img), max(ys) + 1)):
        xs = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if (y0 <= yy < y1) or (y1 <= yy < y0):
                xs.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for a, b in zip(xs[::2], xs[1::2]):
            for xx in range(max(0, int(round(a))), min(len(img[0]), int(round(b)) + 1)):
                img[yy][xx] = rgb


def _layout(wid):
    sys.path.insert(0, os.path.join(HERE, '..'))
    import layouts
    return layouts.load(wid)


def _bitmap(art, rid):
    import bitmaps
    p = os.path.join(tiles.EXTRACTED, 'bitmap', f'{rid:05d}.bin')
    if not os.path.exists(p):
        return None
    return bitmaps.decode(open(p, 'rb').read(), palette=art.pal)


def render_yard(st, path, art=None, human=True, colonies=None):
    """Write the yard window (layout 25) in screen coordinates, cropped to the window: its frame, the
    toolbar 7010 (item 0x1904), then
    - the yard (view G:035C 0 / 1): the yard picture, items 0x1903 (7000, the house) and 0x190F (7003,
      the lawn; its grid is the patch grid), with yard_sprites at the yard origin G:10D2 / G:10D4 = item
      0x1902's corner + (1, 0) = (65, 83) (set by the code at 0x01002);
    - a colony view (`colonies` 'strat' / 'graphic', G:035C >= 2; f_6fac7 draws the grid strips then, on
      640-wide 16-colour screens): the strips 7020..7022 from (item 0x1902's left, item 0x1914's bottom)
      = (64, 148), with yard_colonies at the same origin."""
    house = not colonies
    art = art or Art()
    win = _layout(25)
    items = {it['id']: it for it in win['items']}
    wl, wt, wr, wb = win['rect']
    img = [[tuple(art.pal[12]) + (255,)] * (wr - wl) for _ in range(wb - wt)]
    img = [list(r) for r in img]

    def put(rid, x, y):
        bm = _bitmap(art, rid)
        if bm is None:
            return False
        w, h, rows, _ = bm
        for yy in range(h):
            for xx in range(w):
                px = rows[yy][xx]
                if px[3] and 0 <= y - wt + yy < len(img) and 0 <= x - wl + xx < len(img[0]):
                    img[y - wt + yy][x - wl + xx] = tuple(px)
        return True
    put(7010, *items[0x1904]['rect'][:2])
    ox, oy = items[0x1902]['rect'][0] + 1, items[0x1902]['rect'][1]
    if house:
        put(7000, *items[0x1903]['rect'][:2])
        put(7003, *items[0x190f]['rect'][:2])
        for rid, x, y in yard_sprites(st, human):
            put(rid, x + ox, y + oy)
    else:
        x, y = items[0x1902]['rect'][0], items[0x1914]['rect'][3]
        for rid in (7020, 7021, 7022):
            bm = _bitmap(art, rid)
            if bm is None:
                return False
            put(rid, x, y)
            y += bm[1]
        if colonies:
            rgb = lambda code: tuple(art.pal[code & 0xf]) + (255,)
            for shape in yard_colonies(st, colonies):
                if shape[0] == 'poly':
                    pts = [(x + ox - wl, y + oy - wt) for x, y in shape[1]]
                    _fill_poly(img, pts, rgb(shape[2]))
                    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
                        _line(img, x0, y0, x1, y1, rgb(shape[3]))
                else:
                    l, t, r, b = shape[1]
                    for yy in range(t + oy - wt, b + oy - wt):
                        for xx in range(l + ox - wl, r + ox - wl):
                            if 0 <= yy < len(img) and 0 <= xx < len(img[0]):
                                img[yy][xx] = rgb(shape[2])
    write_png(path, len(img[0]), len(img), img)
    return True


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
    for mode, name in ((1, 'map_surface'), (2, 'map_black_nest'), (3, 'map_red_nest'), (5, 'map_black_trail')):
        p = os.path.join(out, f'{name}_{tick}.png')
        if render_map(st, mode, p, art):
            print('wrote', p)
    p = os.path.join(out, f'yard_{tick}.png')
    if render_yard(st, p, art):
        print('wrote', p)


if __name__ == '__main__':
    main()
```
{% endraw %}
