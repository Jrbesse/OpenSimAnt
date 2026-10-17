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


# ------------------------------------------------------------------------------------------- bugs + caterpillar
def _in_patch(a, b):
    return 0 <= a <= 0x7f and 0 <= b <= 0x3f


def _cmod(a, b):
    """C remainder (sign of the dividend)."""
    r = abs(a) % b
    return -r if a < 0 else r


def bugs(st):
    """f_0ae4c: three harmless bugs (a G:0EAE, b G:0F00, heading G:0F1A, tile under them G:0F28; drawn as
    T:0C52[heading]) wander over open ground."""
    for k in range(3):
        if st.rand4() == 0:
            continue
        o = k * 2
        if st.rand4() == 0:
            h = (st.u8(G, 0xf1a + o) + st.rand(3) - 1) & 7
            st.set16(G, 0xf1a + o, h)
            st.set_grid(SURFACE, s16(st.u16(G, 0xeae + o)), s16(st.u16(G, 0xf00 + o)), st.u8(T, 0xc52 + h))
        h = st.u16(G, 0xf1a + o)
        a, b = s16(st.u16(G, 0xeae + o)), s16(st.u16(G, 0xf00 + o))
        na, nb = a + st.s8(T, h), b + st.s8(T, 8 + h)
        if _in_patch(na, nb) and st.grid(0x6180, na, nb) == 0 and st.grid(SURFACE, na, nb) < 0x10:
            under = st.grid(SURFACE, na, nb)
            st.set_grid(SURFACE, a, b, st.u8(G, 0xf28 + o))
            st.set16(G, 0xf28 + o, under)
            st.set_grid(SURFACE, na, nb, st.u8(T, 0xc52 + h))
            st.set16(G, 0xeae + o, na)
            st.set16(G, 0xf00 + o, nb)


# caterpillar: active T:0C4C, head a T:0C4E / b T:0C50, heading G:0C3C (0 north/up b-, 1 east a+,
# 2 south b+, 3 west a-), step countdown G:0C36 (moves one cell every 5 calls), tiles under the body in
# the 6-entry ring G:0D9C indexed by the coordinate along the path
CAT_STEP = ((0, -1), (1, 0), (0, 1), (-1, 0))


def _cat_put(st, a, b, v):
    """f_0bcaa."""
    if _in_patch(a, b):
        st.set_grid(SURFACE, a, b, v)


def _cat_ring(st, a, b):
    return 0xd9c + _cmod(a if st.u8(G, 0xc3c) & 1 else b, 6) * 2


def _cat_save(st, a, b):
    """f_0babb."""
    if _in_patch(a, b):
        st.set16(G, _cat_ring(st, a, b), st.grid(SURFACE, a, b))


def _cat_restore(st, a, b):
    """f_0bb47."""
    if _in_patch(a, b):
        st.set_grid(SURFACE, a, b, st.u8(G, _cat_ring(st, a, b)))


def _occ(st, a, b):
    """f_0bcde."""
    return st.grid(0x6180, a, b) if _in_patch(a, b) else 0


def caterpillar_start(st):
    """f_0bb9f: enter from a random point of a random edge."""
    d = st.rand(4)
    st.set16(G, 0xc3c, d)
    if d == 0:
        a, b, t = st.rand(0x80), 0x3f, 0x6c
    elif d == 1:
        a, b, t = 0, st.rand(0x40), 0x6b
    elif d == 2:
        a, b, t = st.rand(0x80), 0, 0x6f
    else:
        a, b, t = 0x7f, st.rand(0x40), 0x68
    st.set16(T, 0xc4e, a)
    st.set16(T, 0xc50, b)
    _cat_save(st, a, b)
    _cat_put(st, a, b, t)


