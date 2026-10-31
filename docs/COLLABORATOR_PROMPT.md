# Prompt for a collaborator's Claude (Claude Code, Max plan)

Paste everything below the line into Claude Code, opened in your clone of the repo.

---

You're continuing work on **reelforge**, a private project that turns a written script into a **cinematic, lip-synced, emotional 3D animated short**, mainly 9:16 for Instagram Reels and Shorts. Milestone 1, a working end-to-end pipeline, is done and merged. I'm a collaborator. My job now is to build three things to a **high, professional standard**:

1. **Character generator.** Turn reference images into stylized-premium (Pixar-like) 3D characters that are rigged and fully facially animatable.
2. **Environment generator.** Turn reference images into refined, cinematic, moody 3D environments.
3. **Editor.** A proper local 3D and video editor UI for building, previewing and rendering reels.

## Step 0: Get oriented (do this before anything else)
1. Read `CLAUDE.md`, `docs/HANDOFF.md`, `docs/superpowers/specs/2026-10-31-animated-reel-generator-design.md`, `docs/superpowers/notes/m1-followups.md` and `samples/look-test/REVIEW.md`. Skim `docs/superpowers/plans/2026-10-31-m1-look-test.md` for how the pipeline was built.
2. Look at the code layout: `reelforge/` (Python, standard library only), `blender/` (headless Blender scripts) and `tests/`.
3. **Set up my machine.** Work out my OS and GPU first; they may differ from the original Windows + RTX 4060 laptop.
   - Create `.venv`, then `pip install -e ".[dev,align]"`.
   - Check that `ffmpeg` and `ffprobe` are on PATH.
   - Download **Blender 4.5 LTS portable** into `tools/blender-4.5/`. Ask me before downloading.
   - Write its path into `tools/blender_path.txt`.
   - Run `.venv/Scripts/python -m pytest -q` (or `.venv/bin/python` on macOS and Linux). All tests must pass before you change anything.
4. Reproduce the look test so you can see the current baseline.
   - The voice mp3s aren't in git, so ask me for them, or generate any two short mp3s named `l01.mp3` and `l02.mp3` into `samples/look-test/out/audio/`.
   - Run `reelforge build-assets`, then `reelforge run samples/look-test --stage stills --draft`.
   - Look at the stills.
5. Give me a short summary of what exists, what you saw in the stills, and anything broken on my machine. Then start Step 1.

## Non-negotiable decisions (already made by the project owner; don't re-ask)
- **Engine:** Blender 4.5 LTS, run headless from Python. Not AI video, not Three.js, for final renders.
- **No paid tools or plugins.** Faceit, Character Creator, paid image-to-3D tiers and so on were explicitly rejected. Use free and open-source tools that run locally.
- **Claude never creates accounts or handles passwords or API keys.** If a tool needs a login, I do it.
- **Voices:** ElevenLabs, generated in the ElevenLabs web app. The pipeline imports mp3s from `out/audio/<line_id>.mp3` and aligns them locally with faster-whisper. The API path exists too, if a key is ever provided through an environment variable.
- **Ask before** any download over about 2 GB or any system-wide install (CUDA toolkit, TensorRT, drivers, Visual Studio).
- **Keep these contracts working:**
  - Characters expose `CHAR_root`, `Head` and `FaceCtrl`, where `FaceCtrl` carries **52 ARKit-named float custom properties** that drive the face through drivers.
  - Environments expose the lights `Key`, `Rim`, `Fill` and `Glow`; the emissive materials `ScreenMat` and `HoloMat`, each with a node named `Code`; and the marks `Mark_A` and `Mark_B`.
  - If you need to change a contract, change `blender/render_plan.py`, `reelforge/plan.py` and the tests together, and say so.
- The `reelforge/` core stays **standard library only**. Heavy machine-learning tools live in optional extras or in `tools/` scripts, imported lazily.
- **Token-aware:** use cheaper subagent models for mechanical tasks and the most capable model for design and visual judgment.

