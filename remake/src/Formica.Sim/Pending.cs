namespace Formica.Sim;

// Placeholders for modules not ported yet; each goes away when its module lands.
public static partial class Player
{
    public static void PlayerEvent(State st, int n) => throw new NotImplementedException("player.player_event");
    public static void AttackPlayer(State st, int view, int ant) => throw new NotImplementedException("player.attack_player");
    public static void Nudge(State st, int a, int b, int d) => throw new NotImplementedException("player.nudge");
    public static void MoveYellow(State st, int view, int a, int b, int d, int e) => throw new NotImplementedException("player.move_yellow");
}

public static partial class Game
{
    public static void GameOverScreen(State st) => throw new NotImplementedException("game.game_over_screen");
}
