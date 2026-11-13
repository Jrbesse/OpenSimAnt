"""Builds the clean pack (ROADMAP A1 / A4) from the makers' source files.

    python tools/clean_pack/build.py                       # the clean pack; lists what is still missing
    python tools/clean_pack/build.py --fallback=<zip>      # a dev pack: missing resources taken from <zip>
    python tools/clean_pack/build.py --roundtrip=<zip>     # check the encoders (bitmaps, string lists, menus, texts, cards, glossary, layouts, sounds, the sound bank, songs, cues) against every original in <zip>; builds nothing

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
- bitmaps/<id>.pix (docs/clean_pack/ui_bitmaps.md and later bitmap specs): one .pix per HCEGANT / SHARED type-2
  bitmap, named by the bitmap's id alone (the ids are unique across the two archives; each id's archive is the
  measurements' archive, bitmaps.json), e.g. 4600.pix, exactly the measured size. A bitmap measured "masked" must
  contain '.' pixels (they become the mask plane: the game draws mode-3 bitmaps through it), any other must contain
  none; a 1-plane bitmap (21004, 21005) allows only 0 and f. -> ARCHIVE/2/<id>.bin. --roundtrip=<zip> checks the
  encoder against the originals of a pack.
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
- strings/system.json, balloons.json, messages.json, tutorial.json (docs/clean_pack/strings.md): {"<list id>": ["line", ...]}
  per file. The entry count of each list is the measured one (strings.json; the credits 1700 may have 10..80), a
  line break inside a speech-balloon entry is a real newline (the build writes the two characters backslash, n, which
  the game splits at), printable ASCII only without backslash / percent, widths in pixels from the clean fonts'
  advances (font 0 = 8 px per character), none of the original's names (OpenSimAnt is fine). -> ARCHIVE/4/<id>.bin
  (u16 big-endian count, then Pascal strings). The 6 lists no code reads (STR_UNUSED) are refused and not expected.
- menus/menus.json: {"titles": [5 labels], "menus": [5 lists of item labels]}; a separator is "---" exactly where the
  game has one, titles start with F, W, V, O, S (their Alt keys), labels at most 14 characters (titles 9, the bar at
  most 60 cells), menu 4 item 0 (Pause) is padded to 7. -> SHARED/6/0.bin (enc_menus: offset tables then strings).
- version/version.txt: one line of printable ASCII, at most 72 characters (the Ctrl+Alt+V alert) -> EXE/version.txt.
- texts/cards.json, glossary.json, popups.json, prompts.json (docs/clean_pack/texts.md): the SimAntipedia's prose.
  cards.json {"<card id>": {"title": ..., "text": ...}} (no "text" on cards 127, 129, 177): the title -> SHARED/19 (a caption,
  at most 24 characters), the text -> SHARED/10 + 21 of the card's text id; in a text the bold (link) words are written between
  asterisks and a line break is a real newline (a blank line = two); the style runs are derived from the asterisks.
  glossary.json {"<definition id>": {"word", "term", "text"}} for the 26 ids 901, 910..929, 963..967: "word" the link word as
  the cards write it in bold (the glossary table EXE/glossary.bin is derived from the 26 words), the pop-up definition is
  "*term* - text". popups.json {"950".."962": text}: the 13 flowchart pop-ups. prompts.json {"128".."132": text}: the save
  prompts (128 quit, 130 load / new game; 129, 131, 132 are never shown). The card layouts (SHARED/17) are not made by anyone:
  they are data/card_layouts.json (tools/clean_pack/make_card_layouts.py), always built. Every text is laid out by a port of
  the game's own line breaker (ant_layout) with the clean fonts 2 and 5: it must fit its rectangle, every bold word must become
  a link to the right definition, and each card's required link words (the originals' ones, by definition id) must be there.
- layouts/texts.json (docs/clean_pack/layouts.md): {"<window>.<item>": "text"}, the 12 words inside window items (three window
  captions, the file dialog's two labels and CANCEL, the two "continue" lines, DEBUG, the quit dialog's three buttons); printable
  ASCII, no percent sign, at most the item's room in pixels (font 0 = 8 px per character). The windows themselves (rectangles,
  edge references, item types, colour schemes, the UI tables 128 / 129 / 131) are functional data, not written by any maker:
  data/window_layouts.json, made by tools/clean_pack/make_layouts.py from the player's pack (numbers and ids only), always built
  (enc_layout -> HCEGANT/0/<id>.bin); a window with a word of the makers' waits for it (listed as missing).
- sounds/sfx_<id>.wav (docs/clean_pack/sounds.md): RIFF PCM mono 16-bit 5,576 Hz with only 'fmt ' and 'data' chunks, at most 16,000
  frames, ends at zero, length and peak within the measured table for the 35 required ids (the other ids 0..56 are optional) ->
  SOUND/5/<id>.bin (16 signed deltas, then 4-bit codes, high nibble first; enc_sample searches the table, refuses under 9 dB SNR).
  sounds/fm_patches.json {"patches": [16 objects]} (the OPL2 register fields of the 16 instruments, effect_key, velocity_offset) ->
  EXE/soundbank.bin (2,856 bytes: the song channel table, 20 FM records, 53 sample records, 56 effects, 56 instruments; the
  functional tables come from data/embedded.json).
- music/<song id>.mid (docs/clean_pack/music.md): Standard MIDI file, format 1, 240 ppq, note on / off only, checked with a port of
  the game's sequencer (midi_walk / midi_check) and copied unchanged -> SOUND/20/<id>.bin; the cue entries SOUND/18/<cue>.bin come from
  data/song_cues.json and are always built.
"""
import json, math, os, re, struct, sys, time, zipfile

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
    """src/bitmaps/<id>.pix -> ARCHIVE/2/<id>.bin (ARCHIVE the measurements' archive for the id), sized as measured.
    A bitmap the game draws masked (the measurements' "masked") must have at least one '.' (transparent) pixel and any
    other must have none; a 1-plane bitmap is black ink on white paper, so only 0 (white) and f (black) are allowed in
    it."""
    want = {(b['archive'], b['id']): b for b in data('bitmaps')}
    arch_by_id = {b['id']: b['archive'] for b in data('bitmaps')}
    d = os.path.join(SRC, 'bitmaps')
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith('.pix') or not name[:-4].isdigit():
            continue
        ident = int(name[:-4])
        key = (arch_by_id.get(ident), ident)
        if key[0] is None or key not in want:
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


# ------------------------------------------------------------------------------------------------ string lists, menus
# STR#-style string lists (OriginalFiles.Strings) and the pull-down menus (OpenSimAnt.Data/Menus.cs); the spec is
# docs/clean_pack/strings.md. 113 of the 119 measured lists are read by the game; the other 6 are Macintosh leftovers
# that no code loads (an immediate-operand search of the executable and the remake's code), so they are not in the
# pack and not in expected().
STR_UNUSED = {1030, 1300, 1310, 1350, 2000, 2100}
STR_GROUPS = ['system', 'balloons', 'messages', 'tutorial']       # src/strings/<group>.json
STR_SYSTEM = {1000, 1001, 1010, 1020, 1050, 1100, 1101, 1102, 1103, 1700, 1800, 1900}
STR_BALLOONS = {1200, 1210, 1220, 1230, 1240, 1250, 1260}
STR_TEXT_WIDTH_FONT4 = {'messages': 300, 'tutorial': 460}         # the widest line, in pixels of font 4
CAPTION_CHARS = 40                                                 # window captions: 8-pixel cells
SCENE_CAPTION_CHARS = 24                                           # the picture strip of the death scenes: 200 px / 8


ENGINE_KEYS = ['caption_load', 'caption_save', 'overwrite', 'saved', 'read_error', 'not_found', 'drive_error',
               'no_files', 'yard_choose']                    # OriginalFiles.EngineStringKeys
ENGINE_PLACEHOLDER = {'overwrite': '%s', 'saved': '%s', 'drive_error': '%c'}   # exactly once; %s alone on its line
ENGINE_LINES = {'overwrite': 2, 'saved': 2, 'read_error': 2}                    # lines (1 for every other key)
# the longest line, in characters of the 8-pixel cell: an alert is drawn in text-mode cells, its longest line + 2 cells
# wide on 640 pixels, and the path line (%s) can be long, so every other line is kept to 40; the file dialog's caption is
# an item 240 pixels wide (30 characters of font 0, 28 kept); the list's one row is clipped at 14 characters (12 kept);
# yard_choose is only the status line's fallback for STR# 1010 entry 20 (never shown while that list exists)
ENGINE_IDENTITY = re.compile(r'maxis|simcity|(?<!open)simant', re.I)
ENGINE_MAX = {'caption_load': 28, 'caption_save': 28, 'no_files': 12, 'yard_choose': 70}


def cat_engine_strings(errors):
    """src/strings/engine.json -> EXE/engine_strings.json: {"<key>": "text"}, the engine's own alerts and file dialog
    words (OpenSimAnt.Data/OriginalFiles.EngineString; on the player's files they are read from SIMANT.EXE). Printable
    ASCII and \\n; %s (the path) / %c (the drive letter) as ENGINE_PLACEHOLDER says; no leading or trailing blank."""
    path = os.path.join(SRC, 'strings', 'engine.json')
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf-8') as f:
            src = json.load(f)
    except (OSError, ValueError) as e:
        errors.append('strings/engine.json: %s' % e)
        return
    if not isinstance(src, dict) or set(src) != set(ENGINE_KEYS) or not all(isinstance(v, str) for v in src.values()):
        errors.append('strings/engine.json: an object with exactly the keys %s, string values' % ', '.join(ENGINE_KEYS))
        return
    bad = len(errors)
    for key in ENGINE_KEYS:
        text, where = src[key], 'strings/engine.json "%s"' % key
        lines = text.split('\n')
        if any(not 32 <= ord(c) < 127 for c in text.replace('\n', '')) or text != text.strip() or '' in lines:
            errors.append('%s: printable ASCII only, no blank line, no leading or trailing space' % where)
            continue
        if len(lines) != ENGINE_LINES.get(key, 1):
            errors.append('%s: %d line(s) expected' % (where, ENGINE_LINES.get(key, 1)))
        ph = ENGINE_PLACEHOLDER.get(key)
        if text.count('%') != (1 if ph else 0) or (ph and text.count(ph) != 1):
            errors.append('%s: %s' % (where, ('exactly one %s' % ph) if ph else 'no percent sign'))
        elif ph == '%s' and ph not in lines:
            errors.append('%s: %%s (the path) alone on its line' % where)
        for ln in lines:
            if ln != '%s' and len(ln) > ENGINE_MAX.get(key, 40):
                errors.append('%s: line "%s" is %d characters, at most %d'
                              % (where, ln, len(ln), ENGINE_MAX.get(key, 40)))
        if ENGINE_IDENTITY.search(text):
            errors.append('%s: carries a foreign name' % where)
    if len(errors) == bad:
        yield 'EXE/engine_strings.json', json.dumps({k: src[k] for k in ENGINE_KEYS}, indent=1).encode('ascii')


def str_group(i):
    if i in STR_SYSTEM:
        return 'system'
    if i in STR_BALLOONS:
        return 'balloons'
    if 10000 <= i < 11000:
        return 'messages'
    if 11000 <= i < 12000:
        return 'tutorial'
    return None


def str_rule(i, k):
    """The placement rule of entry k of list i: (font, widest line in pixels, kind). Font 0 is the PC text-cell font
    (8 pixels per character); fonts 1..5 use the advances of src/fonts/font<n>.json. kind: 'text' (non-empty),
    'blank' (must be empty), 'blank_ok' (may be empty), 'balloon' (up to 2 lines, `\\n` = line break),
    'lead_space' / 'trail_space' (must start / end with a space), 'sep' (a separator: spaces around it are fine)."""
    if i == 1000:
        return 0, CAPTION_CHARS * 8, 'text'
    if i == 1001:
        return 4, 100, 'text'
    if i == 1010:
        if k == 14:                                        # the Status window's continue prompt: a 295 px strip
            return 2, 290, 'text'
        return (0, SCENE_CAPTION_CHARS * 8, 'text') if k >= 23 else (2, 340, 'text')
    if i == 1020:
        return 2, 340, 'text'
    if i == 1050:
        return 3, 38, 'text'
    if i in (1100, 1101, 1102, 1103):
        return 2, 75, 'text'
    if i in STR_BALLOONS:
        return 2, 220, 'balloon'
    if i == 1700:
        return 4, 254, 'blank_ok'
    if i == 1800:
        if k <= 12:
            return 4, 0, 'blank'
        return {13: (4, 60, 'trail_space'), 14: (4, 60, 'lead_space'), 15: (0, 40, 'sep'), 16: (4, 38, 'text'),
                17: (4, 280, 'text'), 18: (4, 280, 'text')}[k]
    if i == 1900:
        return 4, 218, 'text'
    return 4, STR_TEXT_WIDTH_FONT4[str_group(i)], 'text'


def enc_strlist(entries):
    """A Mac STR# list as the game reads it (OriginalFiles.Strings): u16 big-endian count, then each entry as a length
    byte and its bytes. A real newline in an entry becomes the two characters backslash, n (the balloons' line break)."""
    out = bytearray(struct.pack('>H', len(entries)))
    for e in entries:
        b = e.replace('\n', '\\n').encode('latin-1')
        out.append(len(b))
        out += b
    return bytes(out)


def dec_strlist(d):
    """The inverse of enc_strlist (a backslash-n pair becomes a newline). Raises ValueError on bytes left over."""
    n, p, res = (d[0] << 8) | d[1], 2, []
    for _ in range(n):
        res.append(d[p + 1:p + 1 + d[p]].decode('latin-1').replace('\\n', '\n'))
        p += 1 + d[p]
    if p != len(d):
        raise ValueError('%d bytes left over' % (len(d) - p))
    return res


_font_cache = {}


def font_advances(n):
    """(advances, missing advance) of the clean font n from src/fonts/font<n>.json; None if it is not made yet."""
    if n not in _font_cache:
        path = os.path.join(SRC, 'fonts', 'font%d.json' % n)
        if os.path.exists(path):
            with open(path) as f:
                j = json.load(f)
            _font_cache[n] = (j['advances'], j.get('missing_advance', 0))
        else:
            _font_cache[n] = None
    return _font_cache[n]


def text_width(font, s):
    """The pixel width of the line s in the game's font (the PC font 0: 8 per character); None if the font is missing."""
    if font == 0:
        return 8 * len(s)
    f = font_advances(font)
    if f is None:
        return None
    adv, missing = f
    return sum(adv[ord(c)] if ord(c) < len(adv) else missing for c in s)


IDENTITY = None


def identity_problem(s):
    """The original's product, publisher and franchise names stay out of the pack (ROADMAP A6); the project's own name,
    OpenSimAnt, is fine."""
    global IDENTITY
    if IDENTITY is None:
        import re
        IDENTITY = re.compile(r'maxis|simcity|(?<!open)simant', re.I)
    return IDENTITY.search(s) is not None


