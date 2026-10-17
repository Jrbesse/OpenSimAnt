# Handoff: SimAnt reverse engineering and reference port

Snapshot of where things stand, written so a fresh Claude Code session can continue without re-reading the
old transcript. Last updated 2026-10-17 (late evening: cheats, debug commands, map tools).

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
python test_newgame.py; python test_newgame.py play; python test_events.py; python test_game.py; python test_savefile.py; python test_cheats.py; python test_tools.py; python test_debug.py; python test_markers.py; python test_balloons.py
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
| `player.py` | the yellow ant (also its death and the takeover, `player_event`): upkeep `f_7bf7e`, actions `f_7b7b8` (pathfinding to the cursor, picking up / dropping / eating, entering and leaving nests, fights), view-generic map accessors |

Player (yellow ant) interactions are routed to `st.player` hooks; `surface.NoPlayer` raises
`NotImplementedError` for the ones that change state, so a test fails loudly if it reaches unported code.

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
   Open:
   - colours 0x10.. in the map window (driver dither, DS:914C; drawn as a plain ramp);
   - the fonts (SHARED type 11, Mac FONT; id 0's header undecoded): no text is drawn yet;
   - the item fields +10 / +18 / +20 and the frame styles (named from their drawing routines only);
   - the UI tables 128 / 129 / 131 (129: 24 entries of 4 colour bytes);
   - the line algorithm of `f_16b58` (Bresenham assumed);
   - the other windows and the menus.)
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
10. Then the Godot remake (RECREATION_PLAN.md).

## Gotchas learned the hard way

- **Shell heredocs mangle backslashes and backticks** in this environment. Write code with the Write/Edit
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
