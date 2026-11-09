# Ant sprites

Made from the spec `docs/clean_pack/ant_sprites.md` only. Regenerate everything (both sheets, both recolour masks and
`preview.png`, which needs Pillow) with `python make_sprites.py`. The checks of the spec's "The script's checks" are
asserts in the script (`--dev` only reports a failed check and carries on, for drawing).

## Files

- `surface.pix`, `nest.pix`: 256 x 128, 16 x 8 sprites of 16 x 16; sprite n at column n % 16, row n // 16.
  103 sprites per sheet are used (0x01..0x4F, 0x60..0x77); the other 25 are opaque light grey placeholders with the
  slot number in 3 x 5 black digits.
- `surface_recolour.pix`, `nest_recolour.pix`: `1` = the pixel changes colour for the black (index xor 15) and red
  (xor 2) colonies, `0` = it does not, `.` = transparent in the picture.
- `preview.png`: both sheets for the yellow, black and red colonies (tan ground / the yard sheet's light tunnel tiles), the queen's two cells
  joined for all 8 headings, and a ground test (surface on tan, brown, white, light grey; nest on yard tunnel tiles 0x90, 0x93 and brown 10).

## The design

- **Surface ants** (seen from above), one pose each: head, thorax, abdomen, three pairs of black legs, feelers (soldier:
  open jaws) and two black eyes. Templates face N and NE; E, S, W are exact 90 degree rotations, SE, SW, NW rotations of
  the NE template, so the eight headings are the same ant. The NE templates are the N ant turned 45 degrees (part masks
  re-sampled, outline and legs redrawn), so the diagonals are not smaller. Worker 13 x 8, soldier larger head and jaws,
  male slim with white wings, young queen the largest single-cell ant with wings.
- **Nest ants** (cross-section): profile facing east (three lumps, eye, feeler, three legs down). North = the profile turned
  to climb a shaft (legs towards the wall on the right), south = its mirror; the diagonals are the profile on a slope
  (NE up, SE down, legs towards the lower side), west / NW / SW are mirrors. **The outline, legs and feelers are black
  (15), as on the surface** (revised 2026-10-31): the yard sheet's open tunnels are now light grey, so a black colony ant
  (dark grey body, black outline) shows on them; `preview.png` tests the nest sheet on yard tiles 0x90 / 0x93 and brown soil.
- **Colours**: body = 1 (yellow), recoloured (the only yellow in the sheets); abdomen shade = 2 (3 to 4 pixels on the
  lower-right rim, placed after the rotation so the light is always top-left; 6 on the queen's rear part); outline, legs,
  feelers, eyes 15, wings 0 with a 12 edge, carried food 0 with a 2 rim, pebble 13 (12 top-left, 14 bottom-right),
  baby 0 core with a 12 rim (a longer capsule), brood 0 / 12 with a 13 outline and a 1-coloured band (2 to 8 recoloured
  pixels), fight cloud 12 / 0 / 13 dust, black limbs, red (3) bite sparks and 11 recoloured body pixels.
- **Carried things** (4 x 4) are stamped at the head end after the rotation; the ant drops its feelers then.
- **Queen**: front and rear are cut from one body whose waist (2 pixels wide, black on both sides) sits exactly on the cut,
  so the cells join on the edge (N, E, S, W) or at the corner pixels (diagonals); checked per heading in the script.
- **Fight cloud**: 8 variants of one scuffle: the cloud and five limbs stay, two limbs, the sparks and the flying specks change.
- A few things the script asserts beyond the spec: no pixel of index 1 outside the mask, mask only on 1 / 2, no isolated
  mask pixel, at most 4 shade pixels (queen rear 8), the 8 headings of a caste within 20 % of each other in size, body at
  least 38 % of an ant's pixels (28 % for the winged males and young queens, whose wings are not body), and **no
  detached limb**: every black pixel of an ant or brood sprite joins its body (the queen's front / rear halves and the
  fight cloud are the only sprites allowed to stand apart, by design).

## Rebuild

`python make_sprites.py`, then `python tools/clean_pack/build.py` (spec side).
