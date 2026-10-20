using Formica.Sim;
using static Formica.Sim.Seg;

namespace Formica.Data;

/// <summary>The map windows' art from the player's files (tools/tiles.py, tools/ref/render_view.py): the
/// palette (HCEGANT type 15 id 0, the Mac 4-bit palette), the 256-tile background sheets (type 9: id 10 the
/// yard, 9 the house) and the 128-sprite sheets (type 9: id 14 the surface, 13 the nests).
/// A tile is 16 rows of 4 planes x 2 bytes (MSB leftmost); a sprite row is 12 bytes: mask, recolour mask,
/// 4 planes. Sprites are stored in the yellow ant's colours: black ants XOR every plane with the recolour mask
/// (mode 0), red ants only plane 1 (mode 3), the yellow ant none.</summary>
public sealed class MapArt
{
    public readonly uint[] Palette = new uint[16];          // 0xAARRGGBB
    readonly byte[] yardTiles, houseTiles, surfaceSprites, nestSprites;
    readonly Dictionary<(bool, int), byte[]> tileCache = new();
    readonly Dictionary<(int, int, int), short[]> spriteCache = new();

    public MapArt(OriginalFiles files)
    {
        var pal = files.Find(15, 0).Data;
        int n = (pal[0] << 8) | pal[1];
        // the VGA driver loads the DAC with each component >> 2 (6 bits); shown as 6-bit * 255 / 63, as tools/re/vga.py
        // renders the original's screens
        static uint Q(byte c) => (uint)((c >> 2) * 255 / 63);
        for (int i = 0; i < Math.Min(n, 16); i++)
            Palette[i] = 0xff000000u | (Q(pal[2 + 3 * i]) << 16) | (Q(pal[3 + 3 * i]) << 8) | Q(pal[4 + 3 * i]);
        houseTiles = files.Find(9, 9).Data;
        yardTiles = files.Find(9, 10).Data;
        nestSprites = files.Find(9, 13).Data;
        surfaceSprites = files.Find(9, 14).Data;
    }

    /// <summary>16 x 16 colour indices of background tile t.</summary>
    public byte[] Tile(bool house, int t)
    {
        if (tileCache.TryGetValue((house, t), out var px)) return px;
        var sheet = house ? houseTiles : yardTiles;
        px = new byte[256];
        for (int y = 0; y < 16; y++)
            for (int x = 0; x < 16; x++)
            {
                int i = t * 128 + y * 8 + (x >> 3), bit = 7 - (x & 7);
                int c = 0;
                for (int p = 0; p < 4; p++)
                    if (i + 2 * p < sheet.Length) c |= ((sheet[i + 2 * p] >> bit) & 1) << p;
                px[y * 16 + x] = (byte)c;
            }
        tileCache[(house, t)] = px;
        return px;
    }

    /// <summary>16 x 16 colour indices of sprite s (sheet 13 or 14), -1 where transparent.</summary>
    public short[] Sprite(int sheet, int s, int mode)
    {
        if (spriteCache.TryGetValue((sheet, s, mode), out var px)) return px;
        var data = sheet == 13 ? nestSprites : surfaceSprites;
        px = new short[256];
        for (int y = 0; y < 16; y++)
        {
            int r = s * 192 + y * 12;
            for (int x = 0; x < 16; x++)
            {
                int bit = 7 - (x & 7), bx = x >> 3;
                if (r + 11 >= data.Length || ((data[r + bx] >> bit) & 1) == 0)
                {
                    px[y * 16 + x] = -1;
                    continue;
                }
                int xor = (data[r + 2 + bx] >> bit) & 1;
                int c = 0;
                for (int p = 0; p < 4; p++)
                {
                    int v = (data[r + 4 + 2 * p + bx] >> bit) & 1;
                    if (mode == 0 || (mode == 3 && p == 1)) v ^= xor;
                    c |= v << p;
                }
                px[y * 16 + x] = (short)c;
            }
        }
        spriteCache[(sheet, s, mode)] = px;
        return px;
    }
}

/// <summary>Draws the surface and nest views the way the original's f_03518 / f_02c21 do (render_view.py).</summary>
public static class MapRenderer
{
    const int SURFACE = 0x0180, OCC = 0x6180;
    static readonly int[] PHER = { 0xd09f, 0xe09f, 0xe89f, 0xf09f };   // T:07BE 0..3; 4 is the red trail (4DA7:0)

    public static int Width(int view) => view <= 1 ? 128 : 64;

    /// <summary>The scent map value under surface cell (a, b) for scent mode `mode` (T:07BE numbering: 0 alarm,
    /// 1 black nest marker, 2 black trail, 3 red nest marker, 4 red trail); each map cell covers 2 x 2 cells.</summary>
    public static int Scent(State st, int mode, int a, int b) =>
        mode == 4 ? st.U8(0x4da7, (a >> 1) * 32 + (b >> 1)) : st.Pher(PHER[mode], a >> 1, b >> 1);

    /// <summary>The Map window's content T:07C8 (4..8: black nest marker, black trail, red nest marker, red
    /// trail, alarm) as a T:07BE scent mode.</summary>
    public static int ScentMode(int content) => content == 8 ? 0 : content - 3;

    public const int Height = 64;

