#!/usr/bin/env python3
"""The listening-pass renderer (issue #35): the clean pack's songs and effects beside the original's,
through the SAME mixer, stitched into listening files with a cue sheet.

Both sides are rendered by `OpenSimAnt.Replay --songs`, which plays the songs out of the SOUND archive
through OpenSimAnt.Data.SoundDriver and OpenSimAnt.Data.SoundMixer -- the remake's own copy of the
original's 5575.6 Hz driver plus its OPL2 and its two sample voices. It is given the clean pack's zip for
one side and the player's original files for the other, so both sides go through one synthesiser: a
difference you hear is notes, instruments or levels, never the renderer. (Rendering one side through
fluidsynth or Timidity and the other through the remake would make a synth difference read exactly like a
wrong instrument, which is the point of doing it this way.)

Usage, from the repo root, after a Release build (no other setup, no DAW step):

    dotnet build remake/OpenSimAnt.sln -c Release
    python3 tools/audio_render.py                    # render both sides, stitch, write docs/LISTENING.md
    python3 tools/audio_render.py --reuse            # reuse the WAVs of a previous run (seconds, not a rebuild)

Writes, into remake/build/listening/ (git-ignored):
  songs_pack.mp3 / .ogg        every cue of the clean pack, in id order, 2 s between tracks
  songs_original.mp3 / .ogg    the same cue list from the player's files, same order, same gaps
  effects_ab.mp3 / .ogg        effect 0..55: the original then the pack, back to back, for A/B
  cue_sheet.md                 track index, start, song id, duration and what to listen for
The mp3s carry a chapter at every track start; Ogg has no chapter standard, so the mp3 is the one to open
in a player that shows chapters (the sheet has the same times).

The output holds audio made from the player's own copy of the game -- never commit it (remake/build/ is
git-ignored). The cue sheet is the one text file that is meant to be committed (--cue).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import wave

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONG_GAP = 2.0          # seconds of silence between two songs
PAIR_GAP = 0.35         # inside an effect A/B pair: the original, then the pack
EFFECT_GAP = 1.2        # between two pairs
SAMPLE_RATE = 44100

# --- what to listen for, per song (docs/clean_pack/music.md sections 4 and 6) -----------------
LISTEN = {
    10001: "The main theme, and the loop seam: it plays until it is replaced, so at 103 s the end must rejoin "
           "the start with no click and no change of tempo, and the intro must not sound stale the second time.",
    10003: "Ambient theme 1, on repeat for minutes: the seam, and whether a tuned-percussion-only texture sits "
           "under the yard's effects without masking them.",
    10004: "Ambient theme 2 (quick, scurrying): the seam, and whether its brightness tires over repeats.",
    10005: "Ambient theme 3: the seam, and whether the crack (channel 6, this piece only) is too loud.",
    10006: "Spare, nothing triggers it: judge the piece on its own -- the two melodic voices against the drums.",
    10007: "Spare, nothing triggers it: a bouncy interlude; balance of the light beat against the lines.",
    10008: "Victory, played once: clipping on the final held chord, and whether it sounds decisive.",
    10010: "Defeat: the falling lines should read weary, not grim, and the last note must not cut off.",
    11002: "Travel flourish, heard often: its level against the effects -- it must not poke out of the mix.",
    11003: "The confirmation 'go!', heard many times a game: whether the 8-note figure grates on the tenth repeat.",
    11004: "Spare 'ta-da': the two melodic voices against the two light percussion hits.",
    11005: "Comic droop 'oh well': the wobble at the end should read as comic, not as a tuning error.",
    11006: "Exchange, chord voice alone: mono collapse -- a single shimmering voice is where a thin or clipped "
           "patch shows.",
    11007: "Spare two-note ominous sting: whether the low drop is audible in mono.",
    11013: "Recruit call, as written (11014 is +6 semitones, 11015 +12): the highest key is at most 83 -- check "
            "the top note is not shrill, then listen to the other two.",
    11014: "Recruit call +6 semitones: the same figure a fourth up, as the game plays it for 'recruit 10'.",
    11015: "Recruit call +12 semitones, an octave up: the register where a patch thins out.",
    11016: "Release 'dismissed, off you go' (11017 is +12): a relaxed falling phrase on the lead.",
    11017: "Release +12 semitones, an octave up.",
    11018: "The attack alarm: three repeated two-note figures -- unmistakable, but not grating.",
    11020: "The player's (black) queen: two voices; check the regal rising phrase is not clipped.",
    11021: "The rival (red) queen, 10.6 s on the chord voice: mono collapse, and whether the creeping line stays "
           "audible at low volume.",
    20000: "Happy sting (the queen scene): the attack transient, and its level against the effects.",
    20001: "A nest founded: a short upward phrase; balance against 20000 beside it.",
    20002: "The reds are gone: a strong full close -- check the final chord is not clipped.",
    20003: "First piece of the win screen: it must end unresolved, because 20004 follows at once.",
    20004: "Second piece of the win screen: the resolution. Judge 20003 -> 20004 as one 11 s piece, and the join.",
    20005: "Full Game won: everything the orchestra has at once, the loudest piece -- check it for clipping.",
    20007: "Sad piece 1 of 5 (one at random on each death): a gently comic lament, not a tragedy, and whether the "
           "long descending line sags into mud.",
    20008: "Sad piece 2: a tired trudging march; the plod should read as tired, not as dragging.",
    20009: "Sad piece 3: a fluttering descent on the pluck voice within about seven semitones -- the quiet end must "
           "still be audible.",
    20010: "Sad piece 4: a short sighing phrase; its two voices against each other.",
    20011: "Sad piece 5: a short low dirge -- whether the low register survives mono on a small speaker.",
}

# docs/clean_pack/sounds.md section 2: the effect numbers whose instrument is an FM patch (15 and 16 share
# one patch); every other 1..54 is a sample, and 55 is sample 10 played ten times faster.
FM_EFFECTS = {0, 3, 9, 15, 16, 17, 18, 19, 25, 30, 35, 46, 48, 50, 51, 53, 54}


def effect_kind(n: int) -> str:
    if n == 55:
        return "sample 10 at 10x"
    return "FM patch" if n in FM_EFFECTS else "sample"


def run(cmd: list[str], cwd: str) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def render_songs(source: str, outdir: str, reuse: bool) -> list[int]:
    """Render every cue and effect of `source` (a pack .zip or the original's folder) with --songs."""
    if reuse and os.path.isdir(outdir) and any(f.startswith("song_") for f in os.listdir(outdir)):
        print(f"reusing {outdir}")
    else:
        os.makedirs(outdir, exist_ok=True)
        run(["dotnet", "run", "--project", "tests/OpenSimAnt.Replay", "-c", "Release", "--no-build",
             "--", "--songs", source, outdir], cwd=os.path.join(REPO, "remake"))
    return sorted(int(m.group(1)) for f in os.listdir(outdir)
                  if (m := re.fullmatch(r"song_(\d+)\.wav", f)))


def wav_info(path: str) -> tuple[float, int, int, int]:
    with wave.open(path) as w:
        return (w.getnframes() / w.getframerate(), w.getframerate(), w.getnchannels(), w.getsampwidth())


def stitch(parts: list[tuple[str, float, str]], out_wav: str) -> list[tuple[float, float, str]]:
    """Concatenate `parts` (wav path, silence after it, chapter title) into one wav.

    Returns (start, duration, title) per part."""
    chapters, at = [], 0.0
    with wave.open(out_wav, "wb") as out:
        first = True
        for path, gap, title in parts:
            with wave.open(path) as w:
                if first:
                    out.setnchannels(w.getnchannels())
                    out.setsampwidth(w.getsampwidth())
                    out.setframerate(w.getframerate())
                    first = False
                elif (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (
                        out.getnchannels(), out.getsampwidth(), out.getframerate()):
                    sys.exit(f"{path}: {w.getnchannels()}ch/{w.getsampwidth() * 8}bit/{w.getframerate()}Hz "
                             f"does not match the first file")
                dur = w.getnframes() / w.getframerate()
                remaining = w.getnframes()
                while remaining > 0:
                    chunk = w.readframes(min(remaining, 1 << 16))
                    out.writeframes(chunk)
                    remaining -= len(chunk) // (w.getsampwidth() * w.getnchannels())
                chapters.append((at, dur, title))
                at += dur
                silence = int(round(gap * out.getframerate()))
                if silence:
                    out.writeframes(b"\0" * silence * out.getsampwidth() * out.getnchannels())
                    at += silence / out.getframerate()
    return chapters


def write_ffmetadata(path: str, title: str, chapters: list[tuple[float, float, str]]) -> None:
    lines = [";FFMETADATA1", f"title={title}"]
    for i, (start, dur, name) in enumerate(chapters):
        lines += ["[CHAPTER]", "TIMEBASE=1/1000",
                  f"START={int(round(start * 1000))}",
                  f"END={int(round((start + dur) * 1000))}",
                  f"title={i + 1:02d} {name}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def encode(wav: str, out_base: str, title: str, chapters: list[tuple[float, float, str]],
           ogg: bool) -> None:
    meta = out_base + ".chapters.txt"
    write_ffmetadata(meta, title, chapters)
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg is not on PATH: it is what turns the stitched WAVs into mp3/ogg (apt install ffmpeg)")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-i", meta, "-map_metadata", "1",
         "-c:a", "libmp3lame", "-q:a", "5", out_base + ".mp3"], cwd=REPO)
    if ogg:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5",
             out_base + ".ogg"], cwd=REPO)
    os.remove(meta)


