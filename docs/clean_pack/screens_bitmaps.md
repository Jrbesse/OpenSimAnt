# Spec: the title, game-select and about screens, the event icons and the event scenes

> **Status (2026-10-31):** complete, ready for a maker (3 passes, see "How to work"). Written from the remake's code
> (`Main.cs`: the title, Select a Game, the About box, the scene window 26 and the message boxes; `UiArt` / `Ui.cs`: how
> pictures and hotspots are drawn and hit), the window layouts (windows 2, 3, 26, 30, 31) and the game's own tables
> (scene timings and overlay positions). Covers **24 bitmaps**. The encoder and its checks are in
> `tools/clean_pack/build.py` (`cat_bitmaps`: the same `.pix` files and rules as `ui_bitmaps.md`; **no build change needed**,
> all 24 are opaque 4-plane pictures). What could not be traced is said where it comes up ("not found", and the closing
> section).

Output folder: `remake/game/assets/clean/src/bitmaps/` (shared with `ui_bitmaps.md` and `yard_bitmaps.md`; **only create
files for the 24 ids of this spec**, see "Files and other batches"). Provenance: `remake/game/assets/clean/PROVENANCE.md`
(add an entry). **One file per bitmap, named `<id>.pix`** (for example `2500.pix`), plus
`make_screens_bitmaps.py` (the script that writes every `.pix`, so they can be regenerated; split it into modules if you
like), `README.md` (the design: the colour roles, the scenes' construction, how to rebuild) and, recommended, `preview.png`
(see "Previews").

## Contents

- Scope - How to work - Files and other batches - Format and rules for every file - Identity and wording - How the game shows these pictures - Look
- Groups: A title (2000, 2001), B Select a Game (2500), C About box (3000, 3001), D the player's-ant pictures (9100, 9101, 9110, 9111),
  E event icons (9150..9156), F the ant lion scene (9200..9203), G the spider scene (12000..12003)
- The script's checks - Previews - Consistency with the other batches - Not found / open

## Scope

The HCEGANT type-2 bitmaps with ids 2000..2999, 3000..3999, 9000..9999 and 12000..12999: **24 files**, all **opaque**, all 4-plane.

| Group | Ids | Count | What |
|---|---|---|---|
| A | 2000, 2001 | 2 | the title screen, in two halves (one above the other) |
| B | 2500 | 1 | the "Select a Game" dialog's picture (six buttons) |
| C | 3000, 3001 | 2 | the About box's background and its name card |
| D | 9100, 9101, 9110, 9111 | 4 | scenes about the player's own ant: killed, reborn / now a worker, fed by a nestmate (and the feeding's second frame) |
| E | 9150..9156 | 7 | the 32 x 32 icons of the message boxes that tell how the player's ant died |
| F | 9200..9203 | 4 | the ant lion takes the player's ant: the scene and its three animation patches |
| G | 12000..12003 | 4 | the spider takes the player's ant: the scene and its three animation patches |

**Not in this spec**: every other HCEGANT bitmap (`ui_bitmaps.md`, `yard_bitmaps.md`), the SHARED bitmaps (SimAntipedia,
a later batch), the lettering **text** the game writes over these pictures (the captions of 9100 / 9101 and the credits that
roll in the About box are strings, in the text category) and all sound and music.

## How to work

Three passes, each ending with a build of what exists (`python tools/clean_pack/build.py` refuses a wrong size, a missing mask or an opaque
picture with holes) and with the script's assertions (see "The script's checks"):

1. **Pass 1: the screens (A, B, C):** 2000, 2001, 2500, 3000, 3001 (5 files). Do the identity wording first (see "Identity and wording"),
   then the fixed rectangles of 2500 and 3000, then the artwork. One script function per screen; draw the title as **one 512 x 372 canvas** and cut it in two.
2. **Pass 2: the event icons and the player's-ant pictures (E, D):** 9150..9156, 9100, 9101, 9110, 9111 (11 files). One helper for the icons' frame and
   their ground colours; one drawing program for the ants (the player's yellow ant and the dark nestmate) shared by 9100, 9101, 9110 and 9111.
3. **Pass 3: the two attack scenes (F, G):** 9200..9203, 12000..12003 (8 files). Each scene is **one drawing program with a "state" parameter**;
   the base picture (9200 / 12000) is the state "at rest" rendered in full, and each patch (9201..9203 / 12001..12003) is **a crop of the same
   program's render in another state**, so that its edges match the base by construction.

Rely on the script's assertions rather than on looking at pictures: **look at `preview.png` at most 5 times per pass** (a pass is one
of the three above; a rebuilt preview counts again).

## Files and other batches

- **Do not open any other file of the repository**, with these exceptions (clean-pack sources made by other makers, never the
  original's data): if they exist when you start, `make_ui_bitmaps.py` and `uilib.py` in your output folder (the interface batch:
  its pixel lettering and bevel helpers, which you may import or copy) and `17000.pix` (the yellow ant on tan ground) so that the scenes' ant
  matches it; and `remake/game/assets/clean/src/sprites/` (the ant sprite sheets: the look of the yellow, black and red ants), and
  `remake/game/assets/clean/src/fonts/` (the faces) if you want to draw lettering from the game's own new fonts.
