---
layout: default
title: "deps_ui"
permalink: /reference/deps-ui/
---

# deps_ui

*`deps_ui.py` — Which bytes of SIMANT.EXE's data image the remake's screens read (ROADMAP A2).*

[Reference index]({{ site.baseurl }}/reference/) · [Download `deps_ui.py`]({{ site.baseurl }}/assets/reference/ref/deps_ui.py)

Which bytes of SIMANT.EXE's data image the remake's screens read (ROADMAP A2).

    python deps_ui.py [--godot=<path to the Godot console exe>]

Runs the Godot shell with screenshot flags that open every window in fresh games (no --state: a loaded State hides
what comes from the image), each with --deps=remake/build/deps_ui.bin, which ORs the bytes read before any write
into that file. Then `OpenSimAnt.Replay --deps` adds the simulation's own reads and writes remake/build/deps.txt.

## At a glance

- **45** lines
- **1 top-level functions**, including `main`

## Source

{% raw %}
```python
"""Which bytes of SIMANT.EXE's data image the remake's screens read (ROADMAP A2).

    python deps_ui.py [--godot=<path to the Godot console exe>]

Runs the Godot shell with screenshot flags that open every window in fresh games (no --state: a loaded State hides
what comes from the image), each with --deps=remake/build/deps_ui.bin, which ORs the bytes read before any write
into that file. Then `OpenSimAnt.Replay --deps` adds the simulation's own reads and writes remake/build/deps.txt.
"""
import os, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GODOT = r'C:\Godot\Godot_v4.6.2-stable_mono_win64\Godot_v4.6.2-stable_mono_win64_console.exe'
OUT = os.path.join(ROOT, 'remake', 'build', 'deps_ui.bin')

ALL = ['--history', '--map-front', '--panels', '--antipedia']
RUNS = [
    [], ['--title'], ['--select'], ['--full'], ['--experimental'], ['--tutorial'], ['--tutorial=12'],
    ['--ticks=3000'], ['--full', '--ticks=3000'], ['--experimental', '--ticks=2000', '--exp-menu'],
    ['--silly', '--ticks=3000'], ['--trails', '--ticks=1500'], ['--report'], ['--mini-map'], ['--scent-menu'],
    ['--efficiency'], ['--status'], ['--help-overlay'], ['--popup'], ['--ant-info'], ['--strat'],
    ALL, ALL + ['--yard'], ['--full'] + ALL + ['--yard', '--strat'], ['--full', '--yard'],
    ALL + ['--about=0,0'], ALL + ['--save-prompt=4'], ALL + ['--load-dialog'], ALL + ['--save-dialog='],
    ALL + ['--alert'], ALL + ['--saved'], ALL + ['--error'], ALL + ['--edit-front', '--start-windows'],
    ALL + ['--game-over'], ['--win'], ['--full', '--win'],
    ['--menu=0'], ['--menu=1'], ['--menu=2'], ['--menu=3'], ['--menu=4'],
] + [['--scene=%d' % n] for n in range(0, 8)]


def main():
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    godot = opts.get('godot') or next((g for g in (GODOT, os.environ.get('GODOT')) if g and os.path.isfile(g)), GODOT)
    if os.path.exists(OUT):
        os.remove(OUT)
    shot = os.path.join(tempfile.gettempdir(), 'opensimant_deps.png')
    for flags in RUNS:
        cmd = [godot, '--path', os.path.join(ROOT, 'remake', 'game'), '--',
               *flags, '--screenshot=' + shot.replace('\\', '/'), '--deps=' + OUT.replace('\\', '/')]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        print(' '.join(flags) or '(start)', 'ok' if r.returncode == 0 else 'exit %d' % r.returncode)
    n = sum(open(OUT, 'rb').read()) if os.path.exists(OUT) else 0
    print('%d bytes read from the image, in %s' % (n, OUT))


if __name__ == '__main__':
    main()
```
{% endraw %}
