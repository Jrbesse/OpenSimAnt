# An ant-colony simulator, reverse engineered and remade

[![Build](https://github.com/Jrbesse/SimAnt-Evolved/actions/workflows/build.yml/badge.svg)](https://github.com/Jrbesse/SimAnt-Evolved/actions/workflows/build.yml)

A fan project around a 1991 DOS ant-colony simulation game: its rules are reverse engineered from the
original executable, ported to a readable reference implementation, verified byte for byte against the
original running in an emulator, and rebuilt as a modern game in Godot.

This repository contains **no original game data**. Every tool and the remake read the player's own copy
of the game (SIMANT.EXE and its .DAT / .NDX archives) at runtime. Nothing extracted from those files is
committed. This is an unofficial fan project; it is not affiliated with or endorsed by the original
publisher, and the remake's public name is still to be chosen.

## What is here

| Path | What |
|---|---|
| `docs/` | `SIM_NOTES.md` (the decoded rules, memory layout and addresses), `FILE_FORMATS.md` (archives, bitmaps, fonts, layouts, saves), `RECREATION_PLAN.md`, `ART_PLAN.md` (how to make a clean-room art pack), `HANDOFF.md` (status and next steps). |
| `tools/` | Python tools that read the original files: archive extraction, bitmaps, tiles, fonts, window layouts. |
| `tools/re/` | Reverse-engineering tooling: a flat memory image of the executable, an annotated disassembler, a Ghidra wrapper, and a Unicorn-based emulator of the game. |
| `tools/ref/` | `simant_ref`, the Python reference port of the whole simulation, and its differential tests against the emulator. |
| `remake/` | The remake: a C# (.NET 8) port of the reference (`Formica.Sim`), the data layer (`Formica.Data`), a Godot 4.6 project (`game/`) and the tests that replay the reference's recorded calls on the port. See `remake/README.md`. |

## Status

- The simulation is completely ported and verified: every tick of the game (both colonies, nests, the
  yellow ant, the spider, ant lions, weather, the yard and the house, new games, saved games, cheats, map
  tools, menu commands) matches the original byte for byte in the tests.
- The C# port matches the Python reference on every recorded call (about 225,000).
- The Godot remake is an early shell: it plays a game from the player's files, draws the map windows with
  the original's art, and takes mouse and keyboard commands. The original's screens (menus, panels, yard
  map, history graph, sounds) are next.

## Using it

You need your own copy of the original DOS game. Put its files in the repository root (they are
git-ignored), then:

```
python -I tools/extract.py                          # optional: browse the art, text and sounds in extracted/
cd remake && dotnet build game/Formica.csproj       # then open remake/game in Godot 4.6 (.NET) and run
```

Test builds for Windows (no Godot or .NET needed) come from tagged releases; see "Test builds for players"
in `remake/README.md`. On first run the game asks for the folder with your copy of the original files.

The verification setup (emulator snapshots, traces) is described in `docs/HANDOFF.md` and
`remake/README.md`.
