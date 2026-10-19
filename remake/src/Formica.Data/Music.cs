namespace Formica.Data;

/// <summary>The songs of the SOUND archive and a small synthesizer for them.
/// The game plays a song by effect id (f_00ea1(id) → f_284b3, only with sound hardware DS:1926 and Music T:07AA on):
/// SOUND type 18 id = the effect id is an 18-byte entry: BE u16 the type-20 song, BE u16 (4 for the 10000s, else 1),
/// u16 0, BE s16 a transposition in semitones (11013..11015 play song 0x2B05, CALL2ARM, at +0 / +6 / +12 for
/// recruit 5 / 10 / all), then bytes not decoded (6 + 4 or 8 + 3 voices? 0x40.. flags, 0x08..0x10). Type 20 is a
/// standard MIDI file (format 1, 240 PPQ) without program changes: each track's name says its instrument ("Kick",
/// "Snare", "Bassline", "Strings", "Choir", ...) and every instrument keeps its own channel, as for an AdLib or
/// MT-32 driver whose patches live in the driver (not decoded). The remake renders a song offline with simple
/// two-operator FM voices picked by those names: a stand-in for the original's AdLib sound, not a copy of it.</summary>
public static class Music
{
    public const int SampleRate = 22050;

    public readonly record struct Note(double Start, double Length, int Key, int Velocity, string Instrument);

    /// <summary>The song behind effect `id`: (type-20 id, transposition), or null when there is none.</summary>
    public static (int song, int transpose)? Entry(OriginalFiles files, int id)
    {
        var e = files.Sound.FirstOrDefault(r => r.Type == 18 && r.Id == id)?.Data;
        if (e == null || e.Length < 8) return files.Sound.Any(r => r.Type == 20 && r.Id == id) ? (id, 0) : null;
        return (e[0] << 8 | e[1], (short)(e[6] << 8 | e[7]));
    }

    /// <summary>Effect `id` rendered as 16-bit mono PCM at SampleRate, or null.</summary>
    public static short[] Render(OriginalFiles files, int id)
    {
        if (Entry(files, id) is not { } e) return null;
        var (song, transpose) = e;
        var midi = files.Sound.FirstOrDefault(r => r.Type == 20 && r.Id == song)?.Data;
        if (midi == null) return null;
        var notes = Parse(midi);
        return notes.Count == 0 ? null : Synth(notes, transpose);
    }

    // ------------------------------------------------------------------------------- the MIDI file
    static int Vlq(byte[] d, ref int i)
    {
        int v = 0;
        while (i < d.Length)
        {
            int b = d[i++];
            v = v << 7 | (b & 0x7f);
            if (b < 0x80) break;
        }
        return v;
    }

    static int Be32(byte[] d, int i) => d[i] << 24 | d[i + 1] << 16 | d[i + 2] << 8 | d[i + 3];

