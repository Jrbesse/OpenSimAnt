using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;
using Mv = OpenSimAnt.Sim.Movement;
using Ng = OpenSimAnt.Sim.NestGrid;

namespace OpenSimAnt.Sim;

/// <summary>The map tools (overlay 27, f_770f6): what a click on the map does with the tool G:104C, in the
/// view on screen G:032E (1 surface, 2 black nest, 3 red nest). Options per tool are the bytes T:07B7..T:07BC.
///   0 info (f_2f8fc, UI)      1 rocks f_7723f (surface)   2 dig f_7739f
///   3 ants f_77672            4 food f_77790              5 pheromone f_7783a (surface)
///   6 insecticide f_778bd
/// Alt (BIOS shift flags 0000:0417 bit 3, st.BiosKbd) takes food and pheromone away instead of adding.</summary>
public static class MapTools
{
    const int OCC = 0x6180;
    const int ALT = 8;

    /// <summary>T:07BB picks the map: black nest marker, black trail, red nest marker, red trail, alarm (64 x 32 each).</summary>
    static readonly (int seg, int off)[] PHER_MAPS = { (SIM, 0xe09f), (SIM, 0xe89f), (SIM, 0xf09f), (0x4da7, 0), (SIM, 0xd09f) };

    static int View(State st) => st.U16(G, 0x32e);

    static void Sound(State st, int n, int pitch = 0) => st.Hooks.Effect(st, "sound", n, pitch);

    /// <summary>f_770f6: the current tool at (a, b); rocks and dig start from the previous point (G:09FC, G:09FE).</summary>
    public static void ApplyTool(State st, int a, int b)
    {
        int tool = st.U16(G, 0x104c);
        int view = View(st);
        switch (tool)
        {
            case 0:
                if (Player.GetOcc(st, view, a, b) != 0) st.Hooks.Effect(st, "info", a, b, view);
                break;
            case 1:
                if (view == 1) Rocks(st, S16(st.U16(G, 0x9fc)), S16(st.U16(G, 0x9fe)), a, b);
                break;
            case 2: Dig(st, S16(st.U16(G, 0x9fc)), S16(st.U16(G, 0x9fe)), a, b); break;
            case 3: Ants(st, a, b); break;
            case 4: Food(st, a, b); break;
            case 5: Pheromone(st, a, b); break;
            case 6: Insecticide(st, a, b); break;
        }
    }

    // ------------------------------------------------------------------------------------------- ants
    /// <summary>f_77672: one worker (T:07B9 == 1: red), state 2; in the other colony's nest an invader (state 7).</summary>
    public static void Ants(State st, int a, int b)
    {
        int t = st.Rand(8) + 0x10;
        if (st.U8(T, 0x7b9) == 1) t += 0x80;
        int view = View(st);
        if (view == 1)
        {
            if (!Player.IsOpenGround(st, 1, a, b)) return;
            Player.AddSurfaceAntRaw(st, a, b, t, 2, 0);
        }
        else if (view == 2 || view == 3)
        {
            if (b == 0) return;
            var n = view == 2 ? Ng.BLACK : Ng.RED;
            if (st.Grid(n.Dirt, a, b) >= 0x1c) Ng.DigAt(st, n, a, b);
            bool own = (t > 0x80) == (view == 3);
            Ng.AddNestAnt(st, n, a, b, t, own ? 2 : 7, 0);
        }
        Sound(st, 0x1c);
    }

    // ------------------------------------------------------------------------------------------- food
    /// <summary>f_77ad6: grow the food crumb at (a, b) by one (a new one on bare ground), or with Alt take it
    /// back to ground. Adding counts it (G:1040 surface, G:1050 black nest, G:1060 red nest); taking only
    /// uncounts surface crumbs. 1 if done.</summary>
    public static int DropCrumb(State st, int a, int b)
    {
        int view = View(st);
        int @base = view == 1 ? 0x48 : 0x10;
        int t = Player.GetTile(st, view, a, b);
        if ((st.BiosKbd & ALT) != 0)
        {
            if (@base > t || @base + 3 < t) return 0;
            t = st.Rand(8);
            // only the surface counter: the nest counters' code (77b5c) is reached only with view 1 (dead)
            if (view == 1 && S16(st.U16(G, 0x1040)) > 0) st.Set16(G, 0x1040, st.U16(G, 0x1040) - 1);
        }
        else
        {
            if (@base + 2 < t) return 0;
            if (@base <= t) t++;
            else if (t < 0x18) t = @base;
            int off = view == 1 ? 0x1040 : view == 2 ? 0x1050 : 0x1060;
            st.Set16(G, off, st.U16(G, off) + 1);
        }
        Player.SetTile(st, view, a, b, t);
        return 1;
    }

