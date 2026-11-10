# OpenSimAnt: an ant-colony simulator, reverse engineered and remade

[![Build](https://github.com/Jrbesse/SimAnt-Evolved/actions/workflows/build.yml/badge.svg)](https://github.com/Jrbesse/SimAnt-Evolved/actions/workflows/build.yml)

A fan project around a 1991 DOS ant-colony simulation game: its rules are reverse engineered from the
original executable, ported to a readable reference implementation, verified byte for byte against the
original running in an emulator, and rebuilt in Godot as **OpenSimAnt**, a faithful 1:1 remake. A modern game built
around the same core, **Formica**, comes after OpenSimAnt is finished.

This repository contains **no original game data**. Every tool and the remake read the player's own copy
of the game (SIMANT.EXE and its .DAT / .NDX archives) at runtime. Nothing extracted from those files is
committed. OpenSimAnt is an unofficial reimplementation of SimAnt (Maxis, 1991). It is not affiliated
with, endorsed by, or sponsored by Electronic Arts. It ships no original Maxis assets.

The **code** is MIT ([`LICENSE`](LICENSE)); the **clean asset pack** — art, layouts, fonts, text, sound and
music — is CC BY 4.0 ([`LICENSE-ASSETS`](LICENSE-ASSETS), which states the attribution line a reuser has to
ship). The two licences do not overlap; see [Licence](#licence) below.

## What is here

| Path | What |
|---|---|
| `docs/` | `ROADMAP.md` (what is left before version 1), `SIM_NOTES.md` (the decoded rules, memory layout and addresses), `FILE_FORMATS.md` (archives, bitmaps, fonts, layouts, saves), `RECREATION_PLAN.md`, `ART_PLAN.md` (how to make a clean-room art pack), `NIGHTLY.md` (how the automated nightly sessions and the PR loop work), `PLAYTEST.md`, `RELEASE_NOTES_TEMPLATE.md` (the notes every release is published with), `HANDOFF.md` (status and next steps). |
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

## Licence

The **code** — `remake/` except `remake/game/assets/clean/` (that is the pack, below), `tools/`, the
workflows and these docs — is MIT: see [`LICENSE`](LICENSE).

The **clean asset pack** — the art, window layouts, fonts, text, sound effects and music built from
`remake/game/assets/clean/src` by `tools/clean_pack/build.py`, and the same pack inside every released
package — is licensed **CC BY 4.0**: see [`LICENSE-ASSETS`](LICENSE-ASSETS). That file states the
attribution line a reuser has to ship; the code carries no such condition.

Nothing here grants rights to SimAnt itself or to any Maxis or Electronic Arts material. The remake
reads the player's own copy of the original game at runtime and ships none of it, as the disclaimer at
the top of this README says.

## Known differences from the original

The remake is compared screen by screen against the original. Two differences are accepted, and they
are listed here rather than left silent: each is recorded, not scheduled for a fix.

- `yard`: **9 px**, all in two columns at x=264 and x=288, y=195–199, on one object in the yard
  view beside the house door. At x=264 the original draws sprite colours (violet `(242,8,133)` at
  y=195, then `(68,0,165)`) where the remake draws background `(64,64,64)`; at x=288 the original
  draws background green `(28,182,20)` at y=195–197 and `(0,101,16)` at y=198, where the remake
  draws a brown sprite pixel `(85,44,4)`. The object is therefore one pixel narrower on its left
  edge and one pixel longer on its right. Neither image has a transparent pixel anywhere (0 of
  307200 in each), so this is an outline difference, not a fill. Which sprite the cell holds is not
  established ([#25](https://github.com/Jrbesse/SimAnt-Evolved/issues/25)).
- `yardfront`: **2 px** at y=83, at x=63 and x=576 — the two ends of the top border, yellow
  `(255,242,4)` in the original and black in the remake.
  [#29](https://github.com/Jrbesse/SimAnt-Evolved/issues/29) reads that shape as the border's end caps,
  which is a hypothesis rather than a measurement.
