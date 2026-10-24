namespace Formica.Data;

/// <summary>The SimAntipedia (window 5; SIM_NOTES "The SimAntipedia"). The Map toolbar's "Ant Info Window"
/// (0x115 → f_78db9) opens it on card 128; f_78808 draws a card into item 0x502, f_790f0 handles clicks.
/// A card is SHARED type 17 (card_layout, big-endian): u16 height, u16 width (200 x 320), then records
/// 'PICT' (u16 bitmap id, Rect top / left / bottom / right, u16 n, n x (Rect, s16 value)) and 'TEXT' (Rect,
/// u16 n, n x u16 text id). Its caption is type 19 (card_name, '_' → ' '). Texts are type 10 with type 21
/// style runs (Mac 'styl': u16 count, 20-byte ScrpSTElements); a run with face 0x0100 (bold) is drawn in
/// font 5, the rest in font 2, and a bold word found in the glossary table (4EE5:0520) is a link to a pop-up
/// definition. A PICT hotspot's value: 1 = PREVIOUS (the history), > 1 = go to that card, ≤ 0 = pop up
/// text -value. All coordinates here are screen coordinates for an item whose top-left is the origin.</summary>
public sealed class Antipedia
{
    public const int TopCard = 0x80, NormalFont = 2, LinkFont = 5;

    public readonly record struct Hotspot(int L, int T, int R, int B, int Value)
    {
        public bool Contains(int x, int y) => x >= L && x < R && y >= T && y < B;     // f_20205
    }

    /// <summary>A picture (Pict ≥ 0) or a run of text in a font, top-left at (X, Y).</summary>
    public readonly record struct Element(int Pict, int X, int Y, int Font, string Text);

    public sealed class Card
    {
        public int Id;
        public string Name;
        public readonly List<Element> Draw = new();
        public readonly List<Hotspot> PictLinks = new();         // 4EE5:0280, count DS:8C22
        public readonly List<Hotspot> TextLinks = new();         // 4EE5:0000, count DS:8C24
    }

    readonly OriginalFiles files;
    readonly Func<int, BitmapFont> font;
    readonly List<(int id, string name)> glossary = new();

    // f_790f0's history: a ring of 16 cards DS:2E04 indexed by the low 4 bits of DS:2E24; DS:2E26 the card shown
    readonly int[] history = new int[16];
    int index;
    public int Current { get; private set; } = TopCard;

    public Antipedia(OriginalFiles files, Func<int, BitmapFont> font)
    {
        this.files = files;
        this.font = font;
        // the glossary: 0x22-byte entries (u16 text id, a 32-byte upper-case name) up to an id of 0
        for (int p = 0x4ee5 * 16 + 0x520; p + 0x22 <= files.Flat.Length; p += 0x22)
        {
            int id = files.Flat[p] | files.Flat[p + 1] << 8;
            if (id == 0) break;
            int end = Array.IndexOf(files.Flat, (byte)0, p + 2);
            glossary.Add((id, System.Text.Encoding.ASCII.GetString(files.Flat, p + 2, Math.Min(end, p + 0x22) - p - 2)));
        }
    }

    /// <summary>f_78db9 when the window was not open: the top card, the history reset to it.</summary>
    public void Open()
    {
        Current = history[0] = TopCard;
        index = 0;
    }

    byte[] Res(int type, int id) => files.Shared.FirstOrDefault(r => r.Type == type && r.Id == id)?.Data;

    static int Be(byte[] d, int o) => (short)(d[o] << 8 | d[o + 1]);

    /// <summary>f_78808: lay out card `id` in the item whose top-left is (ox, oy). Null if there is no such card
    /// ("Card Resource not found").</summary>
    public Card Build(int id, int ox, int oy)
    {
        var d = Res(17, id);
        if (d == null) return null;
        var card = new Card { Id = id };
        var nm = Res(19, id);
        if (nm != null)
        {
            int end = Array.IndexOf(nm, (byte)0);
            card.Name = OriginalFiles.MacText(nm.AsSpan(0, end < 0 ? nm.Length : end)).Replace('_', ' ');
        }
        int o = 4;
        while (o + 4 <= d.Length)
        {
            string tag = System.Text.Encoding.ASCII.GetString(d, o, 4);
            o += 4;
            if (tag[0] == 'P')
            {
                int pict = Be(d, o), t = Be(d, o + 2), l = Be(d, o + 4), n = Be(d, o + 10);
                o += 12;
                card.Draw.Add(new Element(pict, ox + l, oy + t, 0, null));       // f_259de at the rect's top-left
                for (int k = 0; k < n; k++, o += 10)
                    card.PictLinks.Add(new Hotspot(ox + Be(d, o + 2), oy + Be(d, o), ox + Be(d, o + 6), oy + Be(d, o + 4), Be(d, o + 8)));
            }
            else if (tag[0] == 'T')
            {
                int t = Be(d, o), l = Be(d, o + 2), b = Be(d, o + 4), r = Be(d, o + 6), n = Be(d, o + 8);
                o += 10;
                for (int k = 0; k < n; k++, o += 2)
                {
                    // the original adds the item's origin to the rect once per frame (all cards have one)
                    l += ox; t += oy; r += ox; b += oy;
                    var (text, runs) = Text(Be(d, o));
                    if (text == null) continue;
                    card.TextLinks.Clear();                                     // each call resets DS:8C24
                    Layout(text, runs, l, t, r, b, card.Draw, card.TextLinks);
                }
            }
            else break;                                                         // "Unknown Resource."
        }
        return card;
    }

