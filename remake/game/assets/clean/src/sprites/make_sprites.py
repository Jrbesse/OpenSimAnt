#!/usr/bin/env python3
"""make_sprites.py - draws the clean-pack ant sprite sheets (see README.md and docs/clean_pack/ant_sprites.md).

Writes, next to this script:
  surface.pix, nest.pix                   the two 256 x 128 sheets (16 x 8 sprites of 16 x 16 px), one hex digit per pixel
  surface_recolour.pix, nest_recolour.pix the recolour masks ('1' = the pixel changes colour for the black / red colony)
  preview.png                             both sheets drawn for the yellow, black and red colonies, the queen's pairs,
                                          and a ground test (needs Pillow)

Every sprite is drawn once, as the yellow ant.  The ants are pixel templates kept as string grids below (drawn
from part masks - head, thorax, abdomen, legs, wings - with small drawing helpers, then frozen as text so that they
can be edited by hand): the surface ants face north and north-east, the nest ants face east and (on a slope)
north-east / south-east.  The
other headings are exact 90 degree rotations and mirrors of those templates (so all eight look like the same ant),
the carried things are stamped on afterwards at the head end, and the shade pixels on the abdomen are placed after
the rotation so the light always comes from the top-left.

Run: python make_sprites.py      (deterministic; every random choice is seeded)
Every rule of the spec's "The script's checks" section is an assert at the end of main().
"""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

SP = 16                                   # a sprite is 16 x 16 pixels
COLS, ROWS = 16, 8                        # a sheet is 16 sprites across, 8 down
SHEET_W, SHEET_H = COLS * SP, ROWS * SP   # 256 x 128

# the standard 16-colour palette, by index
WHT, YEL, ORA, RED, MAG, PUR, BLU, CYA, GRN, DGN, BRN, TAN, LGR, MGR, DGY, BLK = range(16)
PALETTE = [(255, 255, 255), (252, 243, 5), (255, 100, 2), (221, 8, 6), (242, 8, 132), (70, 0, 165),
           (0, 0, 212), (2, 171, 234), (31, 183, 20), (0, 100, 17), (86, 44, 5), (144, 113, 58),
           (192, 192, 192), (128, 128, 128), (64, 64, 64), (0, 0, 0)]

# ---------------------------------------------------------------------------------------------------------------
# The letters of the templates:  letter -> (palette index, in the recolour mask?)
#   K  outline and legs        black (surface and nest)
#   F  feelers                 like K; dropped when the ant carries something (the carried thing is in front)
#   E  eye                     black
#   Y  body                    1 (yellow), recoloured          A  abdomen body: like Y, a few become shade O
#   O  shade                   2 (orange), recoloured          W  wing, white            V  wing edge, light grey
#   lower case: things that are not recoloured:  w white  l light grey  m medium grey  d dark grey  c orange
#   r red (bite sparks)  k black
LEGEND = {'K': (BLK, 0), 'F': (BLK, 0), 'E': (BLK, 0), 'Y': (YEL, 1), 'A': (YEL, 1), 'O': (ORA, 1),
          'W': (WHT, 0), 'V': (LGR, 0),
          'w': (WHT, 0), 'l': (LGR, 0), 'm': (MGR, 0), 'd': (DGY, 0), 'c': (ORA, 0), 'r': (RED, 0), 'k': (BLK, 0)}
LEGEND_NEST = dict(LEGEND)      # the nest ants have the same black outline, legs and feelers as the surface ones
                                # (the open tunnels of the yard sheet are light, so a dark grey body shows)


