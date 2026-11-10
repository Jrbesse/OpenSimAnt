"""Decode SimAnt type-2 bitmap resources.

Header (12 bytes, LE): u16 mode; u8 planes; u8 flags; u32 size; u16 width; u16 height
  mode 0 -> plain planes, mode 3 -> an extra leading mask plane per row.
Pixel data: raw, row-interleaved planes, rowbytes = ceil(width/8), MSB = leftmost pixel.
"""
import struct

EGA = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
       (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255), (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255)]


def decode(d, palette=EGA, plane_order=(0, 1, 2, 3)):
    mode, planes, flags, size, w, h = struct.unpack_from('<HBBIHH', d, 0)
    rb = (w + 7) // 8
    masked = mode == 3
    np = planes + (1 if masked else 0)
    px = d[12:]
    rows = []
    for y in range(h):
        base = y * rb * np
        pl = [px[base + p * rb: base + (p + 1) * rb] for p in range(np)]
        row = []
        for x in range(w):
            bit = 0x80 >> (x & 7)
            bx = x >> 3
            if planes == 1:
                # Mac convention: 1 = black ink
                v = pl[0][bx] & bit if bx < len(pl[0]) else 0
                row.append((0, 0, 0, 255) if v else (255, 255, 255, 255))
                continue
            cp = pl[1:] if masked else pl
            c = 0
            for i, p in enumerate(plane_order):
                if bx < len(cp[p]) and cp[p][bx] & bit:
                    c |= 1 << i
            a = 255
            if masked and not (pl[0][bx] & bit):
                a = 0
            row.append(palette[c] + (a,))
        rows.append(row)
    return w, h, rows, dict(mode=mode, planes=planes, flags=flags, size=size)
