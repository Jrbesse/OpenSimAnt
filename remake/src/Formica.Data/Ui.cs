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
        var t = files.Hcegant.FirstOrDefault(r => r.Type == 0 && r.Id == 129)?.Data ?? Array.Empty<byte>();
        Schemes = Enumerable.Range(0, t.Length / 6).Select(i => (Palette[t[6 * i] & 15], Palette[t[6 * i + 2] & 15])).ToArray();
        Checkers = Enumerable.Range(0, t.Length / 6).Select(i => (t[6 * i + 2] & 15) != (t[6 * i + 3] & 15) ? Palette[t[6 * i + 3] & 15] : (uint?)null).ToArray();
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
        var r = Files.Hcegant.FirstOrDefault(x => x.Type == 2 && x.Id == id) ?? Files.Shared.FirstOrDefault(x => x.Type == 2 && x.Id == id);
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
        string file = Path.Combine(Files.Dir, $"FONT{id - 1}");
        var r = Files.Shared.FirstOrDefault(x => x.Type == 11 && x.Id == id);
        f = id is >= 2 and <= 5 && File.Exists(file) ? new BitmapFont(File.ReadAllBytes(file))
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
    /// 2 right - width - 4, never left of `l`; vertically centred.</summary>
    public void DrawText(Canvas c, int font, int align, int l, int t, int r, int b, string text, uint colour = Black, uint? back = null)
    {
        var f = Font(font) ?? Font(2);
        if (f == null || string.IsNullOrEmpty(text)) return;
        if (font == 0 && back is { } bk)
        {
            // font 0 is the PC font of the BIOS (8 x 14 cells, DS:3DDE / DS:3DDC), drawn opaque in the item's background:
            // a caption's title sits in a dark box on the checker (the original's screen, tools/re/screens.py)
            int cw = 8 * text.Length, ch = 14;
            int cx = Math.Max(l, align switch { 1 => l + 4, 2 => r - cw - 4, _ => (l + r - cw) / 2 });
            int cy = (t + b - ch) / 2;
            var cc = c.Clip(l, t, r, b);
            cc.Fill(cx, cy, cx + cw, cy + ch, bk);
            for (int i = 0; i < text.Length; i++)
                if (text[i] != ' ') f.Draw(cc.Clip(cx + 8 * i, cy, cx + 8 * i + 8, cy + ch), cx + 8 * i, cy, text[i].ToString(), colour);
            return;
        }
        int w = f.Width(text);
        int x = align switch { 1 => l + 4, 2 => r - w - 4, _ => (l + r - w) / 2 };
        x = Math.Max(x, l);
        int y = (t + b - f.Height) / 2;
        var clip = c.Clip(l, t, r, b);
        f.Draw(clip.Px, clip.Stride, clip.B, x, y, text, colour);
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
    public void DrawWindow(Canvas c, int id, int dx, int dy, string title, ICollection<int> hidden = null)
    {
        if (!Layouts.TryGetValue(id, out var w)) return;
        var (wl, wt, wr, wb) = w.Rect;
        var clip = c.Clip(wl + dx, wt + dy, wr + dx, wb + dy);
        clip.Fill(wl + dx, wt + dy, wr + dx, wb + dy, Grey);
        DrawItems(clip, w, dx, dy, title, hidden);
    }

    /// <summary>
    /// f_21336 opening window `id` at rectangle `rect`: each item edge follows its attach mode (+18: left, top,
    /// right, bottom) against the new rectangle: left / top 0 = pos as stored, 1 / 2 = the window's left / top +
    /// pos, 3 / 4 = the window's right / bottom + pos, 5 = the same edge + pos; right / bottom 1 / 2 = the item's own
    /// left / top + size, 3 / 4 and 5 = the window's right / bottom + size. Checked on layouts 27, 30 and 33.
    /// </summary>
    public WindowLayout Relayout(int id, (int l, int t, int r, int b) rect)
    {
        var w = Layouts[id];
        var items = new List<LayoutItem>();
        foreach (var it in w.Items)
        {
            var a = it.Attach ?? new[] { 1, 2, 1, 2 };
            int l = a[0] switch { 0 => it.Pos.x, 3 => rect.r + it.Pos.x, _ => rect.l + it.Pos.x };
            int t = a[1] switch { 0 => it.Pos.y, 4 => rect.b + it.Pos.y, _ => rect.t + it.Pos.y };
            int r = a[2] is 3 or 5 ? rect.r + it.Size.w : l + it.Size.w;
            int b = a[3] is 4 or 5 ? rect.b + it.Size.h : t + it.Size.h;
            items.Add(it with { Rect = (l, t, r, b) });
        }
        return new WindowLayout(id, (rect.l, rect.t, rect.r, rect.b), items);
    }

    /// <summary>Draw a (re-laid) layout's items, no background fill.</summary>
    public void DrawLayout(Canvas c, WindowLayout w, string title = null) => DrawItems(c, w, 0, 0, title, null);

    void DrawItems(Canvas clip, WindowLayout w, int dx, int dy, string title, ICollection<int> hidden)
    {
        foreach (var it in w.Items)
        {
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
                    DrawText(clip, it.Style, Align(it), l, t, r, b, it.Text != null && !it.Text.Contains('%') ? it.Text : title ?? "", fg, bg);
                    break;
                case 0x06:
                    if (hidden == null || !hidden.Contains(it.Bitmap)) DrawBitmap(clip, it.Bitmap, l, t);
                    break;
                case 0x0d:
                    DrawBitmap(clip, it.Bitmaps[0], l, t);
                    break;
                case 0x05 or 0x09 or 0x0c or 0x10 or 0x11:
                    if (it.Type is 0x05 or 0x0c or 0x11) FillScheme(clip, l, t, r, b, it);
                    if (it.Type == 0x0c) clip.Fill(l, b - 1, r, b, fg);
                    if (it.Text != null && !it.Text.Contains('%')) DrawText(clip, it.Style, Align(it), l, t, r, b, it.Text, fg);
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
        if (it.Type is 0x05 or 0x0c or 0x11) FillScheme(c, l + dx, t + dy, r + dx, b + dy, it);
        DrawText(c, font >= 0 ? font : it.Style, Align(it), l + dx, t + dy, r + dx, b + dy, text, fg);
    }

    /// <summary>f_241f2, a list item (type 4): rows of the font at +28 from the item's top, as many as fit ((bottom -
    /// top) / height); each row's text at the item's left (no margin) in scheme +26, or +27 when the row's flag bit 0
    /// (selected) is set, the rest of the row filled with the background (f_24edb); rows past the end filled.</summary>
    public void DrawList(Canvas c, LayoutItem it, IReadOnlyList<(bool selected, string text)> rows, int first)
    {
        var f = Font(it.Style) ?? Font(2);
        var (l, t, r, b) = it.Rect;
        var clip = c.Clip(l, t, r, b);
        int n = ListRows(it), y = t;
        for (int i = 0; i < n; i++, y += f.Height)
        {
            var (fg, bg) = Schemes[i + first < rows.Count && rows[i + first].selected ? it.AltScheme : it.Scheme];
            clip.Fill(l, y, r, y + f.Height, i + first < rows.Count ? bg : SchemeOf(it).bg);
            if (i + first < rows.Count) f.Draw(clip, l, y, rows[i + first].text, fg);
        }
    }

    /// <summary>The rows a list item shows (f_241f2 stores it at +2A).</summary>
    public int ListRows(LayoutItem it) => (it.Rect.bottom - it.Rect.top) / (Font(it.Style) ?? Font(2)).Height;

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
