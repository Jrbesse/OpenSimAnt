"""Decode HCEGANT type 0 resources: window / dialog layouts.

python layouts.py [id ...]                 print windows (all by default) from extracted/hcegant/layout
python layouts.py --json out.json          write every window as JSON (for the remake's UI)

Layout n is window n, loaded as-is into memory (the window table DS:9230 holds a handle per window id).
An item id is (window << 8) | item index; f_252d8 looks an item's rectangle up through the item table.

Window header (0x2C bytes):
  +00 rect (left, top, right, bottom), screen coordinates (640 x 480)
  +08 u16, u16 (0 so far)
  +0C u16 item count
  +0E u16 resource size
  +10 4 x u16 (0x14 each: margins?), +18.. flags (not decoded)
  +2C item table: per item 4 bytes (offset into the resource, placeholder segment); the loader f_25098
      rebuilds it by walking the records (next = this + its length at +0x22)
Item record:
  +00 rect (absolute), +08 x, y (relative to the window), +0C width, height
  +10 u16 parent id, +12 u16 parent id (the container), +14 u16 own id, +16 u16 own id
  +18 4 x u16 (1, 2, 1, 2 mostly: attachment / resize modes?)
  +20 u8 state (0 normal; other values seen 1, 2, 3)
  +21 u8 type (below), +22 u16 record length (f_2512d: by type)
  +24.. by type; +28 the type's parameter (bitmap id, style); strings NUL-terminated
Types (drawing by f_223b3, sizes by f_2512d):
  0x00 box (style +28, f_22226)        0x02 frame (f_22170)            0x04 scroll bar? (f_241f2, 0x38)
  0x05 / 0x09 text (string +2A)        0x0C framed text button (string +2A)
  0x06 picture (bitmap id +28, f_25c75)                  0x07 / 0x08 icon / check control (f_244cc)
  0x0D two-state picture (+24 bit 2 picks the word +26 or +28)
  0x0F 3-D frame (style +28, f_22248)  0x10 formatted text field (+2C, format string +2E)
  0x11 filled text (string +2E)        0x12 caption (string +2E)
  0x13 / 0x14 / 0x15 / 0x16 frame styles (+28; f_22289, f_2225d, ...)
  0x01 / 0x03 / 0x0A / 0x0B / 0x0E: not drawn (hotspots: buttons over a picture)
Resources 128 / 129 / 131 are UI tables, not windows (129: 24 entries of 4 colour bytes).
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUTS = os.path.join(HERE, '..', 'extracted', 'hcegant', 'layout')

TYPES = {0x00: 'box', 0x01: 'hotspot', 0x02: 'frame', 0x03: 'hotspot', 0x04: 'list', 0x05: 'text',
         0x06: 'picture', 0x07: 'icon', 0x08: 'vscroll', 0x09: 'text', 0x0a: 'hotspot', 0x0b: 'hotspot',
         0x0c: 'text_button', 0x0d: 'toggle_picture', 0x0e: 'hotspot', 0x0f: 'frame3d',
         0x10: 'field', 0x11: 'filled_text', 0x12: 'caption', 0x13: 'frame', 0x14: 'frame', 0x15: 'frame',
         0x16: 'frame'}


def _cstr(b, o):
    e = b.find(b'\0', o)
    return b[o:e if e >= 0 else len(b)].decode('latin-1')


def decode_item(b):
    left, top, right, bottom, x, y, w, h, p1, p2, id1, id2, a1, a2, a3, a4 = struct.unpack_from('<16h', b, 0)
    state, typ, length = b[0x20], b[0x21], struct.unpack_from('<H', b, 0x22)[0]
    it = {'id': id1 & 0xffff, 'rect': [left, top, right, bottom], 'pos': [x, y], 'size': [w, h],
          'parent': [p1 & 0xffff, p2 & 0xffff], 'id2': id2 & 0xffff, 'attach': [a1, a2, a3, a4],
          'state': state, 'type': typ, 'kind': TYPES.get(typ, f'type{typ:02x}'), 'length': length,
          'extra': b[0x24:length].hex()}
    if len(b) >= 0x2a:
        it['param'] = struct.unpack_from('<H', b, 0x28)[0]
    if typ in (0x05, 0x09, 0x0c) and len(b) > 0x2a:
        it['text'] = _cstr(b, 0x2a)
    elif typ in (0x10, 0x11, 0x12) and len(b) > 0x2e:
        it['text'] = _cstr(b, 0x2e)
    if typ == 0x06:
        it['bitmap'] = it['param']
    if typ == 0x0d:
        it['bitmaps'] = list(struct.unpack_from('<2H', b, 0x26))
    return it


def decode(b):
    n = struct.unpack_from('<H', b, 0x0c)[0]
    items, o = [], 0x2c + 4 * n
    offs = [struct.unpack_from('<H', b, 0x2c + 4 * i)[0] for i in range(n)]
    for i in range(n):
        o = offs[i]
        length = struct.unpack_from('<H', b, o + 0x22)[0]
        items.append(decode_item(b[o:o + length]))
    return {'rect': list(struct.unpack_from('<4h', b, 0)), 'size': struct.unpack_from('<H', b, 0x0e)[0],
            'header': b[0x08:0x2c].hex(), 'items': items}


def load(wid):
    b = open(os.path.join(LAYOUTS, f'{wid:05d}.bin'), 'rb').read()
    return decode(b) if len(b) >= 0x2c and wid < 128 else None


def all_ids():
    return sorted(int(f[:5]) for f in os.listdir(LAYOUTS) if f.endswith('.bin'))


def main():
    args = sys.argv[1:]
    if args[:1] == ['--json']:
        out = {wid: load(wid) for wid in all_ids() if wid < 128}
        json.dump(out, open(args[1], 'w'), indent=1)
        print('wrote', args[1])
        return
    for wid in [int(a) for a in args] or all_ids():
        w = load(wid)
        if w is None:
            continue
        print(f'window {wid}: rect {w["rect"]}, {len(w["items"])} items')
        for i, it in enumerate(w['items']):
            extra = ''.join(f' {k}={it[k]!r}' for k in ('bitmap', 'bitmaps', 'text') if k in it)
            print(f'  {i:2d} {it["id"]:04x} {it["kind"]:<14} rect {it["rect"]} parent {it["parent"][0]:04x}/'
                  f'{it["parent"][1]:04x} state {it["state"]} param {it.get("param", 0):#x}{extra}')


if __name__ == '__main__':
    main()
