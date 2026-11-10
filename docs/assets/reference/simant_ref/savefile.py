"""Saved games (.ANT): save (f_6c328) and load (f_6c1a0, fix-ups f_6cf1a / f_6cf5b).

A saved game has no header: it is the game state's memory blocks, one after the other, in the order of
the table at 4E4B:0000 in SIMANT.EXE (entries {count, size, far pointer}, 8 bytes, ending with size 0;
307 blocks, 48386 bytes). The table is read from the user's own executable at runtime.

Not saved, and rebuilt on load: the surface occupancy and both nests' cells (from the ant lists), the
yellow ant on the map, the census. Loading starts a new game first (f_6cf1a), so anything not in the
file comes from a fresh game.
"""
import struct

from .state import SIM, G, T, DS
from .tables import _data
from . import newgame
from . import player
from . import world
from . import terrain

TABLE = 0x4e4b0                  # flat address of 4E4B:0000


def blocks():
    """[(seg, off, length)] in file order."""
    flat, out, a = _data(), [], TABLE
    while True:
        count, size, off, seg = struct.unpack('<hHHH', flat[a:a + 8])
        if size == 0:
            return out
        out.append((seg, off, (count * size) & 0xffff))
        a += 8


def file_size():
    return sum(n for _, _, n in blocks())


def save(st):
    """f_6c328 (after its file dialog): the bytes of the saved game; the game counts as saved (T:02C2 = 0)."""
    out = bytearray()
    for seg, off, n in blocks():
        out += bytes(st.u8(seg, off + i) for i in range(n))
    st.set16(T, 0x2c2, 0)
    return bytes(out)


def prepare_load(st):
    """f_6cf1a: a fresh game to load into."""
    st.set16(G, 0x354, 1)
    st.set32(G, 0x214, 0)
    st.set32(G, 0x204, 0x12c)
    st.set32(G, 0x472, 0)
    newgame.new_game(st)


def finish_load(st):
    """f_6cf5b: the tile set, the occupancy and nest cells rebuilt from the ant lists (each list from one
    past its last ant, sic), the yellow ant back on the map, census and advisor."""
    terrain.StateSurface(st).set_tileset(1 if st.u16(G, 0xf24) == 1 else 0)
    for i in range(0x2000):
        st.set8(SIM, 0x6180 + i, 0)
    for i in range(0x1000):
        st.set8(SIM, 0x8180 + i, 0)
        st.set8(SIM, 0x9180 + i, 0)
    for count, tf, xf, yf, cells in ((0xd6a, 0xad3b, 0xa180, 0xa569, 0x6180),
                                     (0xda8, 0xbaec, 0xb50d, 0xb702, 0x8180),
                                     (0xeaa, 0xc4b5, 0xbed6, 0xc0cb, 0x9180)):
        i = player.s16(st.u16(G, count))
        while i >= 0:
            st.set8(SIM, (cells + st.u8(SIM, xf + i) * 64 + st.u8(SIM, yf + i)) & 0xffff, st.u8(SIM, tf + i))
            i -= 1
    if st.u16(G, 0xa06) == 0:
        g = lambda off: player.s16(st.u16(G, off))
        player.put_yellow(st, g(0x48c), g(0x47c), g(0x48a), g(0x4c2), st.u16(G, 0x496), 0xff)
    world.census_and_advise(st)                                        # f_0c20f
    st.player.effect(st, 'colony_panel')                               # f_2f988 → f_7256f
    st.player.effect(st, 'picture', 1)


def load(st, data):
    """f_6c1a0 (after its file dialog): load a saved game. A short file is a read error: the blocks read
    so far stay, the game mode becomes -1 (no game) and nothing is rebuilt. Returns True if loaded."""
    st.set16(T, 0x2c2, 0)
    prepare_load(st)
    pos = 0
    for seg, off, n in blocks():
        got = data[pos:pos + n]                                        # read() copies what there is
        for i, v in enumerate(got):
            st.set8(seg, off + i, v)
        pos += n
        if len(got) != n:
            st.player.effect(st, 'message', 0x2757)                    # "Read error, game not loaded"
            st.set16(G, 0xeac, 0xffff)
            return False
    st.player.effect(st, 'edit_tool', 1)                               # f_2f97e, f_2f816(1): menus
    finish_load(st)
    return True
