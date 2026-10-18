using Formica.Replay;

// Formica.Replay [trace files or directories...] [--func substring] [--notes n] [--quiet]
// Replays the Python reference's recorded calls on the C# port (default: remake/build/traces).
var paths = new List<string>();
string filter = null;
int notes = 4;
bool quiet = false;
for (int i = 0; i < args.Length; i++)
{
    if (args[i] == "--func") filter = args[++i];
    else if (args[i] == "--notes") notes = int.Parse(args[++i]);
    else if (args[i] == "--quiet") quiet = true;
    else paths.Add(args[i]);
}
if (paths.Count == 0) paths.Add(TracePaths.DefaultDir());
Formica.Sim.GameData.Flat = File.ReadAllBytes(TracePaths.FlatImage());
var files = paths.SelectMany(p => Directory.Exists(p) ? (IEnumerable<string>)Directory.GetFiles(p, "*.trace").OrderBy(x => x) : new[] { p }).ToList();
bool allOk = true;
foreach (var file in files)
{
    var rep = new Replayer { MaxNotes = notes };
    foreach (var rec in TraceReader.Read(file))
    {
        if (filter != null && !rec.Func.Contains(filter)) continue;
        rep.Run(rec);
    }
    int calls = rep.Stats.Values.Sum(s => s.Calls), ok = rep.Stats.Values.Sum(s => s.Ok);
    Console.WriteLine($"{Path.GetFileName(file)}: {ok}/{calls} OK");
    foreach (var (f, s) in rep.Stats.OrderBy(k => k.Key))
    {
        if (s.Ok == s.Calls && quiet) continue;
        string status = s.Missing > 0 ? "NOT PORTED" : s.Ok == s.Calls ? "ok" : "MISMATCH";
        Console.WriteLine($"  {f}: {s.Ok}/{s.Calls} {status}");
        foreach (var n in s.Notes) Console.WriteLine("    " + n);
        if (s.Ok != s.Calls) allOk = false;
    }
}
Console.WriteLine(allOk ? "ALL OK" : "SOME FAILURES");
return allOk ? 0 : 1;

static class TracePaths
{
    public static string DefaultDir()
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        while (d != null && !File.Exists(Path.Combine(d.FullName, "Formica.sln"))) d = d.Parent;
        return Path.Combine(d?.FullName ?? ".", "build", "traces");
    }

    /// <summary>tools/re/build/flat.bin, the flat image built from the user's own SIMANT.EXE.</summary>
    public static string FlatImage() => Path.Combine(DefaultDir(), "..", "..", "..", "tools", "re", "build", "flat.bin");
}
