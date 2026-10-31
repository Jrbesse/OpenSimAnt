# UI bitmaps (clean pack): all four passes (74 pictures)

Made from `docs/clean_pack/ui_bitmaps.md` (groups A to L: all 74 pictures; passes 1-2 = A, B, C, D, E, H; passes 3-4 = F, G, I, J, K, L). One file per
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
| `grp_fg.py` | group F (Behavior Control 4600, Caste Control 4620, overlays 4601 / 4621: shared panel and overlay builders driven by the `CFG` rectangles) and G (History 16000, overlay 16001) |
| `grp_ijkl.py` | group I (win screen 16200 and the three eye frames 16210..16212), J (tutorial pictures 17000..17013), K (encyclopedia strips 21004, 21005), L (neutral start-up cards 28000, 28003) |
| `preview.py` | `preview.png`: contact sheet at 2x, the Edit, Map, Behavior Control, Caste Control and History windows assembled with their overlays (over a brown check standing for the map), Status, Game Over, the popup, the win screen with the six eyes (frames 0, 1, 2 alternating) in place, and every inverted rectangle next to its normal state |
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

## Passes 3-4: decisions

* **Corner boxes (4600 / 4620).** The spec's value rectangles touch or lie on the edge of the hit rectangles, so a 2-px
  frame cannot fit inside them. The 2-px frame in the bar colour (8, 11, 7 / 4, 6, 2) hugs the white value rectangle and the
  label zone and may lie 1-2 px outside the hit rectangle (left of the 4600 top box, below the 4620 boxes, 1 px above all
  of them); the hit rectangle itself is always covered. Labels use the **small face** (the label face is too wide: `Forage`
  needs 35 px of the 32 available). Labels sit in the first rows of the white label zone so that descenders (`g`) stay out
  of the value rectangle.
* **Triangle.** Computed per pixel from signed distances to the three sides of the spec's triangle (apex at the top
  middle, base corners 2 px in from the rectangle's lower corners): flat white inside, 1-px black line, then a 3-px
  edge (white left, 13 / 14 right and bottom). The check flood-fills the white interior and compares it with the triangle
  grown / shrunk by 2 px.
* **Bar well.** The white strip with the three letters (`F D N` / `B W S`, small face) continues the well down to y 92,
  inside one frame; the gauge rectangle itself is flat white.
* **Overlays 4601 / 4621** are built from the panel rectangles minus the overlay origin. Leader tips for the buttons sit
  2 px right of the buttons' right edge (spec: 3 px tolerance), the bar callout overlaps the bar rectangle, the corner-box
  panel is between the two lower boxes with outward arrowheads whose tips are inside the boxes' white value halves. All
  content stays inside 164 x 164 / 169 x 169.
* **History 16000.** Ten captions in the label face: `Pop`, `Food`, `Health` (both rows), `S.Food`, `Hunger` (starved),
  `Eaten`, `Killed` (`Starved` is 41 px, wider than the 38 allowed). All black (inversion rule). Dividers at x about 180
  (between the colony buttons and the four others, the spec's "x about 281" would split the four from the help button; a
  second one is drawn there too). 16001 uses staggered **two-line rotated panels** 22 px wide (spec allows at most 22).
  The two lower-row leaders run at x 182 / 230 so that they pass beside the button caption above.
* **Win screen 16200.** Person (left), cat (upper right, on a tree) and dog (lower right) with a white flag, no ant and
  no yellow at all. The 13 x 13 squares at the six given positions hold only the creature's flat face colour and a plain
  white socket (asserted); everything else (brows, nose, mouth) is outside them. Eyes 16210..16212: the same 24-pixel corner
  mask (rows 0-2 inset by 3, 2, 1 at both ends), black ring, pupil medium, then small with many red veins, then medium and
  shifted with a grey lid shadow, so 0, 1, 2, 0 reads as a trembling panic.
* **Tutorial pictures.** 17005 / 17008 / 17009 / 17011 / 17012 are crops of 14000 made by script and asserted equal (17012
  includes a 1-px face ring, the toolbar has none). 17006 / 17007 are plain bevelled buttons (house, surface) that a later
  batch may replace by crops of its own toolbar. 17010 has the same two wells as 14000's report (64 x 8 and 64 x 5, black
  frame, black fill).  17000 reuses `pics.ant_top` in yellow with a black outline (5103's ant in the player's colour).
* **Encyclopedia strips.** 1 plane, checkerboard `f` where x + y is even, black first row, white boxes (outline x 16..81,
  y 3..17 for BACK) with a 1-px black shadow right and below, label face captions.
* **Start-up cards.** Black, a seven-hexagon flower (own design, drawn at each size from the card's height, not scaled)
  and one line, `AN OPEN FAN PROJECT`, in the small face at 2x with yellow face and two shadow steps (orange, red).
