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
