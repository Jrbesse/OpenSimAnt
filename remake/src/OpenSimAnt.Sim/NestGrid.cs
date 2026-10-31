using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;

namespace OpenSimAnt.Sim;

/// <summary>The memory layout of one nest (black or red): grids in SIM, ant arrays, counters in G.</summary>
public sealed class NestKind
{
    public string Name;
    public int Dirt, Exitf, Cells, X, Y, State, Type, E, Count, Cap, SumCol, SumDepth, CenCol, CenDepth;
    // colony constants for the helpers shared by both nests (nest.BLACK / nest.RED in the reference)
    public int View, Red, Health, Food, Acc, Pop, Soldiers, Entr, EntrXy, EntrCol;
    public Func<int, int, int> HoleRow;
    public override string ToString() => Name;
}

/// <summary>Nest grid helpers shared by surface and nest code: digging, dirt edges, exit fields, nest ant lists.
/// Black nest: dirt 0x2180, exit field 0x4180, cells 0x8180, ants b_* (count G:0da8).
/// Red nest:   dirt 0x3180, exit field 0x5180, cells 0x9180, ants r_* (count G:0eaa).</summary>
public static class NestGrid
{
    public static readonly NestKind BLACK = new()
    {
        Name = "BLACK", Dirt = 0x2180, Exitf = 0x4180, Cells = 0x8180, X = 0xb50d, Y = 0xb702, State = 0xb8f7,
        Type = 0xbaec, E = 0xbce1, Count = 0xda8, Cap = 0x224, SumCol = 0x1068, SumDepth = 0x1082, CenCol = 0x10b2,
        CenDepth = 0x10c0,
        View = 2, Red = 0, Health = 0x10be, Food = 0x1050, Acc = 0x212, Pop = 0x330, Soldiers = 0xaf0, Entr = 0x224,
        EntrXy = 0x2ac, EntrCol = 0x2a4, HoleRow = (k, i) => (k + i) % 0x20 + 2,
    };

    public static readonly NestKind RED = new()
    {
        Name = "RED", Dirt = 0x3180, Exitf = 0x5180, Cells = 0x9180, X = 0xbed6, Y = 0xc0cb, State = 0xc2c0,
        Type = 0xc4b5, E = 0xc6aa, Count = 0xeaa, Cap = 0x232, SumCol = 0x108e, SumDepth = 0x10a2, CenCol = 0x200,
        CenDepth = 0x20e,
        View = 3, Red = 0x80, Health = 0x1fe, Food = 0x1060, Acc = 0x226, Pop = 0x350, Soldiers = 0xafe, Entr = 0x264,
        EntrXy = 0x2b0, EntrCol = 0x2a8, HoleRow = (k, i) => 0x7e - (k + i) % 0x20,
    };

    /// <summary>f_0ca6e.</summary>
    public static bool IsDiggable(int t) => 0x20 <= t && t <= 0x2e;

    /// <summary>f_15a13.</summary>
    public static bool IsDirtForEdge(int t) => !(t < 0x20 || (0x2f < t && t < 0x4f));

    /// <summary>f_158d1 (black) / f_15a3a (red): recompute a dirt cell's edge tile from its dirt neighbours.</summary>
    public static void ReclassifyDirt(State st, NestKind n, int col, int depth)
    {
        if (!(0 <= col && col < 0x40 && depth < 0x40)) return;
        int @base = n.Dirt;
        if (depth == 0)
        {
            if (st.Grid(@base, col, 0) < 0x30) st.SetGrid(@base, col, 0, 0x18);
            return;
        }
        int t = st.Grid(@base, col, depth);
        if (!(t > 0x1f && (t < 0x30 || t > 0x4e))) return;
        int alt = t >= 0x4e ? 0x2f : 0;
        int m = 0;
        if (depth < 2 || IsDirtForEdge(st.Grid(@base, col, depth - 1))) m = 1;
        if (col > 0x3e || IsDirtForEdge(st.Grid(@base, col + 1, depth))) m |= 2;
        if (depth > 0x3e || IsDirtForEdge(st.Grid(@base, col, depth + 1))) m |= 4;
        if (col < 1 || IsDirtForEdge(st.Grid(@base, col - 1, depth))) m |= 8;
        if (m == 0)
        {
            if (alt != 0)
            {
                st.SetGrid(@base, col, depth, 0x4e);
                return;
            }
            st.SetGrid(@base, col, depth, st.Rand8());
        }
        else
            st.SetGrid(@base, col, depth, m + alt + 0x1f);
    }

