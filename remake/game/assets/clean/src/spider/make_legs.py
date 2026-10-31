"""Makes legs.json: the spider's 8 legs and 2 fangs, as docs/clean_pack/spider_legs.md describes.

    python make_legs.py    # writes legs.json and preview.png next to this script

The file holds the spider's right-hand side only (the game mirrors the left). Each right-hand leg is a two-bone
leg, attach -> joint -> tip, whose foot walks over the 8 frames (README.md has the design). The north_east view
is the north view turned 45 degrees clockwise, body and legs together; the fang bases are the spec's fixed ones.
Every limit and rule of the spec is asserted before anything is written.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = math.sqrt(2.0)
FRAMES = 8
FANG_FRAMES = 4
LIMIT = 48            # every coordinate within +-48 (the map redraws 7 x 7 cells of 16 px around the spider)
SOFT = 40             # the motion stays inside +-40
MAX_LEG = 45          # a leg is about 45 px at most, in all
EDGE = 6              # the thorax's side edge: attach points lie on or just inside it
LIFT = 3.0            # a lifted foot is pulled in towards the body by this much at mid-swing

NORTH_BASE = (4, -10)     # fixed by the game (the front edge of the head)
NE_BASE = (10, -3)        # fixed by the game

# The four right-hand legs, front to back. attach: where the leg leaves the thorax (the same in every frame).
# angle: the direction of the foot's rest position from the attach point (0 = right, 90 = down the picture =
# back of the spider, -90 = up = forward). reach: the rest distance. l1, l2: the two segments. stride: how far
# the foot slides forward and back along the body. group: 0 or 1, the two alternating groups (legs 0 and 2 in
# one, 1 and 3 in the other: neighbours are half a cycle apart, and so are the two sides of each leg).
# sigma: which side of its own chord the knee bends to (+1 or -1), fixed for all frames so the knee never flips.
# The angles and knee sides were chosen by a search for layouts where no two legs cross in any frame and the
# joints and tips keep 2.5 px or more apart (probe in the scratchpad, not kept).
LEGS = [
    dict(attach=(5, -6), angle=-45, reach=25, l1=16, l2=16, stride=6, group=0, sigma=-1),
    dict(attach=(5, -2), angle=-10, reach=27, l1=15, l2=16, stride=6, group=1, sigma=-1),
    dict(attach=(5, 2), angle=25, reach=26, l1=15, l2=16, stride=6, group=0, sigma=-1),
    dict(attach=(5, 6), angle=75, reach=22, l1=15, l2=16, stride=5, group=1, sigma=-1),
]

# The right-hand fang, north view: [base, p1, p2] per frame. 0 at rest (folded under the head); 1 open (the
# jaws spread out and forward); 2 snap (shut, reaching forward, the tips meeting at the middle); 3 closing.
FANGS_NORTH = [
    [[4, -10], [3, -12], [2, -11]],
    [[4, -10], [7, -13], [9, -16]],
    [[4, -10], [4, -14], [1, -15]],
    [[4, -10], [5, -13], [2, -16]],
]


def rnd(v):
    return int(math.floor(v + 0.5))


def turn(p):
    """North -> north_east: the picture turned 45 degrees clockwise (y down). Up goes up-right, right goes
    down-right, so the spider's right-hand side is the lower right, as the spec requires."""
    x, y = p
    return ((x - y) / R2, (x + y) / R2)


def mirror_north(p):
    return (-p[0], p[1])


def mirror_ne(p):
    return (-p[1], -p[0])


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def stride_state(phase):
    """(forward position in strides, lift 0..1) of a foot at a phase 0..1 of one step. Half the cycle is a
    stance (on the ground, sliding back from forward to back); the other half a swing (lifted, back to forward).
    The phase half a cycle on gives the same position reversed: the two groups always mirror each other."""
    s = phase % 1.0
    if s < 0.5:
        return 1.0 - 4.0 * s, 0.0
    u = (s - 0.5) * 2.0
    return -1.0 + 2.0 * u, math.sin(math.pi * u)


def group_phase(leg, f):
    return (f + 4 * leg["group"]) / FRAMES


