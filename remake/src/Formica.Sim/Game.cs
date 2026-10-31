using static Formica.Sim.Seg;
using static Formica.Sim.Bits;

namespace Formica.Sim;

/// <summary>The original's data the simulation reads besides the State: the flat memory image built from the
/// player's own SIMANT.EXE (tools/re/build_flat.py). Only the saved-game block table (4E4B:0000) needs it,
/// because the game reuses that memory for window buffers.</summary>
public static class GameData
{
    public static byte[] Flat;
}

/// <summary>SimStep (f_0894e): one game tick, calling every part of the simulation in the original's order.</summary>
public static class Sim
{
    /// <summary>f_0894e.</summary>
    public static void SimStep(State st)
    {
        st.Inc16(G, 0xf08);
        if (st.S16(G, 0xf08) > 0x1000) st.Set16(G, 0xf08, 0);          // the tick counter wraps after 0x1000
        st.Inc32(G, 0xc26);
        if (st.U16(T, 0x7b2) == 1)                                      // the patch is shown: reset the records
        {
            foreach (int off in new[] { 0xf06, 0xf2e, 0xf10, 0xef6 }) st.Set16(G, off, 0);
            st.Set16(G, 0x8ec, 0xffff);
            st.Set16(G, 0x8ee, 0xffff);
            foreach (int off in new[] { 0xaa2, 0xa02, 0x852 }) st.Set32(G, off, 0xffffffffL);
        }
        if ((st.U8(G, 0xf08) & 0x3f) == 0) Colony.HealthDecay(st);
        if ((st.U8(G, 0xf08) & 0x1f) == 0) World.SlowPhase(st);
        Yard.YardStep(st);                                              // f_2f7a8 → sec8 f_68513
        World.Weather(st);
        World.AntLions(st);
        World.Spider(st);
        if ((st.U8(G, 0xf08) & 1) != 0) World.Caterpillar(st);
        Colony.ColonyAdvisor(st, (a, b) => st.Hooks.Effect(st, "status", a, b));
        Colony.ResetCensus(st);
        Surface.SurfaceAntsTick(st);
        Nest.BlackNestLoop(st);                                         // f_2f79e
        RedNest.RedNestLoop(st);
        Player.YellowTick(st);                                          // f_2f794 → f_7bf7e
        Colony.StatsFromCensus(st);
        Player.PlayerAction(st);                                        // f_2f78a → f_7b7b8
        World.Advisor(st);
        if (st.U16(G, 0x376) != 0) st.Hooks.GameOver(st);               // f_2f780 → f_71d95
        st.Set16(T, 0x2c2, 1);
    }
}

/// <summary>Game flow around the simulation: the rating shown when a game ends (f_70fb0), the game-over screen
/// (f_71d95, via the vector f_2f780) and starting a game from the new-game dialog (f_725b6, via f_2f848).
/// Game modes G:0EAC: 0 tutorial, 1 Quick Game, 2 Full Game, 3 experimental. The screens themselves are UI.</summary>
public static class Game
{
    /// <summary>C long division (f_2cd42): truncates toward zero.</summary>
    static long LDiv(long a, long b)
    {
        a = S32(a);
        b = S32(b);
        long q = Math.Abs(a) / Math.Abs(b);
        return S32((a >= 0) == (b >= 0) ? q : -q);
    }

    /// <summary>f_2cddc.</summary>
    static long LMul(long a, long b) => S32(a * b);

    /// <summary>The last T:0828 entries of the 64-entry history ring, ending at G:04F4.</summary>
    static (int n, int[] idx) Window(State st)
    {
        int n = S16(st.U16(T, 0x828));
        int start = (st.U8(G, 0x4f4) - st.U8(T, 0x828)) & 0x3f;
        return (n, Enumerable.Range(0, Math.Max(n, 0)).Select(i => (start + i) & 0x3f).ToArray());
    }

