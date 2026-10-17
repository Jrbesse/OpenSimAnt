# SimAnt — Reverse-Engineering Notes (SIMANT.EXE)

This is the working log of what has been recovered from the DOS executable. Addresses are **flat linear
addresses in `tools/re/build/flat.bin`** unless noted. Ghidra adds its load segment `0x1000`, so Ghidra
`seg:off` = flat `(seg-0x1000):off`.

## Tooling (`tools/re/`)

| Script | Purpose |
|---|---|
| `mz.py` | Loads `SIMANT.EXE`, parses the overlay table, builds resident memory, has a capstone disassembler helper |
| `build_flat.py` | Builds `build/flat.bin` (every overlay at a unique address, call vectors patched) and `build/SIMFLAT.EXE`, a synthetic MZ with merged relocations for Ghidra |
| `segmap.py <seg>` | Lists every function that reads or writes a far data segment, by offset (`build/segmap_<seg>.tsv`) |
| `callgraph.py` | Direct near/far call graph (`build/calls.tsv`) |
| `ghidra_scripts/SetDS.java`, `DecompileAll.java` | Headless Ghidra: preset DS, then dump pseudo-C for every function to `build/decomp/` |

Ghidra run (Ghidra 12.1.4 in `C:\Users\jrbes\tools`):

```
analyzeHeadless.bat <proj_dir> simant -import build\SIMFLAT.EXE -scriptPath ghidra_scripts ^
    -preScript SetDS.java 65b3 -postScript DecompileAll.java build\decomp
```

## Executable layout

- Compiler: **Microsoft C 6.0, large memory model** (far code, far data), built 6 Dec 1991.
- Overlay manager: third party (error strings `eov0001`…`eov0009`, "use RELOAD to increase size").
  - The resident MZ image is 0x31259 bytes. Its entry (`2cff:06f8`) is the overlay-manager stub, which
    then jumps to the C runtime at `29f4:001c`.
  - The overlay table is in the manager segment around `0x2db40`. Records are
    `{u16 load_seg; u16 ?; u16 file_para; u8 0; u8 flags; u16 mem_paras; u16 nrelocs}{ffff; u16 idx; u16 file_paras}`.
  - Each section in the file is `nrelocs × {u16 off, u16 seg}` padded to 16 bytes, then the data.
  - `flags & 1` means loaded at startup and kept: section 2 (code, at seg 0x3126) and section 29 (at seg
    0x3d57, which is **all data**: the sim state segment, the far-data segment and DGROUP).
  - Sections 3–28 are swappable code overlays sharing 4 areas (segs 0x3126, 0x35f5, 0x384c, 0x39c7).
  - **Call vectors** (130 of them, 10 bytes each, ~0x2f600): `e8 <call mgr>; ea <off> <seg>; u16 n`, where
    the target is section `n + 2` (verified: every vector lands on a function entry).
  - MSC functions start with either `push bp; mov bp,sp; mov ax,N; call _chkstk` or the frameless
    `xor ax,ax / mov ax,N; call _chkstk`. `build_flat.py` replaces each `call _chkstk` (`29f4:02cc`) with
    `sub sp,ax` so Ghidra doesn't treat it as non-returning. `funcstarts.py` detects both forms.
  - `T` = segment `0x3d57`: constant tables (direction deltas, behaviour tables, …) plus some variables.
- Data segments:
  - `DGROUP = 0x55b3` (SS=DS). It holds strings and the segment-variable tables MSC uses for far data
    (`mov es,[DS:x]`).
  - `0x50f6` is the misc far globals: string-list handles, UI state, statistics.
  - `0x3e1d` is the **simulation state** (one 64 KB segment, see below).

## Simulation state segment `0x3e1d`

| Offset | Size | Contents |
|---|---|---|
| 0x0180 | 0x2000 | `g0180`: **surface grid, 128 × 64** (x 0–127, y 0–63), terrain/contents; read for passability by the surface AI |
| 0x2180 | 0x1000 | `g2180`: black nest terrain (dirt/tunnel) grid |
| 0x3180 | 0x1000 | `g3180`: red nest terrain grid |
| 0x4180 | 0x1000 | `g4180`: black nest secondary grid |
| 0x5180 | 0x1000 | `g5180`: red nest secondary grid |
| 0x6180 | 0x1000 | `g6180`: surface occupancy grid (written as ants move) |
| 0x7180 | 0x1000 | `g7180`: (written once at setup) |
| 0x8180 | 0x1000 | Black nest **contents** grid. Cell byte = `(caste << 3) | brood_stage`; caste 0 means the low 3 bits are a `STR#1100` brood stage |
| 0x9180 | 0x1000 | Red nest contents grid (same encoding) |
| 0xa180 | 5 × 1001 | **Surface ants** (max 1000), structure-of-arrays: `+0` x, `+0x3e9` y, `+0x7d2` state, `+0xbbb` type, `+0xfa4` ? |
| 0xb50d | 5 × 501 | **Black nest ants** (max 500), same 5 fields; state at 0xb8f7 |
| 0xbed6 | 5 × 501 | **Red nest ants** (max 500); state at 0xc2c0 |
| 0xc89f…0xf09f | 6 × 0x800 | **Pheromone maps at half resolution, 64 × 32**, index `(x>>1)*32 + (y>>1)`. The surface AI reads `0xd09f`; `0xe09f`/`0xf09f` are written by the black/red nest-marker passes (`0x14966`/`0x149e9`). Cells near nest entrances are set to 0xff unless the surface tile there is 0x51. |

Full-resolution grids are indexed `x * 64 + y` (row stride 0x40); the nests are 64 × 64 and the surface is 128 × 64. Neighbor reads at ±1 and ±0x40 appear throughout.

Ant **type** byte (surface `0xad3b`): 0 = empty slot, bit 0x80 = red colony, low bits = caste.

## Surface ant tick (`0x8c8b`, real address `0894:034b`)

```
for ant = surface_count-1 downto 0:
    if type[ant] == 0: continue
    if rand256() == 0 and rand32() > colony_health[colour]:   # black: 50f6:10be, red: 50f6:01fe
        kill(ant)  (0xa961: x, y, colour)
        type[ant] = 0; expired_count++ (32-bit at 0xf30)  -> "Expired" history stat
        continue
    census[colour][state[ant]]++                   # black 0xd40[], red 0xd72[]
    switch state[ant]:                             # jump table at cs:0x470, 20 entries
```

| state | STR#1102 name | handler |
|---|---|---|
| 0 | Bored | 0x9334 |
| 1 | Nesting | 0x99c7 |
| 2 | Foraging | 0x9fe5 |
| 3 | Got Food | 0x9e65 |
| 4 | Dig In | 0x99c7 (same as Nesting) |
| 5 | Dig Out | 0x97ce |
| 6 | Defense | 0xa368 |
| 7 | Attack | 0xab2d |
| 8 | Hatching | 0x8eb2 |
| 9 | Egg Laying | 0x8f2e |
| 10 | Fighting | 0xa871 |
| 11 | Alarmed | 0x9c55 |
| 12 | Defend Nest | 0x92a1 |
| 13 | Resting | 0x9018 |
| 14 | Pre-Flight | 0x9091 |
| 15 | Take off | 0x90f3 |
| 16 | Flying | 0x91d2 |
| 17, 18 | ??? | no-op |
| 19 | Avenger | (inline) |

### Colony health (`BHealth` / `RHealth`)

`50f6:10be` (black) and `50f6:01fe` (red), range 0–100:
- set to 100 (0x64) at new game (overlay 10, `0x6a920`)
- decremented in the main step (`0x888d`), and clamped at 0
- increased when food is eaten (`0x12de1`: `health += n`, capped at 100)
- surface ants roll for death only when health < 32 (see the loop above), so starvation kills ants

### RNG (segment `0093`, flat `0x930`)

Game RNG = 16-bit Galois LFSR, state at `DS:0x8ba2`:

```
x = (x << 1) & 0xffff; if carry_out: x ^= 0x1bf5
```

| Function | Returns |
|---|---|
| `0093:013d` `Rand(n)` | `x % n` (unsigned) |
| `0093:0169`…`0250` | `x & 1, 3, 7, 15, 31, 63, 127, 255` (`Rand2` … `Rand256`) |
| `0093:0118` | `abs(crt_rand()) % n`, using the MSC runtime LCG (`s = s*214013 + 2531011; (s>>16) & 0x7fff`) |

How the seed is initialised is still to be found (look for writes to `DS:0x8ba2`).

## Simulation step (`f_0894e`, called once per game tick)

```
tick = G:0f08 + 1; if tick > 0x1000: tick = 0      # 12-bit tick counter
total_ticks (32-bit G:0c26) += 1
if T:07b2 == 1: reset per-game stats (G:f06, f2e, f10, ef6 = 0; records = -1)
if tick % 64 == 0: HealthDecay()                   # black/red health -= 1 (black skipped if G:0c18)
if tick % 32 == 0: SlowPhase((tick >> 5) & 3)      # each phase runs every 128 ticks
    phase 0: f_0ec12; then as phase 2
    phase 2: f_0c20f, sec26 f_798c8, DiffuseAlarm
    phase 1: f_0ec91, BlackNestMarkers, DecayBlackTrail, DecayBlackScent
    phase 3: f_0ed10, RedNestMarkers, DecayRedTrail, DecayRedScent
sec8 f_68513
f_0c22c, f_0b163, f_0ce63                          # surface world updates
if tick odd: f_0b6cc
ColonyAdvisor()                                    # f_13832: priorities, advisor flags
reset census_black/red; G:08dc, G:08e8 count down to 0
SurfaceAntsTick()                                  # f_08c8b
sec27 f_799e0                                      # nest ants (to confirm)
f_0f3f8
sec27 f_7bf7e
StatsFromCensus()                                  # f_08b25
sec27 f_7b7b8
f_0e2ea
if game_over (G:0376): sec16 f_71d95
```

## Pheromones (64 × 32 maps, one cell per 2×2 tiles)

