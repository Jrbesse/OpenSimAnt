---
layout: default
title: "callgraph"
permalink: /reference/callgraph/
---

# callgraph

*`callgraph.py` — Direct call graph (near e8 + far 9a) over resident code and overlays. Writes build/calls.tsv (caller_func, site, target).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `callgraph.py`]({{ site.baseurl }}/assets/reference/re/callgraph.py)

Direct call graph (near e8 + far 9a) over resident code and overlays. Writes build/calls.tsv (caller_func, site, target).

## At a glance

- **41** lines

## Source

{% raw %}
```python
"""Direct call graph (near e8 + far 9a) over resident code and overlays. Writes build/calls.tsv (caller_func, site, target)."""
import json, struct, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_16

flat = open('build/flat.bin', 'rb').read()
lay = json.load(open('build/layout.json'))
md = Cs(CS_ARCH_X86, CS_MODE_16)
md.skipdata = True
from funcstarts import find_starts
STARTS = find_starts(flat)
regions = [(0x0, 0x2cff0)] + [(o['base'] * 16, o['base'] * 16 + o['size']) for o in lay['overlays']]
edges = []
funcs = set()
for lo, hi in regions:
    base = lo
    func = None
    while base < hi:
        chunk = flat[base:min(hi, base + 0xfff0)]
        prev = b''
        last = 0
        for ins in md.disasm(chunk, 0):
            lin = base + ins.address
            last = ins.address + ins.size
            b = bytes(ins.bytes)
            if lin in STARTS:
                func = lin
                funcs.add(func)
            prev = b
            if ins.id == 0:
                continue
            if b[0] == 0xe8 and len(b) == 3:
                rel = struct.unpack('<h', b[1:])[0]
                edges.append((func, lin, lin + 3 + rel))
            elif b[0] == 0x9a and len(b) == 5:
                off, seg = struct.unpack('<HH', b[1:])
                edges.append((func, lin, seg * 16 + off))
        base += (last // 16) * 16 if last >= 16 else 0xfff0
with open('build/calls.tsv', 'w') as f:
    for c, s, t in edges:
        f.write(f'{c or 0:05x}\t{s:05x}\t{t:05x}\n')
print(len(edges), 'calls,', len(funcs), 'functions')
```
{% endraw %}
