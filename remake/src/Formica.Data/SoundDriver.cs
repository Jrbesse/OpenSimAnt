namespace Formica.Data;

/// <summary>
/// A port of the original's sound driver for the Sound Blaster mode (docs/SIM_NOTES.md "The sound driver"):
/// the MIDI sequencer (f_284b3 / f_28b1f / f_2882f), the voices (G:4A4E, f_29689, f_297ac, f_298a8), the
/// FM device (f_283c5 / f_2815a, f_282b5, f_2839d) as OPL2 register writes, and the sample device as calls on
/// <see cref="ISampleVoices"/>. Checked against the original's register stream (tests: OplTraceTests).
/// One music tick (Step's unit) is 1 / SoundBank.TickRate s.
/// </summary>
public sealed class SoundDriver
{
    /// <summary>The sample device (device 1): the mixer behind f_29263 / f_2933c.</summary>
    public interface ISampleVoices
    {
        /// <summary>Start a sample on hardware voice `voice`: `step` 8.8 fixed point at SoundBank.MixRate,
        /// `attenuation` 0..7 ((0x7F - velocity) >> 4).</summary>
        void Start(int voice, SoundBank.Sample sample, int step, int attenuation);
        void Stop(int voice);
        /// <summary>Still playing (f_29689 frees a sample voice whose sample has ended: DS:6B4E + 0x14 * voice).</summary>
        bool Playing(int voice);
    }

    const int Ds = 0x55b3 * 16;
    const int Channels = 14;                       // MIDI channels 14 and 15 are ignored (f_289d7)
    static readonly int[] EventLength = { 2, 2, 2, 2, 1, 1, 2 };   // DS:75A4 by (status & 0x70) >> 4

    struct Voice { public int Device, Channel, Priority, Instrument, Key, Age; }

    readonly SoundBank bank;
    readonly OriginalFiles files;
    readonly byte[] flat;
    readonly Action<int, int> opl;
    readonly ISampleVoices samples;
    readonly Voice[] voices;
    readonly int[] priority = new int[Channels], instrument = new int[Channels];   // the song header DS:0068

    // the song (f_286f6 / f_28784)
    byte[] midi;
    int playing;                                   // DS:756E: 0 none, 1 playing, 2 ended
    int transpose;                                 // DS:7576
    int tracks, ppq;                               // DS:7566, G:4B2E
    int[] ptr = Array.Empty<int>();                // DS:8DD8: each track's read position
    int[] status = Array.Empty<int>();             // G:4B30: running status (0x2F: ended)
    int[] time = Array.Empty<int>();               // G:4B42: each track's absolute time
    int cur, lastTime, scale;                      // DS:756C, DS:7568, G:4B8A

    /// <summary>Music and effect volumes (DS:7570, DS:7502), 127 in the original; velocity offsets G:4B16, DS:74C0.</summary>
    public int MusicVolume = 127, Volume = 127, FmVelocityOffset, SampleVelocityOffset;

    public SoundDriver(OriginalFiles files, Action<int, int> opl, ISampleVoices samples)
    {
        this.files = files;
        bank = files.Bank;
        flat = files.Flat;
        this.opl = opl;
        this.samples = samples;
        for (int c = 0; c < Channels; c++)
        {
            priority[c] = U16(0x68 + 2 * c);
            instrument[c] = U16(0x68 + 0x1c + 2 * c);
        }
        // Sound Blaster: two sample voices, then FM channels 0..7 (AdLib has FM 1..7); instrument 0xFF, age 0x0F
        voices = new Voice[10];
        for (int v = 0; v < voices.Length; v++)
            voices[v] = new Voice { Device = v < 2 ? SoundBank.DeviceSample : SoundBank.DeviceFm, Channel = v < 2 ? v : v - 2, Instrument = 0xff, Age = 0x0f };
        Init();
    }

    int U16(int ds) => flat[Ds + ds] | flat[Ds + ds + 1] << 8;
    int U8(int ds) => flat[Ds + ds];

