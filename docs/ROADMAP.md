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
| A1 asset layer + encoders | layer, launcher, every encoder (bitmaps ... texts, glossary; 2026-11-01 afternoon: layouts, sound bank + effects, songs + cues, engine strings); the export's `include_filter` (done 2026-10-30) | 0 | |
| A4 bitmaps (252) | all 252 made and checked in the game (2026-11-01 afternoon: yard actors, spider, map actors, SimAntipedia pictures); evening: 630 (army ants) redrawn | 0 | |
| A4 layouts (37) | spec `layouts.md`, measured data, encoder, the 12 words (2026-11-01 afternoon) | 0 | |
| A4 text | strings + menus; texts (53 cards, glossary, pop-ups, prompts) made 2026-11-01 afternoon; all specs and made text at 0 shared runs | 0 | |
| A4 sound (57 effects, instruments) | spec `sounds.md`, encoder, the 16 FM patches (2026-11-01 afternoon); evening: the 35 effects, the loudness balance (by rendering: fm25 / fm53 / fm54 / fm17 louder) | 0 | (the owner's listening: `remake/build/clean_songs`) |
| A4 music (30 songs, 33 cues) | spec `music.md`, encoder, cues built (2026-11-01 afternoon); evening: the 30 songs (2 batches), the stings' velocities raised after a render | 0 | |
| A5 integration | launcher; 2026-11-01 evening: **the clean pack complete** (810 files); release.yml builds it and plays 6 screens on it under xvfb; **2026-11-04: that CI run is watched and green** (run 41920221727: pack built from source, 810 files / 0 missing, six screens drawn from it with no original files, "the clean pack res://assets/clean/clean_pack.zip" in every log); 14 windows drawn from the clean pack locally, no errors | 1 | similarity review |
| A6 identity | name, rename; title / about pictures; Edit caption; 2026-11-01 afternoon: the audit (no marks in the pack), the engine's own strings an asset (`EXE/engine_strings.json`) | 0 | |
| B confirm and polish | 2026-11-01 evening: **B2** (tutorial walk, step 46 fixed), **B4** (Ant Info: closes on release), **B6** (hourglass never shown, scheme bytes never read), font 3 and 630 polished; B3 hang fix; 8200 / 8201 House-view-only; the deaths' cause icons; 2026-11-01: the tutorial's closing box 11112, the History graph's labels 1050 (and its plot start), the glossary read one entry off, 10044 confirmed unused; afternoon: **B3** (f_0c73d + its missing table), **B5** (the Experimental menu / palette / drag loop: 10 differences fixed, emulator-checked); the house screens tables-vs-EXE (26 patches pixel-identical); every control as the original's (the owner's rule: the Edit window's double click, no shell keys) | 2 | B7 (owner); polish: sprite legs ragged |
| C release | player README (2026-11-04) | 4 | public repo, licences, legal review (owner decisions); tagged v1.0.0 |
| Checks found 2026-11-04 | | 0 | **B8 closed** in session 2: a trace that records no calls now prints `0/0 -- WARNING: the file records no calls, this row proves nothing` plus a closing warning, so `test_terrain.trace` cannot pass as evidence — and since 2026-11-05 the verdict (exit 1, `SOME FAILURES`) and the xUnit row fail on it too |
| Checks found 2026-11-05 | | 0 | **B11 closed** 2026-11-06: `--state=` now rebuilds the original's whole z-order from `DS:5702` (the History window, the SimAntipedia and the yard included) — the `mapnest.state` frame went 98432 → 1629 px, of which 1158 are the pre-existing menu-bar band and 99 the capture's own pointer. **B10 closed** in session 2 (the Map window's content was the window stack) |
| Checks found 2026-11-06 | | 2 | **B12** with a window restored on top by `--state=`, the Map window's caption reads "Black Nest View" where the original's capture shows an empty caption bar (~372 px of the frame; see the row in Track B). **B13** a capture whose front window is a *modal* is not drawn at all: `status.state` (window 24) still differs by 60131 px, and the shell says so on stderr |
| **Total** | | **9** | B1 (the owner's test builds) is the owner's, not counted |

### The order (checked at the start of every session, before any work)

The table is a set of jobs, not a queue: the *order* is a prerequisite order, and a session that starts work
without checking it is how a prerequisite gets left behind. At the start of every session, read the "What is
left" cells and answer these in writing in the session's log row:

1. **Is any job blocked by a job that is still open?** (Examples: the similarity review needs the *check* rows
   closed first, because it reads their evidence; the tagged release needs the licence and the name review; a
   spec has to land before its maker runs.) If a prerequisite is open and is agent-doable, it goes to the top
   of this session's list even if it is not the smallest job.
2. **Is any open job actually two jobs?** Split it, so the next session can pick up the half that is ready.
3. **Does any open job need the owner** (his test builds B1, his ears B7, his decisions on the name / licence /
   going public, any visual judgement the agent cannot make)? Mark it `(owner)` in the cell and never schedule
   it as agent work.
4. **Is anything found but not written down?** Every issue a session spots becomes a row before the session
   ends -- this is how the list stays honest. A finding with no row is a finding lost.
5. **Do the counts still add up?** The Total row equals the sum of the Left cells.

Pace so far: 9..15 jobs per 5-hour window with at most 3 agents at once (art makers and emulator work cost the most),
so **about 1 to 2 sessions** to version 1, plus whatever the reviews find and the owner's listening / play-test.

| Session | Jobs done | Jobs left | Est. sessions left |
|---|---|---|---|
| 2026-10-31 evening (start) | (baseline) | 42 | 5..7 |
| 2026-10-31 evening (end) | 9 (+2 found and fixed, +2 found open), in ~80% of the window | 35 | 4..6 |
| 2026-11-01 (start) | | 35 | 4..6 |
| 2026-11-01 (end) | 9 (5 agents in parallel: yard passes 3-5, SimAntipedia pictures, texts spec + encoders, 3 engine findings; +1 found and fixed: the glossary; +3 found open: rewording) in ~92% of the window | 32 | 4..5 |
| 2026-11-01 afternoon (start) | | 32 | 4..5 |
| 2026-11-01 afternoon (end) | 15 (13 agents, at most 3 at once: bitmaps checked, 3 specs + made text reworded, texts maker, layouts spec / encoder / maker, sound + music specs and encoders, FM patches, A6 audit + engine strings, B3, B5; include_filter ticked; +3 found: music as 2..3 batches, a sound listening pass, 630) in ~85% of the window | 21 | 3..4 |
| 2026-11-01 evening (start) | | 21 | 3..4 |
| 2026-11-01 evening (end) | 13 (8 agents, at most 3 at once: sound effects, the 30 songs in 2 batches, the loudness balance, A5's CI step and clean screenshots, 630, font 3, B2, B4, B6; the house screens tables-vs-EXE; +1 found and fixed: the controls made the original's exactly) in ~80% of the window | 8 | 1..2 |
| 2026-11-04 evening (start) | | 8 | 1..2 |
| 2026-11-04 evening (end) | 1 (the player README: `HOW_TO_PLAY.txt` no longer says the original is needed and lists the controls the shell really has; the README's status and the release notes' first-run paragraph say the clean pack ships. A5's CI watch: the first clean-pack `release.yml` run is green — pack built from source, six screens played on it with no original files. Baseline on eagle1: Release build clean, 165 tests pass, 27 trace files / 229,778 calls ALL OK) | 7 | 1 |
| 2026-11-05 nightly session 1 | 1 closed + 1 found. **B9 closed**: the Map window's black interior is the original's own — the map image is one byte per cell stretched 4 px, so a 64-cell nest map is a 256-px strip (x 192..448) in a 512-px item and the margins are black; the original's `mapnest.png` row y=210 is the same three runs (black 64..192, brown 192..448, black 448..576) and the remake's render differs from it in the right margin by 0/32768 px. Reproduced on the Hermes box first (`sh tools/shots.sh game yard`, exit 0, 11.5 s, clean pack in both logs). **B10 found**: `--state=mapnest.state` paints the 128-cell surface map across the item (left margin 32768/32768 differ; strip 18627/65536 with 16-px grey banding) where the original shows the 64-cell nest; `--map-content=2` changes nothing; `quick.state` still matches in 0/307200. Gate on eagle1: Release build 0 errors / 3 warnings, 165 tests pass, 27 traces ALL OK (only `test_terrain.trace` 0/0 — B8 reconfirmed). Order answers: (1) B9 was the first open job and is closed; B8 then B10 are next, neither blocked; (2) B9 was one job, **B10 splits in two** — why the state's Map content is ignored, and the 16-px banding inside the strip; (3) B7 and B1 are (owner), the Track C name / licence / legal decisions are (owner), nothing else needs him; (4) B10 added, the 0/0 terrain trace already had B8; (5) counts 1 + 2 + 4 + 1 + 1 = 9. | 9 | 1 |
| 2026-11-05 nightly session 2 | 2 closed + 1 found. **B10 closed** — it was the **window stack, not the map**: instrumented `DrawMapWindow` on eagle1, whose numbers were right all along (`content=2 mv=2 mw=64`, item 64..576 x 82..338, nest at 192..448); the shell drew the **Edit window after the Map window** (z-order 19,18,1,0) and its 16-px map grid filled 64..418 with brown, while the state says `DS:5702 = 0x0100` (the Map is the active window, as the original's screen shows). Fix in `Main.cs`: in `--state` mode raise `DS:5702 >> 8` once before the first draw, and stop the shell overwriting `DS:5702` with its own stack. Map item **51395 → 0 of 131072 px** vs `mapnest.png`; whole frame 98432 → 25587 (15956 with `--history`); `quick.state` unchanged but for the original capture's own pointer at (600,470). A clean-pack render on the Hermes box (`sh tools/shots.sh game`, exit 0, `the clean pack` in its log) asked vision one question -- "does the Map window's map area have solid black margins either side of a narrower strip, or artwork edge to edge?" -- and the frame shows artwork edge to edge (the surface view), so the normal, non-`--state` path is unchanged. **B8 closed** — a trace that records no calls now prints `0/0 -- WARNING: the file records no calls, this row proves nothing` plus a closing warning, so `test_terrain.trace` cannot pass as evidence (a real terrain trace is still worth recording). **B11 found**: the rest of the `mapnest.state` frame is the History window, which the state does not restore (it holds only the active window). Gate on eagle1 (both commits): Release build 0 errors / 3 addon warnings, 165 tests pass, 27 traces / 229778 calls ALL OK. Order answers: (1) B10 and B8 were the top two and neither was blocked; B9's closure (session 1) unblocked the visual line, so B10 went first. The similarity review (A5) still waits on the check rows. (2) B10 was one job — both halves had one cause — but the `--state` window stack is bigger than the Map window, so the rest splits off as B11. (3) B7, B1 and Track C's name / licence / legal decisions stay (owner); nothing else needs him. (4) B11 added. (5) A5 1 + B 2 + C 4 + B11 1 = 8, and B8 closes at 0. | 8 | 1 |

| 2026-11-06 manual session (headless pipeline test) | 1 closed + 2 found. **B11 closed** (see its row): `DS:5702` turned out to be the original's whole z-order list, so `--state=` now restores every open window — against `master` `bab30c0`, `mapnest` 27117 → 1629 px (the History window itself 0 px), `yard` 182707 → 4414, `panels` 84678 → 2311, `history` 59679 → 1616, `yardfront` 182406 → 4974, and no capture worse. The session also settled B8's leftover: `test_terrain` cannot record a trace (it drives the emulator, not a `State`), the empty file was removed from the traces copy, and the gate is green again (164 tests, 26 traces). **B12 found**: the Map window's caption says "Black Nest View" where the original's capture is blank. Order answers: (1) B11 was the first open agent-doable job and was not blocked; A5's similarity review now waits only on B12. (2) B11 was one job — the stack, the series and the card share one cause (the state's own z-order and selection words). (3) B7, B1 and Track C's name / licence / legal decisions stay (owner); nothing else needs him. (4) B12 added. (5) A5 1 + B 2 + C 4 + B12 1 = 8; **B13 added** by the PR review = 9. | 1 | 2 |

Next: **B13** (a restored front modal is not drawn) -- `status.state`'s z-order starts with 24, `StackWindow` drops it
and says so on stderr; raise it into `modal` in `RestoreStateFrame` (`Main.cs`) and diff `status.png` again. Then **B12**
(the Map window's caption): compare `DrawMapWindow`'s `Title(content <= 8 ? content : MapView)` with the original's
`mapnest.png` (blank caption bar) and trace `f_6efd6`'s title argument. Then **A5's similarity review**, which waits only
on B12. Neither needs the owner.
Why it matters: `--state=` is the visual oracle every state-based screen comparison rests on; B11 gave it the whole
window stack, and B12 is the last known pixel difference inside a restored frame that is not the capture's own pointer.

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
  - [x] window layouts (2026-11-01 afternoon: layouts.md, data/window_layouts.json, encoder, src/layouts/texts.json; checked in the game): re-authored in our own format from the measured geometry (rectangles, item types and
        ids; functional data, see `ART_PLAN.md` section 2);
  - [x] text (2026-11-01 afternoon: the texts maker, src/texts/; all text at 0 shared runs): every string list (messages, ratings, ant states, credits, menus), the save prompts, the tutorial
        (56 steps), speech-balloon lines, and the 53 SimAntipedia cards with their pictures, all new writing;
        *2026-10-31 evening:* the string lists and menus done: spec `strings.md` (113 lists: system, balloons,
        messages, the tutorial's 57 steps; 6 never-read lists excluded), encoder (round trip of all 119 lists and the
        menus), `src/strings/` + `src/menus/` by an isolated agent (checked in the game). Left: the texts (type 10:
        SimAntipedia cards, save prompts), the glossary and style runs;
  - [x] sound effects (57), FM instrument patches, and 30 new songs with their cue list. *2026-11-01 afternoon:* specs sounds.md / music.md, encoders, cues built, the 16 FM patches made (src/sounds/). *Evening:* the 35 effects, the 30 songs (2 batches), the loudness balanced by rendering; **the clean pack is complete**. Left: the owner's listening.
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
- [x] **B2. Walk the tutorial's 56 steps** in the game (by hand or by script). Done 2026-11-01 evening: the box table
      matches an emulator run of `f_0e4e4` (56 steps; `TutorialWalkTests.cs` walks them on the real SimStep, both nests);
      fixed step 46 (never advanced: the population graphs' hold must set G:1074, `f_7179d`), the missing picture's 1 x 1
      box, and a message box now ends the tick loop (`f_71b1a` blocks). The Godot input of each step is not scripted.
- [x] **B3. A possible crash:** `World.SpiderDropFood` threw for a beaten spider over house furniture
      (`f_0c73d` was not ported). Done 2026-11-01: `f_0c73d` ported (`world._spider_food_on_furniture`,
      `World.SpiderFoodOnFurniture`): the path is reachable (house, surface tile 0x27..0x3f). Checked in the emulator:
      six new `test_world.py` cases ("spider beaten furniture ...": rooms 0..3, food found, walk blocked to the map
      edge) are byte-identical over 6 snapshots; every line of the new function ran (`linecov.py`).
- [x] **A hang found 2026-10-30** (by the `--deps` runs): a patch seed of 0 (1 in 32,767, in the original too)
      froze the random generator and hung the terrain generator. Fixed as a marked DIVERGENCE (SIM_NOTES, "New
      game", SetupPatch).
- [x] **B4. Ant Info on a held click:** done 2026-11-01 evening, emulator-confirmed: a left press held 6 ticks on a
      non-yellow ant or brood opens it, and it closes on release (`f_202b8`; the shell waited for a click: fixed);
      `screens.py` antinfo / antinfo_gone pixel-identical. **Found:** only a double click "acts" in the Edit window
      (event +7 & 0x60): the shell acted on a single right click or Shift+click too; fixed (the owner: every control as the original's).
- [x] **B5. Handler audit:** the Experimental menu `f_67010` (and its twin for the Edit window's button,
      `f_67a24`) and the map tools' drag loop `f_76f4a` against the shell. Done 2026-11-01, read from the code
      (`adis.py` / `decomp.py`, SIM_NOTES "The tool palette", "Map tools") and checked against the original in the
      emulator (scenarios with mouse events: hover / hold / click mode, the tutorial, right click, a long drag, the
      RNG frozen while held). Fixed in the shell: the menu does nothing in the tutorial; the Edit button's palette
      opens beside the button (not above the Map's); the palette's option palettes open on hover beside the entry
      (no hold time), store the option on hover, and letting go takes the last entry hovered; Start Game places the
      yellow ant again (`f_6b7d0`, was missing); the Experimental buttons' bitmap stays 5107 until a tool is picked;
      the drag loop follows the pointer beyond the map item (patch-limited), a right press applies once, Ctrl+click
      is not Ant Info there, tools >= 5 and moves respect the patch test, and the game stands still while the loop
      (and any pop-up) runs. New `tools/ref/test_experimental.py` (enter, then Start Game, 8 contexts, byte
      identical; in `record_all.sh`); the tool functions themselves were already covered by `test_tools.py`. Emulator
      captures of the palette, its option palettes and the Edit button's palette match the remake pixel for pixel
      but for the mouse cursor. Left as DIVERGENCEs: the 6-tick double-click wait before the loop starts.
- [x] **B6. Screen details:** the hourglass cursor (never shown by the original: its one cursor load asks for id 4,
      which does not exist); the two undecoded bytes of each colour scheme (never read). Done 2026-11-01 evening by
      code reading. Not checkable here: the colours of message boxes and scenes (window 26) on a real screen.
- [ ] **B7. Audio fidelity (owner):** compare `OpenSimAnt.Replay --songs` with DOSBox; the sample / FM balance
      (`SoundMixer.SampleGain`). Not modelled: AdLib mode.
- [x] **B8. A vacuous green test.** `OpenSimAnt.Replay` printed `test_terrain.trace: 0/0 OK` -- the file records no
      calls, so the row proved nothing while looking exactly like a pass. **Closed 2026-11-05 (nightly session 2):**
      a trace that records no calls (and no `--func` filter) now prints
      `test_terrain.trace: 0/0 -- WARNING: the file records no calls, this row proves nothing`, plus a closing
      `WARNING: N trace file(s) replayed no calls ... they are not evidence` line before the verdict, so the row
      can no longer be read as evidence. **Completed 2026-11-05 (fixer, PR #3):** the count now reaches the verdict --
      an empty trace, or a `--func` that matched nothing (`0/0 with --func '...'`), ends `SOME FAILURES`, exit 1,
      unless `--allow-empty` asks for the deliberate case; and `ReplayTests.TraceMatches` (the row CI runs) fails on
      the same file instead of passing vacuously. **Settled 2026-11-06:** `test_terrain` cannot produce a trace at all —
      it drives the emulator and compares memory, so `record_traces.py test_terrain` logs `50/50 seeds identical` and
      `[trace] test_terrain 0 calls` (the recorder only writes calls made on a `State`). The tracked fix is in
      `tools/ref/record_traces.py`: a run that recorded nothing now deletes its own (empty) trace and says so, so no
      re-record can leave a file that fails the gate; the stale empty file was removed from the traces copy on the
      Hermes box as well, and the local gate is `164 passed` / `26 traces ALL OK` again. A real terrain trace would
      need the test rewritten to call the ported generator through a `State`.
- [x] **B9. The Map window's interior draws black — the original's, not a bug.** In the `game` shot (`--seed=1234
      --ticks=600`) the Map window's map area is black, where the `--yard` shot of the same run shows map art. **Not
      a clean-pack bug** (2026-11-04: both files on eagle1 reproduced it). **Closed 2026-11-05**: the black is the
      original's own. The Map window's item is 512 px wide (64..576) but the map image is one colour byte per cell
      stretched 4 px (`f_6efd6`), so only a 128-cell surface map fills it; a 64-cell nest map is a 256-px strip
      centred in it (x 192..448) with black margins either side, and `DrawMapWindow` fills the item black first for
      exactly that reason. Measured on the original's own capture `tools/re/build/screens/mapnest.png`, row y=210:
      black 64..192, brown (85,44,4) 192..448, black 448..576 — the same three runs as the remake's. The remake's
      `--state=mapnest.state` render differs from that capture in the right margin by **0 of 32768 pixels** (both
      black). Reproduced on the Hermes box first: `sh tools/shots.sh game yard` → exit 0, 11.5 s, both PNGs, `the
      clean pack` in both logs; pixel grid of `game.png`: brown nest map at x 192..448, black at 448..576. Note it,
      do not fix it (fidelity rule). Found and narrowed 2026-11-04, closed 2026-11-05.
- [x] **B10. `--state=` draws the wrong Map window content.** With `--state=tools/re/build/screens/mapnest.state`
      the remake painted the Map window's item (x 64..576) with the Edit window showing through: the left margin
      (64..192) was brown (nest dirt) instead of the original's black, and the strip 192..448 was broken by
      16-px grey column bands. `--map-content=2` changed nothing (byte-identical PNG). **Closed 2026-11-05
      (nightly session 2): it was the window stack, not the map.** Instrumented `DrawMapWindow` on eagle1: the
      numbers were right all along (`content=2 mv=2 mw=64 m=64,82,576,338`, fill and nest drawn correctly). The
      shell's z-order was `19,18,1,0` — the **Edit window drawn after (over) the Map window**, its 16-px map grid
      filling 64..418 with brown, while the state says `DS:5702 = 0x0100` (the Map is the active, front window,
      as the original's screen shows). Fix (`Main.cs`): with `--state`, raise the state's active window
      (`DS:5702 >> 8`) once, before the first draw, and stop overwriting `DS:5702` from the shell's own stack in
      frozen mode. Verified on eagle1: map item **0 of 131072 px** differ from `mapnest.png` (was 51395), and
      `quick.state` is unchanged but for the original's own mouse pointer at (600,470). Whole frame 98432 ->
      25587 px (15956 with `--history`; the rest is the History window -- B11 -- and that pointer).
- [x] **B11. `--state=` does not restore the whole window stack, and the History graph is not plotted.** After
      B10 the remaining 25587 px of the `mapnest.state` frame (x 260..640, y 200..480) are the **History window**:
      the original's capture has it open with a plotted graph and its labels; the remake only shows it with
      `--history` (25587 -> 15956 px), and even then a scrollbar/label strip (x 570..630, y 220..380) and the
      label row (y 380..450) still differ. The state holds only the *active* window (`DS:5702`); the rest of the
      stack is not in the mirrored memory, so open windows beyond the colony-panel set are not inferred. A `--state`
      capture whose active window is not in the shell's stack now says so on stderr instead of quietly drawing the
      shell's stack (fixer, 2026-11-05), so a bad capture is diagnosable. Found
      2026-11-05, by `--state=` after B10. **Closed 2026-11-06 (manual session, Hermes box):** the whole stack *is*
      in the mirrored memory — `DS:5702` is not one word but the original's z-order list (`f_211af` / `f_21336`):
      words of `(window << 8)`, front first, ended by `0x8000`. Read from the state's own copy: `mapnest` is
      `[1, 5, 19, 18, 21, 0]` (Map, SimAntipedia, Caste, Behavior, History, Edit), `yard` is `[25, 5, 19, 18, 21, 0]`,
      `history` `[21, 0, 1, 18, 19]`. `RestoreStateFrame` (Main.cs) rebuilds the shell's `zOrder` from it, restores
      the History window's selected series (`DS:2EF0`, colours `DS:8C26`, free mask `DS:2EF8`) and the SimAntipedia's
      card (`DS:2E26`), and re-applies the stack every frame so the game-start/view events cannot reorder it
      (`Front` is a no-op once the capture is restored). `Off(win)` now falls back to (0,0) for a window the shell
      has no offset for (said once on stderr). A/B of every capture under `master` `bab30c0` vs this head, both with
      the original files: **`mapnest` 27117 → 1629 px**, `yard` 182707 → 4414, `panels` 84678 → 2311, `history`
      59679 → 1616, `yardfront` 182406 → 4974, and 0 px change on `quick`, `surface`, `rednest`, the menus — no state
      regressed. The 1629 are 1158 the pre-existing menu-bar band, 372 the B12 caption and 99 the capture's own
      pointer; the History window itself is 0 px. The History window's *series* restore is untested code: every
      capture on this box has no series switched on (`DS:2EF0` = `0x8000` ×4, `DS:8C26` = 0 ×10), so it cannot change
      a pixel of any available frame — a capture with 2-3 series on would settle it. Verified on the Hermes box:
      Release build 0 errors / 3 addon warnings, 164 tests pass, 26 traces ALL OK. The frame itself, on the clean pack
      (`--clean --state=mapnest.state`, so no original pixels): `docs/screens/b11-window-stack.png`.
- [ ] **B12. With the Map window restored on top, its caption reads "Black Nest View" where the original's capture
      is blank.** The original's `mapnest.png` (a capture whose Map window is in the Black Nest view, `T:07C8 = 2`) has
      a plain grey caption bar; the remake writes `STR# 1000[2]` into it — 372 px of the frame (x 260..400, y 60..90,
      cyan text on the grey bar, against the original's 2041 grey / 324 cyan there vs the remake's 1669 / 696).
      Found 2026-11-06 while comparing the B11 fix; not fixed because the original's rule for *when* the Map window's
      caption is filled (`f_6efd6` draws the title it is given; the capture's own click path may never set one) is not
      traced, and guessing would trade one fidelity difference for another. One job: trace `f_6efd6`'s title argument.
- [ ] **B13. `--state=` does not draw a capture whose front window is a modal.** `StackWindow` admits only the windows
      the shell draws from `zOrder` (Edit, Map, History, Yard, SimAntipedia, Behavior, Caste); the original's modals
      are handled by the shell as `modal` (24 the Status window, 29 Ant Info, ...), so `status.state` — whose
      `DS:5702` list starts with 24 — is drawn without it (60131 px differ, x 128..400, y 96..400) and the shell says
      `--state: window 24 (DS:5702) is not drawn by the shell; left out of the stack` on stderr. One job: raise a
      restored front modal into `modal` instead of skipping it (and the same for a modal anywhere in the list).
      Found 2026-11-06 by the nightly reviewer on PR #11; `mapnest`, `yard`, `history`, `panels`, `yardfront` are
      unaffected.
- **`yard` is not a stable pixel oracle** (found 2026-11-05 by the nightly reviewer): three renders of
  `--seed=1234 --ticks=300 --yard` gave two identical and one differing by 217 px in a single 23×17 sprite box at
  (373,150)..(395,166) — the yard's dog. `game` and `history` were reproducible (0/307200 px, twice). Re-render
  before believing a small `yard` diff; do not file it as a regression without a second run.
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
- [x] README and `remake/dist/HOW_TO_PLAY.txt` rewritten for players: no original files needed; how to use your
      own copy for the original look. **Done 2026-11-04.** Both said the original game was required and that the
      open-assets button was still grey; `HOW_TO_PLAY.txt` also listed controls the shell does not have (`+` / `-`
      for speed, bare arrows to scroll, `F` to follow: the shell reads Shift+0..4 for pause and speed, Ctrl+arrows
      for scrolling and Home to follow — `Main.cs` `_UnhandledInput`, and the owner's no-extra-controls rule). The
      release notes' first-run paragraph was stale the same way. Checked against `Main.cs` (the launcher's
      `packOk` gate at `_Ready`, `ShowLauncher`) and the replay of the clean pack in CI (run 41920221727).
- [ ] A tagged release (`v1.0.0`) with the three builds.

## After version 1

**Formica**: a fully modern game built around the original's core loop (goal 2 in `HANDOFF.md`), started once
OpenSimAnt is completely finished.
