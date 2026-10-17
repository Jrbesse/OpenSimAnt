"""The yellow ant's menu commands (f_76cb9, via f_2f906 from the pop-up menu f_67e93): recruit, release,
exchange, alarm, dig a hole, start brood, and the spider's chase / hunt. See SIM_NOTES "The yellow ant's menu
and commands".

Screen-only effects go to st.player.effect: 'sound' (f_00ed8), 'voice' (f_00ea1), 'help' (f_76eb5),
'pause' (f_2f816, the pick-a-target cursor mode), 'anim_timer' (f_0125f).
"""
from .state import SIM, G, T
from . import player
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


def exchange_click(st, view, a, b):
    """f_11b81 → f_11c18: not ported yet."""
    raise NotImplementedError('f_11b81 / f_11c18 (Exchange)')


def chase_click(st, a, b, k):
    """f_756a6: not ported yet."""
    raise NotImplementedError('f_756a6 (Chase)')