    /// <summary>f_28268: the FM init (waveform select off, deep tremolo / vibrato, all keys off).</summary>
    void Init()
    {
        opl(0x01, 0); opl(0x04, 0x80); opl(0x08, 0); opl(0xbd, 0xc0);
        for (int c = 0; c < 8; c++) opl(0xb0 + c, 0);
    }

    public bool Playing => playing == 1;
    public SoundBank Bank => bank;

    bool started;
    /// <summary>A song started since the last call (f_284b3 then sets the handler's wait DS:6B42 to 5).</summary>
    public bool TakeStarted()
    {
        bool s = started;
        started = false;
        return s;
    }

    // ------------------------------------------------------------------------------------------- songs

    /// <summary>f_284b3: stop the song, then start SOUND type 18 entry `id` (its type-20 MIDI, transposed).</summary>
    public bool StartSong(int id)
    {
        Stop();
        var entry = files.Get("SOUND", 18, id)?.Data;
        if (entry == null || entry.Length < 8) return false;
        int song = entry[0] << 8 | entry[1];
        transpose = (short)(entry[6] << 8 | entry[7]);
        midi = files.Get("SOUND", 20, song)?.Data;
        if (midi == null) return false;
        // f_286f6: the header, the track chunks, each track's first delta and status byte
        int hdr = Be32(4);
        tracks = Be16(10);
        ppq = Be16(12);
        ptr = new int[tracks];
        status = new int[tracks];
        time = new int[tracks];
        int at = hdr + 8;
        for (int t = 0; t < tracks; t++)
        {
            ptr[t] = at + 8;
            at += 8 + Be32(at + 4);
        }
        for (int t = 0; t < tracks; t++)
        {
            time[t] = VarLen(t);
            status[t] = midi[ptr[t]];
        }
        // f_28784
        lastTime = 0;
        cur = 0;
        scale = Scale(0x1e0, 500000);
        playing = 1;
        started = true;
        return true;
    }

    int Be16(int i) => midi[i] << 8 | midi[i + 1];
    int Be32(int i) => midi[i] << 24 | midi[i + 1] << 16 | midi[i + 2] << 8 | midi[i + 3];

    /// <summary>f_28675: a variable-length number at track t's position (advances it).</summary>
    int VarLen(int t)
    {
        int p = ptr[t], b = midi[p++], v = b;
        if ((b & 0x80) != 0)
        {
            v &= 0x7f;
            do
            {
                b = midi[p++];
                v = (v << 7) + (b & 0x7f);
            } while ((b & 0x80) != 0);
        }
        ptr[t] = p;
        return v;
    }

    /// <summary>f_287c5: music ticks per MIDI tick, 8.8: ((tempo / 1000) * 1194 / ppq) / 13.</summary>
    static int Scale(int ppq, int tempo) => ppq == 0 ? 0 : (int)((long)tempo / 1000 * 0x4aa / ppq / 13);

    /// <summary>f_28b1f: the events due now; returns the wait in music ticks until the next one (0xFFFF when
    /// no song plays).</summary>
    public int Step()
    {
        if (playing != 1) return 0xffff;
        int wait;
        do
        {
            int b = midi[ptr[cur]];
            if ((b & 0x80) != 0)
            {
                status[cur] = b;
                ptr[cur]++;
            }
            int st = status[cur];
            if (st == 0xf7 || st == 0xf0)
            {
                int len = VarLen(cur);                                  // f_28b13
                ptr[cur] += len;
            }
            else if (st == 0xff)
                Meta();
            else
            {
                ChannelEvent(st);
                ptr[cur] += EventLength[(st & 0x70) >> 4];
            }
            wait = NextEvent();
        } while (wait == 0 && playing != 2);
        return wait != 0 ? wait : 1;
    }

