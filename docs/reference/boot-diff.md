---
layout: default
title: "boot_diff"
permalink: /reference/boot-diff/
---

# boot_diff

*`boot_diff.py` — What the original's start-up changes in the simulation's memory before the first new game.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `boot_diff.py`]({{ site.baseurl }}/assets/reference/ref/boot_diff.py)

What the original's start-up changes in the simulation's memory before the first new game.

python boot_diff.py [out.bin]

Boots SIMANT.EXE in the emulator (as verify.Verifier does), then compares State memory (0x3d570..0x62000)
with the static image tools/re/build/flat.bin and prints the changed ranges with their names. With an
output path it also writes the booted State bytes (game memory: keep it out of the repository).

## At a glance

- **51** lines
- **1 top-level functions**, including `main`

## Source

{% raw %}
```python
"""What the original's start-up changes in the simulation's memory before the first new game.

python boot_diff.py [out.bin]

Boots SIMANT.EXE in the emulator (as verify.Verifier does), then compares State memory (0x3d570..0x62000)
with the static image tools/re/build/flat.bin and prints the changed ranges with their names. With an
output path it also writes the booted State bytes (game memory: keep it out of the repository).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 're'))

import emu                                            # noqa: E402
from verify import describe                           # noqa: E402
from simant_ref.state import LO, HI                   # noqa: E402

FLAT = os.path.join(HERE, '..', 're', 'build', 'flat.bin')


def main():
    e = emu.SimEmu(base=0x100)
    e.boot(max_insns=1_000_000_000)
    b = e.base * 16
    booted = bytes(e.uc.mem_read(LO + b, HI - LO))
    flat = open(FLAT, 'rb').read()[LO:HI]
    ranges, i = [], 0
    while i < HI - LO:
        if booted[i] != flat[i]:
            j = i
            while j < HI - LO and (booted[j] != flat[j] or (j + 1 < HI - LO and booted[j + 1] != flat[j + 1])
                                   or (j + 2 < HI - LO and booted[j + 2] != flat[j + 2])):
                j += 1
            ranges.append((i, j))
            i = j
        i += 1
    total = sum(j - i for i, j in ranges)
    print(f'{len(ranges)} changed ranges, {total} bytes')
    for i, j in ranges:
        n = j - i
        show = booted[i:i + min(n, 12)].hex()
        print(f'  {describe(LO + i):24s} +{n:5d}  {show}{"..." if n > 12 else ""}')
    if len(sys.argv) > 1:
        open(sys.argv[1], 'wb').write(booted)
        print('wrote', sys.argv[1])


if __name__ == '__main__':
    main()
```
{% endraw %}
