---
layout: default
title: "SimStep — one game tick"
permalink: /reference/sim/
---

# SimStep — one game tick

*`sim.py` — The original's tick order, preserved exactly.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `sim.py`]({{ site.baseurl }}/assets/reference/simant_ref/sim.py)

`sim_step` is `f_0894e`: it bumps the tick counter and the millisecond clock, resets the on-screen event records when the patch is being watched, and then calls every ported phase in the original's order — health decay every 64 ticks, the slow phase every 32, the yard, weather, ant lions, the spider, the caterpillar on odd ticks, the advisor, the census, surface ants, black nest, red nest, the yellow ant, the player action, the advisor's status line, and the game-over check.

- Order is not cosmetic: several phases read flags the previous one set on the same tick, and swapping two calls changes the random stream.
- Screen-only effects leave through `st.player.effect` (status text, sounds, messages) and the game-over screen through the `st.player` hooks, so the simulation stays headless.
- The tick counter wraps at `0x1000`, which is why the decay phases test `& 0x3f` and `& 0x1f`, not `%`.

## At a glance

- **50** lines
- **1 top-level functions**, including `sim_step`
- **Original routines referenced:** `f_0894e`, `f_2f780`, `f_2f78a`, `f_2f794`, `f_2f79e`, `f_2f7a8`, `f_68513`, `f_71d95`, `f_7b7b8`, `f_7bf7e`

## Source

{% raw %}
```python
"""SimStep (f_0894e): one game tick, calling every ported part of the simulation in the original's order.

Screen-only effects go to st.player.effect; the game-over screen (f_71d95, via the vector f_2f780) and the
other player-event UI go to st.player hooks.
"""
from .state import G, T
from . import colony as co
from . import world
from . import yard
from . import surface
from . import nest
from . import red_nest
from . import player


def sim_step(st):
    """f_0894e."""
    st.inc16(G, 0xf08)
    if st.s16(G, 0xf08) > 0x1000:                                      # the tick counter wraps after 0x1000
        st.set16(G, 0xf08, 0)
    st.inc32(G, 0xc26)
    if st.u16(T, 0x7b2) == 1:                                          # the patch is shown: reset the records
        for off in (0xf06, 0xf2e, 0xf10, 0xef6):
            st.set16(G, off, 0)
        st.set16(G, 0x8ec, 0xffff)
        st.set16(G, 0x8ee, 0xffff)
        for off in (0xaa2, 0xa02, 0x852):
            st.set32(G, off, 0xffffffff)
    if st.u8(G, 0xf08) & 0x3f == 0:
        co.health_decay(st)
    if st.u8(G, 0xf08) & 0x1f == 0:
        world.slow_phase(st)
    yard.yard_step(st)                                                 # f_2f7a8 → sec8 f_68513
    world.weather(st)
    world.ant_lions(st)
    world.spider(st)
    if st.u8(G, 0xf08) & 1:
        world.caterpillar(st)
    co.colony_advisor(st, lambda *a: st.player.effect(st, 'status', *a))
    co.reset_census(st)
    surface.surface_ants_tick(st)
    nest.black_nest_loop(st)                                           # f_2f79e
    red_nest.red_nest_loop(st)
    player.yellow_tick(st)                                             # f_2f794 → f_7bf7e
    co.stats_from_census(st)
    player.player_action(st)                                           # f_2f78a → f_7b7b8
    world.advisor(st)
    if st.u16(G, 0x376):
        st.player.game_over(st)                                        # f_2f780 → f_71d95
    st.set16(T, 0x2c2, 1)
```
{% endraw %}
