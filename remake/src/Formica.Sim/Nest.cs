using static Formica.Sim.Seg;
using static Formica.Sim.Bits;
using Mv = Formica.Sim.Movement;
using Ng = Formica.Sim.NestGrid;
using Sf = Formica.Sim.Surface;

namespace Formica.Sim;

/// <summary>Black nest ants: the per-tick loop, state handlers and helpers (SIMANT.EXE overlay section 27,
/// segment 899e, plus nest helpers in segments 0be8, 0ec1 and 14ee).
/// Nest ants live in the b_* arrays (count G:0da8); each one's type byte is also written into the nest
/// contents grid (0x8180) at its cell. The dirt grid (0x2180) holds tunnels, stored food and dirt; the exit
/// field (0x4180) counts up towards the entrance. Red ants in the black nest are invaders and run their own
/// branch of the tick. The shared helpers take the colony (BLACK or RED).</summary>
public static class Nest
{
    public static readonly NestKind BLACK = Ng.BLACK;
    public static readonly NestKind RED = Ng.RED;
    static readonly NestKind N = BLACK;
    static readonly int DIRT = N.Dirt, EXITF = N.Exitf, CELLS = N.Cells;
    static readonly int BX = N.X, BY = N.Y, BSTATE = N.State, BTYPE = N.Type, BE = N.E;

    internal static int Cur(State st) => st.U16(G, 0xf18);

    static int Get(State st, int f, int i) => st.U8(SIM, f + i);

    static void Set(State st, int f, int i, int v) => st.Set8(SIM, f + i, v);

    /// <summary>f_141cb: StateForCaste for a black ant.</summary>
    static int Job(State st, int caste) => Mv.StateForCaste(st, caste, 0);

    static int Visible(State st) => st.U16(T, 0x7b2);

    // ------------------------------------------------------------------------------------------- lookups
    /// <summary>f_0eeed (black) / f_0ef3c (red): index of the nest ant at (col, depth) with type t, searching
    /// from the top; -1 if none.</summary>
    public static int NestAntAt(State st, NestKind n, int col, int depth, int t)
    {
        int i = S16(st.U16(G, n.Count));
        while (i > 0)
        {
            i--;
            if (Get(st, n.X, i) == col && Get(st, n.Y, i) == depth && Get(st, n.Type, i) == t) return i;
        }
        return -1;
    }

    /// <summary>f_0ca41: inside the nest below the top row.</summary>
    public static bool NestCellFree(int col, int depth) => 0 <= col && col <= 0x3f && 1 <= depth && depth <= 0x3f;

    /// <summary>f_0cbe7 NestStepDir: neighbour (not straight back) with the smallest nonzero exit-field value
    /// &lt;= the current one, ties 50/50 - i.e. go deeper. -1 at a dead end.</summary>
    public static int StepDir(State st, NestKind n, int col, int depth, int d)
    {
        int best = -1, cur = st.Grid(n.Exitf, col, depth);
        for (int i = 0; i < 8; i++)
        {
            if ((d ^ 4) == i) continue;
            int c = col + Mv.Dx(st, i), r = depth + Mv.Dy(st, i);
            if (!(0 <= c && c < 0x40 && 0 <= r && r < 0x40)) continue;
            int v = st.Grid(n.Exitf, c, r);
            if (v == 0 || v > cur) continue;
            if (v >= cur && st.Rand2() == 0) continue;
            best = i;
            cur = v;
        }
        return best;
    }

    /// <summary>f_0ca8f NestClimbDir: 1 + direction of the highest exit-field neighbour (not straight back), 0
    /// if none. At depth 1 it heads up the shaft if there is one, else sideways.</summary>
    public static int ClimbDir(State st, NestKind n, int col, int depth, int d)
    {
        if (depth == 1)
        {
            if (st.Grid(n.Dirt, col, 0) == 0x18) return 1;
            return st.Rand2() * 4 + 3;
        }
        int best = 0, bv = 0;
        for (int i = 0; i < 8; i++)
        {
            int c = col + Mv.Dx(st, i), r = depth + Mv.Dy(st, i);
            if (0 <= c && c < 0x40 && 0 <= r && r < 0x40)
            {
                int v = st.Grid(n.Exitf, c, r);
                if (bv < v && (d ^ 4) != i) { best = i + 1; bv = v; }
            }
        }
        return best;
    }

    /// <summary>GetTile(view, c, r): -1 outside the nest.</summary>
    static int NestTile(State st, NestKind n, int c, int r) =>
        0 <= c && c < 0x40 && 0 <= r && r < 0x40 ? st.Grid(n.Dirt, c, r) : -1;

    /// <summary>IsOpenGround(view, c, r) (f_1145c): open tunnel (&lt; 8) and no occupant other than the yellow ant.</summary>
    static bool NestOpen(State st, NestKind n, int c, int r)
    {
        int t = NestTile(st, n, c, r);
        if (t < 0) return false;
        int o = st.Grid(n.Cells, c, r);
        if (o != 0 && !Mv.IsYellow(o)) return false;
        return t < 8;
    }

