# reelforge: project handoff (as of 2026-11-13; Shots-AV in section 9)

Read this first in any new session. It covers what exists, how to run it, the decisions already made, and what to do next.

## 1. Goal
A tool that turns a **script** into a **cinematic, lip-synced, emotional 3D animated short** for Instagram Reels and Shorts. The style references are the @canwebuildthis reels and the NMXWZ "Friday 4:59 PM" reel.
- **Characters:** stylized-premium (Pixar-like), built from the user's reference images.
- **Environments:** refined, moody and glowing, built from the user's reference images.
- **Input:** the user only uploads a script (and references). Everything else is automated.
- **Formats:** 9:16 by default; 16:9, 3:4 and 1:1 are optional.
- **Constraint:** low token use. Claude makes one small call per video; everything else is deterministic and runs locally.

Full design: `docs/superpowers/specs/2026-10-31-animated-reel-generator-design.md`

## 2. User decisions (don't re-ask)
| Topic | Decision |
|---|---|
| Engine | **Blender 4.5 LTS, headless** (not AI video, not Three.js) |
| Character style | Stylized-premium, Pixar-like. The user rejected the procedural stand-in as "too naive". |
| Character source | **Claude generates them from the user's references.** The user doesn't want to buy tools or model anything; **no paid tools** (Faceit rejected). |
| Voice | ElevenLabs, generated **in the web app via the user's Chrome**, which is logged in. **No API key.** Currently Eleven v4, voice "Jessica - Playful, Bright, Warm". |
| Lip sync | Grapheme visemes from local faster-whisper alignment (default). The Audio2Face ONNX adapter exists but isn't the default. |
| Editor | A local web app, planned for a later milestone. |
| Accounts | Claude can't create accounts or handle passwords or keys. The user signs in themselves. |

## 3. What's built (Milestone 1, merged to `main`)
A Python package `reelforge/` (standard library only), Blender scripts in `blender/`, and 49 passing tests.

```
script/performance.json → voice (ElevenLabs API or imported mp3 + faster-whisper align)
 → timeline + dialogue.wav → face tracks (52 ARKit channels: emotion spring + visemes + blinks + nods)
 → shots (wide/medium/closeup, ≤3 s) + mood keys → captions.ass → render_plan.json
 → Blender (character + set, face keys, mood light crossfades, DOF cameras) → frames/
 → ffmpeg finish (halation, grade, vignette, grain, captions, -14 LUFS) → final_9x16.mp4
```

| Module | Role |
|---|---|
| `reelforge/schema.py` | Validates `performance.json`: lines, speaker, emotion, intensity, mood, punchline |
| `voice.py`, `alignment.py`, `align_local.py` | ElevenLabs API client with cache; `import_line()` for web-generated mp3s; Whisper alignment (CPU fallback) |
| `timeline.py` | Places lines on the timeline and mixes `dialogue.wav` |
| `visemes.py`, `face.py`, `a2f.py` | Face tracks; Audio2Face adapter |
| `direct.py`, `moods.py`, `plan.py` | Shot director, mood light presets, `render_plan.json` |
| `captions.py`, `finish.py` | Word-highlighted captions; ffmpeg finishing |
| `cli.py` | `reelforge build-assets` and `reelforge run <project> [--stage stills\|full] [--draft]` |
| `blender/build_character.py` + `cast.py` | The 7-character sculpted cast with wardrobe (see §7). Contract: `CHAR_root` → `Body` (hip pivot: breathing, talk-lean) → body parts, `ElbowL`/`ElbowR` (forearm + hand: talking gestures) and `Head` (nods, listener turns); `FaceCtrl` (52 ARKit props), `FaceAnchor`, `EyeFocus`. |
| `blender/build_set.py` + `sets.py` | 10 sets x 3 lighting presets (night_city is one of them): lights `Key`, `Rim`, `Fill`, `Glow`; optional `ScreenMat`/`HoloMat`; `Mark_A`/`Mark_B` (see §7) |
| `blender/render_plan.py` | Executes the render plan inside Blender |
| `tools/a2f_fetch.py` | Audio2Face v2.3 ONNX on CPU (spike) |

