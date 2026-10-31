using Formica.Sim;
using static Formica.Sim.Seg;

namespace Formica.Data;

/// <summary>A screen-only event from the simulation (sound, message, redraw, marker, ...), for the UI.</summary>
public readonly record struct SimEffect(string Name, object[] Args);

/// <summary>The hooks a playable game uses: the ported player logic, the map's event markers kept as the
/// original does, and every other effect queued for the UI.</summary>
public class SessionHooks : PlayerHooks
{
    public readonly Queue<SimEffect> Effects = new();
    public bool GameOverShown, WinShown, YardMapWanted;

    public override void GameOver(State st)
    {
        if (GameOverShown) return;
        GameOverShown = true;
        Game.GameOverScreen(st);
    }

    public override int? NewGameDialog(State st) => null;
    public override void WinScreen(State st)
    {
        WinShown = true;
        Effect(st, "win_screen");                                               // the shell plays f_72750
    }
    public override void ChoosePatch(State st) => YardMapWanted = true;

    // f_7c149 / f_7c3b1 (the fight and death animations) redraw the Edit window after every frame and wait 6 clock3
    // units: between "anim_begin" and "anim_end" each "anim_frame" keeps a copy of the State with the sounds played
    // since the last frame, and "anim_end" hands them to the UI as one "anim" effect (a list of frames).
    List<(State st, List<object[]> sounds)> anim;
    List<object[]> animSounds;

    public override void Effect(State st, string name, params object[] args)
    {
        if (name == "anim_begin") { anim = new(); animSounds = new(); return; }
        if (anim != null)
        {
            if (name == "sound") { animSounds.Add(args); return; }
            if (name == "anim_frame") { anim.Add((st.Clone(), animSounds)); animSounds = new(); return; }
            if (name == "anim_end")
            {
                if (Effects.Count < 4096) Effects.Enqueue(new SimEffect("anim", new object[] { anim }));
                anim = null;
                return;
            }
        }
        else if (name is "anim_frame" or "anim_end") return;
        if (Markers.IsMarker(name) && args.Length == 3) Markers.Record(st, name, (int)args[0], (int)args[1], (int)args[2]);
        if (Effects.Count < 4096) Effects.Enqueue(new SimEffect(name, args));
    }
}

/// <summary>One game: the State built from the player's SIMANT.EXE, ticked by SimStep, with the real-time
/// clock the original reads advancing with the game (about 18.2 Hz).</summary>
public sealed class GameSession
{
    public const double ClockHz = 1193182.0 / 65536.0;

    public readonly OriginalFiles Files;
    public readonly MapArt Art;
    public State St { get; private set; }
    public SessionHooks Hooks { get; private set; }
    public long Ticks { get; private set; }
    double clockFrac;
    long nextTick;
    int speed = 1;

    /// <summary>The original runs "fast" (T:07CE[2] = 0) as fast as the machine allows; this is the minimum
    /// tick period used for it here, in clock x3 units (~55 per second).</summary>
    public int FastDelay = 2;

    public GameSession(string gameDir) : this(new OriginalFiles(gameDir)) { }

    /// <summary>A session on the original's files or on the clean pack (OriginalFiles(byte[])).</summary>
    public GameSession(OriginalFiles files)
    {
        Files = files;
        Art = new MapArt(Files);
        UseTables = files.Exe == null;                           // the clean pack has no executable image
    }

    /// <summary>Start a game: 0 tutorial (not ported), 1 Quick Game, 2 Full Game, 3 experimental. A real game
    /// seeds both generators from the time of day; pass a seed for a repeatable game.</summary>
    public void NewGame(int mode, int? seed = null, byte[] bootState = null)
    {
        St = bootState != null ? new State((byte[])bootState.Clone()) : UseTables ? TablesState() : ExeImage.NewState(Files.Exe);
        if (bootState == null) ApplyBootDefaults(St);
        Hooks = new SessionHooks();
        St.Hooks = Hooks;
        int s = seed ?? FixedSeed ?? (int)(DateTime.Now.TimeOfDay.TotalSeconds * ClockHz);
        St.Set16(DS, 0x8ba2, (s & 0xffff) | 1);                 // the LFSR must not be 0
        St.Set32(DS, 0x7bbe, s);
        St.Clock = s;
        Game.StartGame(St, mode);
        St.Set16(T, 0x7cc, speed);
        nextTick = St.Clock3();
        if (options != null)
            for (int i = 0; i < 6; i++) St.Set16(T, 0x7a8 + 2 * i, options[i]);
        Ticks = 0;
    }

