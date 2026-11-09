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

    [Fact]
    public void ARealTraceStillExitsZero()
    {
        var dir = TracePaths.DefaultDir();
        var trace = Directory.Exists(dir)
            ? Directory.GetFiles(dir, "*.trace").OrderBy(f => new FileInfo(f).Length).FirstOrDefault()
            : null;
        if (trace == null) return;                                          // no traces (CI); the real 26 run on the Hermes box
        var (code, output) = Run("--quiet", trace);
        Assert.Equal(0, code);
        Assert.Contains("ALL OK", output);
    }
}
