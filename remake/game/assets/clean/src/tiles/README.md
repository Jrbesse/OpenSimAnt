# Yard tile sheet (clean pack)

`yard.pix` is the outdoor patches and the two nest cross-sections: 256 x 256 px, 16 x 16 tiles of
16 x 16 px. `make_yard.py` draws every tile procedurally from seeded random numbers and writes `yard.pix`,
`preview.png` (the sheet at 3x with a grid and row / column numbers) and `mockup.png` (a yard scene and a nest
cross-section put together from the tiles, at 2x). Run `~/work/simant-venv/bin/python make_yard.py` to rebuild all
three. The output is the same on every run. Both scripts in this folder need numpy and Pillow (from
`../requirements.txt`), which the system `python3` on the Hermes box does not have; the venv that has the pair is
`~/work/simant-venv`, so the runs there use its interpreter.

Made from the written spec `docs/clean_pack/map_tiles.md` (yard sheet) alone. See `../../PROVENANCE.md`.

## Palette and readability

Only the 16 standard Macintosh colours, with ordered (Bayer 4 x 4) or checker dithering for in-between
shades. Every dither pattern is laid out on the 4-pixel grid, so it lines up across tile edges.

| Thing | Colours | Why |
|---|---|---|
| Open ground | tan, with sparse brown and grey grains, a few lit grains | mid-toned, so yellow, black and red ants all show |
| Food | white crumb, orange crust, dark-grey outline | the brightest thing on the ground; it is what foragers look for |
| Rock (pebble, boulders) | medium grey, light-grey top-left, dark-grey bottom-right, black outline | reads as solid and impassable |
| Player wall | light-grey / white blocks in courses, mortar lines, black outline | regular, man-made; told apart from boulders by the block pattern |
| Nest entrance | black hole in a brown heap of soil pellets | dark centre with a clear ring |
| Ant-lion pit | sand cone that darkens to a black throat, light rim | a hazard that reads as a hole, not as an object |
| Water | blue with cyan ripple dashes and white glints | the only large blue area; ants drown in it |
| Plants | green / dark green (leaf, weed tuft, caterpillar) | |
| Scent view | tan to magenta, 15 Bayer steps (1/16 .. 15/16) | one hue that nothing else uses, so its strength reads as density |
| Tunnels | light grey (12) with medium-grey, white and tan specks (revised 2026-10-31; was dark grey) | clearly lighter than the brown packed soil, so the black colony's dark-grey ants with black outlines show; the tunnel-wall, stored-food, hole, pebble-plug and shaft tiles (0xA0..0xA4, 0xA8, 0xB0..0xBE, 0xC0, 0xC1) draw the same tunnel colour, and the script asserts 0x90..0x97 hold no dark pixel |
| Packed soil | brown with tan / grey / black grains | |

Light comes from the top-left everywhere: highlights on top-left edges, shading and a 1-px brown cast shadow
bottom-right.

## How the joins work

* **Ground 00..0F**: plain speckle with no structure crossing a tile edge. Each variant has at most one small
  feature (a tiny stone, a darker grain cluster, a crack, a root), kept 2 px inside the edges.
* **Composites** (nest mound 18..1F + 50, leaf 20..23, twig 24/25, dry grass 26/27, ant-lion slope 30..37 + pit 38):
  drawn as one 48 x 48 / 32 x 32 / 32 x 16 picture on a ground background, then cut into tiles. Nothing comes
  within 2 px of the outer border, so the outer edges are plain ground.
* **Boulders 54..5F and packed soil B0..BE / DF..ED**: each tile is drawn as the middle of a 3 x 3 neighbourhood
  of solid and open cells, shaded over the whole 48 x 48 area, and then cropped. Edges facing open cells sit flush
  with the cell border at both ends and dent inwards by 0..2 px in between. Convex corners are rounded, with a
  radius of 7 px for rock and 6 px for soil. At a tile seam a solid edge is always on the cell border, so any
  two pieces that are both solid at a seam join there, including the corner-next-to-inside case in the spec's
  fourth boulder shape.
* **Walls 60..67**: a 10-px band centred in the cell that runs to the edges on the connected sides. The block
  courses have a period of 8 px, so runs tile. Corner pieces have a square capstone.
* **Caterpillar 68..6F**: the body is 8 px wide at every seam and bulges in the middle of each cell, so
  segments pinch where they meet. 69 and 6A have different bulges, and 6A also has prolegs, so the body ripples
  as they alternate. The vertical and E-facing pieces are rotations or mirror images of the W-facing ones.
