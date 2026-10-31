"""Builds the clean pack (ROADMAP A1 / A4) from the makers' source files.

    python tools/clean_pack/build.py                       # the clean pack; lists what is still missing
    python tools/clean_pack/build.py --fallback=<zip>      # a dev pack: missing resources taken from <zip>
    python tools/clean_pack/build.py --roundtrip=<zip>     # check enc_bitmap against every type-2 bitmap in <zip>; builds nothing

Sources: remake/game/assets/clean/src/<category>/ (written by the makers, docs/clean_pack/*.md). Output:
- without --fallback: remake/game/assets/clean/clean_pack.zip, only when nothing is missing (else the list and exit 1;
  --partial writes what exists to remake/build/partial_pack.zip);
- with --fallback (for example remake/build/original_pack.zip from `OpenSimAnt.Replay --export-pack`, the player's own
  files): remake/build/dev_pack.zip (git-ignored: it holds original data). Run the game on it with
  `-- --clean --pack=remake/build/dev_pack.zip` to see each new category in place before the pack is complete.

The pack's layout is OriginalFiles(byte[])'s: ARCHIVE/<type>/<id>.bin in the original's formats (FILE_FORMATS.md),
FONT/<n>.bin, EXE/<name>.bin, EXE/version.txt. Every source is checked against the measurements in
docs/clean_pack/data/*.json (sizes must match: the engine places things by them).

Source formats so far:
- palette/palette.json: the 16 colours in index order (hex R G B, the standard Apple Mac 16-colour palette) ->
  HCEGANT/15/0.bin: a little-endian u16 count (16, as the original's entry), then R, G, B per colour (50 bytes, as the original's entry; nothing
  follows the colours; MapArt reads it).
- .pix: pixel art as text. One row per line, one character per pixel: 0-9 a-f = palette index (the Mac 16-colour
  palette, 0 white .. 15 black), '.' = transparent. Lines starting with '#' are comments.
- bitmaps/<ARCHIVE>_<id>.pix (docs/clean_pack/ui_bitmaps.md and later bitmap specs): one .pix per HCEGANT / SHARED type-2
  bitmap, e.g. HCEGANT_4600.pix, exactly the measured size (bitmaps.json). A bitmap measured "masked" must contain '.'
  pixels (they become the mask plane: the game draws mode-3 bitmaps through it), any other must contain none; a 1-plane
  bitmap (21004, 21005) allows only 0 and f. -> ARCHIVE/2/<id>.bin. --roundtrip=<zip> checks the encoder against the
  originals of a pack.
- sprites/surface.pix, nest.pix (256 x 128: sprite n at column n % 16, row n // 16, 16 x 16 each; 0-9 a-f = the
  yellow ant's colour, '.' = transparent) with surface_recolour.pix, nest_recolour.pix (same size: 1 = recoloured for
  the black and red ants, 0 or '.' = not).
- fonts/font<n>.pix + font<n>.json (n = the game's font number 0..5; docs/clean_pack/fonts.md): the .pix is the glyph
  grid, 16 cells across, character c in column c % 16, row c // 16 (so character 65 is the second cell of row 4); a
  cell is (picture width / 16) x (picture height / rows) pixels, rows = ceil(characters / 16), the cell's left edge
  is the pen position and its top row the font's row 0; 'f' = ink, '.' = none. The .json holds what the picture
  cannot: {"advances": [pen advance per character 0 .. N-1], "ascent": rows above the baseline (fonts 2..5),
  "missing_advance": the advance of every character the font does not draw, N-1 and later included (fonts 2..5),
  "first_index": the number the game's own format counts its first character as (font 0 only: 1; default 0)}.
  Everything else is derived: the height from the picture, a glyph's width and offset from where its ink lies, the
  header fields, the tables. font0 -> SHARED/11/0, font1 -> SHARED/11/1 (the game's own format: a bitmap of
  ceil(cell width / 8) bytes per row for each character that has ink or an advance), font2..font5 -> FONT/1..4
  (Apple FONT: the strike is the ink columns of all glyphs side by side, kernMax 0, fontType 0x9000; the optional
  tables behind the offset / width table are not written, the game never reads them).
- balloon/balloon.pix (docs/clean_pack/balloon.md): the speech balloon's 11 pieces side by side, 88 x 8, piece n at
  columns 8n .. 8n+7 in the order top_left, top_right, top, right, left, bottom_left, bottom_right, bottom, inside,
  tail_right, tail_left. Only '0' (white inside), 'f' (black outline) and '.' (transparent) are used. -> EXE/balloon.bin
  (176 bytes: per piece 8 rows of two bytes, the inside plane (1 = white) then the shape plane (1 = opaque), MSB =
  leftmost pixel). The pieces must join as Balloon.Make lays them out (balloon_seams checks it).
- spider/legs.json (docs/clean_pack/spider_legs.md): {"north": view, "north_east": view}; a view is {"legs": [4 legs],
  "fangs": [4 frames]}; a leg is 8 frames, each a polyline of 3 integer [x, y] points [attach, joint, tip]; a fang frame
  is a polyline of 3 points [base, p1, p2]. Points are pixels from the spider's centre (x right, y down), |x|, |y| <= 48,
  for the spider's right side facing that view; the left side is the mirror image at frame + 4, the other 6 headings
  are made by the game from these two views (turned or flipped). A leg keeps its attach point in all 8 frames; a fang's
  base is the fixed anchor [4, -10] ('north') / [10, -3] ('north_east'), which is not stored. -> EXE/spiderlegs.bin
  (304 bytes of signed bytes; layout in enc_spiderlegs).
- version/version.txt: one line of printable ASCII, at most 72 characters (the Ctrl+Alt+V alert) -> EXE/version.txt.
"""
import json, os, struct, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'remake', 'game', 'assets', 'clean', 'src')
DATA = os.path.join(ROOT, 'docs', 'clean_pack', 'data')
OUT_CLEAN = os.path.join(ROOT, 'remake', 'game', 'assets', 'clean', 'clean_pack.zip')
OUT_DEV = os.path.join(ROOT, 'remake', 'build', 'dev_pack.zip')


