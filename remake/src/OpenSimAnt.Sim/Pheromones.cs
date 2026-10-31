using static OpenSimAnt.Sim.Seg;

namespace OpenSimAnt.Sim;

/// <summary>A pheromone map, addressed by (segment, offset) exactly like the original.</summary>
public readonly record struct PherMap(int Seg, int Off);

/// <summary>Pheromone maps (64 x 32, one cell per 2x2 surface tiles). SIMANT.EXE segment 1496 (flat 0x14966..).
/// Cell index = ca*32 + cb, ca = a>>1, cb = b>>1. The red food trail lives at 0x4da7:0000 (= SIM + 0xf8a0),
/// past the 64 KB SIM segment.</summary>
public static class Pheromones
{
    public const int SIMHI = 0x4da7;

    public static readonly PherMap SCRATCH = new(SIM, 0xc89f);
    public static readonly PherMap ALARM = new(SIM, 0xd09f);
    public static readonly PherMap P2 = new(SIM, 0xd89f);
    public static readonly PherMap BLACK_NEST = new(SIM, 0xe09f);
    public static readonly PherMap BLACK_TRAIL = new(SIM, 0xe89f);
    public static readonly PherMap RED_NEST = new(SIM, 0xf09f);
    public static readonly PherMap RED_TRAIL = new(SIMHI, 0x0000);
    public const int SURFACE = 0x0180;
    public const int ENTRANCE_A_BLACK = 0x0224;   // T: surface a of the black entrance in column b (0 = none)
    public const int ENTRANCE_A_RED = 0x0264;

    static int Cell(int a, int b) => (a & 0xfe) * 16 + (b >> 1);

    public static int Get(State st, PherMap m, int i) => st.U8(m.Seg, m.Off + i);

    public static void Put(State st, PherMap m, int i, int v) => st.Set8(m.Seg, m.Off + i, v);

    /// <summary>f_14966 (black) / f_149e9 (red): pin entrance cells to 0xFF (0 if a rock 0x51 covers it).</summary>
    public static void NestMarkers(State st, int entranceTable, PherMap nestMap)
    {
        for (int b = 0; b < 64; b++)
        {
            int a = st.U8(T, entranceTable + b);
            if (a != 0)
            {
                bool blocked = st.Grid(SURFACE, a, b) == 0x51;
                Put(st, nestMap, Cell(a, b), blocked ? 0 : 0xff);
            }
        }
    }

    public static void BlackNestMarkers(State st) => NestMarkers(st, ENTRANCE_A_BLACK, BLACK_NEST);

    public static void RedNestMarkers(State st) => NestMarkers(st, ENTRANCE_A_RED, RED_NEST);

    /// <summary>f_14a6c / f_14ab3: every cell -= 1 (floor 0). Nest-marker maps.</summary>
    public static void DecayLinear(State st, PherMap m)
    {
        for (int i = 0; i < 64 * 32; i++)
        {
            int v = Get(st, m, i);
            if (v != 0) Put(st, m, i, v - 1);
        }
    }

    public static void DecayBlackNest(State st) => DecayLinear(st, BLACK_NEST);

    public static void DecayRedNest(State st) => DecayLinear(st, RED_NEST);

    /// <summary>f_14afa / f_14b5e: v &lt; 8 -> 0, else v -= v >> 1. Food-trail maps.</summary>
    public static void DecayHalving(State st, PherMap m)
    {
        for (int i = 0; i < 64 * 32; i++)
        {
            int v = Get(st, m, i);
            Put(st, m, i, v < 8 ? 0 : v - (v >> 1));
        }
    }

    public static void DecayBlackTrail(State st) => DecayHalving(st, BLACK_TRAIL);

    public static void DecayRedTrail(State st) => DecayHalving(st, RED_TRAIL);

    /// <summary>f_14bbe: copy alarm to scratch, then v = (v + (N+S+E+W)/4) / 2, cleared if &lt;= 8.</summary>
    public static void DiffuseAlarm(State st)
    {
        for (int i = 0; i < 64 * 32; i++)
            Put(st, SCRATCH, i, Get(st, ALARM, i));
        for (int ca = 0; ca < 64; ca++)
        {
            for (int cb = 0; cb < 32; cb++)
            {
                int i = ca * 32 + cb;
                int s = 0;
                if (ca > 0) s = Get(st, SCRATCH, i - 32);
                if (cb > 0) s += Get(st, SCRATCH, i - 1);
                if (ca < 63) s += Get(st, SCRATCH, i + 32);
                if (cb < 31) s += Get(st, SCRATCH, i + 1);
                int v = (Get(st, SCRATCH, i) + (s >> 2)) >> 1;
                Put(st, ALARM, i, v > 8 ? v : 0);
            }
        }
    }

    /// <summary>f_14d2c/14d64 (nest marker), f_14d9c/14dd4 (food trail), f_14cf5 (alarm): cell = max(cell, strength).</summary>
    public static void LayMax(State st, PherMap m, int a, int b, int strength)
    {
        int i = Cell(a, b);
        if (Get(st, m, i) < strength) Put(st, m, i, strength);
    }

    /// <summary>f_14e0c: a step on the surface wears the colony's food trail by 1.</summary>
    public static void WearTrail(State st, int a, int b, bool red)
    {
        var m = red ? RED_TRAIL : BLACK_TRAIL;
        int i = (a >> 1) * 32 + (b >> 1);
        int v = Get(st, m, i);
        if (v != 0) Put(st, m, i, v - 1);
    }
}
