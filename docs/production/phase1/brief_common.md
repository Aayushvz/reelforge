# Phase 1 bake-off: rules shared by both routes

Read first: `docs/production/phase1-spec.md`, `CLAUDE.md`, `blender/cast.py` (Kai's identity: tight black curls,
light stubble, thin silver chain, silver hoop in the left ear, boxy black open-collar shirt, warm tan skin,
deadpan/chill), and look at `references/characters/style/*.png` (the target look) plus
`docs/production/phase1/v1_kai/face_sheet.png` (today's baseline to beat).

## Output contract (both routes)
- Write one build script (path given in your route brief) that runs headless:
  `"$(cat tools/blender_path.txt)" -b [source] --python-exit-code 1 -P <script> -- <out.blend>`
  and produces `assets/build/bakeoff/kai_<route>.blend`. The script must be re-runnable from scratch.
- The output `.blend` has a collection **`CHAR_base`** holding everything the renderer needs, with:
  - `CHAR_root`, the root at the floor origin; the character faces **-Y**, up is +Z.
  - `Head`, an object whose `rotation_euler` nods/turns the head. `blender/render_plan.py` keys it.
  - `FaceCtrl`, an object with the **52 ARKit float custom properties** (`reelforge/arkit.py` `ARKIT_NAMES`), each driving visible deformation through drivers.
  - `FaceAnchor`, an empty at the face centre that follows the head, with custom property `head_height` (metres, chin to crown).
  - `EyeFocus`, an empty on the eye plane that follows the head.
  - Every face mesh tagged with custom property `face_part` = `head` | `teeth` | `tongue` | `eye` | `lid` | `lash` | `brow` (lids/lashes/brows only if separate objects).
  - Nothing outside `CHAR_base` should be needed. Rig widgets and helper objects must have `hide_render = True`.
- Real-world scale: Kai is an adult, about 1.75–1.85 m tall, standing in a relaxed A-pose. (The seated desk pose is Phase 2.)

## Your iteration loop (use it; it is how you'll be judged)
- Face sheets: `... -b assets/build/bakeoff/kai_<route>.blend --python-exit-code 1 -P blender/bakeoff/face_sheet.py -- docs/production/phase1/kai_<route> 24`
  This renders 17 poses at 85 mm, eye/mouth close-ups and a turnaround, all under one fixed portrait rig.
- Automated check: `... -P blender/bakeoff/face_check.py -- docs/production/phase1/kai_<route>/face_check.json`
  It must say **PASS**: no teeth, tongue or eye poke-through vs. neutral for any ARKit shape or common pair, and lids covering at least 98% of the eye at blink = 1.
- Look at your own sheets with the Read tool after every meaningful change, and compare them with the references.

## Scoring (what matters, in order)
1. Face likeness to the style references, 40%: sculpted planes on the brow, cheekbones, jaw and chin; a real nose (bridge, tip, nostrils); lips with a vermilion border and philtrum; ears; stylized-premium, not doll-like.
2. Expressiveness, 25%: laugh/smug/surprised/sad/angry/worried read clearly at phone size; visemes A/E/O/M are distinct; M fully sealed.
3. Eye quality, 15%: iris detail, a catchlight, lids that conform and close fully, gaze that works.
4. Rig/lip-sync, scalability to 7 characters × 3 outfits, render cost, licence, 20%.

## Hard rules
- Don't edit shared files: `blender/build_character.py`, `blender/cast.py`, `blender/render_plan.py`, `blender/bakeoff/face_sheet.py`, `blender/bakeoff/face_check.py`, anything in `reelforge/` or `tests/`. If a shared file blocks you, say so in your notes instead of editing it.
- Don't commit, push, download anything, or install anything. Never enable Blender auto-run scripts (`--disable-autoexec` on any third-party file).
- 4 GB GPU: keep test renders small (the sheet script already is), and don't run two renders at once.
- Write `docs/production/phase1/route_<x>_notes.md` as you go: what you built, how, measurements (tris per part, Eevee seconds per close-up frame, texture sizes), known defects, and anything a reviewer should look at.
- Done when: the build script runs clean from scratch, face_check says PASS, the sheets exist, and your notes are complete and honest about weaknesses.
