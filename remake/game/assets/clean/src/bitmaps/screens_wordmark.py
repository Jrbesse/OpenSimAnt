"""Flat title-screen wordmark for OpenSimAnt.

Clean-room module generated from spec/title-wordmark.md ONLY. It composes the
string "OpenSimAnt" (or any subset of the nine defined glyphs) into a boolean
mask and stamps it onto a canvas as a single flat palette colour -- no outline,
no shadow, no gradient, no second colour.

The nine glyph bitmaps below are stored EXACTLY as printed in the spec: each is
a full 10-row cell, printed one glyph per block, with the lowercase e, n and m
cells carrying their two leading blank rows (and p its two leading blank rows
plus its descender on the last two rows). Leading and trailing blank rows are
part of the glyph: no trimming, re-centering or re-baselining is applied
anywhere.

Imports: numpy only.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Glyph bitmaps, stored EXACTLY as printed in spec/title-wordmark.md: nine
# stacked 10-row cells, '#' is ink, '.' is blank. Width == row length.
# Do NOT alter, trim, re-center or re-baseline these.
# ---------------------------------------------------------------------------
GLYPHS = {
    "O": [
        ".###.",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".###.",
        ".....",
        ".....",
    ],
    "p": [
        "....",
        "....",
        "###.",
        "#..#",
        "#..#",
        "#..#",
        "#..#",
        "###.",
        "#...",
        "#...",
    ],
    "e": [
        "....",
        "....",
        ".##.",
        "#..#",
        "####",
        "####",
        "#...",
        ".###",
        "....",
        "....",
    ],
    "n": [
        "....",
        "....",
        "###.",
        "#..#",
        "#..#",
        "#..#",
        "#..#",
        "#..#",
        "....",
        "....",
    ],
    "S": [
        ".####",
        "#....",
        "#....",
        ".###.",
        ".###.",
        "....#",
        "....#",
        "####.",
        ".....",
        ".....",
    ],
    "i": [
        "#",
        ".",
        "#",
        "#",
        "#",
        "#",
        "#",
        "#",
        ".",
        ".",
    ],
    "m": [
        ".....",
        ".....",
        "##.#.",
        "#.#.#",
        "#.#.#",
        "#.#.#",
        "#.#.#",
        "#.#.#",
        ".....",
        ".....",
    ],
    "A": [
        ".###.",
        "#...#",
        "#...#",
        "#####",
        "#####",
        "#...#",
        "#...#",
        "#...#",
        ".....",
        ".....",
    ],
    "t": [
        "...",
        ".#.",
        "###",
        ".#.",
        ".#.",
        ".#.",
        ".#.",
        "..#",
        "...",
        "...",
    ],
}

# The face height: every glyph cell is exactly 10 rows tall.
_ROW_HEIGHT = 10


def _parse(rows):
    """Parse a list of '#'/'.' row strings into a boolean 2-D array."""
    return np.array([[ch == "#" for ch in row] for row in rows], dtype=bool)


def render_mask(s, scale=1):
    """Compose the string ``s`` into a boolean mask per the composition rules.

    - Each glyph's advance = its width + 1 (one blank pixel gap between
      letters).
    - Glyph k is placed with its left edge at x = sum of the advances of all
      previous glyphs (first glyph at x = 0).
    - The string matrix is _ROW_HEIGHT rows tall.
    - At scale ``s`` each font pixel becomes an s x s block (the matrix is
      tiled s x s).

    A single-character render places that glyph at column 0, so the result is
    exactly the glyph's stored (exactly-as-printed) bitmap.

    Raises ``ValueError`` on any character not present in GLYPHS.
    """
    if not s:
        return np.zeros((_ROW_HEIGHT, 0), dtype=bool)

    glyphs = []
    for ch in s:
        if ch not in GLYPHS:
            raise ValueError("no glyph defined for %r" % (ch,))
        glyphs.append(_parse(GLYPHS[ch]))

    # Total width: sum of glyph widths + one gap pixel between each pair.
    total_w = sum(g.shape[1] for g in glyphs) + (len(glyphs) - 1)

    matrix = np.zeros((_ROW_HEIGHT, total_w), dtype=bool)
    x = 0
    for g in glyphs:
        gw = g.shape[1]
        matrix[:, x:x + gw] |= g
        x += gw + 1  # advance = width + 1

    if scale == 1:
        return matrix
    # Tile the matrix scale x scale: each font pixel becomes an s x s block.
    return np.kron(matrix, np.ones((scale, scale), dtype=bool))


def plain_wordmark(cv, pic, x, y, s, scale, color, lettered=None):
    """Stamp the composed mask flat onto canvas ``cv`` at pixel (x, y).

    ``cv`` exposes ``cv.w``, ``cv.h``, ``cv.arr()`` (2-D array of palette
    indices, rows x columns) and ``cv.set_arr(a)``.

    Anchor: the mask's top-left corner goes to pixel (x, y). Every mask (ink)
    pixel is set to palette index ``color``; pixels outside the mask are
    untouched. The draw is clamped to the canvas bounds.

    If ``lettered`` is a list, the pair ``(pic, s)`` is appended to it.

    Returns the ink bounding box of the mask as (ink_w, ink_h, ink_x, ink_y),
    with ink_x / ink_y in canvas coordinates, measured from the non-zero mask
    pixels -- like a drawing routine's bounds return.
    """
    mask = render_mask(s, scale)
    mh, mw = mask.shape

    # Ink bounding box within the mask (first/last non-zero row and column).
    if mask.any():
        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        ink_top, ink_bottom = int(rows.min()), int(rows.max())
        ink_left, ink_right = int(cols.min()), int(cols.max())
    else:
        ink_top = ink_bottom = ink_left = ink_right = 0
    ink_h = ink_bottom - ink_top + 1
    ink_w = ink_right - ink_left + 1
    ink_x = x + ink_left
    ink_y = y + ink_top

    # Clamp the mask's canvas footprint to the canvas bounds.
    r0, c0 = y, x
    r1, c1 = y + mh, x + mw
    r0c = max(r0, 0)
    c0c = max(c0, 0)
    r1c = min(r1, cv.h)
    c1c = min(c1, cv.w)

    if r0c < r1c and c0c < c1c:
        arr = cv.arr()
        sub = mask[r0c - r0:r1c - r0, c0c - c0:c1c - c0]
        region = arr[r0c:r1c, c0c:c1c]  # a view; writes go straight into arr
        region[sub] = color  # only ink pixels change; the rest is untouched
        cv.set_arr(arr)

    if lettered is not None:
        lettered.append((pic, s))

    return (ink_w, ink_h, ink_x, ink_y)


if __name__ == "__main__":
    # --- self-test ---------------------------------------------------------
    class _Canvas:
        """Tiny stand-in providing the arr/set_arr/w/h interface."""

        def __init__(self, arr):
            self._arr = arr
            self.w = arr.shape[1]
            self.h = arr.shape[0]

        def arr(self):
            return self._arr

        def set_arr(self, a):
            self._arr = a

    arr = np.zeros((372, 512), dtype=int)
    cv = _Canvas(arr)
    before = cv.arr().copy()

    x, y = 28, 46
    result = plain_wordmark(cv, 2000, x, y, "OpenSimAnt", 4, 1)
    after = cv.arr()

    # 1) the mask is (40, 196)
    mask = render_mask("OpenSimAnt", 4)
    assert mask.shape == (40, 196), "mask shape %r != (40, 196)" % (mask.shape,)

    # 2) painted pixels are exactly 1 and form the 40x196 block at (28, 46):
    #    the set of changed pixels equals the mask pixels offset by (x, y),
    #    and every changed pixel now holds value 1.
    mh, mw = mask.shape
    expected = np.zeros((cv.h, cv.w), dtype=bool)
    expected[y:y + mh, x:x + mw] = mask

    changed = after != before
    assert np.array_equal(changed, expected), (
        "changed pixel set != mask pixel set offset by (%d, %d)" % (x, y))
    assert np.all(after[changed] == 1), "some changed pixel is not exactly 1"

    # 3) no other pixel of the canvas changed
    assert np.all(after[~changed] == 0), "a pixel outside the mask changed"

    # 4) the ink spans the full extent the spec documents: first ink at
    #    column 0 / row 0, last ink at column 195 / row 39, so the returned
    #    ink bounding box is the full 196x40 block at (28, 46).
    assert result == (196, 40, x, y), "bounds return %r != (196, 40, 28, 46)" % (result,)
    ink = after == 1
    irows, icols = np.where(ink)
    assert (int(icols.min()), int(irows.min())) == (x, y), "first ink not at (28, 46)"
    assert (int(icols.max()), int(irows.max())) == (x + 195, y + 39), (
        "last ink not at (%d, %d)" % (x + 195, y + 39))

    # 5) single-glyph equality: for each of the nine glyphs g, render_mask(g)
    #    equals that glyph's printed 10-row cell exactly (a single-character
    #    render places the glyph at column 0, so the result is the stored
    #    bitmap verbatim).
    for g in GLYPHS:
        single = render_mask(g, 1)
        printed_cell = _parse(GLYPHS[g])
        assert len(GLYPHS[g]) == 10, "glyph %r is not a 10-row cell" % (g,)
        assert single.shape == printed_cell.shape, (
            "render_mask(%r) shape %r != %r"
            % (g, single.shape, printed_cell.shape))
        assert np.array_equal(single, printed_cell), (
            "render_mask(%r) does not equal its printed 10-row cell" % (g,))

    print("OK")
