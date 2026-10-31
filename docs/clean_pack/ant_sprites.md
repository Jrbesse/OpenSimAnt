# Spec: ant sprites (the surface sheet and the nest sheet)

> **Status (2026-10-31):** complete, ready for a maker. Written from the simulation's code, the renderer and a
> census of the sprite ids that occur in 40 long games.

Output folder: `remake/game/assets/clean/src/sprites/`. Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an
entry). Files to make, all with the format described below:

| File | What |
|---|---|
| `surface.pix` | the ants seen from above, for the yard and house patches: 256 x 128 pixels |
| `nest.pix` | the ants seen in the nests' cross-section: 256 x 128 pixels |
| `surface_recolour.pix`, `nest_recolour.pix` | one recolour mask per sheet, same size: which pixels change colour for the black and red colonies |
| `make_sprites.py` | the script that writes all four files (and the preview), so they can be regenerated |
| `README.md` | a short note: the design, the colours used for what, how to rebuild |
| `preview.png` | (recommended) both sheets enlarged, each shown three times, drawn for the yellow, black and red colonies by the rules below, over a sample ground colour (tan for the surface, near-black for the nest) |

## Format

Each sheet is **16 sprites across and 8 down: sprite n (n = 0..127) sits at column n % 16, row n // 16, and is 16 x 16
pixels** (so a sheet is 256 wide x 128 high). In `.pix` (README.md: one line per pixel row, one character per
pixel, `#` lines are comments): `.` is transparent (the ground shows through), `0`-`9` / `a`-`f` is a palette index
(README.md: 0 white .. 15 black). Every row has the same length, 128 rows.

The recolour files use the same layout: `1` where the pixel is recoloured, `0` or `.` where it is not. **Never a `1` on
a transparent pixel** (the build rejects it). Sprite n of the recolour sheet belongs to sprite n of the picture.

## What the sprites are

