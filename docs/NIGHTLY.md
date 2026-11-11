# Nightly sessions

Two automated sessions run every night and one report goes out in the morning. They exist to keep the tracker
moving and to hand the next session a clean start: build, fix, test, review, commit, and write down what the next
session picks up.

Each night ends as a **pull request** against `master`. The PR is where review happens: an automated reviewer posts
a review with inline comments, and a fixer acts on those comments and on the owner's. **The merge is the machine's**,
on the evidence listed in "Who merges" below — the owner's lever is the `do-not-merge` label, not a click.

| When (Central) | What | Where it lands |
|---|---|---|
| 01:00 | Nightly session 1 | commits on `nightly/<date>`, then the PR is opened |
| 04:00 | Nightly session 2 | commits on the same branch, PR body rewritten |
| every 20 min, 05:00-22:00 | Review + fixer | a review posted on the PR; fixes pushed to its branch |
| 07:00 | Morning report | the owner's Discord channel: open PRs, CI, verdicts |

Central time is the owner's clock (`America/Chicago`, UTC-6 in winter). The jobs are Hermes cron jobs; the Cron runs
on the Hermes host, whose clock is UTC.

## Branch discipline

- Work goes on **`nightly/YYYY-MM-DD`** (the Central date at the session's start). **Never push `master`**.
- **Stack, do not wait.** If an open PR already has a `nightly/*` head, tonight's branch is cut from the newest
  such PR's head commit, not from `master`. Unmerged nights therefore stay continuous, and once the older PR merges,
  GitHub reduces the newer PR's diff to its own work. If nothing is open, cut from `origin/master`.
- Session 2 reuses the same branch as session 1 (a night is one reviewable diff). If `origin/master` moved during
  the day, rebase at the start of the session and say so in the PR body.
- A day with no nightly branch means no session ran. Say that in the report; do not invent progress.

## The pull request

- **Session 1 opens it**, after the branch is pushed and only if the branch has a commit of its own. Title
  `Nightly <date>`, base `master`, head `nightly/<date>`. A night that changed nothing gets no PR, and the session
  says so instead.
- Anything only the **owner** can settle goes under **Needs the owner** in the body: playing the game, his ears on
  the audio, the name / licence / legal decisions. Nothing that needs the original files belongs there -- they are on
  the Hermes box (see "Reading and writing"), so those checks run in the session and their numbers go in the body.
- **Session 2 rewrites the body** so it describes the finished night: what changed (a bullet per job with the
  evidence and the command), the gate results, the base it stacked on, what is still open, and the line that says
  who merges (the merge job, unless the PR carries `do-not-merge`). Re-runs use `gh pr edit`, never a second PR.
- Nobody pastes review comments into chat. The PR thread is the record.

## Review and fixes

- The reviewer profile wakes on the PR, not a clock: `nightly_review_gate.py` fires it only when an open nightly PR
  has a head SHA that has not been reviewed and the head has settled (10 minutes). It reviews the diff against the
  PR's real base, re-derives what it can locally (`dotnet build` / `dotnet test` / the replay / `tools/shots.sh` +
  `vision`),
  labels each session claim VERIFIED / CLAIMED / UNSUPPORTED, and posts one review with up to a dozen inline
  comments. `post_pr_review.py` posts it and records the reviewed SHA; a comment that cannot be anchored is moved
  into the summary rather than dropped.
- The review is posted by **`Jrbesse-Reviewer`**, a separate account with write access to the repo, using the token in
  `GH_REVIEWER_TOKEN` (`~/.hermes/profiles/reviewer/.env`; the poster also accepts `gh_reviewer_token` in the
  profile directory, read at post time so no gateway restart is needed). So a CHANGES verdict is a real
  `REQUEST_CHANGES` and the PR's review decision reads `CHANGES_REQUESTED` -- GitHub refuses that from the PR's own
  author, which is why one account cannot do this alone. The verdict is repeated in the review's first line for the
  report's benefit. The owner can still merge with changes requested: the approval is his.
- The fixer (`nightly_fix_gate.py`, same 20-minute cadence) acts on anything unprocessed: reviewer findings, and
  every owner comment unless it reads as a question or a scope decision. It has its **own clone** at
  `~/work/SimAnt-Fix` -- never the sessions' `~/work/SimAnt-Evolved`, whose working tree other jobs and the operator
  use. There it edits, runs build and the unit tests (and the replay when simulation behaviour moved), pushes to the
  PR branch, replies per comment, and acks the ids. Caps: 4 wakes per PR per day, and it never force-pushes, rebases
  shared history, merges, or approves.
- Review blocks the **merge job**, not the owner. The job wants an APPROVED review at the current head SHA, so a
  PR with changes requested waits until the fixer lands the fixes and the reviewer approves at the new head. The
  owner can still merge by hand with comments open, and the next night stacks on whatever state `master` is in.

## Who merges

`auto_merge.py` (dev profile, script-only, no agent) merges on its own evidence, so the nightly path does not need
the owner to press merge. All six have to hold:

