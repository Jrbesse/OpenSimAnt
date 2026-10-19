using static Formica.Sim.Seg;
using static Formica.Sim.Bits;
using Co = Formica.Sim.Colony;
using Ng = Formica.Sim.NestGrid;

namespace Formica.Sim;

/// <summary>New game (f_6b36b, overlay 10) and patch setup (f_6ae20): a fresh yard, the starting patch and its
/// colonies, the yellow ant, and every counter the simulation keeps.
/// The game mode is G:0EAC (1 Quick Game, 2 Full Game, 3 the experimental mode). The starting patch is yard
/// patch (col 11, row 8): its seed is SIM:0000 + 2 * (G:07CC * 12 + G:07CA) (sic: rows of 12) and its terrain
/// comes from f_73020(G:07BC, G:07BE).</summary>
public static partial class NewGame
{
    public const int SURFACE = 0x0180, OCC = 0x6180;
    static readonly int[] PHER_MAPS = { 0xd89f, 0xd09f, 0xe09f, 0xe89f, 0xf09f };    // p2, alarm, black nest, black trail, red nest

    // ------------------------------------------------------------------------------------------- clearing
    /// <summary>f_6c010: surface and occupancy, both nests, the pheromone maps, every ant array, the yard colonies.</summary>
    public static void ClearWorld(State st)
    {
        for (int i = 0; i < 0x2000; i++)
        {
            st.Set8(SIM, SURFACE + i, 0);
            st.Set8(SIM, OCC + i, 0);
        }
        foreach (var n in new[] { Ng.BLACK, Ng.RED })
            for (int i = 0; i < 0x1000; i++)
            {
                st.Set8(SIM, n.Dirt + i, 0);
                st.Set8(SIM, n.Exitf + i, 0);
                st.Set8(SIM, n.Cells + i, 0);
            }
        ClearPheromones(st);
        for (int i = 0; i < 1000; i++)
            foreach (int @base in new[] { 0xad3b, 0xa952, 0xb124 })            // s_type, s_state, s_e
                st.Set8(SIM, @base + i, 0);
        for (int i = 0; i < 500; i++)
            foreach (var n in new[] { Ng.BLACK, Ng.RED })
            {
                st.Set8(SIM, n.Type + i, 0);
                st.Set8(SIM, n.State + i, 0);
                st.Set8(SIM, n.E + i, 0);
            }
        for (int i = 0; i < 12 * 16; i++)
        {
            st.Set8(T, 0xa4 + i, 0);
            st.Set8(T, 0x164 + i, 0);
        }
    }

    static void ClearPheromones(State st)
    {
        for (int i = 0; i < 0x800; i++)
        {
            foreach (int @base in PHER_MAPS) st.Set8(SIM, @base + i, 0);
            st.Set8(0x4da7, i, 0);
        }
    }

    static readonly int[] RecordArrays = { 0x516, 0x5a0, 0x626, 0x6ae, 0x73c, 0x7ce, 0x856, 0x8f0, 0x970, 0xa0a };

    /// <summary>f_79478 (via f_2f956): the history records; `full` (a new game) also resets the yard counters.</summary>
    public static void ResetRecords(State st, int full)
    {
        for (int i = 0; i < 0x40; i++)
            foreach (int off in RecordArrays) st.Set16(G, off + 2 * i, 0);
        if (full == 1)
        {
            st.Set32(G, 0xada, 0);
            st.Set16(G, 0xa90, 1);
            st.Set16(G, 0xac4, 1);
            st.Set16(G, 0xa9e, 0);
            st.Set16(G, 0xac8, 0);
        }
        st.Set16(G, 0x4f4, 0x3f);
        st.Set16(T, 0x828, 0);
        foreach (int off in new[] { 0xf20, 0xf30, 0xefc, 0xf80, 0xfbc, 0xf3e, 0xfc2, 0x1000 }) st.Set32(G, off, 0);
    }

