# Publication decisions

The record of every decision that goes with making this repository public, made by the owner
(2026-11-15, this session). This file is the thing a later session re-checks instead of re-litigating:
each decision carries the conditions that keep its risk bounded, as commands that prove them, and the
triggers that reopen it. It is excluded from the Pages build on purpose.

## The decisions, as made

1. **Name: "OpenSimAnt" is kept.** It carries the original's title, which is the riskier-but-precedented
   rung (OpenRA, OpenXcom, OpenLoco, OpenTTD have lived on it for a decade or more). The two mitigations
   that make it defensible are in the tree: a **plain-text wordmark** (the title screen's name is flat,
   single-colour text since v1.0.1 — never typeset or styled like the original's logo) and an explicit
   **"unofficial, not affiliated with or endorsed by Electronic Arts"** line in the README and in every
   release body.
2. **Licence split, two files:** code is **MIT** (`LICENSE`), the clean asset pack is **CC BY 4.0**
   (`LICENSE-ASSETS`), both shipped inside every release package since #34. One licence over both is
   always wrong for a game; this is the split.
3. **The reverse-engineered reference is published on purpose.** `simant_ref` (the line-by-line Python
   translation), its module docs under `docs/reference/`, and `simant_ref.zip` are on the dev log site
   and in this repository, offered as "usable by anyone." The owner decided to keep it public (2026-11-15)
   after the options (keep / strip / stay private) were laid out with their costs. It contains nothing
   extracted from `SIMANT.EXE` — it reads the player's own copy at runtime — and the C# port and the
   clean pack stand independently of it.
4. **No external legal opinion.** The owner declines a paid review and accepts the precedent posture as
   it stands (2026-11-15): if EA or Maxis ever intervenes, he deals with it directly at that time. This
   record, not an opinion letter, is the diligence artifact.
5. **The game's data tables in source (ROADMAP A2):** ~1.2 KB of gameplay numbers committed as named,
   documented tables, the owner's own decision of 2026-10-30. Numbers only — never art, text, sound or
   fonts. Recorded here as part of the accepted posture.
6. **The clean pack's audio is accepted** by the owner's listening pass on the Nov 12 render
   (2026-11-15, #21 closed). Known accepted differences stand: AdLib mode is not modelled.
7. **Publication order:** the repository flips public first; binaries are not a fresh publication —
   v1.0.0 and v1.0.1 were cut from master while the repo was private, and flipping changes who can see
   them, not what they are. The repo flip has an undo button; a published binary does not, which is why
   nothing new ships at the flip.

## The conditions that keep the risk bounded (run them, don't argue them)

- **No original Maxis material is tracked, now or in history:**
  `git ls-files | grep -iE '\.ndx|\.dat$|simant\.exe|/extracted/|hcegant'` returns nothing
  (full history scan done 2026-11-15: zero original files were ever committed).
- **The disclaimer is present:** `grep -c "not affiliated with, endorsed by, or sponsored by" README.md`
  is at least 1, and the same line is in the latest release body (`gh release view <latest> --json body`).
- **Both licences are at the root and in every package:** `LICENSE` (MIT) and `LICENSE-ASSETS`
  (CC BY 4.0) exist in the tree and in each release's three downloads.
- **The pack is clean-room, measured not asserted:** every batch has an entry in
  `remake/game/assets/clean/PROVENANCE.md`, and the similarity review's verdict with its pixel/byte
  evidence is `docs/A5_SIMILARITY_REVIEW.md`.
- **A tag is a release, never a pre-release:** `gh release view <tag> --json isPrerelease` is `false`.
- **The wordmark stays plain:** the title screen's name is flat single-colour text (verified against the
  shipped build, not the repo).

## What reopens this

Any one of these re-opens the relevant decision, and the owner re-makes it — a later session does not:

- A takedown, C&D or any other intervention from EA, Maxis or a rights holder.
- Monetisation of any kind: ads, donations, paid builds, a store listing.
- A contributor PR that ships original data (art, text, sound, fonts, or extracted bytes) into the pack
  or the source.
- Download volume or attention that invites scrutiny (a threshold the owner sets when it comes up).
- Any change that adds original material to the tree, or drops one of the mitigations in decision 1.

## The mechanics around the flip

- The repository was renamed `SimAnt-Evolved` → `OpenSimAnt` on 2026-11-15, before anything goes public;
  GitHub redirects the old URL, and the pipeline (registry, release script, state, clones) points at the
  new slug.
- The dev log's home on `jbesse.me` is decided separately (the domain is shared with the owner's blog);
  when it lands, the new address goes here and the ROADMAP row is reticked.
- The flip itself is the owner's action. Nothing in this repository publishes on a push: releases cut on
  a schedule from tags, and the repo being public only changes who can see what already exists.
