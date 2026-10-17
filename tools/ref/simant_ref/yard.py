"""The yard layer (sec8 f_68513, segment 783a), run every tick by SimStep: the human walking through or
roaming the yard (with the lawnmower), foot stamps on the player's patch, the bird crossing and the bird,
the dog, rain, and the colonies of the other 191 patches of the yard.

The yard is 12 x 16 patches (col G:07CA, row G:07CC is the player's); per-patch colony strengths are
T:00A4[col*16 + row] (black) and T:0164[...] (red), 0..0xFA. Screen coordinates of the yard map turn
into patches as col = (x + y - 0xC8) / 28, row = (y - 0x26) / 10 (C division).
Sounds, music and messages go to st.player.effect; hits on the player to st.player.yard_event.
"""
from .state import SIM, G, T, DS
from . import colony as co
from . import world
from .movement import surface_ant_at, s16
from .surface import place_corpse

OCC, STYPE = 0x6180, 0xad3b
_cdiv, _cmod = co._cdiv, world._cmod


def _sound_on(st):
    return st.u16(T, 0x7c8) == 0 and s16(st.u16(G, 0x35c)) < 2


def human_sound(st, n):
    """f_6856a: queue the human's sound / speech bubble n (shown until clock3() + 300)."""
    if s16(n) <= 0x16:
        st.set32(G, 0x109c, (st.clock3() + 300) & 0xffffffff)
        st.set16(G, 0x10b0, 1)
        st.set16(G, 0x10bc, n)


def yard_step(st):
    """f_68513."""
    st.inc16(G, 0x7c2)
    if s16(st.u16(G, 0x7c2)) >= 0x400:
        st.set16(G, 0x7c2, 0)
    if s16(st.u16(T, 0xc48)) < 0x26:
        human_walk(st)
    else:
        human_roam(st)
    bird_crossing(st)
    bird(st)
    if st.u16(T, 0xc44) == 0:
        dog(st)
    rain_control(st)
    yard_colonies(st)


# ------------------------------------------------------------------------------------------- the human
# T:0C48 script state (< 0x26 scripted walk, 0x26 roaming), T:0C46 frame counter, T:0C2C / T:0C2E position on
# the yard map, T:0C32 sprite, T:0C30 heading (0 up, 1 right, 2 down, 3 left; bit 0 picks the foot's shape),
# T:0C28 roaming mode, T:0C3E foot on the player's patch, T:0C42 alternating foot, G:0246 / G:023E patch
# (col / row), G:0202 mowing
WALK_FRAMES = {
    0: (0x2474, 0x2478, 0x247c), 1: (0x2480, 0x2484, 0x2488), 2: (0x248c, 0x24a0, 0x24b4),
    3: (0x24c8, 0x24dc, 0x24f0), 4: (0x2504, 0x2508, 0x250c), 5: (0x2510, 0x2514, 0x2518),
    6: (0x251c, 0x2528, 0x2534), 7: (0x2540, 0x254c, 0x2558), 8: (0x2564, 0x256a, 0x2570),
    9: (0x2576, 0x257c, 0x2582), 10: (0x2588, 0x258c, 0x2590), 11: (0x2594, 0x2598, 0x259c),
    12: (0x25a0, 0x25a6, 0x25ac), 13: (0x25b2, 0x25b8, 0x25be), 14: (0x25c4, 0x25c8, 0x25cc),
    15: (0x25d0, 0x25d4, 0x25d8),
}


def _walk_frame(st, c48):
    """The jump table at flat 0x68F39 (and the 0x1E..0x26 scripted states): sprite, x, y."""
    c46 = st.u16(T, 0xc46)
    if c48 < 0x1e:
        if c48 in WALK_FRAMES:
            s, x, y = WALK_FRAMES[c48]
            return st.u8(DS, s + c46), st.u8(DS, x + c46), st.u8(DS, y + c46)
        if c48 == 20:
            return st.u16(DS, 0x25dc + c46 * 2), st.u8(DS, 0x25ec + c46), st.u8(DS, 0x25f4 + c46)
        if c48 == 21:
            return st.u16(DS, 0x25fc + c46 * 2), st.u8(DS, 0x2606 + c46), st.u8(DS, 0x260c + c46)
        raise NotImplementedError(f'human_walk state {c48} (uninitialised locals in the original)')
    if c48 >= 0x27:
        raise NotImplementedError(f'human_walk state {c48} (uninitialised locals in the original)')
    d = c48 - 0x1e
    frame = st.u16(DS, 0x2654 + d * 2), st.u8(DS, 0x2666 + d), st.u8(DS, 0x2670 + d)
    n = st.u8(DS, 0x267a + d)
    if n == 0:
        raise NotImplementedError(f'human_walk state {c48}: Rand(0) (division by zero in the original)')
    if st.rand(n) == 0:
        st.set16(T, 0xc48, st.u8(DS, 0x2684 + d))
        st.set16(T, 0xc46, 0)
    return frame