    /// <summary>A text (type 10) and its style runs (type 21: start, face) with f_78808's clean-up: each NUL in
    /// the first size - 4 bytes is removed with the bytes after it that are below 0x20 or above 0x7F (signed
    /// char ≤ 0x1F), and the runs after it move back.</summary>
    (byte[] text, List<(int start, int face)> runs) Text(int id)
    {
        var src = Res(10, id);
        if (src == null) return (null, null);
        var text = (byte[])src.Clone();
        var runs = new List<(int start, int face)>();
        var s = Res(21, id);
        if (s != null)
            for (int k = 0, n = Be(s, 0); k < n; k++)
            {
                int e = 2 + k * 20;
                runs.Add((s[e] << 24 | s[e + 1] << 16 | s[e + 2] << 8 | s[e + 3], (ushort)Be(s, e + 10)));
            }
        int size = text.Length;
        while (true)
        {
            int p = Array.IndexOf(text, (byte)0, 0, Math.Max(0, Math.Min(size - 4, text.Length)));   // _fmemchr
            if (p < 0) break;
            int q = p;
            while ((sbyte)text[q] <= 0x1f && q < size - 4) q++;
            Array.Copy(text, q, text, p, Math.Min(size - q, text.Length - q));
            for (int k = 0; k < runs.Count; k++)
                if (runs[k].start >= q) runs[k] = (runs[k].start - (q - p), runs[k].face);
            size -= q - p;
            if (q == p) break;
        }
        int len = Array.IndexOf(text, (byte)0, 0, size);                        // f_78232 stops at strlen
        return (text.AsSpan(0, len < 0 ? size : len).ToArray(), runs);
    }

    int FontFor(List<(int start, int face)> runs, int k) => k < runs.Count && runs[k].face == 0x100 ? LinkFont : NormalFont;

    int Advance(int f, byte c) => font(f)?.Advance(c) ?? 0;

    /// <summary>A font's height as the original counts it (f_24dbb: an Apple FONT's fRectHeight - 1).</summary>
    int LineHeight(int f) => font(f) is { } bf ? (bf.IsMac ? bf.Height - 1 : bf.Height) : 0;

    static byte At(byte[] t, int i) => i < t.Length ? t[i] : (byte)0;

    /// <summary>f_78232 / f_78641's break rule for character c at i: -1 none, else the break position.</summary>
    static int BreakAt(byte c, int i) => c switch
    {
        0 or 10 or 13 or 0x20 or 0x28 or 0x5b or 0x7b => i,                      // before (a line end, a space, ( [ {)
        0x21 or 0x29 or 0x2c or 0x2d or 0x2e or 0x3f or 0x5d or 0x7d => i + 1,   // after ! ) , - . ? ] }
        _ => -1,
    };

    /// <summary>f_78232(text, styl, rect, first line 0, font 2, font 5, record): draws line by line from
    /// (left + 1, top + 4), breaking at the last break point that fits; each style run is drawn when the next
    /// one starts, and a bold run's words (leading spaces dropped, upper-cased) that name a glossary entry
    /// become a link (when `links` is given).</summary>
    public void Layout(byte[] text, List<(int start, int face)> runs, int l, int t, int r, int b, List<Element> draw, List<Hotspot> links)
    {
        int lh = Math.Max(LineHeight(NormalFont), LineHeight(LinkFont));
        if (lh <= 0) return;
        int width = r - l, lines = (b - t) / lh, y = t + 4, run = 0, i = 0;
        int cur = FontFor(runs, 0);
        for (int line = 0; i < text.Length && line < lines; line++, y += lh)
        {
            int x = 0, brk = 0, segStart = i, segX = l + 1;
            bool end = false;
            while (x < width && !end)
            {
                if (run + 1 < runs.Count && runs[run + 1].start <= i)
                {
                    run++;
                    if (i - segStart > 0)
                    {
                        string seg = Str(text, segStart, i);
                        draw.Add(new Element(-1, segX, y, cur, seg));
                        if (links != null && runs[run - 1].face == 0x100)
                        {
                            int id = Glossary(seg);
                            if (id != 0) links.Add(new Hotspot(segX, y, l + x, y + lh, id));
                        }
                    }
                    segX = l + x + 1;
                    cur = FontFor(runs, run);
                    segStart = i;
                }
                byte c = At(text, i);
                x += Advance(cur, c);
                if (x < width)
                {
                    if (c is 0 or 10 or 13) end = true;
                    int k = BreakAt(c, i);
                    if (k >= 0) brk = k;
                }
                i++;
            }
            int from = segStart, to = i;
            if (brk != 0)
            {
                to = brk;
                if (brk < segStart) from = brk;                                  // the break was in a run already drawn
            }
            if (to - from > 0) draw.Add(new Element(-1, segX, y, cur, Str(text, from, to)));
            while (At(text, to) == ' ') to++;
            if (At(text, to) is 10 or 13) to++;
            i = to;
        }
    }

