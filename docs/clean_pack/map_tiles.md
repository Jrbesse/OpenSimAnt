# Spec: map tiles (both sheets are ready)

> **Status (2026-10-31):** both tables are complete, each written from the simulation's code and a census of the tiles
> that occur in 400 long games. The yard sheet's (2026-10-30) has been made (`yard.pix`); the house sheet's
> (2026-10-31) is ready: a maker can make `house.pix`.

Output folder: `remake/game/assets/clean/src/tiles/`: `yard.pix` and `house.pix`, each a 256 x 256 pixel sheet of
16 x 16 tiles, tile number n at column n % 16, row n / 16 (n in hexadecimal: the first digit is the row, the second
the column). Provenance: `remake/game/assets/clean/PROVENANCE.md`.

## What the tiles are

The game shows an ant colony's patch of ground from above (the surface, 128 x 64 cells) and its two nests in
cross-section (64 x 64 cells each), every cell a 16 x 16 tile; a window shows about 22 x 21 cells. The yard sheet
draws the outdoor patches and the nests; the house sheet draws the patches inside the house (floors, furniture).
Ants, the spider and other creatures are drawn over the tiles separately (other specs), so tiles show only the
ground and fixed things.

## Rules for every tile

- Exactly 16 x 16 pixels, opaque (no `.`): every pixel a palette index (see README: 0 white .. 15 black).
- Ground tiles must tile seamlessly with each other in any combination, and should look like one continuous surface
  when the 16 variants are mixed at random.
- Readability first: at a glance a player must tell open ground, food, rock (impassable), walls, nest openings,
  water and the hazards apart, also in the 4-pixel-per-cell overview map, which uses its own flat colours.
- Ants are small and yellow / black / red: keep the ground mid-toned (browns, tans, greys) so all three show.
- Unused slots: fill with a plain tile of the ground's main colour and the slot's number in a contrasting colour,
  so a mistake shows.

## The yard sheet (`yard.pix`), slot by slot

Written 2026-10-30 from the simulation's code and a census of the tiles that occur in 400 long games. "Passable":
ants walk over tiles up to 0x50; higher ones block them. Directions: N is up (towards row 0 of the map).

**Surface (the patch seen from above):**

