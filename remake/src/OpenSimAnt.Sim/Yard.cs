using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;
using Co = OpenSimAnt.Sim.Colony;

namespace OpenSimAnt.Sim;

/// <summary>The yard layer (sec8 f_68513, segment 783a), run every tick by SimStep: the human walking through
/// or roaming the yard (with the lawnmower), foot stamps on the player's patch, the bird crossing and the
/// bird, the dog, rain, and the colonies of the other 191 patches of the yard.
/// The yard is 12 x 16 patches (col G:07CA, row G:07CC is the player's); per-patch colony strengths are
/// T:00A4[col*16 + row] (black) and T:0164[...] (red), 0..0xFA. Screen coordinates of the yard map turn
/// into patches as col = (x + y - 0xC8) / 28, row = (y - 0x26) / 10 (C division).</summary>
public static class Yard
{
    const int OCC = 0x6180, STYPE = 0xad3b;

    static bool SoundOn(State st) => st.U16(T, 0x7c8) == 0 && S16(st.U16(G, 0x35c)) < 2;

    /// <summary>f_6856a: queue the human's sound / speech bubble n (shown until clock3() + 300).</summary>
    public static void HumanSound(State st, int n)
    {
        if (S16(n) <= 0x16)
        {
            st.Set32(G, 0x109c, (st.Clock3() + 300) & 0xffffffffL);
            st.Set16(G, 0x10b0, 1);
            st.Set16(G, 0x10bc, n);
        }
    }

    /// <summary>f_68513.</summary>
    public static void YardStep(State st)
    {
        st.Inc16(G, 0x7c2);
        if (S16(st.U16(G, 0x7c2)) >= 0x400) st.Set16(G, 0x7c2, 0);
        if (S16(st.U16(T, 0xc48)) < 0x26) HumanWalk(st);
        else HumanRoam(st);
        BirdCrossing(st);
        Bird(st);
        if (st.U16(T, 0xc44) == 0) Dog(st);
        RainControl(st);
        YardColonies(st);
    }

    // ------------------------------------------------------------------------------------------- the human
    // T:0C48 script state (< 0x26 scripted walk, 0x26 roaming), T:0C46 frame counter, T:0C2C / T:0C2E position
    // on the yard map, T:0C32 sprite, T:0C30 heading (0 up, 1 right, 2 down, 3 left; bit 0 picks the foot's
    // shape), T:0C28 roaming mode, T:0C3E foot on the player's patch, T:0C42 alternating foot, G:0246 / G:023E
    // patch (col / row), G:0202 mowing
    static readonly int[][] WALK_FRAMES =
    {
        new[] { 0x2474, 0x2478, 0x247c }, new[] { 0x2480, 0x2484, 0x2488 }, new[] { 0x248c, 0x24a0, 0x24b4 },
        new[] { 0x24c8, 0x24dc, 0x24f0 }, new[] { 0x2504, 0x2508, 0x250c }, new[] { 0x2510, 0x2514, 0x2518 },
        new[] { 0x251c, 0x2528, 0x2534 }, new[] { 0x2540, 0x254c, 0x2558 }, new[] { 0x2564, 0x256a, 0x2570 },
        new[] { 0x2576, 0x257c, 0x2582 }, new[] { 0x2588, 0x258c, 0x2590 }, new[] { 0x2594, 0x2598, 0x259c },
        new[] { 0x25a0, 0x25a6, 0x25ac }, new[] { 0x25b2, 0x25b8, 0x25be }, new[] { 0x25c4, 0x25c8, 0x25cc },
        new[] { 0x25d0, 0x25d4, 0x25d8 },
    };

    /// <summary>The jump table at flat 0x68F39 (and the 0x1E..0x26 scripted states): sprite, x, y.</summary>
    static (int, int, int) WalkFrame(State st, int c48)
    {
        int c46 = st.U16(T, 0xc46);
        if (c48 < 0x1e)
        {
            if (c48 >= 0 && c48 < 16)
            {
                var f = WALK_FRAMES[c48];
                return (st.U8(DS, f[0] + c46), st.U8(DS, f[1] + c46), st.U8(DS, f[2] + c46));
            }
            if (c48 == 20) return (st.U16(DS, 0x25dc + c46 * 2), st.U8(DS, 0x25ec + c46), st.U8(DS, 0x25f4 + c46));
            if (c48 == 21) return (st.U16(DS, 0x25fc + c46 * 2), st.U8(DS, 0x2606 + c46), st.U8(DS, 0x260c + c46));
            throw new NotImplementedException($"human_walk state {c48} (uninitialised locals in the original)");
        }
        if (c48 >= 0x27) throw new NotImplementedException($"human_walk state {c48} (uninitialised locals in the original)");
        int d = c48 - 0x1e;
        var frame = (st.U16(DS, 0x2654 + d * 2), st.U8(DS, 0x2666 + d), st.U8(DS, 0x2670 + d));
        int n = st.U8(DS, 0x267a + d);
        if (n == 0) throw new NotImplementedException($"human_walk state {c48}: Rand(0) (division by zero in the original)");
        if (st.Rand(n) == 0)
        {
            st.Set16(T, 0xc48, st.U8(DS, 0x2684 + d));
            st.Set16(T, 0xc46, 0);
        }
        return frame;
    }

