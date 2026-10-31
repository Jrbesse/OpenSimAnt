using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;

namespace OpenSimAnt.Sim;

/// <summary>The cheat codes (f_6a920, overlay 10): called once per typed key (via thunk 0x2f924 from f_74386).
/// Typed keys go NOT-ed into G:0B0A[T:06DE]; the table at T:067E holds 4-byte codes, also NOT-ed, ending at a
/// 0 byte. A key that leaves no code with a matching prefix clears the buffer (and is not retried as the
/// start of a new code); a full match clears it and runs the cheat. See SIM_NOTES "Cheat codes".
/// Screen-only effects: 'sound' (f_00ed8(n, 0, 0x7E)), 'cheat' (f_277da("CHEAT %d")), 'message'
/// (f_71b1a(0, id, 0)), 'joke' (the screen effects between its two messages), 'win_screen'.</summary>
public static class Cheats
{
    public const int TABLE = 0x67e, LEN = 0x6de, BUF = 0xb0a;

    public static readonly string[] CODES =
        "oops rand erad FUND joke hole HOLE qeen QEEN eggs EGGS heal HEAL zhea ZHEA just will mick jeff joel fred jenn susi".Split(' ');

    /// <summary>X = (X == 0); returns the new value.</summary>
    static int Toggle(State st, int seg, int off)
    {
        int v = st.U16(seg, off) == 0 ? 1 : 0;
        st.Set16(seg, off, v);
        return v;
    }

    static void OnOffSound(State st, int on) => st.Hooks.Effect(st, "sound", on != 0 ? 2 : 1);

    static void Brood(State st, NestKind n, int @base)
    {
        for (int k = 0; k < 16; k++)
        {
            int stage = st.CrtRandMod(6) + @base;
            int b = S16(st.U16(G, 0x48a)) + st.S8(T, 8 + st.Rand8());
            int a = S16(st.U16(G, 0x47c)) + st.S8(T, st.Rand8());
            Nest.SpawnBrood(st, n, a, b, stage);
        }
    }

    /// <summary>f_6a920(key).</summary>
    public static void Cheat(State st, int key)
    {
        int n = st.U16(T, LEN);
        st.Set8(G, BUF + n, ~key & 0xff);
        n++;
        st.Set16(T, LEN, n);
        int i = 0;
        while (st.U8(T, TABLE + 4 * i) != 0)
        {
            bool all = true;
            for (int k = 0; k < n; k++)
                if (st.U8(T, TABLE + 4 * i + k) != st.U8(G, BUF + k)) { all = false; break; }
            if (all) break;
            i++;
        }
        if (st.U8(T, TABLE + 4 * i) == 0 || n >= 4)
        {
            st.Set16(T, LEN, 0);
            for (int k = 0; k < 4; k++) st.Set8(G, BUF + k, 0);
        }
        if (st.U8(T, TABLE + 4 * i) == 0 || n < 4) return;
        st.Hooks.Effect(st, "cheat", i);
        Run(st, i);
    }

