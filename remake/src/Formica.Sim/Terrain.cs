using static Formica.Sim.Seg;

namespace Formica.Sim;

/// <summary>Surface terrain generation for a yard patch (section 20 and helpers of SIMANT.EXE), on the live
/// game State: the generator draws from the game's LFSR and keeps the original's bookkeeping in its globals.
/// Grids are indexed [a][b] with a = 0..127 (horizontal) and b = 0..63 (vertical), stored flat as a*64 + b
/// (the 0x3e1d:0180 surface grid). The constant tables (rock shapes T:08C2 / T:0958, the bug tiles T:0C52,
/// the house pictures in DS) are read from the State, which holds the original's data.</summary>
public static class Terrain
{
    public const int W = 128, H = 64;

    static int Tile(State st, int a, int b) => st.Grid(0x0180, a, b);

    static void SetTile(State st, int a, int b, int t) => st.SetGrid(0x0180, a, b, t);

    static bool InHouse(State st) => st.U16(G, 0xf24) != 0;

    /// <summary>T:07A0 = 1000 + house; f_0286a(0, that): the yard or house tile set (f_02756: G:0F24, cached in
    /// DS:1A2E; the graphics are UI) and the highest passable tile G:0480.</summary>
    public static void SetTileset(State st, int house)
    {
        st.Set16(T, 0x7a0, 0x3e8 + house);
        if (st.U16(DS, 0x1a2e) != house)
        {
            st.Set16(DS, 0x1a2e, house);
            st.Set16(G, 0xf24, house);
            st.Hooks.Effect(st, "tileset", house);
        }
        st.Set16(G, 0x480, house != 0 ? 0x90 : 0x50);
    }

    static void SetRoom(State st, int v) => st.Set16(G, 0xf3a, v);

    /// <summary>f_0afce: n ant lion pits (at most 10; the list keeps 9).</summary>
    public static void PlacePits(State st, int n)
    {
        st.Set16(T, 0xc4a, 0);
        st.Set16(G, 0xa08, 0);
        n = Math.Min(n, 10);
        for (int k = 0; k < n; k++) World.NewLion(st);
        st.Set16(G, 0x8ea, n);
    }

    /// <summary>f_0b66c.</summary>
    public static void ResetHazards(State st)
    {
        st.Set16(T, 0xc4c, 0);
        st.Set16(T, 0xc4e, 0);
        st.Set16(T, 0xc50, 0);
        st.Set16(G, 0xc36, 0);
        st.Set16(G, 0xc3c, 0);
        for (int i = 0; i < 6; i++) st.Set16(G, 0xd9c + 2 * i, 0);
        if (!InHouse(st)) SpecialObjects(st);
    }

    /// <summary>f_0ad9c: the two wandering bugs, slots 2 then 1 (G:0eae a, 0f00 b, 0f1a heading, 0f28 tile under).</summary>
    public static void SpecialObjects(State st)
    {
        int i = 2;
        while (i != 0)
        {
            int a = st.Rand(0x80);
            int b = st.Rand(0x40);
            int old = Tile(st, a, b);
            if (old < 0x10)
            {
                st.Set16(G, 0xeae + 2 * i, a);
                st.Set16(G, 0xf00 + 2 * i, b);
                int kind = st.Rand(8);
                st.Set16(G, 0xf1a + 2 * i, kind);
                st.Set16(G, 0xf28 + 2 * i, old);
                SetTile(st, a, b, st.U8(T, 0xc52 + kind));
                i--;
            }
        }
    }

    static int Shape(State st, int tableOff, int n, int shape, int b, int a) => st.U8(T, tableOff + (shape * n + b) * n + a);

    static void Stamp(State st, int a, int b, int tableOff, int shape, int n)
    {
        for (int da = 0; da < n; da++)
            for (int db = 0; db < n; db++)
                if (Shape(st, tableOff, n, shape, db, da) != 0 && Tile(st, a + da, b + db) > 0x10) return;
        for (int da = 0; da < n; da++)
            for (int db = 0; db < n; db++)
            {
                int v = Shape(st, tableOff, n, shape, db, da);
                if (v != 0) SetTile(st, a + da, b + db, v);
            }
    }

