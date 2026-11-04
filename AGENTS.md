# AGENTS.md — OpenSimAnt

The contract for any agent working in this repo. Human-facing depth lives in `docs/`; this file is the entry point and the rules that are not negotiable.

---

## 1. What this is

**OpenSimAnt** is a faithful 1:1 modern remake of *SimAnt* (Maxis, 1991, DOS) — the art kept as close as possible, published on GitHub. **Reverse engineering comes first.**

**Formica** is a fully modern game built around the original's core loop, and starts only after OpenSimAnt is finished. Naming decided 2026-10-30: "OpenSimAnt" is the 1:1 remake (formerly called "Formica"); "Formica" now names the modern game (formerly "SimAnt: Evolved").

Where it stands: the simulation is byte-identical with the original in the emulator, the screens, sound and modes are built, and the owner played it on 2026-10-29 — "it seems to play identical to the original". All of that still needs the player's own copy of the original; **Track A** removes that need, then Track C releases it. The burn-down in `docs/ROADMAP.md` is the plan and is **updated every session**.

---

## 2. Hard constraints

- **Never commit Maxis files, or anything extracted from them.** `SIMANT.EXE`, `*.NDX`, `*.DAT` and the other originals in the repo root are the owner's own copy and are git-ignored. The game reads them at runtime through the asset layer (`OriginalFiles`), it does not embed them.
  - **One exception, the owner's decision of 2026-10-30:** the ~1.2 KB of *gameplay number tables* the simulation reads out of SIMANT.EXE (direction vectors, caste odds, terrain / rock shapes, cheat codes, the save layout; ROADMAP A2) may be committed as named, documented tables in source so the game runs without the original. **Numbers only — never art, text, sound or fonts.** Flagged for legal review before going public (Track C).
- **Commits use the owner's personal identity, configured repo-locally. Do not change it.**
- **Never commit `remake/build/`** (traces, snapshots, smoke PNGs). They hold game memory.
- The clean pack (`assets/clean/clean_pack.zip`) is built, not tracked: `python tools/clean_pack/build.py`. The release workflow builds it before exporting.

---

## 3. Repo map

| Path | What |
|---|---|
| `docs/SIM_NOTES.md` | **The knowledge base**: every decoded rule, memory layout, address. Read "Status and TODO" first, then the section for what you are porting. |
| `docs/HANDOFF.md` | Goals, repo map, the verification method, what is ported, next steps. |
| `docs/ROADMAP.md` | Burn-down in *jobs*, tracks A/B/C, the per-session log. |
| `docs/FILE_FORMATS.md`, `docs/ART_PLAN.md`, `docs/RECREATION_PLAN.md`, `docs/PLAYTEST.md` | Asset formats; the clean-room asset plan and specs; the overall plan; the owner's play-test checklist. |
| `docs/clean_pack/*.md` | 12 written specs of the clean assets — words only, so makers who never see the originals can build them. |
| `tools/*.py` | Asset extraction: archives, bitmaps, palette, MIDI, sound, `tiles.py` for map tiles / ant sprites. |
| `tools/re/` | Reverse-engineering tooling: `build_flat.py`, `adis.py`, `decomp.py`, `emu.py` (Unicorn), `symbols.json`. Generated output in `tools/re/build/` is git-ignored. |
| `tools/ref/simant_ref/` | **The Python reference port**, verified against the original. The spec for the C# port. |
| `tools/ref/test_*.py`, `verify.py`, `linecov.py` | Differential tests against the emulator; coverage. |
| `remake/src/OpenSimAnt.Sim/` | The simulation, a C# port of `simant_ref`. Plain .NET 8, no Godot. Same memory-mirroring `State`, same function names in PascalCase, one class per reference module. |
| `remake/src/OpenSimAnt.Data/` | Reading the player's files: LZSS archives, the starting State from SIMANT.EXE, map art (palette, tiles, sprites, recolouring), the renderer, `GameSession`. |
| `remake/game/` | The Godot 4.6 C# project: `Main.tscn`, `Main.cs` (the shell, one large file), `OpenSimAnt.csproj`. |
| `remake/tests/OpenSimAnt.Replay/` | Replays traces on the C# port, compares memory byte for byte; `--smoke`, `--songs`, `--longrun`, `--export-pack`. |
| `remake/tests/OpenSimAnt.Sim.Tests/` | xUnit, one test per trace file. |
| `.github/workflows/` | `build.yml` (restore, Release build, tests, Python compile) and `release.yml` (three platforms + clean pack). |