def caterpillar_die(st):
    """f_0bd80: the body turns into food (0x4B) wherever it lay on open ground."""
    d = st.u16(G, 0xc3c)
    a, b = s16(st.u16(T, 0xc4e)), s16(st.u16(T, 0xc50))
    if d > 3:
        return
    sa, sb = CAT_STEP[d]
    for i in range(6):
        x, y = a - sa * i, b - sb * i
        if _in_patch(x, y):                                            # f_0be34
            _cat_restore(st, x, y)
            if st.grid(SURFACE, x, y) < 0x18:
                st.set_grid(SURFACE, x, y, 0x4b)


def caterpillar(st):
    """f_0b6cc (odd ticks, yard only): the bugs, then the caterpillar."""
    if st.u16(G, 0xf24) == 1:
        return
    bugs(st)
    if st.u16(T, 0xc4c) == 0:
        caterpillar_start(st)
        st.set16(T, 0xc4c, 1)
        st.set16(G, 0xc36, 4)
        return
    d = st.u16(G, 0xc3c)
    a, b = s16(st.u16(T, 0xc4e)), s16(st.u16(T, 0xc50))
    if d > 3:
        raise NotImplementedError('caterpillar heading > 3 (uninitialised local in the original)')
    sa, sb = CAT_STEP[d]
    if _occ(st, a + sa, b + sb):                                       # blocked by an ant
        busy = sum(1 for x in range(a - 1, a + 2) for y in range(b - 1, b + 2) if _occ(st, x, y))
        if busy > 5:
            st.set16(T, 0xc4c, 0)
            caterpillar_die(st)
        return
    st.inc16(G, 0xc36, -1)
    n = s16(st.u16(G, 0xc36))
    vert = d in (0, 2)
    if n == 4:
        _cat_restore(st, a - sa * (n + 1), b - sb * (n + 1))          # the tail moves on
    else:
        _cat_put(st, a - sa * (n + 1), b - sb * (n + 1), 0x6d if vert else 0x69)
    _cat_put(st, a - sa * n, b - sb * n, 0x6e if vert else 0x6a)
    if n != 0:
        return
    a, b = a + sa, b + sb
    st.set16(T, 0xc4e, a)
    st.set16(T, 0xc50, b)
    if a < -6 or a > 0x86 or b < -6 or b > 0x45:
        st.set16(T, 0xc4c, 0)
        return
    _cat_save(st, a, b)
    _cat_put(st, a, b, (0x6c, 0x6b, 0x6f, 0x68)[d])
    _cat_put(st, a - sa, b - sb, 0x6d if vert else 0x69)
    st.set16(G, 0xc36, 5)


# ------------------------------------------------------------------------------------------- spider
# position in 1/16 tiles G:0F12 (a) / G:0F34 (b), active G:0F0C, state G:0FB8 (0 resting, 1 walking,
# 2 hunting, 3 eating, 4 fleeing, 5 beaten), heading G:1004, animation G:1042, prey G:0FFC (surface ant,
# -1 the yellow ant, -2 none) whose type is remembered in G:10AE, mode G:06AC (7: hunts any ant within
# ~28 tiles, 8: also lashes out at ants beside it), times beaten G:108A. With G:0A06 == 1 the player
# is the spider (it walks to the cursor G:0F42/0F7E and drags the view, G:047C/048A, along).
SPX, SPY = 0xf12, 0xf34


def _sp_pos(st):
    return s16(st.u16(G, SPX)) >> 4, s16(st.u16(G, SPY)) >> 4


def _sp_step(st, mul, back):
    """Move one step along the heading (T:0994/099C, in 1/16 tiles), mul 1 or 5; animate."""
    h = st.u16(G, 0x1004)
    dx, dy = st.s8(T, 0x994 + h) * mul, st.s8(T, 0x99c + h) * mul
    k = 1 if mul == 1 else 2
    if back:
        dx, dy, k = -dx, -dy, -k
    st.set16(G, SPX, st.u16(G, SPX) + dx)
    st.set16(G, SPY, st.u16(G, SPY) + dy)
    st.set16(G, 0x1042, (st.u16(G, 0x1042) + k) & 0x3ff)


def _sp_turn_random(st):
    st.set16(G, 0x1004, st.s8(T, 0x24 + st.u16(G, 0x1004) * 8 + st.rand(8)))


