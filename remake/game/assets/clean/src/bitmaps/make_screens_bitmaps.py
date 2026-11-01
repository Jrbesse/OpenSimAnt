"""make_screens_bitmaps.py: writes the 24 HCEGANT_<id>.pix of docs/clean_pack/screens_bitmaps.md (the title 2000 / 2001,
Select a Game 2500, the About box 3000 / 3001, the player's-ant pictures 9100 / 9101 / 9110 / 9111, the death icons
9150..9156, the ant lion scene 9200..9203, the spider scene 12000..12003), runs the spec's checks as assertions and
writes preview_screens.png.   Run from anywhere:   python make_screens_bitmaps.py
Modules: screens_lib (canvas, ant drawing program, textures), screens_ab (title, Select, About), screens_icons (E),
screens_ants (D), screens_scenes (F, G).  Needs Python 3, numpy and Pillow."""
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import screens_lib as L  # noqa: E402
import screens_ab as AB  # noqa: E402
import screens_icons as IC  # noqa: E402
import screens_ants as AN  # noqa: E402
import screens_scenes as SC  # noqa: E402
from uilib import contrast  # noqa: E402

HEX = '0123456789abcdef'

SIZES = {
    2000: (512, 172), 2001: (512, 200), 2500: (320, 256), 3000: (320, 200), 3001: (254, 109),
    9100: (200, 161), 9101: (200, 161), 9110: (200, 161), 9111: (80, 89),
    9150: (32, 32), 9151: (32, 32), 9152: (32, 32), 9153: (32, 32), 9154: (32, 32), 9155: (32, 32), 9156: (32, 32),
    9200: (200, 160), 9201: (136, 121), 9202: (136, 108), 9203: (136, 108),
    12000: (189, 171), 12001: (98, 80), 12002: (98, 80), 12003: (98, 80),
}
WHAT = {
    2000: 'title screen, top part (rows 0..171 of the 512 x 372 canvas)',
    2001: 'title screen, bottom part (rows 172..371 of the 512 x 372 canvas)',
    2500: 'Select a Game dialog: heading, five picture buttons with captions, Cancel',
    3000: 'About box background: heading, recessed well, footer line',
    3001: 'About box name card (shown inside the well)',
    9100: "the player's ant after the attack, lying still (caption strip rows 0..14 plain)",
    9101: 'a newly hatched ant next to its torn cocoon (caption strip rows 0..14 plain)',
    9110: "a black nestmate feeds the player's ant: the drop in the nestmate's mouth",
    9111: 'patch over 9110 at (72,62): the drop has passed to the yellow ant',
    9150: 'icon: drowned', 9151: 'icon: poisoned by insecticide', 9152: 'icon: run over by the lawn mower',
    9153: 'icon: mower variant with flying clippings', 9154: 'icon: starved', 9155: 'icon: stepped on',
    9156: 'icon: electrocuted',
    9200: 'ant lion scene, base picture (at rest)', 9201: 'ant lion scene, patch at (38,39): rears up',
    9202: 'ant lion scene, patch at (38,52): jaws clamped, head left',
    9203: 'ant lion scene, patch at (38,52): jaws clamped, head right',
    12000: 'spider scene, base picture (jaws open)', 12001: 'spider scene, patch at (46,77): jaws fully open',
    12002: 'spider scene, patch at (46,77): fangs half closed', 12003: 'spider scene, patch at (46,77): fangs closed',
}
ALLOWED_TEXT = {
    2000: {'OpenSimAnt', 'an open-source remake'},
    2500: {AB.HEADING, 'Tutorial', 'Quick Game', 'Full Game', 'Experimental', 'Load Game', 'Cancel'}
          | {ln for v in AB.DESC.values() for ln in v},
    3000: {AB.ABOUT_HEAD, AB.ABOUT_FOOT},
    3001: {'OpenSimAnt', 'an open-source remake', 'a fan project'},
}
PATCHES = {9201: (38, 39), 9202: (38, 52), 9203: (38, 52)}      # asserted against the spec
PATCHES_G = {12001: (46, 77), 12002: (46, 77), 12003: (46, 77)}


def build():
    L.LETTERED.clear()
    pics = {}
    canvas, info = AB.title_canvas()
    assert (canvas.w, canvas.h) == (512, 372)
    pics[2000] = canvas.crop(0, 0, 512, 172)
    pics[2001] = canvas.crop(0, 172, 512, 372)
    pics[2500] = AB.select_card()
    pics[3000] = AB.about_bg()
    pics[3001] = AB.about_card()
    pics.update(IC.make_icons())
    pics[9100] = AN.scene_9100()
    pics[9101] = AN.scene_9101()
    pics[9110] = AN.scene_9110()
    pics[9111] = AN.scene_9111()
    F, rf = SC.render_F_all()
    G, rg = SC.render_G_all()
    pics.update(F)
    pics.update(G)
    return pics, canvas, info


