---
layout: default
title: "mz"
permalink: /reference/mz/
---

# mz

*`mz.py` — Helpers for reverse-engineering SIMANT.EXE (16-bit MZ, load base segment 0).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `mz.py`]({{ site.baseurl }}/assets/reference/re/mz.py)

Helpers for reverse-engineering SIMANT.EXE (16-bit MZ, load base segment 0).

## At a glance

- **93** lines
- **6 top-level functions**, including `lin`, `dis`, `_sections`, `overlay_mem`, `ds_str`, `find_imm16`

## Source

{% raw %}
```python
"""Helpers for reverse-engineering SIMANT.EXE (16-bit MZ, load base segment 0)."""
import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_16

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
EXE = open(os.path.join(ROOT, 'SIMANT.EXE'), 'rb').read()
HDR = struct.unpack_from('<H', EXE, 8)[0] * 16
NREL = struct.unpack_from('<H', EXE, 6)[0]
RELOCS = [struct.unpack_from('<HH', EXE, 0x1e + 4 * i) for i in range(NREL)]
IMG_END = (struct.unpack_from('<H', EXE, 4)[0] - 1) * 512 + struct.unpack_from('<H', EXE, 2)[0]
IMG = bytearray(EXE[HDR:IMG_END])
RELOC_SET = set(s * 16 + o for o, s in RELOCS)
md = Cs(CS_ARCH_X86, CS_MODE_16)
md.detail = False


def lin(seg, off):
    return seg * 16 + off


def dis(seg, off, n=40, mem=None, stop_ret=False):
    mem = IMG if mem is None else mem
    base = lin(seg, off)
    out = []
    for ins in md.disasm(bytes(mem[base:base + n * 8]), off):
        r = ''
        if any((lin(seg, ins.address) + k) in RELOC_SET for k in range(ins.size)):
            r = '  ; reloc'
        out.append(f'{seg:04x}:{ins.address:04x}  {ins.bytes.hex():<14} {ins.mnemonic} {ins.op_str}{r}')
        if len(out) >= n or (stop_ret and ins.mnemonic in ('ret', 'retf', 'iret')):
            break
    return '\n'.join(out)


# ---- overlay sections (third-party overlay manager, 'eov000x' errors) ----
OVL_TABLE = 0x2db4e  # first record's seg field is at 0x2db62-? ; parsed by scanning ff ff markers
DGROUP = 0x55b3


def _sections():
    secs = []
    for q in range(0x2db40, 0x2dd70):
        if IMG[q] == 0xff and IMG[q + 1] == 0xff:
            idx, fsize = struct.unpack_from('<HH', IMG, q + 2)
            seg, _mgr, pos, _z, fl, msize, nrel = struct.unpack_from('<HHHBBHH', IMG, q - 12)
            fpos = pos * 16
            rel = [struct.unpack_from('<HH', EXE, fpos + 4 * i) for i in range(nrel)]
            dstart = fpos + ((nrel * 4 + 15) // 16) * 16
            secs.append(dict(idx=idx, seg=seg, flags=fl, msize=msize * 16, fsize=fsize * 16,
                             relocs=rel, data=EXE[dstart:dstart + fsize * 16]))
    return secs


SECTIONS = _sections()
RESIDENT = [s for s in SECTIONS if s['flags'] & 1]
MEM = bytearray(0x62000)
MEM[0:len(IMG)] = IMG
for s in RESIDENT:
    MEM[s['seg'] * 16:s['seg'] * 16 + len(s['data'])] = s['data']
    for o, sg in s['relocs']:
        RELOC_SET.add(sg * 16 + o)


def overlay_mem(idx):
    """Flat memory with swap overlay `idx` loaded into its area."""
    s = [x for x in SECTIONS if x['idx'] == idx][0]
    m = bytearray(MEM)
    m[s['seg'] * 16:s['seg'] * 16 + len(s['data'])] = s['data']
    return m


def ds_str(off, mem=None):
    mem = MEM if mem is None else mem
    a = DGROUP * 16 + off
    e = mem.index(0, a)
    return mem[a:e].decode('latin1')


def find_imm16(value, mem=None, lo=0, hi=None):
    """Code locations that load/push imm16 `value` (mov r16,imm / push imm / mov [m],imm)."""
    import re
    mem = MEM if mem is None else mem
    hi = len(mem) if hi is None else hi
    v = struct.pack('<H', value)
    hits = []
    for m in re.finditer(re.escape(v), bytes(mem[lo:hi])):
        a = lo + m.start()
        op = mem[a - 1]
        if 0xb8 <= op <= 0xbf or op == 0x68:
            hits.append(a - 1)
        elif a >= 2 and mem[a - 2] == 0xc7:
            hits.append(a - 2)
    return hits
```
{% endraw %}
