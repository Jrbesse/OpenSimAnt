using OpenSimAnt.Data;
using Xunit;

namespace OpenSimAnt.Sim.Tests;

/// <summary>ROADMAP B2: walks the Tutorial's 56 steps through the simulation (OpenSimAnt.Sim.Tutorial inside the real
/// SimStep): after each step's box appears, the player's action is done by writing what the step's check reads (the
/// same conditions tools/ref/test_tutorial.py plants), and the next box must follow. The expected boxes (STR# id and
/// HCEGANT picture of f_2f6ea's arguments) were taken from the original running in the emulator
/// (f_0e4e4 called for each step with f_71b1a hooked: tools/ref's Verifier, 2026-11-01), not from Tutorial.cs.
/// The shell's part (drawing, the 15 s timeout, the mouse actions) is not covered: see `--tutorial-boxes` in Main.cs.</summary>
public class TutorialWalkTests
{
    // step -> picture, from the emulator; the box ids are 11000 + 2 (step - 1), except step 56 (11112) and step 55's
    // second variant (11110, after the black nest)
    static readonly Dictionary<int, int> Pictures = new()
    {
        [2] = 17000, [5] = 17001, [11] = 17014, [13] = 17002, [14] = 17002, [17] = 17013, [18] = 17003, [21] = 17004,
        [33] = 17005, [36] = 17006, [38] = 17007, [39] = 17008, [40] = 17008, [41] = 17008, [43] = 17009, [44] = 17009,
        [45] = 17010, [46] = 17010, [47] = 17011, [48] = 17011, [50] = 17012,
    };

    static (int id, int pic) Expected(int step, bool blackNest = false) =>
        (step == 56 ? 11112 : 11000 + 2 * (step - 1) + (step == 55 && blackNest ? 2 : 0), Pictures.GetValueOrDefault(step));

    class Recorder : PlayerHooks
    {
        public readonly List<(int id, int pic)> Boxes = new();
        public override void Effect(State st, string name, params object[] args)
        {
            if (name == "message_box") Boxes.Add((Convert.ToInt32(args[0]), args.Length > 2 ? Convert.ToInt32(args[2]) : 0));
        }
    }

    static State NewTutorial(out Recorder rec)
    {
        var st = GameTables.NewState();
        GameSession.ApplyBootDefaults(st);
        rec = new Recorder();
        st.Hooks = rec;
        st.Set16(Seg.DS, 0x8ba2, 0x1235);
        st.Set32(Seg.DS, 0x7bbe, 0x1234);
        st.Clock = 0x1234;
        Game.StartGame(st, 0);
        st.Set16(Seg.T, 0x7cc, 1);
        return st;
    }

