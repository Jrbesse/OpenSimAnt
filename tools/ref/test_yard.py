"""Verify the yard layer (sec8 f_68513) against the original (python test_yard.py [name-substring ...])."""
import sys

from verify import Verifier
from simant_ref import yard
from simant_ref import surface as sf
from simant_ref.state import G, T, SIM, DS

DSL = DS * 16
# screen-only state the port leaves to effect hooks: status-line message slots, the dirty-cell map
SCREEN = ((DSL + 0x19c6, DSL + 0x19d0), (DSL + 0x299a, DSL + 0x29a4), (DSL + 0x15c4, DSL + 0x15c4 + 0x1000))


def port(fn, nargs=0):
    """Wrap a port routine: give it NoPlayer hooks and drop the extra args the scenarios pass."""
    def run(st, *args):
        st.player = sf.NoPlayer()
        return fn(st, *args[:nargs])
    return run


def setter(g=(), t=(), g8=(), t8=(), sim8=(), once=None):
    """pre hook: set G / T words (and bytes); with args (i,), `once` entries only before the first call."""
    def pre(set16, a):
        first = not a or a[0] == 0
        for seg, items, byte in ((G, g, False), (T, t, False), (G, g8, True), (T, t8, True), (SIM, sim8, True)):
            for off, val in items:
                (set16.byte if byte else set16)(seg, off, val)
        if once and first:
            once(set16)
    return pre


def colonies(pattern, g=(), t=()):
    """`once` hook: plant yard colonies, pattern = [(col, row, black, red), ...]."""
    def plant(set16):
        for col, row, b, r in pattern:
            set16.byte(T, 0xa4 + col * 16 + row, b)
            set16.byte(T, 0x164 + col * 16 + row, r)
        for off, val in g:
            set16(G, off, val)
        for off, val in t:
            set16(T, off, val)
    return plant


def init(g=(), t=(), every_g=(), every_t=()):
    """pre hook (for args idx_args): set g / t before the first call, every_g / every_t before each call."""
    return setter(g=every_g, t=every_t, once=colonies((), g=g, t=t))


def ant_spot(st, i):
    """args for foot_stamp: a few cells up-left of a live surface ant (or a fixed spot)."""
    n = st.u16(G, 0xd6a)
    ants = [j for j in range(n) if st.u8(SIM, 0xad3b + j)]
    if not ants:
        return (20 + i, 30)
    j = ants[(i * 7) % len(ants)]
    return (st.u8(SIM, 0xa180 + j) - (i % 5), st.u8(SIM, 0xa569 + j) - (i % 3))


def idx_args(st, i):
    return (i,)


SOUND_ON = ((0x7c8, 0),)
QUEENS = ((0x383a, 100), (0x6aa, 30), (0x7c8, 7), (0x73a, 9), (0x850, 3))      # flying queens, the clock passed
FLYING = ((0x254, 1), (0x2be, 0x150), (0x32c, 0x40), (0x240, 2), (0x22c, 200))  # the bird in flight
SPRAWL = [(c, r, (c * 37 + r * 11) % 260 if (c + r) % 3 else 0, (c * 13 + r * 29) % 260 if (c + r) % 4 == 1 else 0)
          for c in range(12) for r in range(16)]
STRONG = [(c, r, 0xf8, 0) for c in range(4, 9) for r in range(3, 9)] + [(c, r, 0, 0xf9) for c in range(9, 12)
                                                                     for r in range(9, 14)]
HOUSE = [(c, r, 9, 0) for c in range(2) for r in range(16)] + [(3, r, 9, 0) for r in range(5)] + [(10, 3, 0, 40)]
DYING_REDS = [(11, r, 0, 1) for r in range(16) if r != 8] + [(10, r, 5, 0) for r in range(16)]