def rest_foot(leg):
    a = math.radians(leg["angle"])
    ax, ay = leg["attach"]
    return (ax + leg["reach"] * math.cos(a), ay + leg["reach"] * math.sin(a))


def foot(leg, f):
    fwd, lift = stride_state(group_phase(leg, f))
    rx, ry = rest_foot(leg)
    ax, ay = leg["attach"]
    x, y = rx, ry - fwd * leg["stride"]            # forward is up the picture (smaller y)
    dx, dy = rx - ax, ry - ay
    d = math.hypot(dx, dy)
    x -= LIFT * lift * dx / d                       # a lifted foot is drawn pulled in
    y -= LIFT * lift * dy / d
    return (x, y)


def knee(leg, tip, sigma):
    """Two-bone inverse kinematics: the joint at distance l1 from the attach point and l2 from the tip.
    sigma (+1 or -1) picks the side of the chord the knee lies on; it is fixed per leg, so the knee never flips."""
    ax, ay = leg["attach"]
    l1, l2 = leg["l1"], leg["l2"]
    vx, vy = tip[0] - ax, tip[1] - ay
    d = math.hypot(vx, vy)
    ux, uy = vx / d, vy / d
    dc = min(max(d, abs(l1 - l2) + 0.01), l1 + l2 - 0.01)
    a = (l1 * l1 - l2 * l2 + dc * dc) / (2 * dc)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    px, py = ax + a * ux, ay + a * uy
    return (px + sigma * h * -uy, py + sigma * h * ux)


def north_legs():
    out = []
    for leg in LEGS:
        sig = leg["sigma"]
        ax, ay = leg["attach"]
        frames = []
        for f in range(FRAMES):
            tip = foot(leg, f)
            jt = knee(leg, tip, sig)
            frames.append([[ax, ay], [rnd(jt[0]), rnd(jt[1])], [rnd(tip[0]), rnd(tip[1])]])
        out.append(frames)
    return out


def turn_points(pts):
    return [[rnd(turn(p)[0]), rnd(turn(p)[1])] for p in pts]


def ne_legs(nlegs):
    return [[turn_points(fr) for fr in leg] for leg in nlegs]


def turn_fang(fr):
    """Each fang point turned about the north base, then moved to the north_east base (so the base is exact)."""
    out = []
    for p in fr:
        ox, oy = p[0] - NORTH_BASE[0], p[1] - NORTH_BASE[1]
        X, Y = (ox - oy) / R2, (ox + oy) / R2
        out.append([NE_BASE[0] + rnd(X), NE_BASE[1] + rnd(Y)])
    return out


def ne_fangs():
    return [turn_fang(fr) for fr in FANGS_NORTH]


# ---------------------------------------------------------------------------
# checks