def str_problems(i, entries, where):
    """The reasons the new entries of list i break the spec (docs/clean_pack/strings.md); [] when they are fine."""
    errs = []
    count = len(next(m for m in data('strings') if m['id'] == i)['entries'])
    if i == 1700:
        if not 10 <= len(entries) <= 80:
            errs.append('%s: %d lines, the credits roll wants 10..80' % (where, len(entries)))
    elif len(entries) != count:
        errs.append('%s: %d entries, the game indexes exactly %d' % (where, len(entries), count))
        return errs
    for k, e in enumerate(entries):
        w = '%s entry %d' % (where, k)
        if not isinstance(e, str):
            errs.append('%s: not a string' % w)
            continue
        font, limit, kind = str_rule(i, k)
        lines = e.split('\n')
        if any(not 32 <= ord(c) < 127 for c in e.replace('\n', '')):
            errs.append('%s: only printable ASCII (32..126) and line breaks' % w)
        if '\\' in e or '%' in e:
            errs.append('%s: no backslash and no percent sign (they are format codes in the game)' % w)
        if len(lines) > 1 and kind != 'balloon':
            errs.append('%s: a line break is only for the speech balloons (one entry is one line elsewhere)' % w)
        if kind == 'balloon' and len(lines) > 2:
            errs.append('%s: at most 2 lines' % w)
        if kind == 'blank' and e != '':
            errs.append('%s: this entry is never read, leave it empty' % w)
        if kind in ('text', 'balloon', 'lead_space', 'trail_space', 'sep') and not e.strip():
            errs.append('%s: empty' % w)
        if i == 1001 and len(e) > 14:
            errs.append('%s: %d characters, at most 14 (it is also lettered in the 8-pixel text cells of the Edit window caption)' % (w, len(e)))
        if kind in ('text', 'balloon') and e != e.strip(' '):
            errs.append('%s: no leading or trailing spaces' % w)
        if kind == 'lead_space' and not e.startswith(' '):
            errs.append('%s: must start with a space (it is joined to the text before it without one)' % w)
        if kind == 'trail_space' and not e.endswith(' '):
            errs.append('%s: must end with a space (the next text is joined to it without one)' % w)
        if kind in ('lead_space', 'trail_space') and not e.strip():
            errs.append('%s: empty' % w)
        if identity_problem(e):
            errs.append('%s: contains a name the pack must not carry (ROADMAP A6)' % w)
        if limit:
            for line in lines:
                px = text_width(font, line)
                if px is None:
                    errs.append('%s: font %d is not made yet, cannot check the width' % (w, font))
                    break
                if px > limit:
                    errs.append('%s: %d px wide in font %d, the room is %d px' % (w, px, font, limit))
    return errs


def cat_strings(errors):
    """src/strings/<group>.json (system, balloons, messages, tutorial): {"<list id>": ["entry", ...]} -> the archive's
    type-4 resource of each list (ARCHIVE/4/<id>.bin; the archive is the measured one). Counts, widths and the other
    rules are in str_problems."""
    archive = {m['id']: m['archive'] for m in data('strings')}
    seen = {}
    for group in STR_GROUPS:
        path = os.path.join(SRC, 'strings', group + '.json')
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                src = json.load(f)
        except ValueError as e:
            errors.append('strings/%s.json: %s' % (group, e))
            continue
        if not isinstance(src, dict):
            errors.append('strings/%s.json: an object {"<list id>": [entries]}' % group)
            continue
        for key, entries in src.items():
            where = 'strings/%s.json list %s' % (group, key)
            if not key.isdigit() or int(key) not in archive:
                errors.append('%s: no such list in the game' % where)
                continue
            i = int(key)
            if i in STR_UNUSED:
                errors.append('%s: this list is never read by the game, leave it out' % where)
                continue
            if str_group(i) != group:
                errors.append('%s: belongs in strings/%s.json' % (where, str_group(i)))
                continue
            if i in seen:
                errors.append('%s: also in strings/%s.json' % (where, seen[i]))
                continue
            seen[i] = group + '.json'
            if not isinstance(entries, list):
                errors.append('%s: a list of strings' % where)
                continue
            problems = str_problems(i, entries, where)
            errors.extend(problems)
            if not problems:
                yield '%s/4/%d.bin' % (archive[i], i), enc_strlist(entries)


MENU_ITEM_CHARS = 14                  # a label: the box is label + 2 cells wide (8-pixel cells)
MENU_TITLE_CHARS = 9                  # a title takes its label + 1 cells; all five fit the 80-cell bar
MENU_PAUSE_PAD = 7                    # menu 4 item 0 is relabelled by the game with a 7-character word: padded to that
MENU_ALT_KEYS = 'FWVOS'               # the initial letters of the titles = their Alt keys (the key table is fixed)
MENU_SEP = '---'


def enc_menus(titles, menus):
    """SHARED type 6 id 0 (OpenSimAnt.Data/Menus.cs): u32 little-endian offsets of the lists (titles first, then each
    menu) up to a 0, then each list's table of u32 string offsets up to a 0, then the NUL-terminated strings in order.
    A title is a space and its label; an item is its state byte (a space) and its label, a separator is '---'; the
    first item of menu 4 (the Pause toggle) is padded with spaces to MENU_PAUSE_PAD."""
    lists = [[' ' + t for t in titles]]
    for mi, items in enumerate(menus):
        lst = []
        for k, it in enumerate(items):
            if it == MENU_SEP:
                lst.append(MENU_SEP)
            else:
                lst.append(' ' + (it.ljust(MENU_PAUSE_PAD) if (mi, k) == (4, 0) else it))
        lists.append(lst)
    head = 4 * (len(lists) + 1)
    tables, p = [], head
    for lst in lists:
        tables.append(p)
        p += 4 * (len(lst) + 1)
    out = bytearray(struct.pack('<%dI' % (len(lists) + 1), *tables, 0))
    for lst in lists:
        offs = []
        for s in lst:
            offs.append(p)
            p += len(s) + 1
        out += struct.pack('<%dI' % (len(lst) + 1), *offs, 0)
    for lst in lists:
        for s in lst:
            out += s.encode('latin-1') + b'\0'
    return bytes(out)


def dec_menus(d):
    """The inverse of enc_menus: (titles, menus) with the leading space of titles and items removed (a separator is
    '---'). The Pause item keeps its padding."""
    def u32(o):
        return struct.unpack_from('<I', d, o)[0]
    lists, t = [], 0
    while u32(t):
        lst, p = [], u32(t)
        while u32(p):
            s = u32(p)
            lst.append(d[s:d.index(0, s)].decode('latin-1'))
            p += 4
        lists.append(lst)
        t += 4
    clean = lambda lst: [x if x == MENU_SEP else x[1:] for x in lst]
    return clean(lists[0]), [clean(l) for l in lists[1:]]


def menu_problems(src):
    errs = []
    want = data('menus')
    titles, menus = src.get('titles'), src.get('menus')
    if not (isinstance(titles, list) and isinstance(menus, list)):
        return ['menus/menus.json: {"titles": [5 strings], "menus": [5 lists of strings]}']
    if len(titles) != len(want[0]['items']) or len(menus) != len(want) - 1:
        return ['menus/menus.json: %d titles and %d menus, the game has %d and %d'
                % (len(titles), len(menus), len(want[0]['items']), len(want) - 1)]

    def label_problems(w, s, limit, sep_ok):
        out = []
        if not isinstance(s, str) or not s:
            return ['%s: a non-empty string' % w]
        if sep_ok and s == MENU_SEP:
            return out
        if any(not 32 <= ord(c) < 127 for c in s) or s != s.strip(' ') or '%' in s or '\\' in s:
            out.append('%s: printable ASCII without leading / trailing spaces, no percent sign or backslash' % w)
        if len(s) > limit:
            out.append('%s: %d characters, at most %d' % (w, len(s), limit))
        if identity_problem(s):
            out.append('%s: contains a name the pack must not carry (ROADMAP A6)' % w)
        return out
    for k, t in enumerate(titles):
        errs += label_problems('menus.json title %d' % k, t, MENU_TITLE_CHARS, False)
        if isinstance(t, str) and t[:1].upper() != MENU_ALT_KEYS[k]:
            errs.append('menus.json title %d: must start with %s (its Alt key is fixed in the key table)' % (k, MENU_ALT_KEYS[k]))
    if all(isinstance(t, str) for t in titles) and sum(len(t) + 1 for t in titles) > 60:
        errs.append('menus.json: the five titles take %d cells, at most 60' % sum(len(t) + 1 for t in titles))
    for mi, items in enumerate(menus):
        w = want[mi + 1]['items']
        if not isinstance(items, list) or len(items) != len(w):
            errs.append('menus.json menu %d: %d items, the game has %d' % (mi, len(items) if isinstance(items, list) else -1, len(w)))
            continue
        for k, it in enumerate(items):
            where = 'menus.json menu %d item %d' % (mi, k)
            if w[k]['separator'] != (it == MENU_SEP):
                errs.append('%s: %s' % (where, 'must be the separator "---"' if w[k]['separator'] else 'must not be a separator'))
                continue
            errs += label_problems(where, it, MENU_PAUSE_PAD if (mi, k) == (4, 0) else MENU_ITEM_CHARS, True)
    return errs


def cat_menus(errors):
    """src/menus/menus.json: {"titles": [...], "menus": [[...], ...]} -> SHARED/6/0.bin (enc_menus)."""
    path = os.path.join(SRC, 'menus', 'menus.json')
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf-8') as f:
            src = json.load(f)
    except ValueError as e:
        errors.append('menus/menus.json: %s' % e)
        return
    problems = menu_problems(src) if isinstance(src, dict) else ['menus/menus.json: an object']
    errors.extend(problems)
    if not problems:
        yield 'SHARED/6/0.bin', enc_menus(src['titles'], src['menus'])


def check_text_roundtrip(zip_path):
    """The string lists and the menus of the pack <zip> decoded, encoded again and compared byte for byte, and the
    decoders compared with the measurements (strings.json, menus.json). Returns (lists, menus, problems); the pack's
    text is read for this check only and never written anywhere."""
    lists, menus, problems = 0, 0, []
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for m in data('strings'):
            name = '%s/4/%d.bin' % (m['archive'], m['id'])
            if name not in names:
                problems.append('%s: not in the pack' % name)
                continue
            blob = z.read(name)
            try:
                entries = dec_strlist(blob)
            except (ValueError, IndexError) as e:
                problems.append('%s: %s' % (name, e))
                continue
            lists += 1
            if [len(e.replace('\n', '\\n')) for e in entries] != [x['length'] for x in m['entries']]:
                problems.append('%s: the entry lengths differ from the measurements' % name)
            if enc_strlist(entries) != blob:
                problems.append('%s: not byte-identical after decode + encode' % name)
        if 'SHARED/6/0.bin' not in names:
            problems.append('SHARED/6/0.bin: not in the pack')
        else:
            blob = z.read('SHARED/6/0.bin')
            titles, mn = dec_menus(blob)
            menus += 1 + len(mn)
            want = data('menus')
            if len(titles) != len(want[0]['items']) or [len(mi) for mi in mn] != [len(w['items']) for w in want[1:]]:
                problems.append('SHARED/6/0.bin: the item counts differ from the measurements')
            else:
                for w, labels in zip(want, [titles] + mn):
                    got = [(len(x) if x != MENU_SEP else 2, x == MENU_SEP) for x in labels]
                    if w['list'] == 'titles':
                        got = [(len(x) + 1, False) for x in labels]
                    if got != [(i['length'], i['separator']) for i in w['items']]:
                        problems.append('SHARED/6/0.bin %s: lengths or separators differ from the measurements' % w['list'])
            # the whole resource, byte for byte; the Pause padding is the original's
            if enc_menus(titles, mn) != blob:
                problems.append('SHARED/6/0.bin: not byte-identical after decode + encode')
    return lists, menus, problems


# ------------------------------------------------------------------------------------------------ texts, cards, glossary
# The long prose: the SimAntipedia's cards (SHARED type 17 layout, 19 caption, 10 text, 21 style runs), the glossary
# (EXE/glossary.bin), the pop-up definitions and the two save prompts (docs/clean_pack/texts.md). OpenSimAnt.Data/
# Antipedia.cs reads them; the port of its text clean-up and line breaker below (ant_clean, ant_layout) is exact, so
# "the text fits its rectangle" and "this bold word becomes a link" are decided here the way the game will decide them.
NO_STYLE_RUNS = {128, 129, 130, 131, 132, 865}        # texts the original has no style runs for (no SHARED type 21 entry)
PROMPT_IDS = (128, 129, 130, 131, 132)                 # 128 (quit) and 130 (load / new game) are shown, 129 / 131 / 132 never read
GLOSSARY_IDS = [901] + list(range(910, 930)) + list(range(963, 968))      # the 26 definitions the glossary table can hold
POPUP_IDS = list(range(950, 963))                      # the 13 flowchart pop-ups (reached by picture hotspots only)
GLOSSARY_SLOTS = 26                                    # 0x396 bytes: EmbeddedAssets.glossary is exactly 26 entries and the id 0 end entry
BOLD = 0x100                                           # a style run's face word for bold (= a link font 5 word)
STYL_FIXED = (12, 10, 3, 9)                            # height, ascent, font, size of every ScrpSTElement of the originals
CARD_TITLE_CHARS = 24                                  # the caption is lettered in font 0 (8 px) in a 320 px strip: 40 at most
POPUP_WIDTH = 160                                      # Antipedia.Popup: half the card item (320 / 2)
POPUP_MAX_LINES = 10
PROMPT_WIDTH = 258                                     # Main.DrawSavePrompt: the item (266 px) less 8; font 4
PROMPT_MAX_LINES = 7                                   # the item is 109 px tall, a font 4 line 14 px
CARD_BOTTOM = 180                                      # rows 180..199 of a card carry the navigation strip
MISSING_PICTURES = {151, 161, 162, 163, 164, 165, 166, 167, 168, 169, 171, 211, 212, 430, 570, 860, 875, 877}   # the game draws nothing
WARNINGS = []


def enc_card_layout(recs):
    """SHARED type 17 (Antipedia.Build; big-endian): u16 height 200, u16 width 320, then the records in order: 'PICT' + u16
    bitmap, Rect (top, left, bottom, right), u16 n, n x (Rect, s16 value); 'TEXT' + Rect, u16 n, n x u16 text id.
    recs: [["P", bitmap, [t, l, b, r], [[t, l, b, r, value], ...]], ["T", [t, l, b, r], [text ids]], ...]."""
    out = bytearray(struct.pack('>HH', 200, 320))
    for rec in recs:
        if rec[0] == 'P':
            out += b'PICT' + struct.pack('>H4hH', rec[1], *rec[2], len(rec[3]))
            for h in rec[3]:
                out += struct.pack('>5h', *h)
        else:
            out += b'TEXT' + struct.pack('>4hH', *rec[1], len(rec[2])) + b''.join(struct.pack('>H', t) for t in rec[2])
    return bytes(out)


def dec_card_layout(d):
    """The inverse of enc_card_layout."""
    recs, o = [], 4
    while o + 4 <= len(d):
        tag = d[o:o + 4]
        o += 4
        if tag == b'PICT':
            pid, t, l, b, r, n = struct.unpack_from('>H4hH', d, o)
            o += 12
            links = [list(struct.unpack_from('>5h', d, o + 10 * k)) for k in range(n)]
            o += 10 * n
            recs.append(['P', pid, [t, l, b, r], links])
        elif tag == b'TEXT':
            t, l, b, r, n = struct.unpack_from('>4hH', d, o)
            o += 10
            recs.append(['T', [t, l, b, r], list(struct.unpack_from('>%dH' % n, d, o))])
            o += 2 * n
        else:
            raise ValueError('unknown record %r' % tag)
    return recs


def enc_card_name(title):
    """SHARED type 19: the caption, a space written as an underscore (the game shows it as a space), NUL-terminated."""
    return title.replace(' ', '_').encode('latin-1') + b'\0'


def enc_text(plain):
    """SHARED type 10: the text in Mac Roman (printable ASCII here), a line break as CR, one NUL at the end."""
    return plain.replace('\n', '\r').encode('latin-1') + b'\0'


def parse_markup(s):
    """'a *b* c' -> ('a b c', [(2, 3)]): the bold (link) words of a text are written between asterisks. ValueError if an
    asterisk is unpaired or a bold span is empty."""
    plain, spans, start = [], [], None
    for ch in s:
        if ch != '*':
            plain.append(ch)
        elif start is None:
            start = len(plain)
        elif start == len(plain):
            raise ValueError('an empty pair of asterisks')
        else:
            spans.append((start, len(plain)))
            start = None
    if start is not None:
        raise ValueError('an asterisk that is not closed')
    return ''.join(plain), spans


def enc_styl(plain, spans):
    """SHARED type 21 (a Mac 'styl': u16 count, then per run 20 bytes: u32 start, s16 height, ascent, font, u16 face, s16
    size, 6 bytes of colour): the text is one run from 0, a new run wherever bold starts or ends; a bold run's face word
    is 0x0100, the others 0 (STYL_FIXED are the originals' constants, which the game does not read)."""
    flags = [False] * len(plain)
    for s, e in spans:
        flags[s:e] = [True] * (e - s)
    runs, prev = [], None
    for i, f in enumerate(flags):
        if f != prev:
            runs.append((i, BOLD if f else 0))
            prev = f
    if not runs:
        runs = [(0, 0)]
    h, a, fo, sz = STYL_FIXED
    return struct.pack('>H', len(runs)) + b''.join(struct.pack('>I3hHh6s', st, h, a, fo, face, sz, bytes(6)) for st, face in runs)