    /// <summary>f_7a69d (view 2 black / 3 red): like Surface.StepTowardsSurface, inside a nest.</summary>
    public static int StepTowardsNest(State st, NestKind n, int col, int depth, int tc, int tr)
    {
        int dist = Mv.DistanceLo(col, depth, tc, tr);
        if (dist <= 0) return -1;
        int res = -1, fallback = -2;
        for (int d = 0; d < 8; d++)
        {
            int c = col + Mv.Dx(st, d), r = depth + Mv.Dy(st, d);
            int t = NestTile(st, n, c, r);
            if (t < 0 || !(t < 0x19 || (0x30 <= t && t <= 0x31))) continue;   // f_133f9
            if (0x30 <= t && t <= 0x31) continue;                                // f_116a1
            int nd = Mv.DistanceLo(c, r, tc, tr);
            if (nd >= dist) continue;
            dist = nd;
            if (st.Grid(n.Cells, c, r) == 0 && NestOpen(st, n, c, r)) res = d;
            else fallback = d;
        }
        return res >= 0 ? res : fallback;
    }

    // ------------------------------------------------------------------------------------------- terrain
    /// <summary>f_113fe(view 1): the surface cell and all 8 neighbours are open ground.</summary>
    public static bool IsOpenWithRing(State st, int a, int b)
    {
        if (!Sf.IsOpenGround(st, a, b)) return false;
        for (int d = 0; d < 8; d++)
            if (!Sf.IsOpenGround(st, a + Mv.Dx(st, d), b + Mv.Dy(st, d))) return false;
        return true;
    }

    /// <summary>f_15395: draw the ring of entrance tiles (DS:1bb2) around a new yard entrance.</summary>
    public static void EntranceRing(State st, int a, int b)
    {
        for (int d = 0; d < 8; d++)
        {
            int na = a + Mv.Dx(st, d), nb = b + Mv.Dy(st, d);
            if (0 <= na && na <= 0x7f && 0 <= nb && nb <= 0x3f && st.Grid(Sf.SURFACE, na, nb) < 0x50)
                st.SetGrid(Sf.SURFACE, na, nb, st.U8(0x55b3, 0x1bb2 + d));
        }
    }

    /// <summary>f_151f7: the entrance version of a house floor tile, 0 if there is none.</summary>
    public static int HouseEntranceTile(int t)
    {
        if (t == 0) return 0x86;
        if (t == 2 || t == 3) return 0x8a;
        if (0x5d < t)
        {
            if (t < 0x62) return t + 0x22;
            if (t == 0x66) return 0x85;
            if (t == 0x68) return 0x84;
        }
        return 0;
    }

    /// <summary>f_150b0 MakeSurfaceHoleBlack / f_15247 (red): open an entrance on the surface above nest column
    /// `col` (black tries surface rows 2..33, red 126..95).</summary>
    public static void MakeSurfaceHole(State st, NestKind n, int col)
    {
        int k = st.Rand(0x1f);
        int found = -1;
        for (int i = 0; i < 0x22; i++)
        {
            int a = n.HoleRow(k, i);
            if (st.U16(G, 0xf24) == 0)
            {
                if (IsOpenWithRing(st, a, col))
                {
                    st.SetGrid(Sf.SURFACE, a, col, 0x50);
                    found = a;
                }
            }
            else
            {
                int v = HouseEntranceTile(st.Grid(Sf.SURFACE, a, col));
                if (v != 0)
                {
                    st.SetGrid(Sf.SURFACE, a, col, v);
                    found = a;
                }
            }
            if (found >= 0)
            {
                st.Set16(T, n.EntrXy, a);
                st.Set16(T, n.EntrXy + 2, col);
                st.Set16(T, n.EntrCol, col);
                st.Set16(T, n.EntrCol + 2, 0);
                if (st.U16(G, 0xf24) == 0) EntranceRing(st, a, col);
                break;
            }
        }
        if (found >= 0)
        {
            st.Set8(T, n.Entr + col, found);
            Ng.DigAt(st, n, col, 1);
        }
    }

    /// <summary>f_15623 DigCellBlack / f_1577e (red): dig exposed dirt; tunnels stay one cell thick. True if dug.</summary>
    public static bool DigCell(State st, NestKind n, int col, int depth)
    {
        int dirt = n.Dirt;
        if ((depth < 0x3f && !Ng.IsDiggable(st.Grid(dirt, col, depth + 1)))
            || (depth > 2 && !Ng.IsDiggable(st.Grid(dirt, col, depth - 1)))
            || col == 0 || col > 0x3e)
            return false;
        if (depth == 0)
        {
            st.SetGrid(dirt, col, 0, 0x18);
            MakeSurfaceHole(st, n, col);
        }
        else
            st.SetGrid(dirt, col, depth, st.Rand8());
        Ng.DigBookkeeping(st, n, col, depth);
        Ng.ReclassifyDirt(st, n, col, depth - 1);
        Ng.ReclassifyDirt(st, n, col + 1, depth);
        Ng.ReclassifyDirt(st, n, col, depth + 1);
        Ng.ReclassifyDirt(st, n, col - 1, depth);
        Ng.UpdateExitField(st, n, col, depth);
        return true;
    }

