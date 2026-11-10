"""The map tools (overlay 27, f_770f6): what a click on the map does with the tool G:104C, in the view on
screen G:032E (1 surface, 2 black nest, 3 red nest). Options per tool are the bytes T:07B7..T:07BC.

  0 info (f_2f8fc, UI)      1 rocks f_7723f (surface)   2 dig f_7739f
  3 ants f_77672            4 food f_77790              5 pheromone f_7783a (surface)
  6 insecticide f_778bd

Alt (BIOS shift flags 0000:0417 bit 3, st.bios_kbd) takes food and pheromone away instead of adding.
Screen-only effects go to st.player.effect: 'sound' (f_00ed8(n, pitch, 0x7E)), 'info' (f_2f8fc).
"""
from .state import SIM, G, T
from . import nest
from . import nestgrid as ng
from . import player
from . import surface
from . import world
from . import movement as mv
from .colony import _cdiv
from .movement import s16

OCC = 0x6180
ALT = 8
# T:07BB picks the map: black nest marker, black trail, red nest marker, red trail, alarm (64 x 32 each)
PHER_MAPS = ((SIM, 0xe09f), (SIM, 0xe89f), (SIM, 0xf09f), (0x4da7, 0), (SIM, 0xd09f))


def _view(st):
    return st.u16(G, 0x32e)


def _sound(st, n, pitch=0):
    st.player.effect(st, 'sound', n, pitch)


def apply_tool(st, a, b):
    """f_770f6: the current tool at (a, b); rocks and dig start from the previous point (G:09FC, G:09FE)."""
    tool = st.u16(G, 0x104c)
    view = _view(st)
    if tool == 0:
        if player.get_occ(st, view, a, b):
            st.player.effect(st, 'info', a, b, view)
    elif tool == 1:
        if view == 1:
            rocks(st, s16(st.u16(G, 0x9fc)), s16(st.u16(G, 0x9fe)), a, b)
    elif tool == 2:
        dig(st, s16(st.u16(G, 0x9fc)), s16(st.u16(G, 0x9fe)), a, b)
    elif tool == 3:
        ants(st, a, b)
    elif tool == 4:
        food(st, a, b)
    elif tool == 5:
        pheromone(st, a, b)
    elif tool == 6:
        insecticide(st, a, b)


# ------------------------------------------------------------------------------------------- ants
def ants(st, a, b):
    """f_77672: one worker (T:07B9 == 1: red), state 2; in the other colony's nest an invader (state 7)."""
    t = st.rand(8) + 0x10
    if st.u8(T, 0x7b9) == 1:
        t += 0x80
    view = _view(st)
    if view == 1:
        if not player.is_open_ground(st, 1, a, b):
            return
        player.add_surface_ant_raw(st, a, b, t, 2, 0)
    elif view in (2, 3):
        if b == 0:
            return
        n = ng.BLACK if view == 2 else ng.RED
        if st.grid(n['dirt'], a, b) >= 0x1c:
            ng.dig_at(st, n, a, b)
        own = (t > 0x80) == (view == 3)
        ng.add_nest_ant(st, n, a, b, t, 2 if own else 7, 0)
    _sound(st, 0x1c)


# ------------------------------------------------------------------------------------------- food
def drop_crumb(st, a, b):
    """f_77ad6: grow the food crumb at (a, b) by one (a new one on bare ground), or with Alt take it back to
    ground. Adding counts it (G:1040 surface, G:1050 black nest, G:1060 red nest); taking only uncounts
    surface crumbs. 1 if done."""
    view = _view(st)
    base = 0x48 if view == 1 else 0x10
    t = player.get_tile(st, view, a, b)
    if st.bios_kbd & ALT:
        if base > t or base + 3 < t:
            return 0
        t = st.rand(8)
        # only the surface counter: the nest counters' code (77b5c) is reached only with view 1 (dead)
        if view == 1 and s16(st.u16(G, 0x1040)) > 0:
            st.set16(G, 0x1040, st.u16(G, 0x1040) - 1)
    else:
        if base + 2 < t:
            return 0
        if base <= t:
            t += 1
        elif t < 0x18:
            t = base
        off = 0x1040 if view == 1 else 0x1050 if view == 2 else 0x1060
        st.set16(G, off, st.u16(G, off) + 1)
    player.set_tile(st, view, a, b, t)
    return 1


def food(st, a, b):
    """f_77790: one crumb (sound 0x1D), or with T:07BA set 20 at random within 4 cells (sound 0x20)."""
    if st.u8(T, 0x7ba) == 0:
        if drop_crumb(st, a, b):
            _sound(st, 0x1d)
        return
    _sound(st, 0x20)
    view = _view(st)
    for _ in range(0x14):
        x = st.rand(9) + a - 4
        y = st.rand(9) + b - 4
        if player.in_view(view, x, y):
            drop_crumb(st, x, y)


