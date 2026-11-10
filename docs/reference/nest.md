---
layout: default
title: "Black nest ants"
permalink: /reference/nest/
---

# Black nest ants

*`nest.py` — The nest tick, state handlers, digging, brood and the queen.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `nest.py`]({{ site.baseurl }}/assets/reference/simant_ref/nest.py)

The black colony's per-tick loop and state handlers (overlay section 27, segment `899e`, with helpers in `0be8`, `0ec1`, `14ee`): wandering, nesting, carrying food, digging in, going to the surface, brood care, egg laying, fighting, resting, invader handling, plus the queen's movement and the abdomen/head/tail loss rules.

- Nest ants live in the `b_*` arrays and each one's type byte is also written into the contents grid at its cell — two representations that must never disagree.
- The exit field counts *up* toward an opening, which inverts the intuition from the surface: a high value near the entrance is an exit being dug, not a wall.
- Egg cost, food storage and eating are all bookkeeping on the dirt grid, which is why a nest can starve with food on the map.

## At a glance

- **821** lines
- **50 top-level functions**, including `_cur`, `_get`, `_set`, `_job`, `_visible`, `nest_ant_at`, `nest_cell_free`, `step_dir` …
- **Original routines referenced:** `f_0c8db`, `f_0c93e`, `f_0ca41`, `f_0ca8f`, `f_0cbe7`, `f_0eeed`, `f_0ef3c`, `f_0fda0`, `f_103b9`, `f_10667`, `f_10720`, `f_107c7` …

## Source