    /// <summary>f_0c8db SpawnBlackBrood / f_0c93e SpawnRedBrood.</summary>
    public static void SpawnBrood(State st, NestKind n, int col, int depth, int stage)
    {
        if (S16(st.U16(G, n.Count)) < 500 && NestCellFree(col, depth))
        {
            Ng.DigAt(st, n, col, depth);
            Ng.AddNestAnt(st, n, col, depth, stage, 8, 0);
            st.SetGrid(n.Cells, col, depth, stage);
        }
    }

    // ------------------------------------------------------------------------------------------- food
    static void EatCore(State st, NestKind n, int col, int depth, bool healthGain)
    {
        int v = st.Grid(n.Dirt, col, depth);
        st.SetGrid(n.Dirt, col, depth, v == 0x10 ? st.Rand8() : v - 1);
        if (S16(st.U16(G, n.Food)) > 0) st.Inc16(G, n.Food, -1);
        if (!healthGain) return;
        int lim = S16(st.U16(G, n.Soldiers) + st.U16(G, n.Pop)) >> 4;
        st.Inc16(G, n.Acc, 5);
        if (lim < S16(st.U16(G, n.Acc)))
        {
            st.Set16(G, n.Acc, 0);
            if (S16(st.U16(G, n.Health)) < 100) st.Inc16(G, n.Health);
        }
    }

    /// <summary>f_7ae88 EatFoodBlack / f_10720 (red).</summary>
    public static void EatFood(State st, NestKind n, int col, int depth) => EatCore(st, n, col, depth, true);

    /// <summary>f_7adcf EatIfOnFoodBlack / f_10667 (red).</summary>
    public static void EatIfOnFood(State st, NestKind n, int col, int depth)
    {
        int v = st.Grid(n.Dirt, col, depth);
        if (0x10 <= v && v <= 0x13) EatCore(st, n, col, depth, true);
    }

    /// <summary>f_7af2f / f_107c7: an invader eats the other colony's stores (no health gain).</summary>
    public static void InvaderEatFood(State st, NestKind n, int col, int depth) => EatCore(st, n, col, depth, false);

    /// <summary>f_7a2ea StoreFoodBlack / f_0fda0 (red): the carrier drops its food here (counted even when full).</summary>
    public static int StoreFood(State st, NestKind n, int col, int depth)
    {
        int v = st.Grid(n.Dirt, col, depth);
        int ok = 1;
        if (v < 0x10) st.SetGrid(n.Dirt, col, depth, 0x10);
        else if (v > 0x12) ok = 0;
        else st.SetGrid(n.Dirt, col, depth, v + 1);
        st.Inc16(G, n.Food);
        int cur = Cur(st);
        if ((Get(st, n.Type, cur) & 8) != 0) Set(st, n.Type, cur, Get(st, n.Type, cur) - 8);
        return ok;
    }

    /// <summary>f_7af94.</summary>
    public static void EggCost(State st)
    {
        st.Inc16(G, 0x212, -1);
        if (S16(st.U16(G, 0x212)) < 0)
        {
            st.Set16(G, 0x212, S16(st.U16(G, 0x330)) >> 5);
            if (S16(st.U16(G, 0x10be)) > 0 && st.U16(T, 0xc18) == 0) st.Inc16(G, 0x10be, -1);
        }
    }

    // ------------------------------------------------------------------------------------------- moving
    /// <summary>f_7b661 (black) / f_10e27 (red): an ant at the top of the nest tries to leave through the shaft
    /// in its column.</summary>
    public static int ExitToSurface(State st, NestKind n, int col)
    {
        int cur = Cur(st);
        int dirt = n.Dirt, ty = n.Type;
        if (st.Grid(dirt, col, 0) == 0x18)
        {
            int t = Get(st, ty, cur);
            Set(st, ty, cur, 0);
            if (st.U8(T, n.Entr + col) == 0) MakeSurfaceHole(st, n, col);
            int e = Get(st, n.E, cur), state = Get(st, n.State, cur);
            int nt = (st.Rand8() + (t & 0xf8)) & 0xff;
            if (Sf.AddSurfaceAnt(st, st.U8(T, n.Entr + col), col, nt, state, e) != 0)
            {
                st.SetGrid(n.Cells, col, 1, 0);
                return 1;
            }
            Set(st, ty, cur, t);
            Set(st, n.State, cur, 0);
            return 0;
        }
        int v = st.Grid(n.Exitf, col, 0);
        if (v != 0) st.SetGrid(n.Exitf, col, 0, v - 1);
        if (st.Rand2() != 0)
        {
            if (col > 0 && Ng.IsDiggable(st.Grid(dirt, col - 1, 1))) DigCell(st, n, col - 1, 1);
        }
        else if (col < 0x3f && Ng.IsDiggable(st.Grid(dirt, col + 1, 1)))
            DigCell(st, n, col + 1, 1);
        MoveTo(st, n, col, 1, st.Rand8());
        return 0;
    }

