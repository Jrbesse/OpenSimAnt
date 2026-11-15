"""Font 3 redraw -- issue #52 (clean pack), 19-glyph version.

Nineteen replacement glyph cells for the clean pack's font 3 (small book-style
serif face, 16x10 px cells, 1-pixel strokes, one colour), transcribed
verbatim from spec/font3-redraw-52-full.md. Storage format per glyph:

    code -> (top_row, [row strings, '#' ink / '.' empty], left)

Run as a script to print the 19 glyphs and self-check the stored geometry:

    python font3_redraw.py

Exits non-zero if any stored row does not match the row count/width implied
by the spec's printed block dimensions.
"""

# font 3 redraw (issue #52, 19 cells): code -> (top_row, [row strings, '#' ink / '.' empty], left)
FONT3_REDRAW = {
    48: (2, ["####", "#..#", "#..#", "#..#", "#..#", "####"], 0),
    50: (2, ["####", "#..#", "...#", "..#.", ".#..", "####"], 0),
    53: (2, ["####", "#...", "####", "...#", "#..#", "####"], 0),
    54: (2, [".##.", "#...", "#...", "####", "#..#", "####"], 0),
    56: (2, ["####", "#..#", "####", "#..#", "#..#", "####"], 0),
    57: (2, ["####", "#..#", "#..#", "####", "...#", "...#"], 0),
    66: (2, ["#####", ".#..#", ".###.", ".#..#", ".#..#", "#####"], 0),
    72: (2, ["##.##", ".#.#.", ".###.", ".###.", ".#.#.", "##.##"], 0),
    79: (2, ["#####", "#...#", "#...#", "#...#", "#...#", "#####"], 0),
    111: (4, ["####", "#..#", "#..#", "####"], 0),
    112: (4, ["####", "#..#", "#..#", "####", "#...", "###."], 0),
    117: (4, ["#.#", "#.#", "#.#", "##."], 0),
    63: (2, [".##.", "#.#.", "..#.", ".#..", "....", ".#.."], 0),
    61: (4, ["###.", "....", "###."], 0),
    60: (3, ["..#.", ".#..", "#...", "#...", ".#.."], 0),
    62: (3, [".#..", "..#.", "...#", "...#", "..#."], 0),
    47: (2, [".#..", ".#..", "#...", "#...", "#...", "#..."], 0),
    92: (2, ["#...", "#...", ".#..", ".#..", ".#..", ".#.."], 0),
    126: (4, [".##.", "##.."], 0),
}

# Printed block dimensions from the spec: code -> (row count, row width).
EXPECTED = {
    48: (6, 4), 50: (6, 4), 53: (6, 4), 54: (6, 4), 56: (6, 4), 57: (6, 4),
    66: (6, 5), 72: (6, 5), 79: (6, 5),
    111: (4, 4), 112: (6, 4), 117: (4, 3),
    63: (6, 4), 61: (3, 4), 60: (5, 4), 62: (5, 4),
    47: (6, 4), 92: (6, 4), 126: (2, 4),
}

CELL_COLS, CELL_ROWS = 16, 10


def check():
    """Return a list of problem strings (empty when the stored cells are consistent)."""
    problems = []
    if set(FONT3_REDRAW) != set(EXPECTED):
        problems.append("FONT3_REDRAW codes != the expected 19 codes")
    for code, (top, rows, left) in FONT3_REDRAW.items():
        if code not in EXPECTED:
            continue
        n_rows, width = EXPECTED[code]
        if len(rows) != n_rows:
            problems.append("%d: %d rows, expected %d" % (code, len(rows), n_rows))
        for i, row in enumerate(rows):
            if len(row) != width:
                problems.append("%d: row %d is %d wide, expected %d"
                                % (code, i, len(row), width))
            bad = sorted(set(row) - set("#."))
            if bad:
                problems.append("%d: row %d has characters other than #/.: %s"
                                % (code, i, bad))
        if left != 0:
            problems.append("%d: left %d, expected 0" % (code, left))
        if top + len(rows) > CELL_ROWS:
            problems.append("%d: rows spill past cell row %d" % (code, CELL_ROWS - 1))
    return problems


def main():
    problems = check()
    if problems:
        for p in problems:
            print("font3_redraw: FAIL %s" % p)
        return 1
    for code, (top, rows, left) in FONT3_REDRAW.items():
        print("[%d] %s" % (code, chr(code)))
        for row in rows:
            print(row)
        print()
    print("font3_redraw: 19 glyphs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
