# Spec: map tiles (DRAFT: not ready for a maker)

> **Status:** the general part below is written; the per-tile table (what each of the 256 slots of each sheet is
> for) is still to write from the simulation's code (SIM_NOTES: terrain generator, house patches, nest dirt, map
> tools, ant lions, flooding, the yard layer's foot stamps). Don't hand this to a maker until it is complete.

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

## Per-tile table (to write)

| Slots | Sheet | What | Notes |
|---|---|---|---|
| 0x00..0x0F | yard | open ground, 16 variants (the generator picks one at random per cell) | |
| ... | | | |
| 0xF1..0xFF | both | the scent overlay ramp: 15 steps from faint to strong, shown in place of the ground when a scent view is on | |