    /// <summary>f_7aa3b NestMoveTo (black) / f_103b9 (red): step the current ant into a passable cell (dirt
    /// &lt; 0x1c), overwriting whatever the contents grid held there. Stepping above row 1 leaves the nest. 1 if moved.</summary>
    public static int MoveTo(State st, NestKind n, int col, int depth, int d)
    {
        d = S16(d);
        if (d < 0) return 0;
        int c = col + Mv.Dx(st, d), r = depth + Mv.Dy(st, d);
        if (!(0 <= c && c < 0x40 && r < 0x40)) return 0;
        if (r < 1) return ExitToSurface(st, n, col);
        if (st.Grid(n.Dirt, c, r) >= 0x1c) return 0;
        int cur = Cur(st);
        int cells = n.Cells, ty = n.Type;
        if (n.Red == 0 && st.Grid(cells, c, r) == 0xff && st.U16(G, 0x1044) != 0
            && Get(st, n.X, cur) < 0x80)
        {
            st.SetGrid(cells, col, depth, (Get(st, ty, cur) & 0xf8) | d);
            st.Hooks.NestFollow(st, col, depth, d);                         // f_2f7bc
        }
        int v = (Get(st, ty, cur) & 0xf8) | d;
        st.SetGrid(cells, c, r, v);
        st.SetGrid(cells, col, depth, 0);
        Set(st, n.X, cur, c);
        Set(st, n.Y, cur, r);
        Set(st, ty, cur, v);
        return 1;
    }

    /// <summary>f_7a233 NestFightAt: fight a red ant (or the red-side yellow ant) in this cell. Returns 1 if so.</summary>
    public static int FightAt(State st, int col, int depth, int t)
    {
        int o = st.Grid(CELLS, col, depth);
        if (Mv.IsYellow(o) && st.U16(G, 0x4e2) != 0)
        {
            st.Hooks.AttackPlayer(st, 2, Cur(st));
            return 1;
        }
        if (0x87 < o && o < 0xe8)
        {
            int i = NestAntAt(st, N, col, depth, o);
            if (i >= 0)
            {
                int w = Sf.ResolveFight(st, o, t & 0xff);
                Set(st, BE, i, w);
                int nt = ((w & 0x80) + 0x70) & 0xff;
                Set(st, BTYPE, i, nt);
                st.SetGrid(CELLS, col, depth, nt);
                Set(st, BSTATE, i, 10);
                return 1;
            }
        }
        return 0;
    }

    /// <summary>The common 'step into a free tunnel cell' of Got Food / Dig In / Go To Surface. False = fought.</summary>
    static bool Enter(State st, int col, int depth, int c, int r, int d, int nt)
    {
        st.SetGrid(CELLS, col, depth, 0);
        int o = st.Grid(CELLS, c, r);
        if ((o & 0x80) != 0 && (!Mv.IsYellow(o) || st.U16(G, 0x4e2) != 0) && FightAt(st, c, r, nt) != 0) return false;
        int cur = Cur(st);
        int v = (Get(st, BTYPE, cur) & 0xf8) | d;
        Set(st, BTYPE, cur, v);
        st.SetGrid(CELLS, c, r, v);
        Set(st, BX, cur, c);
        Set(st, BY, cur, r);
        return true;
    }

    internal static int TurnTo(State st, NestKind n, int col, int depth, int t, int d)
    {
        int nt = (t & 0xf8) | d;
        st.SetGrid(n.Cells, col, depth, nt);
        Set(st, n.Type, Cur(st), nt);
        return nt;
    }

    // ------------------------------------------------------------------------------------------- queen
    /// <summary>f_7a78f QueenMove: the head walks towards the nest centroid and drags the abdomen after it.</summary>
    public static int QueenMove(State st, int col, int depth, int t)
    {
        int d = StepTowardsNest(st, N, col, depth, S16(st.U16(G, 0x10b2)), S16(st.U16(G, 0x10c0)));
        if (d < 0)
        {
            if (d == -1) return 0;
            d = st.Rand8();
        }
        if ((depth > 2 || (2 < d && d < 6)) && MoveTo(st, N, col, depth, d) != 0)
        {
            int back = (t ^ 0xfc) & 7;
            int c = Mv.Dx(st, back) + col, r = Mv.Dy(st, back) + depth;
            st.SetGrid(CELLS, c, r, 0);
            int i = NestAntAt(st, N, c, r, (t & 7) + 0x68);
            if (i >= 0 && Get(st, BTYPE, i) != 0)
            {
                Set(st, BX, i, col);
                Set(st, BY, i, depth);
                Set(st, BTYPE, i, d + 0x68);
                st.SetGrid(CELLS, col, depth, d + 0x68);
            }
            return 1;
        }
        return 0;
    }

    /// <summary>f_7a9c7: the abdomen sees no head behind (cell behind != t+8 and no such ant there).</summary>
    public static bool QueenHeadLost(State st, int col, int depth, int t)
    {
        int back = (t ^ 0xfc) & 7;
        int c = Mv.Dx(st, back) + col, r = Mv.Dy(st, back) + depth;
        return st.Grid(CELLS, c, r) != t + 8 && NestAntAt(st, N, c, r, t + 8) < 0;
    }