    /// <summary>f_73fc6: stamp a 5x5 boulder (all or nothing; blocked by any tile > 0x10).</summary>
    public static void RockStamp(State st, int a, int b, int shape) => Stamp(st, a, b, 0x08c2, shape, 5);

    /// <summary>f_74076: stamp a 3x3 rock (all or nothing; blocked by any tile > 0x10).</summary>
    public static void SmallRockStamp(State st, int a, int b, int shape) => Stamp(st, a, b, 0x0958, shape, 3);

    /// <summary>f_73dfd: n = Rand(3)+2 rounds of the 6 big boulders, then 2n rounds of the 6 small rocks.</summary>
    public static void PlaceRocks(State st)
    {
        int n = st.Rand(3) + 2;
        for (int k = 0; k < n; k++)
            for (int shape = 0; shape < 6; shape++)
            {
                int b = st.Rand(0x3a);
                int a = st.Rand(0x7a);
                RockStamp(st, a, b, shape);
            }
        for (int k = 0; k < 2 * n; k++)
            for (int shape = 0; shape < 6; shape++)
            {
                int b = st.Rand(0x3c);
                int a = st.Rand(0x7c);
                SmallRockStamp(st, a, b, shape);
            }
    }

    /// <summary>f_73020: patch idx = row*16 + col; the house (idx &lt;= 37) is hand-made (f_7304b).</summary>
    public static void SurfaceTerrain(State st, int row, int col)
    {
        int idx = row * 16 + col;                     // signed compare here, unsigned table bound in f_7304b
        if (idx <= 0x25) HousePatch(st, idx & 0xffff);
        else GenericPatch(st);
    }

    /// <summary>f_73c33: terrain for an ordinary yard patch. The LFSR must already hold the patch seed.</summary>
    public static void GenericPatch(State st)
    {
        if (InHouse(st)) SetTileset(st, 0);
        for (int a = 0; a < W; a++)
            for (int b = 0; b < H; b++)
                SetTile(st, a, b, st.Rand16());
        PlaceRocks(st);
        PlacePits(st, st.Rand4() + 1);
        ResetHazards(st);                                 // f_0b66c → f_0ad9c
        for (int k = 0; k < 20; k++)
        {
            int a = st.Rand(0x7d) + 1;
            int b = st.Rand(0x3d) + 1;
            if (Tile(st, a, b) < 0x18 && Tile(st, a + 1, b) < 0x18 && Tile(st, a, b + 1) < 0x18 && Tile(st, a + 1, b + 1) < 0x18)
            {
                SetTile(st, a, b, 0x20);
                SetTile(st, a + 1, b, 0x21);
                SetTile(st, a, b + 1, 0x22);
                SetTile(st, a + 1, b + 1, 0x23);
            }
        }
        for (int k = 0; k < 30; k++)
        {
            int a = st.Rand(0x7d) + 1;
            int b = st.Rand(0x3d) + 1;
            if (Tile(st, a, b) < 0x18 && Tile(st, a + 1, b) < 0x18)
            {
                int t = (st.Rand(2) + 0x12) * 2;
                SetTile(st, a, b, t);
                SetTile(st, a + 1, b, t + 1);
            }
        }
        for (int k = 0; k < 100; k++)
        {
            int a = st.Rand(0x7d) + 1;
            int b = st.Rand(0x3d) + 1;
            if (Tile(st, a, b) < 0x18) SetTile(st, a, b, 0x28);
        }
        for (int k = 0; k < 128; k++)
        {
            int a = st.Rand(0x7d) + 1;
            int b = st.Rand(0x3d) + 1;
            if (Tile(st, a, b) < 0x18) SetTile(st, a, b, 0x51);
        }
    }

