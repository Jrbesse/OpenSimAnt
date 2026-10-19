namespace Formica.Data;

/// <summary>
/// The sound driver's tables, read from the player's SIMANT.EXE (docs/SIM_NOTES.md "The sound driver"):
/// the 56 instruments (DS:0D92, copied to G:0000 by f_278ea), each an FM record (device 2: 16 bytes from
/// DS:0202) or a sample record (device 1: 0x20 bytes from DS:0342), and the sound effects (DS:0A82: key,
/// priority, instrument, velocity per effect, played by f_00ed8 → f_29927 → f_297ac).
/// </summary>
public sealed class SoundBank
{
    const int Ds = 0x55b3 * 16;
    public const int InstrumentCount = 56, EffectCount = 56;
    public const int DeviceSample = 1, DeviceFm = 2;
    /// <summary>The driver's timer: 1193182 / 0xD6 (DS:74A9). Sample voices are mixed at this rate.</summary>
    public const double MixRate = 1193182.0 / 0xD6;
    /// <summary>A music tick is every 16th interrupt (DS:6B3E): 348.5 Hz.</summary>
    public const double TickRate = MixRate / 16;

    public readonly record struct Instrument(int Device, int Record);
    public readonly record struct Effect(int Key, int Priority, int Instrument, int Velocity);
    /// <summary>A sample record: +06 the loop point (- 2), +08 loops, +09 the base octave, +0A a transposition,
    /// +0E the file name, +1D the SOUND id. No record in the table loops.</summary>
    public readonly record struct Sample(int BaseOctave, int Transpose, string Name, int SoundId, bool Loop, int LoopStart);

    readonly byte[] flat;
    public readonly Instrument[] Instruments = new Instrument[InstrumentCount];
    public readonly Effect[] Effects = new Effect[EffectCount];

    public SoundBank(byte[] flat)
    {
        this.flat = flat;
        for (int i = 0; i < InstrumentCount; i++)
            Instruments[i] = new Instrument(U16(0xd92 + 6 * i), U16(0xd92 + 6 * i + 2));   // far pointer: DS offset (segment DS)
        for (int n = 0; n < EffectCount; n++)
        {
            int a = 0xa82 + 8 * n;
            Effects[n] = new Effect(U16(a), U16(a + 2), U16(a + 4), U16(a + 6));
        }
    }

    int U16(int ds) => flat[Ds + ds] | flat[Ds + ds + 1] << 8;
    short S16(int ds) => (short)U16(ds);

    /// <summary>The FM record of an instrument: bytes 0..10 the OPL2 registers in f_2815a's order, s16 +0x0B an
    /// octave shift, s16 +0x0D a velocity offset.</summary>
    public byte[] Fm(int instrument) => Instruments[instrument].Device == DeviceFm
        ? flat.AsSpan(Ds + Instruments[instrument].Record, 16).ToArray() : null;

    public Sample? SampleOf(int instrument)
    {
        var ins = Instruments[instrument];
        if (ins.Device != DeviceSample) return null;
        int r = ins.Record;
        var name = System.Text.Encoding.ASCII.GetString(flat, Ds + r + 0x0e, 15).Split('\0')[0];
        return new Sample(flat[Ds + r + 9], S16(r + 0x0a), name, U16(r + 0x1d), flat[Ds + r + 8] != 0, U16(r + 6) + 2);
    }

    /// <summary>The mixer's volume table for an attenuation 0..7 (DS:6B9E → DS:6CA3 + 256 * a): unsigned 8-bit
    /// sample in, 128 + (in - 128) * (8 - a) / 8 out.</summary>
    public ReadOnlySpan<byte> VolumeTable(int attenuation) => flat.AsSpan(Ds + U16(0x6b9e) + 256 * (attenuation & 7), 256);

    /// <summary>f_29263's pitch: the 8.8 step for `key` on a sample (DS:74C2[k % 12], shifted by k / 12 against
    /// the base octave, k = key + transposition). 0x100 plays the sample at MixRate.</summary>
    public int SampleStep(int key, Sample s)
    {
        int k = key + s.Transpose, step = U16(0x74c2 + 2 * (((k % 12) + 12) % 12)), oct = k / 12;
        return oct > s.BaseOctave ? step << (oct - s.BaseOctave) : step >> (s.BaseOctave - oct);
    }
}
