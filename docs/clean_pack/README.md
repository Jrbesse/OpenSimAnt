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
   ships; anything too close is remade. The check is mechanical: `python tools/review/similarity.py bitmaps`
   reports, per bitmap, the share of pixels identical on palette index (`drawn` and silhouette IoU as well),
   and the A5 review (`docs/A5_SIMILARITY_REVIEW.md`) records the figures a pass produced. A reading near 1.000
   on a *picture* is a finding to remade. The one class exempt from the test — assets whose geometry a stated
   measurement fully fixes (ART_PLAN section 2, "Exception") — is *expected* to read 1.000 and is kept, with the
   exemption recorded per asset in `PROVENANCE.md`; in the first pass that is the yard's `7021`, `7022`,
   `8905`, `7005`, `7006`, `7007` (all 1.000), `7020` (0.975) and `5002` (0.914).

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
- UI bitmaps (`bitmaps/<id>.pix`, e.g. `4600.pix`; [ui_bitmaps.md](ui_bitmaps.md), and the yard's pictures, [yard_bitmaps.md](yard_bitmaps.md), and the screens and scenes, [screens_bitmaps.md](screens_bitmaps.md), and the encyclopedia's one-bit pictures, [encyclopedia_bitmaps.md](encyclopedia_bitmaps.md) (`<id>.pix`, 1-plane: only `0` and `f`), in the same folder and format): one `.pix` per type-2 bitmap, exactly the measured size
  (`data/bitmaps.json`). A picture the game draws masked (help overlays, the win screen's eyes) must contain `.` pixels
  (they become the mask plane), any other none; a 1-plane picture (21004, 21005) only `0` and `f`. Becomes `ARCHIVE/2/<id>.bin`.
  `python tools/clean_pack/build.py --roundtrip=<pack.zip>` decodes every original bitmap of a pack and encodes it back
  (pixels, size, planes and mask must survive; builds nothing).
- String lists (`strings/system.json`, `balloons.json`, `messages.json`, `tutorial.json`; [strings.md](strings.md)): one JSON object per file, `{"<list id>": ["line", ...]}`; the entry count of each list is fixed by the game (`data/strings.json`), a line break inside a speech-balloon entry is a real newline (JSON `\n`; the build writes the two characters the game splits at), printable ASCII only, no backslash or percent sign, no leading or trailing spaces, widths checked in pixels with the clean fonts' advances (`src/fonts/font<n>.json`; font 0 = 8 px per character), none of the original's names (OpenSimAnt is allowed). Becomes `ARCHIVE/4/<id>.bin` (a Mac `STR#` list: u16 big-endian count, then length-prefixed strings; the archive is the measured one). 113 of the 119 lists are read by the game; 1030, 1300, 1310, 1350, 2000, 2100 never are and are refused.
- Menus (`menus/menus.json`; [strings.md](strings.md) group E): `{"titles": [5 labels], "menus": [5 lists of item labels]}`, a separator is `"---"` exactly where the game has one, titles start with F, W, V, O, S (the Alt keys), labels at most 14 characters (titles 9). Becomes `SHARED/6/0.bin` (u32 offset tables, then NUL-terminated strings; the build adds each label's leading blank cell). `--roundtrip=<zip>` also decodes and re-encodes all 119 lists and the menu resource byte for byte.
- Version line (`version/version.txt`): our own text, one line of printable ASCII, at most 72 characters (the Ctrl+Alt+V alert) -> `EXE/version.txt`. Needs no spec or maker.
- Engine texts (`strings/engine.json`): our own wording for the engine's alerts and file dialog, `{"<key>": "text"}` with the 9 keys `caption_load`, `caption_save`, `overwrite` (`%s` = the path), `saved` (`%s`), `read_error`, `not_found`, `drive_error` (`%c` = the drive letter), `no_files`, `yard_choose`; printable ASCII plus `\n`, an alert line at most 40 characters, a caption at most 28, `no_files` at most 12. Becomes `EXE/engine_strings.json` (`OriginalFiles.EngineString`); on the player's files the same keys are read from SIMANT.EXE (addresses in `OriginalFiles.EngineStringAddresses`) and `--export-pack` writes them out.
- Long texts (`texts/cards.json`, `glossary.json`, `popups.json`, `prompts.json`; [texts.md](texts.md)): the SimAntipedia's prose, printable ASCII, a real newline for a line break, **bold link words between asterisks** (`the *crop* stores food`: the maker never handles a byte offset). `cards.json` = `{"<card id>": {"title": "...", "text": "..."}}` (53 cards; no `"text"` on 127, 129, 177): the title -> `SHARED/19` (a caption, at most 24 characters; the game writes a space as `_`), the text -> `SHARED/10/<text id>` and its style runs `SHARED/21/<text id>` (one run from the start, a new one wherever bold starts or ends; the text id is the card's, from `data/card_layouts.json`). `glossary.json` = `{"<id>": {"word": "...", "term": "...", "text": "..."}}` for the 26 ids 901, 910..929, 963..967: "word" is the link word as the cards write it in bold, "term" the pop-up's bold head word, "text" the definition (the pop-up is `*term* - text`); `EXE/glossary.bin` (26 entries of a text id and the upper-case word, 886 bytes) is **derived** from the 26 words. `popups.json` = `{"950".."962": "text"}` (the colony flowchart's 13 pop-ups), `prompts.json` = `{"128".."132": "text"}` (the save prompts 128 / 130; 129, 131, 132 are never shown). The **card layouts** (`SHARED/17`: pictures, text rectangles, hotspots) are functional data, not written by any maker: `data/card_layouts.json`, made by `tools/clean_pack/make_card_layouts.py` from the measurements of the player's pack (numbers and ids only) and always built. `build.py` ports the game's own line breaker (`ant_layout`, a check against the engine on all 51 reachable cards found no difference) and refuses a text that does not fit its rectangle with the clean fonts 2 and 5, a bold word that the game would not make a link of, a bold word that is not one of the glossary's, and a card that lacks the link words it must carry (by definition id). `--roundtrip=<zip>` decodes every text, style run, caption, layout and the glossary of a pack, writes them in this markup and encodes them back (the game sees the same text and bold words for all 94 texts; byte-identical for 79, the others carry editor debris, a second NUL or underline runs; the same lines and links on the card for 47 of the 50 card texts; 53 layouts, 53 captions and the glossary byte-identical).

