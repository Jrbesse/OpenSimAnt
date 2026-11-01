# Roadmap to version 1

What is left before the remake's first version, in one place. Keep this file current: tick items off here (and say
how they were checked) as they land. `HANDOFF.md` has the session-by-session detail; this file is the list.

**Version 1 is:**
- a faithful 1:1 remake of the 1991 DOS ant-colony game: the same rules, screens, sounds and timing;
- **playable with no original files**: a built-in clean-room asset pack (art, fonts, text, sound effects, music)
  and the game's own data tables in source, so nobody has to own the original to play;
- with "Use your own copy" as an option: point the game at the original files and it looks and sounds exactly
  like the original (the way it works today);
- published on GitHub under its own name, with builds for Windows, macOS and Linux.

## Burn-down (update every session)

Counted in **jobs**: one spec, one maker run, one encoder, one fix or one check, each about a tenth of a 5-hour
usage window when done by a subagent. At the start and end of each session: tick off what landed, add what was found,
and add a row to the log. New work found on the way goes into the table as it shows up.

| Area | Done | Left (jobs) | What is left |
|---|---|---|---|
| A1 asset layer + encoders | layer, launcher, bitmap / tile / sprite / font / balloon / legs / palette / version / strings + menus / texts + style runs + cards + glossary encoders | 4 | encoders: layouts, sound bank + effects, songs + cues; the export's `include_filter` |
| A4 bitmaps (252) | all 252 made (2026-11-01: the yard's passes 3-5, 102; the SimAntipedia's 40) | 1 | check in the game: the yard's people, animals, spider, map actors, door / room patches; the SimAntipedia pictures (540, 630 the weakest) |
| A4 layouts (37) | (measured) | 2 | spec, maker |
| A4 text | strings + menus (113 lists; spec, maker); texts spec `texts.md` + encoders (2026-11-01) | 3 | reword `texts.md` (67 six-word runs shared with the original, `tools/clean_pack/overlap.py`), `strings.md` (11) and `encyclopedia_bitmaps.md` (1); the texts maker; a maker revision of `src/strings` tutorial / messages lines that share runs |
| A4 sound (57 effects, instruments) | (measured) | 2 | spec, maker |
| A4 music (30 songs, 33 cues) | (measured) | 2 | spec, maker |
| A5 integration | launcher | 3 | CI game with no originals; clean screenshots of every window; similarity review |
| A6 identity | name, rename; title / about pictures; the Edit caption says OpenSimAnt on the clean pack | 1 | audit: no SimAnt / Maxis marks in the pack; the engine's own English fallbacks (file dialog, overwrite alert, "Click on a black colony") |
| B confirm and polish | B3 hang fix; 8200 / 8201 House-view-only; the deaths' cause icons; 2026-11-01: the tutorial's closing box 11112, the History graph's labels 1050 (and its plot start), the glossary read one entry off, 10044 confirmed unused | 9 | B2..B7 (6); polish: font 3 cramped, sprite legs ragged, house screens tables-vs-EXE |
| C release | | 5 | public repo, licences, legal review, player README, tagged v1.0.0 |
| **Total** | | **32** | B1 (the owner's test builds) is the owner's, not counted |

Pace so far: 6..10 jobs per 5-hour window (art makers cost the most), so **about 5 to 7 sessions** to version 1, plus
whatever the reviews find.

| Session | Jobs done | Jobs left | Est. sessions left |
|---|---|---|---|
| 2026-10-31 evening (start) | (baseline) | 42 | 5..7 |
| 2026-10-31 evening (end) | 9 (+2 found and fixed, +2 found open), in ~80% of the window | 35 | 4..6 |
| 2026-11-01 (start) | | 35 | 4..6 |
| 2026-11-01 (end) | 9 (5 agents in parallel: yard passes 3-5, SimAntipedia pictures, texts spec + encoders, 3 engine findings; +1 found and fixed: the glossary; +3 found open: rewording) in ~92% of the window | 32 | 4..5 |
| 2026-11-01 afternoon (start) | | 32 | 4..5 |

## Where things stand (2026-10-30)

Done and checked:
- **The simulation**: every rule ported (Python reference, then C#), byte-identical with the original in the
  emulator tests, and in 200,000 ticks of long scripted games (`tools/ref/longrun.py`).
- **The screens**: every window, menu, dialog and panel built from the original's layouts; 38 screen captures
  compared with the original's own screen, all identical except animation / redraw timing.
- **Sound**: the original's sound driver and an emulated OPL2 FM chip; effects and music.
- **Modes**: Tutorial, Quick Game, Full Game, Experimental, save / load, cheats, the SimAntipedia.
- **Builds**: Windows / macOS / Linux from one GitHub workflow (`.github/workflows/release.yml`).
- **Play-test**: the owner played it on 2026-10-29: "it seems to play identical to the original".

All of that still needs the player's own copy of the original. Track A removes that need.

## Track A: run without the original files (next)

The plan and rules are in `ART_PLAN.md` (sections 2, 8 and 9). In short: the game reads everything through one
asset layer that has two sources, the player's copy or the bundled clean pack, keyed by the original's resource ids.
This session (the one that studied the originals) writes **specs in words only**. Separate agents that never see
the original files make the clean assets from those specs.

- [ ] **A1. One asset layer.** *Mostly done 2026-10-30:* resources go through `OriginalFiles.Get` / `Of` (access
      log: the shell's `--requests=<file>`); `OriginalFiles.Flat` holds only the game tables and the embedded assets
      (`EmbeddedAssets`: sound bank, balloon pieces, spider legs, glossary; the version line is `VersionLine`);
      `OriginalFiles(byte[] packZip)` loads a pack, and the shell uses `res://assets/clean/clean_pack.zip` when no
      original is found (`--clean` forces it, `--pack=<zip>` names one). Checked: `OpenSimAnt.Replay --export-pack`
      writes the player's files as a pack (local only) and the game on it is pixel-identical on 24 screen sets; 161
      tests pass (the OPL traces cover the sound bank). Builder: `tools/clean_pack/build.py` (bitmaps and cursors so
      far; its encoders round-trip all 252 original bitmaps). **Left:** encoders for the other formats as their
      categories start (sheets, strings, texts + style runs, cards, menus, layouts, fonts, sounds, songs, the embedded
      assets); the Godot export must include `clean_pack.zip` (export preset `include_filter`); the launcher (done
      2026-10-30) offers both. Design (2026-10-30): the clean pack uses **the original's own resource formats**
      (the planar bitmaps, tile sheets, STR# lists, fonts, sounds, MIDI ...), keyed by the same archive / type / id,
      so the verified decoders and drawing code stay exactly as they are and either source drops in. The makers
      produce ordinary files (indexed PNG, WAV, MIDI, JSON, text); `tools/clean_pack/build.py` encodes them into
      the pack (`remake/game/assets/clean/pack/`). Steps:
  - `OriginalFiles` gets a second constructor that loads the pack instead of a game folder (same `Hcegant` /
        `Shared` / `Sound` lists, fonts 2..5 in place of FONT1..FONT4);
  - every use of `Flat` goes: numbers to the tables of A2; the assets embedded in SIMANT.EXE (the SimAntipedia
        glossary's words, the version line, the sound driver's instruments and effect table) become resources of
        new type ids that `OriginalFiles` builds from the EXE and the pack supplies as files;
  - an access log of every (archive, type, id) the game asks for, merged over the screenshot runs: the exact
        work list for A3; the pack builder checks sizes and frame counts against the specs.
- [x] **A2. The game's data tables in source** (the owner allowed committing these numbers, 2026-10-30; HANDOFF
      "Constraints"). **Done 2026-10-30:** `OpenSimAnt.Sim/GameTables.cs` (40 named tables, ~7.3 KB with the save
      layout, the screens' and the sound driver's tables), generated by `tools/ref/gen_game_tables.py`; games start from them by default
      (`--exe-state` for the old way); `OpenSimAnt.Replay --tables`: 200 games / 1.77 M ticks (with moves into other patches and the house)
      identical to games from the EXE; 18 screen sets pixel-identical; `SaveFile` reads its layout from the tables (remake/README "The game
      tables"). Still read from SIMANT.EXE outside the State, moved by A1: the map's dither patterns, the sound driver's
      tables and bank, the balloon pieces, the spider's legs, the glossary, the version line. Measured with `OpenSimAnt.Replay --deps` (2026-10-30): the
      simulation reads about 6,300 bytes of the starting image before writing them, and **only about 1,200 of
      those are non-zero**: direction and offset tables, the terrain generator's tables, cell / sprite tables, the
      wall-shape table DS:2DF4, the cheat codes T:067E, the saved game's block table, a few start-up values (the
      full list: `remake/build/deps.txt`, regenerated by the command). Write them as named, documented tables
      (`OpenSimAnt.Sim/GameTables.cs`) and build the starting State from them instead of SIMANT.EXE. Check: games
      started from the tables and from the EXE stay identical (like `OpenSimAnt.Replay --smoke`), and every trace
      test still passes. The UI's own tables come with it: the map's dither patterns DS:1F9E, the colour modes
      DS:1A58, menu / alert colours DS:5FEA / DS:550C, the key table DS:2CBE, the balloon shapes, the SimAntipedia
      glossary 4EE5:0520, and the sound driver's effect table and volume tables (its FM instrument patches are
      sound design: the clean pack brings its own, A4).
- [ ] **A3. Specs.** *Started 2026-10-30:* `docs/clean_pack/README.md` (the process, the `.pix` format, the
      makers' brief), the measurements `docs/clean_pack/data/*.json` (`OpenSimAnt.Replay --measure`: sizes, counts,
      lengths, timings and numeric structure only), the pilot spec `cursors.md`. One file per category under `docs/clean_pack/` (see `ART_PLAN.md` section 9 for the list
      and the template): for every asset the id, size, frame count, palette roles, timing, where and when it is
      shown, and what it must show, in words. No images, no original text, no notes.
- [ ] **A4. Make the pack** (isolated agents, one category at a time, each with only its spec; provenance in
      `remake/game/assets/clean/PROVENANCE.md`):
  - [x] palette: the standard Mac 16-colour palette, not Maxis data (`src/palette/palette.json`, 2026-10-31; the same
        colours as the original's in the 6 bits the VGA DAC uses; checked in the game). The colour schemes are part of
        the window layouts (HCEGANT type 0) below. Audit the same day: a complete pack also needs the SimAntipedia's
        style runs SHARED type 21 (88, with the text category); HCEGANT 15 id 1 and SHARED type 9 are never read;
  - [x] map tiles: yard (sheet 10) and house (sheet 9), 256 each, 16 x 16 (`docs/clean_pack/map_tiles.md`; the yard
        sheet made 2026-10-30, the house sheet 2026-10-31, each by an isolated agent and checked in the game on a dev
        pack, the house with `--patch=N`; the nest tunnels lightened 2026-10-31 so the black colony shows);
  - [x] ant sprites: surface (14) and nest (13) sheets, 128 each, with recolour masks (`docs/clean_pack/ant_sprites.md`,
        `src/sprites/`, 2026-10-31; build.py's encoder round-trips both originals). Left for the similarity review:
        the surface diagonals' legs are a little ragged;
  - [ ] the spider bodies and leg geometry (the legs done 2026-10-31: `docs/clean_pack/spider_legs.md`, `src/spider/`,
        checked in the game; the bodies left); the map overlays (small spider, sneaker, mower);
  - [ ] the yard window: house, lawn, toolbar, grid strips, rain, swarms; the yard actors (human, dog, mower,
        cat, bird, sign);
  - [x] the speech balloon's pieces (`docs/clean_pack/balloon.md`, `src/balloon/`, 2026-10-31, checked in the game) and
        our own version line (`src/version/version.txt`);
  - [ ] window and panel bitmaps, tool icons, window controls, the title and menu screens, the about box,
        event pictures and scenes (window 26), the game-over and win screens. *2026-10-31:* the UI batch's spec
        `docs/clean_pack/ui_bitmaps.md` (74 bitmaps: chrome, menus, toolbars, panels, help overlays, the game-over and
        win screens, tutorial pictures, encyclopedia buttons, start-up cards); passes 1-2 made (46, `src/bitmaps/`,
        checked in the game); the yard / actors spec `docs/clean_pack/yard_bitmaps.md` (114, see the yard items above;
        ready for a maker, after the UI batch). *2026-10-31 evening:* all 74 UI bitmaps made; the yard's passes 1-2
        (12: house outside / inside, lawn, strips, toolbar; checked in the Yard and House views); the screens / scenes
        spec `screens_bitmaps.md` and its 24 bitmaps (title, Select a Game, about box, the player's-ant pictures, death
        icons, ant lion and spider scenes; checked in the game); the SimAntipedia pictures spec
        `encyclopedia_bitmaps.md` (SHARED 40, ready for a maker). Left: the yard's passes 3-5, the SimAntipedia maker;
  - [x] mouse cursors (types 7 / 8): the pilot, 2026-10-30 (`src/cursors/`, checked in the game on a dev pack);
  - [x] fonts 0..5 (newly drawn bitmap fonts with the same metrics): spec `docs/clean_pack/fonts.md`, `src/fonts/`
        (2026-10-31, an isolated agent; the build checks every advance; checked in the game). Left for the similarity
        review / polish: font 3 (the small serif) is cramped, some symbols (& % ~ braces) are plain;
  - [ ] window layouts: re-authored in our own format from the measured geometry (rectangles, item types and
        ids; functional data, see `ART_PLAN.md` section 2);
  - [ ] text: every string list (messages, ratings, ant states, credits, menus), the save prompts, the tutorial
        (56 steps), speech-balloon lines, and the 53 SimAntipedia cards with their pictures, all new writing;
        *2026-10-31 evening:* the string lists and menus done: spec `strings.md` (113 lists: system, balloons,
        messages, the tutorial's 57 steps; 6 never-read lists excluded), encoder (round trip of all 119 lists and the
        menus), `src/strings/` + `src/menus/` by an isolated agent (checked in the game). Left: the texts (type 10:
        SimAntipedia cards, save prompts), the glossary and style runs;
  - [ ] sound effects (57), FM instrument patches, and 30 new songs with their cue list.
- [ ] **A5. Integration.** *The launcher is done (2026-10-30): at every start, "Original look" (the player's copy)
      or "Open assets" (the clean pack, enabled once it exists); `--original` / `--clean` skip it.* Left: a CI job plays games with no original files; screenshots of every
      window with the clean pack; a similarity review of the pack against the originals (by the spec side) before
      release.
- [ ] **A6. Our own identity.** The name is **OpenSimAnt** (decided 2026-10-30; the projects, builds and docs are
      renamed). Still to do: a new title screen, about box
      and credits, no "SimAnt" / "Maxis" marks in the clean pack; the original's names stay only in "Use your own
      copy" mode and in the docs' descriptions.

## Track B: confirm and polish (with the original files)

- [ ] **B1. The owner's test builds** on Windows / macOS / Linux (run 41019086870) and longer games: fix what
      they find first.
- [ ] **B2. Walk the tutorial's 56 steps** in the game (by hand or by script).
- [ ] **B3. A possible crash:** `World.SpiderDropFood` throws for a beaten spider over house furniture
      (`f_0c73d` not ported, `remake/src/OpenSimAnt.Sim/World.cs`). Port it, or show it cannot happen.
- [x] **A hang found 2026-10-30** (by the `--deps` runs): a patch seed of 0 (1 in 32,767, in the original too)
      froze the random generator and hung the terrain generator. Fixed as a marked DIVERGENCE (SIM_NOTES, "New
      game", SetupPatch).
- [ ] **B4. Ant Info on a held click:** the remake opens it; whether the original does is unconfirmed (the
      emulator capture never showed it, HANDOFF "Where this stopped").
- [ ] **B5. Handler audit:** the Experimental menu `f_67010` and its map tools `f_76f4a` against the shell.
- [ ] **B6. Screen details:** the hourglass cursor; the colours of message boxes and scenes (window 26) on a real
      screen; the two undecoded bytes of each colour scheme.
- [ ] **B7. Audio fidelity:** compare `OpenSimAnt.Replay --songs` with DOSBox; the sample / FM balance
      (`SoundMixer.SampleGain`). Not modelled: AdLib mode.
- Accepted differences (not bugs): capture diffs from animation / redraw timing; the marked DIVERGENCEs in the
  code (UI randomness on its own generator so drawing never changes the game; crashes in the original turned into
  safe behaviour). The help screens are empty in the DOS version too.

## Track C: release

- [ ] The repository made public (the GitHub repository is still named SimAnt-Evolved: rename it to match, if
      wanted).
- [ ] A licence for the code (none chosen yet) and the clean pack's licence and credits.
- [ ] A review of the name ("OpenSimAnt" contains the trademark "SimAnt", ART_PLAN section 2; projects like
      OpenRCT2 / OpenTTD are the precedent), the clean pack, the game tables in source (A2) and the docs by someone qualified
      (`ART_PLAN.md` note).
- [ ] README and `remake/dist/HOW_TO_PLAY.txt` rewritten for players: no original files needed; how to use your
      own copy for the original look.
- [ ] A tagged release (`v1.0.0`) with the three builds.

## After version 1

**Formica**: a fully modern game built around the original's core loop (goal 2 in `HANDOFF.md`), started once
OpenSimAnt is completely finished.
