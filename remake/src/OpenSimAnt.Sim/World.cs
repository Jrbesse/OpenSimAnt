using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;
using Co = OpenSimAnt.Sim.Colony;
using Mv = OpenSimAnt.Sim.Movement;
using Ng = OpenSimAnt.Sim.NestGrid;
using Ph = OpenSimAnt.Sim.Pheromones;
using Sf = OpenSimAnt.Sim.Surface;

namespace OpenSimAnt.Sim;

/// <summary>World updates run by SimStep besides the ants: the slow phases, history graph, advisor status
/// line, weather, ant lions, the caterpillar and bugs, and the spider (SIMANT.EXE segments 0894, 1be8,
/// 1e2e, 892c). Screen-only side effects go to st.Hooks.Effect.</summary>
public static class World
{
    public const int SURFACE = 0x0180;

    // ------------------------------------------------------------------------------------------- history
    static readonly (int src, int dst)[] HistorySources =
    {
        (0x330, 0x516), (0x350, 0x5a0), (0x1050, 0x626), (0x1060, 0x6ae), (0x10be, 0x73c),
        (0x1fe, 0x7ce), (0x1040, 0x856), (0xf30, 0x8f0), (0xf20, 0x970), (0xefc, 0xa0a),
    };

    /// <summary>f_798c8 (slow phase 0/2): sample the history graph (64-entry ring at G:04F4).</summary>
    public static void History(State st)
    {
        int i = st.U16(G, 0x4f4) * 2;
        foreach (var (src, dst) in HistorySources) st.Set16(G, dst + i, st.U16(G, src));
        if (S16(st.U16(T, 0x828)) < 0x3f) st.Inc16(T, 0x828);
        st.Set16(G, 0x4f4, (st.U8(G, 0x4f4) + 1) & 0x3f);
        st.Hooks.Effect(st, "graph");                                       // f_235a0: redraw if open
    }

    // ------------------------------------------------------------------------------------------- advisor
    /// <summary>f_0e2ea: pick the status-line advice (entries of the message table at G:0360) or clear it.</summary>
    public static void Advisor(State st)
    {
        if (st.U16(G, 0xeac) == 0) Tutorial.Run(st);                       // f_0e425, then the status line as usual
        if (st.U16(T, 0x7b0) == 0) return;
        int playerIn = st.U16(G, 0xa06);
        int yh = S16(st.U16(G, 0xf78));
        if (playerIn == 0 && (S16(st.U16(G, 0xfba)) > yh || yh < 10))
        {
            if (yh < 10) st.Hooks.Effect(st, "status", 0, 120, 1);           // the yellow ant is dying
            else st.Hooks.Effect(st, "status", 1, 120, 0);
        }
        else if (S16(st.U16(G, 0x10be)) < S16(st.U16(G, 0xffe)))
            st.Hooks.Effect(st, "status", 2, 120, 0);                        // the colony is hungry
        else
        {
            int cap = S16(st.U16(G, 0x224));
            if (S16(st.U16(G, 0x330)) <= cap) st.Hooks.Effect(st, "status", null, 0, 0);   // f_2f802: clear
            else if (playerIn == 0 && st.U16(T, 0xc24) == 0 && cap == 0) st.Hooks.Effect(st, "status", 3, 120, 0);
            else st.Hooks.Effect(st, "status", 4, 120, 0);                   // the nest is too small
        }
    }

    // ------------------------------------------------------------------------------------------- slow phases
    /// <summary>f_0c20f.</summary>
    public static void CensusAndAdvise(State st)
    {
        Co.Census(st, m => st.Hooks.Effect(st, "message", m));
        Advisor(st);
    }

    /// <summary>f_08a78: one of four phases every 32 ticks, by bits 5-6 of the tick.</summary>
    public static void SlowPhase(State st)
    {
        int p = (st.U8(G, 0xf08) & 0x60) >> 5;
        if (p == 0 || p == 2)
        {
            if (p == 0) Ng.CompactSurface(st);
            CensusAndAdvise(st);
            History(st);
            Ph.DiffuseAlarm(st);
        }
        else if (p == 1)
        {
            Ng.CompactNest(st, Ng.BLACK);
            Ph.BlackNestMarkers(st);
            Ph.DecayBlackNest(st);
            Ph.DecayBlackTrail(st);
        }
        else
        {
            Ng.CompactNest(st, Ng.RED);
            Ph.RedNestMarkers(st);
            Ph.DecayRedNest(st);
            Ph.DecayRedTrail(st);
        }
    }

    // ------------------------------------------------------------------------------------------- tiles
    /// <summary>GetTile(1, a, b): surface tile, -1 outside the patch.</summary>
    public static int GetTile(State st, int a, int b) => 0 <= a && a <= 0x7f && 0 <= b && b <= 0x3f ? st.Grid(SURFACE, a, b) : -1;

    /// <summary>SetTile(1, a, b, v) (f_1183e).</summary>
    public static void SetTile(State st, int a, int b, int v)
    {
        if (0 <= a && a <= 0x7f && 0 <= b && b <= 0x3f)
        {
            st.SetGrid(SURFACE, a, b, v);
            st.Hooks.Effect(st, "redraw", 1, a, b);
        }
    }

    /// <summary>IsOpenGround(1, a, b) (f_1145c).</summary>
    public static bool IsOpenGround(State st, int a, int b)
    {
        int t = GetTile(st, a, b);
        if (t < 0) return false;
        int o = st.Grid(0x6180, a, b);
        if (o != 0 && o != 0xfe && o != 0xff) return false;
        return t < 0x10;
    }