    /// <summary>f_77790: one crumb (sound 0x1D), or with T:07BA set 20 at random within 4 cells (sound 0x20).</summary>
    public static void Food(State st, int a, int b)
    {
        if (st.U8(T, 0x7ba) == 0)
        {
            if (DropCrumb(st, a, b) != 0) Sound(st, 0x1d);
            return;
        }
        Sound(st, 0x20);
        int view = View(st);
        for (int k = 0; k < 0x14; k++)
        {
            int x = st.Rand(9) + a - 4;
            int y = st.Rand(9) + b - 4;
            if (Player.InView(view, x, y)) DropCrumb(st, x, y);
        }
    }

    // ------------------------------------------------------------------------------------------- pheromone
    /// <summary>f_77ff8.</summary>
    static bool PherOk(int a, int b) => 0 <= a && a <= 0x3f && 0 <= b && b <= 0x1f;

    /// <summary>f_78025: the selected map at (a, b), -1 off the map.</summary>
    public static int PherGet(State st, int a, int b)
    {
        if (!PherOk(a, b)) return -1;
        int k = st.U8(T, 0x7bb);
        if (k > 4) throw new NotImplementedException("f_78025: T:07BB > 4 returns an uninitialised local");
        var (seg, @base) = PHER_MAPS[k];
        return st.U8(seg, @base + a * 32 + b);
    }

    /// <summary>ToolDropPheromone f_780cd (capped at 255; a negative value is stored as its low byte).</summary>
    public static void PherSet(State st, int a, int b, int v)
    {
        if (!PherOk(a, b)) return;
        int k = st.U8(T, 0x7bb);
        if (k > 4) return;
        var (seg, @base) = PHER_MAPS[k];
        st.Set8(seg, @base + a * 32 + b, Math.Min(v, 0xff) & 0xff);
    }

    /// <summary>f_77f71: the cell becomes the mean of itself and the average of its four neighbours.</summary>
    static void Smooth(State st, int a, int b)
    {
        int s = PherGet(st, a, b - 1) + PherGet(st, a + 1, b) + PherGet(st, a, b + 1) + PherGet(st, a - 1, b);
        PherSet(st, a, b, CDiv(CDiv(s, 4) + PherGet(st, a, b), 2));
    }

    /// <summary>f_7783a (surface only): +0x46 to the selected map's cell (Alt: -0x28), smoothed with its neighbours.</summary>
    public static void Pheromone(State st, int a, int b)
    {
        if (View(st) != 1) return;
        int pa = a >> 1, pb = b >> 1;
        int v = PherGet(st, pa, pb) + ((st.BiosKbd & ALT) != 0 ? -0x28 : 0x46);
        PherSet(st, pa, pb, Math.Max(0, Math.Min(v, 0xff)));
        foreach (var (x, y) in new[] { (pa, pb), (pa, pb - 1), (pa + 1, pb), (pa, pb + 1), (pa - 1, pb), (pa, pb) })   // f_77f13
            Smooth(st, x, y);
        Sound(st, 0x1b);
    }

    // ------------------------------------------------------------------------------------------- insecticide
    /// <summary>f_0b58c: the ant-lion pit at (a, b), searching from the last; -1 if none.</summary>
    static int LionAt(State st, int a, int b)
    {
        for (int i = S16(st.U16(T, 0xc4a)) - 1; i >= 0; i--)
            if (st.U8(G, World.LA + i) == a && st.U8(G, World.LB + i) == b) return i;
        return -1;
    }