CHECKS = [
    # (label, original, port, repeat, pre, args_fn)
    ('yard step', 0x68513, port(yard.yard_step), 300, None, None),
    ('yard step sound', 0x68513, port(yard.yard_step), 300, setter(t=SOUND_ON), None),
    ('yard step colonies', 0x68513, port(yard.yard_step, 0), 300,
     setter(once=colonies(SPRAWL)), idx_args),
] + [
    (f'human walk {s}', 0x68e30, port(yard.human_walk), 60,
     setter(t=((0xc48, s), (0xc46, 0), (0xc44, 0))), None) for s in list(range(16)) + [20, 21, 30, 31, 32, 33, 34]
] + [
    (f'human walk long {p}', 0x68e30, port(yard.human_walk), 800,
     setter(g=((0x7ca, p[0]), (0x7cc, p[1])), t=((0xc48, 0), (0xc46, 0), (0xc44, 0))), None)
    for p in ((0, 2), (0, 5), (0, 9), (0, 12), (1, 1), (1, 2), (1, 3), (2, 6), (0, 0), (5, 7))   # its path
] + [
    ('human walk arrived', 0x68e30, port(yard.human_walk), 5, setter(t=((0xc44, 1),)), None),
    ('human roam', 0x68659, port(yard.human_roam), 400, None, None),
] + [
    (f'human roam mode {m}', 0x68659, port(yard.human_roam), 300,
     setter(t=((0xc48, 0x26), (0xc28, m)), g=((0x202, 1 if m in (3, 4) else 0),)), None) for m in range(6)
] + [
    ('human roam to mow', 0x68659, port(yard.human_roam), 1500, setter(t=((0xc48, 0x26), (0xc28, 2))), None),
    ('human roam rain', 0x68659, port(yard.human_roam), 200, setter(t=((0xc48, 0x26), (0xc28, 1)),
                                                                     g=((0x352, 1), (0x202, 0))), None),
    ('human roam full', 0x68659, port(yard.human_roam), 200, setter(t=((0xc48, 0x26), (0xc28, 1)),
                                                                     g=((0xeac, 0), (0x202, 0))), None),
] + [
    (f'human roam over player {p}', 0x68659, port(yard.human_roam, 0), 400,
     setter(once=lambda s16, p=p: [s16(G, 0x7ca, p[0]), s16(G, 0x7cc, p[1])]), idx_args)
    for p in ((9, 11), (4, 4), (8, 3), (1, 0), (7, 14), (9, 13))
] + [
    (f'human roam mowing over player {p}', 0x68659, port(yard.human_roam, 0), 600,
     setter(once=lambda s16, p=p: [s16(G, 0x7ca, p[0]), s16(G, 0x7cc, p[1]), s16(T, 0xc48, 0x26), s16(T, 0xc28, 3),
                                   s16(G, 0x202, 1), s16(G, 0x488, 99)] + [s16(G, 0x334 + c * 2, 0xffff)
                                                                          for c in range(12)]), idx_args)
    for p in ((8, 3), (5, 7), (10, 12))
] + [
    ('foot stamp', 0x69f53, port(yard.foot_stamp, 2), 40, None, ant_spot),
    ('foot stamp across', 0x69f53, port(yard.foot_stamp, 2), 40, setter(t=((0xc30, 1),)), ant_spot),
    ('foot stamp spider', 0x69f53, port(yard.foot_stamp, 2), 3, setter(g=((0xf42, 22), (0xf7e, 33))),
     lambda st, i: (20, 30)),
    ('mower', 0x6a08a, port(yard.mower), 3, None, lambda st, i: (40, 20)),
    ('mower spider', 0x6a08a, port(yard.mower), 3, setter(g=((0xf0c, 1),)), lambda st, i: (40, 20)),
    ('mower tutorial', 0x6a08a, port(yard.mower), 2, setter(g=((0xeac, 0),)), lambda st, i: (40, 20)),
] + [
    (f'mow heading {k}', 0x68d07, lambda st, c, r: yard.mow_heading(sf_player(st), c, r), 40,
     setter(g=tuple((0x334 + c * 2, m) for c in range(12))), lambda st, i: (i % 13 - 1 if i % 13 else 0, i % 17 - 1))
    for k, m in ((0, 0), (1, 0xffff), (2, 0x5a5a))
] + [
    ('bird crossing idle', 0x6959f, port(yard.bird_crossing), 50, setter(g=((0x383a, 100),)), None),
    ('bird crossing queens', 0x6959f, port(yard.bird_crossing, 0), 300, init(g=QUEENS), idx_args),
    ('bird crossing queens sound', 0x6959f, port(yard.bird_crossing, 0), 300, init(g=QUEENS, t=SOUND_ON), idx_args),
    ('bird crossing west', 0x6959f, port(yard.bird_crossing), 50,
     setter(g=((0x383a, 100), (0x6aa, 30), (0x7ca, 3))), None),
    ('bird crossing leaving', 0x6959f, port(yard.bird_crossing, 0), 80,
     init(g=((0x10a0, 2), (0x10ac, 100), (0x10ba, 60))), idx_args),
    ('bird crossing off map', 0x6959f, port(yard.bird_crossing, 0), 80,
     init(g=((0x10a0, 1), (0x10ac, 0x1f8), (0x10ba, 60), (0x210, 200), (0x208, 900))), idx_args),
    ('bird start', 0x6986c, port(yard.bird), 300, setter(g=((0x220, 0), (0x222, 0))), None),
    ('bird forced', 0x6986c, port(yard.bird, 0), 600, init(g=((0x220, 0), (0x222, 0)), every_g=((0xb20, 0x8d),)),
     idx_args),
    ('bird flying sound', 0x6986c, port(yard.bird, 0), 600, init(g=FLYING, t=SOUND_ON), idx_args),
    ('bird lands', 0x6986c, port(yard.bird, 0), 400, init(g=FLYING, every_g=((0x506, 2),), every_t=((0xc28, 0),)),
     idx_args),
    ('bird swoops', 0x6986c, port(yard.bird, 0), 100,
     init(g=FLYING + ((0x22c, 60), (0x4be, 0x150), (0x4c6, 0x48)), t=SOUND_ON, every_g=((0x506, 1),)), idx_args),
    ('bird landed', 0x6986c, port(yard.bird, 0), 60, init(g=((0x254, 2), (0x244, 10), (0x22c, 0), (0x240, 6))),
     idx_args),
    ('bird swooping', 0x6986c, port(yard.bird, 0), 60, init(g=((0x254, 3), (0x244, 20))), idx_args),
    ('dog', 0x69ba3, port(yard.dog), 300, None, None),
    ('dog bird', 0x69ba3, port(yard.dog), 300, setter(g=((0x254, 1),)), None),
    ('dog walk', 0x69ba3, port(yard.dog), 300, setter(t=((0xc48, 3),)), None),
    ('dog chase', 0x69ba3, port(yard.dog), 300, setter(t=((0xc48, 0x26),) + SOUND_ON, g=((0x202, 1),)), None),
    ('dog bark', 0x69ba3, port(yard.dog, 0), 300, init(g=((0x736, 0), (0x738, 0)), every_t=SOUND_ON), idx_args),
    ('dog chase close', 0x69ba3, port(yard.dog), 30, setter(t=SOUND_ON + ((0xc48, 0x26),), g=(
        (0x202, 1), (0x736, 0), (0x738, 0), (0x624, 0), (0x246, 6), (0x23e, 7), (0x4be, 0x10e), (0x4c6, 0x6c))), None),
] + [
    (f'dog at {x},{y} bird {b}', 0x69ba3, port(yard.dog), 3,
     setter(g=((0x4be, x), (0x4c6, y), (0x624, 0), (0x254, b), (0x506, 0))), None)
    for x, y in ((50, 60), (500, 100), (200, 20), (100, 210), (0x150, 0x30), (0x180, 0x60), (0x120, 0x60),
                 (0x100, 0x40), (0x170, 0x24))
    for b in (0, 1)
] + [
    ('rain none', 0x685ac, port(yard.rain_control), 300, None, None),
    ('rain forced', 0x685ac, port(yard.rain_control), 5, setter(g=((0xb20, 0xa8), (0x352, 0))), None),
    ('rain ending', 0x685ac, port(yard.rain_control, 0), 10, init(g=((0x352, 1), (0x356, 4))), idx_args),
    ('rain house', 0x685ac, port(yard.rain_control), 3, setter(g=((0xb20, 0xa8), (0xf24, 1))), None),
    ('yard colonies', 0x6a1f4, port(yard.yard_colonies, 0), 40, setter(g=((0x7c2, 0),), once=colonies(SPRAWL)),
     idx_args),
    ('yard colonies strong', 0x6a1f4, port(yard.yard_colonies, 0), 40, setter(g=((0x7c2, 0),), once=colonies(STRONG)),
     idx_args),
    ('yard colonies new queens', 0x6a1f4, port(yard.yard_colonies, 0), 40, setter(g=((0x7c2, 0),), once=colonies(
        SPRAWL, g=((0x7c8, 6), (0x850, 5), (0x6aa, 9), (0x73a, 2), (0x105c, 30), (0x1066, 30)), t=((0x2c0, 1),))),
     idx_args),
    ('yard colonies off tick', 0x6a1f4, port(yard.yard_colonies, 0), 3, setter(g=((0x7c2, 5),)), idx_args),
    ('yard colonies dying reds', 0x6a1f4, port(yard.yard_colonies, 0), 3, setter(g=((0x7c2, 0),), once=colonies(
        DYING_REDS)), idx_args),
    ('yard colonies full', 0x6a1f4, port(yard.yard_colonies, 0), 20, setter(g=((0x7c2, 0), (0xeac, 2)),
                                                                           once=colonies(HOUSE)), idx_args),
    ('yard colonies full lose', 0x6a1f4, port(yard.yard_colonies, 0), 2, setter(
        g=((0x7c2, 0), (0xeac, 2), (0x330, 0), (0xaf6, 0), (0xaec, 0), (0xaf2, 0), (0xaf4, 0)),
        once=colonies([(5, 5, 9, 9)])), idx_args),
    ('yard colonies full reds gone', 0x6a1f4, port(yard.yard_colonies, 0), 2, setter(
        g=((0x7c2, 0), (0xeac, 2), (0x350, 0), (0x36e, 3)), once=colonies([(5, 5, 9, 0)])), idx_args),
]


def sf_player(st):
    st.player = sf.NoPlayer()
    return st


def main():
    global VER
    only = sys.argv[1:]
    v = VER = Verifier()
    ok = True
    for label, lin, fn, repeat, pre, args_fn in CHECKS:
        if only and not any(o in label for o in only):
            continue
        ok &= v.check(lin, fn, label=label, repeat=repeat, pre=pre, ignore=SCREEN, args_fn=args_fn,
                      pre_once=label.startswith('human') and args_fn is None)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