    /// <summary>Start games from <see cref="GameTables"/> (the numbers in source) instead of SIMANT.EXE's image
    /// (ROADMAP A2; `Formica.Replay --tables` checks that both play the same).</summary>
    public bool UseTables;

    /// <summary>When set, games without an explicit seed use this one instead of the time of day (repeatable runs).</summary>
    public int? FixedSeed;

    /// <summary>T:09E4..T:0B13, the spider's leg geometry: line art, so an asset rather than a game table.</summary>
    public const int SpiderLegsOff = 0x9e4, SpiderLegsEnd = 0xb14;

    State TablesState()
    {
        if (State.Touch != null)
            for (int i = 0; i < State.Size; i++) State.Touch[i] &= 2;
        var st = GameTables.NewState();
        // the spider's leg geometry: an embedded asset (EmbeddedAssets "spiderlegs"), in Flat at its place
        for (int o = SpiderLegsOff; o < SpiderLegsEnd; o++) st.Set8(T, o, Files.Flat[T * 16 + o]);
        return st;
    }

    /// <summary>What the original's start-up sets before the first new game that the simulation reads
    /// (found by diffing the emulator's memory after boot with the static image, tools/ref/boot_diff.py; the
    /// init code that sets them is not decoded yet). Everything else that boot changes is UI, far heap
    /// pointers, or relocated segment words.</summary>
    public static void ApplyBootDefaults(State st)
    {
        st.Set16(G, 0x480, 0x50);         // the highest passable surface tile (the yard tile set)
        st.Set16(G, 0xfba, 0x1e);         // the yellow ant's health warning level
        st.Set16(G, 0xffe, 0x1e);         // the advisor's colony hunger level
        st.Set16(DS, 0x1a2e, 0);          // the loaded tile set (0 the yard)
        st.Set16(G, 0x10de, 0x15);        // the map window's size in cells (event markers)
        st.Set16(G, 0x10e0, 0x16);
    }

    /// <summary>One SimStep; `seconds` of real time pass on the game's clock.</summary>
    public void Step(double seconds = 1.0 / ClockHz)
    {
        clockFrac += seconds * ClockHz;
        long whole = (long)clockFrac;
        clockFrac -= whole;
        St.Clock = (St.Clock + whole) & 0xffffffffL;
        global::Formica.Sim.Sim.SimStep(St);
        Balloons.Run(St);
        Ticks++;
    }

    /// <summary>The speed T:07CC: 0 Slow, 1 Normal (the start-up value), 2 Fast, 3 Ultra (the Speed menu).</summary>
    public int Speed
    {
        get => speed;
        set
        {
            speed = Math.Clamp(value, 0, 3);
            St?.Set16(T, 0x7cc, speed);
        }
    }

    int[] options;

    /// <summary>The Options menu's flags T:07A8 + 2 n (f_6e26d's 0xFD31..36): 0 AutoTrack (follow the walking
    /// yellow ant), 1 Music, 2 Sound Effects, 3 Events (the yellow ant's death messages), 4 Messages (the advisor's
    /// status line), 5 Silly (speech balloons and the event markers behind them). The start-up values are SIMANT.EXE's
    /// (0, 1, 1, 1, 1, 0); a new State starts from them, so the session carries the player's choices over.</summary>
    public bool Option(int n) => St.U16(T, 0x7a8 + 2 * n) != 0;

    public void ToggleOption(int n)
    {
        St.Set16(T, 0x7a8 + 2 * n, Option(n) ? 0 : 1);
        options = Enumerable.Range(0, 6).Select(i => (int)St.U16(T, 0x7a8 + 2 * i)).ToArray();
    }

