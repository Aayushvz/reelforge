# Production prompt for Dhairya's Claude (2026-11-04, v2)

Paste everything below the line into Claude Code (Max plan), opened in your up-to-date clone (`git pull` first). This is a long, multi-session job. Work through it phase by phase, and keep the progress ledger described below so any session can resume.

---

# Mission
You're the lead technical artist and engineer on **reelforge**: script in, cinematic 3D animated reel out (Blender 4.5, headless). Your job is to take the cast and sets from **v1 placeholder quality to production quality**:

- **All 7 characters × 3 outfits (21 looks)** match the owner's stylized-sculpt references, at the level of a premium animated studio short. "Realistic" here means the **rendering**: physically plausible materials, light, skin, hair and cloth on stylized, caricature designs. It does not mean photoreal people.
- **All 10 environments × 3 lighting presets (30 looks)** are cinematic: depth, atmosphere, practical lights, soft bokeh, rich colour. Each needs to hold up in wide, medium and close-up shots, and look good on a phone at 1080×1920.
- **The editor shows and uses the real assets end to end.**
- Everything is **optimized**: fast enough to render reels on an RTX 4060 laptop (8 GB VRAM), with zero visual or functional regressions.

"No mistakes" is enforced by process, not by hope. Every deliverable passes automated checks, a visual review, and an independent reviewer on a different model before it counts as done.

# Read first (in this order)
1. `CLAUDE.md` (ground rules), `docs/HANDOFF.md`, `docs/superpowers/specs/2026-11-01-cast-sets-editor-brief.md`, `docs/superpowers/specs/2026-10-31-multi-style-engines.md`, `docs/superpowers/notes/m1-followups.md`, `editor/README.md`.
2. **Look at these images with the Read tool:**
   - `references/characters/style/*.png`: **the target**, a stylized sculpt. Long necks, strong jaw and cheek planes, slightly oversized heads, big expressive brows, sculpted clay or vinyl hair (curls and swoops as readable shapes), soft subsurface skin with stubble and pores, full bodies with legs, hands and natural poses, clean studio key plus rim light.
   - `samples/previews/cast_lineup.png`: **today's v1**. Blob torsos, no legs, stiff "T" arms, small heads, basic faces. The hair is the best part, but it's still below target.
3. `blender/cast.py`, `blender/build_character.py`, `blender/sets.py`, `blender/build_set.py`, `blender/render_plan.py`, `blender/preview_*.py`, `reelforge/cli.py`, and `tests/`.
4. Run `.venv/Scripts/python -m pytest -q`; it should give 63 passed. Then rebuild with `reelforge build-assets` to confirm the baseline works on your machine.

# Hard rules (never break these)
- **Contracts stay intact**, or change in lockstep with code and tests:
  - characters expose `CHAR_root`, `Head`, `FaceCtrl` (52 ARKit float properties driving the face), `FaceAnchor`, `EyeFocus`;
  - sets expose lights `Key`, `Rim`, `Fill`, `Glow`, materials `ScreenMat` and `HoloMat` (node `Code`), and marks `Mark_A` and `Mark_B`;
  - `render_plan.json` keys are pinned by `tests/test_plan_contract.py`.
- **No paid tools or services** for this style. Use only free, open-source tools that run locally. **Ask the owner before** any download over 2 GB, any system-wide install (CUDA toolkit, drivers), or any licence other than permissive or CC-BY. Record attributions in `ASSETS_CREDITS.md`.
- **Every character is original.** The references are style only; never a likeness of a real person or an existing IP character.
- `reelforge/` stays **standard library only**. Machine-learning tools go in optional extras or `tools/` scripts, imported lazily.
- Claude never handles passwords or API keys and never creates accounts.
- Don't change the look direction (style, proportions, palette) without the owner's approval of a side-by-side comparison.

# How to work (multi-model, verified)
- **Workflow:** superpowers skills, i.e. brainstorming → spec → writing-plans → subagent-driven-development (implementer plus independent spec and quality reviewer per task, plus a final whole-branch review) → finishing-a-development-branch. **One feature branch and one PR per phase.**
- **Use multiple models deliberately:**
  - **Opus:** look design, route decisions, visual judgment, final reviews.
  - **Sonnet:** implementation of non-trivial Blender or editor code, and task reviews.
  - **Haiku:** mechanical, fully specified tasks (transcription, tests, renaming, batch scripts).
  - A **reviewer always runs on a different model from the implementer.**
  - Run independent subagents in parallel, but **never let two writers touch the same files.** For example, character, set and editor work can run in parallel on separate branches.
