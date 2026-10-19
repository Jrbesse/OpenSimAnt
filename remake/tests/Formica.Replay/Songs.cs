using Formica.Data;

namespace Formica.Replay;

/// <summary>--songs [game dir] [out dir]: render every song effect (SOUND type 18 entries, else the type-20 ids)
/// with Formica.Data.Music to 16-bit WAV files, for listening. They are made from the player's own files: never
/// commit them (the default folder is the git-ignored remake/build/songs).</summary>
public static class Songs
{
    public static int Run(string gameDir, string outDir)
    {
        var files = new OriginalFiles(gameDir);
        Directory.CreateDirectory(outDir);
        var ids = files.Sound.Where(r => r.Type == 18).Select(r => r.Id)
            .Concat(files.Sound.Where(r => r.Type == 20).Select(r => r.Id)).Distinct().OrderBy(x => x).ToList();
        int bad = 0;
        foreach (int id in ids)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var pcm = Music.Render(files, id);
            if (pcm == null) { Console.WriteLine($"{id}: no song"); bad++; continue; }
            string path = Path.Combine(outDir, $"song_{id}.wav");
            WriteWav(path, pcm, Music.SampleRate);
            var (song, tr) = Music.Entry(files, id).Value;
            Console.WriteLine($"{id}: song {song} transpose {tr}, {pcm.Length / (double)Music.SampleRate:F1} s, rendered in {sw.ElapsedMilliseconds} ms");
        }
        Console.WriteLine($"wrote {ids.Count - bad} songs to {Path.GetFullPath(outDir)}");
        return 0;
    }

    static void WriteWav(string path, short[] pcm, int rate)
    {
        using var w = new BinaryWriter(File.Create(path));
        w.Write("RIFF"u8);
        w.Write(36 + pcm.Length * 2);
        w.Write("WAVEfmt "u8);
        w.Write(16);
        w.Write((short)1);
        w.Write((short)1);
        w.Write(rate);
        w.Write(rate * 2);
        w.Write((short)2);
        w.Write((short)16);
        w.Write("data"u8);
        w.Write(pcm.Length * 2);
        foreach (short s in pcm) w.Write(s);
    }
}
