# A5 — similarity review of the clean pack against the original

The last job of area A5 (`docs/ROADMAP.md`): before v1 calls the clean-room pack finished, compare what it ships
with what the original draws, plays and prints, and record a verdict per area with the evidence it read.

**Verdict: the pack is similar in shape and structure, and not a copy — with three exceptions that are filed as
issues below (one copied text line, one font whose glyphs are too close, and a rule gap for the assets whose form
is fully specified by measurement).** No area fails on this evidence. What this review can *not* judge is how the
audio sounds: the pack's songs and effects are structurally right and textually new, but the audible comparison is
the owner's (`#21`) and the tooling for a spectral one does not exist yet (`#35`).

Session: nightly session 3, 2026-11-11. Branch `nightly/2026-11-11-20`.

## What was read

The review is downstream of the four check rows the issue named as its blocker; all four closed on 2026-11-07/08
with numbers, and those numbers are the base this review re-measures against:

| Issue | Job | Closed | What it left |
|---|---|---|---|
| #18 | B15 reference captures | 2026-11-08 | a 37-capture font-present set in `tools/re/build/screens`; `screens.py` now refuses to record without `extracted/shared/font/` |
| #17 | B14 modals from the State | 2026-11-08 | 31 / 33 / 4 restored from the State alone, 29 via the `.cell` sidecar, 22 documented as the `--file-dir` path |
| #16 | B16 surface 256 px | 2026-11-08 | re-measured against the new set: unchanged, one simulation step of the original's paint lag |
| #15 | B17 yardfront 3424 px | 2026-11-07 | fixed to 2 px; the residue is **#29**, still open |

Two residuals were already open and are not re-filed: **#25** (`yard` 9 px at (264,195)) and **#29** (`yardfront`
2 px at y=83) — both P3 and both reproduced below.

## How it was measured

Two oracles, both re-run in this session on this box:

```bash
# the pack's assets against the original's, per asset (new tool, no original pixels leave the machine)
python tools/review/similarity.py --json=/tmp/sim_all.json

# the pack drawn by the remake against the original's own captures, per screen
cd tools/re && xvfb-run -a ~/work/simant-venv/bin/python compare_screens.py --godot="$GODOT"
```

`tools/review/similarity.py` is new here and committed with this review so every number below can be re-derived:
it decodes each original bitmap / font / effect / song and compares it with the clean source that replaces it.
Bitmap identity is compared on **palette indices**, not RGB, because the pack's 16 colours are the Macintosh set
and the original's are EGA — equal colours across the two are coincidences, not evidence.

## Bitmaps — PASS

- **252 / 252** type-2 bitmaps measured: sizes match the measurements exactly (`build.py` refuses anything else).
- Identical pixels: **median 0.360**, mean 0.400. Silhouette IoU: **median 1.000** — the pack draws the same
  shapes in the same places, with its own colours.
- `identical` counts both-transparent pixels as a match, which inflates it for mask-heavy sprites; the tool also
  prints **`drawn`**, the same agreement over the drawn union only, and that is the column to rank copies by.
  It changes nothing in the six findings below (all six are opaque), but e.g. `HCEGANT/1050` reads 0.762
  identical against 0.061 drawn — background, not art.