    /// <summary>f_28a65: end of track, tempo, or skipped.</summary>
    void Meta()
    {
        int type = midi[ptr[cur]];
        if (type == 0x2f)
        {
            status[cur] = 0x2f;
            ptr[cur]--;
        }
        else if (type == 0x51)
        {
            ptr[cur] += 2;
            int p = ptr[cur];
            int tempo = midi[p] << 16 | midi[p + 1] << 8 | midi[p + 2];
            ptr[cur] += 3;
            scale = Scale(ppq, tempo);
        }
        else
        {
            ptr[cur]++;
            int len = VarLen(cur);
            ptr[cur] += len;
        }
    }

    /// <summary>f_2882f: the current track's next delta, then the earliest track; the wait to it.</summary>
    int NextEvent()
    {
        if (status[cur] != 0x2f) time[cur] += VarLen(cur);
        else time[cur] = 0x7fffffff;
        int di = 0;
        for (int t = 1; t < tracks; t++)
            if (time[di] > time[t] && status[t] != 0x2f) di = t;
        if (status[di] == 0x2f || time[di] == 0x7fffffff)
        {
            playing = 2;
            return 0;
        }
        int diff = time[di] - lastTime;
        lastTime = time[di];
        cur = di;
        return (diff * scale >> 8) & 0xffff;                            // f_2cddc, f_2ceba: 32 bits, then AX
    }

    /// <summary>f_289d7 → f_28969: note on / off on MIDI channels 0..13; the rest is ignored.</summary>
    void ChannelEvent(int st)
    {
        int ch = st & 0xf, type = (st & 0x70) >> 4;
        if (ch >= Channels || type > 1) return;
        int key = midi[ptr[cur]] + transpose;
        int vel = type == 0 ? 0 : midi[ptr[cur] + 1];
        int v = (MusicVolume * vel & 0xffff) >> 7;
        if (v == 0) NoteOff(instrument[ch], key);
        else NoteOn(priority[ch], instrument[ch], key, v);
    }

    /// <summary>f_285aa: stop the song and every sounding voice (f_29951).</summary>
    public void Stop()
    {
        if (playing == 0) return;
        playing = 0;
        for (int v = 0; v < voices.Length; v++)
            if (voices[v].Priority != 0) NoteOff(voices[v].Instrument, voices[v].Key);
    }

    // ------------------------------------------------------------------------------------------- effects

    /// <summary>f_29927: sound effect n, a note on the instrument of the effect table (DS:0A82).</summary>
    public void Effect(int n)
    {
        var e = bank.Effects[n];
        NoteOn(e.Priority, e.Instrument, e.Key, e.Velocity);
    }

    // ------------------------------------------------------------------------------------------- voices

    /// <summary>f_29689: the voice for a note on `device` at `prio`: the lowest priority, then the oldest;
    /// -1 when every such voice has a higher priority. Ages every voice; frees sample voices that ended.</summary>
    int PickVoice(int device, int prio)
    {
        if (prio < 1) return -1;
        int best = 0xf, bestIdx = 0, bestAge = 0;
        for (int v = 0; v < voices.Length; v++)
        {
            ref var vo = ref voices[v];
            if (vo.Device == SoundBank.DeviceSample && !samples.Playing(vo.Channel)) vo.Priority = 0;
            if (vo.Device == device)
            {
                int p = vo.Priority;
                if (p < best || (p == best && vo.Age > bestAge))
                {
                    best = p;
                    bestIdx = v;
                    bestAge = vo.Age;
                }
            }
            vo.Age = (vo.Age + 1) & 0xff;
        }
        return prio >= best ? bestIdx : -1;
    }

    /// <summary>f_297ac: take a voice, silence its note, load the instrument if it changed, play.</summary>
    void NoteOn(int prio, int ins, int key, int vel)
    {
        int v = PickVoice(bank.Instruments[ins].Device, prio);
        if (v < 0) return;
        vel = (vel * Volume & 0xffff) >> 7;
        ref var vo = ref voices[v];
        DeviceOff(vo.Device, vo.Key, vo.Channel);
        if (vo.Instrument != ins && vo.Device == SoundBank.DeviceFm) Patch(ins, vo.Channel);
        DeviceOn(vo.Device, ins, key, vel, vo.Channel);
        vo.Priority = prio & 0xff;
        vo.Instrument = ins & 0xff;
        vo.Key = key & 0xff;
        vo.Age = 0;
    }

