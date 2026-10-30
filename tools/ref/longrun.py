"""Long-run differential check: the original (in the emulator) and the Python reference play the same long game
tick by tick, with a scripted player, and their memory is compared after every tick and every action.

    python longrun.py [ticks] [game ...] [--out file] [--every n]

A game is "quick:<crt seed hex>" or "full:<crt seed hex>" (default: quick:2468ace full:13579bd quick:badf00d
full:7777777). Each runs `ticks` SimSteps (default 50000) from a new game; when a game ends (G:0376) both sides
start a new one in the same mode and the run goes on. The clock moves 1..7 units per tick (the yard layer, the
speech balloons and the spider's remarks run on it).

The scripted player (one random.Random per game, so the run repeats exactly) walks the yellow ant, digs in the
nest, gives its menu commands (f_76cb9), drops food, sprays insecticide and places rocks with the map tools
(f_770f6), and in the Full Game moves to other patches (f_01d48).

--out writes a recording for the C# port (`Formica.Replay --longrun <file>`): JSON lines of the actions, the
steps with their clock and the Python State every `--every` ticks (default 1000), zlib + base64. The recording
holds game data from the player's own files: it goes to remake/build/longrun (git-ignored), never into the repo.
"""
import base64
import json
import os
import random
import sys
import time
import zlib

from verify import Verifier
from simant_ref import commands, newgame, sim, tools
from simant_ref.state import G, T, DS, LO, HI
import test_sim
import test_newgame

# UI stubs: SimStep's (test_sim), the commands' (voice, help, pause, animation timer), the tools' (info window,
# status line)
STUBS = test_sim.STUBS + (0x00ea1, 0x76eb5, 0x2f816, 0x0125f, 0x2f8fc, 0x15e2c)
DEFAULT_GAMES = ('quick:2468ace', 'full:13579bd', 'quick:badf00d', 'full:7777777')
COMMANDS = (1, 2, 3, 4, 5, 7, 8, 9)            # recruit 5 / 10 / all, release, ..., alarm, dig hole, start brood
TOOL_OPTS = {1: 0x7b7, 2: 0x7b8, 3: 0x7b9, 4: 0x7ba, 5: 0x7bb, 6: 0x7bc}   # the map tools' option bytes (test_tools.OPTS)


