#!/usr/bin/env python3
"""make_music_a.py - batch A of the clean music pack: songs 10001, 10006, 10007, 10008, 10010.

Original compositions (see README_a.md). Deterministic: the notes below are the only input; running
the script rewrites the five .mid files next to it.

Notation of the melodic lines (a string per channel, bars separated by '|'):
    NAME:DUR     a note; NAME is e.g. C5 F#4 Bb3 (C4 = key 60, the written key of the spec);
                 DUR is in sixteenth notes; a token without ':DUR' repeats the previous duration.
    r:DUR        a rest.
    A4+C5+E5:4   several notes at once (a chord on the chord channel).
    flags after the duration: s = staccato (half length), l = legato (full length),
                              ^ = accent, ',' = soft.
  Every bar must add up to 16 sixteenths (4/4); the script stops with a message otherwise.
Harmony: a chord string with one symbol per bar (F  Bb  Dm  C7  Gm7), 'Gm/C' = two chords in one bar.
Bass and chord-stab channels are generated from the chord string with the templates below.
Drum patterns: 16 characters per bar, one per sixteenth: x = hit, X = accent, o = ghost, . = none.
"""
import math
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
PPQ = 240
U = 60            # ticks in a sixteenth note
BAR = 16          # sixteenths in a bar (everything here is in 4/4)

PCS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
ACC = {'': 0, '#': 1, 'b': -1}


def nkey(name):
    m = re.fullmatch(r'([A-G])([#b]?)(-?\d)', name)
    if not m:
        raise ValueError('bad note name ' + name)
    return 12 * (int(m.group(3)) + 1) + PCS[m.group(1)] + ACC[m.group(2)]


# ---------------------------------------------------------------------------------------------
# the orchestra (spec section 2): default velocities and note gates per channel
LINE_VEL = {1: 100, 2: 74, 3: 96, 4: 85, 8: 92, 10: 80}
GATE = {1: 0.90, 2: 0.88, 3: 0.82, 4: 0.80, 8: 0.62, 10: 0.85}
DRUM_KEY = {5: 36, 6: 60, 7: 80, 8: 48, 9: 72, 10: 84}
DRUM_VEL = {5: 110, 6: 100, 7: 60, 8: 95, 9: 45, 10: 80}
NAMES = {1: 'lead', 2: 'chords', 3: 'bass', 4: 'pluck', 5: 'kick', 6: 'crack', 7: 'tick',
         8: 'tuned drum', 9: 'shaker', 10: 'bell'}
# when more than 6 notes would sound, the lowest priority is dropped first
PRIO = {1: 10, 3: 9, 4: 8, 2: 7, 5: 6, 6: 5, 8: 4, 10: 3, 7: 2, 9: 1}

# chord qualities: intervals above the root
QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'm7': (0, 3, 7, 10)}

# bass templates (tokens DEGREE:DUR over one bar; the chord is the one sounding at the token)
#   R root, 3 third, 5 fifth, 7 seventh, 8 octave, 6 sixth, F fifth below the root, '-' rest
BASS_STYLES = {
    'walk':   'R:4 3:4 5:4 3:4',
    'bounce': 'R:3 8:1 5:3 8:1 R:3 8:1 3:2 5:2',
    'oom':    'R:2 -:2 5:2 -:2 R:2 -:2 5:2 -:2',
    'pedal':  'R:8 5:8',
    'long':   'R:16',
    'march':  'R:4 5:4 R:4 5:4',
    'drive':  'R:2 R:2 8:2 R:2 R:2 R:2 8:2 R:2',
    'hop':    'R:4 -:2 5:2 R:4 -:2 5:2',
}
DEG = {'R': lambda q: 0, '3': lambda q: q[1], '5': lambda q: 7, '7': lambda q: 10,
       '8': lambda q: 12, '6': lambda q: 9, 'F': lambda q: -5}

TOKEN = re.compile(r'^(?P<n>[r-]|[A-G][#b]?-?\d(?:\+[A-G][#b]?-?\d)*)'
                   r'(?::(?P<d>\d+(?:\.\d+)?))?(?P<f>[sl^,]*)$')


def parse_chord(sym, shift=0):
    m = re.fullmatch(r'([A-G])([#b]?)(m7|m|7|)', sym)
    if not m:
        raise ValueError('bad chord ' + sym)
    pc = (PCS[m.group(1)] + ACC[m.group(2)] + shift) % 12
    return pc, QUAL[m.group(3)]


