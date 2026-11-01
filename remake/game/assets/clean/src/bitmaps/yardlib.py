"""yardlib: drawing helpers for the yard bitmaps (docs/clean_pack/yard_bitmaps.md).

World = the yard window's two big pictures drawn as ONE canvas in yard coordinates, so the seam between 7000 / 7001 and
7003 cannot show.  Canvas pixel column = yard x + OX (OX = 2): 7000 / 7001 are the columns 0..280, 7003 the columns 281..513.
Everything here takes YARD coordinates (x right, y down), rectangles are [x0, x1) x [y0, y1).

Projection used by the scenery (a house seen from above and in front, depth running up and to the right):
G(s, y, z) = (s - y, y - z): s is the ground coordinate that is constant along a lawn line x + y = s, y the row of the ground
point, z a height in pixels.  The lawn lattice is exactly the grid of constant s (every 28) and constant y (every 10).
"""
import numpy as np

OX = 2                      # canvas column = yard x + OX
WORLD_W, WORLD_H = 514, 226
W7000, W7003 = 281, 233
LAWN_Y0, LAWN_Y1 = 65, 225


# ---------------------------------------------------------------------------------------------- the lattice
def lattice(x, y):
    """The engine's lawn: None outside the parallelogram 65 <= y <= 225, 232 - y <= x <= 568 - y; 9 on a lattice line
    (y = 65 + 10 r, or x + y = 232 + 28 k), 8 inside the cells."""
    if y < LAWN_Y0 or y > LAWN_Y1 or x < 232 - y or x > 568 - y:
        return None
    if (y - 65) % 10 == 0 or (x + y - 232) % 28 == 0:
        return 9
    return 8


def house_covers(x, y):
    """True where the house hides the lawn (the colony views mark the same boundary): the lawn pixel is NOT visible there."""
    return y >= LAWN_Y0 and x + y <= (315 if y <= 114 else 287)


def G(s, y, z=0):
    return (s - y, y - z)


# ---------------------------------------------------------------------------------------------- the canvas
class World:
    def __init__(self, fill=13):
        self.a = np.full((WORLD_H, WORLD_W), fill, dtype=np.int16)
        self.clip = None          # optional boolean array [y, canvas column]: where drawing is allowed

    # ---- pixels
    def put(self, x, y, c):
        if c is None:
            return
        X = int(x) + OX
        y = int(y)
        if 0 <= X < WORLD_W and 0 <= y < WORLD_H:
            if self.clip is None or self.clip[y, X]:
                self.a[y, X] = c

    def get(self, x, y):
        return int(self.a[y, x + OX])

    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)):
                self.put(x, y, c)

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.put(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def poly_outline(self, pts, c):
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            self.line(a[0], a[1], b[0], b[1], c)

    # ---- polygons (pixel centres, even-odd)
    @staticmethod
    def poly_pixels(pts):
        out = []
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(int(np.floor(min(ys))), int(np.ceil(max(ys))) + 1):
            if y < -1 or y >= WORLD_H + 1:
                continue
            yc = y + 0.5
            xs = []
            for i in range(n):
                (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
                if (ya <= yc < yb) or (yb <= yc < ya):
                    xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(np.ceil(xs[k] - 0.5)), int(np.ceil(xs[k + 1] - 0.5))):
                    out.append((x, y))
        return out

    def fill_poly(self, pts, c, pattern=None):
        """Fill; pattern(x, y) -> colour or None replaces c per pixel.  Returns the pixel list."""
        px = self.poly_pixels(pts)
        for (x, y) in px:
            col = c
            if pattern is not None:
                p = pattern(x, y)
                if p is not None:
                    col = p
            self.put(x, y, col)
        return px

    def ellipse(self, cx, cy, rx, ry, c, pattern=None):
        out = []
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                    col = c
                    if pattern is not None:
                        p = pattern(x, y)
                        if p is not None:
                            col = p
                    self.put(x, y, col)
                    out.append((x, y))
        return out

    def outline_pixels(self, pixels, c):
        """Set the pixels of the set that touch (4-neighbour) a pixel outside the set to c (an inner outline)."""
        s = set(pixels)
        for (x, y) in pixels:
            if (x - 1, y) not in s or (x + 1, y) not in s or (x, y - 1) not in s or (x, y + 1) not in s:
                self.put(x, y, c)

    # ---- boxes
    def gbox(self, s0, s1, y0, y1, z0, z1, top, front, right, outline=15):
        """A box on the ground: s in [s0, s1], y in [y0, y1], z in [z0, z1].  front = the face towards the viewer (plane
        y = y1), right = the face towards the lawn (plane s = s1), top.  Silhouette outline (inner) in `outline`."""
        px = []
        fr = [G(s0, y1, z0), G(s1, y1, z0), G(s1, y1, z1), G(s0, y1, z1)]
        rt = [G(s1, y1, z0), G(s1, y0, z0), G(s1, y0, z1), G(s1, y1, z1)]
        tp = [G(s0, y1, z1), G(s1, y1, z1), G(s1, y0, z1), G(s0, y0, z1)]
        px += self.fill_poly(fr, front)
        px += self.fill_poly(rt, right)
        px += self.fill_poly(tp, top)
        if outline is not None:
            self.outline_pixels(px, outline)
        return px

    def obox(self, x0, y0, w, h, d, top, front, right, outline=15):
        """An oblique box given by its front rectangle (x0, y0, w, h) and a depth d (shifted d right and d up)."""
        px = []
        px += self.fill_poly([(x0, y0 + h), (x0 + w, y0 + h), (x0 + w, y0), (x0, y0)], front)
        px += self.fill_poly([(x0 + w, y0 + h), (x0 + w + d, y0 + h - d), (x0 + w + d, y0 - d), (x0 + w, y0)], right)
        px += self.fill_poly([(x0, y0), (x0 + w, y0), (x0 + w + d, y0 - d), (x0 + d, y0 - d)], top)
        if outline is not None:
            self.outline_pixels(px, outline)
        return px

    # ---- views
    def pic(self, x0, x1):
        """Canvas columns for yard x in [x0, x1)."""
        return self.a[:, x0 + OX:x1 + OX].copy()


def polygon_mask(pts):
    """Boolean array [y, canvas column] of the polygon (yard coordinates)."""
    m = np.zeros((WORLD_H, WORLD_W), dtype=bool)
    for (x, y) in World.poly_pixels(pts):
        X = x + OX
        if 0 <= X < WORLD_W and 0 <= y < WORLD_H:
            m[y, X] = True
    return m