class Run:
    def __init__(self, v, out):
        self.v, self.e = v, v.e
        self.st = None
        self.out = out
        self.b = self.e.base * 16
        stack_top = 0x55b3 * 16 + self.e.call_sp + 0x10
        ignore = test_newgame.SCREEN + test_sim.SCREEN + ((stack_top - 0x800, stack_top),)
        self.ignore = [(max(lo, LO) - LO, min(hi, HI) - LO) for lo, hi in ignore if hi > LO and lo < HI]
        self.events = 0

    # ---------------------------------------------------------------- recording
    def rec(self, **kw):
        if self.out:
            self.out.write(json.dumps(kw, separators=(',', ':')) + '\n')
            self.events += 1

    def rec_state(self, tick):
        self.rec(k='state', t=tick, mem=base64.b64encode(zlib.compress(bytes(self.st.mem), 6)).decode())

    # ---------------------------------------------------------------- both sides
    def poke(self, seg, off, val, byte=False):
        if byte:
            self.e.write(seg, off, bytes([val & 0xff]))
            self.st.set8(seg, off, val)
        else:
            self.e.set16(seg, off, val)
            self.st.set16(seg, off, val)
        self.rec(k='poke', seg=seg, off=off, val=val & 0xffff, byte=byte)

    def call(self, lin, args, fn, name):
        self.e.call_lin(lin, args)
        fn(self.st, *args)
        self.rec(k='call', f=name, args=list(args))

    def set_clock(self, c):
        self.e.uc.mem_write(self.e.game_clock, (c & 0xffffffff).to_bytes(4, 'little'))
        self.st.clock = c & 0xffffffff

    def compare(self, what):
        orig = bytearray(self.e.uc.mem_read(LO + self.b, HI - LO))
        port = bytearray(self.st.mem)
        for lo, hi in self.ignore:
            orig[lo:hi] = bytes(hi - lo)
            port[lo:hi] = bytes(hi - lo)
        if orig == port:
            return True
        from verify import describe
        diffs = [i for i in range(HI - LO) if orig[i] != port[i]]
        print(f'  MISMATCH after {what}: {len(diffs)} bytes differ')
        for i in diffs[:12]:
            print(f'      {describe(LO + i)}: original {orig[i]:#04x} port {port[i]:#04x}')
        return False

    # ---------------------------------------------------------------- the game
    def new_game(self, mode, crt):
        for seg, off, val in ((G, 0xeac, mode), (DS, 0x7bbe, crt & 0xffff), (DS, 0x7bc0, crt >> 16)):
            self.poke(seg, off, val)
        self.call(0x6b36b, (), lambda st: newgame.new_game(st), 'newgame.new_game')

    def action(self, rnd, mode):
        """Maybe one scripted player action before this tick; returns its label or None."""
        r = rnd.random()
        if r < 1 / 120:                                       # walk the yellow ant to a surface cell
            a, b = rnd.randrange(128), rnd.randrange(64)
            for off, val in ((0xaa0, 1), (0xa8e, 0), (0xaf8, 1), (0xad6, a), (0xae8, b), (0xd6c, 0xfffe)):
                self.poke(G, off, val)
            return f'walk to ({a}, {b})'
        r -= 1 / 120
        if r < 1 / 400:                                       # dig in the black nest
            a, b = rnd.randrange(64), rnd.randrange(1, 64)
            for off, val in ((0xaa0, 1), (0xa8e, 2), (0xaf8, 2), (0xad6, a), (0xae8, b), (0xd6c, 0xfffe)):
                self.poke(G, off, val)
            return f'dig to ({a}, {b})'
        r -= 1 / 400
        if r < 1 / 500:
            c = rnd.choice(COMMANDS)
            self.call(0x76cb9, (c,), commands.command, 'commands.command')
            return f'command {c}'
        r -= 1 / 500
        # (chance, view, tool, option, label): food, insecticide and rocks on the surface; workers into either nest
        # (f_77672 digs the cell if needed), which keeps both colonies growing so games run long
        for p, view, tool, opt, label in ((1 / 250, 1, 4, 0, 'food'), (1 / 2500, 1, 6, 1, 'insecticide'),
                                          (1 / 3000, 1, 1, 0, 'rocks'), (1 / 60, 2, 3, 0, 'a black worker'),
                                          (1 / 200, 3, 3, 1, 'a red worker')):
            if r < p:
                a, b = (rnd.randrange(128), rnd.randrange(64)) if view == 1 else (rnd.randrange(16, 48), rnd.randrange(2, 24))
                prev = self.st.u16(G, 0x32e)
                self.poke(G, 0x32e, view)
                self.poke(G, 0x104c, tool)
                self.poke(G, 0x9fc, a)
                self.poke(G, 0x9fe, b)
                if tool in TOOL_OPTS:
                    self.poke(T, TOOL_OPTS[tool], opt, byte=True)
                self.call(0x770f6, (a, b), tools.apply_tool, 'tools.apply_tool')
                self.poke(G, 0x32e, prev)
                return f'{label} at ({a}, {b})'
            r -= p
        if mode == 2 and r < 1 / 6000:                        # the Full Game: move to another patch
            row, col = self.st.u16(G, 0x7bc), self.st.u16(G, 0x7be)
            row = max(0, min(11, row + rnd.choice((-1, 0, 1))))
            col = max(0, min(15, col + rnd.choice((-1, 1))))
            self.poke(G, 0x7bc, row)
            self.poke(G, 0x7be, col)
            if not self.st.u8(T, 0xa4 + row * 16 + col):
                self.poke(T, 0xa4 + row * 16 + col, rnd.randrange(3, 12), byte=True)
            self.call(0x01d48, (), lambda st: newgame.move_to_patch(st), 'newgame.move_to_patch')
            return f'move to patch ({row}, {col})'
        return None

    def play(self, mode, crt, ticks, every):
        v, e = self.v, self.e
        v.load(v.snaps[0][1])
        self.st = v.state_from_emu()
        self.st.player = test_sim.Player()
        self.st.bios_kbd = 0
        e.uc.mem_write(0x417, b'\0')
        clock = self.st.clock
        self.rec(k='game', mode=mode, crt=crt, clock=clock)
        self.rec_state(-1)
        self.new_game(mode, crt)
        if not self.compare('the new game'):
            return False, 0, 0
        rnd = random.Random(crt)
        games, actions, t0, started = 1, 0, time.time(), 0
        self.lengths = []
        for t in range(ticks):
            label = self.action(rnd, mode)
            if label:
                actions += 1
                if not self.compare(f'tick {t}: {label}'):
                    return False, t, games
            if e.w16(G, 0x376):                               # game over: a new game, same mode
                self.lengths.append((t - started, 'won' if e.w16(G, 0x366) else 'lost', self.st.u16(G, 0xc26)))
                started = t
                crt = (crt * 1103515245 + 12345) & 0x7fffffff
                self.new_game(mode, crt)
                games += 1
                if not self.compare(f'tick {t}: new game {games}'):
                    return False, t, games
            clock += 1 + (t * 5 + t // 7) % 7
            self.set_clock(clock)
            e.call_lin(0x0894e)
            sim.sim_step(self.st)
            self.rec(k='step', clock=clock)
            if not self.compare(f'tick {t} (SimStep)'):
                return False, t, games
            if every and (t + 1) % every == 0:
                self.rec_state(t + 1)
            if (t + 1) % 5000 == 0:
                print(f'    tick {t + 1}: {games} game(s), {actions} actions, {time.time() - t0:.0f}s')
        self.rec_state(ticks)
        return True, ticks, games


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) if '=' in a else (a[2:], '') for a in sys.argv[1:] if a.startswith('--'))
    ticks = int(args[0]) if args and args[0].isdigit() else 50000
    games = [a for a in args if ':' in a] or list(DEFAULT_GAMES)
    every = int(opts.get('every', 1000))
    out = None
    if 'out' in opts:
        path = opts['out'] or os.path.join(os.path.dirname(__file__), '..', '..', 'remake', 'build', 'longrun', 'longrun.jsonl')
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        out = open(path, 'w')
    v = Verifier()
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    # f_770f6 runs in overlay 24's second code segment (called from f_76f4a): its jump table is CS-relative, so it
    # must run with CS = 0x76F4 (as test_tools.py does)
    seg_of = v.e.seg_of
    v.e.seg_of = lambda lin: (0x76f4, lin - 0x76f40) if lin == 0x770f6 else seg_of(lin)
    run = Run(v, out)
    ok = True
    for g in games:
        kind, seed = g.split(':')
        mode = {'quick': 1, 'full': 2}[kind]
        t0 = time.time()
        good, t, n = run.play(mode, int(seed, 16), ticks, every)
        print(f'{g}: {"OK" if good else "MISMATCH"} at tick {t}, {n} game(s), {time.time() - t0:.0f}s')
        if run.lengths:
            print('    games ended (ticks, result): ' + ', '.join(f'{n} {r}' for n, r, _ in run.lengths[:12]))
        ok &= good
    if out:
        out.close()
        print(f'recorded {run.events} events')
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
