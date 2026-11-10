---
layout: default
title: Reference implementation
permalink: /reference/
---

# The reverse-engineered reference

`simant_ref` is a line-by-line Python translation of the *SimAnt* simulation, written against the disassembly and
verified routine by routine against the original running in emulation. Its purpose in this project is to be the
readable specification the C# remake is ported from. Its purpose here is also to be **usable by anyone**: every
module below is published in full, with the addresses it came from and the reasons it is shaped the way it is.

**Download the whole package:** [`simant_ref.zip`]({{ site.baseurl }}/assets/reference/simant_ref.zip) —
27 files, 8833 lines, MIT licence.

## What it needs from you

The reference reads the original's constant tables and starting state out of the executable at runtime. Nothing
extracted from `SIMANT.EXE` is in this repository or on this site. To run any of it:

```bash
python tools/re/build_flat.py   # from tools/re; builds flat.bin from your SIMANT.EXE
cd tools/ref && python test_sim.py 3000
```

Then `state.State()` loads `tools/re/build/flat.bin`, and the differential tests (`test_*.py`) check a module
against the emulator's snapshots. Without the original files, the source is still readable — the docstrings carry
the flat address of every routine — but it will not boot.

## How the port is verified

1. **Emulator.** `tools/re/emu.py` runs `SIMANT.EXE` in Unicorn, plays a seeded Quick Game, and caches six
   snapshots (ticks 0, 300, 900, 1500, 2200, 3000). A ported routine is run against a snapshot beside the original
   routine and all 150,160 bytes of state are compared.
2. **Reference.** Verified rules become the cheap oracle for the rest of the port.
3. **Replay.** Every outermost reference call is recorded (arguments, clock, state before and after) and replayed
   against the C# port by reflection.

## The machine underneath

- **[`state.py`]({{ site.baseurl }}/reference/state/) — The memory mirror.** One bytearray that is the 1991 program's address space. *(130 lines)*
- **[`rng.py`]({{ site.baseurl }}/reference/rng/) — The two random number generators.** An LFSR and Microsoft C's rand(), both draw-for-draw. *(53 lines)*
- **[`tables.py`]({{ site.baseurl }}/reference/tables/) — The constant tables.** The gameplay numbers, read from your executable at runtime. *(40 lines)*
- **[`sim.py`]({{ site.baseurl }}/reference/sim/) — SimStep — one game tick.** The original's tick order, preserved exactly. *(50 lines)*
- **[`savefile.py`]({{ site.baseurl }}/reference/savefile/) — Saved games (.ANT).** 307 blocks, 48,386 bytes, in the original's order. *(97 lines)*

## The surface world

- **[`terrain.py`]({{ site.baseurl }}/reference/terrain/) — Surface terrain generation.** The yard patch: rocks, pits, the house, and the layout solver. *(490 lines)*
- **[`movement.py`]({{ site.baseurl }}/reference/movement/) — Surface movement and steering.** Walking, turning, edge avoidance, and the direction heuristics. *(271 lines)*
- **[`pheromones.py`]({{ site.baseurl }}/reference/pheromones/) — Pheromone maps.** 64 × 32 cells, one per 2 × 2 tiles, with four decay curves. *(115 lines)*
- **[`surface.py`]({{ site.baseurl }}/reference/surface/) — Surface ants.** The dispatcher and the twenty state handlers. *(762 lines)*
- **[`world.py`]({{ site.baseurl }}/reference/world/) — Weather, predators and the slow phases.** Rain, the spider, the caterpillar, ant lions, the history graph. *(913 lines)*
- **[`yard.py`]({{ site.baseurl }}/reference/yard/) — The yard layer.** 191 other patches, the human, the mower, the dog, the bird and the rain. *(772 lines)*

## The colonies and the game

- **[`colony.py`]({{ site.baseurl }}/reference/colony/) — Colony bookkeeping and policy.** Health, census, priorities, caste choice, the advisor. *(306 lines)*
- **[`newgame.py`]({{ site.baseurl }}/reference/newgame/) — New game and patch setup.** A fresh yard, two colonies, the yellow ant, every counter. *(497 lines)*
- **[`nestgrid.py`]({{ site.baseurl }}/reference/nestgrid/) — Nest grid helpers.** Digging, dirt edges, exit fields, the nest ant lists. *(144 lines)*
- **[`nest.py`]({{ site.baseurl }}/reference/nest/) — Black nest ants.** The nest tick, state handlers, digging, brood and the queen. *(821 lines)*
- **[`red_nest.py`]({{ site.baseurl }}/reference/red-nest/) — Red nest ants.** A separate copy of the nest AI, with its own rules. *(505 lines)*