1. open, not a draft, not from a fork, and based on `master` — a stacked PR is never auto-merged;
2. the author is in `OWNERS` (`{"Jrbesse"}`) — a bot or anyone else is skipped as "author not one of ours";
3. no hold label: `do-not-merge`, `hold` or `wip`;
4. `Jrbesse-Reviewer` has an **APPROVED** review at the **current head SHA**, and nothing has requested changes at
   that SHA (an approval on an older commit is a review of code that no longer exists);
5. every CI check on that SHA is green — at least one completed check, nothing pending, and each conclusion green,
   neutral or skipped (those three count as passing). A re-run leaves two entries of one check name in the rollup,
   often with the superseded one `CANCELLED`; the newest run of each name is the one that counts;
6. the repo's gate is **re-run by the job** on that SHA, in the fixer clone: the trace-count floor
   (`build/traces/*.trace` ≥ 20, so an empty set cannot pass vacuously), `dotnet build`, the unit tests, and the
   26-trace replay. This is the load-bearing step — CI here only compiles, so GitHub's green tick is not evidence
   that the simulation still matches.

It then merges with a merge commit, deletes the head branch (`--delete-branch`), posts the gate output it saw as a
PR comment, and clears the `in-progress` label the session left on its issue.

**The owner's veto is a label, before the fact.** `do-not-merge` (or `hold`, or `wip`) means the job never merges
that PR, whatever the review says, and the veto survives further pushes. After a merge the remedy is a revert PR:
a night lands as one merge commit, and the next session cuts from `master`.

**When it runs:** every 20 minutes (`:08`, `:28`, `:48`) and immediately on an approving review through the
`gh-auto-merge` webhook route. Two things can hold it back, and neither is a window after the approval:

- a PR under 10 minutes old is skipped as "still settling" — `MIN_AGE_SECONDS`, measured from the PR's `createdAt`,
  checked before the review verdict is even read;
- a PR whose checks are still running is skipped as "checks still running", and merges on the first tick that finds
  them finished.

So there is no grace period between approval and merge: once CI is green and the gate passes, the next tick merges.
`do-not-merge` has to be on the PR before that, not after.

## Opening (10 minutes, in this order)

1. **Lock.** Session 1 writes `nightly.lock` (with its start time) into `remake/build/` in the sessions' clone and
   removes it at the end. Session 2 refuses to start if the lock is under 4 hours old (session 1 has overrun) and
   says so in the PR body instead of racing it.
2. **Bridge.** `rql-query 'editor'` on the Godot-MCP endpoint must answer (`godot-mcp-bridge` skill, `AGENTS.md`
   §5). The editor runs on the Hermes box as a service and restarts itself; if the check fails, wait 2 minutes and
   retry once. Still failing is the night's finding -- file an issue before ending.
3. **`AGENTS.md` §9** then **`docs/ROADMAP.md`**: the open issues and the PR body's **"The order"** section. Answer its five questions in the PR body *before* choosing work.
4. **`git status`** in the clone must be clean. If something is modified, say what and do not build on it.

## Choosing work

- Take work from the **top of the prerequisite order**, not the smallest job. A job whose prerequisite is open
  waits; an agent-doable prerequisite jumps the queue.
- **Agent-doable only.** Anything carrying the `owner` label in the issue tracker -- his test builds, his ears on the audio, and
  the name / licence / going-public decisions -- is reported, never attempted. **Screen work is no longer in that
  set:** the game renders its own frames (`tools/shots.sh`, or the live editor) and the `vision` tool reads them -- see "Visual
  checks" below. An `owner` issue for a screen now needs a reason beyond "an agent cannot see it".
- **Timebox ~90 minutes of work.** One job done and verified beats three half-done. Stop with the tree
  consistent, commit what is verified, and leave the rest as an issue.
- **Every finding gets a GitHub issue before the session ends**, with the evidence that found it. This includes
  vacuous tests, stale docs, and anything the session chose not to fix.

## The verification gate (on the Hermes box, in `remake/`)

Nothing is "done" because it compiles. Before committing:

```
dotnet build OpenSimAnt.sln -c Release
dotnet test tests/OpenSimAnt.Sim.Tests -c Release --no-build
dotnet run --project tests/OpenSimAnt.Replay -c Release --no-build -- --quiet    # ends in "ALL OK"
```

- Read the replay's **per-file call counts**, not just the verdict: a `0/0 OK` row is vacuous (B8 is exactly this).
- The traces (`remake/build/traces`, git-ignored, game memory) are recorded **on the Hermes box**:
  `tools/ref/record_all.sh` drives the reference tests through the emulator and the original files, both of which are
  here. Every clone sees the same copy through the `~/work/simant-traces` link, and that copy is read-only to agents --
  a re-record is an operator action (write into a scratch tree and hand the files over), not something a session does
  under another session's feet. A recorder run that captured nothing leaves no trace file at all.
- A few unit tests need the owner's original files and pass as placeholders named `(no traces)` or
  `(no game files)` when they are absent. Those are a finding, never a pass.
- For shell / UI work there is no trace: name the comparison (`tools/shots.sh` + the question you asked `vision`,
  `--state=` + `tools/re/pngdiff.py`, a CI `clean-screens` artifact) and say what it showed. Never write
  "looks right".
