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
from . import pheromones as ph
from . import world
from . import surface
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


# ------------------------------------------------------------------------------------------- acting on a cell
# Carrying castes are odd: 1 brood (type T:0C22), 3 / 7 food, 5 / 9 a pebble. Drops go to the free neighbour
# first in the order T:006C from the heading towards the target, else the yellow ant's own cell.
# Holding Shift and Alt (BIOS keyboard flags 0000:0417, st.bios_kbd) keeps the load: a hidden cheat.
def set_tile(st, view, a, b, v):
    """SetTile f_1183e."""
    if not in_view(view, a, b):
        return
    if 0 <= view <= 3:
        base = SURFACE if view <= 1 else NESTS[view]['dirt']
        st.set_grid(base, a, b, v)
    st.player.effect(st, 'redraw', view, a, b)                         # f_0250e


def _cheat(st):
    k = st.bios_kbd & 0xff
    return k & 3 and k & 8


def find_ant_exact(st, view, a, b, t):
    """f_11327: the top-most ant at (a, b) with type t, -1 if none."""
    f = _ants(view)
    i = s16(st.u16(G, f['count']))
    while i > 0:
        i -= 1
        if st.u8(SIM, f['x'] + i) == a and st.u8(SIM, f['y'] + i) == b and st.u8(SIM, f['type'] + i) == t:
            return i
    return -1


def _drop_spot(st, view, ya, yb, ta, tb, ok):
    """The search shared by the drops: (heading, a, b, result) of the first neighbour (empty and ok) in the
    order T:006C, else the yellow ant's own cell if ok; None if nowhere."""
    d = mv.dir_to(ya, yb, ta, tb)
    h = d - 1 if d > 0 else st.u16(G, 0x496)
    for k in range(8):
        dd = (st.u8(T, 0x6c + k) + h) & 7
        x, y = ya + st.s8(T, dd), yb + st.s8(T, 8 + dd)
        if in_view(view, x, y) and get_occ(st, view, x, y) < 0:
            r = ok(x, y)
            if r is not None:
                return dd, x, y, r
    if in_view(view, ya, yb):
        r = ok(ya, yb)
        if r is not None:
            return h, ya, yb, r
    return None


def drop_food(st, view, ya, yb, ta, tb):
    """f_12306 (type 0x18 / 0x38): add the food to a crumb (up to 3 more) or put a new one down."""
    if st.u16(G, 0x4c2) not in (0x18, 0x38):
        return 0

    def ok(x, y):
        t = get_tile(st, view, x, y)
        if is_food(st, view, t) and t & 3 < 3:
            return t + 1
        if is_open_ground(st, view, x, y) or t == 0x38:
            return 0x10
        return None
    spot = _drop_spot(st, view, ya, yb, ta, tb, ok)
    if spot is None:
        return 0
    h, x, y, t = spot
    st.set16(G, 0x496, h)
    if view <= 1:
        world.spider_drop_food(st, x, y)                                # f_0c692
    else:
        set_tile(st, view, x, y, t)
        st.inc16(G, 0x1050 if view == 2 else 0x1060)
    if not _cheat(st):
        st.set16(G, 0x4c2, st.u16(G, 0x4c2) & 0xf7)
    st.player.effect(st, 'sound', 0x1d)
    return 1


def put_pebble(st, view, a, b):
    """f_1252c: a pebble on an entrance blocks the nest cell below (0x31) and vice versa."""
    if view <= 1:
        if at_exit(st, view, a, b):
            if a < 0x40 and st.u8(T, 0x224 + b) == a:
                st.set_grid(NESTS[2]['dirt'], b, 0, 0x31)
            elif st.u8(T, 0x264 + b) == a:
                st.set_grid(NESTS[3]['dirt'], b, 0, 0x31)
        t = 0x51
    elif at_exit(st, view, a, b):
        st.set_grid(SURFACE, st.u8(T, (0x224 if view == 2 else 0x264) + a), a, 0x51)
        t = 0x31
    else:
        t = 0x30
    set_tile(st, view, a, b, t)


def drop_pebble(st, view, ya, yb, ta, tb):
    """f_12606 (type 0x28 / 0x48)."""
    if st.u16(G, 0x4c2) not in (0x28, 0x48):
        return 0

    def ok(x, y):
        if is_open_ground(st, view, x, y):
            return 1
        t = get_tile(st, view, x, y)
        if is_food(st, view, t) or is_rock(view, t):
            return None
        if at_exit(st, view, x, y) or t == 0x38:
            return 1
        return None
    spot = _drop_spot(st, view, ya, yb, ta, tb, ok)
    if spot is None:
        return 0
    h, x, y, _ = spot
    st.set16(G, 0x496, h)
    put_pebble(st, view, x, y)
    if not _cheat(st) and st.u16(G, 0x4c2) in (0x28, 0x48):
        st.inc16(G, 0x4c2, -0x18)
    st.player.effect(st, 'sound', 0x1e)
    return 1


def drop_brood(st, view, ya, yb, ta, tb):
    """f_12820 (type 0x08): the carried brood (type T:0C22) becomes an ant again (state 8)."""
    if st.u16(G, 0x4c2) != 8:
        return 0

    def ok(x, y):
        if is_open_ground(st, view, x, y) or get_tile(st, view, x, y) == 0x38:
            return 1
        return None
    spot = _drop_spot(st, view, ya, yb, ta, tb, ok)
    if spot is None:
        return 0
    h, x, y, _ = spot
    if not add_ant(st, view, x, y, st.u16(T, 0xc22), 8, 0):
        return 0
    st.set16(G, 0x496, h)
    if not _cheat(st):
        st.set16(G, 0x4c2, 0x10)
        st.set16(T, 0xc22, 0xfd)
    put_yellow(st, s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)),
               st.u16(G, 0x4c2), st.u16(G, 0x496), 0xff)
    st.player.effect(st, 'sound', 0x1c)
    return 1


