---
layout: default
title: "Surface ants"
permalink: /reference/surface/
---

# Surface ants

*`surface.py` — The dispatcher and the twenty state handlers.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `surface.py`]({{ site.baseurl }}/assets/reference/simant_ref/surface.py)

The surface ant tick (`0894`): ants are structure-of-arrays inside the SIM segment, and the occupancy grid stores each ant's type byte (bit 7 red, bits 3–6 caste, bits 0–2 heading). `surface_ants_tick` walks the live list and dispatches to twenty handlers — bored, nesting, foraging, got-food, dig-out, defense, attack, hatching, egg-laying, fighting, alarmed, defend-nest, resting, the flight sequence, the avenger — plus the fight resolver, corpse placement and recruitment.

- This is the largest behavioural surface in the game and the file most trace calls land in; it is also where a one-instruction difference shows up as ants that 'feel' wrong.
- `resolve_fight` and `place_corpse` mutate both ants' arrays and the grid, so call order is part of the result.
- The player's yellow ant is not a surface ant: its hooks are called from here, but its upkeep lives in `player.py`.

## At a glance

- **762** lines
- **Classes / hooks:** `NoPlayer`
- **39 top-level functions**, including `_get`, `_set`, `resolve_fight`, `place_corpse`, `encounter_enemy`, `add_surface_ant`, `enter_nest`, `_try_step` …
- **Original routines referenced:** `f_01315`, `f_08c8b`, `f_08eb2`, `f_08f2e`, `f_09018`, `f_09091`, `f_090f3`, `f_091d2`, `f_092a1`, `f_09334`, `f_0963d`, `f_097ce` …

## Source

