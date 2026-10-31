# Spec: the bitmap fonts

> **Status (2026-10-31):** complete, ready for a maker. Written from the font loader, the shell's text drawing and the
> measured widths. The build encodes and checks the files (`tools/clean_pack/build.py`).

Output folder: `remake/game/assets/clean/src/fonts/`. Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an
entry). Six fonts, numbered as the game numbers them (0..5); for each one a picture and a small metrics file:

| Files | Game font | Size of a cell (w x h) | Characters in the picture | Picture (w x h) |
|---|---|---|---|---|
| `font0.pix`, `font0.json` | 0 | 9 x 15 | 127 (codes 0..126, 8 rows) | 144 x 120 |
| `font1.pix`, `font1.json` | 1 | 8 x 10 | 127 (codes 0..126, 8 rows) | 128 x 80 |
| `font2.pix`, `font2.json` | 2 | 16 x 10 | 256 (16 rows) | 256 x 160 |
| `font3.pix`, `font3.json` | 3 | 16 x 10 | 256 (16 rows) | 256 x 160 |
| `font4.pix`, `font4.json` | 4 | 16 x 15 | 217 (codes 0..216, 14 rows) | 256 x 210 |
| `font5.pix`, `font5.json` | 5 | 16 x 11 | 256 (16 rows) | 256 x 176 |

Also write `make_fonts.py` (a script that writes all twelve files, so they can be regenerated), a short `README.md`
(the design of each face, any open-licensed font used as a base with its licence and a link) and, recommended,
`preview.png` (every font at 1x and 3x showing the pangram line, the digits, the punctuation, the capitals and the
lowercase letters, each character placed with the advances below, so the spacing can be judged).

## Format

**The picture** (`.pix`, see README.md; here only `f` and `.` are used): plain text, one line per pixel row, one
character per pixel; `f` is ink (the font is one colour; the game chooses the colour), `.` is no ink. Lines starting
with `#` are comments and may be used freely (for example one at the top). The picture is a grid of cells, **16 across**:
character code `c` is at column `c % 16`, row `c // 16` (so the capital A, code 65, is the second cell of the fifth
row of cells), every cell has the size in the table, and cells follow each other with no gap. A cell's **left edge is
the pen position** where the character is drawn and its top row is the font's row 0. Ink may reach the right edge of
the cell, past the character's advance (the next character just draws over it, as bold or italic faces do), but never
outside the cell. The cells after the last character (font 4: 217..223) stay empty.

**The metrics file** (`.json`, one per font): a JSON object. Copy the blocks below.

- `"advances"`: a list with one number per character of the picture (code 0 first): how many pixels the pen moves
  right after drawing the character. **These are exact**: the game's layouts and word wrap were built around them and
  the build rejects any difference. A character with an empty cell draws nothing and only moves the pen (by 0, if the
  advance is 0).
- `"ascent"` (fonts 2..5): the number of pixel rows above the baseline, counting from the cell's top: rows `0 .. ascent-1`
  are above it, the letters stand on row `ascent - 1` and descenders use the rows from `ascent` down.
- `"missing_advance"` (fonts 2..5): the advance of every character code the font does not draw: codes after the last
  one of the picture (font 4 only) and any code whose cell is empty and whose advance equals this number.
- `"first_index"` (font 0 only): a header number of the game's own font format, 1 here. Copy it, do not think about it.

A font's **height** is the picture's height divided by its rows of cells, and the build checks height, ascent and every
advance against the measurements. A character whose cell has ink is drawn; a character with no ink draws nothing and
only moves the pen.