    /// <summary>f_778bd: 8 sprays, all on (a, b) when T:07BC is set, else each on a random cell within 4.
    /// Surface ants become corpses, the spider is beaten when hit in its cell, ant-lion pits are filled; nest
    /// ants vanish.</summary>
    public static void Insecticide(State st, int a, int b)
    {
        bool spread = st.U8(T, 0x7bc) == 0;
        int view = View(st);
        for (int k = 0; k < 8; k++)
        {
            int x, y;
            if (spread)
            {
                x = st.Rand(9) + a - 4;
                y = st.Rand(9) + b - 4;
                Sound(st, 9, st.Rand(1000) + 0x278f);
            }
            else
            {
                x = a;
                y = b;
                Sound(st, 9, 0);
            }
            if (!Player.InView(view, x, y)) continue;
            if (view == 1)
            {
                if (st.Grid(OCC, x, y) != 0)
                {
                    int i = Mv.SurfaceAntAt(st, x, y);
                    st.Set16(G, 0xf18, i & 0xffff);
                    if (i >= 0)
                    {
                        Surface.PlaceCorpse(st, x, y, (st.U8(SIM, 0xad3b + i) & 0x80) != 0);
                        st.Set8(SIM, 0xad3b + i, 0);
                        st.SetGrid(OCC, x, y, 0);
                    }
                }
                if (S16(st.U16(G, 0xf12)) >> 4 == x && S16(st.U16(G, 0xf34)) >> 4 == y) World.SpiderBeaten(st);
                int t = st.Grid(World.SURFACE, x, y);
                if (0x38 <= t && t <= 0x3e) World.RemoveLion(st, LionAt(st, x, y));
            }
            else if (view == 2 || view == 3)
            {
                var n = view == 2 ? Ng.BLACK : Ng.RED;
                int o = st.Grid(n.Cells, x, y);
                if (o == 0) continue;
                int i = Nest.NestAntAt(st, n, x, y, o);
                st.Set16(G, 0xf18, i & 0xffff);
                if (i >= 0)
                {
                    st.Set8(SIM, n.Type + i, 0);
                    st.SetGrid(n.Cells, x, y, 0);
                }
            }
        }
    }

    // ------------------------------------------------------------------------------------------- rocks
    /// <summary>f_77d54: wall tiles 0x60..0x67.</summary>
    static bool IsWall(int t) => 0x60 <= t && t <= 0x67;

    /// <summary>f_77cc4: which of the four neighbours are walls (left 8, below 4, right 2, above 1).</summary>
    static int WallMask(State st, int a, int b, int view)
    {
        int m = 0;
        foreach (var (x, y) in new[] { (a - 1, b), (a, b + 1), (a + 1, b), (a, b - 1) })
            m = (m << 1) | (IsWall(Player.GetTile(st, view, x, y)) ? 1 : 0);
        return m;
    }

    /// <summary>f_77c74: a wall tile takes the shape its neighbours call for (table DS:2DF4).</summary>
    static void FitWall(State st, int a, int b)
    {
        if (IsWall(st.Grid(World.SURFACE, a, b)))
            st.SetGrid(World.SURFACE, a, b, st.U8(0x55b3, 0x2df4 + WallMask(st, a, b, 1)));
    }

    /// <summary>f_77bec: the cell and its four neighbours.</summary>
    static void FitWalls(State st, int a, int b)
    {
        FitWall(st, a, b);
        foreach (var (x, y) in new[] { (a, b - 1), (a + 1, b), (a, b + 1), (a - 1, b) })
            if (Mv.InPatch(x, y)) FitWall(st, x, y);
    }

    /// <summary>f_7723f: from the previous point (x, y) to (ta, tb), one axis per step: walls (T:07B7 == 0,
    /// tile 0x60, sound 0x28) or pebbles (tiles 0x51..0x53) on free open ground; Alt clears them back to ground.</summary>
    public static void Rocks(State st, int x, int y, int ta, int tb)
    {
        while (Mv.InPatch(x, y))
        {
            int t = st.Grid(World.SURFACE, x, y);
            bool free = t < 0x50 && st.Grid(OCC, x, y) == 0;
            if ((st.BiosKbd & ALT) != 0)
            {
                if (0x50 < t && t < 0x68) st.SetGrid(World.SURFACE, x, y, st.Rand(0x10));
                FitWalls(st, x, y);
            }
            else if (st.U8(T, 0x7b7) == 0)
            {
                if (free) st.SetGrid(World.SURFACE, x, y, 0x60);
                FitWalls(st, x, y);
                Sound(st, 0x28);
            }
            else
            {
                if (free) st.SetGrid(World.SURFACE, x, y, st.Rand(3) + 0x51);
                Sound(st, 0xa, st.Rand(10000) + 0x7d0);
            }
            int d = Mv.DirTo(x, y, ta, tb);
            if (st.S8(T, 0x10 + d) != 0) x += st.S8(T, 0x10 + d);
            else y += st.S8(T, 0x1a + d);
            if (d == 0) return;
        }
    }