def _patch_of(x, y):
    v = s16(x + y - 0xc8)
    return v, _cdiv(v, 28), _cdiv(s16(y - 0x26), 10)


def _foot_spot(st, v, y):
    """Where on the player's patch the foot lands (G:03E0 a, G:046A b), before the +-6 nudge."""
    r10 = _cmod(s16(y - 0x26), 10)
    st.set16(G, 0x46a, r10)
    st.set16(G, 0x3e0, (_cmod(v, 28) * 4 + 6) & 0x7f)
    st.set16(G, 0x46a, ((r10 + 1) * 6) & 0x3f)


def _foot_nudge(st):
    d = 6 if st.u16(T, 0xc42) else -6
    off = 0x46a if st.u8(T, 0xc30) & 1 else 0x3e0
    st.set16(G, off, st.u16(G, off) + d)


def human_walk(st):
    """f_68e30: the scripted human walking through the yard."""
    if st.u16(T, 0xc44) == 1:
        return
    c48 = s16(st.u16(T, 0xc48))
    if c48 < 0x1e:
        st.inc16(T, 0xc46)
        if st.s8(DS, 0x245e + c48) < s16(st.u16(T, 0xc46)):
            st.set16(T, 0xc46, 0)
            c48 = st.u8(DS, (0x2612, 0x2628, 0x263e)[st.rand(3)] + c48)
            st.set16(T, 0xc48, c48)
            n = None
            if c48 == 0x21:
                n = 0x14
            elif c48 == 6:
                n = 0x15
            elif c48 == 7:
                n = 0x16
            elif c48 == 0xe:
                n = st.rand(3) + 0xf
            elif c48 == 0x10:
                n = st.rand(2) + 0x12
            if n is not None:
                human_sound(st, n)
    si, x, y = _walk_frame(st, s16(st.u16(T, 0xc48)))
    c48 = s16(st.u16(T, 0xc48))
    c46 = s16(st.u16(T, 0xc46))
    st.set16(T, 0xc28, 0)
    if c48 == 0x26:
        st.set16(T, 0xc30, 1)
        st.set16(T, 0xc28, 1)
    if c48 == 0x14 and c46 > 2:
        st.set16(T, 0xc28, 1)
    if c48 == 0x15 and c46 < 3:
        st.set16(T, 0xc28, 1)
    st.set16(T, 0xc2c, x)
    st.set16(T, 0xc2e, y)
    st.set16(T, 0xc32, si)
    if _sound_on(st) and (c46, c48, si) in ((3, 0x14, 0x384), (1, 0x15, 0x387), (6, 0x14, 6), (3, 0x15, 1)):
        st.player.effect(st, 'sound', 0x18)
    v, col, row = _patch_of(x, y)
    st.set16(G, 0x246, col)
    st.set16(T, 0xc3e, 0)
    st.set16(T, 0xc42, 1 if st.u16(T, 0xc42) == 0 else 0)
    st.set16(G, 0x23e, row)
    pcol = st.u16(G, 0x7ca)
    idx = (pcol * 16 + st.u16(G, 0x7cc)) & 0xffff
    if (row & 0xffff) != st.u16(G, 0x7cc) or pcol != (col & 0xffff) or idx in (0, 1, 0x10, 0x20):
        return
    s = s16(st.u16(T, 0xc32))
    st.set16(T, 0xc30, st.u8(DS, 0x268e + s) if 0 <= s < 12 else 2)
    st.set16(T, 0xc3e, 1)
    _foot_spot(st, v, y)
    _foot_nudge(st)
    foot_stamp(st, s16(st.u16(G, 0x3e0)), s16(st.u16(G, 0x46a)))
    st.player.effect(st, 'sound', 9)
    i = 0
    while s16(((st.u16(G, 0x330) + st.u16(G, 0x350)) << 3) & 0xffff) > i:   # random ants all over the patch
        a, b = st.rand128(), st.rand64()
        if st.grid(OCC, a, b):
            j = surface_ant_at(st, a, b)
            st.set16(G, 0xf18, j)
            if j >= 0:
                place_corpse(st, a, b, st.u8(SIM, STYPE + j) & 0x80)
                st.set8(SIM, STYPE + st.u16(G, 0xf18), 0)
                st.set_grid(OCC, a, b, 0)
        if s16(st.u16(G, 0xf12)) >> 4 == a and s16(st.u16(G, 0xf34)) >> 4 == b:
            world.spider_beaten(st)
        i += 1
    if st.u16(G, 0xeac) == 2 and st.u16(G, 0x48c) == 1 and st.rand4() == 0:
        st.player.yard_event(st, 9)


