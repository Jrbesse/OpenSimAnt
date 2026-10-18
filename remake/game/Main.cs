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
            else if (arg == "--history") history = true;
            else if (arg == "--panels") panels = true;
        session = new GameSession(dir);
        session.NewGame(1);
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--ticks="))                                 // run the game ahead (for checking a build)
                for (int t = int.Parse(arg["--ticks=".Length..]); t > 0 && !session.Over; t--) session.Step();
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
            else if (e.Name == "sound" && e.Args.Length > 0 && e.Args[0] is int sfx && sfx < 57
                     && session.St.U16(Seg.T, 0x7ac) != 0)
                PlaySound(sfx);
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

    // ------------------------------------------------------------------------------- the History window (simple)
    // World.History samples ten values every 64 ticks into 64-entry rings (G:04F4 the next slot, T:0828 how
    // many are valid). The original's window scales and draws them (SIM_NOTES "History Window"); this plots
    // the populations and food stores with auto-scaling until that screen is built.
    static readonly (int ring, int str, uint colour)[] HistorySeries =
    {
        (0x516, 0, 0xff202020u), (0x5a0, 5, 0xffd03030u), (0x626, 1, 0xff6060ffu), (0x6ae, 6, 0xffff9020u),
    };
    bool history;
    Label historyLabel;

    void DrawHistory(uint[] dst, int w)
    {
        var st = session.St;
        const int X0 = 8, Y0 = 250, GW = 384, GH = 180;
        for (int y = 0; y < GH; y++)
            for (int x = 0; x < GW; x++)
                dst[(Y0 + y) * w + X0 + x] = (x == 0 || y == GH - 1) ? 0xff000000u : 0xffe8e8d8u;
        int n = Math.Clamp(st.S16(Seg.T, 0x828), 0, 64);
        int start = (st.U8(Seg.G, 0x4f4) - n) & 0x3f;
        int max = 10;
        foreach (var (ring, _, _) in HistorySeries)
            for (int i = 0; i < n; i++) max = Math.Max(max, st.S16(Seg.G, ring + 2 * ((start + i) & 0x3f)));
        foreach (var (ring, _, colour) in HistorySeries)
        {
            int px = -1, py = 0;
            for (int i = 0; i < n; i++)
            {
                int v = Math.Max(0, st.S16(Seg.G, ring + 2 * ((start + i) & 0x3f)));
                int x = 1 + i * (GW - 2) / 63, y = GH - 2 - v * (GH - 4) / max;
                if (px >= 0)
                    for (int k = 0; k <= 16; k++)
                    {
                        int lx = px + (x - px) * k / 16, ly = py + (y - py) * k / 16;
                        dst[(Y0 + ly) * w + X0 + lx] = colour;
                        dst[(Y0 + ly + 1) * w + X0 + lx] = colour;
                    }
                px = x;
                py = y;
            }
        }
        if (historyLabel == null)
        {
            historyLabel = new Label { Position = new Vector2(X0 + 4, Y0 - 16) };
            historyLabel.AddThemeFontSizeOverride("font_size", 10);
            status.GetParent().AddChild(historyLabel);
        }
        var names = session.Files.Strings(1050) ?? new string[10];
        historyLabel.Text = string.Join("   ", HistorySeries.Select(s => (s.str < names.Length ? names[s.str] : "?") + " (" + ColourName(s.colour) + ")"))
                            + $"   top {max}";
        historyLabel.Visible = true;
    }

    static string ColourName(uint c) => c switch
    {
        0xff202020u => "black", 0xffd03030u => "red", 0xff6060ffu => "blue", _ => "orange",
    };

    // ------------------------------------------------------------------------------- colony controls (simple)
    // The Behavior / Caste Control triangles (windows 18 / 19, Panels): weights G:049E.. (forage apex, dig
    // bottom left, nurse bottom right) and G:0482.. (breeders, workers, soldiers), each summing to 0xFFFF.
    // The geometry is the shell's own (the original takes it from the layout items 0x120D / 0x130D).
    static readonly (int left, int top, int right, int bottom) BehaviorRect = (24, 40, 168, 164), CasteRect = (24, 236, 168, 360);
    bool panels;
    Label[] panelLabels;

    static void Line(uint[] img, int w, int x0, int y0, int x1, int y1, uint c)
    {
        int n = Math.Max(Math.Abs(x1 - x0), Math.Abs(y1 - y0));
        for (int k = 0; k <= n; k++)
            img[(y0 + (n == 0 ? 0 : (y1 - y0) * k / n)) * w + x0 + (n == 0 ? 0 : (x1 - x0) * k / n)] = c;
    }

    void DrawTriangle(uint[] dst, int w, (int left, int top, int right, int bottom) r, int values, int tri, int point)
    {
        var st = session.St;
        for (int y = r.top - 16; y < r.bottom + 20; y++)
            for (int x = r.left - 16; x < r.right + 16; x++)
                dst[y * w + x] = 0xffe8e8d8u;
        int apex = r.left + (r.right - r.left) / 2;
        Line(dst, w, apex, r.top, r.left, r.bottom, 0xff000000u);
        Line(dst, w, r.left, r.bottom, r.right, r.bottom, 0xff000000u);
        Line(dst, w, r.right, r.bottom, apex, r.top, 0xff000000u);
        Panels.Triangle(st, r, tri);
        Panels.ToPoint(st, values, tri, point);                      // f_087c7: where the marker sits
        int mx = st.U16(Seg.G, point), my = st.U16(Seg.G, point + 2);
        for (int y = my - 2; y <= my + 2; y++)
            for (int x = mx - 2; x <= mx + 2; x++)
                if (x > 0 && y > 0 && x < w && y < Rows * Cell) dst[y * w + x] = 0xffd02020u;
    }

    void DrawPanels(uint[] dst, int w)
    {
        DrawTriangle(dst, w, BehaviorRect, 0x49e, 0x3816, 0x358);
        DrawTriangle(dst, w, CasteRect, 0x482, 0x3822, 0x22e);
        if (panelLabels == null)
        {
            var spots = new (string text, int x, int y)[]
            {
                ("Forage", 76, 20), ("Dig", 12, 166), ("Nurse", 140, 166),
                ("Breed", 78, 216), ("Work", 10, 362), ("Fight", 140, 362),
            };
            panelLabels = spots.Select(s => new Label { Text = s.text, Position = new Vector2(s.x, s.y) }).ToArray();
            foreach (var l in panelLabels)
            {
                l.AddThemeFontSizeOverride("font_size", 10);
                l.AddThemeColorOverride("font_color", new Color(0, 0, 0));
                status.GetParent().AddChild(l);
            }
        }
        foreach (var l in panelLabels) l.Visible = true;
    }

    bool PanelClick(Vector2 p)
    {
        if (!panels) return false;
        var st = session.St;
        foreach (var (r, values, tri, point, behaviour) in new[] { (BehaviorRect, 0x49e, 0x3816, 0x358, true), (CasteRect, 0x482, 0x3822, 0x22e, false) })
        {
            if (p.X < r.left - 8 || p.X > r.right + 8 || p.Y < r.top - 8 || p.Y > r.bottom + 8) continue;
            Panels.Triangle(st, r, tri);
            st.Set16(Seg.G, point, (int)p.X);
            st.Set16(Seg.G, point + 2, (int)p.Y);
            Panels.ToValues(st, values, tri, point);                 // f_086a1: the weights the click sets
            if (behaviour) st.Set16(Seg.G, 0x378, 0);                // f_07d07: a drag makes the jobs manual
            else
            {
                st.Set16(Seg.T, 0x7e8, 0);                           // f_07ac1: the caste mix becomes manual too
                NewGame.CasteTargets(st);                            // f_085f8: the caste targets T:07DA..
            }
            return true;
        }
        return true;                                                 // the panel covers the map: swallow the click
    }

    // ------------------------------------------------------------------------------- the Ant Info window
    /// <summary>f_67c1c(a, b, view) (window 29, map tool 0): for occupant o, caste = (o &amp; 0x78) >> 3: STR# 1100
    /// [o &amp; 7] for brood (caste 0) else STR# 1101 [caste]; STR# 1102 [the ant's state]; STR# 1103 [caste].</summary>
    string AntInfo(int a, int b)
    {
        var st = session.St;
        int o = Player.GetOcc(st, view, a, b);
        if (o < 0) return null;
        if (Movement.IsYellow(o)) return "The yellow ant (you)";
        int caste = (o & 0x78) >> 3;
        int i = view <= 1 ? Movement.SurfaceAntAt(st, a, b) : Nest.NestAntAt(st, view == 2 ? Nest.BLACK : Nest.RED, a, b, o);
        int state = i < 0 ? 0 : st.U8(Seg.SIM, Player.Ants(view).State + i);
        string Pick(int id, int k)
        {
            var l = session.Files.Strings(id);
            return l != null && k < l.Length ? l[k] : $"{id}[{k}]";
        }
        string kind = caste == 0 ? Pick(1100, o & 7) : Pick(1101, caste);
        string colour = (o & 0x80) != 0 ? "Red" : "Black";
        return $"{colour} {kind}: {Pick(1102, state)}, carrying {Pick(1103, caste)}";
    }

    // ------------------------------------------------------------------------------- sound effects
    readonly Dictionary<int, AudioStreamWav> sfxCache = new();
    readonly List<AudioStreamPlayer> players = new();
    bool muted;

    void PlaySound(int n)
    {
        if (muted) return;
        if (!sfxCache.TryGetValue(n, out var stream))
        {
            var pcm = session.Files.SoundEffect(n);
            stream = pcm == null || pcm.Length == 0 ? null : new AudioStreamWav
            {
                Format = AudioStreamWav.FormatEnum.Format8Bits,
                MixRate = Sounds.SampleRate,
                Stereo = false,
                Data = (byte[])(Array)pcm,
            };
            sfxCache[n] = stream;
        }
        if (stream == null) return;
        var p = players.FirstOrDefault(x => !x.Playing);
        if (p == null)
        {
            if (players.Count >= 6) return;
            p = new AudioStreamPlayer { VolumeDb = -6 };
            AddChild(p);
            players.Add(p);
        }
        p.Stream = stream;
        p.Play();
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

    // ------------------------------------------------------------------------------- the Map window (overview)
    const int OvScale = 2;
    bool overview = true;

    int OvX => Cols * Cell - MapRenderer.Width(view) * OvScale - 4;

    void DrawOverview(uint[] dst, int w)
    {
        var st = session.St;
        int mw = MapRenderer.Width(view), x0 = OvX, y0 = 4;
        for (int b = 0; b < MapRenderer.Height; b++)
            for (int a = 0; a < mw; a++)
            {
                uint c = session.Art.Palette[MapRenderer.MapColour(st, view, a, b)];
                bool frame = (a == originA || a == originA + Cols - 1) && b >= originB && b < originB + Rows
                             || (b == originB || b == originB + Rows - 1) && a >= originA && a < originA + Cols;
                if (frame) c = 0xffffff40u;
                for (int dy = 0; dy < OvScale; dy++)
                    for (int dx = 0; dx < OvScale; dx++)
                        dst[(y0 + b * OvScale + dy) * w + x0 + a * OvScale + dx] = c;
            }
    }

    bool OverviewClick(Vector2 p)
    {
        if (!overview) return false;
        int a = (int)(p.X - OvX) / OvScale, b = (int)(p.Y - 4) / OvScale;
        if (p.X < OvX || p.Y < 4 || a >= MapRenderer.Width(view) || b >= MapRenderer.Height) return false;
        follow = false;
        originA = a - Cols / 2;
        originB = b - Rows / 2;
        Clamp();
        return true;
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
        if (overview && !yardMap) DrawOverview(argb, w);
        if (history && !yardMap) DrawHistory(argb, w);
        else if (historyLabel != null) historyLabel.Visible = false;
        if (panels && !yardMap) DrawPanels(argb, w);
        else if (panelLabels != null) foreach (var l in panelLabels) l.Visible = false;
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
                      + $"  health {st.S16(Seg.G, 0xf78)}  colony {st.S16(Seg.G, 0x10be)}  speed {SpeedNames[session.Speed]}  jobs {(st.U16(Seg.G, 0x378) == 1 ? "auto" : "manual")}"
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
            if (OverviewClick(mb.Position)) return;
            if (mb.Position.X < 190 && PanelClick(mb.Position)) return;
            if (mb.Position.Y >= Rows * Cell || a >= MapRenderer.Width(view)) return;
            var st = session.St;
            if (mb.CtrlPressed)                                                 // the Ant Info tool
            {
                lastMessage = AntInfo(a, b) ?? "";
                return;
            }
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
                case Key.Tab: overview = !overview; break;                                 // the Map window
                case Key.S: muted = !muted; break;                                         // sound effects on / off
                case Key.G: history = !history; break;                                     // the History graph
                case Key.P: panels = !panels; break;                                       // the colony controls
                case Key.O: session.St.Set16(Seg.G, 0x378, session.St.U16(Seg.G, 0x378) == 1 ? 0 : 1); break;   // auto / manual jobs
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
