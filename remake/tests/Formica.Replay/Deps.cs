using Formica.Data;
using Formica.Sim;

namespace Formica.Replay;

/// <summary>`Formica.Replay --deps [game dir] [games] [ticks] [out]`: which bytes of the starting image (SIMANT.EXE's
/// data) the simulation reads before writing them. Plays games like `--fuzz` (all four modes, clicks, commands,
/// cheats, map tools, a save and load) with `State.Touch` on, and writes the ranges read from the image. These are the
/// data a build without the original files has to supply.</summary>
public static class Deps
{
    public static int Run(string gameDir, int games, int ticks, string outFile)
    {
        var s = new GameSession(gameDir);
        var needed = new bool[State.Size];
        byte[] image = ExeImage.NewState(s.Files.Flat).Mem;
        for (int g = 0; g < games; g++)
        {
            var rng = new Random(g);
            int mode = g % 4;
            State.Touch = new byte[State.Size];
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
                            case 10:
                                if (t > 200) SaveFile.Load(st, SaveFile.Save(st));
                                break;
                        }
                    }
                    s.Step();
                }
                catch (Exception)
                {
                    break;                                      // --fuzz reports these; here only the reads count
                }
                s.Hooks.YardMapWanted = false;
            }
            for (int i = 0; i < State.Size; i++)
                if ((State.Touch[i] & 2) != 0) needed[i] = true;
        }
        State.Touch = null;

        // ranges, merging gaps of up to 4 bytes
        var ranges = new List<(int lo, int hi)>();
        for (int i = 0; i < State.Size; i++)
        {
            if (!needed[i]) continue;
            if (ranges.Count > 0 && i - ranges[^1].hi <= 4) ranges[^1] = (ranges[^1].lo, i + 1);
            else ranges.Add((i, i + 1));
        }
        using var w = new StreamWriter(outFile);
        int total = 0, nonzero = 0;
        foreach (var (lo, hi) in ranges)
        {
            int nz = 0;
            for (int i = lo; i < hi; i++) if (needed[i] && image[i] != 0) nz++;
            int n = 0;
            for (int i = lo; i < hi; i++) if (needed[i]) n++;
            total += n;
            nonzero += nz;
            var bytes = string.Join(" ", image.Skip(lo).Take(Math.Min(hi - lo, 24)).Select(b => b.ToString("x2")));
            w.WriteLine($"{Replayer.Describe(lo)} +{hi - lo,-5} read {n,-5} nonzero {nz,-5} {bytes}{(hi - lo > 24 ? " ..." : "")}");
        }
        string summary = $"{games} games x up to {ticks} ticks: {ranges.Count} ranges, {total} bytes read from the image, {nonzero} of them nonzero";
        w.WriteLine(summary);
        Console.WriteLine(summary);
        Console.WriteLine($"written to {outFile}");
        return 0;
    }
}
