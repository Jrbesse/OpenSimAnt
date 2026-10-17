"""Hidden debug commands of the resident code (segment 015b): adding and killing ants, clearing food, and a
random one of 15 actions (menu command 0x112, f_022bc). Ctrl-clicks on the control of command 0x110 reach the
first three through f_6f733 (see SIM_NOTES "Debug commands").

Screen-only effects go to st.player.effect: 'sound' (f_00ed8 / f_00f02), 'music' (f_00ed0), 'message'
(f_71b1a), and 'message' from the census.
"""
from .state import SIM, G, T
from . import colony as co
from . import movement as mv
from . import nest
from . import nestgrid as ng
from . import newgame
from . import surface
from . import world
from .movement import s16

SURFACE, OCC = 0x0180, 0x6180
STYPE, SX, SY = 0xad3b, 0xa180, 0xa569


def player_at(st, view, a, b):
    """f_134b8: is the player at (a, b) in `view` (0 means the surface)? The spider (G:0A06 == 1) covers
    every surface cell centre within squared distance 0x200 of its position (G:0F12, G:0F34)."""
    if st.u16(G, 0x48c) != (view or 1):                          # f_135b0
        return 0
    if st.u16(G, 0xa06) == 1:
        if s16(view) > 1:
            return 0
        d = co.distance(a * 16 + 8, b * 16 + 8, s16(st.u16(G, 0xf12)), s16(st.u16(G, 0xf34)))
        return 1 if d < 0x200 else 0
    if 0 <= view <= 1:
        o = st.grid(OCC, a, b)
    elif view == 2:
        o = st.grid(nest.BLACK['cells'], a, b)
    elif view == 3:
        o = st.grid(nest.RED['cells'], a, b)
    else:
        raise NotImplementedError('f_134b8: a view outside 0..3 reads an uninitialised local')
    return 1 if mv.is_yellow(o) else 0


def add_ants(st, black):
    """f_015be: 32 surface ants of one colony (T:0798 == 1: as many as fit under 1000), then the census."""
    count = s16(st.u16(G, 0xd6a))
    if count < 1000:
        n = 1000 - count if st.u16(T, 0x798) == 1 else 0x20
        newgame.add_surface_ants(st, n, not black)
    world.census_and_advise(st)


def kill_ants(st, black):
    """f_0161f: up to 51 surface ants of one colony die, newest first (red ones on the player are spared)."""
    ng.compact_surface(st)
    world.census_and_advise(st)
    killed = 0
    for i in range(s16(st.u16(G, 0xd6a)) - 1, -1, -1):
        t = st.u8(SIM, STYPE + i)
        a, b = st.u8(SIM, SX + i), st.u8(SIM, SY + i)
        if black:
            if t & 0x80:
                continue
            surface.place_corpse(st, a, b, 0)
        else:
            if not t & 0x80 or player_at(st, 1, a, b):
                continue
            surface.place_corpse(st, a, b, 1)
        st.set8(SIM, STYPE + i, 0)
        killed += 1
        if killed > 0x32:
            break
    ng.compact_surface(st)
    world.census_and_advise(st)


def clear_food(st):
    """f_01707: every food crumb on the surface becomes plain ground (a random tile 0..15)."""
    for a in range(0x80):
        for b in range(0x40):
            if world.is_food_tile(st, st.grid(SURFACE, a, b)):
                st.set_grid(SURFACE, a, b, st.rand16())
    st.set16(G, 0x1040, 0)


def _toggle(st, off):
    v = 1 if st.u16(T, off) == 0 else 0
    st.set16(T, off, v)
    return v


def random_action(st):
    """f_022bc: one of 15 actions, chosen by C rand() % 15."""
    k = st.crt_rand_mod(15)
    fx = st.player.effect
    if k in (0, 1, 2):
        add_ants(st, k == 2)
        add_ants(st, k == 2)
    elif k in (3, 4):
        kill_ants(st, k == 4)
        kill_ants(st, k == 4)
    elif k == 5:
        co.drop_food(st, 0x96, 1)
    elif k == 6:
        fx(st, 'sound2', 0x20, 0, 0x7e)                          # f_00f02
        clear_food(st)
    elif k == 7:
        fx(st, 'music', 0)
    elif k in (8, 9):
        n = nest.RED if k == 8 else nest.BLACK
        for i in range(0x20):
            nest.make_surface_hole(st, n, 2 * i)
    elif k == 10:
        st.set16(T, 0xc18, 0)
        st.set16(G, 0x10be, 0)
        st.set16(G, 0x1fe, 0)
    elif k == 11:
        fx(st, 'sound', 2 if _toggle(st, 0xc14) else 1)
    elif k == 12:
        _toggle(st, 0xc12)
    elif k == 13:
        fx(st, 'message', 0x2726)
        fx(st, 'music', 1)
        fx(st, 'message', 0x2728)
    elif k == 14:
        st.set16(G, 0x6ac, 8)                                    # the spider lashes out
        fx(st, 'sound', 2, 0x2b77, 0x7e)
