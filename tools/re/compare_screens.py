"""Compare the remake's screens with the original's (captured by screens.py) pixel for pixel.

    python compare_screens.py [name ...] [--godot=<path to the Godot console exe>] [--out=<dir>]

For each capture <name>.png in build/screens that has a <name>.state, runs the remake with `--state=<name>.state`
(the original's memory, held still; the timed message from <name>.msg) plus the flags that open the same windows in
the same order, screenshots it and prints pngdiff's count. The remake's screenshots and the diff images (differing
pixels in magenta) go to --out (default build/screens/remake). Godot: --godot, else the path in the handoff, else
$GODOT. The game must be built first (dotnet build remake/game/Formica.csproj).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SCREENS = os.path.join(HERE, 'build', 'screens')
GODOT = r'C:\Godot\Godot_v4.6.2-stable_mono_win64\Godot_v4.6.2-stable_mono_win64_console.exe'

# the windows each capture has open, in the order screens.py opened them (see main() there)
FLAGS = {
    'quick': [],
    'surface': [],
    'rednest': [],
    'history': ['--history'],
    'mapfront': ['--history', '--map-front'],
    'status': ['--history', '--map-front', '--efficiency'],
    'closed': ['--history', '--map-front'],
    'panels': ['--history', '--map-front', '--panels'],
    'info': ['--history', '--map-front', '--panels', '--antipedia'],
    'yard': ['--history', '--map-front', '--panels', '--antipedia', '--yard'],
}
CURSOR = '--cursor=600,470'                       # screens.py parks the mouse there


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    godot = opts.get('godot') or next((g for g in (GODOT, os.environ.get('GODOT')) if g and os.path.isfile(g)), GODOT)
    out = opts.get('out') or os.path.join(SCREENS, 'remake')
    os.makedirs(out, exist_ok=True)
    sys.path.insert(0, HERE)
    import pngdiff  # noqa: E402
    for name in args or FLAGS:
        state = os.path.join(SCREENS, name + '.state')
        if not os.path.exists(state):
            print(f'{name:10s} no capture (run screens.py)')
            continue
        shot = os.path.join(out, name + '.png')
        cmd = [godot, '--path', os.path.join(ROOT, 'remake', 'game'), '--', '--state=' + state.replace('\\', '/')]
        cmd += FLAGS.get(name, []) + [CURSOR, '--screenshot=' + shot.replace('\\', '/')]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        _, _, a = pngdiff.read_png(os.path.join(SCREENS, name + '.png'))
        _, _, b = pngdiff.read_png(shot)
        diff = [(x, y) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]]
        box = ''
        if diff:
            xs, ys = [p[0] for p in diff], [p[1] for p in diff]
            box = f'  in ({min(xs)}, {min(ys)}) .. ({max(xs) + 1}, {max(ys) + 1})'
            subprocess.run([sys.executable, os.path.join(HERE, 'pngdiff.py'), os.path.join(SCREENS, name + '.png'), shot,
                            '--out', os.path.join(out, name + '_diff.png')], stdout=subprocess.DEVNULL)
        print(f'{name:10s} {len(diff):6d} pixels differ{box}')


if __name__ == '__main__':
    main()
