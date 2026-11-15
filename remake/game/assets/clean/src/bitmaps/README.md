# UI bitmaps (clean pack): all four passes (74 pictures)

Made from `docs/clean_pack/ui_bitmaps.md` (groups A to L: all 74 pictures; passes 1-2 = A, B, C, D, E, H; passes 3-4 = F, G, I, J, K, L). One file per
bitmap, `<id>.pix`, written by `make_ui_bitmaps.py`:

```
~/work/simant-venv/bin/python make_ui_bitmaps.py   # writes the .pix files, runs every check as an assertion, writes preview.png
```

Needs Python 3 with numpy (always) and Pillow (preview only) — install the pair from `../requirements.txt`. The
system `python3` on the Hermes box has neither, so every command in this README runs with the venv interpreter
`~/work/simant-venv/bin/python` (from this directory); on a fresh checkout, create a venv from that file and use
its interpreter instead.

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


---

# Yard bitmaps (clean pack): passes 1-2 (12 pictures so far)

Made from `docs/clean_pack/yard_bitmaps.md` (114 pictures in 5 passes; this is **pass 1: the scenery, groups A and C** and
**pass 2: the toolbar, group D**). One file per bitmap, `<id>.pix`, written by `make_yard_bitmaps.py`:

```
~/work/simant-venv/bin/python make_yard_bitmaps.py            # writes the .pix files, runs every check as an assertion, writes preview_yard.png
~/work/simant-venv/bin/python make_yard_bitmaps.py --crops    # only: replace 17006 / 17007 (if they exist) by crops of 7010
~/work/simant-venv/bin/python make_yard_bitmaps.py --no-preview
```

Needs Python 3 with numpy (always) and Pillow (preview only). The yard modules import `uilib.py` of the interface batch
(`Img`, `Reg`, the two pixel faces, `bevel`, `groove`, the contrast maths), which must stay in this folder.

**Made so far:** 7000, 7001, 7003 (the yard window's pictures), 7020, 7021, 7022 (the colony views' grid strips), 7005 (raindrop),
7006, 7007 (the queens' dots), 1260 (the for-sale sign), 7010 (the toolbar), 7011 (its help overlay). **Crops:** 17006 and 17007 are crops of
7010 (the House button's box and the Patch button's box); the script writes them **only if they already exist** (it said so
when it ran); if the interface batch is run later, run `~/work/simant-venv/bin/python make_yard_bitmaps.py --crops` afterwards.
**Not made yet:** passes 3 (the people E, the door / room patches B), 4 (the dog, cat, bird F, G), 5 (the spider H, the
map-window actors I): add a module `yard_pass3.py` ... with a `build(reg)` function and list it in `PASSES` of `make_yard_bitmaps.py`.

## Files (yard)

| File | What |
|---|---|
| `yardlib.py` | `lattice(x, y)` (the engine's lawn: 8 in the cells, 9 on the lines, `None` outside the parallelogram), `house_covers(x, y)` (the boundary the colony views mark), `G(s, y, z)` (the scenery's projection), `World` (one canvas in yard coordinates: polygons, lines, ellipses, `gbox` / `obox` boxes with inner outlines, clipping), `polygon_mask` |
| `yard_scene.py` | **the drawing program**: `draw_scenery` (garden, back fence, lawn), `draw_house_outside` (+ `draw_door`), `draw_house_inside` (+ `draw_fridge`, `draw_chair`), `render_world`, `pictures`, `strips`, `sign_board`; the constants `HOUSE_MASK`, `DOOR_RECT`, `CHAIR_RECT`, `FRIDGE_RECT`, `PERSON_PATH` |
| `yard_pass1.py` | pass 1: registers 7000, 7001, 7003, 7020..7022, 7005..7007, 1260 and their assertions |
| `yard_pass2.py` | pass 2: the toolbar 7010 (button pictures drawn once each), the overlay 7011, the crops, and their assertions |
| `preview_yard.py` | `preview_yard.png`: the yard window as the game shows it in the Yard, House, Strat and Graphic views (2x), the toolbar with its overlay, its inverted buttons, the sign, a raindrop and the two queens' dots |
| `make_yard_bitmaps.py` | the driver: the `PASSES` list, the checks, the writing, `--crops` |

## The look (scenery)

An isometric yard seen from above and in front: lawn lines run down-left at 45 degrees, the rows horizontally, light from the
top-left. **One drawing program** (`yard_scene.py`) draws the whole window as a single canvas in yard coordinates (canvas column =
yard x + 2): 7000 / 7001 are its columns 0..280 and 7003 its columns 281..513, so the seam cannot show. The ground is
`G(s, y, z) = (s - y, y - z)`: `s` is constant along a lawn line (x + y = s), `y` is the row, `z` a height. The house is a box on
the footprint s in [212, 288] with its back wall on y = 65, running on beyond the bottom of the picture; its long right wall
stands on the boundary x + y = 288 (the lattice line k = 2), the porch (s 286..316, y 65..115) holds the door in its front face
on y = 115. Cream-white and light-grey walls, a red (lit slope) and brown (shaded slope) hipped roof, a chimney, a skylight,
three windows on the long wall, a porch with a lean-to roof, a lamp and a brown door with two inset panels. The grey 13 beside and
behind it is the window background; the garden (two trees, bushes, a raised flower bed, a dog house, a coiled hose) stands on it, left of the
house, and the back fence (picket fence, posts every 28 px, a light plank on top at y = 38 for the cat, a flower bed at its foot,
two trees and shrubs behind it) runs from x = 250 to the right edge. **Nothing stands on the lawn**; the sign, mower and porch-lawn places are kept free of detail (asserted).

**The inside view (7001)** is the same program with the roof and the front wall left out: the floor (wood in the living room, a
white / grey check in the kitchen and the porch), the left wall's inner face (light grey, with a window and a picture), the back wall (white,
with a window), the cut tops of the walls, a floor slab edge on the boundary; the kitchen along the back wall (wall cabinets, counter
with sink and cooker, the refrigerator in **its rectangle yard (207,47)-(226,77)**, exactly 19 x 30), the living room along the left wall (bookcase, television
on its stand, a sofa, a rug) and the armchair in **(45,166)-(62,196)** (with a one-pixel floor ring all round). The person's route
(53,195) -> (100,161) -> (163,89) -> (198,89) runs over a floor band kept free of furniture (assert: at least 14 px; the nearest furniture is 16 px away).
Outside the house the two pictures are identical (assert), and 60 % of all their pixels agree.

