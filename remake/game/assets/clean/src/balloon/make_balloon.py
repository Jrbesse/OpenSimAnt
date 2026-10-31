"""Makes balloon.pix: the speech balloon's 11 pieces of 8 x 8, side by side (88 x 8).

    python make_balloon.py    # writes balloon.pix and preview.png next to this script

Only '0' (white), 'f' (black) and '.' (transparent) are used. Every join rule of
docs/clean_pack/balloon.md is asserted before the file is written (see README.md).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

ORDER = ["top_left", "top_right", "top", "right", "left", "bottom_left",
         "bottom_right", "bottom", "inside", "tail_right", "tail_left"]

# ---------------------------------------------------------------------------
# Hand-drawn pieces. Top-left corner: the outline leaves the piece along row 4
# to the right and along column 1 downwards, turning through a rounded arc.
TOP_LEFT = [
    "........",
    "........",
    "........",
    "........",
    "..ffffff",
    ".ff00000",
    ".f000000",
    ".f000000",
]

# The tail, in the second bottom cell: row 3 is open between columns 1 and 5
# and the white inside runs down into a triangle with a vertical left edge, a
# diagonal right edge and a one-pixel white tip on row 7 (column 1).
TAIL_LEFT = [
    "00000000",
    "00000000",
    "00000000",
    "f00000ff",
    "f0000ff.",
    "f000f...",
    "f00f....",
    "f0f.....",
]


def mirror(p):
    return [r[::-1] for r in p]


def vflip(p):
    return p[::-1]


PIECE = {
    "top_left": TOP_LEFT,
    "top_right": mirror(TOP_LEFT),
    "top": ["........"] * 4 + ["ffffffff"] + ["00000000"] * 3,
    "right": ["000000f."] * 8,
    "left": [".f000000"] * 8,
    "bottom_left": vflip(TOP_LEFT),
    "bottom_right": mirror(vflip(TOP_LEFT)),
    "bottom": ["00000000"] * 3 + ["ffffffff"] + ["........"] * 4,
    "inside": ["00000000"] * 8,
    "tail_right": mirror(TAIL_LEFT),
    "tail_left": TAIL_LEFT,
}


def col(p, c):
    return "".join(r[c] for r in p)


def check_pieces():
    P = PIECE
    for name, p in P.items():
        assert len(p) == 8, name
        for r in p:
            assert len(r) == 8 and set(r) <= set("0f."), (name, r)

    # tiles that repeat: rows identical (down), columns identical (across)
    for n in ("left", "right", "inside"):
        assert len(set(P[n])) == 1, n + ": rows differ"
    for n in ("top", "bottom", "inside"):
        assert len({col(P[n], c) for c in range(8)}) == 1, n + ": columns differ"

    # where the outline runs
    assert P["top"][:4] == ["........"] * 4 and P["top"][4] == "ffffffff"
    assert P["top"][5:] == ["00000000"] * 3
    assert all(r == ".f000000" for r in P["left"])
    assert all(r == "000000f." for r in P["right"])
    assert P["bottom"][:3] == ["00000000"] * 3 and P["bottom"][3] == "ffffffff"
    assert P["bottom"][4:] == ["........"] * 4
    assert P["inside"] == ["00000000"] * 8
    assert P["top_left"][4][2:] == "ffffff" and col(P["top_left"], 1)[5:] == "fff"

    # the four corners are one shape turned: mirror and flip
    assert P["top_right"] == mirror(P["top_left"])
    assert P["bottom_left"] == vflip(P["top_left"])
    assert P["bottom_right"] == mirror(P["bottom_left"])
    assert P["tail_right"] == mirror(P["tail_left"])

    # joins: right column of A equals left column of B
    joins = [
        ("top_left", "top"), ("top", "top_right"),
        ("left", "inside"), ("inside", "right"),
        ("bottom_left", "bottom"), ("bottom", "bottom_right"),
    ]
    for a, b in joins:
        assert col(P[a], 7) == col(P[b], 0), a + " | " + b

    # joins: bottom row of the top pieces equals top row of the middle pieces
    assert P["top_left"][7] == P["left"][0]
    assert P["top"][7] == P["inside"][0]
    assert P["top_right"][7] == P["right"][0]

    # joins: top row of the bottom pieces and tails equals the middle pieces'
    assert P["bottom_left"][0] == P["left"][0]
    assert P["bottom"][0] == P["inside"][0]
    assert P["bottom_right"][0] == P["right"][0]
    assert P["tail_left"][0] == P["inside"][0]
    assert P["tail_right"][0] == P["inside"][0]

    # tails: rows 0..2 are plain inside; rows 0..3 join bottom_left and bottom
    for t in ("tail_left", "tail_right"):
        assert P[t][:3] == P["inside"][:3], t
        assert col(P[t], 0)[:4] == col(P["bottom_left"], 7)[:4], t + ": left join"
        assert col(P[t], 7)[:4] == col(P["bottom"], 0)[:4], t + ": right join"

    # tail_left: row 3 open between the two ends, a one-pixel tip on row 7 within columns 0..3
    tl = P["tail_left"]
    assert tl[3][0] == "f" and tl[3][6:] == "ff" and set(tl[3][1:6]) == {"0"}
    tip = [c for c in range(8) if tl[7][c] == "0"]
    assert len(tip) == 1 and tip[0] <= 3, tip


def pix_rows():
    rows = ["".join(PIECE[n][r] for n in ORDER) for r in range(8)]
    assert len(rows) == 8 and all(len(r) == 88 for r in rows)
    return rows


def balloon(cols, rows):
    """A balloon of cols x rows cells, put together as docs/clean_pack/balloon.md
    describes: the top row, middle rows down to the bottom outline, then the bottom
    row with the tail in its second cell (the bottom row starts 8 px above the last
    cell row, so the middle rows are cut just above its outline)."""
    W, H = 8 * cols, 8 * rows
    g = [["."] * W for _ in range(H)]

    def put(piece, x0, y0, stop=H):
        for r in range(8):
            y = y0 + r
            if not 0 <= y < min(stop, H):
                continue
            for c in range(8):
                x = x0 + c
                if 0 <= x < W and piece[r][c] != ".":
                    g[y][x] = piece[r][c]

    bottom_y = 8 * (rows - 1)
    stop = bottom_y + 3                      # the middle stops above the bottom outline (row 3)
    put(PIECE["top_left"], 0, 0)
    for k in range(1, cols - 1):
        put(PIECE["top"], 8 * k, 0)
    put(PIECE["top_right"], 8 * (cols - 1), 0)
    y = 8
    while y < stop:
        put(PIECE["left"], 0, y, stop)
        for k in range(1, cols - 1):
            put(PIECE["inside"], 8 * k, y, stop)
        put(PIECE["right"], 8 * (cols - 1), y, stop)
        y += 8
    put(PIECE["bottom_left"], 0, bottom_y)
    put(PIECE["tail_left"], 8, bottom_y)
    for k in range(2, cols - 1):
        put(PIECE["bottom"], 8 * k, bottom_y)
    put(PIECE["bottom_right"], 8 * (cols - 1), bottom_y)
    return g


def render(samples, path, scale=6, pad=4):
    from PIL import Image, ImageDraw
    back = (90, 160, 70)                     # mid green
    colour = {"0": (255, 255, 255), "f": (0, 0, 0)}
    width = sum(len(g[0]) for g in samples) + pad * (len(samples) + 1)
    height = max(len(g) for g in samples) + 2 * pad
    img = Image.new("RGB", (width * scale, height * scale), back)
    draw = ImageDraw.Draw(img)
    x0 = pad
    for g in samples:
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                if ch in colour:
                    X, Y = (x0 + x) * scale, (pad + y) * scale
                    draw.rectangle([X, Y, X + scale - 1, Y + scale - 1], fill=colour[ch])
        x0 += len(g[0]) + pad
    img.save(path)


def main():
    check_pieces()
    rows = pix_rows()
    path = os.path.join(HERE, "balloon.pix")
    with open(path, "w", newline="\n") as f:
        f.write("# speech balloon pieces, 88 x 8: 11 pieces of 8 x 8 side by side (piece n in columns 8n..8n+7)\n")
        f.write("# order: " + ", ".join(ORDER) + "\n")
        f.write("# generated by make_balloon.py\n")
        for r in rows:
            f.write(r + "\n")
    render([balloon(6, 3), balloon(10, 4)], os.path.join(HERE, "preview.png"))


if __name__ == "__main__":
    main()
