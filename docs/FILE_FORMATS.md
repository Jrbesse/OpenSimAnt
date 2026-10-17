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
| 9 | 11 | Rectangle tables (screen layout) |
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

The tiny ants that walk around the surface and nest views are not among the type 2 bitmaps. They are
probably drawn in code or stored in the undecoded type 8 resources; this needs confirming in the EXE.
| 13000–16212 | Graph/history window, Game Over screen, map and status panels |
| 17000–17013 | Small UI widgets |
| 21004/21005 | Button strips (BACK / PREVIOUS / TOP) |
| 28000/28003 | Large panels |

## The executable, briefly

- It is not packed. The 216 KB resident MZ image is followed by ~290 KB of further code and data
  (DGROUP strings live around file offset 0x72000–0x78000). Ghidra and IDA will load the MZ part, but the
  appended overlay region has to be mapped by hand once the loader is understood.
- The debug strings give useful anchors: `YARD AREA @ %d, %d : %d, %d`, `Yardmode=%d`, `GOT Scenario`,
  `emstiles`, `DBRecall Unpack error` (the archive loader), `CHEAT %d`, `Balloon Size=%d`, and the
  `Ralloc` handle-based memory manager (a Mac Memory Manager clone).
- Its "Sound Driver Shell (c) 1991" supports DAC, FM (AdLib), Tandy and PS/1 PSG, Covox, and MIDI.
