#!/usr/bin/env python3
"""Generate the OpenSimAnt reference pages under docs/reference/ from tools/ref/simant_ref/.

The site is the publication surface for the reverse-engineered code: one page per module, each with what the
module ports, which original routine it came from, and the full annotated source, plus a raw .py download and a
zip of the whole package.

    python tools/gen_devlog_reference.py            # regenerate
    python tools/gen_devlog_reference.py --check    # fail if the committed pages are stale

The module notes below are hand-written; everything else (line counts, function lists, addresses quoted from the
docstrings, the source) is read from the code so a page can never describe a file it does not contain.
"""
import ast
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "tools" / "ref" / "simant_ref"
OUT = ROOT / "docs" / "reference"
RAW = ROOT / "docs" / "assets" / "reference"
TOOLS_RE = ROOT / "tools" / "re"
TOOLS = ROOT / "tools"
TOOLS_REF = ROOT / "tools" / "ref"

GROUPS = [
    ("core", "The machine underneath"),
    ("surface", "The surface world"),
    ("colonies", "The colonies and the game"),
    ("interface", "The player and the interface"),
]

# file -> (title, group, one-line subtitle, what it ports, [what to know])
MODULES = {
    "state.py": (
        "The memory mirror",
        "core",
        "One bytearray that is the 1991 program's address space.",
        "`State` covers flat linear `0x3d570..0x62000` of the original program image and gives the port the "
        "original's accessors: `u8`, `s16`, `set32`, addressed by `(segment, offset)`. It holds the constant "
        "tables `T` (`0x3d57`), the simulation segment `SIM` (`0x3e1d`), the far globals `G` (`0x50f6`) and "
        "DGROUP `DS` (`0x55b3`). The initial bytes are read from `tools/re/build/flat.bin`, built from the "
        "user's own `SIMANT.EXE`.",
        [
            "150,160 bytes. A verifier compares all of them after every call, so a routine cannot be 'roughly' right.",
            "The game's real-time clock (`f_1bc34`, roughly 18.2 ticks a second) is kept outside the buffer: the "
            "engine owns it, the simulation only reads it.",
            "The red food-trail pheromone map lives past the 64 KB SIM segment (`0x4da7:0000`), which is why the "
            "buffer is not simply one segment.",
        ],
    ),
    "rng.py": (
        "The two random number generators",
        "core",
        "An LFSR and Microsoft C's rand(), both draw-for-draw.",
        "The simulation draws from two generators in parallel and both are load-bearing. `Lfsr` is the game's own "
        "16-bit Galois LFSR at `DS:8ba2`: `x <<= 1`, and `x ^= 0x1bf5` on carry. `CrtRand` is Microsoft C 6.0's "
        "`rand()`: `s = s * 214013 + 2531011`, returning `(s >> 16) & 0x7fff`.",
        [
            "`rand_low(n)` is `min(rand(n), rand(n))` (`f_0095b`) — the original's biased-for-zero variant, not a "
            "uniform roll.",
            "`bits(mask)` covers the `x & mask` family at `0093:0169..0250` that the game uses for small ranges.",
            "Matching a seed is not enough: the spider composite, the speech balloons and the yard rain all consume "
            "draws, so a port must call them at the original's moments or the streams diverge.",
        ],
    ),
    "tables.py": (
        "The constant tables",
        "core",
        "The gameplay numbers, read from your executable at runtime.",
        "Access to `T` (segment `0x3d57`) and `DS`: direction deltas, behaviour tables, caste odds, terrain and rock "
        "shapes, the save layout. Nothing in this file is decoded into the repository — every value is read from "
        "`tools/re/build/flat.bin`, which is built from the copy of `SIMANT.EXE` on the machine running the tools.",
        [
            "This is the boundary the project's legal position rests on: the rules are published, the original's "
            "data is not.",
            "`t_bytes`/`ds_bytes` take `(offset, length)`; `signed` reinterprets a byte as a signed 16-bit word.",
            "Building `flat.bin` is one command: `python tools/re/build_flat.py` from `tools/re`.",
        ],
    ),
    "sim.py": (
        "SimStep — one game tick",
        "core",
        "The original's tick order, preserved exactly.",
        "`sim_step` is `f_0894e`: it bumps the tick counter and the millisecond clock, resets the on-screen event "
        "records when the patch is being watched, and then calls every ported phase in the original's order — "
        "health decay every 64 ticks, the slow phase every 32, the yard, weather, ant lions, the spider, the "
        "caterpillar on odd ticks, the advisor, the census, surface ants, black nest, red nest, the yellow ant, "
        "the player action, the advisor's status line, and the game-over check.",
        [
            "Order is not cosmetic: several phases read flags the previous one set on the same tick, and swapping "
            "two calls changes the random stream.",
            "Screen-only effects leave through `st.player.effect` (status text, sounds, messages) and the game-over "
            "screen through the `st.player` hooks, so the simulation stays headless.",
            "The tick counter wraps at `0x1000`, which is why the decay phases test `& 0x3f` and `& 0x1f`, not `%`.",
        ],
    ),
    "savefile.py": (
        "Saved games (.ANT)",
        "core",
        "307 blocks, 48,386 bytes, in the original's order.",
        "Save (`f_6c328`) and load (`f_6c1a0`) write the game state as a headerless concatenation of memory blocks, "
        "in the order of the table at `4E4B:0000` in `SIMANT.EXE`: `{count, size, far pointer}`, 8 bytes per entry, "
        "terminated by a zero size. The table is read from the player's own executable at runtime.",
        [
            "No header, no version field — compatibility with a 1991 save file is the point.",
            "The fix-ups on load (`f_6cf1a`, `f_6cf5b`) are the original's pointer patching, reproduced in "
            "`prepare_load`/`finish_load`.",
            "Anything omitted from the table is rebuilt on load rather than stored.",
        ],
    ),
    "terrain.py": (
        "Surface terrain generation",
        "surface",
        "The yard patch: rocks, pits, the house, and the layout solver.",
        "Generates one yard patch (`f_73020`, section 20) on a 128 × 64 grid indexed `[a][b]` and stored flat as "
        "`a*64 + b`, exactly like the original's `0x3e1d:0180`. It places rocks, pits, special objects and the "
        "house patch, drawing from the LFSR as it goes. `Patch` runs standalone with its own generator; "
        "`StateSurface` drives the live game `State` and the original's globals.",
        [
            "The house screens are composed from a wall/box/counter/stove vocabulary — `_wall_left`, `_box_wide`, "
            "`_counter`, `_stove` — rather than drawn as a bitmap, because the original composes them too.",
            "Determinism here is seed-only: the same seed and patch coordinates give the same yard, which is how "
            "the screen comparisons are reproducible.",
            "Grid conventions matter: `a` is horizontal 0..127, `b` vertical 0..63, and a transposed access still "
            "looks like a plausible yard while being wrong.",
        ],
    ),
    "movement.py": (
        "Surface movement and steering",
        "surface",
        "Walking, turning, edge avoidance, and the direction heuristics.",
        "The shared steering layer for surface ants (`0ad9`, `0be8`, `1383`, `10f7`): one step with collision, "
        "patch-edge direction, `dir_to`, `turn_aside` when blocked, `forage_dir`/`home_dir`/`alarm_dir` and the "
        "guard directions. Every ant state handler calls into these rather than moving itself, which is why the "
        "same twelve lines reproduce the original's slightly awkward gait.",
        [
            "`best_neighbour` picks a direction by trying candidates in a fixed order — the order is the behaviour, "
            "not an implementation detail.",
            "`in_patch` and `at_nest_entrance` are the two boundaries that keep an ant on its own patch.",
            "The original reads the surface grid for passability before every step; the port does the same, which "
            "is why ants cannot walk through a rock the map just gained.",
        ],
    ),
    "pheromones.py": (
        "Pheromone maps",
        "surface",
        "64 × 32 cells, one per 2 × 2 tiles, with four decay curves.",
        "The pheromone layers (`1496`): each map is addressed as `(segment, offset)` like the original, cell index "
        "`ca*32 + cb` with `ca = a>>1`, `cb = b>>1`. `decay_linear`, `decay_halving`, `diffuse_alarm`, `lay_max` "
        "and `wear_trail` reproduce the four different decays the game uses for food trails, alarm, nest markers "
        "and the red trail.",
        [
            "The red food trail sits at `0x4da7:0000` (`SIM + 0xf8a0`), outside the 64 KB simulation segment.",
            "Decay runs on the tick counter's low bits, so a pause in the emulator changes pheromone strength if "
            "you get the phase wrong.",
            "`lay_max` is a maximum, not an add: two ants laying the same cell do not stack the value.",
        ],
    ),
    "surface.py": (
        "Surface ants",
        "surface",
        "The dispatcher and the twenty state handlers.",
        "The surface ant tick (`0894`): ants are structure-of-arrays inside the SIM segment, and the occupancy "
        "grid stores each ant's type byte (bit 7 red, bits 3–6 caste, bits 0–2 heading). `surface_ants_tick` walks "
        "the live list and dispatches to twenty handlers — bored, nesting, foraging, got-food, dig-out, defense, "
        "attack, hatching, egg-laying, fighting, alarmed, defend-nest, resting, the flight sequence, the avenger — "
        "plus the fight resolver, corpse placement and recruitment.",
        [
            "This is the largest behavioural surface in the game and the file most trace calls land in; it is also "
            "where a one-instruction difference shows up as ants that 'feel' wrong.",
            "`resolve_fight` and `place_corpse` mutate both ants' arrays and the grid, so call order is part of "
            "the result.",
            "The player's yellow ant is not a surface ant: its hooks are called from here, but its upkeep lives in "
            "`player.py`.",
        ],
    ),
    "world.py": (
        "Weather, predators and the slow phases",
        "surface",
        "Rain, the spider, the caterpillar, ant lions, the history graph.",
        "Everything SimStep updates that is not an ant and not the yard (`0894`, `1be8`, `1e2e`, `892c`): the "
        "history graph and its labels, the advisor's status line and census advice, the slow phase, weather, the "
        "ant lions, the caterpillar, and the spider with its prey selection, lash, follow and beaten frames.",
        [
            "Predators are the main consumer of the LFSR besides the ants — reproducing the spider exactly means "
            "reproducing its draw count.",
            "The history graph samples all 64 slots from `G:04F4`, newest first, and only while the window is held.",
            "Screen-side effects (status text, dirty cells, sounds) go out through `st.player.effect`; the state "
            "changes stay here.",
        ],
    ),
    "yard.py": (
        "The yard layer",
        "surface",
        "191 other patches, the human, the mower, the dog, the bird and the rain.",
        "The world outside the player's patch (`f_68513`, segment `783a`), run every tick: the human walking or "
        "roaming with the lawnmower, foot stamps on the player's patch, the bird crossing, the dog and its bark, "
        "rain control, and the colony strengths of the yard's other 191 patches (12 × 16, per-patch strengths at "
        "`T:00A4[col*16 + row]`).",
        [
            "The human is a routine, not an AI: a small state machine of habits, which is also why Formica's design "
            "calls him 'weather'.",
            "A foot stamp is a terrain edit plus a nudge; the mower removes a bit of grass per cell it crosses.",
            "`new_colony` and `yard_colonies` are the slow simulation of ants nobody is watching, and they are why "
            "the yard keeps changing while the player is inside the nest.",
        ],
    ),
    "colony.py": (
        "Colony bookkeeping and policy",
        "colonies",
        "Health, census, priorities, caste choice, the advisor.",
        "Colony-level rules (`899e` and helpers): health decay and food drops, the census, statistics, the "
        "black and red priorities that steer what the nest does next, `choose_hatch_caste` (which caste an egg "
        "becomes), `choose_manual_job`, the red launch-attack decision, the avenger spawn, and the advisor's "
        "status line.",
        [
            "Priorities are what the player's behaviour and caste triangles actually change — the click in the "
            "triangle sets weights that sum to `0xFFFF`.",
            "`sin256`/`cos256` are integer sine/cosine tables; `_cdiv` reproduces C's truncating division for "
            "negative operands.",
            "The census drives both the statistics screen and the game's rating, so it runs every tick, not once "
            "per second.",
        ],
    ),
    "newgame.py": (
        "New game and patch setup",
        "colonies",
        "A fresh yard, two colonies, the yellow ant, every counter.",
        "`f_6b36b` and `f_6ae20`: clears the world, resets the yard and the patch globals, scatters both colonies, "
        "digs the starting nests and queen chambers, builds the surface ants, places the yellow ant and sets the "
        "view. The starting patch is yard patch (col 11, row 8) and its seed is `SIM:0000 + 2 * (row * 12 + col)`.",
        [
            "Game modes at `G:0EAC`: 0 tutorial, 1 Quick Game, 2 Full Game, 3 experimental — each changes what is "
            "set up, not how the simulation runs.",
            "The queen chamber and pre-dug tunnels are laid out by `_queen_chamber`/`pre_dig`, so a new nest starts "
            "with the original's shape, not a circle.",
            "This is the code the default-start replay exercises, which is how the missing spider step table "
            "(`DS:1B9A`) was found.",
        ],
    ),
    "nestgrid.py": (
        "Nest grid helpers",
        "colonies",
        "Digging, dirt edges, exit fields, the nest ant lists.",
        "Shared between the surface and the nest code: is a cell diggable, is it dirt that forms an edge, "
        "reclassify dirt after a dig, update the exit field that counts up toward an opening, and add or compact a "
        "nest ant. Black nest: dirt `0x2180`, exit field `0x4180`, cells `0x8180`, ants `b_*` (count `G:0da8`). "
        "Red: `0x3180`, `0x5180`, `0x9180`, ants `r_*` (count `G:0eaa`).",
        [
            "The contents grid encodes `(caste << 3) | brood_stage`; caste 0 means the low bits are a brood stage "
            "from `STR#1100`.",
            "`compact` moves ants into a dense list; the original's iteration order after a compaction is part of "
            "the simulation's behaviour.",
            "A dig is three edits (dirt, contents, exit field) and doing two of the three leaves a nest that looks "
            "open and is not passable.",
        ],
    ),
    "nest.py": (
        "Black nest ants",
        "colonies",
        "The nest tick, state handlers, digging, brood and the queen.",
        "The black colony's per-tick loop and state handlers (overlay section 27, segment `899e`, with helpers in "
        "`0be8`, `0ec1`, `14ee`): wandering, nesting, carrying food, digging in, going to the surface, brood care, "
        "egg laying, fighting, resting, invader handling, plus the queen's movement and the abdomen/head/tail "
        "loss rules.",
        [
            "Nest ants live in the `b_*` arrays and each one's type byte is also written into the contents grid at "
            "its cell — two representations that must never disagree.",
            "The exit field counts *up* toward an opening, which inverts the intuition from the surface: a high "
            "value near the entrance is an exit being dug, not a wall.",
            "Egg cost, food storage and eating are all bookkeeping on the dirt grid, which is why a nest can starve "
            "with food on the map.",
        ],
    ),
    "red_nest.py": (
        "Red nest ants",
        "colonies",
        "A separate copy of the nest AI, with its own rules.",
        "The red colony (`f_0f3f8..f_10e27`, resident segment `1f3f`) is not the black nest with a colour flag: it "
        "is a second implementation with different rules — no Defense job inside, nurses that only shuffle brood, "
        "hatching into a caste picked from the red priority, diggers that can break through into the black nest, "
        "and different fight and invader handling.",
        [
            "Both nests are stepped in the same tick, so the order black-then-red is part of the result.",
            "Red diggers breaking through is a terrain merge between two grids that were separate until that "
            "moment.",
            "The `n_invader_*` handlers only exist here — the black nest's invader path is different code.",
        ],
    ),
    "player.py": (
        "The player (the yellow ant)",
        "interface",
        "Upkeep, actions, pathing, and the map accessors they use.",
        "The yellow ant's per-tick upkeep (`f_7bf7e`) and its actions (`f_7b7b8`), with the view-generic accessors "
        "of segment `10f7`. Position `G:047C`/`G:048A` in view `G:048C` (1 surface, 2 black nest, 3 red nest), type "
        "`G:04C2`, heading `G:0496`, health `G:0F78`. It sits in the view's occupancy grid as `0xFF`, and a queen's "
        "second cell sits behind her as `0xFE`.",
        [
            "The largest module in the port (1,478 lines) because the player can be in three different views, each "
            "with its own walkability, digging and food rules.",
            "`Hooks` is the seam the shell implements: the simulation asks for input and reports events, and never "
            "touches the screen itself.",
            "Pathing is greedy with a wall-following fallback (`wall_step`, `wall_or_greedy`), which is why the "
            "original's player ant hugs a wall instead of routing around it.",
        ],
    ),
    "commands.py": (
        "The yellow ant's menu commands",
        "interface",
        "Recruit, release, exchange, alarm, dig, start brood.",
        "The eight menu commands (`f_76cb9`, reached through `f_2f906` from the pop-up menu `f_67e93`): recruit, "
        "release, exchange, alarm, dig a hole, start brood, and the spider's chase and hunt. Target-picking modes "
        "(`pause`, the pick-a-target cursor) are held in the player effect channel, not in the simulation state.",
        [
            "A command that needs a target sets a mode and returns; the click that resolves it is a separate call, "
            "and cancelling is a third path.",
            "`_yellow_caste`/`_new_yellow` are the only places the player can change its own caste.",
            "Commands are the player's direct orders — the design rule is that these exist for the ant you embody, "
            "and for nothing else.",
        ],
    ),
    "panels.py": (
        "The behaviour and caste triangles",
        "interface",
        "Where the marker sits, and what a click means.",
        "Windows 18 and 19: the behaviour triangle (`G:049E`/`04A0`/`04A2` = forage apex, dig bottom-left, nurse "
        "bottom-right) and the caste triangle (`G:0482`/`0484`/`0486` = breeders, workers, soldiers). Each set sums "
        "to `0xFFFF`. `to_values` inverts a click position into the three weights; `to_point` places the marker.",
        [
            "The triangles are the whole indirect-control interface in the original, and the reason the game is not "
            "an RTS.",
            "Barycentric conversion is integer-only and clamped; the sum staying at `0xFFFF` is the invariant.",
            "The weights persist in the save file, so a saved game keeps its policy.",
        ],
    ),
    "markers.py": (
        "The map's event markers",
        "interface",
        "Where the last hatch, fight, egg and rest happened.",
        "The simulation reports four events — brood, fight, queen, rest — only while the patch is visible "
        "(`T:07B2`), through `st.player.effect` with `(a, b, view)`. `on_screen` decides whether the spot is "
        "visible; `record` writes the marker globals that the marker animation and the speech balloons read.",
        [
            "Reporting only while visible is the original's behaviour, not an optimisation: markers do not "
            "accumulate off-screen.",
            "The recorder latches its spot once (its gate goes non-zero) and then waits out a timer.",
            "This module is the event source `balloons.py` consumes.",
        ],
    ),
    "balloons.py": (
        "Speech balloons",
        "interface",
        "The ants' remarks, timed off the real-time clock.",
        "`f_06a4d`, reached from the window draw (`f_038a6` via `f_07128`): a balloon appears at the spot a marker "
        "recorded, and is re-armed at clock + a random delay when its timer expires. It only runs while the patch "
        "is visible (`T:07B2`) and `T:07BE` is `-1`.",
        [
            "Timing uses the engine's real-time clock, so the port needs the clock hook, not a frame counter.",
            "Each source latches its spot once and then reuses it — a balloon follows the last event, not the ant.",
            "The random delay is an LFSR draw, so balloons are part of the tick-for-tick stream.",
        ],
    ),
    "tutorial.py": (
        "The tutorial",
        "interface",
        "56 steps, each with a box and a check.",
        "Game mode 0: `f_0e425`, run by the advisor every tick before its status line. Every eighth call it either "
        "shows the current step (`f_0e4e4`: a message box with `STR# 11000 + 2*(step-1)`, some with a picture) or "
        "polls the step's completion check (`f_0e93e`) — done advances the step, and a step that polls 16 times "
        "without success gets a nudge.",
        [
            "Step 46 needs the population graphs held, which sets `G:1074`; without it the step can never advance — "
            "a bug the emulator walk caught.",
            "A message box blocks the tick in the original (`f_71b1a`), so `GameSession.Advance` ends its loop "
            "there.",
            "All 56 step boxes were checked against an emulator run of the original routine.",
        ],
    ),
    "tools.py": (
        "The map tools",
        "interface",
        "Rocks, dig, ants, food, pheromone, insecticide.",
        "`f_770f6`: what a click does with the selected tool `G:104C` in the view on screen `G:032E`. Tool options "
        "are the bytes `T:07B7..T:07BC`. Info is UI; rocks, dig, ants, food and insecticide mutate the terrain or "
        "the ant arrays; pheromone paints a map.",
        [
            "Rocks are fitted from a wall mask (`_wall_mask`, `_fit_walls`), so a rock placed over a wall joins it "
            "instead of overwriting it.",
            "Digging in a nest view reclassifies dirt and updates the exit field through `nestgrid`.",
            "Insecticide and pheromone both raise a cloud that decays on later ticks; the click is only the first "
            "edit.",
        ],
    ),
    "cheats.py": (
        "The cheat codes",
        "interface",
        "Typed keys, NOT-ed into a match buffer.",
        "`f_6a920` (overlay 10), called once per typed key through thunk `0x2f924`: typed keys are NOT-ed into "
        "`G:0B0A[T:06DE]`, and the table at `T:067E` holds 4-byte codes, also NOT-ed, terminated by a zero byte.",
        [
            "A key that leaves no code with a matching prefix clears the buffer and is not retried as the start of "
            "a new code — the original's quirk, reproduced.",
            "A full match clears the buffer and runs the cheat.",
            "The codes themselves live in the original's tables, so this module carries machinery, not codes.",
        ],
    ),
    "debug.py": (
        "The hidden debug commands",
        "interface",
        "Add ants, kill ants, clear food, and a random action.",
        "Resident segment `015b`: menu command `0x112` (`f_022bc`) runs one of fifteen actions; Ctrl-clicks on "
        "command `0x110`'s control reach the first three through `f_6f733`.",
        [
            "Screen effects leave through the effect channel: sound, music, message, message box.",
            "The random action draws from the same LFSR, so using it changes the game's future.",
            "Debug actions are still simulation edits: they go through the same add/remove paths as normal ants.",
        ],
    ),
    "game.py": (
        "Game flow, rating and game over",
        "interface",
        "Starting a game, ending one, and the score.",
        "`f_70fb0` (the rating shown when a game ends), `f_71d95` (the game-over screen, via vector `f_2f780`) and "
        "`f_725b6` (starting from the new-game dialog, via `f_2f848`). The mode is `G:0EAC`.",
        [
            "The rating is computed from integer parts (`_lmul`, `_ldiv`) because the original uses 32-bit scaled "
            "arithmetic, not floats.",
            "The game-over screen is a hook, not a state: what changes here is the mode and the counters.",
            "Tutorial, Quick Game, Full Game and experimental all enter through `start_game`.",
        ],
    ),
}

