"""New game (f_6b36b, overlay 10) and patch setup (f_6ae20): a fresh yard, the starting patch and its
colonies, the yellow ant, and every counter the simulation keeps.

The game mode is G:0EAC (1 Quick Game, 2 Full Game, 3 the experimental mode). The starting patch is yard
patch (col 11, row 8): its seed is SIM:0000 + 2 * (G:07CC * 12 + G:07CA) (sic: rows of 12) and its terrain
comes from f_73020(G:07BC, G:07BE).

Screen-only work (the colony-behaviour panel's slider geometry, the redraw) goes to st.player.effect.
"""
from .state import SIM, G, T
from . import colony as co
from . import nest
from . import nestgrid as ng
from . import player
from . import terrain
from .movement import s16

SURFACE, OCC = 0x0180, 0x6180
PHER_MAPS = (0xd89f, 0xd09f, 0xe09f, 0xe89f, 0xf09f)    # p2, alarm, black nest, black trail, red nest
RED_TRAIL = (0x4da7, 0)                                # the red trail map, past the sim segment


# ------------------------------------------------------------------------------------------- clearing
def clear_world(st):
    """f_6c010: surface and occupancy, both nests, the pheromone maps, every ant array, the yard colonies."""
    for i in range(0x2000):
        st.set8(SIM, SURFACE + i, 0)
        st.set8(SIM, OCC + i, 0)
    for n in (ng.BLACK, ng.RED):
        for i in range(0x1000):
            st.set8(SIM, n['dirt'] + i, 0)
            st.set8(SIM, n['exitf'] + i, 0)
            st.set8(SIM, n['cells'] + i, 0)
    _clear_pheromones(st)
    for i in range(1000):
        for base in (0xad3b, 0xa952, 0xb124):                          # s_type, s_state, s_e
            st.set8(SIM, base + i, 0)
    for i in range(500):
        for n in (ng.BLACK, ng.RED):
            for f in ('type', 'state', 'e'):
                st.set8(SIM, n[f] + i, 0)
    for i in range(12 * 16):
        st.set8(T, 0xa4 + i, 0)
        st.set8(T, 0x164 + i, 0)


def _clear_pheromones(st):
    for i in range(0x800):
        for base in PHER_MAPS:
            st.set8(SIM, base + i, 0)
        st.set8(RED_TRAIL[0], RED_TRAIL[1] + i, 0)


def reset_records(st, full):
    """f_79478 (via f_2f956): the history records; `full` (a new game) also resets the yard counters."""
    for i in range(0x40):
        for off in (0x516, 0x5a0, 0x626, 0x6ae, 0x73c, 0x7ce, 0x856, 0x8f0, 0x970, 0xa0a):
            st.set16(G, off + 2 * i, 0)
    if full == 1:
        st.set32(G, 0xada, 0)
        st.set16(G, 0xa90, 1)
        st.set16(G, 0xac4, 1)
        st.set16(G, 0xa9e, 0)
        st.set16(G, 0xac8, 0)
    st.set16(G, 0x4f4, 0x3f)
    st.set16(T, 0x828, 0)
    for off in (0xf20, 0xf30, 0xefc, 0xf80, 0xfbc, 0xf3e, 0xfc2, 0x1000):
        st.set32(G, off, 0)


def init_colony_settings(st):
    """InitColonySettings (f_0888d): automatic behaviour, the default behaviour and caste mixes."""
    st.player.effect(st, 'colony_panel')       # resource 0x578 → G:3832, slider geometry (f_07a57, f_07a19)
    st.set16(G, 0x378, 1)
    st.set16(T, 0x7e8, 1)
    st.set16(G, 0x468, 1)
    st.set16(T, 0x7ea, 1)
    st.set16(G, 0x370, 0xffff)
    st.set16(G, 0x24e, 0xffff)
    for i in range(3):
        w = st.u16(T, 0x80a + 2 * i)
        st.set16(G, 0x49e + 2 * i, w)
        st.set16(T, 0x810 + 2 * i, w)
        c = st.u16(T, 0x7ec + 2 * i)
        st.set16(G, 0x482 + 2 * i, c)
        st.set16(T, 0x7f2 + 2 * i, c)
    caste_targets(st)


