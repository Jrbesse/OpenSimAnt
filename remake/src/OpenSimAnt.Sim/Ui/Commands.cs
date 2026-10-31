using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;

namespace OpenSimAnt.Sim;

/// <summary>The yellow ant's menu commands (f_76cb9, via f_2f906 from the pop-up menu f_67e93): recruit,
/// release, exchange, alarm, dig a hole, start brood, and the spider's chase / hunt. See SIM_NOTES "The yellow
/// ant's menu and commands". Screen-only effects: 'sound' (f_00ed8), 'voice' (f_00ea1), 'help' (f_76eb5),
/// 'pause' (f_2f816, the pick-a-target cursor mode), 'anim_timer' (f_0125f).</summary>
public static class Commands
{
    /// <summary>The menus' command tables (DS:23D0 / DS:23D4 / DS:23DA).</summary>
    public static readonly int[] QUEEN_MENU = { 8, 9, 0 };              // Dig Hole, Start Brood, Help
    public static readonly int[] ANT_MENU = { 1, 2, 4, 5, 6, 0 };       // Recruit 5, Recruit 10 (Shift: 3), Release 1/2, Release All, Exchange, Help
    public static readonly int[] SPIDER_MENU = { 0xa, 0xb, 6, 0 };      // Chase, Hunt (Alt: 0xC), Exchange, Help

    /// <summary>f_13f32: up to n black workers / soldiers (castes 2 and 6) join the yellow ant (state 6),
    /// surface ants from the last down first, then the black nest's.</summary>
    public static void Recruit(State st, int n)
    {
        foreach (var (count, typ, state, e) in new[] { (0xd6a, 0xad3b, 0xa952, 0xb124), (0xda8, 0xbaec, 0xb8f7, 0xbce1) })
        {
            int i = S16(st.U16(G, count));
            while (i > 0 && n > 0)
            {
                i--;
                int t = st.U8(SIM, typ + i);
                int c = (t & 0x78) >> 3;
                if (t == 0 || (t & 0x80) != 0 || (c != 2 && c != 6)) continue;
                if (st.U8(SIM, state + i) == 6) continue;
                st.Set8(SIM, state + i, 6);
                st.Set8(SIM, e + i, 0);
                n--;
            }
        }
    }

    /// <summary>f_11b21 (Exchange, 0x0A) / f_11ac1 (Chase, 0x0B): toggle the pick-a-target cursor mode G:105E.</summary>
    static void TargetMode(State st, int mode)
    {
        if (st.U16(G, 0x105e) == mode)
        {
            CancelTargetMode(st);
            return;
        }
        st.Set16(G, 0x48e, st.U16(G, 0x47e));
        st.Set16(G, 0x105e, mode);
        st.Hooks.Effect(st, "pause", 1);
    }

    /// <summary>f_11b5f / f_11aff.</summary>
    public static void CancelTargetMode(State st)
    {
        st.Set16(G, 0x105e, 0xffff);
        st.Hooks.Effect(st, "pause", st.U16(G, 0x48e));
    }

