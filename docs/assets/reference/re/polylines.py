"""Extract the spider's leg drawings: the per-heading move-to / line-to programs of f_04c44 and f_04666.

python polylines.py [out.json]     (default build/spider_legs.json, read by tools/ref/render_view.py)

Both routines switch on the spider's heading (arg 3, 0..7) through a jump table, then draw with
f_045a5(x, y) (move to) and f_045fa(x, y) (line to). Each coordinate is the routine's x or y argument plus
a signed byte from a T table, indexed by a register (si / di: the routine's frame or jitter value) or
fixed. This walks each case's code and records, per call, ('move' | 'line', x_term, y_term) with a term
= [table offset, index register or None]. Prints anything it does not understand.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FLAT = open(os.path.join(HERE, 'build', 'flat.bin'), 'rb').read()
ROUTINES = {'f_04c44': (0x04c44, 0x04c82, 0x2500), 'f_04666': (0x04666, 0x046d8, 0x2500)}
TAILS = {0x066c4, 0x04c3e}                       # where the cases of f_04c44 / f_04666 rejoin
MOVE, LINE = 0x045a5, 0x045fa


def disasm(start, n):
    out = subprocess.run([sys.executable, os.path.join(HERE, 'adis.py'), hex(start), str(n)],
                         capture_output=True, text=True).stdout
    ins = []
    for l in out.splitlines():
        m = re.match(r'([0-9a-f]{5})  (.*?)\s*(;.*)?$', l)
        if m:
            ins.append((int(m.group(1), 16), m.group(2).strip()))
    return ins


ARG = {'6': 'x', '8': 'y'}
REG = r'(ax|cx|dx|bx|di)'


def walk(entry, ends):
    """Follow one case from `entry` (straight-line code, following unconditional jumps) until it reaches
    one of `ends`, evaluating each register as base + k + sign * T[table + index register]. Returns the
    draw ops: ('move' | 'line', x, y) with x / y = [base 'x' / 'y', k, table offset or None, index register,
    sign]."""
    ops, stack, unknown = [], [], []
    regs = {}
    pc, seen = entry, 0
    code = {a: t for a, t in disasm(entry, 3000)}
    while pc not in ends and seen < 4000:
        seen += 1
        if pc not in code:
            code.update({a: t for a, t in disasm(pc, 3000)})
        t = code[pc]
        nxt = min(a for a in code if a > pc)
        m = re.match(r'mov al, byte ptr es:\[(?:(si|di) \+ )?0x([0-9a-f]+)\]', t)
        m2 = re.match(r'mov ' + REG + r', word ptr (?:es:)?\[bp \+ (6|8)\]$', t)
        m3 = re.match(r'(add|sub) ' + REG + r', (0x[0-9a-f]+|\d+)$', t)
        m4 = re.match(r'(add|sub) ' + REG + r', word ptr \[bp \+ (6|8)\]$', t)
        m5 = re.match(r'mov ' + REG + ', ' + REG + '$', t)
        if m:
            regs['ax'] = [None, 0, int(m.group(2), 16), m.group(1), 1]
        elif m2:
            regs[m2.group(1)] = [ARG[m2.group(2)], 0, None, None, 1]
        elif m3:
            v = int(m3.group(3), 0)
            regs[m3.group(2)][1] += v if m3.group(1) == 'add' else -v
        elif m4:
            r = regs[m4.group(2)]
            if r[0] is not None:
                unknown.append((pc, t, r))
            r[0] = ARG[m4.group(3)]
            if m4.group(1) == 'sub':
                r[0] = '-' + r[0]                        # table - arg, fixed by the neg that follows
        elif re.match(r'neg ' + REG + '$', t):
            r = regs[t.split()[1]]
            if r[0] and r[0].startswith('-'):
                r[0] = r[0][1:]
                r[1], r[4] = -r[1], -r[4]
            else:
                unknown.append((pc, t, r))
        elif m5:
            regs[m5.group(1)] = list(regs[m5.group(2)])
        elif t == 'cwde' or t.startswith('mov es,') or t == 'pop bx' or t == 'push cs':
            pass
        elif re.match(r'push ' + REG + '$', t):
            stack.append(list(regs[t.split()[1]]))
        elif t.startswith('call '):
            target = int(t.split()[1], 16)
            if target in (MOVE, LINE):
                x, y = stack.pop(), stack.pop()
                if x[0] != 'x' or y[0] != 'y':
                    unknown.append((pc, 'odd term', x, y))
                ops.append(('move' if target == MOVE else 'line', x, y))
                stack.clear()
            else:
                unknown.append((pc, t))
        elif t.startswith('jmp '):
            nxt = int(t.split()[1], 16)
        else:
            unknown.append((pc, t))
        pc = nxt
    return ops, unknown


DEFAULT_OUT = os.path.join(HERE, 'build', 'spider_legs.json')      # git-ignored: derived from the EXE


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    result = {}
    for name, (start, table, base) in ROUTINES.items():
        entries = [base + int.from_bytes(FLAT[table + 2 * k: table + 2 * k + 2], 'little') for k in range(8)]
        cases = []
        for h, e in enumerate(entries):
            ops, unknown = walk(e, set(entries) - {e} | TAILS)
            cases.append(ops)
            print(f'{name} heading {h}: entry {e:05x}, {len(ops)} ops')
            for u in unknown[:6]:
                print('    ??', u)
        result[name] = {'entries': entries, 'cases': cases}
    json.dump(result, open(out, 'w'), indent=1)
    print('wrote', out)


if __name__ == '__main__':
    main()
