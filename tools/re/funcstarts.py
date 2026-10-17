"""Function entry detection for build/flat.bin (MSC 6 prologues, after build_flat.py's _chkstk patch).

MSC functions start with `[push bp; mov bp, sp;] mov ax, N | xor ax, ax ; call _chkstk`. build_flat.py turns
that into `sub sp, N ; nop x4` or `nop x7`, so the frameless forms are matched here, with a return
instruction just before them to avoid false hits on the 7-NOP form.
"""
import re

FRAME = rb'\x55\x8b\xec'                                  # push bp; mov bp, sp
FRAMELESS = [rb'\x81\xec..\x90\x90\x90\x90',             # sub sp, N (was mov ax,N; call _chkstk)
             rb'\x90\x90\x90\x90\x90\x90\x90',           # (was xor ax,ax; call _chkstk)
             rb'\x2b\xe0\x90\x90\x90']                    # sub sp, ax (unpatched form)
RETS = (0xcb, 0xc3, 0xca, 0xc2, 0x00)


def find_starts(flat):
    starts = {m.start() for m in re.finditer(FRAME, flat)}
    for p in FRAMELESS:
        for m in re.finditer(p, flat, re.S):
            a = m.start()
            if p.startswith(b'\x2b'):
                a -= 2                                    # include the preceding mov ax / xor ax
            if flat[a - 3:a] == b'\x55\x8b\xec':
                continue
            if flat[a - 1] in RETS:
                starts.add(a)
    return starts
