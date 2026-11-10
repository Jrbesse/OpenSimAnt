---
layout: default
title: "emu"
permalink: /reference/emu/
---

# emu

*`emu.py` — Run original SIMANT.EXE code inside Unicorn (16-bit real mode) on build/flat.bin.*

[Reference index]({{ site.baseurl }}/reference/) · [Download `emu.py`]({{ site.baseurl }}/assets/reference/re/emu.py)

Run original SIMANT.EXE code inside Unicorn (16-bit real mode) on build/flat.bin.

Two ways to use it:

    emu = SimEmu()                    # image at segment 0, no DOS process: call self-contained routines
    emu.call(0x0093, 0x01ab)          # far-call flat seg:off, returns AX

    emu = SimEmu(base=0x100)          # image relocated like a real DOS load, with PSP + environment
    emu.boot()                        # runs the real startup until the game sits in its input loop
    emu.call(0x6b36, 0x000b)          # then drive game routines directly

All seg arguments to call/read/write are *flat* segments (as in the notes); the load base is added here.
A minimal DOS layer (memory blocks, read-only file access to the game directory, console), BIOS
video/keyboard/mouse/timer stubs and port I/O stubs are provided. Every interrupt is counted in `int_counts`.

## At a glance

- **563** lines
- **Classes / hooks:** `SimEmu`
- **1 top-level functions**, including `_rng_selftest`
- **Original routines referenced:** `f_20e20`

## Source