    /// <summary>IsOpenWithRing(1, a, b) (f_113fe).</summary>
    public static bool IsOpenWithRing(State st, int a, int b)
    {
        if (!IsOpenGround(st, a, b)) return false;
        for (int d = 0; d < 8; d++)
            if (!IsOpenGround(st, a + st.S8(T, d), b + st.S8(T, 8 + d))) return false;
        return true;
    }

    /// <summary>TileClass (f_0ad63): food crumbs.</summary>
    public static bool IsFoodTile(State st, int t) => st.U16(G, 0xf24) == 0 ? 0x48 <= t && t <= 0x4b : 0x18 <= t && t <= 0x27;

    // ------------------------------------------------------------------------------------------- ant lions
    // up to 9 pits (count T:0C4A): a G:0A92, b G:0AA8, state G:0ABA (0 lurking, 1 eating, 2 closing),
    // timer G:0ACC, animation frame G:0ADE (tile 0x38 + frame)
    public const int LA = 0xa92, LB = 0xaa8, LSTATE = 0xaba, LTIMER = 0xacc, LFRAME = 0xade;

    /// <summary>f_0b54d.</summary>
    static void LionDraw(State st, int i) => SetTile(st, st.U8(G, LA + i), st.U8(G, LB + i), st.U8(G, LFRAME + i) + 0x38);

    /// <summary>f_0b09c: dig a pit (tile 0x38, sand ring around it) and add it to the list.</summary>
    public static void PlaceLion(State st, int a, int b)
    {
        SetTile(st, a, b, 0x38);
        for (int d = 0; d < 8; d++)
        {
            int na = st.S8(T, d) + a, nb = st.S8(T, 8 + d) + b;
            if (IsOpenGround(st, na, nb)) SetTile(st, na, nb, st.U8(0x55b3, 0x1b92 + d) + 0x30);
        }
        int i = st.U16(T, 0xc4a);
        st.Set8(G, LA + i, a);
        st.Set8(G, LB + i, b);
        foreach (int f in new[] { LSTATE, LTIMER, LFRAME }) st.Set8(G, f + i, 0);
        if (S16(i) < 9) st.Inc16(T, 0xc4a);
    }

    /// <summary>f_0b016: up to 200 tries for a spot, preferring open 3x3 ground.</summary>
    public static void NewLion(State st)
    {
        for (int k = 0; k < 200; k++)
        {
            int a = st.Rand(0x41) + st.Rand(0x40);
            int b = st.Rand(0x21) + st.Rand(0x20);
            if (IsOpenWithRing(st, a, b) || (IsOpenGround(st, a, b) && k > 99))
            {
                PlaceLion(st, a, b);
                return;
            }
        }
    }

    /// <summary>f_0b5c8: the pit is filled in (tile 0x3F) and removed from the list.</summary>
    public static void RemoveLion(State st, int i)
    {
        SetTile(st, st.U8(G, LA + i), st.U8(G, LB + i), 0x3f);
        int n = S16(st.U16(T, 0xc4a));
        if (n > 0)
        {
            st.Set16(T, 0xc4a, n - 1);
            for (int j = i; j < n - 1; j++)
                foreach (int f in new[] { LA, LB, LFRAME, LSTATE, LTIMER })
                    st.Set8(G, f + j, st.U8(G, f + j + 1));
        }
    }

    /// <summary>f_0ed8f: delete surface ant i, closing the gap in the arrays.</summary>
    public static void RemoveSurfaceAnt(State st, int i)
    {
        st.SetGrid(0x6180, st.U8(SIM, 0xa180 + i), st.U8(SIM, 0xa569 + i), 0);
        int n = S16(st.U16(G, 0xd6a));
        if (n > 0)
        {
            n--;
            st.Set16(G, 0xd6a, n);
        }
        foreach (int @base in new[] { 0xa180, 0xa569, 0xa952, 0xad3b, 0xb124 })
            for (int j = i; j < n; j++)
                st.Set8(SIM, @base + j, st.U8(SIM, @base + j + 1));
    }

