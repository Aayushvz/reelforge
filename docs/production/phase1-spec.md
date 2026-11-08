# Phase 1 spec: character look route (bake-off on Kai)

Status: **draft for the owner's approval** (2026-11-08). Nothing in Phase 2 starts until a route is approved.

## Goal
Pick the route that gives the best **face** (the owner's top priority) at a cost that scales to 7 characters × 3
outfits, by building Kai two ways and judging them side by side with `references/characters/style/`.

## Routes in this bake-off (decided 2026-11-08)
| Route | What it is | Runs here? |
|---|---|---|
| **(b) Procedural v2** | Extend `blender/build_character.py`: a real base body (legs, hands, A-pose), a denser hand-shaped head with edge loops, cornea/iris/wet-line eyes, card lashes and brows, sculpted hair volumes, cloth with thickness. | Yes |
| **(c) CC-BY base** | Restyle Blender Studio's **Rain v3** rig (CC-BY, 64 MB, `tools/third_party/rain_v3/`, not committed) into Kai: adult male proportions via shape keys/lattice (longer neck, broader jaw, cheek planes), new hair, stubble shell, outfit. | Yes |
| (a) Image-to-3D | Hunyuan3D-2 mini / TRELLIS from a Kai concept image, retopo, bake. | **Later**, on an 8 GB GPU; same rubric |

### What we learned about Rain v3 (route c)
- About 103k tris total, inside the ~120k budget; the head is 12.6k tris before subdivision (well short of the 60% head target, so the head gets densified).
- It has a full body, a separate cornea/eyes/eyebrows/lashes, gums, tongue, finger and body correctives, and a CloudRig armature (2,166 bones).
- Its face is **bone-driven, not ARKit**. Two options:
  - **c1:** bake 52 ARKit shape keys from bone poses, then drive them from `FaceCtrl` (keeps our contract; per-character sculpt fixes on top).
  - **c2:** drive face bones from `FaceCtrl` directly.

  c1 is recommended: shape keys are cheaper at render time and easy to validate.
- It renders in Blender 5.2 with its textures, with auto-run scripts disabled. Its `cloudrig.py` UI script isn't needed for rendering.
- **Originality:** Kai must not read as Rain. The restyle changes head shape, proportions, hair, palette and wardrobe, and is credited in `ASSETS_CREDITS.md` ("Rain Rig (CC) Blender Foundation | studio.blender.org").

## Deliverables per route (same pose, same lights, same camera)
1. 85 mm face sheet: neutral, laugh, smug, surprised, sad, angry, worried, deadpan, plus visemes A/E/O/M, blink, and gaze L/R/U/D.
2. Extreme close-ups of the eyes and mouth.
3. Turnaround (front, ¾, side, back) in outfit 0.
4. A 5-second talking close-up through the real pipeline (`samples/talk-kai`).
5. The automated face check: all 52 shapes at 1.0, plus common pairs; no lip, lid or teeth intersection; lids fully closed at blink = 1.
6. Measured cost: tris, texture memory, Eevee seconds per frame, and Cycles seconds per frame for a close-up (R2).

## Scoring (from the prompt)
| Criterion | Weight |
|---|---|
| Face likeness to the style references | 40% |
| Expressiveness (emotions read at phone size) | 25% |
| Eye quality (cornea, catchlights, lids, gaze) | 15% |
| Rig / lip-sync quality, scalability to 21 looks, render cost, licence | 20% |

Scored by me (Opus) and an independent reviewer subagent on a different model, from the same sheets. Disagreements over 1 point are re-checked against the images.

## Gates before asking the owner
- Both routes' sheets rendered by script and stored under `docs/production/phase1/`.
- `REVIEW.md` with per-criterion scores, defects and a recommendation.
- The tests are still green; existing contracts (`CHAR_root`, `Head`, `FaceCtrl`, `FaceAnchor`, `EyeFocus`) hold for both prototypes.

## Hardware notes
- **GPU:** an RTX 3050 with 4 GB. Cycles close-ups will be slow, so I'll measure them and report.
- **Disk:** about 15 GB free.
- **Image-to-3D, FLUX/SDXL plates (R1), the enhance pass (R3):** all wait for an 8 GB machine or a free cloud GPU, and each needs the owner's OK for downloads over 2 GB.
