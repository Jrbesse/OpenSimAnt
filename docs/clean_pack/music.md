# Spec: the 30 songs and their cues

> **Status (2026-11-01):** spec written, ready for a maker. The encoder is **in `tools/clean_pack/build.py`**
> (`midi_walk` is the port of the sequencer, `midi_check` the rules, `cat_music`, `cat_cues`; `--roundtrip` checks the port against
> the 30 originals); section "Encoder (for build.py)" describes it, with what its first run measured. The instruments the songs are
> played on are made from a separate spec, [sounds.md](sounds.md) (the FM patches); the table of channel roles
> (section 2) is the contract between the two and is repeated in both.

Output folder: `remake/game/assets/clean/src/music/`. Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an
entry). Thirty short pieces of **original music**, written as standard MIDI files, one per song, for an old
FM-synthesiser sound (the chip of the AdLib and Sound Blaster cards). Compose everything from scratch. **Never quote,
paraphrase or imitate an existing tune** (folk songs, nursery rhymes, classical themes, film or game music): the pack
must not resemble anything that exists. You never see the pieces this set replaces and must not look for them. All
descriptions here are in words; the pace and size figures are measurements of the places the pieces are used, not of
melodies.

## 1. How the game plays music

- A **cue** is a song number the game asks for at some moment (a screen opening, an event). The cue list (section 5) is
  fixed; each cue plays one song, a few cues play the same song transposed.
- **One song at a time.** A new cue stops the song playing at once and starts its own (so the first second or two of
  every piece is what many players hear). Cues asked for within one frame play one after the other.
