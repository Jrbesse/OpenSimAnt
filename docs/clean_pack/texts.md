# Spec: the long texts (the SimAntipedia's cards, the glossary and the pop-ups, the save prompts)

> **Status (2026-11-01):** complete, ready for a maker. Written from the remake's code (`Antipedia.cs`, `Main.cs`), the card
> layouts and text measurements (`data/card_layouts.json`, `data/cards.json`, `data/texts.json`) and the encyclopedia's pictures
> ([encyclopedia_bitmaps.md](encyclopedia_bitmaps.md)). Covers **94 texts** (50 card texts, 26 glossary definitions, 13 flowchart
> pop-ups, 5 prompt / note texts), **53 card captions**, the **glossary** (26 link words) and the style runs derived from the
> markup. The card layouts (type 17: geometry, pictures, link targets) are **not** written by the maker: they are measured data
> and always built. The encoders and checks are in `tools/clean_pack/build.py` (`cat_texts`; `--roundtrip=<zip>` decodes and
> re-encodes every original of these kinds); what could not be traced is said where it comes up and in "Not found / open".

Output folder: `remake/game/assets/clean/src/texts/`. Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an entry).
Files to write (all UTF-8 JSON, no scripts needed, the text *is* the source):

| File | What |
|---|---|
| `texts/prompts.json` | 5 texts: the two save prompts (128, 130) and three notes that are never shown (129, 131, 132) |
| `texts/glossary.json` | 26 definitions with their link words (the pop-up that opens when a bold word, or a picture box, is pressed) |
| `texts/popups.json` | 13 pop-ups of the colony flowchart (950..962) |
| `texts/cards.json` | 53 cards: a caption (title) each and, for 50 of them, a text (the prose of the card) |
| `README.md` | the voice you chose, the link words you fixed, how to check |

## Contents

