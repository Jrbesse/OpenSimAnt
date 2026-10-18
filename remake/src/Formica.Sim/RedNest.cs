using static Formica.Sim.Seg;
using static Formica.Sim.Bits;
using Mv = Formica.Sim.Movement;
using Ng = Formica.Sim.NestGrid;
using Bn = Formica.Sim.Nest;
using Sf = Formica.Sim.Surface;

namespace Formica.Sim;

/// <summary>Red nest ants: the per-tick loop and state handlers (SIMANT.EXE resident segment 1f3f,
/// f_0f3f8..f_10e27). The red nest code is a separate copy of the black one with its own rules: no Defense
/// job inside, nurses only shuffle brood around, brood hatch into a caste picked from the red priority,
/// diggers can break through into the black nest, and fights / invader handling differ in detail. Nest
/// helpers shared with the black nest are in Nest and take the colony as a parameter.</summary>
public static class RedNest
{
    static readonly NestKind N = Bn.RED;
    static readonly int DIRT = N.Dirt, EXITF = N.Exitf, CELLS = N.Cells;
    static readonly int RX = N.X, RY = N.Y, RSTATE = N.State, RTYPE = N.Type, RE = N.E;

    static int Cur(State st) => st.U16(G, 0xf18);

    static int Get(State st, int f, int i) => st.U8(SIM, f + i);

    static void Set(State st, int f, int i, int v) => st.Set8(SIM, f + i, v);

    /// <summary>f_14260: StateForCaste for a red ant.</summary>
    static int Job(State st, int caste) => Mv.StateForCaste(st, caste, 0x80);

    static int Health(State st) => S16(st.U16(G, 0x1fe));

    /// <summary>f_1082c (unlike the black one, not gated by T:0c18).</summary>
    public static void EggCost(State st)
    {
        st.Inc16(G, 0x226, -1);
        if (S16(st.U16(G, 0x226)) < 0)
        {
            st.Set16(G, 0x226, S16(st.U16(G, 0x350)) >> 5);
            if (Health(st) > 0) st.Inc16(G, 0x1fe, -1);
        }
    }

    /// <summary>f_0fce6: fight a black ant (castes 1..12, not brood) or the black-side yellow ant here. 1 if so.</summary>
    public static int FightAt(State st, int col, int depth, int t)
    {
        int o = st.Grid(CELLS, col, depth);
        if (o < 8 || o > 0x67)
        {
            if (!Mv.IsYellow(o) || st.U16(G, 0x4e2) != 0) return 0;
            st.Hooks.AttackPlayer(st, 3, Cur(st));
            return 1;
        }
        int i = Bn.NestAntAt(st, N, col, depth, o);
        if (i < 0) return 0;
        int w = Sf.ResolveFight(st, o, t & 0xff);
        Set(st, RE, i, w);
        int nt = ((w & 0x80) + 0x70) & 0xff;
        Set(st, RTYPE, i, nt);
        st.SetGrid(CELLS, col, depth, nt);
        Set(st, RSTATE, i, 10);
        return 1;
    }

    /// <summary>Step into (c, r) unless a fight breaks out there. False = fought.</summary>
    static bool Enter(State st, int col, int depth, int c, int r, int d, int nt)
    {
        st.SetGrid(CELLS, col, depth, 0);
        if (FightAt(st, c, r, nt) != 0) return false;
        int cur = Cur(st);
        int v = (Get(st, RTYPE, cur) & 0xf8) | d;
        Set(st, RTYPE, cur, v);
        st.SetGrid(CELLS, c, r, v);
        Set(st, RX, cur, c);
        Set(st, RY, cur, r);
        return true;
    }

