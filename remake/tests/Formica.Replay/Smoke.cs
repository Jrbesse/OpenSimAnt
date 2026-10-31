using System.IO.Compression;
using Formica.Data;
using Formica.Sim;

namespace Formica.Replay;

/// <summary>`Formica.Replay --smoke [game dir] [ticks] [out dir]`: checks the State built from SIMANT.EXE against
/// tools/re/build/flat.bin, plays a Quick Game from a fixed seed for a while and writes PNGs of the views.</summary>
public static class Smoke
{
    public static int Run(string gameDir, int ticks, string outDir)
    {
        var s = new GameSession(gameDir);
        var flatPath = TracePaths.FlatImage();
        if (File.Exists(flatPath))
        {
            var refFlat = File.ReadAllBytes(flatPath);
            int diffs = 0;
            for (int i = State.Lo; i < State.Hi; i++)
                if (refFlat[i] != s.Files.Exe[i]) diffs++;
            Console.WriteLine($"state image from SIMANT.EXE vs flat.bin: {diffs} bytes differ");
        }
        // the game tables in source must equal the executable's bytes (they are generated from its image)
        foreach (var t in GameTables.All)
        {
            int at = t.Seg * 16 + t.Off, nd = 0;
            for (int i = 0; i < t.Bytes.Length; i++) if (t.Bytes[i] != s.Files.Exe[at + i]) nd++;
            if (nd > 0) Console.WriteLine($"game table {t.Name}: {nd} of {t.Bytes.Length} bytes differ from SIMANT.EXE");
        }
        var layouts = Layouts.All(s.Files);
        Console.WriteLine($"window layouts: {layouts.Count}, items {layouts.Values.Sum(w => w.Items.Count)}; window 1: rect {layouts.GetValueOrDefault(1)?.Rect}, "
                          + string.Join(", ", layouts.GetValueOrDefault(1)?.Items.Take(6).Select(i => $"{i.Id:x4} {i.Kind} {i.Text}") ?? Array.Empty<string>()));
        var bootPath = Path.Combine(TracePaths.DefaultDir(), "..", "boot_state.bin");
        if (File.Exists(bootPath))
        {
            // a game from the static image + boot defaults must evolve like one from the real booted memory
            var boot = File.ReadAllBytes(bootPath);
            foreach (int mode in new[] { 1, 2 })
            {
                var x = new GameSession(gameDir);
                x.NewGame(mode, 0x4321, boot);
                s.NewGame(mode, 0x4321);
                var x0 = (byte[])x.St.Mem.Clone();
                var s0 = (byte[])s.St.Mem.Clone();
                int bad = -1;
                for (int t = 0; t < ticks && bad < 0; t++)
                {
                    if (t == 100) { x.WalkTo(1, 70, 25); s.WalkTo(1, 70, 25); }
                    x.Step();
                    s.Step();
                    // the simulation's own memory: T, SIM up to the end of the red trail map, G below the UI data
                    for (int i = 0; i < State.Size && bad < 0; i++)
                    {
                        int lin = State.Lo + i;
                        bool sim = lin < 0x4da70 + 0x800 || (lin >= Seg.G * 16 && lin < Seg.G * 16 + 0x1200);
                        // bytes that already differed at the start and neither side changed: relocated segment
                        // words (the emulator loads at segment 0x100) and other start-up differences left alone
                        bool still = x0[i] != s0[i] && x.St.Mem[i] == x0[i] && s.St.Mem[i] == s0[i];
                        if (sim && x.St.Mem[i] != s.St.Mem[i] && !still) bad = i;
                    }
                    if (bad >= 0) Console.WriteLine($"mode {mode}: boot vs image differ at tick {t}: {Replayer.Describe(bad)} boot {x.St.Mem[bad]:x2} image {s.St.Mem[bad]:x2}");
                }
                if (bad < 0) Console.WriteLine($"mode {mode}: {ticks} ticks from the boot state and from SIMANT.EXE + boot defaults match");
            }
        }
        foreach (int mode in new[] { 1, 2 })
        {
            s.NewGame(mode, 0x1234);
            var (v0, a0, b0) = s.Yellow;
            Console.WriteLine($"mode {mode}: yellow ant at view {v0} ({a0}, {b0}); black {s.St.U16(Seg.G, 0x330)} red {s.St.U16(Seg.G, 0x350)}");
            int t = 0;
            for (; t < ticks && !s.Over; t++)
            {
                if (t == 50) s.WalkTo(1, 70, 25);
                s.Step();
            }
            var (v, a, b) = s.Yellow;
            Console.WriteLine($"  after {t} ticks: yellow at view {v} ({a}, {b}), black {s.St.U16(Seg.G, 0x330)} red {s.St.U16(Seg.G, 0x350)}, "
                              + $"surface ants {s.St.U16(Seg.G, 0xd6a)}, spider {s.St.U16(Seg.G, 0xf0c)} at ({s.St.S16(Seg.G, 0xf12) >> 4}, {s.St.S16(Seg.G, 0xf34) >> 4}), over {s.Over}, effects {s.Hooks.Effects.Count}");
            Directory.CreateDirectory(outDir);
            for (int view = 1; view <= 3; view++)
            {
                int w = MapRenderer.Width(view) * 16, h = MapRenderer.Height * 16;
                var px = new uint[w * h];
                MapRenderer.Render(s.St, s.Art, view, 0, 0, MapRenderer.Width(view), MapRenderer.Height, px, w);
                if (view == 1) SpiderRenderer.Draw(s.St, s.Files, s.Art, px, w, h, 0, 0, SpiderRenderer.FangJitter(s.St));
                WritePng(Path.Combine(outDir, $"mode{mode}_view{view}.png"), w, h, px);
                if (view == 1 && s.St.U16(Seg.G, 0xf0c) != 0)
                {
                    // a 256 x 192 crop around the spider, to check its drawing
                    int cx = Math.Clamp(s.St.S16(Seg.G, 0xf12) - 128, 0, w - 256), cy = Math.Clamp(s.St.S16(Seg.G, 0xf34) - 96, 0, h - 192);
                    var crop = new uint[256 * 192];
                    for (int y = 0; y < 192; y++)
                        Array.Copy(px, (cy + y) * w + cx, crop, y * 256, 256);
                    WritePng(Path.Combine(outDir, $"mode{mode}_spider.png"), 256, 192, crop);
                }
            }
        }
        Console.WriteLine("wrote " + outDir);
        return 0;
    }

