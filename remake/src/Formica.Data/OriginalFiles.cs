using System.Buffers.Binary;
using Formica.Sim;

namespace Formica.Data;

/// <summary>One resource of a SimAnt archive (NAME.NDX + NAME.DAT).</summary>
public sealed record Resource(int Index, int Id, int Type, int Flags, byte[] Data);

/// <summary>The resource archive reader (tools/simres.py).
/// NDX: u16 record count, 18 zero bytes, then count x { u32 offset; u16 id; u8 type; u8 flags }.
/// DAT: u32 magic 0x12345678, u16 count, u32 end, 4 zero bytes, then records { u32 magic; u16 0; u32 size;
/// data }; NDX offsets are relative to 0x0E. flags bit 0: compressed = u16 uncompressed size + Okumura LZSS
/// (N=4096, F=18, threshold 2, ring pre-filled with spaces).</summary>
public static class ResourceArchive
{
    const uint MAGIC = 0x12345678;

    public static byte[] Lzss(ReadOnlySpan<byte> src, int outLen)
    {
        const int N = 4096, F = 18, T = 2;
        var ring = new byte[N];
        Array.Fill(ring, (byte)0x20);
        int r = N - F;
        var res = new byte[outLen];
        int n = 0, i = 0, flags = 0;
        while (i < src.Length && n < outLen)
        {
            flags >>= 1;
            if ((flags & 0x100) == 0)
            {
                flags = src[i++] | 0xff00;
                if (i >= src.Length) break;
            }
            if ((flags & 1) != 0)
            {
                byte c = src[i++];
                res[n++] = c;
                ring[r] = c;
                r = (r + 1) & (N - 1);
            }
            else
            {
                if (i + 1 >= src.Length) break;
                int a = src[i], b = src[i + 1];
                i += 2;
                int p = a | ((b & 0xf0) << 4);
                for (int k = 0; k < (b & 0x0f) + T + 1 && n < outLen; k++)
                {
                    byte c = ring[(p + k) & (N - 1)];
                    res[n++] = c;
                    ring[r] = c;
                    r = (r + 1) & (N - 1);
                }
            }
        }
        return n == outLen ? res : res[..n];
    }

    /// <summary>Read NAME.NDX / NAME.DAT in `dir` (either case on disk).</summary>
    public static List<Resource> Read(string dir, string name)
    {
        var ndx = File.ReadAllBytes(OriginalFiles.FilePath(dir, name + ".NDX"));
        var dat = File.ReadAllBytes(OriginalFiles.FilePath(dir, name + ".DAT"));
        int count = BinaryPrimitives.ReadUInt16LittleEndian(ndx);
        var res = new List<Resource>(count);
        for (int i = 0; i < count; i++)
        {
            int e = 0x14 + i * 8;
            int off = (int)BinaryPrimitives.ReadUInt32LittleEndian(ndx.AsSpan(e));
            int id = BinaryPrimitives.ReadUInt16LittleEndian(ndx.AsSpan(e + 4));
            int type = ndx[e + 6], flags = ndx[e + 7];
            int h = 0x0e + off;
            if (BinaryPrimitives.ReadUInt32LittleEndian(dat.AsSpan(h)) != MAGIC)
                throw new InvalidDataException($"{name}.DAT: bad record {i}");
            int size = (int)BinaryPrimitives.ReadUInt32LittleEndian(dat.AsSpan(h + 6));
            var raw = dat.AsSpan(h + 10, size);
            byte[] data = (flags & 1) != 0
                ? Lzss(raw[2..], BinaryPrimitives.ReadUInt16LittleEndian(raw))
                : raw.ToArray();
            res.Add(new Resource(i, id, type, flags, data));
        }
        return res;
    }
}

