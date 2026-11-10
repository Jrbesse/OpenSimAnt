"""Decode SHARED type 11 resources: the game's bitmap fonts.

python fonts.py [out.png]       write a sample sheet of the four fonts

Fonts 0 and 1, the game's own format (little-endian; characters in the PC code page, 1 is the smiley):
  +0 u16 (0xF9 / 0xFA), +2 u16 height (rows), +4 u16 first character
  +6        255 x u16: glyph offset per character - first
  +0x204    255 x u16: 0 / 1 per character (not decoded)
  +0x402    255 x u16: advance width
  +0x600..  glyphs: height rows of (offset step / height) bytes, most significant bit leftmost
Fonts 2 and 3, Apple FONT / NFNT (big-endian): fontType, firstChar, lastChar, widMax, kernMax, nDescent,
  fRectWidth, fRectHeight, owTLoc, ascent, descent, leading, rowWords; then the strike (rowWords * 2 bytes
  x fRectHeight rows), the location table (lastChar - firstChar + 3 words) and the offset / width table
  (at 16 + owTLoc * 2; per char high byte offset, low byte width, 0xFFFF missing).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FONTS = os.path.join(HERE, '..', 'extracted', 'shared', 'font')


class Font:
    def __init__(self, fid):
        b = open(os.path.join(FONTS, f'{fid:05d}.bin'), 'rb').read()
        self.data = b
        self.mac = b[0] & 0xf0 == 0x90 and b[1] in (0, 1)       # FONT fontType 0x90xx, big-endian
        if self.mac:
            (self.ftype, self.first, self.last, self.widmax, self.kernmax, self.ndescent, self.frw, self.height,
             owtloc, self.ascent, self.descent, self.leading, rowwords) = struct.unpack_from('>13h', b, 0)
            self.rowbytes = rowwords * 2
            self.strike = 26
            n = self.last - self.first + 3
            self.loc = struct.unpack_from(f'>{n}H', b, 26 + self.rowbytes * self.height)
            self.ow = struct.unpack_from(f'>{n}H', b, 16 + owtloc * 2)
        else:
            _, self.height, self.first = struct.unpack_from('<3H', b, 0)
            self.offs = struct.unpack_from('<255H', b, 6)
            self.flag = struct.unpack_from('<255H', b, 0x204)
            self.adv_ = struct.unpack_from('<255H', b, 0x402)
            steps = [d for d in (self.offs[i + 1] - self.offs[i] for i in range(254)) if d > 0]
            self.bpr = min(steps) // self.height if steps else 1

    def advance(self, c):
        if self.mac:
            k = c - self.first
            if not 0 <= k <= self.last - self.first or self.ow[k] == 0xffff:
                return 0
            return self.ow[k] & 0xff
        k = c - self.first
        return self.adv_[k] if 0 <= k < 255 else 0

    def glyph(self, c):
        """(x offset, rows of 0 / 1)."""
        if self.mac:
            k = c - self.first
            if not 0 <= k <= self.last - self.first or self.ow[k] == 0xffff:
                return 0, []
            x0, x1 = self.loc[k], self.loc[k + 1]
            rows = []
            for y in range(self.height):
                row = self.data[self.strike + y * self.rowbytes: self.strike + (y + 1) * self.rowbytes]
                rows.append([(row[x >> 3] >> (7 - (x & 7))) & 1 for x in range(x0, x1)])
            return (self.ow[k] >> 8) + self.kernmax, rows
        k = c - self.first
        if not 0 <= k < 255:
            return 0, []
        o = self.offs[k]
        rows = []
        for y in range(self.height):
            bits = int.from_bytes(self.data[o + y * self.bpr: o + (y + 1) * self.bpr], 'big')
            n = self.bpr * 8
            rows.append([(bits >> (n - 1 - x)) & 1 for x in range(n)])
        return 0, rows

    def width(self, text):
        return sum(self.advance(ord(ch)) for ch in text)

    def draw(self, img, x, y, text, rgb):
        """Draw `text` with its top-left at (x, y); returns the pen's x after it."""
        for ch in text:
            c = ord(ch)
            dx, rows = self.glyph(c)
            for yy, row in enumerate(rows):
                for xx, on in enumerate(row):
                    if on and 0 <= y + yy < len(img) and 0 <= x + dx + xx < len(img[0]):
                        img[y + yy][x + dx + xx] = rgb
            x += self.advance(c)
        return x


def main():
    from png import write_png
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'extracted', 'render', 'fonts.png')
    lines = ['The quick brown fox jumps over 13 lazy ants!', 'BEHAVIOR CONTROL  Caste Control  %d%%',
             ''.join(chr(c) for c in range(1, 64)), ''.join(chr(c) for c in range(64, 128))]
    fonts = [Font(i) for i in range(4)]
    h = sum((f.height + 2) * len(lines) + 6 for f in fonts)
    img = [[(255, 255, 255, 255)] * 720 for _ in range(h)]
    y = 2
    for i, f in enumerate(fonts):
        for line in lines:
            f.draw(img, 4, y, line, (0, 0, 0, 255))
            y += f.height + 2
        y += 6
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_png(out, 720, h, img)
    for i, f in enumerate(fonts):
        print(f'font {i}: {"Apple FONT" if f.mac else "PC"}, height {f.height}, advance of "A" {f.advance(65)}')
    print('wrote', out)


if __name__ == '__main__':
    main()