    // ------------------------------------------------------------------------------------------- queen
    /// <summary>f_1010b: as the black QueenMove, towards the red centroid.</summary>
    public static int QueenMove(State st, int col, int depth, int t)
    {
        int d = Bn.StepTowardsNest(st, N, col, depth, S16(st.U16(G, 0x200)), S16(st.U16(G, 0x20e)));
        if (d < 0)
        {
            if (d == -1) return 0;
            d = st.Rand8();
        }
        if ((depth > 2 || (2 < d && d < 6)) && Bn.MoveTo(st, N, col, depth, d) != 0)
        {
            int back = (t ^ 0xfc) & 7;
            int c = Mv.Dx(st, back) + col, r = Mv.Dy(st, back) + depth;
            st.SetGrid(CELLS, c, r, 0);
            int i = Bn.NestAntAt(st, N, c, r, (t & 7) + 0xe8);
            if (i >= 0 && Get(st, RTYPE, i) != 0)
            {
                Set(st, RX, i, col);
                Set(st, RY, i, depth);
                Set(st, RTYPE, i, (d + 0xe8) & 0xff);
                st.SetGrid(CELLS, col, depth, (d + 0xe8) & 0xff);
            }
            return 1;
        }
        return 0;
    }

    /// <summary>f_10345.</summary>
    public static bool QueenHeadLost(State st, int col, int depth, int t)
    {
        int back = (t ^ 0xfc) & 7;
        int c = Mv.Dx(st, back) + col, r = Mv.Dy(st, back) + depth;
        return st.Grid(CELLS, c, r) != t + 8 && Bn.NestAntAt(st, N, c, r, t + 8) < 0;
    }

    /// <summary>f_102d4.</summary>
    public static bool QueenTailLost(State st, int col, int depth, int t)
    {
        int c = Mv.Dx(st, t & 7) + col, r = Mv.Dy(st, t & 7) + depth;
        return st.Grid(CELLS, c, r) != t - 8 && Bn.NestAntAt(st, N, c, r, t - 8) < 0;
    }

    /// <summary>f_10220.</summary>
    public static void AddAbdomen(State st, int i)
    {
        int t = Get(st, RTYPE, i);
        int back = (t & 7) ^ 4;
        Ng.AddNestAnt(st, N, Mv.Dx(st, back) + Get(st, RX, i), Mv.Dy(st, back) + Get(st, RY, i), (t + 8) & 0xff, 9, 0);
    }

    /// <summary>f_1028e.</summary>
    public static void RemoveAnt(State st, int i)
    {
        Set(st, RTYPE, i, 0);
        st.SetGrid(CELLS, Get(st, RX, i), Get(st, RY, i), 0);
    }

    // ------------------------------------------------------------------------------------------- handlers
    /// <summary>f_0fb71 (Bored, Pre-Flight and states > 17).</summary>
    public static void NWander(State st, int col, int depth, int t, int caste)
    {
        if (st.Rand32() == 0) Set(st, RSTATE, Cur(st), Job(st, caste));
        if (FightAt(st, col, depth, t) == 0) Bn.MoveOrRandom(st, N, col, depth, t & 7);
    }

    /// <summary>f_10491: red nurses put brood (always stage 2) down on open tunnel cells and pick brood up.</summary>
    public static void NNesting(State st, int col, int depth, int t, int caste)
    {
        int cur = Cur(st);
        int d = t & 7;
        if (caste == 1)
        {
            if (st.Rand4() == 0 && st.Grid(DIRT, col, depth) < 0x10)
            {
                Set(st, RTYPE, cur, Get(st, RTYPE, cur) + 8);
                st.SetGrid(CELLS, col, depth, Get(st, RTYPE, cur));
                Bn.SpawnBrood(st, N, col, depth, 0x82);
                Set(st, RE, cur, 0);
                Set(st, RSTATE, cur, Job(st, 1));
                return;
            }
            if (st.Rand4() != 0)
            {
                d = Bn.StepDir(st, N, col, depth, d);
                if (d >= 0)
                {
                    Bn.MoveOrRandom(st, N, col, depth, d);
                    return;
                }
            }
        }
        else if (caste != 2)
        {
            Set(st, RSTATE, cur, Job(st, caste));
            Bn.MoveOrRandom(st, N, col, depth, d);
            return;
        }
        else
        {
            if (st.Rand4() == 0)
            {
                int o = st.Grid(CELLS, col, depth);
                if (o == 0 || (o & 0x7f) > 7)
                {
                    if (S16(st.Rand(100)) > Health(st)) Bn.EatIfOnFood(st, N, col, depth);
                    else Set(st, RSTATE, cur, Job(st, 2));
                }
                else
                {
                    int i = Bn.NestAntAt(st, N, col, depth, o);
                    if (i >= 0)
                    {
                        Set(st, RTYPE, i, 0);
                        Set(st, RTYPE, cur, Get(st, RTYPE, cur) - 8);
                        return;
                    }
                }
            }
            if (st.Rand4() != 0)
            {
                Bn.MoveOrRandom(st, N, col, depth, d);
                return;
            }
        }
        Bn.MoveOrRandom(st, N, col, depth, st.Rand8());
    }

