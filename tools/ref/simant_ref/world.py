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


# ------------------------------------------------------------------------------------------- tiles
def get_tile(st, a, b):
    """GetTile(1, a, b): surface tile, -1 outside the patch."""
    return st.grid(SURFACE, a, b) if 0 <= a <= 0x7f and 0 <= b <= 0x3f else -1


def set_tile(st, a, b, v):
    """SetTile(1, a, b, v) (f_1183e)."""
    if 0 <= a <= 0x7f and 0 <= b <= 0x3f:
        st.set_grid(SURFACE, a, b, v)
        st.player.effect(st, 'redraw', 1, a, b)


def is_open_ground(st, a, b):
    """IsOpenGround(1, a, b) (f_1145c)."""
    t = get_tile(st, a, b)
    if t < 0:
        return False
    o = st.grid(0x6180, a, b)
    if o and o not in (0xfe, 0xff):
        return False
    return t < 0x10


def is_open_with_ring(st, a, b):
    """IsOpenWithRing(1, a, b) (f_113fe)."""
    return is_open_ground(st, a, b) and all(
        is_open_ground(st, a + st.s8(T, d), b + st.s8(T, 8 + d)) for d in range(8))


def is_food_tile(st, t):
    """TileClass (f_0ad63): food crumbs."""
    return 0x48 <= t <= 0x4b if st.u16(G, 0xf24) == 0 else 0x18 <= t <= 0x27


# ------------------------------------------------------------------------------------------- ant lions
# up to 9 pits (count T:0C4A): a G:0A92, b G:0AA8, state G:0ABA (0 lurking, 1 eating, 2 closing),
# timer G:0ACC, animation frame G:0ADE (tile 0x38 + frame)
LA, LB, LSTATE, LTIMER, LFRAME = 0xa92, 0xaa8, 0xaba, 0xacc, 0xade


def _lion_draw(st, i):
    """f_0b54d."""
    set_tile(st, st.u8(G, LA + i), st.u8(G, LB + i), st.u8(G, LFRAME + i) + 0x38)


def place_lion(st, a, b):
    """f_0b09c: dig a pit (tile 0x38, sand ring around it) and add it to the list."""
    set_tile(st, a, b, 0x38)
    for d in range(8):
        na, nb = st.s8(T, d) + a, st.s8(T, 8 + d) + b
        if is_open_ground(st, na, nb):
            set_tile(st, na, nb, st.u8(0x55b3, 0x1b92 + d) + 0x30)
    i = st.u16(T, 0xc4a)
    st.set8(G, LA + i, a)
    st.set8(G, LB + i, b)
    for f in (LSTATE, LTIMER, LFRAME):
        st.set8(G, f + i, 0)
    if s16(i) < 9:
        st.inc16(T, 0xc4a)


def new_lion(st):
    """f_0b016: up to 200 tries for a spot, preferring open 3x3 ground."""
    for k in range(200):
        a = st.rand(0x41) + st.rand(0x40)
        b = st.rand(0x21) + st.rand(0x20)
        if is_open_with_ring(st, a, b) or (is_open_ground(st, a, b) and k > 99):
            place_lion(st, a, b)
            return


def remove_lion(st, i):
    """f_0b5c8: the pit is filled in (tile 0x3F) and removed from the list."""
    set_tile(st, st.u8(G, LA + i), st.u8(G, LB + i), 0x3f)
    n = s16(st.u16(T, 0xc4a))
    if n > 0:
        st.set16(T, 0xc4a, n - 1)
        for j in range(i, n - 1):
            for f in (LA, LB, LFRAME, LSTATE, LTIMER):
                st.set8(G, f + j, st.u8(G, f + j + 1))