* **Grass strip AC..AF**: sky (cyan, with a white haze dither near the horizon), a grass line, then 5 rows of
  the same soil texture as B0..BE, so it sits on the soil below. AD has a cloud, AE a flower, AF a stone.
  A8 is a strip tile with the entrance shaft cut into it and dug soil heaped on both sides. C1 is A8 with a
  stone in the shaft.

## Choices where the spec left room

* **26/27** is a dry grass stem with a seed head at its right end.
* **Dead ants** are about 10 px long, smaller than the live ants (16 px), with their legs curled in.
* **Bugs 70..73**: a grey pill bug, a violet ground beetle, an orange beetle with black spots (orange, so it is
  not mistaken for a red ant) and a green shield bug. All face north.
* **Ant-lion frames 39..3F**: the sand trembles, sand is thrown up, the jaws break the surface, the jaws open
  wide, the jaws snap shut, the jaws sink while sand slides back, and the sand settles. Only the inside of the
  tile changes, so the frames join the slope tiles.
* **A4** (hole into the other nest) is a black hole in a rim of packed soil, with a dim red glow at the bottom
  that hints at the red colony.
* **A8 / C1** are drawn to sit in the top row in place of a grass-strip tile, with an open tunnel cell below.
* **Flooded soil DF..ED** has the same shapes as B0..BE. Water fills the open parts, and the soil has a few blue
  wet specks. ED (soil on all four sides) is wet soil. EE and EF are water with bubbles and with a drifting
  clump of soil.
* **Placeholders**: plain tan tiles with the slot number in large black hex digits.

The live ants in `mockup.png` are rough stand-ins, drawn only to check contrast. They are not part of the sheet.

# House tile sheet (clean pack)

`house.pix` is the patches inside the house (floors, counter, wall, sink unit, sockets): 256 x 256 px, 16 x 16
tiles of 16 x 16 px. `make_house.py` draws every tile procedurally (seeded, the same on every run) and writes
`house.pix`, `preview_house.png` (the sheet at 3x with a grid and row / column numbers) and `mockup_house.png`
(every multi-tile assembly of the spec built from the slot grids, enlarged: grout checks with openings, the
counter, raised / sunken frames, tap buttons, the sink unit, both socket plates, rooms with a left / right wall
and skirting, a rug with coin, paper clip and litter, a table-top with its legs, the dead ants and food piles,
the openings beside their base tiles, the shock frames). Run `~/work/simant-venv/bin/python make_house.py` to
rebuild all three; it asserts the checks below as it goes. The scent ramp 0xF1..0xFF is the yard sheet's, unchanged.

Made from the written spec `docs/clean_pack/map_tiles.md` (house sheet) alone. See `../../PROVENANCE.md`.

## Palette and readability

