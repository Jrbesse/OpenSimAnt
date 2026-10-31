"""uilib: the shared helper of the UI bitmaps (lettering, bevels, wells, callouts, rotated text,
inversion check, registry and .pix writer).  See README.md.  Coordinates: pixels from the top-left, the
second corner of every rectangle is EXCLUSIVE (as in the spec)."""
import os
import re
import numpy as np

HEX = '0123456789abcdef'
T = -1  # transparent

# ---- palette (published Apple system colours, only used for the contrast maths) --------------------------------
RGB = {0: 'FFFFFF', 1: 'FCF305', 2: 'FF6402', 3: 'DD0806', 4: 'F20884', 5: '4600A5', 6: '0000D4', 7: '02ABEA',
       8: '1FB714', 9: '006411', 10: '562C05', 11: '90713A', 12: 'C0C0C0', 13: '808080', 14: '404040', 15: '000000'}


def _lin(v):
    v /= 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def lum(c):
    h = RGB[c]
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def inv_ok(face, ink, ratio=3.0):
    """True when ink reads on face both as drawn and inverted (every index XOR 15)."""
    return contrast(face, ink) >= ratio and contrast(face ^ 15, ink ^ 15) >= ratio


# ---- colour roles ----------------------------------------------------------------------------------------------
FACE = 12          # panel / button face, window background
WELL = 0           # wells (numbers, graphs, text)
HI = 0             # highlight edge (top, left)
SH = 13            # shadow edge (bottom, right)
DSH = 14           # deep shadow
INK = 15           # outlines, lettering on buttons
# Lettering of anything the game INVERTS (menu entries, palette options, buttons): blue 6 and the colony colours
# fail the 3:1 rule when inverted (blue 6 on 12 becomes dark green 9 on red 3 = 1.4:1), so it is black.  The spec's
# blue / red / brown menu words are kept as a switch: set MENU_COLOURED = True to use them (the check will fail).
MENU_COLOURED = False
HEADING = 6        # headings that are not inverted (cards, notices, group headings)
BLACKCOL, REDCOL, PLAYER = 15, 3, 1


