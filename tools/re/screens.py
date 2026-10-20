"""Capture the original's own screens: boot SIMANT.EXE in the emulator with the planar VGA model (vga.py) and
write what it draws as PNGs, for comparing the remake's screens pixel for pixel (pngdiff.py).

    python screens.py [out_dir]

Writes boot.png (the first input wait: Select a Game) and quick.png (after clicking Quick Game and letting the game
run). Nothing is stubbed: the game draws through its own VGA driver. The output is the player's own game art, so it
goes to a git-ignored folder (default tools/re/build/screens).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from emu import SimEmu  # noqa: E402
from vga import VGA  # noqa: E402


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
    v.png(os.path.join(out, 'boot.png'))
    click(e, 370, 165)                            # Quick Game
    e.mouse_event(1, 600, 470, 0)
    e.run(3000, 3_000_000_000)
    print(f'after Quick Game: {v.writes} video writes')
    v.png(os.path.join(out, 'quick.png'))
    print('wrote', out)


if __name__ == '__main__':
    main()
