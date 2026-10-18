using static Formica.Sim.Seg;
using static Formica.Sim.Bits;

namespace Formica.Sim;

/// <summary>Colony-level bookkeeping: health, food drops, census, statistics, priorities, caste and job choice.</summary>
public static class Colony
{
    public const int SURFACE = 0x0180, OCC = 0x6180;
    public const int S_TYPE = 0xad3b, S_STATE = 0xa952, S_E = 0xb124;
    public const int B_TYPE = 0xbaec, R_TYPE = 0xc4b5;

    /// <summary>Quarter-wave sine table: int(32767*sin(i*pi/128)) (the original loads it from a resource; same values).</summary>
    public static readonly int[] SINE = Enumerable.Range(0, 64).Select(i => (int)(32767 * Math.Sin(i * Math.PI / 128))).ToArray();

    /// <summary>f_6bc37: sine for an angle 0..255 (256 = full turn), scaled to +-32767.</summary>
    public static int Sin256(int ang)
    {
        int x = ang & 0x7f;
        if (x > 0x3f) x = 0x80 - x;
        int v = x == 0x40 ? 0x7fff : SINE[x & 0x3f];
        return (ang & 0xff) > 0x7f ? -v : v;
    }

    /// <summary>f_6bc8b.</summary>
    public static int Cos256(int ang) => Sin256(ang + 0x40);

    /// <summary>f_0ca03: squared distance (32-bit). Callers usually look at the low word only.</summary>
    public static long Distance(int a1, int b1, int a2, int b2) =>
        ((long)(b2 - b1) * (b2 - b1) + (long)(a2 - a1) * (a2 - a1)) & 0xffffffffL;

    /// <summary>f_6bca5: scatter `count` food crumbs in a disc. count &lt; 0: start-of-game drop (200 crumbs).</summary>
    public static void DropFood(State st, int count, int sound)
    {
        int a0, b0;
        if (count < 0)
        {
            a0 = 0x40;
            b0 = st.Rand(0x30) + 8;
            count = 200;
        }
        else
        {
            a0 = st.Rand128();
            b0 = st.Rand64();
        }
        st.Set16(T, 0x2bc, a0);
        st.Set16(T, 0x2be, b0);
        int r = st.Rand8() + 5;
        for (int k = 0; k < count; k++)
        {
            int ang = st.Rand256();
            int rad = st.Rand(r);
            int a = S16(CDiv(Cos256(ang) * rad, 0x7fff) + a0);
            int b = S16(CDiv(Sin256(ang) * rad, 0x7fff) + b0);
            if (!(0 <= a && a <= 0x7f && 0 <= b && b <= 0x3f)) continue;
            if (st.Grid(OCC, a, b) != 0) continue;
            int t = st.Grid(SURFACE, a, b);
            if (st.U16(G, 0xf24) != 0)
            {
                // house floors: crumbs are 0x18..0x27, four sizes per floor kind
                if (t < 4) st.SetGrid(SURFACE, a, b, (t + 6) << 2);                 // (sic: cl still holds 6)
                else if (t < 0x18) st.SetGrid(SURFACE, a, b, ((t - 8) & 0xfc) + 0x18);
                else if (t < 0x28 && t % 4 < 3) st.SetGrid(SURFACE, a, b, t + 1);
                else continue;
            }
            else if (t < 0x18) st.SetGrid(SURFACE, a, b, 0x48);
            else if (0x48 <= t && t < 0x4b) st.SetGrid(SURFACE, a, b, t + 1);
            else continue;
            st.Inc16(G, 0x1040);
        }
    }

    /// <summary>f_08c12 (every 64 ticks).</summary>
    public static void HealthDecay(State st)
    {
        if (st.U16(T, 0xc18) == 0)
        {
            int v = S16(st.U16(G, 0x10be) - 1);
            st.Set16(G, 0x10be, v >= 0 ? v : 0);
        }
        int w = S16(st.U16(G, 0x1fe) - 1);
        st.Set16(G, 0x1fe, w >= 0 ? w : 0);
        if (st.U16(G, 0xeac) != 3 && S16(st.U16(G, 0x1040)) < S16(st.U16(T, 0xc1a)))
        {
            DropFood(st, 0x96, 1);
            st.Set16(T, 0xc1a, st.Rand(0x32) + 1);
        }
    }