def caste_targets(st):
    """f_085f8(T:07DA): the caste triangle as four percentages (rounded up from 16-bit fractions)."""
    def pct(v, k):
        return ((k * v + 0x3fff) & 0xffffffff) // 0xffff & 0xffff
    st.set16(T, 0x7da, pct(st.u16(G, 0x484), 100))
    st.set16(T, 0x7dc, pct(st.u16(G, 0x486), 100))
    st.set16(T, 0x7de, pct(st.u16(G, 0x482), 50))
    st.set16(T, 0x7e0, pct(st.u16(G, 0x482), 50))


def reset_yard(st):
    """f_683a0 (via f_2f910): the yard layer's state (human, mower, bird, dog, rain, timers)."""
    st.set32(G, 0x109c, 0)
    st.set16(T, 0xc2c, 0xb4)
    st.set16(T, 0xc2e, 0x49)
    st.set16(T, 0xc34, 0xc)
    st.set16(T, 0xc2a, 0x14)
    st.set32(G, 0x107e, 0)
    st.set32(G, 0x220, 0)
    st.set16(G, 0x4be, 0xfa)
    st.set16(G, 0x4c6, 0x96)
    st.set16(T, 0xc30, 2)
    st.set16(G, 0x624, 2)
    for seg, off in ((G, 0x10b0), (G, 0x246), (G, 0x23e), (T, 0xc32), (T, 0xc28), (T, 0xc40), (T, 0xc46),
                     (T, 0xc48), (G, 0x10a0), (G, 0x22c), (G, 0x244), (G, 0x254), (G, 0x4e4), (G, 0x506),
                     (T, 0xc3e), (T, 0xc42), (G, 0x3e0), (G, 0x46a), (G, 0x470), (G, 0x47a), (G, 0x202),
                     (G, 0x352), (G, 0x105c), (G, 0x1066)):
        st.set16(seg, off, 0)
    for off in (0x108c, 0x364, 0x36e):
        st.set16(G, off, 1)
    st.set16(G, 0x10bc, 0xffff)
    st.set16(G, 0x7c2, 0xffff)


def reset_patch_globals(st):
    """f_0cdb0: per-patch globals (the spider's start, timers)."""
    st.set16(G, 0x1076, 10)
    for seg, off in ((G, 0x1054), (G, 0x105a), (G, 0x1042), (G, 0x1072), (G, 0x108a), (G, 0x1004), (T, 0xc12)):
        st.set16(seg, off, 0)
    st.set16(G, 0xf0c, 1 if st.u16(G, 0xeac) >= 1 else 0)
    st.set16(G, 0xf12, 0x400)
    st.set16(G, 0xf34, 0x200)
    st.set16(G, 0xfb8, 0)
    st.set16(G, 0x6ac, 0)
    st.set16(G, 0xffc, 0xfffe)
    st.set16(G, 0x10ae, 0xffff)
    st.set16(G, 0xf42, 0x40)
    st.set16(G, 0xf7e, 0x40)


# ------------------------------------------------------------------------------------------- the patch
def _scatter_colony(st, n, red):
    """Part of f_6ae20: n surface ants of one colony, at random spots (black left, red right)."""
    tries = 0
    w = st.rand(6) + 7                       # workers below w (of 16), soldiers below s, then breeders
    s = 15 - st.rand2()
    while n > 0:
        n -= 1
        r = st.rand_low(0x80)
        a = 0x7f - r if red else r
        b = st.rand64()
        if st.grid(SURFACE, a, b) >= 0x50:
            continue
        if st.grid(OCC, a, b):
            tries += 1
            if tries < 0x32:
                n += 1
            continue
        r = st.rand16()
        if r < w:
            v = 0x10                         # worker
        elif s > r:
            v = 0x30                         # soldier
        elif st.rand2():
            v = 0x20                         # male
        else:
            v = 0x40                         # new queen
        st.set_grid(OCC, a, b, (v + st.rand8() + (0x80 if red else 0)) & 0xff)