    /// <summary>f_298a8: every voice playing `key` on `ins` stops.</summary>
    void NoteOff(int ins, int key)
    {
        for (int v = 0; v < voices.Length; v++)
        {
            ref var vo = ref voices[v];
            if (vo.Key != key || vo.Instrument != ins) continue;        // a stored byte against the word
            DeviceOff(bank.Instruments[ins].Device, key, vo.Channel);
            vo.Key = 0;
            vo.Priority = 0;
            vo.Age = 0x0f;
        }
    }

    void DeviceOff(int device, int key, int ch)
    {
        if (device == SoundBank.DeviceFm)
        {
            opl(0xa0 + ch, 0);                                          // f_2839d
            opl(0xb0 + ch, 0);
        }
        else if (device == SoundBank.DeviceSample) samples.Stop(ch);   // f_2933c
    }

    void DeviceOn(int device, int ins, int key, int vel, int ch)
    {
        if (device == SoundBank.DeviceFm) FmOn(ins, key, vel, ch);
        else if (device == SoundBank.DeviceSample) SampleOn(ins, key, vel, ch);
    }

    // ------------------------------------------------------------------------------------------- FM

    int Slot(int table, int ch) => U8(0x6912 + U8(table + ch));        // operator register offset
    int Modulator(int ch) => Slot(0x68fe, ch);
    int Carrier(int ch) => Slot(0x6908, ch);

    /// <summary>f_283c5 → f_2815a: the 11 register bytes of an FM record.</summary>
    void Patch(int ins, int ch)
    {
        var r = bank.Fm(ins);
        if (r == null) return;
        int m = Modulator(ch), c = Carrier(ch);
        opl(0x20 + m, r[1]); opl(0x20 + c, r[0]);
        opl(0x40 + m, r[3]); opl(0x40 + c, r[2]);
        opl(0x60 + m, r[5]); opl(0x60 + c, r[4]);
        opl(0x80 + m, r[7]); opl(0x80 + c, r[6]);
        opl(0xe0 + m, r[10]); opl(0xe0 + c, r[9]);
        opl(0xc0 + ch, r[8]);
    }

    /// <summary>f_282b5: the carrier's level from the velocity, then the frequency and key on.</summary>
    void FmOn(int ins, int key, int vel, int ch)
    {
        var r = bank.Fm(ins);
        int v = Math.Clamp(vel + FmVelocityOffset + (short)(r[0x0d] | r[0x0e] << 8), 0, 0x7f);
        int att = U8(0x6ba4 + 2 * v);
        int level = ((0x3f - att) * ((r[2] & 0x3f) ^ 0x3f) & 0xffff) >> 6;
        opl(0x40 + Carrier(ch), (level ^ 0x3f) & 0xff | (r[2] & 0xc0));
        key += 12 * (short)(r[0x0b] | r[0x0c] << 8);
        if (key < 0 || key > 0x7f) return;
        int n = key % 12, oct = key / 12;
        opl(0xa0 + ch, U8(0x6924 + 2 * n));
        opl(0xb0 + ch, (((oct + 8) << 2) + U8(0x6925 + 2 * n)) & 0xff);
    }

    // ------------------------------------------------------------------------------------------- samples

    /// <summary>f_29263: the pitch step and attenuation of a sample note.</summary>
    void SampleOn(int ins, int key, int vel, int ch)
    {
        if (bank.SampleOf(ins) is not SoundBank.Sample s) return;
        int v = Math.Clamp(vel + SampleVelocityOffset, 0, 0x7f);
        samples.Start(ch, s, bank.SampleStep(key, s), (0x7f - v) >> 4);
    }
}
