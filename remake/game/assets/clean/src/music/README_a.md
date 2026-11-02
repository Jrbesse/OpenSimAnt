# Music, batch A (written keys as in docs/clean_pack/music.md, C4 = key 60)

All five pieces are original compositions made from the written spec, general music knowledge and the maker's
own invention; no existing tune was used or imitated. The notes are data in `make_music_a.py` (bars of note-name
strings plus chord strings; bass lines, chord stabs and drum patterns are generated from them); running the script
rewrites the five `.mid` files. 4/4 throughout, 240 ppq.

- **10001, the main theme.** F major (then C major, B-flat major, G major), 160 bpm, 68 bars, about 102 s.
  Form: 4-bar intro (hook announced by the lead over a kick and a held chord) | A, 16 bars (4+4+4+4: the hook
  "C A C F" leaping and answering in 8ths, a rising-sequence middle phrase, a returning cadence) with walking bass,
  off-beat chord stabs, kick on 1 and 3, crack on 2 and 4 | B, 16 bars in C major (a skipping arpeggio tune
  answered higher, then a lyrical dotted-rhythm tune) | calm middle, 8 bars in B-flat major: lead silent, the tuned
  drum and the bell trade a call and answer over a long bass and soft chords | build, 4 bars (rising arpeggios, a
  snare roll that grows, a tom fall) | A again a whole tone higher (G major), bigger: the bell doubles the lead in
  the answering phrases, 4-on-the-floor kick, busier ticks | finish, 4 bars (a flourish, a dominant run, a
  ritardando, a long G-major chord on lead, chords and bass with a kick).
- **10006, spare: a bright flourish.** C major, 137 bpm, 12 bars, about 21 s. One-bar scale and arpeggio sweeps on the
  lead (roughly G3 to D6) over C | G | Am | F, Dm | G | C | Am, F | G7 | C | C; a bell ping on the first beat of
  each bar, sustained chord dyads, a light kick / crack / shaker beat.
- **10007, spare: a bouncy interlude.** G major, 120 bpm, 12 bars, 24 s. Hopping arpeggio figures in 3+3+2
  groupings (G Em C D | G Em Am D7 | C G D G), tuned drum as the bouncing low line, short off-beat chord stabs,
  crack on 2 and 4, a shaker, two bell flicks at the turnarounds.
- **10008, victory.** G major, 164 bpm, 20 bars, about 29 s. A two-bar fanfare call built from fourths and fifths;
  an 8-bar rousing tune (rising 4ths, 3+3+2 arpeggios, a cadence on a held G); a 6-bar sequence (a repeated-note
  figure climbing one step per bar, G A B C, with a growing snare roll); a 3-bar climax with the ritardando starting
  in its last bar; a last bar with the held G chord on lead, chords (2) and bass (3). The tuned drum plays the low
  line, there is no bass voice before the last chord.
- **10010, defeat.** D minor, 102 bpm, 13 bars of march plus a 1-bar coda at 80 bpm, about 34 s. A slow plodding
  march (kick on 1 and 3, dyad stabs on 2 and 4, a bass alternating root and fifth). The tune is on the bell: falling
  phrases (F E D, G F E-flat, then a falling line into the dominant), a comic "wobble" (E D E D C#) near the end, a sinking
  last arpeggio over a final D minor chord.
