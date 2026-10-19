namespace Formica.Data;

/// <summary>The pull-down menus (SIM_NOTES "Keys and menu commands"): SHARED type 6 id 0, loaded by 82e5:0039
/// into DS:6054 with its offsets made into pointers. Little-endian u32 offsets from the resource's start: a table
/// up to a 0 entry whose entry 0 lists the menu titles and entry m + 1 menu m's items, each list up to a 0 entry
/// and each string NUL-terminated. Titles: File, Window, View, Options, Speed. An item's first byte is its state:
/// 0x20 plain, 0x10 checked (font 1 draws it as a ►, f_2033e sets it), 0x80 disabled; "---" is a separator.
/// Item n of menu m posts the command 0xFD00 + 16 m + n + 1 (f_6e26d). The bar and the menus are drawn in the
/// text-cell font 1 (8 px wide, DS:3DDE; 10 px tall, DS:3DDC).</summary>
public sealed class Menus
{
    public const int CellW = 8, CellH = 10, Font = 1;
    public const byte Plain = 0x20, Checked = 0x10, Disabled = 0x80;

    public readonly string[] Titles;
    /// <summary>Items per menu, each with its state byte first.</summary>
    public readonly char[][][] Items;
    /// <summary>The titles' left edges (DS:46A8) and widths in cells (DS:46BC).</summary>
    public readonly int[] TitleX, TitleLen;

    public Menus(OriginalFiles files, int screenW = 640)
    {
        var d = files.Shared.FirstOrDefault(r => r.Type == 6 && r.Id == 0)?.Data;
        var lists = new List<List<char[]>>();
        if (d != null)
            for (int t = 0; U32(d, t) != 0; t += 4)
            {
                var list = new List<char[]>();
                for (int p = (int)U32(d, t); U32(d, p) != 0; p += 4)
                {
                    int s = (int)U32(d, p), e = Array.IndexOf(d, (byte)0, s);
                    list.Add(d.AsSpan(s, (e < 0 ? d.Length : e) - s).ToArray().Select(b => (char)b).ToArray());
                }
                lists.Add(list);
            }
        Titles = lists.Count > 0 ? lists[0].Select(c => new string(c)).ToArray() : Array.Empty<string>();
        Items = lists.Skip(1).Select(l => l.ToArray()).ToArray();
        // f_2fd2_0663: the gap between titles is (screen cells - all titles' cells) / (n - 1), kept within 1..3
        int n = Titles.Length;
        TitleX = new int[n];
        TitleLen = Titles.Select(t => t.Length).ToArray();
        int gap = n > 1 ? Math.Clamp((screenW / CellW - TitleLen.Sum()) / (n - 1), 1, 3) : 1;
        for (int i = 1; i < n; i++) TitleX[i] = TitleX[i - 1] + (TitleLen[i - 1] + gap) * CellW;
    }

    static uint U32(byte[] d, int o) => o + 4 <= d.Length ? BitConverter.ToUInt32(d, o) : 0;

    /// <summary>The bar's height: the font's height + 3 (the bar rectangle at DS:3935); titles at y = 1.</summary>
    public int BarHeight => CellH + 3;

    /// <summary>The title rectangle of menu m (82e5:0184): x .. x + 8 * len, y 1 .. 1 + height + 1.</summary>
    public (int l, int t, int r, int b) TitleRect(int m) => (TitleX[m], 1, TitleX[m] + CellW * TitleLen[m], CellH + 2);

    public int TitleAt(int x, int y)
    {
        for (int m = 0; m < Titles.Length; m++)
        {
            var (l, t, r, b) = TitleRect(m);
            if (x >= l && x < r && y >= 0 && y < b) return m;
        }
        return -1;
    }

    public static bool IsSeparator(char[] item) => item.Length > 1 && item[1] == '-';

    /// <summary>The longest item of menu m, in cells (the item width of f_6d9a4).</summary>
    public int Width(int m) => Items[m].Max(i => i.Length);

    /// <summary>f_6d9a4 opened from the bar: the box is centred under the title ((title cells - width) / 2 cells
    /// from its left, at least 0) and starts at y = font height + 5; it is width cells + 16 px wide and n rows +
    /// 6 px tall, kept on screen. The visible frame is that box less 8 px on each side and 3 px top and bottom;
    /// items start at its top-left, one font line each. Returns the frame and the first item's top-left.</summary>
    public ((int l, int t, int r, int b) frame, int x, int y) Box(int m, int screenW = 640, int screenH = 480)
    {
        int w = Width(m), n = Items[m].Length;
        int l = Math.Max(0, ((TitleLen[m] - w) >> 1) * CellW + TitleX[m]);
        int t = CellH + 5;
        int r = CellW * w + l + 16;
        if (r > screenW) { l -= r - screenW; r = screenW; }
        int b = CellH * n + t + 6;
        if (b > screenH - 5) { t -= b - screenH + 5; b = screenH - 5; }
        return ((l + CellW, t + 3, r - CellW, b - 3), l + CellW, t + 3);
    }

    /// <summary>The item row under (x, y) in menu m's box, or -1.</summary>
    public int ItemAt(int m, int x, int y)
    {
        var (f, ix, iy) = Box(m);
        if (x < f.l || x >= f.r || y < iy) return -1;
        int row = (y - iy) / CellH;
        return row < Items[m].Length ? row : -1;
    }

    /// <summary>The text f_6d9a4 draws for an item: a separator becomes " ----- " across the box (width - 2
    /// dashes between two spaces).</summary>
    public string Text(int m, int i)
    {
        var item = Items[m][i];
        int w = Width(m);
        return IsSeparator(item) ? " " + new string('-', Math.Max(0, w - 2)) + " " : new string(item);
    }

    public static int Command(int m, int i) => 0xfd00 + 16 * m + i + 1;

    /// <summary>f_2033e(id, state): the state byte of the item the command id names (menu id >> 4, item id &amp; 0xF).</summary>
    public void SetState(int id, byte state)
    {
        int m = (id >> 4) & 0xf, i = id & 0xf;
        if (m < Items.Length && i < Items[m].Length) Items[m][i][0] = (char)state;
    }

    /// <summary>f_1fe55(id, text): replace an item's text (the Pause item becomes " Unpause" / " Pause").</summary>
    public void SetText(int id, string text)
    {
        int m = (id >> 4) & 0xf, i = (id & 0xf) - 1;
        if (m < Items.Length && i >= 0 && i < Items[m].Length) Items[m][i] = text.ToCharArray();
    }
}
