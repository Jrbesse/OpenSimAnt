using System.IO.Compression;
using System.Text.Json;
using OpenSimAnt.Sim;

namespace OpenSimAnt.Replay;

/// <summary>OpenSimAnt.Replay --longrun [file]: replays a long-run recording of tools/ref/longrun.py on the C# port.
/// The recording (JSON lines) starts each game with the Python State before its new game ("state", t = -1), then
/// lists what both sides did, in order: "poke" (a memory write), "call" (a reference function by its Python name,
/// resolved as the trace replay does), "step" (set the clock, one SimStep), and every n ticks "state" (the
/// Python State after that tick), which the C# State must equal byte for byte.</summary>
public static class LongRun
{
    public static string DefaultFile() => Path.Combine(TracePaths.DefaultDir(), "..", "longrun", "longrun.jsonl");

    public static int Run(string path)
    {
        if (!File.Exists(path))
        {
            Console.WriteLine($"no recording at {path} (python tools/ref/longrun.py [ticks] --out)");
            return 1;
        }
        State st = null;
        string game = null;
        int tick = 0, checkpoints = 0, games = 0;
        bool ok = true, skip = false;
        var t0 = DateTime.Now;
        int line = 0;
        foreach (var text in File.ReadLines(path))
        {
            line++;
            using var doc = JsonDocument.Parse(text);
            var e = doc.RootElement;
            string k = e.GetProperty("k").GetString();
            if (k == "game")
            {
                if (game != null) Report(game, !skip, tick, checkpoints, t0);
                game = $"mode {e.GetProperty("mode").GetInt32()} crt {e.GetProperty("crt").GetInt64():x}";
                games++;
                tick = 0;
                checkpoints = 0;
                skip = false;
                t0 = DateTime.Now;
                st = null;
                pendingClock = e.GetProperty("clock").GetInt64();
                continue;
            }
            if (skip) continue;
            switch (k)
            {
                case "state":
                {
                    var mem = Inflate(Convert.FromBase64String(e.GetProperty("mem").GetString()));
                    int t = e.GetProperty("t").GetInt32();
                    if (st == null)
                    {
                        st = new State(mem) { Clock = pendingClock, BiosKbd = 0, Hooks = new TestSimPlayer() };
                        break;
                    }
                    checkpoints++;
                    int nd = 0;
                    var sb = new System.Text.StringBuilder();
                    for (int i = 0; i < State.Size; i++)
                        if (st.Mem[i] != mem[i])
                        {
                            if (nd < 10) sb.Append($"\n      {Replayer.Describe(i)}: port {st.Mem[i]:x2} expected {mem[i]:x2}");
                            nd++;
                        }
                    if (nd > 0)
                    {
                        Console.WriteLine($"  {game}: MISMATCH at the checkpoint after tick {t} (line {line}): {nd} bytes differ{sb}");
                        ok = false;
                        skip = true;
                    }
                    break;
                }
                case "poke":
                {
                    int seg = e.GetProperty("seg").GetInt32(), off = e.GetProperty("off").GetInt32(), val = e.GetProperty("val").GetInt32();
                    if (e.GetProperty("byte").GetBoolean()) st.Set8(seg, off, val);
                    else st.Set16(seg, off, val);
                    break;
                }
                case "call":
                {
                    string f = e.GetProperty("f").GetString();
                    var args = e.GetProperty("args").EnumerateArray().ToArray();
                    var mi = Replayer.FindMethod(f, args.Length) ?? throw new MissingMethodException(f);
                    var ps = mi.GetParameters();
                    var call = new object[ps.Length];
                    call[0] = st;
                    for (int i = 1; i < ps.Length; i++)
                        call[i] = i - 1 < args.Length ? Replayer.Convert(args[i - 1], ps[i].ParameterType) : ps[i].DefaultValue;
                    try
                    {
                        mi.Invoke(null, call);
                    }
                    catch (System.Reflection.TargetInvocationException ex)
                    {
                        Console.WriteLine($"  {game}: {f} threw at tick {tick} (line {line}): {ex.InnerException?.GetType().Name}: {ex.InnerException?.Message}");
                        ok = false;
                        skip = true;
                    }
                    break;
                }
                case "step":
                    st.Clock = e.GetProperty("clock").GetInt64();
                    try
                    {
                        OpenSimAnt.Sim.Sim.SimStep(st);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"  {game}: SimStep threw at tick {tick} (line {line}): {ex.GetType().Name}: {ex.Message}");
                        ok = false;
                        skip = true;
                    }
                    tick++;
                    break;
            }
        }
        if (game != null) Report(game, !skip, tick, checkpoints, t0);
        Console.WriteLine($"{games} game(s): " + (ok ? "ALL OK" : "SOME MISMATCHES"));
        return ok ? 0 : 1;
    }

    static long pendingClock;

    static void Report(string game, bool good, int tick, int checkpoints, DateTime t0) =>
        Console.WriteLine($"{game}: {(good ? "OK" : "MISMATCH")} ({tick} ticks, {checkpoints} checkpoints, {(DateTime.Now - t0).TotalSeconds:0.0}s)");

    static byte[] Inflate(byte[] data)
    {
        using var z = new ZLibStream(new MemoryStream(data), CompressionMode.Decompress);
        using var ms = new MemoryStream();
        z.CopyTo(ms);
        return ms.ToArray();
    }
}
