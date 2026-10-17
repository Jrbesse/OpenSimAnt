"""Constant tables, read at runtime from the user's own SIMANT.EXE (via tools/re/build/flat.bin).

Nothing here is copied into the repository: run tools/re/build_flat.py against your copy of the game first.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
FLAT = os.path.join(_HERE, '..', '..', 're', 'build', 'flat.bin')
T_BASE = 0x3d570       # segment 0x3d57: constant tables
DS_BASE = 0x55b30      # DGROUP

_flat = None


def _data():
    global _flat
    if _flat is None:
        _flat = open(FLAT, 'rb').read()
    return _flat


def t_bytes(off, n):
    return _data()[T_BASE + off:T_BASE + off + n]


def ds_bytes(off, n):
    return _data()[DS_BASE + off:DS_BASE + off + n]


def signed(b):
    return b - 256 if b > 127 else b


DIR_DX = [signed(b) for b in t_bytes(0x0000, 8)]        # headings 0=N .. 7=NW
DIR_DY = [signed(b) for b in t_bytes(0x0008, 8)]
T_WALK = [list(t_bytes(0x0024 + d * 8, 8)) for d in range(8)]
ROCK_SHAPES = [[list(t_bytes(0x08c2 + (s * 5 + b) * 5, 5)) for b in range(5)] for s in range(6)]  # [shape][b][a]
SMALL_ROCK_SHAPES = [[list(t_bytes(0x0958 + (s * 3 + b) * 3, 3)) for b in range(3)] for s in range(6)]
PILE_EDGE = list(ds_bytes(0x1b92, 8))                    # food pile neighbour tile offsets (+0x30)
SPECIAL_OBJECT_TILE = list(t_bytes(0x0c52, 8))