def drop_load(st, view, ya, yb, ta, tb):
    """f_1317c: drop whatever the yellow ant carries towards (ta, tb)."""
    t = st.u16(G, 0x4c2)
    if t == 0x08:
        return drop_brood(st, view, ya, yb, ta, tb)
    if t in (0x18, 0x38):
        return drop_food(st, view, ya, yb, ta, tb)
    if t in (0x28, 0x48):
        return drop_pebble(st, view, ya, yb, ta, tb)
    return 0


def brood_at(st, view, a, b):
    """f_12bf4: (type, index) of the brood at (a, b), (-1, -1) if none."""
    o = get_occ(st, view, a, b)
    if is_brood(o) and not mv.is_yellow(o):
        return o, find_ant_exact(st, view, a, b, o)
    i = find_ant(st, view, a, b, 1, 7, 0x7f)
    if i >= 0:
        return get_ant(st, view, i)[2], i
    return -1, -1


def take_brood(st, view, a, b):
    """f_12f4f: a plain worker picks up brood; a weak yellow ant (health < 10) eats it instead."""
    if st.u16(G, 0x4c2) != 0x10 and _hp(st) >= 10:
        return 0
    st.set16(T, 0xc22, 0xfd)
    t, i = brood_at(st, view, a, b)
    if t < 0:
        return 0
    set_ant(st, view, i, 0, 0, 0, 0, 0)
    if (s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))) != (a, b):
        set_occ(st, view, a, b, 0)
    if _hp(st) >= 10:
        st.player.effect(st, 'sound', 0x1c)
        st.set16(T, 0xc22, t)
        st.set16(G, 0x4c2, 8)
    else:
        st.set16(T, 0xc26, 3)                                           # eat it (MenuCommand12de1(3))
    return 1


def take_pebble(st, view, a, b):
    """f_12a1e: a plain worker or soldier picks up a pebble (one blocking an entrance reopens it)."""
    if st.u16(G, 0x4c2) not in (0x10, 0x30):
        return 0
    t = get_tile(st, view, a, b)
    picked = False
    if view <= 1:
        if is_rock(view, t):
            blocking = False
            if a < 0x40:
                if st.u8(T, 0x224 + b) == a:
                    st.set_grid(NESTS[2]['dirt'], b, 0, 0x18)
                    blocking = True
            elif st.u8(T, 0x264 + b) == a:
                st.set_grid(NESTS[3]['dirt'], b, 0, 0x18)
                blocking = True
            if blocking:
                st.set_grid(SURFACE, a, b, 0x50 if st.u16(G, 0xf24) == 0 else st.rand(7) + 0x59)
            else:
                st.set_grid(SURFACE, a, b, st.rand16() if st.u16(G, 0xf24) == 0 else 0)
            picked = True
    elif t == 0x30:
        set_tile(st, view, a, b, st.rand8())
        picked = True
    elif t == 0x31:
        n = NESTS[2] if view == 2 else NESTS[3]
        st.set_grid(n['dirt'], a, b, 0x18)
        st.set_grid(SURFACE, st.u8(T, n['entr'] + a), a, 0x50)
        picked = True
    if picked:
        st.set16(G, 0x4c2, 0x28 if st.u16(G, 0x4c2) == 0x10 else 0x48)
        st.player.effect(st, 'sound', 0x1e)
    return 1 if picked else 0


def take_food(st, view, a, b):
    """f_1302f: pick up food (laying the black food trail on the surface); with low health eat it."""
    if not food_at(st, view, a, b):
        return 0
    eat = st.u16(G, 0x1044) != 0
    if not eat and st.u16(G, 0x4c2) not in (0x10, 0x30):
        return 0
    if view <= 1:
        mv.take_food_at(st, a, b)
        if not eat:
            st.set16(G, 0x4c4, 200)
            d = co.distance(a, b, s16(st.u16(T, 0x2ac)), s16(st.u16(T, 0x2ae))) & 0xffff
            st.set16(G, 0xb1e, d)
            st.set16(G, 0xc38, d + 1)
            ph.lay_max(st, ph.BLACK_TRAIL, a, b, st.u16(G, 0x4c4))
    else:
        t = get_tile(st, view, a, b)
        set_tile(st, view, a, b, st.rand8() if t == 0x10 else t - 1)
        food = 0x1050 if view == 2 else 0x1060
        if s16(st.u16(G, food)) > 0:
            st.inc16(G, food, -1)
    if eat:
        st.set16(T, 0xc26, 0)                                           # eat it (MenuCommand12de1(0))
    else:
        st.player.effect(st, 'sound', 0x1d)
        st.inc16(G, 0x4c2, 8)
    return 1


def pick_up(st, view, a, b):
    """f_131ea: brood, else a pebble, else food."""
    if st.u8(G, 0x4c2) & 8:
        return 0
    return take_brood(st, view, a, b) or take_pebble(st, view, a, b) or take_food(st, view, a, b)


def eat(st, n):
    """MenuCommand12de1: n 0 eat food, 3 eat brood (both feed the colony with the old health), 1 / 2 other
    menu actions (2 costs 10 health). Pictures and messages go to effects."""
    st.player.effect(st, 'menu', n)                                    # f_2f802 / f_2f82a / f_15e2c
    if n in (1, 3):
        st.set16(G, 0x474, 0)
        st.set16(G, 0x472, 0)
    if n == 2:
        hp = _hp(st)
        if hp > 10:
            set_health(st, hp - 10)
        return
    hp = _hp(st)
    if s16(hp + 100) > 100 and n != 1:
        k = s16(st.u16(G, 0x330) - 1)
        if k > 0:
            st.inc16(G, 0x10be, co._cdiv(hp, k))
            if s16(st.u16(G, 0x10be)) > 100:
                st.set16(G, 0x10be, 100)
    set_health(st, 100)