def add_surface_ants(st, n, red):
    """f_6be50 (black) / f_6bf06 (red): up to n ants on the free open cells of the colony's half (black
    columns 0..63 up, red 127..64 down; rows 16..47), 3 in 10 soldiers (state 2), else workers (state 4);
    stops early at 1000 surface ants."""
    for a in (range(0x7f, 0x3f, -1) if red else range(0x40)):
        for b in range(0x10, 0x30):
            if st.grid(SURFACE, a, b) >= 0x50 or st.grid(OCC, a, b):
                continue
            base, state = (0x30, 2) if st.rand(10) <= 3 else (0x10, 4)
            t = st.rand8() + base + (0x80 if red else 0)
            st.set_grid(OCC, a, b, t & 0xff)
            player.add_surface_ant_raw(st, a, b, t, state, 0)
            n -= 1
            if n <= 0 or s16(st.u16(G, 0xd6a)) >= 1000:
                return


def _start_nest(st, n, dig_random):
    """f_6b95c (black) / f_6bae2 (red): a shaft from the entrance (nest column 32) down 7..10 rows,
    wandering sideways, then a short diagonal to the queen's chamber."""
    depth_n = st.rand4() + 7
    col, dcol = 0x20, 0
    depth = 1
    while depth_n > depth:
        ng.dig_at(st, n, col, depth)
        dcol = dig_random(st, dcol)
        c = s16(dcol + col)
        if 8 <= c <= 0x38:
            col = c
        depth += 1
    for _ in range(2):
        ng.dig_at(st, n, col, depth)
        col += 1
        depth += 1
    ng.dig_at(st, n, col, depth)
    return col, depth


def _black_drift(st, d):
    return st.rand(3) - 1 if st.rand2() == 0 else d


def _red_drift(st, d):
    return st.rand(3) - 1


def _queen_chamber(st, n, col, depth, heading):
    """f_6ba1c (black) / f_6bb70 (red): dig the chamber and place the queen (two cells, 0x60/0x68 + heading,
    or 0xE0/0xE8 for red), state 9."""
    h = heading ^ 4
    dx, dy = st.s8(T, h), st.s8(T, 8 + h)
    ng.dig_at(st, n, col, depth)
    ng.dig_at(st, n, col + dx, depth + dy)
    ng.dig_at(st, n, col + 2 * dx, depth + 2 * dy)
    red = n['red']
    ng.add_nest_ant(st, n, col, depth, heading + 0x60 + red, 9, 0)
    ng.add_nest_ant(st, n, col + dx, depth + dy, heading + 0x68 + red, 9, 0)
    st.inc16(G, 0x36c if red else 0x35e)


def pre_dig(st, n, steps):
    """f_6b616 (black) / f_6b6f3 (red): a bigger colony gets its tunnels dug by a random walk from the
    entrance (nest column 32), `steps` tries; reaching the top row again opens another entrance."""
    ng.dig_at(st, n, 0x20, 1)
    d, col, depth = 4, 0x20, 1
    while steps != 0:
        d = (st.rand(5) + d - 3) & 7
        c = s16(st.s8(T, d) + col)
        r = s16(st.s8(T, 8 + d) + depth)
        if c < 1:
            c, d = 1, 2
        elif c > 0x3e:
            c, d = 0x3e, 6
        if r < 2:
            r, nd = 1, 4
        else:
            nd = d
            if r > 0x3e:
                r, nd = 0x3e, 0
        if nest.dig_cell(st, n, c, r):
            col, depth = c, r
            if r == 1 and st.u8(T, n['entr'] + c) == 0:
                nest.make_surface_hole(st, n, c)
        steps = (steps - 1) & 0xffff
        d = nd


def start_black_nest(st):
    """f_6b95c."""
    col, depth = _start_nest(st, nest.BLACK, _black_drift)
    st.set16(T, 0x2b4, col)
    st.set16(T, 0x2b6, depth)
    st.set16(G, 0xf0e, col)
    st.set16(G, 0xf26, depth)
    _queen_chamber(st, nest.BLACK, col + 2, depth, 2)