def parse_chords(text, bars, shift):
    """One symbol per bar ('Gm/C' = two halves); returns a list with one chord per half bar."""
    toks = text.replace('|', ' ').split()
    if len(toks) != bars:
        raise ValueError('chord string has %d bars, section %d: %s' % (len(toks), bars, text))
    halves = []
    for t in toks:
        a, _, b = t.partition('/')
        halves.append(parse_chord(a, shift))
        halves.append(parse_chord(b or a, shift))
    return halves


def bass_key(pc):
    return 28 + ((pc - 28) % 12)          # root between E1 (28) and D#2 (39)


def nearest(pc, center):
    k0 = center - ((center - pc) % 12)
    return k0 if center - k0 <= k0 + 12 - center else k0 + 12


def voice(pc, q, n, center):
    tones = [(pc + i) % 12 for i in q]
    if n == 2:
        sel = [tones[1], tones[3]] if len(q) == 4 else [tones[1], tones[2]]
    else:
        sel = tones[1:4] if len(q) == 4 else tones[:3]
    return sorted({nearest(t, center) for t in sel})


def D(p, vel=None, ln=None, key=None, ramp=None):
    """A drum spec: p = pattern string or list of bar patterns (cycled)."""
    return dict(p=p, vel=vel, ln=ln, key=key, ramp=ramp)