    static (int v, int col, int row) PatchOf(int x, int y)
    {
        int v = S16(x + y - 0xc8);
        return (v, CDiv(v, 28), CDiv(S16(y - 0x26), 10));
    }

    /// <summary>Where on the player's patch the foot lands (G:03E0 a, G:046A b), before the +-6 nudge.</summary>
    static void FootSpot(State st, int v, int y)
    {
        int r10 = CMod(S16(y - 0x26), 10);
        st.Set16(G, 0x46a, r10);
        st.Set16(G, 0x3e0, (CMod(v, 28) * 4 + 6) & 0x7f);
        st.Set16(G, 0x46a, ((r10 + 1) * 6) & 0x3f);
    }

    static void FootNudge(State st)
    {
        int d = st.U16(T, 0xc42) != 0 ? 6 : -6;
        int off = (st.U8(T, 0xc30) & 1) != 0 ? 0x46a : 0x3e0;
        st.Set16(G, off, st.U16(G, off) + d);
    }

    /// <summary>f_68e30: the scripted human walking through the yard.</summary>
    public static void HumanWalk(State st)
    {
        if (st.U16(T, 0xc44) == 1) return;
        int c48 = S16(st.U16(T, 0xc48));
        if (c48 < 0x1e)
        {
            st.Inc16(T, 0xc46);
            if (st.S8(DS, 0x245e + c48) < S16(st.U16(T, 0xc46)))
            {
                st.Set16(T, 0xc46, 0);
                c48 = st.U8(DS, new[] { 0x2612, 0x2628, 0x263e }[st.Rand(3)] + c48);
                st.Set16(T, 0xc48, c48);
                int n = -1;
                if (c48 == 0x21) n = 0x14;
                else if (c48 == 6) n = 0x15;
                else if (c48 == 7) n = 0x16;
                else if (c48 == 0xe) n = st.Rand(3) + 0xf;
                else if (c48 == 0x10) n = st.Rand(2) + 0x12;
                if (n >= 0) HumanSound(st, n);
            }
        }
        var (si, x, y) = WalkFrame(st, S16(st.U16(T, 0xc48)));
        c48 = S16(st.U16(T, 0xc48));
        int c46 = S16(st.U16(T, 0xc46));
        st.Set16(T, 0xc28, 0);
        if (c48 == 0x26)
        {
            st.Set16(T, 0xc30, 1);
            st.Set16(T, 0xc28, 1);
        }
        if (c48 == 0x14 && c46 > 2) st.Set16(T, 0xc28, 1);
        if (c48 == 0x15 && c46 < 3) st.Set16(T, 0xc28, 1);
        st.Set16(T, 0xc2c, x);
        st.Set16(T, 0xc2e, y);
        st.Set16(T, 0xc32, si);
        if (SoundOn(st) && ((c46 == 3 && c48 == 0x14 && si == 0x384) || (c46 == 1 && c48 == 0x15 && si == 0x387)
                            || (c46 == 6 && c48 == 0x14 && si == 6) || (c46 == 3 && c48 == 0x15 && si == 1)))
            st.Hooks.Effect(st, "sound", 0x18);
        var (v, col, row) = PatchOf(x, y);
        st.Set16(G, 0x246, col);
        st.Set16(T, 0xc3e, 0);
        st.Set16(T, 0xc42, st.U16(T, 0xc42) == 0 ? 1 : 0);
        st.Set16(G, 0x23e, row);
        int pcol = st.U16(G, 0x7ca);
        int idx = (pcol * 16 + st.U16(G, 0x7cc)) & 0xffff;
        if ((row & 0xffff) != st.U16(G, 0x7cc) || pcol != (col & 0xffff) || idx == 0 || idx == 1 || idx == 0x10 || idx == 0x20)
            return;
        int s = S16(st.U16(T, 0xc32));
        st.Set16(T, 0xc30, 0 <= s && s < 12 ? st.U8(DS, 0x268e + s) : 2);
        st.Set16(T, 0xc3e, 1);
        FootSpot(st, v, y);
        FootNudge(st);
        FootStamp(st, S16(st.U16(G, 0x3e0)), S16(st.U16(G, 0x46a)));
        st.Hooks.Effect(st, "sound", 9);
        int i = 0;
        while (S16(((st.U16(G, 0x330) + st.U16(G, 0x350)) << 3) & 0xffff) > i)   // random ants all over the patch
        {
            int a = st.Rand128(), b = st.Rand64();
            if (st.Grid(OCC, a, b) != 0)
            {
                int j = Movement.SurfaceAntAt(st, a, b);
                st.Set16(G, 0xf18, j);
                if (j >= 0)
                {
                    Surface.PlaceCorpse(st, a, b, (st.U8(SIM, STYPE + j) & 0x80) != 0);
                    st.Set8(SIM, STYPE + st.U16(G, 0xf18), 0);
                    st.SetGrid(OCC, a, b, 0);
                }
            }
            if (S16(st.U16(G, 0xf12)) >> 4 == a && S16(st.U16(G, 0xf34)) >> 4 == b) World.SpiderBeaten(st);
            i++;
        }
        if (st.U16(G, 0xeac) == 2 && st.U16(G, 0x48c) == 1 && st.Rand4() == 0) st.Hooks.YardEvent(st, 9);
    }

