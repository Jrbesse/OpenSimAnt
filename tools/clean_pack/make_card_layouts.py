"""Writes docs/clean_pack/data/card_layouts.json, the measurements of the SimAntipedia that the text builder needs
(docs/clean_pack/texts.md), from the player's own pack (local only; the JSON holds numbers and ids, no text):

    python tools/clean_pack/make_card_layouts.py [remake/build/original_pack.zip]

- "cards": every card's SHARED type 17 layout, record by record in the original's order (the order is the drawing order, which
  data/cards.json does not keep): ["P", bitmap, [top, left, bottom, right], [[top, left, bottom, right, value], ...]] for a
  picture and its hotspots (value 1 = PREVIOUS, > 1 = go to that card, <= 0 = pop up the text -value), ["T", [t, l, b, r],
  [text ids]] for a text frame. Rectangles are card pixels (a card is 200 high, 320 wide). build.py encodes them back byte
  for byte; the card layouts of a clean pack are these, unchanged (they are functional data: 1:1 screens).
- "texts": for each type-10 text its kind (card / definition / popup / prompt) and what the maker needs to know about the
  room: for a card text its rectangle, the width in pixels and the number of lines that fit, how many characters and lines the
  original used, and "needs", the glossary definitions the original card had as bold link words (ids, not words);
  for a definition or flowchart pop-up its length in characters and in lines at the pop-up's 160 px.
- "labels": the card -> the word on the box that opens it in the encyclopedia's pictures (docs/clean_pack/encyclopedia_bitmaps.md,
  the project's own words), which the card's title should agree with.
- "linked_from": for each pop-up text id, the cards whose pictures have a hotspot to it.
"""
import json, os, struct, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B

LABELS = {
    130: 'Ant anatomy', 131: 'Head', 132: 'Thorax', 133: 'Abdomen', 134: 'Social insects', 135: 'Ants', 136: 'Termites',
    137: 'Bees', 138: 'Wasps', 139: 'Castes', 140: 'Worker', 141: 'Soldier', 142: 'Replete', 143: 'Male', 144: 'New queen',
    145: 'Queen', 146: 'Behavior', 147: 'Nest building', 148: 'Communication', 149: 'Scent trails', 150: 'Fighting',
    151: 'Herding aphids', 152: 'Common species', 153: 'Weaver ants', 154: 'Harvester ants', 155: 'Army ants',
    156: 'Leafcutter ants', 157: 'Life cycle', 158: 'Eyes', 159: 'Antennae', 160: 'Mouth', 161: 'Ant life cycle',
    162: 'Colony life cycle', 163: 'Food sharing', 164: 'Brood care', 165: 'Carpenter ants', 166: 'Fire ants',
    167: 'Ant facts', 170: 'Foraging', 171: 'Game strategy', 172: 'Overall goals', 173: 'Gathering food', 174: 'Keyboard shortcuts',
    175: 'Warfare', 176: 'Full game', 177: 'Colony flowchart', 178: 'Experimental game',
}


def main():
    pack = sys.argv[1] if len(sys.argv) > 1 else os.path.join(B.ROOT, 'remake', 'build', 'original_pack.zip')
    z = zipfile.ZipFile(pack)
    adv, lh = B.original_adv(), B.line_height()
    cards = {m['id']: m for m in B.data('cards')}
    texts_meta = {m['id']: m for m in B.data('texts')}
    layouts = {}
    for cid in sorted(cards):
        d = z.read('SHARED/17/%d.bin' % cid)
        recs = B.dec_card_layout(d)
        assert B.enc_card_layout(recs) == d, 'card %d does not round trip' % cid
        layouts[cid] = recs
        # the measurements agree with the layout
        pics = [r for r in recs if r[0] == 'P']
        assert [p[1] for p in pics] == [p['bitmap'] for p in cards[cid]['pictures']], cid
    # the table of link words as the game MEANS it: the file lists [id][word] but the id belongs to the word before it
    g = z.read('EXE/glossary.bin')
    ents = B.dec_glossary(g)
    head = z.read('SHARED/10/901.bin')
    first = head[:head.find(b' -')].decode('latin-1').upper()               # the word of the first entry (its name sits before the table)
    names = [first] + [w for _, w in ents]
    true = {n: i for n, (i, _) in zip(names, ents)}
    assert len(true) == len(ents) and set(true.values()) == set(B.GLOSSARY_IDS), 'the glossary is not the 26 expected ids'

    texts, linked = {}, {}
    for cid, recs in layouts.items():
        for r in recs:
            if r[0] == 'P':
                for h in r[3]:
                    if h[4] <= 0:
                        linked.setdefault(-h[4], set()).add(cid)
    for tid in sorted(texts_meta):
        raw = z.read('SHARED/10/%d.bin' % tid)
        styl = z.read('SHARED/21/%d.bin' % tid) if 'SHARED/21/%d.bin' % tid in z.namelist() else None
        runs = B.dec_styl(styl)[0] if styl else []
        text, runs = B.ant_clean(raw, runs) if tid not in B.PROMPT_IDS else (raw[:raw.find(b'\0')], [])
        spans = B.bold_spans(runs, len(text))
        needs = []
        for a, b in spans:
            i = true.get(text[a:b].lstrip(b' ').decode('latin-1').upper())
            if i and i not in needs:
                needs.append(i)
        e = {'chars': len(text)}
        owner = [(cid, r) for cid, recs in layouts.items() for r in recs if r[0] == 'T' and tid in r[2]]
        if tid in B.PROMPT_IDS:
            e.update(kind='prompt', shown=tid in (128, 130))
        elif owner:
            (cid, r), = owner
            t, l, b, rr = r[1]
            _, _, nl, used, _ = B.ant_layout(text, runs, l, t, rr, b, adv, lh)
            e.update(kind='card', card=cid, rect=r[1], width=rr - l, lines=(b - t) // lh, used=nl, styled=tid not in B.NO_STYLE_RUNS,
                     needs=needs)
        else:
            _, _, nl, _, _ = B.ant_layout(text, runs, 0, 0, B.POPUP_WIDTH, 10000, adv, lh)
            e.update(kind='definition' if tid in B.GLOSSARY_IDS else 'popup', used=nl, linked_from=sorted(linked.get(tid, [])))
        texts[tid] = e
    for tid in B.GLOSSARY_IDS + B.POPUP_IDS + list(B.PROMPT_IDS):
        assert tid in texts, tid

    out = ['{', ' "cards": {']
    out += [' "%d": %s%s' % (cid, json.dumps(recs, separators=(',', ':')), ',' if cid != max(layouts) else '') for cid, recs in sorted(layouts.items())]
    out += [' },', ' "texts": {']
    out += [' "%d": %s%s' % (tid, json.dumps(e, separators=(',', ':')), ',' if tid != max(texts) else '') for tid, e in sorted(texts.items())]
    out += [' },', ' "labels": %s' % json.dumps({str(k): v for k, v in sorted(LABELS.items())}, separators=(',', ':')), '}']
    path = os.path.join(B.DATA, 'card_layouts.json')
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('%d cards, %d texts -> %s' % (len(layouts), len(texts), path))


if __name__ == '__main__':
    main()