    /// <summary>f_15b7c (black) / f_15c51 (red).</summary>
    public static void UpdateExitField(State st, NestKind n, int col, int depth)
    {
        if (depth < 2)
        {
            st.SetGrid(n.Exitf, col, depth, st.Grid(n.Dirt, col, depth) == 0x18 ? 0xff : 0xfe);
            return;
        }
        int best = 0;
        for (int d = 0; d < 8; d++)
        {
            int c = col + st.S8(T, d), r = depth + st.S8(T, 8 + d);
            if (0 <= c && c < 0x40 && 0 <= r && r < 0x40)
            {
                int v = st.Grid(n.Exitf, c, r);
                if (v > best) best = v;
            }
        }
        st.SetGrid(n.Exitf, col, depth, best != 0 ? best - 1 : 0);
    }

    static int SDiv(long a, int b)
    {
        a = (a & 0x80000000L) != 0 ? a - (1L << 32) : a;
        long q = Math.Abs(a) / Math.Abs(b);
        return (int)((a >= 0) == (b >= 0) ? q : -q);
    }

    internal static void DigBookkeeping(State st, NestKind n, int col, int depth)
    {
        st.Set32(G, n.SumCol, (st.U32(G, n.SumCol) + col) & 0xffffffffL);
        st.Set32(G, n.SumDepth, (st.U32(G, n.SumDepth) + depth) & 0xffffffffL);
        st.Inc16(G, n.Cap);
        int cap = S16(st.U16(G, n.Cap));
        if (cap > 0)
        {
            st.Set16(G, n.CenCol, SDiv(st.U32(G, n.SumCol), cap));
            st.Set16(G, n.CenDepth, SDiv(st.U32(G, n.SumDepth), cap));
        }
    }

    /// <summary>f_153f9 (black) / f_15527 (red): dig a cell if diggable (no structural checks); used under
    /// entrances. Deep black digging can break into the red nest.</summary>
    public static void DigAt(State st, NestKind n, int col, int depth)
    {
        if (IsDiggable(st.Grid(n.Dirt, col, depth)))
        {
            st.SetGrid(n.Dirt, col, depth, st.Rand8());
            DigBookkeeping(st, n, col, depth);
            if (n.Dirt == BLACK.Dirt && depth > 0x35 && st.Rand(0x40) == 0)   // (callers pass copies)
            {
                st.SetGrid(BLACK.Dirt, col, depth, 0x14);
                DigAt(st, RED, col, depth);
                st.SetGrid(RED.Dirt, col, depth, 0x14);
            }
        }
        ReclassifyDirt(st, n, col, depth - 1);
        ReclassifyDirt(st, n, col + 1, depth);
        ReclassifyDirt(st, n, col, depth + 1);
        ReclassifyDirt(st, n, col - 1, depth);
        UpdateExitField(st, n, col, depth);
    }

    /// <summary>f_0f1e4 (black) / f_0f261 (red).</summary>
    public static void AddNestAnt(State st, NestKind n, int col, int depth, int t, int state, int e)
    {
        int i = S16(st.U16(G, n.Count));
        if (i >= 500) return;
        st.Set8(SIM, n.X + i, col);
        st.Set8(SIM, n.Y + i, depth);
        st.Set8(SIM, n.State + i, state);
        st.Set8(SIM, n.Type + i, t);
        st.Set8(SIM, n.E + i, e);
        st.SetGrid(n.Cells, col, depth, t);
        st.Inc16(G, n.Count);
    }

    /// <summary>f_0ec12 (surface) / f_0ec91 (black nest) / f_0ed10 (red nest): squeeze out empty slots.</summary>
    public static void Compact(State st, int typeBase, int[] fields, int countOff)
    {
        int shift = 0;
        int n = S16(st.U16(G, countOff));
        for (int i = 0; i < n; i++)
        {
            int t = st.U8(SIM, typeBase + i);
            if (t == 0) shift--;
            else if (shift != 0)
            {
                int j = i + shift;
                st.Set8(SIM, typeBase + j, t);
                foreach (int f in fields) st.Set8(SIM, f + j, st.U8(SIM, f + i));
            }
        }
        st.Set16(G, countOff, n + shift);
    }

    public static readonly int[] SURFACE_FIELDS = { 0xa180, 0xa569, 0xa952, 0xb124 };

    public static void CompactSurface(State st) => Compact(st, 0xad3b, SURFACE_FIELDS, 0xd6a);

    public static void CompactNest(State st, NestKind n) => Compact(st, n.Type, new[] { n.X, n.Y, n.State, n.E }, n.Count);
}
