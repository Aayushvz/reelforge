# Cinema Real progress ledger

Source of truth for resuming `docs/prompts/01-cinema-real-pixar-level.md`. Branch: `feat/cinema-real`.
Machine: RTX 4060 Laptop (8 GB), Blender 4.5.15.

| Phase | Task | Status | Notes |
|---|---|---|---|
| 0 | `reelforge bench` (`reelforge/bench.py`) | done | stills + timings + peak VRAM into `samples/_bench/out/<look>-<quality>/bench.json` |
| 0 | Baseline stills (classic look) | done | 8-18 s/frame Eevee at 1080x1920, peak VRAM 4.4 GB |
| 0 | Rubric (`RUBRIC.md`) | done | |
| 0 | Reference board | **blocked on owner** | `references/style/cinema-real/` is empty: owner to add 8-12 frames |
| 1 | Look system (`blender/looks/`: classic, cinema), `look`/`quality`/`look_params` in schema, plan, CLI | done | classic is the default and unchanged |
| 1 | Cinema look: Cycles (OptiX + OIDN) close-ups, Eevee wides, per-shot render ranges, skin SSS, dither | done | standard: close-ups 9-10 s (tunnel), 12-13 s (cozy), ~19 s (den); VRAM 6.4 GB |
| 1 | World haze unplugged for Cycles shots | done | it cost 75-420 s/frame and greyed the image |
| 1 | Low-key light scale + mood tint kept off the key | done | `LIGHT_SCALE`, `MOOD_TINT` in the look |
| 1 | Cinema finish in `finish.py` (light halo, grain 2, CRF 14, bt709, dither) | done | face-masked finish is Phase 7 |
| 1 | Export presets (ProRes, Master), 16-bit only at cinema tier | partly | presets belong to Phase 8's Export screen |
| 2 | `blender/camera_rig.py` (framing from head size, 10 moves, seeded handheld) | done | shake: classic 57 deg/s2 vs rig 0.5-3 deg/s2 |
| 2 | Director v2 (`plan_shots_v2`): establishing wide, push-in punchlines, listener cutaways, overrides | done | rack focus, whip and OTS not emitted yet |
| 2 | Body cheat (characters open toward each other) | done | |
| 2 | Tests | done | 107 pass (`test_camera_rig.py`, `test_director_v2.py`) |
| 2 | Evidence clip (`samples/cinema-test`, preview quality) | **was rendering when the session ended** | check `samples/cinema-test/out/preview.log` and `final_9x16.mp4`; then render at standard |
| 3-8 | Faces, new cast, rooms, performance, finish, editor | not started | |

## Open items for the next session
- Gate 1/2: show the owner the before/after stills and the test clip; confirm tiers and times.
- A 20 s reel at standard is estimated at 70-110 min, over the 60 min budget. Eevee wides (10-23 s) are the cost; profile them (motion blur, raytracing, 900k-vert Matt).
- Close-ups still show the chest under the face in 9:16; consider head fraction 0.55 or captions-over-chest.
- Tunnel close-ups look flat; the den reads best. Lighting is Phase 5.
- Eevee prints "Shadow buffer full" in the cozy room; pool raised to 1024, not re-verified.