    /// <summary>f_7a956: the abdomen's head (cell in front, type t-8) is gone.</summary>
    public static bool QueenTailLost(State st, int col, int depth, int t)
    {
        int c = Mv.Dx(st, t & 7) + col, r = Mv.Dy(st, t & 7) + depth;
        return st.Grid(CELLS, c, r) != t - 8 && NestAntAt(st, N, c, r, t - 8) < 0;
    }

    /// <summary>f_7a8a2: a caste-12 fight winner gets its abdomen back (as an Egg Laying caste-13 ant behind it).</summary>
    public static void AddAbdomen(State st, int i)
    {
        int t = Get(st, BTYPE, i);
        int back = (t & 7) ^ 4;
        Ng.AddNestAnt(st, N, Mv.Dx(st, back) + Get(st, BX, i), Mv.Dy(st, back) + Get(st, BY, i), (t + 8) & 0xff, 9, 0);
    }

    /// <summary>f_7a910: remove ant i and clear its cell.</summary>
    public static void RemoveAnt(State st, int i)
    {
        Set(st, BTYPE, i, 0);
        st.SetGrid(CELLS, Get(st, BX, i), Get(st, BY, i), 0);
    }

    // ------------------------------------------------------------------------------------------- handlers
    internal static void MoveOrRandom(State st, NestKind n, int col, int depth, int d)
    {
        if (MoveTo(st, n, col, depth, d) == 0) MoveTo(st, n, col, depth, st.Rand8());
    }

    /// <summary>f_7a057 (Bored, Pre-Flight and states > 17).</summary>
    public static void NWander(State st, int col, int depth, int t, int caste)
    {
        if (st.Rand32() == 0) Set(st, BSTATE, Cur(st), Job(st, caste));
        if (FightAt(st, col, depth, t) != 1) MoveOrRandom(st, N, col, depth, t & 7);
    }

    /// <summary>f_7ab6e: nurses carry brood (caste 1 = worker carrying, stage in b_e low bits, bit 3 = direction).</summary>
    public static void NNesting(State st, int col, int depth, int t, int caste)
    {
        int cur = Cur(st);
        int d = t & 7;
        int stage = Get(st, BE, cur) & 7;
        int here = st.Grid(CELLS, col, depth);
        int up = Get(st, BE, cur) >> 3;
        int c;
        if (caste == 1)
        {
            if (up == 0)
            {
                d = StepDir(st, N, col, depth, d);
                if (d < 0) Set(st, BE, cur, stage | 8);
                MoveOrRandom(st, N, col, depth, d);
                return;
            }
            if (here == 0 || here > 8)
            {
                Set(st, BTYPE, cur, Get(st, BTYPE, cur) + 8);
                SpawnBrood(st, N, col, depth, stage);
                st.SetGrid(CELLS, col, depth, Get(st, BTYPE, cur));
                Set(st, BE, cur, 8);
                Set(st, BSTATE, cur, Job(st, 1));
            }
            c = ClimbDir(st, N, col, depth, d);
        }
        else if (caste == 2)
        {
            if (up == 0)
            {
                if (here == 0 || here > 7)
                {
                    if (S16(st.Rand(100)) > S16(st.U16(G, 0x10be))) EatIfOnFood(st, N, col, depth);
                    else if (st.Rand16() == 0) Set(st, BSTATE, cur, Job(st, 2));
                }
                else
                {
                    int i = NestAntAt(st, N, col, depth, here);
                    if (i >= 0)
                    {
                        Set(st, BTYPE, i, 0);
                        Set(st, BTYPE, cur, Get(st, BTYPE, cur) - 8);
                        Set(st, BE, cur, here);
                        return;
                    }
                }
                MoveOrRandom(st, N, col, depth, d);
                return;
            }
            if (st.Rand8() == 0) Set(st, BE, cur, 0);
            c = ClimbDir(st, N, col, depth, d);
        }
        else
        {
            if (S16(st.Rand(100)) > S16(st.U16(G, 0x10be))) EatIfOnFood(st, N, col, depth);
            if (st.Rand8() == 0) Set(st, BSTATE, cur, Job(st, caste));
            MoveOrRandom(st, N, col, depth, d);
            return;
        }
        d = c == 0 ? st.Rand8() : c - 1;
        MoveOrRandom(st, N, col, depth, d);
    }

    /// <summary>f_7afdc: carry food deeper; store it with 1/16 chance or at a dead end, maybe eat, then a new job.</summary>
    public static void NGotFood(State st, int col, int depth, int t)
    {
        int d = StepDir(st, N, col, depth, t & 7);
        if (d < 0 || st.Rand16() == 0)
        {
            StoreFood(st, N, col, depth);
            if (S16(st.Rand(100)) > S16(st.U16(G, 0x10be))) EatFood(st, N, col, depth);
            Set(st, BSTATE, Cur(st), Job(st, (t & 0x78) >> 3));
            return;
        }
        int nt = TurnTo(st, N, col, depth, t, d);
        int c = col + Mv.Dx(st, d), r = depth + Mv.Dy(st, d);
        if (c > 0x3f || c < 0 || r > 0x3f) return;
        if (r < 1)
        {
            ExitToSurface(st, N, col);
            return;
        }
        if (st.Grid(DIRT, c, r) >= 0x30) return;
        Enter(st, col, depth, c, r, d, nt);
    }