- Window layouts (`layouts/texts.json`; [layouts.md](layouts.md)): `{"<window>.<item>": "text"}`, the 12 words inside window items (three window captions, the file dialog's two labels and its cancel button, the two "continue" lines, the debug window's button, the quit prompt's three buttons), printable ASCII, no `%` or backslash, at most the item's room in pixels (`data/window_layouts.json` "texts"; font 0 = 8 px per character). The 34 windows (rectangles, edge references and modes, item types, colour schemes, bitmap ids, the printf formats and drive letters) and the UI tables 128 / 129 / 131 are functional data, not written by any maker: `data/window_layouts.json`, made by `tools/clean_pack/make_layouts.py` from the player's pack (numbers and ids only), always built (`enc_layout` -> `HCEGANT/0/<id>.bin`); a window with a maker's word (18, 19, 21, 22, 27, 28, 30, 33) waits for its words and is listed as missing until they exist. `--roundtrip=<zip>` decodes all 34 layouts into the JSON's form and encodes them back (byte-identical with the original's dead bytes, i.e. the item table's memory segments and the padding behind strings, which are not stored; with zeros there they differ only at those bytes) and checks the 3 tables.

- Sound effects (`sounds/sfx_<id>.wav`, `sounds/fm_patches.json`; [sounds.md](sounds.md)): a WAV is RIFF PCM mono 16-bit **5,576 Hz** (the game's sample rate), at most 16,000 frames, length and peak within the spec's table, zero at both ends; the build codes it as `SOUND/5/<id>.bin` (a 16-entry signed delta table and 4-bit codes, high nibble first). `fm_patches.json` = `{"patches": [16 objects]}`, each the OPL2 register fields of one instrument (`feedback`, `connection`, and per operator `tremolo`, `vibrato`, `sustain`, `ksr`, `multiple`, `ksl`, `level`, `attack`, `decay`, `sustain_level`, `release`), a `velocity_offset` and an `effect_key`; the build writes them with the functional effect / instrument / channel tables into `EXE/soundbank.bin` (2,856 bytes). `build.py` refuses a file that is not mono 16-bit 5,576 Hz with only `fmt ` and `data` chunks, whose length or peak is off the table, that does not start and end at zero, or that the 4-bit code reproduces at under 9 dB signal-to-noise (a loud pure tone above about 1.8 kHz); and an `fm_patches.json` with a wrong id / order, an unknown or out-of-range field, a held carrier, a carrier level above 40, a silent patch or a missing `effect_key`. The 35 required effects are the samples the sound bank reaches; the 22 optional ids are accepted if present (same checks, no length / peak table).
- Songs (`music/<song id>.mid`; [music.md](music.md)): standard MIDI files, format 1, 240 ticks per quarter, track 0 the conductor (tempo only), one track per MIDI channel 1..10 (a fixed FM patch each, no program changes), note on / off only, keys 0..95 (a written key sounds an octave above the usual convention), at most 6 notes held at once; the build validates them with a port of the game's sequencer (length, polyphony, note lengths, key ranges, a tempo event at tick 0, velocities 2..127) and copies them unchanged as `SOUND/20/<id>.bin`; the 33 cue entries (`SOUND/18/<cue>.bin`) are built from `data/song_cues.json`, always.

More formats are added here as their categories start.

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
| [encyclopedia_bitmaps.md](encyclopedia_bitmaps.md) | the in-game encyclopedia's pictures, 40 one-bit bitmaps (`SHARED/2/<id>`, files `<id>.pix`): the ant's anatomy (whole body, head, antennae, thorax and legs, abdomen's inside), castes, other social insects, species scenes, behaviour and nest, life cycles, the colony flowchart, 6 menus of boxed labels, a "next" button, and 7 never-shown spares | spec written 2026-10-31, ready for a maker (5 passes, at most 5 looks at the preview per pass; scientific-illustration originals; no `build.py` change: `<id>.pix` is already accepted) |
| [strings.md](strings.md) | the string lists and the menus: 113 lists of short lines (window captions, game modes, status and advisor lines, history labels, ant names, credits for the About box, score window words, rating titles, 7 speech-balloon lists, 37 message boxes, the tutorial's 57 boxes; `SHARED/4` and `HCEGANT/4`) and the 5 pull-down menus (`SHARED/6/0`); carries the project's own credits; the long prose (SimAntipedia cards, glossary, save prompts) is the later "texts" category | spec written 2026-10-31, ready for a maker (4 passes; encoder `cat_strings` / `cat_menus` and widths / identity checks in `build.py`, round trip of all 119 lists and the menus checked) |
| [texts.md](texts.md) | the long texts: the SimAntipedia's 53 card captions and 50 card texts (anatomy, social insects, castes, behaviour, species, life cycles, ant facts, game strategy), the 26 glossary definitions with their link words (`EXE/glossary.bin`), the 13 colony-flowchart pop-ups, the two save prompts and three never-shown notes; the card layouts (type 17) are measured data, built unchanged | spec written 2026-11-01, ready for a maker (4 passes; encoders `cat_texts`, the engine's line breaker ported as `ant_layout`, and `--roundtrip` of all 94 texts, 53 layouts, 53 captions and the glossary in `build.py`) |
| [layouts.md](layouts.md) | the window layouts (`HCEGANT/0`, 34 windows and the UI tables 128 / 129 / 131): measured functional data (rectangles, edge references, item types, colour schemes, bitmap ids), always built; the maker writes only the 12 words inside items | spec written 2026-11-01, ready for a maker (one small pass; encoder `cat_layouts` / `enc_layout`, `data/window_layouts.json` by `make_layouts.py`, `--roundtrip` of all 34 layouts and 3 tables in `build.py`) |
| [sounds.md](sounds.md) | the sound effects and the FM instrument patches: 35 sampled effects the sound driver can reach (24 the game triggers; `sfx_<id>.wav`, 5,576 Hz mono 16-bit), the 16 two-operator FM patches (7 effects the game triggers, the 10 song voices) as `fm_patches.json`; the effect / channel / instrument wiring is carried over as numbers (`EXE/soundbank.bin`, `SOUND/5/<id>`) | spec written 2026-11-01, ready for a maker (encoder done: `cat_sounds` / `enc_sample` (4-bit delta code, table search, SNR check), `cat_soundbank` / `enc_soundbank` (the 2,856-byte bank with all the field checks); `--roundtrip`: all 57 originals sample-exact and byte-exact, the original bank byte-exact, a clean bank built from the original's own fields) |
| [music.md](music.md) | the 30 songs and the 33-entry cue list: when each plays, its length, pace, voices and mood in words; standard MIDI files (`src/music/<song id>.mid`, format 1, 240 ppq, 10 fixed FM voices, at most 6 notes held, keys 0..95) | spec written 2026-11-01, ready for a maker (encoder done: `midi_walk` ports the game's sequencer, `midi_check` the rules, `cat_music` copies `SOUND/20`, `cat_cues` writes the 33 `SOUND/18` entries; `--roundtrip`: the port reproduces ticks, notes, keys and channels of all 30 originals and the Game Theme's 35,856 steps, the 33 cues byte-exact) |

## The makers' brief (give this with the spec)

> You are making new, original game assets for an open-source fan game, from the written spec below. Work only from
> the spec, general knowledge and your own invention. Do not open or search for any other file in this repository or
> on this computer: in particular never the original game's files (SIMANT.EXE, any .DAT / .NDX, FONT1..FONT4),
> `extracted/`, `tools/re/build/`, `docs/` (other than this spec) or `remake/src`. Do not imitate any existing
> commercial game's art, text or music. Write your output and the scripts that make it into the output folder named
> below, then append an entry to the provenance file named below (date, "agent", the spec file, the files you made,
> the script that makes them). Report what you made.