    /// <summary>f_69f53: everything under the foot (16 x 6 or 6 x 16 cells from (x, y)) dies.</summary>
    public static void FootStamp(State st, int x, int y)
    {
        st.Hooks.Effect(st, "sound", 0x23);
        int xe, ye;
        if ((st.U8(T, 0xc30) & 1) != 0) { xe = x + 16; ye = y + 6; }
        else { xe = x + 6; ye = y + 16; }
        for (int a = x; a < xe; a++)
        {
            for (int b = y; b < ye; b++)
            {
                if (!(0 <= a && a <= 0x7f && 0 <= b && b <= 0x7f)) continue;     // (sic: b up to 0x7F)
                int o = st.U8(SIM, OCC + a * 64 + b);
                if (o == 0) continue;
                if (o == 0xfe || o == 0xff)
                {
                    st.Hooks.YardEvent(st, 5);
                    continue;
                }
                int j = Movement.SurfaceAntAt(st, a, b);
                if (j >= 0)
                {
                    Surface.PlaceCorpse(st, a, b, (st.U8(SIM, STYPE + j) & 0x80) != 0);
                    st.Set8(SIM, STYPE + j, 0);
                }
            }
        }
        int sx = S16(st.U16(G, 0xf42)), sy = S16(st.U16(G, 0xf7e));
        if (x <= sx && sx < xe && y <= sy && sy < ye)
        {
            World.SpiderBeaten(st);
            if (st.U16(G, 0xa06) == 1) st.Hooks.YardEvent(st, 5);
        }
    }

    /// <summary>f_68dd2.</summary>
    static bool InYard(int col, int row) => 0 <= col && col <= 0xb && 0 <= row && row <= 0xf;

    /// <summary>f_68d97: the mowing mask (word G:0334[col], bit row); clears the bit it finds.</summary>
    static bool TakeMowBit(State st, int col, int row)
    {
        int bit = 1 << row;
        int w = st.U16(G, 0x334 + col * 2);
        if ((w & bit) != 0)
        {
            st.Set16(G, 0x334 + col * 2, w - bit);
            return true;
        }
        return false;
    }

    /// <summary>f_68d07: head for an unmown neighbouring patch.</summary>
    public static int MowHeading(State st, int col, int row)
    {
        for (int d = 3; d >= 0; d--)
        {
            int c = col + st.S8(DS, 0x26b2 + d), r = row + st.S8(DS, 0x26b6 + d);
            if (InYard(c, r) && TakeMowBit(st, c, r)) return d;
        }
        if (col > 0xa) return 0;
        if (row > 0xe) return 1;
        if (row < 1)
        {
            HumanSound(st, 6);
            st.Set16(T, 0xc28, 4);
            return 2;
        }
        return st.U8(G, 0x7c2) & 3;
    }

    /// <summary>f_68dff: everything from column 3 on needs mowing.</summary>
    public static void MowReset(State st)
    {
        for (int c = 0; c < 3; c++) st.Set16(G, 0x334 + c * 2, 0);
        for (int c = 3; c < 12; c++) st.Set16(G, 0x334 + c * 2, 0xffff);
    }

    /// <summary>Head for the house corner: rows above/below rowMid, then left. True when there.</summary>
    static bool Steer(State st, int rowMid, int colMax)
    {
        int row = S16(st.U16(G, 0x23e));
        if (row < rowMid) st.Set16(T, 0xc30, 2);
        else if (row > rowMid) st.Set16(T, 0xc30, 0);
        else if (S16(st.U16(G, 0x246)) > colMax) st.Set16(T, 0xc30, 3);
        else return true;
        return false;
    }