- **6 assets are pixel-identical**, and every one is geometry the spec states outright rather than art:
  `7021`, `7022` (512x55 lattice strips, drawn from the spec's line spacing), `7020` (0.975, the same), `8905`
  (a solid colour-15 rectangle), `7006`, `7007` (one opaque pixel each), `7005` (a 1-pixel raindrop line, 4 px of
  slope over 35 rows). `5002` is close (0.914) but its two-colour separator bar is likewise a stated measurement.
  A lattice that had to be redrawn differently would no longer overlay the original's grid, so this is the
  fidelity rule winning over the clean-room rule — see #53.
- **Screens** (`compare_screens.py`, 36 captures, remake vs the original's own memory-rendered capture):
  **29 are 0 of 307200 px.** The seven that differ:

| capture | px | region | reading |
|---|---|---|---|
| `surface` | 256 | (476,94)..(568,238) | the documented one-step paint lag (#16); terrain matches exactly |
| `gameover` | 144 | (84,194)..(168,302) | map art left of the box; the box itself identical — recorded in #18's closing comment |
| `yard` | 9 | (264,195)..(289,200) | **#25**, still open |
| `yardfront` | 2 | (63,83) and (575,83) | **#29**, still open |
| `filedlg` | 989 | (170,125)..(266,162) | the dialog lists the real directory — not comparable while the recording and the render see different files → #54 |
| `editfront`, `popup` | 32 each | (432,102)..(439,109) | the same 8x8 block in both: 16 px light-grey vs black swapped, a 50 % stipple drawn in the other phase → #55 |

## Layouts — PASS

- The window layout table (34 layouts, `HCEGANT/0`) decodes and encodes back **byte-identical for all 34**, dead
  bytes included; the three UI tables (128 / 129 / 131) are byte-identical too.
- The stacks restore from `DS:5702` (#17), and every stack capture except the four residuals above is 0 px — the
  windows are in the original's places, at the original's sizes, in the original's z-order.
- Menu bars, captions and borders are part of those 0-px screens, so the layout work is verified by rendering,
  not only by the encoder.

## Text — PASS with one line to rewrite

- **107 lists compared** with the original's own lists; entry counts match in 106. The exception is list `1700`
  (the credits), which `docs/clean_pack/strings.md` defines as variable-length by design.
- **70 of 518 entries are identical to the original's**, and they are all labels, placeholders or UI fragments,
  never prose. The distribution, by list (counts from `similarity.py strings --json=/tmp/s.json`):

  | list | identical | what they are |
  |---|---|---|
  | `1102` | 18 | 6 activity labels — "Foraging", "Hatching", "Fighting", "Alarmed", "Resting", "Flying" — and 12 `???` |
  | `1103` | 16 | the `Nothing` / `Food` / `Dirt` carry cycle |
  | `1101` | 13 | castes — "Worker" x3, "Soldier" x3, "Male", "Replete", "Queen" x2 — and 3 `?` |
  | `1000` | 7 | view names, "Surface View" through "Graphic View" |
  | `1800` | 6 | 3 empty strings, "Overall ", " Score" and " - " on the score screen |
  | `1001` | 3 | "Quick Game", "Full Game", "Experimental" |
  | `1050` | 2 | "Eaten", "Killed" |
  | `1100` | 2 | "New Egg", "Egg" |
  | `1010` | 1 | "Pause" |
  | `1240` | 1 | "Where am I?" — see below |
  | `1020` | 1 | the verbatim prose line under #51 |

  Every one is a fixed slot in the original's own screen — a label, a placeholder or a separator — so the 1:1
  rule's expected outcome is for it to read the same.
- **One prose line is verbatim the original's**: list `1020`, entry 5 (27 characters, "The red ants are attacking!").
  That is a clean-room breach by the pack's own rule → **#51**.
- **One 11-character balloon line is also verbatim**: list `1240`, entry 0 ("Where am I?"). It is recorded here
  rather than rewritten: a three-word question with no distinctive wording is the ordinary way to ask it, and this
  review's judgement is that it copies no expression — but that is a clean-room judgement, not a measurement, so
  it is put to the owner in #51's thread instead of being silently kept or silently changed.
- Length fit: **52.5 %** of entries are within 0.80–1.25x the original entry's length. The rest are longer or
  shorter new writing; the ones that must fit a fixed cell are checked by the pack's own layout validator
  (`build.py`'s `layout_text_problems`), and the 0-px menu screens show the menu labels land where they should.

## Fonts — PASS with one font to look at

Per font: glyphs compared, glyphs pixel-identical to the original's, ink ratio (pack ink / original ink):

| font | glyphs | identical | share | ink ratio |
|---|---|---|---|---|
| 0 (PC 8x15, menus) | 94 | 4 (`H I o x`) | 4.3 % | 0.96 |
| 1 (PC 10x7) | 126 | 5 (`" + - . I`) | 4.0 % | 0.65 |
| 2 (proportional sans) | 221 | 6 | 2.7 % | 0.51 |
| 3 (bold sans) | 221 | **30** | **13.6 %** | 0.43 |

Fonts 4 and 5 are Apple `FONT` resources the tool does not decode through this path (`extracted/shared/font/`
has no `00004.bin`), so their glyphs are not measured here; their screens (`card`, `exp`, `popup`) are 0 px apart
from the stipple block. Font 3's 13.6 % — digits `0 2 5 6 8 9` and `B H O` among them — is higher than a redrawn
face should reach → **#52**. Advances are exact by construction (`font<n>.json` is the measurement), which
is what keeps the text in the original's cells.

## Sound — structurally PASS, audible judgement not made here

- **35 / 35 effects** exist and every duration equals the measurement to the millisecond (that is the spec: the
  length column *is* the requirement).
- Envelope correlation with the original: **median 0.210**, range -0.196..0.976. Two sit high — `sfx 4` (0.906)
  and `sfx 40` (0.976); both are short percussive hits, where amplitude envelopes necessarily agree. This is not
  evidence of copying and it is not evidence of fidelity: an envelope has no pitch or timbre in it.
- The 17 FM patch fields and the 2856-byte sound bank are byte-identical through the encoder (`build.py
  --roundtrip`), so the driver-facing side is exact.
- **This review cannot say the pack sounds like the original.** A waveform or spectrum comparison needs both
  sides rendered through one mixer — that is **#35**, still open — and the verdict of whether an effect *reads*
  as the right effect is the owner's listening pass, **#21**.

## Music — structurally PASS, melody verifiably new

- **30 / 30 songs** measured against the original's MIDI: **0 exact (pitch, start, length) note triples match in
  any song**. Whatever else is true, no melody was copied.
- Note counts run 0.905x..1.893x the original's, inside the spec's 50–200 % band; tempo is deliberately the
  composer's choice (`music.md` calls the pace column "a guide, not a rule"), so the differs-per-song BPM is
  expected and not a finding.
- Octave-histogram cosine **0.277..0.984** — the pack uses the same registers and the same channel roles; the low
  outliers (`20011` **0.277**, `11007` 0.447, `10010` 0.451, `20010` 0.474, `20001` 0.480) are the short
  stingers, not the themes. (`20009` has no pitch content on one side, so it has no cosine and is excluded.)
- The sequencer port, cue table and lengths are checked by `build.py --roundtrip` against the original's songs.
  Audibility is again **#21**; a mixed-down comparison is **#35**.

## Findings filed with this review

1. **#51** — a copied advisor line: list `1020` entry 5 is verbatim the original's.
2. **#52** — font 3 is too close to the original's: 30 of 221 glyphs pixel-identical, digits and capitals included.
3. **#53** — the clean-room rule has no class for "geometry the measurement fixes": six bitmaps must be identical
   and are correct; the rule as written ("anything too close is remade") would condemn them.
4. **#54** — the file dialog's capture is not reproducible: it lists the real directory, so the pair only compares
   while the recording and the render see the same files (989 px).
5. **#55** — a 50 % stipple is drawn in the wrong phase: 32 px, the same 8x8 block at (432,102) in `editfront`
   and `popup`.

## The gate this review ran on

In `remake/`, before its commits:

```
dotnet build OpenSimAnt.sln -c Release                0 errors / 3 addon warnings
dotnet test tests/OpenSimAnt.Sim.Tests -c Release --no-build   169 passed, 0 failed
dotnet run --project tests/OpenSimAnt.Replay -c Release --no-build -- --quiet   26 files / 229778 calls, ALL OK
```

Traces are gitignored and machine-local, so the file count is whatever the box has recorded; the call total is
the stable figure. On the reviewer's box the same sweep ran 26 files to the same 229,778 calls.

## What the review does not claim

- It does not claim the pack is indistinguishable from the original. Its verdict is "similar in shape, new in
  substance", with the exceptions above.
- It does not judge audio by ear; the listening pass is the owner's.
- It does not re-open the closed check rows. Their numbers were re-measured here and agree.
