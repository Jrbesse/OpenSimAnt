# Spider legs and fangs

Made from the spec `docs/clean_pack/spider_legs.md` only. `make_legs.py` writes `legs.json` (the points of
the legs and fangs, in the spec's format) and `preview.png` (the 8 frames of both views drawn as 1-pixel black
lines on a light background, enlarged 4x, with a grey ellipse where the body goes: 14 x 36, centred on the
thorax). It needs Pillow (it always writes `preview.png` at the end of `main()`, with no fallback), so run it with
an interpreter that has the pair from `../requirements.txt`; on the Hermes box that venv is `~/work/simant-venv`,
so the run there is `~/work/simant-venv/bin/python make_legs.py`.

- The file holds the right-hand side only; the game mirrors the left, half a cycle on.
- Each right-hand leg is two segments, attach -> joint -> tip. The attach points are on the thorax's side edge
  (x = 5, y = -6, -2, 2, 6: front to back) and never move. The foot's rest direction and reach (`angle`, `reach`)
  give each leg its place; the knee is solved by two-bone inverse kinematics with a fixed bend side (`sigma`).
- The walk: each foot slides forward and back along the body for 4 frames on the ground (stance), then is lifted
  (drawn pulled in towards the body) and swings forward for 4 frames. Legs 0 and 2 step together, legs 1 and 3
  half a cycle apart, so neighbours alternate and the two sides are half a cycle apart. Frame 7 leads into frame 0.
  Every second frame (a sprint) still cycles through all four phases.
- The north_east view is the north view turned 45 degrees clockwise (body and legs), so its right-hand side is the
  lower right, as the spec asks. The fang bases are the fixed ones (`[4, -10]`, `[10, -3]`).
- The fangs: frame 0 folded at rest, 1 open (the jaws spread), 2 snapped shut, reaching forward, 3 half-closing.
  The north_east fangs are the north fangs turned the same way.
- The script asserts the spec's limits and rules (counts, integers, +-48 and the +-40 target, distinct neighbouring
  points, fixed attach points, leg length <= 45, attach on the thorax edge, legs in order, no crossing legs in any
  frame of either side, legs 2.5 px apart, legs 2 px clear of the fangs, fang bases, fangs not crossing, the walk's
  smoothness and phase relations) before it writes anything.
