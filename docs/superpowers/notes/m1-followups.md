# Milestone 1: follow-ups from the final review (2026-10-31)

The final whole-branch review found the branch ready to merge, with no must-fix items. Gate status: **pipeline PASS, look PARTIAL**. Re-run the gate once the new character is in and the environment lighting has had a pass.

## Requirements for the Pixar-character sub-project
1. **Stand-in proportions are hard-coded.** Shot distances, `head + 0.18`, the −0.19 Y eye-plane focus offset, and the nod being an Euler rotation on a `Head` empty all live in `blender/render_plan.py`. The new character must:
   - keep the `FaceCtrl` contract: 52 ARKit custom properties, driving Faceit shape keys through drivers;
   - expose `FaceAnchor` and `EyeFocus` empties, parented to the head bone;
   - have shot distance derived from head size.
2. **ARKit-correct MBP.** `visemes.py` drives MBP with `mouthClose 0.7` and jaw 0. On a real ARKit head that pushes the lips through each other. Change it to `jawOpen≈0` plus `mouthPressL/R` plus `mouthRollLower/Upper`, add a 2–3 frame hold, and only ever pair `mouthClose` with a small `jawOpen`. Retune on the new head, not the stand-in.
3. **Audio2Face A/B.** Re-run the Audio2Face side-by-side comparison on the new head; the adapter hook is `out/a2f/<line_id>.json`. The stand-in's 2D mouth made the spike verdict inconclusive.

## Before Milestone 2
4. **Staleness:**
   - wipe `stills/` before a stills render;
   - add an mp3-hash check to the A2F overrides;
   - key the Whisper alignment cache on the mp3's sha1 plus the model size, not on mtime.
5. **Render caching and resume** (spec §3 and §7): hash `render_plan.json` together with the blend files, skip the render when nothing changed, and use `use_overwrite=False` for crash-resume.
6. **Schema hardening:**
   - a non-numeric intensity or pause should raise `PerformanceError`, not a bare `ValueError` (the Claude performance pass depends on this);
   - reject negative `pause_after`;
   - cap the number of characters at the available marks.
7. **Plan-contract test:** assert the full set of keys and shot fields in `render_plan.json` that `blender/render_plan.py` reads.
8. **Error handling:** wrap subprocess errors so they include stderr; log the voice source used for each line; prefer an imported mp3 when one exists.
9. **Housekeeping:**
   - in `.gitignore`, use `tools/*` plus `!tools/*.py`;
   - remove unused imports (`math` in `preview_character.py`, `Vector` in `build_night_city.py`);
   - add an `a2f` optional extra (numpy, onnxruntime).

## Environment look (survives the character swap)
- **Wide-shot bokeh:** at 35 mm and f/1.2 the circle of confusion is about 21 px, against about 87 px on the close-up. Cheat the wide f-stop to about 0.4–0.5 or pull focus closer, and check Eevee's `bokeh_max_size`.
- **Rim light** (`rim_w`) and **haze density**: retune after the new character is lit.
- **Not built yet (M2/M3):**
  - a per-mood grade (today only the light colours change), panic flicker, the reveal bloom spike;
  - Cycles for close-ups;
  - LUT, chromatic aberration, captions placed around faces, two-pass loudnorm, a bundled caption font.

## Lower-priority deferred minors
These are fine as Milestone 2 cleanups:
- the alignment edge cases: an unclosed `[`, and zip truncation;
- voice retry edge cases;
- the visemes test thresholds;
- tests for nods and nervous blinks;
- a hashlib-based blink seed;
- fps-independent blink and nod durations;
- a 1.5 s minimum shot length, and sub-shot push;
- caption regression asserts;
- assertions on the finish codecs;
- a resolution-relative halation radius;
- moving the `Code` brick-texture mapping into `bl_common`.

## Status (2026-11-04)
- **Done:** 1 (`FaceAnchor`/`EyeFocus`, shot distance from head height); 4 (stills/frames wiped before each render; Whisper cache keyed on the mp3's sha1); 6 (non-numeric intensity/pause → `PerformanceError`, negative pause rejected, at most 2 characters); 7 (`tests/test_plan_contract.py`); 8 partly (imported mp3 always wins over the API, voice source logged per line); 9 (`.gitignore` `tools/*` + `!tools/*.py`, `a2f` extra); two-pass loudness (`finish` corrects residual gain, up to 3 passes).
- **Also done:** 2 (MBP = jaw shut + press + roll, ~80 ms hold, no mouthClose).
- **Also done:** A2F overrides carry `audio_sha1` and are skipped when the take changed.
- **Also done:** 5 (render key = plan + blend/script size+mtime; complete output is skipped, a crash resumes with `use_overwrite=False`).
- **Also done:** 8 (Blender failures raise `BlenderError` with the last 25 output lines); wide shots use an f/0.5 cheat for bokeh.
- **Still open:** 3 (A2F A/B on the new head; the ONNX model is not on this machine, so check its download size and ask first), rim retune, the deferred minors.
