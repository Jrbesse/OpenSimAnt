using Godot;
using Formica.Data;
using Formica.Sim;

namespace Formica.Game;

/// <summary>
/// The first playable shell: finds the player's own copy of the original game, starts a game and shows the
/// map window (40 x 28 cells of 16 px, as in the original's 640 x 480 screen) with a status line.
///
/// Controls: left click walks the yellow ant there (with Shift: acts on the cell, picking up / dropping;
/// right click: digs its way), 1 / 2 / 3 the surface / black nest / red nest, arrow keys scroll, F follows
/// the yellow ant, Space pauses, + / - change the speed, N a new Quick Game, M a new Full Game.
/// Commands: R / Shift+R recruit 5 / 10, E / Shift+E release half / all, X exchange (then click an ant, or
/// the spider), A alarm trail, H dig a hole, B start brood, C chase (as the spider, then click), U / Shift+U
/// hunt / lash out.
/// </summary>
public partial class Main : Node2D
{
    const int Cols = 40, Rows = 28, Cell = 16;
    static readonly string[] SpeedNames = { "slow", "medium", "fast" };

    GameSession session;
    Sprite2D map;
    Image image;
    ImageTexture texture;
    uint[] argb;
    byte[] rgba;
    Label status, message;
    int view = 1, originA, originB;
    bool follow = true;
    string lastMessage = "";
    string screenshot;
    int frames;

    public override void _Ready()
    {
        var dir = FindGameDir();
        var layer = new CanvasLayer();
        AddChild(layer);
        status = new Label { Position = new Vector2(4, Rows * Cell + 2), Size = new Vector2(632, 16) };
        message = new Label { Position = new Vector2(4, Rows * Cell + 16), Size = new Vector2(632, 16) };
        foreach (var l in new[] { status, message })
        {
            l.AddThemeFontSizeOverride("font_size", 11);
            layer.AddChild(l);
        }
        if (dir == null)
        {
            status.Text = "Original game files not found.";
            message.Text = "Copy SIMANT.EXE, HCEGANT.DAT/.NDX into the game folder or pass --game-dir=<path>.";
            status.Position = new Vector2(8, 200);
            message.Position = new Vector2(8, 220);
            GD.PrintErr("Formica: no SIMANT.EXE / HCEGANT found");
            return;
        }
        GD.Print("Formica: game files in " + dir);
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--screenshot=")) screenshot = arg["--screenshot=".Length..];
        session = new GameSession(dir);
        session.NewGame(1);
        argb = new uint[Cols * Cell * Rows * Cell];
        rgba = new byte[argb.Length * 4];
        image = Image.CreateEmpty(Cols * Cell, Rows * Cell, false, Image.Format.Rgba8);
        texture = ImageTexture.CreateFromImage(image);
        map = new Sprite2D { Texture = texture, Centered = false };
        AddChild(map);
        MoveChild(map, 0);
        SetView(session.Yellow.view);
        Redraw();
    }

    /// <summary>--game-dir=..., FORMICA_GAME_DIR, or the folders above the project / the executable.</summary>
    static string FindGameDir()
    {
        foreach (var arg in OS.GetCmdlineUserArgs().Concat(OS.GetCmdlineArgs()))
            if (arg.StartsWith("--game-dir=")) return arg["--game-dir=".Length..];
        var env = System.Environment.GetEnvironmentVariable("FORMICA_GAME_DIR");
        if (!string.IsNullOrEmpty(env) && OriginalFiles.Present(env)) return env;
        foreach (var start in new[] { ProjectSettings.GlobalizePath("res://"), System.IO.Path.GetDirectoryName(OS.GetExecutablePath()) })
        {
            var d = new System.IO.DirectoryInfo(start);
            for (int i = 0; i < 5 && d != null; i++, d = d.Parent)
                if (OriginalFiles.Present(d.FullName)) return d.FullName;
        }
        return null;
    }

    public override void _Process(double delta)
    {
        if (session == null) return;
        if (session.Hooks.YardMapWanted)                                    // the yellow ant died: pick a colony
        {
            session.Hooks.YardMapWanted = false;
            yardMap = true;
        }
        if (!session.Over && !yardMap) session.Advance(delta);
        DrainEffects();
        if (follow) CenterOnYellow();
        Redraw();
        if (screenshot != null && ++frames == 240)
        {
            // --screenshot=<png>: save the screen after 240 frames and quit (for checking a build)
            GetViewport().GetTexture().GetImage().SavePng(screenshot);
            GetTree().Quit();
        }
    }