def dec_styl(d):
    """The inverse of enc_styl: [(start, face)] and the other fields of the first element (to check they are constant)."""
    n = struct.unpack_from('>H', d, 0)[0]
    if 2 + 20 * n != len(d):
        raise ValueError('%d bytes for %d runs' % (len(d), n))
    runs, other = [], set()
    for k in range(n):
        st, h, a, fo, face, sz = struct.unpack_from('>I3hHh', d, 2 + 20 * k)
        runs.append((st, face))
        other.add((h, a, fo, sz, d[2 + 20 * k + 14:2 + 20 * k + 20]))
    return runs, other


def enc_glossary(entries):
    """EXE/glossary.bin: the table of the link words, as the game reads it (EmbeddedAssets "glossary", 4EE5:0500,
    f_78440): 0x22-byte entries, the word upper-case in 32 bytes (NUL-padded), then its u16 little-endian text id; the
    entries up to one with id 0; GLOSSARY_SLOTS entries and the end entry = 918 bytes. entries: [(id, word)]. (The
    original's end entry carries a word the game never compares; ours is all zeros.)"""
    out = bytearray()
    ents = [(i, w.upper()) for i, w in sorted(entries)]
    for i, w in ents:
        out += w.encode('ascii').ljust(32, b'\0') + struct.pack('<H', i)
    return bytes(out + bytes(34 * (GLOSSARY_SLOTS - len(ents) + 1)))


def dec_glossary(d):
    """The inverse of enc_glossary (the game's reading): [(id, word)] up to the first id 0."""
    res = []
    for p in range(0, len(d) - 33, 34):
        i = struct.unpack_from('<H', d, p + 32)[0]
        if i == 0:
            break
        res.append((i, d[p:p + 32].split(b'\0')[0].decode('ascii')))
    return res


# --- the engine's reading of a text, ported exactly (Antipedia.Text, Layout, BreakAt)
def ant_clean(raw, runs):
    """Antipedia.Text: each NUL in the first size - 4 bytes goes together with the bytes after it that are below 0x20 (as
    signed chars, so the 0x80.. ones too), the runs after it move back; the text ends at the first NUL. -> (bytes, runs)."""
    text, runs, size = bytearray(raw), list(runs), len(raw)
    while True:
        p = text.find(b'\0', 0, max(0, min(size - 4, len(text))))
        if p < 0:
            break
        q = p
        while (text[q] - 256 if text[q] > 127 else text[q]) <= 0x1f and q < size - 4:
            q += 1
        n = min(size - q, len(text) - q)
        text[p:p + n] = text[q:q + n]
        runs = [((s - (q - p)) if s >= q else s, f) for s, f in runs]
        size -= q - p
        if q == p:
            break
    e = text.find(b'\0', 0, size)
    return bytes(text[:size if e < 0 else e]), runs


def break_at(c, i):
    """Antipedia.BreakAt: -1 none, else the break position (before a line end, a space, ( [ {, after ! ) , - . ? ] })."""
    if c in (0, 10, 13, 0x20, 0x28, 0x5b, 0x7b):
        return i
    if c in (0x21, 0x29, 0x2c, 0x2d, 0x2e, 0x3f, 0x5d, 0x7d):
        return i + 1
    return -1


def ant_layout(text, runs, l, t, r, b, adv, lh):
    """Antipedia.Layout into the rectangle (l, t, r, b) with adv(font, byte) the pen advance and lh the line height. Returns
    (draws, links, lines, consumed, too_long): draws [(x, y, font, bytes)], links [(x, y, bytes)] (a bold segment that ends
    inside its line; the game looks its trimmed upper-case text up in the glossary), the number of lines drawn, how many
    bytes of the text were laid out, and the lines that had no break point and ran past the width (an over-long word)."""
    width, lines, y = r - l, (b - t) // lh, t + 4
    run, i, cur = 0, 0, (5 if runs and runs[0][1] == BOLD else 2)
    draws, links, too_long, line = [], [], [], 0

    def at(k):
        return text[k] if k < len(text) else 0

    while i < len(text) and line < lines:
        x, brk, seg, segx, end = 0, 0, i, l + 1, False
        while x < width and not end:
            if run + 1 < len(runs) and runs[run + 1][0] <= i:
                run += 1
                if i - seg > 0:
                    draws.append((segx, y, cur, text[seg:i]))
                    if runs[run - 1][1] == BOLD:
                        links.append((segx, y, text[seg:i]))
                segx = l + x + 1
                cur = 5 if runs[run][1] == BOLD else 2
                seg = i
            c = at(i)
            x += adv(cur, c)
            if x < width:
                if c in (0, 10, 13):
                    end = True
                k = break_at(c, i)
                if k >= 0:
                    brk = k
            i += 1
        frm, to = seg, i
        if brk != 0:
            to = brk
            if brk < seg:
                frm = brk
        elif x >= width:
            too_long.append(line)
        if to - frm > 0:
            draws.append((segx, y, cur, text[frm:to]))
        while at(to) == 0x20:
            to += 1
        if at(to) in (10, 13):
            to += 1
        i = to
        line += 1
        y += lh
    return draws, links, line, min(i, len(text)), too_long


def ink(b):
    return bytes(c for c in b if c > 32)


def line_height():
    """Antipedia.Layout's line height: the taller of fonts 2 and 5, an Apple FONT counting its height less 1."""
    h = {m['source']: m['height'] for m in data('fonts')}
    return max(h['FONT1'], h['FONT4']) - 1


def clean_adv():
    """adv(font, byte) from the clean fonts' json (fonts 2 and 5); None if one is not made yet."""
    f2, f5 = font_advances(2), font_advances(5)
    if f2 is None or f5 is None:
        return None
    tabs = {2: f2, 5: f5}

    def adv(font, c):
        a, missing = tabs[font]
        return a[c] if c < len(a) else missing
    return adv


def original_adv():
    """adv(font, byte) from the measurements of the originals (FONT1 and FONT4), for the checks of --roundtrip."""
    tabs = {m['source']: m['advances'] for m in data('fonts')}
    t = {2: tabs['FONT1'], 5: tabs['FONT4']}
    return lambda font, c: t[font][c] if c < len(t[font]) else 0


def wrap_prompt(text, width):
    """Main.WrapText for the save prompt (font 4): greedy words, line breaks kept; the lines."""
    lines = []
    for para in text.split('\n'):
        line = ''
        for word in para.split(' '):
            nxt = word if not line else line + ' ' + word
            if line and text_width(4, nxt) > width:
                lines.append(line)
                line = word
            else:
                line = nxt
        lines.append(line)
    return lines


def bold_spans(runs, n):
    """The (start, end) of each bold run of a text of n bytes."""
    return [(st, min(n, runs[k + 1][0] if k + 1 < len(runs) else n)) for k, (st, f) in enumerate(runs) if f == BOLD and st < n]


def markup_of(text, spans):
    """A text (bytes, as the game sees it) and its bold spans as maker markup: asterisks round the bold words, CR / LF as a
    line break. ValueError if the text cannot be written that way."""
    if b'*' in text:
        raise ValueError('an asterisk in the text')
    out, ends = [], {e: 1 for _, e in spans}
    starts = {s for s, _ in spans}
    for k, c in enumerate(text + b'\0'):
        if k in ends:
            out.append('*')
        if k in starts:
            out.append('*')
        if k < len(text):
            out.append('\n' if c in (10, 13) else chr(c))
    if any(spans[k][1] >= spans[k + 1][0] for k in range(len(spans) - 1)):
        raise ValueError('two bold runs touch')
    return ''.join(out)


def check_markup_text(where, s, allow_bold):
    """The character rules shared by every prose text; (plain, spans, problems)."""
    errs = []
    if not isinstance(s, str) or not s.strip():
        return '', [], ['%s: a non-empty string' % where]
    if any(not 32 <= ord(c) < 127 and c != '\n' for c in s):
        errs.append('%s: only printable ASCII (32..126) and line breaks (no tabs, accents or typographic quotes)' % where)
    if '\\' in s:
        errs.append('%s: no backslash' % where)
    if s != s.strip() or '\n ' in s or ' \n' in s or '  ' in s:
        errs.append('%s: no leading / trailing spaces or line breaks, no two spaces in a row, no space next to a line break' % where)
    if identity_problem(s):
        errs.append('%s: contains a name the pack must not carry (ROADMAP A6)' % where)
    try:
        plain, spans = parse_markup(s)
    except ValueError as e:
        return s, [], errs + ['%s: %s' % (where, e)]
    if spans and not allow_bold:
        errs.append('%s: no bold (asterisk) words here' % where)
    for a, b in spans:
        w = plain[a:b]
        if w != w.strip() or '\n' in w:
            errs.append('%s: the bold word "*%s*" has a space or a line break at an end or inside' % (where, w.replace('\n', '\\n')))
    if any(spans[k][1] == spans[k + 1][0] for k in range(len(spans) - 1)):
        errs.append('%s: two bold words touch ("**")' % where)
    if spans and spans[-1][1] == len(plain):
        errs.append('%s: a bold word cannot end the text (the game makes a link only when more text follows it): put a word or a full stop after it' % where)
    return plain, spans, errs


def card_text_problems(where, tid, info, plain, spans, words, adv, lh):
    """Does the card text `plain` (bold spans `spans`) lay out in its rectangle the way the game will draw it, and does
    every bold word become the link to the definition the glossary gives it? words: {UPPER word: definition id}."""
    errs = []
    t, l, b, r = info['rect']
    raw = enc_text(plain)
    styl = None if tid in NO_STYLE_RUNS else dec_styl(enc_styl(plain, spans))[0]
    text, runs = ant_clean(raw, styl or [])
    draws, links, nlines, used, too_long = ant_layout(text, runs, l, t, r, b, adv, lh)
    lines = (b - t) // lh
    if used < len(text):
        errs.append('%s: %d lines hold only the first %d of its %d characters (the rectangle is %d x %d px, %d lines of %d px): '
                    'shorten it' % (where, lines, used, len(text), r - l, b - t, lines, lh))
    elif t + 4 + nlines * lh > CARD_BOTTOM:
        errs.append('%s: %d lines reach row %d, the navigation strip starts at row %d: shorten it' % (where, nlines, t + 4 + nlines * lh, CARD_BOTTOM))
    if too_long:
        errs.append('%s: a word is wider than the %d px of the rectangle (line %d): break it or shorten it' % (where, r - l, too_long[0] + 1))
    if used < len(text):
        pass                                           # the links of the text that did not fit are not worth reporting
    elif ink(b''.join(d[3] for d in draws)) != ink(text[:used]):
        errs.append('%s: the game draws part of this text twice or not at all around a bold word that wraps (a bold word that does not '
                    'start its line must not follow a character other than a space)' % where)
    if words is not None:                              # the link checks need the complete glossary
        got = [words.get(seg.lstrip(b' ').decode('latin-1').upper()) for _, _, seg in links]
        want = [words.get(plain[a:bb].upper()) for a, bb in spans]
        for k, (a, bb) in enumerate(spans):
            if want[k] is None:
                errs.append('%s: the bold word "%s" is not a link word of glossary.json (bold is only for link words)' % (where, plain[a:bb]))
        if None not in want and got != want and used >= len(text):
            bad = [plain[a:bb] for k, (a, bb) in enumerate(spans) if k >= len(got) or got[k] != want[k]]
            errs.append('%s: the link word(s) %s are split by a line break or begin a line after a break in them, so the game would not make '
                        'them links: reword so each bold word lies whole on one line' % (where, ', '.join('"%s"' % w for w in bad[:3])))
        need = [d for d in info.get('needs', []) if d not in want]
        if need:
            errs.append('%s: this card has to contain, in bold, the link word of definition(s) %s (docs/clean_pack/texts.md)' % (where, ', '.join(map(str, need))))
    if info.get('chars') and len(plain) < 0.5 * info['chars']:
        WARNINGS.append('%s: %d characters, the original card had about %d (aim for 70%% to 110%%)' % (where, len(plain), info['chars']))
    return errs