    /// <summary>f_10864: as the black one, but no eating on the way and fights decided by the red rules.</summary>
    public static void NGotFood(State st, int col, int depth, int t)
    {
        int d = Bn.StepDir(st, N, col, depth, t & 7);
        if (d < 0 || st.Rand16() == 0)
        {
            Bn.StoreFood(st, N, col, depth);
            if (S16(st.Rand(100)) > Health(st)) Bn.EatFood(st, N, col, depth);
            Set(st, RSTATE, Cur(st), Job(st, (t & 0x78) >> 3));
            return;
        }
        int nt = Bn.TurnTo(st, N, col, depth, t, d);
        int c = col + Mv.Dx(st, d), r = depth + Mv.Dy(st, d);
        if (c > 0x3f || c < 0 || r > 0x3f) return;
        if (r < 1)
        {
            Bn.ExitToSurface(st, N, col);
            return;
        }
        if (st.Grid(DIRT, c, r) >= 0x30) return;
        Enter(st, col, depth, c, r, d, nt);
    }

    /// <summary>f_109ec: as the black Dig In; a failed dig makes the ant Bored, it eats where it was, and
    /// stepping onto a 0x14 cell (where deep black digging broke through) sends it into the black nest as an
    /// invader.</summary>
    public static void NDigIn(State st, int col, int depth, int t, int caste)
    {
        int cur = Cur(st);
        if (caste != 2 && caste != 6)
        {
            Set(st, RSTATE, cur, Job(st, caste));
            return;
        }
        int d = Bn.StepDir(st, N, col, depth, t & 7);
        if (d < 0) d = st.Rand8();
        int nt = Bn.TurnTo(st, N, col, depth, t, d);
        if (depth == 0x3f)
        {
            Set(st, RSTATE, cur, Job(st, caste));
            return;
        }
        int r = depth + Mv.Dy(st, d), c = col + Mv.Dx(st, d);
        if (c > 0x3f || c < 0 || r > 0x3f) return;
        if (r < 1)
        {
            Bn.ExitToSurface(st, N, col);
            return;
        }
        int tile = st.Grid(DIRT, c, r);
        if (tile > 0x2f) return;
        if (Ng.IsDiggable(tile))
        {
            if (!Bn.DigCell(st, N, c, r))
            {
                Set(st, RSTATE, cur, 0);
                return;
            }
            Set(st, RTYPE, cur, Get(st, RTYPE, cur) + 0x18);
            Set(st, RSTATE, cur, 5);
            st.Hooks.Effect(st, "sound", 0x12);
        }
        if (!Enter(st, col, depth, c, r, d, nt)) return;
        int v = Get(st, RTYPE, cur);
        if (S16(st.Rand64()) > Health(st)) Bn.EatIfOnFood(st, N, col, depth);
        if (st.Rand4() == 0) Ng.UpdateExitField(st, N, c, r);
        if (st.Grid(DIRT, c, r) != 0x14) return;
        Set(st, RTYPE, cur, 0);
        st.SetGrid(CELLS, c, r, 0);
        nt = (st.Rand8() + ((v & 0x7f) < 0x30 ? 0x90 : 0xb0)) & 0xff;
        Ng.AddNestAnt(st, Bn.BLACK, c, r, nt, 3, 0);
        st.SetGrid(Bn.BLACK.Cells, c, r, nt);
    }