def found_nest(st, a, b):
    """f_14f59: a new queen opens a nest entrance at (a, b) (black on the left half, red on the right)."""
    if not (1 <= a < 0x7f and 1 <= b < 0x3f):
        return
    if st.u16(G, 0xf24):
        st.set_grid(SURFACE, a, b, 0x59)
    else:
        st.set_grid(SURFACE, a, b, 0x50)
        nest.entrance_ring(st, a, b)
    if a < 0x40:
        st.set8(T, 0x224 + b, a)
        ng.dig_at(st, ng.BLACK, b, 1)
        st.set16(T, 0x2ac, a)
        st.set16(T, 0x2ae, b)
        st.set16(T, 0x2a4, b)
        st.set16(T, 0x2a6, 0)
    else:
        st.set8(T, 0x264 + b, a)
        ng.dig_at(st, ng.RED, b, 1)
        st.set16(T, 0x2b0, a)
        st.set16(T, 0x2b2, b)
        st.set16(T, 0x2a8, b)
        st.set16(T, 0x2aa, 0)


def try_found_nest(st, a, b):
    """f_14ee2: found a nest here if there is room (open 3x3 in the yard; any tile < 0xC8 in the house)."""
    if not (1 <= a <= 0x7f and 1 <= b <= 0x3f):
        return 0
    if st.u16(G, 0xf24) == 0:
        ok = nest.is_open_with_ring(st, a, b)
    else:
        ok = st.grid(SURFACE, a, b) < 0xc8
    if ok:
        found_nest(st, a, b)
        return 1
    return 0


def act_on_cell(st, view, a, b):
    """f_13644: the yellow ant acts on the target cell next to (or under) it. 1 done, -1 failed, 0 nothing."""
    ya, yb = s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    if st.u8(G, 0x4c2) & 8:
        return 1 if drop_load(st, view, ya, yb, a, b) else -1
    if not pick_up(st, view, a, b):
        t = st.u16(G, 0x4c2)
        if (st.u16(T, 0x798) or (t == 0x40 and st.u16(T, 0xc24) == 0)) and view == 1 and (ya, yb) == (a, b):
            if try_found_nest(st, a, b):
                enter_nest(st)                                          # f_2f834
                ui_follow(st)                                           # f_01c52
                return 1
            return -1
        return 0
    d = mv.dir_to(ya, yb, a, b)
    if d > 0:
        move_yellow(st, s16(st.u16(G, 0x48c)), ya, yb, s16(st.u16(G, 0x4c2)), d - 1)
    st.player.effect(st, 'redraw_all')                                  # f_03391
    c = s16(st.u16(T, 0xc26))
    if c >= 0:
        eat(st, c)
        st.set16(T, 0xc26, 0xffff)
    return 1


def ui_follow(st):
    """f_01c52: G:1074 = 1 and the view scrolls to the yellow ant (f_01aa7, screen only)."""
    st.set16(G, 0x1074, 1)
    st.player.effect(st, 'follow')


# ------------------------------------------------------------------------------------------- nests and fights
def alarm_mode(st, on, quiet):
    """f_76a37 (via f_2f80c): the yellow ant lays alarm scent as it walks (G:104E; surface only)."""
    if on:
        if s16(st.u16(G, 0x48c)) == 1 and st.u16(G, 0xa06) == 0:
            st.set16(T, 0x7be, 0)
            st.player.effect(st, 'menu_check', 0x10, on)                # f_22f65
            st.set16(G, 0x104e, 1)
            if not quiet:
                st.player.effect(st, 'sound', 0xf)
        elif not quiet:
            st.player.effect(st, 'sound', 1)
    else:
        st.set16(G, 0x104e, 0)
        st.player.effect(st, 'menu_check', 0x10, on)
        st.set16(T, 0x7be, 0xffff)
        if not quiet:
            st.player.effect(st, 'sound', 0xf)
    st.player.effect(st, 'redraw_rect')                                  # f_0256e


def enter_nest(st):
    """f_7c7e5 (also via f_2f834): from a surface entrance into the top of nest column b (the black nest
    on the left half of the patch, the red one on the right); alarm-trail mode ends."""
    jingle(st)
    if st.u16(G, 0x104e):
        alarm_mode(st, 0, 1)
    view, a, b = s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    t, h = s16(st.u16(G, 0x4c2)), st.u16(G, 0x496)
    take_yellow(st, view, a, b, t, h)
    st.set16(G, 0x48c, 3 if a > 0x40 else 2)
    st.set16(G, 0x47c, b)
    st.set16(G, 0x48a, 2 if t == 0x60 else 1)
    st.set16(G, 0x496, 4)
    view, a, b = s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    dig_through(st, view, a, b)
    put_yellow(st, view, a, b, t, 4, 0xff)