# ------------------------------------------------------------------------------------------- pheromone
def _pher_ok(a, b):
    """f_77ff8."""
    return 0 <= a <= 0x3f and 0 <= b <= 0x1f


def pher_get(st, a, b):
    """f_78025: the selected map at (a, b), -1 off the map."""
    if not _pher_ok(a, b):
        return -1
    k = st.u8(T, 0x7bb)
    if k > 4:
        raise NotImplementedError('f_78025: T:07BB > 4 returns an uninitialised local')
    seg, base = PHER_MAPS[k]
    return st.u8(seg, base + a * 32 + b)


def pher_set(st, a, b, v):
    """ToolDropPheromone f_780cd (capped at 255; a negative value is stored as its low byte)."""
    if not _pher_ok(a, b):
        return
    k = st.u8(T, 0x7bb)
    if k > 4:
        return
    seg, base = PHER_MAPS[k]
    st.set8(seg, base + a * 32 + b, min(v, 0xff) & 0xff)


def _smooth(st, a, b):
    """f_77f71: the cell becomes the mean of itself and the average of its four neighbours."""
    s = pher_get(st, a, b - 1) + pher_get(st, a + 1, b) + pher_get(st, a, b + 1) + pher_get(st, a - 1, b)
    pher_set(st, a, b, _cdiv(_cdiv(s, 4) + pher_get(st, a, b), 2))


def pheromone(st, a, b):
    """f_7783a (surface only): +0x46 to the selected map's cell (Alt: -0x28), smoothed with its neighbours."""
    if _view(st) != 1:
        return
    pa, pb = a >> 1, b >> 1
    v = pher_get(st, pa, pb) + (-0x28 if st.bios_kbd & ALT else 0x46)
    pher_set(st, pa, pb, max(0, min(v, 0xff)))
    for x, y in ((pa, pb), (pa, pb - 1), (pa + 1, pb), (pa, pb + 1), (pa - 1, pb), (pa, pb)):   # f_77f13
        _smooth(st, x, y)
    _sound(st, 0x1b)


# ------------------------------------------------------------------------------------------- insecticide
def _lion_at(st, a, b):
    """f_0b58c: the ant-lion pit at (a, b), searching from the last; -1 if none."""
    for i in range(s16(st.u16(T, 0xc4a)) - 1, -1, -1):
        if st.u8(G, world.LA + i) == a and st.u8(G, world.LB + i) == b:
            return i
    return -1


def insecticide(st, a, b):
    """f_778bd: 8 sprays, all on (a, b) when T:07BC is set, else each on a random cell within 4. Surface ants
    become corpses, the spider is beaten when hit in its cell, ant-lion pits are filled; nest ants vanish."""
    spread = st.u8(T, 0x7bc) == 0
    view = _view(st)
    for _ in range(8):
        if spread:
            x = st.rand(9) + a - 4
            y = st.rand(9) + b - 4
            _sound(st, 9, st.rand(1000) + 0x278f)
        else:
            x, y = a, b
            _sound(st, 9, 0)
        if not player.in_view(view, x, y):
            continue
        if view == 1:
            if st.grid(OCC, x, y):
                i = mv.surface_ant_at(st, x, y)
                st.set16(G, 0xf18, i & 0xffff)
                if i >= 0:
                    surface.place_corpse(st, x, y, st.u8(SIM, 0xad3b + i) & 0x80)
                    st.set8(SIM, 0xad3b + i, 0)
                    st.set_grid(OCC, x, y, 0)
            if s16(st.u16(G, 0xf12)) >> 4 == x and s16(st.u16(G, 0xf34)) >> 4 == y:
                world.spider_beaten(st)
            if 0x38 <= st.grid(world.SURFACE, x, y) <= 0x3e:
                world.remove_lion(st, _lion_at(st, x, y))
        elif view in (2, 3):
            n = ng.BLACK if view == 2 else ng.RED
            o = st.grid(n['cells'], x, y)
            if not o:
                continue
            i = nest.nest_ant_at(st, n, x, y, o)
            st.set16(G, 0xf18, i & 0xffff)
            if i >= 0:
                st.set8(SIM, n['type'] + i, 0)
                st.set_grid(n['cells'], x, y, 0)


# ------------------------------------------------------------------------------------------- rocks
def _is_wall(t):
    """f_77d54: wall tiles 0x60..0x67."""
    return 0x60 <= t <= 0x67


def _wall_mask(st, a, b, view):
    """f_77cc4: which of the four neighbours are walls (left 8, below 4, right 2, above 1)."""
    m = 0
    for x, y in ((a - 1, b), (a, b + 1), (a + 1, b), (a, b - 1)):
        m = (m << 1) | (1 if _is_wall(player.get_tile(st, view, x, y)) else 0)
    return m


def _fit_wall(st, a, b):
    """f_77c74: a wall tile takes the shape its neighbours call for (table DS:2DF4)."""
    if _is_wall(st.grid(world.SURFACE, a, b)):
        st.set_grid(world.SURFACE, a, b, st.u8(0x55b3, 0x2df4 + _wall_mask(st, a, b, 1)))