    /// <summary>InitColonySettings (f_0888d): automatic behaviour, the default behaviour and caste mixes.</summary>
    public static void InitColonySettings(State st)
    {
        st.Hooks.Effect(st, "colony_panel");       // resource 0x578 → G:3832, slider geometry (f_07a57, f_07a19)
        st.Set16(G, 0x378, 1);
        st.Set16(T, 0x7e8, 1);
        st.Set16(G, 0x468, 1);
        st.Set16(T, 0x7ea, 1);
        st.Set16(G, 0x370, 0xffff);
        st.Set16(G, 0x24e, 0xffff);
        for (int i = 0; i < 3; i++)
        {
            int w = st.U16(T, 0x80a + 2 * i);
            st.Set16(G, 0x49e + 2 * i, w);
            st.Set16(T, 0x810 + 2 * i, w);
            int c = st.U16(T, 0x7ec + 2 * i);
            st.Set16(G, 0x482 + 2 * i, c);
            st.Set16(T, 0x7f2 + 2 * i, c);
        }
        CasteTargets(st);
    }

    /// <summary>f_085f8(T:07DA): the caste triangle as four percentages (rounded up from 16-bit fractions).</summary>
    public static void CasteTargets(State st)
    {
        static int Pct(long v, long k) => (int)((((k * v + 0x3fff) & 0xffffffffL) / 0xffff) & 0xffff);
        st.Set16(T, 0x7da, Pct(st.U16(G, 0x484), 100));
        st.Set16(T, 0x7dc, Pct(st.U16(G, 0x486), 100));
        st.Set16(T, 0x7de, Pct(st.U16(G, 0x482), 50));
        st.Set16(T, 0x7e0, Pct(st.U16(G, 0x482), 50));
    }

    static readonly (int seg, int off)[] YardZeroes =
    {
        (G, 0x10b0), (G, 0x246), (G, 0x23e), (T, 0xc32), (T, 0xc28), (T, 0xc40), (T, 0xc46),
        (T, 0xc48), (G, 0x10a0), (G, 0x22c), (G, 0x244), (G, 0x254), (G, 0x4e4), (G, 0x506),
        (T, 0xc3e), (T, 0xc42), (G, 0x3e0), (G, 0x46a), (G, 0x470), (G, 0x47a), (G, 0x202),
        (G, 0x352), (G, 0x105c), (G, 0x1066),
    };

    /// <summary>f_683a0 (via f_2f910): the yard layer's state (human, mower, bird, dog, rain, timers).</summary>
    public static void ResetYard(State st)
    {
        st.Set32(G, 0x109c, 0);
        st.Set16(T, 0xc2c, 0xb4);
        st.Set16(T, 0xc2e, 0x49);
        st.Set16(T, 0xc34, 0xc);
        st.Set16(T, 0xc2a, 0x14);
        st.Set32(G, 0x107e, 0);
        st.Set32(G, 0x220, 0);
        st.Set16(G, 0x4be, 0xfa);
        st.Set16(G, 0x4c6, 0x96);
        st.Set16(T, 0xc30, 2);
        st.Set16(G, 0x624, 2);
        foreach (var (seg, off) in YardZeroes) st.Set16(seg, off, 0);
        foreach (int off in new[] { 0x108c, 0x364, 0x36e }) st.Set16(G, off, 1);
        st.Set16(G, 0x10bc, 0xffff);
        st.Set16(G, 0x7c2, 0xffff);
    }

    /// <summary>f_0cdb0: per-patch globals (the spider's start, timers).</summary>
    public static void ResetPatchGlobals(State st)
    {
        st.Set16(G, 0x1076, 10);
        foreach (var (seg, off) in new[] { (G, 0x1054), (G, 0x105a), (G, 0x1042), (G, 0x1072), (G, 0x108a), (G, 0x1004), (T, 0xc12) })
            st.Set16(seg, off, 0);
        st.Set16(G, 0xf0c, st.U16(G, 0xeac) >= 1 ? 1 : 0);
        st.Set16(G, 0xf12, 0x400);
        st.Set16(G, 0xf34, 0x200);
        st.Set16(G, 0xfb8, 0);
        st.Set16(G, 0x6ac, 0);
        st.Set16(G, 0xffc, 0xfffe);
        st.Set16(G, 0x10ae, 0xffff);
        st.Set16(G, 0xf42, 0x40);
        st.Set16(G, 0xf7e, 0x40);
    }

