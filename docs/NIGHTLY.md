# Nightly sessions

One continuous session runs around the clock and one report goes out in the morning. It exists to keep
the trackers moving and to hand the next session a clean start: pick, build, fix, test, review, open the
pull request, and leave nothing that cannot be seen on GitHub. Work starts the moment a PR merges instead
of at a fixed slot: the four fixed sessions (01:00 / 02:00 / 03:00 / 04:00 Central, the "Nightly session
1-4" jobs) are paused and superseded as of 2026-11-15, kept for a rollback.

The sessions are the pipeline's hands, not its brain: the **picker** chooses the work, the **reviewer**
judges it, the **fixer** answers findings, and the **merge job** decides when a PR lands. The pipeline
runs across every repo enabled in its registry on the Hermes box, one pick at a time; this file is the
protocol for this repo's share of it.

Every pick ends as a **pull request** against `master`. The PR is where review happens: an automated reviewer posts
a review with inline comments, and a fixer acts on those comments and on the owner's. **The merge is the machine's**,
on the evidence listed in "Who merges" below. The owner's veto is the `do-not-merge` label; he can still merge by
hand with comments open, but nothing waits for him to press anything.

| When | What | Where it lands |
|---|---|---|
| every 20 min, and immediately on a PR merge | Continuous 24/7 session | its pick's branch and PR |
| on a PR event (head settled 10 min) | Reviewer | a review posted on the PR |
| every 2 hours | Reviewer triage (all repos) + PR fixer | priority labels on issues; fixes pushed to the PR branch |
| every 20 min (`:08`/`:28`/`:48`) | Auto-merge job | the merge, when all its conditions hold |
| 07:00 | Morning report | the owner's Discord channel: PRs, CI, queue |

Central time is the owner's clock (`America/Chicago`, UTC-6 in winter). The jobs are Hermes cron jobs; the cron runs
on the Hermes host, whose clock is UTC.

## The pick

The session does not choose; the picker does. Before waking the session, the wake gate
(`continuous_pick_gate.py`) runs `nightly_pick.py` over the registry of enabled repos, lists every open
issue in them, and ranks:

- **priority label first**: `priority: P0` > `P1` > `P2` > `P3` > none. The labels are set by the
  reviewer's triage job, which walks the trackers on a clock.
- within a level, **oldest issue first** (so nothing starves), then lowest number.
- issues labelled `owner` (the owner's judgement), `blocked` (waiting on something else), `in-progress`
  (a session already has a branch open), `question`, `wontfix` or `duplicate` are never picked.

**One in-flight item per repo.** A repo that has an `in-progress` issue or an open `nightly/*` PR
contributes nothing until that work merges: two sessions in one repo share a working tree, and the second
would build on an unmerged foundation. The wake gate claims the pick before the session wakes -- an
exclusive claim file plus the `in-progress` label on the issue -- so a second wake in the same window sees
the label and skips; the merge job clears the label when the PR closes its issue. A claim older than six
hours with no open `nightly/*` PR is a dead session: the sweep clears the label and drops the claim, and
the issue re-enters the queue.

The picker hands the session its pick -- workdir, repo, issue number and body, that repo's gate commands,
the docs to read first -- plus a short list of what it is *not* doing this run. If every enabled repo is
mid-flight, or every tracker is empty, the session says so in one line and stops instead of inventing
work.

## Branch discipline

- Work goes on **`nightly/YYYY-MM-DD-<issue>`** (the Central date at the session's start, the issue's
  number). **Never push `master`.**
- The branch is cut from the repo's **default branch** (read it with `git symbolic-ref
  refs/remotes/origin/HEAD` after a fetch) -- never from another session's branch. Sessions work
  different picks, usually in different repos, so there is nothing to stack on: one pick, one branch,
  one PR.
- A fix that the reviewer or the owner asks for on an open PR goes on that PR's existing branch (the
  fixer pushes there), not on a new one.
- A day with no new branch in this repo means no session picked it. Say that in the report; do not
  invent progress.

## The pull request

- One PR **per pick**, opened by the session that did the work, after the branch is pushed and only if
  the branch has a commit of its own. Base `master`, head `nightly/<date>-<issue>`. A pick that changed
  nothing gets no PR, and the session says so instead.
- The title says what the work is, and the body carries what changed and why, the line that closes the
  issue (`Closes #N`), and the gate evidence with the real command output.
- Anything only the **owner** can settle goes under **Needs the owner** in the body: playing the game, his ears on
  the audio, the name / licence / legal decisions. Nothing that needs the original files belongs there -- they are on
  the Hermes box (see "Reading and writing"), so those checks run in the session and their numbers go in the body.
- **A later session does not rewrite the body.** If the PR has unanswered reviewer comments or a failing
  check, the next session addresses them on the PR's own branch before taking a new pick; a red gate the
  auto-merge job reported is the highest priority of all. Re-runs use `gh pr edit` on the PR that owns
  them, never a second PR for the same issue.
- Nobody pastes review comments into chat. The PR thread is the record.

## Review and fixes

- The reviewer profile wakes on the PR, not a clock: `nightly_review_gate.py` fires it only when an open nightly PR
  has a head SHA that has not been reviewed and the head has settled (10 minutes). It reviews the diff against the
  PR's real base, re-derives what it can locally (`dotnet build` / `dotnet test` / the replay / `tools/shots.sh` +
  `vision`),
  labels each session claim VERIFIED / CLAIMED / UNSUPPORTED, and posts one review with up to a dozen inline
  comments. `post_pr_review.py` posts it and records the reviewed SHA; a comment that cannot be anchored is moved
  into the summary rather than dropped.
- The reviewer profile also runs a **triage job on a clock** (every 2 hours, across every repo in the
  registry): it reviews PRs whose head moved or that gained comments, and it sets the `priority: P0..P3`
  labels the picker ranks by. Everything it says goes on GitHub as the reviewer account, never in chat.
- The review is posted by **`Jrbesse-Reviewer`**, a separate account with write access to the repo, using the token in
  `GH_REVIEWER_TOKEN` (`~/.hermes/profiles/reviewer/.env`; the poster also accepts `gh_reviewer_token` in the
  profile directory, read at post time so no gateway restart is needed). So a CHANGES verdict is a real
  `REQUEST_CHANGES` and the PR's review decision reads `CHANGES_REQUESTED` -- GitHub refuses that from the PR's own
  author, which is why one account cannot do this alone. The verdict is repeated in the review's first line for the
  report's benefit.
- The fixer (`nightly_fix_gate.py`, every 2 hours) acts on anything unprocessed: reviewer findings, and
  every owner comment unless it reads as a question or a scope decision. It has its **own clone** at
  `~/work/SimAnt-Fix` -- never the sessions' `~/work/SimAnt-Evolved`, whose working tree other jobs and the operator
  use. There it edits, runs build and the unit tests (and the replay when simulation behaviour moved), pushes to the
  PR branch, replies per comment, and acks the ids. Caps: 4 wakes per PR per day, and it never force-pushes, rebases
  shared history, merges, or approves.
- Review blocks the **merge job**, not the owner. The job wants an APPROVED review at the current head SHA, so a
  PR with changes requested waits until the fixer lands the fixes and the reviewer approves at the new head. The
  owner can still merge by hand with comments open, and the next session picks from whatever state `master` is in.

## Who merges

`auto_merge.py` (dev profile, script-only, no agent) merges on its own evidence, so the nightly path does not need
the owner to press merge. All six have to hold:

1. open, not a draft, not from a fork, and its **base is `master`** — that is the job's whole stack test
   (`auto_merge.py:213-214`), and it never looks at ancestry, only the base field. So a PR based on another
   branch is skipped as "base is X, not `master`". Branch discipline cuts every nightly branch from the
   default branch, so this test now mostly guards against hand-cut PRs; a content stack is not held for its
   base PR, and if it should be, that is a change to the job, not a guarantee it already gives;
2. the author is in `OWNERS` (`{"Jrbesse"}`) — a bot or anyone else is skipped as "author not one of ours";
3. no hold label: `do-not-merge`, `hold` or `wip`;
4. `Jrbesse-Reviewer` has an **APPROVED** review at the **current head SHA**, and nothing has requested changes at
   that SHA (an approval on an older commit is a review of code that no longer exists);
5. every CI check on that SHA is green — at least one completed check, nothing pending, and each conclusion green,
   neutral or skipped (those three count as passing). A re-run leaves two entries of one check name in the rollup,
   often with the superseded one `CANCELLED`; the newest run of each name is the one that counts;
6. the repo's gate is **re-run by the job** on that SHA, in the fixer clone: the trace-count floor
   (`build/traces/*.trace` ≥ 20, so an empty set cannot pass vacuously), `dotnet build`, the unit tests, and the
   26-trace replay. This is the load-bearing step: CI compiles, runs the unit tests and diffs the generated sprite
   sheets, but it cannot run the replay (the traces are not in the repo), so GitHub's green tick is not evidence
   that the simulation still matches.

It then merges with a merge commit, deletes the head branch (`--delete-branch`), posts the gate output it saw as a
PR comment, and clears the `in-progress` label the session left on its issue.

**The owner's veto is a label, before the fact.** `do-not-merge` (or `hold`, or `wip`) means the job never merges
that PR, whatever the review says, and the veto survives further pushes. After a merge the remedy is a revert PR:
a pick lands as one merge commit, and the next session cuts from the default branch (see "Branch discipline").

**When it runs:** every 20 minutes (`:08`, `:28`, `:48`) and immediately on an approving review through the
`gh-auto-merge` webhook route. Two things can hold it back, and neither is a window after the approval:

- a PR under 10 minutes old is skipped as "still settling" — `MIN_AGE_SECONDS`, measured from the PR's `createdAt`,
  checked before the review verdict is even read;
- a PR whose checks are still running is skipped as "checks still running", and merges on the first tick that finds
  them finished.

So there is no grace period between approval and merge: once CI is green and the gate passes, the next tick merges.
`do-not-merge` has to be on the PR before that, not after.

## Opening (10 minutes, in this order)

1. **The pick and its guard.** The wake gate refused any repo with an `in-progress` issue or an open `nightly/*` PR,
   and it claimed the pick (claim file + `in-progress` label) before waking the session -- that label and the open
   branch are the guard between sessions. No lock file is written; the old `nightly.lock` belonged to the
   two-session schedule.
2. **Bridge.** `rql-query 'editor'` on the Godot-MCP endpoint must answer (`godot-mcp-bridge` skill, `AGENTS.md`
   §5). The editor runs on the Hermes box as a service and restarts itself; if the check fails, wait 2 minutes and
   retry once. Still failing is the run's finding -- file an issue before ending.
3. **`AGENTS.md` §9** then **`docs/ROADMAP.md`**: the open issues and the PR body's **"The order"** section. Answer
   its five questions in the PR body before the work starts.
4. **`git status`** in the clone must be clean. If something is modified, say what and do not build on it.

## Choosing work

- Work **the pick the script named**, not a different issue, and satisfy its acceptance criteria, not your idea of
  a bigger fix.
- **Agent-doable only.** Anything carrying the `owner` label in the issue tracker -- his test builds, his ears on the audio, and
  the name / licence / going-public decisions -- is reported, never attempted. **Screen work is no longer in that
  set:** the game renders its own frames (`tools/shots.sh`, or the live editor) and the `vision` tool reads them -- see "Visual
  checks" below. An `owner` issue for a screen now needs a reason beyond "an agent cannot see it".
- **If the pick turns out to be wrong, needs the owner, or is blocked by another issue**, label it
  (`owner` or `blocked`), say why in a comment on the issue, and stop -- do not substitute a different
  task.
- **Every finding gets a GitHub issue before the session ends**, with the evidence that found it. This includes
  vacuous tests, stale docs, and anything the session chose not to fix. An out-of-scope finding is filed on the
  same repo, with its own acceptance criteria.

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
git fetch origin
git checkout -B nightly/YYYY-MM-DD-<issue> <base>   # <base> = the repo's default branch (origin/HEAD), never another session's branch
git add <files> && git commit -F <msgfile>
GIT_TERMINAL_PROMPT=0 git push -u origin nightly/YYYY-MM-DD-<issue>
git ls-remote origin refs/heads/nightly/YYYY-MM-DD-<issue>  # confirm, do not trust the exit code alone
```

- Small, reviewable commits, each stating **what was verified and with which command**.
- Never commit `remake/build/` (traces, snapshots: they hold game memory), any Maxis file, or the built
  `clean_pack.zip`.

## What the next session starts from

There is no handoff note: the next session starts from what is visible on GitHub. It lists this repo's open
`nightly/*` PRs first, and anything with unanswered reviewer comments or a failing check comes before its own
pick (a red gate the auto-merge job reported is the highest priority of all). The PR body is the record of the
finished work -- what changed and why, the gate evidence, what is still open -- and what is still open should
already be issues, not promises in the body.

## What the morning report says

One line per repo that had activity: the PR link(s) with check state, and the issue(s) closed. Then what is at the
top of the queue now -- the highest-priority open issue per repo, one line each. Then anything that needs the
owner specifically: `owner` issues, blocked work waiting on a decision, a red check nobody has explained, a PR
that is ready to merge. If a scheduled session did not run or produced nothing, it says so plainly instead of
describing an empty day as quiet progress. It points at the PRs and does not restate the review: the code
discussion lives on GitHub. Issued at 07:00 Central to the owner's Discord channel.

## Discord's job, and GitHub's

Discord carries facts, not review: the morning report, a session failure, a PR opened, a CI verdict, a review
landed. Every code question, finding and fix is written on the PR.
