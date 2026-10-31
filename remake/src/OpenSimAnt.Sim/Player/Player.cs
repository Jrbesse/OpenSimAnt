using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;
using Co = OpenSimAnt.Sim.Colony;
using Mv = OpenSimAnt.Sim.Movement;
using Ng = OpenSimAnt.Sim.NestGrid;
using Ph = OpenSimAnt.Sim.Pheromones;

namespace OpenSimAnt.Sim;

/// <summary>An ant list's arrays (surface, black nest, red nest) in the SIM segment.</summary>
public sealed class AntList
{
    public int X, Y, Type, State, E, Count;
}

/// <summary>The player: the yellow ant's per-tick upkeep (sec27 f_7bf7e) and its actions (f_7b7b8), with the
/// view-generic map accessors of segment 10f7 they use.
/// The yellow ant is G:047C (a) / G:048A (b) in view G:048C (1 surface, 2 black nest, 3 red nest), type
/// G:04C2, colour G:04E2 (0 black), heading G:0496, health G:0F78. It sits in the view's occupancy grid as
/// 0xFF (a queen's second cell, behind her, as 0xFE). With G:0A06 != 0 the player is not an ant (the
/// spider). f_2f7d0(n) (dialogs, the yellow ant's death, ...) goes to st.Hooks.GameEvent.</summary>
public static partial class Player
{
    public const int SURFACE = 0x0180, OCC = 0x6180;

    static NestKind Nest_(int view) => view == 2 ? Nest.BLACK : Nest.RED;

    static int G16(State st, int off) => S16(st.U16(G, off));

    // ------------------------------------------------------------------------------------------- map accessors
    /// <summary>f_10f7e: surface 128 x 64 (f_137d7), nests 64 x 64 (f_13804).</summary>
    public static bool InView(int view, int a, int b)
    {
        if (view <= 1) return 0 <= a && a <= 0x7f && 0 <= b && b <= 0x3f;
        return 0 <= a && a <= 0x3f && 0 <= b && b <= 0x3f;
    }

    /// <summary>GetTile f_117c0: surface tile / nest dirt, -1 outside (or for a negative view).</summary>
    public static int GetTile(State st, int view, int a, int b)
    {
        if (!InView(view, a, b) || view < 0 || view > 3) return -1;
        int @base = view <= 1 ? SURFACE : Nest_(view).Dirt;
        return st.Grid(@base, a, b);
    }

    /// <summary>f_1345e: a nest cell the yellow ant would dig through (diggable dirt, or tiles 0x1C..0x1F).</summary>
    public static bool IsDirt(State st, int view, int a, int b)
    {
        if (view < 2 || !InView(view, a, b)) return false;
        int t = GetTile(st, view, a, b);
        return Ng.IsDiggable(t) || (0x1c <= t && t <= 0x1f);                // f_11654
    }

    /// <summary>f_15031: dig the nest cell (the top rows open a new entrance above).</summary>
    public static void DigThrough(State st, int view, int a, int b)
    {
        if (!IsDirt(st, view, a, b)) return;
        var n = view == 2 ? Nest.BLACK : Nest.RED;
        if (b <= 1)
        {
            st.SetGrid(n.Dirt, a, 0, 0x18);
            Nest.MakeSurfaceHole(st, n, a);
            if (b != 1) return;
        }
        Ng.DigAt(st, n, a, b);
    }

    /// <summary>f_1156e: write the view's occupancy grid (in the nests, the yellow ant digs its way).</summary>
    public static void SetOcc(State st, int view, int a, int b, int v)
    {
        if (!InView(view, a, b)) return;
        if (view >= 0)
        {
            if (view <= 1) st.SetGrid(OCC, a, b, v);
            else if (view == 2 || view == 3)
            {
                st.SetGrid(Nest_(view).Cells, a, b, v);
                if (S16(v) > 0 && IsDirt(st, view, a, b))
                {
                    DigThrough(st, view, a, b);
                    st.Hooks.Effect(st, "sound", 0x13);
                }
            }
        }
        st.Hooks.Effect(st, "redraw", view, a, b);                         // f_0250e
    }

    /// <summary>f_1196c: the queen's second cell, behind her.</summary>
    public static void SetQueenTail(State st, int view, int a, int b, int heading, int v)
    {
        int h = (heading ^ 4) & 0xffff;
        SetOcc(st, view, a + st.S8(T, h), b + st.S8(T, 8 + h), v == 0xff ? 0xfe : v);
    }

    /// <summary>f_119b4: write the yellow ant (v 0xFF) or clear it (v 0) at (view, a, b); v != 0 also records
    /// it as the yellow ant's position.</summary>
    public static void PutYellow(State st, int view, int a, int b, int t, int heading, int v)
    {
        if (!InView(view, a, b)) return;
        SetOcc(st, view, a, b, v);
        if (t == 0x60) SetQueenTail(st, view, a, b, heading, v);
        if (v != 0)
        {
            st.Set16(G, 0x47c, a);
            st.Set16(G, 0x48a, b);
            st.Set16(G, 0x496, heading);
            st.Set16(G, 0x4c2, t);
            st.Set16(G, 0x48c, view);
        }
    }

