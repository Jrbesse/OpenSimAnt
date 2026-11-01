"""ency_check.py - the assertions of make_ency_bitmaps.py (text only)."""
import os
import re

import numpy as np

import ency_lib as L

SIZES = {
    150: (102, 116), 400: (76, 90), 500: (109, 120), 600: (93, 90), 700: (101, 30), 850: (128, 113),
    170: (39, 15), 160: (37, 15), 129: (73, 8), 21000: (7, 7), 21001: (7, 7), 21002: (7, 7), 21003: (7, 7),
    410: (92, 48), 420: (141, 54), 440: (128, 51), 460: (155, 56), 128: (223, 86), 200: (184, 89), 210: (153, 137),
    213: (235, 45), 220: (258, 93), 230: (252, 103),
    300: (137, 165), 320: (69, 22), 330: (108, 70), 340: (94, 66),
    610: (141, 117), 620: (139, 64), 630: (112, 65), 640: (122, 110),
    510: (222, 101), 520: (167, 149), 530: (218, 69), 540: (111, 105), 550: (194, 103), 560: (135, 87),
    710: (299, 68), 720: (302, 53), 880: (290, 141),
}
FORBIDDEN = ['simant', 'maxis', 'electronic arts', 'copyright', '(c)', 'inc.', 'trademark', 'wright', 'sim ant', 'opensimant',
             'formica']


def check_all(built):
    """built: {id: Cv}.  returns a list of problems (empty = all fine) and a list of report lines"""
    errs, rep = [], []
    for ident, cv in built.items():
        e = check_one(ident, cv)
        errs += ['%d: %s' % (ident, x) for x in e]
    return errs, rep


