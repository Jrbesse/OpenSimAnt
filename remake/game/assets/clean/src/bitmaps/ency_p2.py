"""ency_p2.py - pass 2: the ant model's pictures 410, 420, 440, 460, 128 and 200 (the labelled whole ant)."""
from ency_lib import Cv, H1, H2, HX, grad, Tone, BAYER
import numpy as np
import ency_ant as A

WORKER = dict(leg=0.85, ant=0.85)
SOLDIER = dict(hs=1.75, ts=1.2, tl=1.05, gh=0.85, gl=0.9, mand='open', teeth=True, muscles=True, leg=0.8, ant=0.7,
               head_tone=Tone(lambda xx, yy, cv: (((xx + yy) % 3 == 0) | (BAYER[yy % 4, xx % 4] < 5))))
ALATE = dict(wings='alate', hs=0.88, ts=1.3, tl=1.25, gl=0.85, gh=0.78, petl=0.075, leg=0.8, ant=0.85, pose='stand')
QUEEN = dict(hs=0.8, tl=0.85, ts=1.15, scars=True, gl=1.9, gh=1.9, seg=6, egg=True, leg=0.8, ant=0.85, pose='stand', petl=0.06)


def leader_to(cv, name, tip, part, mid=3):
    x0, y0, x1, y1 = cv.boxes[name]['rect']
    sx = min(max(tip[0], x0 + 3), x1 - 4)
    start = (sx, y1)
    via = []
    if sx != tip[0]:
        via = [(sx, y1 + mid)]
    cv.leader(name, start, via, tip, part)


def ant410():
    cv = Cv(92, 48, '410')
    cv.cut_rows = [0, 1]
    A.place(cv, WORKER, 0, 2, 92, 48, anchor='c')
    return cv, 'generic worker ant, side view, walking, facing left (no labels)'


def ant420():
    cv = Cv(141, 54, '420')
    A.place(cv, SOLDIER, 0, 0, 141, 54, anchor='c')
    return cv, 'soldier ant (major worker), large head, open toothed mandibles, side view facing left'


def ant440():
    cv = Cv(128, 51, '440')
    cv.cut_rows = [0, 1, 2, 3]
    A.place(cv, ALATE, 0, 4, 128, 51, anchor='c')
    return cv, 'winged reproductive ant, two pairs of wings, side view facing left'


def ant460():
    cv = Cv(155, 56, '460')
    cv.cut_rows = [0, 1]
    A.place(cv, QUEEN, 0, 2, 155, 56, anchor='c')
    return cv, 'mated queen, wingless, wing scars, swollen gaster, an egg, side view facing left'


def ant128():
    cv = Cv(223, 86, '128')
    A.place(cv, ALATE, 2, 2, 221, 84, anchor='c')
    return cv, 'spare (never shown): winged ant, large, same drawing as 440'


def ant200():
    cv = Cv(184, 89, '200')
    cv.box('head', (37, 3, 67, 14), 'Head')
    cv.box('thorax', (74, 3, 118, 14), 'Thorax')
    cv.box('abdomen', (130, 3, 183, 14), 'Abdomen')
    reg = A.place(cv, dict(leg=0.8, ant=0.8), 18, 20, 182, 89, anchor='c')
    for name, key in (('head', 'head'), ('thorax', 'thorax'), ('abdomen', 'gaster')):
        c = {'head': reg['head_c'], 'thorax': reg['thorax_c'], 'abdomen': reg['gaster_c']}[name]
        part = reg[key]
        tip = (c[0] - 1, c[1] - 1)
        if name == 'head':
            tip = (c[0] - 1, c[1] - 2)
        leader_to(cv, name, tip, part)
    cv.extra['ant'] = reg
    return cv, 'whole worker ant with the three body regions labelled Head, Thorax, Abdomen'


def build():
    return {410: ant410(), 420: ant420(), 440: ant440(), 460: ant460(), 128: ant128(), 200: ant200()}