    // ------------------------------------------------------------------------------------------- the patch
    /// <summary>Part of f_6ae20: n surface ants of one colony, at random spots (black left, red right).</summary>
    static void ScatterColony(State st, int n, bool red)
    {
        int tries = 0;
        int w = st.Rand(6) + 7;                       // workers below w (of 16), soldiers below s, then breeders
        int s = 15 - st.Rand2();
        while (n > 0)
        {
            n--;
            int r = st.RandLow(0x80);
            int a = red ? 0x7f - r : r;
            int b = st.Rand64();
            if (st.Grid(SURFACE, a, b) >= 0x50) continue;
            if (st.Grid(OCC, a, b) != 0)
            {
                tries++;
                if (tries < 0x32) n++;
                continue;
            }
            r = st.Rand16();
            int v;
            if (r < w) v = 0x10;                         // worker
            else if (s > r) v = 0x30;                    // soldier
            else if (st.Rand2() != 0) v = 0x20;          // male
            else v = 0x40;                               // new queen
            st.SetGrid(OCC, a, b, (v + st.Rand8() + (red ? 0x80 : 0)) & 0xff);
        }
    }

    /// <summary>f_6be50 (black) / f_6bf06 (red): up to n ants on the free open cells of the colony's half (black
    /// columns 0..63 up, red 127..64 down; rows 16..47), 3 in 10 soldiers (state 2), else workers (state 4);
    /// stops early at 1000 surface ants.</summary>
    public static void AddSurfaceAnts(State st, int n, bool red)
    {
        for (int k = 0; k < 0x40; k++)
        {
            int a = red ? 0x7f - k : k;
            for (int b = 0x10; b < 0x30; b++)
            {
                if (st.Grid(SURFACE, a, b) >= 0x50 || st.Grid(OCC, a, b) != 0) continue;
                int @base, state;
                if (st.Rand(10) <= 3) { @base = 0x30; state = 2; }
                else { @base = 0x10; state = 4; }
                int t = st.Rand8() + @base + (red ? 0x80 : 0);
                st.SetGrid(OCC, a, b, t & 0xff);
                Player.AddSurfaceAntRaw(st, a, b, t, state, 0);
                n--;
                if (n <= 0 || S16(st.U16(G, 0xd6a)) >= 1000) return;
            }
        }
    }

    /// <summary>f_6b95c (black) / f_6bae2 (red): a shaft from the entrance (nest column 32) down 7..10 rows,
    /// wandering sideways, then a short diagonal to the queen's chamber.</summary>
    static (int, int) StartNest(State st, NestKind n, Func<State, int, int> digRandom)
    {
        int depthN = st.Rand4() + 7;
        int col = 0x20, dcol = 0;
        int depth = 1;
        while (depthN > depth)
        {
            Ng.DigAt(st, n, col, depth);
            dcol = digRandom(st, dcol);
            int c = S16(dcol + col);
            if (8 <= c && c <= 0x38) col = c;
            depth++;
        }
        for (int k = 0; k < 2; k++)
        {
            Ng.DigAt(st, n, col, depth);
            col++;
            depth++;
        }
        Ng.DigAt(st, n, col, depth);
        return (col, depth);
    }

    static int BlackDrift(State st, int d) => st.Rand2() == 0 ? st.Rand(3) - 1 : d;

    static int RedDrift(State st, int d) => st.Rand(3) - 1;

