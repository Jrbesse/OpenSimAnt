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
] + WALK_CHECKS + [
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
        ok &= v.check(lin, fn, label=label, repeat=repeat, pre=pre, ignore=SCREEN, args_fn=args_fn)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
