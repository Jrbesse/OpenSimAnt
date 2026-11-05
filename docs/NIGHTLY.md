# Nightly sessions

Two automated sessions run every night and one report goes out in the morning. They exist to keep the burn-down
moving and to hand the next session a clean start: build, fix, test, review, commit, and write down what the next
session picks up.

Each night ends as a **pull request** against `master`. The PR is where review happens: an automated reviewer posts
a review with inline comments, and a fixer acts on those comments and on the owner's. The owner merges.

| When (Central) | What | Where it lands |
|---|---|---|
| 01:00 | Nightly session 1 | commits on `nightly/<date>`, then the PR is opened |
| 04:00 | Nightly session 2 | commits on the same branch, PR body rewritten |
| every 20 min, 05:00-22:00 | Review + fixer | a review posted on the PR; fixes pushed to its branch |
| 07:00 | Morning report | the owner's Discord channel: open PRs, CI, verdicts |

Central time is the owner's clock (`eagle1`, UTC-6 in winter). The jobs are Hermes cron jobs; the Cron runs on the
Hermes host, whose clock is UTC.

## Branch discipline

- Work goes on **`nightly/YYYY-MM-DD`** (the Central date at the session's start). **Never push `master`**.
- **Stack, do not wait.** If an open PR already has a `nightly/*` head, tonight's branch is cut from the newest
  such PR's head commit, not from `master`. Unmerged nights therefore stay continuous, and once the older PR merges,
  GitHub reduces the newer PR's diff to its own work. If nothing is open, cut from `origin/master`.
- Session 2 reuses the same branch as session 1 (a night is one reviewable diff). If `origin/master` moved during
  the day, rebase at the start of the session and say so in the log row.
- A day with no nightly branch means no session ran. Say that in the report; do not invent progress.

## The pull request

- **Session 1 opens it**, after the branch is pushed and only if the branch has a commit of its own. Title
  `Nightly <date>`, base `master`, head `nightly/<date>`. A night that changed nothing gets no PR, and the session
  says so instead.
- **Session 2 rewrites the body** so it describes the finished night: what changed (a bullet per job with the
  evidence and the command), the gate results, the base it stacked on, what is still open, and the line that says
  the merge is the owner's. Re-runs use `gh pr edit`, never a second PR.
- Nobody pastes review comments into chat. The PR thread is the record.

## Review and fixes

- The reviewer profile wakes on the PR, not a clock: `nightly_review_gate.py` fires it only when an open nightly PR
  has a head SHA that has not been reviewed and the head has settled (10 minutes). It reviews the diff against the
  PR's real base, re-derives what it can locally (`dotnet build` / `dotnet test` / `tools/shots.sh` + `vision`),
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
- Review never blocks the owner: he can merge a PR with open comments, and the next night stacks on whatever state
  `master` is in.

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

A screen can be judged inside the session -- no owner, no eagle1, no pushed branch. Two steps:

1. **Render.** In the clone: `sh tools/shots.sh game yard` (any of `title game yard history antipedia
   tutorial`; no argument renders all six). PNGs and logs land in `remake/build/shots/`, git-ignored, a
   few seconds a screen. A non-zero exit is a failure to report, not a frame to judge: a screen made no
   PNG, or its log held an exception or a missing resource.
2. **Ask.** Give the `vision` tool the PNG's **local path** (a tailnet URL is refused by its SSRF guard)
   and one falsifiable question -- "is the interior of the right-hand window solid black, or does it show
   map art?", never "does this look right". Put the question *and* the answer in the log row; that is the
   evidence.

The Hermes box has what this needs: `/opt/godot` (4.6.2 mono), `/opt/dotnet` (SDK 8.0.427) and xvfb, with
`$GODOT` and the `dotnet` path set by `/etc/profile.d/dotnet.sh`. These are the clean pack's screens, the
same six and the same seeds `release.yml` renders, so a local frame and a `clean-screens` frame are the
same frame. The original files never leave eagle1, so a comparison that needs them is `tools/shots.ps1`
there, through the bridge -- the one visual check that still needs eagle1.

`screenshot-*` on the bridge stays blank and always will (`AGENTS.md` §5): it photographs the editor's
empty scene, not the running game. Do not file it as broken.

## Reading and writing

- **Read** from the Linux clone at `~/work/SimAnt-Evolved` (fast, whole files). Refresh it with `git pull` after
  the branch is pushed. Sessions read here and commit on `eagle1`; the fixer edits here and pushes from here, so it
  fetches and checks out the PR head first and never rebases shared history. It does render: `tools/shots.sh`
  builds and draws there ("Visual checks"), and its output is git-ignored, so `git status` in the clone stays clean.
- **Write small text files** on `eagle1` through `script-execute` (base64 or a tailnet `http.server`), then verify
  **SHA-256 against the local file** -- see `godot-mcp-bridge` §"Editing files outside res://".
- **Code under `res://`** goes through `script-create` / `script-update` + `script-build`, then an assertion.

## Committing

On `eagle1`, in the repo, with the repo-local identity (never override it):

```
git -C <repo> checkout -B nightly/YYYY-MM-DD <base>          # session 1: <base> = newest open nightly PR's head, else origin/master
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

One block per open PR: CI state, the review verdict, how many inline comments are open and how many are already
fixed, what landed (per job, with the evidence), and what needs the owner's decision. Then the pipeline state
(session 1, session 2, review, fixer) and what the next night starts from. It points at the PRs and does not restate
the review: the code discussion lives on GitHub. Issued at 07:00 Central to the owner's Discord channel.

## Discord's job, and GitHub's

Discord carries facts, not review: the morning report, a session failure, a PR opened, a CI verdict, a review
landed. Every code question, finding and fix is written on the PR.
