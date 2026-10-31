using OpenSimAnt.Sim;
using static OpenSimAnt.Sim.Seg;

namespace OpenSimAnt.Data;

/// <summary>The yard window (layout 25, f_702f7; tools/ref/render_view.py yard_sprites / yard_colonies; SIM_NOTES
/// "The yard window"). Coordinates are relative to the yard origin G:10D2 / G:10D4 = item 0x1902's corner + (1, 0).
/// The yard has 12 x 16 patches (col 0..11, row 0..15); patch (col, row) has its corner at (28 col - 10 row,
/// 10 row) and is the parallelogram corner + the words DS:2A42.. (169, 67), (193, 67), (186, 74), (162, 74).</summary>
public static class YardRenderer
{
    static int Ds8(State st, int off) => st.S8(DS, off);

    /// <summary>The actors in drawing order as (bitmap id, x, y): the cat (f_7004e), the dog (f_6feb3), the human
    /// (f_6fc6e), the mower (f_701a5), the bird crossing (f_6ff93), the "For Sale" sign (f_70126), and while it
    /// rains (G:0352) 15 raindrops (f_70601) and the mating-flight swarms (f_706d0). The original draws the
    /// raindrops' spots from the game's LFSR (Rand(400) + 50, Rand(150)) on every frame of the yard window; this
    /// takes them from `rain` so that drawing never shifts the simulation (a DIVERGENCE, like the spider's fangs).</summary>
    public static List<(int rid, int x, int y)> Sprites(State st, Random rain, bool human = true)
    {
        var o = new List<(int, int, int)>();
        if (st.U16(G, 0x254) != 0)
        {
            int f = st.U16(G, 0x244), x = st.S16(G, 0x2be), y = st.S16(G, 0x32c);
            if (f >= 10 && f < 20) { x += Ds8(st, 0x2aa4 + f); y += Ds8(st, 0x2aa8 + f); }
            else if (f >= 20) { x += Ds8(st, 0x2aa2 + f); y += Ds8(st, 0x2aac + f); }
            o.Add((1300 + f, x, y));
        }
        if (st.U16(T, 0xc44) == 0)
        {
            int f = st.U16(G, 0x4e4);
            var (dx, dy) = f < 12 ? (0x2a8e, 0x2a9a) : (0x2a42, 0x2a46);
            o.Add((8500 + f, st.S16(G, 0x4be) + Ds8(st, dx + f), st.S16(G, 0x4c6) + Ds8(st, dy + f)));
        }
        {
            int f = st.S16(T, 0xc32);
            bool mowing = st.U16(T, 0xc28) is 3 or 4;
            int hx = st.S16(T, 0xc2c), hy = st.S16(T, 0xc2e);
            if (f >= 0 && (human || st.U16(T, 0xc28) != 0))
            {
                int x = hx, y = hy;
                foreach (var (lim, dx, dy) in new[] { (12, 0x2a56, 0x2a62), (24, 0x2a5a, 0x2a5e), (200, 0x2a12, 0x2a1e) })
                    if (f < lim)
                    {
                        x += Ds8(st, dx + f);
                        y += Ds8(st, dy + f);
                        break;
                    }
                o.Add((8000 + f, x, y));
            }
            if (!mowing) o.Add((8800, 0x62, 0xb5));
            else if (f >= 0x67 && f <= 0x69) o.Add((8801, hx + 0x13, hy + 0xf));
            else if (f >= 0x6d && f <= 0x6f) o.Add((8802, hx - 0xf, hy + 0xf));
        }
        if (st.U16(G, 0x10a0) != 0)
        {
            int f = st.U16(G, 0x108c);
            o.Add((1250 + f, st.S16(G, 0x10ac) - 10 + (f != 0 ? 1 : 0), st.S16(G, 0x10ba) - 3 + (f != 0 ? 2 : 0)));
        }
        if (st.U16(T, 0xc44) != 0) o.Add((1260, 0xaa, 0xba));
        if (st.U16(G, 0x352) != 0)
        {
            for (int i = 0; i < 15; i++) o.Add((7005, rain.Next(400) + 50, rain.Next(150)));
            int col = st.S16(G, 0x7ca), row = st.S16(G, 0x7cc);
            int bx = 28 * col - 10 * row + 0xb2, by = 10 * row + 0x2e;
            foreach (var (count, ox, oy, rid) in new[] { (0x7c8, 0xf46, 0xf84, 7006), (0x850, 0xfc6, 0x1008, 7007) })
                for (int i = 0; i < Math.Min(16, Math.Max(0, (int)st.S16(G, count))); i++)
                    o.Add((rid, bx + st.S8(G, ox + i), by + st.S8(G, oy + i)));
        }
        return o;
    }

