#!/usr/bin/env python3
"""Makes the six clean-pack bitmap fonts (font0..font5: .pix glyph grid + .json metrics) and preview.png.

Run with plain `python make_fonts.py` (Pillow needed for the preview).  Options:
  --dump N [first last]   print the glyphs of font N as text (codes first..last, default 33..126)

All glyphs are drawn here, from scratch: every character is a *skeleton* (a few poly-lines, written as short strings,
in units of the glyph box) that is rasterised for each face with that face's pen (stem width), corner rounding,
anchor rows (cap top, x-height top, baseline, descender bottom) and ink width (taken from the advance table).
So the six faces share their letter shapes, like one family, and only the parameters differ:
  font0  9x15  mono bold sans (text-mode caption face)      font3  16x10  small serif, 1-pixel strokes
  font1  8x10  mono, lighter                                  font4  16x15  large semi-bold sans (2-pixel stems)
  font2  16x10 regular sans, 1-pixel strokes                  font5  16x11  bold sans (2-pixel stems)

Skeleton language (one glyph = strokes separated by '|'; a stroke = words separated by blanks):
  point  "x/y[~]":  x = fraction 0..1 of the ink width (pen-corrected), optional suffix L (round down), R (round up),
                    '<' / '>' (one pixel left / right);   y = anchor C (cap top) X (x-height top) B (baseline row)
                    D (descender bottom row), optional "+f" = move fraction f of the way to the next anchor
                    (C,X -> B; B -> D), then optional '_' / '^' (one pixel down / up) and 'v' (one dot-height down);
                    '~' = round this corner (cut it by the face's corner radius).
  flags  "c" closed, "d" dots (each point is a dot block), "D" i-dot (a dot kept clear of the x-height),
         "k1" thin pen (1 pixel), "r" is not used.
  glyph flags: n narrow (one stem wide), s wider minimum, F full advance wide.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Advances and header numbers, copied from the spec (docs/clean_pack/fonts.md); the build rejects any difference.
ADV = {
    0: [
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
        9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
        9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
        9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
        9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
        9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
    ],
    1: [
        0, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
    ],
    2: [
        3, 6, 6, 6, 6, 6, 6, 6, 6, 3, 6, 6, 6, 1, 6, 6,
        6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
        3, 4, 4, 6, 6, 9, 7, 3, 4, 4, 5, 6, 4, 4, 4, 4,
        6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 4, 4, 6, 6, 6, 6,
        10, 7, 7, 7, 7, 7, 6, 8, 7, 4, 6, 7, 6, 8, 7, 8,
        7, 8, 7, 7, 6, 7, 7, 9, 7, 7, 6, 4, 4, 4, 5, 6,
        4, 6, 6, 6, 6, 6, 4, 6, 6, 3, 3, 6, 3, 8, 6, 6,
        6, 6, 4, 6, 4, 6, 6, 7, 6, 6, 6, 4, 3, 4, 6, 6,
        7, 7, 7, 7, 7, 8, 7, 6, 6, 6, 6, 6, 6, 6, 6, 6,
        6, 6, 3, 3, 4, 4, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
        6, 4, 6, 6, 6, 4, 6, 6, 8, 8, 9, 4, 4, 6, 10, 8,
        7, 6, 6, 6, 6, 6, 5, 7, 9, 6, 4, 4, 4, 8, 9, 6,
        6, 4, 7, 6, 6, 6, 7, 6, 6, 10, 6, 7, 7, 8, 10, 9,
        6, 10, 4, 4, 3, 3, 6, 5, 6, 7, 3, 6, 4, 4, 6, 6,
        6, 4, 3, 4, 10, 7, 7, 7, 7, 7, 4, 4, 4, 4, 8, 8,
        8, 8, 7, 7, 7, 3, 4, 4, 4, 5, 4, 4, 4, 4, 4, 6,
    ],
    3: [
        2, 5, 5, 5, 5, 5, 5, 5, 0, 2, 5, 5, 5, 0, 5, 5,
        5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
        2, 3, 4, 5, 5, 7, 7, 2, 3, 3, 5, 5, 3, 3, 3, 3,
        5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 3, 3, 5, 5, 5, 4,
        8, 6, 6, 6, 6, 5, 5, 6, 6, 3, 4, 6, 5, 8, 6, 6,
        5, 6, 6, 5, 5, 6, 6, 8, 6, 6, 5, 3, 3, 3, 4, 5,
        3, 4, 5, 4, 4, 4, 3, 5, 5, 3, 3, 5, 3, 7, 5, 5,
        5, 4, 3, 4, 3, 4, 5, 6, 5, 5, 4, 4, 2, 4, 5, 5,
        6, 6, 6, 5, 6, 6, 6, 4, 4, 4, 4, 4, 4, 4, 4, 4,
        4, 4, 3, 3, 3, 3, 5, 5, 5, 5, 5, 5, 4, 4, 4, 4,
        5, 3, 5, 5, 5, 3, 4, 5, 7, 7, 8, 3, 3, 5, 8, 6,
        6, 5, 5, 5, 5, 5, 5, 6, 8, 5, 3, 2, 3, 7, 6, 5,
        4, 3, 6, 5, 5, 5, 6, 5, 5, 9, 5, 6, 6, 6, 8, 6,
        5, 9, 4, 4, 3, 3, 5, 4, 5, 6, 3, 5, 3, 3, 5, 5,
        5, 3, 3, 4, 9, 7, 6, 7, 6, 6, 3, 3, 3, 3, 6, 6,
        7, 6, 7, 7, 7, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 5,
    ],
    4: [
        0, 10, 10, 10, 10, 10, 10, 10, 10, 8, 10, 10, 10, 0, 10, 10,
        10, 11, 11, 9, 11, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
        4, 6, 7, 10, 7, 11, 10, 3, 5, 5, 7, 7, 4, 7, 4, 7,
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 4, 4, 6, 8, 6, 8,
        11, 8, 8, 8, 8, 7, 7, 8, 8, 6, 7, 9, 7, 12, 9, 8,
        8, 8, 8, 7, 6, 8, 8, 12, 8, 8, 8, 5, 7, 5, 8, 8,
        6, 8, 8, 7, 8, 8, 6, 8, 8, 4, 6, 8, 4, 12, 8, 8,
        8, 8, 6, 7, 6, 8, 8, 12, 8, 8, 8, 5, 5, 5, 8, 8,
        8, 8, 8, 7, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        8, 8, 6, 6, 6, 6, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        5, 6, 7, 9, 7, 7, 9, 9, 10, 10, 11, 5, 6, 9, 11, 9,
        14, 7, 6, 6, 10, 10, 8, 9, 10, 11, 6, 7, 7, 10, 12, 8,
        8, 6, 7, 12, 6, 10, 9, 9, 9, 14, 8, 8, 8, 8, 11, 12,
        6, 10, 7, 7, 4, 4, 7, 9, 8,
    ],
    5: [
        1, 10, 10, 10, 10, 10, 10, 10, 10, 4, 10, 10, 10, 1, 10, 10,
        10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
        4, 4, 5, 7, 7, 11, 9, 3, 5, 5, 5, 7, 4, 5, 4, 5,
        7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 4, 4, 7, 7, 7, 6,
        10, 8, 7, 8, 9, 6, 6, 9, 9, 4, 4, 8, 6, 10, 9, 10,
        7, 10, 7, 6, 8, 8, 8, 13, 7, 8, 7, 4, 6, 4, 7, 6,
        4, 6, 7, 6, 7, 6, 4, 6, 7, 4, 4, 6, 4, 10, 7, 7,
        7, 7, 5, 5, 5, 7, 6, 9, 6, 6, 6, 5, 7, 5, 7, 10,
        8, 8, 8, 6, 9, 10, 8, 6, 6, 6, 6, 6, 6, 6, 6, 6,
        6, 6, 4, 4, 4, 4, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
        7, 5, 7, 7, 7, 7, 8, 7, 11, 11, 12, 4, 5, 7, 9, 10,
        8, 7, 7, 7, 7, 7, 6, 8, 10, 7, 4, 5, 5, 10, 9, 7,
        6, 4, 7, 7, 7, 7, 8, 7, 6, 10, 4, 8, 8, 10, 11, 10,
        6, 11, 7, 7, 4, 4, 7, 8, 6, 8, 3, 7, 5, 4, 7, 7,
        7, 4, 4, 7, 11, 8, 6, 8, 6, 6, 4, 4, 4, 4, 10, 10,
        9, 10, 8, 8, 8, 4, 5, 5, 5, 4, 4, 5, 4, 5, 4, 4,
    ],
}
META = {0: {'first_index': 1}, 2: {'ascent': 8, 'missing_advance': 6}, 3: {'ascent': 8, 'missing_advance': 5}, 4: {'ascent': 12, 'missing_advance': 10}, 5: {'ascent': 9, 'missing_advance': 10}}

# ----------------------------------------------------------------------------------------------------------------
# face parameters
# ----------------------------------------------------------------------------------------------------------------
FACES = {
    0: dict(cw=9, ch=15, rows=8, n=127, C=2, X=5, B=10, D=12, mono=(1, 7), wide=(0, 8), wideset="MWmwTVXYZ@%&",
            cap=dict(kx=2, ky=1, r=2), low=dict(kx=2, ky=1, r=1), dot_cap=(2, 2), dot_low=(2, 2), serif=False, bs=4,
            gap=1),
    1: dict(cw=8, ch=10, rows=8, n=127, C=0, X=2, B=6, D=7, mono=(0, 7), wide=(0, 7), wideset="",
            cap=dict(kx=2, ky=1, r=1), low=dict(kx=1, ky=1, r=1), dot_cap=(2, 2), dot_low=(1, 1), serif=False, bs=3,
            gap=1),
    2: dict(cw=16, ch=10, rows=16, n=256, C=1, X=3, B=7, D=9, mono=None,
            cap=dict(kx=1, ky=1, r=1), low=dict(kx=1, ky=1, r=1), dot_cap=(1, 1), dot_low=(1, 1), serif=False, bs=3,
            gap=1),
    3: dict(cw=16, ch=10, rows=16, n=256, C=2, X=4, B=7, D=9, mono=None,
            cap=dict(kx=1, ky=1, r=1), low=dict(kx=1, ky=1, r=1), dot_cap=(1, 1), dot_low=(1, 1), serif=True, bs=2,
            gap=1),
    4: dict(cw=16, ch=15, rows=14, n=217, C=3, X=5, B=11, D=14, mono=None,
            cap=dict(kx=2, ky=1, r=2), low=dict(kx=2, ky=1, r=2), dot_cap=(2, 2), dot_low=(2, 2), serif=False, bs=4,
            gap=1),
    5: dict(cw=16, ch=11, rows=16, n=256, C=1, X=4, B=8, D=10, mono=None,
            cap=dict(kx=2, ky=1, r=1), low=dict(kx=2, ky=1, r=1), dot_cap=(2, 2), dot_low=(2, 2), serif=False, bs=3,
            gap=1),
}
for _i, _f in FACES.items():
    _f["id"] = _i

# ----------------------------------------------------------------------------------------------------------------
# skeletons
# ----------------------------------------------------------------------------------------------------------------
SRC = {}      # code -> (strokes string, flags)
SRC_MONO = {}  # overrides for the monospaced faces


def d(ch, strokes, flags="", mono=False):
    code = ch if isinstance(ch, int) else ord(ch)
    (SRC_MONO if mono else SRC)[code] = (strokes, flags)


def low_of(new, old):
    d(new, SRC[ord(old)][0].replace("/C", "/X"), SRC[ord(old)][1])


# --- capitals
d("A", "0/B .5L/C .5R/C 1/B | .17/C+.64 .83/C+.64")
d("B", "0/C 0/B | 0/C 1/C~ 1/C+.48~ 0/C+.48 | 0/C+.48 1/C+.48~ 1/B~ 0/B")
d("C", "1/C+.2 1/C~ 0/C~ 0/B~ 1/B~ 1/C+.8")
d("D", "0/C 0/B | 0/C 1/C~ 1/B~ 0/B")
d("E", "0/C 0/B | 0/C 1/C | 0/C+.5 .85/C+.5 | 0/B 1/B")
d("F", "0/C 0/B | 0/C 1/C | 0/C+.5 .8/C+.5")
d("G", "1/C+.2 1/C~ 0/C~ 0/B~ 1/B~ 1/C+.55 .5/C+.55")
d("H", "0/C 0/B | 1/C 1/B | 0/C+.5 1/C+.5")
d("I", ".5/C .5/B", "n")
d("J", "1/C 1/B~ 0/B~ 0/C+.72")
d("K", "0/C 0/B | 1/C 0/C+.55 | .3/C+.45 1/B")
d("L", "0/C 0/B 1/B")
d("M", "0/B 0/C .5L/C+.6 .5R/C+.6 1/C 1/B")
d("N", "0/B 0/C 1/B 1/C")
d("O", "c 0/C~ 1/C~ 1/B~ 0/B~")
d("P", "0/C 0/B | 0/C 1/C~ 1/C+.55~ 0/C+.55")
d("Q", "c 0/C~ 1/C~ 1/B~ 0/B~ | .55/C+.65 1/B")
d("R", "0/C 0/B | 0/C 1/C~ 1/C+.52~ 0/C+.52 | .45/C+.52 1/B")
d("S", "1/C+.2 1/C~ 0/C~ 0/C+.5~ 1/C+.5~ 1/B~ 0/B~ 0/C+.8")
d("T", "0/C 1/C | .5L/C .5L/B")
d("U", "0/C 0/B~ 1/B~ 1/C")
d("V", "0/C .5L/B .5R/B 1/C")
d("W", "0/C .25L/B .5/C+.45 .75R/B 1/C")
d("X", "0/C 1/B | 1/C 0/B")
d("Y", "0/C .5L/C+.5 | 1/C .5R/C+.5 | .5L/C+.5 .5L/B")
d("Z", "0/C 1/C 0/B 1/B")

# --- digits
d("0", "c 0/C~ 1/C~ 1/B~ 0/B~")
d("1", ".1/C+.25 .5L/C .5L/B | 0/B 1/B")
d("2", "0/C+.22 0/C~ 1/C~ 1/C+.4 0/B 1/B")
d("3", "0/C 1/C~ 1/C+.5~ .3/C+.5 | 1/C+.5 1/B~ 0/B | 0/C 0/C_ | 0/B 0/B^")
d("4", ".72/C 0/C+.68 1/C+.68 | .72/C .72/B")
d("5", "1/C 0/C 0/C+.45 | 0/C+.45 1/C+.45~ 1/B~ 0/B~ 0/B^")
d("6", "1/C 0/C~ 0/B~ 1/B~ 1/C+.5~ 0/C+.5")
d("7", "0/C 1/C .35/B")
d("8", "c 0/C~ 1/C~ 1/C+.5~ 0/C+.5~ | c 0/C+.5~ 1/C+.5~ 1/B~ 0/B~")
d("9", "0/B 1/B~ 1/C~ 0/C~ 0/C+.5~ 1/C+.5")

# --- ASCII symbols
d("!", ".5/C .5/C+.62 | d .5/B", "n")
d('"', "k1? 0/C 0/C+.3 | k1? 1/C 1/C+.3")
d("#", ".3/C .3/B | .7/C .7/B | 0/C+.3 1/C+.3 | 0/C+.7 1/C+.7")
d("$", SRC[ord("S")][0] + " | .5L/C^ .5L/B_")
d("%", "k1 c 0/C .3/C .3/C+.38 0/C+.38 | k1 c .7/C+.62 1/C+.62 1/B .7/B | 1/C 0/B")
d("&", "c .15/C~ .6/C~ .6/C+.4~ .15/C+.4~ | 1/B .3/C+.4 0/C+.65 0/B~ .75/B")
d("'", ".5/C .5/C+.3", "n")
d("(", "1/C 0/C+.25 0/C+.75 1/B")
d(")", "0/C 1/C+.25 1/C+.75 0/B")
d("*", ".5/C .5/C+.55 | 0/C+.12 1/C+.43 | 1/C+.12 0/C+.43")
d("+", "0/C+.5 1/C+.5 | .5L/C+.2 .5L/C+.8")
d(",", "d .5/B | .5/B_ .5</B__", "n")
d("-", ".05/X+.3 .95/X+.3")
d(".", "d .5/B", "n")
d("/", "1/C 0/B")
d(":", "d .5/B | d .5/X+.25", "n")
d(";", "d .5/X+.25 | d .5/B | .5/B_ .5</B__", "n")
d("<", "1/C+.15 0/C+.5 1/C+.85")
d("=", "0/C+.32 1/C+.32 | 0/C+.68 1/C+.68")
d(">", "0/C+.15 1/C+.5 0/C+.85")
d("?", "0/C+.18 0/C~ 1/C~ 1/C+.35 .5/C+.55 .5/C+.7 | d .5/B")
d("@", "c 0/C~ 1/C~ 1/B~ 0/B~ | c .3/C+.3 .75/C+.3 .75/C+.7 .3/C+.7 | .75/C+.3 .75/C+.75 1/C+.75")
d("[", "1/C 0/C 0/B 1/B")
d("\\", "0/C 1/B")
d("]", "0/C 1/C 1/B 0/B")
d("^", "0/C+.4 .5L/C .5R/C 1/C+.4")
d("_", "0/D 1/D", "F")
d("`", "0/C 1/C+.25", "s")
d("{", "1/C .5/C .5/C+.42 0/C+.5 .5/C+.58 .5/B 1/B")
d("|", ".5/C .5/D", "n")
d("}", "0/C .5/C .5/C+.42 1/C+.5 .5/C+.58 .5/B 0/B")
d("~", "0/C+.5 .3/C+.32 .7/C+.68 1/C+.5")

# --- lowercase
d("a", "0>/X 1/X~ 1/B | 1/X+.5 0/X+.5~ 0/B~ 1/B")
d("b", "0/C 0/B | 0/X 1/X~ 1/B~ 0/B")
d("c", "1/X 0/X~ 0/B~ 1/B")
d("d", "1/C 1/B | 1/X 0/X~ 0/B~ 1/B")
d("e", "0/X+.5 1/X+.5 1/X~ 0/X~ 0/B~ 1/B")
d("f", "1/C .4/C~ .4/B | 0/X 1/X", "s")
d("g", "1/X 0/X~ 0/B~ 1/B | 1/X 1/D~ 0/D")
d("h", "0/C 0/B | 0/X 1/X~ 1/B")
d("i", "D .5/C | .5/X .5/B", "n")
d("j", "D 1/C | 1/X 1/D~ 0/D")
d("k", "0/C 0/B | 1/X 0/X+.62 | .3/X+.5 1/B")
d("l", ".5/C .5/B", "n")
d("m", "0/X 0/B | 0/X .5/X~ .5/B | .5/X 1/X~ 1/B")
d("n", "0/X 0/B | 0/X 1/X~ 1/B")
low_of("o", "O")
d("p", "0/X 0/D | 0/X 1/X~ 1/B~ 0/B")
d("q", "1/X 1/D | 1/X 0/X~ 0/B~ 1/B")
d("r", "0/X 0/B | 0/X 1/X~ 1/X+.35", "s")
d("s", "1/X 0/X~ 0/X+.5~ 1/X+.5~ 1/B~ 0/B")
d("t", ".4/C+.15 .4/B~ 1/B | 0/X 1/X", "s")
d("u", "0/X 0/B~ 1/B | 1/X 1/B")
low_of("v", "V")
low_of("w", "W")
low_of("x", "X")
d("y", "0/X .4/B | 1/X .08/D")
low_of("z", "Z")

# --- extras in the Mac Roman positions (fonts 2..5)
d(165, "BULLET", "n")
d(169, "c 0/C~ 1/C~ 1/B~ 0/B~ | k1 .72/C+.3 .3/C+.3 .3/C+.7 .72/C+.7")
d(170, "k1 0/C .3/C | k1 .15L/C .15L/C+.5 | k1 .55/C+.5 .55/C .775/C+.3 1/C 1/C+.5")
d(201, "d 0/B .5/B 1/B")
d(208, "0/X+.3 1/X+.3", "F")
d(209, "0/X+.3 1/X+.3", "F")
d(211, "k1? d 0/C 1/C | k1? 0/Cv 0/Cv_ | k1? 1/Cv 1/Cv_")
d(213, "d .5/C | .5/Cv .5/Cv_", "n")
SRC[210] = ("FLIP211", "")
SRC[212] = ("FLIP213", "n")

# --- monospaced overrides (text-mode feel: foot bars on i, j, l, I; slashed zero)
d("I", ".2/C .8/C | .5L/C .5L/B | .2/B .8/B", mono=True)
d("i", "D .5L/C | .15/X .5L/X .5L/B | .15/B .85/B", mono=True)
d("j", "D .65L/C | .2/X .65L/X .65L/D~ .1/D", mono=True)
d("l", ".15/C .5L/C .5L/B | .15/B .85/B", mono=True)
d("0", "c 0/C~ 1/C~ 1/B~ 0/B~ | k1 .25/C+.78 .75/C+.22", mono=True)
d('"', ".2/C .2/C+.3 | .8/C .8/C+.3", mono=True)

PT = re.compile(r"^(\d*\.?\d+)([LR<>]*)/([CXBD])(\+\d*\.?\d+)?([_^v]*)(~?)$")
_parsed = {}


def parse_strokes(s):
    if s in _parsed:
        return _parsed[s]
    out = []
    for st in s.split("|"):
        flags, pts = set(), []
        for t in st.split():
            if "/" not in t:
                flags.add(t)
                continue
            m = PT.match(t)
            assert m, "bad point %r in %r" % (t, s)
            frac = float(m.group(4)[1:]) if m.group(4) else 0.0
            pts.append((float(m.group(1)), m.group(2), m.group(3), frac, m.group(5), bool(m.group(6))))
        out.append((flags, pts))
    _parsed[s] = out
    return out


# ----------------------------------------------------------------------------------------------------------------
# rasteriser
# ----------------------------------------------------------------------------------------------------------------
def yv(F, anchor, frac, mods, ph, dh):
    rows = {"C": F["C"], "X": F["X"], "B": F["B"] - (ph - 1), "D": F["D"] - (ph - 1)}
    nxt = {"C": "B", "X": "B", "B": "D", "D": "D"}
    a = rows[anchor]
    b = rows[nxt[anchor]]
    y = int(math.floor(a + frac * (b - a) + 0.5))
    for m in mods:
        y += {"_": 1, "^": -1, "v": dh}[m]
    return max(y, 0)


def xv(lb, W, kpen, u, mods):
    v = u * max(W - kpen, 0)
    if "L" in mods:
        x = int(math.floor(v + 1e-9))
    elif "R" in mods:
        x = int(math.ceil(v - 1e-9))
    else:
        x = int(math.floor(v + 0.5))
    x += mods.count(">") - mods.count("<")
    return lb + x


def stamp(px, x, y, w, h):
    for xx in range(x, x + w):
        for yy in range(y, y + h):
            px.add((xx, yy))


def line(px, p, q, kx, ky):
    (x0, y0), (x1, y1) = p, q
    dx, dy = x1 - x0, y1 - y0
    pw, ph = (kx, 1) if (dx == 0 or (dy != 0 and abs(dy) >= abs(dx))) else (1, ky)
    n = max(abs(dx), abs(dy))
    if n == 0:
        stamp(px, x0, y0, pw, ph)
        return
    for i in range(n + 1):
        x = x0 + int(math.floor(dx * i / n + 0.5))
        y = y0 + int(math.floor(dy * i / n + 0.5))
        stamp(px, x, y, pw, ph)


def sgn(v):
    return (v > 0) - (v < 0)


def chamfer(P, rounded, closed, r):
    n = len(P)
    out = []

    def rnd(j):
        return rounded[j] and (closed or 0 < j < n - 1)

    for i in range(n):
        v = P[i]
        if rounded[i] and r > 0 and (closed or 0 < i < n - 1):
            ia, ib = (i - 1) % n, (i + 1) % n
            a, b = P[ia], P[ib]
            da = (a[0] - v[0], a[1] - v[1])
            db = (b[0] - v[0], b[1] - v[1])
            if (da[0] == 0 or da[1] == 0) and (db[0] == 0 or db[1] == 0) and da != (0, 0) and db != (0, 0):
                l1, l2 = abs(da[0]) + abs(da[1]), abs(db[0]) + abs(db[1])
                c1 = l1 // 2 if rnd(ia) else l1
                c2 = l2 // 2 if rnd(ib) else l2
                rr = min(r, c1, c2)
                if rr > 0:
                    out.append((v[0] + sgn(da[0]) * rr, v[1] + sgn(da[1]) * rr))
                    out.append((v[0] + sgn(db[0]) * rr, v[1] + sgn(db[1]) * rr))
                    continue
        out.append(v)
    return out


def draw_stroke(F, cls, flags, pts, lb, W, px):
    P = F[cls]
    kx, ky, r = P["kx"], P["ky"], P["r"]
    dw, dh = F["dot_" + cls]
    if "k1" in flags or ("k1?" in flags and W < 3 * kx + 1):  # k1? = thin pen only where the glyph is too narrow
        kx = ky = dw = dh = 1
    if "d" in flags or "D" in flags:
        for (u, xm, an, fr, ym, rd) in pts:
            x = xv(lb, W, dw, u, xm)
            y = yv(F, an, fr, ym, dh, dh)
            if "D" in flags:
                y = min(y, F["X"] - 1 - dh)
            stamp(px, x, y, dw, dh)
        return
    xs = [xv(lb, W, kx, p[0], p[1]) for p in pts]
    ph = ky if len(set(xs)) > 1 else 1
    ys = [yv(F, p[2], p[3], p[4], ph, dh) for p in pts]
    P2 = list(zip(xs, ys))
    rounded = [p[5] for p in pts]
    closed = "c" in flags
    P3 = chamfer(P2, rounded, closed, r) if any(rounded) else P2
    if len(P3) == 1:
        stamp(px, P3[0][0], P3[0][1], kx, ky)
        return
    m = len(P3)
    for i in range(m - 1):
        line(px, P3[i], P3[i + 1], kx, ky)
    if closed:
        line(px, P3[-1], P3[0], kx, ky)


def cls_of(code):
    return "low" if 97 <= code <= 122 else "cap"


def box(F, code, flags, has_dot, cls):
    adv = ADV[F["id"]][code]
    kx = F[cls]["kx"]
    dw = F["dot_" + cls][0]
    letter = chr(code).isalpha() if code < 128 else False
    if F["mono"]:
        lb0, W0 = F["wide"] if (code < 128 and chr(code) in F["wideset"]) else F["mono"]
        if "n" in flags:
            W = min(max(kx, dw if has_dot else 0), W0)
            return lb0 + (W0 - W) // 2, W
        if "F" in flags:
            return F["wide"][0], F["wide"][1]
        return lb0, W0
    if "n" in flags:
        if F["serif"] and letter:
            W = min(adv, 3)
        else:
            W = max(kx, dw if has_dot else 0)
            W = min(W, adv)
        return (adv - W) // 2, W
    if "F" in flags:
        return 0, adv
    W = adv - F["gap"]
    W = max(W, kx + (2 if "s" in flags else 1))
    return 0, W


def add_serifs(F, px, code, lb, W):
    """Small serifs for the serif face: feet / top flags on the vertical stems of the letters that have them."""
    if not (code < 128 and chr(code).isalpha()):
        return
    c = chr(code)
    upper = c.isupper()
    if upper:
        if c in "TYVAXWZOQCGSU":
            return
        feet, tops = True, True
    else:
        feet, tops = c in "ilrpj", c in "ilbhkmnpruj"
    cols = {}
    for (x, y) in px:
        cols.setdefault(x, []).append(y)
    add = set()
    for x, ys in cols.items():
        ys.sort()
        runs, s = [], ys[0]
        for a, b in zip(ys, ys[1:] + [None]):
            if b is None or b != a + 1:
                runs.append((s, a))
                if b is not None:
                    s = b
        for (r0, r1) in runs:
            if r1 - r0 < 2:
                continue
            if feet and r1 in (F["B"], F["D"]):
                for nx in (x - 1, x + 1):
                    add.add((nx, r1))
            if tops and r0 in (F["C"], F["X"]):
                if upper:
                    for nx in (x - 1, x + 1):
                        add.add((nx, r0))
                else:
                    add.add((x - 1, r0))
    for (x, y) in add:
        if lb <= x <= lb + W - 1 and (x, y) not in px:
            px.add((x, y))


def flip(px):
    xs = [p[0] for p in px]
    ys = [p[1] for p in px]
    a, b, c, e = min(xs), max(xs), min(ys), max(ys)
    return {(a + b - x, c + e - y) for (x, y) in px}


def special(F, code, lb, W):
    px = set()
    if code == 165:  # bullet
        bs = F["bs"]
        h = F["B"] - F["C"] + 1
        top = F["C"] + (h - bs) // 2
        x0 = lb + (W - bs) // 2
        for i in range(bs):
            for j in range(bs):
                if bs >= 4 and i in (0, bs - 1) and j in (0, bs - 1):
                    continue
                px.add((x0 + i, top + j))
    return px


# ----------------------------------------------------------------------------------------------------------------
# font 3, hand-drawn (2026-11-01 polish): the skeleton pass made it cramped, so every ASCII glyph of font 3 is drawn
# here pixel by pixel.  A glyph is its first row (cell row; caps start at row 2, ascenders at row 1, x-height at row 4)
# and its rows as text ('#' ink); the ink is at most (advance - 1) wide where the shape allows, so there is a 1-pixel
# gap between neighbours.  Serifs are kept to flags on the stems (feet / top flags) that do not close the counters.
# ----------------------------------------------------------------------------------------------------------------
HAND3 = {}


def h3(ch, top, art, left=0):
    rows = [r.strip() for r in art.strip().splitlines()]
    HAND3[ch if isinstance(ch, int) else ord(ch)] = (top, rows, left)


# capitals (rows 2..7)
h3("A", 2, """
..#..
.#.#.
.#.#.
#####
#...#
##.##""")
h3("B", 2, """
####.
.#..#
.###.
.#..#
.#..#
####.""")
h3("C", 2, """
.###.
#...#
#....
#....
#...#
.###.""")
h3("D", 2, """
####.
.#..#
.#..#
.#..#
.#..#
####.""")
h3("E", 2, """
####
.#..
.##.
.#..
.#..
####""")
h3("F", 2, """
####
.#..
.##.
.#..
.#..
###.""")
h3("G", 2, """
.###.
#...#
#....
#.###
#...#
.###.""")
h3("H", 2, """
##.##
.#.#.
.###.
.#.#.
.#.#.
##.##""")
h3("I", 2, """
##
.#
.#
.#
.#
##""")
h3("J", 2, """
.##
..#
..#
..#
#.#
.#.""")
h3("K", 2, """
##..#
.#.#.
.##..
.#.#.
.#..#
##..#""")
h3("L", 2, """
##..
.#..
.#..
.#..
.#..
####""")
h3("M", 2, """
##...##
.##.##.
.#.#.#.
.#.#.#.
.#...#.
##...##""")
h3("N", 2, """
##..#
.##.#
.#.##
.#..#
.#..#
##..#""")
h3("O", 2, """
.###.
#...#
#...#
#...#
#...#
.###.""")
h3("P", 2, """
###.
.#.#
.#.#
.##.
.#..
##..""")
h3("Q", 2, """
.###.
#...#
#...#
#.#.#
#..#.
.##.#""")
h3("R", 2, """
####.
.#..#
.#..#
.###.
.#.#.
##..#""")
h3("S", 2, """
.###
#...
.##.
...#
...#
###.""")
h3("T", 2, """
####
.##.
.##.
.##.
.##.
.##.""")
h3("U", 2, """
#...#
#...#
#...#
#...#
#...#
.###.""")
h3("V", 2, """
#...#
#...#
.#.#.
.#.#.
..#..
..#..""")
h3("W", 2, """
#.....#
#..#..#
#..#..#
.#.#.#.
.#...#.
..#.#..""")
h3("X", 2, """
##.##
.#.#.
..#..
.#.#.
.#.#.
##.##""")
h3("Y", 2, """
#...#
.#.#.
..#..
..#..
..#..
.###.""")
h3("Z", 2, """
####
...#
..#.
.#..
#...
####""")
# digits (rows 2..7, 4 wide in the 5 advance)
h3("0", 2, """
.##.
#..#
#..#
#..#
#..#
.##.""")
h3("1", 2, """
.#..
##..
.#..
.#..
.#..
###.""")
h3("2", 2, """
.##.
#..#
...#
..#.
.#..
####""")
h3("3", 2, """
###.
...#
.##.
...#
#..#
.##.""")
h3("4", 2, """
...#
..##
.#.#
#..#
####
...#""")
h3("5", 2, """
####
#...
###.
...#
#..#
.##.""")
h3("6", 2, """
.##.
#...
###.
#..#
#..#
.##.""")
h3("7", 2, """
####
...#
..#.
..#.
.#..
.#..""")
h3("8", 2, """
.##.
#..#
.##.
#..#
#..#
.##.""")
h3("9", 2, """
.##.
#..#
#..#
.###
...#
.##.""")
# lowercase (x-height rows 4..7, ascenders from row 1, descenders to row 9)
h3("a", 4, """
.##
#.#
#.#
.##""")
h3("b", 1, """
##..
.#..
.#..
.##.
.#.#
.#.#
.##.""")
h3("c", 4, """
.##
#..
#..
.##""")
h3("d", 1, """
.##
..#
..#
.##
#.#
#.#
.##""")
h3("e", 4, """
.##
#.#
###
.##""")
h3("f", 1, """
.#
#.
#.
##
#.
#.
#.""")
h3("g", 4, """
.###
#..#
#..#
.###
...#
.##.""")
h3("h", 1, """
##..
.#..
.#..
.##.
.#.#
.#.#
.#.#""")
h3("i", 2, """
.#
..
.#
.#
.#
.#""")
h3("j", 2, """
.#
..
.#
.#
.#
.#
.#
#.""")
h3("k", 1, """
##..
.#..
.#..
.#.#
.##.
.#.#
.#.#""")
h3("l", 1, """
##
.#
.#
.#
.#
.#
.#""")
h3("m", 4, """
#####.
.#.#.#
.#.#.#
.#.#.#""")
h3("n", 4, """
###.
.#.#
.#.#
.#.#""")
h3("o", 4, """
.##.
#..#
#..#
.##.""")
h3("p", 4, """
###.
.#.#
.#.#
.##.
.#..
###.""")
h3("q", 4, """
.##
#.#
#.#
.##
..#
..#""")
h3("r", 4, """
##
#.
#.
#.""")
h3("s", 4, """
.##
#..
..#
##.""")
h3("t", 2, """
#.
#.
##
#.
#.
.#""")
h3("u", 4, """
#.#
#.#
#.#
.##""")
h3("v", 4, """
#..#
#..#
.##.
.##.""")
h3("w", 4, """
#...#
#...#
#.#.#
.#.#.""")
h3("x", 4, """
#..#
.##.
.##.
#..#""")
h3("y", 4, """
#..#
#..#
.###
...#
..#.
##..""")
h3("z", 4, """
###
..#
.#.
###""")
# punctuation and symbols
h3("!", 2, """
#
#
#
#
.
#""", 1)
h3('"', 2, """
#.#
#.#""")
h3("#", 2, """
.#.#
.#.#
####
.#.#
####
.#.#""")
h3("$", 1, """
..#.
.###
#.#.
.##.
..##
#.#.
###.
..#.""")
h3("%", 2, """
###..#
#.#.#.
####..
..####
.#.#.#
#..###""")
h3("&", 2, """
.##...
#..#..
.##...
#.##.#
#..##.
.##.##""")
h3("'", 2, """
#
#""")
h3("(", 1, """
.#
#.
#.
#.
#.
#.
#.
#.
.#""")
h3(")", 1, """
#.
.#
.#
.#
.#
.#
.#
.#
#.""")
h3("*", 2, """
#.#
.#.
###
.#.
#.#""", 1)
h3("+", 4, """
.#.
###
.#.""", 1)
h3(",", 7, """
.#
#.""")
h3("-", 5, """
##""")
h3(".", 7, """
#""", 1)
h3("/", 2, """
.#
.#
.#
#.
#.
#.""")
h3(":", 4, """
#
.
.
#""", 1)
h3(";", 4, """
.#
..
..
.#
#.""")
h3("<", 3, """
..#
.#.
#..
.#.
..#""", 1)
h3("=", 4, """
####
....
####""")
h3(">", 3, """
#..
.#.
..#
.#.
#..""", 1)
h3("?", 2, """
.#.
#.#
..#
.#.
...
.#.""")
h3("@", 2, """
.#####.
#.....#
#.###.#
#.#.#.#
#.####.
.#####.""")
h3("[", 1, """
##
#.
#.
#.
#.
#.
#.
#.
##""")
h3("\\", 2, """
#.
#.
#.
.#
.#
.#""")
h3("]", 1, """
##
.#
.#
.#
.#
.#
.#
.#
##""")
h3("^", 2, """
.#.
#.#""")
h3("_", 9, """
#####""")
h3("`", 2, """
#.
.#""")
h3("{", 1, """
.##
.#.
.#.
.#.
#..
.#.
.#.
.#.
.##""")
h3("|", 1, """
#
#
#
#
#
#
#
#
#""")
h3("}", 1, """
##.
.#.
.#.
.#.
..#
.#.
.#.
.#.
##.""")
h3("~", 4, """
.#.#
#.#.""")
# Mac Roman symbols that were irregular
h3(201, 7, """
#..#..#""", 1)
h3(208, 5, """
####""")
h3(209, 5, """
########""")