/// <summary>The starting memory of the simulation, built from the player's own SIMANT.EXE the way
/// tools/re/mz.py does: the MZ load image, with the resident overlay sections (flags bit 0) copied to their
/// segments. The State covers flat 0x3d570..0x62000 of it (the constant tables, grids, globals and DGROUP).</summary>
public static class ExeImage
{
    /// <summary>The flat image 0..0x62000 (code and data as loaded, overlays resident).</summary>
    public static byte[] BuildFlat(byte[] exe)
    {
        int hdr = BinaryPrimitives.ReadUInt16LittleEndian(exe.AsSpan(8)) * 16;
        int imgEnd = (BinaryPrimitives.ReadUInt16LittleEndian(exe.AsSpan(4)) - 1) * 512
                     + BinaryPrimitives.ReadUInt16LittleEndian(exe.AsSpan(2));
        var img = exe.AsSpan(hdr, imgEnd - hdr);
        var mem = new byte[0x62000];
        img.CopyTo(mem);
        // the overlay manager's section table: records found by their ff ff markers
        for (int q = 0x2db40; q < 0x2dd70; q++)
        {
            if (img[q] != 0xff || img[q + 1] != 0xff) continue;
            int fsize = BinaryPrimitives.ReadUInt16LittleEndian(img[(q + 4)..]) * 16;
            int seg = BinaryPrimitives.ReadUInt16LittleEndian(img[(q - 12)..]);
            int pos = BinaryPrimitives.ReadUInt16LittleEndian(img[(q - 8)..]);
            int fl = img[q - 5];
            int nrel = BinaryPrimitives.ReadUInt16LittleEndian(img[(q - 2)..]);
            if ((fl & 1) == 0) continue;
            int fpos = pos * 16;
            int dstart = fpos + (nrel * 4 + 15) / 16 * 16;
            int n = Math.Min(fsize, exe.Length - dstart);
            int dst = seg * 16;
            if (dst + n > mem.Length) n = mem.Length - dst;
            exe.AsSpan(dstart, n).CopyTo(mem.AsSpan(dst));
        }
        return mem;
    }

    /// <summary>A fresh simulation State from the executable's data.</summary>
    public static State NewState(byte[] flat)
    {
        if (State.Touch != null)                                // analysis: a fresh image, nothing written yet
            for (int i = 0; i < State.Size; i++) State.Touch[i] &= 2;
        return new(flat.AsSpan(State.Lo, State.Size).ToArray());
    }

    /// <summary>Analysis (`--deps`): ORs the bytes read from the image (State.Touch bit 2) into the bitmap file
    /// `path` (one byte per State byte, 1 = read).</summary>
    public static void MergeDeps(string path)
    {
        if (State.Touch == null) return;
        var acc = File.Exists(path) ? File.ReadAllBytes(path) : new byte[State.Size];
        for (int i = 0; i < State.Size; i++) if ((State.Touch[i] & 2) != 0) acc[i] = 1;
        File.WriteAllBytes(path, acc);
    }
}

/// <summary>The game's files: the player's own copy of the original (SIMANT.EXE, the HCEGANT / SHARED / SOUND archives,
/// FONT1..FONT4), or the clean pack (ROADMAP A1: a zip holding the same resources in the same formats, so everything
/// that reads them works the same with either). Read resources through <see cref="Get"/> / <see cref="Of"/>, which
/// log what the game asks for (<see cref="Requested"/>, the clean pack's work list).</summary>
public sealed class OriginalFiles
{
    /// <summary>The original's folder; null for the clean pack.</summary>
    public readonly string Dir;
    /// <summary>True when the files are the clean pack.</summary>
    public bool IsCleanPack => Dir == null;
    /// <summary>The executable's whole image (for `--exe-state` and to extract the embedded assets); null for the
    /// clean pack.</summary>
    public readonly byte[] Exe;
    /// <summary>What the engine reads of the executable: the game tables and the embedded assets at their addresses,
    /// zeros elsewhere (EmbeddedAssets.BuildImage), so the clean pack can supply the same.</summary>
    public readonly byte[] Flat;
    /// <summary>The version line (Ctrl+Alt+V), the string at DS:0064's far pointer.</summary>
    public readonly string VersionLine;
    public readonly List<Resource> Hcegant;
    public readonly List<Resource> Shared;
    public readonly List<Resource> Sound;
    /// <summary>The files FONT1..FONT4 (fonts 2..5 of the game, Mac FONT resources), by number; missing ones absent.</summary>
    public readonly Dictionary<int, byte[]> FontFiles = new();