- [Scope](#scope) - [How to work](#how-to-work) - [Source formats](#source-formats) - [Rules for every text](#rules-for-every-text)
- [How the game lays a text out](#how-the-game-lays-a-text-out) (the room, bold words and links) - [Fonts and widths](#fonts-and-widths)
- [A. The prompts](#a-the-save-prompts-and-notes-promptsjson) - [B. The glossary](#b-the-glossary-glossaryjson-26-definitions) - [C. The flowchart pop-ups](#c-the-flowchart-pop-ups-popupsjson-13)
- [D. The cards](#d-the-cards-cardsjson-53) (groups A to I) - [The build's checks](#the-builds-checks) - [Not found / open](#not-found--open)

## Scope

**In:** every text the game shows in the SimAntipedia (the Info window), plus the two save prompts. The Info window shows one
**card** at a time: a title in the window's caption, a block of text in a rectangle, pictures (the 40 bitmaps of
`encyclopedia_bitmaps.md`) and the button strip at the bottom. Pictures hold the clickable boxes (to other cards, or pop-ups);
the text holds **bold words**, which are links to pop-up definitions (the glossary).

| What | Count | Resource | Written by |
|---|---|---|---|
| Card layouts (pictures, text rectangles, links) | 53 | `SHARED/17` | **nobody**: measured data, built unchanged |
| Card captions | 53 | `SHARED/19` | you (`cards.json` "title") |
| Card texts | 50 | `SHARED/10` + style runs `SHARED/21` | you (`cards.json` "text") |
| Glossary definitions (pop-ups of bold words and of picture boxes) | 26 | `SHARED/10` + `SHARED/21` | you (`glossary.json`) |
| Flowchart pop-ups | 13 | `SHARED/10` + `SHARED/21` | you (`popups.json`) |
| Save prompts and notes | 5 | `SHARED/10` | you (`prompts.json`) |
| Glossary table | 1 | `EXE/glossary.bin` | **derived** from the 26 "word" fields |

Cards 127, 129 and 177 have no text (127 and 129 are never reached; 177 is the flowchart, all pop-ups): they have a title only.

**Not in this spec:** the pictures and the words inside them (encyclopedia_bitmaps.md), the button strip (BACK / PREVIOUS / TOP,
ui_bitmaps.md group K), the string lists (strings.md). 18 pictures that cards refer to do not exist in the game's files (see
"Not found / open"): the game draws nothing for them and the texts must not rely on them.

## How to work

Four passes; after each run `python tools/clean_pack/build.py` (it reads only your sources and says in plain words what is
wrong, with the card and the text named; with nothing else made yet it also lists what is still missing, which is expected).

1. **Pass 1:** `prompts.json`, `glossary.json` (the 26 link words and definitions: the other texts use these words in bold),
   `popups.json`.
2. **Pass 2:** `cards.json` cards of groups A to C (front page, body, social insects, castes).
3. **Pass 3:** groups D to F (behaviour, species, life cycles).
4. **Pass 4:** groups G to I (ant facts, game strategy, the two unreachable cards), then the README.

You may leave cards out until a later pass; the build only complains about cards that are present and wrong. The checks on bold
words wait until `glossary.json` holds all 26 valid definitions (they print a warning meanwhile).

## Source formats

All strings are UTF-8 JSON strings, **printable ASCII only** (space to `~`) plus the line break `"\n"`.

```
texts/cards.json      { "130": { "title": "Ant anatomy", "text": "First paragraph ... a *bold link word* ...\n\nSecond paragraph." },
                        "177": { "title": "Colony flowchart" },  ... }
texts/glossary.json   { "910": { "word": "chitin", "term": "Chitin", "text": "the tough material ..." }, ... }
texts/popups.json     { "950": "The explanation shown when the box is pressed ...", ... }
texts/prompts.json    { "128": "Do you want ...?\n\nIf you ...", ... }
```

- **Bold words** in a card text are written between asterisks: `the *crop* stores food`. The build turns them into the bold style
  runs and the link; a bold word must be one of the 26 glossary words (below) and nothing else may be bold. A literal asterisk
  cannot occur in a text. A bold word may contain a space (for a two-word link word); it has no space at either end, is not
  directly followed by another bold word, and **is never the last thing of a text** (put a word or a full stop after it).
- **Line breaks:** a real newline (`"\n"`) ends the line; a blank line between paragraphs is two newlines. A text needs no
  newline at its end. Do not indent with spaces or tabs, do not write two spaces in a row, do not leave a space next to a
  newline. Text that wraps by itself needs no newline.
- `cards.json`: the key is the card number; `"title"` is the window caption (1 to 24 characters, Title Case or sentence case,
  no underscore or asterisk; the game writes a space as `_` itself); `"text"` is the card's prose and is **absent** for cards 127,
  129 and 177.
- `glossary.json`: the key is the definition id (901, 910..929, 963..967, see B). `"word"` is the **link word**: how the word is
  written inside the bold marks in the cards (1 to 31 letters, a space, apostrophe or hyphen inside; case does not matter; each
  word once). `"term"` is the head word of the pop-up (shown in bold at its start, 1 to 39 letters). `"text"` is the definition;
  the build shows the pop-up as **bold term, ` - `, text**, so do not repeat the term or write the dash.
- `popups.json` and `prompts.json`: the key is the text number; the value is the whole text, plain (no asterisks).

## Rules for every text

1. **Your own words, and true.** Write every text freshly from the topic given here, as a natural-history writer would for
   a general reader of about twelve years and up: clear, factual, friendly. The topics name the subject and the facts to
   cover; the sentences, order, examples and comparisons are yours. Do not recall, reproduce or lightly rephrase text from any
   existing encyclopedia, book, website or game. Be accurate about real ants and insects; where you are unsure of a number, give a
   round figure or leave it out ("hundreds of thousands", not "250,000"); never invent a record.
2. **No names of the original game, of its publisher or its authors, no trademarks.** In particular nothing that contains the
   words *SimAnt*, *Maxis* or *SimCity*; no computer brand ("as powerful as a ... computer"), no company, no real person, no web
   address. The project's name **OpenSimAnt** is allowed (the game's own cards may say "the game" instead). The build rejects the
   other names.
3. **Say what the game does.** The game cards (group H), the pop-ups of the flowchart (C), the prompts (A) and a few definitions
   describe the game; they say only what is listed in this spec and do not promise features that do not exist. The nature cards
   (groups A to G) describe real ants only; they do not mention the game (only the front page talks about the Info window).
4. **No reference to a picture's position or look** ("at the left", "the picture below"): several pictures are absent (see "Not
   found"), and the text sits at different sides of the picture on different cards. You may say "the boxes" / "the buttons" where
   this spec says a card has them. Do not mention an animation or sound.
5. **No reference to a printed manual**; say "the Info window" or "the help windows" if you must point at documentation.
6. **Length.** Each text has a rectangle that holds only so many lines; the build lays the text out with the game's own line breaker
   and refuses a text that does not fit. Aim for **70 % to 110 % of the original card's length** (given in the tables as "orig.
   chars"; shorter is a warning) and never more than fits.
7. **Case and punctuation:** normal sentences with full stops. Titles in Title Case or sentence case. Straight quotes `"` and `'`
   only; a hyphen `-` for a dash, `...` for an ellipsis if you must. A percent sign is allowed, but write "per cent" in prose.
8. **Tone:** neutral and educational (the original encyclopedia is plain and slightly playful in places; you may be lightly
   playful in the game cards, never in the nature cards' facts).

## How the game lays a text out

The game's line breaker is ported exactly into `build.py` (`ant_layout`), so you do not have to count pixels: the build reports a
text that does not fit, a word that is too wide, and a bold word that would not become a link. This is how it works, so you can
aim:

- A text goes into a **rectangle** (width w px, height h px). It is set in lines of **10 px**: the first line starts 4 px below the
  top of the rectangle and 1 px right of its left edge, and there are `floor(h / 10)` lines, so a text of more lines is **cut off**
  (the rest is never drawn). The last line must also end above row 180 of the card (the button strip starts there).
- The text is **filled line by line**: characters are added to the line until its width reaches w; the line then ends at the last
  place where a break is allowed: **before a space or an opening bracket `(` `[` `{`, after `!` `)` `,` `-` `.` `?` `]` `}`**. A
  newline ends a line at once. If a line has no such place (one very long word) it overflows: the build refuses it. The text is
  **left aligned** (ragged right).
- Normal text is in **font 2** (average about 5.3 px per letter in English prose, so a line of w px holds about w / 5.3
  characters), bold in **font 5** (wider, about 6.5 px per letter). A card text is the width of its table row ("room"); the
  glossary and flowchart pop-ups are **160 px** wide and at most **10 lines** high (about 250 characters).
- **Bold words and links.** A bold word is a **link** if it lies **whole on one line**, the line still has room when the bold word
  ends and more text follows it, and its letters (leading spaces dropped, upper-cased) are exactly a glossary word. Pressing and
  holding the mouse button on it shows the definition as a pop-up. A bold word that is split by the end of a line, that ends
  the text, or that comes directly after a character other than a space (such as an opening quote or bracket, when the line
  wraps there) is **not** a link (and the game may draw part of the line twice). The build simulates this and tells you which
  word to move or reword. Keep an ordinary space (or the start of a line) before every bold word.
- The pop-up of a glossary entry is "**bold term** - text", 160 px wide, at most 10 lines.

## Fonts and widths

Pen advances in pixels of the printable characters (the sum along a line is its width; space is `sp`):

```
font 2 (normal text): sp3 !4 "4 #6 $6 %9 &7 '3 (4 )4 *5 +6 ,4 -4 .4 /4 06 16 26 36 46 56 66 76 86 96 :4 ;4 <6 =6 >6 ?6 @10 A7 B7 C7 D7 E7 F6 G8 H7 I4 J6 K7 L6 M8 N7 O8 P7 Q8 R7 S7 T6 U7 V7 W9 X7 Y7 Z6 [4 \4 ]4 ^5 _6 `4 a6 b6 c6 d6 e6 f4 g6 h6 i3 j3 k6 l3 m8 n6 o6 p6 q6 r4 s6 t4 u6 v6 w7 x6 y6 z6 {4 |3 }4 ~6
font 5 (bold link words): sp4 !4 "5 #7 $7 %11 &9 '3 (5 )5 *5 +7 ,4 -5 .4 /5 07 17 27 37 47 57 67 77 87 97 :4 ;4 <7 =7 >7 ?6 @10 A8 B7 C8 D9 E6 F6 G9 H9 I4 J4 K8 L6 M10 N9 O10 P7 Q10 R7 S6 T8 U8 V8 W13 X7 Y8 Z7 [4 \6 ]4 ^7 _6 `4 a6 b7 c6 d7 e6 f4 g6 h7 i4 j4 k6 l4 m10 n7 o7 p7 q7 r5 s5 t5 u7 v6 w9 x6 y6 z6 {5 |7 }5 ~7
font 4 (save prompts, 7 px per letter on average): see strings.md
```

## A. The save prompts and notes (`prompts.json`)

Five texts of the type-10 family that are not cards. They are plain text (no bold). A newline ends a line, two a blank line.

| Id | Shown? | Where / what to say |
|---|---|---|
| 128 | yes | The question in the confirmation window that opens when the player chooses to **quit**: ask whether to save the current game first, then (new paragraph) warn that anything done after the previous save is lost unless the player saves. The window's three buttons are lettered elsewhere (Save / Don't Save / Cancel); do not name them. |
| 130 | yes | The same question when the player chooses to **load a saved game or start a new one**: save the current game first? Then the same warning. Make the two texts different in wording. |
| 129 | never | An unused note of an older edition: a request to type the player's name in a box and to press a key to move between fields. Write 1 to 3 short harmless sentences (e.g. a polite request for a name); at most 240 characters. |
| 131 | never | An unused note that begins "This copy is registered to:" - write one short line of that kind (at most 240 characters). |
| 132 | never | An unused very short label for an identification number (a few words). |

128 and 130 are wrapped by the dialog into **258 px** in font 4 (about 36 characters per line) and at most **7 lines** (a blank line counts):
the build checks it. Say "the game" or "OpenSimAnt".

## B. The glossary (`glossary.json`, 26 definitions)

A **definition** is the text that pops up in a white box, 160 px wide, while the mouse button is held on (1) a **bold word** in a card
text, or (2) a **box of a picture** (the encyclopedia pictures' boxes that open pop-ups, named below). The glossary table
`EXE/glossary.bin` is built from your 26 "word" fields (one link word per definition, 26 in all: that is all the table can
hold). The ids are fixed by the pictures: do not renumber.

Write each as `{"word", "term", "text"}`. A **word** you choose should be the plain form that the cards use in bold (suggested
words are given; you may choose another form, e.g. a singular, if you keep each word once). The **text** is a plain 1- to 3-sentence
definition (about 50 to 250 characters, at most 10 lines at 160 px; the original's longest pop-up was 253 characters).
**Reached from** says where the definition must be reachable: a picture box is already a link; for a "bold in" card, that card's text
**must contain the word in bold** (the build checks it).

| Id | Suggested word | Term | The definition is about | Reached from |
|---|---|---|---|---|
| 901 | `highlighted` | Highlighted | the word used for marked (bold) words that can be pressed for a definition | bold in card 128 |
| 910 | `chitin` | Chitin | the tough material of an insect's outer shell | bold in card 130 |
| 911 | `maxillae` | Maxillae | the small paired mouthparts behind the jaws that chew food and clean legs and antennae | picture box on card 131; bold in card 160 |
| 912 | `ocelli` | Ocelli | the three tiny simple eyes on the head that only judge light and dark | picture box on card 131; bold in card 158 |
| 913 | `infrabuccal` | Infrabuccal pocket | the pouch under the mouth opening where food is squeezed and the liquid separated (the picture calls it the mouth pouch; say so) | picture box on card 133; bold in card 160 |
| 914 | `crop` | Crop | the "social stomach": the storage sac in the gaster where food for sharing is kept | picture box on card 133; bold in card 133, 160, 163 |
| 915 | `midgut` | Midgut | the ant's own stomach, where the food it keeps for itself is digested | picture box on card 133 |
| 916 | `trophallaxis` | Trophallaxis | sharing liquid food mouth to mouth among nestmates | bold in card 142, 163 |
| 917 | `caste` | Caste | a caste: a group of ants with its own body form and job | bold in card 134, 136, 143, 145 |
| 918 | `larvae` | Larvae | larvae: the legless, eyeless, eating and growing young | picture box on card 153, 161; bold in card 138, 153, 161, 179 |
| 919 | `pupate` | Pupate | to pupate: the larva turns into a pupa, often by spinning a cocoon (the picture says "Spin") | picture box on card 161; bold in card 161 |
| 920 | `castes` | Castes | castes (plural): give a different text from 917, for example the main castes and what each does in a few words | bold in card 136, 137, 139, 146 |
| 921 | `pupae` | Pupae | pupae: the resting stage in which the young ant changes into an adult, usually inside a cocoon (the picture says "Pupa") | picture box on card 161; bold in card 161 |
| 922 | `eclose` | Eclose | to eclose: the adult comes out of the pupal case or cocoon (the picture says "Emerge") | picture box on card 161; bold in card 161 |
| 923 | `callows` | Callows | callows: young adults that are soft and pale and darken and harden within days | bold in card 161 |
| 924 | `pheromones` | Pheromones | pheromones: chemical messages that ants of one species use (the picture says "Pheromone") | picture box on card 149; bold in card 148, 149, 150 |
| 925 | `brood` | Brood | brood: the young of the colony, eggs, larvae and pupae | bold in card 140, 144, 155, 162, 164 |
| 926 | `honeydew` | Honeydew | honeydew: the sugary liquid aphids give off | picture box on card 151; bold in card 151 |
| 927 | `aphids` | Aphids | aphids: small sap-sucking insects | picture box on card 151; bold in card 151 |
| 928 | `breeders` | Breeders | breeders: the game's word for the winged males and new queens that fly off to mate and found colonies | bold in card 172 |
| 929 | `recruit` | Recruit | to recruit: to get nestmates to help with a job by chemical signals and touch | bold in card 170, 173 |
| 963 | `forage` | Forage | to forage: to look for and collect food | bold in card 162, 163 |
| 964 | `foraging` | Foraging | foraging (the same idea as 963, the form used as a noun); a different wording from 963 is fine | bold in card 141, 170, 173 |
| 965 | `queen's chamber` | Queen's chamber | the room of the nest where the queen lives, lays eggs and is fed and cleaned by workers | picture box on card 147 |
| 966 | `nurseries` | Nurseries | the rooms where eggs, larvae and pupae are kept and where nurse workers feed and move them | picture box on card 147 |
| 967 | `eggs` | Egg | the egg: the first stage of life, small, hatching after some weeks; fertilised eggs become females, unfertilised ones males | picture box on card 161 |

Notes: (a) 917 `caste` and 920 `castes` and 963 `forage` and 964 `foraging` are inflections of one idea: each needs its own text, written
differently (the game has no way to share one). (b) The picture boxes' words (encyclopedia_bitmaps.md) are **Ocelli, Maxillae, Mouth
pouch, Crop, Midgut, Larvae / Larva, Pupa, Spin, Emerge, Egg, Pheromone, Honeydew, Aphids, Queen's chamber, Nurseries**: the definition
text must agree with the box that opens it (e.g. 919 explains what a larva does when it spins its cocoon, 922 the adult coming out). (c)
901 is the word the front page uses for its marked words; its definition says what a marked word is and how to use it (press and hold).
(d) 928 is a game word: it names the winged males and new queens of the game; say so.

## C. The flowchart pop-ups (`popups.json`, 13)

Card 177 (Colony flowchart) shows a diagram of **13 boxes** (the picture's own words are in encyclopedia_bitmaps.md, group H); pressing and
holding a box shows one of these. Plain text (no bold), 160 px wide, at most 10 lines (about 250 characters; the original's longest was
253). Write to the player ("your colony"), explain the box, give the cause and effect in the diagram and one hint where it fits.

| Id | Box | Facts to cover (state only these; round numbers are the game's real rules) |
|---|---|---|
| 950 | Foraging ants | what fraction of the workers go out foraging; the player adjusts it through the Behavior Control window; increase it as colony health begins to drop |
| 951 | Digging ants | what fraction of the workers dig; adjusted through the Behavior Control window, and bigger nests are safer to defend and hold more food |
| 952 | Nursing ants | what fraction of the workers tend the brood; adjusted through the Behavior Control window; the least dangerous job, as it never takes an ant outside the nest |
| 953 | Food collected | food drives colony growth; each item you gather is one the red colony is denied; beating the reds at foraging gives you a lasting edge in numbers |
| 954 | Food stored | while colony health is good, fresh food goes into storage rather than being consumed; a larger nest has more room for it; once health drops, the nurses begin eating from the reserves |
| 955 | Food eaten | collected food ends up consumed or stockpiled, depending on health; each ant needs a certain amount to live (soldiers and queens more), so a bigger population needs more |
| 956 | Nest size | nest size affects food storage, how well the nest can be defended and, a little, egg laying |
| 957 | Colony health | the colony's nourishment level; it rises when more food comes in than is needed and falls when food runs short; low health lowers egg laying and increases starvation |
| 958 | Egg production | how fast the queen lays eggs, hence how fast the colony grows; it falls sharply when health is below half or when fewer than a fifth of the ants are nursing |
| 959 | Colony population | the number of ants; it rises as eggs hatch and grow and falls when ants die or fly off to mate; aim to outgrow the red colony |
| 960 | Starvation | deaths from hunger; hunger comes from low colony health, which comes from too little food |
| 961 | Predation | ants lost to spiders and ant lions; tips: lure the spider to the red colony; wall in an ant lion near your colony with pebbles, or build a snare for the red ants by combining pebbles with an ant lion |
| 962 | Fights | deaths in fights, mostly against the red ants but also against the human; if you lose most fights (see the Status window), raise soldier production in the Caste Control window |

The Behavior Control window, Caste Control window and Status window are named exactly so (strings.md "Words the lists share").

## D. The cards (`cards.json`, 53)

The tables give for each card: its **id**; the **title** (the caption of the Info window; **it should be the word on the box that opens
the card** in the encyclopedia pictures, a mismatch is a warning); the **room** (width in px x number of lines of 10 px that the text
rectangle holds); the **orig. chars** (length of the original card in characters: aim for 70 to 110 %); **links** (the glossary words
that must appear in bold in the text: the build checks them by definition id); and the **topic** (what the text must cover: in your
own words; the order and the details beyond the list are yours).


### Group A: The front page and the body

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 128 | Top Card | 144 px x 17 lines | 368 | `highlighted` | Welcome page. Say what the Info system is (a small reference about ants and about playing), what the topic boxes do, how to step back (the Previous button) and how to return to this page (the Top button), and that the marked words can be pressed and held to see their meaning. The link word is whatever word you use for "marked". |
| 130 | Ant anatomy | 319 px x 8 lines | 427 | `chitin` | The body in outline: the three body regions (named in the picture; each box opens its own card), the hard outer shell that works as a skeleton (link word chitin), breathing through small air tubes instead of lungs, and hearing: ants have no ears, but vibration detectors in the head, thorax and legs pick up shaking of the ground. |
| 131 | Head | 145 px x 16 lines | 359 | - | What the head carries: antennae, brain, eyes, mouthparts. The brain is tiny yet an ant can learn and remember for a long time (give one example, such as a trail remembered through a winter). Do not compare it to a computer or any brand. The picture's boxes open the Eyes, Antennae and Mouth cards and two pop-ups (Ocelli, Maxillae). |
| 132 | Thorax | 319 px x 8 lines | 350 | - | The middle body section, to which all six legs are attached; the foot, ending in a pair of curved claws that give grip for climbing walls and walking upside down; the leg's cleaning comb, a notch lined with bristles through which an antenna or leg is drawn to be cleaned. |
| 133 | Abdomen | 318 px x 7 lines | 367 | `crop` | The rear section: the narrow waist (petiole) and the gaster behind it; what the gaster holds (the crop for stored food, the intestine, glands that make scent signals and other chemical messages); some ants have a sting at the tip. The picture's boxes are pop-ups (Mouth pouch, Crop, Midgut). |
| 158 | Eyes | 297 px x 11 lines | 526 | `ocelli` | The compound eye, made of many facets, which even underground species have; ants see movement better than still objects, which is why a foraging ant stops and looks about between short walks; the three simple eyes (ocelli) on top of some ants' heads only tell light from dark. |
| 159 | Antennae | 294 px x 12 lines | 521 | - | The main sense organs: touch, smell and vibration; elbowed, in two parts (the long first part, the scape, and the segmented funiculus that carries the sense organs); in constant motion; the two antennae compare the strength of a smell to find its direction, and an ant that loses one loses that skill. |
| 160 | Mouth | 304 px x 11 lines | 553 | `maxillae`, `infrabuccal`, `crop` | The mandibles (jaws that close sideways: for fighting, digging, carrying), the smaller maxillae behind them (chewing, and cleaning legs and antennae); chewed food is kept in a pouch beneath the mouth opening, where muscles squeeze the juice out of it; the ant swallows the juice (which is then held in the crop) and discards the dry residue. |

### Group B: Social insects

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 134 | Social insects | 176 px x 17 lines | 446 | `caste` | Why living and working in groups pays; the four big groups of social insects (ants, termites, bees, wasps); what marks a society: staying together, specialised castes, individuals who give up their own interests for the group; some spiders show a milder form of group life. |
| 135 | Ants | 312 px x 12 lines | 622 | - | Ants as the most widespread and most numerous social insects; more species than the rest of the social insects combined; the range of places they live; descent from wasp-like ancestors; the oldest fossil ants, in amber about a hundred million years old, which still show some wasp features. |
| 136 | Termites | 318 px x 14 lines | 750 | `castes`, `caste` | Small soft-bodied social insects that look like ants but are another group; castes with both sexes; most eat wood with the help of microbes in the gut; because they stay inside the nest almost all are blind; probably descended from cockroach-like ancestors; the "nasute" soldiers that squirt a sticky fluid from a snout on the head. |
| 137 | Bees | 315 px x 10 lines | 495 | `castes` | The variety of bees; they gather nectar and pollen; hairy, usually winged, usually stinging; only a minority (honeybees, bumblebees) are social, with three castes (drones, workers, queens) and hives of wax. A "Next" button below the text leads to the second bee card. |
| 179 | Bees 2 | 316 px x 9 lines | 442 | `larvae` | Foraging bees: pollen carried on the hairs of the hind legs to the hive, where it feeds the larvae; the waggle dance, which tells nestmates where food is; why bees matter for crop pollination. |
| 138 | Wasps | 179 px x 15 lines | 417 | `larvae` | Most wasps live alone; the group shows every step from solitary to fully social life, which helps scientists study how social life evolved; social wasps build paper nests; adults drink nectar and feed their larvae on chewed-up insects. |

### Group C: Castes

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 139 | Castes | 166 px x 17 lines | 451 | `castes` | An ant society contains different body forms with different jobs (castes), all needed for the colony to survive; the queen produces just two sorts of egg, one giving females and one giving males; every female egg is identical at the start, and how the larva is fed and tended settles its final form: worker, soldier, or future queen. The picture's menu opens the six caste cards. |
| 140 | Worker | 289 px x 10 lines | 424 | `brood` | Most ants are workers: sterile females; their jobs (digging, tending brood, finding food, feeding the queen and others, fighting); how long they live (about a year, several years in a few species); some keep one job for life, others change. |
| 141 | Soldier | 321 px x 12 lines | 640 | `foraging` | Sterile females larger than the workers, with oversized heads and powerful mandibles; some, with flat plug-shaped heads, seal the nest entrance with them and step aside only when a returning forager gives the correct signal; the big head is mostly muscle for the jaws, not a bigger brain; also called major workers (the small ones minor workers). |
| 142 | Replete | 209 px x 16 lines | 556 | `trophallaxis` | In some species, above all in dry climates, certain workers swell their crops with liquid food until they cannot walk and hang in the nest as living larders; when food is scarce, nestmates are fed by them. |
| 143 | Male | 259 px x 6 lines | 266 | `caste` | Males live the shortest of all (some only weeks), do no work, and exist to mate; most have wings for the mating flight. |
| 144 | New queen | 322 px x 13 lines | 710 | `brood` | Winged fertile females that leave on the mating flight; after mating a queen may return to her nest, join another or found a colony; she must avoid being eaten, find shelter, rub off her wings, dig a tiny chamber and seal herself in, living on her body reserves (even the wing muscles) until her first workers grow up and bring food. |
| 145 | Queen | 320 px x 12 lines | 675 | `caste` | After the founding stage the queen's main task is egg laying; a colony has one queen or many (even thousands); queens live longest of all ants (over twenty years); she keeps the sperm she received for years in a special organ; fertilised eggs become females and, only at certain times, she lays unfertilised eggs that become males. |

### Group D: Behaviour

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 146 | Behavior | 179 px x 14 lines | 403 | `castes` | Why ant behaviour fascinates scientists and children; simple behaviour of single ants adds up to complex behaviour of the colony; nobody gives orders; castes specialise, yet any ant can pass a message to any other ant. The picture's menu opens eight behaviour cards. |
| 147 | Nest building | 319 px x 7 lines | 347 | - | Ants live in very different places and so build different homes: tunnels in the ground (a few deeper than a tall person), mounds above ground, under stones, in trees and plants, in walls, in house foundations. The picture is a cut-open nest; its boxes open the Queen and Brood cards or are pop-ups (Queen's chamber, Nurseries). |
| 148 | Communication | 173 px x 17 lines | 430 | `pheromones` | A colony needs its members to pass information; ant signals are simpler than human speech but enough: touches, strokes, taps, sounds made by rubbing body parts (stridulation), grasping, nudging, tasting, and above all chemical signals. The picture's "Antennae" box opens the Antennae card. |
| 149 | Scent trails | 309 px x 9 lines | 458 | `pheromones` | A forager that finds food walks home slowly, dragging the tip of its gaster to mark a trail; other ants follow it, and each ant that returns with food adds scent, so the trail grows stronger and draws more ants. The picture's box is a pop-up (Pheromone). |
| 163 | Food sharing | 319 px x 12 lines | 633 | `trophallaxis`, `forage`, `crop` | Trophallaxis: ants pass liquid food from mouth to mouth. A forager fills its crop; only what the ant itself needs goes on to be digested, the rest belongs to the colony's common supply and is passed on when two ants meet and touch antennae. Do not mention any animated picture. |
| 164 | Brood care | 316 px x 8 lines | 376 | `brood` | A worker carries each egg to a nursery chamber; eggs need steady warmth and humidity, so nurse workers move them between chambers all day to keep them near the right temperature (about 25 degrees Celsius), and lick them clean. The strip has two small "see also" hotspots (to the life cycle and nest cards). |
| 150 | Fighting | 202 px x 17 lines | 550 | `pheromones` | Workers as well as soldiers fight to the death for their colony; weapons: poisons and other secretions sprayed, squirted or rubbed onto enemies; some species even use scent signals to confuse the enemy. The strip has a "see also" hotspot to the Warfare card. |
| 151 | Herding aphids | 317 px x 7 lines | 330 | `aphids`, `honeydew` | Aphids drink plant sap and squirt out the surplus as honeydew; some ants stroke ("milk") aphids to collect it and, in return, protect them from other insects. The picture's boxes are pop-ups (Honeydew, Aphids). |
| 170 | Foraging | 303 px x 10 lines | 502 | `foraging`, `recruit` | The usual foraging pattern: scouts (often older workers) search; food small enough is carried home alone; a bigger find makes the scout lay a chemical trail to the nest and call others; food too big for one ant is cut up and carried by several. |

### Group E: Species

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 152 | Common species | 166 px x 14 lines | 353 | - | Introduction to the species cards: thousands of kinds of ant are known (a round figure) and many are not yet found, so the cards show a sample of common and interesting ones. The picture's menu opens six species cards. |
| 153 | Weaver ants | 180 px x 17 lines | 493 | `larvae` | Weaver ants of Africa, southern Asia and Australia: many workers form living chains that draw leaves towards each other; other workers grip nearly grown larvae in their jaws and use the sticky silk the larvae spin as glue to join the leaves into a nest in the trees. The picture's "Larvae" box is a pop-up. |
| 154 | Harvester ants | 294 px x 8 lines | 406 | - | Seed-eating ants of dry regions that also take insects and fruit; deep, elaborate nests (some deeper than two metres) with chambers for storing seeds. |
| 155 | Army ants | 311 px x 10 lines | 470 | `brood` | Nomadic hunting ants (the legionary ants of tropical America and the African driver ants); two phases: a nomadic one (each day the whole colony relocates, hauling its brood and hunting en route) and a stationary one (a camp, the bivouac, where the wingless queen lays her eggs). |
| 156 | Leafcutter ants | 173 px x 16 lines | 433 | - | Ants that farm: workers cut leaves and flowers and carry them to the nest; smaller workers cut and chew them to pulp that feeds a fungus the ants grow underground; the fungus is their only food. |
| 165 | Carpenter ants | 305 px x 6 lines | 269 | - | The best-known wood-nesting ants: they nest in rotten logs, trees and sometimes wooden buildings and chew tunnels through soft rotten wood but, unlike termites, do not eat it. |
| 166 | Fire ants | 286 px x 9 lines | 400 | - | Native to South America; small reddish ants in colonies of hundreds of thousands; a painful sting while they hold on with their jaws; accidentally brought to the southern United States in the early twentieth century and spreading a few miles a year (round figures). |

### Group F: Life cycles

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 157 | Life cycle | 320 px x 12 lines | 563 | - | The colony seen like any living thing: birth, growth, maturity, reproduction; a view in terms of energy (food): the colony grows and stores energy, and once mature spends some on reproduction (new queens and males); that point comes at very different sizes, from a few dozen to hundreds of thousands of ants. The picture's two boxes open the ant and colony life cycles. |
| 161 | Ant life cycle | 320 px x 9 lines | 446 | `larvae`, `pupate`, `pupae`, `eclose`, `callows` | The stages of one ant: young and adult look completely different; a queen lays tens to hundreds of eggs a day; a worker carries each egg to a nursery; after about two weeks the egg hatches into a larva; after one to three weeks of growth the larva pupates; after a further two or three weeks the pupa breaks out of its cocoon as a callow, a young adult. The picture's boxes are pop-ups (Egg, Larva, Pupa, Spin, Emerge). |
| 162 | Colony life cycle | 316 px x 12 lines | 588 | `brood`, `forage` | Three stages: founding (after mating, the lone queen picks a site, produces her first eggs and raises the first workers herself), growth (workers go out to forage, widen the tunnels and chambers, look after the brood in the queen's place, so the queen can concentrate on laying), reproduction (the colony rears a batch of young queens and males who depart to found colonies; the cycle begins again). |

### Group G: Ant facts

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 167 | Ant facts 1 | 299 px x 11 lines | 530 | - | A page of opening facts: the total weight of all ants compared with that of all people (a widely cited comparison: say it is about as much or more); they inhabit almost every land area apart from the icy poles and mountain summits; no other insect group, and no animal, has more individuals; roughly half a million ants make up a pound. Start with a short heading line. A "Next" button below leads to page 2. |
| 168 | Ant facts 2 | 308 px x 12 lines | 543 | - | Two facts, each with a short heading line: ants are among the oldest living creatures and have hardly changed in tens of millions of years (compare, for instance, sharks); ants are very strong for their size: they carry 10 to 20 times their own weight and cooperate to move heavy loads. A "Next" button leads to page 3. |
| 169 | Ant facts 3 | 320 px x 16 lines | 687 | - | Two facts, each with a short heading line: ants are everywhere (a round estimate of how many live on Earth; the largest known colony, a huge connected "supercolony" on the Japanese island of Hokkaido; how common they are in tropical forests) and ants are the longest-lived insects (workers about a year, some species four to five years, queens over twenty). A button leads back to the Top card. Give round, widely cited figures only. |

### Group H: Game strategy

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 171 | Game strategy | 163 px x 14 lines | 347 | - | Introduction to the strategy cards: the player is the mind of the colony and hops into and out of single ants, treating them as disposable instruments; ants die in large numbers, sometimes even the one the player currently occupies, yet losing a single ant barely affects the colony. The picture's menu opens seven cards. |
| 172 | Overall goals | 299 px x 16 lines | 607 | `breeders` | The three games. Quick Game: the player's black colony competes with the red colony for food and land; the aim is to beat the reds by killing their queen; spiders, ant lions, heavy rain, human feet and lawn mowers make it harder. Full Game: the final goal is to take the house (and clear the yard of red ants) by planting fresh colonies throughout the lawn, which needs breeders (males and new queens) and mating (see the Full game card). Experimental Game: the player is a human experimenting with ants. |
| 173 | Gathering food | 307 px x 11 lines | 579 | `foraging`, `recruit` | Food is what new ants are built from: the amount of food sets colony health, and health sets the birth rate. Tips: send the yellow ant running to a fresh find, recruit helpers on the spot and let them go (they lift the food and haul it back); or carry an item to the nest yourself, leaving a scent that pulls your ants towards the source; whatever you remove is lost to the red side. |
| 174 | Keyboard shortcuts | 264 px x 13 lines | 524 | - | One line per shortcut ("key - what it does"), at most 12 lines, no bold words: Tab toggles whether the Map window or the Edit window is active; Backspace stops the yellow ant if it is walking, otherwise re-centres the view on it; Alt + click can replace a double-click; 1 recruits 5 ants, 2 recruits 10, 3 releases half, 4 releases all; X exchanges (jump into another ant); Alt + 2 recruits every ant of the black colony; 0 switches alarm-scent mode on or off; right-click in the Map window opens the yellow ant's commands; Ctrl + arrow keys scroll the Edit window. |
| 175 | Warfare | 222 px x 17 lines | 636 | - | Tactics versus the red colony and the predators: attack only with more ants and better colony health than the enemy; fight in a soldier's body, since soldiers come out ahead more often; lure the spider towards the enemy's nest; raise the yellow ant's low-health alert threshold (it halts to feed more often, but that makes it a stronger fighter); guard the yellow ant during an advance, because its death costs time while it is reborn, frees every ant it had recruited and ends the attack. |
| 176 | Full game | 304 px x 11 lines | 569 | - | The goal: conquer the entire property, house and lawn, and expel the human residents; victory comes from wiping out every red ant and controlling roughly 70 per cent of the house's patches. Strategy: choose sites for new colonies carefully, since you need a route to the house yet must also contain the reds; patches you are not currently playing keep running in the background; a red colony hemmed in by black ones on several sides falls more easily to a freshly founded colony. |
| 177 | Colony flowchart | - | - | - | No text: the flowchart is a picture of 13 boxes, each a pop-up (see the flowchart pop-ups). Title only. |
| 178 | Experimental game | 228 px x 16 lines | 553 | - | A sandbox: tools and toys to set the ants loose on (mazes, chemicals, even insecticide); food never appears by itself, the player controls all food; nothing counts as a win or a loss; holding Alt with a tool removes things (the food tool puts food down; with Alt held it picks food up again). |

### Group I: Cards no one reaches

| Card | Title | Room | Orig. chars | Must link | Topic |
|---|---|---|---|---|---|
| 127 | Top Card | - | - | - | An older copy of the front page that nothing links to and that shows only the buttons. Title only (use the same title as the Top card). |
| 129 | Index | - | - | - | An index page that nothing links to and that shows only the buttons. Title only. |

Use the titles in the tables: they are the words on the boxes of the pictures. A different title is only a warning, but the box still
says the other word. "Ant facts 1/2/3" and "Bees 2" are page titles.

## The build's checks

`python tools/clean_pack/build.py` (reads `src/texts/*.json`, the clean fonts' `font2.json` / `font5.json` / `font4.json` and
`data/card_layouts.json`) refuses, with the file, card or id named: a key that is not a card / definition / pop-up / prompt id;
an entry of the wrong shape (the fields of cards.json, glossary.json); a card with a text where it has none (127, 129, 177) or
without one where it has; characters outside printable ASCII and newline, a backslash, two spaces in a row, a space or
newline at the ends of a text or next to a newline; unpaired asterisks, an empty or touching pair, a bold word with a space at
an end, a bold word at the very end of a text, bold in a place where none is allowed (the prompts, the pop-ups, the keyboard card);
a bold word that is not one of the glossary's words; a glossary word that is not 1 to 31 letters, one used twice; a missing
required link word (by definition id) in a card; a card text that does not fit its rectangle (lines, width of a word, the
button strip), a bold word that would not become a link in the game (it wraps, or follows a character other than a space when the
line breaks there), or that makes the game draw a part of a line twice; a pop-up of more than 10 lines at 160 px; a save prompt of
more than 7 lines at 258 px; an unused note of more than 240 characters; a title longer than 24 characters or with an underscore or
asterisk; the original game's, the publisher's or the franchise's name anywhere. Warnings (not errors): a card text under half
the original's length, a title that differs from the box label, bold words not checked because the glossary is not complete.
It encodes the texts to `SHARED/10/<id>.bin` (text in Mac Roman = ASCII here, a newline as CR, one NUL at the end) and
`SHARED/21/<id>.bin` (the style runs: one run from the start, a new run wherever bold starts or ends), the captions to
`SHARED/19/<card>.bin` (a space written as `_`), the card layouts to `SHARED/17/<card>.bin` and the glossary to
`EXE/glossary.bin`. `python tools/clean_pack/build.py --roundtrip=<pack.zip>` decodes every text, caption, layout and the
glossary of a pack, writes them in this markup and encodes them back: the game sees the same text and bold words for all 94 texts,
the same bytes for 79 (the others carry editor debris in the original, a second NUL, or underline runs the game does not
draw differently), the same lines and links on the card for 47 of the 50 card texts (the other 3 have underline runs), and
53 layouts, 53 captions and the 26-entry glossary are byte-identical.

## Not found / open

- **Engine side, not the pack: the original files' glossary is read one entry off.** The original table is word-then-id but
  `EmbeddedAssets.glossary` and `Antipedia.cs` read it as id-then-word, so with the player's files each link word shows the definition
  of the word before it (and the first word has no entry). The clean pack avoids it: its `glossary.bin` pairs each word with its own id
  in the layout the engine reads today (26 entries and the end = 886 bytes). The maker needs to know nothing of it; if the reader is
  fixed, `enc_glossary(entries, name_first=True)` in `build.py` writes the other layout.
- **The glossary holds at most 26 entries** (`EmbeddedAssets` insists on 886 bytes), so the 26 definition ids are all the link words
  there can be; a new word needs the engine's size check relaxed.
- **Unused texts:** 129, 131, 132 are never read (a registration dialog of an older edition); cards 127 and 129 are never reached
  (nothing links to them). They are written so the pack is complete.
- **18 pictures the cards refer to do not exist** (151, 211, 212, 430, 570, 860, 875, 877 and ten small "see also" buttons 161..169,
  171; encyclopedia_bitmaps.md): the game draws nothing, the card shows an empty space and a clickable blank. The original's card 163
  text speaks of an animation that existed only on another system; the clean text does not.
- **Original quirks the clean texts do not copy:** the originals carry editor debris (a NUL and two bytes) inside four texts which the
  game strips; bold tab characters and underlined headings (the game draws underline as plain text); two pairs of
  identical definitions (917 / 920, 963 / 964); a bold word after an opening quote that wraps (the game then draws the quote twice and makes no
  link). The clean texts have none of these (the build rejects the debris, tabs and the wrapping quote).
- **Keyboard shortcuts (card 174):** the list in group H is the original's; the spec side re-checks it against the remake's key
  handling before the pack ships (Ctrl + arrows and the Map window's right-click are the ones to verify).
- **Label sync:** the box words in the pictures are the encyclopedia maker's; when they change, the titles and the definitions' topics
  are re-checked (`labels` in `data/card_layouts.json` holds the expected titles).