    /// <summary>The switch on the matched code's index.</summary>
    public static void Run(State st, int i)
    {
        void Sound(int k) => st.Hooks.Effect(st, "sound", k);
        switch (i)
        {
            case 0:                                                   // oops
                Sound(10);
                st.Set16(G, 0x850, st.U16(G, 0x850) + 10);
                break;
            case 1: case 2:                                           // rand, erad
                Sound(1);
                Player.SetHealth(st, i == 1 ? 100 : 1);
                break;
            case 3:                                                   // FUND
                st.Hooks.Effect(st, "message", 0x2724);
                break;
            case 4:                                                   // joke
                st.Hooks.Effect(st, "message", 0x2726);
                st.Hooks.Effect(st, "joke", null);
                st.Hooks.Effect(st, "message", 0x2728);
                break;
            case 5: case 6:                                           // hole, HOLE
            {
                var n = i == 5 ? Nest.BLACK : Nest.RED;
                for (int col = 0; col < 0x40; col++) Nest.MakeSurfaceHole(st, n, col);
                break;
            }
            case 7: case 8:                                           // qeen, QEEN
            {
                var n = i == 7 ? Nest.BLACK : Nest.RED;
                NewGame.QueenChamber(st, n, S16(st.U16(G, 0x47c)) + 2, S16(st.U16(G, 0x48a)), 2);
                break;
            }
            case 9: Brood(st, Nest.BLACK, 1); break;                  // eggs
            case 10: Brood(st, Nest.RED, 0x81); break;                // EGGS
            case 11: st.Set16(G, 0x10be, 100); break;                 // heal
            case 12: st.Set16(G, 0x1fe, 100); break;                  // HEAL
            case 13: st.Set16(G, 0x1fe, 0); break;                    // zhea
            case 14:                                                  // ZHEA
                st.Set16(T, 0xc18, 0);
                st.Set16(G, 0x10be, 0);
                break;
            case 15:                                                  // just (NewColonyNoop does nothing)
                st.Set16(G, 0x7c8, st.U16(G, 0x7c8) + 10);
                Sound(0x29);
                break;
            case 16: case 17:                                         // will, mick
                OnOffSound(st, Toggle(st, T, i == 16 ? 0xc14 : 0xc12));
                break;
            case 18:                                                  // jeff
                Sound(2);
                for (int cell = 0; cell < 12 * 16; cell++)
                {
                    st.Set8(T, 0xa4 + cell, st.U8(T, 0xa4 + cell) + 4);
                    st.Set16(G, 0xa90, st.U16(G, 0xa90) + 1);
                }
                break;
            case 19:                                                  // joel
                Sound(1);
                for (int cell = 0; cell < 12 * 16; cell++)
                {
                    if (st.Rand2() == 0)
                    {
                        st.Set8(T, 0xa4 + cell, st.U8(T, 0xa4 + cell) + 1);
                        st.Set16(G, 0xa90, st.U16(G, 0xa90) + 1);
                    }
                    else
                    {
                        st.Set8(T, 0x164 + cell, st.U8(T, 0x164 + cell) + 1);
                        st.Set16(G, 0xac4, st.U16(G, 0xac4) + 1);
                    }
                }
                break;
            case 20:                                                  // fred
                st.Hooks.Effect(st, "win_screen", null);
                break;
            case 21:                                                  // jenn
            {
                int on = Toggle(st, T, 0xc16);
                if (on != 0) st.Set16(G, 0xf78, 100);
                OnOffSound(st, on);
                break;
            }
            case 22:                                                  // susi
            {
                int on = Toggle(st, T, 0xc18);
                if (on != 0) st.Set16(G, 0x10be, 100);
                OnOffSound(st, on);
                break;
            }
        }
    }
}

/// <summary>Hidden debug commands of the resident code (segment 015b): adding and killing ants, clearing food,
/// and a random one of 15 actions (menu command 0x112, f_022bc). Ctrl-clicks on the control of command 0x110
/// reach the first three through f_6f733 (see SIM_NOTES "Debug commands").</summary>
public static class DebugCommands
{
    const int SURFACE = 0x0180, OCC = 0x6180;
    const int STYPE = 0xad3b, SX = 0xa180, SY = 0xa569;

    /// <summary>f_134b8: is the player at (a, b) in `view` (0 means the surface)? The spider (G:0A06 == 1)
    /// covers every surface cell centre within squared distance 0x200 of its position (G:0F12, G:0F34).</summary>
    public static int PlayerAt(State st, int view, int a, int b)
    {
        if (st.U16(G, 0x48c) != (view != 0 ? view : 1)) return 0;          // f_135b0
        if (st.U16(G, 0xa06) == 1)
        {
            if (S16(view) > 1) return 0;
            long d = Colony.Distance(a * 16 + 8, b * 16 + 8, S16(st.U16(G, 0xf12)), S16(st.U16(G, 0xf34)));
            return d < 0x200 ? 1 : 0;
        }
        int o;
        if (0 <= view && view <= 1) o = st.Grid(OCC, a, b);
        else if (view == 2) o = st.Grid(Nest.BLACK.Cells, a, b);
        else if (view == 3) o = st.Grid(Nest.RED.Cells, a, b);
        else throw new NotImplementedException("f_134b8: a view outside 0..3 reads an uninitialised local");
        return Movement.IsYellow(o) ? 1 : 0;
    }