    /// <summary>The player's copy of the original in `dir`.</summary>
    public OriginalFiles(string dir)
    {
        Dir = dir;
        Exe = ExeImage.BuildFlat(File.ReadAllBytes(FilePath(dir, "SIMANT.EXE")));
        // FORMICA_FULL_FLAT=1 (debugging): the whole image, as before ROADMAP A1, to compare screens and sound with
        Flat = Environment.GetEnvironmentVariable("FORMICA_FULL_FLAT") != null ? Exe
             : EmbeddedAssets.BuildImage(a => EmbeddedAssets.Extract(Exe, a));
        int p = Seg.DS * 16 + 0x64, at = (Exe[p + 2] | Exe[p + 3] << 8) * 16 + (Exe[p] | Exe[p + 1] << 8), end = at;
        while (end < Exe.Length && Exe[end] != 0) end++;
        VersionLine = System.Text.Encoding.ASCII.GetString(Exe, at, end - at);
        Hcegant = ResourceArchive.Read(dir, "HCEGANT");
        Shared = File.Exists(FilePath(dir, "SHARED.DAT")) ? ResourceArchive.Read(dir, "SHARED") : new List<Resource>();
        Sound = File.Exists(FilePath(dir, "SOUND.DAT")) ? ResourceArchive.Read(dir, "SOUND") : new List<Resource>();
        for (int n = 1; n <= 4; n++)
            if (File.Exists(FilePath(dir, $"FONT{n}"))) FontFiles[n] = File.ReadAllBytes(FilePath(dir, $"FONT{n}"));
    }

    /// <summary>The clean pack: a zip of `HCEGANT/&lt;type&gt;/&lt;id&gt;.bin`, `SHARED/..`, `SOUND/..` (resources in the
    /// original's formats), `FONT/&lt;n&gt;.bin` (n = 1..4), `EXE/&lt;name&gt;.bin` (EmbeddedAssets) and
    /// `EXE/version.txt`. Built by tools/clean_pack/build.py.</summary>
    public OriginalFiles(byte[] packZip)
    {
        Hcegant = new();
        Shared = new();
        Sound = new();
        var embedded = new Dictionary<string, byte[]>();
        string version = "";
        using (var zip = new System.IO.Compression.ZipArchive(new MemoryStream(packZip)))
            foreach (var e in zip.Entries)
            {
                if (e.Length == 0 && e.FullName.EndsWith('/')) continue;
                using var s = e.Open();
                var ms = new MemoryStream();
                s.CopyTo(ms);
                var data = ms.ToArray();
                var parts = e.FullName.Split('/');
                string stem = Path.GetFileNameWithoutExtension(parts[^1]);
                if (parts.Length == 3 && parts[0] is "HCEGANT" or "SHARED" or "SOUND"
                    && int.TryParse(parts[1], out int type) && int.TryParse(stem, out int id))
                {
                    var list = parts[0] == "HCEGANT" ? Hcegant : parts[0] == "SHARED" ? Shared : Sound;
                    list.Add(new Resource(list.Count, id, type, 0, data));
                }
                else if (parts.Length == 2 && parts[0] == "FONT" && int.TryParse(stem, out int n)) FontFiles[n] = data;
                else if (parts.Length == 2 && parts[0] == "EXE" && parts[1] == "version.txt")
                    version = System.Text.Encoding.UTF8.GetString(data).Trim();
                else if (parts.Length == 2 && parts[0] == "EXE") embedded[stem] = data;
            }
        Flat = EmbeddedAssets.BuildImage(a => embedded.GetValueOrDefault(a.Name));
        VersionLine = version;
    }

    /// <summary>Every (archive, type, id) the game has asked for, and every embedded asset's name (archive "EXE").</summary>
    public readonly HashSet<(string archive, int type, int id)> Requested = new();

    List<Resource> Archive(string archive) => archive switch
    {
        "HCEGANT" => Hcegant,
        "SHARED" => Shared,
        "SOUND" => Sound,
        _ => throw new ArgumentException("no archive " + archive),
    };

    /// <summary>A resource, or null if there is none.</summary>
    public Resource Get(string archive, int type, int id)
    {
        lock (Requested) Requested.Add((archive, type, id));
        return Archive(archive).FirstOrDefault(r => r.Type == type && r.Id == id);
    }

