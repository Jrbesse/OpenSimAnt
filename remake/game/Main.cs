using Godot;
using Formica.Data;
using Formica.Sim;

namespace Formica.Game;

/// <summary>
/// The playable shell, laid out like the original's 640 x 480 screen from its window layouts (UiArt, Layouts):
/// the Edit window (layout 0: the tool strip, bitmap 15000, a 22 x 21 cell map of 16 px, the health bars) and
/// the Map window (layout 1: the whole map at 4 px per cell, the toolbar, bitmap 14000, the population report).
/// Windows move by their caption and come to the front on a click.
///
/// Edit window: the original's clicks (f_74fe0). Keys: the original's (f_74386: letters go to the cheat matcher, the
/// key table DS:2CBE, f_76aeb), plus the shell's own non-letter keys (arrows, + / -, Ctrl+1..3, Tab, F1, F8 / F9, F12).
/// remake/README.md lists every control.
/// </summary>
public partial class Main : Node2D
{
    const int ScreenW = 640, ScreenH = 480, Cell = 16;
    const int EditWin = 0, MapWin = 1;
    // the Edit window's map: G:10E0 x G:10DE = 22 x 21 cells (the start-up values), item 4 of layout 0
    const int Cols = 22, Rows = 21;
    // layout item indices (the ids repeat in layout 0, so the shell matches on the index)
    const int EditMapItem = 4, MapMapItem = 2;
    // item 21 (id 4, like the map): the strip under the map item (64,362 .. 400,377); f_07558 makes the map's
    // drawing region the map item plus this strip (f_1ee65), so the 21st row of 16 px shows in it
    const int EditMapStrip = 21;
    static readonly string[] SpeedNames = { "slow", "normal", "fast", "ultra" };
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
    bool follow = true, help, helpHeld, antInfoArmed;
    string lastMessage = "";
    string screenshot;
    bool tutorialShot, screenshotSpider;
    int shotFrames = 240;
    readonly List<string> frontArgs = new(OS.GetCmdlineUserArgs());        // --history, --panels, --map-front, --antipedia, --yard
    bool frozen;
    string stateMessage;                                                   // --state: the timed message to show                                                            // --state: the game does not run
    int frames;

