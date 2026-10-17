"""Surface terrain generation for a yard patch (section 20 and helpers of SIMANT.EXE).

Grids are indexed [a][b] with a = 0..127 (horizontal) and b = 0..63 (vertical), stored flat as a*64 + b,
exactly like the original's 0x3e1d:0180 surface grid.

The generator runs on either a standalone `Patch` (with its own Lfsr) or `StateSurface`, the live game
`State` (whose LFSR and globals the original uses; see newgame.py).
"""
from .tables import DIR_DX, DIR_DY, ROCK_SHAPES, SMALL_ROCK_SHAPES, PILE_EDGE, SPECIAL_OBJECT_TILE
from .state import G, T

W, H = 128, 64


class Patch:
    def __init__(self):
        self.surface = bytearray(W * H)      # tiles
        self.occ = bytearray(W * H)          # occupancy (ants)
        self.pits = []                       # ant lion pits [a, b, 0, 0, 0] (G:0a92..0ade, count T:0c4a)
        self.special_objects = []            # the wandering bugs (a, b, kind, old_tile) (G:0eae, 0f00, 0f1a, 0f28)
        self.in_house = False

    def tile(self, a, b):
        return self.surface[a * 64 + b]

    def set_tile(self, a, b, t):
        self.surface[a * 64 + b] = t

    def place_pits(self, rng, n):
        place_pits(self, rng, n)

    def reset_hazards(self, rng):
        """f_0b66c: (counters) and, in the yard, the bugs."""
        if not self.in_house:
            special_objects(self, rng)


class StateSurface:
    """The surface of the live game State, with the original's bookkeeping in its globals."""

    def __init__(self, st):
        self.st = st

    @property
    def in_house(self):
        return self.st.u16(G, 0xf24) != 0

    def tile(self, a, b):
        return self.st.grid(0x0180, a, b)

    def set_tile(self, a, b, t):
        self.st.set_grid(0x0180, a, b, t)

    def place_pits(self, rng, n):
        """f_0afce: n ant lion pits (at most 10; the list keeps 9)."""
        from . import world
        st = self.st
        st.set16(T, 0xc4a, 0)
        st.set16(G, 0xa08, 0)
        n = min(n, 10)
        for _ in range(n):
            world.new_lion(st)
        st.set16(G, 0x8ea, n)

    def reset_hazards(self, rng):
        """f_0b66c."""
        st = self.st
        for seg, off in ((T, 0xc4c), (T, 0xc4e), (T, 0xc50), (G, 0xc36), (G, 0xc3c)):
            st.set16(seg, off, 0)
        for i in range(6):
            st.set16(G, 0xd9c + 2 * i, 0)
        if not self.in_house:
            self.special_objects()

    def special_objects(self):
        """f_0ad9c: the two wandering bugs, slots 2 then 1 (G:0eae a, 0f00 b, 0f1a heading, 0f28 tile under)."""
        st = self.st
        i = 2
        while i:
            a = st.rand(0x80)
            b = st.rand(0x40)
            old = self.tile(a, b)
            if old < 0x10:
                st.set16(G, 0xeae + 2 * i, a)
                st.set16(G, 0xf00 + 2 * i, b)
                kind = st.rand(8)
                st.set16(G, 0xf1a + 2 * i, kind)
                st.set16(G, 0xf28 + 2 * i, old)
                self.set_tile(a, b, st.u8(T, 0xc52 + kind))
                i -= 1


def _get_tile(p, a, b):
    """f_117c0(view=1): surface tile, or -1 outside the patch."""
    if 0 <= a < W and 0 <= b < H:
        return p.tile(a, b)
    return -1


def _is_open(p, a, b):
    """f_1145c(view=1): tile in range and < 0x10, and no occupant other than the player."""
    t = _get_tile(p, a, b)
    if t < 0:
        return False
    if 0 <= a < W and 0 <= b < H:
        o = p.occ[a * 64 + b]
        if o and o not in (0xfe, 0xff):
            return False
    return t < 0x10


def _is_open_with_ring(p, a, b):
    """f_113fe(view=1): centre and all 8 neighbours open."""
    if not _is_open(p, a, b):
        return False
    for d in range(8):
        if not _is_open(p, a + DIR_DX[d], b + DIR_DY[d]):
            return False
    return True


def _stamp(p, a, b, s, n):
    for da in range(n):
        for db in range(n):
            if s[db][da] and p.tile(a + da, b + db) > 0x10:
                return
    for da in range(n):
        for db in range(n):
            if s[db][da]:
                p.set_tile(a + da, b + db, s[db][da])


