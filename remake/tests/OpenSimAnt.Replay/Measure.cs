using System.Text.Json;
using System.Text.RegularExpressions;
using OpenSimAnt.Data;

namespace OpenSimAnt.Replay;

/// <summary>`OpenSimAnt.Replay --measure [game dir] [out dir]`: the clean pack's measured specifications (ROADMAP A3), written
/// from the player's own files to docs/clean_pack/data/*.json. Only what ART_PLAN section 2 allows to pass on:
/// sizes, counts, frame lists, colour indices used, text lengths and the code-filled placeholders, durations, tempi,
/// and the numeric structure the engine depends on (window and card geometry, style-run counts, the sound driver's
/// instrument roles). Never pixels, wording, waveforms or melodies.</summary>
public static class Measure
{
    public static int Run(string gameDir, string outDir)
    {
        var f = new OriginalFiles(gameDir);
        Directory.CreateDirectory(outDir);
        var opts = new JsonSerializerOptions { WriteIndented = true };
        void Write(string name, object o)
        {
            File.WriteAllText(Path.Combine(outDir, name + ".json"), JsonSerializer.Serialize(o, opts));
            Console.WriteLine($"{name}.json");
        }

        // colour and 1-bit bitmaps
        Write("bitmaps", new[] { "HCEGANT", "SHARED" }.SelectMany(a => f.Of(a, 2).Select(r =>
        {
            var d = r.Data;
            var (w, h, px) = Bitmaps.Decode(d);
            return new
            {
                archive = a, id = r.Id, width = w, height = h, planes = (int)d[2], masked = (d[0] | d[1] << 8) == 3,
                colours = px.Where(c => c >= 0).Select(c => (int)c).Distinct().OrderBy(c => c).ToArray(),
                transparent_pixels = px.Count(c => c < 0),
            };
        })).OrderBy(x => x.archive).ThenBy(x => x.id).ToList());

        // tile and sprite sheets, cursors, palette
        Write("sheets", f.Of("HCEGANT", 9).Select(r => new
        {
            id = r.Id, bytes = r.Data.Length,
            kind = r.Id is 9 or 10 ? "tiles: 256 x (16 rows x 4 planes x 2 bytes)" : r.Id >= 13 ? "sprites: 128 x 16 rows x (mask, recolour mask, 4 planes) x 2 bytes" : "table",
        }).OrderBy(x => x.id).ToList());
        Write("cursors", new[] { "HCEGANT", "SHARED" }.SelectMany(a => new[] { 7, 8 }.SelectMany(t => f.Of(a, t).Select(r => new
        {
            archive = a, type = t, id = r.Id, width = r.Data[0] | r.Data[1] << 8, height = r.Data[2] | r.Data[3] << 8, bytes = r.Data.Length,
        }))).ToList());

        // fonts: metrics and advance widths (measurements, not the glyphs)
        var fonts = new List<object>();
        foreach (var r in f.Of("SHARED", 11))
        {
            var bf = new BitmapFont(r.Data);
            fonts.Add(new { source = $"SHARED 11 {r.Id}", game_font = r.Id, format = bf.IsMac ? "Apple FONT" : "the game's own", height = bf.Height, ascent = bf.Ascent, advances = Advances(bf) });
        }
        foreach (var (n, data) in f.FontFiles)
        {
            var bf = new BitmapFont(data);
            fonts.Add(new { source = $"FONT{n}", game_font = n + 1, format = bf.IsMac ? "Apple FONT" : "the game's own", height = bf.Height, ascent = bf.Ascent, advances = Advances(bf) });
        }
        Write("fonts", fonts);

        // string lists: per entry its length, the placeholders the code fills, its line breaks
        var ph = new Regex(@"%-?\d*l?[dsxuc]|\^\d|\\n");
        Write("strings", new[] { "SHARED", "HCEGANT" }.SelectMany(a => f.Of(a, 4).Select(r => new
        {
            archive = a, id = r.Id,
            entries = Pascal(r.Data).Select(s => new { length = s.Length, codes = ph.Matches(s).Select(m => m.Value).ToArray() }).ToArray(),
        })).OrderBy(x => x.id).ToList());

        // texts (the SimAntipedia's and the prompts'), with their style runs (bold = a link word) and the cards that show them
        var cards = f.Of("SHARED", 17).OrderBy(r => r.Id).Select(r => Card(r.Id, r.Data)).ToList();
        Write("texts", f.Of("SHARED", 10).OrderBy(r => r.Id).Select(r =>
        {
            int n = Array.IndexOf(r.Data, (byte)0);
            var text = OriginalFiles.MacText(r.Data.AsSpan(0, n < 0 ? r.Data.Length : n));
            var styl = f.Get("SHARED", 21, r.Id)?.Data;
            int runs = styl == null ? 0 : (styl[0] << 8) | styl[1];
            int bold = 0;
            for (int i = 0; styl != null && i < runs; i++) if (((styl[2 + 20 * i + 12] << 8) | styl[2 + 20 * i + 13]) == 0x0100) bold++;
            return new
            {
                id = r.Id, length = text.Length, words = text.Split((char[])null, StringSplitOptions.RemoveEmptyEntries).Length,
                paragraphs = text.Split('\n').Length, style_runs = runs, bold_runs = bold,
                on_cards = cards.Where(c => c.texts.Contains(r.Id)).Select(c => c.id).ToArray(),
            };
        }).ToList());
        Write("cards", cards.Select(c => new { c.id, c.height, c.width, c.pictures, c.text_boxes, name_length = (f.Get("SHARED", 19, c.id)?.Data.Length ?? 0) }).ToList());

        // menus: titles and items as lengths and states
        var menus = f.Get("SHARED", 6, 0)?.Data;
        if (menus != null) Write("menus", MenuShape(menus));

        // window layouts: the numeric structure verbatim (geometry, types, flags, schemes), each item's text as a length
        Write("layouts", f.Of("HCEGANT", 0).OrderBy(r => r.Id).Select(r => r.Id < 128 && r.Data.Length >= 0x2c
            ? (object)LayoutShape(r.Id, r.Data)
            : new { id = r.Id, ui_table_hex = Convert.ToHexString(r.Data) }).ToList());

        // sounds: lengths at the driver's rate; songs: tempo, ticks, tracks, channels, notes
        Write("sounds", f.Of("SOUND", 5).OrderBy(r => r.Id).Select(r =>
        {
            var s = Sounds.Decode(r.Data);
            return new { id = r.Id, samples = s.Length, seconds = Math.Round(s.Length / 5575.6, 3), peak = s.Length == 0 ? 0 : s.Max(v => Math.Abs((int)v)) };
        }).ToList());
        Write("songs", f.Of("SOUND", 20).OrderBy(r => r.Id).Select(r => SongShape(r.Id, r.Data)).ToList());
        Write("song_cues", f.Of("SOUND", 18).OrderBy(r => r.Id).Select(r => new
        {
            cue = r.Id, song = (r.Data[0] << 8) | r.Data[1], transpose = (short)((r.Data[6] << 8) | r.Data[7]), bytes_hex = Convert.ToHexString(r.Data),
        }).ToList());

        // the embedded assets: sizes and roles
        var bank = f.Bank;
        Write("embedded", new
        {
            assets = EmbeddedAssets.All.Select(a => new { a.Name, bytes = a.Size, a.About }).ToArray(),
            instruments = Enumerable.Range(0, SoundBank.InstrumentCount).Select(i => new
            {
                index = i, device = bank.Instruments[i].Device switch { 1 => "sample", 2 => "FM", _ => "none" },
                sample_sound = bank.SampleOf(i)?.SoundId, base_octave = bank.SampleOf(i)?.BaseOctave, transpose = bank.SampleOf(i)?.Transpose,
                used_by_effects = Enumerable.Range(0, SoundBank.EffectCount).Where(e => bank.Effects[e].Instrument == i).ToArray(),
            }).ToArray(),
            effects = Enumerable.Range(0, SoundBank.EffectCount).Select(e => new { effect = e, bank.Effects[e].Key, bank.Effects[e].Priority, bank.Effects[e].Instrument, bank.Effects[e].Velocity }).ToArray(),
            glossary_entries = (EmbeddedAssets.Get("glossary").Size - 2) / 0x22,
            version_line_length = f.VersionLine.Length,
        });
        return 0;
    }

