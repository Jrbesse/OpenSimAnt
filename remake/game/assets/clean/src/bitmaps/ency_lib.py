"""ency_lib.py - drawing tools for the encyclopedia's pictures (SHARED_<id>.pix, 1 plane, 0 = paper, f = ink).

A Cv is a 1-bit canvas.  Every shape goes through an optional transform (cv.at(...)) so one drawing function can be used
at any scale, rotation or mirrored.  Tones are ordered-dither patterns registered to the PICTURE (not to the subject).
Boxed labels, leaders and the other things the script checks are recorded on the canvas as they are drawn.
"""
import math
import os
from contextlib import contextmanager

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def rnd(v):
    return int(math.floor(v + 0.5))


# ----------------------------------------------------------------------------------------------------------- tones
class Tone:
    def __init__(self, fn):
        self.fn = fn


def lvl(t):
    """ordered dither, t/16 of the pixels black"""
    return Tone(lambda xx, yy, cv: BAYER[yy % 4, xx % 4] < t)


W_ = lvl(0)
K_ = lvl(16)
T1 = lvl(2)      # very light
LT = lvl(4)      # light, 25 %
MD = lvl(8)      # mid, checkerboard
DK = lvl(12)     # dark, 3 : 1 mesh
H1 = Tone(lambda xx, yy, cv: (xx + yy) % 3 == 0)           # hatch /
H2 = Tone(lambda xx, yy, cv: (xx - yy) % 3 == 0)           # hatch \
H1W = Tone(lambda xx, yy, cv: (xx + yy) % 4 == 0)          # wide hatch /
H2W = Tone(lambda xx, yy, cv: (xx - yy) % 4 == 0)
HV = Tone(lambda xx, yy, cv: xx % 3 == 0)
HH = Tone(lambda xx, yy, cv: yy % 3 == 0)
HX = Tone(lambda xx, yy, cv: ((xx + yy) % 3 == 0) | ((xx - yy) % 3 == 0))   # cross hatch
DOT = Tone(lambda xx, yy, cv: (xx % 3 == 1) & (yy % 3 == 1))


def grad(cx, cy, r, lo, hi, d=(0.7, 0.7)):
    """dither gradient, lo (upper left) .. hi (lower right) over the radius r (local units)"""
    def fn(xx, yy, cv):
        c = cv._pt((cx, cy))
        rr = max(r * cv.sc(), 1.0)
        t = ((xx - c[0]) * d[0] + (yy - c[1]) * d[1]) / rr * 0.5 + 0.5
        level = lo + (hi - lo) * np.clip(t, 0, 1)
        return BAYER[yy % 4, xx % 4] < level
    return Tone(fn)


# ---------------------------------------------------------------------------------------------------------- font
_G = {}


def _def(chars, s):
    pass