- Heavy reference suites (`tools/ref/record_all.sh`, `test_*.py`) run for minutes: start them detached with a log
  and poll, do not block a tool call on them.

## Visual checks

A screen can be judged inside the session -- no owner, no pushed branch. Two steps:

1. **Render.** In the clone: `sh tools/shots.sh game yard` (any of `title game yard history antipedia
   tutorial`; no argument renders all six). PNGs and logs land in `remake/build/shots/`, git-ignored, a
   few seconds a screen. A non-zero exit is a failure to report, not a frame to judge: a screen made no
   PNG, or its log held an exception or a missing resource.
   The **reference** captures (`tools/re/build/screens`, what `compare_screens.py` reads) are per clone and go
   stale silently: a set recorded before `tools/extract.py` ran in that clone has no font-0 glyphs, so every diff
   against it carries the 1158-px menu band. After `tools/extract.py`, re-record it
   (`cd tools && ~/work/simant-venv/bin/python re/screens.py`, ~6 min); `screens.py` now refuses to record at all
   when `extracted/shared/font/` is missing instead of writing a fontless set.
2. **Ask.** Give the `vision` tool the PNG's **local path** (a tailnet URL is refused by its SSRF guard)
   and one falsifiable question -- "is the interior of the right-hand window solid black, or does it show
   map art?", never "does this look right". Put the question *and* the answer in the PR body; that is the
   evidence.

The Hermes box has what this needs: `/opt/godot` (4.6.2 mono), `/opt/dotnet` (SDK 8.0.427) and xvfb, with
`$GODOT` and the `dotnet` path set by `/etc/profile.d/dotnet.sh`. These are the clean pack's screens, the
same six and the same seeds `release.yml` renders, so a local frame and a `clean-screens` frame are the
same frame. **The original files are on the Hermes box too** -- read-only links in the sessions', reviewer's and
fixer's clones -- so a comparison that needs them runs here and its numbers go in the PR: the original look (run the
game without `--clean`, or `tools/shots.ps1` on the owner's box if the question is about his Windows build),
`--state=` + `tools/re/pngdiff.py`, `tools/re/screens.py` to re-render the original's own screens, or instrumenting the
game on the original files. Nothing on this line goes under Needs the owner any more.

**The live game.** For a screen that needs input to reach, use the editor on the Hermes box: `rql-mutate 'editor |
call PlayScene("res://Main.tscn")'`, drive it with `DISPLAY=:99 xdotool mousemove X Y click 1` (or `xdotool key
<key>`), capture with `godot-shot /tmp/<name>.png`, ask `vision` the same kind of question, then `rql-mutate 'editor
| call StopScene()'`. The editor draws on a virtual 1280x1024 display with software GL, so the frame is real.

`screenshot-*` on the bridge stays blank and always will (`AGENTS.md` §5): it photographs the editor's
empty scene, not the running game. Do not file it as broken.

## Reading and writing

- **Everything happens in the sessions' clone** at `~/work/SimAnt-Evolved` on the Hermes box: read, edit, build,
  test, commit and push there. The live editor has that clone open, so `script-build` builds what the session just
  wrote. The fixer has its own clone (`~/work/SimAnt-Fix`) and the reviewer its own (`~/work/SimAnt-Review`).
- **Code under `res://`** can also go through `script-create` / `script-update` + `script-build`, then an assertion.
- Render output (`remake/build/shots/`) and the traces are git-ignored, so `git status` stays clean.

## Committing

In the sessions' clone, with the owner's identity (never override it):

```
git checkout -B nightly/YYYY-MM-DD <base>          # session 1: <base> = newest open nightly PR's head, else origin/master
git add <files> && git commit -F <msgfile>
GIT_TERMINAL_PROMPT=0 git push -u origin nightly/YYYY-MM-DD
git ls-remote origin refs/heads/nightly/YYYY-MM-DD  # confirm, do not trust the exit code alone
```

- Small, reviewable commits, each stating **what was verified and with which command**.
- Never commit `remake/build/` (traces, snapshots: they hold game memory), any Maxis file, or the built
  `clean_pack.zip`.

## The handoff the next session needs

Before ending, add to the PR body: this session's summary (jobs done, jobs left, the five order answers) and
one line the next session starts from:

```
Next: <the job> -- start at <file / command / screenshot>, it needs <the thing>.
```

Session 2 also leaves the morning report's raw material in place: the branch name, the commit list, and the gate
output. The report reads those; it does not re-derive them.

## What the morning report says

One block per open PR: CI state, the review verdict, how many inline comments are open and how many are already
fixed, what landed (per job, with the evidence), and what needs the owner's decision. Then the pipeline state
(session 1, session 2, review, fixer) and what the next night starts from. It points at the PRs and does not restate
the review: the code discussion lives on GitHub. Issued at 07:00 Central to the owner's Discord channel.

## Discord's job, and GitHub's

Discord carries facts, not review: the morning report, a session failure, a PR opened, a CI verdict, a review
landed. Every code question, finding and fix is written on the PR.
