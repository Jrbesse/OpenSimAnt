---
layout: default
title: "render_state"
permalink: /reference/render-state/
---

# render_state

*`render_state.py` — Run the original simulation for N ticks and render the sim state to PNGs (debug colours, not game art).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `render_state.py`]({{ site.baseurl }}/assets/reference/re/render_state.py)

Run the original simulation for N ticks and render the sim state to PNGs (debug colours, not game art).

python render_state.py [ticks] [out_dir]

Writes surface.png (128x64 grid drawn as [a][b] with a horizontal), black_nest.png, red_nest.png and
pheromones.png, each scaled up 4x.

## At a glance

- **95** lines
- **4 top-level functions**, including `surface_colour`, `nest_colour`, `save`, `main`

## Source

{% raw %}
```python
"""Run the original simulation for N ticks and render the sim state to PNGs (debug colours, not game art).

python render_state.py [ticks] [out_dir]

Writes surface.png (128x64 grid drawn as [a][b] with a horizontal), black_nest.png, red_nest.png and
pheromones.png, each scaled up 4x.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import emu                          # noqa: E402
from emu import G, DGROUP           # noqa: E402
from png import write_png           # noqa: E402

SCALE = 4


def surface_colour(t, occ):
    if occ:
        if occ in (0xfe, 0xff):
            return (255, 230, 0)
        return (220, 40, 40) if occ & 0x80 else (20, 20, 20)
    if 0x48 <= t <= 0x4b:
        return (40, 200, 40)                      # food
    if t == 0x50:
        return (120, 60, 20)                      # nest entrance
    if 0x10 <= t <= 0x17:
        return (140, 120, 140)                    # corpse
    if t < 0x10:
        return (190, 160, 110)                    # ground
    return (90 + (t * 7) % 120, 90, 160)          # other tiles: hashed blue/purple


def nest_colour(d, cell):
    if cell:
        caste = (cell >> 3) & 15
        if cell in (0xfe, 0xff):
            return (255, 230, 0)
        if caste == 0:
            return (255, 255, 255)                # brood
        if caste in (12, 13):
            return (255, 0, 255)                  # queen
        return (220, 40, 40) if cell & 0x80 else (20, 20, 20)
    if d < 0x10:
        return (60, 40, 25)                       # tunnel
    if d <= 0x13:
        return (40, 200, 40)                      # stored food
    if d == 0x18:
        return (200, 160, 60)                     # entrance shaft
    if 0x20 <= d <= 0x2e:
        return (150, 110, 70)                     # exposed dirt
    return (110, 80, 50)                          # solid dirt / rock


def save(path, w, h, colour_at):
    rows = []
    for y in range(h * SCALE):
        rows.append([colour_at(x // SCALE, y // SCALE) + (255,) for x in range(w * SCALE)])
    write_png(path, w * SCALE, h * SCALE, rows)


def main():
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join('build', 'render')
    os.makedirs(out, exist_ok=True)
    e = emu.SimEmu(base=0x100)
    e.boot(max_insns=1_000_000_000)
    e.stub_drawing()
    e.set16(G, 0xeac, 1)
    e.set16(DGROUP, 0x8ba2, 0x1234)
    e.call_lin(0x6b36b)
    for _ in range(ticks):
        e.call_lin(0x0894e)
    s = e.read(emu.SIM, 0, 0x10900)       # red trail map extends past 64 KB (reached via seg 0x4da7)
    surf, occ = s[0x0180:0x2180], s[0x6180:0x8180]
    save(os.path.join(out, 'surface.png'), 128, 64, lambda x, y: surface_colour(surf[x * 64 + y], occ[x * 64 + y]))
    for name, dirt, cells in (('black_nest', 0x2180, 0x8180), ('red_nest', 0x3180, 0x9180)):
        d, c = s[dirt:dirt + 0x1000], s[cells:cells + 0x1000]
        # nest grid is [col][depth]; draw col horizontal, depth downward
        save(os.path.join(out, name + '.png'), 64, 64, lambda x, y: nest_colour(d[x * 64 + y], c[x * 64 + y]))
    maps = [('bnest', 0xe09f), ('btrail', 0xe89f), ('rnest', 0xf09f), ('rtrail', 0xf89f), ('alarm', 0xd09f)]

    def pher(x, y):
        i = (x // 64)
        name, off = maps[i] if i < len(maps) else maps[-1]
        v = s[off + (x % 64) * 32 + y]
        return (v, v, v) if i < len(maps) else (0, 0, 0)
    save(os.path.join(out, 'pheromones.png'), 64 * len(maps), 32, pher)
    print('wrote', out, 'after', ticks, 'ticks')
    print('entrances black (b -> a):', {b: s[0] for b in range(1)})


if __name__ == '__main__':
    main()
```
{% endraw %}