class Song:
    def __init__(self, sid, bpm, drum_ms=105, prio=None):
        self.sid = sid
        self.tempo = [(0, bpm)]
        self.notes = []                   # (ch, start, end, key, vel)
        self.cursor = 0                   # in sixteenths
        self.drum_ln = int(math.ceil(drum_ms / 1000.0 / (60.0 / bpm / PPQ)))
        self.prio = dict(PRIO)
        if prio:
            self.prio.update(prio)
        self.dropped = 0

    def add(self, ch, start, end, key, vel):
        if not 0 <= key <= 95:
            raise ValueError('key %d out of range on channel %d at tick %d' % (key, ch, start))
        self.notes.append((ch, int(start), int(end), key, max(2, min(127, int(vel)))))

    # --- explicit lines ---------------------------------------------------------------------
    def line(self, ch, text, u0, bars, shift, vel):
        bar_texts = [b.strip() for b in text.strip().split('|')]
        if len(bar_texts) > bars:
            raise ValueError('channel %d: %d bars given, section has %d' % (ch, len(bar_texts), bars))
        prev = None
        for bi, bt in enumerate(bar_texts):
            pos = 0.0
            for tok in bt.split():
                m = TOKEN.match(tok)
                if not m:
                    raise ValueError('channel %d bar %d: bad token %r' % (ch, bi + 1, tok))
                d = float(m.group('d')) if m.group('d') else prev
                if d is None:
                    raise ValueError('channel %d bar %d: no duration for %r' % (ch, bi + 1, tok))
                prev = d
                flags = m.group('f')
                if m.group('n') not in ('r', '-'):
                    start = (u0 + bi * BAR + pos) * U
                    g = 0.5 if 's' in flags else (1.0 if 'l' in flags else GATE.get(ch, 0.85))
                    end = start + max(1, int(round(d * U * g)))
                    v = vel + (10 if '^' in flags else 0) - (14 if ',' in flags else 0)
                    for nm in m.group('n').split('+'):
                        self.add(ch, start, end, nkey(nm) + shift, v)
                pos += d
            if abs(pos - BAR) > 1e-9:
                raise ValueError('channel %d bar %d adds up to %g sixteenths, not 16: %s' % (ch, bi + 1, pos, bt))

    # --- generated parts --------------------------------------------------------------------
    def bass(self, ch, style, halves, u0, bars, off, vel):
        toks = BASS_STYLES.get(style, style).split()
        for b in range(bars):
            pos = 0
            for tok in toks:
                deg, _, d = tok.partition(':')
                d = int(d)
                if deg not in ('-', 'r'):
                    pc, q = halves[(b * BAR + pos) // 8]
                    k = bass_key(pc) + DEG[deg](q) + off
                    start = (u0 + b * BAR + pos) * U
                    self.add(ch, start, start + int(d * U * GATE[ch]), k, vel)
                pos += d
            if pos != BAR:
                raise ValueError('bass template %r does not fill a bar' % style)

    def comp(self, halves, u0, bars, spec):
        plist = [spec['p']] if isinstance(spec['p'], str) else spec['p']
        n, center, ln, vel = spec.get('n', 2), spec.get('center', 57), spec.get('ln', 2), spec.get('vel', 72)
        for b in range(bars):
            pat = plist[b % len(plist)]
            if len(pat) != BAR:
                raise ValueError('comp pattern %r is not 16 long' % pat)
            for i, c in enumerate(pat):
                if c in 'xXo':
                    pc, q = halves[(b * BAR + i) // 8]
                    v = vel + (10 if c == 'X' else -14 if c == 'o' else 0)
                    start = (u0 + b * BAR + i) * U
                    for k in voice(pc, q, n, center):
                        self.add(2, start, start + int(ln * U * GATE[2]), k, v)

    def drums(self, ch, spec, u0, bars):
        if not isinstance(spec, dict):
            spec = D(spec)
        plist = [spec['p']] if isinstance(spec['p'], str) else spec['p']
        base = spec['vel'] if spec['vel'] is not None else DRUM_VEL[ch]
        ln = spec['ln'] or self.drum_ln
        key = spec['key'] if spec['key'] is not None else DRUM_KEY[ch]
        for b in range(bars):
            pat = plist[b % len(plist)]
            if len(pat) != BAR:
                raise ValueError('drum pattern %r is not 16 long' % pat)
            for i, c in enumerate(pat):
                if c in 'xXo':
                    v = base
                    if spec['ramp']:
                        v = spec['ramp'][0] + (spec['ramp'][1] - spec['ramp'][0]) * (b * BAR + i) / float(bars * BAR)
                    v += 12 if c == 'X' else -18 if c == 'o' else 0
                    start = (u0 + b * BAR + i) * U
                    self.add(ch, start, start + ln, key, v)

    def section(self, bars, chords=None, lines=None, vels=None, bass=None, bass_ch=3, bass_off=0,
                bass_vel=None, comp=None, drums=None, shift=0, tempo=None):
        u0 = self.cursor
        halves = parse_chords(chords, bars, shift) if chords else None
        for off_bar, bpm in (tempo or []):
            self.tempo.append((int((u0 + off_bar * BAR) * U), bpm))
        for ch, text in (lines or {}).items():
            v = (vels or {}).get(ch, LINE_VEL[ch])
            self.line(ch, text, u0, bars, shift, v)
        if bass:
            self.bass(bass_ch, bass, halves, u0, bars, bass_off, bass_vel or LINE_VEL[bass_ch])
        if comp:
            self.comp(halves, u0, bars, comp)
        for ch, spec in (drums or {}).items():
            self.drums(ch, spec, u0, bars)
        self.cursor += bars * BAR

    # --- finishing --------------------------------------------------------------------------
    def govern(self, limit=6):
        """Keep at most `limit` notes sounding: drop the lowest priority note when a tick overflows."""
        notes = sorted(self.notes, key=lambda n: (n[1], -self.prio[n[0]], n[3]))
        active, dropped = [], set()
        for idx, n in enumerate(notes):
            active = [a for a in active if notes[a][2] > n[1]]
            cand = active + [idx]
            while len(cand) > limit:
                victim = min(cand, key=lambda i: (self.prio[notes[i][0]], -notes[i][1]))
                cand.remove(victim)
                dropped.add(victim)
            active = cand
        self.dropped = len(dropped)
        self.notes = [n for i, n in enumerate(notes) if i not in dropped]

    def tidy(self):
        """Single-voice channels never overlap: cut a note at the start of the next one."""
        by = {}
        for n in self.notes:
            by.setdefault(n[0], []).append(n)
        out = []
        for ch, lst in by.items():
            lst.sort(key=lambda n: (n[1], n[3]))
            if ch in (2, 4):
                for i, n in enumerate(lst):          # same key must not overlap
                    for m in lst[i + 1:]:
                        if m[3] == n[3] and m[1] < n[2]:
                            raise ValueError('same key overlaps on channel %d at tick %d' % (ch, m[1]))
                out.extend(lst)
                continue
            for i, n in enumerate(lst):
                end = n[2]
                if i + 1 < len(lst) and lst[i + 1][1] < end:
                    end = lst[i + 1][1]
                    if ch in (5, 6, 7, 9):          # fast drum rolls: stop just before the next hit
                        end -= 2
                out.append((ch, n[1], end, n[3], n[4]))
        self.notes = sorted(out, key=lambda n: (n[1], n[0], n[3]))

    def final_tick(self):
        return max(n[2] for n in self.notes) + 24

    def tempo_map(self):
        tm = {}
        for t, bpm in self.tempo:
            tm[t] = bpm
        return sorted(tm.items())

    def plain_length(self):
        tm = self.tempo_map()
        end = self.final_tick()
        total = 0.0
        for i, (t, bpm) in enumerate(tm):
            nxt = tm[i + 1][0] if i + 1 < len(tm) else end
            total += (min(nxt, end) - t) * (60.0 / bpm / PPQ)
        return total

    def sim_length(self):
        """The game's clock: waits in whole 1/348.47 s steps, rounded down per gap."""
        times = {0, self.final_tick()}
        for n in self.notes:
            times.add(n[1]); times.add(n[2])
        tm = dict(self.tempo_map())
        times.update(tm)
        cur_tempo = 500000
        total, last = 0, 0
        for t in sorted(times):
            if t in tm:
                cur_tempo = int(round(60e6 / tm[t]))
            scale = int(int(int(cur_tempo / 1000) * 0x4AA / PPQ) / 13)
            nxt = [x for x in times if x > t]
            if not nxt:
                break
            total += (((min(nxt) - t) * scale) >> 8) & 0xFFFF
        return total / 348.47

    def max_poly(self):
        ev = []
        for n in self.notes:
            ev.append((n[1], 1)); ev.append((n[2], -1))
        ev.sort()
        cur = best = 0
        i = 0
        while i < len(ev):
            t = ev[i][0]
            while i < len(ev) and ev[i][0] == t:
                cur += ev[i][1]; i += 1
            best = max(best, cur)
        return best

    # --- MIDI -------------------------------------------------------------------------------
    def to_midi(self, title):
        end = self.final_tick()
        tracks = []
        # build the conductor with explicit absolute ticks
        events = [(0, meta(0x03, title.encode('ascii'))), (0, meta(0x58, bytes([4, 2, 24, 8])))]
        for t, bpm in self.tempo_map():
            events.append((t, meta(0x51, int(round(60e6 / bpm)).to_bytes(3, 'big'))))
        events.sort(key=lambda e: (e[0], 0 if e[1][1:2] == b'\x03' else 1 if e[1][1:2] == b'\x51' else 2))
        tracks.append(chunk_events(events, end))
        for ch in sorted({n[0] for n in self.notes}):
            ev = [(0, meta(0x03, NAMES[ch].encode('ascii')))]
            for (_, s, e, k, v) in [n for n in self.notes if n[0] == ch]:
                ev.append((s, bytes([0x90 | ch, k, v]), 1))
                ev.append((e, bytes([0x80 | ch, k, 0x40]), 0))
            ev.sort(key=lambda e: (e[0], e[2] if len(e) > 2 else -1, e[1][1] if len(e[1]) > 1 else 0))
            tracks.append(chunk_events([(e[0], e[1]) for e in ev], end))
        head = b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), PPQ)
        return head + b''.join(tracks)


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def meta(kind, data):
    return bytes([0xFF, kind]) + vlq(len(data)) + data


