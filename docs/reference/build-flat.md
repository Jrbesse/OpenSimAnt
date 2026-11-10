---
layout: default
title: "build_flat"
permalink: /reference/build-flat/
---

# build_flat

*`build_flat.py` — Build a flat real-mode memory image of SIMANT.EXE for analysis and emulation.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `build_flat.py`]({{ site.baseurl }}/assets/reference/re/build_flat.py)

Build a flat real-mode memory image of SIMANT.EXE for analysis and emulation.

Layout (segment = paragraph, load base 0):
  0000-3125  resident MZ image (overlay manager, C runtime, part of the game)
  3126-35f4  overlay swap area 1, holding section 2 (resident, flags 5)
  35f5-3d56  other swap areas (left empty here)
  3d57-60xx  resident section 29: sim state, far data, DGROUP (0x55b3)
  6200-....  every swappable overlay at its own unique base, relocations rebased

Patches applied to the image:
  * overlay call vectors (e8 <mgr>; ea off seg; u16 n) jump straight to the rebased overlay, and the
    `call mgr` is replaced by NOPs (everything is resident in this image). Vector n -> section n + 2.
  * far calls to MSC _chkstk (29f4:02cc, SP -= AX) become `sub sp,ax` + NOPs so decompilers and
    emulators don't need the runtime stack checker.