def foot_stamp(st, x, y):
    """f_69f53: everything under the foot (16 x 6 or 6 x 16 cells from (x, y)) dies."""
    st.player.effect(st, 'sound', 0x23)
    xe, ye = (x + 16, y + 6) if st.u8(T, 0xc30) & 1 else (x + 6, y + 16)
    for a in range(x, xe):
        for b in range(y, ye):
            if not (0 <= a <= 0x7f and 0 <= b <= 0x7f):                # (sic: b up to 0x7F)
                continue
            o = st.u8(SIM, OCC + a * 64 + b)
            if not o:
                continue
            if o in (0xfe, 0xff):
                st.player.yard_event(st, 5)
                continue
            j = surface_ant_at(st, a, b)
            if j >= 0:
                place_corpse(st, a, b, st.u8(SIM, STYPE + j) & 0x80)
                st.set8(SIM, STYPE + j, 0)
    if x <= s16(st.u16(G, 0xf42)) < xe and y <= s16(st.u16(G, 0xf7e)) < ye:
        world.spider_beaten(st)
        if st.u16(G, 0xa06) == 1:
            st.player.yard_event(st, 5)


def _in_yard(col, row):
    """f_68dd2."""
    return 0 <= col <= 0xb and 0 <= row <= 0xf


def _take_mow_bit(st, col, row):
    """f_68d97: the mowing mask (word G:0334[col], bit row); clears the bit it finds."""
    bit = 1 << row
    w = st.u16(G, 0x334 + col * 2)
    if w & bit:
        st.set16(G, 0x334 + col * 2, w - bit)
        return True
    return False


def mow_heading(st, col, row):
    """f_68d07: head for an unmown neighbouring patch."""
    for d in range(3, -1, -1):
        c, r = col + st.s8(DS, 0x26b2 + d), row + st.s8(DS, 0x26b6 + d)
        if _in_yard(c, r) and _take_mow_bit(st, c, r):
            return d
    if col > 0xa:
        return 0
    if row > 0xe:
        return 1
    if row < 1:
        human_sound(st, 6)
        st.set16(T, 0xc28, 4)
        return 2
    return st.u8(G, 0x7c2) & 3


def mow_reset(st):
    """f_68dff: everything from column 3 on needs mowing."""
    for c in range(3):
        st.set16(G, 0x334 + c * 2, 0)
    for c in range(3, 12):
        st.set16(G, 0x334 + c * 2, 0xffff)


def _steer(st, row_mid, col_max):
    """Head for the house corner: rows above/below row_mid, then left. True when there."""
    row = s16(st.u16(G, 0x23e))
    if row < row_mid:
        st.set16(T, 0xc30, 2)
    elif row > row_mid:
        st.set16(T, 0xc30, 0)
    elif s16(st.u16(G, 0x246)) > col_max:
        st.set16(T, 0xc30, 3)
    else:
        return True
    return False


