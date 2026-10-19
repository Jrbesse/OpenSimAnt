"""Record the reference port's calls as traces for the C# remake's tests.

    python record_traces.py <test_module> [test args...]      e.g.  python record_traces.py test_sim 3000

Wraps every function of every simant_ref module, then runs the test's main(). Each outermost call made on a
State (the calls a test makes directly) is written to remake/build/traces/<name>.trace with its arguments,
the player hook class, the clock and keyboard flags, the return value and the State memory before and
after. The C# tests replay each call on their port and compare.

Traces hold game memory (they start from emulator snapshots): never commit them (remake/build is ignored).

Format: b'SATR1', then records: u32 json length, json, u32 n, zlib(before XOR previous after), u32 n,
zlib(after XOR before). The first record's "previous after" is all zeros.
"""
import importlib
import inspect
import json
import os
import struct
import sys
import types
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT_DIR = os.path.join(HERE, '..', '..', 'remake', 'build', 'traces')

import simant_ref                                       # noqa: E402
from simant_ref.state import State, LO, HI              # noqa: E402

MODULES = ['rng', 'state', 'tables', 'terrain', 'pheromones', 'colony', 'movement', 'surface', 'nestgrid', 'nest',
           'red_nest', 'world', 'yard', 'sim', 'newgame', 'game', 'savefile', 'cheats', 'debug', 'tools', 'markers',
           'balloons', 'panels', 'commands', 'player', 'tutorial']
SIZE = HI - LO
MAX_PER_FUNC = int(os.environ.get('TRACE_MAX', '4000'))


class Recorder:
    def __init__(self, path):
        self.f = open(path, 'wb')
        self.f.write(b'SATR1')
        self.prev = 0
        self.depth = 0
        self.counts = {}
        self.named = {}
        for m in MODULES:
            mod = sys.modules['simant_ref.' + m]
            for k, v in vars(mod).items():
                if isinstance(v, (dict, list, tuple)) and not k.startswith('__'):
                    self.named.setdefault(id(v), f'{m}.{k}')

    def enc(self, v):
        if v is None or isinstance(v, (bool, int, str)):
            return v
        if isinstance(v, State):
            return {'$': 'state'}
        if isinstance(v, (bytes, bytearray)):
            return {'$': 'bytes', 'hex': bytes(v).hex()}
        if id(v) in self.named:
            return {'$': 'ref', 'name': self.named[id(v)]}
        if isinstance(v, (tuple, list)):
            return [self.enc(x) for x in v]
        if isinstance(v, dict):
            return {'$': 'dict', 'items': {str(k): self.enc(x) for k, x in v.items()}}
        if callable(v):
            return {'$': 'callable', 'name': getattr(v, '__qualname__', '?')}
        return {'$': 'other', 'type': type(v).__name__}

    def mem_int(self, st):
        return int.from_bytes(st.mem, 'little')

    def write(self, head, before, after):
        h = json.dumps(head).encode()
        b = zlib.compress((before ^ self.prev).to_bytes(SIZE, 'little'), 6)
        a = zlib.compress((after ^ before).to_bytes(SIZE, 'little'), 6)
        self.f.write(struct.pack('<I', len(h)) + h + struct.pack('<I', len(b)) + b + struct.pack('<I', len(a)) + a)
        self.prev = after

    def wrap(self, modname, name, fn):
        rec = self

        def wrapper(*args, **kw):
            st = args[0] if args else None
            key = f'{modname}.{name}'
            if rec.depth or not isinstance(st, State) or kw or rec.counts.get(key, 0) >= MAX_PER_FUNC:
                rec.depth += 1
                try:
                    return fn(*args, **kw)
                finally:
                    rec.depth -= 1
            rec.counts[key] = rec.counts.get(key, 0) + 1
            player = getattr(st, 'player', None)
            head = {'func': key, 'args': [rec.enc(a) for a in args[1:]],
                    'player': None if player is None else f'{type(player).__module__}.{type(player).__qualname__}',
                    'clock': st.clock, 'kbd': st.bios_kbd}
            before = rec.mem_int(st)
            rec.depth += 1
            try:
                r = fn(*args)
                head['ret'] = rec.enc(r)
            except Exception as ex:                  # noqa: BLE001 - recorded, then re-raised
                head['raise'] = type(ex).__name__
                raise
            finally:
                rec.depth -= 1
                head['clock_after'] = st.clock
                head['kbd_after'] = st.bios_kbd
                rec.write(head, before, rec.mem_int(st))
            return r
        wrapper.__wrapped__ = fn
        wrapper.__name__ = name
        return wrapper

    def install(self):
        for m in MODULES:
            mod = sys.modules['simant_ref.' + m]
            for k, v in list(vars(mod).items()):
                if isinstance(v, types.FunctionType) and v.__module__ == mod.__name__:
                    setattr(mod, k, self.wrap(m, k, v))


def main():
    test = sys.argv[1]
    tag = os.environ.get('TRACE_TAG', '')
    for m in MODULES:
        importlib.import_module('simant_ref.' + m)
    os.makedirs(OUT_DIR, exist_ok=True)
    name = test + (('_' + tag) if tag else '')
    rec = Recorder(os.path.join(OUT_DIR, name + '.trace'))
    rec.install()
    sys.argv = [test + '.py'] + sys.argv[2:]
    mod = importlib.import_module(test)
    try:
        r = mod.main()
    finally:
        rec.f.close()
        print('[trace]', name, sum(rec.counts.values()), 'calls:',
              ', '.join(f'{k} {v}' for k, v in sorted(rec.counts.items())))
    sys.exit(0 if r in (None, True, 0) else 1)


if __name__ == '__main__':
    main()