How the game draws, so you know what the rows mean: text is drawn with its left edge at the pen start and each
character's cell is drawn at the pen, then the pen moves right by the advance. **Fonts 2..5 are drawn one pixel above the
line's top**: their cell row 0 sits above the line and the line pitch is `height - 1` (9, 9, 14, 10 pixels); keep row 0
for accents and tall marks (the dollar sign's stroke ends, accented capitals), and put ordinary capitals from row 1 or
lower as the table says. Fonts 0 and 1 are drawn from the line's top and their pitch is their height.

Palette and colour do not matter (one colour); there is no anti-aliasing and no transparency apart from `.`.

## The fonts, one by one

Vertical measures are in cell rows counted from 0 at the top; match them within a pixel at most, because the windows
centre text by height and the labels were laid out for them.

### Font 0: 9 x 15, monospaced, bold (`font0`)

- **Where**: the main caption face. Window title bars ("Behavior Control", "History Window", "Save Game", "Load Game"),
  the file dialog (drive list, folder line, file names, the typed name), the dialog buttons ("SAVE", "LOAD", "Save",
  "Cancel", "DON'T SAVE", "DEBUG"), the captions under the scene pictures (the ant lion, ...), the alert and error boxes
  ("Permission denied", Yes / No ...), and the pull-down menu bar and menus. It stands in for the PC's text-mode ROM
  font: alerts and menus place one character per 8-pixel cell without reading the advance, so letters are laid out as
  on a text screen.
- **Style**: a bold, upright, monospaced sans-serif with square-ish terminals, like a text-mode terminal face but with
  bold 2-pixel vertical strokes; it must stay legible in cyan or magenta on black or dark grey.
- **Metrics**: height 15, advance 9 for codes 32..126, 0 for everything else. Capitals 9 rows tall on rows 2..10,
  lowercase x-height 6 (rows 5..10), descenders down to row 12, rows 13 and 14 empty; no ink above row 2 except
  accents of the symbols. Letters occupy columns 1..7 of the cell (column 0 and 8 are the spacing between letters);
  the menus and alerts draw each character inside an 8-pixel cell, so **keep ink in columns 0..7** and use column 8
  only if a glyph really needs it (the original uses it for the slash only). Column 0 is for wide letters (M, W, m, w,
  T, V, X, Y, Z, @ and the like).
- **Characters**: codes 32..126, all with a glyph (32 is blank). Optionally, **recommended**: a small right-pointing
  solid triangle (the menus' "checked" mark) at code 16, with advance 0 as listed (the shell draws the check marks of
  the menus with this font).

### Font 1: 8 x 10, monospaced (`font1`)

- **Where**: the PC symbol face; the original draws the menus' "checked" mark (a triangle) with it. The current shell
  does not load it, but the pack must have it (a later version of the menus will).
- **Style**: a plain monospaced text-mode face, 8 pixels per character, upright, strokes 2 pixels wide on capitals;
  a little narrower and lighter than font 0.
- **Metrics**: height 10, advance 8 for codes 1..126, 0 for code 0. Capitals 7 rows tall (rows 0..6), lowercase x-height
  5 (rows 2..6), descenders one row (row 7), rows 8 and 9 empty. Ink in columns 0..6 (column 7 is the spacing) with
  rare exceptions.
- **Characters**: 32..126 (letters, digits, punctuation) and **code 16, a right-pointing solid triangle, 7 rows
  tall and at most 7 wide** (the check mark). The codes 1..15 and 17..31 (the PC code page's face, arrows and card
  suits) and 127 may be left empty; keep their advance 8 as listed.

### Font 2: the normal text face (`font2`)

- **Where**: all running text: the SimAntipedia's body text (everything that is not a bold word), the balloons (the
  tips and the tutorial), the timed messages at the top of the yard and the edit map, "Click here to continue" under
  the four-line message boxes, the population report's lines, the shell's status lines. If a font is missing the game
  falls back to this one.
- **Style**: a clean, regular-weight proportional sans-serif with 1-pixel strokes, readable at this size, slightly
  open letter shapes; digits all 6 wide (tabular).
- **Metrics**: height 10, ascent 8, line pitch 9. Capitals 7 rows tall (rows 1..7), lowercase x-height 5 (rows 3..7),
  descenders 2 rows (rows 8..9), row 0 only for accents and tall symbols. Space 3; digits 6; capitals 6 to 10; lowercase 3
  to 8; the exact numbers are below.
- **Characters**: see "The character set".

### Font 3: the small serif face (`font3`)

- **Where**: the numbers and small labels: the population report's counts in the Map window, the history graph's value
  labels, the yard counters, the value fields of some windows (layouts 24 and 25), and "Click here to continue" in the
  tall message box (layout 30).
