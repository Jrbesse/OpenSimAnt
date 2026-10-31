# The clean pack: specifications

The game's art, fonts, text, sound effects and music, made new so the game runs without the original files
(`docs/ROADMAP.md` Track A, `docs/ART_PLAN.md` sections 2, 8 and 9).

## How it works

1. **Specs** (this folder). One file per category, written by the side that studied the original. Words and
   measurements only: what each asset is for, its size, frames, palette roles, timing. Never images, the original's
   text, waveforms or melodies. `data/*.json` holds the measurements (`Formica.Replay --measure`).
2. **Makers.** A fresh agent (or a person) per batch, given **only one spec file** and an output folder
   (`remake/game/assets/clean/src/<category>/`). Makers never open the original files, `extracted/`,
   `tools/re/build/`, the rest of `docs/`, or the engine's source, and never look for them. They make the assets with
   scripts kept beside the output, so every asset can be rebuilt and its making is on record.
3. **Provenance.** Each batch adds an entry to `remake/game/assets/clean/PROVENANCE.md`: date, maker, spec file and
   commit, files made, scripts.
4. **Build.** `python tools/clean_pack/build.py` encodes the sources into the game's formats and checks them against
   the measurements. `--fallback=remake/build/original_pack.zip` (from `Formica.Replay --export-pack`, local only)
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

More formats (text, sound, music, fonts, layouts) are added here as their categories start.

## Categories

| Spec | What | Status |
|---|---|---|
| [cursors.md](cursors.md) | the 2 mouse cursors | done 2026-10-30 (the pilot: spec, isolated maker, build, checked in the game) |
| [map_tiles.md](map_tiles.md) | the yard and house tile sheets | draft: the per-tile table is still to write |
| (to write) | palette, map tiles, ant sprites, spider, yard, UI bitmaps, title / scenes, SimAntipedia pictures, fonts, layouts, text, sound effects, instruments, music | see ROADMAP A4 |

## The makers' brief (give this with the spec)

> You are making new, original game assets for an open-source fan game, from the written spec below. Work only from
> the spec, general knowledge and your own invention. Do not open or search for any other file in this repository or
> on this computer: in particular never the original game's files (SIMANT.EXE, any .DAT / .NDX, FONT1..FONT4),
> `extracted/`, `tools/re/build/`, `docs/` (other than this spec) or `remake/src`. Do not imitate any existing
> commercial game's art, text or music. Write your output and the scripts that make it into the output folder named
> below, then append an entry to the provenance file named below (date, "agent", the spec file, the files you made,
> the script that makes them). Report what you made.
