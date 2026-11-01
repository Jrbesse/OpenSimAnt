"""screens_lib: shared helpers of the screens / scenes batch (screens_bitmaps.md).
A PIL 'L' canvas (Cv) holds palette indices directly (no anti-aliasing), plus an ant drawing program,
textures, dithering and lettering (uilib's pixel faces).  Coordinates: pixels from the top-left."""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import uilib  # noqa: E402  (the interface batch's pixel faces; reused as the spec allows)
from uilib import Img, SMALL, LABEL, LABEL_TALL, contrast  # noqa: E402,F401
WM = uilib.Face('wordmark', bold=False, tall=True)      # the wordmark's face: regular, 8-px capitals

HEX = '0123456789abcdef'

# The interface batch's bold smears every stroke one pixel to the right, which fills the two gaps of an 'm' into a block;
# here the bold 'm' is its own 8-pixel glyph (three 2-px stems, a joined top).
_BOLD_M = ['.######.', '##.##.##', '##.##.##', '##.##.##', '##.##.##']
_orig_glyph = uilib.Face.glyph


def _glyph(self, ch):
    if self.bold and ch == 'm':
        if ch not in self._c:
            rows = ['.' * 8] * 2 + _BOLD_M + ['.' * 8] * 2
            if self.tall:
                rows = rows[:5] + [rows[4]] + rows[5:]
            self._c[ch] = np.array([[c == '#' for c in r] for r in rows], dtype=bool)
        return self._c[ch]
    return _orig_glyph(self, ch)


uilib.Face.glyph = _glyph

# every string lettered into a picture: (picture id, string); asserted against the allowed list
LETTERED = []

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def bayer(x, y):
    return BAYER[y & 3, x & 3]


class Cv:
    """Canvas of palette indices on a PIL 'L' image."""

    def __init__(self, w, h, fill=0):
        self.w, self.h = w, h
        self.im = Image.new('L', (w, h), fill)
        self.d = ImageDraw.Draw(self.im)

    # ---- numpy bridge
    def arr(self):
        return np.array(self.im).astype(np.int16)

    def set_arr(self, a):
        self.im = Image.fromarray(a.astype(np.uint8), 'L')
        self.d = ImageDraw.Draw(self.im)

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.im.putpixel((int(x), int(y)), int(c))

    def get(self, x, y):
        return self.im.getpixel((int(x), int(y)))

    # ---- shapes (second corner INCLUSIVE for PIL; helpers here take exclusive like the spec)
    def rect(self, x0, y0, x1, y1, c):
        if x1 > x0 and y1 > y0:
            self.d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=c)

    def frame(self, x0, y0, x1, y1, c, t=1):
        for i in range(t):
            self.d.rectangle([x0 + i, y0 + i, x1 - 1 - i, y1 - 1 - i], outline=c)

    def line(self, p, q, c, w=1):
        self.d.line([tuple(p), tuple(q)], fill=c, width=w)

    def poly(self, pts, fill=None, outline=None):
        pts = [(float(x), float(y)) for x, y in pts]
        self.d.polygon(pts, fill=fill, outline=outline)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None):
        self.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill, outline=outline)

    def path(self, pts, c, w=1):
        for a, b in zip(pts, pts[1:]):
            self.line(a, b, c, w)
        if w > 2:
            for a in pts[1:-1]:
                r = (w - 1) / 2.0
                self.d.ellipse([a[0] - r, a[1] - r, a[0] + r, a[1] + r], fill=c)

    def blit(self, other, x, y):
        self.im.paste(other.im, (int(x), int(y)))

    def crop(self, x0, y0, x1, y1):
        o = Cv(x1 - x0, y1 - y0)
        o.im = self.im.crop((x0, y0, x1, y1))
        o.d = ImageDraw.Draw(o.im)
        return o

    def copy(self):
        o = Cv(self.w, self.h)
        o.im = self.im.copy()
        o.d = ImageDraw.Draw(o.im)
        return o

    def to_img(self):
        o = Img(self.w, self.h)
        o.a = self.arr()
        return o

    # ---- lettering through uilib (returns the ink mask bounds)
    def text(self, pic, x, y, s, face=LABEL, color=15, scale=1, outline=None, shadow=None, centre=False):
        LETTERED.append((pic, s))
        img = self.to_img()
        if centre:
            x = x - (face.width(s) * scale) // 2
        uilib.text(img, x, y, s, face, color, scale, shadow=shadow, outline=outline)
        self.set_arr(img.a)
        return x, face.width(s) * scale


def mask_text(s, face, scale):
    return face.render(s, scale)


# ---- dither / texture -----------------------------------------------------------------------------------------
def dither_rect(cv, x0, y0, x1, y1, c0, c1, p):
    """Ordered dither: c1 with probability p (0..1) over c0 (c0 not painted, only c1 pixels)."""
    for y in range(max(0, y0), min(cv.h, y1)):
        for x in range(max(0, x0), min(cv.w, x1)):
            if bayer(x, y) < p:
                cv.px(x, y, c1)


def speckle(cv, rect, colours, n, seed, size=1):
    r = random.Random(seed)
    x0, y0, x1, y1 = rect
    for _ in range(n):
        x = r.randrange(x0, x1)
        y = r.randrange(y0, y1)
        c = r.choice(colours)
        cv.rect(x, y, x + size, y + size, c)


def pebble(cv, cx, cy, rx, ry, main=13, light=12, dark=14, out=15):
    """A lit pebble: outline, body, shade at the bottom-right, highlight at the top-left."""
    cv.ell(cx, cy, rx, ry, fill=dark, outline=out)
    cv.ell(cx - 0.7, cy - 0.7, max(1, rx - 1.6), max(1, ry - 1.6), fill=main)
    if rx >= 3:
        cv.ell(cx - rx * 0.35, cy - ry * 0.35, max(0.8, rx * 0.35), max(0.8, ry * 0.3), fill=light)