    /// <summary>f_08adb: clear per-state counts; count down the two flight timers.</summary>
    public static void ResetCensus(State st)
    {
        for (int i = 0; i < 20; i++)
        {
            st.Set16(G, 0xd40 + 2 * i, 0);
            st.Set16(G, 0xd72 + 2 * i, 0);
        }
        foreach (int off in new[] { 0x8dc, 0x8e8 })
            if (st.U16(G, off) != 0) st.Set16(G, off, st.U16(G, off) - 1);
    }

    /// <summary>f_0def0: if black has >= 30 ants, the last red surface ant becomes the Avenger (state 19).</summary>
    public static void SpawnAvenger(State st)
    {
        st.Set16(T, 0xc1c, 0);
        if (S16(st.U16(G, 0x330)) < 0x1e) return;
        int i = S16(st.U16(G, 0xd6a));
        while (i > 0)
        {
            i--;
            if (st.U8(SIM, S_TYPE + i) > 0x7f)
            {
                st.Set8(SIM, S_TYPE + i, 0xb0);
                st.Set8(SIM, S_STATE + i, 0x13);
                st.Set8(SIM, S_E + i, 0);
                st.Set16(G, 0x4a4, 0);
                st.Set16(T, 0xc1c, 1);
                return;
            }
        }
    }

    /// <summary>f_08b25: history-graph job counts from the per-state census.</summary>
    public static void StatsFromCensus(State st)
    {
        int C(int @base, int s) => st.U16(G, @base + 2 * s);
        foreach (var (@base, @out) in new[] { (0xd40, 0xb12), (0xd72, 0xc2a) })
        {
            st.Set16(G, @out + 0, C(@base, 2) + C(@base, 3));      // foragers: Foraging + Got Food
            st.Set16(G, @out + 2, C(@base, 4) + C(@base, 5));      // diggers: Dig In + Dig Out
            st.Set16(G, @out + 4, C(@base, 1));                    // nurses: Nesting
            st.Set16(G, @out + 6, C(@base, 7));                    // attackers
            st.Set16(G, @out + 8, C(@base, 12));                   // nest defenders
            st.Set16(G, @out + 10, C(@base, 6));                   // guards / recruits
        }
        if (S16(st.U16(G, 0xd98)) < 1) SpawnAvenger(st);           // no red Avenger
    }

