namespace Formica.Data;

/// <summary>Drawing the original's windows from their layouts (Layouts, FILE_FORMATS "Window layouts") into an
/// ARGB screen buffer: pictures (HCEGANT type-2 bitmaps), text items in the game's fonts (SHARED type 11),
/// frames, fills and captions as the item drawer f_223b3 does them, in the item's colour scheme (Schemes).</summary>
public sealed class UiArt
{
    public readonly OriginalFiles Files;
    public readonly uint[] Palette;
    public readonly Dictionary<int, WindowLayout> Layouts;
    readonly Dictionary<int, (int w, int h, short[] px)> bitmaps = new();
    readonly Dictionary<int, BitmapFont> fonts = new();

    public const uint White = 0xffffffffu, Black = 0xff000000u, Grey = 0xffc2c2c2u, DarkGrey = 0xff818181u;   // palette 0, 15, 12, 13 through the 6-bit DAC

    /// <summary>The colour schemes (HCEGANT type 0 id 129, copied to G:46E2 by f_210d0; 6 bytes each): byte 0 the
    /// foreground, byte 2 the background (byte 3 in the video modes with DS:5A97 bit 0; not VGA), as palette indices.
    /// f_220e4 picks an item's scheme (LayoutItem.ColourScheme). Frames are drawn in DS:3DE0, the scheme's foreground.</summary>
    public readonly (uint fg, uint bg)[] Schemes;

    /// <summary>Palette colour → the colour of index ^ 15 (Canvas.Invert).</summary>
    public static Dictionary<uint, uint> XorMap;

    public UiArt(OriginalFiles files, MapArt art)
    {
        Files = files;
        Palette = art.Palette;
        Layouts = Data.Layouts.All(files);
        XorMap = new Dictionary<uint, uint>();
        for (int i = 0; i < 16; i++) XorMap.TryAdd(Palette[i], Palette[i ^ 15]);
        var t = files.Get("HCEGANT", 0, 129)?.Data ?? Array.Empty<byte>();
        Schemes = Enumerable.Range(0, t.Length / 6).Select(i => (Palette[t[6 * i] & 15], Palette[t[6 * i + 2] & 15])).ToArray();
        Checkers = Enumerable.Range(0, t.Length / 6).Select(i => (t[6 * i + 2] & 15) != (t[6 * i + 3] & 15) ? Palette[t[6 * i + 3] & 15] : (uint?)null).ToArray();
        SchemeBytes = Enumerable.Range(0, t.Length / 6).Select(i => t.AsSpan(6 * i, 6).ToArray()).ToArray();
    }

    /// <summary>The colour schemes' six bytes (HCEGANT type 0 id 129): foreground, a second foreground, background, a
    /// second background, two undecoded.</summary>
    public readonly byte[][] SchemeBytes;

    /// <summary>f_222b5, a type-5 button's bevel, from its scheme byte +26 (whatever the selection): unselected, for th =
    /// 3, 2, 1 the left and right bands th px wide over the full height in byte 3 (f_1d098), then the top and bottom bands
    /// between them th px tall, a checker of byte 3 where x + y is even and byte 2 where odd (f_1d802), which leaves
    /// diagonal corners; selected (+24 bit 2), a 3-px frame in byte 0, then a 2-px one in byte 3 over it (f_1d26d; the
    /// second only while DS:5A97 bit 0 is clear, as on the original's screen).</summary>
    void Bevel(Canvas c, LayoutItem it, int l, int t, int r, int b)
    {
        if (it.Scheme >= SchemeBytes.Length) return;
        var sb = SchemeBytes[it.Scheme];
        uint c0 = Palette[sb[0] & 15], c2 = Palette[sb[2] & 15], c3 = Palette[sb[3] & 15];
        if ((it.Flags & 4) != 0)
        {
            ThickFrame(c, l, t, r, b, 3, c0);
            ThickFrame(c, l, t, r, b, 2, c3);
            return;
        }
        for (int th = 3; th > 0; th--)
        {
            c.Fill(l, t, l + th, b, c3);
            c.Fill(r - th, t, r, b, c3);
            foreach (int y0 in new[] { t, b - th })
                for (int y = Math.Max(y0, c.T); y < Math.Min(y0 + th, c.B); y++)
                    for (int x = Math.Max(l + th, c.L); x < Math.Min(r - th, c.R); x++)
                        c.Px[y * c.Stride + x] = ((x + y) & 1) == 0 ? c3 : c2;
        }
    }

