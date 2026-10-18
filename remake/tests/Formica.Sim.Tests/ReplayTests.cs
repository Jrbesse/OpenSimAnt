using Formica.Replay;
using Xunit;

namespace Formica.Sim.Tests;

/// <summary>Replays every trace recorded from the Python reference (tools/ref/record_all.sh) on the C# port.
/// The traces are derived from the original game's memory, so they live in remake/build/traces (git-ignored);
/// without them the tests have nothing to check and pass vacuously.</summary>
public class ReplayTests
{
    public static IEnumerable<object[]> Traces()
    {
        var dir = TracePaths.DefaultDir();
        if (!Directory.Exists(dir)) yield break;
        foreach (var f in Directory.GetFiles(dir, "*.trace").OrderBy(x => x))
            yield return new object[] { Path.GetFileName(f) };
    }

    [Theory]
    [MemberData(nameof(Traces))]
    public void TraceMatches(string name)
    {
        var flat = TracePaths.FlatImage();
        if (File.Exists(flat)) GameData.Flat = File.ReadAllBytes(flat);
        var rep = new Replayer();
        foreach (var rec in TraceReader.Read(Path.Combine(TracePaths.DefaultDir(), name))) rep.Run(rec);
        var bad = rep.Stats.Where(kv => kv.Value.Ok != kv.Value.Calls)
            .Select(kv => $"{kv.Key}: {kv.Value.Ok}/{kv.Value.Calls}\n  " + string.Join("\n  ", kv.Value.Notes)).ToList();
        Assert.True(bad.Count == 0, string.Join("\n", bad));
    }
}