    /// <summary>f_0be82: count every ant by caste, derive populations, detect dead queens / game over.
    /// showMessage(stringId) is called for the messages the original pops up.</summary>
    public static void Census(State st, Action<int> showMessage)
    {
        for (int i = 0; i < 32; i++) st.Set16(G, 0xeb6 + 2 * i, 0);
        st.Set16(G, 0xafa, 0);
        st.Set16(G, 0xaec, 0);
        foreach (var (countOff, typeBase) in new[] { (0xd6a, S_TYPE), (0xda8, B_TYPE), (0xeaa, R_TYPE) })
        {
            int i = S16(st.U16(G, countOff));
            while (i > 0)
            {
                i--;
                int t = st.U8(SIM, typeBase + i);
                if (t != 0) st.Inc16(G, 0xeb6 + ((t & 0xfb) >> 2));
            }
        }
        if (st.U16(G, 0xa06) == 0)                               // count the yellow ant too
        {
            int t = st.U16(G, 0x4c2) & 0xfffb;
            if (st.U16(G, 0x4e2) != 0) t |= 0x80;
            st.Inc16(G, 0xeb6 + (t >> 2));
        }
        int K(int caste) => st.U16(G, 0xeb6 + 2 * caste);
        st.Set16(G, 0xaec, K(0));
        st.Set16(G, 0xaee, K(1) + K(2) + K(3) + K(5));
        st.Set16(G, 0xaf0, K(6) + K(7) + K(9));
        st.Set16(G, 0xaf2, K(4));
        st.Set16(G, 0xaf4, K(8));
        if (st.U16(G, 0xaf6) != 0 && K(12) == 0 && st.U16(G, 0x354) == 0)
        {
            showMessage(10010);                                 // the black queen has died
            if (S16(st.U16(G, 0xeac)) <= 1)
            {
                showMessage(10011);                             // defeated by the reds
                st.Set16(G, 0x376, 1);
                st.Set16(G, 0x366, 0);
            }
        }
        st.Set16(G, 0xaf6, K(12));
        st.Set16(G, 0xafa, K(16));
        st.Set16(G, 0xafc, K(18) + K(19) + K(21) + K(17));     // red workers (castes 2, 3, 5, 1)
        st.Set16(G, 0xafe, K(23) + K(22) + K(25));             // red soldiers (7, 6, 9)
        st.Set16(G, 0xb00, K(20));                             // red males
        st.Set16(G, 0xb02, K(24));                             // red new queens
        if (st.U16(G, 0xb04) != 0)
        {
            if (st.U16(G, 0xeee) == 0 && st.U16(G, 0x354) == 0)
            {
                showMessage(10012);                             // the red queen has died
                if (S16(st.U16(G, 0xeac)) <= 1)
                {
                    showMessage(10013);                         // you have won
                    st.Set16(G, 0x376, 1);
                    st.Set16(G, 0x366, 1);
                }
                if (st.U16(G, 0xeac) == 2 && st.U16(G, 0x400) == 1 && st.U16(G, 0x7ca) == 0xb
                    && st.U16(G, 0x7cc) == 8)
                    st.Set8(T, 0x184 + st.Rand(6) * 16, 0x14);
            }
        }
        st.Set16(G, 0x330, (st.U16(G, 0xaf2) + st.U16(G, 0xaee) + st.U16(G, 0xaf0) + st.U16(G, 0xaf4)
                            + st.U16(G, 0xaf6)) & 0xffff);
        st.Set16(G, 0xb04, st.U16(G, 0xeee));
        st.Set16(G, 0x350, (st.U16(G, 0xb04) + st.U16(G, 0xb02) + st.U16(G, 0xafc) + st.U16(G, 0xb00)
                            + st.U16(G, 0xafe)) & 0xffff);
        st.Set16(G, 0x354, 0);
    }

    /// <summary>f_1395b: colony priority row 0..5 for the black colony (see SIM_NOTES).</summary>
    public static int BlackPriority(State st)
    {
        int health = S16(st.U16(G, 0x10be));
        int pb = S16(st.U16(G, 0x330)), pr = S16(st.U16(G, 0x350));
        if (health < 10 && (pb >> 1) > pr && pr > 0 && S16(st.U16(G, 0x36c)) > 0) return 0;
        if (health < 0x1e) return 5;
        if (health < 0x32) return 4;
        int cap = S16(st.U16(G, 0x224));
        if (pb > cap) return 3;
        if (S16(pb * 2) > cap) return 2;
        if (pb > 0x64 && pr > 0 && S16(st.U16(G, 0x36c)) > 0 && CDiv(pb, 3) > pr) return 0;
        return 1;
    }

    /// <summary>f_13d35.</summary>
    public static void RedLaunchAttack(State st, Action<int, int> showStatus)
    {
        st.Set16(G, 0x504, st.Rand(0x64) + 0x1e);
        showStatus(1020, 5);          // "The red ants are attacking!" in the status line (UI)
    }

    /// <summary>f_13be3: colony priority row for the red colony; also starts red mating flights and raids.</summary>
    public static int RedPriority(State st, Action<int, int> showStatus)
    {
        if (st.U16(G, 0x8e8) == 0 && S16(st.U16(G, 0xb00) + st.U16(G, 0xb02)) > 0x14)
            st.Set16(G, 0x8e8, 0xc8);
        if (st.U16(G, 0x504) != 0)
        {
            st.Set16(G, 0x504, st.U16(G, 0x504) - 1);
            return 0;
        }
        int health = S16(st.U16(G, 0x1fe));
        int pr = S16(st.U16(G, 0x350)), pb = S16(st.U16(G, 0x330));
        if (health < 10 && (pr >> 1) > pb && pb > 0 && S16(st.U16(G, 0x35e)) > 0)
        {
            RedLaunchAttack(st, showStatus);
            return 0;
        }
        if (health < 0x1e) return 5;
        if (health < 0x32) return 4;
        int cap = S16(st.U16(G, 0x232));
        if (pr > cap) return 3;
        if (S16(pr * 2) > cap) return 2;
        if (pr > 0x64 && pb > 0 && S16(st.U16(G, 0x35e)) > 0 && CDiv(pr, 3) > pb)
        {
            RedLaunchAttack(st, showStatus);
            return 0;
        }
        if (st.Rand32() == 0 && pr > 0x14 && pr > pb && st.Rand128() == 0)
        {
            RedLaunchAttack(st, showStatus);
            return 0;
        }
        return 1;
    }

