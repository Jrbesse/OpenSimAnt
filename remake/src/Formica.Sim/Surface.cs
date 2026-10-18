using static Formica.Sim.Seg;
using static Formica.Sim.Bits;
using Mv = Formica.Sim.Movement;
using Ph = Formica.Sim.Pheromones;
using Ng = Formica.Sim.NestGrid;

namespace Formica.Sim;

/// <summary>Surface ants: the per-tick dispatcher and the 20 state handlers (SIMANT.EXE segment 0894 and
/// helpers). Ants are structure-of-arrays in the SIM segment; the occupancy grid holds each ant's type byte
/// (bit 7 red, bits 3-6 caste, bits 0-2 heading). Player (yellow ant) interactions call st.Hooks.</summary>
public static class Surface
{
    public const int SURFACE = 0x0180, OCC = 0x6180;
    public const int SX = 0xa180, SY = 0xa569, SSTATE = 0xa952, STYPE = 0xad3b, SE = 0xb124;

    static int Get(State st, int f, int i) => st.U8(SIM, f + i);

    static void Set(State st, int f, int i, int v) => st.Set8(SIM, f + i, v);

    static bool IsWorkerOrSoldierForager(int caste) => caste == 6 || caste == 2;

    // ------------------------------------------------------------------------------------------- combat
    /// <summary>f_0a774: returns the winner's type byte; the outcome is decided at contact.</summary>
    public static int ResolveFight(State st, int defT, int attT)
    {
        if (st.U16(T, 0xc14) == 1)
        {
            st.Inc32(G, 0xf3e);
            return (defT & 0x80) != 0 ? attT : defT;
        }
        int r = st.CrtRandMod(10);
        int odds = st.U8(DS, 0x1b82 + st.U8(DS, 0x1b72 + ((defT & 0x78) >> 3)) * 4
                             + st.U8(DS, 0x1b72 + ((attT & 0x78) >> 3)));
        int winner = r < odds ? defT : attT;
        if ((winner & 0x80) == 0)          // a black winner counts a red death, and vice versa
        {
            st.Inc16(G, 0xa00);
            st.Inc32(G, 0xf3e);
        }
        else
        {
            st.Inc16(G, 0x9fa);
            st.Inc32(G, 0xefc);
        }
        return winner;
    }

    /// <summary>f_0a961: corpse ring buffer (100 slots); the oldest corpse turns back into ground.</summary>
    public static void PlaceCorpse(State st, int a, int b, bool red)
    {
        int idx = st.U16(G, 0x476) + 1;
        st.Set16(G, 0x476, idx);
        if (S16(idx) > 99)
        {
            st.Set16(G, 0x476, 0);
            idx = 0;
        }
        int oa = st.U8(G, 0x37c + idx), ob = st.U8(G, 0x404 + idx);
        int old = st.Grid(SURFACE, oa, ob);
        bool house = st.U16(G, 0xf24) != 0;
        if (!house)
        {
            if (0x0f < old && old < 0x18) st.SetGrid(SURFACE, oa, ob, st.Rand16());
        }
        else if (7 < old && old < 0x18)
            st.SetGrid(SURFACE, oa, ob, (old - 8) >> 2);
        st.Set8(G, 0x37c + idx, a);
        st.Set8(G, 0x404 + idx, b);
        int t = st.Grid(SURFACE, a, b);
        if (!house)
        {
            if (t <= 0x17) st.SetGrid(SURFACE, a, b, red ? st.Rand4() + 0x14 : st.Rand4() + 0x10);
        }
        else if (t <= 3)
        {
            if (!red) st.SetGrid(SURFACE, a, b, (t + 2) * 4 + st.Rand(2));
            else st.SetGrid(SURFACE, a, b, st.Rand(2) + t * 4 + 10);
        }
        st.SetGrid(OCC, a, b, 0);
    }

    /// <summary>f_0a6c9: the attacker merges into the defender's slot as a 'Fight' entity.</summary>
    public static void EncounterEnemy(State st, int ant, int a, int b, int na, int nb)
    {
        int att = Get(st, STYPE, ant);
        Set(st, STYPE, ant, 0);
        st.SetGrid(OCC, a, b, 0);
        int d = Mv.SurfaceAntAt(st, na, nb);
        if (d < 0) return;
        int w = ResolveFight(st, Get(st, STYPE, d), att);
        int f = ((w & 0x80) + 0x70) & 0xff;
        Set(st, STYPE, d, f);
        st.SetGrid(OCC, na, nb, f);
        Set(st, SSTATE, d, 10);
        Set(st, SE, d, w);
        Ph.LayMax(st, Ph.ALARM, na, nb, 0x28);
    }

