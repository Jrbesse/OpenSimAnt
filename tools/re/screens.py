"""Capture the original's own screens: boot SIMANT.EXE in the emulator with the planar VGA model (vga.py) and
write what it draws as PNGs, for comparing the remake's screens pixel for pixel (pngdiff.py).

    python screens.py [out_dir]

Writes boot.png (the first input wait: Select a Game) and quick.png (after clicking Quick Game and letting the game
run), each with a .state file beside it: the game's memory (State, 0x3d570..0x62000) at that moment, which the
remake loads with `-- --state=<file>` to draw the same game (the comparison is then independent of game state). Nothing is stubbed: the game draws through its own VGA driver. The output is the player's own game art, so it
goes to a git-ignored folder (default tools/re/build/screens).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from emu import SimEmu  # noqa: E402
from vga import VGA  # noqa: E402


LO, HI = 0x3d570, 0x62000                         # simant_ref.state: the State's memory


def shot(e, v, path):
    """The screen as a PNG and the State bytes beside it (path with .state for .png)."""
    v.png(path)
    with open(path[:-4] + '.state', 'wb') as f:
        f.write(bytes(e.uc.mem_read(e.base * 16 + LO, HI - LO)))
    # the timed message's text (f_15e2c: a far pointer DS:19C6 into the far heap, outside the State), if one is set
    off, seg = struct.unpack('<HH', e.read(0x55b3, 0x19c6, 4))
    msg = b''
    if seg or off:
        msg = bytes(e.uc.mem_read(seg * 16 + off, 256)).split(b'\0')[0]
    with open(path[:-4] + '.msg', 'wb') as f:
        f.write(msg)


def run(e, polls, max_insns=100_000_000):
    e.run(polls, max_insns)


def click(e, x, y, polls=60):
    """A left click through the game's mouse handler: move, press, release."""
    e.mouse_event(1, x, y, 0)
    e.mouse_event(2, x, y, 1)
    run(e, polls)
    e.mouse_event(4, x, y, 0)
    run(e, polls)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build', 'screens')
    os.makedirs(out, exist_ok=True)
    e = SimEmu(base=0x100)
    v = VGA(e)
    cs, ip = e.boot(max_insns=1_000_000_000)
    print(f'boot stopped at {cs:04x}:{ip:04x}, mode {e.video_mode:#x}, {v.writes} video writes')
    shot(e, v, os.path.join(out, 'boot.png'))
    click(e, 370, 165)                            # Quick Game
    e.mouse_event(1, 600, 470, 0)
    e.run(3000, 3_000_000_000)
    print(f'after Quick Game: {v.writes} video writes')
    shot(e, v, os.path.join(out, 'quick.png'))
    e.mouse_event(1, 20, 8, 0)                    # File held open
    e.mouse_event(2, 20, 8, 1)
    e.run(200, 200_000_000)
    v.png(os.path.join(out, 'menu.png'))
    e.mouse_event(4, 300, 300, 0)
    e.run(200, 200_000_000)
    # menus held open, then commands chosen from them; each screen with its State
    for x, name in ((90, 'menu_window'), (160, 'menu_view')):
        hold_menu(e, x)
        v.png(os.path.join(out, name + '.png'))
        e.mouse_event(4, 600, 470, 0)
        run(e, 200)
    for x, y, name in ((160, VIEW_SURFACE, 'surface'), (160, VIEW_RED, 'rednest'), (160, VIEW_BLACK, None),
                       (90, WINDOW_HISTORY, 'history'), (90, WINDOW_MAP, 'mapfront'), (90, WINDOW_STATUS, 'status')):
        choose(e, x, y)
        if name:
            shot(e, v, os.path.join(out, name + '.png'))
            print('  ', name)
    click(e, 300, 300)                            # the Status window closes on a click
    e.mouse_event(1, 600, 470, 0)
    run(e, 100)
    shot(e, v, os.path.join(out, 'closed.png'))
    for x, y, name in ((90, WINDOW_BEHAVIOR, None), (90, WINDOW_CASTE, 'panels'), (90, WINDOW_INFO, 'info')):
        choose(e, x, y)
        if name:
            shot(e, v, os.path.join(out, name + '.png'))
            print('  ', name)
    click(e, 600, 470)                            # leave the SimAntipedia (a click outside it)
    run(e, 100)
    choose(e, 160, VIEW_YARD)
    shot(e, v, os.path.join(out, 'yard.png'))
    print('wrote', out)


# the menus' items (8 x 14 cells under the bar): Window (x 72..) and View (x 136..)
WINDOW_MAP, WINDOW_BEHAVIOR, WINDOW_CASTE, WINDOW_HISTORY, WINDOW_INFO, WINDOW_STATUS = 43, 57, 71, 85, 99, 113
VIEW_YARD, VIEW_SURFACE, VIEW_BLACK, VIEW_RED = 29, 99, 113, 127


def hold_menu(e, x):
    """Press on the menu bar at x and keep the button down: the menu stays open."""
    e.mouse_event(1, x, 8, 0)
    e.mouse_event(2, x, 8, 1)
    run(e, 200, 200_000_000)


def choose(e, x, y, polls=150):
    """Pull down the menu at x, release on the item at row y, park the mouse at (600, 470) and let the game run."""
    hold_menu(e, x)
    e.mouse_event(1, x, y, 1)
    run(e, 60)
    e.mouse_event(4, x, y, 0)
    run(e, 60)
    e.mouse_event(1, 600, 470, 0)
    run(e, polls, 300_000_000)


if __name__ == '__main__':
    main()