    // ------------------------------------------------------------------------------------------- the house
    /// <summary>f_73b17: a rectangle of one tile (inclusive bounds).</summary>
    static void Fill(State st, int a0, int a1, int b0, int b1, int t)
    {
        for (int a = a0; a <= a1; a++)
            for (int b = b0; b <= b1; b++)
                SetTile(st, a, b, t);
    }

    /// <summary>f_733e9: 1 cell in 200 gets 0x3E + Rand(2).</summary>
    static void Sprinkle(State st, int a0, int a1, int b0, int b1)
    {
        for (int a = a0; a <= a1; a++)
            for (int b = b0; b <= b1; b++)
                if (st.Rand(200) == 0) SetTile(st, a, b, st.Rand(2) + 0x3e);
    }

    /// <summary>f_73931 / f_739f4 / f_73a3a / f_73a83 / f_73acb: copy a wa x wb picture from DS:off, cell (i, j)
    /// at off + j * strideB + i.</summary>
    static void Blit(State st, int a, int b, int off, int wa, int wb, int strideB, bool skipZero = false)
    {
        for (int i = 0; i < wa; i++)
            for (int j = 0; j < wb; j++)
            {
                int v = st.U8(DS, off + j * strideB + i);
                if (v != 0 || !skipZero) SetTile(st, a + i, b + j, v);
            }
    }

    /// <summary>f_73777: a raised border (corners 0x53 0x55 0x50 0x52).</summary>
    static void FrameIn(State st, int a0, int a1, int b0, int b1)
    {
        Fill(st, a0, a1, b0, b0, 0x54);
        Fill(st, a0, a1, b1, b1, 0x51);
        Fill(st, a0, a0, b0, b1, 0x5a);
        Fill(st, a1, a1, b0, b1, 0x5b);
        SetTile(st, a0, b0, 0x53);
        SetTile(st, a1, b0, 0x55);
        SetTile(st, a0, b1, 0x50);
        SetTile(st, a1, b1, 0x52);
    }

    /// <summary>f_73817: a sunken border (corners 0x56 0x58 0x57 0x59).</summary>
    static void FrameOut(State st, int a0, int a1, int b0, int b1)
    {
        Fill(st, a0, a1, b0, b0, 0x51);
        Fill(st, a0, a1, b1, b1, 0x54);
        Fill(st, a0, a0, b0, b1, 0x5b);
        Fill(st, a1, a1, b0, b1, 0x5a);
        SetTile(st, a0, b0, 0x56);
        SetTile(st, a1, b0, 0x58);
        SetTile(st, a0, b1, 0x57);
        SetTile(st, a1, b1, 0x59);
    }

    /// <summary>f_7397a: a 13 x 9 box with two pictures (DS:2C6E) and a 0x65 mark.</summary>
    static void BoxWide(State st, int a, int b)
    {
        Fill(st, a, a + 12, b, b + 8, 99);
        FrameIn(st, a, a + 12, b, b + 8);
        Blit(st, a + 2, b + 2, 0x2c6e, 4, 5, 4);
        Blit(st, a + 7, b + 2, 0x2c6e, 4, 5, 4);
        SetTile(st, a + 6, b + 4, 0x65);
    }

    /// <summary>f_738b7: a 9 x 13 box with two pictures (DS:2C5A) and a 0x65 mark.</summary>
    static void BoxTall(State st, int a, int b)
    {
        Fill(st, a, a + 8, b, b + 12, 99);
        FrameIn(st, a, a + 8, b, b + 12);
        Blit(st, a + 2, b + 2, 0x2c5a, 5, 4, 5);
        Blit(st, a + 2, b + 7, 0x2c5a, 5, 4, 5);
        SetTile(st, a + 4, b + 6, 0x65);
    }

