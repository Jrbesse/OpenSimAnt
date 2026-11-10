---
layout: default
title: "test_events"
permalink: /reference/test-events/
---

# test_events

*`test_events.py` — Verify the player events against the original: the yellow ant's death and the takeover of another ant*

[Reference index]({{ site.baseurl }}/reference/) · [Download `test_events.py`]({{ site.baseurl }}/assets/reference/ref/test_events.py)

Verify the player events against the original: the yellow ant's death and the takeover of another ant
(f_75d01, via f_2f7d0), the queen scene (f_758e0) and the death animations (f_7c149 modes, f_7c3b1).

python test_events.py [name-substring ...]

The original's dialogs wait for a click (f_01572 is stubbed to report one) and its animations wait on the
clock (which runs during these routines); the UI setup and the screen-only memory are test_sim's.

## At a glance

- **109** lines
- **5 top-level functions**, including `port`, `event_port`, `setter`, `no_black`, `main`
- **Original routines referenced:** `f_01572`, `f_2f7d0`, `f_758e0`, `f_75d01`, `f_7c149`, `f_7c3b1`

## Source

{% raw %}
```python
"""Verify the player events against the original: the yellow ant's death and the takeover of another ant
(f_75d01, via f_2f7d0), the queen scene (f_758e0) and the death animations (f_7c149 modes, f_7c3b1).

python test_events.py [name-substring ...]

The original's dialogs wait for a click (f_01572 is stubbed to report one) and its animations wait on the
clock (which runs during these routines); the UI setup and the screen-only memory are test_sim's.
"""
import sys

from verify import Verifier
from simant_ref import player
from simant_ref.state import G, T, DS, SIM
import test_sim

SCREEN = test_sim.SCREEN


def port(fn, nargs):
    def run(st, *args):
        st.player = test_sim.Player()
        return fn(st, *args[:nargs])
    return run


def event_port(st, n):
    st.player = test_sim.Player()
    player.player_event(st, n)


def setter(g=(), t=(), ds=(), sim8=()):
    def pre(set16, args):
        for seg, items in ((G, g), (T, t), (DS, ds)):
            for off, val in items:
                set16(seg, off, val)
        for off, val in sim8:
            set16.byte(SIM, off, val)
    return pre


def no_black(extra=()):
    """the black nest is empty (count 0, slot 0 cleared)"""
    return ((0xda8, 0),) + tuple(extra)


EMPTY_BLACK = ((0xbaec, 0),)
EMPTY_ALL = ((0xbaec, 0), (0xad3b, 0), (0xc4b5, 0))
ON_SURFACE = ((0x48c, 1), (0x47c, 70), (0x48a, 25))
NO_MSG = ((0x7ae, 0),)
LONG = ((0x5702, 0),)

CHECKS = [(f'event {n}', n, setter()) for n in range(11)]
CHECKS += [(f'event {n} no messages', n, setter(t=NO_MSG)) for n in (0, 1, 2, 5, 8, 10)]
CHECKS += [(f'event {n} long animation', n, setter(ds=LONG)) for n in (1, 2, 7, 10)]
CHECKS += [(f'event {n} long, sound off', n, setter(ds=LONG, t=((0x7aa, 0),))) for n in (1, 7)]
CHECKS += [(f'event {n} on the surface', n, setter(g=ON_SURFACE)) for n in (1, 2, 7, 9, 10)]
CHECKS += [
    ('event 3 carrying food', 3, setter(g=((0x4c2, 0x18),))),
    ('event 3 carrying food on the surface', 3, setter(g=ON_SURFACE + ((0x4c2, 0x18),))),
    ('event 5 alarm trail on', 5, setter(g=((0x104e, 1),))),
    ('event 4 the player is the spider', 4, setter(g=((0xa06, 2),))),
    ('event 6 the stray queen slot', 6, setter(sim8=())),
    ('event 3 to a surface ant', 3, setter(g=no_black(), sim8=EMPTY_BLACK)),
    ('event 3 to a red ant', 3, setter(g=no_black(((0xd6a, 0),)), sim8=EMPTY_BLACK + ((0xad3b, 0),))),
    ('event 3 none left, Quick Game', 3, setter(g=no_black(((0xd6a, 0), (0xeaa, 0))), sim8=EMPTY_ALL)),
    ('event 3 none left, Full Game over', 3,
     setter(g=no_black(((0xd6a, 0), (0xeaa, 0), (0xeac, 2), (0x3e2, 1))), sim8=EMPTY_ALL)),
    ('event 3 none left, Full Game yard map', 3,
     setter(g=no_black(((0xd6a, 0), (0xeaa, 0), (0xeac, 2), (0x3e2, 5))), sim8=EMPTY_ALL)),
]


# (label, view, a, b, t, found, pre g)
SCENES = [
    ('queen scene: reborn', (2, 30, 20, 0x10, 0), ()),
    ('queen scene: reborn as 0x60', (2, 30, 20, 0x60, 0), ((0x4c2, 0x60),)),
    ('queen scene: founds a black nest', (2, 30, 30, 0x60, 1),
     ((0x4c2, 0x60), (0x48c, 2), (0x47c, 30), (0x48a, 30), (0x496, 2))),
    ('queen scene: founds a red nest', (3, 20, 25, 0x60, 1),
     ((0x4c2, 0x60), (0x48c, 3), (0x47c, 20), (0x48a, 25), (0x496, 6), (0x4e2, 1))),
]


def main():
    filters = sys.argv[1:]
    v = Verifier()
    test_sim.prepare(v)
    ok = True
    for label, n, pre in CHECKS:
        if filters and not any(f in label for f in filters):
            continue
        if label == 'event 6 the stray queen slot':
            def pre(set16, args):
                n = v.e.w16(G, 0xda8)
                for off, val in ((0xbaec, 3), (0xb50d, 30), (0xb702, 20)):
                    set16.byte(SIM, off + n, val)
        ok &= v.check(0x75d01, event_port, args_fn=lambda st, i, n=n: (n,), label=label, pre=pre,
                      ignore=SCREEN)
    for label, args, g in SCENES:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x758e0, port(player.queen_scene, 5), args_fn=lambda st, i, a=args: a, label=label,
                      pre=setter(g=g), ignore=SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
```
{% endraw %}