def cat_texts(errors):
    """The cards, the pop-up texts, the glossary and the two save prompts (docs/clean_pack/texts.md); sources in
    src/texts/: cards.json, glossary.json, popups.json, prompts.json. The card layouts (type 17) come from
    docs/clean_pack/data/card_layouts.json and are always built."""
    try:
        lay = data('card_layouts')
    except OSError:
        return
    for cid, recs in lay['cards'].items():
        yield 'SHARED/17/%s.bin' % cid, enc_card_layout(recs)
    d = os.path.join(SRC, 'texts')
    if not os.path.isdir(d):
        return

    def load(name):
        path = os.path.join(d, name + '.json')
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding='utf-8') as f:
                obj = json.load(f)
        except ValueError as e:
            errors.append('texts/%s.json: %s' % (name, e))
            return None
        if not isinstance(obj, dict):
            errors.append('texts/%s.json: a JSON object' % name)
            return None
        return obj

    adv, lh = clean_adv(), line_height()
    texts = lay['texts']

    def put(tid, plain, spans):
        yield 'SHARED/10/%d.bin' % tid, enc_text(plain)
        if tid not in NO_STYLE_RUNS:
            yield 'SHARED/21/%d.bin' % tid, enc_styl(plain, spans)

    # --- the two save prompts and the three unused notes (plain text; 128 and 130 are wrapped by the dialog)
    prompts = load('prompts')
    for key, s in (prompts or {}).items():
        where = 'texts/prompts.json "%s"' % key
        if not key.isdigit() or int(key) not in PROMPT_IDS:
            errors.append('%s: the ids are %s' % (where, list(PROMPT_IDS)))
            continue
        tid = int(key)
        plain, _, errs = check_markup_text(where, s, False)
        if not errs and (tid in (128, 130) or len(plain) > 240):
            if tid in (128, 130):
                lines = wrap_prompt(plain, PROMPT_WIDTH)
                if len(lines) > PROMPT_MAX_LINES:
                    errs.append('%s: %d lines of %d px, the dialog holds %d: shorten it' % (where, len(lines), PROMPT_WIDTH, PROMPT_MAX_LINES))
                if any(text_width(4, ln) > PROMPT_WIDTH for ln in lines):
                    errs.append('%s: a word is wider than %d px' % (where, PROMPT_WIDTH))
            else:
                errs.append('%s: at most 240 characters (the note is never shown)' % where)
        errors.extend(errs)
        if not errs:
            yield from put(tid, plain, [])

    # --- the glossary: one entry (link word, pop-up definition) for each of the 26 ids
    gl = load('glossary')
    words, terms = {}, {}
    for key, e in (gl or {}).items():
        where = 'texts/glossary.json "%s"' % key
        if not key.isdigit() or int(key) not in GLOSSARY_IDS:
            errors.append('%s: the ids are %s' % (where, GLOSSARY_IDS))
            continue
        tid = int(key)
        if not isinstance(e, dict) or set(e) != {'word', 'term', 'text'} or not all(isinstance(e[k], str) for k in e):
            errors.append('%s: {"word": ..., "term": ..., "text": ...}' % where)
            continue
        bad = False
        if not re.fullmatch(r"[A-Za-z][A-Za-z' -]{0,30}", e['word']) or e['word'] != e['word'].strip() or '  ' in e['word']:
            errors.append('%s: "word" is 1 to 31 letters (space, apostrophe, hyphen inside), the form the card texts write in bold' % where)
            bad = True
        if identity_problem(e['word']) or identity_problem(e['term']):
            errors.append('%s: contains a name the pack must not carry (ROADMAP A6)' % where)
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z' -]{0,38}", e['term']) or e['term'] != e['term'].strip():
            errors.append('%s: "term" is the bold head word of the pop-up, letters (space, apostrophe, hyphen inside), at most 39 characters' % where)
            bad = True
        plain, spans, errs = check_markup_text(where + ' text', e['text'], False)
        errors.extend(errs)
        if bad or errs:
            continue
        if e['word'].upper() in words:
            errors.append('%s: the link word "%s" is also the word of definition %d' % (where, e['word'], words[e['word'].upper()]))
            continue
        words[e['word'].upper()] = tid
        terms[tid] = (e['word'], '*%s* - %s' % (e['term'], e['text']))
    # the definitions and the flowchart pop-ups, laid out POPUP_WIDTH px wide (Antipedia.Popup)
    pops = load('popups')
    pop_src = {tid: s for tid, (_, s) in terms.items()}
    for key, s in (pops or {}).items():
        where = 'texts/popups.json "%s"' % key
        if not key.isdigit() or int(key) not in POPUP_IDS:
            errors.append('%s: the ids are %d..%d' % (where, POPUP_IDS[0], POPUP_IDS[-1]))
            continue
        pop_src[int(key)] = s
    for tid, s in sorted(pop_src.items()):
        where = 'texts/%s "%d"' % ('popups.json' if tid in POPUP_IDS else 'glossary.json', tid)
        plain, spans, errs = check_markup_text(where, s, tid in GLOSSARY_IDS)
        if not errs and adv is None:
            errs.append('%s: fonts 2 and 5 are not made yet, cannot check the layout' % where)
        if not errs:
            raw = enc_text(plain)
            text, runs = ant_clean(raw, dec_styl(enc_styl(plain, spans))[0])
            _, _, nlines, used, too_long = ant_layout(text, runs, 0, 0, POPUP_WIDTH, 10000, adv, lh)
            if nlines > POPUP_MAX_LINES:
                errs.append('%s: %d lines at %d px wide, at most %d (the original\'s longest pop-up is 9): shorten it' % (where, nlines, POPUP_WIDTH, POPUP_MAX_LINES))
            if too_long:
                errs.append('%s: a word is wider than %d px' % (where, POPUP_WIDTH))
        errors.extend(errs)
        if not errs:
            yield from put(tid, plain, spans)
    if gl is not None and len(terms) == len(GLOSSARY_IDS):
        yield 'EXE/glossary.bin', enc_glossary([(tid, w) for tid, (w, _) in terms.items()])

    # --- the cards: a caption and a text
    cards = load('cards')
    gloss_ok = len(terms) == len(GLOSSARY_IDS)
    if cards and not gloss_ok:
        WARNINGS.append('texts/cards.json: the bold (link) words are not checked until texts/glossary.json holds all %d valid definitions' % len(GLOSSARY_IDS))
    for key, e in (cards or {}).items():
        where = 'texts/cards.json card %s' % key
        if not key.isdigit() or key not in lay['cards']:
            errors.append('%s: no such card (the ids are 127..179 except as listed in texts.md)' % where)
            continue
        cid = int(key)
        tids = [t for rec in lay['cards'][key] if rec[0] == 'T' for t in rec[2]]
        if not isinstance(e, dict) or set(e) != ({'title', 'text'} if tids else {'title'}):
            errors.append('%s: {"title": ..., "text": ...}%s' % (where, '' if tids else ' (this card has no text, only "title")'))
            continue
        title = e['title']
        errs = []
        if not isinstance(title, str) or not title or len(title) > CARD_TITLE_CHARS or title != title.strip() or any(
                not 32 <= ord(c) < 127 or c in '_*\\' for c in title):
            errs.append('%s title: 1 to %d printable ASCII characters, no underscore or asterisk, no spaces at the ends' % (where, CARD_TITLE_CHARS))
        elif identity_problem(title):
            errs.append('%s title: contains a name the pack must not carry (ROADMAP A6)' % where)
        elif lay.get('labels', {}).get(key) and not title.lower().startswith(lay['labels'][key].lower()):
            WARNINGS.append('%s title: "%s" differs from the label of the box that opens this card ("%s")' % (where, title, lay['labels'][key]))
        if tids:
            tid = tids[0]
            info = texts[str(tid)]
            plain, spans, errs2 = check_markup_text(where + ' text', e['text'], tid not in NO_STYLE_RUNS)
            errs += errs2
            if not errs2:
                if adv is None:
                    errs.append('%s: fonts 2 and 5 are not made yet, cannot check the layout' % where)
                else:
                    errs += card_text_problems(where + ' text', tid, info, plain, spans, words if gloss_ok else None, adv, lh)
                if tid == 865 and len(plain.split('\n')) > 12:
                    errs.append('%s text: at most 12 lines' % where)
        errors.extend(errs)
        if not errs:
            yield 'SHARED/19/%d.bin' % cid, enc_card_name(title)
            if tids:
                yield from put(tids[0], plain, spans)


def check_texts_roundtrip(zip_path):
    """--roundtrip=<zip>: every text-category resource of the pack decoded and encoded again. Card layouts (17), captions (19)
    and the glossary byte for byte; texts (10) and style runs (21) through the maker's markup (asterisks for bold) and back,
    compared by what the game sees (Antipedia.Text: the cleaned text and its bold spans; for 128 / 130 the bytes up to the
    first NUL) and, for the card texts, by the lines the game draws and the links it makes. Returns (counts, notes,
    problems); notes say which texts are not byte-identical and why (the originals carry editor debris, a second NUL and
    underline runs that the game does not draw differently)."""
    counts = dict(texts=0, exact=0, view=0, layout=0, same_layout=0, layouts=0, names=0, glossary=0)
    notes, problems = [], []
    lay = data('card_layouts')
    adv, lh = original_adv(), line_height()
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for m in data('texts'):
            tid = m['id']
            raw = z.read('SHARED/10/%d.bin' % tid) if 'SHARED/10/%d.bin' % tid in names else None
            if raw is None:
                problems.append('SHARED/10/%d.bin: not in the pack' % tid)
                continue
            styl = z.read('SHARED/21/%d.bin' % tid) if 'SHARED/21/%d.bin' % tid in names else None
            counts['texts'] += 1
            try:
                runs = dec_styl(styl)[0] if styl is not None else []
                if styl is not None and {o[:4] for o in dec_styl(styl)[1]} != {STYL_FIXED}:
                    notes.append('SHARED/21/%d.bin: style fields other than %s' % (tid, STYL_FIXED))
                if tid in PROMPT_IDS:
                    n = raw.find(b'\0')
                    text, vruns = raw[:n if n >= 0 else len(raw)], []
                else:
                    text, vruns = ant_clean(raw, runs)
                spans = bold_spans(vruns, len(text))
                mk = markup_of(text, spans)
                plain, spans2 = parse_markup(mk)
            except (ValueError, struct.error) as e:
                problems.append('texts %d: cannot be written as markup: %s' % (tid, e))
                continue
            raw2 = enc_text(plain)
            styl2 = None if tid in NO_STYLE_RUNS else enc_styl(plain, spans2)
            if tid in PROMPT_IDS:
                text2, vruns2 = raw2[:raw2.find(b'\0')], []
            else:
                text2, vruns2 = ant_clean(raw2, dec_styl(styl2)[0] if styl2 else [])
            if (text2, bold_spans(vruns2, len(text2))) != (text, spans):
                problems.append('texts %d: the game would see something else after text -> markup -> text' % tid)
                continue
            counts['view'] += 1
            if raw2 == raw and styl2 == styl:
                counts['exact'] += 1
            else:
                why = []
                if raw2 != raw:
                    why.append('text bytes differ (%s)' % ', '.join(
                        w for w, c in (('editor debris cleaned by the game', len(raw) > 0 and ant_clean(raw, runs)[0] != raw[:raw.find(b'\0')]),
                                       ('a second NUL / DOS tail', raw.count(b'\0') > 1 or raw[-1:] != b'\0'),
                                       ('Mac Roman character', any(c > 127 for c in raw))) if c) or 'other')
                if styl2 != styl and styl is not None:
                    why.append('style runs differ (%s)' % (
                        'underline runs, which the game draws as plain text' if any(f not in (0, BOLD) for _, f in runs) else
                        'positions moved by the cleaning' if ant_clean(raw, runs)[1] != runs else
                        'an extra plain run with other font fields, which the game does not read'))
                notes.append('text %d: not byte-identical: %s' % (tid, '; '.join(why)))
            info = lay['texts'].get(str(tid))
            if info and info['kind'] == 'card':
                counts['layout'] += 1
                t, l, b, r = info['rect']
                a = ant_layout(text, vruns, l, t, r, b, adv, lh)
                c2 = ant_layout(text2, vruns2, l, t, r, b, adv, lh)
                if a == c2:
                    counts['same_layout'] += 1
                else:
                    notes.append('text %d: the lines the game draws differ after the round trip (only where the original has underline runs or a word wraps oddly)' % tid)
        for cid, recs in lay['cards'].items():
            n = 'SHARED/17/%s.bin' % cid
            if n not in names:
                problems.append('%s: not in the pack' % n)
                continue
            d = z.read(n)
            try:
                same = dec_card_layout(d) == recs and enc_card_layout(recs) == d
            except (ValueError, struct.error):
                same = False
            counts['layouts'] += same
            if not same:
                problems.append('%s: docs/clean_pack/data/card_layouts.json is not the pack\'s card (run tools/clean_pack/make_card_layouts.py)' % n)
            n = 'SHARED/19/%s.bin' % cid
            if n not in names:
                problems.append('%s: not in the pack' % n)
                continue
            d = z.read(n)
            title = d[:-1].decode('latin-1').replace('_', ' ')
            if enc_card_name(title) == d:
                counts['names'] += 1
            else:
                problems.append('%s: not byte-identical after decode + encode' % n)
        if 'EXE/glossary.bin' not in names:
            problems.append('EXE/glossary.bin: not in the pack')
        else:
            d = z.read('EXE/glossary.bin')
            ents = dec_glossary(d)
            e = enc_glossary(ents)
            # byte-identical up to the end entry (whose word the game never compares)
            if len(e) == len(d) and e[:-34] == d[:-34] and e[-2:] == d[-2:] and len(ents) == data('embedded')['glossary_entries']:
                counts['glossary'] = len(ents)
            else:
                problems.append('EXE/glossary.bin: not byte-identical after decode + encode (end entry aside)')
    return counts, notes, problems


# ------------------------------------------------------------------------------------------------ window layouts
# HCEGANT type 0 (docs/clean_pack/layouts.md; FILE_FORMATS "Window layouts"; the reader is OpenSimAnt.Data/Layouts.cs).
# Functional data (rectangles, edge references and modes, item types, schemes, flags, bitmap ids, the colour-scheme and
# UI tables) is docs/clean_pack/data/window_layouts.json, made by tools/clean_pack/make_layouts.py from the player's pack
# and always built; the few words inside items are the makers' (src/layouts/texts.json). Little endian.
LAYOUT_TEXT_AT = {0x05: 0x2a, 0x09: 0x2a, 0x0c: 0x2a, 0x10: 0x2e, 0x11: 0x2e, 0x12: 0x2e}   # item type -> where its string starts
LAYOUT_HEADER = 0x2c
LAYOUT_WINDOWS = range(34)
LAYOUT_TABLES = (128, 129, 131)
# texts whose room is not their item's width less 8: the file dialog's drive label is not clipped (the row to its right is free); the
# message box 30 is only as wide as its widest line + 8 (Main.DrawMessageBox, at least 58), so its "continue" line stays within the
# width the original's own line has in font 3 (84 px)
LAYOUT_ROOM = {'22.10': 112, '30.2': 84}
LAYOUT_MISC_WORDS = (4, 5, 12, 13, 15, 16, 17, 18, 19, 20, 21)    # the header's other words (+8 .. +2A), stored as an offset -> value map


def layout_text_ref(wid, k, s):
    """How a layout item's string is carried in window_layouts.json: a printf format the code reads ({"format"}) and a drive
    letter ({"literal"}) are functional and kept; any other string is the maker's new text, looked up by key "window.item"."""
    if '%' in s:
        return {'format': s}
    if re.fullmatch(r'[A-H]:', s):
        return {'literal': s}
    return {'key': '%d.%d' % (wid, k)}


def dec_layout(d):
    """A window layout resource -> (window, dead): the window as window_layouts.json holds it except that a text item carries
    its raw string as "string"; dead = the bytes that mean nothing (the item table's memory segments, the two padding bytes
    behind each string, which hold editor debris in some layouts), {"seg": [...], "pad": [[b, b] or None, ...]}."""
    w = struct.unpack_from('<22H', d, 0)
    n, size = w[6], w[7]
    if size != len(d) or struct.unpack_from('<H', d, LAYOUT_HEADER)[0] != LAYOUT_HEADER + 4 * n:
        raise ValueError('the size or the first item is not where the header says')
    win = {'rect': list(struct.unpack_from('<4h', d, 0)), 'requested': list(struct.unpack_from('<4h', d, 0x10)), 'flags': w[14],
           'misc': {str(2 * i): struct.unpack_from('<h', d, 2 * i)[0] for i in LAYOUT_MISC_WORDS if w[i]}, 'items': []}
    dead, pos = {'seg': [], 'pad': []}, LAYOUT_HEADER + 4 * n
    for k in range(n):
        o, seg = struct.unpack_from('<HH', d, LAYOUT_HEADER + 4 * k)
        if o != pos:
            raise ValueError('item %d is not where the previous one ends' % k)
        state, typ, length = struct.unpack_from('<BBH', d, o + 0x20)
        flags, scheme, alt = struct.unpack_from('<HBB', d, o + 0x24)
        it = {'rect': list(struct.unpack_from('<4h', d, o)), 'off': list(struct.unpack_from('<4h', d, o + 8)),
              'ref': list(struct.unpack_from('<4H', d, o + 16)), 'mode': list(struct.unpack_from('<4H', d, o + 24)),
              'state': state, 'type': typ, 'flags': flags, 'scheme': scheme, 'alt': alt}
        so = LAYOUT_TEXT_AT.get(typ)
        dead['seg'].append(seg)
        if so is None:
            it['tail'] = list(d[o + 0x28:o + length])
            dead['pad'].append(None)
        else:
            s = d[o + so:o + length]
            nul = s.find(0)
            if nul < 0 or len(s) - nul - 1 != 2:
                raise ValueError('item %d: the string is not NUL-terminated with two bytes after it' % k)
            it['tail'] = list(d[o + 0x28:o + so])
            it['string'] = s[:nul].decode('latin-1')
            dead['pad'].append(list(s[nul + 1:]))
        win['items'].append(it)
        pos = o + length
    if pos != len(d):
        raise ValueError('%d bytes left over' % (len(d) - pos))
    return win, dead


def enc_layout(win, texts, dead=None):
    """The inverse of dec_layout, for window_layouts.json's window (items carry "text": {"format" | "literal" | "key"}; the key's
    string comes from texts). dead as dec_layout's, or None for zero segments and zero padding (what the pack carries)."""
    items = win['items']
    n = len(items)
    out = bytearray(LAYOUT_HEADER + 4 * n)
    body = bytearray()
    for k, it in enumerate(items):
        so = LAYOUT_TEXT_AT.get(it['type'])
        tail = bytes(it['tail'])
        ref = it.get('text')
        if (so is None) != (ref is None) or (so is not None and len(tail) != so - 0x28):
            raise ValueError('item %d: type %#x and its text do not agree' % (k, it['type']))
        if ref is None:
            string = b''
        else:
            s = ref['format'] if 'format' in ref else ref['literal'] if 'literal' in ref else texts[ref['key']]
            pad = (dead or {}).get('pad', [None] * n)[k] or [0, 0]
            string = s.encode('latin-1') + b'\0' + bytes(pad)
        length = 0x28 + len(tail) + len(string)
        struct.pack_into('<HH', out, LAYOUT_HEADER + 4 * k, LAYOUT_HEADER + 4 * n + len(body), (dead or {}).get('seg', [0] * n)[k])
        body += struct.pack('<4h4h4H4HBBHHBB', *it['rect'], *it['off'], *it['ref'], *it['mode'], it['state'], it['type'], length,
                            it['flags'], it['scheme'], it['alt']) + tail + string
    struct.pack_into('<4h', out, 0, *win['rect'])
    struct.pack_into('<HH', out, 0xc, n, len(out) + len(body))
    struct.pack_into('<4h', out, 0x10, *win['requested'])
    struct.pack_into('<H', out, 0x1c, win['flags'])
    for off, v in win['misc'].items():
        struct.pack_into('<h', out, int(off), v)
    return bytes(out + body)