- **Bake-offs before commitments.** When a choice matters (image-to-3D model, hair technique, skin shader, rig tool, render settings), prototype 2–3 options on ONE test asset, render them side by side with the reference, score them, recommend one, and get the owner's yes. Then scale up.
- **Progress ledger:** keep `docs/production/PROGRESS.md` updated after every task: phase, task, status, commit, verdict, open issues. Any new session resumes from it and from `git log`. Never redo completed work.
- **Credits:** prefer the cheapest model that can do each task well, keep prompts lean, and hand subagents files rather than long pasted context.

# Quality system ("no mistakes")
Every asset has an automated **validator** plus a **visual gate**:
1. **Validators** (a new `blender/validate_*.py`, run headless and in CI-style tests). For each `.blend`, check:
   - every contract object and property exists; all 52 ARKit properties drive something visible;
   - no non-manifold or inverted normals on visible meshes; no missing textures or links;
   - polygon and texture budgets: character ≤ about 120k tris per outfit, 2K textures; set ≤ about 1.5M tris;
   - the scene opens and renders one Eevee frame in under N seconds on the reference machine;
   - the deformation test passes: all face shapes at 1.0 and the rig at extreme poses produce no intersections through the cheeks, lips or eyelids (sample-based check plus a render).
2. **Visual gates.** Contact sheets are rendered by script, viewed by you, and compared side by side with the references. Each gets a written PASS/PARTIAL/FAIL verdict with specifics, in a `REVIEW.md` per phase.
3. **Independent review:** a reviewer subagent on a different model looks at the same sheets and the diff, and lists defects. Fix them, then re-gate. Use at most 3 fix rounds per issue, then escalate to the owner with the images.
4. **Regression:** after every phase, re-render the regression set (`samples/look-test`, `cafe-test`, `duo-test`, `talk-*`) and diff it against the previous approved stills. Any unexplained change is a bug.

# Phase 1: character look route (bake-off on Kai)
Build Kai three ways, at the same pose and lighting as the references:
- **(a) Image-to-3D:**
  - Make a clean front-facing reference of Kai in the target style (draw it, or paint over a reference, as a style mood board).
  - Run a free local image-to-3D model. Bake off **Hunyuan3D-2 mini** against at least one alternative (TRELLIS, or another open model that fits 8 GB).
  - Retopologize to animation-friendly quads, around 30–60k for the head and body.
  - Bake the textures; add eyes, eyelids, a mouth cavity, teeth and tongue.
- **(b) Hand-built procedural v2:**
  - A real stylized base body: legs, hands with fingers, shoulders, a natural A-pose.
  - A sculpted caricature head built with geometry nodes, sculpt-by-script and shape keys: long neck, jaw and cheek planes, nose and brow volumes, ears.
  - Sculpted hair volumes and cloth with real thickness and folds.
- **(c) A free CC-BY base** (Blender Studio stylized rigs, such as Rain or Ellie), restyled to match.

Score each route on: likeness to the style references, face expressiveness, rig and lip-sync quality, how well it scales to 7 characters and 21 outfits, render cost, and licence. Recommend a route, show the owner the side-by-side, and wait for approval.

# Phase 2: full cast production (7 characters × 3 outfits)
With the approved route, build **Kai, Rey, Dev, Mo, Aria, Zoe and Noor**. Keep their identities from `blender/cast.py` and the brief: curls and chain; curls, beard and glasses; fade and stubble; messy hair and round glasses; long dark hair and hoops; ponytail, freckles and blush; sleek bob or braids and gold jewellery.

For each character:
- **Head:** caricature proportions, sculpted brows, a nose and lip shapes with clear planes. Skin is a layered shader: subsurface, a roughness map, stubble or pores, subtle colour zones (warm cheeks, ears and nose).
- **Eyes:** separate cornea and iris with refraction or parallax, a wet-line, and catchlights. Eyelids close fully and follow the eyeball. Gaze follows `eyeLook*`.
- **Mouth:** teeth, tongue and a mouth cavity, so open vowels read as believable.
- **Face shapes (all 52 ARKit):** appealing, cartoon-expressive shapes with **no intersections**. Also correctives for the common combinations: smile + jawOpen, blink + squint, pucker + jawOpen.
  - Visemes are ARKit-correct: MBP is lips pressed with the jaw shut; FV is lower lip to teeth; O/U is rounded.
  - The emotions read clearly at phone size: laugh, smug, surprised, sad, angry, worried, deadpan.
