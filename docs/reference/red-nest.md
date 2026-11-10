---
layout: default
title: "Red nest ants"
permalink: /reference/red-nest/
---

# Red nest ants

*`red_nest.py` — A separate copy of the nest AI, with its own rules.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `red_nest.py`]({{ site.baseurl }}/assets/reference/simant_ref/red_nest.py)

The red colony (`f_0f3f8..f_10e27`, resident segment `1f3f`) is not the black nest with a colour flag: it is a second implementation with different rules — no Defense job inside, nurses that only shuffle brood, hatching into a caste picked from the red priority, diggers that can break through into the black nest, and different fight and invader handling.

- Both nests are stepped in the same tick, so the order black-then-red is part of the result.
- Red diggers breaking through is a terrain merge between two grids that were separate until that moment.
- The `n_invader_*` handlers only exist here — the black nest's invader path is different code.

## At a glance

- **505** lines
- **26 top-level functions**, including `_job`, `_health`, `egg_cost`, `fight_at`, `_enter`, `queen_move`, `queen_head_lost`, `queen_tail_lost` …
- **Original routines referenced:** `f_0f3f8`, `f_0f465`, `f_0f7a0`, `f_0f871`, `f_0f959`, `f_0f9de`, `f_0fa8a`, `f_0fb71`, `f_0fbdd`, `f_0fce6`, `f_0fe16`, `f_0ff0f` …

## Source