    /// <summary>f_22170, the fill of an item's background: when a scheme's bytes 2 and 3 differ, a 50% checker (the
    /// driver's pattern 0, DS:9138) of byte 3 where x + y is odd and byte 2 where it is even, e.g. the captions'
    /// dark / light grey (scheme 1); else byte 2 solid. Checked on the original's screen (tools/re/screens.py).</summary>
    public readonly uint?[] Checkers;

    public void FillScheme(Canvas c, int l, int t, int r, int b, LayoutItem it)
    {
        var (_, bg) = SchemeOf(it);
        uint? odd = it.ColourScheme < Checkers.Length ? Checkers[it.ColourScheme] : null;
        if (odd is not { } o) { c.Fill(l, t, r, b, bg); return; }
        for (int y = Math.Max(t, c.T); y < Math.Min(b, c.B); y++)
            for (int x = Math.Max(l, c.L); x < Math.Min(r, c.R); x++)
                c.Px[y * c.Stride + x] = ((x + y) & 1) != 0 ? o : bg;
    }

    public (uint fg, uint bg) SchemeOf(LayoutItem it) =>
        it.ColourScheme < Schemes.Length ? Schemes[it.ColourScheme] : (Black, Grey);

    /// <summary>f_1d018: a frame `w` px thick inside the rectangle; f_1d802 with `sides` (1 left, 2 top, 4 right,
    /// 8 bottom) draws only those.</summary>
    public static void ThickFrame(Canvas c, int l, int t, int r, int b, int w, uint colour, int sides = 15)
    {
        if (w <= 0) return;
        if ((sides & 2) != 0) c.Fill(l + w, t, r - w, t + w, colour);
        if ((sides & 8) != 0) c.Fill(l + w, b - w, r - w, b, colour);
        if ((sides & 1) != 0) c.Fill(l, t, l + w, b, colour);
        if ((sides & 4) != 0) c.Fill(r - w, t, r, b, colour);
    }

    /// <summary>A text item's alignment, (word +24 &amp; 0x180) >> 7, as DrawText takes it.</summary>
    static int Align(LayoutItem it) => ((it.Flags & 0x180) >> 7) switch { 1 => 1, 2 => 2, _ => 0 };

    public (int w, int h, short[] px) Bitmap(int id)
    {
        if (bitmaps.TryGetValue(id, out var b)) return b;
        // HCEGANT's colour bitmaps first, then SHARED's 1-bit ones (the SimAntipedia's pictures)
        var r = Files.Get("HCEGANT", 2, id) ?? Files.Get("SHARED", 2, id);
        b = r == null ? (0, 0, Array.Empty<short>()) : Bitmaps.Decode(r.Data);
        bitmaps[id] = b;
        return b;
    }

    public BitmapFont Font(int id)
    {
        if (fonts.TryGetValue(id, out var f)) return f;
        // f_24d5d: fonts 2..5 are the slots DS:4A1A.. that start-up (f_34ab_047d) fills from the files FONT1..FONT4
        // (Mac FONTs; 1 and 2 have the glyph widths of SHARED 2 and 3, 3 is 15 px tall, 4 is the bold the
        // SimAntipedia's links use). Without them, and for 0 / 1, the SHARED type-11 fonts.
        var r = Files.Get("SHARED", 11, id);
        f = id is >= 2 and <= 5 && Files.FontFiles.TryGetValue(id - 1, out var file) ? new BitmapFont(file)
            : r == null ? null : new BitmapFont(r.Data);
        fonts[id] = f;
        return f;
    }