    /// <summary>f_13a28: next hatchling joins the caste group furthest below the caste-triangle target.</summary>
    public static void ChooseHatchCaste(State st)
    {
        var counts = Enumerable.Range(0, 4).Select(i => S16(st.U16(G, 0xaee + 2 * i))).ToArray();
        var targets = Enumerable.Range(0, 4).Select(i => S16(st.U16(T, 0x7da + 2 * i))).ToArray();
        int tot = S16(counts.Sum()), ttot = S16(targets.Sum());
        int best = 0, idx = 0;
        for (int i = 0; i < 4; i++)
        {
            int actual = tot > 0 ? S16(CDiv(100 * counts[i], tot)) : 0;
            int want = ttot > 0 ? S16(CDiv(100 * targets[i], ttot)) : 0;
            int d = S16(actual - want);
            if (d < best) { best = d; idx = i; }
        }
        st.Set16(T, 0xc0e, st.U16(T, 0xb66 + 2 * idx));
    }

    /// <summary>f_13b26: in manual mode, the most understaffed of forage / dig / nurse.</summary>
    public static void ChooseManualJob(State st)
    {
        var cur = Enumerable.Range(0, 3).Select(i => S16(st.U16(G, 0xb12 + 2 * i))).ToArray();
        int tot = S16(cur.Sum());
        int best = 0, idx = 0;
        for (int i = 0; i < 3; i++)
        {
            long w = st.U16(G, 0x49e + 2 * i);
            int want = tot >= 0 ? S16((int)(((w * tot) & 0xffffffffL) / 0xffff)) : S16((int)(w * tot / 0xffff));
            int d = S16(want - cur[i]);
            if (d > best) { best = d; idx = i; }
        }
        st.Set16(T, 0xc10, st.U16(T, 0xb6e + 2 * idx));
    }

    /// <summary>f_13832 (every tick): recruit guard point, priorities, caste and job choice.</summary>
    public static void ColonyAdvisor(State st, Action<int, int> showStatus)
    {
        st.Set16(G, 0x248, 0);
        if (st.U16(G, 0x48c) == 1)
        {
            int ga = S16(st.Rand(5) + st.U16(G, 0x47c) - 2);
            st.Set16(G, 0x22a, ga);
            int gb = S16(st.Rand(5) + st.U16(G, 0x48a) - 2);
            st.Set16(G, 0x238, gb);
            if (S16(st.U16(G, 0x22a)) < 0) st.Set16(G, 0x22a, 0);
            if (S16(st.U16(G, 0x22a)) > 0x7f) st.Set16(G, 0x22a, 0x7f);
            if (S16(st.U16(G, 0x238)) < 0) st.Set16(G, 0x238, 0);
            if (S16(st.U16(G, 0x238)) > 0x3f) st.Set16(G, 0x238, 0x3f);
            if (st.U16(G, 0xf0c) != 0)
            {
                long d = Distance(S16(st.U16(G, 0xf12)) >> 4, S16(st.U16(G, 0xf34)) >> 4,
                                  st.U16(G, 0x47c), st.U16(G, 0x48a));
                if (S16(d) < 0x64) st.Set16(G, 0x248, 1);
            }
        }
        st.Set16(G, 0x22a, st.U16(G, 0x47c));      // (overwrites the jittered value: original behaviour)
        st.Set16(G, 0x1094, BlackPriority(st));
        st.Set16(G, 0x10a6, RedPriority(st, showStatus));
        ChooseHatchCaste(st);
        ChooseManualJob(st);
    }
}
