# Spec: the encyclopedia's pictures (40 one-bit bitmaps: anatomy, castes, species, behaviour, life cycles, menus, small buttons)

> **Status (2026-10-31):** complete, ready for a maker (5 passes, see "How to work"). Written from the card data
> (`docs/clean_pack/data/cards.json`: which card shows which picture, where, and which rectangles of it are links),
> the remake's encyclopedia code (`Antipedia.cs`, `Main.cs` `DrawTextViewer`) and the measured bitmaps
> (`data/bitmaps.json`, archive `SHARED`, type 2). Covers **40 bitmaps**. The encoder and its checks are in
> `tools/clean_pack/build.py` (`cat_bitmaps`: the file name `SHARED_<id>.pix` is accepted as it is; `--roundtrip`
> already checks these 40 originals). Subjects are named from each card's topic; nothing was taken from how the original
> pictures are composed except where a link rectangle fixes a position and, for the 7 never-shown ones (no card explains
> them), a one-line guess at what they were. What could not be traced is said where it comes
> up ("not found") and in the closing section.

Output folder: `remake/game/assets/clean/src/bitmaps/` (shared with `ui_bitmaps.md` and `yard_bitmaps.md`; **only create
files for the 40 ids of this spec**). Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an entry). **One file per
bitmap, named `SHARED_<id>.pix`** (for example `SHARED_200.pix`), plus `make_encyclopedia_bitmaps.py` (the script that
writes every `.pix`, so they can be regenerated; split it into modules if you like), `README_encyclopedia.md` (the design:
the line weights, the tone patterns, the label face, how to rebuild) and, recommended, `preview_encyclopedia.png` (see
"Previews").

## Contents