Writes build/flat.bin, build/layout.json and build/SIMFLAT.EXE (synthetic MZ with merged relocations,
for Ghidra's DOS loader).

## At a glance

- **114** lines

## Source

{% raw %}
```python
"""Build a flat real-mode memory image of SIMANT.EXE for analysis and emulation.

Layout (segment = paragraph, load base 0):
  0000-3125  resident MZ image (overlay manager, C runtime, part of the game)
  3126-35f4  overlay swap area 1, holding section 2 (resident, flags 5)
  35f5-3d56  other swap areas (left empty here)
  3d57-60xx  resident section 29: sim state, far data, DGROUP (0x55b3)
  6200-....  every swappable overlay at its own unique base, relocations rebased

Patches applied to the image:
  * overlay call vectors (e8 <mgr>; ea off seg; u16 n) jump straight to the rebased overlay, and the
    `call mgr` is replaced by NOPs (everything is resident in this image). Vector n -> section n + 2.
  * far calls to MSC _chkstk (29f4:02cc, SP -= AX) become `sub sp,ax` + NOPs so decompilers and
    emulators don't need the runtime stack checker.

Writes build/flat.bin, build/layout.json and build/SIMFLAT.EXE (synthetic MZ with merged relocations,
for Ghidra's DOS loader).
"""
import json
import os
import re
import struct

from mz import MEM, SECTIONS, DGROUP, RELOCS as RELOCS_ROOT, EXE

AREAS = sorted({s['seg'] for s in SECTIONS if not s['flags'] & 1})
AREA_END = {a: (AREAS[i + 1] if i + 1 < len(AREAS) else 0x3d57) for i, a in enumerate(AREAS)}
SEC2_AREA = (0x3126, 0x35f5)

out = bytearray(MEM)
layout = dict(dgroup=DGROUP, overlays=[])

# ---- swappable overlays at unique bases
nxt = 0x6200
for s in SECTIONS:
    if s['flags'] & 1:
        continue
    A, E, N = s['seg'], AREA_END[s['seg']], nxt
    data = bytearray(s['data'])
    for off, seg in s['relocs']:
        loc = seg * 16 + off - A * 16
        w = struct.unpack_from('<H', data, loc)[0]
        if A <= w < E:
            struct.pack_into('<H', data, loc, w - A + N)
    end = N * 16 + len(data)
    if len(out) < end:
        out.extend(bytes(end - len(out)))
    out[N * 16:end] = data
    layout['overlays'].append(dict(idx=s['idx'], area=A, base=N, size=len(data)))
    nxt = N + (s['msize'] + 15) // 16 + 1

# ---- overlay-manager call vectors
base_of = {o['idx']: o for o in layout['overlays']}
vectors = []
for v in range(0x2cff0, 0x31250):
    if out[v] != 0xe8 or out[v + 3] != 0xea:
        continue
    off, seg, n = struct.unpack_from('<HHH', out, v + 4)
    o = base_of.get(n + 2)
    if o and o['area'] <= seg < AREA_END[o['area']]:
        nseg = seg - o['area'] + o['base']
        struct.pack_into('<HH', out, v + 4, off, nseg)
        vectors.append(dict(vec=v, ovl=n + 2, target=nseg * 16 + off))
        out[v:v + 3] = b'\x90\x90\x90'
    elif n in (0xffff, 0) and (seg < 0x3126 or SEC2_AREA[0] <= seg < SEC2_AREA[1]):
        vectors.append(dict(vec=v, ovl=n, target=seg * 16 + off))
        out[v:v + 3] = b'\x90\x90\x90'
layout['vectors'] = vectors
print(len(vectors), 'overlay vectors patched')

# ---- _chkstk
CHK = bytes.fromhex('9acc02f429')
chk_sites = [m.start() for m in re.finditer(re.escape(CHK), bytes(out))]
for a in chk_sites:
    if out[a - 3] == 0xb8:                    # mov ax, N ; call _chkstk  ->  sub sp, N ; 4 x nop
        out[a - 3:a + 5] = b'\x81\xec' + bytes(out[a - 2:a]) + b'\x90' * 4
    elif out[a - 2:a] == b'\x33\xc0':         # xor ax, ax ; call _chkstk  ->  7 x nop
        out[a - 2:a + 5] = b'\x90' * 7
    else:
        out[a:a + 5] = bytes.fromhex('2be0909090')
CHK_RELOCS = {a + 3 for a in chk_sites}
print(len(chk_sites), '_chkstk calls replaced')

os.makedirs('build', exist_ok=True)
open('build/flat.bin', 'wb').write(out)
json.dump(layout, open('build/layout.json', 'w'), indent=1)
print('flat size', hex(len(out)), 'last seg', hex(nxt))

# ---- synthetic MZ so Ghidra's DOS loader derives segments from relocations
rel = set((o, s) for o, s in RELOCS_ROOT)
for s in SECTIONS:
    if s['flags'] & 1:
        rel.update(s['relocs'])
for s, lay in zip([x for x in SECTIONS if not x['flags'] & 1], layout['overlays']):
    A, N = s['seg'], lay['base']
    for off, seg in s['relocs']:
        lin = seg * 16 + off - A * 16 + N * 16
        rel.add((lin & 0xf, lin >> 4))
rel = [r for r in rel if r[1] * 16 + r[0] not in CHK_RELOCS]
rel = sorted(rel, key=lambda r: r[1] * 16 + r[0])
hdr_len = (0x1c + 4 * len(rel) + 511) // 512 * 512
total = hdr_len + len(out)
hdr = bytearray(hdr_len)
orig = struct.unpack_from('<14H', EXE, 2)
struct.pack_into('<2s13H', hdr, 0, b'MZ', total % 512, (total + 511) // 512, len(rel), hdr_len // 16,
                 0x100, 0xffff, orig[6], orig[7], 0, orig[9], orig[10], 0x1c, 0)
for i, (o, s) in enumerate(rel):
    struct.pack_into('<HH', hdr, 0x1c + 4 * i, o, s)
open('build/SIMFLAT.EXE', 'wb').write(hdr + out)
# linear addresses of every segment word that a DOS loader would relocate (for emu.py)
open('build/relocs.bin', 'wb').write(b''.join(struct.pack('<I', s * 16 + o) for o, s in rel))
layout['entry'] = dict(cs=orig[10], ip=orig[9], ss=orig[6], sp=orig[7])
json.dump(layout, open('build/layout.json', 'w'), indent=1)
print('synthetic MZ', len(rel), 'relocs', total, 'bytes')
```
{% endraw %}
