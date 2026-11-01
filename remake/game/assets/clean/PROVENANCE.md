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
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/fonts.md @ f9ce051 | src/fonts/font0.pix, font0.json, font1.pix, font1.json, font2.pix, font2.json, font3.pix, font3.json, font4.pix, font4.json, font5.pix, font5.json, preview.png, README.md | src/fonts/make_fonts.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/ui_bitmaps.md @ bdecf8d (passes 1-2) | src/bitmaps/HCEGANT_<id>.pix for 100..113, 4500..4505, 4510, 5000..5006, 5010, 5011, 5100..5107, 6000, 13000, 14000..14002, 15000, 15001, 16100 (46 files), uilib.py, pics.py, grp_abc.py, grp_deh.py, preview.py, preview.png, README.md | src/bitmaps/make_ui_bitmaps.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/ui_bitmaps.md @ eb96b1e (passes 3-4) | src/bitmaps/HCEGANT_<id>.pix for 4600, 4601, 4620, 4621, 16000, 16001, 16200, 16210..16212, 17000..17013, 21004, 21005, 28000, 28003 (28 files), grp_fg.py, grp_ijkl.py, preview.py, preview.png, README.md | src/bitmaps/make_ui_bitmaps.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/yard_bitmaps.md @ 30f0aa7 (passes 1-2) | src/bitmaps/HCEGANT_<id>.pix for 7000, 7001, 7003, 7020, 7021, 7022, 7005, 7006, 7007, 1260, 7010, 7011 (12 files; 17006 and 17007 replaced by crops of 7010), yardlib.py, yard_scene.py, yard_pass1.py, yard_pass2.py, preview_yard.py, preview_yard.png, README.md (yard section) | src/bitmaps/make_yard_bitmaps.py |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/strings.md @ d65b4dc | src/strings/system.json, balloons.json, messages.json, tutorial.json, README.md; src/menus/menus.json | none (the JSON text is the source) |
| 2026-10-31 | agent (isolated, spec only) | docs/clean_pack/screens_bitmaps.md @ ba22f36 (all 3 passes) | src/bitmaps/HCEGANT_<id>.pix for 2000, 2001, 2500, 3000, 3001, 9100, 9101, 9110, 9111, 9150..9156, 9200..9203, 12000..12003 (24 files), screens_lib.py, screens_ab.py, screens_icons.py, screens_ants.py, screens_scenes.py, screens_preview.py, preview_screens.png, README.md (appended section) | src/bitmaps/make_screens_bitmaps.py |
