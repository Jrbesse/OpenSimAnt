---
layout: default
title: "Surface terrain generation"
permalink: /reference/terrain/
---

# Surface terrain generation

*`terrain.py` — The yard patch: rocks, pits, the house, and the layout solver.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `terrain.py`]({{ site.baseurl }}/assets/reference/simant_ref/terrain.py)

Generates one yard patch (`f_73020`, section 20) on a 128 × 64 grid indexed `[a][b]` and stored flat as `a*64 + b`, exactly like the original's `0x3e1d:0180`. It places rocks, pits, special objects and the house patch, drawing from the LFSR as it goes. `Patch` runs standalone with its own generator; `StateSurface` drives the live game `State` and the original's globals.

- The house screens are composed from a wall/box/counter/stove vocabulary — `_wall_left`, `_box_wide`, `_counter`, `_stove` — rather than drawn as a bitmap, because the original composes them too.
- Determinism here is seed-only: the same seed and patch coordinates give the same yard, which is how the screen comparisons are reproducible.
- Grid conventions matter: `a` is horizontal 0..127, `b` vertical 0..63, and a transposed access still looks like a plausible yard while being wrong.

## At a glance

- **490** lines
- **Classes / hooks:** `Patch`, `StateSurface`
- **29 top-level functions**, including `_get_tile`, `_is_open`, `_is_open_with_ring`, `_stamp`, `rock_stamp`, `small_rock_stamp`, `place_rocks`, `stamp_pit` …
- **Original routines referenced:** `f_02756`, `f_0286a`, `f_0ad9c`, `f_0afce`, `f_0b016`, `f_0b09c`, `f_0b66c`, `f_113fe`, `f_1145c`, `f_117c0`, `f_73020`, `f_7304b` …

## Source

