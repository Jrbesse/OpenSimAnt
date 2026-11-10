"""Verify the colony module against the original (python test_colony.py)."""
import sys

from verify import Verifier
from simant_ref import colony as c

msgs = []
noop_status = lambda *a: None


def main():
    v = Verifier()
    ok = True
    ok &= v.check(0x08c12, c.health_decay, label='HealthDecay', repeat=3)
    ok &= v.check(0x08adb, c.reset_census, label='ResetCensus')
    ok &= v.check(0x08b25, c.stats_from_census, label='StatsFromCensus')
    ok &= v.check(0x0def0, c.spawn_avenger, label='SpawnAvenger')
    ok &= v.check(0x0be82, lambda st: c.census(st, msgs.append), label='Census')
    ok &= v.check(0x1395b, c.black_priority, label='BlackPriority')
    ok &= v.check(0x13be3, lambda st: c.red_priority(st, noop_status), label='RedPriority', repeat=5)
    ok &= v.check(0x13a28, c.choose_hatch_caste, label='ChooseHatchCaste')
    ok &= v.check(0x13b26, c.choose_manual_job, label='ChooseManualJob')
    ok &= v.check(0x13832, lambda st: c.colony_advisor(st, noop_status), label='ColonyAdvisor', repeat=5)
    ok &= v.check(0x6bca5, lambda st, n, s: c.drop_food(st, c._s16(n), s), lambda st, i: (0x96, 1),
                  label='DropFood(150)', repeat=2)
    ok &= v.check(0x6bca5, lambda st, n, s: c.drop_food(st, c._s16(n), s), lambda st, i: (0xffff, 0),
                  label='DropFood(start)')
    print('ALL OK' if ok else 'SOME MISMATCHES')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
