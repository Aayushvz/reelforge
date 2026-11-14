# Thumbnail Generator: design (2026-11-15)

## Goal
Make a cover image from any video frame, in the style of the Shots-AV reference covers. The style is:
- a big two-line headline at the top left: line 1 cream ("FIX THE"), line 2 purple with a trailing period ("NAVBAR.");
- a bold, heavy sans font;
- an optional dark rounded caption pill above it, carrying the spoken line.

After a render, the editor drafts a cover automatically.

## Decisions (agreed with the owner)
- **Renderer:** a browser canvas. One function, `drawCover()`, draws both the live preview and the export at the exact preset size. Imported videos stay in the browser. No new dependencies.
- **Extras in this PR:** auto variants, and Reels/Shorts/YouTube safe-zone overlays.
- **Later:** face-aware crop, export of all sizes at once, outline and shadow, gradient, stickers, saved styles, undo.

## Units
1. **`reelforge/cover.py`** (standard library only)
   - `headline(text)` returns `[line1, line2]` or `None`. The rules run in order:
     1. imperative verb + `the`/`a`/`my`/`this` + noun gives `FIX THE / NAVBAR.`;
     2. `the`/`a` + noun + comparative or state word gives `LOGO / BIGGER.`;
     3. two strongest content words, in order.
     - Names said to someone ("Claude, ...") and filler words are removed first.
     - Line 2 always ends with a period.
   - `pick_frames(plan, n)` scores the shots whose subject is the hero (`me`, or the first character):
     - score = `framing.head` (face size) + 0.3 if the hero speaks + 0.1 × the push-in amount;
     - the frame is 40% into the shot;
     - it returns up to `n` distinct shots, best first.
   - `draft(project_dir)` reads `performance.json` and `out/render_plan.json` and returns `{video, fps, width, height, variants: [{headline, caption, time, frame, shot}]}`:
     - up to 3 variants;
     - the headlines come from different lines (the hook line first);
     - the frames come from different shots.
   - `write_draft(dir)` writes `out/cover.json`.
   - **Clean frames:** when `out/frames/` exists, the draft points at the rendered frame (`still`, and `frames` for scrubbing; frame N is `{N+1:04d}.png`). That frame has no burned-in captions, which would fight the cover's own text. Shots whose eyes fall outside the frame (hands inserts) are never picked.
2. **CLI:** `reelforge cover <project>` prints `SHOTSAV_JSON {...}`.
3. **Server (`editor/server/api.ts`)**
   - After a successful full run, the server runs `reelforge cover` (best effort; a failure is only logged).
   - `GET /api/projects/:id/cover` returns `out/cover.json`, drafting on demand if it's missing (404 if there is no final video).
   - `pipelineEnv` sets `PYTHONPATH=REPO`, so worktrees run their own pipeline code.
4. **`editor/src/lib/cover.ts`**
   - `CoverDoc` type, `SIZE_PRESETS`, `FONTS`, `defaultDoc()`, `applyVariant()`, `drawCover(ctx, doc, frame, w, h, {safeZone})`, `renderCover(doc, frame, type)`.
   - Positions are fractions of W and H and sizes are fractions of the short side, so a doc renders the same at any preview scale.
5. **Page `/thumbnails`** ("Thumbnail Generator", in the main nav)
   - **Source:** a local video file, or `?project=<id>`, which loads the project's final video and draft.
   - **Scrubber:** a range input, ±1 frame buttons, and a time readout. Variant cards apply a draft's headline, caption and frame.
   - **Canvas:**
     - drag the text block to move it;
     - drag the frame to set its focus when it is cropped;
     - arrow keys nudge the selected layer (a keyboard alternative to dragging);
     - nine snap presets.
   - **Clean frame switch** (projects with `out/frames`): the scrubber shows the rendered frame, before the final grade and the captions.
   - **Remembered look** (localStorage): font, sizes, spacing, colours and pill style. Positions, crop and size are never remembered; they belong to one cover.
   - **Long words** shrink to fit the frame instead of running off its edge.
   - **Inspector:** size preset or custom W×H; headline lines with a colour per line; font, size, letter spacing and line spacing; caption pill on/off, text and colours; the safe-zone overlay (Reels, Shorts, YouTube; preview only); and Export PNG/JPG.
6. **Auto-cover card:** shown in the Shots-AV workspace when a full render job finishes, and in the Render page's Result panel whenever a final video exists. It shows a preview drawn by `drawCover`, with **Download PNG** and **Edit in Thumbnail Generator**. If no draft exists, there is no card.

## Testing
- **pytest:** the headline rules (both reference lines, name removal, fallback, period), the frame scoring on a synthetic plan, and `draft()` on a temporary project.
- **Editor build:** `tsc -b && vite build`.
- **Browser check:** on `projects/i-just-asked-you-to-fix-one-thing`.
