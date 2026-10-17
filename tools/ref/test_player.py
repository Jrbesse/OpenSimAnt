"""Verify the player (yellow ant) routines against the original (python test_player.py [name-substring ...])."""
import sys

from verify import Verifier
from simant_ref import player
from simant_ref import surface as sf
from simant_ref.state import G, T, DS

DSL, GL = DS * 16, G * 16
# screen-only state the port leaves to effect hooks: status-line message slots, the dirty-cell maps
SCREEN = ((DSL + 0x19c6, DSL + 0x19d0), (DSL + 0x299a, DSL + 0x29a4), (DSL + 0x15c4, DSL + 0x15c4 + 0x1000),
          (GL + 0x15c4, GL + 0x15c4 + 0x1000))


def port(fn, nargs=0):
    """Wrap a port routine: give it NoPlayer hooks and drop the extra args the scenarios pass."""
    def run(st, *args):
        st.player = sf.NoPlayer()
        return fn(st, *args[:nargs])
    return run


def setter_g(g):
    def pre(set16, a):
        for off, val in g:
            set16(G, off, val)
    return pre


def tick_args(st, i):
    return (i,)


def yellow(view=None, pos=None, t=None, colour=None, heading=None, hp=None, g=(), tt=(), tile=None, tick=True):
    """pre hook: place / configure the yellow ant before the first call; with tick, G:0F08 = call index
    before every call (the routine reads the tick but does not advance it)."""
    def pre(set16, a):
        i = a[0] if a else 0
        if tick:
            set16(G, 0xf08, i)
        if i:
            return
        for off, val in ((0x48c, view), (0x4c2, t), (0x4e2, colour), (0x496, heading), (0xf78, hp)):
            if val is not None:
                set16(G, off, val)
        if pos is not None:
            set16(G, 0x47c, pos[0])
            set16(G, 0x48a, pos[1])
        for off, val in g:
            set16(G, off, val)
        for off, val in tt:
            set16(T, off, val)
        if tile is not None:
            v = view if view is not None else 2
            base = {1: 0x180, 2: 0x2180, 3: 0x3180}[v]
            from simant_ref.state import SIM
            set16.byte(SIM, base + pos[0] * 64 + pos[1], tile)
    return pre


def sweep(*ranges, seed=1):
    """args_fn: pseudo-random args, one value per range (lo, hi inclusive)."""
    def args(st, i):
        x = (seed * 7919 + i * 104729) & 0xffffffff
        out = []
        for lo, hi in ranges:
            x = (x * 1103515245 + 12345) & 0x7fffffff
            out.append(lo + (x >> 8) % (hi - lo + 1))
        return tuple(out)
    return args


def walker(view, start, target, mode=0, tv=None):
    """A yellow ant walking with f_7d24f: (port fn, args_fn, pre). Each call's answer (from the port, which
    must equal the original's) moves it; G:0AB6 / G:0AC6 track its last cell as f_7b7b8 does."""
    tv = view if tv is None else tv
    w = dict(pos=start, prev=(-1, -1), last=-1)

    def fn(st, *args):
        st.player = sf.NoPlayer()
        r = player.step_to_cursor(st, *args)
        w['last'] = r
        return r

    def args_fn(st, i):
        if i == 0:
            w['pos'], w['prev'], w['last'] = start, (-1, -1), -1
        elif w['last'] >= 0:
            d = w['last']
            w['prev'] = w['pos']
            w['pos'] = (w['pos'][0] + st.s8(T, d), w['pos'][1] + st.s8(T, 8 + d))
        return (view,) + w['pos'] + (tv,) + target

    def pre(set16, a):
        set16(G, 0xab6, w['prev'][0])
        set16(G, 0xac6, w['prev'][1])
        set16(G, 0xaf8, tv)
        set16(G, 0xad6, target[0])
        set16(G, 0xae8, target[1])
        set16(G, 0xa8e, mode)
        if a[1:3] == start and w['last'] == -1:
            set16(G, 0xd6c, 0xfffe)
    return fn, args_fn, pre