def human_roam(st):
    """f_68659: the human (and the lawnmower) wandering the yard."""
    if st.u16(T, 0xc3e) != 0 and st.u8(G, 0x7c2) & 3:
        return
    if st.u16(G, 0x202):
        if st.u16(G, 0x246) != st.u16(G, 0x488) or st.u16(G, 0x23e) != st.u16(G, 0x492):
            st.set16(T, 0xc30, mow_heading(st, s16(st.u16(G, 0x246)), s16(st.u16(G, 0x23e))))
    else:
        st.inc16(T, 0xc34, -1)
        if s16(st.u16(T, 0xc34)) < 0:
            st.set16(T, 0xc30, (st.rand(3) + st.u8(T, 0xc30) - 1) & 3)
            st.set16(T, 0xc34, 4)
    mode = st.u16(T, 0xc28)
    if mode == 1:
        if st.rand(900) == 0:
            human_sound(st, 1)
            st.set16(T, 0xc28, 2)
        elif st.rand(600) == 0 or st.u16(G, 0xeac) in (0, 3):
            human_sound(st, 2)
            st.set16(T, 0xc28, 5)
        else:
            if st.rand(200) == 0:
                human_sound(st, st.rand(8) + 7)
            if st.u16(G, 0x352):
                st.set16(T, 0xc28, 5)
    elif mode == 2:
        if _steer(st, 12, 3):
            st.set16(T, 0xc28, 3)
            st.set16(G, 0x488, 3)
            st.set16(G, 0x492, 13)
            st.set16(G, 0x202, 1)
            mow_reset(st)
            st.set16(T, 0xc30, 2)
            st.set16(T, 0xc2c, 0x7d)
            st.set16(T, 0xc2e, 0xaa)
    elif mode == 3:
        if st.rand(100) == 0:
            human_sound(st, st.rand(3) + 3)
        if st.rand(200) == 0:
            human_sound(st, 6)
            st.set16(T, 0xc28, 4)
        st.set16(G, 0x488, st.u16(G, 0x246))
        st.set16(G, 0x492, st.u16(G, 0x23e))
        st.set16(G, 0x202, 1)
    elif mode == 4:
        if _steer(st, 12, 3):
            st.set16(T, 0xc28, 5)
            st.set16(G, 0x202, 0)
        st.set16(G, 0x488, st.u16(G, 0x246))
        st.set16(G, 0x492, st.u16(G, 0x23e))
    elif mode == 5:
        if _steer(st, 5, 3):
            st.set16(T, 0xc28, 1)
    c30 = st.u16(T, 0xc30)
    st.set16(T, 0xc32, st.s8(DS, 0x269e + c30) + st.s8(DS, 0x269a + (st.u8(G, 0x7c2) & 3)))
    mowing = st.u16(G, 0x202) != 0
    if mowing or st.u16(T, 0xc40) == 0:
        if mowing:
            st.inc16(T, 0xc32, 100)
        elif st.rand32() == 0:
            st.set16(T, 0xc40, 20)                                     # stop for a while
        st.inc16(T, 0xc2c, st.s8(T, 0xc36 + c30))
        st.inc16(T, 0xc2e, st.s8(T, 0xc3a + c30))
    else:
        st.inc16(T, 0xc40, -1)
        st.set16(T, 0xc32, c30 + 20)                                   # standing
    x, y = st.u16(T, 0xc2c), st.u16(T, 0xc2e)
    v, col, row = _patch_of(x, y)
    row = min(max(row, 0), 0xf)
    col = min(max(col, 0), 0xb)
    st.set16(G, 0x246, col)
    st.set16(G, 0x23e, row)
    if not mowing:                                                     # keep to the yard, away from the house
        if row < 1:
            st.set16(T, 0xc30, 2)
        elif row > 0xe:
            st.set16(T, 0xc30, 0)
        if col > 0xa:
            st.set16(T, 0xc30, 3)
        elif row < 5:
            if col < 4:
                st.set16(T, 0xc30, 1)
        elif col < 3:
            st.set16(T, 0xc30, 0)
            if row < 6:
                if st.u16(T, 0xc28) == 3:
                    st.set16(T, 0xc30, 1)
                else:
                    st.set16(T, 0xc48, 0x15)
    st.set16(T, 0xc3e, 0)
    st.set16(T, 0xc42, 1 if st.u16(T, 0xc42) == 0 else 0)
    if st.u16(G, 0x7cc) == row and st.u16(G, 0x7ca) == col:
        st.set16(T, 0xc3e, 1)
        _foot_spot(st, v, s16(y))
        c30 = st.u16(T, 0xc30)
        st.set16(G, 0x470, st.u16(G, 0x3e0) + st.u16(DS, 0x26a2 + (c30 & 3) * 2))
        st.set16(G, 0x47a, st.u16(G, 0x46a) + st.u16(DS, 0x26aa + (c30 & 3) * 2))
        _foot_nudge(st)
        foot_stamp(st, s16(st.u16(G, 0x3e0)), s16(st.u16(G, 0x46a)))
        if mowing:
            mower(st)
    elif mowing:                                                       # mowing another patch thins its colonies
        idx = col * 16 + row
        for base, dead in ((0xa4, 0xa9e), (0x164, 0xac8)):
            c = st.u8(T, base + idx)
            if c:
                c -= c >> 2
                if c == 0:
                    st.inc16(G, dead)
                st.set8(T, base + idx, c)


def mower(st):
    """f_6a08a (its position args G:0470 / G:047A are unused): the lawnmower over the player's patch."""
    if st.u16(G, 0xeac) == 0:
        return
    i = s16(st.u16(G, 0xd6a))
    while i > 0:
        i -= 1
        if st.u8(SIM, STYPE + i) and st.rand4():
            st.set_grid(OCC, st.u8(SIM, 0xa180 + i), st.u8(SIM, 0xa569 + i), 0)
            st.set8(SIM, STYPE + i, 0)
    if st.u16(G, 0xf0c) and st.rand4():
        world.spider_beaten(st)
    if s16(st.u16(G, 0xa06)) <= 1 and st.u16(G, 0x48c) == 1 and st.rand4():
        st.player.yard_event(st, 6)