- **No loops.** A song plays once to its end and stops. The game sometimes waits for the end of a song (the end of a game,
  the win screens, the yellow ant's death scenes), so the length matters (section 3).
- Music can be switched off by the player (Options); effects are separate and have their own voices.
- The pieces share the **eight FM voices of the chip** with the sound effects. Sound effects are less important than
  music to the driver, so the music must **leave room** (the polyphony limit below), or effects are lost.

## 2. The orchestra: ten fixed voices

A song file uses MIDI channels 1..10 (numbered from 0, as in the status byte `0x90 + channel`). Each channel is a fixed
instrument with a fixed priority. **There are no program changes, no General MIDI map, no drum map** (channel 10 in the
standard numbering, 9 from 0, is *not* a drum channel here): a channel number means one patch, a key number means a
pitch.

| MIDI channel | Priority | Patch (sounds.md) | Voice | Written keys to use | Typical velocity | Notes at once |
|---|---|---|---|---|---|---|
| 1 | 7 | `fm25` | **lead melody**: bright, clear, singing | 48..88 | 90..120 | 1 |
| 2 | 7 | `fm53` | **harmony / chords / pad**: round, soft | 40..80 | 60..90 | up to 3 |
| 3 | 7 | `fm3` | **bass**: warm and round | 24..52 | 85..110 | 1 |
| 4 | 7 | `fm54` | **plucked counter-melody**: marimba / string-pluck | 48..88 | 70..105 | 1 (2 for a double stop) |
| 5 | 5 | `fm35` | **deep drum** (kick) | 20..55 | 100..127 | 1 |
| 6 | 5 | `fm46` | **noisy crack** (snare / clap): the key only colours it | 40..80 | 90..115 | 1 |
| 7 | 5 | `fm50` | **very short tick** (hi-hat): the shortest voice | 60..95 | 50..80 | 1 |
| 8 | 5 | `fm51` | **tuned drum** (tom / log drum): clear pitch, can carry a tune | 36..84 | 80..110 | 1 |
| 9 | 5 | `fm48` | **shaker / rattle**: a short noisy swish, the quietest | 50..95 | 40..70 | 1 |
| 10 | 5 | `fm0` | **bell / mallet**: pitched, rings | 60..95 | 70..100 | 1 |

Do not use channels 0 (it never sounds), 11..15.

- **Pitch.** A written key `k` sounds at `440 * 2^((k + 12 - 69) / 12)` Hz: **key 60 sounds at 523 Hz, an octave above
  the usual MIDI convention** (so a bass written at keys 24..52 sounds from about 65 Hz to 330 Hz). Equal temperament, any
  key you like; keys 0..95 sound, 96 and above are silent. Pitch bend, vibrato wheel and controllers do nothing.
- **Loudness.** Only the note-on velocity matters (2..127: the driver scales it by the music volume, 127 at the start, and a
  result of 0 is a note off, so **velocity 1 is silent** and the build refuses it). The patches are balanced so the "typical velocity" column
  puts the voices in a good mix; below about 40 a note is nearly silent. Do not use velocity to fake long fades.
- **Polyphony: at most 6 notes held at once, counting all channels together** (a note is held from its note on to its note
  off). The chip has 8 voices; the other two stay free for sound effects. A drum hit is held for its whole note, so make
  drum notes short (80..200 ms). No two notes of the same key may overlap on one channel (a note off silences every
  sounding note of that key on that channel).
- **Note lengths.** Pitched notes at least 40 ms; drum and tick notes (channels 5..7, 9) at least 80 ms (a note off ends
  the sound early, so a very short note is a click). A note longer than 12 s is not allowed. Every note on needs its note
  off. FM notes fade by themselves, so a long note off is not a "sustain pedal": a note's own envelope decides how long it
  rings, and a pad on channel 2 simply rings longer than a pluck.

## 3. The files

Per song `<song id>.mid` (for example `10001.mid`), plus `make_music.py` (a script that writes **all** the files from the
notes it contains, deterministic, so they can be regenerated; write the MIDI bytes yourself, a variable-length writer is
ten lines, do not rely on a library being installed) and `README.md` (one line per song: what it is and how it goes). A
rendered preview is not possible for you (you have no copy of the driver); the spec side renders everything.

**Standard MIDI file rules** (the sequencer in the game is simple and reads only this):

- Header `MThd`, length 6, **format 1**, track count 2..11, **division 240 ticks per quarter** (not SMPTE).
- **Track 0 is the conductor**: its first event is at delta 0; it holds the tempo (`FF 51 03 tt tt tt`, between 100,000 and
  1,000,000 microseconds per quarter, i.e. 60..600 beats per minute; change it as often as you like), **a tempo event at tick 0** (until the game reads one it assumes 480 ticks per quarter, so a song without one runs at the wrong
  speed at the start), optionally a track name (`FF 03`), the time signature (`FF 58`) and the key signature (`FF 59`); **no
  notes**; and an end-of-track. Any other meta event (SMPTE offset, sequencer-specific, channel prefix) is refused.
- Every other track holds the notes of **one MIDI channel** (one track per channel, at most 10), optionally a track
  name (`FF 03`), and ends with `FF 2F 00`. Only note on (`9n kk vv`, velocity 1..127) and note off (`8n kk vv`; a note on with
  velocity 0 also works; velocities 2..127, not 1) are allowed: no controller, program change, pitch bend, aftertouch or system-exclusive events.
  Running status is allowed. Other text meta events (`FF 01`..`FF 0F`) are allowed and ignored.
- Events in a track are in time order; **when events of different tracks fall at the same tick they run in track
  order** (track 1 before track 2 ...); a note off and a note on of the same key at the same tick on one channel must be
  written off first.
- The song **ends when every track has reached its end-of-track**. Put the last end-of-track no more than 0.3 s after the
  last note off (the game treats the song as finished then; ringing tails are fine).
- Keys 0..95 only. **Cues that play a song transposed** (section 5) raise every key: song 11013 plays also at +6 and +12
  semitones, song 11016 also at +12, so **their highest key must be at most 83** (95 - 12).
- Start within 0.3 s of the beginning (no long leading silence).
- Size: at most 64 KB.

**The pace and length of each song.** The engine's clock runs 1/348.47 s per step and works out the length of every
gap between two events as a whole number of steps, rounded down, from the tempo: a piece with very many short gaps plays
up to about 3 % shorter than the tempo arithmetic says. The build simulates this exactly (section "Encoder") and checks
that the **simulated length is within 10 % of the "length" column** (which you compute in the plain way: the sum of
`ticks * tempo / 240 / 1,000,000` seconds over the tempo changes, up to the last end-of-track). The "pace" column is the
beats per minute (quarter note = beat) of the situation the piece is used in: a guide, not a rule. Choose your tempo and
note values (a piece that feels fast at 120 bpm with sixteenth notes is fine); only the length, the number of notes
and the polyphony are checked.

**What the build checks** (all errors unless marked): the header and track structure above (the file ends exactly where
the last track ends); the tempo range; keys in
0..95 and (for 11013, 11016) at most 83; velocities 2..127; every note on matched by a later note off on the same
channel and key; no overlap of the same key on a channel; the minimum and maximum note lengths; at most 6 notes held
at once (3 on channel 2 and a single note on the others, 2 on channel 4), counted after all the events of one tick have run
(a note ending on the tick another starts is not "at once"), and a size of at most 64 KB; the channel of each track is 1..10 and no
two tracks share a channel; a track's keys within 6 semitones of its channel's range in the table (outside the range
itself but within 6: a warning); the simulated length within 10 % of the table; the number of notes within 50..200 %
of the "notes" column (a warning; an error outside 25..400 %); the first note on within 0.3 s of the start; the last
end-of-track within 0.3 s of the last note off; the ambient themes (10003, 10004, 10005) use only channels 5..10.

## 4. The 30 songs

"Length" is the target in seconds (the plain tempo arithmetic above). "Pace" is a guide in beats per minute. "Notes" is
the approximate number of notes in the piece (all channels), a density guide. "Voices" are the channels to use; you may
add or drop one if the piece asks for it. Tier **A**: the game triggers the cue; tier **B**: nothing in the game triggers
it (spare; compose plainly, last).

| Song | Cue(s) | Tier | When it plays | Length s | Pace | Notes | Voices |
|---|---|---|---|---|---|---|---|
| 10001 | 10001 | A | The title screen opens; and the player chooses File > New (a new game) | 103 | 214 | 1185 | 1, 2, 3 and drums 5..10 |
| 10003 | 10003 | A | One of the three **ambient themes**, played in rotation every few minutes while a game runs; also, 10003 or 10004 chosen at random, the tune after the game-over window's own piece has ended | 56 | 180 | 468 | 5, 7, 8, 9, 10 only |
| 10004 | 10004 | A | Ambient theme 2 (and the other game-over closing tune) | 47 | 314 | 452 | 5, 7, 8, 9 only |
| 10005 | 10005 | A | Ambient theme 3 | 42 | 300 | 297 | 5, 6, 8, 9, 10 only |
| 10006 | 10006 | B | not triggered | 21 | 232 | 227 | 1, 2 and drums 5, 6, 9, 10 |
| 10007 | 10007 | B | not triggered | 24 | 224 | 236 | 1, 2 and drums 5, 6, 8, 9, 10 |
| 10008 | 10008 | A | The game ends and the player has **won** (the rating window opens) | 30 | 192 | 292 | 1 and drums 5..10, add 2 and 3 for the final chord |
| 10010 | 10010 | A | The game ends and the player has **lost** | 33 | 260 | 273 | 2, 3 and drums 5, 7, 9, 10 |
| 11002 | 11002 | A | The yellow ant moves to another patch of the yard | 5 | 240 | 35 | 1, 2 |
| 11003 | 11003 | A | The player places a queen, starts a game, or picks a patch on the yard map (often) | 1.3 | 180 | 8 | 4 |
| 11004 | 11004 | B | not triggered | 2 | 240 | 30 | 1, 3 and ticks 7, 8 |
| 11005 | 11005 | A | The player tries to become another ant but there is none to become | 4 | 240 | 23 | 1, 2 |
| 11006 | 11006 | A | The player exchanges places with another ant | 10.6 | 181 | 31 | 2 |
| 11007 | 11007 | B | not triggered | 2.7 | 181 | 6 | 1 |
| 11013 | 11013, 11014, 11015 | A | A recruit command: **recruit 5 / recruit 10 / recruit all**, at its own pitch / 6 semitones up / 12 semitones up | 2.7 | 180 | 15 | 2 |
| 11016 | 11016, 11017 | A | **Release half / release all** the recruits, at its own pitch / 12 semitones up | 4 | 120 | 8 | 1 |
| 11018 | 11018 | A | The attack command (an alarm) | 4 | 240 | 6 | 2 |
| 11020 | 11020 | A | The player's (black) queen is shown | 5 | 480 | 12 | 1, 2 |
| 11021 | 11021 | A | The rival (red) queen is shown | 10.6 | 181 | 70 | 2 |
| 20000 | 20000 | A | A happy event: the queen scene | 2.2 | 220 | 9 | 1, 2 |
| 20001 | 20001 | A | A new nest has been founded | 2.2 | 221 | 12 | 1 |
| 20002 | 20002 | A | The red ants are gone from the yard | 8 | 480 | 36 | 1, 2 |
| 20003 | 20003 | A | The human moves into the house; **also the first piece of the win screen** | 7 | 480 | 34 | 1, 2 |
| 20004 | 20004 | A | The **second piece of the win screen**, played right after 20003 ends | 4 | 480 | 18 | 1, 2 |
| 20005 | 20005 | A | The player wins the Full Game: the final yard scene | 8 | 480 | 36 | 1, 2 |
| 20007 | 20007 | A | One of **five sad pieces**, one chosen at random each time the yellow ant dies | 8 | 480 | 26 | 2, 4 |
| 20008 | 20008 | A | Sad piece 2 | 8 | 240 | 21 | 1, 4 |
| 20009 | 20009 | A | Sad piece 3 | 3.8 | 256 | 32 | 4 |
| 20010 | 20010 | A | Sad piece 4 | 4.3 | 221 | 12 | 1, 2 |
| 20011 | 20011 | A | Sad piece 5 | 4.3 | 221 | 6 | 2, 4 |

### The character of each song

Moods, in words. The game is a cheerful, slightly comic nature-documentary of an ant colony, and the music should stay warm
and playful even when it is sad or sinister. Keep melodies memorable and singable; avoid anything shrill.

- **10001, the main theme** (title screen and new game). The signature tune of the game: cheerful, bustling and a
  little cheeky, like a colony hard at work. A short intro (4..8 s) announces the tune; then the main section with a catchy
  lead (channel 1), a bouncy walking bass (3) and chords (2) over a brisk beat; a calmer contrasting middle section (tuned
  drum and bell, fewer voices); the main tune again, bigger; a finish with a flourish and a clear last chord. Mostly major
  and bright. It is the most-heard piece: it must stay pleasant on repetition, and its first minute is the part everyone
  hears.
- **10003, 10004, 10005, the three ambient themes.** Quiet background pieces for long play, in the tuned-percussion
  channels only (tuned drum 8, bell 10, tick 7, shaker 9, a soft kick 5, the crack 6 only in 10005): no lead, no bass
  voice, no loud drums. They run for a minute and must not get in the way of watching the colony. 10003 is relaxed and
  swaying; 10004 is quick and scurrying, a patter of tiny light notes; 10005 is brisk and curious, a bit skipping and
  quirky. Make them clearly different from each other (they follow one another), never tense, and let each come to a
  settled stop, because 10003 or 10004 also close the game-over moment.
- **10006, 10007** (spare). 10006: a bright flourish whose lines sweep up and down over a wide pitch range, with a light
  beat. 10007: a bouncy, playful interlude.
- **10008, victory.** Triumphant and joyful: a fanfare feel, a rousing lead (1), a driving beat (drums 5..10), building to a
  big final chord held by chords (2) and bass (3). It ends decisively.
- **10010, defeat.** Sombre but gently comic, never grim: a slow plodding march, falling lines, a weary, resigned finish.
- **11002, moving to another patch.** A quick, bright travelling flourish: two voices, rising runs, ending on a small lift.
- **11003, the confirmation.** A tiny rising flourish of eight quick notes on the plucked voice that means "go!". It is
  heard many times in a game: short, bright, never annoying.
- **11004** (spare). A short cheerful "ta-da" with two melodic voices and two light percussion hits.
- **11005, nobody to become.** A comic drooping "oh well": a descending phrase with a wobble at the end.
- **11006, exchange.** A longer, shimmering, magical phrase on the chord voice alone, rising and falling like a spell,
  settling on a calm last note.
- **11007** (spare). A short, low, ominous two-note sting that drops away.
- **11013, recruit.** A short bright call-to-arms ("come on, everybody!") on the chord voice, rising in shape. It is played
  at three pitches (as is, 6 semitones up, an octave up) for recruit 5, 10 and all, so it must sound good at all three
  and its highest key is at most 83.
- **11016, release.** A relaxed, falling "dismissed, off you go" phrase on the lead; played as is and an octave up;
  highest key at most 83.
- **11018, the attack alarm.** Urgent and insistent: a short, sharp figure of two alternating pitches repeated three times,
  unmistakably an alarm but not grating.
- **11020, the player's queen.** Warm, regal, dignified: a small, majestic rising-then-settling phrase, two voices.
- **11021, the rival queen.** Sly and menacing: a winding, creeping line on the chord voice, a minor colour, long and
  slow-moving, never scary enough to frighten a child.
- **20000, 20001.** Quick glad stings: 20000 (two voices) a burst of delight; 20001 (one voice) a satisfied little upward
  phrase for a nest founded.
- **20002, the reds are gone.** Relieved and triumphant, lively and upbeat, ending on a strong full close.
- **20003 and 20004, the human arrives / the win screen.** 20003: wry and dramatic, an "uh-oh" tension with a comic edge,
  ending unresolved so that 20004 can follow at once; 20004: the jolly resolution, a short "the end" that closes the
  win screen. Heard back to back (11 s); they must work as one piece.
- **20005, the Full Game won.** A grand final fanfare, everything the orchestra has, a ringing last chord.
- **20007 .. 20011, the five sad pieces.** Gently comic laments, since the ant is a cartoon, not a tragedy; one chosen at
  random at each death, each different in manner: 20007, a slow, long, drooping lament on chords and pluck; 20008, a tired
  trudging march; 20009, a fluttering, trembling little descent on the plucked voice within about seven semitones; 20010,
  a short sighing phrase; 20011, a short low dirge.

## 5. The cue list (functional, built from `docs/clean_pack/data/song_cues.json`)

33 cues play the 30 songs. A cue number is an effect number of the old numbering; the ones in the 10000s are the title and
ambient music, 11000s the player's commands and events, 20000s the larger events. A cue records which song it plays and a
transposition in semitones (added to every written key, so keep the headroom of section 3):

| Cue | Song | Transposition |
|---|---|---|
| 10001, 10003, 10004, 10005, 10006, 10007, 10008, 10010 | the same number | 0 |
| 11002, 11003, 11004, 11005, 11006, 11007 | the same number | 0 |
| 11013 | 11013 | 0 |
| 11014 | 11013 | +6 |
| 11015 | 11013 | +12 |
| 11016 | 11016 | 0 |
| 11017 | 11016 | +12 |
| 11018, 11020, 11021 | the same number | 0 |
| 20000, 20001, 20002, 20003, 20004, 20005, 20007, 20008, 20009, 20010, 20011 | the same number | 0 |

The makers do not write the cue table; the build does (section "Encoder").

## 6. Composing for this sound

Some practical notes (you have no copy of the driver; the spec side renders and listens afterwards and sends notes back).

- The FM voices have **sine-wave** timbres with envelopes: they are bright and clean, a little bell-like. They carry
  melodies best with clear rhythms and moderate ranges; dense fast runs smear.
- The tempo can change in a piece (ritardando at the ending is welcome): put tempo events in track 0.
- Give the lead room: chords and plucked voices under it, bass and kick carrying the low end, ticks and shaker quiet.
- Dynamics: velocity changes are the only dynamics; use a few clear levels in a piece rather than constant
  variation.
- Endings: stop every note, put the end-of-track right after the last tail you want, so the game knows the song is over.
- Keep a record of how each piece is built (key, form, motif idea) in `README.md`: provenance shows independent creation.

## Encoder (for build.py)

For the later agent who writes the encoder. The engine's readers are fixed and verified (`OpenSimAnt.Data.SoundDriver.StartSong`,
`Step`, `Meta`, `NextEvent`, `ChannelEvent`, `OriginalFiles.Get`); the encoder produces what they read. Pack entries
(`ARCHIVE/type/id.bin` in the zip):

