# Spec: the speech balloon pieces

Output folder: `remake/game/assets/clean/src/balloon/`. Provenance file: `remake/game/assets/clean/PROVENANCE.md`.
Format: `.pix` (see `docs/clean_pack/README.md` "Source formats"). Palette: only index 0 (white), index 15 (black) and
transparent.

## What the balloon is

A comic-style speech balloon that appears next to an ant (or the spider) in the map window and holds a short remark,
one to eleven lines of text. The game does not scale a picture: it **builds each balloon from 11 small pieces of
8 x 8 pixels**, tiling the edge pieces, so the balloon fits its text. Outline: 1 pixel, black. Inside: white, with the
text in black (the game's normal text face, font 2: [fonts.md](fonts.md)). Everything outside the outline is
transparent (the map shows through). It is drawn over any background (green lawn, brown soil, grey floors, black), so the
white inside plus the black outline must read clearly on all of them. Corners are rounded (radius about 4 pixels).

## The file

One file: `balloon.pix`, **88 x 8**: the 11 pieces side by side, piece n in columns 8n .. 8n+7, in this order:

| n | Piece | Where the game puts it |
|---|---|---|
| 0 | `top_left` | the balloon's top-left corner (cell column 0, row 0) |
| 1 | `top_right` | the top-right corner |
| 2 | `top` | the top edge, repeated across every cell between the two top corners |
| 3 | `right` | the right edge, repeated down, in the last cell column |
| 4 | `left` | the left edge, repeated down, in cell column 0 |
| 5 | `bottom_left` | the bottom-left corner |
| 6 | `bottom_right` | the bottom-right corner |
| 7 | `bottom` | the bottom edge, repeated across every cell between the bottom corners (except where a tail is) |
| 8 | `inside` | plain white, tiled over the whole inside |
| 9 | `tail_right` | a tail replacing one `bottom` cell near the right end, pointing down (spare: the game does not use it yet) |
| 10 | `tail_left` | the tail replacing the second bottom cell (the one next to `bottom_left`): **the tail the game uses** |

Characters: `0` white (inside), `f` black (outline), `.` transparent. Nothing else. (Pieces are encoded as a white plane
and an opaque plane per row; a white pixel is always opaque.)

## How the balloon is put together

Width = (widest line of text in pixels + 23) rounded down to a multiple of 8, so a whole number of 8-pixel cells; at
least 3 cells. Height = number of lines x the text face's line height + 16, then 1 less (2 less for a single line).

- Top row of cells: `top_left`, then `top` for every cell in between, then `top_right`.
- Middle rows (from 8 pixels down while there is room, one cell row after another): `left`, `inside` for every cell
  in between, `right`. The pieces `left`, `right`, `inside` are tiled **downwards at any offset**, so every one of
  their 8 rows must be identical.
- Bottom row of cells, placed lines x line height + 6 pixels down, **over** the last middle row (the two overlap at
  an arbitrary pixel offset): `bottom_left`, then `tail_left` in the second cell, then `bottom` for the rest, then
  `bottom_right`. Their top rows must continue the `left` / `inside` / `right` rows above them.
- `top`, `bottom` and `inside` are tiled **across**, so every one of their 8 columns must be identical.
- Text: line i is drawn in black from x = 8 (plus 0..3 pixels to put each line at a byte boundary) and y = 6 + i x line
  height, over the inside. The inside must be white at least from x = 2 to 5 pixels before the right edge and from
  y = 5 down to 3 rows under the last line, so the text is always clear of the outline.

## Where the outline runs (inside each 8 x 8 piece)

These are fixed by the text placement above; the pieces must put their lines here:

- Top pieces: rows 0..3 transparent, the outline on **row 4**, white inside on rows 5..7.
- Left pieces: transparent column 0, the outline on **column 1**, white on columns 2..7.
- Right pieces: white on columns 0..5, the outline on **column 6**, column 7 transparent.
- Bottom pieces: white on rows 0..2, the outline on **row 3**, rows 4..7 transparent.
- Corners: the same lines, turning through a rounded quarter circle that fits the 8 x 8 piece (the outline of the
  top-left corner leaves the piece along row 4 to the right and along column 1 downwards; the other three likewise).
- `inside`: all white, all opaque.
- Tails: a tail is a bottom cell whose outline row (row 3) is **open** between its two ends: the white inside runs on
  down into a small triangle that narrows to a one-pixel tip on the **last row (row 7)**, the tip near the left end of
  `tail_left` (within columns 0..3), its left edge (nearly) vertical along the piece's left edge and its right edge a
  diagonal running down and to the left. Rows 0..2 are plain inside (as `bottom`). Both ends of row 3 (column 0 and
  columns 6..7 for `tail_left`) are the bottom outline, so the outline joins the neighbours. `tail_right` is the exact
  mirror image of `tail_left`. In the game the balloon sits so that the tip lands just above and to the right of the
  ant it belongs to (about 13 pixels right of and 6 above the ant's centre): the tail points down at the ant.

## Joins `build.py` checks

Every one of these must hold or the build refuses the file: `left`, `right`, `inside` have 8 identical rows; `top`,
`bottom`, `inside` have 8 identical columns; the right column of `top_left` equals the left column of `top`, of `top`
equals that of `top_right`, of `left` equals that of `inside`, of `inside` equals that of `right`, of `bottom_left`
equals that of `bottom`, of `bottom` equals that of `bottom_right`; the bottom row of `top_left` / `top` / `top_right`
equals the top row of `left` / `inside` / `right`; the top row of `bottom_left` / `bottom` / `bottom_right` / the
tails equals that of `left` / `inside` / `right` / `inside`; each tail's rows 0..2 equal `inside` and its rows 0..3 join
`bottom_left` and `bottom` on both sides.

## What must read clearly

The outline unbroken all the way round except at the tail's opening, no stray pixels, the corners smooth and the same on
all four sides, the tail clearly a speech tail pointing down at the speaker. Keep it plain: 1-pixel black line,
white fill, no shading and no other colours. Design it yourself; do not copy a particular game's or comic's balloon.

Also write `make_balloon.py` in the output folder (it writes `balloon.pix`, so it can be regenerated) and a short
`README.md` describing the design.
