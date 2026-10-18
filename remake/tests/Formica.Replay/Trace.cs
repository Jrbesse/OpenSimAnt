using System.IO.Compression;
using System.Text.Json;

namespace Formica.Replay;

/// <summary>One recorded call of the Python reference (tools/ref/record_traces.py).</summary>
public sealed class TraceRecord
{
    public int Index;
    public string Func;
    public JsonElement Args;
    public string Player;
    public long Clock, ClockAfter;
    public int Kbd, KbdAfter;
    public JsonElement? Ret;
    public string Raise;
    public byte[] Before, After;
}

/// <summary>Reads a .trace file: b"SATR1", then records (json header, zlib(before ^ previous after),
/// zlib(after ^ before)).</summary>
public static class TraceReader
{
    public static IEnumerable<TraceRecord> Read(string path)
    {
        using var f = File.OpenRead(path);
        using var r = new BinaryReader(f);
        var magic = r.ReadBytes(5);
        if (System.Text.Encoding.ASCII.GetString(magic) != "SATR1") throw new InvalidDataException("not a trace: " + path);
        var prev = new byte[Formica.Sim.State.Size];
        int index = 0;
        while (f.Position < f.Length)
        {
            int hl = r.ReadInt32();
            var head = JsonDocument.Parse(r.ReadBytes(hl)).RootElement;
            var before = Inflate(r.ReadBytes(r.ReadInt32()));
            Xor(before, prev);
            var after = Inflate(r.ReadBytes(r.ReadInt32()));
            Xor(after, before);
            prev = after;
            var rec = new TraceRecord
            {
                Index = index++,
                Func = head.GetProperty("func").GetString(),
                Args = head.GetProperty("args"),
                Player = head.TryGetProperty("player", out var p) && p.ValueKind == JsonValueKind.String ? p.GetString() : null,
                Clock = head.GetProperty("clock").GetInt64(),
                ClockAfter = head.GetProperty("clock_after").GetInt64(),
                Kbd = head.GetProperty("kbd").GetInt32(),
                KbdAfter = head.GetProperty("kbd_after").GetInt32(),
                Ret = head.TryGetProperty("ret", out var ret) ? ret : null,
                Raise = head.TryGetProperty("raise", out var ra) ? ra.GetString() : null,
                Before = before,
                After = after,
            };
            yield return rec;
        }
    }

    static byte[] Inflate(byte[] data)
    {
        using var z = new ZLibStream(new MemoryStream(data), CompressionMode.Decompress);
        var buf = new byte[Formica.Sim.State.Size];
        int n = 0;
        while (n < buf.Length)
        {
            int k = z.Read(buf, n, buf.Length - n);
            if (k == 0) break;
            n += k;
        }
        if (n != buf.Length) throw new InvalidDataException("short memory block");
        return buf;
    }

    static void Xor(byte[] a, byte[] b)
    {
        var va = System.Runtime.InteropServices.MemoryMarshal.Cast<byte, ulong>(a.AsSpan(0, a.Length & ~7));
        var vb = System.Runtime.InteropServices.MemoryMarshal.Cast<byte, ulong>(b.AsSpan(0, b.Length & ~7));
        for (int i = 0; i < va.Length; i++) va[i] ^= vb[i];
        for (int i = a.Length & ~7; i < a.Length; i++) a[i] ^= b[i];
    }
}
