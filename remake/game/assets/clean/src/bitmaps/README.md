# UI bitmaps (clean pack): passes 1 and 2

Made from `docs/clean_pack/ui_bitmaps.md` (groups A, B incl. B2, C, D, E, H: 46 of the 74 pictures). One file per
bitmap, `HCEGANT_<id>.pix`, written by `make_ui_bitmaps.py`:

```
python make_ui_bitmaps.py      # writes the .pix files, runs every check as an assertion, writes preview.png
```

Needs Python 3 with numpy (always) and Pillow (preview only).

## Files

| File | What |
|---|---|
| `uilib.py` | the shared helper: `Img` (numpy canvas: rect, frame, line, poly, ellipse, blit, crop), `bevel`, `chrome_button`, `well`, `groove`, `tri`, the two pixel faces, `text` / `text_c` / `text_r` / `text_rot`, `wrap` (with `**bold**`), `callout` / `callout_rot` / `leader` (help overlays), the inversion test (`inv_ok`, `contrast`), `Reg` (registry of pictures, flat rectangles, icon spots, leader tips, inverted rectangles, checks), `run_generic_checks`, `write_pix` |
| `pics.py` | the shared **subjects**, each drawn once: surface, nest cut-away, ants (top, side), larva, spider, queen on soil, the five scent pictures, alarm bulb, path, graph, house with lawn, card; `pic_button` wraps a picture in a bevelled button |
| `grp_abc.py` | group A (100..113), group C (5100..5107), group B (menus, palettes, notices, the three help pages) |
| `grp_deh.py` | group D (15000 + overlay 15001), E (14000, overlay 14001, popup 14002), H (13000, 16100) |
| `preview.py` | `preview.png`: contact sheet at 2x, the Edit window and the Map window assembled with their overlays (over a brown check standing for the map), Status, Game Over, the popup, and every inverted rectangle next to its normal state |
| `make_ui_bitmaps.py` | the driver: the `GROUPS` list, the checks, the writing |

## The look

A flat, bevelled desktop style in the 16 colours, light from the top-left. Panel face and window background light grey
12; raised things have a white 0 highlight on the top and left and a medium grey 13 shadow on the bottom and right
(2-px frames, e.g. the Status and Game Over panels, add dark grey 14 outermost); sunken things (the population report) swap
them. Wells (counts, gauges, graphs, text) are flat white 0 with a 1-px frame drawn **outside** the rectangle the game
writes into. Window-chrome buttons and menus have a black 15 outline; menus and cards add a 1-px bevel ring inside it.
Colony colours as in the sprites: black colony = black / dark grey, red colony = red 3, the player = yellow 1 (with a
black outline on a light ground). Green 9 is the "?" glyph and the P / H letters of the population report.

**Lettering** (own 5 x 7 pixel faces, `uilib.py`): the **small face** is a regular proportional face (capital height 7,
x-height 5, descenders 2, 4-px lowercase, 4-px digits, 5-px capitals), used for help callouts, pages, headings, the
option palettes. The **label face** is the same glyphs emboldened (each stroke smeared 1 px right), used for buttons, menu
entries, window labels and the big titles; `LABEL_TALL` is the label face with one row repeated (capital height 8) for
the tool palette. Titles are the label face scaled 2x with a shadow. Rotated text (`text_rot`) reads bottom to top.

## Colour roles (constants in `uilib.py`)

`FACE` 12 faces; `WELL` 0; `HI` 0, `SH` 13, `DSH` 14 bevels; `INK` 15 outlines and lettering of anything the game inverts;
`HEADING` 6 headings that are not inverted (cards, notices, window column heads); `BLACKCOL` 15 / `REDCOL` 3 / `PLAYER` 1.
Overlays use only 0 (panels), 14 (frame, text) and 6 (leaders). The soil is tan 11 / brown 10.

## The inversion rule (and one deliberate deviation from the spec)

The game inverts selected rectangles (`c XOR 15`). Every inverted rectangle is registered with `reg.inverted(id, rect,
face, ink)`; the script asserts that `face` is the most frequent colour in the rectangle, that `ink` occurs in it and
that `face`/`ink` have a contrast of at least 3:1 both as drawn and inverted (`uilib.inv_ok`). **Blue 6 lettering on
light grey 12 fails this** (inverted it is dark green 9 on red 3, 1.4:1), and so do red 3 and brown 10 words. The spec
asks for blue / red / brown menu words *and* the 3:1 check for group B, so the check wins: all menu, palette and button
lettering is black 15 (inverts to white on red). The colours the spec wanted survive as decoration (badges, swatches).
`uilib.MENU_COLOURED = True` switches the spec's blue / brown words back on in `grp_abc.py` (the check will then fail).
Pictures inside inverted buttons use a light-ish face (tan 11, white, light grey) with black ink, never dark soil.

## How to add a group (passes 3 and 4)

1. Write `group_f(reg)` (a function of the registry) in a new module, e.g. `grp_fgijkl.py`; draw with `uilib` / `pics`.
   Register each picture: `reg.add(id, img, (w, h), masked=False, colours=None, what='...')` (`colours=(0, 6, 14)` for an
   overlay, `(0, 13, 15)` for the help pages, `masked=True` for a picture with `.`; transparent = `uilib.T`, create with
   `Img(w, h, T)`).
2. Register what the checks need: `reg.flat_rect(id, rect, colour)` for every **text rectangle / gauge**, `reg.spot(id, rect)`
   for icon spots (flat 12), `reg.inverted(id, rect, face, ink)` for every inverted rectangle,
   `leader(img, reg, id, name, [pts...], target_rect)` for every leader (the last point is the tip, asserted inside the target;
   `tol=3` where the spec allows 3 px), `reg.check(fn)` for anything else (`fn(reg)` asserts on `reg.img[...]`).
3. Add it to `GROUPS` in `make_ui_bitmaps.py` (after any group whose pictures it reuses), run the script, run
   `python tools/clean_pack/build.py` and look at `preview.png` (add the new windows to `preview.make`).

Callouts: `callout(img, x, y, lines)` (13 px high for one line, +10 per extra line, 1-px 14 frame, 14 text on 0);
`callout_rot(img, x, y, text, h=...)` is the 12-px wide rotated panel (a wider rotated panel: draw the frame yourself and use
`text_rot`). The Edit / Map overlays keep their leaders axis-aligned or straight and 1 px thick.

## Decisions on ambiguous spots

* **5000 is 97 x 143**: the spec's size column says 96 x 142 (window 97 x 143) but `tools/clean_pack/build.py` rejects
  anything but 97 x 143, so the picture is 97 x 143 (frame at its edge; the entry rectangles are as in the spec).
* Option palettes 5001..5006 use the **small (regular) face**: "20 pieces" must fit 44 px, which the emboldened face cannot.
* 5000's labels are mixed-case (as the spec lists them) in the tall label face (capital height 8), black (see above).
* Scent-menu words are black; the colony is shown by the swatch frame (black / red) instead of by the word's colour.
* 14001: the callouts for the two gauge rows are two panels (`Population`, `Health`) above the report with two leaders
  each (all vertical), not panels on the report; the report sentence has a bracket along the top of the report area.
* 15000: bevels of the Experimental button lie outside its flat 18 x 18 rectangle (so the whole rectangle is flat 12); the
  other pictorial buttons carry the bevel inside their rectangle. Black-colony pictures have a black 15 frame, red-colony
  pictures a red 3 frame (outermost pixel) inside the rectangle.
* The close box 100 is a plain X; 113 is the same X in red 3 on yellow 1.