    /// <summary>f_73b54: a rectangle of t, 1 cell in 20 replaced by 0x38 + Rand(5), with 4 x 4 corners of 0xC0.</summary>
    static void Square(State st, int a0, int a1, int b0, int b1, int t)
    {
        Fill(st, a0, a1, b0, b1, t);
        for (int a = a0; a <= a1; a++)
            for (int b = b0; b <= b1; b++)
                if (st.Rand(0x14) == 0) SetTile(st, a, b, st.Rand(5) + 0x38);
        Fill(st, a0, a0 + 3, b0, b0 + 3, 0xc0);
        Fill(st, a1 - 3, a1, b0, b0 + 3, 0xc0);
        Fill(st, a0, a0 + 3, b1 - 3, b1, 0xc0);
        Fill(st, a1 - 3, a1, b1 - 3, b1, 0xc0);
    }

    /// <summary>f_73350 (room 1): a wall on the left (a 0..23), the floor beyond it, a box.</summary>
    static void WallLeft(State st)
    {
        Fill(st, 0, 0x14, 0, 0x3f, 0x64);
        Fill(st, 0x15, 0x15, 0, 0x3f, 0x7a);
        Fill(st, 0x16, 0x17, 0, 0x3f, 0x7b);
        Fill(st, 0x17, 0x7f, 0, 0x3f, 3);
        Sprinkle(st, 0x17, 0x7f, 0, 0x3f);
        BoxWide(st, 2, 0x19);
        SetRoom(st, 1);
    }

    /// <summary>f_7343d (room 3): the floor, then a wall on the right (a 104..127), a box.</summary>
    static void WallRight(State st)
    {
        Fill(st, 0, 0x69, 0, 0x3f, 3);
        Sprinkle(st, 0, 0x69, 0, 0x3f);
        Fill(st, 0x6a, 0x6a, 0, 0x3f, 0x7c);
        Fill(st, 0x68, 0x69, 0, 0x3f, 0x7b);
        Fill(st, 0x6a, 0x7f, 0, 0x3f, 0x64);
        BoxWide(st, 0x71, 0x23);
        SetRoom(st, 3);
    }

    /// <summary>f_734d3 (room 2): a counter along the top (b 0..23) with two boxes.</summary>
    static void Counter(State st)
    {
        Fill(st, 0, 0x7f, 0, 0x17, 0x62);
        Fill(st, 0, 0x7f, 0x18, 0x3f, 0);
        foreach (int b in new[] { 0, 8, 0x10 })
            for (int a = 0; a < 0x80; a++)
                SetTile(st, a, b, 0x68);
        for (int a = 0; a < 0x80; a += 8)
            for (int b = 0; b < 0x18; b++)
                SetTile(st, a, b, Tile(st, a, b) == 0x62 ? 0x66 : 0x67);
        for (int a = 0; a < 0x80; a++)
            SetTile(st, a, 0x17, Tile(st, a, 0x17) == 0x62 ? 0x68 : 0x69);
        BoxTall(st, 0x24, 2);
        BoxTall(st, 0x54, 2);
        SetRoom(st, 2);
    }

    /// <summary>f_735d5: the big fitting under the counter (patch 0).</summary>
    static void Stove(State st)
    {
        Fill(st, 0x25, 0x5b, 0x1a, 0x38, 1);
        Fill(st, 0x29, 0x44, 0x21, 0x35, 0xc2);
        Fill(st, 0x2a, 0x44, 0x23, 0x35, 0xc1);
        FrameOut(st, 0x28, 0x44, 0x20, 0x35);
        Fill(st, 0x49, 0x58, 0x21, 0x35, 0xc2);
        Fill(st, 0x4a, 0x58, 0x23, 0x35, 0xc1);
        FrameOut(st, 0x48, 0x58, 0x20, 0x35);
        FrameIn(st, 0x25, 0x5b, 0x1a, 0x38);
        Blit(st, 0x2c, 0x1b, 0x2c82, 5, 5, 5);
        Blit(st, 0x3c, 0x1b, 0x2c82, 5, 5, 5);
        SetTile(st, 0x3e, 0x1d, 0x4d);
        Blit(st, 0x34, 0x1b, 0x2c82, 5, 5, 5);
        Blit(st, 0x34, 0x24, 0x2c82, 5, 5, 5);
        Fill(st, 0x34, 0x38, 0x1d, 0x26, 0x4e);
        Fill(st, 0x34, 0x34, 0x1d, 0x26, 0x43);
        Fill(st, 0x38, 0x38, 0x1d, 0x26, 0x44);
        SetTile(st, 0x34, 0x28, 0x45);
        SetTile(st, 0x38, 0x28, 0x48);
        Fill(st, 0x36, 0x38, 0x29, 0x2a, 0xc2);
        Fill(st, 0x39, 0x3a, 0x23, 0x2a, 0xc2);
    }

