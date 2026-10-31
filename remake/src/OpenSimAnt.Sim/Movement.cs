using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;
using Ph = OpenSimAnt.Sim.Pheromones;

namespace OpenSimAnt.Sim;

/// <summary>Surface movement and steering helpers (SIMANT.EXE segments 0ad9, 0be8, 1383, 10f7).</summary>
public static class Movement
{
    public const int SURFACE = 0x0180, OCC = 0x6180;

    public static int Dx(State st, int d) => st.S8(T, d);

    public static int Dy(State st, int d) => st.S8(T, 8 + d);

    /// <summary>T_WALK[d][i] (T:0024).</summary>
    public static int Walk(State st, int d, int i) => st.U8(T, 0x24 + d * 8 + i);

    /// <summary>f_137d7.</summary>
    public static bool InPatch(int a, int b) => 0 <= a && a <= 0x7f && 0 <= b && b <= 0x3f;

    /// <summary>f_0acfb: standing on a nest entrance tile.</summary>
    public static bool AtNestEntrance(State st, int a, int b)
    {
        if (!InPatch(a, b)) return false;
        int t = st.Grid(SURFACE, a, b);
        if (st.U16(G, 0xf24) == 0) return t == 0x50;
        return 0x80 <= t && t <= 0x8f;
    }

    /// <summary>f_0ad63 (TileClass): 1 for food crumbs.</summary>
    public static bool IsFood(State st, int t)
    {
        if (st.U16(G, 0xf24) == 0) return 0x48 <= t && t <= 0x4b;
        return 0x18 <= t && t <= 0x27;
    }

    /// <summary>f_10faa.</summary>
    public static bool IsYellow(int o) => o == 0xfe || o == 0xff;

    /// <summary>f_148d8: at the patch border, 1 + a random inward heading; 0 elsewhere.</summary>
    public static int EdgeDir(int a, int b, State st)
    {
        if (a == 0)
        {
            if (b == 0) return st.Rand(3) + 3;
            if (b == 0x3f) return st.Rand(3) + 1;
            return st.Rand(5) + 1;
        }
        if (b == 0)
        {
            if (a == 0x7f) return st.Rand(3) + 5;
            return st.Rand(5) + 3;
        }
        if (a == 0x7f)
        {
            if (b == 0x3f) return st.Rand(3) + 7;
            return st.Rand(5) + 5;
        }
        if (b == 0x3f) return st.Rand(5) + 7;
        return 0;
    }

    /// <summary>f_146b9.</summary>
    public static int NextDir(State st, int a, int b, int d)
    {
        int e = EdgeDir(a, b, st);
        if (e != 0) return (e - 1) & 7;
        return Walk(st, d, st.Rand8());
    }

    /// <summary>f_0ab05.</summary>
    public static int TurnAside(State st, int d) => Walk(st, d, st.Rand8());

    /// <summary>f_0c9a1: 0 if same cell, else 1 + 8-way heading towards the target.</summary>
    public static int DirTo(int a, int b, int ta, int tb)
    {
        int ddb = tb - b;
        int dda = ta - a;
        if (dda == 0)
        {
            if (ddb == 0) return 0;
            return ddb < 0 ? 1 : 5;
        }
        if (dda > 0)
        {
            if (ddb < 0) return 2;
            return ddb == 0 ? 3 : 4;
        }
        if (ddb > 0) return 6;
        return ddb == 0 ? 7 : 8;
    }

    /// <summary>f_0ca03, low word as the callers use it (signed).</summary>
    public static int DistanceLo(int a1, int b1, int a2, int b2) => S16((b2 - b1) * (b2 - b1) + (a2 - a1) * (a2 - a1));

    static (int best, int bestd) BestNeighbour(State st, PherMap m, int ca, int cb, int startBest = 0, int startDir = 0)
    {
        int best = startBest, bestd = startDir;
        for (int d = 0; d < 8; d++)
        {
            int v = Ph.Get(st, m, ((ca + Dx(st, d)) & 0x3f) * 32 + ((cb + Dy(st, d)) & 0x1f));
            if (v > best) { best = v; bestd = d; }
        }
        return (best, bestd);
    }

    /// <summary>f_142c5: climb the colony's food trail; -1 when on a local maximum ("lost").</summary>
    public static int ForageDir(State st, int a, int b, int d, int t)
    {
        if (a == 0)
        {
            if (b == 0) return 3;
            if (b == 0x3f) return 1;
            return st.Rand(3) + 1;
        }
        if (b == 0)
        {
            if (a == 0x7f) return 5;
            return st.Rand(3) + 3;
        }
        if (a == 0x7f)
        {
            if (b == 0x3f) return 7;
            return st.Rand(3) + 5;
        }
        if (b == 0x3f) return (st.Rand(3) - 1) & 7;
        int ca = a >> 1, cb = b >> 1;
        var m = (t & 0x80) != 0 ? Ph.RED_TRAIL : Ph.BLACK_TRAIL;
        int here = Ph.Get(st, m, ca * 32 + cb);
        int start = st.Rand8();
        var (best, bestd) = BestNeighbour(st, m, ca, cb, 0, start);
        if (best > 0)
        {
            if (here > best) return -1;
            return Walk(st, d, bestd);
        }
        return Walk(st, d, st.Rand8());
    }

