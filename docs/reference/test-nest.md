---
layout: default
title: "test_nest"
permalink: /reference/test-nest/
---

# test_nest

*`test_nest.py` — Verify the nest ants against the original.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `test_nest.py`]({{ site.baseurl }}/assets/reference/ref/test_nest.py)

Verify the nest ants against the original.

    python test_nest.py [--red] [scenario-substring ...]

Black nest by default (nest.py, overlay section 27), red nest with --red (red_nest.py, resident code).

## At a glance

- **232** lines
- **2 top-level functions**, including `with_player`, `main`

## Source

{% raw %}
```python
"""Verify the nest ants against the original.

    python test_nest.py [--red] [scenario-substring ...]

Black nest by default (nest.py, overlay section 27), red nest with --red (red_nest.py, resident code).
"""
import sys

from verify import Verifier
from simant_ref import nest, red_nest
from simant_ref import surface as sf
from simant_ref.state import SIM, G, T

COLONIES = {
    'black': dict(n=nest.BLACK, mod=nest, tick=0x79a4d, loop=0x799e0, loop_fn=nest.black_nest_loop,
                  own=0x00, health=0x10be),
    'red': dict(n=nest.RED, mod=red_nest, tick=0x0f465, loop=0x0f3f8, loop_fn=red_nest.red_nest_loop,
                own=0x80, health=0x1fe),
}

# forced scenarios: (label, state, caste or None = keep, invader, e or None = keep[, opts])
# e is given without the colour bit: fight winners get the fighter's colour, other values are left alone.
# opts: pos=fn(ant) -> (col, depth) to move the ant first; cell=value (colour of the nest's own ants added)
#       written into its cell afterwards; dirt=value for the dirt under it; ring_dirt=value for the dirt of
#       its 8 neighbours; heading=new heading; block=fill the surface around the entrance;
#       g={off: value} / t={off: value} globals set before the call (an 'entr' key = this colony's entrance
#       table entry for column 32, 'health' = its health)
SCENARIOS = [
    ('bored', 0, None, False, None),
    ('nesting worker', 1, 2, False, 0),
    ('nesting worker up', 1, 2, False, 8),
    ('nesting carrier down', 1, 1, False, 3),
    ('nesting carrier up', 1, 1, False, 0x0b),
    ('nesting carrier on tunnel', 1, 1, False, 3, dict(dirt=0x02)),
    ('nesting soldier', 1, 6, False, None),
    ('foraging (go out)', 2, None, False, None),
    ('got food', 3, 3, False, None),
    ('dig in worker', 4, 2, False, None),
    ('dig in soldier', 4, 6, False, None),
    ('dig in male', 4, 4, False, None),
    ('dig in onto 0x14', 4, 2, False, None, dict(ring_dirt=0x14)),
    ('dig out (go out)', 5, 5, False, None),
    ('defense', 6, 6, False, None),
    ('defense watched', 6, 6, False, None, dict(g={0x48c: 2})),
    ('attack (go out)', 7, 6, False, None),
    ('brood', 8, 0, False, None),
    ('brood tiny colony', 8, 0, False, None, dict(g={0x330: 1, 0x350: 1})),
    ('queen head', 9, 12, False, None),
    ('queen abdomen', 9, 13, False, None),
    ('fighting', 10, 14, False, 0x10),
    ('fighting queen win', 10, 14, False, 0x60),
    ('resting', 13, None, False, None),
    ('pre-flight', 14, 4, False, None),
    ('pre-flight timer', 14, 4, False, None, dict(g={0x8dc: 200, 0x8e8: 200})),
    ('state 17', 17, None, False, None),
    ('state 19', 19, None, False, None),
    ('invader move', 1, 2, True, None),
    ('invader attack', 7, 6, True, None),
    ('invader guard', 6, 6, True, None, dict(g={0x48c: 3})),
    ('invader guard on food', 6, 6, True, None, dict(g={0x48c: 3}, dirt=0x12)),
    ('invader attack on food', 7, 6, True, None, dict(dirt=0x11)),
    ('invader fighting', 10, 14, True, 0x10),
    ('invader tiny type', 1, 0, True, None),
    ('invader on phantom', 1, 2, True, None, dict(cell=0x12)),
    ('invader on brood', 1, 2, True, None, dict(cell=0x03)),
    ('invader on queen', 1, 2, True, None, dict(cell=0x61)),
    ('exit shaft', 2, 2, False, None, dict(pos=lambda a: (32, 1))),
    ('exit shaft new hole', 2, 2, False, None, dict(pos=lambda a: (32, 1), t={'entr': 0})),
    ('exit shaft new hole house', 2, 2, False, None, dict(pos=lambda a: (32, 1), t={'entr': 0},
                                                          g={0xf24: 1})),
    ('exit no shaft', 2, 2, False, None, dict(pos=lambda a: ((a * 7) % 62 + 1, 1))),
    ('climb from row 2', 5, 5, False, None, dict(pos=lambda a: (32, 2))),
    ('got food full cell', 3, 3, False, None, dict(dirt=0x13)),
    ('got food at top', 3, 3, False, None, dict(pos=lambda a: (32, 1))),
    ('queen head starving', 9, 12, False, None, dict(g={'health': 0})),
    ('wander at top', 0, 2, False, None, dict(pos=lambda a: (32, 1))),
    ('wander up, no shaft', 0, 2, False, None, dict(pos=lambda a: ((a * 7) % 62 + 1, 1), heading=0)),
    ('exit shaft blocked', 2, 2, False, None, dict(pos=lambda a: (32, 1), block=True)),
    ('wander onto an enemy', 0, 2, False, None, dict(add=[('here', 0x30, 1, True)])),
    ('resting on an enemy', 13, 2, False, None, dict(add=[('here', 0x10, 1, True)])),
    ('nesting worker on brood', 1, 2, False, 0, dict(add=[('here', 0x03, 8, False)])),
    ('invader on real brood', 1, 2, True, None, dict(add=[('here', 0x03, 8, False)])),
    ('invader on real worker', 1, 2, True, None, dict(add=[('here', 0x10, 1, False)])),
    ('invader on real queen', 1, 2, True, None, dict(add=[('here', 0x61, 9, False)])),
    ('queen pair', 9, 12, False, None, dict(add=[('behind', lambda t: (t & 7) | 0x68, 9, False)])),
    # the Quick Game snapshots have the black nest on screen (G:048c = 2), automatic behaviour (G:0378 = 1)
    # and effects off (T:07b2 = 0): flip those, and force the rarer timings
    ('defense unwatched', 6, 6, False, None, dict(g={0x48c: 1})),
    ('brood hatch', 8, 0, False, None, dict(g={0xf08: 0}, heading=7)),
    ('brood hatch manual', 8, 0, False, None, dict(g={0xf08: 0, 0x378: 0, 0x4a2: 0}, heading=7)),
    ('brood visible', 8, 0, False, None, dict(t={0x7b2: 1})),
    ('queen visible', 9, 12, False, None, dict(t={0x7b2: 1})),
    ('fighting visible', 10, 14, False, 0x10, dict(t={0x7b2: 1})),
    ('resting visible', 13, None, False, None, dict(t={0x7b2: 1})),
    ('state 17 in dirt', 17, None, False, None, dict(dirt=0x20)),
    ('sickly', 2, None, False, None, dict(g={'health': 0})),
    ('egg laying on the tick', 9, 13, False, None, dict(g={0xf08: 0x10})),
    ('go out walled in', 2, 2, False, None, dict(ring_dirt=0x30)),
    ('dig out walled in', 5, 5, False, None, dict(ring_dirt=0x30)),
    ('got food walled in', 3, 3, False, None, dict(ring_dirt=0x30)),
    ('dig in at the bottom', 4, 2, False, None, dict(pos=lambda a: (a % 60 + 2, 63))),
    ('dig in at the left edge', 4, 2, False, None, dict(pos=lambda a: (0, a % 50 + 5))),
    ('got food at the right edge', 3, 3, False, None, dict(pos=lambda a: (63, a % 50 + 5))),
    ('go out at the bottom', 2, 2, False, None, dict(pos=lambda a: (a % 60 + 2, 63))),
    ('queen pair abdomen', 9, 13, False, None, dict(add=[('front', lambda t: (t & 7) | 0x60, 9, False)])),
]


def with_player(fn):
    def run(st, *args):
        st.player = sf.NoPlayer()
        return fn(st, *args)
    return run


def main():
    args = sys.argv[1:]
    colony = 'red' if '--red' in args else 'black'
    only = [a for a in args if a != '--red']
    C = COLONIES[colony]
    n = C['n']
    X, Y, STATE, TYPE, E, CELLS, DIRT = n['x'], n['y'], n['state'], n['type'], n['e'], n['cells'], n['dirt']
    v = Verifier()
    rd = lambda seg, off: v.e.read(seg, off, 1)[0]              # noqa: E731
    sdx = lambda i: rd(T, i) - 256 if rd(T, i) > 127 else rd(T, i)  # noqa: E731

    def live(st):
        return [i for i in range(st.u16(G, n['count'])) if st.u8(SIM, TYPE + i)]

    def sample(st, i, counts=None):
        ants = live(st)
        if i == 0 and counts is not None:
            counts.append(len(ants))
        ants = ants[::max(1, len(ants) // 40)]
        return (ants[i],) if i < len(ants) else None

    def ant_args(st, a):
        ant = a[0]
        return (st.u8(SIM, X + ant), st.u8(SIM, Y + ant), st.u8(SIM, TYPE + ant))

    ok = True
    port = with_player(C['mod'].nest_ant_tick)
    if not only:
        counts = []
        ok &= v.check(C['tick'], port, lambda st, i: sample(st, i, counts), label=f'{colony} natural ticks',
                      repeat=40, pre=lambda set16, a: set16(G, 0xf18, a[0]), post_args=ant_args)
        print(f'      (live nest ants per snapshot: {counts})')

    for label, state, caste, invader, e, *rest in SCENARIOS:
        if only and not any(o in label for o in only):
            continue
        opts = rest[0] if rest else {}
        colour = C['own'] ^ (0x80 if invader else 0)

        def pre(set16, a, state=state, caste=caste, colour=colour, e=e, opts=opts):
            set8 = set16.byte
            ant = a[0]
            for off, val in opts.get('g', {}).items():
                set16(G, C['health'] if off == 'health' else off, val)
            for off, val in opts.get('t', {}).items():
                set8(T, n['entr'] + 32 if off == 'entr' else off, val)
            set16(G, 0xf18, ant)
            if 'pos' in opts:
                oc, od = rd(SIM, X + ant), rd(SIM, Y + ant)
                set8(SIM, CELLS + oc * 64 + od, 0)
                nc, nd = opts['pos'](ant)
                set8(SIM, X + ant, nc)
                set8(SIM, Y + ant, nd)
            set8(SIM, STATE + ant, state)
            t = rd(SIM, TYPE + ant)
            if caste is not None:
                t = (t & 0x07) | (caste << 3)
            t = (t & 0x7f) | colour
            set8(SIM, TYPE + ant, t)
            col, depth = rd(SIM, X + ant), rd(SIM, Y + ant)
            set8(SIM, CELLS + col * 64 + depth, t)
            if e is not None:
                set8(SIM, E + ant, e | (colour if state == 10 else 0))
            if 'heading' in opts:
                t = (t & 0xf8) | opts['heading']
                set8(SIM, TYPE + ant, t)
                set8(SIM, CELLS + col * 64 + depth, t)
            if opts.get('block'):
                ea = rd(T, n['entr'] + col)
                for d in range(8):
                    na, nb = ea + sdx(d), col + sdx(8 + d)
                    if 0 <= na < 128 and 0 <= nb < 64:
                        set8(SIM, 0x180 + na * 64 + nb, 0x50)
            if 'cell' in opts:
                set8(SIM, CELLS + col * 64 + depth, opts['cell'] | C['own'])
            if 'dirt' in opts:
                set8(SIM, DIRT + col * 64 + depth, opts['dirt'])
            for where, at, ast, enemy in opts.get('add', ()):
                # plant another nest ant: `where` = 'here' or 'behind' (the cell behind the tested ant)
                tt = rd(SIM, TYPE + ant)
                if where == 'here':
                    c, r = col, depth
                elif where == 'front':
                    c, r = col + sdx(tt & 7), depth + sdx(8 + (tt & 7))
                else:
                    back = (tt ^ 0xfc) & 7
                    c, r = col + sdx(back), depth + sdx(8 + back)
                if not (0 <= c < 64 and 1 <= r < 64):
                    continue
                k = rd(G, n['count']) | (rd(G, n['count'] + 1) << 8)
                if k >= 500:
                    continue
                nt = (at(tt) if callable(at) else at) | (C['own'] ^ (0x80 if enemy else 0))
                set8(SIM, X + k, c)
                set8(SIM, Y + k, r)
                set8(SIM, STATE + k, ast)
                set8(SIM, TYPE + k, nt)
                set8(SIM, E + k, 0)
                set8(SIM, CELLS + c * 64 + r, nt)
                set16(G, n['count'], k + 1)
            if 'ring_dirt' in opts:
                for d in range(8):
                    c, r = col + sdx(d), depth + sdx(8 + d)
                    if 0 <= c < 64 and 1 <= r < 64:
                        set8(SIM, DIRT + c * 64 + r, opts['ring_dirt'])

        ok &= v.check(C['tick'], port, sample, label=f'{colony} forced {label}', repeat=40, pre=pre,
                      post_args=ant_args)

    if not only:
        ok &= v.check(C['loop'], with_player(C['loop_fn']), label=f'{colony} nest loop', repeat=3)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
```
{% endraw %}