def _surface_ant_with(st, a, b, t):
    """f_11327(1, a, b, t): index of the surface ant at (a, b) with type t, from the top; -1 if none."""
    i = s16(st.u16(G, 0xd6a))
    while True:
        i -= 1
        if i < 0:
            return i
        if st.u8(SIM, 0xa180 + i) == a and st.u8(SIM, 0xa569 + i) == b and st.u8(SIM, 0xad3b + i) == t:
            return i


def spider_find_prey(st):
    """f_0dbb9."""
    a, b = _sp_pos(st)
    if st.u16(G, 0x6ac) == 7:
        i = s16(st.u16(G, 0xd6a))
        while i > 0:
            i -= 1
            if st.u8(SIM, 0xad3b + i) and co.distance(a, b, st.u8(SIM, 0xa180 + i), st.u8(SIM, 0xa569 + i)) <= 800:
                return i
        if (st.u16(G, 0xa06) == 0 and st.u16(G, 0x48c) == 1
                and co.distance(a, b, s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))) < 0x321):
            return -1
        return -2
    h = st.u16(G, 0x1004)
    x, y = a, b
    for _ in range(20):
        y += st.s8(T, 8 + h)
        x += st.s8(T, h)
        if not _in_patch(x, y) or co.distance(a, b, x, y) > 400:
            break
        o = st.grid(0x6180, x, y)
        if o:
            if o in (0xfe, 0xff):
                return -1
            j = _surface_ant_with(st, x, y, o)
            if j >= 0:
                return j
    return -2


def spider_lash(st):
    """f_0dd40 (mode 8): strike at an ant in the 90-degree cone ahead, up to 12 tiles; 3/4 kill it."""
    base = ((st.u8(G, 0x1004) - 2) & 7) * 0x20
    fa, fb = s16(st.u16(G, SPX)), s16(st.u16(G, SPY))
    res = -1
    for _ in range(2):
        for ang in range(base - 0x20, base + 0x20):
            r = st.rand(0xc) + 1
            x = s16(co._cdiv(co.cos256(ang) * r, 0x7fff) + (fa >> 4))
            y = s16(co._cdiv(co.sin256(ang) * r, 0x7fff) + (fb >> 4))
            if not _in_patch(x, y):
                continue
            o = st.grid(0x6180, x, y)
            if not o:
                continue
            res = _surface_ant_with(st, x, y, o)
            if res < 0:
                continue
            st.player.effect(st, 'spider_strike', x * 16 + 7, y * 16 + 7)
            if st.rand4() == 0:
                return res
            st.set_grid(0x6180, x, y, 0)
            st.set8(SIM, 0xad3b + res, 0)
            sf_place_corpse(st, x, y, o & 0x80)
            return res
    return res


def sf_place_corpse(st, a, b, red):
    from .surface import place_corpse
    place_corpse(st, a, b, red)


def spider_drop_food(st, a, b):
    """f_0c692: a beaten spider leaves food behind."""
    t = st.grid(SURFACE, a, b)
    if st.u16(G, 0xf24) == 1:
        if t > 3:
            if t < 8 or t > 0x17:
                if t < 0x18 or t > 0x26:
                    if t < 0x40:
                        raise NotImplementedError('f_0c73d (spider food on house furniture)')
                    return 0
                st.set_grid(SURFACE, a, b, t + 1)
                st.inc16(G, 0x1040)
                return 1
            t = (t - 8) >> 2
        st.set_grid(SURFACE, a, b, ((t + 6) * 4) & 0xff)
    else:
        if t > 0x4a:
            return 0
        st.set_grid(SURFACE, a, b, 0x48 if t < 0x48 else t + 1)
    st.inc16(G, 0x1040)
    return 1


def _sp_prey_chosen(st, r):
    """L_cefa: start hunting the prey just found."""
    st.set16(G, 0xfb8, 2)
    st.set16(G, 0x10ae, st.u8(SIM, 0xad3b + r) if r >= 0 else 0xff)


