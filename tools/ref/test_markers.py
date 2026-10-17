"""Verify the event-marker recorders (f_0678a, f_06802, f_0687a, f_068f2, with the on-screen test f_06725)
against the original, with the map window placed over the points.

python test_markers.py
"""
import sys

from verify import Verifier
from simant_ref import markers
from simant_ref.state import G
import test_sim

RECORDERS = {'brood': 0x0678a, 'fight': 0x06802, 'queen': 0x0687a, 'rest': 0x068f2}
# (a, b) around a window at (10, 5), 40 x 20: inside, on every edge, outside, and repeats
POINTS = [(20, 15), (10, 8), (9, 8), (49, 8), (50, 8), (20, 7), (20, 24), (20, 25), (20, 8), (30, 20),
          (20, 15), (-1, 10), (10, 8)]


def setup(view, shown, gate=0, latch=None, origin=(10, 5), size=(40, 20)):
    def pre(set16, args):
        set16(G, 0x32e, shown)
        set16(G, 0x508, origin[0] & 0xffff)
        set16(G, 0x50a, origin[1] & 0xffff)
        set16(G, 0x10e0, size[0])
        set16(G, 0x10de, size[1])
        for kind, (_, g, latched, rec) in markers.KINDS.items():
            set16(G, g, gate)
            for off, v in zip(latched, latch or (0xffff, 0xffff, 0xffff)):
                set16(G, off, v & 0xffff)
    return pre


def port(kind):
    def run(st, a, b, view):
        st.player = test_sim.Player()
        markers.record(st, kind, a, b, view)
    return run


def main():
    v = Verifier()
    test_sim.prepare(v)
    ok = True
    for kind, lin in RECORDERS.items():
        for label, view, pre in [
                ('surface, shown', 1, setup(1, 1)),
                ('black nest, shown', 2, setup(2, 2)),
                ('red nest, shown', 3, setup(3, 3)),
                ('surface, another view shown', 1, setup(1, 2)),
                ('gate busy', 1, setup(1, 1, gate=1)),
                ('latched at (20, 15)', 1, setup(1, 1, latch=(20, 15, 1))),
                ('latched at (20, 15) in another view', 2, setup(2, 2, latch=(20, 15, 1))),
                ('window at a negative origin', 1, setup(1, 1, origin=(-5, -2), size=(30, 12)))]:
            ok &= v.check(lin, port(kind), args_fn=lambda st, i, view=view: (POINTS[i][0] & 0xffff, POINTS[i][1],
                                                                                view),
                          repeat=len(POINTS), label=f'{kind}: {label}', pre=pre, pre_once=True,
                          ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
