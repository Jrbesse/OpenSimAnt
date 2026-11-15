# Art and audio plan for the remake

Goal: the remake should look, sound and feel like the original SimAnt (Maxis, 1991, DOS), without
publishing or deriving from Maxis's copyrighted assets. This file collects what the reverse engineering
established about the original's look (sizes, counts, palettes, timing, techniques), and a process for
making new art that matches it.

> This is engineering guidance, not legal advice. Before publishing, have someone qualified review the
> plan, the project name and the shipped assets.

## 1. Two ways to get the look

1. **"Use your own copy" mode: pixel-identical.**
   - The remake reads the player's own SimAnt files at runtime and uses the original art, fonts, sounds
     and music directly. This is how the reference tools already work: `tools/extract.py`, `bitmaps.py`,
     `tiles.py`, `fonts.py`, `layouts.py` and the sound tools.
   - Nothing from the original is ever committed or shipped.
   - This is the only route to a truly 1:1 look, and it should be a first-class feature, not a debug
     option.
2. **Built-in "clean" asset pack: so the game runs without the originals.**
   - New art, fonts, sound effects and music made from written specifications (below), drawn to the same
     sizes, grids, palettes, frame counts and timings, so either set drops into the engine without code
     changes.
   - It should feel the same at a glance without copying the original pixels, notes or text.

The engine should load assets through a manifest keyed by the original's ids (bitmap 1300, tile sheet
10, sound 23, STR# 1102 ...). The importer fills it from the player's copy, and the clean pack provides
the same keys at the same sizes.

## 2. Clean-room process for the clean pack

- **Split the roles.**
  - Spec writers may look at the original and the reverse-engineering notes. They write down measurements
    and descriptions in words, for example: "16 x 16 tile, sandy ground, 3 shades, scattered pebbles, must
    tile seamlessly". They never pass on images.
  - Artists, sound designers and composers work only from those written specs, this document, and
    generic real-world references: photos of ants, dirt, lawns, houses; their own synthesis.
  - The same person should not both study an original sprite and draw its replacement.
- **No tracing, sampling, re-colouring or "touching up"** of original pixels, waveforms or MIDI.
  Don't start from screenshots or extracted files.
- **Keep provenance.** For every clean asset, record who made it, when, and from which spec entry (a
  simple log or manifest column), and keep the source files (layered images, project files). It shows
  independent creation if ever questioned.
- **Review for similarity** before shipping. Where something comes out too close (a distinctive drawing,
  logo or melody), redesign it.