    /// <summary>f_015be: 32 surface ants of one colony (T:0798 == 1: as many as fit under 1000), then the census.</summary>
    public static void AddAnts(State st, bool black)
    {
        int count = S16(st.U16(G, 0xd6a));
        if (count < 1000)
        {
            int n = st.U16(T, 0x798) == 1 ? 1000 - count : 0x20;
            NewGame.AddSurfaceAnts(st, n, !black);
        }
        World.CensusAndAdvise(st);
    }

    /// <summary>f_0161f: up to 51 surface ants of one colony die, newest first (red ones on the player are spared).</summary>
    public static void KillAnts(State st, bool black)
    {
        NestGrid.CompactSurface(st);
        World.CensusAndAdvise(st);
        int killed = 0;
        for (int i = S16(st.U16(G, 0xd6a)) - 1; i >= 0; i--)
        {
            int t = st.U8(SIM, STYPE + i);
            int a = st.U8(SIM, SX + i), b = st.U8(SIM, SY + i);
            if (black)
            {
                if ((t & 0x80) != 0) continue;
                Surface.PlaceCorpse(st, a, b, false);
            }
            else
            {
                if ((t & 0x80) == 0 || PlayerAt(st, 1, a, b) != 0) continue;
                Surface.PlaceCorpse(st, a, b, true);
            }
            st.Set8(SIM, STYPE + i, 0);
            killed++;
            if (killed > 0x32) break;
        }
        NestGrid.CompactSurface(st);
        World.CensusAndAdvise(st);
    }

    /// <summary>f_01707: every food crumb on the surface becomes plain ground (a random tile 0..15).</summary>
    public static void ClearFood(State st)
    {
        for (int a = 0; a < 0x80; a++)
            for (int b = 0; b < 0x40; b++)
                if (World.IsFoodTile(st, st.Grid(SURFACE, a, b))) st.SetGrid(SURFACE, a, b, st.Rand16());
        st.Set16(G, 0x1040, 0);
    }

    static int Toggle(State st, int off)
    {
        int v = st.U16(T, off) == 0 ? 1 : 0;
        st.Set16(T, off, v);
        return v;
    }

    /// <summary>f_022bc: one of 15 actions, chosen by C rand() % 15.</summary>
    public static void RandomAction(State st)
    {
        int k = st.CrtRandMod(15);
        var fx = st.Hooks;
        switch (k)
        {
            case 0: case 1: case 2:
                AddAnts(st, k == 2);
                AddAnts(st, k == 2);
                break;
            case 3: case 4:
                KillAnts(st, k == 4);
                KillAnts(st, k == 4);
                break;
            case 5: Colony.DropFood(st, 0x96, 1); break;
            case 6:
                fx.Effect(st, "sound2", 0x20, 0, 0x7e);                     // f_00f02
                ClearFood(st);
                break;
            case 7: fx.Effect(st, "music", 0); break;
            case 8: case 9:
            {
                var n = k == 8 ? Nest.RED : Nest.BLACK;
                for (int i = 0; i < 0x20; i++) Nest.MakeSurfaceHole(st, n, 2 * i);
                break;
            }
            case 10:
                st.Set16(T, 0xc18, 0);
                st.Set16(G, 0x10be, 0);
                st.Set16(G, 0x1fe, 0);
                break;
            case 11: fx.Effect(st, "sound", Toggle(st, 0xc14) != 0 ? 2 : 1); break;
            case 12: Toggle(st, 0xc12); break;
            case 13:
                fx.Effect(st, "message", 0x2726);
                fx.Effect(st, "music", 1);
                fx.Effect(st, "message", 0x2728);
                break;
            case 14:
                st.Set16(G, 0x6ac, 8);                                    // the spider lashes out
                fx.Effect(st, "sound", 2, 0x2b77, 0x7e);
                break;
        }
    }
}

