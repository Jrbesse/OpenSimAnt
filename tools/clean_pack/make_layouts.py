"""Writes docs/clean_pack/data/window_layouts.json, the window layouts (HCEGANT type 0) as functional data, from the player's
own pack (local only; the JSON holds numbers and ids, and none of the original's words):

    python tools/clean_pack/make_layouts.py [remake/build/original_pack.zip]

- "windows": for each window 0..33 (docs/clean_pack/layouts.md): "rect" (left, top, right, bottom on the 640 x 480 screen),
  "requested" (the rectangle it was last opened at, which mode-5 edges use), "flags" (the decorations), "misc" (the header's
  other non-zero words by byte offset), "items": one object per item, in order (an item's id is window << 8 | its index):
  "rect" (as last solved), "off" (the four edges' offsets), "ref" (the item each edge hangs off, window << 8 | index), "mode"
  (how each edge is solved), "state", "type", "flags", "scheme", "alt", "tail" (the type's own bytes from +28: font or
  thickness, a bitmap id, the list's fields), and for a text item "text": {"format": the printf format the code fills}, {"literal":
  a drive letter} or {"key": "<window>.<item>"}, the words of a maker (src/layouts/texts.json).
- "tables": the three UI tables 128, 129 (the 16 colour schemes of 6 bytes) and 131 as byte lists.
- "texts": for each key the room of the new words: font, alignment, whether the item clips, its rectangle, the room in pixels
  and how many characters the original's words had (a measurement, not the words).
build.py encodes them back (enc_layout); the bytes the game never reads (the item table's memory segments, the padding behind
each string, editor debris in a few layouts) are not stored.
"""
import json, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B


def line(obj):
    return json.dumps(obj, separators=(',', ':'))


def main():
    pack = sys.argv[1] if len(sys.argv) > 1 else os.path.join(B.ROOT, 'remake', 'build', 'original_pack.zip')
    z = zipfile.ZipFile(pack)
    windows, texts = {}, {}
    for wid in B.LAYOUT_WINDOWS:
        d = z.read('HCEGANT/0/%d.bin' % wid)
        win, strings, dead, infos = B.layout_entry(wid, d)
        assert B.enc_layout(win, strings, dead) == d, 'layout %d does not round trip' % wid
        windows[wid] = win
        texts.update(infos)
    tables = {tid: list(z.read('HCEGANT/0/%d.bin' % tid)) for tid in B.LAYOUT_TABLES}
    out = ['{', ' "windows": {']
    for wid, win in sorted(windows.items()):
        head = {k: v for k, v in win.items() if k != 'items'}
        out.append('  "%d": %s,' % (wid, line(head)[:-1]))
        out.append('   "items": [')
        out += ['    %s%s' % (line(it), ',' if i + 1 < len(win['items']) else '') for i, it in enumerate(win['items'])]
        out.append('   ]}%s' % (',' if wid != max(windows) else ''))
    out += [' },', ' "tables": {']
    out += ['  "%d": %s%s' % (tid, line(t), ',' if tid != max(tables) else '') for tid, t in sorted(tables.items())]
    out += [' },', ' "texts": {']
    keys = sorted(texts, key=lambda k: tuple(int(p) for p in k.split('.')))
    out += ['  "%s": %s%s' % (k, line(texts[k]), ',' if k != keys[-1] else '') for k in keys]
    out += [' }', '}']
    path = os.path.join(B.DATA, 'window_layouts.json')
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('%d windows (%d items), %d tables, %d texts -> %s' % (len(windows), sum(len(w['items']) for w in windows.values()), len(tables), len(texts), path))


if __name__ == '__main__':
    main()
