"""Differential verification of ported routines against the original running in the emulator.

    v = Verifier()                       # boots the game once, records snapshots of a real Quick Game
    v.check(0x14a6c, port_fn)            # runs original and port from each snapshot, compares memory

`port_fn(state, *args)` gets a simant_ref.state.State built from the same memory as the emulator.
Snapshots are cached in tools/re/build/snapshots/ (they contain game data: never commit them).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 're'))

import emu                                            # noqa: E402
from simant_ref.state import State, LO, HI            # noqa: E402

SNAP_DIR = os.path.join(HERE, '..', 're', 'build', 'snapshots')
SNAP_TICKS = (0, 300, 900, 1500, 2200, 3000)   # Quick Game, seed 0x1234 (game over at tick 3264)
SYMBOLS = json.load(open(os.path.join(HERE, '..', 're', 'symbols.json')))


def _region_names():
    seg_of = {v: int(k, 16) for k, v in SYMBOLS['segments'].items()}
    names = []
    import re
    for k, v in SYMBOLS['data'].items():
        sn, off = k.split(':')
        if sn not in seg_of:
            continue
        m = re.search(r'\[(.+)\]', v)
        size = eval(m.group(1)) if m else 2
        names.append((seg_of[sn] * 16 + int(off, 16), size, k, v.split('[')[0]))
    return sorted(names)


NAMES = _region_names()


def describe(lin):
    for start, size, key, name in NAMES:
        if start <= lin < start + size:
            return f'{name}+{lin - start:#x}' if lin != start else name
    for seg, sname in (((0x55b3), 'DS'), (0x50f6, 'G'), (0x3e1d, 'SIM'), (0x3d57, 'T')):
        if lin >= seg * 16:
            return f'{sname}:{lin - seg * 16:04x}'
    return f'{lin:05x}'


class Verifier:
    def __init__(self, ticks=SNAP_TICKS, seed=0x1234):
        self.e = emu.SimEmu(base=0x100)
        os.makedirs(SNAP_DIR, exist_ok=True)
        paths = [os.path.join(SNAP_DIR, f'quick_{seed:04x}_{t:05d}.bin') for t in ticks]
        if all(os.path.exists(p) for p in paths):
            self.e.boot(max_insns=1_000_000_000)
            self.e.stub_drawing()
            self.snaps = [(t, open(p, 'rb').read()) for t, p in zip(ticks, paths)]
            return
        t0 = time.time()
        self.e.boot(max_insns=1_000_000_000)
        self.e.stub_drawing()
        self.e.set16(emu.G, 0xeac, 1)
        self.e.set16(emu.DGROUP, 0x8ba2, seed)
        self.e.call_lin(0x6b36b)
        self.snaps = []
        tick = 0
        for t, p in zip(ticks, paths):
            while tick < t:
                self.e.call_lin(0x0894e)
                tick += 1
                if self.e.w16(emu.G, 0x376):
                    raise RuntimeError(f'game over at tick {tick}, before snapshot tick {t}')
            mem = bytes(self.e.uc.mem_read(0, 0x100000))
            open(p, 'wb').write(mem)
            self.snaps.append((t, mem))
        print(f'[verify] recorded {len(ticks)} snapshots in {time.time() - t0:.1f}s')

    def load(self, mem):
        self.e.uc.mem_write(0, mem)
        self.e.uc.ctl_remove_cache(0, 0x100000)

    def state_from_emu(self):
        b = self.e.base * 16
        return State(bytes(self.e.uc.mem_read(LO + b, HI - LO)))

    def check(self, lin, port_fn, args_fn=None, label=None, repeat=1, ignore=(), pre=None, post_args=None,
              pre_once=False):
        """Run original routine `lin` and `port_fn` from every snapshot (optionally `repeat` times in a row,
        args from args_fn(state, i); args None = skip this call). pre(set16, args) can set globals on both
        sides before each call (set16(seg, off, value)); post_args(state, args) can then rewrite the call's
        args from the (shared) state. pre_once: run pre only before the first call of each snapshot.
        Returns True if all memory matches."""
        label = label or f'{lin:05x}'
        ok = True
        b = self.e.base * 16
        # the call's own stack lives in DGROUP (SS == DS): ignore the scratch area below the call frame
        stack_top = 0x55b3 * 16 + self.e.call_sp + 0x10
        ignore = tuple(ignore) + ((stack_top - 0x800, stack_top),)
        for tick, mem in self.snaps:
            self.load(mem)
            st = self.state_from_emu()
            calls = 0
            for i in range(repeat):
                args = args_fn(st, i) if args_fn else ()
                if args is None:
                    continue
                calls += 1
                if pre and not (pre_once and calls > 1):
                    def set16(seg, off, val):
                        self.e.set16(seg, off, val)
                        st.set16(seg, off, val)

                    def set8(seg, off, val):
                        self.e.write(seg, off, bytes([val & 0xff]))
                        st.set8(seg, off, val)
                    set16.byte = set8
                    pre(set16, args)
                if post_args:
                    args = post_args(st, args)
                ro = self.e.call_lin(lin, args)
                rp = port_fn(st, *args)
                if rp is not None and (rp & 0xffff) != (ro & 0xffff):
                    print(f'  [{label} @tick {tick} call {i}] return {ro:#x} vs port {rp:#x}')
                    ok = False
                    break
            orig = bytes(self.e.uc.mem_read(LO + b, HI - LO))
            diffs = [i for i in range(HI - LO) if orig[i] != st.mem[i]
                     and not any(lo <= LO + i < hi for lo, hi in ignore)]
            if diffs:
                ok = False
                print(f'  [{label} @tick {tick}] {len(diffs)} bytes differ:')
                for i in diffs[:8]:
                    print(f'      {describe(LO + i)}: original {orig[i]:#04x} port {st.mem[i]:#04x}')
        print(f'{label}: {"OK" if ok else "MISMATCH"} ({len(self.snaps)} snapshots x {repeat})')
        return ok