MODULE_ORDER = [
    "state.py", "rng.py", "tables.py", "sim.py", "savefile.py",
    "terrain.py", "movement.py", "pheromones.py", "surface.py", "world.py", "yard.py",
    "colony.py", "newgame.py", "nestgrid.py", "nest.py", "red_nest.py",
    "player.py", "commands.py", "panels.py", "markers.py", "balloons.py", "tutorial.py",
    "tools.py", "cheats.py", "debug.py", "game.py",
]


def slug(name: str) -> str:
    return name[:-3].replace("_", "-")


def docstring_facts(src: str):
    tree = ast.parse(src)
    doc = ast.get_docstring(tree) or ""
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    addrs = sorted(set(re.findall(r"\bf_[0-9a-f]{4,5}\b", doc + src)))
    return doc, funcs, classes, addrs


def dir_slug(path: Path) -> str:
    """The raw-download folder for a file, so two tools with the same name never collide."""
    return {"simant_ref": "simant_ref", "re": "re", "ref": "ref"}.get(path.parent.name, "tools")


def page(path: Path, title: str, subtitle: str, body: str, source: str, kind: str):
    facts, funcs, classes, addrs = docstring_facts(source)
    lines = len(source.splitlines())
    parts = [
        "---",
        "layout: default",
        f'title: "{title}"',
        f"permalink: /reference/{slug(path.name)}/",
        "---",
        "",
        f"# {title}",
        "",
        f"*`{path.name}` — {subtitle}*",
        "",
        f"[Reference index]({{{{ site.baseurl }}}}/reference/) · "
        f"[Download `{path.name}`]({{{{ site.baseurl }}}}/assets/reference/{dir_slug(path)}/{path.name})",
        "",
        body,
        "",
        "## At a glance",
        "",
        f"- **{lines}** lines",
    ]
    if classes:
        parts.append(f"- **Classes / hooks:** {', '.join('`%s`' % c for c in classes)}")
    if funcs:
        parts.append(f"- **{len(funcs)} top-level functions**, including "
                     + ", ".join("`%s`" % f for f in funcs[:8]) + (" …" if len(funcs) > 8 else ""))
    if addrs:
        parts.append("- **Original routines referenced:** " + ", ".join("`%s`" % a for a in addrs[:12])
                     + (" …" if len(addrs) > 12 else ""))
    parts += [
        "",
        "## Source",
        "",
        "{% raw %}",
        "```python",
        source.rstrip("\n"),
        "```",
        "{% endraw %}",
        "",
    ]
    return "\n".join(parts)