# ---- geometry ------------------------------------------------------------------------------------------------
def ell_pts(cx, cy, a, b, ang, n=40):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        u, v = a * math.cos(t), b * math.sin(t)
        pts.append((cx + u * ca - v * sa, cy + u * sa + v * ca))
    return pts


def lp(x, y, ang, u, v):
    ca, sa = math.cos(ang), math.sin(ang)
    return (x + u * ca - v * sa, y + u * sa + v * ca)


def bezier(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t ** 2
        d = t ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def tapered(cv, pts, w0, w1, c, out=None):
    """A thick curve whose width goes from w0 to w1 (discs along the polyline)."""
    n = len(pts)
    if out is not None:
        for i, (x, y) in enumerate(pts):
            w = w0 + (w1 - w0) * i / max(1, n - 1)
            r = w / 2.0 + 1
            cv.d.ellipse([x - r, y - r, x + r, y + r], fill=out)
    for i, (x, y) in enumerate(pts):
        w = w0 + (w1 - w0) * i / max(1, n - 1)
        r = w / 2.0
        cv.d.ellipse([x - r, y - r, x + r, y + r], fill=c)


# ---- the ant drawing program -----------------------------------------------------------------------------------
# local frame: u forward (head), v to the side; the ant faces `ang` (0 = right, 90 deg = down on screen).
LEGS = [  # attach u, knee (du, dv), tip (du, dv)  for the right-hand legs; mirrored with v -> -v
    (0.10, (0.12, 0.20), (0.22, 0.40)),
    (0.00, (0.00, 0.24), (0.04, 0.44)),
    (-0.08, (-0.14, 0.22), (-0.26, 0.40)),
]


def ant(cv, x, y, ang, L, body=14, shade=13, hi=None, out=15, legcol=None, legw=1, antw=1, mand=None,
        eyes=False, head_shift=0.0, antennae=True, legs=True, belly=1.0, mand_col=None, legfill=None):
    """Draws an ant of length L centred at (x, y) facing ang.  mand: None or openness 0..1."""
    legcol = out if legcol is None else legcol
    big = L >= 40
    if legs:
        for s in (1, -1):
            for ua, (ku, kv), (tu, tv) in LEGS:
                a = lp(x, y, ang, ua * L, s * 0.05 * L)
                k = lp(x, y, ang, (ua + ku) * L, s * kv * L)
                t = lp(x, y, ang, (ua + tu) * L, s * tv * L)
                if legfill is not None:
                    cv.path([a, k, t], legcol, legw + 2)
                    cv.path([a, k, t], legfill, legw)
                else:
                    cv.path([a, k, t], legcol, legw)
    hu = 0.27 * L + head_shift * L
    if antennae:
        for s in (1, -1):
            b = lp(x, y, ang, hu + 0.08 * L, s * 0.05 * L)
            e = lp(x, y, ang, hu + 0.20 * L, s * 0.17 * L)
            t = lp(x, y, ang, hu + 0.30 * L, s * 0.10 * L)
            cv.path([b, e, t], out, antw)
    if mand is not None:
        mc = out if mand_col is None else mand_col
        for s in (1, -1):
            b = lp(x, y, ang, hu + 0.10 * L, s * 0.05 * L)
            m = lp(x, y, ang, hu + 0.15 * L, s * (0.065 + 0.04 * mand) * L)
            t = lp(x, y, ang, hu + 0.21 * L, s * (0.015 + 0.075 * mand) * L)
            w = max(1, int(L / 45))
            cv.path([b, m, t], out, w + 2 if big else w)
            if big:
                cv.path([b, m, t], body, w)

    def part(cx_u, a_u, b_v, shaded=True):
        cx, cy = lp(x, y, ang, cx_u, 0)
        pts = ell_pts(cx, cy, a_u, b_v, ang)
        if shaded and L >= 16:
            cv.poly(pts, fill=shade, outline=out)
            k = max(0.8, L * 0.012)
            pts2 = ell_pts(cx - k, cy - k, max(1, a_u - max(1.6, L * 0.014)), max(1, b_v - max(1.6, L * 0.014)), ang)
            cv.poly(pts2, fill=body)
            if hi is not None and L >= 36:
                hx, hy = lp(cx - k, cy - k, ang, -a_u * 0.15, -b_v * 0.35)
                cv.ell(hx, hy, max(1, a_u * 0.35), max(1, b_v * 0.2), fill=hi)
        else:
            cv.poly(pts, fill=body, outline=out)
        return cx, cy

    # petiole (waist) between thorax and abdomen
    pa = lp(x, y, ang, -0.13 * L, 0)
    cv.ell(pa[0], pa[1], max(1, 0.03 * L), max(1, 0.03 * L), fill=body, outline=out)
    if L >= 60:
        nk = lp(x, y, ang, (0.13 + 0.27) / 2 * L, 0)
        cv.ell(nk[0], nk[1], 0.05 * L, 0.05 * L, fill=body, outline=out)
    part(-0.31 * L, 0.22 * L * belly ** 0.0, 0.15 * L * belly)
    part(0.0, 0.13 * L, 0.075 * L)
    hx, hy = part(hu, 0.115 * L, 0.10 * L)
    if eyes or big:
        for s in (1, -1):
            e = lp(x, y, ang, hu + 0.015 * L, s * 0.062 * L)
            r = max(0.8, L * 0.022)
            cv.ell(e[0], e[1], r, r, fill=out)
            if L >= 60:
                cv.ell(e[0] - r * 0.3, e[1] - r * 0.3, max(0.6, r * 0.35), max(0.6, r * 0.35), fill=0)
    return (hx, hy)