    /// <summary>f_0b163.</summary>
    public static void AntLions(State st)
    {
        if (st.U16(T, 0xc4a) == 0 && S16(st.U16(G, 0x8ea)) > 0 && st.Rand(0x400) == 0)
        {
            NewLion(st);
            return;
        }
        int i = 0;
        while (i < S16(st.U16(T, 0xc4a)))
        {
            int state = st.U8(G, LSTATE + i);
            int a = st.U8(G, LA + i), b = st.U8(G, LB + i);
            if (state == 0)
            {
                int t = GetTile(st, a, b);
                if ((0x51 <= t && t <= 0x53) || IsFoodTile(st, t))           // something lies on the pit
                {
                    if (st.Rand(0x200) == 0)
                    {
                        int d = st.Rand8();
                        for (int k = 0; k < 8; k++)
                        {
                            int na = st.S8(T, d) * 2 + a, nb = st.S8(T, 8 + d) * 2 + b;
                            if (IsOpenGround(st, na, nb))
                            {
                                SetTile(st, na, nb, t);                    // flung out of the pit
                                st.Hooks.Effect(st, "sound", 0x1e);
                                break;
                            }
                            d = (d + 1) & 7;
                        }
                        st.Set8(G, LTIMER + i, 0x19);
                        st.Set8(G, LSTATE + i, 1);
                        st.Set8(G, LFRAME + i, 1);
                        LionDraw(st, i);
                    }
                }
                else
                {
                    int k = 0;
                    for (int rep = 0; rep < 2; rep++)
                    {
                        int na = st.S8(T, 0x10 + k) + a, nb = st.S8(T, 0x1a + k) + b;
                        int o = st.Grid(0x6180, na, nb);
                        if (o != 0)
                        {
                            if (o == 0xfe || o == 0xff)
                                st.Hooks.LionEatsPlayer(st, a, b);       // f_11a3e + f_2f7d0(2)
                            else
                            {
                                st.Rand8();                              // 1/8: crunch sound (f_00f54)
                                int j = Mv.SurfaceAntAt(st, na, nb);
                                if (j >= 0) RemoveSurfaceAnt(st, j);
                                st.Inc32(G, (o & 0x80) != 0 ? 0xf80 : 0xf20);
                            }
                            st.Set8(G, LTIMER + i, 0x32);
                            st.Set8(G, LSTATE + i, 1);
                            st.Set8(G, LFRAME + i, 1);
                            LionDraw(st, i);
                            break;
                        }
                        k = st.Rand(8) + 1;
                    }
                }
            }
            else if (state == 1)
            {
                int busy = 0;
                for (int d = 0; d < 8; d++)
                    if (st.Grid(0x6180, a + st.S8(T, d), b + st.S8(T, 8 + d)) != 0) busy++;
                if (busy >= 7)                                              // swarmed: the ant lion dies
                {
                    st.Hooks.Effect(st, "message", 0x2742);
                    RemoveLion(st, i);
                    i++;
                    continue;
                }
                int f = st.U8(G, LFRAME + i);
                if (f < 4) st.Set8(G, LFRAME + i, f + 1);
                else if (st.U8(G, LTIMER + i) == 0)
                {
                    st.Set8(G, LSTATE + i, 2);
                    st.Set8(G, LFRAME + i, 4);
                }
                else
                {
                    st.Set8(G, LTIMER + i, st.U8(G, LTIMER + i) - 1);
                    if ((st.U8(G, LTIMER + i) & 1) != 0) st.Set8(G, LFRAME + i, st.Rand(4) + 3);
                }
                LionDraw(st, i);
            }
            else if (state == 2)
            {
                int f = st.U8(G, LFRAME + i);
                if (f != 0) st.Set8(G, LFRAME + i, f - 1);
                else
                {
                    st.Set8(G, LSTATE + i, 0);
                    st.Inc16(G, 0xa08);
                    if (S16(st.U16(T, 0xc4a)) < 9 && (st.U8(G, 0xa08) & 0xf) == 0xf) NewLion(st);
                }
                LionDraw(st, i);
            }
            i++;
        }
    }

    // ------------------------------------------------------------------------------------------- bugs + caterpillar
    static bool InPatch(int a, int b) => 0 <= a && a <= 0x7f && 0 <= b && b <= 0x3f;

    /// <summary>f_0ae4c: three harmless bugs (a G:0EAE, b G:0F00, heading G:0F1A, tile under them G:0F28;
    /// drawn as T:0C52[heading]) wander over open ground.</summary>
    public static void Bugs(State st)
    {
        for (int k = 0; k < 3; k++)
        {
            if (st.Rand4() == 0) continue;
            int o = k * 2;
            if (st.Rand4() == 0)
            {
                int hh = (st.U8(G, 0xf1a + o) + st.Rand(3) - 1) & 7;
                st.Set16(G, 0xf1a + o, hh);
                st.SetGrid(SURFACE, S16(st.U16(G, 0xeae + o)), S16(st.U16(G, 0xf00 + o)), st.U8(T, 0xc52 + hh));
            }
            int h = st.U16(G, 0xf1a + o);
            int a = S16(st.U16(G, 0xeae + o)), b = S16(st.U16(G, 0xf00 + o));
            int na = a + st.S8(T, h), nb = b + st.S8(T, 8 + h);
            if (InPatch(na, nb) && st.Grid(0x6180, na, nb) == 0 && st.Grid(SURFACE, na, nb) < 0x10)
            {
                int under = st.Grid(SURFACE, na, nb);
                st.SetGrid(SURFACE, a, b, st.U8(G, 0xf28 + o));
                st.Set16(G, 0xf28 + o, under);
                st.SetGrid(SURFACE, na, nb, st.U8(T, 0xc52 + h));
                st.Set16(G, 0xeae + o, na);
                st.Set16(G, 0xf00 + o, nb);
            }
        }
    }

    // caterpillar: active T:0C4C, head a T:0C4E / b T:0C50, heading G:0C3C (0 north/up b-, 1 east a+,
    // 2 south b+, 3 west a-), step countdown G:0C36 (moves one cell every 5 calls), tiles under the body in
    // the 6-entry ring G:0D9C indexed by the coordinate along the path
    static readonly (int, int)[] CAT_STEP = { (0, -1), (1, 0), (0, 1), (-1, 0) };

    /// <summary>f_0bcaa.</summary>
    static void CatPut(State st, int a, int b, int v)
    {
        if (InPatch(a, b)) st.SetGrid(SURFACE, a, b, v);
    }

    static int CatRing(State st, int a, int b) => 0xd9c + CMod((st.U8(G, 0xc3c) & 1) != 0 ? a : b, 6) * 2;

    /// <summary>f_0babb.</summary>
    static void CatSave(State st, int a, int b)
    {
        if (InPatch(a, b)) st.Set16(G, CatRing(st, a, b), st.Grid(SURFACE, a, b));
    }

    /// <summary>f_0bb47.</summary>
    static void CatRestore(State st, int a, int b)
    {
        if (InPatch(a, b)) st.SetGrid(SURFACE, a, b, st.U8(G, CatRing(st, a, b)));
    }

    /// <summary>f_0bcde.</summary>
    static int Occ(State st, int a, int b) => InPatch(a, b) ? st.Grid(0x6180, a, b) : 0;