    /// <summary>f_6ba1c (black) / f_6bb70 (red): dig the chamber and place the queen (two cells, 0x60/0x68 +
    /// heading, or 0xE0/0xE8 for red), state 9.</summary>
    public static void QueenChamber(State st, NestKind n, int col, int depth, int heading)
    {
        int h = heading ^ 4;
        int dx = st.S8(T, h), dy = st.S8(T, 8 + h);
        Ng.DigAt(st, n, col, depth);
        Ng.DigAt(st, n, col + dx, depth + dy);
        Ng.DigAt(st, n, col + 2 * dx, depth + 2 * dy);
        int red = n.Red;
        Ng.AddNestAnt(st, n, col, depth, heading + 0x60 + red, 9, 0);
        Ng.AddNestAnt(st, n, col + dx, depth + dy, heading + 0x68 + red, 9, 0);
        st.Inc16(G, red != 0 ? 0x36c : 0x35e);
    }

    /// <summary>f_6b616 (black) / f_6b6f3 (red): a bigger colony gets its tunnels dug by a random walk from the
    /// entrance (nest column 32), `steps` tries; reaching the top row again opens another entrance.</summary>
    public static void PreDig(State st, NestKind n, int steps)
    {
        Ng.DigAt(st, n, 0x20, 1);
        int d = 4, col = 0x20, depth = 1;
        while (steps != 0)
        {
            d = (st.Rand(5) + d - 3) & 7;
            int c = S16(st.S8(T, d) + col);
            int r = S16(st.S8(T, 8 + d) + depth);
            int nd;
            if (c < 1) { c = 1; d = 2; }
            else if (c > 0x3e) { c = 0x3e; d = 6; }
            if (r < 2) { r = 1; nd = 4; }
            else
            {
                nd = d;
                if (r > 0x3e) { r = 0x3e; nd = 0; }
            }
            if (Nest.DigCell(st, n, c, r))
            {
                col = c;
                depth = r;
                if (r == 1 && st.U8(T, n.Entr + c) == 0) Nest.MakeSurfaceHole(st, n, c);
            }
            steps = (steps - 1) & 0xffff;
            d = nd;
        }
    }

    /// <summary>f_6b95c.</summary>
    public static void StartBlackNest(State st)
    {
        var (col, depth) = StartNest(st, Nest.BLACK, BlackDrift);
        st.Set16(T, 0x2b4, col);
        st.Set16(T, 0x2b6, depth);
        st.Set16(G, 0xf0e, col);
        st.Set16(G, 0xf26, depth);
        QueenChamber(st, Nest.BLACK, col + 2, depth, 2);
    }

    /// <summary>f_6bae2.</summary>
    public static void StartRedNest(State st)
    {
        var (col, depth) = StartNest(st, Nest.RED, RedDrift);
        st.Set16(T, 0x2b8, col);
        st.Set16(T, 0x2ba, depth);
        QueenChamber(st, Nest.RED, col + 2, depth, 2);
    }

    /// <summary>f_0f329: the surface ant arrays from the occupancy grid (the yellow ant stays out); state 2.</summary>
    public static void BuildSurfaceAnts(State st)
    {
        st.Set16(G, 0xd6a, 0);
        for (int a = 0; a < 0x80; a++)
            for (int b = 0; b < 0x40; b++)
            {
                int v = st.Grid(OCC, a, b);
                if (v == 0 || v == 0xfe || v == 0xff) continue;               // IsYellowAnt f_10faa
                int i = st.U16(G, 0xd6a);
                st.Set8(SIM, 0xa180 + i, a);
                st.Set8(SIM, 0xa569 + i, b);
                st.Set8(SIM, 0xa952 + i, 2);
                st.Set8(SIM, 0xad3b + i, v);
                st.Set8(SIM, 0xb124 + i, 0);
                if (S16(i) < 0x3e5) st.Inc16(G, 0xd6a);
            }
    }