    /// <summary>f_70fb0: the eight rating figures (signed words): 0 average of history G:073C, 1 % of G:0626 in
    /// G:0626 + G:06AE (history), 2 % of eggs laid that were not lost (G:0FC2 / G:1000, 100 with none), 3 %
    /// G:09FA of G:09FA + G:0A00 (100 with none); Full Game and mode 3: 4 / 5 % of yard colonies G:0A90 against
    /// G:0AC4 / G:0A9E, 6 % of the 155 yard patches outside the house held by black colonies, 7 % of the 37
    /// house patches.</summary>
    public static int[] RatingParts(State st)
    {
        var p = new int[8];
        var (n, idx) = Window(st);
        if (n > 0)
        {
            int total = 0;
            foreach (int i in idx) total = (total + st.U16(G, 0x73c + 2 * i)) & 0xffff;
            p[0] = S16(S16(total) / n);
        }
        int a = 0, b = 0;
        foreach (int i in idx)
        {
            a = (a + st.U16(G, 0x626 + 2 * i)) & 0xffff;
            b = (b + st.U16(G, 0x6ae + 2 * i)) & 0xffff;
        }
        int tot = S16(a + b);
        p[1] = tot > 0 ? S16(LDiv(100 * S16(a), tot)) : 0;
        long eggs = S32(st.U32(G, 0xfc2));
        p[2] = eggs > 0 ? S16(LDiv(LMul(eggs - S32(st.U32(G, 0x1000)), 100), eggs)) : 100;
        int x = S16(st.U16(G, 0x9fa));
        tot = S16(x + st.U16(G, 0xa00));
        p[3] = tot > 0 ? S16(S16(100 * x) / tot) : 100;
        int mode = st.U16(G, 0xeac);
        if (mode == 2 || mode == 3)
        {
            int black = S16(st.U16(G, 0xa90));
            foreach (var (k, other) in new[] { (4, 0xac4), (5, 0xa9e) })
            {
                int t = S16(black + st.U16(G, other));
                p[k] = t > 0 ? S16(LDiv(100 * black, t)) : 100;
            }
            int yard = 0, house = 0;
            for (int col = 0; col < 16; col++)
            {
                for (int row = col < 5 ? 3 : 2; row < 12; row++)
                    if (st.U8(T, 0xa4 + row * 16 + col) != 0) yard++;
                for (int row = 0; row < (col < 5 ? 3 : 2); row++)
                    if (st.U8(T, 0xa4 + row * 16 + col) != 0) house++;
            }
            p[6] = yard > 0 ? S16(LDiv(LMul(yard, 100), 0x9b)) : 0;
            p[7] = house > 0 ? S16(LDiv(LMul(house, 100), 0x25)) : 0;
        }
        return p;
    }

    /// <summary>f_70fb0: the score (32-bit) and its parts: the yellow ant's health plus 51 x the weighted parts
    /// (weights DS:2AF8), scaled by the game's length G:0C26 (Quick Game: x 29 / 10, then x ticks/100 / 41 if
    /// shorter than 4100 ticks; Full Game: x ticks/100 / 81 if shorter than 8100 ticks, then x 5), plus the
    /// ticks played.</summary>
    public static (long score, int[] parts) Rating(State st)
    {
        var p = RatingParts(st);
        long score = S16(st.U16(G, 0xf78));
        for (int i = 0; i < 8; i++) score = S32(score + LMul(S32((long)p[i] * st.S8(DS, 0x2af8 + i)), 0x33));
        long ticks = S32(st.U32(G, 0xc26));
        if (st.U16(G, 0xeac) != 2)
        {
            score = LDiv(LMul(score, 0x1d), 10);
            if (ticks < 0x1004)
            {
                long t = Math.Max(LDiv(ticks, 100), 1);
                score = LDiv(LMul(t, score), 0x29);
            }
        }
        else
        {
            if (ticks < 0x1fa4)
            {
                long t = Math.Max(LDiv(ticks, 100), 1);
                score = LDiv(LMul(t, score), 0x51);
            }
            score = LMul(score, 5);
        }
        return (S32(ticks + score), p);
    }

