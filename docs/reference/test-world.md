---
layout: default
title: "test_world"
permalink: /reference/test-world/
---

# test_world

*`test_world.py` — Verify the SimStep world updates against the original (python test_world.py [name-substring ...]).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `test_world.py`]({{ site.baseurl }}/assets/reference/ref/test_world.py)

Verify the SimStep world updates against the original (python test_world.py [name-substring ...]).

## At a glance

- **240** lines
- **6 top-level functions**, including `with_player`, `setter`, `lions`, `swarm_cat`, `spider_at`, `main`
- **Original routines referenced:** `f_0c73d`, `f_0db10`

## Source

{% raw %}
```python
"""Verify the SimStep world updates against the original (python test_world.py [name-substring ...])."""
import sys

from verify import Verifier
from simant_ref import world
from simant_ref import surface as sf
from simant_ref.state import G, DS

DSL = DS * 16
# screen-only state the port leaves to effect hooks: status-line message slots, the dirty-cell map
SCREEN = ((DSL + 0x19c6, DSL + 0x19d0), (DSL + 0x299a, DSL + 0x29a4), (DSL + 0x15c4, DSL + 0x15c4 + 0x1000))


def with_player(fn):
    def run(st, *args):
        st.player = sf.NoPlayer()
        return fn(st, *args)
    return run


def setter(g=(), t=()):
    from simant_ref.state import T

    def pre(set16, a):
        for off, val in g:
            set16(G, off, val)
        for off, val in t:
            set16(T, off, val)
    return pre


def lions(states, near_ants=True, cover=None, swarm=False):
    """pre hook: plant ant lions (state, frame, timer) next to surface ants (or on open ground)."""
    from simant_ref.state import SIM, T

    def pre(set16, a):
        set8 = set16.byte
        st = VER.state_from_emu()
        n = st.u16(G, 0xd6a)
        ants = [i for i in range(n) if st.u8(SIM, 0xad3b + i)]
        k = 0
        for j, (state, frame, timer) in enumerate(states):
            if near_ants and ants:
                ant = ants[(j * 37) % len(ants)]
                la, lb = st.u8(SIM, 0xa180 + ant) + 1, st.u8(SIM, 0xa569 + ant)
            else:
                la, lb = 10 + j * 9, 20 + j * 3
            la, lb = min(max(la, 1), 126), min(max(lb, 1), 62)
            set8(G, 0xa92 + k, la)
            set8(G, 0xaa8 + k, lb)
            set8(G, 0xaba + k, state)
            set8(G, 0xade + k, frame)
            set8(G, 0xacc + k, timer)
            if cover is not None:
                set8(SIM, 0x180 + la * 64 + lb, cover)
            if swarm:
                for d in range(8):
                    dx, dy = VER.e.read(T, d, 1)[0], VER.e.read(T, 8 + d, 1)[0]
                    dx, dy = dx - 256 if dx > 127 else dx, dy - 256 if dy > 127 else dy
                    set8(SIM, 0x6180 + (la + dx) * 64 + lb + dy, 0x10)
            k += 1
        set16(T, 0xc4a, k)
    return pre


def swarm_cat(n_occ):
    """pre hook: a caterpillar heading east at (40, 30), with n_occ of the 3x3 around its head occupied
    (always including the cell ahead)."""
    from simant_ref.state import SIM, T

    def pre(set16, a):
        set8 = set16.byte
        set16(T, 0xc4c, 1)
        set16(G, 0xc3c, 1)
        set16(T, 0xc4e, 40)
        set16(T, 0xc50, 30)
        set16(G, 0xc36, 3)
        cells = [(41, 30)] + [(x, y) for x in (39, 40, 41) for y in (29, 30, 31) if (x, y) != (41, 30)]
        for x, y in cells[:n_occ]:
            set8(SIM, 0x6180 + x * 64 + y, 0x10)
    return pre


def spider_at(state=None, mode=None, near=True, off=(3, 0), g=(), t=(), swarm=False, prey=None,
              crowd=0, tile=None, yellow=None, cursor=None, ring=False, plant=()):
    """pre hook: an active spider near a surface ant (in 1/16 tiles), optional state / mode / globals."""
    from simant_ref.state import SIM, T as TT

    def pre(set16, a):
        set8 = set16.byte
        st = VER.state_from_emu()
        n = st.u16(G, 0xd6a)
        ants = [i for i in range(n) if st.u8(SIM, 0xad3b + i)]
        if near and ants:
            ant = ants[len(ants) // 2]
            sa, sb = st.u8(SIM, 0xa180 + ant) + off[0], st.u8(SIM, 0xa569 + ant) + off[1]
        else:
            ant = None
            sa, sb = 60, 30
        sa, sb = min(max(sa, 1), 126), min(max(sb, 1), 62)
        set16(G, 0xf0c, 1)
        set16(G, 0xf12, sa * 16 + 8)
        set16(G, 0xf34, sb * 16 + 8)
        if state is not None:
            set16(G, 0xfb8, state)
        if mode is not None:
            set16(G, 0x6ac, mode)
        if prey == 'ant' and ant is not None:
            set16(G, 0xffc, ant)
            set16(G, 0x10ae, st.u8(SIM, 0xad3b + ant))
        elif prey is not None:
            set16(G, 0xffc, prey)
        for off_, val in g:
            set16(G, off_, val)
        for off_, val in t:
            set16(TT, off_, val)
        if swarm:
            for x in range(sa - 1, sa + 2):
                for y in range(sb - 1, sb + 2):
                    set8(SIM, 0x6180 + x * 64 + y, 0x10)
        for k, (x, y) in enumerate((x, y) for x in range(sa - 1, sa + 2) for y in range(sb - 1, sb + 2)):
            if k < crowd:
                set8(SIM, 0x6180 + x * 64 + y, 0x10)
        if ring:                                # the far row / column of the 4x4 block f_0db10 counts
            for x in range(sa - 1, sa + 3):
                for y in range(sb - 1, sb + 3):
                    if x == sa + 2 or y == sb + 2:
                        set8(SIM, 0x6180 + x * 64 + y, 0x10)
        if tile is not None:
            set8(SIM, 0x180 + sa * 64 + sb, tile)
        for da, db, v in plant:                 # extra surface tiles around the spider (clipped to the map)
            if 0 <= sa + da <= 127 and 0 <= sb + db <= 63:
                set8(SIM, 0x180 + (sa + da) * 64 + sb + db, v)
        if yellow is not None:
            set16(G, 0x47c, sa + yellow[0])
            set16(G, 0x48a, sb + yellow[1])
        if cursor is not None:
            set16(G, 0xf42, sa + cursor[0])
            set16(G, 0xf7e, sb + cursor[1])
            set16(G, 0x47c, sa)
            set16(G, 0x48a, sb)
    return pre


CHECKS = [
    ('history', 0x798c8, world.history, 3, None),
    ('advisor', 0x0e2ea, world.advisor, 2, None),
    ('advisor shown', 0x0e2ea, world.advisor, 1, setter(t=[(0x7b0, 1)])),
    ('advisor hungry', 0x0e2ea, world.advisor, 1, setter(g=[(0xffe, 101)], t=[(0x7b0, 1)])),
    ('advisor crowded', 0x0e2ea, world.advisor, 1, setter(g=[(0x224, 1)], t=[(0x7b0, 1)])),
    ('advisor no nest', 0x0e2ea, world.advisor, 1, setter(g=[(0x224, 0)], t=[(0x7b0, 1)])),
    ('advisor yellow dying', 0x0e2ea, world.advisor, 1, setter(g=[(0xf78, 5)], t=[(0x7b0, 1)])),
    ('census+advisor', 0x0c20f, world.census_and_advise, 2, None),
] + [(f'slow phase {p}', 0x08a78, world.slow_phase, 1, setter(g=[(0xf08, p * 0x20)])) for p in range(4)] + [
    ('weather dry', 0x0c22c, world.weather, 20, None),
    ('weather rain', 0x0c22c, world.weather, 30, setter(g=[(0x352, 1)])),
    ('weather rain flooded', 0x0c22c, world.weather, 30, setter(g=[(0x352, 1), (0x242, 40)])),
    ('weather after rain', 0x0c22c, world.weather, 30, setter(g=[(0x242, 30)], t=[(0xc1e, 1)])),
    ('weather in house', 0x0c22c, world.weather, 5, setter(g=[(0x352, 1), (0xf24, 1)])),
    ('new ant lion', 0x0b016, world.new_lion, 3, None),
    ('ant lions none', 0x0b163, world.ant_lions, 50, None),
    ('ant lions lurking', 0x0b163, world.ant_lions, 30, lions([(0, 0, 0)] * 6)),
    ('ant lions lurking open', 0x0b163, world.ant_lions, 30, lions([(0, 0, 0)] * 4, near_ants=False)),
    ('ant lions covered', 0x0b163, world.ant_lions, 1500, lions([(0, 0, 0)] * 5, near_ants=False, cover=0x49)),
    ('ant lions eating', 0x0b163, world.ant_lions, 60, lions([(1, 0, 5), (1, 4, 0), (1, 4, 9), (1, 2, 3)])),
    ('ant lions closing', 0x0b163, world.ant_lions, 20, lions([(2, 4, 0), (2, 0, 0), (2, 1, 0)])),
    ('ant lions swarmed', 0x0b163, world.ant_lions, 3, lions([(1, 2, 5), (0, 0, 0), (1, 1, 1)], swarm=True)),
    ('bugs', 0x0ae4c, world.bugs, 60, None),
    ('caterpillar', 0x0b6cc, world.caterpillar, 80, None),
    ('caterpillar long', 0x0b6cc, world.caterpillar, 700, None),
    ('caterpillar blocked', 0x0b6cc, world.caterpillar, 12, swarm_cat(4)),
    ('caterpillar swarmed', 0x0b6cc, world.caterpillar, 3, swarm_cat(9)),
    ('spider natural', 0x0ce63, world.spider, 300, None),
    ('spider spawn', 0x0ce63, world.spider, 2000, setter(g=[(0xf0c, 0)])),
    ('spider resting', 0x0ce63, world.spider, 200, spider_at(0)),
    ('spider walking', 0x0ce63, world.spider, 200, spider_at(1)),
    ('spider walking back', 0x0ce63, world.spider, 200, spider_at(1, t=[(0xc12, 1)])),
    ('spider hunting', 0x0ce63, world.spider, 200, spider_at(2, prey='ant')),
    ('spider hunting far', 0x0ce63, world.spider, 50, spider_at(2, prey='ant', off=(40, 0))),
    ('spider hunting lost', 0x0ce63, world.spider, 50, spider_at(2, prey='ant', g=[(0x10ae, 0xf0)])),
    ('spider eating', 0x0ce63, world.spider, 200, spider_at(3, prey='ant', off=(1, 0))),
    ('spider eating none', 0x0ce63, world.spider, 100, spider_at(3, prey=0xfffe, g=[(0x1054, 25)])),
    ('spider fleeing', 0x0ce63, world.spider, 200, spider_at(4)),
    ('spider beaten', 0x0ce63, world.spider, 600, spider_at(5, g=[(0x109a, 450)])),
    ('spider beaten end', 0x0ce63, world.spider, 30, spider_at(5, g=[(0x109a, 3)])),
    ('spider mode 7', 0x0ce63, world.spider, 300, spider_at(0, mode=7)),
    ('spider mode 8', 0x0ce63, world.spider, 300, spider_at(1, mode=8)),
    ('spider swarmed', 0x0ce63, world.spider, 40, spider_at(1, swarm=True, g=[(0x1072, 3)])),
    ('spider swarmed often', 0x0ce63, world.spider, 40, spider_at(1, swarm=True, g=[(0x1072, 3), (0x108a, 4)])),
    ('spider crowded', 0x0ce63, world.spider, 20, spider_at(1, crowd=6, g=[(0x1072, 3)])),
    ('spider swarmed 4x4', 0x0ce63, world.spider, 20, spider_at(1, crowd=2, ring=True, g=[(0x1072, 3)])),
    ('spider crowded 4x4', 0x0ce63, world.spider, 20, spider_at(1, ring=True, g=[(0x1072, 3)])),
    ('spider hunts yellow', 0x0ce63, world.spider, 2, spider_at(2, prey=0xffff, yellow=(12, 0), g=[(0x48c, 1)])),
    ('spider yellow underground', 0x0ce63, world.spider, 5, spider_at(2, prey=0xffff, g=[(0x48c, 2)])),
    ('spider yellow far', 0x0ce63, world.spider, 5, spider_at(2, prey=0xffff, yellow=(70, 0), g=[(0x48c, 1)])),
    ('spider mode 7 yellow', 0x0ce63, world.spider, 2, spider_at(0, mode=7, near=False, yellow=(20, 0),
                                                                g=[(0x48c, 1), (0xd6a, 0)])),
    ('spider eating changed', 0x0ce63, world.spider, 30, spider_at(3, prey='ant', g=[(0x10ae, 0xf0)])),
    ('spider fleeing at edge', 0x0ce63, world.spider, 200, spider_at(4, near=False, off=(0, 0), g=[(0xf12, 126 * 16)])),
    ('spider beaten end house', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1)], tile=2)),
    ('spider beaten end house 2', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1)], tile=0x10)),
    ('spider beaten end house 3', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1)], tile=0x20)),
    ('spider beaten end house 4', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1)], tile=0x50)),
    # f_0c73d: furniture tile (0x27..0x3f) under the beaten spider; the walk's direction is the room G:0F3A
    ('spider beaten furniture room 1', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1), (0xf3a, 1)], tile=0x30, plant=[(1, 0, 0x30), (2, 0, 0x2a), (3, 0, 2)])),
    ('spider beaten furniture room 2', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1), (0xf3a, 2)], tile=0x27, plant=[(0, 1, 0x3f), (0, 2, 1)])),
    ('spider beaten furniture room 0', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1), (0xf3a, 0)], tile=0x3f)),
    ('spider beaten furniture room 3', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1), (0xf3a, 3)], tile=0x38)),
    ('spider beaten furniture room 1 blocked', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1), (0xf3a, 1)], tile=0x30, plant=[(d, 0, 0x30) for d in range(1, 130)])),
    ('spider beaten furniture room 2 blocked', 0x0ce63, world.spider, 5, spider_at(5, g=[(0x109a, 1), (0xf24, 1), (0xf3a, 2)], tile=0x30, plant=[(0, d, 0x2f) for d in range(1, 70)])),
    ('spider player', 0x0ce63, world.spider, 60, spider_at(1, g=[(0xa06, 1), (0x6ac, 0)], cursor=(15, 4))),
    ('spider player charging', 0x0ce63, world.spider, 60, spider_at(1, g=[(0xa06, 1), (0x6ac, 0), (0xa8e, 1)],
                                                                  cursor=(-20, -3))),
    ('spider player arrived', 0x0ce63, world.spider, 3, spider_at(1, g=[(0xa06, 1)], cursor=(0, 0))),
    ('spider player mode 7', 0x0ce63, world.spider, 30, spider_at(1, g=[(0xa06, 1), (0x6ac, 7)], cursor=(9, 9))),
    ('spider player mode 8', 0x0ce63, world.spider, 30, spider_at(1, g=[(0xa06, 1), (0x6ac, 8)], cursor=(9, 9))),
    ('spider player hunting', 0x0ce63, world.spider, 60, spider_at(2, prey='ant', g=[(0xa06, 1)])),
    ('spider player eating', 0x0ce63, world.spider, 60, spider_at(3, prey='ant', off=(1, 0), g=[(0xa06, 1), (0x6ac, 6)])),
    ('spider player prey lost', 0x0ce63, world.spider, 5, spider_at(2, prey='ant', g=[(0xa06, 1), (0x10ae, 0xf0), (0x6ac, 6)])),
    ('spider in house', 0x0ce63, world.spider, 50, spider_at(1, g=[(0xf24, 1)])),
    ('ant lions full', 0x0b163, world.ant_lions, 20, lions([(2, 0, 0)] * 9, near_ants=False)),
]


def main():
    global VER
    only = sys.argv[1:]
    v = VER = Verifier()
    ok = True
    for label, lin, fn, repeat, pre in CHECKS:
        if only and not any(o in label for o in only):
            continue
        ok &= v.check(lin, with_player(fn), label=label, repeat=repeat, pre=pre, ignore=SCREEN,
                      pre_once='lion' in label or 'caterpillar' in label or 'spider' in label)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
```
{% endraw %}
