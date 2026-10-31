"""Writes remake/src/OpenSimAnt.Sim/GameTables.cs: the numbers the game reads from SIMANT.EXE's data, as named tables.

    python gen_game_tables.py [deps.txt]

ROADMAP A2. The owner allowed committing these numbers (2026-10-30, HANDOFF "Constraints"): numbers only, never
art, text, sound or fonts. Each table below has a name and a description; the bytes come from the player's own
flat image (tools/re/build/flat.bin). `deps.txt` (OpenSimAnt.Replay --deps, with the shell's reads merged in from
deps_ui.py) lists the bytes the game reads before writing them; the script fails if one of the non-zero ones is not
inside a named table, so the list stays complete.
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FLAT = os.path.join(ROOT, 'tools', 're', 'build', 'flat.bin')
OUT = os.path.join(ROOT, 'remake', 'src', 'OpenSimAnt.Sim', 'GameTables.cs')
SEGS = {'T': 0x3d57, 'SIM': 0x3e1d, 'G': 0x50f6, 'DS': 0x55b3}
LO = 0x3d570

# (segment, first offset, end offset (exclusive), name, description)
TABLES = [
    ('T', 0x000, 0x008, 'HeadingDx', 'x step per heading 0..7 (N, NE, E, SE, S, SW, W, NW); also Rand8 scatter offsets'),
    ('T', 0x008, 0x010, 'HeadingDy', 'y step per heading'),
    ('T', 0x010, 0x01a, 'NeighbourDx', 'x offsets of the cell and its neighbours, for neighbour scans'),
    ('T', 0x01a, 0x024, 'NeighbourDy', 'y offsets of the cell and its neighbours'),
    ('T', 0x024, 0x064, 'WalkTurns', 'T_WALK[heading][Rand8()]: the next heading of a wandering ant'),
    ('T', 0x06c, 0x074, 'HeadingFan', 'heading changes tried in turn around a wanted heading'),
    ('T', 0x074, 0x094, 'CarryingCaste', 'u16 per caste type: 1 for the castes that carry something (food +1, dirt +3)'),
    ('T', 0x094, 0x0a4, 'EmptyCaste', 'per caste type: the caste with nothing carried'),
    ('T', 0x30e, 0x4ce, 'MapColours', 'the Map window\'s 16-colour indices: surface tiles T:030E (house T:039E), '
                                      'occupants T:046E[o >> 3], nest dirt T:04A6[dirt >> 2] (MapArt.MapColour)'),
    ('T', 0x67e, 0x6de, 'CheatCodes', 'the cheat codes, 4 bytes each, bitwise NOT-ed, ending at a 0 (Cheats.TABLE)'),
    ('T', 0x7a2, 0x7c0, 'StartSettings', 'start-up values: the tutorial counter T:07A2, the Options flags T:07A8.., '
                                         'the patch-visible flag T:07B2, the map tools\' options T:07B6..T:07BC'),
    ('T', 0x7ce, 0x7d6, 'SpeedDelays', 'the main loop\'s wait per speed in clock3 units (21, 7, 0, -1 = Ultra)'),
    ('T', 0x7ec, 0x82a, 'ColonyPresets', 'the Behavior / Caste panels\' Set 1..3 presets and start-up weights '
                                         '(NewGame.InitColonySettings)'),
    ('T', 0x88e, 0x8a2, 'StartWords088E', 'start-up words the simulation reads (two are 1; use not decoded yet)'),
    ('T', 0x8c2, 0x98e, 'RockShapes', 'the terrain generator\'s boulders [6][5][5] (T:08C2) and small rocks [6][3][3] '
                                      '(T:0958), tile numbers, 0 = leave the cell'),
    ('T', 0x994, 0x9d4, 'SpiderMoves', 'the spider: step per heading (T:0994 x, T:099C y), its mouth (T:09A4 / '
                                       'T:09AC), scene picture ids T:09B4, body offsets T:09BC / T:09C4, large frames '
                                       'T:09CC / T:09D0'),
    ('T', 0xb14, 0xb28, 'ScenePositions', 'where the window-26 scenes put their overlay pictures (x, y pairs)'),
    ('T', 0xb36, 0xc0e, 'CasteChoice', 'the caste a new ant gets by colony priority and Rand8: red T:0B36 [7][8], '
                                       'T:0B66 / T:0B6E, black workers T:0B9E [6][8], soldiers T:0BCE [6][8], '
                                       'T:0BFE per caste'),
    ('T', 0xc1a, 0xc1c, 'BreedTimer', 'start value of the breeding timer T:0C1A (40)'),
    ('T', 0xc26, 0xc28, 'StartWordC26', 'start value of T:0C26 (-1)'),
    ('T', 0xc36, 0xc3e, 'HumanDrift', 'the roaming human\'s x / y step per heading (T:0C36, T:0C3A)'),
    ('T', 0xc52, 0xc5a, 'BugTiles', 'the wandering bugs\' tile per kind (Rand8)'),
    ('SIM', 0x102e0, 0x10c80, 'SaveBlocks', 'the saved game\'s block table: {count, size, far pointer} per block, '
                                            'ending with size 0 (SaveFile, FILE_FORMATS "Saved games")'),
    ('DS', 0x1a58, 0x1a5d, 'ColourModes', 'the map driver\'s colour modes by foreground (MapArt)'),
    ('DS', 0x1b46, 0x1b4e, 'PanelBarColours', 'the Caste (DS:1B46) and Behavior (DS:1B4A) panels\' bar colours'),
    ('DS', 0x1b62, 0x1b66, 'PanelPercent', 'the panels\' "show percent" flags at start-up'),
    ('DS', 0x1b72, 0x1b9a, 'FightTables', 'fights: class per ant type DS:1B72, odds [4][4] DS:1B82, the corpse tile by '
                                          'heading DS:1B92'),
    ('DS', 0x1ba2, 0x1bab, 'RedJobByCaste', 'a red ant\'s job after a fight it won, by caste'),
    ('DS', 0x1bb2, 0x1bba, 'EntranceRing', 'the tiles around a nest entrance, by heading'),
    ('DS', 0x2448, 0x26c6, 'YardActors', 'the yard layer: the dog\'s steps and sprites (DS:2448..), the walking '
                                         'human\'s state durations DS:245E, next states, frames and odds '
                                         '(DS:25DC..DS:2684), headings DS:268E, the roaming human\'s sprites and '
                                         'offsets (DS:269A..DS:26BE) (SIM_NOTES "The yard layer")'),
    ('DS', 0x2a12, 0x2ada, 'YardWindowOffsets', 'the yard window\'s actor and colony-view offsets (YardRenderer)'),
    ('DS', 0x2af8, 0x2b00, 'ScoreWeights', 'the efficiency score\'s weight per statistic'),
    ('DS', 0x2c5a, 0x2cae, 'HousePictures', 'the house patches\' stamped tile pictures (Terrain.Blit): 5 x 4 at DS:2C5A, '
                                            '4 x 5 at DS:2C6E, 5 x 5 at DS:2C82, then DS:2C9C and DS:2CA6; tile numbers'),
    ('DS', 0x2df4, 0x2e04, 'WallShapes', 'the wall tile for each mask of wall neighbours (left 8 ...), the map tools'),
    ('DS', 0x5702, 0x5704, 'ActiveWindow', 'start value of the active window word DS:5702 (0x8000: none)'),
    # read outside the State (OpenSimAnt.Data's renderers and sound driver, through OriginalFiles.Flat)
    ('DS', 0x1f9e, 0x1ffe, 'MapDither', 'the 16-colour map driver\'s colour bytes, 4 per colour 0x00..0x17: the dither '
                                         'patterns of the in-between shades (MapRenderer.DitherIndex)'),
    ('DS', 0x68fe, 0x693c, 'OplSlots', 'the sound driver\'s OPL2 operator slots per channel (modulator DS:68FE, carrier '
                                        'DS:6908), register offsets DS:6912, F-numbers per note DS:6924'),
    ('DS', 0x6b9e, 0x6ba0, 'VolumeTablePtr', 'the mixer\'s pointer to its volume tables (DS:6CA3)'),
    ('DS', 0x6ba4, 0x74a3, 'SoundLevels', 'the FM attenuation per velocity DS:6BA4 and the sample mixer\'s 8 volume '
                                           'tables of 256 DS:6CA3'),
    ('DS', 0x74c2, 0x74da, 'SamplePitch', 'the sample player\'s 8.8 pitch step per semitone'),
]

# Read by the game but deliberately left out of the tables:
EXCLUDED = [
    # the red trail map (0x4DA7:0, 64 x 32): the image holds leftover data there (bits of text), not a table; the
    # Map window can show it before the game first writes it, and its scent view reads up to a row past the end
    # (into more leftover bytes, up to the save table). A clean start has zeros.
    ('SIM', 0xfaa0, 0x102e0),
    # the spider's leg geometry (the coordinate tables SpiderLegs.cs draws from): line art, so it is an asset of
    # the clean pack, not a game table (ART_PLAN section 3 "Spider"). GameSession puts it in place.
    ('T', 0x9e4, 0xb14),
]


def flat():
    return open(FLAT, 'rb').read()


def needed(deps):
    """(linear address, image byte) of every non-zero byte the game reads before writing (from deps.txt ranges)."""
    res = []
    img = flat()
    for line in open(deps):
        m = re.match(r'(\w+):([0-9a-f]+) \+(\d+)\s+read', line)
        if not m:
            continue
        lin = SEGS[m.group(1)] * 16 + int(m.group(2), 16)
        for a in range(lin, lin + int(m.group(3))):
            if img[a]:
                res.append(a)
    return res


def cs_bytes(b):
    rows = []
    for i in range(0, len(b), 24):
        rows.append('            ' + ', '.join('0x%02x' % x for x in b[i:i + 24]) + ',')
    return '\n'.join(rows)


def main():
    deps = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'remake', 'build', 'deps.txt')
    img = flat()
    spans = [(SEGS[s] * 16 + lo, SEGS[s] * 16 + hi) for s, lo, hi, _, _ in TABLES]
    spans += [(SEGS[s] * 16 + lo, SEGS[s] * 16 + hi) for s, lo, hi in EXCLUDED]
    for s, lo, hi, name, _ in TABLES:                       # no text in a table
        b = img[SEGS[s] * 16 + lo:SEGS[s] * 16 + hi]
        t = re.search(rb'[A-Za-z]{2,} [A-Za-z]{2,}', b)    # words with a space between: text, not numbers
        if t:
            print('warning: %s holds text-like bytes at +%d: %r' % (name, t.start(), t.group()))
    missing = [a for a in needed(deps) if not any(lo <= a < hi for lo, hi in spans)]
    if missing:
        runs = []
        for a in missing:
            if runs and a - runs[-1][1] <= 4:
                runs[-1][1] = a + 1
            else:
                runs.append([a, a + 1])
        for lo, hi in runs:
            seg = max((v for v in SEGS.items() if v[1] * 16 <= lo), key=lambda v: v[1])
            print('not in a named table: %s:%04x +%d' % (seg[0], lo - seg[1] * 16, hi - lo))
        sys.exit(1)
    out = ['// Generated by tools/ref/gen_game_tables.py from the player\'s SIMANT.EXE; do not edit by hand.',
           '// ROADMAP A2: the numbers the game reads from the original\'s data, so it runs without the original files.',
           '// Numbers only (the owner\'s decision, 2026-10-30, HANDOFF "Constraints"): no art, text, sound or fonts.',
           'namespace OpenSimAnt.Sim;', '',
           '/// <summary>The game\'s data tables at their addresses in the State (see SIM_NOTES for each table\'s use).',
           '/// <see cref="NewState"/> builds a starting State from them, as SIMANT.EXE\'s image gives it.</summary>',
           'public static class GameTables', '{',
           '    public readonly record struct Table(int Seg, int Off, string Name, string About, byte[] Bytes);', '',
           '    public static readonly Table[] All =', '    {']
    for s, lo, hi, name, about in TABLES:
        a = SEGS[s] * 16
        out.append('        new(Seg.%s, 0x%04x, "%s", "%s", new byte[]' % (s, lo, name, about.replace('"', '\\"')))
        out.append('        {')
        out.append(cs_bytes(img[a + lo:a + hi]))
        out.append('        }),')
    out += ['    };', '',
            '    /// <summary>A starting State: zeros, plus every table at its place.</summary>',
            '    public static State NewState()',
            '    {',
            '        var mem = new byte[State.Size];',
            '        foreach (var t in All) t.Bytes.CopyTo(mem, t.Seg * 16 + t.Off - State.Lo);',
            '        return new State(mem);',
            '    }', '}', '']
    with open(OUT, 'w', newline='\n') as f:
        f.write('\n'.join(out))
    print('%d tables, %d bytes -> %s' % (len(TABLES), sum(hi - lo for _, lo, hi, _, _ in TABLES), OUT))


if __name__ == '__main__':
    main()
