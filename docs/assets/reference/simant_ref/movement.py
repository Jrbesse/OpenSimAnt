"""Surface movement and steering helpers (SIMANT.EXE segments 0ad9, 0be8, 1383, 10f7)."""
from .state import SIM, G, T
from . import pheromones as ph

SURFACE, OCC = 0x0180, 0x6180


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def dx(st, d):
    return st.s8(T, d)


def dy(st, d):
    return st.s8(T, 8 + d)


def walk(st, d, i):
    """T_WALK[d][i] (T:0024)."""
    return st.u8(T, 0x24 + d * 8 + i)


def in_patch(a, b):
    """f_137d7."""
    return 0 <= a <= 0x7f and 0 <= b <= 0x3f


def at_nest_entrance(st, a, b):
    """f_0acfb: standing on a nest entrance tile."""
    if not in_patch(a, b):
        return False
    t = st.grid(SURFACE, a, b)
    if st.u16(G, 0xf24) == 0:
        return t == 0x50
    return 0x80 <= t <= 0x8f


def is_food(st, t):
    """f_0ad63 (TileClass): 1 for food crumbs."""
    if st.u16(G, 0xf24) == 0:
        return 0x48 <= t <= 0x4b
    return 0x18 <= t <= 0x27


def is_yellow(o):
    """f_10faa."""
    return o in (0xfe, 0xff)


def edge_dir(a, b, st):
    """f_148d8: at the patch border, 1 + a random inward heading; 0 elsewhere."""
    if a == 0:
        if b == 0:
            return st.rand(3) + 3
        if b == 0x3f:
            return st.rand(3) + 1
        return st.rand(5) + 1
    if b == 0:
        if a == 0x7f:
            return st.rand(3) + 5
        return st.rand(5) + 3
    if a == 0x7f:
        if b == 0x3f:
            return st.rand(3) + 7
        return st.rand(5) + 5
    if b == 0x3f:
        return st.rand(5) + 7
    return 0


def next_dir(st, a, b, d):
    """f_146b9."""
    e = edge_dir(a, b, st)
    if e:
        return (e - 1) & 7
    return walk(st, d, st.rand8())


def turn_aside(st, d):
    """f_0ab05."""
    return walk(st, d, st.rand8())


def dir_to(a, b, ta, tb):
    """f_0c9a1: 0 if same cell, else 1 + 8-way heading towards the target."""
    ddb = tb - b
    dda = ta - a
    if dda == 0:
        if ddb == 0:
            return 0
        return 1 if ddb < 0 else 5
    if dda > 0:
        if ddb < 0:
            return 2
        return 3 if ddb == 0 else 4
    if ddb > 0:
        return 6
    return 7 if ddb == 0 else 8


def distance_lo(a1, b1, a2, b2):
    """f_0ca03, low word as the callers use it (signed)."""
    return s16((b2 - b1) * (b2 - b1) + (a2 - a1) * (a2 - a1))


def _best_neighbour(st, m, ca, cb, start_best=0, start_dir=0):
    best, bestd = start_best, start_dir
    for d in range(8):
        v = ph.get(st, m, ((ca + dx(st, d)) & 0x3f) * 32 + ((cb + dy(st, d)) & 0x1f))
        if v > best:
            best, bestd = v, d
    return best, bestd


def forage_dir(st, a, b, d, t):
    """f_142c5: climb the colony's food trail; -1 when on a local maximum ("lost")."""
    if a == 0:
        if b == 0:
            return 3
        if b == 0x3f:
            return 1
        return st.rand(3) + 1
    if b == 0:
        if a == 0x7f:
            return 5
        return st.rand(3) + 3
    if a == 0x7f:
        if b == 0x3f:
            return 7
        return st.rand(3) + 5
    if b == 0x3f:
        return (st.rand(3) - 1) & 7
    ca, cb = a >> 1, b >> 1
    m = ph.RED_TRAIL if t & 0x80 else ph.BLACK_TRAIL
    here = ph.get(st, m, ca * 32 + cb)
    start = st.rand8()
    best, bestd = _best_neighbour(st, m, ca, cb, 0, start)
    if best > 0:
        if here > best:
            return -1
        return walk(st, d, bestd)
    return walk(st, d, st.rand8())


def home_dir(st, a, b, d, t):
    """f_1445a: back to the colony's nest (nest-marker gradient, else straight at the entrance)."""
    ca, cb = a >> 1, b >> 1
    red = (t >> 7) & 1
    e = edge_dir(a, b, st)
    if e:
        return (e - 1) & 7
    m = ph.RED_NEST if red else ph.BLACK_NEST
    if ph.get(st, m, ca * 32 + cb):
        best, bestd = _best_neighbour(st, m, ca, cb)
        r = walk(st, d, bestd) if st.rand2() else d
        return walk(st, r, bestd)
    if red:
        dd = dir_to(a, b, s16(st.u16(T, 0x2b0)), s16(st.u16(T, 0x2b2)))
        if dd and st.rand4() != 0:
            return walk(st, d, dd - 1)
    else:
        dd = dir_to(a, b, s16(st.u16(T, 0x2ac)), s16(st.u16(T, 0x2ae)))
        if dd and st.rand4() != 0:
            return walk(st, d, dd - 1)
    return walk(st, d, st.rand8())


