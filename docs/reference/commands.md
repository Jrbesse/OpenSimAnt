---
layout: default
title: "The yellow ant's menu commands"
permalink: /reference/commands/
---

# The yellow ant's menu commands

*`commands.py` — Recruit, release, exchange, alarm, dig, start brood.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `commands.py`]({{ site.baseurl }}/assets/reference/simant_ref/commands.py)

The eight menu commands (`f_76cb9`, reached through `f_2f906` from the pop-up menu `f_67e93`): recruit, release, exchange, alarm, dig a hole, start brood, and the spider's chase and hunt. Target-picking modes (`pause`, the pick-a-target cursor) are held in the player effect channel, not in the simulation state.

- A command that needs a target sets a mode and returns; the click that resolves it is a separate call, and cancelling is a third path.
- `_yellow_caste`/`_new_yellow` are the only places the player can change its own caste.
- Commands are the player's direct orders — the design rule is that these exist for the ant you embody, and for nothing else.

## At a glance

- **282** lines
- **11 top-level functions**, including `recruit`, `_target_mode`, `cancel_target_mode`, `command`, `_yellow_caste`, `_new_yellow`, `_add_yellow_ant`, `exchange` …
- **Original routines referenced:** `f_00ea1`, `f_00ed8`, `f_00f1d`, `f_0125f`, `f_0250e`, `f_03391`, `f_10fcd`, `f_11121`, `f_11327`, `f_114bd`, `f_11ac1`, `f_11aff` …

## Source

