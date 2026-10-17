"""Verify the black nest ants against the original (python test_nest.py [scenario-substring ...])."""
import sys

from verify import Verifier
from simant_ref import nest
from simant_ref import surface as sf
from simant_ref.state import SIM, G, T

TICK, LOOP = 0x79a4d, 0x799e0
BX, BY, BSTATE, BTYPE, BE, CELLS = nest.BX, nest.BY, nest.BSTATE, nest.BTYPE, nest.BE, nest.CELLS


def live(st):
    n = st.u16(G, 0xda8)
    return [i for i in range(n) if st.u8(SIM, BTYPE + i)]


def with_player(fn):
    def run(st, *args):
        st.player = sf.NoPlayer()
        return fn(st, *args)
    return run


# forced scenarios: (label, state, caste or None = keep, red, e or None = keep[, opts])
# opts: pos=fn(ant) -> (col, depth) to move the ant first; cell=value written into its cell afterwards;
#       dirt=value for the dirt under it; g={off: value} / t={off: value} globals set before the call
SCENARIOS = [
    ('bored', 0, None, False, None),
    ('nesting worker', 1, 2, False, 0),
    ('nesting worker up', 1, 2, False, 8),
    ('nesting carrier down', 1, 1, False, 3),
    ('nesting carrier up', 1, 1, False, 0x0b),
    ('nesting soldier', 1, 6, False, None),
    ('foraging (go out)', 2, None, False, None),
    ('got food', 3, 3, False, None),
    ('dig in worker', 4, 2, False, None),
    ('dig in soldier', 4, 6, False, None),
    ('dig in male', 4, 4, False, None),
    ('dig out (go out)', 5, 5, False, None),
    ('defense', 6, 6, False, None),
    ('attack (go out)', 7, 6, False, None),
    ('brood', 8, 0, False, None),
    ('queen head', 9, 12, False, None),
    ('queen abdomen', 9, 13, False, None),
    ('fighting', 10, 14, False, 0x10),
    ('fighting queen win', 10, 14, False, 0x60),
    ('resting', 13, None, False, None),
    ('pre-flight', 14, 4, False, None),
    ('state 17', 17, None, False, None),
    ('state 19', 19, None, False, None),
    ('invader move', 1, 2, True, None),
    ('invader attack', 7, 6, True, None),
    ('invader fighting', 10, 14, True, 0x90),
    ('exit shaft', 2, 2, False, None, dict(pos=lambda a: (32, 1))),
    ('exit shaft new hole', 2, 2, False, None, dict(pos=lambda a: (32, 1), t={0x224 + 32: 0})),
    ('exit shaft new hole house', 2, 2, False, None, dict(pos=lambda a: (32, 1), t={0x224 + 32: 0},
                                                          g={0xf24: 1})),
    ('exit no shaft', 2, 2, False, None, dict(pos=lambda a: ((a * 7) % 62 + 1, 1))),
    ('climb from row 2', 5, 5, False, None, dict(pos=lambda a: (32, 2))),
    ('got food full cell', 3, 3, False, None, dict(dirt=0x13)),
    ('got food at top', 3, 3, False, None, dict(pos=lambda a: (32, 1))),
    ('invader on phantom', 1, 2, True, None, dict(cell=0x12)),
    ('invader on brood', 1, 2, True, None, dict(cell=0x03)),
    ('invader on queen', 1, 2, True, None, dict(cell=0x61)),
    ('queen head starving', 9, 12, False, None, dict(g={0x10be: 0})),
    ('wander at top', 0, 2, False, None, dict(pos=lambda a: (32, 1))),
    ('wander up, no shaft', 0, 2, False, None, dict(pos=lambda a: ((a * 7) % 62 + 1, 1), heading=0)),
    ('exit shaft blocked', 2, 2, False, None, dict(pos=lambda a: (32, 1), block=True)),
]


def st_dx(i):
    b = VERIFIER.e.read(T, i, 1)[0]
    return b - 256 if b > 127 else b


def ant_args(st, a):
    ant = a[0]
    return (st.u8(SIM, BX + ant), st.u8(SIM, BY + ant), st.u8(SIM, BTYPE + ant))


def sample(st, i, counts=None):
    ants = live(st)
    if i == 0 and counts is not None:
        counts.append(len(ants))
    ants = ants[::max(1, len(ants) // 40)]
    return (ants[i],) if i < len(ants) else None


def main():
    only = sys.argv[1:]
    global VERIFIER
    v = VERIFIER = Verifier()
    ok = True
    port = with_player(nest.nest_ant_tick)
    if not only:
        counts = []
        ok &= v.check(TICK, port, lambda st, i: sample(st, i, counts), label='natural ticks', repeat=40,
                      pre=lambda set16, a: set16(G, 0xf18, a[0]), post_args=ant_args)
        print(f'      (live nest ants per snapshot: {counts})')

    for label, state, caste, red, e, *rest in SCENARIOS:
        if only and not any(o in label for o in only):
            continue
        opts = rest[0] if rest else {}

        def pre(set16, a, state=state, caste=caste, red=red, e=e, opts=opts):
            set8 = set16.byte
            ant = a[0]
            for off, val in opts.get('g', {}).items():
                set16(G, off, val)
            for off, val in opts.get('t', {}).items():
                set8(T, off, val)
            set16(G, 0xf18, ant)
            if 'pos' in opts:
                oc, od = v.e.read(SIM, BX + ant, 1)[0], v.e.read(SIM, BY + ant, 1)[0]
                set8(SIM, CELLS + oc * 64 + od, 0)
                nc, nd = opts['pos'](ant)
                set8(SIM, BX + ant, nc)
                set8(SIM, BY + ant, nd)
            set8(SIM, BSTATE + ant, state)
            t = v.e.read(SIM, BTYPE + ant, 1)[0]
            if caste is not None:
                t = (t & 0x87) | (caste << 3)
            if red:
                t |= 0x80
            set8(SIM, BTYPE + ant, t)
            col, depth = v.e.read(SIM, BX + ant, 1)[0], v.e.read(SIM, BY + ant, 1)[0]
            set8(SIM, CELLS + col * 64 + depth, t)
            if e is not None:
                set8(SIM, BE + ant, e | (0x80 if red and state == 10 else 0))
            if 'heading' in opts:
                t = (t & 0xf8) | opts['heading']
                set8(SIM, BTYPE + ant, t)
                set8(SIM, CELLS + col * 64 + depth, t)
            if opts.get('block'):
                ea = v.e.read(T, 0x224 + col, 1)[0]
                for d in range(8):
                    na, nb = ea + st_dx(d), col + st_dx(8 + d)
                    if 0 <= na < 128 and 0 <= nb < 64:
                        set8(SIM, 0x180 + na * 64 + nb, 0x50)
            if 'cell' in opts:
                set8(SIM, CELLS + col * 64 + depth, opts['cell'])
            if 'dirt' in opts:
                set8(SIM, nest.DIRT + col * 64 + depth, opts['dirt'])

        ok &= v.check(TICK, port, sample, label=f'forced {label}', repeat=40, pre=pre, post_args=ant_args)

    if not only:
        ok &= v.check(LOOP, with_player(nest.black_nest_loop), label='BlackNestLoop', repeat=3)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
