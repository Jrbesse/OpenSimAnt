"""Verify the hidden debug commands against the original: add ants (f_015be), kill ants (f_0161f), clear
food (f_01707) and the random action (f_022bc, each of its 15 cases via the C rand() state DS:7BBE).

python test_debug.py [name-substring ...]
"""
import sys

from verify import Verifier
from simant_ref import debug
from simant_ref.state import DS, G, T
import test_sim

# UI: f_00f02 (a sound), f_00ed0 (music), thunk 0x2f6ea (f_71b1a messages)
STUBS = test_sim.STUBS + (0x00f02, 0x00ed0, 0x2f6ea)


def crt_rand(seed):
    seed = (seed * 214013 + 2531011) & 0xffffffff
    return (seed >> 16) & 0x7fff


def seeds_for_cases(n):
    found = {}
    s = 1
    while len(found) < n:
        found.setdefault(crt_rand(s) % n, s)
        s += 1
    return [found[k] for k in range(n)]


def setter(g=(), t=(), crt=None):
    def pre(set16, args):
        for off, val in g:
            set16(G, off, val)
        for off, val in t:
            set16(T, off, val)
        if crt is not None:
            set16(DS, 0x7bbe, crt & 0xffff)
            set16(DS, 0x7bc0, crt >> 16)
    return pre


def port(fn):
    def run(st, *args):
        st.player = test_sim.Player()
        fn(st, *args)
    return run


CASES = [
    ('add black', 0x015be, port(lambda st, c: debug.add_ants(st, c == 1)), (1,), setter()),
    ('add red', 0x015be, port(lambda st, c: debug.add_ants(st, c == 1)), (0,), setter()),
    ('fill black', 0x015be, port(lambda st, c: debug.add_ants(st, c == 1)), (1,), setter(t=((0x798, 1),))),
    ('fill red', 0x015be, port(lambda st, c: debug.add_ants(st, c == 1)), (0,), setter(t=((0x798, 1),))),
    ('kill black', 0x0161f, port(lambda st, c: debug.kill_ants(st, c == 1)), (1,), setter()),
    ('kill red', 0x0161f, port(lambda st, c: debug.kill_ants(st, c == 1)), (0,), setter()),
    ('kill red, spider player', 0x0161f, port(lambda st, c: debug.kill_ants(st, c == 1)), (0,),
     setter(g=((0xa06, 1), (0x48c, 1), (0xf12, 0x400), (0xf34, 0x200)))),
    ('kill red, yellow ant on the surface', 0x0161f, port(lambda st, c: debug.kill_ants(st, c == 1)), (0,),
     setter(g=((0xa06, 0), (0x48c, 1)))),
    # a count past the live ants exposes old slots: more than 51 to kill
    ('kill black, many', 0x0161f, port(lambda st, c: debug.kill_ants(st, c == 1)), (1,), setter(g=((0xd6a, 300),))),
    ('kill red, many', 0x0161f, port(lambda st, c: debug.kill_ants(st, c == 1)), (0,),
     setter(g=((0xd6a, 300), (0x48c, 1)))),
    ('clear food', 0x01707, port(debug.clear_food), (), setter()),
] + [(f'random action {k}', 0x022bc, port(debug.random_action), (), setter(crt=s))
     for k, s in enumerate(seeds_for_cases(15))]


def main():
    filters = sys.argv[1:]
    v = Verifier()
    test_sim.prepare(v)
    v.extra_stubs = STUBS
    def fill_first(set16, args):                    # the original side: fill up with black ants first
        set16(T, 0x798, 1)
        v.e.call_lin(0x015be, (1,))

    def fill_then_kill(st, c):
        debug.add_ants(st, True)
        debug.kill_ants(st, c == 1)
    ok = True
    for label, lin, fn, args, pre in CASES + [
            ('fill, then kill black (51 at most)', 0x0161f, port(fill_then_kill), (1,), fill_first)]:
        if filters and not any(f in label for f in filters):
            continue
        ok &= v.check(lin, fn, args_fn=lambda st, i, args=args: args, label=label, pre=pre,
                      ignore=test_sim.SCREEN)
    print('ALL OK' if ok else 'FAILURES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
