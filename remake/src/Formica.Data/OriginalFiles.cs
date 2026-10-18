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

    public OriginalFiles(string dir)
    {
        Dir = dir;
        Flat = ExeImage.BuildFlat(File.ReadAllBytes(Path.Combine(dir, "SIMANT.EXE")));
        Hcegant = ResourceArchive.Read(Path.Combine(dir, "HCEGANT"));
    }

    /// <summary>Is there a copy of the game in this folder?</summary>
    public static bool Present(string dir) =>
        File.Exists(Path.Combine(dir, "SIMANT.EXE")) && File.Exists(Path.Combine(dir, "HCEGANT.DAT"))
        && File.Exists(Path.Combine(dir, "HCEGANT.NDX"));

    public Resource Find(int type, int id) => Hcegant.First(r => r.Type == type && r.Id == id);
}
