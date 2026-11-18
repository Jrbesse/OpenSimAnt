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

Seeding (found 2026-10-17): at startup (init around 0x075B0, unless the check `f_0126f` returns
non-zero) the game seeds the LFSR from the clock, `f_009fe`: DS:8BA2 = clock ^ 0x3751, then `f_00a11`
draws Rand128, seeds the C runtime rand() from the clock (`f_2c8d8`) and calls rand() that many times.
So every real game starts from the time of day; the verifier sets the seeds itself.
UI drawing draws from the LFSR as well:
- the yard window's rain and mating swarms (`f_70601` / `f_706d0`, see "The yard window");
- the spider composite;
- the speech balloons.

To replay a real session, those draws have to be replayed too; a remake that seeds from the clock
anyway can ignore them.

## Simulation step (`f_0894e`, called once per game tick; ported: `simant_ref/sim.py`, verified tick by tick)

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
   G:06AC 7/8, beaten when > 8 cells of the 4x4 block a-1..a+2, b-1..b+2 are occupied (f_0db10 loops -1..2, sic; > 4: flees), drops food when it finally leaves).
   `f_0c692` (the drop, also the player-spider's) on house furniture (surface tile 0x27..0x3f, G:0F24 == 1) calls `f_0c73d`: from
   the tile it walks (a += DS:1B9A[G:0F3A], b += DS:1B9E[G:0F3A], both added as unsigned bytes, so rooms 0 and 3, whose
   step is 0xFF, stop at once) until a tile below 4 becomes food ((t + 6) * 4, G:1040++) or the walk leaves the map;
   the drop counts as done either way (no crash; checked by test_world.py 'spider beaten furniture').
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
5. (done: new game / patch setup, `simant_ref/newgame.py`; see "New game" below.)
6. (done: moving between patches `f_01d48` and the house patches `f_7304b`, see "Moving to another
   patch" and "The house" below. Mating-flight colonisation is the yard layer's (`f_6a721`); `f_01315`
   is an empty stub.)
7. Scoring/ratings, history graph sampling, timers (`G:0c26` total ticks), game speed.
8. Rendering: (started: the cell → tile / sprite mapping and the sheets, "Rendering the map windows";
   still to do: the overview map window, the yard map, the other windows and the UI.)
9. Save-file format (`.ANT`).

## The player (yellow ant): sec27 `f_7bf7e` and `f_7b7b8` (ported: `simant_ref/player.py`)

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

f_7b7b8 (each tick, if G:0AA0), ported and verified (`player_action`):
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
            after entering / climbing out the walk goes on (res 0), unless the cursor was on the cell
            just stepped onto in the old view and the new view is not the one shown (G:032E): res -1
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
- E (done): f_7b7b8 itself, verified by 33 action scenarios run tick by tick until the action ends.
UI pieces to stub in the emulator (they write G screen state): f_01aa7 (scroll the view to the yellow
ant, from f_01c52, which also sets G:1074 = 1), f_03381 (redraw, from f_03391 / f_11ab0); f_0250e marks
the dirty map G:15C4 (ignored by the tests). Thunks: f_2f802 → f_71a7d (full-screen picture, stubbed), f_2f80c → f_76a37
(alarm-trail mode on/off: G:104E, T:07BE, menu check mark), f_2f82a → f_7686d (help message box, UI),
f_2f834 → f_7c7e5 (enter a nest). f_2f7d0 → f_75d01 is the player-event UI (dialogs, death, becoming another ant): a hook.

## Player events and the game flow (ported: `player.player_event`, `game.py`)

**Player events** `f_75d01(n)` (via `f_2f7d0`), verified by `test_events.py` (42 checks) and in full ticks
(`test_sim.py`: a starving yellow ant dies, event 8, and the player takes over):
```
    if not the spider (G:0A06 == 0) and carrying (type & 8): drop the load (f_1317c); failing that,
        type = (type & 0x80) | T:0094[caste] << 3 (T:07AC zeroed meanwhile)
    7 <= n < 10: AnimYellowInsane f_7c3b1 (staggers: C-runtime rand targets within 3, pathfinder f_7a69d)
    n: 0 starved (Rand(5) sound; message 0x272E / 0x2730 by G:1058)
       1 spider (f_71f52 scene: Rand(2) picks message 0x273F / 0x2740), 2 ant lion (f_76707 scene):
         G:0F20 += 1; Rand(5) sound; f_7c149(mode n): pit frames 0x38 + k for the lion
       3, 4: messages 0x272A / 0x272C; 5..9 (Rand(5) sound): 0x2732 0x2734 0x2736 0x2738 0x273A
       G:0EFC += 1 (8: G:0F30 += 1); 10 squashed: G:0EFC += 1, f_7c149(10) (the ground flickers)
       messages only when T:07AE; f_7c149 frame count: 6 (fight), else 8, or 0x20 / 0x40 (T:07AA) when
       the game window is active (DS:5702 == 0); events 1..9 stop early once the sound has finished
    take the yellow ant off the map; release recruits f_14005(1) (state 6 → 0, red nest 7); alarm off
    become (each search starts one past the last ant, sic): black nest types 1..7 → queen scene f_758e0;
        else the last black-nest adult (types 8..0x67), surface adult, red-nest adult: removed from its
        list and map, the yellow ant there as type & 0xF8 (occupancy value type + heading), health 100
    none: Quick Game over (G:0376 = 1, G:0366 = 0); Full Game: G:03E2 < 2 → over (message 0x2748),
        else message 0x274A and the yard map (f_7650c, UI → move_to_patch); mode 3: reads an unset local
```
`f_758e0(view, a, b, t, found)`: found 0 = the new queen leaves her cocoon (G:0502 frames 1..7, heading
2 or 6); found 1 (from `f_76cb9`) = the yellow queen founds a nest: queen chamber `f_6ba1c` / `f_6bb70`,
G:0AF6 / G:0B04 += 1, population counters.

**Game flow** (`test_game.py`):
- Rating `f_70fb0`: eight parts (history average G:073C, % G:0626 of G:0626 + G:06AE over the last T:0828
  history entries, % eggs not lost, % G:09FA of G:09FA + G:0A00; Full Game / mode 3: yard colony
  ratios, % of the 155 yard and 37 house patches held), score = health + 51 x sum(part x DS:2AF8
  weight), Quick: x 29 / 10 and x (ticks / 100) / 41 under 4100 ticks; Full: x (ticks / 100) / 81
  under 8100 ticks, x 5; plus the ticks played. Rank `f_71d95`: thresholds 0x344CC, 0x68998, 0x9CE64,
  0xD1330 (Full Game: score / 5), + 5 when lost.
- Game over `f_71d95`: the rating window (window 4, bitmap 16100; font 4, or 2 when DS:3DB2 == 320; item 0x402
  the mode's name G:0324[G:0EAC], 0x403 the score "%ld" (DS:2B50, the raw score even in a Full Game), 0x404 the
  rank's title G:0328[rank]; any event or `f_01277(100)`'s timeout closes it), one Rand2 for the fanfare once the ending's sound is done,
  then the new-game dialog `f_725b6`: buttons 0x202 Quick (1), 0x203 Full (2), 0x204 experimental (3),
  0x206 tutorial (0), 0x205 quit, 0x207 load; then G:0EAC = mode, G:0354 = 1, G:07C8 = 0, `f_6b36b`;
  tutorial: T:07A4 = 1, T:07A6 = 0.
- Win screen `f_2f91a` → `f_72750` (decoded 2026-10-20; also the 'fred' cheat): the yard window in its Yard view
  (`f_01447`, `f_01823(0)`, `f_01aec(0)`), `f_011e5(150)` (wait 150 clock ticks, or any event, or the timeout of
  `f_01277`); window 26 with its picture item set to 16200 (`f_23557(0x1A01, 16200)`: the human, the cat and the
  dog; layout 26 shrink-wraps a 2-px frame around the picture at 153, 85; 320-px mode moves it); `f_01277(10)`: a
  10-second timeout (DS:8BAC = 180 ticks). Loop until `f_01572` (a key, or that timeout) or clock3 + 600: when
  `f_00f28` reports the music idle, songs 0x4E23 then 0x4E24 (`f_00ea1(n, 0x7E)`); every 8 clock3 units the six
  eyes, bitmaps 16210 + frame (0..2 in turn) at the picture's corner + DS:2C2C's (x, y) pairs (72, 74), (87, 66),
  (175, 64), (191, 66), (159, 122), (179, 124). Then `f_011e5(300)` and the window closes (`f_214b5(0x1A00)`).
- The other scenes in window 26 (decoded 2026-10-20), all only with T:07AE (Options > Events) on:
  - `f_76707`, the ant lion takes the yellow ant: picture 9200, sound 0x26 (then `f_00f1d`, always 1); until an
    event, clock3 + 300 or the window closing, every 0x1E clock3 units frame 9200 + i (i = 1, 2, 3, 2, 3, ...) at
    the corner + T:0B14 / T:0B16[4 i] ((38, 39), (38, 52), (38, 52)), sound 0x25 for odd i.
  - `f_71f52`, the spider takes it: picture 12000, sound 0x2D, `f_01277(8)`; until `f_01572` or an event, every 8
    clock3 units 12001 + T:09B4[i] ((0, 1, 2, 1), i wraps after 3 with sound 0x2D) at the corner + (46, 77); then
    **Rand(2)** (the game's RNG, in the port's player event) picks the box 0x273F / 0x2740, drawn over the scene
    (`f_71b1a(0, id, 1)`), and the window closes after it.
  - `f_7686d(picture, n)` (from `f_75d01`, `f_758e0` and `f_12de1(1)`): 9100 / 9101 with STR# 1010 [23 + n] ("Your
    ant has been killed", "You have been reborn!", "You are now a worker!") written into item 2 (`f_23943` →
    `f_20a0f`: centred, its row filled in scheme 13), then `f_011e5(300)`; 9110 (a nestmate feeds the yellow ant):
    sound 0x2A, `f_011e5(0x2D)`, 9111 at the corner + T:0B24 / T:0B26 = (72, 62), sound 0x2D, `f_011e5(0x2D)`.
- `f_12de1(n)`'s screen part (the port's "menu" effect): 0 sound 0x2C and `f_71a7d(1)`; 1 the 9110 scene and the
  timed line STR# 1010 [11] for 0x78; 2 [12] for 0x78; 3 sound 0x2C, sound 10, [13] for 0xB4.
- `f_71a7d(flag)` (the port's "picture") and `f_6e17e(n)` (the port's "pause" / "edit_tool", via `f_2f816`): the
  pause line. `f_6e17e` first cancels the Exchange / Chase modes when unpausing (`f_11b5f` / `f_11aff`), sets
  G:047E = n, then (both) the lasting timed line STR# 1010 [2] "Game Paused" (G:105E -1), [3] (10, Exchange) or
  [17] (11, Chase) while paused, or clears it. Loading a game pauses it (`f_2f816(1)`).
- `f_7c149` (fights and the deaths 1, 2, 10) and `f_7c3b1` (the deaths 7..9) are animations: each frame waits until
  clock3 passes the last frame + 6 (`f_011e5(1)` in a loop), plays its sounds, changes the cell (`SetTile` for the
  pit, the ground byte for mode 10), moves the yellow ant as type t with a random heading (`f_11a3e`) and redraws the
  Edit window (`f_03391`). A fight is 6 frames (~0.1 s each); a death 8, or 0x20 while the Edit window is the active
  one (0x40 with the music on, ending early when the sound is done). The port marks them with "anim_begin" /
  "anim_frame" / "anim_end"; the shell's hooks keep a copy of the State per frame and replay them.