| map (SIM offset) | meaning | update rule (every 128 ticks unless noted) | used by |
|---|---|---|---|
| `0xe09f` | **black nest marker** | `v -= 1` (`DecayBlackNest`); nest-entrance cells re-pinned to 0xFF (`BlackNestMarkers`) | laid by ants leaving the nest (`LayNestMarkerBlack`, strength = countdown `s_e`); climbed by food carriers to get home (`HomeDir`) |
| `0xe89f` | **black food trail** | `v < 8 ? 0 : v - v/2` (`DecayBlackTrail`) | laid by food carriers (`LayFoodTrailBlack`, strength = countdown from 200); every black surface step does `v -= 1` (`WearTrail`); climbed by foragers (`ForageDir`) |
| `0xf09f` | red nest marker | as black | |
| `0xf89f` | red food trail | as black | |
| `0xd09f` | **alarm** | diffusion every 64 ticks: `v = (v + (N+S+E+W)/4) / 2; if v <= 8: v = 0` (`DiffuseAlarm`, via scratch `0xc89f`) | any ant on alarm → state Alarmed |
| `0xd89f` | ? | written by `DropObjectRandom` and at setup only | |

All laying is `cell = max(cell, strength)`. Experimental "Drop Trails" (`ToolDropPheromone`, `T:07bb`):
0 = black nest, 1 = black trail, 2 = red nest, 3 = red trail, 4 = alarm.

`ForageDir(x, y, dir, t)` (`f_142c5`):
```
at the map border: fixed or random inward heading (x==0: y==0→3, y==63→1, else 1+Rand(3);
    y==0: x==127→5 else 3+Rand(3); x==127: y==63→7 else 5+Rand(3); y==63: (Rand(3)-1)&7)
cx, cy = x>>1, y>>1;  here = trail[cx][cy]
best, bestd = 0, Rand8()
for d in 0..7: v = trail[(cx+dx[d]) & 63][(cy+dy[d]) & 31]; if v > best: best, bestd = v, d
if best == 0: return T_WALK[dir][Rand8()]
if here > best: return -1                       # lost: on a local maximum
return T_WALK[dir][bestd]                       # quirk: indexes the walk table with bestd
```

## Other routines identified

| Address | Role |
|---|---|
| `0x7691`–`0x77c5` | Loads all `STR#` lists at startup into `50f6:xxxx` handles (1100→0x106e, 1101→0x1078, 1102→0x1086, 1103→0x1096, …) |
| overlay 7 `0x67c1c` | "Ant Info" popup: decodes nest cells and ant state/caste/carry for display |
| overlay 10 `0x6c010`, `0x6ae20` | New game: clears or initialises every grid and ant array |
| `0x10fcd` / `0x11121` | Read / write every ant array (save/load or compaction) |
| `0x0f000`–`0x11200` | Spawn and remove ants per array |
| overlay 27 `0x79a4d` … | Black nest ant AI |
| `0x103b9`–`0x10e27` | Red nest ant AI |

## Ant type byte and castes

Type byte (surface `s_type`, nest `b_type`/`r_type`, and occupancy grids): `bit7 = red`, `bits 3–6 = caste`,
`bits 0–2 = heading` (for ants) or brood stage (for caste 0 cells in the nest grids). The player
(yellow ant) appears in the occupancy grid as `0xFE`/`0xFF`; its real type is `G:04c2` and its colour `G:04e2`.

| caste | STR#1101 | census group (`f_0be82`) |
|---|---|---|
| 0 | (brood: stage in low bits) | eggs |
| 1, 2, 3, 5 | Worker (2 = plain, 3 = carrying food) | workers |
| 4 | Male | males |
| 6, 7, 9 | Soldier (6 = plain, 7 = carrying food) | soldiers |
| 8 | New Queen | new queens |
| 12 | Queen | queens |

Picking up food: `type = heading | (type & 0xF8) | 8`, i.e. caste += 1.

Headings: 0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW; `dir_dx = [0,1,1,1,0,-1,-1,-1]`,
`dir_dy = [-1,-1,0,1,1,1,0,-1]` (`T:0000`, `T:0008`; `T` = segment 0x3d57, the constant tables).

## Census and win/lose (`f_0be82`)

Counts every ant in all three arrays (plus the yellow ant) into `G:0eb6[type>>3]` (32 words).
- black: eggs `G:aec`, workers `G:aee`, soldiers `G:af0`, males `G:af2`, new queens `G:af4`, queens `G:af6`
- red: same at `G:afa…b04`
- `G:0330` = black population (workers + soldiers + males + new queens + queens), `G:0350` = red
- If the queen count drops to 0: show message 10010 (black) or 10012 (red). If the game mode is ≤ 1, the game
  ends (`G:0376 = 1`, `G:0366 = 0` lost / `1` won) with 10011 / 10013.
- Game mode `G:0eac`: 3 = Experimental (others still to be confirmed; ≤ 1 = single-patch games).

## Movement

```
NextDir(x, y, dir):                       # f_146b9
    e = EdgeDir(x, y)                     # f_148d8: at the map border returns 1+inward heading
    if e: return (e - 1) & 7              #   corners Rand(3), edges Rand(5) of the inward headings
    return T_WALK[dir][Rand8()]           # T:0024
T_WALK = [[0,1,1,1,7,7,7,7], [0,1,2,2,2,2,0,0], [1,1,2,3,3,3,3,1], [2,2,2,3,4,4,4,4],
          [3,3,3,3,4,5,5,5], [6,6,4,4,4,5,6,6], [7,7,7,5,5,5,6,7], [0,0,0,0,6,6,6,7]]
TurnAside(dir) = T_WALK[dir][Rand8()]     # f_0ab05, used when blocked
```

Surface tiles (`surface_grid`): food = `0x48–0x4B` (yard) / `0x18–0x27` (house, when `G:0f24` != 0);
nest entrance = `0x50` (yard) / `0x80–0x8F` (house); tiles `> G:0480` block movement.

## Surface state: Bored (`0x9334`)

```
S_Bored(ant):
    x, y, t = s_x, s_y, s_type;  caste = (t>>3)&15;  cc = t & 0xF8
    if AtOwnNestEntrance(x, y): EnterNest(x, y, ant); return          # f_0acfb / f_0a5ae
    nd = NextDir(x, y, t&7);  nx, ny = x+dx[nd], y+dy[nd];  tile = surface[nx][ny]
    if IsFood(tile) and caste in (2, 6):                              # worker or soldier
        s_type = occ[x][y] = nd | cc | 8;  s_state = GOT_FOOD
        TakeFoodAt(nx, ny);  s_e = 200;  return
    if not IsFood(tile) and tile > G:0480:                            # blocked
        s_type = occ[x][y] = TurnAside(t&7) | cc;  return
    o = occ[nx][ny]
    if o == 0:                                                        # move
        occ[nx][ny] = s_type = nd | cc;  occ[x][y] = 0;  s_x, s_y = nx, ny
        if s_e: s_e -= 1;  LayNestMarker{Red,Black}(nx, ny, s_e)       # ants fresh out of the nest mark it
        WearTrail(nx, ny, t & 0x80)
        if Rand8() == 0 and caste in (2, 6): s_state = FORAGING
    elif IsYellowAnt(o):                                              # bumped the player
        if enemy colour: f_2f7c6(1, ant)  (attack player)
        else: turn aside (+ f_2f7bc if G:1044 == 1)
    elif same colour: turn aside;  s_state = StateForCaste(caste, t)
    else: SurfaceEncounterEnemy(ant, x, y, nx, ny)                    # f_0a6c9
```

## Colony priorities and job choice

`StateForCaste(caste, t)` (`f_141a6`) → black `f_141cb` / red `f_14260`. For black, when automatic
(`G:0378 == 1`):
- worker (2): `T_WORKER[G:1094][Rand8()]` (`T:0b9e`), soldier (6): `T_SOLDIER[G:1094][Rand8()]` (`T:0bce`)
- other castes: `T_DEFAULT[caste]` (`T:0bfe`) = `[8,1,0,3,14,5,0,3,14,5,0,0,9,9,10,0]`
- manual (`G:0378 != 1`): workers and soldiers get `T:0c10` (=2, Foraging)

| row | T_WORKER (8 picks) | T_SOLDIER |
|---|---|---|
| 0 | Nesting, Foraging, Attack ×6 | Attack ×8 |
| 1 | DigIn, Nesting ×3, DigIn, Foraging ×3 | Nesting, Foraging ×7 |
| 2 | Resting ×3, DigIn ×3, Foraging ×2 | Foraging ×3, DigIn ×2, Foraging ×3 |
| 3 | Resting ×2, DigIn ×5, Foraging | Foraging, DigIn ×6, Foraging |
| 4 | Nesting ×3, Foraging ×5 | Foraging ×8 |
| 5 | Nesting, Foraging ×7 | Foraging ×8 |

Row `G:1094` = colony priority from `f_1395b`, recomputed in `f_13832`:

```
health = black_health
if health < 10 and pop_b/2 > pop_r > 0 and G:036c > 0: return 0      # desperate raid
if health < 30: return 5
if health < 50: return 4
if pop_b > G:0224: return 3                                         # G:0224 = nest capacity (grows by digging)
if pop_b*2 > G:0224: return 2
if pop_b > 100 and pop_r > 0 and G:036c > 0 and pop_b/3 > pop_r: return 0   # attack
return 1
```

## Getting home and entering the nest

```
HomeDir(x, y, dir, t):                                   # f_1445a, used by Got Food
    e = EdgeDir(x, y); if e: return (e-1) & 7
    nest = red ? pher_rnest : pher_bnest
    if nest[x>>1][y>>1] != 0:
        bestd = argmax over 8 neighbours (first max wins, start 0)
        r = Rand2() ? T_WALK[dir][bestd] : dir
        return T_WALK[r][bestd]
    d = DirTo(x, y, entrance_x, entrance_y)              # black T:02ac/02ae, red T:02b0/02b2
    if d and Rand4() != 0: return T_WALK[dir][d-1]
    return T_WALK[dir][Rand8()]

DirTo(x, y, tx, ty) -> 0 if same cell else 1 + heading (8-way sign of the delta)   # f_0c9a1
```

Coordinates: surface grids are `[a][b]` with `a` in 0..127 and `b` in 0..63. **`a < 64` is the black half
and `a >= 64` the red half.** Nest grids are `[col][depth]`-like 64 × 64. `T:0224[b]` / `T:0264[b]` give
the surface `a` of a black/red nest entrance in column `b` (0 = none). Nest column = surface `b`.
(Which axis is horizontal on screen is still to be confirmed from the renderer.)

```
EnterNest(a, b, ant):                                    # f_0a5ae
    colony = black if a < 64 else red
    if nest_count >= 500: compact nest arrays; if still >= 500: return   # ant stays outside
    Add{Black,Red}NestAnt(col=b, depth=1, type=(s_type & 0xF8) | 4 /*heading S*/, s_state, s_e)
    if entrance_a_by_b[b]: f_153f9 / f_15527(b, 1)
    s_type = 0; occ[a][b] = 0                            # slot freed; compacted later
```