def layout_text_info(wid, k, it, s):
    """What a maker needs to know about the room of the item's text (window_layouts.json "texts")."""
    l, t, r, b = it['rect']
    key = '%d.%d' % (wid, k)
    align = (it['flags'] & 0x180) >> 7
    return {'window': wid, 'item': k, 'type': it['type'], 'font': it['tail'][0], 'align': ('centre', 'left', 'right', 'centre')[align],
            'clip': bool(it['flags'] & 0x200), 'rect': it['rect'], 'room_px': LAYOUT_ROOM.get(key, r - l - 8), 'chars': len(s)}


def layout_entry(wid, d):
    """(window, strings, dead, infos) of a layout resource: the window as window_layouts.json holds it, the new-text strings by
    key, the dead bytes, and the text infos by key."""
    win, dead = dec_layout(d)
    strings, infos = {}, {}
    for k, it in enumerate(win['items']):
        if 'string' in it:
            s = it.pop('string')
            it['text'] = layout_text_ref(wid, k, s)
            if 'key' in it['text']:
                strings[it['text']['key']] = s
                infos[it['text']['key']] = layout_text_info(wid, k, it, s)
    return win, strings, dead, infos


def layout_text_problems(key, s, info):
    """The reasons a new text of a layout item breaks docs/clean_pack/layouts.md; []."""
    where = 'layouts/texts.json "%s"' % key
    if not isinstance(s, str):
        return ['%s: a string' % where]
    errs = []
    if not s or s != s.strip(' '):
        errs.append('%s: not empty, no spaces at the ends' % where)
    if any(not 32 <= ord(c) < 127 for c in s) or '%' in s or '\\' in s:
        errs.append('%s: printable ASCII only, no percent sign and no backslash (the game treats % as a format and then draws no text)' % where)
    if identity_problem(s):
        errs.append('%s: contains a name the pack must not carry (ROADMAP A6)' % where)
    px = text_width(info['font'], s) if not errs else 0
    if px is None:
        errs.append('%s: font %d is not made yet, cannot check the width' % (where, info['font']))
    elif px > info['room_px']:
        errs.append('%s: %d px wide in font %d, the room is %d px' % (where, px, info['font'], info['room_px']))
    return errs


def cat_layouts(errors):
    """HCEGANT/0/<id>.bin, the 34 windows and the UI tables 128 / 129 / 131, from docs/clean_pack/data/window_layouts.json; the words
    inside items from src/layouts/texts.json {"<window>.<item>": "text"} (12 keys). A window whose words are not all given (and
    valid) is not built, so the missing list shows it."""
    try:
        lay = data('window_layouts')
    except OSError:
        return
    texts, path = {}, os.path.join(SRC, 'layouts', 'texts.json')
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                src = json.load(f)
        except ValueError as e:
            errors.append('layouts/texts.json: %s' % e)
            src = {}
        if not isinstance(src, dict):
            errors.append('layouts/texts.json: an object {"<window>.<item>": "text"}')
            src = {}
        for key, s in src.items():
            if key not in lay['texts']:
                errors.append('layouts/texts.json "%s": no such text (the keys are %s)' % (key, ', '.join(lay['texts'])))
                continue
            errs = layout_text_problems(key, s, lay['texts'][key])
            errors.extend(errs)
            if not errs:
                texts[key] = s
    for wid, win in lay['windows'].items():
        keys = [it['text']['key'] for it in win['items'] if 'key' in (it.get('text') or {})]
        if all(k in texts for k in keys):
            yield 'HCEGANT/0/%s.bin' % wid, enc_layout(win, texts)
    for tid, table in lay['tables'].items():
        yield 'HCEGANT/0/%s.bin' % tid, bytes(table)


def check_layouts_roundtrip(zip_path):
    """--roundtrip=<zip>: every layout of the pack decoded to window_layouts.json's form and encoded back. Returns (counts, notes,
    problems). byte-identical with the original's dead bytes (item table segments, string padding) for all; with zeros there
    for those whose dead bytes are zero already; the others must differ only at dead bytes."""
    counts = dict(windows=0, same_json=0, exact=0, zero=0, dead_only=0, tables=0)
    notes, problems = [], []
    lay = data('window_layouts')
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for wid in LAYOUT_WINDOWS:
            n = 'HCEGANT/0/%d.bin' % wid
            if n not in names:
                problems.append('%s: not in the pack' % n)
                continue
            d = z.read(n)
            counts['windows'] += 1
            try:
                win, strings, dead, infos = layout_entry(wid, d)
            except (ValueError, struct.error) as e:
                problems.append('%s: %s' % (n, e))
                continue
            if win == lay['windows'].get(str(wid)) and all(lay['texts'].get(k) == v for k, v in infos.items()):
                counts['same_json'] += 1
            else:
                problems.append('%s: docs/clean_pack/data/window_layouts.json is not the pack\'s layout (run tools/clean_pack/make_layouts.py)' % n)
            if enc_layout(win, strings, dead) == d:
                counts['exact'] += 1
            else:
                problems.append('%s: not byte-identical after decode + encode' % n)
                continue
            plain = enc_layout(win, strings)
            if plain == d:
                counts['zero'] += 1
            else:
                a, b = enc_layout(win, strings, dict(dead, seg=[0xffff] * len(win['items']), pad=[None if p is None else [255, 255] for p in dead['pad']])), plain
                free = {i for i in range(len(a)) if a[i] != b[i]}
                if len(plain) == len(d) and all(d[i] == plain[i] or i in free for i in range(len(d))):
                    counts['dead_only'] += 1
                else:
                    problems.append('%s: differs from the pack outside the dead bytes with zeros there' % n)
        for tid in LAYOUT_TABLES:
            n = 'HCEGANT/0/%d.bin' % tid
            if n in names and z.read(n) == bytes(lay['tables'].get(str(tid), [])):
                counts['tables'] += 1
            else:
                problems.append('%s: not the pack\'s table (run tools/clean_pack/make_layouts.py)' % n)
    return counts, notes, problems


# ------------------------------------------------------------------------------------------------ sound effects
# docs/clean_pack/sounds.md: SOUND/5/<id> (the 4-bit delta samples) and EXE/soundbank.bin (the sound driver's tables)
SFX_RATE = 5576                      # the WAV's sample rate (the driver mixes at 5575.6 Hz)
SFX_MAX_FRAMES = 16000
SFX_FRAMES_TOL = 0.20                # frame count within 20 % of the measured one
SFX_PEAK_RANGE = (0.80, 1.10)        # peak (8-bit units) within 80..110 % of the measured one
SFX_EDGE = 6                         # the first and last 8 samples within +-6
SFX_SNR_MIN, SFX_SNR_NOTE = 9.0, 14.0      # coding error: refused below, noted below the second
SFX_ITERATIONS, SFX_STALE = 30, 6    # table refinement passes, stop after this many without a better one


def sfx_required():
    """The sound ids the driver can reach through a sample instrument (35): the ones a complete pack needs."""
    return sorted({i['sample_sound'] for i in data('embedded')['instruments'] if i['device'] == 'sample'})


def dec_sample(d):
    """SOUND type 5 -> signed 8-bit samples, exactly OpenSimAnt.Data Sounds.Decode: a table of 16 signed deltas, then 4-bit
    codes (high nibble first); the running sum wraps in 8 bits."""
    if len(d) < 16:
        return []
    table = [b - 256 if b > 127 else b for b in d[:16]]
    out, s = [], 0
    for b in d[16:]:
        for c in (b >> 4, b & 15):
            s = ((s + table[c] + 128) & 255) - 128
            out.append(s)
    return out


def pack_sample(table, codes):
    blob = bytearray(e & 255 for e in table)
    for i in range(0, len(codes), 2):
        blob.append(codes[i] << 4 | codes[i + 1])
    return bytes(blob)


def enc_sample_lossless(t, table):
    """The samples `t` (decoded from an original) coded with the original's own table: at each step the wanted delta (mod 256)
    and the lowest code whose table entry is that delta. Same samples back; the same bytes when the table entries differ."""
    lowest = {}
    for c, e in enumerate(table):
        lowest.setdefault(e, c)
    s, codes = 0, []
    for x in t:
        codes.append(lowest[((x - s + 128) & 255) - 128])
        s = x
    return pack_sample(table, codes)


def _sample_pass(t, table):
    """One greedy encoding pass (sounds.md E1): at each sample the code whose step lands nearest to it without leaving
    -128..127 (ties: the smaller step, then the lower code). Returns the codes, the squared error and, per code, the sum of the
    ideal deltas and the count (for the next table)."""
    near = [min(range(16), key=lambda c: (abs(d - table[c]), abs(table[c]), c)) for d in range(-255, 256)]
    sums, counts, codes = [0] * 16, [0] * 16, []
    s = err = 0
    for x in t:
        d = x - s
        c = near[d + 255]
        ns = s + table[c]
        if ns < -128 or ns > 127:                               # rare: the nearest step would leave the 8-bit range
            c = min((k for k in range(16) if -128 <= s + table[k] <= 127), key=lambda k: (abs(d - table[k]), abs(table[k]), k))
            ns = s + table[c]
        sums[c] += d
        counts[c] += 1
        codes.append(c)
        err += (x - ns) ** 2
        s = ns
    return codes, err, sums, counts


def _rising(n, top):
    """n distinct integers rising from 1 to about `top`."""
    v = [max(1, int(round(top ** (i / (n - 1))))) for i in range(n)]
    for i in range(1, n):
        if v[i] <= v[i - 1]:
            v[i] = v[i - 1] + 1
    return v


def _separate(mags, top):
    """Sorted, distinct magnitudes in 1..top."""
    mags = sorted(min(top, max(1, m)) for m in mags)
    for i in range(1, len(mags)):
        if mags[i] <= mags[i - 1]:
            mags[i] = mags[i - 1] + 1
    for i in range(len(mags) - 2, -1, -1):
        if mags[i] >= mags[i + 1]:
            mags[i] = mags[i + 1] - 1
    return mags