    /// <summary>f_76cb9: one menu command (ignored while the player is not an ant or the spider, G:0A06 > 1).</summary>
    public static void Command(State st, int cmd)
    {
        if (S16(st.U16(G, 0xa06)) > 1 || !(0 <= cmd && cmd <= 0xc)) return;
        var fx = st.Hooks;
        switch (cmd)
        {
            case 0: fx.Effect(st, "help"); break;
            case 1: case 2: case 3:
                fx.Effect(st, "voice", 0x2b04 + cmd);
                Recruit(st, new[] { 5, 10, 1000 }[cmd - 1]);
                break;
            case 4: case 5:
                fx.Effect(st, "voice", 0x2b04 + cmd);
                Player.ReleaseRecruits(st, cmd - 4);
                break;
            case 6: TargetMode(st, 0xa); break;
            case 7: Player.AlarmMode(st, st.U16(G, 0x104e) == 0 ? 1 : 0, 0); break;
            case 8:
            {
                int view = st.U16(G, 0x48c);
                if (view == 1 && Player.ActOnCell(st, view, S16(st.U16(G, 0x47c)), S16(st.U16(G, 0x48a))) != -1) return;
                fx.Effect(st, "sound", 1);
                break;
            }
            case 9:
                if (st.U16(G, 0x48c) == 2 && S16(st.U16(G, 0x48a)) >= 3)
                {
                    fx.Effect(st, "anim_timer", 6);
                    int h = st.U16(G, 0x496) ^ 4;
                    int a = S16(st.U16(G, 0x47c)) + 2 * st.S8(T, h);
                    int b = S16(st.U16(G, 0x48a)) + 2 * st.S8(T, 8 + h);
                    Player.QueenScene(st, st.U16(G, 0x48c), a, b, 0x10, 1);
                }
                else
                    fx.Effect(st, "sound", 1);
                break;
            case 0xa: TargetMode(st, 0xb); break;
            case 0xb:
                if (st.U16(G, 0x6ac) == 7)
                {
                    st.Set16(G, 0x6ac, 0);
                    fx.Effect(st, "sound", 2, 0x56ee);
                }
                else
                {
                    st.Set16(G, 0x6ac, 7);
                    fx.Effect(st, "sound", 2, 0x2b77);
                }
                break;
            case 0xc:
                if (st.U16(G, 0x6ac) == 8)
                {
                    st.Set16(G, 0x6ac, 0);
                    fx.Effect(st, "sound", 2, 0x56ee);
                }
                else
                {
                    st.Set16(G, 0x6ac, 8);
                    fx.Effect(st, "sound", 0x29);
                }
                break;
        }
    }

    static bool Cheat(State st)
    {
        int k = st.BiosKbd & 0xff;
        return (k & 3) != 0 && (k & 8) != 0;
    }

    /// <summary>The caste the yellow ant leaves behind as a plain ant, and its e: castes 5 / 9 through the load
    /// table T:0094; caste 1 (bit 3 set) keeps its e in T:0C22.</summary>
    static (int c, int e) YellowCaste(State st)
    {
        int t = st.U16(G, 0x4c2);
        int c = (t & 0x78) >> 3, e = 0;
        if ((t & 8) != 0)
        {
            if (c == 5 || c == 9) c = st.S8(T, 0x94 + c);
            else if (c == 1) e = st.U16(T, 0xc22);
        }
        return (c, e);
    }

    /// <summary>The clicked ant o (index i) as the new yellow ant's occupant byte, null if refused: brood, the
    /// queen's second cell's caste 13 and castes 10 / 11 (or no ant) only with the cheat keys and T:0798; castes
    /// 5 / 9 through T:0094; caste 1 hands its e to T:0C22.</summary>
    static int? NewYellow(State st, int view, int i, int o)
    {
        int c = (o & 0x78) >> 3;
        if (c <= 0 || c > 13 || c == 10 || c == 11)
            if (!(Cheat(st) && st.U16(T, 0x798) != 0)) return null;
        if (c == 5 || c == 9) o = ((st.S8(T, 0x94 + c) << 3) | (o & 7)) & 0xffff;
        else if (c == 1) st.Set16(T, 0xc22, Player.GetAnt(st, view, i).Value.e);       // f_10fcd
        return o;
    }

    /// <summary>f_114bd at the yellow ant's position (and the queen's second cell behind her): 0 if no room.</summary>
    static int AddYellowAnt(State st, int t, int q, int e)
    {
        int view = S16(st.U16(G, 0x48c)), ya = S16(st.U16(G, 0x47c)), yb = S16(st.U16(G, 0x48a));
        if (Player.AddAnt(st, view, ya, yb, t, q, e) == 0) return 0;
        if (st.U16(G, 0x4c2) == 0x60)
        {
            int h = st.U16(G, 0x496) ^ 4;
            if (Player.AddAnt(st, view, ya + st.S8(T, h), yb + st.S8(T, 8 + h), (t + 8) & 0xffff, q, 0) == 0) return 0;
        }
        return 1;
    }

