# Nightly sessions

Two automated sessions run every night and one report goes out in the morning. They exist to keep the burn-down
moving and to hand the next session a clean start: build, fix, test, review, commit, and write down what the next
session picks up.

| When (Central) | What | Where it lands |
|---|---|---|
| 01:00 | Nightly session 1 | a commit on `nightly/<date>` |
| 05:00 | Nightly session 2 | a commit on `nightly/<date>` |
| 07:00 | Morning report | the owner's Discord channel |

Central time is the owner's clock (`eagle1`, UTC-6 in winter). The jobs are Hermes cron jobs; the Cron runs on the
Hermes host, whose clock is UTC.

## Branch discipline

- Work goes on **`nightly/YYYY-MM-DD`** (the Central date at the session's start), branched from `origin/master`.
  **Never push `master`**. The owner reads the morning report and says when to merge; the merge is a fast-forward
  and is done by hand, not by a session.
- Session 2 reuses the same branch as session 1 (so a night is one reviewable diff). If `origin/master` moved
  during the day, rebase the branch onto it at the start of the session and say so in the log row.
- A day with no nightly branch means no session ran. Say that in the report; do not invent progress.

## Opening (10 minutes, in this order)

1. **Lock.** Session 1 writes `nightly.lock` (with its start time) into `<repo>/remake/build/` on `eagle1` and
   removes it at the end. Session 2 refuses to start if the lock is under 4 hours old (session 1 has overrun) and
   says so in the log row instead of racing it.
2. **Bridge.** `rql-query 'editor'` on the Godot-MCP endpoint must answer (`godot-mcp-bridge` skill). The editor is
   the server: if it is closed, build and test still work through `script-execute` (plain `dotnet`), but anything
   needing the live editor does not. Do not restart the editor; that is the owner's box.
3. **`AGENTS.md` §9** then **`docs/ROADMAP.md`**: the burn-down, the last log row, and **"The order"**. Answer its
   five questions in this session's log row *before* choosing work.
4. **`git status`** on `eagle1` must be clean apart from the known `remake/game/project.godot` phantom (CRLF, no
   content change). If something else is modified, say what and do not build on it.

## Choosing work

- Take work from the **top of the prerequisite order**, not the smallest job. A job whose prerequisite is open
  waits; an agent-doable prerequisite jumps the queue.
- **Agent-doable only.** Anything marked `(owner)` in the burn-down -- his test builds, his ears on the audio, and
  the name / licence / going-public decisions -- is reported, never attempted. **Screen work is no longer in that
  set:** the game renders its own frames (`tools/shots.ps1`) and the `vision` tool reads them -- see "Visual
  checks" below. A `(owner)` row for a screen now needs a reason beyond "an agent cannot see it".
- **Timebox ~90 minutes of work.** One job done and verified beats three half-done. Stop with the tree
  consistent, commit what is verified, and leave the rest as a row.
- **Every issue spotted gets a row before the session ends**, with the evidence that found it. This includes
  vacuous tests, stale docs, and anything the session chose not to fix.

## The verification gate (on `eagle1`, in `<repo>/remake`)

Nothing is "done" because it compiles. Before committing:

```
dotnet build OpenSimAnt.sln -c Release
dotnet test tests/OpenSimAnt.Sim.Tests -c Release --no-build
dotnet run --project tests/OpenSimAnt.Replay -c Release --no-build -- --quiet    # ends in "ALL OK"
```

- Read the replay's **per-file call counts**, not just the verdict: a `0/0 OK` row is vacuous (B8 is exactly this).
- For shell / UI work there is no trace: name the comparison (`tools/shots.ps1` + the question you asked `vision`,
  `--state=` + `tools/re/pngdiff.py`, a CI `clean-screens` artifact) and say what it showed. Never write
  "looks right".
- Heavy reference suites (`tools/ref/record_all.sh`, `test_*.py`) run for minutes: start them detached with a log
  and poll, do not block a tool call on them.

## Visual checks

A screen can be judged inside the session. It needs neither the owner nor a pushed branch.

1. **Render.** On `eagle1`, through `script-execute` (the box has Windows PowerShell 5.1, no `pwsh`):
   `powershell -NoProfile -ExecutionPolicy Bypass -File tools\shots.ps1 -Only game,yard` (add `-Clean` for the
   clean pack). PNGs and logs land in `remake/build/shots/`, which is git-ignored, and the script exits non-zero if
   a screen produced no PNG or its log holds an exception or a missing resource. The screens and seeds are
   `release.yml`'s, so a local frame and a `clean-screens` frame are the same frame.
2. **Get it to the model.** The `vision` tool reads a **local path**, and its SSRF guard blocks the tailnet range
   (`100.64.0.0/10`) outright -- a `...ts.net` URL is refused, and `eagle1` runs no SSH. Serve the shot from
   `eagle1` with the `http.server` trick (`godot-mcp-bridge` §"Editing files outside res://") and `curl` it to a
   local file first. `tools/shots.sh` on the Hermes box skips the hop entirely (xvfb + `--rendering-driver
   opengl3`, clean pack only, so no Maxis file ever leaves `eagle1`).
3. **Ask something falsifiable.** `vision` answers through a sub-call that returns text, so the question decides
   what the answer is worth: "is the interior of the window titled 'Map' solid black?", never "does this look
   right". `region` crops to one window. Put the question *and* the answer in the log row -- that is the evidence.

The three `screenshot-*` bridge tools stay blank and always will (`AGENTS.md` §5): they photograph the editor's
empty scene, not the running game. Do not file them as broken.

## Reading and writing

- **Read** from the Linux clone at `~/work/SimAnt-Evolved` (fast, whole files). Refresh it with `git pull` after
  the branch is pushed. It is a read path only; commits are made on `eagle1`.
- **Write small text files** on `eagle1` through `script-execute` (base64 or a tailnet `http.server`), then verify
  **SHA-256 against the local file** -- see `godot-mcp-bridge` §"Editing files outside res://".
- **Code under `res://`** goes through `script-create` / `script-update` + `script-build`, then an assertion.

## Committing

On `eagle1`, in the repo, with the repo-local identity (never override it):

```
git -C <repo> checkout -B nightly/YYYY-MM-DD origin/master   # session 1
git -C <repo> add <files> && git -C <repo> commit -F <msgfile>
set GIT_TERMINAL_PROMPT=0 && git -C <repo> push -u origin nightly/YYYY-MM-DD
git ls-remote origin refs/heads/nightly/YYYY-MM-DD            # confirm, do not trust the exit code alone
```

- Small, reviewable commits, each stating **what was verified and with which command**.
- Never commit `remake/build/` (traces, snapshots: they hold game memory), any Maxis file, or the built
  `clean_pack.zip`.

## The handoff the next session needs

Before ending, add to `docs/ROADMAP.md`: this session's log row (jobs done, jobs left, the five order answers) and
one line the next session starts from:

```
Next: <the job> -- start at <file / command / screenshot>, it needs <the thing>.
```

Session 2 also leaves the morning report's raw material in place: the branch name, the commit list, and the gate
output. The report reads those; it does not re-derive them.

## What the morning report says

What landed (per job, with the evidence), what is left and in which order, what needs the owner's decision, and
whether the branch is ready to merge. Issued at 07:00 Central to the owner's Discord channel.