_CAPS = {
    'A': ".###./#...#/#...#/#####/#...#/#...#/#...#",
    'B': "###./#..#/#..#/###./#..#/#..#/###.",
    'C': ".###/#.../#.../#.../#.../#.../.###",
    'D': "###./#..#/#..#/#..#/#..#/#..#/###.",
    'E': "####/#.../#.../###./#.../#.../####",
    'F': "####/#.../#.../###./#.../#.../#...",
    'G': ".###./#...#/#..../#.###/#...#/#...#/.###.",
    'H': "#...#/#...#/#...#/#####/#...#/#...#/#...#",
    'I': "###/.#./.#./.#./.#./.#./###",
    'J': "..##/...#/...#/...#/#..#/#..#/.##.",
    'K': "#..#/#..#/#.#./##../#.#./#..#/#..#",
    'L': "#.../#.../#.../#.../#.../#.../####",
    'M': "#...#/##.##/#.#.#/#.#.#/#...#/#...#/#...#",
    'N': "#...#/##..#/##..#/#.#.#/#..##/#..##/#...#",
    'O': ".###./#...#/#...#/#...#/#...#/#...#/.###.",
    'P': "###./#..#/#..#/###./#.../#.../#...",
    'Q': ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#",
    'R': "###./#..#/#..#/###./#.#./#..#/#..#",
    'S': ".###/#.../#.../.##./...#/...#/###.",
    'T': "#####/..#../..#../..#../..#../..#../..#..",
    'U': "#...#/#...#/#...#/#...#/#...#/#...#/.###.",
    'V': "#...#/#...#/#...#/#...#/.#.#./.#.#./..#..",
    'W': "#...#/#...#/#...#/#.#.#/#.#.#/##.##/#...#",
    'X': "#...#/#...#/.#.#./..#../.#.#./#...#/#...#",
    'Y': "#...#/#...#/.#.#./..#../..#../..#../..#..",
    'Z': "####/...#/..#./.#../#.../#.../####",
}
_LOW = {
    'a': "//.##./...#/.###/#..#/.###",
    'b': "#.../#.../###./#..#/#..#/#..#/###.",
    'c': "//.###/#.../#.../#.../.###",
    'd': "...#/...#/.###/#..#/#..#/#..#/.###",
    'e': "//.##./#..#/####/#.../.###",
    'f': ".##/#../###/#../#../#../#..",
    'g': "//.###/#..#/.###/...#/###.",
    'h': "#.../#.../###./#..#/#..#/#..#/#..#",
    'i': "#//#/#/#/#/#",
    'j': "..#//..#/..#/..#/..#/##.",
    'k': "#.../#.../#..#/#.#./##../#.#./#..#",
    'l': "#/#/#/#/#/#/#",
    'm': "//####./#.#.#/#.#.#/#.#.#/#.#.#",
    'n': "//###./#..#/#..#/#..#/#..#",
    'o': "//.##./#..#/#..#/#..#/.##.",
    'p': "//###./#..#/#..#/###./#...",
    'q': "//.###/#..#/#..#/.###/...#",
    'r': "//#.#/##./#../#../#..",
    's': "//.###/#.../.##./...#/###.",
    't': "/.#./###/.#./.#./.#./.##",
    'u': "//#..#/#..#/#..#/#..#/.###",
    'v': "//#...#/#...#/.#.#./.#.#./..#..",
    'w': "//#...#/#.#.#/#.#.#/#.#.#/.#.#.",
    'x': "//#...#/.#.#./..#../.#.#./#...#",
    'y': "//#..#/#..#/.###/...#/###.",
    'z': "//####/..#./.#../#.../####",
}
_NARROW = {   # narrow variants used only where a word must fit a very small box ('Queen' in a 28 px box)
    '1': ".##./#..#/#..#/#..#/#..#/#.#./.#.#",
    '2': "//#.#/#.#/#.#/#.#/###",
    '3': "//##./#.#/#.#/#.#/#.#",
}
_PUN = {
    "'": ['#', '#', '', '', '', '', ''],
    '.': ['', '', '', '', '', '', '#'],
    '-': ['', '', '', '###', '', '', ''],
    ',': ['', '', '', '', '', '#', '#'],
}


def _build():
    for d in (_CAPS, _LOW, _NARROW):
        for ch, s in d.items():
            rows = s.split('/')
            assert len(rows) == 7, (ch, len(rows))
            w = max(len(r) for r in rows)
            _G[ch] = [r.ljust(w, '.') if r else '.' * w for r in rows]
    for ch, rows in _PUN.items():
        w = max(len(r) for r in rows)
        _G[ch] = [r.ljust(w, '.') if r else '.' * w for r in rows]
    _G[' '] = ['..'] * 7


_build()
EXTRA = {'i': 1, 'l': 1, 'j': 0}   # extra gap after these (advance 3 for i and l)


def face_rows(face):
    """row indices of the 7-row base glyph kept by a face"""
    if face == 'b7':
        return [0, 1, 2, 3, 4, 5, 6]
    if face == 'b8':
        return [0, 1, 2, 3, 3, 4, 5, 6]
    if face == 'r6':
        return [0, 1, 2, 3, 4, 6]
    raise ValueError(face)


def face_cap(face):
    return {'b7': 7, 'b8': 8, 'r6': 6}[face]


def glyph(ch, face):
    g = _G[ch]
    return [g[i] for i in face_rows(face)]


def adv(ch):
    if ch == ' ':
        return 3
    return len(_G[ch][0]) + 1 + EXTRA.get(ch, 0)


def text_w(s, face='b7'):
    return sum(adv(c) for c in s) - 1 - (EXTRA.get(s[-1], 0) if s else 0)


def text_h(face):
    return len(face_rows(face))


# ------------------------------------------------------------------------------------------------------ transform
class Tf:
    def __init__(self, ox=0.0, oy=0.0, sc=1.0, ang=0.0, flip=False, px=0.0, py=0.0):
        self.ox, self.oy, self.s, self.flip, self.px, self.py = ox, oy, sc, flip, px, py
        self.c, self.sn = math.cos(ang), math.sin(ang)

    def __call__(self, p):
        x = p[0] - self.px
        y = p[1] - self.py
        if self.flip:
            x = -x
        return (self.ox + self.s * (self.c * x - self.sn * y), self.oy + self.s * (self.sn * x + self.c * y))


def catmull(pts, closed=True, n=6):
    """Catmull-Rom subdivision of a control polygon"""
    P = list(pts)
    m = len(P)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = P[(i - 1) % m] if (closed or i > 0) else P[i]
        p1 = P[i]
        p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if (closed or i + 2 < m) else P[(i + 1) % m]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(tuple(P[-1]))
    return out