    /// <summary>Every resource of one type.</summary>
    public IEnumerable<Resource> Of(string archive, int type)
    {
        foreach (var r in Archive(archive).Where(r => r.Type == type))
        {
            lock (Requested) Requested.Add((archive, type, r.Id));
            yield return r;
        }
    }

    /// <summary>Writes <see cref="Requested"/> as lines "ARCHIVE type id", merged with the lines already in `path`.</summary>
    public void MergeRequested(string path)
    {
        var lines = new SortedSet<string>(File.Exists(path) ? File.ReadAllLines(path) : Array.Empty<string>());
        lock (Requested)
            foreach (var (a, t, i) in Requested) lines.Add($"{a} {t} {i}");
        File.WriteAllLines(path, lines);
    }

    SoundBank bank;
    /// <summary>The sound driver's instruments and effect table (the embedded asset "soundbank").</summary>
    public SoundBank Bank => bank ??= new SoundBank(Flat);

    /// <summary>SOUND sample n (type 5) as signed 8-bit PCM, null if there is none.</summary>
    public sbyte[] SoundEffect(int n)
    {
        var r = Get("SOUND", 5, n);
        return r == null ? null : Sounds.Decode(r.Data);
    }

    /// <summary>A Mac STR# list (type 4; SHARED first, then HCEGANT): u16 BE count, then Pascal strings.
    /// The game's messages (f_71b1a(0, id, ..)) are the lines of STR# id. Null if there is none.</summary>
    public string[] Strings(int id)
    {
        var r = Get("SHARED", 4, id) ?? Get("HCEGANT", 4, id);
        if (r == null) return null;
        var d = r.Data;
        int n = (d[0] << 8) | d[1], p = 2;
        var res = new string[n];
        for (int i = 0; i < n && p < d.Length; i++)
        {
            int len = d[p];
            res[i] = MacText(d.AsSpan(p + 1, Math.Min(len, d.Length - p - 1)));
            p += 1 + len;
        }
        return res;
    }

    /// <summary>A SHARED type-10 text (the SimAntipedia's, the save prompts' 128 / 130), up to its NUL. Null if none.</summary>
    public string Text(int id)
    {
        var r = Get("SHARED", 10, id);
        if (r == null) return null;
        int n = Array.IndexOf(r.Data, (byte)0);
        return MacText(r.Data.AsSpan(0, n < 0 ? r.Data.Length : n));
    }

    /// <summary>Mac Roman text (the characters the game uses; others as '?').</summary>
    public static string MacText(ReadOnlySpan<byte> b)
    {
        var sb = new System.Text.StringBuilder(b.Length);
        foreach (byte c in b)
            sb.Append(c switch
            {
                < 0x80 => c == 13 ? '\n' : (char)c,
                0xd2 or 0xd3 => '"',
                0xd4 or 0xd5 => '\'',
                0xc9 => '…',
                0xd0 => '–',
                0xd1 => '—',
                0xa5 => '•',
                0xa9 => '©',
                0xaa => '™',
                _ => '?',
            });
        return sb.ToString();
    }

    /// <summary>Is there a copy of the game in this folder?</summary>
    public static bool Present(string dir) =>
        File.Exists(FilePath(dir, "SIMANT.EXE")) && File.Exists(FilePath(dir, "HCEGANT.DAT"))
        && File.Exists(FilePath(dir, "HCEGANT.NDX"));

    /// <summary>The path of the game's file `name` in `dir`, whatever the case of its name on disk (copies of DOS games
    /// often have lower-case names, and Linux and some macOS volumes tell the cases apart); the upper-case path if
    /// there is no such file.</summary>
    public static string FilePath(string dir, string name)
    {
        var exact = Path.Combine(dir, name);
        if (File.Exists(exact) || !Directory.Exists(dir)) return exact;
        try
        {
            foreach (var f in Directory.EnumerateFiles(dir))
                if (string.Equals(Path.GetFileName(f), name, StringComparison.OrdinalIgnoreCase)) return f;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException) { }
        return exact;
    }

    /// <summary>An HCEGANT resource that must exist.</summary>
    public Resource Find(int type, int id) => Get("HCEGANT", type, id)
        ?? throw new InvalidDataException($"HCEGANT type {type} id {id} is missing");
}