    /// <summary>f_68659: the human (and the lawnmower) wandering the yard.</summary>
    public static void HumanRoam(State st)
    {
        if (st.U16(T, 0xc3e) != 0 && (st.U8(G, 0x7c2) & 3) != 0) return;
        if (st.U16(G, 0x202) != 0)
        {
            if (st.U16(G, 0x246) != st.U16(G, 0x488) || st.U16(G, 0x23e) != st.U16(G, 0x492))
                st.Set16(T, 0xc30, MowHeading(st, S16(st.U16(G, 0x246)), S16(st.U16(G, 0x23e))));
        }
        else
        {
            st.Inc16(T, 0xc34, -1);
            if (S16(st.U16(T, 0xc34)) < 0)
            {
                st.Set16(T, 0xc30, (st.Rand(3) + st.U8(T, 0xc30) - 1) & 3);
                st.Set16(T, 0xc34, 4);
            }
        }
        int mode = st.U16(T, 0xc28);
        if (mode == 1)
        {
            if (st.Rand(900) == 0)
            {
                HumanSound(st, 1);
                st.Set16(T, 0xc28, 2);
            }
            else if (st.Rand(600) == 0 || st.U16(G, 0xeac) == 0 || st.U16(G, 0xeac) == 3)
            {
                HumanSound(st, 2);
                st.Set16(T, 0xc28, 5);
            }
            else
            {
                if (st.Rand(200) == 0) HumanSound(st, st.Rand(8) + 7);
                if (st.U16(G, 0x352) != 0) st.Set16(T, 0xc28, 5);
            }
        }
        else if (mode == 2)
        {
            if (Steer(st, 12, 3))
            {
                st.Set16(T, 0xc28, 3);
                st.Set16(G, 0x488, 3);
                st.Set16(G, 0x492, 13);
                st.Set16(G, 0x202, 1);
                MowReset(st);
                st.Set16(T, 0xc30, 2);
                st.Set16(T, 0xc2c, 0x7d);
                st.Set16(T, 0xc2e, 0xaa);
            }
        }
        else if (mode == 3)
        {
            if (st.Rand(100) == 0) HumanSound(st, st.Rand(3) + 3);
            if (st.Rand(200) == 0)
            {
                HumanSound(st, 6);
                st.Set16(T, 0xc28, 4);
            }
            st.Set16(G, 0x488, st.U16(G, 0x246));
            st.Set16(G, 0x492, st.U16(G, 0x23e));
            st.Set16(G, 0x202, 1);
        }
        else if (mode == 4)
        {
            if (Steer(st, 12, 3))
            {
                st.Set16(T, 0xc28, 5);
                st.Set16(G, 0x202, 0);
            }
            st.Set16(G, 0x488, st.U16(G, 0x246));
            st.Set16(G, 0x492, st.U16(G, 0x23e));
        }
        else if (mode == 5)
        {
            if (Steer(st, 5, 3)) st.Set16(T, 0xc28, 1);
        }
        int c30 = st.U16(T, 0xc30);
        st.Set16(T, 0xc32, st.S8(DS, 0x269e + c30) + st.S8(DS, 0x269a + (st.U8(G, 0x7c2) & 3)));
        bool mowing = st.U16(G, 0x202) != 0;
        if (mowing || st.U16(T, 0xc40) == 0)
        {
            if (mowing) st.Inc16(T, 0xc32, 100);
            else if (st.Rand32() == 0) st.Set16(T, 0xc40, 20);                // stop for a while
            st.Inc16(T, 0xc2c, st.S8(T, 0xc36 + c30));
            st.Inc16(T, 0xc2e, st.S8(T, 0xc3a + c30));
        }
        else
        {
            st.Inc16(T, 0xc40, -1);
            st.Set16(T, 0xc32, c30 + 20);                                   // standing
        }
        int x = st.U16(T, 0xc2c), y = st.U16(T, 0xc2e);
        var (v, col, row) = PatchOf(x, y);
        row = Math.Min(Math.Max(row, 0), 0xf);
        col = Math.Min(Math.Max(col, 0), 0xb);
        st.Set16(G, 0x246, col);
        st.Set16(G, 0x23e, row);
        if (!mowing)                                                         // keep to the yard, away from the house
        {
            if (row < 1) st.Set16(T, 0xc30, 2);
            else if (row > 0xe) st.Set16(T, 0xc30, 0);
            if (col > 0xa) st.Set16(T, 0xc30, 3);
            else if (row < 5)
            {
                if (col < 4) st.Set16(T, 0xc30, 1);
            }
            else if (col < 3)
            {
                st.Set16(T, 0xc30, 0);
                if (row < 6)
                {
                    if (st.U16(T, 0xc28) == 3) st.Set16(T, 0xc30, 1);
                    else st.Set16(T, 0xc48, 0x15);
                }
            }
        }
        st.Set16(T, 0xc3e, 0);
        st.Set16(T, 0xc42, st.U16(T, 0xc42) == 0 ? 1 : 0);
        if (st.U16(G, 0x7cc) == row && st.U16(G, 0x7ca) == col)
        {
            st.Set16(T, 0xc3e, 1);
            FootSpot(st, v, S16(y));
            c30 = st.U16(T, 0xc30);
            st.Set16(G, 0x470, st.U16(G, 0x3e0) + st.U16(DS, 0x26a2 + (c30 & 3) * 2));
            st.Set16(G, 0x47a, st.U16(G, 0x46a) + st.U16(DS, 0x26aa + (c30 & 3) * 2));
            FootNudge(st);
            FootStamp(st, S16(st.U16(G, 0x3e0)), S16(st.U16(G, 0x46a)));
            if (mowing) Mower(st);
        }
        else if (mowing)                                                     // mowing another patch thins its colonies
        {
            int idx = col * 16 + row;
            foreach (var (@base, dead) in new[] { (0xa4, 0xa9e), (0x164, 0xac8) })
            {
                int c = st.U8(T, @base + idx);
                if (c != 0)
                {
                    c -= c >> 2;
                    if (c == 0) st.Inc16(G, dead);
                    st.Set8(T, @base + idx, c);
                }
            }
        }
    }

    /// <summary>f_6a08a (its position args G:0470 / G:047A are unused): the lawnmower over the player's patch.</summary>
    public static void Mower(State st)
    {
        if (st.U16(G, 0xeac) == 0) return;
        int i = S16(st.U16(G, 0xd6a));
        while (i > 0)
        {
            i--;
            if (st.U8(SIM, STYPE + i) != 0 && st.Rand4() != 0)
            {
                st.SetGrid(OCC, st.U8(SIM, 0xa180 + i), st.U8(SIM, 0xa569 + i), 0);
                st.Set8(SIM, STYPE + i, 0);
            }
        }
        if (st.U16(G, 0xf0c) != 0 && st.Rand4() != 0) World.SpiderBeaten(st);
        if (S16(st.U16(G, 0xa06)) <= 1 && st.U16(G, 0x48c) == 1 && st.Rand4() != 0) st.Hooks.YardEvent(st, 6);
    }