def leave_nest(st):
    """f_7c8fe: climb out of the nest's entrance (opening one if there is none) onto a free cell next to it
    (2 cells for a queen), facing the cursor if it is on the surface."""
    jingle(st)
    view, a, b = s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    t = s16(st.u16(G, 0x4c2))
    put_yellow(st, view, a, b, t, st.u16(G, 0x496), 0)
    col = st.u8(G, 0x47c) & 0x3f
    st.set16(G, 0x48a, col)
    n = NESTS[2] if view == 2 else NESTS[3]
    if st.u8(T, n['entr'] + col) == 0:
        nest.make_surface_hole(st, n, s16(st.u16(G, 0x47c)))
    st.set16(G, 0x47c, st.u8(T, n['entr'] + col))
    a, b = s16(st.u16(G, 0x47c)), col
    k = 2 if t == 0x60 else 1
    tv = s16(st.u16(G, 0xaf8))
    if tv == 1:
        d = mv.dir_to(a, b, s16(st.u16(G, 0xad6)), s16(st.u16(G, 0xae8)))
        base = d - 1 if d > 0 else d
    elif tv == view:
        base = 2 if a < 0x40 else 6
    else:
        base = step_to_cursor(st, 1, a, b, tv, s16(st.u16(G, 0xad6)), s16(st.u16(G, 0xae8)))
        if base < 0:
            base = st.rand8()
    for i in range(8):
        d = (st.s8(T, 0x6c + i) + base) & 7
        x, y = a + st.s8(T, d) * k, b + st.s8(T, 8 + d) * k
        if can_drop(st, 1, x, y):
            st.set16(G, 0x47c, x)
            st.set16(G, 0x48a, y)
            st.set16(G, 0x496, d)
            break
    else:
        st.set16(G, 0x496, base)
        st.set16(G, 0x47c, (st.u8(G, 0x47c) + k) & 0x7f)
    st.set16(G, 0x48c, 1)
    put_yellow(st, 1, s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)), t, st.u16(G, 0x496), 0xff)


def _anim_frames(st):
    """f_23612(0): the game window is the active one (DS:5702 == 0) → long animations."""
    return st.u16(0x55b3, 0x5702) == 0


def sound_done(st):
    """f_00f28: the last sound has finished (always, without sound hardware DS:1926 or with sound off)."""
    if st.u16(0x55b3, 0x1926) == 0 or st.u16(T, 0x7aa) == 0:
        return True
    return st.player.sound_done(st)


def fight_animation(st, view, a, b, heading, t, mode):
    """f_7c149: the yellow ant flashes as type t with random headings, then is lifted off the map with its
    state restored. Mode 0 (a fight, 6 frames, type 0x70 cloud) or a player event (1 eaten by the spider,
    2 by an ant lion: the pit opens under it; 10 squashed: the ground flickers): 8 frames, 0x20 / 0x40
    (sound on) when the game window is active, events 1..9 stop early once their sound has finished.
    The original waits on the clock between frames (screen only)."""
    put_yellow(st, s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)),
               s16(st.u16(G, 0x4c2)), st.u16(G, 0x496), 0xff)
    saved = (view, a, b, st.u16(G, 0x4c2))
    if mode == 0:
        n = 6
    elif _anim_frames(st):
        n = 0x40 if st.u16(T, 0x7aa) else 0x20
    else:
        n = 8
    if mode == 10:
        under = st.grid(SURFACE, a, b)
        n = 0x20
    k = 3
    for _ in range(n):
        if mode == 0 and st.rand2():
            st.player.effect(st, 'sound', 0x25)
        if mode == 10:
            st.player.effect(st, 'sound', 0x31)
            st.set_grid(SURFACE, a, b, under - 3 if st.rand2() else under)
        if 0 < mode < 10 and st.u16(T, 0x7aa) and sound_done(st):
            break
        if mode == 2:
            set_tile(st, view, a, b, k + 0x38)                         # the pit's frames
            if k < 5:
                k += 1
            elif k > 3:
                k -= 1
        move_yellow(st, view, a, b, t, st.rand8())
    if mode == 10:
        st.set_grid(SURFACE, a, b, under)
    take_yellow(st, view, a, b, t, st.u16(G, 0x496))
    for off, v in zip((0x48c, 0x47c, 0x48a, 0x4c2), saved):
        st.set16(G, off, v)
    st.set16(G, 0x496, heading)


def path_dir(st, view, a, b, ta, tb):
    """f_7a69d: the heading of the neighbour that gets closest to (ta, tb), preferring free open ground;
    -1 if already there, -2 if no neighbour is closer."""
    dist = _dist(a, b, ta, tb)
    if dist <= 0:
        return -1
    best, fallback = -1, -2
    for d in range(8):
        na, nb = a + st.s8(T, d), b + st.s8(T, 8 + d)
        t = get_tile(st, view, na, nb)
        if not can_drop(st, view, na, nb) or is_rock(view, t):
            continue
        nd = _dist(na, nb, ta, tb)
        if nd >= dist:
            continue
        if get_occ(st, view, na, nb) <= 0 and is_open_ground(st, view, na, nb):
            best = d
        else:
            fallback = d
        dist = nd
    return best if best >= 0 else fallback


def insane_animation(st, view, a, b, heading, t):
    """f_7c3b1 (AnimYellowInsane, events 7..9): the yellow ant (as type t) staggers around its spot: back
    there is a random target within 3 cells (C runtime rand), then it heads home; 8 frames, 0x20 when the
    game window is active. Its state is restored afterwards."""
    put_yellow(st, s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)),
               s16(st.u16(G, 0x4c2)), st.u16(G, 0x496), 0xff)
    a0, b0, saved_t = a, b, st.u16(G, 0x4c2)
    n = 0x20 if _anim_frames(st) else 8
    for i in range(n):
        if co.distance(a, b, a0, b0) & 0xffff == 0 and n - i - 1 != 0:
            tb = st.crt_rand_mod(7) + b - 3
            ta = st.crt_rand_mod(7) + a - 3
        else:
            ta, tb = a0, b0
        d = path_dir(st, view, a, b, ta, tb)
        if d >= 0:
            a += st.s8(T, d)
            b += st.s8(T, 8 + d)
        else:
            d = st.rand8()
        move_yellow(st, view, a, b, t, d)
    take_yellow(st, view, a, b, t, st.u16(G, 0x496))
    for off, v in ((0x48c, view), (0x47c, a0), (0x48a, b0), (0x4c2, saved_t), (0x496, heading)):
        st.set16(G, off, v)


