# SimAnt (DOS, Maxis 1991) — File Format Notes

This was reverse-engineered from the files in this folder. The extraction tools are in [`tools/`](../tools):

```
python -I tools/extract.py            # writes everything to extracted/
python -I tools/contact_sheet.py HCEGANT extracted/hcegant_sheet.png
```

They are pure Python 3 with no dependencies.

**Key finding:** the DOS version is a port of the Macintosh version. The archives are a flattened Mac
resource fork. Strings are Pascal `STR#` lists, the text is Mac Roman with CR line endings, the fonts are
Mac `FONT`/`NFNT` resources, the 16-color palette is the Mac system palette, and the data is mostly
big-endian. The code calls things like `GetResource` and `PictStrnDialog`.

## Files

| File | What it is |
|---|---|
| `SIMANT.EXE` | Game. Microsoft C 6.0 runtime, built Fri Dec 06 1991. 216 KB MZ image plus ~290 KB of appended code/data loaded by the program itself (overlays). Has many debug `printf` strings (see `extracted/simant_exe_strings.txt`). |
| `SHARED.NDX/.DAT` | Platform-independent resources: string tables, help/encyclopedia text, fonts, encyclopedia card layouts, 1-bit bitmaps |
| `HCEGANT.NDX/.DAT` | "Hercules/CGA/EGA" graphics: 16-color bitmaps, palette, window layouts, cursors |
| `SOUND.NDX/.DAT` | 57 sound effects (4-bit delta PCM) and 30 MIDI songs, plus per-song metadata |
| `FONT1`–`FONT4` | Raw Mac `FONT` resources (big-endian): the game's font ids 2..5 (FONT1 / FONT2 match SHARED 2 / 3; FONT3 15 rows, FONT4 bold) |
| `SIMANT.CFG` | Plain text: `Display Mode: V` / `Sound Mode: 6` |
| `RALLOC.DMP` | A real crash log from 30 Mar 1993, written by the game's `Ralloc` memory manager ("Window 2340 locked when it should not be!") |
| `INSTALL.EXE`, `INFO.EXE`, `READ.ME` | Installer, README viewer, release notes |

## Archive container (`.NDX` + `.DAT`)

NDX (little-endian):

```
0x00  u16  record count
0x02  18 bytes of zeros
0x14  count x { u32 offset; u16 id; u8 type; u8 flags }
...   256 bytes of uninitialised slack (ignore)
```

DAT:

```
0x00  u32  magic 0x12345678
0x04  u16  record count
0x06  u32  end-of-data offset
0x0A  4 bytes of zeros
0x0E  records: { u32 magic 0x12345678; u16 0; u32 size; u8 payload[size] }
```

NDX offsets are relative to `0x0E`. Resources are addressed by `(type, id)`, like a Mac resource fork.

**Compression:** when `flags & 1` is set, the payload is `u16 LE uncompressed_size` followed by a classic
Okumura LZSS stream (N=4096, F=18, threshold 2, ring pre-filled with spaces, starting at N−F, flag
bits LSB-first, 1 = literal). The other flag bits (0x04, 0x08) are probably loading hints and are not
needed for decoding.

## Resource types

### SHARED
| type | count | content |
|---|---|---|
| 2 | 40 | 1-bit bitmaps (bitmap header below, `planes=1`, 1 = black). Encyclopedia pictures and small icons. |
| 4 | 113 | `STR#` string lists: u16 **BE** count, then Pascal strings. Speech-balloon strings use a literal `\n` (backslash-n) for line breaks. |
| 10 | 94 | Plain text (Mac Roman, CR line endings, NUL-terminated). Help and SimAntipedia text. |
| 11 | 4 | Fonts (`tools/fonts.py`): 0 / 1 the game's own PC-style format (LE; 0 bold, 15 rows; 1 8 x 10), 2 / 3 Apple `FONT` (BE; 2 Geneva-like, 3 Times-like, 10 rows). Layout: see `fonts.py` |
| 17 | 53 | SimAntipedia cards 127..179 (BE): u16 height, u16 width (200 x 320), then records `PICT` (u16 bitmap id, Rect t/l/b/r, u16 n, n x (Rect, s16 link)) and `TEXT` (Rect, u16 n, n x u16 text id). Link 1 = PREVIOUS, > 1 a card, <= 0 a pop-up of text -link. SIM_NOTES "The SimAntipedia". |
| 19 | 53 | Card names (`Top_Card`, `Ant_Anatomy`, `Castes`, `Scent_Trails`, …) |
| 21 | 88 | Text style runs for the type 10 texts: Mac `styl` (u16 count, 20-byte ScrpSTElements: u32 start, height, ascent, font, face, size, colour). Face 0x0100 (bold) = a link word. |
| 6 | 1 | **The pull-down menus** (id 0, loaded by 82e5:0039 into DS:6054): LE u32 offsets from the resource start. A table up to a 0 entry: entry 0 lists the menu titles, entry m + 1 menu m's items; each list ends with a 0 entry, each string is NUL-terminated. Titles " File", " Window", " View", " Options", " Speed". An item's first byte is its state (0x20 plain, 0x10 checked, drawn by font 1 as a ►; 0x80 disabled); "---" is a separator. SIM_NOTES "Keys and menu commands"; remake `Formica.Data/Menus.cs`. |
| 7, 9 | 1–2 each | Cursor, misc tables (not yet decoded) |