    // the window stack (last = front) and each window's offset from its layout position
    readonly List<int> zOrder = new();                                       // f_7256f opens the windows when a game starts
    readonly Dictionary<int, (int dx, int dy)> offsets = new() { [EditWin] = (0, 0), [MapWin] = (-56, 38), [BehaviorWin] = (0, 0), [CasteWin] = (0, 0), [HistoryWin] = (0, 0), [YardWin] = (0, 0) };
    int dragWin = -1;
    bool mapDrag;
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
            GD.PrintErr("Formica: no SIMANT.EXE / HCEGANT found");
            screenshot = OS.GetCmdlineUserArgs().FirstOrDefault(x => x.StartsWith("--screenshot="))?["--screenshot=".Length..];
            ShowSetup(layer);
            return;
        }
        GD.Print("Formica: game files in " + dir);
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--screenshot=")) screenshot = arg["--screenshot=".Length..];
            else if (arg.StartsWith("--frames=")) shotFrames = int.Parse(arg["--frames=".Length..]);
            else if (arg == "--history") { }
            else if (arg == "--panels") { }
            else if (arg == "--help-overlay") help = true;
            else if (arg == "--status") showStatus = true;
            else if (arg.StartsWith("--scene="))                                   // the window-26 scenes, for screenshots
                sceneArg = int.Parse(arg["--scene=".Length..]);
            else if (arg == "--map-front") { }
        session = new GameSession(dir);
        var args = OS.GetCmdlineUserArgs();
        session.NewGame(args.Contains("--full") ? 2 : args.Contains("--experimental") ? 3 : 1);
        if (screenshot == null || args.Contains("--title")) modal = TitleWin;    // the title, then Select a Game
        else if (args.Contains("--select")) modal = SelectWin;
        if (modal == TitleWin) PlaySong(0x2711);                            // f_72bc2: the title plays the Game Theme
        if (args.Contains("--silly")) session.ToggleOption(5);             // Options > Silly: the speech balloons
        foreach (var arg in args.Where(x => x.StartsWith("--tutorial")))   // --tutorial[=step]: the Tutorial at that step
        {
            session.NewGame(0);
            if (arg.Contains('=')) session.St.Set16(Seg.T, 0x7a4, int.Parse(arg[(arg.IndexOf('=') + 1)..]));
            tutorialShot = true;
        }
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--ticks="))                                 // run the game ahead (for checking a build)
                for (int t = int.Parse(arg["--ticks=".Length..]); t > 0 && !session.Over; t--) session.Step();
            else if (arg.StartsWith("--state="))                            // the original's memory (tools/re/screens.py), held still
            {
                var statePath = arg["--state=".Length..];
                session.LoadState(System.IO.File.ReadAllBytes(statePath));
                frozen = true;
                var msgPath = System.IO.Path.ChangeExtension(statePath, ".msg");          // the timed message shown (screens.py)
                if (System.IO.File.Exists(msgPath) && System.IO.File.ReadAllBytes(msgPath) is { Length: > 0 } msg)
                    stateMessage = OriginalFiles.MacText(msg);
            }
        ui = new UiArt(session.Files, session.Art);
        if (OS.GetCmdlineUserArgs().Contains("--efficiency")) OpenEfficiency();
        if (OS.GetCmdlineUserArgs().Contains("--popup")) OpenPopup(200, 150);
        foreach (var arg in OS.GetCmdlineUserArgs())                            // --popup=x,y: held at (x, y), as a press does
            if (arg.StartsWith("--popup=") && arg["--popup=".Length..].Split(',') is { Length: 2 } pp)
                OpenPopup(int.Parse(pp[0]), int.Parse(pp[1]));
        if (OS.GetCmdlineUserArgs().Contains("--scent-menu")) OpenScentMenu();
        if (OS.GetCmdlineUserArgs().Contains("--mini-map")) miniMap = true;
        if (sceneArg != 0) ArmTimeout(15);                                       // as after a message box
        switch (sceneArg)
        {
            case 1: Present(AntLionScene); break;
            case 2: Present(() => PictureScene(0x238c, 0)); break;
            case 3: Present(() => PictureScene(0x238d, 1)); break;
            case 4: Present(() => PictureScene(0x2396, -1)); break;
            case 5: Present(() => SpiderScene(session.Files.Strings(0x2740))); break;
        }
        if (OS.GetCmdlineUserArgs().Contains("--win")) { StartWin(); winPhase = 2; winSong = 0x4e25; winFrame = 1; }
        if (OS.GetCmdlineUserArgs().Contains("--trails")) session.St.Set16(Seg.DS, 0x2994, 1);
        if (OS.GetCmdlineUserArgs().Contains("--report")) popReport = true;
        if (OS.GetCmdlineUserArgs().Contains("--exp-menu")) ExperimentalMenu();
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--antipedia"))                              // --antipedia[=card][,x,y: hold the button there]
            {
                OpenAntipedia();
                var a = arg.Contains('=') ? arg[(arg.IndexOf('=') + 1)..].Split(',').Select(int.Parse).ToArray() : Array.Empty<int>();
                if (a.Length > 0) ShowCard(a[0]);
                else if (frozen) ShowCard(session.St.U16(Seg.DS, 0x2e26));    // --state: the card it shows (DS:2E26)
                if (a.Length > 2) AntipediaPress(a[1], a[2]);
            }
        if (OS.GetCmdlineUserArgs().Contains("--load-dialog")) OpenFileDialog(false);
        if (OS.GetCmdlineUserArgs().Contains("--alert")) OpenAlert("OVERWRITE\nC:\\SIMANT\\MYCOLONY.ANT", new[] { "\rYes", "\x1bNo" });
        if (OS.GetCmdlineUserArgs().Contains("--error")) OpenAlert("  Read error  \ngame not loaded", null);
        foreach (var arg in OS.GetCmdlineUserArgs())                            // --alert-text=line|line: an alert with OK
            if (arg.StartsWith("--alert-text=")) OpenAlert(arg["--alert-text=".Length..].Replace('|', '\n'), null);
        if (OS.GetCmdlineUserArgs().Contains("--save-dialog")) { gameFile = "MYCOLONY.ANT"; OpenFileDialog(true); }
        foreach (var arg in OS.GetCmdlineUserArgs())                            // --save-dialog=NAME: the last file's name (may be empty)
            if (arg.StartsWith("--save-dialog=")) { gameFile = arg["--save-dialog=".Length..]; OpenFileDialog(true); }
        if (OS.GetCmdlineUserArgs().Contains("--game-over"))
        {
            var (score, _) = Formica.Sim.Game.Rating(session.St);
            OpenGameOver(Formica.Sim.Game.Rank(session.St, score), score);
        }
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--save-prompt"))                            // --save-prompt[=n]: before n (1 Quick Game, 4 Load, ...)
            {
                selectMidGame = true;
                Replace(arg.Contains('=') ? int.Parse(arg[(arg.IndexOf('=') + 1)..]) : 1);
            }
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--about"))                                  // File > About; --about=line,pixel: the roll there
            {
                OpenAbout();
                if (arg.Contains('=') && arg[(arg.IndexOf('=') + 1)..].Split(',').Select(int.Parse).ToArray() is { Length: 2 } ab)
                {
                    (aboutLine, aboutPixel, aboutRolling) = (ab[0], ab[1], true);
                    aboutNext = double.MaxValue;
                }
            }
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--message=") && session.Files.Strings(int.Parse(arg["--message=".Length..])) is { } box)
                OpenMessageBox(box);                                        // --message=<STR# id>: show a message box
        if (OS.GetCmdlineUserArgs().Contains("--ant-info")) { var (_, ya, yb) = session.Yellow; SetView(session.Yellow.view); CenterOnYellow(); OpenAntInfo(ya, yb); }
        foreach (var arg in OS.GetCmdlineUserArgs())                            // --ant-info=a,b: held on the ant in cell (a, b)
            if (arg.StartsWith("--ant-info=") && arg["--ant-info=".Length..].Split(',') is { Length: 2 } ai)
                OpenAntInfo(int.Parse(ai[0]), int.Parse(ai[1]));
        if (OS.GetCmdlineUserArgs().Contains("--strat")) session.St.Set16(Seg.G, 0x35c, 2);
        font = ui.Font(2);
        menus = new Menus(session.Files, ScreenW);
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--menu="))                                  // --menu=m[,item]: that menu open, the item highlighted
            {
                var a = arg["--menu=".Length..].Split(',').Select(int.Parse).ToArray();
                OpenMenu(a[0]);
                if (a.Length > 1) menuHot = a[1];
            }
        if (args.Contains("--spider-view"))                                 // the surface centred on the spider
            screenshotSpider = true;
        argb = new uint[ScreenW * ScreenH];
        mapBuf = new uint[Cols * Cell * Rows * Cell];
        rgba = new byte[argb.Length * 4];
        image = Image.CreateEmpty(ScreenW, ScreenH, false, Image.Format.Rgba8);
        texture = ImageTexture.CreateFromImage(image);
        screen = new Sprite2D { Texture = texture, Centered = false };
        AddChild(screen);
        MoveChild(screen, 0);
        int heldView = session.St.U16(Seg.G, 0x32e), heldA = session.St.S16(Seg.G, 0x508), heldB = session.St.S16(Seg.G, 0x50a);
        int heldContent = session.St.U16(Seg.T, 0x7c8);                                 // the Map window's content
        SetView(session.Yellow.view);
        if (frozen && heldView is >= 0 and <= 3)                                       // --state: the view and origin it holds
        {
            if (heldView != 0) SetView(heldView);                                      // the yard: the buttons keep the last view
            session.St.Set16(Seg.G, 0x32e, heldView);
            session.St.Set16(Seg.T, 0x7c8, heldContent);
            originA = heldA;
            originB = heldB;
        }
        if (screenshotSpider) { SetView(1); CenterOn(session.St.S16(Seg.G, 0xf12) >> 4, session.St.S16(Seg.G, 0xf34) >> 4); follow = false; }
        foreach (var arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--map-content="))                           // --map-content=n: the Map window shows T:07C8 = n
                session.St.Set16(Seg.T, 0x7c8, int.Parse(arg["--map-content=".Length..]));
            else if (arg.StartsWith("--series="))                           // --series=a,b,..: History buttons pressed in turn
                foreach (var s in arg["--series=".Length..].Split(',')) ToggleSeries(int.Parse(s));
        Redraw();
    }

    const string SettingsPath = "user://settings.cfg";

    /// <summary>--game-dir=..., FORMICA_GAME_DIR, the folder picked on the setup screen (settings.cfg), the
    /// executable's folder and the ones just inside it, or the folders above the project / the executable.</summary>
    static string FindGameDir()
    {
        foreach (var arg in OS.GetCmdlineUserArgs().Concat(OS.GetCmdlineArgs()))
            if (arg.StartsWith("--game-dir=")) return arg["--game-dir=".Length..];
        var env = System.Environment.GetEnvironmentVariable("FORMICA_GAME_DIR");
        if (!string.IsNullOrEmpty(env) && OriginalFiles.Present(env)) return env;
        var settings = new ConfigFile();
        if (settings.Load(SettingsPath) == Error.Ok)
        {
            var saved = (string)settings.GetValue("files", "game_dir", "");
            if (saved != "" && OriginalFiles.Present(saved)) return saved;
        }
        var exeDir = System.IO.Path.GetDirectoryName(OS.GetExecutablePath());
        if (SearchGameDir(exeDir, 2) is string near) return near;
        // res:// is the project folder only when running from source; an exported build has no such folder
        var starts = OS.HasFeature("template") ? new[] { exeDir } : new[] { ProjectSettings.GlobalizePath("res://"), exeDir };
        foreach (var start in starts)
        {
            var d = new System.IO.DirectoryInfo(start);
            for (int i = 0; i < 5 && d != null; i++, d = d.Parent)
                if (OriginalFiles.Present(d.FullName)) return d.FullName;
        }
        return null;
    }

    /// <summary>The first folder with the game's files: root itself, then the folders inside it, depth levels down.</summary>
    static string SearchGameDir(string root, int depth)
    {
        if (OriginalFiles.Present(root)) return root;
        if (depth == 0) return null;
        try
        {
            foreach (var sub in System.IO.Directory.EnumerateDirectories(root))
                if (SearchGameDir(sub, depth - 1) is string found) return found;
        }
        catch (System.UnauthorizedAccessException) { }
        catch (System.IO.IOException) { }
        return null;
    }

    /// <summary>
    /// No game files found: the first-run screen. A button opens the system's folder picker; the folder the
    /// player picks (or one up to two levels inside it) is kept in user://settings.cfg and the scene restarts.
    /// The game's own text is the original's bitmap font, which is not there yet, so this screen uses Godot's
    /// font, drawn at the window's resolution (canvas_items stretch) instead of doubled from 640 x 480.
    /// </summary>
    void ShowSetup(CanvasLayer layer)
    {
        var root = GetTree().Root;
        root.ContentScaleMode = Window.ContentScaleModeEnum.CanvasItems;
        status.Text = "Formica needs the files from your own copy of the original DOS game.";
        message.Text = "Click the button below and choose the folder that has SIMANT.EXE in it.";
        status.Position = new Vector2(16, 170);
        message.Position = new Vector2(16, 190);
        var button = new Button { Text = "Find my game folder...", Position = new Vector2(16, 224) };
        button.AddThemeFontSizeOverride("font_size", 12);
        foreach (var c in new Control[] { status, message, button }) c.TextureFilter = CanvasItem.TextureFilterEnum.Linear;
        var dialog = new FileDialog
        {
            FileMode = FileDialog.FileModeEnum.OpenDir,
            Access = FileDialog.AccessEnum.Filesystem,
            UseNativeDialog = true,
            Title = "Choose the folder with SIMANT.EXE",
        };
        dialog.DirSelected += picked =>
        {
            var found = SearchGameDir(picked, 2);
            if (found == null)
            {
                message.Text = "SIMANT.EXE, HCEGANT.DAT and HCEGANT.NDX are not in that folder. Try another one.";
                return;
            }
            var settings = new ConfigFile();
            settings.Load(SettingsPath);
            settings.SetValue("files", "game_dir", found);
            settings.Save(SettingsPath);
            root.ContentScaleMode = Window.ContentScaleModeEnum.Viewport;     // back to the game's pixel scaling
            GetTree().ReloadCurrentScene();
        };
        button.Pressed += () => dialog.PopupCentered(new Vector2I(600, 420));
        layer.AddChild(button);
        layer.AddChild(dialog);
    }

    public override void _Process(double delta)
    {
        if (session == null) { ShotPoll(); return; }                       // the setup screen
        if (session.Hooks.YardMapWanted)                                   // the yellow ant died: pick a colony
        {
            session.Hooks.YardMapWanted = false;
            OpenYard(true);
        }
        int ran = 0;
        bool running = !frozen && !session.Over && !yardChoose && modal < 0 && menuOpen < 0 && !miniMap && !helpHeld && winPhase == 0
                       && !Presenting;
        if (!running || session.Paused) mapLive = true;                   // the Map window follows the game while it stands
        if (running && (ran = session.Advance(delta)) > 0)
        {
            MapLoops(ran);
            balloonsNow.Clear();
            // f_701a5 (the yard window's mower, drawn each tick while the window is open): sound 0x24 while mowing
            // (T:0C28 3 or 4) and not paused
            if (zOrder.Contains(YardWin) && session.St.U16(Seg.T, 0xc28) is 3 or 4 && !session.Paused) PlaySound(0x24);
        }
        // f_71d95's loop: once the game-over jingle is done, song 0x2713 + Rand2 (once)
        if (modal == GameOverWin && !gameOverSong && (!session.Option(1) || !AudioReady() || !mixer.Driver.Playing))
        {
            gameOverSong = true;
            PlaySong(0x2713 + session.St.Rand2());
        }
        if (modal != GameOverWin) gameOverSong = false;
        ToolPoll();
        ToolHold(delta);
        PendingClick(delta);
        ScrollPoll(delta);
        FilePoll(delta);
        WinPoll(delta);
        PresentPoll();
        // f_72bc2 (the title, f_01277(40)) and f_71d95 (game over, f_01277(100)) also close when the timeout fires
        if (modal != timedModal)
        {
            timedModal = modal;
            if (modal == TitleWin) ArmTimeout(40);
            else if (modal == GameOverWin) ArmTimeout(100);
        }
        else if (modal is TitleWin or GameOverWin && TimeoutFired())
        {
            modal = timedModal = SelectWin;
            selectMidGame = false;
        }
        SongPoll();
        DrainEffects();
        Redraw();
        ShotPoll();
    }

    void ShotPoll()
    {
        if (screenshot != null && ++frames == shotFrames)
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
            if (e.Name is "message" or "message_box" && e.Args.Length > 0 && e.Args[0] is int)
            {
                // f_71b1a(picture, STR# id, flag): a message box, shown when flag != 0 or Options > Events (T:07AE) is on.
                // "message" is f_71b1a(0, id, 0); "message_box" carries (id, flag[, picture]); the starved queens'
                // "message" has (0x1093, 0, id, 1).
                int id = (int)e.Args[0], flag = 0, pic = 0;
                if (e.Name == "message" && e.Args.Length >= 4) { id = Convert.ToInt32(e.Args[2]); flag = Convert.ToInt32(e.Args[3]); }
                else if (e.Name == "message_box")
                {
                    flag = e.Args.Length > 1 ? Convert.ToInt32(e.Args[1]) : 1;
                    pic = e.Args.Length > 2 && e.Args[2] is int p ? p : 0;
                }
                var lines = session.Files.Strings(id);
                GD.Print("message: " + (lines != null ? string.Join(" ", lines) : $"0x{id:x}"));
                if (lines != null && (flag != 0 || session.Option(3)) && (screenshot == null || tutorialShot))
                {
                    if (id is 0x273f or 0x2740) Present(() => SpiderScene(lines));       // f_71f52, then its box
                    else Present(() => MessageBoxP(lines, pic));
                }
            }
            else if (e.Name == "status" && e.Args.Length > 0)
                StatusEffect(e.Args);
            else if (e.Name is "sound" or "sound2" && e.Args.Length > 0 && e.Args[0] is int sfx && sfx < SoundBank.EffectCount
                     && session.St.U16(Seg.T, 0x7ac) != 0)
                PlaySound(sfx);
            else if (e.Name is "sound" or "voice" or "music" && e.Args.Length > 0 && e.Args[0] is int song && song >= 10000)
                PlaySong(song);
            else if (e.Name == "follow") FollowYellow();                     // f_01c52 (each step with AutoTrack on)
            else if (e.Name == "info" && e.Args.Length >= 2)                // the Ant Info tool (f_2f8fc)
                OpenAntInfo((int)e.Args[0], (int)e.Args[1]);
            else if (e.Name == "balloon" && e.Args.Length >= 5 && e.Args[4] is ValueTuple<int, int> line)
                balloonsNow.Add(((int)e.Args[0], (int)e.Args[1], (int)e.Args[2], BalloonText(line.Item1, line.Item2)));
            else if (e.Name == "win_screen") StartWin();
            else if (e.Name == "colony_panel")                                     // f_7256f (a game started or loaded)
            {
                Front(CasteWin);                                                    // f_07a95, f_07aab
                Front(BehaviorWin);
                OpenMapSlot();                                                      // f_013ff
                Front(EditWin);                                                     // f_03370
                foreach (var arg in frontArgs)                                      // the screenshot flags' windows, in their order
                {
                    if (arg == "--start-windows")                                   // a new game over these windows: f_7256f again
                    {
                        Front(CasteWin);
                        Front(BehaviorWin);
                        OpenMapSlot();
                        Front(EditWin);
                        continue;
                    }
                    foreach (int w in arg switch
                             {
                                 "--history" => new[] { HistoryWin }, "--panels" => new[] { BehaviorWin, CasteWin },
                                 "--map-front" => new[] { MapWin }, "--yard" => new[] { YardWin },
                                 "--edit-front" => new[] { EditWin },
                                 _ when arg.StartsWith("--antipedia") => new[] { TextWin }, _ => Array.Empty<int>(),
                             })
                        if (w == YardWin) OpenYard(false);                             // in the Map window's place
                        else Front(w);
                }
                frontArgs.Clear();
            }
            else if (e.Name == "scene") Present(AntLionScene);                    // f_76707
            else if (e.Name == "anim" && e.Args.Length > 0 && e.Args[0] is List<(State st, List<object[]> sounds)> frames && frames.Count > 0)
                Present(() => AnimP(frames));                                          // f_7c149 / f_7c3b1
            else if (e.Name == "spider_strike" && e.Args.Length >= 2)             // f_753e5: from the spider (1/16 cell = px) to the ant
            {
                PlaySound(0x37);
                var st0 = session.St;
                strikes.Add((st0.S16(Seg.G, 0xf12), st0.S16(Seg.G, 0xf34), Convert.ToInt32(e.Args[0]), Convert.ToInt32(e.Args[1])));
            }
            else if (e.Name == "help" && e.Args.Length >= 2 && session.St.U16(Seg.T, 0x7ae) != 0)
            {
                int pic = Convert.ToInt32(e.Args[0]), n = Convert.ToInt32(e.Args[1]);
                Present(() => PictureScene(pic, n));                                   // f_7686d
            }
            else if (e.Name == "menu" && e.Args.Length > 0) MenuEffect(Convert.ToInt32(e.Args[0]));
            else if (e.Name == "picture" && e.Args.Length > 0) PauseLine(Convert.ToInt32(e.Args[0]));   // f_71a7d
            else if (e.Name is "pause" or "edit_tool" && e.Args.Length > 0) SetPause(Convert.ToInt32(e.Args[0]));   // f_2f816 → f_6e17e
            else if (e.Name == "game_over" && e.Args.Length >= 2)
            {
                // f_71d95's rating window: the rank's title (STR# 1900 = G:0328) and the score (Game.Rating). f_71d95
                // shows entry `rank` of the list at G:0328 (loaded from STR# 1900), with the mode's name (G:0324) above it.
                int rank = (int)e.Args[0];
                var titles = session.Files.Strings(1900);
                string title = titles != null && rank < titles.Length ? titles[rank] : $"rank {rank}";
                lastMessage = $"Game over: {title}  (score {e.Args[1]})  N: new Quick Game, M: new Full Game";
                GD.Print(lastMessage);
                OpenGameOver(rank, Convert.ToInt64(e.Args[1]));
            }
        }
        if (stateMessage != null)                                           // after the replaced game's start effects
        {
            statusText = stateMessage;
            statusUntil = long.MaxValue;
            stateMessage = null;
        }
    }

    // ------------------------------------------------------------------------------- the mouse cursor
    // The driver draws its own cursor (2b73: the image DS:3D10 from type 8 and the mask DS:3D14 from type 7 with the
    // same id, set by f_1b3a9) with its top-left corner at the mouse (DS:9122 / DS:9124). Type 8: u16 width, height,
    // then per row 4 planes of (width / 8) bytes, plane p = bit p of the palette index; type 7: u16 width, height,
    // then a 1-bit AND mask per row (1 = the screen shows through). Cursor 0 is the arrow (HCEGANT 8/0 with SHARED
    // 7/0), 1 the hourglass (HCEGANT 8/1, 7/1). (Start-up asks for cursor 4, which does not exist, so 0 stays.)
    (int w, int h, uint[] px)? cursorArt;

    (int w, int h, uint[] px)? LoadCursor(int id)
    {
        var img = session.Files.Hcegant.FirstOrDefault(r => r.Type == 8 && r.Id == id)?.Data;
        var mask = (session.Files.Hcegant.FirstOrDefault(r => r.Type == 7 && r.Id == id) ?? session.Files.Shared.FirstOrDefault(r => r.Type == 7 && r.Id == id))?.Data;
        if (img == null || mask == null || img.Length < 4 || mask.Length < 4) return null;
        int w = img[0] | img[1] << 8, h = img[2] | img[3] << 8;
        int mw = mask[0] | mask[1] << 8, mh = mask[2] | mask[3] << 8;
        if (w <= 0 || h <= 0 || (img.Length - 4) % h != 0) return null;
        int row = (img.Length - 4) / h, plane = row / 4, mrow = mh > 0 ? (mask.Length - 4) / mh : 0;
        var px = new uint[w * h];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
            {
                bool clear = x >= mw || y >= mh || ((mask[4 + y * mrow + x / 8] >> (7 - x % 8)) & 1) != 0;
                if (clear) continue;
                int k = 0;
                for (int p = 0; p < 4; p++) k |= ((img[4 + y * row + p * plane + x / 8] >> (7 - x % 8)) & 1) << p;
                px[y * w + x] = session.Art.Palette[k];
            }
        return (w, h, px);
    }

    void DrawCursor(UiArt.Canvas c)
    {
        cursorArt ??= LoadCursor(0);
        // screenshots: --cursor at (300, 200), --cursor=x,y there
        var arg = OS.GetCmdlineUserArgs().FirstOrDefault(x => x == "--cursor" || x.StartsWith("--cursor="));
        bool shot = arg != null;
        if (cursorArt is not { } a || screenshot != null && !shot) return;
        var at = arg?.Contains('=') == true ? arg[(arg.IndexOf('=') + 1)..].Split(',').Select(int.Parse).ToArray() : new[] { 300, 200 };
        var p = shot ? new Vector2(at[0], at[1]) : GetViewport().GetMousePosition();
        for (int y = 0; y < a.h; y++)
            for (int x = 0; x < a.w; x++)
                if (a.px[y * a.w + x] != 0) c.Plot((int)p.X + x, (int)p.Y + y, a.px[y * a.w + x]);
        if (Input.MouseMode != Input.MouseModeEnum.Hidden) Input.MouseMode = Input.MouseModeEnum.Hidden;
    }

    // ------------------------------------------------------------------------------- presentations
    // The original shows message boxes and the scenes of window 26 in local loops: the game waits and they come one
    // after the other. Here each is a coroutine in a queue; while one runs the game does not advance. A key (f_01572)
    // or a press (f_21cb8) during one is handed to it through presentKey / presentPress.
    readonly Queue<Func<IEnumerator<bool>>> presentQueue = new();
    IEnumerator<bool> present;
    bool presentKey, presentPress;

    void Present(Func<IEnumerator<bool>> p) => presentQueue.Enqueue(p);

    bool Presenting => present != null || presentQueue.Count > 0;

    void PresentPoll()
    {
        for (int guard = 0; guard < 8; guard++)
        {
            if (present == null)
            {
                if (presentQueue.Count == 0) return;
                presentKey = presentPress = false;
                present = presentQueue.Dequeue()();
            }
            if (present.MoveNext()) return;
            present = null;
            scenePic = -1;
            animState = null;
            presentKey = presentPress = false;
        }
    }

    // f_01277(s) / f_012c4: the global timeout DS:8BA8 (start) / DS:8BAC (ticks), checked by f_1ccfc: outside
    // [start, start + ticks) it reports true once and restarts from now. At start-up both are 0: it always fires.
    double timeoutStart;
    int timeoutTicks;

    static double UiTicks => Time.GetTicksMsec() / 1000.0 * GameSession.ClockHz;

    void ArmTimeout(int seconds)
    {
        timeoutStart = UiTicks;
        timeoutTicks = seconds * 0x12;
    }

    bool TimeoutFired()
    {
        double now = UiTicks;
        if (now >= timeoutStart && now < timeoutStart + timeoutTicks) return false;
        timeoutStart = now;
        return true;
    }

    /// <summary>f_01572: a key, or the timeout.</summary>
    bool KeyOrTimeout()
    {
        if (TimeoutFired()) return true;
        bool k = presentKey;
        presentKey = false;
        return k;
    }

    /// <summary>f_011e5(n): until n clock ticks pass, an event is pending (left for the caller) or f_01572.</summary>
    IEnumerable<bool> WaitTicks(int n)
    {
        double end = UiTicks + n;
        while (UiTicks < end && !presentPress && !presentKey && !KeyOrTimeout()) yield return true;
    }

    /// <summary>f_71bb6's wait: f_01277(15), then until f_01572 (a key or the 15 s), the window closing, or a press.</summary>
    IEnumerator<bool> MessageBoxP(string[] lines, int picture)
    {
        OpenMessageBox(lines, picture);
        ArmTimeout(15);
        while (modal == 30)
        {
            if (KeyOrTimeout() || presentPress) { modal = -1; break; }
            yield return true;
        }
    }

    // Window 26's scenes (layout 26: the picture at 153, 85, a 2-px black frame around it, the hotspot 0x1A00 / item 2
    // a 16-px strip from the picture's top - 1, inset 2 px, where f_7686d writes its line: f_20a0f centres the text
    // and fills its row in the scheme's background, scheme 13: yellow on dark grey).
    int scenePic = -1;
    (int bmp, int x, int y)? sceneOverlay;
    string sceneCaption;

    void OpenScene(int pic)
    {
        scenePic = pic;
        sceneOverlay = null;
        sceneCaption = null;
    }

    void DrawScene(UiArt.Canvas c)
    {
        if (scenePic < 0) return;
        var (w, h, _) = ui.Bitmap(scenePic);
        int x = 153, y = 85;
        c.Fill(x - 2, y - 2, x + w + 2, y + h + 2, UiArt.Grey);
        UiArt.ThickFrame(c, x - 2, y - 2, x + w + 2, y + h + 2, 2, UiArt.Black);
        ui.DrawBitmap(c, scenePic, x, y);
        if (sceneOverlay is { } o) ui.DrawBitmap(c, o.bmp, x + o.x, y + o.y);
        if (sceneCaption != null)
        {
            var f = ui.Font(0);
            var (fg, bg) = ui.Schemes[13];
            int l = x, r = x + w, t = y - 1, b = t + 16;
            int ty = t + (b - t - f.Height) / 2;
            c.Fill(l, ty, r, ty + f.Height, bg);
            f.Draw(c.Clip(l, t, r, b), Math.Max(l, (l + r - f.Width(sceneCaption)) / 2), ty, sceneCaption, fg);
        }
    }

    /// <summary>f_76707, the ant lion takes the yellow ant (T:07AE on): picture 9200, sound 0x26, then until an event,
    /// 300 clock3 units or the window closing: every 0x1E clock3 units frame 9200 + i (i = 1, 2, 3, 2, 3, ...) at the
    /// picture's corner + (T:0B14, T:0B16)[i] ((38, 39), (38, 52), (38, 52)), with sound 0x25 for odd i.</summary>
    IEnumerator<bool> AntLionScene()
    {
        OpenScene(9200);
        PlaySound(0x26);
        var st = session.St;
        double end = UiTicks * 3 + 300, next = UiTicks * 3 + 0x1e;
        int i = 1;
        while (!presentPress && !presentKey && UiTicks * 3 < end)
        {
            if (UiTicks * 3 >= next)
            {
                next = UiTicks * 3 + 0x1e;
                sceneOverlay = (9200 + i, st.S16(Seg.T, 0xb14 + 4 * i), st.S16(Seg.T, 0xb16 + 4 * i));
                if ((i & 1) != 0) PlaySound(0x25);
                if (++i > 3) i = 2;
            }
            yield return true;
        }
    }

    /// <summary>f_7686d(picture, n) (T:07AE on): 9100 "Your ant has been killed" / 9101 "You have been reborn!" or
    /// "You are now a worker!" (STR# 1010 [23 + n] in the strip, then f_011e5(300)); 9110 a nestmate feeds the yellow
    /// ant (sound 0x2A, f_011e5(0x2D), 9111 at T:0B24 / T:0B26 = (72, 62), sound 0x2D, f_011e5(0x2D)).</summary>
    IEnumerator<bool> PictureScene(int pic, int n)
    {
        OpenScene(pic);
        var st = session.St;
        if (pic is 0x238c or 0x238d)
        {
            sceneCaption = session.Files.Strings(1010) is { } l && 23 + n < l.Length ? l[23 + n] : null;
            foreach (var w in WaitTicks(300)) yield return w;
        }
        else if (pic == 0x2396)
        {
            PlaySound(0x2a);
            foreach (var w in WaitTicks(0x2d)) yield return w;
            sceneOverlay = (0x2397, st.S16(Seg.T, 0xb24), st.S16(Seg.T, 0xb26));
            PlaySound(0x2d);
            foreach (var w in WaitTicks(0x2d)) yield return w;
        }
    }

    /// <summary>f_71f52, the spider takes the yellow ant (T:07AE on): picture 12000, sound 0x2D, f_01277(8); until
    /// f_01572 or an event, every 8 clock3 units the next of 12001 + (0, 1, 2, 1)[i] (T:09B4) at the corner + (46,
    /// 77), sound 0x2D each time i wraps to 0; then (the sim drew Rand(2) for the line) the message box over it.</summary>
    IEnumerator<bool> SpiderScene(string[] lines)
    {
        OpenScene(12000);
        PlaySound(0x2d);
        ArmTimeout(8);
        var st = session.St;
        double next = UiTicks * 3 + 8;
        int i = 0;
        while (!presentPress && !KeyOrTimeout())
        {
            if (UiTicks * 3 >= next)
            {
                next = UiTicks * 3 + 8;
                if (++i > 3) { i = 0; PlaySound(0x2d); }
                sceneOverlay = (12001 + st.S16(Seg.T, 0x9b4 + 2 * i), 46, 77);
            }
            yield return true;
        }
        presentPress = presentKey = false;
        if (lines != null)
        {
            var box = MessageBoxP(lines, 0);
            while (box.MoveNext()) yield return true;
        }
    }

    // f_6e17e(n) (from f_2f816, the PAUSE button and Speed > Pause): unpausing in the Exchange / Chase modes cancels
    // them (f_11b5f / f_11aff: G:105E = -1); G:047E = n; the timed line (f_15e2c, lasting) STR# 1010 [2] "Game
    // Paused", [3] while choosing the ant to exchange with (G:105E 10), [17] while choosing the ant to chase (11);
    // unpaused, the line is cleared. f_71a7d(flag) shows the same line without changing anything.
    void SetPause(int n)
    {
        var st = session.St;
        if (n == 0 && st.U16(Seg.G, 0x105e) is 0xa or 0xb) st.Set16(Seg.G, 0x105e, 0xffff);
        st.Set16(Seg.G, 0x47e, n);
        PauseLine(1);
    }

    void PauseLine(int flag)
    {
        var st = session.St;
        int k = st.U16(Seg.G, 0x47e) == 0 ? -1 : st.U16(Seg.G, 0x105e) switch { 0xffff => 2, 0xa => 3, 0xb => 17, _ => -2 };
        if (k == -2) return;
        string text = k < 0 ? null : session.Files.Strings(1010) is { } l && k < l.Length ? l[k] : null;
        ShowStatus(text, -1, flag != 0 || k < 0);
    }

    /// <summary>f_12de1's screen part ("menu" n): 0 eating: sound 0x2C, f_71a7d(1); 1 fed by a nestmate: the 9110
    /// scene, then "You feel much better now!" (STR# 1010 [11], 0x78); 2 [12] "Thank you for your contribution";
    /// 3 eating brood: sound 0x2C, sound 10, [13] "Cannibalism has restored your health" (0xB4).</summary>
    void MenuEffect(int n)
    {
        string S(int k) => session.Files.Strings(1010) is { } l && k < l.Length ? l[k] : null;
        switch (n)
        {
            case 0: PlaySound(0x2c); PauseLine(1); break;
            case 1:
                if (session.St.U16(Seg.T, 0x7ae) != 0) Present(() => PictureScene(0x2396, -1));
                Present(() => After(() => ShowStatus(S(11), 0x78, false)));
                break;
            case 2: ShowStatus(S(12), 0x78, false); break;
            case 3: PlaySound(0x2c); PlaySound(10); ShowStatus(S(13), 0xb4, false); break;
        }
    }

    /// <summary>f_7c149 / f_7c3b1's frames: the Edit window drawn from each frame's State (f_03391), its sounds,
    /// then 6 clock3 units.</summary>
    State animState;

    IEnumerator<bool> AnimP(List<(State st, List<object[]> sounds)> frames)
    {
        foreach (var (fs, sounds) in frames)
        {
            animState = fs;
            foreach (var sd in sounds)
                if (sd.Length > 0 && sd[0] is int n && n < SoundBank.EffectCount && session.St.U16(Seg.T, 0x7ac) != 0) PlaySound(n);
            double until = UiTicks * 3 + 6;
            while (UiTicks * 3 < until) yield return true;
        }
        animState = null;
    }

    static IEnumerator<bool> After(Action a)
    {
        a();
        yield break;
    }

    // ------------------------------------------------------------------------------- windows
    /// <summary>The windows' titles, STR# 1000 (G:046C): 0..8 the Map window's content T:07C8 (BackYard, Surface,
    /// Black Nest, Red Nest View, the five pheromone maps), 9..12 the yard window's modes G:035C (Yard, House,
    /// Strategic, Graphic View).</summary>
    string Title(int k)
    {
        var l = session.Files.Strings(1000);
        return l != null && k >= 0 && k < l.Length ? l[k] : "";
    }

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
        // f_03bfd (from the game's start f_725b6 / f_7256f and the Experimental menu): "SimAnt" + STR# 1800 [15] " - " +
        // the game mode's name (STR# 1001, G:0324)
        var modes = session.Files.Strings(1001);
        int gm = st.U16(Seg.G, 0xeac);
        string title = "SimAnt" + (session.Files.Strings(1800)?[15] ?? " - ") + (modes != null && gm < modes.Length ? modes[gm] : "");
        ui.DrawWindow(c, EditWin, dx, dy, title, new[] { 15001 });
        var win = c.Clip(WindowRect(EditWin).l, WindowRect(EditWin).t, WindowRect(EditWin).r, WindowRect(EditWin).b);
        var m = ItemRect(EditWin, EditMapItem);
        int w = Cols * Cell, h = Rows * Cell;
        // in the yard (G:032E = 0) the map shows view 0, the surface; the view buttons keep their selection (f_01976)
        int shown = st.U16(Seg.G, 0x32e) == 0 ? 1 : view;
        int cols = Math.Min(Cols, MapRenderer.Width(shown));
        Array.Fill(mapBuf, 0xff000000u);
        MapRenderer.Render(animState ?? st, session.Art, shown, originA, originB, originA + cols, originB + Rows, mapBuf, w);
        if (shown == 1)
            SpiderRenderer.Draw(st, session.Files, session.Art, mapBuf, w, h, originA * Cell, originB * Cell, SpiderRenderer.FangJitter(st));
        win.Clip(m.l, m.t, m.r, m.b).Blit(mapBuf, w, h, m.l, m.t);
        var strip = ItemRect(EditWin, EditMapStrip);
        win.Clip(strip.l, strip.t, strip.r, strip.b).Blit(mapBuf, w, h, m.l, m.t);
        ui.DrawDecorations(win, ui.Layouts[EditWin], dx, dy);                         // the grow box stays above the map's last row
        {
            var ti = ItemRect(EditWin, 7);                                             // the Experimental button's tool icon
            ui.DrawBitmap(win, (st.U16(Seg.G, 0xeac) == 3 ? 5100 + Math.Clamp(st.U16(Seg.G, 0x104c), 0, 7) : 5107), ti.l, ti.t);
            if (view is >= 1 and <= 3)                                                 // f_01976: items 8..10, the view shown
            {
                var vb = ItemRect(EditWin, 7 + view);
                win.Invert(vb.l, vb.t, vb.r, vb.b);
            }
        }
        if (session.Paused)                                                       // the PAUSE button while paused (G:047E)
        {
            var pr = ItemRect(EditWin, 15);
            win.Invert(pr.l, pr.t, pr.r, pr.b);
        }
        if (st.U16(Seg.G, 0x104e) != 0)                                            // f_22e9f(0x10, 1): SCENT while the alarm trail is on
        {
            var sr = ItemRect(EditWin, 16);
            win.Invert(sr.l, sr.t, sr.r, sr.b);
        }
        if (view == 1)                                                              // f_753e5: the spider's strikes
            foreach (var (x0, y0, x1, y1) in strikes)
            {
                var mc = win.Clip(m.l, m.t, m.r, strip.b);
                int ox = m.l - originA * Cell, oy = m.t - originB * Cell;
                Line(mc, ox + x0, oy + y0, ox + x1, oy + y1, session.Art.Palette[3]);
                Line(mc, ox + x0 + 1, oy + y0 + 1, ox + x1 + 1, oy + y1 + 1, session.Art.Palette[3]);
                mc.Fill(ox + x1, oy + y1, ox + x1 + 2, oy + y1 + 2, session.Art.Palette[2]);
            }
        // f_03a83, the health bars (items 0x11..0x13): the yellow ant G:0F78, the black colony G:10BE, the red colony
        // G:01FE out of 100; the filled part, bottom - height * v / 100 .. bottom, in the item's scheme foreground, the
        // rest in its background (schemes 4, 9, 10: yellow, black, red on light grey). Then the warning levels, a 1-px
        // line at top + (100 - level) * height / 100: the yellow ant's G:0FBA in black, the colony's hunger level
        // G:0FFE on the black bar through the driver's XOR fill (DS:913C; colour index ^ 15 assumed).
        var values = new[] { st.S16(Seg.G, 0xf78), st.S16(Seg.G, 0x10be), st.S16(Seg.G, 0x1fe) };
        for (int i = 0; i < 3; i++)
        {
            var (l, t, r, b) = ItemRect(EditWin, 17 + i);
            var (fg, bg) = ui.SchemeOf(ui.Layouts[EditWin].Items[17 + i]);
            int y = b - (int)((long)(b - t) * values[i] / 100);
            win.Fill(l, t, r, Math.Min(Math.Max(y, t), b), bg);
            win.Fill(l, Math.Min(Math.Max(y, t), b), r, b, fg);
        }
        {
            var (l, t, r, b) = ItemRect(EditWin, 17);
            int y = (100 - st.S16(Seg.G, 0xfba)) * (b - t) / 100 + t;
            win.Fill(l, y, r, y + 1, session.Art.Palette[15]);
            (l, t, r, b) = ItemRect(EditWin, 18);
            y = (100 - st.S16(Seg.G, 0xffe)) * (b - t) / 100 + t;
            for (int x = Math.Max(l, win.L); x < Math.Min(r, win.R); x++)
                if (y >= win.T && y < win.B)
                {
                    int k = Array.IndexOf(session.Art.Palette, win.Px[y * win.Stride + x]);
                    if (k >= 0) win.Px[y * win.Stride + x] = session.Art.Palette[k ^ 15];
                }
        }
        if (help)
        {
            var it = ui.Layouts[EditWin].Items.First(x => x.Bitmap == 15001);
            ui.DrawBitmap(win, 15001, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    // f_6776f, the Edit window's MAP button: window 20 (64,44 .. 196,112) pops up with the Edit view's whole map at 1 px
    // per cell in its item 0x1401 (f_674ee: 128 x 64 cells, a nest 64 wide at offset 32 with black margins; the Map
    // window's scent layer T:07C8 4..8 drawn instead, f_2f8ca) and the Edit window's area as an XOR frame (f_678d8). A
    // press released over the MAP button closes it and opens the Map window (f_0148a: open, else to the front);
    // otherwise it stays: a press in the map (dragging while held) recentres the Edit window there (f_034c4). The game
    // waits meanwhile (a local event loop). A press outside it closes it (the window library's pop-up; assumed).
    const int MiniMapWin = 20;
    bool miniMap, miniMapPress, miniMapDrag;

    (int l, int t, int w, int off) MiniMapArea()
    {
        var (l, t, _, _) = ui.Layouts[MiniMapWin].Items[1].Rect;
        int w = MapRenderer.Width(view);
        return (l, t, w, w == 0x40 ? 32 : 0);
    }

    void DrawMiniMap(UiArt.Canvas c)
    {
        var st = session.St;
        ui.DrawWindow(c, MiniMapWin, 0, 0, null);
        var (l, t, w, off) = MiniMapArea();
        var item = ui.Layouts[MiniMapWin].Items[1].Rect;
        c.Fill(item.left, item.top, item.right, item.bottom, session.Art.Palette[15]);
        int content = MapContent;
        for (int b = 0; b < MapRenderer.Height; b++)
            for (int a = 0; a < w; a++)
            {
                int k;
                if (content >= 4 && content <= 8)
                {
                    int v = MapRenderer.Scent(st, MapRenderer.ScentMode(content), a, b);
                    k = MapRenderer.DitherIndex(session.Files.Flat, v == 0 ? 0x0b : 0x10 + (v >> 5), (a >> 2) & 1, a & 3, b);
                }
                else k = MapRenderer.MapColour(st, view, a, b);
                c.Plot(l + off + a, t + b, session.Art.Palette[k]);
            }
        int fl = l + off + originA, ft = t + originB, fr = fl + Cols, fb = ft + Rows;
        c.Clip(item.left, item.top, item.right, item.bottom).Invert(fl, ft, fr, ft + 1);
        c.Clip(item.left, item.top, item.right, item.bottom).Invert(fl, fb - 1, fr, fb);
        c.Clip(item.left, item.top, item.right, item.bottom).Invert(fl, ft + 1, fl + 1, fb - 1);
        c.Clip(item.left, item.top, item.right, item.bottom).Invert(fr - 1, ft + 1, fr, fb - 1);
    }

    void MiniMapRelease(Vector2 p)
    {
        miniMapPress = false;
        var (l, t, r, b) = ItemRect(EditWin, 5);
        if (p.X >= l && p.X < r && p.Y >= t && p.Y < b) { miniMap = false; ShowMap(); }
    }

    void MiniMapPress(Vector2 p)
    {
        var (l, t, r, b) = ui.Layouts[MiniMapWin].Rect;
        if (p.X < l || p.X >= r || p.Y < t || p.Y >= b) { miniMap = false; return; }
        miniMapDrag = MiniMapAt(p);
    }

    bool MiniMapAt(Vector2 p)
    {
        var (l, t, w, off) = MiniMapArea();
        var item = ui.Layouts[MiniMapWin].Items[1].Rect;
        if (p.X < item.left || p.X >= item.right || p.Y < item.top || p.Y >= item.bottom) return false;
        int a = (int)p.X - l - off, b = (int)p.Y - t;
        if (a >= 0 && a < w) { CenterOn(a, b); follow = false; }
        return true;
    }

    void EditWindowClick(int index, InputEventMouseButton mb)
    {
        var st = session.St;
        switch (index)
        {
            case EditMapItem: EditMapClick(mb); break;
            case 5: miniMap = true; miniMapPress = true; break;                      // MAP: f_6776f, window 20
            case 6: help = helpHeld = true; break;                                   // ?: f_714ab(2), while held
            case 17: case 18:                                                        // f_68044 / f_68002: the warning levels
            {
                var (_, t, _, b) = ItemRect(EditWin, index);
                st.Set16(Seg.G, index == 17 ? 0xfba : 0xffe, (b - (int)mb.Position.Y) * 100 / (b - t));
                break;
            }
            case 7: ExperimentalMenu(); break;
            case 8: SetView(1); break;
            case 9: SetView(2); break;
            case 10: SetView(3); break;
            case 11: FollowYellow(); break;                                          // f_01c52
            case 12:                                                                 // f_01ca5: the spider G:0F12 / G:0F34 (1/16 cell)
                if (st.U16(Seg.G, 0xf0c) == 0) { PlaySound(1); break; }              // none: f_00ed8(1, 0, 0x7E)
                GoTo(1, st.S16(Seg.G, 0xf12) >> 4, st.S16(Seg.G, 0xf34) >> 4);
                break;
            case 13: GotoQueen(2); break;
            case 14: GotoQueen(3); break;
            case 15: SetPause(session.Paused ? 0 : 1); break;                        // f_2f73a(G:047E == 0)
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
        bool act = mb.ButtonIndex == MouseButton.Right || mb.DoubleClick || mb.ShiftPressed;   // event byte +7 & 0x60
        if (target == 0xa) { Commands.ExchangeClick(st, view, a, b); return; }       // Exchange: pick the ant to become
        if (target == 0xb)
        {
            if (view <= 1 && st.U16(Seg.G, 0xa06) == 1) Commands.SpiderClick(st, a, b, act ? 1 : 0);
            return;
        }
        if (!act && mb.ButtonIndex == MouseButton.Left)
        {
            pendingClick = (a, b, mb.Position, 0);                                  // wait for a second click
            return;
        }
        pendingClick = null;
        MapAction(a, b, true, false, mb.Position);
    }

    // f_74fe0, the Edit map's mouse handler outside the Experimental game and the pick-a-target modes. A left press
    // waits up to 6 clock ticks for a second one (a double click; the right button counts as one at once, and here
    // Shift too): that makes it an action. Then, without one: on the yellow ant (f_134b8 at its own view) a button
    // still held opens its menu (f_2f8e8 → f_67e93), a released one recentres on it (f_01c03, G:1074 = 1); a held
    // press on another ant shows Ant Info (f_2f8fc); otherwise a walk (mode G:0A8E = 0). With one: another ant (not
    // the yellow one, caste > 7) becomes the target to meet (f_11327 → G:07C0; mode 4 for a colony-mate, 3 for an
    // enemy; G:084E, G:08DA, G:08E2 / G:09F0); on the surface mode 1 (act on the cell); in a nest mode 1 (pick up /
    // drop) where there is food, a rock or brood or the ant carries something, else 2 (dig). The spider on the
    // surface takes the click as its own (f_756a6). The target is set by f_75869 (GameSession.SetTarget).
    (int a, int b, Vector2 at, double waited)? pendingClick;

    void PendingClick(double delta)
    {
        if (pendingClick is not { } p) return;
        p.waited += delta;
        pendingClick = p;
        if (p.waited < 6 / GameSession.ClockHz) return;
        pendingClick = null;
        MapAction(p.a, p.b, false, Input.IsMouseButtonPressed(MouseButton.Left), p.at);
    }

    void MapAction(int a, int b, bool act, bool held, Vector2 at)
    {
        var st = session.St;
        int v = view;
        st.Set16(Seg.G, 0xf44, 0);
        bool spider = st.U16(Seg.G, 0xa06) != 0;
        if (!act)
        {
            if (DebugCommands.PlayerAt(st, st.U16(Seg.G, 0x48c), a, b) == 1)
            {
                if (held) OpenPopup((int)at.X, (int)at.Y);
                else if (Player.GetOcc(st, st.U16(Seg.G, 0x48c), a, b) != 0xfe)
                {
                    st.Set16(Seg.G, 0x1074, 1);                                       // f_01c03
                    SetView(session.Yellow.view);
                    CenterOnYellow();
                }
                return;
            }
            if (held && AntInfo(a, b) != null) { OpenAntInfo(a, b); return; }
        }
        else if (!spider && Player.GetOcc(st, v, a, b) is int o && o >= 0 && (o & 0x7f) > 7 && !Movement.IsYellow(o))
        {
            int i = Player.FindAntExact(st, v, a, b, o);
            st.Set16(Seg.G, 0x7c0, i);
            if (i < 0) return;
            st.Set16(Seg.G, 0xa8e, ((st.U8(Seg.G, 0x4e2) ^ o) & 0x80) == 0 ? 4 : 3);
            st.Set16(Seg.G, 0x84e, o);
            st.Set16(Seg.G, 0x8da, v == 0 ? 1 : v);
            st.Set16(Seg.G, 0x8e2, a);
            st.Set16(Seg.G, 0x9f0, b);
            session.SetTarget(v, a, b);
            return;
        }
        if (v < 2)
        {
            if (spider)
            {
                if (st.U16(Seg.G, 0xa06) == 1) Commands.SpiderClick(st, a, b, act ? 1 : 0);
                return;
            }
            st.Set16(Seg.G, 0xa8e, act ? 1 : 0);
        }
        else
        {
            if (spider) return;
            int mode = 0;
            if (act)
            {
                mode = 2;
                if (!Player.IsDirt(st, v, a, b))
                {
                    int t = Player.GetTile(st, v, a, b);
                    bool digTop = st.U16(Seg.G, 0x48c) > 1 && b < 1 && (NestGrid.IsDiggable(t) || (0x1c <= t && t <= 0x1f));   // f_11654
                    var (bt, _) = Player.BroodAt(st, v, a, b);
                    bool pickable = Player.IsFood(st, v, t) || Player.IsRock(v, t) || Player.IsBrood(bt);                // f_135de
                    if (!digTop && ((st.U16(Seg.G, 0x4c2) & 8) != 0 || pickable)) mode = 1;
                }
            }
            st.Set16(Seg.G, 0xa8e, mode);
        }
        session.SetTarget(v, a, b);
    }

    /// <summary>f_01cee / f_01d0f: the black / red queen's spot T:02B4 / T:02B6 and T:02B8 / T:02BA (where she lays),
    /// through f_01aa7.</summary>
    void GotoQueen(int nest)
    {
        var st = session.St;
        int o = nest == 2 ? 0x2b4 : 0x2b8;
        GoTo(nest, st.S16(Seg.T, o), st.S16(Seg.T, o + 2));
    }

    /// <summary>f_01aa7(view, a, b): in that view already, recentre (f_034c4) and G:0AA6 = 0; else switch to it centred
    /// there (f_01976).</summary>
    void GoTo(int v, int a, int b)
    {
        if (view == v) session.St.Set16(Seg.G, 0xaa6, 0);
        else SetView(v);
        CenterOn(a, b);
        follow = false;
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

    // f_15f84's main loop draws the screen after each SimStep, but at Ultra (T:07CC = 3) only when its frame counter
    // G:0A9C & 3 is 0 (the counter goes + 1 & 63 every loop). The Map window (f_2f6e0 → f_6f46a: f_6efd6 and the
    // population report f_6eea5) is drawn every such loop while G:0AA6 < 0, the mouse button is down (f_23612) or at
    // Ultra (G:0AA6 = 0 then); otherwise, while G:04C0 == 0, on every other loop (G:0AA6 bit 0, toggled each loop). So
    // the Map window lags the game by up to a tick. The shell keeps the State the Map window last drew (mapSt) and its
    // own counter and toggle (the sim never reads G:0A9C / G:0AA6); while the game does not advance it follows the game.
    State mapSt;
    bool mapLive = true;
    int mapFrame, mapToggle;

    void MapLoops(int ticks)
    {
        var st = session.St;
        bool due = false;
        for (int i = 0; i < ticks; i++)
        {
            bool ultra = st.U16(Seg.T, 0x7cc) == 3;
            if (!ultra || (mapFrame & 3) == 0)
            {
                if ((short)mapToggle < 0 || Input.IsMouseButtonPressed(MouseButton.Left) || ultra) { due = true; mapToggle = 0; }
                else if (st.U16(Seg.G, 0x4c0) == 0)
                {
                    due |= (mapToggle & 1) != 0;
                    mapToggle ^= 1;
                }
            }
            mapFrame = (mapFrame + 1) & 0x3f;
        }
        mapLive = false;
        if (due || mapSt == null) SnapMap();
    }

    void SnapMap()
    {
        var st = session.St;
        mapSt ??= new State(new byte[State.Size]);
        Array.Copy(st.Mem, mapSt.Mem, State.Size);
        mapSt.Clock = st.Clock;
        mapSt.BiosKbd = st.BiosKbd;
    }

    /// <summary>The State the Map window shows: the one it last drew while the game runs, else the game's.</summary>
    State MapState => mapLive || mapSt == null ? session.St : mapSt;

    void DrawMapWindow(UiArt.Canvas c)
    {
        var st = MapState;
        var (dx, dy) = Off(MapWin);
        int content = MapContent;
        string title = Title(content <= 8 ? content : MapView);
        ui.DrawWindow(c, MapWin, dx, dy, title, new[] { 14001 });
        var wr = WindowRect(MapWin);
        var win = c.Clip(wr.l, wr.t, wr.r, wr.b);
        var m = ItemRect(MapWin, MapMapItem);
        var area = win.Clip(m.l, m.t, m.r, m.b);
        area.Fill(m.l, m.t, m.r, m.b, session.Art.Palette[15]);                // a nest's margins are black (the original's screen)
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
                    // f_6eb66: v ? 0x10 + (v >> 5) : 0x0B; the 0x10.. colours are the driver's dither patterns
                    int v = MapRenderer.Scent(st, MapRenderer.ScentMode(content), a, b);
                    int cb = v == 0 ? 0x0b : 0x10 + (v >> 5);
                    for (int py = 0; py < 4; py++)
                        for (int px = 0; px < 4; px++)
                            area.Plot(x0 + a * 4 + px, y0 + b * 4 + py, session.Art.Palette[MapRenderer.DitherIndex(session.Files.Flat, cb, a, px, py)]);
                    continue;
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
        // f_6efd6: the spider (in its row loop) and f_6f5e1 while the view is the surface (G:032E = 1) and Show Trails is
        // off (DS:2994 = 0), over any content (a scent map too; the original's screen)
        if (st.U16(Seg.G, 0x32e) == 1 && st.U16(Seg.DS, 0x2994) == 0)
        {
            // f_6f505: the small spider, bitmap 1100 + G:1004 at its cell x 4 - 3, while G:0F0C != 0; f_6f5e1: while
            // T:0C3E (the human on the patch) the sneaker 1200 + T:0C30 at (G:03E0, G:046A) x 4, and then while mowing (T:0C28 3 or 4) the
            // mower 1210 + (T:0C30 & 1) at (G:0470, G:047A) x 4
            if (st.U16(Seg.G, 0xf0c) != 0)
                ui.DrawBitmap(area, 1100 + st.U16(Seg.G, 0x1004), x0 + (st.S16(Seg.G, 0xf12) >> 4) * 4 - 3, y0 + (st.S16(Seg.G, 0xf34) >> 4) * 4 - 3);
            if (st.U16(Seg.T, 0xc3e) != 0)                                                  // both only while the human is here
            {
                ui.DrawBitmap(area, 1200 + st.U16(Seg.T, 0xc30), x0 + st.S16(Seg.G, 0x3e0) * 4, y0 + st.S16(Seg.G, 0x46a) * 4);
                if (st.U16(Seg.T, 0xc28) is 3 or 4)
                    ui.DrawBitmap(area, 1210 + (st.U16(Seg.T, 0xc30) & 1), x0 + st.S16(Seg.G, 0x470) * 4, y0 + st.S16(Seg.G, 0x47a) * 4);
            }
        }
        if (mv == 1 && content == 1)                                                        // f_753e5 in the Map window, 4 px per cell
            foreach (var (sx0, sy0, sx1, sy1) in strikes)
            {
                Line(area, x0 + sx0 / 16 * 4, y0 + sy0 / 16 * 4, x0 + sx1 / 16 * 4, y0 + sy1 / 16 * 4, session.Art.Palette[3]);
                Line(area, x0 + sx0 / 16 * 4 + 1, y0 + sy0 / 16 * 4 + 1, x0 + sx1 / 16 * 4 + 1, y0 + sy1 / 16 * 4 + 1, session.Art.Palette[3]);
                area.Fill(x0 + sx1 / 16 * 4, y0 + sy1 / 16 * 4, x0 + sx1 / 16 * 4 + 2, y0 + sy1 / 16 * 4 + 2, session.Art.Palette[2]);
            }
        // f_6efd6: the timed message's copy (DS:299A) at the top of this map too, then the Edit window's area (G:0508 /
        // G:050A, G:10E0 x G:10DE cells) as a 2-px XOR frame inside it (f_6e702, drawn once, DS:298E = 1). f_01024 erases
        // it (DS:298E = 0) before the Edit view moves or a window changes and marks the map for a redraw; a modal window
        // (Status, message boxes) runs its own loop, so the frame stays off until it closes. A --state image holds DS:298E.
        DrawStatusMessage(area, m);
        bool frame = frozen ? st.U16(Seg.DS, 0x298e) != 0 : modal < 0 && !Presenting;
        if (mv == view && frame)
        {
            int l = x0 + originA * 4, t = y0 + originB * 4, r = l + Cols * 4, b = t + Rows * 4;
            area.Invert(l, t, r, t + 2);
            area.Invert(l, b - 2, r, b);
            area.Invert(l, t + 2, l + 2, b - 2);
            area.Invert(r - 2, t + 2, r, b - 2);
        }
        {
            // the Experimental button shows the current tool's icon 5100 + G:104C in every game (the original's screen)
            var ti = ItemRect(MapWin, 23);
            ui.DrawBitmap(win, (st.U16(Seg.G, 0xeac) == 3 ? 5100 + Math.Clamp(st.U16(Seg.G, 0x104c), 0, 7) : 5107), ti.l, ti.t);
            // f_01976: the button of the view shown (0x105 + G:032E) highlighted (f_22fae, the XOR), and with a scent map
            // shown (f_01781: T:07C8 4 / 5 / 8 / 6 / 7 from 0x109..0x10D) its button too (the original's screen)
            int gv = st.U16(Seg.G, 0x32e);
            if (gv <= 3)
            {
                var vb = ItemRect(MapWin, 5 + gv);
                win.Invert(vb.l, vb.t, vb.r, vb.b);
            }
            int scentItem = MapContent switch { 4 => 9, 5 => 10, 8 => 11, 6 => 12, 7 => 13, _ => -1 };
            if (scentItem > 0)
            {
                var sb = ItemRect(MapWin, scentItem);
                win.Invert(sb.l, sb.t, sb.r, sb.b);
            }
        }
        // the population report f_6eea5: counts 0x119 / 0x11A, gauges 0x11B black health (G:10BE / 100), 0x11C red
        // health (G:01FE / 100, 0 without red ants), 0x11D / 0x11E each population / max(1, black, red)
        int black = st.U16(Seg.G, 0x330), red = st.U16(Seg.G, 0x350), most = Math.Max(1, Math.Max(black, red));
        // the counts in font 3 (0 at 320 px), centred in the item, their row filled in its scheme (f_23943 → f_20a0f:
        // black / red on white); the gauges f_23971: the item from its left to left + width x fraction (16.16) in the
        // scheme's foreground (DS:3DE0), the rest in its background (DS:3DE2), no frame of their own (the original's screen)
        var items = ui.Layouts[MapWin].Items;
        void Count(int index, int n)
        {
            var (l, t, r, b) = ItemRect(MapWin, index);
            var (fg, bg) = ui.SchemeOf(items[index]);
            var f = ui.Font(3);
            string text = n.ToString();
            int x = Math.Max(l, (l + r - f.Width(text)) / 2), y = t + (b - t - f.Height) / 2;
            var ic = win.Clip(l, t, r, b);                                         // f_232ae clips to the item (f_1ece3)
            ic.Fill(l, y, r, y + f.Height, bg);
            f.Draw(ic, x, y, text, fg);
        }
        void Bar(int index, double fraction)
        {
            var (l, t, r, b) = ItemRect(MapWin, index);
            var (fg, bg) = ui.SchemeOf(items[index]);
            int split = l + (int)((r - l) * (long)(Math.Clamp(fraction, 0, 1) * 65536) >> 16);
            if (l < split) win.Fill(l, t, split, b, fg);
            if (split < r) win.Fill(split, t, r, b, bg);
        }
        Count(25, black);
        Count(26, red);
        Bar(27, st.S16(Seg.G, 0x10be) / 100.0);
        Bar(28, red == 0 ? 0 : st.S16(Seg.G, 0x1fe) / 100.0);
        Bar(29, black / (double)most);
        Bar(30, red / (double)most);
        if (help)
        {
            var it = ui.Layouts[MapWin].Items.First(x => x.Bitmap == 14001);
            ui.DrawBitmap(win, 14001, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    void MapWindowClick(int index, InputEventMouseButton mb)
    {
        var st = session.St;
        switch (index)
        {
            case MapMapItem:
            {
                // f_6726a: the right button re-sends the click to the Edit map as an action (flags 0x2000 →
                // f_74fe0); the left one recentres the Edit window on the cell under the mouse for as long as it is held
                var (x0, y0) = MapOrigin();
                int a = (int)(mb.Position.X - x0) / 4, b = (int)(mb.Position.Y - y0) / 4;
                if (a < 0 || a >= MapRenderer.Width(MapView) || b >= MapRenderer.Height) break;
                SetView(MapView);
                if (mb.ButtonIndex == MouseButton.Right) { MapAction(a, b, true, false, mb.Position); break; }
                CenterOn(a, b);
                follow = false;
                mapDrag = true;
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
                // f_01781(n): the same layer again shows the surface (1); a layer switches the Edit window to the surface
                int content = ScentButtons[index - 9];
                if (MapContent == content) content = 1;
                if (view != 1) SetView(1);
                st.Set16(Seg.T, 0x7c8, content);
                break;
            }
            case 14:                                                                     // Show Trails: DS:2994 ^= 1 (f_6e5c0)
                st.Set16(Seg.DS, 0x2994, st.U16(Seg.DS, 0x2994) == 0 ? 1 : 0);
                break;
            case 15: Front(BehaviorWin); break;                                          // 0x10F → f_07aab: f_21336(0x1200), opens
            case 17: Front(CasteWin); break;                                             // 0x111 → f_07a95
            case 16:                                                                     // 0x110 → f_6f733
            {
                // the BIOS shift flags: no Ctrl f_01c52; Ctrl + Shift add (with Alt kill) surface ants, black in the
                // button's left half, red in its right (f_015be / f_0161f); Ctrl + Alt sound 0x20 and all food cleared
                // (f_01707); Ctrl alone food dropped (f_6bca5(0x96, 1))
                if (!mb.CtrlPressed) { FollowYellow(); break; }
                if (mb.ShiftPressed)
                {
                    var (l, _, r, _) = ItemRect(MapWin, 16);
                    bool black = mb.Position.X <= (l + r) / 2;
                    if (mb.AltPressed) DebugCommands.KillAnts(st, black);
                    else DebugCommands.AddAnts(st, black);
                }
                else if (mb.AltPressed) { PlaySound(0x20); DebugCommands.ClearFood(st); }
                else Colony.DropFood(st, 0x96, 1);
                break;
            }
            case 18: DebugCommands.RandomAction(st); break;                              // the Mystery Button (f_022bc)
            case >= 24 and <= 30: popReport = true; break;                               // held: the population report
            case 19: Front(HistoryWin); break;                                           // 0x113 → f_792c7: f_21336(0x1500)
            case 20: OpenEfficiency(); break;
            case 22: st.Set16(Seg.G, 0x1074, 1); help = helpHeld = true; break;         // ?: G:1074 = 1, f_714ab(0x103) while held
            case 23: ExperimentalMenu(); break;                                         // 0x117 → f_2f88e
            case 21: OpenAntipedia(); break;                                            // 0x115 → thunk 0x2f9b0 → f_78db9
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
        // f_67e93 → f_2379b → f_21336(window, x, y): the press point is the requested rectangle's corner; the layout's
        // item 0 sits at an offset from it (7: (16, 8), 8: (0, 0), 32: (4, 8)), kept on the screen (UiArt.Open)
        var at = ui.Open(popup, (x, y, x, y), st.S16(Seg.G, 0x3942) is > 0 and var top ? top : 17);
        var (l, t, _, _) = ui.Layouts[popup].Rect;
        popupOff = (at.Rect.left - l, at.Rect.top - t);
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

    // ------------------------------------------------------------------------------- the pull-down menus
    // SHARED type 6 (Formica.Data.Menus): File, Window, View, Options, Speed across the top of the screen in font 1.
    // f_6d7e3 (event 0xFE00 + m: a press on a title, Alt+F / W / V / O / S or F2..F6) shows the title inverted and
    // runs the menu f_6d9a4: while the button is held, releasing on an item picks it; after a click the menu stays
    // open until the next one. Keys: Down / + and Up / - move past separators, Left / Right the next menu (scan codes
    // 'K' / 'M'), a letter the next item starting with it, Enter or Space picks, Esc closes. A pick posts 0xFD00 +
    // 16 m + n + 1 (MenuCommand). The game waits while a menu is open, as in the original's menu loop.
    Menus menus;
    int menuOpen = -1, menuHot = -1;
    bool menuHeld;

    void OpenMenu(int m)
    {
        menuOpen = m;
        menuHot = -1;
    }

    void CloseMenu() => menuOpen = menuHot = -1;

    bool Selectable(int m, int i) => i >= 0 && i < menus.Items[m].Length && !Menus.IsSeparator(menus.Items[m][i])
                                     && (menus.Items[m][i][0] & Menus.Disabled) == 0;

    /// <summary>The next selectable item after `from` in direction `dir`, wrapping (f_6d9a4's + / -).</summary>
    int NextItem(int m, int from, int dir)
    {
        int n = menus.Items[m].Length;
        for (int k = 1; k <= n; k++)
        {
            int i = ((from + dir * k) % n + n) % n;
            if (Selectable(m, i)) return i;
        }
        return -1;
    }

    void PickItem(int m, int i)
    {
        CloseMenu();
        if (Selectable(m, i)) MenuCommand(Menus.Command(m, i));
    }

    /// <summary>f_6e0e0 before a menu is shown: ► on the speed T:07CC (items 0x42..0x45) and on each Options flag
    /// that is on (T:07A8 + 2 n, items 0x30..0x35); the Pause item reads " Unpause" while paused.</summary>
    void MenuMarks()
    {
        var st = session.St;
        for (int si = 0x43; si <= 0x46; si++)
            menus.SetState(si - 1, st.U16(Seg.T, 0x7cc) == si - 0x43 ? Menus.Checked : Menus.Plain);
        menus.SetText(0x41, session.Paused ? " Unpause" : " Pause");
        for (int n = 0; n < 6; n++) menus.SetState(0x30 + n, session.Option(n) ? Menus.Checked : Menus.Plain);
    }

    bool MenuInput(InputEvent ev)
    {
        if (menus == null) return false;
        if (ev is InputEventMouseButton mb && mb.ButtonIndex == MouseButton.Left)
        {
            int x = (int)mb.Position.X, y = (int)mb.Position.Y, m = menus.TitleAt(x, y);
            if (mb.Pressed)
            {
                if (menuOpen >= 0)
                {
                    int i = menus.ItemAt(menuOpen, x, y);
                    if (m >= 0 && m != menuOpen) { OpenMenu(m); menuHeld = true; }
                    else if (i >= 0) PickItem(menuOpen, i);
                    else CloseMenu();
                    return true;
                }
                if (modal >= 0 || y >= menus.BarHeight) return false;
                if (m >= 0 && (menus.Items[m].Length > 0))
                {
                    MenuMarks();
                    OpenMenu(m);
                    menuHeld = true;
                }
                return true;                                                    // the bar itself does nothing
            }
            if (menuOpen < 0) return false;
            if (menuHeld)
            {
                menuHeld = false;
                int i = menus.ItemAt(menuOpen, x, y);
                if (i >= 0) PickItem(menuOpen, i);
                else if (m != menuOpen) CloseMenu();                            // released on the title: a click, it stays open
            }
            return true;
        }
        if (ev is InputEventMouseMotion mm && menuOpen >= 0)
        {
            int x = (int)mm.Position.X, y = (int)mm.Position.Y, m = menus.TitleAt(x, y);
            if (m >= 0 && m != menuOpen && (menuHeld || mm.ButtonMask.HasFlag(MouseButtonMask.Left))) OpenMenu(m);
            int i = menus.ItemAt(menuOpen, x, y);
            if (Selectable(menuOpen, i)) menuHot = i;
            else if (menuHeld) menuHot = -1;
            return true;
        }
        if (ev is InputEventKey k && k.Pressed)
        {
            int n = menus.Titles.Length;
            if (menuOpen < 0)
            {
                int m = k.AltPressed ? k.Keycode switch { Key.F => 0, Key.W => 1, Key.V => 2, Key.O => 3, Key.S => 4, _ => -1 }
                    : k.CtrlPressed || k.ShiftPressed ? -1
                    : k.Keycode switch { Key.F2 => 0, Key.F3 => 1, Key.F4 => 2, Key.F5 => 3, Key.F6 => 4, _ => -1 };
                if (m < 0 || m >= n || modal >= 0 || k.Echo) return false;
                MenuMarks();
                OpenMenu(m);
                menuHot = NextItem(m, -1, 1);
                return true;
            }
            switch (k.Keycode)
            {
                case Key.Escape: CloseMenu(); break;
                case Key.Enter or Key.KpEnter or Key.Space:
                    if (menuHot >= 0) PickItem(menuOpen, menuHot); else CloseMenu();
                    break;
                case Key.Down or Key.KpAdd or Key.Equal: menuHot = NextItem(menuOpen, menuHot, 1); break;
                case Key.Up or Key.KpSubtract or Key.Minus: menuHot = NextItem(menuOpen, menuHot < 0 ? 0 : menuHot, -1); break;
                case Key.Left or Key.Right:
                    OpenMenu(((menuOpen + (k.Keycode == Key.Left ? -1 : 1)) % n + n) % n);
                    menuHot = NextItem(menuOpen, -1, 1);
                    break;
                case >= Key.A and <= Key.Z:
                    for (int s = 1; s <= menus.Items[menuOpen].Length; s++)
                    {
                        int i = (Math.Max(menuHot, -1) + s) % menus.Items[menuOpen].Length;
                        var item = menus.Items[menuOpen][i];
                        if (Selectable(menuOpen, i) && item.Length > 1 && char.ToUpperInvariant(item[1]) == (char)k.Keycode)
                        {
                            menuHot = i;
                            break;
                        }
                    }
                    break;
            }
            return true;
        }
        return false;
    }

    // The bar and menus in f_1ffd1's colours (DS:5FEA cyan, DS:5FEC dark grey, DS:5FEE light grey after start-up):
    // normal cyan text on dark grey, highlighted swapped, disabled cyan on light grey (highlighted dark grey on light
    // grey); text in 8 x 14 cells (f_1fbd0). Measured on the original's screen (tools/re/screens.py, menu.png).
    uint MenuText => session.Art.Palette[7];
    uint MenuBack => session.Art.Palette[14];

    void MenuCells(UiArt.Canvas c, int x, int y, string text, uint fg, uint bg)
    {
        var f = ui.Font(Menus.Font);
        c.Fill(x, y, x + text.Length * Menus.CellW, y + Menus.CellH, bg);
        foreach (char ch in text)
        {
            if (ch != ' ') f?.Draw(c.Clip(x, y, x + Menus.CellW, y + Menus.CellH), x, y, ch.ToString(), fg);
            x += Menus.CellW;
        }
    }

    void DrawMenuBar(UiArt.Canvas c)
    {
        if (menus.Titles.Length == 0) return;
        c.Fill(0, 0, ScreenW, menus.BarHeight, MenuBack);
        for (int m = 0; m < menus.Titles.Length; m++)
        {
            var (l, t, r, b) = menus.TitleRect(m);
            bool open = m == menuOpen;
            MenuCells(c, l, t, menus.Titles[m], open ? MenuBack : MenuText, open ? MenuText : MenuBack);
        }
    }

    // f_6d9a4's box (measured): the outer area (l, t, l + 8 w + 11, b) in cyan, the inner (l + 7, t + 2, r - 2, b - 2)
    // in dark grey, the items from (l + 16, t + 3), one 14-px row each; a separator is a 1-px cyan line 6 px into its
    // row across w - 2 cells.
    void DrawMenu(UiArt.Canvas c)
    {
        MenuMarks();
        var (fr, _, _) = menus.Box(menuOpen);
        int w = menus.Width(menuOpen);
        int l = fr.l - 8, t = fr.t - 3, r = l + 8 * w + 11, b = fr.b + 3, x = l + 16, y = t + 3;
        c.Fill(l + 5, t, r, b, MenuText);                                       // a 2-px frame on every side (the original's screen)
        c.Fill(l + 7, t + 2, r - 2, b - 2, MenuBack);
        for (int i = 0; i < menus.Items[menuOpen].Length; i++)
        {
            int ry = y + i * Menus.CellH;
            if (Menus.IsSeparator(menus.Items[menuOpen][i]))
            {
                c.Fill(x, ry + 6, x + (w - 2) * Menus.CellW, ry + 7, MenuText);
                continue;
            }
            bool off = (menus.Items[menuOpen][i][0] & Menus.Disabled) != 0, hot = i == menuHot;
            string text = menus.Text(menuOpen, i);
            uint fg = hot ? MenuBack : MenuText, bg = off ? session.Art.Palette[12] : hot ? MenuText : MenuBack;
            MenuCells(c, x - Menus.CellW, ry, text, fg, bg);
        }
    }

    /// <summary>f_6e26d: a menu command 0xFDmn, from a menu or a key (SIM_NOTES "Keys and menu commands").</summary>
    void MenuCommand(int cmd)
    {
        var st = session.St;
        int n = cmd & 0xff;
        switch (n)
        {
            case 0x01: OpenAbout(); break;                                               // About: f_72931, window 0x1F00
            case 0x03: PlaySong(0x2711); modal = SelectWin; selectMidGame = true; break; // New: music 0x2711, f_2f848
            case 0x04: selectMidGame = st.U16(Seg.G, 0x2c2) != 0; Replace(4); break;   // Load: f_6c1a0 asks to save first
            case 0x05 or 0x06: SaveCommand(n == 5); break;                               // Save, Save As: f_6c328(1 / 0)
            case 0x08: pendingGame = 5; modal = SavePrompt; break;                       // Quit (save first?)
            case 0x11: Front(EditWin); break;                                            // f_03370
            case 0x12: ShowMap(); break;                                                 // f_0148a
            case 0x13: Front(BehaviorWin); break;                                        // f_07aab
            case 0x14: Front(CasteWin); break;                                           // f_07a95
            case 0x15: Front(HistoryWin); break;                                         // f_2f9ba
            case 0x16: OpenAntipedia(); break;                                           // Info: f_2f9b0, the SimAntipedia
            case 0x17: OpenEfficiency(); break;                                          // Status: f_2f9a6, the Efficiency Score
            case >= 0x21 and <= 0x24:                                                    // the yard window's mode G:035C
                if (!yardChoose) st.Set16(Seg.G, 0x35c, n - 0x21);
                OpenYard(false);
                break;
            case >= 0x26 and <= 0x28:                                                    // f_01aec(1 / 2 / 3): the Map window's view
                st.Set16(Seg.T, 0x7c8, n - 0x25);
                SetView(n - 0x25);
                break;
            case >= 0x31 and <= 0x36:                                                    // T:07A8 + 2 n
                session.ToggleOption(n - 0x31);
                if (n == 0x32 && !session.Option(1)) StopSong();                         // 0x32 also stops the music (f_285aa)
                break;
            case 0x41: SetPause(session.Paused ? 0 : 1); break;                          // G:047E ^= 1
            case >= 0x43 and <= 0x46: session.Speed = n - 0x43; break;                   // T:07CC = 0..3
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

    int boxPicture;

    void OpenMessageBox(string[] lines, int picture = 0)
    {
        boxLines = lines.Select(l => l.Replace("\n", " ")).ToArray();     // literal backslash-n breaks, as in the balloons
        boxPicture = picture;
        modal = 30;
    }

    /// <summary>f_71bb6: font 4 (3 at 320 px); the box is max(50, widest line) + 8 wide (the picture's width does not
    /// count) and (picture height + 2) + lines * font height + 8 tall, centred on the screen, opened as window 0x1E00
    /// (layout 30) at that rectangle: f_21336 re-lays its items (UiArt.Relayout), the 3D frame 5 / 4 px outside,
    /// the fill 2 px inside, "Click here to continue" in (l + 2, b - 13, r - 1, b - 2). The picture (HCEGANT bitmap,
    /// the tutorial's 17000..) is centred at the top, then each line (f_20983) in a font-height row from there.</summary>
    void DrawMessageBox(UiArt.Canvas c)
    {
        var f = ui.Font(4) ?? ui.Font(2);
        var (pw, ph, _) = boxPicture != 0 ? ui.Bitmap(boxPicture) : (0, 0, null);
        int lineH = f.Height, n = boxLines.Length;
        int w = Math.Max(0x32, boxLines.Select(f.Width).DefaultIfEmpty(0).Max()) + 8;
        int h = (ph > 0 ? ph + 2 : 0) + n * lineH + 8;
        int t = (ScreenH - h) / 2, l = (ScreenW - w) / 2, r = l + w, b = t + h;
        ui.DrawLayout(c, ui.Relayout(30, (l, t, r, b)));
        int y = t;
        if (ph > 0)
        {
            ui.DrawBitmap(c, boxPicture, (r - pw + l) / 2, y);
            y += ph + 2;
        }
        foreach (var line in boxLines)
        {
            ui.DrawText(c, 4, 0, l, y, r, y + lineH, line);
            y += lineH;
        }
    }

    // ------------------------------------------------------------------------------- the SimAntipedia (layout 5)
    // The Map toolbar's "Ant Info Window" (0x115 → thunk 0x2f9b0 → f_78db9) opens window 5 on card 128 (Top Card).
    // f_78808 draws the card (Formica.Data.Antipedia) into item 0x502 and its name into the caption 0x501;
    // f_790f0 follows the pictures' links (BACK / PREVIOUS / TOP, topics) and pops up a glossary definition while
    // the button is held on a bold word or a picture's ≤ 0 hotspot (f_78e1c). The window has no close box: here
    // Escape or a click outside it closes it.
    const int TextWin = 5;
    Antipedia antipedia;
    Antipedia.Card card;
    (int l, int t, int r, int b, List<Antipedia.Element> text)? cardPopup;

    void OpenAntipedia()
    {
        antipedia ??= new Antipedia(session.Files, ui.Font);
        antipedia.Open();
        ShowCard(Antipedia.TopCard);
        Front(TextWin);                                                       // at 640 px an ordinary window (f_21cc1 only at 320)
    }

    void ShowCard(int id)
    {
        var (l, t, _, _) = ui.Layouts[TextWin].Items[2].Rect;
        card = antipedia.Build(id, l, t);                                    // null: "Card Resource not found", an empty card
    }

    void AntipediaPress(int x, int y)
    {
        var w = ui.Layouts[TextWin];
        if (!Inside(w.Rect, new Vector2(x, y)))
        {
            modal = -1;
            return;
        }
        int before = antipedia.Current;
        int pop = antipedia.Click(card, x, y);
        if (antipedia.Current != before) ShowCard(antipedia.Current);
        if (pop > 0 && Antipedia.HitLink(card, x, y) is { } h)
        {
            var (il, it, ir, ib) = w.Items[2].Rect;
            cardPopup = antipedia.Popup(pop, (h.L + h.R) / 2, h.T, h.B, il, it, ir, ib);
        }
    }

    void DrawTextViewer(UiArt.Canvas c)
    {
        ui.DrawWindow(c, TextWin, 0, 0, card?.Name ?? "");
        var (l, t, r, b) = ui.Layouts[TextWin].Items[2].Rect;
        var area = c.Clip(l, t, r, b);
        area.Fill(l, t, r, b, UiArt.White);
        if (card != null) DrawElements(area, card.Draw);
        if (cardPopup is { } p)
        {
            area.Fill(p.l, p.t, p.r, p.b, UiArt.White);                         // f_1ce33: the box, a 1-px frame
            area.Frame(p.l, p.t, p.r, p.b, UiArt.Black);
            DrawElements(area.Clip(p.l + 1, p.t + 1, p.r - 1, p.b - 1), p.text);
        }
    }

    void DrawElements(UiArt.Canvas c, List<Antipedia.Element> elements)
    {
        foreach (var e in elements)
            if (e.Pict >= 0) ui.DrawBitmap(c, e.Pict, e.X, e.Y);
            else if (ui.Font(e.Font) is { } f) f.Draw(c, e.X, f.IsMac ? e.Y - 1 : e.Y, e.Text, UiArt.Black);  // f_24e3d: the strike from y - 1
    }

    // ------------------------------------------------------------------------------- the game-over window (layout 4)
    // f_71d95: window 0x400 (bitmap 16100: GAME OVER, FINAL SCORE, YOUR RATING) in font 4 (2 at 320 px wide):
    // 0x402 the mode's name (G:0324 = STR# 1001 [G:0EAC]), 0x403 the score ("%ld", DS:2B50; not divided by 5 in
    // a Full Game, only the rank is), 0x404 the rank's title (G:0328 = STR# 1900 [rank]). A click or key closes
    // it (or f_01277(100)'s timeout, ~100 s, not modelled); then the new-game dialog (f_2f848 → Select a Game).
    const int GameOverWin = 4;
    string[] gameOverText;

    void OpenGameOver(int rank, long score)
    {
        string Entry(int id, int k) => session.Files.Strings(id) is { } l && k >= 0 && k < l.Length ? l[k] : "";
        gameOverText = new[] { Entry(1001, session.St.U16(Seg.G, 0xeac)), score.ToString(), Entry(1900, rank) };
        modal = GameOverWin;
    }

    void DrawGameOver(UiArt.Canvas c)
    {
        ui.DrawWindow(c, GameOverWin, 0, 0, null);
        var items = ui.Layouts[GameOverWin].Items;
        for (int k = 0; k < 3; k++)                                          // f_23943: values in the items' schemes
        {
            var it = items[2 + k];
            var (l, t, r, b) = it.Rect;
            ui.DrawValue(c, 4, l, t, r, b, gameOverText[k], ui.SchemeOf(it).fg, ui.SchemeOf(it).bg);
        }
    }

    // ------------------------------------------------------------------------------- Select a Game (layout 2)
    // The new-game dialog f_725b6 (SIM_NOTES "Player events and the game flow"): bitmap 2500, buttons 0x202 Quick
    // Game (1), 0x203 Full Game (2), 0x204 Experimental (3), 0x205 Cancel, 0x206 the Tutorial (G:0EAC = 0, not
    // ported: World.Advisor's tutorial f_0e425), 0x207 Load Game. Shown at start-up and on F2.
    const int SelectWin = 2, TitleWin = 3, AboutWin = 31;               // the title (2000 / 2001), the about box (3000 / 3001)

    // f_72931, the about box (window 0x1F00): the logo (item 0x1F02, 3001) for 90 clock ticks, then the credits STR# 1700
    // roll up through that item, one pixel per tick, centred in font 4 (lines of its height, fRectHeight - 1) on the
    // item's background, with a 54-tick pause after the first pixel; at the end the logo again, and so on. A key or a
    // press counts as the end of a wait: on the logo it starts the roll while fewer than two waits have passed, during
    // the roll it closes the box once more than three have (f_1ccfc / f_01572 / f_21cb8 and the counter [bp - 0xA]).
    bool aboutRolling;
    int aboutLine, aboutPixel, aboutWaits;
    double aboutNext;

    void OpenAbout()
    {
        modal = AboutWin;
        aboutRolling = false;
        aboutWaits = 0;
        aboutNext = UiTicks + 0x5a;
    }

    void AboutStep()
    {
        aboutWaits++;
        if (!aboutRolling) { aboutRolling = true; aboutLine = aboutPixel = 0; aboutNext = UiTicks + 1; return; }
        var f = ui.Font(4);
        int fh = f.Height - 1;
        if (++aboutPixel == fh) { aboutPixel = 0; aboutLine++; }
        if (aboutLine >= (session.Files.Strings(1700)?.Length ?? 0)) { aboutRolling = false; aboutNext = UiTicks + 0x5a; return; }
        aboutNext = UiTicks + (aboutLine == 0 && aboutPixel == 1 ? 0x36 : 1);
    }

    void AboutEvent()
    {
        if (aboutWaits > (aboutRolling ? 3 : 1)) { modal = -1; return; }
        AboutStep();
    }

    void DrawAbout(UiArt.Canvas c)
    {
        while (UiTicks >= aboutNext) AboutStep();
        ui.DrawWindow(c, AboutWin, 0, 0, null, aboutRolling ? new[] { 3001 } : null);
        if (!aboutRolling) return;
        var it = ui.Layouts[AboutWin].Items[2];
        var (l, t, r, b) = it.Rect;
        var clip = c.Clip(l, t, r, b);
        clip.Fill(l, t, r, b, ui.SchemeOf(it).bg);
        var lines = session.Files.Strings(1700) ?? Array.Empty<string>();
        int fh = ui.Font(4).Height - 1;
        for (int k = aboutLine, y = t - aboutPixel; y < b && k < lines.Length; k++, y += fh)
            if (!string.IsNullOrEmpty(lines[k])) ui.DrawText(clip, 4, 0, l, y, r, y + fh, lines[k], ui.SchemeOf(it).fg);
    }

    bool selectMidGame;                                                      // F2: a game is running, so ask to save first

    void SelectClick(int index)
    {
        switch (index)
        {
            case 2: Replace(1); break;
            case 3: Replace(2); break;
            case 4: Replace(3); break;
            case 5: modal = -1; break;
            case 6: Replace(0); break;                                      // the Tutorial (G:0EAC = 0, Formica.Sim.Tutorial)
            case 7: loadFromSelect = true; Replace(4); break;
        }
    }

    // f_725b6 loops back to its dialog when Load (0x207) loads nothing; File > Load with no game running (G:0EAC = -1)
    // brings the new-game dialog too (8414:0000).
    bool loadFromSelect;

    void LoadFailed()
    {
        if (loadFromSelect || session.St.U16(Seg.G, 0xeac) == 0xffff) { modal = SelectWin; selectMidGame = false; }
        loadFromSelect = false;
    }

    // ------------------------------------------------------------------------------- the save prompt (layout 33)
    // "Do you want to save / your current game / before loading a new SimAnt game?" (STR# 1800 [8..10]) with
    // DON'T SAVE, Save and Cancel (items 0x2103..0x2105) before a running game is replaced.
    const int SavePrompt = 33;
    int pendingGame = -1;                                                    // 0..3 a new game, 4 load, 5 quit

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
        if (what == 4) OpenFileDialog(false);                               // f_6c1a0's file dialog
        else if (what == 5) GetTree().Quit();                               // 0xFD08 (DS:2CBC = 8)
        else Restart(what);
    }

    void DrawSavePrompt(UiArt.Canvas c)
    {
        ui.DrawWindow(c, SavePrompt, 0, 0, null);
        var items = ui.Layouts[SavePrompt].Items;
        // f_72429(n): SHARED text (0x41 - n) * 2 (130 before loading or a new game, 128 before quitting) as a text box
        // (f_25cfa) in item 0x2101 in font 4 (2 at 320 px), its scheme's foreground: words wrapped to the width, lines of
        // the font's height (fRectHeight - 1) from the item's top, left-aligned at its left; the wrap width is the item's less
        // 8 (measured on the original's screen: lines of 243 px kept, 262 wrapped; f_25cfa not decoded)
        var text = session.Files.Text(pendingGame == 5 ? 128 : 130) ?? "";
        var (tl, tt, tr, tb) = items[1].Rect;
        var f = ui.Font(4);
        int fh = f.Height - 1, y = tt;
        var fg = ui.SchemeOf(items[1]).fg;
        var clip = c.Clip(tl, tt, tr, tb);
        foreach (var line in WrapText(f, text, tr - tl - 8))
        {
            f.Draw(clip, tl, y - 1, line, fg);
            y += fh;
        }
    }

    /// <summary>Words wrapped greedily to `width` px (line breaks kept), as a text box lays them out.</summary>
    static List<string> WrapText(Formica.Data.BitmapFont f, string text, int width)
    {
        var lines = new List<string>();
        foreach (var para in text.Split('\n'))
        {
            string line = "";
            foreach (var word in para.Split(' '))
            {
                string next = line.Length == 0 ? word : line + " " + word;
                if (line.Length > 0 && f.Width(next) > width) { lines.Add(line); line = word; }
                else line = next;
            }
            lines.Add(line);
        }
        return lines;
    }

    void SavePromptClick(int index)
    {
        switch (index)
        {
            case 3: Proceed(pendingGame); break;
            case 4: { int what = pendingGame; modal = -1; SaveCommand(true, () => Proceed(what)); break; }   // f_6c328(1)
            case 5: modal = -1; selectMidGame = false; break;
        }
    }

    void QuickSave() => SaveGame(ProjectSettings.GlobalizePath("user://quicksave.ANT"));

    bool SaveGame(string path)
    {
        try { System.IO.File.WriteAllBytes(path, SaveFile.Save(session.St)); }
        catch (Exception e) when (e is System.IO.IOException or UnauthorizedAccessException)
        {
            OpenAlert(e.Message, null);                                        // f_1c6cc(strerror(errno))
            return false;
        }
        lastMessage = "Saved to " + path;
        return true;
    }

    // ------------------------------------------------------------------------------- saving and loading
    // f_6c328(n), File > Save (n = 1) and Save As (n = 0): with Save and a game file name already known (G:3862, the
    // last file loaded or saved) it skips the dialog; else the dialog (f_6c566, "Save Game", "SAVE"), its name becomes
    // G:3862. A file that exists asks "OVERWRITE\n<name>" (f_1ca35, Yes / No): No goes back to the dialog. A failed
    // write shows the C library's message (f_1c6cc) and forgets the name.
    string gameFile;                                                            // G:3862
    Action afterSave;

    void SaveCommand(bool save, Action then = null)
    {
        afterSave = then;
        if (save && !string.IsNullOrEmpty(gameFile)) SaveTo(gameFile);
        else OpenFileDialog(true);
    }

    void SaveTo(string path)
    {
        gameFile = path;
        void Write()
        {
            if (!SaveGame(path)) { gameFile = null; return; }
            var then = afterSave;
            afterSave = null;
            then?.Invoke();
        }
        if (System.IO.File.Exists(path))
            OpenAlert("OVERWRITE\n" + path.ToUpperInvariant(), new[] { "\rYes", "\x1bNo" }, b => { if (b == 0) Write(); else OpenFileDialog(true); });
        else Write();
    }

    // f_6c1a0, File > Load: the dialog ("Load Game", "LOAD"), the name to G:3862; a file that will not open shows the
    // C library's message; a read error "  Read error  \ngame not loaded" and no game (G:0EAC = -1: Select a Game).
    void LoadFrom(string path)
    {
        gameFile = path;
        if (!System.IO.File.Exists(path)) { OpenAlert("No such file or directory", null, _ => LoadFailed()); return; }
        if (!LoadGame(path))
        {
            session.St.Set16(Seg.G, 0xeac, 0xffff);
            OpenAlert("  Read error  \ngame not loaded", null, _ => LoadFailed());
            return;
        }
        loadFromSelect = false;
    }

    // ------------------------------------------------------------------------------- alert boxes
    // The library's alerts, drawn in character cells of the PC font (8 x DS:3DDC) without a layout. f_1ca35(text,
    // set): the box (max(longest line, 2 x buttons) + 2) x (lines + 4) cells, centred on the 80-column screen, filled
    // black (0xF2F), a 4-px frame in colour 4, a 1-px white one on its outer edge; the lines centred from the second
    // row in colour 4 on black (f_1c926); the buttons (sets at DS:5570: Yes / No, Yes / Cancel, Retry / Cancel; the
    // first character of each is its key, \r Enter, \x1b Esc; the label's first letter works too) on the row
    // bottom - 2, centred, 2 cells apart, each (f_6d620) its label in colour 4 on light grey (12), ringed 2 px light
    // grey and 1 px colour 4 outside it. f_1c6f5 (f_1c6cc, set null here): the same box without the white line and one
    // "Continue" button; C, Enter or any click closes it.
    const int AlertWin = 100;
    string[] alertLines = Array.Empty<string>(), alertButtons;
    Action<int> alertDone;
    int alertReturn = -1;

    void OpenAlert(string text, string[] buttons, Action<int> done = null)
    {
        alertLines = text.Split('\n');
        alertButtons = buttons;
        alertDone = done;
        alertReturn = modal;
        modal = AlertWin;
    }

    void CloseAlert(int button)
    {
        modal = alertReturn == AlertWin ? -1 : alertReturn;
        var done = alertDone;
        alertDone = null;
        done?.Invoke(button);
    }

    (int l, int t, int r, int b) AlertRect(out int ch)
    {
        ch = 14;                                                                // DS:3DDC: the BIOS font's 8 x 14 cells
        int w = alertLines.Max(s => s.Length), h = alertLines.Length + 4;
        if (alertButtons != null) w = Math.Max(w, 2 * alertButtons.Length);  // (sic: the labels' lengths are not added)
        w += 2;
        int x = (ScreenW / 8 - w) / 2, y = (ScreenH / ch - h) / 2;            // f_1f9a8
        return (x * 8, y * ch, (x + w) * 8, (y + h) * ch);
    }

    List<(int l, int t, int r, int b)> AlertButtons()
    {
        var (l, t, r, b) = AlertRect(out int ch);
        var labels = alertButtons?.Select(s => s[1..]).ToArray() ?? new[] { "Continue" };
        int total = labels.Sum(s => s.Length + 2) - 2;                         // the cells the row needs
        int col = alertButtons == null ? (l + (r - l - labels[0].Length * 8) / 2) / 8 : ((r - l) / 8 - total - 2) / 2 + l / 8;
        int row = b / ch - 2;
        var rects = new List<(int, int, int, int)>();
        foreach (var s in labels)
        {
            rects.Add((col * 8, row * ch, (col + s.Length) * 8, (row + 1) * ch));
            col += s.Length + 2;
        }
        return rects;
    }

    void DrawAlert(UiArt.Canvas c)
    {
        var f = ui.Font(0);
        uint four = ui.Palette[4], grey = ui.Palette[12];
        var (l, t, r, b) = AlertRect(out int ch);
        c.Fill(l, t, r, b, UiArt.Black);
        UiArt.ThickFrame(c, l, t, r, b, 4, four);
        if (alertButtons != null) UiArt.ThickFrame(c, l, t, r, b, 1, UiArt.White);
        for (int i = 0; i < alertLines.Length; i++)
            Cells(c, l + (r - l - alertLines[i].Length * 8) / 2, t + (i + 1) * ch, alertLines[i], four);
        var labels = alertButtons?.Select(s => s[1..]).ToArray() ?? new[] { "Continue" };
        var rects = AlertButtons();
        for (int i = 0; i < rects.Count; i++)
        {
            var (bl, bt, br, bb) = rects[i];
            // the button's frames end one pixel short at the right and bottom (the original's screen, "Permission denied")
            UiArt.ThickFrame(c, bl - 3, bt - 3, br + 2, bb + 2, 1, four);
            UiArt.ThickFrame(c, bl - 2, bt - 2, br + 1, bb + 1, 2, grey);
            c.Fill(bl, bt, br, bb, grey);
            Cells(c, bl, bt, labels[i], four);
        }
    }

    /// <summary>f_1fbd0: text in the PC font's 8-px cells.</summary>
    void Cells(UiArt.Canvas c, int x, int y, string text, uint colour)
    {
        var f = ui.Font(0);
        foreach (char ch in text)
        {
            f.Draw(c, x + (8 - f.Width(ch.ToString())) / 2, y, ch.ToString(), colour);
            x += 8;
        }
    }

    void AlertClick(Vector2 p)
    {
        var rects = AlertButtons();
        for (int i = 0; i < rects.Count; i++)
            if (p.X >= rects[i].l - 3 && p.X < rects[i].r + 3 && p.Y >= rects[i].t - 3 && p.Y < rects[i].b + 3) { CloseAlert(i); return; }
        if (alertButtons == null) CloseAlert(0);                               // f_1c6f5: any press
    }

    void AlertKey(InputEventKey k)
    {
        char key = k.Keycode is Key.Enter or Key.KpEnter ? '\r' : k.Keycode == Key.Escape ? '\x1b' : char.ToUpperInvariant((char)k.Unicode);
        if (alertButtons == null)
        {
            if (key is 'C' or '\r') CloseAlert(0);
            return;
        }
        for (int i = 0; i < alertButtons.Length; i++)
            if (alertButtons[i].Length > 1 && (alertButtons[i][0] == key || char.ToUpperInvariant(alertButtons[i][1]) == key)) { CloseAlert(i); return; }
    }

    // ------------------------------------------------------------------------------- the file dialog (layout 22)
    // f_6c566(name, caption, button, save), SIM_NOTES "The file dialog". The drive DS:2966 ('A'..'H', set by the
    // buttons 0x160B..0x1612) and its current folder; the path line 0x1606 shows that folder (f_2094b at the item's
    // left + 4 after clearing it); the list 0x1609 (f_241f2, scroll bar 0x1608 f_244cc) holds up to 200 16-byte
    // records: a flag byte '0' (bit 0 = selected) and "<..>" / "<NAME>" for the sub-folders (marker byte 1, sorting
    // them first, shown as '<') or "%-12s" for the *.ant files, sorted with strncmp; "0No Files" when empty. A click
    // selects one row (single selection, +24 & 0x20 with +25 & 4: a selected row stays); a double click on the selected
    // row is the button. The button (or Enter) takes the typed name, else the selected row: a folder is entered
    // (CHDIR), a file returned. Save mode: a letter or digit starts the name (0x1604, f_6d1c2, 8 characters) at the
    // name box's left + 4; a list click clears it; the name is first the last file's (G:3862). f_6cecb: spaces and
    // commas to '_', at most 8 characters before ".ant". The arrows scroll a line per clock tick while held; with a
    // double click (or Shift / right) to the top / the end; the track does nothing.
    const int FileWin = 22, FileList = 9, FileScroll = 8, FileNameBox = 3;
    bool fileSave, fileEditing;
    string fileName = "";
    readonly List<(string text, string name, bool dir)> fileRows = new();
    int fileSel = -1, fileFirst, fileDirs;
    char fileDrive;
    readonly Dictionary<char, string> driveDirs = new();
    int fileArrow;                                                              // a held arrow: -1 up, 1 down
    double fileArrowWait;

    WindowLayout fileLayoutStored;

    /// <summary>f_6c566's set-up of window 22: in Save mode the state-5 items (0x1602..0x1604, the name box) are shown
    /// (f_22e52 / f_23136); in Load mode they are hidden and disabled (f_22e5a / f_2313e) and item 0x1602's offsets get
    /// a zero height (f_22ccd) before f_21336 lays the window out, so everything attached below it moves up and the
    /// window shrinks (UiArt.Relayout). Hidden items get an empty rectangle: not drawn, never hit.</summary>
    void FileLayout()
    {
        fileLayoutStored ??= ui.Layouts[FileWin];
        var w = fileLayoutStored;
        var offsets = new Dictionary<int, (int, int, int, int)>();
        if (!fileSave) offsets[2] = (w.Items[2].Pos.x, w.Items[2].Pos.y, w.Items[2].Size.w, 0);
        var lay = ui.Relayout(FileWin, w.Requested, offsets);
        if (!fileSave)
            for (int i = 0; i < lay.Items.Count; i++)
                if (lay.Items[i].State == 5) lay.Items[i] = lay.Items[i] with { Rect = (0, 0, 0, 0) };
        ui.Layouts[FileWin] = lay;
    }

    void OpenFileDialog(bool save)
    {
        fileSave = save;
        FileLayout();
        fileEditing = false;
        var home = ProjectSettings.GlobalizePath("user://");
        if (fileDrive == 0)
        {
            fileDrive = char.ToUpperInvariant(System.IO.Path.GetPathRoot(System.IO.Path.GetFullPath(home))?.FirstOrDefault() ?? 'C');
            driveDirs[fileDrive] = System.IO.Path.GetFullPath(home);
            foreach (var arg in OS.GetCmdlineUserArgs())
                if (arg.StartsWith("--file-dir="))
                {
                    fileDrive = 'C';
                    driveDirs['C'] = fileDirRoot = arg["--file-dir=".Length..];
                    fileDirShown = "C:\\";
                }
        }
        FileScan(true);
        modal = FileWin;
    }

    string FileDir() => driveDirs.TryGetValue(fileDrive, out var d) ? d : fileDrive + ":\\";

    /// <summary>--file-dir=path (screenshots): the dialog lists that folder as the root of drive C:.</summary>
    string fileDirShown, fileDirRoot;

    void FileScan(bool first)
    {
        fileName = "";
        fileEditing = false;
        if (first && fileSave && !string.IsNullOrEmpty(gameFile)) fileName = System.IO.Path.GetFileName(gameFile).ToUpperInvariant();
        fileRows.Clear();
        fileSel = -1;
        fileFirst = 0;
        var dir = FileDir();
        var rows = new List<(string key, string text, string name, bool dir)>();
        try
        {
            bool shownRoot = fileDirShown != null && fileDrive == 'C' && dir == fileDirRoot;
            if (!shownRoot && System.IO.Directory.GetParent(dir.TrimEnd('\\', '/') + "\\") is { } p && System.IO.Path.GetPathRoot(dir) != System.IO.Path.GetFullPath(dir))
                rows.Add(("\x01..>", "<..>", "..", true));
            foreach (var d in System.IO.Directory.GetDirectories(dir))
            {
                var n = System.IO.Path.GetFileName(d).ToUpperInvariant();
                if ((new System.IO.DirectoryInfo(d).Attributes & System.IO.FileAttributes.Hidden) != 0) continue;
                rows.Add(("\x01" + n + ">", "<" + n + ">", System.IO.Path.GetFileName(d), true));
            }
            foreach (var f in System.IO.Directory.GetFiles(dir, "*.ant"))
            {
                var n = System.IO.Path.GetFileName(f).ToUpperInvariant();
                rows.Add((n.PadRight(12), n.PadRight(12), System.IO.Path.GetFileName(f), false));
            }
        }
        catch (Exception e) when (e is System.IO.IOException or UnauthorizedAccessException) { }
        rows = rows.Take(200).OrderBy(r => r.key.Length > 14 ? r.key[..14] : r.key, StringComparer.Ordinal).ToList();
        fileDirs = rows.Count(r => r.dir);
        foreach (var r in rows) fileRows.Add((r.text.Length > 14 ? r.text[..14] : r.text, r.name, r.dir));
        if (fileRows.Count == 0) fileRows.Add(("No Files", "No Files", false));
    }

    void FileDialogDone(bool ok)
    {
        if (!ok)
        {
            modal = -1;
            afterSave = null;
            if (!fileSave) LoadFailed();
            return;
        }
        string name = fileName;
        if (name.Length == 0)
        {
            if (fileSel < 0) return;                                             // the original waits for a choice
            var row = fileRows[fileSel];
            if (fileSel < fileDirs)                                              // CHDIR
            {
                var dir = FileDir();
                driveDirs[fileDrive] = row.name == ".." ? System.IO.Directory.GetParent(dir.TrimEnd('\\', '/'))?.FullName ?? dir
                                                        : System.IO.Path.Combine(dir, row.name);
                FileScan(false);
                return;
            }
            name = row.name;
        }
        // f_6cecb
        var sb = new System.Text.StringBuilder();
        foreach (char ch in name)
        {
            if (ch == '.' || sb.Length == 8) break;
            sb.Append(ch is ' ' or ',' ? '_' : ch);
        }
        name = sb + ".ant";
        modal = -1;
        var path = System.IO.Path.Combine(FileDir(), name);
        if (fileSave) SaveTo(path);
        else LoadFrom(path);
    }

    void FileDialogClick(int index, InputEventMouseButton mb)
    {
        var items = ui.Layouts[FileWin].Items;
        var at = mb.Position;
        if (index == 19) FileDialogDone(true);                               // 0x1613 LOAD / SAVE
        else if (index == 20) FileDialogDone(false);                         // 0x1614 CANCEL
        else if (index >= 11 && index <= 18)                                 // A: .. H: (DS:2966 = item - 0x15CA)
        {
            char d = (char)('A' + index - 11);
            if (!System.IO.Directory.Exists(d + ":\\")) { OpenAlert("Can't read disk", null); return; }
            fileDrive = d;
            FileScan(false);
        }
        else if (index == FileList && mb.ButtonIndex == MouseButton.Left)    // f_248b3
        {
            int row = ((int)at.Y - items[FileList].Rect.top) / ui.ListRowHeight(items[FileList]) + fileFirst;
            if (mb.DoubleClick)
            {
                if (row == fileSel) FileDialogDone(true);
                return;
            }
            if (row != fileSel) fileSel = row < fileRows.Count ? row : -1;
            if (fileSave && fileName.Length > 0) { fileName = ""; fileEditing = false; }
        }
        else if (index == FileScroll)                                        // f_24971
        {
            var (_, t, _, b) = items[FileScroll].Rect;
            int visible = ui.ListRows(items[FileList]), ah = ui.ArrowHeight;
            if (fileRows.Count <= visible) return;
            int dir = at.Y < t + ah ? -1 : at.Y > b - ah ? 1 : 0;
            if (dir == 0) return;
            if (mb.DoubleClick || mb.ShiftPressed || mb.ButtonIndex == MouseButton.Right) { fileFirst = dir < 0 ? 0 : fileRows.Count - visible; return; }
            fileArrow = dir;
            fileArrowWait = 0;
            FileArrowStep();
        }
    }

    void FileArrowStep()
    {
        int visible = ui.ListRows(ui.Layouts[FileWin].Items[FileList]);
        if (fileArrow < 0 && fileFirst > 0) fileFirst--;                           // f_24736
        if (fileArrow > 0 && fileFirst + visible < fileRows.Count) fileFirst++;    // f_24602
    }

    void FilePoll(double delta)
    {
        if (fileArrow == 0) return;
        if (modal != FileWin || !Input.IsMouseButtonPressed(MouseButton.Left)) { fileArrow = 0; return; }
        fileArrowWait += delta;
        while (fileArrowWait >= 1 / GameSession.ClockHz)                           // f_1f881(1): a clock tick
        {
            fileArrowWait -= 1 / GameSession.ClockHz;
            FileArrowStep();
        }
    }

    void FileDialogKey(InputEventKey k)
    {
        if (k.Keycode == Key.Escape) FileDialogDone(false);
        else if (k.Keycode is Key.Enter or Key.KpEnter) FileDialogDone(true);
        else if (fileSave && fileEditing && k.Keycode == Key.Backspace && fileName.Length > 0) fileName = fileName[..^1];
        else if (fileSave && k.Unicode is > ' ' and < 127 && !"\\/:*?\"<>|.".Contains((char)k.Unicode))
        {
            if (!fileEditing)                                                    // a letter or digit starts the name
            {
                if (!char.IsLetterOrDigit((char)k.Unicode)) return;
                fileEditing = true;
                fileName = "";
            }
            if (fileName.Length < 8) fileName += char.ToUpperInvariant((char)k.Unicode);
        }
        else if (fileSave && fileEditing && k.Keycode == Key.Space && fileName.Length < 8) fileName += ' ';
    }

    void DrawFileDialog(UiArt.Canvas c)
    {
        var items = ui.Layouts[FileWin].Items;
        for (int i = 11; i <= 18; i++)                                           // f_22fae(DS:2966 + 0x15CA): the drive's radio button
        {
            bool sel = fileDrive == 'A' + i - 11;
            items[i] = items[i] with { Flags = sel ? items[i].Flags | 4 : items[i].Flags & ~4 };
        }
        ui.DrawWindow(c, FileWin, 0, 0, fileSave ? "Save Game" : "Load Game",
                      skipItems: fileSave ? null : items.Where(i => i.State == 5).Select(i => i.Id).ToHashSet());
        var f0 = ui.Font(0);
        if (fileSave)                                                            // load: no name box (f_22e5a / f_2313e)
        {
            var (bl, bt, br, bb) = items[FileNameBox].Rect;
            var (fg, _) = ui.SchemeOf(items[4]);
            int y = (bt + bb - f0.Height + 1) / 2;
            var box = c.Clip(bl, bt, br, bb);
            f0.Draw(box, bl + 4, y, fileName, fg);
            if (fileEditing) box.Invert(bl + 4 + f0.Width(fileName), y, bl + 4 + f0.Width(fileName) + 8, y + f0.Height);
        }
        {
            // the path line: the field cleared, the folder at its left + 4
            var it = items[6];
            var (l, t, r, b) = it.Rect;
            var (fg, bg) = ui.SchemeOf(it);
            c.Fill(l, t, r, b, bg);
            var field = c.Clip(l, t, r, b);
            var dir = fileDirShown != null && fileDrive == 'C' ? fileDirShown : FileDir().ToUpperInvariant();
            if (!dir.EndsWith('\\')) dir += "\\";
            var pf = ui.Font(it.Style);
            if (it.Style == 0)                                                   // the BIOS font: 8-px cells
                for (int k = 0; k < dir.Length; k++) pf.Draw(field.Clip(l + 4 + 8 * k, t, l + 12 + 8 * k, t + 14), l + 4 + 8 * k, t, dir[k].ToString(), fg);
            else pf.Draw(field, l + 4, t, dir, fg);
        }
        var rows = fileRows.Select((r, i) => (i == fileSel, r.text)).ToList();
        ui.DrawList(c, items[FileList], rows, fileFirst);
        ui.DrawScrollbar(c, items[FileScroll], ui.ListRows(items[FileList]), fileRows.Count, fileFirst);
        ui.ItemText(c, items[19], 0, 0, fileSave ? "SAVE" : "LOAD");
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
        void Text(int index, string text, int font)                                 // f_23943
        {
            var it = items[index];
            ui.DrawValue(c, font, it.Rect.left, it.Rect.top, it.Rect.right, it.Rect.bottom, text, ui.SchemeOf(it).fg, ui.SchemeOf(it).bg);
        }
        var p = efficiency.parts;
        int mode = st.U16(Seg.G, 0xeac);
        // f_71576: the colony's four fields format their own text ("%d%%", f_2318a) and the window draws them in their font;
        // the universe column and the score lines are values (f_23943) in font 4 (3 / 0 at 320 px)
        for (int i = 0; i < 4; i++) ui.ItemText(c, items[2 + i], 0, 0, $"{p[i]}%");
        for (int i = 0; i < 4; i++) Text(6 + i, mode == 2 ? $"{p[4 + i]}%" : S(1800, 16), 4);
        if (mode == 3)
        {
            Text(10, S(1800, 17), 4);
            Text(11, S(1800, 18), 4);
        }
        else
        {
            Text(10, S(1800, 13) + S(1001, mode) + S(1800, 14), 4);
            Text(11, efficiency.score.ToString(), 4);
        }
        ui.ItemText(c, items[12], 0, 0, S(1010, 14));
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
    // The plotted series, as f_79373 keeps them: four slots DS:2EF0 (a new series goes into slot 0 and pushes the
    // others down, a fifth one evicts slot 3; removing one closes the gap), each series' colour DS:8C26[s] the
    // lowest free bit of DS:2EF8 (start 0xF), the colour codes DS:2EE8 = 0x43, 0x46, 0x49, 0x45.
    readonly int[] historySlots = { -1, -1, -1, -1 };
    readonly int[] historyColour = new int[10];
    int historyFree = 0xf;

    void ToggleSeries(int s)
    {
        int at = Array.IndexOf(historySlots, s);
        if (at >= 0)
        {
            for (int i = at; i < 3; i++) historySlots[i] = historySlots[i + 1];
            historySlots[3] = -1;
            historyFree |= 1 << historyColour[s];
            return;
        }
        if (historySlots[3] >= 0) historyFree |= 1 << historyColour[historySlots[3]];
        for (int i = 3; i > 0; i--) historySlots[i] = historySlots[i - 1];
        historySlots[0] = s;
        for (int colour = 0; colour < 4; colour++)
            if ((historyFree & 1 << colour) != 0)
            {
                historyFree &= ~(1 << colour);
                historyColour[s] = colour;
                break;
            }
    }

    void DrawHistoryWindow(UiArt.Canvas c)
    {
        var st = session.St;
        var (dx, dy) = Off(HistoryWin);
        ui.DrawWindow(c, HistoryWin, dx, dy, null, new[] { 16001 });
        var wr = WindowRect(HistoryWin);
        var clip = c.Clip(wr.l, wr.t, wr.r, wr.b);
        foreach (int s in historySlots.Where(x => x >= 0))
        {
            var b = ItemRect(HistoryWin, 3 + s);
            clip.Invert(b.l, b.t, b.r, b.b);
        }
        // f_795ec(series, no label, slot): one line per series, T:082A[k] (k = (s & 1) * 5 + (s >> 1)), scaled with
        // the other colony's ring T:0852[k]; all 64 entries from (G:04F4 - T:0828) & 63, point 0 at the graph's
        // left, point i at left + slot + i * w / 64; the lines through the driver (DS:916C, a line routine taken as
        // Bresenham), then the labels: the last value ("%d", font 3) at the last point, framed.
        var g = ItemRect(HistoryWin, HistoryGraph);
        int count = st.S16(Seg.T, 0x828), start = (st.U8(Seg.G, 0x4f4) - count) & 0x3f;
        int h = g.b - g.t - 16, w = g.r - g.l - 0x40, bottom = g.b - 8;
        int V(int ring, int i) => st.S16(Seg.G, ring + 2 * ((start + i) & 0x3f));
        var area = clip.Clip(g.l, g.t, g.r, g.b);
        var font = ui.Font(3) ?? ui.Font(2);
        var labels = new List<(int x, int y, string text, uint colour)>();
        for (int slot = 0; slot < 4; slot++)
        {
            int s = historySlots[slot];
            if (s < 0) continue;
            int k = (s & 1) * 5 + (s >> 1), ring = HistoryBlack[k], other = HistoryRed[k];
            int max = 0;
            for (int i = 0; i < count; i++) max = Math.Max(max, Math.Max(V(ring, i), V(other, i)));
            int mult = 1, div = 1;
            if (max > 0)
            {
                int b = 1;
                while (max * b < h) b++;
                if (b > 1) mult = b - 1;
                else while (max / div > h) div++;
            }
            uint colour = session.Art.Palette[st.U8(Seg.DS, 0x2ee8 + 2 * historyColour[s]) & 15];
            int Y(int i) => bottom - (div == 1 ? V(ring, i) * mult : V(ring, i) / div);
            int px = g.l, py = Y(0);
            for (int i = 1; i < 64; i++)
            {
                int x = i * w / 64 + slot + g.l, y = Y(i);
                Line(area, px, py, x, y, colour);
                px = x;
                py = y;
            }
            labels.Add((px, py, V(ring, 63).ToString(), colour));
        }
        foreach (var (x, y, text, colour) in historyHeld ? new() : labels)
        {
            int top = y - font.Height / 2, tw = font.Width(text);
            area.Fill(x - 1, top - 1, x + tw + 1, top + font.Height + 1, session.Art.Palette[0]);
            font.Draw(area, x, top, text, colour);
            area.Frame(x - 1, top - 1, x + tw + 1, top + font.Height + 1, colour);
        }
        if (help)
        {
            var it = ui.Layouts[HistoryWin].Items.First(x => x.Bitmap == 16001);
            ui.DrawBitmap(clip, 16001, it.Rect.left + dx, it.Rect.top + dy);
        }
    }

    /// <summary>The VGA driver's line (DS:916C → 0x32F69): drawn left to right (the ends swapped if needed), both
    /// ends included; the longer axis steps every pixel (x when dx >= dy) and the error, from 0, adds the shorter
    /// span, moving the shorter axis on once it passes half the longer one (then less the longer span).</summary>
    static void Line(UiArt.Canvas c, int x0, int y0, int x1, int y1, uint colour)
    {
        if (x1 < x0) (x0, y0, x1, y1) = (x1, y1, x0, y0);
        int dx = x1 - x0, dy = y1 - y0, sy = 1;
        if (dy < 0) { dy = -dy; sy = -1; }
        int err = 0, x = x0, y = y0;
        if (dx >= dy)
            for (int n = dx; n >= 0; n--)
            {
                c.Plot(x, y, colour);
                x++;
                err += dy;
                if (err > dx >> 1) { err -= dx; y += sy; }
            }
        else
            for (int n = dy; n >= 0; n--)
            {
                c.Plot(x, y, colour);
                y += sy;
                err += dx;
                if (err > dy >> 1) { err -= dy; x++; }
            }
    }

    bool historyHeld;

    void HistoryWindowClick(int index)
    {
        if (index == 13) help = helpHeld = true;                               // 0x150D: f_2f74e(0x150F), while held
        else if (index == 14) historyHeld = true;                              // 0x150E: the plot without labels while held, then f_7959a(3)
        else if (index >= 3 && index <= 12)
        {
            ToggleSeries(index - 3);
        }
    }

    // ------------------------------------------------------------------------------- Behavior / Caste Control
    // Layouts 18 / 19 (bitmaps 4600 / 4620, help overlays 4601 / 4621), the triangles ported in Panels: weights
    // G:049E.. (forage apex, dig bottom left, nurse bottom right) and G:0482.. (breeders, workers, soldiers), each
    // summing to 0xFFFF. Items (indices): 3 help, 4 Auto, 5 Manual, 6..8 Set 1..3 (preset ratios),
    // 12 the relative-setting bars (f_0839a / f_08255, drawn here as three plain bars), 13 the triangle
    // (f_07980 takes its rectangle), 9..11 / 15..17 the corner boxes (percent / count, DS:1B62 / DS:1B64).
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
        // f_080d1 / f_08255: the marker is a sprite (f_26968) of bitmap 1400 centred on the point (G:3832 / G:3834 hold
        // its size, 14 x 14)
        var (mw, mh, _) = ui.Bitmap(1400);
        ui.DrawBitmap(clip, 1400, mx - mw / 2, my - mh / 2);
        // f_083d9 (from f_080d1 / f_08255): bar i spans a fifth of item 0x0C's width at 2 i fifths, from the item's
        // bottom up by w * height / 65535 (an ldiv by -65535: truncated); a bar of 2 px or more is filled with the
        // colour DS:1B4A[i] (Caste DS:1B46[i]) and framed in 15, the rest of the column up to top - 1 is cleared
        // with 0x40. These fills (driver DS:9134) take only the colour's low nibble, DS:41C0 = the identity.
        // The corner values (items 9..11) show the weight as a percentage ("%-ld%%", (100 w + 0x3FFF) / 0xFFFF)
        // when DS:1B62 / DS:1B64 is set, else as ants ("%-ld", (w x total + 0x3FFF) / 0xFFFF; total G:0B12 +
        // G:0B14 + G:0B16, the Caste window G:0AEC)
        var bars = ItemRect(win, 12);
        int w5 = (bars.r - bars.l) / 5, bh = bars.b - bars.t;
        bool percent = (st.U8(Seg.DS, win == BehaviorWin ? 0x1b62 : 0x1b64) & 1) != 0;
        long total = win == BehaviorWin ? st.S16(Seg.G, 0xb12) + st.S16(Seg.G, 0xb14) + st.S16(Seg.G, 0xb16) : st.S16(Seg.G, 0xaec);
        var pal = session.Art.Palette;
        for (int i = 0; i < 3; i++)
        {
            long w = st.U16(Seg.G, values + 2 * i);
            int l = bars.l + 2 * i * w5, r = l + w5;
            int top = bars.b + (int)(w * bh / -65535);
            if (top + 1 < bars.b)
            {
                int colour = st.U8(Seg.DS, (win == BehaviorWin ? 0x1b4a : 0x1b46) + i) & 15;
                clip.Fill(l, top, r, bars.b, pal[colour]);
                clip.Frame(l, top, r, bars.b, pal[15]);
            }
            else top = bars.b;
            clip.Fill(l, bars.t - 1, r, top, pal[0]);
            var lr = ItemRect(win, 9 + i);
            clip.Fill(lr.l, lr.t, lr.r, lr.b, UiArt.White);
            string text = percent ? $"{(100 * w + 0x3fff) / 0xffff}%" : $"{(w * total + 0x3fff) / 0xffff}";
            ui.DrawValue(clip, 4, lr.l, lr.t, lr.r, lr.b, text);                     // f_083d9 → f_23943: font 4 (0 at 320 px)
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
            case 3: help = helpHeld = true; break;                                   // f_2f74e(0x120E / 0x130E), while held
            case 4:
            case 5:
                if (win == BehaviorWin) st.Set16(Seg.G, 0x378, index == 4 ? 1 : 0);
                else
                {
                    st.Set16(Seg.T, 0x7e8, index == 4 ? 1 : 0);                 // f_07cde: Manual only clears T:07E8
                }
                break;
            case 9: case 10: case 11: case 15: case 16: case 17:            // the corner boxes (0x7f06 / 0x7cce)
            {
                int flag = win == BehaviorWin ? 0x1b62 : 0x1b64;
                st.Set8(Seg.DS, flag, st.U8(Seg.DS, flag) ^ 1);
                break;
            }
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

    // ------------------------------------------------------------------------------- the timed message (f_15e2c)
    // f_15e2c(text, duration, force) keeps the message the Edit window draw (f_038a6) shows centred at the top of its
    // map (f_15d96: font 2, scheme 3 black on white, y = map top + 4) until clock + duration * 3 / 2 (a negative
    // duration: until replaced); the yard window shows a second copy (DS:299A, f_7052b). A new message replaces the
    // shown one only when forced, or when none is shown and Options > Messages (T:07B0) is on. The sim's "status"
    // effects: the advisor's (STR# 1020 [index] = G:0360, 120 ticks; null clears a lasting one), entering the red
    // nest (1010 [4]), the map tools' refusals (1010 [22] / [21], forced); MATE and PLACE use it too.
    string statusText;
    long statusUntil;

    void ShowStatus(string text, int duration, bool force)
    {
        bool lasting = statusUntil == long.MaxValue;
        if (!(force || (statusText == null && session.Option(4)) || (text == null && lasting))) return;
        statusUntil = duration < 0 ? long.MaxValue : session.St.Clock + duration * 3L / 2;
        statusText = text;
    }

    void StatusEffect(object[] a)
    {
        string S(int list, int k) => session.Files.Strings(list) is { } l && k < l.Length ? l[k] : null;
        switch (a[0])
        {
            case null: ShowStatus(null, 0, false); break;
            case "red nest": ShowStatus(S(1010, 4), 120, false); break;
            case "cannot dig here": ShowStatus(S(1010, 22), 120, true); break;
            case "cannot fill here": ShowStatus(S(1010, 21), 120, true); break;
            case int list when list >= 1000 && a.Length > 1: ShowStatus(S(list, Convert.ToInt32(a[1])), 120, false); break;
            case int k: ShowStatus(S(1020, k), a.Length > 1 ? Convert.ToInt32(a[1]) : 120, a.Length > 2 && Convert.ToInt32(a[2]) != 0); break;
        }
    }

    void DrawStatusMessage(UiArt.Canvas c) => DrawStatusMessage(c, ItemRect(EditWin, EditMapItem));

    void DrawStatusMessage(UiArt.Canvas c, (int l, int t, int r, int b) m)
    {
        if (statusText == null) return;
        if (session.St.Clock > statusUntil) { statusText = null; return; }
        var f = ui.Font(2);
        string text = statusText.Replace("\n", " ");
        int w = f.Width(text), x = (m.l + m.r - w) / 2, y = m.t + 4;
        var clip = c.Clip(m.l, m.t, m.r, m.b);
        // the original's font height is fRectHeight - 1 (f_262eb), its strike drawn from one row higher
        clip.Fill(x, y, x + w, y + f.Height - 1, UiArt.White);                          // the text's own extent (f_22bfa)
        f.Draw(clip, x, y - 1, text, UiArt.Black);
    }

    // ------------------------------------------------------------------------------- speech balloons
    // Balloons.Run (f_06a4d) emits ("balloon", a, b, view, style, (list handle, line)) each tick a balloon is
    // shown (Options > Silly, T:07B2); the list handles are the STR# lists loaded at start-up: G:020A 1220 (black
    // fighters), G:0218 1230 (red fighters), G:021C 1240 (brood), G:0234 1250 (queen), G:023A 1260 (resting).
    // f_0696a queues up to 6 (G:1092: the cell centre in pixels a * 16 + 8, b * 16 + 8, view, style, the text) when
    // the spot is in the Edit window (f_06725); f_07134 then draws the first queued one that is in view, built by
    // f_1629c (Formica.Data.Balloon), with its top-left at (x + 4, y - height - 4) so the tail points at the ant,
    // and empties the queue. The cells under it are marked for redrawing (DS:15C4), so it lasts one frame unless
    // queued again.
    static readonly Dictionary<int, int> BalloonLists = new() { [0x20a] = 1220, [0x218] = 1230, [0x21c] = 1240, [0x234] = 1250, [0x23a] = 1260 };
    readonly List<(int a, int b, int view, string text)> balloonsNow = new();
    readonly Dictionary<string, (int w, int h, uint[] px)> balloonCache = new();

    string BalloonText(int handle, int index)
    {
        var lines = BalloonLists.TryGetValue(handle, out int id) ? session.Files.Strings(id) : null;
        return lines != null && index < lines.Length ? lines[index] : null;
    }

    // The spider's remarks (f_03de7, while the patch is visible, T:07B2): a timer T:098E; when it passes (not paused) it
    // re-arms at clock + Rand64 + 180 and Rand2 == 0 shows a remark (G:0D6E = 1) and steps T:0992 through 0..4, else
    // hides it. While the spider's state G:0FB8 stays the same (G:0EB4) and is <= 4 a shown remark is queued as
    // f_0696a style 10 (pixels): G:10B4 = STR# 1210 [5 * state + T:0992] at the spider (G:0F12, G:0F34) + its
    // heading's direction * 8; a new state re-arms the timer at clock + Rand32 + 30 and hides it. DIVERGENCE: the
    // original draws these from the game's LFSR in the redraw; the shell uses its own generator (as for the fangs).
    readonly Random spiderTalkRng = new();
    long spiderTalkUntil;
    int spiderTalkState = -1, spiderTalkLine;
    bool spiderTalking;

    (int x, int y, string text)? SpiderRemark()
    {
        var st = session.St;
        if (st.U16(Seg.T, 0x7b2) == 0 || st.U16(Seg.G, 0xf0c) == 0) return null;
        long clock = st.Clock;
        if (!session.Paused && clock > spiderTalkUntil)
        {
            spiderTalkUntil = clock + spiderTalkRng.Next(64) + 180;
            spiderTalking = spiderTalkRng.Next(2) == 0;
            if (spiderTalking) spiderTalkLine = (spiderTalkLine + 1) % 5;
        }
        int state = st.S16(Seg.G, 0xfb8);
        if (state != spiderTalkState)
        {
            spiderTalkUntil = clock + spiderTalkRng.Next(32) + 30;
            spiderTalking = false;
            spiderTalkState = state;
            return null;
        }
        if (state > 4 || !spiderTalking || view != 1) return null;
        var lines = session.Files.Strings(1210);
        int k = 5 * state + spiderTalkLine, d = st.U16(Seg.G, 0x1004) & 7;
        if (lines == null || k < 0 || k >= lines.Length) return null;
        return (st.S16(Seg.G, 0xf12) + Movement.Dx(st, d) * 8, st.S16(Seg.G, 0xf34) + Movement.Dy(st, d) * 8, lines[k]);
    }

    void DrawBalloon(UiArt.Canvas c)
    {
        var m = ItemRect(EditWin, EditMapItem);
        // f_07134 draws the first queued balloon in view: the ants' (f_07128) are queued before the spider's (f_03de7)
        var queue = balloonsNow.Where(x => x.text != null && x.view == view).Select(x => (x: x.a * Cell + 8, y: x.b * Cell + 8, x.text)).ToList();
        if (SpiderRemark() is { } sr) queue.Add(sr);
        foreach (var (px, py, text) in queue)
        {
            int a = px / Cell, b = py / Cell;
            if (a < originA || b < originB || a >= originA + Cols || b >= originB + Rows) continue;   // f_06725
            if (!balloonCache.TryGetValue(text, out var bmp))
                balloonCache[text] = bmp = Balloon.Make(session.Files.Flat, ui.Font(2), text);
            int x = px - originA * Cell + 4 + m.l, y = py - originB * Cell - bmp.h - 4 + m.t;
            var clip = c.Clip(m.l, m.t, m.r, m.b);
            for (int yy = 0; yy < bmp.h; yy++)
                for (int xx = 0; xx < bmp.w; xx++)
                    if (bmp.px[yy * bmp.w + xx] != Balloon.Transparent) clip.Plot(x + xx, y + yy, bmp.px[yy * bmp.w + xx]);
            return;                                                         // one per frame, as f_07134
        }
    }

    // ------------------------------------------------------------------------------- sound
    // The original's own sound: its driver (Formica.Data.SoundDriver, verified on its OPL2 register streams) on an
    // emulated OPL2 plus its two sample voices (SoundMixer), rendered each frame into one AudioStreamGenerator.
    // Songs: f_00ea1(id) → f_284b3, only while Options > Music (T:07AA) is on; a new song stops the one playing
    // (f_285aa). The sim reports songs as "voice", "music" (f_00ed0, an empty stub, for ids below 10000) and "sound"
    // ids from 10000. Songs asked for in the same frame play one after the other (the game over's ending, then its
    // fanfare once f_00f28 says the ending is done). Effects: f_00ed8(n) → f_29927, on the same driver and voices.
    const int AudioRate = 44100;
    const float AudioGain = 1.6f;
    readonly Queue<int> songQueue = new();
    SoundMixer mixer;
    AudioStreamGeneratorPlayback playback;
    short[] mixBuf = Array.Empty<short>();
    Vector2[] frameBuf = Array.Empty<Vector2>();
    bool songThisFrame, muted;

    /// <summary>The mixer and its stream, made on first use (never in screenshot runs).</summary>
    bool AudioReady()
    {
        if (screenshot != null || session == null) return false;
        if (mixer != null) return true;
        mixer = new SoundMixer(session.Files);
        var player = new AudioStreamPlayer { Stream = new AudioStreamGenerator { MixRate = AudioRate, BufferLength = 0.15f } };
        AddChild(player);
        player.Play();
        playback = (AudioStreamGeneratorPlayback)player.GetStreamPlayback();
        return true;
    }

    void PlaySong(int id)
    {
        if (!session.Option(1) || !AudioReady() || !session.Files.Sound.Any(r => r.Type == 18 && r.Id == id)) return;
        if (songThisFrame && mixer.Driver.Playing) { songQueue.Enqueue(id); return; }
        songThisFrame = true;
        songQueue.Clear();
        mixer.Driver.StartSong(id);
        GD.Print($"music: song {id}");
    }

    void StopSong()
    {
        songQueue.Clear();
        mixer?.Driver.Stop();
    }

    void PlaySound(int n)
    {
        if (muted || n < 0 || n >= SoundBank.EffectCount || !AudioReady()) return;
        mixer.Driver.Effect(n);
    }

    /// <summary>Each frame: the next queued song once the last one ended, then as much sound as the stream takes.</summary>
    void SongPoll()
    {
        songThisFrame = false;
        if (playback == null) return;
        if (!mixer.Driver.Playing && songQueue.Count > 0) mixer.Driver.StartSong(songQueue.Dequeue());
        int n = playback.GetFramesAvailable();
        if (n <= 0) return;
        if (mixBuf.Length != n)
        {
            mixBuf = new short[n];
            frameBuf = new Vector2[n];
        }
        mixer.Render(mixBuf, AudioRate);
        for (int i = 0; i < n; i++)
        {
            float s = mixBuf[i] / 32768f * AudioGain;
            frameBuf[i] = new Vector2(s, s);
        }
        playback.PushBuffer(frameBuf);
    }

    /// <summary>f_01c52: G:1074 = 1; in the Experimental game a beep (sound 1), else f_01aa7 to the yellow ant (G:048C,
    /// G:047C, G:048A): recentre in its view, or switch to it. A one-shot move: the original has no continuous follow;
    /// with Options > AutoTrack (T:07A8) the walk calls it every step.</summary>
    void FollowYellow()
    {
        var st = session.St;
        st.Set16(Seg.G, 0x1074, 1);
        if (st.U16(Seg.G, 0xeac) == 3) { PlaySound(1); return; }
        var (v, a, b) = session.Yellow;
        if (v < 1) return;
        GoTo(v, a, b);
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
        if (view is >= 1 and <= 3)                            // 104a:02ad: the view's centre
        {
            session.St.Set16(Seg.G, CentreSlots[view], originA + Cols / 2);
            session.St.Set16(Seg.G, CentreSlots[view] + 2, originB + Rows / 2);
        }
    }

    // ------------------------------------------------------------------------------- the yard window (layout 25)
    // f_702f7 (YardRenderer, SIM_NOTES "The yard window"): the Map window's Yard button sets T:07C8 = 0 and shows
    // it. The yard is 12 x 16 patches (col = G:07BC / G:07CA 0..11, row = G:07BE / G:07CC 0..15); colony strengths
    // T:00A4[col * 16 + row] (black) and T:0164[...] (red). G:035C picks the view: 0 / 1 the yard (the house 7000,
    // the lawn 7003 and the actors), 2 Strat, 3 Graphic (the colony views over the grid strips 7020..7022).
    // Toolbar items (indices): 7 Patch (back to the patch), 8 House (G:035C 0 ↔ 1; from 2 / 3 back to 0), 9 Strat, 10 Graphic, 11 MATE,
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
        if (session.St.U16(Seg.G, 0x32e) != 0)                           // f_01aec(0): the view becomes the yard
        {
            session.St.Set16(Seg.G, 0x332, session.St.U16(Seg.G, 0x32e));
            session.St.Set16(Seg.G, 0x32e, 0);
        }
        if (choose)
        {
            // f_7650c: the dead colony's patch is emptied, the Strategic view (f_01823(2)), G:0C20 = 1
            var st = session.St;
            st.Set8(Seg.T, 0xa4 + st.S16(Seg.G, 0x7ca) * 16 + st.S16(Seg.G, 0x7cc), 0);
            st.Set16(Seg.G, 0xc20, 1);
            yardChoose = true;
            session.St.Set16(Seg.G, 0x35c, 2);
            ShowStatus(session.Files.Strings(1010)?[20] ?? "Click on a black colony to continue.", -1, true);
        }
        if (!zOrder.Contains(YardWin) && zOrder.Contains(MapWin)) Swap(MapWin, YardWin);  // f_01823: f_211af(0x100, 0x1900)
        else Front(YardWin);
    }

    // The Map window and the yard window share one place: f_01823 swaps the Map for the yard (f_211af: the new one in the
    // old one's place, in front; the original's screen), f_013ff the yard back for the Map (with the surface view, f_01aec(1)), and Window > Map (f_0148a)
    // fronts whichever of the two is open, or opens the Map (f_013ff).
    void Swap(int from, int to)
    {
        zOrder.Remove(from);
        Front(to);
    }

    void ShowMap()
    {
        if (zOrder.Contains(MapWin)) Front(MapWin);
        else if (zOrder.Contains(YardWin)) Front(YardWin);
        else OpenMapSlot();
    }

    void OpenMapSlot()
    {
        if (zOrder.Contains(MapWin)) return;
        if (zOrder.Contains(YardWin) && !yardChoose)
        {
            placing = false;
            Swap(YardWin, MapWin);
            session.St.Set16(Seg.T, 0x7c8, 1);
            SetView(1);
        }
        else Front(MapWin);
    }

    // ------------------------------------------------------------------------------- the win screen (f_2f91a → f_72750)
    // The Full Game won (and the 'fred' cheat): the yard window opens in its Yard view (f_01447, f_01823(0), the Edit
    // view the yard, f_01aec(0)); f_011e5(150) waits 150 clock ticks or for any event; then window 26 opens with
    // bitmap 16200 (f_23557: the human, the cat and the dog; the picture at 153, 85, the frame 2 px around it) and
    // f_01277(10) starts a 10-second timeout (180 ticks). Until a key (f_01572), the timeout, or 600 clock3 units: the
    // songs 0x4E23 and 0x4E24 one after the other (f_00ea1 when f_00f28 says the music is idle), and every 8 clock3
    // units the six eyes, bitmaps 16210 + frame (0, 1, 2 in turn) at DS:2C2C's (x, y) pairs + the picture's corner.
    // Then f_011e5(300): until 300 ticks, an event or the timeout; the window closes. The game waits meanwhile.
    const int WinWin = 26;
    static readonly (int x, int y)[] WinEyes = { (72, 74), (87, 66), (175, 64), (191, 66), (159, 122), (179, 124) };
    int winPhase, winFrame, winSong;
    double winTime, winSince, winEyeTime;

    void StartWin()
    {
        session.St.Set16(Seg.G, 0x35c, 0);                                     // f_01823(0)
        OpenYard(false);
        winPhase = 1;
        winTime = 0;
    }

    void WinPoll(double delta)
    {
        if (winPhase == 0) return;
        winTime += delta;
        double ticks = winTime * GameSession.ClockHz;
        if (winPhase == 1 && ticks >= 150) WinNext();
        else if (winPhase == 2)
        {
            winSince += delta;
            if (winSong < 0x4e25 && (!session.Option(1) || !AudioReady() || !mixer.Driver.Playing)) PlaySong(winSong++);
            winEyeTime += delta;
            if (winEyeTime * GameSession.ClockHz * 3 >= 8) { winEyeTime = 0; winFrame = (winFrame + 1) % 3; }
            if (winSince * GameSession.ClockHz >= 180 || ticks * 3 >= 600) WinNext();
        }
        else if (winPhase == 3 && (ticks >= 300 || winSince * GameSession.ClockHz >= 180)) WinNext();
    }

    /// <summary>The next step of the win screen; `key` when a key (f_01572) or any event (f_21cb8) ended the wait.</summary>
    void WinNext(bool key = false)
    {
        winTime = 0;
        switch (winPhase)
        {
            case 1: winPhase = 2; winSince = 0; winEyeTime = 0; winFrame = 0; winSong = 0x4e23; break;
            case 2: winPhase = 3; break;
            default: winPhase = 0; break;
        }
        if (winPhase == 3 && !key) winPhase = 0;                              // the timeout has passed: f_011e5 returns at once
    }

    void DrawWin(UiArt.Canvas c)
    {
        if (winPhase < 2) return;
        var (w, h, _) = ui.Bitmap(16200);
        int x = 153, y = 85;
        c.Fill(x - 2, y - 2, x + w + 2, y + h + 2, UiArt.Grey);
        UiArt.ThickFrame(c, x - 2, y - 2, x + w + 2, y + h + 2, 2, UiArt.Black);
        ui.DrawBitmap(c, 16200, x, y);
        if (winPhase == 2)
            foreach (var (ex, ey) in WinEyes) ui.DrawBitmap(c, 16210 + winFrame, x + ex, y + ey);
    }

    void CloseYard()
    {
        if (yardChoose) return;
        placing = false;
        if (zOrder.Contains(MapWin)) zOrder.Remove(YardWin);
        else Swap(YardWin, MapWin);                                           // the Map back in its place
        session.St.Set16(Seg.T, 0x7c8, view);
        session.St.Set16(Seg.G, 0x32e, view);
    }

    /// <summary>f_013ff (the yard window's Patch, Ctrl+4): back to the patch's surface, f_01aec(1).</summary>
    void BackToPatch()
    {
        if (yardChoose) return;
        OpenMapSlot();
    }

    /// <summary>f_70a7d: a patch's parallelogram (DS:2A42: (169, 67) (193, 67) (186, 74) (162, 74) from (col * 28 - row * 10,
    /// row * 10) past G:10D2 / G:10D4), XOR-filled.</summary>
    static void InvertPatch(UiArt.Canvas area, int ox, int oy, int col, int row)
    {
        int bx = col * 28 - row * 10 + ox, by = row * 10 + oy;
        for (int y = 0; y < 7; y++) area.Invert(bx + 169 - y, by + 67 + y, bx + 193 - y, by + 68 + y);
    }

    void DrawYardWindow(UiArt.Canvas c)
    {
        var st = session.St;
        var (dx, dy) = Off(YardWin);
        int mode = st.S16(Seg.G, 0x35c);
        var hidden = new List<int> { 7011 };
        if (mode >= 1) hidden.Add(7000);                                   // f_01823: item 0x1903 shows 7000 + mode
        if (mode >= 2) hidden.Add(7003);
        // item 0x1914 is the message's strip (f_6fbe8 redraws it after the message), never filled (the original's screen)
        ui.DrawWindow(c, YardWin, dx, dy, Title(9 + Math.Clamp(mode, 0, 3)), hidden, new[] { 0x1914 });
        var wr = WindowRect(YardWin);
        var clip = c.Clip(wr.l, wr.t, wr.r, wr.b);
        if (mode == 1)
        {
            var hp = ItemRect(YardWin, 3);
            ui.DrawBitmap(clip, 7001, hp.l, hp.t);                         // the house's inside
        }
        var (ox, oy) = YardOrigin();
        var pic = ItemRect(YardWin, 2);
        var area = clip.Clip(pic.l, pic.t, pic.r, pic.b);
        if (mode < 2)
            foreach (var (rid, x, y) in YardRenderer.Sprites(st, rainRng))
                ui.DrawBitmap(area, rid, x + ox, y + oy);
        else
        {
            area.Fill(pic.l, pic.t, pic.r - 1, pic.b, session.Art.Palette[13]);    // dark grey, the frame's right line kept (the original's screen)
            int y = ItemRect(YardWin, 20).b;
            foreach (int rid in new[] { 7020, 7021, 7022 })
            {
                ui.DrawBitmap(area, rid, pic.l, y);
                y += ui.Bitmap(rid).h;
            }
            YardRenderer.DrawColonies(area, st, session.Art.Palette, ox, oy, mode == 2);
            // black lines down both sides of the picture, x = 63 and 576 (the original's screen; not traced to code)
            clip.Fill(pic.l - 1, pic.t, pic.l, pic.b, UiArt.Black);
            clip.Fill(pic.r - 1, pic.t, pic.r, pic.b, UiArt.Black);
        }
        // the player's patch (G:07CA / G:07CC): f_702f7 ends with f_6f983, which XOR-fills its parallelogram (f_70a7d) in
        // every view and game
        int pc = st.U16(Seg.G, 0x7ca), pr = st.U16(Seg.G, 0x7cc);
        if (pc < 12 && pr < 16) InvertPatch(area, ox, oy, pc, pr);
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
        // the radio buttons' own selection (item flag +24 bit 2): AUTOMATIC / MANUAL start as the layout has them
        // (AUTOMATIC), follow clicks and PLACE (which selects MANUAL), not T:02C0; the view's button is DS:1984[G:035C]
        // (f_01823 → f_22fae: House for the Yard and House views, Strat, Graphic); PLACE while it runs
        foreach (int index in new[] { yardManual ? 14 : 13, 8 + Math.Clamp(mode - 1, 0, 2) })
        {
            var hr = ItemRect(YardWin, index);
            clip.Invert(hr.l, hr.t, hr.r, hr.b);
        }
        if (placing)
        {
            var plr = ItemRect(YardWin, 16);
            clip.Invert(plr.l, plr.t, plr.r, plr.b);
        }
        var q = ItemRect(YardWin, 12);                                     // the swarm's black queens G:07C8
        clip.Fill(q.l, q.t, q.r, q.b, UiArt.White);
        ui.DrawText(clip, 3, 0, q.l, q.t, q.r, q.b, Math.Max(0, (int)st.S16(Seg.G, 0x7c8)).ToString());
        if (placing)
        {
            // f_01efa's loop: the patch under the mouse (f_70edf's arithmetic) inside the range becomes G:07BC / G:07BE
            // and f_70a7d XOR-fills its parallelogram (DS:2A42: (169, 67) (193, 67) (186, 74) (162, 74) from
            // (col * 28 - row * 10, row * 10) past G:10D2 / G:10D4), unless it is the player's own patch
            var mp = GetViewport().GetMousePosition();
            int row = ((int)mp.Y - oy - 67) / 10, col = (row * 10 - 169 + (int)mp.X - ox) / 28;
            if ((int)mp.Y - oy - 67 >= 0 && InPlaceRange(col, row))
            {
                st.Set16(Seg.G, 0x7bc, col);
                st.Set16(Seg.G, 0x7be, row);
                if (col != st.S16(Seg.G, 0x7ca) || row != st.S16(Seg.G, 0x7cc))
                {
                    InvertPatch(area, ox, oy, col, row);
                }
            }
        }
        if (statusText != null && session.St.Clock <= statusUntil)
        {
            // f_7052b: the message's second copy (DS:299A) as a font-2 sprite centred at the top of the yard picture
            var f = ui.Font(2);
            string text = statusText.Replace("\n", " ");
            int w = f.Width(text), x = (pic.l + pic.r - w) / 2;
            area.Fill(x, pic.t + 4, x + w, pic.t + 4 + f.Height - 1, UiArt.White);  // f_15d96 as over the Edit map
            f.Draw(area, x, pic.t + 3, text, UiArt.Black);
        }
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
            ShowStatus(S(15), 180, true);
            return;
        }
        int n = st.S16(Seg.G, 0xaf2) + st.S16(Seg.G, 0xaf4), t = st.U16(Seg.G, 0x4c2);
        if (t == 0x40 || t == 0x20) n--;
        if (n <= 0)
        {
            st.Hooks.Effect(st, "sound", 1, 0x7e);
            ShowStatus(S(5), 180, true);
            return;
        }
        st.Set16(Seg.G, 0x8dc, 0xc8);
        ShowStatus(S(6), 180, true);
    }

    // PLACE (0x1910 → f_01efa): with no new queens (G:07C8 < 1) sound 1 and STR# 1010 [7] (Full Game) or [16];
    // otherwise T:02C0 = 0 (manual placement) and "Click in the yard to place this new queen" ([8]) until a click.
    // The patches within 3 columns and rows of the player's patch G:07CA / G:07CC (clamped to the yard) are in
    // range. A click in range: voice 0x2AFB, G:07C8 - 1, T:00A4[patch] + 1, G:0A90 + 1, G:0C20 = 1, f_01325(1)
    // (not ported), a redraw and [9] "You have started a new colony"; out of range: [10] and sound 1. With Shift
    // held (and queens left) it goes on placing. A click outside the yard ends it.
    bool placing;
    bool yardManual;                                                       // the yard window's MANUAL selected (else AUTOMATIC)

    void StartPlacing()
    {
        var st = session.St;
        string S(int k) => session.Files.Strings(1010)?[k] ?? "";
        if (st.S16(Seg.G, 0x7c8) < 1)
        {
            st.Hooks.Effect(st, "sound", 1, 0x7e);
            ShowStatus(S(st.U16(Seg.G, 0xeac) == 2 ? 7 : 16), 180, true);
            return;
        }
        if (st.U16(Seg.T, 0x2c0) == 1) st.Set16(Seg.T, 0x2c0, 0);
        placing = true;
        ShowStatus(S(8), -1, true);
    }

    bool InPlaceRange(int col, int row)
    {
        var st = session.St;
        int c = st.S16(Seg.G, 0x7ca), r = st.S16(Seg.G, 0x7cc);
        return col >= Math.Clamp(c - 3, 0, 11) && col <= Math.Clamp(c + 3, 0, 11) && row >= Math.Clamp(r - 3, 0, 15) && row <= Math.Clamp(r + 3, 0, 15);
    }

    void PlaceClick(Vector2 p, bool shift)
    {
        var st = session.St;
        string S(int k) => session.Files.Strings(1010)?[k] ?? "";
        var (ox, oy) = YardOrigin();
        int row = ((int)p.Y - oy - 67) / 10, col = (row * 10 - 169 + (int)p.X - ox) / 28;   // as f_70edf
        if (!InPlaceRange(col, row))
        {
            ShowStatus(S(10), 0x78, true);
            st.Hooks.Effect(st, "sound", 1, 0x7e);
            placing = shift;
            return;
        }
        st.Set16(Seg.G, 0x7bc, col);
        st.Set16(Seg.G, 0x7be, row);
        st.Hooks.Effect(st, "voice", 0x2afb);
        st.Set16(Seg.G, 0x7c8, st.S16(Seg.G, 0x7c8) - 1);
        st.Set8(Seg.T, 0xa4 + col * 16 + row, st.U8(Seg.T, 0xa4 + col * 16 + row) + 1);
        st.Set16(Seg.G, 0xa90, st.U16(Seg.G, 0xa90) + 1);
        st.Set16(Seg.G, 0xc20, 1);
        ShowStatus(S(9), 180, true);
        placing = shift && st.S16(Seg.G, 0x7c8) >= 1;
    }

    void YardWindowClick(int index, Vector2 p, bool doubleClick = false)
    {
        var st = session.St;
        if (placing)
        {
            if (Inside(ItemRect(YardWin, 2), p)) PlaceClick(p, Input.IsKeyPressed(Key.Shift));
            else { placing = false; ShowStatus(null, 0, true); }
            return;
        }
        if (!yardChoose)                                                    // f_7650c's loop takes every click as a yard click
        switch (index)
        {
            case 7: BackToPatch(); return;
            case 8:                                                          // f_6f7f0 0x1908: Strat / Graphic → Yard, else Yard ↔ House
                st.Set16(Seg.G, 0x35c, st.S16(Seg.G, 0x35c) >= 2 ? 0 : st.S16(Seg.G, 0x35c) ^ 1);
                return;
            case 9: st.Set16(Seg.G, 0x35c, 2); return;
            case 10: st.Set16(Seg.G, 0x35c, 3); return;
            case 17: help = helpHeld = true; return;                                 // f_2f74e(0x1906), while held
            case 11: Mate(); return;
            case 13: st.Set16(Seg.T, 0x2c0, 1); yardManual = false; return;  // AUTOMATIC: the sim settles the swarm's queens
            case 14: st.Set16(Seg.T, 0x2c0, 0); yardManual = true; return;   // MANUAL
            case 16: yardManual = true; StartPlacing(); return;              // f_22fae(0x190E), f_22fae(0x1910), f_01efa
        }
        var pic = ItemRect(YardWin, 2);
        var (ox, oy) = YardOrigin();
        if (yardChoose)
        {
            // f_7650c's loop: out of the yard: sound 1 and STR# 1010 [10] for 0x78; a patch with no black colony
            // (T:00A4): sound 1 and [19]; else voice 0x2AFB, G:07BC / G:07BE, f_01d48, and the message cleared
            string S(int k) => session.Files.Strings(1010)?[k] ?? "";
            int row = ((int)p.Y - oy - 67) / 10, col = (row * 10 - 169 + (int)p.X - ox) / 28;
            if (col < 0 || row < 0 || col >= 12 || row >= 16) { st.Hooks.Effect(st, "sound", 1); ShowStatus(S(10), 0x78, true); return; }
            if (st.U8(Seg.T, 0xa4 + col * 16 + row) == 0) { st.Hooks.Effect(st, "sound", 1); ShowStatus(S(19), 0x78, true); return; }
            st.Hooks.Effect(st, "voice", 0x2afb);
            st.Set16(Seg.G, 0x7bc, col);
            st.Set16(Seg.G, 0x7be, row);
            NewGame.MoveToPatch(st);
            yardChoose = false;
            ShowStatus(null, -2, true);
            CloseYard();
            SetView(session.Yellow.view);
            return;
        }
        if (!Inside(pic, p)) return;
        int patch = YardRenderer.PatchAt((int)p.X - ox, (int)p.Y - oy);
        if (patch < 0) return;
        st.Set16(Seg.G, 0x7bc, patch >> 4);                                 // f_70edf: the clicked patch
        st.Set16(Seg.G, 0x7be, patch & 15);
        // f_70edf moves (f_01d48) only on a double click (event byte +7 & 0x60, as in f_74fe0), and the shell
        // only in a Full Game
        if (!doubleClick) return;
        if (st.U16(Seg.G, 0xeac) != 2)
        {
            lastMessage = "Moving between patches is for the Full Game.";
            return;
        }
        NewGame.MoveToPatch(st);                                            // f_01d48 (it may refuse: a message)
        if (st.U16(Seg.G, 0x7ca) == patch >> 4 && st.U16(Seg.G, 0x7cc) == (patch & 15))
        {
            yardChoose = false;
            ShowStatus(null, 0, true);
            CloseYard();
            SetView(session.Yellow.view);
        }
    }

    /// <summary>The shell's status lines (a stand-in for the original's message window) in the game's font 2.</summary>
    // The shell's debug lines (tick, populations, speed, its own messages): not in the original, so off unless F12
    // (or --status) turns them on.
    bool showStatus;
    int sceneArg, timedModal = -1;
    bool gameOverSong;
    readonly List<(int x0, int y0, int x1, int y1)> strikes = new();

    void DrawStatus(UiArt.Canvas canvas)
    {
        status.Visible = message.Visible = false;
        if (font == null || !showStatus) return;
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
        st.Set16(Seg.DS, 0x5702, (modal >= 0 ? modal : zOrder.Count > 0 ? zOrder[^1] : 0) << 8);   // the active window (f_23612)
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
                    argb[y * ScreenW + x] = session.Art.Palette[7];                      // the desktop: cyan (the original's screen)
            DrawStatus(canvas);
            foreach (int win in zOrder)
                if (win == EditWin) { DrawEditWindow(canvas); DrawBalloon(canvas); DrawStatusMessage(canvas); }
                else if (win == MapWin) DrawMapWindow(canvas);
                else if (win == HistoryWin) DrawHistoryWindow(canvas);
                else if (win == YardWin) DrawYardWindow(canvas);
                else if (win == TextWin) DrawTextViewer(canvas);
                else DrawControlWindow(canvas, win);
            if (popReport) DrawPopulationReport(canvas);
            if (miniMap) DrawMiniMap(canvas);
            DrawMenuBar(canvas);
            if (modal == EfficiencyWin) DrawEfficiency(canvas);
            if (modal == AntInfoWin) DrawAntInfo(canvas);
            if (modal == SelectWin) ui.DrawWindow(canvas, SelectWin, 0, 0, null);
            DrawScene(canvas);
            if (modal is 27 or 30) DrawMessageBox(canvas);
            if (modal == SavePrompt) DrawSavePrompt(canvas);
            if (modal == GameOverWin) DrawGameOver(canvas);
            if (modal == FileWin) DrawFileDialog(canvas);
            if (modal == AlertWin) DrawAlert(canvas);
            DrawWin(canvas);
            if (modal == TitleWin) canvas.Fill(0, 0, ScreenW, ScreenH, UiArt.Black);
            if (modal == TitleWin) ui.DrawWindow(canvas, modal, 0, 0, null);
            if (modal == AboutWin) DrawAbout(canvas);
            if (modal == 11) ui.DrawWindow(canvas, 11, 245, 200, null);       // "not available in the full game"
            if (popup >= 0) DrawPopup(canvas);
            if (menuOpen >= 0) DrawMenu(canvas);
        }
        DrawCursor(canvas);
        for (int i = 0; i < argb.Length; i++)
        {
            uint c = argb[i];
            rgba[4 * i] = (byte)(c >> 16);
            rgba[4 * i + 1] = (byte)(c >> 8);
            rgba[4 * i + 2] = (byte)c;
            rgba[4 * i + 3] = 255;
        }
        image.SetData(ScreenW, ScreenH, false, Image.Format.Rgba8, rgba);
        strikes.Clear();                                                            // drawn once, until the next redraw
        texture.Update(image);
    }

    public override void _UnhandledInput(InputEvent ev)
    {
        if (session == null) return;
        if (popup < 0 && MenuInput(ev)) return;
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
            int dy = Math.Clamp(dragOrig.dy + (int)d.Y, menus.BarHeight + 1 - r.top, ScreenH - 20 - r.top);
            offsets[dragWin] = (dx, dy);
            return;
        }
        if (ev is InputEventMouseMotion dm && toolDrag)
        {
            ToolMove(dm.Position, dm);                                          // the tool drag loop f_76f4a
            return;
        }
        if (ev is InputEventMouseMotion mn && miniMapDrag)
        {
            MiniMapAt(mn.Position);
            return;
        }
        if (ev is InputEventMouseMotion md && mapDrag)
        {
            var (x0, y0) = MapOrigin();
            int a = (int)(md.Position.X - x0) / 4, b = (int)(md.Position.Y - y0) / 4;
            if (a >= 0 && a < MapRenderer.Width(MapView) && b >= 0 && b < MapRenderer.Height) CenterOn(a, b);
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
            mapDrag = false;
            if (helpHeld) help = helpHeld = false;
            historyHeld = false;
            if (miniMapPress) MiniMapRelease(up.Position);
            miniMapDrag = false;
            popReport = false;
            cardPopup = null;                                                   // f_78e1c waits for the release
            toolDrag = false;
            return;
        }
        if (ev is InputEventMouseButton mb && mb.Pressed)
        {
            if (present != null)                                                // a local loop: the press is its event
            {
                presentPress = true;
                if (modal == 30) modal = -1;
                return;
            }
            if (miniMap)
            {
                MiniMapPress(mb.Position);
                return;
            }
            if (winPhase != 0)                                                  // f_011e5 ends on any event; f_72750's loop only on a key
            {
                if (winPhase != 2) WinNext(true);
                return;
            }
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
            if (modal is TitleWin or GameOverWin)                               // then Select a Game (f_2f848)
            {
                modal = SelectWin;
                selectMidGame = false;
                return;
            }
            if (modal == FileWin)
            {
                FileDialogClick(ui.HitTest(FileWin, 0, 0, (int)mb.Position.X, (int)mb.Position.Y), mb);
                return;
            }
            if (modal == AlertWin)
            {
                AlertClick(mb.Position);
                return;
            }
            if (modal == AboutWin)
            {
                AboutEvent();
                return;
            }
            if (modal >= 0)                                                     // a click closes the modal window
            {
                modal = -1;
                return;
            }
            int win = WindowAt(mb.Position);
            if (win < 0) return;
            bool behind = zOrder[^1] != win;
            Front(win);
            // a click on a window behind the front one only brings it to the front (the original's screen: the yard
            // window's Patch under the SimAntipedia took two clicks); its caption can still be dragged
            if (behind && !Inside(CaptionRect(win), mb.Position)) return;
            if (win == TextWin)                                                 // the SimAntipedia (f_790f0); not dragged
            {
                if (mb.ButtonIndex == MouseButton.Left) AntipediaPress((int)mb.Position.X, (int)mb.Position.Y);
                return;
            }
            if (Inside(CaptionRect(win), mb.Position) && mb.ButtonIndex == MouseButton.Left)
            {
                dragWin = win;                                                  // drag the window by its caption
                dragFrom = mb.Position;
                dragOrig = offsets[win];
                return;
            }
            var (dx, dy) = Off(win);
            int index = ui.HitTest(win, dx, dy, (int)mb.Position.X, (int)mb.Position.Y);
            if (win == EditWin && index == EditMapStrip) index = EditMapItem;   // the strip has the map's id, 4
            if (win == EditWin) EditWindowClick(index, mb);
            else if (win == MapWin && index == MapMapItem && mb.ButtonIndex == MouseButton.Right) MapWindowClick(index, mb);
            else if (mb.ButtonIndex != MouseButton.Left) return;
            else if (win == MapWin) MapWindowClick(index, mb);
            else if (win == HistoryWin) HistoryWindowClick(index);
            else if (win == YardWin) YardWindowClick(index, mb.Position, mb.DoubleClick);
            else ControlWindowClick(win, index, mb.Position);
        }
        else if (ev is InputEventKey k && k.Pressed && !k.Echo)
        {
            if (present != null)
            {
                presentKey = true;
                return;
            }
            if (modal == FileWin)
            {
                FileDialogKey(k);
                return;
            }
            if (modal == AlertWin)
            {
                AlertKey(k);
                return;
            }
            if (winPhase != 0)
            {
                WinNext(true);
                return;
            }
            if (modal is GameOverWin or TitleWin)                               // f_71d95 / f_72bc2: any event closes them
            {
                modal = SelectWin;
                selectMidGame = false;
                return;
            }
            // f_74386: every key goes to the cheat matcher first (f_2f924 → f_6a920), then to the key table
            if (!k.CtrlPressed && !k.AltPressed && k.Unicode is >= 0x20 and < 0x7f) Cheats.Cheat(session.St, (int)k.Unicode);
            if (OriginalKey(k)) return;
            switch (k.Keycode)
            {
                case Key.Key1 when k.CtrlPressed: SetView(1); break;                // the views (the original's are Ctrl+8 / 9 / 0)
                case Key.Key2 when k.CtrlPressed: SetView(2); break;
                case Key.Key3 when k.CtrlPressed: SetView(3); break;
                case Key.Left when !k.CtrlPressed: Scroll(-4, 0); break;
                case Key.Right when !k.CtrlPressed: Scroll(4, 0); break;
                case Key.Up when !k.CtrlPressed: Scroll(0, -4); break;
                case Key.Down when !k.CtrlPressed: Scroll(0, 4); break;
                case Key.Insert or Key.Space or Key.Delete:                                // f_2024b: Insert and Space the left button, Delete the right
                {
                    var mp = GetViewport().GetMousePosition();
                    var button = k.Keycode == Key.Delete ? MouseButton.Right : MouseButton.Left;
                    Input.ParseInputEvent(new InputEventMouseButton { ButtonIndex = button, Pressed = true, Position = mp, GlobalPosition = mp });
                    Input.ParseInputEvent(new InputEventMouseButton { ButtonIndex = button, Pressed = false, Position = mp, GlobalPosition = mp });
                    break;
                }
                case Key.Equal or Key.KpAdd: session.Speed++; break;
                case Key.Minus or Key.KpSubtract: session.Speed--; break;
                case Key.Escape:
                    if (zOrder.Contains(TextWin)) zOrder.Remove(TextWin);
                    else if (zOrder.Contains(YardWin)) CloseYard();
                    break;
                case Key.Tab:                                                              // the Map window: front / close
                    if (zOrder.Contains(MapWin) && zOrder[^1] != MapWin) Front(MapWin);
                    else if (zOrder.Contains(MapWin)) zOrder.Remove(MapWin);
                    else Front(MapWin);
                    break;
                case Key.F1: help = !help; break;                                          // the help overlays
                case Key.F8: QuickSave(); break;
                case Key.F12: showStatus = !showStatus; break;                              // the shell's debug lines                                           // quick save (F5 is the Options menu now)
                case Key.F9: QuickLoad(); break;                                           // load
            }
        }
    }

    /// <summary>The original's keys (SIM_NOTES "Keys and menu commands"): f_74386's table DS:2CBE turns Ctrl and
    /// shifted keys into menu commands 0xFDmn (MenuCommand, f_6e26d), and f_76aeb handles the plain ones. Alt+F / W /
    /// V / O / S and F2..F6 open the pull-down menus 0xFE00..04 (MenuInput).</summary>
    bool OriginalKey(InputEventKey k)
    {
        var st = session.St;
        bool spider = st.U16(Seg.G, 0xa06) != 0, queen = st.U16(Seg.G, 0x4c2) == 0x40 && st.U16(Seg.G, 0xc24) == 0;
        if (k.CtrlPressed && k.AltPressed)
        {
            // f_74386's debug keys (Ctrl held, f_1c160(0x1D)): Alt+V 0x82F shows the version line (the far pointer
            // DS:0064, "Ver 1.00 ...", f_1c6e0). Not kept: Alt+I 0x817 (free memory), Alt+D 0x820 (the fatal-error
            // exit "User Request", f_174cc), Alt+F 0x821 (flush the resource cache).
            if (k.Keycode != Key.V) return false;
            var flat = session.Files.Flat;
            int p = Seg.DS * 16 + 0x64, at = (flat[p + 2] | flat[p + 3] << 8) * 16 + (flat[p] | flat[p + 1] << 8), end = at;
            while (end < flat.Length && flat[end] != 0) end++;
            OpenAlert(System.Text.Encoding.ASCII.GetString(flat, at, end - at), null);
            return true;
        }
        if (k.AltPressed && k.Keycode == Key.J && spider) { Commands.Command(st, 0xc); return true; }   // f_76aeb 0x824
        if (k.CtrlPressed)
        {
            // f_74386's table DS:2CBE, then the scan codes of 8414:0383 (Ctrl+4 the patch, f_013ff; Ctrl+5..0, H, I)
            if (k.Keycode == Key.Key4) { BackToPatch(); return true; }
            int cmd = k.Keycode switch
            {
                Key.N => 0x03, Key.L => 0x04, Key.S => 0x05, Key.A => 0x06, Key.Q or Key.X => 0x08,
                Key.E => 0x11, Key.M => 0x12, Key.B => 0x13, Key.C => 0x14, Key.T => 0x17, Key.Y => 0x21,
                Key.G => 0x31, Key.J => 0x32, Key.K => 0x33,
                Key.Key5 => 0x22, Key.Key6 => 0x23, Key.Key7 => 0x24, Key.Key8 => 0x26, Key.Key9 => 0x27, Key.Key0 => 0x28,
                Key.H => 0x15, Key.I => 0x16, _ => 0,
            };
            if (cmd == 0) return false;
            MenuCommand(0xfd00 | cmd);
            return true;
        }
        if (k.ShiftPressed && k.Keycode is Key.Key0 or Key.Key1 or Key.Key2 or Key.Key3 or Key.Key4)
        {
            MenuCommand(k.Keycode == Key.Key0 ? 0xfd41 : 0xfd43 + (int)(k.Keycode - Key.Key1));   // ')' '!' '@' '#' '$'
            return true;
        }
        if (k.AltPressed && k.Keycode == Key.Key2) { Commands.Command(st, 3); return true; }   // 8414:0383: Alt+2 recruits all
        if (k.AltPressed || k.ShiftPressed && k.Keycode != Key.Backspace) return false;
        switch (k.Keycode)
        {
            case Key.Key0: Commands.Command(st, 7); return true;                             // alarm trail
            case Key.Key1: Commands.Command(st, spider ? 0xa : queen ? 8 : 1); return true;  // chase / dig hole / recruit 5
            case Key.Key2: Commands.Command(st, spider ? 0xb : queen ? 9 : 2); return true;  // hunt / start brood / recruit 10
            case Key.Key3: Commands.Command(st, 4); return true;                             // release half
            case Key.Key4: Commands.Command(st, 5); return true;                             // release all
            case Key.X: Commands.Command(st, 6); return true;                                // exchange
            case Key.Home: PlaySound(0xf); FollowYellow(); return true;                     // 0x847 (scan 0x47): f_00ed8(0xF), f_01c52
            case Key.Backspace:
                var (yv, ya, yb) = session.Yellow;
                if (k.ShiftPressed) { FollowYellow(); return true; }                     // f_01c52
                if (!spider && st.U16(Seg.G, 0xaa0) != 0) { Player.StopAction(st, yv, ya, yb); return true; }   // f_757dd
                if (spider && st.U16(Seg.G, 0xa06) == 1 && (st.S16(Seg.G, 0xf42) != ya || st.S16(Seg.G, 0xf7e) != yb))
                {
                    st.Set16(Seg.G, 0xf42, ya);                                              // the spider stops where it is
                    st.Set16(Seg.G, 0xf7e, yb);
                    st.Set16(Seg.G, 0xfb8, 0);
                    return true;
                }
                if (spider && st.U16(Seg.G, 0xa06) != 1) return true;
                st.Set16(Seg.G, 0x1074, 1);                                                  // f_01c03: recentre
                SetView(yv);
                CenterOnYellow();
                return true;
        }
        return false;
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
    void QuickLoad() => LoadGame(ProjectSettings.GlobalizePath("user://quicksave.ANT"));

    bool LoadGame(string path)
    {
        if (!System.IO.File.Exists(path)) { lastMessage = "No saved game"; return false; }
        bool ok = SaveFile.Load(session.St, System.IO.File.ReadAllBytes(path));
        lastMessage = ok ? "Loaded " + path : "Read error, game not loaded";
        SetView(session.Yellow.view);
        if (ok) CenterOnYellow();                                              // f_725b6's load path: f_034c4 on the yellow ant
        return ok;
    }

    void Restart(int mode)
    {
        session.NewGame(mode);
        lastMessage = "";
        SetView(session.Yellow.view);
        CenterOnYellow();                                                      // f_725b6: f_034c4(G:047C, G:048A)
    }

    // f_01aec(v), the Edit window's view: G:032E = v; each view's centre is kept in G (the surface G:0596 / 0598, the
    // black nest G:06A6 / 06A8, the red nest G:072E / 0730; saved after every scroll, 104a:02ad: G:0FB6 / 2 + G:0508)
    // and the window recentres there (f_01976 → f_034c4); the Map window follows (f_01781(v): T:07C8 = v).
    static readonly int[] CentreSlots = { 0, 0x596, 0x6a6, 0x72e };

    void SetView(int v)
    {
        var st = session.St;
        view = v;
        st.Set16(Seg.G, 0x32e, v);                            // the view on screen
        if (v is >= 1 and <= 3)
        {
            st.Set16(Seg.T, 0x7c8, v);
            originA = st.S16(Seg.G, CentreSlots[v]) - Cols / 2;
            originB = st.S16(Seg.G, CentreSlots[v] + 2) - Rows / 2;
        }
        follow = session.Yellow.view == v;
        Clamp();
    }

    // The main loop's scrolling, one cell per pass while held (f_03210(dx, dy) steps the Edit window's origin
    // G:0508 / G:050A along the line): Ctrl with the keypad / arrow keys (f_74140: Home / PgUp / End / PgDn the
    // diagonals), and the mouse at the screen's edge (f_0113e: x < 2 or >= width - 4, y < 1 or >= height - 4).
    // A pass is about a tick at Normal speed (T:07CE): here every 1 / 8 s.
    double scrollWait;

    void ScrollPoll(double delta)
    {
        if (modal >= 0 || menuOpen >= 0 || popup >= 0) return;
        int dx = 0, dy = 0;
        if (Input.IsKeyPressed(Key.Ctrl))
        {
            if (Input.IsKeyPressed(Key.Kp7) || Input.IsKeyPressed(Key.Home)) { dx--; dy--; }
            if (Input.IsKeyPressed(Key.Kp9) || Input.IsKeyPressed(Key.Pageup)) { dx++; dy--; }
            if (Input.IsKeyPressed(Key.Kp1) || Input.IsKeyPressed(Key.End)) { dx--; dy++; }
            if (Input.IsKeyPressed(Key.Kp3) || Input.IsKeyPressed(Key.Pagedown)) { dx++; dy++; }
            if (Input.IsKeyPressed(Key.Kp6) || Input.IsKeyPressed(Key.Right)) dx++;
            if (Input.IsKeyPressed(Key.Kp4) || Input.IsKeyPressed(Key.Left)) dx--;
            if (Input.IsKeyPressed(Key.Kp8) || Input.IsKeyPressed(Key.Up)) dy--;
            if (Input.IsKeyPressed(Key.Kp2) || Input.IsKeyPressed(Key.Down)) dy++;
        }
        if (dx == 0 && dy == 0 && screenshot == null && GetWindow().HasFocus())
        {
            var mp = GetViewport().GetMousePosition();
            if (mp.X >= 0 && mp.Y >= 0 && mp.X < ScreenW && mp.Y < ScreenH)
            {
                dx = mp.X < 2 ? -1 : mp.X >= ScreenW - 4 ? 1 : 0;
                dy = mp.Y < 1 ? -1 : mp.Y >= ScreenH - 4 ? 1 : 0;
            }
        }
        if (dx == 0 && dy == 0) { scrollWait = 0; return; }
        scrollWait -= delta;
        if (scrollWait > 0) return;
        scrollWait = 1.0 / 8;
        Scroll(Math.Sign(dx) * Math.Max(1, Math.Abs(dx)), Math.Sign(dy) * Math.Max(1, Math.Abs(dy)));
    }

    void Scroll(int da, int db)
    {
        follow = false;
        originA += da;
        originB += db;
        Clamp();
    }
}