## The player and the interface

- **[`player.py`]({{ site.baseurl }}/reference/player/) — The player (the yellow ant).** Upkeep, actions, pathing, and the map accessors they use. *(1478 lines)*
- **[`commands.py`]({{ site.baseurl }}/reference/commands/) — The yellow ant's menu commands.** Recruit, release, exchange, alarm, dig, start brood. *(282 lines)*
- **[`panels.py`]({{ site.baseurl }}/reference/panels/) — The behaviour and caste triangles.** Where the marker sits, and what a click means. *(77 lines)*
- **[`markers.py`]({{ site.baseurl }}/reference/markers/) — The map's event markers.** Where the last hatch, fight, egg and rest happened. *(49 lines)*
- **[`balloons.py`]({{ site.baseurl }}/reference/balloons/) — Speech balloons.** The ants' remarks, timed off the real-time clock. *(62 lines)*
- **[`tutorial.py`]({{ site.baseurl }}/reference/tutorial/) — The tutorial.** 56 steps, each with a box and a check. *(184 lines)*
- **[`tools.py`]({{ site.baseurl }}/reference/tools/) — The map tools.** Rocks, dig, ants, food, pheromone, insecticide. *(335 lines)*
- **[`cheats.py`]({{ site.baseurl }}/reference/cheats/) — The cheat codes.** Typed keys, NOT-ed into a match buffer. *(126 lines)*
- **[`debug.py`]({{ site.baseurl }}/reference/debug/) — The hidden debug commands.** Add ants, kill ants, clear food, and a random action. *(126 lines)*
- **[`game.py`]({{ site.baseurl }}/reference/game/) — Game flow, rating and game over.** Starting a game, ending one, and the score. *(143 lines)*

## Reverse-engineering toolchain

The tools that turn a 1991 executable into something readable and testable. They all need your own copy of the game.

