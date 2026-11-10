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
