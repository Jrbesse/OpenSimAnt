"""Differential test: reference terrain generator vs. the original f_73c33 running in the emulator.

python test_terrain.py [n_seeds]
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 're'))

import emu                                   # noqa: E402
from emu import SIM, G, DGROUP              # noqa: E402
from simant_ref.rng import Lfsr             # noqa: E402
from simant_ref.terrain import Patch, generic_patch   # noqa: E402

GENERIC_PATCH = 0x73c33


def original(e, seed):
    e.write(SIM, 0x0180, bytes(0x2000))      # surface
    e.write(SIM, 0x6180, bytes(0x2000))      # occupancy
    e.set16(G, 0xf24, 0)                     # yard, not house
    e.set16(DGROUP, 0x8ba2, seed)
    e.call_lin(GENERIC_PATCH)
    return e.read(SIM, 0x0180, 0x2000), e.w16(DGROUP, 0x8ba2)


def ported(seed):
    p = Patch()
    rng = Lfsr(seed)
    generic_patch(p, rng)
    return bytes(p.surface), rng.x


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    e = emu.SimEmu()
    seeds = [0x1234, 1, 0x7fff] + [random.Random(42 + i).randrange(1, 0x10000) for i in range(n - 3)]
    bad = 0
    for s in seeds:
        (og, orng), (pg, prng) = original(e, s), ported(s)
        if og != pg or orng != prng:
            bad += 1
            diffs = [(i // 64, i % 64, og[i], pg[i]) for i in range(len(og)) if og[i] != pg[i]]
            print(f'seed {s:#06x}: {len(diffs)} cells differ, rng {orng:#06x} vs {prng:#06x}; first: {diffs[:5]}')
    print(f'{len(seeds) - bad}/{len(seeds)} seeds identical')
    return bad == 0


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