### HCEGANT
| type | count | content |
|---|---|---|
| 2 | 212 | 16-color bitmaps |
| 15 | 2 | Palette. id 0 is u16 count (16) followed by 16 RGB triplets: the Mac 4-bit system palette (**index 0 = white, 15 = black**). |
| 0 | 37 | Window/dialog layouts: 0..33 are windows, 128 / 129 / 131 UI tables (see "Window layouts") |
| 9 | 11 | id 0: rectangle table (320 bytes). **ids 9 / 10: the house / yard tile sheets; 13..20: ant sprite sheets** (see "Map tiles and ant sprites") |
| 4 | 6 | Tutorial `STR#` strings |
| 7, 8 | 3 | Cursors |

### SOUND
| type | count | content |
|---|---|---|
| 20 | 30 | **Standard MIDI files** (SMF format 1, up to 10 tracks, 240 PPQ). Written out as-is to `.mid`. No program changes: each track's name is its instrument ("Kick", "Snare", "Tom", "Whap", "Stick", "Agogo" on channels 5..10; "Bassline", "Lead", "Strings", "Choir", "Mandolin", "Nylon Gu", ... on 0..4), for a driver with fixed patches. |
| 18 | 33 | One per song effect id (10001.., 11002.., 20000..), 18 bytes, BE: u16 the type-20 song, u16 4 (the 10000s) or 1, u16 0, s16 a transposition in semitones (11014 / 11015 = song 11013 at +6 / +12, 11017 = 11016 at +12), then u16 / u16 (6 / 4, 5 / 5, 8 / 3, 4 / 2: voice counts?), u8 0x40..0x44, u8 0x08..0x10, 4 x 0. f_00ea1(id) → f_284b3 plays it. |
| 5 | 57 | Sound effects. The first 16 bytes are a signed delta table, followed by 4-bit codes (high nibble first). Start at 0, add `table[code]`, clamp to ±127. The sample rate is not stored: the driver mixes at 5575.6 Hz and plays every effect at that rate (SIM_NOTES "The sound driver"; the samples are also the drum and effect instruments of the songs, pitched by key). Sound 56 has a near-linear table and may use a different scheme. |

## Window layouts (HCEGANT type 0; `tools/layouts.py`, `tools/render_windows.py`)

Layout n is window n, loaded into memory as-is: the window table DS:9230 holds a handle per window id.
An item id is (window << 8) | item index. The game asks for an item's rectangle with `f_252d8(id)`
(window struct + 0x2C + 4 * index → the item → its first 8 bytes), and the main window's buttons
arrive as commands with their item id (`f_6e5c0`: 0x102..0x118).

```
window header (0x2C bytes)
  +00 rect: left, top, right, bottom (i16, 640 x 480 screen coordinates)
  +08 2 x u16 (0)
  +0C u16 item count
  +0E u16 resource size
  +10 ... (4 x 0x14, then flags; not decoded)
  +2C item table: 4 bytes per item (offset into the resource + a placeholder segment); the loader
      f_25098 rebuilds it by walking the records (next = item + its length)
item record
  +00 rect (absolute)      +08 x, y relative to the window      +0C width, height
  +10 u16 parent id, +12 u16 container id, +14 u16 link id, +16 u16 own id
  +18 4 x u16 (1, 2, 1, 2 mostly; attachment modes?)
  +20 u8 state (0, 1, 2, 3 seen)
  +21 u8 type
  +22 u16 record length (by type, f_2512d)
  +24.. by type; +28 the type's parameter; strings are NUL-terminated
```