    void DrainEffects()
    {
        while (session.Hooks.Effects.Count > 0)
        {
            var e = session.Hooks.Effects.Dequeue();
            if (e.Name is "message" or "message_box" && e.Args.Length > 0 && e.Args[0] is int id)
            {
                var lines = session.Files.Strings(id);
                lastMessage = lines != null ? string.Join(" ", lines) : $"message 0x{id:x}";
                GD.Print("message: " + lastMessage);
            }
            else if (e.Name == "game_over" && e.Args.Length >= 2)
            {
                // f_71d95's rating window: the rank's title (STR# 1900 = G:0328) and the score (Game.Rating). f_71d95
                // shows entry `rank` of the list at G:0328 (loaded from STR# 1900), with the mode's name (G:0324) above it.
                int rank = (int)e.Args[0];
                var titles = session.Files.Strings(1900);
                string title = titles != null && rank < titles.Length ? titles[rank] : $"rank {rank}";
                lastMessage = $"Game over: {title}  (score {e.Args[1]})  N: new Quick Game, M: new Full Game";
                GD.Print(lastMessage);
            }
        }
    }

    static string Describe(object[] args) => string.Join(" ", args.Select(a => a is int i ? $"0x{i:x}" : a?.ToString() ?? "-"));

    void CenterOnYellow()
    {
        var (v, a, b) = session.Yellow;
        if (v != view) return;
        originA = a - Cols / 2;
        originB = b - Rows / 2;
        Clamp();
    }

    void Clamp()
    {
        originA = Math.Clamp(originA, 0, MapRenderer.Width(view) - Cols);
        originB = Math.Clamp(originB, 0, MapRenderer.Height - Rows);
    }

    // ------------------------------------------------------------------------------- the yard map (simple)
    // The yard is 12 x 16 patches (c = G:07BC / G:07CA 0..11, r = G:07BE / G:07CC 0..15); colony strengths
    // T:00A4[c*16 + r] (black) and T:0164[...] (red), 0..0xFA; patches 0..37 are the house. The original draws
    // it isometric (the yard map f_7650c); this is a plain grid until that screen is built.
    const int YardX = 32, YardY = 24, YardW = 36, YardH = 34;
    bool yardMap;

    void DrawYard(uint[] dst, int w)
    {
        var st = session.St;
        int pc = st.U16(Seg.G, 0x7ca), pr = st.U16(Seg.G, 0x7cc);
        Array.Fill(dst, 0xff204020u);
        for (int c = 0; c < 12; c++)
            for (int r = 0; r < 16; r++)
            {
                int idx = c * 16 + r;
                int black = st.U8(Seg.T, 0xa4 + idx), red = st.U8(Seg.T, 0x164 + idx);
                uint ground = idx <= 0x25 ? 0xff707070u : 0xff3c7a2cu;
                int x0 = YardX + r * YardW, y0 = YardY + c * YardH;
                for (int y = 1; y < YardH - 1; y++)
                    for (int x = 1; x < YardW - 1; x++)
                    {
                        uint col = ground;
                        if (x < YardW / 2 && y >= YardH - 1 - black * (YardH - 2) / 250) col = 0xff101010u;
                        if (x >= YardW / 2 && y >= YardH - 1 - red * (YardH - 2) / 250) col = 0xffc02020u;
                        bool edge = c == pc && r == pr && (x < 3 || y < 3 || x >= YardW - 4 || y >= YardH - 4);
                        dst[(y0 + y) * w + x0 + x] = edge ? 0xffffff40u : col;
                    }
            }
    }

    void YardClick(Vector2 p)
    {
        int r = (int)((p.X - YardX) / YardW), c = (int)((p.Y - YardY) / YardH);
        if (p.X < YardX || p.Y < YardY || r > 15 || c > 11) return;
        var st = session.St;
        st.Set16(Seg.G, 0x7bc, c);
        st.Set16(Seg.G, 0x7be, r);
        NewGame.MoveToPatch(st);                                            // f_01d48 (it may refuse: a message)
        yardMap = false;
        SetView(session.Yellow.view);
    }

    void Redraw()
    {
        var st = session.St;
        int w = Cols * Cell;
        int cols = Math.Min(Cols, MapRenderer.Width(view));
        Array.Fill(argb, 0xff000000u);
        if (yardMap) DrawYard(argb, w);
        else MapRenderer.Render(st, session.Art, view, originA, originB, originA + cols, originB + Rows, argb, w);
        if (view == 1 && !yardMap)
            SpiderRenderer.Draw(st, session.Files, session.Art, argb, w, Rows * Cell, originA * Cell, originB * Cell, SpiderRenderer.FangJitter(st));
        for (int i = 0; i < argb.Length; i++)
        {
            uint c = argb[i];
            rgba[4 * i] = (byte)(c >> 16);
            rgba[4 * i + 1] = (byte)(c >> 8);
            rgba[4 * i + 2] = (byte)c;
            rgba[4 * i + 3] = 255;
        }
        image.SetData(w, Rows * Cell, false, Image.Format.Rgba8, rgba);
        texture.Update(image);
        string[] names = { "", "Surface", "Black nest", "Red nest" };
        string mode = st.U16(Seg.G, 0xeac) == 2 ? "Full Game" : "Quick Game";
        status.Text = $"{mode}  {names[view]}  tick {session.Ticks}  black {st.U16(Seg.G, 0x330)}  red {st.U16(Seg.G, 0x350)}"
                      + $"  health {st.S16(Seg.G, 0xf78)}  colony {st.S16(Seg.G, 0x10be)}  speed {SpeedNames[session.Speed]}"
                      + (session.Paused ? "  PAUSED" : "") + (session.Over ? (st.U16(Seg.G, 0x366) != 0 ? "  YOU WON" : "  GAME OVER") : "");
        message.Text = lastMessage;
    }

