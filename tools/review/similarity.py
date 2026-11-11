"""Measure how similar the clean pack's assets are to the original's -- the numbers behind the A5 review.

    python tools/review/similarity.py [--json=out.json] [categories...]

Categories: bitmaps fonts sounds music. Each is measured against the player's own files in `extracted/`
(run `python tools/extract.py` first) and the clean sources in `remake/game/assets/clean/src/`.

What each number means, and why it is the one that matters:

- **identical** -- the share of pixels whose *palette index* is the same. The pack must be similar in shape and
  colour role, but a high identical share is a copying signal (the clean-room rule: assets that are too close
  are remade). Index comparison, not RGB: the pack's palette is the Mac 16 and the original's is EGA, so equal
  colours across the two palettes are coincidences, not evidence.
- **iou** -- intersection over union of the drawn (non-transparent) pixels: silhouette agreement.
- **colours** -- Jaccard overlap of the palette indices each asset uses: the same colour *roles*, stated
  independently of shape.

Sounds and songs are structure-only (duration, envelope, notes, tempo): a waveform or melody match is a copying
signal, and the pack's own measurements are checked by `tools/clean_pack/build.py --roundtrip`. Rendering both
sides through one mixer is issue #35 and is not done here.
"""
import json
import os
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import bitmaps as bitmaps_lib                                  # noqa: E402
import fonts as fonts_lib                                      # noqa: E402

SRC = os.path.join(ROOT, 'remake', 'game', 'assets', 'clean', 'src')
EXT = os.path.join(ROOT, 'extracted')
DATA = os.path.join(ROOT, 'docs', 'clean_pack', 'data')


def pix_grid(path):
    """A .pix file -> list of rows of palette-index ints (None for '.')."""
    rows = []
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        rows.append([None if c == '.' else int(c, 16) for c in line])
    return rows


EGA_INDEX = {c: i for i, c in enumerate(bitmaps_lib.EGA)}


def original_bitmap(archive, rid):
    """(w, h, rows of index-or-None) for one original type-2 bitmap."""
    name = f'{rid:05d}.bin'
    if archive == 'SHARED' and os.path.exists(os.path.join(EXT, 'shared', 'bitmap_mono', name)):
        p = os.path.join(EXT, 'shared', 'bitmap_mono', name)
    else:
        p = os.path.join(EXT, archive.lower(), 'bitmap', name)
    w, h, _, rgba = decode_any(p)
    rows = [[None if a == 0 else EGA_INDEX[(r, g, b)] for r, g, b, a in row] for row in rgba]
    return w, h, rows


def decode_any(path):
    d = open(path, 'rb').read()
    mode, planes, flags, size, w, h = struct.unpack_from('<HBBIHH', d, 0)
    w, h, rows, meta = bitmaps_lib.decode(d)
    return w, h, planes, rows


def find_pix(archive, rid):
    base = os.path.join(SRC, 'bitmaps')
    for name in (f'{archive}_{rid}.pix', f'{archive.lower()}_{rid}.pix'):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def measure_bitmaps():
    meas = json.load(open(os.path.join(DATA, 'bitmaps.json')))
    out = []
    for m in meas:
        p = find_pix(m['archive'], m['id'])
        if not p:
            out.append(dict(id=m['id'], archive=m['archive'], missing=True))
            continue
        clean = pix_grid(p)
        w, h, orig = original_bitmap(m['archive'], m['id'])
        if (w, h) != (m['width'], m['height']):
            out.append(dict(id=m['id'], archive=m['archive'], shape_mismatch=[w, h]))
            continue
        same = drawn = inter = union = 0
        cset, oset = set(), set()
        for y in range(h):
            for x in range(w):
                a = clean[y][x] if y < len(clean) and x < len(clean[y]) else None
                b = orig[y][x]
                if a is not None:
                    cset.add(a)
                if b is not None:
                    oset.add(b)
                if a == b:
                    same += 1
                if a is not None or b is not None:
                    drawn += 1
                if a is not None and b is not None:
                    inter += 1
                    union += 1
                elif a is not None or b is not None:
                    union += 1
        out.append(dict(id=m['id'], archive=m['archive'], w=w, h=h, planes=m['planes'],
                        identical=round(same / (w * h), 4),
                        iou=round(inter / union, 4) if union else 1.0,
                        colour_jaccard=round(len(cset & oset) / len(cset | oset), 3) if cset | oset else 1.0,
                        clean_colours=sorted(cset), orig_colours=sorted(oset)))
    return out


