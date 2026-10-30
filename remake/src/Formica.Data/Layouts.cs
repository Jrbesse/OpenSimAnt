using System.Buffers.Binary;

namespace Formica.Data;

/// <summary>An item of a window layout (tools/layouts.py): absolute rectangle, id, type, text / bitmap; Flags the word at
/// +24 (text alignment (Flags &amp; 0x180) >> 7; bit 2 picks AltScheme), Scheme / AltScheme the colour schemes at +26 /
/// +27 (UiArt.Schemes), Style the byte at +28 (a frame's thickness, a text's font).</summary>
public sealed record LayoutItem(int Id, (int left, int top, int right, int bottom) Rect, (int x, int y) Pos, (int w, int h) Size,
                                int Parent, int State, int Type, string Kind, int Param, string Text, int Bitmap, int[] Bitmaps,
                                int Flags = 0, int Scheme = 0, int AltScheme = 0, int Style = 0, int[] Attach = null,
                                int[] Refs = null)
{
    // Attach: each edge's mode (+18, left / top / right / bottom); Refs: the item each edge refers to (+10, window << 8 |
    // item index; for mode 5 an edge of the window's requested rectangle). UiArt.Relayout (f_25595) uses both.
    // Id is the right edge's reference (+14): usually the item itself, which is why some "ids" repeat (window 22's list
    // has 0x1607, its frame's); the original names an item window << 8 | its index.
    /// <summary>f_220e4: the colour scheme the item is drawn in.</summary>
    public int ColourScheme => (Flags & 4) != 0 ? AltScheme : Scheme;
}

/// <summary>A window layout: its screen rectangle (640 x 480) and items.</summary>
public sealed record WindowLayout(int Id, (int left, int top, int right, int bottom) Rect, List<LayoutItem> Items)
{
    /// <summary>The header's flags at +1C (u16): the decorations f_2271d draws (UiArt.DrawDecorations).</summary>
    public int Flags { get; init; }

    /// <summary>The header's +10..+16: the rectangle the window was last opened at (f_21336), which mode-5 edges use.</summary>
    public (int l, int t, int r, int b) Requested { get; init; }
}

/// <summary>Window / dialog layouts (HCEGANT type 0; tools/layouts.py, FILE_FORMATS "Window layouts").
/// Layout n is window n. Header (0x2C bytes): +00 rect, +0C u16 item count, +0E u16 resource size, +2C item
/// table (4 bytes per item: the offset into the resource). Item record: +00 rect (absolute), +08 x, y, +0C width,
/// height (the edges' offsets), +10 4 x u16 the edges' references (window &lt;&lt; 8 | item index), +18 4 x u16 the
/// edges' modes (UiArt.Relayout), +20 u8 state, +21 u8 type, +22 u16
/// record length, +28 the type's parameter (bitmap id, style), strings NUL-terminated at +2A (types 5, 9, 0x0C)
/// or +2E (0x10..0x12). Resources 128 / 129 / 131 are UI tables, not windows.</summary>
public static class Layouts
{
    static readonly Dictionary<int, string> Types = new()
    {
        [0x00] = "box", [0x01] = "hotspot", [0x02] = "frame", [0x03] = "hotspot", [0x04] = "list", [0x05] = "text",
        [0x06] = "picture", [0x07] = "icon", [0x08] = "vscroll", [0x09] = "text", [0x0a] = "hotspot", [0x0b] = "hotspot",
        [0x0c] = "text_button", [0x0d] = "toggle_picture", [0x0e] = "hotspot", [0x0f] = "frame3d", [0x10] = "field",
        [0x11] = "filled_text", [0x12] = "caption", [0x13] = "frame", [0x14] = "frame", [0x15] = "frame", [0x16] = "frame",
    };

    static short S(ReadOnlySpan<byte> b, int o) => BinaryPrimitives.ReadInt16LittleEndian(b[o..]);

    static int U(ReadOnlySpan<byte> b, int o) => BinaryPrimitives.ReadUInt16LittleEndian(b[o..]);

    static string CStr(ReadOnlySpan<byte> b, int o)
    {
        int e = o;
        while (e < b.Length && b[e] != 0) e++;
        return string.Concat(b[o..e].ToArray().Select(c => (char)c));
    }

    public static LayoutItem DecodeItem(ReadOnlySpan<byte> b)
    {
        int type = b[0x21], length = U(b, 0x22);
        int param = b.Length >= 0x2a ? U(b, 0x28) : 0;
        string text = null;
        if ((type == 0x05 || type == 0x09 || type == 0x0c) && b.Length > 0x2a) text = CStr(b, 0x2a);
        else if (type >= 0x10 && type <= 0x12 && b.Length > 0x2e) text = CStr(b, 0x2e);
        return new LayoutItem(U(b, 0x14), (S(b, 0), S(b, 2), S(b, 4), S(b, 6)), (S(b, 8), S(b, 10)), (S(b, 12), S(b, 14)),
                              U(b, 0x10), b[0x20], type, Types.GetValueOrDefault(type, $"type{type:x2}"), param, text,
                              type == 0x06 ? param : -1, type == 0x0d ? new[] { U(b, 0x26), U(b, 0x28) } : null,
                              b.Length > 0x25 ? U(b, 0x24) : 0, b.Length > 0x26 ? b[0x26] : 0, b.Length > 0x27 ? b[0x27] : 0,
                              b.Length > 0x28 ? b[0x28] : 0, new int[] { S(b, 0x18), S(b, 0x1a), S(b, 0x1c), S(b, 0x1e) },
                              new int[] { U(b, 0x10), U(b, 0x12), U(b, 0x14), U(b, 0x16) });
    }

    public static WindowLayout Decode(int id, byte[] data)
    {
        var b = data.AsSpan();
        int n = U(b, 0x0c);
        var items = new List<LayoutItem>(n);
        for (int i = 0; i < n; i++)
        {
            int o = U(b, 0x2c + 4 * i);
            int length = U(b, o + 0x22);
            items.Add(DecodeItem(b.Slice(o, Math.Min(length, b.Length - o))));
        }
        return new WindowLayout(id, (S(b, 0), S(b, 2), S(b, 4), S(b, 6)), items)
        {
            Flags = b[0x1c] | b[0x1d] << 8,
            Requested = (S(b, 0x10), S(b, 0x12), S(b, 0x14), S(b, 0x16)),
        };
    }

    /// <summary>Every window layout (ids below 128) of the player's HCEGANT archive.</summary>
    public static Dictionary<int, WindowLayout> All(OriginalFiles files) =>
        files.Hcegant.Where(r => r.Type == 0 && r.Id < 128 && r.Data.Length >= 0x2c)
             .ToDictionary(r => r.Id, r => Decode(r.Id, r.Data));
}
