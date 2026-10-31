"""pics: the shared SUBJECTS of the UI bitmaps (each drawn once, reused wherever it appears): the surface, the nest
cut-away, ants (top view and side view), the queen, the spider, the five scent pictures, the alarm bulb, small
glyph pictures.  Every function returns an Img of the asked size; none draws a bevel (see pic_button)."""
import math
import random
from uilib import *

TAN, SOIL = 11, 10


def pic_button(W, H, content, frame=None):
    """A raised button of size WxH: optional 1-px coloured frame (colony colour), 1-px bevel, content inside."""
    o = Img(W, H, FACE)
    inset = 0
    if frame is not None:
        o.frame(0, 0, W, H, frame)
        inset = 1
    bevel(o, inset, inset, W - inset, H - inset, FACE)
    i = inset + 1
    c = content(W - 2 * i, H - 2 * i)
    o.blit(c, i, i)
    return o


# ---- ground, nest --------------------------------------------------------------------------------------------------
def surface(w, h, seed=3):
    o = Img(w, h, TAN)
    r = random.Random(seed)
    for _ in range(w * h // 14):          # soil grain
        o.px(r.randrange(w), r.randrange(h), SOIL)
    for _ in range(max(2, w * h // 90)):  # pebbles
        x, y = r.randrange(1, w - 2), r.randrange(1, h - 1)
        o.rect(x, y, x + 2, y + 1, 13)
        o.px(x, y, 12)
    o.ellipse(w * 0.72, h * 0.62, 2.2, 1.6, 15)  # a hole in the ground
    for _ in range(max(3, w * h // 60)):  # ants: black marks, a few red
        x, y = r.randrange(1, w - 1), r.randrange(1, h - 1)
        o.rect(x, y, x + 2, y + 1, 15)
    for _ in range(max(2, w * h // 160)):
        x, y = r.randrange(1, w - 2), r.randrange(1, h - 1)
        o.rect(x, y, x + 2, y + 1, 3)
        o.px(x, y + 1, 15)
    return o


def nest_cut(w, h):
    """Soil cut-away: tan soil, black tunnels (a shaft, two galleries, rooms), a green strip of grass on top."""
    o = Img(w, h, TAN)
    o.rect(0, 0, w, 2, 8)
    o.rect(0, 2, w, 3, 9)
    cx = w // 2
    o.rect(cx - 1, 2, cx + 1, h * 6 // 10, 15)
    y1, y2 = max(5, h * 4 // 10), max(8, h * 7 // 10)
    o.rect(max(1, cx - w // 3), y1, cx + 1, y1 + 2, 15)
    o.rect(cx - 1, y2, min(w - 1, cx + w // 3), y2 + 2, 15)
    o.rect(max(1, cx - w // 3) - 1, y1 - 1, max(1, cx - w // 3) + 2, y1 + 3, 15)
    o.rect(min(w - 1, cx + w // 3) - 2, y2 - 1, min(w - 1, cx + w // 3) + 1, y2 + 3, 15)
    r = random.Random(w * 7 + h)
    for _ in range(w * h // 16):
        x, y = r.randrange(w), r.randrange(4, h)
        if o.get(x, y) == TAN:
            o.px(x, y, SOIL)
    return o


# ---- ants ----------------------------------------------------------------------------------------------------------
def ant_top(o, cx, cy, body=15, outline=None, leg=15, s=1.0, bigabd=1.0):
    """Ant seen from above, head up.  (cx, cy) = centre of the thorax region."""
    def L(x0, y0, x1, y1):
        o.line(int(round(cx + x0 * s)), int(round(cy + y0 * s)), int(round(cx + x1 * s)), int(round(cy + y1 * s)), leg)
    for sx in (-1, 1):
        L(sx * 1, -2, sx * 5, -5)
        L(sx * 1, -1, sx * 6, -1)
        L(sx * 1, 0, sx * 5, 4)
        L(sx * 1, -5, sx * 3, -8)
    parts = [(0, -5, 1.7, 1.7), (0, -1.5, 1.7, 2.2), (0, 3.8 * 1, 2.4 * bigabd, 3.2 * bigabd)]
    for p in parts:
        o.ellipse_o(cx + p[0] * s, cy + p[1] * s, p[2] * s, p[3] * s, body, outline if outline is not None else body)


def ant_side(o, x0, y0, kind='worker', body=15):
    """Side view, facing right, in a 20 x 14 box at (x0, y0)."""
    P = {
        'worker':  dict(abd=(4.5, 8, 3.6, 2.8), thor=(10, 7, 2.2, 2.0), head=(15.2, 6.6, 2.6, 2.3)),
        'soldier': dict(abd=(4, 8, 3.4, 2.6), thor=(9.5, 7.5, 2.0, 1.8), head=(15, 6.5, 3.6, 3.4)),
        'male':    dict(abd=(4.5, 8, 3.8, 1.8), thor=(10, 7.5, 2.0, 1.8), head=(14.8, 7.2, 1.8, 1.7), wing=True),
        'newq':    dict(abd=(5, 8.5, 4.8, 3.4), thor=(11, 7.5, 2.8, 2.4), head=(15.8, 7.2, 2.4, 2.2), wing=True),
        'queen':   dict(abd=(7, 8, 6.8, 4.8), thor=(14.2, 7.5, 2.0, 1.8), head=(17.6, 7.2, 2.0, 1.9)),
    }[kind]
    if P.get('wing'):
        wx = 10 if kind == 'male' else 11
        for pts in ([(wx - 1, 5), (wx - 7, 0), (wx - 1, 0), (wx + 2, 5)], [(wx, 5), (wx - 4, 1), (wx + 3, 0), (wx + 4, 5)]):
            q = [(x0 + a, y0 + b) for a, b in pts]
            o.poly(q, 12)
            for a, b in zip(q, q[1:] + q[:1]):
                o.line(a[0], a[1], b[0], b[1], 13)
    for k in ('abd', 'thor', 'head'):
        c = P[k]
        o.ellipse(x0 + c[0], y0 + c[1], c[2], c[3], body)
    tx = P['thor'][0]
    for dx, ex in ((-1, -2), (0, 0), (1, 2)):  # legs
        o.line(int(x0 + tx + dx), int(y0 + 8), int(x0 + tx + ex * 1.5 + dx), y0 + 12, body)
    hc = P['head']
    o.line(int(x0 + hc[0] + hc[2] - 1), int(y0 + hc[1] - hc[3] + 1), int(x0 + hc[0] + hc[2] + 1), y0 + 2, body)
    if kind == 'soldier':
        o.line(int(x0 + hc[0] + hc[2]), int(y0 + hc[1] + 1), int(x0 + hc[0] + hc[2] + 1), int(y0 + hc[1] + 3), body)
    o.px(int(x0 + hc[0] + 1), int(y0 + hc[1] - 1), 0) if kind in ('soldier', 'queen') else None


def larva(o, x0, y0):
    cs = [(5, 8, 2.4), (7.5, 5.2, 2.6), (11.5, 4, 2.7), (15, 5.5, 2.6), (16.2, 9, 2.5), (14.2, 11.6, 2.3)]
    for cx, cy, r in cs:
        o.ellipse(x0 + cx, y0 + cy, r + 0.9, r + 0.9, 13)
    for cx, cy, r in cs:
        o.ellipse(x0 + cx, y0 + cy, r, r, 0)
    for cx, cy, r in cs[1:-1]:
        o.px(int(x0 + cx), int(y0 + cy - r + 1), 12)
        o.px(int(x0 + cx), int(y0 + cy + r - 1), 12)
    o.ellipse(x0 + 14.2, y0 + 11.6, 2.0, 2.0, 12)
    o.px(int(x0 + 14.8), int(y0 + 11.6), 15)


def spider_top(o, cx, cy, s=1.0, body=14):
    for sx in (-1, 1):
        for ang in (-50, -20, 15, 45):
            a = math.radians(ang)
            x1, y1 = sx * (3 + 5 * math.cos(a)) * s, (-4 + 8 * math.sin(a) * 1.0) * s
            o.line(int(cx + sx * 1.5 * s), int(cy), int(cx + x1 + sx * 2 * s), int(cy + y1), 15)
    o.ellipse_o(cx, cy + 2.2 * s, 2.6 * s, 3.2 * s, body, 15)
    o.ellipse_o(cx, cy - 1.6 * s, 1.8 * s, 1.7 * s, body, 15)


# ---- queens on brown soil --------------------------------------------------------------------------------------------
def queen_soil(w, h, colour):
    o = Img(w, h, SOIL)
    r = random.Random(11)
    for _ in range(w * h // 9):
        o.px(r.randrange(w), r.randrange(h), TAN if r.random() < .5 else 13)
    cx, cy = w / 2, h / 2 + 0.5
    ring = 12 if colour == 15 else 15
    o.ellipse(cx + 1.0, cy + 1, 5.9, 3.7, ring)      # light/dark rim so it reads on the soil
    o.ellipse(cx + 3.6, cy, 2.6, 2.4, ring)
    o.ellipse(cx - 2.2, cy + 0.8, 4.8, 3.3, colour)    # the big abdomen
    o.ellipse(cx + 2.6, cy, 1.9, 1.7, colour)
    o.ellipse(cx + 5.0, cy - 0.2, 1.7, 1.6, colour)
    o.line(int(cx + 2), int(cy + 2), int(cx + 1), int(cy + 4), colour)
    o.line(int(cx + 3), int(cy + 2), int(cx + 4), int(cy + 4), colour)
    return o


# ---- scents ------------------------------------------------------------------------------------------------------
def scent_nest(w, h, red):
    o = Img(w, h, TAN)
    col = 3 if red else 15
    ring = 3 if red else 14
    cx, cy = w / 2, h / 2
    for y in range(h):
        for x in range(w):
            d = math.hypot((x + .5 - cx) / (w * 0.42), (y + .5 - cy) / (h * 0.46))
            chk = (x + y) % 2 == 0
            if d < 0.30:
                o.px(x, y, col)
            elif d < 0.55:
                o.px(x, y, ring if (chk or d < 0.43) else TAN)
            elif d < 0.80 and chk:
                o.px(x, y, ring)
            elif d < 1.0 and (x % 2 == 0 and y % 2 == 0):
                o.px(x, y, ring)
    o.rect(int(cx) - 1, int(cy) - 1, int(cx) + 1, int(cy) + 1, 15)  # the nest entrance
    return o


def scent_trail(w, h, red):
    o = Img(w, h, TAN)
    col = 3 if red else 15
    for x in range(1, w - 1):
        y = h / 2 + (h * 0.28) * math.sin(x / w * 2 * math.pi * 1.4 + 0.6)
        yi = int(y)
        o.px(x, yi, col)
        o.px(x, yi + 1, col)
        if red:
            o.px(x, yi + 2, 15)
        if x % 5 == 0:
            o.px(x, yi - 2, col)
            o.px(x, yi + 3 if not red else yi + 4, col)
    return o


def alarm(w, h):
    o = Img(w, h, FACE)
    cx = w / 2
    tall = h > w * 1.4
    cy = h * 0.42 if tall else h / 2
    r = min(w, h) * (0.27 if tall else 0.30)
    r = max(r, 3.0)
    for k in range(8):                     # rays
        a = k * math.pi / 4
        x0, y0 = cx + math.cos(a) * (r + 1.8), cy + math.sin(a) * (r + 1.8)
        x1, y1 = cx + math.cos(a) * (r + 3.8), cy + math.sin(a) * (r + 3.8)
        o.line(int(x0), int(y0), int(x1), int(y1), 15)
    o.ellipse_o(cx, cy, r, r, 3, 15)
    o.px(int(cx - r / 3 - 1), int(cy - r / 3 - 1), 0)
    o.px(int(cx - r / 3), int(cy - r / 3 - 1), 0)
    o.px(int(cx - r / 3 - 1), int(cy - r / 3), 0)
    if tall:
        bx0, by0 = int(cx - 4), int(cy + r + 5)
        o.rect(bx0, by0, bx0 + 9, by0 + 4, 14)
        o.frame(bx0, by0, bx0 + 9, by0 + 4, 15)
        o.rect(bx0 + 2, by0 + 4, bx0 + 7, by0 + 8, 13)
        o.frame(bx0 + 2, by0 + 4, bx0 + 7, by0 + 8, 15)
    return o


def path_pic(w, h):
    """'Show trails': a dotted path across the ground, with a start dot and an end cross."""
    o = Img(w, h, TAN)
    for x in range(2, w - 3):
        y = int(h / 2 + (h * 0.26) * math.sin(x / w * 2 * math.pi * 1.2))
        if x % 3 != 2:
            o.px(x, y, 15)
            o.px(x, y + 1, 15)
    o.rect(1, int(h / 2) - 1, 4, int(h / 2) + 2, 3)
    o.line(w - 6, 2, w - 3, 5, 3)
    o.line(w - 3, 2, w - 6, 5, 3)
    return o


def graph_pic(w, h):
    o = Img(w, h, 0)
    o.hline(1, w - 1, h - 3, 15)
    o.vline(2, 1, h - 2, 15)
    pts = [(3, h - 5), (7, h - 8), (11, h - 6), (14, 3), (18, 5), (w - 3, 4)]
    for a, b in zip(pts, pts[1:]):
        o.line(a[0], a[1], b[0], b[1], 3)
    pts2 = [(3, h - 4), (8, h - 5), (12, h - 9), (16, h - 8), (w - 3, h - 11)]
    for a, b in zip(pts2, pts2[1:]):
        o.line(a[0], a[1], b[0], b[1], 15)
    return o


def house_yard(w, h):
    """The yard: a house with a red roof on a lawn, white sky."""
    o = Img(w, h, 0)
    gy = h * 3 // 5
    o.rect(0, gy, w, h, 8)
    o.hline(0, w, gy, 9)
    hx0, hx1 = w // 6, w // 6 + w // 2
    o.rect(hx0, gy - h // 3, hx1, gy + 1, 11)
    o.frame(hx0, gy - h // 3, hx1, gy + 1, 15)
    roof = [(hx0 - 2, gy - h // 3), ((hx0 + hx1) // 2, 1), (hx1 + 2, gy - h // 3)]
    o.poly(roof, 3)
    for a, b in zip(roof, roof[1:] + roof[:1]):
        o.line(a[0], a[1], b[0], b[1], 15)
    o.rect((hx0 + hx1) // 2 - 1, gy - 4, (hx0 + hx1) // 2 + 2, gy + 1, 15)  # door
    o.rect(hx0 + 2, gy - h // 3 + 3, hx0 + 5, gy - h // 3 + 6, 7)           # window
    o.px(w - 5, 3, 1)
    o.rect(w - 6, 2, w - 3, 5, 1)                                            # sun
    for x in range(1, w - 1, 4):                                             # blades of the lawn
        o.px(x, gy + 2, 9)
    return o


def card_pic(w, h):
    """'Ant info': a card with text lines and a small ant."""
    o = Img(w, h, 0)
    o.frame(0, 0, w, h, 15)
    o.line(2, 2, 2, 2, 15)
    ant_top(o, 5, 7, 15, None, 15, 0.55)
    for i, y in enumerate((3, 6, 9, 12)):
        o.hline(9 if i < 2 else 2, w - 2 if i != 1 else w - 5, y, 14)
    return o


def glyph_pic(w, h, ch, color, bg=FACE, face=LABEL, scale=2):
    o = Img(w, h, bg)
    text_c(o, w // 2, (h - face.cap * scale) // 2, ch, face, color, scale)
    return o