Every creature on the two map views is one sprite drawn over the 16 x 16 ground tile of the cell it stands in
(one ant per cell, at most; a queen takes two cells). The surface view looks straight down at the ground, the nests
are a cross-section (a vertical slice of soil with tunnels and chambers cut into it). A window shows about 22 x 21
cells, so ants are small: **each sprite is one pose, there are no walking frames**; the game moves an ant by changing
its cell and its heading, and an ant that turns simply switches to the sprite for the new heading. An adult ant fills
most of the tile (about 11 to 16 pixels long, legs and feelers may touch the tile's edge; neighbouring ants may touch).

Both sheets use **the same ids for the same things**; only the point of view differs:

- **Surface sheet**: ants seen from above, legs spreading to both sides. Drawn over the yard ground (sandy
  tan / brown, mid-toned) and over house floors (kitchen tiles, rugs, wood: lighter and more varied).
- **Nest sheet**: ants seen from the side, as in a glass ant farm. Facing east or west: a profile (legs down towards
  the floor of the tunnel). Facing north or south: the ant is climbing or descending a vertical shaft, drawn as a
  view along or across the body (your choice, but the head end must be recognisable). The four diagonal headings:
  an ant on a slope, legs towards the lower side. The ground behind them is a **dark tunnel or chamber** (the open
  space of the nest), and in places the brown packed soil: see "Readability".

The look is yours: invent a simple, clear ant in the same 16-colour style as the rest of the pack (see
`cursors.md` / `map_tiles.md` for the outline and light conventions: 1-pixel black outline, light from the top-left).
Mirroring (west from east, south from north) and rotating by script is fine, if the result is clean and the recolour
mask follows (it is a mask on pixels, so it must be transformed together with the picture).

## Headings (the ids' low 3 bits)

The sprite for an ant is `caste * 8 + heading`. The heading is the direction the ant's **head** points on the screen
(north is up, the top of the map). Clockwise from north:

| heading (id & 7) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| the head points | N (up) | NE (up-right) | E (right) | SE (down-right) | S (down) | SW (down-left) | W (left) | NW (up-left) |
| next cell is at (dx, dy) | (0, -1) | (+1, -1) | (+1, 0) | (+1, +1) | (0, +1) | (-1, +1) | (-1, 0) | (-1, -1) |

An ant carrying something holds it **at the head end** (in front of it, between the jaws).

## The sheet layout: eight rows

Each row of the sheet is two groups of 8 headings (or the brood stages), left half = ids 0..7 of the row, right
half = ids 8..15:

| Row | Left half (columns 0..7) | Right half (columns 8..15) |
|---|---|---|
| 0 (0x00..0x0F) | 0x00 unused, then the 7 brood stages 0x01..0x07 | a worker carrying a baby: 0x08..0x0F |
| 1 (0x10..0x1F) | a plain worker: 0x10..0x17 | a worker carrying food: 0x18..0x1F |
| 2 (0x20..0x2F) | a male: 0x20..0x27 | a worker carrying a pebble: 0x28..0x2F |
| 3 (0x30..0x3F) | a soldier: 0x30..0x37 | a soldier carrying food: 0x38..0x3F |
| 4 (0x40..0x4F) | a young queen: 0x40..0x47 | a soldier carrying a pebble: 0x48..0x4F |
| 5 (0x50..0x5F) | unused | unused |
| 6 (0x60..0x6F) | a queen, front part: 0x60..0x67 | a queen, rear part: 0x68..0x6F |
| 7 (0x70..0x7F) | a fight cloud, 8 variants: 0x70..0x77 | unused: 0x78..0x7F |

## The slot table (the same for both sheets)

"Recoloured" says what the recolour mask should cover (see the next section). Numbers of occurrences come from a
census of 40 simulated games; "rare" means seen but infrequent.

| Slots | What | Notes |
|---|---|---|
| 0x00 | unused: the empty cell is never drawn | placeholder |
| 0x01..0x07 | **brood**, 7 growth stages of one baby ant: 0x01 a tiny newly laid egg, 0x02 a larger egg, 0x03 / 0x04 / 0x05 a grub (larva) in its first, second and third growth step (each clearly bigger and plumper than the last), 0x06 a pupa (a wrapped capsule), 0x07 a pupa about to hatch (the same, with the adult's shape showing through or the wrapping splitting) | one sprite per stage, no heading (the baby just lies there). Mostly pale (white / light grey, so it shows on dark tunnels and on tan ground); only a **few pixels** (2 to 20) are recoloured, as a coloured band or spot, so you can see whose brood it is. In play they appear in the nests only (black brood in the black nest, red in the red nest); **in the surface sheet they are used only for the player's own growth animation** (below) but must still be drawn, the same stages. Sizes grow from about 4 x 3 pixels (0x01) to about 8 x 13 (0x06, 0x07) |
| 0x08..0x0F | **a worker carrying a baby** (an egg, grub or pupa; one picture for any stage), 8 headings | a plain worker with a small pale bundle held at the head end. The bundle is not recoloured. Appears when workers move brood around the nest and when raiders steal brood (a red ant on the surface or in the black nest carrying it home); not common |
| 0x10..0x17 | **a worker, empty-handed**, 8 headings | by far the most common sprite in the game (also the player's usual form): spend the most care here. The body (head, thorax, abdomen) is recoloured; legs, feelers and outline are not |
| 0x18..0x1F | **a worker carrying food**: 0x10..0x17 plus a morsel at the head end | very common on the surface (foragers) |
| 0x20..0x27 | **a male** (the winged breeder, a drone), 8 headings | slimmer than a worker, with a pair of wings (translucent look: light grey / white, not recoloured); wings folded back or half open. Rare; appears when a colony breeds, and the player can be one |
| 0x28..0x2F | **a worker carrying a pebble or clump of soil** (the player's ant can carry and drop pebbles; workers carry dug-out soil) | a grey round stone at the head end, not recoloured |
| 0x30..0x37 | **a soldier**, 8 headings | a worker's build with a clearly bigger head and open jaws; reads as "the fighter" at a glance (a larger, heavier silhouette) |
| 0x38..0x3F | **a soldier carrying food** | as 0x18 on a soldier |
| 0x40..0x47 | **a young queen** (a new queen, the breeder that founds colonies), 8 headings | a big ant: the largest single-cell ant, a fat abdomen and a pair of wings like the male's. Seen when a colony breeds, and the player can be one |
| 0x48..0x4F | **a soldier carrying a pebble** | as 0x28 on a soldier |
| 0x50..0x5F | unused (two castes the game never makes) | numbered placeholders |
| 0x60..0x67 | **the queen's front part**: her head and thorax, 8 headings | the queen takes **two cells** (see "The queen" below). Not common (one per nest) but always on screen when the player looks at the nest |
| 0x68..0x6F | **the queen's rear part**: her huge abdomen, 8 headings | the biggest, most recoloured sprite: the abdomen is mostly body colour; id = front part's id + 8 |
| 0x70..0x77 | **a fight cloud**, 8 variants | two ants fighting: a tangle of limbs and jaws in a small dust cloud, hiding which ant is which. See "Fights" below. Occurs on both views |
| 0x78..0x7F | unused | numbered placeholders |

In use: 0x01..0x4F (79 sprites) and 0x60..0x77 (24) = 103 per sheet; unused: 0x00, 0x50..0x5F, 0x78..0x7F (25).

### Castes in plain words (what the player can tell apart)

Workers do all the chores; soldiers (bigger heads) guard and fight; males and young queens are the winged breeders;
the queen lays eggs. The castes must be tellable apart **by silhouette alone, at 16 x 16**: worker < male (wings) <
soldier (head) < young queen (wings + size).

## The queen: two cells that must join

A queen occupies two neighbouring cells. Her **front part is drawn in the cell where the ant is**, and her **rear
part in the cell behind her** (the opposite direction to her heading: the rear part's id is the front part's id + 8,
the same heading). For each heading, the pair on the map looks like this (rows top to bottom; `F` = front part
0x60 + heading, `R` = rear part 0x68 + heading):

| heading | the two cells |
|---|---|
| 0 N | `F` above `R`: `F / R` |
| 1 NE | `. F / R .` (the rear is down-left of the front) |
| 2 E | `R F` (the rear is on the left) |
| 3 SE | `R . / . F` |
| 4 S | `R / F` |
| 5 SW | `. R / F .` |
| 6 W | `F R` |
| 7 NW | `F . / . R` |

The two sprites must **join into one continuous body** with no gap and no step:

- Facing N, E, S or W (the cells share an edge): both sprites have opaque pixels at the middle of the shared edge,
  at the same 2 to 4 positions along it (the front part's rear tip touches the rear part's front end).
- Diagonal (the cells share only a corner): both have opaque pixels in the two corner pixels that meet, so the body
  reads as passing across the corner.
- Both are drawn in the same colouring, so the queen is one colour on screen. The rear part is about 11 to 14 pixels
  long and the whole queen about 20 to 26 pixels, noticeably the largest ant on the map.
- In the nest sheet, the E and W queens lie along a tunnel floor in profile, the join on the body line; the rear part
  may curve down or up a little as long as the join rows match.
- Check the joins in the script (one assert per heading, as the tile pieces are checked) and show all 8 pairs side by
  side in `preview.png`.

The player's own queen uses exactly the same two sprites.

## Fights (0x70..0x77)

When two enemy ants meet, both vanish into one **fight cloud**; after a short while the winner
walks out and the loser's corpse is left. Each game tick the cloud's sprite is chosen **at random among the 8 variants
(the "heading" is just a random jitter)**, so the cloud flickers and churns: the 8 variants must look like the same
scuffle seen at slightly different moments (a few pixels' difference, e.g. different limbs flying out), none of them
reads as a single ant, and none should be so different that the flicker is distracting. They are in play on both
sheets (surface fights, fights in the nests); the player's own fights (a fast animation, 6 frames at random) use all
8 variants as well.

The cloud is coloured by the **winner** of the fight (so one look says whose ant will come out): the black colony's
cloud shows grey (dark) ant parts, the red colony's red ones, the player's yellow. Recolour a small share of the
cloud (about 8 to 16 pixels, as body parts showing through); the rest (black limbs, light grey / white dust, and a few
red "bite" sparks) is not recoloured and so is the same in every fight. Sparks must not be yellow (yellow means the
player).

## Brood and the player's cocoon (an animation in order)

Brood stages 0x01..0x07 are the stages of one baby; the game never skips back. When the **player's ant dies and the
player is given another ant** (the colony's queen's cell, in the nest view), the game plays a short "hatching" scene:
the yellow ant is shown through the seven brood sprites **in order, 0x01 to 0x07, one after the other (a growth
sequence, in the yellow colours, i.e. unrecoloured)**, then as an adult. A yellow queen who founds a new nest plays
the same sequence on her chamber cell. So the seven stages must read as one baby growing into a pupa, and the
recoloured marks must be yellow (1) as drawn.

## Recolouring (the three colonies)

The game has three ant colours: the player's **yellow** ant, the **black** colony and the **red** colony. **You draw
every sprite once, as the yellow ant.** The game draws other colonies' ants by changing the colour of the pixels
listed in the recolour mask, using the palette index:

| Who | What the game does to a recoloured pixel's index c | Pixels not in the mask |
|---|---|---|
| the player (yellow) | nothing: the sprite as drawn | as drawn |
| black colony | c becomes c XOR 15 (flip all four bits) | as drawn |
| red colony | c becomes c XOR 2 (flip bit 1 only) | as drawn |

Which colony an ant belongs to is not part of the sprite: the same ids are used by all three colonies. Any sprite can
be drawn in any of the three, including the brood, the fight clouds and the queen's parts, and no id is exempt: **the
mask alone decides what changes**. Unused slots: an empty mask.

### What each yellow-ant colour becomes

| Index (colour) | in the black colony (c XOR 15) | in the red colony (c XOR 2) | Use it on recoloured pixels? |
|---|---|---|---|
| 0 white | 15 black | 2 orange | no (the black ant's highlight would turn black); leave white pixels unrecoloured |
| **1 yellow** | **14 dark grey** | **3 red** | **yes: the one body colour.** Also what makes the player's ant stand out (the only yellow thing on the map) |
| 2 orange | 13 medium grey | 0 white | only for a few shade / glint pixels on a body (medium grey is a good shade on a dark grey body; the red colony gets white glints, which is acceptable for 1 to 4 pixels but not for areas) |
| 3 red | 12 light grey | 1 yellow | **never** (the red colony would turn yellow, the player's colour). Unrecoloured 3 is fine (it stays red in every colony) |
| 4 magenta | 11 tan | 6 blue | no |
| 5 purple | 10 brown | 7 cyan | no |
| 6 blue | 9 dark green | 4 magenta | no |
| 7 cyan | 8 green | 5 purple | no |
| 8 green | 7 cyan | 10 brown | no (green is for unrecoloured leaves / food) |
| 9 dark green | 6 blue | 11 tan | no |
| 10 brown | 5 purple | 8 green | no |
| 11 tan | 4 magenta | 9 dark green | no |
| 12 light grey | 3 red | 14 dark grey | **never** (a black ant would go red) |
| 13 medium grey | 2 orange | 15 black | **never** |
| 14 dark grey | 1 yellow | 12 light grey | **never** (a black ant would go yellow) |
| 15 black | 0 white | 13 medium grey | **never**: outlines stay black in every colony |

In short: **recolour only pixels of index 1 (the body), and, sparingly, index 2 (a shade on the body).** Everything
else (outline 15, legs, feelers, eyes, wings, carried food, carried pebbles, brood bodies, dust, sparks) is left out
of the mask and keeps its colour in every colony. Two more rules follow:

- **Never leave a 1 (yellow) outside the mask**, in any sprite: an unrecoloured yellow pixel would show on black and
  red ants and be mistaken for the player. (Yellow on the player's ant must be exactly the pixels that the other
  colonies change.)
- Mask pixels only on index 1 or 2 pixels, and every recoloured pixel's neighbours in the body should be recoloured
  too, so that the body changes colour as one shape (no speckle): the build only checks the mask against
  transparency, the script should assert this rule.

Result on screen: yellow body = the player; **dark grey body (14) with black outline = the black colony; red body (3)
with black outline = the red colony**. Make the three *read differently by lightness as well as hue*: yellow is the
lightest, dark grey the darkest, red in between, so they are told apart even with poor colour vision.

## Readability (the checklist)

1. **The three colonies must be told apart at a glance** at 16 x 16 on every ground: yellow body / dark grey body /
   red body, with the same black outline. Make the coloured body area large enough: about half or more of an
   ant's opaque pixels, not a few spots.
2. **The player's ant must stand out**: it is the only yellow ant, the body area is large and bright and the outline
   crisp; do not use yellow anywhere else in a sprite (outside the mask).
3. **Ground.** Surface: sandy tan and brown ground and light house floors; the 1-pixel black outline carries the
   ant on every ground. **Nest: the open tunnels are a light-to-mid tone** (revised 2026-10-31, map_tiles.md 0x90:
   the first clean sheet's dark grey tunnels hid the black colony, whose body is dark grey 14), so the nest sheet
   uses **the same black outline, legs and feelers as the surface sheet**: a black colony ant is then a dark grey
   body with a black outline on a light tunnel. Test each recolouring in `preview.png` on the tunnel colour of the
   clean yard sheet (tile 0x90 of `src/tiles/yard.pix`) and on the brown (10) soil colour.
4. Carried things must be readable and not recoloured: **food** a small bright morsel, white (0) with an orange (2)
   edge (the same look as the pack's food crumb tile, so players see it is the same food); **a pebble** a small grey
   stone (13 with 12 on top-left and 14 bottom-right, like the pack's pebble tile); **a baby** a pale (0 / 12)
   bundle, clearly different from the food morsel (shape: a longer capsule, not round). The carried thing sits at
   the head end and is about 4 x 4 pixels.
5. Head end identifiable in every sprite: heading must be unambiguous, since ants meet, fight and turn (a bigger
   head, mandibles, feelers pointing forward).
6. Light from the top-left (highlights top-left, a shade bottom-right) as in the tile sheets; but keep the ant's
   body colours within indices 1 (and 2) so the mask works.
7. No anti-aliasing, only the 16 palette indices (and `.`). Every used sprite has at least 20 opaque pixels, and no
   pixel is left floating (every opaque pixel is connected to the rest, apart from feelers, a pebble or flying dust).
8. The 8 headings of one caste must look like the same ant: the same size, the same body proportions, the same
   colours. In particular the four diagonal headings must not be visibly smaller or bigger than the straight ones.

## Unused slots

Both sheets: 0x00, 0x50..0x5F, 0x78..0x7F (25). Fill each with an **opaque** 16 x 16 placeholder (not transparent,
so a wrong id shows up on the map): light grey (12) with the slot number as two hexadecimal digits in black (15),
3 x 5 pixel digits, and an empty recolour mask. Draw the number (e.g. `50`) with your own small digit font.

## The script's checks (and the build)

`make_sprites.py` should fail (assert) if: a sheet is not 256 x 128; a recolour mask is not 256 x 128 or has anything
other than `1`, `0`, `.`; a `1` is on a transparent pixel or on a pixel other than index 1 or 2; an unrecoloured
pixel has index 1; a used slot has fewer than 20 opaque pixels; a queen's front and rear parts do not join (the
rules above, per heading); an unused slot is not the opaque placeholder with an empty mask. Then
`python tools/clean_pack/build.py` (spec side) packs the sheets into the game's format; the spec side checks the
result in the game (`--clean` with a dev pack) and compares the look for similarity before the pack ships.

## What is not in these sheets

The spider, the caterpillar, the beetles, the ant lion's pit, the human, the dog, the cat, the bird and the mower:
those are other specs (tiles or separate bitmaps). The ants' corpses are ground tiles (yard sheet 0x10..0x17), not
sprites here. The overview map (the small Map window) uses flat colours, one per cell, and no sprite.
