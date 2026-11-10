---
layout: default
title: "extract"
permalink: /reference/extract/
---

# extract

*`extract.py` — Extract every resource from the SimAnt DOS archives into ../extracted.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `extract.py`]({{ site.baseurl }}/assets/reference/tools/extract.py)

Extract every resource from the SimAnt DOS archives into ../extracted.

Usage: python -I tools/extract.py [game_dir] [out_dir]

## At a glance

- **108** lines
- **5 top-level functions**, including `mac_text`, `pstrings`, `decode_sfx`, `write_wav`, `main`

## Source

{% raw %}
```python
"""Extract every resource from the SimAnt DOS archives into ../extracted.

Usage: python -I tools/extract.py [game_dir] [out_dir]
"""
import json
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simres import read_archive  # noqa: E402
from bitmaps import decode  # noqa: E402
from png import write_png  # noqa: E402

TYPE_NAMES = {
    'SHARED': {2: 'bitmap_mono', 4: 'strings', 6: 'menus', 7: 'cursor', 9: 'misc9', 10: 'text',
               11: 'font', 17: 'card_layout', 19: 'card_name', 21: 'text_style'},
    'HCEGANT': {0: 'layout', 2: 'bitmap', 4: 'strings', 7: 'cursor', 8: 'cursor16', 9: 'rects', 15: 'palette'},
    'SOUND': {5: 'sfx', 18: 'music_info', 20: 'music'},
}


def mac_text(b):
    return b.decode('mac_roman').replace('\r', '\n')


def pstrings(d):
    """Mac STR#: u16 BE count, then Pascal strings."""
    n = struct.unpack_from('>H', d, 0)[0]
    out, p = [], 2
    for _ in range(n):
        ln = d[p]
        out.append(mac_text(d[p + 1:p + 1 + ln]))
        p += 1 + ln
    return out


def decode_sfx(d):
    """16 signed delta-table bytes, then 4-bit codes (high nibble first), into 8-bit unsigned PCM. The sum
    wraps in 8 bits, as the game's loader leaves the samples in memory. The game plays them at 5575.6 Hz
    (docs/SIM_NOTES.md "The sound driver")."""
    table = [b - 256 if b > 127 else b for b in d[:16]]
    s = 0
    out = bytearray()
    for byte in d[16:]:
        for nib in (byte >> 4, byte & 0x0f):
            s = (s + table[nib]) & 0xff
            out.append(s ^ 0x80)
    return bytes(out)


def write_wav(path, pcm, rate=5576):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(pcm)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    game = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, '..', 'extracted')
    manifest = {}

    pal_res = [e for e in read_archive(os.path.join(game, 'HCEGANT')) if e['type'] == 15 and e['id'] == 0][0]
    palette = [tuple(pal_res['data'][2 + i * 3:5 + i * 3]) for i in range(16)]

    for arch in ('SHARED', 'HCEGANT', 'SOUND'):
        res = read_archive(os.path.join(game, arch))
        names = TYPE_NAMES[arch]
        entries = []
        for e in res:
            tname = names.get(e['type'], 'type%d' % e['type'])
            d = e['data']
            folder = os.path.join(out, arch.lower(), tname)
            os.makedirs(folder, exist_ok=True)
            stem = os.path.join(folder, '%05d' % e['id'])
            info = dict(id=e['id'], type=e['type'], kind=tname, flags=e['flags'], size=len(d))
            if e['type'] == 2:
                w, h, rows, hdr = decode(d, palette=palette)
                write_png(stem + '.png', w, h, rows)
                info.update(width=w, height=h, **hdr)
            elif e['type'] == 4:
                strs = pstrings(d)
                json.dump(strs, open(stem + '.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
                info['strings'] = strs
            elif arch == 'SHARED' and e['type'] == 10:
                open(stem + '.txt', 'w', encoding='utf-8').write(mac_text(d.rstrip(b'\0')))
            elif arch == 'SHARED' and e['type'] == 19:
                info['name'] = mac_text(d.rstrip(b'\0'))
            elif arch == 'SOUND' and e['type'] == 20:
                open(stem + '.mid', 'wb').write(d)
            elif arch == 'SOUND' and e['type'] == 5:
                pcm = decode_sfx(d)
                write_wav(stem + '.wav', pcm)
                info['samples'] = len(pcm)
            open(stem + '.bin', 'wb').write(d)
            entries.append(info)
        manifest[arch] = entries
        print(arch, len(entries), 'resources')

    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
```
{% endraw %}