# ------------------------------------------------------------------------------------------- birds
def bird_crossing(st):
    """f_6959f: a bird flies across the yard map (state G:10A0, x G:10AC, y G:10BA); while queens are out on
    their mating flight it dives at the player's patch (G:0208 / G:0210) and eats some of them."""
    state = st.u16(G, 0x10a0)
    if state == 0:
        now = st.u32(G, 0x383a)
        if _s32(now) <= _s32(st.u32(G, 0x107e)):
            return
        st.set32(G, 0x107e, (now + 20) & 0xffffffff)
        if s16(st.u16(G, 0x7ca)) < 5 or st.rand2() != 0:
            return
        if s16(st.u16(G, 0x6aa)) <= 0 and s16(st.u16(G, 0x73a)) <= 0:
            return
        col, row = s16(st.u16(G, 0x7ca)), s16(st.u16(G, 0x7cc))
        st.set16(G, 0x208, col * 28 - row * 10 + 0xb2)
        st.set16(G, 0x210, row * 10 + 0x2e)
        st.set16(G, 0x10a0, 1)
        st.set16(G, 0x10ac, 0)
        st.set16(G, 0x10ba, st.rand64() + 4)
        st.set16(G, 0x108c, 0)
        return
    st.inc16(G, 0x10ac, 16 if state == 1 else 8)
    if state == 1:
        d = s16(st.u16(G, 0x210) - st.u16(G, 0x10ba))
        if d:
            step = 4 if abs(d) >= 4 else 1
            st.inc16(G, 0x10ba, step if d > 0 else -step)
    else:
        st.inc16(G, 0x10ba, -8)
    st.set16(G, 0x108c, (st.u8(G, 0x108c) + 1) & 1)
    x, y = s16(st.u16(G, 0x10ac)), s16(st.u16(G, 0x10ba))
    if x < 0 or x > 0x1ff or y < 0 or y > 0xff:
        st.set16(G, 0x10a0, 0)
        st.set32(G, 0x107e, (st.u32(G, 0x383a) + 30) & 0xffffffff)
        return
    ty = s16(st.u16(G, 0x210))
    if state != 1 or s16(st.u16(G, 0x208)) > x or not (ty - 4 <= y <= ty + 4):
        return
    for off in (0x6aa, 0x7c8, 0x73a, 0x850):                         # flying queens / new colonies eaten
        c = s16(st.u16(G, off))
        if c > 0:
            st.set16(G, off, c - ((c + 7) >> 3))
    if _sound_on(st) and st.rand2() == 0:
        st.player.effect(st, 'sound', 7)
    st.set16(G, 0x10a0, 2)


def _s32(v):
    return v - 0x100000000 if v & 0x80000000 else v


def bird(st):
    """f_6986c: the bird on the yard map (state G:0254, x G:02BE, y G:032C, heading G:0240, frame G:0244,
    timer G:022C); it may land when the dog sits, and swoops at the dog when close. (The yard window draws
    this actor with the cat frames, bitmaps 1300 + G:0244 (f_7004e): it is the cat; the name is kept.)"""
    state = st.u16(G, 0x254)
    if state == 0:
        if _s32(st.u32(G, 0x220)) >= _s32(st.clock3()):
            return
        st.set32(G, 0x220, (st.clock3() + 200) & 0xffffffff)
        if st.rand16() == 0 or st.u16(G, 0xb20) == 0x8d:
            st.set16(G, 0x254, 1)
            st.set16(G, 0x2be, 0xfc)
            st.set16(G, 0x32c, 0x19)
            st.set16(G, 0x240, 2)
            st.set16(G, 0x244, 0)
            st.set16(G, 0x22c, 0)
        return
    st.set16(G, 0x22c, (st.u16(G, 0x22c) + 1) & 0xfff)
    if state == 1:
        h = st.u16(G, 0x240)
        nx = s16(st.s8(T, h) * 4 + st.u16(G, 0x2be))
        ny = st.s8(T, 8 + h) * 4 + st.u16(G, 0x32c)
        if st.rand16() == 0 or nx < 0xfc or nx > 0x1ef:                # turn around
            if h == 2:
                st.set16(G, 0x240, 6)
                st.set16(G, 0x244, 4)
            else:
                st.set16(G, 0x240, 2)
                st.set16(G, 0x244, 1)
        else:
            st.set16(G, 0x2be, nx)
            st.set16(G, 0x32c, ny)
            st.inc16(G, 0x244)
            f = s16(st.u16(G, 0x244))
            if h == 2:
                if f >= 3:
                    st.set16(G, 0x244, 1)
            elif f >= 6:
                st.set16(G, 0x244, 4)
        if _sound_on(st) and st.rand64() == 0:
            st.player.effect(st, 'sound', 0xd)
            return
        if (st.rand16() == 0 and s16(st.u16(G, 0x22c)) > 100 and st.u16(G, 0x506) == 2
                and st.u16(T, 0xc28) == 0):
            st.set16(G, 0x254, 2)                                      # lands
            st.set16(G, 0x22c, 0)
            st.set16(G, 0x244, 10)
            return
        if s16(st.u16(G, 0x22c)) <= 0x32:
            return
        d = co.distance(s16(st.u16(G, 0x2be)), s16(st.u16(G, 0x32c)), s16(st.u16(G, 0x4be)),
                        s16(st.u16(G, 0x4c6)))
        if d <= 0x960:
            st.set16(G, 0x254, 3)                                      # swoops at the dog
            st.set16(G, 0x244, 0x14)
            if _sound_on(st):
                st.player.effect(st, 'sound', 0xe)
    elif state == 2:
        st.inc16(G, 0x244)
        if s16(st.u16(G, 0x244)) >= 0xd:
            st.set16(G, 0x244, 0xb)
        st.inc16(G, 0x22c)
        if s16(st.u16(G, 0x22c)) > 0x1e:
            st.set16(G, 0x22c, 0)
            st.set16(G, 0x254, 1)
            st.set16(G, 0x244, 0 if st.u16(G, 0x240) == 2 else 3)
    else:
        st.inc16(G, 0x244)
        if s16(st.u16(G, 0x244)) >= 0x1e:
            st.set16(G, 0x244, 0)
            st.set16(G, 0x254, 0)
            st.set32(G, 0x220, (st.clock3() + 600) & 0xffffffff)