    /// <summary>f_6b7d0: the yellow ant. Quick Game: in the black nest beside the queen; Full Game: a new queen
    /// on the surface near the middle; mode 3: the player is the spider.</summary>
    public static void PlaceYellow(State st)
    {
        st.Set16(G, 0x49a, 0);
        st.Set16(T, 0xc22, 0xfd);
        if (st.U16(G, 0x104e) != 0)
        {
            st.Set16(G, 0x104e, 0);
            st.Set16(T, 0x7be, 0xffff);
        }
        Player.SetHealth(st, 100);
        int mode = st.U16(G, 0xeac);
        if (mode == 3)
        {
            st.Set16(G, 0x48c, 1);
            st.Set16(G, 0x4e2, 0);
            st.Set16(G, 0xa06, 2);
            st.Set16(G, 0x47c, 0x40);
            st.Set16(G, 0x48a, 0x20);
            st.Set16(G, 0x4c2, 0x10);
        }
        else
        {
            st.Set16(G, 0x4e2, 0);
            st.Set16(G, 0xa06, 0);
            if (mode == 2 && st.U16(T, 0xc24) == 0)
            {
                int a = 0x40, b = 0x20;
                for (int k = 0; k < 100; k++)
                {
                    int da = st.Rand16();
                    int a1 = S16(st.Rand16() - da + 0x20);
                    int db = st.Rand8();
                    int b1 = S16(st.Rand8() - db + 0x20);
                    if (st.Grid(SURFACE, a1, b1) < 0x10)
                    {
                        a = a1;
                        b = b1;
                        break;
                    }
                }
                Player.PutYellow(st, 1, a, b, 0x40, 2, 0xff);
            }
            else
                Player.PutYellow(st, 2, S16(st.U16(G, 0xf0e)), S16(st.U16(G, 0xf26)), 0x10, 2, 0xff);
        }
        SetView(st, st.U16(G, 0x48c), st.U16(G, 0x47c), st.U16(G, 0x48a));
    }

    /// <summary>f_757dd (via f_2f820): show the yellow ant's view; the cursor and its target start on it.</summary>
    public static void SetView(State st, int view, int a, int b)
    {
        st.Set16(G, 0x48c, view);
        st.Set16(G, 0xaf8, view);
        st.Set16(G, 0x47c, a);
        st.Set16(G, 0xab6, a);
        st.Set16(G, 0xad6, a);
        st.Set16(G, 0x48a, b);
        st.Set16(G, 0xac6, b);
        st.Set16(G, 0xae8, b);
        foreach (int off in new[] { 0xa8e, 0xaa0, 0xb1e, 0xc38, 0xc3e }) st.Set16(G, off, 0);
        st.Set16(G, 0xd6c, 0xfffe);
    }

