using Formica.Data;
using Formica.Sim;

namespace Formica.Replay;

/// <summary>`Formica.Replay --tables [game dir] [games] [ticks]`: ROADMAP A2's check. Plays each game twice from the
/// same seed and the same random player (as `--deps`: clicks, commands, cheats, map tools, save and load), once from
/// SIMANT.EXE's image and once from <see cref="GameTables"/>, and compares the two States after every tick. Bytes
/// that differed at the start and that neither side has changed since are skipped (the image's leftovers that the
/// game never reads); every other byte must match. With the environment variable TABLES_SELFTEST set, one table
/// byte is changed on the tables side, to show that the check fails.</summary>
public static class Tables
{
    public static int Run(string gameDir, int games, int ticks)
    {
        var x = new GameSession(gameDir);                         // from the EXE
        var y = new GameSession(gameDir) { UseTables = true };   // from the tables
        int failures = 0;
        long total = 0;
        for (int g = 0; g < games; g++)
        {
            int mode = g % 4, seed = 0x2000 + g * 131;
            x.NewGame(mode, seed);
            y.NewGame(mode, seed);
            if (Environment.GetEnvironmentVariable("TABLES_SELFTEST") != null) y.St.Set8(Seg.T, 0x24 + 9, 3);   // one WalkTurns entry
            var x0 = (byte[])x.St.Mem.Clone();
            var y0 = (byte[])y.St.Mem.Clone();
            var rx = new Random(g);
            var ry = new Random(g);
            int bad = -1, t = 0;
            for (; t < ticks && !x.Over && bad < 0; t++)
            {
                bool okX = Step(x, rx, t), okY = Step(y, ry, t);
                if (okX != okY) { Console.WriteLine($"game {g} mode {mode}: only one side threw at tick {t}"); bad = 0; break; }
                if (!okX) break;
                var a = x.St.Mem;
                var b = y.St.Mem;
                for (int i = 0; i < State.Size; i++)
                    if (a[i] != b[i] && !(x0[i] != y0[i] && a[i] == x0[i] && b[i] == y0[i])) { bad = i; break; }
                if (bad >= 0)
                    Console.WriteLine($"game {g} mode {mode}: differ at tick {t}: {Replayer.Describe(bad)} exe {a[bad]:x2} tables {b[bad]:x2}");
            }
            total += t;
            if (bad >= 0) failures++;
        }
        Console.WriteLine(failures == 0 ? $"{games} games, {total} ticks: games from the tables match games from SIMANT.EXE"
                                        : $"{failures} of {games} games differ");
        return failures == 0 ? 0 : 1;
    }

    /// <summary>One tick with a random player action; false if the port threw (both sides must agree).</summary>
    static bool Step(GameSession s, Random rng, int t)
    {
        var st = s.St;
        try
        {
            if (rng.Next(40) == 0)
            {
                int view = 1 + rng.Next(3);
                int a = rng.Next(view == 1 ? 128 : 64), b = rng.Next(64);
                switch (rng.Next(11))
                {
                    case 0: case 1: case 2: s.WalkTo(view, a, b, rng.Next(3) == 0); break;
                    case 3: s.WalkTo(view, a, b); st.Set16(Seg.G, 0xa8e, 1); break;
                    case 4: Commands.Command(st, rng.Next(13)); break;
                    case 5:
                        if (st.U16(Seg.G, 0x105e) == 0xa) Commands.ExchangeClick(st, view, a, b);
                        else if (st.U16(Seg.G, 0xa06) == 1) Commands.SpiderClick(st, a, b, rng.Next(2));
                        break;
                    case 6:
                        st.Set16(Seg.G, 0x32e, view);
                        st.Set16(Seg.G, 0x104c, rng.Next(7));
                        st.BiosKbd = rng.Next(2) * 8;
                        MapTools.ApplyTool(st, a, b);
                        st.BiosKbd = 0;
                        break;
                    case 7:
                        foreach (char c in Cheats.CODES[rng.Next(Cheats.CODES.Length)]) Cheats.Cheat(st, c);
                        break;
                    case 8: st.Set16(Seg.T, 0x7be, rng.Next(6) == 0 ? 0xffff : rng.Next(5)); break;
                    case 9: s.Speed = rng.Next(3); break;
                    case 10: if (t > 200) SaveFile.Load(st, SaveFile.Save(st)); break;
                }
            }
            s.Step();
            s.Advance(0.02);
            s.Hooks.YardMapWanted = false;
            return true;
        }
        catch (Exception)
        {
            return false;
        }
    }
}