/// <summary>The map's event markers: where on screen the latest hatching, fight, egg laying and resting
/// happened. The simulation reports these only while the patch is visible (T:07B2), through
/// st.Hooks.Effect with 'brood', 'fight', 'queen' or 'rest' and (a, b, view). A renderer calls Record from its
/// effect hook to keep these globals as the original does. See SIM_NOTES "Event markers".</summary>
public static class Markers
{
    // kind: (gate, latched a / b / view (set by f_06a4d), recorded a / b / view)
    static readonly Dictionary<string, (int gate, int[] latched, int[] rec)> KINDS = new()
    {
        ["brood"] = (0xef6, new[] { 0x8de, 0x8e0, 0xad8 }, new[] { 0x852, 0x854, 0xaca }),   // f_0678a
        ["fight"] = (0xf06, new[] { 0x9f2, 0x9f4, 0xb06 }, new[] { 0x8ec, 0x8ee, 0xaea }),   // f_06802
        ["queen"] = (0xf10, new[] { 0xa8a, 0xa8c, 0xc3a }, new[] { 0xa02, 0xa04, 0xb08 }),   // f_0687a
        ["rest"] = (0xf2e, new[] { 0xab2, 0xab4, 0xd9a }, new[] { 0xaa2, 0xaa4, 0xd68 }),    // f_068f2
    };

    public static bool IsMarker(string kind) => KINDS.ContainsKey(kind);

    /// <summary>f_06725: (a, b) is inside the map window showing `view` (origin G:0508 / G:050A, size G:10E0 x
    /// G:10DE; the top three rows of the window don't count).</summary>
    public static int OnScreen(State st, int view, int a, int b)
    {
        if (st.U16(G, 0x32e) != (view & 0xffff)) return 0;
        int x0 = S16(st.U16(G, 0x508)), y0 = S16(st.U16(G, 0x50a));
        if (!(x0 <= a && a < x0 + S16(st.U16(G, 0x10e0)))) return 0;
        if (!(y0 <= b - 3 && b < y0 + S16(st.U16(G, 0x10de)))) return 0;
        return 1;
    }

    /// <summary>f_0678a / f_06802 / f_0687a / f_068f2: while the marker is free (gate 0) and the spot is on
    /// screen, record it; the spot the animation has latched counts up the gate instead (no new marker there).</summary>
    public static void Record(State st, string kind, int a, int b, int view)
    {
        var (gate, latched, rec) = KINDS[kind];
        a = S16(a);
        b = S16(b);
        view = S16(view);
        if (st.U16(G, gate) != 0 || OnScreen(st, view, a, b) == 0) return;
        if (st.U16(G, latched[0]) == (a & 0xffff) && st.U16(G, latched[1]) == (b & 0xffff)
            && st.U16(G, latched[2]) == (view & 0xffff))
        {
            st.Set16(G, gate, st.U16(G, gate) + 1);
            return;
        }
        st.Set16(G, rec[0], a & 0xffff);
        st.Set16(G, rec[1], b & 0xffff);
        st.Set16(G, rec[2], view & 0xffff);
    }
}

/// <summary>Speech balloons (f_06a4d, from the window draw f_038a6 via f_07128): the ants' remarks at the spots
/// the event recorders (Markers) found on screen. Runs only while the patch is visible (T:07B2) and T:07BE is
/// -1. Each source latches its recorded spot once (its gate becomes non-zero), then times its balloon with the
/// real-time clock: when a timer runs out it is re-armed at clock + a random delay and a coin decides whether
/// a balloon shows, each showing advancing to the next line of its string list. The line is drawn by
/// f_0696a(a, b, view, style, line): st.Hooks.Effect(st, "balloon", a, b, view, style, (list, index)).</summary>
public static class Balloons
{
    sealed record Timer(int Off, Func<State, int> Delay, int Const, Func<State, int> Chance, int Shown, int Idx, int Table, int Lines, int Style);

    sealed record Source(int Gate, int[] Rec, int[] Lat, int[] Clear, Timer[] Timers);