    /// <summary>f_7b197: workers/soldiers walk deeper and dig the first exposed dirt they face.</summary>
    public static void NDigIn(State st, int col, int depth, int t, int caste)
    {
        int cur = Cur(st);
        if (caste != 2 && caste != 6)
        {
            Set(st, BSTATE, cur, Job(st, caste));
            return;
        }
        int d = StepDir(st, N, col, depth, t & 7);
        if (d < 0) d = st.Rand8();
        int nt = TurnTo(st, N, col, depth, t, d);
        if (depth != 0x3f)
        {
            int r = depth + Mv.Dy(st, d), c = col + Mv.Dx(st, d);
            if (c > 0x3f || c < 0 || r > 0x3f) return;
            if (r < 1)
            {
                ExitToSurface(st, N, col);
                return;
            }
            int tile = st.Grid(DIRT, c, r);
            if (tile > 0x2f) return;
            if (Ng.IsDiggable(tile))
            {
                if (!DigCell(st, N, c, r))
                {
                    Set(st, BSTATE, cur, Job(st, caste));
                    return;
                }
                Set(st, BTYPE, cur, Get(st, BTYPE, cur) + 0x18);            // now carrying dirt
                Set(st, BSTATE, cur, 5);
                st.Hooks.Effect(st, "sound", 0x11);
            }
            if (!Enter(st, col, depth, c, r, d, nt)) return;
            if (S16(st.Rand64()) > S16(st.U16(G, 0x10be))) EatIfOnFood(st, N, c, r);
            if (st.Rand4() == 0) Ng.UpdateExitField(st, N, c, r);
            return;
        }
        Set(st, BSTATE, cur, Job(st, caste));
    }

    /// <summary>f_7b3ac: every outdoor job climbs the exit field and leaves; at a dead end diggers start digging.</summary>
    public static void NGoToSurface(State st, int col, int depth, int t)
    {
        int c1 = ClimbDir(st, N, col, depth, t & 7);
        int d = c1 < 1 ? Mv.TurnAside(st, t & 7) : c1 - 1;
        int nt = TurnTo(st, N, col, depth, t, d);
        int c = col + Mv.Dx(st, d), r = depth + Mv.Dy(st, d);
        if (!(0 <= c && c < 0x40 && r < 0x40)) return;
        if (r < 1)
        {
            ExitToSurface(st, N, col);
            return;
        }
        int tile = st.Grid(DIRT, c, r);
        if (tile < 0x30)
        {
            if (!Ng.IsDiggable(tile) && Enter(st, col, depth, c, r, d, nt))
                if (S16(st.Rand64()) > S16(st.U16(G, 0x10be))) EatIfOnFood(st, N, c, r);
            return;
        }
        st.SetGrid(EXITF, col, depth, st.Grid(EXITF, col, depth) - 1);
        int caste = (t & 0x78) >> 3;
        int cur = Cur(st);
        if (caste == 5 || caste == 9)
        {
            Set(st, BTYPE, cur, Get(st, BTYPE, cur) - 0x18);
            Set(st, BSTATE, cur, 4);
        }
        if (caste == 2 || caste == 6) Set(st, BSTATE, cur, 4);
    }

    /// <summary>f_7a0c2: guards stay while the player watches the black nest, else go out.</summary>
    public static void NDefense(State st, int col, int depth, int t)
    {
        if (st.U16(G, 0x48c) == 2)
        {
            if (FightAt(st, col, depth, t) != 1) MoveOrRandom(st, N, col, depth, t & 7);
        }
        else
            NGoToSurface(st, col, depth, t);
    }

    /// <summary>f_7a360: brood advance one stage every 128 ticks (32 when the colony is tiny) and hatch after 8.</summary>
    public static void NBrood(State st, int col, int depth)
    {
        int cur = Cur(st);
        int t = Get(st, BTYPE, cur);
        int caste = -1;
        int mask = S16(st.U16(G, 0x330)) < 3 ? 0x1f : 0x7f;
        if ((st.U16(G, 0xf08) & mask) == 0)
        {
            t = (t + 1) & 0xff;
            if ((t & 0xf) == 8)
            {
                if (st.U16(G, 0x378) == 0 && (st.U16(G, 0x4a2) >> 7) < S16(st.RandLow(0xff)))
                {
                    t = 0;
                    st.Inc32(G, 0x1000);
                }
                else
                {
                    caste = S16(st.U16(T, 0xc0e));
                    t = (caste * 8 + 2) & 0xff;
                    Set(st, BSTATE, cur, caste == 2 ? 1 : Job(st, caste));
                }
            }
        }
        if (Visible(st) != 0 && caste < 0) st.Hooks.Effect(st, "brood", col, depth, 2);
        st.SetGrid(CELLS, col, depth, t);
        Set(st, BTYPE, cur, t);
        Set(st, BE, cur, 0);
    }

