"""The map's event markers: where on screen the latest hatching, fight, egg laying and resting happened.

The simulation reports these only while the patch is visible (T:07B2), through st.player.effect with
'brood', 'fight', 'queen' or 'rest' and (a, b, view). In the original each report goes to a recorder that
writes the marker's globals when the spot is on screen; the marker animation (f_06a4d, called from the
window draw) latches a recorded spot, arms a timer and draws its bitmap group there. SimStep clears the
records when the patch is shown (sim.py). See SIM_NOTES "Event markers".

A renderer calls record(st, kind, a, b, view) from its effect hook to keep these globals as the original does.
"""
from .state import G
from .movement import s16

# kind: (recorder, gate, latched a / b / view (set by f_06a4d), recorded a / b / view)
KINDS = {
    'brood': ('f_0678a', 0xef6, (0x8de, 0x8e0, 0xad8), (0x852, 0x854, 0xaca)),
    'fight': ('f_06802', 0xf06, (0x9f2, 0x9f4, 0xb06), (0x8ec, 0x8ee, 0xaea)),
    'queen': ('f_0687a', 0xf10, (0xa8a, 0xa8c, 0xc3a), (0xa02, 0xa04, 0xb08)),
    'rest': ('f_068f2', 0xf2e, (0xab2, 0xab4, 0xd9a), (0xaa2, 0xaa4, 0xd68)),
}


def on_screen(st, view, a, b):
    """f_06725: (a, b) is inside the map window showing `view` (origin G:0508 / G:050A, size G:10E0 x
    G:10DE; the top three rows of the window don't count)."""
    if st.u16(G, 0x32e) != view & 0xffff:
        return 0
    x0, y0 = s16(st.u16(G, 0x508)), s16(st.u16(G, 0x50a))
    if not (x0 <= a < x0 + s16(st.u16(G, 0x10e0))):
        return 0
    if not (y0 <= b - 3 and b < y0 + s16(st.u16(G, 0x10de))):
        return 0
    return 1


def record(st, kind, a, b, view):
    """f_0678a / f_06802 / f_0687a / f_068f2: while the marker is free (gate 0) and the spot is on screen,
    record it; the spot the animation has latched counts up the gate instead (no new marker there)."""
    _, gate, latched, rec = KINDS[kind]
    a, b, view = s16(a), s16(b), s16(view)
    if st.u16(G, gate) != 0 or not on_screen(st, view, a, b):
        return
    if (st.u16(G, latched[0]) == a & 0xffff and st.u16(G, latched[1]) == b & 0xffff
            and st.u16(G, latched[2]) == view & 0xffff):
        st.set16(G, gate, st.u16(G, gate) + 1)
        return
    st.set16(G, rec[0], a & 0xffff)
    st.set16(G, rec[1], b & 0xffff)
    st.set16(G, rec[2], view & 0xffff)
