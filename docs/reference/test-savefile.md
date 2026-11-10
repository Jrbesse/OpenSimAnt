---
layout: default
title: "test_savefile"
permalink: /reference/test-savefile/
---

# test_savefile

*`test_savefile.py` — Verify loading saved games against the original (python test_savefile.py).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `test_savefile.py`]({{ site.baseurl }}/assets/reference/ref/test_savefile.py)

Verify loading saved games against the original (python test_savefile.py).

A game saved from one snapshot is loaded onto another: the original runs its load fix-ups (f_6cf1a, then
the blocks are written as its read() would, then f_6cf5b; the file dialog and DOS I/O are skipped) and
the port runs savefile.load. Then both play on for 300 SimSteps.

## At a glance

- **84** lines
- **3 top-level functions**, including `original_load`, `compare`, `main`
- **Original routines referenced:** `f_6cf1a`, `f_6cf5b`

## Source

{% raw %}
```python
"""Verify loading saved games against the original (python test_savefile.py).

A game saved from one snapshot is loaded onto another: the original runs its load fix-ups (f_6cf1a, then
the blocks are written as its read() would, then f_6cf5b; the file dialog and DOS I/O are skipped) and
the port runs savefile.load. Then both play on for 300 SimSteps.
"""
import sys

from verify import Verifier
from simant_ref import savefile
from simant_ref import sim
from simant_ref.state import T, G, LO, HI
import test_sim
import test_game

IGNORE = test_game.START_SCREEN


def original_load(v, data):
    v.e.set16(T, 0x2c2, 0)
    v.e.call_lin(0x6cf1a)
    pos = 0
    for seg, off, n in savefile.blocks():
        v.e.write(seg, off, data[pos:pos + n])
        pos += n
    v.e.call_lin(0x6cf5b)


def compare(v, st, label):
    b = v.e.base * 16
    stack_top = 0x55b3 * 16 + v.e.call_sp + 0x10
    ignore = IGNORE + ((stack_top - 0x800, stack_top),)
    orig = bytes(v.e.uc.mem_read(LO + b, HI - LO))
    diffs = [i for i in range(HI - LO) if orig[i] != st.mem[i] and not any(lo <= LO + i < hi for lo, hi in ignore)]
    if diffs:
        from verify import describe
        print(f'  [{label}] {len(diffs)} bytes differ: ' + ', '.join(
            f'{describe(LO + i)} {orig[i]:#04x}/{st.mem[i]:#04x}' for i in diffs[:6]))
    return not diffs


def main():
    v = Verifier()
    test_sim.prepare(v)
    ok = True
    pairs = [(5, 0), (0, 5), (2, 4), (3, 1)]
    for src, dst in pairs:
        v.load(v.snaps[src][1])
        data = savefile.save(v.state_from_emu())
        assert len(data) == savefile.file_size() == 48386
        for extra, label in ((None, 'Quick Game'), ((G, 0xf24, 1), 'in the house'), ((G, 0xa06, 2), 'as the spider')):
            v.load(v.snaps[dst][1])
            st = v.state_from_emu()
            st.player = test_sim.Player()
            if extra:
                seg, off, val = extra
                patched = bytearray(data)
                pos = 0
                for s, o, n in savefile.blocks():
                    if (s, o) == (seg, off):
                        patched[pos:pos + 2] = val.to_bytes(2, 'little')
                    pos += n
                d = bytes(patched)
            else:
                d = data
            original_load(v, d)
            savefile.load(st, d)
            name = f'load snapshot {v.snaps[src][0]} over {v.snaps[dst][0]}, {label}'
            good = compare(v, st, name)
            if good:
                for t in range(300):
                    v.e.call_lin(0x0894e)
                    sim.sim_step(st)
                    if v.e.w16(G, 0x376):
                        break
                good = compare(v, st, name + ', then SimStep x 300')
            print(f'{name}: {"OK" if good else "MISMATCH"}')
            ok &= good
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
```
{% endraw %}