def _sp_player_follow(st):
    if st.u16(G, 0xa06) == 1:
        a, b = _sp_pos(st)
        st.set16(G, 0x47c, a)
        st.set16(G, 0x48a, b)
        return True
    return False


def spider(st):
    """f_0ce63."""
    st.set16(G, 0x1072, (st.u16(G, 0x1072) + 1) & 0x3ff)
    a, b = _sp_pos(st)
    state = st.u16(G, 0xfb8)
    if st.u16(G, 0xa06) == 1 and state not in (2, 3):
        _spider_player(st)
        return
    if st.u16(G, 0xf0c) == 0:
        if st.u16(G, 0xeac) == 0 or st.rand(0x12c) != 0:
            return
        st.set16(G, SPX, st.rand(0x400) + 0x200)
        st.set16(G, 0xf0c, 1)
        st.set16(G, 0xfb8, 1)
        st.set16(T, 0xc12, 0)
        if st.rand(2):
            st.set16(G, SPY, 1)
            st.set16(G, 0x1004, 4)
        else:
            st.set16(G, SPY, 0x3ff)
            st.set16(G, 0x1004, 0)
        return
    if st.u8(G, 0x1072) & 3 == 0 and s16(st.u16(G, 0xfb8)) < 5:
        n = sum(1 for x in range(a - 1, a + 3) for y in range(b - 1, b + 3)    # f_0db10: 4x4 (sic)
                if _in_patch(x, y) and st.grid(0x6180, x, y))
        if n > 8:                                                       # swarmed: beaten
            spider_beaten(st)
            if st.u16(G, 0xa06) == 1:
                st.set16(G, 0xa06, 0)
                st.player.spider_event(st, 3)
                return
            st.player.effect(st, 'message', 0x273e)
            if s16(st.u16(G, 0x108a)) < 5:
                st.inc16(G, 0x108a)
            k = s16(st.u16(G, 0x108a))
            if k < 3:
                return
            st.set16(G, 0x6ac, 8 if k >= 5 else 7)
            if k < 6 or st.rand2() != 0:
                return
            st.set16(G, 0x108a, 0)
            st.set16(G, 0x6ac, 0)
            return
        if n > 4:
            st.set16(G, 0xfb8, 4)
    if s16(st.u16(G, 0xfb8)) < 4 and st.u16(G, 0x6ac) == 8:
        spider_lash(st)
    state = st.u16(G, 0xfb8)
    if state == 0:
        st.set16(G, 0x1042, 2)
        if st.rand(0x96) == 0:
            st.set16(G, 0xfb8, 1)
        r = spider_find_prey(st)
        st.set16(G, 0xffc, r)
        if r != -2:
            _sp_prey_chosen(st, r)
            return
        if st.rand(0x1e) == 0:
            _sp_turn_random(st)
        if st.u16(G, 0x6ac) == 8:
            spider_lash(st)
    elif state == 1:
        _sp_step(st, 1, st.u16(T, 0xc12) != 0)
        if st.rand(0x14) == 0:
            _sp_turn_random(st)
        r = spider_find_prey(st)
        st.set16(G, 0xffc, r)
        if r != -2:
            _sp_prey_chosen(st, r)
            return
        _sp_maybe_rest(st)
    elif state == 2:
        if not _spider_hunt(st, a, b):
            return
    elif state == 3:
        if not _spider_eat(st, a, b):
            return
    elif state == 4:
        _sp_turn_random(st)
        _sp_step(st, 5, st.u16(T, 0xc12) != 0)
        _sp_maybe_rest(st)
    elif state == 5:
        st.inc16(G, 0x109a, -1)
        if st.u16(G, 0x109a) == 0:
            st.set16(G, 0xf0c, 0)
            st.set16(G, 0xfb8, 0)
            for _ in range(3):
                spider_drop_food(st, a, b)
            return
        if s16(st.rand(0x3e8)) < s16(st.u16(G, 0x109a)):
            if s16(st.u16(G, 0x109a)) > 0x190:
                st.set16(G, 0x1042, st.rand(3) + 1)
            else:
                st.set16(G, 0x1042, st.rand(2) + 2)
    _spider_tail(st)