Surface count compaction (`CompactSurface` `f_0ec12`) and nest compaction run in the slow phases.

## Surface combat

```
SurfaceEncounterEnemy(ant, a, b, na, nb):                 # f_0a6c9 - ant bumps an enemy at (na, nb)
    att = s_type[ant]; s_type[ant] = 0; occ[a][b] = 0     # attacker leaves the arrays
    d = SurfaceAntAt(na, nb); if d < 0: return
    winner = ResolveFight(s_type[d], att)
    s_type[d] = occ[na][nb] = (winner & 0x80) | 0x70      # caste 14 "Fight", coloured by the winner
    s_state[d] = FIGHTING; s_e[d] = winner                # winner's full type byte kept in s_e
    DepositAlarm(na, nb, 40)                              # alarm = max(alarm, 40)

ResolveFight(def_t, att_t):                               # f_0a774
    if T:0c14 == 1: return the black one                  # (cheat / debug)
    r = crt_rand() % 10
    if combat_odds[class(def)][class(att)] > r: winner = def else winner = att
    kills: loser black -> G:09fa++, G:0efc (32-bit)++;  loser red -> G:0a00++, G:0f3e++
    return winner

S_Fighting(ant):                                          # f_0a871
    s_type = (s_type & 0xF8) + Rand(7)                    # jitter heading (0..6; never 7 - quirk)
    if Rand16() != 0: (if T:07b2 == 1: fight effect f_06802(a, b, 1)); return
    s_type = occ = s_e                                    # the winner re-emerges
    s_state = StateForCaste(caste(s_e), s_e); s_e = 0
    PlaceCorpse(a, b, s_type & 0x80)
```

Combat class (`DS:1b72` by caste): castes 0–3, 5, 10, 11, 14, 15 → 0 (worker); 6, 7, 9 → 1 (soldier);
4, 8 → 2 (breeder); 12, 13 → 3 (queen). Defender-wins chance out of 10 (`DS:1b82[def][att]`):

| defender ↓ / attacker → | worker | soldier | breeder | queen |
|---|---|---|---|---|
| worker | 5 | 2 | 7 | 3 |
| soldier | 8 | 5 | 9 | 4 |
| breeder | 3 | 1 | 5 | 2 |
| queen | 7 | 6 | 8 | 5 |

## Corpses (`PlaceCorpse` f_0a961)

A 100-entry ring buffer (`G:037c`/`G:0404`, index `G:0476`). Placing a corpse first recycles the oldest
slot: if that tile is still a corpse (yard `0x10–0x17`), it becomes `Rand16()` (a ground tile `0x00–0x0F`).
The new corpse is placed if the tile is plain ground (`< 0x18`): black `0x10 + Rand4()`, red `0x14 + Rand4()`.
House mode uses other ranges (floor tiles 0–3 → `(floor+2)*4 + Rand(2)` black, `floor*4 + Rand(2) + 0x0a` red).
The occupancy cell is always cleared.

Yard surface tiles so far: `0x00–0x0F` ground variants, `0x10–0x17` corpses, `0x48–0x4B` food, `0x50` nest
entrance, `0x74` dropped object (`DropObjectRandom`), `> G:0480` impassable.

## Alarm, Defense (recruits) and steering helpers

```
S_Alarmed(ant):                                           # f_09c55
    if AtOwnNestEntrance: EnterNest; return
    if alarm[a>>1][b>>1] == 0 and Rand4() == 0: s_state = StateForCaste(...); return
    nd = AlarmDir(a, b, dir); move like Bored but: no trail laying, no WearTrail;
    blocked -> TurnAside; yellow enemy -> attack player; friend -> TurnAside; enemy -> SurfaceEncounterEnemy

AlarmDir(a, b, dir):                                      # f_145fc
    EdgeDir first; bestd = argmax alarm over 8 neighbours (strictly greater, start 0)
    return T_WALK[dir][bestd] if best > 0 else T_WALK[dir][Rand8()]

S_Defense(ant):                                           # f_0a368 - guards / recruits; never leaves this state itself
    if AtOwnNestEntrance: EnterNest; return
    nd = alarm here ? AlarmDir : (red ? RedGuardDir : BlackGuardDir)(a, b, dir)
    blocked -> random heading Rand8() (not TurnAside); otherwise like Alarmed

BlackGuardDir(a, b, dir):                                 # f_146fc, mode = G:048c
    EdgeDir first
    mode 1 (recruited/guard):
        if G:0248 == 1: d = DirTo(a, b, G:0f12>>4, G:0f34>>4)          # straight at the yellow ant
        elif Distance(a, b, guard_a, guard_b) > stat_black_defense/2: d = DirTo(guard point)
        else: d = 1 + Rand(8)
    mode 2: return HomeDir(a, b, dir, black)              # go home
    mode 3: return HomeDir(a, b, dir, red)                # march on the red nest
    other: return dir
    return d ? T_WALK[dir][d-1] : dir
```

`ColonyAdvisor` (`f_13832`) each tick: if mode 1, `guard = yellow position (G:047c, G:048a) + (Rand(5)-2)`
clamped to the patch, and `G:0248 = 1` when the yellow ant's pixel position (`G:0f12`, `G:0f34`, /16)
is within distance 100.

## Remaining surface states

Carrying castes: **+1 = food, +3 = dirt** (worker 2 → 3 food / 5 dirt; soldier 6 → 7 food / 9 dirt;
worker 1 is probably carrying brood). `T:0074[caste]` marks the carrying castes, `T:0094[caste]` maps them
back to the empty caste: `[0,2,2,2,4,2,6,6,8,6,10,11,12,13,14,15]`.

| state | behaviour (`T:07b2` = "this patch is on screen", gates effects only) |
|---|---|
| Got Food (3) | `HomeDir`; moves **without** checking occupancy; lays food trail from countdown `s_e` (200 at pickup); entering the nest delivers it |
| Nesting / Dig In (1/4) | `HomeDir`; picks up food on the way (workers/soldiers → Got Food, `s_e = 200`); otherwise like Bored |
| Dig Out (5) | dirt carriers wander (`T_WALK` random + `EdgeDir`); each tick 1/8: drop dirt (caste −3) and `StateForCaste`; non-carriers → `StateForCaste` at once; lays nest marker from `s_e` |
| Attack (7) | carriers drop their load first; then `HomeDir` toward the **enemy** colony (colour flipped); fights whatever it meets; entering the enemy entrance raids the enemy nest |
| Resting (13) | stays still; 1/4 per tick → Foraging |
| Defend Nest (12) | own nest marker here < 110 → act as Nesting, else `Wander` |
| Pre-Flight (14) | 50/50 `Wander` or Nesting; when flight timer (`G:08dc` black / `G:08e8` red) > 100 → Take Off |
| Take Off (15) | nest marker ≥ 100 → `Wander`, else Nesting; then, with timer t (counts down 1/tick): t == 1 or `Rand(t) == 0` → Flying |
| Flying (16) | each tick 1/32: if colony's flown count (`G:06aa` / `G:073a`) < 50 → ant leaves the patch; in the Full Game the count increments and 1/16 of departures found a new colony (black: `G:07c8++`, `f_01315`; red: `G:0850++`) |
| Egg Laying (9) | queen on the surface: castes ≥ 13 call `TryFoundNest` (`f_08fb1`); on success she leaves the surface |
| Hatching (8) | stays; disappears with 1/200 per tick |
| 17, 18 | no-op |

`Wander` (`f_0963d`) = `NextDir` random walk with the usual move/bump rules.

## Nest ant tick

Black nest: `BlackNestLoop` (`f_799e0`, section 27) → `BlackNestAntTick` (`f_79a4d`). Red nest: `RedNestLoop`
(`f_0f3f8`) → `RedNestAntTick` (`f_0f465`) in resident code (to be compared; may differ).

```
BlackNestAntTick(col, depth, t):
    if t is red (an invader): see "Invaders" below
    census_black[state]++
    if Rand256() == 0 and state != EGG_LAYING and Rand32() > black_health: die (cell = 0, expired++)
    switch state:  0 Bored → N_Wander (7a057)        1 Nesting → N_Nesting (7ab6e)
                   3 Got Food → N_GotFood (7afdc)    4 Dig In → N_DigIn (7b197)
                   6 Defense → N_Defense (7a0c2)     8 Hatching → N_Brood (7a360)
                   9 Egg Laying → N_EggLaying (7a490) 10 Fighting → N_Fighting (7a126)
                   13 Resting → N_Resting (79ec5)    14 Pre-Flight → N_Wander, then timer > 100 → Take Off
                   17 → 79f70
                   2, 5, 7, 11, 12, 15, 16 (outdoor jobs) → N_GoToSurface (7b3ac)
```

Invaders (red ant inside the black nest): fight entities (type > 0xEF) run `N_Fighting`. Otherwise the
ant inspects the black-nest cell at its position. Yellow ant there (and the player is black) →
`AttackPlayer(2, ant)`. A black ant/brood there (cell 1..0x67): brood (cell < 8) is **stolen** (invader
becomes Got Food, carrying; `G:1000++`); an adult is fought (`ResolveFight` → fight entity, state 10);
a queen also triggers `f_7a910`. Otherwise Attack-state invaders run `79d6f`, others `79e40`.

## Brood and hatching (`N_Brood` f_7a360)

Brood are ordinary nest-array entries: caste 0, state Hatching, low 3 bits = stage (`STR#1100`:
Weird Egg, New Egg, Egg, 1st/2nd/3rd Instar, Pupae, Hatching Pupae).

```
period = (black_pop <= 2) ? 32 : 128
if tick % period == 0:                         # all brood advance on the same tick
    t += 1
    if (t & 0xF) == 8:                         # finished stage 7 → hatch
        if behavior_auto == 0 and (G:04a2 >> 7) < RandLow(255):   # manual mode: insufficient care
            t = 0; G:1000++                    # brood dies
        else:
            c = next_hatch_caste (T:0c0e); t = (c << 3) | 2        # new adult facing E
            state = (c == 2) ? NESTING : StateForCaste_black(c)
    cell = t; b_type = t; b_e = 0
```
`RandLow(n) = min(Rand(n), Rand(n))` (`f_0095b`). So egg to adult takes 8 × 128 = 1024 ticks.