    static readonly long[] RankLimits = { 0x344cc, 0x68998, 0x9ce64, 0xd1330 };

    /// <summary>f_71d95: the title shown, 0..4 by score (Full Game: score / 5), 5..9 when the game was lost.</summary>
    public static int Rank(State st, long score)
    {
        if (st.U16(G, 0xeac) == 2) score = LDiv(score, 5);
        int r = 4;
        for (int i = 0; i < RankLimits.Length; i++)
            if (score < RankLimits[i])
            {
                r = i;
                break;
            }
        return st.U16(G, 0x366) != 0 ? r : r + 5;
    }

    /// <summary>f_71d95 (via f_2f780, when G:0376 is set): the rating window. Once the ending's sound has
    /// finished a fanfare plays (a Rand2 draw); the player closes the window, then picks the next game (f_725b6).</summary>
    public static int? GameOverScreen(State st)
    {
        if (st.U16(T, 0x7aa) != 0) st.Hooks.Effect(st, "sound", st.U16(G, 0x366) != 0 ? 0x2718 : 0x271a);
        var (score, parts) = Rating(st);
        st.Hooks.Effect(st, "game_over", Rank(st, score), score, parts);
        if (Player.SoundDone(st)) st.Hooks.Effect(st, "sound", st.Rand2() + 0x2713);   // f_00f28, polled with the window open
        return st.Hooks.NewGameDialog(st);
    }

    /// <summary>The new-game dialog's buttons (f_725b6): game mode (0 tutorial .. 3 experimental), or -1 quit /
    /// -2 load.</summary>
    public static readonly Dictionary<int, int> BUTTONS = new()
    {
        [0x202] = 1, [0x203] = 2, [0x204] = 3, [0x206] = 0, [0x205] = -1, [0x207] = -2,
    };

    /// <summary>f_725b6 after the dialog: start a game in `mode` (0 tutorial, 1 Quick, 2 Full, 3 experimental).</summary>
    public static void StartGame(State st, int mode)
    {
        st.Set16(G, 0xeac, mode);
        int pend = st.U16(G, 0x105e);
        if (pend == 0xa || pend == 0xb)                                  // a pending yard map edit (f_11b5f / f_11aff)
        {
            st.Set16(G, 0x105e, 0xffff);
            st.Hooks.Effect(st, "edit_tool", st.U16(G, 0x48e));          // f_2f816 → f_6e168
        }
        st.Hooks.Effect(st, "picture", 1);
        st.Set16(G, 0x354, 1);
        st.Set16(G, 0x7c8, 0);
        NewGame.NewGameStart(st);                                         // f_2f942 → f_6b36b
        if (mode == 0)                                                    // the tutorial
        {
            st.Set16(T, 0x7a4, 1);
            st.Set16(T, 0x7a6, 0);
        }
        st.Set16(T, 0x2c2, 0);
    }
}

/// <summary>Saved games (.ANT): save (f_6c328) and load (f_6c1a0, fix-ups f_6cf1a / f_6cf5b).
/// A saved game has no header: it is the game state's memory blocks, one after the other, in the order of
/// the table at 4E4B:0000 in SIMANT.EXE (entries {count, size, far pointer}, 8 bytes, ending with size 0;
/// 307 blocks, 48386 bytes). Not saved, and rebuilt on load: the surface occupancy and both nests' cells
/// (from the ant lists), the yellow ant on the map, the census. Loading starts a new game first.</summary>
public static class SaveFile
{
    public const int TABLE = 0x4e4b0;                  // flat address of 4E4B:0000

    /// <summary>[(seg, off, length)] in file order.</summary>
    public static List<(int seg, int off, int n)> Blocks()
    {
        var t = GameTables.All.First(x => x.Name == "SaveBlocks").Bytes;   // 4E4B:0000 = TABLE
        var res = new List<(int, int, int)>();
        for (int a = 0; ; a += 8)
        {
            int count = (short)(t[a] | (t[a + 1] << 8));
            int size = t[a + 2] | (t[a + 3] << 8);
            int off = t[a + 4] | (t[a + 5] << 8);
            int seg = t[a + 6] | (t[a + 7] << 8);
            if (size == 0) return res;
            res.Add((seg, off, (count * size) & 0xffff));
        }
    }