    /// <summary>f_7a490: the queen's head wanders (towards the centroid), her abdomen lays eggs.</summary>
    public static void NEggLaying(State st, int col, int depth, int caste, int t)
    {
        int cur = Cur(st);
        int v;
        if (caste == 12)
        {
            if (st.Rand64() == 0)
            {
                if (st.U16(G, 0x10be) == 0)
                {
                    Set(st, BTYPE, cur, 0);
                    st.SetGrid(CELLS, col, depth, 0);
                    st.Hooks.Effect(st, "message", 0x1093, 0, 0x271f, 1);     // f_2f6ea: the queen starved
                    return;
                }
                if (QueenMove(st, col, depth, t) != 0) return;
            }
            v = Get(st, BTYPE, cur);
            if (QueenHeadLost(st, col, depth, v))
            {
                v = 0;
                Set(st, BTYPE, cur, 0);
                st.Inc16(G, 0x35e, -1);
            }
            st.SetGrid(CELLS, col, depth, v);
            if (Visible(st) != 0) st.Hooks.Effect(st, "queen", col, depth, 2);
            return;
        }
        if (caste != 13) return;
        v = Get(st, BTYPE, cur);
        st.SetGrid(CELLS, col, depth, v);
        if (S16(st.U16(G, 0x35e)) > 0 && QueenTailLost(st, col, depth, v))
        {
            st.Inc16(G, 0x35e, -1);
            Set(st, BTYPE, cur, 0);
            st.SetGrid(CELLS, col, depth, 0);
            return;
        }
        int back = (t ^ 0xfc) & 7;
        int r = Mv.Dy(st, back) + depth, c = Mv.Dx(st, back) + col;
        if (!NestCellFree(c, r)) return;
        st.Set16(T, 0x2b4, c);
        st.Set16(T, 0x2b6, r);
        if ((st.U16(G, 0xf08) & 0xf) != 0) return;
        if (S16(st.Rand128()) > S16(st.U16(G, 0x10be))) return;
        SpawnBrood(st, N, c, r, 1);
        EggCost(st);
        st.Inc32(G, 0xfc2);
    }

    /// <summary>f_7a126: a fight entity jitters; with 1/16 per tick the winner (saved in b_e) emerges.</summary>
    public static void NFighting(State st, int col, int depth)
    {
        int cur = Cur(st);
        int j = st.Rand(7);
        Set(st, BTYPE, cur, ((Get(st, BTYPE, cur) & 0xf8) + j) & 0xff);
        st.SetGrid(CELLS, col, depth, Get(st, BTYPE, cur));
        if (st.Rand16() == 0)
        {
            int w = Get(st, BE, cur);
            st.SetGrid(CELLS, col, depth, w);
            Set(st, BTYPE, cur, w);
            if ((w & 0x78) == 0x60) AddAbdomen(st, cur);
            w = Get(st, BTYPE, cur);
            Set(st, BSTATE, cur, (w & 0x80) != 0 ? 7 : Mv.StateForCaste(st, (w & 0x78) >> 3, w));
        }
        else if (Visible(st) == 1)
            st.Hooks.Effect(st, "fight", col, depth, 2);
    }

    /// <summary>f_79ec5.</summary>
    public static void NResting(State st, int col, int depth, int t)
    {
        if (FightAt(st, col, depth, t) == 1) return;
        int cur = Cur(st);
        st.SetGrid(CELLS, col, depth, Get(st, BTYPE, cur));
        if (st.Rand(20) == 0)
        {
            int b = Get(st, BTYPE, cur);
            Set(st, BSTATE, cur, Mv.StateForCaste(st, (b & 0x78) >> 3, b));
        }
        else if (Visible(st) == 1)
            st.Hooks.Effect(st, "rest", col, depth, 2);
    }

    /// <summary>f_79f70: dying in the dirt? Leaves at a tunnel/food cell, else jitters and dies with 1/100.</summary>
    public static void NState17(State st, int col, int depth, int t)
    {
        int cur = Cur(st);
        if (st.Grid(DIRT, col, depth) < 0x14)
        {
            Set(st, BSTATE, cur, Job(st, (t & 0x78) >> 3));
            return;
        }
        int nt = (((st.Rand(3) + t - 1) & 7) | (t & 0xf8)) & 0xff;
        Set(st, BTYPE, cur, nt);
        st.SetGrid(CELLS, col, depth, nt);
        if (st.Rand(100) == 0)
        {
            st.SetGrid(CELLS, col, depth, 0);
            Set(st, BTYPE, cur, 0);
            st.Inc32(G, (t & 0x80) != 0 ? 0xfbc : 0xf30);
        }
    }