    // ------------------------------------------------------------------------------------------- birds
    /// <summary>f_6959f: a bird flies across the yard map (state G:10A0, x G:10AC, y G:10BA); while queens are
    /// out on their mating flight it dives at the player's patch (G:0208 / G:0210) and eats some of them.</summary>
    public static void BirdCrossing(State st)
    {
        int state = st.U16(G, 0x10a0);
        if (state == 0)
        {
            long now = st.U32(G, 0x383a);
            if (S32(now) <= S32(st.U32(G, 0x107e))) return;
            st.Set32(G, 0x107e, (now + 20) & 0xffffffffL);
            if (S16(st.U16(G, 0x7ca)) < 5 || st.Rand2() != 0) return;
            if (S16(st.U16(G, 0x6aa)) <= 0 && S16(st.U16(G, 0x73a)) <= 0) return;
            int col = S16(st.U16(G, 0x7ca)), row = S16(st.U16(G, 0x7cc));
            st.Set16(G, 0x208, col * 28 - row * 10 + 0xb2);
            st.Set16(G, 0x210, row * 10 + 0x2e);
            st.Set16(G, 0x10a0, 1);
            st.Set16(G, 0x10ac, 0);
            st.Set16(G, 0x10ba, st.Rand64() + 4);
            st.Set16(G, 0x108c, 0);
            return;
        }
        st.Inc16(G, 0x10ac, state == 1 ? 16 : 8);
        if (state == 1)
        {
            int d = S16(st.U16(G, 0x210) - st.U16(G, 0x10ba));
            if (d != 0)
            {
                int step = Math.Abs(d) >= 4 ? 4 : 1;
                st.Inc16(G, 0x10ba, d > 0 ? step : -step);
            }
        }
        else
            st.Inc16(G, 0x10ba, -8);
        st.Set16(G, 0x108c, (st.U8(G, 0x108c) + 1) & 1);
        int x = S16(st.U16(G, 0x10ac)), y = S16(st.U16(G, 0x10ba));
        if (x < 0 || x > 0x1ff || y < 0 || y > 0xff)
        {
            st.Set16(G, 0x10a0, 0);
            st.Set32(G, 0x107e, (st.U32(G, 0x383a) + 30) & 0xffffffffL);
            return;
        }
        int ty = S16(st.U16(G, 0x210));
        if (state != 1 || S16(st.U16(G, 0x208)) > x || !(ty - 4 <= y && y <= ty + 4)) return;
        foreach (int off in new[] { 0x6aa, 0x7c8, 0x73a, 0x850 })                 // flying queens / new colonies eaten
        {
            int c = S16(st.U16(G, off));
            if (c > 0) st.Set16(G, off, c - ((c + 7) >> 3));
        }
        if (SoundOn(st) && st.Rand2() == 0) st.Hooks.Effect(st, "sound", 7);
        st.Set16(G, 0x10a0, 2);
    }

    /// <summary>f_6986c: the bird on the yard map (state G:0254, x G:02BE, y G:032C, heading G:0240, frame
    /// G:0244, timer G:022C); it may land when the dog sits, and swoops at the dog when close. (The yard window
    /// draws this actor with the cat frames, bitmaps 1300 + G:0244 (f_7004e): it is the cat; the name is kept.)</summary>
    public static void Bird(State st)
    {
        int state = st.U16(G, 0x254);
        if (state == 0)
        {
            if (S32(st.U32(G, 0x220)) >= S32(st.Clock3())) return;
            st.Set32(G, 0x220, (st.Clock3() + 200) & 0xffffffffL);
            if (st.Rand16() == 0 || st.U16(G, 0xb20) == 0x8d)
            {
                st.Set16(G, 0x254, 1);
                st.Set16(G, 0x2be, 0xfc);
                st.Set16(G, 0x32c, 0x19);
                st.Set16(G, 0x240, 2);
                st.Set16(G, 0x244, 0);
                st.Set16(G, 0x22c, 0);
            }
            return;
        }
        st.Set16(G, 0x22c, (st.U16(G, 0x22c) + 1) & 0xfff);
        if (state == 1)
        {
            int h = st.U16(G, 0x240);
            int nx = S16(st.S8(T, h) * 4 + st.U16(G, 0x2be));
            int ny = st.S8(T, 8 + h) * 4 + st.U16(G, 0x32c);
            if (st.Rand16() == 0 || nx < 0xfc || nx > 0x1ef)                // turn around
            {
                if (h == 2)
                {
                    st.Set16(G, 0x240, 6);
                    st.Set16(G, 0x244, 4);
                }
                else
                {
                    st.Set16(G, 0x240, 2);
                    st.Set16(G, 0x244, 1);
                }
            }
            else
            {
                st.Set16(G, 0x2be, nx);
                st.Set16(G, 0x32c, ny);
                st.Inc16(G, 0x244);
                int f = S16(st.U16(G, 0x244));
                if (h == 2)
                {
                    if (f >= 3) st.Set16(G, 0x244, 1);
                }
                else if (f >= 6) st.Set16(G, 0x244, 4);
            }
            if (SoundOn(st) && st.Rand64() == 0)
            {
                st.Hooks.Effect(st, "sound", 0xd);
                return;
            }
            if (st.Rand16() == 0 && S16(st.U16(G, 0x22c)) > 100 && st.U16(G, 0x506) == 2
                && st.U16(T, 0xc28) == 0)
            {
                st.Set16(G, 0x254, 2);                                      // lands
                st.Set16(G, 0x22c, 0);
                st.Set16(G, 0x244, 10);
                return;
            }
            if (S16(st.U16(G, 0x22c)) <= 0x32) return;
            long d = Co.Distance(S16(st.U16(G, 0x2be)), S16(st.U16(G, 0x32c)), S16(st.U16(G, 0x4be)),
                                 S16(st.U16(G, 0x4c6)));
            if (d <= 0x960)
            {
                st.Set16(G, 0x254, 3);                                      // swoops at the dog
                st.Set16(G, 0x244, 0x14);
                if (SoundOn(st)) st.Hooks.Effect(st, "sound", 0xe);
            }
        }
        else if (state == 2)
        {
            st.Inc16(G, 0x244);
            if (S16(st.U16(G, 0x244)) >= 0xd) st.Set16(G, 0x244, 0xb);
            st.Inc16(G, 0x22c);
            if (S16(st.U16(G, 0x22c)) > 0x1e)
            {
                st.Set16(G, 0x22c, 0);
                st.Set16(G, 0x254, 1);
                st.Set16(G, 0x244, st.U16(G, 0x240) == 2 ? 0 : 3);
            }
        }
        else
        {
            st.Inc16(G, 0x244);
            if (S16(st.U16(G, 0x244)) >= 0x1e)
            {
                st.Set16(G, 0x244, 0);
                st.Set16(G, 0x254, 0);
                st.Set32(G, 0x220, (st.Clock3() + 600) & 0xffffffffL);
            }
        }
    }