def spider_beaten(st):
    """f_0db90."""
    st.set16(G, 0xfb8, 5)
    st.set16(G, 0x109a, 500)
    st.set16(G, 0x1042, 0)


def _sp_maybe_rest(st):
    """0d7cd."""
    if st.rand(0x32) == 0:
        st.set16(G, 0xfb8, 0)
        st.set16(G, 0x1042, 2)


def _spider_tail(st):
    """0da96: leaving the patch (or climbing furniture in the house) ends the visit."""
    a, b = _sp_pos(st)
    if not _in_patch(a, b):
        st.set16(G, 0xf0c, 0)
        if st.u16(G, 0xa06) == 1:
            st.set16(G, 0xa06, 0)
            st.player.spider_event(st, 4)
    if st.u16(G, 0xf24) != 0:
        if st.u8(SIM, 0x180 + ((st.u16(G, SPX) & 0xfff0) << 2) + (s16(st.u16(G, SPY)) >> 4)) > 0x90:
            st.set16(G, 0xf0c, 0)


def _sp_lose_prey(st):
    st.set16(G, 0xfb8, 0)
    st.set16(G, 0xffc, 0xfffe)


def _spider_hunt(st, a, b):
    """State 2 (0d3ee). Returns False when the tick ends without the common tail."""
    p = s16(st.u16(G, 0xffc))
    if p >= 0:
        if (st.u8(SIM, 0xad3b + p) ^ st.u8(G, 0x10ae)) & 0xf0:      # the prey is gone
            _sp_lose_prey(st)
            if st.u16(G, 0xa06) == 1:
                st.set16(G, 0xf7e, b)
                st.set16(G, 0xf42, a)
                st.set16(G, 0x47c, a)
                st.set16(G, 0x48a, b)
                if st.u16(G, 0x6ac) == 6:
                    st.set16(G, 0x6ac, 0)
                st.player.effect(st, 'scroll')
            return False
    elif s16(st.u16(G, 0x48c)) > 1:                                  # the yellow ant went underground
        _sp_lose_prey(st)
        return False
    if p < 0:
        tx, ty = s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    else:
        tx, ty = st.u8(SIM, 0xa180 + p), st.u8(SIM, 0xa569 + p)
    d = abs(tx - a) + abs(ty - b)                                     # f_0dec8
    if d > 0x40 and st.u16(G, 0xa06) != 1:
        _sp_lose_prey(st)
        return False
    if d < 2:                                                         # caught
        st.set16(G, 0xfb8, 3)
        st.set16(G, SPX, (st.u16(G, SPX) & 0xfff0) + 8)
        st.set16(G, SPY, (st.u16(G, SPY) & 0xfff0) + 8)
        return _spider_eat(st, a, b)
    dd = mv_dir_to(a, b, tx, ty)
    st.set16(G, 0x1004, st.s8(T, 0x23 + st.u16(G, 0x1004) * 8 + dd))
    st.player.effect(st, 'sound', 0x2f)
    _sp_step(st, 5, st.u16(T, 0xc12) != 0)
    if _sp_player_follow(st):
        st.player.effect(st, 'scroll')
    _spider_tail(st)
    return False


def mv_dir_to(a, b, ta, tb):
    from .movement import dir_to
    return dir_to(a, b, ta, tb)


