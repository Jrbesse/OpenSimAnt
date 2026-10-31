# Provenance of the clean pack

Every asset in `src/` was made new from a written spec in `docs/clean_pack/`, by a maker who did not see the
original game's files (docs/ART_PLAN.md sections 2 and 9). Each batch adds an entry: date, maker, spec (file and
commit), the files made, and the script that makes them (kept beside them, so every asset can be regenerated).

| Date | Maker | Spec | Files | Made by |
|---|---|---|---|---|
| 2026-10-30 | agent (isolated, spec only) | docs/clean_pack/cursors.md @ 10f6736 | src/cursors/0.pix, 1.pix | src/cursors/make_cursors.py |
| 2026-10-30 | agent (isolated, spec only) | docs/clean_pack/map_tiles.md @ 80a3c2c (yard sheet) | src/tiles/yard.pix | src/tiles/make_yard.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/map_tiles.md @ 0c6e3f7 (house sheet) | src/tiles/house.pix, src/tiles/preview_house.png, src/tiles/mockup_house.png | src/tiles/make_house.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/ant_sprites.md @ 0c6e3f7 | src/sprites/surface.pix, nest.pix, surface_recolour.pix, nest_recolour.pix, preview.png, README.md | src/sprites/make_sprites.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/map_tiles.md, ant_sprites.md as revised in the commit adding this row (light tunnels) | src/tiles/yard.pix, preview.png, mockup.png, README.md (tunnel tiles 0x90..0x97 light grey 12; walls, food, hole, plug, shaft follow); src/sprites/nest.pix, nest_recolour.pix, preview.png, README.md (black outline, legs, feelers) | src/tiles/make_yard.py, src/sprites/make_sprites.py |
| 2026-10-31 | written by hand from the public palette (not the game's data): docs/clean_pack/README.md, the palette table | src/palette/palette.json, src/palette/README.md | none (encoded by tools/clean_pack/build.py) |
| 2026-10-31 | spec side (own text) | none (the project's own words) | src/version/version.txt | none (encoded by tools/clean_pack/build.py; the Ctrl+Alt+V line) |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/balloon.md @ 4cce0ee | src/balloon/balloon.pix, preview.png, README.md | src/balloon/make_balloon.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/spider_legs.md @ 2fe2759 | src/spider/legs.json, preview.png, README.md | src/spider/make_legs.py |