    // ------------------------------------------------------------------------------------------- the dog
    /// <summary>f_69ea8.</summary>
    public static void Bark(State st, int p, int vol)
    {
        if (!SoundOn(st)) return;
        if (S32(st.U32(G, 0x736)) >= S32(st.Clock3())) return;
        if (p >= 0 && p <= 3) st.Hooks.Effect(st, "sound", new[] { 0x17, 0x15, 0x17, 0x16 }[p], vol);
        st.Set32(G, 0x736, (st.Clock3() + st.Rand(30) + 60) & 0xffffffffL);
    }

    /// <summary>f_69e5f: back towards the house while the bird is about.</summary>
    static int DogHome(State st)
    {
        int col = S16(st.U16(G, 0x510));
        if (col < 5) return 1;
        if (col > 8) return 3;
        if (S16(st.U16(G, 0x59e)) > 0) return 0;
        return st.U8(G, 0x7c2) & 3;
    }

    /// <summary>f_69daf: follow the human (barking at the mower).</summary>
    static int DogChase(State st)
    {
        int dr = S16(st.U16(G, 0x59e) - st.U16(G, 0x23e));
        int dc = S16(st.U16(G, 0x510) - st.U16(G, 0x246));
        if (Math.Abs(dc) < 1 && Math.Abs(dr) < 1 && st.U16(G, 0x202) != 0) Bark(st, 1, 0x7f);
        if (Math.Abs(dc) >= 2 || Math.Abs(dr) >= 2)
        {
            if (dr < 0) return 2;
            if (dr > 1) return 0;
            if (dc < 0) return 1;
            if (dc > 1) return 3;
        }
        return st.U8(G, 0x7c2) & 3;
    }

    /// <summary>f_69ba3: the dog (heading G:0506: 0..3 walking, 4/5 sitting; x G:04BE, y G:04C6, sprite G:04E4,
    /// patch G:0510 / G:059E, turn timer G:0624).</summary>
    public static void Dog(State st)
    {
        st.Inc16(G, 0x624, -1);
        if (S16(st.U16(G, 0x624)) < 0)
        {
            int hh;
            if (st.U16(G, 0x254) != 0) hh = DogHome(st);
            else if (S16(st.U16(T, 0xc48)) < 0x26) hh = (st.Rand(3) + st.U8(G, 0x506) - 1) & 3;
            else hh = DogChase(st);
            st.Set16(G, 0x506, hh);
            st.Set16(G, 0x624, 4);
        }
        if (st.U16(G, 0x506) == 1 && st.Rand(10) == 0)
        {
            st.Set16(G, 0x506, st.Rand2() + 4);                             // sits down
            st.Set16(G, 0x624, 6);
        }
        int h = st.U16(G, 0x506);
        if (S16(h) > 3) st.Set16(G, 0x4e4, st.S8(DS, 0x2458 + h) + (st.U8(G, 0x7c2) & 1));
        else st.Set16(G, 0x4e4, st.S8(DS, 0x2458 + h) + st.S8(DS, 0x2454 + (st.U8(G, 0x7c2) & 3)));
        st.Inc16(G, 0x4c6, st.S8(DS, 0x244e + h));
        int y = S16(st.U16(G, 0x4c6));
        int row = CDiv(S16(y - 0x26), 10);
        st.Set16(G, 0x59e, row);
        st.Inc16(G, 0x4be, st.S8(DS, 0x2448 + h));
        st.Set16(G, 0x510, CDiv(S16(st.U16(G, 0x4be) + y - 0xc8), 28));
        if (row < 0) st.Set16(G, 0x59e, 0);
        if (S16(st.U16(G, 0x59e)) > 0xf) st.Set16(G, 0x59e, 0xf);
        if (S16(st.U16(G, 0x510)) < 0) st.Set16(G, 0x510, 0);
        if (S16(st.U16(G, 0x510)) > 0xb) st.Set16(G, 0x510, 0xb);
        if (S16(st.U16(G, 0x59e)) < 1) st.Set16(G, 0x506, 2);
        else if (S16(st.U16(G, 0x59e)) > 0xe) st.Set16(G, 0x506, 0);
        if (S16(st.U16(G, 0x510)) > 0xa) st.Set16(G, 0x506, 3);
        else if (S16(st.U16(G, 0x510)) < 4) st.Set16(G, 0x506, 1);
        int spr = S16(st.U16(G, 0x4e4));
        if (0x64 <= spr && spr <= 0x67 && st.Rand(6) == 0) Bark(st, st.Rand4(), 5);
    }