# ------------------------------------------------------------------------------------------- the dog
def bark(st, p, vol):
    """f_69ea8."""
    if not _sound_on(st):
        return
    if _s32(st.u32(G, 0x736)) >= _s32(st.clock3()):
        return
    if p in (0, 1, 2, 3):
        st.player.effect(st, 'sound', (0x17, 0x15, 0x17, 0x16)[p], vol)
    st.set32(G, 0x736, (st.clock3() + st.rand(30) + 60) & 0xffffffff)


def _dog_home(st):
    """f_69e5f: back towards the house while the bird is about."""
    col = s16(st.u16(G, 0x510))
    if col < 5:
        return 1
    if col > 8:
        return 3
    if s16(st.u16(G, 0x59e)) > 0:
        return 0
    return st.u8(G, 0x7c2) & 3


def _dog_chase(st):
    """f_69daf: follow the human (barking at the mower)."""
    dr = s16(st.u16(G, 0x59e) - st.u16(G, 0x23e))
    dc = s16(st.u16(G, 0x510) - st.u16(G, 0x246))
    if abs(dc) < 1 and abs(dr) < 1 and st.u16(G, 0x202):
        bark(st, 1, 0x7f)
    if abs(dc) >= 2 or abs(dr) >= 2:
        if dr < 0:
            return 2
        if dr > 1:
            return 0
        if dc < 0:
            return 1
        if dc > 1:
            return 3
    return st.u8(G, 0x7c2) & 3


def dog(st):
    """f_69ba3: the dog (heading G:0506: 0..3 walking, 4/5 sitting; x G:04BE, y G:04C6, sprite G:04E4,
    patch G:0510 / G:059E, turn timer G:0624)."""
    st.inc16(G, 0x624, -1)
    if s16(st.u16(G, 0x624)) < 0:
        if st.u16(G, 0x254):
            h = _dog_home(st)
        elif s16(st.u16(T, 0xc48)) < 0x26:
            h = (st.rand(3) + st.u8(G, 0x506) - 1) & 3
        else:
            h = _dog_chase(st)
        st.set16(G, 0x506, h)
        st.set16(G, 0x624, 4)
    if st.u16(G, 0x506) == 1 and st.rand(10) == 0:
        st.set16(G, 0x506, st.rand2() + 4)                             # sits down
        st.set16(G, 0x624, 6)
    h = st.u16(G, 0x506)
    if s16(h) > 3:
        st.set16(G, 0x4e4, st.s8(DS, 0x2458 + h) + (st.u8(G, 0x7c2) & 1))
    else:
        st.set16(G, 0x4e4, st.s8(DS, 0x2458 + h) + st.s8(DS, 0x2454 + (st.u8(G, 0x7c2) & 3)))
    st.inc16(G, 0x4c6, st.s8(DS, 0x244e + h))
    y = s16(st.u16(G, 0x4c6))
    row = _cdiv(s16(y - 0x26), 10)
    st.set16(G, 0x59e, row)
    st.inc16(G, 0x4be, st.s8(DS, 0x2448 + h))
    st.set16(G, 0x510, _cdiv(s16(st.u16(G, 0x4be) + y - 0xc8), 28))
    if row < 0:
        st.set16(G, 0x59e, 0)
    if s16(st.u16(G, 0x59e)) > 0xf:
        st.set16(G, 0x59e, 0xf)
    if s16(st.u16(G, 0x510)) < 0:
        st.set16(G, 0x510, 0)
    if s16(st.u16(G, 0x510)) > 0xb:
        st.set16(G, 0x510, 0xb)
    if s16(st.u16(G, 0x59e)) < 1:
        st.set16(G, 0x506, 2)
    elif s16(st.u16(G, 0x59e)) > 0xe:
        st.set16(G, 0x506, 0)
    if s16(st.u16(G, 0x510)) > 0xa:
        st.set16(G, 0x506, 3)
    elif s16(st.u16(G, 0x510)) < 4:
        st.set16(G, 0x506, 1)
    if 0x64 <= s16(st.u16(G, 0x4e4)) <= 0x67 and st.rand(6) == 0:
        bark(st, st.rand4(), 5)