def render(F, code):
    """Ink pixels (set of (x, y) in cell coordinates) of one character."""
    fid = F["id"]
    if fid == 3 and code in HAND3:
        top, rows, left = HAND3[code]
        px = set()
        for j, r in enumerate(rows):
            for i, c in enumerate(r):
                if c == "#":
                    px.add((left + i, top + j))
        return px
    if fid in (0, 1) and code == 16:  # solid right-pointing triangle (the menus' check mark)
        x0, y0 = (1, 3) if fid == 0 else (0, 0)
        px = set()
        for j, w in enumerate([1, 2, 3, 4, 3, 2, 1]):
            for i in range(w):
                px.add((x0 + i, y0 + j))
        return px
    if code in (32, 160) or code >= F["n"]:
        return set()
    src = SRC_MONO.get(code) if F["mono"] and code in SRC_MONO else SRC.get(code)
    if src is None or (code > 126 and F["mono"]):
        return set()
    s, flags = src
    if s.startswith("FLIP"):
        return flip(render(F, int(s[4:])))
    cls = cls_of(code)
    strokes = parse_strokes(s) if s != "BULLET" else []
    has_dot = any(("d" in f or "D" in f) for f, _ in strokes)
    lb, W = box(F, code, flags, has_dot, cls)
    if s == "BULLET":
        return special(F, code, lb, W)
    px = set()
    for f, pts in strokes:
        draw_stroke(F, cls, f, pts, lb, W, px)
    if F["serif"]:
        add_serifs(F, px, code, lb, W)
    return px