    // ------------------------------------------------------------------------------------------- nests
    /// <summary>f_0f047 AddSurfaceAnt: an ant leaving a nest appears on a free tile next to the entrance (a, b).
    /// The occupancy grid is not written. Ants fresh out of their own nest get a nest-marker countdown.</summary>
    public static int AddSurfaceAnt(State st, int a, int b, int t, int state, int e)
    {
        int na = 0, nb = 0;
        bool found = false;
        for (int d = 0; d < 8; d++)
        {
            na = a + Mv.Dx(st, d);
            nb = b + Mv.Dy(st, d);
            if (Mv.InPatch(na, nb) && st.Grid(SURFACE, na, nb) < 0x50) { found = true; break; }
        }
        if (!found) return 0;
        int i = st.U16(G, 0xd6a);
        Set(st, SX, i, na);
        Set(st, SY, i, nb);
        Set(st, STYPE, i, t);
        Set(st, SSTATE, i, state);
        if (state == 6) Set(st, SE, i, e);
        else
        {
            Set(st, SE, i, 0);
            if (state != 3 && state != 7 && (((t & 0x80) != 0 && a > 0x40) || ((t & 0x80) == 0 && a < 0x40)))
                Set(st, SE, i, 0x78);
        }
        if (S16(st.U16(G, 0xd6a)) >= 1000)
        {
            Ng.CompactSurface(st);
            if (S16(st.U16(G, 0xd6a)) >= 1000) return 1;
        }
        st.Inc16(G, 0xd6a);
        return 1;
    }

    /// <summary>f_0a5ae: the ant leaves the surface into the nest of that half of the patch (column = b).</summary>
    public static void EnterNest(State st, int a, int b, int ant)
    {
        int t = Get(st, STYPE, ant), state = Get(st, SSTATE, ant), e = Get(st, SE, ant);
        NestKind n;
        int entr;
        if (a < 0x40) { n = Ng.BLACK; entr = 0x224; }
        else { n = Ng.RED; entr = 0x264; }
        if (S16(st.U16(G, n.Count)) > 499) Ng.CompactNest(st, n);
        if (S16(st.U16(G, n.Count)) > 499) return;
        Ng.AddNestAnt(st, n, b, 1, ((t & 0xf8) + 4) & 0xff, state, e);
        if (st.U8(T, entr + b) != 0) Ng.DigAt(st, n, b, 1);
        Set(st, STYPE, ant, 0);
        st.SetGrid(OCC, a, b, 0);
    }

    // ------------------------------------------------------------------------------------------- moving
    /// <summary>Move into (a+dx, b+dy) facing nd; returns (na, nb).</summary>
    static (int, int) TryStep(State st, int ant, int a, int b, int nd, int cc)
    {
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        int v = (nd | cc) & 0xff;
        st.SetGrid(OCC, na, nb, v);
        Set(st, STYPE, ant, v);
        st.SetGrid(OCC, a, b, 0);
        Set(st, SX, ant, na);
        Set(st, SY, ant, nb);
        return (na, nb);
    }

    static void Turn(State st, int ant, int a, int b, int d, int cc)
    {
        int v = (Mv.TurnAside(st, d) | cc) & 0xff;
        Set(st, STYPE, ant, v);
        st.SetGrid(OCC, a, b, v);
    }

    static void LayNestMarker(State st, int ant, int na, int nb, int t)
    {
        int e = Get(st, SE, ant);
        if (e != 0)
        {
            e--;
            Set(st, SE, ant, e);
            Ph.LayMax(st, (t & 0x80) != 0 ? Ph.RED_NEST : Ph.BLACK_NEST, na, nb, e);
        }
    }

    static void Pickup(State st, int ant, int a, int b, int nd, int cc, int na, int nb)
    {
        int v = (nd | cc | 8) & 0xff;
        Set(st, STYPE, ant, v);
        st.SetGrid(OCC, a, b, v);
        Set(st, SSTATE, ant, 3);
        Mv.TakeFoodAt(st, na, nb);
        Set(st, SE, ant, 200);
    }

