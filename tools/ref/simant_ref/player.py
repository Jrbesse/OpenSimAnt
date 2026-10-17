"""The player: the yellow ant's per-tick upkeep (sec27 f_7bf7e) and its actions (f_7b7b8), with the
view-generic map accessors of segment 10f7 they use.

The yellow ant is G:047C (a) / G:048A (b) in view G:048C (1 surface, 2 black nest, 3 red nest), type
G:04C2, colour G:04E2 (0 black), heading G:0496, health G:0F78. It sits in the view's occupancy grid as
0xFF (a queen's second cell, behind her, as 0xFE). With G:0A06 != 0 the player is not an ant (the spider).
Screen-only effects go to st.player.effect; f_2f7d0(n) (dialogs, the yellow ant's death, ...) to
st.player.game_event.
"""
from .state import SIM, G, T
from . import nestgrid as ng
from . import nest
from . import red_nest
from . import movement as mv
from . import colony as co
from .movement import s16

SURFACE, OCC = 0x0180, 0x6180
NESTS = {2: nest.BLACK, 3: nest.RED}


# ------------------------------------------------------------------------------------------- map accessors
def in_view(view, a, b):
    """f_10f7e: surface 128 x 64 (f_137d7), nests 64 x 64 (f_13804)."""
    if view <= 1:
        return 0 <= a <= 0x7f and 0 <= b <= 0x3f
    return 0 <= a <= 0x3f and 0 <= b <= 0x3f


def get_tile(st, view, a, b):
    """GetTile f_117c0: surface tile / nest dirt, -1 outside (or for a negative view)."""
    if not in_view(view, a, b) or view < 0 or view > 3:
        return -1
    base = SURFACE if view <= 1 else NESTS[view]['dirt']
    return st.grid(base, a, b)


def is_dirt(st, view, a, b):
    """f_1345e: a nest cell the yellow ant would dig through (diggable dirt, or tiles 0x1C..0x1F)."""
    if view < 2 or not in_view(view, a, b):
        return False
    t = get_tile(st, view, a, b)
    return ng.is_diggable(t) or 0x1c <= t <= 0x1f                     # f_11654


def dig_through(st, view, a, b):
    """f_15031: dig the nest cell (the top rows open a new entrance above)."""
    if not is_dirt(st, view, a, b):
        return
    n = NESTS[2] if view == 2 else NESTS[3]
    if b <= 1:
        st.set_grid(n['dirt'], a, 0, 0x18)
        nest.make_surface_hole(st, n, a)
        if b != 1:
            return
    ng.dig_at(st, n, a, b)


def set_occ(st, view, a, b, v):
    """f_1156e: write the view's occupancy grid (in the nests, the yellow ant digs its way)."""
    if not in_view(view, a, b):
        return
    if view >= 0:
        if view <= 1:
            st.set_grid(OCC, a, b, v)
        elif view in NESTS:
            st.set_grid(NESTS[view]['cells'], a, b, v)
            if s16(v) > 0 and is_dirt(st, view, a, b):
                dig_through(st, view, a, b)
                st.player.effect(st, 'sound', 0x13)
    st.player.effect(st, 'redraw', view, a, b)                         # f_0250e


def set_queen_tail(st, view, a, b, heading, v):
    """f_1196c: the queen's second cell, behind her."""
    h = (heading ^ 4) & 0xffff
    set_occ(st, view, a + st.s8(T, h), b + st.s8(T, 8 + h), 0xfe if v == 0xff else v)


def put_yellow(st, view, a, b, t, heading, v):
    """f_119b4: write the yellow ant (v 0xFF) or clear it (v 0) at (view, a, b); v != 0 also records it
    as the yellow ant's position."""
    if not in_view(view, a, b):
        return
    set_occ(st, view, a, b, v)
    if t == 0x60:
        set_queen_tail(st, view, a, b, heading, v)
    if v:
        st.set16(G, 0x47c, a)
        st.set16(G, 0x48a, b)
        st.set16(G, 0x496, heading)
        st.set16(G, 0x4c2, t)
        st.set16(G, 0x48c, view)