def A(pics, pid):
    return pics[pid].arr()


def ring(a):
    return np.concatenate([a[0, :], a[-1, :], a[:, 0], a[:, -1]])


def colours(a):
    return set(int(v) for v in np.unique(a))


def freq(a, skip=()):
    vals, cnt = np.unique(a, return_counts=True)
    d = {int(v): int(c) for v, c in zip(vals, cnt) if int(v) not in skip}
    return d


def run_checks(pics, canvas, info):
    n = 0
    # 1. sizes, characters, ids
    assert set(pics) == set(SIZES), set(pics) ^ set(SIZES)
    assert len(pics) == 24
    for pid, cv in pics.items():
        a = cv.arr()
        assert (a.shape[1], a.shape[0]) == SIZES[pid], (pid, a.shape, SIZES[pid])
        assert a.min() >= 0 and a.max() <= 15, pid
    n += 1
    # 2. identity: every lettered string is allowed for its picture, no forbidden word
    for pid, s in L.LETTERED:
        assert pid in ALLOWED_TEXT, ('lettering in a picture that must have none', pid, s)
        assert s in ALLOWED_TEXT[pid], (pid, s)
        assert 'SimAnt' not in s.replace('OpenSimAnt', ''), s
        assert 'maxis' not in s.lower(), s
        assert not re.search(r'\d{4}', s), s
    texts = {}
    for pid, s in L.LETTERED:
        texts.setdefault(pid, set()).add(s)
    assert texts[2000] == ALLOWED_TEXT[2000], texts[2000]
    assert texts[3000] == ALLOWED_TEXT[3000], texts[3000]
    assert texts[3001] == ALLOWED_TEXT[3001], texts[3001]
    assert texts[2500] == ALLOWED_TEXT[2500], texts[2500] ^ ALLOWED_TEXT[2500]
    assert all(pid < 9000 for pid, _ in L.LETTERED)
    n += 1
    # 3. the title
    ca = canvas.arr()
    assert (ring(ca) == 15).all()
    assert (A(pics, 2000) == ca[0:172]).all() and (A(pics, 2001) == ca[172:372]).all()
    black = (ca == 15).mean()
    assert black <= 0.40, black
    wx, wy = info[2], info[3]
    ww, wh = info[0], info[1]
    assert wh >= 22, wh
    assert not (wy <= 172 <= wy + wh), 'the wordmark touches the seam'
    reg = ca[max(0, wy - 8):wy + wh + 8, max(0, wx - 8):wx + ww + 8]
    assert len(colours(reg) & {0, 1, 2, 15}) >= 3
    others = colours(reg) - {0, 1, 2}
    assert all(contrast(1, c) >= 3.0 for c in others), [(c, contrast(1, c)) for c in others]
    # the small line: white on dark
    tag = ca[104:124, 28:300]
    assert all(contrast(0, c) >= 3.0 for c in colours(tag) - {0}), colours(tag)
    # no thin line exactly on the seam: no long run of one colour on row 171 or 172 that differs from both neighbours
    for row in (171, 172):
        iso = (ca[row] != ca[row - 1]) & (ca[row] != ca[row + 1])
        run = best = 0
        for v in iso:
            run = run + 1 if v else 0
            best = max(best, run)
        assert best < 40, (row, best)
    n += 1
    # 4. Select a Game
    s = A(pics, 2500)
    assert (ring(s) == 12).all()
    allowed = np.zeros(s.shape, dtype=bool)
    for name, r in AB.SEL.items():
        allowed[r[1]:r[3], r[0]:r[2]] = True
    allowed[AB.HEADING_ROWS[0]:AB.HEADING_ROWS[1], :] = True
    for name, z in AB.ZONES.items():
        allowed[z[1]:z[3], z[0]:z[2]] = True
    assert (s[~allowed] == 12).all()
    # heading ink: rows 2..22, 9..16 tall, centred
    hs = s[0:25, :]
    ys, xs = np.nonzero(hs != 12)
    assert ys.min() >= 2 and ys.max() <= 22, (ys.min(), ys.max())
    assert 9 <= ys.max() - ys.min() + 1 <= 16
    assert abs((xs.min() + xs.max()) / 2.0 - 159.5) <= 2
    for name, r in AB.SEL.items():
        t = s[r[1]:r[3], r[0]:r[2]]
        if name == 'Cancel':
            assert (ring(t) == 15).all()
            assert (t[1:-1, 1:-1] == 15).any()
            assert t.shape == (17, 66)
            continue
        assert (ring(t) == 15).all(), name
        inner = t[1:-1, 1:-1]
        assert set(ring(inner)) <= {0, 13, 14}, (name, set(ring(inner)))
        assert len(colours(t)) >= 6, (name, colours(t))
        assert max(freq(t).values()) / t.size <= 0.70, (name, freq(t))
    # caption ink outside the tiles / heading lies in its own zone only
    for name, z in AB.ZONES.items():
        zone = s[z[1]:z[3], z[0]:z[2]]
        assert (zone != 12).any(), name
        ink = set(int(v) for v in np.unique(zone)) - {12}
        assert ink <= {15, 6}, (name, ink)
    for ink in (15, 6):
        assert contrast(12, ink) >= 3.0
    cancel_ink = contrast(12, 15)
    assert cancel_ink >= 3.0
    n += 1
    # 5. the About box
    b = A(pics, 3000)
    assert (ring(b) == 12).all()
    x0, y0, x1, y1 = 33, 61, 287, 171
    assert (b[y0:y1, x0:x1] == 12).all()
    top = (b[59:61, 31:289] == 0).mean()
    left = (b[59:173, 31:33] == 0).mean()
    bot13 = (b[171, 31:290] == 13).mean()
    bot14 = (b[172, 31:290] == 14).mean()
    r13 = (b[59:173, 287] == 13).mean()
    r14 = (b[59:173, 288] == 14).mean()
    for nm, v in (('top', top), ('left', left), ('bot13', bot13), ('bot14', bot14), ('r13', r13), ('r14', r14)):
        assert v >= 0.95, (nm, v)
    near = np.zeros(b.shape, dtype=bool)
    near[y0 - 8:y1 + 8, x0 - 8:x1 + 8] = True
    bev = np.zeros(b.shape, dtype=bool)
    bev[59:61, 31:289] = True
    bev[59:173, 31:33] = True
    bev[171:173, 31:290] = True
    bev[59:173, 287:289] = True
    assert (b[near & ~bev] == 12).all(), np.argwhere((b != 12) & near & ~bev)[:5]
    ys, xs = np.nonzero(b[0:48] != 12)
    head = b[0:44]
    hy, hx = np.nonzero(head != 12)
    assert hy.min() >= 3 and hy.max() <= 38 and 16 <= hy.max() - hy.min() + 1 <= 26, (hy.min(), hy.max())
    assert abs((hx.min() + hx.max()) / 2.0 - 159.5) <= 3
    foot = b[174:200]
    fy, fx = np.nonzero(foot != 12)
    fy = fy + 174
    assert fy.min() >= 178 and fy.max() <= 197 and 8 <= fy.max() - fy.min() + 1 <= 12, (fy.min(), fy.max())
    assert set(int(v) for v in np.unique(foot)) <= {12, 15}
    assert abs((fx.min() + fx.max()) / 2.0 - 159.5) <= 3
    for c in (6, 5):
        assert contrast(12, c) >= 3.0
    c = A(pics, 3001)
    assert (ring(c) == 12).all() and (c[108] == 12).all()
    assert (c[0:6] == 12).all() and (c[103:] == 12).all() and (c[:, 0:6] == 12).all() and (c[:, 248:] == 12).all()
    emblem = c[:, 0:76]
    eh = np.nonzero((emblem != 12).any(axis=1))[0]
    assert 40 <= eh.max() - eh.min() + 1 <= 70
    assert (emblem != 12).sum() / c.size <= 0.40
    assert len([1 for pid, s_ in L.LETTERED if pid == 3001]) == 3
    for col in (6, 5, 15, 14):
        assert contrast(12, col) >= 3.0
    n += 1
    # 6. the icons
    six = [9150, 9151, 9152, 9154, 9155, 9156]
    grounds = {}
    for pid in six + [9153]:
        a = A(pics, pid)
        assert (ring(a) == 15).all(), pid
        assert len(colours(a)) >= 4, pid
        f = freq(a, skip=(15,))
        grounds[pid] = max(f, key=f.get)
    assert len({grounds[p] for p in six}) == 6, grounds
    assert grounds[9153] == grounds[9152]
    assert (A(pics, 9153) == A(pics, 9152)).mean() >= 0.60
    assert not (A(pics, 9153) == A(pics, 9152)).all()
    for i, p in enumerate(sorted(six + [9153])):
        for q in sorted(six + [9153])[i + 1:]:
            assert not (A(pics, p) == A(pics, q)).all(), (p, q)
    n += 1
    # 7. the player's-ant pictures
    for pid in (9100, 9101):
        a = A(pics, pid)
        assert not ((a[0:15] == 1) | (a[0:15] == 15)).any(), pid
    for pid in (9100, 9101, 9110):
        assert (A(pics, pid) == 1).any(), pid
    base = A(pics, 9110)
    r = AN.PATCH_9111
    crop = base[r[1]:r[3], r[0]:r[2]]
    p = A(pics, 9111)
    assert p.shape == crop.shape
    assert (ring(p) == ring(crop)).all()
    assert (p != crop).mean() >= 0.10, (p != crop).mean()
    assert {8, 9} <= colours(p) and {8, 9} <= colours(base)
    assert r == (72, 62, 152, 151)
    n += 1
    # 8. the patches of the scenes
    assert AN.PATCH_9111 == (72, 62, 152, 151)
    assert SC.PATCHES_F == PATCHES and SC.PATCH_G == (46, 77, 144, 157)
    assert SC.PATCH_SIZE_F == {9201: (136, 121), 9202: (136, 108), 9203: (136, 108)}
    b0 = A(pics, 9200)
    for pid, (px, py) in PATCHES.items():
        pa = A(pics, pid)
        assert (px + pa.shape[1], py + pa.shape[0]) == (174, 160), pid
        bc = b0[py:py + pa.shape[0], px:px + pa.shape[1]]
        assert (ring(pa) == ring(bc)).all(), pid
    assert (A(pics, 9201)[0:13] == b0[39:52, 38:174]).all()      # rows 39..51 are the same as the base: no stale strip
    assert (b0 == 1).sum() > 0 and (A(pics, 9201) == 1).sum() > 0
    assert (A(pics, 9202) == 1).sum() < 30 and (A(pics, 9203) == 1).sum() < 30
    p2, p3 = A(pics, 9202), A(pics, 9203)
    p1 = A(pics, 9201)[13:]
    assert (p2 != p3).mean() >= 0.05 and (p1 != p2).mean() >= 0.05 and (p1 != p3).mean() >= 0.05
    g0 = A(pics, 12000)
    gr = SC.PATCH_G
    gc = g0[gr[1]:gr[3], gr[0]:gr[2]]
    gp = {pid: A(pics, pid) for pid in (12001, 12002, 12003)}
    for pid, pa in gp.items():
        assert pa.shape == (80, 98)
        assert (ring(pa) == ring(gc)).all(), pid
    assert (gp[12001] == gc).all()
    ids = (12001, 12002, 12003)
    for i in range(3):
        for j in range(i + 1, 3):
            assert (gp[ids[i]] != gp[ids[j]]).mean() >= 0.05, (ids[i], ids[j])
    # the sky is flat in the patch's outer 3 px at the left, right and bottom edges, wherever it is not the spider
    for strip in (gc[:, 0:3], gc[:, -3:], gc[-3:, :]):
        assert colours(strip) <= {5, 14, 15, 10, 13, 2, 12, 11, 0}
    n += 1
    # 9. distinct, not flat
    keys = {}
    for pid in pics:
        a = A(pics, pid)
        assert len(colours(a)) > 1, pid
        k = (a.shape, a.tobytes())
        assert k not in keys, (pid, keys.get(k))
        keys[k] = pid
    n += 1
    return n


