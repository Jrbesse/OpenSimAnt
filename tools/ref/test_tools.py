"""Verify the add-ants routines f_6be50 (black) / f_6bf06 (red) and the map tools (f_770f6: rocks, dig, ants,
food, pheromone, insecticide) against the original.

python test_tools.py [name-substring ...]
"""
import sys

from verify import Verifier
from simant_ref import newgame, nestgrid, tools
from simant_ref.state import G, T
import test_sim

ALT = 8
# UI: the info window (thunk 0x2f8fc), the status line (f_15e2c)
STUBS = test_sim.STUBS + (0x2f8fc, 0x15e2c)
V = None

# click points per view, the previous point (G:09FC, G:09FE) set a few cells away
SURFACE_PTS = [(40, 20), (100, 30), (64, 32), (5, 60), (127, 0), (20, 45), (90, 10), (0, 33)]
NEST_PTS = [(20, 1), (30, 10), (10, 5), (40, 2), (5, 20), (63, 63), (32, 0), (12, 30)]
OPTS = {1: (0x7b7,), 2: (0x7b8,), 3: (0x7b9,), 4: (0x7ba,), 5: (0x7bb,), 6: (0x7bc,)}


def port_add(red):
    def run(st, n):
        st.player = test_sim.Player()
        newgame.add_surface_ants(st, n, red)
    return run


def port_tool(st, a, b):
    st.player = test_sim.Player()
    tools.apply_tool(st, a, b)


def tool_setup(view, tool, opt, alt, prev):
    def pre(set16, args):
        set16(G, 0x32e, view)
        set16(G, 0x104c, tool)
        a, b = args
        set16(G, 0x9fc, (a + prev[0]) & 0xffff)
        set16(G, 0x9fe, (b + prev[1]) & 0xffff)
        if tool in OPTS:
            set16.byte(T, OPTS[tool][0], opt)
        V.e.uc.mem_write(0x417, bytes([ALT if alt else 0]))
    return pre


def tool_cases():
    cases = []
    for view in (1, 2, 3):
        pts = SURFACE_PTS if view == 1 else NEST_PTS
        for tool in range(7):
            opts = (0, 1, 2, 3, 4) if tool == 5 else (0, 1)
            for opt in opts:
                for alt in (False, True):
                    for prev in ((0, 0), (5, -3), (-2, 7)):
                        label = f'tool {tool} view {view} opt {opt}{" alt" if alt else ""} prev {prev}'
                        cases.append((label, pts, tool_setup(view, tool, opt, alt, prev)))
    return cases


# targeted clicks: positions taken from the state, so the tools hit ants, crumbs, pits and the spider
def _surface_ants(st, i):
    n = st.u16(G, 0xd6a)
    if i >= n:
        return None
    k = (i * 7) % n
    return st.u8(0x3e1d, 0xa180 + k), st.u8(0x3e1d, 0xa569 + k)


def _nest_ants(red):
    n = (nestgrid.RED if red else nestgrid.BLACK)

    def at(st, i):
        c = st.u16(G, n['count'])
        if i >= c:
            return None
        k = (i * 5) % c
        x, y = st.u8(0x3e1d, n['x'] + k), st.u8(0x3e1d, n['y'] + k)
        return (x, y) if y else None
    return at


def _lions(st, i):
    if i >= st.u16(T, 0xc4a):
        return None
    return st.u8(G, 0xa92 + i), st.u8(G, 0xaa8 + i)


def _spider(st, i):
    return (st.u16(G, 0xf12) >> 4) & 0x7f, (st.u16(G, 0xf34) >> 4) & 0x3f


def _tiles(base, lo, hi, w):
    def at(st, i):
        found = [(a, b) for a in range(w) for b in range(64) if lo <= st.grid(base, a, b) <= hi]
        return found[(i * 13) % len(found)] if found else None
    return at


TARGETED = [
    ('insecticide on surface ants', 1, 6, 1, False, _surface_ants),
    ('insecticide on ant lions', 1, 6, 1, False, _lions),
    ('insecticide on the spider', 1, 6, 1, False, _spider),
    ('insecticide on black nest ants', 2, 6, 1, False, _nest_ants(False)),
    ('insecticide on red nest ants', 3, 6, 1, False, _nest_ants(True)),
    ('insecticide near red nest ants', 3, 6, 0, False, _nest_ants(True)),
    ('fill on black nest ants', 2, 2, 1, False, _nest_ants(False)),
    ('fill on red nest ants', 3, 2, 1, False, _nest_ants(True)),
    ('dig (Alt fill) on black nest ants', 2, 2, 0, True, _nest_ants(False)),
    ('take surface crumbs', 1, 4, 0, True, _tiles(0x180, 0x48, 0x4b, 128)),
    ('grow surface crumbs', 1, 4, 0, False, _tiles(0x180, 0x48, 0x4b, 128)),
    ('take black nest crumbs', 2, 4, 0, True, _tiles(0x2180, 0x10, 0x13, 64)),
    ('take red nest crumbs', 3, 4, 0, True, _tiles(0x3180, 0x10, 0x13, 64)),
    ('take black nest crumbs, food 0', 2, 4, 0, True, _tiles(0x2180, 0x10, 0x13, 64)),
    ('rocks Alt on walls', 1, 1, 0, True, _tiles(0x180, 0x51, 0x67, 128)),
    ('pheromone Alt', 1, 5, 1, True, _surface_ants),
]


def main():
    global V
    filters = sys.argv[1:]
    V = v = Verifier()
    # f_770f6 is in the overlay at 0x74FE0 but in its second code segment (base 0x76F40, entered by a near
    # call from f_76f4a); its jump table is CS-relative, so it must run with CS = 0x76F4
    seg_of = v.e.seg_of
    v.e.seg_of = lambda lin: (0x76f4, lin - 0x76f40) if lin == 0x770f6 else seg_of(lin)
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    ok = True
    if not filters or any(f in 'add ants' for f in filters):
        for lin, red in ((0x6be50, False), (0x6bf06, True)):
            for n in (1, 25, 300, 2000, 0):
                ok &= v.check(lin, port_add(red), args_fn=lambda st, i, n=n: (n,), label=f'{lin:05x}({n})',
                              ignore=test_sim.SCREEN)
    bad = []
    for label, pts, pre in tool_cases():
        if filters and not any(f in label for f in filters):
            continue
        r = v.check(0x770f6, port_tool, args_fn=lambda st, i, pts=pts: pts[i], repeat=len(pts), label=label,
                    pre=pre, ignore=test_sim.SCREEN)
        ok &= r
        if not r:
            bad.append(label)
    for label, view, tool, opt, alt, where in TARGETED:
        if filters and not any(f in label for f in filters):
            continue
        base = tool_setup(view, tool, opt, alt, (0, 0))
        food0 = 'food 0' in label

        def pre(set16, args, base=base, food0=food0):
            base(set16, args)
            if food0:
                set16(G, 0x1050, 0)
        r = v.check(0x770f6, port_tool, args_fn=where, repeat=12, label=label, pre=pre, ignore=test_sim.SCREEN)
        ok &= r
        if not r:
            bad.append(label)
    for label in bad:
        print('  failed:', label)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
