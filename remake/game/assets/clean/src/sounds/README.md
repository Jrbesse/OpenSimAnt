# Clean sound set (sources)

## Sampled effects (`sfx_<id>.wav`, `preview.wav`)

Made by `make_sounds.py` (Python 3 + numpy; deterministic, one seeded `RandomState` per effect). Every effect is
synthesised from scratch at 44,608 Hz (8 x 5,576) with sine oscillators, formant-shaped harmonic "voices", filtered
noise, damped resonances and small drop/knock models; then low-passed (windowed-sinc FIR, -6 dB at 2.45 kHz), decimated
by 8, given soft zero edges, and scaled to the spec's peak. Frame counts equal the table's. `preview.wav` plays all 35 in
id order with 0.25 s of silence between. Run `python make_sounds.py` to regenerate everything.

| Id | Sounds like | How it is made |
|---|---|---|
| 1 | a dull, low "nope": two quick soft buzzes, the second lower | two band-limited saw-like stacks (150 and 108 Hz, gliding down), raised-cosine windows |
| 2 | friendly bright rising two-note "yes" | sine + 2nd/3rd harmonic, 587 Hz then 880 Hz (a fifth up), exponential decay |
| 4 | one short bright beep | 988 Hz sine + weak 2nd harmonic, soft attack and release |
| 5 | one medium beep with a slight warble | 587 Hz with 6.5 Hz vibrato, three harmonics |
| 6 | a very short high pip with a tiny ring | 1.3 kHz sine, fast exponential decay |
| 7 | a whistled bird call: two quick chirps and a longer trilled one | gliding sines with an up-and-down contour, a 26 Hz trill on the last |
| 8 | a long synthetic horn chord (D major add 9) that swells and fades | five detuned saw-like voices whose brightness follows the swell, slow vibrato |
| 10 | comic rubbery descending gurgle; at 10x speed a sharp zip or whip-crack | exponentially falling pitch (about 1.1 kHz to 150 Hz) with a "boing" wobble and a 26 Hz bubbling gate, full level from the start, a short filtered noise crack at the very beginning |
| 11 | an insect drone, nasal buzz with a wobble | harmonic voice at about 170 Hz with two broad formants, slow pitch wobble, 29 Hz wing flutter |
| 13 | a cat's meow (mm-ee-aa-oo, pitch up then down) | glottal-style harmonic voice, moving F1/F2 formants, light jitter |
| 14 | a longer, angrier yowl | like 13 but lower start, wider range, flatter spectrum, half-integer partials, 41 Hz roughness, breath noise |
| 20 | one small dry paw-step | low-passed noise thump plus a short 170 Hz knock |
| 21 | a short whimper, rising | voice sliding 420 to 760 Hz with 11 Hz tremble, "ee" colour |
| 22 | a longer whine, falling | voice sliding 820 to 360 Hz with 8 Hz tremble |
| 23 | one sharp yap with a growly decaying tail | voice with a bright onset (840 Hz) falling to 290 Hz, fast attack, 0.13 s decay, a noise burst on the attack |
| 24 | a wooden door banging shut: dull crack, then a short rattle | low noise crack, a 110 Hz thump, three wood modes (210/390/640 Hz), four decaying bounces |
| 26 | a single water drip | a sine bubble gliding 600 to 1150 Hz, 14 ms decay |
| 27 | a soft liquid "bloop" | a sine rising 280 to 680 Hz with a slow attack and a trace of 2nd harmonic |
| 28 | a soft small "plop" | a sine falling 520 to 170 Hz, short, with a puff of low noise |
| 29 | a tiny dry tick (the shortest) | 1 kHz damped sine plus a 1.5 ms noise grain, rounded onset |
| 31 | a slow food drip with a wet tail | one drip blip followed by five smaller decaying bubbles and a faint wet noise |
| 32 | a wet splat of many bits landing | a big band-passed noise impact with a falling thump, then 30 random small droplets thinning out |
| 33 | a sucking, squelching pull | rising growly voice with a sweeping vowel, moving resonant noise, irregular bubbling gate, closing pop |
| 34 | one heavy muffled human footstep | falling 110 to 52 Hz thump, low noise, a softer toe slap, a low rumble tail |
| 36 | a low engine motor, quiet, motor-like in any 0.1 s | 47 Hz four-stroke pulse train of damped resonances, a 94 Hz saw buzz and rough noise, all chopped; no attack or decay |
| 37 | a crisp crunch | eight small noise cracks (decreasing level) over a dull 170-210 Hz body |
| 38 | a short low gravelly roar | 55-95 Hz voice with half-integer partials, random amplitude jitter, formants near 650 and 1200 Hz |
| 39 | a longer low snarl | like 38 over two seconds, moving vowel, 27 Hz "rrr" gate |
| 40 | a short hollow pop | a 300 Hz damped sine dropping in pitch plus a 640 Hz partial |
| 41 | a soft steady shower, fading in and out | band-limited hiss plus random short pattering ticks, slow swell, soft limiter |
| 42 | a comic retching: three rough heaves and a wet gurgle | rough pulsing voice at 100-210 Hz with rising pitch in each heave, noise, then a descending wobbling "bleh" and bubble blips |
| 44 | a short wet slurp, ending in a smack | resonant noise sweeping 500 to 2000 Hz, a rising tone, a 31 Hz bubble gate, a closing blip |
| 45 | a longer, drawn-out slurp with a gulp | the same family, slower sweep, then a low falling gulp thump |
| 47 | a tiny dry tap | a short band-passed noise grain and a 760 Hz damped sine, a smaller bounce after 26 ms |
| 49 | a short ripping, tearing rasp | band-limited noise gated by random stick-slip pulses in three rips |

## Patch loudness change (spec side request, batch B review)

Renders showed the stings that use only `fm53` (chords) and `fm54` (pluck) far quieter than the full pieces, and effect 17 far quieter than intended. Changed in `make_fm_patches.py` (and `fm_patches.json` regenerated), no other patch touched:
- `fm53`: carrier level 12 -> 2 and `velocity_offset` -4 -> 0 (about 8 dB louder).
- `fm54`: carrier level 6 -> 0, `velocity_offset` -4 -> 0 (about 8 dB louder), carrier decay 8 -> 7 so the pluck rings a little longer.
- `fm17` (effect 17, the dig sound): carrier level 18 -> 6 (about 9 dB louder, still soft).
- `fm25` (lead, channel 1): carrier level 6 -> 0 (about 4.5 dB louder) so the lead stays above the louder `fm53` chords and lead-only pieces match the others.