**How to run it:**
```bash
export REELFORGE_BLENDER="$(cat tools/blender_path.txt)"   # Blender 4.5.15 in tools/blender-4.5/
.venv/Scripts/reelforge build-assets
.venv/Scripts/reelforge run samples/look-test --stage stills --draft   # quick check
.venv/Scripts/reelforge run samples/look-test --stage full            # final video
.venv/Scripts/python -m pytest -q
```
- Put voice mp3s at `samples/<project>/out/audio/<line_id>.mp3`.
- Output goes to `samples/<project>/out/final_9x16.mp4`.

**Look-test result** (`samples/look-test/REVIEW.md`): **pipeline PASS, look PARTIAL.**
- Working: lip sync, emotion blending, the mood shift, close-up bokeh, captions, −14.9 LUFS.
- Weak: flat face lighting, a weak rim light, the wide shot isn't bokeh, lip closures are a thin line, and the stand-in character.

## 4. Next milestone: generate characters and environments from references
**Status:** agreed in principle; not brainstormed or specced yet. Start with the brainstorming skill.

**Inputs from the user:**
- `references/characters/`: front-facing, full-body, plain background
- `references/environments/`

**Proposed approach.** Everything is free, local and account-free. Ask before downloading 5–10 GB of models into `tools/`.
- **Character mesh:** Hunyuan3D-2 mini (open source, image to textured 3D; fits the RTX 4060's 8 GB).
- **Face for animation:** add eyeballs, eyelids and a mouth cavity by script, then generate the face shapes. They must use ARKit-correct names and drive through the `FaceCtrl` contract.
- **Body rig:** Blender Rigify or UniRig (open source).
- **Environments:** Depth Anything V2 turns a reference image into a depth-displaced 3D backdrop, giving parallax and real depth of field. Real 3D props (desk, glowing screens, lights) sit in front of it so the mood shifts keep working.
- **Free fallback** if quality disappoints: Blender Studio's CC-BY stylized rigs (Rain, Ellie).
- **Honest expectation:** "very good stylized" first, then iterate. Hands and hair are the hard parts.

**Requirements from the M1 final review** (`docs/superpowers/notes/m1-followups.md`):
1. The new character must expose `FaceAnchor` and `EyeFocus` empties on the head bone, and shot distance should come from head size. `render_plan.py` currently hard-codes the stand-in's proportions.
2. **ARKit-correct MBP viseme:** `jawOpen≈0` plus `mouthPress` plus `mouthRoll`, with a 2–3 frame hold. `mouthClose` is used only with a small `jawOpen`. Fix this in `visemes.py` when the new head lands.
3. Re-run the Audio2Face vs viseme comparison on the new head (drop-in via `out/a2f/<id>.json`).
4. Environment: cheat the wide-shot f-stop to about 0.4–0.5 for bokeh, and retune the rim light and haze.

## 4. CURRENT PRIORITY: production brief (2026-11-01)
**Read `docs/superpowers/specs/2026-11-01-cast-sets-editor-brief.md`.** The owner wants:
- **7 original characters** (4 male, 3 female) in a stylized-sculpt look, with a Gen-Z wardrobe system;
- **10 environments × 3 lighting presets**;
- a **dark, minimal editor UI** that uses Higgsfield and InVideo as references only, our own design, with no AI-slop patterns.

The brief's build order supersedes the earlier orders below. The style reference images go in `references/characters/style/`; ask the owner to add them if they're missing.

## 4a. Platform direction: multiple animation styles (decided 2026-10-31)
reelforge becomes a **multi-style platform with 5–6 styles**; the user will add more references over time.
- **Style 1** is the Blender 3D pipeline built in Milestone 1 (`blender3d`).
- **Style 2** is the ink.industries cinematic AI-video look (`cinematic-ai`, §4b). It's an **additional option**, not a replacement.
- Shared spine: script → voice → timeline → **pluggable style engine** → finish.
- See `docs/superpowers/specs/2026-10-31-multi-style-engines.md` for the engine contract and the revised build order. In short: engine refactor → Style 1 characters and environments → Style 2 engine → editor with a style picker → more styles.

## 4b. Long-term look target (the user's end goal)
The user's ultimate references are the **ink.industries "First kiss effect V2"** style reels. These are Pixar-like characters (strand hair, knit fabric, expressive faces with blush) in cinematic environments: a lantern-lit street, a San Francisco hill with a cable car, an aerial bridge shot, a stylized cracked-ground VFX shot.
- **Honest assessment (shared with the user on 2026-10-31):** those reels are **AI-video generated** (labelled "AI content"). A Blender pipeline with free tools **cannot fully match them.** The realistic ceiling is high-quality stylized 3D animation, below those frames.
- **Update (same day):** the user now wants this look as **Style 2** (`cinematic-ai`), built with AI image and video generation as an *additional* style, while Style 1 stays on Blender. Style 2's paid providers are acceptable as an opt-in, with costs shown up front; the free fallback is Wan 2.2.
- For **Style 1 (Blender)**, still use these references as inspiration for look decisions: hair cards with clump detail, fabric with fuzz and sheen, a cartoon-expressive face with blush, warm sunset or lantern lighting, atmospheric depth, a strong depth-of-field look.
- Each sub-project's quality gate should compare stills against these references and state honestly how close they get.
- AI video (Kling, Veo, Seedance, or the free Wan 2.2) was offered and declined. Don't re-propose it unless the user asks.
- The user's reference screenshots aren't saved in the repo. Ask the user to drop them into `references/style/`.

## 5. Later milestones (from the spec)
- **M2, automation:** a Claude "performance pass" that turns the script into `performance.json`; two characters with listener reactions; a mocap gesture library; music and foley; captions placed around faces; staleness and render caching (see the follow-ups).
- **M3:** more sets and outfits; per-mood grade, flicker and bloom; Cycles for close-ups.
- **M4:** the local web editor.
- **M5:** multi-ratio export (16:9, 3:4, 1:1).

## 6. Environment notes
- Windows 11, RTX 4060 laptop (8 GB). Python 3.14 in `.venv`. ffmpeg 9. Git repo with `main` only and no remote.
- CUDA libraries aren't installed, so faster-whisper and ONNX run on CPU. That's fine for short lines.
- `tools/` and `samples/*/out/` are git-ignored. `tools/blender_path.txt` holds the Blender path; never use `setx`.
- Claude credits: the Pro plan's weekly limit was **92% used on 2026-10-31**, resetting on 2026-11-03. Keep sessions lean, start fresh sessions, and use cheaper models for mechanical tasks.
- Workflow: superpowers brainstorming → spec → plan → subagent-driven development, with per-task reviews.

## 7. Session 2026-11-04 (Aman's machine)
- Hardware differs from §6: **RTX 3050 Laptop, 4 GB VRAM**, ~21 GB free on C:, **Blender 5.2.3 LTS** at `C:\Program Files\Blender Foundation\Blender 5.2\` (written to `tools/blender_path.txt`). Python 3.13 venv. 4 GB rules out Hunyuan3D-2 locally, so characters are sculpted by script.
- Blender 5.x renamed `BLENDER_EEVEE_NEXT` back to `BLENDER_EEVEE`: `bl_common.EEVEE` picks the right one.
- **Engine refactor done:** `reelforge/engines/` registry, `blender3d` engine, `--style` on `run`/`build-assets`, optional `"style"` in `performance.json` (default `blender3d`). 63 tests pass (as of the end of this session).
- **Cast (all 7):** `blender/build_character.py -- <out.blend> <char_id>` sculpts a head by script (cube-sphere + sculpt fields, real mouth slit, teeth/tongue/cavity, eyeballs + lids, chunky brows) with ARKit shape keys driven from `FaceCtrl`, plus `FaceAnchor`/`EyeFocus`. Every dial lives in `blender/cast.py`: kai, rey, dev, mo, aria, zoe, noor. Systems: hair styles `curls|swoop|messy|long|bob|ponytail` (clay locks grown over a scalp cap with a smoothed hairline), beard (masked twin of the head mesh, so it rides the jaw shape keys), glasses `round|rect`, freckles, blush, lashes, top types `shirt|tee|hoodie|turtle|zip`, earrings, chains, watch. Pick a member per character with `"model"` in `performance.json` (default `kai`).
- **Environments (10 sets × 3 presets):** `blender/build_set.py -- <out.blend> <set> <preset>`, data in `blender/sets.py`. Files are `assets/build/<set>__<preset>.blend`; `<set>.blend` is the first preset. Choose with `"environment"` + optional `"lighting"` in `performance.json`. Each light keeps `base_color`/`base_energy`; moods tint them by the scene's `mood_tint` (night_city = 1.0, the old behaviour). `build_night_city.py` is gone (night_city is a set now).
- `reelforge build-assets` builds the whole cast and all 30 set files (a few minutes). Previews: `blender -b <char>.blend -P blender/preview_character.py -- out.png yaw=30 shot=bust jawOpen=0.5`; `blender -b <set>.blend -P blender/preview_set.py -- out.png <abs path to char.blend> medium`.
- **Staging:** every character in `performance.json` renders on its mark (Mark_A, Mark_B). Close and medium shots aim at the shot's `subject`, wide shots frame everyone, and listeners turn their head and eyes toward the speaker. `--draft` = 16 samples at 50% resolution (~4 s/frame on the 3050; full res ~15 s/frame).
- **Sound + grade per set:** `reelforge/ambience.py` mixes a procedural ffmpeg bed (room tone, wind, waves, murmur, hum; plus rain for rain presets) at -24 dB under the dialogue (`"ambience": false` turns it off; the dry mix stays in `dialogue_dry.wav`). `finish.GRADES` adds a per-set colour-balance push, which plays the role of the brief's LUT.
- Verdict vs `references/characters/style/`: rig and expressions work across the cast; look is "clean stylized toy", below the references (soft face planes, simple tube bodies, mitten hands, no outfit layering yet). Sets are procedural boxes lit well rather than modelled; see `docs/review/cast-sets-v1/REVIEW.md`.
- **Next steps (suggested):** (1) swap the placeholder Windows-TTS voices in `samples/*/out/audio` for real ElevenLabs takes and re-run (`pip install -e ".[align]"` for Whisper); (2) the face quality pass in `docs/review/cast-sets-v1/REVIEW.md` (crisper planes, bigger smile range); (3) wrist/finger poses and a proper body rig; (4) fold/seam detail on clothes; (5) the editor's cast/outfit/set/lighting pickers now have real data to bind to (`blender/cast.py`, `blender/sets.py`); (6) the `cinematic-ai` engine. This folder is not a git repo: nothing from this session is committed.

## 8. Session 2026-11-04 (imported cast + sets)
The owner supplied third-party Blender files (`~/Downloads/BLENDER FILES`; RARs extracted to `extracted/`). They're wired to the existing contracts and live next to the procedural cast and sets.
- **Rule (in CLAUDE.md):** never reduce character quality. No decimation, texture downscaling or shape-key pruning. Facial detail is the target.
- `blender/imported.py` holds the data: source paths (`SRC_ROOT`, override with `REELFORGE_IMPORTS`), rig bone maps, and ARKit → face maps. The face maps are CC4 shape keys for Matt, Rigify controls for Freya, and Auto-Rig Pro controls for cute girl ("Mina" in the editor).
- `blender/import_character.py -- <out> <id>` does the following:
  - removes widgets, lights, cameras and unused armatures, and prefixes object names;
  - resets the pose, then relaxes the arms down from the A/T pose;
  - builds `CHAR_root` → `Body` → `Head`/`ElbowL`/`ElbowR`, which steer bones through Copy Rotation from pivot empties;
  - adds `FaceCtrl` (52 ARKit props) with simple-expression drivers that work without autoexec, plus `FaceAnchor`/`EyeFocus` on the head bone;
  - fixes FBX material slips (Reflection→Metallic, sRGB data maps, glossy alpha cards, opaque hair shadows);
  - saves into a clean scene, because Freya's source scene settings darkened half her face.
- `blender/import_set.py -- <out> <set> <preset>` scales each room to metres facing -Y (the tunnel ×1.4, the cozy room ×0.36, the den rotated -90°). It keeps the authored practicals (energy × scale²), adds the Key/Rim/Fill/Glow contract and `Mark_A`/`Mark_B`, and switches to EEVEE + AgX.
- The engine (`cast_ids`, `set_presets`, `build_assets`) merges these assets in. The editor catalog lists Matt, Freya, Mina and the 3 rooms. `tests/test_imported.py` covers the registry. 71 tests pass.
- Demo: `samples/imported-test` (Matt + Mina, neon_tunnel) renders through `render_plan.py`.
- **Known gaps:**
  - **Tasha has no rig**, so she isn't wired. The owner can auto-rig her (for example Mixamo, which needs their own account), then add her spec.
  - `matt.blend` is 1.6 GB (a 900k-vertex body × 149 morphs). That's expected, and it loads slowly.
  - The Rigify and ARP face moves are hand-tuned bone offsets. Freya's smile range is subtle.
  - Wide-shot framing was tuned for the seated stand-in, so standing characters sit low in frame.
  - The procedural (seated) cast doesn't suit the imported rooms.

## 9. Shots-AV Animation (style `shots-av`, 2026-11-11 to 2026-11-13, branch `feat/shots-av`)
A desk two-hander: you (a low-poly hero with the owner's likeness, Aayush Visuals purple `#7C3AED`) talking to an
AI buddy robot. Brief: `docs/prompts/03-shots-av-animation.md`. Ledger, decisions and evidence:
`docs/production/shots-av/PROGRESS.md` (read it first; it is the source of truth). Rubric: `RUBRIC.md` there.
**Status: P0-P8 done; the P7 benchmark won 10 of 10 rubric rows** (`docs/production/shots-av/p7/score.md`).

**Use it (editor):** `/shots-av` in the editor (dev server `reelforge-editor`, port 5190). Paste a script ("Me: ...",
"Claude: ..."), pick the buddy, room, your spot in the room, look and captions, then **Generate reel**: ElevenLabs
voices (the owner's key in Settings; each line's emotion becomes an audio tag), then the video timed to that audio.
Quality: Draft (about 0.27 s/frame), **Balanced** (default, about 1 s/frame, 1080x1920), Final (about 3.3 s/frame).
Restarting the dev server kills running render jobs.

**Use it (CLI):** `reelforge build-assets --style shots-av` (hero, 4 buddies, 12 rooms);
`reelforge run <project> --stage full [--draft | --quality cinema]`; `reelforge animatic <project>` (silent,
estimated timing); `reelforge shots-av catalog|plan|preview <project>`; `reelforge thumbnails --style shots-av`.

**Where things live:**
- Characters: `blender/shotsav/hero.py` (hero, every option in the `HERO` table: 6 hairs, 7 skins, glasses, beards,
  outfits), `buddies.py` (claude, chatgpt, figma, nova), `geo.py`; built on demand per option set by
  `engines/shots_av.ensure_hero`.
- Rooms: `blender/shotsav/rooms.py` (12: six original + six 3D gamer/editor rooms in `gamer_rooms.py`); everything
  behind the desk hangs off `RoomPivot`, moved by `performance.room_view` {pan, height, turn}; `room_pano.py` renders
  the editor's panorama picker into `assets/build/shotsav/thumbs/<room>_pano.jpg`.
- Camera: `reelforge/angles.py` (36 angles + the director that picks them per shot from mood, role and reuse; seeded
  per project, Reroll in the editor, per-shot override), `reelforge/direct.py::plan_shots_av` (cutting grammar,
  "reference" keeps the reference reel's five set-ups), `blender/camera_rig.py` (framing maths, moves).
- Acting, sound, captions, finish: `reelforge/buddy.py`, `engines/shots_av.py` (lip smoothing, loudness jaw,
  acting), `ambience.py` (beds, foley, voice reflections), `captions.py` (`build_ass_shotsav`, the 10 editor
  templates, hand placement and size, end card), `finish.py` (purple-safe grade, halo, vignette, -14 LUFS).
- Render tiers: `engines/shots_av.TIERS` read by `blender/looks/shotsav.py`; `render_plan.py ... bench` times frames.
- Editor: `editor/src/pages/shotsav/` (list, workspace, `Placers.tsx` for the room frame and caption placement).

**Decisions to keep:** Khronos PBR Neutral, not AgX (purple accuracy); neutral-warm key, never orange; buddies read
as their products with no traced logos; reference art is inspiration only, never a backdrop; Balanced is the default
full-size render; never reduce character quality (render settings only).

**Projects:** `projects/i-just-asked-you-to-fix-one-thing` (the owner's script, Editor night),
`projects/p7-bench-{reference,signature,morning}` (benchmark). Projects are git-ignored.

**Next steps (from the P7 score):** ~~a connected camera move~~ done 2026-11-14 (`camera.connect`); ~~moving background life~~ done 2026-11-14 (`blender/shotsav/life.py`) (cars, signs, monitor activity); ~~stronger
subsurface at phone size~~ done 2026-11-14 (`SKIN_SSS`); ~~draft speed~~ 2026-11-14: draft tier, 7.8 min for the 55 s P7 reel (about 6.9 min for 49 s; a minute over budget).


## 10. The old cast, wardrobe and sets moved into Shots-AV (2026-11-14)
Owner's call: the seven procedural characters (Kai, Rey, Dev, Mo, Aria, Zoe, Noor) are deleted; their 21 outfits and
the 13 environments live on inside Shots-AV. Matt, Freya and Mina (imported) stay in the Blender 3D style.
- **Outfits:** `blender/shotsav/hero.py` OUTFITS has 24 (the 3 brand ones + the old wardrobe redrawn in the hero's
  faceted style: Boxy black, Hoodie & cargos, Knit vest, Grey sweats, Track jacket, Puffer vest, Camel & black,
  Techwear, Varsity, Cardigan, Tee & beanie, Flannel layers, Cropped knit, Blazer & mini, Baby tee & cargos,
  Sporty zip, Butterfly top, Cream puffer, Trench, Cargo set, Sweater & beret). Each has its own colour
  (`OUTFIT_COLORS`, mirrored in `schema.AV_OUTFIT_COLORS`); new pieces: crew/V/turtle/lapel/rib collars, vests (tee
  sleeves), contrast sleeves, stripes, plaid, chest prints, a beanie (replaces the hair) and a beret. Only the 3 brand
  outfits are prebuilt; the rest build on demand.
- **Environments:** 25 Shots-AV rooms. The 10 old sets are `av_old_*` (code moved to `blender/shotsav/set_data.py` and
  `legacy_sets.py`: built in their default lighting, desk area cleared, pushed back 0.9 m). The 3 imported rooms are
  `av_imp_*` (`blender/shotsav/imported_rooms.py`, loaded from the owner's source files in `SRC_ROOT`, sightlines
  cleared by ray casts). The editor lists them as "Classic sets".
- **Removed:** `blender/cast.py`, `build_character.py`, `build_set.py`, `import_set.py`, two bakeoff scripts, the
  samples that used the old cast, the old projects, and every built file of the old cast and sets (about 2.5 GB).
- **Blender 3D style now:** cast = Matt, Freya, Mina; no environments of its own (the editor's Environments page and
  Set panel point to Shots-AV). `reelforge bench` and `samples/imported-test` need an environment again before they
  can render.
