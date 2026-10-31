"""Builds the clean pack (ROADMAP A1 / A4) from the makers' source files.

    python tools/clean_pack/build.py                       # the clean pack; lists what is still missing
    python tools/clean_pack/build.py --fallback=<zip>      # a dev pack: missing resources taken from <zip>

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
- .pix: pixel art as text. One row per line, one character per pixel: 0-9 a-f = palette index (the Mac 16-colour
  palette, 0 white .. 15 black), '.' = transparent. Lines starting with '#' are comments.
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
def read_pix(path):
    """(width, height, rows): rows of palette indices, None = transparent."""
    rows = []
    with open(path) as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line or line.startswith('#'):
                continue
            rows.append([None if c == '.' else int(c, 16) for c in line])
    w = len(rows[0]) if rows else 0
    if any(len(r) != w for r in rows):
        raise ValueError('%s: rows of different lengths' % path)
    return w, len(rows), rows


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
def cat_bitmaps(errors):
    """src/bitmaps/<ARCHIVE>_<id>.pix -> ARCHIVE/2/<id>.bin, sized as measured."""
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


CATEGORIES = [cat_bitmaps, cat_cursors, cat_tiles, cat_sprites, cat_fonts]


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
    for a in data('embedded')['assets']:
        names.add('EXE/%s.bin' % a['Name'])
    # fonts: Ui.Font loads SHARED 11 ids 0 and 1 (the game's own PC fonts) and, for game fonts 2..5, the files FONT1..FONT4;
    # SHARED 11 ids 2 and 3 (copies of FONT1 / FONT2) are only the fallback when those files are missing, never read
    names.update(['SHARED/6/0.bin', 'EXE/version.txt', 'SHARED/11/0.bin', 'SHARED/11/1.bin']
                 + ['FONT/%d.bin' % n for n in range(1, 5)])
    return names


def main():
    opts = dict(a[2:].split('=', 1) if '=' in a else (a[2:], '1') for a in sys.argv[1:] if a.startswith('--'))
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