    static int[] Advances(BitmapFont bf) => Enumerable.Range(0, 256).Select(bf.Advance).ToArray();

    static List<string> Pascal(byte[] d)
    {
        int n = (d[0] << 8) | d[1], p = 2;
        var res = new List<string>();
        for (int i = 0; i < n && p < d.Length; i++)
        {
            int len = d[p];
            res.Add(OriginalFiles.MacText(d.AsSpan(p + 1, Math.Min(len, d.Length - p - 1))));
            p += 1 + len;
        }
        return res;
    }

    sealed record CardShape(int id, int height, int width, List<object> pictures, List<object> text_boxes, HashSet<int> texts);

    static CardShape Card(int id, byte[] d)
    {
        static int Be(byte[] b, int o) => (short)((b[o] << 8) | b[o + 1]);
        var pics = new List<object>();
        var boxes = new List<object>();
        var texts = new HashSet<int>();
        int p = 4;
        while (p + 4 <= d.Length)
        {
            string tag = System.Text.Encoding.ASCII.GetString(d, p, 4);
            p += 4;
            if (tag == "PICT")
            {
                int bmp = Be(d, p);
                var rect = new[] { Be(d, p + 2), Be(d, p + 4), Be(d, p + 6), Be(d, p + 8) };
                int n = Be(d, p + 10);
                var links = Enumerable.Range(0, n).Select(i => new { rect = new[] { Be(d, p + 12 + 10 * i), Be(d, p + 14 + 10 * i), Be(d, p + 16 + 10 * i), Be(d, p + 18 + 10 * i) }, link = Be(d, p + 20 + 10 * i) }).ToArray();
                pics.Add(new { bitmap = bmp, rect, links });
                p += 12 + 10 * n;
            }
            else if (tag == "TEXT")
            {
                var rect = new[] { Be(d, p), Be(d, p + 2), Be(d, p + 4), Be(d, p + 6) };
                int n = Be(d, p + 8);
                var ids = Enumerable.Range(0, n).Select(i => Be(d, p + 10 + 2 * i)).ToArray();
                foreach (var t in ids) texts.Add(t);
                boxes.Add(new { rect, texts = ids });
                p += 10 + 2 * n;
            }
            else break;
        }
        return new CardShape(id, Be(d, 0), Be(d, 2), pics, boxes, texts);
    }