- **Style**: a small, compact proportional serif (a book-style text face), 1-pixel strokes, the narrowest of the
  proportional fonts; digits 5 wide.
- **Metrics**: height 10, ascent 8, line pitch 9. Capitals 6 rows tall (rows 2..7), lowercase x-height 4 (rows 4..7),
  descenders 2 rows (rows 8..9). Its advances are about 1 pixel narrower than font 2's for the same character.
- **Characters**: see "The character set".

### Font 4: the large face (`font4`)

- **Where**: the boxes that must be read: the message boxes with a picture (the tutorial and information boxes), the
  GAME OVER window (the mode, the score, the rank), the Efficiency Score window's figures, the Save / Load prompt's
  question, the percentages of the Behavior and Caste Control windows, and the credits that scroll up in the About box.
  If missing, the game falls back to font 2.
- **Style**: a large, sturdy, semi-bold proportional sans-serif, strokes 2 pixels wide on the stems, clearly bigger
  than font 2; digits 8 wide.
- **Metrics**: height 15, ascent 12, line pitch 14. Capitals 9 rows tall (rows 3..11), lowercase x-height 7 (rows
  5..11), descenders 3 rows (rows 12..14), rows 0..2 for accents only. The picture has **217 characters** (codes 0..216);
  every later code uses `missing_advance`.
- **Characters**: see "The character set". The codes 17..20 may stay empty.

### Font 5: the bold face (`font5`)

- **Where**: only the SimAntipedia: the bold words of the articles, which are links to the glossary pop-ups.
- **Style**: a bold proportional sans-serif, the same family and size as font 2 but heavier (2-pixel stems), so a bold
  word inside a font-2 sentence reads as emphasis; advances a little wider than font 2's.
- **Metrics**: height 11, ascent 9, line pitch 10. Capitals 8 rows tall (rows 1..8), lowercase x-height 5 (rows 4..8),
  descenders 2 rows (rows 9..10).
- **Characters**: see "The character set".

## The character set

Text in the game is written in ASCII plus Mac Roman (codes 128..255) for a few symbols; the shell maps the symbols it
knows (bullet, copyright, trademark, ellipsis, en and em dash) to those codes and every other non-ASCII character to
`?`. Scanning every string, text and menu of the original, outside ASCII only the trademark sign (several times), the em
dash (7 times) and the right single quote (once) occur. The clean pack's fonts therefore need:

- **Required, all fonts that draw text (0, 2, 3, 4, 5)**: codes 32..126 (the space, all the punctuation and symbols
  of ASCII including the backslash, caret, underscore, grave accent and tilde, the digits, the capitals and the
  lowercase letters) and the six symbols
  **165 bullet, 169 copyright sign, 170 trademark sign, 201 horizontal ellipsis, 208 en dash, 209 em dash** (fonts 2,
  3, 4 and 5; fonts 0 and 1 have no codes above 126). Codes 9 (tab) and 13 (return) are blank with the advances listed.
- **Recommended**: the typographic quotes **210 (left double), 211 (right double), 212 (left single), 213 (right
  single)** (the shell shows straight quotes for them for now) and 160 (non-breaking space: blank, advance as listed).
- **Optional**: every other code from 128 to 255 of the Mac Roman set (accented letters, symbols) may stay empty. Keep their
  advances as listed anyway; if you do draw them, use Mac Roman's meaning.

The new text written for the clean pack will be limited to this required and recommended set.

## The advances (copy these)

Line `n` of a list holds the codes `16 n` .. `16 n + 15`. Do not change any number; the metrics files are exactly these.
Keep the number of entries as the first table says (fonts 0 and 1: 127 entries, font 4: 217, the others 256), so that
the picture has the rows stated there.

`font0.json`

```json
{
  "first_index": 1,
  "advances": [
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,
     9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,
     9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,
     9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,
     9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,
     9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9
  ]
}
```

`font1.json`

```json
{
  "advances": [
     0,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8
  ]
}
```

`font2.json`

