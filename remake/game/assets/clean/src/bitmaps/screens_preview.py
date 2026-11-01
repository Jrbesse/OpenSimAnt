"""screens_preview: writes preview_screens.png (each picture assembled as the game shows it, at 2x on mid-grey)."""
import os

import numpy as np
from PIL import Image

import screens_lib as L
import screens_ab as AB
import screens_scenes as SC
import screens_ants as AN
from uilib import SMALL, Img, text, text_c

HERE = os.path.dirname(os.path.abspath(__file__))
PAL = [(255, 255, 255), (252, 243, 5), (255, 100, 2), (221, 8, 6), (242, 8, 132), (70, 0, 165), (0, 0, 212), (2, 171, 234),
       (31, 183, 20), (0, 100, 17), (86, 44, 5), (144, 113, 58), (192, 192, 192), (128, 128, 128), (64, 64, 64), (0, 0, 0)]
GREY = (110, 110, 110)


def to_im(a):
    return Image.fromarray(np.array(PAL, dtype=np.uint8)[a.astype(int)])


def arr(pics, pid):
    return pics[pid].arr()


def frame_box(a, t=1, c=15):
    h, w = a.shape
    o = np.full((h + 2 * t, w + 2 * t), c, dtype=np.int16)
    o[t:-t, t:-t] = a
    return o


def title_screen(pics):
    scr = np.full((480, 640), 15, dtype=np.int16)
    a, b = arr(pics, 2000), arr(pics, 2001)
    scr[63:63 + 172, 64:64 + 512] = a
    scr[235:235 + 200, 64:64 + 512] = b
    return scr


def hits(pics):
    a = arr(pics, 2500)
    im = to_im(a).convert('RGB')
    px = im.load()
    for name, r in AB.SEL.items():
        for x in range(r[0], r[2]):
            for y in (r[1], r[3] - 1):
                px[x, y] = (255, 0, 255)
        for y in range(r[1], r[3]):
            for x in (r[0], r[2] - 1):
                px[x, y] = (255, 0, 255)
    for name, z in AB.ZONES.items():
        for x in range(z[0], z[2]):
            for y in (z[1], z[3] - 1):
                px[x, y] = (0, 200, 200)
        for y in range(z[1], z[3]):
            for x in (z[0], z[2] - 1):
                px[x, y] = (0, 200, 200)
    return im


def about_variants(pics):
    bg = arr(pics, 3000).copy()
    card = arr(pics, 3001)
    v1 = bg.copy()
    v1[61:61 + 109, 33:33 + 254] = card
    v2 = bg.copy()
    v2[61:171, 33:287] = 12
    img = Img(320, 200)
    img.a = v2.copy()
    for i, s in enumerate(['Sample credit line one', 'Sample credit line two', 'Sample credit line three']):
        text_c(img, 160, 80 + 14 * i, s, SMALL, 15)
    return v1, img.a


def message_box(icon):
    w, h = 190, 100
    a = np.full((h, w), 12, dtype=np.int16)
    a[0, :] = 0
    a[:, 0] = 0
    a[-1, :] = 13
    a[:, -1] = 13
    a[1, 1:-1] = 0
    a[1:-1, 1] = 0
    a[-2, 1:-1] = 13
    a[1:-1, -2] = 13
    a[0, :] = 15
    a[-1, :] = 15
    a[:, 0] = 15
    a[:, -1] = 15
    a[2:34, 79:111] = icon[:32, :32] if icon.shape == (32, 32) else 12
    img = Img(w, h)
    img.a = a
    for i, s in enumerate(['The ant met a sad end,', 'which is a pity for it.', 'Try again with another.']):
        text_c(img, w // 2, 38 + 11 * i, s, SMALL, 15)
    text_c(img, w // 2, 85, 'Click here to continue', SMALL, 15)
    return img.a


def scene_window(pics, base_id, patches, caption=False):
    base = arr(pics, base_id).copy()
    for pid, (x, y) in patches:
        p = arr(pics, pid)
        base[y:y + p.shape[0], x:x + p.shape[1]] = p
    if caption:
        base[0:15, :] = 14
        img = Img(base.shape[1], base.shape[0])
        img.a = base
        text_c(img, base.shape[1] // 2, 3, 'SAMPLE CAPTION TEXT 24', SMALL, 1)
        base = img.a
    out = frame_box(base, 2, 15)
    return frame_box(out, 4, 12)


def make(pics):
    S = 2

    def up(a):
        im = to_im(a) if isinstance(a, np.ndarray) else a
        return im.resize((im.width * S, im.height * S), Image.NEAREST)

    sections = []
    # (1) the title as the game shows it (a 640 x 480 black screen), (2) Select a Game plain and with the hit
    # rectangles (magenta) and caption zones (cyan) outlined
    sections.append([up(title_screen(pics)), up(frame_box(arr(pics, 2500), 1, 15)), up(hits(pics))])
    # (3) the About box: with the card, and with the well filled with grey and sample credits
    v1, v2 = about_variants(pics)
    sections.append([up(frame_box(v1, 1, 15)), up(frame_box(v2, 1, 15))])
    # (4) message boxes with the seven icons
    sections.append([up(message_box(arr(pics, pid))) for pid in (9150, 9151, 9152, 9153, 9154, 9155, 9156)])
    # (5) the scenes in the scene window, each patch laid on its base in cycle order
    sections.append([
        up(scene_window(pics, 9100, [], caption=True)),
        up(scene_window(pics, 9101, [], caption=True)),
        up(scene_window(pics, 9110, [])),
        up(scene_window(pics, 9110, [(9111, (72, 62))])),
        up(scene_window(pics, 9200, [])),
        up(scene_window(pics, 9200, [(9201, (38, 39))])),
        up(scene_window(pics, 9200, [(9201, (38, 39)), (9202, (38, 52))])),
        up(scene_window(pics, 9200, [(9201, (38, 39)), (9203, (38, 52))])),
        up(scene_window(pics, 12000, [])),
        up(scene_window(pics, 12000, [(12002, (46, 77))])),
        up(scene_window(pics, 12000, [(12003, (46, 77))])),
        up(scene_window(pics, 12000, [(12001, (46, 77))])),
    ])
    W = 2600
    placed = []
    y = 12
    for sec in sections:
        x, rowh = 12, 0
        for im in sec:
            if x + im.width > W - 12:
                x, y, rowh = 12, y + rowh + 12, 0
            placed.append((im, x, y))
            x += im.width + 12
            rowh = max(rowh, im.height)
        y += rowh + 24
    sheet = Image.new('RGB', (W, y), GREY)
    for im, px, py in placed:
        sheet.paste(im, (px, py))
    sheet.save(os.path.join(HERE, 'preview_screens.png'))