def chunk_events(events, end):
    data = bytearray()
    t = 0
    for ev in events:
        data += vlq(ev[0] - t) + ev[1]
        t = ev[0]
    data += vlq(end - t) + meta(0x2F, b'')
    return b'MTrk' + struct.pack('>I', len(data)) + bytes(data)


# =============================================================================================
# 10001 - the main theme.  F major, 160 bpm, 68 bars (about 103 s)
#   intro 4 | A 16 | B (C major) 16 | calm middle (Bb) 8 | build 4 | A again, a tone higher, bigger 16 | finish 4
# =============================================================================================
A_CHORDS = 'F F Bb C  F Dm C F  Bb C Dm C  F F Gm/C F'
A_LEAD = '''
C5:2 A4 C5 F5:6 C5:2 A4 | G5:2 F5 E5 F5:6 r:4 | D5:2 Bb4 D5 G5:6 D5:2 Bb4 | A5:2 G5 E5 G5:6 C5:2 E5 |
C5:2 A4 C5 F5:6 C5:2 A4 | A5:2 G5 F5 D5:6 F5:2 A5 | G5:4 F5:2 E5 D5:2 E5 F5 G5 | A4:2 C5 F5 A5 F5:6 r:2 |
Bb4:3 D5 F5:2 D5:3 F5 G5:2 | E5:3 G5 A5:2 G5:3 E5 C5:2 | D5:3 F5 A5:2 G5:4 F5:2 E5 | C5:2 D5 E5 F5 G5:4 E5:2 G5 |
C5:2 A4 C5 F5:6 C5:2 A4 | G5:2 F5 E5 F5:6 r:4 | D5:2 Bb4 D5 G5 E5 G5 C5 E5 | A5:2 F5 C5 A4 F5:8
'''
A_BARS = [b.strip() for b in A_LEAD.strip().split('|')]
assert len(A_BARS) == 16

