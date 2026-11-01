using System.IO.Compression;
using OpenSimAnt.Data;

namespace OpenSimAnt.Replay;

/// <summary>`OpenSimAnt.Replay --export-pack [game dir] [out.zip]`: writes the player's original files as a pack, in the
/// clean pack's layout (OriginalFiles(byte[])). For checking the pack loader only: the result holds original data,
/// so it stays in remake/build (git-ignored) and is never shipped. A game run on it (`--clean --pack=out.zip`) must
/// look and sound exactly like one on the original files.</summary>
public static class ExportPack
{
    public static int Run(string gameDir, string outFile)
    {
        var f = new OriginalFiles(gameDir);
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outFile))!);
        if (File.Exists(outFile)) File.Delete(outFile);
        int n = 0;
        using (var zip = ZipFile.Open(outFile, ZipArchiveMode.Create))
        {
            void Add(string name, byte[] data)
            {
                using var s = zip.CreateEntry(name, CompressionLevel.Optimal).Open();
                s.Write(data);
                n++;
            }
            foreach (var (name, list) in new[] { ("HCEGANT", f.Hcegant), ("SHARED", f.Shared), ("SOUND", f.Sound) })
                foreach (var r in list) Add($"{name}/{r.Type}/{r.Id}.bin", r.Data);
            foreach (var (k, v) in f.FontFiles) Add($"FONT/{k}.bin", v);
            foreach (var a in EmbeddedAssets.All) Add($"EXE/{a.Name}.bin", EmbeddedAssets.Extract(f.Exe, a));
            Add("EXE/version.txt", System.Text.Encoding.UTF8.GetBytes(f.VersionLine));
            Add("EXE/engine_strings.json", System.Text.Encoding.UTF8.GetBytes(
                System.Text.Json.JsonSerializer.Serialize(f.EngineStrings, new System.Text.Json.JsonSerializerOptions { WriteIndented = true })));
        }
        Console.WriteLine($"{n} files -> {outFile} (original data: for testing only, never ship it)");
        // the pack must load back to the same resources
        var p = new OriginalFiles(File.ReadAllBytes(outFile));
        bool same = p.Hcegant.Count == f.Hcegant.Count && p.Shared.Count == f.Shared.Count && p.Sound.Count == f.Sound.Count
                    && p.Flat.AsSpan().SequenceEqual(f.Flat) && p.VersionLine == f.VersionLine
                    && p.EngineStrings.Count == f.EngineStrings.Count && f.EngineStrings.All(kv => p.EngineString(kv.Key) == kv.Value);
        Console.WriteLine(same ? "reloaded: the same resources and image" : "reloaded: DIFFERENT");
        return same ? 0 : 1;
    }
}