def build() -> dict:
    pages = {}
    if not REF.is_dir():
        sys.exit(f"missing {REF}")
    for name in MODULE_ORDER:
        f = REF / name
        if not f.exists():
            sys.exit(f"missing module {f}")
        title, group, subtitle, what, points = MODULES[name]
        body = what + "\n\n" + "\n".join(f"- {p}" for p in points)
        pages[f"docs/reference/{slug(name)}.md"] = page(f, title, subtitle, body, f.read_text(), "ref")

    # --- the RE toolchain and the asset tools: docstring-derived, one page each
    return pages


def tool_pages():
    pages = {}
    for base in (TOOLS_RE, TOOLS, TOOLS_REF):
        for f in sorted(base.glob("*.py")):
            if f.name == "gen_devlog_reference.py":
                continue  # this generator, not part of the reference
            src = f.read_text()
            doc, funcs, classes, addrs = docstring_facts(src)
            first = (doc.strip().splitlines() or [f.stem])[0]
            title = f.stem
            pages[f"docs/reference/{slug(f.name)}.md"] = page(
                f, title, first, doc.strip() or "(No docstring.)", src, "tool"
            )
    return pages


def main() -> int:
    check = "--check" in sys.argv
    pages = build()
    pages.update(tool_pages())

    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    # raw downloads: every published file, in a folder per source directory
    raw_files = {}
    for base in (REF, TOOLS_RE, TOOLS, TOOLS_REF):
        for f in sorted(base.glob("*.py")):
            if f.name == "gen_devlog_reference.py":
                continue
            raw_files[f"docs/assets/reference/{dir_slug(f)}/{f.name}"] = f.read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(REF.glob("*.py")):
            info = zipfile.ZipInfo(f"simant_ref/{f.name}", date_time=(1991, 12, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_text())
    raw_files["docs/assets/reference/simant_ref.zip"] = buf.getvalue()

    # index
    rows = []
    for gid, gname in GROUPS:
        rows.append(f"## {gname}\n")
        for name in MODULE_ORDER:
            title, group, subtitle, _what, _points = MODULES[name]
            if group != gid:
                continue
            n = len((REF / name).read_text().splitlines())
            rows.append(f"- **[`{name}`]({{{{ site.baseurl }}}}/reference/{slug(name)}/) — {title}.** "
                        f"{subtitle} *({n} lines)*")
        rows.append("")

    rows.append("## Reverse-engineering toolchain\n")
    rows.append("The tools that turn a 1991 executable into something readable and testable. They all need your own "
                "copy of the game.\n")
    for f in sorted(TOOLS_RE.glob("*.py")):
        doc, *_ = docstring_facts(f.read_text())
        first = (doc.strip().splitlines() or [""])[0]
        rows.append(f"- **[`{f.name}`]({{{{ site.baseurl }}}}/reference/{slug(f.name)}/)** — {first}")
    rows.append("")
    rows.append("## Differential tests\n")
    rows.append("Each module's test boots the original in the emulator and compares the port's output against it. "
                "These need `flat.bin` and the game; see `verify.py` for the harness they share.\n")
    for f in sorted(TOOLS_REF.glob("*.py")):
        doc, *_ = docstring_facts(f.read_text())
        first = (doc.strip().splitlines() or [""])[0]
        rows.append(f"- **[`{f.name}`]({{{{ site.baseurl }}}}/reference/{slug(f.name)}/)** — {first}")
    rows.append("")
    rows.append("## Asset tools\n")
    rows.append("Readers for the original's archives, bitmaps, tiles, fonts, layouts and saves.\n")
    for f in sorted(TOOLS.glob("*.py")):
        doc, *_ = docstring_facts(f.read_text())
        first = (doc.strip().splitlines() or [""])[0]
        rows.append(f"- **[`{f.name}`]({{{{ site.baseurl }}}}/reference/{slug(f.name)}/)** — {first}")
    rows.append("")

    head = f"""---
layout: default
title: Reference implementation
permalink: /reference/
---

# The reverse-engineered reference

`simant_ref` is a line-by-line Python translation of the *SimAnt* simulation, written against the disassembly and
verified routine by routine against the original running in emulation. Its purpose in this project is to be the
readable specification the C# remake is ported from. Its purpose here is also to be **usable by anyone**: every
module below is published in full, with the addresses it came from and the reasons it is shaped the way it is.

**Download the whole package:** [`simant_ref.zip`]({{{{ site.baseurl }}}}/assets/reference/simant_ref.zip) —
{len(list(REF.glob('*.py')))} files, {sum(len(p.read_text().splitlines()) for p in REF.glob('*.py'))} lines, MIT licence.

## What it needs from you

The reference reads the original's constant tables and starting state out of the executable at runtime. Nothing
extracted from `SIMANT.EXE` is in this repository or on this site. To run any of it:

```bash
python tools/re/build_flat.py          # from tools/re; writes build/flat.bin from YOUR SIMANT.EXE
cd tools/ref && python test_sim.py 3000
```

Then `state.State()` loads `tools/re/build/flat.bin`, and the differential tests (`test_*.py`) check a module
against the emulator's snapshots. Without the original files, the source is still readable — the docstrings carry
the flat address of every routine — but it will not boot.

## How the port is verified

1. **Emulator.** `tools/re/emu.py` runs `SIMANT.EXE` in Unicorn, plays a seeded Quick Game, and caches six
   snapshots (ticks 0, 300, 900, 1500, 2200, 3000). A ported routine is run against a snapshot beside the original
   routine and all 150,160 bytes of state are compared.
2. **Reference.** Verified rules become the cheap oracle for the rest of the port.
3. **Replay.** Every outermost reference call is recorded (arguments, clock, state before and after) and replayed
   against the C# port by reflection.

"""
    pages["docs/reference/index.md"] = head + "\n".join(rows) + "\n"

    seen = {}
    for rel in pages:
        name = rel.rsplit("/", 1)[1]
        if name in seen:
            sys.exit(f"slug collision: {rel} and {seen[name]} both render as {name}")
        seen[name] = rel

    changed, same = [], []
    for rel, text in sorted(pages.items()):
        p = ROOT / rel
        old = p.read_text() if p.exists() else None
        if old != text:
            changed.append(rel)
            if not check:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
        else:
            same.append(rel)
    for rel, data in sorted(raw_files.items()):
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_bytes() if p.exists() else None
        if old != data:
            changed.append(rel)
            if not check:
                p.write_bytes(data)
        else:
            same.append(rel)

    print(f"{len(pages)} pages, {len(raw_files)} downloads: {len(changed)} changed, {len(same)} unchanged")
    for c in changed:
        print("  ~", c)
    if check and changed:
        print("STALE: rerun tools/gen_devlog_reference.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