    /// <summary>f_79e40: red invaders climb towards the exit (any direction allowed).</summary>
    public static void NInvaderMove(State st, int col, int depth, int t)
    {
        int c = ClimbDir(st, N, col, depth, 8);
        int d = c == 0 ? st.Rand8() : c - 1;
        if (MoveTo(st, N, col, depth, d) == 0 && MoveTo(st, N, col, depth, st.Rand8()) == 0)
            st.SetGrid(CELLS, col, depth, Get(st, BTYPE, Cur(st)));
    }

    /// <summary>f_79d6f: raiding invaders head deeper looking for stored food, eat it and carry some home.</summary>
    public static void NInvaderAttack(State st, int col, int depth, int t)
    {
        int cur = Cur(st);
        int v = st.Grid(DIRT, col, depth);
        if (v < 0x10 || v > 0x13)
        {
            if (MoveTo(st, N, col, depth, (st.Rand(3) + t - 2) & 7) != 0) return;
            int d = StepDir(st, N, col, depth, t & 7);
            if (d < 0) d = st.Rand(8);
            if (MoveTo(st, N, col, depth, d) != 0) return;
            Set(st, BSTATE, cur, 1);
        }
        else
        {
            InvaderEatFood(st, N, col, depth);
            Set(st, BSTATE, cur, 3);
            Set(st, BTYPE, cur, Get(st, BTYPE, cur) | 8);
        }
        st.SetGrid(CELLS, col, depth, Get(st, BTYPE, cur));
    }

    /// <summary>f_79a4d BlackNestAntTick.</summary>
    public static void NestAntTick(State st, int col, int depth, int t)
    {
        int caste = (t & 0x78) >> 3;
        int cur = Cur(st);
        int state = Get(st, BSTATE, cur);
        if ((t & 0x80) != 0)
        {
            st.Inc16(G, 0xd72 + state * 2);
            if (t > 0xef)
            {
                NFighting(st, col, depth);
                return;
            }
            int o = st.Grid(CELLS, col, depth);
            if (Mv.IsYellow(o) && st.U16(G, 0x4e2) == 0)
            {
                st.Hooks.AttackPlayer(st, 2, cur);
                return;
            }
            if (0 < o && o < 0x68)
            {
                int i = NestAntAt(st, N, col, depth, o);
                if (i >= 0)
                {
                    if (o > 0x5f) RemoveAnt(st, i);
                    if (o < 8)                                    // steal brood
                    {
                        Set(st, BSTATE, cur, 3);
                        Set(st, BTYPE, cur, Get(st, BTYPE, cur) | 8);
                        st.SetGrid(CELLS, col, depth, Get(st, BTYPE, cur));
                        Set(st, BTYPE, i, 0);
                        st.Inc32(G, 0x1000);
                        return;
                    }
                    int w = Sf.ResolveFight(st, Get(st, BTYPE, i), t);
                    Set(st, BTYPE, cur, 0);
                    Set(st, BE, i, w);
                    int nt = ((w & 0x80) + 0x70) & 0xff;
                    Set(st, BTYPE, i, nt);
                    st.SetGrid(CELLS, col, depth, nt);
                    Set(st, BSTATE, i, 10);
                    return;
                }
            }
            if (state == 7) NInvaderAttack(st, col, depth, t);
            else NInvaderMove(st, col, depth, t);
            return;
        }
        st.Inc16(G, 0xd40 + state * 2);
        if (st.Rand256() == 0 && state != 9 && S16(st.Rand32()) > S16(st.U16(G, 0x10be)))
        {
            Set(st, BTYPE, cur, 0);
            st.SetGrid(CELLS, col, depth, 0);
            st.Inc32(G, 0xf30);
            return;
        }
        if (state > 0x11 || state == 0) NWander(st, col, depth, t, caste);
        else if (state == 1) NNesting(st, col, depth, t, caste);
        else if (state == 3) NGotFood(st, col, depth, t);
        else if (state == 4) NDigIn(st, col, depth, t, caste);
        else if (state == 6) NDefense(st, col, depth, t);
        else if (state == 8) NBrood(st, col, depth);
        else if (state == 9) NEggLaying(st, col, depth, caste, t);
        else if (state == 10) NFighting(st, col, depth);
        else if (state == 13) NResting(st, col, depth, t);
        else if (state == 14)
        {
            NWander(st, col, depth, t, caste);
            if (S16(st.U16(G, 0x8dc)) > 100) Set(st, BSTATE, Cur(st), 15);
        }
        else if (state == 17) NState17(st, col, depth, t);
        else NGoToSurface(st, col, depth, t);
    }

    /// <summary>f_799e0 BlackNestLoop: every live black-nest ant, from the top of the array down.</summary>
    public static void BlackNestLoop(State st)
    {
        st.Set16(G, 0xf18, st.U16(G, 0xda8));
        while (S16(st.U16(G, 0xf18)) > 0)
        {
            st.Inc16(G, 0xf18, -1);
            int i = st.U16(G, 0xf18);
            int t = Get(st, BTYPE, i);
            if (t != 0) NestAntTick(st, Get(st, BX, i), Get(st, BY, i), t);
        }
    }
}