| Thing | Colours | Why |
|---|---|---|
| Floor 0 (kitchen floor) | tan, brown and light-grey flecks | warm and mid-toned; the checkerboard's darker check |
| Floor 1 (pale floor tile, the sink unit's top, socket plate face 0x63) | light grey, white flecks | clearly paler than floor 0; 0x63 is the same tile |
| Grout | dark grey, 2 px, along the top row / left column of a check | same colour and width on all six tiles |
| Carpet (floor 3) | mid grey, fine dark / light fibres (period 8) | neutral, so yellow, black and red ants and crumbs all show |
| Rug / table-top (floor 2) | the carpet's grey with a warm diagonal weave (a tan thread every 4th pixel) | looks like the carpet but the rug's edge shows |
| Wall | near white, faint light-grey dots | light; also the inside of a socket body |
| Skirting board | brown wood, vertical grain, two grooves; 0x7A has a black left edge against the wall | warm, unlike carpet and wall |
| Counter | glazed cyan with white glints, white-and-dark seams | the only large cyan area: a colour no floor uses |
| Basin | light grey (0xC1) and darker grey (0xC2) dither, same lattice | "a little darker than floor 1"; the frame around it shows the rim |
| Table legs 0xC0 | black and dark-grey wood-grain dither | solid and dark against floor 2 / 3 |
| Food | white morsel, orange crust, black outline, cast shadow | the only orange-and-white thing on all four floors; the yard sheet's look |
| Litter | pale / grey thin things, no outline, no orange | clearly not food |
| Coin | silver: reeded rim, star, black outline | decoration; not yellow, so not mistaken for the player's ant |
| Electric slots 0x76 / 0x77 / 0x78 | black opening, red ring, yellow-orange glowing contact bar | red + glow read as danger; 0x79 (lower end) and the hole 0x74 are dark with a grey ring and no glow: harmless |
| Shock frames 0x73 / 0x75 | the slot with a yellow / white / cyan star burst | vivid; the outermost pixel ring is the slot tile's |
| Nest openings 0x80..0x86, 0x8A | black round hole, dark-grey rim with a lit upper-left edge, four short cracks | the same hole on every base, so it is recognised on any floor |

Light comes from the top-left: lit bevels white, shaded bevels dark grey, every raised piece outlined black on the
outside.

## How the joins work

* **Floors** are built from an 8 x 8 cell repeated 2 x 2, so any tile edge continues exactly into the next tile.
  Floor 2 differs from floor 3 in about a third of its pixels (the weave); 0x04..0x07 are plain copies of floor 3.
* **Structured tiles** (grout, counter seams, bevelled frames, buttons, socket bodies) are built by one function
  that takes the face texture as a parameter. The script calls it twice with two different flat fills, and the
  pixels that did not change are the tile's "structure" mask; the join checks compare only structure, in the same
  colour, along the shared edge.
* **Grout**: a 2-px line in the top rows / left columns over the plain floor; 0x5C / 0x5D have both lines.
* **Counter**: seams are two pixels wide (dark, then white), in columns / rows 7 and 8 of 0x66, 0x68, 0x67, 0x69.
  0x69 has the vertical seam only down to the horizontal one. The front edge (0x68) is a seam, so a strip of
  counter face shows below it before floor 0 starts.
* **Skirting**: the edge columns of 0x7B are plain lines, symmetric (so it can sit next to the wall, carpet or
  another 0x7B); 0x7A is 0x7B with a black left column. The grain wraps top to bottom.
* **Frames** (0x50..0x5B): an outer black outline, then 2 px of bevel (white on the top / left, dark grey on the
  bottom / right), a mitred corner, and the face of floor 1 inside. The sunken frame reuses the straight edges
  (lit and shaded swap, which is right for a basin) and has four own corners: where the two walls' bands meet, the
  wall whose band is deeper at a pixel wins, so a lit and a dark wall meet on a diagonal. Each frame tile is a
  one-tile ring; the dark / lit band lies in the ring's inner 3 px.
* **Socket plates**: body tiles 0x6B..0x72 are the same bevel with rounded corners and a dark-grey outline, on a
  white (wall) face. The slot halves are cut from one capsule drawn across two tiles; the upright slot is that
  capsule turned 90 degrees (0x78 danger part: red ring and glow; 0x79 lower end: grey ring, no glow).
* **Taps**: a button / spout is a rounded raised piece with a metal-grey face (0x4E). 0x45 and 0x48 (the spout's
  lower corners) are rounder than 0x46 / 0x49 and sit on the basin floor: their corner background is the basin tone
  (0x45 on 0xC1, 0x48 on 0xC2, in the spout's shadow). 0x4C / 0x4D are 0x4E with a red "H" / blue "C" label.
* **Coin and paper clip** are drawn as one 48 x 48 picture on the rug and cut into tiles; nothing comes within 2
  px of the block's border, and the clip stays out of the top-left and bottom-right cells.
* **Openings** copy their base tile's outermost pixel ring (all four edges) and put the hole in the interior.

## Checks in the script (all asserted)

Size 256 x 256 and 16 x 16 tiles, opaque, every pixel a palette index; seamless self-tiling of the floors, wall,
counter face, basin, leg and the repeated edge tiles; every join of the spec's assemblies (grout checks, the
counter's seams and front edge, raised and sunken frames, both socket plates, the sink unit with its basins and
taps, the spout), including that the seams of 0x66 / 0x67 / 0x68 / 0x69 sit at the same pixels; skirting edge
columns; the opening tiles keep the outer edges of their base tiles (0x80..0x86 and 0x8A against 0x03); the shock
frames keep the outer edges of 0x76 / 0x78; 0x63 is floor 1; dead-ant and food tiles have the exact floor around
them and each food pile covers more than the one before; the 111 unused slots are numbered placeholders on a flat
mid-grey (floor 3's colour).

## Choices where the spec left room

* **Floor colours**: tan (0), light grey (1), grey carpet (3) with a warm-weave rug (2); an unusual choice for a
  carpet, made so that all three ant colours and the white-and-orange food read on it.
* **The sink unit** is laid out inside its 55 x 31 cells as: frame ring, then 5 rows of floor 1 for the taps, the
  basins side by side (left 29 x 22 at column 2, right 17 x 22 at column 35, both starting in row 6), buttons at
  columns 4..8 and 24..28, the spout at columns 14..18 (14 rows long, overhanging the basin by 9 rows) and its
  0xC2 shadow 2 cells to the right and 2 rows under it. The spec leaves these positions open.
* **The slot contact bar**, the red ring and the screw's slot are my own signs for "danger" and "screw".
* **Placeholders**: flat mid-grey tiles with the slot number in white hex digits.