- **Never overwrite or delete a file that is not in your 24.**

## Format and rules for every file

- `.pix` as in `docs/clean_pack/README.md` (one line per pixel row, one character per pixel: `0`-`9`, `a`-`f` a palette index, `#` comment lines,
  every row the same length). **All 24 pictures are opaque: no `.` anywhere.** **The size of each picture is exact** (the game places things by pixel;
  the build rejects another size). The sizes are in the tables.
- The palette is the Apple 16 colours of `README.md`. Their values (for contrast and colour judgement): 0 `FFFFFF`, 1 `FCF305`, 2 `FF6402`,
  3 `DD0806`, 4 `F20884`, 5 `4600A5`, 6 `0000D4`, 7 `02ABEA`, 8 `1FB714`, 9 `006411`, 10 `562C05`, 11 `90713A`, 12 `C0C0C0`, 13 `808080`,
  14 `404040`, 15 `000000`. Everything is drawn at 640 x 480 with no scaling and no anti-aliasing; use flat colours, hand-placed (or ordered) dithering,
  no gradients as such.
- **Coordinates** in the tables are pixels from the picture's own top-left corner, **x1 / y1 exclusive** (a rectangle `(5,25)-(68,88)` is 63 x 63
  pixels), unless the word "screen" is used (640 x 480 screen pixels).
- **Do not copy** another game's art, its characters or its logo. The roles, sizes, rectangles and timings are fixed by the game; the drawing is yours.
  Where this spec says "steer away", it names what the picture must **not** look like: take that seriously, the pack is reviewed for similarity
  with the original before it ships and anything too close is remade.
- **Contrast.** Every piece of lettering must have a contrast ratio of at least 3 : 1 against the colour behind it (computed from the colour values above).

## Identity and wording

The pack carries the project's own identity (the name is **OpenSimAnt**). **No picture may contain the word "SimAnt" except as part of the
word "OpenSimAnt", never "Maxis", a publisher's, author's or tester's name, a year, a logo or a trademark symbol.** The script's own
strings are checked (see "The script's checks"). The words to letter, **exactly** (capitalisation and punctuation as given; you choose the face, size and colour):

| Where | Text |
|---|---|
| the title (A) | `OpenSimAnt` once, large; and one small line `an open-source remake` (optional, but recommended) |
| the About box's background (C), its heading | `About OpenSimAnt` |
| the About box's background (C), its footer line | `A fan project. Not an official game.` |
| the About name card 3001 (C) | three lines: `OpenSimAnt` (large) / `an open-source remake` / `a fan project` |
| the Select a Game picture (B), its heading | `Choose a Game` |
| Select a Game, the six labels (function words: use these words or a plain synonym of the same length) | `Tutorial`, `Quick Game`, `Full Game`, `Experimental`, `Load Game`, `Cancel` |
| Select a Game, the five descriptions | **new wording** of the meaning given in group B, never a remembered sentence |
| the event icons and scenes (D to G) | **no lettering at all** (the game writes the captions and messages itself) |