def measure_fonts():
    out = []
    for fid in range(6):
        pix = os.path.join(SRC, 'fonts', f'font{fid}.pix')
        spec = os.path.join(SRC, 'fonts', f'font{fid}.json')
        if not os.path.exists(pix):
            out.append(dict(font=fid, missing=True))
            continue
        grid = pix_grid(pix)
        meta = json.load(open(spec)) if os.path.exists(spec) else {}
        ncodes = len(meta.get('advances', []))
        if not ncodes:
            out.append(dict(font=fid, original='no advances in spec'))
            continue
        cw = len(grid[0]) // 16
        nrows = -(-ncodes // 16)
        ch = len(grid) // nrows
        try:
            f = fonts_lib.Font(fid)
        except OSError:
            out.append(dict(font=fid, original='absent-too'))
            continue
        total = same = 0
        cink = oink = 0
        for code in range(ncodes):
            if code < f.first:
                continue
            cx, cy = (code % 16) * cw, (code // 16) * ch
            cell = [row[cx:cx + cw] for row in grid[cy:cy + ch]]
            dx, orows = f.glyph(code)
            if not orows or not sum(sum(r) for r in orows):
                continue                       # the original has no glyph here: nothing to compare
            total += 1
            eq = True
            for y in range(min(ch, len(orows))):
                for x in range(cw):
                    a = 1 if cell[y][x] is not None else 0
                    xx = x - dx
                    b = orows[y][xx] if 0 <= xx < len(orows[y]) else 0
                    cink += a
                    oink += b
                    if a != b:
                        eq = False
            if eq:
                same += 1
        out.append(dict(font=fid, glyphs=total, identical_glyphs=same,
                        identical_share=round(same / total, 3) if total else None,
                        ink_ratio=round(cink / oink, 3) if oink else None,
                        advances_match=(meta.get('advances') is not None)))
    return out


def read_wav(path):
    with wave.open(path, 'rb') as w:
        n, sw, ch, sr = w.getnframes(), w.getsampwidth(), w.getnchannels(), w.getframerate()
        raw = w.readframes(n)
    if sw == 1:
        vals = [b - 128 for b in raw][::ch]
    else:
        vals = list(struct.unpack(f'<{n * ch}h', raw))[::ch]
    return vals, sr


def envelope(vals, sr, rate=200):
    """Peak envelope at `rate` Hz, normalised to 0..1 -- a size-independent shape signature."""
    step = max(1, sr // rate)
    env = [max((abs(v) for v in vals[i:i + step]), default=0) for i in range(0, len(vals), step)]
    peak = max(env) if env else 0
    return [e / peak for e in env] if peak else env


def corr(a, b):
    n = min(len(a), len(b))
    if n < 4:
        return None
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((x - mb) ** 2 for x in b) ** 0.5
    if not va or not vb:
        return None
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (va * vb)


def measure_sounds():
    out = []
    base = os.path.join(SRC, 'sounds')
    for name in sorted(os.listdir(base)):
        if not (name.startswith('sfx_') and name.endswith('.wav')):
            continue
        n = int(name[4:-4])
        cvals, csr = read_wav(os.path.join(base, name))
        op = os.path.join(EXT, 'sound', 'sfx', f'{n:05d}.wav')
        if not os.path.exists(op):
            out.append(dict(id=n, original='absent'))
            continue
        ovals, osr = read_wav(op)
        ce, oe = envelope(cvals, csr), envelope(ovals, osr)
        out.append(dict(id=n, clean_s=round(len(cvals) / csr, 3), orig_s=round(len(ovals) / osr, 3),
                        duration_ratio=round((len(cvals) / csr) / (len(ovals) / osr), 3),
                        env_corr=round(corr(ce, oe), 3) if corr(ce, oe) is not None else None,
                        clean_peak=max(abs(v) for v in cvals) if cvals else 0,
                        orig_peak=max(abs(v) for v in ovals) if ovals else 0))
    return out


def midi_notes(path):
    """(ppq, [(tick, channel, pitch, dur_ticks)]) from a format-0/1 MIDI file; tempo events too."""
    d = open(path, 'rb').read()
    assert d[:4] == b'MThd'
    hlen, fmt, ntrk, ppq = struct.unpack('>IHHH', d[4:14])
    pos = 8 + hlen
    notes = []
    tempos = []
    for _ in range(ntrk):
        assert d[pos:pos + 4] == b'MTrk'
        tlen = struct.unpack('>I', d[pos + 4:pos + 8])[0]
        p, end = pos + 8, pos + 8 + tlen
        tick, status, on = 0, 0, {}
        while p < end:
            delta, p = _varlen(d, p)
            tick += delta
            if d[p] & 0x80:
                status = d[p]
                p += 1
            if status == 0xFF:
                meta = d[p]
                p += 1
                ln, p = _varlen(d, p)
                if meta == 0x51 and ln == 3:
                    us = int.from_bytes(d[p:p + 3], 'big')
                    tempos.append((tick, us))
                p += ln
            elif status in (0xF0, 0xF7):
                ln, p = _varlen(d, p)
                p += ln
            else:
                hi, ch = status & 0xF0, status & 0x0F
                if hi in (0xC0, 0xD0):
                    p += 1
                else:
                    a, b = d[p], d[p + 1]
                    p += 2
                    if hi == 0x90 and b > 0:
                        on[(ch, a)] = tick
                    elif hi == 0x80 or (hi == 0x90 and b == 0):
                        t0 = on.pop((ch, a), None)
                        if t0 is not None:
                            notes.append((t0, ch, a, tick - t0))
        pos = end
    return ppq, notes, tempos


def _varlen(d, p):
    v = 0
    while True:
        b = d[p]
        p += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, p


def hist_cosine(a, b):
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return dot / (na * nb) if na and nb else None


def measure_music():
    out = []
    base = os.path.join(SRC, 'music')
    for name in sorted(os.listdir(base)):
        if not name.endswith('.mid'):
            continue
        sid = int(name[:-4])
        cppq, cnotes, ctempos = midi_notes(os.path.join(base, name))
        op = os.path.join(EXT, 'sound', 'music', f'{sid}.mid')
        if not os.path.exists(op):
            out.append(dict(id=sid, original='absent'))
            continue
        oppq, onotes, otempos = midi_notes(op)
        cbeat = ctempos[0][1] if ctempos else 500000
        obeat = otempos[0][1] if otempos else 500000
        c_hist, o_hist = {}, {}
        for _, _, pitch, _ in cnotes:
            c_hist[pitch // 12] = c_hist.get(pitch // 12, 0) + 1
        for _, _, pitch, _ in onotes:
            o_hist[pitch // 12] = o_hist.get(pitch // 12, 0) + 1
        # exact note identity: a copied melody keeps (pitch, start, length) triples
        cset = {(p, round(t * cbeat / cppq), round(d * cbeat / cppq)) for t, _, p, d in cnotes}
        oset = {(p, round(t * obeat / oppq), round(d * obeat / oppq)) for t, _, p, d in onotes}
        out.append(dict(id=sid, clean_notes=len(cnotes), orig_notes=len(onotes),
                        note_ratio=round(len(cnotes) / len(onotes), 3) if onotes else None,
                        clean_bpm=round(60_000_000 / cbeat, 1), orig_bpm=round(60_000_000 / obeat, 1),
                        octave_cosine=round(hist_cosine(c_hist, o_hist), 3) if hist_cosine(c_hist, o_hist) else None,
                        exact_note_share=round(len(cset & oset) / len(cset | oset), 4) if cset | oset else None))
    return out


def summarise(name, rows):
    rows = [r for r in rows if not r.get('missing') and not r.get('original')]
    print(f'\n## {name}: {len(rows)} measured')
    if name == 'bitmaps':
        rows.sort(key=lambda r: -r['identical'])
        ident = [r['identical'] for r in rows]
        print(f'  identical pixels: median {sorted(ident)[len(ident) // 2]:.3f}, '
              f'max {max(ident):.3f} ({rows[0]["archive"]}/{rows[0]["id"]})')
        print(f'  silhouette IoU:   median {sorted(r["iou"] for r in rows)[len(rows) // 2]:.3f}')
        print(f'  colour Jaccard:   median {sorted(r["colour_jaccard"] for r in rows)[len(rows) // 2]:.3f}')
        print('  most identical:')
        for r in rows[:10]:
            print(f'    {r["archive"]}/{r["id"]:<6} identical {r["identical"]:.3f}  iou {r["iou"]:.3f}  '
                  f'colours {r["colour_jaccard"]:.2f}  {r["w"]}x{r["h"]}')
    elif name == 'fonts':
        for r in rows:
            print(f'  font {r["font"]}: {r["glyphs"]} glyphs, identical {r["identical_glyphs"]} '
                  f'({r["identical_share"]}), ink {r["ink_ratio"]}')
    elif name == 'sounds':
        for r in sorted(rows, key=lambda r: r['id']):
            print(f'  sfx {r["id"]:<3} {r["clean_s"]:>6}s / {r["orig_s"]:>6}s  x{r["duration_ratio"]:<5} '
                  f'env_corr {r["env_corr"]}')
    elif name == 'music':
        for r in rows:
            print(f'  {r["id"]} notes {r["clean_notes"]:>5}/{r["orig_notes"]:<5} x{r["note_ratio"]:<5} '
                  f'bpm {r["clean_bpm"]:>6}/{r["orig_bpm"]:<6} octave-cos {r["octave_cosine"]} '
                  f'exact {r["exact_note_share"]}')
    return rows


def measure_strings():
    """Do the pack's new words fit the original's slots, and are any of them the original's words?

    Reports counts and ratios only -- the original's text is the owner's copy and never leaves this measurement."""
    from clean_pack.build import dec_strlist
    out = []
    base = os.path.join(SRC, 'strings')
    for name in sorted(os.listdir(base)):
        if not name.endswith('.json'):
            continue
        lists = json.load(open(os.path.join(base, name)))
        numeric = [(k, v) for k, v in lists.items() if k.isdigit()]
        for sid, entries in sorted(numeric, key=lambda kv: int(kv[0])):
            p = os.path.join(EXT, 'shared', 'strings', f'{int(sid):05d}.bin')
            if not os.path.exists(p):
                out.append(dict(list=int(sid), file=name, original='absent'))
                continue
            orig = dec_strlist(open(p, 'rb').read())
            pairs = list(zip(entries, orig))
            exact = sum(1 for a, b in pairs if a == b)
            ratios = sorted((len(a) / len(b)) for a, b in pairs if b)
            out.append(dict(list=int(sid), file=name, entries=len(entries), orig_entries=len(orig),
                            compared=len(pairs), exact=exact,
                            len_ratio_median=round(ratios[len(ratios) // 2], 3) if ratios else None,
                            fits_80_125=sum(1 for r in ratios if 0.8 <= r <= 1.25),
                            ratio_n=len(ratios)))
    return out


def summarise_strings(rows):
    rows = [r for r in rows if not r.get('original')]
    print(f'\n## strings: {len(rows)} lists measured')
    exact = sum(r['exact'] for r in rows)
    comp = sum(r['compared'] for r in rows)
    fit = sum(r['fits_80_125'] for r in rows)
    rn = sum(r['ratio_n'] for r in rows)
    print(f'  lists with the original list present: {len(rows)}; entries compared {comp}')
    print(f'  entries identical to the original: {exact} ({exact / comp:.1%})' if comp else '  no entries compared')
    print(f'  entries within 0.80..1.25x the original length: {fit}/{rn} ({fit / rn:.1%})' if rn else '')
    short = [r for r in rows if r['entries'] != r['orig_entries']]
    print(f'  lists whose entry count differs: {len(short)}')
    for r in short[:8]:
        print(f'    list {r["list"]} ({r["file"]}): {r["entries"]} vs {r["orig_entries"]}')
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    jout = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--json=')), None)
    cats = args or ['bitmaps', 'fonts', 'sounds', 'music', 'strings']
    result = {}
    for c in cats:
        if c == 'strings':
            result[c] = summarise_strings(measure_strings())
            continue
        rows = {'bitmaps': measure_bitmaps, 'fonts': measure_fonts,
                'sounds': measure_sounds, 'music': measure_music}[c]()
        result[c] = summarise(c, rows)
    if jout:
        json.dump(result, open(jout, 'w'), indent=1)
        print(f'\nwrote {jout}')


if __name__ == '__main__':
    main()
