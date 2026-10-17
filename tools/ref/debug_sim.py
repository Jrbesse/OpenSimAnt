"""Debug helper: python debug_sim.py [snapshot index] [max ticks]

Runs SimStep in the original and the port side by side from a snapshot, comparing all memory after every
tick, and reports the first tick that differs (with the RNG state and the differing bytes)."""
import sys

import test_sim as ts
from verify import Verifier, describe
from simant_ref.state import LO, HI, DS, G

def replay_pieces(n):
    """Replay the divergent tick component by component (original routine vs port function)."""
    from simant_ref import colony as co, world, yard, surface, nest, red_nest, player
    from simant_ref.state import T
    v.load(mem)
    s = v.state_from_emu()
    for _ in range(n):
        v.e.call_lin(0x0894e)
        ts.step(s)
    s.player = ts.Player()

    def tick_head(x):
        x.inc16(G, 0xf08)
        if x.s16(G, 0xf08) > 0x1000:
            x.set16(G, 0xf08, 0)
        x.inc32(G, 0xc26)
    t = (s.u16(G, 0xf08) + 1) & 0xffff
    pieces = [('tick', None, tick_head)]
    if t & 0x3f == 0:
        pieces.append(('HealthDecay', 0x08c12, co.health_decay))
    if t & 0x1f == 0:
        pieces.append(('SlowPhase', 0x08a78, world.slow_phase))
    pieces += [('yard', 0x68513, yard.yard_step), ('weather', 0x0c22c, world.weather),
               ('ant lions', 0x0b163, world.ant_lions), ('spider', 0x0ce63, world.spider)]
    if t & 1:
        pieces.append(('caterpillar', 0x0b6cc, world.caterpillar))
    pieces += [('advisor', 0x13832, lambda x: co.colony_advisor(x, lambda *a: None)),
               ('reset census', 0x08adb, co.reset_census), ('surface ants', 0x08c8b, surface.surface_ants_tick),
               ('black nest', 0x799e0, nest.black_nest_loop), ('red nest', 0x0f3f8, red_nest.red_nest_loop),
               ('yellow', 0x7bf7e, player.yellow_tick), ('stats', 0x08b25, co.stats_from_census),
               ('action', 0x7b7b8, player.player_action), ('advice', 0x0e2ea, world.advisor)]
    for name, lin, fn in pieces:
        if lin is None:
            v.e.set16(G, 0xf08, (v.e.w16(G, 0xf08) + 1) & 0xffff)
            if v.e.w16(G, 0xf08) & 0x8000 == 0 and v.e.w16(G, 0xf08) > 0x1000:
                v.e.set16(G, 0xf08, 0)
            c = v.e.w16(G, 0xc26) | v.e.w16(G, 0xc28) << 16
            c = (c + 1) & 0xffffffff
            v.e.set16(G, 0xc26, c & 0xffff)
            v.e.set16(G, 0xc28, c >> 16)
        else:
            if name == 'spider':
                sa, sb = s.s16(G, 0xf12) >> 4, s.s16(G, 0xf34) >> 4
                print(f'  spider at ({sa}, {sb}) state {s.u16(G, 0xfb8)} 1072 {s.u16(G, 0x1072)} prey '
                      f'{s.s16(G, 0xffc)} a06 {s.u16(G, 0xa06)} yellow v{s.u16(G, 0x48c)} '
                      f'({s.s16(G, 0x47c)}, {s.s16(G, 0x48a)})')
                for y in range(sb - 1, sb + 2):
                    print('   ', [hex(s.grid(0x6180, x, y)) for x in range(sa - 1, sa + 2)])
            v.e.call_lin(lin)
        fn(s)
        o = bytes(v.e.uc.mem_read(LO + b, HI - LO))
        d = [i for i in range(HI - LO) if o[i] != s.mem[i] and not any(lo <= LO + i < hi for lo, hi in ignore)]
        print(f'  after {name}: {len(d)} bytes differ', *[f'{describe(LO + i)} {o[i]:#04x}/{s.mem[i]:#04x}' for i in d[:6]])
        if d:
            break


snap = int(sys.argv[1]) if len(sys.argv) > 1 else 0
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
v = Verifier()
v.extra_stubs = ts.STUBS
v.clock_neutral(0x7c149, 0x7c3b0)
tick0, mem = v.snaps[snap]
v.load(mem)
st = v.state_from_emu()
b = v.e.base * 16
stack_top = 0x55b3 * 16 + v.e.call_sp + 0x10
ignore = tuple(ts.SCREEN) + ((stack_top - 0x800, stack_top),)
for n in range(limit):
    v.e.call_lin(0x0894e)
    ts.step(st)
    orig = bytes(v.e.uc.mem_read(LO + b, HI - LO))
    if orig == bytes(st.mem):
        continue
    diffs = [i for i in range(HI - LO) if orig[i] != st.mem[i] and not any(lo <= LO + i < hi for lo, hi in ignore)]
    if not diffs:
        continue
    print(f'snapshot tick {tick0}: first divergence after {n + 1} ticks (game tick G:0F08 = {st.u16(G, 0xf08)})')
    print(f'  lfsr original {v.e.w16(0x55b3, 0x8ba2):#06x} port {st.u16(DS, 0x8ba2):#06x}')
    for i in diffs[:16]:
        print(f'  {describe(LO + i)}: original {orig[i]:#04x} port {st.mem[i]:#04x}')
    if '--pieces' in sys.argv:
        replay_pieces(n)
    break
else:
    print(f'no divergence in {limit} ticks')