    public static int FileSize() => Blocks().Sum(b => b.n);

    /// <summary>f_6c328 (after its file dialog): the bytes of the saved game; the game counts as saved (T:02C2 = 0).</summary>
    public static byte[] Save(State st)
    {
        var res = new List<byte>();
        foreach (var (seg, off, n) in Blocks())
            for (int i = 0; i < n; i++) res.Add((byte)st.U8(seg, off + i));
        st.Set16(T, 0x2c2, 0);
        return res.ToArray();
    }

    /// <summary>f_6cf1a: a fresh game to load into.</summary>
    public static void PrepareLoad(State st)
    {
        st.Set16(G, 0x354, 1);
        st.Set32(G, 0x214, 0);
        st.Set32(G, 0x204, 0x12c);
        st.Set32(G, 0x472, 0);
        NewGame.NewGameStart(st);
    }

    /// <summary>f_6cf5b: the tile set, the occupancy and nest cells rebuilt from the ant lists (each list from
    /// one past its last ant, sic), the yellow ant back on the map, census and advisor.</summary>
    public static void FinishLoad(State st)
    {
        Terrain.SetTileset(st, st.U16(G, 0xf24) == 1 ? 1 : 0);
        for (int i = 0; i < 0x2000; i++) st.Set8(SIM, 0x6180 + i, 0);
        for (int i = 0; i < 0x1000; i++)
        {
            st.Set8(SIM, 0x8180 + i, 0);
            st.Set8(SIM, 0x9180 + i, 0);
        }
        foreach (var (count, tf, xf, yf, cells) in new[] { (0xd6a, 0xad3b, 0xa180, 0xa569, 0x6180),
                                                         (0xda8, 0xbaec, 0xb50d, 0xb702, 0x8180),
                                                         (0xeaa, 0xc4b5, 0xbed6, 0xc0cb, 0x9180) })
        {
            int i = S16(st.U16(G, count));
            while (i >= 0)
            {
                st.Set8(SIM, (cells + st.U8(SIM, xf + i) * 64 + st.U8(SIM, yf + i)) & 0xffff, st.U8(SIM, tf + i));
                i--;
            }
        }
        if (st.U16(G, 0xa06) == 0)
            Player.PutYellow(st, S16(st.U16(G, 0x48c)), S16(st.U16(G, 0x47c)), S16(st.U16(G, 0x48a)), S16(st.U16(G, 0x4c2)),
                             st.U16(G, 0x496), 0xff);
        World.CensusAndAdvise(st);                                        // f_0c20f
        st.Hooks.Effect(st, "colony_panel");                              // f_2f988 → f_7256f
        st.Hooks.Effect(st, "picture", 1);
    }

    /// <summary>f_6c1a0 (after its file dialog): load a saved game. A short file is a read error: the blocks
    /// read so far stay, the game mode becomes -1 (no game) and nothing is rebuilt. Returns true if loaded.</summary>
    public static bool Load(State st, byte[] data)
    {
        st.Set16(T, 0x2c2, 0);
        PrepareLoad(st);
        int pos = 0;
        foreach (var (seg, off, n) in Blocks())
        {
            int got = Math.Max(0, Math.Min(n, data.Length - pos));                // read() copies what there is
            for (int i = 0; i < got; i++) st.Set8(seg, off + i, data[pos + i]);
            pos += n;
            if (got != n)
            {
                st.Hooks.Effect(st, "message", 0x2757);                   // "Read error, game not loaded"
                st.Set16(G, 0xeac, 0xffff);
                return false;
            }
        }
        st.Hooks.Effect(st, "edit_tool", 1);                              // f_2f97e, f_2f816(1): menus
        FinishLoad(st);
        return true;
    }
}