{% raw %}
```python
"""Black nest ants: the per-tick loop, state handlers and helpers (SIMANT.EXE overlay section 27, segment
899e, plus nest helpers in segments 0be8, 0ec1 and 14ee).

Nest ants live in the b_* arrays (count G:0da8); each one's type byte is also written into the nest
contents grid (0x8180) at its cell. The dirt grid (0x2180) holds tunnels, stored food and dirt; the exit
field (0x4180) counts up towards the entrance. Red ants in the black nest are invaders and run their own
branch of the tick. Player (yellow ant) interactions call st.player hooks (see surface.NoPlayer).
"""
from .state import SIM, G, T
from . import movement as mv
from . import nestgrid as ng
from . import surface as sf

# colony constants for the helpers shared by both nests (the red nest handlers are in red_nest.py)
BLACK = dict(ng.BLACK, view=2, red=0, health=0x10be, food=0x1050, acc=0x212, pop=0x330, soldiers=0xaf0,
             entr=0x224, entr_xy=0x2ac, entr_col=0x2a4, hole_row=lambda k, i: (k + i) % 0x20 + 2)
RED = dict(ng.RED, view=3, red=0x80, health=0x1fe, food=0x1060, acc=0x226, pop=0x350, soldiers=0xafe,
           entr=0x264, entr_xy=0x2b0, entr_col=0x2a8, hole_row=lambda k, i: 0x7e - (k + i) % 0x20)
N = BLACK
DIRT, EXITF, CELLS = N['dirt'], N['exitf'], N['cells']
BX, BY, BSTATE, BTYPE, BE = N['x'], N['y'], N['state'], N['type'], N['e']
s16 = mv.s16


def _cur(st):
    return st.u16(G, 0xf18)


def _get(st, f, i):
    return st.u8(SIM, f + i)


def _set(st, f, i, v):
    st.set8(SIM, f + i, v)


def _job(st, caste):
    """f_141cb: StateForCaste for a black ant."""
    return mv.state_for_caste(st, caste, 0)


def _visible(st):
    return st.u16(T, 0x7b2)


# ------------------------------------------------------------------------------------------- lookups
def nest_ant_at(st, n, col, depth, t):
    """f_0eeed (black) / f_0ef3c (red): index of the nest ant at (col, depth) with type t, searching from the
    top; -1 if none."""
    i = s16(st.u16(G, n['count']))
    while i > 0:
        i -= 1
        if _get(st, n['x'], i) == col and _get(st, n['y'], i) == depth and _get(st, n['type'], i) == t:
            return i
    return -1


def nest_cell_free(col, depth):
    """f_0ca41: inside the nest below the top row."""
    return 0 <= col <= 0x3f and 1 <= depth <= 0x3f


def step_dir(st, n, col, depth, d):
    """f_0cbe7 NestStepDir: neighbour (not straight back) with the smallest nonzero exit-field value <= the
    current one, ties 50/50 - i.e. go deeper. -1 at a dead end."""
    best, cur = -1, st.grid(n['exitf'], col, depth)
    for i in range(8):
        if (d ^ 4) == i:
            continue
        c, r = col + mv.dx(st, i), depth + mv.dy(st, i)
        if not (0 <= c < 0x40 and 0 <= r < 0x40):
            continue
        v = st.grid(n['exitf'], c, r)
        if v == 0 or v > cur:
            continue
        if v >= cur and st.rand2() == 0:
            continue
        best, cur = i, v
    return best


def climb_dir(st, n, col, depth, d):
    """f_0ca8f NestClimbDir: 1 + direction of the highest exit-field neighbour (not straight back), 0 if none.
    At depth 1 it heads up the shaft if there is one, else sideways."""
    if depth == 1:
        if st.grid(n['dirt'], col, 0) == 0x18:
            return 1
        return st.rand2() * 4 + 3
    best, bv = 0, 0
    for i in range(8):
        c, r = col + mv.dx(st, i), depth + mv.dy(st, i)
        if 0 <= c < 0x40 and 0 <= r < 0x40:
            v = st.grid(n['exitf'], c, r)
            if bv < v and (d ^ 4) != i:
                best, bv = i + 1, v
    return best


def _nest_tile(st, n, c, r):
    """GetTile(view, c, r): -1 outside the nest."""
    return st.grid(n['dirt'], c, r) if 0 <= c < 0x40 and 0 <= r < 0x40 else -1


def _nest_open(st, n, c, r):
    """IsOpenGround(view, c, r) (f_1145c): open tunnel (< 8) and no occupant other than the yellow ant."""
    t = _nest_tile(st, n, c, r)
    if t < 0:
        return False
    o = st.grid(n['cells'], c, r)
    if o and not mv.is_yellow(o):
        return False
    return t < 8


def step_towards_nest(st, n, col, depth, tc, tr):
    """f_7a69d (view 2 black / 3 red): like surface.step_towards_surface, inside a nest."""
    dist = mv.distance_lo(col, depth, tc, tr)
    if dist <= 0:
        return -1
    res, fallback = -1, -2
    for d in range(8):
        c, r = col + mv.dx(st, d), depth + mv.dy(st, d)
        t = _nest_tile(st, n, c, r)
        if t < 0 or not (t < 0x19 or 0x30 <= t <= 0x31):          # f_133f9
            continue
        if 0x30 <= t <= 0x31:                                     # f_116a1
            continue
        nd = mv.distance_lo(c, r, tc, tr)
        if nd >= dist:
            continue
        dist = nd
        if st.grid(n['cells'], c, r) == 0 and _nest_open(st, n, c, r):
            res = d
        else:
            fallback = d
    return res if res >= 0 else fallback


# ------------------------------------------------------------------------------------------- terrain
def is_open_with_ring(st, a, b):
    """f_113fe(view 1): the surface cell and all 8 neighbours are open ground."""
    if not sf._is_open_ground(st, a, b):
        return False
    return all(sf._is_open_ground(st, a + mv.dx(st, d), b + mv.dy(st, d)) for d in range(8))


def entrance_ring(st, a, b):
    """f_15395: draw the ring of entrance tiles (DS:1bb2) around a new yard entrance."""
    for d in range(8):
        na, nb = a + mv.dx(st, d), b + mv.dy(st, d)
        if 0 <= na <= 0x7f and 0 <= nb <= 0x3f and st.grid(sf.SURFACE, na, nb) < 0x50:
            st.set_grid(sf.SURFACE, na, nb, st.u8(0x55b3, 0x1bb2 + d))


def house_entrance_tile(t):
    """f_151f7: the entrance version of a house floor tile, 0 if there is none."""
    if t == 0:
        return 0x86
    if t in (2, 3):
        return 0x8a
    if 0x5d < t:
        if t < 0x62:
            return t + 0x22
        if t == 0x66:
            return 0x85
        if t == 0x68:
            return 0x84
    return 0


def make_surface_hole(st, n, col):
    """f_150b0 MakeSurfaceHoleBlack / f_15247 (red): open an entrance on the surface above nest column `col`
    (black tries surface rows 2..33, red 126..95)."""
    k = st.rand(0x1f)
    found = None
    for i in range(0x22):
        a = n['hole_row'](k, i)
        if st.u16(G, 0xf24) == 0:
            if is_open_with_ring(st, a, col):
                st.set_grid(sf.SURFACE, a, col, 0x50)
                found = a
        else:
            v = house_entrance_tile(st.grid(sf.SURFACE, a, col))
            if v:
                st.set_grid(sf.SURFACE, a, col, v)
                found = a
        if found is not None:
            st.set16(T, n['entr_xy'], a)
            st.set16(T, n['entr_xy'] + 2, col)
            st.set16(T, n['entr_col'], col)
            st.set16(T, n['entr_col'] + 2, 0)
            if st.u16(G, 0xf24) == 0:
                entrance_ring(st, a, col)
            break
    if found is not None:
        st.set8(T, n['entr'] + col, found)
        ng.dig_at(st, n, col, 1)


def dig_cell(st, n, col, depth):
    """f_15623 DigCellBlack / f_1577e (red): dig exposed dirt; tunnels stay one cell thick. True if dug."""
    dirt = n['dirt']
    if ((depth < 0x3f and not ng.is_diggable(st.grid(dirt, col, depth + 1)))
            or (depth > 2 and not ng.is_diggable(st.grid(dirt, col, depth - 1)))
            or col == 0 or col > 0x3e):
        return False
    if depth == 0:
        st.set_grid(dirt, col, 0, 0x18)
        make_surface_hole(st, n, col)
    else:
        st.set_grid(dirt, col, depth, st.rand8())
    ng._dig_bookkeeping(st, n, col, depth)
    ng.reclassify_dirt(st, n, col, depth - 1)
    ng.reclassify_dirt(st, n, col + 1, depth)
    ng.reclassify_dirt(st, n, col, depth + 1)
    ng.reclassify_dirt(st, n, col - 1, depth)
    ng.update_exit_field(st, n, col, depth)
    return True


def spawn_brood(st, n, col, depth, stage):
    """f_0c8db SpawnBlackBrood / f_0c93e SpawnRedBrood."""
    if s16(st.u16(G, n['count'])) < 500 and nest_cell_free(col, depth):
        ng.dig_at(st, n, col, depth)
        ng.add_nest_ant(st, n, col, depth, stage, 8, 0)
        st.set_grid(n['cells'], col, depth, stage)


# ------------------------------------------------------------------------------------------- food
def _eat_core(st, n, col, depth, health_gain):
    v = st.grid(n['dirt'], col, depth)
    st.set_grid(n['dirt'], col, depth, st.rand8() if v == 0x10 else v - 1)
    if s16(st.u16(G, n['food'])) > 0:
        st.inc16(G, n['food'], -1)
    if not health_gain:
        return
    lim = s16(st.u16(G, n['soldiers']) + st.u16(G, n['pop'])) >> 4
    st.inc16(G, n['acc'], 5)
    if lim < s16(st.u16(G, n['acc'])):
        st.set16(G, n['acc'], 0)
        if s16(st.u16(G, n['health'])) < 100:
            st.inc16(G, n['health'])


def eat_food(st, n, col, depth):
    """f_7ae88 EatFoodBlack / f_10720 (red)."""
    _eat_core(st, n, col, depth, True)


def eat_if_on_food(st, n, col, depth):
    """f_7adcf EatIfOnFoodBlack / f_10667 (red)."""
    if 0x10 <= st.grid(n['dirt'], col, depth) <= 0x13:
        _eat_core(st, n, col, depth, True)


def invader_eat_food(st, n, col, depth):
    """f_7af2f / f_107c7: an invader eats the other colony's stores (no health gain)."""
    _eat_core(st, n, col, depth, False)


def store_food(st, n, col, depth):
    """f_7a2ea StoreFoodBlack / f_0fda0 (red): the carrier drops its food here (counted even when full)."""
    v = st.grid(n['dirt'], col, depth)
    ok = 1
    if v < 0x10:
        st.set_grid(n['dirt'], col, depth, 0x10)
    elif v > 0x12:
        ok = 0
    else:
        st.set_grid(n['dirt'], col, depth, v + 1)
    st.inc16(G, n['food'])
    cur = _cur(st)
    if _get(st, n['type'], cur) & 8:
        _set(st, n['type'], cur, _get(st, n['type'], cur) - 8)
    return ok


def egg_cost(st):
    """f_7af94."""
    st.inc16(G, 0x212, -1)
    if s16(st.u16(G, 0x212)) < 0:
        st.set16(G, 0x212, s16(st.u16(G, 0x330)) >> 5)
        if s16(st.u16(G, 0x10be)) > 0 and st.u16(T, 0xc18) == 0:
            st.inc16(G, 0x10be, -1)


# ------------------------------------------------------------------------------------------- moving
def exit_to_surface(st, n, col):
    """f_7b661 (black) / f_10e27 (red): an ant at the top of the nest tries to leave through the shaft in
    its column."""
    cur = _cur(st)
    dirt, ty = n['dirt'], n['type']
    if st.grid(dirt, col, 0) == 0x18:
        t = _get(st, ty, cur)
        _set(st, ty, cur, 0)
        if st.u8(T, n['entr'] + col) == 0:
            make_surface_hole(st, n, col)
        e, state = _get(st, n['e'], cur), _get(st, n['state'], cur)
        nt = (st.rand8() + (t & 0xf8)) & 0xff
        if sf.add_surface_ant(st, st.u8(T, n['entr'] + col), col, nt, state, e):
            st.set_grid(n['cells'], col, 1, 0)
            return 1
        _set(st, ty, cur, t)
        _set(st, n['state'], cur, 0)
        return 0
    v = st.grid(n['exitf'], col, 0)
    if v:
        st.set_grid(n['exitf'], col, 0, v - 1)
    if st.rand2():
        if col > 0 and ng.is_diggable(st.grid(dirt, col - 1, 1)):
            dig_cell(st, n, col - 1, 1)
    elif col < 0x3f and ng.is_diggable(st.grid(dirt, col + 1, 1)):
        dig_cell(st, n, col + 1, 1)
    move_to(st, n, col, 1, st.rand8())
    return 0


def move_to(st, n, col, depth, d):
    """f_7aa3b NestMoveTo (black) / f_103b9 (red): step the current ant into a passable cell (dirt < 0x1c),
    overwriting whatever the contents grid held there. Stepping above row 1 leaves the nest. 1 if moved."""
    d = s16(d)
    if d < 0:
        return 0
    c, r = col + mv.dx(st, d), depth + mv.dy(st, d)
    if not (0 <= c < 0x40 and r < 0x40):
        return 0
    if r < 1:
        return exit_to_surface(st, n, col)
    if st.grid(n['dirt'], c, r) >= 0x1c:
        return 0
    cur = _cur(st)
    cells, ty = n['cells'], n['type']
    if (not n['red'] and st.grid(cells, c, r) == 0xff and st.u16(G, 0x1044) != 0
            and _get(st, n['x'], cur) < 0x80):
        st.set_grid(cells, col, depth, (_get(st, ty, cur) & 0xf8) | d)
        st.player.nest_follow(st, col, depth, d)                         # f_2f7bc
    v = (_get(st, ty, cur) & 0xf8) | d
    st.set_grid(cells, c, r, v)
    st.set_grid(cells, col, depth, 0)
    _set(st, n['x'], cur, c)
    _set(st, n['y'], cur, r)
    _set(st, ty, cur, v)
    return 1


def fight_at(st, col, depth, t):
    """f_7a233 NestFightAt: fight a red ant (or the red-side yellow ant) in this cell. Returns 1 if so."""
    o = st.grid(CELLS, col, depth)
    if mv.is_yellow(o) and st.u16(G, 0x4e2) != 0:
        st.player.attack_player(st, 2, _cur(st))
        return 1
    if 0x87 < o < 0xe8:
        i = nest_ant_at(st, N, col, depth, o)
        if i >= 0:
            w = sf.resolve_fight(st, o, t & 0xff)
            _set(st, BE, i, w)
            nt = ((w & 0x80) + 0x70) & 0xff
            _set(st, BTYPE, i, nt)
            st.set_grid(CELLS, col, depth, nt)
            _set(st, BSTATE, i, 10)
            return 1
    return 0


def _enter(st, col, depth, c, r, d, nt):
    """The common 'step into a free tunnel cell' of Got Food / Dig In / Go To Surface. False = fought."""
    st.set_grid(CELLS, col, depth, 0)
    o = st.grid(CELLS, c, r)
    if o & 0x80 and (not mv.is_yellow(o) or st.u16(G, 0x4e2) != 0) and fight_at(st, c, r, nt):
        return False
    cur = _cur(st)
    v = (_get(st, BTYPE, cur) & 0xf8) | d
    _set(st, BTYPE, cur, v)
    st.set_grid(CELLS, c, r, v)
    _set(st, BX, cur, c)
    _set(st, BY, cur, r)
    return True


def _turn_to(st, n, col, depth, t, d):
    nt = (t & 0xf8) | d
    st.set_grid(n['cells'], col, depth, nt)
    _set(st, n['type'], _cur(st), nt)
    return nt


# ------------------------------------------------------------------------------------------- queen
def queen_move(st, col, depth, t):
    """f_7a78f QueenMove: the head walks towards the nest centroid and drags the abdomen after it."""
    d = step_towards_nest(st, N, col, depth, s16(st.u16(G, 0x10b2)), s16(st.u16(G, 0x10c0)))
    if d < 0:
        if d == -1:
            return 0
        d = st.rand8()
    if (depth > 2 or 2 < d < 6) and move_to(st, N, col, depth, d):
        back = (t ^ 0xfc) & 7
        c, r = mv.dx(st, back) + col, mv.dy(st, back) + depth
        st.set_grid(CELLS, c, r, 0)
        i = nest_ant_at(st, N, c, r, (t & 7) + 0x68)
        if i >= 0 and _get(st, BTYPE, i):
            _set(st, BX, i, col)
            _set(st, BY, i, depth)
            _set(st, BTYPE, i, d + 0x68)
            st.set_grid(CELLS, col, depth, d + 0x68)
        return 1
    return 0


def queen_head_lost(st, col, depth, t):
    """f_7a9c7: the abdomen sees no head behind... (cell behind != t+8 and no such ant there)."""
    back = (t ^ 0xfc) & 7
    c, r = mv.dx(st, back) + col, mv.dy(st, back) + depth
    return st.grid(CELLS, c, r) != t + 8 and nest_ant_at(st, N, c, r, t + 8) < 0


def queen_tail_lost(st, col, depth, t):
    """f_7a956: the abdomen's head (cell in front, type t-8) is gone."""
    c, r = mv.dx(st, t & 7) + col, mv.dy(st, t & 7) + depth
    return st.grid(CELLS, c, r) != t - 8 and nest_ant_at(st, N, c, r, t - 8) < 0


def add_abdomen(st, i):
    """f_7a8a2: a caste-12 fight winner gets its abdomen back (as an Egg Laying caste-13 ant behind it)."""
    t = _get(st, BTYPE, i)
    back = (t & 7) ^ 4
    ng.add_nest_ant(st, N, mv.dx(st, back) + _get(st, BX, i), mv.dy(st, back) + _get(st, BY, i),
                    (t + 8) & 0xff, 9, 0)


def remove_ant(st, i):
    """f_7a910: remove ant i and clear its cell."""
    _set(st, BTYPE, i, 0)
    st.set_grid(CELLS, _get(st, BX, i), _get(st, BY, i), 0)


# ------------------------------------------------------------------------------------------- handlers
def _move_or_random(st, n, col, depth, d):
    if not move_to(st, n, col, depth, d):
        move_to(st, n, col, depth, st.rand8())


def n_wander(st, col, depth, t, caste):
    """f_7a057 (Bored, Pre-Flight and states > 17)."""
    if st.rand32() == 0:
        _set(st, BSTATE, _cur(st), _job(st, caste))
    if fight_at(st, col, depth, t) != 1:
        _move_or_random(st, N, col, depth, t & 7)


def n_nesting(st, col, depth, t, caste):
    """f_7ab6e: nurses carry brood (caste 1 = worker carrying, stage in b_e low bits, bit 3 = direction)."""
    cur = _cur(st)
    d = t & 7
    stage = _get(st, BE, cur) & 7
    here = st.grid(CELLS, col, depth)
    up = _get(st, BE, cur) >> 3
    if caste == 1:
        if up == 0:
            d = step_dir(st, N, col, depth, d)
            if d < 0:
                _set(st, BE, cur, stage | 8)
            _move_or_random(st, N, col, depth, d)
            return
        if here == 0 or here > 8:
            _set(st, BTYPE, cur, _get(st, BTYPE, cur) + 8)
            spawn_brood(st, N, col, depth, stage)
            st.set_grid(CELLS, col, depth, _get(st, BTYPE, cur))
            _set(st, BE, cur, 8)
            _set(st, BSTATE, cur, _job(st, 1))
        c = climb_dir(st, N, col, depth, d)
    elif caste == 2:
        if up == 0:
            if here == 0 or here > 7:
                if s16(st.rand(100)) > s16(st.u16(G, 0x10be)):
                    eat_if_on_food(st, N, col, depth)
                elif st.rand16() == 0:
                    _set(st, BSTATE, cur, _job(st, 2))
            else:
                i = nest_ant_at(st, N, col, depth, here)
                if i >= 0:
                    _set(st, BTYPE, i, 0)
                    _set(st, BTYPE, cur, _get(st, BTYPE, cur) - 8)
                    _set(st, BE, cur, here)
                    return
            _move_or_random(st, N, col, depth, d)
            return
        if st.rand8() == 0:
            _set(st, BE, cur, 0)
        c = climb_dir(st, N, col, depth, d)
    else:
        if s16(st.rand(100)) > s16(st.u16(G, 0x10be)):
            eat_if_on_food(st, N, col, depth)
        if st.rand8() == 0:
            _set(st, BSTATE, cur, _job(st, caste))
        _move_or_random(st, N, col, depth, d)
        return
    d = st.rand8() if c == 0 else c - 1
    _move_or_random(st, N, col, depth, d)


def n_got_food(st, col, depth, t):
    """f_7afdc: carry food deeper; store it with 1/16 chance or at a dead end, maybe eat, then a new job."""
    d = step_dir(st, N, col, depth, t & 7)
    if d < 0 or st.rand16() == 0:
        store_food(st, N, col, depth)
        if s16(st.rand(100)) > s16(st.u16(G, 0x10be)):
            eat_food(st, N, col, depth)
        _set(st, BSTATE, _cur(st), _job(st, (t & 0x78) >> 3))
        return
    nt = _turn_to(st, N, col, depth, t, d)
    c, r = col + mv.dx(st, d), depth + mv.dy(st, d)
    if c > 0x3f or c < 0 or r > 0x3f:
        return
    if r < 1:
        exit_to_surface(st, N, col)
        return
    if st.grid(DIRT, c, r) >= 0x30:
        return
    _enter(st, col, depth, c, r, d, nt)


def n_dig_in(st, col, depth, t, caste):
    """f_7b197: workers/soldiers walk deeper and dig the first exposed dirt they face."""
    cur = _cur(st)
    if caste not in (2, 6):
        _set(st, BSTATE, cur, _job(st, caste))
        return
    d = step_dir(st, N, col, depth, t & 7)
    if d < 0:
        d = st.rand8()
    nt = _turn_to(st, N, col, depth, t, d)
    if depth != 0x3f:
        r, c = depth + mv.dy(st, d), col + mv.dx(st, d)
        if c > 0x3f or c < 0 or r > 0x3f:
            return
        if r < 1:
            exit_to_surface(st, N, col)
            return
        tile = st.grid(DIRT, c, r)
        if tile > 0x2f:
            return
        if ng.is_diggable(tile):
            if not dig_cell(st, N, c, r):
                _set(st, BSTATE, cur, _job(st, caste))
                return
            _set(st, BTYPE, cur, _get(st, BTYPE, cur) + 0x18)            # now carrying dirt
            _set(st, BSTATE, cur, 5)
            st.player.effect(st, 'sound', 0x11)
        if not _enter(st, col, depth, c, r, d, nt):
            return
        if s16(st.rand64()) > s16(st.u16(G, 0x10be)):
            eat_if_on_food(st, N, c, r)
        if st.rand4() == 0:
            ng.update_exit_field(st, N, c, r)
        return
    _set(st, BSTATE, cur, _job(st, caste))


def n_go_to_surface(st, col, depth, t):
    """f_7b3ac: every outdoor job climbs the exit field and leaves; at a dead end diggers start digging."""
    c1 = climb_dir(st, N, col, depth, t & 7)
    d = mv.turn_aside(st, t & 7) if c1 < 1 else c1 - 1
    nt = _turn_to(st, N, col, depth, t, d)
    c, r = col + mv.dx(st, d), depth + mv.dy(st, d)
    if not (0 <= c < 0x40 and r < 0x40):
        return
    if r < 1:
        exit_to_surface(st, N, col)
        return
    tile = st.grid(DIRT, c, r)
    if tile < 0x30:
        if not ng.is_diggable(tile) and _enter(st, col, depth, c, r, d, nt):
            if s16(st.rand64()) > s16(st.u16(G, 0x10be)):
                eat_if_on_food(st, N, c, r)
        return
    st.set_grid(EXITF, col, depth, st.grid(EXITF, col, depth) - 1)
    caste = (t & 0x78) >> 3
    cur = _cur(st)
    if caste in (5, 9):
        _set(st, BTYPE, cur, _get(st, BTYPE, cur) - 0x18)
        _set(st, BSTATE, cur, 4)
    if caste in (2, 6):
        _set(st, BSTATE, cur, 4)


def n_defense(st, col, depth, t):
    """f_7a0c2: guards stay while the player watches the black nest, else go out."""
    if st.u16(G, 0x48c) == 2:
        if fight_at(st, col, depth, t) != 1:
            _move_or_random(st, N, col, depth, t & 7)
    else:
        n_go_to_surface(st, col, depth, t)


def n_brood(st, col, depth):
    """f_7a360: brood advance one stage every 128 ticks (32 when the colony is tiny) and hatch after 8."""
    cur = _cur(st)
    t = _get(st, BTYPE, cur)
    caste = -1
    mask = 0x1f if s16(st.u16(G, 0x330)) < 3 else 0x7f
    if st.u16(G, 0xf08) & mask == 0:
        t = (t + 1) & 0xff
        if t & 0xf == 8:
            if st.u16(G, 0x378) == 0 and (st.u16(G, 0x4a2) >> 7) < s16(st.rand_low(0xff)):
                t = 0
                st.inc32(G, 0x1000)
            else:
                caste = s16(st.u16(T, 0xc0e))
                t = (caste * 8 + 2) & 0xff
                _set(st, BSTATE, cur, 1 if caste == 2 else _job(st, caste))
    if _visible(st) and caste < 0:
        st.player.effect(st, 'brood', col, depth, 2)
    st.set_grid(CELLS, col, depth, t)
    _set(st, BTYPE, cur, t)
    _set(st, BE, cur, 0)


def n_egg_laying(st, col, depth, caste, t):
    """f_7a490: the queen's head wanders (towards the centroid), her abdomen lays eggs."""
    cur = _cur(st)
    if caste == 12:
        if st.rand64() == 0:
            if st.u16(G, 0x10be) == 0:
                _set(st, BTYPE, cur, 0)
                st.set_grid(CELLS, col, depth, 0)
                st.player.effect(st, 'message', 0x1093, 0, 0x271f, 1)     # f_2f6ea: the queen starved
                return
            if queen_move(st, col, depth, t):
                return
        v = _get(st, BTYPE, cur)
        if queen_head_lost(st, col, depth, v):
            v = 0
            _set(st, BTYPE, cur, 0)
            st.inc16(G, 0x35e, -1)
        st.set_grid(CELLS, col, depth, v)
        if _visible(st):
            st.player.effect(st, 'queen', col, depth, 2)
        return
    if caste != 13:
        return
    v = _get(st, BTYPE, cur)
    st.set_grid(CELLS, col, depth, v)
    if s16(st.u16(G, 0x35e)) > 0 and queen_tail_lost(st, col, depth, v):
        st.inc16(G, 0x35e, -1)
        _set(st, BTYPE, cur, 0)
        st.set_grid(CELLS, col, depth, 0)
        return
    back = (t ^ 0xfc) & 7
    r, c = mv.dy(st, back) + depth, mv.dx(st, back) + col
    if not nest_cell_free(c, r):
        return
    st.set16(T, 0x2b4, c)
    st.set16(T, 0x2b6, r)
    if st.u16(G, 0xf08) & 0xf:
        return
    if s16(st.rand128()) > s16(st.u16(G, 0x10be)):
        return
    spawn_brood(st, N, c, r, 1)
    egg_cost(st)
    st.inc32(G, 0xfc2)


def n_fighting(st, col, depth):
    """f_7a126: a fight entity jitters; with 1/16 per tick the winner (saved in b_e) emerges."""
    cur = _cur(st)
    j = st.rand(7)
    _set(st, BTYPE, cur, ((_get(st, BTYPE, cur) & 0xf8) + j) & 0xff)
    st.set_grid(CELLS, col, depth, _get(st, BTYPE, cur))
    if st.rand16() == 0:
        w = _get(st, BE, cur)
        st.set_grid(CELLS, col, depth, w)
        _set(st, BTYPE, cur, w)
        if w & 0x78 == 0x60:
            add_abdomen(st, cur)
        w = _get(st, BTYPE, cur)
        _set(st, BSTATE, cur, 7 if w & 0x80 else mv.state_for_caste(st, (w & 0x78) >> 3, w))
    elif _visible(st) == 1:
        st.player.effect(st, 'fight', col, depth, 2)


def n_resting(st, col, depth, t):
    """f_79ec5."""
    if fight_at(st, col, depth, t) == 1:
        return
    cur = _cur(st)
    st.set_grid(CELLS, col, depth, _get(st, BTYPE, cur))
    if st.rand(20) == 0:
        b = _get(st, BTYPE, cur)
        _set(st, BSTATE, cur, mv.state_for_caste(st, (b & 0x78) >> 3, b))
    elif _visible(st) == 1:
        st.player.effect(st, 'rest', col, depth, 2)


def n_state17(st, col, depth, t):
    """f_79f70: dying in the dirt? Leaves at a tunnel/food cell, else jitters and dies with 1/100."""
    cur = _cur(st)
    if st.grid(DIRT, col, depth) < 0x14:
        _set(st, BSTATE, cur, _job(st, (t & 0x78) >> 3))
        return
    nt = (((st.rand(3) + t - 1) & 7) | (t & 0xf8)) & 0xff
    _set(st, BTYPE, cur, nt)
    st.set_grid(CELLS, col, depth, nt)
    if st.rand(100) == 0:
        st.set_grid(CELLS, col, depth, 0)
        _set(st, BTYPE, cur, 0)
        st.inc32(G, 0xfbc if t & 0x80 else 0xf30)


def n_invader_move(st, col, depth, t):
    """f_79e40: red invaders climb towards the exit (any direction allowed)."""
    c = climb_dir(st, N, col, depth, 8)
    d = st.rand8() if c == 0 else c - 1
    if not move_to(st, N, col, depth, d) and not move_to(st, N, col, depth, st.rand8()):
        st.set_grid(CELLS, col, depth, _get(st, BTYPE, _cur(st)))


def n_invader_attack(st, col, depth, t):
    """f_79d6f: raiding invaders head deeper looking for stored food, eat it and carry some home."""
    cur = _cur(st)
    v = st.grid(DIRT, col, depth)
    if v < 0x10 or v > 0x13:
        if move_to(st, N, col, depth, (st.rand(3) + t - 2) & 7):
            return
        d = step_dir(st, N, col, depth, t & 7)
        if d < 0:
            d = st.rand(8)
        if move_to(st, N, col, depth, d):
            return
        _set(st, BSTATE, cur, 1)
    else:
        invader_eat_food(st, N, col, depth)
        _set(st, BSTATE, cur, 3)
        _set(st, BTYPE, cur, _get(st, BTYPE, cur) | 8)
    st.set_grid(CELLS, col, depth, _get(st, BTYPE, cur))


GO_OUT = (2, 5, 7, 11, 12, 15, 16)


def nest_ant_tick(st, col, depth, t):
    """f_79a4d BlackNestAntTick."""
    caste = (t & 0x78) >> 3
    cur = _cur(st)
    state = _get(st, BSTATE, cur)
    if t & 0x80:
        st.inc16(G, 0xd72 + state * 2)
        if t > 0xef:
            n_fighting(st, col, depth)
            return
        o = st.grid(CELLS, col, depth)
        if mv.is_yellow(o) and st.u16(G, 0x4e2) == 0:
            st.player.attack_player(st, 2, cur)
            return
        if 0 < o < 0x68:
            i = nest_ant_at(st, N, col, depth, o)
            if i >= 0:
                if o > 0x5f:
                    remove_ant(st, i)
                if o < 8:                                    # steal brood
                    _set(st, BSTATE, cur, 3)
                    _set(st, BTYPE, cur, _get(st, BTYPE, cur) | 8)
                    st.set_grid(CELLS, col, depth, _get(st, BTYPE, cur))
                    _set(st, BTYPE, i, 0)
                    st.inc32(G, 0x1000)
                    return
                w = sf.resolve_fight(st, _get(st, BTYPE, i), t)
                _set(st, BTYPE, cur, 0)
                _set(st, BE, i, w)
                nt = ((w & 0x80) + 0x70) & 0xff
                _set(st, BTYPE, i, nt)
                st.set_grid(CELLS, col, depth, nt)
                _set(st, BSTATE, i, 10)
                return
        if state == 7:
            n_invader_attack(st, col, depth, t)
        else:
            n_invader_move(st, col, depth, t)
        return
    st.inc16(G, 0xd40 + state * 2)
    if st.rand256() == 0 and state != 9 and s16(st.rand32()) > s16(st.u16(G, 0x10be)):
        _set(st, BTYPE, cur, 0)
        st.set_grid(CELLS, col, depth, 0)
        st.inc32(G, 0xf30)
        return
    if state > 0x11 or state == 0:
        n_wander(st, col, depth, t, caste)
    elif state == 1:
        n_nesting(st, col, depth, t, caste)
    elif state == 3:
        n_got_food(st, col, depth, t)
    elif state == 4:
        n_dig_in(st, col, depth, t, caste)
    elif state == 6:
        n_defense(st, col, depth, t)
    elif state == 8:
        n_brood(st, col, depth)
    elif state == 9:
        n_egg_laying(st, col, depth, caste, t)
    elif state == 10:
        n_fighting(st, col, depth)
    elif state == 13:
        n_resting(st, col, depth, t)
    elif state == 14:
        n_wander(st, col, depth, t, caste)
        if s16(st.u16(G, 0x8dc)) > 100:
            _set(st, BSTATE, _cur(st), 15)
    elif state == 17:
        n_state17(st, col, depth, t)
    else:
        n_go_to_surface(st, col, depth, t)


def black_nest_loop(st):
    """f_799e0 BlackNestLoop: every live black-nest ant, from the top of the array down."""
    st.set16(G, 0xf18, st.u16(G, 0xda8))
    while s16(st.u16(G, 0xf18)) > 0:
        st.inc16(G, 0xf18, -1)
        i = st.u16(G, 0xf18)
        t = _get(st, BTYPE, i)
        if t:
            nest_ant_tick(st, _get(st, BX, i), _get(st, BY, i), t)
```
{% endraw %}