{% raw %}
```python
"""Red nest ants: the per-tick loop and state handlers (SIMANT.EXE resident segment 1f3f, f_0f3f8..f_10e27).

The red nest code is a separate copy of the black one with its own rules: no Defense job inside, nurses
only shuffle brood around, brood hatch into a caste picked from the red priority, diggers can break through
into the black nest, and fights / invader handling differ in detail. Nest helpers shared with the black
nest (movement, digging, food, leaving) are in nest.py and take the colony as a parameter.
"""
from .state import SIM, G, T, DS
from . import movement as mv
from . import nestgrid as ng
from . import nest as bn
from . import surface as sf

N = bn.RED
DIRT, EXITF, CELLS = N['dirt'], N['exitf'], N['cells']
RX, RY, RSTATE, RTYPE, RE = N['x'], N['y'], N['state'], N['type'], N['e']
s16 = mv.s16
_cur, _get, _set = bn._cur, bn._get, bn._set


def _job(st, caste):
    """f_14260: StateForCaste for a red ant."""
    return mv.state_for_caste(st, caste, 0x80)


def _health(st):
    return s16(st.u16(G, 0x1fe))


def egg_cost(st):
    """f_1082c (unlike the black one, not gated by T:0c18)."""
    st.inc16(G, 0x226, -1)
    if s16(st.u16(G, 0x226)) < 0:
        st.set16(G, 0x226, s16(st.u16(G, 0x350)) >> 5)
        if _health(st) > 0:
            st.inc16(G, 0x1fe, -1)


def fight_at(st, col, depth, t):
    """f_0fce6: fight a black ant (castes 1..12, not brood) or the black-side yellow ant here. 1 if so."""
    o = st.grid(CELLS, col, depth)
    if o < 8 or o > 0x67:
        if not mv.is_yellow(o) or st.u16(G, 0x4e2) != 0:
            return 0
        st.player.attack_player(st, 3, _cur(st))
        return 1
    i = bn.nest_ant_at(st, N, col, depth, o)
    if i < 0:
        return 0
    w = sf.resolve_fight(st, o, t & 0xff)
    _set(st, RE, i, w)
    nt = ((w & 0x80) + 0x70) & 0xff
    _set(st, RTYPE, i, nt)
    st.set_grid(CELLS, col, depth, nt)
    _set(st, RSTATE, i, 10)
    return 1


def _enter(st, col, depth, c, r, d, nt):
    """Step into (c, r) unless a fight breaks out there. False = fought."""
    st.set_grid(CELLS, col, depth, 0)
    if fight_at(st, c, r, nt):
        return False
    cur = _cur(st)
    v = (_get(st, RTYPE, cur) & 0xf8) | d
    _set(st, RTYPE, cur, v)
    st.set_grid(CELLS, c, r, v)
    _set(st, RX, cur, c)
    _set(st, RY, cur, r)
    return True


# ------------------------------------------------------------------------------------------- queen
def queen_move(st, col, depth, t):
    """f_1010b: as the black QueenMove, towards the red centroid."""
    d = bn.step_towards_nest(st, N, col, depth, s16(st.u16(G, 0x200)), s16(st.u16(G, 0x20e)))
    if d < 0:
        if d == -1:
            return 0
        d = st.rand8()
    if (depth > 2 or 2 < d < 6) and bn.move_to(st, N, col, depth, d):
        back = (t ^ 0xfc) & 7
        c, r = mv.dx(st, back) + col, mv.dy(st, back) + depth
        st.set_grid(CELLS, c, r, 0)
        i = bn.nest_ant_at(st, N, c, r, (t & 7) + 0xe8)
        if i >= 0 and _get(st, RTYPE, i):
            _set(st, RX, i, col)
            _set(st, RY, i, depth)
            _set(st, RTYPE, i, (d + 0xe8) & 0xff)
            st.set_grid(CELLS, col, depth, (d + 0xe8) & 0xff)
        return 1
    return 0


def queen_head_lost(st, col, depth, t):
    """f_10345."""
    back = (t ^ 0xfc) & 7
    c, r = mv.dx(st, back) + col, mv.dy(st, back) + depth
    return st.grid(CELLS, c, r) != t + 8 and bn.nest_ant_at(st, N, c, r, t + 8) < 0


def queen_tail_lost(st, col, depth, t):
    """f_102d4."""
    c, r = mv.dx(st, t & 7) + col, mv.dy(st, t & 7) + depth
    return st.grid(CELLS, c, r) != t - 8 and bn.nest_ant_at(st, N, c, r, t - 8) < 0


def add_abdomen(st, i):
    """f_10220."""
    t = _get(st, RTYPE, i)
    back = (t & 7) ^ 4
    ng.add_nest_ant(st, N, mv.dx(st, back) + _get(st, RX, i), mv.dy(st, back) + _get(st, RY, i),
                    (t + 8) & 0xff, 9, 0)


def remove_ant(st, i):
    """f_1028e."""
    _set(st, RTYPE, i, 0)
    st.set_grid(CELLS, _get(st, RX, i), _get(st, RY, i), 0)


# ------------------------------------------------------------------------------------------- handlers
def n_wander(st, col, depth, t, caste):
    """f_0fb71 (Bored, Pre-Flight and states > 17)."""
    if st.rand32() == 0:
        _set(st, RSTATE, _cur(st), _job(st, caste))
    if fight_at(st, col, depth, t) == 0:
        bn._move_or_random(st, N, col, depth, t & 7)


def n_nesting(st, col, depth, t, caste):
    """f_10491: red nurses put brood (always stage 2) down on open tunnel cells and pick brood up."""
    cur = _cur(st)
    d = t & 7
    if caste == 1:
        if st.rand4() == 0 and st.grid(DIRT, col, depth) < 0x10:
            _set(st, RTYPE, cur, _get(st, RTYPE, cur) + 8)
            st.set_grid(CELLS, col, depth, _get(st, RTYPE, cur))
            bn.spawn_brood(st, N, col, depth, 0x82)
            _set(st, RE, cur, 0)
            _set(st, RSTATE, cur, _job(st, 1))
            return
        if st.rand4() != 0:
            d = bn.step_dir(st, N, col, depth, d)
            if d >= 0:
                bn._move_or_random(st, N, col, depth, d)
                return
    elif caste != 2:
        _set(st, RSTATE, cur, _job(st, caste))
        bn._move_or_random(st, N, col, depth, d)
        return
    else:
        if st.rand4() == 0:
            o = st.grid(CELLS, col, depth)
            if o == 0 or (o & 0x7f) > 7:
                if s16(st.rand(100)) > _health(st):
                    bn.eat_if_on_food(st, N, col, depth)
                else:
                    _set(st, RSTATE, cur, _job(st, 2))
            else:
                i = bn.nest_ant_at(st, N, col, depth, o)
                if i >= 0:
                    _set(st, RTYPE, i, 0)
                    _set(st, RTYPE, cur, _get(st, RTYPE, cur) - 8)
                    return
        if st.rand4() != 0:
            bn._move_or_random(st, N, col, depth, d)
            return
    bn._move_or_random(st, N, col, depth, st.rand8())


def n_got_food(st, col, depth, t):
    """f_10864: as the black one, but no eating on the way and fights decided by the red rules."""
    d = bn.step_dir(st, N, col, depth, t & 7)
    if d < 0 or st.rand16() == 0:
        bn.store_food(st, N, col, depth)
        if s16(st.rand(100)) > _health(st):
            bn.eat_food(st, N, col, depth)
        _set(st, RSTATE, _cur(st), _job(st, (t & 0x78) >> 3))
        return
    nt = bn._turn_to(st, N, col, depth, t, d)
    c, r = col + mv.dx(st, d), depth + mv.dy(st, d)
    if c > 0x3f or c < 0 or r > 0x3f:
        return
    if r < 1:
        bn.exit_to_surface(st, N, col)
        return
    if st.grid(DIRT, c, r) >= 0x30:
        return
    _enter(st, col, depth, c, r, d, nt)


def n_dig_in(st, col, depth, t, caste):
    """f_109ec: as the black Dig In; a failed dig makes the ant Bored, it eats where it was, and stepping
    onto a 0x14 cell (where deep black digging broke through) sends it into the black nest as an invader."""
    cur = _cur(st)
    if caste not in (2, 6):
        _set(st, RSTATE, cur, _job(st, caste))
        return
    d = bn.step_dir(st, N, col, depth, t & 7)
    if d < 0:
        d = st.rand8()
    nt = bn._turn_to(st, N, col, depth, t, d)
    if depth == 0x3f:
        _set(st, RSTATE, cur, _job(st, caste))
        return
    r, c = depth + mv.dy(st, d), col + mv.dx(st, d)
    if c > 0x3f or c < 0 or r > 0x3f:
        return
    if r < 1:
        bn.exit_to_surface(st, N, col)
        return
    tile = st.grid(DIRT, c, r)
    if tile > 0x2f:
        return
    if ng.is_diggable(tile):
        if not bn.dig_cell(st, N, c, r):
            _set(st, RSTATE, cur, 0)
            return
        _set(st, RTYPE, cur, _get(st, RTYPE, cur) + 0x18)
        _set(st, RSTATE, cur, 5)
        st.player.effect(st, 'sound', 0x12)
    if not _enter(st, col, depth, c, r, d, nt):
        return
    v = _get(st, RTYPE, cur)
    if s16(st.rand64()) > _health(st):
        bn.eat_if_on_food(st, N, col, depth)
    if st.rand4() == 0:
        ng.update_exit_field(st, N, c, r)
    if st.grid(DIRT, c, r) != 0x14:
        return
    _set(st, RTYPE, cur, 0)
    st.set_grid(CELLS, c, r, 0)
    nt = (st.rand8() + (0x90 if (v & 0x7f) < 0x30 else 0xb0)) & 0xff
    ng.add_nest_ant(st, bn.BLACK, c, r, nt, 3, 0)
    st.set_grid(bn.CELLS, c, r, nt)


def n_go_to_surface(st, col, depth, t):
    """f_10c5b: as the black one (eats at the cell it left; the dead-end counter does not wrap)."""
    c1 = bn.climb_dir(st, N, col, depth, t & 7)
    d = mv.turn_aside(st, t & 7) if c1 < 1 else c1 - 1
    nt = bn._turn_to(st, N, col, depth, t, d)
    c, r = col + mv.dx(st, d), depth + mv.dy(st, d)
    if not (0 <= c < 0x40 and r < 0x40):
        return
    if r < 1:
        bn.exit_to_surface(st, N, col)
        return
    tile = st.grid(DIRT, c, r)
    if tile < 0x30:
        if not ng.is_diggable(tile) and _enter(st, col, depth, c, r, d, nt):
            if s16(st.rand64()) > _health(st):
                bn.eat_if_on_food(st, N, col, depth)
        return
    v = st.grid(EXITF, col, depth)
    if v:
        st.set_grid(EXITF, col, depth, v - 1)
    caste = (t & 0x78) >> 3
    cur = _cur(st)
    if caste in (5, 9):
        _set(st, RTYPE, cur, _get(st, RTYPE, cur) - 0x18)
        _set(st, RSTATE, cur, 4)
    if caste in (2, 6):
        _set(st, RSTATE, cur, 4)


def n_brood(st, col, depth):
    """f_0fe16: red brood never die of neglect; the hatch caste comes from T:0b36[priority % 7][Rand8]."""
    cur = _cur(st)
    t = _get(st, RTYPE, cur)
    caste = -1
    mask = 0x1f if st.u16(G, 0x350) == 1 else 0x7f
    if st.u16(G, 0xf08) & mask == 0:
        t += 1
        if t & 0xf == 8:
            r = st.rand8()
            p = s16(st.u16(G, 0x10a6))
            caste = st.s8(T, 0xb36 + (p - int(p / 7) * 7) * 8 + r)
            t = caste * 8 + 0x82
            _set(st, RSTATE, cur, _job(st, caste))
    if st.u16(T, 0x7b2) and caste < 0:
        st.player.effect(st, 'brood', col, depth, 3)
    st.set_grid(CELLS, col, depth, t & 0xff)
    _set(st, RTYPE, cur, t & 0xff)
    _set(st, RE, cur, 0)


def n_egg_laying(st, col, depth, caste, t):
    """f_0ff0f: as the black queen (no eggs-laid counter)."""
    cur = _cur(st)
    if caste == 12:
        if st.rand64() == 0:
            if st.u16(G, 0x1fe) == 0:
                _set(st, RTYPE, cur, 0)
                st.set_grid(CELLS, col, depth, 0)
                st.player.effect(st, 'message', 0x1093, 0, 0x2720, 1)     # f_2f6ea: the red queen starved
                return
            if queen_move(st, col, depth, t):
                return
        v = _get(st, RTYPE, cur)
        if queen_head_lost(st, col, depth, v):
            v = 0
            _set(st, RTYPE, cur, 0)
            st.inc16(G, 0x36c, -1)
        st.set_grid(CELLS, col, depth, v)
        if st.u16(T, 0x7b2):
            st.player.effect(st, 'queen', col, depth, 3)
        return
    if caste != 13:
        return
    v = _get(st, RTYPE, cur)
    st.set_grid(CELLS, col, depth, v)
    if s16(st.u16(G, 0x36c)) > 0 and queen_tail_lost(st, col, depth, v):
        st.inc16(G, 0x36c, -1)
        _set(st, RTYPE, cur, 0)
        st.set_grid(CELLS, col, depth, 0)
        return
    back = (t ^ 0xfc) & 7
    r, c = mv.dy(st, back) + depth, mv.dx(st, back) + col
    if not bn.nest_cell_free(c, r):
        return
    st.set16(T, 0x2b8, c)
    st.set16(T, 0x2ba, r)
    if st.u16(G, 0xf08) & 0xf:
        return
    if s16(st.rand128()) > _health(st):
        return
    bn.spawn_brood(st, N, c, r, 0x81)
    egg_cost(st)


def n_fighting(st, col, depth):
    """f_0fbdd: like the black one; a black winner becomes Attack, a red one takes its job from DS:1ba2."""
    cur = _cur(st)
    j = st.rand(7)
    _set(st, RTYPE, cur, ((_get(st, RTYPE, cur) & 0xf8) + j) & 0xff)
    st.set_grid(CELLS, col, depth, _get(st, RTYPE, cur))
    if st.rand16() == 0:
        w = _get(st, RE, cur)
        st.set_grid(CELLS, col, depth, w)
        _set(st, RTYPE, cur, w)
        if w & 0x78 == 0x60:
            add_abdomen(st, cur)
        w = _get(st, RTYPE, cur)
        _set(st, RSTATE, cur, st.u8(DS, 0x1ba2 + ((w & 0x78) >> 3)) if w & 0x80 else 7)
    elif st.u16(T, 0x7b2):
        st.player.effect(st, 'fight', col, depth, 3)


def n_resting(st, col, depth, t):
    """f_0f9de."""
    if fight_at(st, col, depth, t):
        return
    cur = _cur(st)
    st.set_grid(CELLS, col, depth, _get(st, RTYPE, cur))
    if st.rand(20) == 0:
        b = _get(st, RTYPE, cur)
        _set(st, RSTATE, cur, mv.state_for_caste(st, (b & 0x78) >> 3, b))
    elif st.u16(T, 0x7b2):
        st.player.effect(st, 'rest', col, depth, 3)


def n_state17(st, col, depth, t):
    """f_0fa8a."""
    cur = _cur(st)
    if st.grid(DIRT, col, depth) < 0x14:
        _set(st, RSTATE, cur, _job(st, (t & 0x78) >> 3))
        return
    nt = (((st.rand(3) + t - 1) & 7) | (t & 0xf8)) & 0xff
    _set(st, RTYPE, cur, nt)
    st.set_grid(CELLS, col, depth, nt)
    if st.rand(100) == 0:
        st.set_grid(CELLS, col, depth, 0)
        _set(st, RTYPE, cur, 0)
        st.inc32(G, 0xfbc if t & 0x80 else 0xf30)


# ------------------------------------------------------------------------------------------- invaders
def n_invader_move(st, col, depth, t):
    """f_0f959: black invaders climb towards the exit."""
    c = bn.climb_dir(st, N, col, depth, 8)
    d = st.rand8() if c == 0 else c - 1
    if not bn.move_to(st, N, col, depth, d) and not bn.move_to(st, N, col, depth, st.rand8()):
        st.set_grid(CELLS, col, depth, _get(st, RTYPE, _cur(st)))


def _invader_raid(st, col, depth, t, guard):
    cur = _cur(st)
    v = st.grid(DIRT, col, depth)
    if v < 0x10 or v > 0x13:
        d = (st.rand(3) + t - 2) & 7
        if guard:
            _set(st, RTYPE, cur, (_get(st, RTYPE, cur) & 0xf8) | d)
        if bn.move_to(st, N, col, depth, d):
            return
        d = bn.step_dir(st, N, col, depth, t & 7)
        if d < 0:
            d = st.rand(8)
        if bn.move_to(st, N, col, depth, d):
            return
        if not guard:
            _set(st, RSTATE, cur, 1)
    else:
        bn.invader_eat_food(st, N, col, depth)
        _set(st, RSTATE, cur, 3)
        _set(st, RTYPE, cur, _get(st, RTYPE, cur) | 8)
    st.set_grid(CELLS, col, depth, _get(st, RTYPE, cur))


def n_invader_attack(st, col, depth, t):
    """f_0f7a0: black raiders look for red stores (like the red raiders in the black nest)."""
    _invader_raid(st, col, depth, t, False)


def n_invader_guard(st, col, depth, t):
    """f_0f871: a black Defense ant in the red nest while the player watches it: raids without giving up."""
    _invader_raid(st, col, depth, t, True)


GO_OUT = (2, 5, 6, 7, 11, 12, 15, 16)


def nest_ant_tick(st, col, depth, t):
    """f_0f465 RedNestAntTick."""
    caste = (t & 0x78) >> 3
    cur = _cur(st)
    state = _get(st, RSTATE, cur)
    if not t & 0x80:                                         # a black invader
        st.inc16(G, 0xd40 + state * 2)
        if t < 8:
            _set(st, RTYPE, cur, 0)
            st.set_grid(CELLS, _get(st, RX, cur), _get(st, RY, cur), 0)
            return
        if t > 0x6f:
            n_fighting(st, col, depth)
            return
        o = st.grid(CELLS, col, depth)
        if 0x80 < o < 0xe8:
            i = bn.nest_ant_at(st, N, col, depth, o)
            if i >= 0:
                if o > 0xdf:
                    remove_ant(st, i)
                if o < 0x88:                                 # steal red brood
                    _set(st, RSTATE, cur, 3)
                    _set(st, RTYPE, cur, _get(st, RTYPE, cur) | 8)
                    st.set_grid(CELLS, col, depth, _get(st, RTYPE, cur))
                    _set(st, RTYPE, i, 0)
                    return
                w = sf.resolve_fight(st, _get(st, RTYPE, i), t)
                _set(st, RTYPE, cur, 0)
                _set(st, RE, i, w)
                nt = ((w & 0x80) + 0x70) & 0xff
                _set(st, RTYPE, i, nt)
                st.set_grid(CELLS, col, depth, nt)
                _set(st, RSTATE, i, 10)
                return
        if state == 6 and st.u16(G, 0x48c) == 3:
            n_invader_guard(st, col, depth, t)
        elif state == 7:
            n_invader_attack(st, col, depth, t)
        else:
            n_invader_move(st, col, depth, t)
        return
    st.inc16(G, 0xd72 + state * 2)
    if st.rand256() == 0 and state != 9 and s16(st.rand32()) > _health(st):
        _set(st, RTYPE, cur, 0)
        st.set_grid(CELLS, col, depth, 0)
        st.inc32(G, 0xfbc)
        return
    if state > 0x11 or state == 0:
        n_wander(st, col, depth, t, caste)
    elif state == 1:
        n_nesting(st, col, depth, t, caste)
    elif state == 3:
        n_got_food(st, col, depth, t)
    elif state == 4:
        n_dig_in(st, col, depth, t, caste)
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
        if s16(st.u16(G, 0x8e8)) > 100:
            _set(st, RSTATE, _cur(st), 15)
    elif state == 17:
        n_state17(st, col, depth, t)
    else:
        n_go_to_surface(st, col, depth, t)


def red_nest_loop(st):
    """f_0f3f8 RedNestLoop."""
    st.set16(G, 0xf18, st.u16(G, 0xeaa))
    while s16(st.u16(G, 0xf18)) > 0:
        st.inc16(G, 0xf18, -1)
        i = st.u16(G, 0xf18)
        t = _get(st, RTYPE, i)
        if t:
            nest_ant_tick(st, _get(st, RX, i), _get(st, RY, i), t)
```
{% endraw %}