def start_red_nest(st):
    """f_6bae2."""
    col, depth = _start_nest(st, nest.RED, _red_drift)
    st.set16(T, 0x2b8, col)
    st.set16(T, 0x2ba, depth)
    _queen_chamber(st, nest.RED, col + 2, depth, 2)


def build_surface_ants(st):
    """f_0f329: the surface ant arrays from the occupancy grid (the yellow ant stays out); state 2."""
    st.set16(G, 0xd6a, 0)
    for a in range(0x80):
        for b in range(0x40):
            v = st.grid(OCC, a, b)
            if not v or v in (0xfe, 0xff):                           # IsYellowAnt f_10faa
                continue
            i = st.u16(G, 0xd6a)
            st.set8(SIM, 0xa180 + i, a)
            st.set8(SIM, 0xa569 + i, b)
            st.set8(SIM, 0xa952 + i, 2)
            st.set8(SIM, 0xad3b + i, v)
            st.set8(SIM, 0xb124 + i, 0)
            if s16(i) < 0x3e5:
                st.inc16(G, 0xd6a)


def place_yellow(st):
    """f_6b7d0: the yellow ant. Quick Game: in the black nest beside the queen; Full Game: a new queen on
    the surface near the middle; mode 3: the player is the spider."""
    st.set16(G, 0x49a, 0)
    st.set16(T, 0xc22, 0xfd)
    if st.u16(G, 0x104e):
        st.set16(G, 0x104e, 0)
        st.set16(T, 0x7be, 0xffff)
    player.set_health(st, 100)
    mode = st.u16(G, 0xeac)
    if mode == 3:
        st.set16(G, 0x48c, 1)
        st.set16(G, 0x4e2, 0)
        st.set16(G, 0xa06, 2)
        st.set16(G, 0x47c, 0x40)
        st.set16(G, 0x48a, 0x20)
        st.set16(G, 0x4c2, 0x10)
    else:
        st.set16(G, 0x4e2, 0)
        st.set16(G, 0xa06, 0)
        if mode == 2 and st.u16(T, 0xc24) == 0:
            a, b = 0x40, 0x20
            for _ in range(100):
                da = st.rand16()
                a1 = s16(st.rand16() - da + 0x20)
                db = st.rand8()
                b1 = s16(st.rand8() - db + 0x20)
                if st.grid(SURFACE, a1, b1) < 0x10:
                    a, b = a1, b1
                    break
            player.put_yellow(st, 1, a, b, 0x40, 2, 0xff)
        else:
            player.put_yellow(st, 2, s16(st.u16(G, 0xf0e)), s16(st.u16(G, 0xf26)), 0x10, 2, 0xff)
    set_view(st, st.u16(G, 0x48c), st.u16(G, 0x47c), st.u16(G, 0x48a))


def set_view(st, view, a, b):
    """f_757dd (via f_2f820): show the yellow ant's view; the cursor and its target start on it."""
    st.set16(G, 0x48c, view)
    st.set16(G, 0xaf8, view)
    st.set16(G, 0x47c, a)
    st.set16(G, 0xab6, a)
    st.set16(G, 0xad6, a)
    st.set16(G, 0x48a, b)
    st.set16(G, 0xac6, b)
    st.set16(G, 0xae8, b)
    for off in (0xa8e, 0xaa0, 0xb1e, 0xc38, 0xc3e):
        st.set16(G, off, 0)
    st.set16(G, 0xd6c, 0xfffe)