    /// <summary>f_10c5b: as the black one (eats at the cell it left; the dead-end counter does not wrap).</summary>
    public static void NGoToSurface(State st, int col, int depth, int t)
    {
        int c1 = Bn.ClimbDir(st, N, col, depth, t & 7);
        int d = c1 < 1 ? Mv.TurnAside(st, t & 7) : c1 - 1;
        int nt = Bn.TurnTo(st, N, col, depth, t, d);
        int c = col + Mv.Dx(st, d), r = depth + Mv.Dy(st, d);
        if (!(0 <= c && c < 0x40 && r < 0x40)) return;
        if (r < 1)
        {
            Bn.ExitToSurface(st, N, col);
            return;
        }
        int tile = st.Grid(DIRT, c, r);
        if (tile < 0x30)
        {
            if (!Ng.IsDiggable(tile) && Enter(st, col, depth, c, r, d, nt))
                if (S16(st.Rand64()) > Health(st)) Bn.EatIfOnFood(st, N, col, depth);
            return;
        }
        int v = st.Grid(EXITF, col, depth);
        if (v != 0) st.SetGrid(EXITF, col, depth, v - 1);
        int caste = (t & 0x78) >> 3;
        int cur = Cur(st);
        if (caste == 5 || caste == 9)
        {
            Set(st, RTYPE, cur, Get(st, RTYPE, cur) - 0x18);
            Set(st, RSTATE, cur, 4);
        }
        if (caste == 2 || caste == 6) Set(st, RSTATE, cur, 4);
    }

    /// <summary>f_0fe16: red brood never die of neglect; the hatch caste comes from T:0b36[priority % 7][Rand8].</summary>
    public static void NBrood(State st, int col, int depth)
    {
        int cur = Cur(st);
        int t = Get(st, RTYPE, cur);
        int caste = -1;
        int mask = st.U16(G, 0x350) == 1 ? 0x1f : 0x7f;
        if ((st.U16(G, 0xf08) & mask) == 0)
        {
            t++;
            if ((t & 0xf) == 8)
            {
                int r = st.Rand8();
                int p = S16(st.U16(G, 0x10a6));
                caste = st.S8(T, 0xb36 + CMod(p, 7) * 8 + r);
                t = caste * 8 + 0x82;
                Set(st, RSTATE, cur, Job(st, caste));
            }
        }
        if (st.U16(T, 0x7b2) != 0 && caste < 0) st.Hooks.Effect(st, "brood", col, depth, 3);
        st.SetGrid(CELLS, col, depth, t & 0xff);
        Set(st, RTYPE, cur, t & 0xff);
        Set(st, RE, cur, 0);
    }

    /// <summary>f_0ff0f: as the black queen (no eggs-laid counter).</summary>
    public static void NEggLaying(State st, int col, int depth, int caste, int t)
    {
        int cur = Cur(st);
        int v;
        if (caste == 12)
        {
            if (st.Rand64() == 0)
            {
                if (st.U16(G, 0x1fe) == 0)
                {
                    Set(st, RTYPE, cur, 0);
                    st.SetGrid(CELLS, col, depth, 0);
                    st.Hooks.Effect(st, "message", 0x1093, 0, 0x2720, 1);     // f_2f6ea: the red queen starved
                    return;
                }
                if (QueenMove(st, col, depth, t) != 0) return;
            }
            v = Get(st, RTYPE, cur);
            if (QueenHeadLost(st, col, depth, v))
            {
                v = 0;
                Set(st, RTYPE, cur, 0);
                st.Inc16(G, 0x36c, -1);
            }
            st.SetGrid(CELLS, col, depth, v);
            if (st.U16(T, 0x7b2) != 0) st.Hooks.Effect(st, "queen", col, depth, 3);
            return;
        }
        if (caste != 13) return;
        v = Get(st, RTYPE, cur);
        st.SetGrid(CELLS, col, depth, v);
        if (S16(st.U16(G, 0x36c)) > 0 && QueenTailLost(st, col, depth, v))
        {
            st.Inc16(G, 0x36c, -1);
            Set(st, RTYPE, cur, 0);
            st.SetGrid(CELLS, col, depth, 0);
            return;
        }
        int back = (t ^ 0xfc) & 7;
        int rr = Mv.Dy(st, back) + depth, c = Mv.Dx(st, back) + col;
        if (!Bn.NestCellFree(c, rr)) return;
        st.Set16(T, 0x2b8, c);
        st.Set16(T, 0x2ba, rr);
        if ((st.U16(G, 0xf08) & 0xf) != 0) return;
        if (S16(st.Rand128()) > Health(st)) return;
        Bn.SpawnBrood(st, N, c, rr, 0x81);
        EggCost(st);
    }