    /// <summary>Yellow ant / friend / enemy reaction used by Bored, Nesting and Foraging.</summary>
    static void BumpCommon(State st, int ant, int a, int b, int na, int nb, int nd, int t, int cc, int o,
                           bool stateOnFriend = false)
    {
        if (Mv.IsYellow(o))
        {
            if (((st.U8(G, 0x4e2) ^ t) & 0x80) != 0)
            {
                st.Hooks.AttackPlayer(st, 1, ant);
                return;
            }
            if (st.U16(G, 0x1044) == 1)
            {
                int v = (nd | cc) & 0xff;
                Set(st, STYPE, ant, v);
                st.SetGrid(OCC, a, b, v);
                st.Hooks.NudgePlayer(st, a, b, nd);
            }
            Turn(st, ant, a, b, t & 7, cc);
            return;
        }
        if (((o ^ t) & 0x80) != 0)
        {
            EncounterEnemy(st, ant, a, b, na, nb);
            return;
        }
        Turn(st, ant, a, b, t & 7, cc);
        if (stateOnFriend) Set(st, SSTATE, ant, Mv.StateForCaste(st, (t >> 3) & 15, t));
    }

    /// <summary>f_09334 (state 0).</summary>
    public static void SBored(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        int cc = t & 0xf8, caste = (t & 0x78) >> 3;
        int nd = Mv.NextDir(st, a, b, t & 7);
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        int tile = st.Grid(SURFACE, na, nb);
        if (Mv.IsFood(st, tile))
        {
            if (IsWorkerOrSoldierForager(caste))
            {
                Pickup(st, ant, a, b, nd, cc, na, nb);
                return;
            }
        }
        else if (S16(st.U16(G, 0x480)) < tile)
        {
            Turn(st, ant, a, b, t & 7, cc);
            return;
        }
        int o = st.Grid(OCC, na, nb);
        if (o == 0)
        {
            TryStep(st, ant, a, b, nd, cc);
            LayNestMarker(st, ant, na, nb, t);
            Ph.WearTrail(st, na, nb, (t & 0x80) != 0);
            if (st.Rand8() == 0 && IsWorkerOrSoldierForager(caste)) Set(st, SSTATE, ant, 2);
            return;
        }
        BumpCommon(st, ant, a, b, na, nb, nd, t, cc, o, stateOnFriend: true);
    }

    /// <summary>f_099c7 (states 1 Nesting, 4 Dig In on the surface): head home.</summary>
    public static void SNesting(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        int cc = t & 0xf8, caste = (t & 0x78) >> 3;
        int nd = Mv.HomeDir(st, a, b, t & 7, t);
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        int tile = st.Grid(SURFACE, na, nb);
        if (Mv.IsFood(st, tile))
        {
            if (IsWorkerOrSoldierForager(caste))
            {
                Pickup(st, ant, a, b, nd, cc, na, nb);
                return;
            }
        }
        else if (S16(st.U16(G, 0x480)) < tile)
        {
            Turn(st, ant, a, b, t & 7, cc);
            return;
        }
        int o = st.Grid(OCC, na, nb);
        if (o == 0)
        {
            TryStep(st, ant, a, b, nd, cc);
            LayNestMarker(st, ant, na, nb, t);
            return;
        }
        BumpCommon(st, ant, a, b, na, nb, nd, t, cc, o);
    }

