---
layout: default
title: "png"
permalink: /reference/png/
---

# png

*`png.py` — Minimal dependency-free RGBA PNG writer.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `png.py`]({{ site.baseurl }}/assets/reference/tools/png.py)

Minimal dependency-free RGBA PNG writer.

## At a glance

- **22** lines
- **1 top-level functions**, including `write_png`

## Source

{% raw %}
```python
"""Minimal dependency-free RGBA PNG writer."""
import struct
import zlib


def write_png(path, width, height, rgba_rows):
    """rgba_rows: list of rows, each a list of (r, g, b, a) tuples."""
    raw = bytearray()
    for row in rgba_rows:
        raw.append(0)
        for px in row:
            raw.extend(px)

    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(raw), 9)))
        f.write(chunk(b'IEND', b''))
```
{% endraw %}
