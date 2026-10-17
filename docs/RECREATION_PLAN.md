# Recreating SimAnt in Godot — Plan

See [FILE_FORMATS.md](FILE_FORMATS.md) for how the original data is laid out. All of it can now be extracted
with `tools/extract.py`.

## 1. What we have and what we don't

**Solved (assets):**
- All 840 resources unpack: 212 color bitmaps, 40 mono bitmaps, the palette, 113 string tables, 94
  help/encyclopedia texts, 4 fonts, 30 MIDI songs, and 57 sound effects.
- We have the complete text of the game: tutorial script, death messages, ant chatter, the 53-card
  "SimAntipedia" encyclopedia, and end-of-game ratings.

**Not solved (rules):** the simulation lives only in `SIMANT.EXE`. The assets tell us *what* exists but
not the numbers: how fast pheromones evaporate, how the AI picks targets, how combat resolves, and so on.
That is the real work of this project.

The string tables give us a solid skeleton of the simulation's vocabulary. These lists are almost
certainly the original enums, in their original order:

| Concept | Values (from the game's own strings) |
|---|---|
| Views | BackYard, Surface, Black Nest, Red Nest, Yard, House, Strategic, Graphic |
| Pheromones | Black Nest Marker, Black Trail Marker, Red Nest Marker, Red Trail Marker, Alarm |
| Ant AI states (`STR# 1102`) | Bored, Nesting, Foraging, Got Food, Dig In, Dig Out, Defense, Attack, Hatching, Egg Laying, Fighting, Alarmed, Defend Nest, Resting, Pre-Flight, Take off, Flying, …, Avenger |
| Carried item per state (`1103`) | Nothing / Egg / Food / Dirt |
| Castes (`1101`) | Egg Tender, Worker, Soldier, Male, New Queen, Replete, Queen |
| Brood stages (`1100`) | Weird Egg, New Egg, Egg, 1st–3rd Instar, Pupae, Hatching Pupae |
| History stats (`1050`) | BPop, BFood, BHealth, SFood, Expired, RPop, RFood, RHealth, Eaten, Killed |
| Player commands | Recruit 5 / Recruit 10 / Release ½ / Release All / Exchange / Dig Hole / Start Brood / Chase / Hunt |
| Colony controls | Behavior triangle (Forage / Dig / Nurse), Caste triangle (Workers / Soldiers / Breeders), 3 presets each, Auto/Manual |
| Hazards | enemy ants, spider, ant lion, human foot, lawn mower, flooding/rain, insecticide, electrocution, starvation |
| Modes | Tutorial, Quick Game (one patch, Black vs. Red), Full Game (whole yard plus house), Experimental (sandbox tools), Load |
| Experimental tools | Ant Info, Barriers (walls/rocks), Dig/Fill, Add Ants, Add Food, Drop Trails, Insecticide |

## 2. Guiding decisions

1. **Bring your own data.** The art, music and text belong to Maxis/EA. The Godot project should
   ship *no* original assets. Instead it should read the player's own `SHARED/HCEGANT/SOUND` files at
   first launch and cache converted PNG/OGG files under `user://`. OpenRCT2 and OpenTTD use this model.
   It keeps the repo publishable. (Don't commit `extracted/` to a public repo.)
2. **The simulation is a pure library, separate from rendering.** It uses plain `RefCounted` classes with
   no Nodes, a fixed tick rate, a seeded RNG and serializable state. Views only read from it. This makes
   it testable, makes save/load trivial, and lets you compare runs against the original.
3. **Be faithful where it matters and modern where it doesn't.** Match the rules, timings and feel
   exactly. Modernize the windowing: one resizable window, integer pixel scaling, and remappable
   keys instead of a 1991 MDI desktop.
4. **Use DOSBox as a lab instrument, not as the way to play.** You don't want to *play* in an emulator,
   but running the original side by side is the fastest way to answer "what does it actually do?" The
   DOSBox-X debugger can also dump memory while the game runs, which pairs well with Ghidra.
5. **Language:** GDScript for everything at first. The original ran on a 286, so the entity counts
   are small. Only move the hot loop (ant ticks, pheromone diffusion) to C# or a GDExtension if profiling
   says so.

## 3. Architecture (Godot 4.x)

```
simant-godot/
  importer/      # GDScript port of tools/simres.py + bitmaps + sfx decoder; MIDI→OGG step
  sim/           # pure logic: World, Patch, Grid layers, Colony, Ant, Brood, Pheromones, Actors, Rules
  views/         # SurfaceView, NestView, YardMapView (isometric), HouseView, CutscenePlayer
  ui/            # toolbars, caste/behavior triangles, history graph, info cards, balloons, dialogs
  data/          # *your own* tuning tables (JSON) filled in as RE uncovers constants
  tests/         # GUT or gdUnit4 tests for sim rules (determinism, lifecycle, combat)
```

- **Grids:** each patch keeps per-cell layers (terrain/dirt, food, 5 pheromone channels, occupancy) in
  `PackedByteArray`/`PackedFloat32Array`. The surface and the two nests are separate grids.
- **Rendering:** a `TileMapLayer` for terrain and `MultiMeshInstance2D` (or a single `_draw()`) for
  ants. That handles thousands of ants in one draw call. Pheromones go in an overlay `ImageTexture`
  updated each tick.
- **Audio:** Godot has no built-in MIDI synth. The simplest route is to render the 30 `.mid` songs to OGG
  at import with a General MIDI SoundFont (FluidSynth). Alternatively, play them live with a GDScript MIDI
  player plus a SoundFont. Sound effects become `AudioStreamWAV`.
- **Fonts:** convert the Mac `FONT` strikes to BMFont `.fnt` + PNG, which Godot imports natively,
  for that pixel-exact UI text.

## 4. Milestones

### M0 — Finish the asset pipeline *(mostly done)*
- [x] Archive reader, LZSS, bitmaps, palette, strings, texts, MIDI, SFX
- [ ] Confirm the SFX sample rate by ear (11025 Hz is a guess) and look at sound #56's odd table
- [ ] Decode fonts (type 11, `FONT1-4`) to BMFont
- [ ] Decode cursors (types 6/7/8), layouts (types 0/9), card layouts and styles (types 17/21)
- [ ] Find where the tiny surface and nest ant sprites come from (probably drawn in code)

### M1 — Reverse-engineer the rules *(the critical path; runs alongside M2–M5)*
- Load `SIMANT.EXE` into **Ghidra**. Work out how the ~290 KB appended overlay region gets loaded and
  map it in as extra segments.
- Use the debug strings as anchors: `YARD AREA`, `Yardmode`, `GOT Scenario`, `CHEAT %d`,
  `DBRecall`, the `STR#` ids (1100–1103 are read wherever ant info is shown, which leads you to the
  ant struct).
- Goals, in order: (1) the ant record layout and the per-tick state machine; (2) grid sizes for
  surface, nest and yard; (3) pheromone deposit/decay/diffusion; (4) brood timings and caste
  allocation from the triangle; (5) combat; (6) predator and human AI; (7) the save-file format
  (`.ANT`), so old saves could be loaded.
- Write findings into `docs/SIM_NOTES.md` and turn the constants into `data/*.json`.

### M2 — Godot skeleton
- Project setup, importer running on first launch, title screen (bitmap 2001), "Select a Game"
  screen (2500), About box (3000/3001), music playback.

### M3 — One patch, surface only
- Terrain grid, food spawning, the yellow ant under player control (move, pick up, drop, lay trail),
  black workers foraging with trail pheromones. Map overview window.
- This is the first "it feels like SimAnt" moment, so get the ant-movement feel right here.

### M4 — The nest
- Side-view nest grid, digging (Dig In/Dig Out), queen egg-laying, the brood lifecycle (egg →
  instars → pupae → adult), nurses, food storage. Behavior and caste triangles drive allocation.

### M5 — Quick Game (first fully playable build)
- Red colony mirrored on the same patch, soldiers, combat, Alarm pheromone, Recruit/Release/Exchange
  commands, win/lose for one patch, history graph, game-over screen with ratings (`STR# 1900`).

### M6 — Hazards and wildlife
- Spider (hunt + "Spider Slayer" kill by swarm), ant lion pits, human walking/stomping, lawn mower,
  rain/flood, insecticide, plus the death cutscenes and their texts.

### M7 — Full Game
- Isometric yard map of patches, house view, mating flights (males and new queens), founding new
  colonies, transferring the yellow ant between patches, driving the humans out (winning).

### M8 — Remaining modes and content
- The Tutorial, scripted from the existing tutorial strings (`11000+`, `1030`). Experimental mode tools.
  The SimAntipedia card browser (types 17/19/10/21). Save/load.

### M9 — Modern polish (optional)
- Speed controls, scalable UI, optional CRT/scanline shader, a 1-color-per-palette-slot "remaster"
  palette option, Steam Deck/gamepad support.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Overlay loading in the EXE is non-standard, so Ghidra misses code | Find the loader early in M1; DOSBox-X memory dumps after the overlays load give you a flat image to analyze |
| RE takes longer than expected | M3–M5 can proceed on "observed behavior" from DOSBox side-by-side, with numbers refined later |
| MIDI sounds different from the original AdLib/Roland | Offer 2–3 SoundFonts, or emulate OPL (e.g. an OPL3 emulator GDExtension) for authentic AdLib |
| Legal | Ship code only; require the player's own original files |

## 6. Suggested next steps

1. Run `python -I tools/extract.py` and browse `extracted/` (start with `hcegant_sheet.png`).
2. Get the original manual and addendum (the in-game card text is in `extracted/shared/text/`) as a
   rules reference.
3. Start M1 (Ghidra) and M2 (Godot skeleton + importer) in parallel.