    /// <summary>f_09fe5 (state 2).</summary>
    public static void SForaging(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        if (st.Rand32() == 0)
        {
            Set(st, SSTATE, ant, 13);
            return;
        }
        int cc = t & 0xf8, caste = (t & 0x78) >> 3;
        if (Ph.Get(st, Ph.ALARM, (a & 0xfe) * 16 + (b >> 1)) != 0)
        {
            Set(st, SSTATE, ant, 11);
            return;
        }
        if (!IsWorkerOrSoldierForager(caste))
        {
            Set(st, SSTATE, ant, Mv.StateForCaste(st, caste, t));
            Set(st, SE, ant, 0);
            return;
        }
        int d = t & 7;
        int nd = Mv.ForageDir(st, a, b, d, t);
        if (nd < 0)                                       // lost
        {
            if (st.Rand8() == 0) Set(st, SSTATE, ant, Mv.StateForCaste(st, caste, t));
            else Set(st, SSTATE, ant, 0);
            Set(st, SE, ant, 0);
            Ph.WearTrail(st, a >> 1, b >> 1, (t & 0x80) != 0);  // original quirk: halved coordinates
            return;
        }
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        int tile = st.Grid(SURFACE, na, nb);
        if (Mv.IsFood(st, tile))
        {
            Pickup(st, ant, a, b, nd, cc, na, nb);
            return;
        }
        if (S16(st.U16(G, 0x480)) < tile)
        {
            Turn(st, ant, a, b, d, cc);
            if (st.Rand16() != 0) return;
            Set(st, SSTATE, ant, Mv.StateForCaste(st, caste, t));
            Set(st, SE, ant, 0);
            return;
        }
        int o = st.Grid(OCC, na, nb);
        if (o != 0)
        {
            BumpCommon(st, ant, a, b, na, nb, nd, t, cc, o);
            return;
        }
        TryStep(st, ant, a, b, nd, cc);
        LayNestMarker(st, ant, na, nb, t);
        Ph.WearTrail(st, na, nb, (t & 0x80) != 0);
    }

    /// <summary>f_09e65 (state 3): carry food home, laying the food trail; ignores occupancy.</summary>
    public static void SGotFood(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        int cc = t & 0xf8;
        int nd = Mv.HomeDir(st, a, b, t & 7, t);
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        if (S16(st.U16(G, 0x480)) < st.Grid(SURFACE, na, nb))
        {
            Turn(st, ant, a, b, t & 7, cc);
            return;
        }
        TryStep(st, ant, a, b, nd, cc);
        int e = Get(st, SE, ant);
        if (e != 0)
        {
            e--;
            Set(st, SE, ant, e);
            Ph.LayMax(st, (t & 0x80) != 0 ? Ph.RED_TRAIL : Ph.BLACK_TRAIL, na, nb, e);
        }
    }

    /// <summary>f_097ce (state 5): wander with dirt, drop it 1/8 per tick.</summary>
    public static void SDigOut(State st, int ant)
    {
        int a = Get(st, SX, ant), b = Get(st, SY, ant);
        int t = Get(st, STYPE, ant);
        int cc = t & 0xf8, caste = (t & 0x78) >> 3;
        int nd = Mv.Walk(st, t & 7, st.Rand8());
        int e = Mv.EdgeDir(a, b, st);
        if (e != 0) nd = (e - 1) & 7;
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        if (caste != 5 && caste != 9)
        {
            Set(st, SSTATE, ant, Mv.StateForCaste(st, caste, t));
            Set(st, SE, ant, 0);
            return;
        }
        if (st.Rand8() == 0)
        {
            Set(st, STYPE, ant, (t - 0x18) & 0xff);
            Set(st, SSTATE, ant, Mv.StateForCaste(st, caste, t));
            Set(st, SE, ant, 0);
        }
        else if (st.Grid(SURFACE, na, nb) <= S16(st.U16(G, 0x480)) && st.Grid(OCC, na, nb) == 0)
        {
            TryStep(st, ant, a, b, nd, cc);
            LayNestMarker(st, ant, na, nb, t);
            return;
        }
        else
            Set(st, STYPE, ant, (Mv.TurnAside(st, t & 7) | cc) & 0xff);
        st.SetGrid(OCC, a, b, Get(st, STYPE, ant));
    }