    /// <summary>All notes of a standard MIDI file, with times in seconds from its tempo map.</summary>
    public static List<Note> Parse(byte[] d)
    {
        var notes = new List<Note>();
        if (d.Length < 14 || d[0] != 'M' || d[1] != 'T' || d[2] != 'h' || d[3] != 'd') return notes;
        int tracks = d[10] << 8 | d[11], ppq = d[12] << 8 | d[13];
        if (ppq <= 0 || (ppq & 0x8000) != 0) return notes;
        var tempos = new List<(long tick, int usPerQuarter)> { (0, 500000) };
        var raw = new List<(long on, long off, int key, int vel, string name)>();
        int p = 8 + Be32(d, 4);
        for (int t = 0; t < tracks && p + 8 <= d.Length; t++)
        {
            int len = Be32(d, p + 4), i = p + 8, end = Math.Min(d.Length, i + len);
            p = i + len;
            long tick = 0;
            int status = 0;
            string name = "";
            var open = new Dictionary<int, (long tick, int vel)>();
            var trackNotes = new List<(long, long, int, int)>();
            while (i < end)
            {
                tick += Vlq(d, ref i);
                if (i >= end) break;
                int b = d[i];
                if (b == 0xff)
                {
                    int type = d[i + 1];
                    i += 2;
                    int l = Vlq(d, ref i);
                    if (type == 3) name = System.Text.Encoding.ASCII.GetString(d, i, Math.Min(l, end - i)).Trim();
                    if (type == 0x51 && l == 3) tempos.Add((tick, d[i] << 16 | d[i + 1] << 8 | d[i + 2]));
                    i += l;
                    continue;
                }
                if (b is 0xf0 or 0xf7)
                {
                    i++;
                    i += Vlq(d, ref i);
                    continue;
                }
                if ((b & 0x80) != 0) { status = b; i++; }
                int kind = status >> 4, ch = status & 15;
                int a1 = i < end ? d[i] : 0, a2 = i + 1 < end ? d[i + 1] : 0;
                i += kind is 0xc or 0xd ? 1 : 2;
                int key = ch << 8 | a1;
                if (kind == 9 && a2 > 0)
                {
                    if (open.Remove(key, out var o)) trackNotes.Add((o.tick, tick, a1, o.vel));
                    open[key] = (tick, a2);
                }
                else if (kind == 8 || kind == 9)
                {
                    if (open.Remove(key, out var o)) trackNotes.Add((o.tick, tick, a1, o.vel));
                }
            }
            foreach (var (k, o) in open) trackNotes.Add((o.tick, tick, k & 0xff, o.vel));
            foreach (var (on, off, k, v) in trackNotes) raw.Add((on, off, k, v, name));
        }
        tempos.Sort((x, y) => x.tick.CompareTo(y.tick));
        double Seconds(long tick)
        {
            double s = 0;
            long at = 0;
            int us = 500000;
            foreach (var (tt, u) in tempos)
            {
                if (tt >= tick) break;
                s += (tt - at) * (double)us / ppq / 1e6;
                at = tt;
                us = u;
            }
            return s + (tick - at) * (double)us / ppq / 1e6;
        }
        foreach (var (on, off, key, vel, name) in raw)
        {
            double s = Seconds(on);
            notes.Add(new Note(s, Math.Max(0.02, Seconds(off) - s), key, vel, name));
        }
        notes.Sort((x, y) => x.Start.CompareTo(y.Start));
        return notes;
    }

    // ------------------------------------------------------------------------------- the voices
    enum Kind { Bass, Brass, Pad, Pluck, Bell, Kick, Snare, Tom, Clap, Click }

    /// <summary>A two-operator FM patch: carrier : modulator frequency ratio, modulation index at the attack and
    /// at rest, envelope (attack, decay to the sustain level, release, in seconds) and level.</summary>
    readonly record struct Patch(Kind Kind, double Ratio, double IndexHi, double IndexLo, double A, double D, double S,
        double R, double Level);

    static Patch PatchFor(string name)
    {
        string n = name.ToLowerInvariant();
        if (n.Contains("kick")) return new(Kind.Kick, 1, 0, 0, 0.001, 0.16, 0, 0.02, 0.9);
        if (n.Contains("snare")) return new(Kind.Snare, 1, 0, 0, 0.001, 0.13, 0, 0.02, 0.55);
        if (n.Contains("tom")) return new(Kind.Tom, 1, 0, 0, 0.001, 0.22, 0, 0.03, 0.7);
        if (n.Contains("whap")) return new(Kind.Clap, 1, 0, 0, 0.001, 0.09, 0, 0.02, 0.5);
        if (n.Contains("stick")) return new(Kind.Click, 1, 0, 0, 0.001, 0.035, 0, 0.01, 0.45);
        if (n.Contains("agogo")) return new(Kind.Bell, 1.4, 3, 0.5, 0.001, 0.25, 0, 0.05, 0.35);
        if (n.Contains("xylo")) return new(Kind.Bell, 3.5, 2.5, 0.3, 0.001, 0.35, 0, 0.06, 0.4);
        if (n.Contains("bass") || n.Contains("bad") || n.Contains("low horn"))
            return new(Kind.Bass, 1, 3.5, 1.2, 0.004, 0.25, 0.55, 0.06, 0.5);
        if (n.Contains("lead") || n.Contains("melody") || n.Contains("horn"))
            return new(Kind.Brass, 1, 1.0, 2.6, 0.03, 0.2, 0.75, 0.08, 0.38);
        if (n.Contains("string") || n.Contains("choir"))
            return new(Kind.Pad, 1, 1.4, 1.0, 0.12, 0.3, 0.8, 0.25, 0.3);
        if (n.Contains("mandolin") || n.Contains("nylon") || n.Contains("harp") || n.Contains("filler"))
            return new(Kind.Pluck, 1, 2.2, 0.4, 0.002, 0.45, 0.15, 0.1, 0.4);
        return new(Kind.Pluck, 1, 1.5, 0.5, 0.004, 0.3, 0.4, 0.1, 0.35);
    }

