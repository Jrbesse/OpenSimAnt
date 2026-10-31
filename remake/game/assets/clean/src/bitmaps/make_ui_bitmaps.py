"""make_ui_bitmaps.py: writes every HCEGANT_<id>.pix of the UI bitmaps (passes 1-2: groups A, B, C, D, E, H),
runs the spec's checks as assertions, and writes preview.png.  Run from anywhere:  python make_ui_bitmaps.py
Groups are functions group_x(reg) in grp_*.py; add a group by writing one and listing it in GROUPS (order matters:
a group may use pictures made by an earlier one, e.g. 5000 uses the icons 5100..5106)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from uilib import Reg, run_generic_checks, write_pix  # noqa: E402
import grp_abc  # noqa: E402

GROUPS = [
    ('A window chrome', grp_abc.group_a),
    ('C tool icons', grp_abc.group_c),
    ('B menus, palettes, help pages', grp_abc.group_b),
]
try:
    import grp_deh
    GROUPS += [('D Edit strip', grp_deh.group_d), ('E Map toolbar', grp_deh.group_e), ('H Status, Game Over', grp_deh.group_h)]
except ImportError:
    pass


def build():
    reg = Reg()
    for name, fn in GROUPS:
        fn(reg)
    return reg


def main():
    reg = build()
    n = run_generic_checks(reg)
    for bid in sorted(reg.img):
        write_pix(os.path.join(HERE, 'HCEGANT_%d.pix' % bid), reg.img[bid],
                  'HCEGANT_%d: %s' % (bid, reg.meta[bid]['what']))
    print('wrote %d bitmaps; checks passed: sizes/masks/colours %d, flat rects %d, icon spots %d, leader tips %d, '
          'inverted rects %d, group checks %d' % (n, n, len(reg.flat), len(reg.spots), len(reg.tips), len(reg.inv),
                                                  len(reg.checks)))
    try:
        import preview
        preview.make(reg, os.path.join(HERE, 'preview.png'))
    except ImportError:
        pass


if __name__ == '__main__':
    main()