| Slots | What | Notes |
|---|---|---|
| 0x00..0x0F | open ground: 16 variants of bare sandy soil | picked at random per cell, so they must mix seamlessly; the most common tiles by far. Small differences only (a pebble, a darker grain) |
| 0x10..0x13 | a dead black ant lying on the ground, 4 variants | ants carry the remains away; must read as small, dark, still |
| 0x14..0x17 | a dead red ant, 4 variants | as above, red |
| 0x18..0x1F | the mound of dug-out soil around a nest entrance, one tile per side of the hole: 0x18 NW, 0x19 N, 0x1A NE, 0x1B W, 0x1C E, 0x1D SW, 0x1E S, 0x1F SE | with 0x50 in the middle they form a 3 x 3 crater: `18 19 1A / 1B 50 1C / 1D 1E 1F` |
| 0x20..0x23 | a large fallen leaf covering 2 x 2 cells: 0x20 top-left, 0x21 top-right, 0x22 bottom-left, 0x23 bottom-right | passable ground cover; the four join into one leaf |
| 0x24, 0x25 | a twig lying across 2 cells: left half, right half | passable |
| 0x26, 0x27 | a second kind of 2-cell debris (a blade of dry grass, a seed husk ...): left, right | passable |
| 0x28 | a small tuft of weed | scattered, passable |
| 0x30..0x37 | the sand slope around an ant-lion pit, one tile per side: 0x30 NW, 0x31 N, 0x32 NE, 0x33 W, 0x34 E, 0x35 SW, 0x36 S, 0x37 SE | with the pit in the middle: `30 31 32 / 33 pit 34 / 35 36 37`, a funnel sloping down to the centre |
| 0x38..0x3F | the ant-lion pit itself, 8 animation frames | 0x38 the pit at rest (a cone of sand with a dark centre); the others its animation when it catches an ant (sand flying, jaws showing), played in order |
| 0x48..0x4B | a food crumb, 4 amounts: 0x48 the last small bit .. 0x4B a whole crumb | each bite moves the tile one step down; after 0x48 it becomes ground. Must stand out clearly (the goal of foraging) |
| 0x50 | a nest entrance: a dark hole in the ground | the middle of the mound 0x18..0x1F; passable (ants go in) |
| 0x51 | a pebble: a small stone filling the cell | impassable, scattered |
| 0x54..0x5F | pieces of large rocks (boulders 3 x 3 to 5 x 5 cells), assembled from: 0x5B top-left corner, 0x54 top edge, 0x55 top-right corner, 0x5A left edge, 0x5C inside, 0x56 right edge, 0x59 bottom-left corner, 0x58 bottom edge, 0x57 bottom-right corner, and three inside (concave) corners, rock on all four sides with only one diagonal neighbour outside: 0x5D (outside at the bottom-left), 0x5E (outside at the top-right), 0x5F (outside at the bottom-right) | impassable; the pieces must join seamlessly in any of these shapes (rows top to bottom): `. 5B 54 55 . / 5B 5C 5C 56 . / 5A 5C 5C 5E 55 / 59 5D 5C 5C 56 / . 59 58 58 57`, `5B 54 55 / 5A 5C 56 / 59 58 57`, `5B 55 . / 59 5E 55 / . 59 57`, `5B 54 54 54 55 / 59 5D 5C 5F 57 / . 5A 5C 56 . / 5B 5C 5F 57 . / 59 58 57 . .` |
| 0x60..0x67 | a barrier the player builds with the map tools (a low wall), drawn by its neighbours: 0x60 a horizontal run (or a lone piece), 0x61 a vertical run, 0x62 the top end of a vertical run, 0x64 its bottom end, 0x65 the left end of a horizontal run, 0x63 its right end, 0x66 a corner joining up and right, 0x67 a corner joining left and down | impassable; pieces must join |
| 0x68..0x6F | a caterpillar crossing the patch, cell by cell: heads 0x68 facing W, 0x6B facing E, 0x6C facing N, 0x6F facing S; body segments 0x69 and 0x6A (horizontal, two alternating shapes so it ripples), 0x6D and 0x6E (vertical, likewise) | about 3-4 cells long; impassable while it is there |
| 0x70..0x73 | four kinds of small beetle / pill bug wandering the patch | each fits in one cell; they move cell to cell |
| 0x74..0x77 | a raindrop hitting the ground, then the wet spot drying: 4 stages, 0x74 the splash .. 0x77 nearly dry | then the cell becomes ground again |
| 0xF1..0xFF | the scent overlay: 15 steps from faint (0xF1) to strong (0xFF) | shown instead of the ground when the player turns on a scent view; a smooth ramp of one hue family so strength reads at a glance |

**Nests (the side view underground).** A nest cell's tile is its soil value - 0x70, so the nests use these slots:

