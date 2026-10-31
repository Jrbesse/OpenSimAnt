using Formica.Sim;
using static Formica.Sim.Seg;

namespace Formica.Data;

public static partial class SpiderLegs
{
    /// <summary>A move-to (Line false) or line-to of a leg program.</summary>
    public readonly record struct Op(bool Line, Term X, Term Y);

    /// <summary>k + sign * T[table + register] (table -1: none; register 0 none, 1 si, 2 di).</summary>
    public readonly record struct Term(int K, int Table, int Reg, int Sign);
}

/// <summary>Type-2 bitmaps (tools/bitmaps.py): header u16 mode, u8 planes, u8 flags, u32 size, u16 width,
/// u16 height; rows of interleaved planes (rowbytes = ceil(width / 8), MSB leftmost); mode 3 has a leading
/// mask plane per row. Returns colour indices, -1 where transparent.</summary>
public static class Bitmaps
{
    public static (int w, int h, short[] px) Decode(byte[] d)
    {
        int mode = d[0] | (d[1] << 8), planes = d[2];
        int w = d[8] | (d[9] << 8), h = d[10] | (d[11] << 8);
        int rb = (w + 7) / 8;
        bool masked = mode == 3;
        int np = planes + (masked ? 1 : 0);
        var px = new short[w * h];
        for (int y = 0; y < h; y++)
        {
            int @base = 12 + y * rb * np;
            for (int x = 0; x < w; x++)
            {
                int bit = 0x80 >> (x & 7), bx = x >> 3;
                byte P(int p) => @base + p * rb + bx < d.Length ? d[@base + p * rb + bx] : (byte)0;
                if (planes == 1)
                {
                    px[y * w + x] = (short)((P(0) & bit) != 0 ? 15 : 0);      // Mac convention: 1 = black ink
                    continue;
                }
                int off = masked ? 1 : 0, c = 0;
                for (int i = 0; i < planes && i < 4; i++)
                    if ((P(off + i) & bit) != 0) c |= 1 << i;
                px[y * w + x] = (short)(masked && (P(0) & bit) == 0 ? -1 : c);
            }
        }
        return (w, h, px);
    }
}

/// <summary>The spider on the surface (f_03de7 and its leg routines; render_view.spider): its bitmap at its
/// 1/16-cell position (1 px at 16 px per cell) and the legs and fangs as lines.</summary>
public static class SpiderRenderer
{
    static readonly Dictionary<int, (int w, int h, short[] px)> cache = new();
    static readonly Random jitterRng = new();

    /// <summary>The fangs' frame: Rand(4) when the spider hunts or eats (G:0FB8 > 1) or is enraged (G:06AC
    /// >= 6), else 0. The original draws it from the game's LFSR during the redraw; this uses its own
    /// generator so that drawing never shifts the simulation (see HANDOFF, "redraw draws from the RNG").</summary>
    public static int FangJitter(State st) => st.U16(G, 0xfb8) > 1 || st.U16(G, 0x6ac) >= 6 ? jitterRng.Next(4) : 0;

    /// <summary>f_03de7: the bitmap and its offset: walking frame 1000 + G:1004 (offsets T:09BC / T:09C4), or
    /// 1050 + G:1042 while beaten (G:0FB8 == 5; offsets T:09CC / T:09D0).</summary>
    public static (int rid, int dx, int dy) Frame(State st)
    {
        if (st.U16(G, 0xfb8) == 5)
        {
            int f = st.U16(G, 0x1042);
            return (1050 + f, st.S8(T, 0x9cc + f), st.S8(T, 0x9d0 + f));
        }
        int h = st.U16(G, 0x1004);
        return (1000 + h, st.S8(T, 0x9bc + h), st.S8(T, 0x9c4 + h));
    }

    /// <summary>Draw the spider into an ARGB view whose top-left pixel is map pixel (ox, oy). `jitter` is the
    /// fangs' frame, which the original draws as Rand(4) when G:0FB8 > 1 or G:06AC >= 6 (else 0).</summary>
    public static void Draw(State st, OriginalFiles files, MapArt art, uint[] dst, int stride, int height, int ox, int oy, int jitter)
    {
        if (st.U16(G, 0xf0c) == 0) return;
        var (rid, dx, dy) = Frame(st);
        if (!cache.TryGetValue(rid, out var bmp))
        {
            var r = files.Get("HCEGANT", 2, rid);
            bmp = r == null ? (0, 0, Array.Empty<short>()) : Bitmaps.Decode(r.Data);
            cache[rid] = bmp;
        }
        int x0 = st.S16(G, 0xf12) + dx - ox, y0 = st.S16(G, 0xf34) + dy - oy;
        for (int y = 0; y < bmp.h; y++)
            for (int x = 0; x < bmp.w; x++)
            {
                int c = bmp.px[y * bmp.w + x];
                int px = x0 + x, py = y0 + y;
                if (c >= 0 && px >= 0 && px < stride && py >= 0 && py < height) dst[py * stride + px] = art.Palette[c];
            }
        if (st.U16(G, 0xfb8) == 5) return;
        int sx = st.S16(G, 0xf12), sy = st.S16(G, 0xf34), heading = st.U16(G, 0x1004) & 7;
        int frame = st.U16(G, 0x1042) & 7;
        Program(st, SpiderLegs.Legs[heading], sx, sy, frame, (frame + 4) & 7, art.Palette[15], dst, stride, height, ox, oy);
        Program(st, SpiderLegs.Fangs[heading], sx, sy, jitter, 0, art.Palette[st.U16(G, 0xa06) == 1 ? 1 : 15], dst, stride, height, ox, oy);
    }

    static void Program(State st, SpiderLegs.Op[] ops, int x, int y, int si, int di, uint colour, uint[] dst, int stride, int height, int ox, int oy)
    {
        int V(SpiderLegs.Term t, int @base)
        {
            int v = @base + t.K;
            if (t.Table >= 0) v += t.Sign * st.S8(T, t.Table + (t.Reg == 1 ? si : t.Reg == 2 ? di : 0));
            return v;
        }
        bool pen = false;
        int px = 0, py = 0;
        foreach (var op in ops)
        {
            int nx = V(op.X, x), ny = V(op.Y, y);
            if (op.Line && pen) Line(dst, stride, height, px - ox, py - oy, nx - ox, ny - oy, colour);
            pen = true;
            px = nx;
            py = ny;
        }
    }

    /// <summary>Bresenham, both ends included (the original draws with f_16b58; checked by eye).</summary>
    static void Line(uint[] img, int stride, int height, int x0, int y0, int x1, int y1, uint c)
    {
        int dx = Math.Abs(x1 - x0), dy = -Math.Abs(y1 - y0);
        int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
        int err = dx + dy;
        for (int n = 0; n < 4096; n++)
        {
            if (y0 >= 0 && y0 < height && x0 >= 0 && x0 < stride) img[y0 * stride + x0] = c;
            if (x0 == x1 && y0 == y1) return;
            int e2 = 2 * err;
            if (e2 >= dy) { err += dy; x0 += sx; }
            if (e2 <= dx) { err += dx; y0 += sy; }
        }
    }
}