def check_one(ident, cv):
    errs = []
    if (cv.w, cv.h) != SIZES[ident]:
        errs.append('size %dx%d, want %dx%d' % (cv.w, cv.h, *SIZES[ident]))
    if cv.a.max() > 1:
        errs.append('value > 1')
    # forbidden words
    low = ' '.join(cv.strings).lower()
    for f in FORBIDDEN:
        if f in low:
            errs.append('forbidden word %r' % f)
    # cut rows / columns
    for r in cv.cut_rows:
        if cv.a[r, :].any():
            errs.append('row %d must be white' % r)
    for c in cv.cut_cols:
        if cv.a[:, c].any():
            errs.append('column %d must be white' % c)
    if 'ground540' in cv.extra:
        g = cv.extra['ground540']
        sub = cv.a[:g, :16]
        if sub.any():
            errs.append('540 columns 0..15 carry ink above the ground line (row %d)' % g)
    # boxes
    rects = []
    for name, b in cv.boxes.items():
        x0, y0, x1, y1 = b['rect']
        if b['rect'][2] > cv.w or b['rect'][3] > cv.h:
            errs.append('box %s outside' % name)
        top = cv.a[y0, x0:x1].mean()
        bot = cv.a[y1 - 1, x0:x1].mean()
        lef = cv.a[y0:y1, x0].mean()
        rig = cv.a[y0:y1, x1 - 1].mean()
        for nm, v in (('top', top), ('bottom', bot), ('left', lef), ('right', rig)):
            if v < 0.95:
                errs.append('box %s %s edge %.0f%% black' % (name, nm, v * 100))
        inner = cv.a[y0 + 1:y1 - 1, x0 + 1:x1 - 1]
        cols = np.nonzero(inner.any(axis=0))[0]
        rows = np.nonzero(inner.any(axis=1))[0]
        if len(cols) == 0:
            errs.append('box %s empty' % name)
        else:
            gl = cols.min()
            gr = inner.shape[1] - 1 - cols.max()
            if gl < 2 or gr < 2:
                errs.append('box %s: lettering %d / %d px from the outline (need 2)' % (name, gl, gr))
            if abs(gl - gr) > 2:
                errs.append('box %s: lettering off centre (%d / %d)' % (name, gl, gr))
            if len(rows) and (rows.min() < 0 or rows.max() > inner.shape[0] - 1):
                errs.append('box %s: lettering rows')
        rects.append((name, b['rect']))
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i][1], rects[j][1]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                errs.append('boxes %s and %s overlap' % (rects[i][0], rects[j][0]))
    # unlisted rectangles
    known = {(r[0], r[1]) for _, r in rects}
    if 'button' in cv.extra:
        known.add(cv.extra['button']['rect'][:2])
    errs += stray_rects(cv, known)
    # leaders
    for ld in cv.leaders:
        tx, ty = ld['tip']
        px0, py0, px1, py1 = ld['part']
        if not (px0 <= tx < px1 and py0 <= ty < py1):
            errs.append('leader of %s: tip %s outside its part %s' % (ld['box'], ld['tip'], ld['part']))
        sx, sy = ld['start']
        bx0, by0, bx1, by1 = cv.boxes[ld['box']]['rect']
        if not (bx0 - 1 <= sx <= bx1 and by0 - 1 <= sy <= by1):
            errs.append('leader of %s does not start at its box' % ld['box'])
        for name, b in cv.boxes.items():
            x0, y0, x1, y1 = b['rect']
            hit = [p for p in ld['pix'] if x0 <= p[0] < x1 and y0 <= p[1] < y1]
            if hit:
                errs.append('leader of %s passes through box %s at %s' % (ld['box'], name, hit[0]))
    # button
    if 'button' in cv.extra:
        x0, y0, x1, y1 = cv.extra['button']['rect']
        if cv.a[0, :].any() or cv.a[cv.h - 1, :].any() or cv.a[:, 0].any() or cv.a[:, cv.w - 1].any():
            errs.append('button: the white border all round is missing')
        wx0, wx1 = cv.extra['button']['word']
        if not (x0 < wx0 and wx1 < x1):
            errs.append('button: word outside the box')
        if cv.a[y0:y1, x0:x1].mean() < 0.6:
            errs.append('button not solid enough')
    # arrows (880)
    for ar in cv.arrows:
        for (x, y) in ar['pix']:
            for name, b in cv.boxes.items():
                if name in (ar['src'], ar['dst']):
                    continue
                x0, y0, x1, y1 = b['rect']
                if x0 <= x < x1 and y0 <= y < y1:
                    errs.append('arrow %s->%s passes through box %s at %s' % (ar['src'], ar['dst'], name, (x, y)))
                    break
        # endpoints on the named boxes' edges
        for key, nm in (('p0', ar['src']), ('p1', ar['dst'])):
            if nm in cv.boxes:
                x0, y0, x1, y1 = cv.boxes[nm]['rect']
                x, y = ar[key]
                if not (x0 - 1 <= x <= x1 and y0 - 1 <= y <= y1):
                    errs.append('arrow %s->%s end %s is not on box %s' % (ar['src'], ar['dst'], key, nm))
    return errs


def stray_rects(cv, known):
    """a black 1-px outlined rectangle of 20 x 10 or more with a mostly white inside that is not a listed box"""
    a = cv.a.astype(bool)
    h, w = a.shape
    hrun = np.zeros((h, w), int)
    vrun = np.zeros((h, w), int)
    for x in range(w - 1, -1, -1):
        hrun[:, x] = np.where(a[:, x], 1 + (hrun[:, x + 1] if x + 1 < w else 0), 0)
    for y in range(h - 1, -1, -1):
        vrun[y, :] = np.where(a[y, :], 1 + (vrun[y + 1, :] if y + 1 < h else 0), 0)
    errs = []
    ys, xs = np.nonzero((hrun >= 20) & (vrun >= 10))
    for y, x in zip(ys, xs):
        if (x, y) in known:
            continue
        if y + 2 >= h or x + 2 >= w or a[y + 1, x + 1] or a[y + 2, x + 2]:
            continue
        for ww in range(20, hrun[y, x] + 1):
            if not a[y:y + vrun[y, x], x + ww - 1].any():
                continue
            for hh in range(10, vrun[y, x] + 1):
                if y + hh > h:
                    break
                if a[y + hh - 1, x:x + ww].all() and a[y:y + hh, x + ww - 1].all():
                    inner = a[y + 1:y + hh - 1, x + 1:x + ww - 1]
                    if inner.size and (1 - inner.mean()) >= 0.7:
                        errs.append('unlisted outlined rectangle %dx%d at (%d,%d)' % (ww, hh, x, y))
                        return errs
    return errs