    /// <summary>f_11c18: the player becomes the ant at (view, a, b), 1 if done (also a click on itself), 0 if not.
    /// An empty surface cell within squared distance 0x200 of the spider: the player becomes the spider (the
    /// yellow ant stays behind as a plain ant). An ant: it leaves its list (a queen with her second cell) and
    /// the yellow ant takes its place and type; red ants, brood and the odd castes need the cheat keys (Shift +
    /// Alt) and T:0798. As the yellow ant (G:0A06 == 0), the old yellow ant is added back as a plain ant.</summary>
    public static int Exchange(State st, int view, int a, int b)
    {
        var fx = st.Hooks;
        int o = Player.GetOcc(st, view, a, b) & 0xffff;
        if (S16(o) <= 0)
        {
            if (view != 1) return 0;
            if (Colony.Distance(a * 16 + 8, b * 16 + 8, S16(st.U16(G, 0xf12)), S16(st.U16(G, 0xf34))) >= 0x200) return 0;
            var (c0, e0) = YellowCaste(st);
            int t0 = ((st.U16(G, 0x4e2) & 0x80) | st.U16(G, 0x496) | (c0 << 3)) & 0xffff;
            int q0 = st.U16(G, 0x4c2) == 0x60 ? 9 : 0;
            if (AddYellowAnt(st, t0, q0, e0) == 0) return 0;
            Player.PutYellow(st, S16(st.U16(G, 0x48c)), S16(st.U16(G, 0x47c)), S16(st.U16(G, 0x48a)), st.U16(G, 0x4c2), st.U16(G, 0x496), 0);
            st.Set16(G, 0xffc, 0xfffe);
            int sa = S16(st.U16(G, 0xf12)) >> 4, sb = S16(st.U16(G, 0xf34)) >> 4;
            st.Set16(G, 0xf42, sa & 0xffff);
            st.Set16(G, 0xf7e, sb & 0xffff);
            st.Set16(G, 0xa06, 1);
            foreach (int off in new[] { 0xfb8, 0x6ac, 0x4e2 }) st.Set16(G, off, 0);
            Player.StopAction(st, view, sa, sb);                              // f_2f820
            Player.SetHealth(st, 100);
            return 1;
        }
        if (DebugCommands.PlayerAt(st, view, a, b) != 0 || Movement.IsYellow(o)) return 1;
        int c = (o & 0x78) >> 3;
        int a2 = 0, b2 = 0, o2 = 0, i2 = -1;
        if (c == 0xc)                                                        // a queen: her second cell behind her
        {
            int h = (o & 7) ^ 4;
            a2 = a + st.S8(T, h);
            b2 = b + st.S8(T, 8 + h);
            o2 = Player.GetOcc(st, view, a2, b2) & 0xffff;
        }
        else if (c == 0xd)                                                   // her second cell: the queen ahead
        {
            a2 = a;
            b2 = b;
            o2 = o;
            a += st.S8(T, o & 7);
            b += st.S8(T, 8 + (o & 7));
            o = Player.GetOcc(st, view, a, b) & 0xffff;
            c = 0xc;
        }
        int i = Player.FindAntExact(st, view, a, b, o);                      // f_11327
        if (c == 0xc) i2 = Player.FindAntExact(st, view, a2, b2, o2);
        if (i < 0) return 0;
        if (st.U16(G, 0xa06) == 0)
        {
            var (yc, e) = YellowCaste(st);
            int t = ((yc << 3) | st.U16(G, 0x496) | (o & 0x80)) & 0xffff;
            if ((o & 0x80) != 0 && !Cheat(st)) return 0;
            var no = NewYellow(st, view, i, o);
            if (no == null) return 0;
            o = no.Value;
            int q = st.U16(G, 0x4c2) == 0x60 ? 9 : 0;
            int view0 = S16(st.U16(G, 0x48c)), ya = S16(st.U16(G, 0x47c)), yb = S16(st.U16(G, 0x48a));
            fx.Effect(st, "redraw", view0, ya, yb);                         // f_0250e
            if (q != 0)
            {
                int h = st.U16(G, 0x496) ^ 4;
                fx.Effect(st, "redraw", view0, ya + st.S8(T, h), yb + st.S8(T, 8 + h));
            }
            fx.Effect(st, "redraw", view, a, b);
            if (c == 0xc) fx.Effect(st, "redraw", view, a2, b2);
            Player.SetAnt(st, view, i, 0, 0, 0, 0, 0);
            if (c == 0xc) Player.SetAnt(st, view, i2, 0, 0, 0, 0, 0);
            if (AddYellowAnt(st, t, q, e) == 0) return 0;
        }
        else
        {
            if ((o & 0x80) != 0 && !Cheat(st)) return 0;
            var no = NewYellow(st, view, i, o);
            if (no == null) return 0;
            o = no.Value;
            Player.SetAnt(st, view, i, 0, 0, 0, 0, 0);
            if (c == 0xc) Player.SetAnt(st, view, i2, 0, 0, 0, 0, 0);
        }
        st.Set16(G, 0x4e2, o & 0x80);
        foreach (int off in new[] { 0x49a, 0xa06, 0x6ac }) st.Set16(G, off, 0);
        Player.SetHealth(st, 100);
        Player.PutYellow(st, view, a, b, o & 0x78, o & 7, 0xff);
        if (S16(st.U16(G, 0x4c2)) < 8) st.Set16(G, 0x502, st.U16(G, 0x496));
        return 1;
    }

