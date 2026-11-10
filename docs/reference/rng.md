---
layout: default
title: "The two random number generators"
permalink: /reference/rng/
---

# The two random number generators

*`rng.py` — An LFSR and Microsoft C's rand(), both draw-for-draw.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `rng.py`]({{ site.baseurl }}/assets/reference/simant_ref/rng.py)

The simulation draws from two generators in parallel and both are load-bearing. `Lfsr` is the game's own 16-bit Galois LFSR at `DS:8ba2`: `x <<= 1`, and `x ^= 0x1bf5` on carry. `CrtRand` is Microsoft C 6.0's `rand()`: `s = s * 214013 + 2531011`, returning `(s >> 16) & 0x7fff`.

- `rand_low(n)` is `min(rand(n), rand(n))` (`f_0095b`) — the original's biased-for-zero variant, not a uniform roll.
- `bits(mask)` covers the `x & mask` family at `0093:0169..0250` that the game uses for small ranges.
- Matching a seed is not enough: the spider composite, the speech balloons and the yard rain all consume draws, so a port must call them at the original's moments or the streams diverge.

## At a glance

- **53** lines
- **Classes / hooks:** `Lfsr`, `CrtRand`
- **Original routines referenced:** `f_0095b`

## Source

{% raw %}
```python
"""Random number generators (segment 0093 of SIMANT.EXE)."""


class Lfsr:
    """The game's 16-bit Galois LFSR (state at DS:8ba2): x <<= 1; if carry: x ^= 0x1bf5."""

    def __init__(self, seed=0):
        self.x = seed & 0xffff

    def step(self):
        x = self.x << 1
        if x & 0x10000:
            x ^= 0x1bf5
        self.x = x & 0xffff
        return self.x

    def rand(self, n):
        """0093:013d - x % n (unsigned)."""
        return self.step() % n

    def bits(self, mask):
        """0093:0169..0250 - x & mask (mask = 1, 3, 7, 15, 31, 63, 127, 255)."""
        return self.step() & mask

    def rand2(self): return self.bits(1)
    def rand4(self): return self.bits(3)
    def rand8(self): return self.bits(7)
    def rand16(self): return self.bits(15)
    def rand32(self): return self.bits(31)
    def rand64(self): return self.bits(63)
    def rand128(self): return self.bits(127)
    def rand256(self): return self.bits(255)

    def rand_low(self, n):
        """0093:002b (f_0095b) - min(Rand(n), Rand(n)), biased towards 0."""
        a = self.rand(n)
        b = self.rand(n)
        return b if b < a else a


class CrtRand:
    """Microsoft C 6.0 runtime rand(): s = s*214013 + 2531011; return (s >> 16) & 0x7fff."""

    def __init__(self, seed=1):
        self.s = seed & 0xffffffff

    def rand(self):
        self.s = (self.s * 214013 + 2531011) & 0xffffffff
        return (self.s >> 16) & 0x7fff

    def rand_mod(self, n):
        """0093:0118 - abs(rand()) % n."""
        return abs(self.rand()) % n
```
{% endraw %}