def setup_patch(st, seed, n_black, n_red, row, col):
    """f_6ae20: generate the patch from its seed and scatter n_black / n_red surface ants (+ a quarter);
    with colonies, dig their nests and place the queens, then the yellow ant and the first food."""
    st.set16(0x55b3, 0x8ba2, seed)                                     # SeedLfsr f_009bf
    reset_patch_globals(st)
    terrain.surface_terrain(terrain.StateSurface(st), st, row, col)    # f_2f94c → f_73020
    n_black += n_black >> 2
    n_red += n_red >> 2
    for n in (ng.BLACK, ng.RED):
        for i in range(0x1000):
            st.set8(SIM, n['dirt'] + i, 0x2e)
            st.set8(SIM, n['exitf'] + i, 0)
            st.set8(SIM, n['cells'] + i, 0)
    for i in range(0x2000):
        st.set8(SIM, OCC + i, 0)
    for c in range(0x40):                    # the top soil row
        if st.u16(G, 0xf24) == 0:
            st.set_grid(ng.BLACK['dirt'], c, 0, st.rand4() + 0x1c)
            st.set_grid(ng.RED['dirt'], c, 0, st.rand4() + 0x1c)
        else:
            st.set_grid(ng.BLACK['dirt'], c, 0, st.rand(2) + 0x1c if s16(col) > 3 else 0x1e)
            st.set_grid(ng.RED['dirt'], c, 0, st.rand(2) + 0x1c if s16(col) > 3 else 0x1e)
        st.set_grid(ng.BLACK['exitf'], c, 0, 0xff)
        st.set_grid(ng.RED['exitf'], c, 0, 0xff)
    _clear_pheromones(st)
    _scatter_colony(st, n_black, False)
    _scatter_colony(st, n_red, True)
    for c in range(0x40):
        st.set8(T, 0x224 + c, 0)
        st.set8(T, 0x264 + c, 0)
    if st.u16(G, 0xeac) != 2 or n_black >= 1:
        nest.make_surface_hole(st, nest.BLACK, 0x20)
    if n_red >= 1:
        nest.make_surface_hole(st, nest.RED, 0x20)
    for off in (0x10a2, 0x108e, 0x1082, 0x1068):
        st.set32(G, off, 0)
    for off in (0x224, 0x232, 0x20e, 0x200, 0x10c0, 0x10b2):
        st.set16(G, off, 0)
    st.set16(G, 0x242, 0x40)
    if n_black > 1:
        pre_dig(st, nest.BLACK, n_black << 4)                          # f_6b616
    if n_red > 1:
        pre_dig(st, nest.RED, n_red << 4)                              # f_6b6f3
    build_surface_ants(st)
    st.set16(G, 0xda8, 0)                                              # f_0f3d1
    st.set16(G, 0xeaa, 0)                                              # f_0f3e4
    st.set16(G, 0x35e, 0)
    st.set16(G, 0x36c, 0)
    st.set32(T, 0x2b4, 0xffffffff)
    st.set32(T, 0x2b8, 0xffffffff)
    if n_red > 0:
        start_red_nest(st)
    if n_black > 0:
        start_black_nest(st)
    place_yellow(st)
    st.set16(G, 0x1050, 0)
    st.set16(G, 0x1060, 0)
    st.set16(G, 0x1040, 0)
    if st.u16(G, 0xeac) != 3:
        co.drop_food(st, -1, 0)
    st.set16(G, 0x10be, 100)
    st.set16(G, 0x1fe, 100)
    st.set32(G, 0x472, 0)
    for off in (0x9fa, 0xa00, 0xf08):
        st.set16(G, off, 0)
    reset_records(st, 0)
    co.census(st, lambda m: st.player.effect(st, 'message', m))
    st.player.effect(st, 'redraw_rect', 0, 0, st.u16(G, 0xfb6), st.u16(G, 0xffa))     # f_0256e
    st.set16(G, 0x508, 0x40)
    st.set16(G, 0x596, 0x40)
    st.set16(G, 0x50a, 0x20)
    st.set16(G, 0x598, 0x20)
    st.set16(G, 0x6a6, 0x20)
    st.set16(G, 0x72e, 0x20)
    st.set16(G, 0x6a8, 1)
    st.set16(G, 0x730, 1)