## Look target
Read `docs/HANDOFF.md` §4b. The owner's end goal is the ink.industries "First kiss effect V2" Pixar-like look; the reference stills go in `references/style/`. Those reels are AI-video generated. The owner knowingly chose Blender anyway, so aim as close as free 3D allows:
- hair cards with clumps and flyaways
- fabric with fuzz and sheen
- expressive cartoon faces with blush
- sunset or lantern lighting with atmospheric haze
- shallow depth of field

At every quality gate, say honestly how close you got. Don't propose switching to AI video unless the owner asks.

## Working method (follow strictly)
Use the **superpowers** skills, as the project did for Milestone 1:
**brainstorming** (one question at a time, propose 2–3 approaches with a recommendation) → a written **spec** in `docs/superpowers/specs/` → **writing-plans** (bite-sized TDD tasks with complete code) in `docs/superpowers/plans/` → **subagent-driven-development** (one implementer per task, plus a spec and quality review after each, plus a final whole-branch review) → **finishing-a-development-branch**.

- Treat each of the three deliverables as its **own sub-project**, with its own spec, plan and feature branch. Build them in this order: **characters → environments → editor**. Characters are the biggest quality jump, and the editor needs both to exist.
- **Visual quality gates are mandatory.** Render stills, *look at them*, and judge them honestly against the references. Iterate within a stated budget of rounds, and show me the images. Never claim something looks good without having viewed the render.
- Commit often, on feature branches. Push to `origin` (the private GitHub repo) when a sub-project is merged.

## Sub-project A: Character generator (start here)
**Goal:** `reelforge make-character references/characters/<name>.png` produces `assets/build/characters/<name>.blend`. The result is a stylized-premium character that drops into the existing pipeline and talks, emotes and blinks convincingly.

The input folder is `references/characters/`; I'll add front-facing, full-body, plain-background images.

**Proposed approach.** Validate it in brainstorming; improve it if you know better free options.
1. **Image to mesh:** use Hunyuan3D-2 (the mini variant if VRAM is under about 12 GB) or another open-source image-to-3D model that runs locally to get a textured mesh. Clean it up: remesh, recalculate normals, decimate to animation-friendly density, and fix the texture.
2. **Make the face animatable.** Generated meshes have painted-on eyes and mouths, so add real eyeballs with catchlights, eyelids, a mouth cavity with teeth and tongue, and real brows. Then generate **the face shapes the pipeline uses**, at minimum:
   - jawOpen, mouthClose, mouthFunnel, mouthPucker
   - mouthSmile L/R, mouthFrown L/R, mouthStretch L/R, mouthPress L/R, mouthRollLower/Upper
   - eyeBlink L/R, eyeWide L/R, eyeSquint L/R, eyeLook* (gaze)
   - browInnerUp, browDown L/R, browOuterUp L/R
   - cheekSquint L/R, noseSneer L/R

   Wire each one to the matching `FaceCtrl` property with drivers. Shapes should look appealing and cartoon-expressive, not merely technically correct.
3. **Body rig:** use Rigify, UniRig or a similar free auto-rigging tool, with sensible weights. It must support head nods and the gesture library planned for Milestone 2: shrug, chin-rest, lean, facepalm, typing.
4. **Outfits and look variants:** at least swappable colour and material parameters for skin, hair and clothing. Ideally, separate outfit meshes.
5. **New requirements from the M1 review** (see `m1-followups.md`):
   - Expose `FaceAnchor` and `EyeFocus` empties on the head bone.
   - Make `render_plan.py` derive shot distance, aim and focus from them instead of the hard-coded stand-in numbers.
   - Make the MBP viseme ARKit-correct: jaw closed, press, roll, and a 2–3 frame hold.
6. **Fallback:** if the quality of image-to-3D faces disappoints after honest iteration, propose the Blender Studio CC-BY stylized rigs (Rain, Ellie) as bases, adapted to my references.

**Quality bar:** compare against `references/characters/*` and the Pixar-style examples. Show turnaround stills, an expression sheet (neutral, happy, sad, surprised, angry, smug, blink), and a lip-sync test clip using the look-test audio. Re-run the Audio2Face vs viseme comparison on the new head (`out/a2f/<id>.json` drop-in, via `tools/a2f_fetch.py`).

