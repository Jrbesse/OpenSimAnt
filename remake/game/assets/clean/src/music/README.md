# Music (the 30 songs)

Composed new from `docs/clean_pack/music.md` (spec only) by two isolated agents working in parallel. The `.mid` files are
standard MIDI files; `tools/clean_pack/build.py` checks them with a port of the game's sequencer and copies them as
`SOUND/20/<id>.bin` (the 33 cues `SOUND/18` are built from `docs/clean_pack/data/song_cues.json`).

| Batch | Songs | Script | Notes per song |
|---|---|---|---|
| A | 10001 (main theme), 10006, 10007, 10008 (victory), 10010 (defeat) | `make_music_a.py` | `README_a.md` |
| B | 10003, 10004, 10005 (ambient themes), and the 22 short pieces 11002..11021, 20000..20011 | `make_music_b.py` | `README_b.md` |

`python make_music.py` writes all 30 (deterministic); it needs no third-party package, so plain `python3` runs it
(unlike the makers that take numpy / Pillow from `../requirements.txt`). After the spec side's render of the songs on the clean FM
patches, the short pieces' main lines were raised to velocities 105..127, and the chord, pluck and lead patches made
louder (`../sounds/README.md`), so the stings sit at about the level of the full pieces.