def set_health(st, hp):
    """f_12d43: the yellow ant's health G:0F78 (0..100; T:0C16 keeps it full); G:1044 warns when low."""
    hp = s16(hp)
    st.set16(G, 0xf78, 100 if st.u16(T, 0xc16) else hp)
    if s16(st.u16(G, 0xf78)) > 0:
        st.set16(G, 0x1006, 0)
    if s16(st.u16(G, 0xf78)) > 100:
        st.set16(G, 0xf78, 100)
    elif s16(st.u16(G, 0xf78)) < 0:
        st.set16(G, 0xf78, 0)
    hp = s16(st.u16(G, 0xf78))
    st.set16(G, 0x1044, 0 if hp > s16(st.u16(G, 0xfba)) and hp >= 10 else 1)


def get_occ(st, view, a, b):
    """GetOccupant f_11737: the view's occupancy byte, -1 if empty or outside."""
    if not in_view(view, a, b) or view < 0:
        return -1
    if view <= 1:
        v = st.grid(OCC, a, b)
    elif view in NESTS:
        v = st.grid(NESTS[view]['cells'], a, b)
    else:
        return -1
    return v if v else -1


def clear_occ_if(st, view, a, b, v):
    """f_118c4: clear the cell if it holds v."""
    if not in_view(view, a, b):
        return
    if get_occ(st, view, a, b) == v:
        set_occ(st, view, a, b, 0)
    st.player.effect(st, 'redraw', view, a, b)                         # f_0250e


def take_yellow(st, view, a, b, t, heading):
    """f_11918: lift the yellow ant (and a queen's second cell) off the map."""
    clear_occ_if(st, view, a, b, 0xff)
    if t == 0x60:
        h = (heading ^ 4) & 0xffff
        clear_occ_if(st, view, a + st.s8(T, h), b + st.s8(T, 8 + h), 0xfe)


def move_yellow(st, view, a, b, t, heading):
    """f_11a3e: move the yellow ant to (view, a, b) (view 0 means the surface)."""
    take_yellow(st, s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)),
                s16(st.u16(G, 0x4c2)), st.u16(G, 0x496))
    put_yellow(st, view or 1, a, b, t, heading, 0xff)


ANTS = {1: dict(x=0xa180, y=0xa569, type=0xad3b, state=0xa952, e=0xb124, count=0xd6a),
        2: dict(x=0xb50d, y=0xb702, type=0xbaec, state=0xb8f7, e=0xbce1, count=0xda8),
        3: dict(x=0xbed6, y=0xc0cb, type=0xc4b5, state=0xc2c0, e=0xc6aa, count=0xeaa)}


def _ants(view):
    return ANTS[1] if view <= 1 else ANTS[2] if view == 2 else ANTS[3]


def get_ant(st, view, i):
    """f_10fcd: (a, b, type, state, e) of ant i of the view's list, None if out of range."""
    f = _ants(view)
    if i < 0 or s16(st.u16(G, f['count'])) <= i:
        return None
    return tuple(st.u8(SIM, f[k] + i) for k in ('x', 'y', 'type', 'state', 'e'))


def set_ant(st, view, i, a, b, t, state, e):
    """f_11121."""
    f = _ants(view)
    if i < 0 or s16(st.u16(G, f['count'])) <= i:
        return
    for k, v in (('x', a), ('y', b), ('type', t), ('state', state), ('e', e)):
        st.set8(SIM, f[k] + i, v)


def find_ant(st, view, a, b, lo, hi, mask):
    """f_11246: the top-most ant at (a, b) with lo <= type & mask <= hi, -1 if none."""
    f = _ants(view)
    i = s16(st.u16(G, f['count'])) - 1
    while i >= 0:
        t = st.u8(SIM, f['type'] + i) & mask
        if st.u8(SIM, f['x'] + i) == a and st.u8(SIM, f['y'] + i) == b and lo <= t <= hi:
            return i
        i -= 1
    return i


def is_brood(t):
    """f_1162f."""
    return 1 <= t & 0x7f <= 7