    static short[] Synth(List<Note> notes, int transpose)
    {
        double end = notes.Max(n => n.Start + n.Length) + 0.6;
        var mix = new float[(int)(end * SampleRate) + 1];
        uint noise = 0x12345678;
        foreach (var note in notes)
        {
            var pt = PatchFor(note.Instrument);
            int key = note.Key + transpose;
            double f = 440.0 * Math.Pow(2, (key - 69) / 12.0);
            double amp = pt.Level * (0.35 + 0.65 * note.Velocity / 127.0);
            int s0 = (int)(note.Start * SampleRate);
            bool drum = pt.Kind is Kind.Kick or Kind.Snare or Kind.Tom or Kind.Clap or Kind.Click;
            double hold = drum ? 0 : note.Length;
            int n = (int)((hold + pt.R + (drum ? pt.D : 0)) * SampleRate);
            double phase = 0, mphase = 0, lp = 0;
            for (int k = 0; k < n && s0 + k < mix.Length; k++)
            {
                double t = (double)k / SampleRate;
                // the envelope: attack, decay to sustain while the key is held, then release
                double env;
                if (drum) env = Math.Exp(-t / (pt.D / 3));
                else
                {
                    double held = t < pt.A ? t / pt.A : pt.S + (1 - pt.S) * Math.Exp(-(t - pt.A) / (pt.D / 3));
                    env = t <= hold ? held : HeldAt(pt, hold) * Math.Max(0, 1 - (t - hold) / pt.R);
                }
                double v;
                noise ^= noise << 13; noise ^= noise >> 17; noise ^= noise << 5;
                double white = (noise & 0xffff) / 32768.0 - 1;
                switch (pt.Kind)
                {
                    case Kind.Kick:
                        phase += 2 * Math.PI * (45 + 110 * Math.Exp(-t * 30) + (key - 70) * 2) / SampleRate;
                        v = Math.Sin(phase);
                        break;
                    case Kind.Tom:
                        phase += 2 * Math.PI * (f * 0.25 * (1 + Math.Exp(-t * 12))) / SampleRate;
                        v = Math.Sin(phase);
                        break;
                    case Kind.Snare:
                        phase += 2 * Math.PI * 190 / SampleRate;
                        v = 0.45 * Math.Sin(phase) + 0.75 * white * Math.Exp(-t * 14);
                        break;
                    case Kind.Clap:
                        lp += 0.35 * (white - lp);
                        v = (white - lp) * (t < 0.012 || t > 0.02 ? 1 : 0.3);
                        break;
                    case Kind.Click:
                        phase += 2 * Math.PI * (f * 2) / SampleRate;
                        v = 0.6 * Math.Sin(phase) + 0.4 * white;
                        break;
                    default:
                    {
                        // two operators: the modulator's index falls from IndexHi to IndexLo with the envelope's attack
                        double index = pt.IndexLo + (pt.IndexHi - pt.IndexLo) * Math.Exp(-t * (pt.Kind == Kind.Brass ? 25 : 8));
                        double vib = pt.Kind == Kind.Pad ? 1 + 0.004 * Math.Sin(2 * Math.PI * 5.5 * t) : 1;
                        mphase += 2 * Math.PI * f * pt.Ratio * vib / SampleRate;
                        phase += 2 * Math.PI * f * vib / SampleRate;
                        v = Math.Sin(phase + index * Math.Sin(mphase));
                        break;
                    }
                }
                mix[s0 + k] += (float)(v * env * amp);
            }
        }
        // a gentle limiter, then 16 bits
        float peak = mix.Length == 0 ? 1 : Math.Max(1f, mix.Max(Math.Abs));
        var pcm = new short[mix.Length];
        for (int i = 0; i < mix.Length; i++)
            pcm[i] = (short)Math.Clamp(Math.Tanh(mix[i] / peak * 1.6) * 0.8 * 32767, -32768, 32767);
        return pcm;
    }

    static double HeldAt(Patch pt, double t) =>
        t < pt.A ? t / pt.A : pt.S + (1 - pt.S) * Math.Exp(-(t - pt.A) / (pt.D / 3));
}
