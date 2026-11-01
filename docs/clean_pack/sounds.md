# Spec: sound effects and FM instrument patches

> **Status (2026-11-01):** spec written, ready for a maker. The encoder is **in `tools/clean_pack/build.py`** (`cat_sounds`,
> `enc_sample`, `cat_soundbank`, `enc_soundbank`; `--roundtrip` checks it against the originals); section "Encoder
> (for build.py)" describes what it does, with the numbers its first run measured. Music is a separate spec,
> [music.md](music.md); the two share the table of channel roles (section 2), repeated in both.

Output folder: `remake/game/assets/clean/src/sounds/`. Provenance: `remake/game/assets/clean/PROVENANCE.md` (add an
entry). Two kinds of new sound design live here:

1. **Sampled effects**: short mono recordings (here: synthesised) that the game plays through a 2-voice sample mixer.
2. **FM instrument patches**: the register settings of 16 instruments for a two-operator FM chip (the OPL2, the chip of
   the AdLib and Sound Blaster cards). They are the game's other effects *and* the voices of every song.

Everything else about sound is a **functional table** that the pack carries over as plain numbers and the maker does
not touch (section 1).

## 1. What is new and what is carried over

| Part | Kind | Who makes it |
|---|---|---|
| The 35 sampled effects the sound driver can reach (24 the game triggers, 11 spare) and 22 optional extra ids | **new** sound design | the maker: `sfx_<id>.wav` |
| The 16 FM patches (7 of them are effects the game triggers, 10 are the song channels' voices, one patch is both) | **new** sound design | the maker: `fm_patches.json` |
| The 30 songs | **new** music | another maker, [music.md](music.md) |
| Which effect number plays which instrument, at which priority and velocity; which instruments are FM and which are samples; the priority and instrument of each MIDI channel; the sample records' fields (base octave 5, no transposition, no loop); the cue table (`SOUND/18`) | **functional numbers**, carried over (like `OpenSimAnt.Sim/GameTables.cs`; the measurements are in `docs/clean_pack/data/embedded.json` and `song_cues.json`) | `build.py`, from tables it holds |
| The volume tables, the FM attenuation per velocity, the F-number table, the operator slots, the pitch-step table | **functional numbers**, already in source (`GameTables.cs`) | nothing to supply |
| The names of the sample files that the original keeps in its sample records | **dropped** (they are never read; the clean bank writes neutral names `sfx<id>`) | `build.py` |

So the maker delivers **only waveforms and patch settings**. The wiring (effect 17 plays instrument 17 ...) is fixed
by this spec and written by the build.

## 2. How the game plays sound (what you need to know to design for it)

**Effects.** The game asks for "effect n" (n = 0..55). Each effect is a note on instrument n. An instrument is either
a **sample** (a recording played back by the mixer) or an **FM patch**. Which is which is fixed:

- FM instruments (17 of them): 0, 3, 9, 15, 16, 17, 18, 19, 25, 30, 35, 46, 48, 50, 51, 53, 54 (15 and 16 share one
  patch).
- Sample instruments: every other number from 1 to 54 except those, i.e. 38 instruments. Three of them (12, 43, 52) are
  aliases of sample 5 and never triggered. Instrument 55 is empty.
- **Effect 55 is sample 10 played ten times faster** (and so ten times shorter and three and a bit octaves higher):
  the spider's lashing strike. Sample 10 therefore has to be a sound that works at normal speed *and* at ten times
  speed (see its row).

**Samples** play at a fixed rate of **5,575.6 Hz** (a note at the effect's key plays the recording at exactly that rate;
other keys speed it up or slow it down, but only effect 55 does). The driver has **two sample voices**; a third sample
effect started while two play replaces the oldest. A sample is 8-bit, so the whole recording is lo-fi on purpose: it
has no content above about 2.7 kHz (half the rate). The game stores samples with a crude 4-bit delta code (section
"Encoder"), so the quality is that of an old home-computer game, not of a recording. Design for it: simple shapes,
strong envelopes, little high-frequency detail.

**FM patches** play on **8 FM voices shared by effects and music**. An FM effect has no "note off": it must fade out
by itself. Songs do send note offs.

**The pitch of an FM note.** A note is a key number k (0..95 work; higher is silent). It sounds at the equal-tempered
frequency `440 * 2^((k + 12 - 69) / 12)` Hz, i.e. **key 60 sounds at 523 Hz (C5), an octave above the usual MIDI
convention**; key 0 is 16 Hz, key 95 is 3,951 Hz. (Within about 15 cents.) The patch's modulator and carrier multiples
are relative to that. **Every patch has octave shift 0** (the field exists but is always written as 0): choose the sounding
pitch of an effect with its `effect_key` (below), and of a song note by the key the composer writes.

**The chip.** Two operators per voice (a modulator and a carrier), **both sine waves** (the driver switches the
waveform selection off), either frequency-modulated (connection 0) or added (connection 1), with feedback on the
modulator (0..7). The driver turns on **deep tremolo and deep vibrato** (the chip's 4.8 dB amplitude and 14-cent pitch
depths), so the tremolo/vibrato flags are audible when set. Percussion mode is off. All envelope settings below are the
chip's own and are documented in any public YM3812 / OPL2 reference.

**The loudness of a note.** The driver recomputes the carrier's level at every note on: it scales the patch's carrier
"total level" by the velocity (127 = the patch's own level, lower velocities are quieter, below about 40 nearly
silent), after adding the patch's `velocity_offset`. The modulator's level is fixed (it sets the brightness). Effects are
played at velocity 127.

**The channels of the songs** (the same table is in [music.md](music.md)). A song file uses MIDI channels 1..10 (numbered
from 0); each channel is a fixed patch with a fixed priority. There are no program changes and no General MIDI map:

| MIDI channel | Priority | Instrument | Patch | Role in the songs |
|---|---|---|---|---|
| 1 | 7 | 25 | `fm25` | lead melody |
| 2 | 7 | 53 | `fm53` | harmony / chords / pad |
| 3 | 7 | 3 | `fm3` | bass |
| 4 | 7 | 54 | `fm54` | plucked counter-melody |
| 5 | 5 | 35 | `fm35` | deep drum (kick) |
| 6 | 5 | 46 | `fm46` | noisy crack (snare / clap) |
| 7 | 5 | 50 | `fm50` | very short tick (hi-hat) |
| 8 | 5 | 51 | `fm51` | tuned drum (tom, can carry a tune) |
| 9 | 5 | 48 | `fm48` | shaker / rattle (a short noisy swish) |
| 10 | 5 | 0 | `fm0` | bell / mallet (pitched, rings) |

(Channel 0 has priority 0 and never sounds; channels 11..13 would play a short beep sample and are not used; 14 and 15 are
ignored.) Written key ranges the composers are told to use, so design each patch to sound good **across** its range:
`fm25` 48..88; `fm53` 40..80; `fm3` 24..52; `fm54` 48..88; `fm35` 20..55; `fm46` 40..80 (the pitch mostly colours the
noise); `fm50` 60..95; `fm51` 36..84; `fm48` 50..95; `fm0` 60..95.

Effects have priority 3 (the three dig effects 2), songs 7 and 5, so **an effect can only use a voice that no song note
holds**; the songs keep at most 6 notes held at once so there is always room.

## 3. The deliverables

All in `remake/game/assets/clean/src/sounds/`:

| File | What |
|---|---|
| `sfx_<id>.wav` | one per sampled effect (section 4); the 35 listed as "required" must exist, the optional ones may |
| `fm_patches.json` | the 16 FM patches (section 5) |
| `make_sounds.py` | a script that writes **all** the files above, deterministic (seeded random numbers), so they can be regenerated |
| `README.md` | one line per sound and per patch: what it is meant to sound like, how it is made |
| `preview.wav` (recommended) | every sampled effect in order at 5,576 Hz with a quarter second of silence between, for a listening pass |
| `preview_fm.wav` (optional) | each FM patch played at a few keys, rendered with a rough two-operator sine FM renderer of your own (a modulator phase-modulating a carrier, with the envelopes above; it does not have to be exact), so you can judge the timbres and lengths. The spec side renders the real chip afterwards |

Work with Python 3 and numpy (the standard `wave` module writes the WAV files). **Synthesise everything yourself** (oscillators,
noise, filters, envelopes, simple physical models); no library samples, no recordings of existing games, no imitation of
a particular game's sounds. Seed every random number generator.

## 4. The sampled effects

### 4.1 File format

`sfx_<id>.wav`: RIFF/WAVE, PCM, **mono, 16-bit, 5,576 Hz** (the driver's rate, rounded), nothing but the `fmt ` and `data`
chunks. The build turns it into signed 8 bits (sample / 256) and codes it, so:

- Synthesise at a higher rate (any whole multiple of 5,576, e.g. 44,608), **low-pass below about 2.5 kHz with a steep
  filter, then decimate by that whole number**. Anything above 2.8 kHz folds back as ugly noise at the playback rate.
- **Start and end at zero** (the first and last 8 samples within +-6/127 of full scale): the sample is played from a
  zero level and a voice that ends on a level leaves a click.
- Very high-frequency content at a high level cannot be coded (the code can move the level by at most ~127 per sample
  and 4 bits only choose between 16 steps). Keep most energy below 1.5 kHz and sharp attacks short; the build measures the
  coding error and rejects a file that comes out as mush (section "Encoder"), so if it does, soften it.
- The number of samples (the frame count) is within 20 % of the "samples" column; it is rounded up to even by the build.
  At most 16,000 samples in any file.
- The peak (largest absolute value, in 8-bit units out of 127) is within 80 %..110 % of the "peak" column. The
  differences between the peaks are deliberate (a lawn mower is quiet, a dog yap loud).

### 4.2 The effects

Tier **A** = the game triggers it; tier **B** = reachable through the instrument table but nothing triggers it (spare;
make it, plainly, last). "Samples" and "peak" are measurements of the sounds the pack replaces (numbers only; the
duration is samples / 5,576 s). The "character" column is a design brief in words; make it your own.

| Id | Tier | When the game plays it | Character | Samples | Peak |
|---|---|---|---|---|---|
| 1 | A | The player's action is refused or does nothing (many places: a patch the ant cannot go to, a tool that cannot work here, no ant to follow, a wrong cheat word) | A short, dull, low "nope": two quick soft-edged low buzz tones | 752 | 121 |
| 2 | A | A switch or mode is turned on (a cheat toggle, Hunt mode) | A friendly bright rising two-note beep ("yes") | 1672 | 127 |
| 4 | B | spare | One short bright beep | 1244 | 90 |
| 5 | B | spare (also what the unused music channels 11..13 would play) | One medium beep with a slight warble | 2784 | 120 |
| 6 | B | spare | A very short high pip | 1040 | 124 |
| 7 | A | A bird flies across the yard (and at times when it catches a flying queen) | A bright whistled bird call: two or three quick rising-and-falling chirps | 4960 | 127 |
| 8 | B | spare | A long synthetic horn-like chord that swells and fades | 12736 | 128 |
| 10 | A | A pebble is dropped; the "silly" mode's random remark; part of two death scenes. **Also effect 55 (this sample at ten times speed): the spider's strike** | A comic, rubbery, descending gurgle. At ten times speed (0.05 s, far higher) it must still read as a sharp whip-crack or zip, so give it a strong, clean attack and an obvious pitch glide | 2706 | 127 |
| 11 | B | spare | An insect drone: a buzzing hum with a little wobble | 6688 | 127 |
| 13 | A | The cat meows | A cat's meow: a rise and fall in pitch with a vowel-like formant | 2016 | 120 |
| 14 | A | The cat attacks the dog | A longer, angrier yowl, a harsher meow | 5196 | 128 |
| 20 | B | spare | One small dry paw-step | 436 | 109 |
| 21 | A | The dog barks (one of its moods) | A short whimper, rising | 1742 | 107 |
| 22 | A | The dog barks (another mood) | A longer whimper / whine, falling | 2874 | 115 |
| 23 | A | The dog barks (the usual bark) | A single sharp yap | 4010 | 127 |
| 24 | A | The human goes through the house door | A wooden door banging shut: a dull crack and a short rattle | 1480 | 122 |
| 26 | B | spare | A single water drip | 330 | 125 |
| 27 | A | The pheromone tool lays scent | A soft liquid drip, a small round "bloop" | 804 | 128 |
| 28 | A | The ants tool puts ants down; an item is put down | A soft, small plop | 436 | 127 |
| 29 | A | The food tool drops a crumb | A tiny dry tick, the shortest sound of the set | 172 | 121 |
| 31 | B | spare | A slow food drip with a wet tail | 1812 | 117 |
| 32 | A | A heap of food is spilled (the food tool with Alt, a clear-all-food cheat) | A wet splat of many bits landing | 3374 | 115 |
| 33 | B | spare | A sucking, squelching pull | 3862 | 110 |
| 34 | B | spare | One heavy human footstep, muffled | 3628 | 119 |
| 36 | A | The lawn mower runs. **Started again at every simulation step (several times a second) while it moves**, so in practice mostly the first 0.1 to 0.15 s is heard | A low engine motor: a steady rough buzz with a regular chop, **quiet**, and any 0.1-second stretch of it must sound like a motor, not like a start | 1864 | 55 |
| 37 | A | An ant bites (a fight; also the ant lion's scene) | A crisp crunch | 1888 | 124 |
| 38 | A | The ant lion takes the yellow ant | A short, low, gravelly roar | 2880 | 127 |
| 39 | B | spare | A longer low snarl | 11692 | 128 |
| 40 | A | A wall block is placed with the rock tool | A short hollow pop | 184 | 115 |
| 41 | A | Rain showers in the yard | A soft, steady shower: a gentle hiss with random pattering, fading in and out | 12896 | 127 |
| 42 | A | One of the yellow ant's death scenes | A comic retching sound | 3484 | 128 |
| 44 | A | An ant eats (and in a death scene) | A short wet slurp | 1824 | 125 |
| 45 | A | The spider swallows an ant | A longer, drawn-out slurp | 3296 | 128 |
| 47 | A | Each step of the spider | A tiny dry tap | 466 | 110 |
| 49 | A | An ant tears at food or prey (the yellow ant's biting actions) | A short ripping, tearing rasp | 2428 | 124 |

**Optional extra ids** (never read by the driver, kept in the original's archive as leftovers; skip them): 0, 3, 9, 12, 15,
16, 17, 18, 19, 25, 30, 35, 43, 46, 48, 50, 51, 52, 53, 54, 55, 56. If a `sfx_<id>.wav` of one of these exists the
build encodes it like the others (the 5576 Hz format, the same checks, no length or peak table); nothing needs it.

One more hint for the whole set: the effects happen **all the time** (digging, walking, dropping food), so the tier A
sounds that repeat often (29, 28, 27, 47, 40, 36, and the FM dig sounds) must be soft-edged and unobtrusive, and the
rarer, dramatic ones (38, 42, 45, 14) can be bold and funny. The game has a playful, cartoonish tone.

## 5. The FM patches

### 5.1 The file

`fm_patches.json`: `{"patches": [ ... 16 objects ... ]}`, in this order and with these ids. One object:

```
{
  "id": "fm35",
  "instruments": [35],
  "effect_key": 30,
  "velocity_offset": -10,
  "feedback": 5,
  "connection": 0,
  "modulator": { "tremolo": 0, "vibrato": 0, "sustain": 0, "ksr": 0, "multiple": 1,
                 "ksl": 0, "level": 20, "attack": 15, "decay": 8, "sustain_level": 15, "release": 8 },
  "carrier":   { "tremolo": 0, "vibrato": 0, "sustain": 0, "ksr": 0, "multiple": 1,
                 "ksl": 0, "level": 0,  "attack": 15, "decay": 9, "sustain_level": 15, "release": 9 },
  "note": "one line: what it should sound like"
}
```

(The numbers in the example are arbitrary; they show the form, not a recommended sound.)

| Field | Range | Meaning |
|---|---|---|
| `id`, `instruments` | fixed (table below) | the patch and the instrument numbers (= effect numbers) that play it; do not change |
| `effect_key` | 0..95 | the key at which the **effects** that play this patch sound (the effect table's key); sets the pitch of the effect. Ignored for songs. Required for the patches that serve a triggered effect, optional (default 60) for the others |
| `velocity_offset` | -64..0 | added to every velocity before the loudness is worked out: more negative = quieter. Use it to balance the patches against each other (the song channels and the effects should sit at about the same loudness at velocity 100) |
| `feedback` | 0..7 | the modulator's self-feedback (0 none; 5..7 turns it noisy) |
| `connection` | 0 or 1 | 0: the modulator frequency-modulates the carrier; 1: the two are added |
| `tremolo`, `vibrato` | 0/1 | amplitude (4.8 dB deep) / pitch (14 cents deep) modulation of that operator |
| `sustain` | 0/1 | **modulator only may be 1**; the **carrier's must be 0** in every patch (an effect has no note off: a held carrier would never stop) |
| `ksr` | 0/1 | key scaling of the envelope rates |
| `multiple` | 0..15 | frequency multiple: 0 = x0.5, 1..10 = x1..x10, 11 = x10, 12 = x12, 13 = x12, 14 = x15, 15 = x15 |
| `ksl` | 0..3 | level key scaling: higher notes quieter (0 none, 1 = 3 dB/octave, 2 = 1.5, 3 = 6 dB/octave) |
| `level` | 0..63 | total level, 0.75 dB per step, **0 = loudest**. The carrier's level is the loudness at velocity 127 (keep it in 0..30); the modulator's level sets the brightness (lower = brighter / more modulation) |
| `attack`, `decay`, `release` | 0..15 | envelope rates, 15 = fastest, 0 = never. Each step down roughly doubles the time. Approximate times: attack, silence to full level: 15 immediate, 12 about 2 ms, 10 about 4 ms, 8 about 15 ms, 6 about 60 ms, 4 about 240 ms. Decay and release, full level to silence (96 dB): 15 about 2 ms, 12 about 20 ms, 9 about 150 ms, 7 about 0.6 s, 6 about 1.2 s, 4 about 5 s |
| `sustain_level` | 0..15 | the level at which the decay stops and the release rate takes over (a percussive operator, `sustain` 0, goes straight on to release speed): 0 = full level, 15 = silence (-93 dB), a step is 3 dB |

The audible length of a note is about the decay down to the sustain level, then the release rate onward; a song note
that gets its note off earlier is cut short (the release begins). The envelope times above are approximate; the spec
side will render every patch with the real emulator and send corrections.

Remember an FM sound is built with only sine waves: the colour comes from the multiples, the modulator's level and
the feedback. Noise (shaker, snare, hiss) comes from feedback 5..7 with a high multiple and a fast decay; bells from
inharmonic multiples and a long release; basses from multiple 1, a low modulator level and a long decay; plucks from a
fast attack, a quick decay and a short release.

### 5.2 The 16 patches

`effect_key` is the pitch of the effect (sounding frequency from the table in section 2). Lengths are the audible
length at velocity 127 (down to -40 dB).

| Id | Instruments | Serves | Design brief |
|---|---|---|---|
| `fm25` | 25 | song channel 1: lead | A bright, clear, singing lead: a quick attack, a long tail, light vibrato. Must be pleasant across keys 48..88 and cut through the other voices. (Effect 25 is never triggered) |
| `fm53` | 53 | song channel 2: harmony / pad | A rounder, softer, slower-speaking voice for chords: a gentle attack (a few ms to 30 ms), a long smooth tail. Several of its notes sound at once, so no harsh edge. (Effect 53 never triggered) |
| `fm3` | 3 | song channel 3: bass | A warm, round bass with a strong fundamental, a firm attack and a medium-long tail; keeps its weight on keys 24..52. (Effect 3 never triggered) |
| `fm54` | 54 | song channel 4: plucked counter-melody | A plucked string / marimba-like voice: a sharp attack, a quick decay, a short ring; clearly different from `fm25`. (Effect 54 never triggered) |
| `fm35` | 35 | song channel 5: deep drum **and effect 35: the human's foot stamping** | A deep drum thump: a fast attack, a short sine-like body, a quick decay, with a touch of click at the start. As the stamp it must sound heavy: choose `effect_key` low (about 24..36). Length about 0.15..0.3 s |
| `fm46` | 46 | song channel 6: noisy crack | A snare / clap: noise from high feedback and a high multiple, a very fast attack, a decay of about 0.1..0.2 s. (Effect 46 never triggered) |
| `fm50` | 50 | song channel 7: tick | A very short high tick for subdivisions: the shortest voice, 20..40 ms. (Effect 50 never triggered) |
| `fm51` | 51 | song channel 8: tuned drum | A pitched drum (tom / log drum): a fast attack, a clear fundamental, a decay of 0.2..0.4 s. It carries tunes in the quiet themes, so its pitch must be clear across 36..84. (Effect 51 never triggered) |
| `fm48` | 48 | song channel 9: shaker | A short noisy swish: a soft attack (a few ms), noise colour, a fade of about 0.1 s, quieter than the others (use `velocity_offset`). (Effect 48 never triggered) |
| `fm0` | 0 | song channel 10: bell / mallet | A pitched bell or glockenspiel: a fast attack, inharmonic or bright, a ring of 0.5..1 s. Clear across 60..95. (Effect 0 never triggered) |
| `fm9` | 9 | **effect 9**: one burst of the insecticide spray (eight in a row), and the human's foot landing | A short airy puff / hiss, a little falling in feel: noise colour, a soft-fast attack, 0.08..0.2 s. Repeated quickly, so keep it light |
| `fm15` | 15, 16 | **effect 15**: a small acknowledgement (a mode switched for the yellow ant, a follow command, an exchange finished); effect 16 never triggered | A clean, short, bright blip, 0.05..0.12 s |
| `fm17` | 17 | **effect 17**: an ant digs out a bit of dirt in the nest (happens constantly) | A small dry scrape-tick, soft and unobtrusive, 0.04..0.1 s |
| `fm18` | 18 | **effect 18**: an ant digs in, or a cell is filled | The same family as `fm17`, a little lower and duller (a different pitch), 0.05..0.12 s |
| `fm19` | 19 | **effect 19**: the dig tool, or a nest is founded | The same family, a little brighter and longer, a small cheerful pop, 0.1..0.25 s |
| `fm30` | 30 | **effect 30**: a pebble is picked up or put down; an ant is thrown out of a pit | A dull stone knock: a short body with a bit of click, 0.08..0.2 s |

The dig family (17, 18, 19) are played with priority 2, so any other effect can replace them. Make the three
distinguishable at a glance but obviously one family (the same few multiples and rates, different pitches and levels).

Notes for the whole set: the patches serving songs (the first ten) are heard in **every** piece of music, hours of
play, so avoid anything shrill, buzzing or fatiguing; keep their levels balanced (a lead sits just above the chords, the
bass and kick carry the low end, the ticks and shaker sit under everything).

## 6. What the build checks

Samples: the file is a valid 5,576 Hz mono 16-bit WAV; frames within 20 % of the table and at most 16,000; the peak
within 80..110 % of the table; the first and last 8 samples within +-6 of full scale (8-bit units); the **coding error**
(signal-to-noise ratio of the decoded 4-bit result against your file) at least 9 dB, with a warning when under 14 dB (see
"Calibration" below for what that means for a sound); no
file for an id outside 0..56; every required id present.

Patches: valid JSON of the form above; all 16 ids exactly once in the order of the table, `instruments` as in the
table; no field outside the form above (a misspelt name is an error); every field an integer in its range; the carrier's `sustain` 0; `effect_key` present for `fm9`, `fm15`,
`fm17`, `fm18`, `fm19`, `fm30`, `fm35`; the carrier level at most 40; no patch silent (carrier level below 63, attack
above 0, and not both release and decay 0).

The spec side, not the build, then renders everything through the real driver and emulated chip and listens.

## Encoder (for build.py)

For the later agent who writes the encoder. The engine's readers are fixed and verified (`OpenSimAnt.Data`: `Sounds.Decode`,
`SoundBank`, `SoundDriver`, `SoundMixer`, `OriginalFiles`); the encoder produces what they read. A pack is a zip of
entries named `ARCHIVE/type/id.bin`; here:

- `SOUND/5/<id>.bin`, one per sampled effect: the compressed sample (E1 below);
- `EXE/soundbank.bin`, 2,856 bytes: the sound driver's bank (E2 below). `OriginalFiles(byte[] packZip)` builds the
  executable image the driver reads from it with `EmbeddedAssets.BuildImage` (the four ranges at the DS addresses);
- the cue table `SOUND/18` and the songs `SOUND/20` belong to [music.md](music.md).

`expected()` lists `SOUND/5/<id>` for the 35 required ids (1, 2, 4, 5, 6, 7, 8, 10, 11, 13, 14, 20, 21, 22, 23, 24, 26,
27, 28, 29, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 44, 45, 47, 49) and `EXE/soundbank`. `--fallback` takes the
missing ones from the original pack as for the other categories.

### E1. The sample code (`SOUND/5/<id>.bin`)

Layout: 16 bytes, a table of 16 signed 8-bit deltas; then 4-bit codes, **high nibble first**, two per byte. The length is
`16 + n / 2` for `n` samples (n even). Decoder (exactly the engine's `Sounds.Decode`): `s = 0`; for each nibble `c`:
`s = ((s + table[c] + 128) & 255) - 128` (the sum **wraps** in 8 bits), output `s` (a signed 8-bit sample). The engine
adds 128 to get the unsigned byte the mixer reads, and plays the samples at 5,575.6 Hz; the mixer never plays sample
position 0 and stops after position `n - 2`.

**Round trip of the 57 originals** (`--roundtrip`): decode each, then re-encode losslessly with its own table: at each step
the needed delta is `((t - s + 128) & 255) - 128`; take the **lowest code** whose table entry equals it (it exists since the
data came from that table). The pass criterion is that the decoded samples are identical and the count is equal. Measured:
the samples are identical for all 57 **and so are the file bytes**: 34 of the tables have 16 distinct entries (where the bytes
must agree), the other 23 repeat an entry and the original too always used the lowest code. The summary line reports both
counts; it fails a file whose table is all distinct but whose bytes differ.

**Encoder for a maker's WAV** (lossy):

1. Read the WAV (`wave`/`struct`), check mono / 16-bit / 5,576 Hz. `t[i] = clamp(round(x[i] / 256), -128, 127)`; if the
   count is odd append one 0.
2. Choose the table by iteration. Start: entry 0 = 0; entries 1..7 = a rising geometric series of 7 distinct integers from 1 to
   `P = clamp(ceil(0.9 * max|t[i+1] - t[i]|), 8, 127)` (the first step is taken from 0); entries 8..15 = a rising series of 8
   from 1 to `P + 1` (at most 128), negated (so 7 positive steps, a hold step and 8 negative ones). Repeat up to 30 times:
   encode greedily (below), for each code average the *ideal* deltas (`t[i] - s`) of the samples that chose it, set the entry
   to that average rounded (entry 0 stays 0; the positives are sorted and kept positive and distinct, the negatives negative
   and distinct, nudged by 1 to separate equals; a code nobody chose keeps its entry), and keep the pass with the least
   squared error (= the best signal-to-noise ratio). The build stops early after 6 passes without a better one.
3. Greedy encode: `s = 0`; for each sample choose the code that minimises `|t[i] - (s + table[c])|` among codes with
   `-128 <= s + table[c] <= 127` (so the sum **never wraps**); ties go to the smaller `|delta|`, then the lower code;
   `s += table[c]`.
4. Pack the nibbles, high first; prepend the table as unsigned bytes.
5. SNR = `10 log10(sum t^2 / sum (t - decoded)^2)`; refuse below 9 dB, warn below 14 dB.
6. The checks of section 4.1 above (frames within 20 %, peak, first / last samples, at most 16,000 samples).

**Calibration** (the encoder run on test signals; the thresholds stay 9 and 14 dB). The 57 decoded originals, re-coded by the
lossy encoder: 11.4 dB at worst (the drip, 26), median 25 dB, so none would be refused. Synthetic sounds of 5,576 Hz: a sine of
300 Hz 31 dB, 1 kHz 22 dB, **2 kHz 8.6 dB (refused)**, 2.6 kHz 9.7 dB, white noise 16 dB (noise is *not* the worst case: its
error is uniform), a smooth low rumble (noise low-passed near 300 Hz) 20 dB, a chirp 30 dB, a three-note chord 28 dB. So what fails is a loud, pure
tone above about 1.8 kHz (a delta code of 16 steps cannot follow it); anything with its energy under 1.5 kHz passes with a
margin, and a sound below 14 dB is a noisy, hard-edged one worth a second look. A full build of 35 effects and the sound bank
takes about 1 s.

### E2. The sound bank (`EXE/soundbank.bin`, 2,856 bytes)

Four ranges of the executable's data segment, concatenated in this order (`EmbeddedAssets.All["soundbank"]`):

| Asset bytes | DS address | Size | Content |
|---|---|---|---|
| 0 .. 55 | 0068 .. 009F | 56 | the song header: 14 x u16 LE **priority** (MIDI channels 0..13), then 14 x u16 LE **instrument** of each channel |
| 56 .. 2071 | 0202 .. 09E1 | 2,016 | 20 **FM records** of 16 bytes (DS:0202 + 16 r), then 53 **sample records** of 32 bytes (DS:0342 + 32 s) |
| 2072 .. 2519 | 0A82 .. 0C41 | 448 | 56 **effects**: u16 LE key, priority, instrument, velocity |
| 2520 .. 2855 | 0D92 .. 0EE1 | 336 | 56 **instruments**: u16 LE device (0 none, 1 sample, 2 FM), u16 LE DS offset of its record, u16 LE `0x55B3` (the segment of the far pointer; 0 for the empty instrument 55) |

**FM record (16 bytes)**: `[0]` carrier register 0x20 value, `[1]` modulator 0x20, `[2]` carrier 0x40, `[3]` modulator 0x40,
`[4]` carrier 0x60, `[5]` modulator 0x60, `[6]` carrier 0x80, `[7]` modulator 0x80, `[8]` register 0xC0, `[9]` carrier
0xE0, `[10]` modulator 0xE0, `[11..12]` s16 LE octave shift, `[13..14]` s16 LE velocity offset, `[15]` 0. From the patch
fields: register 0x20 = `tremolo << 7 | vibrato << 6 | sustain << 5 | ksr << 4 | multiple`; 0x40 = `ksl << 6 | level`;
0x60 = `attack << 4 | decay`; 0x80 = `sustain_level << 4 | release`; 0xC0 = `feedback << 1 | connection`. For a clean patch
`[9]`, `[10]` (the waveform selects, ignored by the driver, which turns waveform selection off), the high nibble of `[8]` (unused
bits) and the octave shift are **0**. The decoder of the originals keeps the raw `[9]`, `[10]` and `[8] >> 4` so the round trip
is exact (two originals have non-zero waveform bytes, five have `[8] >> 4` = 15).

**Sample record (32 bytes)**: `[0..5]` 0, `[6..7]` u16 LE loop point (0), `[8]` loop flag (0), `[9]` base octave (**5** for every
record the driver reaches), `[10..11]` s16 LE transposition (**0** for those), `[12..13]` 0, `[14..28]` the file name, ASCII, NUL
padded (clean: `sfx<id>`, e.g. `sfx13`), `[29..30]` u16 LE the SOUND type 5 id, `[31]` 0.

**The functional tables** (carried, not made by the maker): the channel table above (priorities `0, 7, 7, 7, 7, 5 x 9`;
instruments `0, 25, 53, 3, 54, 35, 46, 50, 51, 48, 0, 12, 43, 52`); the effect table: effect `n` = (`key`, `priority`,
`instrument`, `velocity`) = (60, 3, n, 127) for n = 0..54 except priority **2** for 17, 18 and 19; effect 55 = (100, 4, 10,
127); the device of each instrument (the `device` lists in `docs/clean_pack/data/embedded.json`: FM for 0, 3, 9, 15..19, 25,
30, 35, 46, 48, 50, 51, 53, 54; sample for the rest of 1..54 and the aliases 12 / 43 / 52 -> the record of sound 5;
none for 55).

**Building the clean bank** from the maker's `fm_patches.json`:

1. FM records: record `r` = the `r`-th patch of the file (in file order); records 16..19 are zero. Instrument `i`'s record
   offset = `0x202 + 16 r` for the patch whose `instruments` contains `i`.
2. The effect table is the functional one, with the **key** (`[0]` of the entry) replaced by the patch's `effect_key` for every
   effect whose instrument is an FM instrument (default 60 when absent). Samples keep key 60; effect 55 keeps 100.
3. Sample records: one per distinct sound id the sample instruments reach (the 35 required ids in ascending order = slots 0..34;
   slots 35..52 zero). Instrument `i` (sample) points at the slot of its sound id; aliases 12, 43, 52 point at the slot of id 5.
4. Everything is little-endian. The result must be exactly 2,856 bytes. The original's FM records 16..19 (not reached by any
   instrument) hold data; the clean bank writes them as zeros. A clean record's waveform bytes `[9]`, `[10]`, the unused
   high nibble of `[8]`, the octave shift `[11..12]` and `[15]` are 0.

**Round trip** (`--roundtrip`): `dec_soundbank` splits an original `EXE/soundbank.bin` into the model (channels, 20 raw FM
records with their fields, 53 sample records, 56 effects, 56 instruments) and `enc_soundbank` writes it back: **byte-identical**.
Also check on the originals: byte 15 of every FM record is 0, every instrument's segment word is `0x55B3` (or 0), every
referenced record offset lies inside its table, and the field <-> byte conversion of the FM records is an exact inverse.
(Measured on the original: all 2,856 bytes, the records' fields both ways, and every value of every operator field.) Then
build the clean bank, decode it with the same decoder and check the same invariants plus: every FM instrument has a
patch, every sample instrument a record whose sound id exists in the pack (`SOUND/5/<id>`), the 56 effects match the
functional table except the keys. With no maker file yet, `--roundtrip` builds this clean bank from patches read out of the
original's own bank (`patches_of_bank`: fields of the first instrument's record, the effect's key as `effect_key`) and checks
that all 17 FM instruments keep their fields; two of those 16 original patches would break a clean-file rule (a positive velocity
offset, a held carrier), which the summary lists as a note.
