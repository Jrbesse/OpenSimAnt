namespace Formica.Data;

/// <summary>The samples of the SOUND archive (type 5, ids 0..56; tools/extract.py decode_sfx): the sample
/// instruments of the sound driver. Which sample an effect plays, and at what rate, is SoundBank's: effect n
/// is instrument n of the driver (DS:0A82), mixed at SoundBank.MixRate (5575.6 Hz) times the note's step.
/// Ids 10000 and up are the MIDI songs (types 18 / 20), not decoded here.</summary>
public static class Sounds
{

    /// <summary>16 signed delta-table bytes, then 4-bit codes (high nibble first): signed 8-bit PCM. The sum
    /// wraps in 8 bits, as the original's loader leaves the samples in memory (checked against the emulator:
    /// clamping changes most of the cat's meow and the bird call).</summary>
    public static sbyte[] Decode(byte[] d)
    {
        if (d.Length < 16) return Array.Empty<sbyte>();
        var res = new sbyte[(d.Length - 16) * 2];
        int s = 0, k = 0;
        for (int i = 16; i < d.Length; i++)
        {
            foreach (int nib in new[] { d[i] >> 4, d[i] & 0x0f })
            {
                s = (sbyte)(s + (sbyte)d[nib]);
                res[k++] = (sbyte)s;
            }
        }
        return res;
    }
}