def data(name):
    with open(os.path.join(DATA, name + '.json')) as f:
        return json.load(f)


# ------------------------------------------------------------------------------------------------ source readers
def parse_pix(lines, what='pix'):
    """(width, height, rows) from the lines of a .pix: rows of palette indices, None = transparent."""
    rows = []
    for line in lines:
        line = line.rstrip('\r\n')
        if not line or line.startswith('#'):
            continue
        rows.append([None if c == '.' else int(c, 16) for c in line])
    w = len(rows[0]) if rows else 0
    if any(len(r) != w for r in rows):
        raise ValueError('%s: rows of different lengths' % what)
    return w, len(rows), rows


def read_pix(path):
    """(width, height, rows): rows of palette indices, None = transparent."""
    with open(path) as f:
        return parse_pix(f, path)


# ------------------------------------------------------------------------------------------------ encoders
def bits(row, test):
    """A plane row: ceil(w / 8) bytes, MSB = leftmost pixel."""
    out = bytearray((len(row) + 7) // 8)
    for x, c in enumerate(row):
        if test(c):
            out[x >> 3] |= 0x80 >> (x & 7)
    return bytes(out)


def enc_bitmap(w, h, rows, planes):
    """HCEGANT / SHARED type 2 (FILE_FORMATS "Bitmap format"); 1-plane bitmaps: 1 = black ink (index 15)."""
    masked = any(c is None for r in rows for c in r)
    body = bytearray()
    for r in rows:
        if masked:
            body += bits(r, lambda c: c is not None)
        if planes == 1:
            body += bits(r, lambda c: c is not None and c >= 8)
        else:
            for p in range(4):
                body += bits(r, lambda c, p=p: c is not None and (c >> p) & 1)
    return struct.pack('<HBBIHH', 3 if masked else 0, planes, 0, len(body), w, h) + bytes(body)


def enc_cursor(w, h, rows):
    """HCEGANT type 8 (u16 w, h; per row 4 planes) and type 7 (u16 w, h; 1 bit per pixel, 1 = transparent)."""
    img = bytearray(struct.pack('<HH', w, h))
    mask = bytearray(struct.pack('<HH', w, h))
    for r in rows:
        for p in range(4):
            img += bits(r, lambda c, p=p: c is not None and (c >> p) & 1)
        mask += bits(r, lambda c: c is None)
    return bytes(img), bytes(mask)


# ------------------------------------------------------------------------------------------------ categories
def enc_palette(hexes):
    """HCEGANT type 15 id 0 (OpenSimAnt.Data/MapArt.cs): u16 little-endian count as the original stores it (MapArt
    reads it big-endian, 0x1000, and caps it at 16), then R, G, B bytes per colour; nothing
    follows the colours (the original's entry is 50 bytes, 2 + 16 x 3)."""
    return struct.pack('<H', len(hexes)) + b''.join(bytes.fromhex(h) for h in hexes)


def cat_palette(errors):
    """src/palette/palette.json -> HCEGANT/15/0.bin."""
    path = os.path.join(SRC, 'palette', 'palette.json')
    if not os.path.exists(path):
        return
    with open(path) as f:
        cols = json.load(f).get('colours', [])
    hexes = [c.get('hex') for c in cols]
    if [c.get('index') for c in cols] != list(range(16)) or any(not isinstance(h, str) or len(h) != 6 for h in hexes):
        errors.append('palette/palette.json: 16 colours, index 0..15 in order, each a 6-digit hex')
        return
    try:
        blob = enc_palette(hexes)
    except ValueError:
        errors.append('palette/palette.json: a colour is not hex')
        return
    yield 'HCEGANT/15/0.bin', blob


def dec_bitmap(d):
    """HCEGANT / SHARED type 2 -> (width, height, planes, masked, rows): rows of palette indices, None = transparent
    (a masked bitmap's mask bit 0); a 1-plane bitmap's ink (1) is index 15, its paper index 0. The inverse of
    enc_bitmap (and OpenSimAnt.Data Bitmaps.Decode); only used to check that the encoder reads the originals back."""
    mode, planes, _flags, _size, w, h = struct.unpack_from('<HBBIHH', d, 0)
    rb, masked = (w + 7) // 8, mode == 3
    np_ = planes + (1 if masked else 0)
    rows = []
    for y in range(h):
        pl = [d[12 + (y * np_ + p) * rb:12 + (y * np_ + p + 1) * rb] for p in range(np_)]
        row = []
        for x in range(w):
            bit, bx = 0x80 >> (x & 7), x >> 3
            if masked and not pl[0][bx] & bit:
                row.append(None)
            elif planes == 1:
                row.append(15 if pl[-1][bx] & bit else 0)
            else:
                row.append(sum(1 << p for p in range(planes) if pl[(1 if masked else 0) + p][bx] & bit))
        rows.append(row)
    return w, h, planes, masked, rows


def check_bitmap_roundtrip(zip_path):
    """--roundtrip=<zip>: every bitmap of the measurements (bitmaps.json) in the pack <zip> (for example
    remake/build/original_pack.zip) is decoded, written as .pix text, read back with read_pix, encoded with
    enc_bitmap and decoded again; width, height, planes, masked and every pixel must survive. The header's size hint and
    flags and the padding bits are not stored by the encoder, so the bytes may differ (the game ignores those). Returns
    (checked, problems)."""
    checked, problems = 0, []
    with zipfile.ZipFile(zip_path) as z:
        for m in data('bitmaps'):
            name = '%s/2/%d.bin' % (m['archive'], m['id'])
            if name not in z.namelist():
                problems.append('%s: not in the pack' % name)
                continue
            w, h, planes, masked, rows = dec_bitmap(z.read(name))
            if (w, h, planes, masked) != (m['width'], m['height'], m['planes'], m['masked']):
                problems.append('%s: %dx%d, %d planes, masked %s; the measurements say %dx%d, %d, %s'
                                % (name, w, h, planes, masked, m['width'], m['height'], m['planes'], m['masked']))
                continue
            text = [''.join('.' if c is None else '%x' % c for c in r) for r in rows]
            w2, h2, rows2 = parse_pix(text)
            blob = enc_bitmap(w2, h2, rows2, planes)
            back = dec_bitmap(blob)
            checked += 1
            if back != (w, h, planes, masked, rows):
                problems.append('%s: the pixels do not survive the encoder' % name)
    return checked, problems


def cat_bitmaps(errors):
    """src/bitmaps/<ARCHIVE>_<id>.pix -> ARCHIVE/2/<id>.bin, sized as measured. A bitmap the game draws masked (the
    measurements' "masked") must have at least one '.' (transparent) pixel and any other must have none; a 1-plane
    bitmap is black ink on white paper, so only 0 (white) and f (black) are allowed in it."""
    want = {(b['archive'], b['id']): b for b in data('bitmaps')}
    d = os.path.join(SRC, 'bitmaps')
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith('.pix'):
            continue
        arch, ident = name[:-4].split('_')
        key = (arch, int(ident))
        if key not in want:
            errors.append('bitmaps/%s: no such bitmap in the game' % name)
            continue
        w, h, rows = read_pix(os.path.join(d, name))
        m = want[key]
        if (w, h) != (m['width'], m['height']):
            errors.append('bitmaps/%s: %d x %d, the spec says %d x %d' % (name, w, h, m['width'], m['height']))
            continue
        has_hole = any(c is None for r in rows for c in r)
        if has_hole != m['masked']:
            errors.append('bitmaps/%s: %s' % (name, "must have transparent ('.') pixels (it is drawn masked)" if m['masked']
                                              else "must be opaque, no '.' pixels"))
            continue
        if m['planes'] == 1 and any(c not in (0, 15) for r in rows for c in r):
            errors.append("bitmaps/%s: a 1-plane bitmap allows only '0' (white) and 'f' (black)" % name)
            continue
        yield '%s/2/%d.bin' % key, enc_bitmap(w, h, rows, m['planes'])


def cat_cursors(errors):
    """src/cursors/<id>.pix -> HCEGANT/8/<id>.bin and its mask (id 0's in SHARED/7, the others in HCEGANT/7)."""
    want = {c['id']: c for c in data('cursors') if c['type'] == 8}
    d = os.path.join(SRC, 'cursors')
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith('.pix'):
            continue
        ident = int(name[:-4])
        w, h, rows = read_pix(os.path.join(d, name))
        m = want.get(ident)
        if m is None or (w, h) != (m['width'], m['height']):
            errors.append('cursors/%s: the spec says %s' % (name, m and '%d x %d' % (m['width'], m['height'])))
            continue
        img, mask = enc_cursor(w, h, rows)
        yield 'HCEGANT/8/%d.bin' % ident, img
        yield ('SHARED/7/0.bin' if ident == 0 else 'HCEGANT/7/%d.bin' % ident), mask


def enc_tiles(rows):
    """HCEGANT type 9 tile sheet from a 256 x 256 picture: tile n at column n % 16, row n / 16; per tile 16 rows of
    planes 0..3, 2 bytes each (FILE_FORMATS "Map tiles and ant sprites")."""
    out = bytearray()
    for n in range(256):
        tx, ty = (n % 16) * 16, (n // 16) * 16
        for y in range(16):
            row = rows[ty + y][tx:tx + 16]
            for p in range(4):
                out += bits(row, lambda c, p=p: (c >> p) & 1)
    return bytes(out)


def cat_tiles(errors):
    """src/tiles/yard.pix, house.pix (256 x 256, opaque) -> HCEGANT/9/10.bin, HCEGANT/9/9.bin."""
    d = os.path.join(SRC, 'tiles')
    for name, ident in (('yard.pix', 10), ('house.pix', 9)):
        path = os.path.join(d, name)
        if not os.path.exists(path):
            continue
        w, h, rows = read_pix(path)
        if (w, h) != (256, 256) or any(c is None for r in rows for c in r):
            errors.append('tiles/%s: must be 256 x 256 with no transparent pixels' % name)
            continue
        yield 'HCEGANT/9/%d.bin' % ident, enc_tiles(rows)


def enc_sprites(rows, recolour):
    """HCEGANT type 9 sprite sheet from a 256 x 128 picture and its recolour mask (1 = recoloured): sprite n at column
    n % 16, row n / 16; per sprite 16 rows of mask, recolour mask, planes 0..3, 2 bytes each (FILE_FORMATS "Map tiles
    and ant sprites"). A transparent pixel is mask 0 and planes 0."""
    out = bytearray()
    for n in range(128):
        sx, sy = (n % 16) * 16, (n // 16) * 16
        for y in range(16):
            row = rows[sy + y][sx:sx + 16]
            out += bits(row, lambda c: c is not None)
            out += bits(recolour[sy + y][sx:sx + 16], lambda c: c == 1)
            for p in range(4):
                out += bits(row, lambda c, p=p: c is not None and (c >> p) & 1)
    return bytes(out)


def cat_sprites(errors):
    """src/sprites/surface.pix, nest.pix (256 x 128) with surface_recolour.pix, nest_recolour.pix -> HCEGANT/9/14.bin,
    HCEGANT/9/13.bin."""
    d = os.path.join(SRC, 'sprites')
    for name, ident in (('surface', 14), ('nest', 13)):
        path = os.path.join(d, name + '.pix')
        if not os.path.exists(path):
            continue
        rec_name = name + '_recolour.pix'
        rec_path = os.path.join(d, rec_name)
        if not os.path.exists(rec_path):
            errors.append('sprites/%s: the recolour file %s is missing' % (name + '.pix', rec_name))
            continue
        w, h, rows = read_pix(path)
        rw, rh, rec = read_pix(rec_path)
        if (w, h) != (256, 128) or (rw, rh) != (256, 128):
            errors.append('sprites/%s and %s: must be 256 x 128' % (name + '.pix', rec_name))
            continue
        if any(c not in (None, 0, 1) for r in rec for c in r):
            errors.append('sprites/%s: only 1 (recoloured) and 0 or . (not) are allowed' % rec_name)
            continue
        hole = next(((x, y) for y in range(h) for x in range(w) if rec[y][x] == 1 and rows[y][x] is None), None)
        if hole:
            errors.append('sprites/%s: recoloured at (%d, %d), a transparent pixel' % (rec_name, hole[0], hole[1]))
            continue
        yield 'HCEGANT/9/%d.bin' % ident, enc_sprites(rows, rec)


def enc_font_own(cells, advances, first_index, h, cw):
    """SHARED type 11, the game's own format (OpenSimAnt.Data/BitmapFont.cs, tools/fonts.py): +0 u16 (250 - first),
    +2 height, +4 first; +6 255 offsets, +0x204 255 flags (bytes per row of a character that has a glyph, else 0),
    +0x402 255 advances, +0x600 the glyphs in character order, h rows of ceil(cw / 8) bytes. A character has a glyph when
    its cell has ink or its advance is not 0; any other one points at the next glyph's data (or the end)."""
    bpr, n = (cw + 7) // 8, len(advances)
    has = [any(any(r) for r in cells[c]) or advances[c] != 0 for c in range(n)]
    data, start = bytearray(), {}
    for c in range(n):
        if has[c]:
            start[c] = 0x600 + len(data)
            for r in cells[c]:
                data += bits(r, lambda v: v == 1)
    end = 0x600 + len(data)
    offs, flags, adv = [], [], []
    for i in range(255):
        c = first_index + i
        offs.append(next((start[k] for k in range(c, n) if has[k]), end))
        flags.append(bpr if c < n and has[c] else 0)
        adv.append(advances[c] if c < n else 0)
    return (struct.pack('<3H', 250 - first_index, h, first_index) + struct.pack('<255H', *offs)
            + struct.pack('<255H', *flags) + struct.pack('<255H', *adv) + bytes(data))


def enc_font_mac(cells, advances, missing, ascent, h, cw):
    """FONT / SHARED 11 ids 2, 3, the Apple FONT format (big-endian; tools/fonts.py): 13 header words, the strike (the
    glyphs' ink columns side by side, h rows of rowWords * 2 bytes), the location table (n + 2 words: where each
    character's columns start, then the missing glyph's start, then the end), the offset / width table (n + 2 words: high
    byte the glyph's x offset from the pen, low byte its advance, 0xFFFF = no glyph, then the missing glyph's entry and
    0xFFFF). kernMax is 0, so a glyph is drawn at pen + offset. A character with no ink and the missing advance has no
    glyph; the missing glyph has no columns."""
    n = len(advances)
    strips, loc, ow, x = [], [], [], 0
    for c in range(n):
        cols = [i for i in range(cw) if any(cells[c][r][i] for r in range(h))]
        loc.append(x)
        if not cols and advances[c] == missing:
            ow.append(0xffff)
            continue
        x0, x1 = (cols[0], cols[-1] + 1) if cols else (0, 0)
        ow.append(x0 << 8 | advances[c])
        strips.append((c, x0, x1))
        x += x1 - x0
    loc += [x, x]
    ow += [missing, 0xffff]
    rb = 2 * ((x + 15) // 16)
    strike = bytearray(rb * h)
    for r in range(h):
        px = 0
        for c, x0, x1 in strips:
            for i in range(x0, x1):
                if cells[c][r][i]:
                    strike[r * rb + (px >> 3)] |= 0x80 >> (px & 7)
                px += 1
    owt = (26 + rb * h + 2 * (n + 2) - 16) // 2
    ink_w = max([x1 for _, _, x1 in strips] + [0])
    head = struct.pack('>H12h', 0x9000, 0, n - 1, max(advances + [missing]), 0, -(h - ascent), ink_w, h, owt, ascent,
                       h - ascent, 0, rb // 2)
    return head + bytes(strike) + struct.pack('>%dH' % (n + 2), *loc) + struct.pack('>%dH' % (n + 2), *ow)


FONT_FILES = {0: 'SHARED/11/0.bin', 1: 'SHARED/11/1.bin', 2: 'FONT/1.bin', 3: 'FONT/2.bin', 4: 'FONT/3.bin', 5: 'FONT/4.bin'}
FONT_SOURCES = {0: 'SHARED 11 0', 1: 'SHARED 11 1', 2: 'FONT1', 3: 'FONT2', 4: 'FONT3', 5: 'FONT4'}


def cat_fonts(errors):
    """src/fonts/font<n>.pix + .json -> the fonts the game loads (FONT_FILES), checked against the measurements."""
    want = {m['source']: m for m in data('fonts')}
    d = os.path.join(SRC, 'fonts')
    for num in range(6):
        name = 'font%d' % num
        pix, js = os.path.join(d, name + '.pix'), os.path.join(d, name + '.json')
        if not os.path.exists(pix) and not os.path.exists(js):
            continue
        if not (os.path.exists(pix) and os.path.exists(js)):
            errors.append('fonts/%s: needs both %s.pix and %s.json' % (name, name, name))
            continue
        with open(js) as f:
            meta = json.load(f)
        mac = num >= 2
        keys = {'advances', 'ascent', 'missing_advance'} if mac else {'advances', 'first_index'}
        need = {'advances', 'ascent', 'missing_advance'} if mac else {'advances'}
        if set(meta) - keys or need - set(meta):
            errors.append('fonts/%s.json: the keys must be %s (optional: %s)' % (name, sorted(need), sorted(keys - need)))
            continue
        adv, missing, first_index = meta['advances'], meta.get('missing_advance', 0), meta.get('first_index', 0)
        if not (1 <= len(adv) <= 256) or any(not isinstance(a, int) or not 0 <= a <= 255 for a in adv + [missing]):
            errors.append('fonts/%s.json: advances are 1 to 256 integers 0..255' % name)
            continue
        w, ph, rows = read_pix(pix)
        grid_rows = (len(adv) + 15) // 16
        if w == 0 or w % 16 or ph % grid_rows:
            errors.append('fonts/%s.pix: %d x %d is not %d rows of 16 equal cells' % (name, w, ph, grid_rows))
            continue
        cw, h = w // 16, ph // grid_rows
        if any(c not in (None, 15) for r in rows for c in r):
            errors.append("fonts/%s.pix: only 'f' (ink) and '.' are allowed" % name)
            continue
        cells = [[[0 if rows[(c // 16) * h + y][(c % 16) * cw + x] is None else 1 for x in range(cw)] for y in range(h)]
                 for c in range(grid_rows * 16)]
        stray = next((c for c in range(len(adv), len(cells)) if any(any(r) for r in cells[c])), None)
        if stray is not None:
            errors.append('fonts/%s.pix: ink in the cell of character %d, beyond the %d characters' % (name, stray, len(adv)))
            continue
        cells = cells[:len(adv)]
        if not mac and (first_index > 255 or any(adv[c] or any(any(r) for r in cells[c]) for c in range(min(first_index, len(adv))))
                        or len(adv) - 1 - first_index > 254):
            errors.append('fonts/%s: first_index %d: characters before it must be empty, those after it fit 255 entries'
                          % (name, first_index))
            continue
        m = want[FONT_SOURCES[num]]
        ascent = meta['ascent'] if mac else h
        if (h, ascent) != (m['height'], m['ascent']):
            errors.append('fonts/%s: height %d, ascent %d; the spec says %d, %d' % (name, h, ascent, m['height'], m['ascent']))
            continue
        # the advance the game will measure for every character 0..255, against the measurements (the junk entries of the
        # game's own fonts, values above 100, are not widths)
        got = [(adv[c] if c < len(adv) else missing) if mac else
               (adv[c] if first_index <= c < len(adv) else 0) for c in range(256)]
        bad = [c for c in range(256) if m['advances'][c] <= 100 and got[c] != m['advances'][c]]
        if bad:
            errors.append('fonts/%s.json: advance of character %d is %d, the spec says %d (%d wrong in all)'
                          % (name, bad[0], got[bad[0]], m['advances'][bad[0]], len(bad)))
            continue
        yield FONT_FILES[num], (enc_font_mac(cells, adv, missing, ascent, h, cw) if mac
                                else enc_font_own(cells, adv, first_index, h, cw))


BALLOON_PIECES = ['top_left', 'top_right', 'top', 'right', 'left', 'bottom_left', 'bottom_right', 'bottom', 'inside',
                  'tail_right', 'tail_left']


def enc_balloon(rows):
    """EXE/balloon.bin (OpenSimAnt.Data/Balloon.cs; docs/clean_pack/balloon.md) from the 88 x 8 strip of the 11 pieces
    (BALLOON_PIECES, in this order): per piece 8 rows of two bytes, MSB = leftmost pixel: first the inside plane (1 =
    white), then the shape plane (1 = opaque: white inside or black outline; 0 = transparent). 176 bytes."""
    out = bytearray()
    for i in range(11):
        for r in rows:
            seg = r[8 * i:8 * i + 8]
            out += bits(seg, lambda c: c == 0) + bits(seg, lambda c: c is not None)
    return bytes(out)


def balloon_seams(rows):
    """Why the 11 pieces do not join (a list of sentences), by how Balloon.Make lays them out: left / right / inside
    are tiled down any number of rows and top / bottom / inside across any number of cells (so they must be uniform
    that way), and a piece must continue its neighbour at the shared edge."""
    P = {n: [r[8 * i:8 * i + 8] for r in rows] for i, n in enumerate(BALLOON_PIECES)}
    col = lambda n, x: [row[x] for row in P[n]]
    why = []
    for n in ('left', 'right', 'inside'):
        if any(P[n][y] != P[n][0] for y in range(8)):
            why.append('%s: all 8 rows must be the same (it is tiled downwards)' % n)
    for n in ('top', 'bottom', 'inside'):
        if any(col(n, x) != col(n, 0) for x in range(8)):
            why.append('%s: all 8 columns must be the same (it is tiled across)' % n)
    # a piece's last column continues the next piece's first; a piece's last row continues the one below
    for a, b in (('top_left', 'top'), ('top', 'top_right'), ('left', 'inside'), ('inside', 'right'),
                 ('bottom_left', 'bottom'), ('bottom', 'bottom_right')):
        if col(a, 7) != col(b, 0):
            why.append('%s | %s: the right column of the first must equal the left column of the second' % (a, b))
    for a, b in (('top_left', 'left'), ('top', 'inside'), ('top_right', 'right')):
        if P[a][7] != P[b][0]:
            why.append('%s over %s: the bottom row of the first must equal the top row of the second' % (a, b))
    for a, b in (('left', 'bottom_left'), ('inside', 'bottom'), ('right', 'bottom_right'), ('inside', 'tail_left'),
                 ('inside', 'tail_right')):
        if P[a][0] != P[b][0]:
            why.append('%s / %s: the top row of both must be equal (the bottom pieces are laid over the tiles)' % (a, b))
    # a tail replaces a bottom piece and runs on below the outline, so only its rows 0..3 (down to the outline) join
    for a, b in (('bottom_left', 'tail_left'), ('tail_left', 'bottom'), ('bottom', 'tail_right'),
                 ('tail_right', 'bottom')):
        if col(a, 7)[:4] != col(b, 0)[:4]:
            why.append('%s | %s: rows 0..3 of the right column of the first must equal those of the left column of the second' % (a, b))
    for n in ('tail_left', 'tail_right'):
        if any(P[n][y] != P['inside'][0] for y in range(3)):
            why.append('%s: rows 0..2 must be the inside, as the bottom piece they replace' % n)
    return why


def cat_balloon(errors):
    """src/balloon/balloon.pix (88 x 8; 0 white, f black, . transparent) -> EXE/balloon.bin."""
    path = os.path.join(SRC, 'balloon', 'balloon.pix')
    if not os.path.exists(path):
        return
    w, h, rows = read_pix(path)
    if (w, h) != (88, 8):
        errors.append('balloon/balloon.pix: %d x %d, must be 88 x 8 (11 pieces of 8 x 8)' % (w, h))
        return
    if any(c not in (None, 0, 15) for r in rows for c in r):
        errors.append("balloon/balloon.pix: only '0' (white), 'f' (black) and '.' are allowed")
        return
    why = balloon_seams(rows)
    if why:
        errors.extend('balloon/balloon.pix: ' + s for s in why)
        return
    yield 'EXE/balloon.bin', enc_balloon(rows)


SPIDER_VIEWS = ('north', 'north_east')
SPIDER_ANCHORS = {'north': (4, -10), 'north_east': (10, -3)}    # where the code starts each view's first fang (not stored)
SPIDER_LIMIT = 48                                               # |x|, |y| of every stored point (pixels from the centre)


def enc_spiderlegs(src):
    """EXE/spiderlegs.bin (OpenSimAnt.Data/SpiderLegs.cs, tools/ref/gen_spider_legs_cs.py; docs/clean_pack/spider_legs.md),
    304 bytes of signed bytes, from {"north": view, "north_east": view}; a view is {"legs": [4 legs], "fangs": [4 frames]}, a
    leg is 8 frames of [attach, joint, tip], a fang frame is [base, p1, p2] (base not stored). The game draws the other 6
    headings from these two views by turning / flipping them (the engine's code, not the file) and the spider's other side
    as the mirror image of this side at frame + 4. Layout: 0 'north' fangs: x1[4] y1[4] x2[4] y2[4] (p1, p2 per frame);
    16 'north_east' fangs; 32 'north' legs: attach x[4] y[4], then joint x[4 legs][8 frames] ... 40 + 16 * leg + 8 * (0
    joint, 1 tip) + frame, y the same + 64; 168 'north_east' legs: attach x[4] y[4], then 176 + 16 * leg + 64 * (0 joint,
    1 tip) + frame for x, +8 for y."""
    out = bytearray(304)
    for v, view in enumerate(SPIDER_VIEWS):
        s = src[view]
        fang, legs = 16 * v, (32, 168)[v]
        for f in range(4):
            for j in range(2):
                for c in range(2):
                    out[fang + 8 * j + 4 * c + f] = s['fangs'][f][1 + j][c] & 255
        for k in range(4):
            for c in range(2):
                out[legs + 4 * c + k] = s['legs'][k][0][0][c] & 255
            for f in range(8):
                for j in range(2):
                    p = s['legs'][k][f][1 + j]
                    if v == 0:
                        out[legs + 8 + 16 * k + 8 * j + f] = p[0] & 255
                        out[legs + 72 + 16 * k + 8 * j + f] = p[1] & 255
                    else:
                        out[legs + 8 + 16 * k + 64 * j + f] = p[0] & 255
                        out[legs + 16 + 16 * k + 64 * j + f] = p[1] & 255
    return bytes(out)


def spiderlegs_problems(src):
    """Why legs.json is not acceptable (a list of sentences): the shape, integer points within SPIDER_LIMIT, each leg
    keeping its attach point in all 8 frames, each fang starting at the engine's anchor, no two points of a polyline
    equal (a line must have a length), and a leg's joint and tip neither both at the attach point."""
    why = []
    if not isinstance(src, dict) or set(src) != set(SPIDER_VIEWS):
        return ['the keys must be %s' % list(SPIDER_VIEWS)]

    def pt(p):
        return isinstance(p, list) and len(p) == 2 and all(type(c) is int and abs(c) <= SPIDER_LIMIT for c in p)

    for view in SPIDER_VIEWS:
        s = src[view]
        if not isinstance(s, dict) or set(s) != {'legs', 'fangs'}:
            why.append('%s: the keys must be legs and fangs' % view)
            continue
        legs, fangs = s['legs'], s['fangs']
        if not (isinstance(legs, list) and len(legs) == 4 and all(isinstance(l, list) and len(l) == 8 for l in legs)):
            why.append('%s: legs must be 4 legs of 8 frames' % view)
            continue
        if not (isinstance(fangs, list) and len(fangs) == 4):
            why.append('%s: fangs must be 4 frames' % view)
            continue
        for k, leg in enumerate(legs):
            for f, pl in enumerate(leg):
                if not (isinstance(pl, list) and len(pl) == 3 and all(pt(p) for p in pl)):
                    why.append('%s: leg %d frame %d must be 3 points [attach, joint, tip], integers within +-%d' % (view, k, f, SPIDER_LIMIT))
                elif pl[0] != legs[k][0][0]:
                    why.append('%s: leg %d frame %d: the attach point must be the same in all 8 frames' % (view, k, f))
                elif pl[1] == pl[0] or pl[2] == pl[1]:
                    why.append('%s: leg %d frame %d: two points of the leg are the same' % (view, k, f))
        for f, pl in enumerate(fangs):
            if not (isinstance(pl, list) and len(pl) == 3 and all(pt(p) for p in pl)):
                why.append('%s: fang frame %d must be 3 points [base, p1, p2], integers within +-%d' % (view, f, SPIDER_LIMIT))
            elif tuple(pl[0]) != SPIDER_ANCHORS[view]:
                why.append('%s: fang frame %d must start at the anchor %s' % (view, f, list(SPIDER_ANCHORS[view])))
            elif pl[1] == pl[0] or pl[2] == pl[1]:
                why.append('%s: fang frame %d: two points of the fang are the same' % (view, f))
    return why


def cat_spiderlegs(errors):
    """src/spider/legs.json -> EXE/spiderlegs.bin."""
    path = os.path.join(SRC, 'spider', 'legs.json')
    if not os.path.exists(path):
        return
    with open(path) as f:
        src = json.load(f)
    why = spiderlegs_problems(src)
    if why:
        errors.extend('spider/legs.json: ' + s for s in why)
        return
    yield 'EXE/spiderlegs.bin', enc_spiderlegs(src)


VERSION_MAX = 72


def cat_version(errors):
    """src/version/version.txt -> EXE/version.txt (the Ctrl+Alt+V alert: one line of printable ASCII; the alert is a
    text-mode box of 8-pixel cells on 640 pixels, line + 2 cells wide, so at most 78 characters; kept to VERSION_MAX)."""
    path = os.path.join(SRC, 'version', 'version.txt')
    if not os.path.exists(path):
        return
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('latin-1').strip('\r\n')
    if not text or any(not 32 <= ord(c) < 127 for c in text):
        errors.append('version/version.txt: one non-empty line of printable ASCII (32..126)')
    elif len(text) > VERSION_MAX:
        errors.append('version/version.txt: %d characters, at most %d' % (len(text), VERSION_MAX))
    else:
        yield 'EXE/version.txt', text.encode('ascii')


CATEGORIES = [cat_palette, cat_bitmaps, cat_cursors, cat_tiles, cat_sprites, cat_fonts, cat_balloon, cat_spiderlegs,
              cat_version]

# texts (SHARED type 10) that the original has no style runs for (no SHARED type 21 entry): Antipedia.Text reads
# type 21 as optional, so these are not in expected()
NO_STYLE_RUNS = {128, 129, 130, 131, 132, 865}


def expected():
    """Every entry a complete pack needs (from the measurements), for the missing list."""
    names = set()
    for b in data('bitmaps'):
        names.add('%s/2/%d.bin' % (b['archive'], b['id']))
    for c in data('cursors'):
        names.add('%s/%d/%d.bin' % (c['archive'], c['type'], c['id']))
    # only the sheets MapArt reads: 9 / 10 the house / yard tiles, 13 / 14 the nest / surface sprites (0 and the EMS
    # copies 15..20 are never loaded by the game)
    for s in data('sheets'):
        if s['id'] in (9, 10, 13, 14):
            names.add('HCEGANT/9/%d.bin' % s['id'])
    for s in data('strings'):
        names.add('%s/4/%d.bin' % (s['archive'], s['id']))
    for t in data('texts'):
        names.add('SHARED/10/%d.bin' % t['id'])
    for c in data('cards'):
        names.update(['SHARED/17/%d.bin' % c['id'], 'SHARED/19/%d.bin' % c['id']])
    for l in data('layouts'):
        names.add('HCEGANT/0/%d.bin' % l['id'])
    for s in data('sounds'):
        names.add('SOUND/5/%d.bin' % s['id'])
    for s in data('songs'):
        names.add('SOUND/20/%d.bin' % s['id'])
    for s in data('song_cues'):
        names.add('SOUND/18/%d.bin' % s['cue'])
    # the palette (MapArt); HCEGANT 15 id 1 (21 bytes) is never read. SHARED 9 is never read: the game asks SHARED for
    # types 2, 4, 6, 7, 10, 11, 17, 19 and 21 only
    names.add('HCEGANT/15/0.bin')
    # SHARED type 21 (the style runs of a text, the same id as its type-10 text): read by Antipedia.Text (Res(21, id))
    names.update('SHARED/21/%d.bin' % t['id'] for t in data('texts') if t['id'] not in NO_STYLE_RUNS)
    for a in data('embedded')['assets']:
        names.add('EXE/%s.bin' % a['Name'])
    # fonts: Ui.Font loads SHARED 11 ids 0 and 1 (the game's own PC fonts) and, for game fonts 2..5, the files FONT1..FONT4;
    # SHARED 11 ids 2 and 3 (copies of FONT1 / FONT2) are only the fallback when those files are missing, never read
    names.update(['SHARED/6/0.bin', 'EXE/version.txt', 'SHARED/11/0.bin', 'SHARED/11/1.bin']
                 + ['FONT/%d.bin' % n for n in range(1, 5)])
    return names


def main():
    opts = dict(a[2:].split('=', 1) if '=' in a else (a[2:], '1') for a in sys.argv[1:] if a.startswith('--'))
    if 'roundtrip' in opts:                                   # check the encoder against the originals, build nothing
        checked, problems = check_bitmap_roundtrip(opts['roundtrip'])
        for p in problems:
            print('error:', p)
        print('%d bitmaps checked through enc_bitmap, %d problems' % (checked, len(problems)))
        sys.exit(1 if problems else 0)
    errors, made = [], {}
    for cat in CATEGORIES:
        for name, blob in cat(errors):
            made[name] = blob
    for e in errors:
        print('error:', e)
    if errors:
        sys.exit(1)
    fallback = opts.get('fallback')
    if fallback:
        out, n_fb = OUT_DEV, 0
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with zipfile.ZipFile(fallback) as fb, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, blob in sorted(made.items()):
                z.writestr(name, blob)
            for info in fb.infolist():
                if info.filename not in made:
                    z.writestr(info.filename, fb.read(info.filename))
                    n_fb += 1
        print('%d clean files, %d from the fallback -> %s (holds original data: never ship it)' % (len(made), n_fb, out))
        return
    missing = sorted(expected() - set(made))
    by_cat = {}
    for m in missing:
        k = '/'.join(m.split('/')[:2])
        by_cat[k] = by_cat.get(k, 0) + 1
    print('%d clean files; %d still missing:' % (len(made), len(missing)))
    for k, v in sorted(by_cat.items()):
        print('  %-12s %d' % (k, v))
    if missing and not opts.get('partial'):
        sys.exit(1)
    # an incomplete pack never goes where the game would load it
    out = OUT_CLEAN if not missing else os.path.join(ROOT, 'remake', 'build', 'partial_pack.zip')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, blob in sorted(made.items()):
            z.writestr(name, blob)
    print('->', out)


if __name__ == '__main__':
    main()