    /// <summary>f_0fbdd: like the black one; a black winner becomes Attack, a red one takes its job from DS:1ba2.</summary>
    public static void NFighting(State st, int col, int depth)
    {
        int cur = Cur(st);
        int j = st.Rand(7);
        Set(st, RTYPE, cur, ((Get(st, RTYPE, cur) & 0xf8) + j) & 0xff);
        st.SetGrid(CELLS, col, depth, Get(st, RTYPE, cur));
        if (st.Rand16() == 0)
        {
            int w = Get(st, RE, cur);
            st.SetGrid(CELLS, col, depth, w);
            Set(st, RTYPE, cur, w);
            if ((w & 0x78) == 0x60) AddAbdomen(st, cur);
            w = Get(st, RTYPE, cur);
            Set(st, RSTATE, cur, (w & 0x80) != 0 ? st.U8(DS, 0x1ba2 + ((w & 0x78) >> 3)) : 7);
        }
        else if (st.U16(T, 0x7b2) != 0)
            st.Hooks.Effect(st, "fight", col, depth, 3);
    }

    /// <summary>f_0f9de.</summary>
    public static void NResting(State st, int col, int depth, int t)
    {
        if (FightAt(st, col, depth, t) != 0) return;
        int cur = Cur(st);
        st.SetGrid(CELLS, col, depth, Get(st, RTYPE, cur));
        if (st.Rand(20) == 0)
        {
            int b = Get(st, RTYPE, cur);
            Set(st, RSTATE, cur, Mv.StateForCaste(st, (b & 0x78) >> 3, b));
        }
        else if (st.U16(T, 0x7b2) != 0)
            st.Hooks.Effect(st, "rest", col, depth, 3);
    }

    /// <summary>f_0fa8a.</summary>
    public static void NState17(State st, int col, int depth, int t)
    {
        int cur = Cur(st);
        if (st.Grid(DIRT, col, depth) < 0x14)
        {
            Set(st, RSTATE, cur, Job(st, (t & 0x78) >> 3));
            return;
        }
        int nt = (((st.Rand(3) + t - 1) & 7) | (t & 0xf8)) & 0xff;
        Set(st, RTYPE, cur, nt);
        st.SetGrid(CELLS, col, depth, nt);
        if (st.Rand(100) == 0)
        {
            st.SetGrid(CELLS, col, depth, 0);
            Set(st, RTYPE, cur, 0);
            st.Inc32(G, (t & 0x80) != 0 ? 0xfbc : 0xf30);
        }
    }

    // ------------------------------------------------------------------------------------------- invaders
    /// <summary>f_0f959: black invaders climb towards the exit.</summary>
    public static void NInvaderMove(State st, int col, int depth, int t)
    {
        int c = Bn.ClimbDir(st, N, col, depth, 8);
        int d = c == 0 ? st.Rand8() : c - 1;
        if (Bn.MoveTo(st, N, col, depth, d) == 0 && Bn.MoveTo(st, N, col, depth, st.Rand8()) == 0)
            st.SetGrid(CELLS, col, depth, Get(st, RTYPE, Cur(st)));
    }

    static void InvaderRaid(State st, int col, int depth, int t, bool guard)
    {
        int cur = Cur(st);
        int v = st.Grid(DIRT, col, depth);
        if (v < 0x10 || v > 0x13)
        {
            int d = (st.Rand(3) + t - 2) & 7;
            if (guard) Set(st, RTYPE, cur, (Get(st, RTYPE, cur) & 0xf8) | d);
            if (Bn.MoveTo(st, N, col, depth, d) != 0) return;
            d = Bn.StepDir(st, N, col, depth, t & 7);
            if (d < 0) d = st.Rand(8);
            if (Bn.MoveTo(st, N, col, depth, d) != 0) return;
            if (!guard) Set(st, RSTATE, cur, 1);
        }
        else
        {
            Bn.InvaderEatFood(st, N, col, depth);
            Set(st, RSTATE, cur, 3);
            Set(st, RTYPE, cur, Get(st, RTYPE, cur) | 8);
        }
        st.SetGrid(CELLS, col, depth, Get(st, RTYPE, cur));
    }

