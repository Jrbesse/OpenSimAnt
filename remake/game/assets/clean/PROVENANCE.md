# Provenance of the clean pack

Every asset in `src/` was made new from a written spec in `docs/clean_pack/`, by a maker who did not see the
original game's files (docs/ART_PLAN.md sections 2 and 9). Each batch adds an entry: date, maker, spec (file and
commit), the files made, and the script that makes them (kept beside them, so every asset can be regenerated).

| Date | Maker | Spec | Files | Made by |
|---|---|---|---|---|
| 2026-10-30 | agent (isolated, spec only) | docs/clean_pack/cursors.md @ 10f6736 | src/cursors/0.pix, 1.pix | src/cursors/make_cursors.py |
