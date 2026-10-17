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
| `FONT1`–`FONT4` | Raw Mac `FONT` resources (big-endian), copies of the fonts in SHARED |
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
| 11 | 4 | Fonts (Mac `FONT` format, BE; id 0 has a different header that is still undecoded) |
| 17 | 53 | Encyclopedia card layouts: references to `PICT` ids and rectangles (HyperCard-like) |
| 19 | 53 | Card names (`Top_Card`, `Ant_Anatomy`, `Castes`, `Scent_Trails`, …) |
| 21 | 88 | Text style runs for the type 10 texts (like Mac `styl`) |
| 6, 7, 9 | 1–2 each | Cursor table, cursor, misc tables (not yet decoded) |

### HCEGANT
| type | count | content |
|---|---|---|
| 2 | 212 | 16-color bitmaps |
| 15 | 2 | Palette. id 0 is u16 count (16) followed by 16 RGB triplets: the Mac 4-bit system palette (**index 0 = white, 15 = black**). |
| 0 | 37 | Window/dialog layouts (rectangles plus items, not decoded yet) |
| 9 | 11 | id 0: rectangle table (320 bytes). **ids 9 / 10: the house / yard tile sheets; 13..20: ant sprite sheets** (see "Map tiles and ant sprites") |
| 4 | 6 | Tutorial `STR#` strings |
| 7, 8 | 3 | Cursors |

### SOUND
| type | count | content |
|---|---|---|
| 20 | 30 | **Standard MIDI files** (SMF format 1, 10 tracks, 240 PPQ). Written out as-is to `.mid`. |
| 18 | 33 | Per-song metadata, 18 bytes: BE id, channel/instrument hints |
| 5 | 57 | Sound effects. The first 16 bytes are a signed delta table, followed by 4-bit codes (high nibble first). Start at 0, add `table[code]`, clamp to ±127. The sample rate is not stored; 11025 Hz is a guess to confirm by ear. Sound 56 has a near-linear table and may use a different scheme. |

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
| 1260 | "For Sale" sign |
| 1300–1329 | Cat: walking, scared, running |
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
  bytes per row) for the DS:19D0 != 0 drawing path (`f_02aeb`, not traced).
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
