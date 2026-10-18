using Godot;
using Formica.Data;
using Formica.Sim;

namespace Formica.Game;

/// <summary>
/// The playable shell, laid out like the original's 640 x 480 screen from its window layouts (UiArt, Layouts):
/// the Edit window (layout 0: the tool strip, bitmap 15000, a 22 x 21 cell map of 16 px, the health bars) and
/// the Map window (layout 1: the whole map at 4 px per cell, the toolbar, bitmap 14000, the population report).
/// Windows move by their caption and come to the front on a click. Status lines sit below them.
///
/// Edit window: left click walks the yellow ant there (with Shift: acts on the cell, picking up / dropping;
/// right click: digs its way). Keys: 1 / 2 / 3 the surface / black nest / red nest, arrow keys scroll, F follows
/// the yellow ant, Space pauses, + / - change the speed, N a new Quick Game, M a new Full Game.
/// Commands: R / Shift+R recruit 5 / 10, E / Shift+E release half / all, X exchange (then click an ant, or
/// the spider), A alarm trail, H dig a hole, B start brood, C chase (as the spider, then click), U / Shift+U
/// hunt / lash out. remake/README.md lists every control.
/// </summary>
public partial class Main : Node2D
{
    const int ScreenW = 640, ScreenH = 480, Cell = 16;
    const int EditWin = 0, MapWin = 1;
    // the Edit window's map: G:10E0 x G:10DE = 22 x 21 cells (the start-up values), item 4 of layout 0
    const int Cols = 22, Rows = 21;
    // layout item indices (the ids repeat in layout 0, so the shell matches on the index)
    const int EditMapItem = 4, MapMapItem = 2;
    static readonly string[] SpeedNames = { "slow", "medium", "fast" };
    static readonly string[] ViewNames = { "Yard", "Surface", "Black Nest", "Red Nest" };
    static readonly string[] Scents = { "alarm", "black nest marker", "black trail", "red nest marker", "red trail" };

    GameSession session;
    UiArt ui;
    BitmapFont font;
    Sprite2D screen;
    Image image;
    ImageTexture texture;
    uint[] argb, mapBuf;
    byte[] rgba;
    Label status, message;
    int view = 1, originA, originB;
    bool follow = true, help, antInfoArmed;
    string lastMessage = "";
    string screenshot;
    int frames;

    // the window stack (last = front) and each window's offset from its layout position
    readonly List<int> zOrder = new() { MapWin, EditWin };
    readonly Dictionary<int, (int dx, int dy)> offsets = new() { [EditWin] = (0, 0), [MapWin] = (0, 0), [BehaviorWin] = (0, 0), [CasteWin] = (0, 0), [HistoryWin] = (0, 0), [YardWin] = (0, 0) };
    int dragWin = -1;
    Vector2 dragFrom;
    (int dx, int dy) dragOrig;