# ---- the image ---------------------------------------------------------------------------------------------------
class Img:
    def __init__(self, w, h, fill=FACE):
        self.w, self.h = w, h
        self.a = np.full((h, w), fill, dtype=np.int16)

    # basic
    def px(self, x, y, c):
        if c is not None and c != T and 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = c

    def set_any(self, x, y, c):  # may write T
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = c

    def get(self, x, y):
        return int(self.a[y, x])

    def rect(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(self.w, x1), min(self.h, y1)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = c

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y + 1, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x + 1, y1, c)

    def frame(self, x0, y0, x1, y1, c, t=1):
        self.rect(x0, y0, x1, y0 + t, c)
        self.rect(x0, y1 - t, x1, y1, c)
        self.rect(x0, y0, x0 + t, y1, c)
        self.rect(x1 - t, y0, x1, y1, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        """Bresenham, inclusive end points; t x t square brush."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            for i in range(t):
                for j in range(t):
                    self.px(x0 + i, y0 + j, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def poly(self, pts, c):
        """Filled polygon (even-odd, pixel centres)."""
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(int(min(ys)), int(max(ys)) + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
                if (ya <= yc < yb) or (yb <= yc < ya):
                    xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(np.ceil(xs[k] - 0.5)), int(np.ceil(xs[k + 1] - 0.5))):
                    self.px(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                    self.px(x, y, c)

    def ellipse_o(self, cx, cy, rx, ry, fill, outline):
        self.ellipse(cx, cy, rx + 0.9, ry + 0.9, outline)
        self.ellipse(cx, cy, rx, ry, fill)

    def blit(self, src, x, y):
        for yy in range(src.h):
            for xx in range(src.w):
                v = int(src.a[yy, xx])
                if v != T:
                    self.px(x + xx, y + yy, v)

    def crop(self, x0, y0, x1, y1):
        o = Img(x1 - x0, y1 - y0)
        o.a = self.a[y0:y1, x0:x1].copy()
        return o

    def copy(self):
        o = Img(self.w, self.h)
        o.a = self.a.copy()
        return o

    def stamp(self, mask, x, y, c):
        h, w = mask.shape
        for yy in range(h):
            for xx in range(w):
                if mask[yy, xx]:
                    self.px(x + xx, y + yy, c)

    def dump(self, x0=0, y0=0, x1=None, y1=None):
        x1 = self.w if x1 is None else x1
        y1 = self.h if y1 is None else y1
        out = []
        for y in range(y0, y1):
            out.append(''.join('.' if self.a[y, x] == T else HEX[self.a[y, x]] for x in range(x0, x1)))
        return '\n'.join(out)


def from_map(rows, legend, bg=FACE):
    """Hand-drawn picture: rows of characters, legend char -> palette index ('.' = bg)."""
    h, w = len(rows), len(rows[0])
    o = Img(w, h, bg)
    for y, r in enumerate(rows):
        assert len(r) == w, (y, len(r), w)
        for x, ch in enumerate(r):
            if ch != '.':
                o.a[y, x] = legend[ch]
    return o


# ---- shapes ------------------------------------------------------------------------------------------------------
def bevel(img, x0, y0, x1, y1, face=FACE, raised=True, deep=False, hi=HI, sh=SH, dsh=DSH):
    """A bevelled box inside the rectangle: 1-px highlight top/left, shadow bottom/right (deep: 2 px)."""
    a, b = (hi, sh) if raised else (sh, hi)
    if face is not None:
        img.rect(x0, y0, x1, y1, face)
    img.rect(x0, y0, x1 - 1, y0 + 1, a)
    img.rect(x0, y0, x0 + 1, y1 - 1, a)
    img.rect(x0 + 1, y1 - 1, x1, y1, b)
    img.rect(x1 - 1, y0 + 1, x1, y1, b)
    if deep:
        d = dsh if raised else hi
        img.rect(x0 + 1, y1 - 1, x1, y1, d)
        img.rect(x1 - 1, y0 + 1, x1, y1, d)
        img.rect(x0 + 2, y1 - 2, x1 - 1, y1 - 1, b)
        img.rect(x1 - 2, y0 + 2, x1 - 1, y1 - 1, b)


def chrome_button(w, h, face=FACE):
    """Window-chrome button: black outline, 1-px highlight, 1-px shadow, face."""
    o = Img(w, h, face)
    o.frame(0, 0, w, h, INK)
    bevel(o, 1, 1, w - 1, h - 1, face)
    return o


def well(img, x0, y0, x1, y1, fill=WELL, frame=INK):
    """A 'well': the rectangle is filled flat; a 1-px frame is drawn OUTSIDE it."""
    img.rect(x0, y0, x1, y1, fill)
    img.frame(x0 - 1, y0 - 1, x1 + 1, y1 + 1, frame)


def groove(img, x0, y0, x1, y1):
    """Thin divider: shadow line with a highlight line next to it (horizontal if wider than tall)."""
    if (x1 - x0) >= (y1 - y0):
        img.rect(x0, y0, x1, y0 + 1, SH)
        img.rect(x0, y0 + 1, x1, y0 + 2, HI)
    else:
        img.rect(x0, y0, x0 + 1, y1, SH)
        img.rect(x0 + 1, y0, x0 + 2, y1, HI)


def tri(img, cx, cy, s, d, c):
    """Small solid triangle, 'size' s (half length), direction r/l/u/d, centred on cx, cy."""
    for i in range(s + 1):
        n = s - i
        if d == 'r':
            img.vline(cx - s // 2 + i, cy - n, cy + n + 1, c)
        elif d == 'l':
            img.vline(cx + s // 2 - i, cy - n, cy + n + 1, c)
        elif d == 'u':
            img.hline(cx - n, cx + n + 1, cy + s // 2 - i, c)
        else:
            img.hline(cx - n, cx + n + 1, cy - s // 2 + i, c)


def inv(img, x0, y0, x1, y1):
    o = img.copy()
    o.a[y0:y1, x0:x1] = o.a[y0:y1, x0:x1] ^ 15
    return o


# ---- the two pixel faces -----------------------------------------------------------------------------------------
_G = {}


def _g(ch, spec):
    _G[ch] = spec


for _c, _s in {
    'A': ".###.|#...#|#...#|#####|#...#|#...#|#...#", 'B': "####.|#...#|#...#|####.|#...#|#...#|####.",
    'C': ".###.|#...#|#....|#....|#....|#...#|.###.", 'D': "####.|#...#|#...#|#...#|#...#|#...#|####.",
    'E': "#####|#....|#....|####.|#....|#....|#####", 'F': "#####|#....|#....|####.|#....|#....|#....",
    'G': ".###.|#...#|#....|#.###|#...#|#...#|.###.", 'H': "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    'I': "###|.#.|.#.|.#.|.#.|.#.|###", 'J': "..##|...#|...#|...#|...#|#..#|.##.",
    'K': "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", 'L': "#...|#...|#...|#...|#...|#...|####",
    'M': "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", 'N': "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    'O': ".###.|#...#|#...#|#...#|#...#|#...#|.###.", 'P': "####.|#...#|#...#|####.|#....|#....|#....",
    'Q': ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", 'R': "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    'S': ".####|#....|#....|.###.|....#|....#|####.", 'T': "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    'U': "#...#|#...#|#...#|#...#|#...#|#...#|.###.", 'V': "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    'W': "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#", 'X': "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    'Y': "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", 'Z': "#####|....#|...#.|..#..|.#...|#....|#####",
    'a': "x.##.|...#|.###|#..#|.###", 'b': "#...|#...|###.|#..#|#..#|#..#|###.",
    'c': "x.##.|#..#|#...|#..#|.##.", 'd': "...#|...#|.###|#..#|#..#|#..#|.###",
    'e': "x.##.|#..#|####|#...|.###", 'f': ".##|#..|###|#..|#..|#..|#..",
    'g': "x.###|#..#|#..#|#..#|.###/...#|.##.", 'h': "#...|#...|###.|#..#|#..#|#..#|#..#",
    'i': "#|.|#|#|#|#|#", 'j': "..#|...|..#|..#|..#|..#|..#/..#|##.",
    'k': "#...|#...|#..#|#.#.|##..|#.#.|#..#", 'l': "#|#|#|#|#|#|#",
    'm': "x##.#.|#.#.#|#.#.#|#.#.#|#.#.#", 'n': "x###.|#..#|#..#|#..#|#..#",
    'o': "x.##.|#..#|#..#|#..#|.##.", 'p': "x###.|#..#|#..#|#..#|###./#...|#...",
    'q': "x.###|#..#|#..#|#..#|.###/...#|...#", 'r': "x#.#|##.|#..|#..|#..",
    's': "x.###|#...|.##.|...#|###.", 't': "...|.#.|###|.#.|.#.|.#.|..#",
    'u': "x#..#|#..#|#..#|#..#|.###", 'v': "x#...#|#...#|#...#|.#.#.|..#..",
    'w': "x#...#|#...#|#.#.#|#.#.#|.#.#.", 'x': "x#..#|#..#|.##.|#..#|#..#",
    'y': "x#..#|#..#|#..#|#..#|.###/...#|.##.", 'z': "x####|...#|.##.|#...|####",
    '0': ".##.|#..#|#..#|#..#|#..#|#..#|.##.", '1': ".#.|##.|.#.|.#.|.#.|.#.|###",
    '2': ".##.|#..#|...#|..#.|.#..|#...|####", '3': ".##.|#..#|...#|.##.|...#|#..#|.##.",
    '4': "..#.|.##.|#.#.|#..#|####|..#.|..#.", '5': "####|#...|###.|...#|...#|#..#|.##.",
    '6': ".##.|#...|###.|#..#|#..#|#..#|.##.", '7': "####|...#|..#.|.#..|.#..|.#..|.#..",
    '8': ".##.|#..#|#..#|.##.|#..#|#..#|.##.", '9': ".##.|#..#|#..#|.###|...#|...#|.##.",
    ' ': "..|..|..|..|..|..|..", '.': ".|.|.|.|.|.|#", ',': ".|.|.|.|.|#|#/#",
    ':': ".|.|#|.|.|#|.", ';': ".|.|#|.|.|#|#/#", '-': "...|...|...|###|...|...|...",
    '/': "..#|..#|.#.|.#.|.#.|#..|#..", '?': ".###.|#...#|....#|...#.|..#..|.....|..#..",
    '!': "#|#|#|#|#|.|#", '(': "..#|.#.|#..|#..|#..|.#.|..#", ')': "#..|.#.|..#|..#|..#|.#.|#..",
    '+': "...|...|.#.|###|.#.|...|...", '=': "....|....|####|....|####|....|....",
    "'": "#|#|.|.|.|.|.", '%': "##..#|##.#.|...#.|..#..|.#...|.#.##|#..##",
    '>': "...|#..|.#.|..#|.#.|#..|...", '<': "...|..#|.#.|#..|.#.|..#|...",
    '*': "...|#.#|.#.|###|.#.|#.#|...", '&': ".##.|#..#|.##.|.##.|#..#|#..#|.###",
    '"': "#.#|#.#|...|...|...|...|...", ':': ".|.|#|.|.|#|.",
}.items():
    _g(_c, _s)


def _parse(spec):
    desc = []
    if '/' in spec and spec.count('/') == 1 and not spec.startswith('/'):
        # '/' is also a glyph ('/' key has no leading x and no second part): only treat as descender if rows exist
        pass
    main, _, d = spec.partition('/')
    xh = main.startswith('x')
    rows = main[1:].split('|') if xh else main.split('|')
    w = len(rows[0])
    for r in rows:
        assert len(r) == w, spec
    if xh:
        rows = ['.' * w] * 2 + rows
    assert len(rows) == 7, spec
    if d:
        desc = d.split('|')
        for r in desc:
            assert len(r) == w, spec
    rows = rows + desc + ['.' * w] * (2 - len(desc))
    return rows, xh


# '/' key conflicts with the descender separator: define it by hand
def _glyph_rows(ch):
    if ch == '/':
        rows = ["..#", "..#", ".#.", ".#.", ".#.", "#..", "#.."] + ['...'] * 2
        return rows, False
    return _parse(_G[ch])


class Face:
    def __init__(self, name, bold=False, tall=False):
        self.name, self.bold, self.tall = name, bold, tall
        self.cap = 8 if tall else 7
        self.height = self.cap + 2
        self._c = {}

    def glyph(self, ch):
        if ch not in self._c:
            if ch not in _G:
                ch2 = '?'
            else:
                ch2 = ch
            rows, lower = _glyph_rows(ch2)
            if self.tall:
                i = 4 if (lower or ch2.islower()) else 3
                rows = rows[:i + 1] + [rows[i]] + rows[i + 1:]
            if self.bold and ch2 != ' ':
                rows = [r + '.' for r in rows] if False else [self._smear(r) for r in rows]
            arr = np.array([[c == '#' for c in r] for r in rows], dtype=bool)
            self._c[ch] = arr
        return self._c[ch]

    @staticmethod
    def _smear(r):
        o = ['.'] * (len(r) + 1)
        for i, c in enumerate(r):
            if c == '#':
                o[i] = '#'
                o[i + 1] = '#'
        return ''.join(o)

    def adv(self, ch):
        return self.glyph(ch).shape[1] + 1

    def width(self, s):
        return sum(self.adv(c) for c in s) - 1 if s else 0

    def render(self, s, scale=1):
        h = self.height
        out = np.zeros((h, max(1, self.width(s))), dtype=bool)
        x = 0
        for ch in s:
            g = self.glyph(ch)
            out[:, x:x + g.shape[1]] |= g
            x += g.shape[1] + 1
        if scale > 1:
            out = np.kron(out, np.ones((scale, scale), dtype=bool))
        return out


SMALL = Face('small')
LABEL = Face('label', bold=True)
LABEL_TALL = Face('label_tall', bold=True, tall=True)


def text(img, x, y, s, face=LABEL, color=INK, scale=1, shadow=None, outline=None):
    """Draw s with its capital top at y.  Returns the x just past the ink."""
    m = face.render(s, scale)
    if outline is not None:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    img.stamp(m, x + dx, y + dy, outline)
    if shadow is not None:
        img.stamp(m, x + scale, y + scale, shadow)
    img.stamp(m, x, y, color)
    return x + m.shape[1]


def text_c(img, cx, y, s, face=LABEL, color=INK, scale=1, **kw):
    w = face.width(s) * scale
    return text(img, cx - w // 2, y, s, face, color, scale, **kw)


def text_r(img, xr, y, s, face=LABEL, color=INK, scale=1, **kw):
    w = face.width(s) * scale
    return text(img, xr - w, y, s, face, color, scale, **kw)


def text_rot(img, x, y, s, face=SMALL, color=14):
    """Text rotated 90 degrees counter-clockwise (reads bottom to top); (x, y) = top-left of the rotated block."""
    m = np.rot90(face.render(s), 1)
    img.stamp(m, x, y, color)
    return m.shape  # (rows, cols)


def ink_box(img_or_mask, bg):
    a = img_or_mask.a if isinstance(img_or_mask, Img) else img_or_mask
    ys, xs = np.where(a != bg)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else None


# ---- text wrapping with **bold** ------------------------------------------------------------------------------
def wrap(markup, width, reg_face=SMALL, bold_face=LABEL):
    toks = [(m.group(1), True) if m.group(1) else (m.group(2), False)
            for m in re.finditer(r'\*\*(.+?)\*\*|(\S+)', markup)]
    lines, cur, cw = [], [], 0
    sp = reg_face.adv(' ')
    for t, b in toks:
        f = bold_face if b else reg_face
        w = f.width(t)
        if cur and cw + sp + w > width:
            lines.append(cur)
            cur, cw = [], 0
        cw += (sp if cur else 0) + w
        cur.append((t, b))
    if cur:
        lines.append(cur)
    return lines


def draw_line(img, x, y, toks, color, reg_face=SMALL, bold_face=LABEL, underline=False):
    sp = reg_face.adv(' ')
    x0 = x
    for i, (t, b) in enumerate(toks):
        f = bold_face if b else reg_face
        if i:
            x += sp
        x = text(img, x, y, t, f, color) + 0
    if underline:
        img.hline(x0, x, y + 9, color)
    return x


# ---- help callouts (overlays: only colours 0, 6, 14) ---------------------------------------------------------------
LINE_PITCH = 10


def callout_size(lines, face=SMALL, padx=3):
    w = max(face.width(s) for s in lines) + 2 * padx + 2
    h = 13 + LINE_PITCH * (len(lines) - 1)
    return w, h


def callout(img, x, y, lines, w=None, face=SMALL, padx=3, fill=0, frame=14, ink=14):
    cw, ch = callout_size(lines, face, padx)
    w = w or cw
    img.rect(x, y, x + w, y + ch, fill)
    img.frame(x, y, x + w, y + ch, frame)
    for i, s in enumerate(lines):
        text(img, x + 1 + padx, y + 2 + LINE_PITCH * i, s, face, ink)
    return (x, y, x + w, y + ch)


def callout_rot(img, x, y, s, face=SMALL, fill=0, frame=14, ink=14, h=None):
    """Panel with text rotated 90 deg ccw; 12 wide (frame, 1 pad, 9 text rows, frame)."""
    tw = face.width(s)
    h = h or tw + 6
    w = 12
    img.rect(x, y, x + w, y + h, fill)
    img.frame(x, y, x + w, y + h, frame)
    text_rot(img, x + 2, y + 1 + (h - 2 - tw) // 2, s, face, ink)
    return (x, y, x + w, y + h)


def hit(r, p, tol=0):
    return r[0] - tol <= p[0] < r[2] + tol and r[1] - tol <= p[1] < r[3] + tol


# ---- registry / checks / output ---------------------------------------------------------------------------------
class Reg:
    def __init__(self):
        self.img = {}
        self.meta = {}   # id -> dict(size, masked, only1plane, colours, what)
        self.flat = []   # (id, rect, colour, what)
        self.spots = []  # (id, rect)
        self.tips = []   # (id, name, (x, y), target rect, tol)
        self.inv = []    # (id, rect, face, ink, what)
        self.checks = []
        self.panels = {}  # id -> [rects] (callout panels)

    def add(self, bid, img, size, masked=False, colours=None, what=''):
        assert bid not in self.img, bid
        self.img[bid] = img
        self.meta[bid] = dict(size=size, masked=masked, colours=colours, what=what)

    def flat_rect(self, bid, rect, colour, what=''):
        self.flat.append((bid, rect, colour, what))

    def spot(self, bid, rect):
        self.spots.append((bid, rect))

    def tip(self, bid, name, pt, target, tol=0):
        self.tips.append((bid, name, pt, target, tol))

    def inverted(self, bid, rect, face, ink, what=''):
        self.inv.append((bid, rect, face, ink, what))

    def check(self, fn):
        self.checks.append(fn)
        return fn


def leader(img, reg, bid, name, pts, target, tol=0, color=6, dot=False):
    """Polyline of 1-px lines; the LAST point is the tip, recorded for the target check."""
    for a, b in zip(pts, pts[1:]):
        img.line(a[0], a[1], b[0], b[1], color)
    reg.tip(bid, name, pts[-1], target, tol)


def run_generic_checks(reg):
    n = 0
    for bid, img in reg.img.items():
        m = reg.meta[bid]
        w, h = m['size']
        assert (img.w, img.h) == (w, h), (bid, img.w, img.h, w, h)
        a = img.a
        assert a.min() >= T and a.max() <= 15, bid
        tr = int((a == T).sum())
        if m['masked']:
            assert tr > 0, (bid, 'masked picture without transparent pixels')
        else:
            assert tr == 0, (bid, 'opaque picture with transparent pixels')
        if m['colours'] is not None:
            used = set(int(v) for v in np.unique(a)) - {T}
            assert used <= set(m['colours']), (bid, used - set(m['colours']))
        n += 1
    for bid, r, colour, what in reg.flat:
        sub = reg.img[bid].a[r[1]:r[3], r[0]:r[2]]
        assert sub.size and (sub == colour).all(), (bid, r, colour, what, sorted(set(sub.flatten().tolist())))
    for bid, r in reg.spots:
        sub = reg.img[bid].a[r[1]:r[3], r[0]:r[2]]
        assert (sub == FACE).all(), (bid, r, 'icon spot not flat light grey')
    for bid, name, p, r, tol in reg.tips:
        assert hit(r, p, tol), (bid, name, p, r)
    for bid, r, face, ink, what in reg.inv:
        sub = reg.img[bid].a[r[1]:r[3], r[0]:r[2]]
        vals, cnt = np.unique(sub, return_counts=True)
        dom = int(vals[cnt.argmax()])
        assert dom == face, (bid, r, what, 'dominant colour', dom, 'expected face', face)
        assert (sub == ink).any(), (bid, r, what, 'ink colour missing', ink)
        assert inv_ok(face, ink), (bid, r, what, 'contrast', contrast(face, ink), contrast(face ^ 15, ink ^ 15))
    for fn in reg.checks:
        fn(reg)
    return n


def write_pix(path, img, comment):
    lines = ['# ' + comment, '# %d x %d' % (img.w, img.h)]
    for y in range(img.h):
        lines.append(''.join('.' if v == T else HEX[v] for v in img.a[y]))
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
