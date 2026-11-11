# PROMPT A: "Cinema Real" (Pixar-level realistic 3D style)

Paste everything below the line into Claude Code (Fable 5.2) opened in the reelforge repo. This is a long, multi-session job. Work phase by phase, keep the progress ledger described in section 16, and stop at every owner gate.

---

# 0. How to work (read first)

1. Read `CLAUDE.md`, then `docs/HANDOFF.md` (especially sections 7 and 8), then `docs/production/PROGRESS.md` (Dhairya's ledger, for context only), then `reelforge/engines/`, `blender/render_plan.py`, `reelforge/finish.py`, `reelforge/direct.py` and `reelforge/plan.py`.
2. Create `docs/production/cinema-real/PROGRESS.md` and update it after every task. A new session reads it and `git log` and never redoes a row marked done.
3. Work on a new branch `feat/cinema-real` cut from the current branch.
4. For every phase: spec the phase in 10 lines, build it, render the evidence stills listed in the phase, review them yourself as an animator (section 15), then show the owner and wait at the gate.
5. Keep token and credit use low. Do mechanical work (renaming, boilerplate, contact sheets) with a cheaper subagent model. Keep design-heavy work (lighting, shaders, camera maths, animation reviews) for yourself.
6. Never claim "done" without evidence: a render, a number, or a passing test. Say honestly where a result falls short of the target.

# 1. Mission

Turn reelforge's `blender3d` style from "decent 3D render" into **cinematic, Pixar-level, dark and moody reels with realistic faces, lighting and backgrounds**, comparable in finish to Higgsfield and ink.industries output, while staying free, local and fully automated from a script.

Define "Pixar-level realistic" precisely, so nobody argues later:
- **Faces:** believable skin that glows with light passing through it (subsurface), real eyes with wet reflective surfaces and catchlights, alive micro-movement, readable emotion. Proportions may be gently stylized (slightly larger eyes, clean forms) or realistic; the finish must be studio-grade either way.
- **Light:** physically plausible, motivated, low-key. Every shot has a clear key, a shaped shadow side, a rim for separation, and practical lights that make sense in the room.
- **Backgrounds:** real places with depth, atmosphere, props, wear and soft out-of-focus detail. Never empty boxes, never smeared blur.
- **Camera:** smooth, intentional and motivated like a film camera. No shake, no random jitter.
- **Finish:** a graded, filmic image with controlled bloom, grain and halation that never wrecks the face.

Honesty clause: this is a free, local Blender pipeline on a laptop GPU. It will not equal a hand-crafted feature film. The target is "a viewer scrolling Instagram believes it came from a real animation studio". Measure against that in section 15 and report where you fall short. Never inflate scores.

# 2. Ground truth: what exists and what is wrong

## 2.1 Repo map (what you build on)
- `reelforge/engines/blender3d.py`: the engine. `build_assets()` builds procedural and imported assets. `render()` builds `render_plan.json` and runs `blender/render_plan.py` inside the environment `.blend`.
- `blender/render_plan.py`: loads the characters from `assets/build/<id>.blend` (collection `CHAR_base`), puts them on `Mark_A`/`Mark_B`, keys face tracks onto `FaceCtrl` custom props, head turns, breathing, talking gestures, mood light crossfades, then **creates the cameras** (the `SHOT` table plus `jitter`), sets EEVEE, renders.
- `blender/imported.py`, `import_character.py`, `import_set.py`: the imported cast (`matt`, `freya`, `cute_girl`) and rooms (`neon_tunnel`, `gaming_den`, `cozy_gaming_room`). Data in `imported.py`.
- `blender/build_character.py` + `cast.py`: 7 procedural characters. `blender/build_set.py` + `sets.py`: 10 procedural sets x 3 lighting presets.
- `reelforge/direct.py` (shot director, shots of at most 3 s), `moods.py`, `plan.py`, `finish.py` (ffmpeg: halation, grade, vignette, grain, captions, -14 LUFS), `faces`/`visemes.py`, `schema.py` (`performance.json`).
- Editor: `editor/src/data/catalog.ts` (CHARACTERS, ENVIRONMENTS, STYLES), `editor/server/api.ts` (spawns `reelforge run`), pages under `editor/src/pages/`.
- Contract every character must keep: `CHAR_root` > `Body` > `Head`, `ElbowL`/`ElbowR`, `FaceCtrl` (52 ARKit props), `FaceAnchor` (with custom prop `head_height`), `EyeFocus`. Every set keeps lights `Key`/`Rim`/`Fill`/`Glow` (with `base_color`/`base_energy`) and empties `Mark_A`/`Mark_B`.

## 2.2 Defects seen in the owner's screenshots, with root causes
| Symptom | Root cause (verify, do not assume) | Fix lives in |
|---|---|---|
| Face soft and waxy, no pores or skin depth | Draft renders (16 samples at 50% resolution) and EEVEE's approximate subsurface | Phase 1 (Cycles close-ups, full-res finals) and Phase 3 (skin shader) |
| Face lit flat, teal-and-red cast on skin | Mood tints replace key/rim colours at `TINT`, a rim tinted by the mood hits the skin | Phase 5 (light recipes keep skin tones natural; mood tints the environment, not skin) |
| Image looks "mushy" | Halation, bloom and grain applied in `finish.py` over the whole frame | Phase 7 (face-masked finish) |
| Camera looks bad | Random sine jitter on position, location keys every 2 frames, a fixed azimuth per shot kind, straight linear push, a 0.5 f-stop "cheat" on wides | Phase 2 (new camera system) |
| Nose, eyes and hair can't all be sharp | f/2.0 on 2.3 m close-ups, focus on `EyeFocus` plus a 1.5 oval aperture | Phase 1 and 2 (lens and DOF recipes) |
| Backgrounds don't read as real places | Sparse rooms, practicals too weak, heavy blur, no scene detail, no atmosphere | Phase 5 |
| Standing characters sit low in wides | Framing tuned for the seated procedural cast | Phase 2 (framing from head size and body height) |

# 3. Non-negotiable rules
- **Free and local.** No paid tools or APIs for this style. Free downloads (Poly Haven CC0, MPFB/MakeHuman, Blender Studio CC-BY) are allowed. **Ask the owner before any download over 2 GB or any system-wide install.** Never create accounts, never handle keys or passwords. The owner signs in themselves.
- **Never reduce character quality.** No decimation, no texture downscaling, no shape-key pruning on characters. Optimization means cleanup, wiring, sampling and caching.
- **Keep the `reelforge/` core standard-library only.** Blender-side scripts may import `bpy`, `bmesh`, `mathutils`, `numpy` (bundled with Blender) and nothing else.
- **Both Blender 4.5 LTS and 5.x must work.** Use `bl_common.EEVEE`. Check API differences each time you touch render, compositor or node APIs.
- **Source files you did not write never run code.** Open third-party blends with `--factory-startup` and scripts disabled (`-Y`, `use_scripts=False`).
- **Backwards compatibility.** Existing projects, `performance.json` files, the 7 procedural characters, the 10 procedural sets and the 71 existing tests must keep working. New fields are optional with defaults that reproduce the old behaviour (`"look": "classic"`).
- **No `.blend1` backups.** Set `bpy.context.preferences.filepaths.save_version = 0` in every building script. `assets/build/` is git-ignored; large files stay out of git.
- **Never use `setx`.** Blender path: `export REELFORGE_BLENDER="$(cat tools/blender_path.txt)"`.
- **Tests:** `.venv/Scripts/python -m pytest -q` must pass after every task. Add tests for every pure-Python piece you add.

# 4. Machine and budgets
- Target machine: Windows 11, **RTX 4060 Laptop, 8 GB VRAM**, Blender 4.5.15 in `tools/blender-4.5/` (also test 5.x if installed), ffmpeg 9 on PATH, Python venv in `.venv`.
- Cycles with **OptiX** (GPU) is available. Use persistent data and adaptive sampling. Keep VRAM under 7 GB per render (matt.blend alone is 1.6 GB on disk; measure).
- Budgets (measure with the benchmark you build in Phase 0, then hold yourself to them):
  - **Preview** (editor thumbnails/stills): <= 6 s per still.
  - **Standard** (a 20 s reel, 30 fps, 600 frames): <= 60 minutes total.
  - **Cinema** (same reel, every shot in Cycles): <= 3 hours total.
  - Reels are 9:16, 1080x1920. 16:9, 3:4 and 1:1 must keep working.

# 5. Art direction bible (this is the look; every phase serves it)

## 5.1 Dark, low-key, refined
The owner wants **dark outputs**, because dark is easier to make look refined and hides what we cannot model. Do this deliberately, not lazily:
- **Key-to-fill ratio 4:1 to 8:1** on faces, so shadows model the face. Blacks are rich, never crushed to zero on skin. Keep detail in the shadow side of the face (lift fill by 5 to 10% if the shadow side loses the eye or the lip).
- **Motivated light only.** Every light in the frame has a source in the room (lamp, monitor, window, neon, street light). The Key, Rim, Fill and Glow rig is aimed so it looks like those sources.
- **Rim/kicker for separation** from the background on every close-up. Rim colour comes from the environment (cool window, neon, sodium streetlight), at 30 to 60% of the key's energy, never a saturated tint on skin. Keep skin hue within +-8 degrees of the character's authored skin tone in the final frame (this is a test, see section 15).
- **Practical lights visible in the frame** (lamp heads, screens, signs) bloom softly, with a controlled halo, and they light the foreground faces by spill.
- **Atmosphere:** volumetric haze (density 0.003 to 0.012), dust motes in a key beam when the room allows, steam or smoke if the set suits it. Haze makes beams visible and separates depth planes.
- **Colour:** one dominant colour family per scene, one accent, skin stays warm. Teal/orange is allowed as a restrained grade, not as a lighting hack on faces.
- **Contrast with texture:** wet floors, glossy plastics, brushed metal and glass supply specular highlights that make dark scenes sparkle.

## 5.2 Lens and depth of field
| Shot | Lens | f-stop | Notes |
|---|---|---|---|
| Wide / establishing | 28 to 35 mm | f/4 to f/5.6 | Room readable, background soft but legible. Remove the old f/0.5 cheat |
| Medium | 50 mm | f/2.8 to f/3.5 | Eyes and shoulders sharp, room softly out of focus |
| Close-up | 85 mm | f/2.8 to f/4 | **Focus pinned on the near eye**; nose tip to ear acceptable fall-off. Never shallower than f/2.8 |
| Extreme close-up (eyes/mouth) | 100 to 135 mm | f/4 | Hero beats only |
- Aperture shape: round blades (6 to 9), ratio 1.0 for natural, 1.25 anamorphic only as a look option.
- Focus pulls (rack focus) animate `dof.focus_distance` or switch the focus object over 8 to 14 frames with ease-in-out, at moments of attention change.

## 1.3 Grade
Filmic/AgX base (use `AgX` with "Medium High Contrast"), then in the finish: lifted blacks of 1 to 2%, soft shoulder on highlights, restrained saturation (0.9 to 1.05), a subtle split tone (cool shadows, warm highlights, amount per set), and a LUT generated by script (`.cube`) per set preset. Skin stays protected (see Phase 7).

# 6. PHASE 0: baseline, benchmark, reference board (small)
Goal: a measurable starting point and a target to chase.

0.1 Add `reelforge/bench.py` and CLI `reelforge bench [--style blender3d] [--look classic|cinema]`: renders a fixed set of 6 stills (close-up Matt, close-up Mina, medium two-shot, wide neon_tunnel, wide gaming_den, wide cozy_gaming_room) at Draft/Standard/Cinema settings and prints seconds per frame and peak VRAM (read from `nvidia-smi` if present; skip gracefully if not). Save JSON to `docs/production/cinema-real/bench.json`.
0.2 Render **baseline stills** of the current output into `docs/production/cinema-real/baseline/` with the current code, untouched. Keep the 6 owner screenshot-like frames (Mina close-up with caption, Matt close-up).
0.3 Ask the owner to drop 8 to 12 reference frames into `references/style/cinema-real/` (Higgsfield / ink.industries stills they love). If empty, **stop and ask**. Build a `docs/production/cinema-real/refboard.png` (contact sheet) with `ffmpeg` or PIL-free Blender compositing.
0.4 Write the **scoring rubric** into `docs/production/cinema-real/RUBRIC.md` (section 15) before building anything.
Gate 0: the owner confirms the reference board and the rubric.

# 7. PHASE 1: render pipeline (Cycles/EEVEE hybrid, settings, export)

## 7.1 Look system
- Add `blender/looks/__init__.py`, `looks/classic.py` (today's behaviour, byte-identical settings), `looks/cinema.py`. `render_plan.py` reads `plan["look"]` and calls `look.apply_scene(sc, plan)` once after the scene is built and `look.shot_settings(sc, shot)` before each shot is rendered.
- `plan.py` gains `"look"` and `"quality"` (`preview|standard|cinema`) taken from `performance.json` (new optional keys `"look"`, `"quality"`; defaults `"classic"` and `"standard"`). Add both to `schema.py` with validation and tests.
- **Per-shot engine choice:** `cinema` look renders close-ups and extreme close-ups in **Cycles (OptiX)** and wides/mediums in **EEVEE** when `quality == "standard"`, and everything in Cycles when `quality == "cinema"`. Because a single Blender render call uses one engine, render shot ranges separately: loop over shots, `sc.frame_start/end = shot range`, set engine and settings, `bpy.ops.render.render(animation=True)`, writing to the same numbered frame sequence. Keep the resume behaviour (`use_overwrite = False`).
- Stills mode renders one still per shot with that shot's engine.

## 7.2 Cycles settings (cinema look), starting values; tune by measurement
| Setting | Value |
|---|---|
| Device | OptiX (fallback CUDA, then CPU) |
| Samples: preview/standard/cinema | 24 / 96 / 192 for faces, 48 / 128 for wides |
| Adaptive sampling | on, threshold 0.01, min samples 16 |
| Denoiser | OptiX (or OpenImageDenoise), with albedo and normal passes, `denoising_input_passes = RGB_ALBEDO_NORMAL`, prefilter accurate |
| Light paths | max 8, diffuse 3, glossy 4, transmission 6, volume 1, transparent 8 |
| Clamp | indirect 8 to 10, direct 0 |
| Caustics | off |
| Subsurface | on Principled BSDF, **random walk (skin)** method for faces |
| Motion blur | on, shutter 0.5 (180 degree), position center |
| Film | filter size 1.2, transparent off |
| Color management | AgX, "Medium High Contrast", exposure per preset, gamma 1.0 |
| Persistent data | on when the scene allows |
| Tile | auto/`2048` for OptiX |
Never use fireflies as an excuse for very high clamp; fix lights and materials instead.

## 7.3 EEVEE settings for wides and previews (Blender 4.5 Next and 5.x)
Raytracing on (reflections and GI), shadows 'virtual' enabled with soft light radius, volumetric (start 0.1, end 40, tile size 2 px) and `use_volume_custom_range`, horizon scan 1.0 for AO, fast GI off in finals, motion blur on, 64 samples final, 16 draft. Light threshold 0.01. Check each setting name against both API versions before use.

## 7.4 Render passes and the compositor (for the finishing in Phase 7)
Enable passes: Combined, Z (for DOF-aware haze), Mist, Normal, Denoising Data, **Object Index** (skin mask: give every skin mesh `pass_index = 1`, eyes 2, hair 3, clothing 4), and **Cryptomatte Object** (for fixing any mask problem). Write them via **multilayer OpenEXR half-float** (`OPEN_EXR_MULTILAYER`, DWAA/ZIP) only when the finishing compositor runs in Blender; otherwise write the combined image as **16-bit PNG**.

## 7.5 Export and encode
- Frame sequence format: 16-bit PNG (`color_depth = '16'`), colour space Filmic/AgX output display sRGB. If the Phase 7 compositor runs in Blender, EXR half then composite to 16-bit PNG.
- Final encode in one pass from the highest-quality frames, no intermediate lossy copies:
  `ffmpeg -framerate 30 -i frames/%04d.png -i dialogue_mix.wav -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -profile:v high -level 4.2 -color_primaries bt709 -color_trc bt709 -colorspace bt709 -movflags +faststart -c:a aac -b:a 192k -ar 48000 final_9x16.mp4`
- Offer in the editor's Export: **Instagram (H.264, CRF 14)**, **Master (H.264 CRF 10 high bitrate, 4:2:0)**, **ProRes 422 HQ** (for editing elsewhere), **Web preview (CRF 23, 720p)**.
- Add a dither step before 8-bit conversion to avoid banding in dark gradients (very important for dark looks): in the compositor or via `ffmpeg -vf "format=gbrp16le,...,format=yuv420p,noise=alls=1:allf=t"` limited to the shadow range; prove it on a smooth dark gradient test image.
- Keep 30 fps. Provide `"fps": 24` as the cinematic option; both must produce correct motion blur and caption timing.
- Add a frame-rate conform for **slow motion hero beats** (see Phase 6): render those shot ranges at 60 fps and conform.

Evidence for Phase 1: the 6 benchmark stills at each quality tier, a table of time and VRAM per frame, a before/after crop (100% zoom) of the Mina face at baseline vs standard vs cinema, and a gradient banding test before/after the dither.
Gate 1: the owner picks the quality tiers and confirms times.

# 8. PHASE 2: the camera system (animator's pass)

Replace the jitter-and-linear-push code in `render_plan.py` with a proper, deterministic **camera rig**. Put the maths in a pure module `blender/camera_rig.py` (testable without Blender: only `math` and plain tuples) and a thin Blender adapter.

## 8.1 Principles
- **Every move is motivated.** A push-in means growing intensity or intimacy. A slow pull-out reveals isolation. An orbit sells a two-person reveal. A static shot is confident. Never move for movement's sake.
- **Moves start and end with eased motion** (ease-in-out, Bezier handles, no linear ramps). Land on the final frame softly, don't stop dead.
- **Slow.** Typical push distance 6 to 12% of subject distance over the shot. Orbit 8 to 18 degrees. Drift 3 to 6 cm over the shot.
- **No random shake.** If handheld feel is requested, use a **low-frequency, band-limited noise** (0.3 to 0.8 Hz, amplitude 0.15 to 0.4 degrees rotation, 1 to 3 mm position, deterministic seeded by shot id, fades in and out over 0.4 s). Provide `handheld` intensity 0 to 1, default 0.15 for cinema look.
- **Key every frame** (not every 2) with Bezier interpolation, or compute a curve and use auto-clamped handles. Verify no popping.

## 8.2 Move library (each is a pure function: `(t, params) -> camera pose`)
| Move | Use | Defaults |
|---|---|---|
| `static` | confident beats, punchlines | 0 movement, optional micro-drift 0.5 mm |
| `push_in` | rising emotion, listening, realisation | -8% distance, ease-in-out |
| `pull_out` | defeat, isolation, reveal context | +10% distance |
| `orbit` | two characters, reveal, flirty or tense moments | 10 to 16 degrees azimuth, constant radius |
| `truck` | follow a lateral glance, reveal | 0.15 to 0.3 m lateral |
| `drift` | idle holds, wide establishing | 3 to 6 cm diagonal with slight rotation |
| `crane_up/down` | rooftops, big reveals | 0.2 to 0.4 m vertical plus tilt compensation |
| `whip_pan` | transitions between speakers | 6 to 8 frames, motion-blurred, hides the cut |
| `rack_focus` | attention change | 8 to 14 frames |
| `slow_zoom` | lens-based push (dolly-zoom off) | 50 to 58 mm, mild |
Plus a "dolly-zoom" for one hero beat (disabled by default).

## 8.3 Shot grammar and framing
- Shot kinds and typical lens: wide 28 to 35 mm, medium 50 mm, close-up 85 mm, over-the-shoulder 65 mm, insert/cutaway 100 mm. Keep a **180-degree line** per dialogue scene: speaker A always screen-left, B screen-right. Compute it from `Mark_A`/`Mark_B` x positions.
- **Over-the-shoulder** shots for two-character dialogue: foreground character's shoulder and ear soft in the lower corner, speaker sharp.
- **Reaction shots**: cut to the listener for 0.8 to 1.6 s at emotional lines.
- **Headroom and caption-safe areas for 9:16**: keep eyes at 38 to 42% from the top (rule of thirds), keep the **top 14% and bottom 20%** free of faces and key detail (platform UI and the captions). Test with a safe-zone overlay in the review sheets.
- **Frame from head size, not hard-coded distance**: compute the distance for each shot from `FaceAnchor['head_height']`, the lens and the target head-to-frame ratio (close-up head = 38 to 48% of frame height; medium = 18 to 24%; wide = 8 to 12%). Standing characters (imported cast) and seated ones (procedural) must both frame correctly. Reuse the body height measured from the character's bounding box.
- **Eyeline**: close-ups look slightly toward the other speaker (use `EyeFocus` plus the existing eyeLook channels) with the camera on the opposite side of the look direction to keep "looking room".
- **Parallax**: favour camera positions with foreground elements (a lamp, a plant, a shoulder) in a lower or side band at least once per scene.

## 8.4 Cutting rhythm (shot director, `reelforge/direct.py`)
Keep the old "at most 3 s per shot" cap but make the director smarter and fully deterministic (seeded by project id, so the editor preview and the render agree):
- Open with a wide or medium establishing shot of 1.5 to 2.5 s (with `drift` or `crane`).
- Dialogue: cut on the first strong syllable of a new speaker, not on the silence before it ("J-cut" feel); hold a close-up for 1.2 to 3 s; avoid cuts shorter than 0.9 s except whip transitions.
- Punchline lines get a push-in to a close-up, a 4 to 6 frame hold on the last word, then a reaction cut.
- No two consecutive shots with the same camera kind and same character.
- Emit per shot: `kind`, `lens`, `move`, `move_params`, `subject`, `focus_target`, `fstop`, `handheld`. Keep old fields so the old look still works.
- Allow editor overrides per shot (Phase 8).

## 8.5 Tests and evidence
Unit tests for `camera_rig.py`: ease monotonicity, endpoints exact, no NaN, deterministic for a seed, orbit radius constant, headroom ratio within +-2%, caption-safe overlap detection. Render a **12-second contact strip** per move (6 frames over time, 9:16) and a **camera-path plot** (matplotlib is not allowed in core, so draw the path in Blender with a curve or output a CSV and a PNG made in Blender). Run the *shake detector*: compute frame-to-frame rotation acceleration; fail if any shot exceeds the threshold except `whip_pan`.
Gate 2: the owner watches a rendered 10-second dialogue draft showing each move.

# 9. PHASE 3: faces (the top priority, spend the most time here)

Reels are mostly close-ups. The face decides whether the whole product looks professional. Do not move on until the face gates pass.

## 9.1 Skin shader library (`blender/looks/skin.py`)
A reusable node-group builder `make_skin(name, albedo_tex, normal_tex, rough_tex, spec_tex, params)` used by the imported cast (replace slot materials, keep every original texture at full resolution) and any new character.
- **Principled BSDF**: Subsurface Weight 0.12 to 0.35, Radius (1.0, 0.35, 0.2) scaled in metres to the head (0.006 to 0.012 m), Subsurface Scale tuned by head size, method **random walk (skin)**, IOR 1.4, Specular IOR Level 0.45 to 0.55, Coat 0.05 to 0.15 with roughness 0.3 for a thin oily layer in the T-zone only (mask by a texture or by vertex group), Sheen 0.05 for peach fuzz.
- **Roughness variation**: T-zone and nose 0.38, cheeks 0.55, lips 0.28, ears 0.6, driven by the supplied roughness texture or a procedural mask (never a single value).
- **Micro detail**: layer a tileable pore and fine-line **bump** (procedural: Voronoi + Noise, scale in metres so pores are 0.1 to 0.2 mm) blended at 0.15 to 0.35 strength over the texture's own normal map, with a mask that fades out on lips, eyelids, and the nose bridge. Keep all source normal maps at full resolution and correct colour space (Non-Color).
- **Regional redness / melanin variation**: subtle red at ears, nostrils, knuckles; blue-grey in stubble areas; controlled by masks. Support `blush`, `freckles` channels as optional inputs.
- **Lip shader**: separate material or mask with higher gloss (0.2), deeper saturation, slight coat; wet line along the lip line.
- **Peach fuzz**: Sheen Weight 0.08 and a low-strength velvet look on cheeks, off on lips.
- Verify under three lights (neutral studio, low-key warm, neon) that skin keeps its hue: write `qa/skin_hue_check.py` that renders a calibrated head against a neutral grey card and measures the mean skin hue shift versus the authored albedo; the shift must stay within +-8 degrees at the key's centre.

## 9.2 Eyes (the most important thing on the face)
- Eyeball: sclera with subtle veins and a warm tint at the corners (never pure white: 0.82 to 0.9 albedo), iris with depth and fibres (use parallax via a bump or a recessed pupil geometry), pupil size reacting to light and emotion (a driver or key: surprise +15%, anger -10%), limbal ring darkening, **cornea as a separate transmissive layer** (IOR 1.376) with a wet-line meniscus along the lower lid, **tear film** specular line, **caruncle** (tear duct) tinted pink.
- **Catchlights**: guarantee one clear catchlight per eye in every close-up. Implement a per-shot "eye light" (small soft area light parented to the camera at 8 to 15 degrees above and to the key side, energy tuned so the highlight is visible but not clipped) that only affects eyes via light linking (Blender 4.0+ light linking collections; fall back to a **shadow-catcher trick** or a reflective card if unavailable on 4.5/5.x; verify).
- **Eyelid behaviour**: thickness visible at the rims, a skin-coloured fold, **lashes** as cards or curves with clumping, lid corners conforming. Blinks must close fully with no eyeball showing through and no lash intersection (test with the `eyeBlink*` at 1.0 and at 0.97).
- **Eye micro-motion** (animator's section, Phase 6): saccades, drift, and gaze that leads the head by 3 to 5 frames.
- Verify the **sclera and cornea shadows** from the upper lid (soft contact shadow) so the eye sits inside the skull rather than looking stuck on.

## 9.3 Mouth
Teeth with a slightly warm off-white and a gum with subsurface, a **dark gradient** in the cavity (ambient occlusion by distance to the lips, or a dark inside shader) so the mouth never looks like a bright hole, a tongue with a wet look and subsurface, a wet lip line, and **lip seal on M/B/P** (no gaps, no intersections; fix with corrective shape keys if needed, driven from the same ARKit channels). The MBP viseme in `reelforge/visemes.py` must follow the ARKit-correct recipe (jawOpen near 0, mouthPress plus mouthRoll, a 2 to 3 frame hold) because the old follow-up note says it is still pending; do it.

## 9.4 Hair (Pixar-level hair is the hardest part)
- Replace hair-card sheets that look like plates with a mixed approach: **base hair cards for volume and silhouette** (keep the originals) plus **Hair Curves** (Blender's new curve hair, geometry nodes) for **fly-aways and a hairline fringe** (a few thousand strands, shaded with the Principled Hair BSDF (Huang) model in Cycles; in EEVEE use cards only).
- Hair shader: Huang model, melanin 0.3 to 0.9, melanin redness, coat 0.05, roughness 0.25 to 0.35, random colour per strand 0.04, IOR 1.55, radial roughness 0.3. Strand width taper.
- **Light separation**: hair must catch a rim light. Add per-scene hair rim strength (+20% on the rim) and **dark hair needs a lifted rim** so its silhouette isn't lost in dark backgrounds (very important for dark looks).
- Fix hair cards casting solid shadows: `use_transparent_shadow = True` and alpha-hashed shadows (already partly done in `import_character.py`; keep it).
- Hairline blending: soften the scalp-to-hair transition with a gradient on the scalp cap and a fringe of fine cards.

## 9.5 Brows, lashes, ears, peach fuzz, pores
Brow hair with direction and thickness variation, lashes with clumps, ear subsurface with a red translucency when back-lit by the rim (test with a strong rim from behind), nose wing translucency, and pore detail at 100% crop in close-ups.

## 9.6 Expression quality (what the animator checks)
For each character render the **face sheet at 85 mm** with: neutral, joy, laugh, smug, anger, sadness, surprise, fear, disgust, contempt, worry, and visemes (A, E, I, O, U, M, F, TH, L). Standards:
- **Smile range**: Freya's smile is subtle; increase the `mouthSmile*` and `cheekSquint*` moves so a full smile reads: lifted cheeks, crow's feet, dimples if the face has them, squinted eyes. Smile must engage the eyes (Duchenne).
- **Asymmetry**: a smug expression lifts one corner; add 4 to 8% natural asymmetry at rest.
- **Wrinkle maps**: forehead lines on `browInnerUp`/`browOuterUp`, nasolabial deepening on smile, crow's feet, nose bridge on `noseSneer`. Blend normal-map layers by the ARKit values via drivers (no code autoexec needed: use simple expression drivers).
- **Corrective shapes** for bad combinations (jawOpen + mouthSmile, mouthFunnel + jawOpen, eyeBlink + browDown).
- Run `blender/bakeoff/face_check.py` ideas against our rigs: all 52 at 1.0, common pairs, with no intersections (adapt Dhairya's checker from branch `prod/phase1-look-route`, already merged, into `qa/face_check.py`).

## 9.7 Evidence and gate for faces
For Matt, Freya and Mina: an 85 mm **face sheet**, an **eyes-and-mouth extreme close-up**, a **5-second talking close-up** with captions off, and a **side-by-side** at 100% crop of baseline vs new. Gate 3: owner approval of the face of every character before any other phase proceeds.

# 10. PHASE 4: original characters (create your own, super realistic)

The owner allows creating new characters. Build them for the cinematic look, with the same contracts.

## 10.1 Routes (decide with a short bake-off, then commit to one)
- **Route R1: MPFB2 / MakeHuman-based realistic base** (free, open source, output CC0). Download size is small; ask before installing the Blender add-on (it is an add-on, not system-wide, but confirm). Produces anatomically correct bodies and heads with ARKit-compatible face rigs via the add-on's face shape options (verify). Then sculpt/shader/hair per character.
- **Route R2: Blender Studio CC-BY characters** (Rain, Ellie and others): check each licence; credit in `ASSETS_CREDITS.md`. Strong rigs. Restyle as Dhairya did for Rain (the code is in `blender/bakeoff/route_c_rain.py`).
- **Route R3: image-to-3D** on the 8 GB GPU (Hunyuan3D-2 mini). Ask before downloading several GB. Face detail is usually weak; use only as a challenger.
Pick the route by scoring the same test character (one male, one female) on the rubric (section 15); face quality dominates.

## 10.2 The cast (design them like a casting director)
Create **6 new original realistic characters** (3 male, 3 female) that complement the imported ones, spanning ages (20s to 50s), skin tones (include deep, medium and light), face shapes and personalities. For each, write a one-paragraph character bible: age, job, vibe, voice description for the ElevenLabs voice picker, signature look, wardrobe, three outfits, and the tag that goes in the editor (`catalog.ts`). Avoid likenesses of real people. Use distinctive, believable features: asymmetry, a scar, a gap tooth, freckles, laugh lines, eye bags. Perfection reads as plastic.

## 10.3 Technical specification per character
- **Proportions**: realistic with gentle Pixar-style refinement (eyes 4 to 8% larger, clean jaw, slightly softened forehead) so they read as "animated film" not "uncanny photo".
- **Head**: up to 60% of the triangle budget on the head; edge loops around the eyes, mouth and nasolabial folds.
- **Textures**: 4K head and face (albedo, normal, roughness, subsurface/thickness, displacement/bump), 2K body, 2K to 4K clothing. If textures must be created, paint them procedurally with node layers in Blender, then bake to 4K with Cycles baking. Everything packed.
- **Clothing** with real fabric: knit (Sheen and a woven normal), denim (twill pattern normal and fading), leather (anisotropic reflection and creases), cotton (soft sheen), silk (anisotropic). Use thickness (Solidify), seams, stitching, wrinkles baked in the neutral pose, and a **cloth bake** (Blender cloth sim, cached, run once at build time for the neutral pose) so folds look natural. Layered outfits (shirt under jacket) with no interpenetration.
- **Hands**: real hands with fingers and a small set of **hand poses** (relaxed, gesture-point, open palm, fist, holding a phone, typing), selectable per talking gesture. Imported rigs need hand bones mapped; procedural characters currently have mitten hands, so use the new characters for gestures.
- **Rig and face**: ARKit 52 shape keys sculpted/transferred per character (not a single generic transfer), correctives, the same `FaceCtrl` driver contract, `FaceAnchor`, `EyeFocus`, plus a trimmed deform rig (fewer bones than Rain's 2,166; remove control-only bones from the render copy).
- **Body**: breathing, weight shifts, posture presets (standing, seated, leaning on a wall) selected by the set's props.
- **Standing and seated** variants where the set needs them (seated at a desk/sofa, standing at a window), so characters work in every room.

## 10.4 Quality gate for new characters
Each new character passes: face sheet, 52-shape check, 5 s talking close-up, outfit turntable (3 outfits), hair rim test in a dark scene, skin hue test under neon, and an animator review (section 15). Spend the review time on the face.
Gate 4: owner approves the roster.

# 11. PHASE 5: environments and lighting (backgrounds that look like real places)

## 11.1 The kit
Build a reusable **lighting and set-dressing kit** (`blender/looks/kit.py`) so every room goes through the same upgrade:
- **Light rig upgrade** (keep the names `Key`, `Rim`, `Fill`, `Glow` for compatibility; they are still the mood controls) plus **practical lights**: lamp shades with emission, monitor/TV screens (emission plus a soft area light in front), neon tubes (emission plus an area light), window light (large area plus a haze shaft), under-shelf LEDs (area strips). Use real-world watts and sizes. Make them baseline from the room's authored lights (the imported rooms already have some; preserve and rebalance, see `import_set.py`).
- **World lighting**: a dim HDRI for ambient colour and window views. Prefer **Poly Haven** CC0 HDRIs (interiors, night cities, studios). Allowed to download small HDRIs (1 to 2K for lighting, 4K only if seen through windows). Ask before any big batch (> 2 GB total). Credit in `ASSETS_CREDITS.md`. Rotate the HDRI per set preset.
- **Materials pass**: swap flat materials for believable ones: scuffed floor with roughness maps, wallpaper/plaster with subtle bump, wood grain, glossy lacquer, fabric, glass with proper IOR and thin walls. Use Poly Haven CC0 PBR textures (2K). Add **wear**: edge dirt, fingerprints on glass, dust.
- **Set dressing**: each room gets 15 to 30 small story props placed with intent (cups, cables, sticky notes, books, plants, posters, a jacket on a chair), kept clear of the characters' hands and faces. Use Poly Haven CC0 models (ask before large packs) or simple procedural props. Keep the room's silhouette readable in a wide.
- **Atmosphere**: volume scatter in the world (density per preset), a dust particle volume in key beams (small geometry-nodes point cloud with emission 0, scattering only), subtle floor reflections, light shafts through windows.
- **Depth layers**: foreground (blurred props near the lens), midground (characters), background (room). Add at least one foreground element per wide.
- **Backdrop through windows**: a believable outside (a night skyline plate on an emissive plane or an HDRI), not black.

## 11.2 Lighting recipes per room (starting points; verify by eye and by the rubric)
| Room | Mood recipes (each 2 to 3 presets) | Key idea |
|---|---|---|
| **neon_tunnel** | Neon (magenta key from the side, cyan rim), Blackout (cool minimal), Rain-slick (wet floor reflections) | Glossy black surfaces carry the look; skin keeps warm tone through a neutral key, colour lives in rims and reflections |
| **gaming_den** | RGB night, Late session, Daybreak | Screen glow as key (cool, 4500 K), warm lamp as kicker, LED coves as separation |
| **cozy_gaming_room** | Purple neon, Chill evening, Rainy window | Practicals everywhere: TV, speakers, lamps; keep exposure down so colours stay rich |
| Procedural sets (10) | Upgrade the key/rim/fill per `sets.py` with the same kit | Each gets its dominant colour and one accent |
Per-preset targets: exposure (stops) and the average luminance of the frame for dark looks: **mean luma 0.08 to 0.22** for the key frame, with highlight peaks under 1.0 after the grade and no clipped faces.

## 11.3 Evidence
For each room: wide, medium and close-up with Matt or Mina on the mark, at standard and cinema quality. For each preset: a 3-frame strip showing the mood crossfade. Gate 5: the owner approves rooms one by one.

# 12. PHASE 6: performance and animation (animator's pass)

Think like an animator. Look at the output as a viewer who has watched 10,000 films.

## 12.1 The 12 principles applied to our rig
- **Anticipation** before a head turn or a punchline: a 3 to 5 frame counter-movement.
- **Overlap and follow-through**: head leads, hair and shoulders follow 2 to 4 frames later; earrings and hair swing.
- **Slow in/out** on every head turn, nod and gesture.
- **Arcs**: head turns and nods travel on slight arcs, never straight lines.
- **Holds**: let the last word of a punchline breathe 6 to 10 frames before moving.
- **Secondary action**: breaths, swallow, tiny brow flicks, lip lick before a line, blinks.
- **Appeal**: faces never freeze; keep a living micro-motion (0.1 to 0.3 degree head drift, 1 to 2 mm posture).

## 12.2 Eyes (the soul of the performance)
- **Blinks**: every 2.5 to 5.5 s (randomised), double blinks occasionally, a blink on every large head turn and at the start of a thought; duration 6 to 9 frames (close 3, open 5).
- **Saccades**: tiny eye darts every 0.5 to 1.5 s (1 to 3 degrees), larger shifts when thinking (look up-left or away then back); the eyes lead the head by 3 to 5 frames.
- **Gaze direction**: when a character listens, look at the speaker's eyes with periodic breaks; when speaking, glance away while forming a thought, return at the key word.
- **Lid dynamics**: the upper lids follow vertical gaze (lower when looking down).

## 12.3 Acting from the line
Use the `emotion`, `intensity`, `mood` and `punchline` fields from `performance.json` plus the text itself:
- Emphasis beats on stressed words: a small brow raise or head nod aligned to the word's start (use word timings from the alignment).
- **Listener reactions**: micro-expressions (a smirk, a tight lip, a raised brow) timed to the speaker's emotional peaks; stronger on punchlines.
- **Thinking pauses**: gaze breaks and a slight head tilt.
- **Emotion transitions**: ease between emotions over 6 to 12 frames, never snap; the eyes change first, the mouth last.
- **Viseme quality**: co-articulation (blend neighbouring visemes), the jaw follows loudness (not just a binary open/closed), lip corners stay engaged with the emotion, teeth visible on the right sounds, a 2 to 3 frame M/B/P seal, small jaw lag.
- **Body**: breathing (sine plus a slight asymmetry), a weight shift every 3 to 6 s, shoulders react to emotion (shrug on doubt, rise on tension), hands gesture on emphasised words using the hand-pose library, hand-to-face or fidget touches while listening (rarely).
- **Standing characters**: weight on one leg with the pelvis tilt; no foot sliding; subtle sway.

## 12.4 Hero beats
One to three per reel: a slow-motion moment (60 fps conform) on the punchline; a whip-pan transition; an extreme close-up of the eyes; a foreground rack focus. The director selects them from the script's `punchline` and `mood` fields.

## 12.5 Evidence
Review every talking close-up **at full speed and at 25% speed**. Use a checklist: do the eyes feel alive, are blinks natural, does the head ever look frozen, any foot slide, pops, jitter, lip-sync slip greater than 2 frames, skin flicker? Note issues with frame numbers.

# 13. PHASE 7: finish, grade, sound, export

- Rework `reelforge/finish.py` so the cinema look uses: a **per-set LUT** (generated by script as a 33-point `.cube` from the set's grade parameters) applied in 16-bit; **halation** and **bloom** limited to highlights above a threshold and **masked off skin** (use the Object Index mask: composite in Blender and write the final frames, or render a skin-mask pass and use ffmpeg `maskedmerge`); a **vignette** of 8 to 14%; **filmic grain** at low intensity (luminance-only, size 1 to 1.3 px, strength 0.015 to 0.03, applied with a shadow-weighted mask so it never sits on the skin highlights); optional **chromatic aberration** at the frame edges (0.2 px); **lens bloom streaks** only on neon sources (off by default).
- **Depth-based atmosphere**: use the Z/Mist pass to add slight distance haze to the background (and a subtle bokeh glow on highlights).
- **Sound**: keep `ambience.py`; add **room-specific foley** (a keyboard clack for desks, a distant street, rain), a **soft low-end bed**, and **gentle ducking** under dialogue. Optionally a small music bed generator (very simple ambient pad via ffmpeg `aevalsrc`) behind a flag. Keep -14 LUFS integrated, true peak -1.0 dBTP.
- **Captions**: keep the word-highlight style; place captions in the caption-safe band, never over the eyes or mouth; use the face position from `FaceAnchor` projected into the camera to push captions up or down per shot.
- **Transitions**: whip-pan blur dissolves, 4-frame dip-to-black on mood changes.
- Output presets as in Phase 1. Write `final_9x16.mp4` and a `report.json` (render times, settings, warnings).

# 14. PHASE 8: editor integration (think as a product designer)

The owner wants this in the existing editor (`editor/`, Vite + React + TS + Zustand). Use the existing design tokens in `src/styles/tokens.css` (dark, minimal; Higgsfield and InVideo are layout references only; no AI-slop patterns: no gradient blobs, no emoji icons, no purple-on-white defaults). Every control has a purpose, a default, a tooltip, and an empty/loading/error state.

## 14.1 Style picker (Create page and project settings)
- Cards for each style: **Cinema Real** (this prompt) and later **Painted Toon**, **Classic 3D** (the old `blender3d` look, kept). Each card shows a live **thumbnail from a real render** (generated by the preview pipeline, cached), a one-line description, and badges: `Free`, `Local`, estimated render time per 10 s of video at the chosen quality (from `bench.json`).
- Changing the style updates the preview stills and the available controls.

## 14.2 Look panel (per style)
Controls for **Cinema Real** (all saved into `performance.json`, optional, with defaults):
- **Quality**: Preview / Standard / Cinema, with the time estimate and a one-line explanation (Cycles faces, full-res, noise cleaning).
- **Mood lighting**: Low-key (default) / Neutral / High-key (maps to exposure and fill ratios) and a **Light colour accent** swatch from the room's practicals.
- **Skin glow** slider (subsurface 0.6 to 1.4x), **Eye shine** (catchlight intensity), **Depth of field** (Natural / Cinematic / Extreme), **Film grain**, **Bloom**, **Haze** sliders, **Vignette**, **Grade strength**.
- **Dark/Bright** quick toggle for the room.
- A **"Reset to look default"** button and a **compare** toggle showing the Classic look vs Cinema on the selected shot.

## 14.3 Camera panel (per shot in the timeline editor)
- Per-shot **move picker** (Auto, Static, Push-in, Pull-out, Orbit, Drift, Truck, Crane, Whip), **intensity** slider, **lens** (28 / 35 / 50 / 85 / 100), **focus target** (left/right character, background), **handheld** amount, **length**, **cut**.
- A **move preview**: a small looping 9:16 preview of the path using 6 cached stills or a quick EEVEE draft; a **safe-zone overlay** toggle (top 14%, bottom 20%, eye line at 40%).
- A **"Re-roll camera"** button (changes the seed within the director's rules), and a **lock** icon so a re-roll never overwrites a hand-picked shot.

## 14.4 Cast, outfit and set pickers
Add the new characters to `CHARACTERS` and the new lighting presets to `ENVIRONMENTS` in `catalog.ts`, with real render thumbnails served by the existing thumbnail endpoint (`/thumbnails`), computed in the background with the 2-slot queue already in `api.ts`. Show a "Face sheet" button on each character that opens the 85 mm expression grid. Show `Standing`/`Seated` tags and which sets each character suits.

## 14.5 Render screen
Show: estimated total time (from the bench) before starting, per-shot progress with thumbnails as they finish, a live log, the stills approval step (approve / re-render with changes per shot), cancel and resume, and a **final report** (time, warnings, file sizes). Add a **"Render this shot only"** and **"Render stills"** action. Never start a paid or heavy action without an explicit button press; show the time estimate first.

## 14.6 Export screen
Presets as in Phase 1 (Instagram, Master, ProRes, Web preview), caption burn-in toggle, SRT export, thumbnail frame picker, and a **platform safe-zone check** overlay.

## 14.7 Server and schema
- `editor/server/api.ts`: pass `--style` and `--quality` through to `reelforge run`; stream progress; store settings in `performance.json` keys: `style`, `look`, `quality`, `look_params {...}`, `shots[i].camera {move, intensity, lens, focus, handheld, locked}`.
- `reelforge/schema.py`: validate and document every new key, with defaults that reproduce current behaviour. Add `tests/test_look_schema.py`, `tests/test_camera_rig.py`, `tests/test_director_v2.py`, `tests/test_bench.py`.
- Add Playwright-free smoke checks (curl the dev server endpoints) and `npm run typecheck`.
- Verify in the browser pane: the style picker, look panel, camera panel, render screen; check the console is clean; screenshot every screen.

# 15. QA, rubric and review protocol

## 15.1 Scoring rubric (score every deliverable 1 to 10 against the reference board)
| Criterion | Weight |
|---|---|
| Face realism and appeal (skin, eyes, mouth, hair at 100% crop) | 30% |
| Lighting (motivated, sculpting, mood, skin tone integrity) | 20% |
| Background believability and depth | 15% |
| Camera (smoothness, intent, framing, caption safety) | 10% |
| Performance (blinks, eyes, lip-sync, secondary motion) | 15% |
| Finish (grade, grain, bloom, banding, export) | 10% |
A phase passes only if the weighted score is >= 7.5 **and** no criterion is below 6. The face criterion must be >= 8.

## 15.2 Automated checks (add to `qa/` and run in CI-like fashion before each gate)
`qa/skin_hue_check.py`, `qa/face_check.py` (52 shapes, pairs, intersections, full blink), `qa/shake_check.py` (camera acceleration), `qa/safe_zone_check.py` (faces outside the caption bands), `qa/banding_check.py` (dark gradient steps), `qa/luma_check.py` (mean luma in range, no clipped faces), `qa/flicker_check.py` (frame-to-frame difference of static regions), plus all unit tests.

## 15.3 Independent review
After each phase, spawn a reviewer subagent on a **different model**, give it only the evidence images, the rubric, and the reference board (no explanation), and have it score blind. Compare with your own scores and fix the top defects. Record both scores in the ledger.

## 15.4 Animator's viewing checklist (every video, at full speed and 25%)
Eyes alive? Blinks natural? Head freezes? Pops or jitter? Lip-sync within 2 frames? Skin flicker or noise crawl in darks? Banding in dark gradients? Camera moves eased and motivated? Cuts land on beats? Captions clear of faces? Colour consistent across cuts? Any uncanny moment? Any shot you would be embarrassed to post?

# 16. Deliverables, ledger, git hygiene, stop conditions
- Deliver in this order, each behind its gate: Phase 0 (bench, baseline, refs), Phase 1 (render pipeline), Phase 2 (camera), Phase 3 (faces), Phase 4 (new cast), Phase 5 (rooms), Phase 6 (performance), Phase 7 (finish and sound), Phase 8 (editor). Phases 1 and 2 are independent and cheap: do them first, because they fix what the owner complained about immediately.
- Ledger: `docs/production/cinema-real/PROGRESS.md` with a status table, decisions, open questions and scores, updated after every task.
- Commit small and often on `feat/cinema-real` with clear messages. Never commit `assets/build/`, big blends, or frames. Add credits for every third-party asset to `ASSETS_CREDITS.md`.
- Stop and ask the owner when: a download exceeds 2 GB; a system-wide install is needed; the reference board is empty; two routes tie on the rubric; a licence is unclear; a phase fails its gate twice.
- Write `docs/production/cinema-real/FINAL_REPORT.md` at the end: what changed, evidence stills, the benchmark table, the scores, known gaps, and how to rebuild everything with one command.

# Appendix: default numbers (starting points)
- Frame: 1080x1920, 30 fps, 9:16. Safe area: top 14%, bottom 20%. Eye line at 40% from the top.
- Head-to-frame ratios: wide 8 to 12%, medium 18 to 24%, close-up 38 to 48%.
- Move amounts: push-in -8%, pull-out +10%, orbit 10 to 16 degrees, drift 3 to 6 cm.
- Handheld: 0.3 to 0.8 Hz, 0.15 to 0.4 degrees, 1 to 3 mm, seeded.
- Blink: every 2.5 to 5.5 s, 6 to 9 frames. Saccades: 0.5 to 1.5 s, 1 to 3 degrees.
- Cuts: 0.9 to 3 s; whip 6 to 8 frames; rack focus 8 to 14 frames.
- Samples (Cycles faces): preview 24, standard 96, cinema 192; wides 48 / 128.
- Mean luma target 0.08 to 0.22; key:fill 4:1 to 8:1; rim 30 to 60% of key; skin hue within +-8 degrees.
- Encode: x264 CRF 14, preset slow, yuv420p, bt709 tags, AAC 192k, -14 LUFS, -1 dBTP.
