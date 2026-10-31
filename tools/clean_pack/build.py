"""Builds the clean pack (ROADMAP A1 / A4) from the makers' source files.

    python tools/clean_pack/build.py                       # the clean pack; lists what is still missing
    python tools/clean_pack/build.py --fallback=<zip>      # a dev pack: missing resources taken from <zip>

Sources: remake/game/assets/clean/src/<category>/ (written by the makers, docs/clean_pack/*.md). Output:
- without --fallback: remake/game/assets/clean/clean_pack.zip, only when nothing is missing (else the list and exit 1;
  --partial writes what exists to remake/build/partial_pack.zip);
- with --fallback (for example remake/build/original_pack.zip from `Formica.Replay --export-pack`, the player's own
  files): remake/build/dev_pack.zip (git-ignored: it holds original data). Run the game on it with
  `-- --clean --pack=remake/build/dev_pack.zip` to see each new category in place before the pack is complete.

The pack's layout is OriginalFiles(byte[])'s: ARCHIVE/<type>/<id>.bin in the original's formats (FILE_FORMATS.md),
FONT/<n>.bin, EXE/<name>.bin, EXE/version.txt. Every source is checked against the measurements in
docs/clean_pack/data/*.json (sizes must match: the engine places things by them).

Source formats so far:
- .pix: pixel art as text. One row per line, one character per pixel: 0-9 a-f = palette index (the Mac 16-colour
  palette, 0 white .. 15 black), '.' = transparent. Lines starting with '#' are comments.
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


CATEGORIES = [cat_bitmaps, cat_cursors, cat_tiles]


def expected():
    """Every entry a complete pack needs (from the measurements), for the missing list."""
    names = set()
    for b in data('bitmaps'):
        names.add('%s/2/%d.bin' % (b['archive'], b['id']))
    for c in data('cursors'):
        names.add('%s/%d/%d.bin' % (c['archive'], c['type'], c['id']))
    for s in data('sheets'):
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
    names.update(['SHARED/6/0.bin', 'EXE/version.txt'] + ['FONT/%d.bin' % n for n in range(1, 5)])
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