    /// <summary>f_6ae20: generate the patch from its seed and scatter nBlack / nRed surface ants (+ a quarter);
    /// with colonies, dig their nests and place the queens, then the yellow ant and the first food.</summary>
    public static void SetupPatch(State st, int seed, int nBlack, int nRed, int row, int col)
    {
        st.Set16(DS, 0x8ba2, seed);                                         // SeedLfsr f_009bf
        ResetPatchGlobals(st);
        Terrain.SurfaceTerrain(st, row, col);                               // f_2f94c → f_73020
        nBlack += nBlack >> 2;
        nRed += nRed >> 2;
        foreach (var n in new[] { Ng.BLACK, Ng.RED })
            for (int i = 0; i < 0x1000; i++)
            {
                st.Set8(SIM, n.Dirt + i, 0x2e);
                st.Set8(SIM, n.Exitf + i, 0);
                st.Set8(SIM, n.Cells + i, 0);
            }
        for (int i = 0; i < 0x2000; i++) st.Set8(SIM, OCC + i, 0);
        for (int c = 0; c < 0x40; c++)                    // the top soil row
        {
            if (st.U16(G, 0xf24) == 0)
            {
                st.SetGrid(Ng.BLACK.Dirt, c, 0, st.Rand4() + 0x1c);
                st.SetGrid(Ng.RED.Dirt, c, 0, st.Rand4() + 0x1c);
            }
            else
            {
                st.SetGrid(Ng.BLACK.Dirt, c, 0, S16(col) > 3 ? st.Rand(2) + 0x1c : 0x1e);
                st.SetGrid(Ng.RED.Dirt, c, 0, S16(col) > 3 ? st.Rand(2) + 0x1c : 0x1e);
            }
            st.SetGrid(Ng.BLACK.Exitf, c, 0, 0xff);
            st.SetGrid(Ng.RED.Exitf, c, 0, 0xff);
        }
        ClearPheromones(st);
        ScatterColony(st, nBlack, false);
        ScatterColony(st, nRed, true);
        for (int c = 0; c < 0x40; c++)
        {
            st.Set8(T, 0x224 + c, 0);
            st.Set8(T, 0x264 + c, 0);
        }
        if (st.U16(G, 0xeac) != 2 || nBlack >= 1) Nest.MakeSurfaceHole(st, Nest.BLACK, 0x20);
        if (nRed >= 1) Nest.MakeSurfaceHole(st, Nest.RED, 0x20);
        foreach (int off in new[] { 0x10a2, 0x108e, 0x1082, 0x1068 }) st.Set32(G, off, 0);
        foreach (int off in new[] { 0x224, 0x232, 0x20e, 0x200, 0x10c0, 0x10b2 }) st.Set16(G, off, 0);
        st.Set16(G, 0x242, 0x40);
        if (nBlack > 1) PreDig(st, Nest.BLACK, nBlack << 4);               // f_6b616
        if (nRed > 1) PreDig(st, Nest.RED, nRed << 4);                     // f_6b6f3
        BuildSurfaceAnts(st);
        st.Set16(G, 0xda8, 0);                                              // f_0f3d1
        st.Set16(G, 0xeaa, 0);                                              // f_0f3e4
        st.Set16(G, 0x35e, 0);
        st.Set16(G, 0x36c, 0);
        st.Set32(T, 0x2b4, 0xffffffffL);
        st.Set32(T, 0x2b8, 0xffffffffL);
        if (nRed > 0) StartRedNest(st);
        if (nBlack > 0) StartBlackNest(st);
        PlaceYellow(st);
        st.Set16(G, 0x1050, 0);
        st.Set16(G, 0x1060, 0);
        st.Set16(G, 0x1040, 0);
        if (st.U16(G, 0xeac) != 3) Co.DropFood(st, -1, 0);
        st.Set16(G, 0x10be, 100);
        st.Set16(G, 0x1fe, 100);
        st.Set32(G, 0x472, 0);
        foreach (int off in new[] { 0x9fa, 0xa00, 0xf08 }) st.Set16(G, off, 0);
        ResetRecords(st, 0);
        Co.Census(st, m => st.Hooks.Effect(st, "message", m));
        st.Hooks.Effect(st, "redraw_rect", 0, 0, st.U16(G, 0xfb6), st.U16(G, 0xffa));     // f_0256e
        st.Set16(G, 0x508, 0x40);
        st.Set16(G, 0x596, 0x40);
        st.Set16(G, 0x50a, 0x20);
        st.Set16(G, 0x598, 0x20);
        st.Set16(G, 0x6a6, 0x20);
        st.Set16(G, 0x72e, 0x20);
        st.Set16(G, 0x6a8, 1);
        st.Set16(G, 0x730, 1);
    }