## Caste allocation (`ChooseHatchCaste` f_13a28, run every tick by the advisor)

Groups: 0 workers (`G:aee`), 1 soldiers (`G:af0`), 2 males (`G:af2`), 3 new queens (`G:af4`).
Target weights `caste_ratio_target[4]` (`T:07da`, set by the caste triangle; default 60/40/0/0).
```
actual%[i] = 100*count[i]/sum(count); want%[i] = 100*target[i]/sum(target)   (0 if sums are 0)
pick the i with the most negative (actual% - want%) (strictly < 0; default 0)
next_hatch_caste = [2, 6, 4, 8][i]              # worker, soldier, male, new queen
```

## Manual behaviour (`ChooseManualJob` f_13b26)

When `behavior_auto == 0`, workers and soldiers that pick a new job all get `manual_job` (`T:0c10`):
```
cur = [stat_foragers, stat_diggers, stat_nurses]          # Foraging+GotFood, DigIn+DigOut, Nesting
tot = sum(cur); want[i] = tot * behavior_weight[i] / 65535 # triangle weights G:049e (forage, dig, nurse)
pick the i with the largest (want[i] - cur[i]) > 0 (default 0)
manual_job = [FORAGING, DIG_IN, NESTING][i]
```

## Red AI priority (`RedPriority` f_13be3 → `G:10a6`)

```
if red_flight_timer == 0 and red_males + red_new_queens > 20: red_flight_timer = 200
if red_war_timer (G:0504) > 0: red_war_timer -= 1; return 0           # attacking
if red_health < 10 and red_pop/2 > black_pop > 0 and G:035e > 0: RedLaunchAttack(); return 0
if red_health < 30: return 5;  if red_health < 50: return 4
if red_pop > red_nest_capacity (G:0232): return 3;  if red_pop*2 > capacity: return 2
if red_pop > 100 and black_pop > 0 and G:035e > 0 and red_pop/3 > black_pop: RedLaunchAttack(); return 0
if Rand32() == 0 and red_pop > 20 and red_pop > black_pop and Rand128() == 0: RedLaunchAttack(); return 0
return 1
```

## The queen (two cells) and egg laying (`N_EggLaying` f_7a490)

A queen is **two nest cells**: caste 12 = head, caste 13 = abdomen, placed at `head - dir[heading]`
(the cell behind her: `dir[(t ^ 0xFC) & 7]`, i.e. heading + 4). Only caste 12 is counted as a queen.

```
caste 12 (head), each tick:
    if Rand64() == 0:
        if black_health == 0: remove head; message 10015 "black queen starves"; return
        if QueenMove(col, depth, heading): return                     # f_7a78f: moves, drags the abdomen
    if QueenHeadLost: (cell behind != t+8 and no ant there) -> remove head, black_colonies--
caste 13 (abdomen), each tick:
    if black_colonies > 0 and the head (cell in front, t-8) is gone: remove abdomen, black_colonies--; return
    spot = cell behind the abdomen; if NestCellFree(spot): egg_spot = spot (T:02b4/02b6)
        if tick % 16 == 0 and Rand128() <= black_health:
            SpawnBlackBrood(spot, 1); f_7af94(); eggs_laid++ (G:0fc2, 32-bit)
```
So a fully healthy queen lays on about 79% of 16-tick boundaries (one egg every ~20 ticks), and a starving one almost never.

## Food economy (black; red mirrors it with its own globals)

Nest grid `bnest_dirt` (`0x2180`) cell values: `< 0x10` open tunnel (variants), **`0x10–0x13` stored food
(1–4 units)**, `>= 0x30` solid dirt (impassable). `black_food` (`G:1050`) = stored units ("BFood").

```
StoreFoodBlack(col, depth):       # f_7a2ea - carrier drops food here
    v = cell; if v < 0x10: cell = 0x10 elif v < 0x13: cell += 1 else: return 0 (full)
    black_food += 1; ant loses carrying bit (type -= 8)

Eat(col, depth):                  # EatFoodBlack f_7ae88 / EatIfOnFoodBlack f_7adcf (same core)
    cell = (cell == 0x10) ? Rand8() : cell - 1;  black_food -= 1 (if > 0)
    eat_acc (G:0212) += 5
    if eat_acc > (black_pop + soldiers) >> 4: eat_acc = 0; black_health = min(100, black_health + 1)

EggCost():                        # f_7af94, after each egg (and some player action)
    eat_acc -= 1; if eat_acc < 0: eat_acc = black_pop >> 5; if black_health > 0 and !T:0c18: black_health -= 1
```

Who eats: a forager in the nest with food (N_GotFood) moves along tunnels. Each tick it drops the food
with 1/16 chance, or when stuck. Then, if `Rand(100) > black_health`, it eats one unit where it stands,
and picks a new job. Ants in Nesting / Dig In / Go-To-Surface eat whenever they step on a food cell
(`EatIfOnFoodBlack`). Red invaders eat black stores with no health gain (`InvaderEatFood`).
Health also decays by 1 every 64 ticks (`HealthDecay`).

## Nest terrain, digging and navigation

`bnest_dirt` values: `0x00–0x07` open tunnel (visual variants), `0x10–0x13` stored food, `0x18` entrance
shaft (row 0), **`0x20–0x2E` exposed dirt = `0x1F + mask`** where mask = which of up(1)/right(2)/down(4)/left(8)
are dirt (edge-tile graphics; diggable, `IsDiggable` = 0x20..0x2E), `0x30+` solid interior dirt (not
enterable, not diggable until exposed), `0x4E–0x5E` alternate material (rock?) with the same edge scheme
(base `0x2F`). Anything `>= 0x30` blocks movement.

```
DigCellBlack(col, depth):                         # f_15623
    require col in 1..62
    require depth == 63 or cell below is IsDiggable           # tunnels stay 1 cell thick,
    require depth <= 2  or cell above is IsDiggable           # so shafts run diagonally
    cell = (depth == 0) ? 0x18 (+ MakeSurfaceHoleBlack(col)) : Rand8()
    black_nest_capacity += 1; running sums → centroid (G:10b2 col, G:10c0 depth)  # queen walks toward it
    ReclassifyDirt on the 4 neighbours; UpdateExitField(col, depth)

ReclassifyDirt(col, depth):                       # f_158d1, only touches dirt cells (0x20..0x2F or >= 0x4F)
    mask = dirt-ness of up/right/down/left (out-of-range counts as dirt)
    if mask: cell = base + 0x1F + mask           # base 0 normally, 0x2F for the alternate set (> 0x4D)
    else:    cell = base ? 0x4E : Rand8()        # isolated dirt crumbles into tunnel
```

Exit field (`bnest_exitfield` `0x4180`, red `0x5180`): rows 0–1 = `0xFF` at the entrance shaft (dirt
`0x18`), else `0xFE`; other cells = `max(8 neighbours) − 1` (0 if none), updated **only incrementally**
(when a cell is dug, on 1/4 of Dig In moves, and as ants leave). `NestStepDir(col, depth, dir)` (`f_0cbe7`)
picks the neighbour (not straight back) with the **smallest nonzero** value `<=` current (ties 50/50), i.e.
it goes **deeper**. Returns −1 at a dead end.

```
N_DigIn(ant):                                     # f_7b197
    if caste not in (2, 6): state = StateForCaste
    d = NestStepDir(...); if d < 0: d = Rand8()
    turn to d; if depth == 63: state = StateForCaste; return
    target = cell + dir[d]; if target depth < 1: ExitToSurface; return
    if target dirt >= 0x30: return
    if IsDiggable(target): if DigCellBlack(target): caste += 3 (dirt); state = DIG_OUT; sound 0x11
                           else: state = StateForCaste; return
                           (after a successful dig the ant moves into the new cell, as below)
    if target holds an enemy (and not our yellow ant): NestFightAt(...); return
    move; if Rand64() > black_health: EatIfOnFoodBlack; if Rand4() == 0: UpdateExitField(new cell)
```

## Leaving the nest

```
N_GoToSurface(ant):                               # f_7b3ac, all outdoor jobs inside the nest
    d = NestClimbDir(col, depth, dir) (f_0ca8f: climbs the exit field; returns 1+dir) else TurnAside
    target = cell + dir[d]; if out of bounds: return; if target depth < 1: ExitToSurface(col); return
    if target dirt >= 0x30:                       # dead end
        exitfield[cell] -= 1
        if caste in (5, 9): caste -= 3 (drop dirt); state = DIG_IN
        if caste in (2, 6): state = DIG_IN        # becomes a digger here
        return
    if IsDiggable(target): return
    move (fight invaders as in Dig In, eat on food) ...

ExitToSurface(col):                               # f_7b661, ant at depth 0..1 trying to leave
    if bnest_dirt[col][0] == 0x18:                # entrance shaft
        if black_entrance_a_by_b[col] == 0: MakeSurfaceHoleBlack(col)
        if AddSurfaceAnt(a = black_entrance_a_by_b[col], b = col, (t & 0xF8) + Rand8(), state, s_e):
            remove from nest; return 1
        restore type; state = BORED; return 0
    else:
        exitfield[col][0] -= 1 (if > 0)
        Rand2() ? dig (col-1, 1) if diggable : dig (col+1, 1) if diggable
        NestMoveTo(col, 1, Rand8())
```
Nest column `col` == surface `b`; the surface `a` comes from the entrance table.

## Nursing (`N_Nesting` f_7ab6e)

`b_e` of a nurse: bits 0–2 = carried brood stage, bit 3 = "going up" flag. `here` = contents cell at the ant.
```
caste 1 (worker carrying brood):
    if !up: d = NestStepDir(...); if d < 0: up = 1 (b_e |= 8);  move d (else random)    # carry it deeper
    else:
        if here == 0 or here > 8:            # (own cell normally holds the ant itself; quirk: heading 0 = 8)
            caste = 2; SpawnBlackBrood(col, depth, stage); cell = ant; b_e = 8; state = StateForCaste(1)
        d = NestClimbDir(...) - 1 (0 → Rand8); move d (else random)
caste 2 (worker):
    if !up:
        if here is brood (1..7) and a brood ant is there: remove it; caste = 1; b_e = stage; return (pick up)
        Rand(100) > health ? EatIfOnFood : (1/16 → StateForCaste(2));  move heading (else random)
    else: 1/8 → b_e = 0;  d = NestClimbDir(...) - 1 (0 → Rand8); move d (else random)
other castes: Rand(100) > health → EatIfOnFood; 1/8 → StateForCaste; move heading (else random)
```
`NestMoveTo` (f_7aa3b) moves into any cell with dirt < 0x1C and **overwrites** the contents grid there
(no occupancy check); above row 1 it calls `ExitToSurface`.