| Type | Length | What (drawing by `f_223b3`) |
|---|---|---|
| 0x00 | 0x29 | box: filled with the scheme's background, then a frame +28 px thick (`f_22226`) |
| 0x01, 0x03, 0x0A, 0x0B, 0x0E | 0x28 | not drawn: hotspots (buttons over a picture) |
| 0x02 | 0x29 | a filled rectangle, the scheme's background (`f_22170`; not a frame) |
| 0x04 | 0x38 | scroll bar? (`f_241f2`) |
| 0x05, 0x09 | strlen + 0x2D | text, string at +2A |
| 0x06 | 0x2A | picture, bitmap id at +28 (`f_25c75`) |
| 0x07, 0x08 | 0x2A | icon / check control (`f_244cc`) |
| 0x0C | strlen + 0x2D | text button, string at +2A: fill, a 1-px line in the foreground along the bottom, text |
| 0x0D | 0x2C | two-state picture: the bitmap word at +28 when +24 has bit 2, else at +2A (`f_223b3` 0x224E0; no layout uses the type) |
| 0x0F | 0x29 | a frame +28 px thick (`f_22248` → `f_1d018`), no fill; windows' borders are 2 |
| 0x10 | strlen + 0x31 | formatted field: +2C, printf format at +2E ("%d", "%d%%") |
| 0x11 | strlen + 0x31 | filled text, string at +2E |
| 0x12 | strlen + 0x31 | caption, string at +2E ("%s": the window's title): fill, a 1-px foreground line along the bottom, text |
| 0x13 / 0x14 | 0x29 | left and right / top and bottom lines +28 px thick (`f_22289` / `f_2225d` → `f_1d802` sides 5 / 10) |
| 0x15 / 0x16 | 0x29 | the same after a fill |

Every item starts with `f_220e4`: its **colour scheme** is the byte at +26 (+27 when the word at +24 has bit 2),
an index into the table at G:46E2, which start-up (`f_210d0`) copies from HCEGANT type 0 id 129 (16 schemes of 6
bytes: foreground, foreground, background, background in the modes with DS:5A97 bit 0, two bytes not decoded).
The colours are palette indices: e.g. scheme 1 (captions) cyan on dark grey, 3 black on white (fields, lists), 4
yellow on light grey (dialogs), 6 red on black (CANCEL), 9 black on light grey. Frames and lines are drawn in
DS:3DE0 (15, black) whatever the scheme. Texts of types 5 and 0x11 are filled with the background first, 9 and
0x10 are not. Records of length 0x29 hold +28 as a single byte (the thickness or the font).

Text items (types 0x05, 0x09, 0x0C, 0x10..0x12) are drawn by `f_21fa2`:
- Font: the byte at +28 (`f_24d5d`). Ids 2..5 are the slots DS:4A1A.. that start-up (`f_34ab_047d`) loads from
  the files FONT1..FONT4 (FONT1 / FONT2 have the glyph widths of SHARED 2 / 3; FONT3 is 15 rows, FONT4 an
  11-row bold); 0 / 1 are the PC fonts (SHARED 0 / 1). Captions and the status numbers use font
  0, "Click here to continue" font 2, the yard counters font 3.
- Alignment: (word +24 & 0x180) >> 7.
  - 0 / 3: centred, x = (left + right - width) / 2 (3 also underlines).
  - 1: left + 4.
  - 2: right - width - 4.
  - x is never less than left.
- Vertical position: y = (top + bottom - font height) / 2.
- Type 0x10's string can come from a far pointer at +2A / +2C at run time. Strings with % are printf
  formats ("%s" captions are the window titles).
- The text colour (+26?) is not decoded.

The windows:

| Window | What | Pictures |
|---|---|---|
| 0 | the Edit window: the close-up map (item 0x0000 at 64, 41 = G:110C / G:110E, 22 x 21 cells = G:10E0 / G:10DE), the tool strip 15000 (map, help, views, go-to buttons, pause, scent menu, health bars) | 15000, 15001 (help overlay) |
| 1 | the Map window (`f_6efd6` draws its map item 0x102 at 4 px per cell): map views, scent layers, buttons, population report | 14000, 14001 (help overlay) |
| 2 | "Select a Game" | 2500 |
| 3 | title | 2000, 2001 |
| 4 | | 16100 |
| 5 | message window | |
| 6 / 7 / 8 / 9 / 29 / 32 | menus and palettes | 6000, 4500, 4502, 5000, 4510, 4504 |
| 10..17 | tool option palettes | 5010, 5011, 5001, 5005, 5006, 5002, 5003, 5004 |
| 18 / 19 | Behavior Control / Caste Control | 4600 / 4601, 4620 / 4621 |
| 20 | | |
| 21 | History Window | 16000, 16001 |
| 22 | file dialog ("Path:", "Select Drive:") | |
| 23 | | 14002 |
| 24 | status ("%d%%" fields) | 13000 |
| 25 | the yard (`f_702f7`): house 7000 + lawn 7003 (items 0x1903 / 0x190F), toolbar 7010 (0x1904), its help overlay 7011, the yard picture item 0x1902 (7002; G:10D2 / G:10D4 = its corner + (1, 0)), grid area 0x1914 | 7000, 7002, 7003, 7010, 7011 |
| 26 | | 2100 |
| 27 / 30 | "Click here to continue" boxes | |
| 28 | DEBUG | |
| 31 | about box | 3000, 3001 |
| 33 | save prompt ("DON'T SAVE", "Save", "Cancel") | |

Main window commands (`f_6e5c0`, command id = item id), names from its help overlay 14001:

| Ids | Control |
|---|---|
| 0x102 | the map area |
| 0x105..0x108 | map views: Yard, Surface, Black Nest, Red Nest |
| 0x109..0x10D | scent layers (nest scents, food trails, alarm scent) |
| 0x10E | Show Trails |
| 0x10F | Behavior Control |
| 0x110 | Center on Yellow (Ctrl variants: the debug actions, SIM_NOTES "Debug commands") |
| 0x111 | Caste Control |
| 0x112 | Mystery Button (the random action `f_022bc`) |
| 0x113 | History Display |
| 0x114 | Efficiency Score |
| 0x115 | Ant Info Window |
| 0x116 / 0x117 | Experimental Menu |
| 0x118 | population report area |

## Bitmap format (type 2)

```
u16 mode     0 = opaque, 3 = has a mask plane
u8  planes   1 or 4
u8  flags    (ignored for decoding)
u32 size     buffer size hint (not reliable)
u16 width
u16 height
pixel data:  rows top to bottom. Each row has (mask plane if mode 3), then plane0..plane(N-1).
             Each plane row is ceil(width/8) bytes, MSB = leftmost pixel.
             Color index = p0 | p1<<1 | p2<<2 | p3<<3, looked up in the type 15 palette.
             Mask bit 1 = opaque.
```

The pixel data is never compressed beyond the archive-level LZSS.

## What the sprite ids are (from the contact sheet)

| ids | content |
|---|---|
| 100–113 | 15×15 window-control and map icons |
| 1000–1007 | Large black ant, 8 directions (masked) |
| 1050–1053 | Spider (large frames) |
| 1100–1107 | Small spider, 8 directions |
| 1200–1203 | Human's sneaker stomping, 4 directions |
| 1210/1211 | Lawn mower, top-down |
| 1250/1251 | Bird crossing the yard, two wing frames |
| 1260 | "For Sale" sign |
| 1300–1329 | Cat: walking, scared, running (the yard actor `yard.py` calls the bird, G:0254) |
| 7005 | Raindrop (yard window) |
| 7006 / 7007 | Black / red winged queen of a mating swarm (yard window, 8 x 1) |
| 7010 | Yard window toolbar (Patch / House / Strat / Graphic, Mate, Queens, Place, colony counts) |
| 7020–7022 | Yard grid strips (stacked, the grid from y 64) |
| 8500+ | Dog (yard window) |
| 8800–8802 | Lawn mower in the yard window: parked, and two mowing positions |
| 2000/2001 | Title screen (2001: 512×200 ant head, "© 1991 MAXIS") |
| 2500 | "Select a Game" screen (Tutorial / Quick / Full / Experimental / Load) |
| 3000, 3001 | About box, credits ("By Justin McCormick & Will Wright, IBM Version by Daniel Goldman") |
| 4500–4621 | Behavior and caste control panels (Forage/Dig/Nurse and Workers/Soldiers/Breeders triangles) plus their help overlays |
| 5000–5107 | Toolbars and tool icons (magnifier, food, pheromone dropper, …) |
| 7000–7022 | House exterior, yard strips |
| 8000–8905 | Isometric map actors: human walking or mowing, dog, small mower, human at the door |
| 9100–9203, 12000–12003 | Cutscene art: yellow ant, pupa, black vs. red fight, ant lion, jumping spider |
| 9150–9156 | 32×32 event icons (e.g. ant drowning) |

The tiny ants that walk around the surface and nest views are not among the type 2 bitmaps: they are
the type 9 sprite sheets below.
| 13000–16212 | Graph/history window, Game Over screen, map and status panels |
| 17000–17013 | Small UI widgets |
| 21004/21005 | Button strips (BACK / PREVIOUS / TOP) |
| 28000/28003 | Large panels |

## Map tiles and ant sprites (HCEGANT type 9)

Decoder: `tools/tiles.py` (contact sheets); renderer: `tools/ref/render_view.py`.

- **Tile sheets**, ids 10 (yard) and 9 (house), 32768 bytes: 256 tiles of 16x16, 128 bytes each; each
  of the 16 rows is 8 bytes = planes 0..3, 2 bytes each (MSB = leftmost). A surface cell's tile number is
  its surface byte; nest cells use `(dirt - 0x70) & 0xFF` from the same sheet; 0xF1..0xFF are the
  pheromone overlay ramp (shown instead of the ground when a scent view, T:07BE 0..4, is on and the
  level > 0x10: tile `(level >> 4) - 0x10`). Unused slots hold numbered yellow / orange placeholders.
- **Sprite sheets**, ids 13 and 14 (24576 bytes, 128 sprites of 192 bytes): 16 rows of 12 bytes =
  mask (1 = opaque), recolour mask, planes 0..3. Index = ant type byte & 0x7F (caste << 3 | heading):
  0 unused, 1..7 brood, then each caste in 8 headings (with carrying variants), 0x60..0x6F the queen's
  head and tail, 0x70 fight clouds, letters / numbers as placeholders. 14 is the surface's, 13 the
  nests' (loaded on demand by `f_02b43` with `f_1a5ea(id, 9)`); ids 15..20 are 160-byte variants (10
  bytes per row) for the DS:19D0 != 0 drawing path (`f_02aeb`). DS:19D0 is an EMS handle (set by the
  startup code at 0x026bb when at least 8 EMS pages are free, "TILESXXX"): the sheets are kept in
  expanded memory then; it is a storage path, not a different look.