    /// <summary>f_0bb9f: enter from a random point of a random edge.</summary>
    public static void CaterpillarStart(State st)
    {
        int d = st.Rand(4);
        st.Set16(G, 0xc3c, d);
        int a, b, t;
        if (d == 0) { a = st.Rand(0x80); b = 0x3f; t = 0x6c; }
        else if (d == 1) { a = 0; b = st.Rand(0x40); t = 0x6b; }
        else if (d == 2) { a = st.Rand(0x80); b = 0; t = 0x6f; }
        else { a = 0x7f; b = st.Rand(0x40); t = 0x68; }
        st.Set16(T, 0xc4e, a);
        st.Set16(T, 0xc50, b);
        CatSave(st, a, b);
        CatPut(st, a, b, t);
    }

    /// <summary>f_0bd80: the body turns into food (0x4B) wherever it lay on open ground.</summary>
    public static void CaterpillarDie(State st)
    {
        int d = st.U16(G, 0xc3c);
        int a = S16(st.U16(T, 0xc4e)), b = S16(st.U16(T, 0xc50));
        if (d > 3) return;
        var (sa, sb) = CAT_STEP[d];
        for (int i = 0; i < 6; i++)
        {
            int x = a - sa * i, y = b - sb * i;
            if (InPatch(x, y))                                            // f_0be34
            {
                CatRestore(st, x, y);
                if (st.Grid(SURFACE, x, y) < 0x18) st.SetGrid(SURFACE, x, y, 0x4b);
            }
        }
    }

    /// <summary>f_0b6cc (odd ticks, yard only): the bugs, then the caterpillar.</summary>
    public static void Caterpillar(State st)
    {
        if (st.U16(G, 0xf24) == 1) return;
        Bugs(st);
        if (st.U16(T, 0xc4c) == 0)
        {
            CaterpillarStart(st);
            st.Set16(T, 0xc4c, 1);
            st.Set16(G, 0xc36, 4);
            return;
        }
        int d = st.U16(G, 0xc3c);
        int a = S16(st.U16(T, 0xc4e)), b = S16(st.U16(T, 0xc50));
        if (d > 3) throw new NotImplementedException("caterpillar heading > 3 (uninitialised local in the original)");
        var (sa, sb) = CAT_STEP[d];
        if (Occ(st, a + sa, b + sb) != 0)                                  // blocked by an ant
        {
            int busy = 0;
            for (int x = a - 1; x < a + 2; x++)
                for (int y = b - 1; y < b + 2; y++)
                    if (Occ(st, x, y) != 0) busy++;
            if (busy > 5)
            {
                st.Set16(T, 0xc4c, 0);
                CaterpillarDie(st);
            }
            return;
        }
        st.Inc16(G, 0xc36, -1);
        int n = S16(st.U16(G, 0xc36));
        bool vert = d == 0 || d == 2;
        if (n == 4) CatRestore(st, a - sa * (n + 1), b - sb * (n + 1));          // the tail moves on
        else CatPut(st, a - sa * (n + 1), b - sb * (n + 1), vert ? 0x6d : 0x69);
        CatPut(st, a - sa * n, b - sb * n, vert ? 0x6e : 0x6a);
        if (n != 0) return;
        a += sa;
        b += sb;
        st.Set16(T, 0xc4e, a);
        st.Set16(T, 0xc50, b);
        if (a < -6 || a > 0x86 || b < -6 || b > 0x45)
        {
            st.Set16(T, 0xc4c, 0);
            return;
        }
        CatSave(st, a, b);
        CatPut(st, a, b, new[] { 0x6c, 0x6b, 0x6f, 0x68 }[d]);
        CatPut(st, a - sa, b - sb, vert ? 0x6d : 0x69);
        st.Set16(G, 0xc36, 5);
    }

    // ------------------------------------------------------------------------------------------- spider
    // position in 1/16 tiles G:0F12 (a) / G:0F34 (b), active G:0F0C, state G:0FB8 (0 resting, 1 walking,
    // 2 hunting, 3 eating, 4 fleeing, 5 beaten), heading G:1004, animation G:1042, prey G:0FFC (surface ant,
    // -1 the yellow ant, -2 none) whose type is remembered in G:10AE, mode G:06AC (7: hunts any ant within
    // ~28 tiles, 8: also lashes out at ants beside it), times beaten G:108A. With G:0A06 == 1 the player
    // is the spider (it walks to the cursor G:0F42/0F7E and drags the view, G:047C/048A, along).
    public const int SPX = 0xf12, SPY = 0xf34;

    static (int, int) SpPos(State st) => (S16(st.U16(G, SPX)) >> 4, S16(st.U16(G, SPY)) >> 4);

    /// <summary>Move one step along the heading (T:0994/099C, in 1/16 tiles), mul 1 or 5; animate.</summary>
    static void SpStep(State st, int mul, bool back)
    {
        int h = st.U16(G, 0x1004);
        int dx = st.S8(T, 0x994 + h) * mul, dy = st.S8(T, 0x99c + h) * mul;
        int k = mul == 1 ? 1 : 2;
        if (back) { dx = -dx; dy = -dy; k = -k; }
        st.Set16(G, SPX, st.U16(G, SPX) + dx);
        st.Set16(G, SPY, st.U16(G, SPY) + dy);
        st.Set16(G, 0x1042, (st.U16(G, 0x1042) + k) & 0x3ff);
    }

    static void SpTurnRandom(State st) => st.Set16(G, 0x1004, st.S8(T, 0x24 + st.U16(G, 0x1004) * 8 + st.Rand(8)));

