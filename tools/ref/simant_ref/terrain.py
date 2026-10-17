"""Surface terrain generation for a yard patch (section 20 and helpers of SIMANT.EXE).

Grids are indexed [a][b] with a = 0..127 (horizontal) and b = 0..63 (vertical), stored flat as a*64 + b,
exactly like the original's 0x3e1d:0180 surface grid.
"""
from .tables import DIR_DX, DIR_DY, ROCK_SHAPES, SMALL_ROCK_SHAPES, PILE_EDGE, SPECIAL_OBJECT_TILE

W, H = 128, 64


class Patch:
    def __init__(self):
        self.surface = bytearray(W * H)      # tiles
        self.occ = bytearray(W * H)          # occupancy (ants)
        self.food_piles = []                 # [a, b, 0, 0, 0] per pile (G:0a92..0ade)
        self.special_objects = []            # (a, b, kind, old_tile) (G:0eae, 0f00, 0f1a, 0f28)
        self.in_house = False

    def tile(self, a, b):
        return self.surface[a * 64 + b]

    def set_tile(self, a, b, t):
        self.surface[a * 64 + b] = t


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


def stamp_food_pile(p, a, b):
    """f_0b09c: 3x3 food pile, centre 0x38, open neighbours 0x30 + PILE_EDGE[d]."""
    if 0 <= a < W and 0 <= b < H:
        p.set_tile(a, b, 0x38)
    for d in range(8):
        na, nb = a + DIR_DX[d], b + DIR_DY[d]
        if _is_open(p, na, nb):
            p.set_tile(na, nb, 0x30 + PILE_EDGE[d])
    if len(p.food_piles) < 10:
        p.food_piles.append([a, b, 0, 0, 0])


def place_food_pile(p, rng):
    """f_0b016."""
    tries = 0
    while tries < 200:
        a = rng.rand(0x41) + rng.rand(0x40)
        b = rng.rand(0x21) + rng.rand(0x20)
        if _is_open_with_ring(p, a, b) or (_is_open(p, a, b) and tries >= 100):
            stamp_food_pile(p, a, b)
            return
        tries += 1


def place_food_piles(p, rng, n):
    """f_0afce."""
    p.food_piles = []
    for _ in range(min(n, 10)):
        place_food_pile(p, rng)


def special_objects(p, rng):
    """f_0ad9c (yard only): two special objects."""
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


def generic_patch(p, rng):
    """f_73c33: terrain for an ordinary yard patch. `rng` must already be seeded with the patch seed."""
    for a in range(W):
        for b in range(H):
            p.set_tile(a, b, rng.rand16())
    place_rocks(p, rng)
    place_food_piles(p, rng, rng.rand4() + 1)
    if not p.in_house:                       # f_0b66c → f_0ad9c
        special_objects(p, rng)
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
