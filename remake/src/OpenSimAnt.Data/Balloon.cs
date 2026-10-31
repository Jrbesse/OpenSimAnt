namespace OpenSimAnt.Data;

/// <summary>A speech balloon as f_1629c ("MakeBaloon") builds it from a line of text (SIM_NOTES "Speech balloons"):
/// the text is split at its literal backslash-n breaks (up to 10 more lines) and measured in the current font (font 2,
/// f_07134 sets it); the balloon is (widest + 0x17) &amp; ~7 px wide and lines * font height + 16 tall, put together from
/// the 8 x 8 pieces at DS:1D0A (16 bytes each, 8 rows of two bytes: the white inside, then the whole shape; shape
/// without inside is the black outline, the rest is transparent): top-left 1D0A, top 1D2A (repeated), top-right 1D1A;
/// rows from y = 8 of left 1D4A, inside 1D8A, right 1D3A while y &lt; height - 8; at y = lines * font height + 6
/// bottom-left 1D5A, bottom 1D7A, bottom-right 1D6A, and the tail 1DAA in the second column (f_1629c(text, 0); 1D9A,
/// a tail on the right, goes in the second-last). Line i is drawn at x = 8 + ((-width) &amp; 6) / 2 (its byte-aligned
/// shift), y = 6 + i * font height. The height is then 1 less, 2 for a single line.</summary>
public static class Balloon
{
    const int Ds = 0x55b3 * 16;
    const int TL = 0x1d0a, TR = 0x1d1a, T = 0x1d2a, R = 0x1d3a, L = 0x1d4a, BL = 0x1d5a, BR = 0x1d6a, B = 0x1d7a,
        Fill = 0x1d8a, TailRight = 0x1d9a, TailLeft = 0x1daa;

    public const uint Transparent = 0, White = 0xffffffffu, Black = 0xff000000u;

    /// <summary>The balloon for `text` (lines separated by "\n" or the strings' literal backslash-n): width, height
    /// and ARGB pixels (0 transparent).</summary>
    public static (int w, int h, uint[] px) Make(byte[] flat, BitmapFont font, string text, bool tailRight = false)
    {
        var lines = text.Replace("\\n", "\n").Split('\n').Take(11).ToArray();
        int lineH = font.Height, n = lines.Length;
        int widest = lines.Max(font.Width);
        int w = (widest + 0x17) & ~7, cells = w >> 3, e = cells - 2;
        int full = lineH * n + 16;
        var px = new uint[w * full];
        void Piece(int at, int cx, int y)
        {
            for (int r = 0; r < 8; r++)
            {
                int yy = y + r;
                if (yy < 0 || yy >= full) continue;
                byte inside = flat[Ds + at + 2 * r], shape = flat[Ds + at + 2 * r + 1];
                for (int bit = 0; bit < 8; bit++)
                {
                    int xx = cx * 8 + bit;
                    if (xx >= w) continue;
                    int m = 0x80 >> bit;
                    px[yy * w + xx] = (shape & m) == 0 ? Transparent : (inside & m) != 0 ? White : Black;
                }
            }
        }
        Piece(TL, 0, 0);
        for (int i = 0; i < e; i++) Piece(T, 1 + i, 0);
        Piece(TR, e + 1, 0);
        for (int y = 8; y < full - 8; y += 8)
        {
            for (int i = 0; i < e; i++) Piece(Fill, 1 + i, y);
            Piece(L, 0, y);
            Piece(R, e + 1, y);
        }
        int yb = lineH * n + 6;
        Piece(BR, e + 1, yb);
        Piece(BL, 0, yb);
        for (int i = 0; i < e; i++) Piece(B, 1 + i, yb);
        Piece(tailRight ? TailRight : TailLeft, tailRight ? e - 1 : 1, yb);
        for (int i = 0; i < n; i++)
        {
            int tw = font.Width(lines[i]);
            font.Draw(px, w, full, 8 + ((-tw & 6) >> 1), 6 + i * lineH, lines[i], Black);
        }
        int h = full - 1 - (n == 1 ? 1 : 0);
        return (w, h, h == full ? px : px.AsSpan(0, w * h).ToArray());
    }
}
