"""Capture the original's AdLib (OPL2) register writes in the emulator.

python opl_capture.py modes                 # boot with each Sound Mode 0..9 and count OPL writes (which is AdLib?)
python opl_capture.py song <effect id> [mode]   # boot with AdLib, start a song (f_284b3), log the writes

The driver writes the OPL2 through f_28400 (index port 0x388, data port 0x389). SimEmu stubs all port I/O;
this subclass answers the AdLib detection (timer 1 sets status bits 0xC0) and records (register, value) pairs.
"""
import sys
from emu import SimEmu

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
