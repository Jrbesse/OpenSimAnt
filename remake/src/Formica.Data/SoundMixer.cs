namespace Formica.Data;

/// <summary>
/// The original's sound, rendered: the driver (<see cref="SoundDriver"/>) clocked like its timer handler (a
/// 5575.6 Hz interrupt, a music tick every 16th), writing to an <see cref="Opl2"/>, plus the driver's two sample
/// voices, mixed to 16-bit mono at any output rate. Not thread-safe: call Render and the driver from one thread.
/// </summary>
public sealed class SoundMixer : SoundDriver.ISampleVoices
{
    public readonly SoundDriver Driver;
    readonly Opl2 opl = new();
    readonly OriginalFiles files;

    /// <summary>A sample voice as the handler keeps it (DS:6B4C + 0x14 * v): the position, its fraction (+0E),
    /// the 8.8 step (+0A), the last position played (+06: size - 2), the loop point (+08), the volume table (+0C).</summary>
    struct Voice
    {
        public byte[] Pcm;                      // unsigned 8-bit, as the loader leaves it in memory
        public int Pos, Frac, Step, End, LoopStart;
        public bool Loop, On;
        public byte[] Volume;
    }
    readonly Voice[] voices = new Voice[2];
    readonly Dictionary<int, byte[]> pcmCache = new();
    readonly byte[][] volumeTables = new byte[8][];

    int fastTicks, wait = 0xffff;
    double fastPhase, oplPhase;
    short oplPrev, oplCur;
    int dac = 0x80;

    /// <summary>Gain of the Sound Blaster's 8-bit DAC against the OPL2's 16-bit output (the card mixes the two;
    /// not measured): a full-scale DAC byte is ±128 * SampleGain.</summary>
    public int SampleGain = 160;

    public SoundMixer(OriginalFiles files)
    {
        this.files = files;
        Driver = new SoundDriver(files, opl.Write, this);
    }

    // ------------------------------------------------------------------------------- the sample device

    /// <summary>f_29168: the voice starts at position 0 (the handler moves before it reads, so sample 0 never
    /// plays) and ends after size - 2.</summary>
    public void Start(int voice, SoundBank.Sample sample, int step, int attenuation)
    {
        if (!pcmCache.TryGetValue(sample.SoundId, out var pcm))
        {
            var s = files.SoundEffect(sample.SoundId) ?? Array.Empty<sbyte>();
            pcmCache[sample.SoundId] = pcm = s.Select(x => (byte)(x + 128)).ToArray();
        }
        var vol = volumeTables[attenuation & 7] ??= Driver.Bank.VolumeTable(attenuation).ToArray();
        voices[voice] = new Voice { Pcm = pcm, Step = step & 0xffff, End = pcm.Length - 2, LoopStart = sample.LoopStart, Loop = sample.Loop, Volume = vol, On = pcm.Length > 2 };
    }

    public void Stop(int voice) => voices[voice].On = false;

    public bool Playing(int voice) => voices[voice].On;

    /// <summary>One tick of the driver's 5575.6 Hz handler (0x28BD5): each sample voice adds its step to the
    /// fraction and moves by the carry, then reads its byte through its volume table (0x80 when idle); the two
    /// are averaged into the DAC (DSP command 0x10). A voice that runs past its end loops or stops, and that
    /// tick writes nothing (the other voice does not move either). Every 16th tick (DS:6B3E) is a music tick
    /// that counts the sequencer's wait (DS:6B42) down and steps it at 0.</summary>
    /// <returns>The byte written to the DAC this tick, or -1 when none was.</returns>
    public int Tick()
    {
        int a = Sample(0), b = a < 0 ? -1 : Sample(1), written = -1;
        if (a >= 0 && b >= 0) written = dac = (a + b) >> 1;
        if (++fastTicks < 16) return written;
        fastTicks = 0;
        if (Driver.TakeStarted()) wait = 5;                         // f_284b3: DS:6B42 = 5
        if (--wait != 0) return written;
        wait = Driver.Step();                                       // 0xFFFF when no song plays: idle
        return written;
    }

    /// <summary>The voice's next byte, or -1 when it ran past its end this tick.</summary>
    int Sample(int v)
    {
        ref var vo = ref voices[v];
        if (!vo.On) return 0x80;
        int ax = vo.Frac + vo.Step;
        vo.Frac = ax & 0xff;
        vo.Pos = (vo.Pos + ((ax >> 8) & 0xff)) & 0xffff;
        if (vo.Pos > vo.End)
        {
            if (vo.Loop) vo.Pos = vo.LoopStart;
            else vo.On = false;
            return -1;
        }
        return vo.Volume[vo.Pcm[vo.Pos]];
    }

    /// <summary>Fill `buffer` with mono samples at `rate` Hz.</summary>
    public void Render(Span<short> buffer, int rate)
    {
        double fastStep = SoundBank.MixRate / rate, oplStep = Opl2.SampleRate / rate;
        for (int n = 0; n < buffer.Length; n++)
        {
            fastPhase += fastStep;
            while (fastPhase >= 1)
            {
                fastPhase -= 1;
                Tick();
            }
            oplPhase += oplStep;
            while (oplPhase >= 1)
            {
                oplPhase -= 1;
                oplPrev = oplCur;
                oplCur = opl.Next();
            }
            double fm = oplPrev + (oplCur - oplPrev) * oplPhase;
            buffer[n] = (short)Math.Clamp(fm + (dac - 0x80) * SampleGain, short.MinValue, short.MaxValue);
        }
    }

    /// <summary>Is anything still sounding from the sample voices (for offline renders).</summary>
    public bool SamplesPlaying => voices.Any(v => v.On);
}
