"""World updates run by SimStep besides the ants: the slow phases, history graph, advisor status line and
weather (SIMANT.EXE segments 0894, 1be8, 1e2e, 892c).

Screen-only side effects (status line text, dirty-cell marks, sounds) go to st.player.effect.
"""
from .state import SIM, G, T
from . import colony as co
from . import nestgrid as ng
from . import pheromones as ph

SURFACE = 0x0180
s16 = ng.s16


# ------------------------------------------------------------------------------------------- history
def history(st):
    """f_798c8 (slow phase 0/2): sample the history graph (64-entry ring at G:04F4)."""
    i = st.u16(G, 0x4f4) * 2
    for src, dst in ((0x330, 0x516), (0x350, 0x5a0), (0x1050, 0x626), (0x1060, 0x6ae), (0x10be, 0x73c),
                     (0x1fe, 0x7ce), (0x1040, 0x856), (0xf30, 0x8f0), (0xf20, 0x970), (0xefc, 0xa0a)):
        st.set16(G, dst + i, st.u16(G, src))
    if s16(st.u16(T, 0x828)) < 0x3f:
        st.inc16(T, 0x828)
    st.set16(G, 0x4f4, (st.u8(G, 0x4f4) + 1) & 0x3f)
    st.player.effect(st, 'graph')                                       # f_235a0: redraw if open


# ------------------------------------------------------------------------------------------- advisor
def advisor(st):
    """f_0e2ea: pick the status-line advice (entries of the message table at G:0360) or clear it."""
    if st.u16(G, 0xeac) == 0:
        raise NotImplementedError('f_0e425 (tutorial advisor)')
    if st.u16(T, 0x7b0) == 0:
        return
    player_in = st.u16(G, 0xa06)
    yh = s16(st.u16(G, 0xf78))
    if player_in == 0 and (s16(st.u16(G, 0xfba)) > yh or yh < 10):
        if yh < 10:
            st.player.effect(st, 'status', 0, 120, 1)                    # the yellow ant is dying
        else:
            st.player.effect(st, 'status', 1, 120, 0)
    elif s16(st.u16(G, 0x10be)) < s16(st.u16(G, 0xffe)):
        st.player.effect(st, 'status', 2, 120, 0)                        # the colony is hungry
    else:
        cap = s16(st.u16(G, 0x224))
        if s16(st.u16(G, 0x330)) <= cap:
            st.player.effect(st, 'status', None, 0, 0)                   # f_2f802: clear
        elif player_in == 0 and st.u16(T, 0xc24) == 0 and cap == 0:
            st.player.effect(st, 'status', 3, 120, 0)
        else:
            st.player.effect(st, 'status', 4, 120, 0)                    # the nest is too small


# ------------------------------------------------------------------------------------------- slow phases
def census_and_advise(st):
    """f_0c20f."""
    co.census(st, lambda m: st.player.effect(st, 'message', m))
    advisor(st)


def slow_phase(st):
    """f_08a78: one of four phases every 32 ticks, by bits 5-6 of the tick."""
    p = (st.u8(G, 0xf08) & 0x60) >> 5
    if p in (0, 2):
        if p == 0:
            ng.compact_surface(st)
        census_and_advise(st)
        history(st)
        ph.diffuse_alarm(st)
    elif p == 1:
        ng.compact_nest(st, ng.BLACK)
        ph.black_nest_markers(st)
        ph.decay_black_nest(st)
        ph.decay_black_trail(st)
    else:
        ng.compact_nest(st, ng.RED)
        ph.red_nest_markers(st)
        ph.decay_red_nest(st)
        ph.decay_red_trail(st)


# ------------------------------------------------------------------------------------------- weather
def drop_object_random(st, i):
    """f_0c3d4: move rain object i to a random cell; on ground it becomes a puddle that wipes the scent."""
    a, b = st.crt_rand_mod(0x80), st.crt_rand_mod(0x40)
    st.set8(G, 0x256 + i, a)
    st.set8(G, 0x2c0 + i, b)
    if st.grid(SURFACE, a, b) >= 0xe:
        return
    st.set_grid(SURFACE, a, b, 0x74)
    k = (a >> 1) * 32 + (b >> 1)
    st.set8(SIM, 0xd09f + k, 0)
    st.set8(SIM, 0xd89f + k, 0)
    for m in (0xe09f, 0xf09f):
        v = st.u8(SIM, m + k)
        st.set8(SIM, m + k, v - 0x14 if v >= 0x14 else 0)
    st.set8(SIM, 0xe89f + k, 0)
    st.set8(0x4da7, k, 0)


def flood_row(st, depth):
    """f_0c4d2: water rises to nest row `depth`: ants there start drowning (state 17), the row's cells turn
    to their flooded variants."""
    for n in (ng.BLACK, ng.RED):
        i = s16(st.u16(G, n['count']))
        while i > 0:
            i -= 1
            t = st.u8(SIM, n['type'] + i)
            if st.u8(SIM, n['y'] + i) == depth and t and 0 < (t & 0x78) >> 3 < 0xc:
                st.set8(SIM, n['state'] + i, 0x11)
    for col in range(0x40):
        for n in (ng.BLACK, ng.RED):
            v = st.grid(n['dirt'], col, depth)
            st.set_grid(n['dirt'], col, depth, 0x4e if v < 0x20 else v + 0x2f)
        st.player.effect(st, 'redraw', 2, col, depth)
        st.player.effect(st, 'redraw', 3, col, depth)


def drain_row(st, depth):
    """f_0c56e: the water recedes from nest row `depth`."""
    for col in range(0x40):
        for n in (ng.BLACK, ng.RED):
            v = st.grid(n['dirt'], col, depth)
            st.set_grid(n['dirt'], col, depth, st.rand(8) if v == 0x4e else v - 0x2f)
        st.player.effect(st, 'redraw', 2, col, depth)
        st.player.effect(st, 'redraw', 3, col, depth)


def weather(st):
    """f_0c22c: rain (G:0352, yard only) grows puddles and floods the nests from below (water level G:0242);
    afterwards the puddles dry and the water drains."""
    yard = st.u16(G, 0xf24) == 0
    if st.u16(G, 0x352) and yard:
        if st.rand(0x32) == 0:
            st.player.effect(st, 'sound', 0x29)
        st.set16(T, 0xc1e, 1)
        if st.rand(10) == 0 and s16(st.u16(G, 0x242)) > 4:
            st.inc16(G, 0x242, -1)
            flood_row(st, s16(st.u16(G, 0x242)))
        for i in range(100):
            a, b = st.u8(G, 0x256 + i), st.u8(G, 0x2c0 + i)
            t = st.grid(SURFACE, a, b)
            if 0x74 <= t < 0x77:
                st.set_grid(SURFACE, a, b, t + 1)
                continue
            if t == 0x77:
                st.set_grid(SURFACE, a, b, st.rand(0xe))
            drop_object_random(st, i)
        return
    if not yard:
        return
    if st.u16(T, 0xc1e) == 1:
        st.set16(T, 0xc1e, 0)
        for i in range(100):
            a, b = st.u8(G, 0x256 + i), st.u8(G, 0x2c0 + i)
            if 0x74 <= st.grid(SURFACE, a, b) <= 0x77:
                st.set_grid(SURFACE, a, b, st.rand(0xe))
    if s16(st.u16(G, 0x242)) < 0x40 and st.rand(10) == 0:
        drain_row(st, s16(st.u16(G, 0x242)))
        st.inc16(G, 0x242)
