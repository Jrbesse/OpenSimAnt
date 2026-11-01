"""Helper for the texts maker: print how the game lays out card texts (lines, bold words) with the clean fonts.

    python remake/game/assets/clean/src/texts/show_layout.py 161 [more card ids]

It uses the build's own line breaker (tools/clean_pack/build.py). Lines that the game would draw twice show up as repeated text.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'clean_pack'))
import build  # noqa: E402


def main(ids):
    cards = json.load(open(os.path.join(HERE, 'cards.json'), encoding='utf-8'))
    lay = build.data('card_layouts')
    adv, lh = build.clean_adv(), build.line_height()
    for cid in ids:
        e = cards[cid]
        tids = [t for rec in lay['cards'][cid] if rec[0] == 'T' for t in rec[2]]
        info = lay['texts'][str(tids[0])]
        plain, spans = build.parse_markup(e['text'])
        raw = build.enc_text(plain)
        styl = build.dec_styl(build.enc_styl(plain, spans))[0]
        text, runs = build.ant_clean(raw, styl)
        t, l, b, r = info['rect']
        draws, links, nlines, used, too_long = build.ant_layout(text, runs, l, t, r, b, adv, lh)
        print('card %s %s: %d chars, %d lines of %d, used %d/%d' % (cid, e['title'], len(plain), nlines, (b - t) // lh, used, len(text)))
        for x, y, font, seg in draws:
            print('  y=%3d x=%3d f%d %s' % (y, x, font, seg.decode('latin-1')))


if __name__ == '__main__':
    main(sys.argv[1:])