## Sub-project B: Environment generator
**Goal:** `reelforge make-environment references/environments/<name>.png` produces `assets/build/environments/<name>.blend`. The environment satisfies the environment contract and looks as refined as the references, the NMXWZ-style reels: glowing practical lights, deep blacks, soft bokeh, haze.

**Proposed approach:**
- Depth Anything V2 (or a similar local depth model) turns the reference into a depth map. The depth map displaces a plane or mesh into a **2.5D backdrop** with real parallax and depth of field.
- Real 3D foreground geometry goes in front: desk, screens, props, and the floor where the character sits. That keeps the mood light crossfades working.
- Place the lights to match the reference's lighting, plus the `Key`, `Rim`, `Fill` and `Glow` contract lights and the `Mark_A` and `Mark_B` character marks.
- Fix the known look gaps:
  - **Wide shots:** bokeh. Cheat the f-stop to about 0.4–0.5 or pull focus, and check Eevee's bokeh clamp.
  - **Rim light:** make it visible.
  - **Haze:** make it subtle but present.
  - **Face lighting:** sculpt it with key and rim; don't light it flat.
- Ship at least 4 presets: night-city desk (rebuilt to a higher standard), rainy café, sunset loft, cozy bedroom.

**Quality bar:** stills at wide, medium and close-up, in every mood (calm, success, panic, awkward, reveal, sad), compared side by side against the reference.

## Sub-project C: Editor (a proper 3D and video editor UI)
**Goal:** a **local web app** that runs on localhost, launched by `reelforge editor`. A non-technical creator uses it to make a reel end to end. It must feel like a real, polished creative tool, not a form.

**Must have:**
- **Project manager.** Create and open projects; each project is a `samples/<project>/`-style folder holding `performance.json`.
- **Script panel.** Edit lines, speaker, emotion, intensity, mood, pause and punchline. Show validation errors from `reelforge/schema.py`.
- **Cast panel.** Pick characters and outfits and colours (from Sub-project A assets), with thumbnails.
- **Set panel.** Pick an environment and default mood (from Sub-project B), with thumbnails.
- **Voice panel.** Upload or import mp3s per line, play them, and show the waveform and alignment. Re-voicing one line re-aligns only that line.
- **Timeline.** A track-based, scrubbable timeline with:
  - a dialogue waveform
  - shot blocks: change the kind or lens, drag cut points
  - mood segments
  - caption chunks
  - emotion and gesture markers

  Edits write back to plan overrides. Undo and redo.
- **3D viewport preview.** Three.js (or similar) loading glTF exports of the scene and character. It needs a camera per shot, scrubbing in sync with the timeline, and face animation played from the face tracks. It's a preview, so it can be lower fidelity; final renders always go through Blender.
- **Stills gate.** Render one still per shot through Blender, then approve or reject each.
- **Render queue.** Draft (Eevee) or final; aspect ratio 9:16, 16:9, 3:4 or 1:1; live progress with an estimated finish time; play and download the result.
- **Backend.** A small local server (Node or Python; justify the choice) that wraps the existing `reelforge` CLI and stages, streams job progress, and keeps all state in the project folder. No database.

**Design quality:** a dark, modern, professional editor aesthetic, in the spirit of DaVinci Resolve, CapCut desktop or Figma. Use the frontend-design and impeccable skills. Make it responsive down to laptop widths, with keyboard shortcuts for the timeline. Test it in a browser and look at screenshots before calling any screen done.

## Definition of done (for each sub-project)
- Spec and plan are committed, every task is reviewed, the final review is clean, all tests pass, and the branch is merged and pushed.
- The look test, and one new sample project using a new character and environment, renders end to end via both the CLI and the editor.
- A short `REVIEW.md` per sub-project records stills or screenshots, honest pass/fail verdicts against the references, and open items.
- `docs/HANDOFF.md` is updated with what changed and what's next.

Start with Step 0 now, then brainstorm Sub-project A with me.
