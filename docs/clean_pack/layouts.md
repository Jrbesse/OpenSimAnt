# Spec: the window layouts (`HCEGANT` type 0)

37 resources: the layouts of 34 windows (ids 0..33) and three user-interface tables (128, 129, 131). A layout says where
every control of a window sits, how the placement follows the window when it is opened at another place, what kind of
control each is, which bitmap it shows and in which colour scheme it is drawn. The game reads them through
`remake/src/OpenSimAnt.Data/Layouts.cs` (the format: `docs/FILE_FORMATS.md` "Window layouts").

**Almost all of this is functional data and is not written by any maker.** `data/window_layouts.json` carries it as
numbers and ids, made by `tools/clean_pack/make_layouts.py` from the measurements of the player's pack (like the
SimAntipedia's card layouts, [texts.md](texts.md)), and `build.py` always builds it. What a maker writes is the **12 words
inside items** (below), in one small file.

## What is functional data (carried over as numbers, ART_PLAN section 2: window geometry, palette roles)

| In a layout | What |
|---|---|
| window header | the screen rectangle (640 x 480), the rectangle it was last opened at (the "requested" one that mode-5 edges follow), the decoration flags, a few header words the loader keeps |
| item rectangle, offsets, references, modes | where the item sits and how: each of its four edges is solved from an offset plus an edge of another item (any window's) or of the window's requested rectangle (`UiArt.Relayout`); an item's id is `window << 8 \| index`, the ids the code names (`0x102`..`0x118` are the Map window's commands) |
| item type | box, frame, picture, hotspot, button, list, scroll bar, caption, field (23 types in use, `Layouts.Types`) |
| flags, colour scheme, alternate scheme | alignment, clipping, which scheme the item uses (an index into table 129) |
| type bytes ("tail") | a text item's font, a frame's thickness, a picture's **bitmap id** (the pictures themselves are the bitmap specs), the list's fields |
| text that the code fills | the `printf` formats `%s`, `%d`, `%d%%` (14 items: window captions, counters, the file dialog's LOAD / SAVE button) and the eight drive letters `A:` to `H:`: format codes and device names, kept as they are |
| table 129 | the 16 colour schemes (foreground, second foreground, background, second background and two bytes) as palette indices |
| tables 128, 131 | 20 and 40 bytes of flags and limits that no code of the remake reads; carried unchanged |

What is **not** stored, because it means nothing: the item table's memory segments (the loader rebuilds the table) and the two
padding bytes behind each string (editor leftovers in some layouts). The encoder writes zeros there.

## What is creative: the words inside items (12)

Everything else a layout draws is a bitmap or a number. Twelve items hold readable words; they are the maker's
(`remake/game/assets/clean/src/layouts/texts.json`, an object `{"<window>.<item>": "text"}`, key = window id, a dot, the
item's index; all 12 keys, no others). The original words are not given here. Every text:

- printable ASCII (32..126), at least one character, no leading or trailing space, **no `%` and no backslash** (the game
  treats a string with `%` as a format and then draws no text), none of the original's names (OpenSimAnt is allowed);
- at most the room in pixels below, measured with the clean fonts (`src/fonts/font<n>.json`; font 0 = 8 px per character);
- written new, in your own words, the same job. Where a word is plainly the only natural one for a control, use it.
  Nothing here is long enough to share a run of words with the original (`python tools/clean_pack/overlap.py` on this file and
  on `src/layouts` must report 0 shared runs).

| Key | Item | Font, alignment | Room | Original length | What it says |
|---|---|---|---|---|---|
| `18.1` | caption bar of the window where the player sets what the black ants do | 0, centred | 202 px (25 chars) | 16 chars | the window's **fixed name**, exactly the words `src/strings/README.md` fixes: Behavior Control |
| `19.1` | caption bar of the window where the player sets the black colony's castes | 0, centred | 202 px (25 chars) | 13 chars | the fixed name: Caste Control |
| `21.1` | caption bar of the population history window | 0, centred | 312 px (39 chars) | 14 chars | the fixed name of that window, the Window menu's word (History) with at most one more word |
| `22.6` | the label of the file dialog's folder line (the game clears that line and writes the current folder over it, so it is rarely visible) | 0, left | 195 px (24 chars) | 5 chars | a label for "the folder shown here" |
| `22.10` | the file dialog's label above the row of eight drive buttons (A: to H:) | 0, left, **not clipped** | 112 px (14 chars; the row to its right is free) | 13 chars | an invitation to choose a drive |
| `22.20` | the file dialog's button that leaves the dialog without opening or saving anything | 0, centred | 83 px (10 chars) | 6 chars | abandon the dialog. The game letters the dialog's other button (LOAD / SAVE) in capitals, so this one in capitals |
| `27.1` | the last line of the fixed-size message box (layout 27), under its text | 2, centred | 271 px | 22 chars | tells the player that a mouse click closes the box and the game goes on |
| `30.2` | the same line in the message box that is as wide as its text (layout 30: the tutorial's and the events' boxes, the ones the game draws with a picture above the lines) | 3, centred | **84 px** (that box can be as narrow as 58 px, so the line may be no wider than the original's own, 84 px in font 3) | 22 chars | the same meaning as `27.1`; give both the same words (so they must fit both fonts: at most 84 px in font 3 and 271 px in font 2) |
| `28.1` | the title button of the developer window of debug actions (opened only by a key combination) | 0, centred | 192 px (24 chars) | 5 chars | a one-word name for "debug tools", in capitals |
| `33.3` | the quit / new-game prompt's button that continues without saving the running game | 0, centred | 83 px (10 chars) | 10 chars | go on without saving; Title Case |
| `33.4` | the same prompt's button that saves the running game first | 0, centred | 65 px (8 chars) | 4 chars | save; Title Case |
| `33.5` | the same prompt's button that cancels what the player asked for and returns to the game | 0, centred | 68 px (8 chars) | 6 chars | cancel; Title Case |

Notes for the maker:

- The captions `18.1`, `19.1`, `21.1` should agree with the clean Window menu (`Edit, Map, Behavior, Caste, History, Info,
  Status`) and with the tutorial text that names the windows (`strings.md`); a caption is the menu word plus, for the two
  control windows, the word Control.
- `33.3` is the widest of the three prompt buttons; the three sit in a row, the two outer ones are the "no save" and "cancel"
  buttons. Keep the three words clearly different from each other.
- A text may be much shorter than its room. Buttons are centred; only `22.6` and `22.10` start at the left.

## `data/window_layouts.json` (made by `make_layouts.py`, 285 items in 34 windows)

```
{"windows": {"<id>": {"rect": [l, t, r, b], "requested": [l, t, r, b], "flags": n, "misc": {"<byte offset>": value},
                      "items": [ {"rect", "off", "ref", "mode", "state", "type", "flags", "scheme", "alt", "tail",
                                  "text": {"format": "%s"} | {"literal": "A:"} | {"key": "22.10"}}, ... ]}},
 "tables": {"128": [bytes], "129": [bytes], "131": [bytes]},
 "texts": {"<key>": {"window", "item", "type", "font", "align", "clip", "rect", "room_px", "chars"}}}
```

`texts` is the room table above, measured (`chars` is the original text's length, a count only). `build.py` takes the room
from it, so the table in this spec and the checks cannot drift apart.

## Build and checks

`tools/clean_pack/build.py` (`cat_layouts`, `enc_layout`):

- a window with no words of the maker's (26 of the 34) and the three tables are always built to `HCEGANT/0/<id>.bin`;
- a window with makers' words (18, 19, 21, 22, 27, 28, 30, 33) is built when all its words are in `texts.json` and valid;
  otherwise it is listed as missing (`HCEGANT/0 8`), or taken from the fallback pack with `--fallback`;
- each text is refused when it is empty, not ASCII, has `%` or a backslash, a banned name, or is wider than its room.

`python tools/clean_pack/build.py --roundtrip=remake/build/original_pack.zip` decodes every original layout into the JSON's form
and encodes it back: the JSON must equal the pack's layouts, the encoding with the original's own dead bytes must be
byte-identical for all 34, and with zeros in the dead bytes it may differ from the pack only at those bytes; the three tables
must be byte-identical.

## Not covered

- The words the **program** writes into formats (the file dialog's LOAD / SAVE, "OVERWRITE", the Pause / Unpause relabel) are in the
  engine, not in a layout ([strings.md](strings.md), "Not found / open").
- The colour schemes (table 129) are carried as measured. A later change of the pack's colour roles is a decision for the
  project, made by editing that table.
