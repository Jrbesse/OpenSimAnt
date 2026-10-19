using Formica.Data;

namespace Formica.Replay;

/// <summary>--songs [game dir] [out dir]: render every song (SOUND type 18 entries) and every sound effect
/// through the original's driver and an OPL2 (Formica.Data.SoundMixer) to 16-bit WAV files, for listening. They
/// are made from the player's own files: never commit them (the default folder is the git-ignored
/// remake/build/songs).</summary>
public static class Songs
{
    const int Rate = 44100;

    public static int Run(string gameDir, string outDir)
    {
        var files = new OriginalFiles(gameDir);
        Directory.CreateDirectory(outDir);
        var ids = files.Sound.Where(r => r.Type == 18).Select(r => r.Id).OrderBy(x => x).ToList();
        foreach (int id in ids)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var mix = new SoundMixer(files);
            if (!mix.Driver.StartSong(id)) { Console.WriteLine($"{id}: no song"); continue; }
            var pcm = Render(mix, () => mix.Driver.Playing, 600);
            WriteWav(Path.Combine(outDir, $"song_{id}.wav"), pcm, Rate);
            Console.WriteLine($"{id}: {pcm.Length / (double)Rate:F1} s, rendered in {sw.ElapsedMilliseconds} ms");
        }
        for (int n = 0; n < SoundBank.EffectCount; n++)
        {
            var mix = new SoundMixer(files);
            mix.Driver.Effect(n);
            WriteWav(Path.Combine(outDir, $"fx_{n:00}.wav"), Render(mix, () => mix.SamplesPlaying, 20), Rate);
        }
        Console.WriteLine($"wrote {ids.Count} songs and {SoundBank.EffectCount} effects to {Path.GetFullPath(outDir)}");
        return 0;
    }

    /// <summary>Render while `busy` (at most `maxSeconds`), then two more seconds for the release tails.</summary>
    static short[] Render(SoundMixer mix, Func<bool> busy, int maxSeconds)
    {
        var all = new List<short>();
        var buf = new short[Rate / 10];
        for (int i = 0; i < maxSeconds * 10 && busy(); i++)
        {
            mix.Render(buf, Rate);
            all.AddRange(buf);
        }
        for (int i = 0; i < 20; i++)
        {
            mix.Render(buf, Rate);
            all.AddRange(buf);
        }
        return all.ToArray();
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
