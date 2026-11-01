using static OpenSimAnt.Sim.Seg;
using static OpenSimAnt.Sim.Bits;

namespace OpenSimAnt.Sim;

/// <summary>The tutorial (game mode G:0EAC = 0; port of simant_ref/tutorial.py): f_0e425, run by the advisor
/// f_0e2ea every tick before its status line. Every 8th call (T:07A2 counts to 0x400) it either shows the current
/// step T:07A4 (f_0e4e4: a message box with the step's text, STR# 11000 + 2 (step - 1), some with a picture
/// 17000.., and a little setup) or polls the step's check (f_0e93e): done → the next step; not done after 16 polls
/// (G:10B8) and past the clock target G:0204 → the step's message again. T:07A6 says whether the step has been
/// shown. Steps run 1..56. Screen only: "message_box" (f_2f6ea → f_71b1a(picture, STR# id, 1)) with args (id, 1,
/// picture).</summary>
public static class Tutorial
{
    static long Target(State st) => S32(st.U32(G, 0x204));
    static void SetTarget(State st, long v) => st.Set32(G, 0x204, v & 0xffffffffL);
    /// <summary>f_23612(win): window `win` (layout &lt;&lt; 8) is the active one, DS:5702.</summary>
    static bool Front(State st, int win) => st.U16(DS, 0x5702) == win;
    static int YellowSum(State st) => (st.U16(G, 0x48a) + st.U16(G, 0x47c)) & 0xffff;
    static void Box(State st, int text, int picture = 0) => st.Hooks.Effect(st, "message_box", text, 1, picture);

    /// <summary>f_0e425.</summary>
    public static void Run(State st)
    {
        st.Set16(T, 0x7a2, st.U16(T, 0x7a2) + 1);
        if (S16(st.U16(T, 0x7a2)) > 0x400) st.Set16(T, 0x7a2, 0);
        if ((st.U16(T, 0x7a2) & 7) != 0) return;
        st.Set16(G, 0x10b8, st.U16(G, 0x10b8) + 1);
        int step = st.U16(T, 0x7a4);
        if (st.U16(T, 0x7a6) == 0)
        {
            Show(st, step);
            st.Set16(T, 0x7a6, 1);
            st.Set16(G, 0x10b8, 0);
            return;
        }
        if (Done(st, step)) st.Set16(T, 0x7a4, step + 1);
        else if (S16(st.U16(G, 0x10b8)) <= 0xf || Target(st) >= S32(st.Clock3())) return;
        st.Set16(T, 0x7a6, 0);
    }

    /// <summary>The steps' message boxes (STR# id, picture), where a step has a picture; the others show
    /// 0x2AF8 + 2 (step - 1) without one (step 56: 0x2B68).</summary>
    static readonly Dictionary<int, (int text, int picture)> Pictures = new()
    {
        [2] = (0x2afa, 0x4268), [5] = (0x2b00, 0x4269), [11] = (0x2b0c, 0x4276), [13] = (0x2b10, 0x426a),
        [14] = (0x2b12, 0x426a), [17] = (0x2b18, 0x4275), [18] = (0x2b1a, 0x426b), [21] = (0x2b20, 0x426c),
        [33] = (0x2b38, 0x426d), [36] = (0x2b3e, 0x426e), [38] = (0x2b42, 0x426f), [39] = (0x2b44, 0x4270),
        [40] = (0x2b46, 0x4270), [41] = (0x2b48, 0x4270), [43] = (0x2b4c, 0x4271), [44] = (0x2b4e, 0x4271),
        [45] = (0x2b50, 0x4272), [46] = (0x2b52, 0x4272), [47] = (0x2b54, 0x4273), [48] = (0x2b56, 0x4273),
        [50] = (0x2b5a, 0x4274),
    };