def _fit_walls(st, a, b):
    """f_77bec: the cell and its four neighbours."""
    _fit_wall(st, a, b)
    for x, y in ((a, b - 1), (a + 1, b), (a, b + 1), (a - 1, b)):
        if mv.in_patch(x, y):
            _fit_wall(st, x, y)


def rocks(st, x, y, ta, tb):
    """f_7723f: from the previous point (x, y) to (ta, tb), one axis per step: walls (T:07B7 == 0, tile 0x60,
    sound 0x28) or pebbles (tiles 0x51..0x53) on free open ground; Alt clears them back to ground."""
    while mv.in_patch(x, y):
        t = st.grid(world.SURFACE, x, y)
        free = t < 0x50 and st.grid(OCC, x, y) == 0
        if st.bios_kbd & ALT:
            if 0x50 < t < 0x68:
                st.set_grid(world.SURFACE, x, y, st.rand(0x10))
            _fit_walls(st, x, y)
        elif st.u8(T, 0x7b7) == 0:
            if free:
                st.set_grid(world.SURFACE, x, y, 0x60)
            _fit_walls(st, x, y)
            _sound(st, 0x28)
        else:
            if free:
                st.set_grid(world.SURFACE, x, y, st.rand(3) + 0x51)
            _sound(st, 0xa, st.rand(10000) + 0x7d0)
        d = mv.dir_to(x, y, ta, tb)
        if st.s8(T, 0x10 + d):
            x += st.s8(T, 0x10 + d)
        else:
            y += st.s8(T, 0x1a + d)
        if d == 0:
            return


# ------------------------------------------------------------------------------------------- dig
def _clear_nest_ants(st, n, col, depth):
    """f_775a2 (black) / f_7760a (red): every live nest ant on the cell is removed, newest first."""
    for i in range(s16(st.u16(G, n['count'])) - 1, -1, -1):
        if (st.u8(SIM, n['type'] + i) and st.u8(SIM, n['x'] + i) == col
                and st.u8(SIM, n['y'] + i) == depth):
            st.set8(SIM, n['type'] + i, 0)
    st.set_grid(n['cells'], col, depth, 0)


def _fill_cell(st, n, col, depth):
    """f_77d75 (black) / f_77e44 (red): the cell back to dirt (0x2E), undoing the dig bookkeeping."""
    st.set_grid(n['dirt'], col, depth, 0x2e)
    st.set_grid(n['cells'], col, depth, 0)
    if s16(st.u16(G, n['cap'])) > 1:
        for off, v in ((n['sum_col'], col), (n['sum_depth'], depth)):
            s = (st.u32(G, off) - v) & 0xffffffff
            st.set32(G, off, 0 if s & 0x80000000 else s)
        st.set16(G, n['cap'], st.u16(G, n['cap']) - 1)
    ng.reclassify_dirt(st, n, col, depth - 1)
    ng.reclassify_dirt(st, n, col + 1, depth)
    ng.reclassify_dirt(st, n, col, depth + 1)
    ng.reclassify_dirt(st, n, col - 1, depth)
    st.set_grid(n['exitf'], col, depth, 0)


def dig(st, x, y, ta, tb):
    """f_7739f: from the previous point (x, y) to (ta, tb), diagonally: dig (T:07B8 == 0; Alt flips it) a
    nest tunnel, or on the surface found a nest; or fill tunnels back in (on the surface: a message)."""
    fill = st.u8(T, 0x7b8)
    if st.bios_kbd & ALT:
        fill ^= 1
    view = _view(st)
    while True:
        if fill == 0:
            if view == 1:
                if player.try_found_nest(st, x, y):
                    _sound(st, 0x13)
                else:
                    _sound(st, 1)
                    st.player.effect(st, 'status', 'cannot dig here')          # f_15e2c
            elif view in (2, 3):
                n = nest.BLACK if view == 2 else nest.RED
                if player.is_dirt(st, view, x, y) and y != 0:
                    ng.dig_at(st, n, x, y)
                    if y == 1:
                        nest.make_surface_hole(st, n, x)
                    _sound(st, 0x13)
        else:
            if view == 1:
                _sound(st, 1)
                st.player.effect(st, 'status', 'cannot fill here')             # f_15e2c
            elif view in (2, 3):
                n = nest.BLACK if view == 2 else nest.RED
                if not player.is_dirt(st, view, x, y) and y != 0:
                    if st.grid(n['cells'], x, y):
                        _clear_nest_ants(st, n, x, y)
                    _fill_cell(st, n, x, y)
                    _sound(st, 0x12)
        d = mv.dir_to(x, y, ta, tb)
        x += st.s8(T, 0x10 + d)
        y += st.s8(T, 0x1a + d)
        if d == 0:
            return
