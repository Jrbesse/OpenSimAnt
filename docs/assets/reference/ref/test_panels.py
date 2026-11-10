"""Verify the Behavior / Caste Control triangles against the original: the geometry (f_07980), weights to
marker (f_087c7) and click to weights (f_086a1), over many weights and points.

python test_panels.py
"""
import random
import sys

from verify import Verifier
from simant_ref import panels
from simant_ref.state import G
import test_sim

# the triangles' item rectangles (windows 18 / 19, item 0x0D), as the layout gives them
PANELS = [('behaviour', (136, 344, 247, 440), 0x49e, 0x3816, 0x358),
          ('caste', (392, 344, 501, 440), 0x482, 0x3822, 0x22e)]


def far(v, off):
    return (off, G + v.e.base)


def main():
    v = Verifier()
    test_sim.prepare(v)
    ok = True
    rng = random.Random(7)
    for name, rect, values, tri, point in PANELS:
        def setup(set16, args, rect=rect, tri=tri):
            l, t, r, b = rect
            w, h = r - l, b - t
            for off, val in ((0x3814, w), (0x3812, w >> 1), (0x3810, w >> 1), (0x380e, h)):
                set16(G, off, val)
            for i, val in enumerate((l + (w >> 1), t, l, b, r, b)):
                set16(G, tri + 2 * i, val)
        weights = [(0xffff, 0, 0), (0, 0xffff, 0), (0, 0, 0xffff), (0x5555, 0x5555, 0x5555), (0xfffe, 1, 0)]
        for _ in range(40):
            a, b = sorted(rng.randrange(0x10000) for _ in range(2))
            weights.append((a, b - a, 0xffff - b))

        def pre_w(set16, args, ws=weights, setup=setup, values=values):
            setup(set16, args)
            w = ws[pre_w.i % len(ws)]
            pre_w.i += 1
            for k in range(3):
                set16(G, values + 2 * k, w[k])
        pre_w.i = 0
        ok &= v.check(0x087c7, lambda st, *a, values=values, tri=tri, point=point: panels.to_point(st, values, tri, point),
                      args_fn=lambda st, i, values=values, tri=tri, point=point: far(v, values) + far(v, tri) + far(v, point),
                      repeat=len(weights), label=f'{name}: weights to marker', pre=pre_w, ignore=test_sim.SCREEN)
        l, t, r, b = rect
        pts = [(x, y) for x in range(l - 6, r + 7, 7) for y in range(t - 4, b + 5, 6)]

        def pre_p(set16, args, pts=pts, setup=setup, point=point):
            setup(set16, args)
            x, y = pts[pre_p.i % len(pts)]
            pre_p.i += 1
            set16(G, point, x & 0xffff)
            set16(G, point + 2, y & 0xffff)
        pre_p.i = 0
        ok &= v.check(0x086a1, lambda st, *a, values=values, tri=tri, point=point: panels.to_values(st, values, tri, point),
                      args_fn=lambda st, i, values=values, tri=tri, point=point: far(v, values) + far(v, tri) + far(v, point),
                      repeat=len(pts), label=f'{name}: click to weights', pre=pre_p, ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