- **Hair:** sculpted, clump-based volumes (or hair cards) with a tangent-aware shader, roughness variation and a rim-catching sheen. It must not clip the head or clothes.
- **Body rig:** Rigify (or the approved tool) with clean weights, working hands (fingers), a head and neck that support nods, and the gesture library planned for Milestone 2: shrug, chin-rest, lean in, facepalm, typing, point, arms crossed.
- **Wardrobe (Gen-Z), 3 outfits each, 25+ items in total:** hoodies, boxy shirts, cargos, wide-leg jeans, track jackets, puffers, knit vests, cardigans, cropped knits, blazers, mini skirts, sneakers, caps, beanies, chains, hoops, glasses, watches.
  - Cloth has thickness, seams and hems, sculpted folds or a cloth-sim bake, and fuzz or sheen on knits and fleece.
  - The slot system is `top`, `outer`, `bottom`, `shoes`, `accessories`, with editor-recolourable material parameters.
  - **No clothing intersections** in the rest pose or any gesture pose; the validator checks this.

**Deliverables per character:**
- a turnaround (front, ¾, side, back) in each outfit;
- an expression sheet (neutral, laugh, smug, surprised, sad, angry, worried, blink, and the talk shapes A, E, O, M);
- a gesture sheet;
- a 5-second lip-sync clip (`samples/talk-<name>`).

**The cast lineup is re-rendered** next to `references/characters/style/` and the v1 lineup.

# Phase 3: environments (10 sets × 3 lighting presets)
Sets: night-city desk, bedroom or gaming room, rooftop skyline, café by the window, lantern-lit old-town street, subway platform, campus classroom, startup office, night convenience store, beach pier. The lighting presets are listed in `blender/sets.py` and the brief.

For each set:
- **Composition:** a believable, art-directed layout with foreground, midground and background layers, at least 3 practical light sources, story props, and clutter with intent. Real 3D foreground where the characters stand, plus a depth backdrop or modelled background for distance.
  - Optionally use Depth Anything V2 to build the 2.5D backdrop from a generated or painted plate, after a bake-off against fully modelled backgrounds.
- **Lighting per preset:** motivated key, fill and rim; the characters' faces must be **sculpted, not flat**. Use volumetric haze in the right amount, emissive practicals that bloom, coloured bounce, and night versus golden-hour colour stories. Mood crossfades (`moods.py`) must still work.
- **Materials:** PBR with roughness variation, wear, wet surfaces where rainy, and glass with reflections.
- **Camera:** camera anchors for wide, medium and close-up. Wides must show soft bokeh (use the f/0.5 cheat already in the code), close-ups keep the face sharp, and the top quarter stays clear for captions.

**Deliverables per set:** a contact sheet of 3 presets × 3 framings with 2 characters in place, plus one 5-second test render using the new cast.

# Phase 4: performance and optimization
- Profile Eevee render times per framing and set. The target is a 45-second 9:16 reel in **≤ 30 minutes at final quality** on the RTX 4060 laptop, and ≤ 8 minutes in draft.
- Use texture budgets and mipmaps, instancing for repeated props, light-count and shadow budgets, and clamped volumetrics. Decimate background assets with LODs. Bake what can be baked.
- Keep VRAM at 7 GB or less; out-of-memory errors are build failures.
- Add a `reelforge bench` command that renders a fixed shot per set and character and reports seconds per frame and peak memory. Record the results in `docs/production/PERF.md`.

# Phase 5: editor integration (real assets, end to end)
- Add `reelforge thumbnails`. It renders portrait and full-body thumbnails per character and outfit, and a preview still per set and lighting preset, into `assets/build/thumbs/`, cached by blend hash.
- The editor shows the real thumbnails (SVG placeholders only as a fallback) on the Characters, Cast, Environments, Set and Library screens.
- **Verify the wiring.** The cast, outfit, recolours, set and lighting picked in the editor must reach `performance.json` and **visibly change the render**. Fix anything still disconnected; the editor README lists gaps.
- Browser-test every affected screen at 1440 and 1920 width, with screenshots, and keep the dark, minimal, no-AI-slop design system.

# Phase 6: ship
- Update `README.md`, `docs/HANDOFF.md`, `editor/README.md`, `ASSETS_CREDITS.md` and `docs/production/PROGRESS.md`.
- Publish the build as a GitHub Release asset (`gh release create assets-vN cast-build.tar.gz ...`, noting the source commit), so the owner can download it instead of rebuilding.
- Merge each phase's PR only after its gate passes. Push.

# Definition of done
- All 21 character looks and all 30 set looks pass their validators and visual gates, with independent-review sign-off and REVIEW.md verdicts of PASS (or PARTIAL with the owner's explicit acceptance).
- A new sample reel, `samples/showcase`, uses 2 new characters in 2 sets with a mood change. It renders cleanly via both the CLI and the editor and looks like a premium stylized short at phone size.
- The full test suite is green with new tests for every command and validator, and the regression stills are approved.
- The performance targets are met and recorded.

**Start now:** read the docs, view both reference images, run the tests and the baseline build, create `docs/production/PROGRESS.md`, then brainstorm **Phase 1** with the owner.
