namespace Formica.Sim;

/// <summary>Segments of the original's memory that the simulation state mirrors (see <see cref="State"/>).</summary>
public static class Seg
{
    /// <summary>Constant tables and some variables.</summary>
    public const int T = 0x3d57;
    /// <summary>Grids, ant arrays, pheromone maps (the red trail map runs past 64 KB into 0x4da7:0).</summary>
    public const int SIM = 0x3e1d;
    /// <summary>Far globals.</summary>
    public const int G = 0x50f6;
    /// <summary>DGROUP: strings, the LFSR at DS:8ba2, the C runtime's rand state.</summary>
    public const int DS = 0x55b3;
}

/// <summary>Integer helpers that reproduce the original's 16-bit C arithmetic and the reference port's Python
/// semantics (floor division and modulo) exactly.</summary>
public static class Bits
{
    public static int S16(int v)
    {
        v &= 0xffff;
        return (v & 0x8000) != 0 ? v - 0x10000 : v;
    }

    public static int S16(long v) => S16((int)(v & 0xffff));

    public static int S8(int v)
    {
        v &= 0xff;
        return v > 127 ? v - 256 : v;
    }

    public static long S32(long v)
    {
        v &= 0xffffffffL;
        return (v & 0x80000000L) != 0 ? v - 0x100000000L : v;
    }

    /// <summary>C division: truncates toward zero.</summary>
    public static int CDiv(int a, int b) => a / b;

    /// <summary>C remainder: has the sign of the dividend.</summary>
    public static int CMod(int a, int b) => a % b;

    /// <summary>Python's a // b (floors).</summary>
    public static int FloorDiv(int a, int b)
    {
        int q = a / b;
        if ((a % b != 0) && ((a < 0) != (b < 0))) q--;
        return q;
    }

    public static long FloorDiv(long a, long b)
    {
        long q = a / b;
        if ((a % b != 0) && ((a < 0) != (b < 0))) q--;
        return q;
    }

    /// <summary>Python's a % b (result has the sign of b).</summary>
    public static int Mod(int a, int b)
    {
        int r = a % b;
        if (r != 0 && ((r < 0) != (b < 0))) r += b;
        return r;
    }

    public static long Mod(long a, long b)
    {
        long r = a % b;
        if (r != 0 && ((r < 0) != (b < 0))) r += b;
        return r;
    }

    public static int B(bool v) => v ? 1 : 0;
}