- `f_753e5(sx, sy, x, y)` (thunk 0x2F7E4, from the spider's lash `f_0dd40`, the port's "spider_strike"): sound 0x37
  (`f_00ed8(0x37, 0x8265, 0x3F)`); with the Edit window on the surface a line in colour 3 from the spider (G:0F12 /
  G:0F34, 1/16 cell = 1 px at 16 px per cell) to the struck ant's cell centre, again 1 px down-right, and a 2 x 2
  dot in colour 2 at its end (the driver's line DS:916C, the fill DS:9134); the same in the Map window at its scale.
  The next redraw removes it.
- `f_22e9f(id, on)` sets an item's highlight bit (+24 bit 2) and redraws it inverted (`f_1d250`, the XOR fill): the
  yellow ant's alarm trail marks the Edit window's SCENT button 0x10 this way (`f_22f65`, the port's
  "menu_check"), as G:047E marks PAUSE. `f_00ed0` and `f_0125f` are empty in the DOS version (the 'joke' cheat and
  the Mystery Button's music do nothing on screen).
- The global timeout: `f_01277(s)` sets DS:8BA8 = now and DS:8BAC = 18 s; `f_012c4` → `f_1ccfc(&8BA8, 8BAC)` is
  true when now is outside [start, start + period) and then restarts the period from now (a periodic timer that
  starts expired: 0 / 0). Message boxes (`f_71bb6`) arm 15 s and close on it, a key or a press; the title
  (`f_72bc2`) 40 s; game over (`f_71d95`) 100 s; `f_71f52` 8 s; the win screen 10 s; the help stub (`f_76eb5`) 30 s.
  A wait like `f_011e5(300)` therefore ends early when the period of the last armed timeout runs out.
- `f_011e5(n)`: waits until n clock ticks pass, an event arrives (`f_21cb8`) or `f_01572` is true. `f_01277(s)`:
  flushes the mouse buttons and starts an s-second timeout that `f_012c4` / `f_01572` report.

## The tutorial (`f_0e425`, `f_0e4e4`, `f_0e93e`, segment 0e2e; ported: `simant_ref/tutorial.py`, verified by `test_tutorial.py`)

Game mode G:0EAC = 0. Starting it (`game.start_game`) sets the step T:07A4 = 1 and T:07A6 = 0. The advisor
`f_0e2ea` calls `f_0e425` every tick in this mode, then does its usual status line. `f_0e425`: T:07A2 + 1 (back to
0 past 0x400); only when T:07A2 & 7 == 0: G:10B8 + 1; if the step has not been shown (T:07A6 == 0), show it
(`f_0e4e4(step)`), T:07A6 = 1, G:10B8 = 0; else if its check passes (`f_0e93e(step)`) the step + 1 and T:07A6 = 0
(shown next time); else, after 16 polls (G:10B8 > 15) and once the clock3 passes the 32-bit target G:0204, T:07A6 =
0 (the message again). Both routines switch on step - 1 through jump tables right after the jump (CS base 0x0E2E0;
Ghidra garbles them), 56 steps.

`f_0e4e4`: a message box `f_2f6ea(picture, STR# 0x2AF8 + 2 (step - 1), 1)` (SHARED STR# 11000..11112; step 56, the closing box, is the one off the rule: case 56 at 0e925 pushes 0x2B68 = 11112, as
55's two variants take 0x2B64 / 0x2B66; pictures
HCEGANT 17000..17014 for steps 2, 5, 11, 13, 14, 17, 18, 21, 33, 36, 38..41, 43..48, 50; step 55 shows 0x2B64 or
0x2B66 by G:1074, i.e. which nest step 54 found). Setups: steps 3 / 4 the target G:0204 = nest capacity G:0224 + 2 /
10; 7 / 26 G:1074 = yellow a + b and the target = clock3 + 0x258; 8, 30, 43, 46, 50 G:1074 = 0; 9 G:1074 = the Edit
window's origin G:0508 + G:050A, target clock3 + 0x258; 14 health 8 (`f_12d43`); 23 ten black surface ants
(`f_2f6cc` → `f_6be50`); 27 G:1074 = a + b; 41 G:1074 = the behaviour weights G:049E + G:04A0; 49 eighty black
ants, then the alarm map (SIM:D09F, 64 x 32) cleared.

`f_0e93e` (1 = done): 3 / 4 capacity > target and no action pending (G:0AA0 == 0); 5, 20 on the surface (G:048C ==
1); 7 / 26 moved (a + b != G:1074), G:0B1E == 0 and the clock past the target; 8, 43, 46, 50 G:1074 != 0 (the UI sets
it when the view recentres or follows, f_01c03 / f_01c52); 9 the Edit window scrolled, or the clock past the target;
10, 32, 42 the Map window active (`f_23612(0x100)`: DS:5702, the active window's id, == 0x100); 12, 49 the Edit
window active (0); 39 / 47 Behavior / Caste Control (0x1200 / 0x1300); 13 on the surface on a tile > 0x47 (food);
14 health > 90; 16 carrying food (G:04C2 == 0x18); 18 in the black nest; 19, 22 G:04C2 == 0x10; 21 carrying a rock
(0x28); 24 / 52 recruits G:0B1C > 1 / > 40; 27 moved with alarm scent on (G:104E) and G:0B1E == 0; 30 turns the
alarm scent off quietly (`f_2f80c(0, 1)`) and waits for G:1074; 33 the view is the yard (G:032E == 0), 38 the
surface (1); 36 the yard window's House view (G:035C == 1); 41 the behaviour weights changed; 54 entered a nest
(red: G:1074 = 0, black: 1). The other steps pass at once (the message box itself waits for its click). Step 57
and later do nothing.

`test_tutorial.py`: every step shown and checked (passing, failing early, failing late with the re-show) from every
snapshot, 9 calls each so the state carries on: 213 cases, ALL OK.

## Cheat codes (`f_6a920`, overlay 10; ported: `simant_ref/cheats.py`, verified by `test_cheats.py`)

Called once per typed key (`f_6a920(key)`, via thunk 0x2f924 from `f_74386`). Matching:

- The key is stored bitwise-NOT in G:0B0A[T:06DE], then T:06DE += 1.
- The table at T:067E holds 4-byte codes, also NOT-ed, and ends at an entry whose first byte is 0.
  Entries are scanned in order; the first one whose first T:06DE bytes equal the buffer wins (a prefix
  match).
- No entry matches: T:06DE = 0 and G:0B0A[0..3] = 0. The key that broke the match is dropped, not
  retried as the start of a new code ("hhole" does nothing).
- Match with T:06DE >= 4: clear the same way, `f_277da("CHEAT %d", index)`, then run the cheat.
- Codes are case sensitive; the capitalised ones are the red twins.

`snd(n)` below is `f_00ed8(n, 0, 0x7E)`; "toggle X" is `X = (X == 0)`, then snd(2) if it is now on,
snd(1) if off.

| # | Code | Effect |
|---|---|---|
| 0 | oops | snd(10); G:0850 (red new colonies) += 10 |
| 1 | rand | snd(1); `f_12d43(100)` (yellow ant health) |
| 2 | erad | snd(1); `f_12d43(1)` |
| 3 | FUND | `f_71b1a(0, 0x2724, 0)` (via thunk 0x2f6ea; a message) |
| 4 | joke | `f_71b1a(0, 0x2726, 0)`, `f_0151c()`, `f_0125f(6)`, `f_00ed0(0)`, `f_0125f(0)`, `f_71b1a(0, 0x2728, 0)` |
| 5 | hole | `MakeSurfaceHoleBlack(i)` for i = 0..63 |
| 6 | HOLE | `f_15247(i)` (red entrance) for i = 0..63 |
| 7 | qeen | black queen chamber `f_6ba1c(yellow_a + 2, yellow_b, 2)` (thunk 0x2f938) |
| 8 | QEEN | red queen chamber `f_6bb70(yellow_a + 2, yellow_b, 2)` (thunk 0x2f92e) |
| 9 | eggs | 16 x `SpawnBlackBrood(yellow_a + T:0000[Rand8()], yellow_b + T:0008[Rand8()], rand() % 6 + 1)` |
| 10 | EGGS | the same with `SpawnRedBrood` and type `rand() % 6 + 0x81` |
| 11 | heal | G:10BE (black health) = 100 |
| 12 | HEAL | G:01FE (red health) = 100 |
| 13 | zhea | G:01FE = 0 |
| 14 | ZHEA | T:0C18 (no health loss) = 0, G:10BE = 0 |
| 15 | just | G:07C8 (black new colonies) += 10, `NewColonyNoop()`, snd(0x29) |
| 16 | will | toggle T:0C14 |
| 17 | mick | toggle T:0C12 |
| 18 | jeff | snd(2); every yard cell (12 x 16): T:00A4[cell] += 4 (black yard colonies), G:0A90 += 1 |
| 19 | joel | snd(1); every yard cell: Rand2() == 0 ? T:00A4[cell] += 1, G:0A90 += 1 : T:0164[cell] += 1, G:0AC4 += 1 |
| 20 | fred | the win screen `f_2f91a` |
| 21 | jenn | toggle T:0C16 (yellow ant invulnerable, see `f_12d43`); on: G:0F78 = 100 |
| 22 | susi | toggle T:0C18 (no health loss); on: G:10BE = 100 |

Evaluation order for eggs / EGGS (C pushes right to left): `rand()` first, then the Rand8 for the y
offset, then the Rand8 for the x offset. eggs, EGGS and joel draw from the game's RNG (whether the
spawn / chamber helpers draw too is not checked yet). Of the cheats, only FUND, joke and fred are pure UI.

## Debug commands (segment 015b; ported: `simant_ref/debug.py`, verified by `test_debug.py`)

Reached from the menu-command handler `f_6e5c0(event)` (via thunk 0x2f9c4 from `f_74140`): command id
event[0x0C] 0x102..0x118 through a jump table at 0x6e5e8 (cs base 0x6e460). The ids are the main window's
items (FILE_FORMATS "Window layouts"): 0x110 is the "Center on Yellow" button and 0x112 the "Mystery
Button".

The whole table (the Map window's toolbar, layout 1):
- 0x102 (the map) → `f_2f898(event)`; 0x103 / 0x104 nothing;
- 0x105 Yard → `f_01447`; 0x106 / 0x107 / 0x108 → `f_011d2()` then `f_01aec(1 / 2 / 3)` (0x108 also
  `f_215a5(0x100)`);
- the scent layers → `f_01781(n)`: 0x109 → 4, 0x10A → 5, 0x10B → 8, 0x10C → 6, 0x10D → 7 (T:07C8);
- 0x10E Show Trails: DS:2994 = (DS:2994 == 0), the "redraw only the ants over the kept image" flag of
  `f_6efd6`;
- 0x10F → `f_07aab` (Behavior Control), 0x111 → `f_07a95` (Caste Control), 0x110 → `f_6f733`,
  0x112 → `f_022bc`, 0x113 → `f_2f9ba` (History), 0x114 → `f_2f9a6` (Efficiency Score), 0x115 →
  `f_2f9b0` (Ant Info);
- 0x116: G:1074 = 1, `f_2f74e(0x103)`; 0x117 → `f_2f88e` (the Experimental menu); 0x118 → `f_2f9ce`
  (the population report).

- Command 0x110 ("Center on Yellow") → `f_6f733(event)`: the BIOS shift flags 0000:0417 pick a hidden
  action.
  - No Ctrl: `f_01c52` (the normal action: follow the yellow ant).
  - Ctrl + Shift: left half of control 0x110's rect (from `f_252d8`) = black, right half = red.
    With Alt that colony loses ants (`f_0161f`), without Alt it gains ants (`f_015be`).
  - Ctrl + Alt: sound `f_00ed8(0x20, 0, 0x7E)`, then clear all food (`f_01707`).
  - Ctrl only: drop food, `f_6bca5(0x96, 1)`.
- Command 0x112 (the "Mystery Button") → `f_022bc`: one of 15 actions by `rand() % 15`:
  - 0, 1: 2 x add red ants; 2: 2 x add black ants
  - 3: 2 x kill red ants; 4: 2 x kill black ants
  - 5: drop food `f_6bca5(0x96, 1)`
  - 6: sound `f_00f02(0x20, 0, 0x7E)`, then clear all food
  - 7: `f_00ed0(0)` (music)
  - 8: red holes `f_15247(2i)`, i < 32; 9: black holes MakeSurfaceHoleBlack(2i), i < 32
  - 10: T:0C18 = G:10BE = G:01FE = 0
  - 11: toggle T:0C14 (sound 2 if on, 1 if off); 12: toggle T:0C12, no sound
  - 13: message 0x2726, `f_00ed0(1)`, message 0x2728
  - 14: G:06AC = 8 (the spider lashes out), `f_00ed8(2, 0x2B77, 0x7E)`

The routines they call:

- `f_015be(black)`, add ants: if the surface has fewer than 1000 ants, add 32 of the colony
  (`f_6be50` / `f_6bf06`, see `newgame.add_surface_ants`); T:0798 == 1 adds 1000 - count instead.
  Then the census `f_0c20f`.
- `f_0161f(black)`, kill ants: CompactSurface + census, then from the last surface ant down, up to 51
  of the colony become corpses (PlaceCorpse(x, y, red)) and get type 0, then CompactSurface + census
  again. Red ants on the player (`f_134b8(1, x, y)`) are spared.
- `f_134b8(view, a, b)`, is the player here?
  - The yellow ant's view must be `view` (0 counts as 1).
  - Spider player (G:0A06 == 1): surface only; true when the squared distance from (16a + 8, 16b + 8)
    to (G:0F12, G:0F34) is under 0x200.
  - Otherwise: true when the view's occupancy byte at (a, b) is 0xFE / 0xFF.
- `f_01707`, clear food: every surface tile of TileClass 1 (food) gets `Rand16()`; G:1040 = 0.

All of these draw from the game's RNG except the toggles and messages.

## Map tools (`f_770f6`, overlay 0x74FE0, second code segment 0x76F40; ported: `simant_ref/tools.py`)

The map's mouse handler `f_74fe0` → `f_76f4a` → `f_770f6(a, b)` applies tool G:104C at the clicked cell
in the view on screen G:032E (1 surface, 2 black nest, 3 red nest). Rocks and dig run from the previous
point (G:09FC, G:09FE) to the click.

`f_76f4a(a, b)` is the drag loop (UI, not ported; audited 2026-11-01, with the emulator):
- It is only entered from `f_74fe0` (the Edit map's handler) in Experimental (G:0EAC == 3), by either mouse
  button, before anything else there (Ctrl is not special). `f_74fe0` first waits up to 6 clock ticks for a second
  click when the first was a left one and the Edit window is the active one (`f_23612(0)`).
- Only when G:032E != 0. The previous point is first set to (a, b), and the tool is applied if (a, b)
  is in the patch (`f_10f7e`: surface 128 x 64, nests 64 x 64).
- Then, while the **left button alone** is down (`f_0122c() == 1`: a right-button press applies the tool once and
  leaves), it reads the mouse (`f_201f0`) and turns it into a cell: through the Map window's rect G:10D2 / cell
  size G:3856 when that window is the active one (`f_23612(0x100)`; not reachable from the Edit map's click),
  otherwise (x - G:110C) / DS:19BE + the view origin G:0508 (C division). The mouse need not be over the map item:
  the loop follows the pointer anywhere, limited only by the patch test.
- When the cell changes, the previous point becomes the old cell and the tool is applied at the new one (if in the
  patch).
- Tools >= 5 (pheromone, insecticide) are also applied on every poll (at the pointer's cell, if in the patch), and
  then G:106C ^= 1.
- The game does not run while the loop does: the main loop is inside `f_74fe0` (`f_771cf` only redraws the Edit /
  Map windows; `f_01325` is empty). Checked: the RNG does not move while the button is held.
- G:0A9C counts the polls. Option bytes T:07B7..T:07BC belong to tools 1..6. Alt (0000:0417 bit 3)
reverses food, pheromone, rocks and dig.

| G:104C | Tool | What it does |
|---|---|---|
| 0 | info | GetOccupant != 0 → `f_2f8fc(a, b, view)` (UI) |
| 1 | rocks `f_7723f` | surface only; see below |
| 2 | dig `f_7739f` | see below |
| 3 | ants `f_77672` | see below |
| 4 | food `f_77790` | T:07BA == 0: one crumb `f_77ad6`, sound 0x1D if placed; else sound 0x20 and 20 crumbs at (a + Rand(9) - 4, b + Rand(9) - 4) |
| 5 | pheromone `f_7783a` | surface only; see below |
| 6 | insecticide `f_778bd` | see below |

**Rocks.** Steps from (x, y) toward the click, one axis per step: x += T:0010[d], or y += T:001A[d] when
that is 0, with d = DirTo. It stops after the step with d == 0, or when the cell leaves the patch. Per cell:
- Alt: tiles 0x51..0x67 become Rand(16), then the walls are refitted.
- T:07B7 == 0: free open ground (tile < 0x50, no occupant) becomes wall 0x60, the walls are refitted,
  sound 0x28.
- Otherwise: free open ground becomes a pebble, Rand(3) + 0x51, then sound 0x0A at pitch
  Rand(10000) + 0x7D0.

Refitting the walls (`f_77bec`) handles the cell and then its in-patch neighbours (above, right, below,
left): each wall tile (0x60..0x67) becomes DS:2DF4[mask]. The mask's bits are the wall neighbours: left 8,
below 4, right 2, above 1.

**Dig.** Steps diagonally (x += T:0010[d], y += T:001A[d]) until d == 0, with no bounds check. The mode
is T:07B8, XOR 1 with Alt.
- Dig, on the surface: `try_found_nest` (sound 0x13); if that fails, sound 1 and a status message.
- Dig, in a nest: a diggable cell (`f_1345e`) below row 0 is dug (DigAt); at row 1 a surface hole is
  opened too. Sound 0x13.
- Fill, on the surface: sound 1 and a status message.
- Fill, in a nest, on a cell that is not diggable and below row 0:
  - if an ant is there, every live nest ant on the cell is removed (`f_775a2` / `f_7760a`);
  - the cell is refilled (`f_77d75` / `f_77e44`): dirt 0x2E, cell and exit field cleared, the four
    neighbours reclassified; while the capacity is > 1, the dig sums lose (col, depth) (32-bit, clamped
    at 0) and the capacity drops by 1;
  - sound 0x12.

**Ants.** Type Rand(8) + 0x10, + 0x80 when T:07B9 == 1.
- Surface: open ground only, `f_0f167` with state 2.
- Nest: not at row 0. A cell with dirt >= 0x1C is dug first, then AddNestAnt with state 2 for the nest's
  own colony, 7 (invader) for the other.
- Sound 0x1C, except when the surface check or row 0 stops it.

**Food crumb `f_77ad6`.** The base tile is 0x48 on the surface and 0x10 in a nest.
- Alt: only a crumb (base..base + 3) is taken. It becomes Rand(8), and G:1040 - 1 (if > 0) on the
  surface only. The code that would count down the nest counters (G:1050, then G:1060) is reached only
  with view 1, where its view == 2 test fails: dead code.
- Otherwise: refused when the tile is above base + 2. A crumb grows by 1, ground below 0x18 becomes base,
  and any other tile is kept but still counted: G:1040 / G:1050 / G:1060 + 1.

**Pheromone.** Works on the map chosen by T:07BB (0 black nest marker SIM:E09F, 1 black trail E89F, 2 red
nest F09F, 3 red trail 4DA7:0000, 4 alarm D09F; 64 x 32, index a * 32 + b) at the cell (a >> 1, b >> 1).
- The cell gets + 0x46, or - 0x28 with Alt, clamped to 0..255. A read off the map gives -1, and writes off
  the map are dropped.
- Then `f_77f13` smooths the cell, its four neighbours (above, right, below, left) and the cell again.
  Each smooth (`f_77f71`) sets the cell to (sum of the four neighbours / 4 + the cell) / 2, with C
  truncation; a negative result is stored as its low byte.
- Sound 0x1B.

**Insecticide.** Always 8 sprays. With T:07BC set, each hits (a, b) with sound 9. Otherwise each hits
(a + Rand(9) - 4, b + Rand(9) - 4) with sound 9 at pitch Rand(1000) + 0x278F; the Rands run in that order.
- Surface:
  - an occupied cell: the ant there (SurfaceAntAt → G:0F18) becomes a corpse, PlaceCorpse(x, y,
    type & 0x80); its type and the occupancy are cleared;
  - the spider (G:0F12 >> 4, G:0F34 >> 4) on the cell: `f_0db90`;
  - an ant-lion tile (0x38..0x3E): `f_0b5c8(f_0b58c(x, y))`.
- Nest: the ant on the cell (by its type) is removed: its type and the cell are cleared.

## Rendering the map windows (`f_0379e`, `f_03518`, `f_02fdb`, `f_02c21`)

A map window is 40 x 30 cells (`f_0379e(x, y)`), its origin G:0508 (a) / G:050A (b), its view G:032E
(1 surface, 2 black nest, 3 red nest), screen cell size DS:19BE x DS:19C0 at G:110C / G:110E. A cell's
(background, foreground) pair is cached in the dirty map G:15C4 (40 x 30 words) and the tile cache
G:1114 (40 x 30 bytes); only changed cells are redrawn. `f_03518` (ported as `render_view.cell`) picks
them, see FILE_FORMATS "Map tiles and ant sprites"; `f_02fdb` draws a background tile only, `f_02c21`
a tile with a sprite (sheet by view, sprite = id & 0x7F, recoloured). Rows past b 63 wrap to a + 64.
The tile sheet is loaded by `f_02756` (yard / house) and the sprite sheets by `f_028b6` per video mode
(DS:5A97); render paths by G:1102 (1 EGA/VGA planar, 2 and 3 other adapters).

### The redraw draws from the game's RNG (`f_03de7`)

**Important for a faithful remake.** The map window's full redraw `f_03de7` draws the spider overlay
(see FILE_FORMATS / render_view.spider_frame) and then, **only when the patch is visible (T:07B2 != 0)**,
times a small spider animation with the game's LFSR:
```
    if G:047E == 0 and clock >= T:098E (32-bit):
        T:098E = clock + Rand64 + 180
        Rand2 == 0: G:0D6E = 1, T:0992 = (T:0992 + 1), back to 0 at 5    else: G:0D6E = 0
    if the spider's state G:0FB8 == G:0EB4 and <= 4:
        if G:0D6E: draw G:10B4 handle [5 * state + T:0992] at the spider's position + heading * 8 (f_0696a)
    else: T:098E = clock + Rand32 + 30; G:0D6E = 0; G:0EB4 = state
```
So in the original, whenever this redraw runs (the window is shown and gets redrawn, which depends on
the UI), the simulation's random sequence shifts. The verifier never sees it because the patch stays
hidden. A remake that must match the original tick for tick has to call this at the same redraws; a
remake that only needs to play the same way can draw these from a separate generator.
The spider's fangs (`f_04666`, drawn right after its legs at 0x0420a) take one more draw: Rand(4)
picks their offsets (tables T:09E4 / T:09E8 / ...) when the spider's state G:0FB8 > 1 or G:06AC >= 6,
on every redraw that draws the spider, whether or not the patch is visible.

### The spider composite (`f_03de7`; rendered by `render_view.spider` / `spider_lines`)

`f_03de7` is not the whole map redraw: it redraws the 7 x 7 cells around the spider (block origin
G:37D2 / G:37D4) into an off-screen buffer (G:1F26) and draws the spider on it.
- Body: bitmap 1000 + G:1004, or 1050 + G:1042 in state 5.
- Except in state 5: the legs `f_04c44(x, y, heading G:1004, frame G:1042 & 7)` and the fangs
  `f_04666(x, y, heading)`, at the spider's position (G:0F12, G:0F34).
- Both are polylines: `f_045a5` moves the pen, `f_045fa` draws a line (`f_16b58`), with coordinates
  scaled by 3/4 on video mode 2.
- Each heading has its own program, a jump-table case: 8 legs of move + 2 lines for `f_04c44`, and
  2 fangs of move + 2 lines for `f_04666`. Each point is the argument + a signed T byte, indexed by the
  frame (si), the opposite-phase frame (di = (si + 4) & 7, the other side's legs, mirrored in x), or
  fixed.
- `tools/re/polylines.py` extracts the programs from the user's EXE into the git-ignored
  `build/spider_legs.json`.
- Colour 15; the fangs are colour 1 when the player is the spider (G:0A06 == 1).
- Then the spider's remarks (STR# 1210 = G:10B4, see the timer above) go through the balloon routine
  `f_0696a`.

### The map window (`f_6efd6`; rendered by `render_view.render_map`)

The small "Map" window draws one colour byte per cell into an image 128 bytes wide (64 for a nest),
stretched to G:3856 x G:3858 px per cell (4 x 4 at 640 x 480) by the video driver (DS:914C). Its
content is T:07C8:
- 0: "Draw map - yard", which calls the fatal-error routine `f_1c62c`. The map window has no yard.
- 1, the surface (`f_6e892`): an occupied cell gets T:046E[occupant >> 3]; a free one gets
  T:030E[tile], or T:039E[tile] in the house.
- 2 / 3, the black / red nest (`f_6ec6e`): the yellow ant 1, red ants 3, black ants 15, else
  T:04A6[dirt >> 2].
- 4..8, the black nest marker, black trail, red nest marker, red trail and alarm maps (`f_6eb66`):
  each map cell is 2 x 2 bytes, v ? 0x10 + (v >> 5) : 0x0B.
- Bytes 0x10 and up are dither patterns (decoded 2026-10-19; `MapRenderer.DitherIndex`). The image goes to
  the screen a row at a time through the 16-colour driver's converter (`f_6e830` → G:38B8 = 0x31260 for 128
  wide, G:38BC = 0x31397 for 64): colour byte c is four plane bytes at DS:1F9E + 4c (static; 0..15 are
  solid, 0x10 = ff 55 00 55, 0x11 = ff 55 00 55, 0x12 = ff 00 00 00, 0x13 = 55 aa 00 00, 0x14 = 00 ff 00
  00, 0x15 = aa ff 00 00, 0x16 = ff ff 00 00, 0x17 = 55 55 aa 00). A cell is 4 x 4 px; two neighbouring
  cells share each plane byte (the even one its high nibble, the odd one its low nibble, a bit per pixel
  from the left); scanlines 0 and 2 take the bytes as they are, 1 and 3 rotated left by one: checkerboards
  from yellow through orange to red for the scent maps.

These are the 16-colour tables, used when the video mode DS:5A97 has bit 0 clear (8 in the
snapshots). The other set (T:061E, T:04CE, T:054E, T:0656) holds 256-colour values.

**The screen is one paint behind the step.** `f_6efd6` reads the OCC grid when it runs, and it runs again
after each simulation step, so the window on screen shows ants where they were before that step's moves and
an emulator capture can fall between the step and the repaint. Measured on the `surface` capture
(2026-11-07, B16): the red-ant cells on the screen are exactly the OCC grid one step earlier — at the
capture instant memory held (103,4) (104,37) (105,5) (106,27) (118,25) (121,31) (124,23) (125,21) (125,22)
and the screen held the previous step's (104,3) (104,38) (105,26) (106,5) (117,26) (122,32) (125,20)
(125,22) (125,23). Eight of the nine ants moved one cell, which is that capture's whole 256-px diff: a 4 x 4
cell left behind plus the same cell at its new position, 32 px each. The State is self-consistent at that
instant — the OCC grid and the ant arrays (SX / SY / STYPE) agree cell for cell and type byte for type byte
for all 25 surface ants — so a `--state=` render cannot reproduce it: it draws memory as it is. This is the
first thing to check before calling a small diff in a moving picture a render bug.

With DS:2994 set, only the ants are redrawn over a cached background (G:10E2). After the image, when
the window shows the surface and DS:2994 is 0:
- the small spider (`f_6f505`): bitmap 1100 + G:1004 at (its cell × 4 - 3) + the window's corner
  G:10D2 / G:10D4, while G:0F0C != 0;
- the human (`f_6f5e1`): while T:0C3E, the sneaker 1200 + T:0C30 at (G:03E0, G:046A) × 4, and while
  mowing (T:0C28 3 or 4) the mower 1210 + (T:0C30 & 1) at (G:0470, G:047A) × 4.

On a 320-wide screen the factors halve.

**The caption** (item 0x101) is `STR# 1000[T:07C8]` and only `f_01058` sets it — reached from `f_01781` (a scent layer
or view change), from the tail of `f_01aec` (the toolbar's view buttons 0x106..0x108, which pass 1..3 through
`f_01781` anyway) and from `f_01823` (the yard view modes, via the View menu `f_6e26d`). Opening or fronting the
window (`f_2148a` / `f_215a5`) does not touch it. It is drawn in **font 0, the PC BIOS font** fetched through INT 10h
AX=1130h, opaque in the item's background: the dark plate is 8 px per character, so "Black Nest View" is a 120-px box
in the 512-px bar. That box is what a capture taken without a ROM font stand-in shows — an empty plate of exactly
8 × length px (see B12 / B15 in ROADMAP), not a missing caption.

### The yard window (`f_702f7`; rendered by `render_view.render_yard`)

`f_6fc36` → `f_6fac7` → `f_6fa6c` → `f_702f7(mode)`, from the yard map (`f_7650c` / `f_01823`) and the
win screen (`f_72750`).
- **Background** (window 25, FILE_FORMATS "Window layouts").
  - The yard view (G:035C 0 / 1) shows the window's pictures: the house 7000 (item 0x1903) and the
    lawn 7003 (item 0x190F), whose grid is the patch grid, above the toolbar 7010 (item 0x1904).
  - The colony views (G:035C >= 2) get the grid strips 7020..7022 from `f_6fac7` on 640-wide 16-colour
    screens, from (item 0x1902's left, item 0x1914's bottom) = (64, 148); otherwise 7002.
  - The yard origin G:10D2 / G:10D4 is item 0x1902's corner + (1, 0) = (65, 83) (code at 0x01002),
    so the grid's top is at yard y 65.
- **Sprites.** The actors live on a sprite layer (G:10DA): `f_26968` creates a sprite, `f_26f2d` moves
  it, `f_26bbc` removes it, `f_272c2` composites. The handles are DS:2A2A.. per actor, and G:38CA.. /
  G:38E8.. / G:390A.. for the raindrops and the swarms.
  - **The dog's clip / sprite-layer path draws the full sprite — no tail clip** (B20, #103; traced
    2026-11-18 in the emulator: `f_6feb3` → `f_26968` / `f_26f2d` → `f_272c2` → the type-3 picture draw).
    The dog-draw `f_6feb3` computes the position, then branches on `DS:2A30`: `-1` → `f_26968` creates a
    sprite-layer record (the returned handle is stored into `DS:2A30`); `≠ -1` → `f_26f2d` updates the
    existing record. So `DS:2A30` is the dog's per-actor record handle — a create-vs-update selector, not a
    clip parameter. `G:10DA` / `G:10DC` name the shared sprite layer: the composite `f_272c2` (from
    `f_702f7` via `f_6fa6c`) resolves it with `f_18d44(G:10DA, G:10DC)` (the `G:10DC == 0xF0F` handle-table
    path in `f_19182`) and draws every record in it. Each record's bitmap (`[rec+0x28]`) is resolved to a
    picture object and blitted at the record's `([rec+0x16], [rec+0x18])` through the picture's own draw;
    the dog's frame 8510 is a type-3 picture (live at flat `0x36a67`), 20 px wide. That draw is a 4-plane
    blit of the **full picture width** — for 8510 it writes 3 byte-columns, the last masked to the picture's
    own 4 trailing bits. The word passed as the "clip" (`[rec+0x16] & 7` = `x & 7`) is only a **sub-byte bit
    offset**, a rotation applied to both the source bytes and the last-byte mask to land the sprite on the
    pixel grid; it removes no column. **Consequence:** a from-`yard.state` render draws the full 20 px,
    including the right-hand column — bitmap 8510 has palette 10 (brown) in column 19, rows 2..5, the 4 px at
    screen (288, 195..198) that B18 found missing in the capture. B18's missing tail is the one-step paint
    lag, confirmed: the path is a no-op for the tail, and the clip always covers the full sprite.
- **Actors, mode <= 1**, each at its position + per-frame offsets from signed-byte tables in DS:

| Actor | Routine | Shown while | Bitmap | Position |
|---|---|---|---|---|
| cat | `f_7004e` | G:0254 | 1300 + G:0244 | (G:02BE, G:032C); frames 10..19 + DS:2AA4 / 2AA8[f], 20.. + DS:2AA2 / 2AAC[f] |
| dog | `f_6feb3` | T:0C44 == 0 | 8500 + G:04E4 | (G:04BE, G:04C6) + DS:2A8E / 2A9A[f] (f < 12), else DS:2A42 / 2A46[f] |
| human | `f_6fc6e` | T:0C32 >= 0 (and T:0C28 != 0 when mode 0) | 8000 + T:0C32 | (T:0C2C, T:0C2E) + DS:2A56 / 2A62[f] (< 12), DS:2A5A / 2A5E[f] (< 24), DS:2A12 / 2A1E[f] (< 200); speech bubble: line G:10BC of STR# 1200 while G:10B0 (cleared when clock3 passes G:109C) |
| mower | `f_701a5` | always | 8800 / 8801 / 8802 | parked at (0x62, 0xB5); while mowing (sound 0x24 per frame) 8801 at the human + (0x13, 0xF) on frames 0x67..0x69, 8802 at + (-0xF, 0xF) on 0x6D..0x6F, hidden on the others |
| bird crossing | `f_6ff93` | G:10A0 | 1250 + G:108C | (G:10AC - 10, G:10BA - 3), + (1, 2) on frame 1 |
| "For Sale" sign | `f_70126` | T:0C44 | 1260 | (0xAA, 0xBA) |
| raindrops | `f_70601` | rain G:0352 | 7005 | 15 drops at (Rand(400) + 50, Rand(150)), new every frame |
| mating swarms | `f_706d0` | rain G:0352, T:07C8 == 0 | 7006 / 7007 | G:07C8 black / G:0850 red queens (16 at most) around the player's patch corner (G:103C = 28 col - 10 row + 0xB2, G:1048 = 10 row + 0x2E) + offsets G:0F46 / G:0F84 (black) and G:0FC6 / G:1008 (red). Each frame they jitter by Rand(3) - 1; when one strays (`f_70a50`) it resets to Rand16 - 10 (black) or 0 (red) |

The actor `yard.py` calls the bird (G:0254, `bird`) is drawn with the cat frames 1300..1329; the bird
proper is the crossing (G:10A0, 1250).

- **Colony views, mode >= 2** (T:0C20 = 0). For each patch (col, row), with corner
  (28 col - 10 row, 10 row):
  - Strat (mode 2, `f_70b82`): a parallelogram, corner + the word pairs DS:2A42 + 4i (169, 67 ...),
    filled with DS:2AD2[k] and outlined with DS:2ACA[k] (`f_1faa6`); k = 0 black only, 1 both, 2 red
    only, 3 none.
  - Graphic (`f_70cf5`): bars (strength + 3) >> 2 tall standing on 10 row + 0x47, 9 px wide; black
    (0x0F) at x + 168, red (0x23) at x + 180 (`f_1d28d`).
  - Colour codes go through `f_1b4ed(c) = (c & 0xF0) | DS:41C0[c & 0xF]` (DS:41C0 is the identity): the
    low nibble is the palette colour, the high nibble a pattern that the VGA driver's fills ignore.
  - The parallelogram (`f_1faa6`, decoded 2026-10-19; `YardRenderer.DrawColonies`): rows p0.y .. p2.y - 1,
    each from the left edge to the right one - 1, the edges 16.16 fixed point starting at p0.x / p1.x and
    stepping by -((p0.x - p3.x) << 16) / height, -((p1.x - p2.x) << 16) / height (`f_2cd42`). The pen
    `f_9128(fill, frame)` keeps DS:3DE0 / DS:3DE2. A fill of -1 draws through DS:913C; fill == frame a solid
    row (DS:9134); else DS:9138 (0x31BF2) with pattern 0x20 & 15 = 0: the 8 patterns at DS:41D0 (16 bytes,
    row (2y & 7)), drawn in two passes, DS:3DE0 where the mask bit is set and DS:3DE2 where it is clear.
    Pattern 0 is 55 / AA: the fill colour where x + y is odd. With DS:2AD2 / DS:2ACA = (0x0F, 0x0F), (0x13,
    0x1F), (0x23, 0x23), (0x48, 0x48), only "both colonies" is a checkerboard (red and black).

The window's items go to `f_6f7f0(event)`, a jump table at 0x6f815 (cs base 0x6f7f0, item - 0x1902):
- 0x1902, the yard picture: `f_70edf(event)` (the patch click);
- 0x1907 Patch: `f_013ff`; 0x1908 House: `f_01823(G:035C < 2 ? G:035C ^ 1 : 0)`; 0x1909 Strat:
  `f_01823(2)`; 0x190A Graphic: `f_01823(3)`;
- 0x190B MATE: outside the Full Game sound 1 (0x7E) and the timed message `f_15e2c(STR# 1010 [15],
  0xB4, 1)`. Otherwise n = G:0AF2 + G:0AF4 (males and new queens, the census's castes 3 / 4), minus 1
  when the yellow ant is one (G:04C2 0x40 or 0x20); n <= 0: sound 1 and STR# 1010 [5]; else the black
  mating flight starts, G:08DC = 0xC8, with STR# 1010 [6];
- 0x190D AUTOMATIC: T:02C0 = 1 (the sim settles the swarm's queens, `yard.py`); 0x190E MANUAL: T:02C0 = 0;
- 0x1910 PLACE: the buttons' states, `f_01efa()`, then a redraw `f_6fc62`. `f_01efa`: with no queens
  (G:07C8 < 1) sound 1 and the timed message STR# 1010 [7] (Full Game) or [16]. Otherwise T:02C0 = 0 if
  it was 1, the range is columns G:07CA +- 3 and rows G:07CC +- 3 clamped to 0..11 / 0..15, and a loop
  shows [8] until a click, tracking the patch under the mouse with `f_70edf`'s arithmetic (G:07BC /
  G:07BE follow it inside the range, and `f_2f708` highlights it unless it is the player's own patch;
  leaving the yard area, `f_23612() == 0`, ends it). A click out of range: [10] for 0x78 ticks and sound
  1. In range: voice 0x2AFB, G:07C8 - 1, T:00A4[col * 16 + row] + 1, G:0A90 + 1, G:0C20 = 1,
  `f_01325(1)`, `f_2f6e0(0x10F8)`, [9]; done when no queens are left. The loop repeats while Shift is
  held (0000:0417 & 3); an out-of-range click with Shift also calls `f_011e5(0x1E, 0)`.
- 0x1911: the help overlay 0x1906.
### Event markers (recorders ported: `simant_ref/markers.py`, verified by `test_markers.py`)

While the patch is visible (T:07B2), the simulation reports four kinds of events; the port sends them to
`st.player.effect` with (a, b, view):

| kind | Recorder | Reported by | Gate | Recorded a, b, view | Latched by the animation |
|---|---|---|---|---|---|
| brood | `f_0678a` | N_Brood f_7a360 / red f_0fe16 (a brood hatches) | G:0EF6 | G:0852, G:0854, G:0ACA | G:08DE, G:08E0, G:0AD8 |
| fight | `f_06802` | f_7a126 / f_0fbdd (nest fights), f_0a871 (surface) | G:0F06 | G:08EC, G:08EE, G:0AEA | G:09F2, G:09F4, G:0B06 |
| queen | `f_0687a` | N_EggLaying f_7a490 / red f_0ff0f | G:0F10 | G:0A02, G:0A04, G:0B08 | G:0A8A, G:0A8C, G:0C3A |
| rest | `f_068f2` | f_79ec5 / f_0f9de (nests), f_09018 (surface) | G:0F2E | G:0AA2, G:0AA4, G:0D68 | G:0AB2, G:0AB4, G:0D9A |

A recorder acts only while its gate is 0 and the spot is on screen. `f_06725(view, a, b)`: `view` is
the view shown (G:032E), G:0508 <= a < G:0508 + G:10E0, and G:050A <= b - 3 with b < G:050A + G:10DE,
all signed.
- If the spot is the one the animation has latched, the gate counts up.
- Otherwise it records a, b and view.

The animation `f_06a4d` latches a recorded spot (its gate then becomes non-zero), draws there and times
it with the clock (see HANDOFF step 9). SimStep clears the gates and records when the patch is shown.
Since the verifier's patch window is never on screen, the full-tick checks never see these writes. A
remake that shows the window should call `markers.record` from its effect hook.

### The Efficiency Score window (window 24, `f_71576`, main-window command 0x114)

It runs the rating `f_70fb0` (`game.rating`): the score goes to G:0ADA (32-bit), the 8 parts p[] to a
local. It fills the window with `f_2318a` (number) / `f_23943` (formatted text):
- the colony fields 0x1802..0x1805 (Colony Health, Foraging, Eggs Hatched, Fights Won) = p[0..3];
- the universe fields 0x1806..0x1809 (Colonies Started / Held, Yard / House Filled) = p[4..7] as
  "%d%%" in the Full Game (G:0EAC == 2); otherwise STR# 1800 (G:0368) entry at +0x40;
- the bottom lines:
  - experimental mode: 0x180A / 0x180B are STR# 1800 entries at +0x44 / +0x48;
  - otherwise: 0x180A = STR# 1800 [+0x34] + the game mode's name (STR# 1001 = G:0324, index G:0EAC)
    + STR# 1800 [+0x38], and 0x180B = the score through the format at DS:2B16;
- the caption 0x180C = STR# 1010 (G:034C) entry at +0x38.

The lists hold 4-byte far pointers, so +n is entry n / 4: STR# 1800 [13] "Overall ", [14] " Score",
[16] "N.A.", [17] / [18] "Score not available" / "in Experimental Game"; STR# 1010 [14] "Click here to
continue". DS:2B16 is "%ld". (An earlier version of this note said STR# 1020; G:0368 is STR# 1800, see
the handle list under "Speech balloons".) The remake draws this window (`Main.cs`, Efficiency Score).

It then waits for a click.

### The yellow ant's menu and commands (`f_67e93` → `f_76cb9`; ported: `simant_ref/commands.py`, `test_commands.py`, all of them)

`f_67e93` opens a pop-up menu (`f_2379b`) and turns the choice into a command through a byte table in
DS:

| Window | Who | Entries → command |
|---|---|---|
| 32 (4504) | the spider (G:0A06 == 1) | Chase 0x0A, Hunt 0x0B (Alt held: 0x0C), Exchange 6, Help 0 (DS:23DA) |
| 8 (4502) | a queen (G:04C2 == 0x40) with T:0C24 == 0 | Dig Hole 8, Start Brood 9, Help 0 (DS:23D0) |
| 7 (4500) | any other ant | Recruit 5 → 1, Recruit 10 → 2 (Shift held: 3), Release 1/2 → 4, Release All → 5, Exchange 6, Help 0 (DS:23D4) |

Window 6 (6000) is the scent-layer menu (Off, Alarm, B-Nest, B-Trail, R-Nest, R-Trail: T:07BE, `f_679c0`).

`f_2f906` → `f_76cb9(command)` (only while G:0A06 <= 1), through a jump table at 0x76CE3 (cs base 0x74FE0):
- 0: help (`f_76eb5`, UI: window 26, an empty stub in the DOS version; see "The SimAntipedia").
- 1 / 2 / 3: voice `f_00ea1` + `f_13f32(5 / 10 / 1000)`, recruiting n.
  `f_13f32` walks the surface ants from the last down, then the black-nest ants. Each live black ant
  of caste 2 or 6 that is not in state 6 gets state 6 and e = 0, until n are recruited.
- 4 / 5: voice + `f_14005(0 / 1)` (release half / all; ported: `player.release_recruits`).
- 6: Exchange, `f_11b21`. It toggles the cursor mode G:105E = 0x0A: G:048E = G:047E, then `f_2f816(1)`
  pauses; `f_11b5f` cancels, with G:105E = -1 and `f_2f816(G:048E)`. The next map click (`f_74fe0`)
  calls `f_11b81(view or 1, a, b)`:
  - G:1074 = 1, then `f_11c18(view, a, b)` makes the swap (`commands.exchange`, returns 1 / 0):
    - The yellow ant's leftover type: caste c = (G:04C2 & 0x78) >> 3 and e = 0. If bit 3 of the type
      is set, castes 5 / 9 map through the load table T:0094[c]; caste 1 keeps e = T:0C22.
    - **An empty cell** (GetOccupant <= 0): only on the surface (view 1), and only within squared
      Distance 0x200 of the spider's cell centre (a * 16 + 8, b * 16 + 8) vs (G:0F12, G:0F34). The
      player becomes the spider; G:0A06 is not checked, so a yellow ant can do it too.
      1. `f_114bd` adds an ant at the yellow ant's spot with type (G:04E2 & 0x80) | G:0496 | c << 3,
         state 9 for a queen (G:04C2 == 0x60, plus her second cell behind her, type + 8, e 0), else 0.
         If either add fails (list full): return 0.
      2. `f_119b4(..., 0)` then clears the yellow ant's cells, so the occupancy of the ant just added
         is 0 again (as in the original).
      3. The spider state: G:0FFC = -2, (G:0F42, G:0F7E) = (G:0F12 >> 4, G:0F34 >> 4),
         G:0A06 = 1, and G:0FB8 = G:06AC = G:04E2 = 0.
      4. `f_2f820` → `f_757dd(view, those)` (`player.stop_action`), health 100 (`f_12d43`), return 1.
    - **The player itself** (`f_134b8`, `debug.player_at`) or a yellow cell (0xFE / 0xFF): return 1,
      nothing changes. Exchange still ends with sound 0x0F.
    - **A queen's cell**:
      - caste 12: her second cell is behind her, (a, b) + dir[(o & 7) ^ 4];
      - caste 13 (the second cell): the queen is at (a, b) + dir[o & 7]. (a, b) and o move to her, and
        c = 12.
      i = `f_11327(view, a, b, o)`, the second cell's i2 likewise. i < 0: return 0.
    - Taking the clicked ant (o) needs:
      - Shift + Alt (BIOS flags 0:0417 & 8 and & 3) for a red ant (o & 0x80);
      - Shift + Alt **and** T:0798 for caste 0 (brood), 10, 11 or > 13.
      Otherwise: return 0. Castes 5 / 9 become T:0094[c] (heading kept); caste 1 copies its e
      (`f_10fcd`) into T:0C22.
    - **As the yellow ant** (G:0A06 == 0): the leftover ant's type is c << 3 | G:0496 | (o & 0x80),
      with the clicked ant's colour. The red check comes before the caste check.
      1. Redraws (`f_0250e`).
      2. The clicked ant (and i2) is zeroed in its list (`f_11121(view, i, 0, 0, 0, 0, 0)`).
      3. `f_114bd` adds the leftover ant at the yellow ant's spot (a queen: state 9, with the second
         cell); a failed add returns 0, after the clicked ant was already removed.
    - **As the spider** (G:0A06 != 0): the same checks, then the clicked ant (and i2) is zeroed. Nothing
      is left behind.
    - Both then: G:04E2 = o & 0x80, G:049A = G:0A06 = G:06AC = 0, health 100,
      `f_119b4(view, a, b, o & 0x78, o & 7, 0xFF)` (the new yellow ant, type o & 0x78, heading o & 7),
      and G:0502 = G:0496 if G:04C2 < 8. Return 1.
  - On 1: cancel the mode and play sound 0x0F; as a queen also the redraw `f_03391` and the voice line
    0x2AFE (the wait between them, `f_00f1d`, always returns 1 in this build). On 0: sound 1.
  - `test_commands.py`: 32 click scenarios, each from every snapshot, through both `f_11c18` and
    `f_11b81`. They click surface, black and red nest ants, brood and odd castes, queens and their second
    cells, empty cells, the yellow ant itself and cells around the spider. Each runs as the yellow ant, as
    the spider, as a queen and as castes 1 / 5 / 9, with and without the cheat keys, and with full or
    nearly full lists.
- 7: `f_76a37(G:104E == 0, 0)` (alarm mode toggle; ported: `player.alarm_mode`).
- 8: Dig Hole. On the surface `f_13644(view, a, b)` (`player.act_on_cell`); if that returns -1, or off
  the surface: sound 1.
- 9: Start Brood. In the black nest at depth >= 3: `f_0125f(6)` and
  `f_758e0(view, a + 2 dx[h ^ 4], b + 2 dy[h ^ 4], 0x10, 1)` (`player.queen_scene`, founding); else
  sound 1.
- 0x0A: Chase, `f_11ac1`: like Exchange with cursor mode 0x0B. Map clicks on the surface while the
  player is the spider go to `f_756a6(a, b, k)` (`commands.spider_click`):
  - k < 1 outside Chase mode: walk to (a, b). G:0FFC = -2, G:10AE = -1, G:0FB8 = 0, (G:0F42, G:0F7E)
    = (a, b), G:0A8E = k.
  - Otherwise, an ant on the cell (`f_11327`) becomes the prey: G:10AE = its type, G:0FFC = its index,
    G:0FB8 = 2. In Chase mode also sound 0x0F, G:06AC = 6, and the mode ends.
  - An empty cell: in Chase mode sound 1, otherwise walk.
- 0x0B: Hunt. G:06AC == 7 ? 0 (sound 2, pitch 0x56EE) : 7 (sound 2, pitch 0x2B77).
- 0x0C: Hunt with Alt. G:06AC == 8 ? 0 (sound 2, pitch 0x56EE) : 8 (sound 0x29).

### The tool palette (window 9, `f_680a4`)

- Window 9 (bitmap 5000) has eight hotspots, 0x902..0x909: a click selects the map tool G:104C =
  item - 0x902 (see "Map tools").
- (Audited 2026-11-01 against the original in the emulator, `tools/re` scenarios.) The loop `f_680a4(x, y)` runs
  while the button is held (`f_202b8`: after a grace of 2 clock ticks, a release ends it; let go sooner and the
  menu stays open until the next press) and returns `cur`, the entry the pointer was last on (G:104C at first), so
  letting go outside every entry still takes the last one; the caller then does `f_2f8a2(cur)`. The game does not
  run meanwhile (the sim's RNG is frozen). The pointer moving onto an entry 1..6 opens that tool's options palette
  at once, no hold time (windows 12, 15, 16, 17, 13, 14 from the table DS:2438; right of the entry, or left of it
  when `w + right + 1 >= DS:3DB2`, at the entry's top; the current option highlighted), closing the old one; moving
  onto an option stores it in T:07B6 + cur straight away (hover, not release). Entry 0 and 7 have none. Keys: 0x0D
  returns `cur`, 0x1B returns -1 (`f_1f610`).
- The option palettes by their bitmaps: window 12 (5001) Walls / Rocks = tool 1, 15 (5002) Dig / Fill = 2,
  16 (5003) Black / Red = 3, 17 (5004) 1 Piece / 20 Pieces = 4, 13 (5005) Black Nest / Black Trail / Red
  Nest / Red Trail / Alarm = 5, 14 (5006) Spray / Stream = 6.

The palette is a pop-up of the Experimental menu: `f_67010` (Map toolbar 0x117 via thunk 0x2f88e), placed
centred over item 0x117 and 4 px above it, and `f_67a24` (the Edit window's button 7, thunk 0x2f744), the same
code placed at that button's right edge + 2, its top (`f_252d8(7)` = the rect of item 7 of window 0). By the game
mode G:0EAC (any other, the tutorial's 0, does nothing):
- 1: window 10 ("EXPERIMENTAL MODE", `f_2379b`: a release on its entry, or a press on it, picks; a press outside
  closes it after a quick click; a release outside after a hold leaves it open). Choosing it: `f_2f8a2(G:104C)`,
  G:0EAC = 3, `f_11918(view, a, b, G:04C2, G:0496)` lifts the yellow ant off the map, G:0A06 = 2, `f_0cdb0()`,
  the caption `f_03bfd`, sound 2 (0x7E). No `f_25ca8`: the buttons keep their bitmap (5107).
- 2: window 11 ("Experimental Mode is not available in the full game.").
- 3: window 9 through `f_2f8b6` (`f_680a4`). Entry 7 (Start Game): G:0EAC = 1, **`f_2f8ac` = `f_6b7d0`** (the
  yellow ant placed again: `NewGame.PlaceYellow`, health 100, alarm trail off), and on the surface (G:032E == 1)
  `f_119b4(..., 0xFF)` puts the yellow ant back, `f_03bfd`, voice 0x2AFB. Then `f_2f8a2(choice)` (G:104C = 7
  after Start Game), and the open Edit / Map windows' buttons (items 7 / 0x117) get bitmap 5100 + G:104C
  (`f_25ca8`).
- Checked in the emulator 2026-11-01: `test_experimental.py` (enter, then start, in eight contexts, byte for byte).

### The Ant Info window (window 29, `f_67c1c(a, b, view)` via thunk 0x2f8fc, map tool 0)

- o = the occupant byte of the cell (surface occupancy, or the black / red nest cells); 0: return -1.
- Window 29 opens at ((a - G:0508 + 1) * DS:19BE + G:110C, (b - G:050A - 1) * DS:19C0 + G:110E). It
  moves left by a cell + its width if it would pass the screen's width (DS:3DB2), and up to fit the
  height (DS:3DB4).
- Lines (font 2), with caste = (o & 0x78) >> 3:
  - 0x1D02: STR# 1100 (G:106E) [o & 7] for brood (caste 0), else STR# 1101 (G:1078) [caste];
  - 0x1D03: STR# 1102 (G:1086) [state of the ant found there: SurfaceAntAt / BlackNestAntAt /
    `f_0ef3c`; 0 if none];
  - 0x1D04: STR# 1103 (G:1096) [caste].
- It waits for a click and returns o.

### The population report (main window items 0x119..0x11E, `f_6eea5`)

- 0x119 / 0x11A: the black / red populations G:0330 / G:0350 as text (formats DS:29D8 / DS:29DC).
- Gauges `f_23971(item, 16.16 fraction)`:
  - 0x11B: black health G:10BE / 100;
  - 0x11C: red health G:01FE / 100 (0 when there are no red ants);
  - 0x11D / 0x11E: each population / max(1, black, red).

Holding the button on the report (command 0x118 → thunk 0x2f9ce → `f_7179d`) shows window 23 (bitmap
14002, rows Larvae, Workers, Soldiers, Males, New Queens, Queens) until the button is released (G:1074 = 1
meanwhile). In item 0x1702, font 2 (font 0 on a 320-wide screen), for caste i = 0..5: the black count
G:0AEC[i] as text at the item's left, the red count G:0AFA[i] one font line below, and for i > 0 a bar each
from x = left + 4 x the widest digit + 2, of length count x (right - that x) / M (32-bit), M = the largest
count of castes 1..5 of both colours (at least 1), from 1 px below the text line's top to 2 px above its
bottom. The rows share the spare height (height - 12 font lines, + 3 at 640 x 480) in fifths, the remainder
added a pixel at a time; the last row sits 1 px higher. The remake draws it (`Main.cs`).

### The History Window (window 21, `f_792d2` handler, `f_795ec` plot)

- Buttons 0x1503..0x150C toggle the plotted series (`f_79373`), up to 4 at once (DS:2EF0[4], 0x8000 =
  empty). 0x150D shows the help overlay 16001, and a click on the graph area 0x150E redraws.
- Series s plots its black and red data: far pointers T:082A[(s & 1) * 5 + (s >> 1)] (black) and
  T:0852[...] (red), each a 64-entry ring (the history graph in `world.py`: head G:04F4, count T:0828).
- The graph's height H is item 0x150E's height - 16 (8 px margin top and bottom); the width is its
  width - 0x40.
- Scale: M = the largest value of both rings over the last T:0828 entries.
  - If M * 2 < H: y = bottom - v * mult, with mult the largest integer that keeps M * mult < H.
  - Otherwise: y = bottom - v / div, with div the smallest that brings M / div <= H.
- (decoded 2026-10-19, `Main.DrawHistoryWindow`) `f_795ec(series, no_label, slot)` plots one line per
  series: ring T:082A[k], k = (s & 1) * 5 + (s >> 1) (the 10 buttons are 5 measures x 2 colonies), scaled
  together with the other colony's ring T:0852[k]. The scale M looks at the newest T:0828 entries, from
  (G:04F4 - T:0828) & 63; the plot runs over all 64 ring slots from G:04F4 (the oldest, or never written) to
  G:04F4 - 1 (the newest, at the right; corrected 2026-11-01, it had started at G:04F4 - T:0828): point 0 at the
  graph's left, point i at left + slot + i * w / 64 (truncated toward zero); y as above (mult when M < H:
  the largest with M * mult < H; else the smallest div with M / div <= H; values not clamped). The lines go
  through the driver's DS:916C (0x32F69: left to right, the ends swapped if needed, both drawn; the longer
  axis steps every pixel, x when dx >= dy; the error starts at 0, adds the shorter span and moves the shorter
  axis once it passes half the longer one, then loses the longer span; x < 0 is skipped). The colour is
  DS:2EE8[DS:8C26[s]] (0x43, 0x46, 0x49, 0x45). The
  Each call draws its line and then its label (a later series' line runs over an earlier label): in font 3 at
  the last point (point 63), its top half the text height above it, framed 1 px out in the same colour
  (`f_9128(colour, 0, colour)`), clipped by the window. **The flag (bp+8) picks the text** (corrected
  2026-11-01): flag 0 is the series' name, STR# 1050[k] (G:02BA, loaded by f_07680: BPop, BFood, BHealth, SFood,
  Expired, RPop, RFood, RHealth, Eaten, Killed), flag 1 the newest value "%d" (DS:2EFA). The normal draw
  `f_7959a(3)` (also after every new sample, `f_798c8`) clears the graph item to colour 0 (`f_22200`) and draws
  every slot with flag 0; a press on the graph (0x150E, `f_792d2`) clears the same way, draws with flag 1 and waits
  for the button to go up (`f_20262`), then redraws with `f_7959a(3)`.
- The series (`f_79373`): four slots DS:2EF0 (0x8000 empty, all empty at start-up); a new series goes into
  slot 0 and pushes the others down, a fifth evicts slot 3 (its button released); removing one closes the gap.
  Its colour DS:8C26[s] is the lowest free bit of DS:2EF8 (0xF at start), given back when it goes.

### Behavior / Caste Control triangles (windows 18 / 19; ported: `simant_ref/panels.py`, `test_panels.py`)

Each panel holds three 16-bit weights summing to 0xFFFF:
- behaviour G:049E / 04A0 / 04A2 = forage (apex), dig (bottom left), nurse (bottom right);
- caste G:0482 / 0484 / 0486 = breeders (apex), workers (bottom left), soldiers (bottom right).

The triangle is item 0x120D / 0x130D's rectangle (`f_07980`): apex (left + w/2, top), corners (left,
bottom) and (right, bottom). Its sizes go to G:3814 (w), G:3810 = G:3812 (w/2), G:380E (h) and G:382E
(32-bit (w/2 << 8) / h, not verified); the points go to G:3816 / G:3822. The marker is G:0358 / G:022E.

```
weights → marker (f_087c7), unsigned unless noted:
  y = top + (0xFFFF - v0) * (h - 2) / 0xFFFF
  k = w/2 * v0 / 0xFFFF;  m = w - 2k
  x = (v0 != 0xFFFF and m >= 3) ? left + k + (signed) v2 * (m - 3) / (0xFFFF - v0) : apex x;  x += 2
click → weights (f_086a1):
  dx = px - left;  dy = py - top
  v0 = dy > h - 2 ? 0 : (h - dy - 2) * 0xFFFF / (h - 2)
  k, m as above; m <= 2: v1 = v2 = 0
  c = dx - k: v2 = c >= m - 2 ? 0xFFFF - v0 : c <= 2 ? 0 : (0xFFFF - v0) * c / (m - 2)  (signed)
  v1 = 0xFFFF - v0 - v2
```

The redraws `f_07a57` / `f_07a19` (marker) run from InitColonySettings and from the drag handlers
`f_07d07` / `f_07ac1`, which loop on the mouse (`f_201f0`). After a change the caste weights become
the percentages T:07DA.. (`f_085f8`, `newgame.caste_targets`). The bar charts on the right (item 0x0C:
F D N / B W S) are drawn by `f_0839a` / `f_08255` (not traced).

The windows' handlers switch on the item id through jump tables (cs base 0x7980): the Behavior window's
`f_07d07` (table at 0x7d3b, item - 0x1203), the Caste window's routine at 0x7ae2 (table at 0x7af5, item -
0x1303):
- help 0x1203 / 0x1303: `f_2f74e(0x120e / 0x130e)`, the help overlay;
- Auto 0x1204: if G:0378 == 0, G:0378 = 1 (Caste: T:07E8); Manual 0x1205: if G:0378 != 0, G:0378 = 0
  (Caste 0x1305 at 0x7cde: T:07E8 = 0 only);
- Set 1..3 0x1206..0x1208: copy the 6 weight bytes G:049E into the slot of the current preset,
  T:0810 + 6 x DS:1B50, set DS:1B50 = item - 0x1206 and copy that slot back into G:049E; redraw, then the
  Manual path (G:0378 = 0). Caste: G:0482 ↔ T:07F2 + 6 x DS:1B4E, then the Manual path. The start-up
  slots are T:0810 = (0x9999, 0x3333, 0x3333), (0xFFFF, 0, 0), (0, 0xFFFF, 0) and T:07F2 = (0, 0x9999,
  0x6666), (0x7FFF, 0x3FFF, 0x3FFF), (0, 0xFFFF, 0), with DS:1B50 = DS:1B4E = 0;
- the triangle 0x120D / 0x130D: the drag;
- the corner boxes 0x1209..0x120B / 0x120F..0x1211 (0x7f06; Caste 0x7cce): DS:1B62 ^= 1 (Caste DS:1B64),
  then the chart redraw. `f_083d9(window, 0, flag)` (from `f_080d1` / `f_08255`) writes into items
  0x1209 + i the weight i as "%-ld%%" = (100 w + 0x3FFF) / 0xFFFF when the flag is set, else "%-ld" =
  (w x total + 0x3FFF) / 0xFFFF with total = G:0B12 + G:0B14 + G:0B16 (foragers, diggers, nurses) or, in
  the Caste window, G:0AEC. **The bars** (decoded 2026-10-19) in item 0x0C (l, t, r, b): bar i spans
  l + 2 i w5 .. + w5 (w5 = (r - l) / 5), from b up to top = b + w (b - t) / -65535 (`f_2cd42`, truncated);
  when top + 1 < b it is filled with DS:1B4A[i] (Behavior: 0x28, 0x2B, 0x27) or DS:1B46[i] (Caste: 0x24,
  0x26, 0x22) and framed in 0x0F (`f_1d28d`, `f_1d26d`), then (l, t - 1, r, top) is cleared with 0x40.
  The VGA driver's fill (DS:9134 → 0x33191) programs set / reset with the colour's low nibble only, so the
  pattern nibble of a colour code draws nothing in this mode (DS:5AAE = 0) and DS:41C0 is the identity:
  the bars are palette 8, 11, 7 and 4, 6, 2, the colours of their corner boxes.

### Speech balloons (`f_06a4d`; ported: `simant_ref/balloons.py`, verified by `test_balloons.py`)

The window draw `f_038a6` → `f_07128` → `f_06a4d` shows the ants' remarks at the spots the event
recorders found. It runs only while T:07B2 != 0 and T:07BE == -1. For each source, in the order fight,
brood, queen, rest:
- **Latch.** If the gate is 0 and the recorded a, b are >= 0, copy the record (a, b, view) to the
  latched globals and add 1 to the gate. Clear the source's timers (32-bit), and for brood, queen and
  rest also its shown flag.
- Nothing more happens while the gate is <= 0.
- **Timers** (only when G:047E == 0). For each balloon of the source, if timer < clock (signed 32-bit):
  re-arm it to clock + delay + const. Then a chance draw: 0 shows the next line (shown = 1, index + 1,
  wrapping at the list's end); anything else sets shown = 0.
- **Draw.** Every balloon with shown != 0 draws `f_0696a(a, b, view, style, list[index])` at the latched
  spot.

| Source | Timer | Delay | Chance | Shown, index | List (STR#), lines | Style |
|---|---|---|---|---|---|---|
| fight (black ant) | G:050C | Rand32 + 60 | Rand2 | G:1046, G:0F3C | G:020A (1220), 8 taunts | 0 |
| fight (red ant) | G:0732 | Rand32 + 60 | Rand2 | G:1064, G:0FF8 | G:0218 (1230), 8 taunts | 1 |
| brood | G:059A | Rand32 + 0xAA | Rand4 | G:104A, G:0F7A | G:021C (1240), 15 lines | 2 |
| queen | G:0620 | Rand32 + 0xB4 | Rand4 | G:1062, G:0FC0 | G:0234 (1250), 8 complaints | 2 |
| rest | G:07C4 | Rand64 + 0x78 | Rand2 | G:107C, G:103A | G:023A (1260), 8 remarks | 2 |

The fight timers are checked one after the other, then both balloons are drawn. The clock is read again
for the new value (`f_1bc34` twice).

**Drawing** (decoded 2026-10-18 night; remake `OpenSimAnt.Data/Balloon.cs`). `f_0696a(a, b, view, style, text)` only
queues: up to 6 (count G:1092) when the spot is in the Edit window (`f_06725`), with the cell centre in pixels a *
16 + 8, b * 16 + 8 (style 10 means a, b are pixels already: the spider's remarks) at G:04C8, the view G:04F6, the
style G:04E6 and the text G:04A6. `f_07134` sets font 2 and draws the first queued balloon still in view (one per
frame, then G:1092 = 0): `f_1629c(text, 0)` builds its bitmap, which goes at (x + 4, y - height - 4) over the map
cells it covers (redrawn into a buffer first; DS:15C4 marks them for the next redraw, so a balloon lasts one
frame unless queued again). `f_1629c` ("MakeBaloon", "BAD font in MakeBaloon") splits the text at literal
backslash-n (up to 10 breaks), measures it (`f_24dd9`), makes a (widest + 0x17) & ~7 by lines * font height + 16
bitmap and tiles it from 8 x 8 pieces in DS (16 bytes: 8 rows of the white inside byte and the shape byte; shape
without inside is the black outline): top-left 1D0A, top 1D2A (repeated, `f_169e0`), top-right 1D1A; for y = 8
while y < height - 8 left 1D4A, inside 1D8A, right 1D3A; at y = lines * font height + 6 bottom-right 1D6A,
bottom-left 1D5A, bottom 1D7A, and the tail: 1DAA in column 1 (pointing down-left; `f_1629c(.., 1)` would put
1D9A in the second-last column). Line i goes at x = 1 byte + ((-width) & 6) / 2, y = 6 + i * font height
(`f_2632e`, `f_16a36`). The height then shrinks by 1, by 2 for a single line; the result is converted for the
video mode (DS:5A97: `f_166f3` / `f_167c1`).

STR# list handles loaded at startup (`f_0765e`, part of the STR# loader 0x7691..0x77C5; these are
string lists, not bitmaps): 1000 → G:046C, 1001 → G:0324, 1010 → G:034C, 1020 → G:0360,
1050 → G:02BA, 1100..1103 → G:106E / 1078 / 1086 / 1096, 1200 → G:10A8, 1210 → G:10B4, 1220 → G:020A,
1230 → G:0218, 1240 → G:021C, 1250 → G:0234, 1260 → G:023A, 1900 → G:0328, 1800 → G:0368.
STR# 1000 holds window titles: entries 0..8 name the Map window's contents T:07C8 ("BackYard View",
"Surface View", "Black Nest View", "Red Nest View", the five pheromone maps), 9..12 the yard window's
modes G:035C ("Yard View", "House View", "Strategic View", "Graphic View"). `f_01058` (from `f_01781`) sets the
Map window's caption 0x101 to entry T:07C8 and the yard window's 0x1901 to entry 9 + G:035C (`f_2318a`), then
redraws them. The Edit window's caption 0x0001 is set by `f_03bfd` (from `f_725b6`, `f_7256f`, `f_67010`, `f_67a24`):
"SimAnt" + STR# 1800 [15] (" - ") + STR# 1001 [G:0EAC] (the game mode: "SimAnt - Quick Game").

### The Edit window's map region (`f_07558`)

The Edit window's map item 4 is 64,41 .. 416,362 (321 px), but the map is 21 rows of 16 px (G:10DE = 0x15,
336 px). Item 21 (64,362 .. 400,377) also has id 4. `f_07558` keeps its rectangle in G:1104 and makes the
drawing region the map rectangle G:110C plus G:1104 (`f_1ee65`: a list of rectangles ended by 0x8000), so the
21st row shows in the strip and only the corner 400,362 .. 416,377 stays the window's own.

### Keys and menu commands (`f_74386`, `f_76aeb`, `f_6e26d`, `f_8414_0000`)

The main loop's event dispatcher (8414:0000) sends events by type (high byte): 0 → `f_1250_0c0f`, 0xFA
(keys) → 8414:0383 (the low byte is the scan code, event +2 & 4 Ctrl, & 8 Alt: Ctrl+4 → `f_013ff` (back to the
patch), Ctrl+5 / 6 / 7 → 0xFD22..24, Ctrl+8 / 9 / 0 → 0xFD26..28, Ctrl+H → 0xFD15, Ctrl+I → 0xFD16; Alt+2 →
`f_76cb9(3)` (recruit all); Backspace → `f_76aeb(0x88)`, Tab → `f_2f8f2` (the Map window)), 0xFD (menu commands) →
thunk 0x2f992 → `f_6e26d`, 0xFE (open a pull-down menu) → thunk 0x2fa0a → `f_6d7e3`. The pull-down itself
is a generic text-cell menu (f_6d9a4 at 7d62:0384, "Menu data too long"; item n of menu m posts 0xFD00 + 16 m
+ n + 1).

**The menus are SHARED type 6 id 0** (FILE_FORMATS; corrected 2026-10-18 night: an earlier note said the labels
were nowhere). 82e5:0039 loads it (resource loader `f_2a53_0125(id, 6)`) into DS:6054 and turns its offsets into
far pointers. The menus, with their commands:

| menu (Alt / F key) | items → command |
|---|---|
| File (Alt+F, F2) | About 0x01 (`f_72931`, the about box 0x1F00), ---, New 0x03, Load 0x04, Save 0x05, Save As 0x06, ---, Quit 0x08 |
| Window (Alt+W, F3) | Edit 0x11, Map 0x12, Behavior 0x13, Caste 0x14, History 0x15, Info 0x16 (the SimAntipedia), Status 0x17 (the Efficiency Score) |
| View (Alt+V, F4) | Yard 0x21, House 0x22, Strategic 0x23, Graphic 0x24 (the yard window's modes G:035C), ---, Surface 0x26, Black Nest 0x27, Red Nest 0x28 |
| Options (Alt+O, F5) | AutoTrack 0x31 (T:07A8), Music 0x32 (T:07AA), Sound Effects 0x33 (T:07AC), Events 0x34 (T:07AE), Messages 0x35 (T:07B0), Silly 0x36 (T:07B2) |
| Speed (Alt+S, F6) | Pause 0x41, ---, Slow 0x43, Normal 0x44, Fast 0x45, Ultra 0x46 (T:07CC = 0..3) |

What the Options flags do (their readers in `segmap_3d57.tsv`): AutoTrack, the view follows the walking yellow ant
(`player.ui_follow` each step, f_7b661; the spider too, f_0ce63); Music, the songs (game over, f_71d95), the
long death animations (f_7c149 0x40 frames) and `sound_done`; Sound Effects, f_00ed8; Events, the yellow ant's
death messages (f_75d01, f_76707, f_7686d) and f_71b1a's message boxes; Messages, the advisor's status line
(`world.advisor` f_0e2ea returns early) and f_15e2c; Silly, the speech balloons (f_06a4d) and the event records
behind them (nests, surface, `sim.py`: the reference called T:07B2 "the patch is visible"). SIMANT.EXE's start-up
values are 0, 1, 1, 1, 1, 0: **Silly is off** unless the player turns it on (the emulator's Quick Game has T:07B2
= 0, so `test_nest.py` / `test_balloons.py` set it).

**Songs** (`f_00ea1(id, 0x7E)`: only with sound hardware DS:1926 and Music T:07AA; `f_026e7`, then `f_284b3(id)`
stops the current song (`f_285aa`) and starts SOUND type 18 entry `id`; FILE_FORMATS). `f_00ed8(n, 0, 0x7E)` is a
sound effect (Sound Effects T:07AC), `f_00ed0` an empty stub, `f_00f28` "has the song finished". The call sites
(`calls.tsv`, the pushed id): 0x2711 Game Theme from the title `f_72bc2` (window 0x300, then a wait `f_01277(0x28)`)
and File > New (f_6e26d); 0x2713 + Rand2 the fanfare and 0x2718 / 0x271A Victory / Defeat (f_71d95); 0x2713 +
G:0228 the three Ant Themes in turn (`player.jingle` f_0cd37, at most every 0x1C20 clock ticks); 0x2AFA moving to a
patch (f_01d48), 0x2AFB placing a queen / Start Game / the yard map (f_01efa, f_67010, f_67a24, f_7650c), 0x2AFD
NEWBODY (f_758e0, no ant to become), 0x2AFE the Exchange (f_11b81), 0x2B05..0x2B09 recruit 5 / 10 / all and
release half / all (f_76cb9: CALL2ARM at +0 / +6 / +12, then song 11016 at +0 / +12), 0x2B0A ATTACK (f_13d35, the
alarm), 0x2B0C / 0x2B0D the black / red queen (f_0be34), 0x4E20 / 0x4E21 HAPPY1 / 2 (f_758e0: the queen scene,
found a nest), 0x4E22 / 0x4E23 / 0x4E25 the yard's news (reds gone, the human moves in, ...; `yard.py`), 0x4E27 +
Rand(5) the sad songs (the yellow ant's deaths, f_75d01). The reference had three of these as `'sound', 0x7e` (the
volume argument): fixed to `'voice', 0x2afa` (newgame.move_to_patch) and `'sound', 1` (f_00ed8(1, 0, 0x7E): a
refused patch, and death events 3 / 4).

**The timed message** (`f_15e2c(text, duration, force)`, the "status line"): two slots, DS:19C6 (text far
pointer, expiry DS:19CA = clock + duration * 3 / 2, or 0x7FFFFFFF for a negative duration; dirty DS:19CE) and the
copy DS:299A (expiry DS:299E, dirty DS:29A2). A message is taken when forced, or when none is shown and Messages
(T:07B0) is on, or when it clears (null) a lasting one. The Edit window draw `f_038a6` clears an expired one, else
draws it with `f_15d96(text, G:110C (the map rectangle), G:110E + 4)`: font 2 (0 at 320 px), scheme 3, centred
over the map at its top + 4. `f_7052b` shows the copy in the yard window as a font-2 sprite centred at the top of
the yard picture (G:10D2..G:10D6). Texts: the advisor G:0360 (STR# 1020) for 120; STR# 1010 by offset from G:034C
(e.g. +0x10 [4] entering the red nest, +0x58 [22] / +0x54 [21] the dig / fill refusals, forced, 120; MATE's
[15] / [5] / [6] for 180). `f_71b1a(picture, id, flag)` (the reference's 'message' / 'message_box') is a message
box shown when flag != 0 or Events (T:07AE) is on.

Layout (`f_2fd2_0663`): the titles' widths in cells go to DS:46BC and their x to DS:46A8: x0 = 0, then + (len +
gap) * 8 with gap = (screen width / 8 - all titles' cells) / (n - 1) kept within 1..3 (3 at 640 px: x = 0, 64,
144, 208, 296). The bar is the font's height + 3 px tall, titles at y = 1 in font 1 (8 x 10, DS:3DDE / DS:3DDC);
`f_1fd28(x, y, normal, text)` draws a title, inverted while its menu is open. f_6d9a4 (opened from the bar): w =
the longest item (state byte included), the box left = (title cells - w) / 2 cells from the title (>= 0), top = font
height + 5, w * 8 + 16 wide and n rows + 6 tall (kept on screen); it saves the area (f_1d2e9), fills and frames the
inner rectangle (8 px in at the sides, 3 at top and bottom; `f_1ffd1(1)`, `f_1d26d`, `f_1ffd1(0)`, `f_1d26d`) and
draws the items from its top-left, one font line each; a separator is drawn as a space, w - 2 dashes and a space.
Keys inside: '+' / Down next, '-' / Up previous (wrapping), Enter / CR / Space pick, Esc cancel, a letter jumps to
an item; f_6d7e3 moves between menus on the scan codes 'K' / 'M' (Left / Right), skipping disabled titles
(first byte & 0x80). With the button held a release picks; after a click the menu stays until the next one.
`f_6e0e0` sets the marks before: `f_2033e(id, 0x10 / 0x20)` (id = 16 m + item) checks Slow..Ultra for T:07CC and
each Options flag that is on, and `f_1fe55(0x41, " Unpause" / " Pause")` relabels the Pause item (DS:297E /
DS:2987).

`f_74386` (a typed key; it also feeds the cheats, `f_6a920`): with Ctrl (`f_1c160(0x1d)`) the Alt keys 0x817 /
0x820 / 0x821 / 0x82F are debug keys (decoded 2026-10-29: Ctrl+Alt+I `f_74460` an alert with the free memory,
Ctrl+Alt+D `f_174cc("User Request")` the fatal-error exit, Ctrl+Alt+F `f_190ba` flushes the resource cache ("FLUSH"),
Ctrl+Alt+V an alert `f_1c6e0` with the far pointer DS:0064: "Ver 1.00 Fri Dec 06 14:51:14 1991"; the shell keeps only V).
A key 0x8nn is scan code nn without a character (Alt + letter): 0x824 is Alt+J. Then the table DS:2CBE (u16 key, u16 command; 0-terminated) posts
the command (`f_1ba3f`): Alt+F / W / V / O / S and F2..F6 → 0xFE00..04; ')' 0xFD41, '!' 0xFD43, '@'
0xFD44, '#' 0xFD45, '$' 0xFD46; ^N 0xFD03, ^S 0xFD05, ^A 0xFD06, ^L 0xFD04, ^E 0xFD11, ^M 0xFD12, ^B
0xFD13, ^C 0xFD14, ^T 0xFD17, ^G 0xFD31, ^J 0xFD32, ^K 0xFD33, ^X / ^Q 0xFD08, ^Y 0xFD21. Other keys go to
`f_76aeb` (thunk 0x2fa28):
- '0' → `f_76cb9(7)` (alarm); '1' → 10 for the spider (G:0A06 != 0), 8 for a queen that can dig
  (G:04C2 == 0x40, G:0C24 == 0), else 1; '2' → 0x0B / 9 / 2 likewise; '3' → 4; '4' → 5; 'X' / 'x' → 6.
- Backspace (0x88) without Shift (0000:0417 & 3): the yellow ant (G:0A06 == 0) walking (G:0AA0 != 0) →
  `f_757dd(G:048C, G:047C, G:048A)` (stop); the spider (G:0A06 == 1) with its target G:0F42 / G:0F7E off its
  position → target = position, G:0FB8 = 0; else `f_01c03` (G:1074 = 1, view and centre on the yellow ant).
  With Shift: `f_01c52` (follow). 0x824 (the spider only) → 0x0C; 0x847 → sound 15 and `f_01c52`.

`f_6e26d(event)` switches on the command's low byte (jump table at 0x6E296, CS base 0x6E0E0):
- 0x01 → `f_2f99c`; 0x03 → music 0x2711 and `f_2f848(0)` (the new-game dialog);
- 0x04 / 0x05 / 0x06 / 0x08 → DS:2CBC = n, done by the main loop (8414:0000): 4 load (`f_2f970`, and the
  new-game dialog when no game runs, G:0EAC == -1), 5 save (`f_2f97a(1)`), 6 save as (`f_2f97a(0)`), 8 quit.
  The thunks reach `f_6c1a0` (load: the save prompt `f_2f974` when G:02C2 != 0, then `f_6c566`) and `f_6c328`
  (save). `f_6c566(name, caption, button, save)` is the file dialog, window 22: caption 0x1601, the path
  field 0x1606 ("Path:"), the list 0x1609 (sub-folders first, then `*.ant`, 16-byte records sorted with
  `strncmp`, a folder's marker byte 1 shown as '<'; "No Files"), drives 0x160B..0x1612 (DS:2966 = item -
  0x15CA, 'A'..'H'), the button 0x1613 ("LOAD" / "SAVE"), CANCEL 0x1614; in save mode (save == 1) the name
  field 0x1604 (`f_6d1c2`, 9 characters; a typed letter starts it); Enter = the button, Esc = cancel; a
  double click on a folder changes into it ("CHDIR");
- 0x11 → `f_03370` (the Edit window), 0x12 → `f_0148a` (the Map window), 0x13 → `f_07aab` (Behavior),
  0x14 → `f_07a95` (Caste), 0x15 → `f_2f9ba` (History), 0x16 → `f_2f9b0` (the SimAntipedia), 0x17 →
  `f_2f9a6` (Efficiency Score);
- 0x21..0x24 → the yard window's mode G:035C = n - 0x21 (`f_01823` when it changes), `f_01aec(0)` when
  G:032E != 0, open the yard window (0x1900, `f_01447`) if it is not; 0x26 / 0x27 / 0x28 → `f_01aec(1 / 2 /
  3)` (surface / black / red nest);
- 0x31..0x36 → toggle T:0746 + 2n, i.e. T:07A8, T:07AA (0x32 also stops the music, `f_285aa`), T:07AC
  (sound effects), T:07AE (messages), T:07B0, T:07B2;
- 0x41 → G:047E ^= 1 (pause) and `f_6e17e(G:047E)`; 0x43..0x46 → T:07CC = 0..3 (Slow, Normal, Fast, Ultra; 3
  reads the delay T:07D4 = -1: no wait; at Ultra with a Shift key held the main loop also skips the redraw,
  16196), then `f_6e0e0` (the menus' marks, above).

### The Edit window's tool strip (`f_0310f`, decoded 2026-10-20)

Events of window 0 (`f_74140`: event high byte 0) go to `f_0310f(event)`, a jump table at 0x3140 (CS base 0x2500) on
the item id - 4 (ids 4..0x15; layout 0 repeats ids, the event carries the item's own id):
- 4 and 0x15 (the map and the strip under it) → `f_2f762` → `f_74fe0` (the map's clicks);
- 5 MAP → `f_6776f`: window 20 pops up (scale DS:8BD2 / 8BD4 = 1 px per cell in VGA, 2 otherwise), `f_674ee` draws
  the Edit view's map into item 0x1401: width G:3854 = 0x80, or 0x40 for a nest (G:032E 2..3) at offset G:3852 =
  32 x scale with the margins filled black (0x0F); a scent layer when T:07C8 is 4..8 (`f_2f8ca`: alarm D09F, the
  nest markers E09F / F09F, the trails E89F / the red trail map 4DA7:0); the image is kept in two far blocks ("Map
  window image", "Generated map window", DS:2996). `f_678d8` XORs the Edit window's area (G:0508 / G:050A,
  G:10E0 x G:10DE cells) as a frame (`f_1d230`, mode 1), `f_6796e` removes it. If the button is still held, it
  waits for the release: released over the button, the pop-up closes (`f_214b5`) and `f_0148a` opens the Map
  window (or brings it to the front: it does not toggle). Otherwise, while the pop-up is open, a press in it
  recentres the Edit window on the cell under the mouse (`f_034c4`) for as long as the button is held. It runs its
  own event loop, so the game does not advance meanwhile;
- 6 "?" → `f_2f74e(2)` → `f_714ab(2)`: the help overlay picture (item 2, 15001) is drawn while the button is held
  (its own loop), then the window is redrawn. The Map window's 0x116 does the same with item 0x103 (14001) after
  G:1074 = 1;
- 7 → `f_2f744` (the Experimental menu, 0x67A24); 8 / 9 / 10 → `f_01aec(1 / 2 / 3)`; 0x0B → `f_01c52` (follow);
  0x0C / 0x0D / 0x0E → `f_01ca5` / `f_01cee` / `f_01d0f` (the spider, the queens); 0x0F → `f_2f73a(G:047E == 0)`
  (pause); 0x10 → `f_2f730` (`f_679c0`, the scent menu);
- 0x11 / 0x12, the yellow and black health bars → `f_68044` / `f_68002`: G:0FBA (the yellow ant's health warning)
  / G:0FFE (the advisor's hunger level) = (bottom - y) x 100 / (bottom - top) of the click; 0x13 (red) nothing.

The go-to buttons: 0x0C `f_01ca5` the spider: none (G:0F0C == 0) → sound 1 (`f_00ed8(1, 0, 0x7E)`), else
`f_01aa7(1, G:0F12 >> 4, G:0F34 >> 4)`; 0x0D / 0x0E `f_01cee` / `f_01d0f` the queens: `f_01aa7(2, T:02B4, T:02B6)` /
`f_01aa7(3, T:02B8, T:02BA)` (the spots where they lay, not a search for the queen). `f_01aa7(v, a, b)`: in view v
already (and v > 0), `f_034c4(a, b)` and G:0AA6 = 0; else `f_01976(v, a, b)`.

The view switch `f_01aec(v)`: v == 0 keeps the old view in G:0332; else `f_0256e` (redraw); G:032E = v; G:0F36 =
(v == 1 ? 0x80 : 0x40) - G:0FB6 (the Edit window's width in cells; G:0FFA its height); G:0D70 = T:07C0[v]; the
view's kept centre (the yard G:07BC / 07BE, the surface G:0596 / 0598, the black nest G:06A6 / 06A8, the red nest
G:072E / 0730) → `f_01976` → `f_034c4` (recentre there); `f_01781(v)`. After every scroll (`f_031f6` → 104a:02ad)
the current view's slot = G:0FB6 / 2 + G:0508, G:0FFA / 2 + G:050A. `f_01781(n)` (the Map window's layer T:07C8):
the same scent layer (4..8) again gives 1 (the surface); 0 → T:07C8 = 0 and `f_01823(G:035C)` (the yard window);
4..8 switch the Edit window to the surface first (`f_01aec(1)`); then T:07C8 = n. So the Map window shows the Edit
window's view, or a scent layer while the Edit window shows the surface.

The bars (`f_03a83`): for the yellow ant G:0F78, the black and red colonies G:10BE / G:01FE (items DS:1AA4 =
0x11..0x13, schemes 4 / 9 / 10: yellow, black, red on light grey), the part bottom - height x v / 100 .. bottom
filled in the scheme's foreground, the rest in its background; then a 1-px line at top + (100 - G:0FBA) x height /
100 on the yellow bar in black (0x0F), and one at the G:0FFE level on the black bar through the driver's XOR fill
(DS:913C).

### The file dialog (window 22, `f_6c566`), saving and loading (`f_6c328`, `f_6c1a0`), alert boxes (decoded 2026-10-20)

`f_6c566(name, caption, button, save)`:
- The drive DS:2966 (0 at first: the current drive DS:38B6); its folder from `f_1f70f(drive - 0x40, buf)` (getcwd
  per drive), a '\' appended. A drive that cannot be read shows an error box and falls back to the previous one
  ("Can't read disk. Aborting" if that is the start-up drive); B: becomes A: with a single floppy (BIOS 0x410).
- The path line 0x1606: `f_2094b(0x1606, "", 0, 0)` puts the pen at the item's corner, `f_23828` fills from the
  pen's x to the item's right in the scheme's background (so the "Path:" of the layout disappears), then
  `f_2094b(0x1606, folder, 4, 0)`: the folder at the item's left + 4, top.
- The list: a 0xC80-byte buffer ("File list"), up to 200 - DS:2968 records of 16 bytes, from `findfirst("<folder>*.*",
  0x10)`: a folder (attribute 0x10) gives "0\x01..>" for "..", nothing for ".", else "0\x01<NAME>>" (sprintf "\x01%s>");
  a file matching "*.ant" (`f_1f68d`) "0%-12s". '0' is the flag byte (bit 0 = selected). Sorted with strncmp over
  the 16 bytes (a selection sort with `f_2c6fe` / `f_1f597`), so the folders come first; then each marker byte 1
  becomes '<' and the records are packed as NUL-terminated strings for the list item (`f_240c6`). None: "0No Files".
  The number of folders is kept (`local_2a`): a chosen row below it is a folder.
- Set-up: `f_2318a(0x1613, button)` and `(0x1601, caption)` set the run-time texts. Save mode shows the state-5 items
  0x1602..0x1604 (`f_22e52` / `f_23136`); Load mode hides and disables them (`f_22e5a` / `f_2313e`), reads 0x1602's
  offsets (`f_22c9a`) and writes them back with a zero height (`f_22ccd`). Then `f_21336(0x1600)` lays the window out
  (FILE_FORMATS "Window layouts"): 0x1605 hangs off 0x1602's bottom, so in Load mode everything below moves up 35 px
  and the window ends at y = 331 instead of 366 (the original's screen). After the drive is settled, `f_22fae(DS:2966 +
  0x15CA)` → `f_22f65(item, 1)` selects the drive's button (+24 bit 2; the radio group, +24 bit 5, cleared first by
  `f_22fbd`): the selected bevel.
- Save mode: the name box 0x1603 / 0x1604 (`f_22e52` / `f_23136`; load hides it: `f_22e5a` / `f_2313e`). The name
  is drawn at 0x1603's left + 4, y = (top + bottom - height + 1) / 2, in 0x1604's scheme (8: cyan on white). On the
  first scan, with a game file name known (G:3862), the name is preset to its last component. A key with ctype & 7
  (a letter or digit) starts `f_6d1c2` (the line editor, 9 bytes, starting empty with the key typed).
- Events: Enter or the button 0x1613: with no name, the selected row (`f_23f69` rows, `f_23eff` selected?,
  `f_23f92` its text): a folder → "CHDIR %s" (`f_2cad3`) and a rescan; a file → its text (from the byte after the
  flag) is the name. Esc or CANCEL 0x1614: no name, return 0. A drive button 0x160B..0x1612: DS:2966 = id - 0x15CA
  and a rescan. The list 0x1609: a press (0x200 / 0x800) remembers the selected row (`local_26`) and, in save mode,
  clears a typed name; a double click (0x2000 / 0x4000) on the remembered row is the button.
- Return: `f_6cecb(name)`: spaces and commas become '_', at most 8 characters before a '.', then ".ant" (DS:296A);
  the result is "<folder><name>".

The list item (type 4) and its scroll bar (type 8), in the window library (segment 33e6):
- `f_241f2` draws a list: the font at +28, rows = (bottom - top) / height (stored at +2A); each row's text at the
  item's left (no margin) and top + i * height (`f_24edb`: the text, then the rest of the row filled with the
  background), in scheme +26, or +27 when the row's flag bit 0 is set (`f_2208e`); rows past the end are filled
  with the background. +2C the row count, +2E the first row shown, +30 its byte offset, +34 / +36 the text handle.
- `f_248b3` a click: row = (y - top) / height + first. With +24 & 0x20 (single selection): if +25 & 4 and the row is
  selected nothing changes, else all rows are cleared (`f_23fcb`); then an unselected row is selected (`f_2403c`).
- `f_244cc` draws a scroll bar (type 8; +28 the list's id; type 7 draws nothing): bitmap 109 (up arrow) at the top,
  111 (down arrow) at the bottom - G:47DC (the arrows' height, 13), the track between them in the background, then
  `f_24378` the thumb when the list has more rows than it shows: inside the track less 1 px on each side, height
  span * shown / rows (at least 10), top first * (span - height) / (rows - shown), in the scheme's foreground
  (scheme 1 in the file dialog: cyan on dark grey).
- `f_24971` a click on it (only when the list has more rows than it shows): on an arrow, a plain press scrolls one
  row (`f_24736` up / `f_24602` down) per clock tick while the button is held (`f_1f881(1)`, `f_20262`); with
  flags & 0x68 (double click, right, Shift) it jumps (`f_24551`) to the top / to rows - shown. The track does nothing.

`f_6c328(n)`, File > Save (n = 1) and Save As (n = 0); also the save prompt's Save. With n = 1 and a game file name
G:3862 it opens that file read / write (`f_2b482(name, 0x8002)`): if it exists, the alert "OVERWRITE\n<name>"
(`f_1ca35(text, 0)`, Yes / No); No → the dialog (`f_6c566(buf, "Save Game", "SAVE", 1)`, cancel ends); the name
goes to G:3862 and the check repeats. Then the file is created (0x8302) and the block table at 4E4B:0 written; a
failure shows `f_1c6cc(strerror(errno))` (the MSC table DS:7D12) and empties G:3862.

`f_6c1a0`, File > Load: the save prompt (`f_2f974`) when G:02C2 != 0, the dialog ("Load Game", "LOAD"); the name to
G:3862; a file that will not open: `f_1c6cc(strerror(errno))`; a read error: "  Read error  \ngame not loaded" and
G:0EAC = -1 (no game); success clears the timed message (`f_15e2c`).

Alert boxes (the library's, segment 2c62; no layout): sizes in character cells of the PC font (DS:3DDE = 8 px wide,
DS:3DDC high). `f_1f80c(text)` measures the lines (the longest in DS:8CD8, the count in DS:8CDA); `f_1f9a8(rect, w,
h)` centres w x h cells on the screen (DS:3DB2 / 8, DS:3DB4 / font height); `f_1d1bb` turns cells into pixels (a
row's high byte is a fraction in 14ths).
- `f_1ca35(text, set)`: the button set DS:5570[set] (far string lists, counts DS:5584: 0 Yes / No, 1 Yes / ? / Cancel,
  2 Retry / Cancel; each label's first byte is its key, \r Enter or \x1b Esc). The box is (max(longest line, 2 x
  buttons) + 2) x (lines + 4) cells (sic: the labels' lengths are summed but not used). Fill 0xF2F (black), a 4-px
  frame in colour 4, a 1-px frame in colour 0 (white) on its outer edge; the lines centred (`f_1f977`) from the second
  row, colour 4 on black (`f_1c926`, `f_1fbd0` draws 8-px cells); the buttons on the row bottom - 2, starting at
  ((width - total label length - 2) / 2) + left, 2 cells apart. A button (`f_6d620`, thunk 0x2FA5A): its label in
  colour 4 on light grey (12), a 3-px frame outside it in colour 4 and inside that a 2-px one in light grey
  (`f_1d018` with negative thicknesses draws outside the rectangle), hotspot id 0x900 + i. It returns the button
  pressed: a key equal to a label's first byte or its first letter (lower case folded), or a click.
- `f_1c6f5(text, timeout)` (`f_1c6cc(text)` with no timeout): the same box without the white line, colours from the
  table DS:550C (fill 0xF0F black, frame 0x404, buttons 0x404 / 0xC0C), one "Continue" button centred on the row
  bottom - 2; C, Enter, any press or the button close it.

### The SimAntipedia (window 5, `f_78db9` / `f_78808` / `f_790f0`, overlay 881a; remake: `OpenSimAnt.Data/Antipedia.cs`)

The Map toolbar's 0x115 "Ant Info Window" → thunk 0x2f9b0 → `f_78db9`: if window 0x500 is not open
(`f_235a0`), the card DS:2E26 = 128 (Top Card), the history DS:2E04[0] = 128, its index DS:2E24 = 0; then
`f_21336(0x500)` opens it. With DS:3DB2 == 320 it runs its own event loop (`f_21cc1`) while the window is
open, passing each event to `f_790f0`. The window's draw callback `f_78215(flags)` redraws the card
(`f_78808(DS:2E26)`) when flags & 2. Window 5 has no close box.

`f_78808(card)`: SHARED type 17 (card layout) id = card; "Card Resource not found" if there is none.
Type 19 (card name, '_' → ' ') goes into the caption 0x501 (`f_2318a`). The item 0x502's rect (`f_252d8`)
is the origin (279, 245); the card is 320 x 200. Records (big-endian; `f_781c4` swaps every word,
`f_781a0` the halves of a dword):
- 'PICT' + 12 bytes: bitmap id, Rect (top, left, bottom, right), n; `f_259de(id, left + ox, top + oy)`
  draws it (HCEGANT's colour bitmaps, SHARED's 1-bit ones; 151 exists in neither and is skipped). Then n
  hotspots of 10 bytes (Rect, value) appended to 4EE5:0280 (count DS:8C22, reset per card), stored
  left / top / right / bottom, item-relative.
- 'TEXT' + 10 bytes: Rect, n; n text ids. For each: type 10 text, type 21 style runs (`styl`). Each NUL in
  the first size - 4 bytes is removed together with the bytes after it that are ≤ 0x1F as a signed char
  (`_fmemchr` loop; texts 212, 310, 420, 802 have such `00 00 01` debris), and runs after it move back. The
  rect gets the item origin added once per frame (a bug for n > 1; every card has n = 1). Then
  `f_78232(text, styl, rect, 0, font 2, font 5, 1)`.
- anything else: "Unknown Resource." and stop.

`f_78232(text, styl, rect, first, f1, f2, record)` (also used by the pop-up, record = 0): lines of
max(height f1, height f2) from (left + 1, top + 4), at most (bottom - top) / line height of them; text up to
strlen. Run k is drawn in f2 when its face word is 0x0100 (bold), else f1. Per line: x = 0; for each
character, first if run k + 1 starts here: draw the pending segment (from the segment's start to here) at
the segment's x, and with `record`, if run k was bold: strip leading spaces, upper-case it, and look it up in
the glossary 4EE5:0500 (0x22-byte entries: a 32-byte name, then its u16 text id at +0x20; f_78440 tests the
id at 0x520 + 0x22 i and compares the name at 0x500 + 0x22 i; 26 entries HIGHLIGHTED 901, CHITIN 910 .. EGGS 967,
ended by an entry with id 0, `strcmp`; until 2026-11-01 the remake read [id][name] from 0x520, giving every word
the previous word's definition); a match adds a hotspot (segment x, line top, left + x, line top + line height,
id) to 4EE5:0000 (count DS:8C24, reset per call), no match logs "ERROR: Cannot file text rez". Then
x += the character's width in the current font; if x < width: a line end (0, LF, CR) ends the line with a
break before it; a break goes before space ( [ {, after ! ) , - . ? ] }. The line ends when x ≥ width. Its
tail is drawn from the segment start to the last break (or through the overflowing character if there was
none; if the break lies before the segment start, nothing), then spaces and one CR / LF are skipped.
`f_78641` measures the same way (lines x line height) without drawing.

`f_790f0(event)` (only for clicks in 0x502; point item-relative): the first PICT hotspot hit (`f_20205`:
left ≤ x < right, top ≤ y < bottom):
- 1 (PREVIOUS): prev = DS:2E04[(index - 1) & 15]; if nonzero, card = prev, index - 1, redraw (`f_22882`);
- > 1: index + 1, DS:2E04[index & 15] = card = value, DS:2E04[(index + 1) & 15] = 0, redraw;
- ≤ 0: `f_78e1c(centre x, top, bottom, -value)`.
If none was hit, the first text hotspot hit → `f_78e1c(centre x, top, bottom, id)` (item-relative).
The nav bar is bitmap 21004 (BACK = the parent card, PREVIOUS = 1, TOP = 128) or 21005 (PREVIOUS only).

`f_78e1c(x, top, bottom, text)`: a pop-up half the item wide (a), left = x - a / 2 (absolute), kept 4 px
inside the item; height h = `f_78641(text, styl, a, 2, 5)` + 5; below the link (top = item top + bottom +
4) unless item height - 10 < h + bottom + 4, then above (top = item top - h + top - 4); the box is 4 px
larger each way, clamped to the item. It saves the screen (`f_1d2e9`), draws the box (`f_1ce33(.., 1)`)
and the text (`f_78232`, record 0), waits while the button is down (`f_20262`), and restores.

Cards: 128 Top Card (topics: Social Insects 134, Ant Anatomy 130, Lifecycle 157, Castes 139, Social
Behavior 146, Common Species 152, Ant Facts 167, SimAnt Strategy 171), 127 / 129 (an older top card and
an "Index" with links [1, 2, 129, 128]: no card links to them), 130..179 the topics.

The help (`f_76eb5`, menu command 0) is not this viewer: it opens window 26 (0x1a00, a 5 x 5 frame with
picture 2100, which does not exist) and waits up to 30 s (`f_01277(0x1e)`) or for a key; in the DOS
version it shows nothing useful.

## The sound driver ("Sound Driver Shell (c) 1991 -- LIB link version", code 0x277E0..0x2A05C)

Decoded 2026-10-19 with `tools/re/opl_capture.py`, which boots the original in the emulator with a sound
mode set and logs every OPL2 register write (and Sound Blaster DSP traffic). It needs two things SimEmu
does not do: the PIT counter on port 0x40 must count (the AdLib init `f_28415` times a delay on it and
hangs otherwise) and the OPL status port must answer the timer detection (0xC0 after timer 1 starts).

**Modes.** `SIMANT.CFG` "Sound Mode: n" → DS:610A (-1: detect with `f_293a6`); the `/s{NABCI}` switch too.
`f_00df4` → `f_277e0(mode, 0)`: detect through DS:74DA[mode], init through DS:68B6[mode], set the timer
(`f_2902b` / `f_29048(0xD6, 0x132)`, then `f_28f8c` installs the handler at DS:74BC straight into the
interrupt table), G:01F0 = mode, then DS:1926 = 1 (sound hardware present). Mode 4 is AdLib (port 0x388),
mode 5 probes 0x220 / 0x240 / 0x280 / 0x2C0 (CMS), mode 6 is Sound Blaster (DSP reset at 0x2x6; FM at
0x388), mode 7 writes port 2. The owner's copy uses 6.

**Timing.** The PIT runs at 1193182 / 0xD6 (DS:74A9) = 5575.6 Hz: the sample voices are mixed at this
rate (see "Sound effects" below for what that means for the effects). Every 16th interrupt
(DS:6B3E / 6B40 = 16; divisor DS:74AB = 0xD60) is a music tick, 348.5 Hz (2.870 ms). The sequencer
`f_28b1f` handles one MIDI event per call and returns the wait in music ticks (kept in DS:6B42); the
handlers at 0x28CB0 / 0x28F4A call it. The Game Theme (0x2711, 88320 MIDI ticks at 240 PPQ and
280373 us per beat = 103.2 s) takes 35856 music ticks = 102.9 s.

**Songs.** `f_284b3(id)` stops the song (`f_285aa`), loads SOUND type 18 `id` and its type-20 MIDI with
`f_00193` (the type 18 transposition goes to DS:7576 and is added to every key), keeps the MIDI handle at
G:4B28, and copies two 14-word arrays from the song header (DS:00B4 →): +0x00 → G:4BAA (a priority per
MIDI channel: 7 for the tune, 5 for the drums in the Game Theme) and +0x1C → G:4B8E (the **instrument per
MIDI channel**, 0..55: the Game Theme uses 25, 53, 3, 54, 35, 46, 50, 51, 48, 0, 12, 43, 52). MIDI
channels 14 and 15 are ignored. Channel events (`f_289d7`): note on `f_28969` → `f_297ac(priority,
instrument, key + DS:7576, velocity * DS:7570 >> 7)` (velocity 0 → note off `f_298a8`); meta events
`f_28a65` (0x51 tempo), sysex `f_28b13`.

**Instruments** (56, G:0000 + 6n: u16 device, far pointer to the record). The device's init copies them
with `f_278ea(table)` from the static table at **DS:0D92** (flat 0x568C2; the same table in AdLib and
Sound Blaster modes). Device 2 is FM, device 1 a sample voice:

```
types of instruments 0..55 (1 sample, 2 FM, 0 none):
21121111121111122222111112111121111211111111112121221220
```

- **FM records**: 20 x 16 bytes in SIMANT.EXE's data at DS:0202 (flat 0x55D32). Bytes 0..10 are the
  OPL2 registers in the order `f_2815a(record, channel)` writes them: [0] carrier 0x20, [1] modulator 0x20,
  [2] carrier 0x40, [3] modulator 0x40, [4] carrier 0x60, [5] modulator 0x60, [6] carrier 0x80,
  [7] modulator 0x80, [8] 0xC0 + channel, [9] carrier 0xE0, [10] modulator 0xE0; s16 at +0x0B an octave
  shift (key += 12 * it), s16 at +0x0D a velocity offset. Operators by channel: modulator DS:68FE
  {0,1,2,6,7,8,12,13,14}, carrier DS:6908 {3,4,5,9,10,11,15,16,17}, slot → register offset DS:6912
  {0,1,2,3,4,5,8,9,10,11,12,13,16,17,18,19,20,21}. Instruments → records: 0 → 9, 3 → 7, 9 → 19,
  15 / 16 → 1, 17 → 2, 18 → 3, 19 → 4, 25 → 8, 30 → 5, 35 → 14, 46 → 11, 48 → 12, 50 → 15, 51 → 13,
  53 / 54 → 10 (records 0, 6, 16, 17, 18 unused by the table).
- **Sample records**: 0x20 bytes from DS:0342: +09 u8, +0A s16 a transposition, +0C u16 loaded state,
  +0E the original file name ("kick.adp", "snare.adp", "agogo.adp", "sinwave.adp", ...), +1D u16 the SOUND
  type-5 id (loaded on demand by `f_00090`). Played pitched (`f_29263`): with k = key + the +0A
  transposition, the step (8.8 fixed point) is DS:74C2[k % 12] (0x100, 0x10F, 0x11F, 0x130, 0x142, 0x155,
  0x169, 0x17F, 0x196, 0x1AE, 0x1C8, 0x1E3: equal temperament), shifted left by k / 12 - the +09 byte (the
  sample's base octave, 5 for every record in the table) or right by the difference; the attenuation
  is (0x7F - v) >> 4 with v = velocity + DS:74C0 (0) clamped to 0..127, passed to `f_29168`. A step of 0x100 plays the sample at the mixing rate, 5575.6 Hz.

**Sound effects** (`f_00ed8(n)` → `f_29927(n)`): the static table DS:0A82 + 8n = (key, priority,
instrument, velocity) → `f_297ac(priority, instrument, key, velocity)`. Effects 0..54 are instrument n at
key 60, priority 3, velocity 127; effect 55 is instrument 10 (burp) at key 100, priority 4 (step 0xA10:
about ten times faster). So **every sample effect plays at 5575.6 Hz**, not 11025 (the remake's guess);
effects 0, 3, 9, 15..19, 25, 30, 35, 46, 48, 50, 51, 53 and 54 are FM notes (key 60 on that instrument),
not samples; effects 12, 43 and 52 play sample 5 (beep2), not samples 12 / 43 / 52.

**Voices** (G:4A4E + 6v: device, hardware channel, MIDI channel, instrument, key, age). AdLib: two
sample voices and FM channels 1..7 (channel 0 keeps the start-up detection tone's key-on bit); Sound
Blaster: two sample voices and FM channels 0..7. `f_29689(priority, device)` picks a voice. Per-device
calls: note on DS:7504[device], note off DS:7524, set patch DS:7544 (device 2: `f_282b5`, `f_2839d`,
`f_283c5`).

**FM note on** (`f_282b5(instrument, key, velocity, channel)`): carrier level =
`(record[2] & 0xC0) | (0x3F ^ (((0x3F - att[v]) * (0x3F ^ (record[2] & 0x3F))) >> 6))` with v = velocity
+ G:4B16 + record s16 +0x0D clamped to 0..127 and att = the 128-entry table DS:6BA4 (64, 51, 45, ..., 0);
key += 12 * record s16 +0x0B, played only if 0..127; 0xA0 + ch = F-number DS:6924[key % 12] low byte
(12 words: 0x157, 0x16B, 0x181, 0x198, 0x1B0, 0x1CA, 0x1E5, 0x202, 0x220, 0x241, 0x263, 0x287), 0xB0 + ch
= 0x20 (key on) | (key / 12) << 2 | the F-number's high bits. So block = key / 12: MIDI 60 plays as an
OPL block-5 C (523 Hz), an octave above General MIDI. **Note off** (`f_2839d`): 0xA0 + ch = 0, 0xB0 + ch = 0.

**Init** (`f_28268`, both modes): 0x01 = 0 (**waveform select off: every operator is a sine**, the 0xE0
bytes have no effect on an OPL2), 0x04 = 0x80, 0x08 = 0, 0xBD = 0xC0 (deep tremolo and deep vibrato,
no rhythm mode), 0xB0..0xB7 = 0. AdLib mode first runs the detection (`f_28415`: timers, then a tone on
channel 0).

**The sequencer** (ported: `remake/src/OpenSimAnt.Data/SoundDriver.cs`, verified by `OplTraceTests` on 91
traces from `opl_capture.py record`). `f_286f6` reads the header (DS:7566 = tracks, G:4B2E = PPQ), finds
the track chunks (read positions DS:8DD8), reads each track's first delta into G:4B42 (32-bit absolute
times) and peeks its first byte into G:4B30 (running status). `f_28784`: last time DS:7568 = 0, current
track DS:756C = 0, scale = `f_287c5(480, 500000)`. `f_28b1f` (one call per wait): read a byte; if it has
bit 7 it is the new status; then 0xF0 / 0xF7 skip a length (`f_28b13`), 0xFF a meta event (`f_28a65`: 0x2F
marks the track ended, 0x51 sets the scale, others are skipped), anything else is a channel event
(`f_289d7`, then the read position moves by DS:75A4[(status & 0x70) >> 4] = 2, 2, 2, 2, 1, 1, 2); then
`f_2882f`: the current track's next delta (or 0x7FFFFFFF when ended), the track with the earliest time
wins (a later one only if strictly earlier and not ended), and the wait is `(time - last) * scale >> 8`
(32-bit `f_2cddc`, `f_2ceba`, then the low word). It loops while the wait is 0; the end of every track sets
DS:756E = 2. **The scale** (`f_287c5(ppq, tempo)`, G:4B8A) = `(tempo / 1000 * 1194 / ppq) / 13` in integers
(107 for the Game Theme): about 3% faster than the MIDI's tempo against the 348.5 Hz tick, and each wait is
truncated on its own. Only note on / off on channels 0..13 do anything (velocity 0 is a note off).

**The song header** is one static table for every song: DS:00B4 points at DS:0068, priorities
(0, 7, 7, 7, 7, 5 x 9) and instruments (0, 25, 53, 3, 54, 35, 46, 50, 51, 48, 0, 12, 43, 52) for MIDI
channels 0..13. Channel 0 has priority 0 and never sounds; channels 1..10 are FM, the drums (5..10)
included; 11..13 play sample 5 (beep2).

**Voices.** `f_29689(device, priority)`: -1 if the priority is below 1; else over every voice: a sample
voice whose sample ended gets priority 0; among the voices of the device, take the lowest priority, on a
tie the highest age; every voice's age goes up by one (a byte); the note gets the voice only if its
priority is at least the lowest found (no voice of the device: 0x0F). `f_297ac(priority, instrument, key,
velocity)`: velocity * DS:7502 >> 7; the voice's old note is silenced (DS:7524[device](old key, channel)),
the patch is loaded if the instrument changed (DS:7544), then note on; the voice keeps priority,
instrument, key and age 0. `f_298a8(instrument, key)` (note off): every voice with that key and instrument
(its stored byte against the full word) is silenced (by the instrument's device) and gets key 0,
priority 0, age 0x0F. Stopping a song (`f_285aa` → `f_29951`) does that for every voice with a priority.
FM effects have no note off: they decay on their envelopes until a voice is taken.

**The sample mixer** (ported: `SoundMixer.Tick`, verified by `OplTraceTests.DacMatches` on 5 traces of the
original's handler run tick by tick, `opl_capture.py record` → `*.dac`). The loader leaves a sample in memory
as unsigned 8-bit PCM, its delta sum **wrapping** in 8 bits (not clamped as FILE_FORMATS first said: the
cat's meow and the bird call differ in most bytes). `f_29168(record, step, attenuation, voice)` fills the
voice (DS:6B4C + 0x14 * v): +00 position 0, +02 the record, +06 the end (size - 2), +08 the loop point
(record +06, + 2), +0A the step, +0C the volume table DS:6B9E + attenuation * 256 (DS:6CA3: eight 256-byte
tables, 128 + (in - 128) * (8 - a) / 8), +0E the fraction 0, +0F bit 7 = loops (record +08; none does),
then starts the timer (`f_28f8c`). The handler (0x28BD5, 5575.6 Hz): per voice (an empty one gives 0x80)
fraction + step, move by the carry, then **past the end** → loop or stop, and the tick ends there (no DAC
byte, the other voice does not move); else the byte through the volume table. The output is the average
`(a + b) >> 1`, through DS:6B9C (Sound Blaster: DSP command 0x10, the direct DAC, `0x28D4E`; other
devices: the PC speaker, Covox at port 0x222 / DS:6B4A + 1, Tandy at port 0x200, ...). Then the music
tick: DS:6B3E counts 16 handler ticks, DS:6B42 the sequencer's wait. `f_284b3` sets DS:6B42 = 5; with no
song the sequencer returns 0xFFFF, so it is called again only 65535 music ticks later.

Not decoded yet: `f_2c75a` (taken as a copy of the MIDI), the volume G:4B16 (0), the AdLib mode's
sample output. DS:00B2 + 6n looks like the instrument → MIDI program map of
the MIDI mode (0xFFFF: none).

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

## New game (`f_6b36b`) and patch setup (`f_6ae20`), overlay 10 (ported: `simant_ref/newgame.py`)

Ported and verified (`test_newgame.py`): new games in modes 1/2/3 from every snapshot with several C
runtime `rand()` states, `f_6ae20` directly with colonies of 1..1125 ants on other patches, and
`test_newgame.py play`: a game started by each side, then 2000 SimSteps side by side, byte-identical.

```
NewGame():                                         # f_6b36b; the mode G:0EAC is set by the caller
    f_6c010: clear surface, occupancy, both nests (dirt, exit field, cells), all six pheromone maps,
             the s_/b_/r_ type, state, e arrays, the yard colony grids T:00A4 / T:0164 [12][16]
    f_79478(1) (via f_2f956): history arrays (10 x 64 words) and counters; with 1 also the yard
             counters (G:0A90 = G:0AC4 = 1 colony each)
    InitColonySettings f_0888d: automatic behaviour (G:0378 = 1), behaviour weights G:049E = T:080A,
             caste mix G:0482 = T:07EC (copies at T:0810 / T:07F2), caste targets T:07DA (f_085f8:
             (100 * G:0484 + 0x3FFF) / 0xFFFF, same for G:0486, then twice 50 * G:0482); the panel's
             slider geometry (resources 0x578, 0x120D, 0x130D → G:3810..3835, slider positions G:0358 /
             G:022E) is UI only
    G:07CA = G:07BC = 11, G:07CC = G:07BE = 8 (the player's patch)
    f_683a0 (via f_2f910): the yard layer's state (human, mower, bird, dog, rain, timers)
    clear game-over flags, timers, G:0C26 tick count; G:032E = T:07C8 = 2 (Quick) / 1 (other modes)
    SIM:0000[192] patch seeds = (crt_rand() % 0x7FFF - 0xC000) & 0x7FFF
    T:0C24 = mode != 2
    f_6ae20(seed[G:07CC * 12 + G:07CA] (sic: rows of 12, index 107), n_black = mode == 2 ? 0 : 1,
            n_red = 1, G:07BC, G:07BE)
    the yellow ant's view cursor (G:0596/0598, 06A6/06A8 or 072E/0730 by view) = its position

SetupPatch(seed, n_black, n_red, row, col):        # f_6ae20
    SeedLfsr(seed) (f_009bf); f_0cdb0 (per-patch globals: spider at G:0F12 = 0x400, G:0F34 = 0x200, ...)
    **A bug in the original:** a seed is 0 when crt_rand() % 0x7FFF == 0x4000 (1 patch in 32,767); the LFSR then
    stays 0 forever (0 << 1 never carries), every Rand returns 0, and a yard patch hangs in f_0ad9c (the two bugs
    wait for a free cell at (0, 0)). Found 2026-10-30 by `OpenSimAnt.Replay --deps` (a load's new game). The C# port
    seeds such a patch with 0x3751 (a marked DIVERGENCE in NewGame.SetupPatch); the Python reference keeps the hang.
    f_73020(row, col): surface terrain (below)
    n_black += n_black >> 2; n_red += n_red >> 2
    nests: dirt 0x2E everywhere, exit field 0, cells empty; surface occupancy cleared
    nest row 0 (top soil): yard: 0x1C + Rand4 (black, then red, per column); house: col > 3 ?
        0x1C + Rand(2) : 0x1E; exit field row 0 = 0xFF; the pheromone maps cleared
    for each colony (black, then red):
        w = 7 + Rand(6); s = 15 - Rand2                  # per-colony caste odds (out of 16)
        n times: a = RandLow(128) (red: 127 - RandLow(128)); b = Rand64
            tile >= 0x50: dropped (no retry)
            occupied: retried (one more turn) while fewer than 50 collisions so far, else dropped
            r = Rand16: r < w worker 0x10, r < s soldier 0x30, else Rand2 ? male 0x20 : new queen 0x40;
            occ = that + Rand8 (+ 0x80 red)
    entrance tables cleared; black entrance (MakeSurfaceHoleBlack(32)) unless Full Game without
        black ants; red entrance (f_15247(32)) if n_red >= 1
    nest sums, capacities, centroids = 0; G:0242 (water level) = 64
    n > 1: pre-dig (f_6b616 black / f_6b6f3 red, 16 n steps): a random walk from (32, 1), heading
        4, each step turns by Rand(5) - 3 (so it mostly circles), clamped to cols 1..62 and rows 1..62;
        a successful DigCell moves it, reaching row 1 opens another entrance there
    f_0f329: surface ant arrays from the occupancy grid (state 2), count capped at 0x3E5
    nest counts, colony counts = 0; egg spots T:02B4 / T:02B8 = -1
    n_red > 0: red nest f_6bae2, n_black > 0: black nest f_6b95c:
        shaft from (32, 1) down to row 7 + Rand4, each row drifting Rand(3) - 1 columns (black only
        re-draws the drift when Rand2 == 0) within cols 8..56; then 2 diagonal steps; the egg spot
        (black also G:0F0E / G:0F26) is the end; queen chamber f_6ba1c / f_6bb70 at (col + 2, row):
        three cells towards heading 6, the queen (0x62 / 0x6A, red 0xE2 / 0xEA) in state 9;
        G:035E / G:036C colony count + 1
    f_6b7d0: the yellow ant (health 100). Mode 3: the player is the spider (G:0A06 = 2), view 1 at
        (64, 32). Full Game (with T:0C24 == 0): a new queen (0x40) on the surface, up to 100 tries
        for a spot near (32 +- 15, 32 +- 7) on a tile < 0x10. Otherwise a worker (0x10) in the black
        nest at the egg spot. Then f_757dd (via f_2f820): view and cursor on it
    food: G:1050 / G:1060 / G:1040 = 0; mode != 3: f_6bca5(-1) (200 crumbs)
    health 100 / 100; f_79478(0); Census; redraw (f_0256e); view cursors (64, 32), (32, 1)
```

### Moving to another patch (`f_01d48`, Full Game; ported: `newgame.move_to_patch`)

The yard map UI sets the target G:07BC (row 0..11) / G:07BE (col 0..15) and calls `f_01d48`:
```
    target == current (G:07CA / G:07CC): nothing
    refused (sound 0x7E, message box): not a Full Game (0x2710); G:03E2 <= 1 and black pop <= 1 (0x2712);
        no black colony in the target's yard cell T:00A4[row*16 + col], unless the yellow ant is an
        unsettled new queen (type 0x40, T:0C24 == 0) (0x2714)
    else: current = target; G:0354 = 1; the flight counters G:07C8, G:0850, G:06AA, G:073A = 0;
        T:0C24 = 1; f_6ae20(seed[col*12 + row], T:00A4[cell], T:0164[cell], row, col)
        (the yard cell values are the colony sizes); no reds there: red health 0;
        message 0x2716 (yard) or 0x2717 (house, idx <= 36)
```
Verified (`test_newgame.py move:`), and `test_newgame.py play` moves into the house and to another
patch, then plays 2000 SimSteps side by side.

### The house (`f_7304b`, ported: `terrain.house_patch`)

Yard rows 0..1 and row 2 cols 0..5 (idx <= 37; `f_73020` compares signed) are the house. Entering it
switches the tile set (T:07A0 = 1001, `f_0286a(0, 1001)` → `f_02756(1)`: G:0F24 = 1, cached in DS:1A2E,
house tile graphics; G:0480 = 0x90 highest passable tile); the generic generator switches back
(1000, G:0480 = 0x50). House patches get no ant lion pits (`f_0afce(0)`) and no wandering bugs, then one
of the layouts (G:0F3A = room: 0 tiled floor, 1 wall on the left, 2 counter / plain, 3 wall on the right):

| idx | layout |
|---|---|
| 0 | counter (`f_734d3`) + the big fitting below it (`f_735d5`) |
| 1, 16, 32 | counter: tiles 0x62 (b 0..23) with 0x66..0x69 seams, two 9x13 boxes (`f_738b7`) |
| 2, 3, 17..19, 33..35 | tiled floor (`f_73236`): 16x16 checks of 0/1, grout 0x5C..0x61 |
| 4, 10, 11, 13, 14 | wall on the left (`f_73350`): 0x64 / 0x7A / 0x7B, floor 3 with 1/200 0x3E..0x3F, a 13x9 box |
| 5..8, 12, 15 | wall on the left + a rug (fill 2, or `f_73b54`: 1/20 cells 0x38 + Rand(5), 0xC0 corners) and 3x3 pictures |
| 9 | floor 3 everywhere (room 2) |
| 20..31 | wall on the right (`f_7343d`) |
| 36, 37 | tile 0 everywhere (room 2) |

Pictures come from DGROUP tables (DS:2C5A, 2C6E, 2C82, 2C9C, 2CA6). In the house, food crumbs are
tiles 0x18..0x27 (`f_6bca5`: floor t < 4 → (t + 6) * 4, sic, a stale CL; t < 0x18 → ((t - 8) & 0xFC)
+ 0x18; crumbs grow while t % 4 < 3).

### Surface terrain (section 20, entry `f_73020(row, col)`)

`idx = row*16 + col`. Patches with `idx <= 37` are the house (above). All other patches use the generic
generator `f_73c33`. RNG = LFSR seeded with the patch seed (`SeedLfsr` `f_009bf` just sets `DS:8ba2`),
so a patch is identical every time it is generated.

```
GenericPatch():                                    # f_73c33
    for a in 0..127: for b in 0..63: surface[a][b] = Rand16()     # 16 ground variants
    repeat Rand(3)+2 times:                        # rocks, f_73dfd
        for shape in 0..5: RockStamp(Rand(122), Rand(58), shape)
    AntLionPits(Rand4()+1)                         # f_0afce, max 10; G:08EA = n
    HazardsReset()                                 # f_0b66c: clears counters; yard: WanderingBugs()
    20 ×: a, b = Rand(125)+1, Rand(61)+1; if the 2×2 block at (a..a+1, b..b+1) is all < 0x18:
          (a,b)=0x20, (a+1,b)=0x21, (a,b+1)=0x22, (a+1,b+1)=0x23
    30 ×: same position rule; if (a,b) and (a+1,b) < 0x18: t = (Rand(2)+0x12)*2 → (a,b)=t, (a+1,b)=t+1
    100 ×: single cell < 0x18 → 0x28
    128 ×: single cell < 0x18 → 0x51 (rock, impassable)

RockStamp(a, b, shape):                            # f_73fc6, shape table T:08c2 [6][5 b][5 a] bytes
    if any nonzero shape cell lands on a tile > 0x10: return   # all or nothing
    copy the nonzero shape cells into the surface

AntLionPits(n):                                    # f_0afce → n × f_0b016 (see "ant lions" in world.py)
    up to 200 tries: a = Rand(65)+Rand(64); b = Rand(33)+Rand(32)          # centre-biased
        if centre and all 8 neighbours are open ground: stamp; stop
        (after 100 tries a centre that is merely open is accepted)
    stamp (f_0b09c): centre = 0x38; each open neighbour i = 0x30 + DS:1b92[i]
    pit table: G:0a92 a, G:0aa8 b, G:0aba/0acc/0ade = 0 at slot T:0c4a, which counts up to 9

WanderingBugs():                                   # f_0ad9c (yard only), slots 2 then 1
    a, b = Rand(128), Rand(64) on a tile < 0x10; kind (heading) = Rand(8)
    remember a, b, kind, old tile (G:0eae, 0f00, 0f1a, 0f28 + 2 * slot); tile = T:0c52[kind]
```
Open ground (`f_1145c(view, a, b)`): tile < 0x10 on the surface (< 8 in a nest) and no occupant except
the player. Map accessors used everywhere: `GetTile(view, a, b)` `f_117c0`, `GetOccupant` `f_11737`,
`SetTile(view, a, b, t)` `f_1183e` (view 1 = surface).

Surface tile summary: `0x00–0x0F` ground, `0x10–0x17` corpses, `0x18–0x1F`/`0x20–0x28` passable
decorations, `0x30–0x38` ant lion pit (3×3), `0x48–0x4B` food crumbs (what ants pick up), `0x50` nest
entrance, `0x51–0x5F` rocks (impassable), `0x71`/`0x73` wandering bugs.

## Verification plan

Run the original routines **in a CPU emulator** (Unicorn, 16-bit real mode) on `build/flat.bin`: load the
image at linear 0, set `DS = SS = 0x55b3`, seed a sim state, call e.g. `SimStep` (`0894:000e`) and dump
the `0x3e1d` segment. The port then gets compared tick by tick against the original (differential
testing). Patch out display/sound side effects by keeping `patch_visible` (`T:07b2`) = 0, and stub any DOS
interrupts.

## The main loop and game speed (f_15f84)

After start-up (install check, resources, sound, the new-game dialog f_2f848) the main loop runs forever:
input (f_23ae4, f_0046f), a 32-bit loop counter, f_16293, then `next = clock3()` (f_0123e, the clock x3).
If the game is not paused (G:047E == 0), or the yellow ant has an action pending (G:0AA0 != 0) and no
pick-a-target cursor mode is on (G:105E < 10), `next += T:07CE[T:07CC]` and SimStep (f_0894e) runs. Then
the windows are redrawn, and the loop waits until `clock3() >= next`. T:07CC is the speed (set to 1 when
the loop starts): T:07CE = 21, 7, 0 clock3 units (about 0.38 s, 0.13 s, and no wait) for slow, medium and
fast; fast runs as fast as the machine draws. The remake's `GameSession.Advance` follows this, with a
minimum period for fast.

The redraw (decoded 2026-10-29): at Ultra (T:07CC = 3) only when the frame counter G:0A9C & 3 is 0, else every loop;
G:0A9C = (G:0A9C + 1) & 0x3F at the end of each loop. Then, if the Map window is open (f_235a0): with G:0AA6 < 0, the
mouse button down (f_23612) or at Ultra, f_01325(0) and the Map window (thunk 0x2F6E0 → f_6f46a: f_6efd6, the population
report f_6eea5) and G:0AA6 = 0; else, while G:04C0 == 0, the Map window when G:0AA6 bit 0 is set, then G:0AA6 ^= 1:
every other loop, so it lags the game by up to a tick (the 'surface' capture). Then the yard window's colony views
(G:035C > 2 and f_1ccfc: thunk 0x2F83E, else 0x2F6FE), the Edit window (f_0339d, f_033d2), and the wait. The sim never
reads G:0A9C / G:0AA6 / G:04C0; the shell keeps the cadence with its own counters (`Main.MapLoops`).