B_CHORDS = 'C Am Dm G  C Am F G  F G Em Am  Dm G7 C C'
B_LEAD = '''
r:2 G4:2 C5 E5 G5:4 E5:2 C5 | A4:2 C5 E5 A5:4 G5:2 E5 C5 | D5:2 F5 A5:4 G5:2 F5 E5 D5 | G5:4 F5:2 D5 B4:4 r:2 D5 |
r:2 G4:2 C5 E5 G5 A5 G5 E5 | A5:2 G5 E5 C5 A4:4 C5:2 E5 | A5:3 F5 C5:2 A4:3 C5 F5:2 | D5:2 E5 F5 G5 A5:4 B5:4 |
A5:6 G5:2 F5:6 E5:2 | D5:6 E5:2 F5:6 G5:2 | G5:6 F5:2 E5:6 D5:2 | C5:6 D5:2 E5:4 A4:4 |
F5:6 E5:2 D5:6 C5:2 | B4:6 C5:2 D5:4 F5:4 | E5:2 G5 C6:4 G5:4 E5:4 | C5:2 E5 G5 E5 C5:8
'''

MID_CHORDS = 'Bb Gm Eb F  Bb Dm Eb F'
MID_TUNED = '''
D5:4 F5 Bb4 D5 | G4:4 Bb4 D5:6 r:2 | r:16 | r:16 |
Bb4:2 D5 F5 D5 Bb4 D5 F5 D5 | A4:2 D5 F5 D5 A4 D5 F5 A5 | G4:4 Bb4 Eb5:8 | C5:4 A4 F4:6 r:2
'''
MID_BELL = '''
r:16 | r:16 | Bb5:4 G5 Eb5 G5 | A5:4 C6 F5:8 |
r:8 F5:4 D5 | r:8 A5:4 F5 | Bb5:4 G5 Eb5:8 | A5:4 C6 F5:8
'''

BUILD_CHORDS = 'Eb F A7 D7'
BUILD_LEAD = '''
Bb4:2 Eb5 G5 Eb5 Bb4 Eb5 G5 Bb5 | C5:2 F5 A5 F5 C5 F5 A5 C6 |
E5:2 G5 A5 G5 E5 G5 A5 C#6 | F#5:2 A5 C6 A5 r:8
'''

FIN_LEAD3 = '''
C5:2 E5 G5 C6 B5 A5 G5 E5 | F#5:1 A5 C6 A5 F#5 A5 C6 A5 D6:4 r:4 |
D5:2 G5 B5:4 G5:8
'''


