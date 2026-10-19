// A C# port of the YM3812 (OPL2) parts of ymfm, https://github.com/aaronsgiles/ymfm:
// ymfm_fm.ipp (operators, envelopes, the 2-operator channel), ymfm_opl.cpp (the OPL registers, LFO, key
// scaling, phase steps) and ymfm.h (the DAC round trip). Left out because the original's sound driver never
// uses them: rhythm mode, the timers and CSM.
//
// BSD 3-Clause License
//
// Copyright (c) 2021, Aaron Giles
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// 1. Redistributions of source code must retain the above copyright notice, this
//    list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
//
// 3. Neither the name of the copyright holder nor the names of its
//    contributors may be used to endorse or promote products derived from
//    this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

namespace Formica.Data;

/// <summary>A YM3812 (OPL2): register writes in, 16-bit mono samples out at <see cref="SampleRate"/>.</summary>
public sealed class Opl2
{
    /// <summary>The AdLib's 3.579545 MHz clock / 72.</summary>
    public const double SampleRate = 3579545.0 / 72;

    const int EgDepress = 0, EgAttack = 1, EgDecay = 2, EgSustain = 3, EgRelease = 4;
    const int EgQuiet = 0x380;

    static readonly ushort[] SinTable =
    {
        0x859,0x6c3,0x607,0x58b,0x52e,0x4e4,0x4a6,0x471,0x443,0x41a,0x3f5,0x3d3,0x3b5,0x398,0x37e,0x365,
        0x34e,0x339,0x324,0x311,0x2ff,0x2ed,0x2dc,0x2cd,0x2bd,0x2af,0x2a0,0x293,0x286,0x279,0x26d,0x261,
        0x256,0x24b,0x240,0x236,0x22c,0x222,0x218,0x20f,0x206,0x1fd,0x1f5,0x1ec,0x1e4,0x1dc,0x1d4,0x1cd,
        0x1c5,0x1be,0x1b7,0x1b0,0x1a9,0x1a2,0x19b,0x195,0x18f,0x188,0x182,0x17c,0x177,0x171,0x16b,0x166,
        0x160,0x15b,0x155,0x150,0x14b,0x146,0x141,0x13c,0x137,0x133,0x12e,0x129,0x125,0x121,0x11c,0x118,
        0x114,0x10f,0x10b,0x107,0x103,0x0ff,0x0fb,0x0f8,0x0f4,0x0f0,0x0ec,0x0e9,0x0e5,0x0e2,0x0de,0x0db,
        0x0d7,0x0d4,0x0d1,0x0cd,0x0ca,0x0c7,0x0c4,0x0c1,0x0be,0x0bb,0x0b8,0x0b5,0x0b2,0x0af,0x0ac,0x0a9,
        0x0a7,0x0a4,0x0a1,0x09f,0x09c,0x099,0x097,0x094,0x092,0x08f,0x08d,0x08a,0x088,0x086,0x083,0x081,
        0x07f,0x07d,0x07a,0x078,0x076,0x074,0x072,0x070,0x06e,0x06c,0x06a,0x068,0x066,0x064,0x062,0x060,
        0x05e,0x05c,0x05b,0x059,0x057,0x055,0x053,0x052,0x050,0x04e,0x04d,0x04b,0x04a,0x048,0x046,0x045,
        0x043,0x042,0x040,0x03f,0x03e,0x03c,0x03b,0x039,0x038,0x037,0x035,0x034,0x033,0x031,0x030,0x02f,
        0x02e,0x02d,0x02b,0x02a,0x029,0x028,0x027,0x026,0x025,0x024,0x023,0x022,0x021,0x020,0x01f,0x01e,
        0x01d,0x01c,0x01b,0x01a,0x019,0x018,0x017,0x017,0x016,0x015,0x014,0x014,0x013,0x012,0x011,0x011,
        0x010,0x00f,0x00f,0x00e,0x00d,0x00d,0x00c,0x00c,0x00b,0x00a,0x00a,0x009,0x009,0x008,0x008,0x007,
        0x007,0x007,0x006,0x006,0x005,0x005,0x005,0x004,0x004,0x004,0x003,0x003,0x003,0x002,0x002,0x002,
        0x002,0x001,0x001,0x001,0x001,0x001,0x001,0x001,0x000,0x000,0x000,0x000,0x000,0x000,0x000,0x000,
    };

