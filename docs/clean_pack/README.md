# The clean pack: specifications

The game's art, fonts, text, sound effects and music, made new so the game runs without the original files
(`docs/ROADMAP.md` Track A, `docs/ART_PLAN.md` sections 2, 8 and 9).

## How it works

1. **Specs** (this folder). One file per category, written by the side that studied the original. Words and
   measurements only: what each asset is for, its size, frames, palette roles, timing. Never images, the original's
   text, waveforms or melodies. `data/*.json` holds the measurements (`OpenSimAnt.Replay --measure`).
2. **Makers.** A fresh agent (or a person) per batch, given **only one spec file** and an output folder
   (`remake/game/assets/clean/src/<category>/`). Makers never open the original files, `extracted/`,
   `tools/re/build/`, the rest of `docs/`, or the engine's source, and never look for them. They make the assets with
   scripts kept beside the output, so every asset can be rebuilt and its making is on record.
3. **Provenance.** Each batch adds an entry to `remake/game/assets/clean/PROVENANCE.md`: date, maker, spec file and
   commit, files made, scripts.
4. **Build.** `python tools/clean_pack/build.py` encodes the sources into the game's formats and checks them against
   the measurements. `--fallback=remake/build/original_pack.zip` (from `OpenSimAnt.Replay --export-pack`, local only)
   builds a dev pack with the missing parts taken from the player's files; run it with
   `-- --clean --pack=remake/build/dev_pack.zip`. Without `--fallback` it lists what is still missing, and writes
   `remake/game/assets/clean/clean_pack.zip` once nothing is.
5. **Review.** The spec side compares each batch with the original for similarity (ART_PLAN section 2) before it
   ships; anything too close is remade.

## Source formats

- `.pix`: pixel art as text, one row per line, one character per pixel: `0`-`9`, `a`-`f` = a palette index,
  `.` = transparent; lines starting with `#` are comments.
- The palette is the standard Apple Macintosh 16-colour palette, by index:

  | index | colour | | index | colour |
  |---|---|---|---|---|
  | 0 | white | | 8 | green |
  | 1 | yellow | | 9 | dark green |
  | 2 | orange | | 10 | brown |
  | 3 | red | | 11 | tan |
  | 4 | magenta | | 12 | light grey |
  | 5 | purple | | 13 | medium grey |
  | 6 | blue | | 14 | dark grey |
  | 7 | cyan | | 15 | black |