def song_10001():
    s = Song(10001, 160, prio={})
    # intro: announces the hook (C A C F)
    s.section(4, chords='F F Bb C', bass='pedal',
              lines={1: '''r:4 C5:2 A4 C5 F5:6 | G5:2 F5 E5 F5:6 r:4 | D5:4 F5 D5 G5 | G4:2 A4 C5 E5 G5:4 r:2 G4''',
                     8: 'r:16 | r:16 | r:16 | r:8 E5:2 D5 B4 G4'},
              comp=dict(p='x.......x.......', n=2, ln=7, vel=58),
              drums={5: ['x.......x.......', 'x.......x.......', 'x...x...x...x...', 'x...x...x...x...'],
                     6: D(['................', '................', '....x.......x...', '..x.x.x.x.x.x.x.'], ramp=(70, 105)),
                     9: ['................', '................', '..x...x...x...x.', '..x...x...x...x.']})
    # A: the tune, twice through its 16 bars
    s.section(16, chords=A_CHORDS, lines={1: A_LEAD}, bass='walk',
              comp=dict(p='..x...x...x...x.', n=2, ln=2, vel=66),
              drums={5: ['x.......x.......'] * 7 + ['x.......x...x.x.'] + ['x.......x.......'] * 7 + ['x...x...x.x.x.x.'],
                     6: ['....x.......x...'] * 7 + ['....x.....x.x.x.'] + ['....x.......x...'] * 7 + ['....x.....x.xxxx'],
                     7: '..x...x...x...x.',
                     9: ['................'] * 8 + ['x...x...x...x...'] * 8})
    # B: the second tune, in C major
    s.section(16, chords=B_CHORDS, lines={1: B_LEAD}, bass='oom',
              comp=dict(p='x...x...x...x...', n=2, ln=3, vel=64),
              drums={5: ['x.......x.x.....'] * 7 + ['x.......x.x.x.x.'] + ['x.......x.x.....'] * 7 + ['x...x...x...x...'],
                     6: ['....x.......x...'] * 15 + ['....x...x.x.x.xx'],
                     7: '..x...x...x...x.',
                     9: ['x.x.x.x.x.x.x.x.'] * 8 + ['................'] * 8})
    # calm middle: tuned drum and bell, fewer voices
    s.section(8, chords=MID_CHORDS, lines={8: MID_TUNED, 10: MID_BELL}, vels={8: 86, 10: 74},
              bass='long', bass_vel=80,
              comp=dict(p='x.......x.......', n=2, ln=7, vel=54),
              drums={5: D('x...............', vel=84), 9: D('..x...x...x...x.', vel=36)})
    # build: the lead climbs, the snare rolls
    s.section(4, chords=BUILD_CHORDS, lines={1: BUILD_LEAD, 8: 'r:16 | r:16 | r:16 | r:8 E5:2 D5 B4 G4'},
              bass='drive', comp=dict(p='x.x.x.x.x.x.x.x.', n=2, ln=2, vel=66),
              drums={5: ['x...x...x...x...'] * 3 + ['x...x...x...x...'],
                     6: D(['....x.......x...', '..x.x.x.x.x.x.x.', 'xxxxxxxxxxxxxxxx', 'xxxxxxxx........'], ln=57, ramp=(70, 112)),
                     7: '..x...x...x...x.'})
    # A again, a whole tone higher (G major), bigger: bell doubles the lead in the a' phrases
    bell = ' | '.join(A_BARS[i] if i in (4, 5, 6, 7, 12, 13, 14, 15) else 'r:16' for i in range(16))
    s.section(16, chords=A_CHORDS, lines={1: A_LEAD, 10: bell}, shift=2, vels={1: 104, 10: 66},
              bass='bounce', bass_vel=100,
              comp=dict(p='..x...x...x...x.', n=2, ln=2, vel=72),
              drums={5: ['x...x...x...x...'] * 7 + ['x...x...x.x.x.x.'] + ['x...x...x...x...'] * 7 + ['x...x...x.x.xxxx'],
                     6: ['....x.......x...'] * 7 + ['....x.....x.x.x.'] + ['....x.......x...'] * 7 + ['....x...xxxxxxxx'],
                     7: D(['..x...x...x...x.'] * 8 + ['x.x.x.x.x.x.x.x.'] * 8, vel=56),
                     9: D('..x...x...x...x.', vel=44)})
    # finish: a flourish, a dominant, a ritardando and a clear last chord (G major)
    s.section(3, chords='C D7 G', bass='drive', comp=dict(p='x...x...x...x...', n=2, ln=3, vel=70),
              lines={1: FIN_LEAD3, 10: 'r:16 | r:16 | B5:4 G5:4 D5:8'}, vels={1: 106, 10: 70},
              tempo=[(2, 148)],
              drums={5: ['x...x...x...x...'] * 3,
                     6: D(['....x.......x...', '..x.x.x.x.x.x.x.', 'x...x...xxxxxxxx'], ln=57),
                     7: D(['x.x.x.x.x.x.x.x.', 'x.x.x.x.x.x.x.x.', '................'], vel=56)})
    s.section(1, chords='G',
              lines={1: 'G5:12l r:4', 2: 'G3+B3+D4:12l r:4', 3: 'G1:12l r:4'}, vels={1: 110, 2: 80, 3: 104},
              tempo=[(0, 118)],
              drums={5: D('X...............', vel=108)})
    return s