    static readonly Source[] SOURCES =
    {
        new(0xf06, new[] { 0x8ec, 0x8ee, 0xaea }, new[] { 0x9f2, 0x9f4, 0xb06 }, Array.Empty<int>(), new[]
        {
            new Timer(0x50c, s => s.Rand32(), 0x3c, s => s.Rand2(), 0x1046, 0xf3c, 0x20a, 8, 0),    // the black ant's taunts
            new Timer(0x732, s => s.Rand32(), 0x3c, s => s.Rand2(), 0x1064, 0xff8, 0x218, 8, 1),    // the red ant's
        }),
        new(0xef6, new[] { 0x852, 0x854, 0xaca }, new[] { 0x8de, 0x8e0, 0xad8 }, new[] { 0x104a }, new[]
        {
            new Timer(0x59a, s => s.Rand32(), 0xaa, s => s.Rand4(), 0x104a, 0xf7a, 0x21c, 15, 2),
        }),
        new(0xf10, new[] { 0xa02, 0xa04, 0xb08 }, new[] { 0xa8a, 0xa8c, 0xc3a }, new[] { 0x1062 }, new[]
        {
            new Timer(0x620, s => s.Rand32(), 0xb4, s => s.Rand4(), 0x1062, 0xfc0, 0x234, 8, 2),
        }),
        new(0xf2e, new[] { 0xaa2, 0xaa4, 0xd68 }, new[] { 0xab2, 0xab4, 0xd9a }, new[] { 0x107c }, new[]
        {
            new Timer(0x7c4, s => s.Rand64(), 0x78, s => s.Rand2(), 0x107c, 0x103a, 0x23a, 8, 2),
        }),
    };

    /// <summary>f_06a4d.</summary>
    public static void Run(State st)
    {
        if (st.U16(T, 0x7b2) == 0 || st.U16(T, 0x7be) != 0xffff) return;
        foreach (var src in SOURCES)
        {
            if (st.U16(G, src.Gate) == 0 && S16(st.U16(G, src.Rec[0])) >= 0 && S16(st.U16(G, src.Rec[1])) >= 0)
            {
                for (int k = 0; k < 3; k++) st.Set16(G, src.Lat[k], st.U16(G, src.Rec[k]));
                st.Set16(G, src.Gate, st.U16(G, src.Gate) + 1);
                foreach (var t in src.Timers) st.Set32(G, t.Off, 0);
                foreach (int off in src.Clear) st.Set16(G, off, 0);
            }
            if (S16(st.U16(G, src.Gate)) <= 0) continue;
            if (st.U16(G, 0x47e) == 0)
            {
                foreach (var t in src.Timers)
                {
                    if (S32(st.U32(G, t.Off)) < S32(st.ReadClock()))
                    {
                        st.Set32(G, t.Off, (st.ReadClock() + t.Delay(st) + t.Const) & 0xffffffffL);
                        if (t.Chance(st) == 0)
                        {
                            st.Set16(G, t.Shown, 1);
                            int i = st.U16(G, t.Idx) + 1;
                            st.Set16(G, t.Idx, S16(i) >= t.Lines ? 0 : i);
                        }
                        else
                            st.Set16(G, t.Shown, 0);
                    }
                }
            }
            foreach (var t in src.Timers)
            {
                if (st.U16(G, t.Shown) != 0)
                {
                    int a = st.U16(G, src.Lat[0]), b = st.U16(G, src.Lat[1]), view = st.U16(G, src.Lat[2]);
                    st.Hooks.Effect(st, "balloon", S16(a), S16(b), S16(view), t.Style, (t.Table, st.U16(G, t.Idx)));
                }
            }
        }
    }
}

