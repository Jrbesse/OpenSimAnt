"""Verify the surface-ant handlers and dispatcher against the original (python test_surface.py [state ...])."""
import sys

from verify import Verifier
from simant_ref import surface as sf
from simant_ref.state import SIM, G

HANDLERS = [(0, 0x09334, sf.s_bored), (1, 0x099c7, sf.s_nesting), (2, 0x09fe5, sf.s_foraging),
            (3, 0x09e65, sf.s_got_food), (4, 0x099c7, sf.s_nesting), (5, 0x097ce, sf.s_dig_out),
            (6, 0x0a368, sf.s_defense), (7, 0x0ab2d, sf.s_attack), (8, 0x08eb2, sf.s_hatching),
            (9, 0x08f2e, sf.s_egg_laying), (10, 0x0a871, sf.s_fighting), (11, 0x09c55, sf.s_alarmed),
            (12, 0x092a1, sf.s_defend_nest), (13, 0x09018, sf.s_resting), (14, 0x09091, sf.s_pre_flight),
            (15, 0x090f3, sf.s_take_off), (16, 0x091d2, sf.s_flying), (19, 0x0df5b, sf.s_avenger)]


def ants_in_state(st, state):
    n = st.u16(G, 0xd6a)
    return [i for i in range(n) if st.u8(SIM, 0xad3b + i) and st.u8(SIM, 0xa952 + i) == state]


def with_player(fn):
    def run(st, *args):
        st.player = sf.NoPlayer()
        return fn(st, *args)
    return run


def main():
    only = {int(x) for x in sys.argv[1:]}
    v = Verifier()
    ok = True
    for state, lin, fn in HANDLERS:
        if only and state not in only:
            continue
        found = []

        def args(st, i, state=state, found=found):
            ants = ants_in_state(st, state)
            if i == 0:
                found.append(len(ants))
            return (ants[i],) if i < len(ants) else None
        ok &= v.check(lin, with_player(fn), args, label=f'state {state:2d} {fn.__name__}', repeat=12,
                      pre=lambda set16, a: set16(G, 0xf18, a[0]))
        print(f'      (ants in state per snapshot: {found})')
    # forced coverage: put every live surface ant into each state, with a fitting caste
    caste_for = {3: 3, 5: 5, 9: 13, 10: 14, 19: 6}
    for state, lin, fn in HANDLERS:
        if only and state not in only:
            continue

        def args(st, i):
            n = st.u16(G, 0xd6a)
            live = [k for k in range(n) if st.u8(SIM, 0xad3b + k)]
            return (live[i],) if i < len(live) else None

        def pre(set16, a, state=state):
            set8 = set16.byte
            ant = a[0]
            set16(G, 0xf18, ant)
            set8(SIM, 0xa952 + ant, state)
            if state in caste_for:
                tb = 0
                # keep colour and heading, replace the caste
                t = v.e.read(SIM, 0xad3b + ant, 1)[0]
                if state == 19:
                    tb = 0x80
                nt = (t & 0x87) | tb | (caste_for[state] << 3)
                set8(SIM, 0xad3b + ant, nt)
                aa, bb = v.e.read(SIM, 0xa180 + ant, 1)[0], v.e.read(SIM, 0xa569 + ant, 1)[0]
                set8(SIM, 0x6180 + aa * 64 + bb, nt)
                if state == 10:
                    set8(SIM, 0xb124 + ant, (t & 0x80) | (2 << 3) | (t & 7))
        ok &= v.check(lin, with_player(fn), args, label=f'forced {state:2d} {fn.__name__}', repeat=40, pre=pre)
    if not only:
        ok &= v.check(0x08c8b, with_player(sf.surface_ants_tick), label='SurfaceAntsTick', repeat=3)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