    public override void _Ready()
    {
        var dir = FindGameDir();
        var layer = new CanvasLayer();
        AddChild(layer);
        status = new Label { Position = new Vector2(4, 384), Size = new Vector2(632, 16) };
        message = new Label { Position = new Vector2(4, 400), Size = new Vector2(632, 16) };
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
            else if (arg == "--history") Front(HistoryWin);
            else if (arg == "--panels") { Front(BehaviorWin); Front(CasteWin); }
            else if (arg == "--help-overlay") help = true;
            else if (arg == "--map-front") Front(MapWin);
        session = new GameSession(dir);
        var args = OS.GetCmdlineUserArgs();
        session.NewGame(args.Contains("--full") ? 2 : args.Contains("--experimental") ? 3 : 1);
        if (screenshot == null || args.Contains("--title")) modal = TitleWin;    // the title, then Select a Game
        else if (args.Contains("--select")) modal = SelectWin;
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--ticks="))                                 // run the game ahead (for checking a build)
                for (int t = int.Parse(arg["--ticks=".Length..]); t > 0 && !session.Over; t--) session.Step();
        ui = new UiArt(session.Files, session.Art);
        if (OS.GetCmdlineUserArgs().Contains("--efficiency")) OpenEfficiency();
        if (OS.GetCmdlineUserArgs().Contains("--popup")) OpenPopup(200, 150);
        if (OS.GetCmdlineUserArgs().Contains("--yard")) OpenYard(false);
        if (OS.GetCmdlineUserArgs().Contains("--scent-menu")) OpenScentMenu();
        if (OS.GetCmdlineUserArgs().Contains("--trails")) session.St.Set16(Seg.DS, 0x2994, 1);
        if (OS.GetCmdlineUserArgs().Contains("--report")) popReport = true;
        if (OS.GetCmdlineUserArgs().Contains("--exp-menu")) ExperimentalMenu();
        if (OS.GetCmdlineUserArgs().Contains("--save-prompt")) { selectMidGame = true; Replace(1); }
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--message=") && session.Files.Strings(int.Parse(arg["--message=".Length..])) is { } box)
                OpenMessageBox(box);                                        // --message=<STR# id>: show a message box
        if (OS.GetCmdlineUserArgs().Contains("--ant-info")) { var (_, ya, yb) = session.Yellow; SetView(session.Yellow.view); CenterOnYellow(); OpenAntInfo(ya, yb); }
        if (OS.GetCmdlineUserArgs().Contains("--strat")) session.St.Set16(Seg.G, 0x35c, 2);
        font = ui.Font(2);
        argb = new uint[ScreenW * ScreenH];
        mapBuf = new uint[Cols * Cell * Rows * Cell];
        rgba = new byte[argb.Length * 4];
        image = Image.CreateEmpty(ScreenW, ScreenH, false, Image.Format.Rgba8);
        texture = ImageTexture.CreateFromImage(image);
        screen = new Sprite2D { Texture = texture, Centered = false };
        AddChild(screen);
        MoveChild(screen, 0);
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
            OpenYard(true);
        }
        if (!session.Over && !yardChoose && modal < 0 && session.Advance(delta) > 0) balloonsNow.Clear();
        ToolPoll();
        ToolHold(delta);
        DrainEffects();
        if (follow) CenterOnYellow();
        Redraw();
        ShowBalloons();
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
                if (e.Name == "message_box" && lines != null && screenshot == null) OpenMessageBox(lines);
            }
            else if (e.Name == "sound" && e.Args.Length > 0 && e.Args[0] is int sfx && sfx < 57
                     && session.St.U16(Seg.T, 0x7ac) != 0)
                PlaySound(sfx);
            else if (e.Name == "info" && e.Args.Length >= 2)                // the Ant Info tool (f_2f8fc)
                OpenAntInfo((int)e.Args[0], (int)e.Args[1]);
            else if (e.Name == "balloon" && e.Args.Length >= 5 && e.Args[4] is ValueTuple<int, int> line)
                balloonsNow[(int)e.Args[3]] = ((int)e.Args[0], (int)e.Args[1], (int)e.Args[2], BalloonText(line.Item1, line.Item2));
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

    // ------------------------------------------------------------------------------- windows
    (int dx, int dy) Off(int win) => offsets[win];

    /// <summary>Item `index` of window `win`'s layout, on screen (moved with the window).</summary>
    (int l, int t, int r, int b) ItemRect(int win, int index)
    {
        var (l, t, r, b) = ui.Layouts[win].Items[index].Rect;
        var (dx, dy) = Off(win);
        return (l + dx, t + dy, r + dx, b + dy);
    }

    (int l, int t, int r, int b) WindowRect(int win)
    {
        var (l, t, r, b) = ui.Layouts[win].Rect;
        var (dx, dy) = Off(win);
        return (l + dx, t + dy, r + dx, b + dy);
    }

    static bool Inside((int l, int t, int r, int b) rc, Vector2 p) => p.X >= rc.l && p.X < rc.r && p.Y >= rc.t && p.Y < rc.b;

    void Front(int win)
    {
        zOrder.Remove(win);
        zOrder.Add(win);
    }

    int WindowAt(Vector2 p)
    {
        for (int i = zOrder.Count - 1; i >= 0; i--)
            if (Inside(WindowRect(zOrder[i]), p)) return zOrder[i];
        return -1;
    }

    /// <summary>The window's caption item (kind "caption"), on screen.</summary>
    (int l, int t, int r, int b) CaptionRect(int win)
    {
        var items = ui.Layouts[win].Items;
        int i = items.FindIndex(it => it.Kind == "caption");
        return i < 0 ? (0, 0, 0, 0) : ItemRect(win, i);
    }

    // ------------------------------------------------------------------------------- the Edit window (layout 0)
    // Tool strip items (layout 0 indices; names from its help overlay 15001): 5 MAP (open the Map window), 6 help,
    // 7 the Experimental menu, 8 / 9 / 10 surface / black nest / red nest, 11..14 go to the yellow ant / the
    // spider / the black queen / the red queen, 15 pause, 16 the scent overlay menu, 17..19 the health bars
    // (yellow ant, black colony, red colony).
    void DrawEditWindow(UiArt.Canvas c)
    {
        var st = session.St;
        var (dx, dy) = Off(EditWin);
        string title = ViewNames[view] + (st.U16(Seg.T, 0x7be) < 5 ? " (" + Scents[st.U16(Seg.T, 0x7be)] + ")" : "");
        ui.DrawWindow(c, EditWin, dx, dy, title, new[] { 15001 });
        var win = c.Clip(WindowRect(EditWin).l, WindowRect(EditWin).t, WindowRect(EditWin).r, WindowRect(EditWin).b);
        var m = ItemRect(EditWin, EditMapItem);
        int w = Cols * Cell, h = Rows * Cell;
        int cols = Math.Min(Cols, MapRenderer.Width(view));
        Array.Fill(mapBuf, 0xff000000u);
        MapRenderer.Render(st, session.Art, view, originA, originB, originA + cols, originB + Rows, mapBuf, w);
        if (view == 1)
            SpiderRenderer.Draw(st, session.Files, session.Art, mapBuf, w, h, originA * Cell, originB * Cell, SpiderRenderer.FangJitter(st));
        win.Clip(m.l, m.t, m.r, m.b).Blit(mapBuf, w, h, m.l, m.t);
        if (session.Paused)                                                       // the PAUSE button while paused (G:047E)
        {
            var pr = ItemRect(EditWin, 15);
            win.Invert(pr.l, pr.t, pr.r, pr.b);
        }
        // the health bars: the yellow ant G:0F78, the black colony G:10BE, the red colony G:01FE (out of 100)
        var colours = new[] { session.Art.Palette[1], session.Art.Palette[15], session.Art.Palette[3] };
        var values = new[] { st.S16(Seg.G, 0xf78), st.S16(Seg.G, 0x10be), st.S16(Seg.G, 0x1fe) };
        for (int i = 0; i < 3; i++)
            UiArt.VGauge(win, ItemRect(EditWin, 17 + i), values[i] / 100.0, colours[i]);
        if (help)
        {
            var it = ui.Layouts[EditWin].Items.First(x => x.Bitmap == 15001);
            ui.DrawBitmap(win, 15001, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    void EditWindowClick(int index, InputEventMouseButton mb)
    {
        var st = session.St;
        switch (index)
        {
            case EditMapItem: EditMapClick(mb); break;
            case 5:                                                                  // MAP: open / close the Map window
                if (zOrder.Contains(MapWin)) zOrder.Remove(MapWin);
                else Front(MapWin);
                break;
            case 6: help = !help; break;
            case 7: ExperimentalMenu(); break;
            case 8: SetView(1); break;
            case 9: SetView(2); break;
            case 10: SetView(3); break;
            case 11: SetView(session.Yellow.view); follow = true; break;
            case 12:                                                                 // the spider G:0F12 / G:0F34 (1/16 cell)
                if (st.U16(Seg.G, 0xf0c) == 0) { lastMessage = "There is no spider."; break; }
                SetView(1);
                CenterOn(st.S16(Seg.G, 0xf12) >> 4, st.S16(Seg.G, 0xf34) >> 4);
                break;
            case 13: GotoQueen(2); break;
            case 14: GotoQueen(3); break;
            case 15: session.Paused = !session.Paused; break;
            case 16: OpenScentMenu(); break;
        }
    }

    void EditMapClick(InputEventMouseButton mb)
    {
        var m = ItemRect(EditWin, EditMapItem);
        int a = (int)(mb.Position.X - m.l) / Cell + originA, b = (int)(mb.Position.Y - m.t) / Cell + originB;
        if (a >= MapRenderer.Width(view) || b >= MapRenderer.Height) return;
        var st = session.St;
        if (mb.CtrlPressed || antInfoArmed)                                        // the Ant Info tool
        {
            antInfoArmed = false;
            OpenAntInfo(a, b);
            return;
        }
        if (st.U16(Seg.G, 0xeac) == 3)                                             // Experimental: the map tools
        {
            if (mb.ButtonIndex == MouseButton.Left) ToolPress(a, b, mb);
            return;
        }
        int target = st.U16(Seg.G, 0x105e);
        // f_74fe0: a left press on the player itself, with the button still held (f_0122c → f_20262), opens its
        // menu (f_2f8e8 → f_67e93) at the mouse
        if (target != 0xa && target != 0xb && mb.ButtonIndex == MouseButton.Left && view == session.Yellow.view
            && DebugCommands.PlayerAt(st, view, a, b) == 1)
        {
            OpenPopup((int)mb.Position.X, (int)mb.Position.Y);
            return;
        }
        if (target == 0xa) Commands.ExchangeClick(st, view, a, b);                  // Exchange: pick the ant to become
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

    /// <summary>Go to the colony's queen in its nest: the first cell whose occupant has caste 12 (o &amp; 0x78 ==
    /// 0x60) in that nest's colour.</summary>
    void GotoQueen(int nest)
    {
        var st = session.St;
        var n = nest == 2 ? NestGrid.BLACK : NestGrid.RED;
        for (int a = 0; a < 64; a++)
            for (int b = 0; b < 64; b++)
            {
                int o = st.Grid(n.Cells, a, b);
                if (o != 0 && o < 0xfe && (o & 0x78) == 0x60 && ((o & 0x80) != 0) == (nest == 3))
                {
                    SetView(nest);
                    CenterOn(a, b);
                    return;
                }
            }
        lastMessage = nest == 2 ? "The black colony has no queen." : "The red colony has no queen.";
    }

    void CycleScent()
    {
        int m = session.St.U16(Seg.T, 0x7be);
        session.St.Set16(Seg.T, 0x7be, m == 0xffff ? 0 : m >= 4 ? 0xffff : m + 1);
        int now = session.St.U16(Seg.T, 0x7be);
        lastMessage = now < 5 ? "Scent view: " + Scents[now] : "Scent view off";
    }

    // ------------------------------------------------------------------------------- the Map window (layout 1)
    // Toolbar items (layout 1 indices = item id - 0x100; names from its help overlay 14001): 5..8 map views (Yard,
    // Surface, Black Nest, Red Nest), 9..13 scent layers, 14 Show Trails, 15 Behavior Control, 16 Center on
    // Yellow, 17 Caste Control, 18 the Mystery Button, 19 History Display, 20 Efficiency Score, 21 Ant Info,
    // 22 / 23 the Experimental menu, 24..30 the population report. Its content is T:07C8: 1..3 a view, 4..8 a
    // scent map (black nest marker, black trail, red nest marker, red trail, alarm); 0 (the yard) is not drawn
    // here (f_6efd6 calls the fatal-error routine for it).
    static readonly int[] ScentButtons = { 4, 5, 8, 6, 7 };              // items 9..13 → T:07C8

    int MapContent => session.St.U16(Seg.T, 0x7c8);

    // Show Trails (0x10E, DS:2994): f_6efd6 then redraws only the ants over the image it keeps (G:10E2), so their
    // paths stay on the map until it is drawn afresh (here: when the option or the view changes).
    readonly uint[] trailImage = new uint[128 * 64];
    int trailView = -1;

    int MapView => MapContent is >= 1 and <= 3 ? MapContent : 1;

    /// <summary>The map's pixel scale and its left edge inside the map item: 4 x 4 px per cell (G:3856 x G:3858 at
    /// 640 x 480); a nest is 64 cells wide and is centred in the 128-cell area (how the original places it is
    /// not traced).</summary>
    (int x0, int y0) MapOrigin()
    {
        var m = ItemRect(MapWin, MapMapItem);
        return (m.l + (128 - MapRenderer.Width(MapView)) * 2, m.t);
    }

    void DrawMapWindow(UiArt.Canvas c)
    {
        var st = session.St;
        var (dx, dy) = Off(MapWin);
        int content = MapContent;
        string title = content >= 4 && content <= 8 ? "Map: " + Scents[MapRenderer.ScentMode(content)] : "Map: " + ViewNames[MapView];
        ui.DrawWindow(c, MapWin, dx, dy, title, new[] { 14001 });
        var wr = WindowRect(MapWin);
        var win = c.Clip(wr.l, wr.t, wr.r, wr.b);
        var m = ItemRect(MapWin, MapMapItem);
        var area = win.Clip(m.l, m.t, m.r, m.b);
        area.Fill(m.l, m.t, m.r, m.b, session.Art.Palette[13]);
        int mv = MapView, mw = MapRenderer.Width(mv);
        var (x0, y0) = MapOrigin();
        bool trails = st.U16(Seg.DS, 0x2994) != 0 && content is >= 1 and <= 3;
        if (trails && trailView != mv)                                                       // start from the current map
        {
            trailView = mv;
            for (int b = 0; b < MapRenderer.Height; b++)
                for (int a = 0; a < mw; a++) trailImage[b * 128 + a] = session.Art.Palette[MapRenderer.MapColour(st, mv, a, b)];
        }
        if (!trails) trailView = -1;
        for (int b = 0; b < MapRenderer.Height; b++)
            for (int a = 0; a < mw; a++)
            {
                uint col;
                if (content >= 4 && content <= 8)
                {
                    // f_6eb66: v ? 0x10 + (v >> 5) : 0x0B; the 0x10.. colours are the driver's dithers (not decoded):
                    // drawn as a ramp from light to dark
                    int v = MapRenderer.Scent(st, MapRenderer.ScentMode(content), a, b);
                    col = v == 0 ? session.Art.Palette[11] : Ramp(v);
                }
                else if (trails)
                {
                    // Show Trails: only cells with an ant are painted, over the image kept from before
                    if (Player.GetOcc(st, mv, a, b) > 0) trailImage[b * 128 + a] = session.Art.Palette[MapRenderer.MapColour(st, mv, a, b)];
                    col = trailImage[b * 128 + a];
                }
                else col = session.Art.Palette[MapRenderer.MapColour(st, mv, a, b)];
                area.Fill(x0 + a * 4, y0 + b * 4, x0 + a * 4 + 4, y0 + b * 4 + 4, col);
            }
        if (mv == 1 && content == 1 && !trails)
        {
            // f_6f505: the small spider, bitmap 1100 + G:1004 at its cell x 4 - 3, while G:0F0C != 0; f_6f5e1: while
            // T:0C3E the human's sneaker 1200 + T:0C30 at (G:03E0, G:046A) x 4, and while mowing (T:0C28 3 or 4) the
            // mower 1210 + (T:0C30 & 1) at (G:0470, G:047A) x 4
            if (st.U16(Seg.G, 0xf0c) != 0)
                ui.DrawBitmap(area, 1100 + st.U16(Seg.G, 0x1004), x0 + (st.S16(Seg.G, 0xf12) >> 4) * 4 - 3, y0 + (st.S16(Seg.G, 0xf34) >> 4) * 4 - 3);
            if (st.U16(Seg.T, 0xc3e) != 0)
                ui.DrawBitmap(area, 1200 + st.U16(Seg.T, 0xc30), x0 + st.S16(Seg.G, 0x3e0) * 4, y0 + st.S16(Seg.G, 0x46a) * 4);
            if (st.U16(Seg.T, 0xc28) is 3 or 4)
                ui.DrawBitmap(area, 1210 + (st.U16(Seg.T, 0xc30) & 1), x0 + st.S16(Seg.G, 0x470) * 4, y0 + st.S16(Seg.G, 0x47a) * 4);
        }
        if (mv == view)                                                                     // the Edit window's view
        {
            int l = x0 + originA * 4, t = y0 + originB * 4;
            area.Frame(l, t, l + Cols * 4, t + Rows * 4, 0xffffff40u);
        }
        if (st.U16(Seg.G, 0xeac) == 3)                                                     // f_67010: the tool's icon
        {
            var ti = ItemRect(MapWin, 23);
            ui.DrawBitmap(win, 5100 + Math.Clamp(st.U16(Seg.G, 0x104c), 0, 7), ti.l, ti.t);
        }
        // the population report f_6eea5: counts 0x119 / 0x11A, gauges 0x11B black health (G:10BE / 100), 0x11C red
        // health (G:01FE / 100, 0 without red ants), 0x11D / 0x11E each population / max(1, black, red)
        int black = st.U16(Seg.G, 0x330), red = st.U16(Seg.G, 0x350), most = Math.Max(1, Math.Max(black, red));
        var r1 = ItemRect(MapWin, 25);
        var r2 = ItemRect(MapWin, 26);
        win.Fill(r1.l, r1.t, r1.r, r1.b, UiArt.White);
        win.Fill(r2.l, r2.t, r2.r, r2.b, UiArt.White);
        ui.DrawText(win, 0, 0, r1.l, r1.t - 1, r1.r, r1.b + 1, black.ToString());
        ui.DrawText(win, 0, 0, r2.l, r2.t - 1, r2.r, r2.b + 1, red.ToString());
        UiArt.Gauge(win, ItemRect(MapWin, 27), st.S16(Seg.G, 0x10be) / 100.0);
        UiArt.Gauge(win, ItemRect(MapWin, 28), red == 0 ? 0 : st.S16(Seg.G, 0x1fe) / 100.0, session.Art.Palette[3]);
        UiArt.Gauge(win, ItemRect(MapWin, 29), black / (double)most);
        UiArt.Gauge(win, ItemRect(MapWin, 30), red / (double)most, session.Art.Palette[3]);
        if (help)
        {
            var it = ui.Layouts[MapWin].Items.First(x => x.Bitmap == 14001);
            ui.DrawBitmap(win, 14001, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    static uint Ramp(int v)
    {
        int k = Math.Clamp(v >> 5, 0, 7);
        int g = 230 - k * 28;
        return 0xff000000u | ((uint)g << 16) | ((uint)(g * 3 / 4) << 8) | (uint)(g / 3);
    }

    void MapWindowClick(int index, InputEventMouseButton mb)
    {
        var st = session.St;
        switch (index)
        {
            case MapMapItem:                                                            // centre the Edit window there
            {
                var (x0, y0) = MapOrigin();
                int a = (int)(mb.Position.X - x0) / 4, b = (int)(mb.Position.Y - y0) / 4;
                if (a < 0 || a >= MapRenderer.Width(MapView) || b >= MapRenderer.Height) break;
                SetView(MapView);
                CenterOn(a, b);
                break;
            }
            case 5:                                                                      // Yard: the yard map (Full Game)
                OpenYard(false);
                break;
            case 6: case 7: case 8:
                st.Set16(Seg.T, 0x7c8, index - 5);
                SetView(index - 5);
                break;
            case >= 9 and <= 13:
            {
                int content = ScentButtons[index - 9];
                st.Set16(Seg.T, 0x7c8, MapContent == content ? view : content);
                break;
            }
            case 14:                                                                     // Show Trails: DS:2994 ^= 1 (f_6e5c0)
                st.Set16(Seg.DS, 0x2994, st.U16(Seg.DS, 0x2994) == 0 ? 1 : 0);
                break;
            case 15: ToggleWindow(BehaviorWin); break;
            case 17: ToggleWindow(CasteWin); break;
            case 16: SetView(session.Yellow.view); follow = true; break;
            case 18: DebugCommands.RandomAction(st); break;                              // the Mystery Button (f_022bc)
            case >= 24 and <= 30: popReport = true; break;                               // held: the population report
            case 19: ToggleWindow(HistoryWin); break;
            case 20: OpenEfficiency(); break;
            case 22: case 23: ExperimentalMenu(); break;
            case 21: antInfoArmed = true; lastMessage = "Ant Info: click an ant in the Edit window."; break;
        }
    }

    // ------------------------------------------------------------------------------- the yellow ant's menu
    // f_67e93 (SIM_NOTES "The yellow ant's menu and commands"): layout 32 (4504) as the spider (G:0A06 == 1), 8
    // (4502) as a queen (G:04C2 == 0x40) with T:0C24 == 0, else 7 (4500). Entries (items 2..) → f_76cb9 commands;
    // Shift on Recruit 10 gives 3 (recruit all), Alt on Hunt gives 0x0C (lash out). 0 is help (f_76eb5, UI).
    static readonly Dictionary<int, int[]> PopupCommands = new()
    {
        [7] = new[] { 1, 2, 4, 5, 6, 0 }, [8] = new[] { 8, 9, 0 }, [32] = new[] { 0xa, 0xb, 6, 0 },
        // layout 6 (6000), the scent overlay menu (f_679c0): Off, Alarm, B-Nest, B-Trail, R-Nest, R-Trail → T:07BE
        [6] = new[] { 0xffff, 0, 1, 2, 3, 4 },
        // the tools' option palettes (layouts 12..17): entry e stores e in T:07B6 + tool; 10 the Experimental menu
        [12] = new[] { 0, 1 }, [15] = new[] { 0, 1 }, [16] = new[] { 0, 1 }, [17] = new[] { 0, 1 },
        [13] = new[] { 0, 1, 2, 3, 4 }, [14] = new[] { 0, 1 }, [10] = new[] { 0 },
        [9] = new[] { 0, 1, 2, 3, 4, 5, 6, 7 }, [11] = Array.Empty<int>(),
    };
    int popup = -1, popupHover = -1;
    (int dx, int dy) popupOff;

    void OpenPopup(int x, int y)
    {
        var st = session.St;
        popup = st.U16(Seg.G, 0xa06) == 1 ? 32 : st.U16(Seg.G, 0x4c2) == 0x40 && st.U16(Seg.T, 0xc24) == 0 ? 8 : 7;
        var (l, t, r, b) = ui.Layouts[popup].Rect;
        popupOff = (Math.Clamp(x, 0, ScreenW - (r - l)) - l, Math.Clamp(y, 0, ScreenH - (b - t)) - t);
        popupHover = -1;
    }

    /// <summary>The scent overlay menu (layout 6) opens at its layout place next to its parent, the Edit window's
    /// SCENT button (item 0x0010), so it moves with that window.</summary>
    void OpenScentMenu()
    {
        popup = 6;
        popupOff = Off(EditWin);
        popupHover = -1;
    }

    void DrawPopup(UiArt.Canvas c)
    {
        ui.DrawWindow(c, popup, popupOff.dx, popupOff.dy, null);
        if (popupHover >= 2)
        {
            var (l, t, r, b) = ui.Layouts[popup].Items[popupHover].Rect;
            c.Invert(l + popupOff.dx, t + popupOff.dy, r + popupOff.dx, b + popupOff.dy);
        }
    }

    int PopupEntry(Vector2 p)
    {
        int i = ui.HitTest(popup, popupOff.dx, popupOff.dy, (int)p.X, (int)p.Y);
        return i >= 2 && i - 2 < PopupCommands[popup].Length ? i : -1;
    }

    /// <summary>Mouse events while the menu is open: the entry under the pointer is highlighted; releasing on an
    /// entry runs it (press-and-hold, or a second click); a press outside closes the menu.</summary>
    void PopupInput(InputEvent ev)
    {
        if (ev is InputEventMouseMotion mm) popupHover = PopupEntry(mm.Position);
        else if (ev is InputEventMouseButton mb && mb.ButtonIndex == MouseButton.Left)
        {
            int entry = PopupEntry(mb.Position);
            var (l, t, r, b) = ui.Layouts[popup].Rect;
            bool inside = Inside((l + popupOff.dx, t + popupOff.dy, r + popupOff.dx, b + popupOff.dy), mb.Position);
            if (mb.Pressed && (!inside || popup == 11)) popup = -1;
            else if (mb.Pressed && popup == ToolMenu && entry >= 0) ToolMenuPress(entry);
            else if (!mb.Pressed && entry >= 0)
            {
                int cmd = PopupCommands[popup][entry - 2];
                if (popup == 6)
                {
                    popup = -1;
                    session.St.Set16(Seg.T, 0x7be, cmd);
                    return;
                }
                if (popup == 10)
                {
                    popup = -1;
                    EnterExperimental();
                    return;
                }
                if (popup == ToolMenu)
                {
                    popup = -1;
                    toolHold = -1;
                    ToolChoice(cmd);
                    return;
                }
                if (popup >= 12 && popup <= 17)
                {
                    popup = -1;
                    session.St.Set8(Seg.T, 0x7b6 + optionTool, cmd);
                    return;
                }
                if (cmd == 2 && mb.ShiftPressed) cmd = 3;
                if (cmd == 0xb && mb.AltPressed) cmd = 0xc;
                popup = -1;
                if (cmd == 0) lastMessage = "Help: the original's help screens (f_76eb5) are not built yet.";
                else Commands.Command(session.St, cmd);
            }
        }
    }

    // ------------------------------------------------------------------------------- the Experimental menu, the tools
    // f_67010 (the Map toolbar's 0x117, thunk 0x2f88e) opens a pop-up above item 0x117 by the game mode G:0EAC:
    // - 1, a Quick Game: layout 10 ("EXPERIMENTAL MODE"); choosing it sets G:0EAC = 3, lifts the yellow ant off
    //   the map (f_11918), G:0A06 = 2, f_0cdb0 (the per-patch globals), a redraw and sound 2;
    // - 2, the Full Game: layout 11 ("not available in the full game");
    // - 3, Experimental: the tool palette, layout 9 (bitmap 5000; f_680a4): entries 0..6 pick the map tool G:104C
    //   (Ant Info, Barriers, Dig / Fill, Add Ants, Add Food, Drop Trails, Insecticide) through f_2f8a2, and 7
    //   (Start Game) makes it a Quick Game again (G:0EAC = 1), puts the yellow ant back on the map when the
    //   surface is shown (f_119b4 with 0xFF) and plays voice 0x2AFB. The toolbar then shows tool icon 5100 +
    //   G:104C in item 0x117 (not drawn here).
    // In the Experimental game a press on the Edit window's map runs the drag loop f_76f4a: the previous point
    // G:09FC / G:09FE starts at the cell and the tool is applied there (MapTools.ApplyTool = f_770f6); when the
    // cell under the held button changes, the previous point becomes the old cell and the tool is applied at the
    // new one; tools >= 5 are also applied on every poll (here every frame), with G:106C ^= 1, and G:0A9C counts
    // the polls. Holding a tool's entry opens its option palette (layouts 12..17 by their bitmaps 5001..5006:
    // Walls / Rocks, Dig / Fill, Black / Red, 1 / 20 pieces, the five scent maps, Spray / Stream).
    const int ToolMenu = 9;
    bool toolDrag;
    (int a, int b) toolCell;
    static readonly int[] OptionWindows = { -1, 12, 15, 16, 17, 13, 14 };
    int optionTool = -1;
    double toolHold = -1;
    (int l, int t, int r, int b) holdEntry;

    /// <summary>A press on a tool entry of the palette starts the hold timer for its options.</summary>
    void ToolMenuPress(int entry)
    {
        optionTool = entry - 2;
        toolHold = optionTool is > 0 and < 7 ? 0 : -1;
        var (l, t, r, b) = ui.Layouts[ToolMenu].Items[entry].Rect;
        holdEntry = (l + popupOff.dx, t + popupOff.dy, r + popupOff.dx, b + popupOff.dy);
    }

    /// <summary>Each frame: a tool entry held for a third of a second opens that tool's option palette beside it,
    /// with the current option (T:07B6 + tool) highlighted.</summary>
    void ToolHold(double delta)
    {
        if (toolHold < 0) return;
        if (!Input.IsMouseButtonPressed(MouseButton.Left) || popup != ToolMenu) { toolHold = -1; return; }
        toolHold += delta;
        if (toolHold < 0.33) return;
        toolHold = -1;
        session.St.Set16(Seg.G, 0x104c, optionTool);
        popup = OptionWindows[optionTool];
        var (l, t, r, b) = ui.Layouts[popup].Rect;
        popupOff = (Math.Min(holdEntry.r, ScreenW - (r - l)) - l, Math.Min(holdEntry.t, ScreenH - (b - t)) - t);
        popupHover = 2 + Math.Min(session.St.U8(Seg.T, 0x7b6 + optionTool), PopupCommands[popup].Length - 1);
    }

    void EnterExperimental()
    {
        var st = session.St;
        st.Set16(Seg.G, 0xeac, 3);
        var (v, a, b) = session.Yellow;
        Player.TakeYellow(st, v, a, b, st.U16(Seg.G, 0x4c2), st.U16(Seg.G, 0x496));      // f_11918
        st.Set16(Seg.G, 0xa06, 2);
        NewGame.ResetPatchGlobals(st);                                                  // f_0cdb0
        st.Hooks.Effect(st, "sound", 2, 0x7e);
    }

    void ToolChoice(int si)
    {
        var st = session.St;
        if (si == 7)                                                                    // Start Game
        {
            st.Set16(Seg.G, 0xeac, 1);
            if (st.U16(Seg.G, 0x32e) == 1)
            {
                var (v, a, b) = session.Yellow;
                Player.PutYellow(st, v, a, b, st.U16(Seg.G, 0x4c2), st.U16(Seg.G, 0x496), 0xff);   // f_119b4
            }
            st.Hooks.Effect(st, "voice", 0x2afb);
        }
        st.Set16(Seg.G, 0x104c, si);                                                    // f_2f8a2
    }

    /// <summary>The pop-up of f_67010, centred over the Map window's item 0x117 and 4 px above it.</summary>
    void ExperimentalMenu()
    {
        int mode = session.St.U16(Seg.G, 0xeac);
        popup = mode == 3 ? ToolMenu : mode == 2 ? 11 : 10;
        var item = ItemRect(MapWin, 23);
        var (l, t, r, b) = ui.Layouts[popup].Rect;
        int x = Math.Clamp((item.l + item.r - (r - l)) / 2, 0, ScreenW - (r - l)), y = Math.Max(0, item.t - (b - t) - 4);
        popupOff = (x - l, y - t);
        popupHover = mode == 3 ? 2 + Math.Clamp(session.St.U16(Seg.G, 0x104c), 0, 7) : -1;
    }

    static int Kbd(InputEventWithModifiers m) => (m.ShiftPressed ? 2 : 0) | (m.CtrlPressed ? 4 : 0) | (m.AltPressed ? 8 : 0);

    (int a, int b)? EditCell(Vector2 p)
    {
        var m = ItemRect(EditWin, EditMapItem);
        if (!Inside(m, p)) return null;
        int a = (int)(p.X - m.l) / Cell + originA, b = (int)(p.Y - m.t) / Cell + originB;
        return a < MapRenderer.Width(view) && b < MapRenderer.Height ? (a, b) : null;
    }

    void ToolPress(int a, int b, InputEventMouseButton mb)
    {
        var st = session.St;
        st.BiosKbd = Kbd(mb);
        st.Set16(Seg.G, 0x9fc, a);
        st.Set16(Seg.G, 0x9fe, b);
        MapTools.ApplyTool(st, a, b);
        toolDrag = true;
        toolCell = (a, b);
    }

    void ToolMove(Vector2 p, InputEventWithModifiers m)
    {
        if (EditCell(p) is not var (a, b) || (a, b) == toolCell) return;
        var st = session.St;
        st.BiosKbd = Kbd(m);
        st.Set16(Seg.G, 0x9fc, toolCell.a);
        st.Set16(Seg.G, 0x9fe, toolCell.b);
        toolCell = (a, b);
        MapTools.ApplyTool(st, a, b);
    }

    /// <summary>Each frame while the button is held: tools >= 5 apply again (pheromone, insecticide).</summary>
    void ToolPoll()
    {
        if (!toolDrag) return;
        var st = session.St;
        st.Set16(Seg.G, 0xa9c, st.U16(Seg.G, 0xa9c) + 1);
        if (st.U16(Seg.G, 0x104c) >= 5)
        {
            st.Set16(Seg.G, 0x106c, st.U16(Seg.G, 0x106c) ^ 1);
            MapTools.ApplyTool(st, toolCell.a, toolCell.b);
        }
    }

    // ------------------------------------------------------------------------------- message boxes (layouts 27 / 30)
    // f_71b1a(0, id, 1): the lines of STR# id in a box that waits for a click ("Click here to continue"); the game
    // does not run meanwhile. Which box the original picks, and the text placement, are not traced: up to four
    // lines go in layout 27, more in layout 30, centred above the "Click here" line in font 2.
    string[] boxLines;

    void OpenMessageBox(string[] lines)
    {
        boxLines = lines.Select(l => l.Replace("\\n", " ")).ToArray();      // literal backslash-n breaks, as in the balloons
        modal = lines.Length <= 4 ? 27 : 30;
    }

    void DrawMessageBox(UiArt.Canvas c)
    {
        ui.DrawWindow(c, modal, 0, 0, null);
        var w = ui.Layouts[modal];
        var click = w.Items[^1].Rect;
        var f = ui.Font(2);
        int top = w.Rect.top + 6, bottom = click.top - 2, n = boxLines.Length;
        int y = top + Math.Max(0, (bottom - top - n * f.Height) / 2);
        foreach (var line in boxLines)
        {
            ui.DrawText(c, 2, 0, w.Rect.left + 4, y, w.Rect.right - 4, y + f.Height, line);
            y += f.Height;
        }
    }

    // ------------------------------------------------------------------------------- Select a Game (layout 2)
    // The new-game dialog f_725b6 (SIM_NOTES "Player events and the game flow"): bitmap 2500, buttons 0x202 Quick
    // Game (1), 0x203 Full Game (2), 0x204 Experimental (3), 0x205 Cancel, 0x206 the Tutorial (G:0EAC = 0, not
    // ported: World.Advisor's tutorial f_0e425), 0x207 Load Game. Shown at start-up and on F2.
    const int SelectWin = 2, TitleWin = 3, AboutWin = 31;               // the title (2000 / 2001), the about box (3000 / 3001)

    bool selectMidGame;                                                      // F2: a game is running, so ask to save first

    void SelectClick(int index)
    {
        switch (index)
        {
            case 2: Replace(1); break;
            case 3: Replace(2); break;
            case 4: Replace(3); break;
            case 5: modal = -1; break;
            case 6: lastMessage = "The Tutorial is not ported yet (f_0e425)."; break;
            case 7: Replace(4); break;
        }
    }

    // ------------------------------------------------------------------------------- the save prompt (layout 33)
    // "Do you want to save / your current game / before loading a new SimAnt game?" (STR# 1800 [8..10]) with
    // DON'T SAVE, Save and Cancel (items 0x2103..0x2105) before a running game is replaced.
    const int SavePrompt = 33;
    int pendingGame = -1;                                                    // 1..3 a new game, 4 load

    void Replace(int what)
    {
        if (!selectMidGame) { Proceed(what); return; }
        pendingGame = what;
        modal = SavePrompt;
    }

    void Proceed(int what)
    {
        modal = -1;
        selectMidGame = false;
        if (what == 4) QuickLoad();
        else Restart(what);
    }

    void DrawSavePrompt(UiArt.Canvas c)
    {
        ui.DrawWindow(c, SavePrompt, 0, 0, null);
        var items = ui.Layouts[SavePrompt].Items;
        for (int i = 3; i <= 5; i++)
        {
            var (l, t, r, b) = items[i].Rect;
            c.Frame(l, t, r, b, UiArt.Black);
        }
        var lines = session.Files.Strings(1800);
        var (_, bt, _, _) = items[1].Rect;
        var (bl, _, br, _) = items[2].Rect;                                  // the wider of the two text items
        var f = ui.Font(0);
        for (int k = 0; k < 3; k++)
            ui.DrawText(c, 0, 0, bl, bt + 12 + k * (f.Height + 4), br, bt + 12 + k * (f.Height + 4) + f.Height, lines?[8 + k] ?? "");
    }

    void SavePromptClick(int index)
    {
        switch (index)
        {
            case 3: Proceed(pendingGame); break;
            case 4: QuickSave(); Proceed(pendingGame); break;
            case 5: modal = -1; selectMidGame = false; break;
        }
    }

    void QuickSave()
    {
        var path = ProjectSettings.GlobalizePath("user://quicksave.ANT");
        System.IO.File.WriteAllBytes(path, SaveFile.Save(session.St));
        lastMessage = "Saved to " + path;
    }

    // ------------------------------------------------------------------------------- the Efficiency Score (layout 24)
    // f_71576 (SIM_NOTES "The Efficiency Score window"): the rating f_70fb0 (score to G:0ADA), the colony fields
    // 0x1802..0x1805 = p[0..3] "%d%%", the universe fields 0x1806..0x1809 = p[4..7] in a Full Game, else STR#
    // 1800 [16] "N.A."; the bottom lines STR# 1800 [13] + the mode's name (STR# 1001) + [14] and the score
    // ("%ld"), or [17] / [18] in the Experimental game; the caption STR# 1010 [14]. It waits for a click (the
    // game does not run meanwhile).
    const int EfficiencyWin = 24;
    int modal = -1;
    (long score, int[] parts) efficiency;

    void OpenEfficiency()
    {
        var st = session.St;
        efficiency = Formica.Sim.Game.Rating(st);
        st.Set32(Seg.G, 0xada, efficiency.score);
        modal = EfficiencyWin;
    }

    void DrawEfficiency(UiArt.Canvas c)
    {
        var st = session.St;
        ui.DrawWindow(c, EfficiencyWin, 0, 0, null);
        var items = ui.Layouts[EfficiencyWin].Items;
        string S(int id, int k)
        {
            var l = session.Files.Strings(id);
            return l != null && k < l.Length ? l[k] : "";
        }
        void Text(int index, string text, int font = -1)
        {
            var (l, t, r, b) = items[index].Rect;
            ui.DrawText(c, font >= 0 ? font : items[index].Param & 0xff, 0, l, t, r, b, text);
        }
        var p = efficiency.parts;
        int mode = st.U16(Seg.G, 0xeac);
        for (int i = 0; i < 4; i++) Text(2 + i, $"{p[i]}%");
        for (int i = 0; i < 4; i++) Text(6 + i, mode == 2 ? $"{p[4 + i]}%" : S(1800, 16), 0);
        if (mode == 3)
        {
            Text(10, S(1800, 17), 0);
            Text(11, S(1800, 18), 0);
        }
        else
        {
            Text(10, S(1800, 13) + S(1001, mode) + S(1800, 14), 0);
            Text(11, efficiency.score.ToString(), 0);
        }
        Text(12, S(1010, 14));
    }

    // ------------------------------------------------------------------------------- the population report (layout 23)
    // f_7179d (Map toolbar 0x118, while the button is held): bitmap 14002 lists the castes (larvae, workers,
    // soldiers, males, new queens, queens); for caste i the black count G:0AEC[i] and below it the red G:0AFA[i]
    // in item 0x1702, as text from its left edge, and for i > 0 a bar from x = left + 4 x the widest digit + 2,
    // of length count x (right - that x) / the largest count of castes 1..5 (at least 1), from 1 px below the
    // line's top to 2 px above its bottom. The rows share the item's spare height (height - 12 font lines + 3,
    // in fifths, the remainder spread in steps), the last row 1 px higher. Font 2 at 640 x 480.
    bool popReport;

    void DrawPopulationReport(UiArt.Canvas c)
    {
        var st = session.St;
        const int Win = 23;
        var (dx, dy) = Off(MapWin);
        ui.DrawWindow(c, Win, dx, dy, null);
        var r = ui.Layouts[Win].Items[2].Rect;
        int left = r.left + dx, top = r.top + dy, right = r.right + dx, bottom = r.bottom + dy;
        var f = ui.Font(2);
        int digit = Enumerable.Range('0', 10).Max(ch => f.Advance(ch));
        int x0 = digit * 4 + left + 2, len = right - x0, fh = f.Height;
        int spare = bottom - top - fh * 12 + 3, extra = spare % 5, acc = 0;
        spare /= 5;
        int max = 1;
        for (int i = 1; i < 6; i++) max = Math.Max(max, Math.Max((int)st.S16(Seg.G, 0xaec + 2 * i), (int)st.S16(Seg.G, 0xafa + 2 * i)));
        int y = top;
        for (int i = 0; i < 6; i++)
        {
            acc += extra;
            int row = y;
            if (acc > 5) { row++; acc -= 5; }
            if (i == 5) row--;
            foreach (var (off, k, colour) in new[] { (0xaec, 0, UiArt.Black), (0xafa, 1, session.Art.Palette[3]) })
            {
                int v = st.S16(Seg.G, off + 2 * i), ry = row + k * fh;
                f.Draw(c.Px, c.Stride, c.B, left, ry, v.ToString(), colour);
                if (i != 0) c.Fill(x0, ry + 1, x0 + (int)((long)Math.Max(0, v) * len / max), ry + fh - 2, colour);
            }
            y = row + fh * 2 + spare;
        }
    }

    // ------------------------------------------------------------------------------- the History window (layout 21)
    // f_792d2 / f_795ec (SIM_NOTES "The History Window"): buttons 0x1503..0x150C (items 3..12, series s = item - 3)
    // toggle up to 4 series (DS:2EF0[4]); series s plots the rings of T:082A[(s & 1) * 5 + (s >> 1)] in black and
    // T:0852[...] in red (far pointers into G, the start-up values below; World.History fills the rings: 64
    // entries, G:04F4 the next slot, T:0828 how many are valid). The graph is item 0x150E (index 14): height H =
    // its height - 16 (8 px margins), width its width - 0x40. Scale: M = the largest value shown; if M * 2 < H,
    // y = bottom - v * mult with the largest mult keeping M * mult < H, else y = bottom - v / div with the
    // smallest div bringing M / div <= H. The line drawing and the x placement are not traced: points are spread
    // evenly with 32 px on each side. Item 13 shows the help overlay 16001.
    const int HistoryWin = 21, HistoryGraph = 14;
    static readonly int[] HistoryBlack = { 0x516, 0x626, 0x73c, 0x856, 0x8f0, 0x5a0, 0x6ae, 0x7ce, 0x970, 0xa0a };
    static readonly int[] HistoryRed = { 0x5a0, 0x6ae, 0x7ce, 0x856, 0xa0a, 0x516, 0x626, 0x73c, 0xa0a, 0x970 };
    readonly List<int> historySeries = new() { 0 };

    void DrawHistoryWindow(UiArt.Canvas c)
    {
        var st = session.St;
        var (dx, dy) = Off(HistoryWin);
        ui.DrawWindow(c, HistoryWin, dx, dy, null, new[] { 16001 });
        var wr = WindowRect(HistoryWin);
        var clip = c.Clip(wr.l, wr.t, wr.r, wr.b);
        foreach (int s in historySeries)
        {
            var b = ItemRect(HistoryWin, 3 + s);
            clip.Invert(b.l, b.t, b.r, b.b);
        }
        var g = ItemRect(HistoryWin, HistoryGraph);
        int n = Math.Clamp(st.S16(Seg.T, 0x828), 0, 64);
        int start = (st.U8(Seg.G, 0x4f4) - n) & 0x3f;
        int h = g.b - g.t - 16, w = g.r - g.l - 0x40, bottom = g.b - 8;
        int V(int ring, int i) => Math.Max(0, st.S16(Seg.G, ring + 2 * ((start + i) & 0x3f)));
        int max = 0;
        foreach (int s in historySeries)
        {
            int k = (s & 1) * 5 + (s >> 1);
            for (int i = 0; i < n; i++) max = Math.Max(max, Math.Max(V(HistoryBlack[k], i), V(HistoryRed[k], i)));
        }
        int mult = 1, div = 1;
        if (max * 2 < h) while (max * (mult + 1) < h) mult++;
        else while (max / div > h) div++;
        var area = clip.Clip(g.l, g.t, g.r, g.b);
        foreach (int s in historySeries)
        {
            int k = (s & 1) * 5 + (s >> 1);
            foreach (var (ring, colour) in new[] { (HistoryRed[k], session.Art.Palette[3]), (HistoryBlack[k], UiArt.Black) })
            {
                int px = 0, py = 0;
                for (int i = 0; i < n; i++)
                {
                    int x = g.l + 32 + (n > 1 ? i * w / 63 : 0), y = bottom - (max * 2 < h ? V(ring, i) * mult : V(ring, i) / div);
                    if (i > 0) Line(area, px, py, x, y, colour);
                    px = x;
                    py = y;
                }
            }
        }
        if (help)
        {
            var it = ui.Layouts[HistoryWin].Items.First(x => x.Bitmap == 16001);
            ui.DrawBitmap(clip, 16001, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    static void Line(UiArt.Canvas c, int x0, int y0, int x1, int y1, uint colour)
    {
        int n = Math.Max(Math.Abs(x1 - x0), Math.Abs(y1 - y0));
        for (int k = 0; k <= n; k++)
            c.Plot(x0 + (n == 0 ? 0 : (x1 - x0) * k / n), y0 + (n == 0 ? 0 : (y1 - y0) * k / n), colour);
    }

    void HistoryWindowClick(int index)
    {
        if (index == 13) help = !help;
        else if (index >= 3 && index <= 12)
        {
            int s = index - 3;
            if (!historySeries.Remove(s) && historySeries.Count < 4) historySeries.Add(s);
        }
    }

    // ------------------------------------------------------------------------------- Behavior / Caste Control
    // Layouts 18 / 19 (bitmaps 4600 / 4620, help overlays 4601 / 4621), the triangles ported in Panels: weights
    // G:049E.. (forage apex, dig bottom left, nurse bottom right) and G:0482.. (breeders, workers, soldiers), each
    // summing to 0xFFFF. Items (indices): 3 help, 4 Auto, 5 Manual, 6..8 Set 1..3 (preset ratios),
    // 12 the relative-setting bars (f_0839a / f_08255, drawn here as three plain bars), 13 the triangle
    // (f_07980 takes its rectangle), 9..11 / 15..17 the corner labels ("click to toggle display", not decoded).
    // As the original's handlers do, a behaviour drag sets manual jobs G:0378 = 0 (f_07d07), a caste drag sets
    // T:07E8 = 0 and recomputes the targets with f_085f8 (f_07ac1).
    const int BehaviorWin = 18, CasteWin = 19, TriangleItem = 13;
    int triangleDrag = -1;

    static (int values, int tri, int point) ControlGlobals(int win) => win == BehaviorWin ? (0x49e, 0x3816, 0x358) : (0x482, 0x3822, 0x22e);

    bool ControlAuto(int win) => win == BehaviorWin ? session.St.U16(Seg.G, 0x378) == 1 : session.St.U16(Seg.T, 0x7e8) != 0;

    void DrawControlWindow(UiArt.Canvas c, int win)
    {
        var st = session.St;
        var (dx, dy) = Off(win);
        int overlay = win == BehaviorWin ? 4601 : 4621;
        ui.DrawWindow(c, win, dx, dy, null, new[] { overlay });
        var wr = WindowRect(win);
        var clip = c.Clip(wr.l, wr.t, wr.r, wr.b);
        var auto = ItemRect(win, ControlAuto(win) ? 4 : 5);
        clip.Invert(auto.l, auto.t, auto.r, auto.b);
        var (values, tri, point) = ControlGlobals(win);
        Panels.Triangle(st, ItemRect(win, TriangleItem), tri);
        Panels.ToPoint(st, values, tri, point);                      // f_087c7: where the marker sits
        int mx = st.U16(Seg.G, point), my = st.U16(Seg.G, point + 2);
        clip.Fill(mx - 3, my - 3, mx + 4, my + 4, UiArt.Black);
        clip.Fill(mx - 1, my - 1, mx + 2, my + 2, UiArt.White);
        var bars = ItemRect(win, 12);
        int bw = (bars.r - bars.l - 4) / 3;
        for (int i = 0; i < 3; i++)
        {
            int h = (int)((long)st.U16(Seg.G, values + 2 * i) * (bars.b - bars.t - 4) / 0xffff);
            int l = bars.l + 2 + i * bw;
            clip.Fill(l + 1, bars.b - 2 - h, l + bw - 1, bars.b - 2, UiArt.Black);
        }
        if (help)
        {
            var it = ui.Layouts[win].Items.First(x => x.Bitmap == overlay);
            ui.DrawBitmap(clip, overlay, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    void ControlWindowClick(int win, int index, Vector2 p)
    {
        var st = session.St;
        switch (index)
        {
            case TriangleItem:
                triangleDrag = win;
                TriangleAt(win, p);
                break;
            case 3: help = !help; break;
            case 4:
            case 5:
                if (win == BehaviorWin) st.Set16(Seg.G, 0x378, index == 4 ? 1 : 0);
                else
                {
                    st.Set16(Seg.T, 0x7e8, index == 4 ? 1 : 0);                 // f_07cde: Manual only clears T:07E8
                }
                break;
            case 6: case 7: case 8:
            {
                // Set 1..3 (f_07d07 at 0x7d8a, the caste handler at 0x7b44): save the weights (6 bytes) into the
                // current preset's slot, T:0810 / T:07F2 + 6 x DS:1B50 / DS:1B4E, make the clicked one current and
                // load its slot; then the panel is manual (G:0378 = 0 / T:07E8 = 0)
                bool behaviour = win == BehaviorWin;
                int slots = behaviour ? 0x810 : 0x7f2, cur = behaviour ? 0x1b50 : 0x1b4e;
                var (values, _, _) = ControlGlobals(win);
                int old = st.U16(Seg.DS, cur);
                for (int k = 0; k < 6; k++) st.Set8(Seg.T, slots + 6 * old + k, st.U8(Seg.G, values + k));
                st.Set16(Seg.DS, cur, index - 6);
                for (int k = 0; k < 6; k++) st.Set8(Seg.G, values + k, st.U8(Seg.T, slots + 6 * (index - 6) + k));
                if (behaviour) st.Set16(Seg.G, 0x378, 0);
                else
                {
                    st.Set16(Seg.T, 0x7e8, 0);
                    NewGame.CasteTargets(st);                                    // the targets follow the weights (as after a drag)
                }
                break;
            }
        }
    }

    /// <summary>f_086a1: the weights at a point in the triangle (clamped to its rectangle).</summary>
    void TriangleAt(int win, Vector2 p)
    {
        var st = session.St;
        var r = ItemRect(win, TriangleItem);
        var (values, tri, point) = ControlGlobals(win);
        Panels.Triangle(st, r, tri);
        st.Set16(Seg.G, point, Math.Clamp((int)p.X, r.l, r.r));
        st.Set16(Seg.G, point + 2, Math.Clamp((int)p.Y, r.t, r.b));
        Panels.ToValues(st, values, tri, point);
        if (win == BehaviorWin) st.Set16(Seg.G, 0x378, 0);           // f_07d07: a drag makes the jobs manual
        else
        {
            st.Set16(Seg.T, 0x7e8, 0);                               // f_07ac1: the caste mix becomes manual too
            NewGame.CasteTargets(st);                                // f_085f8: the caste targets T:07DA..
        }
    }

    void ToggleWindow(int win)
    {
        if (zOrder.Contains(win) && zOrder[^1] == win) zOrder.Remove(win);
        else Front(win);
    }

    // ------------------------------------------------------------------------------- the Ant Info window
    /// <summary>f_67c1c(a, b, view) (window 29, map tool 0): for occupant o, caste = (o &amp; 0x78) >> 3: STR# 1100
    /// [o &amp; 7] for brood (caste 0) else STR# 1101 [caste]; STR# 1102 [the ant's state]; STR# 1103 [caste].
    /// The yellow ant's own cell holds a marker (0xFE / 0xFF), so its type G:04C2 stands in for it (not traced).
    /// The window (layout 29, bitmap 4510) opens at ((a - G:0508 + 1) * 16 + G:110C, (b - G:050A - 1) * 16 + G:110E),
    /// a cell + its width further left if it would pass the screen's right edge, and up to fit; it waits for a
    /// click.</summary>
    string[] AntInfo(int a, int b)
    {
        var st = session.St;
        int o = Player.GetOcc(st, view, a, b);
        if (o <= 0) return null;
        bool yellow = Movement.IsYellow(o);
        if (yellow) o = st.U16(Seg.G, 0x4c2) | (st.U16(Seg.G, 0x4e2) & 0x80);
        int caste = (o & 0x78) >> 3;
        int i = yellow ? -1 : view <= 1 ? Movement.SurfaceAntAt(st, a, b) : Nest.NestAntAt(st, view == 2 ? Nest.BLACK : Nest.RED, a, b, o);
        int state = i < 0 ? 0 : st.U8(Seg.SIM, Player.Ants(view).State + i);
        string Pick(int id, int k)
        {
            var l = session.Files.Strings(id);
            return l != null && k < l.Length ? l[k] : "";
        }
        return new[] { caste == 0 ? Pick(1100, o & 7) : Pick(1101, caste), Pick(1102, state), Pick(1103, caste) };
    }

    const int AntInfoWin = 29;
    string[] antInfoLines;
    (int dx, int dy) antInfoOff;

    void OpenAntInfo(int a, int b)
    {
        antInfoLines = AntInfo(a, b);
        if (antInfoLines == null) return;
        var m = ItemRect(EditWin, EditMapItem);
        var (l, t, r, bb) = ui.Layouts[AntInfoWin].Rect;
        int w = r - l, h = bb - t;
        int x = (a - originA + 1) * Cell + m.l, y = (b - originB - 1) * Cell + m.t;
        if (x + w > ScreenW) x -= Cell + w;
        y = Math.Clamp(y, 0, ScreenH - h);
        antInfoOff = (x - l, y - t);
        modal = AntInfoWin;
    }

    void DrawAntInfo(UiArt.Canvas c)
    {
        ui.DrawWindow(c, AntInfoWin, antInfoOff.dx, antInfoOff.dy, null);
        for (int i = 0; i < 3; i++)
        {
            var (l, t, r, b) = ui.Layouts[AntInfoWin].Items[2 + i].Rect;
            ui.DrawText(c, 2, 0, l + antInfoOff.dx, t + antInfoOff.dy, r + antInfoOff.dx, b + antInfoOff.dy, antInfoLines[i]);
        }
    }

    // ------------------------------------------------------------------------------- speech balloons
    // Balloons.Run (f_06a4d) emits ("balloon", a, b, view, style, (list handle, line)) each tick a balloon is
    // shown; the list handles are the STR# lists loaded at start-up: G:020A 1220 (black fighters), G:0218 1230
    // (red fighters), G:021C 1240 (brood), G:0234 1250 (queen), G:023A 1260 (resting). The original draws a
    // balloon bitmap group (f_0696a); this shows the text.
    static readonly Dictionary<int, int> BalloonLists = new() { [0x20a] = 1220, [0x218] = 1230, [0x21c] = 1240, [0x234] = 1250, [0x23a] = 1260 };
    readonly Dictionary<int, (int a, int b, int view, string text)> balloonsNow = new();
    readonly List<Label> balloonLabels = new();

    string BalloonText(int handle, int index)
    {
        var lines = BalloonLists.TryGetValue(handle, out int id) ? session.Files.Strings(id) : null;
        // the lines hold a literal backslash-n where the original's text drawing breaks the line
        return lines != null && index < lines.Length ? lines[index].Replace("\\n", "\n") : null;
    }

    void ShowBalloons()
    {
        int k = 0;
        var m = ItemRect(EditWin, EditMapItem);
        bool editOnTop = zOrder[^1] == EditWin;
        foreach (var (a, b, v, text) in balloonsNow.Values)
        {
            if (text == null || v != view || !editOnTop) continue;
            int x = (a - originA) * Cell + m.l, y = (b - originB) * Cell - 18 + m.t;
            if (x < m.l || y < m.t || x >= m.r || y >= m.b) continue;
            if (k == balloonLabels.Count)
            {
                var l = new Label();
                l.AddThemeFontSizeOverride("font_size", 10);
                l.AddThemeColorOverride("font_color", new Color(0, 0, 0));
                l.AddThemeStyleboxOverride("normal", new StyleBoxFlat { BgColor = new Color(1, 1, 1), ContentMarginLeft = 3, ContentMarginRight = 3 });
                status.GetParent().AddChild(l);
                balloonLabels.Add(l);
            }
            balloonLabels[k].Text = text;
            balloonLabels[k].Position = new Vector2(Math.Min(x, m.r - 160), y);
            balloonLabels[k].Visible = true;
            k++;
        }
        for (; k < balloonLabels.Count; k++) balloonLabels[k].Visible = false;
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

    void CenterOnYellow()
    {
        var (v, a, b) = session.Yellow;
        if (v != view) return;
        originA = a - Cols / 2;
        originB = b - Rows / 2;
        Clamp();
    }

    void CenterOn(int a, int b)
    {
        follow = false;
        originA = a - Cols / 2;
        originB = b - Rows / 2;
        Clamp();
    }

    void Clamp()
    {
        originA = Math.Clamp(originA, 0, MapRenderer.Width(view) - Cols);
        originB = Math.Clamp(originB, 0, MapRenderer.Height - Rows);
    }

    // ------------------------------------------------------------------------------- the yard window (layout 25)
    // f_702f7 (YardRenderer, SIM_NOTES "The yard window"): the Map window's Yard button sets T:07C8 = 0 and shows
    // it. The yard is 12 x 16 patches (col = G:07BC / G:07CA 0..11, row = G:07BE / G:07CC 0..15); colony strengths
    // T:00A4[col * 16 + row] (black) and T:0164[...] (red). G:035C picks the view: 0 / 1 the yard (the house 7000,
    // the lawn 7003 and the actors), 2 Strat, 3 Graphic (the colony views over the grid strips 7020..7022).
    // Toolbar items (indices): 7 Patch (back to the patch), 8 House (G:035C 0 / 1), 9 Strat, 10 Graphic, 11 MATE,
    // 13 / 14 automatic / manual queen placement, 16 PLACE, 17 help (overlay 7011), 18 / 19 the black / red colony
    // counts. A click on a patch moves there in a Full Game (f_01d48); when the yellow ant dies in a Full Game the
    // window opens and the game waits for a black colony to be picked (STR# 1010 [20]).
    const int YardWin = 25;
    bool yardChoose;
    readonly Random rainRng = new();

    (int x, int y) YardOrigin()
    {
        var r = ItemRect(YardWin, 2);                                     // item 0x1902's corner + (1, 0)
        return (r.l + 1, r.t);
    }

    void OpenYard(bool choose)
    {
        session.St.Set16(Seg.T, 0x7c8, 0);
        if (choose)
        {
            yardChoose = true;
            session.St.Set16(Seg.G, 0x35c, 2);
            lastMessage = session.Files.Strings(1010)?[20] ?? "Click on a black colony to continue.";
        }
        Front(YardWin);
    }

    void CloseYard()
    {
        if (yardChoose) return;
        zOrder.Remove(YardWin);
        session.St.Set16(Seg.T, 0x7c8, view);
    }

    void DrawYardWindow(UiArt.Canvas c)
    {
        var st = session.St;
        var (dx, dy) = Off(YardWin);
        int mode = st.S16(Seg.G, 0x35c);
        string[] titles = { "The Yard", "The Yard", "Colony Coverage", "Colony Sizes" };
        var hidden = new List<int> { 7011 };
        if (mode >= 2) { hidden.Add(7000); hidden.Add(7003); }
        ui.DrawWindow(c, YardWin, dx, dy, titles[Math.Clamp(mode, 0, 3)], hidden);
        var wr = WindowRect(YardWin);
        var clip = c.Clip(wr.l, wr.t, wr.r, wr.b);
        var (ox, oy) = YardOrigin();
        var pic = ItemRect(YardWin, 2);
        var area = clip.Clip(pic.l, pic.t, pic.r, pic.b);
        if (mode < 2)
            foreach (var (rid, x, y) in YardRenderer.Sprites(st, rainRng))
                ui.DrawBitmap(area, rid, x + ox, y + oy);
        else
        {
            area.Fill(pic.l, pic.t, pic.r, pic.b, session.Art.Palette[12]);
            int y = ItemRect(YardWin, 20).b;
            foreach (int rid in new[] { 7020, 7021, 7022 })
            {
                ui.DrawBitmap(area, rid, pic.l, y);
                y += ui.Bitmap(rid).h;
            }
            YardRenderer.DrawColonies(area, st, session.Art.Palette, ox, oy, mode == 2);
        }
        // the player's patch
        int pc = st.U16(Seg.G, 0x7ca), pr = st.U16(Seg.G, 0x7cc);
        if (st.U16(Seg.G, 0xeac) == 2 && pc < 12 && pr < 16)
        {
            int x = ox + 28 * pc - 10 * pr + 169, y = oy + 10 * pr + 67;
            for (int k = 0; k < 8; k++)
            {
                area.Plot(x - k - 1, y + k, 0xffffff40u);
                area.Plot(x + 25 - k, y + k, 0xffffff40u);
            }
        }
        int black = 0, red = 0;
        for (int i = 0; i < 192; i++)
        {
            if (st.U8(Seg.T, 0xa4 + i) != 0) black++;
            if (st.U8(Seg.T, 0x164 + i) != 0) red++;
        }
        foreach (var (index, n) in new[] { (18, black), (19, red) })
        {
            var r = ItemRect(YardWin, index);
            clip.Fill(r.l, r.t, r.r, r.b, UiArt.White);
            ui.DrawText(clip, 3, 0, r.l, r.t, r.r, r.b, n.ToString());
        }
        var am = ItemRect(YardWin, st.U16(Seg.T, 0x2c0) == 1 ? 13 : 14);    // AUTOMATIC / MANUAL (T:02C0)
        clip.Invert(am.l, am.t, am.r, am.b);
        var q = ItemRect(YardWin, 12);                                     // the swarm's black queens G:07C8
        clip.Fill(q.l, q.t, q.r, q.b, UiArt.White);
        ui.DrawText(clip, 3, 0, q.l, q.t, q.r, q.b, Math.Max(0, (int)st.S16(Seg.G, 0x7c8)).ToString());
        if (help)
        {
            var it = ui.Layouts[YardWin].Items.First(x => x.Bitmap == 7011);
            ui.DrawBitmap(clip, 7011, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    /// <summary>MATE (0x190B in f_6f7f0): only in a Full Game; needs males or new queens, G:0AF2 + G:0AF4, not
    /// counting the yellow ant if it is one (type 0x40 / 0x20); then the black flight timer G:08DC = 0xC8.
    /// Otherwise sound 1 and a 180-tick message (STR# 1010 [15] / [5]); on success [6].</summary>
    void Mate()
    {
        var st = session.St;
        string S(int k) => session.Files.Strings(1010)?[k] ?? "";
        if (st.U16(Seg.G, 0xeac) != 2)
        {
            st.Hooks.Effect(st, "sound", 1, 0x7e);
            lastMessage = S(15);
            return;
        }
        int n = st.S16(Seg.G, 0xaf2) + st.S16(Seg.G, 0xaf4), t = st.U16(Seg.G, 0x4c2);
        if (t == 0x40 || t == 0x20) n--;
        if (n <= 0)
        {
            st.Hooks.Effect(st, "sound", 1, 0x7e);
            lastMessage = S(5);
            return;
        }
        st.Set16(Seg.G, 0x8dc, 0xc8);
        lastMessage = S(6);
    }

    void YardWindowClick(int index, Vector2 p)
    {
        var st = session.St;
        switch (index)
        {
            case 7: CloseYard(); return;
            case 8: st.Set16(Seg.G, 0x35c, st.S16(Seg.G, 0x35c) == 0 ? 1 : 0); return;
            case 9: st.Set16(Seg.G, 0x35c, 2); return;
            case 10: st.Set16(Seg.G, 0x35c, 3); return;
            case 17: help = !help; return;
            case 11: Mate(); return;
            case 13: st.Set16(Seg.T, 0x2c0, 1); return;                     // AUTOMATIC: the sim settles the swarm's queens
            case 14: st.Set16(Seg.T, 0x2c0, 0); return;                     // MANUAL
            case 16: lastMessage = "PLACE (placing a founding queen, f_01efa) is not ported yet."; return;
        }
        var pic = ItemRect(YardWin, 2);
        if (!Inside(pic, p)) return;
        var (ox, oy) = YardOrigin();
        int patch = YardRenderer.PatchAt((int)p.X - ox, (int)p.Y - oy);
        if (patch < 0) return;
        if (st.U16(Seg.G, 0xeac) != 2)
        {
            lastMessage = "Moving between patches is for the Full Game.";
            return;
        }
        st.Set16(Seg.G, 0x7bc, patch >> 4);
        st.Set16(Seg.G, 0x7be, patch & 15);
        NewGame.MoveToPatch(st);                                            // f_01d48 (it may refuse: a message)
        if (st.U16(Seg.G, 0x7ca) == patch >> 4 && st.U16(Seg.G, 0x7cc) == (patch & 15))
        {
            yardChoose = false;
            CloseYard();
            SetView(session.Yellow.view);
        }
    }

    /// <summary>The shell's status lines (a stand-in for the original's message window) in the game's font 2.</summary>
    void DrawStatus(UiArt.Canvas canvas)
    {
        if (font == null) return;
        int y0 = 384;
        canvas.Fill(0, y0, ScreenW, y0 + 2 * font.Height + 6, 0xffc0c0c0u);
        font.Draw(argb, ScreenW, ScreenH, 4, y0 + 2, status.Text, 0xff000000u);
        font.Draw(argb, ScreenW, ScreenH, 4, y0 + 3 + font.Height, message.Text.Replace("\n", " "), 0xff000080u);
        status.Visible = message.Visible = false;
    }

    void Redraw()
    {
        var st = session.St;
        // the Edit window the original keeps in G (the event markers record only spots inside it, f_06725)
        st.Set16(Seg.G, 0x508, originA);
        st.Set16(Seg.G, 0x50a, originB);
        st.Set16(Seg.G, 0x10e0, Cols);
        st.Set16(Seg.G, 0x10de, Rows);
        var canvas = new UiArt.Canvas(argb, ScreenW, ScreenH);
        var modes = session.Files.Strings(1001);                       // STR# 1001 (G:0324): the game modes' names
        int gm = st.U16(Seg.G, 0xeac);
        string mode = modes != null && gm < modes.Length ? modes[gm] : $"mode {gm}";
        status.Text = $"{mode}  {ViewNames[view]}  tick {session.Ticks}  black {st.U16(Seg.G, 0x330)}  red {st.U16(Seg.G, 0x350)}"
                      + $"  health {st.S16(Seg.G, 0xf78)}  colony {st.S16(Seg.G, 0x10be)}  speed {SpeedNames[session.Speed]}  jobs {(st.U16(Seg.G, 0x378) == 1 ? "auto" : "manual")}"
                      + (session.Paused ? "  PAUSED" : "") + (session.Over ? (st.U16(Seg.G, 0x366) != 0 ? "  YOU WON" : "  GAME OVER") : "");
        message.Text = lastMessage;
        {
            // the desktop: a 50% grey pattern, the status lines on it, then the windows back to front
            for (int y = 0; y < ScreenH; y++)
                for (int x = 0; x < ScreenW; x++)
                    argb[y * ScreenW + x] = ((x ^ y) & 1) == 0 ? 0xff9a9a9au : 0xff7a7a7au;
            DrawStatus(canvas);
            foreach (int win in zOrder)
                if (win == EditWin) DrawEditWindow(canvas);
                else if (win == MapWin) DrawMapWindow(canvas);
                else if (win == HistoryWin) DrawHistoryWindow(canvas);
                else if (win == YardWin) DrawYardWindow(canvas);
                else DrawControlWindow(canvas, win);
            if (popReport) DrawPopulationReport(canvas);
            if (modal == EfficiencyWin) DrawEfficiency(canvas);
            if (modal == AntInfoWin) DrawAntInfo(canvas);
            if (modal == SelectWin) ui.DrawWindow(canvas, SelectWin, 0, 0, null);
            if (modal is 27 or 30) DrawMessageBox(canvas);
            if (modal == SavePrompt) DrawSavePrompt(canvas);
            if (modal == TitleWin) canvas.Fill(0, 0, ScreenW, ScreenH, UiArt.Black);
            if (modal is TitleWin or AboutWin) ui.DrawWindow(canvas, modal, 0, 0, null);
            if (modal == 11) ui.DrawWindow(canvas, 11, 245, 200, null);       // "not available in the full game"
            if (popup >= 0) DrawPopup(canvas);
        }
        for (int i = 0; i < argb.Length; i++)
        {
            uint c = argb[i];
            rgba[4 * i] = (byte)(c >> 16);
            rgba[4 * i + 1] = (byte)(c >> 8);
            rgba[4 * i + 2] = (byte)c;
            rgba[4 * i + 3] = 255;
        }
        image.SetData(ScreenW, ScreenH, false, Image.Format.Rgba8, rgba);
        texture.Update(image);
    }

    public override void _UnhandledInput(InputEvent ev)
    {
        if (session == null) return;
        if (popup >= 0 && ev is InputEventMouse)
        {
            PopupInput(ev);
            return;
        }
        if (ev is InputEventMouseMotion mm && dragWin >= 0)
        {
            var d = mm.Position - dragFrom;
            var r = ui.Layouts[dragWin].Rect;
            // keep the caption reachable on screen
            int dx = Math.Clamp(dragOrig.dx + (int)d.X, -r.right + 40, ScreenW - 40 - r.left);
            int dy = Math.Clamp(dragOrig.dy + (int)d.Y, -r.top, ScreenH - 20 - r.top);
            offsets[dragWin] = (dx, dy);
            return;
        }
        if (ev is InputEventMouseMotion dm && toolDrag)
        {
            ToolMove(dm.Position, dm);                                          // the tool drag loop f_76f4a
            return;
        }
        if (ev is InputEventMouseMotion tm && triangleDrag >= 0)
        {
            TriangleAt(triangleDrag, tm.Position);                              // dragging the marker
            return;
        }
        if (ev is InputEventMouseButton up && !up.Pressed && up.ButtonIndex == MouseButton.Left)
        {
            dragWin = triangleDrag = -1;
            popReport = false;
            toolDrag = false;
            return;
        }
        if (ev is InputEventMouseButton mb && mb.Pressed)
        {
            if (modal == SavePrompt)
            {
                if (mb.ButtonIndex == MouseButton.Left) SavePromptClick(ui.HitTest(SavePrompt, 0, 0, (int)mb.Position.X, (int)mb.Position.Y));
                return;
            }
            if (modal == SelectWin)
            {
                if (mb.ButtonIndex == MouseButton.Left) SelectClick(ui.HitTest(SelectWin, 0, 0, (int)mb.Position.X, (int)mb.Position.Y));
                return;
            }
            if (modal == TitleWin)
            {
                modal = SelectWin;
                return;
            }
            if (modal >= 0)                                                     // a click closes the modal window
            {
                modal = -1;
                return;
            }
            int win = WindowAt(mb.Position);
            if (win < 0) return;
            Front(win);
            if (Inside(CaptionRect(win), mb.Position) && mb.ButtonIndex == MouseButton.Left)
            {
                dragWin = win;                                                  // drag the window by its caption
                dragFrom = mb.Position;
                dragOrig = offsets[win];
                return;
            }
            var (dx, dy) = Off(win);
            int index = ui.HitTest(win, dx, dy, (int)mb.Position.X, (int)mb.Position.Y);
            if (win == EditWin) EditWindowClick(index, mb);
            else if (mb.ButtonIndex != MouseButton.Left) return;
            else if (win == MapWin) MapWindowClick(index, mb);
            else if (win == HistoryWin) HistoryWindowClick(index);
            else if (win == YardWin) YardWindowClick(index, mb.Position);
            else ControlWindowClick(win, index, mb.Position);
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
                case Key.Y: if (zOrder.Contains(YardWin)) CloseYard(); else OpenYard(false); break;  // the yard window
                case Key.Escape: if (zOrder.Contains(YardWin)) CloseYard(); break;
                case Key.Tab:                                                              // the Map window: front / close
                    if (zOrder.Contains(MapWin) && zOrder[^1] != MapWin) Front(MapWin);
                    else if (zOrder.Contains(MapWin)) zOrder.Remove(MapWin);
                    else Front(MapWin);
                    break;
                case Key.S: muted = !muted; break;                                         // sound effects on / off
                case Key.G: ToggleWindow(HistoryWin); break;                                     // the History graph
                case Key.P: ToggleWindow(BehaviorWin); ToggleWindow(CasteWin); break;                                       // the colony controls
                case Key.F1: help = !help; break;                                          // the help overlays
                case Key.F5: QuickSave(); break;                                           // save (the original's .ANT format)
                case Key.F9: QuickLoad(); break;                                           // load
                case Key.F2: modal = SelectWin; selectMidGame = true; break;
                case Key.F3: modal = AboutWin; break;                                      // the about box                                     // Select a Game
                case Key.V: CycleScent(); break;                                           // the scent views (T:07BE)
                case Key.O: session.St.Set16(Seg.G, 0x378, session.St.U16(Seg.G, 0x378) == 1 ? 0 : 1); break;   // auto / manual jobs
                case Key.N: Restart(1); break;
                case Key.M: Restart(2); break;
                case Key.K: Restart(3); break;
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

    /// <summary>The Experimental menu (layout 10) at the mouse; in an Experimental game the button shows / hides the
    /// tool palette.</summary>
    void QuickLoad()
    {
        var path = ProjectSettings.GlobalizePath("user://quicksave.ANT");
        if (!System.IO.File.Exists(path)) { lastMessage = "No saved game"; return; }
        bool ok = SaveFile.Load(session.St, System.IO.File.ReadAllBytes(path));
        lastMessage = ok ? "Loaded " + path : "Read error, game not loaded";
        SetView(session.Yellow.view);
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
