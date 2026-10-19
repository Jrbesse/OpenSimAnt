# Play-test profile: the Formica shell

A checklist for playing the remake by hand. Every screen below was built from the original's code and checked
only with screenshot flags. Nobody has played it yet. Work through the sections in order, tick what behaves,
and write down anything that differs from the original or from what's described here (see "Reporting" at the
end). Sections 1-4 make a good first sitting (~30 min); the rest can come later.

## 0. Setup

- Build: `dotnet build remake/game/Formica.csproj`, then open `remake/game` in Godot 4.6 (.NET) and press
  Play, or run Godot with `--path remake/game`.
- The original files (SIMANT.EXE, HCEGANT / SHARED / SOUND .DAT + .NDX, FONT1..4) must be in the repository
  root (or pass `-- --game-dir=<path>`).
- Saves go to `%APPDATA%\Godot\app_userdata\Formica\` (quick save: `quicksave.ANT`).
- Keep the Godot output panel / console visible: messages and errors print there.
- Full key list: `remake/README.md` ("Keys"). The original's keys are listed first.

## 1. Start-up and new games

- [ ] The title screen shows; a click brings up Select a Game.
- [ ] Quick Game, Full Game and Experimental each start the right kind of game (the status line names it).
- [ ] Cancel closes the dialog.

## 1c. The Tutorial (Select a Game > Tutorial)

- [ ] Its message boxes appear one by one (some with a small picture); each step waits until you do what it asks
  (dig, go outside, walk, recentre with Backspace, scroll, open the Map window with Tab, eat, carry food home,
  move a rock, recruit, alarm scent (the text says Escape, a leftover of the Mac version: SIMANT.EXE has no Escape check, its alarm key
  is 0), the yard, House,
  Patch, the Behavior and Caste windows, enter a nest).
- [ ] A step you don't do shows its message again after a while.
- [ ] Note any step that cannot be completed in the shell (the checks are the original's; the shell's controls
  must set what they read).
- [ ] File > New / Ctrl+N mid-game asks to save first; DON'T SAVE, Save and Cancel each do what they say.
- [ ] File > About shows the about box; a click closes it.

## 1b. The menu bar (the original's menus, SHARED type 6)

- [ ] File / Window / View / Options / Speed across the top. Press on a title, slide to an item, release: it runs.
  Click a title: the menu stays open; click an item (or elsewhere to close).
- [ ] Alt+F / W / V / O / S and F2..F6 open them; Up / Down, Left / Right, a letter, Enter, Esc work.
- [ ] Window: Edit, Map, Behavior, Caste, History, Info (SimAntipedia), Status (Efficiency Score).
- [ ] View: Yard / House / Strategic / Graphic open the yard window in that mode; Surface / Black Nest / Red Nest.
- [ ] Options (► = on): AutoTrack (the view follows the walking yellow ant), Sound Effects, Events (death
  messages), Messages (the advisor's line), Silly (speech balloons, drawn as the original's
  balloon bitmaps: off at start, as in the original). Music
  (the songs, through the remake's own FM voices: listen for wrong instruments, timing or pitch; the console
  prints "music: song N").
- [ ] Speed: ► on the current speed; Ultra runs faster than Fast; Pause reads "Unpause" while paused.
- [ ] Options and speed carry over to the next new game.

## 2. The yellow ant (Edit window)

- [ ] Click on the map: the yellow ant walks there (after a short pause: the original waits for a double click).
- [ ] Double click (or right click / Shift+click): acts: eats or picks up / drops food on the surface, digs in a
  nest (or picks up / drops food, rocks, brood), walks up to an ant to meet (colony-mate) or fight (enemy).
- [ ] Quick click on the yellow ant: the view recentres on it. Press and hold on another ant (or Ctrl+click):
  the Ant Info window (caste, state, carrying).
- [ ] Food: pick up, carry into the nest, drop; eat when hungry (health bar on the left).
- [ ] Enter and leave the nest through the hole; the view follows (Surface / Black / Red nest).
- [ ] Hold the button on the yellow ant: its menu. Recruit 5 / 10, Release 1/2 / All, Exchange (then click an
  ant) all work.
- [ ] As a queen (after a mating flight, Full Game): Dig Hole, Start Brood in the menu.
- [ ] As the spider (Exchange onto it): Chase, Hunt; Alt for lash out.
- [ ] Death: the message box text matches the cause (eaten, mower, drowned, ...); you take over another ant.

## 3. The original's keys

- [ ] 1 / 2: recruit 5 / 10 (a queen: dig hole / start brood; the spider: chase / hunt).
- [ ] 3 / 4: release half / all. X: exchange. 0: alarm trail on / off.
- [ ] Backspace while walking: stops. Backspace standing still: recentres. Shift+Backspace: follows.
- [ ] Shift+0: pause. Shift+1 / 2 / 3 / 4: slow / normal / fast / ultra (the status line shows the speed).
- [ ] Ctrl+E / Ctrl+M: Edit / Map window to the front. Ctrl+B / Ctrl+C: Behavior / Caste Control.
- [ ] Ctrl+T: Efficiency Score. Ctrl+Y: the yard window (Full Game).
- [ ] Ctrl+H History, Ctrl+I the SimAntipedia; Ctrl+4 back to the patch, Ctrl+5 / 6 / 7 the yard window's House /
  Strategic / Graphic views; Ctrl+8 / 9 / 0 Surface / Black / Red nest; Alt+2 recruits all.
- [ ] Ctrl+K: sound effects off / on. Tab: Map window front / hide.
- [ ] Ctrl+S: save dialog, type a name, SAVE (or Enter); Ctrl+L: load dialog, click / double-click the file.
- [ ] Ctrl+Q: asks to save, then quits.
- [ ] Shell keys still work: Ctrl+1 / 2 / 3 views, arrows scroll, Space pause, + / - speed, F8 / F9 (quick save / load).

## 4. Map window and the colony controls

- [ ] Click the map to look there; the scent layers; Show Trails.
- [ ] Hold the population report: the detailed per-caste window.
- [ ] Behavior / Caste Control: drag the marker; Auto / Manual; Set 1..3 presets; the bars and corner values
  move as the colony changes.
- [ ] History: the series buttons (up to four at once), the scale label.
- [ ] Efficiency Score: values look sane (the Full Game's universe column filled, Quick Game "N.A.").
- [ ] Mystery Button and Center on Yellow.

## 5. The SimAntipedia (Map toolbar: Ant Info)

- [ ] Opens on Top Card. Each topic label opens its card. The caption shows the card's name.
- [ ] BACK goes up a level, PREVIOUS retraces your path, TOP returns to Top Card.
- [ ] Hold the button on a bold word (e.g. "chitin" on Ant Anatomy): a definition pops up and goes away on
  release. Picture labels with definitions (Head: Ocelli, Maxillae) do the same.
- [ ] Text wraps the way it did in the original; bold words in the bold font. Escape / a click outside closes it.

## 6. Full Game: the yard

- [ ] The yard window: Patch / House / Strat / Graphic views; the human, mower, dog, bird, rain.
- [ ] Moving to another patch (click a patch next to the colony), the refusals ("suicide to transfer", ...).
- [ ] MATE, AUTOMATIC / MANUAL, PLACE (a new queen within 3 patches, Shift to keep placing).
- [ ] Losing the colony's last ant opens the yard to pick another.
- [ ] The house patches.

## 7. Experimental game

- [ ] The tool palette pops up from the Experimental button; holding a tool shows its options.
- [ ] Rocks, dig, ants, food, pheromone, insecticide on the Edit map; Alt removes; drag paints.
- [ ] Start Game returns to a Quick Game. No food appears by itself (expected).

## 8. Endings

- [ ] Lose a Quick Game (let the reds win) and win one: the GAME OVER window shows the mode, the score and
  the rating title; a click leads to Select a Game. (`-- --game-over` shows the window directly.)
- [ ] Full Game win / loss messages.

## 9. Long run

- [ ] Leave a Full Game on fast for 30+ minutes: no crash, no stall, memory steady.
- [ ] Save, quit, start again, load: the game continues where it was.

## Known gaps (don't report these)

Music; the pull-down menus (their labels are not in the data); the tutorial; the help (empty in the DOS
version anyway); speech balloons and event markers as bitmaps (text stands in); the file dialog's folders,
path line and drive buttons; the Edit window's bottom strip; exact frame styles; the isometric yard map.
Sound effects are a best guess at the sample rate.

## Reporting

For each issue, one line or a short note:

```
[section] what you did → what happened (expected: ...)
seed / mode / tick (from the status line), F8 quick save attached if it can be reproduced, screenshot if visual
```

Fidelity notes are as useful as bugs: anything that "feels different" from the original (speed, colours,
text placement, how ants behave) is worth a line. Note how sure you are.
