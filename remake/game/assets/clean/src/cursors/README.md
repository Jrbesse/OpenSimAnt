# Mouse cursors

Made from the spec `docs/clean_pack/cursors.md` only. Regenerate with `python make_cursors.py`
(`--preview` also writes `preview.png`, the two cursors over lawn green, soil brown, window grey and black).
Only palette indices 0 (white), f (black) and `.` (transparent) are used; 1-pixel lines, no anti-aliasing.

- `0.pix` (16 x 16): the pointer. Drawn by hand in the script: an arrow 10 x 15 pixels with its tip at (0, 0),
  a straight left edge, a 45-degree right edge, a flat shoulder at row 10 and a tail that steps down and right one
  pixel per row. White fill with a black outline, so the black edge shows on light ground and the white body on dark.
- `1.pix` (24 x 32): the busy cursor, an hourglass computed in the script. Two white caps with black frames
  (rows 1-3 and 28-30); between them a mirror-symmetric glass whose half-width follows
  `1 + 8 sin(d * pi / 2)` (d = distance from the neck), outlined in black and filled white; a thin layer of black
  sand draining from the top bulb, a 2-pixel stream broken once (so the grains read as falling) and a mound in the
  bottom bulb. On black ground the caps and the white glass carry the shape.