    // ------------------------------------------------------------------------------------------- rain
    /// <summary>f_685ac (yard only): start rain now and then (G:0352, length G:0356), stop it when it runs out.</summary>
    public static void RainControl(State st)
    {
        if (st.U16(G, 0xf24) == 1) return;
        if (st.U16(G, 0x352) == 0)
        {
            if (st.U16(G, 0xb20) == 0xa8 || (st.CrtRandMod(0x20) == 0 && st.CrtRandMod(0x80) == 0))
            {
                st.Set16(G, 0x352, 1);
                st.Set16(G, 0x356, st.Rand(150) + 150);
                for (int i = 0; i < 100; i++) World.DropObjectRandom(st, i);   // f_0c4ba
                HumanSound(st, 0);
            }
            return;
        }
        if (S16(st.U16(G, 0x356)) > 0) st.Inc16(G, 0x356, -1);
        if (S16(st.U16(G, 0x356)) < 1) st.Set16(G, 0x352, 0);
    }

    // ------------------------------------------------------------------------------------------- yard colonies
    public const int BLACK_PATCH = 0xa4, RED_PATCH = 0x164;

    static void DecayFlown(State st, int flown, int @new)
    {
        int c = S16(st.U16(G, flown));
        if (c > 0) c = c >= 4 ? c - (c >> 2) : c - 1;
        c = Math.Max(c, S16(st.U16(G, @new)));
        st.Set16(G, flown, Math.Min(c, 50));
    }

    /// <summary>f_6a6b4: +3 per black, -3 per red colony among the neighbours (offsets read as unsigned bytes,
    /// so only (1, 0), (0, 1) and the patch itself, twice, count).</summary>
    static int NeighbourBias(State st, int col, int row)
    {
        int adj = 0;
        for (int d = 0; d < 6; d++)
        {
            int c = col + st.U8(DS, 0x26ba + d);
            int r = row + st.U8(DS, 0x26c0 + d);
            if ((c & 0x8000) != 0 || r < 0 || c >= 0xc || r >= 0x10) continue;
            if (st.U8(T, BLACK_PATCH + c * 16 + r) != 0) adj += 3;
            if (st.U8(T, RED_PATCH + c * 16 + r) != 0) adj -= 3;
        }
        return adj;
    }

    /// <summary>f_6a721: a colony founded near (col, row); nothing if the spot is the patch itself.</summary>
    public static void NewColony(State st, int col, int row, bool red)
    {
        int Off()                                                         // f_00984
        {
            int m = st.RandLow(4);
            return st.Rand2() != 0 ? -m : m;
        }
        int c = Math.Min(Math.Max(Off() + col, 0), 0xb);
        int r = Math.Min(Math.Max(Off() + row, 0), 0xf);
        if (c == col && r == row) return;
        int a = (red ? RED_PATCH : BLACK_PATCH) + c * 16 + r;
        int v = st.U8(T, a);
        if (v == 0) st.Inc16(G, red ? 0xac4 : 0xa90);
        st.Set8(T, a, v + 1);
    }