def write_all(pics):
    for pid, cv in sorted(pics.items()):
        a = cv.arr()
        lines = ['# HCEGANT_%d: %s' % (pid, WHAT[pid]), '# %d x %d' % (a.shape[1], a.shape[0])]
        for y in range(a.shape[0]):
            lines.append(''.join(HEX[v] for v in a[y]))
        with open(os.path.join(HERE, 'HCEGANT_%d.pix' % pid), 'w', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')


def reread(pics):
    """The written files parse back to the same pictures (exact size, no '.', equal rows)."""
    for pid, cv in pics.items():
        rows = [ln for ln in open(os.path.join(HERE, 'HCEGANT_%d.pix' % pid)).read().split('\n') if ln and not ln.startswith('#')]
        w, h = SIZES[pid]
        assert len(rows) == h and all(len(r) == w for r in rows), pid
        assert not any('.' in r for r in rows), pid
        back = np.array([[int(ch, 16) for ch in r] for r in rows])
        assert (back == cv.arr()).all(), pid


def main():
    pics, canvas, info = build()
    n = run_checks(pics, canvas, info)
    write_all(pics)
    reread(pics)
    print('%d check groups passed; %d files written' % (n, len(pics)))
    try:
        import screens_preview
        screens_preview.make(pics)
    except ImportError:
        pass


if __name__ == '__main__':
    main()
