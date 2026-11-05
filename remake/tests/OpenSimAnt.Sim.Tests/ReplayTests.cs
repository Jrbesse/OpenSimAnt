using OpenSimAnt.Replay;
using Xunit;

namespace OpenSimAnt.Sim.Tests;

/// <summary>Replays every trace recorded from the Python reference (tools/ref/record_all.sh) on the C# port.
/// The traces are derived from the original game's memory, so they live in remake/build/traces (git-ignored);
/// without them (as on CI) the one row is NoTraces, which passes: xUnit fails a theory that has no data.
/// A trace that records no calls fails its row (B8): the row would otherwise be a pass with no input at all.</summary>
public class ReplayTests
{
    const string NoTraces = "(no traces)";

    public static IEnumerable<object[]> Traces()
    {
        var dir = TracePaths.DefaultDir();
        var files = Directory.Exists(dir) ? Directory.GetFiles(dir, "*.trace").OrderBy(x => x).ToArray() : Array.Empty<string>();
        if (files.Length == 0) yield return new object[] { NoTraces };
        foreach (var f in files)
            yield return new object[] { Path.GetFileName(f) };
    }

    [Theory]
    [MemberData(nameof(Traces))]
    public void TraceMatches(string name)
    {
        if (name == NoTraces) return;
        var rep = new Replayer();
        foreach (var rec in TraceReader.Read(Path.Combine(TracePaths.DefaultDir(), name))) rep.Run(rec);
        int calls = rep.Stats.Values.Sum(s => s.Calls);
        Assert.True(calls > 0, $"{name}: the trace records no calls, so this row proves nothing "        // B8: an empty trace is a failure, not a pass
                               + "(record a real trace with tools/ref/record_all.sh or delete the file)");
        var bad = rep.Stats.Where(kv => kv.Value.Ok != kv.Value.Calls)
            .Select(kv => $"{kv.Key}: {kv.Value.Ok}/{kv.Value.Calls}\n  " + string.Join("\n  ", kv.Value.Notes)).ToList();
        Assert.True(bad.Count == 0, string.Join("\n", bad));
    }
}