    public override void _UnhandledInput(InputEvent ev)
    {
        if (session == null) return;
        if (ev is InputEventMouseButton mb && mb.Pressed)
        {
            int a = (int)(mb.Position.X / Cell) + originA, b = (int)(mb.Position.Y / Cell) + originB;
            if (yardMap)
            {
                YardClick(mb.Position);
                return;
            }
            if (mb.Position.Y >= Rows * Cell || a >= MapRenderer.Width(view)) return;
            var st = session.St;
            int target = st.U16(Seg.G, 0x105e);
            if (target == 0xa) Commands.ExchangeClick(st, view, a, b);          // Exchange: pick the ant to become
            else if (st.U16(Seg.G, 0xa06) == 1 || target == 0xb)
            {
                if (view == 1) Commands.SpiderClick(st, a, b, mb.ButtonIndex == MouseButton.Right ? 1 : 0);
            }
            else if (mb.ButtonIndex == MouseButton.Left)
            {
                if (mb.ShiftPressed) ActOn(a, b);
                else session.WalkTo(view, a, b);
            }
            else if (mb.ButtonIndex == MouseButton.Right)
                session.WalkTo(view, a, b, dig: true);
        }
        else if (ev is InputEventKey k && k.Pressed && !k.Echo)
        {
            switch (k.Keycode)
            {
                case Key.Key1: SetView(1); break;
                case Key.Key2: SetView(2); break;
                case Key.Key3: SetView(3); break;
                case Key.Left: Scroll(-4, 0); break;
                case Key.Right: Scroll(4, 0); break;
                case Key.Up: Scroll(0, -4); break;
                case Key.Down: Scroll(0, 4); break;
                case Key.F: follow = true; break;
                case Key.Space: session.Paused = !session.Paused; break;
                case Key.Equal or Key.KpAdd: session.Speed++; break;
                case Key.Minus or Key.KpSubtract: session.Speed--; break;
                // the yellow ant's menu commands (f_76cb9)
                case Key.R: Commands.Command(session.St, k.ShiftPressed ? 2 : 1); break;      // recruit 5 / 10
                case Key.E: Commands.Command(session.St, k.ShiftPressed ? 5 : 4); break;      // release half / all
                case Key.X: Commands.Command(session.St, 6); break;                           // exchange (then click)
                case Key.A: Commands.Command(session.St, 7); break;                           // alarm trail on / off
                case Key.H: Commands.Command(session.St, 8); break;                           // dig a hole (a queen founds a nest)
                case Key.B: Commands.Command(session.St, 9); break;                           // start brood (a queen in the nest)
                case Key.C: Commands.Command(session.St, 0xa); break;                         // the spider: chase (then click)
                case Key.U: Commands.Command(session.St, k.ShiftPressed ? 0xc : 0xb); break;  // the spider: hunt / lash out
                case Key.Y: yardMap = !yardMap && session.St.U16(Seg.G, 0xeac) == 2; break;  // the yard map (Full Game)
                case Key.Escape: yardMap = false; break;
                case Key.N: Restart(1); break;
                case Key.M: Restart(2); break;
            }
        }
    }

    /// <summary>Walk to the cell and act on it (mode 1: pick up / drop, as the original's click on a cell next to
    /// the yellow ant does).</summary>
    void ActOn(int a, int b)
    {
        session.WalkTo(view, a, b);
        session.St.Set16(Seg.G, 0xa8e, 1);
    }

    void Restart(int mode)
    {
        session.NewGame(mode);
        lastMessage = "";
        SetView(session.Yellow.view);
    }

    void SetView(int v)
    {
        view = v;
        session.St.Set16(Seg.G, 0x32e, v);                    // the view on screen
        follow = session.Yellow.view == v;
        Clamp();
    }

    void Scroll(int da, int db)
    {
        follow = false;
        originA += da;
        originB += db;
        Clamp();
    }
}
