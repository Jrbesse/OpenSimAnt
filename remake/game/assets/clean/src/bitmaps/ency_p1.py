"""ency_p1.py - pass 1: the menus (150, 400, 500, 600, 700, 850), the buttons (170, 160), the spares (129, 21000..21003)."""
from ency_lib import Cv, text_w

MENUS = {
    150: ((102, 116), "the front page's eight topics", [
        ((10, 3, 94, 14), "Social insects"), ((14, 17, 91, 28), "Ant anatomy"), ((22, 31, 81, 42), "Life cycle"),
        ((28, 45, 75, 56), "Castes"), ((7, 59, 97, 70), "Behavior"), ((5, 73, 99, 83), "Common species"),
        ((22, 87, 82, 98), "Ant facts"), ((3, 104, 101, 115), "Game strategy")]),
    400: ((76, 90), "the six castes", [
        ((12, 3, 65, 14), "Worker"), ((11, 18, 66, 29), "Soldier"), ((11, 33, 65, 44), "Replete"),
        ((16, 48, 59, 59), "Male"), ((3, 63, 75, 74), "New queen"), ((13, 78, 61, 89), "Queen")]),
    500: ((109, 120), "behaviour topics", [
        ((11, 3, 100, 14), "Communication"), ((27, 18, 80, 29), "Foraging"), ((16, 33, 93, 44), "Scent trails"),
        ((16, 48, 92, 59), "Food sharing"), ((3, 63, 108, 74), "Nest building"), ((19, 78, 88, 89), "Brood care"),
        ((25, 93, 80, 104), "Fighting"), ((11, 108, 95, 119), "Herding aphids")]),
    600: ((93, 90), "six common ant groups", [
        ((3, 3, 92, 14), "Carpenter ants"), ((3, 18, 92, 29), "Harvester ants"), ((3, 33, 92, 44), "Leafcutter ants"),
        ((9, 48, 85, 59), "Weaver ants"), ((15, 63, 78, 74), "Army ants"), ((18, 78, 74, 89), "Fire ants")]),
    700: ((101, 30), "the two life cycles", [
        ((12, 3, 92, 14), "Ant life cycle"), ((3, 18, 100, 29), "Colony life cycle")]),
    850: ((128, 113), "tips for playing", [
        ((15, 2, 115, 15), "Overall goals"), ((19, 25, 110, 39), "Gathering food"), ((33, 41, 92, 54), "Warfare"),
        ((8, 56, 121, 69), "Full game"), ((6, 71, 123, 84), "Experimental game"), ((5, 87, 124, 100), "Keyboard shortcuts"),
        ((2, 102, 126, 115), "Colony flowchart")]),
}


def menu(ident):
    (w, h), desc, items = MENUS[ident]
    cv = Cv(w, h, '%d' % ident)
    for i, (r, word) in enumerate(items):
        cv.box('m%d' % i, r, word)
    return cv, 'menu of boxed labels: ' + desc


def button(ident):
    """170: 39 x 15, box (1,1)-(38,14); 160: 37 x 15, box (1,1)-(36,14).  Solid black, the word knocked out in white."""
    w = 39 if ident == 170 else 37
    word = 'Next' if ident == 170 else 'Back'
    cv = Cv(w, 15, '%d' % ident)
    x1 = w - 1
    cv.rect(1, 1, x1, 14, 1, 1)
    # round the four corners a little (the box edges stay black along > 95 % of their length)
    for (x, y) in ((1, 1), (x1 - 1, 1), (1, 13), (x1 - 1, 13)):
        cv.put(x, y, 0)
    tw = text_w(word, 'b7')
    tx = 1 + (x1 - 1 - tw) // 2
    cv.text(tx, 4, word, 'b7', 0)
    cv.extra['button'] = dict(rect=(1, 1, x1, 14), word=(tx, tx + tw))
    return cv, ('"next card" button, solid black with the word %s knocked out in white' % word) if ident == 170 else \
        'spare twin of 170: solid black button, the word Back knocked out in white'


def strip129():
    cv = Cv(73, 8, '129')
    return cv, 'spare one-line text strip, entirely white'


ICONS = {
    21000: ("up-pointing arrow", ["...#...", "..###..", ".#####.", "#######", "..###..", "..###..", "..###.."]),
    21001: ("down-pointing arrow", ["..###..", "..###..", "..###..", "#######", ".#####.", "..###..", "...#..."]),
    21002: ("right-pointing arrow", ["...#...", "...##..", "######.", "#######", "######.", "...##..", "...#..."]),
    21003: ("bullet, a filled 5 x 5 diamond", [".......", "...#...", "..###..", ".#####.", "..###..", "...#...", "......."]),
}


def icon(ident):
    desc, rows = ICONS[ident]
    cv = Cv(7, 7, '%d' % ident)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == '#':
                cv.put(x, y, 1)
    return cv, 'spare 7 x 7 icon: ' + desc


def build():
    out = {}
    for i in MENUS:
        out[i] = menu(i)
    out[170] = button(170)
    out[160] = button(160)
    out[129] = strip129()
    for i in ICONS:
        out[i] = icon(i)
    return out