## Other nest handlers

```
N_Wander (0, 14, >17):  1/32 → StateForCaste; unless NestFightAt(here): move heading, else random
                        Pre-Flight (14) then: black_flight_timer > 100 → Take Off (15)
N_GotFood (3):          d = NestStepDir; d < 0 or 1/16: StoreFood(here); Rand(100) > health → EatFood(here);
                        StateForCaste. Else turn to d and step in (dirt < 0x30; fights red ants in the way)
N_Defense (6):          player viewing the black nest (G:048c == 2): stay and fight/wander; else GoToSurface
N_Resting (13):         unless fighting: 1/20 → StateForCaste, else rest effect
N_Fighting (10):        heading jitter Rand(7); 1/16 → the winner (b_e) replaces the fight entity: a black
                        winner gets StateForCaste, a red one Attack (7); a caste-12 winner regrows its
                        abdomen (f_7a8a2 adds a caste-13 Egg Laying ant behind it)
state 17 (79f70):       on tunnel/food (dirt < 0x14): StateForCaste; else jitter and die with 1/100
NestFightAt (7a233):    cell holds the yellow ant and the player is red → AttackPlayer(2); a red ant/fight
                        (0x88..0xE7) → ResolveFight; the black ant becomes the fight entity (type
                        (winner & 0x80) + 0x70, state 10, b_e = winner)
```
Invaders (red ants in the black nest, branch of `BlackNestAntTick`): Attack-state ones (`79d6f`) wander
deeper (`Rand(3)` jitter, then `NestStepDir`) until on stored food, eat a unit (`InvaderEatFood`) and turn
Got Food carrying (state 3, type |= 8); stuck → state 1. Others (`79e40`) climb the exit field towards the
entrance (any direction) and leave like black ants do.

`ExitToSurface`: on success the ant appears on the surface via `AddSurfaceAnt` (f_0f047): the first of the
8 neighbours of the entrance that is in the patch with surface tile < 0x50; the occupancy grid is **not**
written. `s_e` = carried value for Defense, else 0 — or 0x78 (nest marker countdown) for ants coming out of
their own colony's half, unless Got Food / Attack. With no free neighbour the ant stays (state Bored).
`MakeSurfaceHoleBlack` (f_150b0): tries 34 surface rows `a = (Rand(31)+i) % 32 + 2` in that column for an
open 3×3 (yard: tile 0x50 + entrance ring from DS:1BB2; house: `f_151f7` floor → entrance tile), records
the entrance (T:02AC/02AE, T:02A4), sets `T:0224[col] = a` and digs (col, 1).

## The red nest (`RedNestLoop` f_0f3f8 → `RedNestAntTick` f_0f465, resident segment 1f3f)

