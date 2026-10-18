namespace Formica.Sim;

/// <summary>
/// The hooks the simulation calls for the player (the yellow ant) and for everything screen-only. The names
/// of <see cref="Effect"/> are the remake's event list (sounds, redraws, messages, balloons, markers, pause).
/// </summary>
public interface IPlayer
{
    void AttackPlayer(State st, int view, int ant);
    void NudgePlayer(State st, int a, int b, int d);
    void SpiderEvent(State st, int n);
    void SpiderEatsPlayer(State st, int a, int b);
    void LionEatsPlayer(State st, int a, int b);
    void NestFollow(State st, int col, int depth, int d);
    void YardEvent(State st, int n);
    void GameEvent(State st, int n);
    void GameOver(State st);
    void WinScreen(State st);
    int NewGameDialog(State st);
    void ChoosePatch(State st);
    bool SoundDone(State st);

    /// <summary>A screen-only effect. Arguments are evaluated by the caller in the original's order (some of
    /// them draw from the game's RNG).</summary>
    void Effect(State st, string name, params object[] args);
}

/// <summary>Player hooks not ported: fail loudly if the simulation reaches them (surface.NoPlayer).</summary>
public class NoPlayer : IPlayer
{
    public virtual void AttackPlayer(State st, int view, int ant) => throw new NotImplementedException("AttackPlayer (f_7c5ab)");
    public virtual void NudgePlayer(State st, int a, int b, int d) => throw new NotImplementedException("f_769c5 (player follow nudge)");
    public virtual void SpiderEvent(State st, int n) => throw new NotImplementedException($"f_2f7d0({n}) (the player-spider leaves or is beaten)");
    public virtual void SpiderEatsPlayer(State st, int a, int b) => throw new NotImplementedException("f_11a3e / f_2f7d0(1) (the spider eats the yellow ant)");
    public virtual void LionEatsPlayer(State st, int a, int b) => throw new NotImplementedException("f_11a3e / f_2f7d0(2) (an ant lion catches the yellow ant)");
    public virtual void NestFollow(State st, int col, int depth, int d) => throw new NotImplementedException("f_2f7bc (nest ant steps onto the yellow ant)");
    public virtual void YardEvent(State st, int n) => throw new NotImplementedException($"f_2f7d0({n}) (the human or the mower hits the player)");
    public virtual void GameEvent(State st, int n) => throw new NotImplementedException($"f_2f7d0({n}) -> f_75d01 (player event)");
    public virtual void GameOver(State st) => throw new NotImplementedException("f_71d95 (the game-over screen: rating, new game)");
    public virtual void WinScreen(State st) => throw new NotImplementedException("f_2f91a (Full Game won: the end screen)");
    public virtual int NewGameDialog(State st) => throw new NotImplementedException("f_725b6 (the new-game dialog)");
    public virtual void ChoosePatch(State st) => throw new NotImplementedException("f_7650c (the yard map: pick a patch)");
    public virtual bool SoundDone(State st) => throw new NotImplementedException("f_284a4 (the sound driver: has the sound finished?)");
    public virtual void Effect(State st, string name, params object[] args) { }
}