- Colours: sprites are stored as the **yellow** ant. Black ants XOR all four planes with the recolour
  mask (yellow 1 → 14), red ants (type 0x80+) only plane 1 (yellow 1 → red 3), the yellow ant none
  (mode = low byte of the word at DS:1A58 + ((id & 0xFFBF) >> 6): 0, 3, 1).

## Saved games (`.ANT`)

Ported and verified: `tools/ref/simant_ref/savefile.py`, `tools/ref/test_savefile.py`.

A saved game has **no header and no checksum**: it is 307 blocks of the game's memory written one after
another, 48386 bytes in all. The block list is a table in SIMANT.EXE at 4E4B:0000 (flat 0x4E4B0):
8-byte entries `{int16 count, uint16 size, far pointer}`, ending at size 0; each block is `count * size`
bytes. In file order: the surface tiles (8192), both nests' dirt and exit fields (4 x 4096), the
surface / black / red ant arrays (x, y, state, type, e: 5 x 1000, 10 x 500), the alarm, black nest,
black trail, red nest and red trail pheromone maps (5 x 2048), the entrance rows, the yard colony grids
(2 x 192), the 192 patch seeds, then counters, statistics, the history graphs and ~230 single globals
(the game mode, the yellow ant, timers, the human / bird / dog state, ...). All values little-endian,
laid out exactly as in memory (see SIM_NOTES for the meaning of each address).

