"""make_yard_bitmaps.py: writes the yard bitmaps <id>.pix of docs/clean_pack/yard_bitmaps.md that exist so far
(passes 1 and 2: 7000, 7001, 7003, 7020, 7021, 7022, 7005, 7006, 7007, 1260, 7010, 7011), runs the spec's checks as
assertions and writes preview_yard.png.  Run from anywhere:

    python make_yard_bitmaps.py            # all pictures + the crops 17006 / 17007 if they exist + preview_yard.png
    python make_yard_bitmaps.py --crops    # only: replace the existing 17006 / 17007 by crops of 7010 (run after the interface batch)
    python make_yard_bitmaps.py --no-preview

Passes are modules with a build(reg) function (registers pictures and checks), listed in PASSES in order: later passes
(3: the people and the door / room patches, 4: the animals, 5: the spider and the map-window actors) are added by writing a module
and listing it.  A pass may use what an earlier one left on `reg` (reg.worlds: the rendered scenes, for the patches).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from uilib import Reg, run_generic_checks, write_pix  # noqa: E402
import yard_pass1  # noqa: E402
import yard_pass2  # noqa: E402
import yard_pass3  # noqa: E402
import yard_pass4  # noqa: E402
import yard_pass5  # noqa: E402

PASSES = [
    ('1 scenery (A, C)', yard_pass1),
    ('2 toolbar (D)', yard_pass2),
    ('3 people and door / room patches (E, B)', yard_pass3),
    ('4 animals (F, G)', yard_pass4),
    ('5 spider and map-window actors (H, I)', yard_pass5),
]


def build():
    reg = Reg()
    for name, mod in PASSES:
        mod.build(reg)
    return reg


def write_crops(t7010):
    """17006 / 17007 (the tutorial's House / Patch button pictures) = crops of 7010; only replaced when they already exist."""
    out = []
    for bid in sorted(yard_pass2.CROPS):
        path = os.path.join(HERE, '%d.pix' % bid)
        if not os.path.exists(path):
            print('crop %d: %s does not exist (interface batch not run yet): left alone; run  python make_yard_bitmaps.py --crops  later' % (bid, os.path.basename(path)))
            continue
        c = yard_pass2.crop_of(t7010, bid)
        what = 'tutorial: yard window %s button (a crop of 7010, pixels %s)' % ('House' if bid == 17006 else 'Patch', yard_pass2.CROPS[bid])
        write_pix(path, c, '%d: %s' % (bid, what))
        print('crop %d: REPLACED %s by the crop of 7010 %s (%d x %d)' % (bid, os.path.basename(path), yard_pass2.CROPS[bid], c.w, c.h))
        out.append(bid)
    return out


def main(argv):
    if '--crops' in argv:
        reg = Reg()
        t, o = yard_pass2.build(reg)
        yard_pass2.check_pass2(reg)
        write_crops(t)
        return
    reg = build()
    n = run_generic_checks(reg)
    for bid in sorted(reg.img):
        write_pix(os.path.join(HERE, '%d.pix' % bid), reg.img[bid], '%d: %s' % (bid, reg.meta[bid]['what']))
    print('wrote %d yard bitmaps; checks passed: sizes / masks / colours %d, flat rects %d, pass checks %d' % (n, n, len(reg.flat), len(reg.checks)))
    st = getattr(reg, 'stats', {})
    print('  7000 / 7001 identical pixels: %.1f %%; furniture clear of the person\'s route by >= %.1f px' % (100 * st.get('equal_7000_7001', 0), st.get('route_clear_px', 0)))
    for k, v in st.get('contrast', {}).items():
        print('  contrast %-7s top2/light/dark: %s' % (k, v))
    write_crops(reg.img[7010])
    if '--no-preview' not in argv:
        try:
            import preview_yard
            preview_yard.make(reg, os.path.join(HERE, 'preview_yard.png'))
        except ImportError:
            pass


if __name__ == '__main__':
    main(sys.argv[1:])