# =============================================================================================
# 10008 - victory.  G major, 164 bpm, 20 bars (about 30 s): fanfare, tune, sequence, climax, last chord
# =============================================================================================
def song_10008():
    s = Song(10008, 164, prio={8: 8})
    # fanfare call
    s.section(2, chords='G D',
              lines={1: 'r:2 D5:2 G5:4 B4:2 D5:2 G5:4 | A5:2 F#5 D5:6 F#5:2 A5:4',
                     8: 'r:16 | r:8 D4:2 E4 F#4 G4'},
              vels={1: 106},
              drums={5: ['x.......x...x.x.', 'x...x...x.x.x.x.'],
                     6: D(['................', 'xxxxxxxx........'], ln=57, ramp=(80, 110)),
                     9: D(['................', 'x.x.x.x.x.x.x.x.'])})
    # the rousing tune (the tuned drum plays the low line: there is no bass voice here)
    s.section(8, chords='G C D G  Em C D G',
              lines={1: '''B4:2 D5 G5:4 G5:2 A5 B5:4 | A5:4 G5:2 E5 G5:4 C5:4 | F#5:4 A5 F#5:2 D5 A4:4 | G5:4 D5 B4 r:2 D5 |
                          E5:3 G5 B5:2 A5:3 G5 E5:2 | C5:3 E5 G5:2 A5:3 G5 E5:2 | D5:2 F#5 A5:4 F#5:2 A5 C6:4 | B5:4 A5:2 G5 G5:8'''},
              vels={1: 106},
              bass='oom', bass_ch=8, bass_off=12, bass_vel=96,
              drums={5: 'x...x...x...x...',
                     6: ['....x.......x...'] * 3 + ['....x.....x.xxxx'] + ['....x.......x...'] * 3 + ['....x...xxxxxxxx'],
                     7: D('..x...x...x...x.', vel=54),
                     9: D(['................'] * 4 + ['x.x.x.x.x.x.x.x.'] * 4, vel=44),
                     10: D('x...............', key=79, vel=80)})
    # a rising sequence, one step higher each bar
    s.section(6, chords='C D Em C D D',
              lines={1: '''G5:4 G5:2 G5 E5:4 C5:4 | A5:4 A5:2 A5 F#5:4 D5:4 | B5:4 B5:2 B5 G5:4 E5:4 |
                          C6:4 C6:2 C6 G5:4 E5:4 | A5:2 F#5 D5 F#5 A5:4 C6:4 | D6:4 A5:4 F#5:4 r:4''',
                     10: '''r:16 | r:16 | r:16 | r:16 | r:8 A5:2 F#5 D5 F#5 | r:16'''},
              vels={1: 108, 10: 78},
              bass='hop', bass_ch=8, bass_off=12, bass_vel=98,
              drums={5: ['x...x...x...x...'] * 5 + ['x...x...x...xxxx'],
                     6: D(['....x.......x...'] * 4 + ['..x.x.x.x.x.x.x.', 'xxxxxxxxxxxxxxxx'], ln=57, ramp=(92, 118)),
                     7: D('..x...x...x...x.', vel=58),
                     9: D('x.x.x.x.x.x.x.x.', vel=46)})
    # climax
    s.section(3, chords='G C D',
              lines={1: '''B4:2 D5 G5 B5 D6:4 B5:4 | C6:4 A5:2 G5 E5:4 G5:4 | F#5:4 A5 D6 A5:2 F#5'''},
              vels={1: 112},
              bass='drive', bass_ch=8, bass_off=12, bass_vel=100,
              tempo=[(2, 150)],
              drums={5: 'x...x...x...x...',
                     6: D(['x.x.x.x.x.x.x.x.', 'x.x.x.x.x.x.x.x.', 'x...x...xxxxxxxx'], ln=57, vel=104),
                     7: D('x.x.x.x.x.x.x.x.', vel=60),
                     10: D('x...x...x...x...', key=79, vel=82)})
    # the last chord: lead, chords and bass together
    s.section(1, chords='G',
              lines={1: 'G5:12l r:4', 2: 'G3+B3+D4:12l r:4', 3: 'G1:12l r:4'},
              vels={1: 112, 2: 84, 3: 105},
              tempo=[(0, 124)],
              drums={5: D('X...............', vel=108)})
    return s


# =============================================================================================
# 10010 - defeat.  D minor, 102 bpm, 14 bars (about 33 s): a slow plodding march, falling lines
# =============================================================================================
def song_10010():
    s = Song(10010, 102)
    s.section(13, chords='Dm Gm A7 Dm  Dm Bb A7 Dm  Gm Dm Eb A7  Dm',
              lines={10: '''F5:6 E5:2 D5:4 r:4 | G5:6 F5:2 Eb5:4 r:4 | G5:4 F5:2 E5 C#5:4 r:4 | D5:8 r:8 |
                            A5:6 G5:2 F5:4 E5:4 | F5:6 E5:2 D5:4 C5:4 | E5:4 C#5:4 A4:8 | D5:12 r:4 |
                            Bb5:4 A5:4 G5:4 F5:4 | F5:4 E5:4 D5:4 C5:4 | Eb5:4 D5:4 C5:4 Bb4:4 | E5:2 D5 E5 D5 C#5:8 |
                            F5:4 E5:4 D5:8'''},
              vels={10: 84},
              bass='march', bass_vel=98,
              comp=dict(p='....x.......x...', n=2, ln=3, vel=68, center=56),
              tempo=[(11, 94)],
              drums={5: D('x.......x.......', vel=104),
                     7: D('..x...x...x...x.', vel=50),
                     9: D('....x.......x...', vel=40)})
    s.section(1, chords='Dm', lines={2: 'D3+A3+F4:12l r:4', 3: 'D2:12l r:4',
                                     10: 'r:4 A5:2 F5:2 D5:8l'}, vels={10: 80, 2: 74}, tempo=[(0, 80)],
              drums={5: D('x...............', vel=100), 7: D('x...............', vel=46)})
    return s


