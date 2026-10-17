"""Annotated disassembly of a function in build/flat.bin.

python adis.py <flat_hex_addr|name> [max_insns]
Resolves `mov es,[segvar]` to named segments, names sim arrays / globals from symbols.json,
names call targets, and shows DS string literals.
"""
import json, re, struct, sys, bisect, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_16
from capstone.x86 import X86_OP_MEM, X86_OP_REG, X86_OP_IMM

HERE = os.path.dirname(os.path.abspath(__file__))
flat = open(os.path.join(HERE, 'build/flat.bin'), 'rb').read()
SYM = json.load(open(os.path.join(HERE, 'symbols.json')))
DG = 0x55b3
SEGNAME = {int(k, 16): v for k, v in SYM['segments'].items()}
FUNCS = {int(k, 16): v for k, v in SYM['funcs'].items()}
NAME2F = {v: k for k, v in FUNCS.items()}

DATA = {}
for k, v in SYM['data'].items():
    sn, off = k.split(':')
    m = re.search(r'\[(.+)\]', v)
    size = eval(m.group(1)) if m else 2
    DATA.setdefault(sn, []).append((int(off, 16), size, v.split('[')[0]))
for sn in DATA:
    DATA[sn].sort()

# function starts from prologues + far-call targets
from funcstarts import find_starts
starts = find_starts(flat)
calls = [l.split() for l in open(os.path.join(HERE, 'build/calls.tsv'))]
for c, s, t in calls:
    starts.add(int(t, 16))
starts = sorted(starts)
segbases = set()
for m in re.finditer(rb'\x9a(..)(..)', flat, re.S):
    off, seg = struct.unpack('<HH', m.group(1) + m.group(2))
    if seg * 16 + off < len(flat) and seg * 16 + off in set():
        pass
for c, s, t in calls:
    pass


def segvar(off):
    v = struct.unpack_from('<H', flat, DG * 16 + off)[0]
    return SEGNAME.get(v, '%04x' % v)


def dname(seg, off):
    for base, size, name in reversed(DATA.get(seg, [])):
        if base <= off < base + size:
            return name if off == base else f'{name}+{off - base:#x}'
    return f'{seg}:{off:04x}'


def ds_string(off):
    a = DG * 16 + off
    if a >= len(flat):
        return None
    e = flat.find(b'\0', a, a + 120)
    s = flat[a:e]
    if e > a + 3 and all(32 <= c < 127 or c in (9, 10, 13) for c in s):
        return s.decode('latin1')
    return None


def fname(a):
    return FUNCS.get(a, 'f_%05x' % a)


def dis(addr, maxn=400):
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    md.detail = True
    i = bisect.bisect_right(starts, addr)
    end = starts[i] if i < len(starts) else addr + 0x2000
    # include tail chunks: continue past `end` only if no ret seen yet
    es = None
    ds = 'DS'
    regimm = {}
    out = [f'; ==== {fname(addr)} ({addr:05x})']
    pos = addr
    n = 0
    hard_end = addr + 0x4000
    seen_ret = False
    for ins in md.disasm(flat[addr:hard_end], 0):
        lin = addr + ins.address
        if lin >= end and seen_ret:
            break
        n += 1
        if n > maxn:
            out.append('; ... truncated')
            break
        note = []
        ops = ins.operands
        mn = ins.mnemonic
        if mn == 'mov' and len(ops) == 2 and ops[0].type == X86_OP_REG and ops[1].type == X86_OP_IMM:
            regimm[md.reg_name(ops[0].reg)] = ops[1].imm & 0xffff
        if mn == 'mov' and len(ops) == 2 and ops[0].type == X86_OP_REG and md.reg_name(ops[0].reg) in ('es', 'ds'):
            s = ops[1]
            if s.type == X86_OP_MEM and not s.mem.base and not s.mem.index:
                v = segvar(s.mem.disp & 0xffff)
            elif s.type == X86_OP_REG and md.reg_name(s.reg) in regimm:
                v = SEGNAME.get(regimm[md.reg_name(s.reg)], '%04x' % regimm[md.reg_name(s.reg)])
            else:
                v = None
            if md.reg_name(ops[0].reg) == 'es':
                es = v
            else:
                ds = v or '?'
            note.append(f'{md.reg_name(ops[0].reg)}={v}')
        elif mn == 'les' or (mn == 'pop' and ins.op_str == 'es'):
            es = '?ptr'
        for o in ops:
            if o.type == X86_OP_MEM:
                sr = md.reg_name(o.mem.segment) if o.mem.segment else None
                disp = o.mem.disp & 0xffff
                based = o.mem.base or o.mem.index
                if sr == 'es' and es and es != '?ptr':
                    note.append(dname(es, disp))
                elif sr in (None, 'ds') and md.reg_name(o.mem.base) not in ('bp',) and not (o.mem.base == 0 and o.mem.index == 0 and False):
                    if md.reg_name(o.mem.base) != 'bp':
                        nm = dname(ds, disp)
                        if ds != 'DS' or not nm.startswith('DS:'):
                            note.append(nm)
            if o.type == X86_OP_IMM and mn in ('mov', 'push') and 0x1000 <= o.imm <= 0xffff:
                s = ds_string(o.imm)
                if s:
                    note.append(repr(s[:50]))
        if mn == 'call' and ops and ops[0].type == X86_OP_IMM:
            t = (lin + ins.size + struct.unpack('<h', bytes(ins.bytes[1:3]))[0]) & 0xfffff
            note.append('-> ' + fname(t))
        if mn == 'lcall' and len(ins.bytes) == 5:
            off, seg = struct.unpack('<HH', bytes(ins.bytes[1:]))
            note.append('-> ' + fname(seg * 16 + off))
        if mn in ('ret', 'retf'):
            seen_ret = True
        opstr = ins.op_str
        if (mn.startswith('j') or mn in ('call', 'loop')) and ops and ops[0].type == X86_OP_IMM and mn != 'ljmp':
            opstr = f'{(addr + ops[0].imm) & 0xfffff:05x}'
        if mn in ('add', 'mov') and len(ops) == 2 and ops[1].type == X86_OP_IMM and ops[0].type == X86_OP_REG:
            nm = dname('SIM', ops[1].imm & 0xffff)
            if not nm.startswith('SIM:') and '+' not in nm:
                note.append('&' + nm)
        txt = f'{lin:05x}  {mn} {opstr}'
        out.append(f'{txt:<52}' + ('; ' + ', '.join(note) if note else ''))
    return '\n'.join(out)


if __name__ == '__main__':
    a = sys.argv[1]
    addr = int(NAME2F.get(a, a), 16) if not isinstance(NAME2F.get(a), int) else NAME2F[a]
    if a in NAME2F:
        addr = NAME2F[a]
    print(dis(addr, int(sys.argv[2]) if len(sys.argv) > 2 else 400))
