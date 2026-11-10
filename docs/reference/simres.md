---
layout: default
title: "simres"
permalink: /reference/simres/
---

# simres

*`simres.py` — SimAnt (DOS, Maxis 1991) resource archive reader.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `simres.py`]({{ site.baseurl }}/assets/reference/tools/simres.py)

SimAnt (DOS, Maxis 1991) resource archive reader.

Archive = NAME.NDX (index) + NAME.DAT (data).

NDX layout (little-endian):
    0x00  u16   record count
    0x02  18 bytes zero
    0x14  count x { u32 offset; u16 id; u8 type; u8 flags }
    (trailing bytes are uninitialised slack from the original tool)

DAT layout:
    0x00  u32   magic 0x12345678
    0x04  u16   record count
    0x06  u32   end of data
    0x0A  4 bytes zero
    0x0E  records, each:  u32 magic; u16 0; u32 size; size bytes
          NDX offsets are relative to 0x0E.

flags bit 0: payload is compressed = u16 uncompressed size + Okumura LZSS
             (N=4096, F=18, threshold 2, ring pre-filled with spaces).

## At a glance

- **80** lines
- **3 top-level functions**, including `lzss`, `decompress`, `read_archive`

## Source

{% raw %}
```python
"""SimAnt (DOS, Maxis 1991) resource archive reader.

Archive = NAME.NDX (index) + NAME.DAT (data).

NDX layout (little-endian):
    0x00  u16   record count
    0x02  18 bytes zero
    0x14  count x { u32 offset; u16 id; u8 type; u8 flags }
    (trailing bytes are uninitialised slack from the original tool)

DAT layout:
    0x00  u32   magic 0x12345678
    0x04  u16   record count
    0x06  u32   end of data
    0x0A  4 bytes zero
    0x0E  records, each:  u32 magic; u16 0; u32 size; size bytes
          NDX offsets are relative to 0x0E.

flags bit 0: payload is compressed = u16 uncompressed size + Okumura LZSS
             (N=4096, F=18, threshold 2, ring pre-filled with spaces).
"""
import struct

MAGIC = 0x12345678


def lzss(src, out_len=None, N=4096, F=18, T=2, fill=0x20):
    ring = bytearray([fill]) * N
    r = N - F
    out = bytearray()
    i = 0
    flags = 0
    while i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xff00
            i += 1
            if i >= len(src):
                break
        if flags & 1:
            c = src[i]
            i += 1
            out.append(c)
            ring[r] = c
            r = (r + 1) & (N - 1)
        else:
            if i + 1 >= len(src):
                break
            a, b = src[i], src[i + 1]
            i += 2
            p = a | ((b & 0xf0) << 4)
            for k in range((b & 0x0f) + T + 1):
                c = ring[(p + k) & (N - 1)]
                out.append(c)
                ring[r] = c
                r = (r + 1) & (N - 1)
        if out_len is not None and len(out) >= out_len:
            break
    return bytes(out)


def decompress(raw):
    n = struct.unpack_from('<H', raw, 0)[0]
    return lzss(raw[2:], n)[:n]


def read_archive(base):
    ndx = open(base + '.NDX', 'rb').read()
    dat = open(base + '.DAT', 'rb').read()
    count = struct.unpack_from('<H', ndx, 0)[0]
    res = []
    for i in range(count):
        off, rid, rtype, flags = struct.unpack_from('<IHBB', ndx, 0x14 + i * 8)
        h = 0x0E + off
        magic, _, size = struct.unpack_from('<IHI', dat, h)
        assert magic == MAGIC, (base, i, hex(off))
        raw = dat[h + 10:h + 10 + size]
        data = decompress(raw) if flags & 1 else raw
        res.append(dict(index=i, id=rid, type=rtype, flags=flags, raw=raw, data=data))
    return res
```
{% endraw %}