    /// <summary>f_11b81: a map click in the Exchange cursor mode (G:105E == 0x0A): G:1074 = 1, then the swap.
    /// Done: the mode ends with sound 0x0F (as a queen also a redraw, f_03391, and a voice line); refused: sound 1.</summary>
    public static void ExchangeClick(State st, int view, int a, int b)
    {
        st.Set16(G, 0x1074, 1);
        var fx = st.Hooks;
        if (Exchange(st, view, a, b) == 1)
        {
            CancelTargetMode(st);
            fx.Effect(st, "sound", 0xf);
            if (st.U16(G, 0x4c2) == 0x60)
            {
                fx.Effect(st, "redraw_view");                                // f_03391; f_00f1d is always 1
                fx.Effect(st, "voice", 0x2afe);
            }
        }
        else
            fx.Effect(st, "sound", 1);
    }

    static void SpiderWalk(State st, int a, int b, int k)
    {
        st.Set16(G, 0xffc, 0xfffe);
        st.Set16(G, 0x10ae, 0xffff);
        st.Set16(G, 0xfb8, 0);
        st.Set16(G, 0xf42, a & 0xffff);
        st.Set16(G, 0xf7e, b & 0xffff);
        st.Set16(G, 0xa8e, k & 0xffff);
    }

    /// <summary>f_756a6: a map click while the player is the spider (from f_74fe0; in the Chase cursor mode
    /// G:105E == 0x0B, or with k >= 1): an ant on the cell becomes its prey (G:10AE its type, G:0FFC its index,
    /// state G:0FB8 = 2; in Chase mode also sound 0x0F, G:06AC = 6 and the mode ends); otherwise it walks there
    /// (G:0F42 / G:0F7E, G:0A8E = k), or in Chase mode just sound 1.</summary>
    public static void SpiderClick(State st, int a, int b, int k)
    {
        bool chase = st.U16(G, 0x105e) == 0xb;
        if (S16(k) < 1 && !chase)
        {
            SpiderWalk(st, a, b, k);
            return;
        }
        int o = st.Grid(0x6180, a, b);
        int i = o != 0 ? Player.FindAntExact(st, 1, a, b, o) : -1;
        if (i >= 0)
        {
            st.Set16(G, 0x10ae, o);
            st.Set16(G, 0xffc, i & 0xffff);
            st.Set16(G, 0xfb8, 2);
            if (chase)
            {
                st.Hooks.Effect(st, "sound", 0xf);
                st.Set16(G, 0x6ac, 6);
                CancelTargetMode(st);
            }
            return;
        }
        if (chase)
        {
            st.Hooks.Effect(st, "sound", 1);
            return;
        }
        SpiderWalk(st, a, b, k);
    }
}