def songs_table() -> dict[int, dict[str, str]]:
    """The song table of docs/clean_pack/music.md section 4, by cue id: cue -> when it plays, tier, target
    length. A cue that is another song's transposition (11014/11015 are 11013 at +6/+12) takes that song's row
    and names the transposition, so no track is left without its description."""
    rows, path = {}, os.path.join(REPO, "docs", "clean_pack", "music.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return rows
    by_song = {}
    for line in text.splitlines():
        m = re.match(r"\|\s*(\d{5})\s*\|\s*([\d,\s]+)\|\s*([AB])\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|", line)
        if m:
            by_song[int(m.group(1))] = {"cues": [int(c) for c in m.group(2).split(",")],
                                        "tier": m.group(3), "when": m.group(4), "length": m.group(5)}
        # section 5's cue table: | cue | song | transposition |
        t = re.match(r"\|\s*(\d{5})\s*\|\s*(\d{5})\s*\|\s*([+-]\d+)\s*\|", line)
        if t:
            by_song.setdefault(int(t.group(2)), {"cues": [], "tier": "", "when": "", "length": ""})
            by_song[int(t.group(2))].setdefault("transpose", {})[int(t.group(1))] = int(t.group(3))
    for song, row in by_song.items():
        for cue in row["cues"] + [c for c in row.get("transpose", {}) if c not in row["cues"]]:
            if cue == song:
                when = row["when"]
            else:
                semis = row.get("transpose", {}).get(cue, 0)
                when = f"{row['when']} -- played as cue {cue}, {semis:+d} semitones"
            rows[cue] = {"song": str(song), "tier": row["tier"], "when": when, "length": row["length"]}
    return rows


def listening_time(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(round(seconds % 60)):02d}"


def main() -> int:
    global REPO
    ap = argparse.ArgumentParser(description="Render the pack's and the original's audio through one mixer, "
                                             "stitched for the owner's listening pass (issue #35).")
    ap.add_argument("--repo", default=REPO, help="the clone's root (default: this script's repository)")
    ap.add_argument("--original", default=None, help="the original's folder (default: the repo root, where "
                     "SIMANT.EXE and SOUND.DAT are)")
    ap.add_argument("--pack", default=os.path.join("game", "assets", "clean", "clean_pack.zip"),
                    help="the clean pack's zip, relative to remake/ (default: %(default)s)")
    ap.add_argument("--out", default=os.path.join(REPO, "remake", "build", "listening"),
                    help="where the rendered WAVs and the listening files go (default: remake/build/listening, "
                         "git-ignored)")
    ap.add_argument("--cue", default=os.path.join(REPO, "docs", "LISTENING.md"),
                    help="the cue sheet to write (default: docs/LISTENING.md); '' for none")
    ap.add_argument("--reuse", action="store_true", help="reuse the WAVs of a previous run instead of re-rendering")
    ap.add_argument("--no-ogg", action="store_true", help="mp3 only (skip the Ogg Vorbis copies)")
    a = ap.parse_args()

    REPO = os.path.abspath(a.repo)
    original = os.path.abspath(a.original or REPO)
    wavs = os.path.join(a.out, "wav")
    pack_zip = os.path.join(REPO, "remake", a.pack)
    for p in (pack_zip, os.path.join(original, "SIMANT.EXE")):
        if not os.path.exists(p):
            sys.exit(f"missing {p}")
    os.makedirs(a.out, exist_ok=True)

    ids_pack = render_songs(pack_zip, os.path.join(wavs, "pack"), a.reuse)
    ids_orig = render_songs(original, os.path.join(wavs, "original"), a.reuse)
    if ids_pack != ids_orig:
        sys.exit(f"the two sides do not carry the same cue list: pack {ids_pack} vs original {ids_orig}")
    print(f"{len(ids_pack)} cues on both sides")

    table = songs_table()

    # ---- songs, one stitched file per side, the same order on both
    chapters = {}
    for side, wavdir in (("pack", "pack"), ("original", "original")):
        parts = []
        for i, n in enumerate(ids_pack):
            info = table.get(n, {})
            part = os.path.join(wavs, wavdir, f"song_{n}.wav")
            title = f"song {n}" + (f" ({info['tier']})" if info.get("tier") else "")
            parts.append((part, SONG_GAP, title))
        stitched = os.path.join(a.out, f"songs_{side}.wav")
        chapters[side] = stitch(parts, stitched)
        encode(stitched, os.path.join(a.out, f"songs_{side}"),
               f"OpenSimAnt listening pass -- clean pack songs" if side == "pack"
               else "OpenSimAnt listening pass -- original songs", chapters[side], not a.no_ogg)
        os.remove(stitched)
        print(f"wrote songs_{side}.mp3  ({len(ids_pack)} cues, {listening_time(chapters[side][-1][0] + chapters[side][-1][1])})")

    # ---- effects, A/B: the original then the pack, per effect number
    parts, fx_rows = [], []
    for n in range(56):
        o = os.path.join(wavs, "original", f"fx_{n:02d}.wav")
        p = os.path.join(wavs, "pack", f"fx_{n:02d}.wav")
        od, pd = wav_info(o)[0], wav_info(p)[0]
        fx_rows.append((n, od, pd))
        parts.append((o, PAIR_GAP, f"fx {n:02d} -- the original"))
        parts.append((p, EFFECT_GAP, f"fx {n:02d} -- the pack"))
    stitched = os.path.join(a.out, "effects_ab.wav")
    fx_chapters = stitch(parts, stitched)
    encode(stitched, os.path.join(a.out, "effects_ab"), "OpenSimAnt listening pass -- effects A/B", fx_chapters,
           not a.no_ogg)
    os.remove(stitched)
    fx_total = fx_chapters[-1][0] + fx_chapters[-1][1]
    print(f"wrote effects_ab.mp3  (56 effects, original then pack, {listening_time(fx_total)})")

    # ---- the cue sheet
    total_pack = chapters["pack"][-1][0] + chapters["pack"][-1][1]
    total_orig = chapters["original"][-1][0] + chapters["original"][-1][1]
    if a.cue:
        lines = [
            "# Listening pass: the clean pack's songs and effects, beside the original's",
            "",
            "Generated by `tools/audio_render.py` -- do not hand-edit; re-run the tool instead. This is the",
            "sheet for issue #21 (the owner's listening pass) and the file list it asks for; #21 itself has no",
            "id list of its own, so this is that list.",
            "",
            "Both files were rendered by `OpenSimAnt.Replay --songs` through `OpenSimAnt.Data.SoundMixer` -- the",
            "remake's own copy of the driver, its OPL2 and its two sample voices -- from the clean pack's zip on",
            "one side and the player's original files on the other. One synthesiser for both sides, so what you",
            "hear differs by notes, instruments and levels, never by renderer.",
            "",
            "| File | Contents | Listening time |",
            "|---|---|---|",
            f"| `songs_pack.mp3` / `.ogg` | the {len(ids_pack)} cues of the clean pack, in cue order | "
            f"**{listening_time(total_pack)}** |",
            f"| `songs_original.mp3` / `.ogg` | the same {len(ids_orig)} cues from the original files, same order | "
            f"**{listening_time(total_orig)}** |",
            f"| `effects_ab.mp3` / `.ogg` | effect 0..55, the original then the pack, back to back | "
            f"**{listening_time(fx_total)}** |",
            "",
            "The mp3s carry a chapter at every track start (2 s of silence between songs, 0.35 s inside an",
            "effect pair, 1.2 s between pairs); Ogg has no chapter standard, so open the mp3 where chapters",
            "matter, and use the tables below for the times. All three files are mono 44.1 kHz, straight from",
            "the mixer: no EQ, no compression, no normalisation -- levels are comparable across files.",
            "",
            "Reproduce (from the clone root, no DAW step):",
            "",
            "```",
            "dotnet build remake/OpenSimAnt.sln -c Release",
            "python3 tools/audio_render.py",
            "```",
            "",
            "The audio lands in `remake/build/listening/` (git-ignored: it is made from the player's own copy",
            "of the game). `--reuse` re-stitches a previous render in seconds.",
            "",
            "## The songs",
            "",
            "Track order is cue order on both files, so track *n* in one is the same cue as track *n* in the",
            "other. \"Plays when\" is the spec's own description (`docs/clean_pack/music.md` section 4); \"listen",
            "for\" is what this pass is asking your ears.",
            "",
            "| # | start | cue | pack | original | plays when | listen for |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, n in enumerate(ids_pack):
            start = chapters["pack"][i][0]
            info = table.get(n, {})
            pd = chapters["pack"][i][1]
            od = chapters["original"][i][1]
            when = info.get("when", "").replace("|", "/")
            listen = LISTEN.get(n, "Balance, and whether anything in it is clipping.").replace("|", "/")
            lines.append(f"| {i + 1} | {listening_time(start)} | {n} | {pd:.1f} s | {od:.1f} s | {when} | {listen} |")
        lines += [
            "",
            "Cue tier: A is triggered by the game, B is spare (nothing plays it). 11014/11015 are 11013 at +6",
            "and +12 semitones and 11017 is 11016 at +12 -- the game plays those transpositions, so they are",
            "separate tracks here rather than one tune sped up.",
            "",
            "## The effects",
            "",
            "Each pair is the original, 0.35 s of silence, the pack. These are short: the level match against",
            "the songs and against each other is the thing to judge, not the notes.",
            "",
            "| # | kind | original | pack | listen for |",
            "|---|---|---|---|---|",
        ]
        for n, od, pd in fx_rows:
            kind = effect_kind(n)
            if n == 55:
                what = "sample 10 at ten times speed (the spider's lash) -- it must still read as a strike."
            elif kind == "FM patch":
                what = "an FM patch with no note-off: it must fade out by itself, and sit at the same loudness as its neighbours."
            else:
                what = ("a sampled effect, recorded at 5.5 kHz by design: judge the envelope and the level, "
                        "not the bandwidth.")
            lines.append(f"| {n} | {kind} | {od:.2f} s | {pd:.2f} s | {what} |")
        lines += [
            "",
            "The original's raw sample sources are the 57 WAVs under `extracted/sound/sfx/` (16-bit mono at",
            "5,576 Hz, one per sample). The original column above is those, or the original's FM patches, played",
            "by the mixer -- the same path the game uses, which is what makes the A/B fair.",
            "",
            "## What this pass cannot tell you",
            "",
            "- The DAC/FM balance: `SoundMixer.SampleGain` is a stated estimate, not a measurement (the card's",
            "  own mix was never measured here), so a level mismatch between a sampled effect and an FM one may",
            "  be the mixer's gain rather than the pack's design. Say so if that is what you hear.",
            "- How it sounds beside the yard's other audio in a real game: these are solo renders. Anything that",
            "  only shows up in play (an effect under a song, a cue cut off by the next one) needs a play-test.",
            "",
        ]
        with open(a.cue, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"wrote {a.cue}")

    print(f"total listening time: songs pack {listening_time(total_pack)}, original {listening_time(total_orig)}, "
          f"effects A/B {listening_time(fx_total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