def release_recruits(st, more):
    """f_14005: let recruited ants (state 6) go: half the census count G:0D4C, or it + 100; surface and
    black nest ants of the black colony return to state 0, black invaders in the red nest to 7."""
    n = s16(st.u16(G, 0xd4c))
    n = n + 100 if more else int(n / 2)
    for count, tf, sf, new in ((0xd6a, 0xad3b, 0xa952, 0), (0xda8, 0xbaec, 0xb8f7, 0), (0xeaa, 0xc4b5, 0xc2c0, 7)):
        i = s16(st.u16(G, count))
        while i > 0 and n > 0:
            i -= 1
            t = st.u8(SIM, tf + i)
            if t and not t & 0x80 and st.u8(SIM, sf + i) == 6:
                st.set8(SIM, sf + i, new)
                n -= 1


def queen_scene(st, view, a, b, t, found):
    """f_758e0: the yellow ant becomes the queen. found == 0 (the old one died, f_75d01): she comes out of
    her cocoon (G:0502 frames 1..7) as type t. found != 0 (f_76cb9): the yellow queen at (a, b) founds a
    nest there: a queen chamber (f_6ba1c / f_6bb70) and one more adult. The waits are screen only."""
    saved_7ac, old_t = st.u16(T, 0x7ac), st.u16(G, 0x4c2)
    st.set16(T, 0x7ac, 0)
    st.set16(G, 0xa06, 0)
    if found == 0:
        st.set16(G, 0x502, 1)
        put_yellow(st, view, a, b, 0, st.u16(G, 0x496), 0xff)
    else:
        g = lambda off: s16(st.u16(G, off))
        take_yellow(st, g(0x48c), g(0x47c), g(0x48a), g(0x4c2), st.u16(G, 0x496))
        put_yellow(st, g(0x48c), g(0x47c), g(0x48a), 0x60, st.u16(G, 0x496), 0xff)
    if found == 0:
        ui_follow(st)
    st.player.effect(st, 'redraw_all')                                  # f_11ab0
    if found:
        st.player.effect(st, 'sound', 0x4e20)
        set_occ(st, view, a, b, 1)
        st.player.effect(st, 'redraw_all')
    st.set16(T, 0x7ac, saved_7ac)
    st.player.effect(st, 'sound', 0x1c)
    g = lambda off: s16(st.u16(G, off))
    stop_action(st, g(0x48c), g(0x47c), g(0x48a))
    st.set16(T, 0xc24, 1)
    set_health(st, 100)
    if found == 0:
        st.set16(G, 0x496, 2 if old_t == 0x60 else 6)
    for frame in range(2, 8):
        if found == 0:
            st.set16(G, 0x502, frame)
            put_yellow(st, g(0x48c), g(0x47c), g(0x48a), 0, st.u16(G, 0x496), 0xff)
        else:
            set_occ(st, g(0x48c), a, b, frame)
        st.player.effect(st, 'redraw')                                 # f_03391
    st.player.effect(st, 'sound', 0x31)
    if found == 0:
        put_yellow(st, g(0x48c), g(0x47c), g(0x48a), t, st.u16(G, 0x496), 0xff)
    else:
        from . import newgame
        take_yellow(st, g(0x48c), g(0x47c), g(0x48a), g(0x4c2), st.u16(G, 0x496))
        if g(0x48c) == 2:
            newgame._queen_chamber(st, nest.BLACK, g(0x47c), g(0x48a), st.u16(G, 0x496))   # f_6ba1c
            st.inc16(G, 0xaf6)
        else:
            newgame._queen_chamber(st, nest.RED, g(0x47c), g(0x48a), st.u16(G, 0x496))     # f_6bb70
            st.inc16(G, 0xb04)
        put_yellow(st, g(0x48c), a, b, t, st.u16(G, 0x496) ^ 4, 0xff)
        if st.u16(G, 0x4e2) == 0:
            st.inc16(G, 0xaee)
            st.inc16(G, 0xaf4, -1)
            st.inc16(G, 0x330)
        else:
            st.inc16(G, 0xafc)
            st.inc16(G, 0xb02, -1)
            st.inc16(G, 0x350)
    st.player.effect(st, 'redraw')
    st.player.effect(st, 'sound', 0x4e21 if found else 0x2afd)
    st.player.effect(st, 'help', 0x238d, found + 1)                    # f_7686d


# the death messages per event (f_75d01), shown when T:07AE (messages on)
EVENT_MESSAGE = {3: 0x272a, 4: 0x272c, 5: 0x2732, 6: 0x2734, 7: 0x2736, 8: 0x2738, 9: 0x273a, 10: 0x273d}
# the picture f_75d01 passes with each death's message (f_2f6ea(picture, id, 1)): the cause icons 9150..9156
EVENT_PICTURE = {5: 0x23c3, 6: 0x23c0, 7: 0x23be, 8: 0x23c2, 9: 0x23bf, 10: 0x23c4}


