"""Capture the original's own screens: boot SIMANT.EXE in the emulator with the planar VGA model (vga.py) and
write what it draws as PNGs, for comparing the remake's screens pixel for pixel.

    python screens.py [out_dir]          boot to the first input wait and save boot.png

Nothing is stubbed: the game draws through its own VGA driver. The output is the player's own game art, so it goes
to a git-ignored folder (default tools/re/build/screens).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from emu import SimEmu  # noqa: E402
from vga import VGA  # noqa: E402


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build', 'screens')
    os.makedirs(out, exist_ok=True)
    e = SimEmu(base=0x100)
    v = VGA(e)
    cs, ip = e.boot(max_insns=1_000_000_000)
    print(f'boot stopped at {cs:04x}:{ip:04x}, mode {e.video_mode:#x}, {v.writes} video writes')
    v.png(os.path.join(out, 'boot.png'))
    print('wrote', os.path.join(out, 'boot.png'))


if __name__ == '__main__':
    main()