    /// <summary>f_12d43: the yellow ant's health G:0F78 (0..100; T:0C16 keeps it full); G:1044 warns when low.</summary>
    public static void SetHealth(State st, int hp)
    {
        hp = S16(hp);
        st.Set16(G, 0xf78, st.U16(T, 0xc16) != 0 ? 100 : hp);
        if (G16(st, 0xf78) > 0) st.Set16(G, 0x1006, 0);
        if (G16(st, 0xf78) > 100) st.Set16(G, 0xf78, 100);
        else if (G16(st, 0xf78) < 0) st.Set16(G, 0xf78, 0);
        hp = G16(st, 0xf78);
        st.Set16(G, 0x1044, hp > G16(st, 0xfba) && hp >= 10 ? 0 : 1);
    }

    /// <summary>GetOccupant f_11737: the view's occupancy byte, -1 if empty or outside.</summary>
    public static int GetOcc(State st, int view, int a, int b)
    {
        if (!InView(view, a, b) || view < 0) return -1;
        int v;
        if (view <= 1) v = st.Grid(OCC, a, b);
        else if (view == 2 || view == 3) v = st.Grid(Nest_(view).Cells, a, b);
        else return -1;
        return v != 0 ? v : -1;
    }

    /// <summary>f_118c4: clear the cell if it holds v.</summary>
    public static void ClearOccIf(State st, int view, int a, int b, int v)
    {
        if (!InView(view, a, b)) return;
        if (GetOcc(st, view, a, b) == v) SetOcc(st, view, a, b, 0);
        st.Hooks.Effect(st, "redraw", view, a, b);                         // f_0250e
    }

    /// <summary>f_11918: lift the yellow ant (and a queen's second cell) off the map.</summary>
    public static void TakeYellow(State st, int view, int a, int b, int t, int heading)
    {
        ClearOccIf(st, view, a, b, 0xff);
        if (t == 0x60)
        {
            int h = (heading ^ 4) & 0xffff;
            ClearOccIf(st, view, a + st.S8(T, h), b + st.S8(T, 8 + h), 0xfe);
        }
    }

