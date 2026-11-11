# Publication: licence, legal position, and what goes public

**Decided 2026-11-11 by the owner** (issue #22). Three decisions, and the conditions that keep them true.
This file is the answer to "can this be published?"; the roadmap's Track C points here.

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
- **No original text.** The A5 review measured every string: 70 of 518 entries identical, all functional labels
  (castes, view names, "Nothing") except one advisor line, which is #51.
- **The disclaimer ships everywhere** — README, and `docs/RELEASE_NOTES_TEMPLATE.md`, which is the body of every
  release: "OpenSimAnt is an unofficial reimplementation of SimAnt (Maxis, 1991). It is not affiliated with,
  endorsed by, or sponsored by EA. It ships no original Maxis assets."
- **A distinct name.** The project is OpenSimAnt; the repo is SimAnt-Evolved. The rename/text pass is #36.
- **No money changes hands.** Nothing is sold, no donations, no ads.

**What reopens this decision:** monetisation of any kind, a takedown or a letter, download volume that attracts
attention, or contributor PRs that want to ship original data. Say so here before acting on any of them.

## 3. What goes public, and in what order

| Artifact | State now | When it changes |
|---|---|---|
| The dev log site (`jbesse.me/SimAnt-Evolved`) **and the published Python reference port** | **public** | stays public |
| The repository | private | public **after #36** (rename/text pass) |
| Release downloads | private (needs a GitHub account) | after the repository is public |

**The site is deliberately public**, and it already was before this decision: GitHub Pages publishes `/docs` from a
private repo publicly, which is a default rather than a choice, so the owner confirmed it as the intended state. It
carries the dev log and the 89 generated reference pages — the port's own source, no original art, text or data —
and it is the project's only public-facing channel.

**The repository waits for #36** because the repo is what carries the trace fixtures, the extracted tables' shape
and the working documents; the rename and text pass is the thing that makes it read as a reimplementation rather
than a copy, and doing it first costs one night.

## Checking the mitigations still hold

```bash
python3 tools/clean_pack/build.py                     # 810 clean files, 0 missing
grep -c "unofficial reimplementation" README.md docs/RELEASE_NOTES_TEMPLATE.md   # 1 and 1
gh release view <tag> --json assets                   # packages carry LICENSE + LICENSE-ASSETS
python tools/review/similarity.py strings             # 69 identical after #51 lands
```