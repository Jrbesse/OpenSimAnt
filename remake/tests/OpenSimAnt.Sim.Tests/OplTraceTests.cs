using OpenSimAnt.Data;
using OpenSimAnt.Replay;
using Xunit;

namespace OpenSimAnt.Sim.Tests;

/// <summary>Replays the original sound driver's register streams (tools/re/opl_capture.py record: every song,
/// every effect, all effects in a row, a song with effects) on SoundDriver and compares every OPL2 write and
/// every sequencer wait. The traces come from the player's own game, so they live in remake/build/traces/opl
/// (git-ignored); without them, or without the game files, the one row passes.</summary>
public class OplTraceTests
{
    const string NoTraces = "(no traces)";

    static string Dir => Path.Combine(TracePaths.DefaultDir(), "opl");
    static string GameDir => Path.GetFullPath(Path.Combine(TracePaths.DefaultDir(), "..", "..", ".."));

    public static IEnumerable<object[]> Traces()
    {
        var files = Directory.Exists(Dir) && OriginalFiles.Present(GameDir)
            ? Directory.GetFiles(Dir, "*.trace").OrderBy(x => x).ToArray() : Array.Empty<string>();
        if (files.Length == 0) yield return new object[] { NoTraces };
        foreach (var f in files)
            yield return new object[] { Path.GetFileName(f) };
    }

    /// <summary>The capture never runs the mixer's interrupt, so a started sample never ends there.</summary>
    sealed class NeverEnding : SoundDriver.ISampleVoices
    {
        readonly bool[] on = new bool[2];
        public void Start(int voice, SoundBank.Sample sample, int step, int attenuation) => on[voice] = true;
        public void Stop(int voice) => on[voice] = false;
        public bool Playing(int voice) => on[voice];
    }

    static OriginalFiles files;

    public static IEnumerable<object[]> DacTraces()
    {
        var found = Directory.Exists(Dir) && OriginalFiles.Present(GameDir)
            ? Directory.GetFiles(Dir, "*.dac").OrderBy(x => x).ToArray() : Array.Empty<string>();
        if (found.Length == 0) yield return new object[] { NoTraces };
        foreach (var f in found)
            yield return new object[] { Path.GetFileName(f) };
    }

    /// <summary>The sample mixer: the original's 5575.6 Hz handler run tick by tick after some effects
    /// (E n), with the byte it wrote to the Sound Blaster's DAC each tick (K v, or K - for none).</summary>
    [Theory]
    [MemberData(nameof(DacTraces))]
    public void DacMatches(string name)
    {
        if (name == NoTraces) return;
        files ??= new OriginalFiles(GameDir);
        var mix = new SoundMixer(files);
        int line = 0;
        foreach (var l in File.ReadLines(Path.Combine(Dir, name)))
        {
            line++;
            if (l.StartsWith("E ")) mix.Driver.Effect(int.Parse(l[2..]));
            else
            {
                int got = mix.Tick();
                Assert.True(l == "K " + (got < 0 ? "-" : got.ToString()), $"{name} line {line}: want '{l}', got {got}");
            }
        }
    }

    [Theory]
    [MemberData(nameof(Traces))]
    public void TraceMatches(string name)
    {
        if (name == NoTraces) return;
        files ??= new OriginalFiles(GameDir);
        var writes = new List<string>();
        var driver = new SoundDriver(files, (r, v) => writes.Add($"W {r:x2} {v:x2}"), new NeverEnding());
        writes.Clear();                                         // the init ran at boot, before the trace
        var got = new List<string>();
        foreach (var line in File.ReadLines(Path.Combine(Dir, name)))
        {
            var p = line.Split(' ');
            switch (p[0])
            {
                case "S":
                    Flush(); got.Add(line); driver.StartSong(int.Parse(p[1])); break;
                case "E":
                    Flush(); got.Add(line); driver.Effect(int.Parse(p[1])); break;
                case "T":
                    Flush(); got.Add(line); int wait = driver.Step(); Flush(); got.Add($"R {wait}"); break;
            }
        }
        Flush();
        var want = File.ReadLines(Path.Combine(Dir, name)).ToList();
        int i = 0;
        while (i < want.Count && i < got.Count && want[i] == got[i]) i++;
        Assert.True(i == want.Count && i == got.Count,
            $"{name}: first difference at line {i + 1}: want '{(i < want.Count ? want[i] : "(end)")}', got '{(i < got.Count ? got[i] : "(end)")}'\n"
            + string.Join("\n", want.Skip(Math.Max(0, i - 6)).Take(8)));

        void Flush()
        {
            got.AddRange(writes);
            writes.Clear();
        }
    }
}
