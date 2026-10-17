"""Colony-level bookkeeping: health, food drops, census, statistics, priorities, caste and job choice.

Ported from SIMANT.EXE (addresses in docstrings are flat linear addresses in tools/re/build/flat.bin).
"""
import math

from .state import SIM, G, T

SURFACE, OCC = 0x0180, 0x6180
S_TYPE, S_STATE, S_E = 0xad3b, 0xa952, 0xb124
B_TYPE, R_TYPE = 0xbaec, 0xc4b5

# quarter-wave sine table: int(32767*sin(i*pi/128)) (the original loads it from a resource; identical values)
SINE = [int(32767 * math.sin(i * math.pi / 128)) for i in range(64)]


def _s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def _cdiv(a, b):
    """C (MSC) signed integer division: truncates toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def sin256(ang):
    """f_6bc37: sine for an angle 0..255 (256 = full turn), scaled to +-32767."""
    x = ang & 0x7f
    if x > 0x3f:
        x = 0x80 - x
    v = 0x7fff if x == 0x40 else SINE[x & 0x3f]
    return -v if (ang & 0xff) > 0x7f else v


def cos256(ang):
    """f_6bc8b."""
    return sin256(ang + 0x40)


def distance(a1, b1, a2, b2):
    """f_0ca03: squared distance (32-bit). Callers usually look at the low word only."""
    return ((b2 - b1) * (b2 - b1) + (a2 - a1) * (a2 - a1)) & 0xffffffff


def drop_food(st, count, sound):
    """f_6bca5: scatter `count` food crumbs in a disc. count < 0: start-of-game drop (200 crumbs)."""
    if count < 0:
        a0 = 0x40
        b0 = st.rand(0x30) + 8
        count = 200
    else:
        a0 = st.rand128()
        b0 = st.rand64()
    st.set16(T, 0x2bc, a0)
    st.set16(T, 0x2be, b0)
    r = st.rand8() + 5
    for _ in range(count):
        ang = st.rand256()
        rad = st.rand(r)
        a = _s16(_cdiv(cos256(ang) * rad, 0x7fff) + a0)
        b = _s16(_cdiv(sin256(ang) * rad, 0x7fff) + b0)
        if not (0 <= a <= 0x7f and 0 <= b <= 0x3f):
            continue
        if st.grid(OCC, a, b):
            continue
        t = st.grid(SURFACE, a, b)
        if st.u16(G, 0xf24):
            # house floors: crumbs are 0x18..0x27, four sizes per floor kind
            if t < 4:
                st.set_grid(SURFACE, a, b, (t + 6) << 2)                 # (sic: cl still holds 6)
            elif t < 0x18:
                st.set_grid(SURFACE, a, b, ((t - 8) & 0xfc) + 0x18)
            elif t < 0x28 and t % 4 < 3:
                st.set_grid(SURFACE, a, b, t + 1)
            else:
                continue
        elif t < 0x18:
            st.set_grid(SURFACE, a, b, 0x48)
        elif 0x48 <= t < 0x4b:
            st.set_grid(SURFACE, a, b, t + 1)
        else:
            continue
        st.inc16(G, 0x1040)


def health_decay(st):
    """f_08c12 (every 64 ticks)."""
    if st.u16(T, 0xc18) == 0:
        v = _s16(st.u16(G, 0x10be) - 1)
        st.set16(G, 0x10be, v if v >= 0 else 0)
    v = _s16(st.u16(G, 0x1fe) - 1)
    st.set16(G, 0x1fe, v if v >= 0 else 0)
    if st.u16(G, 0xeac) != 3 and _s16(st.u16(G, 0x1040)) < _s16(st.u16(T, 0xc1a)):
        drop_food(st, 0x96, 1)
        st.set16(T, 0xc1a, st.rand(0x32) + 1)


def reset_census(st):
    """f_08adb: clear per-state counts; count down the two flight timers."""
    for i in range(20):
        st.set16(G, 0xd40 + 2 * i, 0)
        st.set16(G, 0xd72 + 2 * i, 0)
    for off in (0x8dc, 0x8e8):
        if st.u16(G, off):
            st.set16(G, off, st.u16(G, off) - 1)


def spawn_avenger(st):
    """f_0def0: if black has >= 30 ants, the last red surface ant becomes the Avenger (state 19)."""
    st.set16(T, 0xc1c, 0)
    if _s16(st.u16(G, 0x330)) < 0x1e:
        return
    i = _s16(st.u16(G, 0xd6a))
    while i > 0:
        i -= 1
        if st.u8(SIM, S_TYPE + i) > 0x7f:
            st.set8(SIM, S_TYPE + i, 0xb0)
            st.set8(SIM, S_STATE + i, 0x13)
            st.set8(SIM, S_E + i, 0)
            st.set16(G, 0x4a4, 0)
            st.set16(T, 0xc1c, 1)
            return


def stats_from_census(st):
    """f_08b25: history-graph job counts from the per-state census."""
    c = lambda base, s: st.u16(G, base + 2 * s)
    for base, out in ((0xd40, 0xb12), (0xd72, 0xc2a)):
        st.set16(G, out + 0, c(base, 2) + c(base, 3))      # foragers: Foraging + Got Food
        st.set16(G, out + 2, c(base, 4) + c(base, 5))      # diggers: Dig In + Dig Out
        st.set16(G, out + 4, c(base, 1))                    # nurses: Nesting
        st.set16(G, out + 6, c(base, 7))                    # attackers
        st.set16(G, out + 8, c(base, 12))                   # nest defenders
        st.set16(G, out + 10, c(base, 6))                   # guards / recruits
    if _s16(st.u16(G, 0xd98)) < 1:                          # no red Avenger
        spawn_avenger(st)


def census(st, show_message):
    """f_0be82: count every ant by caste, derive populations, detect dead queens / game over.
    show_message(string_id) is called for the messages the original pops up."""
    for i in range(32):
        st.set16(G, 0xeb6 + 2 * i, 0)
    st.set16(G, 0xafa, 0)
    st.set16(G, 0xaec, 0)
    for count_off, type_base in ((0xd6a, S_TYPE), (0xda8, B_TYPE), (0xeaa, R_TYPE)):
        i = _s16(st.u16(G, count_off))
        while i > 0:
            i -= 1
            t = st.u8(SIM, type_base + i)
            if t:
                st.inc16(G, 0xeb6 + ((t & 0xfb) >> 2))
    if st.u16(G, 0xa06) == 0:                               # count the yellow ant too
        t = st.u16(G, 0x4c2) & 0xfffb
        if st.u16(G, 0x4e2):
            t |= 0x80
        st.inc16(G, 0xeb6 + (t >> 2))
    k = lambda caste: st.u16(G, 0xeb6 + 2 * caste)
    st.set16(G, 0xaec, k(0))
    st.set16(G, 0xaee, k(1) + k(2) + k(3) + k(5))
    st.set16(G, 0xaf0, k(6) + k(7) + k(9))
    st.set16(G, 0xaf2, k(4))
    st.set16(G, 0xaf4, k(8))
    if st.u16(G, 0xaf6) and k(12) == 0 and st.u16(G, 0x354) == 0:
        show_message(10010)                                 # the black queen has died
        if _s16(st.u16(G, 0xeac)) <= 1:
            show_message(10011)                             # defeated by the reds
            st.set16(G, 0x376, 1)
            st.set16(G, 0x366, 0)
    st.set16(G, 0xaf6, k(12))
    st.set16(G, 0xafa, k(16))
    st.set16(G, 0xafc, k(18) + k(19) + k(21) + k(17))     # red workers (castes 2, 3, 5, 1)
    st.set16(G, 0xafe, k(23) + k(22) + k(25))             # red soldiers (7, 6, 9)
    st.set16(G, 0xb00, k(20))                             # red males
    st.set16(G, 0xb02, k(24))                             # red new queens
    if st.u16(G, 0xb04):
        if st.u16(G, 0xeee) == 0 and st.u16(G, 0x354) == 0:
            show_message(10012)                             # the red queen has died
            if _s16(st.u16(G, 0xeac)) <= 1:
                show_message(10013)                         # you have won
                st.set16(G, 0x376, 1)
                st.set16(G, 0x366, 1)
            if (st.u16(G, 0xeac) == 2 and st.u16(G, 0x400) == 1 and st.u16(G, 0x7ca) == 0xb
                    and st.u16(G, 0x7cc) == 8):
                st.set8(T, 0x184 + st.rand(6) * 16, 0x14)
    st.set16(G, 0x330, (st.u16(G, 0xaf2) + st.u16(G, 0xaee) + st.u16(G, 0xaf0) + st.u16(G, 0xaf4)
                        + st.u16(G, 0xaf6)) & 0xffff)
    st.set16(G, 0xb04, st.u16(G, 0xeee))
    st.set16(G, 0x350, (st.u16(G, 0xb04) + st.u16(G, 0xb02) + st.u16(G, 0xafc) + st.u16(G, 0xb00)
                        + st.u16(G, 0xafe)) & 0xffff)
    st.set16(G, 0x354, 0)


def black_priority(st):
    """f_1395b: colony priority row 0..5 for the black colony (see SIM_NOTES)."""
    health = _s16(st.u16(G, 0x10be))
    pb, pr = _s16(st.u16(G, 0x330)), _s16(st.u16(G, 0x350))
    if health < 10 and (pb >> 1) > pr and pr > 0 and _s16(st.u16(G, 0x36c)) > 0:
        return 0
    if health < 0x1e:
        return 5
    if health < 0x32:
        return 4
    cap = _s16(st.u16(G, 0x224))
    if pb > cap:
        return 3
    if _s16(pb * 2) > cap:
        return 2
    if pb > 0x64 and pr > 0 and _s16(st.u16(G, 0x36c)) > 0 and _cdiv(pb, 3) > pr:
        return 0
    return 1


def red_launch_attack(st, show_status):
    """f_13d35."""
    st.set16(G, 0x504, st.rand(0x64) + 0x1e)
    show_status(1020, 5)          # "The red ants are attacking!" in the status line (UI)


def red_priority(st, show_status):
    """f_13be3: colony priority row for the red colony; also starts red mating flights and raids."""
    if st.u16(G, 0x8e8) == 0 and _s16(st.u16(G, 0xb00) + st.u16(G, 0xb02)) > 0x14:
        st.set16(G, 0x8e8, 0xc8)
    if st.u16(G, 0x504):
        st.set16(G, 0x504, st.u16(G, 0x504) - 1)
        return 0
    health = _s16(st.u16(G, 0x1fe))
    pr, pb = _s16(st.u16(G, 0x350)), _s16(st.u16(G, 0x330))
    if health < 10 and (pr >> 1) > pb and pb > 0 and _s16(st.u16(G, 0x35e)) > 0:
        red_launch_attack(st, show_status)
        return 0
    if health < 0x1e:
        return 5
    if health < 0x32:
        return 4
    cap = _s16(st.u16(G, 0x232))
    if pr > cap:
        return 3
    if _s16(pr * 2) > cap:
        return 2
    if pr > 0x64 and pb > 0 and _s16(st.u16(G, 0x35e)) > 0 and _cdiv(pr, 3) > pb:
        red_launch_attack(st, show_status)
        return 0
    if st.rand32() == 0 and pr > 0x14 and pr > pb and st.rand128() == 0:
        red_launch_attack(st, show_status)
        return 0
    return 1


def choose_hatch_caste(st):
    """f_13a28: next hatchling joins the caste group furthest below the caste-triangle target."""
    counts = [_s16(st.u16(G, 0xaee + 2 * i)) for i in range(4)]
    targets = [_s16(st.u16(T, 0x7da + 2 * i)) for i in range(4)]
    tot, ttot = _s16(sum(counts)), _s16(sum(targets))
    best, idx = 0, 0
    for i in range(4):
        actual = _s16(_cdiv(100 * counts[i], tot)) if tot > 0 else 0
        want = _s16(_cdiv(100 * targets[i], ttot)) if ttot > 0 else 0
        d = _s16(actual - want)
        if d < best:
            best, idx = d, i
    st.set16(T, 0xc0e, st.u16(T, 0xb66 + 2 * idx))


def choose_manual_job(st):
    """f_13b26: in manual mode, the most understaffed of forage / dig / nurse."""
    cur = [_s16(st.u16(G, 0xb12 + 2 * i)) for i in range(3)]
    tot = _s16(sum(cur))
    best, idx = 0, 0
    for i in range(3):
        w = st.u16(G, 0x49e + 2 * i)
        want = _s16(((w * tot) & 0xffffffff) // 0xffff) if tot >= 0 else _s16(_cdiv(w * tot, 0xffff))
        d = _s16(want - cur[i])
        if d > best:
            best, idx = d, i
    st.set16(T, 0xc10, st.u16(T, 0xb6e + 2 * idx))


def colony_advisor(st, show_status):
    """f_13832 (every tick): recruit guard point, priorities, caste and job choice."""
    st.set16(G, 0x248, 0)
    if st.u16(G, 0x48c) == 1:
        ga = _s16(st.rand(5) + st.u16(G, 0x47c) - 2)
        st.set16(G, 0x22a, ga)
        gb = _s16(st.rand(5) + st.u16(G, 0x48a) - 2)
        st.set16(G, 0x238, gb)
        if _s16(st.u16(G, 0x22a)) < 0:
            st.set16(G, 0x22a, 0)
        if _s16(st.u16(G, 0x22a)) > 0x7f:
            st.set16(G, 0x22a, 0x7f)
        if _s16(st.u16(G, 0x238)) < 0:
            st.set16(G, 0x238, 0)
        if _s16(st.u16(G, 0x238)) > 0x3f:
            st.set16(G, 0x238, 0x3f)
        if st.u16(G, 0xf0c):
            d = distance(_s16(st.u16(G, 0xf12)) >> 4, _s16(st.u16(G, 0xf34)) >> 4,
                         st.u16(G, 0x47c), st.u16(G, 0x48a))
            if _s16(d) < 0x64:
                st.set16(G, 0x248, 1)
    st.set16(G, 0x22a, st.u16(G, 0x47c))      # (overwrites the jittered value: original behaviour)
    st.set16(G, 0x1094, black_priority(st))
    st.set16(G, 0x10a6, red_priority(st, show_status))
    choose_hatch_caste(st)
    choose_manual_job(st)