Not saved: the surface occupancy, the nest cell grids, the p2 pheromone map, the LFSR and C runtime
random states, and the screen state. Loading (`f_6c1a0`) starts a new game (`f_6cf1a` → `f_6b36b`),
reads the blocks over it (a short file: "Read error, game not loaded", game mode -1, the blocks read so
far stay), then `f_6cf5b` restores the tile set, rebuilds the occupancy and nest cells from the ant
lists, puts the yellow ant back and runs the census. Because the random state and census are not
saved, a reloaded game does not continue exactly like the original one would have (in the original
too). Saving (`f_6c328`) writes the blocks and clears the unsaved-changes flag T:02C2 (SimStep sets it).

## The executable, briefly

- It is not packed. The 216 KB resident MZ image is followed by ~290 KB of further code and data
  (DGROUP strings live around file offset 0x72000–0x78000). Ghidra and IDA will load the MZ part, but the
  appended overlay region has to be mapped by hand once the loader is understood.
- The debug strings give useful anchors: `YARD AREA @ %d, %d : %d, %d`, `Yardmode=%d`, `GOT Scenario`,
  `emstiles`, `DBRecall Unpack error` (the archive loader), `CHEAT %d`, `Balloon Size=%d`, and the
  `Ralloc` handle-based memory manager (a Mac Memory Manager clone).
- Its "Sound Driver Shell (c) 1991" supports DAC, FM (AdLib), Tandy and PS/1 PSG, Covox, and MIDI.
