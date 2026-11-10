"""Render every window layout (HCEGANT type 0) to a PNG: pictures at their item rectangles, other items as
outlines (frames dark grey, hotspots blue, text items red, with no text: the fonts are not decoded).

python render_windows.py [out_dir]          (default extracted/render/windows)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bitmaps                                    # noqa: E402
import layouts                                    # noqa: E402
import tiles                                      # noqa: E402
from png import write_png                         # noqa: E402

OUTLINE = {'frame': (64, 64, 64), 'frame3d': (64, 64, 64), 'box': (64, 64, 64), 'hotspot': (0, 0, 255),
           'caption': (255, 0, 0), 'text': (255, 0, 0), 'field': (255, 0, 0), 'filled_text': (255, 0, 0),
           'text_button': (255, 0, 255), 'list': (0, 160, 0), 'icon': (0, 160, 160),
           'vscroll': (0, 160, 160), 'toggle_picture': (0, 160, 160)}


def render_window(wid, path, pal):
    w = layouts.load(wid)
    if w is None:
        return False
    wl, wt, wr, wb = w['rect']
    img = [[(192, 192, 192, 255)] * (wr - wl + 1) for _ in range(wb - wt + 1)]

    def plot(x, y, c):
        if 0 <= y - wt < len(img) and 0 <= x - wl < len(img[0]):
            img[y - wt][x - wl] = c
    for it in w['items']:
        l, t, r, b = it['rect']
        rid = it.get('bitmap') or (it.get('bitmaps') or [0])[0]
        p = os.path.join(tiles.EXTRACTED, 'bitmap', f'{rid:05d}.bin') if rid else None
        if p and os.path.exists(p):
            bw, bh, rows, _ = bitmaps.decode(open(p, 'rb').read(), palette=pal)
            for y in range(bh):
                for x in range(bw):
                    if rows[y][x][3]:
                        plot(l + x, t + y, tuple(rows[y][x]))
            continue
        c = OUTLINE.get(it['kind'], (128, 128, 0)) + (255,)
        for x in range(l, r):
            plot(x, t, c)
            plot(x, b - 1, c)
        for y in range(t, b):
            plot(l, y, c)
            plot(r - 1, y, c)
        if it.get('text'):
            draw_text(img, it, wl, wt)
    write_png(path, len(img[0]), len(img), img)
    return True


_fonts = {}


def draw_text(img, it, wl, wt, rgb=(0, 0, 0, 255)):
    """f_21fa2: font = the byte at +28 (f_24d5d), alignment = (word +24 & 0x180) >> 7: 0 / 3 centred
    ((left + right - width) / 2), 1 left + 4, 2 right - width - 4, never left of `left`; vertically
    centred, y = (top + bottom - font height) / 2 (3 also underlines). Strings with % are printf formats
    filled at run time (drawn as is). Colour (+26?) not decoded: black."""
    from fonts import Font
    extra = bytes.fromhex(it['extra'])
    fid = extra[4] if len(extra) > 4 else 0
    if fid not in _fonts:
        try:
            _fonts[fid] = Font(fid)
        except (OSError, ValueError):
            _fonts[fid] = None
    f = _fonts[fid]
    if f is None:
        return
    align = ((extra[0] | extra[1] << 8) & 0x180) >> 7 if len(extra) > 1 else 0
    l, t, r, b = it['rect']
    w = f.width(it['text'])
    x = {1: l + 4, 2: r - w - 4}.get(align, (l + r - w) // 2)
    x = max(x, l)
    y = (t + b - f.height) // 2
    f.draw(img, x - wl, y - wt, it['text'], rgb)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'extracted', 'render', 'windows')
    os.makedirs(out, exist_ok=True)
    pal = tiles.palette()
    for wid in layouts.all_ids():
        if render_window(wid, os.path.join(out, f'window_{wid:02d}.png'), pal):
            print('window', wid)


if __name__ == '__main__':
    main()
