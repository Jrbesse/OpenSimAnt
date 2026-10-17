# Handoff: SimAnt reverse engineering and reference port

Snapshot of where things stand, written so a fresh Claude Code session can continue without re-reading the
old transcript. Last updated 2026-10-17.

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
python test_newgame.py; python test_newgame.py play; python test_events.py; python test_game.py; python test_savefile.py
```

All of these printed ALL OK at this handoff (terrain prints "50/50 seeds identical").

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
   no planar VGA). Open: which sprite sheet each video mode uses (`f_028b6`; ids 15..20), the
   overview map window, the yard map, the other windows, the menus.)
9. Then the Godot remake (RECREATION_PLAN.md).

## Gotchas learned the hard way

- **Shell heredocs mangle backslashes and backticks** in this environment. Write code with the Write/Edit
  tools, or put a script in a file and run it. Never generate source through `cat <<EOF`.
- Ghidra pseudo-C is often wrong about **segments** (G vs T vs DS) and garbles jump tables. Always confirm
  with `adis.py`, which annotates `es=` segments. Segments: DGROUP/DS 0x55b3, SIM 0x3e1d, G 0x50f6,
  T 0x3d57, red trail map at 0x4da7:0.
- Overlay calls go through vector thunks (for example `f_2f7da` → `f_7a69d`); `decomp.py <thunk>` shows the
  target.
- Unicorn harness: SS must equal DS; `call_lin` returns AX only.
- C semantics matter: signed division and remainder truncate toward zero (`colony._cdiv`, `world._cmod`),
  16-bit wraparound (`s16`), and the short-circuit order decides which `Rand` calls happen.
- Some original code reads uninitialised locals in unreachable states; ports raise NotImplementedError
  there rather than guess.

## Commit log since the last summary

```
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