    /// <summary>f_0e4e4(step): the step's message box and setup.</summary>
    public static void Show(State st, int step)
    {
        if (step < 1 || step > 0x38) return;
        if (step == 23) NewGame.AddSurfaceAnts(st, 10, false);           // f_2f6cc → f_6be50
        if (step == 55)
        {
            Box(st, st.U16(G, 0x1074) == 0 ? 0x2b64 : 0x2b66);
            return;
        }
        // Step 56 (the closing box) is the one step off the 0x2AF8 + 2 (step - 1) rule: f_0e4e4 case 56 (0e925) pushes
        // 0x2B68 (list 11112), since step 55's two variants take 0x2B64 and 0x2B66 (11108, 11110).
        var (text, picture) = step == 0x38 ? (0x2b68, 0) : Pictures.TryGetValue(step, out var p) ? p : (0x2af8 + 2 * (step - 1), 0);
        Box(st, text, picture);
        switch (step)
        {
            case 3 or 4:                                                  // dig: the nest must grow past this
                SetTarget(st, S16(st.U16(G, 0x224)) + (step == 3 ? 2 : 10));
                break;
            case 7 or 26:                                                 // walk: from here, within ~10 s
                st.Set16(G, 0x1074, YellowSum(st));
                SetTarget(st, st.Clock3() + 0x258);
                break;
            case 8 or 30 or 43 or 46 or 50:
                st.Set16(G, 0x1074, 0);
                break;
            case 9:                                                       // scroll the view
                st.Set16(G, 0x1074, st.U16(G, 0x50a) + st.U16(G, 0x508));
                SetTarget(st, st.Clock3() + 0x258);
                break;
            case 14:
                Player.SetHealth(st, 8);                                  // f_12d43: hungry, so it eats
                break;
            case 27:
                st.Set16(G, 0x1074, YellowSum(st));
                break;
            case 41:                                                      // the behaviour triangle
                st.Set16(G, 0x1074, st.U16(G, 0x4a0) + st.U16(G, 0x49e));
                break;
            case 49:
                NewGame.AddSurfaceAnts(st, 0x50, false);                  // f_2f6cc(0x50)
                for (int i = 0; i < 0x40 * 0x20; i++) st.Set8(SIM, 0xd09f + i, 0);   // clear the alarm scent map
                break;
        }
    }

    static bool ClockPassed(State st) => S32(st.Clock3()) > Target(st);

    /// <summary>f_0e93e(step): has the player done what the step asks?</summary>
    public static bool Done(State st, int step)
    {
        int G_(int off) => st.U16(G, off);
        switch (step)
        {
            case 3 or 4: return S16(G_(0x224)) > Target(st) && G_(0xaa0) == 0;
            case 5 or 20: return G_(0x48c) == 1;
            case 7 or 26: return YellowSum(st) != G_(0x1074) && G_(0xb1e) == 0 && ClockPassed(st);
            case 8 or 43 or 46 or 50: return G_(0x1074) != 0;
            case 9: return ((G_(0x50a) + G_(0x508)) & 0xffff) != G_(0x1074) || ClockPassed(st);
            case 10 or 32 or 42: return Front(st, 0x100);
            case 12 or 49: return Front(st, 0);
            case 13: return G_(0x48c) == 1 && st.U8(SIM, 0x180 + (((G_(0x47c) << 6) + G_(0x48a)) & 0xffff)) > 0x47;
            case 14: return S16(G_(0xf78)) > 0x5a;
            case 16: return G_(0x4c2) == 0x18;
            case 18: return G_(0x48c) == 2;
            case 19 or 22: return G_(0x4c2) == 0x10;
            case 21: return G_(0x4c2) == 0x28;
            case 24: return S16(G_(0xb1c)) > 1;
            case 27: return YellowSum(st) != G_(0x1074) && G_(0x104e) != 0 && G_(0xb1e) == 0;
            case 30:
                if (G_(0x104e) != 0) Player.AlarmMode(st, 0, 1);         // f_2f80c(0, 1)
                return G_(0x1074) != 0;
            case 33: return G_(0x32e) == 0;
            case 36: return G_(0x35c) == 1;
            case 38: return G_(0x32e) == 1;
            case 39: return Front(st, 0x1200);
            case 41: return ((G_(0x4a0) + G_(0x49e)) & 0xffff) != G_(0x1074);
            case 47: return Front(st, 0x1300);
            case 52: return S16(G_(0xb1c)) > 0x28;
            case 54:
                if (G_(0x48c) == 3) { st.Set16(G, 0x1074, 0); return true; }
                if (G_(0x48c) == 2) { st.Set16(G, 0x1074, 1); return true; }
                return false;
            default: return step >= 1 && step <= 0x38;
        }
    }
}
