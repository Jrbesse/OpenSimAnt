"""Verify the add-ants routines f_6be50 (black) / f_6bf06 (red) against the original.

python test_tools.py
"""
import sys

from verify import Verifier
from simant_ref import newgame
import test_sim


def port(red):
    def run(st, n):
        st.player = test_sim.Player()
        newgame.add_surface_ants(st, n, red)
    return run


def main():
    v = Verifier()
    test_sim.prepare(v)
    ok = True
    for lin, red in ((0x6be50, False), (0x6bf06, True)):
        for n in (1, 25, 300, 2000, 0):
            ok &= v.check(lin, port(red), args_fn=lambda st, i, n=n: (n,), label=f'{lin:05x}({n})',
                          ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