    /// <summary>The pause flag G:047E (a pending yellow-ant action still runs, as in the original).</summary>
    public bool Paused
    {
        get => St.U16(G, 0x47e) != 0;
        set => St.Set16(G, 0x47e, value ? 1 : 0);
    }

    /// <summary>The main loop f_15f84: `seconds` of real time pass on the clock; each pass sets the next
    /// deadline to clock3() + T:07CE[speed] (21, 7, 0: about 2.6, 7.8 ticks per second and "as fast as
    /// possible"), runs SimStep unless paused (G:047E; while the yellow ant has an action pending, G:0AA0, and
    /// no pick-a-target mode is on, G:105E &lt; 10, it runs anyway), then waits for the deadline. Returns the
    /// number of SimSteps run.</summary>
    public int Advance(double seconds, int maxSteps = 8)
    {
        if (St.U16(T, 0x7cc) == 3) maxSteps *= 4;
        clockFrac += seconds * ClockHz;
        long whole = (long)clockFrac;
        clockFrac -= whole;
        St.Clock = (St.Clock + whole) & 0xffffffffL;
        int steps = 0;
        for (int pass = 0; pass < maxSteps; pass++)
        {
            long now = St.Clock3();
            if (now < nextTick) break;
            int delay = St.S16(T, 0x7ce + 2 * St.U16(T, 0x7cc));         // Ultra: T:07D4 = -1, no wait at all
            nextTick = now + (delay < 0 ? 0 : Math.Max(delay, FastDelay));
            if (St.U16(G, 0x47e) == 0 || (St.U16(G, 0xaa0) != 0 && St.S16(G, 0x105e) < 10))
            {
                global::Formica.Sim.Sim.SimStep(St);
                Balloons.Run(St);
                Ticks++;
                steps++;
            }
        }
        if (St.Clock3() >= nextTick) nextTick = St.Clock3();      // fell behind: don't try to catch up
        return steps;
    }

    public bool Over => St != null && St.U16(G, 0x376) != 0;

    /// <summary>Replace the game's memory with a State image (the original's own, dumped from the emulator by
    /// tools/re/screens.py), keeping the hooks and the clock: for drawing the same game as a captured screen.</summary>
    public void LoadState(byte[] mem)
    {
        long clock = St.Clock;
        St = new State((byte[])mem.Clone()) { Hooks = Hooks, Clock = clock };
        nextTick = St.Clock3();
    }

    /// <summary>Send the yellow ant towards (view, a, b) (1 surface, 2 black nest, 3 red nest): a walk (mode 0),
    /// or with dig a tunnel dug on the way (mode 2). What a click on the map does in the original.</summary>
    public void WalkTo(int view, int a, int b, bool dig = false)
    {
        St.Set16(G, 0xaa0, 1);
        St.Set16(G, 0xa8e, dig ? 2 : 0);
        St.Set16(G, 0xaf8, view);
        St.Set16(G, 0xad6, a);
        St.Set16(G, 0xae8, b);
        St.Set16(G, 0xd6c, 0xfffe);
    }

    /// <summary>f_75869: the yellow ant's walk target (view 0 counts as the surface; in a nest's top two rows a stays
    /// within 1..0x3E), then G:0AA0 = 1 as f_74fe0 sets it.</summary>
    public void SetTarget(int view, int a, int b)
    {
        St.Set16(G, 0xaf8, view == 0 ? 1 : view);
        St.Set16(G, 0xad6, view > 1 && b < 2 ? Math.Clamp(a, 1, 0x3e) : a);
        St.Set16(G, 0xae8, b);
        St.Set16(G, 0xd6c, 0xfffe);
        St.Set16(G, 0xaa0, 1);
    }

    /// <summary>The yellow ant: view, a, b.</summary>
    public (int view, int a, int b) Yellow => (St.U16(G, 0x48c), St.S16(G, 0x47c), St.S16(G, 0x48a));
}