def add_surface_ant_raw(st, a, b, t, state, e):
    """f_0f167: append a surface ant (and write the occupancy grid)."""
    i = s16(st.u16(G, 0xd6a))
    if i >= 1000:
        return
    for k, v in ((0xa180, a), (0xa569, b), (0xa952, state), (0xad3b, t), (0xb124, e)):
        st.set8(SIM, k + i, v)
    st.set_grid(OCC, a, b, t)
    st.inc16(G, 0xd6a)


def add_ant(st, view, a, b, t, state, e):
    """f_114bd: add an ant to the view's list (if there is room) and put it on the map. 1 if added."""
    if view <= 1:
        if s16(st.u16(G, 0xd6a)) >= 1000:
            return 0
        add_surface_ant_raw(st, a, b, t, state, e)
    else:
        n = NESTS[2] if view == 2 else NESTS[3]
        if s16(st.u16(G, n['count'])) >= 500:
            return 0
        ng.add_nest_ant(st, n, a, b, t, state, e)
    set_occ(st, view, a, b, t)
    return 1


def is_rock(view, t):
    """f_116a1."""
    if view > 1:
        return 0x30 <= t <= 0x31
    return view == 1 and 0x51 <= t <= 0x53


def is_nest_food(t):
    """f_116d6."""
    return 0x10 <= t <= 0x13


def is_food(st, view, t):
    """f_1167b."""
    return mv.is_food(st, t) if view <= 1 else is_nest_food(t)


def food_at(st, view, a, b):
    """f_116f7."""
    t = get_tile(st, view, a, b)
    return t >= 0 and is_food(st, view, t)


def at_exit(st, view, a, b):
    """f_13791: on a nest entrance (surface) / on the top row's entrance tile 0x18 (nest)."""
    if view <= 1:
        return mv.at_nest_entrance(st, a, b)
    return b <= 0 and get_tile(st, view, a, b) == 0x18


def _low_tile(st, t):
    """f_133cc."""
    return t <= 0x50 if st.u16(G, 0xf24) == 0 else t <= 0x5f


def can_drop(st, view, a, b):
    """f_133f9: open ground (or a tunnel / rock in the nest)."""
    t = get_tile(st, view, a, b)
    if t < 0:
        return False
    if view <= 1:
        return t <= 0x53 if st.u16(G, 0xf24) == 0 else _low_tile(st, t)
    return t <= 0x18 or is_rock(view, t)


def jingle(st):
    """f_0cd37: at most every 0x1C20 clock ticks, the next of three tunes (G:0228)."""
    if _s32(st.u32(G, 0x214) + 0x1c20) > _s32(st.read_clock()):
        return
    st.set32(G, 0x214, st.read_clock())
    st.inc16(G, 0x228)
    if s16(st.u16(G, 0x228)) > 2:
        st.set16(G, 0x228, 0)
    st.player.effect(st, 'music', st.u16(G, 0x228) + 0x2713)


# ------------------------------------------------------------------------------------------- pathfinding
# The yellow ant walks to the cursor target G:0AF8 (view) / G:0AD6 (a) / G:0AE8 (b) one cell per tick. A
# greedy step that gets closer is preferred; when blocked it follows the wall (side G:0EFA: 1 clockwise,
# -1 counter-clockwise, heading G:0EF8) for up to 16 steps (G:0D6C), never back onto its last cell
# (G:0AB6 / G:0AC6). In mode 2 (G:0A8E) it digs through nest dirt.
def is_open_ground(st, view, a, b):
    """IsOpenGround f_1145c: tile < 0x10 (surface) / < 8 (nest), no occupant but the yellow ant."""
    t = get_tile(st, view, a, b)
    if t < 0:
        return False
    o = get_occ(st, view, a, b)
    if o >= 0 and not mv.is_yellow(o):
        return False
    return t < (0x10 if view <= 1 else 8)


