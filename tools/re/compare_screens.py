"""Compare the remake's screens with the original's (captured by screens.py) pixel for pixel.

    python compare_screens.py [name ...] [--godot=<path to the Godot console exe>] [--out=<dir>]

For each capture <name>.png in build/screens that has a <name>.state, runs the remake with `--state=<name>.state`
(the original's memory, held still; the timed message from <name>.msg) plus the flags that open the same windows in
the same order, screenshots it and prints pngdiff's count. The remake's screenshots and the diff images (differing
pixels in magenta) go to --out (default build/screens/remake). Godot: --godot, else the path in the handoff, else
$GODOT. The game must be built first (dotnet build remake/game/OpenSimAnt.csproj).

A display is required: `--headless` renders nothing (dummy renderer, blank frame). On a machine with no X session
(the Hermes box) the script runs Godot under `xvfb-run` itself, the same recipe tools/shots.sh uses, so no display
has to be exported. Windows and macOS need no display server and never set `DISPLAY`; Godot opens its own window
there, so neither `DISPLAY` nor `xvfb-run` is looked for on those hosts. To use an X display that already exists,
set it -- the editor's virtual display works:

    DISPLAY=:99 GODOT=/opt/godot/Godot_v4.6.2-stable_mono_linux_x86_64/Godot_v4.6.2-stable_mono_linux.x86_64 \
        ~/work/simant-venv/bin/python compare_screens.py            # every capture
    # off the box, or with xvfb not installed, wrap it yourself:
    xvfb-run -a -s "-screen 0 1280x1024x24" python compare_screens.py about load filedlg

Exit status is 1 when a comparison that was asked for did not happen: a render that saved no frame, a capture with no
`.png` to compare against, or a capture with no `.state`. An absent capture fails in the default sweep as well as when
named by hand -- on a clone whose reference set was never recorded (docs/NIGHTLY.md: it is per clone and goes stale
silently) an empty run must not read as a pass -- with one exception, OPTIONAL below: `savedlg` / `overwrite` / `saved`
/ `savecancel` have no capture, because screens.py writes the save prompt only when the game has unsaved changes, and
naming one of those by hand is a request, so it exits 1 like any other absent name. A run that compares nothing at all
exits 1 whatever the names.

A capture can be one simulation step behind its own `.state`: the original repaints the Map window after the
step (f_6efd6), so its ants can still be at the cells they had before that step's moves — that is the whole
256-px `surface` diff of B16. The yard shows the same lag: B18's 9 px are the dog's tail (x=288, the brown
right-hand column of frame 8510) and a porch flower (x=264, a 1-px pink/purple stem) — animation elements at the
capture instant's phase, one step before `yard.state`'s (G:04E4=10); the capture's dog body is still 8510 and its
human 8001, so it is not a body-frame drift. The dog is drawn through a clip / sprite-layer path (f_6feb3,
DS:2A30 / G:10DA) the remake does not model, and those values are animation-dependent; the flower is in no
capture's actor list and no archive bitmap. Check the State before calling such a difference a render bug: the
OCC grid and the ant arrays (SX / SY / STYPE) agree at the capture instant, so the render is drawing what memory
holds.

Which window the capture held is the original's own z-order (DS:5702), and `--state=` puts it back by itself:
the stack windows (Edit, Map, History, yard, SimAntipedia, Behavior, Caste) and the front modal. The front modal
is restored from the State alone for the title (3), Select a Game (2), the Efficiency Score (24), game over (4),
the About box (31) and the save prompt (33); the Ant Info window (29) also needs the cell it was held on, which
screens.py writes to `<name>.cell` beside the state (the game reads it there). So the flags for those five
captures are redundant, and are kept only as a re-statement of how each window was opened.

The one modal `--state=` cannot restore is the file dialog (22): its list is the filesystem (the folders, then
`*.ant`), and neither the directory nor the selection is in the original's memory. `--load-dialog --file-dir=…`
is the capture-time workaround and stays in FLAGS below; a bare `--state=` render of `filedlg.state` leaves the
dialog out and says so on stderr (that is 63902 px, not a render bug). The `…` is not this machine's directory:
each capture whose flags carry `--file-dir=` gets its own fresh fixture directory (file_fixture.py) rebuilt from
that capture's <name>.files sidecar — the names screens.py recorded when it recorded the capture — or from the
fixture's canonical names for a capture set recorded before the sidecar existed, so the pair is comparable on any
machine (#54). `filedlg` and `savedlg` record their own sidecars and render against their own lists.
"""
import atexit
import os
import shutil
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
    'house': ['--history', '--map-front', '--panels', '--antipedia', '--yard'],
    'strat': ['--history', '--map-front', '--panels', '--antipedia', '--yard'],
    'graphic': ['--history', '--map-front', '--panels', '--antipedia', '--yard'],
    'card': ['--history', '--map-front', '--panels', '--yard', '--antipedia'],
    'yardfront': ['--history', '--map-front', '--panels', '--yard', '--antipedia', '--yard'],
    'mapback': ['--history', '--panels', '--antipedia', '--map-front'],
    'scent1': ['--history', '--panels', '--antipedia', '--map-front'],
    'scent3': ['--history', '--panels', '--antipedia', '--map-front'],
    'mapnest': ['--history', '--panels', '--antipedia', '--map-front'],
    'about': ['--history', '--panels', '--antipedia', '--map-front', '--about=0,0'],
    'load': ['--history', '--panels', '--antipedia', '--map-front', '--save-prompt=4'],
    'filedlg': ['--history', '--panels', '--antipedia', '--map-front', '--load-dialog',
                '--file-dir=$'],
    'cancel': ['--history', '--panels', '--antipedia', '--map-front'],
    'savedlg': ['--history', '--panels', '--antipedia', '--map-front', '--save-dialog=',
                '--file-dir=$'],
    'overwrite': ['--history', '--panels', '--antipedia', '--map-front', '--alert'],
    'saved': ['--history', '--panels', '--antipedia', '--map-front', '--saved'],
    'savecancel': ['--history', '--panels', '--antipedia', '--map-front'],
    'menu_options': ['--history', '--panels', '--antipedia', '--map-front', '--menu=3', '--cursor=240,8'],
    'menu_speed': ['--history', '--panels', '--antipedia', '--map-front', '--menu=4', '--cursor=322,8'],
    'editfront': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front'],
    'popup': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front', '--popup=@'],  # @: popup.at
    'antinfo': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front', '--ant-info=#'],  # #: antinfo.cell
    'antinfo_gone': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front'],
    'newselect': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front', '--select'],
    'exp': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front', '--start-windows'],
    'expmenu': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front', '--start-windows', '--map-front',
                '--exp-menu'],
    'gameover': ['--history', '--panels', '--antipedia', '--map-front', '--edit-front', '--start-windows', '--map-front',
                 '--game-over'],
    'menu': ['--menu=0', '--cursor=20,8'],
    'menu_window': ['--menu=1', '--cursor=90,8'],
    'menu_view': ['--menu=2', '--cursor=160,8'],
}
CURSOR = '--cursor=600,470'                       # screens.py parks the mouse there
XVFB = ['xvfb-run', '-a', '-s', '-screen 0 1280x1024x24']   # tools/shots.sh's recipe
OPTIONAL = {'savedlg', 'overwrite', 'saved', 'savecancel'}  # screens.py writes these only with unsaved changes


