"""Nest grid helpers shared by surface and nest code: digging, dirt edges, exit fields, nest ant lists.

Black nest: dirt 0x2180, exit field 0x4180, cells 0x8180, ants b_* (count G:0da8).
Red nest:   dirt 0x3180, exit field 0x5180, cells 0x9180, ants r_* (count G:0eaa).
"""
from .state import SIM, G, T

BLACK = dict(dirt=0x2180, exitf=0x4180, cells=0x8180, x=0xb50d, y=0xb702, state=0xb8f7, type=0xbaec,
             e=0xbce1, count=0xda8, cap=0x224, sum_col=0x1068, sum_depth=0x1082, cen_col=0x10b2, cen_depth=0x10c0)
RED = dict(dirt=0x3180, exitf=0x5180, cells=0x9180, x=0xbed6, y=0xc0cb, state=0xc2c0, type=0xc4b5,
           e=0xc6aa, count=0xeaa, cap=0x232, sum_col=0x108e, sum_depth=0x10a2, cen_col=0x200, cen_depth=0x20e)


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def is_diggable(t):
    """f_0ca6e."""
    return 0x20 <= t <= 0x2e


def is_dirt_for_edge(t):
    """f_15a13."""
    return not (t < 0x20 or (0x2f < t < 0x4f))


def reclassify_dirt(st, n, col, depth):
    """f_158d1 (black) / f_15a3a (red): recompute a dirt cell's edge tile from its dirt neighbours."""
    if not (0 <= col < 0x40 and depth < 0x40):
        return
    base = n['dirt']
    if depth == 0:
        if st.grid(base, col, 0) < 0x30:
            st.set_grid(base, col, 0, 0x18)
        return
    t = st.grid(base, col, depth)
    if not (t > 0x1f and (t < 0x30 or t > 0x4e)):
        return
    alt = 0x2f if t >= 0x4e else 0
    m = 0
    if depth < 2 or is_dirt_for_edge(st.grid(base, col, depth - 1)):
        m = 1
    if col > 0x3e or is_dirt_for_edge(st.grid(base, col + 1, depth)):
        m |= 2
    if depth > 0x3e or is_dirt_for_edge(st.grid(base, col, depth + 1)):
        m |= 4
    if col < 1 or is_dirt_for_edge(st.grid(base, col - 1, depth)):
        m |= 8
    if m == 0:
        if alt:
            st.set_grid(base, col, depth, 0x4e)
            return
        st.set_grid(base, col, depth, st.rand8())
    else:
        st.set_grid(base, col, depth, m + alt + 0x1f)


def update_exit_field(st, n, col, depth):
    """f_15b7c (black) / f_15c51 (red)."""
    if depth < 2:
        st.set_grid(n['exitf'], col, depth, 0xff if st.grid(n['dirt'], col, depth) == 0x18 else 0xfe)
        return
    best = 0
    for d in range(8):
        c, r = col + st.s8(T, d), depth + st.s8(T, 8 + d)
        if 0 <= c < 0x40 and 0 <= r < 0x40:
            v = st.grid(n['exitf'], c, r)
            if v > best:
                best = v
    st.set_grid(n['exitf'], col, depth, best - 1 if best else 0)


def _dig_bookkeeping(st, n, col, depth):
    st.set32(G, n['sum_col'], (st.u32(G, n['sum_col']) + col) & 0xffffffff)
    st.set32(G, n['sum_depth'], (st.u32(G, n['sum_depth']) + depth) & 0xffffffff)
    st.inc16(G, n['cap'])
    cap = s16(st.u16(G, n['cap']))
    if cap > 0:
        def sdiv(a, b):
            a = a - (1 << 32) if a & 0x80000000 else a
            q = abs(a) // abs(b)
            return q if (a >= 0) == (b >= 0) else -q
        st.set16(G, n['cen_col'], sdiv(st.u32(G, n['sum_col']), cap))
        st.set16(G, n['cen_depth'], sdiv(st.u32(G, n['sum_depth']), cap))


def dig_at(st, n, col, depth):
    """f_153f9 (black) / f_15527 (red): dig a cell if diggable (no structural checks); used under entrances.
    Deep black digging can break into the red nest."""
    if is_diggable(st.grid(n['dirt'], col, depth)):
        st.set_grid(n['dirt'], col, depth, st.rand8())
        _dig_bookkeeping(st, n, col, depth)
        if n['dirt'] == BLACK['dirt'] and depth > 0x35 and st.rand(0x40) == 0:   # (callers pass copies)
            st.set_grid(BLACK['dirt'], col, depth, 0x14)
            dig_at(st, RED, col, depth)
            st.set_grid(RED['dirt'], col, depth, 0x14)
    reclassify_dirt(st, n, col, depth - 1)
    reclassify_dirt(st, n, col + 1, depth)
    reclassify_dirt(st, n, col, depth + 1)
    reclassify_dirt(st, n, col - 1, depth)
    update_exit_field(st, n, col, depth)


def add_nest_ant(st, n, col, depth, t, state, e):
    """f_0f1e4 (black) / f_0f261 (red)."""
    i = s16(st.u16(G, n['count']))
    if i >= 500:
        return
    st.set8(SIM, n['x'] + i, col)
    st.set8(SIM, n['y'] + i, depth)
    st.set8(SIM, n['state'] + i, state)
    st.set8(SIM, n['type'] + i, t)
    st.set8(SIM, n['e'] + i, e)
    st.set_grid(n['cells'], col, depth, t)
    st.inc16(G, n['count'])


def compact(st, type_base, fields, count_off):
    """f_0ec12 (surface) / f_0ec91 (black nest) / f_0ed10 (red nest): squeeze out empty slots."""
    shift = 0
    n = s16(st.u16(G, count_off))
    for i in range(n):
        t = st.u8(SIM, type_base + i)
        if t == 0:
            shift -= 1
        elif shift:
            j = i + shift
            st.set8(SIM, type_base + j, t)
            for f in fields:
                st.set8(SIM, f + j, st.u8(SIM, f + i))
    st.set16(G, count_off, n + shift)


SURFACE_FIELDS = (0xa180, 0xa569, 0xa952, 0xb124)


def compact_surface(st):
    compact(st, 0xad3b, SURFACE_FIELDS, 0xd6a)


def compact_nest(st, n):
    compact(st, n['type'], (n['x'], n['y'], n['state'], n['e']), n['count'])
