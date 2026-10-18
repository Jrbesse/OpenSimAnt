# Formica: the Godot remake

"Formica" is a working code name (the public release needs its own name; see `docs/ART_PLAN.md`). It is a
fan remake of a 1991 ant-colony simulator, built on a byte-exact port of the original's simulation. It ships
no original data: it reads the player's own copy of the game (SIMANT.EXE and the HCEGANT archives) at runtime.

## Layout

| Path | What |
|---|---|
| `src/Formica.Sim/` | The simulation, a C# port of `tools/ref/simant_ref` (plain .NET 8, no Godot). Same memory-mirroring `State`, same function names (PascalCase), one class per reference module. |
| `src/Formica.Data/` | Reading the player's files: the resource archives (LZSS), the starting State built from SIMANT.EXE, the map art (palette, tiles, sprites, recolouring) and the map renderer; `GameSession` (a game: new game, ticks, clock, effects queue). |
| `game/` | The Godot 4.6 C# project (`Formica.csproj`, `Main.tscn`, `Main.cs`). |
| `tests/Formica.Replay/` | Replays traces recorded from the Python reference on the C# port and compares memory byte for byte; `--smoke` plays games from SIMANT.EXE and writes PNGs. |
| `tests/Formica.Sim.Tests/` | xUnit: one test per trace file. |
| `build/` | Git-ignored: traces (`build/traces`), smoke PNGs. They hold game memory: never commit them. |

## How the port is checked

The Python reference was verified against the original running in an emulator. Its own tests are re-run with
every reference function wrapped (`tools/ref/record_traces.py`); each outermost call is recorded with its
arguments, the player hook class, the clock and the State before and after. The C# side replays each record
on its port (found by reflection: `surface.s_bored` → `Surface.SBored`) and compares the return value and all
150,160 bytes of State.

```
sh tools/ref/record_all.sh                      # record every test's traces (minutes; needs the emulator setup)
cd remake
dotnet run --project tests/Formica.Replay -c Release -- --quiet
dotnet test tests/Formica.Sim.Tests -c Release
dotnet run --project tests/Formica.Replay -c Release -- --smoke
```

At this commit all 25 trace files (about 225,000 calls, including 67,200 SimStep ticks) match.

## Running the game

Open `remake/game` in Godot 4.6 (.NET), or build with `dotnet build remake/game/Formica.csproj` and run
Godot with `--path remake/game`. The game looks for the original files in `--game-dir=<path>` (a user arg after
`--`), `FORMICA_GAME_DIR`, or the folders above the project. `-- --screenshot=out.png` saves the screen after
240 frames and quits; `--ticks=N` runs the game N ticks ahead first, `--history` opens the History graph.

The screen is built from the original's window layouts (`Formica.Data/Ui.cs` draws them with the player's own
bitmaps and fonts): the **Edit window** (the close-up map with its tool strip and health bars) and the **Map
window** (the whole map, the toolbar and the population report), plus the Behavior / Caste Control, History
and Efficiency Score windows and the yellow ant's pop-up menu. Drag a window by its caption; a click brings it
to the front. The status lines below the windows are the shell's own.

Mouse:

| Where | Action |
|---|---|
| Edit window map | left click: walk the yellow ant there (Shift: walk and act on the cell: pick up / drop); right click: walk there digging; Ctrl + click: Ant Info |
| on the yellow ant | press and hold: its menu (recruit, release, exchange; a queen: dig hole, start brood; the spider: chase, hunt); release on an entry |
| Edit tool strip | MAP (show / hide the Map window), ? (help overlays), Surface / Black / Red nest, go to the yellow ant / spider / queens, PAUSE, SCENT (cycle the scent views) |
| Map window | click the map to look there; toolbar: Yard (Full Game), the views, scent layers, Behavior / Caste Control, Center on Yellow, the Mystery Button, History, Efficiency Score, Ant Info |
| Behavior / Caste Control | click or drag in the triangle; Auto / Manual |
| History window | the series buttons (up to four at once) |

Keys:

| Input | Action |
|---|---|
| 1 / 2 / 3 | surface / black nest / red nest |
| Arrows, F | scroll; follow the yellow ant |
| Space, + / - | pause (G:047E); speed slow / medium / fast (T:07CC) |
| R, Shift+R | recruit 5 / 10 |
| E, Shift+E | release half / all |
| X | exchange: then click an ant (or the spider) to become it |
| A, H, B | alarm trail; dig a hole (a queen founds a nest); start brood |
| C, U, Shift+U | as the spider: chase (then click), hunt, lash out |
| P, O | Behavior and Caste Control windows; automatic / manual jobs (G:0378) |
| G, Tab, V | History window; Map window (front / hide); scent views (T:07BE) |
| F1, F2 | the help overlays; Select a Game (also shown at start-up) |
| Y, Esc | yard map in a Full Game (click a patch to move; also opens when another colony must be picked) |
| F5 / F9 | quick save / load (the original's .ANT format, in Godot's user:// folder) |
| S | sound effects on / off |
| N / M / K | new Quick Game / Full Game / Experimental game (tool palette: hold a tool for its options) |

Build checks: `-- --ticks=N --screenshot=out.png`, plus `--history`, `--panels`, `--efficiency`, `--popup`,
`--map-front`, `--help-overlay`, `--yard`, `--strat`, `--scent-menu`, `--ant-info`, `--select` to open those
windows first; `--full` / `--experimental` start that kind of game.

## Porting notes

- Python ints become `int`, 32-bit values `long`; `State` setters mask like the reference. Python `//` and
  `%` floor while C# truncates: the reference already uses C semantics (`_cdiv`, `_cmod`) where it matters,
  ported as `Bits.CDiv` / `CMod`; `Bits.FloorDiv` / `Mod` exist for Python semantics.
- Argument evaluation order matters (some effect arguments draw from the RNG); C# evaluates left to right
  like Python.
- `st.player` is `st.Hooks` (`IPlayer`); `NoPlayer` throws like `surface.NoPlayer`, `PlayerHooks` is
  `player.Hooks`. Effects are `Effect(st, name, args)` with the reference's names.
- Renamed: `newgame.new_game` → `NewGame.NewGameStart`, `balloons.balloons` → `Balloons.Run`, module `debug` →
  `DebugCommands`, `tools` → `MapTools`.