    // ------------------------------------------------------------------------------------------- dig
    /// <summary>f_775a2 (black) / f_7760a (red): every live nest ant on the cell is removed, newest first.</summary>
    static void ClearNestAnts(State st, NestKind n, int col, int depth)
    {
        for (int i = S16(st.U16(G, n.Count)) - 1; i >= 0; i--)
            if (st.U8(SIM, n.Type + i) != 0 && st.U8(SIM, n.X + i) == col && st.U8(SIM, n.Y + i) == depth)
                st.Set8(SIM, n.Type + i, 0);
        st.SetGrid(n.Cells, col, depth, 0);
    }

    /// <summary>f_77d75 (black) / f_77e44 (red): the cell back to dirt (0x2E), undoing the dig bookkeeping.</summary>
    static void FillCell(State st, NestKind n, int col, int depth)
    {
        st.SetGrid(n.Dirt, col, depth, 0x2e);
        st.SetGrid(n.Cells, col, depth, 0);
        if (S16(st.U16(G, n.Cap)) > 1)
        {
            foreach (var (off, v) in new[] { (n.SumCol, col), (n.SumDepth, depth) })
            {
                long s = (st.U32(G, off) - v) & 0xffffffffL;
                st.Set32(G, off, (s & 0x80000000L) != 0 ? 0 : s);
            }
            st.Set16(G, n.Cap, st.U16(G, n.Cap) - 1);
        }
        Ng.ReclassifyDirt(st, n, col, depth - 1);
        Ng.ReclassifyDirt(st, n, col + 1, depth);
        Ng.ReclassifyDirt(st, n, col, depth + 1);
        Ng.ReclassifyDirt(st, n, col - 1, depth);
        st.SetGrid(n.Exitf, col, depth, 0);
    }

    /// <summary>f_7739f: from the previous point (x, y) to (ta, tb), diagonally: dig (T:07B8 == 0; Alt flips it)
    /// a nest tunnel, or on the surface found a nest; or fill tunnels back in (on the surface: a message).</summary>
    public static void Dig(State st, int x, int y, int ta, int tb)
    {
        int fill = st.U8(T, 0x7b8);
        if ((st.BiosKbd & ALT) != 0) fill ^= 1;
        int view = View(st);
        while (true)
        {
            if (fill == 0)
            {
                if (view == 1)
                {
                    if (Player.TryFoundNest(st, x, y) != 0) Sound(st, 0x13);
                    else
                    {
                        Sound(st, 1);
                        st.Hooks.Effect(st, "status", "cannot dig here");          // f_15e2c
                    }
                }
                else if (view == 2 || view == 3)
                {
                    var n = view == 2 ? Nest.BLACK : Nest.RED;
                    if (Player.IsDirt(st, view, x, y) && y != 0)
                    {
                        Ng.DigAt(st, n, x, y);
                        if (y == 1) Nest.MakeSurfaceHole(st, n, x);
                        Sound(st, 0x13);
                    }
                }
            }
            else
            {
                if (view == 1)
                {
                    Sound(st, 1);
                    st.Hooks.Effect(st, "status", "cannot fill here");             // f_15e2c
                }
                else if (view == 2 || view == 3)
                {
                    var n = view == 2 ? Nest.BLACK : Nest.RED;
                    if (!Player.IsDirt(st, view, x, y) && y != 0)
                    {
                        if (st.Grid(n.Cells, x, y) != 0) ClearNestAnts(st, n, x, y);
                        FillCell(st, n, x, y);
                        Sound(st, 0x12);
                    }
                }
            }
            int d = Mv.DirTo(x, y, ta, tb);
            x += st.S8(T, 0x10 + d);
            y += st.S8(T, 0x1a + d);
            if (d == 0) return;
        }
    }
}
