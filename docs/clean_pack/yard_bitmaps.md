# Spec: the yard and its actors (the yard window's pictures and toolbar, the people and animals, the spider, the map-window actors)

> **Status (2026-10-31):** complete, ready for a maker (5 passes, see "How to work"). Written from the remake's yard code
> (`YardRenderer`, `Spider`, `Main.cs`), the window layout, the game's own tables (offsets per frame, states and timings
> of the actors, the spider's body offsets) and the finished spider-legs spec. Covers **114 bitmaps**. The encoder and its
> checks are in `tools/clean_pack/build.py` (`cat_bitmaps`; the same `.pix` files and rules as `ui_bitmaps.md`). What could
> not be traced is said where it comes up ("not found", and the closing section).

Output folder: `remake/game/assets/clean/src/bitmaps/` (shared with `ui_bitmaps.md`; **only create files for the 114 ids of
this spec**, see "Files and other batches"). Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an entry). **One
file per bitmap, named `<id>.pix`** (for example `8000.pix`), plus `make_yard_bitmaps.py` (the script that
writes every `.pix`, so they can be regenerated; split it into modules if you like), `README.md` (the design: the scale,
the light, the colour roles, how to rebuild) and, recommended, `preview.png` (see "Previews").

## Contents

- Scope - How to work - Files and other batches - Format and rules for every file - Conventions (coordinates, drawing order, what the game does) - Look
- Groups: A the yard's pictures (house outside and inside, lawn, grid strips), B door and room patches, C small scenery (rain, queens, sign),
  D the toolbar and its help, E the person and the yard mower, F the dog, G the cat and the bird, H the spider, I the map-window actors and the marker
- The script's checks - Previews - Consistency with the other batches - Not found / open

## Scope

The HCEGANT type-2 bitmaps with ids 1000..1999, 7000..7999 and 8000..8999: **114 files**.

| Group | Ids | Count | What |
|---|---|---|---|
| A | 7000, 7001, 7003, 7020, 7021, 7022 | 6 | the yard window's house (outside, inside), lawn, and the three stacked grid strips of the colony views |
| B | 8900..8903, 8905, 8200, 8201 | 7 | patches drawn over the house pictures: the door opening, the person in the chair and at the fridge, a spare |
| C | 7005, 7006, 7007, 1260 | 4 | raindrop, the two mating-flight queens (1 x 1 dots), the "for sale" sign |
| D | 7010, 7011 | 2 | the yard window's toolbar and its help overlay |
| E | 8000..8011, 8020..8023, 8100..8111, 8800..8802 | 31 | the person walking, standing, mowing, and the yard mower |
| F | 8500..8511, 8600..8603 | 16 | the dog |
| G | 1300..1305, 1310..1312, 1320..1329, 1250, 1251 | 21 | the cat (walking, startled, pouncing) and the bird crossing the yard |
| H | 1000..1007, 1050..1053 | 12 | the spider's body in 8 headings, and its 4 "beaten" frames |
| I | 1100..1107, 1200..1203, 1210, 1211, 1400 | 15 | the small spider, the sneaker and the mower of the Map window, and the triangle marker |

(The file-format notes list 1000..1007 as a "large black ant": the game draws them as **the spider's body**; there is no
large ant. The ant sprites are another batch, `ant_sprites.md`.)

**Not in this spec**: the title, select and about screens (2000s, 3000s), the scenes (9000s, 12000s), the interface bitmaps
(`ui_bitmaps.md`), the ant and tile sheets, the spider's legs and fangs (`spider_legs.md`, made already: they are
**lines drawn by the game over your body pictures**, group H says how they meet), and every SHARED bitmap.

## How to work

Five passes; each ends with a build of what exists (`python tools/clean_pack/build.py` refuses a wrong size, a missing mask
or an opaque picture with holes) and with the script's assertions (see "The script's checks"):