- `SOUND/20/<song id>.bin` (30): the Standard MIDI file, **unchanged bytes** of `src/music/<song id>.mid` after validation;
- `SOUND/18/<cue>.bin` (33): the 18-byte cue entry (below), written for every cue of `data/song_cues.json`;
- the sound bank `EXE/soundbank.bin` (the 16 FM patches the songs play) belongs to [sounds.md](sounds.md).

`expected()` lists the 30 `SOUND/20/<id>` and the 33 `SOUND/18/<cue>`. `--fallback` takes missing ones from the original pack as
for the other categories (the cue entries are always built, being data).

### The cue entry (`SOUND/18/<cue>.bin`, 18 bytes, big-endian)

`struct.pack('>HHHhHHBB4x', song, kind, 0, transposition, a, b, c, d)`: `song` the SOUND type 20 id to play, `kind` 4 for the
10000s cues and 1 for the others, 0, a signed transposition in semitones added to every key, then `a`, `b` (voice-count-like
numbers, 4..8 and 2..5), `c` (0x40..0x44), `d` (0x08..0x10) and four zero bytes. **The engine reads only `song` (bytes 0..1) and
the transposition (bytes 6..7)**; the rest is written verbatim from `bytes_hex` in `docs/clean_pack/data/song_cues.json`
(functional metadata of the old driver, carried as numbers). So the builder reads that file, checks that the `song` of every
cue has a `src/music/<song>.mid`, and writes `bytes.fromhex(bytes_hex)`. `--roundtrip`: decode the 33 originals with the struct
format and re-encode: byte-identical.