def player_event(st, n):
    """f_75d01 (via f_2f7d0): the yellow ant dies (n: 0 starved, 1 spider, 2 ant lion, 3..10 other deaths,
    see EVENT_MESSAGE) and the player takes over another ant: the black queen if she is gone ... (types
    1..7 in the black nest), else the last adult of the black nest, the surface, the red nest. With
    none left: Quick Game over, or in the Full Game the yard map (another colony) or game over."""
    g = lambda off: s16(st.u16(G, off))
    st.player.effect(st, 'picture', 1)                                 # f_2f802 → f_71a7d
    if st.u16(G, 0xa06) == 0 and st.u16(G, 0x4c2) & 8:                 # drop what it carries
        saved = st.u16(T, 0x7ac)
        st.set16(T, 0x7ac, 0)
        if not drop_load(st, g(0x48c), g(0x47c), g(0x48a), g(0x47c), g(0x48a)):
            t = st.u16(G, 0x4c2)
            st.set16(G, 0x4c2, (t & 0x80) | ((st.s8(T, 0x94 + ((t & 0x78) >> 3)) << 3) & 0xffff))
        st.set16(T, 0x7ac, saved)
    ui_follow(st)
    st.player.effect(st, 'redraw_all')
    if 7 <= n < 10:
        insane_animation(st, g(0x48c), g(0x47c), g(0x48a), st.u16(G, 0x496), st.u16(G, 0x4c2))
    msg = st.u16(T, 0x7ae)
    if n == 0:
        st.player.effect(st, 'sound', st.rand(5) + 0x4e27)
        if msg:
            st.player.effect(st, 'message_box', 0x272e if st.u16(G, 0x1058) else 0x2730, 1)
    elif n in (1, 2):
        if msg:
            if n == 1:                                                 # f_71f52: the spider scene
                st.player.effect(st, 'message_box', 0x2740 if st.rand(2) else 0x273f, 1)
            else:
                st.player.effect(st, 'scene', 0x1a00)                  # f_76707: the ant lion scene
        st.inc32(G, 0xf20)
        st.player.effect(st, 'sound', st.rand(5) + 0x4e27)
        fight_animation(st, g(0x48c), g(0x47c), g(0x48a), st.u16(G, 0x496), st.u16(G, 0x4c2), n)
    elif n in (3, 4):
        st.player.effect(st, 'sound', 1)                               # f_00ed8(1, 0, 0x7e)
        if msg:
            st.player.effect(st, 'message_box', EVENT_MESSAGE[n], 1)
        st.inc32(G, 0xefc)
    elif 5 <= n <= 9:
        st.player.effect(st, 'sound', st.rand(5) + 0x4e27)
        if msg:
            st.player.effect(st, 'message_box', EVENT_MESSAGE[n], 1, EVENT_PICTURE[n])
        st.inc32(G, 0xf30 if n == 8 else 0xefc)
    elif n == 10:
        st.inc32(G, 0xefc)
        fight_animation(st, g(0x48c), g(0x47c), g(0x48a), st.u16(G, 0x496), st.u16(G, 0x4c2), 10)
        if msg:
            st.player.effect(st, 'message_box', EVENT_MESSAGE[n], 1, EVENT_PICTURE[n])
    if 1 <= n <= 2:
        st.player.effect(st, 'help', 0x238c, 0)                        # f_7686d
    st.player.effect(st, 'redraw_all')                                  # f_0151c
    if st.u16(G, 0xa06) == 0:
        take_yellow(st, g(0x48c), g(0x47c), g(0x48a), g(0x4c2), st.u16(G, 0x496))
    release_recruits(st, 1)
    if st.u16(G, 0x104e):
        alarm_mode(st, 0, 1)
    found = _take_over(st)
    if found == 0:
        mode = g(0xeac)
        if mode <= 1:
            st.set16(G, 0x376, 1)
            st.set16(G, 0x366, 0)
        elif mode == 2:
            if g(0x3e2) < 2:
                st.set16(G, 0x376, 1)
                st.set16(G, 0x366, 0)
                st.player.effect(st, 'message_box', 0x2748, 1)
            else:
                st.player.effect(st, 'message_box', 0x274a, 1)
                st.player.choose_patch(st)                             # f_7650c: the yard map
        else:
            raise NotImplementedError('f_75d01: no ant left in mode 3 (reads an unset local)')
        return
    if found[0] == 1:                                                  # the queen
        if st.u16(G, 0x4c2) == 0x60:
            st.set16(G, 0x4c2, 0x10)
        queen_scene(st, g(0x48c), g(0xf0e), g(0xf26), g(0x4c2), 0)
        return
    st.set16(G, 0xa06, 0)
    t = found[1] & 0xf8
    h = st.u16(G, 0x496)
    put_yellow(st, g(0x48c), g(0xf0e), g(0xf26), t, h, t + h)
    stop_action(st, g(0x48c), g(0xf0e), g(0xf26))
    set_health(st, 100)
    ui_follow(st)
    st.player.effect(st, 'redraw_all')
    st.player.effect(st, 'message_box', 0x274b, 1)


def _take_over(st):
    """Part of f_75d01: pick the ant to become, remove it from its list and map. Returns 0, (1, t) for the
    black nest's types 1..7, or (2, t) for an adult (types 8..0x67). Each search starts one past the last
    ant (sic)."""
    lists = ((1, 0xda8, 0xbaec, 0xb50d, 0xb702, 0x8180, 2, 1, 8),
             (2, 0xda8, 0xbaec, 0xb50d, 0xb702, 0x8180, 2, 8, 0x68),
             (2, 0xd6a, 0xad3b, 0xa180, 0xa569, 0x6180, 1, 8, 0x68),
             (2, 0xeaa, 0xc4b5, 0xbed6, 0xc0cb, 0x9180, 3, 8, 0x68))
    for kind, count, tf, xf, yf, cells, view, lo, hi in lists:
        i = s16(st.u16(G, count))
        while i >= 0:
            t = st.u8(SIM, tf + i)
            if lo <= t < hi:
                y, x = st.u8(SIM, yf + i), st.u8(SIM, xf + i)
                st.set16(G, 0xf26, y)
                st.set8(SIM, tf + i, 0)
                st.set16(G, 0xf0e, x)
                st.set_grid(cells, x, y, 0)
                st.set16(G, 0x48c, view)
                return kind, t
            i -= 1
    return 0


def stop_action(st, view, a, b):
    """f_757dd (via f_2f820): the action is over; the cursor rests on the yellow ant."""
    for off in (0x48c, 0xaf8):
        st.set16(G, off, view)
    for off in (0x47c, 0xab6, 0xad6):
        st.set16(G, off, a)
    for off in (0x48a, 0xac6, 0xae8):
        st.set16(G, off, b)
    for off in (0xa8e, 0xaa0, 0xb1e, 0xc38, 0xc3e):
        st.set16(G, off, 0)
    st.set16(G, 0xd6c, 0xfffe)