WALKS = [
    (1, (60, 30), (90, 40)), (1, (60, 30), (10, 5)), (1, (5, 60), (120, 2)), (1, (100, 10), (20, 55)),
    (1, (34, 20), (34, 50)), (1, (64, 32), (0, 0)), (2, (34, 9), (10, 30)), (2, (34, 9), (50, 40)),
    (2, (20, 20), (34, 0)), (3, (32, 12), (5, 40)), (2, (34, 9), (20, 0)), (1, (60, 30), (60, 30)),
]
WALK_CHECKS = []
for k, (wv, ws, wt) in enumerate(WALKS):
    for wm in ((0, 2) if wv > 1 else (0,)):
        fn_, args_, pre_ = walker(wv, ws, wt, wm)
        WALK_CHECKS.append((f'walk {k} view {wv} {ws}->{wt} mode {wm}', 0x7d24f, fn_, 150, pre_, args_))
for k, (wv, ws, tv) in enumerate(((1, (60, 30), 2), (1, (100, 50), 3), (2, (30, 20), 1), (3, (32, 12), 2))):
    fn_, args_, pre_ = walker(wv, ws, (40, 20), 0, tv=tv)
    WALK_CHECKS.append((f'walk out {k} view {wv} -> {tv}', 0x7d24f, fn_, 150, pre_, args_))


def as_yellow(t, hp=None, g=(), tt=(), kbd=None, plant=(), pos_args=True):
    """pre hook for the cell actions: before every call the yellow ant (type t) stands at the call's
    (view, ya, yb) args; `plant` = [(seg, off, byte)] written before the first call; kbd = BIOS flags."""
    def pre(set16, a):
        if pos_args and a:
            set16(G, 0x48c, a[0])
            set16(G, 0x47c, a[1])
            set16(G, 0x48a, a[2])
        set16(G, 0x4c2, t)
        if hp is not None:
            set16(G, 0xf78, hp)
        for off, val in g:
            set16(G, off, val)
        for off, val in tt:
            set16(T, off, val)
        VER.e.uc.mem_write(0x417, bytes([kbd or 0]))
        for seg, off, val in plant:
            if VER.e.read(seg, off, 1)[0] != val:
                set16.byte(seg, off, val)
    return pre


def near(view, spread=2, seed=1):
    """args (view, ya, yb, ta, tb): a yellow ant somewhere and a target next to it."""
    hi_a = 0x7f if view == 1 else 0x3f
    base = sweep((view, view), (1, hi_a - 1), (1, 0x3e), (-spread, spread), (-spread, spread), seed=seed)

    def args(st, i):
        v, a, b, da, db = base(st, i)
        return (v, a, b, a + da, b + db)
    return args


def cell_args(view, seed=1):
    """args (view, a, b) for actions on a cell; the yellow ant stands next to it (pre hook below)."""
    hi_a = 0x7f if view == 1 else 0x3f
    return sweep((view, view), (2, hi_a - 1), (1, 0x3e), seed=seed)


def next_to(t, hp=None, g=(), tt=(), plant=()):
    """pre hook: the yellow ant (type t) stands on the cell just west of the call's (view, a, b)."""
    inner = as_yellow(t, hp=hp, g=g, tt=tt, plant=plant, pos_args=False)

    def pre(set16, a):
        set16(G, 0x48c, a[0])
        set16(G, 0x47c, a[1] - 1)
        set16(G, 0x48a, a[2])
        inner(set16, a)
    return pre


SIM_ = 0x3e1d
NEST_PEBBLES = [(SIM_, 0x2180 + c * 64 + d, v) for c, d, v in ((20, 10, 0x30), (21, 11, 0x30), (34, 0, 0x31),
                                                                (30, 12, 0x30), (40, 20, 0x30))]
NEST_FOOD = [(SIM_, base + c * 64 + 10, v) for base in (0x2180, 0x3180)
             for c, v in ((20, 0x10), (21, 0x11), (22, 0x12), (23, 0x13), (24, 0x10), (25, 0x13))]