    static object MenuShape(byte[] d)
    {
        var lists = new List<object>();
        for (int e = 0; ; e++)
        {
            int off = BitConverter.ToInt32(d, 4 * e);
            if (off == 0 || off >= d.Length) break;
            var items = new List<object>();
            int p = off;
            while (p < d.Length)
            {
                int q = BitConverter.ToInt32(d, p);
                p += 4;
                if (q == 0 || q >= d.Length) break;
                int end = Array.IndexOf(d, (byte)0, q);
                var s = System.Text.Encoding.ASCII.GetString(d, q, end - q);
                items.Add(e == 0 ? new { length = s.Length, state = 0, separator = false }
                                 : new { length = s.Length - 1, state = (int)d[q], separator = s.EndsWith("---") });
            }
            lists.Add(new { list = e == 0 ? "titles" : $"menu {e - 1}", items });
        }
        return lists;
    }

    static object LayoutShape(int id, byte[] d)
    {
        int n = d[0x0c] | d[0x0d] << 8;
        var items = new List<object>();
        for (int i = 0; i < n; i++)
        {
            int o = d[0x2c + 4 * i] | d[0x2d + 4 * i] << 8;
            int len = d[o + 0x22] | d[o + 0x23] << 8;
            int type = d[o + 0x21];
            int at = (type == 0x05 || type == 0x09 || type == 0x0c) && len > 0x2a ? 0x2a : type >= 0x10 && type <= 0x12 && len > 0x2e ? 0x2e : -1;
            var b = d.AsSpan(o, Math.Min(len, d.Length - o)).ToArray();
            if (at < 0) items.Add(new { offset = o, item_hex = Convert.ToHexString(b), text_length = (int?)null });
            else
            {
                int e = Array.IndexOf(b, (byte)0, at);
                if (e < 0) e = b.Length;
                items.Add(new { offset = o, item_hex = Convert.ToHexString(b[..at]), text_length = (int?)(e - at), after_hex = Convert.ToHexString(b[Math.Min(e + 1, b.Length)..]) });
            }
        }
        int first = n == 0 ? d.Length : Enumerable.Range(0, n).Min(i => d[0x2c + 4 * i] | d[0x2d + 4 * i] << 8);
        return new { id, header_hex = Convert.ToHexString(d.AsSpan(0, first)), bytes = d.Length, items };
    }

