# AGENTS.md — OpenSimAnt

The contract for any agent working in this repo. Human-facing depth lives in `docs/`; this file is the entry point and the rules that are not negotiable.

---

## 1. What this is

**OpenSimAnt** is a faithful 1:1 modern remake of *SimAnt* (Maxis, 1991, DOS) — the art kept as close as possible, published on GitHub. **Reverse engineering comes first.**

**Formica** is a fully modern game built around the original's core loop, and starts only after OpenSimAnt is finished. Naming decided 2026-10-30: "OpenSimAnt" is the 1:1 remake (formerly called "Formica"); "Formica" now names the modern game (formerly "SimAnt: Evolved").

Where it stands: the simulation is byte-identical with the original in the emulator, the screens, sound and modes are built, and the owner played it on 2026-10-29 — "it seems to play identical to the original". All of that still needs the player's own copy of the original; **Track A** removes that need, then Track C releases it. Open work is tracked in **GitHub issues**; `docs/ROADMAP.md` is the last burn-down snapshot and its label rules, kept as history.

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
| `docs/ROADMAP.md` | History: the last burn-down snapshot and the label rules. Open work is GitHub issues. |
| `docs/FILE_FORMATS.md`, `docs/ART_PLAN.md`, `docs/RECREATION_PLAN.md`, `docs/PLAYTEST.md` | Asset formats; the clean-room asset plan and specs; the overall plan; the owner's play-test checklist. |
| `docs/NIGHTLY.md` | The protocol the automated nightly sessions follow (branch, gate, commits, the handoff to the next session). |
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

### Screenshots in a pull request

A PR that changes anything a player can see ships **one picture of it, captured from a real run of the built code** — not the editor, not a mock, and not the launcher unless the launcher is what changed:

```bash
shot --project remake/game --self-flag '--screenshot={out} --frames=240' --label <what-it-shows>
```

`shot` always exits 0, is hard-timeout bounded, and falls back from the desktop VM to this container's Xvfb on its own, so a capture can never fail a session. The order that keeps a night safe: verify → commit and push the branch → capture → commit the image → open the PR. Never put a capture between "the work is done" and "the work is pushed".

- Commit the `-1360x768.jpg` under `docs/assets/images/pr-<issue>/` in a small docs-only commit, after the branch is already pushed.
- Embed it in the PR body under a `## Screenshot` heading with one line saying what to look at, using the blob URL at the head SHA: `https://github.com/Jrbesse/SimAnt-Evolved/blob/<head-sha>/docs/assets/images/pr-<issue>/<name>-1360x768.jpg?raw=true`
- If it prints `SHOT SKIP`, write that in the PR body in one line and carry on. Do not retry it in a loop and do not substitute a staged or editor frame.
- Look at the file before committing it. A capture of the wrong window or a black frame has happened before; a mislabelled image is worse than none.

---

## 5. The Godot editor bridge