    /// <summary>f_11a3e: move the yellow ant to (view, a, b) (view 0 means the surface).</summary>
    public static void MoveYellow(State st, int view, int a, int b, int t, int heading)
    {
        TakeYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x4c2), st.U16(G, 0x496));
        PutYellow(st, view != 0 ? view : 1, a, b, t, heading, 0xff);
    }

    public static readonly AntList SurfaceAnts = new() { X = 0xa180, Y = 0xa569, Type = 0xad3b, State = 0xa952, E = 0xb124, Count = 0xd6a };
    public static readonly AntList BlackAnts = new() { X = 0xb50d, Y = 0xb702, Type = 0xbaec, State = 0xb8f7, E = 0xbce1, Count = 0xda8 };
    public static readonly AntList RedAnts = new() { X = 0xbed6, Y = 0xc0cb, Type = 0xc4b5, State = 0xc2c0, E = 0xc6aa, Count = 0xeaa };

    public static AntList Ants(int view) => view <= 1 ? SurfaceAnts : view == 2 ? BlackAnts : RedAnts;

    /// <summary>f_10fcd: (a, b, type, state, e) of ant i of the view's list, null if out of range.</summary>
    public static (int a, int b, int t, int state, int e)? GetAnt(State st, int view, int i)
    {
        var f = Ants(view);
        if (i < 0 || S16(st.U16(G, f.Count)) <= i) return null;
        return (st.U8(SIM, f.X + i), st.U8(SIM, f.Y + i), st.U8(SIM, f.Type + i), st.U8(SIM, f.State + i), st.U8(SIM, f.E + i));
    }

    /// <summary>f_11121.</summary>
    public static void SetAnt(State st, int view, int i, int a, int b, int t, int state, int e)
    {
        var f = Ants(view);
        if (i < 0 || S16(st.U16(G, f.Count)) <= i) return;
        st.Set8(SIM, f.X + i, a);
        st.Set8(SIM, f.Y + i, b);
        st.Set8(SIM, f.Type + i, t);
        st.Set8(SIM, f.State + i, state);
        st.Set8(SIM, f.E + i, e);
    }

    /// <summary>f_11246: the top-most ant at (a, b) with lo &lt;= type &amp; mask &lt;= hi, -1 if none.</summary>
    public static int FindAnt(State st, int view, int a, int b, int lo, int hi, int mask)
    {
        var f = Ants(view);
        int i = S16(st.U16(G, f.Count)) - 1;
        while (i >= 0)
        {
            int t = st.U8(SIM, f.Type + i) & mask;
            if (st.U8(SIM, f.X + i) == a && st.U8(SIM, f.Y + i) == b && lo <= t && t <= hi) return i;
            i--;
        }
        return i;
    }

    /// <summary>f_1162f.</summary>
    public static bool IsBrood(int t) => 1 <= (t & 0x7f) && (t & 0x7f) <= 7;

    /// <summary>f_0f167: append a surface ant (and write the occupancy grid).</summary>
    public static void AddSurfaceAntRaw(State st, int a, int b, int t, int state, int e)
    {
        int i = S16(st.U16(G, 0xd6a));
        if (i >= 1000) return;
        st.Set8(SIM, 0xa180 + i, a);
        st.Set8(SIM, 0xa569 + i, b);
        st.Set8(SIM, 0xa952 + i, state);
        st.Set8(SIM, 0xad3b + i, t);
        st.Set8(SIM, 0xb124 + i, e);
        st.SetGrid(OCC, a, b, t);
        st.Inc16(G, 0xd6a);
    }

    /// <summary>f_114bd: add an ant to the view's list (if there is room) and put it on the map. 1 if added.</summary>
    public static int AddAnt(State st, int view, int a, int b, int t, int state, int e)
    {
        if (view <= 1)
        {
            if (S16(st.U16(G, 0xd6a)) >= 1000) return 0;
            AddSurfaceAntRaw(st, a, b, t, state, e);
        }
        else
        {
            var n = view == 2 ? Nest.BLACK : Nest.RED;
            if (S16(st.U16(G, n.Count)) >= 500) return 0;
            Ng.AddNestAnt(st, n, a, b, t, state, e);
        }
        SetOcc(st, view, a, b, t);
        return 1;
    }

    /// <summary>f_116a1.</summary>
    public static bool IsRock(int view, int t)
    {
        if (view > 1) return 0x30 <= t && t <= 0x31;
        return view == 1 && 0x51 <= t && t <= 0x53;
    }

    /// <summary>f_116d6.</summary>
    public static bool IsNestFood(int t) => 0x10 <= t && t <= 0x13;

    /// <summary>f_1167b.</summary>
    public static bool IsFood(State st, int view, int t) => view <= 1 ? Mv.IsFood(st, t) : IsNestFood(t);

    /// <summary>f_116f7.</summary>
    public static bool FoodAt(State st, int view, int a, int b)
    {
        int t = GetTile(st, view, a, b);
        return t >= 0 && IsFood(st, view, t);
    }

    /// <summary>f_13791: on a nest entrance (surface) / on the top row's entrance tile 0x18 (nest).</summary>
    public static bool AtExit(State st, int view, int a, int b)
    {
        if (view <= 1) return Mv.AtNestEntrance(st, a, b);
        return b <= 0 && GetTile(st, view, a, b) == 0x18;
    }

    /// <summary>f_133cc.</summary>
    static bool LowTile(State st, int t) => st.U16(G, 0xf24) == 0 ? t <= 0x50 : t <= 0x5f;

    /// <summary>f_133f9: open ground (or a tunnel / rock in the nest).</summary>
    public static bool CanDrop(State st, int view, int a, int b)
    {
        int t = GetTile(st, view, a, b);
        if (t < 0) return false;
        if (view <= 1) return st.U16(G, 0xf24) == 0 ? t <= 0x53 : LowTile(st, t);
        return t <= 0x18 || IsRock(view, t);
    }

    /// <summary>f_0cd37: at most every 0x1C20 clock ticks, the next of three tunes (G:0228).</summary>
    public static void Jingle(State st)
    {
        if (S32(st.U32(G, 0x214) + 0x1c20) > S32(st.ReadClock())) return;
        st.Set32(G, 0x214, st.ReadClock());
        st.Inc16(G, 0x228);
        if (G16(st, 0x228) > 2) st.Set16(G, 0x228, 0);
        st.Hooks.Effect(st, "music", st.U16(G, 0x228) + 0x2713);
    }

    // ------------------------------------------------------------------------------------------- pathfinding
    // The yellow ant walks to the cursor target G:0AF8 (view) / G:0AD6 (a) / G:0AE8 (b) one cell per tick. A
    // greedy step that gets closer is preferred; when blocked it follows the wall (side G:0EFA: 1 clockwise,
    // -1 counter-clockwise, heading G:0EF8) for up to 16 steps (G:0D6C), never back onto its last cell
    // (G:0AB6 / G:0AC6). In mode 2 (G:0A8E) it digs through nest dirt.
    /// <summary>IsOpenGround f_1145c: tile &lt; 0x10 (surface) / &lt; 8 (nest), no occupant but the yellow ant.</summary>
    public static bool IsOpenGround(State st, int view, int a, int b)
    {
        int t = GetTile(st, view, a, b);
        if (t < 0) return false;
        int o = GetOcc(st, view, a, b);
        if (o >= 0 && !Mv.IsYellow(o)) return false;
        return t < (view <= 1 ? 0x10 : 8);
    }

    /// <summary>IsWalkable f_1323e. In the nests the top two rows lead only to the exit the target is at.</summary>
    public static bool IsWalkable(State st, int view, int a, int b, int tv, int ta, int tb, int dig)
    {
        if (view <= 1)
        {
            if (!(0 <= a && a <= 0x7f && 0 <= b && b <= 0x3f)) return false;
            int ts = st.Grid(SURFACE, a, b);
            return st.U16(G, 0xf24) == 0 ? ts <= 0x53 : ts <= 0x90;
        }
        if (!(0 <= a && a <= 0x3f && 0 <= b && b <= 0x3f)) return false;
        var n = view == 2 ? Nest.BLACK : Nest.RED;
        int t = st.Grid(n.Dirt, a, b);
        bool dirt;
        if (t <= 0x18 || (0x30 <= t && t <= 0x31)) dirt = false;
        else if (dig != 0 && ((0x20 <= t && t <= 0x2e) || (0x1c <= t && t <= 0x1f))) dirt = true;
        else return false;
        if (b > 1 || tv != view) return true;
        if (dig == 0)
        {
            if (b == 0) return ta == a && tb == 0;
            return ta == a || tb != 0;
        }
        if (!dirt) return b != 0 || (ta == a && tb == 0);
        if (ta != a) return false;
        if (b != 0) return true;
        int t1 = st.Grid(n.Dirt, a, 1);
        return !(0x20 <= t1 && t1 <= 0x2e);
    }

    /// <summary>Distance f_0ca03, low word as a signed int (how these callers read it).</summary>
    static int Dist(int a, int b, int ta, int tb) => S16(Co.Distance(a, b, ta, tb));

    static int DigMode(State st) => st.U16(G, 0xa8e) == 2 ? 1 : 0;

    static bool WalkableToTarget(State st, int view, int a, int b) =>
        IsWalkable(st, view, a, b, G16(st, 0xaf8), G16(st, 0xad6), G16(st, 0xae8), DigMode(st));

    /// <summary>f_7cd31: the neighbour that brings the yellow ant closest (each closer one tightens the
    /// threshold); the last free open-ground one wins, else the last other one. -1 when there, -2 when
    /// nothing is closer.</summary>
    public static int GreedyStep(State st, int view, int a, int b, int ta, int tb)
    {
        int best = Dist(a, b, ta, tb);
        if (best <= 0) return -1;
        int free = -1, busy = -2;
        for (int d = 0; d < 8; d++)
        {
            int na = a + st.S8(T, d), nb = b + st.S8(T, 8 + d);
            if (!WalkableToTarget(st, view, na, nb)) continue;
            int nd = Dist(na, nb, ta, tb);
            if (nd >= best) continue;
            if (GetOcc(st, view, na, nb) > 0 || !IsOpenGround(st, view, na, nb)) busy = d;
            else free = d;
            best = nd;
        }
        return free >= 0 ? free : busy;
    }

    /// <summary>f_7d03a: follow greedy steps (up to 64): -2 if they run into a block, else -1.</summary>
    public static int LookAhead(State st, int view, int a, int b, int ta, int tb)
    {
        int d = GreedyStep(st, view, a, b, ta, tb);
        if (d < 0) return d;
        int x = a + st.S8(T, d), y = b + st.S8(T, 8 + d);
        int n = 0;
        while (d >= 0 && n < 0x40)
        {
            d = GreedyStep(st, view, x, y, ta, tb);
            if (d >= 0)
            {
                x += st.S8(T, d);
                y += st.S8(T, 8 + d);
            }
            n++;
        }
        return d >= 0 ? -1 : d;
    }

    /// <summary>f_7ce36: follow the wall (G:0EFA side, G:0EF8 heading); back to greedy (side 0) once a step
    /// does not get further from the target.</summary>
    public static int WallStep(State st, int view, int a, int b, int ta, int tb)
    {
        int dist0 = Dist(a, b, ta, tb);
        if (dist0 <= 0) return -1;
        var ok = new bool[8];
        int anyd = -2;
        int pa = G16(st, 0xab6), pb = G16(st, 0xac6);
        for (int d = 0; d < 8; d++)
        {
            int na = a + st.S8(T, d), nb = b + st.S8(T, 8 + d);
            bool w = !(na == pa && nb == pb) && WalkableToTarget(st, view, na, nb);
            if (w) anyd = d;
            ok[d] = w;
        }
        if (anyd < 0) return anyd;
        int side = G16(st, 0xefa);
        int h = st.U16(G, 0xef8);
        int cw = h, ccw = h;
        if (side == 0)                                                      // pick a side
        {
            for (int k = 0; k < 8; k++)
            {
                if (ok[cw & 7])
                {
                    st.Set16(G, 0xef8, Mv.DirTo(a, b, ta, tb) - 1);
                    st.Set16(G, 0xefa, 1);
                    return cw;
                }
                if (ok[ccw & 7])
                {
                    st.Set16(G, 0xef8, Mv.DirTo(a, b, ta, tb) - 1);
                    st.Set16(G, 0xefa, 0xffff);
                    return ccw;
                }
                cw = (cw + 1) & 7;
                ccw = (ccw - 1) & 7;
            }
            return -1;
        }
        for (int k = 0; k < 8; k++)
        {
            int d = side > 0 ? cw : ccw;
            if (ok[d & 7])
            {
                if (Dist(a + st.S8(T, d), b + st.S8(T, 8 + d), ta, tb) <= dist0)
                {
                    st.Set16(G, 0xef8, Mv.DirTo(a, b, ta, tb) - 1);
                    st.Set16(G, 0xefa, 0);
                }
                return d;
            }
            cw = (cw + 1) & 7;
            ccw = (ccw - 1) & 7;
        }
        return -1;
    }

    /// <summary>f_7d15d: start following the wall for 16 steps.</summary>
    public static int StartWall(State st, int view, int a, int b, int ta, int tb)
    {
        st.Set16(G, 0xef8, Mv.DirTo(a, b, ta, tb) - 1);
        st.Set16(G, 0xd6c, 0x10);
        st.Set16(G, 0xefa, 0);
        return WallStep(st, view, a, b, ta, tb);
    }

    /// <summary>f_7d0e5.</summary>
    public static int WallOrGreedy(State st, int view, int a, int b, int ta, int tb)
    {
        if (LookAhead(st, view, a, b, ta, tb) == -2) return WallStep(st, view, a, b, ta, tb);
        st.Set16(G, 0xd6c, 0xffff);
        return GreedyStep(st, view, a, b, ta, tb);
    }

    /// <summary>f_7d1bd.</summary>
    public static int PathStep(State st, int view, int a, int b, int ta, int tb)
    {
        if (G16(st, 0xd6c) < 0)
        {
            int d0 = GreedyStep(st, view, a, b, ta, tb);
            if (d0 == -2 && G16(st, 0xd6c) == -2) d0 = StartWall(st, view, a, b, ta, tb);
            return d0;
        }
        int d = WallOrGreedy(st, view, a, b, ta, tb);
        st.Inc16(G, 0xd6c, -1);
        return d;
    }

    /// <summary>f_7d24f: the next step towards the cursor; in another view, towards this view's way out.</summary>
    public static int StepToCursor(State st, int view, int a, int b, int tv, int ta, int tb)
    {
        if (view <= 1)
        {
            if (tv > 1)
            {
                int off = tv == 2 ? 0x2ac : 0x2b0;                           // that nest's entrance on the surface
                ta = S16(st.U16(T, off));
                tb = S16(st.U16(T, off + 2));
            }
        }
        else if (tv != view)
        {
            int off = view == 2 ? 0x2a4 : 0x2a8;                             // this nest's exit column, row 0
            ta = S16(st.U16(T, off));
            tb = S16(st.U16(T, off + 2));
        }
        return PathStep(st, view, a, b, ta, tb);
    }

    // ------------------------------------------------------------------------------------------- acting on a cell
    // Carrying castes are odd: 1 brood (type T:0C22), 3 / 7 food, 5 / 9 a pebble. Drops go to the free
    // neighbour first in the order T:006C from the heading towards the target, else the yellow ant's own cell.
    // Holding Shift and Alt (BIOS keyboard flags 0000:0417, st.BiosKbd) keeps the load: a hidden cheat.
    /// <summary>SetTile f_1183e.</summary>
    public static void SetTile(State st, int view, int a, int b, int v)
    {
        if (!InView(view, a, b)) return;
        if (0 <= view && view <= 3)
        {
            int @base = view <= 1 ? SURFACE : Nest_(view).Dirt;
            st.SetGrid(@base, a, b, v);
        }
        st.Hooks.Effect(st, "redraw", view, a, b);                         // f_0250e
    }

    static bool Cheat(State st)
    {
        int k = st.BiosKbd & 0xff;
        return (k & 3) != 0 && (k & 8) != 0;
    }

    /// <summary>f_11327: the top-most ant at (a, b) with type t, -1 if none.</summary>
    public static int FindAntExact(State st, int view, int a, int b, int t)
    {
        var f = Ants(view);
        int i = S16(st.U16(G, f.Count));
        while (i > 0)
        {
            i--;
            if (st.U8(SIM, f.X + i) == a && st.U8(SIM, f.Y + i) == b && st.U8(SIM, f.Type + i) == t) return i;
        }
        return -1;
    }

    /// <summary>The search shared by the drops: (heading, a, b, result) of the first neighbour (empty and ok)
    /// in the order T:006C, else the yellow ant's own cell if ok; null if nowhere.</summary>
    static (int h, int x, int y, int r)? DropSpot(State st, int view, int ya, int yb, int ta, int tb, Func<int, int, int?> ok)
    {
        int d = Mv.DirTo(ya, yb, ta, tb);
        int h = d > 0 ? d - 1 : st.U16(G, 0x496);
        for (int k = 0; k < 8; k++)
        {
            int dd = (st.U8(T, 0x6c + k) + h) & 7;
            int x = ya + st.S8(T, dd), y = yb + st.S8(T, 8 + dd);
            if (InView(view, x, y) && GetOcc(st, view, x, y) < 0)
            {
                var r = ok(x, y);
                if (r.HasValue) return (dd, x, y, r.Value);
            }
        }
        if (InView(view, ya, yb))
        {
            var r = ok(ya, yb);
            if (r.HasValue) return (h, ya, yb, r.Value);
        }
        return null;
    }

    /// <summary>f_12306 (type 0x18 / 0x38): add the food to a crumb (up to 3 more) or put a new one down.</summary>
    public static int DropFood(State st, int view, int ya, int yb, int ta, int tb)
    {
        int c = st.U16(G, 0x4c2);
        if (c != 0x18 && c != 0x38) return 0;
        int? Ok(int x, int y)
        {
            int t = GetTile(st, view, x, y);
            if (IsFood(st, view, t) && (t & 3) < 3) return t + 1;
            if (IsOpenGround(st, view, x, y) || t == 0x38) return 0x10;
            return null;
        }
        var spot = DropSpot(st, view, ya, yb, ta, tb, Ok);
        if (spot == null) return 0;
        var (h, sx, sy, st2) = spot.Value;
        st.Set16(G, 0x496, h);
        if (view <= 1) World.SpiderDropFood(st, sx, sy);                    // f_0c692
        else
        {
            SetTile(st, view, sx, sy, st2);
            st.Inc16(G, view == 2 ? 0x1050 : 0x1060);
        }
        if (!Cheat(st)) st.Set16(G, 0x4c2, st.U16(G, 0x4c2) & 0xf7);
        st.Hooks.Effect(st, "sound", 0x1d);
        return 1;
    }

    /// <summary>f_1252c: a pebble on an entrance blocks the nest cell below (0x31) and vice versa.</summary>
    public static void PutPebble(State st, int view, int a, int b)
    {
        int t;
        if (view <= 1)
        {
            if (AtExit(st, view, a, b))
            {
                if (a < 0x40 && st.U8(T, 0x224 + b) == a) st.SetGrid(Nest.BLACK.Dirt, b, 0, 0x31);
                else if (st.U8(T, 0x264 + b) == a) st.SetGrid(Nest.RED.Dirt, b, 0, 0x31);
            }
            t = 0x51;
        }
        else if (AtExit(st, view, a, b))
        {
            st.SetGrid(SURFACE, st.U8(T, (view == 2 ? 0x224 : 0x264) + a), a, 0x51);
            t = 0x31;
        }
        else
            t = 0x30;
        SetTile(st, view, a, b, t);
    }

    /// <summary>f_12606 (type 0x28 / 0x48).</summary>
    public static int DropPebble(State st, int view, int ya, int yb, int ta, int tb)
    {
        int c = st.U16(G, 0x4c2);
        if (c != 0x28 && c != 0x48) return 0;
        int? Ok(int x, int y)
        {
            if (IsOpenGround(st, view, x, y)) return 1;
            int t = GetTile(st, view, x, y);
            if (IsFood(st, view, t) || IsRock(view, t)) return null;
            if (AtExit(st, view, x, y) || t == 0x38) return 1;
            return null;
        }
        var spot = DropSpot(st, view, ya, yb, ta, tb, Ok);
        if (spot == null) return 0;
        var (h, x, y, _) = spot.Value;
        st.Set16(G, 0x496, h);
        PutPebble(st, view, x, y);
        c = st.U16(G, 0x4c2);
        if (!Cheat(st) && (c == 0x28 || c == 0x48)) st.Inc16(G, 0x4c2, -0x18);
        st.Hooks.Effect(st, "sound", 0x1e);
        return 1;
    }

    /// <summary>f_12820 (type 0x08): the carried brood (type T:0C22) becomes an ant again (state 8).</summary>
    public static int DropBrood(State st, int view, int ya, int yb, int ta, int tb)
    {
        if (st.U16(G, 0x4c2) != 8) return 0;
        int? Ok(int x, int y) => IsOpenGround(st, view, x, y) || GetTile(st, view, x, y) == 0x38 ? 1 : null;
        var spot = DropSpot(st, view, ya, yb, ta, tb, Ok);
        if (spot == null) return 0;
        var (h, x, y, _) = spot.Value;
        if (AddAnt(st, view, x, y, st.U16(T, 0xc22), 8, 0) == 0) return 0;
        st.Set16(G, 0x496, h);
        if (!Cheat(st))
        {
            st.Set16(G, 0x4c2, 0x10);
            st.Set16(T, 0xc22, 0xfd);
        }
        PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), st.U16(G, 0x4c2), st.U16(G, 0x496), 0xff);
        st.Hooks.Effect(st, "sound", 0x1c);
        return 1;
    }

    /// <summary>f_1317c: drop whatever the yellow ant carries towards (ta, tb).</summary>
    public static int DropLoad(State st, int view, int ya, int yb, int ta, int tb)
    {
        int t = st.U16(G, 0x4c2);
        if (t == 0x08) return DropBrood(st, view, ya, yb, ta, tb);
        if (t == 0x18 || t == 0x38) return DropFood(st, view, ya, yb, ta, tb);
        if (t == 0x28 || t == 0x48) return DropPebble(st, view, ya, yb, ta, tb);
        return 0;
    }

    /// <summary>f_12bf4: (type, index) of the brood at (a, b), (-1, -1) if none.</summary>
    public static (int t, int i) BroodAt(State st, int view, int a, int b)
    {
        int o = GetOcc(st, view, a, b);
        if (IsBrood(o) && !Mv.IsYellow(o)) return (o, FindAntExact(st, view, a, b, o));
        int i = FindAnt(st, view, a, b, 1, 7, 0x7f);
        if (i >= 0) return (GetAnt(st, view, i).Value.t, i);
        return (-1, -1);
    }

    /// <summary>f_12f4f: a plain worker picks up brood; a weak yellow ant (health &lt; 10) eats it instead.</summary>
    public static int TakeBrood(State st, int view, int a, int b)
    {
        if (st.U16(G, 0x4c2) != 0x10 && Hp(st) >= 10) return 0;
        st.Set16(T, 0xc22, 0xfd);
        var (t, i) = BroodAt(st, view, a, b);
        if (t < 0) return 0;
        SetAnt(st, view, i, 0, 0, 0, 0, 0);
        if (G16(st, 0x47c) != a || G16(st, 0x48a) != b) SetOcc(st, view, a, b, 0);
        if (Hp(st) >= 10)
        {
            st.Hooks.Effect(st, "sound", 0x1c);
            st.Set16(T, 0xc22, t);
            st.Set16(G, 0x4c2, 8);
        }
        else
            st.Set16(T, 0xc26, 3);                                           // eat it (MenuCommand12de1(3))
        return 1;
    }

    /// <summary>f_12a1e: a plain worker or soldier picks up a pebble (one blocking an entrance reopens it).</summary>
    public static int TakePebble(State st, int view, int a, int b)
    {
        int c = st.U16(G, 0x4c2);
        if (c != 0x10 && c != 0x30) return 0;
        int t = GetTile(st, view, a, b);
        bool picked = false;
        if (view <= 1)
        {
            if (IsRock(view, t))
            {
                bool blocking = false;
                if (a < 0x40)
                {
                    if (st.U8(T, 0x224 + b) == a)
                    {
                        st.SetGrid(Nest.BLACK.Dirt, b, 0, 0x18);
                        blocking = true;
                    }
                }
                else if (st.U8(T, 0x264 + b) == a)
                {
                    st.SetGrid(Nest.RED.Dirt, b, 0, 0x18);
                    blocking = true;
                }
                if (blocking) st.SetGrid(SURFACE, a, b, st.U16(G, 0xf24) == 0 ? 0x50 : st.Rand(7) + 0x59);
                else st.SetGrid(SURFACE, a, b, st.U16(G, 0xf24) == 0 ? st.Rand16() : 0);
                picked = true;
            }
        }
        else if (t == 0x30)
        {
            SetTile(st, view, a, b, st.Rand8());
            picked = true;
        }
        else if (t == 0x31)
        {
            var n = view == 2 ? Nest.BLACK : Nest.RED;
            st.SetGrid(n.Dirt, a, b, 0x18);
            st.SetGrid(SURFACE, st.U8(T, n.Entr + a), a, 0x50);
            picked = true;
        }
        if (picked)
        {
            st.Set16(G, 0x4c2, st.U16(G, 0x4c2) == 0x10 ? 0x28 : 0x48);
            st.Hooks.Effect(st, "sound", 0x1e);
        }
        return picked ? 1 : 0;
    }

    /// <summary>f_1302f: pick up food (laying the black food trail on the surface); with low health eat it.</summary>
    public static int TakeFood(State st, int view, int a, int b)
    {
        if (!FoodAt(st, view, a, b)) return 0;
        bool eat = st.U16(G, 0x1044) != 0;
        int c = st.U16(G, 0x4c2);
        if (!eat && c != 0x10 && c != 0x30) return 0;
        if (view <= 1)
        {
            Mv.TakeFoodAt(st, a, b);
            if (!eat)
            {
                st.Set16(G, 0x4c4, 200);
                int d = (int)(Co.Distance(a, b, S16(st.U16(T, 0x2ac)), S16(st.U16(T, 0x2ae))) & 0xffff);
                st.Set16(G, 0xb1e, d);
                st.Set16(G, 0xc38, d + 1);
                Ph.LayMax(st, Ph.BLACK_TRAIL, a, b, st.U16(G, 0x4c4));
            }
        }
        else
        {
            int t = GetTile(st, view, a, b);
            SetTile(st, view, a, b, t == 0x10 ? st.Rand8() : t - 1);
            int food = view == 2 ? 0x1050 : 0x1060;
            if (G16(st, food) > 0) st.Inc16(G, food, -1);
        }
        if (eat) st.Set16(T, 0xc26, 0);                                     // eat it (MenuCommand12de1(0))
        else
        {
            st.Hooks.Effect(st, "sound", 0x1d);
            st.Inc16(G, 0x4c2, 8);
        }
        return 1;
    }

    /// <summary>f_131ea: brood, else a pebble, else food.</summary>
    public static int PickUp(State st, int view, int a, int b)
    {
        if ((st.U8(G, 0x4c2) & 8) != 0) return 0;
        int r = TakeBrood(st, view, a, b);
        if (r != 0) return r;
        r = TakePebble(st, view, a, b);
        if (r != 0) return r;
        return TakeFood(st, view, a, b);
    }

    /// <summary>MenuCommand12de1: n 0 eat food, 3 eat brood (both feed the colony with the old health), 1 / 2
    /// other menu actions (2 costs 10 health). Pictures and messages go to effects.</summary>
    public static void Eat(State st, int n)
    {
        st.Hooks.Effect(st, "menu", n);                                    // f_2f802 / f_2f82a / f_15e2c
        if (n == 1 || n == 3)
        {
            st.Set16(G, 0x474, 0);
            st.Set16(G, 0x472, 0);
        }
        int hp;
        if (n == 2)
        {
            hp = Hp(st);
            if (hp > 10) SetHealth(st, hp - 10);
            return;
        }
        hp = Hp(st);
        if (S16(hp + 100) > 100 && n != 1)
        {
            int k = S16(st.U16(G, 0x330) - 1);
            if (k > 0)
            {
                st.Inc16(G, 0x10be, CDiv(hp, k));
                if (G16(st, 0x10be) > 100) st.Set16(G, 0x10be, 100);
            }
        }
        SetHealth(st, 100);
    }

    /// <summary>f_14f59: a new queen opens a nest entrance at (a, b) (black on the left half, red on the right).</summary>
    public static void FoundNest(State st, int a, int b)
    {
        if (!(1 <= a && a < 0x7f && 1 <= b && b < 0x3f)) return;
        if (st.U16(G, 0xf24) != 0) st.SetGrid(SURFACE, a, b, 0x59);
        else
        {
            st.SetGrid(SURFACE, a, b, 0x50);
            Nest.EntranceRing(st, a, b);
        }
        if (a < 0x40)
        {
            st.Set8(T, 0x224 + b, a);
            Ng.DigAt(st, Ng.BLACK, b, 1);
            st.Set16(T, 0x2ac, a);
            st.Set16(T, 0x2ae, b);
            st.Set16(T, 0x2a4, b);
            st.Set16(T, 0x2a6, 0);
        }
        else
        {
            st.Set8(T, 0x264 + b, a);
            Ng.DigAt(st, Ng.RED, b, 1);
            st.Set16(T, 0x2b0, a);
            st.Set16(T, 0x2b2, b);
            st.Set16(T, 0x2a8, b);
            st.Set16(T, 0x2aa, 0);
        }
    }

    /// <summary>f_14ee2: found a nest here if there is room (open 3x3 in the yard; any tile &lt; 0xC8 in the house).</summary>
    public static int TryFoundNest(State st, int a, int b)
    {
        if (!(1 <= a && a <= 0x7f && 1 <= b && b <= 0x3f)) return 0;
        bool ok = st.U16(G, 0xf24) == 0 ? Nest.IsOpenWithRing(st, a, b) : st.Grid(SURFACE, a, b) < 0xc8;
        if (ok)
        {
            FoundNest(st, a, b);
            return 1;
        }
        return 0;
    }

    /// <summary>f_13644: the yellow ant acts on the target cell next to (or under) it. 1 done, -1 failed, 0 nothing.</summary>
    public static int ActOnCell(State st, int view, int a, int b)
    {
        int ya = G16(st, 0x47c), yb = G16(st, 0x48a);
        if ((st.U8(G, 0x4c2) & 8) != 0) return DropLoad(st, view, ya, yb, a, b) != 0 ? 1 : -1;
        if (PickUp(st, view, a, b) == 0)
        {
            int t = st.U16(G, 0x4c2);
            if ((st.U16(T, 0x798) != 0 || (t == 0x40 && st.U16(T, 0xc24) == 0)) && view == 1 && ya == a && yb == b)
            {
                if (TryFoundNest(st, a, b) != 0)
                {
                    EnterNest(st);                                          // f_2f834
                    UiFollow(st);                                           // f_01c52
                    return 1;
                }
                return -1;
            }
            return 0;
        }
        int d = Mv.DirTo(ya, yb, a, b);
        if (d > 0) MoveYellow(st, G16(st, 0x48c), ya, yb, G16(st, 0x4c2), d - 1);
        st.Hooks.Effect(st, "redraw_all");                                  // f_03391
        int c = S16(st.U16(T, 0xc26));
        if (c >= 0)
        {
            Eat(st, c);
            st.Set16(T, 0xc26, 0xffff);
        }
        return 1;
    }

    /// <summary>f_01c52: G:1074 = 1 and the view scrolls to the yellow ant (f_01aa7, screen only).</summary>
    public static void UiFollow(State st)
    {
        st.Set16(G, 0x1074, 1);
        st.Hooks.Effect(st, "follow");
    }
}
