"""Writes the two mouse cursors as .pix files (see README.md).

    python make_cursors.py            # writes 0.pix and 1.pix next to this script
    python make_cursors.py --preview  # also writes preview.png (needs Pillow)

Only palette indices 0 (white), 15 / 'f' (black) and '.' (transparent) are used.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 0.pix: the pointer, 16 x 16, tip at (0, 0). Drawn by hand: a straight left
# edge, a 45-degree right edge, a flat shoulder and a tail that steps down and
# to the right one pixel per row.
POINTER = [
    "f...............",
    "ff..............",
    "f0f.............",
    "f00f............",
    "f000f...........",
    "f0000f..........",
    "f00000f.........",
    "f000000f........",
    "f0000000f.......",
    "f00000000f......",
    "f000000ffff.....",
    "f00ff00f........",
    "f0f..f00f.......",
    "ff....f00f......",
    ".......ff.......",
    "................",
]

# ---------------------------------------------------------------------------
# 1.pix: the busy cursor, 24 x 32: an hourglass with white caps, a white glass
# with a black outline, a little sand left in the top bulb, a falling stream
# and a heap in the bottom bulb.
W, H = 24, 32
CX = (W - 1) / 2.0          # 11.5: the glass is mirror-symmetric about it
CAP_TOP = (1, 3)            # rows of the top cap (outline, white, outline)
CAP_BOT = (28, 30)
CAP_X = (1, 22)
GLASS = (4, 27)             # rows of the glass between the caps
NECK = (GLASS[0] + GLASS[1]) / 2.0


def half_width(y):
    """Half the glass width at row y: narrow neck, round bulbs."""
    d = abs(y - NECK) / (NECK - GLASS[0])          # 0 at the neck, 1 at a cap
    return 1.0 + 8.0 * math.sin(d * math.pi / 2)


def hourglass():
    g = [["."] * W for _ in range(H)]

    # caps: black frame, white inside
    for top, bot in (CAP_TOP, CAP_BOT):
        for y in range(top, bot + 1):
            for x in range(CAP_X[0], CAP_X[1] + 1):
                edge = y in (top, bot) or x in CAP_X
                g[y][x] = "f" if edge else "0"

    # glass mask
    inside = set()
    for y in range(GLASS[0], GLASS[1] + 1):
        left = int(math.floor(CX - half_width(y) + 0.5))
        for x in range(left, W - left):
            inside.add((x, y))

    for (x, y) in inside:
        border = any((x + dx, y + dy) not in inside
                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        g[y][x] = "f" if border else "0"

    def interior(x, y):
        return (x, y) in inside and g[y][x] == "0"

    # sand left in the top bulb: a shallow layer just above the neck,
    # dipping in the middle where it drains
    for y in range(10, 16):
        for x in range(W):
            if interior(x, y):
                dip = abs(x - CX)
                if y >= 13 or (y == 12 and dip > 1):
                    g[y][x] = "f"

    # the stream through the neck and down the bottom bulb, 2 px wide,
    # broken once so the grains read as falling
    for y in range(16, 23):
        if y == 19:
            continue
        for x in (11, 12):
            if interior(x, y):
                g[y][x] = "f"

    # the heap in the bottom bulb: a mound peaking under the stream
    for y in range(21, 27):
        for x in range(W):
            if interior(x, y):
                top = 23 + abs(x - CX) * 0.6
                if y >= top:
                    g[y][x] = "f"

    return ["".join(r) for r in g]


def check(rows, w, h):
    assert len(rows) == h, (len(rows), h)
    for r in rows:
        assert len(r) == w, (r, w)
        assert set(r) <= set("0f."), r


def write(name, rows, comment):
    path = os.path.join(HERE, name)
    with open(path, "w", newline="\n") as f:
        for c in comment:
            f.write("# " + c + "\n")
        for r in rows:
            f.write(r + "\n")
    return path


def preview(sets, path, scale=6):
    from PIL import Image
    backs = [(80, 170, 60), (90, 60, 30), (170, 170, 170), (0, 0, 0)]
    cw = max(len(r[0]) for r in sets)
    ch = max(len(r) for r in sets)
    img = Image.new("RGB", ((cw + 4) * scale * len(sets), (ch + 4) * scale * len(backs)))
    px = img.load()
    for bi, back in enumerate(backs):
        for si, rows in enumerate(sets):
            ox = si * (cw + 4) * scale
            oy = bi * (ch + 4) * scale
            for y in range((ch + 4) * scale):
                for x in range((cw + 4) * scale):
                    cx, cy = x // scale - 2, y // scale - 2
                    col = back
                    if 0 <= cy < len(rows) and 0 <= cx < len(rows[0]):
                        c = rows[cy][cx]
                        if c == "0":
                            col = (255, 255, 255)
                        elif c == "f":
                            col = (0, 0, 0)
                    px[ox + x, oy + y] = col
    img.save(path)


def main():
    busy = hourglass()
    check(POINTER, 16, 16)
    check(busy, 24, 32)
    write("0.pix", POINTER, ["pointer, 16 x 16, hot spot = tip at (0, 0)",
                             "generated by make_cursors.py"])
    write("1.pix", busy, ["busy (hourglass), 24 x 32, top-left at the mouse",
                          "generated by make_cursors.py"])
    if "--preview" in sys.argv:
        preview([POINTER, busy], os.path.join(HERE, "preview.png"))


if __name__ == "__main__":
    main()
