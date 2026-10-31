using OpenSimAnt.Data;
using OpenSimAnt.Sim;

namespace OpenSimAnt.Replay;

/// <summary>`OpenSimAnt.Replay --fuzz [game dir] [games] [ticks]`: plays games from SIMANT.EXE with random clicks,
/// commands, cheats and map tools, and reports every exception (paths a player could reach that the port
/// leaves unported or that read uninitialised data in the original).</summary>
public static class Fuzz
{
    public static int Run(string gameDir, int games, int ticks)
    {
        var s = new GameSession(gameDir);
        var seen = new Dictionary<string, int>();
        int total = 0;
        for (int g = 0; g < games; g++)
        {
            var rng = new Random(g);
            int mode = g % 4;                                  // 0 the tutorial, 1 Quick, 2 Full, 3 Experimental
            s.NewGame(mode, 0x1000 + g * 77);
            for (int t = 0; t < ticks && !s.Over; t++)
            {
                var st = s.St;
                try
                {
                    if (rng.Next(40) == 0)
                    {
                        int view = 1 + rng.Next(3);
                        int a = rng.Next(view == 1 ? 128 : 64), b = rng.Next(64);
                        switch (rng.Next(10))
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
                        }
                    }
                    s.Step();
                }
                catch (Exception ex)
                {
                    total++;
                    var frame = (ex.StackTrace ?? "").Split('\n').FirstOrDefault(l => l.Contains("OpenSimAnt.Sim"))?.Trim() ?? "";
                    string key = ex.GetType().Name + ": " + ex.Message + " " + frame;
                    seen[key] = seen.GetValueOrDefault(key) + 1;
                    if (seen[key] == 1) Console.WriteLine($"game {g} mode {mode} tick {t}: {key}");
                    break;
                }
            }
            if (s.Hooks.YardMapWanted)
            {
                s.Hooks.YardMapWanted = false;
            }
        }
        Console.WriteLine($"{games} games x up to {ticks} ticks: {total} games stopped by an exception, {seen.Count} distinct");
        return total == 0 ? 0 : 1;
    }
}
