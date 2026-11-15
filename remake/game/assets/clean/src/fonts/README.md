# Clean-pack bitmap fonts

Six original fonts (`font0` .. `font5`, each a `.pix` glyph grid and a `.json` of advances), made from the written
spec `docs/clean_pack/fonts.md`. **No open-licensed or other existing font was used as a base**: every glyph is drawn
by `make_fonts.py` from scratch. Run `python make_fonts.py` to rewrite all twelve files, run the self-check and redraw
`preview.png` (`python make_fonts.py --dump N [first last]` prints the glyphs of font N as text).

## How the glyphs are made

Each character is a *skeleton*: one to four poly-lines in units of the glyph box (x as a fraction of the ink width, y
relative to the face's anchor rows: cap top, x-height top, baseline, descender bottom; see the docstring in the
script). A skeleton is rasterised for each face with that face's pen (1 or 2 pixel stems), corner rounding (a cut of
1 or 2 pixels at the corners marked `~`), anchor rows, dot size and ink width. The ink width of a glyph is its
advance from the spec minus the gap (so the advance table, which is exact, drives the shapes: a 7-wide `H` is wider
than a 6-wide one). A few letters (`i`, `j`, `l`, `I`, the slashed zero) have a separate drawing for the two
monospaced faces. The four proportional faces therefore look like one family; only the parameters differ.

## The faces

- **font0** (9 x 15, mono, bold): the text-mode caption face. 2-pixel vertical stems, 1-pixel horizontals, corners
  cut by 2 pixels on capitals. Capitals rows 2..10, x-height rows 5..10, descenders to row 12, advance 9. Ink in
  columns 1..7; the wide letters (M W T V X Y Z m w @ % &) use column 0 as well, and nothing uses column 8. `i`, `j`,
  `l`, `I` have foot bars, the zero is slashed, so it stays readable as caption text on dark colours. Code 16 is a
  solid right-pointing triangle (4 x 7, advance 0) for the menus' check marks.
- **font1** (8 x 10, mono, lighter): same plan, narrower and lighter than font0: capitals and digits have 2-pixel
  stems, lowercase 1-pixel strokes. Capitals rows 0..6, x-height rows 2..6, descender row 7; ink in columns 0..6
  (column 7 is the spacing). Code 16 is the 4 x 7 solid triangle
  (the original check mark's place); codes 1..15, 17..31 and 127 are empty with advance 8 as listed.
- **font2** (16 x 10, regular sans): 1-pixel strokes, capitals rows 1..7, x-height rows 3..7, descenders rows 8..9,
  row 0 only for the dollar sign's stroke ends. Digits are 5 pixels of ink in the 6-pixel advance (tabular).
  Double-storey `a`, single-storey `g`, open squarish shapes with cut corners.
- **font3** (16 x 10, small serif): since the 2026-11-01 polish every ASCII glyph (33..126) and the ellipsis and the
  two dashes are **hand-drawn pixel by pixel** (`HAND3` / `h3()` in `make_fonts.py`), not made from skeletons: the
  skeleton pass left the narrow letters cramped, the counters filled in and the symbols plain. The rules: ink at most
  advance - 1 wide wherever the shape allows (a clear 1-pixel gap between letters; only `_` runs the full advance so
  underlines join), capitals and digits rows 2..7, x-height rows 4..7, **ascenders (b d f h k l) from row 1**,
  descenders to row 9, dots of `i` / `j` on row 2 with a clear row beneath, parentheses and brackets rows 1..9. The
  serif character is kept as small flags and feet that do not close a counter: symmetric feet on `A H I J K L M N P R B
  D E F Y X`, top flags on the lowercase stems (`b d h k l`), but no one-sided feet on lowercase stems (they
  read as a hook: `i` looked like `j`). `a` is single-storey, `e` keeps a 1-pixel counter above its bar, `T` has a
  2-pixel stem, `$` runs rows 1..8, `% & @ # ~ { }` are drawn properly (`%` with two hollow 3 x 3 rings and a diagonal,
  `&` with a closed top loop, `@` an a in a ring, `{ }` with the pointed middle). The 4x sample line is in
  `font3_sample_4x.png`. The advances, ascent and missing advance are unchanged (fixed by the game); fonts 0, 1, 2, 4,
  5 are byte-identical to before. The bullet, copyright, trademark and quote marks (codes 165..213 except 201, 208,
  209) still come from the skeleton pass.
  - **The 2026-11-15 re-drawing (issue #52):** the similarity review measured 30 of the 221 inked glyphs as
    pixel-identical to the original's face. Nineteen of them are re-drawn here — the digits `0 2 5 6 8 9`, the capitals
    `B H O`, the lowercase `o p u` and the symbols `/ < = > ? \ ~` — as the cells in `font3_redraw.py`: the isolated
    clean-room maker's transcription of the spec's printed cells, verified pixel-exact against the spec (the module's
    self-test: `python font3_redraw.py`). The old hand-drawn art for those codes is retired from this file; the
    remaining 11 identical glyphs are the geometrically-forced marks (the dot, the ticks, the caret, the underscore and
    the rare Mac-roman symbols) that the other fonts' residual matches are made of. `font3_sample_4x.png` is
    re-drawn from the current cells by `sample4x()` on every run.
- **font4** (16 x 15, large semi-bold sans): 2-pixel stems, 1-pixel horizontals, 2-pixel corner cuts; capitals rows
  3..11, x-height rows 5..11, descenders rows 12..14, digits 7 pixels of ink in the advance 8. The 217-character
  picture leaves 217..223 empty; codes 17..20 are empty as the spec permits.
- **font5** (16 x 11, bold sans): font2's shapes with 2-pixel stems; capitals rows 1..8, x-height rows 4..8,
  descenders rows 9..10. Wider advances than font2 (the exact table), so a bold word reads as emphasis.

Fonts 2..5 also draw the six required symbols (bullet 165, copyright 169, trademark 170, ellipsis 201, en dash 208,
em dash 209) and the recommended typographic quotes 210..213 (the double quote is two dots with tails, the opening
marks are the closing ones turned 180 degrees). Codes 9, 13 and 160 are blank; everything else outside ASCII is
empty with the listed advance.

## The self-check

`make_fonts.py` reads the twelve files back and asserts, for each font: picture size against the spec's table; only
`f` and `.`; the advances list identical to the spec's (and its length); the header numbers (`first_index`, `ascent`,
`missing_advance`); no ink outside the cell, and none in cells beyond the last character; ink on every required code
(33..126, the six symbols, the four quotes, code 16 in fonts 0 and 1); the ink's right edge at most 2 pixels past the
advance; the vertical measures of the capitals and digits, the x-height letters, the ascender letters and the
descender letters within one pixel of the spec; font0 ink only in columns 0..7, font1 only in 0..6.

## Known limits

Fonts 0, 1, 2, 4 and 5 are skeleton-made and not hand-tuned pixel by pixel: their ampersand, percent sign, braces and
tilde are plain. Font 3 is hand-drawn (see above) but at 3 pixels of ink the `a` and `e` stay close cousins and the
counters are one pixel. Everything is one colour with no anti-aliasing, as the spec asks.
