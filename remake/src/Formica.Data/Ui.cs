namespace Formica.Data;

/// <summary>Drawing the original's windows from their layouts (Layouts, FILE_FORMATS "Window layouts") into an
/// ARGB screen buffer: pictures (HCEGANT type-2 bitmaps), text items in the game's fonts (SHARED type 11),
/// frames and captions. The frame styles are only named from their drawing routines (f_22170, f_22248, ...),
/// not traced, so frames are drawn as plain 1-px outlines in the Mac style the pictures use.</summary>
public sealed class UiArt
{
    public readonly OriginalFiles Files;
    public readonly uint[] Palette;
    public readonly Dictionary<int, WindowLayout> Layouts;
    readonly Dictionary<int, (int w, int h, short[] px)> bitmaps = new();
    readonly Dictionary<int, BitmapFont> fonts = new();

    public const uint White = 0xffffffffu, Black = 0xff000000u, Grey = 0xffc0c0c0u, DarkGrey = 0xff808080u;

    public UiArt(OriginalFiles files, MapArt art)
    {
        Files = files;
        Palette = art.Palette;
        Layouts = Data.Layouts.All(files);
    }

    public (int w, int h, short[] px) Bitmap(int id)
    {
        if (bitmaps.TryGetValue(id, out var b)) return b;
        var r = Files.Hcegant.FirstOrDefault(x => x.Type == 2 && x.Id == id);
        b = r == null ? (0, 0, Array.Empty<short>()) : Bitmaps.Decode(r.Data);
        bitmaps[id] = b;
        return b;
    }

    public BitmapFont Font(int id)
    {
        if (fonts.TryGetValue(id, out var f)) return f;
        var r = Files.Shared.FirstOrDefault(x => x.Type == 11 && x.Id == id);
        f = r == null ? null : new BitmapFont(r.Data);
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

        /// <summary>Invert the colours of a rectangle (a highlighted menu entry).</summary>
        public void Invert(int l, int t, int r, int b)
        {
            l = Math.Max(l, L); t = Math.Max(t, T); r = Math.Min(r, R); b = Math.Min(b, B);
            for (int y = t; y < b; y++)
                for (int x = l; x < r; x++)
                    Px[y * Stride + x] ^= 0x00ffffffu;
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
    public void DrawText(Canvas c, int font, int align, int l, int t, int r, int b, string text, uint colour = Black)
    {
        var f = Font(font) ?? Font(2);
        if (f == null || string.IsNullOrEmpty(text)) return;
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
        foreach (var it in w.Items)
        {
            var (l, t, r, b) = it.Rect;
            l += dx; t += dy; r += dx; b += dy;
            switch (it.Kind)
            {
                case "frame3d":
                    clip.Frame(l, t, r, b, Black);
                    clip.Frame(l + 1, t + 1, r - 1, b - 1, White);
                    clip.Fill(r - 2, t + 1, r - 1, b - 1, DarkGrey);
                    clip.Fill(l + 1, b - 2, r - 1, b - 1, DarkGrey);
                    break;
                case "caption":
                    clip.Fill(l, t, r, b, White);
                    clip.Fill(l, b - 1, r, b, Black);
                    DrawText(clip, 0, 0, l, t, r, b, it.Text != null && !it.Text.Contains('%') ? it.Text : title ?? "");
                    break;
                case "box":
                    clip.Fill(l, t, r, b, White);
                    clip.Frame(l, t, r, b, Black);
                    break;
                case "frame":
                    clip.Frame(l, t, r, b, Black);
                    break;
                case "picture":
                    if (hidden == null || !hidden.Contains(it.Bitmap)) DrawBitmap(clip, it.Bitmap, l, t);
                    break;
                case "toggle_picture":
                    DrawBitmap(clip, it.Bitmaps[0], l, t);
                    break;
                case "text" or "text_button" or "filled_text":
                    if (it.Kind == "text_button") clip.Frame(l, t, r, b, Black);
                    if (it.Text != null && !it.Text.Contains('%')) DrawText(clip, it.Param & 0xff, 0, l, t, r, b, it.Text);
                    break;
            }
        }
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