/// <summary>The Behavior Control and Caste Control triangles (windows 18 / 19): where the marker sits for the
/// colony's three weights, and the weights a click in the triangle sets. Behaviour weights G:049E / 04A0 /
/// 04A2 = forage (apex), dig (bottom left), nurse (bottom right); caste weights G:0482 / 0484 / 0486 =
/// breeders (apex), workers (bottom left), soldiers (bottom right). Each set sums to 0xFFFF. The triangle is
/// the rectangle of item 0x120D / 0x130D (f_07980), kept at G:3816 / G:3822 with its sizes G:3814 (width),
/// G:3810 = G:3812 (half width), G:380E (height) and G:382E (32-bit half width &lt;&lt; 8 / height); the marker
/// point is G:0358 / G:022E (f_07a57 / f_07a19).</summary>
public static class Panels
{
    /// <summary>f_07980(item, out): apex (left + w/2, top), bottom left (left, bottom), bottom right (right, bottom).</summary>
    public static void Triangle(State st, (int left, int top, int right, int bottom) rect, int @out)
    {
        var (left, top, right, bottom) = rect;
        int w = (right - left) & 0xffff;
        st.Set16(G, 0x3814, w);
        st.Set16(G, 0x3812, w >> 1);
        st.Set16(G, 0x3810, w >> 1);
        int h = (bottom - top) & 0xffff;
        st.Set16(G, 0x380e, h);
        st.Set32(G, 0x382e, h != 0 ? ((long)(w >> 1) << 8) / h : 0);
        int[] pts = { left + (w >> 1), top, left, bottom, right, bottom };
        for (int i = 0; i < 6; i++) st.Set16(G, @out + 2 * i, pts[i] & 0xffff);
    }

    static long SDiv32(long a, long b)
    {
        a = (a & 0x80000000L) != 0 ? a - (1L << 32) : a;
        b = (b & 0x80000000L) != 0 ? b - (1L << 32) : b;
        long q = Math.Abs(a) / Math.Abs(b);
        return ((a >= 0) == (b >= 0) ? q : -q) & 0xffffffffL;
    }

    /// <summary>f_087c7: the marker for the weights at G:`values` (v0 apex, v1 bottom left, v2 bottom right).</summary>
    public static void ToPoint(State st, int values, int tri, int @out)
    {
        long v0 = st.U16(G, values), v2 = st.U16(G, values + 4);
        int h = st.U16(G, 0x380e);
        long y = ((0xffff - v0) * ((h - 2) & 0xffff)) / 0xffff + st.U16(G, tri + 2);
        st.Set16(G, @out + 2, y & 0xffff);
        long k = (st.U16(G, 0x3810) * v0) / 0xffff & 0xffff;
        long m = (st.U16(G, 0x3814) - 2 * k) & 0xffff;
        long ms = (m & 0x8000) != 0 ? m - 0x10000 : m;
        long x;
        if (v0 != 0xffff && ms >= 3)
        {
            x = SDiv32((v2 * ((ms - 3) & 0xffffffffL)) & 0xffffffffL, 0xffff - v0);
            x = (x + st.U16(G, tri + 4) + k) & 0xffff;
        }
        else
            x = st.U16(G, tri);
        st.Set16(G, @out, (x + 2) & 0xffff);
    }

    /// <summary>f_086a1: the weights a click at G:`point` sets.</summary>
    public static void ToValues(State st, int values, int tri, int point)
    {
        long dx = (st.U16(G, point) - st.U16(G, tri + 4)) & 0xffff;
        long dy = (st.U16(G, point + 2) - st.U16(G, tri + 2)) & 0xffff;
        long h = st.U16(G, 0x380e);
        long v0;
        if (dy > ((h - 2) & 0xffff)) v0 = 0;
        else v0 = SDiv32((((h - dy - 2) & 0xffff) * 0xffff) & 0xffffffffL, (h - 2) & 0xffff) & 0xffff;
        st.Set16(G, values, v0);
        long k = (v0 * st.U16(G, 0x3810)) / 0xffff & 0xffff;
        long m = (st.U16(G, 0x3814) - 2 * k) & 0xffff;
        long ms = (m & 0x8000) != 0 ? m - 0x10000 : m;
        if (ms <= 2)
        {
            st.Set16(G, values + 2, 0);
            st.Set16(G, values + 4, 0);
            return;
        }
        long c = (dx - k) & 0xffff;
        long cs = (c & 0x8000) != 0 ? c - 0x10000 : c;
        long v2;
        if (ms - 2 <= cs) v2 = 0xffff - v0;
        else if (cs <= 2) v2 = 0;
        else v2 = SDiv32(((0xffff - v0) * cs) & 0xffffffffL, (ms - 2) & 0xffffffffL) & 0xffff;
        st.Set16(G, values + 4, v2 & 0xffff);
        st.Set16(G, values + 2, (0xffff - v2 - v0) & 0xffff);
    }
}