    public static void WritePng(string path, int w, int h, uint[] argb)
    {
        var raw = new byte[h * (w * 4 + 1)];
        int k = 0;
        for (int y = 0; y < h; y++)
        {
            raw[k++] = 0;
            for (int x = 0; x < w; x++)
            {
                uint c = argb[y * w + x];
                raw[k++] = (byte)(c >> 16);
                raw[k++] = (byte)(c >> 8);
                raw[k++] = (byte)c;
                raw[k++] = (byte)(c >> 24);
            }
        }
        using var f = File.Create(path);
        f.Write(new byte[] { 0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a });
        var ihdr = new byte[13];
        System.Buffers.Binary.BinaryPrimitives.WriteInt32BigEndian(ihdr, w);
        System.Buffers.Binary.BinaryPrimitives.WriteInt32BigEndian(ihdr.AsSpan(4), h);
        ihdr[8] = 8;
        ihdr[9] = 6;
        Chunk(f, "IHDR", ihdr);
        var ms = new MemoryStream();
        using (var z = new ZLibStream(ms, CompressionLevel.Fastest, true)) z.Write(raw);
        Chunk(f, "IDAT", ms.ToArray());
        Chunk(f, "IEND", Array.Empty<byte>());
    }

    static void Chunk(Stream f, string tag, byte[] data)
    {
        var len = new byte[4];
        System.Buffers.Binary.BinaryPrimitives.WriteInt32BigEndian(len, data.Length);
        f.Write(len);
        var td = System.Text.Encoding.ASCII.GetBytes(tag).Concat(data).ToArray();
        f.Write(td);
        var crc = new byte[4];
        System.Buffers.Binary.BinaryPrimitives.WriteUInt32BigEndian(crc, Crc32(td));
        f.Write(crc);
    }

    static uint Crc32(byte[] d)
    {
        uint c = 0xffffffff;
        foreach (byte b in d)
        {
            c ^= b;
            for (int k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xedb88320 ^ (c >> 1) : c >> 1;
        }
        return ~c;
    }
}