# ---------------------------------------------------------------------------------------------------------------
# THE TEMPLATES (string grids, 16 x 16; letters as in the legend above).
# Surface: seen from above, facing N and NE.  Nest: seen from the side, facing E, and on a slope (NE up, SE down).
# The queen is two cells: front part and rear part, cut from one continuous body so that they join.
SURFACE_ANTS = {
  'worker': dict(
    N=[
        "................",
        "...FF......FF...",
        ".....F....F.....",
        "......KKKK......",
        ".....KEYYEK.....",
        ".....KYYYYK.....",
        "..K..KYYYYK..K..",
        "...K..KYYK..K...",
        "....KKYYYYKK....",
        "..KKKKYYYYKKKK..",
        "....KKKYYKKK....",
        "...KKAAAAAAKK...",
        "..K.KAAAAAAK.K..",
        "....KAAAAAAK....",
        ".....KAAAAK.....",
        "......KKKK......",
    ],
    NE=[
        "........F.......",
        ".........F......",
        ".........F......",
        "....K...K.......",
        "....K..KEK......",
        "..K.K.KYYYK.....",
        "...KKKKYYYEK.FF.",
        "KKKKKYYYYYYK....",
        "..KKKYYYKYK.....",
        ".KAAAYYYYK......",
        "KAAAAYYYKKKKK...",
        "KAAAAAKKK.......",
        ".KAAAAAKKK......",
        "..KAAAK.K.K.....",
        "...KKK..K.......",
        "........K.......",
    ],
  ),
  'soldier': dict(
    N=[
        "................",
        ".....K....K.....",
        ".....KK..KK.....",
        "......KKKK......",
        ".....KYYYYK.....",
        "....KYEYYEYK....",
        "....KYYYYYYK....",
        "..K..KYYYYK..K..",
        "...K..KYYK..K...",
        "....KKYYYYKK....",
        "..KKKKYYYYKKKK..",
        "....KKKYYKKK....",
        "...KKAAAAAAKK...",
        "..K.KAAAAAAK.K..",
        ".....KAAAAK.....",
        "......KKKK......",
    ],
    NE=[
        "...........K....",
        "..........K.....",
        "....K...KK.K....",
        "....K..KYYK.....",
        "....K.KYYEYK.KK.",
        "..KKK.KYYYYYK.K.",
        "....KKKYYYYEK...",
        "KKKKKYYYYYYYK...",
        "..KAKYYYYKKK....",
        ".KAAAYYYYK......",
        ".KAAAAYYKKKKK...",
        "..KAAAAK.K......",
        "...KAAAKKKK.....",
        "....KKK.K.......",
        "........K.......",
        "................",
    ],
  ),
  'male': dict(
    N=[
        ".....F....F.....",
        "......F..F......",
        ".......KK.......",
        "......KYYK......",
        ".....KEYYEK.....",
        "..K..KYYYYK..K..",
        "...K..KYYK..K...",
        "....KKYYYYKK....",
        "...KKKYYYYKKK...",
        "..KWKVKYYKVKWK..",
        "..VKWKAAAAKWKV..",
        ".VKWWKAAAAKWWKV.",
        ".VWWVKAAAAKVWWV.",
        ".VWWVKAAAAKVWWV.",
        ".VVV..KAAK..VVV.",
        ".......KK.......",
    ],
    NE=[
        "...........F....",
        "......K....F....",
        "......K..KKK....",
        "......K.KEYYK.FF",
        "..VKKVKKKYYYK...",
        "VKKKKKKYYYYEK...",
        "VWWWWKYYYYYYK...",
        "VWWVKAKYYYKK....",
        "VVVKAAAYYYK.....",
        "..KAAAAAKKKKKKK.",
        "..KAAAAAKKVK....",
        "..KAAAAKWKVK....",
        "...KKAKVWKVK....",
        ".....K.VWKV.....",
        ".......VVV......",
        "................",
    ],
  ),
  'yqueen': dict(
    N=[
        "....F......F....",
        ".....F....F.....",
        ".......KK.......",
        "......KYYK......",
        ".....KEYYEK.....",
        ".....KYYYYK.....",
        ".....KYYYYK.....",
        "...VKYYYYYYKV...",
        "..VWKYYYYYYKWV..",
        ".VWWVKYYYYKVWWV.",
        "VWWWVKKYYKKVWWWV",
        "VWWWKAAAAAAKWWWV",
        "VWWWKAAAAAAKWWWV",
        "VWWVKAAAAAAKVWWV",
        "VVV..KAAAAK..VVV",
        "......KKKK......",
    ],
    NE=[
        "...........F....",
        "...........F....",
        "................",
        ".........KKK....",
        ".VVVVV..KEYYK...",
        "VWWWWWKKYYYYK.FF",
        "VWWWWKYYYYYEK...",
        "VWWWVKYYYYYYK...",
        "VVVKKKYYYYYK....",
        "..KAAAYYYYYK....",
        ".KAAAAYYYYKV....",
        ".KAAAAAKKKWV....",
        "..KAAAAAKWWWV...",
        "...KAAAKVWWV....",
        "....KKKVWWWV....",
        ".......VVVVV....",
    ],
  ),
  'queen_front': dict(
    N=[
        "................",
        "................",
        ".....FFKKFFF....",
        "......FYYF......",
        ".....KYYYYK.....",
        ".....KYYYYK.....",
        ".....KYYYYK.....",
        "..KKK.KYYK.KKK..",
        ".....KYYYYK.....",
        "....KYYYYYYK....",
        "...KKYYYYYYKK...",
        "..K.KYYYYYYK.K..",
        ".....KYYYYK.....",
        "....K.KYYK.K....",
        "...K..KYYK..K...",
        "......KYYK......",
    ],
    NE=[
        "................",
        "................",
        "................",
        "................",
        ".......F........",
        "......KKF.......",
        "..K..KYYK.......",
        "...KKYYYYKF.....",
        "K.KKKKYYYYKF....",
        ".KYYYYYYYYK.....",
        "KYYYYYYKYK......",
        "KYYYYYYKK.......",
        "KYYYYYYKK.......",
        "KYYYYYYK.K......",
        "YYYYYYK.........",
        "YYKKKK.K........",
    ],
  ),
  'queen_rear': dict(
    N=[
        "......KYYK......",
        "......KYYK......",
        "......KKKK......",
        ".....KAAAAK.....",
        "....KAAAAAAK....",
        "...KAAAAAAAAK...",
        "...KAAAAAAAAK...",
        "..KAAAAAAAAAAK..",
        "..KAAAAAAAAAAK..",
        "...KAAAAAAAAK...",
        "...KAAAAAAAAK...",
        "...KAAAAAAAAK...",
        "....KAAAAAAK....",
        ".....KKKKKK.....",
        "................",
        "................",
    ],
    NE=[
        "........KKKKKKYY",
        ".......KAAAAAKYY",
        "......KAAAAAAAKK",
        ".....KAAAAAAAAAK",
        ".....KAAAAAAAAAK",
        "....KAAAAAAAAAAK",
        "....KAAAAAAAAAAK",
        "....KAAAAAAAAAAK",
        ".....KAAAAAAAAK.",
        "......KAAAAAAK..",
        ".......KAAAKK...",
        "........KKK.....",
        "................",
        "................",
        "................",
        "................",
    ],
  ),
}

