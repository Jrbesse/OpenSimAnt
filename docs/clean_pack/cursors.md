# Spec: mouse cursors

Output folder: `remake/game/assets/clean/src/cursors/`. Provenance file: `remake/game/assets/clean/PROVENANCE.md`.
Format: `.pix` (see below). Palette: indices 0 white, 15 black (others listed in the table below, but cursors use only
white and black).

## Format: .pix

Plain text. One line per pixel row, top to bottom; one character per pixel, left to right: a hexadecimal digit
`0`-`9` / `a`-`f` is a palette index, `.` is transparent (the screen shows through). Lines starting with `#` are
comments. Every row of a file must have the same length.

Palette indices: 0 white, 1 yellow, 2 orange, 3 red, 4 magenta, 5 purple, 6 blue, 7 cyan, 8 green, 9 dark green,
10 (`a`) brown, 11 (`b`) tan, 12 (`c`) light grey, 13 (`d`) medium grey, 14 (`e`) dark grey, 15 (`f`) black.

## The cursors

The game runs at 640 x 480 with 16 colours and a mouse. The cursor is drawn with its **top-left pixel at the mouse
position**, so for a pointer the tip must be the top-left pixel (0, 0).

| File | Size (w x h) | What |
|---|---|---|
| `0.pix` | 16 x 16 | **The normal pointer.** An arrow pointing up and to the left, tip at (0, 0). It must read clearly over any background (bright green lawn, dark brown soil, grey windows, black): use a black outline around a white fill (or the reverse), and transparent everywhere else. About 10-12 pixels tall is typical; it may use the whole 16 x 16. |
| `1.pix` | 24 x 32 | **The busy cursor**, shown while the game is working: an hourglass (or another clear "please wait" shape), black and white, transparent around it. Its top-left is at the mouse. |

Keep them simple, crisp, 1-pixel lines, no anti-aliasing (only indices 0, 15 and `.`). Design them yourself; don't copy
a particular system's or game's cursor pixel for pixel.

Also write `make_cursors.py` in the output folder: a script that writes both files (so they can be regenerated), and
a short `README.md` there describing the design.
