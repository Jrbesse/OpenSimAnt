# Spec: the spider's legs and fangs

Output folder: `remake/game/assets/clean/src/spider/`. Provenance file: `remake/game/assets/clean/PROVENANCE.md`.
Format: one JSON file, `legs.json` (below). Written as a hand-made list of numbers, or by a script kept beside it
(`make_legs.py`, which makes the file so it can be regenerated, plus a short `README.md` on the design).

## What it is

The big hunting spider that walks the yard's surface map, seen from straight above; the player can be it. Its
**body** (head and thorax in front, a larger round abdomen behind) is a sprite, made by another spec, one per heading.
The **8 legs** and the **2 fangs** are not sprites: the game draws them over the body every time the spider is redrawn,
as **1-pixel straight lines** (a line from point to point, no anti-aliasing, no fill), so the legs can bend, step and
change with the heading. This file holds the points those lines run through. The legs are drawn in black (palette
index 15). The fangs are black too, and yellow (index 1) while the player is the spider.

## Headings, frames, sides

- **Headings**: 8, clockwise from the top of the screen: north, north-east, east, south-east, south, south-west, west,
  north-west. The file holds only **two views**, `north` and `north_east`: the game makes the other six itself. East,
  south and west are the north view turned a quarter turn, a half turn and three quarters clockwise; south-east,
  south-west and north-west are the north-east view flipped (south-east: upside down; north-west: left to right;
  south-west: both). So the `north` drawing must look right turned, and the `north_east` drawing must look right when
  flipped, which holds for any plain drawing.
- **Which side**: a view is drawn for the spider's **right-hand side** (in `north`: the right of the picture, x > 0; in
  `north_east`: the lower right, the side towards the bottom right of the picture). The left-hand side is made by the
  game as the **mirror image** across the spider's own axis (`north`: left-right; `north_east`: across its diagonal).
- **Leg frames**: the walk cycle has **8 frames**, numbered 0..7. The right-hand legs are drawn in frame f, the
  left-hand legs in frame f + 4 (mirrored), so the two sides are always half a cycle apart: an **alternating gait**.
  The cycle moves on **one frame per step** the spider takes (a step is one game tick, about 3 to 8 a second depending
  on the game speed; a sprint takes **two frames per step**, so frames 0, 2, 4, 6 alone, and 1, 3, 5, 7 alone, must
  also read as a walk). Walking backwards plays the frames backwards. A resting spider holds one fixed frame. Frame 7
  must lead smoothly back into frame 0.
- **Fang frames**: 4, numbered 0..3. Frame 0 is the fangs at rest, the one shown while the spider is merely walking.
  While the spider hunts, eats, or is angry, the game picks one of the four frames at random each redraw, so frames
  1..3 are three different strike poses (opening, snapping, closing) that must each look right on their own and
  flicker convincingly in any order. Both fangs use the same frame, mirrored.

## Coordinates

Pixels, integers, **relative to the spider's centre**: x grows to the right, y grows **down**. In the `north` view the
centre is the middle of the thorax; the body sprite reaches 6 pixels left of it, 7 to the right, 10 above it (the front
edge of the head) and 25 below it (the back of the abdomen), 14 x 36 in all. In the other headings the body is turned
the same way. Each leg line and fang line is a **polyline of exactly 3 points**: two straight segments.

- **Legs**: 4 per side (8 in all), each in each of the 8 frames `[attach, joint, tip]`. `attach` is where the leg leaves
  the body: it must lie on or just inside the thorax's side edge (so the leg appears to start at the body), and it is
  **the same in all 8 frames** (the body does not move). `joint` is the knee, `tip` the foot. In `north` the 4 legs go
  from front to back: the front leg first, the hind leg last, attach points in that order down the thorax. In
  `north_east` the same four, ordered from the front leg to the hind leg again (the first attached nearest the head).
  A spider's legs reach well beyond its body: front legs forward and out, hind legs backward and out, the middle pairs
  to the side; the foot goes through a step (forward on the ground, lifted, back) over the 8 frames.
- **Fangs**: 2 (one per side of the head, mirrored), each frame `[base, p1, p2]`. The `base` is **fixed by the game**
  and must be written exactly: `[4, -10]` in `north` and `[10, -3]` in `north_east` (a point on the front edge of the
  head, so the body sprite's front edge must pass there); the build refuses any other. `p1` and `p2` are the jaw:
  base to `p1` to `p2`, so the pair can open (the jaws spread apart), close (together, crossing at most) and snap.
- **Limits**: every coordinate an integer within **+-48** (the surface map redraws a block of 7 x 7 cells of 16 pixels
  around the spider, so nothing may reach further than 48 pixels from the centre). Two consecutive points of a
  polyline must differ (a line has a length). A leg should not be longer than about 45 pixels in all and most of the
  motion should fall inside +-40.

## The file: `legs.json`

```
{
 "north":      { "legs": [ leg0, leg1, leg2, leg3 ], "fangs": [ f0, f1, f2, f3 ] },
 "north_east": { "legs": [ ... ], "fangs": [ ... ] }
}
```

`legs` is 4 legs; a leg is a list of 8 frames; a frame is `[[ax, ay], [jx, jy], [tx, ty]]` (attach, joint, tip);
`fangs` is 4 frames, each `[[bx, by], [p1x, p1y], [p2x, p2y]]`. Nothing else, no other keys. `build.py` turns it into
`EXE/spiderlegs.bin`, 304 bytes (the game needs exactly that size: it is a table of signed bytes that is read in place),
and refuses a file with the wrong counts, a coordinate out of range or not an integer, a leg whose attach point moves
between frames, a fang that does not start at its fixed base, or a polyline whose neighbouring points are equal.

## What must read clearly

A spider with **eight** distinct legs, four a side, that do not cross each other on the same side; a stepping, crawling
motion with the two sides alternating (when one side's front leg reaches forward, the other side's is pulling back); the
legs thin lines that clearly belong to the body in every heading; fangs that clearly open and close, small beside the
legs. Check the drawing yourself on all 8 headings by drawing the six derived views as the game does, on the brown and
green background of the map, with the body sprite; keep it plain, black lines, no other colours. Design it yourself;
do not copy a particular game's spider.
