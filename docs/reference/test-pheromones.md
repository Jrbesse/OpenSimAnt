---
layout: default
title: "test_pheromones"
permalink: /reference/test-pheromones/
---

# test_pheromones

*`test_pheromones.py` — Verify the pheromone module against the original (python test_pheromones.py).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `test_pheromones.py`]({{ site.baseurl }}/assets/reference/ref/test_pheromones.py)

Verify the pheromone module against the original (python test_pheromones.py).

## At a glance

- **40** lines
- **1 top-level functions**, including `main`

## Source

{% raw %}
```python
"""Verify the pheromone module against the original (python test_pheromones.py)."""
import sys

from verify import Verifier
from simant_ref import pheromones as ph


def main():
    v = Verifier()
    ok = True
    ok &= v.check(0x14966, ph.black_nest_markers, label='BlackNestMarkers')
    ok &= v.check(0x149e9, ph.red_nest_markers, label='RedNestMarkers')
    ok &= v.check(0x14a6c, ph.decay_black_nest, label='DecayBlackNest', repeat=3)
    ok &= v.check(0x14ab3, ph.decay_red_nest, label='DecayRedNest', repeat=3)
    ok &= v.check(0x14afa, ph.decay_black_trail, label='DecayBlackTrail', repeat=3)
    ok &= v.check(0x14b5e, ph.decay_red_trail, label='DecayRedTrail', repeat=3)
    ok &= v.check(0x14bbe, ph.diffuse_alarm, label='DiffuseAlarm', repeat=3)

    def lay_args(st, i):
        return ((i * 37) % 128, (i * 11) % 64, (i * 53) % 256)
    ok &= v.check(0x14d2c, lambda st, a, b, s: ph.lay_max(st, ph.BLACK_NEST, a, b, s), lay_args,
                  label='LayNestMarkerBlack', repeat=20)
    ok &= v.check(0x14d64, lambda st, a, b, s: ph.lay_max(st, ph.RED_NEST, a, b, s), lay_args,
                  label='LayNestMarkerRed', repeat=20)
    ok &= v.check(0x14d9c, lambda st, a, b, s: ph.lay_max(st, ph.BLACK_TRAIL, a, b, s), lay_args,
                  label='LayFoodTrailBlack', repeat=20)
    ok &= v.check(0x14dd4, lambda st, a, b, s: ph.lay_max(st, ph.RED_TRAIL, a, b, s), lay_args,
                  label='LayFoodTrailRed', repeat=20)
    ok &= v.check(0x14cf5, lambda st, a, b, s: ph.lay_max(st, ph.ALARM, a, b, s), lay_args,
                  label='DepositAlarm', repeat=20)

    def wear_args(st, i):
        return ((i * 37) % 128, (i * 11) % 64, 0x80 if i & 1 else 0)
    ok &= v.check(0x14e0c, ph.wear_trail, wear_args, label='WearTrail', repeat=20)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
```
{% endraw %}