- **[`adis.py`]({{ site.baseurl }}/reference/adis/)** — Annotated disassembly of a function in build/flat.bin.
- **[`build_flat.py`]({{ site.baseurl }}/reference/build-flat/)** — Build a flat real-mode memory image of SIMANT.EXE for analysis and emulation.
- **[`callgraph.py`]({{ site.baseurl }}/reference/callgraph/)** — Direct call graph (near e8 + far 9a) over resident code and overlays. Writes build/calls.tsv (caller_func, site, target).
- **[`compare_screens.py`]({{ site.baseurl }}/reference/compare-screens/)** — Compare the remake's screens with the original's (captured by screens.py) pixel for pixel.
- **[`decomp.py`]({{ site.baseurl }}/reference/decomp/)** — Print Ghidra's pseudo-C for routines, with called functions renamed from symbols.json.
- **[`emu.py`]({{ site.baseurl }}/reference/emu/)** — Run original SIMANT.EXE code inside Unicorn (16-bit real mode) on build/flat.bin.
- **[`funcstarts.py`]({{ site.baseurl }}/reference/funcstarts/)** — Function entry detection for build/flat.bin (MSC 6 prologues, after build_flat.py's _chkstk patch).
- **[`mz.py`]({{ site.baseurl }}/reference/mz/)** — Helpers for reverse-engineering SIMANT.EXE (16-bit MZ, load base segment 0).
- **[`opl_capture.py`]({{ site.baseurl }}/reference/opl-capture/)** — Capture the original's AdLib (OPL2) register writes in the emulator.
- **[`pngdiff.py`]({{ site.baseurl }}/reference/pngdiff/)** — Compare two 640 x 480 screenshots (the original's from screens.py, the remake's from its --screenshot flag).
- **[`polylines.py`]({{ site.baseurl }}/reference/polylines/)** — Extract the spider's leg drawings: the per-heading move-to / line-to programs of f_04c44 and f_04666.
- **[`render_state.py`]({{ site.baseurl }}/reference/render-state/)** — Run the original simulation for N ticks and render the sim state to PNGs (debug colours, not game art).
- **[`run_quickgame.py`]({{ site.baseurl }}/reference/run-quickgame/)** — Boot the original game headless, start a Quick Game and run the real simulation for N ticks.
- **[`screens.py`]({{ site.baseurl }}/reference/screens/)** — Capture the original's own screens: boot SIMANT.EXE in the emulator with the planar VGA model (vga.py) and
- **[`segmap.py`]({{ site.baseurl }}/reference/segmap/)** — Map which functions read/write which offsets of a far data segment (default: 0x3e1d sim state).
- **[`trace_crash.py`]({{ site.baseurl }}/reference/trace-crash/)** — Run a Quick Game in the emulator and, when emulation crashes, print the functions that led there.
- **[`vga.py`]({{ site.baseurl }}/reference/vga/)** — A planar VGA (mode 12h, 640 x 480 x 16) for the Unicorn emulator, so the original's own drawing can be captured.

## Differential tests

Each module's test boots the original in the emulator and compares the port's output against it. These need `flat.bin` and the game; see `verify.py` for the harness they share.

- **[`boot_diff.py`]({{ site.baseurl }}/reference/boot-diff/)** — What the original's start-up changes in the simulation's memory before the first new game.
- **[`debug_player.py`]({{ site.baseurl }}/reference/debug-player/)** — Debug helper: python debug_player.py <check label> [snapshot index].
- **[`debug_sim.py`]({{ site.baseurl }}/reference/debug-sim/)** — Debug helper: python debug_sim.py [snapshot index] [max ticks]
- **[`deps_ui.py`]({{ site.baseurl }}/reference/deps-ui/)** — Which bytes of SIMANT.EXE's data image the remake's screens read (ROADMAP A2).
- **[`gen_game_tables.py`]({{ site.baseurl }}/reference/gen-game-tables/)** — Writes remake/src/OpenSimAnt.Sim/GameTables.cs: the numbers the game reads from SIMANT.EXE's data, as named tables.
- **[`gen_spider_legs_cs.py`]({{ site.baseurl }}/reference/gen-spider-legs-cs/)** — Write remake/src/OpenSimAnt.Data/SpiderLegs.cs: the C# port of the spider's leg and fang drawing routines
- **[`linecov.py`]({{ site.baseurl }}/reference/linecov/)** — Minimal line coverage for a port module: python linecov.py <module_file.py> <test_script.py> [args...]
- **[`longrun.py`]({{ site.baseurl }}/reference/longrun/)** — Long-run differential check: the original (in the emulator) and the Python reference play the same long game
- **[`record_traces.py`]({{ site.baseurl }}/reference/record-traces/)** — Record the reference port's calls as traces for the C# remake's tests.
- **[`render_view.py`]({{ site.baseurl }}/reference/render-view/)** — Render the game state with the game's own graphics, the way the original draws its map windows.
- **[`rng_diff.py`]({{ site.baseurl }}/reference/rng-diff/)** — Find where the reference port and the original diverge, by comparing the sequence of RNG *calls*
- **[`test_balloons.py`]({{ site.baseurl }}/reference/test-balloons/)** — Verify the speech balloons (f_06a4d via f_07128) against the original, with the drawing f_0696a stubbed.
- **[`test_cheats.py`]({{ site.baseurl }}/reference/test-cheats/)** — Verify the cheat codes (f_6a920) against the original: every code typed key by key from every snapshot,
- **[`test_colony.py`]({{ site.baseurl }}/reference/test-colony/)** — Verify the colony module against the original (python test_colony.py).
- **[`test_commands.py`]({{ site.baseurl }}/reference/test-commands/)** — Verify the yellow ant's menu commands (f_76cb9) against the original.
- **[`test_debug.py`]({{ site.baseurl }}/reference/test-debug/)** — Verify the hidden debug commands against the original: add ants (f_015be), kill ants (f_0161f), clear
- **[`test_events.py`]({{ site.baseurl }}/reference/test-events/)** — Verify the player events against the original: the yellow ant's death and the takeover of another ant
- **[`test_experimental.py`]({{ site.baseurl }}/reference/test-experimental/)** — Verify the State changes of the Experimental menu handlers f_67010 / f_67a24 (ROADMAP B5).
- **[`test_game.py`]({{ site.baseurl }}/reference/test-game/)** — Verify the game flow against the original: the rating (f_70fb0), the game-over screen (f_71d95) and
- **[`test_markers.py`]({{ site.baseurl }}/reference/test-markers/)** — Verify the event-marker recorders (f_0678a, f_06802, f_0687a, f_068f2, with the on-screen test f_06725)
- **[`test_movement.py`]({{ site.baseurl }}/reference/test-movement/)** — Verify the surface movement helpers against the original (python test_movement.py).
- **[`test_nest.py`]({{ site.baseurl }}/reference/test-nest/)** — Verify the nest ants against the original.
- **[`test_newgame.py`]({{ site.baseurl }}/reference/test-newgame/)** — Verify the new game (f_6b36b) and the patch setup (f_6ae20) against the original.
- **[`test_panels.py`]({{ site.baseurl }}/reference/test-panels/)** — Verify the Behavior / Caste Control triangles against the original: the geometry (f_07980), weights to
- **[`test_pheromones.py`]({{ site.baseurl }}/reference/test-pheromones/)** — Verify the pheromone module against the original (python test_pheromones.py).
- **[`test_player.py`]({{ site.baseurl }}/reference/test-player/)** — Verify the player (yellow ant) routines against the original (python test_player.py [name-substring ...]).
- **[`test_savefile.py`]({{ site.baseurl }}/reference/test-savefile/)** — Verify loading saved games against the original (python test_savefile.py).
- **[`test_sim.py`]({{ site.baseurl }}/reference/test-sim/)** — Full-tick check: run SimStep (f_0894e) of the original and the port side by side from every snapshot
- **[`test_surface.py`]({{ site.baseurl }}/reference/test-surface/)** — Verify the surface-ant handlers and dispatcher against the original (python test_surface.py [state ...]).
- **[`test_terrain.py`]({{ site.baseurl }}/reference/test-terrain/)** — Differential test: reference terrain generator vs. the original f_73c33 running in the emulator.
- **[`test_tools.py`]({{ site.baseurl }}/reference/test-tools/)** — Verify the add-ants routines f_6be50 (black) / f_6bf06 (red) and the map tools (f_770f6: rocks, dig, ants,
- **[`test_tutorial.py`]({{ site.baseurl }}/reference/test-tutorial/)** — Verify the tutorial (f_0e425 with its steps f_0e4e4 / f_0e93e) against the original: every step shown and
- **[`test_world.py`]({{ site.baseurl }}/reference/test-world/)** — Verify the SimStep world updates against the original (python test_world.py [name-substring ...]).
- **[`test_yard.py`]({{ site.baseurl }}/reference/test-yard/)** — Verify the yard layer (sec8 f_68513) against the original (python test_yard.py [name-substring ...]).
- **[`verify.py`]({{ site.baseurl }}/reference/verify/)** — Differential verification of ported routines against the original running in the emulator.

## Asset tools

Readers for the original's archives, bitmaps, tiles, fonts, layouts and saves.

- **[`asset_inventory.py`]({{ site.baseurl }}/reference/asset-inventory/)** — Measure the user's own extracted SimAnt assets and write a metadata-only inventory: sizes, frame counts,
- **[`bitmaps.py`]({{ site.baseurl }}/reference/bitmaps/)** — Decode SimAnt type-2 bitmap resources.
- **[`contact_sheet.py`]({{ site.baseurl }}/reference/contact-sheet/)** — Tile all extracted bitmaps of an archive into one PNG (ordered by id) and print each tile's position.
- **[`extract.py`]({{ site.baseurl }}/reference/extract/)** — Extract every resource from the SimAnt DOS archives into ../extracted.
- **[`fonts.py`]({{ site.baseurl }}/reference/fonts/)** — Decode SHARED type 11 resources: the game's bitmap fonts.
- **[`gen_devlog_reference.py`]({{ site.baseurl }}/reference/gen-devlog-reference/)** — Generate the OpenSimAnt reference pages under docs/reference/ from tools/ref/simant_ref/.
- **[`layouts.py`]({{ site.baseurl }}/reference/layouts/)** — Decode HCEGANT type 0 resources: window / dialog layouts.
- **[`png.py`]({{ site.baseurl }}/reference/png/)** — Minimal dependency-free RGBA PNG writer.
- **[`render_windows.py`]({{ site.baseurl }}/reference/render-windows/)** — Render every window layout (HCEGANT type 0) to a PNG: pictures at their item rectangles, other items as
- **[`simres.py`]({{ site.baseurl }}/reference/simres/)** — SimAnt (DOS, Maxis 1991) resource archive reader.
- **[`tiles.py`]({{ site.baseurl }}/reference/tiles/)** — Decode the EGA tile sheets (HCEGANT type 9 ids 9 house, 10 yard; 13..20 sprites) to PNG contact sheets.