{% raw %}
```python
"""Run original SIMANT.EXE code inside Unicorn (16-bit real mode) on build/flat.bin.

Two ways to use it:

    emu = SimEmu()                    # image at segment 0, no DOS process: call self-contained routines
    emu.call(0x0093, 0x01ab)          # far-call flat seg:off, returns AX

    emu = SimEmu(base=0x100)          # image relocated like a real DOS load, with PSP + environment
    emu.boot()                        # runs the real startup until the game sits in its input loop
    emu.call(0x6b36, 0x000b)          # then drive game routines directly

All seg arguments to call/read/write are *flat* segments (as in the notes); the load base is added here.
A minimal DOS layer (memory blocks, read-only file access to the game directory, console), BIOS
video/keyboard/mouse/timer stubs and port I/O stubs are provided. Every interrupt is counted in `int_counts`.
"""
import collections
import json
import os
import struct
from unicorn import (Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR, UC_HOOK_INSN, UC_HOOK_MEM_READ, UC_HOOK_CODE, UcError)
from unicorn.x86_const import (UC_X86_REG_EFLAGS, UC_X86_REG_AX, UC_X86_REG_BX, UC_X86_REG_CX,
                               UC_X86_REG_DX, UC_X86_REG_SI, UC_X86_REG_DI, UC_X86_REG_BP, UC_X86_REG_SP,
                               UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_IP,
                               UC_X86_INS_IN, UC_X86_INS_OUT)

HERE = os.path.dirname(os.path.abspath(__file__))
DGROUP = 0x55b3
SIM = 0x3e1d
G = 0x50f6
T = 0x3d57
RET_SEG = 0x7f00              # absolute: far-return trap (`hlt`); image (base 0x100) ends at 0x7ebb0
STACK_SEG = 0xF000            # absolute: scratch stack for call() (above the DOS heap)
HEAP = [(0x8000, 0xA000), (0xC000, 0xF000)]   # absolute paragraphs for INT 21h/48h (avoids video RAM)
FLAG_CF, FLAG_ZF = 0x0001, 0x0040
HEADLESS_STUBS = [
    0x259de,   # window/sprite draw dispatcher (reached from sim events via section 24)
    0x71a7d,   # section 16: game-over screen (vector 2f802)
]
MESSAGE_BOX = 0x71b1a  # section 16: modal message dialog f(0, string_id, 1) - logged, then skipped


class SimEmu:
    def __init__(self, base=0, game_dir=os.path.join(HERE, '..', '..')):
        flat = open(os.path.join(HERE, 'build', 'flat.bin'), 'rb').read()
        self.base = base
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_16)
        uc.mem_map(0, 0x100000)
        img = bytearray(flat)
        if base:
            relocs = open(os.path.join(HERE, 'build', 'relocs.bin'), 'rb').read()
            for i in range(0, len(relocs), 4):
                a = struct.unpack_from('<I', relocs, i)[0]
                struct.pack_into('<H', img, a, (struct.unpack_from('<H', img, a)[0] + base) & 0xffff)
        uc.mem_write(base * 16, bytes(img))
        uc.mem_write(RET_SEG * 16, b'\xf4')       # hlt
        self.layout = json.load(open(os.path.join(HERE, 'build', 'layout.json')))
        self.game_dir = game_dir
        self.console = []
        self.int_counts = collections.Counter()
        self.files = {}
        self.next_handle = 5
        self.heap = [list(r) for r in HEAP]
        self.ticks = 0
        self.mouse = dict(x=320, y=200, buttons=0)
        self.keys = []                            # queued BIOS keystrokes (ax values)
        self.stop_after_polls = None
        self.video_mode = 3
        # files served from memory instead of the game directory (no sound: the sound driver needs hardware)
        self.overrides = {'SIMANT.CFG': b'Display Mode: V\r\nSound Mode: 0\r\n'}
        uc.hook_add(UC_HOOK_INTR, self._on_int)
        uc.hook_add(UC_HOOK_INSN, self._on_in, None, 1, 0, UC_X86_INS_IN)
        uc.hook_add(UC_HOOK_INSN, self._on_out, None, 1, 0, UC_X86_INS_OUT)
        uc.hook_add(UC_HOOK_MEM_READ, self._on_bios_timer_read, None, 0x46c, 0x46f)
        # The game's own clock: 32-bit counter at flat 1b73:0012, normally bumped by its INT 8 handler
        # (hardware interrupts never fire here), so every read advances it by one tick instead.
        self.game_clock = (0x1b73 + base) * 16 + 0x12
        uc.hook_add(UC_HOOK_MEM_READ, self._on_game_clock_read, None, self.game_clock, self.game_clock + 1)
        # f_20e20(n) waits for the INT 8 handler to count the word at 1b73:0006 down to 0: count it down per read
        self.game_delay = (0x1b73 + base) * 16 + 6
        uc.hook_add(UC_HOOK_MEM_READ, self._on_game_delay_read, None, self.game_delay, self.game_delay + 1)

    # ---------------------------------------------------------------- hardware stubs
    vga = None                                    # a vga.VGA takes the port I/O when attached

    def _on_in(self, uc, port, size, user):
        if self.vga:
            return self.vga._on_in(uc, port, size, user)
        if port == 0x3da:                         # VGA input status: toggle retrace bits
            self.ticks += 1
            return 0x09 if self.ticks & 1 else 0x00
        return 0xff if size == 1 else 0xffff

    def _on_out(self, uc, port, size, value, user):
        if self.vga:
            self.vga._on_out(uc, port, size, value, user)

    def _on_bios_timer_read(self, uc, access, address, size, value, user):
        if address == 0x46c:
            self.ticks += 1
            uc.mem_write(0x46c, struct.pack('<I', self.ticks))

    def stub(self, lin, ax=None):
        """Make the far function at flat linear `lin` return immediately (optionally with AX = ax)."""
        code = (b'\xb8' + struct.pack('<H', ax) if ax is not None else b'') + b'\xcb'   # [mov ax, imm] retf
        a = self.base * 16 + lin
        self.uc.mem_write(a, code)
        self.uc.ctl_remove_cache(a, a + 16)       # drop any already-translated code block

    def stub_drawing(self):
        """Headless: skip window/sprite drawing and modal message boxes that the simulation triggers.
        Messages are recorded in self.messages as (tick, string id)."""
        for lin in HEADLESS_STUBS:
            self.stub(lin)
        self.messages = []
        a = self.base * 16 + MESSAGE_BOX

        def on_msg(uc, address, size, user):
            sp = uc.reg_read(UC_X86_REG_SP)
            ss = uc.reg_read(UC_X86_REG_SS)
            args = struct.unpack('<3H', bytes(uc.mem_read(ss * 16 + sp + 4, 6)))
            self.messages.append((self.w16(G, 0xf08), args[1]))
        self.uc.hook_add(UC_HOOK_CODE, on_msg, None, a, a)
        self.stub(MESSAGE_BOX)

    def _on_game_delay_read(self, uc, access, address, size, value, user):
        if address == self.game_delay:
            v = struct.unpack('<H', bytes(uc.mem_read(address, 2)))[0]
            if v:
                uc.mem_write(address, struct.pack('<H', v - 1))

    def _on_game_clock_read(self, uc, access, address, size, value, user):
        if address == self.game_clock and not getattr(self, 'clock_frozen', False):
            v = struct.unpack('<I', bytes(uc.mem_read(address, 4)))[0] + 1
            uc.mem_write(address, struct.pack('<I', v & 0xffffffff))

    # ---------------------------------------------------------------- DOS / BIOS
    def _flags(self, uc, set_bits=0, clear_bits=0):
        f = uc.reg_read(UC_X86_REG_EFLAGS)
        uc.reg_write(UC_X86_REG_EFLAGS, (f | set_bits) & ~clear_bits)

    def _str(self, seg, off):
        b = bytearray()
        while True:
            c = self.uc.mem_read(seg * 16 + off + len(b), 1)[0]
            if c == 0:
                return b.decode('latin1')
            b.append(c)

    def _alloc(self, paras):
        for r in self.heap:
            if r[1] - r[0] >= paras:
                seg = r[0]
                r[0] += paras
                return seg
        return None

    def _largest(self):
        return max(r[1] - r[0] for r in self.heap)

    mouse_handler = None                          # (segment, offset, event mask) from INT 33h AX=0Ch
    TRAMP = 0x0600                                # flat address of the handler-call trampoline

    @property
    def mouse_events(self):
        if not hasattr(self, '_mouse_events'):
            self._mouse_events = []
        return self._mouse_events

    def mouse_event(self, cond, x, y, buttons):
        """Queue a mouse driver event (cond: 1 move, 2 left press, 4 left release, 8 right press, 16 right
        release); it is delivered at the game's next keyboard poll."""
        if not self.mouse_events:
            self.mouse.update(x=x, y=y)
        self.mouse_events.append((cond, x, y, buttons))

    def _deliver_mouse(self, uc, zf=True):
        """Run the game's mouse handler as the driver would: an interrupt-style frame back to the poll (with ZF set:
        no key), then a trampoline that saves the registers, loads AX = condition, BX = buttons, CX / DX = position,
        far-calls the handler, restores the registers and IRETs."""
        import struct as st
        cond, x, y, buttons = self.mouse_events.pop(0)
        self.mouse.update(x=x, y=y, buttons=buttons)
        seg, off, mask = self.mouse_handler
        cond &= mask
        code = (b'\x50\x53\x51\x52\x56\x57\x55\x1e\x06'
                + b'\xb8' + st.pack('<H', cond) + b'\xbb' + st.pack('<H', buttons)
                + b'\xb9' + st.pack('<H', x) + b'\xba' + st.pack('<H', y)
                + b'\x31\xf6\x31\xff'
                + b'\x9a' + st.pack('<HH', off, seg)
                + b'\x07\x1f\x5d\x5f\x5e\x5a\x59\x5b\x58\xcf')
        uc.mem_write(self.TRAMP, code)
        uc.ctl_remove_cache(self.TRAMP, self.TRAMP + len(code))
        from unicorn.x86_const import UC_X86_REG_SS, UC_X86_REG_CS, UC_X86_REG_IP
        ss, sp = uc.reg_read(UC_X86_REG_SS), uc.reg_read(UC_X86_REG_SP)
        flags = uc.reg_read(UC_X86_REG_EFLAGS) | (FLAG_ZF if zf else 0)
        cs, ip = uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)
        sp = (sp - 6) & 0xffff
        uc.mem_write(ss * 16 + sp, st.pack('<HHH', ip, cs, flags & 0xffff))
        uc.reg_write(UC_X86_REG_SP, sp)
        uc.reg_write(UC_X86_REG_CS, self.TRAMP >> 4)
        uc.reg_write(UC_X86_REG_IP, self.TRAMP & 15)

    def run(self, polls, max_insns=400_000_000, chunk=2_000_000):
        """Continue from where the emulation stopped until `polls` more input polls (or max_insns), in slices;
        between slices (an instruction boundary) a queued mouse event is delivered, so a game busy-waiting on its
        handler's variables still gets it."""
        from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP
        uc = self.uc
        self.stop_after_polls = polls
        done = 0
        try:
            while done < max_insns and self.stop_after_polls > 0:
                if self.mouse_events and self.mouse_handler:
                    self._deliver_mouse(uc, zf=False)
                cs, ip = uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)
                uc.emu_start(cs * 16 + ip, 0xfffff, count=chunk)
                done += chunk
        finally:
            self.stop_after_polls = None

    def _poll(self):
        if self.stop_after_polls is not None:
            self.stop_after_polls -= 1
            if self.stop_after_polls <= 0:
                self.uc.emu_stop()

    def _on_int(self, uc, intno, user):
        r, w = uc.reg_read, uc.reg_write
        ax, bx, cx, dx = r(UC_X86_REG_AX), r(UC_X86_REG_BX), r(UC_X86_REG_CX), r(UC_X86_REG_DX)
        ds = r(UC_X86_REG_DS)
        ah, al = ax >> 8, ax & 0xff
        self.int_counts[(intno, ah if intno != 0x33 else ax)] += 1
        if intno == 0x21:
            return self._dos(uc, ah, al, ax, bx, cx, dx, ds)
        if intno == 0x10:                         # video BIOS
            if self.vga and self.vga.int10(uc, ax, bx, cx, dx, r(UC_X86_REG_ES)):
                return
            if ah == 0x00:
                self.video_mode = al
            elif ah == 0x0f:
                w(UC_X86_REG_AX, (80 << 8) | self.video_mode)
                w(UC_X86_REG_BX, 0)
            elif ah == 0x12:                      # EGA info: 256K, colour
                w(UC_X86_REG_BX, 0x0003)
                w(UC_X86_REG_CX, 0x0009)
            elif ah == 0x1a:                      # display combination: VGA colour
                w(UC_X86_REG_AX, 0x001a)
                w(UC_X86_REG_BX, 0x0008)
            return
        if intno == 0x16:                         # keyboard
            if ah in (0x01, 0x11):
                self._poll()
                if self.mouse_events and self.mouse_handler:
                    self._deliver_mouse(uc)       # the driver calls the game's handler (INT 33h AX=0Ch)
                    return
                if self.keys:
                    w(UC_X86_REG_AX, self.keys[0])
                    self._flags(uc, clear_bits=FLAG_ZF)
                else:
                    self._flags(uc, set_bits=FLAG_ZF)
            elif ah in (0x00, 0x10):
                w(UC_X86_REG_AX, self.keys.pop(0) if self.keys else 0)
            elif ah == 0x02:
                w(UC_X86_REG_AX, 0)
            return
        if intno == 0x33:                         # mouse driver present, 2 buttons
            if ax == 0:
                w(UC_X86_REG_AX, 0xffff)
                w(UC_X86_REG_BX, 2)
            elif ax == 3:
                self._poll()
                if self.mouse_events and self.mouse_handler:
                    self.mouse.update(buttons=self.mouse_events[0][3])
                w(UC_X86_REG_BX, self.mouse['buttons'])
                w(UC_X86_REG_CX, self.mouse['x'])
                w(UC_X86_REG_DX, self.mouse['y'])
                if self.mouse_events and self.mouse_handler:
                    self._deliver_mouse(uc)       # results set first: the trampoline restores them
            elif ax == 0x0c:                      # the event handler: CX mask, ES:DX far address
                self.mouse_handler = (r(UC_X86_REG_ES), dx, cx)
            elif ax in (5, 6):
                w(UC_X86_REG_AX, self.mouse['buttons'])
                w(UC_X86_REG_BX, 0)
            elif ax == 0x0b:
                w(UC_X86_REG_CX, 0)
                w(UC_X86_REG_DX, 0)
            return
        if intno == 0x1a and ah == 0:             # timer ticks
            self.ticks += 1
            w(UC_X86_REG_CX, self.ticks >> 16)
            w(UC_X86_REG_DX, self.ticks & 0xffff)
            w(UC_X86_REG_AX, 0)
            return
        if intno == 0x67:                         # EMS: not installed
            w(UC_X86_REG_AX, 0x8000)
            return
        if intno == 0x11:                         # equipment list
            w(UC_X86_REG_AX, 0x0026)
            return
        if intno == 0x12:                         # conventional memory KB
            w(UC_X86_REG_AX, 640)
            return

    def _dos(self, uc, ah, al, ax, bx, cx, dx, ds):
        w = uc.reg_write
        self._flags(uc, clear_bits=FLAG_CF)

        def fail(code):
            w(UC_X86_REG_AX, code)
            self._flags(uc, set_bits=FLAG_CF)

        if ah == 0x02:
            self.console.append(chr(dx & 0xff))
        elif ah == 0x09:
            self.console.append(self._str(ds, dx).split('$')[0])
        elif ah == 0x30:
            w(UC_X86_REG_AX, 0x0005)
            w(UC_X86_REG_BX, 0)
        elif ah == 0x1a:                          # set the DTA (find first / next write there)
            self.dta = ds * 16 + dx
        elif ah in (0x25, 0x0e, 0x3b, 0x0b, 0x0d):
            if ah == 0x0e:
                w(UC_X86_REG_AX, (ax & 0xff00) | 26)
        elif ah == 0x35:
            w(UC_X86_REG_BX, 0)
            w(UC_X86_REG_ES, 0)
        elif ah == 0x19:
            w(UC_X86_REG_AX, (ax & 0xff00) | 2)  # drive C:
        elif ah == 0x47:
            uc.mem_write(ds * 16 + uc.reg_read(UC_X86_REG_SI), bytes(1))
        elif ah == 0x48:                          # allocate BX paragraphs
            seg = None if bx == 0xffff else self._alloc(bx)
            if seg is None:
                w(UC_X86_REG_BX, self._largest())
                fail(8)
            else:
                w(UC_X86_REG_AX, seg)
        elif ah == 0x49:
            pass
        elif ah == 0x4a:                          # resize: accept anything
            pass
        elif ah == 0x3d:                          # open (read-only)
            name = self._str(ds, dx).replace('/', chr(92)).split(chr(92))[-1].split(':')[-1]
            path = os.path.join(self.game_dir, name.upper())
            served = getattr(self, 'find_dir', None)
            if name and served and not os.path.isfile(path) and os.path.isfile(os.path.join(served, name.upper())):
                path = os.path.join(served, name.upper())     # a file of the served folder (the file dialog's)
            if name and (name.upper() in self.overrides or os.path.isfile(path)):
                h = 5                             # DOS hands out the lowest free handle (MSC caps at 20)
                while h in self.files:
                    h += 1
                if name.upper() in self.overrides:
                    import io
                    self.files[h] = io.BytesIO(self.overrides[name.upper()])
                else:
                    self.files[h] = open(path, 'rb')
                w(UC_X86_REG_AX, h)
            else:
                self.console.append(f'[open fail {name}]')
                fail(2)
        elif ah == 0x3c:                          # create: refused (read-only harness)
            fail(5)
        elif ah == 0x3e:
            f = self.files.pop(bx, None)
            if f:
                f.close()
        elif ah == 0x3f:                          # read
            f = self.files.get(bx)
            if not f:
                if bx == 0:                       # stdin
                    w(UC_X86_REG_AX, 0)
                else:
                    fail(6)
            else:
                data = f.read(cx)
                uc.mem_write(ds * 16 + dx, data)
                w(UC_X86_REG_AX, len(data))
        elif ah == 0x40:                          # write: stdout/stderr go to console
            data = bytes(uc.mem_read(ds * 16 + dx, cx))
            if bx in (1, 2, 3, 4):
                self.console.append(data.decode('latin1'))
            w(UC_X86_REG_AX, cx)
        elif ah == 0x42:                          # seek
            f = self.files.get(bx)
            if not f:
                return fail(6)
            pos = f.seek(((cx << 16) | dx) - (1 << 32 if cx & 0x8000 else 0), al)
            w(UC_X86_REG_AX, pos & 0xffff)
            w(UC_X86_REG_DX, pos >> 16)
        elif ah == 0x44:                          # ioctl
            if al == 0:
                w(UC_X86_REG_DX, 0x80d3 if bx < 5 else 0x0002)
            else:
                w(UC_X86_REG_AX, 0)
        elif ah == 0x2c:
            w(UC_X86_REG_CX, 0x0c00)
            w(UC_X86_REG_DX, 0)
        elif ah == 0x2a:
            w(UC_X86_REG_CX, 1991)
            w(UC_X86_REG_DX, 0x0c06)
        elif ah in (0x4e, 0x4f):                  # find first / next: the served folder's entries (find_dir), else none
            find_dir = getattr(self, 'find_dir', None)
            dta = getattr(self, 'dta', None)
            if not find_dir or dta is None:
                return fail(18)
            if ah == 0x4e:                        # every entry (the game filters "*.ant" itself); folders with CX bit 4
                names = []
                for n in sorted(os.listdir(find_dir)):
                    p = os.path.join(find_dir, n)
                    if os.path.isdir(p) and not (cx & 0x10):
                        continue
                    names.append((n.upper()[:12], 0x10 if os.path.isdir(p) else 0x20, 0 if os.path.isdir(p) else os.path.getsize(p)))
                self.finds = names
            if not getattr(self, 'finds', None):
                return fail(18)
            name, attr, size = self.finds.pop(0)
            rec = bytearray(43)
            rec[0x15] = attr
            struct.pack_into('<HHI', rec, 0x16, 0, ((1991 - 1980) << 9) | (12 << 5) | 6, size)
            rec[0x1e:0x1e + len(name)] = name.encode('ascii')
            uc.mem_write(dta, bytes(rec))
        elif ah == 0x36:                          # disk free
            w(UC_X86_REG_AX, 64)
            w(UC_X86_REG_BX, 4096)
            w(UC_X86_REG_CX, 512)
            w(UC_X86_REG_DX, 8192)
        elif ah == 0x4c or ah == 0x00:
            self.console.append(f'[exit {al}]')
            uc.emu_stop()
        else:
            self.console.append(f'[int21 ah={ah:02x}]')

    # ---------------------------------------------------------------- process start-up
    def boot(self, max_insns=2_000_000_000, stop_after_polls=2000):
        """Run from the EXE entry point like DOS would, until the game settles into input polling."""
        if not self.base:
            raise RuntimeError('boot() needs a load base (SimEmu(base=0x100))')
        uc, b = self.uc, self.base
        psp = b - 0x10
        env = 0x0080
        envdata = b'COMSPEC=C:\\COMMAND.COM\0PATH=C:\\\0\0\x01\0C:\\SIMANT\\SIMANT.EXE\0'
        uc.mem_write(env * 16, envdata)
        p = bytearray(256)
        p[0:2] = b'\xcd\x20'
        struct.pack_into('<H', p, 2, 0xA000)      # top of memory
        struct.pack_into('<H', p, 0x2c, env)
        p[0x80] = 0
        p[0x81] = 0x0d
        uc.mem_write(psp * 16, bytes(p))
        e = self.layout['entry']
        for reg, v in ((UC_X86_REG_DS, psp), (UC_X86_REG_ES, psp), (UC_X86_REG_SS, e['ss'] + b),
                       (UC_X86_REG_SP, e['sp']), (UC_X86_REG_CS, e['cs'] + b),
                       (UC_X86_REG_AX, 0), (UC_X86_REG_BX, 0), (UC_X86_REG_BP, 0)):
            uc.reg_write(reg, v)
        self.stop_after_polls = stop_after_polls
        start = (e['cs'] + b) * 16 + e['ip']
        try:
            uc.emu_start(start, 0xfffff, count=max_insns)
        except UcError as ex:
            cs, ip = uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)
            raise RuntimeError(f'emulation error {ex} at {cs:04x}:{ip:04x} (flat {cs - b:04x}:{ip:04x})')
        finally:
            self.stop_after_polls = None
        cs, ip = uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)
        # the game's own stack (SS == DGROUP, as MSC code requires); call() runs below the suspended frames
        self.call_ss = uc.reg_read(UC_X86_REG_SS)
        self.call_sp = (uc.reg_read(UC_X86_REG_SP) - 0x80) & 0xfffe
        return cs - b, ip

    # ---------------------------------------------------------------- address helpers
    _segs = None

    def seg_of(self, lin):
        """Correct code segment for a flat linear function address: overlay base, or the segment used
        by the program's own far calls (near calls inside a function are relative to it)."""
        for o in self.layout['overlays']:
            if o['base'] * 16 <= lin < o['base'] * 16 + o['size']:
                return o['base'], lin - o['base'] * 16
        if SimEmu._segs is None:
            import re
            segs, exact = set(), {}
            flat = open(os.path.join(HERE, 'build', 'flat.bin'), 'rb').read()
            for m in re.finditer(rb'\x9a(..)(..)', flat, re.S):
                off, seg = struct.unpack('<HH', m.group(1) + m.group(2))
                if seg * 16 + off < 0x31260:
                    segs.add(seg)
                    exact.setdefault(seg * 16 + off, seg)
            SimEmu._segs = (sorted(segs), exact)
        segs, exact = SimEmu._segs
        if lin in exact:
            return exact[lin], lin - exact[lin] * 16
        best = max(s for s in segs if s * 16 <= lin and lin - s * 16 < 0x10000)
        return best, lin - best * 16

    def call_lin(self, lin, args=(), max_insns=200_000_000):
        seg, off = self.seg_of(lin)
        return self.call(seg, off, args, max_insns)

    # ---------------------------------------------------------------- calls and memory (flat segments)
    def call(self, seg, off, args=(), max_insns=200_000_000):
        """Far-call flat seg:off with word args (cdecl, pushed right-to-left). Returns AX.
        MSC code assumes SS == DS == DGROUP (it addresses locals through DS), so the call runs on a stack
        inside DGROUP: the game's own stack after boot(), otherwise the top of DGROUP's free space."""
        uc = self.uc
        ss = getattr(self, 'call_ss', DGROUP + self.base)
        sp = getattr(self, 'call_sp', 0xa4e0)
        for a in reversed(args):
            sp -= 2
            uc.mem_write(ss * 16 + sp, struct.pack('<H', a & 0xffff))
        sp -= 4
        uc.mem_write(ss * 16 + sp, struct.pack('<HH', 0, RET_SEG))
        for reg, v in ((UC_X86_REG_SS, ss), (UC_X86_REG_SP, sp), (UC_X86_REG_DS, DGROUP + self.base),
                       (UC_X86_REG_ES, DGROUP + self.base), (UC_X86_REG_BP, 0)):
            uc.reg_write(reg, v)
        uc.reg_write(UC_X86_REG_CS, seg + self.base)
        try:
            # Unicorn 16-bit: start/until are linear addresses (CS must also be set)
            uc.emu_start((seg + self.base) * 16 + off, RET_SEG * 16 + 1, count=max_insns)
        except UcError as ex:
            cs, ip = uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)
            raise RuntimeError(f'emulation error {ex} at {cs:04x}:{ip:04x} (flat {cs - self.base:04x}:{ip:04x})')
        return uc.reg_read(UC_X86_REG_AX)

    def read(self, seg, off, n):
        return bytes(self.uc.mem_read((seg + self.base) * 16 + off, n))

    def write(self, seg, off, data):
        self.uc.mem_write((seg + self.base) * 16 + off, bytes(data))

    def w16(self, seg, off):
        return struct.unpack('<H', self.read(seg, off, 2))[0]

    def set16(self, seg, off, v):
        self.write(seg, off, struct.pack('<H', v & 0xffff))

    def sim_bytes(self):
        return self.read(SIM, 0, 0x10000)


def _rng_selftest():
    e = SimEmu()
    e.set16(DGROUP, 0x8ba2, 1)
    seq = [e.call(0x0093, 0x01ab) for _ in range(16)]
    x, ref = 1, []
    for _ in range(16):
        c = x & 0x8000
        x = (x << 1) & 0xffff
        if c:
            x ^= 0x1bf5
        ref.append(x & 7)
    print('Rand8 emulated vs reference:', 'match' if seq == ref else f'MISMATCH {seq} {ref}')


if __name__ == '__main__':
    _rng_selftest()
    e = SimEmu(base=0x100)
    try:
        where = e.boot()
        print('stopped at flat %04x:%04x' % where)
    except RuntimeError as ex:
        print(ex)
    print('console:', ''.join(e.console)[-600:])
    print('ints:', e.int_counts.most_common(25))
```
{% endraw %}
