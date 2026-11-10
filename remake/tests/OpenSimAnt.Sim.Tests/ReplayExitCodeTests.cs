using System;
using System.IO;
using System.Linq;
using OpenSimAnt.Replay;
using Xunit;

namespace OpenSimAnt.Sim.Tests;

/// <summary>The replay's exit code is the pipeline's oracle (issue #37), so these assert the int Program.cs hands to
/// the OS -- an empty trace set must not exit 0 and print "ALL OK", or a fresh clone is a green gate over nothing.
/// The traces directory exists in the sessions' clone and not on CI; the non-empty direction skips when it is absent.</summary>
public class ReplayExitCodeTests
{
    static string NewTempDir()
    {
        var dir = Path.Combine(Path.GetTempPath(), "opensimant-replay-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    static (int Code, string Output) Run(params string[] args)
    {
        var output = new StringWriter();
        int code = ReplayRunner.Run(args, output);
        return (code, output.ToString());
    }

    [Fact]
    public void EmptyTraceDirectoryExitsNonZeroAndNamesTheDirectory()
    {
        var dir = NewTempDir();
        try
        {
            var (code, output) = Run("--quiet", dir);
            Assert.NotEqual(0, code);
            Assert.Contains(dir, output);
        }
        finally { Directory.Delete(dir, true); }
    }

    [Fact]
    public void ExplicitTracePathThatMatchesNothingExitsNonZero()
    {
        var dir = NewTempDir();
        try
        {
            var missing = Path.Combine(dir, "not-recorded.trace");
            var (code, output) = Run("--quiet", missing);
            Assert.NotEqual(0, code);
            Assert.Contains(missing, output);
        }
        finally { Directory.Delete(dir, true); }
    }

    [Fact]
    public void AllowEmptyIsTheDeliberateException()
    {
        var dir = NewTempDir();
        try
        {
            Assert.Equal(0, Run("--quiet", "--allow-empty", dir).Code);
        }
        finally { Directory.Delete(dir, true); }
    }

    /// <summary>Writes a minimal valid trace (b"SATR1", then a json header + two zlib blocks per record) so the
    /// non-empty direction is asserted on CI too, not just on a box that happens to hold the recorded set.</summary>
    static string WriteSyntheticTrace(string dir)
    {
        var path = Path.Combine(dir, "synthetic.trace");
        var zero = new byte[OpenSimAnt.Sim.State.Size];                     // a zeroed image: every read is 0, no writes
        using var f = File.Create(path);
        using var w = new BinaryWriter(f);
        w.Write(System.Text.Encoding.ASCII.GetBytes("SATR1"));
        void Record(string func, string args, string ret)
        {
            var json = $"{{\"func\":\"{func}\",\"args\":{args},\"clock\":0,\"clock_after\":0,\"kbd\":0,\"kbd_after\":0,\"ret\":{ret}}}";
            var head = System.Text.Encoding.UTF8.GetBytes(json);
            w.Write(head.Length);
            w.Write(head);
            foreach (var _ in new[] { 0, 0 })                               // before ^ prev, then after ^ before (prev is zero, after == before)
            {
                var comp = Deflate(zero);
                w.Write(comp.Length);
                w.Write(comp);
            }
        }
        Record("movement.dx", "[0]", "0");                                  // pure reads of the zeroed image
        Record("movement.walk", "[0,0]", "0");
        w.Flush();
        return path;
    }

    static byte[] Deflate(byte[] data)
    {
        using var ms = new MemoryStream();
        using (var z = new System.IO.Compression.ZLibStream(ms, System.IO.Compression.CompressionLevel.Optimal, true))
            z.Write(data, 0, data.Length);
        return ms.ToArray();
    }

    [Fact]
    public void MixedCaseBlamesThePathNotTheWholeSet()
    {
        var dir = NewTempDir();
        try
        {
            var trace = WriteSyntheticTrace(dir);
            var missing = Path.Combine(dir, "not-recorded.trace");
            var (code, output) = Run("--quiet", trace, missing);
            Assert.NotEqual(0, code);                                       // the bad path is a mistake, as before
            Assert.Contains("one or more paths yielded no traces", output);
            Assert.DoesNotContain("the trace set is empty", output);         // false: 2 records did replay
            Assert.Contains("synthetic.trace: 2/2 OK", output);
        }
        finally { Directory.Delete(dir, true); }
    }

    [Fact]
    public void ARealTraceStillExitsZero()
    {
        var dir = NewTempDir();
        try
        {
            var trace = WriteSyntheticTrace(dir);
            var (code, output) = Run("--quiet", trace);
            Assert.Equal(0, code);
            Assert.Contains("synthetic.trace: 2/2 OK", output);
            Assert.Contains("ALL OK", output);
        }
        finally { Directory.Delete(dir, true); }
    }
}