    /// <summary>f_0a368 (state 6): guards / recruits.</summary>
    public static void SDefense(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        int cc = t & 0xf8;
        int nd;
        if (Ph.Get(st, Ph.ALARM, (a & 0xfe) * 16 + (b >> 1)) == 0)
            nd = t < 0x80 ? Mv.BlackGuardDir(st, a, b, t & 7) : Mv.RedGuardDir(st, a, b, t & 7);
        else
            nd = Mv.AlarmDir(st, a, b, t & 7);
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        if (S16(st.U16(G, 0x480)) < st.Grid(SURFACE, na, nb))
        {
            int v = (st.Rand8() | cc) & 0xff;
            Set(st, STYPE, ant, v);
        }
        else
        {
            int o = st.Grid(OCC, na, nb);
            if (o == 0)
            {
                TryStep(st, ant, a, b, nd, cc);
                return;
            }
            if (Mv.IsYellow(o))
            {
                if (((st.U8(G, 0x4e2) ^ t) & 0x80) != 0)
                {
                    st.Hooks.AttackPlayer(st, 1, ant);
                    return;
                }
                if (st.U16(G, 0x1044) != 0)
                {
                    int v = (nd | cc) & 0xff;
                    Set(st, STYPE, ant, v);
                    st.SetGrid(OCC, a, b, v);
                    st.Hooks.NudgePlayer(st, a, b, nd);
                }
                Turn(st, ant, a, b, t & 7, cc);
                return;
            }
            if (((o ^ t) & 0x80) != 0)
            {
                EncounterEnemy(st, ant, a, b, na, nb);
                return;
            }
            Set(st, STYPE, ant, (Mv.TurnAside(st, t & 7) | cc) & 0xff);
        }
        st.SetGrid(OCC, a, b, Get(st, STYPE, ant));
    }

    /// <summary>f_0ab2d (state 7): drop any load, march on the enemy nest.</summary>
    public static void SAttack(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        int caste = (t & 0x78) >> 3;
        if (st.U16(T, 0x74 + caste * 2) == 1)
            t = ((st.S8(T, 0x94 + caste) << 3) | (t & 0x87)) & 0xffff;
        int cc = t & 0xf8;
        int nd = Mv.HomeDir(st, a, b, t & 7, t ^ 0x80);
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        if (st.Grid(SURFACE, na, nb) <= S16(st.U16(G, 0x480)))
        {
            int o = st.Grid(OCC, na, nb);
            if (o == 0)
            {
                TryStep(st, ant, a, b, nd, cc);
                return;
            }
            if (Mv.IsYellow(o))
            {
                if (((st.U8(G, 0x4e2) ^ t) & 0x80) != 0)
                {
                    st.Hooks.AttackPlayer(st, 1, ant);
                    return;
                }
            }
            else if (((o ^ t) & 0x80) != 0)
            {
                EncounterEnemy(st, ant, a, b, na, nb);
                return;
            }
        }
        Turn(st, ant, a, b, t & 7, cc);
    }

    /// <summary>f_08eb2 (state 8).</summary>
    public static void SHatching(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        st.SetGrid(OCC, a, b, t);
        if (st.Rand(200) == 0)
        {
            Set(st, STYPE, ant, 0);
            st.SetGrid(OCC, a, b, 0);
        }
    }

    /// <summary>f_08f2e (state 9): a queen's abdomen (caste >= 13) on the surface vanishes if its head is gone.</summary>
    public static void SEggLaying(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        st.SetGrid(OCC, a, b, t);
        if ((t & 0x7f) > 0x67)
        {
            int d = t & 7;
            int ha = a + Mv.Dx(st, d), hb = b + Mv.Dy(st, d);
            if (((st.Grid(OCC, ha, hb) - t) & 0xffff) != 0xfff8 && Mv.SurfaceAntAt(st, ha, hb) < 0)
            {
                st.SetGrid(OCC, a, b, 0);
                Set(st, STYPE, ant, 0);
            }
        }
    }

    /// <summary>f_0a871 (state 10).</summary>
    public static void SFighting(State st, int ant)
    {
        int a = Get(st, SX, ant), b = Get(st, SY, ant);
        int t = ((Get(st, STYPE, ant) & 0xf8) + st.Rand(7)) & 0xff;
        Set(st, STYPE, ant, t);
        st.SetGrid(OCC, a, b, t);
        if (st.Rand16() == 0)
        {
            int w = Get(st, SE, ant);
            st.SetGrid(OCC, a, b, w);
            Set(st, STYPE, ant, w);
            int cur = st.U16(G, 0xf18);
            Set(st, SSTATE, cur, Mv.StateForCaste(st, (w & 0x78) >> 3, w));
            Set(st, SE, ant, 0);
            PlaceCorpse(st, a, b, (Get(st, STYPE, ant) & 0x80) != 0);
        }
        else if (st.U16(T, 0x7b2) == 1)
            st.Hooks.Effect(st, "fight", a, b, 1);
    }

