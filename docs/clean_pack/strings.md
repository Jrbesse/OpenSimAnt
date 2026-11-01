# Spec: the string lists and the menus

> **Status (2026-10-31):** complete, ready for a maker. Written from the remake's code (`Main.cs`, `OpenSimAnt.Data`,
> `OpenSimAnt.Sim`), the notes on the game's own code and the measurements in `data/strings.json` / `data/menus.json`.
> Covers **113 string lists** (573 lines of text: 224 + 95 + 91 + 163 by file) and the **pull-down menus**. The encoder and its checks are in
> `tools/clean_pack/build.py` (`cat_strings`, `cat_menus`; `--roundtrip=<zip>` decoded and re-encoded all 119 original
> lists and the menus byte for byte). What could not be traced is said where it comes up ("not found").

Output folder: `remake/game/assets/clean/src/`. Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an entry).
Files to write (all UTF-8 JSON, no scripts needed, the text *is* the source):

| File | What |
|---|---|
| `strings/system.json` | 12 lists: window captions, game modes, status lines, advisor lines, history labels, ant names, credits, score window words, rating titles |
| `strings/balloons.json` | 7 lists: what the ants, the person and the spider say in speech balloons |
| `strings/messages.json` | 37 lists: the message boxes (queen deaths, wins and losses, ways the player's ant dies, yard events, cheats) |
| `strings/tutorial.json` | 57 lists: the tutorial's 57 message boxes |
| `menus/menus.json` | the menu bar's 5 titles and 5 pull-down menus |
| `README.md` | the voice you chose (see "Voice"), a short glossary of the game words you fixed, how to check |

## Contents

- [Scope](#scope) - [How to work](#how-to-work) - [Source format](#source-format) - [Rules for every line](#rules-for-every-line)
- [Fonts and widths](#fonts-and-widths) - [Voice](#voice) - [Words the lists share](#words-the-lists-share)
- Lists: [A system.json](#a-systemjson-12-lists), [B balloons.json](#b-balloonsjson-7-lists),
  [C messages.json](#c-messagesjson-37-lists), [D tutorial.json](#d-tutorialjson-57-lists), [E the menus](#e-the-menus-menusmenusjson)
- [The build's checks](#the-builds-checks) - [Not found / open](#not-found--open)

## Scope

**In:** every string list (a Macintosh-style `STR#` resource: an ordered list of short lines) that the game reads, 113 of
the 119 measured, plus the menu resource. A list is addressed by its number; the game asks for entry *k* of list *n*
(for example "entry 22 of list 1010"), so **the number of entries and their order are fixed by the game**; only the
wording is yours.

**Out, never read (6 lists), do not write them:** 1030, 1300, 1310, 1350, 2000, 2100. They are leftovers of an older
or another edition of the game: 1030 is a 160-line text version of the tutorial (the tutorial the game runs is list
group D), 1300 / 1310 / 1350 are scene and death texts for scenes that are pictures only here, 2000 is a list of
operating-system file-error names, 2100 a list of three font names. No code in the remake asks for them and a search of
the original program for loads of those numbers found none. `build.py` refuses them and does not expect them.

**Other text that is NOT in this spec** (other categories, other specs):

- The long prose: the encyclopedia's 53 cards and their style runs, the glossary, and the two save prompts (texts 128
  and 130), also the other short texts 129, 131, 132, 865: **the "texts" category** (`data/texts.json`, `data/cards.json`).
- Words that are part of a picture: button labels, help overlays, tutorial picture captions: **the bitmap specs**
  (`ui_bitmaps.md`, `yard_bitmaps.md`, `screens_bitmaps.md`).
- Words stored inside the window layouts (a few captions and button words such as the file dialog's, in
  `HCEGANT/0`): the layouts category.
- The one-line version alert: `version/version.txt` (no spec needed).
- The words the program itself contains (for example the Pause / Unpause relabel of the Speed menu's first item, the
  file dialog's wording): engine-side, see "Not found / open".

## How to work

Write the four string files and the menu file in four passes; after each pass run `python tools/clean_pack/build.py`
(it reads only your sources and says in plain words what is wrong; with nothing else made yet it also lists what is
still missing, which is expected). It tells you the width in pixels of any line that is too wide, so you do not have
to count pixels yourself; the table under "Fonts and widths" lets you aim.

1. **Pass 1:** `menus/menus.json` and `strings/system.json` (set the vocabulary first; the other lists reuse it).
2. **Pass 2:** `strings/balloons.json`.
3. **Pass 3:** `strings/messages.json`.
4. **Pass 4:** `strings/tutorial.json` (it names controls, windows and menu entries: use the words you fixed in pass 1 and
   the labels given in "Words the lists share").

You may leave a list out until a later pass; the build only complains about lists that are present and wrong.

## Source format

Each `strings/*.json` is one JSON object: the key is the list's number as a decimal string, the value is the list of its
lines, in order:

```
{ "1000": ["first line of list 1000", "second line", "..."],
  "1001": ["..."] }
```

- Every list must have **exactly the number of entries** the tables below give (except the credits, list 1700). Entry
  *k* is the *k*-th line, counting from 0. A list belongs in the file named in its heading and nowhere else.
- A **line break inside one entry** (only in the speech balloons, group B) is a real newline: in JSON `"\n"`, for example
  `"first part\nsecond part"`. The build turns it into the two characters the game splits at. Nowhere else may an entry
  contain a newline: elsewhere one entry is one printed line, and the *number of entries* is the number of lines.
- Characters: printable ASCII only (space to `~`), the apostrophe is the plain `'`. No backslash and no percent sign
  (they are control characters for the game). No tab, no accents, no typographic quotes or dashes.
- No leading or trailing spaces, except the three entries of list 1800 that are joined to other text and say so.
- No empty entry, except the credits' spacer lines (1700) and the never-read entries 0..12 of list 1800 (which must
  be empty).
- `menus/menus.json` is described in group E.

Numbers, names and other values are **never** inserted by the game into these lists (no `%d`, no `%s`): where the game
puts a value next to a line it draws that value itself. The only code in any entry is the line break above, so there
are no format codes to keep. Where the game *joins* lines (the status window's "overall ... score" line, the Edit
window caption) it is said in the list.

## Rules for every line

1. **Your own words.** Write every line freshly, from the meaning given here. Do not recall, reproduce or lightly
   rephrase text from any existing game, book or website. The jokes are yours too: the original is jokey, you may be
   jokey, but invent your own.
2. **No names of the original game, of its publisher or its authors, no trademarks.** In particular nothing that contains
   the words *SimAnt*, *Maxis* or *SimCity*. The project's own name, **OpenSimAnt**, is allowed (and is the only
   product name allowed). Where a line must name the game, say "the game" or "OpenSimAnt". The build rejects the
   other names. No real person's name, phone number, address or web address anywhere. Nothing about "the manual": say
   "the help windows" or "the Info window" when you must point at documentation.
3. **Say what the game does, in the game's present state.** Do not describe features that do not exist. The tutorial
   (group D) names real controls: see "Words the lists share".
4. **Widths are hard limits.** A line wider than its box is cut off or overwrites its neighbour. Each list below gives its
   font and the room in pixels (the build checks it with exact letter widths).
5. **Same function, similar length.** Keep a line about as long as the original was where the measure is given
   ("measured widest line") and never wider than the limit; a line much shorter than its box is fine.
6. **Case.** Window captions, game modes, button-like words, ant names, states and castes, history labels, credits
   headings, rating titles: Title Case, no final full stop. Status lines, messages, balloon lines: a normal
   sentence, capital at the start, a final full stop, question mark or exclamation mark where it reads naturally.
   Names of controls in the tutorial: exactly as lettered on the screen (see below).
7. **Nothing hostile.** The game is silly and a little gruesome (ants get eaten), but keep it good-humoured: no
   slurs, no real-world politics, no swearing, no real brands.

## Fonts and widths

The game letters these lines in its bitmap fonts; widths differ by font. **Font 0** is a fixed-width text-cell font:
**8 pixels per character**. The others are proportional; the advance (pixels) of every printable character is below
(space is `sp`; a line's width is the sum of its characters' advances). Rule of thumb for ordinary English prose:
font 2 about 5 px per character, font 3 about 4, font 4 about 7.

```
font 2: sp3 !4 "4 #6 $6 %9 &7 '3 (4 )4 *5 +6 ,4 -4 .4 /4 06 16 26 36 46 56 66 76 86 96 :4 ;4 <6 =6 >6 ?6 @10 A7 B7 C7 D7 E7 F6 G8 H7 I4 J6 K7 L6 M8 N7 O8 P7 Q8 R7 S7 T6 U7 V7 W9 X7 Y7 Z6 [4 \4 ]4 ^5 _6 `4 a6 b6 c6 d6 e6 f4 g6 h6 i3 j3 k6 l3 m8 n6 o6 p6 q6 r4 s6 t4 u6 v6 w7 x6 y6 z6 {4 |3 }4 ~6
font 3: sp2 !3 "4 #5 $5 %7 &7 '2 (3 )3 *5 +5 ,3 -3 .3 /3 05 15 25 35 45 55 65 75 85 95 :3 ;3 <5 =5 >5 ?4 @8 A6 B6 C6 D6 E5 F5 G6 H6 I3 J4 K6 L5 M8 N6 O6 P5 Q6 R6 S5 T5 U6 V6 W8 X6 Y6 Z5 [3 \3 ]3 ^4 _5 `3 a4 b5 c4 d4 e4 f3 g5 h5 i3 j3 k5 l3 m7 n5 o5 p5 q4 r3 s4 t3 u4 v5 w6 x5 y5 z4 {4 |2 }4 ~5
font 4: sp4 !6 "7 #10 $7 %11 &10 '3 (5 )5 *7 +7 ,4 -7 .4 /7 08 18 28 38 48 58 68 78 88 98 :4 ;4 <6 =8 >6 ?8 @11 A8 B8 C8 D8 E7 F7 G8 H8 I6 J7 K9 L7 M12 N9 O8 P8 Q8 R8 S7 T6 U8 V8 W12 X8 Y8 Z8 [5 \7 ]5 ^8 _8 `6 a8 b8 c7 d8 e8 f6 g8 h8 i4 j6 k8 l4 m12 n8 o8 p8 q8 r6 s7 t6 u8 v8 w12 x8 y8 z8 {5 |5 }5 ~8
```

Which font and how much room each list has is in its entry below; summary:

| Lists | Font | Room for one line |
|---|---|---|
| 1000 captions | 0 | 40 characters |
| 1001 modes | 4 (and 0 in a caption) | 100 px and 14 characters |
| 1010 [0..22] status lines | 2 | 340 px (entry 14: 290 px) |
| 1010 [23..25] picture captions | 0 | 24 characters |
| 1020 advisor lines | 2 | 340 px |
| 1050 history labels | 3 | 38 px |
| 1100..1103 ant names | 2 | 75 px |
| 1200..1260 balloon lines | 2 | 220 px per line, at most 2 lines |
| 1700 credits | 4 | 254 px |
| 1800 score window words | 4 (0 for [15]) | per entry, see group A |
| 1900 rating titles | 4 | 218 px |
| 10000..10059 message boxes | 4 | 300 px |
| 11000..11112 tutorial boxes | 4 | 460 px |

## Words the lists share

Fixed by the other clean-pack specs, so that the whole game talks with one voice. Use exactly these words when a line
names the thing (the tutorial especially). They are functional labels, not text to be copied from anywhere.

- Windows: **Edit** (the close-up window where you play the yellow ant), **Map** (the overview window), **Behavior
  Control**, **Caste Control**, **History**, **Status** (the efficiency score window), **Info** (the encyclopedia).
- Menus: the menu bar is **File, Window, View, Options, Speed** (group E); the *Window* menu lists *Edit, Map, Behavior,
  Caste, History, Info, Status*.
- The yellow ant's pop-up menu (press and hold on the ant): **Recruit 5, Recruit 10, Release 1/2, Release All, Exchange,
  Help**. The spider's: *Chase, Hunt, Exchange, Help*.
- Map window buttons: a **Yard** button, a **House** button and a **Patch** button; two small triangle icons, one
  lettered **B** (opens Behavior Control) and one lettered **C** (opens Caste Control); a green **?** help button; two bar
  graphs lettered **P** (population) and **H** (health) for the red and black colonies.
- Edit window: a yellow-ant icon at the left of the tool strip that re-centres the view on your ant.
- Keys: **Ctrl** (the Control key), **0** (the zero key: toggles dropping the alarm scent), Tab (Map / Edit), Esc.
- The game modes: **Tutorial, Quick Game, Full Game, Experimental** (the same words as the Select-a-Game buttons).
- The About box shows a name card with `OpenSimAnt` / `an open-source remake` / `a fan project`; the credits (list
  1700) roll next to it.
- Creatures and things: the player's ant is the **yellow ant**; the player's colony is the **black** colony, the enemy
  the **red** colony; the **spider**, the **ant lion** (a sand-pit predator), the **person**, the **mower**,
  **food**, **pebbles**, **alarm scent**.

## A. `system.json` (12 lists)

### 1000 (SHARED), 13 entries: window captions

The title bar of the **Map window** (entries 0 to 8: what it currently shows) and of the **yard window** (entries 9 to
12: its four display modes). Lettered in font 0 (8 px per character), centred in a caption bar 513 px wide, so at most
**40 characters**. Title Case, no final full stop. Measured widest: 28 characters.

| # | The caption of |
|---|---|
| 0 | the Map window showing the whole outdoor patch from above (the backyard overview) |
| 1 | the Map window showing the surface of the colony's patch |
| 2 | the Map window showing the black colony's nest underground |
| 3 | the Map window showing the red colony's nest underground |
| 4 | the black colony's nest-marker scent map |
| 5 | the black colony's trail-marker scent map |
| 6 | the red colony's nest-marker scent map |
| 7 | the red colony's trail-marker scent map |
| 8 | the alarm scent map |
| 9 | the yard window in its plain picture mode (the lawn, the fence, the house) |
| 10 | the same window showing the inside of the house |
| 11 | the strategic mode (a chart of colony strengths over the yard's squares) |
| 12 | the graphic mode (small pictures for each square) |

Entries 1 to 3 and 9 to 12 should contain the same word as the matching *View* menu item (Surface, Black Nest, Red
Nest; Yard, House, Strategic, Graphic) followed by a generic word like "View". Entries 4 to 8 use the word the scent
menu's labels use (see `ui_bitmaps.md`, the scent palette).

### 1001 (SHARED), 4 entries: game mode names

Entry 0 the tutorial, 1 the quick (single patch) game, 2 the full game, 3 the experimental (sandbox) game. Use the
Select-a-Game words: *Tutorial, Quick Game, Full Game, Experimental*. Shown in: the Edit window's caption (font 0),
the Game Over window's mode line (font 4), and the middle of the Status window's score line (font 4). So at most
**14 characters and 100 px in font 4**. Measured widest: 90 px.

### 1010 (SHARED), 26 entries: short status lines and prompts

Mostly shown on the **status strip** at the top of the Edit window's map (font 2, centred over a 352-px wide map: at
most **340 px**, about 65 characters), some also on the yard window. One line, no line break. Written to the player,
second person ("You ..."), plain and short. Measured widest: 254 px.

| # | When the game shows it |
|---|---|
| 0 | label for the pause command (never read; keep it short) |
| 1 | label for the unpause command (never read; keep it short) |
| 2 | stays up for as long as the game is paused |
| 3 | stays up while paused in Exchange mode: click another ant to swap bodies with it |
| 4 | the yellow ant has just crossed into enemy territory, the red nest |
| 5 | a mating flight was refused: there are no males or new queens yet to breed |
| 6 | the mating flight has started |
| 7 | placing a queen was refused: none left to drop (Full Game) |
| 8 | stays up while placing: click a square of the yard to put the new queen there |
| 9 | a new colony was founded on that square |
| 10 | the click was outside the allowed area of the yard |
| 11 | the player was fed by a nestmate and feels better |
| 12 | the player gave food to a nestmate; the ant's thanks |
| 13 | the player ate brood and recovered health by it |
| 14 | prompt on the Status window: click to continue. **At most 290 px** (its strip is 295 px) |
| 15 | mating was tried outside a Full Game: refused, it only works in a Full Game |
| 16 | placing a queen was tried outside a Full Game: refused, it only works in a Full Game |
| 17 | stays up in Chase mode (spider): pick the target by clicking an ant; unpausing aborts |
| 18 | a second "click to continue" prompt (never read; keep it short) |
| 19 | on the yard map: that square has no black colony |
| 20 | on the yard map after the colony was lost: asks for a pick among the black colonies so play can resume |
| 21 | the fill tool was refused: it is not available on the surface |
| 22 | the dig tool was refused: not enough room for a hole there |
| 23 | caption of the scene picture when the yellow ant is dead |
| 24 | caption of the scene picture when the player is reborn in another ant |
| 25 | caption of the scene picture when the player is now an ordinary worker |

Entries **23 to 25** are lettered in font 0 (8 px per character) in a strip 200 px wide above the scene picture: at most
**24 characters**, Title Case or sentence case, a short exclamation or statement.

### 1020 (SHARED), 6 entries: the advisor's lines

The colony advisor puts one on the status strip (font 2, **at most 340 px**, measured widest 182) when the situation
calls for it; second person, an instruction or warning.

| # | Situation |
|---|---|
| 0 | the yellow ant's health is critical: it must eat now |
| 1 | the yellow ant's health is low: go and find food |
| 2 | the colony is short of food |
| 3 | there is no nest yet: dig one |
| 4 | the nest is too small for the colony: dig it out more |
| 5 | the red ants have launched an attack |

### 1050 (SHARED), 10 entries: History window graph labels

Short labels drawn in a small frame at the end of each plotted line of the History window's graph, in the small font
3, so at most **38 px** (about 9 characters). Title Case or abbreviations; they should match the captions on the
History window's ten buttons (`ui_bitmaps.md` group G). Measured widest: 31 px.

| # | Series |
|---|---|
| 0 | black colony's population |
| 1 | black colony's stored food |
| 2 | black colony's health |
| 3 | food lying on the surface |
| 4 | ants that died of old age or hunger |
| 5 | red colony's population |
| 6 | red colony's stored food |
| 7 | red colony's health |
| 8 | ants eaten by enemies (the spider, ant lions) |
| 9 | ants killed in fights |

### 1100, 1101, 1102, 1103 (SHARED), the Ant Info window

Clicking an ant with the Ant Info tool opens a small window of three lines (font 2, each **at most 75 px**, about 14
characters; Title Case, no final full stop): what the ant is, what it is doing, what it carries.

**1100, 8 entries: brood stage.** Shown as the first line for brood (an egg or young). Entries in order of growth: a
malformed egg, a freshly laid egg, an egg, the first, second and third larval stages, the pupa, a pupa about to
hatch. (Measured widest 78 px; yours must be 75 or less.)

**1101, 17 entries: what the ant is** (the first line for an adult), indexed by caste number: 0 a nurse that tends
brood; 1, 2, 3 and 5 workers (3 is a worker carrying food; you may use one word for all or tell them apart); 4 a male;
6, 7 and 9 soldiers (7 carrying food); 8 a young queen; 10 a "replete", an ant swollen with stored food; 11 unused;
12 and 13 the queen; 14 a fighter (a fight marker); 15 and 16 unused. For the unused entries (11, 15, 16) write a single
`?`.

**1102, 30 entries: what the ant is doing** (second line), indexed by the ant's state number. 0 idle; 1 tending the
nest; 2 foraging; 3 carrying found food home; 4 digging inwards; 5 digging outwards; 6 on defence duty; 7 attacking;
8 hatching (brood); 9 laying eggs (the queen); 10 fighting; 11 alarmed; 12 defending the nest; 13 resting; 14 getting
ready for a mating flight; 15 taking off; 16 flying; 17 and 18 unused; 19 an avenger (an ant seeking revenge for a
dead nestmate); 20 to 29 unused. For each unused entry (17, 18, 20..29) write `???`.

**1103, 17 entries: what the ant carries** (third line), indexed by caste number: entry 1 an egg; 3 and 7 food; 5
and 9 dirt; **every other entry (0, 2, 4, 6, 8, 10..16) the same word meaning "nothing"**. Use the same wording for
the repeated meanings.

### 1700 (SHARED), the credits (variable length)

The About box shows the name card, then rolls these lines upwards one pixel at a time, **centred, in font 4, at most
254 px per line**; a blank entry (`""`) is a blank line (spacing between groups). Write **10 to 80 entries**.
**This list carries the project's own identity; use exactly this structure:**

- First group, in this order: `OpenSimAnt`, `an open-source remake`, `a fan project`, then a blank line.
- A heading line and then one or two lines for each of: what the project is inspired by (say it accurately and without
  a name: "inspired by a classic 1991 ant colony simulation game"); the code ("OpenSimAnt contributors" is the
  credit; no individual names); the engine ("Built with the Godot engine"); the newly made pictures, text, sounds
  and music ("made for this project by AI assistants from written specifications", one short line); thanks
  to everyone who played and tested; a closing line to the ants. Your wording; keep it short and warm.
- Do not credit the original game's authors, testers, companies or product names, and do not name individuals at all.

### 1800 (SHARED), 19 entries: words of the Status window and the Edit caption

Only entries **13 to 18** are read. **Entries 0 to 12 must be empty strings** (`""`): they belonged to file dialogs of
another edition and are never read, and writing nothing keeps them free of anything but the project's own words.

| # | Use | Limits |
|---|---|---|
| 13 | start of the Status window's score line (a word like "overall"): this text, then the game mode's name (list 1001), then entry 14 are **joined without any added space** and lettered as one line | font 4, **60 px, must end with a space** |
| 14 | the end of that line (the word for the score) | font 4, **60 px, must start with a space** |
| 15 | the joiner between the product name and the game mode in the **Edit window caption** ("OpenSimAnt", this entry, the mode), like a dash with a space each side | font 0, **at most 5 characters** (so a space, a dash, a space) |
| 16 | shown in each of the four small boxes of the score column when it does not apply: a short "n/a" | font 4, **38 px** |
| 17 | first line of the Experimental game's score area: "no score" | font 4, **280 px** |
| 18 | second line, completing it: "in the Experimental game" (it is in the line below 17) | font 4, **280 px** |

### 1900 (SHARED), 10 entries: rating titles

The Game Over window shows one as the player's rating, in a 218-px well in font 4 (**at most 218 px**). Title Case,
funny but not insulting. Entries **0 to 4** are for a game that was **won** and **5 to 9** for one that was **lost**; within
each five, the number is the score band of the game, lowest band first. Write the won titles with rising honour with
the index (0 the plainest, 4 the grandest, as in army ranks or ant castes) and the lost ones as rising consolation (5 the
most pitiful, 9 the least). Measured widest: 184 px.

## B. `balloons.json` (7 lists)

The speech balloons that appear beside an ant (Options > Silly on). The balloon is built around the text from small
pieces, in font 2. Each entry is one remark of **one or two lines** (a real newline in JSON between them), each line
**at most 220 px** (about 40 characters in font 2); entries with one line are fine. A balloon takes the lines of
its list in turn, wrapping round at the end, so the order is free but the **count is fixed**. Remarks are in the
first person, in character. No format codes. Measured widest line: 217 px.

| List | Count | Who talks and when |
|---|---|---|
| 1200 | 23 | **the person** in the yard (the one who mows the lawn and walks in and out of the house); the entry is picked by what the person is doing: 0 it starts to rain; 1 about to mow, the lawn needs it; 2 feeling hungry, going in; 3 to 5 pushing the mower (enjoying the work, a worry, wishing for a better mower); 6 giving up and leaving the yard; 7 to 14 idle chatter on the lawn: a remark about ants, calling a pet by a name, a musing about another animal, about the neighbourhood, about homework, about pacing, about the time; 15 to 17 in the kitchen: about shopping and food and being hungry; 18 and 19 outdoors: enjoying the day; 20 dirty hands; 21 and 22 television: about to watch it, then disliking it |
| 1210 | 25 | **the spider**. Five remarks for each of its five states, in this order: 0..4 resting (smug, relaxed); 5..9 walking (idle, hungry, searching for ants); 10..14 hunting (taunting the ant it is chasing); 15..19 eating (enjoying the meal); 20..24 fleeing (frightened, wanting out of the colony) |
| 1220 | 8 | **black ants** fighting a red ant: battle taunts |
| 1230 | 8 | **red ants** fighting a black ant: battle taunts (rivals of 1220; use your own insults, none about real groups) |
| 1240 | 15 | **brood** in the nest (eggs and young): idle thoughts of a baby ant: where am I, it is dark, wanting food, wondering what it will become (a soldier, a queen, a male), being turned over, boredom |
| 1250 | 8 | **the queen**: she complains, in a motherly way, about laying eggs all day and never leaving the nest |
| 1260 | 8 | **resting workers**: lazy remarks and jokes about being tired, their mandibles, food, grooming |

Do not write the same line twice in one list. Keep each remark one idea.

## C. `messages.json` (37 lists)

The message boxes: a framed box in the middle of the screen with a few centred lines (font 4), waiting for a click.
**One entry is one printed line**, so the entry count is the number of lines and must stay as listed. Each line
**at most 300 px** (about 40 characters); the box is as wide as its widest line, so give the lines of one box roughly the
same length. No format codes; no numbers are inserted. Write to the player ("you"), the queen or the colony ("the black
queen"); speak plainly, with a touch of humour where the event is silly. The "measured widest" column is the original's
widest line in px, to show the scale.

| List | Lines | Measured widest | When shown, what to say |
|---|---|---|---|
| 10000 | 2 | 172 | a request to relocate to a new yard square is turned down because relocating belongs to the Full Game only |
| 10002 | 3 | 228 | a relocation is turned down: the colony is too small to survive such a trip; advise growing it first |
| 10004 | 2 | 190 | a relocation is turned down: the chosen yard square holds no black colony |
| 10006 | 2 | 182 | the player's ant is being sent to the chosen spot, outdoors in the yard |
| 10007 | 2 | 182 | the player's ant is being sent to the chosen spot, indoors in the house |
| 10010 | 1 | 254 | announces the death of this patch's black queen |
| 10011 | 2 | 223 | the game ends in defeat: the red colony prevailed; encourage another attempt |
| 10012 | 1 | 241 | announces the death of this patch's red queen |
| 10013 | 2 | 243 | the game ends in victory: the red colony has been destroyed |
| 10015 | 2 | 249 | the black queen has died of hunger |
| 10016 | 2 | 236 | the red queen has died of hunger |
| 10020 | 3 | 229 | a secret code has dropped a heap of cash on the player, which ants cannot use (a gag) |
| 10022 | 2 | 206 | gag part one: a nonsense riddle posed as a question (the music plays between the two parts) |
| 10024 | 1 | 223 | gag part two: the nonsense answer to that riddle |
| 10026 | 3 | 214 | the yellow ant dies: swamped and consumed by a horde of ants |
| 10028 | 3 | 250 | the yellow ant dies: frightened of ants, it loses its mind and kills itself; it will return as an ant again |
| 10030 | 3 | 246 | the yellow ant dies: a hostile ant bites its head off (one of two versions the game picks between, with 10032) |
| 10032 | 3 | 223 | the yellow ant dies: a hostile ant wins a brawl and tears its limbs off (the other version) |
| 10034 | 3 | 211 | the yellow ant dies: squashed under the person's shoe |
| 10036 | 3 | 241 | the yellow ant dies: drawn into the mower's blades |
| 10038 | 3 | 232 | the yellow ant dies: swept away and drowned in the muddy water |
| 10040 | 3 | 217 | the yellow ant dies: starvation drives it frantic until its body gives out |
| 10042 | 3 | 231 | the yellow ant dies: sprayed with a bug killer, its nerves fail |
| 10044 | 3 | 231 | the yellow ant dies: falls into a sand-pit trap and is devoured by its occupant (the game shows a picture instead; keep it ready) |
| 10045 | 1 | 188 | the yellow ant dies: an electric shock |
| 10046 | 3 | 170 | the spider was slain by the ants: a note of triumph |
| 10047 | 3 | 192 | the yellow ant dies: the spider drains its body (one of two versions, with 10048) |
| 10048 | 3 | 193 | the yellow ant dies: the spider's poison burns through it (the other version) |
| 10050 | 3 | 205 | the ants swarm and kill an ant lion, then dismember and eat it |
| 10052 | 3 | 175 | triumph: not a single red ant is left anywhere in the yard |
| 10053 | 2 | 293 | hint, after the humans have been driven away but red ants survive: finish them off to win the Full Game |
| 10054 | 2 | 226 | triumph: the humans have given up the house and left |
| 10055 | 2 | 220 | hint, when the humans are gone but the house is not yet captured: conquer it to win the Full Game |
| 10056 | 4 | 228 | the Full Game is lost: no black queen, breeder or egg remains anywhere, so the line cannot continue |
| 10057 | 3 | 229 | the Full Game is won: the red ants are crushed and the house is occupied |
| 10058 | 3 | 249 | this colony has no ants left; the player must choose another black colony in the yard or house |
| 10059 | 2 | 215 | the player's consciousness has been moved to an ant that was already alive |

The death messages (10026 to 10048) are shown when the yellow ant dies; the player then takes over another ant. Mention
the cause of death and, in one of the lines, that the player carries on (as another ant). 10053 is the widest in the
original; keep yours under 300 px.

## D. `tutorial.json` (57 lists)

The tutorial has 57 boxes; step *n* is list `11000 + 2 (n - 1)` (11000, 11002, ... 11112). The box appears when the
step begins and the tutorial moves on when the player has done what it asks (the game watches for it: the condition
is given so the text asks for exactly that). Format as group C (centred lines of font 4, **at most 460 px**, about 65
characters, each entry one printed line, count fixed). Boxes marked **picture** are drawn with a small picture above
the text (the buttons and icons in `ui_bitmaps.md` group J): refer to it ("this icon", "like this") but do not
describe it in detail. Address the player as "you". Name controls exactly as in "Words the lists share" (for
example *Recruit 10*, *Exchange*, *Map*, *Edit*, the *Window* menu, the *0* key). Keep the steps short and encouraging.
The "measured widest" column is the original's widest line in px.

| Step | List | Lines | Measured widest | What the box says / what the player must do next |
|---|---|---|---|---|
| 1 | 11000 | 3 | 282 | greets the player; the tutorial will teach the game one task at a time |
| 2 | 11002 | 3 | 261 | **picture.** presents the yellow ant as the player's avatar and starts the lesson on steering it |
| 3 | 11004 | 3 | 206 | asks the player to excavate the soil beside the ant by double-clicking it (done when the nest has grown a little) |
| 4 | 11006 | 3 | 215 | praises the first digging and asks for more of it as practice (done when the nest has grown further) |
| 5 | 11008 | 3 | 280 | **picture.** asks the player to tunnel upwards through the sky-coloured strip at the nest's top, out into the open air (done on reaching the surface view) |
| 6 | 11010 | 3 | 203 | states that the ant is now above ground, names this view, and warns that danger lurks here |
| 7 | 11012 | 3 | 260 | asks the player to click open ground so that the ant walks to it (done after a walk) |
| 8 | 11014 | 2 | 233 | asks the player to click the ant itself so that the window centres on it again (done when the view re-centres) |
| 9 | 11016 | 5 | 378 | teaches a second way to scroll: push the pointer against the border of the window in the wanted direction; keyboard-only players hold Ctrl and press the arrow keys (done when the view has moved, or after a while) |
| 10 | 11018 | 3 | 220 | proposes a food hunt and asks the player to open the Map window from the Window menu (done when the Map window is frontmost) |
| 11 | 11020 | 3 | 345 | explains the Map window: it shows the whole patch; green markers are food, the yellow marker is the player, other markers may drift about |
| 12 | 11022 | 3 | 344 | asks the player to remember the food's position, then reopen the Edit window from the Window menu (done when it is frontmost) |
| 13 | 11024 | 2 | 251 | **picture.** asks the player to go to the food and stand on one piece (done when standing on food) |
| 14 | 11026 | 3 | 210 | **picture.** the game has made the ant hungry; asks the player to double-click a piece of food to eat it (done when health has recovered) |
| 15 | 11028 | 2 | 189 | a brief reaction: the meal worked and the ant feels refreshed |
| 16 | 11030 | 3 | 272 | asks the player to bring food home: double-click a second piece to lift it (done when carrying food) |
| 17 | 11032 | 4 | 347 | **picture.** explains why the piece was lifted and not eaten: the ant eats only when its health sits below the threshold mark on the health graph at the left |
| 18 | 11034 | 3 | 233 | **picture.** asks the player to re-enter the nest, which lies to the left (done in the black nest) |
| 19 | 11036 | 2 | 244 | asks the player to double-click inside the tunnel to put the food down (done when dropped) |
| 20 | 11038 | 2 | 231 | asks the player to climb back to the surface for further exercises (done on the surface) |
| 21 | 11040 | 3 | 239 | **picture.** asks the player to find a small pebble like the pictured one and double-click to lift it (done when carrying a pebble) |
| 22 | 11042 | 2 | 239 | asks the player to double-click a spot to walk there and release the pebble (done when dropped) |
| 23 | 11044 | 3 | 218 | remarks that loose pebbles can be piled into walls and obstacles that shield the colony (ten black ants are added now) |
| 24 | 11046 | 3 | 207 | asks the player to press and hold on the ant and pick Recruit 10 from the menu that opens (done when followers exist) |
| 25 | 11048 | 3 | 200 | confirms that a few black ants are now tagging along |
| 26 | 11050 | 2 | 259 | asks the player to roam and watch the followers keep up (done after a walk) |
| 27 | 11052 | 3 | 159 | asks the player to press the 0 key and then pace back and forth over a stretch of ground (done when walked with the alarm scent on) |
| 28 | 11054 | 4 | 339 | explains that this trail of scent makes the colony's ants guard that area; press 0 again to stop it |
| 29 | 11056 | 3 | 225 | announces the next lesson: Exchange, which puts the player into another ant |
| 30 | 11058 | 3 | 288 | asks the player to press and hold on the ant, pick Exchange, then click a black ant close by (done after the swap) |
| 31 | 11060 | 3 | 267 | confirms the swap: the chosen ant is now the player's, and any black ant can be taken over this way |
| 32 | 11062 | 3 | 172 | asks the player to return to the Map window via the Window menu (done when it is frontmost) |
| 33 | 11064 | 3 | 343 | **picture.** moves the lesson to the wider world: asks the player to press the Yard button at the lower left of the Map window (done in the yard view) |
| 34 | 11066 | 3 | 200 | points out that the blinking square on the yard's right-hand side marks the current colony |
| 35 | 11068 | 3 | 234 | explains that the yard view is where, in the Full Game, new colonies are bred and spread |
| 36 | 11070 | 2 | 209 | **picture.** asks the player to press the House button at the lower left (done in the house view) |
| 37 | 11072 | 3 | 303 | explains that a Full Game is also won by seizing the interior of the house, in addition to beating the red ants |
| 38 | 11074 | 3 | 251 | **picture.** asks the player to press the Patch button and so go back to the colony's surface (done in the patch view) |
| 39 | 11076 | 3 | 265 | **picture.** asks the player to press the little triangle icon lettered B at the lower middle of the Map window (done when Behavior Control is frontmost) |
| 40 | 11078 | 3 | 217 | **picture.** introduces the Behavior Control window as the place to decide what the black ants do |
| 41 | 11080 | 3 | 456 | **picture.** asks the player to drag the small dot inside the triangle, which sets how the ants split between three jobs (done when the dot has moved) |
| 42 | 11082 | 3 | 233 | asks the player to go back to the Map window, by clicking it or via the Window menu (done when it is frontmost) |
| 43 | 11084 | 3 | 268 | **picture.** asks the player to press and hold the "?" icon below and let go after reading the pop-up |
| 44 | 11086 | 4 | 319 | **picture.** explains that such icons are help buttons found in most windows, each opening a pop-up that labels that window's controls |
| 45 | 11088 | 3 | 286 | **picture.** points to the two bar graphs at the lower right, which compare the colonies' headcount (P) and health (H) |
| 46 | 11090 | 3 | 224 | **picture.** asks the player to press and hold inside the bar graph area for a detailed population breakdown |
| 47 | 11092 | 3 | 206 | **picture.** asks the player to open caste control by pressing the triangle icon lettered C below (done when Caste Control is frontmost) |
| 48 | 11094 | 3 | 279 | **picture.** says this window chooses which kinds of ants (castes) the queen raises, and that it is used like Behavior Control |
| 49 | 11096 | 2 | 233 | asks the player to go back to the Edit window via the Window menu (done when it is frontmost; eighty black ants are added now) |
| 50 | 11098 | 2 | 254 | **picture.** asks the player to press the yellow ant icon at the left so the window centres on the ant (done when the view centres) |
| 51 | 11100 | 2 | 232 | announces the first battle: an assault on the red colony far across the map |
| 52 | 11102 | 3 | 257 | asks the player to gather helpers: press and hold on the ant, choose Recruit 10, and repeat that about five times (done at roughly forty followers) |
| 53 | 11104 | 2 | 206 | states that roughly fifty ants are now ready for the assault |
| 54 | 11106 | 3 | 233 | asks the player to cross the patch to the entrance of the red nest (on the right) while dodging red ants (done when inside the red nest, or when the ant dies) |
| 55 | 11108 | 2 | 309 | shown when the player **reached** the red nest: congratulate them on a skilful run |
| 56 | 11110 | 2 | 271 | shown when the attack **failed**: sympathy and a push to practise and try again |
| 57 | 11112 | 4 | 452 | closes the tutorial: much remains to be found out, the Info window carries further advice, the help buttons remain available, and the player should simply enjoy experimenting |

Notes: step 18 sends the player to the black nest, which lies to the left of where they stand, and step 54 sends them to
the red nest's entrance, which lies to the right: keep those directions. Write "alarm scent" in the same term as the
scent menu's label (`ui_bitmaps.md`). Where a step would point at a printed manual (steps 17, 28, 41), point to the
help buttons or the Info window, or say nothing.

## E. The menus (`menus/menus.json`)

The pull-down menu bar across the top of the screen. Drawn in the 8 x 14 pixel text-cell font (font 0), one character
per cell. `menus.json` is one object:

```
{ "titles": ["F...", "W...", "V...", "O...", "S..."],
  "menus": [ ["item", "---", "item", ...], [ ... ], [ ... ], [ ... ], [ ... ] ] }
```

- `titles`: exactly 5, left to right. The bar opens each by **Alt plus the initial letter** (the key table is fixed:
  Alt+F, W, V, O, S) so the titles must **start with F, W, V, O and S** in that order. At most **9 characters** each, and the
  five together with a blank after each must fit the 80-cell bar (at most 60 cells in all). Title Case.
- `menus`: exactly 5 lists, one per title, with the item counts below. An item is its label, at most **14 characters**
  (the box is as wide as the longest label plus two cells). **A separator is the string `"---"` exactly**, and it
  stands only where the table shows one. Title Case, no trailing space, no `%`, printable ASCII.
- Typing a letter inside an open menu jumps to the next item whose label starts with that letter, so give the items of
  one menu different initial letters wherever you can (items that must share one are fine).
- The build adds the blank cell in front of every label; do not write it. The **first item of the Speed menu** is
  relabelled by the game while it runs (it alternates between pausing and resuming); give it any label of up to
  7 characters, the build pads it.
- Checked items are shown with a mark by the game; do not write marks.
- Items are listed in a fixed order because the game acts on the position, not the text. The order and meaning:

| Menu | # | Item does |
|---|---|---|
| **File** (title 0) | 0 | opens the About box (credits) |
| | 1 | separator |
| | 2 | starts a new game (opens Select a Game) |
| | 3 | loads a saved game |
| | 4 | saves the game |
| | 5 | saves the game under a new name |
| | 6 | separator |
| | 7 | quits the program |
| **Window** (title 1) | 0 | brings up the Edit window |
| | 1 | the Map window |
| | 2 | the Behavior Control window |
| | 3 | the Caste Control window |
| | 4 | the History window |
| | 5 | the Info window (the encyclopedia) |
| | 6 | the Status window (the efficiency score) |
| **View** (title 2) | 0 | the yard window in plain mode |
| | 1 | the yard window showing the house |
| | 2 | the yard window in strategic mode |
| | 3 | the yard window in graphic mode |
| | 4 | separator |
| | 5 | the Map window shows the surface |
| | 6 | the Map window shows the black colony's nest |
| | 7 | the Map window shows the red colony's nest |
| **Options** (title 3), each a switch | 0 | the view follows the walking yellow ant (auto tracking) |
| | 1 | music on / off |
| | 2 | sound effects on / off |
| | 3 | event pictures and message boxes on / off |
| | 4 | the status strip's advice lines on / off |
| | 5 | the silly speech balloons on / off |
| **Speed** (title 4) | 0 | pause / unpause (relabelled by the game) |
| | 1 | separator |
| | 2 | slow |
| | 3 | normal |
| | 4 | fast |
| | 5 | the fastest speed |

The labels should match the words of the window captions (list 1000), the game-mode names (list 1001) and the
Select-a-Game and tool labels in the bitmap specs.

## The build's checks

`python tools/clean_pack/build.py` (reads `src/strings/*.json` and `src/menus/menus.json`) refuses, with the file, list
and entry named: a list that is not in the game, is one of the 6 never-read lists, is in the wrong file or is given
twice; a wrong number of entries (the credits may have 10 to 80); an entry that is not a string, has characters outside
printable ASCII, a backslash or a percent sign, or a newline where none is allowed; an empty entry where text is
required, an entry in list 1800 [0..12] that is not empty, leading or trailing spaces; entries 13 and 14 of list 1800
that do not end / start with the space they must; a balloon entry with more than two lines; any line wider than its box
(exact, with the font widths above); the original game's, the publisher's or the franchise's name in any line; in the menus: a wrong
number of titles, menus or items, a separator in the wrong place (or an item where one belongs), a title whose
initial is not its Alt key, a too long label, too many cells in the bar. It encodes each list to `ARCHIVE/4/<id>.bin`
(the archive, SHARED or HCEGANT, is the measured one; it does not matter for you) and the menus to `SHARED/6/0.bin`.
`python tools/clean_pack/build.py --roundtrip=<pack.zip>` decodes every original list and the menu resource of a pack
and encodes them back byte for byte (119 lists and the menu resource: 0 problems).

## Not found / open

- **Engine side, not the pack.** The Edit window's caption starts with the product name from the program itself, not from
  a list: `Main.cs` builds it as a literal plus list 1800 [15] plus the mode name; for the clean pack the literal must
  become `OpenSimAnt`. A few fallback lines and dialogs in `Main.cs` (the file dialog's words, the overwrite alert, the
  game-over console line, "Click on a black colony to continue." as a fallback for 1010 [20]) are English text written
  in the code, to be moved to the pack or made our own (ROADMAP A6).
- **Entries never read:** 1010 [0], [1] and [18]; 1800 [0..12]; 1101 [0], [11], [15], [16] and 1102 [17], [18],
  [20..29] are placeholders for states and castes the game never produces. They must still exist.
- **List 1050 (History labels):** read by the original's History graph (a framed label at the end of each line) but
  not drawn by the remake yet; written anyway so the pack is complete.
- **List 10044** (the ant lion kills the yellow ant): the remake shows the scene picture only; the original may show
  this box too. Kept in scope.
- **Tutorial end:** the remake maps step 56 to list 11110 and never shows 11112, the closing box. The numbering is the
  original's; the code path may be off by one. The text is written either way.
- **Reachability** was decided by reading the code and an immediate-operand search of the original program, not by playing
  every screen; the shell's `--requests=<file>` log of a long game would confirm (it lists every list asked for).
- **Case/number conventions** (Title Case, sentence case) are conventions of this pack, not requirements of the code.