    static object SongShape(int id, byte[] m)
    {
        int Be16(int o) => (m[o] << 8) | m[o + 1];
        int Be32(int o) => (m[o] << 24) | (m[o + 1] << 16) | (m[o + 2] << 8) | m[o + 3];
        int ntr = Be16(10), ppq = Be16(12), p = 14;
        var tempos = new List<int>();
        var channels = new SortedSet<int>();
        int notes = 0, lo = 127, hi = 0;
        long end = 0;
        var tracks = new List<object>();
        for (int t = 0; t < ntr && p + 8 <= m.Length; t++)
        {
            int len = Be32(p + 4), q = p + 8, stop = q + len, status = 0, tn = 0;
            long time = 0;
            string name = null;
            var tch = new SortedSet<int>();
            while (q < stop)
            {
                int v = 0;
                do { v = (v << 7) | (m[q] & 0x7f); } while ((m[q++] & 0x80) != 0);
                time += v;
                int b = m[q];
                if (b == 0xff)
                {
                    int type = m[q + 1], l = 0;
                    q += 2;
                    do { l = (l << 7) | (m[q] & 0x7f); } while ((m[q++] & 0x80) != 0);
                    if (type == 0x51) tempos.Add((m[q] << 16) | (m[q + 1] << 8) | m[q + 2]);
                    if (type == 0x03) name = System.Text.Encoding.ASCII.GetString(m, q, l);
                    q += l;
                    continue;
                }
                if (b == 0xf0 || b == 0xf7)
                {
                    q++;
                    int l = 0;
                    do { l = (l << 7) | (m[q] & 0x7f); } while ((m[q++] & 0x80) != 0);
                    q += l;
                    continue;
                }
                if ((b & 0x80) != 0) { status = b; q++; }
                int kind = status & 0xf0, ch = status & 15;
                int dlen = kind is 0xc0 or 0xd0 ? 1 : 2;
                if (kind == 0x90 && m[q + 1] > 0)
                {
                    notes++; tn++;
                    lo = Math.Min(lo, m[q]); hi = Math.Max(hi, m[q]);
                    channels.Add(ch); tch.Add(ch);
                }
                q += dlen;
            }
            end = Math.Max(end, time);
            tracks.Add(new { role = tch.Count == 0 ? "tempo / title (no notes)" : tch.All(c => c is >= 5 and <= 10) ? "percussion (sampled drums)" : "melodic", notes = tn, channels = tch.ToArray() });
            p = stop;
        }
        int tempo = tempos.Count > 0 ? tempos[0] : 500000;
        return new
        {
            id, ppq, tracks = ntr, tempo_us_per_quarter = tempos.Distinct().ToArray(), bpm = Math.Round(60e6 / tempo, 1),
            ticks = end, seconds = ppq == 0 ? 0 : Math.Round(end * (double)tempo / ppq / 1e6, 1),
            notes, lowest = lo, highest = hi, channels = channels.ToArray(), per_track = tracks,
        };
    }
}
