"""Measure the user's own extracted SimAnt assets and write a metadata-only inventory: sizes, frame counts,
colour usage, durations, instruments. No pixels, no audio, no text: only facts an artist / composer needs to
match the original's proportions and timing (see docs/ART_PLAN.md).

python asset_inventory.py [out.json]       (default extracted/inventory.json, git-ignored)
"""
import json
import os
import struct
import sys
import wave
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bitmaps                                    # noqa: E402
import tiles                                      # noqa: E402

EXT = os.path.join(HERE, '..', 'extracted')

# bitmap id ranges (FILE_FORMATS "What the sprite ids are", plus later findings)
GROUPS = [(100, 199, 'window controls and map icons'), (1000, 1007, 'spider, walking (8 headings)'),
          (1050, 1053, 'spider, large frames'), (1100, 1107, 'small spider (map window)'),
          (1200, 1203, 'human sneaker (map window)'), (1210, 1211, 'lawn mower (map window)'),
          (1250, 1251, 'bird crossing (yard window)'), (1260, 1260, 'For Sale sign'),
          (1300, 1329, 'cat (yard window)'), (2000, 2100, 'title screen'), (2500, 2500, 'Select a Game'),
          (3000, 3001, 'about box'), (4500, 4699, 'panels, menus and help overlays'),
          (5000, 5199, 'toolbars and tool icons'), (6000, 6000, 'scent menu'),
          (7000, 7099, 'yard window: house, lawn, toolbar, grid, rain, swarms'),
          (8000, 8499, 'yard actors: human'), (8500, 8799, 'yard actors: dog'),
          (8800, 8999, 'yard actors: mower'), (9000, 9999, 'cutscenes and event icons'),
          (12000, 12999, 'cutscene art'), (13000, 13999, 'status window'), (14000, 14999, 'main window'),
          (15000, 15999, 'map window'), (16000, 16999, 'history window and others')]


def group_of(rid):
    for lo, hi, name in GROUPS:
        if lo <= rid <= hi:
            return name
    return 'other'


def bitmaps_info():
    d = os.path.join(EXT, 'hcegant', 'bitmap')
    pal = tiles.palette()
    out = []
    for n in sorted(os.listdir(d)):
        if not n.endswith('.bin'):
            continue
        rid = int(n[:5])
        b = open(os.path.join(d, n), 'rb').read()
        w, h, rows, info = bitmaps.decode(b, palette=pal)
        cols = Counter(pal.index(tuple(px[:3])) if tuple(px[:3]) in pal else -1
                       for r in rows for px in r if px[3])
        out.append({'id': rid, 'group': group_of(rid), 'w': w, 'h': h, 'masked': info['mode'] == 3,
                    'planes': info['planes'], 'colours': sorted(c for c in cols if c >= 0)})
    return out


def mono_info():
    d = os.path.join(EXT, 'shared', 'bitmap_mono')
    out = []
    for n in sorted(os.listdir(d)):
        if n.endswith('.bin'):
            b = open(os.path.join(d, n), 'rb').read()
            mode, planes, flags, size, w, h = struct.unpack_from('<HBBIHH', b, 0)
            out.append({'id': int(n[:5]), 'w': w, 'h': h})
    return out


def sheets_info():
    out = []
    for rid in (9, 10, 13, 14, 15, 16, 17, 18, 19, 20):
        p = os.path.join(EXT, 'hcegant', 'rects', f'{rid:05d}.bin')
        if os.path.exists(p):
            size = os.path.getsize(p)
            kind = 'tiles 16x16 (256)' if rid in (9, 10) else 'sprites 16x16 (128, mask + recolour + 4 planes)'
            out.append({'id': rid, 'bytes': size, 'kind': kind})
    return out


def fonts_info():
    from fonts import Font
    out = []
    for i in range(4):
        try:
            f = Font(i)
        except OSError:
            continue
        adv = [f.advance(c) for c in range(32, 127)]
        out.append({'id': i, 'format': 'Apple FONT' if f.mac else 'PC bitmap', 'height': f.height,
                    'advance_min': min(a for a in adv if a), 'advance_max': max(adv),
                    'monospaced': len(set(a for a in adv if a)) == 1})
    return out