    /// <summary>
    /// The 16-colour driver's row converter for the 128-wide map image (G:38B8 → 0x31260): colour byte c is four
    /// plane bytes at DS:1F9E + 4c (0..15 solid, 0x10.. dither patterns). A cell is 4 x 4 px; two neighbouring cells
    /// share each plane byte, the even one taking its high nibble and the odd one its low nibble, a bit per pixel
    /// from the left; scanlines 1 and 3 take the byte rotated left by one. Returns the palette index (0..15) of
    /// pixel (px, py) of cell column `a` in colour `c`.
    /// </summary>
    public static int DitherIndex(byte[] flat, int c, int a, int px, int py)
    {
        int index = 0, bit = (a & 1) == 0 ? 7 - px : 3 - px;
        for (int p = 0; p < 4; p++)
        {
            int t = flat[0x55b3 * 16 + 0x1f9e + 4 * c + p];
            if ((py & 1) != 0) t = ((t << 1) | (t >> 7)) & 0xff;
            index |= ((t >> bit) & 1) << p;
        }
        return index;
    }

    /// <summary>f_02c21: the recolour mode, the low byte of the word at DS:1A58 + ((fg &amp; 0xFFBF) >> 6).</summary>
    static int ColourMode(State st, int fg) => st.U8(DS, 0x1a58 + (((fg & 0xffbf) >> 6) & 0xffff));

    /// <summary>f_03518 for map cell (a, b): (background tile, foreground id or 0). Foreground ids as the
    /// original: surface ant 0x100 + type, nest ant 0x200 + type, the yellow ant 0x380 / 0x300 + type + G:049A +
    /// (its heading, or G:0502 for a queen's cocoon), a queen's tail 0x388 / 0x308 + type + heading + G:049A.</summary>
    public static (int bg, int fg) Cell(State st, int view, int a, int b)
    {
        int bg, o, @base, yellow, tail;
        if (view <= 1)
        {
            bg = 0;
            int mode = st.U16(T, 0x7be);
            if (mode < 5)
            {
                int v = mode == 4 ? st.U8(0x4da7, (a >> 1) * 32 + (b >> 1)) : st.Pher(PHER[mode], a >> 1, b >> 1);
                if (v > 0x10) bg = (((v >> 4) & 0x1f) - 0x10) & 0xff;
            }
            if (bg == 0) bg = st.Grid(SURFACE, a, b);
            o = st.Grid(OCC, a, b);
            @base = 0x100;
            yellow = 0x380;
            tail = 0x388;
        }
        else
        {
            var n = view == 2 ? NestGrid.BLACK : NestGrid.RED;
            bg = (st.Grid(n.Dirt, a, b) - 0x70) & 0xff;
            o = st.Grid(n.Cells, a, b);
            @base = 0x200;
            yellow = 0x300;
            tail = 0x308;
        }
        if (o == 0) return (bg, 0);
        int extra = st.U16(G, 0x49a), t = st.U16(G, 0x4c2), h = st.U16(G, 0x496);
        int fg;
        if (o == 0xff) fg = extra + t + yellow + (t < 8 ? st.U16(G, 0x502) : h);
        else if (o == 0xfe) fg = extra + h + t + tail;
        else fg = o + @base;
        return (bg, fg & 0xffff);
    }

    /// <summary>The Map window's colour for cell (a, b) of `view` (f_6efd6, the 16-colour path; render_view.map_cells):
    /// surface (f_6e892): occupant ? T:046E[occupant >> 3] : T:030E[tile] (house T:039E); nests (f_6ec6e): the
    /// yellow ant 1, red ants 3, black ants 15, else T:04A6[dirt >> 2].</summary>
    public static int MapColour(State st, int view, int a, int b)
    {
        if (view <= 1)
        {
            int o = st.Grid(OCC, a, b);
            if (o != 0) return st.U8(T, 0x46e + (o >> 3)) & 15;
            int ground = st.U16(G, 0xf24) == 1 ? 0x39e : 0x30e;
            return st.U8(T, ground + st.Grid(SURFACE, a, b)) & 15;
        }
        var n = view == 2 ? NestGrid.BLACK : NestGrid.RED;
        int c = st.Grid(n.Cells, a, b);
        if (c == 0) return st.U8(T, 0x4a6 + (st.Grid(n.Dirt, a, b) >> 2)) & 15;
        return c >= 0xfe ? 1 : (c & 0x80) != 0 ? 3 : 15;
    }

    /// <summary>Draw cells [a0, a1) x [b0, b1) of `view` into an ARGB buffer (16 px per cell, x = a, y = b).</summary>
    public static void Render(State st, MapArt art, int view, int a0, int b0, int a1, int b1, uint[] dst, int stride)
    {
        bool house = view <= 1 && st.U16(G, 0xf24) != 0;
        for (int a = a0; a < a1; a++)
            for (int b = b0; b < b1; b++)
            {
                var (bg, fg) = Cell(st, view, a, b);
                var tile = art.Tile(house, bg);
                short[] spr = null;
                if (fg != 0)
                {
                    int f = fg - (fg >= 0x380 ? 0x280 : fg >= 0x200 ? 0x200 : 0x100);
                    int sheet = 0x200 <= fg && fg < 0x380 ? 13 : 14;                 // f_02b43: nests 13, surface 14
                    spr = art.Sprite(sheet, f & 0x7f, ColourMode(st, f));
                }
                int ox = (a - a0) * 16, oy = (b - b0) * 16;
                for (int y = 0; y < 16; y++)
                {
                    int row = (oy + y) * stride + ox;
                    for (int x = 0; x < 16; x++)
                    {
                        int k = y * 16 + x;
                        int c = spr != null && spr[k] >= 0 ? spr[k] : tile[k];
                        dst[row + x] = art.Palette[c & 15];
                    }
                }
            }
    }
}