def seg_cross(p1, p2, p3, p4):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(p3, p4, p1), orient(p3, p4, p2)
    d3, d4 = orient(p1, p2, p3), orient(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and d1 != 0 and d2 != 0 and ((d3 > 0) != (d4 > 0)) and d3 != 0 and d4 != 0


def polyline_cross(a, b):
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            if seg_cross(a[i], a[i + 1], b[j], b[j + 1]):
                return True
    return False


def picture(legs, mirror, f):
    """The 8 leg polylines as the game draws them in frame f: right legs in frame f, left legs = mirror of
    frame f + 4."""
    polys = []
    for li, leg in enumerate(legs):
        polys.append(((li, "R"), [tuple(p) for p in leg[f]]))
        polys.append(((li, "L"), [mirror(tuple(p)) for p in leg[(f + 4) % FRAMES]]))
    return polys


def check_view(name, view, base, mirror):
    legs, fangs = view["legs"], view["fangs"]
    assert len(legs) == 4, name + ": legs"
    assert len(fangs) == FANG_FRAMES, name + ": fangs"
    for li, leg in enumerate(legs):
        assert len(leg) == FRAMES, (name, li)
        attach = leg[0][0]
        leg_obj = LEGS[li]
        for f, fr in enumerate(leg):
            assert len(fr) == 3 and all(len(p) == 2 for p in fr), (name, li, f)
            for p in fr:
                for v in p:
                    assert type(v) is int and abs(v) <= LIMIT, (name, li, f, p)
                assert abs(p[0]) <= SOFT and abs(p[1]) <= SOFT, (name, li, f, p)
            assert fr[0] != fr[1] and fr[1] != fr[2], (name, li, f, "equal neighbours")
            assert fr[0] == attach, (name, li, f, "attach moves")
            length = dist(fr[0], fr[1]) + dist(fr[1], fr[2])
            assert length <= MAX_LEG, (name, li, f, length)
            reach = dist(fr[0], fr[2])
            assert abs(leg_obj["l1"] - leg_obj["l2"]) + 0.5 <= reach <= leg_obj["l1"] + leg_obj["l2"] - 0.5, (name, li, f, reach)
        # the attach point lies on or just inside the thorax's side edge
        if name == "north":
            assert 3 <= attach[0] <= EDGE and -8 <= attach[1] <= 6, (name, li, attach)
        else:
            perp = (attach[0] + attach[1]) / R2
            assert 3 <= perp <= EDGE + 0.5, (name, li, attach, perp)
    # legs run front to back: the first attached nearest the head
    if name == "north":
        ys = [leg[0][0][1] for leg in legs]
        assert ys == sorted(ys) and len(set(ys)) == 4, ("north order", ys)
    else:
        ax = [(leg[0][0][0] - leg[0][0][1]) / R2 for leg in legs]
        assert ax == sorted(ax, reverse=True) and len(set(ax)) == 4, ("north_east order", ax)

    # the 8 frames of the whole picture: no two legs cross, and the legs keep apart
    worst = 1e9
    for f in range(FRAMES):
        polys = picture(legs, mirror, f)
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                (ka, pa), (kb, pb) = polys[i], polys[j]
                if ka == kb:
                    continue
                assert not polyline_cross(pa, pb), (name, "legs cross", f, ka, kb)
                for p in pa[1:]:                  # the attach points sit on the body, 3 px apart
                    for q in pb[1:]:
                        worst = min(worst, dist(p, q))
    assert worst >= 2.5, (name, "legs too close", worst)

    # the walk: each foot moves smoothly round the cycle, also in the sprint (every second frame)
    for li, leg in enumerate(legs):
        tips = [fr[2] for fr in leg]
        st = LEGS[li]["stride"]
        for f in range(FRAMES):
            assert dist(tips[f], tips[(f + 1) % FRAMES]) <= st + 2 * LIFT + 2, (name, li, f)
            assert dist(tips[f], tips[(f + 2) % FRAMES]) <= 2 * st + 2 * LIFT + 2, (name, li, f, "sprint")
        assert len({tuple(t) for t in tips}) == FRAMES, (name, li, "feet repeat")
    # neighbours half a cycle apart, and each leg's other side half a cycle on
    for f in range(FRAMES):
        fw = [stride_state(group_phase(leg, f))[0] for leg in LEGS]
        for k in range(3):
            assert abs(fw[k] + fw[k + 1]) < 1e-9, (name, "neighbours in phase", f, k)
        for leg in LEGS:
            a = stride_state(group_phase(leg, f))[0]
            b = stride_state(group_phase(leg, f + 4))[0]
            assert abs(a + b) < 1e-9, (name, "sides not alternating", f)

    # fangs: fixed base, real segments, the two fangs do not cross (they may meet at the middle)
    fang_worst = 1e9
    for f, fr in enumerate(fangs):
        assert len(fr) == 3 and list(fr[0]) == list(base), (name, "fang base", f, fr[0], base)
        for p in fr:
            for v in p:
                assert type(v) is int and abs(v) <= LIMIT
        assert fr[0] != fr[1] and fr[1] != fr[2], (name, "fang", f)
        assert dist(fr[0], fr[1]) + dist(fr[1], fr[2]) <= 16, (name, "fang too long", f)
        right = [tuple(p) for p in fr]
        left = [mirror(tuple(p)) for p in fr]
        assert not polyline_cross(right, left), (name, "fangs cross", f)
        for p in right:
            for q in left:
                fang_worst = min(fang_worst, dist(p, q))
    # the legs keep clear of the fangs (joints and tips against both fangs, all frames)
    for f in range(FRAMES):
        fr = fangs[f % FANG_FRAMES]
        both = [tuple(q) for q in fr] + [mirror(tuple(q)) for q in fr]
        for _, poly in picture(legs, mirror, f):
            for p in poly[1:]:
                for q in both:
                    assert dist(p, q) >= 2, (name, "leg touches a fang", f, p, q)
    return worst, fang_worst


# ---------------------------------------------------------------------------
# preview

def body_outline(view):
    pts = []
    for i in range(72):
        t = 2 * math.pi * i / 72
        p = (0.5 + 6.5 * math.cos(t), 7.5 + 17.5 * math.sin(t))   # the body's 14 x 36 box
        pts.append(turn(p) if view == "north_east" else p)
    return pts


def draw_preview(path, data):
    from PIL import Image, ImageDraw
    W, C, S, PAD = 89, 44, 4, 8
    BG, BODY, INK = (236, 234, 222), (150, 150, 150), (0, 0, 0)
    rows = [("north", 0), ("north", 4), ("north_east", 0), ("north_east", 4)]
    big = Image.new("RGB", (4 * W * S + 5 * PAD, 4 * W * S + 5 * PAD), (255, 255, 255))
    for ri, (view, f0) in enumerate(rows):
        v = data[view]
        mirror = mirror_north if view == "north" else mirror_ne
        for ci in range(4):
            f = f0 + ci
            img = Image.new("RGB", (W, W), BG)
            d = ImageDraw.Draw(img)
            d.polygon([(x + C, y + C) for x, y in body_outline(view)], fill=BODY)
            polys = []
            for leg in v["legs"]:
                polys.append([tuple(p) for p in leg[f]])
                polys.append([mirror(tuple(p)) for p in leg[(f + 4) % FRAMES]])
            for poly in polys:
                d.line([(x + C, y + C) for x, y in poly], fill=INK, width=1)
            fang = v["fangs"][f % FANG_FRAMES]
            for poly in ([tuple(p) for p in fang], [mirror(tuple(p)) for p in fang]):
                d.line([(x + C, y + C) for x, y in poly], fill=INK, width=1)
            img = img.resize((W * S, W * S), Image.NEAREST)
            big.paste(img, (PAD + ci * (W * S + PAD), PAD + ri * (W * S + PAD)))
    big.save(path)


# ---------------------------------------------------------------------------

def build():
    nl = north_legs()
    data = {
        "north": {"legs": nl, "fangs": FANGS_NORTH},
        "north_east": {"legs": ne_legs(nl), "fangs": ne_fangs()},
    }
    return data


def text(data):
    out = ["{"]
    names = ["north", "north_east"]
    for vi, name in enumerate(names):
        view = data[name]
        out.append(' "%s": {' % name)
        out.append('  "legs": [')
        for li, leg in enumerate(view["legs"]):
            frames = ",\n    ".join(json.dumps(fr, separators=(",", ":")) for fr in leg)
            out.append("   [" + frames + "]" + ("," if li < 3 else ""))
        out.append('  ],')
        out.append('  "fangs": [' + ",\n   ".join(json.dumps(fr, separators=(",", ":")) for fr in view["fangs"]) + "]")
        out.append(" }" + ("," if vi == 0 else ""))
    out.append("}")
    return "\n".join(out) + "\n"


def main():
    data = build()
    wn, fn = check_view("north", data["north"], NORTH_BASE, mirror_north)
    wne, fne = check_view("north_east", data["north_east"], NE_BASE, mirror_ne)
    txt = text(data)
    assert json.loads(txt) == data, "text does not round-trip"
    assert set(json.loads(txt).keys()) == {"north", "north_east"}
    assert set(json.loads(txt)["north"].keys()) == {"legs", "fangs"}
    with open(os.path.join(HERE, "legs.json"), "w", newline="\n") as f:
        f.write(txt)
    draw_preview(os.path.join(HERE, "preview.png"), data)
    print("legs.json and preview.png written; all asserts passed")
    print("nearest leg points of different legs: north %.1f, north_east %.1f; nearest fang points: north %.1f, north_east %.1f"
          % (wn, wne, fn, fne))


if __name__ == "__main__":
    main()