# --------------------------------------------------------------------------------------------------------- canvas
class Cv:
    def __init__(self, w, h, name=''):
        self.w, self.h, self.name = w, h, name
        self.a = np.zeros((h, w), np.uint8)
        self.al = np.zeros((h, w), bool)
        self.yy, self.xx = np.mgrid[0:h, 0:w]
        self.tf = None
        self.boxes = {}
        self.leaders = []
        self.strings = []
        self.cut_rows = []
        self.cut_cols = []
        self.arrows = []
        self.extra = {}

    # transform ---------------------------------------------------------------------------------------------
    def _pt(self, p):
        return self.tf(p) if self.tf else p

    def sc(self):
        return self.tf.s if self.tf else 1.0

    @contextmanager
    def at(self, ox, oy, sc=1.0, ang=0.0, flip=False, px=0.0, py=0.0):
        old = self.tf
        self.tf = Tf(ox, oy, sc, ang, flip, px, py)
        try:
            yield self
        finally:
            self.tf = old

    @contextmanager
    def raw(self):
        old = self.tf
        self.tf = None
        try:
            yield self
        finally:
            self.tf = old

    # pixels ------------------------------------------------------------------------------------------------
    def put(self, x, y, v=1):
        x, y = rnd(x), rnd(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = v
            self.al[y, x] = True

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return int(self.a[y, x])
        return 0

    def _line(self, p0, p1, v=1, dash=None, w=1):
        x0, y0, x1, y1 = rnd(p0[0]), rnd(p0[1]), rnd(p1[0]), rnd(p1[1])
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        n = 0
        while True:
            if dash is None or (n % (dash[0] + dash[1])) < dash[0]:
                self.put(x0, y0, v)
                if w >= 2:
                    if dx >= dy:
                        self.put(x0, y0 + 1, v)
                    else:
                        self.put(x0 + 1, y0, v)
            n += 1
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def line(self, p0, p1, v=1, dash=None, w=1):
        self._line(self._pt(p0), self._pt(p1), v, dash, w)

    def pline(self, pts, v=1, dash=None, w=1, closed=False):
        P = [self._pt(p) for p in pts]
        for i in range(len(P) - 1):
            self._line(P[i], P[i + 1], v, dash, w)
        if closed:
            self._line(P[-1], P[0], v, dash, w)

    def dot(self, x, y, v=1, r=0):
        """a pixel (r = 0) or a filled square (2r + 1) at a transformed point"""
        px, py = self._pt((x, y))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                self.put(px + dx, py + dy, v)

    def _mask(self, P):
        im = Image.new('1', (self.w, self.h), 0)
        ImageDraw.Draw(im).polygon([(p[0], p[1]) for p in P], fill=1)
        return np.array(im, bool)

    def _apply(self, mask, tone):
        if isinstance(tone, int):
            arr = np.full(mask.shape, bool(tone))
        else:
            arr = tone.fn(self.xx, self.yy, self)
        self.a[mask] = arr[mask]
        self.al[mask] = True

    def poly(self, pts, tone=None, line=1, closed=True, dash=None, w=1, smooth=0):
        if smooth:
            pts = catmull(pts, closed=True, n=smooth)
        P = [self._pt(p) for p in pts]
        if tone is not None:
            self._apply(self._mask(P), tone)
        if line is not None:
            for i in range(len(P) - 1):
                self._line(P[i], P[i + 1], line, dash, w)
            if closed:
                self._line(P[-1], P[0], line, dash, w)

    def ell(self, cx, cy, rx, ry, tone=None, line=1, rot=0.0, n=0, dash=None):
        n = n or max(12, int(max(rx, ry) * self.sc() * 3))
        pts = []
        c, s = math.cos(rot), math.sin(rot)
        for k in range(n):
            t = 2 * math.pi * k / n
            x, y = rx * math.cos(t), ry * math.sin(t)
            pts.append((cx + c * x - s * y, cy + s * x + c * y))
        self.poly(pts, tone, line, dash=dash)

    def rect(self, x0, y0, x1, y1, tone=None, line=1):
        """raw rectangle, x1 / y1 exclusive"""
        with self.raw():
            if tone is not None:
                m = np.zeros((self.h, self.w), bool)
                m[max(y0, 0):y1, max(x0, 0):x1] = True
                self._apply(m, tone)
            if line is not None:
                for x in range(x0, x1):
                    self.put(x, y0, line)
                    self.put(x, y1 - 1, line)
                for y in range(y0, y1):
                    self.put(x0, y, line)
                    self.put(x1 - 1, y, line)

    def clear(self, x0, y0, x1, y1):
        self.a[max(y0, 0):y1, max(x0, 0):x1] = 0
        self.al[max(y0, 0):y1, max(x0, 0):x1] = True

    # text --------------------------------------------------------------------------------------------------
    def text(self, x, y, s, face='b7', v=1):
        """raw text, top-left at (x, y); returns the width"""
        self.strings.append(s)
        cx = x
        for ch in s:
            g = glyph(ch, face)
            for r, row in enumerate(g):
                for c, px in enumerate(row):
                    if px == '#':
                        self.put(cx + c, y + r, v)
            cx += adv(ch)
        return text_w(s, face)

    def caption(self, x, y, s, face='r6'):
        with self.raw():
            return self.text(x, y, s, face)

    # boxed label -------------------------------------------------------------------------------------------
    def box(self, name, r, lines, face=None, pitch=8):
        """a 1-px outlined box exactly on r = (x0, y0, x1, y1) (x1, y1 exclusive), white inside, the lines centred.
        r may run past the picture: the box is then cut by the picture's edge (outline kept inside)."""
        x0, y0, x1, y1 = r
        x1c, y1c = min(x1, self.w), min(y1, self.h)
        if isinstance(lines, str):
            lines = [lines]
        lines = [{'Queen': '12ee3'}.get(l, l) for l in lines]
        bw, bh = x1c - x0, y1c - y0
        if face is None:
            face = 'r6' if len(lines) > 1 else ('b7' if bh <= 12 else 'b8')
        with self.raw():
            self.clear(x0, y0, x1c, y1c)
            self.rect(x0, y0, x1c, y1c, None, 1)
            th = text_h(face)
            if len(lines) == 1:
                ty = y0 + (bh - th + 1) // 2
                ys = [ty]
            else:
                total = pitch * (len(lines) - 1) + face_cap(face)
                ty0 = y0 + (bh - total) // 2
                ys = [ty0 + pitch * i for i in range(len(lines))]
            ink = [10 ** 6, 10 ** 6, -1, -1]
            for ln, ty in zip(lines, ys):
                tw = text_w(ln, face)
                tx = x0 + (bw - tw) // 2
                self.text(tx, ty, ln, face)
                ink[0] = min(ink[0], tx)
                ink[2] = max(ink[2], tx + tw)
            self.boxes[name] = dict(rect=(x0, y0, x1c, y1c), lines=lines, face=face, inkx=(ink[0], ink[2]), want=r)
        return self.boxes[name]

    def leader(self, name, start, via, tip, part, halo=True):
        """a 1-px leader from just outside box `name` (start = the first pixel, adjacent to the box edge) along the
        points `via` to `tip`, ended by a 2 x 2 dot (tip = its upper left pixel); `part` is the rectangle of the named part
        the tip must lie in.  Raw (picture) coordinates."""
        pts = [start] + list(via) + [tip]
        with self.raw():
            pix = set()
            for i in range(len(pts) - 1):
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                dx, dy = abs(x1 - x0), abs(y1 - y0)
                sx = 1 if x0 < x1 else -1
                sy = 1 if y0 < y1 else -1
                err = dx - dy
                while True:
                    pix.add((x0, y0))
                    if x0 == x1 and y0 == y1:
                        break
                    e2 = 2 * err
                    if e2 > -dy:
                        err -= dy
                        x0 += sx
                    if e2 < dx:
                        err += dx
                        y0 += sy
            tx, ty = tip
            if halo:
                for yy in range(ty - 2, ty + 4):
                    for xx in range(tx - 2, tx + 4):
                        if (xx, yy) not in pix:
                            self.put(xx, yy, 0)
            for (x, y) in pix:
                self.put(x, y, 1)
            for yy in range(ty, ty + 2):
                for xx in range(tx, tx + 2):
                    self.put(xx, yy, 1)
                    pix.add((xx, yy))
        self.leaders.append(dict(box=name, start=start, tip=tip, part=part, pix=pix))

    def bbox(self):
        ys, xs = np.nonzero(self.al)
        if len(xs) == 0:
            return None
        return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1

    def ascii(self, x0=0, y0=0, x1=None, y1=None):
        x1 = x1 or self.w
        y1 = y1 or self.h
        return '\n'.join(''.join('#' if self.a[y, x] else '.' for x in range(x0, x1)) for y in range(y0, y1))


# ----------------------------------------------------------------------------------------------------------- io
def write_pix(ident, cv, desc):
    path = os.path.join(HERE, '%d.pix' % ident)
    with open(path, 'w', newline='\n') as f:
        f.write('# %d: %s\n# %d x %d\n' % (ident, desc, cv.w, cv.h))
        for row in cv.a:
            f.write(''.join('f' if v else '0' for v in row) + '\n')
    return path


def read_pix(ident):
    rows = []
    with open(os.path.join(HERE, '%d.pix' % ident)) as f:
        for ln in f:
            ln = ln.rstrip('\n')
            if ln.startswith('#') or not ln:
                continue
            rows.append([1 if c == 'f' else 0 for c in ln])
    return np.array(rows, np.uint8)