def display_wrapper():
    """The prefix that gives Godot a display, or [] when it needs none or DISPLAY already names one.

    Godot without a display renders nothing, and `--headless` is worse: it is a dummy renderer that saves a blank
    frame without complaining. So on a host with no X session (the Hermes box) run it under xvfb; when there is
    neither a DISPLAY nor xvfb-run, stop with one line instead of a traceback on the missing PNG.

    Windows and macOS need no display server and never set DISPLAY -- and Windows is the host this file defaults to
    (GODOT above) -- so they answer before the X11 test, which is only true there.
    """
    if os.name == 'nt' or sys.platform == 'darwin':
        return []
    if os.environ.get('DISPLAY'):
        return []
    if shutil.which(XVFB[0]):
        return XVFB
    sys.exit('compare_screens.py: no DISPLAY and no xvfb-run -- set DISPLAY to an X display (the editor\'s is '
             'DISPLAY=:99) or install xvfb; a --headless run would only save a blank frame.')



def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    godot = opts.get('godot') or next((g for g in (GODOT, os.environ.get('GODOT')) if g and os.path.isfile(g)), GODOT)
    if not os.path.isfile(godot):
        sys.exit(f'compare_screens.py: no Godot at {godot} -- pass --godot=<mono binary> or set $GODOT '
                 '(the Hermes box has it under /opt/godot, see the docstring).')
    out = opts.get('out') or os.path.join(SCREENS, 'remake')
    os.makedirs(out, exist_ok=True)
    wrapper = display_wrapper()
    sys.path.insert(0, HERE)
    import pngdiff  # noqa: E402
    import file_fixture  # noqa: E402
    fixtures = {}       # per capture: its --file-dir fixture, from its own <name>.files sidecar (#54)
    missing = []
    compared = 0
    for name in args or FLAGS:
        state = os.path.join(SCREENS, name + '.state')
        if not os.path.exists(state):
            print(f'{name:10s} no capture (run screens.py)')
            if args or name not in OPTIONAL:      # an absent capture fails unless it is a tolerated save prompt
                missing.append(name)
            continue
        ref = os.path.join(SCREENS, name + '.png')
        if not os.path.exists(ref):
            print(f'{name:10s} no {name}.png to compare against (run screens.py)')
            missing.append(name)
            continue
        shot = os.path.join(out, name + '.png')
        cmd = wrapper + [godot, '--path', os.path.join(ROOT, 'remake', 'game'), '--',
                         '--state=' + state.replace('\\', '/')]
        flags = FLAGS.get(name, [])
        if any('--file-dir=' in f for f in flags):
            # the file dialog's list is the filesystem (the docstring): render against a fresh fixture directory
            # rebuilt from this capture's own sidecar, not whatever this clone's build/screens/files holds, so
            # the pair is comparable on any machine (#54). filedlg's and savedlg's sidecars are separate, and so
            # are their fixtures
            if name not in fixtures:
                fixtures[name] = file_fixture.build_for_render(SCREENS, name)
                atexit.register(shutil.rmtree, fixtures[name], True)
            flags = [f.replace('$', fixtures[name]) for f in flags]
        at = os.path.join(SCREENS, name + '.at')
        if os.path.exists(at):                    # a press point saved by screens.py: the flag's '@' and the cursor
            xy = open(at).read().strip()
            flags = [f.replace('@', xy) for f in flags] + ['--cursor=' + xy]
        cell = os.path.join(SCREENS, name + '.cell')
        if os.path.exists(cell):                  # the map cell pressed on: the flag's '#'
            flags = [f.replace('#', open(cell).read().strip()) for f in flags]
        cmd += flags + ([] if any(f.startswith('--cursor') for f in flags) else [CURSOR])
        cmd += ['--screenshot=' + shot.replace('\\', '/')]
        if os.path.exists(shot):
            os.remove(shot)                       # a frame from an earlier run must not stand in for this one
        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180)
        except subprocess.TimeoutExpired:
            print(f'{name:10s} the render did not finish in 180 s')
            missing.append(name)
            continue
        if not os.path.exists(shot):
            tail = proc.stderr.decode(errors='replace').strip().splitlines()[-1:] or ['(no output)']
            print(f'{name:10s} saved no frame (exit {proc.returncode}): {tail[0]}')
            missing.append(name)
            continue
        _, _, a = pngdiff.read_png(ref)
        _, _, b = pngdiff.read_png(shot)
        diff = [(x, y) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]]
        box = ''
        if diff:
            xs, ys = [p[0] for p in diff], [p[1] for p in diff]
            box = f'  in ({min(xs)}, {min(ys)}) .. ({max(xs) + 1}, {max(ys) + 1})'
            subprocess.run([sys.executable, os.path.join(HERE, 'pngdiff.py'), ref, shot,
                            '--out', os.path.join(out, name + '_diff.png')], stdout=subprocess.DEVNULL)
        print(f'{name:10s} {len(diff):6d} pixels differ{box}')
        compared += 1
    if missing:
        sys.exit(f'{len(missing)} capture(s) produced no comparison: {" ".join(missing)}')
    if not compared:                              # zero comparisons is the empty set, not a pass
        sys.exit(f'compare_screens.py: nothing compared -- no capture in {SCREENS} (run screens.py)')


if __name__ == '__main__':
    main()
