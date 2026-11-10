"""Print Ghidra's pseudo-C for routines, with called functions renamed from symbols.json.

python decomp.py <flat_hex_or_name> [...]

Ghidra addresses are flat + 0x1000 paragraphs (its load segment). Unnamed functions appear as f_<flat>.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEC = os.path.join(HERE, 'build', 'decomp')
SYM = json.load(open(os.path.join(HERE, 'symbols.json')))
NAMES = {int(k, 16): v for k, v in SYM['funcs'].items()}
BYNAME = {v: k for k, v in NAMES.items()}

_index = None


def index():
    global _index
    if _index is None:
        _index = {}
        for line in open(os.path.join(DEC, 'functions.tsv')):
            addr = line.split('\t')[0]
            seg, off = (int(x, 16) for x in addr.split(':'))
            _index[(seg - 0x1000) * 16 + off] = addr
    return _index


def flat_of(m):
    seg, off = int(m.group(1), 16), int(m.group(2), 16)
    return (seg - 0x1000) * 16 + off


def rename(text):
    def sub(m):
        lin = flat_of(m)
        return NAMES.get(lin, f'f_{lin:05x}')
    return re.sub(r'FUN_([0-9a-f]{4})_([0-9a-f]{4})', sub, text)


def get(lin):
    addr = index().get(lin)
    if not addr:
        return f'// no Ghidra function at {lin:05x}'
    seg = addr.split(':')[0]
    text = open(os.path.join(DEC, f'decomp_{seg}.c')).read()
    start = text.index(f'// ==== {addr} ')
    end = text.find('// ==== ', start + 10)
    body = text[start:end if end > 0 else None]
    body = '\n'.join(l for l in body.splitlines() if l.strip() and not l.strip().startswith('/* WARNING'))
    return rename(body)


if __name__ == '__main__':
    for a in sys.argv[1:]:
        lin = BYNAME[a] if a in BYNAME else int(a, 16)
        print(get(lin))
        print()
