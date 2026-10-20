"""Compare two 640 x 480 screenshots (the original's from screens.py, the remake's from its --screenshot flag).

    python pngdiff.py a.png b.png [l t r b] [--out diff.png]

Prints how many pixels differ in the rectangle (default: the whole screen), the bounding box of the differences
and the most common (colour a, colour b) pairs; --out writes a PNG with the differing pixels in magenta.
"""
import collections
import struct
import sys
import zlib


def read_png(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    pos, idat, w = 8, bytearray(), 0
    while pos < len(data):
        n, tag = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if tag == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
            assert depth == 8 and ctype in (2, 6), (path, depth, ctype)
            bpp = 3 if ctype == 2 else 4
        elif tag == b'IDAT':
            idat += body
        pos += 12 + n
    raw = zlib.decompress(bytes(idat))
    stride = w * bpp
    rows, prev = [], bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x * bpp:x * bpp + 3]) for x in range(w)])
        prev = line
    return w, h, rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = None
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
        args = [a for a in args if a != out]
    wa, ha, ra = read_png(args[0])
    wb, hb, rb = read_png(args[1])
    l, t, r, b = (int(v) for v in args[2:6]) if len(args) >= 6 else (0, 0, min(wa, wb), min(ha, hb))
    diff, pairs = [], collections.Counter()
    for y in range(t, b):
        for x in range(l, r):
            if ra[y][x] != rb[y][x]:
                diff.append((x, y))
                pairs[(ra[y][x], rb[y][x])] += 1
    print(f'{len(diff)} of {(r - l) * (b - t)} pixels differ in ({l}, {t}) .. ({r}, {b})')
    if diff:
        xs, ys = [d[0] for d in diff], [d[1] for d in diff]
        print(f'bounding box ({min(xs)}, {min(ys)}) .. ({max(xs)}, {max(ys)})')
        for (ca, cb), n in pairs.most_common(10):
            print(f'  {n:7d}  {ca} vs {cb}')
    if out:
        sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__file__), '..'))
        from png import write_png
        ds = set(diff)
        rows = [[(255, 0, 255, 255) if (x, y) in ds else ra[y][x] + (255,) for x in range(wa)] for y in range(ha)]
        write_png(out, wa, ha, rows)


if __name__ == '__main__':
    main()