---

## 4. Verification — what counts as done

Three oracles, cheapest last:

1. **The emulator is ground truth.** `verify.Verifier` boots SIMANT.EXE in Unicorn, plays a Quick Game (seed `0x1234`) and caches six snapshots (ticks 0, 300, 900, 1500, 2200, 3000) in `tools/re/build/snapshots/`. `v.check(lin, port_fn, ...)` restores each, runs the original routine at flat address `lin` and the port on a `State` built from the same memory, and compares `0x3d570..0x62000` byte for byte. Useful options: `args_fn`, `repeat`, `pre` / `pre_once` (plant rare states, force rare branches), `post_args`, `ignore`.
2. **The Python reference is the cheap oracle.** Already verified against the emulator; port new behaviour there first when the rule is unclear.
3. **The C# port is checked by replaying recorded traces.** `record_traces.py` records every outermost reference call (arguments, player-hook class, clock, State before/after); the C# side finds the port by reflection (`surface.s_bored` → `Surface.SBored`) and compares the return value plus all 150,160 bytes of `State`. At the documented commit 25 trace files (~225,000 calls, 67,200 SimStep ticks) match.

```bash
sh tools/ref/record_all.sh          # re-record traces (minutes; needs the emulator setup)
cd remake
dotnet run --project tests/OpenSimAnt.Replay -c Release -- --quiet
dotnet test tests/OpenSimAnt.Sim.Tests -c Release
dotnet run --project tests/OpenSimAnt.Replay -c Release -- --smoke
```

The reference suite (`cd tools/ref && python test_terrain.py`, `test_sim.py 3000`, …) each takes minutes — run it in the background.

**Rule: a change is done when a trace replay or an emulator check passes — not when `dotnet build` is clean.** Shell/UI work has no trace: say what you checked and how (a named comparison, a `--screenshot` frame, a PLAYTEST section), and never write "looks right" without having looked at it.

