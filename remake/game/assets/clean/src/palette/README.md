# Palette

`palette.json` is the game's 16-colour palette (HCEGANT type 15, id 0): the standard Apple Macintosh 16-colour
system palette, in index order (0 white .. 15 black). It is a public palette, not the original game's data.

The colours are the standard 16-bit-per-channel Mac values, written as their high bytes. `MapArt` reads each
channel's top six bits, so the low bits do not change what the game shows.

`python tools/clean_pack/build.py` encodes it as `HCEGANT/15/0.bin`: a little-endian u16 count (16, as the original's entry), then R, G, B per
colour, 50 bytes in all (the original entry's size; nothing follows the colours).