def _spider_eat(st, a, b):
    """State 3 (0d526): eat the prey. Returns True to run the common tail."""
    if _sp_player_follow(st):
        if st.u16(G, 0x6ac) == 6:
            st.set16(G, 0x6ac, 0)
        st.player.effect(st, 'scroll')
    p = s16(st.u16(G, 0xffc))
    if p != -2:
        if p < 0:
            h = st.u16(G, 0x1004)
            st.player.spider_eats_player(st, (st.s8(T, 0x9a4 + h) + a) & 0x7f, (st.s8(T, 0x9ac + h) + b) & 0x3f)
            st.set16(G, 0x105a, 0)
        elif (st.u8(G, 0x10ae) ^ st.u8(SIM, 0xad3b + p)) & 0xf0:
            st.set16(G, 0xffc, 0xfffe)
            _sp_done_eating(st, a, b)
            return True
        else:
            if st.u8(G, 0x10ae) & 0x80:
                st.inc32(G, 0xf80)
                st.set16(G, 0x105a, 4)
            else:
                st.inc32(G, 0xf20)
                st.set16(G, 0x105a, 0)
            st.set_grid(0x6180, st.u8(SIM, 0xa180 + p), st.u8(SIM, 0xa569 + p), 0)
            st.set8(SIM, 0xad3b + p, 0)
        st.set16(G, 0xffc, 0xfffe)
        st.set16(G, 0x1054, 0xb if s16(st.u16(G, 0x6ac)) >= 7 else 0x32)
    # 0d95c: chewing in front of the spider leaves a corpse
    h = st.u16(G, 0x1004)
    x = (st.s8(T, 0x9a4 + h) + a) & 0x7f
    y = (st.s8(T, 0x9ac + h) + b) & 0x3f
    if st.u16(G, 0xf24) == 0 and st.grid(SURFACE, x, y) < 0x18:
        st.set_grid(SURFACE, x, y, (st.rand4() + st.u8(G, 0x105a) + 0x10) & 0xff)
    if s16(st.u16(G, 0x1054)) > 0:
        st.inc16(G, 0x1054, -1)
        if s16(st.u16(G, 0x1054)) % 10 == 0 and st.rand2() != 0:
            st.player.effect(st, 'sound', 0x2c, st.rand256())
        return True
    st.inc16(G, 0x1076, -1)
    if st.u16(G, 0x1076) == 0:
        st.set16(G, 0x1076, 10)
        if st.u16(T, 0x7b2) and st.rand2() == 0:
            st.player.effect(st, 'sound', 10)
    sf_place_corpse(st, x, y, st.u16(G, 0x105a))
    _sp_done_eating(st, a, b)
    return True


def _sp_done_eating(st, a, b):
    """0da5c."""
    st.set16(G, 0xfb8, 0)
    if st.u16(G, 0xa06) == 1:
        if st.u16(G, 0x6ac) == 6:
            st.set16(G, 0x6ac, 0)
        st.set16(G, 0xf42, a)
        st.set16(G, 0xf7e, b)


def _spider_player(st):
    """The player is the spider (G:0A06 == 1, not hunting or eating): walk towards the cursor."""
    if st.u16(G, 0x6ac) == 7:
        r = spider_find_prey(st)
        st.set16(G, 0xffc, r)
        if r != -2:
            _sp_prey_chosen(st, r)
            return
    elif st.u16(G, 0x6ac) == 8:
        spider_lash(st)
    pa, pb = s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))
    ta, tb = s16(st.u16(G, 0xf42)), s16(st.u16(G, 0xf7e))
    dist = mv_distance_lo(pa, pb, ta, tb)
    if dist < 1:
        st.set16(G, 0x1042, 2)
        return
    from .surface import step_towards_surface
    d = step_towards_surface(st, pa, pb, ta, tb)
    if d == -1:
        return
    if d == -2:
        d = mv_dir_to(pa, pb, ta, tb) - 1
        if d < 0:
            return
    st.set16(G, 0x1004, st.s8(T, 0x24 + st.u16(G, 0x1004) * 8 + d))
    _sp_step(st, 5 if st.u16(G, 0xa8e) != 0 and dist > 2 else 1, False)
    a, b = _sp_pos(st)
    st.set16(G, 0x47c, a)
    st.set16(G, 0x48a, b)
    st.player.effect(st, 'scroll')


def mv_distance_lo(a1, b1, a2, b2):
    from .movement import distance_lo
    return distance_lo(a1, b1, a2, b2)


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