    /// <summary>f_11327(1, a, b, t): index of the surface ant at (a, b) with type t, from the top; -1 if none.</summary>
    static int SurfaceAntWith(State st, int a, int b, int t)
    {
        int i = S16(st.U16(G, 0xd6a));
        while (true)
        {
            i--;
            if (i < 0) return i;
            if (st.U8(SIM, 0xa180 + i) == a && st.U8(SIM, 0xa569 + i) == b && st.U8(SIM, 0xad3b + i) == t) return i;
        }
    }

    /// <summary>f_0dbb9.</summary>
    public static int SpiderFindPrey(State st)
    {
        var (a, b) = SpPos(st);
        if (st.U16(G, 0x6ac) == 7)
        {
            int i = S16(st.U16(G, 0xd6a));
            while (i > 0)
            {
                i--;
                if (st.U8(SIM, 0xad3b + i) != 0 && Co.Distance(a, b, st.U8(SIM, 0xa180 + i), st.U8(SIM, 0xa569 + i)) <= 800)
                    return i;
            }
            if (st.U16(G, 0xa06) == 0 && st.U16(G, 0x48c) == 1
                && Co.Distance(a, b, S16(st.U16(G, 0x47c)), S16(st.U16(G, 0x48a))) < 0x321)
                return -1;
            return -2;
        }
        int h = st.U16(G, 0x1004);
        int x = a, y = b;
        for (int k = 0; k < 20; k++)
        {
            y += st.S8(T, 8 + h);
            x += st.S8(T, h);
            if (!InPatch(x, y) || Co.Distance(a, b, x, y) > 400) break;
            int o = st.Grid(0x6180, x, y);
            if (o != 0)
            {
                if (o == 0xfe || o == 0xff) return -1;
                int j = SurfaceAntWith(st, x, y, o);
                if (j >= 0) return j;
            }
        }
        return -2;
    }

    /// <summary>f_0dd40 (mode 8): strike at an ant in the 90-degree cone ahead, up to 12 tiles; 3/4 kill it.</summary>
    public static int SpiderLash(State st)
    {
        int @base = ((st.U8(G, 0x1004) - 2) & 7) * 0x20;
        int fa = S16(st.U16(G, SPX)), fb = S16(st.U16(G, SPY));
        int res = -1;
        for (int rep = 0; rep < 2; rep++)
        {
            for (int ang = @base - 0x20; ang < @base + 0x20; ang++)
            {
                int r = st.Rand(0xc) + 1;
                int x = S16(CDiv(Co.Cos256(ang) * r, 0x7fff) + (fa >> 4));
                int y = S16(CDiv(Co.Sin256(ang) * r, 0x7fff) + (fb >> 4));
                if (!InPatch(x, y)) continue;
                int o = st.Grid(0x6180, x, y);
                if (o == 0) continue;
                res = SurfaceAntWith(st, x, y, o);
                if (res < 0) continue;
                st.Hooks.Effect(st, "spider_strike", x * 16 + 7, y * 16 + 7);
                if (st.Rand4() == 0) return res;
                st.SetGrid(0x6180, x, y, 0);
                st.Set8(SIM, 0xad3b + res, 0);
                Sf.PlaceCorpse(st, x, y, (o & 0x80) != 0);
                return res;
            }
        }
        return res;
    }

    /// <summary>f_0c692: a beaten spider leaves food behind.</summary>
    public static int SpiderDropFood(State st, int a, int b)
    {
        int t = st.Grid(SURFACE, a, b);
        if (st.U16(G, 0xf24) == 1)
        {
            if (t > 3)
            {
                if (t < 8 || t > 0x17)
                {
                    if (t < 0x18 || t > 0x26)
                    {
                        if (t < 0x40) throw new NotImplementedException("f_0c73d (spider food on house furniture)");
                        return 0;
                    }
                    st.SetGrid(SURFACE, a, b, t + 1);
                    st.Inc16(G, 0x1040);
                    return 1;
                }
                t = (t - 8) >> 2;
            }
            st.SetGrid(SURFACE, a, b, ((t + 6) * 4) & 0xff);
        }
        else
        {
            if (t > 0x4a) return 0;
            st.SetGrid(SURFACE, a, b, t < 0x48 ? 0x48 : t + 1);
        }
        st.Inc16(G, 0x1040);
        return 1;
    }

    /// <summary>L_cefa: start hunting the prey just found.</summary>
    static void SpPreyChosen(State st, int r)
    {
        st.Set16(G, 0xfb8, 2);
        st.Set16(G, 0x10ae, r >= 0 ? st.U8(SIM, 0xad3b + r) : 0xff);
    }

    static bool SpPlayerFollow(State st)
    {
        if (st.U16(G, 0xa06) == 1)
        {
            var (a, b) = SpPos(st);
            st.Set16(G, 0x47c, a);
            st.Set16(G, 0x48a, b);
            return true;
        }
        return false;
    }

