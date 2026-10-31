"""preview.py: builds preview.png (contact sheet, windows assembled as the game shows them, inverted states)."""
import numpy as np
from PIL import Image, ImageDraw
from uilib import RGB, T

PAL = {i: tuple(int(RGB[i][k:k + 2], 16) for k in (0, 2, 4)) for i in range(16)}
MID = (110, 110, 120)
MAG = (255, 0, 255)


def to_pil(img, scale=1, bg=None):
    a = img.a
    out = np.zeros(a.shape + (3,), dtype=np.uint8)
    for i in range(16):
        out[a == i] = PAL[i]
    if (a == T).any():
        out[a == T] = bg or MAG
    im = Image.fromarray(out)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale != 1 else im


def compose(base, overlay, ox, oy, size, backdrop=None):
    """base placed at (bx, by) is given as (img, x, y) list; overlay drawn after."""
    pass


def sheet(items, width, scale, pad=6, bg=MID):
    """Shelf-pack PIL images, return the canvas."""
    x = y = pad
    rowh = 0
    pos = []
    for im in items:
        w, h = im.size
        if x + w + pad > width:
            x, y, rowh = pad, y + rowh + pad, 0
        pos.append((x, y))
        x += w + pad
        rowh = max(rowh, h)
    canvas = Image.new('RGB', (width, y + rowh + pad), bg)
    for im, p in zip(items, pos):
        canvas.paste(im, p)
    return canvas


def checker(w, h, a=(120, 100, 60), b=(105, 88, 50)):
    im = Image.new('RGB', (w, h), a)
    d = ImageDraw.Draw(im)
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            if (x // 8 + y // 8) % 2:
                d.rectangle([x, y, x + 7, y + 7], fill=b)
    return im


def window(base_items, overlay, size, scale):
    """base_items: [(img, x, y)], overlay: (img, x, y) or None; the map area is a brown check."""
    im = checker(*size)
    for img, x, y in base_items:
        im.paste(to_pil(img), (x, y))
    if overlay:
        o = to_pil(overlay[0], bg=None)
        a = np.array(overlay[0].a != T)
        mask = Image.fromarray((a * 255).astype(np.uint8))
        im.paste(o, (overlay[1], overlay[2]), mask)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def inverted_pairs(reg, scale=2):
    from uilib import inv
    items = []
    seen = set()
    for bid, r, face, ink, what in reg.inv:
        key = (bid, r)
        if key in seen or (r[2] - r[0]) > 120:
            continue
        seen.add(key)
        img = reg.img[bid]
        a = to_pil(img.crop(*r), scale)
        b = to_pil(inv(img, *r).crop(*r), scale)
        pair = Image.new('RGB', (a.width * 2 + 4, a.height), MID)
        pair.paste(a, (0, 0))
        pair.paste(b, (a.width + 4, 0))
        items.append(pair)
    return items


def make(reg, path, sections=None):
    secs = {}
    ids = sorted(reg.img)
    secs['sheet'] = sheet([to_pil(reg.img[i], 2) for i in ids if reg.img[i].w <= 330], 1500, 2)
    wins = []
    I = reg.img
    if 15000 in I and 15001 in I:
        wins.append(window([(I[15000], 0, 1)], (I[15001], 10, 0), (190, 262), 3))
    if 14000 in I and 14001 in I:
        wins.append(window([(I[14000], 0, 89)], (I[14001], 0, 0), (512, 135), 2))
    for i in (13000, 16100, 14002):
        if i in I:
            wins.append(to_pil(I[i], 2))
    for base, ov, off, size in ((4600, 4601, (40, 2), (210, 170)), (4620, 4621, (35, -1), (210, 170)),
                                (16000, 16001, (45, 20), (320, 179))):
        if base in I and ov in I:
            wins.append(window([(I[base], 0, 0)], (I[ov], off[0], off[1]), size, 2))
    if 16200 in I and 16210 in I:
        from uilib import Img
        pic = I[16200].copy()
        for k, (x, y) in enumerate([(72, 74), (87, 66), (175, 64), (191, 66), (159, 122), (179, 124)]):
            e = I[16210 + k % 3]
            for yy in range(13):
                for xx in range(13):
                    if e.a[yy, xx] != T:
                        pic.a[y + yy, x + xx] = e.a[yy, xx]
        wins.append(to_pil(pic, 2))
    secs['windows'] = sheet(wins, 1700, 2)
    secs['inverted'] = sheet(inverted_pairs(reg), 1500, 2)
    W = max(s.width for s in secs.values())
    H = sum(s.height for s in secs.values())
    full = Image.new('RGB', (W, H), MID)
    y = 0
    for k in ('sheet', 'windows', 'inverted'):
        full.paste(secs[k], (0, y))
        y += secs[k].height
    full.save(path)
    if sections:   # optional: also save the three sections separately (for looking at one part)
        base = path.rsplit('.', 1)[0]
        for k, s in secs.items():
            s.save('%s_%s.png' % (base, k))
    return full
