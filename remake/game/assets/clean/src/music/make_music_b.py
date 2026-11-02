#!/usr/bin/env python3
"""Batch B of the clean music pack: the ambient themes 10003..10005 and the short pieces.

Original compositions, written from the spec docs/clean_pack/music.md only.
Run:  python make_music_b.py     (writes <song id>.mid and README_b.md next to this file;
                                  deterministic, standard library only, MIDI bytes written here)

NOTATION (the music is data: one string per voice)
  token      = PITCH[:UNITS][@VEL][ACCENTS]
  PITCH      = r (rest) | NOTE | NOTE+NOTE+NOTE (a chord on one channel)
  NOTE       = letter A..G, optional # or b, octave digit: C4 is written key 60 (the sound is an
               octave higher than the usual MIDI convention, see the spec).  B6 = 95 is the top key.
  :UNITS     = length in grid units (the song's `unit` in ticks; default 1)
  @VEL       = absolute velocity for this note;  ! = +10, . = -8 (accent / soft; may repeat)
  v=NN       = sets the base velocity from here on in this string
  >N         = jump to absolute position N (units) in this string
  |          = bar line (checked: the position must be a multiple of the song's `bar`)
Each channel holds one or several strings (layers) that play together (a layer is monophonic).
A note sounds for its length minus a small gap (channel option `gap`, in ticks) and at most
`hold` ticks (drum voices are cut short).
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PPQ = 240
PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
NOTE_RE = re.compile(r'^([A-G])([#b]?)(\d)$')
TOK_RE = re.compile(r'^(r|[A-G][#b]?\d(?:\+[A-G][#b]?\d)*)(?::(\d+))?(@\d+)?([!.]*)$')

# written-key ranges of the channels (spec section 2) and default velocities
RANGE = {1: (48, 88), 2: (40, 80), 3: (24, 52), 4: (48, 88), 5: (20, 55),
         6: (40, 80), 7: (60, 95), 8: (36, 84), 9: (50, 95), 10: (60, 95)}
VEL = {1: 105, 2: 75, 3: 98, 4: 88, 5: 105, 6: 95, 7: 64, 8: 92, 9: 55, 10: 85}
DRUM = (5, 6, 7, 9)


def key_of(name):
    m = NOTE_RE.match(name)
    if not m:
        raise ValueError('bad note name ' + name)
    k = 12 * (int(m.group(3)) + 1) + PC[m.group(1)]
    k += {'#': 1, 'b': -1, '': 0}[m.group(2)]
    return k


def parse_layer(text, unit, vel0, bar, label):
    """-> (events [(tick, dur_ticks, key, vel)], end_tick)"""
    ev, pos, vel = [], 0, vel0
    for tok in text.split():
        if tok == '|':
            if bar:
                assert pos % bar == 0, '%s: bar line at unit %d is not a multiple of %d' % (label, pos, bar)
            continue
        if tok.startswith('v='):
            vel = int(tok[2:])
            continue
        if tok.startswith('>'):
            n = int(tok[1:])
            assert n >= pos, '%s: jump back to %d from %d' % (label, n, pos)
            pos = n
            continue
        m = TOK_RE.match(tok)
        assert m, '%s: bad token %r' % (label, tok)
        p, d, v, acc = m.groups()
        d = int(d) if d else 1
        if p != 'r':
            nv = int(v[1:]) if v else vel
            nv += 10 * acc.count('!') - 8 * acc.count('.')
            nv = max(2, min(127, nv))
            for nm in p.split('+'):
                ev.append((pos * unit, d * unit, key_of(nm), nv))
        pos += d
    return ev, pos * unit


def vlq(n):
    b = [n & 0x7F]
    n >>= 7
    while n:
        b.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(b))


def chunk(tag, data):
    return tag + struct.pack('>I', len(data)) + data


def track_bytes(events, end):
    """events: [(tick, order, bytes)]; order 0 before 1 at the same tick"""
    out = b''
    t = 0
    for tick, _o, data in sorted(events, key=lambda e: (e[0], e[1])):
        out += vlq(tick - t) + data
        t = tick
    out += vlq(end - t) + b'\xFF\x2F\x00'
    return chunk(b'MTrk', out)


class Song:
    def __init__(self, sid, bpm, unit, bar, chans, ts=(4, 4), name='', info='', key=''):
        self.sid, self.unit, self.bar = sid, unit, bar
        self.tempi = bpm if isinstance(bpm, list) else [(0, bpm)]  # [(unit position, bpm)]
        self.chans, self.ts, self.name, self.info, self.key = chans, ts, name, info, key

    def build(self):
        u = self.unit
        tracks, notes, end = {}, [], 0
        for ch, spec in sorted(self.chans.items()):
            layers = spec['layers'] if isinstance(spec['layers'], list) else [spec['layers']]
            vel0 = spec.get('vel', VEL[ch])
            gap = spec.get('gap', 3 if ch in DRUM else 10)
            hold = spec.get('hold', 64 if ch in DRUM else None)
            evs = []
            for i, lt in enumerate(layers):
                e, endt = parse_layer(lt, u, vel0, self.bar, '%s ch%d layer%d' % (self.sid, ch, i))
                end = max(end, endt)
                for (t, d, k, v) in e:
                    ln = d - gap
                    if hold:
                        ln = min(ln, hold)
                    assert ln > 0, (self.sid, ch, t)
                    lo, hi = RANGE[ch]
                    assert lo - 6 <= k <= hi + 6, '%s ch%d key %d far outside range' % (self.sid, ch, k)
                    if not (lo <= k <= hi):
                        print('  note: %s ch%d key %d outside %d..%d' % (self.sid, ch, k, lo, hi))
                    evs.append((t, 1, bytes([0x90 | ch, k, v])))
                    evs.append((t + ln, 0, bytes([0x80 | ch, k, 64])))
                    notes.append((t, t + ln, ch, k))
            tracks[ch] = evs
        last_off = max(n[1] for n in notes)
        end = max(end, last_off)
        # conductor
        us = lambda b: int(round(60000000 / b))
        cond = [(0, 0, b'\xFF\x51\x03' + us(self.tempi[0][1]).to_bytes(3, 'big'))]
        nm = self.name.encode('ascii')
        cond.append((0, 0, b'\xFF\x03' + vlq(len(nm)) + nm))
        cond.append((0, 0, b'\xFF\x58\x04' + bytes([self.ts[0], {2: 1, 4: 2, 8: 3}[self.ts[1]], 24, 8])))
        for pos, b in self.tempi[1:]:
            cond.append((pos * u, 0, b'\xFF\x51\x03' + us(b).to_bytes(3, 'big')))
        body = [chunk(b'MThd', struct.pack('>HHH', 1, 1 + len(tracks), PPQ)), track_bytes(cond, end)]
        for ch, evs in sorted(tracks.items()):
            names = b'ch%d' % ch
            evs = [(0, -1, b'\xFF\x03' + vlq(len(names)) + names)] + evs
            body.append(track_bytes(evs, end))
        data = b''.join(body)
        # statistics
        self.data = data
        self.n_notes = len(notes)
        self.seconds = self.ticks_to_sec(end)
        self.tail = self.ticks_to_sec(end) - self.ticks_to_sec(last_off)
        self.first = self.ticks_to_sec(min(n[0] for n in notes))
        ons = sorted([(n[0], 1, n[2]) for n in notes] + [(n[1], 0, n[2]) for n in notes])
        held, mx, per = 0, 0, {}
        for t, kind, ch in ons:
            if kind:
                held += 1
                per[ch] = per.get(ch, 0) + 1
            else:
                held -= 1
                per[ch] -= 1
            mx = max(mx, held)
        self.maxpoly = mx
        # the maximum is meaningful only after all events of one tick: recompute grouped
        by_tick, held, mx = {}, 0, 0
        for t, kind, ch in ons:
            by_tick.setdefault(t, []).append(kind)
        for t in sorted(by_tick):
            for kind in by_tick[t]:
                held += 1 if kind else -1
            mx = max(mx, held)
        self.maxpoly = mx
        return data

    def ticks_to_sec(self, ticks):
        tm = [(p * self.unit, b) for p, b in self.tempi]
        s = 0.0
        for i, (t0, b) in enumerate(tm):
            t1 = tm[i + 1][0] if i + 1 < len(tm) else None
            if t1 is None or ticks <= t1:
                return s + (ticks - t0) * 60.0 / b / PPQ
            s += (t1 - t0) * 60.0 / b / PPQ
        return s


SONGS = []


def song(*a, **k):
    SONGS.append(Song(*a, **k))


def C(layers, **opt):
    d = {'layers': layers}
    d.update(opt)
    return d


# =====================================================================================
# THE AMBIENT THEMES (channels 5..10 only)
# =====================================================================================

# ---- 10003: swaying 6/8 in F major, tuned drum tune over a bell glow ------------------
# unit = sixteenth (60 ticks); a bar of 6/8 is 12 units; quarter = 90 bpm; 28 bars = 56 s
_K = "C2:1 r:5 C2:1. r:5 | "
_K1 = "C2:1 r:11 | "
_T = "G5:2! G5:2. G5:2. G5:2 G5:2. G5:2. | "
_TC = "G5:2. r:4 G5:2. r:4 | "
_S = "r:2 C5:2 C5:2 r:2 C5:2 C5:2 | "
_SC = "r:6 C5:2 r:4 | "
# tuned drum (channel 8): the tune
_a = "C5:3 A4:1 G4:2 A4:6 | F4:3 G4:1 A4:2 G4:6 | C5:3 D5:1 C5:2 A4:6 | G4:3 A4:1 G4:2 F4:6 | "
_a2 = "C5:3 A4:1 G4:2 A4:3 C5:3 | F4:3 G4:1 A4:2 G4:3 F4:3 | C5:3 D5:1 C5:2 A4:3 G4:3 | A4:3 G4:1 F4:2 F4:6 | "
_b = "D5:3 C5:1 Bb4:2 C5:6 | C5:3 Bb4:1 A4:2 Bb4:6 | A4:3 G4:1 F4:2 G4:6 | A4:3 Bb4:1 C5:8 | "
_c = "v=62 F3:6 C4:6 | F3:6 C4:6 | Bb3:6 F4:6 | C4:6 G3:6 | v=92 "
_a4 = "C5:3 A4:1 G4:2 A4:6 | F4:3 G4:1 A4:2 C5:6 | D5:3 C5:1 A4:2 G4:6 | A4:3 G4:1 F4:2 F4:6 | "
_out_t = "A4:3 G4:1 F4:2 G4:6 | F4:12 | "
# bell (channel 10)
_i_b = "F5:4 A5:4 C6:4 | G5:4 A5:4 F5:4 | "
_ba = "r:6 C6:6 | r:6 A5:6 | r:6 D6:6 | r:6 C6:6 | "
_ba2 = "r:6 F5:2 A5:2 C6:2 | r:6 G5:2 A5:2 F5:2 | r:6 D5:2 F5:2 A5:2 | r:6 G5:2 E5:2 C5:2 | "
_bb = "Bb5:6 D6:6 | A5:6 C6:6 | G5:6 Bb5:6 | A5:6 C6:6 | "
_bc = "v=66 C6:6 A5:3 F5:3 | G5:6 A5:3 C6:3 | D6:6 C6:3 A5:3 | G5:3 A5:3 F5:6 | v=78 "
_out_b = "r:6 C6:6 | F5:12 | "
song('10003', 90, 60, 12, {
    5: C(_K * 2 + _K * 16 + _K1 * 4 + _K * 4 + _K + "C2:2 r:10 | ", vel=76, hold=40),
    7: C("r:12 | " + _T + _T * 16 + _TC * 4 + _T * 4 + _T + "G5:2. r:10 | ", vel=56, hold=40),
    8: C("r:12 | r:12 | " + _a + _a2 + _b + _a + _c + _a4 + _out_t, vel=84, gap=14),
    9: C("r:12 | r:12 | " + _S * 16 + _SC * 4 + _S * 4 + _S + "r:12 | ", vel=44, hold=36),
    10: C(_i_b + _ba + _ba2 + _bb + _ba + _bc + _ba2 + _out_b, vel=76, gap=10),
}, ts=(6, 8), name='Ambient 1 swaying', key='F major',
     info="ambient theme 1: a relaxed 6/8 sway; a soft four-bar tune on the tuned drum over a bell glow; "
          "a lower middle phrase, a hushed section with the tune moved to the bells, a quiet settled close on F")

# ---- 10004: scurrying, A dorian, sixteenth patter on the tuned drum --------------------
# unit = sixteenth (60 ticks), bar = 16 units, 160 bpm, 32 bars = 48 s
_a1 = "A4 C5 E5 C5 A4 C5 E5 r D5 E5 D5 C5 A4:2 r:2 | "
_a1b = "A4 C5 E5 C5 A4 C5 E5 r D5 E5 F#5 E5 D5:2 r:2 | "
_a2 = "G4 B4 D5 B4 G4 B4 D5 r C5 D5 C5 B4 A4:2 r:2 | "
_a3 = "A4 C5 E5 C5 A4 C5 E5 G5 E5 D5 C5 D5 E5:2 r:2 | "
_a4 = "D5 C5 A4 G4 A4 C5 A4 G4 E4 G4 A4 C5 A4:2 r:2 | "
_a4b = "D5 C5 A4 G4 A4 C5 A4 G4 E4 G4 A4 B4 C5:2 r:2 | "
_A = _a1 + _a2 + _a3 + _a4
_A1 = _a1b + _a2 + _a3 + _a4b
_B = ("E5:2 D5 C5 E5:2 D5 C5 A4:2 C5 D5 E5:2 r:2 | D5:2 C5 B4 D5:2 C5 B4 G4:2 B4 C5 D5:2 r:2 | "
      "C5:2 B4 A4 C5:2 B4 A4 E4:2 A4 B4 C5:2 r:2 | A4 E4 A4 E4 C5 A4 C5 A4 E5 C5 E5 C5 A5:2 r:2 | ")
_C = ("v=60 A4:2 E4:2 A4:2 C5:2 E5:2 C5:2 A4:2 r:2 | G4:2 D4:2 G4:2 B4:2 D5:2 B4:2 G4:2 r:2 | "
      "A4:2 E4:2 A4:2 C5:2 E5:2 C5:2 A4:2 r:2 | D5:2 C5:2 A4:2 G4:2 A4:8 | v=78 ")
_in_t = "A3:4 E4:4 A3:4 E4:4 | A3:4 E4:4 C5:4 E5:4 | "
_out_t = "A4 C5 E5 C5 A4 C5 E5 r D5 C5 A4 G4 A4:2 r:2 | E4:2 A4:2 A3:12 | "
_k4 = "C2:2 r:6 C2:2 r:6 | "
_kb = "C2:2 r:2 C2:2. r:2 C2:2 r:2 C2:2. r:2 | "
_ks = "C2:2 r:14 | "
_tt = "r:2 G5:2 r:2 G5:2 r:2 G5:2 r:2 G5:2 | "
_tc = "r:4 G5:2. r:6 G5:2. r:2 | "
_sa = "S:1 S:1 r:6 S:1 S:1 r:6 | ".replace('S', 'C5')
_sb = "S:2 r:2 S:2 r:2 S:2 r:2 S:2 r:2 | ".replace('S', 'C5')
_sc = "r:8 C5:2 r:6 | "
song('10004', 160, 60, 16, {
    5: C(_k4 * 2 + _k4 * 8 + _kb * 4 + _k4 * 4 + _ks * 4 + _k4 * 4 + _kb * 4 + _k4 + _ks, vel=70, hold=64),
    7: C(_tt * 2 + _tt * 12 + _tt * 4 + _tc * 4 + _tt * 8 + _tt + "r:16 | ", vel=54, hold=64),
    8: C(_in_t + _A + _A1 + _B + _A + _C + _A1 + _B + _out_t, vel=78, gap=12),
    9: C(_sb * 2 + _sa * 8 + _sb * 4 + _sa * 4 + _sc * 4 + _sa * 4 + _sb * 4 + _sb + "r:16 | ", vel=42, hold=64),
}, name='Ambient 2 scurrying', key='A dorian',
     info="ambient theme 2: a quick scurrying patter of light sixteenths on the tuned drum with a tick/shaker/soft-kick "
          "bed; A-section cells (rising triads, small turns) twice varied, a syncopated B section twice, a hushed C section, "
          "a patter fade-out onto a low A")

# ---- 10005: brisk, curious, skipping; B-flat lydian; bell tune over a log-drum ostinato -
# unit = sixteenth, bar = 16 units, 144 bpm, 25 bars = 41.7 s
def _ost(root, fifth):
    return "%s:3 %s:1 r:4 %s:2 %s:2 r:4 | " % (root, fifth, root, fifth)


_m1 = "F5:3 G5:1 A5:2 r:2 D5:3 E5:1 F5:4 | "
_m2 = "G5:3 A5:1 Bb5:2 r:2 A5:3 G5:1 E5:4 | "
_m3 = "C6:3 A5:1 F5:2 r:2 A5:3 G5:1 F5:4 | "
_m4 = "D5:2 E5:2 F5:2 G5:2 A5:4 r:4 | "
_m4s = "D5:2 E5:2 F5:2 G5:2 Bb5:8 | "
_n = ("D6:3 Bb5:1 G5:2 r:2 Bb5:3 C6:1 D6:4 | A5:3 C6:1 A5:2 r:2 F5:3 G5:1 A5:4 | "
      "D6:3 Bb5:1 G5:2 r:2 Bb5:3 A5:1 G5:4 | E5:2 G5:2 C6:2 E6:2 D6:4 r:4 | ")
_p = ("v=62 F5:1 r:1 F5:1 r:1 G5:1 r:1 A5:1 r:1 Bb5:4 r:4 | A5:1 r:1 A5:1 r:1 G5:1 r:1 E5:1 r:1 C5:4 r:4 | "
      "F5:1 r:1 F5:1 r:1 G5:1 r:1 A5:1 r:1 Bb5:4 r:4 | D5:2 E5:2 F5:2 G5:2 A5:8 | v=78 ")
_cod = _m1 + _m2 + _m3 + "D6:2 C6:2 Bb5:2 A5:2 Bb5:8 | "
_ost_a = _ost('Bb3', 'F4') + _ost('C3', 'G3') + _ost('Bb3', 'F4') + _ost('F3', 'C4')
_ost_b = _ost('G3', 'D4') + _ost('F3', 'C4') + _ost('G3', 'D4') + _ost('C3', 'G3')
_ost_c = ("Bb3:2 r:6 F3:2 r:6 | C3:2 r:6 G3:2 r:6 | Bb3:2 r:6 F3:2 r:6 | F3:2 r:6 C4:2 r:6 | ")
_ost_cod = _ost('Bb3', 'F4') + _ost('C3', 'G3') + _ost('Bb3', 'F4') + "Bb3:4 F4:4 Bb3:8 | "
_kk = "C2:2 r:8 C2:2 r:4 | "
_cr = "r:4 E4:2 r:6 E4:2 r:2 | "
_sk = "r:6 S:2 r:6 S:2 | ".replace('S', 'C5')
song('10005', 144, 60, 16, {
    5: C(_kk + _kk * 16 + _ks * 4 + _kk * 3 + "C2:2 r:14 | ", vel=72, hold=64),
    6: C("r:16 | " + "r:16 | " * 4 + _cr * 8 + _cr * 4 + "r:16 | " * 4 + _cr * 4, vel=62, hold=64),
    8: C("Bb3:4 F4:4 Bb3:4 F4:4 | " + _ost_a + _ost_a + _ost_b + _ost_a + _ost_c + _ost_cod, vel=80, gap=12),
    9: C("r:16 | " + _sk * 16 + "r:16 | " * 4 + _sk * 4, vel=44, hold=64),
    10: C("r:12 F5:2 G5:2 | " + _m1 + _m2 + _m3 + _m4 + _m1 + _m2 + _m3 + _m4s + _n + _m1 + _m2 + _m3 + _m4
          + _p + _cod, vel=78, gap=10),
}, name='Ambient 3 skipping', key='B-flat lydian',
     info="ambient theme 3: brisk and curious, a skipping dotted rhythm; a bell tune with a lydian (raised fourth) twist "
          "over a pitched log-drum ostinato, soft kick, a light crack on 2 and 4 and a sparse shaker; contrasting minor-side "
          "B section, a pizzicato hushed section, a coda that ends on a held B-flat")

# =====================================================================================
# THE SHORT PIECES
# =====================================================================================

# ---- 11002: the yellow ant moves to another patch: four rising runs and a lift (D major) --
song('11002', 240, 60, 16, {
    1: C("A4:1 B4:1 C#5:1 D5:1 E5:1 F#5:1 A5:2 r:8 | B4:1 C#5:1 D5:1 E5:1 F#5:1 G5:1 B5:2 r:8 | "
         "D5:1 E5:1 F#5:1 G5:1 A5:1 B5:1 D6:2 r:8 | E5:1 F#5:1 G#5:1 A5:1 B5:1 C#6:1 E6:2 r:8 | "
         "F#5:2 A5:2 B5:2 D6:6 r:4 |", vel=115),
    2: C("D4+F#4+A4:16 | G4+B4+D5:16 | E4+G4+B4:16 | A4+C#5+E5:16 | D4+A4+D5:16 |", vel=105),
}, name='Moving on', key='D major',
     info="travelling flourish: four sixteenth runs, each starting a step higher over a changing chord, then a small lift "
          "(F#-A-B-D) onto a held D major")

# ---- 11003: the confirmation: eight quick rising notes (D pentatonic) -------------------
song('11003', 180, 60, None, {
    4: C("D4@108 E4@110 G4@112 A4@114 C5@116 D5@118 E5@120 G5:9@127", gap=14),
}, name='Go', key='D (major pentatonic with a flat seventh)',
     info="the 'go!' flourish: seven quick sixteenths climbing a pentatonic scale from D4 and a held top G5, plucked voice only")

# ---- 11004 (spare): ta-da -------------------------------------------------------------
song('11004', 240, 60, 16, {
    1: C("C4:1 E4:1 G4:1 C5:3 r:1 B4:1 C5:1 D5:1 E5:3 r:3 | G4:1 E4:1 C4:1 G4:1 E5:2 D5:2 C5:8 |", vel=118),
    3: C("C3:4 G2:4 C3:4 G2:4 | F2:4 G2:4 C3:8 |", vel=110),
    7: C("T:2 r:6 T:2 r:6 | T:2 r:6 T:2 r:6 |".replace('T', 'C6'), vel=78, hold=100),
    8: C("r:16 | C4:2 r:6 C3:8 |", vel=110, gap=10),
}, name='Ta-da', key='C major',
     info="spare cheerful ta-da: a rising pick-up arpeggio and a tumbling answer to a held C on the lead, an oom-pah bass, "
          "four ticks and two tuned drum strokes")

# ---- 11005: nobody to become: a drooping 'oh well' with a wobble (C major, sagging) --------
song('11005', 240, 60, None, {
    1: C("G5:3 E5:3 C5:6 r:2 | F5:3 D5:3 B4:6 r:2 | A4:2 Ab4:2 A4:2 Ab4:2 A4:2 Ab4:2 G4:24 |", vel=115),
    2: C("C4+E4+G4:14 | F3+A3+C4:14 | D3+F3+A3:12 C3+G3+E4:24 |", vel=105),
}, name='Oh well', key='C major',
     info="comic droop: two falling triad-skips (G-E-C, F-D-B: the B is the joke) then a wobble between A and A-flat before "
          "sagging onto a long G; soft chords C, F, Dm, C underneath")

# ---- 11006: exchange places: a spell of overlapping arpeggios on the chord voice (A lydian) -
_seq = ("A3 E4 C#4 F#4 E4 A4 F#4 B4 A4 C#5 B4 D#5 C#5 E5 D#5 F#5 "
        "E5 C#5 D#5 B4 C#5 A4 B4 F#4 A4 E4 F#4 C#4").split()
_lay = ['', '', '']
_final = ['A3', 'E4', 'A4']
for _i, _n_ in enumerate(_seq):
    _vel = 105 + _i if _i < 16 else max(106, 120 - 2 * (_i - 15))
    _dur = min(5, 56 - 2 * _i)
    _lay[_i % 3] += ">%d %s:%d@%d " % (2 * _i, _n_, _dur, _vel)
for _j in range(3):
    _lay[_j] += ">56 %s:8@110" % _final[_j]
song('11006', 180, 120, None, {2: C(_lay, gap=12)}, name='Exchange', key='A lydian',
     info="a spell: slow eighth-note arpeggios whose long notes overlap into a shimmer, rising for four bars through A lydian "
          "(the raised fourth D# gives the magic) and sinking back, settling on a calm A major chord")

# ---- 11007 (spare): ominous sting -----------------------------------------------------
song('11007', 181, 120, None, {
    1: C("Bb3:1 A3:2 r:1 G3:1 F#3:2 r:1 Eb3:2 D3:6", vel=118),
}, name='Sting', key='D (Bb-A, G-F#, Eb-D)',
     info="spare ominous sting: three falling pairs of notes (Bb-A, G-F#, Eb-D), each a half step or step lower, "
          "the last one dropping onto a long low D")

# ---- 11013: recruit: a rising call on the chord voice (C major), also +6 and +12 --------
song('11013', 180, 120, None, {
    2: C("C4+E4+G4:1 r:1 E4+G4+C5:1 r:1 G4+C5+E5:1 r:1 A4+D5+F5:2 C5+E5+G5:8!", vel=110),
}, name='Recruit', key='C major (works at +6 and +12)',
     info="call to arms 'come on, everybody': three short chord stabs climbing in inversions, a D-minor lean, then a bright held C "
          "major chord; top key G5 so it survives +12")

# ---- 11016: release: a relaxed falling phrase (C major pentatonic), also +12 -------------
song('11016', 120, 120, None, {
    1: C("G5:3 E5:1 D5:2 C5:2 | A4:2 B4:1 A4:1 G4:4 |", vel=115),
}, name='Dismissed', key='C major',
     info="'dismissed, off you go': a lazy falling line from G5 with one small upturn (A-B-A) and a settled G4; top key G5")

# ---- 11018: attack alarm: two alternating pitches, three times (tritone, E5-Bb4) ---------
song('11018', 240, 120, None, {
    2: C("E5:2! Bb4:2 r:7 E5:2! Bb4:2 r:7 E5:2! Bb4:8", vel=117),
}, name='Alarm', key='E / B-flat (tritone pair)',
     info="alarm: a sharp two-note figure E-Bb, three times, the last one left ringing; plain unison, no harmony")

# ---- 11020: the player's queen: regal, rises and settles (E-flat major) ------------------
song('11020', 96, 120, None, {
    1: C("Bb4:2 Eb5:2 G5:4 F5:2 Eb5:1 D5:1 Eb5:4", vel=118),
    2: C("Eb4+Bb4:8 Bb3+D4+F4:4 Eb4+G4+Bb4:4", vel=105),
}, name='Black queen', key='E-flat major',
     info="dignified: a rising broken Eb arpeggio (Bb-Eb-G), a stately turn and a settled Eb, under slow plain chords I, V, I")

# ---- 11021: the rival queen: a creeping chromatic line over a drone (A harmonic minor) ---
song('11021', 181, 120, 8, {
    2: C(["v=105 A4 B4 C5 B4 A4 G#4 A4 E4 | F4 E4 D4 E4 F4 E4 D#4 E4 | A4 C5 B4 A4 G#4 A4 B4 G#4 | "
          "A4 B4 C5 D5 C5 B4 A4 G#4 | F4 A4 G#4 F4 E4 F4 G#4 E4 | D4 F4 E4 D4 C4 D4 E4 C4 | "
          "B3 D4 C4 B3 A3 B3 C4 G#3 | A4 G#4 A4 E4 A4:4 |",
          "v=110 A2:8 | F2:8 | E2:8 | A2:8 | D3:8 | D3:8 | E2:8 | A2:8 |"], gap=14),
}, name='Red queen', key='A harmonic minor',
     info="sly creeping: an eight-bar winding line of slow-stepping eighths that sidle chromatically (G#, D#) through A minor, "
          "with a low drone changing only once a bar; ends back on A")

# ---- 20000: queen scene sting (C major) -----------------------------------------------
song('20000', 220, 60, None, {
    1: C("G4:1 C5:1 E5:1 G5:1 C6:6 r:2 E5:2 G5:2 C6:16", vel=118),
    2: C("r:4 C4+G4+E5:28", vel=105),
}, name='Queen joy', key='C major',
     info="burst of delight: a four-note upward spring to a high C, a quick echo (E-G-C) and a long C chord")

# ---- 20001: a nest founded (A major) --------------------------------------------------
song('20001', 221, 60, None, {
    1: C("A4:2 C#5:2 E5:2 F#5:2 D5:2 E5:2 F#5:2 A5:2 G5:2 A5:2 B5:4 A5:8", vel=118),
}, name='Nest founded', key='A major',
     info="satisfied upward phrase: two rising steps up a sixth chord (A-C#-E-F#, D-E-F#-A) then G-A-B and home on A")

# ---- 20002: the reds are gone (G major) -----------------------------------------------
song('20002', 120, 60, 16, {
    1: C("D5:2 G5:2 B5:2 G5:1 A5:1 B5:2 D6:2 r:2 B5:1 A5:1 | G5:2 E5:2 C6:2 B5:1 A5:1 G5:2 E5:2 G5:2 A5:1 B5:1 | "
         "C6:2 B5:1 A5:1 B5:2 G5:2 A5:2 F#5:2 D5:2 r:2 | B5:2 A5:2 B5:2 D6:2 G5:8 |", vel=118),
    2: C("G3+B3+D4:16 | C4+E4+G4:16 | D4+F#4+A4:16 | G3+D4+G4:16 |", vel=105),
    3: C("G2:8 D3:8 | C3:8 G2:8 | D3:8 A2:8 | G2:16 |", vel=108),
}, name='Reds gone', key='G major',
     info="relieved and lively: bouncy syncopated lead over I, IV, V, I with a walking bass; ends with a full G close "
          "(a deliberate last bar of held G chord and G bass)")

# ---- 20003 + 20004: the human arrives (C minor, ends on a dominant) / the jolly resolution -
song('20003', 120, 60, 16, {
    1: C("v=112 C4:2 r:2 C#4:2 r:2 D4:2 r:2 D#4:2 r:2 | G5:2! Eb5:6 r:2 F#5:2! D5:4 | "
         "D5:1 r:1 D5:1 r:1 D5:1 r:1 D5:1! r:1 Eb5:1 r:1 Eb5:1 r:1 E5:1! r:1 E5:1! r:1 | G5:8", gap=12),
    2: C("C3+Eb3+G3:4 r:4 C3+Eb3+G3:4 r:4 | F3+Ab3+C4:8 G3+B3+D4:8 | D3+F3+Ab3:16 | G3+B3+F4:8", vel=105),
}, name='Human moves in', key='C minor, ending unresolved on G7',
     info="wry 'uh-oh': a staccato chromatic creep (C-C#-D-D#) over minor stabs, a falling two-note gasp twice, pulsing repeated "
          "notes tightening by half steps, then a held G with a G7 chord left hanging for 20004")
song('20004', 120, 60, 16, {
    1: C("E5:2 G5:2 C6:4 G5:2 E5:2 G5:4 | F5:2 E5:2 D5:2 B4:2 C5:8 |", vel=118),
    2: C("C4+E4+G4:16 | G3+B3+D4:8 C4+E4+G4:8 |", vel=105),
}, name='The end', key='C major',
     info="the jolly 'the end': picks up on the C that 20003 withheld; a bouncing C arpeggio, a stepwise cadence "
          "(F-E-D-B-C) over V to I; heard right after 20003 (20003 ends on G, 20004 answers in C)")

# ---- 20005: the Full Game won: grand fanfare (E-flat major), ritardando on the last chord --
song('20005', [(0, 120), (56, 90)], 60, 16, {
    1: C("Eb5:3 r:1 Eb5:1 r:1 Bb4:2 Eb5:2 G5:2 Bb5:4 | Ab5:3 G5:1 F5:2 G5:2 Bb5:6 r:2 | "
         "C6:3 Bb5:1 Ab5:2 G5:2 Eb6:3 D6:1 C6:2 Bb5:2 | Bb5:2 G5:2 Eb5:2 Bb5:2 Eb6:8 |", vel=120),
    2: C("Eb4+G4+Bb4:12 r:4 | Ab3+C4+Eb4:12 r:4 | C4+Eb4+G4:12 r:4 | Bb3+D4+F4:8 Eb4+G4+Bb4:8 |", vel=108),
    3: C("Eb3:8 Bb2:8 | Ab2:8 Bb2:8 | C3:8 Ab2:8 | Bb2:8 Eb3:8 |", vel=110),
    5: C("C2:1 r:7 C2:1 r:7 | C2:1 r:7 C2:1 r:7 | C2:1 r:7 C2:1 r:7 | C2:1 r:15 |", vel=120, hold=64),
    10: C("r:56 Eb5:8", vel=105),
}, name='Final fanfare', key='E-flat major',
     info="grand finale: a heroic E-flat theme (repeated-note motif, a leap to Bb, a sequence climbing to a high Eb) over I-IV-vi-V-I "
          "with kick and bass, and a slower final chord with bell (tempo 120 then 90 for the last eight sixteenths)")

# ---- 20007: sad piece 1: a slow drooping lament, chords and pluck (D minor) --------------
song('20007', [(0, 90), (18, 80)], 120, 6, {
    2: C("D3+F3+A3:6 | Bb2+D3+F3:6 | G3+Bb3+D4:6 | D3+F3+A3:6 |", vel=105),
    4: C("A5:2 G5:1 F5:1 E5:2 | F5:3 E5:1 D5:2 | D5:2 C5:1 Bb4:1 G4:2 | F4:2 E4:1 D4:3 |", vel=112),
}, name='Lament one', key='D minor',
     info="slow drooping lament: each four-bar phrase of the pluck sags by a step or two (A-G-F-E, F-E-D, D-C-Bb-G, F-E-D) "
          "over i, VI, iv, i chords; a small ritardando at the end")

# ---- 20008: sad piece 2: a tired trudging march (G minor) -------------------------------
song('20008', [(0, 120), (24, 100)], 120, 8, {
    1: C("D5:3 r:1 D5:2 C5:2 | Bb4:3 r:1 Bb4:2 A4:2 | G4:3 r:1 A4:2 Bb4:2 | A4:3 r:1 G4:4 |", vel=115),
    4: C("G3:2 r:2 D4:2 r:2 | Eb3:2 r:2 Bb3:2 r:2 | C3:2 r:2 G3:2 r:2 | D3:2 r:2 G3:4 |", vel=110),
}, name='Lament two', key='G minor',
     info="tired trudge: a long-short plodding lead step by step down D-C-Bb-A and back to G, a pluck plodding on beats 1 and 3 "
          "with falling bass roots G, Eb, C, D, G; slows slightly in the last bar")

# ---- 20009: sad piece 3: a fluttering trembling little descent, pluck only (G5 down to C5) -
song('20009', 128, 60, 4, {
    4: C("G5! F#5 G5 F#5 | F#5! F5 F#5 F5 | F5! E5 F5 E5 | E5! Eb5 E5 Eb5 | Eb5! D5 Eb5 D5 | D5! C#5 D5 C#5 | "
         "C#5! C5 C#5 C5 | C#5! C5 C#5 C5:2", vel=108, gap=12),
}, name='Lament three', key='chromatic, G5 to C5',
     info="trembling descent: thirty-two sixteenths in a shiver between two neighbouring semitones, each pair a half step lower, "
          "from G5 down to C5 (seven semitones); the last note is held")

# ---- 20010: sad piece 4: a short sighing phrase (E minor) -------------------------------
song('20010', 112, 120, None, {
    1: C("G5:4 F#5:2 E5:2 D5:3 C5:1 B4:4", vel=115),
    2: C("A3+C4+E4:8 E3+G3+B3:8", vel=105),
}, name='Lament four', key='E minor',
     info="a sigh: a long G falling stepwise (G-F#-E over Am) then D-C-B over Em with the C as the 'sigh' semitone, settling on B")

# ---- 20011: sad piece 5: a short low dirge (F minor) ----------------------------------------
song('20011', 60, 60, None, {
    2: C("F2+C3+Ab3:17", vel=105),
    4: C("F3:4 F3:4 C3:9", vel=118, gap=14),
}, name='Lament five', key='F minor',
     info="low dirge: slow tolling F, F, C on the pluck (the C a fifth below) over one held F minor chord; four and a quarter beats at 60 bpm")


# =====================================================================================
def main():
    table = []
    readme = ["# Batch B: ambient themes and short pieces (provenance of independent composition)", "",
              "Written from docs/clean_pack/music.md alone, by `make_music_b.py` (notes are in that script as note-name "
              "strings). One line per song: what it is, key, shape / motif idea, tempo.", ""]
    for s in SONGS:
        data = s.build()
        with open(os.path.join(HERE, s.sid + '.mid'), 'wb') as f:
            f.write(data)
        bpm = ('%d bpm' % s.tempi[0][1]) if len(s.tempi) == 1 else (
            '%d bpm, then %s' % (s.tempi[0][1], ', '.join('%d bpm from unit %d' % (b, p) for p, b in s.tempi[1:])))
        readme.append("- **%s** (%s): %s. Key: %s. Tempo: %s (grid unit %d ticks; ~%.1f s)." %
                      (s.sid, s.name, s.info, s.key, bpm, s.unit, s.seconds))
        table.append((s.sid, s.seconds, s.n_notes, s.maxpoly, s.first, s.tail, len(data)))
    with open(os.path.join(HERE, 'README_b.md'), 'w', newline='\n') as f:
        f.write('\n'.join(readme) + '\n')
    print('%-6s %8s %6s %5s %6s %6s %6s' % ('song', 'sec', 'notes', 'poly', 'first', 'tail', 'bytes'))
    for r in table:
        print('%-6s %8.2f %6d %5d %6.2f %6.2f %6d' % r)


if __name__ == '__main__':
    main()