```json
{
  "ascent": 8,
  "missing_advance": 6,
  "advances": [
     3,  6,  6,  6,  6,  6,  6,  6,  6,  3,  6,  6,  6,  1,  6,  6,
     6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,
     3,  4,  4,  6,  6,  9,  7,  3,  4,  4,  5,  6,  4,  4,  4,  4,
     6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  4,  4,  6,  6,  6,  6,
    10,  7,  7,  7,  7,  7,  6,  8,  7,  4,  6,  7,  6,  8,  7,  8,
     7,  8,  7,  7,  6,  7,  7,  9,  7,  7,  6,  4,  4,  4,  5,  6,
     4,  6,  6,  6,  6,  6,  4,  6,  6,  3,  3,  6,  3,  8,  6,  6,
     6,  6,  4,  6,  4,  6,  6,  7,  6,  6,  6,  4,  3,  4,  6,  6,
     7,  7,  7,  7,  7,  8,  7,  6,  6,  6,  6,  6,  6,  6,  6,  6,
     6,  6,  3,  3,  4,  4,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,
     6,  4,  6,  6,  6,  4,  6,  6,  8,  8,  9,  4,  4,  6, 10,  8,
     7,  6,  6,  6,  6,  6,  5,  7,  9,  6,  4,  4,  4,  8,  9,  6,
     6,  4,  7,  6,  6,  6,  7,  6,  6, 10,  6,  7,  7,  8, 10,  9,
     6, 10,  4,  4,  3,  3,  6,  5,  6,  7,  3,  6,  4,  4,  6,  6,
     6,  4,  3,  4, 10,  7,  7,  7,  7,  7,  4,  4,  4,  4,  8,  8,
     8,  8,  7,  7,  7,  3,  4,  4,  4,  5,  4,  4,  4,  4,  4,  6
  ]
}
```

`font3.json`

```json
{
  "ascent": 8,
  "missing_advance": 5,
  "advances": [
     2,  5,  5,  5,  5,  5,  5,  5,  0,  2,  5,  5,  5,  0,  5,  5,
     5,  5,  5,  5,  5,  5,  5,  5,  5,  5,  5,  5,  5,  5,  5,  5,
     2,  3,  4,  5,  5,  7,  7,  2,  3,  3,  5,  5,  3,  3,  3,  3,
     5,  5,  5,  5,  5,  5,  5,  5,  5,  5,  3,  3,  5,  5,  5,  4,
     8,  6,  6,  6,  6,  5,  5,  6,  6,  3,  4,  6,  5,  8,  6,  6,
     5,  6,  6,  5,  5,  6,  6,  8,  6,  6,  5,  3,  3,  3,  4,  5,
     3,  4,  5,  4,  4,  4,  3,  5,  5,  3,  3,  5,  3,  7,  5,  5,
     5,  4,  3,  4,  3,  4,  5,  6,  5,  5,  4,  4,  2,  4,  5,  5,
     6,  6,  6,  5,  6,  6,  6,  4,  4,  4,  4,  4,  4,  4,  4,  4,
     4,  4,  3,  3,  3,  3,  5,  5,  5,  5,  5,  5,  4,  4,  4,  4,
     5,  3,  5,  5,  5,  3,  4,  5,  7,  7,  8,  3,  3,  5,  8,  6,
     6,  5,  5,  5,  5,  5,  5,  6,  8,  5,  3,  2,  3,  7,  6,  5,
     4,  3,  6,  5,  5,  5,  6,  5,  5,  9,  5,  6,  6,  6,  8,  6,
     5,  9,  4,  4,  3,  3,  5,  4,  5,  6,  3,  5,  3,  3,  5,  5,
     5,  3,  3,  4,  9,  7,  6,  7,  6,  6,  3,  3,  3,  3,  6,  6,
     7,  6,  7,  7,  7,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  5
  ]
}
```

`font4.json`

