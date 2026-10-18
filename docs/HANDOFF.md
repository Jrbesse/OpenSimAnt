# Handoff: SimAnt reverse engineering and reference port

Snapshot of where things stand, written so a fresh Claude Code session can continue without re-reading the
old transcript. Last updated 2026-10-18 (afternoon: the shell now uses the original's windows).

## Goals (from the owner)

1. A faithful 1:1 modern remake of SimAnt (Maxis, 1991, DOS), graphics kept as close as possible, published
   on GitHub. **Reverse engineering comes first.**
2. Later: "SimAnt: Evolved", a new game built around the original's core loop.

Constraints:
- **Never commit original Maxis files or anything extracted from them.** The tools read the user's own copy
  (SIMANT.EXE and the .NDX/.DAT archives in the repo root, all git-ignored) at runtime.
- Commits use the owner's personal identity, which is configured repo-locally (do not change it).
- Keep an eye on the plan's usage limits (`get_usage`); stop at a clean, committed point when the 5-hour
  window gets high.

## Repo map

| Path | What |
|---|---|
| `docs/SIM_NOTES.md` | **The main knowledge base**: every decoded simulation rule, memory layout, addresses. Read the "Status and TODO" section first, then the section for whatever you port. |
| `docs/FILE_FORMATS.md`, `docs/RECREATION_PLAN.md` | Asset formats; the overall plan. |
| `tools/*.py` | Asset extraction (archives, bitmaps, palette, MIDI, sound); `tiles.py` the map tile / ant sprite sheets. |
| `tools/re/` | RE tooling: `build_flat.py` (flat memory image), `adis.py` (annotated disassembler), `decomp.py` (Ghidra pseudo-C with our names), `emu.py` (Unicorn emulator of the game), `symbols.json` (names). |
| `tools/re/build/` | Generated, git-ignored: `flat.bin`, Ghidra project + `decomp/`, `asm/` scratch dumps, `snapshots/` (verifier cache). Exists on the owner's machine. |
| `tools/ref/simant_ref/` | **The Python reference port** of the simulation, verified against the original. |
| `tools/ref/render_view.py` | Renders a State's surface / nests to PNG with the game's art (from the user's extracted files). |
| `tools/ref/test_*.py`, `verify.py`, `linecov.py` | Differential tests against the emulator, and a line-coverage helper. |
| `tools/ref/record_traces.py`, `record_all.sh` | Record the reference's calls during its tests as traces for the C# port. |
| `remake/` | **The Godot remake (C#)**: `src/Formica.Sim` (the sim), `src/Formica.Data` (files, art, session), `game/` (Godot project), `tests/` (trace replay, xUnit). See `remake/README.md`. |

## How verification works

`verify.Verifier` boots SIMANT.EXE in Unicorn, plays a Quick Game (seed 0x1234) and caches six memory
snapshots (ticks 0, 300, 900, 1500, 2200, 3000) in `tools/re/build/snapshots/`. `v.check(lin, port_fn, ...)`
restores each snapshot, runs the original routine at flat address `lin` in the emulator and the port on a
`State` built from the same memory, and compares memory 0x3d570..0x62000 byte for byte.

Useful `check` options: `args_fn`, `repeat`, `pre` (set globals on both sides; `set16.byte` for bytes),
`pre_once` (only before the first call per snapshot, so state can evolve), `post_args`, `ignore` (address
ranges, e.g. screen-only DS state).

Forced scenarios are how rare branches get covered: plant state with `pre`, then run many calls. Check
coverage with `python linecov.py simant_ref/<module>.py test_<x>.py [filters]`; it prints port lines that
never ran (continuation lines of multi-line statements show up as false positives).

The real-time clock (`f_1bc34`) is an input: the emulator advances it per read only during boot; the
verifier freezes it and copies it into `State.clock` (see SIM_NOTES "The real-time clock").

Run everything (each takes a few minutes):

```
cd tools/ref
python test_terrain.py; python test_pheromones.py; python test_colony.py; python test_movement.py
python test_surface.py; python test_nest.py; python test_nest.py --red; python test_world.py
python test_yard.py; python test_player.py; python test_sim.py 3000
python test_newgame.py; python test_newgame.py play; python test_events.py; python test_game.py; python test_savefile.py; python test_cheats.py; python test_tools.py; python test_debug.py; python test_markers.py; python test_balloons.py; python test_panels.py; python test_commands.py
```

All of these printed ALL OK at this handoff (terrain prints "50/50 seeds identical"); last full run
2026-10-17 after the map-tools commit (test_markers.py was added after it and passes on its own).

## What is ported and verified (`tools/ref/simant_ref/`)

| Module | Contents |
|---|---|
| `rng.py`, `state.py` | LFSR game RNG, MSC `rand()`, memory-mirroring `State` (+ clock) |
| `terrain.py` | patch generation, yard and house (`house_patch`); runs on a standalone `Patch` or on the `State` (`StateSurface`) |
| `pheromones.py` | trail / nest-marker / alarm maps |
| `colony.py` | census, priorities, caste choice, advisor job logic, health, food drop |
| `movement.py` | steering helpers |
| `surface.py` | surface ants: all states, combat, corpses, entering nests, AddSurfaceAnt; `NoPlayer` hooks |
| `nestgrid.py`, `nest.py` | nest grids, digging, exit field; **black nest** ants (all handlers, queen, brood, invaders); shared helpers take a colony dict |
| `red_nest.py` | **red nest** ants (a separate, different copy in the original) |
| `world.py` | slow phases, history graph, advisor status, weather/flooding, ant lions, caterpillar + bugs, **spider** |
| `yard.py` | the yard layer: human walk/roam + lawnmower, foot stamps, bird crossing, bird, dog, rain control, yard colonies |
| `sim.py` | **SimStep**: one full game tick |
| `newgame.py` | **new game** `f_6b36b`, the Full Game's move to another patch `f_01d48`, and patch setup `f_6ae20`: clearing, colony settings, patch seeds, terrain, scattered colonies, pre-dug nests, queens, the yellow ant's start per mode |
| `game.py` | game flow: rating, game-over screen, starting a game |
| `savefile.py` | saved games: the block table, save, load with its fix-ups |
| `cheats.py` | the cheat codes `f_6a920`: key matching and all 23 cheats |
| `debug.py` | hidden debug commands: add / kill ants, clear food, the random action `f_022bc` |
| `tools.py` | the map tools `f_770f6`: rocks, dig, ants, food, pheromone, insecticide |
| `markers.py` | the event-marker recorders behind the 'brood' / 'fight' / 'queen' / 'rest' effects |
| `balloons.py` | the speech balloons `f_06a4d` (timers, RNG draws, line choice; drawing is a hook) |
| `panels.py` | the Behavior / Caste Control triangles: weights ↔ marker point |
| `commands.py` | the yellow ant's menu commands `f_76cb9`: recruit, release, modes, alarm, dig, brood, hunt; the Exchange swap `f_11b81` / `f_11c18`; the spider's map click `f_756a6` |
| `player.py` | the yellow ant (also its death and the takeover, `player_event`): upkeep `f_7bf7e`, actions `f_7b7b8` (pathfinding to the cursor, picking up / dropping / eating, entering and leaving nests, fights), view-generic map accessors |

Player (yellow ant) interactions are routed to `st.player` hooks; `surface.NoPlayer` raises
`NotImplementedError` for the ones that change state, so a test fails loudly if it reaches unported code.

## Where things stand (2026-10-18, end of the night session)

**The Godot remake is under way, in C#** (the owner works in C# / Godot 4.6 .NET; see their other
project's CLAUDE.md). Everything is under `remake/`; read `remake/README.md` first.
- `remake/src/Formica.Sim`: **the whole of `simant_ref` is ported to C#** and checked against the Python
  reference: every recorded call of every reference test (25 trace files, ~225,000 calls, 67,200 SimStep
  ticks) replays byte for byte (`dotnet test remake/tests/Formica.Sim.Tests`). One marked DIVERGENCE (grep
  it) where the original reads an unset local.
- `remake/src/Formica.Data`: archives + LZSS, the starting State from SIMANT.EXE plus the start-up values
  the sim reads (step 11, verified against the emulator's booted memory), map art and renderer, the
  spider (bitmaps, legs), the Map window colours, STR# strings, sound effects, the bitmap fonts,
  `GameSession` (new game, the original's main-loop timing, pause, speed, effects queue, `WalkTo`).
- `remake/game`: a Godot 4.6 C# shell (`Main.cs`) that is playable: map window with the original's art,
  yellow ant control, the menu commands on keys, colony triangles, yard map, History graph, overview,
  scent views, Ant Info, speech balloons, sound effects, quick save / load, game-over rating; status
  lines in the game's font. Controls: `remake/README.md`. Checked with screenshot runs
  (`-- --ticks=N --screenshot=out.png`) and `Formica.Replay --fuzz` (150 games x 5000 ticks clean); not
  yet played by a human: please try it.
- "Formica" is a placeholder code name (the public name is still open, ART_PLAN). The repository has a
  top-level README for GitHub.

**Performance:** the C# SimStep runs well over 10,000 ticks per second (six 5,000-tick fuzz games with
startup in 1.2 s), so the original's "fast" speed is bounded only by drawing (`GameSession.FastDelay`).

**Usage note:** the 2026-10-18 afternoon session stopped at about 97% of the weekly allowance, which resets
2026-10-18 22:00 UTC; after that there is plenty of room.

**The screens (2026-10-18 afternoon):** the shell is now built from the original's window layouts.
`Formica.Data/Ui.cs` (`UiArt`) draws any layout (pictures, frames, captions, text in the game's fonts,
gauges, hit tests by item index; frame styles are approximations). `Main.cs` keeps a window stack (drag by
the caption, click to front) with: the Edit window (layout 0: tool strip, 22 x 21 cell map = G:10E0 /
G:10DE, health bars), the Map window (layout 1: the map at 4 px per cell, scent layers via T:07C8, toolbar,
population report), Behavior / Caste Control (18 / 19 on the ported Panels), History (21: the series table
T:082A / T:0852 and the original's scaling), Efficiency Score (24), the yellow ant's pop-up menu (7 / 8 / 32,
opened by pressing on the yellow ant as f_74fe0 does) and the yard window (25, `YardRenderer.cs`, a port of
render_view's yard code; patch clicks move in a Full Game), the scent overlay menu (6), Ant Info (29),
Select a Game (2, at start-up and F2), the Experimental menu as `f_67010` does it (Quick Game → Experimental;
in Experimental the tool palette 9 as a pop-up with the option palettes 12..17 and the map tools' drag
loop; Start Game returns to a Quick Game; SIM_NOTES "The tool palette"), message
boxes (27 / 30) for the sim's message_box effects, the detailed population report (23, `f_7179d`, while
the report is held), Show Trails (DS:2994), the Map window's small spider / human / mower overlays and the
control windows' preset ratios (decoded: SIM_NOTES "Behavior / Caste Control triangles"), the save prompt
(33) before F2 replaces a running game, the title (3) and about (31) screens, and the yard window's MATE /
AUTOMATIC / MANUAL (decoded: SIM_NOTES "The yard window"). Help overlays: F1 or the ? buttons. Screenshot
flags for each: remake/README.md. Notes: layout 0 is the Edit window and 1 the Map window (FILE_FORMATS had
them the other way round in places); T:07C8 matters to the sim (yard sounds draw from the RNG only while it
is 0), so the shell sets it only where the original's Map window does.

Suggested next session (in order):
1. Play the shell and note what feels wrong (speed, controls, missing feedback).
2. Remaining screens: window 5 is the **SimAntipedia / help text viewer** (the Map toolbar's "Ant Info
   Window" 0x115 → thunk 0x2f9b0 → `f_78db9` opens it; `f_78808` draws a SHARED type 10 text, with type 21
   style runs, into item 0x502, the caption via 0x501). The shell shows text 200 only: trace the topic
   choice and paging (and whether the help `f_76eb5` uses it too); the menus (no menu bar is decoded: find how the
   original reaches speed, sound, save / load, quit); the Edit window's bottom strip (item 21); G:1074 (set
   when several windows open: a redraw flag?); the windows' real frame styles; f_70edf's move condition
   (event byte +7 & 0x60). Done since the last list: PLACE, the patch click arithmetic, the corner values,
   the captions (STR# 1000).
3. The isometric yard map (f_7650c), if it differs from the yard window's colony views.
4. Music: the MIDI songs (SOUND types 18 / 20, effect ids 10000+) through a C# SoundFont synth (e.g. the
   MeltySynth library) or pre-rendered OGG; the player supplies or picks a SoundFont.
5. Event markers and balloon bitmaps (f_0696a), the yard window actors, the tutorial (f_0e425).
6. The clean-room art pack (ART_PLAN) once the screens exist.

## Notes for the Godot remake (what the reference teaches)

- **Art and audio**: read `docs/ART_PLAN.md`. It covers the two asset modes ("Use your own copy" for a
  pixel-identical look, plus a clean-room asset pack), the clean-room process, and the measured specs.
  `tools/asset_inventory.py` regenerates the metadata (sizes, frame counts, durations) from the
  player's own files without copying any art.
- **Assets**: never ship or commit Maxis data. The remake should read the player's own SIMANT files at
  runtime (or on first run) with ports of `tools/extract.py`, `bitmaps.py`, `tiles.py`, `fonts.py`,
  `layouts.py` and the sound/MIDI tools; the Python versions are the spec. Palette: HCEGANT type 15, the
  Mac 4-bit palette (index 0 white, 15 black); sprites are stored as the yellow ant and recoloured.
- **State model**: `simant_ref` mirrors the original's memory (`State`: segments SIM / G / T / DS, u8 /
  u16 / s16 accessors). That made byte-for-byte checks possible; the remake can keep the same layout
  first (easiest to port and to diff) and refactor into objects later. 16-bit wraparound, C truncating
  division (`_cdiv`, `_cmod`) and short-circuit order matter for exactness.
- **Randomness**: two generators. The game's LFSR (`State.rand*`, `rng.py`) drives the simulation; MSC
  `rand()` (`crt_rand_mod`) is used in a few places (new game, cheats, the Mystery Button). Every
  `Rand` call in the reference is in the original's order. UI that also draws from the LFSR: the spider
  composite, speech balloons, the yard window's rain and swarms (SIM_NOTES). For tick-for-tick fidelity
  the remake must make those draws at the same moments; otherwise give the UI its own generator.
- **Clock**: some timers read the real-time clock (`State.read_clock` ~18.2 Hz, `clock3` x3): the yard
  layer, speech balloons, the spider's remarks. A remake should feed a clock that advances with the game.
- **Seeding**: a real game seeds both generators from the time of day (SIM_NOTES "RNG").
- **The UI boundary**: everything screen-only goes through `st.player.effect(st, name, ...)` (sounds,
  redraws, messages, balloons, markers, pause) and `st.player` hooks (`player.Hooks`: game events, dialogs,
  the win / game-over screens). These hook names are the remake's event list: grep `effect(st, '` in
  `simant_ref` for all of them.
- **Tick**: `sim.sim_step` is one game tick; the yard, nests, surface ants, spider, weather and colony
  logic all run inside it in the original's order (SIM_NOTES "Simulation step").
- **Screens**: `render_view.py` shows how each view is composed (cells, sprites, recolouring, the spider
  polylines, the map window, the yard window from layout 25); `render_windows.py` and `layouts.py --json`
  give every window's geometry and item types (FILE_FORMATS "Window layouts"). Coordinates are 640 x 480.
- **Testing the remake**: the cheapest oracle is the Python reference. Record traces from it (State bytes
  after N ticks for fixed seeds, `test_sim.py`-style) and compare the Godot port against them; the
  emulator is only needed for new reverse engineering.
- **Running the tests**: each test file takes minutes; run them in the background, e.g. the list under
  "How verification works". All 23 passed at this handoff (test_commands.py and test_balloons /
  test_panels / test_markers ran on their own after the last full run).

## Next steps, in order

1. (done: the yard layer, sec8 `f_68513`, in `simant_ref/yard.py` / `test_yard.py`.)
2. (done: the player system, `simant_ref/player.py` / `test_player.py`; SIM_NOTES "The player (yellow
   ant)". UI routines the player code calls are stubbed per check via `Verifier.extra_stubs`, re-applied
   after each load because loads restore code; `test_player.configure` holds the setup, including an
   unfrozen clock for the fight animation, which busy-waits on it. `debug_player.py <label>
   [snapshot]` finds the first call where a check diverges. Not ported: `f_2f7d0` → `f_75d01`, the
   player-event UI (the yellow ant's death, becoming another ant, dialogs), which is a hook.)
3. (done: **SimStep `f_0894e`** in `simant_ref/sim.py`. `test_sim.py [ticks]` runs the original and
   the port side by side from every snapshot: 3000 ticks x 6 snapshots are byte-identical, past the
   recorded game's end; seeds 0x4321, 0x0001, 0xBEEF, 0x7777, 0x2B2B (`test_sim.py 3000 beef`) also
   match, and so do Full Games (`test_sim.py 2500 beef full`; snapshots up to tick 2200, as an idle
   Full Game ends around tick 2282). `debug_sim.py [snapshot] [ticks] [--pieces]` finds the first divergent tick
   and replays it component by component. The game-over screen `f_71d95` is UI (rating, new game): a
   hook. The port's real player hooks are `player.Hooks`; the UI hooks in it still raise.)
4. (done: **new game** `f_6b36b` / patch setup `f_6ae20` in `simant_ref/newgame.py`; SIM_NOTES "New
   game". `test_newgame.py`: 16 new-game scenarios (modes 1/2/3, C `rand()` states, alarm-trail mode)
   and 16 direct `f_6ae20` calls (colonies up to 1125 ants, other patches) x 6 snapshots, byte-identical;
   `test_newgame.py play [ticks]` starts a game on each side and runs SimStep side by side (2000 ticks,
   Quick and Full Games, OK). Ignored as UI: the behaviour panel's slider geometry and the resource
   manager's counters (see the test's SCREEN).)
5. (done: the Full Game's **move to another patch** `f_01d48` (`newgame.move_to_patch`) and the **house
   patches** `f_7304b` (`terrain.house_patch`, all 38, entered from the yard or the house); the food
   drop in the house. `test_newgame.py`: 77 house checks, 10 move checks; `play` also moves into the
   house and to another patch and plays 2000 ticks. Overlay callers go through vector thunks in
   segment 3cff (`90 90 90 EA off seg`); scan for them to find who calls an overlay routine.
   Mating-flight colonisation was already in yard.py; `f_01315` is an empty stub.)
6. (done: the **player events** `f_75d01` (`player.player_event`: deaths, animations, the takeover,
   the queen scene `f_758e0`), `test_events.py`, now also run inside `test_sim.py`; the **game flow**
   (`game.py`: rating `f_70fb0`, game over `f_71d95`, starting a game `f_725b6`), `test_game.py`.
   See SIM_NOTES "Player events and the game flow". test_sim.prepare(v) holds the UI stubs and the
   screen-only memory, each range traced to UI / library code with a write hook.)
7. (done: **saved games** `.ANT`, `simant_ref/savefile.py`, `test_savefile.py`; the format is in
   FILE_FORMATS.md "Saved games".)
8. (started: **rendering**. `tools/tiles.py` decodes the tile and sprite sheets (HCEGANT type 9),
   `tools/ref/render_view.py` renders a State's surface and nests with the game's art the way
   `f_03518` / `f_02c21` do; FILE_FORMATS "Map tiles and ant sprites", SIM_NOTES "Rendering the map
   windows". Checked by eye against the art (no pixel comparison: the emulator stubs drawing and has
   no planar VGA). **Note: the redraw `f_03de7` draws from the game's LFSR when the patch is
   visible** (SIM_NOTES "The redraw draws from the game's RNG").
   Done 2026-10-17 (SIM_NOTES "The spider composite", "The map window", "The yard window"):
   - the spider's legs and fangs: polyline programs extracted by `tools/re/polylines.py`,
     `render_view.spider_lines`;
   - the map window `f_6efd6`: surface, nests and pheromone maps, plus the spider, human and mower
     overlays (`render_view.render_map`);
   - the yard window `f_702f7`: the grid, the cat, dog, human, mower, bird crossing, "For Sale" sign,
     rain and mating swarms, and the Strat / Graphic colony views (`render_view.render_yard`).
   The DS:19D0 path is EMS storage, not a different look. All of it is checked by eye.
   Also done: the **window layouts** (HCEGANT type 0: FILE_FORMATS "Window layouts",
   `tools/layouts.py` (dump / JSON), `tools/render_windows.py` (an atlas of all 34 windows)). The yard
   window is now composed from its layout: the house 7000 + lawn 7003, the toolbar at the bottom, the
   actors at G:10D2 / G:10D4 = (65, 83), and the grid strips only under the colony views.
   Also done:
   - the fonts (`tools/fonts.py`; text placement in `render_windows.py`);
   - the Behavior / Caste Control triangles (`simant_ref/panels.py`, verified);
   - the Efficiency Score window, the population report, the History Window's scaling (SIM_NOTES).
   **Done: the yellow ant's commands** `f_76cb9` / `f_13f32` (`simant_ref/commands.py`,
   `test_commands.py` ALL OK), and the spider's map click `f_756a6` (`commands.spider_click`, walk /
   prey / Chase mode; verified), and the **Exchange swap** `f_11b81` → `f_11c18` (`commands.exchange`, 32
   click scenarios ALL OK; SIM_NOTES "The yellow ant's menu and commands"). All menu commands are ported.
   `game.py` calls the G:105E modes 0x0A / 0x0B "a pending yard map edit": they are Exchange / Chase.
   Also documented (SIM_NOTES): the Ant Info window (`f_67c1c`), the tool palette (`f_680a4`), the
   four in-game menus.
   Open (all visual detail; none blocks the Godot port):
   - colours 0x10.. in the map window (driver dither, DS:914C; drawn as a plain ramp);
   - the panels' bar charts (`f_0839a` / `f_08255`), the History Window's line drawing;
   - the text colours (+26?), the frame styles (named from their drawing routines only), the item
     fields +10 / +18 / +20, the UI tables 128 / 129 / 131;
   - the line algorithm of `f_16b58` (Bresenham assumed);
   - which tool options palette (windows 10..17) belongs to which tool; the help screens (`f_76eb5`);
   - sounds: which effect id plays which SOUND resource, and the music (MIDI) triggers.)
9. **Unported routines that draw from the game's RNG** (found 2026-10-17 by cross-referencing the
   callers of Rand* in `build/calls.tsv` with the `f_xxxxx` names in `simant_ref`; f_0cb3b / f_0cc8f are
   red-nest helpers already covered by their ported callers). Each can shift the random sequence, so
   each needs classifying and, if the remake must match tick for tick, porting:
   - map drawing: `f_03de7` (documented, see SIM_NOTES). `f_04666` (from it) is the spider overlay's
     animation (G:0FB8, G:06AC, G:0A06, Rand; see step 8). `f_07128` is the speech balloons (below).
     `f_07558` does **not** draw from the RNG: it ends at 0x075AE. The Rand-side calls `calls.tsv` gives
     it (up to `f_00a11`, the startup seeding at 0x07642) belong to the next function, the init near
     0x075B0.
   - (done: `f_6be50` / `f_6bf06`, add up to n black / red surface ants on free cells of the colony's
     half, `newgame.add_surface_ants`, `test_tools.py` ALL OK. Their callers: the debug commands below;
     `f_6b592` (no callers found: a preset start, Quick Game + 32 ants each + Full Game with 30 yard
     patches from DS:26D0..; not ported); `f_0e4e4` ← `f_0e425` (the tutorial advisor, a hook in
     world.py, not ported))
   - (done: the **debug commands**, SIM_NOTES "Debug commands", `simant_ref/debug.py`, `test_debug.py`
     ALL OK over 25 cases: add ants `f_015be`, kill ants `f_0161f` (+ `f_134b8` player_at), clear food
     `f_01707`, the random action `f_022bc` (menu command 0x112, all 15 cases), and the Ctrl-click
     dispatch `f_6f733` documented (UI, not ported). 0x110 is the main window's "Center on Yellow"
     button, 0x112 its "Mystery Button" (FILE_FORMATS "Window layouts").)
   - (done: cheats `f_6a920`, SIM_NOTES "Cheat codes", `simant_ref/cheats.py`; `test_cheats.py`
     types all 23 codes plus broken prefixes and toggles twice, key by key, from every snapshot: ALL OK.
     UI stubbed: f_277da, thunk 0x2f6ea (f_71b1a messages), f_00ed0, f_0125f; sound f_00ed8 runs.)
   - startup seeding: `f_00a11` (documented in SIM_NOTES "RNG"; called from the init near 0x075B0)
   - (done: the **map tools** `f_770f6` (rocks f_7723f, dig f_7739f, ants f_77672, food f_77790 /
     f_77ad6, pheromone f_7783a, insecticide f_778bd), SIM_NOTES "Map tools", `simant_ref/tools.py`;
     `test_tools.py` runs 306 tool scenarios (3 views x 7 tools x options x Alt x 3 previous points,
     8 clicks each): ALL OK. Not ported: the mouse handler around them, f_74fe0 → f_76f4a, which
     also sets the previous point G:09FC / G:09FE.)
   - classified, nothing to port:
     - `f_008ae` doesn't draw. The Rand calls `calls.tsv` puts in it belong to the next routine,
       `f_00932(n) = max(Rand(n), Rand(n))`, which has no callers; `calls.tsv` attributes call sites
       to the nearest function start above them, so check where a routine really begins.
     - `f_0c7cb` / `f_0c853`: no callers, segments hard-coded; a black / red nest "eat the food here"
       (tile 0x10 → Rand8, 0x11..0x13 shrink, food - 1). Dead code.
     - `f_7b59b`: no callers; a variant of exit_to_surface (f_7b661). Dead code.
   - still to do, UI that draws from the RNG:
     - (done: `f_06a4d` (← f_07128 ← the window draw f_038a6) is the **speech balloons**: taunts
       during fights, the brood's chatter, the queen's complaints and resting ants' remarks, from STR#
       lists 1220..1260. `simant_ref/balloons.py`, `test_balloons.py` ALL OK (9 cases, plus a check of
       the five list lengths against memory); SIM_NOTES "Speech balloons". The CS of f_07128 must be
       pinned to 0x250 in the test (see Gotchas). Details from the first look:)
       It runs only while the patch is visible (T:07B2) and T:07BE == -1.
       - Gates and positions: G:0F06, G:0EF6, G:0F10 and G:0F2E, with positions G:08EC, G:0852,
         G:0A02 and G:0AA2. They are written by the four **event recorders** (done:
         `simant_ref/markers.py`, `test_markers.py` ALL OK over 32 cases; SIM_NOTES "Event markers"),
         which the sim's 'brood' / 'fight' / 'queen' / 'rest' effect hooks stand for.
       - When a gate is 0 and its position is >= 0, it latches the position and arms.
       - Each source has a real-time-clock timer (G:050C / G:0732 / G:059A / G:0620 / G:07C4...) that
         re-arms at clock + Rand32() + 60, 0xAA or 0xB4. Each re-arm draws Rand2 or Rand4; 0 means
         draw the next frame of a bitmap group through `f_0696a`.
       - The lists are handles G:020A / G:0218 / G:021C / G:0234 / G:023A = STR# 1220..1260 (far
         heap; the index wraps at the null entry).
       Because the timing comes from the clock, a tick-for-tick remake has to model the clock reads
       (`State.clock`) to stay in step.
     - `f_70601` / `f_706d0` (← f_702f7 ← f_6fa6c ← f_6fac7 ← f_6fc36, from the yard map f_7650c
       and the win screen) are the **yard window's rain and mating swarms** (corrected 2026-10-17: an
       earlier note called this a pre-game screen, misled by `profile.py`'s string annotations,
       which tag any immediate that equals a DS string's offset). While it rains (G:0352) every
       yard-window frame draws 15 raindrops at random spots (Rand(400) + 50, Rand(150)), and the
       swarm queens jitter by Rand(3) - 1 (SIM_NOTES "The yard window").
       Earlier notes on this pair: / `f_706d0` (← f_702f7 ← f_6fa6c ← f_6fac7: a
     window's drawing, rects G:10D2.., drawing library calls; f_706d0 reads the yard position
     G:07CA / G:07CC)
10. (started 2026-10-18: the Godot remake in C#, `remake/`; see "Where things stand" and
    `remake/README.md`. Traces: `sh tools/ref/record_all.sh` (all tests in parallel, ~15 min) writes
    `remake/build/traces/*.trace`; `record_traces.py <test> [args]` one test. Each trace record is one
    outermost `simant_ref` call: args (State refs by name, bytes as hex), player hook class, clock, kbd,
    zlib'd State before / after.)
11. (done 2026-10-18: **the boot state.** `tools/ref/boot_diff.py [out]` boots the original in the
    emulator and diffs State memory with flat.bin (write the booted bytes to `remake/build/boot_state.bin`
    for the smoke test). Besides relocated segment words (the emulator loads at segment 0x100: high byte
    +1) and UI / far-heap data, start-up sets what the sim reads: G:0480 = 0x50 (highest passable tile;
    with 0, surface ants are blocked everywhere), G:0FBA = G:0FFE = 0x1E (the yellow ant's health warning,
    the advisor's hunger level), DS:1A2E = 0 (tile-set cache), G:10DE / G:10E0 = 0x15 / 0x16 (map window
    size, used by the event markers). `GameSession.ApplyBootDefaults` sets them; `Formica.Replay --smoke`
    checks that games from SIMANT.EXE + defaults and from the booted memory stay identical (2000 ticks,
    Quick and Full Game, the yellow ant walking): they do. Still open: where the init code takes the 0x1E
    values from (SIMANT.CFG? a resource?), and the far-heap string lists (balloon lines, G:020A..).)
12. (done 2026-10-18: **game speed**, SIM_NOTES "The main loop and game speed": T:07CC speed, delays
    T:07CE = 21 / 7 / 0 clock3 units, pause G:047E with the pending-action exception;
    `GameSession.Advance(seconds)`, `Speed`, `Paused`; the shell uses them.)
13. **UI screens**, each from the decoded layouts (`tools/layouts.py --json`, FILE_FORMATS "Window
    layouts") and fonts (`tools/fonts.py`): status line and messages (STR# text from the archives),
    the yellow ant's pop-up menu (`Commands.Command`), Behavior / Caste panels (`Panels`), the map window
    (`render_view.render_map`), the yard window and yard map (patch choice → `NewGame.MoveToPatch`),
    the History window, the tool palette (`MapTools.ApplyTool`), the game-over / rating screen
    (`Game.Rating`), save / load (`SaveFile`), cheats (`Cheats.Cheat` per key). Port `fonts.py`,
    `layouts.py`, `bitmaps.py` to `Formica.Data` as each screen needs them.
14. (spider done 2026-10-18: `Formica.Data/Spider.cs` (type-2 bitmap decoder, body frames, Bresenham legs),
    `SpiderLegs.cs` generated by `tools/ref/gen_spider_legs_cs.py` from `polylines.py`'s analysis; the fangs'
    jitter uses its own Random, not the game's LFSR, so drawing never shifts the simulation: a known
    divergence from the original's redraw, see step 8.) **Still missing in the renderer**: speech balloons and markers (effects `balloon`, the marker globals), the yard window
    actors. Sound effects: done 2026-10-18 as a hypothesis: f_00ed8(n) → f_29927 plays entry n of the
    DS:0A80 table (8 bytes each, filled from the SOUND archive at start-up, only with sound hardware DS:1926
    and sound on T:07AC); the shell plays SOUND type 5 id n (`Formica.Data/Sounds.cs`, 11025 Hz guessed).
    Confirm the table's load order and the rate by ear. Music: effect ids 10000+ (0x2713.., 0x4e20..) are
    the MIDI songs (SOUND types 18 / 20); not played yet (needs a synth or pre-rendered OGG, RECREATION_PLAN).
15. Tutorial mode (G:0EAC = 0) is not ported (`World.Advisor` throws, f_0e425).
16. Shell features added 2026-10-18 (all in `remake/game/Main.cs`, a stand-in until the real screens
    exist): STR# messages, a plain-grid yard map (Y; opens when the yellow ant dies in a Full Game), the
    game-over rating line, a History graph (G), the colony triangles (P; as the original's handlers do, a
    behaviour drag sets manual jobs G:0378 = 0 (f_07d07), a caste drag sets T:07E8 = 0 and recomputes the
    targets with f_085f8 (f_07ac1)), sound
    effects, the Map window overview (Tab), speech balloons as text (STR# 1220..1260 by list handle; the
    shell writes the map window's origin and size G:0508 / G:050A / G:10E0 / G:10DE so the event markers
    record spots in view; the strings hold literal backslash-n line breaks), Ant Info (Ctrl+click), scent
    views (V), quick save / load (F5 / F9), the status lines drawn in the game's font 2 (`Formica.Data/BitmapFont.cs`,
    a port of `tools/fonts.py`: both the game's own and the Mac FONT formats). The rating line's title: f_71d95 shows entry `rank` of the
    G:0328 list (STR# 1900) below the mode's name from G:0324 (decoded). `Formica.Replay --fuzz [dir] [games] [ticks]` plays random games
    (clicks, commands, tools, cheats): 150 x 5000 ticks run clean. The one crash path it found (f_75d01 with
    no ant left in mode 3 reads an unset local) is a marked DIVERGENCE in `PlayerActions.cs` (grep
    DIVERGENCE for all deliberate departures from the original).

## Gotchas learned the hard way

- **Shell heredocs mangle backslashes and backticks** in this environment (it happened again on
  2026-10-18 with `'\n'` inside a Python heredoc: the file got a real newline in a C# string). Write code with the Write/Edit
  tools, or put a script in a file and run it. Never generate source through `cat <<EOF`.
- Ghidra pseudo-C is often wrong about **segments** (G vs T vs DS) and garbles jump tables. Always confirm
  with `adis.py`, which annotates `es=` segments. Segments: DGROUP/DS 0x55b3, SIM 0x3e1d, G 0x50f6,
  T 0x3d57, red trail map at 0x4da7:0.
- Overlay calls go through vector thunks (for example `f_2f7da` → `f_7a69d`); `decomp.py <thunk>` shows the
  target.
- Unicorn harness: SS must equal DS; `call_lin` returns AX only.
- `build/calls.tsv` files each call site under the nearest function start above it. When the next
  routine has no entry of its own (no direct callers), its calls are credited to the previous one
  (`f_008ae` and `f_07558` looked like Rand callers this way). Check where the routine really ends
  (`retf`) before classifying it.
- The string annotations of `adis.py` and the scratch profilers (`'...'` after an immediate) only mean
  that the immediate equals some DS string's offset. They are often false (a window id, a constant), so
  don't classify a routine by them.
- `emu.seg_of` gives an overlay routine its overlay's base as CS. An overlay can hold more than one code
  segment (the 0x74FE0 overlay has a second one at 0x76F40). A routine there that uses a CS-relative jump
  table (`jmp cs:[bx + n]`) then jumps into the wrong code. Pin the CS in the test (`test_tools.py` does
  this for `f_770f6`). The table normally sits right after the jump, which gives away the real base.
  Resident code has the same trap: if `seg_of` picks a segment based between a routine and the target
  of one of its near calls, the call wraps around 64K and the emulator runs garbage or hangs
  (`test_balloons.py` pins `f_07128` to CS 0x250, the segment the game's far calls use there).
- C semantics matter: signed division and remainder truncate toward zero (`colony._cdiv`, `world._cmod`),
  16-bit wraparound (`s16`), and the short-circuit order decides which `Rand` calls happen.
- Some original code reads uninitialised locals in unreachable states; ports raise NotImplementedError
  there rather than guess.

## Commit log since the last summary

2026-10-18 afternoon (the screens):
```
(next) Remake shell: the Map toolbar's Ant Info opens the SimAntipedia text viewer (window 5), first page
c514379 Remake shell: the control windows' corner values (percent / ants) and bar placement from f_083d9
76335d3 Remake shell: the yard window's PLACE (f_01efa)
a387036 Remake shell: window captions from STR# 1000
7ea5c3f Remake shell: yard patch clicks use f_70edf's arithmetic
b92e9ef Remake shell: the yard window's MATE, AUTOMATIC and MANUAL as f_6f7f0 does them
afb6836 Remake: Mac Roman 0xAA (™) in strings; BitmapFont maps MacText's special characters back
195869f Remake shell: the title screen (layout 3) before Select a Game, the about box (layout 31, F3)
0b24139 Remake shell: the save prompt (layout 33) before a running game is replaced (F2)
6819d56 Remake shell: the Experimental button shows the tool's icon; PAUSE shows inverted while paused
a561c59 Remake shell: the Experimental menu as f_67010 does it; the tool palette as a pop-up
0485c84 Remake shell: the Behavior / Caste preset ratios (Set 1..3); notes: the control windows' handlers
003e527 Remake shell: the detailed population report (window 23, f_7179d)
8100765 Remake shell: the Map window's overlays (f_6f505 the small spider, f_6f5e1 the human and the mower)
ffffd01 Remake shell: Show Trails (0x10E toggles DS:2994); notes: the Map toolbar's command table
00e55cd Remake shell: message boxes (layouts 27 / 30) for the sim's message_box effects
378eae5 Remake shell: Select a Game (layout 2) at start-up and on F2
4f8ad0b Remake shell: the map tools' option palettes (layouts 12..17) and the Experimental menu (10 / 11)
0feb3c1 Remake shell: the tool palette (layout 9) and the map tools' drag loop (f_76f4a) in the Experimental game
086ce9d Remake shell: the scent overlay menu (layout 6), the Ant Info window (layout 29)
96f88c0 Remake shell: the yard window (layout 25, f_702f7) in place of the plain grid
d9d2388 Remake shell: the History window (layout 21)
c39c43c Remake shell: Behavior / Caste Control as the original's windows (layouts 18 / 19)
4ffeee8 Remake shell: the yellow ant's pop-up menu (layouts 7 / 8 / 32, f_67e93)
f66140d Remake shell: the Efficiency Score window (layout 24, f_71576); notes: STR# 1800
5eec643 Remake shell: the original's Edit and Map windows from their layouts (UiArt draws layouts 0 / 1)
```

2026-10-18 (the remake):
```
0b2ce94 Remake: the game's bitmap fonts in C# (BitmapFont, port of fonts.py); the shell's status lines use font 2
4d45215 Remake shell: speech balloons as text at the ants (STR# 1220..1260); keep the map window globals in step
9507d8a Remake README: the shell's controls as a table
f37d684 Remake shell: quick save / load (F5 / F9) in the original's .ANT format
6252f88 Remake shell: scent views (V cycles T:07BE)
6c88d83 Remake shell: the Ant Info tool (Ctrl+click), with the game's STR# 1100..1103 names
ab07e2d Remake shell: triangle clicks set the manual flags as the original's handlers f_07d07 / f_07ac1 do
cae930c Handoff: tidy the shell features note
c8d0c19 Remake shell: the Behavior / Caste triangles (P) on the ported Panels, auto / manual jobs (O)
d5e5e4a Remake shell: --ticks / --history for build checks; the History label follows its scale
7ee1b61 Remake shell: a simple History graph (G) from the sim's history rings, labelled with STR# 1050
037b97a Remake: sound effects from the player's SOUND archive (effect 'sound' n = resource n)
a10396a README for the repository: what the project is, the bring-your-own-files rule, layout and status
9e84ba1 Remake: the Map window's cell colours (f_6efd6) as an overview in the shell, click to scroll
600e559 Notes: f_71d95 indexes the rank titles (G:0328, STR# 1900) directly by rank
c0453db Remake shell: the game-over rating line; handoff notes on the shell and fuzzing
8606290 Remake shell: a simple yard map (Full Game) to move between patches, also when the yellow ant dies
7bc9a3a Remake: fuzz mode (random clicks, commands, tools, cheats over many games); define the one crash path
e983225 Remake shell: the yellow ant's commands on keys; map clicks follow the Exchange / Chase cursor modes and the spider
b965ce1 Remake: draw the spider (body bitmaps, legs and fangs from the ported f_04c44 / f_04666 programs)
a4eec41 Remake: the original's main-loop timing (speed T:07CC, delays T:07CE, pause G:047E)
74c0c0d Remake: read the game's STR# messages (SHARED / HCEGANT type 4) and show them in the shell
9e20448 Remake: the start-up state the simulation reads (G:0480, G:0FBA, G:0FFE, DS:1A2E, ...)
f6df340 Remake: data layer (archives, state image from SIMANT.EXE, map art and renderer) and a first Godot 4.6 C# shell
331eacc Remake: port cheats, debug commands, map tools, markers, speech balloons, panels and menu commands
b81f195 Remake: port the yellow ant, SimStep, new game, terrain, game flow and saved games
7438c61 Remake: port the nests, world (lions, caterpillar, spider, weather) and yard layer; all traces match
e642345 Remake: C# simulation library (Formica.Sim) and a trace replayer checked against the Python reference
```

Earlier:
```
b015a51 Notes: the map redraw (f_03de7) draws from the game's RNG when the patch is visible
532c7e0 Rendering: the spider overlay (f_03de7)
908541d Rendering: the surface uses sprite sheet 14, the nests 13 (f_02b43)
6267910 Rendering: decode the tile and sprite sheets; render views with the game's art
0d690ae Port saved games (.ANT): save (f_6c328) and load (f_6c1a0, f_6cf1a, f_6cf5b)
ea46cec Port the game flow: the rating (f_70fb0), game over (f_71d95), starting a game (f_725b6)
62484f3 Port the player events (f_75d01): the yellow ant's death and the takeover
73a8ea8 Port the Full Game's move between patches (f_01d48) and the house patches (f_7304b)
8f7f04f Port the new game (f_6b36b) and patch setup (f_6ae20); verified
(this session) Port the yard layer (sec8 f_68513); verified over 114 scenarios
b66ff09 Port the spider (f_0ce63 and helpers); verified over 37 scenarios
f7642c9 Port the caterpillar and wandering bugs (f_0b6cc, f_0ae4c); verified
ab29ecc Port ant lions (f_0b163 and helpers); verifier gains pre_once
2fbdda2 Port slow phases, history graph, advisor and weather; verified
d8e5d18 Port red nest ants to the reference sim, verified against the original
3c9b823 Port black nest ants to the reference sim, verified against the original
```
plus this handoff commit (frozen clock in the verifier, sec8 notes, this file).
