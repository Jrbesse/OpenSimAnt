"""make_ency_bitmaps.py - writes the encyclopedia's SHARED_<id>.pix files and runs every check.
Run:  python make_ency_bitmaps.py          (from any folder; no arguments)
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ency_lib as L
import ency_check as C

PASSES = ['ency_p1', 'ency_p2', 'ency_p3', 'ency_p4', 'ency_p5']


def build_all():
    built, descs = {}, {}
    for name in PASSES:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name == name:
                print('(%s not written yet)' % name)
                continue
            raise
        if hasattr(mod, 'build'):
            for ident, (cv, desc) in mod.build().items():
                built[ident] = cv
                descs[ident] = desc
    return built, descs


def main():
    built, descs = build_all()
    errs, _ = C.check_all(built)
    for ident, cv in sorted(built.items()):
        L.write_pix(ident, cv, descs[ident])
    missing = sorted(set(C.SIZES) - set(built))
    print('written %d of %d files' % (len(built), len(C.SIZES)))
    if missing:
        print('not yet made:', missing)
    if errs:
        print('CHECKS FAILED (%d):' % len(errs))
        for e in errs:
            print('  ', e)
        sys.exit(1)
    print('all checks pass')


if __name__ == '__main__':
    main()