**For pass 3 (the door and room patches):** render the scenes with the person drawn in through the hooks, then crop, never paint a patch
by hand (see the docstring of `yard_scene.py`):

```python
import yard_scene as ys
w = ys.render_world('outside', door=0.35, hooks={'behind': fn})      # fn(world) draws the person in yard coordinates
patch8900 = w.pic(172, 198)[73:115]                                  # 26 x 42; door 0.0 closed .. 1.0 wide open; hooks 'behind' | 'front'
w = ys.render_world('inside', hooks={'chair': fn})                   # 8200 = w.pic(45, 62)[166:196]
w = ys.render_world('inside', fridge_open=True, hooks={'fridge': fn}) # 8201 = w.pic(207, 226)[47:77]
```
(`World.pic(x0, x1)` returns the canvas columns of the yard x range as a numpy array, all 226 rows.) The niche's outermost ring is wall colour 0
in 7000 (asserted); the door, its frame and its step lie inside it, the step on the niche's last rows (nothing goes below y = 115, the lawn's line).

## The look (toolbar)

A light-grey 12 panel (white top row and left column, black bottom row), four picture buttons for the views, the mating group
(MATE, the queens count, the AUTO / MANUAL radio pair, PLACE), the `?` button and two colony counters; thin grooves between
the groups (x = 165 and x = 362). Picture buttons have a raised bevel **outside** their hit rectangle (box = rect grown 1 / 1 / 2 / 2: white
top and left, dark grey 14 and medium grey 13 at the bottom and right); the radios and the `?` have the bevel inside. Every picture has a
black 15 ring on its hit rectangle's edge (so inversion keeps it neutral). Pictures (each drawn once): **Patch** the ground from above (tan soil, food crumbs, ants, a pebble); **House** a front view of a house on its lawn
(white sky, black roof and outline); **Strat** the grid of patches in perspective with black, red, checkered and (two) green cells on white; **Graphic** the same grid with short
black and red bars; **MATE** a few winged ants in flight; **PLACE** a winged queen about to land on a dark ground. The inverted buttons
(House, Strat, Graphic, PLACE, AUTO, MANUAL) are drawn so that the two most frequent colours (and the dominant light and dark colours)
contrast at least 3 : 1 both as drawn and with every pixel XOR-ed with 15 (asserted; the Strat picture has only two green cells for that reason: green
as a dominant colour fails the inverted test). Labels (the interface batch's bold face, rows 35..41): Patch, House, Strat, Graphic, MATE, PLACE; `AUTOMATIC` does not fit 56 px (60), so the
button says `AUTO`. The text rectangles (queens, black colonies, red colonies) are flat white with a black frame **outside**.

**Overlay 7011** (masked, only colours 0, 14, 15): eight white callout boxes side by side from x = 0 to 363 (rows 10..46, 37 rows, 14 frame,
three or two short lines in the small face, each box centred on and wider than the middle 60 % of its button), two heading tabs
(`Views`, `Mating`) joined to the band's top edge, and the colony counters' box (x 443..511, rows 20..46). Every box ends on row 46 (a continuous dark line).

**Crops.** 17006 (37 x 29) = 7010 pixels (45,4)-(82,33); 17007 (41 x 30) = 7010 pixels (4,3)-(45,33): no label ink in either (labels start at row 35).

## Checks (asserted by `make_yard_bitmaps.py`)

Sizes, masks and colours of all 12 pictures; the raindrop (one pixel per row 1..35, colour 7, column 5 -> 1), the queens' dots, the
sign (tight, both sides of the post transparent, two lines of lettering in two colours); the frame (black left column, top row, 7003's right column; row 1 = 13); **every visible lawn pixel of 7000, 7001, 7003 equals
`lattice()`** (the house hides the rest; no lawn colour peeks out), the seam columns; the strips equal `lattice()` over 13 plus the colour-10 house line and contain only 8, 9, 10, 13; 7000 / 7001
identical outside `HOUSE_MASK` and at least 55 % identical; the niche ring, the fridge and chair rectangles; the free places (sign, porch lawn, mower's place); the person's route; text rectangles flat white; labels
(start on row 35, never touch each other, panel below the buttons); box bevels; the 3 : 1 inversion test; the crops (windows contain the boxes and end above the label); the overlay's colours, boxes (end on row 46, cover the
middle 60 % of their buttons, no gaps in the left group, the text fits) and tabs. `python tools/clean_pack/build.py` accepts all the files.


# Screens and scenes (clean pack, `screens_bitmaps.md`: 24 pictures)

Made from `docs/clean_pack/screens_bitmaps.md` (all three passes). One file per bitmap, `<id>.pix`, written by `make_screens_bitmaps.py`:

```
~/work/simant-venv/bin/python make_screens_bitmaps.py   # writes the 24 .pix files, runs the spec's checks as assertions, writes preview_screens.png
```

Needs Python 3 with numpy and Pillow. Pillow's `ImageDraw` is used only on 8-bit index canvases (`Cv` in `screens_lib.py`): no anti-aliasing, the pixel values are palette indices.

| File | What |
|---|---|
| `screens_lib.py` | `Cv` (index canvas), the **ant drawing program** `ant()` (one body plan: abdomen, waist, thorax, neck, head, three leg pairs, elbowed antennae, mandibles; used from 10-px ants to the 230-px nestmate), dithering, pebbles, curves, lettering through `uilib`'s pixel faces; the `LETTERED` list of every string drawn |
| `screens_ab.py` | A the title (2000 / 2001), B Select a Game (2500), C the About box (3000 / 3001); the two-colour wordmark routine (the About heading and card) |
| `screens_wordmark.py` | the title wordmark: the nine 10-row glyph bitmaps from the spec, `render_mask(s, scale)` composition, `plain_wordmark(cv, pic, x, y, s, scale, color, lettered)` — the flat single-colour stamp (#36's plain-text requirement; made in the clean room) |
| `screens_icons.py` | E the seven 32 x 32 icons (9150..9156) |
| `screens_ants.py` | D the player's-ant pictures (9100, 9101, 9110, 9111) |
| `screens_scenes.py` | F the ant lion scene (9200..9203) and G the spider scene (12000..12003), each one `render(state)` |
| `screens_preview.py` | `preview_screens.png`: the title on its black screen, Select a Game (plain and with the hit rectangles / caption zones outlined), the About box with the card and with sample credits, the seven message boxes, every scene with its patches in cycle order |
| `make_screens_bitmaps.py` | the driver: sizes, the checks, the writing, a re-read of the files |

## Design

- **Title (A).** Option (c), a **night scene**: a purple-to-blue dithered sky with stars and a moon, a broad dark hill with three lit tunnel mouths, tan trails with marching ants (black colony, a few red, some carrying leaf pieces), a grass strip in front; the whole 512 x 372 canvas is drawn once and cut at row 172 (a script assertion: no wordmark and no thin line on the seam). The edges fade to black by ordered dither; the outermost ring is black 15 (11 % of the canvas is black). The wordmark `OpenSimAnt` is a regular 8-px face at 4x (32 px capitals), set as **plain flat text: one solid yellow 1, no outline, no shade, no highlight, no shadow** (`screens_wordmark.plain_wordmark` — the #36 plain-text requirement; the maker's check asserts the name's region holds no 0/2/14/15); `an open-source remake` below it, white with a black outline.
- **Select a Game (B).** Grey 12 everywhere except the heading, the five 63 x 63 (64 x 63) picture buttons, their caption zones and the Cancel button. Each tile has its own ground colour (cyan, tan, green, yellow, blue) and subject: Tutorial = a yellow ant with a pointer in front of a green chalkboard; Quick Game = a black and a red ant face to face under two flags with a spark between; Full Game = the yard from above (a lawn of 14-px cells, a house corner, a fence, two red and three black cells); Experimental = a soil heap with a spade, a magnifier and two ants; Load Game = a folder with a sheet sliding out and a returning arrow. Each tile: black 15 ring, bevel ring (white top / left, grey 13 bottom / right). Captions: a bold 9-px-capital title (black) and two lines of 7-px lettering (blue 6); the descriptions are our own wording.
- **About (C).** 3000 is flat 12 with the heading `About OpenSimAnt` (regular 8-px face at 2x, blue with a purple lower part), a groove at rows 46..47, the sunken well bevel round R exactly as the spec says (white 0 top / left, 13 then 14 bottom / right) and the footer; nothing else within 8 px of R. 3001 is the card: a round badge (sky, hill, tunnel mouth, an ant) at the left and the three lines at the right, a 6-px free margin all round.
- **Icons (E).** One 1-px black ring, one ground colour per cause (grass 8, grass 9 for the mower, water 6, light grey 12, magenta 4, purple 5), 6 to 9 colours each. 9155 a shoe sole (two parts, the ant's legs sticking out); 9152 / 9153 the same mower from above with wheels at the sides and a round shield, 9153 with flying clippings; 9150 an ant on its back in ripples; 9154 an empty gauge (red zone, needle at the empty end); 9151 a spray can, a green cloud and an ant on its back; 9156 a bolt and a small dark ant.
- **Player's-ant pictures (D).** 9100 a low three-quarter side view, the yellow ant lying on its back with curled legs, an X eye, one antenna bent; 9101 the newborn, seen from the front and a little above, beside a torn cocoon; 9110 / 9111 one `render_feed(state)`: the black nestmate (230 px, head down, body off the top) and the small yellow ant (head up), the green drop between their mouths; 9111 is the crop (72,62)-(152,151) of the "after" state (drop in the yellow ant's mouth, head leaning forward, mandibles changed): 17.7 % of its pixels differ from 9110's crop. Rows 0..14 of 9100 / 9101 are plain soil (no colour 1 or 15).
- **Ant lion (F).** A cross-section: dry ground above, the funnel with its far wall, layered sand with pebbles at both sides, the larva (flat wedge head, red eyes, two sickle jaws, a ridged neck) in four states "rest / rear / left / right"; the base is "rest", the patches are crops of the other states at (38,39) and (38,52); rows 39..51 of the "rear" render equal the base (so the strip stays correct when 9202 / 9203 replace the lower part). The caught ant shows only a leg and an antenna (no colour 1) in 9202 / 9203.
- **Spider (G).** A glossy black spider facing the viewer on a flat dusk-purple sky (blue strip at the bottom): a big abdomen above the head, eight small eyes in two rows, four jointed legs raised at each side, two chelicerae with curved fangs (orange tips); states "open / half / closed", 12000 = "open" in full, the patches are crops of (46,77)-(144,157).

## Checks (assertions in `make_screens_bitmaps.py`)

The nine groups of "The script's checks": sizes, characters, no `.`; the identity strings (`LETTERED`, no "SimAnt" outside "OpenSimAnt", no publisher / year, no lettering in the scenes and icons); the title (ring, cut, black share, wordmark height, the name flat one colour — no 0/2/14/15 in its region, no line on the seam, contrast); Select (flat 12 outside the allowed rectangles, tile rings and bevels, colour counts, caption inks, heading rows); About (ring, R, the bevel on at least 95 % of each side, the 8-px clearance, heading / footer rows, the card's margins and last row); the icons; 9100 / 9101 rows 0..14, 9110 / 9111 ring and difference; the patches of 9200 / 12000 (ring equality, pairwise differences, the yellow-ant rule, the constants `PATCHES`); all 24 distinct and not flat.


# The yard, passes 4-5: the animals, the spider and the map-window actors (yard_bitmaps.md, groups F, G, H, I)

64 files: the dog 8500..8511, 8600..8603; the cat 1300..1305, 1310..1312, 1320..1329; the bird 1250, 1251; the spider's bodies
1000..1007 and beaten frames 1050..1053; the small spiders 1100..1107; the sneaker 1200..1203; the Map window's mower 1210, 1211; the
marker 1400. Written by `make_yard_bitmaps.py` (passes 4 and 5 are listed in its `PASSES`); `~/work/simant-venv/bin/python preview_yard_actors.py` writes
`preview_yard_actors.png` (the animation strips at their offsets, the spider composite with the game's legs and fangs, the beaten frames,
the Map-window actors on 4-px cells).

| File | What |
|---|---|
| `yard_sprite.py` | a small software renderer: spheres and capsules in 3-D (`Pose`: heading, pitch, roll, spin), orthographic camera, z-buffer, light from the screen's top-left, cut to the bounding box and resampled to the exact sprite size (so every sprite is tight), 1-px black outline, single-pixel `marks` (eyes, collars) |
| `yard_pass4.py` | the dog, the cat, the bird and their checks |
| `yard_pass5.py` | the spider bodies (with the table recomputed from `spider/legs.json`), the beaten frames, the small spiders and the pass-5 checks |
| `yard_mapactors.py` | the sneaker, the Map window's mower and the marker |
| `preview_yard_actors.py` | the preview of these two passes |

## Design (passes 4-5)

- **One model per creature, many views.** The dog (white, brown patches and ears, a yellow collar of 1 to 3 pixels) and the cat (ginger, brown
  stripes, white chest, muzzle and paws, a cyan 7 collar) are chains of shaded spheres posed in 3-D, so all headings and poses are one animal.
  The left-walking cat 1303..1305 is the exact mirror image of 1300..1302 (as the spec says; so its light comes from the right). The startled
  cat is the same cat seen from the front, arched, with bristling fur and an open mouth; the pounce frames 1322..1324 are the same cat springing at the viewer
  with the claws out, 1321 / 1325 turn in the air, 1326..1329 are the tumbling cat rotated about the view axis. The bird is hand-drawn pixels (tan body, brown wings, orange beak).
- **Per-frame tweaks.** The alignment rule (R = centroid + offset) is met by the plain model except for 8508 (head turned 30 degrees, tail raised)
  and 8602 (thick raised tail); they are in `DOG_TWEAK`.
- **The spider.** A tan cephalothorax (head and thorax in one, 18 px long) and a dark-brown abdomen with a dark dorsal stripe and a pale highlight
  top-left (colours 10, 11, 12, 14, 15), a narrow waist, four pale eye pixels; seen from straight above, 36 px long and 14 wide on the axes; the diagonal bodies are stretched
  along the axis (not squeezed) so they keep the width the leg table needs. The beaten frames carry the 1007 body unchanged (legs are drawn only outside it) with four sets of black legs: sprawled, bent, two curls.
- **Map actors.** The small spiders are generated for 8 headings from one model (body 14, highlight 13, legs 15) and tuned to the spec's transparent counts. The sneaker
  is white with a red toe cap and heel tab, dark-grey sole, black laces, a padded heel opening (1201..1203 are 1200 turned). The mower 1210 is point-symmetric (red deck,
  orange rim, dark engine cover, four black wheels, slots, rivets) on a dark-green 9 mat; 1211 is 1210 turned by 90 degrees. The marker is a black ring, a red 3 ring, a white centre with a black cross-hair.
- **Colour choices the spec left open.** The sneaker colours (white / red / dark grey) should be used by the person of pass 3; the mower colours (red 3 deck, dark engine 14, black wheels)
  should be the yard mower 8100..8802's machine; the sign 1260 / house colours are pass 1's.

## Checks (assertions in `check_pass4` / `check_pass5`)

Sizes, masks, colour sets (dog 0, 1, 10, 11, 12, 15; cat 0, 2, 3, 4, 7, 10, 12, 15; spider 10..15; small spiders 13..15); tightness; dog alignment and collar (1 to 3 px, visible in profile and resting);
cat walking centroid and back line, mirror, startled bottom centre and feet, pounce centroid and the arc of the box centres; bird alignment; colour 1 only on the dog; the spider table recomputed from `legs.json`,
attach points and fang bases, mirror symmetry (at least 85 %), the beaten frames' body identical and the centre opaque; the small spiders' transparent counts and centroids; the sneakers' sizes; the mower's point symmetry and
rotation; the marker.


# The encyclopedia's pictures (`<id>.pix`, 40 one-bit bitmaps; spec `docs/clean_pack/encyclopedia_bitmaps.md`)

Made 2026-11-01 by an isolated agent from the spec only. Rebuild everything with `~/work/simant-venv/bin/python make_ency_bitmaps.py` (from any folder, no
arguments): it draws the 40 pictures, runs every assertion of the spec's "The script's checks" (sizes, only `0` / `f`, boxed labels on
their rectangles with the lettering centred and 2 px clear of the outline, no overlapping or unlisted outlined rectangle, leader tips
inside the named part and no leader through a box, the cut rows / columns white, 540's left 16 columns empty above the ground row,
880's arrows on their boxes and never through another box, 170 / 160's white border and word, the forbidden-word list) and writes the files.
`~/work/simant-venv/bin/python ency_preview.py all` writes `preview_ency.png` (the contact sheet at 2x, then every card of the placement table at 2x with the
text rectangles hatched grey, the navigation strip darker, the link rectangles red).

| File | What it is |
|---|---|
| `ency_lib.py` | the canvas `Cv` (1-bit, optional transform so any drawing runs at any scale, rotation or mirrored), tone patterns, the label face, `box` (boxed label), `leader`, the file writer |
| `ency_ant.py` | **the one ant model** (`draw_ant`, `place`, `fit`, `on_ground`): worker, soldier, winged ant, queen and every small ant of the scenes are parameter sets of it |
| `ency_insects.py` | termite, bee, wasp, larva, egg, pupa, seed, aphid, leaf, hexagonal cell |
| `ency_p1.py` .. `ency_p5.py` | the five passes (p1 menus and small items, p2 ant bodies and 200, p3 head / antennae / thorax / inside, p4 insects and species, p5 behaviour, life cycles, flowchart) |
| `ency_check.py` | the assertions; `make_ency_bitmaps.py` the driver; `ency_preview.py` the preview |

`630` was redrawn on 2026-11-01 (the first version, three tiny ants over a noisy strip, was too small to read; a second one with overlapping ants
read as a caterpillar): `ency_p4.py` `army630()` now draws a double file of five army ants marching left (two on a dotted back ground line at scale 0.6, three on a
solid 2 px ground line at 0.62, each about 30 px from head to gaster, every ant a separate silhouette with a 2..4 px gap to the next) with a dedicated pixel-space ant,
`_army_ant()`, because the shared ant model is too thin at this size: the biggest part is a white head with no eye, two long black hooked mandibles reach well past it, then a
narrower, longer white thorax, a small black waist node, a black gaster with a white glint, three solid legs and two dashed far legs in two alternating walking poses; two ants
carry a white outlined larva and one a piece of prey (a mid-tone oval with a groove and legs), held in the jaws in front of the head. Every other picture is byte-identical to before.

## Design

- **Line weights:** every contour is 1 px; the heavier 2-px stroke is used only for ground lines, femurs, the antennae's scape / funiculus and
  tubes of the gut. Leaders are 1 px ending in a 2 x 2 dot with a small white halo so it shows on a dark tone.
- **Tones** (registered to the picture, a 4 x 4 ordered dither): 0 white; 2/16 very light; 4/16 light (25 %); 8/16 mid (checkerboard); 12/16 dark
  (3 : 1 mesh); 16/16 black; plus diagonal hatches (every 3rd or 4th diagonal) and a cross hatch for the compound eyes. Rounded forms (head,
  thorax, gaster, leaves) use a gradient of these levels, lighter at the upper left, darker at the lower right. Small ants (body length under
  45 px) use 62 % of the tone levels so they stay legible.
- **The ant model:** local units of one body length, facing left; head 17 % (ellipse), thorax 30 % (three lobes, sutures), one-node waist, gaster 40 %
  (egg-shaped, banded for the queen), elbowed antennae (scape, bend, funiculus; the far one dashed), six legs in a tripod stride (the far three
  dashed and lighter), eye, mandibles (closed or open and toothed). Soldier = head scale 1.75 with hatching and open toothed jaws; winged ant = bigger
  thorax, two veined wings (front pair longer); queen = small head, wing scars, gaster 1.9 x long and high with segment lines and an egg.
- **Label face:** my own 1-px-stroke pixel face (`ency_lib.py`): capital height 7 (`b7`, boxes 11-12 high), 8 (`b8`, boxes 13 and higher, also for a
  one-word label in a tall box), 6 for the two-line labels (`r6`, pitch 8) and for plain captions. Narrow forms of `Q`, `u`, `n` are used only for
  "Queen" in 510's 28-px box. It is regular, not bold (a bold face would not fit the spec's narrow boxes).
- **Boxed label:** the outline is the rectangle's outermost pixels, white inside, the word centred; the box is drawn last so it erases whatever is
  under it.

## The words in the pictures (a later text batch must match them)

| Picture | Words |
|---|---|
| 150 | `Social insects`, `Ant anatomy`, `Life cycle`, `Castes`, `Behavior`, `Common species`, `Ant facts`, `Game strategy` |
| 400 | `Worker`, `Soldier`, `Replete`, `Male`, `New queen`, `Queen` |
| 500 | `Communication`, `Foraging`, `Scent trails`, `Food sharing`, `Nest building`, `Brood care`, `Fighting`, `Herding aphids` |
| 600 | `Carpenter ants`, `Harvester ants`, `Leafcutter ants`, `Weaver ants`, `Army ants`, `Fire ants` |
| 700 | `Ant life cycle`, `Colony life cycle` |
| 850 | `Overall goals`, `Gathering food`, `Warfare`, `Full game`, `Experimental game`, `Keyboard shortcuts`, `Colony flowchart` |
| 170 / 160 | `Next` / `Back` (white on a solid black button) |
| 200 | `Head`, `Thorax`, `Abdomen` |
| 210 | `Eyes`, `Ocelli`, `Maxillae`, `Antennae`, `Mouth` |
| 230 | `Mouth` over `pouch` (two lines), `Crop`, `Midgut` |
| 300 | `Ants`, `Termites`, `Bees`, `Wasps` |
| 510 | `Queen's` over `chamber` (two lines), `Queen`, `Brood`, `Brood`, `Nurseries` |
| 520 | `Antennae` |
| 530 | `Pheromone` |
| 550 | `Honeydew`, `Aphid` (singular: "Aphids" does not fit 29 px) |
| 610 | `Larvae` |
| 710 | `Egg`, `Larva`, `Pupa`, `Spin`, `Hatch` ("Emerge" does not fit 31 px) |
| 880 | `Foraging ants`, `Food collected`, `Food stored`, `Food eaten`, `Digging ants`, `Nest size`, `Colony health`, `Nursing ants`, `Egg production`, `Colony population`, `Starvation`, `Predation`, `Fights`; hint caption (unboxed) `click a box for` / `an explanation` |
| plain unboxed captions | 220: `claws`, `notch`; 720: `founding`, `growth`, `spreading` |

Open choices / deviations: 129 is entirely white; 21000..21003 are an up arrow, a down arrow, a right arrow and a diamond bullet; 170's and 160's
corners are rounded by one pixel; 880's three death boxes join a bar at x 223..224 that feeds one arrow into F10; the spare 128 is 440's drawing scaled up.