A separate copy of the black nest code (`simant_ref/red_nest.py`) using the red globals: `red_health`
G:01FE, `red_food` G:1060, eat accumulator G:0226 (limit `(G:0AFE + red_pop G:0350) >> 4`), centroid
G:0200/020E, colonies G:036C, egg spot T:02B8/02BA, entrance table T:0264 (rows `0x7E - (Rand(31)+i) % 32`,
entrance T:02B0/02B2, T:02A8). Shared helpers (`NestStepDir`/`NestClimbDir` on the red exit field 0x5180,
digging, food, leaving, `QueenMove`'s path step `f_7a69d` with view 3) behave identically. Differences:

```
dispatch:      no Defense job inside: state 6 goes out like the other outdoor jobs
random death:  Rand256() == 0 and state != 9 and Rand32() > red_health  (G:0FBC counts it)
NestFightAt:   (f_0fce6) fights black adults 0x08..0x67 (not black brood); the black-side yellow ant
               (player colour 0) is attacked with AttackPlayer(3)
Nesting:       caste 1 (carrier): 1/4 and standing on open tunnel (dirt < 0x10): put the brood down as a
               fresh stage-2 egg (0x82), become a worker, StateForCaste. Else 3/4 NestStepDir, else random.
               caste 2: 1/4: on brood → pick it up (no stage kept); else Rand(100) > health ? eat : new job.
               Then 3/4 keep heading, 1/4 random. Other castes: StateForCaste (every tick) and move.
Got Food:      as black, but no eating on the way
Dig In:        a failed dig → Bored (0); eats at the cell it left; sound 0x12. Stepping onto a 0x14 cell
               (where a deep black dig broke through) moves it into the BLACK nest arrays as a Got Food
               invader (type 0x90/0xB0 + Rand8 for worker/soldier)
Go To Surface: as black; eats at the cell it left; the dead-end counter does not wrap below 0
Brood:         period 32 only when red_pop == 1; never die of neglect; hatch caste =
               T:0B36[(red_priority % 7) * 8 + Rand8()], type caste*8 + 0x82, StateForCaste_red
Egg Laying:    as black (abdomen type 0xE8+dir), eggs are 0x81; no eggs-laid counter;
               EggCost_red (f_1082c) is not gated by T:0C18
Fighting:      winner black → Attack (7); winner red → job DS:1BA2[caste]
Resting etc.:  effects whenever T:07B2 != 0 (black: == 1 for rest/fight)
```
Black invaders in the red nest: type < 8 → removed; fight entities (> 0x6F) fight; on a red cell
(0x81..0xE7) with a matching ant: queen cells (> 0xDF) are removed first, brood (< 0x88) stolen (no
counter), else `ResolveFight`. Otherwise: Defense (6) while the player views the red nest (G:048C == 3) →
`f_0f871` (raid, keeps trying); Attack (7) → `f_0f7a0` (raid; stuck → Nesting); others climb out (`f_0f959`).

---

# Status and TODO

Decoded: executable/overlay format, sim state layout, RNG, SimStep schedule, all surface ant states,
movement/pheromones, combat, corpses, census, win/lose, colony priorities (black/red), caste allocation,
manual behaviour, brood development, queen + egg laying, food economy, nest terrain/digging/exit field,
leaving/entering the nest.

Still to do:
1. (done: black and red nests ported and verified in `simant_ref/nest.py` / `red_nest.py`.)
2. (done: red nest compared, see "The red nest".)
3. Surface world per tick: `f_0c22c`, `f_0b163`, `f_0ce63`, `f_0b6cc`, `f_0e2ea`, sec8 `f_68513`,
   sec26 `f_798c8`, `f_0c20f`: food spawning, predators (spider, ant lion), humans/mower/rain/insecticide.
   Ported and verified in `simant_ref/world.py` (`test_world.py`): slow phases, history graph (`f_798c8`),
   advisor (`f_0e2ea`, status line as an effect), weather (`f_0c22c`: puddles on the 100 rain objects
   G:0256 a / G:02C0 b, flooding nest rows from below as the water level G:0242 sinks, ants on a flooded
   row go to state 17), ant lions (`f_0b163`, count T:0C4A, arrays G:0A92..0ADE), the caterpillar
   (`f_0b6cc`: enters from an edge, 6 cells long, one cell per 5 odd ticks, swarmed by > 5 ants it turns
   into food 0x4B) and three wandering bugs (`f_0ae4c`, G:0EAE..0F28).
   Also ported and verified: the **spider** (`f_0ce63` + helpers, `world.spider`, 37 scenarios; see the
   comment block in world.py: 1/16-tile position G:0F12/0F34, states G:0FB8 0..5, prey G:0FFC, modes
   G:06AC 7/8, beaten when > 8 of the 3x3 around it are occupied, drops food when it finally leaves).
   With G:0A06 == 1 the player is the spider (ported, partly covered).
   Still to do:
   - SimStep's overlay calls are vector thunks: `f_2f7a8` → sec8 `f_68513`, `f_2f79e` → `BlackNestLoop`,
     `f_2f794` → `f_7bf7e`, `f_2f78a` → `f_7b7b8`, `f_2f780` → `f_71d95`; SimStep ends with `T?:02C2 = 1`.
   - (done: sec8 `f_68513`, the yard layer, ported in `simant_ref/yard.py`, verified by `test_yard.py`
     over 114 scenarios; see "The yard layer" below.)
   - `f_7bf7e` / `f_7b7b8` the yellow ant (player) per tick: health `f_12d43`, queen egg laying, movement
     towards the cursor `f_7d24f`, trail laying, entering/leaving nests.

## The real-time clock

`f_1bc34` returns the 32-bit counter at 1b73:0012 (bumped by the game's INT 8 handler, ~18.2/s);
`f_0123e` returns it x3. The sim uses it only for ambient timers (bird, dog barks, sound/message
timeouts). In the port it is `State.clock` (an input set by the engine; `read_clock()`, `clock3()`).
The emulator normally advances it on every read (needed during boot); `Verifier` freezes it after boot
(`emu.clock_frozen`) and copies its value into `State.clock`, so original and port read the same value.

## The yard layer (sec8 `f_68513`, segment 783a; ported: `simant_ref/yard.py`)

Ported and verified (`test_yard.py`, 114 scenarios). Details found while porting, beyond the summary below:
- The scripted walk (states < 0x1E and 20/21) only crosses yard columns 0..2 (by the house); the
  sound for new state 7 and 0x10 can never fire (no transition table leads there from a state < 0x1E).
- The human's sounds f_00ed8(0x18) (walk frames), 0x23 (foot_stamp), 9 (after a walk stamp), the bird's
  7 / 0xD / 0xE and the dog's barks (p 0..3 → 0x17, 0x15, 0x17, 0x16) are screen-only, but their gates
  (T:07C8 == 0 and G:035C < 2) decide whether `Rand2` / `Rand64` / `Rand(30)` are drawn. T:07C8 is 2 in
  the verifier's snapshots, so tests force it to 0.
- Mowing another patch takes a quarter (v - v>>2), which never reaches 0, so G:0A9E/G:0AC8 are never
  counted there. `f_6a6b4` reads its neighbour offsets as unsigned bytes: only (+1, 0), (0, +1) and the
  patch itself (twice) count.
- Clock comparisons (bird G:0220, bark G:0736, crossing G:383A vs G:107E) are signed 32-bit.
- f_2f7d0(5/6/9) (the foot / mower hits the player) and f_2f91a (Full Game won: end screen) are player
  hooks (`yard_event`, `win_screen`), not ported yet.

Runs every tick from SimStep. Globals: G:07C2 yard tick (0..0x3FF), the player's patch G:07CA (col 0..11)
/ G:07CC (row 0..15); per-patch colony strengths T:00A4[col*16+row] (black) and T:0164[...] (red),
0..0xFA. All DS tables below are read with ds (= ss). Segments as given; when the decompile and the asm
disagree, the asm wins.

```
f_68513:  G:07C2 += 1, wraps at 0x400 to 0
          if T:0C48 < 0x26: human_walk (f_68e30) else human_roam (f_68659)
          bird_crossing (f_6959f); bird (f_6986c); if T:0C44 == 0: dog (f_69ba3)
          rain_control (f_685ac); yard_colonies (f_6a1f4)

f_6856a(n) "human sound/message": if n <= 0x16: G:109C(32) = clock3() + 300; G:10B0 = 1; G:10BC = n

human_walk (f_68e30), the scripted human walking through (state T:0C48, timer T:0C46):
  if T:0C44 == 1: return
  if c48 < 0x1E:
      T:0C46 += 1; if s8 DS:245E[c48] < c46: c46 = 0; c48 = DS:[(2612, 2628, 263E)[Rand(3)] + c48]
          sound by new c48: 0x21 → f_6856a(0x14), 6 → 0x15, 7 → 0x16, 0xE → Rand(3)+0xF, 0x10 → Rand(2)+0x12
  frame (si, x, y) by c48 (jump table at flat 0x68F39; all unsigned bytes [c46 + base]):
      0: 2474/2478/247C   1: 2480/2484/2488   2: 248C/24A0/24B4   3: 24C8/24DC/24F0
      4: 2504/2508/250C   5: 2510/2514/2518   6: 251C/2528/2534   7: 2540/254C/2558
      8: 2564/256A/2570   9: 2576/257C/2582  10: 2588/258C/2590  11: 2594/2598/259C
     12: 25A0/25A6/25AC  13: 25B2/25B8/25BE  14: 25C4/25C8/25CC  15: 25D0/25D4/25D8
     20: si = word 25DC[c46*2], x 25EC, y 25F4      21: si = word 25FC[c46*2], x 2606, y 260C
     16..19, 22..29: uninitialised locals (unreachable from the tables: raise)
     0x1E..0x26: d = c48-0x1E; si = word 2654[d*2], x 2666[d], y 2670[d];
                 if Rand(DS:267A[d]) == 0: c48 = DS:2684[d]; c46 = 0     (entries 6, 7 are Rand(0): unreachable)
  T:0C28 = 0; if c48 == 0x26: T:0C30 = 1, T:0C28 = 1
  if c48 == 0x14 and c46 > 2: T:0C28 = 1;  if c48 == 0x15 and c46 < 3: T:0C28 = 1
  T:0C2C = x; T:0C2E = y; T:0C32 = si
  v = c2e + c2c - 0xC8; G:0246 = v / 28 (C division); T:0C3E = 0; T:0C42 = (T:0C42 == 0)
  G:023E = (c2e - 0x26) / 10
  foot lands on the player's patch iff G:023E == G:07CC and G:07CA == G:0246 and col*16+row not in
  (0, 1, 0x10, 0x20) — then:
      T:0C30 = DS:268E[c32] if 0 <= c32 < 12 else 2;  T:0C3E = 1
      G:046A = (c2e - 0x26) % 10 (C remainder) → r10;  G:03E0 = ((v % 28) * 4 + 6) & 0x7F
      G:046A = ((r10 + 1) * 6) & 0x3F
      if T:0C30 & 1: G:046A += T:0C42 ? 6 : -6   else: G:03E0 += T:0C42 ? 6 : -6
      foot_stamp(G:03E0, G:046A)
      repeat (s16(G:0330) + s16(G:0350)) << 3 times (re-evaluated each pass):
          a = Rand128(); b = Rand64()
          if occ(a, b): G:0F18 = SurfaceAntAt(a, b); if >= 0: PlaceCorpse(a, b, s_type & 0x80);
                        s_type = 0; occ = 0
          if spider at (a, b) (G:0F12 >> 4, G:0F34 >> 4): spider beaten (f_0db90)
      if G:0EAC == 2 and G:048C == 1 and Rand4() == 0: f_2f7d0(9)   (player event)

foot_stamp (f_69f53, x, y): w, h = (6, 16) if T:0C30 & 1 == 0 else (16, 6)
  every occupied cell (0 <= a < 0x80, 0 <= b < 0x80 — sic) in [x, x+w) x [y, y+h): yellow ant →
  f_2f7d0(5); else the ant there dies (PlaceCorpse(a, b, red), s_type = 0)
  if G:0F42 in [x, x+w) and G:0F7E in [y, y+h): f_0db90; and if G:0A06 == 1: f_2f7d0(5)

human_roam (f_68659), the human/lawnmower wandering the yard (T:0C28 mode 1..5, G:0202 mowing):
  if T:0C3E != 0 and G:07C2 & 3: return
  if G:0202: if (G:0246, G:023E) != (G:0488, G:0492): T:0C30 = f_68d07(G:0246, G:023E)
  else: T:0C34 -= 1; if < 0: T:0C30 = (Rand(3) + T:0C30 - 1) & 3; T:0C34 = 4
  mode 1: Rand(900)==0 → f_6856a(1), mode 2
          else if Rand(600) == 0 or G:0EAC in (0, 3): f_6856a(2), mode 5
          else: Rand(200)==0 → f_6856a(Rand(8)+7); if G:0352 (rain): mode 5
  mode 2: G:023E < 12 → T:0C30 = 2; > 12 → 0; else G:0246 > 3 → 3;
          else mode 3, G:0488 = 3, G:0492 = 13, G:0202 = 1, f_68dff, T:0C30 = 2, T:0C2C = 0x7D, T:0C2E = 0xAA
  mode 3: Rand(100)==0 → f_6856a(Rand(3)+3); Rand(200)==0 → f_6856a(6), mode 4
          G:0488 = G:0246; G:0492 = G:023E; G:0202 = 1
  mode 4: like mode 2's steering, but at the target: mode 5, G:0202 = 0; then G:0488/0492 = G:0246/023E
  mode 5: G:023E < 5 → T:0C30 = 2; > 5 → 0; else G:0246 > 3 → 3; else mode 1
  then: T:0C32 = s8 DS:269E[c30] + s8 DS:269A[G:07C2 & 3]
        mowing: T:0C32 += 100; move: T:0C2C += s8 T:0C36[c30]; T:0C2E += s8 T:0C3A[c30]
        else if T:0C40 == 0: (Rand32() == 0 → T:0C40 = 20); move as above
        else: T:0C40 -= 1; T:0C32 = c30 + 20 (standing)
  v = c2e + c2c - 0xC8; G:0246 = clamp(v / 28, 0, 11); G:023E = clamp((c2e - 0x26) / 10, 0, 15)
  not mowing: G:023E < 1 → c30 = 2, > 14 → 0; then G:0246 > 10 → 3; elif G:023E < 5: G:0246 < 4 → 1;
              else G:0246 < 3 → c30 = 0 and, if G:023E < 6: mode 3 ? c30 = 1 : T:0C48 = 0x15
  T:0C3E = 0; T:0C42 = (T:0C42 == 0)
  on the player's patch: T:0C3E = 1; G:046A/G:03E0 as in human_walk; G:0470 = G:03E0 + s16 DS:26A2[c30&3];
      G:047A = G:046A + s16 DS:26AA[c30&3]; ±6 nudge as in human_walk; foot_stamp; mowing → f_6a08a
  elsewhere, mowing: patch strengths T:00A4/T:0164[col*16+row] lose a quarter (v - v>>2);
      reaching 0 counts G:0A9E (black) / G:0AC8 (red)
  f_68d07(col, row): for d = 3..0: (col + s8 DS:26B2[d], row + s8 DS:26B6[d]) in the 12x16 yard and its
      bit is set in the mowing mask (word G:0334[col] bit row, cleared on use, f_68d97) → d;
      else col >= 11 → 0, row >= 15 → 1, row < 1 → f_6856a(6), mode 4, 2; else G:07C2 & 3
  f_68dff: G:0334..0338 = 0, G:033A..0349 (cols 3..11) = 0xFFFF
  f_6a08a (mower over the player's patch): if G:0EAC: each live surface ant dies with 3/4
      (occ = 0, s_type = 0, no corpse); spider present and Rand4() → f_0db90;
      G:0A06 < 2 and G:048C == 1 and Rand4() → f_2f7d0(6)

bird_crossing (f_6959f), state G:10A0 (0 idle, 1 diving, 2 leaving), x G:10AC (0..0x1FF), y G:10BA:
  idle: when G:383A(32) > G:107E(32): G:107E = G:383A + 20; if G:07CA >= 5 and Rand2() == 0 and
        (G:06AA > 0 or G:073A > 0) (flying black / red queens): target G:0208 = col*28 - row*10 + 0xB2,
        G:0210 = row*10 + 0x2E; state 1; x = 0; y = Rand64() + 4; G:108C = 0
  else: x += 16 (state 1) or 8; state 1: y steps towards G:0210 by 4 (|d| >= 4) or 1; else y -= 8
        G:108C = (G:108C + 1) & 1
        off the map (x < 0 or > 0x1FF or y < 0 or > 0xFF): state 0, G:107E = G:383A + 30
        state 1 at the target (x >= G:0208, |y - G:0210| <= 4): each of G:06AA, G:07C8 (+ f_01315 no-op),
            G:073A, G:0850 loses (v + 7) >> 3 if > 0; if T:07C8 == 0 and G:035C < 2: Rand2() (sound);
            state 2

bird (f_6986c), state G:0254, x G:02BE, y G:032C, heading G:0240, frame G:0244, timer G:022C:
  0: if clock3() > G:0220(32): G:0220 = clock3() + 200; if Rand16() == 0 or G:0B20 == 0x8D:
        state 1, x 0xFC, y 0x19, heading 2, frame 0, timer 0
  else G:022C = (G:022C + 1) & 0xFFF, then
  1 (flying): nx = s8 T:[heading]*4 + x; if Rand16() == 0 or nx < 0xFC or nx > 0x1EF:
        heading 2 → 6, frame 4; else heading 2, frame 1
      else x = nx; y += s8 T:[8+heading]*4; frame += 1; frame wraps: heading != 2: >= 6 → 4; == 2: >= 3 → 1
      then if T:07C8 == 0 and G:035C < 2 and Rand64() == 0: sound 0xD, done
      else: if Rand16() == 0 and G:022C > 100 and G:0506 == 2 (dog) and T:0C28 == 0:
                state 2, timer 0, frame 10; done
            if timer >= 0x33 and Distance(x, y, G:04BE, G:04C6) <= 0x960 (32-bit): state 3, frame 20
                (sound 0xE if T:07C8 == 0 and G:035C < 2)
  2: frame += 1 (max 11 → kept at 11 once > 12); timer += 1; at 0x1F: timer 0, state 1, frame 0/3
  3+: frame += 1; at 0x1E: frame 0, state 0, G:0220 = clock3() + 600

dog (f_69ba3), heading G:0506 (0..3 walking, 4/5 sitting), x G:04BE, y G:04C6, sprite G:04E4,
  patch G:0510 (col) / G:059E (row), turn timer G:0624:
  G:0624 -= 1; if < 0: heading = G:0254 ? f_69e5f() : (T:0C48 < 0x26 ? (Rand(3) + heading - 1) & 3
                                                                    : f_69daf()); G:0624 = 4
  heading 1 and Rand(10) == 0: heading = Rand2() + 4, G:0624 = 6
  sprite = s8 DS:2458[heading] + (heading > 3 ? G:07C2 & 1 : s8 DS:2454[G:07C2 & 3])
  y += s8 DS:244E[heading]; G:059E = clamp((y - 0x26) / 10, 0, 15)
  x += s8 DS:2448[heading]; G:0510 = clamp((x + y - 0xC8) / 28, 0, 11)
  G:059E < 1 → heading 2, > 14 → 0; G:0510 > 10 → 3, < 4 → 1
  sprite in 100..103 and Rand(6) == 0: bark (f_69ea8(Rand4(), 5))
  f_69e5f: G:0510 < 5 → 1; < 9 → (G:059E < 1 ? G:07C2 & 3 : 0); else 3
  f_69daf: chase the human: dr = G:059E - G:023E, dc = G:0510 - G:0246; same patch and G:0202 →
      bark(1, 0x7F); if |dc| > 1 or |dr| > 1: dr < 0 → 2, dr > 1 → 0, dc < 0 → 1, dc > 1 → 3;
      else G:07C2 & 3
  f_69ea8 bark (p, vol): only if T:07C8 == 0, G:035C < 2 and clock3() > G:0736(32);
      G:0736 = clock3() + Rand(30) + 60

rain_control (f_685ac), yard only (G:0F24 != 1):
  not raining: if G:0B20 == 0xA8 or (crt_rand() % 32 == 0 and crt_rand() % 128 == 0):
      G:0352 = 1; G:0356 = Rand(150) + 150; DropObjectRandom(0..99) (f_0c4ba); f_6856a(0)
  raining: G:0356 -= 1 if > 0; when < 1: G:0352 = 0

yard_colonies (f_6a1f4), every 32 yard ticks (G:07C2 & 0x1F == 0):
  T:0C20 = 1; f_6a13d: G:06AA (and G:073A) decay: v < 4 ? v - 1 : v - v>>2 (if > 0), at least G:07C8
      (resp. G:0850), at most 50
  G:03E2 = G:0400 = G:0478 = 0; G:03E2 = 1 if black_pop > 0; G:0400 = 1 if red_pop > 0
  this patch: T:00A4 = min(black_pop & 0x3FF, 0xFA); T:0164 = min(red_pop & 0x3FF, 0xFA)
  every other patch with any colony: G:0EAC == 2 and (col < 2 or (col == 3 and row < 5)) → G:0478 += 1
      adj = f_6a6b4 (+3 per black, -3 per red among 6 neighbours at DS:26BA/26C0 offsets, unsigned bytes)
      black: G:03E2 += 1; v += adj or 1; v <= 0 → 0, G:0A9E += 1; v >= 0xFA → 0xFA and 1/10 f_6a721(…, 0)
      red:   G:0400 += 1; v -= adj (or += 1); v <= 0 → 0, G:0AC8 += 1, and in col 11: row := 8,
             T:0184[Rand(6)*16] = 0x14; v >= 0xFA → 0xFA and 1/10 f_6a721(…, 1)
  if T:02C0 == 1: G:105C += 1; when > Rand8() + 10: G:105C = 0; while G:07C8 > 0: f_6a721(player patch, 0), G:07C8 -= 1
  G:1066 += 1; when > Rand8() + 10: G:1066 = 0; while G:0850 > 0: f_6a721(player patch, 1), G:0850 -= 1
  Full Game only (G:0EAC == 2): messages 0x2744/0x2747 when the reds vanish; G:0364 = G:03E2,
      G:036E = G:0400; the human arrives (T:0C44 = 1, T:0C48 = 0, T:0C28 = 0, T:0C32 = -1) when
      G:0478 > 24; win (G:0376 = G:0366 = 1, f_2f91a) when the human is there and no reds remain;
      lose (G:0376 = 1, G:0366 = 0, message 0x2748) when <= 1 black patch and no queen/brood/males/queens.
  f_6a721(col, row, red): new colony at (col + f_00984(4), row + f_00984(4)) clamped; if it moved:
      cell += 1 (an empty cell also counts G:0A90 black / G:0AC4 red)
  f_00984(n): m = min(Rand(n), Rand(n)); Rand2() ? -m : m
```
4. Yellow (player) ant: in progress, see "The player (yellow ant)" below.
5. New game / map generation (overlay 10 `6ae20`, `6c010`), initial colonies, entrance tables.
6. Full Game: the yard of patches, house, transfers, mating-flight colonisation (`f_01315`).
7. Scoring/ratings, history graph sampling, timers (`G:0c26` total ticks), game speed.
8. Rendering: tile and sprite mapping for surface/nest views (find the draw routines), map windows, UI.
9. Save-file format (`.ANT`).

## The player (yellow ant): sec27 `f_7bf7e` and `f_7b7b8` (port in progress: `simant_ref/player.py`)

State: position G:047C (a) / G:048A (b) in view G:048C (1 surface, 2 black nest, 3 red nest), type
G:04C2, colour G:04E2 (0 black), heading G:0496, health G:0F78 (0..100), G:1006 ticks at zero health. On
the map it is 0xFF in the view's occupancy grid (surface 0x6180, nest cells 0x8180 / 0x9180); a queen's
second cell, behind her, is 0xFE. G:0A06 != 0: the player is not an ant (1 = the spider).
Action state: G:0AA0 action pending, G:0A8E mode (0 walk, 1 act on the target cell, 2 dig, 3 attack the
target ant, 4 recruit/talk to it), cursor target G:0AF8 (view) / G:0AD6 / G:0AE8, target ant G:08DA (view)
/ G:07C0 (index) with its type remembered in G:084E, last cell G:0AB6 / G:0AC6, step counter G:0C3E.
In the verifier's snapshots the yellow ant idles in the black nest at (34, 9) with G:0AA0 = 0.

```
f_7bf7e (each tick, G:0A06 == 0), ported and verified (`yellow_tick`):
  f_119b4(view, a, b, type, heading, 0xFF)       # re-assert the yellow ant on the map (digs dirt it is in)
  every 64 ticks: health -= 1 (f_12d43); in a nest on a tile >= 0x4E (flooded): health -= 1
  queen (type 0x60) in a nest, every 16 ticks: egg 2 cells behind her if NestCellFree and Rand128() <= health
      (black: SpawnBlackBrood + EggCost, red: SpawnRedBrood + f_1082c); health -= 5
  health <= 0: G:1006 += 1; at 100: f_2f7d0(7 drowned / 8 died)
f_12d43(hp): G:0F78 = T:0C16 ? 100 : hp, clamped 0..100; > 0 clears G:1006; G:1044 = low-health warning

f_7b7b8 (each tick, if G:0AA0), decoded, not yet ported:
  res = 0
  if mode >= 3: (a, b, t, x, y) = ant G:07C0 of view G:08DA (f_10fcd); gone or (t ^ G:084E) & 0xF0 → res -2
      same view and |da| <= 1 and |db| <= 1: face it (DirTo - 1 → G:0496); res -1
      else the cursor follows it: G:08E2 = G:0AD6 = a, G:09F0 = G:0AE8 = b
  if mode == 1 and G:0AF8 == view: c = the cell next to the yellow ant towards the target (T:0010/T:001A
      offsets of DirTo, clamped to the yellow ant's own a / b if outside); if it is the target:
      r = f_13644(view, c) (act on the cell); r 1 → res -1, r other non-zero → res -2
  d = f_7d24f(view, a, b, G:0AF8, G:0AD6, G:0AE8) (step towards the cursor); d < 0 → res d
  else: G:0AB6/0AC6 = position; f_11a3e (move); G:0C3E += 1
        surface: carrying food (G:04C4 > 0, type 0x18 or 0x38) lays the colony's food trail at strength
            G:04C4 (then G:04C4 -= 1 while > 10); G:104E → alarm += 50 (f_14cad)
        nest: UpdateExitField(Red)
        odd G:0C3E: health -= 1 (a black queen 0x40 also costs black health unless T:0C24 / T:0C18)
        surface on an entrance (f_0acfb), cursor in a nest or here: f_7c7e5 (enter the nest)
        nest row 0: f_7c8fe (climb out)
        nest, target tile 0x14 (hole into the other nest) here, not a queen: switch nests (view 2 <-> 3)
  res == 0 and at the cursor in mode 0 → res -1
  res -2: sound, f_01c52; res != 0: mode 3 → AttackPlayer(G:08DA, G:07C0) with G:1058 = 1;
          mode 4 → turn the target ant to face the yellow ant (f_11121 / f_1156e), MenuCommand12de1(1)
  res != 0: f_2f820 → f_757dd (action done: cursor = position, G:0A8E = G:0AA0 = G:0B1E = G:0C38 =
          G:0C3E = 0, G:0D6C = -2); in the house on tile 0x76 / 0x78: f_2f7d0(10)
```

Pathfinding (`f_7d24f`, ported and verified by walking the yellow ant step by step): in another view the
goal becomes the nest entrance on the surface (T:02AC black / T:02B0 red) or this nest's exit (T:02A4 /
T:02A8). `f_7cd31` greedy step: the last closer free open-ground neighbour, else the last closer other one
(-2 if none, -1 at the goal); distances are the low word of `Distance`, signed. Blocked (-2 twice) →
wall following `f_7ce36` for 16 steps (G:0D6C), side G:0EFA (1 cw, -1 ccw), heading G:0EF8, never back to
the last cell; it returns to greedy when a step does not get further. `f_7d03a` looks 64 greedy steps
ahead to decide. `IsWalkable` f_1323e: surface tile <= 0x53 (house <= 0x90); nest tunnels <= 0x18 and
0x30/0x31, dirt (0x20..0x2E, 0x1C..0x1F) only in dig mode 2; the top two nest rows only towards an exit
the target is at.

Port plan, bottom-up, each layer verified on its own (`test_player.py`):
- A accessors (done): GetOccupant, f_118c4, f_11918, f_11a3e, f_119b4, f_1156e, f_10fcd, f_11121, f_11246,
  f_114bd, f_0f167, f_116a1, f_116d6, f_1167b, f_116f7, f_13791, f_133cc, f_133f9, f_1162f, f_0cd37.
- B pathfinding (done): f_7cd31, f_7ce36, f_7d03a, f_7d0e5, f_7d15d, f_7d1bd, f_7d24f, IsWalkable,
  IsOpenGround.
- C acting on a cell (done): `f_13644` act_on_cell; drops f_1317c → f_12820 brood (becomes a nest ant again,
  state 8, type T:0C22), f_12306 food (onto a crumb, up to 3 more, else a new one), f_12606 pebble (f_1252c:
  on an entrance it also seals the nest cell below with 0x31, and vice versa); pick-ups f_131ea → f_12f4f
  brood (a weak yellow ant eats it: T:0C26 = 3), f_12a1e pebble (one blocking an entrance reopens it),
  f_1302f food (surface: food trail 200 on the *black* map, G:0B1E / G:0C38 distance home; low health
  G:1044: eat it, T:0C26 = 0); MenuCommand12de1(n) eat: health back to 100, n 0 / 3 give the colony
  old health / (black pop - 1), n 2 costs 10; f_14ee2 / f_14f59 a new queen (0x40, or T:0798) founds a
  nest on open ground (then f_2f834 = f_7c7e5 enters it). Drops and pick-ups read the BIOS keyboard
  flags at 0000:0417: Shift + Alt keeps the load (a cheat; `State.bios_kbd`).
- D (done): f_7c7e5 enter a nest (left half of the patch → black, right → red; top of nest column = the
  surface b; a queen one row deeper; alarm-trail mode off via f_76a37), f_7c8fe climb out (opens an
  entrance if the column has none; a free cell next to it, 2 away for a queen, facing the cursor),
  AttackPlayer f_7c5ab (ResolveFight(yellow, ant); winner keeps the cell; the loser's corpse on the
  surface; the yellow ant losing → f_2f7d0(0)), f_7c149 mode 0 the fight animation (6 frames of a 0x70
  fight cloud with random headings: Rand2 + Rand8 each; it busy-waits on the clock, so the verifier
  unfreezes the clock for these checks), f_757dd stop_action. f_15e2c is the status line (screen only),
  f_14cad alarm += n (max 200).
- E f_7b7b8 itself.
UI pieces to stub in the emulator (they write G screen state): f_01aa7 (scroll the view to the yellow
ant, from f_01c52, which also sets G:1074 = 1), f_03381 (redraw, from f_03391 / f_11ab0); f_0250e marks
the dirty map G:15C4 (ignored by the tests). Thunks: f_2f802 → f_71a7d (full-screen picture, stubbed), f_2f80c → f_76a37
(alarm-trail mode on/off: G:104E, T:07BE, menu check mark), f_2f82a → f_7686d (help message box, UI),
f_2f834 → f_7c7e5 (enter a nest). f_2f7d0 → f_75d01 is the player-event UI (dialogs, death, becoming another ant): a hook.

## Verification harness (tools/re/emu.py)

Status: **the original game runs headless and plays complete games.**

- `SimEmu(base=0x100).boot()` loads the flat image like DOS would, with all relocations applied, a PSP
  and an environment. It runs the real startup (overlay-manager stub → C runtime → `main` → resource
  loading → video mode 0x12) until the title screen polls the keyboard.
- `call_lin(addr)` calls any routine with its correct code segment (overlay base, or the segment the
  program's own far calls use). Calling with a wrong `seg:off` split breaks near calls.
- Headless pieces: the game's clock (`1b73:0012`, normally bumped by its INT 8 handler) advances on each
  read; drawing (`f_259de`), the game-over screen (`f_71a7d`) and message boxes (`f_71b1a`, logged as
  `(tick, STR id)`) are stubbed; `SIMANT.CFG` is served with sound off; DOS file handles are reused
  (MSC refuses handles >= 20).
- `run_quickgame.py`: Quick Game (mode 1) + `SimStep` loop with a fixed LFSR seed. Deterministic. With
  seed 0x1234 the red queen starves at tick 7705 and black wins at tick 7745 (messages 10016, 10012,
  10013); ~650 ticks/s. `--dump` writes the sim segment per sample as ground truth.
- `render_state.py`: debug renders of the surface, both nests and the pheromone maps from a live run.

Observed at the start of a Quick Game: `max_passable_tile` = 0x50; black entrance at surface (a 20,
b 32), red at (a 121, b 32), both nest column 32.

## Patch generation (`f_6ae20`, overlay 10; called by new game `f_6b36b`)

The yard is 192 patches (12 × 16). Each has a random seed (`SIM:0000 + 2*index`, filled at new game with
`(crt_rand() % 0x7fff - 0xc000) & 0x7fff`), and the player starts on patch (11, 8). Generation is
**deterministic per patch**:

```
GeneratePatch(seed, n_black, n_red, ..., house_args):
    SeedLfsr(seed) (f_009bf); BuildSurfaceTerrain() (f_0cdb0); f_2f94c(house args)
    n_black += n_black/4; n_red += n_red/4
    nests: every cell dirt 0x2E (diggable), exit field 0, cells empty; surface occupancy cleared
    nest row 0 (top soil): yard 0x1C + Rand4 (black and red separately); house: 0x1C/0x1D or 0x1E
    exit field row 0 = 0xFF; all pheromone maps cleared
    for each colony (black: a = RandLow(128), red: a = 127 - RandLow(128); b = Rand64):
        w = 7 + Rand(6); s = 15 - Rand2                  # per-colony caste odds (out of 16)
        repeat n times: pick (a, b); skip if tile >= 0x50 (retry); if occupied, retry (up to 50 times)
            r = Rand16(): r < w → worker (caste 2); r < s → soldier (6); else Rand2 ? male (4) : new queen (8)
            occ[a][b] = caste<<3 | Rand8() (| 0x80 for red)
    entrance tables cleared; MakeSurfaceHoleBlack(32) / f_15247(32) (red) → both entrances in nest column 32
    nest stats, capacities and centroids reset; G:0242 = 64
    if n > 1: pre-dig the nests (f_6b616(n_black*16) / f_6b6f3(n_red*16))
    f_0f329: build the surface ant arrays from the occupancy grid
```

### Surface terrain (section 20, entry `f_73020(row, col)`)

`idx = row*16 + col`. Patches with `idx < 38` (near the house) use hand-made layouts in a switch
(`f_7304b`). All other patches use the generic generator `f_73c33`. RNG = LFSR seeded with the patch
seed (`SeedLfsr` `f_009bf` just sets `DS:8ba2`), so a patch is identical every time it is generated.

```
GenericPatch():                                    # f_73c33
    for a in 0..127: for b in 0..63: surface[a][b] = Rand16()     # 16 ground variants
    repeat Rand(3)+2 times:                        # rocks, f_73dfd
        for shape in 0..5: RockStamp(Rand(122), Rand(58), shape)
    FoodPiles(Rand4()+1)                           # f_0afce, max 10
    HazardsReset()                                 # f_0b66c: clears counters; yard: SpecialObjects()
    20 ×: a, b = Rand(125)+1, Rand(61)+1; if the 2×2 block at (a..a+1, b..b+1) is all < 0x18:
          (a,b)=0x20, (a+1,b)=0x21, (a,b+1)=0x22, (a+1,b+1)=0x23
    30 ×: same position rule; if (a,b) and (a+1,b) < 0x18: t = (Rand(2)+0x12)*2 → (a,b)=t, (a+1,b)=t+1
    100 ×: single cell < 0x18 → 0x28
    128 ×: single cell < 0x18 → 0x51 (rock, impassable)

RockStamp(a, b, shape):                            # f_73fc6, shape table T:08c2 [6][5 b][5 a] bytes
    if any nonzero shape cell lands on a tile > 0x10: return   # all or nothing
    copy the nonzero shape cells into the surface

FoodPiles(n):                                      # f_0afce → n × f_0b016
    up to 200 tries: a = Rand(65)+Rand(64); b = Rand(33)+Rand(32)          # centre-biased
        if centre and all 8 neighbours are open ground: stamp; stop
        (after 100 tries a centre that is merely open is accepted)
    stamp (f_0b09c): centre = 0x38; each open neighbour i = 0x30 + DS:1b92[i]
    pile table (10 slots): G:0a92 a, G:0aa8 b, G:0aba/0acc/0ade = 0; T:0c4a = count

SpecialObjects():                                  # f_0ad9c (yard only), 2 objects
    a, b = Rand(128), Rand(64) on a tile < 0x10; kind = Rand(8)
    remember a, b, kind, old tile (G:0eae, 0f00, 0f1a, 0f28); tile = T:0c52[kind]
```
Open ground (`f_1145c(view, a, b)`): tile < 0x10 on the surface (< 8 in a nest) and no occupant except
the player. Map accessors used everywhere: `GetTile(view, a, b)` `f_117c0`, `GetOccupant` `f_11737`,
`SetTile(view, a, b, t)` `f_1183e` (view 1 = surface).

Surface tile summary: `0x00–0x0F` ground, `0x10–0x17` corpses, `0x18–0x1F`/`0x20–0x28` passable
decorations, `0x30–0x38` food pile (3×3), `0x48–0x4B` food crumbs (what ants pick up), `0x50` nest
entrance, `0x51–0x5F` rocks (impassable), `0x71`/`0x73` special objects.

## Verification plan

Run the original routines **in a CPU emulator** (Unicorn, 16-bit real mode) on `build/flat.bin`: load the
image at linear 0, set `DS = SS = 0x55b3`, seed a sim state, call e.g. `SimStep` (`0894:000e`) and dump
the `0x3e1d` segment. The port then gets compared tick by tick against the original (differential
testing). Patch out display/sound side effects by keeping `patch_visible` (`T:07b2`) = 0, and stub any DOS
interrupts.