    /// <summary>f_0ce63.</summary>
    public static void Spider(State st)
    {
        st.Set16(G, 0x1072, (st.U16(G, 0x1072) + 1) & 0x3ff);
        var (a, b) = SpPos(st);
        int state = st.U16(G, 0xfb8);
        if (st.U16(G, 0xa06) == 1 && state != 2 && state != 3)
        {
            SpiderPlayer(st);
            return;
        }
        if (st.U16(G, 0xf0c) == 0)
        {
            if (st.U16(G, 0xeac) == 0 || st.Rand(0x12c) != 0) return;
            st.Set16(G, SPX, st.Rand(0x400) + 0x200);
            st.Set16(G, 0xf0c, 1);
            st.Set16(G, 0xfb8, 1);
            st.Set16(T, 0xc12, 0);
            if (st.Rand(2) != 0)
            {
                st.Set16(G, SPY, 1);
                st.Set16(G, 0x1004, 4);
            }
            else
            {
                st.Set16(G, SPY, 0x3ff);
                st.Set16(G, 0x1004, 0);
            }
            return;
        }
        if ((st.U8(G, 0x1072) & 3) == 0 && S16(st.U16(G, 0xfb8)) < 5)
        {
            int n = 0;                                                       // f_0db10: 4x4 (sic)
            for (int x = a - 1; x < a + 3; x++)
                for (int y = b - 1; y < b + 3; y++)
                    if (InPatch(x, y) && st.Grid(0x6180, x, y) != 0) n++;
            if (n > 8)                                                       // swarmed: beaten
            {
                SpiderBeaten(st);
                if (st.U16(G, 0xa06) == 1)
                {
                    st.Set16(G, 0xa06, 0);
                    st.Hooks.SpiderEvent(st, 3);
                    return;
                }
                st.Hooks.Effect(st, "message", 0x273e);
                if (S16(st.U16(G, 0x108a)) < 5) st.Inc16(G, 0x108a);
                int k = S16(st.U16(G, 0x108a));
                if (k < 3) return;
                st.Set16(G, 0x6ac, k >= 5 ? 8 : 7);
                if (k < 6 || st.Rand2() != 0) return;
                st.Set16(G, 0x108a, 0);
                st.Set16(G, 0x6ac, 0);
                return;
            }
            if (n > 4) st.Set16(G, 0xfb8, 4);
        }
        if (S16(st.U16(G, 0xfb8)) < 4 && st.U16(G, 0x6ac) == 8) SpiderLash(st);
        state = st.U16(G, 0xfb8);
        if (state == 0)
        {
            st.Set16(G, 0x1042, 2);
            if (st.Rand(0x96) == 0) st.Set16(G, 0xfb8, 1);
            int r = SpiderFindPrey(st);
            st.Set16(G, 0xffc, r);
            if (r != -2)
            {
                SpPreyChosen(st, r);
                return;
            }
            if (st.Rand(0x1e) == 0) SpTurnRandom(st);
            if (st.U16(G, 0x6ac) == 8) SpiderLash(st);
        }
        else if (state == 1)
        {
            SpStep(st, 1, st.U16(T, 0xc12) != 0);
            if (st.Rand(0x14) == 0) SpTurnRandom(st);
            int r = SpiderFindPrey(st);
            st.Set16(G, 0xffc, r);
            if (r != -2)
            {
                SpPreyChosen(st, r);
                return;
            }
            SpMaybeRest(st);
        }
        else if (state == 2)
        {
            if (!SpiderHunt(st, a, b)) return;
        }
        else if (state == 3)
        {
            if (!SpiderEat(st, a, b)) return;
        }
        else if (state == 4)
        {
            SpTurnRandom(st);
            SpStep(st, 5, st.U16(T, 0xc12) != 0);
            SpMaybeRest(st);
        }
        else if (state == 5)
        {
            st.Inc16(G, 0x109a, -1);
            if (st.U16(G, 0x109a) == 0)
            {
                st.Set16(G, 0xf0c, 0);
                st.Set16(G, 0xfb8, 0);
                for (int k = 0; k < 3; k++) SpiderDropFood(st, a, b);
                return;
            }
            if (S16(st.Rand(0x3e8)) < S16(st.U16(G, 0x109a)))
            {
                if (S16(st.U16(G, 0x109a)) > 0x190) st.Set16(G, 0x1042, st.Rand(3) + 1);
                else st.Set16(G, 0x1042, st.Rand(2) + 2);
            }
        }
        SpiderTail(st);
    }

    /// <summary>f_0db90.</summary>
    public static void SpiderBeaten(State st)
    {
        st.Set16(G, 0xfb8, 5);
        st.Set16(G, 0x109a, 500);
        st.Set16(G, 0x1042, 0);
    }

    /// <summary>0d7cd.</summary>
    static void SpMaybeRest(State st)
    {
        if (st.Rand(0x32) == 0)
        {
            st.Set16(G, 0xfb8, 0);
            st.Set16(G, 0x1042, 2);
        }
    }

    /// <summary>0da96: leaving the patch (or climbing furniture in the house) ends the visit.</summary>
    static void SpiderTail(State st)
    {
        var (a, b) = SpPos(st);
        if (!InPatch(a, b))
        {
            st.Set16(G, 0xf0c, 0);
            if (st.U16(G, 0xa06) == 1)
            {
                st.Set16(G, 0xa06, 0);
                st.Hooks.SpiderEvent(st, 4);
            }
        }
        if (st.U16(G, 0xf24) != 0)
        {
            if (st.U8(SIM, 0x180 + ((st.U16(G, SPX) & 0xfff0) << 2) + (S16(st.U16(G, SPY)) >> 4)) > 0x90)
                st.Set16(G, 0xf0c, 0);
        }
    }

    static void SpLosePrey(State st)
    {
        st.Set16(G, 0xfb8, 0);
        st.Set16(G, 0xffc, 0xfffe);
    }