    /// <summary>f_70edf: the patch (col * 16 + row, the index of T:00A4 / T:0164) under (x, y) relative to the yard
    /// origin, or -1: row = (y - DS:2A44) / 10, col = (row * 10 - DS:2A42 + x) / 28 with C's truncating division
    /// (so the cells have no gaps, and a few pixels left of / above the grid still count as col / row 0).</summary>
    public static int PatchAt(int x, int y)
    {
        int row = (y - 67) / 10;
        int col = (row * 10 - 169 + x) / 28;
        return col >= 0 && col < 12 && row >= 0 && row < 16 ? col * 16 + row : -1;
    }

    /// <summary>The colony views (G:035C >= 2): 'strat' (f_70b82) fills each patch's parallelogram with DS:2AD2[k]
    /// and outlines it with DS:2ACA[k], k = 0 black only, 1 both, 2 red only, 3 none; 'graphic' (f_70cf5) stands
    /// bars of height (strength + 3) >> 2 on 10 row + 0x47, 9 px wide, black (0x0F) at x 28 col - 10 row + 168 and
    /// red (0x23) at + 180. Colour codes: the VGA driver draws their low nibble only (the high nibble is a pattern
    /// for other display modes).
    /// The parallelogram is f_1faa6: rows from p0.y up to (not including) p2.y, each from the left edge to (not
    /// including) the right one, the edges 16.16 fixed point from p0 / p1 stepping by (p0.x - p3.x) &lt;&lt; 16 / height
    /// and (p1.x - p2.x) &lt;&lt; 16 / height; fill == frame paints the row solid, else (DS:9138 with pattern 0, DS:41D0)
    /// a checkerboard: the fill colour where x + y is odd, the frame colour elsewhere. No separate outline.</summary>
    public static void DrawColonies(UiArt.Canvas c, State st, uint[] pal, int ox, int oy, bool strat)
    {
        for (int col = 0; col < 12; col++)
            for (int row = 0; row < 16; row++)
            {
                int black = st.U8(T, 0xa4 + col * 16 + row), red = st.U8(T, 0x164 + col * 16 + row);
                int x = ox + 28 * col - 10 * row, y = oy + 10 * row;
                if (strat)
                {
                    int k = black != 0 ? (red == 0 ? 0 : 1) : (red == 0 ? 3 : 2);
                    int fill = st.U16(DS, 0x2ad2 + 2 * k), frame = st.U16(DS, 0x2aca + 2 * k);
                    var p = new (int x, int y)[4];
                    for (int i = 0; i < 4; i++) p[i] = (x + st.S16(DS, 0x2a42 + 4 * i), y + st.S16(DS, 0x2a44 + 4 * i));
                    int top = p[0].y, bottom = p[2].y, dy = bottom - top;
                    int slopeL = dy == 0 ? 0 : (int)(((long)(p[0].x - p[3].x) << 16) / dy);
                    int slopeR = dy == 0 ? 0 : (int)(((long)(p[1].x - p[2].x) << 16) / dy);
                    int accL = p[0].x << 16, accR = p[1].x << 16;
                    for (int yy = top; yy < bottom; yy++)
                    {
                        int l = accL >> 16, r = accR >> 16;
                        if (l > r) (l, r) = (r, l);
                        for (int xx = l; xx < r; xx++)
                            c.Plot(xx, yy, pal[(fill == frame || ((xx + yy) & 1) == 0 ? fill : frame) & 15]);  // fill where x + y is even (the original's screen)
                        accL -= slopeL;
                        accR -= slopeR;
                    }
                }
                else
                    foreach (var (strength, dx, code) in new[] { (black, 168, 0x0f), (red, 180, 0x23) })
                    {
                        int h = (strength + 3) >> 2;
                        if (h > 0) c.Fill(x + dx, y + 0x47 - h, x + dx + 9, y + 0x47, pal[code & 15]);
                    }
            }
    }
}
