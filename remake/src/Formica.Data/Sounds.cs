namespace Formica.Data;

/// <summary>The sound effects of the SOUND archive (type 5, ids 0..56; tools/extract.py decode_sfx).
/// f_00ed8(n, ..) plays entry n of the table at DS:0A80 (8 bytes each, filled from the archive at start-up)
/// when there is sound hardware (DS:1926) and sound is on (T:07AC): the remake takes entry n as resource id n.
/// Ids 10000 and up are the MIDI songs (types 18 / 20), not decoded here.</summary>
public static class Sounds
{
    /// <summary>The sample rate is not stored; 11025 Hz is a guess still to be confirmed by ear.</summary>
    public const int SampleRate = 11025;

    /// <summary>16 signed delta-table bytes, then 4-bit codes (high nibble first), clamped: signed 8-bit PCM.</summary>
    public static sbyte[] Decode(byte[] d)
    {
        if (d.Length < 16) return Array.Empty<sbyte>();
        var res = new sbyte[(d.Length - 16) * 2];
        int s = 0, k = 0;
        for (int i = 16; i < d.Length; i++)
        {
            foreach (int nib in new[] { d[i] >> 4, d[i] & 0x0f })
            {
                s = Math.Clamp(s + (sbyte)d[nib], -128, 127);
                res[k++] = (sbyte)s;
            }
        }
        return res;
    }
}
