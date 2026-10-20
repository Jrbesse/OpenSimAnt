using static Formica.Sim.Seg;
using static Formica.Sim.Bits;
using Co = Formica.Sim.Colony;
using Mv = Formica.Sim.Movement;
using Ng = Formica.Sim.NestGrid;
using Ph = Formica.Sim.Pheromones;

namespace Formica.Sim;

public static partial class Player
{
    static int Hp(State st) => S16(st.U16(G, 0xf78));

    // ------------------------------------------------------------------------------------------- nests and fights
    /// <summary>f_76a37 (via f_2f80c): the yellow ant lays alarm scent as it walks (G:104E; surface only).</summary>
    public static void AlarmMode(State st, int on, int quiet)
    {
        if (on != 0)
        {
            if (G16(st, 0x48c) == 1 && st.U16(G, 0xa06) == 0)
            {
                st.Set16(T, 0x7be, 0);
                st.Hooks.Effect(st, "menu_check", 0x10, on);                 // f_22f65
                st.Set16(G, 0x104e, 1);
                if (quiet == 0) st.Hooks.Effect(st, "sound", 0xf);
            }
            else if (quiet == 0)
                st.Hooks.Effect(st, "sound", 1);
        }
        else
        {
            st.Set16(G, 0x104e, 0);
            st.Hooks.Effect(st, "menu_check", 0x10, on);
            st.Set16(T, 0x7be, 0xffff);
            if (quiet == 0) st.Hooks.Effect(st, "sound", 0xf);
        }
        st.Hooks.Effect(st, "redraw_rect");                                  // f_0256e
    }

    /// <summary>f_7c7e5 (also via f_2f834): from a surface entrance into the top of nest column b (the black
    /// nest on the left half of the patch, the red one on the right); alarm-trail mode ends.</summary>
    public static void EnterNest(State st)
    {
        Jingle(st);
        if (st.U16(G, 0x104e) != 0) AlarmMode(st, 0, 1);
        int view = G16(st, 0x48c), a = G16(st, 0x47c), b = G16(st, 0x48a);
        int t = G16(st, 0x4c2), h = st.U16(G, 0x496);
        TakeYellow(st, view, a, b, t, h);
        st.Set16(G, 0x48c, a > 0x40 ? 3 : 2);
        st.Set16(G, 0x47c, b);
        st.Set16(G, 0x48a, t == 0x60 ? 2 : 1);
        st.Set16(G, 0x496, 4);
        view = G16(st, 0x48c);
        a = G16(st, 0x47c);
        b = G16(st, 0x48a);
        DigThrough(st, view, a, b);
        PutYellow(st, view, a, b, t, 4, 0xff);
    }

    /// <summary>f_7c8fe: climb out of the nest's entrance (opening one if there is none) onto a free cell next
    /// to it (2 cells for a queen), facing the cursor if it is on the surface.</summary>
    public static void LeaveNest(State st)
    {
        Jingle(st);
        int view = G16(st, 0x48c), a = G16(st, 0x47c), b = G16(st, 0x48a);
        int t = G16(st, 0x4c2);
        PutYellow(st, view, a, b, t, st.U16(G, 0x496), 0);
        int col = st.U8(G, 0x47c) & 0x3f;
        st.Set16(G, 0x48a, col);
        var n = view == 2 ? Nest.BLACK : Nest.RED;
        if (st.U8(T, n.Entr + col) == 0) Nest.MakeSurfaceHole(st, n, G16(st, 0x47c));
        st.Set16(G, 0x47c, st.U8(T, n.Entr + col));
        a = G16(st, 0x47c);
        b = col;
        int k = t == 0x60 ? 2 : 1;
        int tv = G16(st, 0xaf8);
        int @base;
        if (tv == 1)
        {
            int d0 = Mv.DirTo(a, b, G16(st, 0xad6), G16(st, 0xae8));
            @base = d0 > 0 ? d0 - 1 : d0;
        }
        else if (tv == view)
            @base = a < 0x40 ? 2 : 6;
        else
        {
            @base = StepToCursor(st, 1, a, b, tv, G16(st, 0xad6), G16(st, 0xae8));
            if (@base < 0) @base = st.Rand8();
        }
        bool found = false;
        for (int i = 0; i < 8; i++)
        {
            int d = (st.S8(T, 0x6c + i) + @base) & 7;
            int x = a + st.S8(T, d) * k, y = b + st.S8(T, 8 + d) * k;
            if (CanDrop(st, 1, x, y))
            {
                st.Set16(G, 0x47c, x);
                st.Set16(G, 0x48a, y);
                st.Set16(G, 0x496, d);
                found = true;
                break;
            }
        }
        if (!found)
        {
            st.Set16(G, 0x496, @base);
            st.Set16(G, 0x47c, (st.U8(G, 0x47c) + k) & 0x7f);
        }
        st.Set16(G, 0x48c, 1);
        PutYellow(st, 1, G16(st, 0x47c), G16(st, 0x48a), t, st.U16(G, 0x496), 0xff);
    }