NEST_ANTS = {
  'worker': dict(
    E=[
        "................",
        "................",
        "................",
        "................",
        "................",
        "...............F",
        "..KK...KK....FF.",
        ".KAAK.KYYKKKF...",
        "KAAAAKYYYKYYYK..",
        "KAAAAKYYYKYEYK..",
        "KAAAAKYYYKYYYK..",
        ".KAAK.KYYKKYYK..",
        "..KK..KKK.KKK...",
        ".....K..K..K....",
        "....K..K...K....",
        "...K...K...K....",
    ],
    NE=[
        ".........F......",
        ".........F......",
        ".........F......",
        ".........FK.....",
        "........KYYK....",
        "......KKYEYYK...",
        ".....KYKYYYYK...",
        "....KYYYKYYYK...",
        "....KYYYYKKKK...",
        "..KKKKYYYYK..K..",
        ".KAAAKKKYKK...K.",
        ".KAAAAK.K.K.....",
        ".KAAAAK.K.KK....",
        "..KAAAK.K.......",
        "...KKK..K.......",
        "................",
    ],
    SE=[
        "................",
        "...KKK..........",
        "..KAAAK.........",
        ".KAAAAK.........",
        ".KAAAAKKK.......",
        ".KAAAKKYYK......",
        "..KKKKYYYYK.....",
        ".....KYYYKK.....",
        "KKKKKYYYKYYK....",
        ".....KYKYYEYFFFF",
        "...KKKKKYYYYK...",
        "...K...KYYYK....",
        ".......KKKK.....",
        "......K.........",
        "................",
        "................",
    ],
  ),
  'soldier': dict(
    E=[
        "................",
        "................",
        "................",
        "................",
        "..........KKK...",
        ".........KYYYK..",
        "......KKKYYYYK..",
        "..KK.KYYKYYEYK..",
        ".KAAKYYYKYYYYK..",
        "KAAAKYYYKYYYYK..",
        "KAAAKYYYKYYYYKK.",
        ".KAAKKYYKKYYYKK.",
        "..KK.KKKK.KKKK..",
        "....K..K.K......",
        "...K..K...K.....",
        "..K...K...K.....",
    ],
    NE=[
        "................",
        ".......KK.......",
        "......KYYK......",
        ".....KYYYYK.....",
        ".....KYYEYYKK...",
        ".....KYYYYYYKK..",
        ".....KKYYYYYKK..",
        "....KYKKYYYYK...",
        "....KYYKKKKK....",
        "...KYYYYK.......",
        "..KAKYYYYKKKKK..",
        ".KAAAKKKKK......",
        ".KAAAAKK.K......",
        "..KAAAKK..K.....",
        "...KKK.K........",
        "................",
    ],
    SE=[
        "................",
        "...KK...........",
        "..KAAK..........",
        ".KAAAAK.........",
        ".KAAAKYKK.......",
        ".KAAKYYYYKKKK...",
        "..KKKYYYKKYYYK..",
        "KKKKKYYKKYYYYYK.",
        "....KYKKYYYEYYK.",
        "...KKK.KYYYYYK..",
        "..K..K.KYYYYK...",
        ".....K.KYYYK....",
        ".....K..KKKK....",
        ".....K...KK.....",
        "................",
        "................",
    ],
  ),
  'male': dict(
    E=[
        "................",
        "................",
        "................",
        "................",
        "...VVVV.........",
        "...VWWWVV.......",
        "....VVWWWV.....F",
        "......VVKK...FF.",
        "..KKK..KYYKKF...",
        ".KAAAKKYYYKYYK..",
        "KAAAAAKYYYKYEK..",
        ".KAAAK.KYYKYYK..",
        "..KKK..KKK.KK...",
        "......K.K.K.....",
        ".....K.K...K....",
        "....K..K...K....",
    ],
    NE=[
        "..........F.....",
        "..........F.....",
        "..........F.....",
        ".........F......",
        ".........FKK....",
        "...VVVVKKYYEK...",
        ".VVWWWKYKKYYK...",
        "VWWWVKYYYKKYK...",
        "VVVV.KYYYYKK....",
        "....KKKYYYKKKK..",
        "...KAAAKKKK...K.",
        "..KAAAAK.KK.....",
        "..KAAAAK.KKK....",
        "..KAAAK..K......",
        "...KKK...K......",
        "................",
    ],
    SE=[
        "................",
        ".......VV.......",
        ".......VWV......",
        "..KKK..VWV......",
        ".KAAAK.VWWV.....",
        ".KAAAAK.VWV.....",
        ".KAAAAKKKWV.....",
        "..KAAAKYYKV.....",
        "...KKKYYYYK.....",
        ".....KYYYKK.....",
        "KKKKKKYYKKYFF...",
        "...KKKKKKYYK.FFF",
        "...K..KKYYEK....",
        "......K.KKK.....",
        "......K.........",
        "................",
    ],
  ),
  'yqueen': dict(
    E=[
        "................",
        ".VVVVV..........",
        ".VWWWWV.........",
        ".VWWWWWV........",
        "..VWWWWWV.......",
        "...VWWWKK......F",
        "..KKVVKYYK...FF.",
        ".KAAKKYYYYKKF...",
        "KAAAAKYYYYKYYK..",
        "KAAAAKYYYYKYEK..",
        "KAAAAKYYYYKYYK..",
        ".KAAK.KYYKKYYK..",
        "..KK..KKKK.KK...",
        ".....K..K.K.....",
        "....K..K...K....",
        "...K...K...K....",
    ],
    NE=[
        "..........F.....",
        "..........F.....",
        "..........F.....",
        "..........FK....",
        ".VVVVVK..KYYK...",
        "VWWWWKYKKKYEYK..",
        "VWWWKYYYYKKYYK..",
        "VWWWVKYYYYKKYK..",
        "VVVV.KYYYYK.K...",
        "...KKKKYYYYKKKK.",
        "..KAAAKKKYKK...K",
        "..KAAAAK.K.K....",
        "..KAAAAK.K.KK...",
        "...KAAAK.K......",
        "....KKK..K......",
        "................",
    ],
    SE=[
        ".......VVVV.....",
        ".......VWWV.....",
        ".......VWWWV....",
        "...KKK.VWWWV....",
        "..KAAAKVWWWV....",
        ".KAAAAK.VKWV....",
        ".KAAAAKKKYKV....",
        ".KAAAKKYYYYK....",
        "..KKKKYYYYK.....",
        ".....KYYYYK.....",
        "KKKKKYYYYKKK....",
        ".....KYKKKYYFFFF",
        "...KKKK.KYEYK...",
        "...K..KKYYYK....",
        "......K.KKK.....",
        "......K.........",
    ],
  ),
  'queen_front': dict(
    E=[
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "....KKKK......FF",
        "...KYYYYK..KKF..",
        "KKKYYYYYYKKYYYK.",
        "YYYYYYYYYKYYYEK.",
        "YYYYYYYYYKYYYYK.",
        "KKKYYYYYYKKYYK..",
        "...KYYYYK..KK...",
        "....KKKKK.......",
        "...K..K..K......",
        "..K..K....K.....",
    ],
    NE=[
        "................",
        "................",
        "........F.......",
        ".......F........",
        ".......FK.......",
        ".......KYK......",
        "......KYYEK.....",
        "...K..KYYYK.....",
        "..KYKKKYYYK.....",
        ".KYYYYKKKK......",
        "KYYYYYYK........",
        "KYYYYYYK........",
        "KYYYYYYYKKKK....",
        "KYYYYYYK........",
        "YYYYYYKK........",
        "YYKKKK.K........",
    ],
    SE=[
        "YYKKKK..........",
        "YYYYYYK.........",
        "KYYYYYYK........",
        "KYYYYYYYK.......",
        "KYYYYYYK........",
        "KYYYYYYK........",
        ".KYYYYKKKK......",
        "KKKYKKKYYYKFF...",
        "...K..KYYYYK.F..",
        "...K..KYYEK.....",
        "...K...KKK......",
        "...K............",
        "................",
        "................",
        "................",
        "................",
    ],
  ),
  'queen_rear': dict(
    E=[
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "......KKKKK.....",
        "....KKAAAAAKK...",
        "...KAAAAAAAAAKKK",
        "..KAAAAAAAAAYYYY",
        "..KAAAAAAAAAYYYY",
        "..KAAAAAAAAAAKKK",
        "...KAAAAAAAAAK..",
        "....KAAAAAAAK...",
        ".....KKAAAAK....",
        ".......KKKK.....",
    ],
    NE=[
        "............KKYY",
        ".........KKKAYYY",
        "........KAAAAAYK",
        ".......KAAAAAAAK",
        "......KAAAAAAAAA",
        "......KAAAAAAAAA",
        "......KAAAAAAAAA",
        "......KAAAAAAAAA",
        ".....KAAAAAAAAAK",
        "......KAAAAAKAK.",
        ".......KKKKK.K..",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    SE=[
        "................",
        "................",
        "................",
        "................",
        "................",
        ".......K........",
        "......KAKKKK....",
        ".....KAAAAAAK...",
        ".....KAAAAAAAK..",
        ".....KAAAAAAAAK.",
        ".....KAAAAAAAAK.",
        ".....KAAAAAAAAK.",
        "......KAAAAAAAAK",
        ".....KAAAAAAAAYK",
        "......KAAAAAAYYY",
        ".......KAAAAKKYY",
    ],
  ),
}


# ---------------------------------------------------------------------------------------------------------------
# The carried things (4 x 4 boxes, stamped over the head end) and where the box goes in each template pose.
FOOD = ['.cc.',
        'cwwc',
        'cwwc',
        '.cc.']
PEBBLE = ['.ll.',
          'lmmm',
          'mmmd',
          '.dd.']
BABY_N = ['.ll.',          # a pale capsule, long axis along the heading (here: north); grey rim, white core
          'lwwl',
          'lwwl',
          '.ll.']
BABY_NE = ['..ll',         # the same capsule pointing north-east
           '.lwl',
           'lwwl',
           'll..']

# top-left corner of the 4 x 4 box in the template (the pose it is stamped on), per view and caste
ITEM_BOX = {
    'surface': {'worker': {'N': (6, 0), 'NE': (10, 1)}, 'soldier': {'N': (6, 0), 'NE': (10, 0)}},
    'nest': {'worker': {'E': (12, 7), 'NE': (9, 2), 'SE': (10, 9)}, 'soldier': {'E': (12, 7), 'NE': (9, 2), 'SE': (10, 9)}},
}

# which template (and which exact rotations / mirrors) gives each heading 0..7 (N, NE, E, SE, S, SW, W, NW).
# R = turn 90 degrees clockwise, H = mirror left-right, V = mirror top-bottom
HEADINGS = {
    'surface': [('N', ''), ('NE', ''), ('N', 'R'), ('NE', 'R'), ('N', 'RR'), ('NE', 'RR'), ('N', 'RRR'), ('NE', 'RRR')],
    'nest': [('E', 'RRR'), ('NE', ''), ('E', ''), ('SE', ''), ('E', 'RRRV'), ('SE', 'H'), ('E', 'H'), ('NE', 'H')],
}


def rot_cw(g):
    n = len(g)
    return [''.join(g[n - 1 - x][y] for x in range(n)) for y in range(n)]


def flip_h(g):
    return [r[::-1] for r in g]


def flip_v(g):
    return g[::-1]


OPS = {'R': rot_cw, 'H': flip_h, 'V': flip_v}


def apply_ops(g, ops):
    for o in ops:
        g = OPS[o](g)
    return g


def map_point(x, y, op, n=SP):
    if op == 'R':
        return n - 1 - y, x
    if op == 'H':
        return n - 1 - x, y
    return x, n - 1 - y


def map_box(x0, y0, ops, size=4):
    """where the size x size box with top-left (x0, y0) lands after the operations"""
    pts = [(x0, y0), (x0 + size - 1, y0 + size - 1)]
    for o in ops:
        pts = [map_point(x, y, o) for x, y in pts]
    return min(p[0] for p in pts), min(p[1] for p in pts)


def put_grid(g, x0, y0, box):
    out = [list(r) for r in g]
    for j, row in enumerate(box):
        for i, ch in enumerate(row):
            if ch != '.':
                out[y0 + j][x0 + i] = ch
    return [''.join(r) for r in out]


def drop_feelers(g):
    """feelers go (the carried thing is in front); an F that is part of the head's outline stays as outline"""
    out = [list(r) for r in g]
    n = len(g)
    for y in range(n):
        for x in range(n):
            if g[y][x] == 'F':
                near = any(0 <= x + dx < n and 0 <= y + dy < n and g[y + dy][x + dx] in 'YAO'
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                out[y][x] = 'K' if near else '.'
    return [''.join(r) for r in out]


def shade(g, count):
    """turn `count` abdomen pixels on the lower-right rim into shade (index 2): the light is from the top-left"""
    body = {(x, y) for y, r in enumerate(g) for x, ch in enumerate(r) if ch in 'YAO'}
    cand = []
    for y, r in enumerate(g):
        for x, ch in enumerate(r):
            if ch == 'A':
                right, below = (x + 1, y) not in body, (x, y + 1) not in body
                if right or below:
                    cand.append((int(right) + int(below), x + y, x, y))
    cand.sort(reverse=True)
    out = [list(r) for r in g]
    for _, _, x, y in cand[:count]:
        out[y][x] = 'O'
    return [''.join(r).replace('A', 'Y') for r in out]


SHADE = {'worker': 3, 'soldier': 3, 'male': 2, 'yqueen': 4, 'queen_front': 0, 'queen_rear': 6}


def ant_grid(view, caste, heading, item=None):
    """one 16 x 16 template-letter grid of an ant of that caste, facing that heading, carrying `item` (or nothing)"""
    table = SURFACE_ANTS if view == 'surface' else NEST_ANTS
    pose, ops = HEADINGS[view][heading]
    g = table[caste][pose]
    box = None
    if item:
        g = drop_feelers(g)
        x0, y0 = ITEM_BOX[view][caste][pose]
        if item == 'food':
            box = FOOD
        elif item == 'pebble':
            box = PEBBLE
        else:                                                   # a baby: a capsule oriented along the heading
            box = {'surface': {'N': BABY_N, 'NE': BABY_NE},
                   'nest': {'E': rot_cw(BABY_N), 'NE': BABY_NE, 'SE': rot_cw(BABY_NE)}}[view][pose]
        bx, by = map_box(x0, y0, ops)
        if item == 'baby':
            box = apply_ops(box, ops)
    g = apply_ops(g, ops)
    if item:
        g = put_grid(g, bx, by, box)
    return shade(g, SHADE[caste])


# ---------------------------------------------------------------------------------------------------------------
# Brood: seven growth stages of one baby (no heading), pale with a coloured band / spot (Y, recoloured).
def outlined(rows, ch='m'):
    """a 1-pixel outline (medium grey: it shows on tan, on light floors and on the dark tunnels) round a small bitmap"""
    h, w = len(rows), len(rows[0])
    g = [['.'] * (w + 2) for _ in range(h + 2)]
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            g[j + 1][i + 1] = c
    out = [r[:] for r in g]
    for y in range(h + 2):
        for x in range(w + 2):
            if g[y][x] == '.' and any(0 <= x + dx < w + 2 and 0 <= y + dy < h + 2 and g[y + dy][x + dx] != '.'
                                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = ch
    return [''.join(r) for r in out]


def centred(rows):
    rows = outlined(rows)
    h, w = len(rows), len(rows[0])
    x0, y0 = (SP - w) // 2, (SP - h) // 2
    g = [['.'] * SP for _ in range(SP)]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != '.':
                g[y0 + j][x0 + i] = ch
    return [''.join(r) for r in g]


BROOD = {
    1: centred(['wwwl',                 # 0x01 a tiny newly laid egg, 4 x 3
                'wYYl',
                'wlll']),
    2: centred(['.www.',                # 0x02 a larger egg, 5 x 4
                'wwwwl',
                'wYYYl',
                '.lll.']),
    3: centred(['.ww.',                 # 0x03 a grub, first growth step, 4 x 6
                'wwwl',
                'wYYl',
                'wwwl',
                'wwll',
                '.ll.']),
    4: centred(['..ww..',               # 0x04 second step, 6 x 8
                '.wwwl.',
                'wwwwwl',
                'wYYYYl',
                'wwwwll',
                'wwwwll',
                '.wlll.',
                '..ll..']),
    5: centred(['..wwww..',             # 0x05 third step, 8 x 11, plump, with the grooves between its segments
                '.wwwwwl.',
                'wwwwwwwl',
                'mmmmmmmm',
                'wYYYYYYl',
                'wwwwwwwl',
                'mmmmmmmm',
                'wwwwwwll',
                'wwwwwwll',
                '.wwwwll.',
                '..llll..']),
    6: centred(['..llll..',             # 0x06 a pupa: a wrapped capsule, 8 x 12, with the coloured band
                '.lwwwwl.',
                'lwwwwwwl',
                'lmmmmmml',
                'lwwwwwwl',
                'lwYYYYwl',
                'lwYYYYwl',
                'lwwwwwwl',
                'lmmmmmml',
                'lwwwwwwl',
                '.lwwwwl.',
                '..llll..']),
    7: centred(['..llll..',             # 0x07 a pupa about to hatch: the adult's head and legs show through the wrapping
                '.lwddwl.',
                'lwwddwwl',
                'lmdmmdml',
                'lwdwwdwl',
                'lwYYYYwl',
                'lwYYYYwl',
                'lwdwwdwl',
                'lmmddmml',
                'lwwddwwl',
                '.lwwwwl.',
                '..llll..']),
}


# ---------------------------------------------------------------------------------------------------------------
# The fight cloud: one scuffle, 8 variants (the game picks one at random each tick, so they must flicker, not jump).
def fight_cloud(v):
    """two ants in a dust cloud.  What stays the same in all 8 variants: the cloud's shape (within a pixel), five of
    the limbs and the bodies showing through; what changes: two more limbs, where the bites spark, the flying specks."""
    rnd = random.Random(1000 + v)
    cx, cy = 7.5, 7.5
    puffs = [(0.0, 0.0, 4.6)]
    for ang, dist, rad in [(20, 4.0, 2.6), (95, 4.2, 2.4), (160, 3.9, 2.6), (225, 4.2, 2.4), (290, 4.0, 2.5), (345, 4.3, 2.0)]:
        a = np.radians(ang + rnd.uniform(-6, 6))
        d = dist + rnd.uniform(-0.3, 0.3)
        puffs.append((d * np.cos(a), d * np.sin(a), rad + rnd.uniform(-0.2, 0.2)))
    cloud = set()
    for y in range(SP):
        for x in range(SP):
            for px, py, r in puffs:
                if (x + .5 - cx - px) ** 2 + (y + .5 - cy - py) ** 2 <= r * r:
                    cloud.add((x, y))
    g = [['.'] * SP for _ in range(SP)]
    for x, y in cloud:
        up_left = (x - 1, y) not in cloud or (x, y - 1) not in cloud
        low_right = (x + 1, y) not in cloud or (x, y + 1) not in cloud
        g[y][x] = 'w' if up_left and not low_right else ('m' if low_right and not up_left else 'l')
    # limbs sticking out of the dust (black): five always, two of four more
    fixed = [[(5, 6), (4, 5), (3, 4)], [(11, 9), (12, 10), (13, 10)], [(4, 9), (3, 10), (2, 10)],
             [(9, 11), (10, 12), (10, 13)], [(7, 4), (7, 3), (6, 2)]]
    extra = [[(10, 5), (11, 4), (12, 3)], [(5, 11), (4, 12), (3, 13)], [(11, 7), (12, 7), (13, 6)], [(6, 9), (5, 10), (5, 11)]]
    for limb in fixed + rnd.sample(extra, 2):
        for x, y in limb:
            g[y][x] = 'k'
    # two ant bodies showing through the dust, the winner's colour (recoloured): 11 pixels, each moving at most a pixel
    parts = [[(5, 8), (6, 8), (5, 9), (6, 9), (7, 9)], [(9, 6), (10, 6), (9, 7), (10, 7)], [(8, 8), (8, 9)]]
    for i, part in enumerate(parts):
        jx, jy = (rnd.choice([-1, 0, 0, 1]), rnd.choice([-1, 0, 0, 1])) if i < 2 else (0, 0)
        for x, y in part:
            g[y + jy][x + jx] = 'Y'
    g[6][11] = 'k'                       # a mandible on the head part
    sparks = [(3, 6), (12, 8), (7, 2), (8, 13), (11, 11), (4, 11)]
    for x, y in rnd.sample(sparks, 3):
        g[y][x] = 'r'
    specks = [(1, 7), (14, 6), (6, 0), (9, 14), (13, 12), (2, 3), (14, 2), (1, 12)]
    for x, y in rnd.sample(specks, 3):
        if g[y][x] == '.':
            g[y][x] = rnd.choice('wl')
    return [''.join(r) for r in g]


# ---------------------------------------------------------------------------------------------------------------
# The unused slots: an opaque light grey tile with the slot number in 3 x 5 hex digits.
DIGITS = {
    '0': ['kkk', 'k.k', 'k.k', 'k.k', 'kkk'], '1': ['.k.', 'kk.', '.k.', '.k.', 'kkk'],
    '2': ['kkk', '..k', 'kkk', 'k..', 'kkk'], '3': ['kkk', '..k', '.kk', '..k', 'kkk'],
    '4': ['k.k', 'k.k', 'kkk', '..k', '..k'], '5': ['kkk', 'k..', 'kkk', '..k', 'kkk'],
    '6': ['kkk', 'k..', 'kkk', 'k.k', 'kkk'], '7': ['kkk', '..k', '.k.', '.k.', '.k.'],
    '8': ['kkk', 'k.k', 'kkk', 'k.k', 'kkk'], '9': ['kkk', 'k.k', 'kkk', '..k', 'kkk'],
    'A': ['.k.', 'k.k', 'kkk', 'k.k', 'k.k'], 'B': ['kk.', 'k.k', 'kk.', 'k.k', 'kk.'],
    'C': ['.kk', 'k..', 'k..', 'k..', '.kk'], 'D': ['kk.', 'k.k', 'k.k', 'k.k', 'kk.'],
    'E': ['kkk', 'k..', 'kk.', 'k..', 'kkk'], 'F': ['kkk', 'k..', 'kk.', 'k..', 'k..'],
}


def placeholder(n):
    g = [['l'] * SP for _ in range(SP)]
    for d, x0 in zip('%02X' % n, (4, 9)):
        for j, row in enumerate(DIGITS[d]):
            for i, ch in enumerate(row):
                if ch == 'k':
                    g[5 + j][x0 + i] = 'k'
    return [''.join(r) for r in g]


USED = list(range(0x01, 0x50)) + list(range(0x60, 0x78))
UNUSED = [n for n in range(128) if n not in USED]
assert len(USED) == 103 and len(UNUSED) == 25


def sprite_grids(view):
    """{slot: 16 rows of template letters} for one sheet"""
    out = {}
    for n in UNUSED:
        out[n] = placeholder(n)
    for stage in range(1, 8):
        out[stage] = BROOD[stage]
    for h in range(8):
        out[0x08 + h] = ant_grid(view, 'worker', h, 'baby')
        out[0x10 + h] = ant_grid(view, 'worker', h)
        out[0x18 + h] = ant_grid(view, 'worker', h, 'food')
        out[0x20 + h] = ant_grid(view, 'male', h)
        out[0x28 + h] = ant_grid(view, 'worker', h, 'pebble')
        out[0x30 + h] = ant_grid(view, 'soldier', h)
        out[0x38 + h] = ant_grid(view, 'soldier', h, 'food')
        out[0x40 + h] = ant_grid(view, 'yqueen', h)
        out[0x48 + h] = ant_grid(view, 'soldier', h, 'pebble')
        out[0x60 + h] = ant_grid(view, 'queen_front', h)
        out[0x68 + h] = ant_grid(view, 'queen_rear', h)
        out[0x70 + h] = fight_cloud(h)
    assert sorted(out) == list(range(128))
    return out


def to_arrays(grids, legend):
    pic = np.full((SHEET_H, SHEET_W), -1, np.int16)
    msk = np.zeros((SHEET_H, SHEET_W), np.uint8)
    for n, g in grids.items():
        assert len(g) == SP and all(len(r) == SP for r in g), hex(n)
        ox, oy = (n % COLS) * SP, (n // COLS) * SP
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                if ch != '.':
                    idx, m = legend[ch]
                    pic[oy + y, ox + x] = idx
                    msk[oy + y, ox + x] = m
    return pic, msk


def tile(a, n):
    return a[(n // COLS) * SP:(n // COLS) * SP + SP, (n % COLS) * SP:(n % COLS) * SP + SP]


# ---------------------------------------------------------------------------------------------------------------
# .pix output
def write_pix(path, pic, title, mask=None):
    lines = ['# ' + title, '# 256 x 128: 16 x 8 sprites of 16 x 16 pixels; sprite n at column n % 16, row n // 16.']
    if mask is None:
        lines.append('# one hex digit per pixel = palette index, . = transparent. Made by make_sprites.py.')
        for y in range(SHEET_H):
            lines.append(''.join('.' if v < 0 else '0123456789abcdef'[v] for v in pic[y]))
    else:
        lines.append('# 1 = the pixel changes colour for the black (index xor 15) and red (index xor 2) colonies; 0 = it does not;')
        lines.append('# . = transparent in the picture. Made by make_sprites.py.')
        for y in range(SHEET_H):
            lines.append(''.join('.' if pic[y, x] < 0 else str(int(mask[y, x])) for x in range(SHEET_W)))
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def read_pix(path):
    rows = [l.rstrip('\n') for l in open(path) if not l.startswith('#') and l.strip()]
    return rows


# ---------------------------------------------------------------------------------------------------------------
# the colonies
def recolour(pic, msk, colony):
    out = pic.copy()
    m = (msk == 1) & (pic >= 0)
    if colony == 'black':
        out[m] = pic[m] ^ 15
    elif colony == 'red':
        out[m] = pic[m] ^ 2
    return out


# ---------------------------------------------------------------------------------------------------------------
# the checks (the spec's "The script's checks")
def components(cells):
    cells = set(cells)
    seen, comps = set(), []
    for c in cells:
        if c in seen:
            continue
        stack, comp = [c], []
        seen.add(c)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in cells and q not in seen:
                        seen.add(q)
                        stack.append(q)
        comps.append(comp)
    return comps


def check_sheet(name, pic, msk, grids):
    assert pic.shape == (128, 256), (name, pic.shape)
    assert msk.shape == (128, 256), (name, msk.shape)
    assert set(np.unique(msk).tolist()) <= {0, 1}, name
    assert not ((msk == 1) & (pic < 0)).any(), name + ': a 1 on a transparent pixel'
    bad = (msk == 1) & (pic >= 0) & (pic != YEL) & (pic != ORA)
    assert not bad.any(), name + ': a recoloured pixel that is not index 1 or 2'
    assert not ((msk == 0) & (pic == YEL)).any(), name + ': an unrecoloured yellow pixel'
    for n in USED:
        p, m = tile(pic, n), tile(msk, n)
        opaque = int((p >= 0).sum())
        assert opaque >= 20, (name, hex(n), 'only %d opaque pixels' % opaque)
        masked = int(m.sum())
        # the mask follows the body: every masked pixel touches another masked pixel (no speckle)
        ys, xs = np.nonzero(m)
        for y, x in zip(ys, xs):
            nb = [(y + dy, x + dx) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= y + dy < SP and 0 <= x + dx < SP]
            assert any(m[a, b] for a, b in nb), (name, hex(n), 'speckle at', x, y)
        # at most a few shade (index 2) pixels, they stay on the body
        shade_px = int(((p == ORA) & (m == 1)).sum())
        assert shade_px <= (8 if 0x60 <= n < 0x70 else 4), (name, hex(n), 'too much shade', shade_px)
        kind = 'brood' if n < 8 else 'cloud' if 0x70 <= n < 0x78 else 'ant'
        if kind == 'brood':
            assert 2 <= masked <= 20, (name, hex(n), 'brood mark', masked)
        elif kind == 'cloud':
            assert 8 <= masked <= 16, (name, hex(n), 'cloud body', masked)
        else:
            winged = 0x20 <= n < 0x28 or 0x40 <= n < 0x48       # the wings are not body: they take a third of the pixels
            need = 0.28 if winged else 0.38
            assert masked >= need * opaque, (name, hex(n), 'body is only %d of %d pixels' % (masked, opaque))
        # nothing floats: one connected body (the carried thing, a few feelers and flying dust may stand apart)
        if kind != 'cloud':
            letters = {(x, y) for y in range(SP) for x in range(SP) if grids[n][y][x] != '.'
                       and not grids[n][y][x].islower()}
            if kind == 'brood':
                letters = {(x, y) for y in range(SP) for x in range(SP) if grids[n][y][x] != '.'}
            comps = components(letters)
            main = max(len(c) for c in comps)
            assert len(letters) - main <= 4, (name, hex(n), 'floating pixels', sorted(len(c) for c in comps))
    for n in UNUSED:
        p, m = tile(pic, n), tile(msk, n)
        assert (p >= 0).all() and (m == 0).all(), (name, hex(n), 'placeholder')
        assert (p == LGR).sum() + (p == BLK).sum() == 256 and (p == BLK).sum() > 0, (name, hex(n))
    # the eight headings of one caste look like the same ant: about as many pixels, diagonals not smaller
    for base, label in ((0x10, 'worker'), (0x20, 'male'), (0x30, 'soldier'), (0x40, 'young queen'),
                        (0x60, 'queen front'), (0x68, 'queen rear')):
        counts = [int((tile(pic, base + h) >= 0).sum()) for h in range(8)]
        bodies = [int(tile(msk, base + h).sum()) for h in range(8)]
        assert min(counts) >= 0.8 * max(counts), (name, label, counts)
        assert min(bodies) >= 0.8 * max(bodies), (name, label, bodies)
        straight = np.mean([bodies[h] for h in (0, 2, 4, 6)])
        diag = np.mean([bodies[h] for h in (1, 3, 5, 7)])
        assert diag >= 0.88 * straight, (name, label, 'diagonals look smaller', straight, diag)


def opaque_cell(a):
    return a >= 0


def check_queen(name, pic):
    """the queen's front (0x60 + h) and rear (0x68 + h) parts join, heading by heading"""
    for h in range(8):
        F, R = opaque_cell(tile(pic, 0x60 + h)), opaque_cell(tile(pic, 0x68 + h))
        what = '%s queen heading %d' % (name, h)
        if h in (0, 2, 4, 6):
            if h == 0:      # F above R
                a, b = F[15, :], R[0, :]
            elif h == 2:    # R F
                a, b = F[:, 0], R[:, 15]
            elif h == 4:    # R above F
                a, b = F[0, :], R[15, :]
            else:           # F R
                a, b = F[:, 15], R[:, 0]
            pa, pb = np.nonzero(a)[0].tolist(), np.nonzero(b)[0].tolist()
            assert pa == pb and 2 <= len(pa) <= 4, (what, pa, pb)
            assert min(pa) >= 4 and max(pa) <= 11, (what, 'the join is not at the middle of the edge', pa)
        else:
            if h == 1:      # . F / R .
                a, b = F[15, 0], R[0, 15]
            elif h == 3:    # R . / . F
                a, b = F[0, 0], R[15, 15]
            elif h == 5:    # . R / F .
                a, b = F[0, 15], R[15, 0]
            else:           # F . / . R
                a, b = F[15, 15], R[0, 0]
            assert a and b, (what, 'the corner pixels that meet are not both opaque')


# ---------------------------------------------------------------------------------------------------------------
# preview.png
def ground(w, h, base, speck, density, seed):
    rnd = np.random.RandomState(seed)
    g = np.full((h, w), base, np.int16)
    r = rnd.rand(h, w)
    g[r < density] = speck[0]
    g[(r >= density) & (r < 2 * density)] = speck[1]
    return g


def yard_tunnel_tiles():
    """the open-tunnel tiles 0x90..0x97 of the clean yard sheet (../tiles/yard.pix), as 16 x 16 index arrays"""
    path = os.path.join(HERE, '..', 'tiles', 'yard.pix')
    rows = [l.strip() for l in open(path) if l.strip() and not l.startswith('#')]
    assert len(rows) == 256 and all(len(r) == 256 for r in rows), path
    sheet = np.array([[int(c, 16) for c in r] for r in rows], np.int16)
    return [sheet[9 * 16:10 * 16, i * 16:(i + 1) * 16].copy() for i in range(8)]


def tunnel_ground(w, h, seed):
    """a w x h ground made of random tunnel tiles of the yard sheet (w, h multiples of 16)"""
    rnd = random.Random(seed)
    tiles = yard_tunnel_tiles()
    g = np.zeros((h, w), np.int16)
    for ty in range(h // SP):
        for tx in range(w // SP):
            g[ty * SP:(ty + 1) * SP, tx * SP:(tx + 1) * SP] = rnd.choice(tiles)
    return g


def paint(canvas, pic, x0, y0, scale, bg=None):
    """draw an index array (-1 = transparent) onto an RGB canvas; bg (index array) is painted first"""
    h, w = pic.shape
    for y in range(h):
        for x in range(w):
            v = pic[y, x]
            if bg is not None and v < 0:
                v = bg[y, x]
            if v >= 0:
                canvas[y0 + y * scale:y0 + (y + 1) * scale, x0 + x * scale:x0 + (x + 1) * scale] = PALETTE[v]


def pair_canvas(pic, msk, h, colony):
    """the queen's two cells for heading h on a 32 x 32 canvas (index array, -1 transparent)"""
    cells = {0: ((8, 0), (8, 16)), 1: ((16, 0), (0, 16)), 2: ((16, 8), (0, 8)), 3: ((16, 16), (0, 0)),
             4: ((8, 16), (8, 0)), 5: ((0, 16), (16, 0)), 6: ((0, 8), (16, 8)), 7: ((0, 0), (16, 16))}[h]
    pc = recolour(pic, msk, colony)
    cv = np.full((32, 32), -1, np.int16)
    for (x, y), base in zip(cells, (0x60 + h, 0x68 + h)):
        t = tile(pc, base)
        sub = cv[y:y + 16, x:x + 16]
        sub[t >= 0] = t[t >= 0]
    return cv


def make_preview(path, surf, nest):
    from PIL import Image, ImageDraw
    S = 3
    colonies = ('yellow', 'black', 'red')
    pw = SHEET_W * S
    gap = 24
    W = 3 * pw + 2 * gap + 40
    sel = [0x10, 0x11, 0x12, 0x18, 0x28, 0x08, 0x20, 0x30, 0x38, 0x40, 0x03, 0x06, 0x07, 0x70, 0x73]
    surf_grounds = [('tan 11', ground(SP, SP, TAN, (BRN, LGR), 0.05, 1)), ('brown 10', np.full((SP, SP), BRN, np.int16)),
                    ('white floor 0', np.full((SP, SP), WHT, np.int16)), ('light grey 12', np.full((SP, SP), LGR, np.int16))]
    tun = yard_tunnel_tiles()
    nest_grounds = [('tunnel, yard tile 0x90', tun[0]), ('tunnel, yard tile 0x93', tun[3]),
                    ('brown soil 10', np.full((SP, SP), BRN, np.int16))]
    sel_w = len(sel) * SP * S
    H = 24 + 2 * (SHEET_H * S + 30) + 2 * (32 * S + 30) + (len(surf_grounds) + len(nest_grounds)) * (SP * S + 26) + 30
    canvas = np.zeros((H, W, 3), np.uint8)
    canvas[:] = (236, 236, 236)
    img_y = 8
    texts = []

    def label(x, y, s):
        texts.append((x, y, s))

    for sheet_name, (pic, msk), gbg in (('SURFACE sheet: yellow (player) | black colony | red colony, on tan', surf,
                                         lambda s: ground(SHEET_W, SHEET_H, TAN, (BRN, LGR), 0.05, 3)),
                                        ('NEST sheet: yellow | black | red, on the yard sheet\'s light tunnel tiles (0x90..0x97)', nest,
                                         lambda s: tunnel_ground(SHEET_W, SHEET_H, 4))):
        label(8, img_y, sheet_name)
        img_y += 16
        for i, col in enumerate(colonies):
            x0 = 8 + i * (pw + gap)
            bg = gbg(0)
            canvas[img_y:img_y + SHEET_H * S, x0:x0 + pw] = 0
            paint(canvas, recolour(pic, msk, col), x0, img_y, S, bg)
        img_y += SHEET_H * S + 14
    for sheet_name, (pic, msk), grounds in (('queens, the 8 headings: surface', surf, ground(32, 32, TAN, (BRN, LGR), 0.05, 5)),
                                            ('queens, the 8 headings: nest', nest, tunnel_ground(32, 32, 6))):
        label(8, img_y, sheet_name + '  (yellow | black | red; N NE E SE S SW W NW)')
        img_y += 16
        for i, col in enumerate(colonies):
            for h in range(8):
                cv = pair_canvas(pic, msk, h, col)
                x0 = 8 + (i * 8 + h) * (32 * S + 8)
                paint(canvas, cv, x0, img_y, S, grounds)
        img_y += 32 * S + 14
    for title, (pic, msk), grounds in (('ground test, surface sheet', surf, surf_grounds), ('ground test, nest sheet', nest, nest_grounds)):
        for gname, gt in grounds:
            label(8, img_y, '%s: %s' % (title, gname))
            img_y += 14
            for i, col in enumerate(colonies):
                pc = recolour(pic, msk, col)
                for j, n in enumerate(sel):
                    x0 = 8 + i * (sel_w + 12) + j * SP * S
                    paint(canvas, tile(pc, n), x0, img_y, S, gt)
            img_y += SP * S + 12
    im = Image.fromarray(canvas[:img_y + 8])
    d = ImageDraw.Draw(im)
    for x, y, s in texts:
        d.text((x, y), s, fill=(0, 0, 0))
    im.save(path)


# ---------------------------------------------------------------------------------------------------------------
def run_check(fn, *args):
    """the checks are asserts; `--dev` (while drawing) prints the first failure and carries on"""
    if '--dev' not in sys.argv:
        fn(*args)
        return
    try:
        fn(*args)
    except AssertionError as e:
        print('CHECK FAILED:', fn.__name__, e)


def main():
    out = {}
    for view, legend, stem in (('surface', LEGEND, 'surface'), ('nest', LEGEND_NEST, 'nest')):
        grids = sprite_grids(view)
        pic, msk = to_arrays(grids, legend)
        run_check(check_sheet, view, pic, msk, grids)
        run_check(check_queen, view, pic)
        write_pix(os.path.join(HERE, stem + '.pix'), pic,
                  'OpenSimAnt clean pack: the ants seen %s. 16 x 8 sprites, the yellow ant (see ant_sprites.md).'
                  % ('from above' if view == 'surface' else 'in the nests\' cross-section'))
        write_pix(os.path.join(HERE, stem + '_recolour.pix'), pic,
                  'recolour mask of %s.pix' % stem, msk)
        out[view] = (pic, msk)
    # re-read what was written and check the files themselves
    for stem in ('surface', 'nest'):
        pr = read_pix(os.path.join(HERE, stem + '.pix'))
        mr = read_pix(os.path.join(HERE, stem + '_recolour.pix'))
        assert len(pr) == 128 and len(mr) == 128, stem
        assert all(len(r) == 256 for r in pr + mr), stem
        assert all(set(r) <= set('.0123456789abcdef') for r in pr), stem
        assert all(set(r) <= set('.01') for r in mr), stem
        for ry, my in zip(pr, mr):
            assert all(not (p == '.' and m == '1') for p, m in zip(ry, my)), stem + ': a 1 on a transparent pixel'
            assert all(not (m == '1' and p not in '12') for p, m in zip(ry, my)), stem + ': a 1 on a pixel that is not index 1 or 2'
            assert all(not (m != '1' and p == '1') for p, m in zip(ry, my)), stem + ': an unrecoloured yellow pixel'
    try:
        make_preview(os.path.join(HERE, 'preview.png'), out['surface'], out['nest'])
    except ImportError:
        print('Pillow is not installed: preview.png not written')
    print('ok: surface.pix, nest.pix, the two recolour masks and preview.png written' +
          (' (--dev: failed checks only reported)' if '--dev' in sys.argv else '; all checks passed'))


if __name__ == '__main__':
    main()