{% raw %}
```python
"""Surface terrain generation for a yard patch (section 20 and helpers of SIMANT.EXE).

Grids are indexed [a][b] with a = 0..127 (horizontal) and b = 0..63 (vertical), stored flat as a*64 + b,
exactly like the original's 0x3e1d:0180 surface grid.

The generator runs on either a standalone `Patch` (with its own Lfsr) or `StateSurface`, the live game
`State` (whose LFSR and globals the original uses; see newgame.py).
"""
from .tables import DIR_DX, DIR_DY, ROCK_SHAPES, SMALL_ROCK_SHAPES, PILE_EDGE, SPECIAL_OBJECT_TILE, ds_bytes
from .state import G, T, DS

W, H = 128, 64


class Patch:
    def __init__(self):
        self.surface = bytearray(W * H)      # tiles
        self.occ = bytearray(W * H)          # occupancy (ants)
        self.pits = []                       # ant lion pits [a, b, 0, 0, 0] (G:0a92..0ade, count T:0c4a)
        self.special_objects = []            # the wandering bugs (a, b, kind, old_tile) (G:0eae, 0f00, 0f1a, 0f28)
        self.in_house = False
        self.room = 0                        # G:0f3a: which part of the house (see house_patch)

    def tile(self, a, b):
        return self.surface[a * 64 + b]

    def set_tileset(self, house):
        self.in_house = bool(house)

    def set_room(self, v):
        self.room = v

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
        return self.st.u16(G, 0xf24)

    def tile(self, a, b):
        return self.st.grid(0x0180, a, b)

    def set_tile(self, a, b, t):
        self.st.set_grid(0x0180, a, b, t)

    def set_tileset(self, house):
        """T:07A0 = 1000 + house; f_0286a(0, that): the yard or house tile set (f_02756: G:0F24, cached in
        DS:1A2E; the graphics are UI) and the highest passable tile G:0480."""
        st = self.st
        st.set16(T, 0x7a0, 0x3e8 + house)
        if st.u16(DS, 0x1a2e) != house:
            st.set16(DS, 0x1a2e, house)
            st.set16(G, 0xf24, house)
            st.player.effect(st, 'tileset', house)
        st.set16(G, 0x480, 0x90 if house else 0x50)

    def set_room(self, v):
        self.st.set16(G, 0xf3a, v)

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
    """f_73020: patch idx = row*16 + col; the house (idx <= 37) is hand-made (f_7304b)."""
    idx = row * 16 + col                     # signed compare here, unsigned table bound in f_7304b
    if idx <= 0x25:
        house_patch(p, rng, idx & 0xffff)
    else:
        generic_patch(p, rng)


def generic_patch(p, rng):
    """f_73c33: terrain for an ordinary yard patch. `rng` must already be seeded with the patch seed."""
    if p.in_house:
        p.set_tileset(0)
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


# ------------------------------------------------------------------------------------------- the house
def _fill(p, a0, a1, b0, b1, t):
    """f_73b17: a rectangle of one tile (inclusive bounds)."""
    for a in range(a0, a1 + 1):
        for b in range(b0, b1 + 1):
            p.set_tile(a, b, t)


def _sprinkle(p, rng, a0, a1, b0, b1):
    """f_733e9: 1 cell in 200 gets 0x3E + Rand(2)."""
    for a in range(a0, a1 + 1):
        for b in range(b0, b1 + 1):
            if rng.rand(200) == 0:
                p.set_tile(a, b, rng.rand(2) + 0x3e)


def _blit(p, a, b, off, wa, wb, stride_b, skip_zero=False):
    """f_73931 / f_739f4 / f_73a3a / f_73a83 / f_73acb: copy a wa x wb picture from DS:off, cell (i, j) at
    off + j * stride_b + i."""
    data = ds_bytes(off, stride_b * wb + wa)
    for i in range(wa):
        for j in range(wb):
            v = data[j * stride_b + i]
            if v or not skip_zero:
                p.set_tile(a + i, b + j, v)


def _frame_in(p, a0, a1, b0, b1):
    """f_73777: a raised border (corners 0x53 0x55 0x50 0x52)."""
    _fill(p, a0, a1, b0, b0, 0x54)
    _fill(p, a0, a1, b1, b1, 0x51)
    _fill(p, a0, a0, b0, b1, 0x5a)
    _fill(p, a1, a1, b0, b1, 0x5b)
    p.set_tile(a0, b0, 0x53)
    p.set_tile(a1, b0, 0x55)
    p.set_tile(a0, b1, 0x50)
    p.set_tile(a1, b1, 0x52)


def _frame_out(p, a0, a1, b0, b1):
    """f_73817: a sunken border (corners 0x56 0x58 0x57 0x59)."""
    _fill(p, a0, a1, b0, b0, 0x51)
    _fill(p, a0, a1, b1, b1, 0x54)
    _fill(p, a0, a0, b0, b1, 0x5b)
    _fill(p, a1, a1, b0, b1, 0x5a)
    p.set_tile(a0, b0, 0x56)
    p.set_tile(a1, b0, 0x58)
    p.set_tile(a0, b1, 0x57)
    p.set_tile(a1, b1, 0x59)


def _box_wide(p, a, b):
    """f_7397a: a 13 x 9 box with two pictures (DS:2C6E) and a 0x65 mark."""
    _fill(p, a, a + 12, b, b + 8, 99)
    _frame_in(p, a, a + 12, b, b + 8)
    _blit(p, a + 2, b + 2, 0x2c6e, 4, 5, 4)
    _blit(p, a + 7, b + 2, 0x2c6e, 4, 5, 4)
    p.set_tile(a + 6, b + 4, 0x65)


def _box_tall(p, a, b):
    """f_738b7: a 9 x 13 box with two pictures (DS:2C5A) and a 0x65 mark."""
    _fill(p, a, a + 8, b, b + 12, 99)
    _frame_in(p, a, a + 8, b, b + 12)
    _blit(p, a + 2, b + 2, 0x2c5a, 5, 4, 5)
    _blit(p, a + 2, b + 7, 0x2c5a, 5, 4, 5)
    p.set_tile(a + 4, b + 6, 0x65)


def _square(p, rng, a0, a1, b0, b1, t):
    """f_73b54: a rectangle of t, 1 cell in 20 replaced by 0x38 + Rand(5), with 4 x 4 corners of 0xC0."""
    _fill(p, a0, a1, b0, b1, t)
    for a in range(a0, a1 + 1):
        for b in range(b0, b1 + 1):
            if rng.rand(0x14) == 0:
                p.set_tile(a, b, rng.rand(5) + 0x38)
    _fill(p, a0, a0 + 3, b0, b0 + 3, 0xc0)
    _fill(p, a1 - 3, a1, b0, b0 + 3, 0xc0)
    _fill(p, a0, a0 + 3, b1 - 3, b1, 0xc0)
    _fill(p, a1 - 3, a1, b1 - 3, b1, 0xc0)


def _wall_left(p, rng):
    """f_73350 (room 1): a wall on the left (a 0..23), the floor beyond it, a box."""
    _fill(p, 0, 0x14, 0, 0x3f, 0x64)
    _fill(p, 0x15, 0x15, 0, 0x3f, 0x7a)
    _fill(p, 0x16, 0x17, 0, 0x3f, 0x7b)
    _fill(p, 0x17, 0x7f, 0, 0x3f, 3)
    _sprinkle(p, rng, 0x17, 0x7f, 0, 0x3f)
    _box_wide(p, 2, 0x19)
    p.set_room(1)


def _wall_right(p, rng):
    """f_7343d (room 3): the floor, then a wall on the right (a 104..127), a box."""
    _fill(p, 0, 0x69, 0, 0x3f, 3)
    _sprinkle(p, rng, 0, 0x69, 0, 0x3f)
    _fill(p, 0x6a, 0x6a, 0, 0x3f, 0x7c)
    _fill(p, 0x68, 0x69, 0, 0x3f, 0x7b)
    _fill(p, 0x6a, 0x7f, 0, 0x3f, 0x64)
    _box_wide(p, 0x71, 0x23)
    p.set_room(3)


def _counter(p):
    """f_734d3 (room 2): a counter along the top (b 0..23) with two boxes."""
    _fill(p, 0, 0x7f, 0, 0x17, 0x62)
    _fill(p, 0, 0x7f, 0x18, 0x3f, 0)
    for b in (0, 8, 0x10):
        for a in range(0x80):
            p.set_tile(a, b, 0x68)
    for a in range(0, 0x80, 8):
        for b in range(0x18):
            p.set_tile(a, b, 0x66 if p.tile(a, b) == 0x62 else 0x67)
    for a in range(0x80):
        p.set_tile(a, 0x17, 0x68 if p.tile(a, 0x17) == 0x62 else 0x69)
    _box_tall(p, 0x24, 2)
    _box_tall(p, 0x54, 2)
    p.set_room(2)


def _stove(p):
    """f_735d5: the big fitting under the counter (patch 0)."""
    _fill(p, 0x25, 0x5b, 0x1a, 0x38, 1)
    _fill(p, 0x29, 0x44, 0x21, 0x35, 0xc2)
    _fill(p, 0x2a, 0x44, 0x23, 0x35, 0xc1)
    _frame_out(p, 0x28, 0x44, 0x20, 0x35)
    _fill(p, 0x49, 0x58, 0x21, 0x35, 0xc2)
    _fill(p, 0x4a, 0x58, 0x23, 0x35, 0xc1)
    _frame_out(p, 0x48, 0x58, 0x20, 0x35)
    _frame_in(p, 0x25, 0x5b, 0x1a, 0x38)
    _blit(p, 0x2c, 0x1b, 0x2c82, 5, 5, 5)
    _blit(p, 0x3c, 0x1b, 0x2c82, 5, 5, 5)
    p.set_tile(0x3e, 0x1d, 0x4d)
    _blit(p, 0x34, 0x1b, 0x2c82, 5, 5, 5)
    _blit(p, 0x34, 0x24, 0x2c82, 5, 5, 5)
    _fill(p, 0x34, 0x38, 0x1d, 0x26, 0x4e)
    _fill(p, 0x34, 0x34, 0x1d, 0x26, 0x43)
    _fill(p, 0x38, 0x38, 0x1d, 0x26, 0x44)
    p.set_tile(0x34, 0x28, 0x45)
    p.set_tile(0x38, 0x28, 0x48)
    _fill(p, 0x36, 0x38, 0x29, 0x2a, 0xc2)
    _fill(p, 0x39, 0x3a, 0x23, 0x2a, 0xc2)


def _tiles(p):
    """f_73236 (room 0): the checkered floor with grout lines."""
    for a in range(0x80):
        for b in range(0x40):
            p.set_tile(a, b, 0 if ((b >> 4) + (a >> 4)) & 1 else 1)
    for b in range(0, 0x40, 0x10):
        for a in range(0x80):
            p.set_tile(a, b, 0x60 if (a + b) & 0x10 else 0x61)
    for a in range(0, 0x80, 0x10):
        for b in range(0x40):
            if p.tile(a, b) < 2:
                p.set_tile(a, b, 0x5e if (a + b) & 0x10 else 0x5f)
            else:
                p.set_tile(a, b, 0x5d if (a + b) & 0x10 else 0x5c)
    p.set_room(0)


def _picture(p, a, b):
    """f_73a83: a 3 x 3 picture (DS:2C9C)."""
    _blit(p, a, b, 0x2c9c, 3, 3, 3)


def _picture_over(p, a, b):
    """f_73acb: a 3 x 3 picture (DS:2CA6) over what is there."""
    _blit(p, a, b, 0x2ca6, 3, 3, 3, skip_zero=True)


def house_patch(p, rng, idx):
    """f_7304b: the 38 hand-made patches of the house (yard rows 0..1 and row 2 up to col 5)."""
    if p.in_house != 1:
        p.set_tileset(1)
    p.place_pits(rng, 0)
    p.reset_hazards(rng)
    if idx == 0:
        _counter(p)
        _stove(p)
    elif idx in (1, 16, 32):
        _counter(p)
    elif idx in (2, 3, 17, 18, 19, 33, 34, 35):
        _tiles(p)
    elif idx in (4, 10, 11, 13, 14):
        _wall_left(p, rng)
    elif idx == 5:
        _wall_left(p, rng)
        _fill(p, 0x18, 0x46, 0x14, 0x3f, 2)
        _picture(p, 0x28, 0x2d)
    elif idx == 6:
        _wall_left(p, rng)
        _fill(p, 0x18, 0x46, 0, 0x3f, 2)
        _picture(p, 0x20, 0x14)
        _picture_over(p, 0x26, 0x37)
    elif idx == 7:
        _wall_left(p, rng)
        _fill(p, 0x18, 0x46, 0, 0x14, 2)
        _picture_over(p, 0x2a, 0xa)
    elif idx == 8:
        _wall_left(p, rng)
        _square(p, rng, 0x18, 0x36, 0xf, 0x2d, 2)
        _picture_over(p, 0x1c, 0x22)
    elif idx == 9:
        _fill(p, 0, 0x7f, 0, 0x3f, 3)
        p.set_room(2)
    elif idx == 12:
        _wall_left(p, rng)
        _square(p, rng, 0x2d, 0x5f, 8, 0x2e, 2)
    elif idx == 15:
        _wall_left(p, rng)
        _square(p, rng, 0x32, 0x64, 0xa, 0x2d, 2)
        _picture(p, 0x4b, 0x22)
    elif 20 <= idx <= 31:
        _wall_right(p, rng)
    elif idx in (36, 37):
        _fill(p, 0, 0x7f, 0, 0x3f, 0)
        p.set_room(2)
```
{% endraw %}