- Fonts (`fonts/font<n>.pix` + `font<n>.json`, n = the game's font number 0..5; [fonts.md](fonts.md)): the `.pix` is a
  **glyph grid**, 16 cells across: character code `c` at column `c % 16`, row `c // 16`, all cells the same size
  (picture width / 16 by picture height / rows of cells); a cell's left edge is the pen position, its top row the font's
  row 0; `f` = ink, `.` = none (no other characters). The `.json` holds what the picture cannot:
  `"advances"` (the pen advance of each character from code 0, exact), `"ascent"` and `"missing_advance"` (fonts 2..5),
  `"first_index"` (font 0 only, a header number). The height, each glyph's width and offset, the header fields and the
  tables are derived by `build.py`. Fonts 0 and 1 become `SHARED/11/0` and `1` (the game's own font format), fonts 2..5
  `FONT/1..4` (Apple `FONT`). The game never loads `SHARED/11/2` and `3` while `FONT/1` and `2` exist.

- Speech balloon (`balloon/balloon.pix`; [balloon.md](balloon.md)): the 11 pieces of 8 x 8 side by side, 88 x 8, in the order top_left, top_right, top, right, left, bottom_left, bottom_right, bottom, inside, tail_right, tail_left; `0` = white (inside), `f` = black (outline), `.` = transparent. Becomes `EXE/balloon.bin` (176 bytes: per piece 8 rows of an inside byte and a shape byte). `build.py` checks that the pieces join as the game lays them out.
- Spider legs (`spider/legs.json`; [spider_legs.md](spider_legs.md)): `{"north": view, "north_east": view}`; a view is
  `{"legs": [4 legs], "fangs": [4 frames]}`; a leg is 8 frames, each a polyline of 3 integer `[x, y]` points
  `[attach, joint, tip]`; a fang frame is a polyline of 3 points `[base, p1, p2]`. Pixels from the spider's centre (x
  right, y down), each coordinate within +-48, for the spider's right side. Becomes `EXE/spiderlegs.bin` (304 bytes).
  `build.py` checks the shape, the range, that each leg keeps its attach point, and that each fang starts at its fixed anchor.
- UI bitmaps (`bitmaps/<ARCHIVE>_<id>.pix`, e.g. `HCEGANT_4600.pix`; [ui_bitmaps.md](ui_bitmaps.md), and the yard's pictures, [yard_bitmaps.md](yard_bitmaps.md), and the screens and scenes, [screens_bitmaps.md](screens_bitmaps.md), and the encyclopedia's one-bit pictures, [encyclopedia_bitmaps.md](encyclopedia_bitmaps.md) (`SHARED_<id>.pix`, 1-plane: only `0` and `f`), in the same folder and format): one `.pix` per type-2 bitmap, exactly the measured size
  (`data/bitmaps.json`). A picture the game draws masked (help overlays, the win screen's eyes) must contain `.` pixels
  (they become the mask plane), any other none; a 1-plane picture (21004, 21005) only `0` and `f`. Becomes `ARCHIVE/2/<id>.bin`.
  `python tools/clean_pack/build.py --roundtrip=<pack.zip>` decodes every original bitmap of a pack and encodes it back
  (pixels, size, planes and mask must survive; builds nothing).
- String lists (`strings/system.json`, `balloons.json`, `messages.json`, `tutorial.json`; [strings.md](strings.md)): one JSON object per file, `{"<list id>": ["line", ...]}`; the entry count of each list is fixed by the game (`data/strings.json`), a line break inside a speech-balloon entry is a real newline (JSON `\n`; the build writes the two characters the game splits at), printable ASCII only, no backslash or percent sign, no leading or trailing spaces, widths checked in pixels with the clean fonts' advances (`src/fonts/font<n>.json`; font 0 = 8 px per character), none of the original's names (OpenSimAnt is allowed). Becomes `ARCHIVE/4/<id>.bin` (a Mac `STR#` list: u16 big-endian count, then length-prefixed strings; the archive is the measured one). 113 of the 119 lists are read by the game; 1030, 1300, 1310, 1350, 2000, 2100 never are and are refused.
- Menus (`menus/menus.json`; [strings.md](strings.md) group E): `{"titles": [5 labels], "menus": [5 lists of item labels]}`, a separator is `"---"` exactly where the game has one, titles start with F, W, V, O, S (the Alt keys), labels at most 14 characters (titles 9). Becomes `SHARED/6/0.bin` (u32 offset tables, then NUL-terminated strings; the build adds each label's leading blank cell). `--roundtrip=<zip>` also decodes and re-encodes all 119 lists and the menu resource byte for byte.
- Version line (`version/version.txt`): our own text, one line of printable ASCII, at most 72 characters (the Ctrl+Alt+V alert) -> `EXE/version.txt`. Needs no spec or maker.

More formats (text, sound, music, layouts) are added here as their categories start.

## Categories

| Spec | What | Status |
|---|---|---|
| [cursors.md](cursors.md) | the 2 mouse cursors | done 2026-10-30 (the pilot: spec, isolated maker, build, checked in the game) |
| [map_tiles.md](map_tiles.md) | the yard and house tile sheets | both tables written (yard sheet made 2026-10-30; house sheet ready for a maker) |
| [ant_sprites.md](ant_sprites.md) | the 2 ant sprite sheets (surface, nest) with their recolour masks | spec written 2026-10-31, ready for a maker |
| [fonts.md](fonts.md) | the 6 bitmap fonts (2 PC text-mode faces, 4 proportional faces) with their exact advance widths | spec written 2026-10-31, ready for a maker (encoder in `build.py`, round trip of all originals checked) |
| [balloon.md](balloon.md) | the speech balloon's 11 pieces (`EXE/balloon.bin`) | spec written 2026-10-31, ready for a maker (encoder and join checks in `build.py`, round trip of the original checked) |
| [spider_legs.md](spider_legs.md) | the spider's 8 legs and 2 fangs as 1-pixel lines (`EXE/spiderlegs.bin`) | spec written 2026-10-31, ready for a maker (encoder and checks in `build.py`, round trip of the original checked) |
| [ui_bitmaps.md](ui_bitmaps.md) | the user-interface bitmaps, 74 pictures: window chrome icons, pop-up menus and help pages, tool icons, the Edit / Map window strips with their help overlays, Behavior / Caste Control, History, Status, Game Over, the win screen and its eyes, the tutorial pictures, the encyclopedia buttons, the start-up cards (`HCEGANT/2/<id>`) | spec written 2026-10-31, ready for a maker (4 passes; encoder checks and `--roundtrip` in `build.py`, round trip of all 252 originals checked) |
| [yard_bitmaps.md](yard_bitmaps.md) | the yard and its actors, 114 pictures: the house outside / inside, lawn and grid strips, the yard toolbar and its help, the person, the dog, the cat, the bird, the spider's body and beaten frames, the map window's small spider, sneaker and mower, the triangle marker, the door / room patches (`HCEGANT/2/<id>`, ids 1000s, 7000s, 8000s) | spec written 2026-10-31, ready for a maker (5 passes; same encoder checks as the UI bitmaps; no `build.py` change) |
| [screens_bitmaps.md](screens_bitmaps.md) | the title, Select a Game and About screens, the 7 death-cause icons, the event scenes (the player's-ant pictures, the ant lion, the spider) with their animation patches, 24 pictures (`HCEGANT/2/<id>`, ids 2000s, 3000s, 9000s, 12000s); carries the project's own identity ("OpenSimAnt", no original name / credits) | spec written 2026-10-31, ready for a maker (3 passes, at most 5 looks at `preview.png` per pass; same encoder checks as the UI bitmaps; no `build.py` change) |
| [encyclopedia_bitmaps.md](encyclopedia_bitmaps.md) | the in-game encyclopedia's pictures, 40 one-bit bitmaps (`SHARED/2/<id>`, files `SHARED_<id>.pix`): the ant's anatomy (whole body, head, antennae, thorax and legs, abdomen's inside), castes, other social insects, species scenes, behaviour and nest, life cycles, the colony flowchart, 6 menus of boxed labels, a "next" button, and 7 never-shown spares | spec written 2026-10-31, ready for a maker (5 passes, at most 5 looks at the preview per pass; scientific-illustration originals; no `build.py` change: `SHARED_<id>.pix` is already accepted) |
| [strings.md](strings.md) | the string lists and the menus: 113 lists of short lines (window captions, game modes, status and advisor lines, history labels, ant names, credits for the About box, score window words, rating titles, 7 speech-balloon lists, 37 message boxes, the tutorial's 57 boxes; `SHARED/4` and `HCEGANT/4`) and the 5 pull-down menus (`SHARED/6/0`); carries the project's own credits; the long prose (SimAntipedia cards, glossary, save prompts) is the later "texts" category | spec written 2026-10-31, ready for a maker (4 passes; encoder `cat_strings` / `cat_menus` and widths / identity checks in `build.py`, round trip of all 119 lists and the menus checked) |
| (to write) | layouts, texts (SimAntipedia cards, glossary, save prompts, style runs), sound effects, instruments, music | see ROADMAP A4 |

## The makers' brief (give this with the spec)

> You are making new, original game assets for an open-source fan game, from the written spec below. Work only from
> the spec, general knowledge and your own invention. Do not open or search for any other file in this repository or
> on this computer: in particular never the original game's files (SIMANT.EXE, any .DAT / .NDX, FONT1..FONT4),
> `extracted/`, `tools/re/build/`, `docs/` (other than this spec) or `remake/src`. Do not imitate any existing
> commercial game's art, text or music. Write your output and the scripts that make it into the output folder named
> below, then append an entry to the provenance file named below (date, "agent", the spec file, the files you made,
> the script that makes them). Report what you made.
