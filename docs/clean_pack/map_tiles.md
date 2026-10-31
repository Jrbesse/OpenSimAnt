# Spec: map tiles (the yard sheet is ready; the house sheet is still a draft)

> **Status (2026-10-30):** the yard sheet's table is complete (from the code and a census of 400 games); a maker can
> make `yard.pix`. The house sheet's table is still to write: don't hand `house.pix` to a maker yet.

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

## The house sheet (`house.pix`): to write

The house patches (kitchen floors, rugs, counters, a stove, sinks with taps, a power outlet that electrocutes ants,
small objects) use their own sheet with the same rules: 0x00..0x0F floors, 0x18..0x27 food crumbs (4 kinds x 4
amounts), 0x50.. fittings, 0xF1..0xFF the same scent ramp. The slot-by-slot table is still to write from
`Terrain.HousePatch` and the census (128 slots in use).