### The sequencer, as the engine reads a MIDI file (port to Python as `midi_check`)

`StartSong`: `hdr = be32(file[4:8])` (6), `tracks = be16(file[10:12])`, `ppq = be16(file[12:14])`; the first track chunk is at
`hdr + 8`; every chunk `MTrk` + be32 length; a track's data starts 8 bytes after its chunk. Per track it reads the first delta
(a variable-length number) into `time[t]` (absolute ticks) and peeks the next byte as the running status. Initial scale
`Scale(480, 500000)`, `cur = 0`, `lastTime = 0`.

`Scale(ppq, tempo)` = `int(int(int(tempo / 1000) * 0x4AA / ppq) / 13)` (all integer divisions, truncating): music steps per MIDI
tick in 8.8 fixed point. One step is `1 / (1193182 / 0xD6 / 16)` = 1/348.47 s.

`Step()` (one call per wait; it loops until a wait is not 0 or the song ended and returns the wait, or 1 when it ended with
wait 0): read the byte at the current track's position; if bit 7 is set it is the new status, advance one; status `0xF0` or
`0xF7`: skip a variable-length count of bytes; `0xFF`: a meta event (`0x2F`: mark the track ended, status := 0x2F and step
back one byte; `0x51`: skip the length byte, read 3 bytes, tempo := them, advance and `scale := Scale(ppq, tempo)`; any other:
skip the type, read a variable-length count, skip it); any other status: a channel event, which `ChannelEvent` handles
(**only note on `0x9n` and note off `0x8n`, channels 0..13**, velocity 0 on a note on = note off; key + transposition), then
advance by 2, 2, 2, 2, 1, 1, 2 bytes for the status's `(status & 0x70) >> 4` = 0..6. Then `NextEvent`: if the current track has
not ended add the next delta to its time, else its time := 0x7FFFFFFF; `di := 0`; for `t` in 1..tracks-1: if `time[di] >
time[t]` and track `t` not ended: `di := t` (**ties go to the lower track**; a later track wins only when strictly earlier);
if track `di` is ended or its time is 0x7FFFFFFF the song is over (return 0, mark ended); else `wait = ((time[di] - lastTime) *
scale >> 8) & 0xFFFF`, `lastTime := time[di]`, `cur := di`. Note the first event processed is track 0's first event whatever
the other tracks hold, so track 0 starts at delta 0 with the tempo or the name. Simulated length of the song in seconds =
(sum of the waits) / 348.47. The music starts about 5 steps after the cue.