All lettering is English and yours (pixel lettering drawn by your script; a pixel face of your own, or the interface batch's).

## How the game shows these pictures

Read this first; most constraints come from it.

1. **The screen is 640 x 480.** Pictures are drawn at their window's top-left, unscaled, opaque. The game's windows have a grey 12 face, a 3-D frame
   drawn **outside** the picture by the game, and the pictures cover the window's inside.
2. **The title (window 3).** At start-up the game clears the whole screen to **black 15** and draws two pictures one above the other at
   **screen (64,63)** (2000, 512 x 172) and **(64,235)** (2001, 512 x 200): together **one 512 x 372 picture at screen (64,63)-(576,435)**, centred
   horizontally (64 px of black each side) and 63 px of black above, 45 below. Nothing is drawn over it; the game theme plays; **a key or a click, or 40 seconds, ends it** and shows Select a Game.
3. **Select a Game (window 2).** Drawn when the title ends, on F2 / File > New (with a game running, over the desktop) and after Game Over. The window is
   the 3-D frame **screen (163,107)-(485,365)** and the picture 2500 at **screen (164,108)** (320 x 256). **The picture is the whole dialog: there are no separate buttons.**
   The game defines **six invisible hit rectangles** over it (a click inside one acts; **the game draws nothing on them: no highlight, no pressed state**; a click anywhere else does nothing),
   so the picture must draw the six buttons itself, in these rectangles (relative to the picture):

   | Button | Rect (x0, y0)-(x1, y1) | Size | What the click does |
   |---|---|---|---|
   | Tutorial | (5,25)-(68,88) | 63 x 63 | starts the tutorial game |
   | Quick Game | (175,25)-(238,88) | 63 x 63 | a small game, one black colony against one red |
   | Full Game | (101,94)-(164,157) | 63 x 63 | the full game: the yard and the house with many colonies |
   | Experimental | (5,163)-(69,226) | 64 x 63 | a sandbox game, no rules to win |
   | Load Game | (175,163)-(238,226) | 63 x 63 | opens the file dialog to load a saved game |
   | Cancel | (100,232)-(166,249) | 66 x 17 | closes the dialog (continues the running game, or leaves) |

4. **The About box (window 31).** Opened by the Help menu's About. The window is the 3-D frame **screen (176,117)-(498,319)**; the background **3000
   at screen (177,118)** (320 x 200); and, in the **item rectangle R = picture (33,61)-(287,171)** (screen (210,179)-(464,289): 254 x 110), the game shows in turn:
   **first the name card 3001** (254 x 109, drawn at R's top-left, opaque) **for about 5 seconds**; then **it stops drawing 3001, fills R with light grey 12 and
   scrolls the credits text (black 15, 14-px lines, centred) up through R**, one pixel at a time, with a pause after the first line; at the end the card again, and so on;
   a key or click moves on (card -> credits -> closes). So: **R is always completely covered** (by 3001, or by the game's grey 12 fill and the text) and **3000 is visible
   only outside R**; and what 3000 holds inside R is never seen.
5. **The scene window (window 26) and its scenes.** The event scenes (groups D, F, G) are shown **only when "Events" is on in the Options menu**, each in the same
   window: the picture is drawn at **screen (153,85)**; the game draws a **grey 12 fill and a 2-px black 15 frame** around it (screen (151,83) outward, 2 px
   outside the picture: the picture's own edge needs no frame), and
   - **overlays (patches)** are opaque pictures drawn at a fixed offset over the base picture: they replace the rectangle they cover (so they must match
     the base at their edge, see "Alignment of the patches");
   - for 9100 / 9101 the game **writes a caption** (one line of text) in the **top 15 rows of the picture** (picture rows 0..14, the full width): the strip is
     filled with dark grey 14 and the text is written over it in yellow 1, centred. **Nothing you draw in rows 0..14 of 9100 and 9101 is seen**; keep them plain ground;
   - the scene lasts until a key or click, or the time given per picture.
6. **The message box (window 30) and the event icons.** When the player's ant dies of certain causes and Events is on, the game shows a message box (a 3-D frame on a
   light grey 12 face, a text of three lines, "Click here to continue" at the foot) and **draws the cause's icon (one of 9150..9156) at the box's top, centred
   horizontally, with its top-left corner 0 px below the box's top edge and a 2-px gap before the first text line**. The box is at least 58 px wide, so a 32-px icon fits. The icons are opaque squares on the grey face.
7. **Nothing here is recoloured, masked or inverted.** The pictures are drawn exactly as they are.

## Look

A **16-colour pixel-art** look, drawn like the rest of the pack: flat colours, a black 15 outline on the creatures, light from the top-left, dark and light tones from the palette's
brown / tan / grey ranges for ground and creatures, the full palette for the title and the Select card icons. The scenes are **close-ups, "movie stills"** of insects, big in the frame.
The mood: a friendly nature documentary with a little humour; **nothing gory** (the event pictures show what happened to the ant by a symbol or an implied pose, not a body).

**Colour roles (as in the rest of the pack):** the **player's ant is yellow (colour 1 body, with 2 orange for a few shade pixels, 15 outline)**; the **black colony's ants are dark grey (14 body, 13 shade, 15 outline)**;
the **red colony's ants are red (3, with 2 orange shade)**; the spider is browns and greys (10 to 15; the same family as the yard's spider); green (8 / 9) is for food and plants. Use colour 1 **only** for the
player's ant in the scenes D, F and G (so he is always recognised) and, in the icons, only where a yellow thing is the subject.

# Groups

## A. The title screen (2000, 2001)

| File | Size | Where (screen) | What |
|---|---|---|---|
| `2000.pix` | 512 x 172 | (64,63) | the **top part** of the title |
| `2001.pix` | 512 x 200 | (64,235) | the **bottom part**: the two halves are cut from one 512 x 372 picture, so **row 171 of 2000 and row 0 of 2001 are neighbours** |

Both opaque. **The role:** the first thing a player sees: a poster. It carries the name **`OpenSimAnt`** (large, the main element; exactly one occurrence, see "Identity and wording") and,
smaller, `an open-source remake`. Everything else is picture: ants, a colony, a lawn, the sky, as you choose, but the picture must say "ants" and "a colony game" within a second.

- **The picture is on a black screen:** its **outermost pixel ring (all four edges of the 512 x 372 canvas) is black 15**, and the picture should fade into black at the edges
  (no hard-edged rectangle against the screen). The game draws nothing else, so the composition is free inside 512 x 372.
- **Cut the picture in two with one script function**: draw the 512 x 372 canvas, then `2000 = rows 0..171`, `2001 = rows 172..371`. **The seam (between row 171 and 172) must be invisible**:
  do **not** put the wordmark, an outline or a thin line exactly on the seam; a large shape may cross it.
- **Wordmark:** your own lettering, **at least 22 px tall**, set as **plain flat text — one solid colour, no outline, no shade, no highlight, no shadow, no gradient** (the name is never typeset, kerned or otherwise styled like a logo — the public-release gate's hard requirement), reading well against what is behind it (contrast >= 3 : 1).
  `OpenSimAnt` must appear as one word with the capitals as written (the three capitals O, S, A make it legible: lettering them in your own style is fine).
- **Steer away from** the original's composition: **do not** make a front-on giant ant head filling the lower half, a V-shaped blue frame or blue lines, a word arched over the top in an
  orange-yellow gradient, or red / black framing lines. **Do** pick one of these (or your own, as long as it is a different layout): (a) a **cut-away "ant farm" strip**: a thin sky and lawn band
  at the top, the name over it, tunnels and chambers with tiny ants below; (b) **a column of ants marching diagonally** across the picture, carrying leaf pieces and crumbs, towards a hill on the
  right, the name large on the left; (c) **a night scene**: a dark hill with lit tunnel mouths and small ants, a moon, the name in warm light. Name your choice in your `README.md`.
- The palette is free. At most **40 %** of the canvas may be black 15 (so it is a picture, not a black screen with a word).

## B. Select a Game (2500)

| File | Size | Where (screen) | What |
|---|---|---|---|
| `2500.pix` | 320 x 256 | (164,108) | the dialog: a heading, five picture buttons with captions, a Cancel button |

Opaque. **The role:** the dialog from which the player picks how to start. The six hit rectangles of "How the game shows these pictures" 3 are fixed (they are measured from the layout;
the game tests clicks against exactly them): **the picture must draw a button in each**, and the captions beside them. **Outside the buttons, captions and heading the picture is flat light grey 12**; its **outermost ring is
also 12** (the game draws the 3-D frame outside it).

- **Heading** (`Choose a Game`): centred horizontally, in **rows 2..22**, colour 15 or a dark colour of your choice, **bold, 9 to 16 px tall**.
- **The five picture buttons** (Tutorial, Quick Game, Full Game, Experimental, Load Game): each is a **picture of its subject, filling its hit rectangle exactly** (63 x 63 or 64 x 63), with a **1-px
  black 15 outline on the rectangle's outermost ring** and a raised bevel just inside it (white 0 highlight on top and left, dark grey 13 or 14 shadow on bottom and right, 1 px), so it looks like a button. Each picture uses
  **at least 6 colours** and no colour covers more than 70 % of its rectangle. Subjects (your own compositions: the **subject** is fixed, the drawing is yours):
  - **Tutorial**: an ant **learning**: for example a small ant with a pointer in front of a board, or an ant reading a book. Ground or background of your choice.
  - **Quick Game**: **one black ant and one red ant facing each other** (the two colonies of the small game). Use the colony colours of "Look".
  - **Full Game**: the **yard from above with its grid of patches**: a lawn with a house corner or a fence, a grid of cells, a few cells coloured black and red.
  - **Experimental**: a **sandbox / a free-play toy**: for example a heap of soil with a spade and a magnifier, ants walking around a toy, or a beaker over an anthill. It says "try anything".
  - **Load Game**: **a saved game coming back**: for example a folder or a drawer with a sheet sliding out, or a disk in your own colours. **Not** a blue floppy disk with a yellow arrow.
  Pick a **different background colour** for each button (the five tiles are told apart at a glance).
- **Captions**: each button's caption is **to its right** (this is where the game's layout leaves room), **left-aligned, a title line (the label, bold, 9 to 11 px tall) and a one- or two-line description** under it
  (smaller, regular, 7 to 9 px tall), in the **caption zones** below. All caption ink is black 15 or one dark accent colour (6 blue is good) on the grey 12 ground:

  | Button | Caption zone (x0, y0)-(x1, y1) | The description says (your own words, **at most 2 lines, each within the zone's width**) |
  |---|---|---|
  | Tutorial | (74,27)-(170,88) | learn to play with a guided first game |
  | Quick Game | (244,27)-(320,88) | one black colony against one red colony (this zone is only 76 px wide: short words) |
  | Full Game | (170,96)-(320,157) | all the colonies of the yard and the house, play to win |
  | Experimental | (75,165)-(172,226) | a free-play sandbox, no rules |
  | Load Game | (244,165)-(320,226) | continue a game saved earlier (76 px wide again) |

  The zones are the only room there is. The title line (the label) may be centred vertically in its zone with the description under it.
- **Cancel**: a **plain button** in its rectangle (100,232)-(166,249): 1-px black 15 outline, light grey 12 or white 0 face, the same bevel, the word `Cancel` centred inside in black 15 (bold, cap height 7 to 9).
- **Nothing else**: no line, no logo, no version, no name in this picture (`Choose a Game` and the labels only).

## C. The About box (3000, 3001)

| File | Size | Where (screen) | What |
|---|---|---|---|
| `3000.pix` | 320 x 200 | (177,118) | the **background**: heading, a recessed well, a footer line |
| `3001.pix` | 254 x 109 | (210,179) = R's top-left | the **name card** shown inside the well for the first 5 seconds |

Both opaque. **The role:** the About box shows who made the game. The credits themselves (a list of lines, black 15 on light grey 12) are written by the game over R (text category, not here); this batch makes the frame around them and the card before them.

**3000** (flat **light grey 12** everywhere except the elements below; its outermost ring is 12):
- **The heading `About OpenSimAnt`**: centred horizontally, in **rows 3..38**, bold, 16 to 26 px tall, a main colour plus a darker shade or outline (your own style: **not** a red-and-black two-tone,
  3-D-shadowed capital style); contrast >= 3 : 1 against 12. Below it, a **separator line** (1 or 2 px, colours 13 / 0, or one of your own) across the full width at row 44 to 50, optional.
- **The well (a recessed rectangle)**: the **item rectangle R = (33,61)-(287,171)**, and the picture inside R is **flat 12** (it is always covered, see 4 above). Just outside R draw the sunken bevel:
  **a 2-px white 0 line on R's top and left sides** (rows 59..60 above R from x = 31 to 288; columns 31..32 left of R from y = 59 to 172) and **a 2-px dark line on its bottom and right sides**
  (colour 13 then 14, rows 171..172 below R from x = 31 to 289, columns 287..288 right of R from y = 59 to 172: the line in 14 outermost); no other colours
  within 2 px of R. The corners may be mitred. **Nothing else within 8 px of R except flat 12.**
- **The footer line `A fan project. Not an official game.`**: centred horizontally, in rows **178..197**, 8 to 12 px tall, black 15, regular.
- Nothing else (no logo, no year, no name but "OpenSimAnt" in the heading).

**3001** (the name card; its **outermost ring is flat light grey 12**, and everything around the lettering and emblem is flat 12, so the card joins the well's grey and shows no edge):
- Three lines, **exactly**: `OpenSimAnt` (large: 16 to 24 px tall, the same colours and style as the title's wordmark if you like), `an open-source remake` (8 to 12 px tall), `a fan project` (8 to 12 px tall); centred as a block.
  Leave **6 px free of ink on every side**.
- An **emblem** (a small ant, a tunnel mark, a logo-like badge of your own, 40 to 70 px high, **no more than 40 % of the area**) beside or above the text, **not** a red / black triangle and not a person.
- Contrast >= 3 : 1 for all lettering against 12. Its bottom row (row 108) is flat 12 (R is 110 rows high and the card 109: R's last row, below the card, shows 3000's flat 12, so the card's own edge must be 12 too).

## D. The player's-ant pictures (9100, 9101, 9110, 9111)

All opaque. The four stills of the player's own ant, shown in the scene window (screen (153,85)) when Events is on. Ground: soil (browns 10 / 11 with grey pebbles 12 / 13 / 14). The **player's ant is yellow**
(see "Colour roles"); you may show it larger than life (it is a close-up).

| File | Size | When it is shown | What it shows |
|---|---|---|---|
| `9100.pix` | 200 x 161 | after the player's ant is killed by the spider or the ant lion (shown for about 16 s, or until a key / click); the game writes a caption over its top rows | **the player's yellow ant after the attack, lying still** on the ground (on its back or its side, legs curled in, one antenna bent): it is hurt, not gory. Ground: soil, a few pebbles. **Rows 0..14 are covered by the caption strip: plain ground there.** |
| `9101.pix` | 200 x 161 | when the player takes over another ant: as a newly **hatched queen / reborn ant**, or as **a worker** (same picture for both, about 16 s; caption over its top rows) | **a new ant just out of its cocoon**: a pale, freshly hatched ant standing next to its torn cocoon on the ground, looking up. Pale colours (0 white, 12, 11 tan) for the cocoon, the ant yellow-pale. **Rows 0..14 plain ground.** |
| `9110.pix` | 200 x 161 | when a nestmate **feeds** the player's ant (the first of two frames; about 2.5 s, then 9111 is laid over it for another 2.5 s) | **two ants head to head**: the big **black nestmate** (dark grey 14, 15 outline) above, the **small yellow player's ant** below, the nestmate **offering a drop of food** (a **green 8 / 9 drop** with a white 0 highlight) at the tip of its mouth, between the two heads |
| `9111.pix` | 80 x 89 | the **patch** laid over 9110 at (72,62) (so covering 9110's rectangle (72,62)-(152,151)) | **the same moment a beat later**: the drop has passed to the yellow ant (the drop now at the yellow ant's mouth, partly in it, the nestmate's mouth empty and open a little). **The patch covers the two heads' mouths and the drop**; the rest of 9110 shows unchanged around it |

**Alignment of the patch 9111 with 9110**: the patch's outermost ring (all four sides) **equals the 9110 pixels at its own place** (so the patch is invisible at its edge): make both from one program, render the "before" and the "after" states of the two-ant scene, set `9110` = the "before" render and `9111` = the crop
(72,62)-(152,151) of the "after" render. The script asserts the ring equality, and that **at least 10 % of the patch's pixels differ from the same crop of 9110** (it animates). The green drop (colours 8 / 9) is present in both.

For 9100 and 9101: the rest of the picture (rows 15..160) is the scene; you may put the main subject centred slightly low. **Steer away** from the original's composition: do **not** make a top-down view with the ant diagonal across the picture;
choose a low, three-quarter **side** view of the ground for 9100 and a view from the front and slightly above for 9101.

## E. The event icons (9150..9156)

All **32 x 32**, opaque. The icon of a message box that says how the player's ant died (see 6 above). Each is **a symbol on a coloured square**: a **1-px black 15 ring all round the edge**, then a ground colour (a different one per icon,
no two icons with the same ground), and a bold symbol, **at least 4 colours**, no lettering. The symbols are comic and **not bloody**. The ant, where one appears, is the **yellow player's ant** or a plain dark ant.

| File | Cause (when shown) | Symbol |
|---|---|---|
| `9155.pix` | **stepped on by the human** | a big shoe sole coming down on a small ant (sole seen from below, tread marks, the ant's legs sticking out); ground: grass (8) |
| `9152.pix` | **run over by the lawn mower** | a lawn mower seen from above (deck, wheels, handle) over grass; ground: grass (8 / 9) |
| `9153.pix` | not found in use (a variant of the mower) | the same mower as 9152 with a **few grass clippings and small flecks flying** from it; **the same drawing as 9152 outside the flecks** (script: at least 60 % of the pixels equal) |
| `9150.pix` | **drowned** | an ant on its back in **water**: concentric ripples round it (ground: blues 6 / 7 with white 0 ripple lines) |
| `9154.pix` | **starved** | an **empty fuel-gauge or an empty bowl**: a round gauge whose needle is at the empty end (a red 3 mark), a small empty plate with a fork, or an hourglass; your choice, readable as "ran out". Ground: a light colour |
| `9151.pix` | **poisoned by insecticide** | a **skull and crossed bones** or a **spray can with a toxic cloud** (a cloud and a small ant on its back); ground: red 3 or magenta 4 |
| `9156.pix` | **electrocuted** | a **lightning bolt** (yellow 1 / orange 2) striking a small ant, on a dark ground (5 purple, 14 dark grey) |

**Steer away**: do **not** reproduce a mower seen from above with a cross-shaped blade, a skull with long crossed bones on red, or a red X over an ant; draw **your own**, with the mower's wheels seen at the sides and a round shield,
the skull small and cartoon-like **or** a spray can instead, and a bolt instead of a cross.

## F. The ant lion scene (9200..9203)

All opaque. Shown when the player's ant is taken by an **ant lion** (a larva that waits at the bottom of a funnel-shaped pit in the sand and catches ants that fall in). With sound; about 5.5 seconds, or until a key / click.
The scene is a cross-section view: **dry ground above, the pit below**.

| File | Size | Drawn | What |
|---|---|---|---|
| `9200.pix` | 200 x 160 | the base picture (scene window, screen (153,85)) | the **pit**: a funnel of sand seen from the side at the bottom of the frame (darker sand layers 10 / 11 / 13 / 14, grains and pebbles), the **ant lion at rest** at its bottom (a big round head with two long curved jaws, eyes, a ridged body, **colour 3 red for the eyes**), and the **player's yellow ant** walking on the edge above it. Ground above in tan / brown; a few pebbles. Sky is not shown. |
| `9201.pix` | 136 x 121 | the **patch** at (38,39), after 0.5 s (laid over 9200) | the ant lion **rears up**, jaws spread wide, at the pit's mouth; the yellow ant at the edge about to be grabbed. The patch runs from y = 39 to the picture's bottom edge (y = 160). |
| `9202.pix` | 136 x 108 | the **patch** at (38,52) | the jaws **clamped** on the ant, the head tilted **left**, the ant mostly hidden (a leg or antenna sticks out). The patch runs from y = 52 to y = 160. |
| `9203.pix` | 136 x 108 | the **patch** at (38,52) | the same, the head tilted **right** (a different position of the head and jaws) |

**Timing** (so the pictures flow): at 0 s the base 9200 only; every **0.55 s** the overlay changes: **9201, then 9202, 9203, 9202, 9203, 9202 ...** (9201 once, then the two alternate) until the scene ends.
The ant lion's roar plays on every other change.

**Alignment of the patches**: each patch's outermost ring (left, top, right and, for the bottom edge, the picture's last row) **equals the 9200 pixels at its own place**; the patch pictures replace
their rectangle completely, the area outside them stays as 9200. Make the scene from **one program** (`render(state)` with the states "rest", "rear", "left", "right"), set `9200` = "rest" in full and each patch = the crop of its state's render.
The script asserts the ring equality of all three patches, that **each pair of patches differs in at least 5 % of the pixels** of their common area, and that the player's yellow ant (colour 1 pixels) is present in 9200 and 9201 but **at most a few pixels (< 30)** in 9202 / 9203.

**Steer away**: no spider in the picture's corner, no red eyes with a white pupil ring **exactly** like a cartoon snake; give the ant lion your own head shape (a wedge or a round head, a flat head with horns), and view the pit from a lower angle than "straight on".

## G. The spider scene (12000..12003)

All opaque. Shown when the player's ant is taken by the **spider** (its own sound, shown for up to 8 seconds, then the death message box over it). A **close-up portrait of the spider, facing the viewer**, the player's ant not shown (it is "in the jaws").

| File | Size | Drawn | What |
|---|---|---|---|
| `12000.pix` | 189 x 171 | the base picture (screen (153,85)) | the **spider's face and front legs, centred**, on a sky background: head with **eyes**, the first legs raised at both sides, **jaws (fangs) open in the lower middle**; the pose = the "jaws open" state |
| `12001.pix` | 98 x 80 | the **patch** at (46,77): the jaws **fully open** | the lower face and the two fangs, wide apart, over the sky |
| `12002.pix` | 98 x 80 | the patch | the fangs **half closed**, bent in |
| `12003.pix` | 98 x 80 | the patch | the fangs **closed together** (touching or crossing at the tips) |

**Timing**: at 0 s the base 12000; every **0.15 s** the next patch of the cycle **12002, 12003, 12002, 12001, 12002, 12003 ...** (the jaws close, open, close ...); the scene's sound repeats
each cycle. After the scene the game draws the death message box over it.

**Alignment of the patches**: the patch rectangle is **(46,77)-(144,157) of 12000** (the lower middle of the face: x 46..144 of 189 wide is horizontally centred; y 77..157 of 171 high is the lower half down to the bottom
of the jaws). Each patch's **outermost ring equals the 12000 pixels at its place**, so make one `render(state)` ("open", "half", "closed"), set `12000` = "open" in full and each patch = the crop of its state's render. The three patches differ pairwise in at least 5 % of their pixels.
The sky around the face is a **flat colour** (or two flat bands) so the patches' edges are invisible there: do not put a gradient or a cloud in the patch rectangle's outer 3 px.

**Steer away**: do **not** make the original's pose, **a furry brown jumping spider seen straight on with two huge round eyes in the middle of its face and a flat cyan sky**. Make a **glossy, dark spider (black 15, greys 13 / 14, a little brown 10)
with eight small eyes in two rows**, a big hairless abdomen peeking above the head, long thin legs raised at the sides with joints bent, and curved **orange-tipped fangs** (2 orange); the sky a **dusk colour** (5 purple or 6 blue,
flat) or a **leaf-green** (8 / 9). It must still read as **the game's spider** (browns / greys, eight legs): it is the same animal as the yard's spider, drawn in a close-up.

## The script's checks

`make_screens_bitmaps.py` must **assert** (fail the build of the files) that:

1. every file has its **exact size**, only valid characters and **no `.`**; the 24 ids are exactly those of the Scope table;
2. **identity**: no string of the script that is lettered into a picture contains `SimAnt` other than as part of `OpenSimAnt`, or `Maxis`, or a four-digit year; the lettered strings are the ones of "Identity and wording" (script: a list `LETTERED` of every string drawn, asserted
   against the allowed list for each picture);
3. **the title**: the 512 x 372 canvas' outermost ring is colour 15; `2000` = its rows 0..171 and `2001` = its rows 172..371; colour 15 is at most 40 % of the canvas; the wordmark is at least 22 px tall (script: the height of the ink of the lettering);
4. **Select a Game**: the outermost ring and every pixel outside the six hit rectangles, the heading, and the caption zones is colour 12; each of the five button rectangles has its outermost ring in colours 15 (outline) and 0 / 13 / 14 (bevel) **only**, at least 6 colours inside, no colour above 70 %;
   the Cancel rectangle's ring is colour 15 and contains label ink; all lettering contrasts >= 3 : 1; no caption ink outside the zones;
5. **the About box**: `3000`: the outermost ring and R = (33,61)-(287,171) are colour 12 throughout; the bevel pixels as in C (white 0 above / left, 13 and 14 below / right) along at least 95 % of each side; **no pixel except 12 within 8 px of R besides the bevel**; heading and footer present
   (ink in rows 3..38 and 178..197); `3001`: the outermost ring is 12, **row 108 is 12**, at least 6 px of margin free of ink on every side, ink coverage by the emblem at most 40 %, three lines of lettering;
6. **group E**: each icon has a 1-px colour-15 ring, at least 4 colours, **pairwise different ground** (the most frequent non-15 colour differs), **9153 and 9152 agree in at least 60 % of their pixels**, no two icons identical;
7. **9100 / 9101**: no colour-1 pixel and no colour-15 pixel in rows 0..14; **9110 / 9111**: the ring equality, the 10 % difference, the presence of the colours 8 / 9 in both; the yellow colour 1 is present in 9100, 9101 and 9110;
8. **the patches of 9200 and 12000** (F, G): the ring equality of every patch with its base, the pairwise differences (>= 5 %), and for F the presence rule of the yellow ant; the **patch sizes and positions are constants** (`PATCHES = {9201: (38,39), ...}`) asserted against this spec;
9. no picture is **an exact copy of another** (all 24 distinct), and none is a single flat colour.

`python tools/clean_pack/build.py` then packs the files (`HCEGANT/2/<id>.bin`); the spec side runs the game with `-- --clean --pack=remake/build/dev_pack.zip`
(`--title`, `--select`, the About box in the Help menu, `--scene=1..5` for the scenes) and compares the look with the originals for similarity before the pack ships.

## Previews

`preview.png` (each assembled as the game shows it, at 2 x on a mid-grey background): (1) **the title**: the 640 x 480 black screen with the two halves at (64,63) and (64,235) (the seam must not show);
(2) **Select a Game**: 2500 inside its 3-D frame (a 1-px black line round it is enough), **with the six hit rectangles outlined in a thin colour on a second copy** to prove the buttons sit in them; (3) **the About box**: the well showing the card 3001, and a second copy showing
the well filled with grey 12 and three lines of sample credit text (black, 14-px pitch) so the bevel and the footer can be judged; (4) **a message box** (a 3-D frame, three lines of sample text, an icon at the top) for each of the seven icons in turn, in one row;
(5) **each scene in the scene window**: the base picture with its 2-px black frame at (153,85) and each patch laid on it in its cycle order (9200 + 9201 / 9202 / 9203; 12000 + 12002 / 12003 / 12002 / 12001; 9110 + 9111), and the captions strips of 9100 / 9101 drawn as the game does (dark grey 14 over the top 15 rows with 24 characters of yellow sample text).

## Consistency with the other batches

- **`ui_bitmaps.md`**: the message box face (grey 12, black text) and the 3-D frame are the game's; the **yellow player's ant** of these scenes is the same ant as 17000 (the tutorial's "you are the yellow ant"); the Select card's **Quick Game**
  black and red ants and the scenes' dark nestmate use the **colony colours** of `ant_sprites.md` (black colony: dark grey 14 / shade 13; red colony: red 3 / shade 2).
- **`yard_bitmaps.md`**: the **spider of group G is the yard's spider** (browns / greys 10..15, eight legs, curved fangs); the **sneaker** of 9155 is a shoe like the person's and the **mower** of 9152 / 9153 is the same
  kind of machine as the yard's mower (a deck and wheels): use the **same colour scheme** (a red or orange deck, dark engine) if the yard batch is done (its `8800.pix`, if it exists when you start, shows the mower's colours; you may look at it for colours only).
- **The ant lion's pit**: the pit tiles of the map (`map_tiles.md`) are a sandy funnel in tan / brown; keep the scene's sand in the same colours (11 tan, 10 brown, shading 13 / 14).
- **The title and the About name card** share the **wordmark's style** (the same lettering, colours and emblem if you give it one).

## Not found / open

- **9153** (the mower with flecks) is not referenced by any code I could trace: the six other icons are the causes of death 5..10 (foot, mower, drowning, hunger, insecticide, electric current) and 9153 may be an alternate mower picture; it is in the spec so every id exists.
- **The icons in the remake.** The original passes the icon's id as the message box's picture argument (events 5..10: 9155, 9152, 9150, 9154, 9151, 9156); the remake's `PlayerActions.PlayerEvent` does not (it passes none), so the icons are never shown yet: an engine change on the spec side.
- **The caption width of 9100 / 9101.** The game's font for captions is 9 px per character; the longest of the three caption lines the game writes is 24 characters = 216 px, wider than the picture (200 px): the remake clips it. The **new caption texts must be at most 22 characters**
  (the text spec's rule), and the rows 0..14 strip is the same size either way.
- **The caption strip's exact rows** (rows 0..14 of the picture; the strip is 15 rows from picture row -1 to 13 in the remake's drawing; the original's row is not measured to the pixel): keep rows 0..14 plain.
- **The well's edge in 3000.** The item rectangle R and the original's bevel differ by about 1 px at the right and bottom; the spec gives the bevel adjacent to R (rows / columns 59..60 and 31..32 for the light edge, 171..172 and 287..288 for the shadow).
- **The title screen's frame.** The original has a coloured border line on its outer ring; the spec makes it black. The game's window rectangle is one pixel larger than the pictures (513 x 372 by the layout; the pictures are 512 wide): the extra column is never drawn by the game from the bitmap.
- **The time unit.** The scene timings are in the game's clock (18.2 ticks a second; the code counts three units per tick): 30 units = 0.55 s, 8 units = 0.15 s, 0x2D ticks = 2.5 s.
- **320-px mode** (the original's low-resolution mode moves some windows): not modelled; the remake always runs 640 x 480.
- **The Help / About text** (the credits that roll over R) and **the captions** are strings (text category). The credits' wording is not in this spec: only the room (R: 254 x 110, black 15 on light grey 12, 14-px line pitch, centred).