    static readonly ushort[] PowerMantissa =
    {
        0x3fa,0x3f5,0x3ef,0x3ea,0x3e4,0x3df,0x3da,0x3d4,0x3cf,0x3c9,0x3c4,0x3bf,0x3b9,0x3b4,0x3ae,0x3a9,
        0x3a4,0x39f,0x399,0x394,0x38f,0x38a,0x384,0x37f,0x37a,0x375,0x370,0x36a,0x365,0x360,0x35b,0x356,
        0x351,0x34c,0x347,0x342,0x33d,0x338,0x333,0x32e,0x329,0x324,0x31f,0x31a,0x315,0x310,0x30b,0x306,
        0x302,0x2fd,0x2f8,0x2f3,0x2ee,0x2e9,0x2e5,0x2e0,0x2db,0x2d6,0x2d2,0x2cd,0x2c8,0x2c4,0x2bf,0x2ba,
        0x2b5,0x2b1,0x2ac,0x2a8,0x2a3,0x29e,0x29a,0x295,0x291,0x28c,0x288,0x283,0x27f,0x27a,0x276,0x271,
        0x26d,0x268,0x264,0x25f,0x25b,0x257,0x252,0x24e,0x249,0x245,0x241,0x23c,0x238,0x234,0x230,0x22b,
        0x227,0x223,0x21e,0x21a,0x216,0x212,0x20e,0x209,0x205,0x201,0x1fd,0x1f9,0x1f5,0x1f0,0x1ec,0x1e8,
        0x1e4,0x1e0,0x1dc,0x1d8,0x1d4,0x1d0,0x1cc,0x1c8,0x1c4,0x1c0,0x1bc,0x1b8,0x1b4,0x1b0,0x1ac,0x1a8,
        0x1a4,0x1a0,0x19c,0x199,0x195,0x191,0x18d,0x189,0x185,0x181,0x17e,0x17a,0x176,0x172,0x16f,0x16b,
        0x167,0x163,0x160,0x15c,0x158,0x154,0x151,0x14d,0x149,0x146,0x142,0x13e,0x13b,0x137,0x134,0x130,
        0x12c,0x129,0x125,0x122,0x11e,0x11b,0x117,0x114,0x110,0x10c,0x109,0x106,0x102,0x0ff,0x0fb,0x0f8,
        0x0f4,0x0f1,0x0ed,0x0ea,0x0e7,0x0e3,0x0e0,0x0dc,0x0d9,0x0d6,0x0d2,0x0cf,0x0cc,0x0c8,0x0c5,0x0c2,
        0x0be,0x0bb,0x0b8,0x0b5,0x0b1,0x0ae,0x0ab,0x0a8,0x0a4,0x0a1,0x09e,0x09b,0x098,0x094,0x091,0x08e,
        0x08b,0x088,0x085,0x082,0x07e,0x07b,0x078,0x075,0x072,0x06f,0x06c,0x069,0x066,0x063,0x060,0x05d,
        0x05a,0x057,0x054,0x051,0x04e,0x04b,0x048,0x045,0x042,0x03f,0x03c,0x039,0x036,0x033,0x030,0x02d,
        0x02a,0x028,0x025,0x022,0x01f,0x01c,0x019,0x016,0x014,0x011,0x00e,0x00b,0x008,0x006,0x003,0x000,
    };

    static readonly uint[] IncrementTable =
    {
        0x00000000, 0x00000000, 0x10101010, 0x10101010, 0x10101010, 0x10101010, 0x11101110, 0x11101110,
        0x10101010, 0x10111010, 0x11101110, 0x11111110, 0x10101010, 0x10111010, 0x11101110, 0x11111110,
        0x10101010, 0x10111010, 0x11101110, 0x11111110, 0x10101010, 0x10111010, 0x11101110, 0x11111110,
        0x10101010, 0x10111010, 0x11101110, 0x11111110, 0x10101010, 0x10111010, 0x11101110, 0x11111110,
        0x10101010, 0x10111010, 0x11101110, 0x11111110, 0x10101010, 0x10111010, 0x11101110, 0x11111110,
        0x10101010, 0x10111010, 0x11101110, 0x11111110, 0x10101010, 0x10111010, 0x11101110, 0x11111110,
        0x11111111, 0x21112111, 0x21212121, 0x22212221, 0x22222222, 0x42224222, 0x42424242, 0x44424442,
        0x44444444, 0x84448444, 0x84848484, 0x88848884, 0x88888888, 0x88888888, 0x88888888, 0x88888888,
    };