    /// <summary>f_78641: the height of a text laid out `width` wide (lines x the line height).</summary>
    public int Measure(byte[] text, List<(int start, int face)> runs, int width)
    {
        int lh = Math.Max(LineHeight(NormalFont), LineHeight(LinkFont));
        int lines = 0, run = 0, i = 0, cur = FontFor(runs, 0);
        while (i < text.Length)
        {
            int x = 0, brk = 0;
            bool end = false;
            while (x < width && !end)
            {
                if (run + 1 < runs.Count && runs[run + 1].start <= i) cur = FontFor(runs, ++run);
                byte c = At(text, i);
                x += Advance(cur, c);
                if (x < width)
                {
                    if (c is 0 or 10 or 13) end = true;
                    int k = BreakAt(c, i);
                    if (k >= 0) brk = k;
                }
                i++;
            }
            if (brk != 0) i = brk;
            while (At(text, i) == ' ') i++;
            if (At(text, i) is 10 or 13) i++;
            lines++;
        }
        return lines * lh;
    }

    static string Str(byte[] t, int from, int to)
    {
        var sb = new System.Text.StringBuilder(to - from);
        for (int k = from; k < to; k++) sb.Append((char)At(t, k));             // the font's own codes (Mac Roman)
        return sb.ToString();
    }

    int Glossary(string seg)
    {
        string w = seg.TrimStart(' ');
        var sb = new System.Text.StringBuilder(w.Length);
        foreach (char ch in w) sb.Append(ch is >= 'a' and <= 'z' ? (char)(ch - 0x20) : ch);
        w = sb.ToString();
        foreach (var (id, name) in glossary)
            if (name == w) return id;
        return 0;                                                               // "ERROR: Cannot file text rez"
    }

    /// <summary>f_790f0: a click at (x, y) on the card. Returns a pop-up text id (a definition shown while the
    /// button is held) or 0; a link to a card or PREVIOUS changes Current.</summary>
    public int Click(Card card, int x, int y)
    {
        if (card == null) return 0;
        foreach (var h in card.PictLinks)
        {
            if (!h.Contains(x, y)) continue;
            if (h.Value == 1)
            {
                int prev = history[(index - 1) & 15];
                if (prev != 0)
                {
                    Current = prev;
                    index--;
                }
            }
            else if (h.Value > 0)
            {
                index++;
                history[index & 15] = h.Value;
                Current = h.Value;
                history[(index + 1) & 15] = 0;
            }
            else return -h.Value;
            return 0;
        }
        foreach (var h in card.TextLinks)
            if (h.Contains(x, y)) return h.Value;
        return 0;
    }

    /// <summary>The hotspot that was hit (for placing the pop-up), or null.</summary>
    public static Hotspot? HitLink(Card card, int x, int y) =>
        card?.PictLinks.Concat(card.TextLinks).Cast<Hotspot?>().FirstOrDefault(h => h.Value.Contains(x, y));

    /// <summary>f_78e1c: a pop-up with text `id` for a link centred at x spanning top..bottom, inside the item
    /// (il, it, ir, ib): half the item wide, centred on the link and kept 4 px inside, below the link or
    /// above it when it would not fit. Returns the box (white, 1-px frame) and the text.</summary>
    public (int l, int t, int r, int b, List<Element> text)? Popup(int id, int x, int top, int bottom, int il, int it, int ir, int ib)
    {
        var (txt, runs) = Text(id);
        if (txt == null) return null;
        int a = (ir - il) / 2, h = ib - it;
        int left = x - a / 2, right = x + a / 2;                                 // the original's x is item-relative
        if (left < il + 4) { right = il + 4 + a; left = il + 4; }
        if (ir - 4 < right) { left = ir - 4 - a; right = ir - 4; }
        int height = Measure(txt, runs, a) + 5;
        int ptop = top - it, pbot = bottom - it, tt, tb;
        if (h - 10 < height + pbot + 4) { tt = it - height + ptop - 4; tb = it + ptop - 4; }
        else { tt = it + pbot + 4; tb = tt + height; }
        int bl = left - 4, br = right + 4, bt = tt - 4, bb = tb + 4;
        if (bt < it) { bt = it; bb = it + height + 8; }
        else if (ib < bb) { bb = ib; bt = ib - height - 8; }
        var draw = new List<Element>();
        Layout(txt, runs, left, tt, right, tb, draw, null);
        return (bl, bt, br, bb, draw);
    }
}
