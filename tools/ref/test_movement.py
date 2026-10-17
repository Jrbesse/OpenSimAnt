"""Verify the surface movement helpers against the original (python test_movement.py)."""
import random
import sys

from verify import Verifier
from simant_ref import movement as mv


def pos(i):
    r = random.Random(i)
    edges = [(0, 0), (0, 63), (127, 0), (127, 63), (0, r.randrange(64)), (127, r.randrange(64)),
             (r.randrange(128), 0), (r.randrange(128), 63)]
    if i % 5 == 0:
        return edges[(i // 5) % len(edges)]
    return r.randrange(128), r.randrange(64)


def args_abd(st, i):
    a, b = pos(i)
    return (a, b, random.Random(i + 99).randrange(8))


def args_abdt(st, i):
    a, b, d = args_abd(st, i)
    return (a, b, d, (0x80 if i % 2 else 0) | (2 << 3) | d)


def main():
    v = Verifier()
    ok = True
    n = 40
    ok &= v.check(0x148d8, lambda st, a, b: mv.edge_dir(a, b, st), lambda st, i: pos(i), label='EdgeDir', repeat=n)
    ok &= v.check(0x146b9, mv.next_dir, args_abd, label='NextDir', repeat=n)
    ok &= v.check(0x0ab05, mv.turn_aside, lambda st, i: (i % 8,), label='TurnAside', repeat=n)
    ok &= v.check(0x0c9a1, lambda st, a, b, c, d: mv.dir_to(a, b, c, d), lambda st, i: pos(i) + pos(i + 1000),
                  label='DirTo', repeat=n)
    ok &= v.check(0x142c5, mv.forage_dir, args_abdt, label='ForageDir', repeat=n)
    ok &= v.check(0x1445a, mv.home_dir, args_abdt, label='HomeDir', repeat=n)
    ok &= v.check(0x145fc, mv.alarm_dir, args_abd, label='AlarmDir', repeat=n)
    ok &= v.check(0x146fc, mv.black_guard_dir, args_abd, label='BlackGuardDir', repeat=n)
    ok &= v.check(0x147fe, mv.red_guard_dir, args_abd, label='RedGuardDir', repeat=n)
    ok &= v.check(0x0acfb, lambda st, a, b: int(mv.at_nest_entrance(st, a, b)), lambda st, i: pos(i),
                  label='AtNestEntrance', repeat=n)
    ok &= v.check(0x0eea1, mv.surface_ant_at, lambda st, i: (st.u8(0x3e1d, 0xa180 + i), st.u8(0x3e1d, 0xa569 + i))
                  if i % 2 else pos(i), label='SurfaceAntAt', repeat=n)
    ok &= v.check(0x141a6, mv.state_for_caste,
                  lambda st, i: ((2, 6, 4, 8, 12, 1, 3)[i % 7], 0x80 if i % 2 else 0), label='StateForCaste', repeat=n)

    def food_args(st, i):
        # cells that hold food crumbs, if any
        cells = [(a, b) for a in range(128) for b in range(64) if 0x48 <= st.grid(0x180, a, b) <= 0x4b]
        return cells[i % len(cells)] if cells else pos(i)
    ok &= v.check(0x0c618, mv.take_food_at, food_args, label='TakeFoodAt', repeat=10)
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