    /// <summary>f_73236 (room 0): the checkered floor with grout lines.</summary>
    static void Tiles(State st)
    {
        for (int a = 0; a < 0x80; a++)
            for (int b = 0; b < 0x40; b++)
                SetTile(st, a, b, (((b >> 4) + (a >> 4)) & 1) != 0 ? 0 : 1);
        for (int b = 0; b < 0x40; b += 0x10)
            for (int a = 0; a < 0x80; a++)
                SetTile(st, a, b, ((a + b) & 0x10) != 0 ? 0x60 : 0x61);
        for (int a = 0; a < 0x80; a += 0x10)
            for (int b = 0; b < 0x40; b++)
            {
                if (Tile(st, a, b) < 2) SetTile(st, a, b, ((a + b) & 0x10) != 0 ? 0x5e : 0x5f);
                else SetTile(st, a, b, ((a + b) & 0x10) != 0 ? 0x5d : 0x5c);
            }
        SetRoom(st, 0);
    }

    /// <summary>f_73a83: a 3 x 3 picture (DS:2C9C).</summary>
    static void Picture(State st, int a, int b) => Blit(st, a, b, 0x2c9c, 3, 3, 3);

    /// <summary>f_73acb: a 3 x 3 picture (DS:2CA6) over what is there.</summary>
    static void PictureOver(State st, int a, int b) => Blit(st, a, b, 0x2ca6, 3, 3, 3, skipZero: true);

    /// <summary>f_7304b: the 38 hand-made patches of the house (yard rows 0..1 and row 2 up to col 5).</summary>
    public static void HousePatch(State st, int idx)
    {
        if (st.U16(G, 0xf24) != 1) SetTileset(st, 1);
        PlacePits(st, 0);
        ResetHazards(st);
        switch (idx)
        {
            case 0:
                Counter(st);
                Stove(st);
                break;
            case 1: case 16: case 32:
                Counter(st);
                break;
            case 2: case 3: case 17: case 18: case 19: case 33: case 34: case 35:
                Tiles(st);
                break;
            case 4: case 10: case 11: case 13: case 14:
                WallLeft(st);
                break;
            case 5:
                WallLeft(st);
                Fill(st, 0x18, 0x46, 0x14, 0x3f, 2);
                Picture(st, 0x28, 0x2d);
                break;
            case 6:
                WallLeft(st);
                Fill(st, 0x18, 0x46, 0, 0x3f, 2);
                Picture(st, 0x20, 0x14);
                PictureOver(st, 0x26, 0x37);
                break;
            case 7:
                WallLeft(st);
                Fill(st, 0x18, 0x46, 0, 0x14, 2);
                PictureOver(st, 0x2a, 0xa);
                break;
            case 8:
                WallLeft(st);
                Square(st, 0x18, 0x36, 0xf, 0x2d, 2);
                PictureOver(st, 0x1c, 0x22);
                break;
            case 9:
                Fill(st, 0, 0x7f, 0, 0x3f, 3);
                SetRoom(st, 2);
                break;
            case 12:
                WallLeft(st);
                Square(st, 0x2d, 0x5f, 8, 0x2e, 2);
                break;
            case 15:
                WallLeft(st);
                Square(st, 0x32, 0x64, 0xa, 0x2d, 2);
                Picture(st, 0x4b, 0x22);
                break;
            case 36: case 37:
                Fill(st, 0, 0x7f, 0, 0x3f, 0);
                SetRoom(st, 2);
                break;
            default:
                if (20 <= idx && idx <= 31) WallRight(st);
                break;
        }
    }
}