    static readonly byte[] FnumToAtten = { 0, 24, 32, 37, 40, 43, 45, 47, 48, 50, 51, 52, 53, 54, 55, 56 };
    static readonly sbyte[] PmScale = { 8, 4, 0, -4, -8, -4, 0, 4 };
    static readonly ushort[][] Waveforms = BuildWaveforms();

    static ushort[][] BuildWaveforms()
    {
        var w = new ushort[4][];
        for (int i = 0; i < 4; i++) w[i] = new ushort[0x400];
        for (int i = 0; i < 0x400; i++)
            w[0][i] = (ushort)(AbsSinAttenuation(i) | (Bit(i, 9) << 15));
        ushort zero = w[0][0];
        for (int i = 0; i < 0x400; i++)
        {
            w[1][i] = Bit(i, 9) != 0 ? zero : w[0][i];
            w[2][i] = (ushort)(w[0][i] & 0x7fff);
            w[3][i] = Bit(i, 8) != 0 ? zero : (ushort)(w[0][i] & 0x7fff);
        }
        return w;
    }

    static int Bit(int v, int start, int len = 1) => (v >> start) & ((1 << len) - 1);

    static int AbsSinAttenuation(int input)
    {
        if (Bit(input, 8) != 0) input = ~input;
        return SinTable[input & 0xff];
    }

    static int AttenuationToVolume(int input) => (((PowerMantissa[input & 0xff] | 0x400) << 2)) >> (input >> 8);

    static int AttenuationIncrement(int rate, int index) => (int)((IncrementTable[rate] >> (4 * index)) & 0xf);

    static int EffectiveRate(int raw, int ksr) => raw == 0 ? 0 : Math.Min(raw + ksr, 63);

    /// <summary>ymfm's roundtrip_fp: the YM3014 DAC's 10.3 floating point.</summary>
    static short RoundTripFp(int value)
    {
        if (value < -32768) return -32768;
        if (value > 32767) return 32767;
        int scan = value ^ (value >> 31);
        int exponent = 7 - System.Numerics.BitOperations.LeadingZeroCount((uint)(scan << 17));
        exponent = Math.Max(exponent, 1) - 1;
        return (short)(value & ~((1 << exponent) - 1));
    }

    sealed class Operator
    {
        public int Offset;
        public uint Phase;
        public int EnvAttenuation = 0x3ff, EnvState = EgRelease, KeyState, KeyOnLive;
        // the cache (cache_operator_data)
        public ushort[] Waveform = Waveforms[0];
        public int BlockFreq, Multiple, PhaseStep, TotalLevel, EgSustain;
        public bool PhaseDynamic;
        public readonly int[] EgRate = new int[5];

        public int PhaseIndex => (int)(Phase >> 10);
    }

    sealed class Channel
    {
        public int Offset;
        public Operator Mod, Car;
        public readonly int[] Feedback = new int[2];
        public int FeedbackIn;
    }

    readonly byte[] regs = new byte[0x100];
    readonly Operator[] ops = new Operator[18];
    readonly Channel[] chans = new Channel[9];
    int envCounter, lfoAmCounter, lfoPmCounter, lfoAm;
    bool modified = true;

    public Opl2()
    {
        for (int i = 0; i < 18; i++) ops[i] = new Operator { Offset = i + 2 * (i / 6) };
        int[][] map = { new[] { 0, 3 }, new[] { 1, 4 }, new[] { 2, 5 }, new[] { 6, 9 }, new[] { 7, 10 }, new[] { 8, 11 }, new[] { 12, 15 }, new[] { 13, 16 }, new[] { 14, 17 } };
        for (int c = 0; c < 9; c++) chans[c] = new Channel { Offset = c, Mod = ops[map[c][0]], Car = ops[map[c][1]] };
    }

