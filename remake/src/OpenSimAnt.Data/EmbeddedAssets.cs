using OpenSimAnt.Sim;

namespace OpenSimAnt.Data;

/// <summary>The art, text and sound design the original keeps inside SIMANT.EXE rather than in its archives (ROADMAP A1).
/// Each is a list of memory ranges; its "file" is those ranges' bytes, one after the other. With the original files
/// they come from the executable; the clean pack ships its own files (`exe/&lt;name&gt;.bin`) in the same layout, so the
/// code that reads them stays as it is.</summary>
public static class EmbeddedAssets
{
    public readonly record struct Asset(string Name, (int lo, int hi)[] Ranges, string About)
    {
        public int Size => Ranges.Sum(r => r.hi - r.lo);
    }

    const int DS = Seg.DS * 16, T = Seg.T * 16;

    public static readonly Asset[] All =
    {
        new("soundbank", new[] { (DS + 0x68, DS + 0xa0), (DS + 0x202, DS + 0x9e2), (DS + 0xa82, DS + 0xc42), (DS + 0xd92, DS + 0xee2) },
            "the sound driver's bank (SoundBank): per MIDI channel a priority and an instrument (DS:0068), the FM records "
            + "(16 bytes, DS:0202..) and sample records (0x20 bytes, DS:0342..), the 56 effects (key, priority, instrument, "
            + "velocity; DS:0A82), the 56 instruments (device, record; DS:0D92)"),
        new("balloon", new[] { (DS + 0x1d0a, DS + 0x1dba) },
            "the speech balloon's 8 x 8 pieces, 16 bytes each: corners, edges, inside, two tails (Balloon)"),
        new("spiderlegs", new[] { (T + 0x9e4, T + 0xb14) },
            "the spider's leg and fang coordinates per heading and frame (SpiderLegs reads them from the State's T:09E4)"),
        new("glossary", new[] { (0x4f370, 0x4f6e6) },
            "the SimAntipedia glossary: 0x22-byte entries (u16 text id, a 32-byte upper-case word), ending with id 0"),
    };

    public static Asset Get(string name) => All.First(a => a.Name == name);

    /// <summary>An asset's bytes from a flat image (the executable's).</summary>
    public static byte[] Extract(byte[] flat, Asset a)
    {
        var res = new byte[a.Size];
        int p = 0;
        foreach (var (lo, hi) in a.Ranges)
        {
            Array.Copy(flat, lo, res, p, hi - lo);
            p += hi - lo;
        }
        return res;
    }

    /// <summary>The image the engine reads (OriginalFiles.Flat): zeros, the game tables, and every embedded asset from
    /// `asset(name)` at its ranges. Nothing else of the executable is in it.</summary>
    public static byte[] BuildImage(Func<Asset, byte[]> asset)
    {
        var img = new byte[0x62000];
        foreach (var t in GameTables.All) t.Bytes.CopyTo(img, t.Seg * 16 + t.Off);
        foreach (var a in All)
        {
            var data = asset(a);
            if (data == null) continue;
            if (data.Length != a.Size) throw new InvalidDataException($"embedded asset {a.Name}: {data.Length} bytes, expected {a.Size}");
            int p = 0;
            foreach (var (lo, hi) in a.Ranges)
            {
                Array.Copy(data, p, img, lo, hi - lo);
                p += hi - lo;
            }
        }
        return img;
    }
}
