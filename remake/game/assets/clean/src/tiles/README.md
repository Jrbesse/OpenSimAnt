# Yard tile sheet (clean pack)

`yard.pix` is the outdoor patches and the two nest cross-sections: 256 x 256 px, 16 x 16 tiles of
16 x 16 px. `make_yard.py` draws every tile procedurally from seeded random numbers and writes `yard.pix`,
`preview.png` (the sheet at 3x with a grid and row / column numbers) and `mockup.png` (a yard scene and a nest
cross-section put together from the tiles, at 2x). Run `python make_yard.py` to rebuild all three. The output
is the same on every run.

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
| Tunnels | dark grey with black and brown specks | dark, but not black, so black ants still show |
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
