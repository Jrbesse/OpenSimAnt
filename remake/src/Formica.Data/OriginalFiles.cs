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

    /// <summary>Read NAME.NDX / NAME.DAT (basePath without the extension).</summary>
    public static List<Resource> Read(string basePath)
    {
        var ndx = File.ReadAllBytes(basePath + ".NDX");
        var dat = File.ReadAllBytes(basePath + ".DAT");
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
                throw new InvalidDataException($"{basePath}: bad record {i}");
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
    public static State NewState(byte[] flat) => new(flat.AsSpan(State.Lo, State.Size).ToArray());
}

/// <summary>The player's own copy of the game (SIMANT.EXE, HCEGANT / SHARED / SOUND archives).</summary>
public sealed class OriginalFiles
{
    public readonly string Dir;
    public readonly byte[] Flat;
    public readonly List<Resource> Hcegant;
    public readonly List<Resource> Shared;

    public OriginalFiles(string dir)
    {
        Dir = dir;
        Flat = ExeImage.BuildFlat(File.ReadAllBytes(Path.Combine(dir, "SIMANT.EXE")));
        Hcegant = ResourceArchive.Read(Path.Combine(dir, "HCEGANT"));
        Shared = File.Exists(Path.Combine(dir, "SHARED.DAT")) ? ResourceArchive.Read(Path.Combine(dir, "SHARED")) : new List<Resource>();
        Sound = File.Exists(Path.Combine(dir, "SOUND.DAT")) ? ResourceArchive.Read(Path.Combine(dir, "SOUND")) : new List<Resource>();
    }

    public readonly List<Resource> Sound;

    SoundBank bank;
    /// <summary>The sound driver's instruments and effect table (from SIMANT.EXE).</summary>
    public SoundBank Bank => bank ??= new SoundBank(Flat);

    /// <summary>SOUND sample n (type 5) as signed 8-bit PCM, null if there is none.</summary>
    public sbyte[] SoundEffect(int n)
    {
        var r = Sound.FirstOrDefault(x => x.Type == 5 && x.Id == n);
        return r == null ? null : Sounds.Decode(r.Data);
    }

    /// <summary>A Mac STR# list (type 4; SHARED first, then HCEGANT): u16 BE count, then Pascal strings.
    /// The game's messages (f_71b1a(0, id, ..)) are the lines of STR# id. Null if there is none.</summary>
    public string[] Strings(int id)
    {
        var r = Shared.FirstOrDefault(x => x.Type == 4 && x.Id == id) ?? Hcegant.FirstOrDefault(x => x.Type == 4 && x.Id == id);
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
        File.Exists(Path.Combine(dir, "SIMANT.EXE")) && File.Exists(Path.Combine(dir, "HCEGANT.DAT"))
        && File.Exists(Path.Combine(dir, "HCEGANT.NDX"));

    public Resource Find(int type, int id) => Hcegant.First(r => r.Type == type && r.Id == id);
}
