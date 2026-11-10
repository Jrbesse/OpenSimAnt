---
layout: default
title: "segmap"
permalink: /reference/segmap/
---

# segmap

*`segmap.py` — Map which functions read/write which offsets of a far data segment (default: 0x3e1d sim state).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `segmap.py`]({{ site.baseurl }}/assets/reference/re/segmap.py)

Map which functions read/write which offsets of a far data segment (default: 0x3e1d sim state).

Linear-sweeps all code (resident image + every overlay at its flat base), tracks `mov es, [DS:x]`
where DS:x holds the target segment, and records es:-prefixed memory operands.
Output: build/segmap_<seg>.tsv  (offset, access, func, insn_addr, insn)

## At a glance

- **87** lines
- **1 top-level functions**, including `seg_of`

## Source

{% raw %}
```python
"""Map which functions read/write which offsets of a far data segment (default: 0x3e1d sim state).

Linear-sweeps all code (resident image + every overlay at its flat base), tracks `mov es, [DS:x]`
where DS:x holds the target segment, and records es:-prefixed memory operands.
Output: build/segmap_<seg>.tsv  (offset, access, func, insn_addr, insn)
"""
import json, struct, sys, collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_16
from capstone.x86 import X86_OP_MEM, X86_REG_ES
from mz import DGROUP

TARGET = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x3e1d
flat = open('build/flat.bin', 'rb').read()
lay = json.load(open('build/layout.json'))
segvars = {i for i in range(0, 0x10000, 2) if struct.unpack_from('<H', flat, DGROUP * 16 + i)[0] == TARGET}

md = Cs(CS_ARCH_X86, CS_MODE_16)
md.detail = True
md.skipdata = True
from funcstarts import find_starts
STARTS = find_starts(flat)

regions = [(0x0000, 0x0, 0x2cff0)]  # (seg, start linear, end linear) resident code (before overlay mgr)
for o in lay['overlays']:
    regions.append((o['base'], o['base'] * 16, o['base'] * 16 + o['size']))


def seg_of(lin, rseg):
    return rseg


rows = []
for rseg, lo, hi in regions:
    es_ok = False
    func = None
    # sweep in 64K-or-smaller chunks addressed relative to a paragraph base
    base = lo
    while base < hi:
        cseg = base >> 4
        chunk = flat[base:min(hi, base + 0xfff0)]
        last = 0
        prev = b''
        regimm = {}
        for ins in md.disasm(chunk, 0):
            lin = base + ins.address
            last = ins.address + ins.size
            if ins.id == 0:
                es_ok = False
                continue
            b = ins.bytes
            if lin in STARTS:
                func = lin
                es_ok = False
            prev = bytes(b)
            if ins.mnemonic == 'mov' and len(ins.operands) == 2:
                d, s = ins.operands
                if d.type == 1 and s.type == 2:
                    regimm[d.reg] = s.imm & 0xffff
                if d.type == 1 and d.reg == X86_REG_ES and s.type == 1:
                    es_ok = regimm.get(s.reg) == TARGET
                    continue
                if d.type == 1 and d.reg == X86_REG_ES:
                    es_ok = s.type == X86_OP_MEM and s.mem.base == 0 and s.mem.index == 0 and md.reg_name(s.mem.segment) in (None, 'ds') and (s.mem.disp & 0xffff) in segvars
                    continue
            if ins.mnemonic in ('les', 'pop') and ins.op_str.startswith(('es', 'bx') if False else ()):
                pass
            if ins.mnemonic == 'les' or (ins.mnemonic == 'pop' and ins.op_str == 'es'):
                es_ok = False
            if ins.mnemonic in ('call', 'lcall', 'ret', 'retf'):
                if ins.mnemonic in ('call', 'lcall'):
                    es_ok = False
            if not es_ok:
                continue
            for i, op in enumerate(ins.operands):
                if op.type == X86_OP_MEM and op.mem.segment == X86_REG_ES:
                    acc = 'W' if i == 0 and ins.mnemonic not in ('cmp', 'test', 'push') else 'R'
                    idx = '+'.join(md.reg_name(r) for r in (op.mem.base, op.mem.index) if r)
                    rows.append((op.mem.disp & 0xffff, acc, func or 0, lin, f'{ins.mnemonic} {ins.op_str}', idx))
        base += max(16, (last // 16) * 16) if last else 0xfff0

with open(f'build/segmap_{TARGET:04x}.tsv', 'w') as f:
    for r in sorted(rows):
        f.write(f'{r[0]:04x}\t{r[1]}\t{r[2]:05x}\t{r[3]:05x}\t{r[5]}\t{r[4]}\n')
byoff = collections.defaultdict(set)
for r in rows:
    byoff[r[0]].add(r[2])
print(len(rows), 'accesses,', len(byoff), 'distinct offsets,', len({r[2] for r in rows}), 'functions')
```
{% endraw %}
