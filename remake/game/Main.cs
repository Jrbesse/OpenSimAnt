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
    readonly Dictionary<int, (int dx, int dy)> offsets = new() { [EditWin] = (0, 0), [MapWin] = (0, 0) };
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
            else if (arg == "--history") history = true;
            else if (arg == "--panels") panels = true;
            else if (arg == "--help-overlay") help = true;
            else if (arg == "--map-front") Front(MapWin);
        session = new GameSession(dir);
        session.NewGame(1);
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--ticks="))                                 // run the game ahead (for checking a build)
                for (int t = int.Parse(arg["--ticks=".Length..]); t > 0 && !session.Over; t--) session.Step();
        ui = new UiArt(session.Files, session.Art);
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
            yardMap = true;
        }
        if (!session.Over && !yardMap && session.Advance(delta) > 0) balloonsNow.Clear();
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
            }
            else if (e.Name == "sound" && e.Args.Length > 0 && e.Args[0] is int sfx && sfx < 57
                     && session.St.U16(Seg.T, 0x7ac) != 0)
                PlaySound(sfx);
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
            case 7: lastMessage = "The Experimental menu is not built yet."; break;
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
            case 16: CycleScent(); break;
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
            lastMessage = AntInfo(a, b) ?? "";
            return;
        }
        int target = st.U16(Seg.G, 0x105e);
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
                else col = session.Art.Palette[MapRenderer.MapColour(st, mv, a, b)];
                area.Fill(x0 + a * 4, y0 + b * 4, x0 + a * 4 + 4, y0 + b * 4 + 4, col);
            }
        if (mv == view)                                                                     // the Edit window's view
        {
            int l = x0 + originA * 4, t = y0 + originB * 4;
            area.Frame(l, t, l + Cols * 4, t + Rows * 4, 0xffffff40u);
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
                if (st.U16(Seg.G, 0xeac) == 2) yardMap = true;
                else lastMessage = "The yard map is for the Full Game.";
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
            case 14: lastMessage = "Show Trails is not decoded yet."; break;
            case 15: case 17: panels = !panels; break;
            case 16: SetView(session.Yellow.view); follow = true; break;
            case 18: DebugCommands.RandomAction(st); break;                              // the Mystery Button (f_022bc)
            case 19: history = !history; break;
            case 20: lastMessage = $"Efficiency Score: not built yet (score {Formica.Sim.Game.Rating(st).score})"; break;
            case 22: case 23: lastMessage = "The Experimental menu is not built yet."; break;
            case 21: antInfoArmed = true; lastMessage = "Ant Info: click an ant in the Edit window."; break;
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
                if (x > 0 && y > 0 && x < w && y < ScreenH) dst[y * w + x] = 0xffd02020u;
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
        return p.Y < 380;                                            // the panel covers the windows: swallow the click
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
            if (text == null || v != view || yardMap || !editOnTop) continue;
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
        // the Edit window the original keeps in G (the event markers record only spots inside it, f_06725)
        st.Set16(Seg.G, 0x508, originA);
        st.Set16(Seg.G, 0x50a, originB);
        st.Set16(Seg.G, 0x10e0, Cols);
        st.Set16(Seg.G, 0x10de, Rows);
        var canvas = new UiArt.Canvas(argb, ScreenW, ScreenH);
        if (yardMap) DrawYard(argb, ScreenW);
        else
        {
            // the desktop: a 50% grey pattern
            for (int y = 0; y < ScreenH; y++)
                for (int x = 0; x < ScreenW; x++)
                    argb[y * ScreenW + x] = ((x ^ y) & 1) == 0 ? 0xff9a9a9au : 0xff7a7a7au;
            foreach (int win in zOrder)
                if (win == EditWin) DrawEditWindow(canvas);
                else DrawMapWindow(canvas);
        }
        if (history && !yardMap) DrawHistory(argb, ScreenW);
        else if (historyLabel != null) historyLabel.Visible = false;
        if (panels && !yardMap) DrawPanels(argb, ScreenW);
        else if (panelLabels != null) foreach (var l in panelLabels) l.Visible = false;
        string mode = st.U16(Seg.G, 0xeac) == 2 ? "Full Game" : "Quick Game";
        status.Text = $"{mode}  {ViewNames[view]}  tick {session.Ticks}  black {st.U16(Seg.G, 0x330)}  red {st.U16(Seg.G, 0x350)}"
                      + $"  health {st.S16(Seg.G, 0xf78)}  colony {st.S16(Seg.G, 0x10be)}  speed {SpeedNames[session.Speed]}  jobs {(st.U16(Seg.G, 0x378) == 1 ? "auto" : "manual")}"
                      + (session.Paused ? "  PAUSED" : "") + (session.Over ? (st.U16(Seg.G, 0x366) != 0 ? "  YOU WON" : "  GAME OVER") : "");
        message.Text = lastMessage;
        if (font != null)                                               // the status lines in the game's font 2
        {
            int y0 = 384;
            canvas.Fill(0, y0, ScreenW, y0 + 2 * font.Height + 6, 0xffc0c0c0u);
            font.Draw(argb, ScreenW, ScreenH, 4, y0 + 2, status.Text, 0xff000000u);
            font.Draw(argb, ScreenW, ScreenH, 4, y0 + 3 + font.Height, message.Text.Replace("\n", " "), 0xff000080u);
            status.Visible = message.Visible = false;
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
        if (ev is InputEventMouseButton up && !up.Pressed && up.ButtonIndex == MouseButton.Left)
        {
            dragWin = -1;
            return;
        }
        if (ev is InputEventMouseButton mb && mb.Pressed)
        {
            if (yardMap)
            {
                YardClick(mb.Position);
                return;
            }
            if (mb.Position.X < 190 && PanelClick(mb.Position)) return;
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
            else if (mb.ButtonIndex == MouseButton.Left) MapWindowClick(index, mb);
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
                case Key.Tab:                                                              // the Map window: front / close
                    if (zOrder.Contains(MapWin) && zOrder[^1] != MapWin) Front(MapWin);
                    else if (zOrder.Contains(MapWin)) zOrder.Remove(MapWin);
                    else Front(MapWin);
                    break;
                case Key.S: muted = !muted; break;                                         // sound effects on / off
                case Key.G: history = !history; break;                                     // the History graph
                case Key.P: panels = !panels; break;                                       // the colony controls
                case Key.F1: help = !help; break;                                          // the help overlays
                case Key.F5:                                                               // save (the original's .ANT format)
                {
                    var path = ProjectSettings.GlobalizePath("user://quicksave.ANT");
                    System.IO.File.WriteAllBytes(path, SaveFile.Save(session.St));
                    lastMessage = "Saved to " + path;
                    break;
                }
                case Key.F9:                                                               // load
                {
                    var path = ProjectSettings.GlobalizePath("user://quicksave.ANT");
                    if (!System.IO.File.Exists(path)) { lastMessage = "No saved game"; break; }
                    bool ok = SaveFile.Load(session.St, System.IO.File.ReadAllBytes(path));
                    lastMessage = ok ? "Loaded " + path : "Read error, game not loaded";
                    SetView(session.Yellow.view);
                    break;
                }
                case Key.V: CycleScent(); break;                                           // the scent views (T:07BE)
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
