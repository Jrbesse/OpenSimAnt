---
layout: default
title: "trace_crash"
permalink: /reference/trace-crash/
---

# trace_crash

*`trace_crash.py` — Run a Quick Game in the emulator and, when emulation crashes, print the functions that led there.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `trace_crash.py`]({{ site.baseurl }}/assets/reference/re/trace_crash.py)

Run a Quick Game in the emulator and, when emulation crashes, print the functions that led there.

python trace_crash.py [max_ticks]

## At a glance

- **56** lines
- **2 top-level functions**, including `func_of`, `main`

## Source

{% raw %}
```python
"""Run a Quick Game in the emulator and, when emulation crashes, print the functions that led there.

python trace_crash.py [max_ticks]
"""
import bisect
import collections
import json
import sys

import adis
import emu
from emu import G, DGROUP
from unicorn import UC_HOOK_BLOCK

F = json.load(open('symbols.json'))['funcs']


def func_of(lin):
    i = bisect.bisect_right(adis.starts, lin)
    f = adis.starts[i - 1] if i else 0
    return f'{f:05x}' + (f' {F[f"{f:05x}"]}' if f'{f:05x}' in F else '')


def main():
    max_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    e = emu.SimEmu(base=0x100)
    e.boot(max_insns=1_000_000_000)
    e.stub_drawing()
    e.set16(G, 0xeac, 1)
    e.set16(DGROUP, 0x8ba2, 0x1234)
    e.call_lin(0x6b36b)
    blocks = []

    def hb(uc, a, s, u):
        if len(blocks) < 6000:
            blocks.append(a - e.base * 16)
    e.uc.hook_add(UC_HOOK_BLOCK, hb)
    for i in range(1, max_ticks + 1):
        blocks.clear()
        try:
            e.call_lin(0x0894e)
        except RuntimeError as ex:
            print('tick', i, ex)
            print('first blocks', ' '.join('%x' % b for b in list(blocks)[:12]), '... total', len(blocks))
            seq = []
            for b in blocks:
                f = func_of(b)
                if not seq or seq[-1] != f:
                    seq.append(f)
            print('\n'.join(seq[-70:]))
            return
    print('no crash in', max_ticks, 'ticks')


if __name__ == '__main__':
    main()
```
{% endraw %}