# ------------------------------------------------------------------------------------------- moving
def move_to_patch(st):
    """f_01d48 (Full Game): go to the yard patch the player picked (row G:07BC, col G:07BE, set by the yard
    map). It must hold a black colony, unless the yellow ant is a new queen that has not settled yet
    (T:0C24 == 0). The patch is generated afresh with the yard's colony sizes."""
    row, col = s16(st.u16(G, 0x7bc)), s16(st.u16(G, 0x7be))
    if row == s16(st.u16(G, 0x7ca)) and s16(st.u16(G, 0x7cc)) == col:
        return
    if st.u16(G, 0xeac) != 2:
        refuse = 0x2710                      # only in a Full Game
    elif s16(st.u16(G, 0x3e2)) <= 1 and s16(st.u16(G, 0x330)) <= 1:
        refuse = 0x2712                      # the colony is too small to move
    else:
        refuse = None
        idx = (row * 16 + col) & 0xffff
        if st.u8(T, 0xa4 + idx) < 1 and not (st.u16(G, 0x4c2) == 0x40 and st.u16(T, 0xc24) == 0):
            refuse = 0x2714                  # no black colony there
    if refuse:
        st.player.effect(st, 'sound', 1)                               # f_00ed8(1, 0, 0x7e)
        st.player.effect(st, 'message_box', refuse, 1)                 # f_2f6ea → f_71b1a(0, id, 1)
        return
    st.player.effect(st, 'voice', 0x2afa)                              # f_00ea1(0x2afa, 0x7e)
    st.set16(G, 0x7ca, row)
    st.set16(G, 0x7cc, col)
    st.player.effect(st, 'yard_map')                                   # f_2f6e0 → f_6f46a
    st.set16(G, 0x354, 1)
    for off in (0x7c8, 0x850, 0x6aa, 0x73a):
        st.set16(G, off, 0)
    st.set16(T, 0xc24, 1)
    black, red = st.u8(T, 0xa4 + idx), st.u8(T, 0x164 + idx)
    setup_patch(st, st.u16(SIM, (2 * (col * 12 + row)) & 0xffff), black, red, row, col)
    if st.u8(T, 0x164 + idx) == 0:
        st.set16(G, 0x1fe, 0)
    st.player.effect(st, 'message_box', 0x2716 if s16(idx) > 0x24 else 0x2717, 0)


# ------------------------------------------------------------------------------------------- new game
def new_game(st):
    """f_6b36b: start a game in mode G:0EAC (the caller sets it)."""
    clear_world(st)
    reset_records(st, 1)
    init_colony_settings(st)
    st.set16(G, 0x7ca, 0xb)
    st.set16(G, 0x7bc, 0xb)
    st.set16(G, 0x7cc, 8)
    st.set16(G, 0x7be, 8)
    reset_yard(st)
    st.set16(G, 0x105e, 0xffff)
    st.set32(G, 0x214, 0)
    st.set32(G, 0x204, 0)
    for seg, off in ((G, 0x228), (G, 0x478), (G, 0x504), (G, 0x366), (G, 0x376), (T, 0xc44), (T, 0xc18),
                     (T, 0xc16), (T, 0xc14)):
        st.set16(seg, off, 0)
    st.set32(G, 0xc26, 0)
    mode = s16(st.u16(G, 0xeac))
    st.set16(G, 0x32e, 1 if mode > 1 else 2)
    st.set16(T, 0x7c8, st.u16(G, 0x32e))
    st.set16(G, 0x35c, 0)
    for i in range(0xc0):                    # the yard's patch seeds
        st.set16(SIM, 2 * i, (st.crt_rand_mod(0x7fff) - 0xc000) & 0x7fff)
    full = st.u16(G, 0xeac) == 2
    st.set16(T, 0xc24, 0 if full else 1)
    idx = s16(st.u16(G, 0x7cc)) * 12 + s16(st.u16(G, 0x7ca))
    setup_patch(st, st.u16(SIM, (2 * idx) & 0xffff), 0 if full else 1, 1, s16(st.u16(G, 0x7bc)),
                s16(st.u16(G, 0x7be)))
    view = s16(st.u16(G, 0x48c))
    a, b = st.u16(G, 0x47c), st.u16(G, 0x48a)
    if view < 2:
        st.set16(G, 0x596, a)
        st.set16(G, 0x598, b)
    elif view == 2:
        st.set16(G, 0x6a6, a)
        st.set16(G, 0x6a8, b)
    else:
        st.set16(G, 0x72e, a)
        st.set16(G, 0x730, b)
