---
layout: default
title: "opl_capture"
permalink: /reference/opl-capture/
---

# opl_capture

*`opl_capture.py` — Capture the original's AdLib (OPL2) register writes in the emulator.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `opl_capture.py`]({{ site.baseurl }}/assets/reference/re/opl_capture.py)

Capture the original's AdLib (OPL2) register writes in the emulator.

python opl_capture.py modes                 # boot with each Sound Mode 0..9 and count OPL writes (which is AdLib?)
python opl_capture.py song <effect id> [mode]   # boot with AdLib, start a song (f_284b3), log the writes
python opl_capture.py record [outdir]          # traces for the C# driver port (remake/build/traces/opl)

The driver writes the OPL2 through f_28400 (index port 0x388, data port 0x389). SimEmu stubs all port I/O;
this subclass answers the AdLib detection (timer 1 sets status bits 0xC0) and records (register, value) pairs.

## At a glance

- **240** lines
- **Classes / hooks:** `OplEmu`, `Snapshot`, `Trace`
- **4 top-level functions**, including `boot`, `main`, `record`, `capture_song`
- **Original routines referenced:** `f_28400`, `f_28415`, `f_284b3`, `f_28b1f`, `f_29927`

## Source

{% raw %}
```python
"""Capture the original's AdLib (OPL2) register writes in the emulator.

python opl_capture.py modes                 # boot with each Sound Mode 0..9 and count OPL writes (which is AdLib?)
python opl_capture.py song <effect id> [mode]   # boot with AdLib, start a song (f_284b3), log the writes
python opl_capture.py record [outdir]          # traces for the C# driver port (remake/build/traces/opl)

The driver writes the OPL2 through f_28400 (index port 0x388, data port 0x389). SimEmu stubs all port I/O;
this subclass answers the AdLib detection (timer 1 sets status bits 0xC0) and records (register, value) pairs.
"""
import copy
import os
import sys
from emu import SimEmu

HERE = os.path.dirname(os.path.abspath(__file__))

OPL = 0x388


class OplEmu(SimEmu):
    def __init__(self, mode, **kw):
        super().__init__(base=0x100, **kw)
        self.overrides['SIMANT.CFG'] = b'Display Mode: V\r\nSound Mode: %d\r\n' % mode
        self.opl_index = 0
        self.opl_status = 0
        self.writes = []                          # (register, value)
        self.other_ports = {}
        self.pit, self.pit_high = 0xffff, False   # PIT channel 0, read low byte then high byte
        self.dsp_out = []                         # Sound Blaster DSP at 0x220: bytes waiting at 0x22A
        self.dsp_cmd = []                         # bytes written to 0x22C (commands and their data)
        self.dac = []                             # (register write count so far, sample) for DSP command 0x10

    def _on_in(self, uc, port, size, user):
        if port == OPL:
            return self.opl_status
        if port == 0x22e:                         # read-buffer status: bit 7 = data waiting
            return 0x80 if self.dsp_out else 0
        if port == 0x22a:
            return self.dsp_out.pop(0) if self.dsp_out else 0xff
        if port == 0x22c:                         # write-buffer status: always ready
            return 0
        if port == 0x40:                          # the driver times its delays on the PIT (f_28415): count down
            if not self.pit_high:
                self.pit = (self.pit - 0x40) & 0xffff
            self.pit_high = not self.pit_high
            return (self.pit >> 8) if not self.pit_high else (self.pit & 0xff)
        return super()._on_in(uc, port, size, user)

    def _on_out(self, uc, port, size, value, user):
        if port == OPL:
            self.opl_index = value & 0xff
        elif port == OPL + 1:
            v = value & 0xff
            if self.opl_index == 4:               # timer control: reset clears the flags, starting timer 1 sets them
                self.opl_status = 0 if v & 0x80 else (0xC0 if v & 1 else self.opl_status)
            self.writes.append((self.opl_index, v))
        elif port == 0x226:                       # DSP reset: answers 0xAA
            if value & 1 == 0:
                self.dsp_out = [0xaa]
        elif port == 0x22c:
            v = value & 0xff
            if self.dsp_cmd[-1:] == [0x10] and len(self.dsp_cmd) % 2 == 1:
                self.dac.append((len(self.writes), v))
                self.dsp_cmd = []
            else:
                self.dsp_cmd.append(v)
                if v == 0xe1:                     # DSP version: 2.0
                    self.dsp_out += [2, 0]
                    self.dsp_cmd = []
                elif v != 0x10:
                    self.dsp_cmd = []
            self.other_ports[port] = self.other_ports.get(port, 0) + 1
        elif port not in (0x3c4, 0x3c5, 0x3ce, 0x3cf, 0x3c8, 0x3c9, 0x43, 0x40, 0x61, 0x20):
            self.other_ports[port] = self.other_ports.get(port, 0) + 1


def boot(mode):
    e = OplEmu(mode)
    e.boot()
    return e


def main():
    if sys.argv[1] == 'modes':
        for mode in range(10):
            try:
                e = boot(mode)
                print(mode, 'opl writes', len(e.writes), 'other ports', e.other_ports, 'console', ''.join(e.console)[-200:].replace('\n', ' | '))
            except Exception as ex:                # noqa: BLE001 (a probe: report and go on)
                print(mode, 'failed', ex)
    elif sys.argv[1] == 'song':
        song = int(sys.argv[2], 0)
        mode = int(sys.argv[3]) if len(sys.argv) > 3 else 4
        for t, reg, v in capture_song(boot(mode), song):
            print(f'{t} {reg:02x} {v:02x}')
    elif sys.argv[1] == 'record':
        record(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', '..', 'remake', 'build', 'traces', 'opl'))


class Snapshot:
    """The emulator's memory, registers and Python-side state, to run each case from the same booted game."""
    SKIP = ('uc', 'layout', 'files')

    def __init__(self, e):
        self.mem = bytes(e.uc.mem_read(0, 0x100000))
        self.ctx = e.uc.context_save()
        self.py = {k: copy.deepcopy(v) for k, v in vars(e).items() if k not in self.SKIP}
        self.files = {h: (f, f.tell()) for h, f in e.files.items()}   # open files: keep the objects, restore positions

    def restore(self, e):
        e.uc.mem_write(0, self.mem)
        e.uc.context_restore(self.ctx)
        e.uc.ctl_remove_cache(0, 0x100000)
        for k, v in self.py.items():
            setattr(e, k, copy.deepcopy(v))
        for h, f in list(e.files.items()):
            if h not in self.files:
                f.close()
        e.files = {}
        for h, (f, pos) in self.files.items():
            f.seek(pos)
            e.files[h] = f


class Trace:
    """A replayable trace: commands for the driver and the register writes each one makes.
    S id: start song id (f_284b3); T: one sequencer step (f_28b1f), then R wait; E n: sound effect n
    (f_29927); W rr vv: an OPL2 register write (hex), belonging to the command above it."""

    def __init__(self, e):
        self.e, self.lines = e, []

    def _run(self, cmd, lin, args=()):
        n = len(self.e.writes)
        r = self.e.call_lin(lin, args)
        self.lines.append(cmd)
        self.lines += [f'W {reg:02x} {v:02x}' for reg, v in self.e.writes[n:]]
        return r

    def song(self, song_id):
        self._run(f'S {song_id}', 0x284b3, (song_id,))

    def step(self):
        wait = self._run('T', 0x28b1f)
        self.lines.append(f'R {wait}')
        return wait

    def effect(self, n):
        self._run(f'E {n}', 0x29927, (n,))

    def play(self, max_steps=20000):
        for _ in range(max_steps):
            if self.step() == 0xffff:
                break

    def save(self, path):
        with open(path, 'w', newline='\n') as f:
            f.write('\n'.join(self.lines) + '\n')


def record(outdir, mode=6):
    """Every song (SOUND type 18 ids) and every effect from a fresh boot, all effects in a row, and a song
    with effects in between (voice stealing), as traces for OpenSimAnt.Data's driver port."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    import simres
    game_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    songs = sorted(r['id'] for r in simres.read_archive(os.path.join(game_dir, 'SOUND')) if r['type'] == 18)
    os.makedirs(outdir, exist_ok=True)
    e = boot(mode)
    snap = Snapshot(e)
    for s in songs:
        snap.restore(e)
        t = Trace(e)
        t.song(s)
        t.play()
        t.save(os.path.join(outdir, f'song_{s}.trace'))
        print('song', s, len(t.lines))
    for n in range(56):
        snap.restore(e)
        t = Trace(e)
        t.effect(n)
        t.save(os.path.join(outdir, f'fx_{n:02d}.trace'))
    snap.restore(e)
    t = Trace(e)
    for n in range(56):
        t.effect(n)
    t.save(os.path.join(outdir, 'fx_all.trace'))
    snap.restore(e)
    t = Trace(e)
    t.song(0x2711)
    k = 0
    for i in range(3000):
        if t.step() == 0xffff:
            break
        if i % 40 == 7:
            t.effect([0, 3, 9, 15, 25, 30, 35, 46, 48, 50, 51, 53, 54][k % 13])
            k += 1
    t.save(os.path.join(outdir, 'mixed_2711.trace'))
    print('effects and mixed done')
    # the sample mixer: the fast handler's DAC bytes (DSP command 0x10), one line per tick
    for name, plan in (('dac_13', [(0, 13)]), ('dac_01', [(0, 1)]), ('dac_41', [(0, 41)]), ('dac_55', [(0, 55)]),
                       ('dac_overlap', [(0, 13), (300, 41), (700, 1), (900, 13)])):
        snap.restore(e)
        lines, todo, k = [], list(plan), 0
        while k < 20000:
            while todo and todo[0][0] == k:
                n = todo.pop(0)[1]
                e.call_lin(0x29927, (n,))
                lines.append(f'E {n}')
            e.set16(0x55b3, 0x74a3, 1000)          # never chain to the BIOS timer (there is none here)
            m = len(e.dac)
            e.call(0x28bc, 0x28bd5 - 0x28bc0, (0x0202,))   # the handler, as an interrupt (FLAGS for its iret)
            lines.append('K ' + (' '.join(str(v) for _, v in e.dac[m:]) or '-'))
            k += 1
            idle = all(e.w16(0x55b3, 0x6b4c + 0x14 * v + 2) == 0 and e.w16(0x55b3, 0x6b4c + 0x14 * v + 4) == 0 for v in (0, 1))
            if idle and not todo:
                break
        with open(os.path.join(outdir, name + '.dac'), 'w', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print(name, k, 'ticks')


def capture_song(e, song, max_events=20000):
    """Start song `song` (f_284b3) and step the sequencer f_28b1f (one MIDI event per call; the timer
    handlers 0x28cb0 / 0x28f4a call it and keep its result, the wait in driver ticks, in DS:6B42) until it
    returns -1. Returns [(driver tick, register, value)]."""
    e.call_lin(0x284b3, (song,))
    out, t = [], 0
    for _ in range(max_events):
        n = len(e.writes)
        wait = e.call_lin(0x28b1f)
        out += [(t, reg, v) for reg, v in e.writes[n:]]
        if wait == 0xffff:
            break
        t += wait
    return out


if __name__ == '__main__':
    main()
```
{% endraw %}
