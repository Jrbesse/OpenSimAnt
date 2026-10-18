namespace Formica.Sim;

/// <summary>
/// Simulation state, laid out exactly like the original's memory so the port can be checked byte for byte
/// against the Python reference (tools/ref/simant_ref/state.py), which is checked against the original.
/// The buffer covers flat linear 0x3d570..0x62000 of the original program image (segments T, SIM, G, DS).
/// Initial contents come from the player's own SIMANT.EXE.
/// </summary>
public sealed class State
{
    public const int Lo = 0x3d570, Hi = 0x62000, Size = Hi - Lo;

    public readonly byte[] Mem;

    /// <summary>The game's real-time clock (f_1bc34: a 32-bit counter, ~18.2 ticks/s). The engine sets it; the
    /// simulation only reads it.</summary>
    public long Clock;

    /// <summary>BIOS keyboard shift flags (0000:0417): holding Shift and Alt lets the yellow ant keep its load.</summary>
    public int BiosKbd;

    /// <summary>Player and UI hooks.</summary>
    public IPlayer Hooks = new NoPlayer();

    public State(byte[] mem)
    {
        if (mem.Length != Size) throw new ArgumentException($"state memory must be {Size} bytes");
        Mem = mem;
    }

    public State Clone()
    {
        var s = new State((byte[])Mem.Clone()) { Clock = Clock, BiosKbd = BiosKbd, Hooks = Hooks };
        return s;
    }

    /// <summary>f_1bc34.</summary>
    public long ReadClock() => Clock & 0xffffffffL;

    /// <summary>f_0123e: the clock x3 (about 1/60 s units, like Mac ticks).</summary>
    public long Clock3() => (ReadClock() * 3) & 0xffffffffL;

    // ---- raw access by (segment, offset)
    static int A(int seg, int off) => seg * 16 + (off & 0xffff) - Lo;

    public int U8(int seg, int off) => Mem[A(seg, off)];

    public int S8(int seg, int off)
    {
        int v = Mem[A(seg, off)];
        return v > 127 ? v - 256 : v;
    }

    public void Set8(int seg, int off, int v) => Mem[A(seg, off)] = (byte)v;

    public int U16(int seg, int off)
    {
        int a = A(seg, off);
        return Mem[a] | (Mem[a + 1] << 8);
    }

    public int S16(int seg, int off)
    {
        int v = U16(seg, off);
        return (v & 0x8000) != 0 ? v - 0x10000 : v;
    }

    public void Set16(int seg, int off, int v)
    {
        int a = A(seg, off);
        Mem[a] = (byte)v;
        Mem[a + 1] = (byte)(v >> 8);
    }

    public void Set16(int seg, int off, long v) => Set16(seg, off, (int)(v & 0xffff));

    public long U32(int seg, int off) => (uint)(U16(seg, off) | (U16(seg, off + 2) << 16));

    public void Set32(int seg, int off, long v)
    {
        Set16(seg, off, (int)(v & 0xffff));
        Set16(seg, off + 2, (int)((v >> 16) & 0xffff));
    }

    public void Inc16(int seg, int off, int d = 1) => Set16(seg, off, U16(seg, off) + d);

    public void Inc32(int seg, int off, long d = 1) => Set32(seg, off, (U32(seg, off) + d) & 0xffffffffL);

    // ---- the game RNG (LFSR at DS:8ba2), stored in memory like the original
    public int LfsrStep()
    {
        int x = U16(Seg.DS, 0x8ba2) << 1;
        if ((x & 0x10000) != 0) x ^= 0x1bf5;
        x &= 0xffff;
        Set16(Seg.DS, 0x8ba2, x);
        return x;
    }

    /// <summary>0093:013d Rand(n) = x % n.</summary>
    public int Rand(int n) => LfsrStep() % n;

    public int Rand2() => LfsrStep() & 1;
    public int Rand4() => LfsrStep() & 3;
    public int Rand8() => LfsrStep() & 7;
    public int Rand16() => LfsrStep() & 15;
    public int Rand32() => LfsrStep() & 31;
    public int Rand64() => LfsrStep() & 63;
    public int Rand128() => LfsrStep() & 127;
    public int Rand256() => LfsrStep() & 255;

    /// <summary>MSC runtime rand() (state DS:7bbe, 32-bit): s = s*0x343fd + 0x269ec3; (s >> 16) &amp; 0x7fff.</summary>
    public int CrtRand()
    {
        uint s = (uint)U32(Seg.DS, 0x7bbe) * 0x343fdu + 0x269ec3u;
        Set32(Seg.DS, 0x7bbe, s);
        return (int)((s >> 16) & 0x7fff);
    }

    /// <summary>0093:0118 abs(rand()) % n.</summary>
    public int CrtRandMod(int n) => CrtRand() % n;

    /// <summary>0093:002b min(Rand(n), Rand(n)).</summary>
    public int RandLow(int n)
    {
        int a = Rand(n);
        int b = Rand(n);
        return b < a ? b : a;
    }

    // ---- common sim-segment grids (index a*64 + b)
    public int Grid(int @base, int a, int b) => U8(Seg.SIM, @base + a * 64 + b);

    public void SetGrid(int @base, int a, int b, int v) => Set8(Seg.SIM, @base + a * 64 + b, v);

    /// <summary>Pheromone map cell (half resolution, index ca*32 + cb).</summary>
    public int Pher(int @base, int ca, int cb) => U8(Seg.SIM, @base + ca * 32 + cb);

    public void SetPher(int @base, int ca, int cb, int v) => Set8(Seg.SIM, @base + ca * 32 + cb, v);
}