1. **Pass 1: the yard's scenery (group A and C):** 7000, 7001, 7003, 7020..7022, 7005..7007, 1260 (10 files).
   Do the lattice and the fixed rectangles first, then the three big pictures from **one drawing program** (a function that
   draws the lawn, the fence and the yard's furniture once, and two functions for the house, outside and inside, with a
   parameter for the door's state and for the two room spots of group B). Keep the program importable: pass 3 renders from it.
2. **Pass 2: the toolbar (D):** 7010, 7011 (2 files) and the two crops for the tutorial (see "Files and other batches").
3. **Pass 3: the people (E) and the patches that show them (B):** 8000..8011, 8020..8023, 8100..8111, 8800..8802, then 8900..8903, 8905, 8200, 8201 (38 files).
   One figure model (proportions, clothes, the walk cycle) drawn for four headings; the mower for 8100..8111 and 8800..8802 belongs to it. The door and room patches
   are made last, **by cropping renders of pass 1's program with the figure drawn into them** (so their edges match the pictures by construction).
4. **Pass 4: the animals (F, G):** 8500..8511, 8600..8603, 1300..1305, 1310..1312, 1320..1329, 1250, 1251 (37 files).
5. **Pass 5: the spider and the map-window actors (H, I):** 1000..1007, 1050..1053, 1100..1107, 1200..1203, 1210, 1211, 1400 (27 files).

Make every picture of a set from the same model (a figure drawn procedurally or by hand once, then posed); the sets are
animations, and the frames of a set must agree with each other and with the game's per-frame offsets (see "Alignment").
Rely on the script's assertions rather than on looking at pictures: **look at `preview.png` at most 5 times per pass**.

## Files and other batches

- **Do not open any other file of the repository**, with these exceptions (all are clean-pack sources made by other makers,
  never the original's data): `remake/game/assets/clean/src/spider/legs.json` (the spider's leg geometry; group H),
  and, if they exist when you start, the files `14000.pix`, `17006.pix`, `17007.pix` and
  `make_ui_bitmaps.py` in your output folder (the interface batch, which runs in the same folder; you may copy its pixel
  lettering and match the buttons' subjects, see D and "Consistency").
- **Never overwrite or delete a file that is not in your 114.** The one exception: `17006.pix` and
  `17007.pix` (the tutorial's "House" and "Patch" button pictures, made as plain buttons by the interface batch) are
  to be **crops of your own 7010** (D says which windows). Your script writes them **only if they already exist**
  (replacing them) and says so in its output; if they do not exist yet, it leaves them alone, and your `README.md`
  says "run `python make_yard_bitmaps.py --crops` after the interface batch" (a flag your script must provide). This keeps the two
  batches from fighting over the files whichever finishes first.

## Format and rules for every file

- `.pix` as in `docs/clean_pack/README.md` (one line per pixel row, one character per pixel: `0`-`9`, `a`-`f` a palette
  index, `.` transparent, `#` comment lines, every row the same length). **The size of each picture is exact** (the game places
  things by pixel; the build rejects another size). The sizes are in the tables.
- **Opaque** pictures contain **no `.`**; **masked** ones **must** contain `.` where the picture below shows through. Every
  table says which. All pictures are 4-plane (16 colours). **Tightness:** unless the table says otherwise, a masked
  sprite's opaque pixels must **touch all four edges of its frame** (the game's per-frame offsets assume the frames are
  cropped to their drawing: a frame with an empty border would sit in the wrong place).
- The palette is the Apple 16 colours of `README.md`. Their values (for contrast and colour judgement): 0 `FFFFFF`, 1 `FCF305`,
  2 `FF6402`, 3 `DD0806`, 4 `F20884`, 5 `4600A5`, 6 `0000D4`, 7 `02ABEA`, 8 `1FB714`, 9 `006411`, 10 `562C05`, 11 `90713A`,
  12 `C0C0C0`, 13 `808080`, 14 `404040`, 15 `000000`. Everything is drawn at 640 x 480 with no scaling and no anti-aliasing.
- **Wording.** All lettering is English and yours. A label that names a function (`Patch`, `House`, `MATE`) may use that word or
  a plain synonym of the same length; a help sentence (7011) is **new wording** of the same meaning and about the same length.
  No picture may contain "SimAnt", "Maxis", a publisher's or author's name, a logo or a trademark.
- **Coordinates** in the tables are pixels from the picture's own top-left corner, **x1 / y1 exclusive**, unless the
  words "yard coordinates" or "screen" are used (see the next section).
- **Do not copy** another game's art, and do not draw the people, the animals or the house as a known cartoon, comic or game
  character or place. The roles, sizes, poses, anchors and positions are fixed; the drawing is yours. Where a design choice would
  not matter to the game (colours of clothes, the style of the house) **choose your own**: for similarity review the house, the
  lawn's planting, the clothes and the animals' colours must **not** be a recolour of a famous original: pick, for example, a
  cream-walled house with a red-brown roof, a person in a red jacket and dark trousers, a spotted dog, a ginger cat.

## Conventions: coordinates, drawing order, what the game does

Read this first; most constraints come from it.

1. **The yard window** is window 25, rectangle **screen (62,62)-(578,386)**; it clips everything to it. Its pieces, in screen
   coordinates: the house picture at **(63,83)** (item 0x1903, 7000 in the Yard view, 7001 in the House view), the lawn picture
   7003 at **(344,83)**, the toolbar 7010 at **(64,339)**, the help overlay 7011 at **(62,296)**, and, in the colony views, the grid strips
   7020, 7021, 7022 at **(64,148)**, **(64,199)**, **(64,254)** (one under the other: they are stacked and end at y = 309).
   The **yard origin** is screen **(65,83)**: *yard coordinates* are screen minus (65,83), x to the right, y down. Hence:
   **picture pixel = yard + (2, 0) in 7000 / 7001; = yard - (279, 0) in 7003; = yard + (1, -65) in the strips.** The two house pictures
   are 281 wide (yard x -2..278) and the lawn begins at yard x 279: they join without a gap; **the seam must be invisible**.
   All three are 226 high (yard y 0..225). The grid strips cover yard y 65..225 (7020: 65..115, 7021: 116..170, 7022: 171..225).
2. **Actors are sprites drawn at yard (x, y) + the frame's offset (dx, dy), the sprite's top-left corner**, over the pictures, in
   this order (later ones on top): the cat, the dog, the person, the yard mower, the bird crossing, the sign, the raindrops, the
   mating queens. **They are clipped to the yard picture (64,83)-(577,339).** The tables in E to G give each set's offsets; the
   game's actor position is a point of its own that the offsets tie to your figure (see "Alignment"), so **the offsets are
   data you must design to, not something you can change**.
3. **Masked** bitmaps are drawn through their mask; nothing is recoloured (the black / red colour schemes of ants do not apply here).
   Pictures and sprites are drawn **as they are** and the game then XOR-fills (`colour ^ 15`) the **player's patch**
   (below) over everything, actors included. 
4. **The patch grid.** The yard is **12 x 16 patches** (column c = 0..11, row r = 0..15). The pictures show the grid as a **lattice of
   1-px lines** on the lawn: in yard coordinates, **horizontal lines at y = 65 + 10 r for r = 0..16** and **slanted lines on
   x + y = 232 + 28 k for k = 0..12**, all in **colour 9** on a lawn of **colour 8**, inside the parallelogram
   **65 <= y <= 225, 232 - y <= x <= 568 - y** (that is: 12 cells of 28 x 10 px per row, each row shifted 10 px to the left
   of the one above, so the edges slope one pixel per row). Patch (c, r)'s cell has its top-left corner at
   **yard (167 + 28 c - 10 r, 65 + 10 r)**; the game fills a parallelogram of 24 x 7 px inside it, corner at (169 + 28 c - 10 r, 67 + 10 r),
   in the colony views (black, red, a black / red check, or colour 8 for an empty patch) and XOR-inverts the same parallelogram on the
   player's patch in every view; in the "Graphic" view it stands 9-px-wide bars on the baseline y = 71 + 10 r at x offsets 168 and 180.
   **Every picture that shows the lawn must use exactly this lattice** (the codes above are the engine's constants).
   Use one function `lattice(x, y)` in your script and draw all of A with it.
5. **Frame rate.** The yard moves one step per game tick (about 3 to 8 steps a second at the normal speeds).
   Walk cycles advance one frame per tick (the table of each set says the order); actors move 3 to 6 px per tick.
6. **Highlighting** is the XOR above and, in the toolbar, an XOR of a button's rectangle (D).

## Look

A **16-colour pixel-art isometric yard**: the viewer looks down on a house and its lawn from above and in front; lawn lines run
down-left to up-right at 45 degrees (one pixel left per pixel down) and the lawn's rows run horizontally. **Light comes
from the top-left.** Sprites have a **black 15 outline** (1 px, except where the table says "no outline"), flat shading with
2 to 3 tones, no dithering except where said. The dark-grey **13** is the window's background around the yard (sky and everything
outside the lawn and the house): use exactly 13 there (the colony views fill the same area with 13 and the pictures must meet it).
Scale: the person is **about 30 px tall** and the dog **about 16 px long**, the house about 280 px long on screen; the ants of the
patch are invisible at this scale (a patch is 24 x 7 px). Keep all sets of one actor in one style (clothes, proportions).

# Groups

## A. The yard window: house outside, inside, lawn and grid strips (7000, 7001, 7003, 7020..7022)

All **opaque**, 4 planes.

| File | Size | Where (screen / yard) | What |
|---|---|---|---|
| `7000.pix` | 281 x 226 | (63,83); yard x -2..278 | **The Yard view's left part**: the house seen from outside, with the lawn in front of it and the garden behind it. |
| `7001.pix` | 281 x 226 | same place, drawn **instead of 7000** in the **House view** | The **same house with its roof and front wall cut away so the inside shows** (rooms, furniture), everything outside the house identical to 7000. |
| `7003.pix` | 233 x 226 | (344,83); yard x 279..511 | **The Yard view's right part** (drawn in both views): the lawn and its back fence. |
| `7020.pix` | 513 x 51 | (64,148); strip rows are yard y 65..115 | the **top third of the colony views' grid**: the lattice only |
| `7021.pix` | 512 x 55 | (64,199); yard y 116..170 | the middle third |
| `7022.pix` | 512 x 55 | (64,254); yard y 171..225 | the bottom third |

### The lawn, the lattice and the seam (7000, 7001, 7003, strips)

- The lawn is the parallelogram of convention 4, **colour 8 flat** (no texture; the colony views fill empty patches with colour 8
  and it must match), with the lattice in colour 9. In 7000 / 7001 the left part of the lawn is covered by the house (below); the
  part that shows must follow the lattice exactly, and **the lines must carry across the seam** between 7000 and 7003
  (pixel column 280 of 7000 / 7001 and column 0 of 7003 are neighbours in yard x 278 / 279): write the lawn by one
  function of yard coordinates, never by two drawings.
- **The house stands on the lawn's left side** and hides lattice columns 0 and 1 (all rows) and column 2 in rows 0..4: its front-wall base
  runs along the lattice line k = 3 from y = 65 to y = 115, steps over to the line k = 2 along y = 115 (a protruding **porch**, which
  holds the door and its steps), and then runs along the line k = 2 down to y = 225. Everything right of that boundary is
  open lawn with the full lattice. The boundary is the one the colony views mark (below).
- **Back fence**: a fence along the lawn's back edge, **top edge at yard y = 38 (+-1) from x = 250 to the right edge (x = 511)**, standing just
  above the lattice's top line (its foot at y 62..64). **The cat walks along its top**: the cat's feet are at y 36..38, so the
  top rail must be a plausible walking surface there. The fence is **in 7003 and in the right-hand 30 px of 7000 and 7001**, identical.
- Above and to the right of the lawn and behind the house (sky / outside): **colour 13** flat.
- **Frame**: the leftmost column of 7000 and 7001 and the **top row** of all three (and the rightmost column of 7003) are **black 15**
  (the window's border line); **row 1 is colour 13** (except at those frame columns). The bottom row of every picture is a lattice
  line where the lawn shows (y = 225 is the last row).
- **Furniture** is up to you (doghouse, hose, flower bed, tree ...) but keep **clear of the lawn lattice's visible cells**: nothing on the lawn except
  small things that do not cross the lattice lines, and **keep three areas free of detail** (the game draws actors there):
  the yard mower's parked place **yard (98,181)-(113,196)** and the sign's place **(170,186)-(224,223)**; also leave the lawn in front of the porch (yard x 150..230, y 100..160) open (the person comes out of the door and walks down there).
  The roof, walls and windows must lie **left of** the boundary above.
- **The person's route indoors (7001)**: in the House view the person walks around **inside the house** (scripted: from the armchair to the fridge and back, and to the porch door). His sprite's top-left, over time, is
  (44..91, 130..166) near the armchair, then up the house to (135..154, 60) and (159..208, 44..60) in the kitchen; his **feet** are about 9 px right of and 29 px below the sprite's top-left, so his feet follow the path
  **(53,195) -> (100,161) -> (163,89) -> (198,89)**. Keep a **floor band about 30 px wide along that path free of furniture** (a passage from the living area to the kitchen), with the armchair and the fridge at its two ends (their rectangles are below). In the Yard (outside) view he is not drawn on this route.
- **Fixed rectangles in 7000** (outside view; yard coordinates, picture pixel = x + 2): the **front door niche** is the rectangle
  **yard (172,73)-(198,115)** (26 x 42): a door in the porch's front wall, with the porch's wall around it; group B's door patches replace exactly this rectangle
  (picture pixels (174,73)-(200,115)). The niche's outer ring (1 px) must be wall colour. The door's steps may extend below y = 115.
- **Fixed rectangles in 7001** (inside view): the same house with the roof removed, and these two things **exactly where group B draws the patches**:
  an **armchair** (and the floor and wall behind it) in the rectangle **yard (45,166)-(62,196)** (17 x 30; picture pixels (47,166)-(64,196)), and a
  **refrigerator** (closed, upright, about 19 px wide) in **yard (207,47)-(226,77)** (picture (209,47)-(228,77)). A television and a
  sofa nearby are good; the rest of the rooms (a kitchen along the porch side, a living room along the other) is yours. In the inside view
  the **front wall is not drawn** (cut away) so that the player sees the floor and furniture from above-front.
- **7000 and 7001 are identical outside the house**: write a polygon `HOUSE_MASK` (the house's outline plus its roof overhang) in
  your script and assert that every pixel outside it is equal in the two pictures, and that **at least 55 % of all pixels are equal**
  (the garden, the lawn, the fence, the sky).
- The house's **style, colours, windows, roof, chimney, garden furniture and the fence's design are yours**. Avoid a blue-walled,
  black-roofed house; do not reuse any layout of windows from a known original.

### The grid strips (7020, 7021, 7022)

Used only in the colony views ("Strat" and "Graphic"). The game fills the yard picture area with colour 13 and then draws the three strips,
so **everything outside the lawn parallelogram is colour 13** in the strips, and the lawn is **colour 8 with the lattice in colour 9**, the
same function as in the pictures (convention 4; the strips are the lattice's rows y 65..225 cut into three pieces of 51, 55 and 55 rows;
7020 is one pixel wider, 513, and its last column is 13). Their pixel (sx, sy) is yard (sx - 1, sy + 65) in 7020, (sx - 1, sy + 116) in
7021 and (sx - 1, sy + 171) in 7022. Hence the top line of the lattice is the first row of 7020 and the bottom line the last row of 7022.
In addition, **mark the house's footprint** with a 1-px line of **colour 10**, drawn over the picture, one pixel up / left of the lattice's own pixels, along the boundary
described above (no code reads it; it shows the player which patches hold the house), in yard coordinates: the pixels with **x + y = 315 for y = 66..113**, then the horizontal run **y = 114 for x = 173..201**,
then the pixels with **x + y = 287 for y = 115..224**. The strips contain only colours 8, 9, 10, 13.

### Constraints that keep the pictures consistent with the sprites

- Actors are drawn over the lawn (and in front of the house wall) with their feet on the ground: the lawn's green 8 and the lattice 9 are
  the backgrounds all the actors' outlines must read on (black 15 outlines do).
- When the player's patch is highlighted the parallelogram is XOR-inverted (8 -> 7, 9 -> 6): nothing to design, but do not put colour 7 or 6 pixels in the lawn
  (the highlight would vanish).

## B. The door and room patches (8900..8903, 8905, 8200, 8201)

All **opaque**, 4 planes. Each is a small **patch drawn over a part of the house picture**, replacing it; they show the person at
the door, in his chair and at the fridge. The game draws them as sprites at the yard positions below, so **a patch's outer ring (the outermost pixel
all round) must equal the picture it lies on, and the rest must be the same room / wall seen with the person**. Make each patch **by rendering the scene from your program in
the right state and cropping the rectangle**, never by painting a separate picture.

| File | Size | Drawn at (yard) over | What it must show |
|---|---|---|---|
| `8900.pix` | 26 x 42 | (172,73) over **7000** (picture px (174,73)) | the porch door **just opening** (or just closing): the person is mostly hidden behind the door |
| `8901.pix` | 26 x 42 | same | the door **wide open**, the person **starting to step out** (leaning forward) |
| `8902.pix` | 26 x 42 | same | the door open, the person **in the doorway, almost out** |
| `8903.pix` | 26 x 42 | same | the door open, the person **standing on the threshold**, about to go in or out |
| `8905.pix` | 19 x 35 | not found in use | **spare**: a solid colour-15 rectangle (every pixel `f`) |
| `8200.pix` | 17 x 30 | (45,166) over **7001** | the **person sitting in the armchair** (watching the television), the chair and the floor as in 7001 |
| `8201.pix` | 19 x 30 | (207,47) over **7001** | the **person standing at the refrigerator with its door open**, taking something out |

How they play (so the sequence reads): **leaving**: 8900, 8901, 8902, then the walking figure (8006, 8007 in group E) at (174,93), (175,99); **entering**: the walking figure at (172,93) (8000), 8903, 8900 (the
door closing), then nothing. So **8900 must look right both as the door starting to open and as the door closing**. A frame lasts one tick (a few frames a second).
8200 and 8201 are drawn by the game **only in the House view** (the original hides the scripted figure in the Yard view; the remake
currently draws it in both views and will be fixed on the spec side); the door frames appear in the Yard view and, harmlessly, over 7001 in the
House view. The person is the **same figure as group E** (same clothes, same proportions, same colours), shown at the same scale.
Rules: the opaque pictures contain no `.`; the person's pixels never extend past the patch.

**Check**: write the ring comparison into the script: for 8900..8903 the outermost ring equals the 7000 pixels, for 8200 and 8201 it equals the 7001 pixels
at the stated rectangles (this holds by construction if you crop renders).

## C. Small scenery sprites: rain, queens, for-sale sign (7005..7007, 1260)

| File | Size | Masked | What |
|---|---|---|---|
| `7005.pix` | 7 x 37 | yes | **a raindrop streak**: a **1-pixel-wide slanted line** of colour **7** (cyan) from near the top right to the bottom left, falling to the lower left: it runs from column 5 at the top to column 1 at the bottom (a slope of 4 px over 35 rows). **Not tight**: the first and the last row are transparent. Exactly one opaque pixel per row from row 1 to row 35. 15 streaks are drawn at random places at once (x 50..449, y 0..149 yard) every frame while it rains, over everything. |
| `7006.pix` | 8 x 1 | yes | **a black colony's winged queen on her mating flight**: only **one opaque pixel, at column 1**, colour **15**; the other 7 pixels transparent. Up to 16 are drawn on the player's patch corner while it rains, jittering by a pixel a tick. |
| `7007.pix` | 8 x 1 | yes | the same for **a red colony's queen**: one pixel at column 1, colour **3**. |
| `1260.pix` | 54 x 37 | yes | **a "for sale" sign**: a board on a post, planted in the lawn, drawn at **yard (170,186)** (picture px (172,186) of 7000) when the people put the house up for sale (the ants have won). The board fills the **top two thirds** (about 54 x 26, with a 1-px black outline) and the post runs down from it (about 4 px wide) to the bottom row; **both sides of the post below the board are transparent** (about 48 % of the picture). Two lines on the board in your lettering: **`FOR SALE`** (large, black) and under it a **short second line of your own** (3 to 12 characters, for example `CHEAP`, small). Board colours: pale (light grey 12 or white 0), post brown or grey. It stands on the lawn, so give its foot a 1-px dark outline and no shadow. **Tight**: the opaque pixels touch all four edges. |

## D. The yard toolbar (7010) and its help (7011)

### 7010: `7010.pix`, 512 x 46, opaque

Drawn at screen (64,339), at the bottom of the yard window. A **bevelled panel on light grey 12** (top row white 0, bottom row black 15,
buttons raised) with **four view buttons, the mating-flight controls, a "help" button and two colony counters**. Every control below is a **hit rectangle** in the picture's
coordinates (checked against the window's layout: the game tests clicks against them), and the buttons marked **inverted** are shown by the game by XOR-ing
their rectangle (`colour ^ 15`: yellow / dark grey, orange / medium grey, red / light grey, magenta / tan, purple / brown, blue / dark green, cyan / green, white / black) while they are selected or active: **their picture and lettering must read both as drawn and inverted** (lettering / symbol against its face: contrast ratio at least 3 : 1 in both states,
computed with the colour values above; do not put mid-tones on mid-tones).

| Control | Rect (x0, y0)-(x1, y1) | Size | What it shows / does |
|---|---|---|---|
| `Patch` view | (7,5)-(40,31) | 33 x 26 | a picture of **the patch's ground seen from above with small dots for food and ants** (the subject of the Map window's "Surface" button); returns to the single-patch view. Label **below**. Not inverted. |
| `House` view | (47,5)-(80,31) | 33 x 26 | a picture of **the house and its lawn**, front view (the subject of the Map window's "Yard" button); toggles inside / outside. **Inverted** while the Yard or House view shows. Label below. |
| `Strat` view | (87,5)-(120,31) | 33 x 26 | a picture of the **grid of patches coloured by colony** (a few cells black, red and checkered on green); **inverted** while the Strat view shows. |
| `Graphic` view | (126,5)-(159,31) | 33 x 26 | a picture of the **grid with bars standing in it** (short black and red bars); **inverted** while the Graphic view shows. |
| `MATE` | (173,5)-(207,32) | 34 x 27 | a picture of **a few winged ants in the air** (the mating flight), on a pale sky; starts the flight. Label below. Not inverted. |
| queens count | (215,21)-(249,31) | 34 x 10 | a **text rectangle: flat white 0** (the game writes the number of waiting queens in black, centred): keep it plain, frame it **outside** the rectangle. The word `Queens` (label face, black) above / left of it, in the rows 4..19. |
| `AUTOMATIC` | (257,6)-(317,17) | 60 x 11 | a **flat bevelled button, label inside**; one of two radio buttons: **inverted** while automatic placement is selected. |
| `MANUAL` | (257,20)-(317,31) | 60 x 11 | the same for manual placement; inverted while selected. |
| `PLACE` | (324,5)-(357,32) | 33 x 27 | a picture of **one winged queen about to land** on the ground (founding a colony), pale sky; **inverted** while placing. Label below. |
| `?` help | (367,25)-(390,43) | 23 x 18 | a button with a **green 9 "?"**; the overlay shows while it is held. |
| black colonies | (473,7)-(507,17) | 34 x 10 | **text rectangle: flat white 0** (the game writes the number, black, centred). The words **`BLACK COLONIES`** (black 15) at its left, right-aligned to x about 470, in rows 5..19. |
| red colonies | (473,27)-(507,37) | 34 x 10 | **text rectangle: flat white 0** (number in black). The words **`RED COLONIES`** in **red 3** at its left, right-aligned to x about 470. |

- **Button boxes.** A picture button's visible box is its hit rectangle **grown by 1 px at the left and top and 2 px at the right and bottom**
  (raised bevel: white 0 highlight 1 px top and left, dark grey 14 or 13 shadow 1 to 2 px bottom and right): e.g. Patch's box is
  (6,4)-(42,33). The XOR rectangle is the hit rectangle itself, so the outer ring stays as it is and must look right either way
  (use light and dark greys, not coloured pixels). Radio buttons: the bevel is **inside** the hit rectangle.
- **Labels** (label face: bold, upright, capital height 7, black 15; draw your own or copy the interface batch's) **centred under their buttons in rows 35..41**:
  `Patch`, `House`, `Strat`, `Graphic`, `MATE`, `PLACE` (a plain synonym of the same length is fine). Nothing else in rows 33..44 under those buttons.
  `AUTOMATIC` may be written `AUTO` if the word does not fit 56 px.
- Colours: light grey 12 face; the picture buttons may use the full palette inside their boxes. The five pictures (Patch, House, Strat, Graphic) should be
  **drawn once each and reused**: the House picture and the Patch picture are the same subjects as the Map window's `Yard` and `Surface` buttons (`ui_bitmaps.md`, E); if
  `14000.pix` exists you may crop its pictures and enlarge or redraw them, otherwise draw your own (you do not have to match them pixel for pixel,
  but a player must recognise the same subject).
- The area outside the controls is flat light grey 12 with thin dividers between the groups (views, mating, the colony counters).

**The tutorial's crops (17006, 17007).** The tutorial shows two of these buttons as pictures. They are **crops of your 7010**, exactly:
`17006.pix` (37 x 29) = 7010 pixels **(45,4)-(82,33)** (the House button's box (46,4)-(82,33) and one column of the panel at its left, no label), and
`17007.pix` (41 x 30) = 7010 pixels **(4,3)-(45,33)** (the Patch button's box (6,4)-(42,33) with 2 to 3 columns and one row of the panel round it, no label). Your script asserts that each button's box lies inside its window and that the windows end above the label (label ink starts at row 35). See "Files and other batches" for when to write them.

### 7011: `7011.pix`, 512 x 47, **masked**, 4 planes

The **help overlay** of the yard window, drawn at **screen (62,296)** (that is **(-2, -43) relative to the toolbar's top-left**) while the `?` button is held.
Its **rows 0..46 cover the yard picture's bottom edge (screen y 296..338) and rows 43..46 the toolbar's top 4 rows**, so the callouts sit **just above their buttons**, and
the buttons themselves (from toolbar row 5) are never covered. A **band of white callout boxes, one above each control**, with a dark frame, the lettering inside in your
**small face** (regular, line pitch 10 or 11), centred, 2 to 3 short lines per box. **Every box ends on overlay row 46** (its bottom edge is the picture's last row, a continuous dark line along the band's foot);
the boxes of the left group (the four views and the mating controls) **start at row 10** (37 rows high: three lines of 11 px fit) and sit side by side **without overlapping or gaps** from x = 0 to about x = 363,
and **two small heading tabs rise above the band** (rows 0..10, about 40 to 60 px wide, a frame on three sides joined to the band's top edge; each carries a one-line heading). **There are no leader lines** (the box is the pointer).
The colony counters' box is separate, at the right, **top at row 20**, x 443..511. Colours: only **0, 14 and 15** (white panel, dark frame and lettering) plus transparent `.`; everything else transparent.
Overlay x = toolbar x + 2. Each box must cover **at least the middle 60 %** of its button's x-range (given in overlay x), and neighbouring boxes do not overlap.

| Callout (new wording, what it says) | Covers overlay x (hit rect + 2) |
|---|---|
| `Patch`: go back to the patch view of the ants | 9..42 |
| `House`: switch between the house's inside and outside | 49..82 |
| `Strat`: colour the grid by which colonies live on each patch | 89..122 |
| `Graphic`: show each patch's colonies as bars | 128..161 |
| heading **tab** over the four view boxes (a heading such as `Views`) | within 9..161 |
| `MATE`: send the males and new queens on their mating flight | 175..209 |
| the queens count: the number of new queens waiting | 217..251 |
| `AUTOMATIC` / `MANUAL`: let the game place new queens, or place them yourself (one box over both) | 259..319 |
| `PLACE`: found a colony with a waiting queen | 326..359 |
| heading **tab** over the mating group (such as `Mating flight`) | within 175..359 |
| the colony counters: how many black and red colonies exist (the separate box, **top at row 20**, x **443..511**) | 475..509 |

The `?` button itself (overlay x 369..392) has no callout; the band may stop at x about 363 and resume with the colony box.

## E. The human and the yard mower (8000..8023, 8100..8111, 8800..8802)

All **masked**, 4 planes, black 15 outline, **tight** frames. One person (the owner of the house), about **30 px tall**, seen from above-front in the yard's isometric
view; the same figure in all of E and in group B. **Headings** (the person moves along the yard's axes, on screen):
**0 = up-right** (moving away from the viewer, back or three-quarter-back view; 4 px right and 4 px up per tick),
**1 = right** (6 px per tick, profile / three-quarter), **2 = down-left** (towards the viewer, front or three-quarter-front view; 4 px left and 4 px down),
**3 = left** (6 px per tick). A walking set has 3 frames per heading; **the game cycles them in the order 0, 1, 2, 1** (one frame per tick): **frame 1 is the passing pose
(legs together, the narrowest), frames 0 and 2 the two strides (opposite legs forward)**, so 0 -> 1 -> 2 -> 1 -> 0 ... must read as one continuous walk.

| Set | Files | Size and the game's offset (dx, dy) per frame |
|---|---|---|
| **Walk, heading 0** (up-right) | 8000, 8001, 8002 | 12x30 (3,2) · 15x30 (3,0) · 17x30 (1,2) |
| Walk, heading 1 (right) | 8003, 8004, 8005 | 18x29 (0,3) · 10x30 (3,2) · 17x28 (0,3) |
| Walk, heading 2 (down-left) | 8006, 8007, 8008 | 19x30 (1,2) · 14x30 (4,0) · 14x29 (4,2) |
| Walk, heading 3 (left) | 8009, 8010, 8011 | 17x28 (3,3) · 10x30 (7,2) · 18x29 (2,3) |
| **Standing**, headings 0..3 | 8020, 8021, 8022, 8023 | 13x30 (4,0) · 7x29 (5,2) · 13x31 (4,0) · 7x29 (6,2) (one picture per heading; the game shows it when the person pauses: 8021 / 8023 are the **narrow profile** views, so heading 1 / 3 are side views) |
| **Mowing, heading 0** (mower baked in, pushed up-right) | 8100, 8101, 8102 | 19x29 (0,1) · 16x28 (3,0) · 17x29 (2,1) |
| Mowing, heading 1 (right; **mower is sprite 8801**) | 8103, 8104, 8105 | 18x28 (1,1) · 14x28 (5,0) · 19x28 (0,1) |
| Mowing, heading 2 (down-left, mower baked in) | 8106, 8107, 8108 | 22x32 (0,1) · 19x33 (0,0) · 21x32 (0,1) |
| Mowing, heading 3 (left; **mower is sprite 8802**) | 8109, 8110, 8111 | 19x28 (0,1) · 14x28 (0,0) · 18x28 (0,1) |
| **Yard mower, parked** | 8800 | 14x15, offset none: the game draws it at yard **(98,181)** whenever the person is not mowing |
| Yard mower, pushed right | 8801 | 15x14: drawn at the person's position + **(19, 15)** on mowing frames 8103..8105 |
| Yard mower, pushed left | 8802 | 15x14: drawn at the person's position + **(-15, 15)** on mowing frames 8109..8111 |

(The walking figure is walked through the whole yard by the game: its position is a point of its own; the `Alignment` rule below ties your figure to it.)

**Alignment** (script-checked): for each frame, `R = centroid(opaque pixels of the frame) + (dx, dy)` (the centroid is the mean of the x and of the y of the opaque pixels, in the
frame's own pixels). **Every frame of E (walk, standing, mowing: 8000..8023, 8100..8111) must satisfy |R.x - 9.0| <= 3.0 and |R.y - 15.5| <= 2.5**,
and **within one set (3 or 4 frames) R must differ by at most 3.0 px in x and 3.0 px in y**. (This keeps the figure's body on the same spot of the screen from frame to frame, so it
does not jump; the game's offsets compensate each frame's width and height.) The sprite **widths and heights are fixed** by the table.

**Mowing** (the rule that joins the person and the mower): in the sets with a separate mower the person pushes it **at his side**:
- heading 1 (8103..8105): the person's right edge is at the person's position + 19 (the sprite's width + dx is 19 in all three) and **8801's left edge touches it**:
  the **person's hands hold the mower's handle at the right edge of the picture**, hands at the picture's bottom half; the mower 8801 (15 x 14) then sits to the right with its **bottom
  within 1 px of the person's bottom row**. The figure's feet are at its picture's bottom rows.
- heading 3 (8109..8111): the same, mirrored: the person's picture starts at the person's position (dx = 0), **8802's right edge touches its left edge**, hands at the **left edge**.
- headings 0 and 2: the mower is **part of the picture** (the person and the mower in front of him in the direction of travel, up-right for 8100..8102, down-left for 8106..8108); these pictures are wider and taller.
The mower must look like **one machine in all of 8100..8111, 8800..8802** (a small push mower: a deck, wheels, a handle, a grass bag; colour of your choice, not the person's colour). 8800 (14 x 15) shows it parked, seen from the same viewpoint.

## F. The dog (8500..8511, 8600..8603)

All **masked**, 4 planes, black outline, **tight**. A **medium-sized dog** about **16 px long**, seen from the isometric viewpoint. The dog wears a **collar of colour 1 (yellow)** (a 1 to 3 pixel mark; one pixel colour,
no other use of colour 1). **Headings** as in E: 0 up-right, 1 right, 2 down-left, 3 left (steps 3 px and 4 px per tick); **a walking set has 3 frames cycled 0, 1, 2, 1** (frame 1 = legs gathered).
Two **resting** headings (4 and 5), each with **2 frames alternating every tick**: they are drawn when the dog sits down or lies down (it barks from them at random).

| Set | Files | Size and offset (dx, dy) per frame |
|---|---|---|
| Walk, heading 0 (up-right) | 8500, 8501, 8502 | 17x18 (1,0) · 16x17 (0,1) · 15x16 (1,0) |
| Walk, heading 1 (right) | 8503, 8504, 8505 | 18x16 (2,1) · 21x16 (0,2) · 19x15 (1,1) |
| Walk, heading 2 (down-left) | 8506, 8507, 8508 | 16x16 (2,2) · 14x19 (2,0) · 12x17 (2,0) |
| Walk, heading 3 (left) | 8509, 8510, 8511 | 19x15 (1,1) · 20x16 (0,2) · 18x16 (1,1) |
| Resting, heading 4: **sitting up**, facing right, 2 frames (a small movement of the head or tail) | 8600, 8601 | 17x16 (2,1) · 19x16 (0,1) |
| Resting, heading 5: **lying or crouching**, facing right, 2 frames | 8602, 8603 | 18x15 (2,3) · 20x15 (0,3) |

**Alignment** (script-checked, same rule as E): `R = centroid + (dx, dy)` must satisfy **|R.x - 9.5| <= 1.5 and |R.y - 9.2| <= 2.0** for every frame (8500..8511, 8600..8603), and R differs by at most 2.0 px in x and 2.5 px in y
inside a set. The dog is never seen standing still: it is walking or resting; **a collar mark visible in profile** on headings 1, 3 and in the resting frames (heading 2 may hide it).
The dog is **the person's dog**: do not copy a known cartoon dog; choose coat and markings (for example a spotted or a tan dog).

## G. The cat (1300..1329) and the bird (1250, 1251)

### The cat: 1300..1305, 1310..1312, 1320..1329

All **masked**, 4 planes, black outline, **tight**. A house cat that **walks along the top of the back fence** (its feet at yard y about 36..38, x from 252 to 495), turns round at each end, sometimes stops and
**puffs itself up when the dog comes close**, and **pounces at the dog** when it is near. It is drawn at its position + the offsets below (the position of walking frames is the picture's **top-left**: no offset). Sprite sizes are fixed.

| Set | Files | What and the game's offset |
|---|---|---|
| **Walking right**: the game shows frame 0 only when it starts out or when it has finished being startled, and when it turns round to the right it jumps straight to frame 1; it then **loops 1, 2, 1, 2 ...** (so 1301 / 1302 are the two stride poses and 1300 a longer, stretched pose) | 1300, 1301, 1302 | 18x11 · 16x13 · 16x12, **no offset**, cat in profile, **head to the right** (a small collar mark of colour 7 on its neck) |
| **Walking left**: frame 3 only after a startle, a turn to the left jumps to frame 4; it then **loops 4, 5, 4, 5 ...** | 1303, 1304, 1305 | 18x11 · 16x13 · 16x12, the **mirror image** of 1300..1302 (collar on the left) |
| **Startled** (arched, bristling, mouth open; drawn when it stops): the game plays frame 10 once, then alternates **11, 12, 11, 12 ...** for about 30 ticks | 1310, 1311, 1312 | 39x34 (-10,-21) · 37x32 (-9,-19) · 39x31 (-10,-18): the cat stands **upright facing the viewer**, much bigger than when it walks |
| **Pounce** (10 frames 20..29, one per tick, then it goes back to walking) | 1320..1329 | 23x16 (0,0) · 26x26 (2,-16) · 34x33 (4,-23) · 33x34 (6,-24) · 34x33 (8,-22) · 26x26 (10,-18) · 23x16 (12,-10) · 16x23 (14,-10) · 23x16 (16,-4) · 16x23 (18,-2): the cat **leaps, grows towards the viewer** (frames 1321..1325 are big and seen head-on or from above, claws out) **and tumbles away, shrinking and turning** (1326..1329 small, rotating through horizontal and vertical poses) |

The walking cat's ground contact is its **bottom row**: bottom-centre at position + (9, 11 to 13). **Walking alignment** (script): the centroid of each of 1300..1305 within x 7.0..9.5 and y 5.0..7.0 of its own frame, and all three frames' **top rows are the back line (row 0 is opaque in every frame)**.
**Startled alignment**: the sprite's **bottom edge centre** (x = floor(width / 2), y = height) lands at position + (9, 13) in all three frames (this is how the offsets are built:
check that the cat's feet are in the bottom 3 rows and its horizontal centroid is within 2 px of x = floor(width / 2)).
**Pounce alignment**: the **bounding-box centre** of frame n (sprite centre + offset) follows the arc (11.5, 8) (15, -3) (21, -6.5) (22.5, -7) (25, -5.5) (23, -5) (23.5, -2) (22, 1.5) (27.5, 4) (26, 9.5) (relative to the position): the cat's body
(its mass) must stay within **3 px** of the frame's centre in both axes (script: centroid vs. box centre). 1320 and 1326 / 1328 and 1327 / 1329 are the small frames: draw the cat stretched out or tumbling, not facing you.
The cat is **not a copy of a known cartoon cat**: choose coat colours (a ginger or a grey tabby), your own face and body; the startled and pouncing frames are comic, bold and readable at their size.

### The bird: 1250, 1251

Both **masked**, black or dark outline, **tight**: a **small bird in flight, seen in profile, flying to the right** (beak on the right; a spot of colour 2 or 1 for the beak, a body of your choice), two wing positions drawn alternately every tick
(1250 wings up, 11 x 6, offset (-10, -3); 1251 wings down, 10 x 7, offset (-9, -1)). It crosses the yard from left to right 16 px per tick at a random height, may dive at the player's patch (eating
queens) and leaves up and to the right. **Alignment:** `R = centroid + (dx, dy)` of both frames within 2.0 px of (-4.7, 0.8).

## H. The spider (1000..1007, 1050..1053)

The big hunting spider of the surface map, seen from above; the player can be it. Two kinds of pictures, **both masked, 4 planes, colours 10 to 15 only** (browns, tans, greys, black: it must never melt
into the ground's greens, so no 7, 8, 9): **the body** (heads / thorax / abdomen, no legs) for 8 headings (1000..1007), and **the "beaten" frames** (1050..1053, the spider lying with its legs curling up, legs included).

### The bodies 1000..1007 and how the legs meet them

The game draws, for the spider at pixel position P (the **centre of its thorax**): the **body sprite with its top-left at P + (dx, dy)**; then **eight legs and two fangs as 1-px straight lines in colour 15 (the fangs in colour 1 while the player is the spider)** from the file
`spider/legs.json` of the previous batch (`spider_legs.md`). The legs' attach points and the fangs' base points are **fixed** relative to P, so **your body must be drawn around them**:

| Heading | File | Size | Thorax centre in the picture (= -(dx, dy)) | Right-hand leg attach points A1..A4 (front to back), picture pixels | Left-hand B1..B4 | Fang bases F1, F2 |
|---|---|---|---|---|---|---|
| 0 north | 1000 | 14 x 36 | (6, 10) | (11,4) (11,8) (11,12) (11,16) | (1,4) (1,8) (1,12) (1,16) | (10,0) (2,0) |
| 1 north-east | 1001 | 28 x 28 | (20, 8) | (28,7) (25,10) (22,13) (19,16) | (21,0) (18,3) (15,6) (12,9) | (30,5) (23,-2) |
| 2 east | 1002 | 36 x 14 | (25, 6) | (31,11) (27,11) (23,11) (19,11) | (31,1) (27,1) (23,1) (19,1) | (35,2) (35,10) |
| 3 south-east | 1003 | 28 x 28 | (20, 20) | (28,21) (25,18) (22,15) (19,12) | (21,28) (18,25) (15,22) (12,19) | (30,23) (23,30) |
| 4 south | 1004 | 14 x 36 | (6, 26) | (1,32) (1,28) (1,24) (1,20) | (11,32) (11,28) (11,24) (11,20) | (10,36) (2,36) |
| 5 south-west | 1005 | 28 x 28 | (8, 20) | (0,21) (3,18) (6,15) (9,12) | (7,28) (10,25) (13,22) (16,19) | (-2,23) (5,30) |
| 6 west | 1006 | 36 x 14 | (10, 6) | (4,1) (8,1) (12,1) (16,1) | (4,11) (8,11) (12,11) (16,11) | (0,2) (0,10) |
| 7 north-west | 1007 | 28 x 28 | (9, 9) | (1,8) (4,11) (7,14) (10,17) | (8,1) (11,4) (14,7) (17,10) | (-1,6) (6,-1) |

(Heading numbers are clockwise from the top of the screen; the spider **walks in the direction its head points**.) The table is computed from the legs file as committed with this spec
(north attach points `(5, -6) (5, -2) (5, 2) (5, 6)` and `(-5, ...)` from the thorax centre, north-east `(8,-1) (5,2) (2,5) (-1,8)` and their mirror `(1,-8) (-2,-5) (-5,-2) (-8,1)`, fang bases north `(4,-10) (-4,-10)`, north-east `(10,-3) (3,-10)`; the
other six headings turn or flip these: east = north turned 90 degrees clockwise (x, y) -> (-y, x); south = (-x, -y); west = (y, -x); south-east = north-east flipped top to bottom (x, -y); north-west left to right (-x, y); south-west both (-x, -y); the left-hand legs are the
mirror across the spider's own axis: north (-x, y), north-east (-y, -x)). **If `src/spider/legs.json` exists, your script recomputes the table from it by these rules and asserts it equals the table above (if it does not, it warns and uses the table); if it were changed later the table in the file is what the spec side re-derives.**

**Where things must be** (script-checked, for each of the 8 bodies):

1. **The thorax centre** is the pixel in the "Thorax centre" column (the game's position of the spider: it is the middle of the part that carries the legs). The head points in the heading and the **abdomen is behind**; the body is **36 px long** along the heading
   (head front **10 px ahead** of the centre in the north, east and west bodies, 9 px in the south body; the abdomen's rear **25 px behind** the centre, 26 in the south body; on the diagonals the body fills its 28 x 28 box along the diagonal),
   and 14 px across in the four axis bodies. **Each body is mirror-symmetric about its own axis** (north and south: the picture's vertical mid-line; east and west: the horizontal mid-line; the diagonals: the diagonal of the picture along the heading) **within 1 px**.
2. **Attach points A1..B4 must lie on the thorax's side edge**: each attach pixel is **opaque or within 1 px (Chebyshev distance) of an opaque pixel and at most 3 px inside the body** (so the legs visibly start at the body). The four attach points on a side go down the thorax from the front leg to the hind leg.
3. **The fang bases F1, F2** must lie **within 2 px of an opaque pixel for headings 0, 2, 4, 6 and within 3 px for 1, 3, 5, 7** (the bases are in front of the head or at its sides; a base can lie 1 to 3 px outside the picture on the diagonal headings: the head's front edge then touches the picture's edge there).
4. **Tight**: the opaque pixels touch all four edges of the frame. A spider has two parts: a **front part (head and thorax in one, the cephalothorax)** about **18 px long (from the head tip to about 8 px behind the centre), which carries all eight leg attachments and the eyes (a few small pixels; the jaws are the game's fangs, draw none)**,
   joined by a short narrow waist to the **big round abdomen** behind it (about 17 px long, from 8 to 25 px behind the centre). A 1-px black 15 outline all round the body.
5. The **eight bodies are one creature**: build one body model (front part, waist, abdomen with fixed lengths and widths) and render it for the 8 headings (turn the pixel art by 90 degrees for the 4 axis headings if your drawing allows it, but re-centre by the table; the south body's centre is one pixel off the pure turn).
6. **Palette**: colours 10 to 15 (and none of 7, 8, 9); a black 15 outline; a pale highlight on the abdomen (colour 11 or 12) at the top-left of the shape (light from the top-left in every heading: the highlight does **not** turn with the spider); body colours dark enough that the **black legs and yellow fangs** drawn over the head stay visible.

### The beaten frames 1050..1053

When the spider is beaten (by the human's foot, the mower, ants) it **lies still for up to about 500 ticks while the game picks a frame at random** (the **first frame shown is 1050**; **1051..1053** are shown at random during the first 100 ticks; afterwards only **1052 and 1053**, changing less and less often),
then it vanishes and drops food. **The legs are part of these pictures** (no lines are drawn over them) and the spider faces **up and to the left** (about north-west) in all four. Sizes and the spider centre (the pixel at which the game puts the spider's position: **the thorax centre**; the picture is drawn at position - that point):

| File | Size | Thorax centre in the picture | Pose |
|---|---|---|---|
| `1050.pix` | 67 x 67 | (27, 25) | **just beaten**: the legs still **sprawled wide** (reach to the frame's edges, 8 legs in an even star) |
| `1051.pix` | 62 x 53 | (21, 15) | legs **bent and twitching, still wide** |
| `1052.pix` | 41 x 37 | (14, 10) | legs **curled up over and under the body** (a tangle) |
| `1053.pix` | 41 x 36 | (14, 10) | a **different curl** of the same, as 1052 (the two alternate at the end) |

The four frames may follow each other **in any order** (random), so **no frame may assume a neighbour**; they all show the **same body at the same place and size** (the body of 1007 or yours in one fixed pose, tilted towards the upper left by up to 30 degrees), so the swap reads as the legs moving.
**Check**: the thorax centre pixel of each frame is opaque, and the body (opaque pixels of colours 11..14) is **identical in the four frames up to the legs** (script: draw the body once and the legs per frame).

## I. The map-window actors and the marker (1100..1107, 1200..1203, 1210, 1211, 1400)

### The small spider: 1100..1107, 12 x 12 each, masked

The spider as a **dot-sized picture on the Map window** (4 px per map cell): drawn with its top-left at the spider's cell x 4 - 3, so **the picture's centre is on the cell**. One picture per heading (as the bodies: 1100 + heading;
0 north, clockwise). A tiny spider with **eight legs spread round a round body**: the body faces the heading (the abdomen away from it). Colours **13, 14, 15 only** (dark greys and black; it lies over green, tan, grey and brown cells and over the red and black ants' dots).
**Tight** (the opaque pixels touch all four edges). Centroid within **1 px of (5.5, 5.5)** (the frame's centre). The even headings (north, east, south, west) have **84** transparent pixels each, the diagonals **91** (the legs differ a little in length): **use these counts
or within +-6**, so the cardinal and diagonal spiders have the same visual size. The 8 pictures should look like **one spider turned**, not 8 different drawings.

### The sneaker: 1200..1203, masked

The **person's foot stamping on the patch** as the Map window shows it (4 px per cell), **seen from above** as a **sneaker / trainer**, drawn with its top-left at the foot's footprint corner (cells x 4, y 4). The footprint of one stamp is **6 x 16 cells = 24 x 64 px** (heading 0 / 2) or **16 x 6 cells = 64 x 24 px** (heading 1 / 3): the sneaker fills that rectangle (the picture is 4 px longer than the footprint, at its bottom or right end).
Sizes: **1200: 23 x 68 (toe up), 1201: 68 x 23 (toe right), 1202: 23 x 68 (toe down), 1203: 68 x 23 (toe left)** (**toe in the direction the person goes**; 1202 / 1203 may be 1200 / 1201 turned 180 degrees). It must show: **a sole outline**, **laces**, a **toe cap**, a **heel opening**; black 15 outline; colours of your choice (not the original's sky blue); it lies over green, tan, brown and grey cells and must be visible on all (a light interior, dark outline). **Tight.**

### The mower of the Map window: 1210, 1211, opaque

**1210: 98 x 103 (travelling up or down), 1211: 103 x 98 (travelling left or right)**: the **lawn mower seen from above, drawn over the map while the person mows**; it **replaces the map cells it covers** (an opaque rectangle: **no transparent pixels**, so the picture is a mower on its own mat of ground: **the mower's deck and shell reach all four edges**; outside the machine, inside the rectangle, **flat colour of your choice** that shows the mower is "pressing on" the map).
The same picture is used for **both directions** of travel (up and down share 1210, left and right share 1211), so **draw it point-symmetric** (the same after a 180-degree turn, +-2 %) or at least with **nothing that points one way** (no arrow, no handle on one end only); **1211 equals 1210 turned by 90 degrees in at least 95 % of its pixels** (let the script make it so).
The game draws it with its top-left a few dozen cells ahead of the foot in the direction of travel; it kills nothing visible, so no detail inside is read by the game. Palette: a **red or orange deck with a dark engine cover** are fine, anything from the palette; **no tan background exactly equal to the ground tile** (it must read as a machine). Light from the top-left.

### The marker: 1400, 14 x 14, masked

The **round marker drawn on the Behavior / Caste Control triangles** (a separate sprite over the triangle's white interior and over its light-grey and white edges) showing the current mix: drawn with its **top-left at the point minus (7, 7)**, so **the picture's pixel (7, 7) is the point**. A round target: a **ring with a cross-hair or a dot** at (7, 7).
**The figure occupies the 13 x 13 square (1,1)-(13,13)** (its row 0 and column 0 are transparent; opaque pixels touch rows 1 and 13 and columns 1 and 13), roughly round (corners transparent), **centre pixel (7,7) opaque**. Colours: it must read on **white 0**, **light grey 12** and **dark grey 13/14** (the bevel around the triangle): use a dark outline ring (colour 14 or 15) and a saturated inner ring (colour 3, 4 or 6).
At least 40 transparent pixels in all.

## The script's checks

`make_yard_bitmaps.py` must **assert** (fail the build of the files) that:

1. every file has its **exact size**, only valid characters, and the right masking: the masked ones are exactly 1000..1007 (all), 1050..1053, 1100..1107, 1200..1203, 1250, 1251, 1260, 1300..1329, 1400, 7005, 7006, 7007, 7011, 8000..8023,
   8100..8111, 8500..8511, 8600..8603, 8800..8802 (these contain `.`); all others are opaque (no `.`): 1210, 1211, 7000, 7001, 7003, 7010, 7020, 7021, 7022, 8200, 8201, 8900..8903, 8905;
2. every masked sprite is **tight** (opaque pixels touch all four edges) except 7005, 7006, 7007, 7011, 1400 (13 x 13 at (1,1)), and 7006 / 7007 have exactly one opaque pixel, at column 1; 7005 has exactly one opaque pixel in each of rows 1..35, colour 7, column 5 at row 1 and column 1 at row 35;
3. the **lattice**: the pictures 7000, 7001, 7003 and the strips contain colour 9 on every lattice pixel that is visible (not covered by the house, the fence or furniture) and colour 8 inside the cells and **no other lawn pixel colours**; the lines
   continue across the seam (check the 7000 / 7003 columns at the seam against `lattice()`); the strips equal `lattice()` rendered over colour 13, the strips contain only 8, 9, 10, 13 and the house polyline of colour 10;
4. **7000 and 7001**: identical outside `HOUSE_MASK`, at least 55 % identical overall; the fixed rectangles of A / B are in place (the door niche and the two room rectangles, with their ring pixels equal in the patches);
   the frame pixels (leftmost column, top row and the 7003 rightmost column: colour 15; second row: colour 13);
5. **group B**: ring equality of 8900..8903 with 7000 and of 8200 / 8201 with 7001 as in B; 8905 all `f`;
6. **alignment** (E, F, G): for every frame `R = centroid + (dx, dy)` inside its box (E: x 6.0..12.0, y 13.0..18.0; F: x 8.0..11.0, y 7.2..11.2; bird: within 2.0 of (-4.7, 0.8)) and the within-set spreads; the mower's touching
   edges (8103..8105: width + dx = 19 and 8801's left column adjacent; 8109..8111: dx = 0 and 8802's right column adjacent); the cat's frame tests (walking: y centroid 5..7 and top row opaque; startled: bottom centre; pounce: centroid within 3 px of the box centre);
7. **the spider**: for each of the 8 bodies the thorax-centre pixel is opaque, the **attach points and fang bases** satisfy rules 2 and 3 of H against the table (recomputed from `legs.json` if present), the body is mirror-symmetric about the heading's axis (+-1 px; compare with
   the pixel-flipped picture and require at least 85 % of the opaque pixels to agree), the colours are within 10..15 (13..15 for 1100..1107); the beaten frames: body identical, centre pixel opaque; the small spiders' transparent counts within the stated ranges and their centroids;
8. **the toolbar**: every text rectangle of D (queens count, black colonies, red colonies) is flat white 0 across its whole rectangle; the radio buttons, the House / Strat / Graphic / PLACE buttons pass the **3 : 1 contrast test** in the picture as drawn and with every pixel XOR-ed with 15 (dominant light colour against dominant dark colour inside the rectangle); the
   crops 17006 / 17007 equal their windows of 7010 and contain no label pixel; the help overlay 7011 contains only colours 0, 14, 15 and `.`, and every callout box ends on row 46 and covers the stated x-range;
9. the **marker** 1400 has its centre pixel opaque, its opaque pixels fill exactly (1,1)-(13,13)'s bounding box and has at least 40 transparent pixels; the **mower** 1211 is 1210 turned by 90 degrees; the raindrop and the queens' dots are as in C;
10. **no picture contains the words** "SimAnt" or "Maxis" (the script has no such strings), and the For Sale sign has its two lines.

`python tools/clean_pack/build.py` then packs the files (`HCEGANT/2/<id>.bin`); the spec side runs the game with `-- --clean --pack=remake/build/dev_pack.zip`, checks the yard window in each view and each actor in place and compares the look with the originals for similarity before the pack ships.

## Previews

`preview.png`: (1) **the yard window assembled as the game shows it**: the Yard view (7000, 7003 at their screen places, the toolbar 7010 below, a few actors at sample positions: the person walking at (130,110) heading 1, the dog at (300,150), the cat on the fence at (300,25), the parked mower, the sign
at (170,186), 15 raindrops, a handful of queens), the House view (7001 with 8200 and 8201 on it), the **Strat view** and the **Graphic view** (the strips over colour 13, with sample coloured parallelograms and bars drawn by the rule of convention 4), and the toolbar with 7011 over it,
each at 2 x on a mid-grey background; (2) **every animation as a horizontal strip at 4 x**, in the game's cycle order (0, 1, 2, 1 ...), with the frames drawn on their offsets so the figure's alignment can be seen (a small cross at the actor's position); (3) **the spider composite**: the eight bodies, each with its legs and fangs
drawn **by your own code** as the game does it (legs.json's frame 0 for the right side, frame 4 for the left, the turn and flip rules above, 1-px lines in colour 15), on a brown-and-green background; (4) the beaten frames; (5) the Map-window actors on a grid of 4-px cells (the small spiders, the sneaker and the mower over a patch of green and tan);
(6) the toolbar buttons next to their **inverted** state and the doors patched into 7000.

## Consistency with the other batches

- **`ui_bitmaps.md` group J:** 17006 and 17007 are crops of your 7010 (above). 17005 / 17008 / 17009 / 17011 / 17012 are crops of 14000, not yours. The **Yard** picture of 14000's button and the **House** picture of 7010 are the same subject (house and lawn); the **Surface** button of 14000 and the **Patch** button of 7010 too.
- **The map sprites in `ui_bitmaps.md` (17000 the yellow ant, 17002 food, 17004 the rock, 5103 the ant) and `ant_sprites.md` / `map_tiles.md`:** the ants and the food are 16 x 16 tiles in the patch; the yard shows no ants. **Shared with them: the palette roles.** Black colony = black / dark grey, red colony = red 3, the player = yellow 1 (so the dog's yellow collar is the only other use of colour 1 in the yard's actors: keep it a collar, 1 to 3 px, and the fang colour 1 is the game's). The spider's body browns and greys must read against the tan and green ground tiles of `map_tiles.md`.
- **`spider_legs.md`:** the attach points and the fang bases above are its numbers; **if the legs are redone, the table in H is recomputed** (the script checks).
- **The person, dog, cat and sneaker / mower** are one world: the person's foot print (1200..1203) is a foot in the same sneakers as the walking figure's (the same colour scheme), the mower of 1210 / 1211 and of 8100.. / 8800.. is one machine in one colour scheme, and the 1260 sign's board matches the house's colours.
- **The scale of the yard window:** the person is about 30 px tall, the dog 16 px long, the cat 18 x 11 on the fence, the bird 11 x 6; the lattice cell is 28 x 10 px.

## Not found / open

- **8905** (19 x 35, all black in the original) is not referenced by any table or code I could trace; the spec makes it a plain black rectangle. **8200 / 8201** (the person in the chair and at the fridge) are drawn at fixed yard positions (45,166) and (207,47) by the person's script states 0x20 and 0x22; the original draws them only in the House view
  (`T:0C28` gating); the remake draws every figure in both views (a remake bug, spec side).
- **The door patches' position.** The code draws them at yard (172,73), i.e. picture pixel (174,73) of 7000; the original's door pictures match their background best at picture pixel (172,73): the two differ by 2 px (cause not found: the original's own registration, or the remake's yard origin). The spec follows the code (174); all positions are constants in your script (`DOOR_X`), so the spec side can shift them.
- **The brown line in the strips** (the house's footprint) is not read by the code; it is in the spec because the original has it.
- **The 1400 marker** in the original sits one pixel left of the true point (its figure is at x 0..12); the spec centres it on pixel (7, 7).
- **Which tick the animations change on** (the remake runs one frame per tick); the cat's startled frames alternate (11, 12) with a 30-tick timer, and the pounce lasts 10 ticks; the beaten spider's frame pick is random.
- **The yard's speech bubbles** (the person speaks in balloons, STR# 1200) are drawn by the balloon routine, not by these bitmaps.
- **The mower's two mowing sprites 8801 / 8802** are only shown on 6 of the 12 mowing frames (8103..8105, 8109..8111); on frames 8100..8102 and 8106..8108 the mower is baked into the person's picture and **no** parked mower is drawn.
- **Hit areas** of the toolbar are in the window layout, not in the picture; the picture's buttons must coincide with the rectangles given.
- **Where the patch-highlight XOR meets the actors:** the highlight covers actors on the player's patch; nothing to draw.
