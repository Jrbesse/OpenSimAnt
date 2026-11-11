# Publication: licence, legal position, and what goes public

**Decided 2026-11-09 by the owner** (issue #22), recorded here on 2026-11-11. Three decisions, and the conditions
that keep them true. This file is the answer to "can this be published?"; the roadmap's Track C points here.

## 1. Licence — settled

- **Code: MIT** (`LICENSE`, 415 tracked files at v1.0.0). **Clean asset pack: CC BY 4.0** (`LICENSE-ASSETS`,
  440 files). No path is under both.
- Both files ship **inside every release package**, with `THIRD_PARTY_NOTICES.txt` and `HOW_TO_PLAY.txt`, because
  the CC BY attribution requirement fails if a downloader never sees the repository.
- The CC BY legal code in `LICENSE-ASSETS` is byte-identical to the canonical text (lines 30–425,
  `sha256 9ba9550a…`), so the file is the licence rather than a paraphrase of it.

## 2. Legal position — accepted risk, not an outstanding review

**No external legal review.** A faithful recreation of a 1991 commercial game is published on the same basis that
OpenRCT2 and OpenTTD are: unofficial, unaffiliated, and shipping none of the original's content.

The conditions that carry the risk, all of them verifiable:

- **No original assets, ever.** The clean pack is built from its own sources by
  `tools/clean_pack/build.py` and the release workflow plays the game on it under `xvfb` before packaging, on a
  runner that has never seen `SIMANT.EXE`. That is the evidence, not the promise.
- **No original text.** The A5 review measured every string: 70 of 518 entries identical, and all but two are
  functional labels (castes, view names, "Nothing"). Both exceptions are on the record in
  `docs/A5_SIMILARITY_REVIEW.md`: list `1020` entry 5 ("The red ants are attacking!") is verbatim prose and is the
  one open item — **#51**, still open, and the number drops to 69 when it lands; list `1240` entry 0
  ("Where am I?") is kept, on that review's judgement that a three-word question copies no expression — a
  judgement, not a measurement, so it is put to the owner in #51's thread rather than settled here.
- **The disclaimer ships everywhere** — README, and `docs/RELEASE_NOTES_TEMPLATE.md`, which is the body of every
  release, quoted verbatim: "OpenSimAnt is an unofficial reimplementation of SimAnt (Maxis, 1991). It is not
  affiliated with, endorsed by, or sponsored by Electronic Arts. It ships no original Maxis assets."
- **The name keeps the mark, and that is accepted.** The project is OpenSimAnt — the OpenRA/OpenXcom rung, not
  OpenTTD's: the original mark stays inside the name, and the owner recorded and accepted that on 2026-11-09 (#22).
  What carries it is mitigation rather than a rename of the name: a **plain-text wordmark**, never typeset, kerned
  or otherwise styled like the SimAnt logo, and the disclaimer above in the README and every release note. **#36**
  is the text/identity pass — in-game strings, window title, asset names that still carry the original archive's
  naming — not a rename of the name.
- **No money changes hands.** Nothing is sold, no donations, no ads.

**What reopens this decision:** monetisation of any kind, a takedown or a letter, download volume that attracts
attention, or contributor PRs that want to ship original data. Say so here before acting on any of them.

## 3. What goes public, and in what order

| Artifact | State now | When it changes |
|---|---|---|
| The dev log site (`jbesse.me/SimAnt-Evolved`) **and the published Python reference port** | **public** | stays public |
| The repository | private | public **after #36** (text/identity pass) |
| Release downloads | private (needs a GitHub account) | after the repository is public |

**The site is deliberately public**, and it already was before this decision: GitHub Pages publishes `/docs` from a
private repo publicly, which is a default rather than a choice, so the owner confirmed it as the intended state. It
carries the dev log and the 89 generated reference pages — the port's own source, no original art, text or data —
and it is the project's only public-facing channel.

**The repository waits for #36** because the repo is what carries the trace fixtures, the extracted tables' shape
and the working documents; the text/identity pass is the thing that makes it read as a reimplementation rather
than a copy, and doing it first costs one night.

## Checking the mitigations still hold

Each command prints a number to compare against the one in the comment. A run that prints **zero** has measured
nothing and is a failure, not a pass — so read the output, not the exit code.

```bash
python3 tools/clean_pack/build.py                          # 810 clean files, 0 still missing
grep -c "unofficial reimplementation" README.md docs/RELEASE_NOTES_TEMPLATE.md   # 1 and 1

# The similarity numbers need the player's own copy extracted into `extracted/` first
# (tools/extract.py reads SIMANT.EXE and its archives, so it cannot run on a fresh clone).
# Without that directory this prints "## strings: 0 lists measured" and exits 0.
python3 tools/review/similarity.py strings                 # 107 lists measured, 70 of 518 identical (69 after #51)

# `gh release view --json assets` reports only name and size, so open a package instead.
gh release download v1.0.0 --pattern '*linux*.tar.gz' --dir /tmp/osapkg --clobber
tar -tzf /tmp/osapkg/*.tar.gz | grep -E 'LICENSE(-ASSETS)?$'   # OpenSimAnt/LICENSE, OpenSimAnt/LICENSE-ASSETS
```