Since 2026-11-05 the editor runs **on the Hermes box** (the agent's Linux container), not on the owner's Windows box (`eagle1`). It is a systemd service (`godot-editor.service`) on the sessions' clone `~/work/SimAnt-Evolved`, drawing on a virtual display (`:99`, 1280x1024, software GL). It runs the Godot-MCP addon (0.35.0 / server 9.4.0, the linux-x64 build) and exposes 14 tools. **0.35.0 was promoted to the permanent pin on 2026-11-06** after a night of use (`com.IvanMurzak.McpPlugin` 8.19.0 in `remake/game/OpenSimAnt.csproj`) and it is now the known-good fallback copy; a newer release is tried as an experiment — see §10. The editor **is** the server: if it stops, systemd restarts it within seconds, a watchdog restarts it after ~15 minutes without an answer, and it is restarted fresh at 00:40 Central before the nightly sessions.

- **Endpoint:** `http://127.0.0.1:25901/mcp`, loopback only. The port is derived from the project's absolute path, so it changes if the clone moves; `godot-cli status <project>` prints the truth. (The `/p/<pin>` route is only needed when one server hosts several projects.)
- **Tools:** `script-create`, `script-update`, `script-read`, `script-delete`, `script-attach-to-node`, `script-build`, `script-validate`, `script-execute`, `rql-query`, `rql-mutate`, `rql-schema`, `screenshot-viewport`, `screenshot-camera`, `screenshot-isolated`. There is no `play_scene`, no `reflection-method-*`, no `console-get-logs`.
- **Everything that is not `script-*` / `screenshot-*` is RQL**, by upstream policy: `source | stage | stage`. `rql-schema` with no argument lists the sources.
- **Restart** is automatic; agents cannot run `systemctl`. If `rql-query 'editor'` fails, wait 2 minutes and retry once, then report it.
- **The loop:** `script-read` → `script-create`/`script-update` → `script-build` → `rql-mutate 'editor | call PlayScene("res://Main.tscn")'` → `rql-query 'gameLog | where LogType != "Info" | first 20'` → look at it (below) → `script-execute` to assert → `rql-mutate 'editor | call StopScene()'`.
- **A call during a pending assembly reload fails with a retryable error.** Wait a few seconds and retry; that is not a failed build.
- **`script-build` succeeding means only that the compiler agreed.** Assert with `script-execute` or `gameLog`.
- **`screenshot-*` capture the editor viewport, not the running game.** `Main.tscn` is a bare `Node2D` with no children — the shell draws everything procedurally at runtime — so those frames are blank, and no fix to those three tools would change it. **To see the running game,** capture the virtual display while it plays: `godot-shot /tmp/<name>.png`, driven with `DISPLAY=:99 xdotool ...`, then give the PNG to `vision`. For the six named screens, `tools/shots.sh` renders the game's own capture (`--screenshot=<png>`, handled by `Main.cs` `ShotPoll`; xvfb + `--rendering-driver opengl3`, clean pack only). **Never `--headless` for a frame** — that is the dummy renderer, and it really does save a blank image.
- **The endpoint is unauthenticated** and bound to loopback, so nothing off the box can reach it. Send no `Authorization` header.
- `godot-cli install-plugin --path <project> --with-server` installs the addon and the matching server; `addons/godot_mcp/` and `.ai-game-dev/` are git-ignored, so a new clone needs it run once. The service sets `GODOT_MCP_START_SERVER=true` (undocumented upstream), without which an editor starts no server.
- **The original files are on the Hermes box** (read-only links in the sessions', reviewer's and fixer's clones; never the release clone), so everything that needs them runs there: the original look (run the game without `--clean`: it reads the original files when they are there), `--state=` + `tools/re/pngdiff.py` against the original's own memory captures, `tools/re/screens.py` to re-render those captures from `SIMANT.EXE`, and the reference tests in the emulator. Nothing is deferred to the owner's box any more; what stays the owner's is his test builds, his ears on the audio, and the name / licence decisions.

---

## 6. Toolchain rules

- **`global.json` pins SDK 8.0.415 — keep it** (with `rollForward: latestFeature`, the Hermes box's 8.0.427 satisfies it). eagle1's default is 10.0.101, and a C# assembly reload on .NET 10 can crash or hang the editor. There is no .NET 7 on eagle1, so `-PinSdk 8.0.404` hard-fails.
- **Keep `ImplicitUsings` disabled.** With it enabled the addon fails to compile (CS0104 on bare `Timer` / `FileAccess`); filed upstream as IvanMurzak/Godot-MCP#474.
- **Never put dev files under `remake/game/addons/godot_mcp/Runtime/`** — that directory ships in game builds.
- **Never bump the `com.IvanMurzak.*` NuGet pins.** Upstream owns them; they are mirrored in four places.
- New editor data access belongs in **RQL**, not a new `[AiTool]`.
- `remake/game/.mcp.json` is gitignored per-checkout; regenerate with `godot-cli configure <project> --agent <id>`.

---

## 7. Conventions the owner enforces

- **Every control is the original's.** The shell adds no keys and no clicks of its own (rule of 2026-11-01). New input is a bug, not a feature.
- **The owner's rule is fidelity, not improvement.** When the original is odd, reproduce the oddity; note it, don't fix it.
- Keep the tracker honest: close what landed, file what you found, and put the session summary in the PR body — at the start and end of every session.
- Commit in small, reviewable steps, each stating what was verified and with which command.
- The clean-room rule is structural: sessions that study the originals write **specs in words only**; separate agents that never see the originals make the assets from those specs.

---

## 8. Where to read, and what is stale

| Read this | For |
|---|---|
| `docs/SIM_NOTES.md` → "Status and TODO", then the section for your subsystem | before porting any rule |
| `docs/HANDOFF.md` | the verification method and what is ported |
| `docs/ROADMAP.md` | history: the last burn-down snapshot and the label rules; open work is GitHub issues |
| `docs/ART_PLAN.md` §2, §8, §9 | the asset modes and the clean-room process |
| `remake/README.md` | the C# layout, the replay workflow, how to run the game |
| `docs/PLAYTEST.md` | what the owner checks, by section |

**Known stale:** `docs/HANDOFF.md` and the setup notes predate the working toolchain. Specifically: there is no `SETUP.md` in this repo (referenced by older notes but never committed), and any instructions naming port `8080` or `27785`, the eagle1 endpoint, `play_scene`, `reflection-method-*`, `console-get-logs`, or "MCP config hot-reloads" are wrong — §5 is the verified state.

---

## 9. Opening a session

1. The **open issues** (`gh issue list --state open`) and the PR body's **"The order"** section, before
   choosing any work. A job whose prerequisite is open waits, even if it is the smaller one; a prerequisite
   that is agent-doable goes to the top of the session. Answer the five questions in the PR body.
2. Anything the session finds and does not fix becomes a GitHub issue **before the session ends**.
   A finding with no issue is lost.
3. `docs/HANDOFF.md` "How verification works", if you will touch the simulation.
4. `docs/SIM_NOTES.md` "Status and TODO", before porting anything.
5. If you will touch the Godot project: confirm the bridge answers (`rql-query 'editor'`), and that `git status` is clean before you start.
6. Nightly sessions (the automated ones) follow `docs/NIGHTLY.md`: the same opening, plus the build / test gate,
   the commit rule and the handoff they must leave for the session after them.

---

## 10. A new Godot-MCP release (the upgrade loop)

The addon is environment, not repo: it lives in a git-ignored `res://addons/godot_mcp/`, and its NuGet pin is the
only committed trace of it. A new upstream release is tried as an **experiment** for a night and promoted only
after it has earned it. Nobody installs an addon by hand; `simant_mcp_envelope.py` owns all of it.

- **Detection is automatic.** `godot_mcp_watch.py` (daily, 09:00) reads Ivan's releases; when the newest tag is
  newer than the known-good copy it runs `upgrade <tag>` and says so in the digest. `upgrade` downloads
  `godot-mcp-addon-<v>.zip`, takes the McpPlugin version the addon itself requires from its `nuget-deps.json`,
  installs the addon, writes a temporary `remake/game/Directory.Build.targets` pin override (never in git),
  builds, restarts the editor and probes. It is one command by hand too: `python3
  ~/.hermes/profiles/dev/scripts/simant_mcp_envelope.py upgrade v0.36.0`.
- **The night tests it.** The 00:45 preflight (`7b9ee2a44166`) waits up to 4 minutes for the staged addon; if it
  does not come up it restores the known-good copy, restarts the editor, re-probes, and posts one line to
  Discord. Sessions then run on whatever is healthy — a revert is a finding to record, not a failed session.
  The PR body's `## MCP environment` section carries the addon and server version actually used.
- **The morning decides.** `simant_mcp_envelope.py promote-check <pr>` answers READY / NOT READY from three
  facts: the reviewer's verdict is MERGE, no `fallback` event fired that night, and the bridge is on the
  experiment. The morning report states it; it never promotes.
- **Promotion is a person's call**, and it is two steps: `promote --yes` (writes the pin into
  `OpenSimAnt.csproj`, builds Release, retires the override, and leaves the change **uncommitted**), then snapshot
  the new known-good (`cp -a` the addon into `~/work/mcp-addon-backups/<v>-<stamp>` and point
  `LAST_KNOWN_GOOD` at it, or the next experiment would fall back to the old version), then land the csproj
  change through a branch and a PR — never on master from the script.
- **A failed experiment never gets left installed.** `upgrade` restores the known-good addon if the build
  against the new pin breaks, and the preflight covers the case where it builds but does not serve.
- Verified 2026-11-06: 0.35.0 promoted (pin 8.19.0, server 9.4.0, bridge healthy, `upgrade v0.35.0` re-stage
  23 s end to end), and a fake newer tag fails safe (`Staging Godot-MCP 9.9.9 failed ... bridge stays on 0.35.0`).