    int Reg(int r, int start, int len, int extra = 0) => Bit(regs[(r + extra) & 0xff], start, len);
    int WaveformEnable => Reg(0x01, 5, 1);
    int NoteSelect => Reg(0x08, 6, 1);
    int LfoAmDepth => Reg(0xbd, 7, 1);
    int LfoPmDepth => Reg(0xbd, 6, 1);

    public void Write(int reg, int data)
    {
        reg &= 0xff;
        if (reg == 0x04) { regs[reg] = (byte)((data & 0x80) != 0 ? regs[reg] | 0x80 : data); return; }   // the mode register: timers only
        regs[reg] = (byte)data;
        modified = true;
        if ((reg & 0xf0) == 0xb0 && (reg & 0x0f) < 9)
        {
            var ch = chans[reg & 0x0f];
            int on = Bit(data, 5);
            ch.Mod.KeyOnLive = on;
            ch.Car.KeyOnLive = on;
        }
    }

    /// <summary>One sample (ym3812::generate): clock everything, then sum the channels through the DAC.</summary>
    public short Next()
    {
        if (modified)
        {
            foreach (var ch in chans)
            {
                Prepare(ch, ch.Mod);
                Prepare(ch, ch.Car);
            }
            modified = false;
        }
        envCounter += 4;
        int pm = ClockLfo();
        foreach (var ch in chans)
        {
            ch.Feedback[0] = ch.Feedback[1];
            ch.Feedback[1] = ch.FeedbackIn;
            ClockOperator(ch.Mod, pm);
            ClockOperator(ch.Car, pm);
        }
        int sum = 0;
        foreach (var ch in chans) sum += Output(ch, 1, 32767);
        return RoundTripFp(sum);
    }

    public void Generate(Span<short> buffer)
    {
        for (int i = 0; i < buffer.Length; i++) buffer[i] = Next();
    }

    int ClockLfo()
    {
        int am = lfoAmCounter++;
        if (am >= 210 * 64 - 1) lfoAmCounter = 0;
        int shift = 9 - 2 * LfoAmDepth;
        lfoAm = ((am < 105 * 64) ? am : (210 * 64 + 63 - am)) >> shift;
        int pmc = lfoPmCounter;
        lfoPmCounter = (lfoPmCounter + 1) & 0xffff;
        return PmScale[Bit(pmc, 10, 3)] >> (LfoPmDepth ^ 1);
    }

    void Prepare(Channel ch, Operator op)
    {
        Cache(ch, op);
        int keystate = op.KeyOnLive != 0 ? 1 : 0;
        if ((keystate ^ op.KeyState) != 0)
        {
            op.KeyState = keystate;
            if (keystate != 0) StartAttack(op);
            else if (op.EnvState < EgRelease) op.EnvState = EgRelease;
        }
    }

    static void StartAttack(Operator op)
    {
        if (op.EnvState == EgAttack) return;
        op.EnvState = EgAttack;
        op.Phase = 0;
        if (op.EgRate[EgAttack] >= 62) op.EnvAttenuation = 0;
    }

    void Cache(Channel ch, Operator op)
    {
        int o = op.Offset;
        op.Waveform = Waveforms[WaveformEnable != 0 ? Reg(0xe0, 0, 2, o) : 0];
        int blockFreq = op.BlockFreq = Reg(0xb0, 0, 5, ch.Offset) << 8 | Reg(0xa0, 0, 8, ch.Offset);
        int keycode = Bit(blockFreq, 10, 3) << 1 | Bit(blockFreq, 9 - NoteSelect, 1);
        int multiple = Reg(0x20, 0, 4, o);
        op.Multiple = ((multiple & 0xe) | Bit(0xc2aa, multiple)) * 2;
        if (op.Multiple == 0) op.Multiple = 1;
        op.PhaseDynamic = Reg(0x20, 6, 1, o) != 0;
        if (!op.PhaseDynamic) op.PhaseStep = PhaseStep(blockFreq, op.Multiple, 0);
        op.TotalLevel = Reg(0x40, 0, 6, o) << 3;
        int kslRaw = Reg(0x40, 6, 2, o), ksl = Bit(kslRaw, 1) | Bit(kslRaw, 0) << 1;
        if (ksl != 0) op.TotalLevel += Math.Max(0, FnumToAtten[Bit(blockFreq, 6, 4)] - 8 * (Bit(blockFreq, 10, 3) ^ 7)) << ksl;
        int sl = Reg(0x80, 4, 4, o);
        op.EgSustain = (sl | ((sl + 1) & 0x10)) << 5;
        int ksrval = keycode >> (2 * (Reg(0x20, 4, 1, o) ^ 1));
        op.EgRate[EgAttack] = EffectiveRate(Reg(0x60, 4, 4, o) * 4, ksrval);
        op.EgRate[EgDecay] = EffectiveRate(Reg(0x60, 0, 4, o) * 4, ksrval);
        op.EgRate[EgSustain] = Reg(0x20, 5, 1, o) != 0 ? 0 : EffectiveRate(Reg(0x80, 0, 4, o) * 4, ksrval);
        op.EgRate[EgRelease] = EffectiveRate(Reg(0x80, 0, 4, o) * 4, ksrval);
        op.EgRate[EgDepress] = 0x3f;
    }

