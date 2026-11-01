# Clean strings and menus

New, original text for the game's 113 string lists and the pull-down menus, written from `docs/clean_pack/strings.md`
by an isolated agent (spec only). Files: `system.json`, `balloons.json`, `messages.json`, `tutorial.json` here and
`../menus/menus.json`.

## Voice

Friendly, short and a little cheeky. Status and advisor lines speak to the player ("You ..."); balloons are in
character and jokey (the spider is smug, the queen weary, the person absent-minded); death messages are good-humoured
and always say the player carries on as another ant; the tutorial is encouraging, one task per box. Printable ASCII
only. The only product name is "OpenSimAnt".

## Words fixed

- Windows: Edit, Map, Behavior Control, Caste Control, History, Status, Info. Modes: Tutorial, Quick Game, Full Game,
  Experimental.
- Menus: File (About, New Game, Open Game, Save Game, Save As, Quit), Window, View (Yard, House, Strategic, Graphic,
  Surface, Black Nest, Red Nest), Options (Tracking, Music, Sounds, Events, Advice, Balloons), Speed (Pause, Slow,
  Normal, Fast, Turbo). Map and yard captions (list 1000) are the View words plus "View" or "Scent Map".
- The scent the player lays with the 0 key is "alarm scent". The player's ant is the yellow ant; the colonies are
  black and red.
- Ant Info window: castes Nurse, Worker, Food Worker, Male, Soldier, Young Queen, Replete, Queen, Fighter; carrying
  words Nothing, An Egg, Food, Dirt.
- History labels are short forms: B / R = black / red colony (Pop, Food, Health), Surface (food on the surface),
  Deaths, Eaten, Killed.

## How to check

`python tools/clean_pack/build.py` from the repository root. It checks counts, characters, pixel widths and banned
names for these files and encodes them.
