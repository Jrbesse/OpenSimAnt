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

More formats (text, sound, music, layouts) are added here as their categories start.

## Categories

| Spec | What | Status |
|---|---|---|
| [cursors.md](cursors.md) | the 2 mouse cursors | done 2026-10-30 (the pilot: spec, isolated maker, build, checked in the game) |
| [map_tiles.md](map_tiles.md) | the yard and house tile sheets | both tables written (yard sheet made 2026-10-30; house sheet ready for a maker) |
| [ant_sprites.md](ant_sprites.md) | the 2 ant sprite sheets (surface, nest) with their recolour masks | spec written 2026-10-31, ready for a maker |
| [fonts.md](fonts.md) | the 6 bitmap fonts (2 PC text-mode faces, 4 proportional faces) with their exact advance widths | spec written 2026-10-31, ready for a maker (encoder in `build.py`, round trip of all originals checked) |
| (to write) | palette, spider, UI bitmaps, title / scenes, SimAntipedia pictures, layouts, text, sound effects, instruments, music | see ROADMAP A4 |

## The makers' brief (give this with the spec)

> You are making new, original game assets for an open-source fan game, from the written spec below. Work only from
> the spec, general knowledge and your own invention. Do not open or search for any other file in this repository or
> on this computer: in particular never the original game's files (SIMANT.EXE, any .DAT / .NDX, FONT1..FONT4),
> `extracted/`, `tools/re/build/`, `docs/` (other than this spec) or `remake/src`. Do not imitate any existing
> commercial game's art, text or music. Write your output and the scripts that make it into the output folder named
> below, then append an entry to the provenance file named below (date, "agent", the spec file, the files you made,
> the script that makes them). Report what you made.