Byte-exactness has sharp edges worth knowing before you "fix" something: 16-bit wraparound, C truncating division (`_cdiv`, `_cmod`) and short-circuit order all matter. Two random generators run in parallel (the game's LFSR, and MSC `rand()` in a few places); the LFSR is also drawn from by the spider composite, speech balloons and the yard's rain, so tick-for-tick fidelity means making those draws at the same moments.

---

## 5. The Godot editor bridge

The editor on the Windows box (`eagle1`) runs the Godot-MCP addon (0.34.0 / server 9.3.0) and exposes 14 tools. The editor **is** the server — close it and the bridge is gone. Facts below were verified by direct probe on 2026-11-04; older docs are wrong about several of them.

- **Endpoint:** `http://eagle1.tail2d7f30.ts.net:27785/p/293d4f7c`. The port is derived from the project's absolute path and the route is `/p/<pin>` — **do not hardcode either**; `godot-cli status` prints the truth.
- **Tools:** `script-create`, `script-update`, `script-read`, `script-delete`, `script-attach-to-node`, `script-build`, `script-validate`, `script-execute`, `rql-query`, `rql-mutate`, `rql-schema`, `screenshot-viewport`, `screenshot-camera`, `screenshot-isolated`. There is no `play_scene`, no `reflection-method-*`, no `console-get-logs`.
- **Everything that is not `script-*` / `screenshot-*` is RQL**, by upstream policy: `source | stage | stage`. `rql-schema` with no argument lists the sources.
- **Restart** (PowerShell, on the box): set `GODOT_MCP_CONNECTION_MODE=Custom`, `GODOT_MCP_HOST=http://localhost:27785`, `GODOT_MCP_START_SERVER=true`, `DOTNET_ThreadPool_ThreadsToKeepAlive=-1` **in that shell only** — never at User scope, where a stale value silently overrides every later fix — then `Start-Process godot -ArgumentList '--editor','--path',$P`.
- **The loop:** `script-read` → `script-create`/`script-update` → `script-build` → `rql-mutate 'editor | call PlayScene("res://Main.tscn")'` → `rql-query 'gameLog | where LogType != "Info" | first 20'` → `script-execute` to assert → `rql-mutate 'editor | call StopScene()'`.
- **A call during a pending assembly reload fails with a retryable error.** Wait a few seconds and retry; that is not a failed build.
- **`script-build` succeeding means only that the compiler agreed.** Assert with `script-execute` or `gameLog`.
- **`screenshot-*` capture the editor viewport, not the running game.** `Main.tscn` is a bare `Node2D` with no children — the shell draws everything procedurally at runtime — so those frames are blank. Visual QA needs an OS-level capture on the Windows box.
- **The endpoint is deliberately unauthenticated**; tailnet membership is the access control. Send no `Authorization` header. If calls start returning 401/403, someone changed that — look for `GODOT_MCP_AUTH_OPTION` / `GODOT_MCP_TOKEN` in the editor's environment.
- `godot-cli install-plugin` needs `--with-server`, and a GUI editor starts no server without `GODOT_MCP_START_SERVER=true` (undocumented upstream).

---

## 6. Toolchain rules

- **`global.json` pins SDK 8.0.415 — keep it.** The machine default is 10.0.101, and a C# assembly reload on .NET 10 can crash or hang the editor. There is no .NET 7 on the box, so `-PinSdk 8.0.404` hard-fails.
- **Keep `ImplicitUsings` disabled.** With it enabled the addon fails to compile (CS0104 on bare `Timer` / `FileAccess`); filed upstream as IvanMurzak/Godot-MCP#474.
- **Never put dev files under `remake/game/addons/godot_mcp/Runtime/`** — that directory ships in game builds.
- **Never bump the `com.IvanMurzak.*` NuGet pins.** Upstream owns them; they are mirrored in four places.
- New editor data access belongs in **RQL**, not a new `[AiTool]`.
- `remake/game/.mcp.json` is gitignored per-checkout; regenerate with `godot-cli configure <project> --agent <id>`.

---

## 7. Conventions the owner enforces

- **Every control is the original's.** The shell adds no keys and no clicks of its own (rule of 2026-11-01). New input is a bug, not a feature.
- **The owner's rule is fidelity, not improvement.** When the original is odd, reproduce the oddity; note it, don't fix it.
- Keep the burn-down honest: tick off what landed, add what you found, add a row to the session log — at the start and end of every session.
- Commit in small, reviewable steps, each stating what was verified and with which command.
- The clean-room rule is structural: sessions that study the originals write **specs in words only**; separate agents that never see the originals make the assets from those specs.

---

## 8. Where to read, and what is stale

| Read this | For |
|---|---|
| `docs/SIM_NOTES.md` → "Status and TODO", then the section for your subsystem | before porting any rule |
| `docs/HANDOFF.md` | the verification method and what is ported |
| `docs/ROADMAP.md` | what is left, and the current burn-down |
| `docs/ART_PLAN.md` §2, §8, §9 | the asset modes and the clean-room process |
| `remake/README.md` | the C# layout, the replay workflow, how to run the game |
| `docs/PLAYTEST.md` | what the owner checks, by section |

**Known stale:** `docs/HANDOFF.md` and the setup notes predate the working toolchain. Specifically: there is no `SETUP.md` in this repo (referenced by older notes but never committed), and any instructions naming port `8080`, the route `/mcp`, `play_scene`, `reflection-method-*`, `console-get-logs`, or "MCP config hot-reloads" are wrong — §5 is the verified state.

---

## 9. Opening a session

1. `docs/ROADMAP.md`: the burn-down table and the last log row.
2. `docs/HANDOFF.md` "How verification works", if you will touch the simulation.
3. `docs/SIM_NOTES.md` "Status and TODO", before porting anything.
4. If you will touch the Godot project: confirm the bridge answers (`rql-query 'editor'`), and that `git status` is clean before you start.