def enc_sample(t):
    """The lossy encoder for a maker's samples (signed 8-bit list, even length): a table found by repeated greedy passes
    (sounds.md E1). Returns (SOUND/5 bytes, signal-to-noise ratio in dB of the decoded result against `t`)."""
    t = list(t)
    energy = sum(x * x for x in t)
    if energy == 0:
        raise ValueError('silent')
    top = max(abs(b - a) for a, b in zip([0] + t, t))
    p = min(127, max(8, -(-9 * top // 10)))
    table = [0] + _rising(7, p) + [-m for m in _rising(8, min(128, p + 1))]
    best, stale = None, 0
    for _ in range(SFX_ITERATIONS):
        codes, err, sums, counts = _sample_pass(t, table)
        if best is None or err < best[0]:
            best, stale = (err, list(table), codes), 0
        else:
            stale += 1
            if stale >= SFX_STALE:
                break
        new = [0] + [int(math.floor(sums[c] / counts[c] + 0.5)) if counts[c] else table[c] for c in range(1, 16)]
        pos = _separate(new[1:8], 127)
        neg = _separate([-v for v in new[8:16]], 128)
        table = [0] + pos + [-m for m in neg]
    err, table, codes = best
    snr = 99.0 if err == 0 else 10 * math.log10(energy / err)
    return pack_sample(table, codes), snr


def read_wav(raw):
    """(rate, channels, bits, samples) of a RIFF PCM file holding only a 'fmt ' and a 'data' chunk; ValueError otherwise."""
    if len(raw) < 12 or raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
        raise ValueError('not a RIFF/WAVE file')
    p, fmt, pcm, ids = 12, None, None, []
    while p + 8 <= len(raw):
        cid, size = raw[p:p + 4], struct.unpack_from('<I', raw, p + 4)[0]
        body = raw[p + 8:p + 8 + size]
        if len(body) < size:
            raise ValueError('a chunk is cut short')
        ids.append(cid.decode('latin-1'))
        if cid == b'fmt ' and size >= 16:
            fmt = struct.unpack_from('<HHIIHH', body, 0)
        elif cid == b'data':
            pcm = body
        p += 8 + size + (size & 1)
    if ids != ['fmt ', 'data'] or fmt is None:
        raise ValueError("chunks %s, expected exactly 'fmt ' and 'data'" % ids)
    tag, ch, rate, _bps, _align, bits = fmt
    if tag != 1:
        raise ValueError('not PCM (format tag %d)' % tag)
    if bits != 16 or len(pcm) % 2:
        raise ValueError('%d bits, must be 16' % bits)
    return rate, ch, bits, list(struct.unpack('<%dh' % (len(pcm) // 2), pcm))


def sfx_problems(where, ident, t):
    """The checks of sounds.md section 4.1 / 6 on the 8-bit samples of one file (before the SNR). A required id is also
    compared with the measurements (frames, peak)."""
    errs = []
    if not t:
        return ['%s: no samples' % where]
    if len(t) > SFX_MAX_FRAMES:
        errs.append('%s: %d samples, at most %d' % (where, len(t), SFX_MAX_FRAMES))
    peak = max(abs(x) for x in t)
    if peak == 0:
        errs.append('%s: silent' % where)
    row = next((r for r in data('sounds') if r['id'] == ident), None)
    if ident in sfx_required() and row:
        lo, hi = row['samples'] * (1 - SFX_FRAMES_TOL), row['samples'] * (1 + SFX_FRAMES_TOL)
        if not lo <= len(t) <= hi:
            errs.append('%s: %d samples, the spec says %d (within %d %%: %d..%d)'
                        % (where, len(t), row['samples'], SFX_FRAMES_TOL * 100, lo, hi))
        lo, hi = row['peak'] * SFX_PEAK_RANGE[0], row['peak'] * SFX_PEAK_RANGE[1]
        if not lo <= peak <= hi:
            errs.append('%s: peak %d (8-bit units), the spec says %d (%.0f..%.0f)' % (where, peak, row['peak'], lo, hi))
    if any(abs(x) > SFX_EDGE for x in t[:8] + t[-8:]):
        errs.append('%s: the first and last 8 samples must be within +-%d (8-bit units): start and end at zero' % (where, SFX_EDGE))
    return errs


def to_8bit(x16):
    """16-bit sample -> signed 8-bit, rounded (sounds.md E1 step 1), odd counts padded with one zero."""
    t = [max(-128, min(127, (x + 128) >> 8)) for x in x16]
    if len(t) % 2:
        t.append(0)
    return t


def cat_sounds(errors):
    """src/sounds/sfx_<id>.wav (RIFF PCM mono 16-bit 5,576 Hz) -> SOUND/5/<id>.bin, with the checks of sounds.md."""
    d = os.path.join(SRC, 'sounds')
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.startswith('sfx_') or not name.endswith('.wav'):
            continue
        where = 'sounds/' + name
        m = re.fullmatch(r'sfx_(\d+)\.wav', name)
        if not m or int(m.group(1)) not in range(57):
            errors.append('%s: sfx_<id>.wav with an id 0..56' % where)
            continue
        ident = int(m.group(1))
        try:
            with open(os.path.join(d, name), 'rb') as f:
                rate, ch, _bits, x16 = read_wav(f.read())
        except ValueError as e:
            errors.append('%s: %s' % (where, e))
            continue
        if ch != 1 or rate != SFX_RATE:
            errors.append('%s: %d channel(s) at %d Hz, must be mono at %d Hz' % (where, ch, rate, SFX_RATE))
            continue
        t = to_8bit(x16)
        errs = sfx_problems(where, ident, t)
        if errs:
            errors.extend(errs)
            continue
        blob, snr = enc_sample(t)
        if snr < SFX_SNR_MIN:
            errors.append('%s: the 4-bit code reproduces it at %.1f dB signal-to-noise, at least %.0f needed: soften it (less high '
                          'frequency, a gentler attack, less noise)' % (where, snr, SFX_SNR_MIN))
            continue
        if snr < SFX_SNR_NOTE:
            WARNINGS.append('%s: the 4-bit code reproduces it at %.1f dB signal-to-noise (below %.0f: rough)' % (where, snr, SFX_SNR_NOTE))
        yield 'SOUND/5/%d.bin' % ident, blob


# ------------------------------------------------------------------------------------------------ FM patches and the sound bank
FM_PATCH_TABLE = [('fm25', (25,)), ('fm53', (53,)), ('fm3', (3,)), ('fm54', (54,)), ('fm35', (35,)), ('fm46', (46,)),
                  ('fm50', (50,)), ('fm51', (51,)), ('fm48', (48,)), ('fm0', (0,)), ('fm9', (9,)), ('fm15', (15, 16)),
                  ('fm17', (17,)), ('fm18', (18,)), ('fm19', (19,)), ('fm30', (30,))]
FM_EFFECT_KEY_REQUIRED = {'fm9', 'fm15', 'fm17', 'fm18', 'fm19', 'fm30', 'fm35'}
FM_OPERATOR = (('tremolo', 0, 1), ('vibrato', 0, 1), ('sustain', 0, 1), ('ksr', 0, 1), ('multiple', 0, 15), ('ksl', 0, 3),
               ('level', 0, 63), ('attack', 0, 15), ('decay', 0, 15), ('sustain_level', 0, 15), ('release', 0, 15))
FM_CARRIER_LEVEL_MAX = 40
FM_DEFAULT_KEY = 60
SB_SIZE = 2856
SB_SEG = 0x55B3                       # the segment of the far pointers in the instrument table
SB_FM_AT, SB_FM_N = 0x202, 20         # DS offsets of the FM records (16 bytes) and the sample records (32 bytes)
SB_SMP_AT, SB_SMP_N = 0x342, 53
SB_CHANNEL_PRIORITY = [0, 7, 7, 7, 7] + [5] * 9               # MIDI channels 0..13
SB_CHANNEL_INSTRUMENT = [0, 25, 53, 3, 54, 35, 46, 50, 51, 48, 0, 12, 43, 52]


def fm_op_bytes(o):
    """An operator's registers 0x20, 0x40, 0x60, 0x80."""
    return (o['tremolo'] << 7 | o['vibrato'] << 6 | o['sustain'] << 5 | o['ksr'] << 4 | o['multiple'],
            o['ksl'] << 6 | o['level'], o['attack'] << 4 | o['decay'], o['sustain_level'] << 4 | o['release'])


def fm_op_fields(b0, b1, b2, b3):
    return dict(tremolo=b0 >> 7, vibrato=b0 >> 6 & 1, sustain=b0 >> 5 & 1, ksr=b0 >> 4 & 1, multiple=b0 & 15,
                ksl=b1 >> 6, level=b1 & 63, attack=b2 >> 4, decay=b2 & 15, sustain_level=b3 >> 4, release=b3 & 15)


FM_EXTRA = dict(c0_hi=0, wave_c=0, wave_m=0, octave=0, b15=0)       # the bytes of a record that a clean patch leaves 0


def enc_fm_record(p, x=None):
    """The 16-byte FM record (sounds.md E2) of a patch's fields; x = the bytes a clean patch leaves 0."""
    x = dict(FM_EXTRA, **(x or {}))
    c, m = fm_op_bytes(p['carrier']), fm_op_bytes(p['modulator'])
    return (bytes([c[0], m[0], c[1], m[1], c[2], m[2], c[3], m[3], x['c0_hi'] << 4 | p['feedback'] << 1 | p['connection'],
                   x['wave_c'], x['wave_m']]) + struct.pack('<hh', x['octave'], p['velocity_offset']) + bytes([x['b15']]))


def dec_fm_record(b):
    """(fields, extra): the inverse of enc_fm_record."""
    p = dict(velocity_offset=struct.unpack_from('<h', b, 13)[0], feedback=b[8] >> 1 & 7, connection=b[8] & 1,
             modulator=fm_op_fields(b[1], b[3], b[5], b[7]), carrier=fm_op_fields(b[0], b[2], b[4], b[6]))
    return p, dict(c0_hi=b[8] >> 4, wave_c=b[9], wave_m=b[10], octave=struct.unpack_from('<h', b, 11)[0], b15=b[15])


def dec_sample_record(b):
    return dict(head=bytes(b[0:6]), loop=b[6] | b[7] << 8, loop_flag=b[8], base_octave=b[9], transpose=struct.unpack_from('<h', b, 10)[0],
                w12=b[12] | b[13] << 8, name=bytes(b[14:29]), sound=b[29] | b[30] << 8, b31=b[31])


def enc_sample_record(r):
    return (r['head'] + struct.pack('<HBBhH', r['loop'], r['loop_flag'], r['base_octave'], r['transpose'], r['w12']) + r['name']
            + struct.pack('<HB', r['sound'], r['b31']))


def dec_soundbank(d):
    """EXE/soundbank.bin -> the model: channels (priority, instrument), 20 FM records (fields + extra), 53 sample records,
    56 effects (key, priority, instrument, velocity), 56 instruments (device, DS offset, segment)."""
    if len(d) != SB_SIZE:
        raise ValueError('%d bytes, expected %d' % (len(d), SB_SIZE))
    return dict(priority=list(struct.unpack_from('<14H', d, 0)), instrument=list(struct.unpack_from('<14H', d, 28)),
                fm=[dec_fm_record(d[56 + 16 * r:72 + 16 * r]) for r in range(SB_FM_N)],
                samples=[dec_sample_record(d[376 + 32 * s:408 + 32 * s]) for s in range(SB_SMP_N)],
                effects=[struct.unpack_from('<4H', d, 2072 + 8 * n) for n in range(56)],
                instruments=[struct.unpack_from('<3H', d, 2520 + 6 * i) for i in range(56)])


def enc_soundbank(m):
    out = struct.pack('<14H', *m['priority']) + struct.pack('<14H', *m['instrument'])
    out += b''.join(enc_fm_record(p, x) for p, x in m['fm'])
    out += b''.join(enc_sample_record(r) for r in m['samples'])
    out += b''.join(struct.pack('<4H', *e) for e in m['effects'])
    out += b''.join(struct.pack('<3H', *i) for i in m['instruments'])
    assert len(out) == SB_SIZE
    return out


def patch_problems(doc, where='sounds/fm_patches.json'):
    """Validates fm_patches.json (sounds.md section 5 / 6). Returns (the 16 patches, []) or (None, errors)."""
    isint = lambda v: isinstance(v, int) and not isinstance(v, bool)
    if not isinstance(doc, dict) or not isinstance(doc.get('patches'), list):
        return None, ['%s: {"patches": [16 objects]}' % where]
    errs, ps = [], doc['patches']
    if len(ps) != len(FM_PATCH_TABLE):
        errs.append('%s: %d patches, exactly %d in the order of the spec' % (where, len(ps), len(FM_PATCH_TABLE)))
    for k, (pid, ins) in enumerate(FM_PATCH_TABLE[:len(ps)]):
        p, w = ps[k], '%s "%s"' % (where, pid)
        if not isinstance(p, dict):
            errs.append('%s: not an object' % w)
            continue
        if p.get('id') != pid or p.get('instruments') != list(ins):
            errs.append('%s: patch %d must be id "%s", instruments %s (got %r, %r)' % (w, k, pid, list(ins), p.get('id'), p.get('instruments')))
        for key in p:
            if key not in ('id', 'instruments', 'effect_key', 'velocity_offset', 'feedback', 'connection', 'modulator', 'carrier', 'note'):
                errs.append('%s: unknown field "%s"' % (w, key))

        def num(obj, key, lo, hi, what):
            v = obj.get(key)
            if not isint(v) or not lo <= v <= hi:
                errs.append('%s: %s must be an integer %d..%d (got %r)' % (w, what, lo, hi, v))
                return False
            return True
        if 'effect_key' in p:
            num(p, 'effect_key', 0, 95, 'effect_key')
        elif pid in FM_EFFECT_KEY_REQUIRED:
            errs.append('%s: effect_key is required (an effect plays this patch)' % w)
        num(p, 'velocity_offset', -64, 0, 'velocity_offset')
        num(p, 'feedback', 0, 7, 'feedback')
        num(p, 'connection', 0, 1, 'connection')
        for op in ('modulator', 'carrier'):
            o = p.get(op)
            if not isinstance(o, dict):
                errs.append('%s: "%s" must be an object' % (w, op))
                continue
            for key in o:
                if key not in [f[0] for f in FM_OPERATOR]:
                    errs.append('%s %s: unknown field "%s"' % (w, op, key))
            for key, lo, hi in FM_OPERATOR:
                num(o, key, lo, hi, '%s.%s' % (op, key))
        c = p.get('carrier')
        if errs or not isinstance(c, dict):
            continue
        if c['sustain'] != 0:
            errs.append('%s: the carrier\'s sustain must be 0 (an effect has no note off: a held carrier never stops)' % w)
        if c['level'] > FM_CARRIER_LEVEL_MAX:
            errs.append('%s: the carrier\'s level is %d, at most %d' % (w, c['level'], FM_CARRIER_LEVEL_MAX))
        if c['attack'] == 0 or (c['decay'] == 0 and c['release'] == 0):
            errs.append('%s: silent (carrier attack 0, or decay and release both 0)' % w)
    return (None, errs) if errs else (ps, [])


def clean_soundbank(patches):
    """The model of the clean EXE/soundbank.bin from the 16 patches (sounds.md E2 "Building the clean bank"): the functional
    tables of embedded.json (effects, instrument devices), the patches' fields and effect keys, one sample record per
    required sound id."""
    emb = data('embedded')
    rec_of = {i: r for r, (pid, ins) in enumerate(FM_PATCH_TABLE) for i in ins}
    slot = {sid: k for k, sid in enumerate(sfx_required())}
    zero_fm = ({o: 0 for o in ('velocity_offset', 'feedback', 'connection')}, FM_EXTRA)
    zero_op = {f[0]: 0 for f in FM_OPERATOR}
    zero_fm = (dict(zero_fm[0], modulator=dict(zero_op), carrier=dict(zero_op)), dict(FM_EXTRA))
    fm = [({k: v for k, v in p.items() if k in ('velocity_offset', 'feedback', 'connection', 'modulator', 'carrier')}, dict(FM_EXTRA))
          for p in patches] + [zero_fm] * (SB_FM_N - len(patches))
    zero_smp = dict(head=bytes(6), loop=0, loop_flag=0, base_octave=0, transpose=0, w12=0, name=bytes(15), sound=0, b31=0)
    samples = [dict(zero_smp, base_octave=5, name=b'sfx%d' % sid + bytes(15 - len(b'sfx%d' % sid)), sound=sid) for sid in slot]
    samples += [zero_smp] * (SB_SMP_N - len(samples))
    instruments, key_of = [], {}
    for ins in emb['instruments']:
        i = ins['index']
        if ins['device'] == 'FM':
            instruments.append((2, SB_FM_AT + 16 * rec_of[i], SB_SEG))
            key_of[i] = patches[rec_of[i]].get('effect_key', FM_DEFAULT_KEY)
        elif ins['device'] == 'sample':
            instruments.append((1, SB_SMP_AT + 32 * slot[ins['sample_sound']], SB_SEG))
        else:
            instruments.append((0, 0, 0))
    effects = [(key_of.get(e['Instrument'], e['Key']), e['Priority'], e['Instrument'], e['Velocity']) for e in emb['effects']]
    return dict(priority=list(SB_CHANNEL_PRIORITY), instrument=list(SB_CHANNEL_INSTRUMENT), fm=fm, samples=samples,
                effects=effects, instruments=instruments)


def soundbank_problems(m, names=None, clean=None):
    """Invariants of a decoded bank (originals and the clean one): channel tables, FM byte 15, far pointer segments, record
    offsets inside their tables, sample records (base octave 5, no transposition, no loop) behind sample instruments, the
    effects against the functional table. `clean` (the patches) adds: every FM instrument has its patch with clean extras,
    sample instruments name sfx<id> records whose SOUND/5 id exists in `names`, effect keys are the patches'."""
    errs, emb = [], data('embedded')
    if m['priority'] != SB_CHANNEL_PRIORITY or m['instrument'] != SB_CHANNEL_INSTRUMENT:
        errs.append('the song channel table is not the functional one')
    if any(x['b15'] != 0 for _p, x in m['fm']):
        errs.append('an FM record has a non-zero byte 15')
    for ins in emb['instruments']:
        i = ins['index']
        dev, off, seg = m['instruments'][i]
        want = {'FM': 2, 'sample': 1, 'none': 0}[ins['device']]
        if dev != want or seg != (0 if want == 0 else SB_SEG) or (want == 0 and off != 0):
            errs.append('instrument %d: device %d, segment %04X, expected device %d' % (i, dev, seg, want))
        elif dev == 2:
            r = (off - SB_FM_AT) // 16
            if off < SB_FM_AT or (off - SB_FM_AT) % 16 or r >= (len(clean) if clean else SB_FM_N):
                errs.append('instrument %d: FM record offset %04X is outside the table' % (i, off))
            elif clean is not None:
                p, x = m['fm'][r]
                if x != FM_EXTRA:
                    errs.append('instrument %d: the clean record has extra (waveform, octave, unused) bytes set' % i)
                if i not in FM_PATCH_TABLE[r][1]:
                    errs.append('instrument %d plays patch %s' % (i, FM_PATCH_TABLE[r][0]))
        elif dev == 1:
            s = (off - SB_SMP_AT) // 32
            if off < SB_SMP_AT or (off - SB_SMP_AT) % 32 or s >= SB_SMP_N:
                errs.append('instrument %d: sample record offset %04X is outside the table' % (i, off))
                continue
            r = m['samples'][s]
            if (r['base_octave'], r['transpose'], r['loop_flag']) != (5, 0, 0):
                errs.append('instrument %d: sample record %d has octave %d, transposition %d, loop %d (expected 5, 0, 0)'
                            % (i, s, r['base_octave'], r['transpose'], r['loop_flag']))
            if r['sound'] != ins['sample_sound']:
                errs.append('instrument %d: its sample record says sound %d, the measurements say %d' % (i, r['sound'], ins['sample_sound']))
            if clean is not None:
                if r['name'].split(b'\0')[0] != b'sfx%d' % r['sound']:
                    errs.append('instrument %d: sample record name %r is not sfx%d' % (i, r['name'], r['sound']))
                if names is not None and 'SOUND/5/%d.bin' % r['sound'] not in names:
                    errs.append('instrument %d: sound %d is not in the pack' % (i, r['sound']))
    for e, want in zip(m['effects'], emb['effects']):
        got = (e[1], e[2], e[3])
        if got != (want['Priority'], want['Instrument'], want['Velocity']):
            errs.append('effect %d: priority, instrument, velocity %s are not the functional table\'s' % (want['effect'], got))
        elif clean is None and e[0] != want['Key']:
            errs.append('effect %d: key %d, the functional table says %d' % (want['effect'], e[0], want['Key']))
        elif clean is not None:
            ins = emb['instruments'][want['Instrument']]
            if ins['device'] == 'FM':
                r = (m['instruments'][ins['index']][1] - SB_FM_AT) // 16
                if e[0] != clean[r].get('effect_key', FM_DEFAULT_KEY):
                    errs.append('effect %d: key %d is not the patch\'s effect_key' % (want['effect'], e[0]))
            elif e[0] != want['Key']:
                errs.append('effect %d: key %d, the functional table says %d' % (want['effect'], e[0], want['Key']))
    return errs


def patches_of_bank(m):
    """The 16 patch objects (fm_patches.json's form) read out of an original's bank model: each patch's fields from the record
    of its first instrument, effect_key the effect's key. The original's octave shift, waveform bytes and unused bits are not
    part of a patch (a clean patch is 0 there), so the clean sound is not the original's pitch."""
    out = []
    for pid, ins in FM_PATCH_TABLE:
        _dev, off, _seg = m['instruments'][ins[0]]
        p = m['fm'][(off - SB_FM_AT) // 16][0]
        out.append(dict(id=pid, instruments=list(ins), effect_key=m['effects'][ins[0]][0], **json.loads(json.dumps(p)), note=''))
    return out


def cat_soundbank(errors):
    """src/sounds/fm_patches.json -> EXE/soundbank.bin (2,856 bytes) with the functional tables."""
    path = os.path.join(SRC, 'sounds', 'fm_patches.json')
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf-8') as f:
            doc = json.load(f)
    except ValueError as e:
        errors.append('sounds/fm_patches.json: %s' % e)
        return
    patches, errs = patch_problems(doc)
    errors.extend(errs)
    if patches is None:
        return
    blob = enc_soundbank(clean_soundbank(patches))
    bad = soundbank_problems(dec_soundbank(blob), clean=patches)
    if bad:
        errors.extend('sounds/fm_patches.json: the bank built from it fails its own checks: %s' % b for b in bad)
        return
    yield 'EXE/soundbank.bin', blob


def check_sounds_roundtrip(zip_path):
    """--roundtrip=<zip>: the 57 samples of the pack decoded and coded back (the same samples; the same bytes where the table
    entries are distinct), the lossy encoder run on the decoded originals (the SNR it reaches), the sound bank decoded and encoded
    back byte for byte with its invariants, and a clean bank built from the original's own fields. Returns (counts, notes,
    problems)."""
    c = dict(samples=0, same=0, exact=0, dup_tables=0, snr=[], seconds=0.0, bank=0, patches=0, fm_fields=0)
    notes, problems = [], []
    rows = {r['id']: r for r in data('sounds')}
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for ident in range(57):
            n = 'SOUND/5/%d.bin' % ident
            if n not in names:
                problems.append('%s: not in the pack' % n)
                continue
            d = z.read(n)
            t = dec_sample(d)
            c['samples'] += 1
            row = rows[ident]
            if len(t) != row['samples'] or max(abs(x) for x in t) != row['peak']:
                problems.append('%s: %d samples, peak %d; the measurements say %d, %d'
                                % (n, len(t), max(abs(x) for x in t), row['samples'], row['peak']))
            table = [b - 256 if b > 127 else b for b in d[:16]]
            back = enc_sample_lossless(t, table)
            if dec_sample(back) != t or len(back) != len(d):
                problems.append('%s: the samples do not survive the lossless coder' % n)
                continue
            c['same'] += 1
            if back == d:
                c['exact'] += 1
            elif len(set(table)) == 16:
                problems.append('%s: the table has 16 distinct entries but the bytes differ' % n)
            if len(set(table)) < 16:
                c['dup_tables'] += 1
            start = time.time()
            if any(t):
                blob, snr = enc_sample(t)
                got = dec_sample(blob)
                err = sum((x - y) ** 2 for x, y in zip(t, got))
                if len(got) != len(t) or abs((99.0 if err == 0 else 10 * math.log10(sum(x * x for x in t) / err)) - snr) > 1e-6:
                    problems.append('%s: the lossy coder result does not decode to the SNR it reports' % n)
                c['snr'].append((snr, ident))
            c['seconds'] += time.time() - start
        # the sound bank
        raw = z.read('EXE/soundbank.bin') if 'EXE/soundbank.bin' in names else None
        if raw is None:
            problems.append('EXE/soundbank.bin: not in the pack')
        else:
            m = dec_soundbank(raw)
            if enc_soundbank(m) != raw:
                problems.append('EXE/soundbank.bin: not byte-identical after decode + encode')
            else:
                c['bank'] = 1
            for p in soundbank_problems(m):
                problems.append('EXE/soundbank.bin: %s' % p)
            for pid, ins in FM_PATCH_TABLE:
                for i in ins[1:]:
                    if m['instruments'][i][1] != m['instruments'][ins[0]][1]:
                        problems.append('EXE/soundbank.bin: instruments %s do not share one record' % list(ins))
            for pa, x in m['fm']:                                   # the field <-> byte conversion is an exact inverse
                if dec_fm_record(enc_fm_record(pa, x)) != (pa, x):
                    problems.append('EXE/soundbank.bin: an FM record\'s fields do not survive the conversion')
            for op in FM_OPERATOR:                                  # and every value of every field
                for v in range(op[1], op[2] + 1):
                    o = {f[0]: 0 for f in FM_OPERATOR}
                    o[op[0]] = v
                    if fm_op_fields(*fm_op_bytes(o)) != o:
                        problems.append('FM field %s=%d does not survive the conversion' % (op[0], v))
            # a clean bank from the original's fields
            patches = patches_of_bank(m)
            ps, errs = patch_problems({'patches': patches}, 'patches read from the original')
            if errs:
                notes.append('read out of the original\'s bank, %d of its 16 patches break a clean-file rule (for example a held carrier, '
                             'carrier level above %d, octave shift): %s' % (len({e.split('"')[1] for e in errs if '"' in e}),
                                                                             FM_CARRIER_LEVEL_MAX, errs[0]))
            cm = clean_soundbank(patches)
            blob = enc_soundbank(cm)
            back = dec_soundbank(blob)
            if len(blob) != SB_SIZE or enc_soundbank(back) != blob:
                problems.append('the clean bank is not %d bytes / not a fixed point of decode + encode' % SB_SIZE)
            for p in soundbank_problems(back, names, patches):
                problems.append('clean bank: %s' % p)
            for ins in data('embedded')['instruments']:
                if ins['device'] != 'FM':
                    continue
                i = ins['index']
                a = m['fm'][(m['instruments'][i][1] - SB_FM_AT) // 16][0]
                b = back['fm'][(back['instruments'][i][1] - SB_FM_AT) // 16][0]
                if a == b:
                    c['fm_fields'] += 1
                else:
                    problems.append('clean bank: instrument %d has other FM fields than the original' % i)
            c['patches'] = len(patches)
    if c['snr']:
        snrs = sorted(s for s, _i in c['snr'])
        notes.append('the lossy encoder on the %d decoded originals (their own delta codes): SNR min %.1f dB (id %d), median %.1f, max %.1f; '
                     '%.1f s in all' % (len(snrs), snrs[0], min(c['snr'])[1], snrs[len(snrs) // 2], snrs[-1], c['seconds']))
    return c, notes, problems


# ------------------------------------------------------------------------------------------------ music
# docs/clean_pack/music.md: SOUND/20/<song>.bin (the Standard MIDI file unchanged after the checks) and SOUND/18/<cue>.bin
STEP_HZ = 1193182 / 0xD6 / 16               # the driver's music clock: steps per second (348.47)
MUSIC_PPQ = 240
MIDI_MAX_BYTES = 64 * 1024
MIDI_TEMPO = (100000, 1000000)
MIDI_MAX_HELD = 6
MIDI_CHANNEL_HELD = {2: 3, 4: 2}                                  # notes at once per channel (1 elsewhere)
MIDI_LENGTH_TOL = 0.10
MIDI_START_MAX = MIDI_END_MAX = 0.3        # seconds: the first note on, the last end-of-track after the last note off
MIDI_NOTE_MIN, MIDI_NOTE_MIN_DRUM, MIDI_NOTE_MAX = 0.04, 0.08, 12.0
MIDI_DRUM_CHANNELS = (5, 6, 7, 9)
MIDI_KEYS = {1: (48, 88), 2: (40, 80), 3: (24, 52), 4: (48, 88), 5: (20, 55), 6: (40, 80), 7: (60, 95), 8: (36, 84), 9: (50, 95),
             10: (60, 95)}
MIDI_KEY_SLACK = 6
MIDI_AMBIENT = (10003, 10004, 10005)


class MidiError(Exception):
    pass


def midi_scale(ppq, tempo):
    """Music steps per MIDI tick in 8.8 fixed point (SoundDriver.Scale)."""
    return tempo // 1000 * 0x4AA // ppq // 13 if ppq else 0


def midi_walk(d):
    """A port of the game's sequencer (SoundDriver.StartSong / Step / Meta / NextEvent / ChannelEvent): the events in the order the
    game runs them, with the music clock. Returns dict(events=[(step, track, status, a, b)] for the note on / off events of the
    channels 0..13, eots=[step of each end-of-track], steps=the song's length in steps, ticks=the last event's tick, tracks, ppq).
    Raises MidiError for what the game's reader would choke on."""
    try:
        return _midi_walk(d)
    except (IndexError, struct.error):
        raise MidiError('the file ends where the game\'s sequencer still reads')


def _midi_walk(d):
    be16 = lambda i: d[i] << 8 | d[i + 1]
    be32 = lambda i: d[i] << 24 | d[i + 1] << 16 | d[i + 2] << 8 | d[i + 3]
    hdr, tracks, ppq = be32(4), be16(10), be16(12)
    ptr, at = [], hdr + 8
    for _t in range(tracks):
        ptr.append(at + 8)
        at += 8 + be32(at + 4)

    def varlen(t):
        p = ptr[t]
        b = d[p]
        p += 1
        v = b
        if b & 0x80:
            v &= 0x7f
            while True:
                b = d[p]
                p += 1
                v = (v << 7) + (b & 0x7f)
                if not b & 0x80:
                    break
        ptr[t] = p
        return v
    time_, status = [0] * tracks, [0] * tracks
    for t in range(tracks):
        time_[t] = varlen(t)
        status[t] = d[ptr[t]]
    last, cur, scale, now, events, eots = 0, 0, midi_scale(480, 500000), 0, [], []
    for _ in range(8 * len(d) + 64):
        b = d[ptr[cur]]
        if b & 0x80:
            status[cur] = b
            ptr[cur] += 1
        st = status[cur]
        if st in (0xf0, 0xf7):
            n = varlen(cur)
            ptr[cur] += n
        elif st == 0xff:
            typ = d[ptr[cur]]
            if typ == 0x2f:
                status[cur] = 0x2f
                ptr[cur] -= 1
                eots.append(now)
            elif typ == 0x51:
                ptr[cur] += 2
                p = ptr[cur]
                scale = midi_scale(ppq, d[p] << 16 | d[p + 1] << 8 | d[p + 2])
                ptr[cur] += 3
            else:
                ptr[cur] += 1
                n = varlen(cur)
                ptr[cur] += n
        else:
            if st < 0x80 or st >= 0xf0:
                raise MidiError('track %d: status byte %02X' % (cur, st))
            if (st >> 4) <= 9 and (st & 15) < 14 and (st >> 4) in (8, 9):
                events.append((now, cur, st, d[ptr[cur]], d[ptr[cur] + 1]))
            ptr[cur] += (2, 2, 2, 2, 1, 1, 2)[(st & 0x70) >> 4]
        if status[cur] != 0x2f:
            time_[cur] += varlen(cur)
        else:
            time_[cur] = 0x7fffffff
        di = 0
        for t in range(1, tracks):
            if time_[di] > time_[t] and status[t] != 0x2f:
                di = t
        if status[di] == 0x2f or time_[di] == 0x7fffffff:
            return dict(events=events, eots=eots, steps=now, ticks=last, tracks=tracks, ppq=ppq)
        diff = time_[di] - last
        last = time_[di]
        cur = di
        now += (diff * scale >> 8) & 0xffff
    raise MidiError('the sequencer would not stop')


def _midi_track(t, body, bad):
    """One track chunk read strictly: a list of ('note', tick, status, key, velocity) and ('meta', tick, type, data)."""
    ev, i, tick, running, ended, n, seen = [], 0, 0, None, False, len(body), set()
    while i < n:
        v = 0
        for _k in range(4):
            if i >= n:
                bad('structure', 'track %d: ends inside a delta time' % t)
                return ev
            b = body[i]
            i += 1
            v = v << 7 | b & 0x7f
            if not b & 0x80:
                break
        else:
            bad('structure', 'track %d: a variable-length number longer than 4 bytes' % t)
            return ev
        if ended:
            bad('structure', 'track %d: events after the end-of-track' % t)
            return ev
        tick += v
        if i >= n:
            bad('structure', 'track %d: ends inside an event' % t)
            return ev
        b = body[i]
        if b == 0xff:
            if i + 2 > n:
                bad('structure', 'track %d: ends inside a meta event' % t)
                return ev
            typ, i, ln = body[i + 1], i + 2, 0
            for _k in range(4):
                if i >= n:
                    bad('structure', 'track %d: ends inside a meta event' % t)
                    return ev
                x = body[i]
                i += 1
                ln = ln << 7 | x & 0x7f
                if not x & 0x80:
                    break
            if i + ln > n:
                bad('structure', 'track %d: a meta event runs past the end of the track' % t)
                return ev
            ev.append(('meta', tick, typ, bytes(body[i:i + ln])))
            i += ln
            running = None
            ended = typ == 0x2f
        elif b >= 0xf0:
            bad('event', 'track %d: system exclusive / system messages are not allowed' % t)
            return ev
        else:
            if b & 0x80:
                running = b
                i += 1
            elif running is None:
                bad('structure', 'track %d: a data byte with no status' % t)
                return ev
            kind = running >> 4
            ln = 1 if kind in (0xc, 0xd) else 2
            if i + ln > n:
                bad('structure', 'track %d: ends inside an event' % t)
                return ev
            data_ = body[i:i + ln]
            i += ln
            if any(x > 127 for x in data_):
                bad('structure', 'track %d: a data byte above 127' % t)
                return ev
            if kind in (8, 9):
                ev.append(('note', tick, running, data_[0], data_[1]))
            elif kind not in seen:
                seen.add(kind)
                bad('event', 'track %d: %s events are not allowed (note on / off only)'
                    % (t, {0xa: 'aftertouch', 0xb: 'controller', 0xc: 'program change', 0xd: 'aftertouch', 0xe: 'pitch bend'}[kind]))
    if not ended:
        bad('structure', 'track %d: no end-of-track' % t)
    return ev


def midi_check(d, song=None):
    """The checks of music.md section 3 on a song file. Returns (errors, warnings, info); the first two are lists of (kind, text),
    info the measurements (steps, seconds, notes, lowest, highest, channels, max held, ticks) when the file could be walked."""
    errs, warns, info = [], [], {}
    bad = lambda kind, text: errs.append((kind, text))
    if len(d) > MIDI_MAX_BYTES:
        bad('size', '%d bytes, at most %d' % (len(d), MIDI_MAX_BYTES))
    if len(d) < 14 or d[:4] != b'MThd' or struct.unpack_from('>I', d, 4)[0] != 6:
        bad('header', 'not a Standard MIDI file (MThd, header length 6)')
        return errs, warns, info
    fmt, ntr, div = struct.unpack_from('>HHH', d, 8)
    if fmt != 1:
        bad('header', 'format %d, must be 1' % fmt)
    if not 2 <= ntr <= 11:
        bad('header', '%d tracks, 2..11' % ntr)
    if div != MUSIC_PPQ:
        bad('header', 'division %d, must be %d ticks per quarter' % (div, MUSIC_PPQ))
    p, tracks = 14, []
    for t in range(ntr):
        if p + 8 > len(d) or d[p:p + 4] != b'MTrk':
            bad('structure', 'track %d: no MTrk chunk where the file should hold it' % t)
            return errs, warns, info
        n = struct.unpack_from('>I', d, p + 4)[0]
        if p + 8 + n > len(d):
            bad('structure', 'track %d: its chunk runs past the end of the file' % t)
            return errs, warns, info
        tracks.append(_midi_track(t, d[p + 8:p + 8 + n], bad))
        p += 8 + n
    if p != len(d):
        bad('structure', '%d bytes after the last track' % (len(d) - p))
    if errs:
        return errs, warns, info
    # track layout
    chan_of, tempo_at0 = {}, False
    for t, ev in enumerate(tracks):
        notes = [e for e in ev if e[0] == 'note']
        if t == 0:
            if notes:
                bad('track', 'track 0 (the conductor) holds notes')
            if not ev or ev[0][1] != 0:
                bad('track', 'track 0: the first event must be at delta 0')
            for e in ev:
                if e[0] != 'meta':
                    continue
                typ, data_ = e[2], e[3]
                if typ == 0x51:
                    if len(data_) != 3 or not MIDI_TEMPO[0] <= int.from_bytes(data_, 'big') <= MIDI_TEMPO[1]:
                        bad('tempo', 'tempo %s microseconds per quarter, %d..%d' % (int.from_bytes(data_, 'big'), *MIDI_TEMPO))
                    tempo_at0 = tempo_at0 or e[1] == 0
                elif typ not in (0x2f, 0x58, 0x59) and not 1 <= typ <= 15:
                    bad('meta', 'track 0: meta event FF %02X is not allowed (tempo, time / key signature, text)' % typ)
            continue
        for e in ev:
            if e[0] == 'meta' and e[2] not in (0x2f,) and not 1 <= e[2] <= 15:
                bad('meta', 'track %d: meta event FF %02X is not allowed (a name or text, and the end-of-track)' % (t, e[2]))
        chans = {e[2] & 15 for e in notes}
        if len(chans) > 1:
            bad('track', 'track %d uses several MIDI channels %s' % (t, sorted(chans)))
        for ch in chans:
            if not 1 <= ch <= 10:
                bad('channel', 'track %d: MIDI channel %d, must be 1..10' % (t, ch))
            if ch in chan_of:
                bad('track', 'tracks %d and %d both use channel %d' % (chan_of[ch], t, ch))
            chan_of[ch] = t
        for e in notes:
            if e[3] > 95:
                bad('key', 'track %d tick %d: key %d, at most 95' % (t, e[1], e[3]))
                break
        for e in notes:
            if e[2] >> 4 == 9 and e[4] == 1:
                bad('velocity', 'track %d tick %d: velocity 1 is read as a note off by the driver (2..127)' % (t, e[1]))
                break
        for ch in chans:
            if 1 <= ch <= 10:
                lo, hi = MIDI_KEYS[ch]
                keys = [e[3] for e in notes if e[2] & 15 == ch]
                far = [k for k in keys if k < lo - MIDI_KEY_SLACK or k > hi + MIDI_KEY_SLACK]
                near = [k for k in keys if (k < lo or k > hi) and k not in far]
                if far:
                    bad('range', 'channel %d: key %d is more than %d semitones outside its range %d..%d' % (ch, far[0], MIDI_KEY_SLACK, lo, hi))
                elif near:
                    warns.append(('range', 'channel %d: key %d is outside its range %d..%d' % (ch, near[0], lo, hi)))
    if not tempo_at0:
        bad('tempo', 'track 0 needs a tempo event at tick 0 (the game assumes 480 ticks per quarter until it reads one)')
    if errs:
        return errs, warns, info
    try:
        w = midi_walk(d)
    except MidiError as e:
        bad('walk', str(e))
        return errs, warns, info
    on = [e for e in w['events'] if e[2] >> 4 == 9 and e[4] > 0]
    info.update(steps=w['steps'], seconds=w['steps'] / STEP_HZ, ticks=w['ticks'], notes=len(on),
                lowest=min((e[3] for e in on), default=None), highest=max((e[3] for e in on), default=None),
                channels=sorted({e[2] & 15 for e in w['events']}))
    if not on:
        bad('notes', 'no notes')
        return errs, warns, info
    # held notes, lengths, polyphony
    held, played, by_step, max_total, max_ch = {}, [], {}, 0, {}
    for step, trk, st, key, vel in w['events']:
        ch = st & 15
        if st >> 4 == 9 and vel > 0:
            if (ch, key) in held:
                bad('overlap', 'channel %d: key %d is struck again while held (step %d)' % (ch, key, step))
            else:
                held[(ch, key)] = step
        elif (ch, key) not in held:
            bad('overlap', 'channel %d: note off for key %d which is not held (step %d)' % (ch, key, step))
        else:
            played.append((held.pop((ch, key)), step, ch, key))
        by_step[step] = (len(held), [c for c, _k in held])
    if held:
        bad('overlap', '%d notes are never switched off' % len(held))
    for total, chs in by_step.values():
        max_total = max(max_total, total)
        for ch in set(chs):
            max_ch[ch] = max(max_ch.get(ch, 0), chs.count(ch))
    info['max_held'] = max_total
    if max_total > MIDI_MAX_HELD:
        bad('polyphony', '%d notes held at once, at most %d' % (max_total, MIDI_MAX_HELD))
    for ch, n in sorted(max_ch.items()):
        if n > MIDI_CHANNEL_HELD.get(ch, 1):
            bad('polyphony', 'channel %d holds %d notes at once, at most %d' % (ch, n, MIDI_CHANNEL_HELD.get(ch, 1)))
    for a, b, ch, key in played:
        sec = (b - a) / STEP_HZ
        if sec < (MIDI_NOTE_MIN_DRUM if ch in MIDI_DRUM_CHANNELS else MIDI_NOTE_MIN) - 1e-9:
            bad('length', 'channel %d key %d at step %d lasts %.0f ms, at least %d' %
                (ch, key, a, sec * 1000, 1000 * (MIDI_NOTE_MIN_DRUM if ch in MIDI_DRUM_CHANNELS else MIDI_NOTE_MIN)))
            break
    if any((b - a) / STEP_HZ > MIDI_NOTE_MAX for a, b, _c, _k in played):
        bad('length', 'a note lasts longer than %g s' % MIDI_NOTE_MAX)
    first = min(e[0] for e in on) / STEP_HZ
    if first > MIDI_START_MAX:
        bad('timing', 'the first note starts at %.2f s, at most %.1f' % (first, MIDI_START_MAX))
    tail = w['steps'] / STEP_HZ - max((b for _a, b, _c, _k in played), default=0) / STEP_HZ
    if tail > MIDI_END_MAX:
        bad('timing', 'the last end-of-track comes %.2f s after the last note off, at most %.1f' % (tail, MIDI_END_MAX))
    if song is not None:
        row = next((s for s in data('songs') if s['id'] == song), None)
        if row is None:
            bad('song', 'no such song')
        else:
            if abs(info['seconds'] - row['seconds']) > MIDI_LENGTH_TOL * row['seconds']:
                bad('length', 'plays for %.1f s through the game\'s clock, the spec says %g s (within %d %%)'
                    % (info['seconds'], row['seconds'], MIDI_LENGTH_TOL * 100))
            ratio = info['notes'] / row['notes']
            if not 0.25 <= ratio <= 4:
                bad('notes', '%d notes, the spec says about %d (25..400 %%)' % (info['notes'], row['notes']))
            elif not 0.5 <= ratio <= 2:
                warns.append(('notes', '%d notes, the spec says about %d (50..200 %%)' % (info['notes'], row['notes'])))
            if song in MIDI_AMBIENT and any(not 5 <= ch <= 10 for ch in info['channels']):
                bad('channel', 'an ambient theme uses only channels 5..10')
            up = max((c['transpose'] for c in data('song_cues') if c['song'] == song), default=0)
            if info['highest'] + up > 95:
                bad('key', 'highest key %d, a cue plays it %d semitones up: at most %d' % (info['highest'], up, 95 - up))
    return errs, warns, info


def cat_music(errors):
    """src/music/<song id>.mid -> SOUND/20/<id>.bin (unchanged bytes) after the checks of music.md."""
    ids = {s['id'] for s in data('songs')}
    d = os.path.join(SRC, 'music')
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith('.mid'):
            continue
        where = 'music/' + name
        if not name[:-4].isdigit() or int(name[:-4]) not in ids:
            errors.append('%s: no such song (the ids are %s ...)' % (where, ', '.join(str(i) for i in sorted(ids)[:4])))
            continue
        ident = int(name[:-4])
        with open(os.path.join(d, name), 'rb') as f:
            raw = f.read()
        errs, warns, _info = midi_check(raw, ident)
        errors.extend('%s: %s' % (where, t) for _k, t in errs)
        WARNINGS.extend('%s: %s' % (where, t) for _k, t in warns)
        if not errs:
            yield 'SOUND/20/%d.bin' % ident, raw


def enc_cue(song, kind, transposition, a, b, c, d):
    """SOUND type 18 (18 bytes, big-endian): the song, a kind, 0, the transposition in semitones, and the old driver's numbers."""
    return struct.pack('>HHHhHHBB4x', song, kind, 0, transposition, a, b, c, d)


def dec_cue(blob):
    song, kind, zero, tr, a, b, c, d = struct.unpack('>HHHhHHBB4x', blob)
    return dict(song=song, kind=kind, zero=zero, transposition=tr, a=a, b=b, c=c, d=d)


def cat_cues(errors):
    """data/song_cues.json -> SOUND/18/<cue>.bin (functional data, always built): the cue's 18 bytes, checked against its song and
    transposition."""
    songs = {s['id'] for s in data('songs')}
    for cue in data('song_cues'):
        blob = bytes.fromhex(cue['bytes_hex'])
        try:
            f = dec_cue(blob)
        except struct.error:
            errors.append('song_cues.json cue %d: not 18 bytes' % cue['cue'])
            continue
        if f['song'] != cue['song'] or f['transposition'] != cue['transpose'] or f['song'] not in songs or f['zero'] != 0:
            errors.append('song_cues.json cue %d: its bytes do not say song %d, transposition %d' % (cue['cue'], cue['song'], cue['transpose']))
            continue
        yield 'SOUND/18/%d.bin' % cue['cue'], blob


def check_music_roundtrip(zip_path):
    """--roundtrip=<zip>: the 30 songs of the pack through the sequencer port (ticks, notes, keys and channels as measured; the
    Game Theme 35,856 steps), the clean-file rules on them (which originals would not pass is listed, not an error), and the 33 cue
    entries decoded and encoded back. Returns (counts, notes, problems)."""
    c = dict(songs=0, measured=0, would_pass=0, cues=0, steps=0)
    notes, problems, broken = [], [], {}
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for s in data('songs'):
            n = 'SOUND/20/%d.bin' % s['id']
            if n not in names:
                problems.append('%s: not in the pack' % n)
                continue
            raw = z.read(n)
            c['songs'] += 1
            try:
                w = midi_walk(raw)
            except MidiError as e:
                problems.append('%s: %s' % (n, e))
                continue
            on = [e for e in w['events'] if e[2] >> 4 == 9 and e[4] > 0]
            got = dict(ticks=w['ticks'], notes=len(on), lowest=min(e[3] for e in on), highest=max(e[3] for e in on),
                       channels=sorted({e[2] & 15 for e in on}))
            want = {k: s[k] for k in got}
            if got != want or w['ppq'] != s['ppq'] or w['tracks'] != s['tracks']:
                problems.append('%s: the port finds %s (%d tracks, ppq %d), the measurements say %s' % (n, got, w['tracks'], w['ppq'], want))
            else:
                c['measured'] += 1
            if abs(w['steps'] / STEP_HZ - s['seconds']) > 0.02 * s['seconds'] + 0.1:
                problems.append('%s: %.1f s through the game\'s clock, the measurements say %g s' % (n, w['steps'] / STEP_HZ, s['seconds']))
            if s['id'] == 10001:
                c['steps'] = max(e[0] for e in w['events'])
                if c['steps'] != 35856:
                    problems.append('%s: the last note event comes at step %d, the game plays the main theme for 35,856' % (n, c['steps']))
            errs, _w, _i = midi_check(raw, s['id'])
            if errs:
                for k in {k for k, _t in errs}:
                    broken[k] = broken.get(k, 0) + 1
            else:
                c['would_pass'] += 1
        for cue in data('song_cues'):
            n = 'SOUND/18/%d.bin' % cue['cue']
            if n not in names:
                problems.append('%s: not in the pack' % n)
                continue
            raw = z.read(n)
            f = dec_cue(raw)
            if enc_cue(f['song'], f['kind'], f['transposition'], f['a'], f['b'], f['c'], f['d']) == raw == bytes.fromhex(cue['bytes_hex']) \
                    and (f['song'], f['transposition']) == (cue['song'], cue['transpose']) and f['kind'] == (4 if cue['cue'] < 11000 else 1):
                c['cues'] += 1
            else:
                problems.append('%s: not byte-identical after decode + encode / not the cue table\'s' % n)
    if broken:
        notes.append('the clean-file rules (music.md section 3) applied to the originals: %d of %d would fail, by rule: %s'
                     % (c['songs'] - c['would_pass'], c['songs'], ', '.join('%s %d' % kv for kv in sorted(broken.items()))))
    return c, notes, problems


CATEGORIES = [cat_palette, cat_bitmaps, cat_cursors, cat_tiles, cat_sprites, cat_fonts, cat_balloon, cat_spiderlegs,
              cat_version, cat_strings, cat_engine_strings, cat_menus, cat_texts, cat_layouts, cat_sounds, cat_soundbank, cat_music, cat_cues]


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
        if s['id'] not in STR_UNUSED:                      # the 6 Macintosh leftovers no code loads are not needed
            names.add('%s/4/%d.bin' % (s['archive'], s['id']))
    for t in data('texts'):
        names.add('SHARED/10/%d.bin' % t['id'])
    for c in data('cards'):
        names.update(['SHARED/17/%d.bin' % c['id'], 'SHARED/19/%d.bin' % c['id']])
    for l in data('layouts'):
        names.add('HCEGANT/0/%d.bin' % l['id'])
    # the 35 samples a sample instrument reaches; the other 22 ids of the original's archive are never read (optional here)
    for ident in sfx_required():
        names.add('SOUND/5/%d.bin' % ident)
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
    names.update(['SHARED/6/0.bin', 'EXE/version.txt', 'EXE/engine_strings.json', 'SHARED/11/0.bin', 'SHARED/11/1.bin']
                 + ['FONT/%d.bin' % n for n in range(1, 5)])
    return names


def main():
    opts = dict(a[2:].split('=', 1) if '=' in a else (a[2:], '1') for a in sys.argv[1:] if a.startswith('--'))
    if 'roundtrip' in opts:                                   # check the encoder against the originals, build nothing
        checked, problems = check_bitmap_roundtrip(opts['roundtrip'])
        n_lists, n_menus, text_problems = check_text_roundtrip(opts['roundtrip'])
        counts, notes, prose_problems = check_texts_roundtrip(opts['roundtrip'])
        lcounts, lnotes, layout_problems = check_layouts_roundtrip(opts['roundtrip'])
        prose_problems = prose_problems + layout_problems
        notes = notes + lnotes
        scounts, snotes, sound_problems = check_sounds_roundtrip(opts['roundtrip'])
        mcounts, mnotes, music_problems = check_music_roundtrip(opts['roundtrip'])
        notes = notes + snotes + mnotes
        sound_problems = sound_problems + music_problems
        for p in problems + text_problems + prose_problems + sound_problems:
            print('error:', p)
        for n in notes:
            print('note:', n)
        print('%d bitmaps checked through enc_bitmap, %d problems' % (checked, len(problems)))
        print('%d string lists and %d menu lists (SHARED/6/0) decoded and encoded back byte-identically, %d problems'
              % (n_lists, n_menus, len(text_problems)))
        print('%d texts (SHARED/10 + 21): the game sees the same text and bold words after text -> markup -> text for %d, '
              'the same bytes for %d, the same lines and links on the card for %d of %d card texts; %d card layouts (17), %d '
              'captions (19) and %d glossary entries (EXE/glossary.bin) byte-identical; %d problems'
              % (counts['texts'], counts['view'], counts['exact'], counts['same_layout'], counts['layout'], counts['layouts'],
                 counts['names'], counts['glossary'], len(prose_problems) - len(layout_problems)))
        print('%d window layouts (HCEGANT/0, ids 0..33) decoded and encoded back: the same as window_layouts.json for %d, '
              'byte-identical with the original\'s dead bytes (item table segments, padding after strings) for %d, with zeros there '
              'for %d (the other %d differ only in dead bytes); %d of the %d UI tables (128 / 129 / 131) byte-identical; %d problems'
              % (lcounts['windows'], lcounts['same_json'], lcounts['exact'], lcounts['zero'], lcounts['dead_only'], lcounts['tables'],
                 len(LAYOUT_TABLES), len(layout_problems)))
        print('%d sound samples (SOUND/5) decoded and coded back with their own tables: the same samples for %d, the same bytes for %d '
              '(%d of the 57 tables repeat an entry, where the lowest code is only a convention); the lossy encoder reaches the SNRs in the note above; '
              'the sound bank (EXE/soundbank.bin, %d bytes) byte-identical: %s; a clean bank built from the original\'s %d patches keeps '
              'the fields of all %d FM instruments; %d problems'
              % (scounts['samples'], scounts['same'], scounts['exact'], scounts['dup_tables'], SB_SIZE, 'yes' if scounts['bank'] else 'NO',
                 scounts['patches'], scounts['fm_fields'], len(sound_problems) - len(music_problems)))
        print('%d songs (SOUND/20) through the port of the game\'s sequencer: ticks, notes, keys and channels as measured for %d (the '
              'Game Theme\'s last note comes at step %d); %d of the 33 cue entries (SOUND/18) byte-identical; %d problems'
              % (mcounts['songs'], mcounts['measured'], mcounts['steps'], mcounts['cues'], len(music_problems)))
        sys.exit(1 if problems or text_problems or prose_problems or sound_problems else 0)
    errors, made = [], {}
    for cat in CATEGORIES:
        for name, blob in cat(errors):
            made[name] = blob
    for w in WARNINGS:
        print('warning:', w)
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