# ------------------------------------------------------------------------------------------- rain
def rain_control(st):
    """f_685ac (yard only): start rain now and then (G:0352, length G:0356), stop it when it runs out."""
    if st.u16(G, 0xf24) == 1:
        return
    if st.u16(G, 0x352) == 0:
        if st.u16(G, 0xb20) == 0xa8 or (st.crt_rand_mod(0x20) == 0 and st.crt_rand_mod(0x80) == 0):
            st.set16(G, 0x352, 1)
            st.set16(G, 0x356, st.rand(150) + 150)
            for i in range(100):                                       # f_0c4ba
                world.drop_object_random(st, i)
            human_sound(st, 0)
        return
    if s16(st.u16(G, 0x356)) > 0:
        st.inc16(G, 0x356, -1)
    if s16(st.u16(G, 0x356)) < 1:
        st.set16(G, 0x352, 0)


# ------------------------------------------------------------------------------------------- yard colonies
BLACK_PATCH, RED_PATCH = 0xa4, 0x164


def _decay_flown(st, flown, new):
    c = s16(st.u16(G, flown))
    if c > 0:
        c = c - (c >> 2) if c >= 4 else c - 1
    c = max(c, s16(st.u16(G, new)))
    st.set16(G, flown, min(c, 50))


def _neighbour_bias(st, col, row):
    """f_6a6b4: +3 per black, -3 per red colony among the neighbours (offsets read as unsigned bytes, so
    only (1, 0), (0, 1) and the patch itself, twice, count)."""
    adj = 0
    for d in range(6):
        c = col + st.u8(DS, 0x26ba + d)
        r = row + st.u8(DS, 0x26c0 + d)
        if c & 0x8000 or r < 0 or c >= 0xc or r >= 0x10:
            continue
        if st.u8(T, BLACK_PATCH + c * 16 + r):
            adj += 3
        if st.u8(T, RED_PATCH + c * 16 + r):
            adj -= 3
    return adj


def new_colony(st, col, row, red):
    """f_6a721: a colony founded near (col, row); nothing if the spot is the patch itself."""
    def off():                                                         # f_00984
        m = st.rand_low(4)
        return -m if st.rand2() else m
    c = min(max(off() + col, 0), 0xb)
    r = min(max(off() + row, 0), 0xf)
    if (c, r) == (col, row):
        return
    a = (RED_PATCH if red else BLACK_PATCH) + c * 16 + r
    v = st.u8(T, a)
    if v == 0:
        st.inc16(G, 0xac4 if red else 0xa90)
    st.set8(T, a, v + 1)