- **Exception — assets whose form the measurement fixes.** A bitmap is exempt from that test only where its
  geometry is fully determined by a number the spec writes down: a lattice's line spacing, a solid
  single-colour fill, one opaque pixel, an exact one-pixel-per-row profile (a 1-px raindrop line's 4 px of
  slope over 35 rows). Where the measurement fixes every pixel, such an asset is *expected* to match the
  original pixel for pixel — remaking it would break the fidelity the measurement exists to guarantee —
  and a 1.000 reading on it is correct, not a clean-room breach; where the measurement leaves a pixel-level
  choice the reading lands below 1.000, still exempt (the fixing measurement, not the number, is what
  exempts it). The class is narrow and mechanical: the exemption is recorded per asset in
  `remake/game/assets/clean/PROVENANCE.md`, naming the measurement that fixes the geometry (the line spacing,
  the colour-15 fill, the per-row slope), so "a measurement fixes it" cannot be claimed for an asset whose note
  names no measurement. It says nothing about pictures: a photographic or hand-drawn bitmap at 1.000 is still
  a finding, tested in full. The class is checked by `python tools/review/similarity.py bitmaps` (the A5
  similarity review's tool; `docs/A5_SIMILARITY_REVIEW.md` records the first pass): an exempt asset reads 1.000
  on the `identical` column where the measurement fixes every pixel, and just below it otherwise. The first
  such assets are the yard's `7021`, `7022` (512x55 lattice strips),
  `8905` (a solid colour-15 rectangle), `7006`, `7007` (one opaque pixel each) and `7005` (the 1-px raindrop
  line) — all 1.000 — with `7020` (the same lattice, one line placed differently) at 0.975 and `5002` (a
  two-colour separator bar) at 0.914.
- **Things to replace rather than imitate:**
  - logos and trademarks: "SimAnt", "Maxis", the title art, the "© 1991 MAXIS" credits;
  - all text: the SimAntipedia, help screens, speech-balloon lines, tutorial strings, menus and
    messages (write new wording with the same function and length);
  - the music compositions (new pieces in the same spirit);
  - recorded or sampled sounds.
- **Project name:** "SimAnt" is a trademark. A public release must not suggest it is official, while
  describing it accurately (for example "a fan remake of a 1991 ant-colony simulator"). The owner named the
  1:1 version **OpenSimAnt** (2026-10-30), in the style of OpenRCT2 / OpenTTD; the legal review (ROADMAP Track C)
  covers the name. The clean pack itself carries no "SimAnt" or "Maxis" marks.
- **What is generally fine to match:** the rules and mechanics, grid dimensions, screen and window
  geometry, colour counts and palette roles, sprite and tile dimensions, frame counts, animation timing,
  the general art style (16-colour pixel art, top-down ants, an isometric yard), and functional
  techniques such as the recolouring scheme and the vector spider legs. These are what this document
  records.

## 3. Global specifications

- **Screen**: 640 x 480, 16 colours (EGA/VGA planar), the main game window and floating windows
  (layouts: `tools/layouts.py --json`, FILE_FORMATS "Window layouts"; 34 windows, positions in screen
  pixels).
- **Palette**: the Apple Macintosh standard 4-bit (16-colour) palette, index 0 white … 15 black (the
  game's own palette resource holds it; a published, standard Apple palette, not Maxis art). Typical
  roles: 1 yellow (the player), 3 red (red ants), 15 black (black ants), 8 / 9 green (grass), 10 / 11
  browns and tans (dirt, ground), 12..14 greys (rocks, UI).
- **Cell grid**: the patch and the nests are drawn as 16 x 16-pixel cells. The surface is 128 x 64 cells,
  each nest 64 x 64, and a map window shows 40 x 30 cells.
- **Map window**: one colour per cell (4 x 4 px at 640 wide), coloured by tile class and occupant
  (SIM_NOTES "The map window").

## 4. Inventory by category (measured; regenerate with `python tools/asset_inventory.py`)

`asset_inventory.py` measures the player's own files and writes `extracted/inventory.json` (git-ignored),
with only sizes, counts, colours used, durations and tempos. The figures below come from the reference
copy.

| Category | Ids | Count | Sizes (px) / notes |
|---|---|---|---|
| Background tiles | sheets 10 (yard), 9 (house) | 256 each | 16 x 16, opaque; indexed by the surface tile byte (SIM_NOTES / FILE_FORMATS "Map tiles") |
| Ant sprites | sheets 14 (surface), 13 (nests); 15..20 EMS variants | 128 each | 16 x 16 with a mask, a recolour mask and 4 planes. Drawn as the **yellow** ant; black = all planes XOR the recolour mask, red = plane 1 only. Ids are caste << 3 | heading: 8 headings, castes and carrying variants, brood 1..7, the queen's head and tail 0x60..0x6F, fight clouds 0x70.. |
| Spider (patch) | 1000..1007, 1050..1053 | 8 + 4 | body 28 x 28 to 36 x 14 by heading, large frames to 67 x 67. Legs and fangs are **vector lines** in colour 15, from tables of per-heading points (`render_view.spider_lines`): new art must design its own leg geometry, and can keep the technique |
| Small spider (map) | 1100..1107 | 8 | 12 x 12, one per heading |
| Human / mower (map) | 1200..1203 / 1210..1211 | 4 / 2 | sneaker 23 x 68 and 68 x 23; mower 98 x 103 and 103 x 98 |
| Yard window | 7000, 7003, 7010, 7011, 7020..7022, 7005..7007 | 11 | house 281 x 226, lawn 233 x 226 (joined at x 344), toolbar 512 x 46 (+ help overlay 512 x 47), grid strips 512 x 51 / 55, raindrop 7 x 37, swarm queens 8 x 1 |
| Yard actors | human 8000.., dog 8500.., mower 8800..8802, cat 1300..1329, bird 1250..1251, sign 1260 | 30 / 16 / 8 / 19 / 2 / 1 | human about 17 x 30, dog about 18 x 16, cat about 23 x 16, bird 11 x 6, mower 26 x 42; frame lists and per-frame offsets in SIM_NOTES "The yard window" |
| Windows and panels | 4500..4699, 5000.., 6000, 13000, 14000.., 15000.., 16000.. | about 45 | e.g. the main window toolbar 512 x 133, the triangle panels 210 x 170, the tool palette 97 x 143, 16 x 16 tool icons, 15 x 15 window controls |
| Title / menus | 2000, 2001, 2500, 3000, 3001 | 5 | 512 x 172, 512 x 200, 320 x 256, 320 x 200 |
| Cutscenes / events | 9100..9203, 12000..12003, 9150..9156 | about 19 | 32 x 32 event icons; scenes up to 200 x 161 |
| Mono bitmaps | SHARED type 2 | 40 | SimAntipedia pictures and icons (1 bit) |
| Fonts | SHARED type 11 | 4 | 0: monospaced bold, 15 rows, 9 px advance; 1: monospaced 8 x 10 (PC style); 2: proportional sans, 10 rows (Geneva-like); 3: proportional serif, 10 rows (Times-like) |
| Sound effects | SOUND type 5 | 57 | 0.01..1.17 s, about 11 kHz (assumed), 4-bit delta coded |
| Music | SOUND type 20 | 30 | Standard MIDI files, 10 tracks, 240 PPQ, 1.3..103 s, tempi 120..480. **No program changes in the files**: the instruments come from the per-song metadata (SOUND type 18) and the driver |

## 5. Category notes for artists

- **Tiles**: the yard sheet must cover every tile class the simulation uses: open ground, food crumbs
  (4 sizes), rocks and pebbles, walls 0x60..0x67 with neighbour-dependent shapes (DS:2DF4 table, SIM_NOTES
  "Map tools"), nest entrances, corpses, ant-lion pits (7 frames 0x38..0x3E), the pheromone overlay shades
  0xF1..0xFF, and the house's floors and objects. Get the list of tile ids in use from the simulation
  code (`terrain.py`, `world.py`) rather than from the original sheet.
- **Ants**: draw each pose once in the yellow colour set, plus a recolour mask. That keeps the three
  colonies consistent and matches the engine's recolouring. There are 8 headings; the castes are
  workers, soldiers, breeders (male, queen) and the queen's two cells, and carrying variants exist.
- **Spider**: a body sprite per heading, with legs drawn as lines in code. The walk cycle is 8 frames
  (G:1042 & 7), and the fangs jitter when it attacks.
- **Yard**: an isometric lawn with a 12 x 16 patch grid, the house, doghouse and fence, plus the
  human, dog, cat, bird and mower sprites at the listed sizes. The Strat / Graphic views use plain grid
  strips.
- **UI**: match the window geometry from the layouts so the hotspots line up: buttons are hotspots over
  one picture per panel. Help overlays are separate pictures over the toolbars.
- **Speech balloons**: the content is all new writing; keep the timing and placement (SIM_NOTES
  "Speech balloons").
- **Fonts**: use openly licensed fonts with matching metrics. Candidates: the PC-style faces from "The
  Ultimate Oldschool PC Font Pack" (CC BY-SA 4.0, check the licence), and open Chicago / Geneva-like
  bitmap fonts. Or draw new 8 x 10 / 9 x 15 bitmap fonts. Do not convert the game's own font resources
  for shipping.

## 6. Audio notes

- **Effects**: recreate each effect by function (footstep stomp, mower, bite, bird, eat, dig, alarm, UI
  clicks ...) at a similar length and a lo-fi character. Which effect id plays when is in the code
  (`st.player.effect(st, 'sound', n)` calls). Decoded since (SIM_NOTES "The sound driver"): the driver's effect
  table names an instrument per effect; sampled effects play at 5575.6 Hz, some effects are FM notes.
- **Instruments**: the original's FM patches (OPL2 register values in SIMANT.EXE) are sound design, so the clean
  pack defines its own patches for the same driver (or plays its music through another synth).
- **Music**: compose new pieces per cue, with similar length, tempo and mood. The cues are the effect ids 10000+
  the sim and the shell play (the title, File > New, the win screen ...; `remake/README.md` "Sound"). Playing the
  player's own MIDI files is part of "Use your own copy" mode.

## 7. Engine requirements that follow

- An asset manifest keyed by original ids, with a size and frame-count check on load (warn if a clean
  asset doesn't match its spec).
- A recolour shader or palette swap for ant sprites (the mask scheme), and the 16-colour palette as the
  only colours in the clean pack, so "Use your own copy" and the clean pack mix freely.
- Vector-line rendering for the spider's legs (1 px, no anti-aliasing) to keep the original's feel.
- Integer scaling of the 640 x 480 canvas, with no filtering.

## 8. Everything the game reads from the original files (2026-10-30)

Not only art: to run with no original files, the clean pack (or the source code) has to supply all of this.
Where it is read today, in `remake/src/OpenSimAnt.Data` and `remake/game/Main.cs`:

| Source | What | Read by | Clean replacement |
|---|---|---|---|
| SIMANT.EXE, the sim's tables | ~6,300 bytes read before written, ~1,200 non-zero (`OpenSimAnt.Replay --deps`): direction / offset tables, terrain generator tables, cell and sprite tables, wall shapes DS:2DF4, cheat codes T:067E, start-up values | `ExeImage.NewState`, `GameSession.NewGame` | named tables in source (ROADMAP A2) |
| SIMANT.EXE, the saved game's block table 4E4B:0000 | the .ANT file layout | `SaveFile.Blocks` (`GameData.Flat`) | a table in source (it is the file format, FILE_FORMATS "Saved games") |
| SIMANT.EXE, UI tables | map dither patterns DS:1F9E, colour modes DS:1A58, menu colours DS:5FEA, alert colours DS:550C, key table DS:2CBE, balloon shapes (`Balloon.Make`), SimAntipedia glossary 4EE5:0520 | `MapRenderer`, `Balloon`, `Antipedia`, `Main` | tables in source; the glossary's words are new text |
| SIMANT.EXE, the sound driver's data | the effect table DS:0A82, volume tables, FM instrument patches | `SoundBank`, `SoundDriver` | tables in source; new instrument patches |
| HCEGANT type 0 | window layouts (34) and the UI tables 128 / 129 / 131 (colour schemes) | `Layouts`, `UiArt` | re-authored layouts in our own format (geometry and item types: functional) |
| HCEGANT type 2 | colour bitmaps: UI, title, yard, actors, spider, scenes | `UiArt.Bitmap`, `Spider`, `YardRenderer`, `Main` | new art |
| HCEGANT type 9 | tile and sprite sheets 9, 10, 13, 14 (15..20 EMS copies) | `MapArt` | new art |
| HCEGANT type 15 | the palette | `MapArt` | the standard Mac 16-colour palette |
| HCEGANT types 7 / 8 | cursors and masks | `Main` | new art |
| SHARED type 2 | mono bitmaps (SimAntipedia pictures, icons) | `UiArt.Bitmap`, `Antipedia` | new art |
| SHARED type 4 (and HCEGANT type 4) | STR# string lists: messages, ratings, names, balloon lines, credits, tutorial | `OriginalFiles.Strings` | new text |
| SHARED type 6 | the pull-down menus | `Menus` | new text, same structure |
| SHARED type 10 | texts: the 53 SimAntipedia cards, the save prompts 128 / 130 | `OriginalFiles.Text`, `Antipedia` | new text |
| SHARED type 11, FONT1..FONT4 | fonts 0..4 | `UiArt.Font` | open-licensed or new bitmap fonts, same metrics |
| SOUND type 5 | 57 sampled effects | `OriginalFiles.SoundEffect` | new effects |
| SOUND types 18 / 20 | per-song metadata and 30 MIDI songs | `SoundDriver`, `Main` | new songs |

## 9. Making the clean pack with isolated agents (decided 2026-10-30)

The owner chose to have the pack made by AI agents, kept apart as section 2 requires:

- **The spec side** is the session that studied the originals. It writes the specs (`docs/clean_pack/<category>.md`)
  and the engine work, and later reviews the results for similarity. It never makes an asset.
- **The makers** are fresh agents, one per batch, started with only the spec file's text and an output folder
  (`remake/game/assets/clean/<category>/`). Their instructions: read nothing else in the repository, never open the
  original files (SIMANT.EXE, *.DAT, *.NDX, FONT*), `extracted/` or `tools/re/build/`, and never search for them; work
  from the spec, general knowledge and their own invention. They write the assets with scripts (pixel art drawn in
  code, synthesized sounds, MIDI written note by note, new prose) and keep those scripts beside the output, so
  every asset can be regenerated and its making is on record.
- **Provenance**: each batch appends to `remake/game/assets/clean/PROVENANCE.md`: date, maker (agent run), spec
  file and revision, the files made, and the scripts that made them.
- **The pack is a first version**: decent, consistent programmer art that makes the game complete. Any asset can be
  replaced later (by people or better agents) from the same spec without code changes.

**A spec entry** gives, per asset or group:
- the id(s) and the category, and what it is for (where and when the game shows or plays it);
- sizes in pixels, frame counts, origins / offsets that the code depends on, and the transparency or mask rule;
- the palette indices allowed and their roles (for ants: drawn in the yellow set, plus the recolour mask);
- for text: the purpose of each line, its maximum length in characters or pixels, and the placeholders the code
  fills in (`%d`, `%s`), never the original's wording;
- for sound: the function, the length, the character (for example "a short dry thump"), the sample rate, or for FM
  the instrument's role; for music the cue, the length, the tempo range and the mood;
- what to avoid: the original's distinctive designs, logos and names.

Measurements, counts, sizes, timings and functional descriptions are fine to pass on (section 2); images, text,
waveforms and melodies are not.