    /// <summary>f_1445a: back to the colony's nest (nest-marker gradient, else straight at the entrance).</summary>
    public static int HomeDir(State st, int a, int b, int d, int t)
    {
        int ca = a >> 1, cb = b >> 1;
        int red = (t >> 7) & 1;
        int e = EdgeDir(a, b, st);
        if (e != 0) return (e - 1) & 7;
        var m = red != 0 ? Ph.RED_NEST : Ph.BLACK_NEST;
        if (Ph.Get(st, m, ca * 32 + cb) != 0)
        {
            var (_, bestd) = BestNeighbour(st, m, ca, cb);
            int r = st.Rand2() != 0 ? Walk(st, d, bestd) : d;
            return Walk(st, r, bestd);
        }
        if (red != 0)
        {
            int dd = DirTo(a, b, S16(st.U16(T, 0x2b0)), S16(st.U16(T, 0x2b2)));
            if (dd != 0 && st.Rand4() != 0) return Walk(st, d, dd - 1);
        }
        else
        {
            int dd = DirTo(a, b, S16(st.U16(T, 0x2ac)), S16(st.U16(T, 0x2ae)));
            if (dd != 0 && st.Rand4() != 0) return Walk(st, d, dd - 1);
        }
        return Walk(st, d, st.Rand8());
    }

    /// <summary>f_145fc: climb the alarm gradient.</summary>
    public static int AlarmDir(State st, int a, int b, int d)
    {
        int ca = a >> 1, cb = b >> 1;
        int e = EdgeDir(a, b, st);
        if (e != 0) return (e - 1) & 7;
        var (best, bestd) = BestNeighbour(st, Ph.ALARM, ca, cb);
        if (best != 0) return Walk(st, d, bestd);
        return Walk(st, d, st.Rand8());
    }

    /// <summary>f_146fc: black recruits / guards (mode G:048c).</summary>
    public static int BlackGuardDir(State st, int a, int b, int d)
    {
        int si = EdgeDir(a, b, st);
        if (si != 0) return (si - 1) & 7;
        int mode = st.U16(G, 0x48c);
        if (mode == 1)
        {
            if (st.U16(G, 0x248) == 1)
                si = DirTo(a, b, S16(st.U16(G, 0xf12)) >> 4, S16(st.U16(G, 0xf34)) >> 4);
            else
            {
                int dist = DistanceLo(a, b, S16(st.U16(G, 0x22a)), S16(st.U16(G, 0x238)));
                if ((S16(st.U16(G, 0xb1c)) >> 1) < dist)
                    si = DirTo(a, b, S16(st.U16(G, 0x22a)), S16(st.U16(G, 0x238)));
                else
                    si = st.Rand(8) + 1;
            }
        }
        else if (mode == 2) return HomeDir(st, a, b, d, 0);
        else if (mode == 3) return HomeDir(st, a, b, d, 0x80);
        if (si == 0) return d;
        return Walk(st, d, si - 1);
    }

    /// <summary>f_147fe: red guards (mode G:0498; guard point G:0490/0494; radius red defenders G:0c34 / 2).</summary>
    public static int RedGuardDir(State st, int a, int b, int d)
    {
        int si = EdgeDir(a, b, st);
        if (si != 0) return (si - 1) & 7;
        int mode = st.U16(G, 0x498);
        if (mode == 1)
        {
            int dist = DistanceLo(a, b, S16(st.U16(G, 0x490)), S16(st.U16(G, 0x494)));
            if ((S16(st.U16(G, 0xc34)) >> 1) < dist)
                si = DirTo(a, b, S16(st.U16(G, 0x490)), S16(st.U16(G, 0x494)));
            else
                si = st.Rand(8) + 1;
        }
        else if (mode == 2) return HomeDir(st, a, b, d, 0);
        else if (mode == 3) return HomeDir(st, a, b, d, 0x80);
        if (si == 0) return d;
        return Walk(st, d, si - 1);
    }

    /// <summary>f_0c618: take one unit from a food crumb.</summary>
    public static void TakeFoodAt(State st, int a, int b)
    {
        int t = st.Grid(SURFACE, a, b);
        if (st.U16(G, 0xf24) == 0)
        {
            if (t == 0x48) st.SetGrid(SURFACE, a, b, st.Rand16());
            else st.SetGrid(SURFACE, a, b, t - 1);
        }
        else
        {
            if (t % 4 == 0) st.SetGrid(SURFACE, a, b, (t - 0x18) >> 2);
            else st.SetGrid(SURFACE, a, b, t - 1);
        }
        if (S16(st.U16(G, 0x1040)) > 0) st.Set16(G, 0x1040, st.U16(G, 0x1040) - 1);
    }

    /// <summary>f_0eea1: index of the live surface ant at (a, b), searching from the top; -1 if none.</summary>
    public static int SurfaceAntAt(State st, int a, int b)
    {
        int i = S16(st.U16(G, 0xd6a));
        while (i > 0)
        {
            i--;
            if (st.U8(SIM, 0xa180 + i) == a && st.U8(SIM, 0xa569 + i) == b && st.U8(SIM, 0xad3b + i) != 0) return i;
        }
        return -1;
    }

    /// <summary>f_141a6 -> f_141cb (black) / f_14260 (red): the next job for an ant of this caste.</summary>
    public static int StateForCaste(State st, int caste, int t)
    {
        if ((t & 0x80) != 0)
        {
            if (caste == 2) return st.U8(T, 0xb9e + st.U16(G, 0x10a6) * 8 + st.Rand8());
            if (caste == 6) return st.U8(T, 0xbce + st.U16(G, 0x10a6) * 8 + st.Rand8());
            return st.U8(T, 0xbfe + caste);
        }
        if (st.U16(G, 0x378) == 1)
        {
            if (caste == 2) return st.U8(T, 0xb9e + st.U16(G, 0x1094) * 8 + st.Rand8());
            if (caste == 6) return st.U8(T, 0xbce + st.U16(G, 0x1094) * 8 + st.Rand8());
            return st.U8(T, 0xbfe + caste);
        }
        if (caste == 2 || caste == 6) return st.U16(T, 0xc10) & 0xff;
        return st.U8(T, 0xbfe + caste);
    }
}