| Slots | What | Notes |
|---|---|---|
| 0x90..0x97 | an open tunnel or chamber: 8 variants of dug-out space | picked at random; dark, so ants show up |
| 0xA0..0xA3 | food stored in a chamber, 4 amounts (0xA0 the least) | |
| 0xA4 | a hole leading into the other colony's nest | |
| 0xA8 | the entrance shaft at the top of the nest (where the tunnel meets the surface) | |
| 0xAC..0xAF | the strip of ground surface along the top of the cross-section: grass and the sky above it, 4 variants | |
| 0xB0..0xBE | packed soil next to a tunnel, by which sides have more soil: tile 0xAF + mask, mask = 1 soil above + 2 soil to the right + 4 soil below + 8 soil to the left (0xB0 = soil above only .. 0xBE = soil on all four sides; 15 combinations) | the tunnel's walls: the open sides show the tunnel's edge |
| 0xC0 | a pebble plugging a tunnel (the player's ant can carry pebbles and drop them) | blocks the tunnel |
| 0xC1 | a pebble plugging the entrance shaft at the top of the nest (dropped on the entrance from above) | blocks the entrance |
| 0xDE..0xEF | flooded tunnels after heavy rain: 0xDE flooded open space, 0xDF..0xED flooded soil edges with the same mask scheme as 0xB0..0xBE (0xDE + mask), 0xEE..0xEF more flooded variants | water must read clearly (ants drown) |

**Unused** (fill with a numbered placeholder): 0x29..0x2F, 0x40..0x47, 0x4C..0x4F, 0x52, 0x53, 0x78..0x8F,
0x98..0x9F, 0xA5..0xA7, 0xA9..0xAB, 0xBF, 0xC2..0xDD, 0xF0.

## The house sheet (`house.pix`), slot by slot

Written 2026-10-31 from the simulation's code and the same census (400 long games): 128 slots occur in play; two more
(the shock frames) show only in an animation and fifteen (the scent ramp) only as an overlay, so 145 slots are
described and 111 are unused. The sheet draws only the 38 patches inside the house, seen from above like the yard.
**The nests are always drawn from the yard sheet**, so the house sheet has no nest tiles. "Passable": ants walk over
every tile up to 0x90, so in practice only 0xC0, 0xC1 and 0xC2 block them. Walls, the counter, the sink's rim and
the sockets are therefore surfaces ants walk on: draw them as surfaces (a wall seen from the front or from above is
fine), never as barriers. N is up (towards row 0 of the map).

**The house, at an ant's size.** Each patch is 128 x 64 cells. Everyday human things are huge: a coin, a paper
clip, a wall socket, a sink with taps. A patch is one of these (patch counts in brackets; every floor tile is a
single plain tile, no random variants):

- **Carpeted room, wall on the left** (11): columns 0..20 a plain wall (0x64), column 21 `7A`, column 22 `7B` (a
  skirting board), then floor 3 (carpet) to the right edge, a wall socket plate 13 x 9 cells on the wall at columns
  2..14, rows 25..33. Six of the eleven also have, on the carpet, a **rug** (a rectangle of floor 2, 47 cells wide, with a
  coin or a paper clip or both lying on it) or a **table-top** (a rectangle of floor 2 from 31 x 31 to 51 x 39 cells
  with a solid 4 x 4 block in each corner, like the legs of a table seen from above, litter on it, sometimes a coin
  or a clip).
- **Carpeted room, wall on the right** (12): floor 3 from column 0 to 103, then `7B 7B` (columns 104, 105), then the
  wall (0x64) from column 106 to 127; a wall socket plate 13 x 9 at columns 113..125, rows 35..43.
- **Carpet only** (1): floor 3 everywhere. **Bare floor only** (2): floor 0 everywhere.
- **Tiled floor** (8): a checkerboard of floor 1 and floor 0, each check 16 x 16 cells with a grout line along its top
  and left edges.
- **Counter** (4): rows 0..23 are the counter, a tiled wall or worktop; rows 24..63 are floor 0 (the floor below it).
  Two wall socket plates 9 x 13 cells stand on the counter at columns 36..44 and 84..92, rows 2..14. In one of these
  four patches a **sink unit** (55 x 31 cells, at columns 37..91, rows 26..56) stands on the floor below the counter.

Slot grids below are rows top to bottom, tile numbers in hexadecimal, `.` = no tile drawn (what is already there shows).

**Floors, and what lies on them:**

| Slots | What | Notes |
|---|---|---|
| 0x00 | floor 0: a hard floor tile (a kitchen floor), also one colour of the checkerboard | very common; must tile seamlessly with itself; the ground under corpses 0x08..0x0B, food 0x18..0x1B and the entrance 0x86 |
| 0x01 | floor 1: a second hard floor tile, pale, the other colour of the checkerboard; it also fills the top of the sink unit | must contrast clearly with floor 0; seamless with itself; ground under 0x0C..0x0F and 0x1C..0x1F. Keep it near-identical to 0x63 (the socket plate's face): the frame tiles 0x50..0x5B sit against both |
| 0x02 | floor 2: a rug or table-top laid on the carpet | ground under 0x10..0x13 and 0x20..0x23, and under the coin, the clip and the litter. Looks like floor 3 but a little different (a shade, a weave) so the rug's edge shows; it must stay close to 0x03 because one entrance tile (0x8A) serves both; seamless with itself and with 0x03 |
| 0x03 | floor 3: the carpet | by far the most common tile (over a third of all cells in play); calm and fine-grained so ants and crumbs stand out; seamless with itself and 0x02; ground under 0x14..0x17, 0x24..0x27 and the specks 0x3E, 0x3F |
| 0x04..0x07 | never placed by the house's code; they appear only in rare stray frames (a few hundred cells in all 400 games, probably ground values left from a yard patch for a moment while the game switches into the house) | draw each as a plain copy of floor 3, so nothing flashes |
| 0x08..0x17 | a dead ant lying on a floor, 4 floors x 4 tiles: on floor 0 `08 09 0A 0B`, floor 1 `0C 0D 0E 0F`, floor 2 `10 11 12 13`, floor 3 `14 15 16 17`; in each group the first two are a black ant (two poses), the last two a red ant (two poses) | ants carry the remains away: the tile then turns back into plain floor, so its background must be exactly that floor. Small, dark or red, still. Passable |
| 0x18..0x27 | a food crumb pile on a floor, 4 floors x 4 amounts: floor 0 `18 19 1A 1B`, floor 1 `1C 1D 1E 1F`, floor 2 `20 21 22 23`, floor 3 `24 25 26 27`; in each group the first is the smallest (one morsel) .. the last the biggest (four) | the food drop makes the smallest (and a drop on an existing pile makes it one step bigger, up to the biggest); each bite moves it one step down, and after the smallest it becomes plain floor again, so the background must be exactly that floor. Must stand out clearly on all four floors (a dark outline, a colour no floor uses) and must not look like the litter below. Passable |
| 0x28..0x30 | a large coin lying flat, 3 x 3 cells: `28 29 2A / 2B 2C 2D / 2E 2F 30` | passable decoration (not food); a round object about 40 pixels across, centred in the block; the rest of the 9 tiles is floor 2, so it sits on a rug |
| 0x31..0x37 | a thin object (a paper clip, a bent wire) lying diagonally from the bottom-left cell to the top-right cell of 3 x 3 cells: `. 31 32 / 33 34 35 / 36 37 .` | the two `.` cells are not drawn: floor 2 shows there. The other pieces have floor 2 as their background |
| 0x38..0x3C | five kinds of small litter on a rug or table-top (threads, a hair, crumbs, a paper scrap) | one tile each, scattered about one cell in twenty over the table-top; background floor 2; passable; thin, pale or grey: not food |
| 0x3E, 0x3F | two kinds of specks (lint, dust) on the carpet | about one cell in 200 of the carpet; background floor 3; not food |

**The tiled floor (grout):** each 16 x 16 check has a grout line along its top edge and its left edge. Tiles: `5D` the
top-left corner of a check of floor 0, `60` its top edge (repeated 15 times), `5E` its left edge (15 times), the rest
`00`; for a check of floor 1: `5C`, `61` (top edge), `5F` (left edge), the rest `01`. The checks alternate between
the two floors like a chessboard, so a floor-0 check is next to floor-1 checks on all four sides. Four checks meeting
(each shown by its first two rows and columns; a floor-1 check top-left):

```
5C 61 61 ...   5D 60 60 ...
5F 01 01 ...   5E 00 00 ...
...            ...
5D 60 60 ...   5C 61 61 ...
5E 00 00 ...   5F 01 01 ...
```

| Slots | What | Notes |
|---|---|---|
| 0x5C, 0x5D | the corner of a check where the two grout lines meet: 0x5C on a floor-1 check, 0x5D on a floor-0 check | passable. The line is the same colour and width in all six tiles (suggested: 2 pixels, along the tile's top row / left column); the rest of the tile is that floor |
| 0x5E, 0x5F | the left edge of a check, with the vertical grout line: 0x5E on floor 0, 0x5F on floor 1 | repeats vertically; seamless |
| 0x60, 0x61 | the top edge of a check, with the horizontal grout line: 0x60 on floor 0, 0x61 on floor 1 | repeats horizontally; seamless |

**The counter (a tiled wall or worktop):** blocks of plain tile face split by thin seams. Horizontal seams run along
rows 0, 8 and 16 and along the front edge (row 23), vertical seams every 8th column. One block of the pattern
(8 columns, then it repeats; row 0 at the top):

```
67 68 68 68 68 68 68 68       row 0: a horizontal seam
66 62 62 62 62 62 62 62       rows 1..7: plain face, a vertical seam on the first column
...
67 68 68 68 68 68 68 68       rows 8 and 16: the same as row 0
...
69 68 68 68 68 68 68 68       row 23, the front edge: the last row; floor 0 starts below it
```

| Slots | What | Notes |
|---|---|---|
| 0x62 | the counter's face: a plain glazed tile surface | seamless in all directions; give it a strong colour of its own, unlike any floor. Passable (ants walk on it) |
| 0x66 | a vertical seam running the full height of the tile (suggested: centred) | seamless vertically |
| 0x68 | a horizontal seam running the full width (suggested: centred); also the counter's front edge | seamless horizontally |
| 0x67, 0x69 | the crossing of a vertical and a horizontal seam: 0x67 a full cross (inside the counter), 0x69 where the vertical seam meets the front edge | the seams of 0x66, 0x68, 0x67, 0x69 must run at the same pixel positions so the lines join |

**The wall and the skirting board** (rooms with a wall):

| Slots | What | Notes |
|---|---|---|
| 0x64 | the wall: a plain, light surface | seamless in all directions; also the plain parts inside a socket (see below). Passable |
| 0x7A, 0x7B | a skirting board (a strip of wood) at the foot of the wall, running the full height of the patch: in left-wall rooms, from left to right: wall `64`, `7A` (touches the wall), `7B`, carpet `03`; in right-wall rooms: carpet `03`, `7B`, `7B`, wall `64` | seamless vertically; 0x7B has neutral, symmetric edges (it sits next to the wall on one side and the carpet on the other, in both kinds of room); 0x7A is 0x7B with its left edge finished against the wall. Passable |

**Raised and sunken frames** (the rim of the sink unit, the rim of its basins, the plate of a wall socket):

| Slots | What | Notes |
|---|---|---|
| 0x50..0x55, 0x5A, 0x5B | a raised bevelled frame, lit from the top-left: 0x53 top-left corner, 0x54 top edge, 0x55 top-right corner, 0x5A left edge, 0x5B right edge, 0x50 bottom-left corner, 0x51 bottom edge, 0x52 bottom-right corner | passable; the lit edges (0x54, 0x5A) are light, the shaded ones (0x51, 0x5B) dark. Each tile carries its own dark outline on the outer side, so it sits on any neighbour (floor 0, the wall, the counter); its inner side continues a light face (floor 1 inside the sink unit, 0x63 inside a socket plate) |
| 0x56..0x59 | the corners of a **sunken** frame (a basin's rim): 0x56 top-left, 0x58 top-right, 0x57 bottom-left, 0x59 bottom-right | the straight edges of a sunken frame reuse the tiles above with the light and the shade swapped: top edge 0x51, left edge 0x5B, right edge 0x5A, bottom edge 0x54 (so 0x51 and 0x54 serve as the top of one kind and the bottom of the other; same for 0x5A, 0x5B): the lighting must stay consistent in both uses. Passable |
| 0x63 | the face of a socket plate: a smooth light surface | seamless; near-identical to floor 1 |

The raised frame (corners and edges only; `..` is the face inside):
`53 54 54 54 55 / 5A .. .. .. 5B / 5A .. .. .. 5B / 50 51 51 51 52`.
The sunken frame: `56 51 51 51 58 / 5B .. .. .. 5A / 5B .. .. .. 5A / 57 54 54 54 59`.

**Wall sockets (the electrical hazard).** A socket plate is a raised frame of 0x63 with one or two sockets and a
screw. Two kinds of plate:

*Wide plate* (13 x 9 cells, on the wall of the rooms; two sockets side by side, a screw between them):

```
53 54 54 54 54 54 54 54 54 54 54 54 55
5A 63 63 63 63 63 63 63 63 63 63 63 5B
5A 63 6B 6C 6C 6D 63 6B 6C 6C 6D 63 5B
5A 63 71 76 77 72 63 71 76 77 72 63 5B
5A 63 71 64 64 72 65 71 64 64 72 63 5B
5A 63 71 76 77 72 63 71 76 77 72 63 5B
5A 63 6E 6F 6F 70 63 6E 6F 6F 70 63 5B
5A 63 63 63 63 63 63 63 63 63 63 63 5B
50 51 51 51 51 51 51 51 51 51 51 51 52
```

*Tall plate* (9 x 13 cells, on the counter; two sockets one above the other, a screw between them):

```
53 54 54 54 54 54 54 54 55
5A 63 63 63 63 63 63 63 5B
5A 63 6B 6C 6C 6C 6D 63 5B
5A 63 71 78 64 78 72 63 5B
5A 63 71 79 74 79 72 63 5B
5A 63 6E 6F 6F 6F 70 63 5B
5A 63 63 63 65 63 63 63 5B
5A 63 6B 6C 6C 6C 6D 63 5B
5A 63 71 78 64 78 72 63 5B
5A 63 71 79 74 79 72 63 5B
5A 63 6E 6F 6F 6F 70 63 5B
5A 63 63 63 63 63 63 63 5B
50 51 51 51 51 51 51 51 52
```

| Slots | What | Notes |
|---|---|---|
| 0x6B, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x71, 0x72 | the raised rounded body of a socket: 0x6B top-left corner, 0x6C top edge, 0x6D top-right corner, 0x6E bottom-left corner, 0x6F bottom edge, 0x70 bottom-right corner, 0x71 left edge, 0x72 right edge | passable; the same lighting as the raised frame (lit top-left); the body is a different tone from the 0x63 face so it reads as a block |
| 0x64 | (inside a socket) the plain middle of the body | as in the wall table above |
| 0x76, 0x77 | the two halves of a horizontal slot opening of the wide plate's sockets: 0x76 left half, 0x77 right half | passable, **dangerous**: the player's ant that steps on 0x76 is electrocuted (see 0x73); the opening is dark and must read as a slot, and as a danger |
| 0x78, 0x79 | an upright slot opening of the tall plate's sockets: 0x78 its upper part, 0x79 its lower end | the upper part (0x78) is **dangerous** like 0x76 (the player's ant dies on it, see 0x75); the lower end (0x79) is harmless; both dark |
| 0x74 | a small round hole in the middle of a tall-plate socket | passable; harmless |
| 0x65 | a screw head (round, with a slot) on the plate between the two sockets | passable; harmless |
| 0x73, 0x75 | the shock frames: 0x73 is 0x76 with a bright electric spark over it, 0x75 is 0x78 with a spark | shown only for about 32 frames while the player's ant is being electrocuted: the tile flickers at random between 0x76 and 0x73 (or 0x78 and 0x75) while the ant jerks about, then the ant dies and the tile returns to normal. Each must keep the outer edges of the tile it replaces (so it still joins its neighbours) and have a vivid burst in the middle; they must not appear anywhere else |

Only the player's ant is hurt by the dangerous tiles; as far as the code shows, other ants walk over the sockets
unharmed.

**The sink unit** (one patch): a raised frame (0x53..0x5B pieces, 55 x 31 cells) enclosing floor 1, and inside it two
sunken basins side by side, the left one 29 x 22 cells and the right one 17 x 22, with the taps on the rim of the left
basin. Each basin is a sunken frame whose inside is 0xC2 (a shaded strip: the first 2 rows and the first column
under the rim) and 0xC1 (the basin floor). Rows of a basin, top to bottom:

```
56 51 51 .. 51 58
5B C2 C2 .. C2 5A      (twice: the shade the rim casts)
5B C2 C1 .. C1 5A      (the rest: 18 rows)
57 54 54 .. 54 59
```

The taps stand across the top of the left basin: a round-cornered button on each side and a spout between them; the
spout overhangs the basin and casts a shadow of 0xC2 on the basin floor (2 cells wide to its right, 3 cells wide
under its foot, 2 cells deep).

| Slots | What | Notes |
|---|---|---|
| 0xC1 | the basin floor: a flat, cool metal or porcelain tone, a little darker than floor 1 | **impassable** (ants do not enter the basin); seamless with 0xC2 and itself |
| 0xC2 | the same floor in shade (the shadow of the rim and of the spout): a darker version of 0xC1 | **impassable**; seamless with 0xC1 |
| 0x40, 0x41, 0x42, 0x43, 0x44, 0x46, 0x47, 0x49, 0x4E | a tap button 5 x 5 cells (a rounded square seen from above): `40 41 41 41 42 / 43 4E 4E 4E 44 / 43 4E 4C 4E 44 / 43 4E 4E 4E 44 / 46 47 47 47 49` (0x40 top-left corner, 0x41 top edge, 0x42 top-right, 0x43 left edge, 0x44 right edge, 0x46 bottom-left, 0x47 bottom edge, 0x49 bottom-right, 0x4E the flat face) | passable; lit from the top-left like the raised frames |
| 0x4C, 0x4D | the middle of the left button (0x4C, hot) and of the right button (0x4D, cold): a small label square with a letter, H on 0x4C, C on 0x4D | the two must differ at a glance (suggested: red for hot, blue for cold) |
| 0x45, 0x48 | the lower corners of the spout: 0x45 bottom-left, 0x48 bottom-right | like 0x46 / 0x49 but the end of a longer body; the spout is 5 x 14 cells: `40 41 41 41 42 / (43 4E 4E 4E 44) x 12 / 45 47 47 47 48`; passable |

**Nest openings.** An ant colony's entrance is a dark opening that takes the place of a floor or grout tile; it is the
surface end of the nest tunnel and the cell the player's ant walks onto to go underground. Each opening tile is the
tile it replaces with a dark hole or crack in it, so it joins its neighbours exactly like that tile:

| Slots | What | Notes |
|---|---|---|
| 0x80 | an opening in the left-edge grout line of a floor-0 check (replaces 0x5E) | passable; must read as a hole at a glance, as the yard's 0x50 does |
| 0x81 | the same on a floor-1 check (replaces 0x5F) | |
| 0x82 | an opening in the top-edge grout line of a floor-0 check (replaces 0x60) | |
| 0x83 | the same on a floor-1 check (replaces 0x61) | |
| 0x84 | an opening in a horizontal counter seam (replaces 0x68) | |
| 0x85 | an opening in a vertical counter seam (replaces 0x66) | |
| 0x86 | an opening in bare floor 0 (replaces 0x00) | |
| 0x8A | an opening in the carpet (replaces 0x02 or 0x03) | one tile for both floors, so keep floors 2 and 3 close |

There is no opening on floor 1, on a counter face or on a seam crossing.

**The scent overlay.**

| Slots | What | Notes |
|---|---|---|
| 0xF1..0xFF | the scent overlay: 15 steps from faint (0xF1) to strong (0xFF) | the same ramp as the yard sheet's 0xF1..0xFF (use the same look), shown instead of the floor when the player turns on a scent view; a smooth ramp of one hue family so strength reads at a glance. It must not be mistaken for a floor |

**The table legs.**

| Slots | What | Notes |
|---|---|---|
| 0xC0 | a solid, dark block: one of the 16 cells of a 4 x 4 square at each corner of a table-top (floor 2), like a table leg seen from directly above | **impassable**; must tile seamlessly with itself so the 4 x 4 square reads as one block, and sit well against floor 2 and floor 3 |

**Readability.** At a glance a player must tell: food piles (on all four floors), nest openings, the electric slots
(0x76, 0x78 and their frames), the blocked basin and table legs (0xC0..0xC2), and dead ants; the rugs, skirting and
walls are only scenery.

**Unused** (fill with a numbered placeholder on a plain tile of floor 3's colour): 0x3D, 0x4A, 0x4B, 0x4F, 0x6A,
0x7C..0x7F, 0x87..0x89, 0x8B..0xBF, 0xC3..0xF0. (The range 0x90..0xF0 is where the yard sheet keeps the nest tiles;
this sheet uses only 0xC0..0xC2 and the scent ramp 0xF1..0xFF of it.)