    /// <summary>f_0f7a0: black raiders look for red stores (like the red raiders in the black nest).</summary>
    public static void NInvaderAttack(State st, int col, int depth, int t) => InvaderRaid(st, col, depth, t, false);

    /// <summary>f_0f871: a black Defense ant in the red nest while the player watches it: raids without giving up.</summary>
    public static void NInvaderGuard(State st, int col, int depth, int t) => InvaderRaid(st, col, depth, t, true);

    /// <summary>f_0f465 RedNestAntTick.</summary>
    public static void NestAntTick(State st, int col, int depth, int t)
    {
        int caste = (t & 0x78) >> 3;
        int cur = Cur(st);
        int state = Get(st, RSTATE, cur);
        if ((t & 0x80) == 0)                                         // a black invader
        {
            st.Inc16(G, 0xd40 + state * 2);
            if (t < 8)
            {
                Set(st, RTYPE, cur, 0);
                st.SetGrid(CELLS, Get(st, RX, cur), Get(st, RY, cur), 0);
                return;
            }
            if (t > 0x6f)
            {
                NFighting(st, col, depth);
                return;
            }
            int o = st.Grid(CELLS, col, depth);
            if (0x80 < o && o < 0xe8)
            {
                int i = Bn.NestAntAt(st, N, col, depth, o);
                if (i >= 0)
                {
                    if (o > 0xdf) RemoveAnt(st, i);
                    if (o < 0x88)                                 // steal red brood
                    {
                        Set(st, RSTATE, cur, 3);
                        Set(st, RTYPE, cur, Get(st, RTYPE, cur) | 8);
                        st.SetGrid(CELLS, col, depth, Get(st, RTYPE, cur));
                        Set(st, RTYPE, i, 0);
                        return;
                    }
                    int w = Sf.ResolveFight(st, Get(st, RTYPE, i), t);
                    Set(st, RTYPE, cur, 0);
                    Set(st, RE, i, w);
                    int nt = ((w & 0x80) + 0x70) & 0xff;
                    Set(st, RTYPE, i, nt);
                    st.SetGrid(CELLS, col, depth, nt);
                    Set(st, RSTATE, i, 10);
                    return;
                }
            }
            if (state == 6 && st.U16(G, 0x48c) == 3) NInvaderGuard(st, col, depth, t);
            else if (state == 7) NInvaderAttack(st, col, depth, t);
            else NInvaderMove(st, col, depth, t);
            return;
        }
        st.Inc16(G, 0xd72 + state * 2);
        if (st.Rand256() == 0 && state != 9 && S16(st.Rand32()) > Health(st))
        {
            Set(st, RTYPE, cur, 0);
            st.SetGrid(CELLS, col, depth, 0);
            st.Inc32(G, 0xfbc);
            return;
        }
        if (state > 0x11 || state == 0) NWander(st, col, depth, t, caste);
        else if (state == 1) NNesting(st, col, depth, t, caste);
        else if (state == 3) NGotFood(st, col, depth, t);
        else if (state == 4) NDigIn(st, col, depth, t, caste);
        else if (state == 8) NBrood(st, col, depth);
        else if (state == 9) NEggLaying(st, col, depth, caste, t);
        else if (state == 10) NFighting(st, col, depth);
        else if (state == 13) NResting(st, col, depth, t);
        else if (state == 14)
        {
            NWander(st, col, depth, t, caste);
            if (S16(st.U16(G, 0x8e8)) > 100) Set(st, RSTATE, Cur(st), 15);
        }
        else if (state == 17) NState17(st, col, depth, t);
        else NGoToSurface(st, col, depth, t);
    }

    /// <summary>f_0f3f8 RedNestLoop.</summary>
    public static void RedNestLoop(State st)
    {
        st.Set16(G, 0xf18, st.U16(G, 0xeaa));
        while (S16(st.U16(G, 0xf18)) > 0)
        {
            st.Inc16(G, 0xf18, -1);
            int i = st.U16(G, 0xf18);
            int t = Get(st, RTYPE, i);
            if (t != 0) NestAntTick(st, Get(st, RX, i), Get(st, RY, i), t);
        }
    }
}
