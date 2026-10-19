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
dotnet run --project tests/Formica.Replay -c Release -- --songs   # every song and effect as WAV in build/songs (to listen)
python tools/re/opl_capture.py record           # (from the repo root) the original driver's OPL2 streams → build/traces/opl
```

At this commit all 25 trace files (about 225,000 calls, including 67,200 SimStep ticks) match.

## Running the game

Open `remake/game` in Godot 4.6 (.NET), or build with `dotnet build remake/game/Formica.csproj` and run
Godot with `--path remake/game`. The game looks for the original files in `--game-dir=<path>` (a user arg after
`--`), `FORMICA_GAME_DIR`, the folder picked on the setup screen (kept in `user://settings.cfg`), the
executable's folder and up to two levels inside it, or the folders above the project / the executable. With
none of those it shows the setup screen: a button opening the system's folder picker. `-- --screenshot=out.png` saves the screen after
240 frames and quits; `--ticks=N` runs the game N ticks ahead first, `--history` opens the History graph.

The screen is built from the original's window layouts (`Formica.Data/Ui.cs` draws them with the player's own
bitmaps and fonts): the **Edit window** (the close-up map with its tool strip and health bars) and the **Map
window** (the whole map, the toolbar and the population report), plus the Behavior / Caste Control, History
and Efficiency Score windows and the yellow ant's pop-up menu. Drag a window by its caption; a click brings it
to the front. The menu bar across the top is the original's (SHARED type 6). The game's timed messages (the advisor,
refusals, the yard's notices) appear centred at the top of the Edit window's map, as `f_15e2c` / `f_038a6` show
them; message boxes follow Options > Events. The status lines below the windows are the shell's own.

Mouse:

| Where | Action |
|---|---|
| Menu bar (top) | the original's pull-down menus (SHARED type 6): File, Window, View, Options, Speed. Press on a title and release on an item, or click a title, then an item; ► marks the speed and the Options that are on |
| Edit window map | as the original's f_74fe0: click: walk there; double click (or right click, or Shift+click): act: pick up / drop / eat on the surface, dig or pick up / drop in a nest, meet or fight the ant clicked; press and hold on an ant: Ant Info (Ctrl+click too) |
| on the yellow ant | quick click: recentre on it; press and hold: its menu (recruit, release, exchange; a queen: dig hole, start brood; the spider: chase, hunt); release on an entry |
| Edit tool strip | MAP (show / hide the Map window), ? (help overlays), Surface / Black / Red nest, go to the yellow ant / spider / queens, PAUSE, SCENT (cycle the scent views) |
| Map window | press (and drag) on the map to look there, right click to send the yellow ant there to act (f_6726a); toolbar: Yard (Full Game), the views, scent layers, Behavior / Caste Control, Center on Yellow, the Mystery Button, History, Efficiency Score, Ant Info (the SimAntipedia: click a picture's labels or the BACK / PREVIOUS / TOP bar to change cards, hold the button on a bold word for its definition; Escape or a click outside closes it) |
| Behavior / Caste Control | click or drag in the triangle; Auto / Manual |
| History window | the series buttons (up to four at once) |
| Experimental button (Map toolbar, Edit strip) | Quick Game: switch to Experimental; Experimental: the tool palette (hold a tool for its options; Start Game returns to a Quick Game), then press / drag on the Edit map |
| Population report (Map window) | hold: the detailed report per caste |

Keys:

| Input | Action |
|---|---|
| **The original's keys** (f_74386's table, f_76aeb; the SimAntipedia's "Keyboard Shortcuts" card) | |
| 1 / 2 | recruit 5 / 10 (a queen: dig hole / start brood; the spider: chase / hunt) |
| 3 / 4, X, 0 | release half / all; exchange (then click an ant or the spider); alarm trail |
| Backspace, Shift+Backspace | stop the yellow ant's walk (else recentre on it); follow it |
| Alt+F / W / V / O / S, F2..F6 | open a menu (File, Window, View, Options, Speed); then Up / Down, Left / Right, a letter, Enter / Space, Esc |
| Shift+0, Shift+1 / 2 / 3 / 4 | pause (G:047E); speed Slow / Normal / Fast / Ultra (T:07CC) |
| Ctrl+N, Ctrl+L, Ctrl+S / A, Ctrl+Q / X | Select a Game; load, save (the file dialog: Godot's user:// folder, type a name to save, click / double-click a file to load); quit (asks to save first) |
| Ctrl+E, Ctrl+M, Ctrl+B, Ctrl+C, Ctrl+T, Ctrl+Y | Edit window; Map window; Behavior / Caste Control; Efficiency Score; the yard window |
| Ctrl+H, Ctrl+I | History; Info (the SimAntipedia) |
| Ctrl+4 / 5 / 6 / 7 | back to the patch; the yard window as House / Strategic / Graphic view |
| Ctrl+8 / 9 / 0 | Surface / Black Nest / Red Nest |
| Alt+2 | recruit all |
| Space or Insert, Delete | the left / right mouse button at the pointer (the original's keyboard mouse, f_2024b); pause with the PAUSE button or Speed > Pause |
| Ctrl + arrows / keypad (Home / PgUp / End / PgDn diagonals), the mouse at the screen's edge | scroll the Edit window while held (f_74140, f_0113e) |
| Ctrl+G / J / K | Options: AutoTrack / Music (the songs, through the original's driver on an emulated OPL2: see "Sound" below) / Sound Effects (T:07A8 / T:07AA / T:07AC); Events, Messages and Silly (speech balloons, off at start-up as in the original) are in the menu |
| Tab | Map window (front / hide) |
| **The shell's own keys** | |
| Ctrl+1 / 2 / 3 | surface / black nest / red nest |
| Arrows, F | scroll; follow the yellow ant |
| + / - | speed |
| R, Shift+R, E, Shift+E, A, H, B | recruit 5 / 10, release half / all, alarm trail, dig a hole, start brood |
| C, U, Shift+U | as the spider: chase (then click), hunt, lash out |
| P, O | Behavior and Caste Control windows; automatic / manual jobs (G:0378) |
| G, V | History window; scent views (T:07BE) |
| F1 | the help overlays (File > New is Select a Game, File > About the about box) |
| Y, Esc | yard map in a Full Game (double-click a patch to move; also opens when another colony must be picked: click one with a black colony); Esc also closes the SimAntipedia |
| F8 / F9 | quick save / load (the original's .ANT format, in Godot's user:// folder) |
| S | sound effects on / off (the shell's mute) |
| N / M / K | new Quick Game / Full Game / Experimental game |

Build checks: `-- --ticks=N --screenshot=out.png`, plus `--history`, `--panels`, `--efficiency`, `--popup`,
`--map-front`, `--map-content=n` (the Map window shows T:07C8 = n: 4..8 the scent maps), `--series=a,b` (History buttons pressed), `--help-overlay`, `--yard`, `--strat`, `--scent-menu`, `--ant-info`, `--select`, `--report`,
`--exp-menu`, `--trails`, `--spider-view` (the surface around the spider), `--frames=N` (screenshot after N frames), `--tutorial[=step]` (the Tutorial, at that step), `--silly` (Options > Silly on: speech balloons), `--menu=m[,item]` (a menu open, an item highlighted), `--message=<STR# id>`, `--antipedia[=card[,x,y]]` (a card, the button held at x, y), `--game-over`, `--load-dialog`, `--save-dialog` to open those
windows first; `--full` / `--experimental` start that kind of game.

## Sound

The original's own sound, in its Sound Blaster mode (docs/SIM_NOTES.md "The sound driver"):

| File | What |
|---|---|
| `Formica.Data/SoundBank.cs` | The driver's tables from SIMANT.EXE: 56 instruments (FM records or pitched samples), the effect table, the mixing and tick rates. |
| `Formica.Data/SoundDriver.cs` | A port of the driver: the MIDI sequencer, the static channel map, the voices (priority, stealing), FM note on / off / patch as OPL2 register writes, the sample device behind an interface. `OplTraceTests` replays the original's register streams (`tools/re/opl_capture.py record`: 33 songs, 56 effects, effects in a row, a song with effects): every write and every wait match. |
| `Formica.Data/Opl2.cs` | The YM3812 parts of ymfm (Aaron Giles, BSD-3-Clause, licence in the file and in `dist/THIRD_PARTY_NOTICES.txt`). |
| `Formica.Data/SoundMixer.cs` | The driver's 5575.6 Hz handler (two sample voices through its volume tables into the DAC, a music tick every 16th), the OPL2 resampled. `OplTraceTests.DacMatches` replays the original handler's DAC bytes tick by tick. The shell renders it into one `AudioStreamGenerator`. |

Guessed, not measured: the balance between the Sound Blaster's DAC and its FM (`SoundMixer.SampleGain`).

## Test builds for players

`game/export_presets.cfg` has a "Windows Desktop" preset (x86_64, the PCK embedded in the exe; the .NET
runtime goes in `data_Formica_windows_x86_64/`, so players install nothing). Export locally with

```
Godot_v4.6.2-stable_mono_win64_console.exe --headless --path remake/game --export-release "Windows Desktop" ../build/export/windows/Formica.exe
```

`.github/workflows/release.yml` does the same on GitHub: pushing a tag `v*` exports, zips the build with
`dist/HOW_TO_PLAY.txt` (the player's instructions) and attaches the zip to a pre-release; running it by hand
keeps the zip as a workflow artifact only. No original data goes in the zip: on first run the game asks for
the player's own copy (the setup screen above).

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