    /// <summary>A screen buffer and a clip rectangle (right / bottom exclusive).</summary>
    public readonly record struct Canvas(uint[] Px, int Stride, int Height, int L, int T, int R, int B)
    {
        public Canvas(uint[] px, int stride, int height) : this(px, stride, height, 0, 0, stride, height) { }

        public Canvas Clip(int l, int t, int r, int b) =>
            this with { L = Math.Max(L, l), T = Math.Max(T, t), R = Math.Min(R, r), B = Math.Min(B, b) };

        public void Plot(int x, int y, uint c)
        {
            if (x >= L && x < R && y >= T && y < B) Px[y * Stride + x] = c;
        }

        public void Fill(int l, int t, int r, int b, uint c)
        {
            l = Math.Max(l, L); t = Math.Max(t, T); r = Math.Min(r, R); b = Math.Min(b, B);
            for (int y = t; y < b; y++)
                Array.Fill(Px, c, y * Stride + l, Math.Max(0, r - l));
        }

        public void Frame(int l, int t, int r, int b, uint c)
        {
            Fill(l, t, r, t + 1, c);
            Fill(l, b - 1, r, b, c);
            Fill(l, t, l + 1, b, c);
            Fill(r - 1, t, r, b, c);
        }

        /// <summary>Invert a rectangle as the VGA driver's XOR fill does (DS:913C, f_1d250: the highlighted items,
        /// PAUSE, the current view's button): palette index ^ 15 (brown becomes purple, light grey red; checked on
        /// the original's screen); colours outside the palette are inverted in RGB.</summary>
        public void Invert(int l, int t, int r, int b)
        {
            l = Math.Max(l, L); t = Math.Max(t, T); r = Math.Min(r, R); b = Math.Min(b, B);
            var map = XorMap;
            for (int y = t; y < b; y++)
                for (int x = l; x < r; x++)
                {
                    uint p = Px[y * Stride + x];
                    Px[y * Stride + x] = map != null && map.TryGetValue(p, out var q) ? q : p ^ 0x00ffffffu;
                }
        }

        /// <summary>Copy a block of ARGB pixels (w x h) with its top-left at (x, y).</summary>
        public void Blit(uint[] src, int w, int h, int x, int y)
        {
            for (int j = Math.Max(0, T - y); j < h && y + j < B; j++)
                for (int i = Math.Max(0, L - x); i < w && x + i < R; i++)
                    Px[(y + j) * Stride + x + i] = src[j * w + i];
        }
    }

