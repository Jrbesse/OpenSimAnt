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
    public override void WinScreen(State st) => WinShown = true;
    public override void ChoosePatch(State st) => YardMapWanted = true;

    public override void Effect(State st, string name, params object[] args)
    {
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

    public GameSession(string gameDir)
    {
        Files = new OriginalFiles(gameDir);
        GameData.Flat = Files.Flat;
        Art = new MapArt(Files);
    }

    /// <summary>Start a game: 0 tutorial (not ported), 1 Quick Game, 2 Full Game, 3 experimental. A real game
    /// seeds both generators from the time of day; pass a seed for a repeatable game.</summary>
    public void NewGame(int mode, int? seed = null, byte[] bootState = null)
    {
        St = bootState != null ? new State((byte[])bootState.Clone()) : ExeImage.NewState(Files.Flat);
        if (bootState == null) ApplyBootDefaults(St);
        Hooks = new SessionHooks();
        St.Hooks = Hooks;
        int s = seed ?? (int)(DateTime.Now.TimeOfDay.TotalSeconds * ClockHz);
        St.Set16(DS, 0x8ba2, (s & 0xffff) | 1);                 // the LFSR must not be 0
        St.Set32(DS, 0x7bbe, s);
        St.Clock = s;
        Game.StartGame(St, mode);
        St.Set16(T, 0x7cc, speed);
        nextTick = St.Clock3();
        St.Set16(T, 0x7b2, 1);                                  // the patch is shown
        Ticks = 0;
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

    /// <summary>The speed T:07CC: 0 slow, 1 medium (the start-up value), 2 fast.</summary>
    public int Speed
    {
        get => speed;
        set
        {
            speed = Math.Clamp(value, 0, 2);
            St?.Set16(T, 0x7cc, speed);
        }
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
        clockFrac += seconds * ClockHz;
        long whole = (long)clockFrac;
        clockFrac -= whole;
        St.Clock = (St.Clock + whole) & 0xffffffffL;
        int steps = 0;
        for (int pass = 0; pass < maxSteps; pass++)
        {
            long now = St.Clock3();
            if (now < nextTick) break;
            int delay = St.S16(T, 0x7ce + 2 * St.U16(T, 0x7cc));
            nextTick = now + Math.Max(delay, FastDelay);
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

    /// <summary>The yellow ant: view, a, b.</summary>
    public (int view, int a, int b) Yellow => (St.U16(G, 0x48c), St.S16(G, 0x47c), St.S16(G, 0x48a));
}
