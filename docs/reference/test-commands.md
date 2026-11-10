---
layout: default
title: "test_commands"
permalink: /reference/test-commands/
---

# test_commands

*`test_commands.py` — Verify the yellow ant's menu commands (f_76cb9) against the original.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `test_commands.py`]({{ site.baseurl }}/assets/reference/ref/test_commands.py)

Verify the yellow ant's menu commands (f_76cb9) against the original.

python test_commands.py [name-substring ...]

## At a glance

- **209** lines
- **13 top-level functions**, including `setter`, `port`, `port_click`, `_surface_ant`, `port_exchange`, `port_swap`, `ex_pre`, `ants_of` …
- **Original routines referenced:** `f_00ea1`, `f_0125f`, `f_76cb9`, `f_76eb5`

## Source

{% raw %}
```python
"""Verify the yellow ant's menu commands (f_76cb9) against the original.

python test_commands.py [name-substring ...]
"""
import sys

from verify import Verifier
from simant_ref import commands, player
from simant_ref.state import G, T, SIM
from simant_ref.movement import s16
import test_sim

# UI: voice (f_00ea1), help (f_76eb5), pause (thunk 0x2f816), the animation timer (f_0125f)
STUBS = test_sim.STUBS + (0x00ea1, 0x76eb5, 0x2f816, 0x0125f)


def setter(g=()):
    def pre(set16, args):
        for off, val in g:
            set16(G, off, val)
    return pre


def port(st, cmd):
    st.player = test_sim.Player()
    commands.command(st, cmd)


CASES = [(f'command {c:#x}', [c], setter()) for c in (1, 2, 3, 4, 5, 7, 8, 9, 0xb, 0xc)] + [
    ('recruit all, then release half', [3, 4], setter()),
    ('recruit 5 twice, release all', [1, 1, 5], setter()),
    ('exchange mode on and off', [6, 6], setter()),
    ('chase mode on and off', [0xa, 0xa], setter()),
    ('exchange then chase mode', [6, 0xa], setter()),
    ('hunt as the spider', [0xb, 0xb, 0xc, 0xc], setter(g=((0xa06, 1),))),
    ('the spider hunting', [0xb, 0xc], setter(g=((0xa06, 1), (0x6ac, 7)))),
    ('no player (G:0A06 = 2)', [1, 0xb], setter(g=((0xa06, 2),))),
    ('dig hole on the surface', [8, 8], setter(g=((0x48c, 1),))),
    ('dig hole in the nest', [8], setter(g=((0x48c, 2),))),
    ('start brood on the surface', [9], setter(g=((0x48c, 1),))),
    ('start brood in the nest, shallow', [9], setter(g=((0x48c, 2), (0x48a, 2)))),
    ('alarm toggled', [7, 7], setter()),
]


def port_click(st, a, b, k):
    st.player = test_sim.Player()
    commands.spider_click(st, a, b, k)


def _surface_ant(k):
    def at(st, i):
        n = st.u16(G, 0xd6a)
        if not n:
            return None
        j = (i * 11) % n
        return st.u8(0x3e1d, 0xa180 + j), st.u8(0x3e1d, 0xa569 + j), k
    return at


CLICKS = [
    ('spider walks', lambda st, i: ((i * 17) % 128, (i * 7) % 64, 0), setter(g=((0xa06, 1),))),
    ('spider clicks with k = 1', lambda st, i: ((i * 17) % 128, (i * 7) % 64, 1), setter(g=((0xa06, 1),))),
    ('spider picks surface ants', _surface_ant(1), setter(g=((0xa06, 1),))),
    ('chase mode on ants', _surface_ant(0), setter(g=((0xa06, 1), (0x105e, 0xb)))),
    ('chase mode on empty cells', lambda st, i: (0, (i * 5) % 64, 0), setter(g=((0xa06, 1), (0x105e, 0xb)))),
]


V = None


def port_exchange(st, view, a, b):
    st.player = test_sim.Player()
    commands.exchange_click(st, view, a, b)


def port_swap(st, view, a, b):
    st.player = test_sim.Player()
    return commands.exchange(st, view, a, b)


def ex_pre(g=(), tt=(), kbd=0):
    """pre hook for the Exchange clicks: the Exchange cursor mode, globals g, T globals tt, BIOS flags kbd."""
    def pre(set16, args):
        set16(G, 0x105e, 0xa)
        for off, val in g:
            set16(G, off, val)
        for off, val in tt:
            set16(T, off, val)
        V.e.uc.mem_write(0x417, bytes([kbd]))
    return pre


def ants_of(view, want=None, k=7):
    """args: the i-th pick (stride k) of the view's ants, optionally only types with want(type)."""
    def at(st, i):
        f = player.ANTS[view]
        n = s16(st.u16(G, f['count']))
        idx = [j for j in range(n) if st.u8(SIM, f['type'] + j) and (want is None or want(st.u8(SIM, f['type'] + j)))]
        if not idx:
            return None
        j = idx[(i * k) % len(idx)]
        return view, st.u8(SIM, f['x'] + j), st.u8(SIM, f['y'] + j)
    return at


def near_spider(st, i):
    """args: cells around the spider (G:0F12 / G:0F34 in pixels), out to a little past its reach."""
    sa, sb = s16(st.u16(G, 0xf12)) >> 4, s16(st.u16(G, 0xf34)) >> 4
    da, db = ((0, 0), (1, 0), (0, -1), (-1, 1), (1, 1), (2, 0), (0, 2), (-2, -1))[i % 8]
    return 1, max(0, min(0x7f, sa + da)), max(0, min(0x3f, sb + db))


def as_caste(c, pre):
    """pre hook: the clicked ant (and its cell) first becomes caste c, keeping its heading."""
    def p(set16, args):
        pre(set16, args)
        view, a, b = args
        f = player.ANTS[view]
        cells = player.OCC if view == 1 else player.NESTS[view]['cells']
        o = V.e.read(SIM, cells + a * 64 + b, 1)[0]
        n = s16(int.from_bytes(V.e.read(G, f['count'], 2), 'little'))
        for j in range(n - 1, -1, -1):
            if (V.e.read(SIM, f['x'] + j, 1)[0] == a and V.e.read(SIM, f['y'] + j, 1)[0] == b
                    and V.e.read(SIM, f['type'] + j, 1)[0] == o):
                t = (o & 0x87) | (c << 3)
                set16.byte(SIM, f['type'] + j, t)
                set16.byte(SIM, cells + a * 64 + b, t)
                return
    return p


def the_yellow(st, i):
    return st.u16(G, 0x48c), s16(st.u16(G, 0x47c)), s16(st.u16(G, 0x48a))


def caste(*cs):
    return lambda t: (t & 0x78) >> 3 in cs


CHEAT = 0x0b                                                            # Shift + Alt
EXCHANGES = [
    ('surface ants', ants_of(1), ex_pre()),
    ('black nest ants', ants_of(2), ex_pre()),
    ('red nest ants', ants_of(3), ex_pre()),
    ('red nest ants, cheat', ants_of(3), ex_pre(kbd=CHEAT)),
    ('red surface ants, cheat', ants_of(1, lambda t: t & 0x80), ex_pre(kbd=CHEAT)),
    ('black nest brood', ants_of(2, caste(0)), ex_pre()),
    ('black nest brood, cheat', ants_of(2, caste(0)), ex_pre(kbd=CHEAT, tt=((0x798, 1),))),
    ('odd castes, cheat', ants_of(2, caste(1, 5, 9, 10, 11)), ex_pre(kbd=CHEAT, tt=((0x798, 1),))),
    ('queens', ants_of(2, caste(12, 13), k=1), ex_pre()),
    ('red queens, cheat', ants_of(3, caste(12, 13), k=1), ex_pre(kbd=CHEAT)),
    ('empty cells', lambda st, i: (1 + i % 3, (i * 13) % 64, (i * 29) % 64), ex_pre()),
    ('the yellow ant itself', the_yellow, ex_pre()),
    ('cells near the spider', near_spider, ex_pre()),
    ('as the spider: surface ants', ants_of(1), ex_pre(g=((0xa06, 1),))),
    ('as the spider: nest ants', ants_of(2), ex_pre(g=((0xa06, 1),))),
    ('as the spider: red ants, cheat', ants_of(1, lambda t: t & 0x80), ex_pre(g=((0xa06, 1),), kbd=CHEAT)),
    ('as the spider: brood, cheat', ants_of(2, caste(0)), ex_pre(g=((0xa06, 1),), kbd=CHEAT, tt=((0x798, 1),))),
    ('as the spider: queens', ants_of(2, caste(12, 13), k=1), ex_pre(g=((0xa06, 1),))),
    ('as the spider: near the spider', near_spider, ex_pre(g=((0xa06, 1),))),
    ('as a queen: surface ants', ants_of(1), ex_pre(g=((0x4c2, 0x60),))),
    ('as a queen: nest ants', ants_of(2), ex_pre(g=((0x4c2, 0x60),))),
    ('as a queen: near the spider', near_spider, ex_pre(g=((0x4c2, 0x60),))),
    ('as caste 1: nest ants', ants_of(2), ex_pre(g=((0x4c2, 0x08),), tt=((0xc22, 0x33),))),
    ('as caste 5: nest ants', ants_of(2), ex_pre(g=((0x4c2, 0x28),))),
    ('as caste 9: near the spider', near_spider, ex_pre(g=((0x4c2, 0x48),))),
    ('clicked caste 5', ants_of(2, caste(2, 3, 4, 6)), as_caste(5, ex_pre())),
    ('clicked caste 9, as the spider', ants_of(1, caste(2, 3, 4, 6)), as_caste(9, ex_pre(g=((0xa06, 1),)))),
    ('as the spider: red ants', ants_of(1, lambda t: t & 0x80), ex_pre(g=((0xa06, 1),))),
    ('lists full: near the spider', near_spider, ex_pre(g=((0xd6a, 1000), (0xda8, 500), (0xeaa, 500)))),
    ('lists full: nest ants', ants_of(2), ex_pre(g=((0xd6a, 1000), (0xda8, 500), (0xeaa, 500)))),
    ('lists nearly full, as a queen: near the spider', near_spider,
     ex_pre(g=((0x4c2, 0x60), (0xd6a, 999), (0xda8, 499), (0xeaa, 499)))),
    ('lists nearly full, as a queen: nest ants', ants_of(2),
     ex_pre(g=((0x4c2, 0x60), (0xd6a, 999), (0xda8, 499), (0xeaa, 499)))),
]


def main():
    global V
    filters = sys.argv[1:]
    v = V = Verifier()
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    ok = True
    for label, where, pre in EXCHANGES:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x11c18, port_swap, args_fn=where, repeat=4, label=f'swap: {label}', pre=pre,
                      ignore=test_sim.SCREEN)
        ok &= v.check(0x11b81, port_exchange, args_fn=where, repeat=8, label=f'exchange: {label}', pre=pre,
                      ignore=test_sim.SCREEN)
    for label, where, pre in CLICKS:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x756a6, port_click, args_fn=where, repeat=10, label=label, pre=pre, ignore=test_sim.SCREEN)
    for label, cmds, pre in CASES:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x76cb9, port, args_fn=lambda st, i, cmds=cmds: (cmds[i],), repeat=len(cmds), label=label,
                      pre=pre, pre_once=True, ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
```
{% endraw %}