    public void DrawBitmap(Canvas c, int id, int x, int y)
    {
        var (w, h, px) = Bitmap(id);
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                int k = px[j * w + i];
                if (k >= 0) c.Plot(x + i, y + j, Palette[k & 15]);
            }
    }

    /// <summary>f_21fa2: text in item rectangle (l, t, r, b), font `font`, alignment 0 / 3 centred, 1 left + 4,
    /// 2 right - width - 4, never left of `l`; vertically centred. `clip`: clipped to the rectangle (f_223b3 does that
    /// only for items whose flags have bit 0x200, +25 bit 1: f_1ece3; f_21fa2 itself does not clip).</summary>
    public void DrawText(Canvas c, int font, int align, int l, int t, int r, int b, string text, uint colour = Black, uint? back = null, bool clip = true)
    {
        if (!clip) { DrawText(c, font, align, l, t, r, b, text, colour, back, c); return; }
        DrawText(c, font, align, l, t, r, b, text, colour, back, c.Clip(l, t, r, b));
    }

    void DrawText(Canvas c, int font, int align, int l, int t, int r, int b, string text, uint colour, uint? back, Canvas cc)
    {
        var f = Font(font) ?? Font(2);
        if (f == null || string.IsNullOrEmpty(text)) return;
        if (font == 0)
        {
            // font 0 is the PC font of the BIOS (8 x 14 cells, DS:3DDE / DS:3DDC: f_24dd9 / f_24dbb measure it so), drawn
            // opaque in the item's background when given: a caption's title sits in a dark box on the checker (the original's
            // screen, tools/re/screens.py). The ROM glyphs are not available: SHARED's font 0 stands in for them.
            int cw = 8 * text.Length, ch = 14;
            int cx = Math.Max(l, align switch { 1 => l + 4, 2 => r - cw - 4, _ => (l + r - cw) / 2 });
            int cy = (t + b - ch) / 2;
            if (back is { } bk) cc.Fill(cx, cy, cx + cw, cy + ch, bk);
            for (int i = 0; i < text.Length; i++)
                if (text[i] != ' ') f.Draw(cc.Clip(cx + 8 * i, cy, cx + 8 * i + 8, cy + ch), cx + 8 * i, cy, text[i].ToString(), colour);
            return;
        }
        int w = f.Width(text);
        int x = align switch { 1 => l + 4, 2 => r - w - 4, _ => (l + r - w) / 2 };
        x = Math.Max(x, l);
        // f_21fa2 / f_20a0f: y = (t + b - the font's height) / 2, the height of an Apple FONT being fRectHeight - 1, its
        // strike drawn from y - 1
        int y = f.IsMac ? (t + b - (f.Height - 1)) / 2 - 1 : (t + b - f.Height) / 2;
        f.Draw(cc, x, y, text, colour);
    }

    /// <summary>f_23943 → f_232ae → f_20a0f: a value drawn into item rectangle (l, t, r, b), clipped to it: centred
    /// (never left of l), y = t + (b - t - height) / 2 (truncated; an Apple FONT's height is fRectHeight - 1, its strike
    /// drawn from y - 1), its row filled with `back` when given.</summary>
    public void DrawValue(Canvas c, int font, int l, int t, int r, int b, string text, uint colour = Black, uint? back = null)
    {
        var f = Font(font) ?? Font(2);
        if (f == null) return;
        int fh = f.IsMac ? f.Height - 1 : f.Height, w = f.Width(text ?? "");
        int x = Math.Max(l, (l + r - w) / 2), y = t + (b - t - fh) / 2;
        var clip = c.Clip(l, t, r, b);
        if (back is { } bk) clip.Fill(l, y, r, y + fh, bk);                   // the row, the text's cells included
        if (!string.IsNullOrEmpty(text)) f.Draw(clip, x, f.IsMac ? y - 1 : y, text, colour);
    }

    /// <summary>A horizontal gauge (f_23971: a 16.16 fraction of the item's width), filled black on white.</summary>
    public static void Gauge(Canvas c, (int l, int t, int r, int b) rect, double fraction, uint colour = Black)
    {
        var (l, t, r, b) = rect;
        c.Fill(l, t, r, b, White);
        c.Frame(l, t, r, b, Black);
        int w = (int)Math.Round((r - l - 2) * Math.Clamp(fraction, 0, 1));
        c.Fill(l + 1, t + 1, l + 1 + w, b - 1, colour);
    }

    /// <summary>A vertical gauge filled from the bottom (the Edit window's health bars).</summary>
    public static void VGauge(Canvas c, (int l, int t, int r, int b) rect, double fraction, uint colour = Black)
    {
        var (l, t, r, b) = rect;
        c.Fill(l, t, r, b, White);
        int h = (int)Math.Round((b - t) * Math.Clamp(fraction, 0, 1));
        c.Fill(l, b - h, r, b, colour);
    }

    /// <summary>Draw window `id`'s frame, caption, pictures, frames and static text, moved by (dx, dy). Pictures
    /// listed in `hidden` (help overlays) are skipped.</summary>
    public void DrawWindow(Canvas c, int id, int dx, int dy, string title, ICollection<int> hidden = null, ICollection<int> skipItems = null)
    {
        if (!Layouts.TryGetValue(id, out var w)) return;
        var (wl, wt, wr, wb) = w.Rect;
        var clip = c.Clip(wl + dx, wt + dy, wr + dx, wb + dy);
        clip.Fill(wl + dx, wt + dy, wr + dx, wb + dy, Grey);
        DrawItems(clip, w, dx, dy, title, hidden, skipItems);
        DrawDecorations(clip, w, dx, dy);
    }

    /// <summary>
    /// f_21336 opening window `id` at rectangle `rect` (stored in the header's +10..+16), then f_25595 laying out its
    /// items. Each edge e (left, top, right, bottom) of an item has a mode (+18 + 2e), a reference (+10 + 2e: window
    /// &lt;&lt; 8 | item index) and an offset (+08 + 2e: x, y, w, h); f_25409 computes it: mode 0 = the offset, 1..4 =
    /// edge (mode - 1) of the referenced item + the offset (f_254a3), 5 = edge (reference) of `rect` + the offset
    /// (f_25527). Every edge starts unknown (0x8000) and the passes repeat until nothing changes; then f_25561 swaps
    /// reversed edges, and the window's rectangle is item 0's. `offsets` replaces items' offsets first (f_22ccd, by
    /// index; the file dialog's Load mode). A reference into another window (pop-ups 6, 20, 23 hang off an item of
    /// window 0 or 1) reads that window's item through `foreign` (reference → its rectangle, or null), by default the
    /// stored layout. Checked on every layout (LayoutTests: each gives its stored rectangles back).
    /// </summary>
    public WindowLayout Relayout(int id, (int l, int t, int r, int b) rect, IReadOnlyDictionary<int, (int x, int y, int w, int h)> offsets = null,
                                 Func<int, (int l, int t, int r, int b)?> foreign = null)
    {
        foreign ??= rf => Layouts.TryGetValue(rf >> 8, out var fw) && (rf & 0xff) < fw.Items.Count ? fw.Items[rf & 0xff].Rect : null;
        var w = Layouts[id];
        const int Unknown = -0x8000;
        int n = w.Items.Count;
        var off = new int[n][];
        var mode = new int[n][];
        var refs = new int[n][];
        var e = new int[n][];
        for (int i = 0; i < n; i++)
        {
            var it = w.Items[i];
            var o = offsets != null && offsets.TryGetValue(i, out var ov) ? ov : (it.Pos.x, it.Pos.y, it.Size.w, it.Size.h);
            off[i] = new[] { o.x, o.y, o.w, o.h };
            mode[i] = it.Attach ?? new[] { 1, 2, 1, 2 };
            refs[i] = it.Refs ?? new[] { 0, 0, i, i };
            e[i] = new[] { Unknown, Unknown, Unknown, Unknown };
        }
        int[] req = { rect.l, rect.t, rect.r, rect.b };
        for (int pass = 0, changed = 1; changed != 0 && pass < 4 * n + 4; pass++)    // the original loops until stable
        {
            changed = 0;
            for (int i = 0; i < n; i++)
                for (int k = 0; k < 4; k++)
                {
                    int m = mode[i][k], v;
                    if (m == 0) v = off[i][k];
                    else if (m <= 4)
                    {
                        int rf = refs[i][k], j = rf & 0xff, bv;
                        if (rf >> 8 == id) bv = j < n ? e[j][m - 1] : Unknown;
                        else if (foreign(rf) is { } fr) bv = (m - 1) switch { 0 => fr.l, 1 => fr.t, 2 => fr.r, _ => fr.b };
                        else bv = Unknown;
                        v = bv == Unknown ? Unknown : bv + off[i][k];
                    }
                    else if (m == 5 && (uint)refs[i][k] < 4) v = req[refs[i][k]] + off[i][k];
                    else v = Unknown;
                    if (v != e[i][k]) { e[i][k] = v; changed = 1; }
                }
        }
        var items = new List<LayoutItem>(n);
        for (int i = 0; i < n; i++)
        {
            int l = Math.Min(e[i][0], e[i][2]), r = Math.Max(e[i][0], e[i][2]);
            int t = Math.Min(e[i][1], e[i][3]), b = Math.Max(e[i][1], e[i][3]);
            var o = off[i];
            items.Add(w.Items[i] with { Rect = (l, t, r, b), Pos = (o[0], o[1]), Size = (o[2], o[3]) });
        }
        var box = n > 0 ? items[0].Rect : (rect.l, rect.t, rect.r, rect.b);
        return new WindowLayout(id, box, items) { Flags = w.Flags };
    }

    /// <summary>f_21336 opening window `id` at `rect` (Relayout), then, for a window whose header has +1D bit 4 (flags
    /// 0x1000: the pop-up menus), keeping it on the screen: below the bottom (480) it moves up by the overshoot, else
    /// with its top at or above G:3942 (17, under the menu bar) down to it; left of 0 it moves right, else with its
    /// right at or past 640 left by the overshoot. The shift goes into item 0's offsets and the layout is solved again.
    /// Checked on the original's screen (the yellow ant's menu, layout 7: (16, 8) from the press point).</summary>
    public WindowLayout Open(int id, (int l, int t, int r, int b) rect, int top = 17, int width = 640, int height = 480)
    {
        var w = Relayout(id, rect);
        if ((Layouts[id].Flags & 0x1000) == 0 || w.Items.Count == 0) return w;
        var (l, t, r, b) = w.Rect;
        int dy = b > height ? height - b : top >= t ? top - t : 0;
        int dx = l < 0 ? -l : r >= width ? width - r : 0;
        if (dx == 0 && dy == 0) return w;
        var it = Layouts[id].Items[0];
        return Relayout(id, rect, new Dictionary<int, (int x, int y, int w, int h)> { [0] = (it.Pos.x + dx, it.Pos.y + dy, it.Size.w, it.Size.h) });
    }

    /// <summary>f_2271d, the window's decorations by the header flags (+1C / +1D) inside the window less its first
    /// item's thickness (+28): bit 2 the close box 100 at the top left (the left edge moves past it), bit 4 bitmap 101
    /// there, bit 3 the grow box 112 at the bottom right; +1D bit 0 the zoom box at the top right (102 with +1C bit 7,
    /// else 103; the right edge moves left of it), +1D bit 2 bitmap 105 left of that. Checked on the original's
    /// screen (the Edit window: close, 105, 103 and the grow box).</summary>
    public void DrawDecorations(Canvas c, WindowLayout w, int dx = 0, int dy = 0)
    {
        if (w.Items.Count == 0) return;
        int th = w.Items[0].Style;
        int l = w.Rect.left + dx + th, t = w.Rect.top + dy + th, r = w.Rect.right + dx - th, b = w.Rect.bottom + dy - th;
        int f = w.Flags;
        if ((f & 4) != 0) { DrawBitmap(c, 100, l, t); l += Bitmap(100).w; }
        if ((f & 8) != 0) { var (gw, gh, _) = Bitmap(112); DrawBitmap(c, 112, r - gw, b - gh); }
        if ((f & 0x100) != 0)
        {
            int z = (f & 0x80) != 0 ? 102 : 103;
            r -= Bitmap(z).w;
            DrawBitmap(c, z, r, t);
        }
        if ((f & 0x10) != 0) DrawBitmap(c, 101, l, t);
        if ((f & 0x400) != 0) { r -= Bitmap(105).w; DrawBitmap(c, 105, r, t); }
    }

    /// <summary>Draw a (re-laid) layout's items, no background fill.</summary>
    public void DrawLayout(Canvas c, WindowLayout w, string title = null) => DrawItems(c, w, 0, 0, title, null);

    void DrawItems(Canvas clip, WindowLayout w, int dx, int dy, string title, ICollection<int> hidden, ICollection<int> skipItems = null)
    {
        foreach (var it in w.Items)
        {
            if (skipItems != null && skipItems.Contains(it.Id)) continue;
            var (l, t, r, b) = it.Rect;
            l += dx; t += dy; r += dx; b += dy;
            var (fg, bg) = SchemeOf(it);
            // f_223b3 by type: 0 box (fill, frame of thickness +28), 2 fill, 5 fill + text, 9 text, 0x0C fill, a line
            // under it, text; 0x0F frame; 0x10 text; 0x11 fill + text; 0x12 caption (fill, line under, text); 0x13 /
            // 0x14 left and right / top and bottom lines, 0x15 / 0x16 the same after a fill. Frames are drawn in DS:3DE0, the
            // scheme's foreground (f_220e4 → f_9128), checked on the original's screen (Select a Game: scheme 6, red).
            switch (it.Type)
            {
                case 0x00:
                    FillScheme(clip, l, t, r, b, it);
                    ThickFrame(clip, l, t, r, b, it.Style, fg);
                    break;
                case 0x02:
                    FillScheme(clip, l, t, r, b, it);
                    break;
                case 0x0f:
                    ThickFrame(clip, l, t, r, b, it.Style, fg);
                    break;
                case 0x13 or 0x14 or 0x15 or 0x16:
                    if (it.Type >= 0x15) FillScheme(clip, l, t, r, b, it);
                    ThickFrame(clip, l, t, r, b, it.Style, fg, it.Type is 0x13 or 0x15 ? 5 : 10);
                    break;
                case 0x12:
                    FillScheme(clip, l, t, r, b, it);
                    clip.Fill(l, b - 1, r, b, fg);
                    DrawText(clip, it.Style, Align(it), l, t, r, b, it.Text != null && !it.Text.Contains('%') ? it.Text : title ?? "", fg, bg, ClipsText(it));
                    break;
                case 0x06:
                    if (hidden == null || !hidden.Contains(it.Bitmap)) DrawBitmap(clip, it.Bitmap, l, t);
                    break;
                case 0x0d:
                    DrawBitmap(clip, it.Bitmaps[0], l, t);
                    break;
                case 0x05 or 0x11:                                               // f_223b3: a solid fill of byte 2, the bevel, text
                    clip.Fill(l, t, r, b, bg);
                    Bevel(clip, it, l, t, r, b);
                    if (it.Text != null && !it.Text.Contains('%')) DrawText(clip, it.Style, Align(it), l, t, r, b, it.Text, fg, null, ClipsText(it));
                    break;
                case 0x09 or 0x0c or 0x10:
                    if (it.Type == 0x0c) FillScheme(clip, l, t, r, b, it);
                    if (it.Type == 0x0c) clip.Fill(l, b - 1, r, b, fg);
                    if (it.Text != null && !it.Text.Contains('%')) DrawText(clip, it.Style, Align(it), l, t, r, b, it.Text, fg, null, ClipsText(it));
                    break;
            }
        }
    }

    /// <summary>Run-time text in an item, as f_223b3 draws its text types: a fill first for types 5, 0x0C and 0x11,
    /// then the text in the item's font (+28, or `font`), alignment and scheme colour.</summary>
    public void ItemText(Canvas c, LayoutItem it, int dx, int dy, string text, int font = -1)
    {
        var (l, t, r, b) = it.Rect;
        var (fg, bg) = SchemeOf(it);
        if (it.Type is 0x05 or 0x11)
        {
            c.Fill(l + dx, t + dy, r + dx, b + dy, bg);
            Bevel(c, it, l + dx, t + dy, r + dx, b + dy);
        }
        else if (it.Type == 0x0c) FillScheme(c, l + dx, t + dy, r + dx, b + dy, it);
        DrawText(c, font >= 0 ? font : it.Style, Align(it), l + dx, t + dy, r + dx, b + dy, text, fg, null, ClipsText(it));
    }

    /// <summary>f_223b3 clips an item's drawing to its rectangle only with flags bit 0x200 (+25 bit 1: f_1f31a / f_1ece3).</summary>
    static bool ClipsText(LayoutItem it) => (it.Flags & 0x200) != 0;

    /// <summary>f_241f2, a list item (type 4): rows of the font at +28 from the item's top, as many as fit ((bottom -
    /// top) / height); each row's text at the item's left (no margin) in scheme +26, or +27 when the row's flag bit 0
    /// (selected) is set, the rest of the row filled with the background (f_24edb); rows past the end filled.</summary>
    public void DrawList(Canvas c, LayoutItem it, IReadOnlyList<(bool selected, string text)> rows, int first)
    {
        var f = Font(it.Style) ?? Font(2);
        var (l, t, r, b) = it.Rect;
        var clip = c.Clip(l, t, r, b);
        int n = ListRows(it), y = t, h = ListRowHeight(it);
        for (int i = 0; i < n; i++, y += h)
        {
            var (fg, bg) = Schemes[i + first < rows.Count && rows[i + first].selected ? it.AltScheme : it.Scheme];
            clip.Fill(l, y, r, y + h, i + first < rows.Count ? bg : SchemeOf(it).bg);
            if (i + first >= rows.Count) continue;
            var text = rows[i + first].text;
            if (it.Style == 0)                                                   // the BIOS font: 8 x 14 cells
            {
                for (int k = 0; k < text.Length; k++)
                    if (text[k] != ' ') f.Draw(clip.Clip(l + 8 * k, y, l + 8 * k + 8, y + 14), l + 8 * k, y, text[k].ToString(), fg);
            }
            else f.Draw(clip, l, y, text, fg);
        }
    }

    /// <summary>A list row's height: the font's (f_24dbb), 14 for font 0 (the BIOS font's cells, as for item text).</summary>
    public int ListRowHeight(LayoutItem it) => it.Style == 0 ? 14 : (Font(it.Style) ?? Font(2)).Height;

    /// <summary>The rows a list item shows (f_241f2 stores it at +2A).</summary>
    public int ListRows(LayoutItem it) => (it.Rect.bottom - it.Rect.top) / ListRowHeight(it);

    /// <summary>The arrow height G:47DC (bitmap 109's).</summary>
    public int ArrowHeight => Bitmap(109).h;

    /// <summary>f_244cc, a vertical scroll bar (type 8, its list's id at +28): the up arrow (bitmap 109) at the top,
    /// the down arrow (111) at the bottom - G:47DC, the track between them in the scheme's background, then the thumb
    /// (f_24378) when the list holds more rows than it shows: inside the track less a pixel on each side, its height
    /// span * visible / total (at least 10), its top first * (span - height) / (total - visible), in the foreground.</summary>
    public void DrawScrollbar(Canvas c, LayoutItem it, int visible, int total, int first)
    {
        var (l, t, r, b) = it.Rect;
        var (fg, bg) = SchemeOf(it);
        int ah = ArrowHeight;
        DrawBitmap(c, 109, l, t);
        DrawBitmap(c, 111, l, b - ah);
        c.Fill(l, t + ah, r, b - ah, bg);
        if (total <= visible) return;
        int x0 = l + 1, x1 = r - 1, y0 = t + ah + 1, y1 = b - (ah + 1), span = y1 - y0;
        int h = Math.Max(10, span * visible / total);
        int top = first * (span - h) / (total - visible);
        if (top > 0) c.Fill(x0, y0, x1, y0 + top, bg);
        c.Fill(x0, y0 + top, x1, y0 + top + h, fg);
        if (h + top < span) c.Fill(x0, y0 + top + h, x1, y1, bg);
    }

    /// <summary>The item of window `id` with item id `item`, or null.</summary>
    public LayoutItem Item(int id, int item) =>
        Layouts.TryGetValue(id, out var w) ? w.Items.FirstOrDefault(i => i.Id == item) : null;

    /// <summary>The index (in layout order) of the topmost hotspot-like item of window `id` (moved by dx, dy)
    /// under (x, y), skipping frames, captions and pictures; -1 if none. Item ids are not unique in every
    /// window (window 0 reuses 0x0000), so callers match on the index.</summary>
    public int HitTest(int id, int dx, int dy, int x, int y)
    {
        if (!Layouts.TryGetValue(id, out var w)) return -1;
        int hit = -1;
        for (int i = 0; i < w.Items.Count; i++)
        {
            var it = w.Items[i];
            if (it.Kind is "frame3d" or "caption" or "picture" or "box" or "frame") continue;
            var (l, t, r, b) = it.Rect;
            if (x >= l + dx && x < r + dx && y >= t + dy && y < b + dy) hit = i;
        }
        return hit;
    }
}
