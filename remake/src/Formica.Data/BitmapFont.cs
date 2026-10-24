using System.Buffers.Binary;

namespace Formica.Data;

/// <summary>The game's bitmap fonts (SHARED type 11; tools/fonts.py).
/// Fonts 0 and 1, the game's own format (little-endian): +0 u16 (0xF9 / 0xFA), +2 u16 height, +4 u16 first
/// character, +6 255 x u16 glyph offsets, +0x204 255 x u16 (not decoded), +0x402 255 x u16 advance widths,
/// glyphs: height rows of (offset step / height) bytes, MSB leftmost.
/// Fonts 2 and 3, Apple FONT / NFNT (big-endian): the header, the strike (rowWords * 2 bytes x fRectHeight
/// rows), the location table and the offset / width table (at 16 + owTLoc * 2; high byte offset, low byte
/// width, 0xFFFF missing).</summary>
public sealed class BitmapFont
{
    readonly byte[] d;
    readonly bool mac;
    readonly int first, last, kernMax, rowBytes, bpr;
    readonly int[] loc, ow, offs, adv;
    public readonly int Height, Ascent;

    /// <summary>An Apple FONT (fonts 2..5): the original counts its height as fRectHeight - 1 (f_262eb) and draws its
    /// strike from one row above the text's y.</summary>
    public bool IsMac => mac;

    public BitmapFont(byte[] data)
    {
        d = data;
        mac = (d[0] & 0xf0) == 0x90 && (d[1] == 0 || d[1] == 1);
        if (mac)
        {
            short H(int i) => BinaryPrimitives.ReadInt16BigEndian(d.AsSpan(2 * i));
            first = H(1);
            last = H(2);
            kernMax = H(4);
            Height = H(7);
            int owtLoc = H(8);
            Ascent = H(9);
            rowBytes = H(12) * 2;
            int n = last - first + 3;
            loc = new int[n];
            ow = new int[n];
            for (int i = 0; i < n; i++)
            {
                loc[i] = BinaryPrimitives.ReadUInt16BigEndian(d.AsSpan(26 + rowBytes * Height + 2 * i));
                ow[i] = BinaryPrimitives.ReadUInt16BigEndian(d.AsSpan(16 + owtLoc * 2 + 2 * i));
            }
        }
        else
        {
            Height = BinaryPrimitives.ReadUInt16LittleEndian(d.AsSpan(2));
            Ascent = Height;
            first = BinaryPrimitives.ReadUInt16LittleEndian(d.AsSpan(4));
            offs = new int[255];
            adv = new int[255];
            for (int i = 0; i < 255; i++)
            {
                offs[i] = BinaryPrimitives.ReadUInt16LittleEndian(d.AsSpan(6 + 2 * i));
                adv[i] = BinaryPrimitives.ReadUInt16LittleEndian(d.AsSpan(0x402 + 2 * i));
            }
            int step = int.MaxValue;
            for (int i = 0; i < 254; i++)
            {
                int s = offs[i + 1] - offs[i];
                if (s > 0) step = Math.Min(step, s);
            }
            bpr = step == int.MaxValue ? 1 : Math.Max(1, step / Height);
        }
    }

    /// <summary>A character's advance as the original measures it (f_2616e): the width table's width (a missing glyph
    /// takes the missing-glyph entry, font +0x28), plus 1 in a font with a negative kernMax (font +8: FONT1 and FONT4).</summary>
    public int Advance(int c)
    {
        int k = c - first;
        if (mac)
        {
            if (k < 0 || k > last - first || ow[k] == 0xffff) k = last - first + 1;
            return (ow[k] == 0xffff ? 0 : ow[k] & 0xff) + (kernMax < 0 ? 1 : 0);
        }
        return k >= 0 && k < 255 ? adv[k] : 0;
    }

    public int Width(string text) => text.Sum(ch => Advance(MacCode(ch)));

    /// <summary>The font's character code for a character of OriginalFiles.MacText (Mac Roman for the few
    /// non-ASCII characters the game's strings use).</summary>
    public static int MacCode(char ch) => ch switch
    {
        '…' => 0xc9, '–' => 0xd0, '—' => 0xd1, '•' => 0xa5, '©' => 0xa9, '™' => 0xaa,
        _ => ch,
    };

    /// <summary>Draw text with its top-left at (x, y) into an ARGB buffer; returns the end x.</summary>
    public int Draw(uint[] dst, int stride, int height, int x, int y, string text, uint colour) =>
        Draw(x, y, text, (px, py) => Plot(dst, stride, height, px, py, colour));

    /// <summary>Draw text with its top-left at (x, y), clipped to the canvas; returns the end x.</summary>
    public int Draw(UiArt.Canvas c, int x, int y, string text, uint colour) => Draw(x, y, text, (px, py) => c.Plot(px, py, colour));

    int Draw(int x, int y, string text, Action<int, int> plot)
    {
        foreach (char ch in text)
        {
            int c = MacCode(ch), k = c - first;
            if (mac)
            {
                if (k >= 0 && k <= last - first && ow[k] != 0xffff)
                {
                    int x0 = loc[k], x1 = loc[k + 1];
                    // f_2632e: with a negative kernMax the glyph goes at the pen (its offset ignored), else at pen + kernMax + offset
                    int gx = kernMax < 0 ? x : x + (ow[k] >> 8) + kernMax;
                    for (int row = 0; row < Height; row++)
                        for (int px = x0; px < x1; px++)
                            if (((d[26 + row * rowBytes + (px >> 3)] >> (7 - (px & 7))) & 1) != 0)
                                plot(gx + px - x0, y + row);
                }
            }
            else if (k >= 0 && k < 255)
            {
                int o = offs[k];
                for (int row = 0; row < Height; row++)
                    for (int px = 0; px < bpr * 8; px++)
                    {
                        int byteAt = o + row * bpr + (px >> 3);
                        if (byteAt < d.Length && ((d[byteAt] >> (7 - (px & 7))) & 1) != 0) plot(x + px, y + row);
                    }
            }
            x += Advance(c);
        }
        return x;
    }

    static void Plot(uint[] dst, int stride, int height, int x, int y, uint c)
    {
        if (x >= 0 && x < stride && y >= 0 && y < height) dst[y * stride + x] = c;
    }
}