def render_font(fid):
    F = FACES[fid]
    return {c: render(F, c) for c in range(F["n"])}


# ----------------------------------------------------------------------------------------------------------------
# files
# ----------------------------------------------------------------------------------------------------------------
def picture_lines(fid, glyphs):
    F = FACES[fid]
    cw, ch, rows = F["cw"], F["ch"], F["rows"]
    grid = [["."] * (16 * cw) for _ in range(rows * ch)]
    for code, px in glyphs.items():
        cx, cy = (code % 16) * cw, (code // 16) * ch
        for (x, y) in px:
            assert 0 <= x < cw and 0 <= y < ch, "ink outside the cell: font %d code %d (%d,%d)" % (fid, code, x, y)
            grid[cy + y][cx + x] = "f"
    return ["".join(r) for r in grid]


DESCR = {
    0: "bold monospaced sans (text-mode caption face), 9 x 15 cells, advance 9",
    1: "plain monospaced sans (PC symbol face), 8 x 10 cells, advance 8",
    2: "regular proportional sans, 1-pixel strokes, 16 x 10 cells",
    3: "small proportional serif, 1-pixel strokes, 16 x 10 cells",
    4: "large semi-bold proportional sans, 2-pixel stems, 16 x 15 cells",
    5: "bold proportional sans, 2-pixel stems, 16 x 11 cells",
}


def write_font(fid, glyphs):
    F = FACES[fid]
    lines = picture_lines(fid, glyphs)
    with open(os.path.join(HERE, "font%d.pix" % fid), "w", newline="\n") as fh:
        fh.write("# font%d: %s\n" % (fid, DESCR[fid]))
        fh.write("# glyph grid, 16 cells across, cell %d x %d, character code c at column c%%16 row c//16; f = ink\n"
                 % (F["cw"], F["ch"]))
        fh.write("# written by make_fonts.py (original design, drawn from skeletons; see README.md)\n")
        fh.write("\n".join(lines) + "\n")
    meta = META.get(fid, {})
    adv = ADV[fid]
    out = "{\n"
    for k in ("first_index", "ascent", "missing_advance"):
        if k in meta:
            out += '  "%s": %d,\n' % (k, meta[k])
    out += '  "advances": [\n'
    rows = []
    for i in range(0, len(adv), 16):
        rows.append("    " + ", ".join("%2d" % v for v in adv[i:i + 16]))
    out += ",\n".join(rows) + "\n  ]\n}\n"
    json.loads(out)
    with open(os.path.join(HERE, "font%d.json" % fid), "w", newline="\n") as fh:
        fh.write(out)


# ----------------------------------------------------------------------------------------------------------------
# self-check (reads the files back)
# ----------------------------------------------------------------------------------------------------------------
REQ = list(range(33, 127))
EXTRA_REQ = [165, 169, 170, 201, 208, 209, 210, 211, 212, 213]
CAPS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
XH = "acemnorsuvwxz"
ASC = "bdfhkl"
DESC = "gjpqy"


def check():
    problems = []
    report = []

    def bad(fid, msg):
        problems.append("font%d: %s" % (fid, msg))

    for fid, F in FACES.items():
        cw, ch, rows = F["cw"], F["ch"], F["rows"]
        pix = [l for l in open(os.path.join(HERE, "font%d.pix" % fid)).read().splitlines() if not l.startswith("#")]
        pix = [l for l in pix if l != ""]
        js = json.load(open(os.path.join(HERE, "font%d.json" % fid)))
        adv = js["advances"]
        if adv != ADV[fid] or len(adv) != F["n"]:
            bad(fid, "advances differ from the table or have the wrong length")
        if len(pix) != rows * ch or any(len(l) != 16 * cw for l in pix):
            bad(fid, "picture size is %d x %d, expected %d x %d" % (len(pix[0]) if pix else 0, len(pix), 16 * cw, rows * ch))
            continue
        if set("".join(pix)) - set("f."):
            bad(fid, "characters other than f and . in the picture")
        expect_meta = META.get(fid, {})
        for k, v in expect_meta.items():
            if js.get(k) != v:
                bad(fid, "metric %s differs" % k)
        ink = {}
        for code in range(rows * 16):
            cx, cy = (code % 16) * cw, (code // 16) * ch
            pts = [(x, y) for y in range(ch) for x in range(cw) if pix[cy + y][cx + x] == "f"]
            if pts:
                ink[code] = pts
        for code in range(F["n"], rows * 16):
            if code in ink:
                bad(fid, "code %d is outside the character range but has ink" % code)
        req = list(REQ) + ([16] if fid in (0, 1) else []) + (EXTRA_REQ if fid >= 2 else [])
        for code in req:
            if code not in ink:
                bad(fid, "required code %d (%r) has no ink" % (code, chr(code) if code < 256 else code))
        C, X, B, D = F["C"], F["X"], F["B"], F["D"]
        for code, pts in ink.items():
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            a = adv[code]
            if min(xs) < 0 or max(xs) >= cw or min(ys) < 0 or max(ys) >= ch:
                bad(fid, "code %d ink outside the cell" % code)
            if a > 0 and (max(xs) + 1 > a + 2):
                bad(fid, "code %d ink right edge %d exceeds advance %d by more than 2" % (code, max(xs) + 1, a))
            if fid == 0 and code != 16 and max(xs) > 7:
                bad(fid, "code %d has ink in column %d" % (code, max(xs)))
            if fid == 1 and code != 16 and max(xs) > 6 and chr(code) not in "_":
                bad(fid, "code %d has ink in column %d" % (code, max(xs)))
            if fid == 0 and code != 16 and min(ys) < 2 and chr(code) not in "$[]()|{}'\"`^*":
                bad(fid, "code %d has ink above row 2" % code)
            if fid >= 2 and min(ys) == 0 and not (code < 128 and chr(code) in "$"):
                bad(fid, "code %d has ink in row 0" % code) if fid == 2 else None
            if code < 128:
                c = chr(code)
                if c in CAPS:
                    if not (C - 1 <= min(ys) <= C + 1 and B - 1 <= max(ys) <= B + 1):
                        bad(fid, "%r rows %d..%d, expected %d..%d" % (c, min(ys), max(ys), C, B))
                elif c in XH:
                    if not (X - 1 <= min(ys) <= X + 1 and B - 1 <= max(ys) <= B + 1):
                        bad(fid, "%r rows %d..%d, expected %d..%d" % (c, min(ys), max(ys), X, B))
                elif c in ASC:
                    if not (C - 1 <= min(ys) <= C + 1 and B - 1 <= max(ys) <= B + 1):
                        bad(fid, "%r rows %d..%d, expected %d..%d" % (c, min(ys), max(ys), C, B))
                elif c in DESC:
                    if not (D - 1 <= max(ys) <= D + 1):
                        bad(fid, "%r bottom row %d, expected %d" % (c, max(ys), D))
                    if c != "j" and not (X - 1 <= min(ys) <= X + 1):
                        bad(fid, "%r top row %d, expected %d" % (c, min(ys), X))
                elif c in "it":
                    if not (B - 1 <= max(ys) <= B + 1):
                        bad(fid, "%r bottom row %d, expected %d" % (c, max(ys), B))
        # summary line
        def hh(c):
            ys = [p[1] for p in ink[ord(c)]]
            return "%s:%d..%d" % (c, min(ys), max(ys))
        report.append("font%d  %dx%d px, cell %dx%d, %d inked codes; rows  %s  %s  %s  %s; max ink col %d"
                      % (fid, 16 * cw, rows * ch, cw, ch, len(ink), hh("H"), hh("x"), hh("d"), hh("g"),
                         max(p[0] for pts in ink.values() for p in pts)))
    return problems, report


# ----------------------------------------------------------------------------------------------------------------
# preview
# ----------------------------------------------------------------------------------------------------------------
PANGRAM = "The quick brown fox jumps over the lazy dog 0123456789"
PUNCT = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
CAPS_LINE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOW_LINE = "abcdefghijklmnopqrstuvwxyz"
MAC = {"•": 165, "©": 169, "™": 170, "…": 201, "–": 208, "—": 209,
       "“": 210, "”": 211, "‘": 212, "’": 213}


def text_width(fid, text):
    return sum(ADV[fid][MAC.get(c, ord(c))] for c in text)


def draw_text(img_px, fid, glyphs, text, x, y, scale, color=(0, 0, 0)):
    F = FACES[fid]
    pen = x
    for c in text:
        code = MAC.get(c, ord(c))
        for (gx, gy) in glyphs.get(code, ()):
            for sx in range(scale):
                for sy in range(scale):
                    img_px[pen + gx * scale + sx, y + gy * scale + sy] = color
        pen += ADV[fid][code] * scale


def preview(all_glyphs):
    from PIL import Image, ImageDraw
    lines_for = {}
    for fid in FACES:
        ls = [PANGRAM, PUNCT, CAPS_LINE, LOW_LINE]
        if fid >= 2:
            ls[3] = LOW_LINE + " • © ™ … – — “quoted” ‘single’"
        lines_for[fid] = ls
    width = 20
    for fid, ls in lines_for.items():
        for l in ls:
            width = max(width, text_width(fid, l) * 3 + 24)
    height = 8
    layout = []
    for fid, ls in lines_for.items():
        F = FACES[fid]
        layout.append((fid, height))
        height += 14
        for scale in (1, 3):
            height += len(ls) * (F["ch"] * scale + 3) + 4
        height += 8
    img = Image.new("RGB", (width, height), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    px = img.load()
    for fid, y0 in layout:
        F = FACES[fid]
        dr.text((6, y0), "font%d  %s" % (fid, DESCR[fid]), fill=(160, 0, 0))
        y = y0 + 14
        for scale in (1, 3):
            for l in lines_for[fid]:
                draw_text(px, fid, all_glyphs[fid], l, 10, y, scale)
                y += F["ch"] * scale + 3
            y += 4
        dr.line([(0, y + 2), (width, y + 2)], fill=(200, 200, 200))
    img.save(os.path.join(HERE, "preview.png"))


# ----------------------------------------------------------------------------------------------------------------
def dump(fid, first=33, last=126, per_line=14):
    F = FACES[fid]
    g = render_font(fid)
    rows = range(0, F["ch"])
    codes = [c for c in range(first, last + 1)]
    for i in range(0, len(codes), per_line):
        chunk = codes[i:i + per_line]
        wid = {}
        for c in chunk:
            xs = [p[0] for p in g[c]] or [0]
            wid[c] = max(max(xs) + 1, ADV[fid][c], 1) + 1
        print("      " + "".join(("%d:%s" % (c, chr(c) if 32 < c < 127 else "?")).ljust(wid[c]) for c in chunk))
        used = [p[1] for c in chunk for p in g[c]]
        if not used:
            continue
        for y in range(min(used), max(used) + 1):
            tag = "C" if y == F["C"] else "X" if y == F["X"] else "B" if y == F["B"] else "D" if y == F["D"] else " "
            print("%2d %s  " % (y, tag) + "".join(
                "".join("#" if (x, y) in g[c] else "." for x in range(wid[c] - 1)) + " " for c in chunk))
        print()


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--dump":
        a = [int(v) for v in sys.argv[2:]]
        dump(a[0], *(a[1:3] if len(a) > 2 else ()))
        return
    all_glyphs = {}
    for fid in FACES:
        all_glyphs[fid] = render_font(fid)
        write_font(fid, all_glyphs[fid])
    problems, report = check()
    print("self-check:")
    for r in report:
        print("  " + r)
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print("  all checks passed (sizes, characters, advances, ink inside cells, required ink, vertical measures)")
    try:
        preview(all_glyphs)
        print("wrote preview.png")
    except ImportError:
        print("Pillow not available: preview.png not written")


if __name__ == "__main__":
    main()