    /// <summary>f_09c55 (state 11).</summary>
    public static void SAlarmed(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        int cc = t & 0xf8;
        if (Ph.Get(st, Ph.ALARM, (a & 0xfe) * 16 + (b >> 1)) == 0 && st.Rand4() == 0)
        {
            st.SetGrid(OCC, a, b, Get(st, STYPE, ant));
            Set(st, SSTATE, ant, Mv.StateForCaste(st, (t & 0x78) >> 3, t));
            return;
        }
        int nd = Mv.AlarmDir(st, a, b, t & 7);
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        if (st.Grid(SURFACE, na, nb) <= S16(st.U16(G, 0x480)))
        {
            int o = st.Grid(OCC, na, nb);
            if (o == 0)
            {
                TryStep(st, ant, a, b, nd, cc);
                return;
            }
            if (!Mv.IsYellow(o))
            {
                if (((o ^ t) & 0x80) != 0)
                {
                    EncounterEnemy(st, ant, a, b, na, nb);
                    return;
                }
            }
            else if (((st.U8(G, 0x4e2) ^ t) & 0x80) != 0)
            {
                st.Hooks.AttackPlayer(st, 1, ant);
                return;
            }
        }
        Turn(st, ant, a, b, t & 7, cc);
    }

    /// <summary>f_0963d.</summary>
    public static void Wander(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        int cc = t & 0xf8;
        int nd = Mv.NextDir(st, a, b, t & 7);
        int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
        if (st.Grid(SURFACE, na, nb) <= S16(st.U16(G, 0x480)))
        {
            int o = st.Grid(OCC, na, nb);
            if (o == 0)
            {
                TryStep(st, ant, a, b, nd, cc);
                return;
            }
            if (Mv.IsYellow(o))
            {
                if (((st.U8(G, 0x4e2) ^ t) & 0x80) != 0)
                {
                    st.Hooks.AttackPlayer(st, 1, ant);
                    return;
                }
            }
            else if (((t ^ o) & 0x80) != 0)
            {
                EncounterEnemy(st, ant, a, b, na, nb);
                return;
            }
        }
        Turn(st, ant, a, b, t & 7, cc);
    }

    static int HomeMarker(State st, int ant)
    {
        int a = Get(st, SX, ant), b = Get(st, SY, ant), t = Get(st, STYPE, ant);
        var m = (t & 0x80) != 0 ? Ph.RED_NEST : Ph.BLACK_NEST;
        return Ph.Get(st, m, (a & 0xfe) * 16 + (b >> 1));
    }

    /// <summary>f_092a1 (state 12).</summary>
    public static void SDefendNest(State st, int ant)
    {
        if (HomeMarker(st, ant) < 0x6e) SNesting(st, ant);
        else Wander(st, ant);
    }

    /// <summary>f_09018 (state 13).</summary>
    public static void SResting(State st, int ant)
    {
        int b = Get(st, SY, ant), a = Get(st, SX, ant);
        if (Mv.AtNestEntrance(st, a, b))
        {
            EnterNest(st, a, b, ant);
            return;
        }
        if (st.Rand4() == 0) Set(st, SSTATE, ant, 2);
        else if (st.U16(T, 0x7b2) == 1) st.Hooks.Effect(st, "rest", a, b, 1);
    }

    static int FlightTimer(State st, int ant) => S16(st.U16(G, (Get(st, STYPE, ant) & 0x80) != 0 ? 0x8e8 : 0x8dc));

    /// <summary>f_09091 (state 14).</summary>
    public static void SPreFlight(State st, int ant)
    {
        if (st.Rand2() == 0) SNesting(st, ant);
        else Wander(st, ant);
        if (FlightTimer(st, ant) > 100) Set(st, SSTATE, st.U16(G, 0xf18), 0xf);
    }

    /// <summary>f_090f3 (state 15).</summary>
    public static void STakeOff(State st, int ant)
    {
        if (HomeMarker(st, ant) < 100) SNesting(st, ant);
        else Wander(st, ant);
        int tm = FlightTimer(st, ant);
        if (tm != 0)
        {
            if (tm != 1 && st.Rand(tm & 0xffff) != 0) return;
            Set(st, SSTATE, st.U16(G, 0xf18), 0x10);
        }
    }