def is_walkable(st, view, a, b, tv, ta, tb, dig):
    """IsWalkable f_1323e. In the nests the top two rows lead only to the exit the target is at."""
    if view <= 1:
        if not (0 <= a <= 0x7f and 0 <= b <= 0x3f):
            return False
        t = st.grid(SURFACE, a, b)
        return t <= 0x53 if st.u16(G, 0xf24) == 0 else t <= 0x90
    if not (0 <= a <= 0x3f and 0 <= b <= 0x3f):
        return False
    n = NESTS[2] if view == 2 else NESTS[3]
    t = st.grid(n['dirt'], a, b)
    if t <= 0x18 or 0x30 <= t <= 0x31:
        dirt = False
    elif dig and (0x20 <= t <= 0x2e or 0x1c <= t <= 0x1f):
        dirt = True
    else:
        return False
    if b > 1 or tv != view:
        return True
    if not dig:
        if b == 0:
            return ta == a and tb == 0
        return ta == a or tb != 0
    if not dirt:
        return b != 0 or (ta == a and tb == 0)
    if ta != a:
        return False
    if b != 0:
        return True
    t1 = st.grid(n['dirt'], a, 1)
    return not (0x20 <= t1 <= 0x2e)


def _dist(a, b, ta, tb):
    """Distance f_0ca03, low word as a signed int (how these callers read it)."""
    return s16(co.distance(a, b, ta, tb))


def _dig_mode(st):
    return 1 if st.u16(G, 0xa8e) == 2 else 0


def _walkable_to_target(st, view, a, b):
    return is_walkable(st, view, a, b, s16(st.u16(G, 0xaf8)), s16(st.u16(G, 0xad6)), s16(st.u16(G, 0xae8)),
                       _dig_mode(st))


def greedy_step(st, view, a, b, ta, tb):
    """f_7cd31: the neighbour that brings the yellow ant closest (each closer one tightens the threshold);
    the last free open-ground one wins, else the last other one. -1 when there, -2 when nothing is closer."""
    best = _dist(a, b, ta, tb)
    if best <= 0:
        return -1
    free, busy = -1, -2
    for d in range(8):
        na, nb = a + st.s8(T, d), b + st.s8(T, 8 + d)
        if not _walkable_to_target(st, view, na, nb):
            continue
        nd = _dist(na, nb, ta, tb)
        if nd >= best:
            continue
        if get_occ(st, view, na, nb) > 0 or not is_open_ground(st, view, na, nb):
            busy = d
        else:
            free = d
        best = nd
    return free if free >= 0 else busy


def look_ahead(st, view, a, b, ta, tb):
    """f_7d03a: follow greedy steps (up to 64): -2 if they run into a block, else -1."""
    d = greedy_step(st, view, a, b, ta, tb)
    if d < 0:
        return d
    x, y = a + st.s8(T, d), b + st.s8(T, 8 + d)
    n = 0
    while d >= 0 and n < 0x40:
        d = greedy_step(st, view, x, y, ta, tb)
        if d >= 0:
            x += st.s8(T, d)
            y += st.s8(T, 8 + d)
        n += 1
    return -1 if d >= 0 else d


def wall_step(st, view, a, b, ta, tb):
    """f_7ce36: follow the wall (G:0EFA side, G:0EF8 heading); back to greedy (side 0) once a step does not
    get further from the target."""
    dist0 = _dist(a, b, ta, tb)
    if dist0 <= 0:
        return -1
    ok = []
    anyd = -2
    pa, pb = s16(st.u16(G, 0xab6)), s16(st.u16(G, 0xac6))
    for d in range(8):
        na, nb = a + st.s8(T, d), b + st.s8(T, 8 + d)
        w = not (na == pa and nb == pb) and _walkable_to_target(st, view, na, nb)
        if w:
            anyd = d
        ok.append(w)
    if anyd < 0:
        return anyd
    side = s16(st.u16(G, 0xefa))
    h = st.u16(G, 0xef8)
    cw, ccw = h, h
    if side == 0:                                                      # pick a side
        for _ in range(8):
            if ok[cw & 7]:
                st.set16(G, 0xef8, mv.dir_to(a, b, ta, tb) - 1)
                st.set16(G, 0xefa, 1)
                return cw
            if ok[ccw & 7]:
                st.set16(G, 0xef8, mv.dir_to(a, b, ta, tb) - 1)
                st.set16(G, 0xefa, 0xffff)
                return ccw
            cw = (cw + 1) & 7
            ccw = (ccw - 1) & 7
        return -1
    for _ in range(8):
        if side > 0:
            d = cw
        else:
            d = ccw
        if ok[d & 7]:
            if _dist(a + st.s8(T, d), b + st.s8(T, 8 + d), ta, tb) <= dist0:
                st.set16(G, 0xef8, mv.dir_to(a, b, ta, tb) - 1)
                st.set16(G, 0xefa, 0)
            return d
        cw = (cw + 1) & 7
        ccw = (ccw - 1) & 7
    return -1