    /// <summary>f_6a1f4, every 32 yard ticks: the colonies of the other patches grow or shrink with their
    /// neighbours and found new ones; the player's colonies' new queens settle nearby; the Full Game's end.</summary>
    public static void YardColonies(State st)
    {
        if ((st.U8(G, 0x7c2) & 0x1f) != 0) return;
        st.Set16(T, 0xc20, 1);
        DecayFlown(st, 0x6aa, 0x7c8);
        DecayFlown(st, 0x73a, 0x850);
        st.Set16(G, 0x3e2, 0);
        st.Set16(G, 0x400, 0);
        st.Set16(G, 0x478, 0);
        if (S16(st.U16(G, 0x330)) > 0) st.Set16(G, 0x3e2, 1);
        if (S16(st.U16(G, 0x350)) > 0) st.Set16(G, 0x400, 1);
        int pcol = st.U16(G, 0x7ca), prow = st.U16(G, 0x7cc);
        int here = (pcol * 16 + prow) & 0xffff;
        st.Set8(T, BLACK_PATCH + here, Math.Min(st.U16(G, 0x330) & 0x3ff, 0xfa));
        st.Set8(T, RED_PATCH + here, Math.Min(st.U16(G, 0x350) & 0x3ff, 0xfa));
        bool full = st.U16(G, 0xeac) == 2;
        int col = 0;
        while (col < 12)
        {
            int row = 0;
            while (row < 16)
            {
                if (col == pcol && row == prow)
                {
                    row++;
                    continue;
                }
                int idx = col * 16 + row;
                int red = st.U8(T, RED_PATCH + idx);
                int black = st.U8(T, BLACK_PATCH + idx);
                if (black == 0 && red == 0)
                {
                    row++;
                    continue;
                }
                if (full && (col < 2 || (col == 3 && row < 5))) st.Inc16(G, 0x478);   // colonies near the house
                int adj = NeighbourBias(st, col, row);
                if (black != 0)
                {
                    st.Inc16(G, 0x3e2);
                    black += adj != 0 ? adj : 1;
                    if (black <= 0)
                    {
                        st.Inc16(G, 0xa9e);
                        st.Set8(T, BLACK_PATCH + idx, 0);
                    }
                    else if (black < 0xfa) st.Set8(T, BLACK_PATCH + idx, black);
                    else
                    {
                        st.Set8(T, BLACK_PATCH + idx, 0xfa);
                        if (st.Rand(10) == 0) NewColony(st, col, row, false);
                    }
                }
                if (red != 0)
                {
                    st.Inc16(G, 0x400);
                    red = adj != 0 ? red - adj : red + 1;
                    if (red <= 0)
                    {
                        st.Inc16(G, 0xac8);
                        st.Set8(T, RED_PATCH + idx, 0);
                        if (col == 0xb)
                        {
                            row = 8;
                            st.Set8(T, 0x184 + st.Rand(6) * 16, 0x14);
                        }
                    }
                    else if (red < 0xfa) st.Set8(T, RED_PATCH + idx, red);
                    else
                    {
                        st.Set8(T, RED_PATCH + idx, 0xfa);
                        if (st.Rand(10) == 0) NewColony(st, col, row, true);
                    }
                }
                row++;
            }
            col++;
        }
        if (st.U16(T, 0x2c0) == 1)
        {
            st.Inc16(G, 0x105c);
            if (st.Rand8() + 10 < S16(st.U16(G, 0x105c)))
            {
                st.Set16(G, 0x105c, 0);
                while (S16(st.U16(G, 0x7c8)) > 0)                           // the black queens settle nearby
                {
                    NewColony(st, S16(st.U16(G, 0x7ca)), S16(st.U16(G, 0x7cc)), false);
                    st.Inc16(G, 0x7c8, -1);
                }
            }
        }
        st.Inc16(G, 0x1066);
        if (st.Rand8() + 10 < S16(st.U16(G, 0x1066)))
        {
            st.Set16(G, 0x1066, 0);
            while (S16(st.U16(G, 0x850)) > 0)
            {
                NewColony(st, S16(st.U16(G, 0x7ca)), S16(st.U16(G, 0x7cc)), true);
                st.Inc16(G, 0x850, -1);
            }
        }
        if (!full) return;
        if (st.U16(G, 0x400) == 0 && st.U16(G, 0x36e) != 0)
        {
            st.Hooks.Effect(st, "music", 0x4e22);
            st.Hooks.Effect(st, "message", 0x2744);                       // the reds are gone from the yard
            if (st.U16(T, 0xc44) == 0) st.Hooks.Effect(st, "message", 0x2747);
        }
        st.Set16(G, 0x364, st.U16(G, 0x3e2));
        st.Set16(G, 0x36e, st.U16(G, 0x400));
        if (st.U16(T, 0xc44) == 0 && S16(st.U16(G, 0x478)) > 0x18)        // the human moves in
        {
            st.Set16(T, 0xc44, 1);
            st.Set16(T, 0xc48, 0);
            st.Set16(T, 0xc28, 0);
            st.Set16(T, 0xc32, 0xffff);
            st.Hooks.Effect(st, "music", 0x4e23);
            st.Hooks.Effect(st, "message", 0x2746);
            if (st.U16(G, 0x400) != 0) st.Hooks.Effect(st, "message", 0x2745);
        }
        if (st.U16(T, 0xc44) != 0 && st.U16(G, 0x400) == 0)              // won the Full Game
        {
            st.Hooks.Effect(st, "music", 0x4e25);
            st.Hooks.Effect(st, "message", 0x2749);
            st.Set16(G, 0x376, 1);
            st.Set16(G, 0x366, 1);
            st.Hooks.WinScreen(st);
            return;
        }
        if (S16(st.U16(G, 0x3e2)) < 2 && st.U16(G, 0xaf6) == 0 && st.U16(G, 0xaec) == 0
            && st.U16(G, 0xaf2) == 0 && st.U16(G, 0xaf4) == 0)
        {
            st.Set16(G, 0x376, 1);                                          // lost the Full Game
            st.Set16(G, 0x366, 0);
            st.Hooks.Effect(st, "message", 0x2748);
        }
    }
}