def rock_stamp(p, a, b, shape):
    """f_73fc6: stamp a 5x5 boulder (all or nothing; blocked by any tile > 0x10)."""
    _stamp(p, a, b, ROCK_SHAPES[shape], 5)


def small_rock_stamp(p, a, b, shape):
    """f_74076: stamp a 3x3 rock (all or nothing; blocked by any tile > 0x10)."""
    _stamp(p, a, b, SMALL_ROCK_SHAPES[shape], 3)


def place_rocks(p, rng):
    """f_73dfd: n = Rand(3)+2 rounds of the 6 big boulders, then 2n rounds of the 6 small rocks."""
    n = rng.rand(3) + 2
    for _ in range(n):
        for shape in range(6):
            b = rng.rand(0x3a)
            a = rng.rand(0x7a)
            rock_stamp(p, a, b, shape)
    for _ in range(2 * n):
        for shape in range(6):
            b = rng.rand(0x3c)
            a = rng.rand(0x7c)
            small_rock_stamp(p, a, b, shape)


def stamp_pit(p, a, b):
    """f_0b09c: an ant lion pit, centre 0x38, open neighbours 0x30 + PILE_EDGE[d]."""
    if 0 <= a < W and 0 <= b < H:
        p.set_tile(a, b, 0x38)
    for d in range(8):
        na, nb = a + DIR_DX[d], b + DIR_DY[d]
        if _is_open(p, na, nb):
            p.set_tile(na, nb, 0x30 + PILE_EDGE[d])
    if len(p.pits) < 10:
        p.pits.append([a, b, 0, 0, 0])


def place_pit(p, rng):
    """f_0b016."""
    tries = 0
    while tries < 200:
        a = rng.rand(0x41) + rng.rand(0x40)
        b = rng.rand(0x21) + rng.rand(0x20)
        if _is_open_with_ring(p, a, b) or (_is_open(p, a, b) and tries >= 100):
            stamp_pit(p, a, b)
            return
        tries += 1


def place_pits(p, rng, n):
    """f_0afce."""
    p.pits = []
    for _ in range(min(n, 10)):
        place_pit(p, rng)


def special_objects(p, rng):
    """f_0ad9c (yard only): the two wandering bugs."""
    p.special_objects = []
    i = 2
    while i:
        a = rng.rand(0x80)
        b = rng.rand(0x40)
        old = p.tile(a, b)
        if old < 0x10:
            kind = rng.rand(8)
            p.special_objects.append((a, b, kind, old))
            p.set_tile(a, b, SPECIAL_OBJECT_TILE[kind])
            i -= 1


def surface_terrain(p, rng, row, col):
    """f_73020: patch idx = row*16 + col; the patches near the house (idx <= 37) are hand-made (f_7304b)."""
    if row * 16 + col <= 0x25:
        raise NotImplementedError('hand-made patch layouts (f_7304b)')
    generic_patch(p, rng)


def generic_patch(p, rng):
    """f_73c33: terrain for an ordinary yard patch. `rng` must already be seeded with the patch seed."""
    if p.in_house:
        # T:07A0 = 1000 and f_0286a(0, 1000): not ported yet (with the house)
        raise NotImplementedError('generic patch in the house')
    for a in range(W):
        for b in range(H):
            p.set_tile(a, b, rng.rand16())
    place_rocks(p, rng)
    p.place_pits(rng, rng.rand4() + 1)
    p.reset_hazards(rng)                     # f_0b66c → f_0ad9c
    for _ in range(20):
        a = rng.rand(0x7d) + 1
        b = rng.rand(0x3d) + 1
        if (p.tile(a, b) < 0x18 and p.tile(a + 1, b) < 0x18 and p.tile(a, b + 1) < 0x18
                and p.tile(a + 1, b + 1) < 0x18):
            p.set_tile(a, b, 0x20)
            p.set_tile(a + 1, b, 0x21)
            p.set_tile(a, b + 1, 0x22)
            p.set_tile(a + 1, b + 1, 0x23)
    for _ in range(30):
        a = rng.rand(0x7d) + 1
        b = rng.rand(0x3d) + 1
        if p.tile(a, b) < 0x18 and p.tile(a + 1, b) < 0x18:
            t = (rng.rand(2) + 0x12) * 2
            p.set_tile(a, b, t)
            p.set_tile(a + 1, b, t + 1)
    for _ in range(100):
        a = rng.rand(0x7d) + 1
        b = rng.rand(0x3d) + 1
        if p.tile(a, b) < 0x18:
            p.set_tile(a, b, 0x28)
    for _ in range(128):
        a = rng.rand(0x7d) + 1
        b = rng.rand(0x3d) + 1
        if p.tile(a, b) < 0x18:
            p.set_tile(a, b, 0x51)
