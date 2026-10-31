using OpenSimAnt.Data;
using Xunit;

namespace OpenSimAnt.Sim.Tests;

/// <summary>Sanity checks of the OPL2 port: pitch from F-number and block, the envelope's attack and release.</summary>
public class Opl2Tests
{
    static Opl2 Sine(int fnum, int block)
    {
        var opl = new Opl2();
        opl.Write(0x20, 0x21); opl.Write(0x23, 0x21);   // sustained, multiple 1
        opl.Write(0x40, 0x3f); opl.Write(0x43, 0x00);   // modulator silent, carrier full
        opl.Write(0x60, 0xf0); opl.Write(0x63, 0xf0);   // fastest attack
        opl.Write(0x80, 0x0f); opl.Write(0x83, 0x0f);   // sustain level 0, fastest release
        opl.Write(0xc0, 0x00);
        opl.Write(0xa0, fnum & 0xff);
        opl.Write(0xb0, 0x20 | block << 2 | fnum >> 8);
        return opl;
    }

    [Theory]
    [InlineData(0x157, 4)]
    [InlineData(0x287, 5)]
    [InlineData(0x1ca, 2)]
    public void PitchMatchesFnumAndBlock(int fnum, int block)
    {
        var opl = Sine(fnum, block);
        var buf = new short[(int)Opl2.SampleRate];
        opl.Generate(buf);
        int crossings = 0;
        for (int i = 1; i < buf.Length; i++)
            if (buf[i - 1] < 0 && buf[i] >= 0) crossings++;
        double want = fnum * Opl2.SampleRate / (1 << (20 - block));
        Assert.InRange(crossings, want - 2, want + 2);
        Assert.True(buf.Max() > 3000, $"peak {buf.Max()}");
    }

    [Fact]
    public void KeyOffReleases()
    {
        var opl = Sine(0x157, 4);
        var buf = new short[4000];
        opl.Generate(buf);
        opl.Write(0xb0, 0x11);                          // key off
        opl.Generate(buf);
        opl.Generate(buf);
        Assert.True(buf.Max() < 50, $"still {buf.Max()} after the release");
    }
}
