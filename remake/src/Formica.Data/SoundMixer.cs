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
    readonly Dictionary<int, sbyte[]> pcmCache = new();

    struct Voice
    {
        public sbyte[] Pcm;
        public int Pos, Step, Attenuation;     // Pos and Step: 8.8 fixed point, in samples
        public bool On;
    }
    readonly Voice[] voices = new Voice[2];

    int fastTicks, wait = 1;
    double fastPhase, oplPhase;
    short oplPrev, oplCur;
    int dac;

    /// <summary>Linear gain of the 8-bit sample voices against the OPL2's 16-bit output (the Sound Blaster
    /// mixes its DAC and FM at the card; not measured).</summary>
    public int SampleGain = 96;

    public SoundMixer(OriginalFiles files)
    {
        this.files = files;
        Driver = new SoundDriver(files, opl.Write, this);
    }

    // ------------------------------------------------------------------------------- the sample device

    public void Start(int voice, SoundBank.Sample sample, int step, int attenuation)
    {
        if (!pcmCache.TryGetValue(sample.SoundId, out var pcm))
            pcmCache[sample.SoundId] = pcm = files.SoundEffect(sample.SoundId) ?? Array.Empty<sbyte>();
        voices[voice] = new Voice { Pcm = pcm, Step = step, Attenuation = attenuation, On = pcm.Length > 0 };
    }

    public void Stop(int voice) => voices[voice].On = false;

    public bool Playing(int voice) => voices[voice].On;

    /// <summary>One tick of the driver's 5575.6 Hz interrupt: the sample voices move on (the level is taken as
    /// a right shift by the attenuation, a guess: the mixer is not decoded), and every 16th tick is a music
    /// tick that counts the sequencer's wait down (DS:6B42) and steps it at 0.</summary>
    void FastTick()
    {
        int sum = 0;
        for (int v = 0; v < voices.Length; v++)
        {
            ref var vo = ref voices[v];
            if (!vo.On) continue;
            int i = vo.Pos >> 8;
            if (i >= vo.Pcm.Length) { vo.On = false; continue; }
            sum += vo.Pcm[i] >> vo.Attenuation;
            vo.Pos += vo.Step;
        }
        dac = sum;
        if (++fastTicks < 16) return;
        fastTicks = 0;
        if (--wait > 0) return;
        int w = Driver.Step();
        wait = w == 0xffff ? 1 : w;
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
                FastTick();
            }
            oplPhase += oplStep;
            while (oplPhase >= 1)
            {
                oplPhase -= 1;
                oplPrev = oplCur;
                oplCur = opl.Next();
            }
            double fm = oplPrev + (oplCur - oplPrev) * oplPhase;
            buffer[n] = (short)Math.Clamp(fm + dac * SampleGain, short.MinValue, short.MaxValue);
        }
    }

    /// <summary>Is anything still sounding from the sample voices (for offline renders).</summary>
    public bool SamplesPlaying => voices.Any(v => v.On);
}