- [Scope](#scope) - [How to work](#how-to-work) - [Format and rules for every file](#format-and-rules-for-every-file)
- [What the game does with these pictures](#what-the-game-does-with-these-pictures) - [Look, drawing and lettering](#look-drawing-and-lettering)
- [Where each picture is shown](#where-each-picture-is-shown) (the placement table the script checks against)
- Groups: [A menus of boxed labels](#a-menus-of-boxed-labels-150-400-500-600-700-850), [B buttons, a strip and spare icons](#b-small-buttons-a-text-strip-and-spare-icons-170-160-129-21000-21003),
  [C the ant's body and its parts](#c-the-ants-body-and-its-parts-410-420-440-460-128-200-210-213-220-230), [D other social insects](#d-other-social-insects-300-320-330-340),
  [E ant species](#e-ant-species-610-620-630-640), [F behaviour and the nest](#f-behaviour-and-the-nest-510-520-530-540-550-560), [G life cycles](#g-life-cycles-710-720),
  [H the flowchart](#h-the-colony-flowchart-880)
- [The script's checks](#the-scripts-checks) - [Previews](#previews) - [Consistency between the pictures](#consistency-between-the-pictures) - [Not found / open](#not-found--open)

## Scope

All 40 type-2 bitmaps of the game's shared archive, **1 plane** (black ink on white paper, 0 or f only), all opaque.
They are the pictures of the in-game encyclopedia: a window that shows one **card** at a time (a card is a 320 x 200 page
with a title, a block of text, and pictures), reached from the Map window's Ant Info button.

| Group | Ids | Count | What |
|---|---|---|---|
| A | 150, 400, 500, 600, 700, 850 | 6 | menus: a column of boxed labels, each box a link to another card |
| B | 170, 160, 129, 21000, 21001, 21002, 21003 | 7 | a "next card" button, its spare twin, a spare text strip, four spare 7 x 7 icons |
| C | 410, 420, 440, 460, 128, 200, 210, 213, 220, 230 | 10 | the ant: worker, soldier, winged ant, queen, a spare winged ant, the whole body with labels, head, antennae, thorax and legs, the abdomen's inside |
| D | 300, 320, 330, 340 | 4 | the four kinds of social insect, termite, bee, wasp |
| E | 610, 620, 630, 640 | 4 | weaver, harvester, army and leafcutter ants |
| F | 510, 520, 530, 540, 550, 560 | 6 | nest cross-section, ants communicating, a scent trail, a fight, aphid herding, brood care |
| G | 710, 720 | 2 | the ant's life cycle, the colony's life cycle |
| H | 880 | 1 | the colony flowchart (13 boxes and arrows) |

Of the 40, **7 are never shown by the game** (128, 129, 160, 21000..21003: group B and 128 in group C): they are made
anyway because a complete pack contains every resource of the original (the pack builder lists a missing one); they are
low priority and simple (see their rows). The other 33 are each shown on one to five cards.

**Not in this spec**: the encyclopedia's navigation strips 21004 / 21005 (BACK / PREVIOUS / TOP buttons, in
`ui_bitmaps.md` group K), the card texts, titles and glossary (a later text batch), and 18 picture ids that cards refer to
but that do not exist in the game's files (see "Not found / open": the game draws nothing for them and so does the pack).

## How to work

One script and one set of helpers for all 40 (a small module of your own: a line tool, a polygon fill, tone patterns, a
label face, a boxed label, a leader line, an ant model, the checks). Do it in five passes, each ending with a build of what
exists (`python tools/clean_pack/build.py` refuses a wrong size, a hole, or a colour other than white and black):

1. **Pass 1: the label tools, the menus and the small items:** 150, 400, 500, 600, 700, 850, 170, 160, 129, 21000, 21001,
   21002, 21003 (13 files). Build the label face and the boxed label first; every later picture uses them.
2. **Pass 2: the ant model and the ant's bodies:** 410, 420, 440, 460, 128, 200 (6 files). **One ant model** (a function that
   draws a side-view ant from parameters: head size, thorax, waist, gaster size, wings, leg pose, scale) serves all six, and
   later passes.
3. **Pass 3: the parts of the ant:** 210, 213, 220, 230 (4 files).
4. **Pass 4: other insects and species:** 300, 320, 330, 340, 610, 620, 630, 640 (8 files).
5. **Pass 5: behaviour, nest, life cycles, flowchart:** 510, 520, 530, 540, 550, 560, 710, 720, 880 (9 files).

**Previews: look at your preview image at most 5 times per pass** (render it, then look; do not look after every small
change; use the script's checks, which are text, for everything else). Spend the looks on proportions, the drawing's legibility
at 1x, and label / leader placement.

## Format and rules for every file

- `.pix` as in `docs/clean_pack/README.md`: one line per pixel row, one character per pixel, `#` comment lines, every row the
  same length. **The size of each picture is exact.**
- **1-plane, opaque, only `0` (white, the paper) and `f` (black, the ink)**: no other index and no `.` (the build rejects
  both). Grey is made with **tone patterns** (see "Look").
- All lettering is **English and yours**. A **label** is a short functional word or two naming the thing it points at or
  the card it opens (a natural-history term such as "Head", or a plain synonym); where this spec suggests a word you may
  use it or another plain word of the same meaning that fits the box. No picture may contain a company, publisher, author
  or product name, a logo, a trademark, a signature, a date or a credit line, and the words "SimAnt" and "Maxis".
- **Drawings are your own**, made from general knowledge of real ants and insects (anatomy, proportions, behaviour), as a
  natural-history illustrator would draw them: do not trace, copy or imitate any existing picture, cartoon or game.
- Coordinates in the tables are pixels from the picture's own top-left corner, `(x0, y0)-(x1, y1)` with **x1 and y1
  exclusive** (a box `(37, 3)-(67, 14)` is 30 x 11). Card coordinates (in "Where each picture is shown") are from the card's
  top-left corner (the card is 320 x 200).

## What the game does with these pictures

Read this before drawing; the constraints come from it.

1. **A card** is a white 320 x 200 page. The game draws its title elsewhere (the window's caption), then, in the order of
   the card's data, its pictures (**opaque, top-left corner at the position in the placement table**, so a picture's
   white pixels erase what is under them), then each text block into its text rectangle. The last 20 rows of the card
   (y 180..199) carry the navigation strip (another bitmap, drawn on top). No picture reaches the strip.
2. **Clipping.** A card is clipped to its own 320 x 200 rectangle. Where a picture is placed partly outside it, the outer
   rows or columns are cut off (said per picture: for example 213's top 2 rows). **Whatever lies in a hidden row or
   column must be unimportant: keep it white** (or plain ground line) so the cut shows nothing.
3. **Text beside the picture.** Each card's text is laid out by the game in a **text rectangle** that, in every case but
   two noted rows, does not touch the picture's area. It flows in lines (about 10 px high) from 4 px below the
   rectangle's top. Do not draw text-like lines in the picture's free margin.
4. **Links.** Rectangles of the picture are links, fixed in the card data and **not drawn by the game** (nothing is
   highlighted or inverted): a click on a **menu / label box** jumps to another card (**card link**) or shows a short
   definition in a white pop-up for as long as the button is held (**pop-up link**). The visible box must coincide with the
   rectangle: so the pictures contain their own **boxed labels** (a word in a box), and those are the only clickable
   things. A boxed label is therefore the picture's one way of saying "click here": **draw a box only where a link
   rectangle is listed**, and nowhere else (a caption that is not a link is plain unboxed text, see "Look").
5. **No colour, no mask.** 1-plane bitmaps are drawn black on white with no mask; there is nothing to recolour or
   invert, and no overlay is drawn by the game on a picture.

## Look, drawing and lettering

- **Style: scientific illustration**, as in a field guide printed in black ink: clean 1-px contour lines, the interior
  shaded with hatching or stipple, a few small details (hairs, veins, joints) where they help recognition. At 1x each
  picture is a small drawing: favour a clear silhouette and correct anatomy over fine detail.
- **Line weights**: contour 1 px; a second, heavier contour (2 px) only for the ground line or for the subject's main
  outline if you like; thin interior lines 1 px. No isolated single black pixels except as stipple.
- **Tone**: three tones are enough and are made with patterns: **dark** = solid black or a 3 : 1 black mesh, **mid** =
  a 50 % checkerboard, **light** = about 25 % (one black pixel in a regular 2 x 2 or an ordered 4 x 4 dither pattern);
  white = the paper. Hatching lines (diagonal 1-px lines 2..3 px apart) are an alternative mid tone. Keep the
  pattern **registered to the picture** (not to the subject), so neighbouring areas of one tone match.
- **Light** from the top-left (shade the lower-right side of rounded forms).
- **Orientation**: single insects in side view **face left** (head at the left), unless a row says otherwise.
- **Anatomy to keep right** (the cards teach it): an ant has **three body regions** (head, thorax, abdomen) and **six
  legs, all attached to the thorax**; the abdomen is joined by a narrow **waist (petiole)**, with one or two small
  nodes, and its main part is the **gaster**; **antennae are elbowed** (a long first segment, then a bend, then a
  chain of short segments); big compound eyes at the sides of the head, strong **mandibles** at the front; workers and
  soldiers are **wingless**; males and young queens have **two pairs of wings** (the front pair larger); a mated queen
  has shed her wings and carries a much enlarged gaster. A termite has no waist and straight, beaded antennae; a bee and a
  wasp have a waist too but are hairy / smooth respectively and have a **stinger**.
- **Label face**: draw your own pixel face, bold, upright, capitals and lowercase, **capital height 7 px** for a box 11 or 12
  high, 8 px for a box 13 to 15 high (average advance about 5 px; keep it narrow, `i` and `l` 3 px). A **two-line label**
  (a box 21 px high or more) uses a regular face of capital height 6 px, line pitch 8 px. The word must fit its box with 2 px
  of white on each side; the script measures and asserts it. Plain captions that are not links use the same face with no
  box.
- **Boxed label**: exactly on its rectangle, a **1-px black outline** (the rectangle's outermost pixels), white inside, the
  word **centred** in black. Where a rectangle is cut by the picture's edge (said in the table), the outline stays
  inside the picture and the box is as large as the picture allows.
- **Leader line**: where a label names a part of a drawing, a **1-px black line**, straight or with one bend, from the
  nearest side of the box to the part, ending in a small dot (2 x 2) or a 3-px arrowhead **on the part**. Leaders never
  cross a box (their own or another's) and cross each other as little as possible.

## Where each picture is shown

The placement table is from the card data: the **cards that show the picture**, the picture's top-left corner on the
card, and the card's **text rectangle(s)** `(x0, y0)-(x1, y1)` (the text that flows beside / below the picture). Cards are
named by topic in my words. A picture shown on several cards must work on **all** of them (a picture reused on a card
about something else is generic).

| Id | Size | Cards (topic) at card (x, y) | Text rectangle | Clip / notes |
|---|---|---|---|---|
| 150 | 102 x 116 | 128 (the top card: the encyclopedia's front page) at (4, 29) | (176,1)-(320,180) right | a column of 8 topic boxes |
| 400 | 76 x 90 | 139 (the castes) at (27, 21) | (144,4)-(310,176) right | 6 caste boxes; card 139 also shows 410 at (19, 124) |
| 500 | 109 x 120 | 146 (behaviour) at (6, 28) | (130,12)-(309,161) right | 8 topic boxes |
| 600 | 93 x 90 | 152 (common species) at (17, 62) | (138,13)-(304,162) right | 6 species boxes; card 152 also shows 410 at (1, 15) |
| 700 | 101 x 30 | 157 (life cycle) at (35, 9) | (0,52)-(320,175) below | 2 boxes; card 157 also shows 410 at (170, -2) |
| 850 | 128 x 113 | 171 (strategy for playing) at (4, 32) | (147,17)-(310,157) right | 7 boxes; the last box's rectangle runs 2 px past the picture's bottom |
| 170 | 39 x 15 | 137 (bees) at (276, 57); 167 (ant facts, page 1) at (137, 151); 168 (ant facts, page 2) at (138, 152) | (2,76)-(317,177) / (11,14)-(310,129) / (5,4)-(313,130) | the "next card" button, lower right of the text |
| 410 | 92 x 48 | 135 (ants, introduction) at (110, -1); 139 (castes) at (19, 124); 140 (the worker caste) at (112, 7); 152 (common species) at (1, 15); 157 (life cycle) at (170, -2) | (4,51)-(316,176); (144,4)-(310,176); (17,68)-(306,168); (138,13)-(304,162); (0,52)-(320,175) | **rows 0 (card 135) and 0..1 (card 157) are cut: keep rows 0 and 1 white** |
| 420 | 141 x 54 | 141 (the soldier caste) at (89, 0); 165 (carpenter ants) at (81, 11); 166 (fire ants) at (88, 11) | (1,57)-(322,181); (7,81)-(312,149); (17,78)-(303,168) | text is below the picture on all three |
| 440 | 128 x 51 | 143 (the male) at (89, 12); 144 (the new queen) at (85, -4) | (29,86)-(288,154); (0,43)-(322,179) | **rows 0..3 are cut on card 144: keep rows 0..3 white** |
| 460 | 155 x 56 | 145 (the queen) at (71, -2) | (-1,55)-(319,180) | **rows 0..1 are cut: keep them white** |
| 200 | 184 x 89 | 130 (body overview) at (66, 90) | (0,0)-(319,87) above | 3 boxes |
| 210 | 153 x 137 | 131 (the head) at (3, 18) | (167,7)-(312,171) right | 5 boxes |
| 213 | 235 x 45 | 159 (antennae) at (85, -2) | (13,51)-(307,176) below | **rows 0..1 are cut: keep them white** |
| 220 | 258 x 93 | 132 (the thorax and legs) at (34, 85) | (0,0)-(319,80) above | no links |
| 230 | 252 x 103 | 133 (the abdomen) at (37, 77) | (0,0)-(318,78) above | 3 boxes; **keep row 0 white** (the text rectangle ends 1 row into it) |
| 300 | 137 x 165 | 134 (social insects) at (0, 5) | (141,3)-(317,176) right | 4 boxes |
| 320 | 69 x 22 | 136 (termites) at (118, 4) | (1,30)-(319,177) below | |
| 330 | 108 x 70 | 137 (bees) at (100, 1); 179 (bees, page 2: foraging) at (100, 1) | (2,76)-(317,177); (2,81)-(318,174) | text below on both |
| 340 | 94 x 66 | 138 (wasps) at (204, 43) | (11,15)-(190,165) left | the text is at the left of it |
| 610 | 141 x 117 | 153 (weaver ants) at (-7, 39) | (136,3)-(316,176) right | **columns 0..6 are cut: keep white**; 1 box |
| 620 | 139 x 64 | 154 (harvester ants) at (82, 3); 170 (foraging) at (66, 3) | (13,78)-(307,167); (8,73)-(311,174) | text below |
| 630 | 112 x 65 | 155 (army ants) at (98, 6) | (4,75)-(315,176) below | |
| 640 | 122 x 110 | 156 (leafcutter ants) at (5, 35) | (135,9)-(308,171) right | |
| 510 | 222 x 101 | 147 (nest building) at (53, 79) | (0,0)-(319,77) above | 5 boxes |
| 520 | 167 x 149 | 148 (communication) at (-34, 13) | (139,3)-(312,176) right | **columns 0..33 are cut: keep white**; 1 box |
| 530 | 218 x 69 | 149 (scent trails) at (45, 110) | (6,3)-(315,102) above | 1 box |
| 540 | 111 x 105 | 150 (fighting) at (1, 26); 175 (warfare tactics) at (-16, 31) | (114,3)-(316,176); (96,4)-(318,178) | **on card 175 columns 0..15 are cut**: put only ground line / leg tips there |
| 550 | 194 x 103 | 151 (aphid herding) at (51, 75) | (0,0)-(317,75) above | 2 boxes |
| 560 | 135 x 87 | 164 (brood care) at (58, 2) | (94,3)-(319,175) below | |
| 710 | 299 x 68 | 161 (the ant's life cycle) at (12, 93) | (-1,0)-(319,91) above | 5 boxes |
| 720 | 302 x 53 | 162 (the colony's life cycle) at (9, 126) | (2,1)-(318,125) above | no links |
| 880 | 290 x 141 | 177 (the colony flowchart) at (10, 16) | none | 13 boxes; two boxes' rectangles run 1 px past the picture |
| 128, 129, 160, 21000..21003 | see group B / C | **never shown** | | |

(The rectangle of a picture in the card data is 1 to 2 px larger than the bitmap in many cases; only its top-left matters.
Where a picture is placed so a link rectangle falls partly outside the bitmap, the table says so.)

# Groups

## A. Menus of boxed labels (150, 400, 500, 600, 700, 850)

Six pictures that are **nothing but boxed labels in a column** (a menu): each box is a link to a card. **Draw only the
boxes** (and, if you like, a thin 1-px connecting vertical line behind them, at most): no other drawing. The box widths
differ (each is as wide as its word plus padding, centred in the picture): draw them exactly as the rectangles say. Label
face as above. The suggested words are plain topic names of the target cards (**use them or a plain synonym that fits**;
`fits` = the longest word that fits at 5 px per letter).

**150 (102 x 116), the front page's 8 topics** (the box says what the target card is about):

| Box | Size | Opens a card about | Suggested word |
|---|---|---|---|
| (10,3)-(94,14) | 84 x 11 | the four groups of social insects | Social insects |
| (14,17)-(91,28) | 77 x 11 | the ant's body | Ant anatomy |
| (22,31)-(81,42) | 59 x 11 | the life cycle | Life cycle |
| (28,45)-(75,56) | 47 x 11 | the castes | Castes |
| (7,59)-(97,70) | 90 x 11 | ant behaviour | Behavior |
| (5,73)-(99,83) | 94 x **10** | the common species | Common species |
| (22,87)-(82,98) | 60 x 11 | a few ant facts | Ant facts |
| (3,104)-(101,115) | 98 x 11 | tips for playing the game | Game strategy |

**400 (76 x 90), the six castes:**

| Box | Size | Opens a card about | Suggested word |
|---|---|---|---|
| (12,3)-(65,14) | 53 x 11 | the worker | Worker |
| (11,18)-(66,29) | 55 x 11 | the soldier | Soldier |
| (11,33)-(65,44) | 54 x 11 | the replete (the living food-store ant) | Replete |
| (16,48)-(59,59) | 43 x 11 | the male | Male |
| (3,63)-(75,74) | 72 x 11 | the new queen | New queen |
| (13,78)-(61,89) | 48 x 11 | the queen | Queen |

**500 (109 x 120), behaviour topics:**

| Box | Size | Opens a card about | Suggested word |
|---|---|---|---|
| (11,3)-(100,14) | 89 x 11 | how ants communicate | Communication |
| (27,18)-(80,29) | 53 x 11 | foraging | Foraging |
| (16,33)-(93,44) | 77 x 11 | scent trails | Scent trails |
| (16,48)-(92,59) | 76 x 11 | trophallaxis (sharing food mouth to mouth) | Food sharing |
| (3,63)-(108,74) | 105 x 11 | building the nest | Nest building |
| (19,78)-(88,89) | 69 x 11 | brood care | Brood care |
| (25,93)-(80,104) | 55 x 11 | fighting | Fighting |
| (11,108)-(95,119) | 84 x 11 | keeping aphids | Herding aphids |

**600 (93 x 90), six common ant groups:**

| Box | Size | Opens a card about | Suggested word |
|---|---|---|---|
| (3,3)-(92,14) | 89 x 11 | carpenter ants | Carpenter ants |
| (3,18)-(92,29) | 89 x 11 | harvester ants | Harvester ants |
| (3,33)-(92,44) | 89 x 11 | leafcutter ants | Leafcutter ants |
| (9,48)-(85,59) | 76 x 11 | weaver ants | Weaver ants |
| (15,63)-(78,74) | 63 x 11 | army ants | Army ants |
| (18,78)-(74,89) | 56 x 11 | fire ants | Fire ants |

**700 (101 x 30), the two life cycles:**

| Box | Size | Opens a card about | Suggested word |
|---|---|---|---|
| (12,3)-(92,14) | 80 x 11 | the individual ant's life cycle | Ant life cycle |
| (3,18)-(100,29) | 97 x 11 | the whole colony's life cycle | Colony life cycle |

**850 (128 x 113), tips for playing:** (the last box is cut by the picture's bottom edge: draw it from y 102 to the last row,
y 112 inclusive, 11 px high)

| Box | Size | Opens a card about | Suggested word |
|---|---|---|---|
| (15,2)-(115,15) | 100 x 13 | the overall goals of the three game modes | Overall goals |
| (19,25)-(110,39) | 91 x 14 | gathering food | Gathering food |
| (33,41)-(92,54) | 59 x 13 | fighting the rival colony | Warfare |
| (8,56)-(121,69) | 113 x 13 | the full game's strategy | Full game |
| (6,71)-(123,84) | 117 x 13 | the experimental game | Experimental game |
| (5,87)-(124,100) | 119 x 13 | the keys and mouse shortcuts | Keyboard shortcuts |
| (2,102)-(126,115) | 124 x 13 (11 visible) | the flowchart of colony dynamics | Colony flowchart |

The free strip between the first and second box (y 16..24 of 850) stays white.

## B. Small buttons, a text strip and spare icons (170, 160, 129, 21000..21003)

| File | Size | What it is | What to draw |
|---|---|---|---|
| `SHARED_170.pix` | 39 x 15 | **The "next card" button**, placed under a block of text on three cards (bees, ant facts 1, ant facts 2) to go to the following card. The link rectangle is `(1, 1)-(38, 14)` (37 x 13). | A button the player recognises as "go on": the box exactly on `(1,1)-(38,14)` with **1 white pixel all round it** (row 0, row 14, column 0, column 38 white), and a short word meaning *next* or *more*, centred. It must look different from a boxed label: draw it **solid black with the word knocked out in white**, or a 2-px outline with a drop shadow inside the rectangle (your choice). Word at most 6 letters, capital height 7. |
| `SHARED_160.pix` | 37 x 15 | A **spare twin of 170** (never shown; presumably a "back" or "top" button of the same family). | The same style as 170 at 37 x 15 (box `(1,1)-(36,14)`, 1 white pixel all round) with a different word meaning *back* or *top*. |
| `SHARED_129.pix` | 73 x 8 | A **spare one-line text strip** (never shown). | Make it **entirely white** (every pixel `0`), or one short line of plain lowercase lettering in the small face (at most 12 characters, for example `see also`); no name, credit or date. |
| `SHARED_21000.pix`, `21001`, `21002`, `21003` | 7 x 7 each | Four **spare small icons** (never shown; the family of tiny pointer / bullet glyphs). | Four distinct, simple 7 x 7 glyphs: an up-pointing arrowhead, a down-pointing arrowhead, a right-pointing arrowhead and a plain bullet (a filled 5 x 5 diamond). Black on white, no frame. |

## C. The ant's body and its parts (410, 420, 440, 460, 128, 200, 210, 213, 220, 230)

One **ant model** (pass 2) draws a worker in side view; the soldier, the winged ant and the queen are variations of it
(soldier: a head about one third of the body's length and strong mandibles; winged: a bigger thorax, two pairs of
veined wings; queen: tiny head, thorax with wing scars, a huge gaster). Legs: three per side, the far side's slightly
shorter or lighter; antennae elbowed. Proportions are those of a real ant: head about 15 % of the length, thorax about 25 %,
waist 5 %, gaster about 35 % (a worker).

| File | Size | Subject (what it must show for the cards to make sense) |
|---|---|---|
| `SHARED_410.pix` | 92 x 48 | **A worker ant, side view, walking, facing left**, in a stride (legs in a tripod pose), antennae raised and elbowed, mandibles closed, one-node waist, rounded gaster. **No labels.** It is the *generic ant* of the encyclopedia (shown on the ants introduction, the castes overview, the worker caste, the species list and the life cycle cards): a plain, typical worker, not a particular species. **Rows 0 and 1 are cut on two cards: keep them white**; the ant starts at row 2. |
| `SHARED_420.pix` | 141 x 54 | **A soldier (major worker), side view, facing left**, large: a **head about 30 % of the body's length**, much bigger than a worker's, with powerful toothed mandibles open, big muscles shown by hatching; thicker thorax; the same walking pose. No labels. It stands for the soldier caste and, on the other two cards, for a big wood-nesting ant and a stinging ant: so keep it a plain "big-headed ant", no species marks. |
| `SHARED_440.pix` | 128 x 51 | **A winged reproductive ant (a male or a young queen), side view, facing left**: slender body, a larger thorax than a worker's, **two pairs of wings** swept back over the body, drawn as outlines with a few veins and a darker leading edge, the front pair clearly longer. No labels. Shown on the male card and on the new-queen card, so keep it neutral (no queen-only or male-only parts). **Rows 0..3 are cut on one card: keep them white** (the wing tips start no higher than row 4). |
| `SHARED_460.pix` | 155 x 56 | **A mated queen, wingless, side view, facing left**: a small head, a small thorax with two **scars where the wings were**, and an **enormously swollen gaster** (about 60 % of the length) with fine segment lines; optionally an egg at the tip of the gaster or lying in front of her. No labels. **Rows 0..1 are cut: keep them white.** |
| `SHARED_128.pix` | 223 x 86 | **Spare (never shown): a winged ant in side view, large**, facing left, in the same drawing as 440 at a bigger scale, centred. No labels, no boxes. Lowest priority. |
| `SHARED_200.pix` | 184 x 89 | **The whole ant, to show the three body regions**: a worker in side view, **facing left**, the head at the left. Three boxed labels in a row along the top (rows 3..14): `Head` (37,3)-(67,14), `Thorax` (74,3)-(118,14), `Abdomen` (130,3)-(183,14). The ant is drawn **below** the labels (rows 20..88, x about 18..180) so that the **head lies under the first box, the thorax under the second and the abdomen under the third**, and each box has a near-vertical **leader line** (1 px) down to its region (the tip on the head, on the thorax, on the gaster). The waist may be marked by a short bracket with no box. |
| `SHARED_210.pix` | 153 x 137 | **The head, large**, a three-quarter front view of a worker's head (about 100 px tall, filling the picture), showing the **two elbowed antennae** springing from sockets, the **two big compound eyes** (finely cross-hatched or dotted to suggest facets), **three small ocelli** (simple eyes) in a triangle on the top of the head, the **mandibles** (toothed, at the front/bottom, slightly open), and the smaller **maxillae** behind them, with the clypeus and the head's hairs as light detail. Five boxed labels with leaders: `Eyes` (6,10)-(40,21), top left, to a compound eye; `Ocelli` (105,1)-(136,14), top right (a plain word that fits 27 px, narrow letters), to the ocelli; `Maxillae` (16,98)-(60,113), left (a 44 x 15 box), to a maxilla; `Antennae` (3,124)-(52,135), bottom left, to an antenna; `Mouth` (80,123)-(129,134), bottom right, to the mandibles. Fit the head so that the leaders' tips land on the named parts and no leader crosses a box. |
| `SHARED_213.pix` | 235 x 45 | **The antennae**: a small piece of head at the left edge with **two elbowed antennae** sweeping to the right in a wide, shallow curve (one slightly behind the other): each has a **long first segment (the scape)**, a **bend**, then the **flagellum (the funiculus)**, a chain of short segments (10 to 12) with fine hairs and small sense pits at their tips. Optional **plain unboxed captions** (small face) for the scape, the elbow and the chain of segments. No boxes, no links. **Rows 0..1 are cut: keep them white.** |
| `SHARED_220.pix` | 258 x 93 | **The thorax and legs**, large: the thorax seen from the side (head end at the left, waist at the right), with **all six legs attached to it** (three pairs: front, middle, hind) spread out and each drawn with its segments (coxa, short trochanter, femur, tibia, a chain of tarsal segments, **a foot with two hooked claws and a small pad**). Add two **detail drawings in plain circles of 1-px outline** (circles, not rectangles): the **foot's two curved claws**, and the **foreleg's cleaning notch** (a curved spur against a notch lined with a comb of short bristles, where an antenna is drawn through to be cleaned). No boxes, no links; plain unboxed captions optional. |
| `SHARED_230.pix` | 252 x 103 | **A lengthwise cut-away of the ant's body from the mouth to the tail, head at the left**: the head and thorax shown mostly as an outline (the foregut tube passing through them), the narrow **waist with its node**, and the **gaster opened** to show the big thin-walled **crop** (a storage sac), behind it the coiled **midgut**, small clusters for the **glands**, and at the rear the **sting** (or a plain tip). At the mouth, a **small pouch below the mouth opening** (the infrabuccal pocket). Three boxed labels with leaders: `Mouth pouch` (1,73)-(54,97), a **two-line** label (53 x 24), to the pouch, bottom left; `Crop` (104,2)-(130,15) (26 x 13), top, to the crop (which therefore lies at the front of the gaster, around x 100..150); `Midgut` (198,3)-(233,17) (35 x 14), top, to the midgut (behind the crop, around x 190..240). **Row 0 white.** |

## D. Other social insects (300, 320, 330, 340)

| File | Size | Subject |
|---|---|---|
| `SHARED_300.pix` | 137 x 165 | **Four small portraits and four boxed labels**: an **ant**, a **termite**, a **bee** and a **wasp** (the four groups of social insects), each about 50 to 80 px wide and 25 to 40 px high, in side view, in a **zig-zag**: the boxes are fixed and each portrait lies **in the free space across from its box**, next to it, never touching it. Boxes: `Ants` (15,17)-(50,28) (35 x 11), `Termites` (79,56)-(136,67) (57 x 11), `Bees` (12,96)-(49,107) (37 x 11), `Wasps` (82,142)-(126,153) (44 x 11). Suggested placement: the ant at the right of its box (x 55..135, y 0..45), the termite at the left of its box (x 0..75, y 45..90), the bee at the right of its box (x 52..135, y 85..135), the wasp at the left of its box (x 0..78, y 128..165). Draw each insect in the style of 320, 330, 340 and the ant model, at a smaller scale. |
| `SHARED_320.pix` | 69 x 22 | **A termite worker, side view, facing left**: a soft, pale body (light stipple), **no waist** (the thorax and abdomen join broadly), a rounded head, **straight, beaded antennae** (no elbow), short legs, no wings. Small and simple. |
| `SHARED_330.pix` | 108 x 70 | **A honeybee in flight, side view, facing left**: a hairy body (short hatching or stipple fringe), a big eye, **two pairs of translucent wings** (outlined, a few veins), the narrow waist, **a pollen basket** (a swollen, stippled bulge on the hind leg), the stinger tip. Shown on the bees card and on its second page (foraging bees, pollen on the hind legs), so the pollen basket must show. |
| `SHARED_340.pix` | 94 x 66 | **A social (paper) wasp, side view, facing left**: a slender, smooth body with a clear black-and-light banded abdomen (alternate hatching and white bands), a long narrow waist, two pairs of narrow wings held back, long legs hanging, a stinger; optionally a few hexagonal cells of a **paper comb** at one corner, if it fits. |

## E. Ant species (610, 620, 630, 640)

| File | Size | Subject |
|---|---|---|
| `SHARED_610.pix` | 141 x 117 | **Weaver ants building a leaf nest**: the edges of two big leaves (curved outlines with veins) being drawn together; **a chain of worker ants**, each holding the waist of the one in front, pulling one leaf edge across; **one worker holding a larva in its mandibles** against the leaf edge and spinning a fine silk thread (a line of dots / a thin line between the larva and the leaf). One boxed label with a leader: `Larvae` (89,5)-(124,17) (35 x 12), top right, to the larva held by the worker. **Columns 0..6 are cut: keep them white** (so start the drawing at x 7). |
| `SHARED_620.pix` | 139 x 64 | **Harvester ants carrying seeds**: two or three workers in side view walking left to right (or right to left; your choice), each with **a large seed in its mandibles**, on a ground line, with several loose seeds (ovals with a groove) scattered on the ground. No boxes. Shown on the harvester-ants card and on the foraging card, so it reads as "foraging workers carrying food". |
| `SHARED_630.pix` | 112 x 65 | **A column of army ants on the march**: five to seven big-headed, long-legged workers in single or double file, side view, overlapping a little, some carrying **a larva or a piece of prey**, small drawing, on a ground line; no eyes drawn (they are almost blind), hooked mandibles. No boxes. |
| `SHARED_640.pix` | 122 x 110 | **Leafcutter ants**: three or four workers walking in a line, each **holding a cut piece of leaf upright over its back** (a green-leaf crescent, shown with a midrib), one worker at the left **cutting a leaf edge** with its mandibles; at the bottom a hint of the **fungus garden** (a rounded, sponge-like mass with a tiny worker on it) if it fits. No boxes. |

## F. Behaviour and the nest (510, 520, 530, 540, 550, 560)

| File | Size | Subject |
|---|---|---|
| `SHARED_510.pix` | 222 x 101 | **A nest cut open (a cross-section of the ground)**: the **ground surface** near the top (rows 0..14) with a few grass blades and a small mound with the **entrance hole**; a vertical **shaft** going down, side tunnels, and rounded **chambers** with soil drawn in hatching. Lower left: the **queen's chamber** with a large queen and a few eggs; in the middle and the right: **nurseries** holding eggs, larvae and pupae in small piles, with a worker or two; one or two small chambers (stores) with grains or crumbs. Five boxed labels with leaders: `Queen's chamber` (1,55)-(42,83), a **three-line or two-line** label (41 x 28), to the queen's chamber (lower left); `Queen` (56,60)-(84,77) (28 x 17), to the queen herself; `Brood` (136,40)-(165,55) (29 x 15) and `Brood` (122,62)-(152,79) (30 x 17), each to a different small chamber of young; `Nurseries` (173,52)-(222,67) (49 x 15), to the right-hand nursery. The boxes sit on the soil: keep the chambers they name close to them. |
| `SHARED_520.pix` | 167 x 149 | **Two ants communicating**: two workers meeting head to head and **touching antennae** (the antennae drawn in the foreground, crossing), with short wavy lines or dots between and above them for **chemical signals**, and, near the lower part, a short **trail of dots** leading away. One boxed label with a leader: `Antennae` (107,0)-(156,21) (49 x 21), top right, to an antenna. **Columns 0..33 are cut on the card: keep them white** (so the drawing starts at x 34). |
| `SHARED_530.pix` | 218 x 69 | **A scent trail**: along a ground line, an **ant pressing the end of its abdomen (gaster) against the soil** to lay a trail (a dotted line behind it) as it leaves a **food item** at the right (a crumb or a seed) and heads left toward a **nest entrance** (a hole with a small mound); behind it a **line of ants** following the dotted trail. One boxed label with a leader: a label for the chemical signal the trail is made of, the pheromone (16,2)-(71,25) (55 x 23: one line `Pheromone` in the small face, or two short lines), top left, to the dotted trail. |
| `SHARED_540.pix` | 111 x 105 | **A fight between ants**: two or three ants in combat, seen from the side, one **gripping the other's leg with its mandibles**, another **raising its gaster to spray** (small dots and lines for the spray); a few fine motion lines; a ground line. Shown on the fighting card and the warfare-tactics card. **On card 175 columns 0..15 are cut**: keep the left 16 columns to a ground line, leg tips and motion lines only (no body). No boxes. |
| `SHARED_550.pix` | 194 x 103 | **Ants tending aphids**: a plant stem or leaf with **a cluster of aphids** (small, round, soft, with short tubes at the rear), and **an ant stroking an aphid with its antennae** while a **drop of honeydew** swells at the aphid's rear; a second ant drinking the drop. Two boxed labels with leaders: `Honeydew` (91,4)-(143,16) (52 x 12), top middle, to the droplet; `Aphids` (161,16)-(190,30) (29 x 14), top right, to the aphid cluster (so put the cluster in the right half and the ant and the droplet in the middle). |
| `SHARED_560.pix` | 135 x 87 | **Brood care in a nursery chamber**: a rounded chamber cut in the soil (hatched), a pile of **eggs** (small ovals) on one side and **larvae** (curved, segmented grubs) and a **pupa in a cocoon** on the other; **two nurse workers**: one **carrying an egg in its mandibles** towards the pile, the other **licking a larva**. No boxes. |

## G. Life cycles (710, 720)

| File | Size | Subject |
|---|---|---|
| `SHARED_710.pix` | 299 x 68 | **The ant's life cycle as a strip, left to right**: an **egg** (a small oval), a **larva** (a curved, legless, segmented grub, bigger), the larva **spinning a cocoon**, a **pupa** (a pale, folded adult form inside the cocoon's outline), and an **adult worker just emerging** from the cocoon. Small **arrowed lines** between the stages. Five boxed labels with leaders: **top row** `Egg` (7,2)-(30,14) (23 x 12), `Larva` (80,2)-(115,13) (35 x 11), `Pupa` (198,1)-(228,14) (30 x 13) (each a **short leader down to its stage**, so the stages' drawings sit **below** those boxes: egg around x 5..35, larva x 70..125, pupa x 185..240); **bottom row** `Spin` (124,54)-(159,67) (35 x 13: the action of spinning the cocoon) and `Emerge` (267,51)-(298,66) (31 x 15: the adult coming out), each with a **short leader up to its drawing** (the cocoon-spinning larva around x 120..165, the emerging adult around x 255..298, both **above** the bottom boxes). Words fit the boxes (`Emerge` in 31 px with narrow letters; or `Hatch`). |
| `SHARED_720.pix` | 302 x 53 | **The colony's three stages**, side by side in three equal panels separated by thin vertical lines (no boxes): **(1) founding**: a ground cross-section with a **lone queen** in a tiny sealed chamber with a few eggs and a first small group of larvae; **(2) growth**: a bigger nest with many **workers** and tunnels, food being carried in; **(3) reproduction**: the nest with winged **males and new queens** flying up from the entrance. Plain unboxed captions under each panel are optional (`founding`, `growth`, `spreading`). |

## H. The colony flowchart (880)

`SHARED_880.pix`, **290 x 141**: a diagram of how the colony's numbers influence one another (shown on the card that
explains the Quick Game's dynamics). It is **13 boxed labels joined by arrows**, each box a **pop-up link** whose
definition appears while the button is held. **Box rectangles are fixed** (label face; each 11 px high); draw them exactly:

| Id | Box | Size | Names | Suggested word |
|---|---|---|---|---|
| F1 | (4,3)-(74,14) | 70 x 11 | the share of workers sent foraging | Foraging ants |
| F2 | (106,3)-(176,14) | 70 x 11 | the food brought in | Food collected |
| F3 | (79,29)-(142,40) | 63 x 11 | the food kept in the nest | Food stored |
| F4 | (156,29)-(213,40) | 57 x 11 | the food the ants eat | Food eaten |
| F5 | (4,52)-(67,63) | 63 x 11 | the share of workers sent digging | Digging ants |
| F6 | (81,52)-(131,63) | 50 x 11 | the size of the nest | Nest size |
| F7 | (143,62)-(222,73) | 79 x 11 | the colony's nourishment level | Colony health |
| F8 | (3,90)-(73,101) | 70 x 11 | the share of workers nursing | Nursing ants |
| F9 | (121,90)-(194,101) | 73 x 11 | how fast the queen lays | Egg production |
| F10 | (99,123)-(199,134) | 100 x 11 | the number of ants | Colony population |
| F11 | (231,92)-(290,103) | 59 x 11 (the rectangle is 1 px past the picture: draw it x 231..289) | deaths by hunger | Starvation |
| F12 | (231,111)-(284,122) | 53 x 11 | deaths by predators | Predation |
| F13 | (231,130)-(271,141) | 40 x 11 | deaths in fights | Fights |

**Arrows** (cause to effect; 1-px lines with a 3-px arrowhead at the effect end, straight or with a right-angle bend,
**never through a box**): F1 to F2; F2 to F3; F2 to F4; F5 to F6; F6 to F3 (a bigger nest stores more); F6 to F9 (a
smaller effect: a thinner or dashed line is fine); F4 to F7; F3 and F7 **both ways** (stored food is used when health
is low: an arrow with a head at each end); F7 to F9; F8 to F9; F9 to F10; F7 to F11; F11, F12 and F13 each to F10 (draw
one vertical bar at about x 222..226, between the three boxes' left edges and F10, to which the three boxes connect, and
one arrow from the bar to F10's right edge). No other arrows.

A **hint caption** (your own words, 2 lines in the small face, unboxed: that the boxes can be clicked for an
explanation) goes into the free lower-left area (x 0..95, y 108..140). Nothing else is drawn.

## The script's checks

`make_encyclopedia_bitmaps.py` must **assert** (fail the build of the files) that:

1. exactly the **40 files** of the scope table exist, each `SHARED_<id>.pix` with the **exact size** of the table, only `0` and
   `f`, no `.`;
2. **every boxed label** (the box tables of groups A, B, C, D, E, F, H): its rectangle's four edges are black along at least
   95 % of their length (the outline is in the rectangle), the inside is white except the lettering, the lettering is
   centred (the left and right gaps differ by at most 2 px) and **at least 2 px** of white lie between lettering and
   outline on each side; a rectangle that the table says is cut by the picture's edge is checked against the shortened
   box; **no two boxes overlap**; **no box exists outside the lists** (a black 1-px outlined rectangle of 20 x 10 or more that
   is not a listed box is an error);
3. **each leader's tip** (record one `(x, y)` per leader, and the rectangle of the part it names) lies inside that part's
   rectangle; no leader pixel lies inside a box other than its own box's edge;
4. **the cut rows and columns are white**: 410 rows 0..1, 440 rows 0..3, 460 rows 0..1, 213 rows 0..1, 230 row 0, 520
   columns 0..33, 610 columns 0..6; and 540 columns 0..15 carry no black pixel above the ground line (record the ground line's
   row);
5. **880**: every arrow's recorded endpoints lie on the named boxes' edges, and no arrow's pixels pass through a box other
   than at its endpoints;
6. **170 / 160**: the one-pixel white border all round the box; the word's pixels inside the box only;
7. **128, 129, 160, 21000..21003** exist (spares);
8. the lettering never spells a forbidden word (a list of the forbidden names in the script, checked against the strings
   the script draws).

`python tools/clean_pack/build.py` then packs the files (`SHARED/2/<id>.bin`, 1 plane); the spec side runs the game with
`-- --clean --pack=remake/build/dev_pack.zip`, opens the encyclopedia and every card, checks each picture in place and
compares the look with the originals for similarity before the pack ships.

## Previews

`preview_encyclopedia.png`: (1) a **contact sheet** of all 40 pictures at 2x on a mid-grey background, each with its id
and size; (2) **the cards as the game shows them**: for each row of the placement table, a 320 x 200 white card at 2x with the
picture drawn at the given position (clipped to the card), the text rectangles shown as a light-grey hatched block, the
navigation strip (rows 180..199) as a darker hatched block, and the link rectangles outlined in red (so a box that is
off its rectangle shows at once). **Look at it at most 5 times per pass.**

## Consistency between the pictures

- **One ant model** for 410, 420, 440, 460, 128, 200, 300's ant, the heads of 520, 540, 610, 620, 630, 640, 550, 560, 510,
  530, 710, 720: same proportions, leg style, antenna elbows and head shape at any scale (small ones simplify, not redesign).
- **One tone set and one line weight** throughout; one label face and one box style throughout (the small differences of
  box height only).
- **Orientation**: single insects face left; sequences read left to right (life cycles, the trail's direction is free).
- The **picture's words must agree with the topic of the card they open** (the later card text names the same things):
  names of anatomy, castes and species are the standard terms; the spec side reconciles any difference with the card
  text when that is written.
- Pictures that **share a card** (410 with 400, 600, 700) must not clash in scale: 410 is the same ant as the other
  worker drawings at 92 px long.

## Not found / open

- **18 picture ids that cards refer to but that do not exist in the game's files** (the game draws nothing; the card's
  link rectangles still work, so the card shows an empty space and a clickable blank): **151** (65 x 111 on the top card,
  to the right of the topic menu), **211** (81 x 36, the eyes card), **212** (39 x 36, the mouth card), **430** (67 x 75,
  the replete card), **570** (127 x 69, the trophallaxis card, whose text speaks of an animated sequence: a Mac-only
  feature), **860** (36 x 19, gathering food), **875** (107 x 31, the full game), **877** (20 x 122, the experimental
  game), and ten small **see-also buttons** 161, 162, 163, 164, 165, 166, 167, 168, 169, 171 (each 15 px high and 37 to
  111 px wide, each the hotspot of a card link). They are **not part of this batch**: the pack builder refuses an id that
  is not in the measurements (`bitmaps.json`), so making them needs a change of the measurements and of `build.py` first;
  the 1:1 remake leaves them blank as the original does. They are candidates for the modern game (Formica).
- **Cards 127 and 129** (an older top card, an index) are never reached (no card links to them) and show only the
  navigation strip: no picture of this batch.
- The seven **never-shown pictures** (128, 129, 160, 21000..21003): no card, no layout and no code draws them; their roles
  are guesses from their sizes (see group B). If one turns out to be used, the spec side will fix its description.
- **The pictures' label words** are in the pictures, so they cannot follow the later card text automatically: when the
  cards' text is re-written the spec side checks that the topic names match (a label that no longer fits is redrawn).
- The **link rectangles** are the original's; the pictures' boxes must match them to the pixel, so the cards' own link
  data (a later batch) keeps these rectangles.
- **Where the card data's picture rectangle is 1 or 2 px larger than the bitmap** the engine draws only the bitmap at the
  rectangle's top-left; the extra pixels are never drawn.
