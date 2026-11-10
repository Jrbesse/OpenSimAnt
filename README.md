# OpenSimAnt: an ant-colony simulator, reverse engineered and remade

[![Build](https://github.com/Jrbesse/SimAnt-Evolved/actions/workflows/build.yml/badge.svg)](https://github.com/Jrbesse/SimAnt-Evolved/actions/workflows/build.yml)

A fan project around a 1991 DOS ant-colony simulation game: its rules are reverse engineered from the
original executable, ported to a readable reference implementation, verified byte for byte against the
original running in an emulator, and rebuilt in Godot as **OpenSimAnt**, a faithful 1:1 remake. A modern game built
around the same core, **Formica**, comes after OpenSimAnt is finished.

This repository contains **no original game data**. Every tool and the remake read the player's own copy
of the game (SIMANT.EXE and its .DAT / .NDX archives) at runtime. Nothing extracted from those files is
committed. This is an unofficial fan project; it is not affiliated with or endorsed by the original
publisher.

## What is here

| Path | What |
|---|---|
| `docs/` | `ROADMAP.md` (what is left before version 1), `SIM_NOTES.md` (the decoded rules, memory layout and addresses), `FILE_FORMATS.md` (archives, bitmaps, fonts, layouts, saves), `RECREATION_PLAN.md`, `ART_PLAN.md` (how to make a clean-room art pack), `NIGHTLY.md` (how the automated nightly sessions and the PR loop work), `PLAYTEST.md`, `HANDOFF.md` (status and next steps). |
| `tools/` | Python tools that read the original files: archive extraction, bitmaps, tiles, fonts, window layouts. |
| `tools/re/` | Reverse-engineering tooling: a flat memory image of the executable, an annotated disassembler, a Ghidra wrapper, and a Unicorn-based emulator of the game. |
| `tools/ref/` | `simant_ref`, the Python reference port of the whole simulation, and its differential tests against the emulator. |
| `remake/` | The remake: a C# (.NET 8) port of the reference (`OpenSimAnt.Sim`), the data layer (`OpenSimAnt.Data`), a Godot 4.6 project (`game/`) and the tests that replay the reference's recorded calls on the port. See `remake/README.md`. |

## Status

- The simulation is completely ported and verified: every tick of the game (both colonies, nests, the
  yellow ant, the spider, ant lions, weather, the yard and the house, new games, saved games, cheats, map
  tools, menu commands) matches the original byte for byte in the tests.
- The C# port matches the Python reference on every recorded call (about 236,000), and long scripted games
  (200,000 ticks) stay identical to the original.
- The Godot remake is complete with the player's own files: every window, menu, panel, the yard, the
  SimAntipedia, the tutorial, sound and music, compared screen by screen with the original.
- **The clean-room asset pack is complete** (810 assets: art, layouts, fonts, text, sound effects and
  music), made by makers who worked from written specs and never saw the originals. The release
  workflow builds the pack, plays six screens on it with no original files present, and ships it in
  every package. What is left before version 1 -- the similarity review, and the release itself
  (licence, name review, player README) -- is listed in [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Using it

You don't need the original game any more. Build the remake's own assets and start it on them:

```
python tools/clean_pack/build.py                     # the open asset pack, from remake/game/assets/clean/src
cd remake && dotnet build game/OpenSimAnt.csproj     # then open remake/game in Godot 4.6 (.NET) and run
```

The game starts on a launcher: "Open assets" (the pack just built, no original files needed) or
"Original look". If you own the DOS version and want the original's look, put its files in the
repository root (they are git-ignored), or pick the folder on that screen; `--clean` and `--original`
skip the launcher. `python -I tools/extract.py` browses the art, text and sounds of your own copy in
`extracted/`.

Test builds for Windows, macOS and Linux (no Godot or .NET needed) come from tagged releases; see "Test builds for players"
in `remake/README.md`. Each package carries the pack, so it plays with no original files at all; the
first screen offers the open assets or, if you have them, your own copy of the original files.

The verification setup (emulator snapshots, traces) is described in `docs/HANDOFF.md` and
`remake/README.md`.