def remove_surface_ant(st, i):
    """f_0ed8f: delete surface ant i, closing the gap in the arrays."""
    st.set_grid(0x6180, st.u8(SIM, 0xa180 + i), st.u8(SIM, 0xa569 + i), 0)
    n = s16(st.u16(G, 0xd6a))
    if n > 0:
        n -= 1
        st.set16(G, 0xd6a, n)
    for base in (0xa180, 0xa569, 0xa952, 0xad3b, 0xb124):
        for j in range(i, i + n - i):
            st.set8(SIM, base + j, st.u8(SIM, base + j + 1))


def ant_lions(st):
    """f_0b163."""
    if st.u16(T, 0xc4a) == 0 and s16(st.u16(G, 0x8ea)) > 0 and st.rand(0x400) == 0:
        new_lion(st)
        return
    i = 0
    while i < s16(st.u16(T, 0xc4a)):
        state = st.u8(G, LSTATE + i)
        a, b = st.u8(G, LA + i), st.u8(G, LB + i)
        if state == 0:
            t = get_tile(st, a, b)
            if (0x51 <= t <= 0x53) or is_food_tile(st, t):           # something lies on the pit
                if st.rand(0x200) == 0:
                    d = st.rand8()
                    for _ in range(8):
                        na, nb = st.s8(T, d) * 2 + a, st.s8(T, 8 + d) * 2 + b
                        if is_open_ground(st, na, nb):
                            set_tile(st, na, nb, t)                    # flung out of the pit
                            st.player.effect(st, 'sound', 0x1e)
                            break
                        d = (d + 1) & 7
                    st.set8(G, LTIMER + i, 0x19)
                    st.set8(G, LSTATE + i, 1)
                    st.set8(G, LFRAME + i, 1)
                    _lion_draw(st, i)
            else:
                k = 0
                for _ in range(2):
                    na, nb = st.s8(T, 0x10 + k) + a, st.s8(T, 0x1a + k) + b
                    o = st.grid(0x6180, na, nb)
                    if o:
                        if o in (0xfe, 0xff):
                            st.player.lion_eats_player(st, a, b)       # f_11a3e + f_2f7d0(2)
                        else:
                            st.rand8()                                 # 1/8: crunch sound (f_00f54)
                            j = sf_surface_ant_at(st, na, nb)
                            if j >= 0:
                                remove_surface_ant(st, j)
                            st.inc32(G, 0xf80 if o & 0x80 else 0xf20)
                        st.set8(G, LTIMER + i, 0x32)
                        st.set8(G, LSTATE + i, 1)
                        st.set8(G, LFRAME + i, 1)
                        _lion_draw(st, i)
                        break
                    k = st.rand(8) + 1
        elif state == 1:
            busy = sum(1 for d in range(8) if st.grid(0x6180, a + st.s8(T, d), b + st.s8(T, 8 + d)))
            if busy >= 7:                                              # swarmed: the ant lion dies
                st.player.effect(st, 'message', 0x2742)
                remove_lion(st, i)
                i += 1
                continue
            f = st.u8(G, LFRAME + i)
            if f < 4:
                st.set8(G, LFRAME + i, f + 1)
            elif st.u8(G, LTIMER + i) == 0:
                st.set8(G, LSTATE + i, 2)
                st.set8(G, LFRAME + i, 4)
            else:
                st.set8(G, LTIMER + i, st.u8(G, LTIMER + i) - 1)
                if st.u8(G, LTIMER + i) & 1:
                    st.set8(G, LFRAME + i, st.rand(4) + 3)
            _lion_draw(st, i)
        elif state == 2:
            f = st.u8(G, LFRAME + i)
            if f:
                st.set8(G, LFRAME + i, f - 1)
            else:
                st.set8(G, LSTATE + i, 0)
                st.inc16(G, 0xa08)
                if s16(st.u16(T, 0xc4a)) < 9 and st.u8(G, 0xa08) & 0xf == 0xf:
                    new_lion(st)
            _lion_draw(st, i)
        i += 1


def sf_surface_ant_at(st, a, b):
    from .movement import surface_ant_at
    return surface_ant_at(st, a, b)


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