def yard_colonies(st):
    """f_6a1f4, every 32 yard ticks: the colonies of the other patches grow or shrink with their neighbours
    and found new ones; the player's colonies' new queens settle nearby; the Full Game's end."""
    if st.u8(G, 0x7c2) & 0x1f:
        return
    st.set16(T, 0xc20, 1)
    _decay_flown(st, 0x6aa, 0x7c8)
    _decay_flown(st, 0x73a, 0x850)
    st.set16(G, 0x3e2, 0)
    st.set16(G, 0x400, 0)
    st.set16(G, 0x478, 0)
    if s16(st.u16(G, 0x330)) > 0:
        st.set16(G, 0x3e2, 1)
    if s16(st.u16(G, 0x350)) > 0:
        st.set16(G, 0x400, 1)
    pcol, prow = st.u16(G, 0x7ca), st.u16(G, 0x7cc)
    here = (pcol * 16 + prow) & 0xffff
    st.set8(T, BLACK_PATCH + here, min(st.u16(G, 0x330) & 0x3ff, 0xfa))
    st.set8(T, RED_PATCH + here, min(st.u16(G, 0x350) & 0x3ff, 0xfa))
    full = st.u16(G, 0xeac) == 2
    col = 0
    while col < 12:
        row = 0
        while row < 16:
            if (col, row) == (pcol, prow):
                row += 1
                continue
            idx = col * 16 + row
            red = st.u8(T, RED_PATCH + idx)
            black = st.u8(T, BLACK_PATCH + idx)
            if black == 0 and red == 0:
                row += 1
                continue
            if full and (col < 2 or (col == 3 and row < 5)):
                st.inc16(G, 0x478)                                     # colonies near the house
            adj = _neighbour_bias(st, col, row)
            if black:
                st.inc16(G, 0x3e2)
                black += adj if adj else 1
                if black <= 0:
                    st.inc16(G, 0xa9e)
                    st.set8(T, BLACK_PATCH + idx, 0)
                elif black < 0xfa:
                    st.set8(T, BLACK_PATCH + idx, black)
                else:
                    st.set8(T, BLACK_PATCH + idx, 0xfa)
                    if st.rand(10) == 0:
                        new_colony(st, col, row, 0)
            if red:
                st.inc16(G, 0x400)
                red = red - adj if adj else red + 1
                if red <= 0:
                    st.inc16(G, 0xac8)
                    st.set8(T, RED_PATCH + idx, 0)
                    if col == 0xb:
                        row = 8
                        st.set8(T, 0x184 + st.rand(6) * 16, 0x14)
                elif red < 0xfa:
                    st.set8(T, RED_PATCH + idx, red)
                else:
                    st.set8(T, RED_PATCH + idx, 0xfa)
                    if st.rand(10) == 0:
                        new_colony(st, col, row, 1)
            row += 1
        col += 1
    if st.u16(T, 0x2c0) == 1:
        st.inc16(G, 0x105c)
        if st.rand8() + 10 < s16(st.u16(G, 0x105c)):
            st.set16(G, 0x105c, 0)
            while s16(st.u16(G, 0x7c8)) > 0:                           # the black queens settle nearby
                new_colony(st, s16(st.u16(G, 0x7ca)), s16(st.u16(G, 0x7cc)), 0)
                st.inc16(G, 0x7c8, -1)
    st.inc16(G, 0x1066)
    if st.rand8() + 10 < s16(st.u16(G, 0x1066)):
        st.set16(G, 0x1066, 0)
        while s16(st.u16(G, 0x850)) > 0:
            new_colony(st, s16(st.u16(G, 0x7ca)), s16(st.u16(G, 0x7cc)), 1)
            st.inc16(G, 0x850, -1)
    if not full:
        return
    if st.u16(G, 0x400) == 0 and st.u16(G, 0x36e) != 0:
        st.player.effect(st, 'music', 0x4e22)
        st.player.effect(st, 'message', 0x2744)                       # the reds are gone from the yard
        if st.u16(T, 0xc44) == 0:
            st.player.effect(st, 'message', 0x2747)
    st.set16(G, 0x364, st.u16(G, 0x3e2))
    st.set16(G, 0x36e, st.u16(G, 0x400))
    if st.u16(T, 0xc44) == 0 and s16(st.u16(G, 0x478)) > 0x18:     # the human moves in
        st.set16(T, 0xc44, 1)
        st.set16(T, 0xc48, 0)
        st.set16(T, 0xc28, 0)
        st.set16(T, 0xc32, 0xffff)
        st.player.effect(st, 'music', 0x4e23)
        st.player.effect(st, 'message', 0x2746)
        if st.u16(G, 0x400):
            st.player.effect(st, 'message', 0x2745)
    if st.u16(T, 0xc44) and st.u16(G, 0x400) == 0:                    # won the Full Game
        st.player.effect(st, 'music', 0x4e25)
        st.player.effect(st, 'message', 0x2749)
        st.set16(G, 0x376, 1)
        st.set16(G, 0x366, 1)
        st.player.win_screen(st)
        return
    if (s16(st.u16(G, 0x3e2)) < 2 and st.u16(G, 0xaf6) == 0 and st.u16(G, 0xaec) == 0
            and st.u16(G, 0xaf2) == 0 and st.u16(G, 0xaf4) == 0):
        st.set16(G, 0x376, 1)                                          # lost the Full Game
        st.set16(G, 0x366, 0)
        st.player.effect(st, 'message', 0x2748)