**Verification of the port** (`--roundtrip`): run it on the 30 originals: total MIDI ticks = `ticks` in `data/songs.json`; notes,
lowest / highest key and the channel set equal the measurements; the Game Theme (10001)'s last note event comes at **step 35,856 = 102.9 s**
(SIM_NOTES; the song's own end, the last end-of-track, is 97 steps later, 35,953 = 103.2 s: the figure the table's "length" and
the build's 10 % check use); no original fails the structural checks except the ones a clean file must avoid (the originals carry controller,
SMPTE-offset and time-signature events and use channel 0; list them, do not fail on them). Measured with the finished port: ticks, notes, lowest and highest key, channels and track
count agree with the measurements for all 30; 28 of the 30 would fail the clean-file rules (by rule: key range 13 songs, more than 6
notes at once 7, a late first note or a long tail 4, header 3 (format, track count or division), plus one each for a controller event, channel 0, a key above 95, a
velocity of 1 and a note length outside the limits), which is expected: the clean rules are stricter than the old files.

### The checks for a clean file

All in section 3; implement them on the parsed events in the engine's order (by time, ties by track):

- held notes: +1 at a note on (velocity > 0), -1 at the matching note off; the maximum over time <= 6, taken after the last event
  of each step (<= 3 for channel 2's own count, <= 1 for channels 1, 3, 5..10, <= 2 for channel 4); a note on while the same key
  is held on the channel is an error (checked event by event, in the engine's order); a note off with nothing held is an
  error; at the end of the song nothing is held;
- lengths in seconds from the simulated clock: pitched >= 40 ms, channels 5, 6, 7, 9 >= 80 ms, any <= 12 s;
- the transposed cues: `max key + max(transposition of the cues of that song) <= 95`;
- the track layout (one channel per track, no shared channels, track 0 without notes, the first event of track 0 at delta 0);
- the length by `Scale` and the simulated waits within 10 % of the table in section 4 (put those lengths and the "notes" column into
  the builder as a table: the numbers of section 4 are in `data/songs.json`).

### Notes on the driver, for reviewers

The pitch rule (section 2) is `Opl block = key / 12` of the written key (with the transposition), the F-number table by `key % 12`;
a key of 96 or more overflows the chip's 3-bit block field and is silent. Songs run on FM voices 0..7 shared with the effects;
`PickVoice` takes the lowest-priority voice, the oldest among equals, and a note replaces it only if its own priority is at least as
high: song notes (7 and 5) replace effect notes (3, 2); a drum's note off silences all sounding notes of that key on that
channel. The sampled drums of the old set are not used by any channel (every drum here is an FM patch).
