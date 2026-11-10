---
layout: default
title: "run_quickgame"
permalink: /reference/run-quickgame/
---

# run_quickgame

*`run_quickgame.py` — Boot the original game headless, start a Quick Game and run the real simulation for N ticks.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `run_quickgame.py`]({{ site.baseurl }}/assets/reference/re/run_quickgame.py)

Boot the original game headless, start a Quick Game and run the real simulation for N ticks.

python run_quickgame.py [ticks] [sample_every] [--dump DIR]

Prints colony statistics over time. With --dump, writes the 0x3e1d sim segment (64 KB) after every
sampled tick as DIR/sim_<tick>.bin; these are the ground truth for testing a reimplementation.

## At a glance

- **59** lines
- **2 top-level functions**, including `stats`, `main`

## Source

{% raw %}
```python
"""Boot the original game headless, start a Quick Game and run the real simulation for N ticks.

python run_quickgame.py [ticks] [sample_every] [--dump DIR]

Prints colony statistics over time. With --dump, writes the 0x3e1d sim segment (64 KB) after every
sampled tick as DIR/sim_<tick>.bin; these are the ground truth for testing a reimplementation.
"""
import os
import sys
import time

import emu
from emu import G, DGROUP

SIMSTEP = 0x0894e
NEWGAME = 0x6b36b


def stats(e):
    return dict(tick=e.w16(G, 0xf08), surf=e.w16(G, 0xd6a), bnest=e.w16(G, 0xda8), rnest=e.w16(G, 0xeaa),
                bpop=e.w16(G, 0x330), rpop=e.w16(G, 0x350), bhealth=e.w16(G, 0x10be), rhealth=e.w16(G, 0x1fe),
                bfood=e.w16(G, 0x1050), bcap=e.w16(G, 0x224), prio=e.w16(G, 0x1094))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ticks = int(args[0]) if args else 5000
    every = int(args[1]) if len(args) > 1 else 500
    dump = sys.argv[sys.argv.index('--dump') + 1] if '--dump' in sys.argv else None
    e = emu.SimEmu(base=0x100)
    e.boot(max_insns=1_000_000_000)
    e.stub_drawing()
    e.set16(G, 0xeac, 1)                      # game mode 1 = Quick Game
    e.set16(DGROUP, 0x8ba2, 0x1234)           # fixed LFSR seed for reproducible runs
    e.call_lin(NEWGAME)
    if dump:
        os.makedirs(dump, exist_ok=True)
    t0 = time.time()
    print(stats(e))
    for i in range(1, ticks + 1):
        try:
            e.call_lin(SIMSTEP)
        except RuntimeError as ex:
            if not e.w16(G, 0x376):
                raise
            print(f'(game-over UI not emulated: {ex})')
        if i % every == 0 or e.w16(G, 0x376):
            print(f'tick {i}:', stats(e))
            if dump:
                open(os.path.join(dump, f'sim_{i:06d}.bin'), 'wb').write(e.sim_bytes())
        if e.w16(G, 0x376):
            print('GAME OVER at tick', i, '- player', 'won' if e.w16(G, 0x366) else 'lost')
            break
    print(f'{i} ticks in {time.time() - t0:.1f}s')
    print('messages (tick, STR# id):', e.messages)


if __name__ == '__main__':
    main()
```
{% endraw %}
