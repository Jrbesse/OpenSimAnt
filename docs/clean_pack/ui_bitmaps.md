# Spec: the user-interface bitmaps (window chrome, menus, toolbars, panels, help overlays, small pictures)

> **Status (2026-10-31):** complete, ready for a maker (4 passes, see "How to work"). Written from the remake's window
> code (`UiArt`, `Main.cs`), the window layouts and the game's help and tutorial data. Covers 74 bitmaps. The encoder
> and its checks are in `tools/clean_pack/build.py` (`cat_bitmaps`; `--roundtrip=<zip>` checked all 252 originals).
> What could not be traced is said where it comes up ("not found").

Output folder: `remake/game/assets/clean/src/bitmaps/`. Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an
entry). **One file per bitmap, named `<id>.pix`** (for example `4600.pix`), plus `make_ui_bitmaps.py` (the
script that writes every `.pix`, so they can be regenerated; split it into modules if you like), `README.md` (the design:
the faces, the bevel, the colour roles, how to rebuild) and, recommended, `preview.png` (a contact sheet of everything,
and each window assembled as the game shows it: see "Previews").

## Contents

- [Scope](#scope) - [How to work](#how-to-work) - [Format and rules for every file](#format-and-rules-for-every-file)
- [What the game does to these pictures](#what-the-game-does-to-these-pictures) - [Look and lettering](#look-and-lettering)
- Groups: [A window chrome](#a-window-chrome-icons-100-113), [B pop-up menus, option palettes and help pages](#b-pop-up-menus-and-option-palettes),
  [C tool icons](#c-tool-icons-5100-5107), [D the Edit window's tool strip](#d-the-edit-windows-tool-strip-15000-and-its-help-15001),
  [E the Map window's toolbar](#e-the-map-windows-toolbar-14000-its-help-14001-and-the-population-popup-14002),
  [F Behavior and Caste Control](#f-behavior-control-and-caste-control-4600-4601-4620-4621), [G the History window](#g-the-history-window-16000-16001),
  [H Status and Game Over](#h-the-status-window-13000-and-the-game-over-window-16100), [I the win screen](#i-the-win-screen-16200-and-its-eyes-16210-16212),
  [J tutorial pictures](#j-tutorial-pictures-17000-17013), [K encyclopedia buttons](#k-the-encyclopedia-button-strips-21004-and-21005), [L start-up card](#l-the-start-up-cards-28000-and-28003)
- [The script's checks](#the-scripts-checks) - [Consistency between the pictures](#consistency-between-the-pictures) - [Not found / open](#not-found--open)

## Scope

The HCEGANT type-2 bitmaps that are interface chrome, **74 files**: 100..113; 4500..4505, 4510; 4600, 4601, 4620, 4621;
5000..5006, 5010, 5011, 5100..5107; 6000; 13000; 14000..14002; 15000, 15001; 16000, 16001; 16100; 16200, 16210..16212;
17000..17013; 21004, 21005; 28000, 28003. (Groups: A 14, B 14, B2 3, C 8, D 2, E 3, F 4, G 2, H 2, I 4, J 14, K 2, L 2.)

**Not in this spec** (later batches): the title, select and about screens (2000s, 3000s: the title picture, "Select a
Game", the about box), the yard and its actors (1000s, 7000s, 8000s: the marker 1400, the spider, the human, the dog,
the yard window's pictures and toolbar 7010), the scenes (9000s, 12000s) and every SHARED type-2 bitmap (the
encyclopedia's pictures and small icons). Two pictures here show buttons of the yard window's toolbar (17006, 17007):
see group J.

## How to work

The 74 pictures share one look and one set of lettering, so make them with **one script and one helper** (a small module
of your own: your pixel lettering, a bevelled box, a 'well', a rotated-text routine, the inversion check). Do it in four
passes, each ending with a build of what exists (`python tools/clean_pack/build.py` refuses a wrong size, a missing mask
or an opaque picture that has holes):

1. **Pass 1:** groups A, B, C (chrome icons, menus, tool icons): 100..113, 4500..4510, 5000..5011, 5100..5107, 6000.
2. **Pass 2:** groups D, E, H: 15000, 15001, 14000..14002, 13000, 16100.
3. **Pass 3:** groups F, G: 4600, 4601, 4620, 4621, 16000, 16001.
4. **Pass 4:** groups I, J, K, L: 16200, 16210..16212, 17000..17013, 21004, 21005, 28000, 28003.

## Format and rules for every file

- `.pix` as in `docs/clean_pack/README.md`: one line per pixel row, one character per pixel (`0`-`9`, `a`-`f` a palette
  index, `.` transparent), `#` comment lines, every row the same length. **The size of each picture is exact** (the game
  places things by pixel; the build rejects another size).
- **Opaque pictures** (the default) contain **no `.`**. **Masked pictures** (help overlays 4601, 4621, 14001, 15001,
  16001 and the eyes 16210..16212) **must** contain `.` where the window below shows through. The table in each group
  says which.
- **1-plane pictures** (21004, 21005 only) allow only `0` (white) and `f` (black): they are black-and-white bitmaps and
  the game shows them as they are (a checkerboard of the two reads as grey).
- The palette is the standard 16 colours of `README.md`. Their values, for contrast checks (published Apple system
  colours): 0 `FFFFFF`, 1 `FCF305`, 2 `FF6402`, 3 `DD0806`, 4 `F20884`, 5 `4600A5`, 6 `0000D4`, 7 `02ABEA`, 8 `1FB714`,
  9 `006411`, 10 `562C05`, 11 `90713A`, 12 `C0C0C0`, 13 `808080`, 14 `404040`, 15 `000000`.
- Everything is drawn at 640 x 480 with no scaling, no anti-aliasing, no colours outside the 16.
- **Wording.** All lettering is English and yours. Where this spec lists **a label** (a short functional UI word such as
  "Forage", "Pause", "Surface") use that word or a plain synonym of the same length. Where it says **a help sentence**
  (the help overlays, the tutorial pictures' captions, the start-up card) write **new wording** with the same meaning and
  about the same length, never a remembered or copied sentence. No picture may contain the words "SimAnt" or "Maxis", a
  publisher's or author's name, a logo or a trademark.
- **Coordinates** below are pixels from the picture's own top-left corner `(x0, y0)-(x1, y1)`, **x1 and y1 exclusive**
  (a rectangle `(3, 3)-(44, 14)` is 41 x 11 pixels). They are measured from the game's window layouts, which the game
  uses for hit testing and for what it draws on top: they cannot move.

## What the game does to these pictures

Read this before drawing; most constraints come from it.

1. **Highlighting is a colour inversion.** The game shows "selected", "pressed" or "under the pointer" by inverting a
   whole rectangle of the screen: every pixel's palette index `c` becomes `c XOR 15`. The pairs: white 0 / black 15,
   yellow 1 / dark grey 14, orange 2 / medium grey 13, red 3 / light grey 12, magenta 4 / tan 11, purple 5 / brown 10,
   blue 6 / dark green 9, cyan 7 / green 8. There is no separate picture for a pressed button. The rectangles that are
   inverted are called **"inverted"** in the tables; their art must **read both as drawn and inverted**: the lettering
   or symbol against its face must keep a contrast ratio of at least 3 : 1 in both states (compute with the colour
   values above; black on light grey becomes white on red, which passes; avoid faces and lettering that are both mid
   tones, e.g. orange on medium grey). **This rule wins over any lettering colour named in the tables below**: on a
   light grey 12 face, blue 6, red 3 and brown 10 lettering fail it once inverted, so lettering in an inverted rectangle
   is black 15 unless the colour named passes the check (a colour may still go in a swatch, frame or badge beside it).
2. **Text and numbers are drawn over some pictures** by the game, in its own fonts (black unless said): the rectangles are
   called **"text rectangle"**. The game draws the text straight onto the picture (and in most cases first fills the
   rectangle's rows with its background), so a text rectangle must be **one flat colour, the one given**, with no
   pattern, picture or lettering in it; put your frame around it, outside the rectangle.
3. **Bars, gauges and icons are drawn over some pictures.** Rectangles called **"gauge"** are filled completely by the
   game (draw the 'well' around them, not in them); **"icon spot"** is where the game draws a 16 x 16 icon with its
   top-left corner on the rectangle's: keep the rectangle a flat button face.
4. **Clipping.** A window is drawn clipped to its own rectangle. Where that is smaller than the picture, the outermost
   column or row is cut off (said per picture: 4500's right-hand column, 6000's bottom row); where it is larger, the
   rim is filled with the panel's flat light grey (12): then the picture's own right / bottom edge should be a frame or
   shadow that sits well on light grey.
5. **Hit areas are not in the pictures** (they are in the layouts). The visible controls must simply coincide with the
   rectangles given.
6. **Help overlays** (masked pictures) are drawn over their window only while the "?" button is held, at the position
   given, so they hide what is under their opaque pixels. Their callouts point at controls with **leader lines**; where
   the game puts the controls is fixed, so each leader's tip is checked (see each overlay and "The script's checks").

## Look and lettering

The interface is a flat, bevelled, desktop-style one, light grey with black lettering, in the 16-colour palette, as the
windows the game draws itself.

- **Colour roles.** Panel face and window background: light grey 12. Wells (places that show numbers, bars, graphs or
  text): white 0 with a 1-px frame. Highlight edge (top and left of a raised object): white 0; shadow edge (bottom and
  right): medium grey 13 or dark grey 14. Outlines and lettering: black 15. Headings and the word labels in menus: blue 6
  (menus) or black 15 (buttons). Quantities that belong to the red colony are drawn in red 3, those of the black colony
  in black 15, the player's in yellow 1 (on a light ground give yellow a black or dark grey outline), as in the ant
  sprites. Green 9 is for the "?" help glyph.
- **Light** comes from the top-left: raised things have the highlight on top and left and the shadow on the bottom and
  right.
- **Lettering**: draw **your own pixel faces**, the same two everywhere: a **label face** (bold, upright, capitals and
  lowercase, capital height 7 to 9 px, used for buttons, menu entries, window labels, headings) and a **small face**
  (regular, capital height 6 to 7 px, used in help callouts and the tutorial pictures). Titles ("GAME OVER", "STATUS")
  may be bigger (up to 18 px high), in your own display lettering. A label sits vertically centred in its row with at
  least 2 px above and below.
- **Do not copy** another program's or game's icons or lettering. The functions and positions are fixed, the drawing is
  yours. Where a symbol is named (a magnifier, a spade) draw a plain, common version of it.
- Each help-callout face shows only **colours 0, 6 and 14** (see group D).

# Groups

## A. Window chrome icons (100..113)

All opaque, 4 planes, small bevelled square buttons. The game draws them on the **title bar** (a 18-px high strip,
dithered dark / light grey, with the window's title in it) and the Edit window's corner: the title bar is flush with the
top of the window, so each icon sits at the very top of the bar with about 3 px of bar below it. **Each icon has its own
button face** (it is opaque), a raised bevel (highlight 1 px on top and left, 1 to 2 px of shadow on the bottom and
right) and a symbol in the middle. They must read at 15 x 15.

| File | Size | What it is / where | Constraints |
|---|---|---|---|
| `100.pix` | 15 x 15 | **The close box**, at the left end of every window's title bar (drawn for the Edit, Map, Behavior, Caste, History, Yard, Encyclopedia and Debug windows). | A "close / dismiss" symbol of your design. (Its click behaviour is not implemented in the remake yet.) |
| `103.pix` | 15 x 15 | **The zoom box**, at the right end of the Edit window's title bar. | A "make larger / open the big map" symbol. |
| `105.pix` | 15 x 15 | **A document icon**, at the right end of the title bar of every window that has one, left of the zoom box in the Edit window (Edit, Map, Behavior, Caste, History, Yard, Encyclopedia, Debug). | A "page / window list" symbol (a sheet of paper). |
| `112.pix` | 16 x 16 | **The grow box**, drawn over the bottom-right corner of the Edit window's map area (inside the window's frame). | A resize symbol (two nested corners); it lies over the map, so give it a clear outline on all sides. |
| `109.pix` | 15 x 13 | **Scroll bar: up arrow**, at the top of the file dialog's scroll bar. | Exactly 15 wide (the bar's width) and **13 high: the same height as 111** (the game takes 109's height as the arrow height and places 111 that high at the bottom). An up-pointing arrow on a button face. |
| `111.pix` | 15 x 13 | **Scroll bar: down arrow**, at the bottom of the same bar. | 15 x 13, the mirror partner of 109. |
| `110.pix` | 15 x 13 | A third scroll-bar glyph of the same family (probably the thumb or a page marker); **not drawn by the remake** (the thumb is a plain filled rectangle; not found where the original uses it). | Same style and size as 109 / 111, a different symbol (for example a plain box). |
| `101.pix` | 15 x 15 | Alternative window-corner icon, drawn by the engine only for a window-flag no layout sets (not found in use). | A "move / re-order window" style symbol. |
| `102.pix` | 15 x 15 | Alternative zoom box (the engine draws it instead of 103 for a flag no layout sets; not found in use). | A pair of 103: same family, "zoom in" if 103 is "zoom out". |
| `104.pix`, `106.pix`, `107.pix`, `108.pix` | 15 x 15 each | **Not drawn by the remake; not found in use.** Four more control glyphs of the same family (the originals look like a corner arrow, a down-left arrow, a ruler and a double vertical arrow). | Make four distinct, plain symbols in the same style: a corner / diagonal arrow, the opposite diagonal arrow, a ruler (measure) and a two-headed vertical arrow (resize height). They are spares: do not make them elaborate. |
| `113.pix` | 15 x 15 | **Not drawn by the remake; not found in use.** The same kind of symbol as 100 in a different state. | The close symbol as an "inactive / warning" variant (another colour of the same symbol). |

Palette: faces light grey 12; symbols may use blue 6, orange 2 / red 3 and white; keep black or dark grey for outlines.
The 109 / 111 arrows are drawn on the scroll bar's light-grey track (so a face and edge that fit light grey).

## B. Pop-up menus and option palettes

These are small windows that open at the pointer and close when released; **each entry is a rectangle of the picture**:
the game inverts the entry under the pointer (and, for the option palettes, the current option when it opens). All are
opaque, 4 planes. **Every menu entry's rectangle below is "inverted"** (read both ways, see above) and also the hit area.

| File | Size (window) | Entries (top to bottom) and rectangles | Constraints |
|---|---|---|---|
| `4500.pix` | 82 x 102 (window 81 x 102: the **last column is cut off**) | **The yellow ant's menu** (any ant but the spider or a queen): six rows: `Recruit 5`, `Recruit 10`, `Release 1/2`, `Release All`, `Exchange`, `Help`. Rects: (3,3)-(78,19), (3,19)-(78,35), (3,35)-(78,51), (3,51)-(78,67), (3,67)-(78,83), (3,83)-(78,98). | Rows 16 px high. A key badge at the left of the first five entries (1, 2, 3, 4, and X for Exchange, in a small square each, each badge in its own colour: decoration, the entry's number) and a green "?" glyph with the label for `Help`. The lettering in blue 6 on light grey. |
| `4502.pix` | 82 x 54 (window 82 x 53) | **The queen's menu**: `Dig Hole`, `Start Brood`, `Help`. Rects: (3,3)-(78,18), (3,19)-(78,35), (3,35)-(78,50). | Same style as 4500; badges 1 and 2. |
| `4504.pix` | 82 x 70 | **The spider's menu**: `Chase`, `Hunt`, `Exchange`, `Help`. Rects: (3,3)-(79,19), (3,19)-(79,35), (3,35)-(79,51), (3,51)-(79,67). | Same style; badges 1, 2 and X. |
| `4510.pix` | 81 x 85 (window 83 x 87, picture at +1,+1) | **The "Ant Info" card**, shown when the information tool is clicked on an ant. It is not a menu: nothing is inverted. Three lines of text are written by the game into **text rectangles**: (3,3)-(78,15) black (the ant's kind), (3,28)-(78,50) blue 6 (what it is doing), (3,64)-(78,81) blue 6 (what it carries); all on **flat light grey 12**, text centred in font 2. | Two heading labels baked in, in blue 6, small face: **`Behavior`** centred in y 16..27 (above the second rectangle) and **`Carrying`** centred in y 52..63 (above the third); a thin separator line at y 15..16 and y 50..51 is fine. A frame round the card. |
| `6000.pix` | 85 x 109 (window 86 x 108: the **last row is cut off**) | **The scent-layer menu** (opens from the SCENT button): six rows `Off`, `Alarm`, `B-Nest`, `B-Trail`, `R-Nest`, `R-Trail` (black colony's nest scent and trail, red colony's). Rects: (3,3)-(81,20), (3,20)-(81,37), (3,37)-(81,54), (3,54)-(81,71), (3,71)-(81,88), (3,88)-(81,105). | 17-px rows. Rows 2..6 carry a **swatch** at the left, about 32 x 15 at x 4..35: the same picture as that scent's button on the Map window's toolbar (14000: alarm; black nest scent; black trail; red nest scent; red trail), drawn smaller; `Off` has no swatch. The word labels: `Off` brown 10, `Alarm` blue 6, the two `B-` rows black 15, the two `R-` rows red 3 (the game's colour code for the colonies); you may write "Black nest" etc. if it fits 40 px. |
| `5000.pix` | 97 x 143 (as its window) | **The tool palette** of the Experimental game: eight rows of 17 px, label right of a 16 x 16 icon at **x 4, y 4 + 17 k** (k = 0..7): `Ant Info`, `Barriers`, `Dig/Fill`, `Add Ants`, `Add Food`, `Drop Trails`, `Insecticide`, `Start Game`. Rects: (3, 3 + 17 k)-(93, 20 + 17 k). | **The seven icons at (4, 4 + 17 k), k = 0..6, must be pixel-identical to files 5100..5106** (group C; copy them in by script); the eighth row has no icon (centre `Start Game`). Labels in blue 6, capitals, 8 to 9 px high. |
| `5010.pix` | 129 x 24 | **"Experimental mode" switch** (shown above the Map window's Experimental button in a Quick game): one entry (3,3)-(125,20) saying `EXPERIMENTAL MODE` (a mode name in capitals). | One flat button; blue 6 lettering. |
| `5011.pix` | 110 x 53 | **A notice**: the same button in a Full game: not an entry (nothing happens when clicked). Three lines: *Experimental mode is not available in the full game.* (write your own wording, three lines, small blue face). | No hit areas; the whole picture is the card. |
| `5001.pix` | 49 x 29 (window 49 x 29) | **Option palette of Barriers**: `Walls` (0,0)-(48,14), `Rocks` (0,14)-(48,28). | The two options fill the whole picture edge to edge, 14 px each, 1-px dividers inside the rects. Black 15 lettering on light grey 12. |
| `5002.pix` | 49 x 29 (window 50 x 30) | **Dig / Fill**: `Dig` (0,0)-(48,14), `Fill` (0,14)-(48,28). | As 5001; the window's extra right / bottom pixel is flat light grey. |
| `5003.pix` | 49 x 29 (window 50 x 30) | **Add Ants**: `Black` (0,0)-(48,14), `Red` (0,14)-(48,28) (which colony's ants). | As 5001. Both words in black 15 (a red word on the inverted red / grey would be too weak). |
| `5004.pix` | 49 x 29 (window 49 x 29) | **Add Food**: `1 piece` (0,0)-(48,14), `20 pieces` (0,14)-(48,28). | As 5001; the longest word must fit 44 px. |
| `5005.pix` | 64 x 71 | **Drop Trails**: five options 14 px each: `Black nest`, `Black trail`, `Red nest`, `Red trail`, `Alarm`: (0,0)-(63,14), (0,14)-(63,28), (0,28)-(63,42), (0,42)-(63,56), (0,56)-(63,70). | As 5001; widest label 59 px. |
| `5006.pix` | 43 x 29 (window 44 x 30) | **Insecticide**: `Spray` (0,0)-(42,14), `Stream` (0,14)-(42,28). | As 5002. |

Whenever the same option appears in two places they are the same word: the five trail options (5005) and the scent menu's
(6000) name the same five maps in the same order of colours.

### B2. Help pages (4501, 4503, 4505)

Three **text pages**, one per ant menu above: the page that the `Help` entry of that menu is meant to show (4501 for
the yellow ant's menu 4500, 4503 for the queen's menu 4502, 4505 for the spider's menu 4504). **The remake does not
show them yet** (its `Help` command only prints a note; the original's DOS build shows no page either), so they will be
wired up later: they must be correct for this game's controls. All opaque, **4 planes but only colours 0, 13 and 15**
(a black-and-white page).

| File | Size | Page title and content |
|---|---|---|
| `4501.pix` | 185 x 235 | **yellow ant help**: *Movement* (click the ground to walk there; click the yellow ant to re-centre the view on it; double-click inside a nest to dig), *Moving things* (double-click a pebble or a piece of food to pick it up, double-click again to drop it), then one short sentence each for the menu's commands *Recruit* (calls ants to follow you), *Release* (lets them go) and *Exchange* (swap bodies with another ant) |
| `4503.pix` | 185 x 235 | **new queen help**: *Movement* (as above), *Dig Hole* (first walk to a clear area; try other places until the hole works), *Start Brood* (starts egg laying; you become the first ant to hatch) |
| `4505.pix` | 184 x 235 | **spider help**: *Movement* (click to walk, double-click to run, click the spider to re-centre), *Chase* (pick it, then click an ant to eat it), *Hunt* (the spider looks for ants and attacks them on its own), *Exchange* (switch back to an ant) |

Layout and style (all three the same): a **medium grey 13 1-px outline** round the whole picture, then 1 px of white, then a
**black 15 1-px frame** (so the frame's top-left corner is at (2,2)); inside, white 0 paper with black 15 text in the
**small face** (regular, line pitch 11 or 12 px, left margin 8, at most 20 lines, text area (8,8)-(177,227)): a centred
**title line in capitals** at the top; each section starts with its **name underlined** (one line) followed by one to
three short lines; one empty line between sections; command names that are explained in the sentence may be in a bold
version of the face. No pictures. **Write new wording** (the contents above are what each section must explain, not
the sentences); do not mention a keyboard alternative to double-clicking (the spec side adds the right line when these
pages are wired up).

## C. Tool icons (5100..5107)

16 x 16, opaque, 4 planes. The Edit window and the Map window draw one of them at the **icon spot** of their
"Experimental menu" button: `5100 + tool` when the game is the Experimental game (tool 0..6), `5107` otherwise.
5100..5106 also appear in the tool palette 5000 (pixel-identical). Each is a **pictogram on a light grey 12 square** (the
button's face; the icon replaces the face's top-left 16 x 16 pixels, so its own background must be light grey and its
edge must not need a bevel).

| File | Tool | Picture (your plain version of it) |
|---|---|---|
| `5100.pix` | Ant Info: click an ant to read about it | a magnifying glass |
| `5101.pix` | Barriers: lay walls or rocks | a rock or a stone block |
| `5102.pix` | Dig / Fill: dig or fill soil | a spade |
| `5103.pix` | Add Ants | a single ant seen from above (black body, legs) |
| `5104.pix` | Add Food | a green food morsel or two (green 8 / dark green 9) |
| `5105.pix` | Drop Trails: lay a pheromone trail | a dropper or pipette over a short trail line (red or pink drops) |
| `5106.pix` | Insecticide: spray the pest | a spray can with a warning mark (a skull or a cross) |
| `5107.pix` | the "tools" icon shown when no tool is active (not the Experimental game) | two tools crossed (the spade and the dropper), so it reads as "the toolbox" |

Light from the top-left; black or dark grey outlines; at most 8 colours each.

## D. The Edit window's tool strip (15000) and its help (15001)

### 15000: `15000.pix`, 48 x 252, opaque, 4 planes

The vertical strip of buttons at the left of the Edit window (the close-up map is on its right). It is a column of
pictorial buttons, a menu title, a pause button, and three health bars with their labels. **Rectangles (the game's hit
and draw areas), in picture coordinates:**

| Control | Rect | What the picture shows / the game does |
|---|---|---|
| `MAP` button | (3,3)-(44,14) | a **wide, short button labelled `MAP`** with a small right-pointing triangle (menu mark); opens the overview map |
| `?` help button | (3,21)-(22,40) | a button with a green "?"; the overlay shows while held |
| Experimental button | (26,22)-(44,40) | a **blank button face**: **icon spot** (26,22)-(42,38), the whole rect flat light grey 12 |
| Surface view | (3,47)-(44,66) | a picture of the **surface** (top view of ground with small black and red marks): **inverted** while the surface is shown |
| Black nest view | (3,69)-(22,88) | a picture of a **nest cut-away** (soil with tunnels): **inverted** while shown |
| Red nest view | (25,69)-(44,88) | the same picture with a **red frame / border** (the red colony): **inverted** while shown |
| Go to yellow ant | (3,91)-(22,105) | a yellow ant on tan ground |
| Go to spider | (25,91)-(44,105) | a spider on tan ground |
| Go to black queen | (3,108)-(22,122) | a black ant with a big abdomen on brown soil |
| Go to red queen | (25,108)-(44,122) | the same in red, on brown soil |
| `PAUSE` button | (3,129)-(44,140) | a wide button labelled `PAUSE`: **inverted** while the game is paused |
| `SCENT` button | (3,147)-(44,158) | a wide button labelled `SCENT` with a right-pointing triangle: **inverted** while the alarm trail is shown |
| Yellow health bar | (8,176)-(13,239) | **gauge** 5 x 63, filled by the game yellow 1 (from the bottom) on light grey 12 |
| Black colony bar | (21,176)-(26,239) | gauge, filled black 15 |
| Red colony bar | (34,176)-(39,239) | gauge, filled red 3 |

Also baked in: a heading **`Health`** (label face, black, about 7 px high) above the bars, in y 163..172 under a
full-width black divider line at y 161; below the bars, at y 243..251, the letters **`Y`** (yellow 1 with a dark
outline), **`B`** (black), **`R`** (red 3), each about 7 px high and centred on its bar (x 10, 23, 36). The game also
draws, **over the bars**, a 1-px horizontal line across the yellow bar (black, at the yellow ant's eat threshold) and
across the black bar (inverted); that is code, not your concern. Draw each bar's well as a **thin black 1-px frame round
its rectangle, outside it** (so the three frames lie at x 7 and 13, 20 and 26, 33 and 39, and at y 175 and 239) and
nothing inside. Everything else is flat light grey 12 with thin dividers between
the groups (top buttons, views, go-to buttons, pause / scent, health).

The picture's **last column (x 47)** is a black 15 line (the edge against the map); the bottom edge (y 251) ends in
light grey with no frame (the window's own light grey continues below).

**Pictures on the buttons** (views, go-to, queens): 19 x 14 to 41 x 19 px, light from the top-left, a bevel round each (1-px
highlight and shadow inside the rect); they must still read when inverted.

### 15001: `15001.pix`, 174 x 238, **masked**, 4 planes

The **help overlay** of the Edit window, drawn at **(+10, -1) relative to 15000's top-left** while "?" is held. Colours
only **0, 6, 14**; everything else transparent. It is a column of **callouts** (a white panel 0 with 1-px dark-grey 14 frame
and 14 lettering, small face) with **blue 6 1-px leader lines** from each panel to the control it names. The panels must
sit at **x >= 40** (right of the strip, over the map); only leader lines and small brackets enter x < 40.

Write the callouts' wording yourself (a help sentence, 1 to 2 short lines, or a label). Callouts and their targets, in
**overlay coordinates** (the strip lies at x -10..38; targets with x < 0 can only be reached up to x = 0):

| Callout (what it explains) | Target rect | Leader tip |
|---|---|---|
| the `MAP` button: click to open the overview map, drag to open the Map window (2 lines) | (-7,4)-(34,15) | on or beside the button, within 3 px of the rect |
| the Experimental menu button | (16,23)-(34,41) | inside the rect |
| the surface view button | (-7,48)-(34,67) | inside |
| the black nest view button | (-7,70)-(12,89) | inside (x 0..11) |
| the red nest view button | (15,70)-(34,89) | inside |
| go to the yellow ant | (-7,92)-(12,106) | inside |
| go to the spider | (15,92)-(34,106) | inside |
| go to the black queen | (-7,109)-(12,123) | inside |
| go to the red queen | (15,109)-(34,123) | inside |
| pause the game | (-7,130)-(34,141) | inside |
| the scent overlay menu | (-7,148)-(34,159) | inside |
| the yellow ant's health bar | (-2,177)-(3,240) | inside (x 0..2) |
| the marker line that shows the level at which the yellow ant eats | the same bar, x 0..2 and y 177..239 | inside, at a different height from the line above |
| the black colony's health bar | (11,177)-(16,240) | inside |
| the colony's alert level (the line across the black bar) | the same bar | inside, at a different height |
| the red colony's health bar | (24,177)-(29,240) | inside |

Callouts are stacked top to bottom in the same order as their targets; no two panels overlap; no panel needs more than
about 135 px of width.

## E. The Map window's toolbar (14000), its help (14001) and the population popup (14002)

### 14000: `14000.pix`, 512 x 46, opaque, 4 planes

The strip of buttons under the Map window's overview map. **Rectangles** (hit areas / draw areas), picture coordinates:

| Control | Rect | What it shows / does |
|---|---|---|
| **Yard** view | (5,5)-(42,31) | a button picture: the yard seen as a house with its lawn; label **`Yard`** below, y 33..45 (label face, black); **inverted** while the yard is the view |
| **Surface** view | (47,5)-(84,31) | picture: the ground with food and ants as dots; label `Surface`; inverted when shown |
| **Black nest** view | (89,5)-(114,31) | a nest cut-away; label **`Nest`** (black); inverted when shown |
| **Red nest** view | (119,5)-(144,31) | the same with a **red frame**; label **`Nest`** in **red 3**; inverted when shown |
| Black nest scent | (155,3)-(189,21) | picture on tan ground: a glowing blob (the nest's scent) in the black colony's look; **inverted** while that scent layer is shown |
| Black food trail | (155,25)-(189,43) | picture: a scent trail (a winding line) on tan, black colony; inverted when shown |
| Alarm scent | (195,3)-(213,43) | a **tall button** (18 x 40): a red alarm bulb / ball; inverted when shown |
| Red nest scent | (219,3)-(253,21) | like the black one with **red frame** (red colony); inverted when shown |
| Red food trail | (219,25)-(253,43) | like the black one, red frame; inverted when shown |
| Show Trails | (264,3)-(287,21) | a picture of a path line on tan |
| Behavior Control | (264,25)-(287,43) | a button with **`B`** in a triangle (small coloured bars beside it) |
| Center on Yellow | (290,3)-(313,22) | a yellow ant with a small marker |
| Caste Control | (290,25)-(313,43) | the same, **`C`** in a triangle |
| Mystery button | (316,3)-(339,21) | **a blank button face** (it has no label; leave it flat) |
| History Display | (316,25)-(339,43) | a small line graph |
| Efficiency Score | (342,3)-(365,22) | a blue **`%`** sign |
| Ant Info window | (342,25)-(365,43) | an ant with text lines (a "card") |
| Help `?` | (368,25)-(391,43) | a button with a green **`?`** |
| Experimental menu | (369,4)-(391,21) | blank button face, **icon spot** (369,4)-(385,20), rect flat light grey 12 |
| Population report area | (395,1)-(510,45) | **a panel**: see below; held = the detailed popup 14002 |
| black count | (398,3)-(432,11) | **text rectangle** flat white 0: a number, black, font 3, centred |
| red count | (398,26)-(432,34) | text rectangle flat white 0: a number, red 3 |
| black population gauge | (445,3)-(509,11) | **gauge** 64 x 8: filled black 15 from the left, the rest white 0 |
| black health gauge | (445,15)-(509,20) | gauge 64 x 5, black 15 over white 0 |
| red population gauge | (445,26)-(509,34) | gauge 64 x 8, red 3 over white 0 |
| red health gauge | (445,38)-(509,43) | gauge 64 x 5, red 3 over white 0 |

Baked into the **population report panel**: the word **`BLACK`** (black, label face) under the black count, y 12..22, the
word **`RED`** (red 3) under the red count, y 35..45, the letters **`P`** and **`H`** (green 9) at the left of each pair
of gauges (x 436..444, at the population gauge's y and the health gauge's y), and a frame in black (the black colony's
two gauges) or red 3 (the red colony's two) round the gauges. The panel and the count wells have a thin dark line
between the colony rows. The rest is flat light grey 12 with thin separators between the groups of buttons.

All buttons are bevelled (white 1-px highlight top-left, dark shadow bottom-right) and the pictures inside them must
still read when **inverted**. The pictorial buttons may reuse the same small pictures as the Edit window's strip (surface,
nest, red nest, yellow ant).

**The tutorial pictures of group J are crops of this picture**, so draw the buttons so that each one's face and bevel
cover its crop window completely (the bevel's outer edge on or inside the window's edge; the window may include a pixel
or two of the panel's grey around the button): Yard (2,3)-(43,33); Behavior Control (262,24)-(287,44); Caste Control
(288,24)-(313,44); `?` (366,24)-(391,44); Center on Yellow face (291,5)-(312,21). Leave at least one pixel of grey between
neighbouring buttons' crop windows.

### 14001: `14001.pix`, 512 x 133, **masked**, 4 planes

The **help overlay** of the Map window, drawn at **(0, -89) relative to 14000's top-left** (so its rows 89..132 lie on the
toolbar and rows 0..88 on the map above it). Colours only **0, 6, 14**. Callouts (white panel, 14 frame and lettering,
small face, **blue 6 leader lines**), all placed in rows **0..88** (above the toolbar), except the two gauge labels of the
population report (right-hand end, may lie on the report panel). Every leader must reach its target; the leaders of
the right-hand button columns must stay inside their column (the buttons there are 26 px apart: callouts for them are
narrow, **rotated 90 degrees** text panels no wider than 12 px side by side, the upper button of a pair has a short
leader, the lower one a long leader; you may stagger them differently).

**Targets in overlay coordinates** (toolbar rows are shifted by 89 from 14000: add 89 to the y of the 14000 table; x is
the same):

| Callout (what it explains) | Target rect | Leader tip |
|---|---|---|
| **Map views** heading + `Yard View` | (5,94)-(42,120) | inside, y >= 94 |
| `Surface View` | (47,94)-(84,120) | inside |
| `Black Nest` | (89,94)-(114,120) | inside |
| `Red Nest` | (119,94)-(144,120) | inside |
| **Scent layers** heading + `Nest Scents` (two buttons) | (155,92)-(189,110) and (219,92)-(253,110) | a bracket / two tips, each inside one |
| `Food Trails` (two buttons) | (155,114)-(189,132) and (219,114)-(253,132) | two tips |
| `Alarm Scent` | (195,92)-(213,132) | inside |
| `Show Trails` | (264,92)-(287,110) | inside |
| `Behavior Control` | (264,114)-(287,132) | inside |
| `Center on Yellow` | (290,92)-(313,111) | inside |
| `Caste Control` | (290,114)-(313,132) | inside |
| `Mystery Button` | (316,92)-(339,110) | inside |
| `History Display` | (316,114)-(339,132) | inside |
| `Efficiency Score` | (342,92)-(365,111) | inside |
| `Ant Info Window` | (342,114)-(365,132) | inside |
| `Experimental Menu` | (369,93)-(391,110) | inside |
| report: hold the button here for the detailed population report (a help sentence) | (395,90)-(510,134) | a bracket along the top of the report area |
| `Population` (the two gauge rows 8 px high) | (445,92)-(509,100) and (445,115)-(509,123) | one tip each, inside |
| `Health` (the two thin gauge rows) | (445,104)-(509,109) and (445,127)-(509,132) | one tip each, inside |
| count wells: no callout is needed | | |

No panel may cover a button in rows 89..132 (the gauge labels excepted); panels do not overlap each other.

### 14002: `14002.pix`, 181 x 142, opaque, 4 planes

The **population popup** (opens while the report area is held): a list of the six castes with the
numbers and bars **drawn by the game** on the right, in the **text / gauge area (88,4)-(177,139)** (flat light grey 12:
the game writes two counts per caste, black above red, 10 px lines, and bars from x about 118 to 177). The picture holds
the caste **names** and a small **picture of each caste**, left of x = 88, and a frame. Rows (each is two 10-px lines,
tops at y = 4, 28, 51, 75, 98, 121): centre each name and picture vertically on **y = 14, 38, 61, 85, 108, 131** (+-3):

| Row | Label | Picture (about 20 x 14, right edge at x about 86) |
|---|---|---|
| 0 | `Larvae` | a grub (pale, curled) |
| 1 | `Workers` | a worker ant, side view, black |
| 2 | `Soldiers` | an ant with a big head (soldier), black |
| 3 | `Males` | a winged ant (wings light grey) |
| 4 | `New Queens` | a winged ant, bigger body |
| 5 | `Queens` | a queen: a huge abdomen with a small head |

Names right-aligned (ending at x about 62), label face black 15 on light grey 12. The pictures must match the ant
sprites' design language (black body, same legs and head shapes), though this is a standalone, side-on drawing.
The layout also holds two small rectangles at the top, (95,3)-(119,22) and (124,4)-(148,23), that the remake never
draws into (probably the two colonies' column heads; not found): keep that part of the text area plain.

## F. Behavior Control and Caste Control (4600, 4601, 4620, 4621)

Two nearly identical windows. **Behavior Control** sets how the colony's workers are split between three jobs; **Caste
Control** sets how the queen's eggs are split between three castes. In each a **triangle** is the control: the pointer
position inside it sets three weights (apex, bottom-left, bottom-right) that sum to 100%, shown by the game as a small
marker drawn over the triangle (a separate sprite). Three coloured **corner boxes** name the three corners and show a
number; **bars** at the right show the three weights.

| File | Size | What |
|---|---|---|
| `4600.pix` | 210 x 170, opaque | Behavior Control's panel. Corners: apex `Forage`, bottom-left `Dig`, bottom-right `Nurse`. |
| `4620.pix` | 210 x 170, opaque | Caste Control's panel. Corners: apex `Breeders`, bottom-left `Workers`, bottom-right `Soldiers`. |
| `4601.pix` | 168 x 168, **masked** | Behavior Control's help overlay, drawn at **(+40, +2) relative to 4600's top-left**. |
| `4621.pix` | 175 x 175, **masked** | Caste Control's help overlay, drawn at **(+35, -1) relative to 4620's top-left**. |

### The panels 4600 and 4620

Light grey 12 background; a column of **buttons** top-left, a **triangle** in the middle, a **bar well** at the right, the
**three corner boxes**. Rectangles in picture coordinates (the same sets for both, the values that differ are given as
`4600 / 4620`):

| Control | 4600 | 4620 | Notes |
|---|---|---|---|
| `Auto` button | (5,5)-(46,16) | (4,5)-(46,16) | **inverted** while automatic is selected |
| `Manual` button | (4,20)-(46,32) | (4,21)-(46,32) | inverted while manual is selected |
| `Set 1` | (4,38)-(46,50) | (4,39)-(46,50) | recalls preset ratios; the three are bevelled buttons with labels `Set 1`, `Set 2`, `Set 3` |
| `Set 2` | (4,54)-(46,66) | (4,55)-(46,66) | |
| `Set 3` | (4,70)-(47,82) | (4,71)-(46,82) | |
| `?` help | (14,88)-(39,100) | (14,89)-(39,100) | small button with a green "?" |
| **triangle** | (48,38)-(159,134) | (48,37)-(157,133) | see below |
| **bar well** | (167,8)-(199,80) | (168,8)-(198,81) | **gauge**, flat white 0 (three bars are drawn here, see below) |
| top corner box (hit) | (86,6)-(121,26) | (80,6)-(127,26) | label above, **value rectangle** below |
| top value | (87,16)-(119,25) | (82,14)-(124,26) | **text rectangle**, flat white 0 (a number or a percentage, black, font 4, centred) |
| bottom-left corner box | (21,144)-(56,164) | (15,144)-(62,164) | |
| bottom-left value | (22,154)-(54,163) | (17,152)-(59,164) | text rectangle, white 0 |
| bottom-right corner box | (154,144)-(189,164) | (148,144)-(195,164) | |
| bottom-right value | (155,153)-(187,162) | (150,152)-(192,164) | text rectangle, white 0 |

- **The triangle.** Apex at the middle of the rectangle's top edge, base along its bottom edge from its left corner to its
  right corner (isosceles). The game maps pointer positions inside that rectangle to weights (apex at `y = top`, base
  at about `y = bottom - 2`, the left and right corners at the base ends), so the picture's triangle must be **that
  triangle within +-2 px**: its **white 0 interior** (flat, nothing in it: the marker is drawn over it) with the
  apex at (rect.left + width/2, rect.top) and the base corners at (rect.left + 2, rect.bottom - 2) and
  (rect.right - 2, rect.bottom - 2). Draw a **raised edge around the triangle outside** the interior: a bright
  highlight edge on the left side and a darker shadow edge on the right side and along the bottom, 2 to 4 px wide, a
  1-px black line between the edge and the interior. The interior has no gridlines, no labelling.
- **The corner boxes.** Each is a small framed box about 35 x 20 (47 x 20 in 4620). **Top half: the label** (label
  face, black, centred): `Forage` / `Dig` / `Nurse` (4600), `Breeders` / `Workers` / `Soldiers` (4620). **Bottom half:
  the white value rectangle** above. **The frame colour of each box is fixed** because the game draws the matching bar in
  the same colour: 4600 `Forage` green **8**, `Dig` tan **11**, `Nurse` cyan **7**; 4620 `Breeders` magenta **4**,
  `Workers` blue **6**, `Soldiers` orange **2**. The frame is 2 px thick; the label's background is white 0. The
  boxes are clickable (they toggle between showing a percentage and a count).
- **The bar well.** One flat white rectangle with a 1-px frame outside it; the game draws three bars from the rectangle's
  bottom up, each **6 px wide** at x offsets 0, 12 and 24 from the rectangle's left (4600: x 167..172, 179..184, 191..196;
  4620: x 168..173, 180..185, 192..197), in the colours of the three corners, each framed black, with the area above
  each bar cleared to white. Under the well (y 82..92, on the well's white), draw **one letter per bar**, black, small
  label face, centred under its column: **`F` `D` `N`** (4600: forage, dig, nurse) and **`B` `W` `S`** (4620: breeders,
  workers, soldiers). Nothing else inside the well.
- The buttons are bevelled; `Auto` and `Manual` must stay readable inverted.
- Between the two windows keep the same layout and style; only labels, frame colours and a few rect widths differ.

### The help overlays 4601 and 4621

Masked, colours **0, 6, 14** only, same callout style as group D. Overlay origin and target rectangles in **overlay
coordinates**; the buttons and the three corner boxes at the left lie partly left of the overlay (x < 0): their leaders
must stop at the overlay's left part within 3 px of the buttons' right edge (x = 6 in 4601; x = 11 in 4621: so tips at
x 3..9 resp. 8..14).

| Callout (what it explains) | 4601 target | 4621 target | Tip |
|---|---|---|---|
| `Auto` / `Manual`: choose automatic or manual control (2 lines) | buttons (-35,3)-(6,14) and (-36,18)-(6,30) | (-31,6)-(11,17) and (-31,22)-(11,33) | **two** short leaders, one to each button (x as above) |
| the three `Set` buttons: recall preset ratios (1 line) | (-36,36)-(6,48) .. (-36,68)-(7,80) | (-31,40)-(11,51) .. (-31,72)-(11,83) | a bracket whose two ends reach the first and the third button |
| the **triangle**: move the cursor inside to change the current ratios (3 lines) | (8,36)-(119,132) | (13,38)-(122,134) | a leader ending with a dot **inside** the triangle (y >= 36 / 38) |
| the **bars** (the relative setting of the three jobs / castes) | (127,6)-(159,78) | (133,9)-(163,82) | the panel **overlaps** this rectangle; no leader needed |
| the **corner boxes**: click to toggle the display (2 lines) | the two bottom corner boxes (-19,142)-(16,162) and (114,142)-(149,162) | (-20,145)-(27,165) and (113,145)-(160,165) | two leaders from a panel between them (arrows pointing outward), tips inside the boxes (4601: x 0..15 and 114..147; 4621: x 0..26 and 113..160) |

Panels may cover the triangle (the player is holding help, not dragging) but **not** the three corner boxes' rectangles
nor the bar well beyond what is said. A panel needs at most about 130 px of width.

## G. The History window (16000, 16001)

### 16000: `16000.pix`, 320 x 179, opaque, 4 planes

The **History** window: a line **graph** of up to four series (colony populations, food, health, deaths over the
last 64 samples), and under it a grid of ten **toggle buttons**. The game draws the graph lines and number labels
itself into the white well; a toggled-on button is **inverted** (no other pressed state).

| Control | Rect | Notes |
|---|---|---|
| **graph well** | (4,4)-(315,131) | a **gauge**: flat white 0, no gridlines (the game draws lines, with 8-px margins, in red 3, blue 6, dark green 9 and purple 5, with framed numeric labels near the right end); frame it outside |
| `Pop` (black colony) | (36,138)-(77,153) | **inverted** when plotted |
| `Pop` (red colony) | (36,160)-(77,175) | |
| `Food` (black) | (85,138)-(126,153) | |
| `Food` (red) | (84,160)-(125,175) | |
| `Health` (black) | (132,138)-(174,152) | |
| `Health` (red) | (132,160)-(174,174) | |
| surface food | (187,138)-(229,152) | a series that has no colony row |
| starved (ants died of hunger) | (235,138)-(277,152) | |
| eaten by enemies (the spider, ant lions) | (187,160)-(229,174) | |
| killed in fights | (235,160)-(277,174) | |
| `?` help | (285,151)-(311,163) | small button with a green "?" |

Two **row labels** at the left of the two colony rows: **`Black`** (black 15) at y 138..152 and **`Red`** (red 3) at
y 160..174, right-aligned to x about 34. Seven distinct captions (ten buttons), the words above, short, black 15 on light grey (the four
on the right may be coloured green 9, brown 10 etc., any dark colour; they must read inverted too), at most 38 px wide
(`Pop`, `Food`, `Health` and four short words of your own, e.g. `S.Food`, `Starved`, `Eaten`, `Killed`). A thin divider
at x about 281 between the six colony buttons and the four others is fine. Flat light grey 12 elsewhere.

### 16001: `16001.pix`, 247 x 144, **masked**, 4 planes

The help overlay, drawn at **(+45, +20) relative to 16000's top-left**, colours **0, 6, 14** only, callout style of group D.
Callouts:

1. A panel placed **inside the graph well** (about x 40..250, y 2..50 in overlay coordinates): a help sentence (2 lines)
   telling the player that holding the button down in the white area shows the current values. No leader.
2. Seven panels naming the series, each with a **blue leader dropping to the first row of its button(s)**. Tip rules:
   the last leader pixel is in the first row of the target rect (y = 118 for the top row) and inside its x-range.

| Callout | Target rect (overlay coordinates) | Tip |
|---|---|---|
| both colonies' population | `Pop`: (-9,118)-(32,133) | x 0..31, y = 118 |
| both colonies' food in the nest | `Food`: (40,118)-(81,133) | x 40..80, y = 118 |
| both colonies' health | `Health`: (87,118)-(129,132) | x 87..128, y = 118 |
| food available on the surface | (142,118)-(184,132) | x 142..183, y = 118 |
| black ants eaten by predators (the spider, ant lions) | (142,140)-(184,154) | y = 140 (the leader passes over the button above it), x 142..183 |
| black ants that starved | (190,118)-(232,132) | x 190..231, y = 118 |
| black ants killed by red ants or the human | (190,140)-(232,154) | y = 140, x 190..231 (passes over the button above) |

The seven panels must lie in rows 0..117 (above the button rows, which start at y = 118; the first callout and these
panels all lie over the graph's well, which is fine while help is held). They are tall, narrow panels with **text
rotated 90 degrees** (the seven leaders are only 23 to 48 px apart, so a panel is at most 22 px wide); you may instead
lay them out as staggered horizontal panels with diagonal leaders, but panels must not overlap each other, must not
reach the button rows (y >= 118) and every leader tip must obey the rule. The leaders' x positions in the original are
12, 59, 107, 151, 175, 200 and 223 (any x inside the target's x-range will do).

## H. The Status window (13000) and the Game Over window (16100)

### 13000: `13000.pix`, 312 x 180, opaque, 4 planes

The **Efficiency Score / Status** window: how well the colony is doing. A title, two columns of four figures, and a panel
at the bottom with two lines of text. The game writes the numbers and lines itself.

Baked in: a title **`STATUS`** (display lettering, top, y 2..22, centred), two column headings in blue 6: **`COLONY`** (left
column, centred about x = 74, y 32..40) and **`UNIVERSE`** (right column, centred about x = 238, y 32..40); then two columns of
four **labels** (y 48..112) each ending in a short horizontal **leader line** that runs to the value that follows. Left
column (x 10..110): `Colony Health`, `Foraging`, `Eggs Hatched`, `Fights Won`; right column (x 168..270): `Colonies Started`,
`Colonies Held`, `Yard Filled`, `House Filled`. A **framed panel** at the bottom (x 10..303, y 119..169: a 2-px bevelled
frame, white highlight on the top and left, dark shadow on the bottom and right, **flat light grey 12** inside)
containing the two message lines.

| Rect | What the game writes there |
|---|---|
| (112,47)-(155,63), (113,63)-(156,79), (113,80)-(156,96), (113,98)-(156,114) | the four colony values ("NN%"), font 0, black on **flat light grey 12** (text rectangles; the leader lines must end at x <= 110) |
| (272,45)-(310,63), (272,62)-(310,80), (272,79)-(310,97), (272,96)-(310,114) | the four universe values, font 4, black on flat light grey 12 (leader lines end at x <= 270) |
| (13,123)-(299,141) | first message line (text rectangle, font 4, blue 6 on flat light grey 12) |
| (13,146)-(299,164) | second message line (text rectangle, blue 6 on flat light grey 12) |
| (10,170)-(305,179) | a third line, black font 3 on flat light grey 12, below the panel |

The rows of labels sit level with the rows of value rectangles (a label's lettering centred on its row). Everything else
flat light grey 12; the panel frame and the title must be drawn **outside** the text rectangles. Not inverted anywhere.

### 16100: `16100.pix`, 321 x 201, opaque, 4 planes

The **Game Over** window shown when the game ends: a big title, a framed panel with two captions: the final score and the
player's rating, and three lines the game writes. (Only 320 x 200 is shown: the last column and row are cut off.)

Baked in: a title **`GAME OVER`** (display lettering about 18 px high, centred, y 14..32, in red 3 with a black or dark
shadow, between two small ant-shaped ornaments (optional)); a horizontal **divider** under it (y 44..47, 4 px: grey, black and white
lines); a **bevelled panel** (white highlight on the top and left, dark shadow on the bottom and right; x 47..275,
y 61..188) with two **captions** (label face): **`FINAL SCORE`** in red 3 at y 73..83, underlined at y 88..89, and **`YOUR RATING`** in
blue 6 at y 135..145, underlined at y 150..151 (both centred, x about 105..210).

| Rect | What the game writes there |
|---|---|
| (49,92)-(270,106) | the mode's name (e.g. the kind of game), font 4, black on **flat light grey 12** |
| (49,104)-(270,118) | the score, black, font 4, flat light grey 12 (the rect overlaps the line above by 2 rows) |
| (50,154)-(268,168) | the rating's title, blue 6 on flat light grey 12 |

The three text rectangles and their surroundings inside the panel are flat light grey 12; the captions' text and underline
lie above y = 90 and above y = 152 so they do not touch the text rectangles.

## I. The win screen (16200) and its eyes (16210..16212)

### 16200: `16200.pix`, 254 x 199, opaque, 4 planes

The picture of the **ending of the Full Game** (shown in a bevelled frame for about 10 s while the victory tunes play):
the yard's three pests, **a person, a cat and a dog**, startled and fleeing from the ants. It is a comic illustration
(full colour, black outlines, flat shading, at most 16 colours); the mood is "they have lost". There is **no ant in
it**: the ants have won.

The **eyes are drawn by the game** over the picture, three 13 x 13 sprites at fixed positions (x, y = the sprite's
top-left corner): **(72,74), (87,66)** for the person, **(175,64), (191,66)** for the cat, **(159,122), (179,124)** for the
dog (each pair is one creature's two eyes; the pair's spacing and tilt tell you how its head is turned: the person's
pair is 15 px apart and rises to the right, the cat's 16 px and falls slightly, the dog's 20 px and falls slightly). The
picture must therefore show each creature's face so that an eye of 13 x 13 fits exactly where given, with face around
it, and nothing important (a nose, a mouth) under a sprite's square (so the eyes' neighbourhood is face colour only).
Draw the eye sockets as plain light discs or leave them to the sprites (the sprites are opaque inside their round
outline and cover them). The positions put the person on the left of the picture, the cat at the upper right and the
dog at the lower right; compose the rest (bodies, limbs, the ground) yourself so the picture reads as three pests in
panic. Do not copy a known cartoon, comic or game; the creatures are yours.

### 16210, 16211, 16212: `16210.pix`, `16211.pix`, `16212.pix`, 13 x 13 each, **masked**, 4 planes

**One eye, three frames.** The game shows frame 0, 1, 2, 0, 1, 2 ... (one change every 8/3 of a game tick, about 7 a
second) on all six eyes at once while the win screen runs (about 10 s), so the eyes "come alive". Each frame is a round
**eyeball disc**: the corners transparent (24 `.` pixels, the four corner arcs of a 13 x 13 circle; **the same 24 in all
three frames**), white 0 sclera, a **black 15 pupil** near the centre and **red 3** and **light grey 12** details. The
three frames must differ so that cycling them 0, 1, 2, 0, 1 reads as a lively, panicked animation (your choice: a
pupil that shrinks and grows, a moving highlight, trembling veins ...); frame 2 must lead back into frame 0. Only
colours 0, 3, 12, 15.

## J. Tutorial pictures (17000..17013)

The tutorial's step windows show **a picture above their text** when the step talks about a thing: each picture is the
thing, small, so the player knows what to look for. The picture is drawn **centred above the text on a light-grey
box** (its own pixels all opaque, no transparent). All **opaque, 4 planes**; give each a 1-px black or dark grey frame
unless it is already a framed button. Sizes are exact.

| File | Size | Shows | Used in step about |
|---|---|---|---|
| `17000.pix` | 22 x 16 | the **player's ant**: a yellow ant seen from above on tan ground (a sandy tile) | "you are the yellow ant" |
| `17001.pix` | 53 x 16 | the **surface strip at the top of the nest**: sky (cyan 7) over a grass band, a thin brown 10 soil line at the bottom: the place to dig to reach the surface | "dig a tunnel up through the blue" |
| `17002.pix` | 19 x 18 | **food**: two green morsels (8 / 9) on tan ground | "get to the food" |
| `17003.pix` | 53 x 48 | **the nest entrance**: a round dark hole in soil with a mound or ring around it, on ground | "get back into your nest" |
| `17004.pix` | 20 x 18 | **a small rock**: a grey stone (13 with 12 highlight top-left and 14 shadow) on tan ground | "pick up the rock" |
| `17005.pix` | 41 x 30 | **the Map window's `Yard` button** (view picture and bevel, no label): **a crop of your 14000, (2,3)-(43,33)** (the button's rect (5,5)-(42,31) plus its bevel) | "click the YARD icon" |
| `17006.pix` | 37 x 29 | the yard window's **`House`** toolbar button: a picture of the house from the front, its lawn, in a bevelled button (labels are not part of it) | "click HOUSE" |
| `17007.pix` | 41 x 30 | the yard window's **`Patch`** toolbar button: the ground view with food and ants as dots, in a bevelled button | "click PATCH" |
| `17008.pix` | 25 x 20 | the **Behavior Control button** (the `B` triangle) of the Map toolbar: **a crop of your 14000, (262,24)-(287,44)** (its rect (264,25)-(287,43) plus bevel) | "click the B triangle" |
| `17009.pix` | 25 x 20 | the **`?` help button** of the Map toolbar: **a crop of 14000, (366,24)-(391,44)** | "hold the ? button" |
| `17010.pix` | 75 x 21 | **the population gauges**: a pair of bars, `P` above `H`, black 15 on white 0 (a long white bar, a short black fill), as the report panel's gauges in 14000 (see E); 75 x 21 | "look at the bars at the lower right" |
| `17011.pix` | 25 x 20 | the **Caste Control button** (the `C` triangle): **a crop of 14000, (288,24)-(313,44)** | "click the C triangle" |
| `17012.pix` | 21 x 16 | the **Center-on-Yellow button's face** (a yellow ant with a marker): **a crop of 14000, (291,5)-(312,21)**, no bevel | "click the yellow ant icon" |
| `17013.pix` | 84 x 65 | a **vertical health gauge** (the same idea as the Edit window's yellow bar, bigger): a framed tall bar about 18 px wide filled yellow 1 about 60 % from the bottom, a **horizontal threshold line** across it a little lower (black or brown 10), a small tab with a yellow **`Y`** under the bar, and at the right **two short labels of your own wording** (label face, black, each with a leader line): one naming the ant's health (it points at the top of the fill), one naming the level below which it eats (it points at the threshold line) | "it eats only when health is below the line" |

Constraints:

- 17005, 17008, 17009, 17011, 17012 show buttons that **also exist in 14000** (the Map toolbar): **copy them from your
  own 14000 by script** (a crop with the bevel) so a player recognises the button. 17006 and 17007 show two buttons of the
  yard window's toolbar (bitmap 7010, made in a later batch: that batch will be told to match these; draw them as
  plain 3-D buttons now). 17010 matches the gauges of 14000's report panel in form.
- 17000, 17002, 17004 and the ant in 5103 show things that **also exist as map sprites**: keep your ant (yellow body with
  black outline, six legs, two feelers) and your food and rock consistent with what the sprites will look like. The spec
  side will check them against the finished sprite sheets and may replace them by crops of the sprites.
- Step 11 refers to a picture **17014 which does not exist in the game** (the box then shows no picture): no file is
  needed.

## K. The encyclopedia button strips (21004 and 21005)

**1-plane, 320 x 20, opaque** (only `0` white and `f` black). The row of buttons at the bottom of the **encyclopedia
window**'s card (drawn over the card's last 20 rows). They are **pictures of buttons** (the click areas are in the card
data; the remake draws the picture as it is):

- `21004.pix`: three buttons `BACK` (go to the parent card), `PREVIOUS` (the card seen before), `TOP` (the first
  card). Hit rectangles (the visible boxes must cover them): **BACK (17,4)-(81,17)**, **PREVIOUS (128,4)-(192,17)**,
  **TOP (239,4)-(303,17)**.
- `21005.pix`: only `PREVIOUS`, at **(128,4)-(192,17)**; nothing else drawn (the strip's background only).

Both: the background of the strip is a **50 % checkerboard** of black and white (`f` and `0` alternating by (x + y)
parity), which reads as mid grey; each button is a **white box with a 1-px black outline and a 1-px black shadow at
right and below** (box about 66 x 15, rows 3..17), its caption in **black capitals centred** (label face, about 7 px
high). The strip must meet the card above: the first row (y = 0) is a solid black line (a divider).
Two cards of the data (ids 127 and 129) have other, four-button hit rectangles; no card can reach them, so ignore them.

## L. The start-up cards (28000 and 28003)

**Not drawn by the remake** (nothing in the code or the data refers to them); they are the original's start-up splash
pictures (two sizes of the same card). They are a **publisher's logo**, so they must be **replaced**, not recreated.
Make **neutral cards**: black 15 background, an **emblem of your own design** in the upper half (an
abstract mark that is not a ball with a banner, not a letter monogram and not the project's name), and under it a **single
line of lettering** that carries no name of a company, author or product (for example three words such as `AN OPEN FAN
PROJECT`), in your display lettering, 3 to 5 colours in it. Both are **opaque, 4 planes**:

| File | Size |
|---|---|
| `28000.pix` | 263 x 204 |
| `28003.pix` | 257 x 195 |

The two are the same card redrawn at its own size (not scaled from each other: the pixels are drawn for each size).

## The script's checks

`make_ui_bitmaps.py` must **assert** (fail the build of the files) that:

1. every file has its **exact size** (the table size: 15 x 15 etc.), contains only valid characters, and has the right
   masking (the masked set above has `.`, all others none; 21004 / 21005 only `0` and `f`);
2. every **text rectangle** and **gauge** listed above is a single colour (the one given) and **icon spots** are flat
   light grey 12 in the whole item rectangle;
3. **5100..5106 are pixel-identical** to the icons inside 5000 at (4, 4 + 17 k);
4. **109 and 111** are both 15 x 13; the sizes of the copies in group J match their sources (17005, 17008, 17009,
   17011, 17012 equal a crop of 14000 up to the bevel);
5. every **leader tip** you draw falls inside the **target rectangle** (or within 3 px of it where the table says so);
   record the tips (one `(x, y)` per leader) in the script and assert on them;
6. overlays contain **only colours 0, 6, 14** and `.`; the opaque pixels of 15001 at x < 40 are only leader lines
   (at most 1 px thick) and the 4601 / 4621 panels do not cover the corner boxes;
7. every **inverted** rectangle passes the 3 : 1 contrast test (on the dominant light colour of the face versus the
   dominant dark lettering colour, as drawn and `XOR 15`) in the files of groups B, D, E, F, G;
8. the frame colours of the six corner boxes of 4600 / 4620 are exactly 8, 11, 7 and 4, 6, 2, the triangle's interior is
   flat white 0 and inside the given triangle (apex at the top middle of its rectangle) within 2 px;
9. 16210..16212 have the **same 24 transparent pixels**; 4501, 4503, 4505 contain only colours 0, 13, 15;
10. no picture contains a transparent pixel unless it is in the masked set.

`python tools/clean_pack/build.py` then packs the files (`HCEGANT/2/<id>.bin`); the spec side runs the game with
`-- --clean --pack=remake/build/dev_pack.zip`, checks every window in place and compares the look with the originals
for similarity before the pack ships.

## Previews

`preview.png`: (1) a contact sheet of all 74 pictures at 3x on a mid-grey background (masked ones on magenta); (2) each
window as it appears in the game, assembled by the script from your pieces at the given offsets: Edit window strip
with its help overlay, Map window toolbar with its overlay, the two control panels with overlays, the History window
with overlay, Status, Game Over, the three menus; (3) the **inverted** state of each highlight rectangle next to its
normal state.

## Consistency between the pictures

- The five scent pictures (14000, 6000's swatches) and the nest / surface / queen pictures (15000, 14000) are the same
  subjects: draw each subject once and reuse it.
- Colony colours: **black colony = black / dark grey, red colony = red 3**, the player = yellow 1, everywhere.
- The corner boxes' frame colours (group F) are fixed by the game's bar colours.
- The label faces are one face everywhere; overlays use the small face.

## Not found / open

- **Chrome icons 101, 102, 104, 106, 107, 108, 110, 113**: no layout, no code in the remake and no original behaviour I
  could trace draws them (the engine's window decorations draw 100, 103, 105, 109, 111, 112 and, by flags no window sets,
  101 and 102). They are spares; their symbols above are guesses of what a window toolbox needs. If one turns out to be
  used, the spec side will fix its description.
- The **close, zoom and document icons' click behaviours** are not implemented in the remake; only their pictures and
  places are.
- Where the original clips a help overlay that is larger than its layout rectangle (4601, 4621: 168 and 175 against 164
  and 169) is not known: keep all callout content within the layout rectangle's size (164 x 164 in 4601, 169 x 169 in
  4621) and the leader tips as given; the remaining rows and columns are transparent.
- **Mouse-down appearance** of buttons: the remake only highlights (inverts) buttons that are selected or under the
  pointer; a separate pressed picture is not used anywhere.
- The two **start-up cards** are never shown by the remake; they are made to keep the pack complete.