{% raw %}
```python
"""Surface ants: the per-tick dispatcher and the 20 state handlers (SIMANT.EXE segment 0894 and helpers).

Ants are structure-of-arrays in the SIM segment; the occupancy grid holds each ant's type byte
(bit 7 red, bits 3-6 caste, bits 0-2 heading). Player (yellow ant) interactions call st.player hooks.
"""
from .state import SIM, G, T, DS
from . import movement as mv
from . import pheromones as ph
from . import nestgrid as ng

SURFACE, OCC = 0x0180, 0x6180
SX, SY, SSTATE, STYPE, SE = 0xa180, 0xa569, 0xa952, 0xad3b, 0xb124
s16 = mv.s16


class NoPlayer:
    """Player hooks not ported yet: fail loudly if the simulation reaches them."""

    def attack_player(self, st, view, ant):
        raise NotImplementedError('AttackPlayer (f_7c5ab)')

    def nudge_player(self, st, a, b, d):
        raise NotImplementedError('f_769c5 (player follow nudge)')

    def spider_event(self, st, n):
        raise NotImplementedError(f'f_2f7d0({n}) (the player-spider leaves or is beaten)')

    def spider_eats_player(self, st, a, b):
        raise NotImplementedError('f_11a3e / f_2f7d0(1) (the spider eats the yellow ant)')

    def lion_eats_player(self, st, a, b):
        raise NotImplementedError('f_11a3e / f_2f7d0(2) (an ant lion catches the yellow ant)')

    def nest_follow(self, st, col, depth, d):
        raise NotImplementedError('f_2f7bc (nest ant steps onto the yellow ant)')

    def yard_event(self, st, n):
        raise NotImplementedError(f'f_2f7d0({n}) (the human or the mower hits the player)')

    def game_event(self, st, n):
        raise NotImplementedError(f'f_2f7d0({n}) -> f_75d01 (player event: dialogs, the yellow ant dies, ...)')

    def game_over(self, st):
        raise NotImplementedError('f_71d95 (the game-over screen: rating, new game)')

    def win_screen(self, st):
        raise NotImplementedError('f_2f91a (Full Game won: the end screen)')

    def new_game_dialog(self, st):
        raise NotImplementedError('f_725b6 (the new-game dialog)')

    def choose_patch(self, st):
        raise NotImplementedError('f_7650c (the yard map: pick a patch)')

    def sound_done(self, st):
        raise NotImplementedError('f_284a4 (the sound driver: has the sound finished?)')

    def effect(self, st, name, *args):
        pass                                    # visual effects only (patch_visible)


def _get(st, f, i):
    return st.u8(SIM, f + i)


def _set(st, f, i, v):
    st.set8(SIM, f + i, v)


# ------------------------------------------------------------------------------------------- combat
def resolve_fight(st, def_t, att_t):
    """f_0a774: returns the winner's type byte; the outcome is decided at contact."""
    if st.u16(T, 0xc14) == 1:
        st.inc32(G, 0xf3e)
        return att_t if def_t & 0x80 else def_t
    r = st.crt_rand_mod(10)
    odds = st.u8(DS, 0x1b82 + st.u8(DS, 0x1b72 + ((def_t & 0x78) >> 3)) * 4
                 + st.u8(DS, 0x1b72 + ((att_t & 0x78) >> 3)))
    winner = def_t if r < odds else att_t
    if winner & 0x80 == 0:          # a black winner counts a red death, and vice versa
        st.inc16(G, 0xa00)
        st.inc32(G, 0xf3e)
    else:
        st.inc16(G, 0x9fa)
        st.inc32(G, 0xefc)
    return winner


def place_corpse(st, a, b, red):
    """f_0a961: corpse ring buffer (100 slots); the oldest corpse turns back into ground."""
    idx = st.u16(G, 0x476) + 1
    st.set16(G, 0x476, idx)
    if s16(idx) > 99:
        st.set16(G, 0x476, 0)
        idx = 0
    oa, ob = st.u8(G, 0x37c + idx), st.u8(G, 0x404 + idx)
    old = st.grid(SURFACE, oa, ob)
    house = st.u16(G, 0xf24) != 0
    if not house:
        if 0x0f < old < 0x18:
            st.set_grid(SURFACE, oa, ob, st.rand16())
    elif 7 < old < 0x18:
        st.set_grid(SURFACE, oa, ob, (old - 8) >> 2)
    st.set8(G, 0x37c + idx, a)
    st.set8(G, 0x404 + idx, b)
    t = st.grid(SURFACE, a, b)
    if not house:
        if t <= 0x17:
            st.set_grid(SURFACE, a, b, (st.rand4() + 0x14) if red else (st.rand4() + 0x10))
    elif t <= 3:
        if not red:
            st.set_grid(SURFACE, a, b, (t + 2) * 4 + st.rand(2))
        else:
            st.set_grid(SURFACE, a, b, st.rand(2) + t * 4 + 10)
    st.set_grid(OCC, a, b, 0)


def encounter_enemy(st, ant, a, b, na, nb):
    """f_0a6c9: the attacker merges into the defender's slot as a 'Fight' entity."""
    att = _get(st, STYPE, ant)
    _set(st, STYPE, ant, 0)
    st.set_grid(OCC, a, b, 0)
    d = mv.surface_ant_at(st, na, nb)
    if d < 0:
        return
    w = resolve_fight(st, _get(st, STYPE, d), att)
    f = ((w & 0x80) + 0x70) & 0xff
    _set(st, STYPE, d, f)
    st.set_grid(OCC, na, nb, f)
    _set(st, SSTATE, d, 10)
    _set(st, SE, d, w)
    ph.lay_max(st, ph.ALARM, na, nb, 0x28)


# ------------------------------------------------------------------------------------------- nests
def add_surface_ant(st, a, b, t, state, e):
    """f_0f047 AddSurfaceAnt: an ant leaving a nest appears on a free tile next to the entrance (a, b).
    The occupancy grid is not written. Ants fresh out of their own nest get a nest-marker countdown."""
    for d in range(8):
        na, nb = a + mv.dx(st, d), b + mv.dy(st, d)
        if mv.in_patch(na, nb) and st.grid(SURFACE, na, nb) < 0x50:
            break
    else:
        return 0
    i = st.u16(G, 0xd6a)
    _set(st, SX, i, na)
    _set(st, SY, i, nb)
    _set(st, STYPE, i, t)
    _set(st, SSTATE, i, state)
    if state == 6:
        _set(st, SE, i, e)
    else:
        _set(st, SE, i, 0)
        if state not in (3, 7) and ((t & 0x80 and a > 0x40) or (not t & 0x80 and a < 0x40)):
            _set(st, SE, i, 0x78)
    if s16(st.u16(G, 0xd6a)) >= 1000:
        ng.compact_surface(st)
        if s16(st.u16(G, 0xd6a)) >= 1000:
            return 1
    st.inc16(G, 0xd6a)
    return 1


def enter_nest(st, a, b, ant):
    """f_0a5ae: the ant leaves the surface into the nest of that half of the patch (column = b)."""
    t, state, e = _get(st, STYPE, ant), _get(st, SSTATE, ant), _get(st, SE, ant)
    if a < 0x40:
        n, entr = ng.BLACK, 0x224
    else:
        n, entr = ng.RED, 0x264
    if s16(st.u16(G, n['count'])) > 499:
        ng.compact_nest(st, n)
    if s16(st.u16(G, n['count'])) > 499:
        return
    ng.add_nest_ant(st, n, b, 1, ((t & 0xf8) + 4) & 0xff, state, e)
    if st.u8(T, entr + b):
        ng.dig_at(st, n, b, 1)
    _set(st, STYPE, ant, 0)
    st.set_grid(OCC, a, b, 0)


# ------------------------------------------------------------------------------------------- moving
def _try_step(st, ant, a, b, nd, cc):
    """Move into (a+dx, b+dy) facing nd; returns (na, nb)."""
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    v = (nd | cc) & 0xff
    st.set_grid(OCC, na, nb, v)
    _set(st, STYPE, ant, v)
    st.set_grid(OCC, a, b, 0)
    _set(st, SX, ant, na)
    _set(st, SY, ant, nb)
    return na, nb


def _turn(st, ant, a, b, d, cc):
    v = (mv.turn_aside(st, d) | cc) & 0xff
    _set(st, STYPE, ant, v)
    st.set_grid(OCC, a, b, v)


def _lay_nest_marker(st, ant, na, nb, t):
    e = _get(st, SE, ant)
    if e:
        e -= 1
        _set(st, SE, ant, e)
        ph.lay_max(st, ph.RED_NEST if t & 0x80 else ph.BLACK_NEST, na, nb, e)


def _pickup(st, ant, a, b, nd, cc, na, nb):
    v = (nd | cc | 8) & 0xff
    _set(st, STYPE, ant, v)
    st.set_grid(OCC, a, b, v)
    _set(st, SSTATE, ant, 3)
    mv.take_food_at(st, na, nb)
    _set(st, SE, ant, 200)


def _bump_common(st, ant, a, b, na, nb, nd, t, cc, o, state_on_friend=False):
    """Yellow ant / friend / enemy reaction used by Bored, Nesting and Foraging."""
    if mv.is_yellow(o):
        if (st.u8(G, 0x4e2) ^ t) & 0x80:
            st.player.attack_player(st, 1, ant)
            return
        if st.u16(G, 0x1044) == 1:
            v = (nd | cc) & 0xff
            _set(st, STYPE, ant, v)
            st.set_grid(OCC, a, b, v)
            st.player.nudge_player(st, a, b, nd)
        _turn(st, ant, a, b, t & 7, cc)
        return
    if (o ^ t) & 0x80:
        encounter_enemy(st, ant, a, b, na, nb)
        return
    _turn(st, ant, a, b, t & 7, cc)
    if state_on_friend:
        _set(st, SSTATE, ant, mv.state_for_caste(st, (t >> 3) & 15, t))


def s_bored(st, ant):
    """f_09334 (state 0)."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    cc, caste = t & 0xf8, (t & 0x78) >> 3
    nd = mv.next_dir(st, a, b, t & 7)
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    tile = st.grid(SURFACE, na, nb)
    if mv.is_food(st, tile):
        if caste in (6, 2):
            _pickup(st, ant, a, b, nd, cc, na, nb)
            return
    elif s16(st.u16(G, 0x480)) < tile:
        _turn(st, ant, a, b, t & 7, cc)
        return
    o = st.grid(OCC, na, nb)
    if o == 0:
        _try_step(st, ant, a, b, nd, cc)
        _lay_nest_marker(st, ant, na, nb, t)
        ph.wear_trail(st, na, nb, t & 0x80)
        if st.rand8() == 0 and caste in (6, 2):
            _set(st, SSTATE, ant, 2)
        return
    _bump_common(st, ant, a, b, na, nb, nd, t, cc, o, state_on_friend=True)


def s_nesting(st, ant):
    """f_099c7 (states 1 Nesting, 4 Dig In on the surface): head home."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    cc, caste = t & 0xf8, (t & 0x78) >> 3
    nd = mv.home_dir(st, a, b, t & 7, t)
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    tile = st.grid(SURFACE, na, nb)
    if mv.is_food(st, tile):
        if caste in (6, 2):
            _pickup(st, ant, a, b, nd, cc, na, nb)
            return
    elif s16(st.u16(G, 0x480)) < tile:
        _turn(st, ant, a, b, t & 7, cc)
        return
    o = st.grid(OCC, na, nb)
    if o == 0:
        _try_step(st, ant, a, b, nd, cc)
        _lay_nest_marker(st, ant, na, nb, t)
        return
    _bump_common(st, ant, a, b, na, nb, nd, t, cc, o)


def s_foraging(st, ant):
    """f_09fe5 (state 2)."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    if st.rand32() == 0:
        _set(st, SSTATE, ant, 13)
        return
    cc, caste = t & 0xf8, (t & 0x78) >> 3
    if ph.get(st, ph.ALARM, (a & 0xfe) * 16 + (b >> 1)):
        _set(st, SSTATE, ant, 11)
        return
    if caste not in (6, 2):
        _set(st, SSTATE, ant, mv.state_for_caste(st, caste, t))
        _set(st, SE, ant, 0)
        return
    d = t & 7
    nd = mv.forage_dir(st, a, b, d, t)
    if nd < 0:                                       # lost
        if st.rand8() == 0:
            _set(st, SSTATE, ant, mv.state_for_caste(st, caste, t))
        else:
            _set(st, SSTATE, ant, 0)
        _set(st, SE, ant, 0)
        ph.wear_trail(st, a >> 1, b >> 1, t & 0x80)  # original quirk: halved coordinates
        return
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    tile = st.grid(SURFACE, na, nb)
    if mv.is_food(st, tile):
        _pickup(st, ant, a, b, nd, cc, na, nb)
        return
    if s16(st.u16(G, 0x480)) < tile:
        _turn(st, ant, a, b, d, cc)
        if st.rand16() != 0:
            return
        _set(st, SSTATE, ant, mv.state_for_caste(st, caste, t))
        _set(st, SE, ant, 0)
        return
    o = st.grid(OCC, na, nb)
    if o:
        _bump_common(st, ant, a, b, na, nb, nd, t, cc, o)
        return
    _try_step(st, ant, a, b, nd, cc)
    _lay_nest_marker(st, ant, na, nb, t)
    ph.wear_trail(st, na, nb, t & 0x80)


def s_got_food(st, ant):
    """f_09e65 (state 3): carry food home, laying the food trail; ignores occupancy."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    cc = t & 0xf8
    nd = mv.home_dir(st, a, b, t & 7, t)
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    if s16(st.u16(G, 0x480)) < st.grid(SURFACE, na, nb):
        _turn(st, ant, a, b, t & 7, cc)
        return
    _try_step(st, ant, a, b, nd, cc)
    e = _get(st, SE, ant)
    if e:
        e -= 1
        _set(st, SE, ant, e)
        ph.lay_max(st, ph.RED_TRAIL if t & 0x80 else ph.BLACK_TRAIL, na, nb, e)


def s_dig_out(st, ant):
    """f_097ce (state 5): wander with dirt, drop it 1/8 per tick."""
    a, b = _get(st, SX, ant), _get(st, SY, ant)
    t = _get(st, STYPE, ant)
    cc, caste = t & 0xf8, (t & 0x78) >> 3
    nd = mv.walk(st, t & 7, st.rand8())
    e = mv.edge_dir(a, b, st)
    if e:
        nd = (e - 1) & 7
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    if caste not in (5, 9):
        _set(st, SSTATE, ant, mv.state_for_caste(st, caste, t))
        _set(st, SE, ant, 0)
        return
    if st.rand8() == 0:
        _set(st, STYPE, ant, (t - 0x18) & 0xff)
        _set(st, SSTATE, ant, mv.state_for_caste(st, caste, t))
        _set(st, SE, ant, 0)
    elif st.grid(SURFACE, na, nb) <= s16(st.u16(G, 0x480)) and st.grid(OCC, na, nb) == 0:
        _try_step(st, ant, a, b, nd, cc)
        _lay_nest_marker(st, ant, na, nb, t)
        return
    else:
        _set(st, STYPE, ant, (mv.turn_aside(st, t & 7) | cc) & 0xff)
    st.set_grid(OCC, a, b, _get(st, STYPE, ant))


def s_defense(st, ant):
    """f_0a368 (state 6): guards / recruits."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    cc = t & 0xf8
    if ph.get(st, ph.ALARM, (a & 0xfe) * 16 + (b >> 1)) == 0:
        nd = mv.black_guard_dir(st, a, b, t & 7) if t < 0x80 else mv.red_guard_dir(st, a, b, t & 7)
    else:
        nd = mv.alarm_dir(st, a, b, t & 7)
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    if s16(st.u16(G, 0x480)) < st.grid(SURFACE, na, nb):
        v = (st.rand8() | cc) & 0xff
        _set(st, STYPE, ant, v)
    else:
        o = st.grid(OCC, na, nb)
        if o == 0:
            _try_step(st, ant, a, b, nd, cc)
            return
        if mv.is_yellow(o):
            if (st.u8(G, 0x4e2) ^ t) & 0x80:
                st.player.attack_player(st, 1, ant)
                return
            if st.u16(G, 0x1044) != 0:
                v = (nd | cc) & 0xff
                _set(st, STYPE, ant, v)
                st.set_grid(OCC, a, b, v)
                st.player.nudge_player(st, a, b, nd)
            _turn(st, ant, a, b, t & 7, cc)
            return
        if (o ^ t) & 0x80:
            encounter_enemy(st, ant, a, b, na, nb)
            return
        _set(st, STYPE, ant, (mv.turn_aside(st, t & 7) | cc) & 0xff)
    st.set_grid(OCC, a, b, _get(st, STYPE, ant))


def s_attack(st, ant):
    """f_0ab2d (state 7): drop any load, march on the enemy nest."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    caste = (t & 0x78) >> 3
    if st.u16(T, 0x74 + caste * 2) == 1:
        t = ((st.s8(T, 0x94 + caste) << 3) | (t & 0x87)) & 0xffff
    cc = t & 0xf8
    nd = mv.home_dir(st, a, b, t & 7, t ^ 0x80)
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    if st.grid(SURFACE, na, nb) <= s16(st.u16(G, 0x480)):
        o = st.grid(OCC, na, nb)
        if o == 0:
            _try_step(st, ant, a, b, nd, cc)
            return
        if mv.is_yellow(o):
            if (st.u8(G, 0x4e2) ^ t) & 0x80:
                st.player.attack_player(st, 1, ant)
                return
        elif (o ^ t) & 0x80:
            encounter_enemy(st, ant, a, b, na, nb)
            return
    _turn(st, ant, a, b, t & 7, cc)


def s_hatching(st, ant):
    """f_08eb2 (state 8)."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    st.set_grid(OCC, a, b, t)
    if st.rand(200) == 0:
        _set(st, STYPE, ant, 0)
        st.set_grid(OCC, a, b, 0)


def s_egg_laying(st, ant):
    """f_08f2e (state 9): a queen's abdomen (caste >= 13) on the surface vanishes if its head is gone."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    st.set_grid(OCC, a, b, t)
    if (t & 0x7f) > 0x67:
        d = t & 7
        ha, hb = a + mv.dx(st, d), b + mv.dy(st, d)
        if ((st.grid(OCC, ha, hb) - t) & 0xffff) != 0xfff8 and mv.surface_ant_at(st, ha, hb) < 0:
            st.set_grid(OCC, a, b, 0)
            _set(st, STYPE, ant, 0)


def s_fighting(st, ant):
    """f_0a871 (state 10)."""
    a, b = _get(st, SX, ant), _get(st, SY, ant)
    t = ((_get(st, STYPE, ant) & 0xf8) + st.rand(7)) & 0xff
    _set(st, STYPE, ant, t)
    st.set_grid(OCC, a, b, t)
    if st.rand16() == 0:
        w = _get(st, SE, ant)
        st.set_grid(OCC, a, b, w)
        _set(st, STYPE, ant, w)
        cur = st.u16(G, 0xf18)
        _set(st, SSTATE, cur, mv.state_for_caste(st, (w & 0x78) >> 3, w))
        _set(st, SE, ant, 0)
        place_corpse(st, a, b, _get(st, STYPE, ant) & 0x80)
    elif st.u16(T, 0x7b2) == 1:
        st.player.effect(st, 'fight', a, b, 1)


def s_alarmed(st, ant):
    """f_09c55 (state 11)."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    cc = t & 0xf8
    if ph.get(st, ph.ALARM, (a & 0xfe) * 16 + (b >> 1)) == 0 and st.rand4() == 0:
        st.set_grid(OCC, a, b, _get(st, STYPE, ant))
        _set(st, SSTATE, ant, mv.state_for_caste(st, (t & 0x78) >> 3, t))
        return
    nd = mv.alarm_dir(st, a, b, t & 7)
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    if st.grid(SURFACE, na, nb) <= s16(st.u16(G, 0x480)):
        o = st.grid(OCC, na, nb)
        if o == 0:
            _try_step(st, ant, a, b, nd, cc)
            return
        if not mv.is_yellow(o):
            if (o ^ t) & 0x80:
                encounter_enemy(st, ant, a, b, na, nb)
                return
        elif (st.u8(G, 0x4e2) ^ t) & 0x80:
            st.player.attack_player(st, 1, ant)
            return
    _turn(st, ant, a, b, t & 7, cc)


def wander(st, ant):
    """f_0963d."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    cc = t & 0xf8
    nd = mv.next_dir(st, a, b, t & 7)
    na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
    if st.grid(SURFACE, na, nb) <= s16(st.u16(G, 0x480)):
        o = st.grid(OCC, na, nb)
        if o == 0:
            _try_step(st, ant, a, b, nd, cc)
            return
        if mv.is_yellow(o):
            if (st.u8(G, 0x4e2) ^ t) & 0x80:
                st.player.attack_player(st, 1, ant)
                return
        elif (t ^ o) & 0x80:
            encounter_enemy(st, ant, a, b, na, nb)
            return
    _turn(st, ant, a, b, t & 7, cc)


def _home_marker(st, ant):
    a, b, t = _get(st, SX, ant), _get(st, SY, ant), _get(st, STYPE, ant)
    m = ph.RED_NEST if t & 0x80 else ph.BLACK_NEST
    return ph.get(st, m, (a & 0xfe) * 16 + (b >> 1))


def s_defend_nest(st, ant):
    """f_092a1 (state 12)."""
    if _home_marker(st, ant) < 0x6e:
        s_nesting(st, ant)
    else:
        wander(st, ant)


def s_resting(st, ant):
    """f_09018 (state 13)."""
    b, a = _get(st, SY, ant), _get(st, SX, ant)
    if mv.at_nest_entrance(st, a, b):
        enter_nest(st, a, b, ant)
        return
    if st.rand4() == 0:
        _set(st, SSTATE, ant, 2)
    elif st.u16(T, 0x7b2) == 1:
        st.player.effect(st, 'rest', a, b, 1)


def _flight_timer(st, ant):
    return s16(st.u16(G, 0x8e8 if _get(st, STYPE, ant) & 0x80 else 0x8dc))


def s_pre_flight(st, ant):
    """f_09091 (state 14)."""
    if st.rand2() == 0:
        s_nesting(st, ant)
    else:
        wander(st, ant)
    if _flight_timer(st, ant) > 100:
        _set(st, SSTATE, st.u16(G, 0xf18), 0xf)


def s_take_off(st, ant):
    """f_090f3 (state 15)."""
    if _home_marker(st, ant) < 100:
        s_nesting(st, ant)
    else:
        wander(st, ant)
    tm = _flight_timer(st, ant)
    if tm != 0:
        if tm != 1 and st.rand(tm & 0xffff) != 0:
            return
        _set(st, SSTATE, st.u16(G, 0xf18), 0x10)


def s_flying(st, ant):
    """f_091d2 (state 16)."""
    t = _get(st, STYPE, ant)
    if st.rand32() != 0:
        return
    red = t & 0x80
    if (not red and s16(st.u16(G, 0x6aa)) < 0x32) or (red and s16(st.u16(G, 0x73a)) < 0x32):
        _set(st, STYPE, ant, 0)
        st.set_grid(OCC, _get(st, SX, ant), _get(st, SY, ant), 0)
        if st.u16(G, 0xeac) == 2:
            st.inc16(G, 0x73a if red else 0x6aa)
            if st.rand16() == 0:
                st.inc16(G, 0x850 if red else 0x7c8)      # black: f_01315 (empty in this version)


# ------------------------------------------------------------------------------------------- Avenger
def release_red_guards(st):
    """f_14167: red surface ants in Defense go back to Bored."""
    i = s16(st.u16(G, 0xd6a))
    while i > 0:
        i -= 1
        tt = _get(st, STYPE, i)
        if tt and tt > 0x7f and _get(st, SSTATE, i) == 6:
            _set(st, SSTATE, i, 0)


def recruit_red(st, n):
    """f_140e4: put up to n red workers/soldiers (not the Avenger) into Defense."""
    n = s16(n)
    i = s16(st.u16(G, 0xd6a))
    while i > 0 and n > 0:
        i -= 1
        tt = _get(st, STYPE, i)
        if tt and tt > 0x7f:
            c = (tt & 0x78) >> 3
            if c in (2, 6) and _get(st, SSTATE, i) not in (0x13, 6):
                _set(st, SSTATE, i, 6)
                _set(st, SE, i, 0)
                n -= 1


def avenger_pick_target(st):
    """f_0e123."""
    release_red_guards(st)
    if (st.u16(G, 0x48c) == 1 and st.rand(0x20) + 0x40 < s16(st.u16(G, 0x47c))
            and st.rand(10) < s16(st.u16(G, 0xb1c))):
        st.set16(G, 0x4a4, 2)
        recruit_red(st, st.u16(G, 0xb1c))
        return
    st.set16(G, 0x4f2, st.u16(T, 0x2be))
    ta = s16(st.u16(T, 0x2bc))
    st.set16(G, 0x4e0, ta)
    if ta < 0x1f:
        tb = s16(st.u16(G, 0x4f2))
        if tb < 0x14:
            st.set16(G, 0x4f2, tb + 5)
        elif tb > 0x28:
            st.set16(G, 0x4f2, tb - 5)
    else:
        st.set16(G, 0x4e0, ta - 5)
    n = s16(st.u16(G, 0xafc) + st.u16(G, 0xafe))
    recruit_red(st, n >> 2 if n < 0x14 else n >> 3)
    st.set16(G, 0x4a4, 1)


def is_walkable_surface(st, a, b):
    """f_1323e for view 1 (surface)."""
    if not (0 <= a < 0x80 and 0 <= b < 0x40):
        return False
    t = st.grid(SURFACE, a, b)
    return t < 0x54 if st.u16(G, 0xf24) == 0 else t < 0x91


def step_towards_surface(st, a, b, ta, tb):
    """f_0e20f(view 1). Each walkable neighbour that is closer than the best so far tightens the threshold;
    a free open-ground one becomes the answer, any other becomes the fallback. -1/-2 = no step."""
    dist = mv.distance_lo(a, b, ta, tb)
    if dist <= 0:
        return -1
    res, fallback = -1, -2
    for d in range(8):
        na, nb = a + mv.dx(st, d), b + mv.dy(st, d)
        if not is_walkable_surface(st, na, nb):
            continue
        nd = mv.distance_lo(na, nb, ta, tb)
        if nd >= dist:
            continue
        dist = nd
        if st.grid(OCC, na, nb) == 0 and _is_open_ground(st, na, nb):
            res = d
        else:
            fallback = d
    return res if res >= 0 else fallback


def _is_open_ground(st, a, b):
    if not (0 <= a < 128 and 0 <= b < 64):
        return False
    o = st.grid(OCC, a, b)
    if o and not mv.is_yellow(o):
        return False
    return st.grid(SURFACE, a, b) < 0x10


def s_avenger(st, ant):
    """f_0df5b (state 19): leads red guards towards its target."""
    b, t, a = _get(st, SY, ant), _get(st, STYPE, ant), _get(st, SX, ant)
    cc = t & 0xf8
    st.set16(G, 0x490, a)
    st.set16(G, 0x494, b)
    st.set16(G, 0x498, 1)
    mode = st.u16(G, 0x4a4)
    if mode == 0:
        avenger_pick_target(st)
    elif mode == 2 and st.u16(G, 0x48c) == 1:
        st.set16(G, 0x4e0, st.u16(G, 0x22a))
        st.set16(G, 0x4f2, st.u16(G, 0x238))
    nd = step_towards_surface(st, a, b, s16(st.u16(G, 0x4e0)), s16(st.u16(G, 0x4f2)))
    if nd < 0:
        if st.rand(10) == 0:
            st.set16(G, 0x4a4, 0)
    else:
        na, nb = a + mv.dx(st, nd), b + mv.dy(st, nd)
        o = st.grid(OCC, na, nb)
        if o == 0:
            _try_step(st, ant, a, b, nd, cc)
            return
        if mv.is_yellow(o):
            st.player.attack_player(st, 1, ant)
            return
        if o < 0x80:
            return
        _set(st, STYPE, ant, (mv.turn_aside(st, t & 7) | cc) & 0xff)
    st.set_grid(OCC, a, b, _get(st, STYPE, ant))


# ------------------------------------------------------------------------------------------- dispatcher
HANDLERS = {0: s_bored, 1: s_nesting, 2: s_foraging, 3: s_got_food, 4: s_nesting, 5: s_dig_out,
            6: s_defense, 7: s_attack, 8: s_hatching, 9: s_egg_laying, 10: s_fighting, 11: s_alarmed,
            12: s_defend_nest, 13: s_resting, 14: s_pre_flight, 15: s_take_off, 16: s_flying,
            19: s_avenger}


def surface_ants_tick(st):
    """f_08c8b: every surface slot from the top down: death roll, census, state handler."""
    st.set16(G, 0xf18, st.u16(G, 0xd6a))
    while s16(st.u16(G, 0xf18)) >= 1:
        i = st.u16(G, 0xf18) - 1
        st.set16(G, 0xf18, i)
        if st.rand256() == 0:
            t = _get(st, STYPE, i)
            if t:
                health = s16(st.u16(G, 0x1fe if t & 0x80 else 0x10be))
                if st.rand32() > health:
                    place_corpse(st, _get(st, SX, i), _get(st, SY, i), t & 0x80)
                    _set(st, STYPE, i, 0)
                    st.inc32(G, 0xf30)
        t = _get(st, STYPE, i)
        if t == 0:
            continue
        state = _get(st, SSTATE, i)
        st.inc16(G, (0xd72 if t & 0x80 else 0xd40) + state * 2)
        if state > 0x13:
            continue
        h = HANDLERS.get(state)
        if h:
            h(st, i)
```
{% endraw %}