{% raw %}
```python
"""The yellow ant's menu commands (f_76cb9, via f_2f906 from the pop-up menu f_67e93): recruit, release,
exchange, alarm, dig a hole, start brood, and the spider's chase / hunt. See SIM_NOTES "The yellow ant's menu
and commands".

Screen-only effects go to st.player.effect: 'sound' (f_00ed8), 'voice' (f_00ea1), 'help' (f_76eb5),
'pause' (f_2f816, the pick-a-target cursor mode), 'anim_timer' (f_0125f).
"""
from .state import SIM, G, T
from . import player
from . import debug
from . import colony as co
from . import movement as mv
from .movement import s16

# the menus' command tables (DS:23D0 / DS:23D4 / DS:23DA)
QUEEN_MENU = (8, 9, 0)                  # Dig Hole, Start Brood, Help
ANT_MENU = (1, 2, 4, 5, 6, 0)           # Recruit 5, Recruit 10 (Shift: 3), Release 1/2, Release All, Exchange, Help
SPIDER_MENU = (0xa, 0xb, 6, 0)          # Chase, Hunt (Alt: 0xC), Exchange, Help


def recruit(st, n):
    """f_13f32: up to n black workers / soldiers (castes 2 and 6) join the yellow ant (state 6), surface ants
    from the last down first, then the black nest's."""
    for count, typ, state, e in ((0xd6a, 0xad3b, 0xa952, 0xb124), (0xda8, 0xbaec, 0xb8f7, 0xbce1)):
        i = s16(st.u16(G, count))
        while i > 0 and n > 0:
            i -= 1
            t = st.u8(SIM, typ + i)
            if t == 0 or t & 0x80 or ((t & 0x78) >> 3) not in (2, 6):
                continue
            if st.u8(SIM, state + i) == 6:
                continue
            st.set8(SIM, state + i, 6)
            st.set8(SIM, e + i, 0)
            n -= 1


def _target_mode(st, mode):
    """f_11b21 (Exchange, 0x0A) / f_11ac1 (Chase, 0x0B): toggle the pick-a-target cursor mode G:105E."""
    if st.u16(G, 0x105e) == mode:
        cancel_target_mode(st)
        return
    st.set16(G, 0x48e, st.u16(G, 0x47e))
    st.set16(G, 0x105e, mode)
    st.player.effect(st, 'pause', 1)


def cancel_target_mode(st):
    """f_11b5f / f_11aff."""
    st.set16(G, 0x105e, 0xffff)
    st.player.effect(st, 'pause', st.u16(G, 0x48e))


def command(st, cmd):
    """f_76cb9: one menu command (ignored while the player is not an ant or the spider, G:0A06 > 1)."""
    if s16(st.u16(G, 0xa06)) > 1 or not 0 <= cmd <= 0xc:
        return
    fx = st.player.effect
    if cmd == 0:
        fx(st, 'help')
    elif cmd in (1, 2, 3):
        fx(st, 'voice', 0x2b04 + cmd)
        recruit(st, (5, 10, 1000)[cmd - 1])
    elif cmd in (4, 5):
        fx(st, 'voice', 0x2b04 + cmd)
        player.release_recruits(st, cmd - 4)
    elif cmd == 6:
        _target_mode(st, 0xa)
    elif cmd == 7:
        player.alarm_mode(st, 1 if st.u16(G, 0x104e) == 0 else 0, 0)
    elif cmd == 8:
        view = st.u16(G, 0x48c)
        if view == 1 and player.act_on_cell(st, view, s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))) != -1:
            return
        fx(st, 'sound', 1)
    elif cmd == 9:
        if st.u16(G, 0x48c) == 2 and s16(st.u16(G, 0x48a)) >= 3:
            fx(st, 'anim_timer', 6)
            h = st.u16(G, 0x496) ^ 4
            a = s16(st.u16(G, 0x47c)) + 2 * st.s8(T, h)
            b = s16(st.u16(G, 0x48a)) + 2 * st.s8(T, 8 + h)
            player.queen_scene(st, st.u16(G, 0x48c), a, b, 0x10, 1)
        else:
            fx(st, 'sound', 1)
    elif cmd == 0xa:
        _target_mode(st, 0xb)
    elif cmd == 0xb:
        if st.u16(G, 0x6ac) == 7:
            st.set16(G, 0x6ac, 0)
            fx(st, 'sound', 2, 0x56ee)
        else:
            st.set16(G, 0x6ac, 7)
            fx(st, 'sound', 2, 0x2b77)
    elif cmd == 0xc:
        if st.u16(G, 0x6ac) == 8:
            st.set16(G, 0x6ac, 0)
            fx(st, 'sound', 2, 0x56ee)
        else:
            st.set16(G, 0x6ac, 8)
            fx(st, 'sound', 0x29)


def _yellow_caste(st):
    """The caste the yellow ant leaves behind as a plain ant, and its e: castes 5 / 9 through the load table
    T:0094; caste 1 (bit 3 set) keeps its e in T:0C22."""
    t = st.u16(G, 0x4c2)
    c, e = (t & 0x78) >> 3, 0
    if t & 8:
        if c in (5, 9):
            c = st.s8(T, 0x94 + c)
        elif c == 1:
            e = st.u16(T, 0xc22)
    return c, e


def _new_yellow(st, view, i, o):
    """The clicked ant o (index i) as the new yellow ant's occupant byte, None if refused: brood, the queen's
    second cell's caste 13 and castes 10 / 11 (or no ant) only with the cheat keys and T:0798; castes 5 / 9
    through T:0094; caste 1 hands its e to T:0C22."""
    c = (o & 0x78) >> 3
    if c <= 0 or c > 13 or c in (10, 11):
        if not (player._cheat(st) and st.u16(T, 0x798)):
            return None
    if c in (5, 9):
        o = ((st.s8(T, 0x94 + c) << 3) | (o & 7)) & 0xffff
    elif c == 1:
        st.set16(T, 0xc22, player.get_ant(st, view, i)[4])                 # f_10fcd
    return o


def _add_yellow_ant(st, t, q, e):
    """f_114bd at the yellow ant's position (and the queen's second cell behind her): 0 if no room."""
    g = st.u16
    view, ya, yb = s16(g(G, 0x48c)), s16(g(G, 0x47c)), s16(g(G, 0x48a))
    if not player.add_ant(st, view, ya, yb, t, q, e):
        return 0
    if g(G, 0x4c2) == 0x60:
        h = g(G, 0x496) ^ 4
        if not player.add_ant(st, view, ya + st.s8(T, h), yb + st.s8(T, 8 + h), (t + 8) & 0xffff, q, 0):
            return 0
    return 1


def exchange(st, view, a, b):
    """f_11c18: the player becomes the ant at (view, a, b), 1 if done (also a click on itself), 0 if not.
    - An empty surface cell within squared distance 0x200 of the spider (G:0F12, G:0F34): the player becomes
      the spider. The yellow ant stays behind as a plain ant (f_114bd), and its cell is then cleared.
    - An ant: it leaves its list (f_11121; a queen with her second cell) and the yellow ant takes its place
      and type. Red ants, brood and the odd castes need the cheat keys (Shift + Alt) and T:0798. As the
      yellow ant (G:0A06 == 0), the old yellow ant is added back as a plain ant of the clicked ant's colour.
    """
    g = st.u16
    fx = st.player.effect
    o = player.get_occ(st, view, a, b) & 0xffff
    if s16(o) <= 0:
        if view != 1:
            return 0
        if co.distance(a * 16 + 8, b * 16 + 8, s16(g(G, 0xf12)), s16(g(G, 0xf34))) >= 0x200:
            return 0
        c, e = _yellow_caste(st)
        t = ((g(G, 0x4e2) & 0x80) | g(G, 0x496) | (c << 3)) & 0xffff
        q = 9 if g(G, 0x4c2) == 0x60 else 0
        if not _add_yellow_ant(st, t, q, e):
            return 0
        player.put_yellow(st, s16(g(G, 0x48c)), s16(g(G, 0x47c)), s16(g(G, 0x48a)), g(G, 0x4c2), g(G, 0x496), 0)
        st.set16(G, 0xffc, 0xfffe)
        sa, sb = s16(g(G, 0xf12)) >> 4, s16(g(G, 0xf34)) >> 4
        st.set16(G, 0xf42, sa & 0xffff)
        st.set16(G, 0xf7e, sb & 0xffff)
        st.set16(G, 0xa06, 1)
        for off in (0xfb8, 0x6ac, 0x4e2):
            st.set16(G, off, 0)
        player.stop_action(st, view, sa, sb)                              # f_2f820
        player.set_health(st, 100)
        return 1
    if debug.player_at(st, view, a, b) or mv.is_yellow(o):
        return 1
    c = (o & 0x78) >> 3
    if c == 0xc:                                                        # a queen: her second cell behind her
        h = (o & 7) ^ 4
        a2, b2 = a + st.s8(T, h), b + st.s8(T, 8 + h)
        o2 = player.get_occ(st, view, a2, b2) & 0xffff
    elif c == 0xd:                                                      # her second cell: the queen ahead
        a2, b2, o2 = a, b, o
        a += st.s8(T, o & 7)
        b += st.s8(T, 8 + (o & 7))
        o = player.get_occ(st, view, a, b) & 0xffff
        c = 0xc
    i = player.find_ant_exact(st, view, a, b, o)                        # f_11327
    if c == 0xc:
        i2 = player.find_ant_exact(st, view, a2, b2, o2)
    if i < 0:
        return 0
    if g(G, 0xa06) == 0:
        yc, e = _yellow_caste(st)
        t = ((yc << 3) | g(G, 0x496) | (o & 0x80)) & 0xffff
        if o & 0x80 and not player._cheat(st):
            return 0
        o = _new_yellow(st, view, i, o)
        if o is None:
            return 0
        q = 9 if g(G, 0x4c2) == 0x60 else 0
        view0, ya, yb = s16(g(G, 0x48c)), s16(g(G, 0x47c)), s16(g(G, 0x48a))
        fx(st, 'redraw', view0, ya, yb)                                 # f_0250e
        if q:
            h = g(G, 0x496) ^ 4
            fx(st, 'redraw', view0, ya + st.s8(T, h), yb + st.s8(T, 8 + h))
        fx(st, 'redraw', view, a, b)
        if c == 0xc:
            fx(st, 'redraw', view, a2, b2)
        player.set_ant(st, view, i, 0, 0, 0, 0, 0)
        if c == 0xc:
            player.set_ant(st, view, i2, 0, 0, 0, 0, 0)
        if not _add_yellow_ant(st, t, q, e):
            return 0
    else:
        if o & 0x80 and not player._cheat(st):
            return 0
        o = _new_yellow(st, view, i, o)
        if o is None:
            return 0
        player.set_ant(st, view, i, 0, 0, 0, 0, 0)
        if c == 0xc:
            player.set_ant(st, view, i2, 0, 0, 0, 0, 0)
    st.set16(G, 0x4e2, o & 0x80)
    for off in (0x49a, 0xa06, 0x6ac):
        st.set16(G, off, 0)
    player.set_health(st, 100)
    player.put_yellow(st, view, a, b, o & 0x78, o & 7, 0xff)
    if s16(g(G, 0x4c2)) < 8:
        st.set16(G, 0x502, g(G, 0x496))
    return 1


def exchange_click(st, view, a, b):
    """f_11b81: a map click in the Exchange cursor mode (G:105E == 0x0A): G:1074 = 1, then the swap. Done:
    the mode ends with sound 0x0F (as a queen also a redraw, f_03391, and a voice line); refused: sound 1."""
    st.set16(G, 0x1074, 1)
    fx = st.player.effect
    if exchange(st, view, a, b) == 1:
        cancel_target_mode(st)
        fx(st, 'sound', 0xf)
        if st.u16(G, 0x4c2) == 0x60:
            fx(st, 'redraw_view')                                       # f_03391; f_00f1d is always 1
            fx(st, 'voice', 0x2afe)
    else:
        fx(st, 'sound', 1)


def _spider_walk(st, a, b, k):
    st.set16(G, 0xffc, 0xfffe)
    st.set16(G, 0x10ae, 0xffff)
    st.set16(G, 0xfb8, 0)
    st.set16(G, 0xf42, a & 0xffff)
    st.set16(G, 0xf7e, b & 0xffff)
    st.set16(G, 0xa8e, k & 0xffff)


def spider_click(st, a, b, k):
    """f_756a6: a map click while the player is the spider (from f_74fe0; in the Chase cursor mode G:105E ==
    0x0B, or with k >= 1): an ant on the cell becomes its prey (G:10AE its type, G:0FFC its index, state
    G:0FB8 = 2; in Chase mode also sound 0x0F, G:06AC = 6 and the mode ends); otherwise it walks there
    (G:0F42 / G:0F7E, G:0A8E = k), or in Chase mode just sound 1."""
    chase = st.u16(G, 0x105e) == 0xb
    if s16(k) < 1 and not chase:
        _spider_walk(st, a, b, k)
        return
    o = st.grid(0x6180, a, b)
    i = player.find_ant_exact(st, 1, a, b, o) if o else -1
    if i >= 0:
        st.set16(G, 0x10ae, o)
        st.set16(G, 0xffc, i & 0xffff)
        st.set16(G, 0xfb8, 2)
        if chase:
            st.player.effect(st, 'sound', 0xf)
            st.set16(G, 0x6ac, 6)
            cancel_target_mode(st)
        return
    if chase:
        st.player.effect(st, 'sound', 1)
        return
    _spider_walk(st, a, b, k)
```
{% endraw %}
