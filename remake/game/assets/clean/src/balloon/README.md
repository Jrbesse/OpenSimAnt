# Speech balloon

Made from the spec `docs/clean_pack/balloon.md` only. `make_balloon.py` writes `balloon.pix` (88 x 8: the 11
pieces of 8 x 8 side by side, in the spec's order) and `preview.png` (two sample balloons, 6 x 3 and 10 x 4 cells, the
tail on each, enlarged 6x over mid green). It needs Pillow (it always writes `preview.png` at the end of `main()`,
with no fallback), so run it with an interpreter that has the pair from `../requirements.txt`; on the Hermes box
that venv is `~/work/simant-venv`, so the run there is `~/work/simant-venv/bin/python make_balloon.py`.

- Only `0` (white inside), `f` (black outline) and `.` (transparent). A 1-pixel black outline, white fill, no shading.
- Corners: the top-left corner is drawn by hand (the outline runs along row 4 to the right and along column 1 down,
  turning through a rounded arc in the 4 x 4 corner of the piece). The other three corners are its mirror and flip
  images.
- Tail (`tail_left`, the second bottom cell): row 3 is open between columns 1 and 5. The white inside runs down into a
  triangle with a vertical left edge, a diagonal right edge running down and to the left, and a one-pixel white tip on
  row 7 (column 1). `tail_right` is its mirror image (spare; the game does not use it).
- The script asserts every join rule in the spec's "Joins build.py checks" section, plus the outline positions and the
  corner symmetry, before it writes the file.