    static int PhaseStep(int blockFreq, int multiple, int pm)
    {
        int fnum = Bit(blockFreq, 0, 10) << 2;
        fnum += (pm * Bit(blockFreq, 7, 3)) >> 1;
        fnum &= 0xfff;
        int step = (fnum << Bit(blockFreq, 10, 3)) >> 2;
        return (step * multiple) >> 1;
    }

    void ClockOperator(Operator op, int pm)
    {
        if ((envCounter & 3) == 0) ClockEnvelope(op, envCounter >> 2);
        op.Phase += (uint)(op.PhaseDynamic ? PhaseStep(op.BlockFreq, op.Multiple, pm) : op.PhaseStep);
    }

    static void ClockEnvelope(Operator op, int counter)
    {
        if (op.EnvState == EgAttack && op.EnvAttenuation == 0) op.EnvState = EgDecay;
        if (op.EnvState == EgDecay && op.EnvAttenuation >= op.EgSustain) op.EnvState = EgSustain;
        int rate = op.EgRate[op.EnvState];
        int rateShift = rate >> 2;
        counter <<= rateShift;
        if (Bit(counter, 0, 11) != 0) return;
        int relevant = Bit(counter, rateShift <= 11 ? 11 : rateShift, 3);
        int inc = AttenuationIncrement(rate, relevant);
        if (op.EnvState == EgAttack)
        {
            if (rate < 62) op.EnvAttenuation = (op.EnvAttenuation + ((~op.EnvAttenuation * inc) >> 4)) & 0xffff;
        }
        else
        {
            op.EnvAttenuation += inc;
            if (op.EnvAttenuation >= 0x400) op.EnvAttenuation = 0x3ff;
        }
    }

    int EnvelopeAttenuation(Operator op)
    {
        int r = op.EnvAttenuation;
        if (Reg(0x20, 7, 1, op.Offset) != 0) r += lfoAm;
        r += op.TotalLevel;
        return Math.Min(r, 0x3ff);
    }

    int Volume(Operator op, int phase)
    {
        if (op.EnvAttenuation > EgQuiet) return 0;
        int sin = op.Waveform[phase & 0x3ff];
        int result = AttenuationToVolume((sin & 0x7fff) + (EnvelopeAttenuation(op) << 2));
        return Bit(sin, 15) != 0 ? -result : result;
    }

    /// <summary>output_2op with the OPL2's modulator delay (the previous sample modulates).</summary>
    int Output(Channel ch, int rshift, int clipmax)
    {
        int opmod = 0;
        int fb = Reg(0xc0, 1, 3, ch.Offset);
        if (fb != 0) opmod = (ch.Feedback[0] + ch.Feedback[1]) >> (10 - fb);
        ch.FeedbackIn = Volume(ch.Mod, ch.Mod.PhaseIndex + opmod);
        if (Reg(0xc0, 0, 1, ch.Offset) == 0)
            return Volume(ch.Car, ch.Car.PhaseIndex + (ch.Feedback[1] >> 1)) >> rshift;
        int result = (ch.Feedback[1] >> rshift) + (Volume(ch.Car, ch.Car.PhaseIndex) >> rshift);
        return Math.Clamp(result, -clipmax - 1, clipmax);
    }
}