    /// <summary>f_091d2 (state 16).</summary>
    public static void SFlying(State st, int ant)
    {
        int t = Get(st, STYPE, ant);
        if (st.Rand32() != 0) return;
        bool red = (t & 0x80) != 0;
        if ((!red && S16(st.U16(G, 0x6aa)) < 0x32) || (red && S16(st.U16(G, 0x73a)) < 0x32))
        {
            Set(st, STYPE, ant, 0);
            st.SetGrid(OCC, Get(st, SX, ant), Get(st, SY, ant), 0);
            if (st.U16(G, 0xeac) == 2)
            {
                st.Inc16(G, red ? 0x73a : 0x6aa);
                if (st.Rand16() == 0) st.Inc16(G, red ? 0x850 : 0x7c8);      // black: f_01315 (empty in this version)
            }
        }
    }

    // ------------------------------------------------------------------------------------------- Avenger
    /// <summary>f_14167: red surface ants in Defense go back to Bored.</summary>
    public static void ReleaseRedGuards(State st)
    {
        int i = S16(st.U16(G, 0xd6a));
        while (i > 0)
        {
            i--;
            int tt = Get(st, STYPE, i);
            if (tt != 0 && tt > 0x7f && Get(st, SSTATE, i) == 6) Set(st, SSTATE, i, 0);
        }
    }

    /// <summary>f_140e4: put up to n red workers/soldiers (not the Avenger) into Defense.</summary>
    public static void RecruitRed(State st, int n)
    {
        n = S16(n);
        int i = S16(st.U16(G, 0xd6a));
        while (i > 0 && n > 0)
        {
            i--;
            int tt = Get(st, STYPE, i);
            if (tt != 0 && tt > 0x7f)
            {
                int c = (tt & 0x78) >> 3;
                int s = Get(st, SSTATE, i);
                if ((c == 2 || c == 6) && s != 0x13 && s != 6)
                {
                    Set(st, SSTATE, i, 6);
                    Set(st, SE, i, 0);
                    n--;
                }
            }
        }
    }

    /// <summary>f_0e123.</summary>
    public static void AvengerPickTarget(State st)
    {
        ReleaseRedGuards(st);
        if (st.U16(G, 0x48c) == 1 && st.Rand(0x20) + 0x40 < S16(st.U16(G, 0x47c))
            && st.Rand(10) < S16(st.U16(G, 0xb1c)))
        {
            st.Set16(G, 0x4a4, 2);
            RecruitRed(st, st.U16(G, 0xb1c));
            return;
        }
        st.Set16(G, 0x4f2, st.U16(T, 0x2be));
        int ta = S16(st.U16(T, 0x2bc));
        st.Set16(G, 0x4e0, ta);
        if (ta < 0x1f)
        {
            int tb = S16(st.U16(G, 0x4f2));
            if (tb < 0x14) st.Set16(G, 0x4f2, tb + 5);
            else if (tb > 0x28) st.Set16(G, 0x4f2, tb - 5);
        }
        else
            st.Set16(G, 0x4e0, ta - 5);
        int n = S16(st.U16(G, 0xafc) + st.U16(G, 0xafe));
        RecruitRed(st, n < 0x14 ? n >> 2 : n >> 3);
        st.Set16(G, 0x4a4, 1);
    }

    /// <summary>f_1323e for view 1 (surface).</summary>
    public static bool IsWalkableSurface(State st, int a, int b)
    {
        if (!(0 <= a && a < 0x80 && 0 <= b && b < 0x40)) return false;
        int t = st.Grid(SURFACE, a, b);
        return st.U16(G, 0xf24) == 0 ? t < 0x54 : t < 0x91;
    }

    /// <summary>f_0e20f(view 1). Each walkable neighbour that is closer than the best so far tightens the
    /// threshold; a free open-ground one becomes the answer, any other becomes the fallback. -1/-2 = no step.</summary>
    public static int StepTowardsSurface(State st, int a, int b, int ta, int tb)
    {
        int dist = Mv.DistanceLo(a, b, ta, tb);
        if (dist <= 0) return -1;
        int res = -1, fallback = -2;
        for (int d = 0; d < 8; d++)
        {
            int na = a + Mv.Dx(st, d), nb = b + Mv.Dy(st, d);
            if (!IsWalkableSurface(st, na, nb)) continue;
            int nd = Mv.DistanceLo(na, nb, ta, tb);
            if (nd >= dist) continue;
            dist = nd;
            if (st.Grid(OCC, na, nb) == 0 && IsOpenGround(st, na, nb)) res = d;
            else fallback = d;
        }
        return res >= 0 ? res : fallback;
    }