    /// <summary>f_23612(0): the game window is the active one (DS:5702 == 0) → long animations.</summary>
    static bool AnimFrames(State st) => st.U16(0x55b3, 0x5702) == 0;

    /// <summary>f_00f28: the last sound has finished (always, without sound hardware DS:1926 or with sound off).</summary>
    public static bool SoundDone(State st)
    {
        if (st.U16(0x55b3, 0x1926) == 0 || st.U16(T, 0x7aa) == 0) return true;
        return st.Hooks.SoundDone(st);
    }

    /// <summary>f_7c149: the yellow ant flashes as type t with random headings, then is lifted off the map with
    /// its state restored. Mode 0 (a fight, 6 frames, type 0x70 cloud) or a player event (1 eaten by the spider,
    /// 2 by an ant lion: the pit opens under it; 10 squashed: the ground flickers): 8 frames, 0x20 / 0x40
    /// (sound on) when the game window is active, events 1..9 stop early once their sound has finished.
    /// The original waits on the clock between frames (screen only).</summary>
    public static void FightAnimation(State st, int view, int a, int b, int heading, int t, int mode)
    {
        st.Hooks.Effect(st, "anim_begin");                                 // the frames are drawn by the UI
        PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x4c2), st.U16(G, 0x496), 0xff);
        int[] saved = { view, a, b, st.U16(G, 0x4c2) };
        int n;
        if (mode == 0) n = 6;
        else if (AnimFrames(st)) n = st.U16(T, 0x7aa) != 0 ? 0x40 : 0x20;
        else n = 8;
        int under = 0;
        if (mode == 10)
        {
            under = st.Grid(SURFACE, a, b);
            n = 0x20;
        }
        int k = 3;
        for (int f = 0; f < n; f++)
        {
            if (mode == 0 && st.Rand2() != 0) st.Hooks.Effect(st, "sound", 0x25);
            if (mode == 10)
            {
                st.Hooks.Effect(st, "sound", 0x31);
                st.SetGrid(SURFACE, a, b, st.Rand2() != 0 ? under - 3 : under);
            }
            if (0 < mode && mode < 10 && st.U16(T, 0x7aa) != 0 && SoundDone(st)) break;
            if (mode == 2)
            {
                SetTile(st, view, a, b, k + 0x38);                         // the pit's frames
                if (k < 5) k++;
                else if (k > 3) k--;
            }
            MoveYellow(st, view, a, b, t, st.Rand8());
            st.Hooks.Effect(st, "anim_frame");                             // f_03391, then 6 clock3 units
        }
        st.Hooks.Effect(st, "anim_end");
        if (mode == 10) st.SetGrid(SURFACE, a, b, under);
        TakeYellow(st, view, a, b, t, st.U16(G, 0x496));
        int[] offs = { 0x48c, 0x47c, 0x48a, 0x4c2 };
        for (int i = 0; i < 4; i++) st.Set16(G, offs[i], saved[i]);
        st.Set16(G, 0x496, heading);
    }

    /// <summary>f_7a69d: the heading of the neighbour that gets closest to (ta, tb), preferring free open
    /// ground; -1 if already there, -2 if no neighbour is closer.</summary>
    public static int PathDir(State st, int view, int a, int b, int ta, int tb)
    {
        int dist = Dist(a, b, ta, tb);
        if (dist <= 0) return -1;
        int best = -1, fallback = -2;
        for (int d = 0; d < 8; d++)
        {
            int na = a + st.S8(T, d), nb = b + st.S8(T, 8 + d);
            int t = GetTile(st, view, na, nb);
            if (!CanDrop(st, view, na, nb) || IsRock(view, t)) continue;
            int nd = Dist(na, nb, ta, tb);
            if (nd >= dist) continue;
            if (GetOcc(st, view, na, nb) <= 0 && IsOpenGround(st, view, na, nb)) best = d;
            else fallback = d;
            dist = nd;
        }
        return best >= 0 ? best : fallback;
    }

    /// <summary>f_7c3b1 (AnimYellowInsane, events 7..9): the yellow ant (as type t) staggers around its spot:
    /// back there is a random target within 3 cells (C runtime rand), then it heads home; 8 frames, 0x20 when
    /// the game window is active. Its state is restored afterwards.</summary>
    public static void InsaneAnimation(State st, int view, int a, int b, int heading, int t)
    {
        st.Hooks.Effect(st, "anim_begin");
        PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x4c2), st.U16(G, 0x496), 0xff);
        int a0 = a, b0 = b, savedT = st.U16(G, 0x4c2);
        int n = AnimFrames(st) ? 0x20 : 8;
        for (int i = 0; i < n; i++)
        {
            int ta, tb;
            if ((Co.Distance(a, b, a0, b0) & 0xffff) == 0 && n - i - 1 != 0)
            {
                tb = st.CrtRandMod(7) + b - 3;
                ta = st.CrtRandMod(7) + a - 3;
            }
            else
            {
                ta = a0;
                tb = b0;
            }
            int d = PathDir(st, view, a, b, ta, tb);
            if (d >= 0)
            {
                a += st.S8(T, d);
                b += st.S8(T, 8 + d);
            }
            else
                d = st.Rand8();
            MoveYellow(st, view, a, b, t, d);
            st.Hooks.Effect(st, "anim_frame");
        }
        st.Hooks.Effect(st, "anim_end");
        TakeYellow(st, view, a, b, t, st.U16(G, 0x496));
        st.Set16(G, 0x48c, view);
        st.Set16(G, 0x47c, a0);
        st.Set16(G, 0x48a, b0);
        st.Set16(G, 0x4c2, savedT);
        st.Set16(G, 0x496, heading);
    }

    /// <summary>f_14005: let recruited ants (state 6) go: half the census count G:0D4C, or it + 100; surface
    /// and black nest ants of the black colony return to state 0, black invaders in the red nest to 7.</summary>
    public static void ReleaseRecruits(State st, int more)
    {
        int n = G16(st, 0xd4c);
        n = more != 0 ? n + 100 : n / 2;
        foreach (var (count, tf, sf, nw) in new[] { (0xd6a, 0xad3b, 0xa952, 0), (0xda8, 0xbaec, 0xb8f7, 0), (0xeaa, 0xc4b5, 0xc2c0, 7) })
        {
            int i = S16(st.U16(G, count));
            while (i > 0 && n > 0)
            {
                i--;
                int t = st.U8(SIM, tf + i);
                if (t != 0 && (t & 0x80) == 0 && st.U8(SIM, sf + i) == 6)
                {
                    st.Set8(SIM, sf + i, nw);
                    n--;
                }
            }
        }
    }

    /// <summary>f_758e0: the yellow ant becomes the queen. found == 0 (the old one died, f_75d01): she comes out
    /// of her cocoon (G:0502 frames 1..7) as type t. found != 0 (f_76cb9): the yellow queen at (a, b) founds a
    /// nest there: a queen chamber (f_6ba1c / f_6bb70) and one more adult. The waits are screen only.</summary>
    public static void QueenScene(State st, int view, int a, int b, int t, int found)
    {
        int saved7ac = st.U16(T, 0x7ac), oldT = st.U16(G, 0x4c2);
        st.Set16(T, 0x7ac, 0);
        st.Set16(G, 0xa06, 0);
        if (found == 0)
        {
            st.Set16(G, 0x502, 1);
            PutYellow(st, view, a, b, 0, st.U16(G, 0x496), 0xff);
        }
        else
        {
            TakeYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x4c2), st.U16(G, 0x496));
            PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), 0x60, st.U16(G, 0x496), 0xff);
        }
        if (found == 0) UiFollow(st);
        st.Hooks.Effect(st, "redraw_all");                                  // f_11ab0
        if (found != 0)
        {
            st.Hooks.Effect(st, "sound", 0x4e20);
            SetOcc(st, view, a, b, 1);
            st.Hooks.Effect(st, "redraw_all");
        }
        st.Set16(T, 0x7ac, saved7ac);
        st.Hooks.Effect(st, "sound", 0x1c);
        StopAction(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a));
        st.Set16(T, 0xc24, 1);
        SetHealth(st, 100);
        if (found == 0) st.Set16(G, 0x496, oldT == 0x60 ? 2 : 6);
        for (int frame = 2; frame < 8; frame++)
        {
            if (found == 0)
            {
                st.Set16(G, 0x502, frame);
                PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), 0, st.U16(G, 0x496), 0xff);
            }
            else
                SetOcc(st, G16(st, 0x48c), a, b, frame);
            st.Hooks.Effect(st, "redraw");                                 // f_03391
        }
        st.Hooks.Effect(st, "sound", 0x31);
        if (found == 0)
            PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), t, st.U16(G, 0x496), 0xff);
        else
        {
            TakeYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x4c2), st.U16(G, 0x496));
            if (G16(st, 0x48c) == 2)
            {
                NewGame.QueenChamber(st, Nest.BLACK, G16(st, 0x47c), G16(st, 0x48a), st.U16(G, 0x496));   // f_6ba1c
                st.Inc16(G, 0xaf6);
            }
            else
            {
                NewGame.QueenChamber(st, Nest.RED, G16(st, 0x47c), G16(st, 0x48a), st.U16(G, 0x496));     // f_6bb70
                st.Inc16(G, 0xb04);
            }
            PutYellow(st, G16(st, 0x48c), a, b, t, st.U16(G, 0x496) ^ 4, 0xff);
            if (st.U16(G, 0x4e2) == 0)
            {
                st.Inc16(G, 0xaee);
                st.Inc16(G, 0xaf4, -1);
                st.Inc16(G, 0x330);
            }
            else
            {
                st.Inc16(G, 0xafc);
                st.Inc16(G, 0xb02, -1);
                st.Inc16(G, 0x350);
            }
        }
        st.Hooks.Effect(st, "redraw");
        st.Hooks.Effect(st, "sound", found != 0 ? 0x4e21 : 0x2afd);
        st.Hooks.Effect(st, "help", 0x238d, found + 1);                    // f_7686d
    }

    /// <summary>The death messages per event (f_75d01), shown when T:07AE (messages on).</summary>
    public static readonly Dictionary<int, int> EVENT_MESSAGE = new()
    {
        [3] = 0x272a, [4] = 0x272c, [5] = 0x2732, [6] = 0x2734, [7] = 0x2736, [8] = 0x2738, [9] = 0x273a, [10] = 0x273d,
    };

    /// <summary>f_75d01 (via f_2f7d0): the yellow ant dies (n: 0 starved, 1 spider, 2 ant lion, 3..10 other
    /// deaths, see EVENT_MESSAGE) and the player takes over another ant: the black queen if she is gone ...
    /// (types 1..7 in the black nest), else the last adult of the black nest, the surface, the red nest. With
    /// none left: Quick Game over, or in the Full Game the yard map (another colony) or game over.</summary>
    public static void PlayerEvent(State st, int n)
    {
        st.Hooks.Effect(st, "picture", 1);                                 // f_2f802 → f_71a7d
        if (st.U16(G, 0xa06) == 0 && (st.U16(G, 0x4c2) & 8) != 0)          // drop what it carries
        {
            int saved = st.U16(T, 0x7ac);
            st.Set16(T, 0x7ac, 0);
            if (DropLoad(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x47c), G16(st, 0x48a)) == 0)
            {
                int t = st.U16(G, 0x4c2);
                st.Set16(G, 0x4c2, (t & 0x80) | ((st.S8(T, 0x94 + ((t & 0x78) >> 3)) << 3) & 0xffff));
            }
            st.Set16(T, 0x7ac, saved);
        }
        UiFollow(st);
        st.Hooks.Effect(st, "redraw_all");
        if (7 <= n && n < 10) InsaneAnimation(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), st.U16(G, 0x496), st.U16(G, 0x4c2));
        int msg = st.U16(T, 0x7ae);
        if (n == 0)
        {
            st.Hooks.Effect(st, "sound", st.Rand(5) + 0x4e27);
            if (msg != 0) st.Hooks.Effect(st, "message_box", st.U16(G, 0x1058) != 0 ? 0x272e : 0x2730, 1);
        }
        else if (n == 1 || n == 2)
        {
            if (msg != 0)
            {
                if (n == 1) st.Hooks.Effect(st, "message_box", st.Rand(2) != 0 ? 0x2740 : 0x273f, 1);   // f_71f52: the spider scene
                else st.Hooks.Effect(st, "scene", 0x1a00);                  // f_76707: the ant lion scene
            }
            st.Inc32(G, 0xf20);
            st.Hooks.Effect(st, "sound", st.Rand(5) + 0x4e27);
            FightAnimation(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), st.U16(G, 0x496), st.U16(G, 0x4c2), n);
        }
        else if (n == 3 || n == 4)
        {
            st.Hooks.Effect(st, "sound", 1);                                    // f_00ed8(1, 0, 0x7e)
            if (msg != 0) st.Hooks.Effect(st, "message_box", EVENT_MESSAGE[n], 1);
            st.Inc32(G, 0xefc);
        }
        else if (5 <= n && n <= 9)
        {
            st.Hooks.Effect(st, "sound", st.Rand(5) + 0x4e27);
            if (msg != 0) st.Hooks.Effect(st, "message_box", EVENT_MESSAGE[n], 1);
            st.Inc32(G, n == 8 ? 0xf30 : 0xefc);
        }
        else if (n == 10)
        {
            st.Inc32(G, 0xefc);
            FightAnimation(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), st.U16(G, 0x496), st.U16(G, 0x4c2), 10);
            if (msg != 0) st.Hooks.Effect(st, "message_box", EVENT_MESSAGE[n], 1);
        }
        if (1 <= n && n <= 2) st.Hooks.Effect(st, "help", 0x238c, 0);        // f_7686d
        st.Hooks.Effect(st, "redraw_all");                                  // f_0151c
        if (st.U16(G, 0xa06) == 0) TakeYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x4c2), st.U16(G, 0x496));
        ReleaseRecruits(st, 1);
        if (st.U16(G, 0x104e) != 0) AlarmMode(st, 0, 1);
        var found = TakeOver(st);
        if (found == null)
        {
            int mode = G16(st, 0xeac);
            if (mode <= 1)
            {
                st.Set16(G, 0x376, 1);
                st.Set16(G, 0x366, 0);
            }
            else if (mode == 2)
            {
                if (G16(st, 0x3e2) < 2)
                {
                    st.Set16(G, 0x376, 1);
                    st.Set16(G, 0x366, 0);
                    st.Hooks.Effect(st, "message_box", 0x2748, 1);
                }
                else
                {
                    st.Hooks.Effect(st, "message_box", 0x274a, 1);
                    st.Hooks.ChoosePatch(st);                               // f_7650c: the yard map
                }
            }
            else
            {
                // DIVERGENCE: f_75d01 reads an unset local here (no ant left in the experimental mode). The
                // remake makes the player an observer, as mode 3 starts (G:0A06 = 2, see NewGame.PlaceYellow).
                st.Set16(G, 0xa06, 2);
            }
            return;
        }
        if (found.Value.kind == 1)                                         // the queen
        {
            if (st.U16(G, 0x4c2) == 0x60) st.Set16(G, 0x4c2, 0x10);
            QueenScene(st, G16(st, 0x48c), G16(st, 0xf0e), G16(st, 0xf26), G16(st, 0x4c2), 0);
            return;
        }
        st.Set16(G, 0xa06, 0);
        int tt = found.Value.t & 0xf8;
        int h = st.U16(G, 0x496);
        PutYellow(st, G16(st, 0x48c), G16(st, 0xf0e), G16(st, 0xf26), tt, h, tt + h);
        StopAction(st, G16(st, 0x48c), G16(st, 0xf0e), G16(st, 0xf26));
        SetHealth(st, 100);
        UiFollow(st);
        st.Hooks.Effect(st, "redraw_all");
        st.Hooks.Effect(st, "message_box", 0x274b, 1);
    }

    static readonly (int kind, int count, int tf, int xf, int yf, int cells, int view, int lo, int hi)[] TakeOverLists =
    {
        (1, 0xda8, 0xbaec, 0xb50d, 0xb702, 0x8180, 2, 1, 8),
        (2, 0xda8, 0xbaec, 0xb50d, 0xb702, 0x8180, 2, 8, 0x68),
        (2, 0xd6a, 0xad3b, 0xa180, 0xa569, 0x6180, 1, 8, 0x68),
        (2, 0xeaa, 0xc4b5, 0xbed6, 0xc0cb, 0x9180, 3, 8, 0x68),
    };

    /// <summary>Part of f_75d01: pick the ant to become, remove it from its list and map. Returns null, (1, t)
    /// for the black nest's types 1..7, or (2, t) for an adult (types 8..0x67). Each search starts one past the
    /// last ant (sic).</summary>
    static (int kind, int t)? TakeOver(State st)
    {
        foreach (var l in TakeOverLists)
        {
            int i = S16(st.U16(G, l.count));
            while (i >= 0)
            {
                int t = st.U8(SIM, l.tf + i);
                if (l.lo <= t && t < l.hi)
                {
                    int y = st.U8(SIM, l.yf + i), x = st.U8(SIM, l.xf + i);
                    st.Set16(G, 0xf26, y);
                    st.Set8(SIM, l.tf + i, 0);
                    st.Set16(G, 0xf0e, x);
                    st.SetGrid(l.cells, x, y, 0);
                    st.Set16(G, 0x48c, l.view);
                    return (l.kind, t);
                }
                i--;
            }
        }
        return null;
    }

    /// <summary>f_757dd (via f_2f820): the action is over; the cursor rests on the yellow ant.</summary>
    public static void StopAction(State st, int view, int a, int b)
    {
        foreach (int off in new[] { 0x48c, 0xaf8 }) st.Set16(G, off, view);
        foreach (int off in new[] { 0x47c, 0xab6, 0xad6 }) st.Set16(G, off, a);
        foreach (int off in new[] { 0x48a, 0xac6, 0xae8 }) st.Set16(G, off, b);
        foreach (int off in new[] { 0xa8e, 0xaa0, 0xb1e, 0xc38, 0xc3e }) st.Set16(G, off, 0);
        st.Set16(G, 0xd6c, 0xfffe);
    }

    /// <summary>AttackPlayer f_7c5ab: the yellow ant fights ant i of the view's list.</summary>
    public static void AttackPlayer(State st, int view, int i)
    {
        var f = Ants(view);
        int t = st.U8(SIM, f.Type + i);
        int x = st.U8(SIM, f.X + i), y = st.U8(SIM, f.Y + i);
        ClearOccIf(st, view, x, y, t);
        int w = Surface.ResolveFight(st, st.U16(G, 0x4c2), st.U8(SIM, f.Type + i));
        if (st.U16(G, 0x4c2) != w) UiFollow(st);
        int ya = G16(st, 0x47c), yb = G16(st, 0x48a);
        FightAnimation(st, G16(st, 0x48c), ya, yb, st.U16(G, 0x496), 0x70, 0);
        if (st.U16(G, 0x4c2) == w)                                          // the yellow ant wins
        {
            PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), G16(st, 0x4c2), st.U16(G, 0x496), 0xff);
            if (view <= 1) Surface.PlaceCorpse(st, st.U8(SIM, f.X + i), st.U8(SIM, f.Y + i), (st.U8(SIM, f.Type + i) & 0x80) != 0);
            st.Set8(SIM, f.Type + i, 0);
            if (st.U16(G, 0xa8e) == 3 && st.U16(G, 0x48c) == st.U16(G, 0x8da) && st.U16(G, 0x7c0) == (i & 0xffff))
                StopAction(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a));
            return;
        }
        SetOcc(st, view, st.U8(SIM, f.X + i), st.U8(SIM, f.Y + i), st.U8(SIM, f.Type + i));
        if (view <= 1) Surface.PlaceCorpse(st, G16(st, 0x47c), G16(st, 0x48a), st.U16(G, 0x4e2) != 0);
        st.Hooks.GameEvent(st, 0);                                         // the yellow ant dies
    }

    // ------------------------------------------------------------------------------------------- the action
    /// <summary>f_7b7b8 (each tick while an action is pending, G:0AA0): walk one step towards the cursor (or
    /// the target ant), act on the target cell, enter / leave / switch nests; when the action ends: fight or
    /// talk to the target ant, then StopAction.</summary>
    public static void PlayerAction(State st)
    {
        if (st.U16(G, 0xaa0) == 0) return;
        int res = 0;
        int mode = G16(st, 0xa8e);
        (int a, int b, int t, int state, int e)? ant = null;
        bool done = false;
        if (mode >= 3)
        {
            ant = GetAnt(st, G16(st, 0x8da), G16(st, 0x7c0));
            if (ant == null || ((st.U8(G, 0x84e) ^ ant.Value.t) & 0xf0) != 0)
            {
                res = -2;                                                  // the target ant is gone
                done = true;
            }
            else if (G16(st, 0x48c) == G16(st, 0x8da) && Math.Abs(G16(st, 0x47c) - ant.Value.a) <= 1
                     && Math.Abs(G16(st, 0x48a) - ant.Value.b) <= 1)
            {
                int d = Mv.DirTo(G16(st, 0x47c), G16(st, 0x48a), ant.Value.a, ant.Value.b) - 1;   // next to it: face it
                if (d >= 0) st.Set16(G, 0x496, d);
                st.Hooks.Effect(st, "redraw_all");                          // f_03391
                res = -1;
                done = true;
            }
            else                                                           // the cursor follows it
            {
                st.Set16(G, 0x8e2, ant.Value.a);
                st.Set16(G, 0xad6, ant.Value.a);
                st.Set16(G, 0x9f0, ant.Value.b);
                st.Set16(G, 0xae8, ant.Value.b);
            }
        }
        if (!done && G16(st, 0xa8e) == 1 && G16(st, 0xaf8) == G16(st, 0x48c))
        {
            int d = Mv.DirTo(G16(st, 0x47c), G16(st, 0x48a), G16(st, 0xad6), G16(st, 0xae8));
            int ca = st.S8(T, 0x10 + d) + G16(st, 0x47c);
            int cb = st.S8(T, 0x1a + d) + G16(st, 0x48a);
            if (!(0 <= ca && ca <= 0x7f)) ca = G16(st, 0x47c);
            if (!(0 <= cb && cb <= 0x3f)) cb = G16(st, 0x48a);
            if (G16(st, 0xad6) == ca && G16(st, 0xae8) == cb)              // the target cell is next to it
            {
                int r = ActOnCell(st, G16(st, 0x48c), ca, cb);
                if (r != 0)
                {
                    res = r == 1 ? -1 : -2;
                    done = true;
                }
            }
        }
        if (!done) (res, done) = Step(st);
        if (st.U16(T, 0x7a8) != 0) UiFollow(st);
        if (res == 0 && G16(st, 0xaf8) == G16(st, 0x48c) && G16(st, 0xad6) == G16(st, 0x47c) && G16(st, 0xae8) == G16(st, 0x48a)
            && G16(st, 0xa8e) == 0)
            res = -1;                                                      // arrived
        if (res == 0) return;
        if (res == -2)
        {
            st.Hooks.Effect(st, "sound", 1);
            UiFollow(st);
        }
        else if (G16(st, 0xa8e) == 3)
        {
            st.Set16(G, 0x1058, 1);
            AttackPlayer(st, G16(st, 0x8da), G16(st, 0x7c0));
            st.Set16(G, 0x1058, 0);
        }
        else if (G16(st, 0xa8e) == 4)
        {
            var (x, y, t, state, e) = ant.Value;
            int d = Mv.DirTo(x, y, G16(st, 0x47c), G16(st, 0x48a)) - 1;
            if (d >= 0 && (t & 0x70) != 0x60)                              // the ant turns to face the yellow one
            {
                t = (t & 0xf8) | d;
                SetAnt(st, G16(st, 0x48c), G16(st, 0x7c0), x, y, t, state, e);
                SetOcc(st, G16(st, 0x48c), x, y, t);
                st.Hooks.Effect(st, "redraw_all");
            }
            Eat(st, 1);                                                    // MenuCommand12de1(1)
        }
        StopAction(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a));    // f_2f820
        if (st.U16(G, 0xf24) != 0 && G16(st, 0x48c) == 1)                 // on the house's 0x76 / 0x78 tiles
        {
            int o = ((st.U16(G, 0x47c) << 6) + st.U16(G, 0x48a)) & 0xffff;
            int tile = st.U8(SIM, SURFACE + o);
            if (tile == 0x76 || tile == 0x78) st.Hooks.GameEvent(st, 10);
        }
    }

    /// <summary>The walking part of f_7b7b8: (res, done).</summary>
    static (int, bool) Step(State st)
    {
        int view = G16(st, 0x48c);
        int d = StepToCursor(st, view, G16(st, 0x47c), G16(st, 0x48a), G16(st, 0xaf8), G16(st, 0xad6), G16(st, 0xae8));
        if (d < 0) return (d, true);
        int nb = st.S8(T, 8 + d) + G16(st, 0x48a);
        st.Set16(G, 0xab6, G16(st, 0x47c));
        st.Set16(G, 0xac6, G16(st, 0x48a));
        int na = G16(st, 0x47c) + st.S8(T, d);
        MoveYellow(st, view, na, nb, G16(st, 0x4c2), d);
        st.Inc16(G, 0xc3e);
        int t = G16(st, 0x4c2);
        if (view == 1)
        {
            if (G16(st, 0x4c4) > 0 && (t == 0x18 || t == 0x38))           // carrying food: lay the trail
            {
                Ph.LayMax(st, st.U16(G, 0x4e2) == 0 ? Ph.BLACK_TRAIL : Ph.RED_TRAIL, G16(st, 0x47c), G16(st, 0x48a),
                          st.U16(G, 0x4c4));
                if (G16(st, 0x4c4) > 10) st.Inc16(G, 0x4c4, -1);
            }
            if (st.U16(G, 0x104e) != 0) AlarmAdd(st, G16(st, 0x47c), G16(st, 0x48a), 0x32);
        }
        else
            Ng.UpdateExitField(st, view == 2 ? Ng.BLACK : Ng.RED, G16(st, 0x47c), G16(st, 0x48a));
        if ((st.U8(G, 0xc3e) & 1) != 0)
        {
            if (t == 0x40 && st.U16(T, 0xc24) == 0 && G16(st, 0x10be) > 0 && st.U16(T, 0xc18) == 0)
                st.Inc16(G, 0x10be, -1);
            SetHealth(st, Hp(st) - 1);
        }
        if (G16(st, 0x48c) == 1)
        {
            if (!Mv.AtNestEntrance(st, G16(st, 0x47c), G16(st, 0x48a))) return (0, true);
            if (!(G16(st, 0xaf8) > 1 || (G16(st, 0xaf8) == G16(st, 0x48c) && G16(st, 0xad6) == G16(st, 0x47c)
                                         && G16(st, 0xae8) == G16(st, 0x48a))))
                return (0, true);
            st.Hooks.Effect(st, "redraw_all");                              // f_11ab0
            int old = G16(st, 0x48c);
            EnterNest(st);
            return AfterSwitch(st, old, na, nb);
        }
        if (G16(st, 0x48a) == 0)
        {
            st.Hooks.Effect(st, "redraw_all");
            int old = G16(st, 0x48c);
            LeaveNest(st);
            return AfterSwitch(st, old, na, nb);
        }
        if (GetTile(st, G16(st, 0x48c), G16(st, 0xad6), G16(st, 0xae8)) == 0x14 && t != 0x60
            && G16(st, 0xad6) == G16(st, 0x47c) && G16(st, 0xae8) == G16(st, 0x48a))   // through the hole into the other nest
        {
            TakeYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), t, st.U16(G, 0x496));
            st.Set16(G, 0x48c, G16(st, 0x48c) == 2 ? 3 : 2);
            PutYellow(st, G16(st, 0x48c), G16(st, 0x47c), G16(st, 0x48a), t, st.U16(G, 0x496), 0xff);
            st.Hooks.Effect(st, "sound", 1);
            UiFollow(st);
            if (G16(st, 0x48c) == 3) st.Hooks.Effect(st, "status", "red nest");   // f_15e2c
            return (-1, true);
        }
        return (0, true);
    }

    /// <summary>L_bc43: after entering or leaving a nest the walk goes on, unless the cursor was on the
    /// entrance cell just stepped onto (and the new view is not the one shown, G:032E).</summary>
    static (int, bool) AfterSwitch(State st, int oldView, int na, int nb)
    {
        if (!(G16(st, 0xaf8) == oldView && G16(st, 0xad6) == na && G16(st, 0xae8) == nb)) return (0, true);
        if (G16(st, 0x48c) == G16(st, 0x32e)) return (0, true);
        if (st.U16(T, 0x7a8) == 0) UiFollow(st);
        return (-1, true);
    }

    /// <summary>f_14cad: alarm scent += n (max 200).</summary>
    public static void AlarmAdd(State st, int a, int b, int n)
    {
        int i = (S16(a) >> 1) * 32 + (S16(b) >> 1);
        int v = st.U8(SIM, 0xd09f + i) + n;
        st.Set8(SIM, 0xd09f + i, Math.Min(v, 200));
    }

    /// <summary>f_769c5 (also via f_2f7bc): an ant at (a, b) bumps the yellow ant along heading d; it turns to
    /// face the ant (and MenuCommand12de1(1) runs).</summary>
    public static void Nudge(State st, int a, int b, int d)
    {
        int na = a + st.S8(T, d), nb = b + st.S8(T, 8 + d);
        int h = Mv.DirTo(na, nb, a, b) - 1;
        MoveYellow(st, G16(st, 0x48c), na, nb, G16(st, 0x4c2), h);
        st.Hooks.Effect(st, "redraw_all");
        Eat(st, 1);
    }

    // ------------------------------------------------------------------------------------------- upkeep
    /// <summary>f_7bf7e: keep the yellow ant on the map, age it, let a yellow queen lay; it dies after 100
    /// ticks at zero health.</summary>
    public static void YellowTick(State st)
    {
        if (st.U16(G, 0xa06) != 0) return;
        int view = G16(st, 0x48c);
        int a = G16(st, 0x47c), b = G16(st, 0x48a);
        PutYellow(st, view, a, b, G16(st, 0x4c2), st.U16(G, 0x496), 0xff);
        view = G16(st, 0x48c);
        a = G16(st, 0x47c);
        b = G16(st, 0x48a);
        if ((st.U8(G, 0xf08) & 0x3f) == 0) SetHealth(st, Hp(st) - 1);
        int tile = -1;
        bool haveTile = false;
        if (view >= 2)
        {
            tile = GetTile(st, view, a, b);
            haveTile = true;
            if (tile >= 0x4e) SetHealth(st, Hp(st) - 1);                   // flooded
        }
        if (st.U16(G, 0x4c2) == 0x60 && view > 1 && (st.U8(G, 0xf08) & 0xf) == 0)
        {
            int h = st.U16(G, 0x496) ^ 4;
            int eb = st.S8(T, 8 + h) * 2 + G16(st, 0x48a);
            int ea = st.S8(T, h) * 2 + G16(st, 0x47c);
            if (Nest.NestCellFree(ea, eb) && st.Rand128() <= Hp(st))      // lay an egg behind her
            {
                if (st.U16(G, 0x4e2) == 0)
                {
                    Nest.SpawnBrood(st, Nest.BLACK, ea, eb, 1);
                    Nest.EggCost(st);
                }
                else
                {
                    Nest.SpawnBrood(st, Nest.RED, ea, eb, 1);
                    RedNest.EggCost(st);
                }
                SetHealth(st, Hp(st) - 5);
            }
        }
        if (Hp(st) <= 0)
        {
            st.Inc16(G, 0x1006);
            if (G16(st, 0x1006) >= 100) st.Hooks.GameEvent(st, view >= 2 && haveTile && tile >= 0x4e ? 7 : 8);
        }
    }
}
