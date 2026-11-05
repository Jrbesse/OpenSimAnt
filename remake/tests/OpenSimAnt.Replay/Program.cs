using OpenSimAnt.Replay;

// OpenSimAnt.Replay [trace files or directories...] [--func substring] [--notes n] [--quiet] [--allow-empty]
// Replays the Python reference's recorded calls on the C# port (default: remake/build/traces).
if (args.Length > 0 && args[0] == "--smoke")
    return OpenSimAnt.Replay.Smoke.Run(args.Length > 1 ? args[1] : Path.Combine(TracePaths.DefaultDir(), "..", "..", ".."),
                                    args.Length > 2 ? int.Parse(args[2]) : 2000,
                                    args.Length > 3 ? args[3] : Path.Combine(TracePaths.DefaultDir(), "..", "smoke"));
if (args.Length > 0 && args[0] == "--songs")
    return OpenSimAnt.Replay.Songs.Run(args.Length > 1 ? args[1] : Path.Combine(TracePaths.DefaultDir(), "..", "..", ".."),
                                    args.Length > 2 ? args[2] : Path.Combine(TracePaths.DefaultDir(), "..", "songs"));
if (args.Length > 0 && args[0] == "--longrun")
    return OpenSimAnt.Replay.LongRun.Run(args.Length > 1 ? args[1] : OpenSimAnt.Replay.LongRun.DefaultFile());
if (args.Length > 0 && args[0] == "--measure")
    return OpenSimAnt.Replay.Measure.Run(args.Length > 1 ? args[1] : "..",
                                      args.Length > 2 ? args[2] : Path.Combine(TracePaths.DefaultDir(), "..", "..", "..", "docs", "clean_pack", "data"));
if (args.Length > 0 && args[0] == "--export-pack")
    return OpenSimAnt.Replay.ExportPack.Run(args.Length > 1 ? args[1] : "..",
                                         args.Length > 2 ? args[2] : Path.Combine(TracePaths.DefaultDir(), "..", "original_pack.zip"));
if (args.Length > 0 && args[0] == "--tables")
    return OpenSimAnt.Replay.Tables.Run(args.Length > 1 ? args[1] : "..", args.Length > 2 ? int.Parse(args[2]) : 40,
                                     args.Length > 3 ? int.Parse(args[3]) : 20000);
if (args.Length > 0 && args[0] == "--deps")
    return OpenSimAnt.Replay.Deps.Run(args.Length > 1 ? args[1] : "..", args.Length > 2 ? int.Parse(args[2]) : 40,
                                   args.Length > 3 ? int.Parse(args[3]) : 5000,
                                   args.Length > 4 ? args[4] : Path.Combine(TracePaths.DefaultDir(), "..", "deps.txt"));
if (args.Length > 0 && args[0] == "--fuzz")
    return OpenSimAnt.Replay.Fuzz.Run(args.Length > 1 ? args[1] : "..", args.Length > 2 ? int.Parse(args[2]) : 30,
                                   args.Length > 3 ? int.Parse(args[3]) : 3000);
var paths = new List<string>();
string filter = null;
int notes = 4;
bool quiet = false;
bool allowEmpty = false;                                                // B8: a 0/0 row fails the run unless --allow-empty asks for it
for (int i = 0; i < args.Length; i++)
{
    if (args[i] == "--func") filter = args[++i];
    else if (args[i] == "--notes") notes = int.Parse(args[++i]);
    else if (args[i] == "--quiet") quiet = true;
    else if (args[i] == "--allow-empty") allowEmpty = true;
    else paths.Add(args[i]);
}
if (paths.Count == 0) paths.Add(TracePaths.DefaultDir());
var files = paths.SelectMany(p => Directory.Exists(p) ? (IEnumerable<string>)Directory.GetFiles(p, "*.trace").OrderBy(x => x) : new[] { p }).ToList();
bool allOk = true;
int empty = 0;                                                          // trace files that record no calls (B8)
foreach (var file in files)
{
    var rep = new Replayer { MaxNotes = notes };
    foreach (var rec in TraceReader.Read(file))
    {
        if (filter != null && !rec.Func.Contains(filter)) continue;
        rep.Run(rec);
    }
    int calls = rep.Stats.Values.Sum(s => s.Calls), ok = rep.Stats.Values.Sum(s => s.Ok);
    if (calls == 0)                                                         // nothing ran: an empty trace, or a filter that matched nothing
    {
        empty++;
        Console.WriteLine(filter == null
            ? $"{Path.GetFileName(file)}: 0/0 -- WARNING: the file records no calls, this row proves nothing"
            : $"{Path.GetFileName(file)}: 0/0 with --func '{filter}' -- the filter matched nothing, this row proves nothing");
    }
    else Console.WriteLine($"{Path.GetFileName(file)}: {ok}/{calls} OK");
    foreach (var (f, s) in rep.Stats.OrderBy(k => k.Key))
    {
        if (s.Ok == s.Calls && quiet) continue;
        string status = s.Missing > 0 ? "NOT PORTED" : s.Ok == s.Calls ? "ok" : "MISMATCH";
        Console.WriteLine($"  {f}: {s.Ok}/{s.Calls} {status}");
        foreach (var n in s.Notes) Console.WriteLine("    " + n);
        if (s.Ok != s.Calls) allOk = false;
    }
}
if (empty > 0)
{
    Console.WriteLine($"WARNING: {empty} trace file(s) replayed no calls (the 0/0 rows above); they are not evidence -- record a real trace or delete the file");
    if (!allowEmpty) allOk = false;                                         // B8: a 0/0 row is not a pass (--allow-empty is the deliberate exception)
}
Console.WriteLine(allOk ? "ALL OK" : "SOME FAILURES");
return allOk ? 0 : 1;

public static class TracePaths
{
    public static string DefaultDir()
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        while (d != null && !File.Exists(Path.Combine(d.FullName, "OpenSimAnt.sln"))) d = d.Parent;
        return Path.Combine(d?.FullName ?? ".", "build", "traces");
    }

    /// <summary>tools/re/build/flat.bin, the flat image built from the user's own SIMANT.EXE.</summary>
    public static string FlatImage() => Path.Combine(DefaultDir(), "..", "..", "..", "tools", "re", "build", "flat.bin");
}