    /// <summary>State 2 (0d3ee). Returns false when the tick ends without the common tail.</summary>
    static bool SpiderHunt(State st, int a, int b)
    {
        int p = S16(st.U16(G, 0xffc));
        if (p >= 0)
        {
            if (((st.U8(SIM, 0xad3b + p) ^ st.U8(G, 0x10ae)) & 0xf0) != 0)      // the prey is gone
            {
                SpLosePrey(st);
                if (st.U16(G, 0xa06) == 1)
                {
                    st.Set16(G, 0xf7e, b);
                    st.Set16(G, 0xf42, a);
                    st.Set16(G, 0x47c, a);
                    st.Set16(G, 0x48a, b);
                    if (st.U16(G, 0x6ac) == 6) st.Set16(G, 0x6ac, 0);
                    st.Hooks.Effect(st, "scroll");
                }
                return false;
            }
        }
        else if (S16(st.U16(G, 0x48c)) > 1)                                  // the yellow ant went underground
        {
            SpLosePrey(st);
            return false;
        }
        int tx, ty;
        if (p < 0) { tx = S16(st.U16(G, 0x47c)); ty = S16(st.U16(G, 0x48a)); }
        else { tx = st.U8(SIM, 0xa180 + p); ty = st.U8(SIM, 0xa569 + p); }
        int d = Math.Abs(tx - a) + Math.Abs(ty - b);                         // f_0dec8
        if (d > 0x40 && st.U16(G, 0xa06) != 1)
        {
            SpLosePrey(st);
            return false;
        }
        if (d < 2)                                                         // caught
        {
            st.Set16(G, 0xfb8, 3);
            st.Set16(G, SPX, (st.U16(G, SPX) & 0xfff0) + 8);
            st.Set16(G, SPY, (st.U16(G, SPY) & 0xfff0) + 8);
            return SpiderEat(st, a, b);
        }
        int dd = Mv.DirTo(a, b, tx, ty);
        st.Set16(G, 0x1004, st.S8(T, 0x23 + st.U16(G, 0x1004) * 8 + dd));
        st.Hooks.Effect(st, "sound", 0x2f);
        SpStep(st, 5, st.U16(T, 0xc12) != 0);
        if (SpPlayerFollow(st)) st.Hooks.Effect(st, "scroll");
        SpiderTail(st);
        return false;
    }

    /// <summary>State 3 (0d526): eat the prey. Returns true to run the common tail.</summary>
    static bool SpiderEat(State st, int a, int b)
    {
        if (SpPlayerFollow(st))
        {
            if (st.U16(G, 0x6ac) == 6) st.Set16(G, 0x6ac, 0);
            st.Hooks.Effect(st, "scroll");
        }
        int p = S16(st.U16(G, 0xffc));
        if (p != -2)
        {
            if (p < 0)
            {
                int h0 = st.U16(G, 0x1004);
                st.Hooks.SpiderEatsPlayer(st, (st.S8(T, 0x9a4 + h0) + a) & 0x7f, (st.S8(T, 0x9ac + h0) + b) & 0x3f);
                st.Set16(G, 0x105a, 0);
            }
            else if (((st.U8(G, 0x10ae) ^ st.U8(SIM, 0xad3b + p)) & 0xf0) != 0)
            {
                st.Set16(G, 0xffc, 0xfffe);
                SpDoneEating(st, a, b);
                return true;
            }
            else
            {
                if ((st.U8(G, 0x10ae) & 0x80) != 0)
                {
                    st.Inc32(G, 0xf80);
                    st.Set16(G, 0x105a, 4);
                }
                else
                {
                    st.Inc32(G, 0xf20);
                    st.Set16(G, 0x105a, 0);
                }
                st.SetGrid(0x6180, st.U8(SIM, 0xa180 + p), st.U8(SIM, 0xa569 + p), 0);
                st.Set8(SIM, 0xad3b + p, 0);
            }
            st.Set16(G, 0xffc, 0xfffe);
            st.Set16(G, 0x1054, S16(st.U16(G, 0x6ac)) >= 7 ? 0xb : 0x32);
        }
        // 0d95c: chewing in front of the spider leaves a corpse
        int h = st.U16(G, 0x1004);
        int x = (st.S8(T, 0x9a4 + h) + a) & 0x7f;
        int y = (st.S8(T, 0x9ac + h) + b) & 0x3f;
        if (st.U16(G, 0xf24) == 0 && st.Grid(SURFACE, x, y) < 0x18)
            st.SetGrid(SURFACE, x, y, (st.Rand4() + st.U8(G, 0x105a) + 0x10) & 0xff);
        if (S16(st.U16(G, 0x1054)) > 0)
        {
            st.Inc16(G, 0x1054, -1);
            if (S16(st.U16(G, 0x1054)) % 10 == 0 && st.Rand2() != 0) st.Hooks.Effect(st, "sound", 0x2c, st.Rand256());
            return true;
        }
        st.Inc16(G, 0x1076, -1);
        if (st.U16(G, 0x1076) == 0)
        {
            st.Set16(G, 0x1076, 10);
            if (st.U16(T, 0x7b2) != 0 && st.Rand2() == 0) st.Hooks.Effect(st, "sound", 10);
        }
        Sf.PlaceCorpse(st, x, y, st.U16(G, 0x105a) != 0);
        SpDoneEating(st, a, b);
        return true;
    }

    /// <summary>0da5c.</summary>
    static void SpDoneEating(State st, int a, int b)
    {
        st.Set16(G, 0xfb8, 0);
        if (st.U16(G, 0xa06) == 1)
        {
            if (st.U16(G, 0x6ac) == 6) st.Set16(G, 0x6ac, 0);
            st.Set16(G, 0xf42, a);
            st.Set16(G, 0xf7e, b);
        }
    }