def attack_player(st, view, i):
    """AttackPlayer f_7c5ab: the yellow ant fights ant i of the view's list."""
    f = _ants(view)
    t = st.u8(SIM, f['type'] + i)
    x, y = st.u8(SIM, f['x'] + i), st.u8(SIM, f['y'] + i)
    clear_occ_if(st, view, x, y, t)
    from .surface import resolve_fight, place_corpse
    w = resolve_fight(st, st.u16(G, 0x4c2), st.u8(SIM, f['type'] + i))
    if st.u16(G, 0x4c2) != w:
        ui_follow(st)
    ya, yb = s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    fight_animation(st, s16(st.u16(G, 0x48c)), ya, yb, st.u16(G, 0x496), 0x70, 0)
    if st.u16(G, 0x4c2) == w:                                          # the yellow ant wins
        put_yellow(st, s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)),
                   s16(st.u16(G, 0x4c2)), st.u16(G, 0x496), 0xff)
        if view <= 1:
            place_corpse(st, st.u8(SIM, f['x'] + i), st.u8(SIM, f['y'] + i), st.u8(SIM, f['type'] + i) & 0x80)
        st.set8(SIM, f['type'] + i, 0)
        if (st.u16(G, 0xa8e) == 3 and st.u16(G, 0x48c) == st.u16(G, 0x8da)
                and st.u16(G, 0x7c0) == i & 0xffff):
            stop_action(st, s16(st.u16(G, 0x48c)), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)))
        return
    set_occ(st, view, st.u8(SIM, f['x'] + i), st.u8(SIM, f['y'] + i), st.u8(SIM, f['type'] + i))
    if view <= 1:
        place_corpse(st, s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a)), st.u16(G, 0x4e2))
    st.player.game_event(st, 0)                                         # the yellow ant dies


# ------------------------------------------------------------------------------------------- the action
def player_action(st):
    """f_7b7b8 (each tick while an action is pending, G:0AA0): walk one step towards the cursor (or the
    target ant), act on the target cell, enter / leave / switch nests; when the action ends: fight or
    talk to the target ant, then stop_action."""
    if st.u16(G, 0xaa0) == 0:
        return
    g = lambda off: s16(st.u16(G, off))
    res = 0
    mode = g(0xa8e)
    ant = None
    done = False
    if mode >= 3:
        ant = get_ant(st, g(0x8da), g(0x7c0))
        if ant is None or (st.u8(G, 0x84e) ^ ant[2]) & 0xf0:
            res, done = -2, True                                       # the target ant is gone
        elif g(0x48c) == g(0x8da) and abs(g(0x47c) - ant[0]) <= 1 and abs(g(0x48a) - ant[1]) <= 1:
            d = mv.dir_to(g(0x47c), g(0x48a), ant[0], ant[1]) - 1        # next to it: face it
            if d >= 0:
                st.set16(G, 0x496, d)
            st.player.effect(st, 'redraw_all')                          # f_03391
            res, done = -1, True
        else:                                                          # the cursor follows it
            for off, v in ((0x8e2, ant[0]), (0xad6, ant[0]), (0x9f0, ant[1]), (0xae8, ant[1])):
                st.set16(G, off, v)
    if not done and g(0xa8e) == 1 and g(0xaf8) == g(0x48c):
        d = mv.dir_to(g(0x47c), g(0x48a), g(0xad6), g(0xae8))
        ca = st.s8(T, 0x10 + d) + g(0x47c)
        cb = st.s8(T, 0x1a + d) + g(0x48a)
        if not 0 <= ca <= 0x7f:
            ca = g(0x47c)
        if not 0 <= cb <= 0x3f:
            cb = g(0x48a)
        if g(0xad6) == ca and g(0xae8) == cb:                          # the target cell is next to it
            r = act_on_cell(st, g(0x48c), ca, cb)
            if r:
                res, done = (-1 if r == 1 else -2), True
    if not done:
        res, done = _step(st)
    if st.u16(T, 0x7a8):
        ui_follow(st)
    if (res == 0 and g(0xaf8) == g(0x48c) and g(0xad6) == g(0x47c) and g(0xae8) == g(0x48a)
            and g(0xa8e) == 0):
        res = -1                                                       # arrived
    if res == 0:
        return
    if res == -2:
        st.player.effect(st, 'sound', 1)
        ui_follow(st)
    elif g(0xa8e) == 3:
        st.set16(G, 0x1058, 1)
        attack_player(st, g(0x8da), g(0x7c0))
        st.set16(G, 0x1058, 0)
    elif g(0xa8e) == 4:
        x, y, t, state, e = ant
        d = mv.dir_to(x, y, g(0x47c), g(0x48a)) - 1
        if d >= 0 and t & 0x70 != 0x60:                                # the ant turns to face the yellow one
            t = (t & 0xf8) | d
            set_ant(st, g(0x48c), g(0x7c0), x, y, t, state, e)
            set_occ(st, g(0x48c), x, y, t)
            st.player.effect(st, 'redraw_all')
        eat(st, 1)                                                      # MenuCommand12de1(1)
    stop_action(st, g(0x48c), g(0x47c), g(0x48a))                      # f_2f820
    if st.u16(G, 0xf24) and g(0x48c) == 1:                             # on the house's 0x76 / 0x78 tiles
        o = ((st.u16(G, 0x47c) << 6) + st.u16(G, 0x48a)) & 0xffff
        if st.u8(SIM, SURFACE + o) in (0x76, 0x78):
            st.player.game_event(st, 10)


