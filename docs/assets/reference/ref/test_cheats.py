"""Verify the cheat codes (f_6a920) against the original: every code typed key by key from every snapshot,
plus broken prefixes and toggles typed twice.

python test_cheats.py [name-substring ...]
"""
import sys

from verify import Verifier
from simant_ref import cheats
from simant_ref.state import G, T
import test_sim

# UI: "CHEAT %d" (f_277da), the messages (thunk 0x2f6ea → f_71b1a), joke's screen effects (f_0151c is
# already stubbed by test_sim)
STUBS = test_sim.STUBS + (0x277da, 0x2f6ea, 0x00ed0, 0x0125f)

SEQUENCES = [(c, c) for c in cheats.CODES] + [
    ('broken prefix', 'hex'), ('repeated first key', 'hhole'), ('prefix, then a code', 'jojoel'),
    ('will twice', 'willwill'), ('mick twice', 'mickmick'), ('jenn twice', 'jennjenn'),
    ('susi twice', 'susisusi'), ('eggs twice', 'eggseggs'), ('unknown keys', 'xyz!'),
]


def clear(set16, args):
    set16(T, cheats.LEN, 0)
    set16(G, cheats.BUF, 0)
    set16(G, cheats.BUF + 2, 0)


def port(st, key):
    st.player = test_sim.Player()
    cheats.cheat(st, key)


def main():
    filters = sys.argv[1:]
    v = Verifier()
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    ok = True
    for label, keys in SEQUENCES:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(0x6a920, port, args_fn=lambda st, i, keys=keys: (ord(keys[i]),), repeat=len(keys), label=label,
                      pre=clear, pre_once=True, ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