def sfx_info():
    d = os.path.join(EXT, 'sound', 'sfx')
    out = []
    for n in sorted(os.listdir(d)):
        if n.endswith('.wav'):
            with wave.open(os.path.join(d, n)) as w:
                out.append({'id': int(n[:5]), 'samples': w.getnframes(), 'rate_assumed': w.getframerate(),
                            'seconds': round(w.getnframes() / w.getframerate(), 3)})
    return out


def midi_info():
    d = os.path.join(EXT, 'sound', 'music')
    out = []
    for n in sorted(os.listdir(d)):
        if not n.endswith('.mid'):
            continue
        b = open(os.path.join(d, n), 'rb').read()
        fmt, ntrk, div = struct.unpack_from('>HHH', b, 8)
        o, tempo, programs, notes, length = 14, 500000, set(), 0, 0
        for _ in range(ntrk):
            if b[o:o + 4] != b'MTrk':
                break
            tl = struct.unpack_from('>I', b, o + 4)[0]
            p, end, t, status = o + 8, o + 8 + tl, 0, 0
            while p < end:
                dt = 0
                while True:
                    c = b[p]
                    p += 1
                    dt = (dt << 7) | (c & 0x7f)
                    if not c & 0x80:
                        break
                t += dt
                if b[p] & 0x80:
                    status = b[p]
                    p += 1
                if status == 0xff:
                    typ, ln = b[p], b[p + 1]
                    if typ == 0x51:
                        tempo = int.from_bytes(b[p + 2:p + 5], 'big')
                    p += 2 + ln
                elif status in (0xf0, 0xf7):
                    ln = b[p]
                    p += 1 + ln
                else:
                    hi = status & 0xf0
                    if hi == 0xc0:
                        programs.add(b[p])
                    if hi == 0x90 and b[p + 1]:
                        notes += 1
                    p += 1 if hi in (0xc0, 0xd0) else 2
            length = max(length, t)
            o = end
        out.append({'id': int(n[:5]), 'tracks': ntrk, 'ppq': div, 'tempo_bpm': round(60e6 / tempo, 1),
                    'seconds': round(length / div * tempo / 1e6, 1), 'notes': notes,
                    'gm_programs': sorted(programs)})
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(EXT, 'inventory.json')
    inv = {'palette_size': 16, 'bitmaps': bitmaps_info(), 'mono_bitmaps': mono_info(), 'sheets': sheets_info(),
           'fonts': fonts_info(), 'sfx': sfx_info(), 'music': midi_info()}
    json.dump(inv, open(out, 'w'), indent=1)
    g = Counter(b['group'] for b in inv['bitmaps'])
    print(f'{len(inv["bitmaps"])} bitmaps, {len(inv["mono_bitmaps"])} mono, {len(inv["sheets"])} sheets, '
          f'{len(inv["fonts"])} fonts, {len(inv["sfx"])} sfx, {len(inv["music"])} songs')
    for name, n in sorted(g.items(), key=lambda kv: -kv[1]):
        sizes = Counter((b['w'], b['h']) for b in inv['bitmaps'] if b['group'] == name).most_common(3)
        print(f'  {n:3d}  {name:<50} sizes {sizes}')
    for f in inv['fonts']:
        print('  font', f)
    secs = [s['seconds'] for s in inv['sfx']]
    print(f'  sfx: {min(secs)}..{max(secs)} s at {inv["sfx"][0]["rate_assumed"]} Hz (assumed)')
    mus = inv['music']
    print(f'  music: {min(m["seconds"] for m in mus)}..{max(m["seconds"] for m in mus)} s, tempi '
          f'{sorted(set(m["tempo_bpm"] for m in mus))}, GM programs used '
          f'{sorted(set(p for m in mus for p in m["gm_programs"]))}')
    print('wrote', out)


if __name__ == '__main__':
    main()
