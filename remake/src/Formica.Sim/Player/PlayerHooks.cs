namespace Formica.Sim;

/// <summary>The player hooks the simulation calls, routed to the ports (player.Hooks). What is left to a UI:
/// Effect (screen only), ChoosePatch (the yard map: the player picks a patch, then the UI calls
/// NewGame.MoveToPatch), NewGameDialog (pick the next game: Game.StartGame), SoundDone (the sound driver,
/// only with sound hardware). The win screen (f_2f91a → f_72750) changes no game state.</summary>
public class PlayerHooks : NoPlayer
{
    public override void GameEvent(State st, int n) => Player.PlayerEvent(st, n);
    public override void GameOver(State st) => Game.GameOverScreen(st);
    public override void WinScreen(State st) => Effect(st, "win_screen");
    public override int NewGameDialog(State st) { Effect(st, "new_game_dialog"); return -1; }
    public override void ChoosePatch(State st) => Effect(st, "yard_map");
    public override bool SoundDone(State st) => true;
    public override void AttackPlayer(State st, int view, int ant) => Player.AttackPlayer(st, view, ant);
    public override void NudgePlayer(State st, int a, int b, int d) => Player.Nudge(st, a, b, d);
    public override void NestFollow(State st, int col, int depth, int d) => Player.Nudge(st, col, depth, d);

    public override void SpiderEatsPlayer(State st, int a, int b)
    {
        Player.MoveYellow(st, Bits.S16(st.U16(Seg.G, 0x48c)), a, b, Bits.S16(st.U16(Seg.G, 0x4c2)), st.U16(Seg.G, 0x496));
        GameEvent(st, 1);
    }

    public override void LionEatsPlayer(State st, int a, int b)
    {
        Player.MoveYellow(st, 1, a, b, Bits.S16(st.U16(Seg.G, 0x4c2)), st.U16(Seg.G, 0x496));
        GameEvent(st, 2);
    }

    public override void SpiderEvent(State st, int n) => GameEvent(st, n);
    public override void YardEvent(State st, int n) => GameEvent(st, n);
}