def start_wall(st, view, a, b, ta, tb):
    """f_7d15d: start following the wall for 16 steps."""
    st.set16(G, 0xef8, mv.dir_to(a, b, ta, tb) - 1)
    st.set16(G, 0xd6c, 0x10)
    st.set16(G, 0xefa, 0)
    return wall_step(st, view, a, b, ta, tb)


def wall_or_greedy(st, view, a, b, ta, tb):
    """f_7d0e5."""
    if look_ahead(st, view, a, b, ta, tb) == -2:
        return wall_step(st, view, a, b, ta, tb)
    st.set16(G, 0xd6c, 0xffff)
    return greedy_step(st, view, a, b, ta, tb)


def path_step(st, view, a, b, ta, tb):
    """f_7d1bd."""
    if s16(st.u16(G, 0xd6c)) < 0:
        d = greedy_step(st, view, a, b, ta, tb)
        if d == -2 and s16(st.u16(G, 0xd6c)) == -2:
            d = start_wall(st, view, a, b, ta, tb)
        return d
    d = wall_or_greedy(st, view, a, b, ta, tb)
    st.inc16(G, 0xd6c, -1)
    return d


def step_to_cursor(st, view, a, b, tv, ta, tb):
    """f_7d24f: the next step towards the cursor; in another view, towards this view's way out."""
    if view <= 1:
        if tv > 1:
            off = 0x2ac if tv == 2 else 0x2b0                           # that nest's entrance on the surface
            ta, tb = s16(st.u16(T, off)), s16(st.u16(T, off + 2))
    elif tv != view:
        off = 0x2a4 if view == 2 else 0x2a8                             # this nest's exit column, row 0
        ta, tb = s16(st.u16(T, off)), s16(st.u16(T, off + 2))
    return path_step(st, view, a, b, ta, tb)


def _s32(v):
    v &= 0xffffffff
    return v - 0x100000000 if v & 0x80000000 else v


def _hp(st):
    return s16(st.u16(G, 0xf78))


# ------------------------------------------------------------------------------------------- upkeep
def yellow_tick(st):
    """f_7bf7e: keep the yellow ant on the map, age it, let a yellow queen lay; it dies after 100 ticks
    at zero health."""
    if st.u16(G, 0xa06) != 0:
        return
    view = s16(st.u16(G, 0x48c))
    a, b = s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    put_yellow(st, view, a, b, s16(st.u16(G, 0x4c2)), st.u16(G, 0x496), 0xff)
    view = s16(st.u16(G, 0x48c))
    a, b = s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    if st.u8(G, 0xf08) & 0x3f == 0:
        set_health(st, _hp(st) - 1)
    tile = None
    if view >= 2:
        tile = get_tile(st, view, a, b)
        if tile >= 0x4e:                                               # flooded
            set_health(st, _hp(st) - 1)
    if st.u16(G, 0x4c2) == 0x60 and view > 1 and st.u8(G, 0xf08) & 0xf == 0:
        h = st.u16(G, 0x496) ^ 4
        eb = st.s8(T, 8 + h) * 2 + s16(st.u16(G, 0x48a))
        ea = st.s8(T, h) * 2 + s16(st.u16(G, 0x47c))
        if nest.nest_cell_free(ea, eb) and st.rand128() <= _hp(st):     # lay an egg behind her
            if st.u16(G, 0x4e2) == 0:
                nest.spawn_brood(st, nest.BLACK, ea, eb, 1)
                nest.egg_cost(st)
            else:
                nest.spawn_brood(st, nest.RED, ea, eb, 1)
                red_nest.egg_cost(st)
            set_health(st, _hp(st) - 5)
    if _hp(st) <= 0:
        st.inc16(G, 0x1006)
        if s16(st.u16(G, 0x1006)) >= 100:
            st.player.game_event(st, 7 if view >= 2 and tile >= 0x4e else 8)