def _step(st):
    """The walking part of f_7b7b8: (res, done)."""
    g = lambda off: s16(st.u16(G, off))
    view = g(0x48c)
    d = step_to_cursor(st, view, g(0x47c), g(0x48a), g(0xaf8), g(0xad6), g(0xae8))
    if d < 0:
        return d, True
    nb = st.s8(T, 8 + d) + g(0x48a)
    st.set16(G, 0xab6, g(0x47c))
    st.set16(G, 0xac6, g(0x48a))
    na = g(0x47c) + st.s8(T, d)
    move_yellow(st, view, na, nb, g(0x4c2), d)
    st.inc16(G, 0xc3e)
    t = g(0x4c2)
    if view == 1:
        if g(0x4c4) > 0 and t in (0x18, 0x38):                         # carrying food: lay the trail
            ph.lay_max(st, ph.BLACK_TRAIL if st.u16(G, 0x4e2) == 0 else ph.RED_TRAIL, g(0x47c), g(0x48a),
                       st.u16(G, 0x4c4))
            if g(0x4c4) > 10:
                st.inc16(G, 0x4c4, -1)
        if st.u16(G, 0x104e):
            alarm_add(st, g(0x47c), g(0x48a), 0x32)
    else:
        ng.update_exit_field(st, ng.BLACK if view == 2 else ng.RED, g(0x47c), g(0x48a))
    if st.u8(G, 0xc3e) & 1:
        if t == 0x40 and st.u16(T, 0xc24) == 0 and g(0x10be) > 0 and st.u16(T, 0xc18) == 0:
            st.inc16(G, 0x10be, -1)
        set_health(st, _hp(st) - 1)
    if g(0x48c) == 1:
        if not mv.at_nest_entrance(st, g(0x47c), g(0x48a)):
            return 0, True
        if not (g(0xaf8) > 1 or (g(0xaf8) == g(0x48c) and g(0xad6) == g(0x47c) and g(0xae8) == g(0x48a))):
            return 0, True
        st.player.effect(st, 'redraw_all')                              # f_11ab0
        old = g(0x48c)
        enter_nest(st)
        return _after_switch(st, old, na, nb)
    if g(0x48a) == 0:
        st.player.effect(st, 'redraw_all')
        old = g(0x48c)
        leave_nest(st)
        return _after_switch(st, old, na, nb)
    if (get_tile(st, g(0x48c), g(0xad6), g(0xae8)) == 0x14 and t != 0x60
            and g(0xad6) == g(0x47c) and g(0xae8) == g(0x48a)):           # through the hole into the other nest
        take_yellow(st, g(0x48c), g(0x47c), g(0x48a), t, st.u16(G, 0x496))
        st.set16(G, 0x48c, 3 if g(0x48c) == 2 else 2)
        put_yellow(st, g(0x48c), g(0x47c), g(0x48a), t, st.u16(G, 0x496), 0xff)
        st.player.effect(st, 'sound', 1)
        ui_follow(st)
        if g(0x48c) == 3:
            st.player.effect(st, 'status', 'red nest')                  # f_15e2c
        return -1, True
    return 0, True


def _after_switch(st, old_view, na, nb):
    """L_bc43: after entering or leaving a nest the walk goes on, unless the cursor was on the entrance
    cell just stepped onto (and the new view is not the one shown, G:032E)."""
    g = lambda off: s16(st.u16(G, off))
    if not (g(0xaf8) == old_view and g(0xad6) == na and g(0xae8) == nb):
        return 0, True
    if g(0x48c) == g(0x32e):
        return 0, True
    if st.u16(T, 0x7a8) == 0:
        ui_follow(st)
    return -1, True


def alarm_add(st, a, b, n):
    """f_14cad: alarm scent += n (max 200)."""
    i = (s16(a) >> 1) * 32 + (s16(b) >> 1)
    v = st.u8(SIM, 0xd09f + i) + n
    st.set8(SIM, 0xd09f + i, min(v, 200))


def nudge(st, a, b, d):
    """f_769c5 (also via f_2f7bc): an ant at (a, b) bumps the yellow ant along heading d; it turns to face
    the ant (and MenuCommand12de1(1) runs)."""
    na, nb = a + st.s8(T, d), b + st.s8(T, 8 + d)
    h = mv.dir_to(na, nb, a, b) - 1
    move_yellow(st, s16(st.u16(G, 0x48c)), na, nb, s16(st.u16(G, 0x4c2)), h)
    st.player.effect(st, 'redraw_all')
    eat(st, 1)


class Hooks(surface.NoPlayer):
    """The player hooks the simulation calls, routed to the ports. What is left to a UI: effect (screen
    only), choose_patch (the yard map: the player picks a patch, then the UI calls newgame.move_to_patch),
    new_game_dialog (pick the next game: game.start_game), sound_done (the sound driver, only with sound
    hardware). The win screen (f_2f91a → f_72750) changes no game state."""

    def game_event(self, st, n):
        player_event(st, n)

    def game_over(self, st):
        from . import game
        return game.game_over_screen(st)

    def win_screen(self, st):
        self.effect(st, 'win_screen')

    def new_game_dialog(self, st):
        self.effect(st, 'new_game_dialog')

    def choose_patch(self, st):
        self.effect(st, 'yard_map')

    def sound_done(self, st):
        return True

    def attack_player(self, st, view, ant):
        attack_player(st, view, ant)

    def nudge_player(self, st, a, b, d):
        nudge(st, a, b, d)

    def nest_follow(self, st, col, depth, d):
        nudge(st, col, depth, d)

    def spider_eats_player(self, st, a, b):
        move_yellow(st, s16(st.u16(G, 0x48c)), a, b, s16(st.u16(G, 0x4c2)), st.u16(G, 0x496))
        self.game_event(st, 1)

    def lion_eats_player(self, st, a, b):
        move_yellow(st, 1, a, b, s16(st.u16(G, 0x4c2)), st.u16(G, 0x496))
        self.game_event(st, 2)

    def spider_event(self, st, n):
        self.game_event(st, n)

    def yard_event(self, st, n):
        self.game_event(st, n)


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
