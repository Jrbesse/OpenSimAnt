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
240 frames and quits.

Controls (first shell): left click walks the yellow ant there (Shift: walk and act on the cell, picking up /
dropping), right click digs its way there, 1 / 2 / 3 surface / black nest / red nest, arrows scroll, F follows
the yellow ant, Space pauses (G:047E), + / - speed (slow / medium / fast, as the original's T:07CC), N a new Quick Game, M a new Full Game.

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
