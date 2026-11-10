"""Verify the speech balloons (f_06a4d via f_07128) against the original, with the drawing f_0696a stubbed.

python test_balloons.py
"""
import sys

from verify import Verifier
from simant_ref import balloons
from simant_ref.state import G, T
import test_sim

STUBS = test_sim.STUBS + (0x0696a,)
SPOTS = {'fight': (40, 20, 1), 'brood': (12, 30, 2), 'queen': (30, 8, 3), 'rest': (90, 50, 1)}


def setup(visible=1, mode=0xffff, records=True, gates=0, expire=False, paused=0, idx=None, latched=False):
    def pre(set16, args):
        set16(T, 0x7b2, visible)
        set16(T, 0x7be, mode)
        set16(G, 0x47e, paused)
        for kind, gate, rec, lat, clear, timers in balloons.SOURCES:
            a, b, view = SPOTS[kind] if records else (0xffff, 0xffff, 1)
            for off, v in zip(rec, (a, b, view)):
                set16(G, off, v)
            if gates is not None:
                set16(G, gate, gates)
            if latched:
                for off, v in zip(lat, SPOTS[kind]):
                    set16(G, off, v)
            for timer in timers:
                if expire:
                    set16(G, timer[0], 0)
                    set16(G, timer[0] + 2, 0)
                if idx is not None:
                    set16(G, timer[5], timer[7] - 1 if idx == 'last' else idx)
    return pre


def port(st):
    st.player = test_sim.Player()
    balloons.balloons(st)


CASES = [
    ('latch, then wait', setup(), True, 20),
    ('timers always expired', setup(gates=None, expire=True), False, 150),
    ('timers always expired, from the last line', setup(gates=None, expire=True, idx='last'), True, 60),
    ('latched, every call expired', setup(gates=1, expire=True, latched=True), False, 80),
    ('paused', setup(gates=1, expire=True, paused=1, latched=True), False, 10),
    ('patch hidden', setup(visible=0, expire=True), False, 10),
    ('another mode (T:07BE = 0)', setup(mode=0, expire=True), False, 10),
    ('no records', setup(records=False, expire=True), False, 10),
    ('gates negative', setup(gates=0xffff, expire=True), False, 10),
]


def main():
    v = Verifier()
    # f_07128 near-calls f_06a4d below it: run it in the segment the game's far calls use for this code
    # (0x250, as in `lcall 0x250, 0x428a` → f_0678a), so the near call doesn't wrap around
    seg_of = v.e.seg_of
    v.e.seg_of = lambda lin: (0x250, lin - 0x2500) if lin == 0x07128 else seg_of(lin)
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    ok = True
    for label, pre, once, n in CASES:
        ok &= v.check(0x07128, port, repeat=n, label=label, pre=pre, pre_once=once, ignore=test_sim.SCREEN)
    # the line counts the port uses must match the lists in memory (index wraps at the null entry)
    b = v.e.base * 16
    for kind, gate, rec, lat, clear, timers in balloons.SOURCES:
        for timer in timers:
            lo, seg = v.e.w16(G, timer[6]), v.e.w16(G, timer[6] + 2)
            n = 0
            while bytes(v.e.uc.mem_read(seg * 16 + lo + 4 * n, 4)) != b'\0\0\0\0':
                n += 1
            if n != timer[7]:
                ok = False
                print(f'  {kind}: list G:{timer[6]:04x} has {n} lines, the port says {timer[7]}')
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
