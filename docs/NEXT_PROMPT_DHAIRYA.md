# Next-session prompt for Dhairya's Claude (2026-11-04)

Paste everything below the line into Claude Code, opened in your up-to-date clone (`git pull` first).

---

You're continuing **reelforge**: script in, cinematic 3D animated reel out. Read `CLAUDE.md`, `docs/HANDOFF.md`, `docs/superpowers/specs/2026-11-01-cast-sets-editor-brief.md` and `docs/superpowers/notes/m1-followups.md` first. Then look at the two images that define the job:
- `references/characters/style/*.png`: **the target look**, a stylized sculpt. Long necks, strong jaw and cheek planes, slightly oversized heads, expressive brows, sculpted clay or vinyl hair, soft skin, full bodies with legs and natural poses.
- `samples/previews/cast_lineup.png`: **where v1 is today** (Kai, Rey, Dev, Mo, Aria, Zoe, Noor). It works, but it's far from the target:
  - blob torsos and no legs;
  - stiff "T" arms;
  - small heads with basic faces.

  Hair reads best, but is still not at reference quality.

The owner's verdict: **the characters must look like the references. That's the top priority.** Use the superpowers workflow (brainstorm → spec → plan → subagent-driven development with reviews), with one feature branch and one PR per item. Keep the existing contracts working:
- `CHAR_root`, `Head`, `FaceCtrl` (52 ARKit properties), `FaceAnchor`, `EyeFocus`;
- the set lights, materials and marks.

The rules in `CLAUDE.md` apply, including **no paid tools** for this style and **ask before downloads over 2 GB**.

## Priority 1: character quality pass (the big one)
Goal: all 7 characters × 3 outfits look like `references/characters/style/` while staying riggable and lip-syncable.
1. **Decide the route in brainstorming, with evidence.** Prototype ONE character (Kai) both ways, and show me the stills side by side with the references:
   - **(a) Image-to-3D:** run Hunyuan3D-2 (the mini variant fits 8 GB) or a similar free, local model on a generated or drawn reference of Kai. Then add real eyes, eyelids, a mouth cavity, teeth, the 52 ARKit shapes and a body rig (Rigify or UniRig).
   - **(b) A much better procedural base:** a proper stylized base body with legs, hands and natural rest-pose arms; a sculpted caricature head (long neck, jaw planes, nose and brow volumes); sculpted hair shapes; cloth with thickness, folds, and sheen or fuzz.
   - **(c) A free CC-BY base** (Blender Studio rigs) restyled to match, as a fallback.

   Recommend one route and wait for the owner's yes.
2. Roll the chosen route out to all 7 characters and all 21 outfits. Keep each character's identity from `blender/cast.py` (hair, beard, glasses, colours).
3. For each character, deliver:
   - a turnaround (front, ¾, side), full body;
   - an expression sheet: neutral, laugh, smug, surprised, sad, angry, blink, and the talk shapes A/O/M;
   - a 5-second lip-sync test from `samples/talk-<name>`.

   Also fix the MBP and blink look on the new heads, and re-run the Audio2Face vs viseme comparison (follow-up 3; check the model's download size and ask first).
4. **Quality gate:** put the new lineup next to the references and the v1 lineup, and give an honest verdict on how close it is. Iterate at most 3 rounds per issue, then report.

## Priority 2: the editor shows the real characters and sets
Today the editor's Characters, Cast and Environments screens show **SVG placeholder silhouettes** tagged "Concept". Replace them with real renders:
- Add `reelforge thumbnails`, which renders, through the existing `blender/preview_character.py` and `preview_set.py`:
  - per-character, per-outfit portrait and full-body thumbnails;
  - per-set, per-lighting preview stills.

  Write them to `assets/build/thumbs/` and cache them by blend hash.
- The editor backend serves them; `CharacterThumb` and the environment cards use the real image when it exists and fall back to the SVG.
- **Verify the wiring end to end.** A cast, outfit, set and lighting picked in the editor must reach `performance.json` (`model`, `outfit`, `environment`, `lighting`) and change the actual render. The editor README says some selections "aren't used by the renderer yet"; fix whatever is still disconnected.
- Check it in a real browser (screenshots) at desktop width.

## Priority 3: sets quality pass
- Render wide, medium and close-up for each of the 10 sets × 3 lighting presets, with the new cast in frame.
- Fix the known gaps: a visible rim light, subtle haze, sculpted face light (not flat), and depth and bokeh on wides.
- Compare against the mood of the ink.industries references described in `docs/HANDOFF.md` §4b.
- Deliver a contact sheet per set, and an honest verdict.

## Priority 4: share built assets with the owner
The owner rebuilds locally with `reelforge build-assets` (about 600 MB+, git-ignored). After each quality milestone, also publish the build as a GitHub Release asset (`gh release create assets-vN ...`), noting the commit it was built from, so the owner can download it instead of rebuilding.

## Working agreements
- Show images before claiming quality. Every PR includes its stills or contact sheets and an honest REVIEW.md.
- Keep `reelforge/` standard library only. Keep the full test suite green (63 tests today) and add tests for new CLI commands.
- Update `docs/HANDOFF.md`, `README.md` and the editor README at the end of each item.
- Ask the owner before any decision that changes the look direction, adds a dependency over 2 GB, or costs money.

Start by reading the docs and both images, then brainstorm Priority 1 with the owner.
