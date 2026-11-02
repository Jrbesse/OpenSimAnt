#!/usr/bin/env python3
"""Writes fm_patches.json: the 16 two-operator FM patches of the clean sound bank.

Spec: docs/clean_pack/sounds.md section 5. Run from anywhere:  python make_fm_patches.py
Deterministic (no random numbers).  Also prints a rough audible-length estimate per patch
(carrier envelope only: decay down to the sustain level, then the release rate, to -40 dB),
which is the only "preview" kept here; the real chip is rendered by the spec side.

Reading the numbers (OPL2): rates 15 = fastest .. 0 = never; full-scale-to-silence time is
about 2 ms * 2^(15 - rate).  Levels are 0.75 dB per step (0 = loudest).  Key k sounds at
440 * 2^((k - 57) / 12) Hz (key 60 = 523 Hz).  Multiples: 0 = x0.5, 1..10 = x1..x10, 11 = x10,
12/13 = x12, 14/15 = x15.  Connection 0 = FM (modulator bends the carrier), 1 = both added.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def op(multiple, level, attack, decay, sustain_level, release,
       tremolo=0, vibrato=0, sustain=0, ksr=0, ksl=0):
    """One operator, fields in the order of the spec."""
    return {"tremolo": tremolo, "vibrato": vibrato, "sustain": sustain, "ksr": ksr,
            "multiple": multiple, "ksl": ksl, "level": level, "attack": attack,
            "decay": decay, "sustain_level": sustain_level, "release": release}


def patch(pid, instruments, feedback, connection, mod, car, note,
          effect_key=None, velocity_offset=0):
    p = {"id": pid, "instruments": instruments}
    if effect_key is not None:
        p["effect_key"] = effect_key
    p.update({"velocity_offset": velocity_offset, "feedback": feedback,
              "connection": connection, "modulator": mod, "carrier": car, "note": note})
    return p


PATCHES = [
    # --- the ten song voices -------------------------------------------------------------
    # fm25, lead: 1:1 FM, moderate index that relaxes after the attack, light vibrato on both
    # operators, a long tail. The modulator's key scaling dims the brightness on high keys so
    # that keys up to 88 stay singing instead of shrill.
    patch("fm25", [25], 2, 0,
          op(1, 22, 13, 6, 7, 6, vibrato=1, sustain=1, ksl=1),
          op(1, 0, 12, 5, 3, 5, vibrato=1),
          "Clear, singing lead with light vibrato: bright on the attack, mellowing, a long tail.",
          velocity_offset=0),
    # fm53, pad: low modulation index, a gentle attack (~30 ms), no tremolo or vibrato, so
    # that several notes at once blend smoothly; sits a little under the lead.
    patch("fm53", [53], 1, 0,
          op(1, 32, 7, 5, 8, 5, sustain=1, ksl=1),
          op(1, 2, 7, 5, 4, 5),
          "Round, soft chord voice that fades in over ~30 ms and has a long smooth tail.",
          velocity_offset=0),
    # fm3, bass: 1:1 with a weak modulator that fades faster than the carrier = a firm
    # attack that settles into an almost pure, heavy fundamental; ~0.8 s tail.
    patch("fm3", [3], 2, 0,
          op(1, 28, 15, 8, 10, 8),
          op(1, 4, 14, 6, 5, 5),
          "Warm, round bass: firm attack, strong fundamental, medium-long tail.",
          velocity_offset=0),
    # fm54, pluck: modulator at x3 with a big index that collapses within ~20 ms leaves a
    # woody marimba-like "tok" on top of a quick-decaying body, then a short ring.
    patch("fm54", [54], 0, 0,
          op(3, 16, 15, 10, 15, 10, ksl=1),
          op(1, 0, 15, 7, 6, 6),
          "Plucked marimba / harp-like voice: sharp attack, quick decay, short ring.",
          velocity_offset=0),
    # fm35, kick and foot stamp: modulator feedback gives a very brief click, then a sine
    # body with a quick fall; effect_key 30 = 92 Hz, heavy for the stamp.
    patch("fm35", [35], 4, 0,
          op(1, 14, 15, 11, 15, 11),
          op(1, 0, 15, 7, 10, 7),
          "Deep drum thump with a touch of click; as the stamp a heavy low thud, ~0.2 s.",
          effect_key=30, velocity_offset=-8),
    # fm46, snare/clap: full feedback on a x15 modulator is chaotic = noise; it bends a x2
    # carrier into a hissy crack of ~0.12 s; the noise thins out faster than the carrier.
    patch("fm46", [46], 7, 0,
          op(14, 8, 15, 9, 15, 9),
          op(2, 6, 15, 8, 15, 8),
          "Noisy snare / clap crack, fast attack, ~0.12 s.",
          velocity_offset=-10),
    # fm50, tick: the shortest voice: a noisy x12 modulator on a x1 carrier, ~30 ms; key
    # scaling on the carrier keeps the top keys from piercing; sits low in the mix.
    patch("fm50", [50], 5, 0,
          op(12, 12, 15, 11, 15, 11),
          op(1, 14, 15, 10, 15, 10, ksl=1),
          "Very short, dry high tick (about 30 ms), quiet.",
          velocity_offset=-20),
    # fm51, tuned drum: x2 modulator with a click-length envelope on a x1 carrier = a
    # wooden "bonk" with a clear fundamental; 0.25 s fall; readable as a tune at 36..84.
    patch("fm51", [51], 0, 0,
          op(2, 20, 15, 10, 15, 10),
          op(1, 6, 15, 7, 15, 7),
          "Pitched tom / log drum: fast attack, clear fundamental, ~0.25 s fall.",
          velocity_offset=-6),
    # fm48, shaker: soft (~4 ms) attack, a full-feedback x15 modulator on a x6 carrier
    # (noise), carrier key scaling against hiss on the highest keys; about 0.12 s; quiet.
    patch("fm48", [48], 7, 0,
          op(15, 10, 10, 8, 15, 8),
          op(6, 16, 10, 8, 15, 8, ksl=1),
          "Short noisy swish with a soft attack, ~0.12 s, kept low in the mix.",
          velocity_offset=-28),
    # fm0, bell/mallet: ADDED (connection 1) carrier x1 + a quickly fading x3 partial with a
    # little feedback = a clear fundamental with a bright, slightly out-of-tune strike
    # (glockenspiel-like partial ~2.8x). ksr shortens the ring on higher keys, as bells do.
    patch("fm0", [0], 2, 1,
          op(3, 14, 15, 8, 15, 8),
          op(1, 8, 15, 5, 15, 5, ksr=1),
          "Glockenspiel / small bell: bright strike, clear pitch, ring of about 0.5 to 1 s.",
          velocity_offset=-8),

    # --- the effects ---------------------------------------------------------------------
    # fm9, spray puff and footfall: noise (full feedback x15) bending a x3 carrier, ~3 ms soft
    # attack, the noise lasting a little longer than the carrier so it ends as hiss; light.
    patch("fm9", [9], 7, 0,
          op(15, 14, 11, 7, 15, 7),
          op(3, 12, 11, 8, 15, 8),
          "Airy puff / hiss, softly starting and falling away, ~0.12 s; light enough to repeat.",
          effect_key=70, velocity_offset=-12),
    # fm15, acknowledgement blip: clean 1:2 FM, no feedback, a bright start that mellows.
    patch("fm15", [15, 16], 0, 0,
          op(2, 16, 15, 10, 15, 10),
          op(1, 6, 15, 9, 15, 9),
          "Clean short bright blip, ~0.07 s.",
          effect_key=69, velocity_offset=-6),
    # Dig family (fm17, fm18, fm19): same multiples (modulator x5, carrier x1), feedback 3,
    # rates 15 / 11 / 9 or 8; they differ in pitch and levels. 17 = base scrape-tick, 18 =
    # lower and duller (weaker modulation, quieter), 19 = higher, brighter, longer, cheerful.
    patch("fm17", [17], 3, 0,
          op(5, 16, 15, 11, 15, 11),
          op(1, 6, 15, 9, 15, 9),
          "Small dry scrape-tick, soft and unobtrusive, ~0.06 s (the dig family's base).",
          effect_key=67, velocity_offset=-8),
    patch("fm18", [18], 3, 0,
          op(5, 28, 15, 11, 15, 11),
          op(1, 18, 15, 9, 6, 8),
          "Same family as fm17 but lower and duller (a fifth below, little brightness), ~0.08 s.",
          effect_key=60, velocity_offset=-8),
    patch("fm19", [19], 3, 0,
          op(5, 10, 15, 11, 15, 11),
          op(1, 10, 15, 8, 8, 7),
          "Same family, brighter and longer: a small cheerful pop, ~0.15 s.",
          effect_key=72, velocity_offset=-4),
    # fm30, stone knock: x3 modulator with feedback gives a hollow click that dies at once,
    # leaving a dull low body (~260 Hz) of ~0.12 s.
    patch("fm30", [30], 3, 0,
          op(3, 14, 15, 12, 15, 12),
          op(1, 4, 15, 8, 15, 8),
          "Dull stone knock: short hollow body with a bit of click, ~0.12 s.",
          effect_key=48, velocity_offset=-6),
]


def t_to_minus40(op_, floor_db=40.0):
    """Rough time (s) from full level to -40 dB for the carrier's decay + release."""
    t96 = lambda r: float("inf") if r == 0 else 0.002 * 2 ** (15 - r)
    sl_db = 93.0 if op_["sustain_level"] == 15 else 3.0 * op_["sustain_level"]
    d = op_["decay"]
    first = min(floor_db, sl_db)
    t = first / 96.0 * t96(d)
    if floor_db > sl_db:
        t += (floor_db - sl_db) / 96.0 * t96(op_["release"])
    return t


def main():
    assert len(PATCHES) == 16
    path = os.path.join(HERE, "fm_patches.json")
    with open(path, "w", newline="\n") as f:
        json.dump({"patches": PATCHES}, f, indent=2)
        f.write("\n")
    for p in PATCHES:
        print("%-5s carrier to -40 dB: %.3f s   %s" % (p["id"], t_to_minus40(p["carrier"]), p["note"]))
    print("wrote", path)


if __name__ == "__main__":
    main()