def alarm_dir(st, a, b, d):
    """f_145fc: climb the alarm gradient."""
    ca, cb = a >> 1, b >> 1
    e = edge_dir(a, b, st)
    if e:
        return (e - 1) & 7
    best, bestd = _best_neighbour(st, ph.ALARM, ca, cb)
    if best:
        return walk(st, d, bestd)
    return walk(st, d, st.rand8())


def black_guard_dir(st, a, b, d):
    """f_146fc: black recruits / guards (mode G:048c)."""
    si = edge_dir(a, b, st)
    if si:
        return (si - 1) & 7
    mode = st.u16(G, 0x48c)
    if mode == 1:
        if st.u16(G, 0x248) == 1:
            si = dir_to(a, b, s16(st.u16(G, 0xf12)) >> 4, s16(st.u16(G, 0xf34)) >> 4)
        else:
            dist = distance_lo(a, b, s16(st.u16(G, 0x22a)), s16(st.u16(G, 0x238)))
            if (s16(st.u16(G, 0xb1c)) >> 1) < dist:
                si = dir_to(a, b, s16(st.u16(G, 0x22a)), s16(st.u16(G, 0x238)))
            else:
                si = st.rand(8) + 1
    elif mode == 2:
        return home_dir(st, a, b, d, 0)
    elif mode == 3:
        return home_dir(st, a, b, d, 0x80)
    if si == 0:
        return d
    return walk(st, d, si - 1)


def red_guard_dir(st, a, b, d):
    """f_147fe: red guards (mode G:0498; guard point G:0490/0494; radius red defenders G:0c34 / 2)."""
    si = edge_dir(a, b, st)
    if si:
        return (si - 1) & 7
    mode = st.u16(G, 0x498)
    if mode == 1:
        dist = distance_lo(a, b, s16(st.u16(G, 0x490)), s16(st.u16(G, 0x494)))
        if (s16(st.u16(G, 0xc34)) >> 1) < dist:
            si = dir_to(a, b, s16(st.u16(G, 0x490)), s16(st.u16(G, 0x494)))
        else:
            si = st.rand(8) + 1
    elif mode == 2:
        return home_dir(st, a, b, d, 0)
    elif mode == 3:
        return home_dir(st, a, b, d, 0x80)
    if si == 0:
        return d
    return walk(st, d, si - 1)


def take_food_at(st, a, b):
    """f_0c618: take one unit from a food crumb."""
    t = st.grid(SURFACE, a, b)
    if st.u16(G, 0xf24) == 0:
        if t == 0x48:
            st.set_grid(SURFACE, a, b, st.rand16())
        else:
            st.set_grid(SURFACE, a, b, t - 1)
    else:
        if t % 4 == 0:
            st.set_grid(SURFACE, a, b, (t - 0x18) >> 2)
        else:
            st.set_grid(SURFACE, a, b, t - 1)
    if s16(st.u16(G, 0x1040)) > 0:
        st.set16(G, 0x1040, st.u16(G, 0x1040) - 1)


def surface_ant_at(st, a, b):
    """f_0eea1: index of the live surface ant at (a, b), searching from the top; -1 if none."""
    i = s16(st.u16(G, 0xd6a))
    while i > 0:
        i -= 1
        if st.u8(SIM, 0xa180 + i) == a and st.u8(SIM, 0xa569 + i) == b and st.u8(SIM, 0xad3b + i):
            return i
    return -1


def state_for_caste(st, caste, t):
    """f_141a6 -> f_141cb (black) / f_14260 (red): the next job for an ant of this caste."""
    if t & 0x80:
        if caste == 2:
            return st.u8(T, 0xb9e + st.u16(G, 0x10a6) * 8 + st.rand8())
        if caste == 6:
            return st.u8(T, 0xbce + st.u16(G, 0x10a6) * 8 + st.rand8())
        return st.u8(T, 0xbfe + caste)
    if st.u16(G, 0x378) == 1:
        if caste == 2:
            return st.u8(T, 0xb9e + st.u16(G, 0x1094) * 8 + st.rand8())
        if caste == 6:
            return st.u8(T, 0xbce + st.u16(G, 0x1094) * 8 + st.rand8())
        return st.u8(T, 0xbfe + caste)
    if caste in (2, 6):
        return st.u16(T, 0xc10) & 0xff
    return st.u8(T, 0xbfe + caste)