    internal static bool IsOpenGround(State st, int a, int b)
    {
        if (!(0 <= a && a < 128 && 0 <= b && b < 64)) return false;
        int o = st.Grid(OCC, a, b);
        if (o != 0 && !Mv.IsYellow(o)) return false;
        return st.Grid(SURFACE, a, b) < 0x10;
    }

    /// <summary>f_0df5b (state 19): leads red guards towards its target.</summary>
    public static void SAvenger(State st, int ant)
    {
        int b = Get(st, SY, ant), t = Get(st, STYPE, ant), a = Get(st, SX, ant);
        int cc = t & 0xf8;
        st.Set16(G, 0x490, a);
        st.Set16(G, 0x494, b);
        st.Set16(G, 0x498, 1);
        int mode = st.U16(G, 0x4a4);
        if (mode == 0) AvengerPickTarget(st);
        else if (mode == 2 && st.U16(G, 0x48c) == 1)
        {
            st.Set16(G, 0x4e0, st.U16(G, 0x22a));
            st.Set16(G, 0x4f2, st.U16(G, 0x238));
        }
        int nd = StepTowardsSurface(st, a, b, S16(st.U16(G, 0x4e0)), S16(st.U16(G, 0x4f2)));
        if (nd < 0)
        {
            if (st.Rand(10) == 0) st.Set16(G, 0x4a4, 0);
        }
        else
        {
            int na = a + Mv.Dx(st, nd), nb = b + Mv.Dy(st, nd);
            int o = st.Grid(OCC, na, nb);
            if (o == 0)
            {
                TryStep(st, ant, a, b, nd, cc);
                return;
            }
            if (Mv.IsYellow(o))
            {
                st.Hooks.AttackPlayer(st, 1, ant);
                return;
            }
            if (o < 0x80) return;
            Set(st, STYPE, ant, (Mv.TurnAside(st, t & 7) | cc) & 0xff);
        }
        st.SetGrid(OCC, a, b, Get(st, STYPE, ant));
    }

    // ------------------------------------------------------------------------------------------- dispatcher
    static void Handle(State st, int state, int i)
    {
        switch (state)
        {
            case 0: SBored(st, i); break;
            case 1: SNesting(st, i); break;
            case 2: SForaging(st, i); break;
            case 3: SGotFood(st, i); break;
            case 4: SNesting(st, i); break;
            case 5: SDigOut(st, i); break;
            case 6: SDefense(st, i); break;
            case 7: SAttack(st, i); break;
            case 8: SHatching(st, i); break;
            case 9: SEggLaying(st, i); break;
            case 10: SFighting(st, i); break;
            case 11: SAlarmed(st, i); break;
            case 12: SDefendNest(st, i); break;
            case 13: SResting(st, i); break;
            case 14: SPreFlight(st, i); break;
            case 15: STakeOff(st, i); break;
            case 16: SFlying(st, i); break;
            case 19: SAvenger(st, i); break;
        }
    }

    /// <summary>f_08c8b: every surface slot from the top down: death roll, census, state handler.</summary>
    public static void SurfaceAntsTick(State st)
    {
        st.Set16(G, 0xf18, st.U16(G, 0xd6a));
        while (S16(st.U16(G, 0xf18)) >= 1)
        {
            int i = st.U16(G, 0xf18) - 1;
            st.Set16(G, 0xf18, i);
            if (st.Rand256() == 0)
            {
                int tt = Get(st, STYPE, i);
                if (tt != 0)
                {
                    int health = S16(st.U16(G, (tt & 0x80) != 0 ? 0x1fe : 0x10be));
                    if (st.Rand32() > health)
                    {
                        PlaceCorpse(st, Get(st, SX, i), Get(st, SY, i), (tt & 0x80) != 0);
                        Set(st, STYPE, i, 0);
                        st.Inc32(G, 0xf30);
                    }
                }
            }
            int t = Get(st, STYPE, i);
            if (t == 0) continue;
            int state = Get(st, SSTATE, i);
            st.Inc16(G, ((t & 0x80) != 0 ? 0xd72 : 0xd40) + state * 2);
            if (state > 0x13) continue;
            Handle(st, state, i);
        }
    }
}
