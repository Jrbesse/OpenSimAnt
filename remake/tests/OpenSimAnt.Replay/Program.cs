using OpenSimAnt.Replay;

// OpenSimAnt.Replay [trace files or directories...] [--func substring] [--notes n] [--quiet] [--allow-empty]
// Replays the Python reference's recorded calls on the C# port (default: remake/build/traces).
// The default run lives in Runner.cs so a test can assert its exit code.
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
return OpenSimAnt.Replay.ReplayRunner.Run(args);

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