    /// <summary>What the player has to do in `step` (done every tick while the step is current): the globals its check
    /// (f_0e93e) reads. Steps that pass at once need nothing.</summary>
    static void Act(State st, int step, int nest)
    {
        int G(int off) => st.U16(Seg.G, off);
        void Set(int off, int v) => st.Set16(Seg.G, off, v);
        switch (step)
        {
            case 3 or 4: Set(0x224, st.S16(Seg.G, 0x204) + 5); Set(0xaa0, 0); break;     // dig: the nest grows past the target
            case 5 or 20: Set(0x48c, 1); break;                                         // on the surface
            case 7 or 26 or 27:                                                         // walk: the yellow ant's a + b changes, in time
                if (((G(0x48a) + G(0x47c)) & 0xffff) == G(0x1074)) Set(0x48a, G(0x48a) + 1);
                Set(0xb1e, 0);
                if (step == 27 && G(0x104e) == 0) Commands.Command(st, 7);              // the 0 key: the alarm scent on
                else st.Clock += 0x200;                                                 // the 10 s target passes
                break;
            case 8 or 43 or 46 or 50: Set(0x1074, 1); break;                            // recentre / help held / report held / follow
            case 9: Set(0x50a, G(0x50a) + 1); break;                                    // the Edit window scrolled
            case 10 or 32 or 42: st.Set16(Seg.DS, 0x5702, 0x100); break;                // the Map window active
            case 12 or 49: st.Set16(Seg.DS, 0x5702, 0); break;                          // the Edit window active
            case 13:
                Set(0x48c, 1);
                st.Set8(Seg.SIM, 0x180 + (((G(0x47c) << 6) + G(0x48a)) & 0xffff), 0x50); // standing on food
                break;
            case 14: Set(0xf78, 0x5b); break;                                           // fed
            case 16: Set(0x4c2, 0x18); break;                                           // carrying food
            case 18: Set(0x48c, 2); break;                                              // in the black nest
            case 19 or 22: Set(0x4c2, 0x10); break;                                     // food / pebble put down
            case 21: Set(0x4c2, 0x28); break;                                           // carrying a rock
            case 24 or 52: Commands.Command(st, 2); break;                              // Recruit 10, as often as it takes (G:0B1C is a census of the followers)
            case 30: Set(0x1074, 1); Set(0x104e, 1); break;                             // exchanged (the scent is switched off quietly)
            case 33: Set(0x32e, 0); break;                                              // the yard
            case 36: Set(0x35c, 1); break;                                              // the House view
            case 38: Set(0x32e, 1); break;                                              // the patch
            case 39: st.Set16(Seg.DS, 0x5702, 0x1200); break;                           // Behavior Control
            case 41: Set(0x49e, G(0x49e) + 1); break;                                   // the triangle's dot moved
            case 47: st.Set16(Seg.DS, 0x5702, 0x1300); break;                           // Caste Control
            case 54: Set(0x48c, nest); break;                                           // entered the red (3) / black (2) nest
        }
        if (step != 14) Set(0xf78, Math.Max(G(0xf78), 100));                            // the yellow ant is not in danger meanwhile
    }

    [Theory]
    [InlineData(3)]       // the red nest: "You reached the red nest" (11108)
    [InlineData(2)]       // the black nest: the other box (11110)
    public void AllFiftySixStepsShowTheirBoxesInOrder(int nest)
    {
        var st = NewTutorial(out var rec);
        int shown = 0;
        for (int tick = 0; tick < 6000 && st.U16(Seg.T, 0x7a4) < 57; tick++)
        {
            int step = st.U16(Seg.T, 0x7a4);
            if (st.U16(Seg.T, 0x7a6) != 0) Act(st, step, nest);            // the step has been shown: the player acts
            global::OpenSimAnt.Sim.Sim.SimStep(st);
            Assert.Equal(0, st.U16(Seg.G, 0x376));                          // the game is not over
            while (shown < rec.Boxes.Count)
            {
                int expectedStep = shown + 1;
                Assert.Equal(Expected(expectedStep, nest == 2), rec.Boxes[shown]);
                shown++;
            }
        }
        Assert.Equal(57, st.U16(Seg.T, 0x7a4));
        Assert.Equal(56, rec.Boxes.Count);

        for (int i = 0; i < 200; i++) global::OpenSimAnt.Sim.Sim.SimStep(st);   // after step 56: nothing more is shown
        Assert.Equal(56, rec.Boxes.Count);
        Assert.Equal(57, st.U16(Seg.T, 0x7a4));
    }

    [Fact]
    public void AStepNotDoneShowsItsBoxAgain()
    {
        // step 5 (go up to the surface) is not done: after 16 polls, and once the clock has passed the target
        // G:0204 (0 here), the box is shown again (f_0e425)
        var st = NewTutorial(out var rec);
        st.Set16(Seg.T, 0x7a4, 5);
        for (int i = 0; i < 8 * 40; i++) global::OpenSimAnt.Sim.Sim.SimStep(st);
        Assert.True(rec.Boxes.Count >= 2, $"{rec.Boxes.Count} boxes");
        Assert.All(rec.Boxes, b => Assert.Equal((11008, 17001), b));
        Assert.Equal(5, st.U16(Seg.T, 0x7a4));
    }
}
