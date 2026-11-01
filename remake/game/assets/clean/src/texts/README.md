# Texts (the SimAntipedia, the glossary, the flowchart pop-ups, the save prompts)

Written new from `docs/clean_pack/texts.md` (spec only) by an isolated agent. The text in the JSON files is the source;
`tools/clean_pack/build.py` encodes it (`SHARED/10`, `19`, `21`, `EXE/glossary.bin`).

| File | Content |
|---|---|
| `prompts.json` | 5 texts: the save prompts 128 (quit) and 130 (load / new game), and the never-shown notes 129, 131, 132 |
| `glossary.json` | 26 definitions with their link words (901, 910..929, 963..967) |
| `popups.json` | the 13 pop-ups of the colony flowchart (950..962) |
| `cards.json` | 53 cards: a title each, and a text for 50 (none for 127, 129, 177) |
| `show_layout.py` | helper: prints how the game's line breaker sets a card text (lines, bold words) with the clean fonts |

## Voice

Plain, friendly, factual natural-history prose for a reader of about twelve and up. The nature cards (groups A to G) describe
real ants and insects only, with round figures where a number is uncertain. The game cards (group H), the flowchart pop-ups
and the prompts speak to the player ("your colony") and say only what the spec lists. No name of the original game, its
publisher or its authors; the project's own name is OpenSimAnt.

## Link words fixed

highlighted, chitin, maxillae, ocelli, infrabuccal, crop, midgut, trophallaxis, caste, larvae, pupate, castes, pupae, eclose,
callows, pheromones, brood, honeydew, aphids, breeders, recruit, forage, foraging, queen's chamber, nurseries, eggs
(terms as in the spec; 917 / 920 and 963 / 964 are worded differently). Card 131 (Head) names ocelli and maxillae in plain text,
since the spec reaches them through the picture boxes.

## How to check

    python tools/clean_pack/build.py                                   # no "error:" or "warning:" line for texts
    python remake/game/assets/clean/src/texts/show_layout.py 161 170   # the lines of a card as the game draws them

A bold word must lie whole on one line with text after it; if the build says the game would draw part of a text twice,
move the bold word away from the end of a line (reword the sentence) and run `show_layout.py` on that card.