    /// <summary>The player is the spider (G:0A06 == 1, not hunting or eating): walk towards the cursor.</summary>
    static void SpiderPlayer(State st)
    {
        if (st.U16(G, 0x6ac) == 7)
        {
            int r = SpiderFindPrey(st);
            st.Set16(G, 0xffc, r);
            if (r != -2)
            {
                SpPreyChosen(st, r);
                return;
            }
        }
        else if (st.U16(G, 0x6ac) == 8)
            SpiderLash(st);
        int pa = S16(st.U16(G, 0x47c)), pb = S16(st.U16(G, 0x48a));
        int ta = S16(st.U16(G, 0xf42)), tb = S16(st.U16(G, 0xf7e));
        int dist = Mv.DistanceLo(pa, pb, ta, tb);
        if (dist < 1)
        {
            st.Set16(G, 0x1042, 2);
            return;
        }
        int d = Sf.StepTowardsSurface(st, pa, pb, ta, tb);
        if (d == -1) return;
        if (d == -2)
        {
            d = Mv.DirTo(pa, pb, ta, tb) - 1;
            if (d < 0) return;
        }
        st.Set16(G, 0x1004, st.S8(T, 0x24 + st.U16(G, 0x1004) * 8 + d));
        SpStep(st, st.U16(G, 0xa8e) != 0 && dist > 2 ? 5 : 1, false);
        var (a, b) = SpPos(st);
        st.Set16(G, 0x47c, a);
        st.Set16(G, 0x48a, b);
        st.Hooks.Effect(st, "scroll");
    }

    // ------------------------------------------------------------------------------------------- weather
    /// <summary>f_0c3d4: move rain object i to a random cell; on ground it becomes a puddle that wipes the scent.</summary>
    public static void DropObjectRandom(State st, int i)
    {
        int a = st.CrtRandMod(0x80), b = st.CrtRandMod(0x40);
        st.Set8(G, 0x256 + i, a);
        st.Set8(G, 0x2c0 + i, b);
        if (st.Grid(SURFACE, a, b) >= 0xe) return;
        st.SetGrid(SURFACE, a, b, 0x74);
        int k = (a >> 1) * 32 + (b >> 1);
        st.Set8(SIM, 0xd09f + k, 0);
        st.Set8(SIM, 0xd89f + k, 0);
        foreach (int m in new[] { 0xe09f, 0xf09f })
        {
            int v = st.U8(SIM, m + k);
            st.Set8(SIM, m + k, v >= 0x14 ? v - 0x14 : 0);
        }
        st.Set8(SIM, 0xe89f + k, 0);
        st.Set8(0x4da7, k, 0);
    }

    /// <summary>f_0c4d2: water rises to nest row `depth`: ants there start drowning (state 17), the row's cells
    /// turn to their flooded variants.</summary>
    public static void FloodRow(State st, int depth)
    {
        foreach (var n in new[] { Ng.BLACK, Ng.RED })
        {
            int i = S16(st.U16(G, n.Count));
            while (i > 0)
            {
                i--;
                int t = st.U8(SIM, n.Type + i);
                if (st.U8(SIM, n.Y + i) == depth && t != 0 && 0 < (t & 0x78) >> 3 && (t & 0x78) >> 3 < 0xc)
                    st.Set8(SIM, n.State + i, 0x11);
            }
        }
        for (int col = 0; col < 0x40; col++)
        {
            foreach (var n in new[] { Ng.BLACK, Ng.RED })
            {
                int v = st.Grid(n.Dirt, col, depth);
                st.SetGrid(n.Dirt, col, depth, v < 0x20 ? 0x4e : v + 0x2f);
            }
            st.Hooks.Effect(st, "redraw", 2, col, depth);
            st.Hooks.Effect(st, "redraw", 3, col, depth);
        }
    }

    /// <summary>f_0c56e: the water recedes from nest row `depth`.</summary>
    public static void DrainRow(State st, int depth)
    {
        for (int col = 0; col < 0x40; col++)
        {
            foreach (var n in new[] { Ng.BLACK, Ng.RED })
            {
                int v = st.Grid(n.Dirt, col, depth);
                st.SetGrid(n.Dirt, col, depth, v == 0x4e ? st.Rand(8) : v - 0x2f);
            }
            st.Hooks.Effect(st, "redraw", 2, col, depth);
            st.Hooks.Effect(st, "redraw", 3, col, depth);
        }
    }

    /// <summary>f_0c22c: rain (G:0352, yard only) grows puddles and floods the nests from below (water level
    /// G:0242); afterwards the puddles dry and the water drains.</summary>
    public static void Weather(State st)
    {
        bool yard = st.U16(G, 0xf24) == 0;
        if (st.U16(G, 0x352) != 0 && yard)
        {
            if (st.Rand(0x32) == 0) st.Hooks.Effect(st, "sound", 0x29);
            st.Set16(T, 0xc1e, 1);
            if (st.Rand(10) == 0 && S16(st.U16(G, 0x242)) > 4)
            {
                st.Inc16(G, 0x242, -1);
                FloodRow(st, S16(st.U16(G, 0x242)));
            }
            for (int i = 0; i < 100; i++)
            {
                int a = st.U8(G, 0x256 + i), b = st.U8(G, 0x2c0 + i);
                int t = st.Grid(SURFACE, a, b);
                if (0x74 <= t && t < 0x77)
                {
                    st.SetGrid(SURFACE, a, b, t + 1);
                    continue;
                }
                if (t == 0x77) st.SetGrid(SURFACE, a, b, st.Rand(0xe));
                DropObjectRandom(st, i);
            }
            return;
        }
        if (!yard) return;
        if (st.U16(T, 0xc1e) == 1)
        {
            st.Set16(T, 0xc1e, 0);
            for (int i = 0; i < 100; i++)
            {
                int a = st.U8(G, 0x256 + i), b = st.U8(G, 0x2c0 + i);
                int t = st.Grid(SURFACE, a, b);
                if (0x74 <= t && t <= 0x77) st.SetGrid(SURFACE, a, b, st.Rand(0xe));
            }
        }
        if (S16(st.U16(G, 0x242)) < 0x40 && st.Rand(10) == 0)
        {
            DrainRow(st, S16(st.U16(G, 0x242)));
            st.Inc16(G, 0x242);
        }
    }
}
