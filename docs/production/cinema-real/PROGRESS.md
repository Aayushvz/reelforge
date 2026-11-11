# Cinema Real progress ledger

Source of truth for resuming `docs/prompts/01-cinema-real-pixar-level.md`. Branch: `feat/cinema-real`.
Machine: RTX 4060 Laptop (8 GB), Blender 4.5.15. Evidence sheets: `docs/production/cinema-real/evidence/`.

## Status
| Phase | Task | Status | Notes |
|---|---|---|---|
| 0 | `reelforge bench [--look] [--quality] [--room]` | done | stills, timings and peak VRAM into `samples/_bench/out/<look>-<quality>/bench.json` |
| 0 | Baseline stills (classic look) | done | 8-37 s/frame Eevee at 1080x1920, peak VRAM 4.4 GB; `evidence/01_before_classic_den.jpg` |
| 0 | Rubric (`RUBRIC.md`) | done | |
| 0 | Reference board | **blocked on owner** | `references/style/cinema-real/` is empty: owner to add 8-12 frames |
| 1 | Look system (`blender/looks/`: classic, cinema); `look`, `quality`, `look_params` in schema, plan, CLI | done | classic is the default and unchanged |
| 1 | Cinema look: Cycles (OptiX + OIDN) on every shot at standard/cinema, Eevee at preview | done | see Decisions for why the Eevee/Cycles hybrid was dropped |
| 1 | Skin subsurface (random walk), low-key light scale, dimmed practicals, desaturated rim, mood tint kept off the key | done | `LIGHT_SCALE`, `PRACTICALS`, `DESATURATE`, `MOOD_TINT` in `looks/cinema.py` |
| 1 | World haze unplugged for Cycles | done | it cost 75-420 s/frame and greyed the image |
| 1 | Frames: RGB PNG, compression 15, dither; 16-bit at the cinema tier | done | some sets saved RGBA at compression 0 |
| 1 | Cinema finish in `finish.py` (faint halo, grain 2, CRF 14, bt709 tags, dithered 8-bit) | done | face-masked finish is Phase 7 |
| 1 | Export presets (ProRes, Master) | not started | belongs with Phase 8's Export screen |
| 2 | `blender/camera_rig.py`: framing from head size, 10 eased moves, seeded handheld | done | shake: classic 57 deg/s2, rig 0.5-3 deg/s2 |
| 2 | Portrait-first grammar: nothing wider than waist-up; three-quarter faces; per-character `min_head` | done | owner rejected full-body wides (2026-11-11) |
| 2 | Director v2 (`plan_shots_v2`): waist-up opener, push-in punchlines, listener cutaways, overrides | done | rack focus, whip, raking two-shot exist but are opt-in |
| 2 | Body cheat (two characters open toward each other) | done | |
| 2 | Tests | done | 110 pass (`test_camera_rig.py`, `test_director_v2.py`) |
| 2 | Evidence stills (`samples/cinema-test`) | done | `evidence/02_after_cinema_den_sequence.jpg`, `03_...`, `04_...` |
| 2 | Evidence clip at standard quality (`samples/cinema-test`, 238 frames) | **rendering** | log: `samples/cinema-test/out/standard.log`; gives the real per-frame time |
| 3-8 | Faces, new cast, rooms, performance, finish, editor | not started | |

## Measurements (standard quality, 1080x1920, stills incl. scene sync)
| Room | Classic (Eevee) | Cinema (Cycles 48/40 samples) |
|---|---|---|
| neon_tunnel | 8-17 s | 10-14 s |
| cozy_gaming_room | 17-37 s | 14-15 s |
| gaming_den | 10-21 s | 18-24 s (about 11 s scene sync + 11 s sampling; 233 objects) |
Peak VRAM 3.7-6.4 GB. A 20 s reel (600 frames) is estimated at 100-240 minutes at standard: over the 60 minute target.

## Decisions
- 2026-11-11 (owner): **no full-body shots.** The imported models are references with stiff standing poses; frame them waist-up or closer. `FRAMING` in `camera_rig.py` enforces it and a test guards it.
- 2026-11-11: **one engine per reel.** Eevee wides next to Cycles close-ups changed the room's brightness (the emission-lit tunnel) and the softness of faces from cut to cut. Standard and cinema are all-Cycles; preview is all-Eevee.
- 2026-11-11: the raking two-shot (`two`) is opt-in. With side-by-side standing characters the near body takes over the frame.
- 2026-11-11: Mina (`cute_girl`) `min_head` 0.50, Freya 0.34: the camera never frames them wider.

## Open items
- Render time is the main gap. Ideas, in order: measure the animation-render cost (persistent data should drop the den's per-frame sync); 32 samples for mediums; find why the den samples 2.7x slower than the tunnel; consider a render-time proxy of the room.
- Tunnel close-ups look flat and the den's back wall is plain: lighting and set dressing are Phase 5.
- Skin shader is a single calibrated subsurface amount: the full skin, eye, mouth and hair work is Phase 3.
- Eevee "Shadow buffer full" in the cozy room at preview; pool raised to 1024, not re-verified.
