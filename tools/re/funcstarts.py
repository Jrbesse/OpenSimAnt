"""Function entry detection for build/flat.bin (MSC 6 prologues)."""
import re

FRAME = rb'\x55\x8b\xec'                                  # push bp; mov bp, sp
FRAMELESS = [rb'\x33\xc0\x2b\xe0\x90\x90\x90',            # xor ax,ax; sub sp,ax (patched _chkstk)
             rb'\xb8..\x2b\xe0\x90\x90\x90']               # mov ax,N;  sub sp,ax (patched _chkstk)


def find_starts(flat):
    starts = {m.start() for m in re.finditer(FRAME, flat)}
    for p in FRAMELESS:
        for m in re.finditer(p, flat, re.S):
            a = m.start()
            if flat[a - 3:a] != b'\x55\x8b\xec':
                starts.add(a)
    return starts