    // ------------------------------------------------------------------------------------------- moving
    /// <summary>f_01d48 (Full Game): go to the yard patch the player picked (row G:07BC, col G:07BE, set by the
    /// yard map). It must hold a black colony, unless the yellow ant is a new queen that has not settled yet
    /// (T:0C24 == 0). The patch is generated afresh with the yard's colony sizes.</summary>
    public static void MoveToPatch(State st)
    {
        int row = S16(st.U16(G, 0x7bc)), col = S16(st.U16(G, 0x7be));
        if (row == S16(st.U16(G, 0x7ca)) && S16(st.U16(G, 0x7cc)) == col) return;
        int refuse = 0;
        int idx = 0;
        if (st.U16(G, 0xeac) != 2) refuse = 0x2710;                         // only in a Full Game
        else if (S16(st.U16(G, 0x3e2)) <= 1 && S16(st.U16(G, 0x330)) <= 1) refuse = 0x2712;   // the colony is too small to move
        else
        {
            idx = (row * 16 + col) & 0xffff;
            if (st.U8(T, 0xa4 + idx) < 1 && !(st.U16(G, 0x4c2) == 0x40 && st.U16(T, 0xc24) == 0))
                refuse = 0x2714;                                            // no black colony there
        }
        if (refuse != 0)
        {
            st.Hooks.Effect(st, "sound", 1);                                // f_00ed8(1, 0, 0x7e)
            st.Hooks.Effect(st, "message_box", refuse, 1);                  // f_2f6ea → f_71b1a(0, id, 1)
            return;
        }
        st.Hooks.Effect(st, "voice", 0x2afa);                               // f_00ea1(0x2afa, 0x7e)
        st.Set16(G, 0x7ca, row);
        st.Set16(G, 0x7cc, col);
        st.Hooks.Effect(st, "yard_map");                                    // f_2f6e0 → f_6f46a
        st.Set16(G, 0x354, 1);
        foreach (int off in new[] { 0x7c8, 0x850, 0x6aa, 0x73a }) st.Set16(G, off, 0);
        st.Set16(T, 0xc24, 1);
        int black = st.U8(T, 0xa4 + idx), red = st.U8(T, 0x164 + idx);
        SetupPatch(st, st.U16(SIM, (2 * (col * 12 + row)) & 0xffff), black, red, row, col);
        if (st.U8(T, 0x164 + idx) == 0) st.Set16(G, 0x1fe, 0);
        st.Hooks.Effect(st, "message_box", S16(idx) > 0x24 ? 0x2716 : 0x2717, 0);
    }

    // ------------------------------------------------------------------------------------------- new game
    /// <summary>f_6b36b: start a game in mode G:0EAC (the caller sets it).</summary>
    public static void NewGameStart(State st)
    {
        ClearWorld(st);
        ResetRecords(st, 1);
        InitColonySettings(st);
        st.Set16(G, 0x7ca, 0xb);
        st.Set16(G, 0x7bc, 0xb);
        st.Set16(G, 0x7cc, 8);
        st.Set16(G, 0x7be, 8);
        ResetYard(st);
        st.Set16(G, 0x105e, 0xffff);
        st.Set32(G, 0x214, 0);
        st.Set32(G, 0x204, 0);
        foreach (var (seg, off) in new[] { (G, 0x228), (G, 0x478), (G, 0x504), (G, 0x366), (G, 0x376), (T, 0xc44), (T, 0xc18), (T, 0xc16), (T, 0xc14) })
            st.Set16(seg, off, 0);
        st.Set32(G, 0xc26, 0);
        int mode = S16(st.U16(G, 0xeac));
        st.Set16(G, 0x32e, mode > 1 ? 1 : 2);
        st.Set16(T, 0x7c8, st.U16(G, 0x32e));
        st.Set16(G, 0x35c, 0);
        for (int i = 0; i < 0xc0; i++)                    // the yard's patch seeds
            st.Set16(SIM, 2 * i, (st.CrtRandMod(0x7fff) - 0xc000) & 0x7fff);
        bool full = st.U16(G, 0xeac) == 2;
        st.Set16(T, 0xc24, full ? 0 : 1);
        int idx = S16(st.U16(G, 0x7cc)) * 12 + S16(st.U16(G, 0x7ca));
        SetupPatch(st, st.U16(SIM, (2 * idx) & 0xffff), full ? 0 : 1, 1, S16(st.U16(G, 0x7bc)), S16(st.U16(G, 0x7be)));
        int view = S16(st.U16(G, 0x48c));
        int a = st.U16(G, 0x47c), b = st.U16(G, 0x48a);
        if (view < 2)
        {
            st.Set16(G, 0x596, a);
            st.Set16(G, 0x598, b);
        }
        else if (view == 2)
        {
            st.Set16(G, 0x6a6, a);
            st.Set16(G, 0x6a8, b);
        }
        else
        {
            st.Set16(G, 0x72e, a);
            st.Set16(G, 0x730, b);
        }
    }
}