```json
{
  "ascent": 12,
  "missing_advance": 10,
  "advances": [
     0, 10, 10, 10, 10, 10, 10, 10, 10,  8, 10, 10, 10,  0, 10, 10,
    10, 11, 11,  9, 11, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
     4,  6,  7, 10,  7, 11, 10,  3,  5,  5,  7,  7,  4,  7,  4,  7,
     8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  4,  4,  6,  8,  6,  8,
    11,  8,  8,  8,  8,  7,  7,  8,  8,  6,  7,  9,  7, 12,  9,  8,
     8,  8,  8,  7,  6,  8,  8, 12,  8,  8,  8,  5,  7,  5,  8,  8,
     6,  8,  8,  7,  8,  8,  6,  8,  8,  4,  6,  8,  4, 12,  8,  8,
     8,  8,  6,  7,  6,  8,  8, 12,  8,  8,  8,  5,  5,  5,  8,  8,
     8,  8,  8,  7,  9,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     8,  8,  6,  6,  6,  6,  8,  8,  8,  8,  8,  8,  8,  8,  8,  8,
     5,  6,  7,  9,  7,  7,  9,  9, 10, 10, 11,  5,  6,  9, 11,  9,
    14,  7,  6,  6, 10, 10,  8,  9, 10, 11,  6,  7,  7, 10, 12,  8,
     8,  6,  7, 12,  6, 10,  9,  9,  9, 14,  8,  8,  8,  8, 11, 12,
     6, 10,  7,  7,  4,  4,  7,  9,  8
  ]
}
```

`font5.json`

```json
{
  "ascent": 9,
  "missing_advance": 10,
  "advances": [
     1, 10, 10, 10, 10, 10, 10, 10, 10,  4, 10, 10, 10,  1, 10, 10,
    10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
     4,  4,  5,  7,  7, 11,  9,  3,  5,  5,  5,  7,  4,  5,  4,  5,
     7,  7,  7,  7,  7,  7,  7,  7,  7,  7,  4,  4,  7,  7,  7,  6,
    10,  8,  7,  8,  9,  6,  6,  9,  9,  4,  4,  8,  6, 10,  9, 10,
     7, 10,  7,  6,  8,  8,  8, 13,  7,  8,  7,  4,  6,  4,  7,  6,
     4,  6,  7,  6,  7,  6,  4,  6,  7,  4,  4,  6,  4, 10,  7,  7,
     7,  7,  5,  5,  5,  7,  6,  9,  6,  6,  6,  5,  7,  5,  7, 10,
     8,  8,  8,  6,  9, 10,  8,  6,  6,  6,  6,  6,  6,  6,  6,  6,
     6,  6,  4,  4,  4,  4,  7,  7,  7,  7,  7,  7,  7,  7,  7,  7,
     7,  5,  7,  7,  7,  7,  8,  7, 11, 11, 12,  4,  5,  7,  9, 10,
     8,  7,  7,  7,  7,  7,  6,  8, 10,  7,  4,  5,  5, 10,  9,  7,
     6,  4,  7,  7,  7,  7,  8,  7,  6, 10,  4,  8,  8, 10, 11, 10,
     6, 11,  7,  7,  4,  4,  7,  8,  6,  8,  3,  7,  5,  4,  7,  7,
     7,  4,  4,  7, 11,  8,  6,  8,  6,  6,  4,  4,  4,  4, 10, 10,
     9, 10,  8,  8,  8,  4,  5,  5,  5,  4,  4,  5,  4,  5,  4,  4
  ]
}
```

## Notes

- **Open-licensed fonts as a base.** You may start from an open-licensed bitmap font, as long as you redraw it to these
  advances, cell sizes and vertical measures and note its name, licence and link in `README.md` and the provenance entry.
  Possible bases (check the licence text and the metrics yourself before use): *Terminus* (SIL OFL 1.1; a monospaced
  bitmap family, for fonts 0 and 1), *Spleen* (BSD 2-Clause; monospaced bitmap sizes), *ProggyClean* (MIT; monospaced),
  *Cozette* (MIT; small proportional-looking bitmap face). Generally no font will already have these exact advances:
  expect to redraw at least the proportional faces (2..5) by hand or by script. Do not copy or trace any commercial
  game's or system's fonts.
- **Fonts 2 to 5 should look like one family**: 3 is the small serif for numbers, 2 the everyday sans, 5 its bold,
  4 the large sans for headlines. Fonts 0 and 1 are the text-mode faces.
- Everything that is not listed here (kerning, ligatures, more sizes) does not exist in the game. One colour, no
  anti-aliasing.
- Check your files before you finish: the picture sizes in the first table, every row of equal length, only `f` and `.`,
  the number of `advances` as stated, and that no ink lies outside its cell.