# =============================================================================================
# 10006 - spare: a bright flourish.  C major, 137 bpm, 12 bars (about 21 s)
# =============================================================================================
def song_10006():
    s = Song(10006, 137)
    s.section(12, chords='C G Am F  Dm G C Am  F G7 C C',
              lines={1: '''C5:1 D5 E5 F5 G5 A5 B5 C6 B5 A5 G5 F5 E5 D5 C5:2 |
                           G3:1 B3 D4 G4 B4 D5 G5 B5 D6:2 B5:1 G5 D5 B4 G4:2 |
                           A4:1 C5 E5 A5 C6 A5 E5 C5 A4:2 C5 E5 A4 |
                           F5:2 A5 C6:4 A5:2 F5 C5 F5 |
                           D6:1 C6 A5 F5 D5 A4 F4 D4 F4 A4 D5 F5 A5 D6 A5:2 |
                           G5:1 F5 E5 D5 C5 B4 A4 G4 G4:2 B4 D5 G5 |
                           C5:2 E5 G5 C6 G5 E5 C5:4 |
                           A4:1 B4 C5 D5 E5 F5 G5 A5 G5 E5 C5 A4 E5:2 A5 |
                           F5:2 A5 C6 A5 F5 C5 A4 F4 |
                           G4:1 B4 D5 F5 G5 B5 D6 B5 G5 F5 D5 B4 G4:4 |
                           C5:1 E5 G5 C6 G5 E5 C5 G4 C5 E5 G5 C6 C6:4 |
                           C6:4 G5:4 C5:8l''',
                     10: '''G5:4 r:12 | D6:4 r:12 | C6:4 r:12 | A5:4 r:12 | A5:4 r:12 | B5:4 r:12 |
                            G5:4 r:12 | C6:4 r:12 | A5:4 r:12 | D6:4 r:12 | G5:4 r:12 | C6:6l r:10'''},
              vels={1: 100, 10: 74},
              comp=dict(p='x.......x.......', n=2, ln=6, vel=62),
              drums={5: ['x.......x.......'] * 11 + ['x...............'],
                     6: D(['....x.......x...'] * 11 + ['................'], vel=70),
                     9: D(['x.x.x.x.x.x.x.x.'] * 11 + ['................'], vel=38)})
    return s


# =============================================================================================
# 10007 - spare: a bouncy, playful interlude.  G major, 120 bpm, 12 bars (24 s)
# =============================================================================================
def song_10007():
    s = Song(10007, 120, prio={8: 8})
    s.section(12, chords='G Em C D  G Em Am D7  C G D G',
              lines={1: '''G5:3 D5 B4:2 G5:3 D5 B4:2 | E5:3 B4 G4:2 B4 E5 G5 r:2 | C5:2 E5 G5 E5 G5:4 E5:2 C5 | D5:3 F#5 A5:2 F#5:3 D5 r:2 |
                           G5:3 D5 B4:2 G5:3 B5 G5:2 | E5:3 G5 B5:2 G5:3 E5 r:2 | A4:2 C5 E5 A5 E5 C5 A4:4 | D5:2 F#5 A5 C6 A5 F#5 D5:4 |
                           E5:4 E5:2 G5 C6:4 G5:4 | D5:4 D5:2 G5 B5:4 G5:4 | A5:3 F#5 D5:2 F#5:3 A5 r:2 | G5:2 B5 D6:4 G5:8l''',
                     10: '''r:16 | r:16 | r:16 | r:12 A5:2 D6 | r:16 | r:16 | r:16 | r:12 C6:2 A5 | r:16 | r:16 | r:16 | G5:4l r:12'''},
              vels={1: 100, 10: 72},
              bass='oom', bass_ch=8, bass_off=12, bass_vel=94,
              comp=dict(p='..x...x...x...x.', n=2, ln=2, vel=64),
              drums={5: ['x.....x...x.....'] * 11 + ['x...............'],
                     6: D(['....x.......x...'] * 11 + ['................'], vel=84),
                     9: D(['x.x.x.x.x.x.x.x.'] * 11 + ['................'], vel=40)})
    return s


SONGS = [(10001, song_10001, 103, 1185, 'Main theme'), (10006, song_10006, 21, 227, 'Bright flourish'),
         (10007, song_10007, 24, 236, 'Bouncy interlude'), (10008, song_10008, 30, 292, 'Victory'),
         (10010, song_10010, 33, 273, 'Defeat')]


def main():
    for sid, make, want_len, want_notes, title in SONGS:
        s = make()
        before = len(s.notes)
        s.govern()
        s.tidy()
        data = s.to_midi(title)
        with open(os.path.join(HERE, '%d.mid' % sid), 'wb') as f:
            f.write(data)
        keys = [n[3] for n in s.notes]
        print('%d: %5.1f s plain, %5.1f s clock (table %d); %d notes (table %d, %d%%; %d dropped of %d); '
              'poly %d; keys %d..%d; %d bytes' % (
                  sid, s.plain_length(), s.sim_length(), want_len, len(s.notes), want_notes,
                  100 * len(s.notes) // want_notes, s.dropped, before, s.max_poly(), min(keys), max(keys), len(data)))


if __name__ == '__main__':
    main()