LAYER_C = [
    ('drop food nest', 0x12306, port(player.drop_food, 5), 300, as_yellow(0x18), near(2, seed=21)),
    ('drop food red nest', 0x12306, port(player.drop_food, 5), 200, as_yellow(0x38), near(3, seed=22)),
    ('drop food surface', 0x12306, port(player.drop_food, 5), 300, as_yellow(0x18), near(1, seed=23)),
    ('drop food cheat', 0x12306, port(player.drop_food, 5), 50, as_yellow(0x18, kbd=0x09), near(2, seed=24)),
    ('drop food wrong type', 0x12306, port(player.drop_food, 5), 20, as_yellow(0x10), near(2, seed=25)),
    ('drop pebble nest', 0x12606, port(player.drop_pebble, 5), 300, as_yellow(0x28), near(2, seed=26)),
    ('drop pebble red nest', 0x12606, port(player.drop_pebble, 5), 200, as_yellow(0x48), near(3, seed=27)),
    ('drop pebble surface', 0x12606, port(player.drop_pebble, 5), 300, as_yellow(0x28), near(1, seed=28)),
    ('drop pebble at exits', 0x12606, port(player.drop_pebble, 5), 60, as_yellow(0x28),
     lambda st, i: (2, 34 + (i % 3) - 1, 1, 34, 0) if i % 2 else (1, 20 + i % 3 - 1, 33, 20, 32)),
    ('drop pebble cheat', 0x12606, port(player.drop_pebble, 5), 30, as_yellow(0x48, kbd=0x0a), near(1, seed=29)),
    ('drop brood nest', 0x12820, port(player.drop_brood, 5), 300, as_yellow(8, tt=((0xc22, 0x01),)), near(2, seed=30)),
    ('drop brood red', 0x12820, port(player.drop_brood, 5), 200, as_yellow(8, tt=((0xc22, 0x83),)), near(3, seed=31)),
    ('drop brood surface', 0x12820, port(player.drop_brood, 5), 100, as_yellow(8, tt=((0xc22, 0x02),)),
     near(1, seed=32)),
    ('drop brood cheat', 0x12820, port(player.drop_brood, 5), 30, as_yellow(8, kbd=0x0b, tt=((0xc22, 0x01),)),
     near(2, seed=33)),
] + [
    (f'drop load {t:#x}', 0x1317c, port(player.drop_load, 5), 100, as_yellow(t, tt=((0xc22, 0x01),)),
     near(v, seed=35 + k)) for k, (t, v) in enumerate(((8, 2), (0x18, 1), (0x28, 3), (0x38, 2), (0x48, 1),
                                                       (0x10, 2)))
] + [
    (f'pick up {k} view {v} type {t:#x}', 0x131ea, port(player.pick_up, 3), 500,
     next_to(t, hp=hp, plant=NEST_PEBBLES), cell_args(v, seed=50 + k))
    for k, (v, t, hp) in enumerate(((2, 0x10, 80), (3, 0x10, 80), (1, 0x10, 80), (1, 0x30, 80), (2, 0x30, 80),
                                    (2, 0x10, 5), (1, 0x20, 80), (1, 0x18, 80), (2, 0x40, 80)))
] + [
    ('pick up low health', 0x131ea, port(player.pick_up, 3), 300, next_to(0x20, g=((0x1044, 1),)),
     cell_args(1, seed=60)),
    ('pick up low health nest', 0x131ea, port(player.pick_up, 3), 300, next_to(0x20, g=((0x1044, 1),)),
     cell_args(2, seed=61)),
    ('take pebble entrance', 0x12a1e, port(player.take_pebble, 3), 6, next_to(0x10, plant=(
        (SIM_, 0x180 + 20 * 64 + 32, 0x51), (SIM_, 0x180 + 121 * 64 + 32, 0x52), (SIM_, 0x180 + 50 * 64 + 9, 0x53))),
     lambda st, i: ((1, 20, 32), (1, 121, 32), (1, 50, 9), (2, 34, 0), (2, 20, 10), (3, 5, 5))[i]),
    ('take pebble house', 0x12a1e, port(player.take_pebble, 3), 3, next_to(0x30, g=((0xf24, 1),), plant=(
        (SIM_, 0x180 + 20 * 64 + 32, 0x51), (SIM_, 0x180 + 50 * 64 + 9, 0x53))),
     lambda st, i: ((1, 20, 32), (1, 50, 9), (1, 51, 9))[i]),
    ('eat food', 0x12de1, port(player.eat, 1), 1, setter_g(((0xf78, 40),)), lambda st, i: (0,)),
    ('eat brood', 0x12de1, port(player.eat, 1), 1, setter_g(((0xf78, 4),)), lambda st, i: (3,)),
    ('eat 2', 0x12de1, port(player.eat, 1), 2, setter_g(((0xf78, 40),)), lambda st, i: (2,)),
    ('eat 2 weak', 0x12de1, port(player.eat, 1), 1, setter_g(((0xf78, 8),)), lambda st, i: (2,)),
    ('eat dead', 0x12de1, port(player.eat, 1), 1, setter_g(((0xf78, 0),)), lambda st, i: (0,)),
    ('eat alone', 0x12de1, port(player.eat, 1), 1, setter_g(((0xf78, 50), (0x330, 1))), lambda st, i: (3,)),
    ('found nest', 0x14f59, port(player.found_nest, 2), 4, None,
     lambda st, i: ((20, 10), (100, 50), (0, 5), (127, 5))[i]),
    ('found nest house', 0x14f59, port(player.found_nest, 2), 2, setter_g(((0xf24, 1),)),
     lambda st, i: ((20, 10), (100, 50))[i]),
    ('try found nest', 0x14ee2, port(player.try_found_nest, 2), 200, None, sweep((0, 128), (0, 64), seed=70)),
    ('try found nest house', 0x14ee2, port(player.try_found_nest, 2), 50, setter_g(((0xf24, 1),)),
     sweep((0, 128), (0, 64), seed=71)),
] + [
    (f'act on cell {k} view {v} type {t:#x}', 0x13644, port(player.act_on_cell, 3), 400,
     next_to(t, hp=hp, plant=NEST_PEBBLES, tt=((0xc22, 0x01),)), cell_args(v, seed=80 + k))
    for k, (v, t, hp) in enumerate(((2, 0x10, 80), (2, 0x10, 5), (1, 0x10, 80), (3, 0x30, 80), (2, 0x18, 80),
                                    (1, 0x28, 80), (2, 8, 80), (1, 0x18, 80), (2, 0x40, 80), (1, 0x20, 80)))
] + [
    ('act on cell low health', 0x13644, port(player.act_on_cell, 3), 300, next_to(0x10, g=((0x1044, 1),)),
     cell_args(1, seed=95)),
    ('act new queen fails', 0x13644, port(player.act_on_cell, 3), 3,
     as_yellow(0x40, pos_args=False, g=((0x48c, 1), (0x47c, 60), (0x48a, 2)), tt=((0xc24, 0),),
               plant=[(SIM_, 0x180 + 61 * 64 + 2, 0x51)]), lambda st, i: (1, 60, 2)),
    ('act on cell T:0798', 0x13644, port(player.act_on_cell, 3), 3,
     as_yellow(0x10, pos_args=False, g=((0x48c, 1), (0x47c, 60), (0x48a, 2)), tt=((0x798, 1),),
               plant=[(SIM_, 0x180 + 61 * 64 + 2, 0x51)]), lambda st, i: (1, 60, 2)),
    ('take food nest', 0x1302f, port(player.take_food, 3), 12, next_to(0x10, plant=NEST_FOOD),
     lambda st, i: (2 + i // 6,) + ((20, 10), (21, 10), (22, 10), (23, 10), (24, 10), (25, 10))[i % 6]),
    ('take food nest low health', 0x1302f, port(player.take_food, 3), 6,
     next_to(0x18, g=((0x1044, 1),), plant=NEST_FOOD),
     lambda st, i: (2 + i // 3,) + ((20, 10), (21, 10), (22, 10))[i % 3]),
    ('take pebble nest exit', 0x12a1e, port(player.take_pebble, 3), 2, next_to(0x10, plant=(
        (SIM_, 0x2180 + 34 * 64, 0x31), (SIM_, 0x3180 + 32 * 64, 0x31))),
     lambda st, i: ((2, 34, 0), (3, 32, 0))[i]),
    ('act on cell nest food', 0x13644, port(player.act_on_cell, 3), 12, next_to(0x10, plant=NEST_FOOD),
     lambda st, i: (2 + i // 6,) + ((20, 10), (21, 10), (22, 10), (23, 10), (24, 10), (25, 10))[i % 6]),
]


class QuietPlayer(sf.NoPlayer):
    """Player hooks for checks where the original's f_2f7d0 (player-event UI) is stubbed."""
    def game_event(self, st, n):
        pass


def quiet(fn, nargs=0):
    def run(st, *args):
        st.player = QuietPlayer()
        return fn(st, *args[:nargs])
    return run


def live_ant(view, k=0):
    """args (view, i): the k-th live ant (from the top) of the view's list."""
    def args(st, i):
        f = player._ants(view)
        n = st.s16(G, f['count'])
        live = [j for j in range(n) if st.u8(SIM_, f['type'] + j)]
        if not live:
            return None
        return (view, live[-1 - ((k + i * 7) % len(live))])
    return args


def entrance(nest_view, k=0):
    """(a, b) of a surface entrance of the black (2) or red (3) nest."""
    def get(st):
        base = 0x224 if nest_view == 2 else 0x264
        cols = [c for c in range(64) if st.u8(T, base + c)]
        c = cols[k % len(cols)]
        return st.u8(T, base + c), c
    return get


def yellow_on(view, where, t=0x10, g=(), tt=()):
    """pre hook: put the yellow ant (type t) at view / where (a tuple or a function of the state)."""
    def pre(set16, a):
        st = VER.state_from_emu()
        pos = where(st) if callable(where) else where
        set16(G, 0x48c, view)
        set16(G, 0x47c, pos[0])
        set16(G, 0x48a, pos[1])
        set16(G, 0x4c2, t)
        for off, val in g:
            set16(G, off, val)
        for off, val in tt:
            set16(T, off, val)
    return pre


def boxed_exit(box, t=0x10):
    """pre hook: the yellow ant leaves the black nest at column 32, the cursor in the red nest whose
    entrance is moved onto the black one (so the step there fails); box: rocks all around the entrance."""
    def pre(set16, a):
        st = VER.state_from_emu()
        ea = st.u8(T, 0x224 + 32)
        set16(G, 0x48c, 2)
        set16(G, 0x47c, 32)
        set16(G, 0x48a, 0)
        set16(G, 0x4c2, t)
        set16(G, 0xaf8, 3)
        set16(T, 0x2b0, ea)
        set16(T, 0x2b2, 32)
        if box:
            for da in range(-2, 3):
                for db in range(-2, 3):
                    if (da, db) != (0, 0):
                        set16.byte(SIM_, 0x180 + (ea + da) * 64 + 32 + db, 0x60)
    return pre


LAYER_D = [
    ('enter nest black', 0x7c7e5, port(player.enter_nest), 1, yellow_on(1, entrance(2)), None),
    ('enter nest red', 0x7c7e5, port(player.enter_nest), 1, yellow_on(1, entrance(3)), None),
    ('enter nest queen', 0x7c7e5, port(player.enter_nest), 1, yellow_on(1, entrance(2), t=0x60), None),
    ('enter nest alarm mode', 0x7c7e5, port(player.enter_nest), 1, yellow_on(1, entrance(2), g=((0x104e, 1),)),
     None),
    ('enter nest anywhere', 0x7c7e5, port(player.enter_nest), 1, yellow_on(1, (70, 20)), None),
    ('enter nest jingle', 0x7c7e5, port(player.enter_nest), 1,
     yellow_on(1, entrance(2), g=((0x214, 0), (0x216, 0))), None),
] + [
    (f'leave nest {k}', 0x7c8fe, port(player.leave_nest), 1,
     yellow_on(v, pos, t=t, g=((0xaf8, tv), (0xad6, 60), (0xae8, 30))), None)
    for k, (v, pos, t, tv) in enumerate((
        (2, (34, 0), 0x10, 1), (2, (34, 0), 0x10, 2), (2, (34, 0), 0x10, 3), (2, (34, 0), 0x60, 1),
        (3, (32, 0), 0x10, 1), (3, (32, 0), 0x10, 3), (3, (32, 0), 0x10, 2), (2, (10, 0), 0x10, 1),
        (3, (50, 0), 0x10, 1), (2, (20, 0), 0x10, 3)))
] + [
    ('leave nest cursor step fails', 0x7c8fe, port(player.leave_nest), 1, boxed_exit(False), None),
    ('leave nest boxed in', 0x7c8fe, port(player.leave_nest), 1, boxed_exit(True), None),
    ('leave nest boxed in queen', 0x7c8fe, port(player.leave_nest), 1, boxed_exit(True, t=0x60), None),
] + [
    (f'alarm mode {on} {q} view {v}', 0x76a37, port(player.alarm_mode, 2), 1, setter_g(((0x48c, v),)),
     lambda st, i, on=on, q=q: (on, q)) for on in (0, 1) for q in (0, 1) for v in (1, 2)
] + [
    ('stop action', 0x757dd, port(player.stop_action, 3), 3, None, sweep((1, 3), (0, 63), (0, 63), seed=90)),
] + [
    (f'attack view {v} type {t:#x} {k}', 0x7c5ab, quiet(player.attack_player, 2), 6,
     yellow_on(yv, ypos, t=t, g=g), live_ant(v, k))
    for k, (v, yv, ypos, t, g) in enumerate((
        (2, 2, (34, 9), 0x10, ()), (2, 2, (34, 9), 0x30, ()), (1, 1, (60, 30), 0x10, ()),
        (1, 1, (60, 30), 0x30, ()), (3, 3, (32, 12), 0x10, ()), (2, 2, (34, 9), 0x60, ()),
        (2, 2, (34, 9), 0x10, ((0xa8e, 3), (0x8da, 2))), (1, 1, (60, 30), 0x90, ()),
        (2, 2, (34, 9), 0x10, ((0x4e2, 1),)),
    ))
] + [
    ('attack T:0C14', 0x7c5ab, quiet(player.attack_player, 2), 4, yellow_on(2, (34, 9), tt=((0xc14, 1),)),
     live_ant(2, 3)),
]


CHECKS = [
    ('is walkable surface', 0x1323e, port(player.is_walkable, 7), 600,
     None, sweep((0, 1), (-2, 129), (-2, 65), (0, 3), (0, 127), (0, 63), (0, 1))),
    ('is walkable nest', 0x1323e, port(player.is_walkable, 7), 3000,
     None, sweep((2, 3), (-1, 64), (-1, 3), (1, 3), (0, 63), (0, 3), (0, 1), seed=2)),
    ('is walkable nest deep', 0x1323e, port(player.is_walkable, 7), 1000,
     None, sweep((2, 3), (0, 63), (0, 63), (2, 3), (0, 63), (0, 63), (0, 1), seed=3)),
    ('is walkable house', 0x1323e, port(player.is_walkable, 7), 300, setter_g(((0xf24, 1),)),
     sweep((1, 1), (0, 127), (0, 63), (1, 1), (0, 127), (0, 63), (0, 0), seed=4)),
    ('is open ground', 0x1145c, port(player.is_open_ground, 3), 2000, None,
     sweep((-1, 4), (-1, 128), (-1, 64), seed=5)),
    ('get occupant', 0x11737, port(player.get_occ, 3), 2000, None, sweep((-1, 4), (-1, 128), (-1, 64), seed=6)),
    ('food at', 0x116f7, port(player.food_at, 3), 1500, None, sweep((1, 3), (-1, 128), (-1, 64), seed=7)),
    ('at exit', 0x13791, port(player.at_exit, 3), 1500, None, sweep((1, 3), (-1, 128), (-1, 64), seed=8)),
    ('can drop', 0x133f9, port(player.can_drop, 3), 1500, None, sweep((1, 3), (-1, 128), (-1, 64), seed=9)),
    ('can drop house', 0x133f9, port(player.can_drop, 3), 300, setter_g(((0xf24, 1),)),
     sweep((1, 1), (0, 127), (0, 63), seed=10)),
    ('find ant', 0x11246, port(player.find_ant, 6), 800, None,
     sweep((1, 3), (0, 127), (0, 63), (0, 0x40), (0x40, 0xff), (0x78, 0xff), seed=11)),
    ('set ant', 0x11121, port(player.set_ant, 7), 300, None,
     sweep((1, 3), (-1, 400), (0, 63), (0, 63), (0, 255), (0, 20), (0, 255), seed=12)),
    ('add ant', 0x114bd, port(player.add_ant, 6), 200, None,
     sweep((1, 3), (0, 63), (0, 63), (0x08, 0xf8), (0, 20), (0, 255), seed=13)),
    ('clear occupant', 0x118c4, port(player.clear_occ_if, 4), 500, None,
     sweep((1, 3), (0, 127), (0, 63), (0, 2), seed=14)),
    ('take yellow', 0x11918, port(player.take_yellow, 5), 3, None, lambda st, i: (2, 34, 9, 0x10, 2)),
    ('take yellow queen', 0x11918, port(player.take_yellow, 5), 3, setter_g(((0x4c2, 0x60),)),
     lambda st, i: (2, 34, 9, 0x60, 2)),
    ('move yellow', 0x11a3e, port(player.move_yellow, 5), 60, None,
     sweep((0, 3), (0, 63), (0, 63), (0x10, 0x10), (0, 7), seed=15)),
    ('move yellow queen', 0x11a3e, port(player.move_yellow, 5), 60, setter_g(((0x4c2, 0x60),)),
     sweep((1, 3), (1, 62), (1, 62), (0x60, 0x60), (0, 7), seed=16)),
    ('jingle', 0x0cd37, port(player.jingle), 5, setter_g(((0x214, 0), (0x216, 0))), None),
    ('jingle wait', 0x0cd37, port(player.jingle), 5, None, None),
] + WALK_CHECKS + LAYER_C + LAYER_D + [
    # (label, original, port, repeat, pre, args_fn)
    ('upkeep', 0x7bf7e, port(player.yellow_tick), 200, yellow(), tick_args),
    ('upkeep queen', 0x7bf7e, port(player.yellow_tick), 200, yellow(t=0x60, heading=2), tick_args),
    ('upkeep queen weak', 0x7bf7e, port(player.yellow_tick), 300, yellow(t=0x60, heading=6, hp=30), tick_args),
    ('upkeep queen edge', 0x7bf7e, port(player.yellow_tick), 100, yellow(t=0x60, heading=0, pos=(1, 2)),
     tick_args),
    ('upkeep red queen', 0x7bf7e, port(player.yellow_tick), 200,
     yellow(view=3, pos=(32, 12), t=0x60, colour=1, heading=4), tick_args),
    ('upkeep queen surface', 0x7bf7e, port(player.yellow_tick), 50,
     yellow(view=1, pos=(60, 30), t=0x60, heading=2), tick_args),
    ('upkeep surface', 0x7bf7e, port(player.yellow_tick), 100, yellow(view=1, pos=(60, 30)), tick_args),
    ('upkeep flooded', 0x7bf7e, port(player.yellow_tick), 100, yellow(pos=(34, 9), tile=0x50), tick_args),
    ('upkeep dying', 0x7bf7e, port(player.yellow_tick), 90, yellow(hp=0), tick_args),
    ('upkeep dying low', 0x7bf7e, port(player.yellow_tick), 90, yellow(hp=3, g=((0xfba, 50),)), tick_args),
    ('upkeep invincible', 0x7bf7e, port(player.yellow_tick), 70, yellow(hp=5, tt=((0xc16, 1),)), tick_args),
    ('upkeep spider', 0x7bf7e, port(player.yellow_tick), 20, yellow(g=((0xa06, 1),)), tick_args),
] + [
    (f'upkeep in dirt {p}', 0x7bf7e, port(player.yellow_tick), 3, yellow(pos=p, tick=False), tick_args)
    for p in ((20, 20), (40, 30), (10, 1), (50, 0), (5, 1), (34, 2))
] + [
    (f'upkeep red in dirt {p}', 0x7bf7e, port(player.yellow_tick), 3,
     yellow(view=3, colour=1, pos=p, tick=False), tick_args)
    for p in ((20, 20), (12, 1), (50, 0))
] + [
    (f'upkeep queen in dirt {p}', 0x7bf7e, port(player.yellow_tick), 3,
     yellow(t=0x60, heading=h, pos=p, tick=False), tick_args)
    for p, h in (((20, 20), 2), ((40, 1), 4), ((12, 30), 1))
]


def main():
    global VER
    only = sys.argv[1:]
    v = VER = Verifier()
    ok = True
    for label, lin, fn, repeat, pre, args_fn in CHECKS:
        if only and not any(o in label for o in only):
            continue
        # UI: scroll to the yellow ant, redraw, menu check marks; the player-event UI where hooks are quiet
        v.extra_stubs = (0x01aa7, 0x03381, 0x22f65) + ((0x2f7d0,) if label.startswith('attack') else ())
        v.e.clock_frozen = not label.startswith('attack')     # the fight animation waits on the clock
        ok &= v.check(lin, fn, label=label, repeat=repeat, pre=pre, ignore=SCREEN, args_fn=args_fn)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
