# Route (c) notes: Rain v3 restyled into Kai

Output: `assets/build/bakeoff/kai_c.blend` (10 MB). Sheets: `docs/production/phase1/kai_c/`. face_check: **PASS** (58 cases).

Rebuild (about 55 s, headless, source opened with auto-run off and never modified):
```
"$(cat tools/blender_path.txt)" -b --disable-autoexec "tools/third_party/rain_v3/Rain v3.3/rain_v3.2.blend" --python-exit-code 1 -P blender/bakeoff/route_c_rain.py -- assets/build/bakeoff/kai_c.blend
```
Extra script: `blender/bakeoff/route_c_turnaround.py` (see "Shared-file issue").

## What was built
1. **Restyle field** (one smooth numpy field applied to every face part's base mesh and shape keys, so parts stay fitted): narrower cheeks, wider chin/jaw angle, chin forward, cheekbones and hollows, brow ridge shelf, longer lower face (+20%), broader nose with higher bridge, wider and thinner mouth, eyes shrunk to 88% (deep-set), thicker neck. Brows thickened/flattened separately. The bones are not moved, only the meshes (jaw pivot is a few mm off; baked recipes absorb it).
2. **ARKit bake (c1)**: 52 pose recipes on Rain's controls (`RECIPES`, bone-local metres/degrees). Each is evaluated at the identity pose and stored as a shape key delta on the evaluated, subsurf-off head, brows, lashes, upper/lower gums+teeth and tongue (6 parts, new objects with an Armature modifier, so head/neck motion still works). Keys are driven 1:1 from `FaceCtrl` (SUM drivers). Neutral expression has heavier lids and lower brows baked in.
3. **Long neck**: `FK-Head` is lifted 6 cm in the neutral pose; Rain's DEF-Neck stretch constraint lengthens the neck. Rig scaled 1.07 (character is 1.86 m with hair).
4. **Contract**: `CHAR_base` holds everything; `CHAR_root`, `Head` (Copy Rotation, world, "after" on `FK-Head`), `Body` (same on `FK-Spine`, for render_plan's lean/breath), `FaceCtrl` (52 props), `FaceAnchor` (`head_height` 0.327 m), `EyeFocus` (both bone-parented to `DEF-Head`); `face_part` tags on head, brow, lash, teeth x2, tongue, eye x2 (eyeball, cornea). Widgets/lights removed; lattice helper is `hide_render`.
5. **Look**: tan skin shader with lip and stubble masks from the lip-bone vertex groups; brown iris by re-tinting Rain's iris texture (packed, 2048 px); black brows/lashes; A-pose via FK arms (IK off; note `.R` bones need the opposite sign); hair = scalp cap plus coiled clay tubes (parented to the head bone); boxy open-collar shirt cut from a copy of the body mesh (inherits the weights; superellipse torso, loose sleeves, collar band, solidify); Rain's jeans inflated and narrowed at the hips; sneakers recoloured; silver hoop in the left ear (+X) and a thin silver chain. Rain's top, scarf, hair, hairband were removed.

## Collision pass (needed for face_check)
Rain's rig is not collision-free, and its teeth/lips and eyeballs/lids already overlap at neutral (baseline 419 / 51 / 409 triangle pairs). After the bake, `resolve()` pushes **skin** vertices off teeth, tongue and eyeballs (along the inner surface normal, or radially off the eye) until the count is under the neutral count, using the same BVH overlap test as face_check. It runs in the finished pose, then once more on the real driven objects (verification). Six corrective keys `fix_*` (value = product of the member shapes) cover face_check's pair cases. Cost: a few mm of lip/lid bulge in some mouth shapes.

## Deviations worth knowing
- **eyeLook\*** stays bone-driven (TGT-Eye bones from FaceCtrl drivers; Rain's sticky lids follow). Head shape keys exist for these only as collision fixes.
- **mouthClose is relative to the jaw**: its driver is `mouthClose * jawOpen` (it shows only with the jaw open). Standing alone it would push closed lips into the teeth.
- Recipes for funnel, pucker and dimple were weakened to avoid torn lips; they read subtly.

## Measurements
Tris, base / at render subdivision: Head 12.6k / 202k (level 2), brows 0.5k / 2.1k, lashes 0.5k / 1.9k, teeth 11.5k / 46k, tongue 0.5k / 2.1k, eyes 2.8k, corneas 1.3k / 2.6k, body 20.5k base (12k after Rain's clothing mask), shirt 4.4k / 36.8k, trousers 8.9k, shoes 12.4k, hair curls 12.7k + cap 2.5k, jewellery 0.9k. Total 92k base, 345k at render subdivision (dropping the head to level 1 would cut about 150k).
Eevee: about **2.2 s per 85 mm close-up frame** (720x900, 24 samples, 4 GB GPU, scene load excluded; 19 frames in 50 s). Textures: one 2048 px eye texture (packed); everything else is procedural. Rig: 2,166 bones, 519 original drivers plus about 300 new ones (heavy for 7 characters; a trimmed face rig would help).

## Known defects (honest)
- **Hair is the weakest part**: coils read as hexagonal chain links, not sculpted clay curls; hairline front is blunt. Needs a real curl generator or sculpt.
- Head is still too round and soft for the references: no sharp planes, weak jaw angle, pouty Rain lips and a babyish nose tip; stubble is a speckle shader.
- Smile/laugh shows a bulge under the chin and cheek; funnel/pucker are weak; viseme M seal is soft.
- Body is Rain's female base under a boxy shirt: narrow trousers still read slim-hipped; shoulders are only broadened by the shirt. Collar is a crude extruded band. Arms are in a plain A-pose, hands untouched.
- Rig pivots (jaw) are slightly off because meshes, not bones, were restyled.
- Eye whites keep Rain's noisy texture; brown iris is a re-tint.

## Shared-file issue
`blender/bakeoff/face_sheet.py` frames its turnaround on all visible meshes including its own 40 m backdrop plane, so its `turn_*.png` are tiny specks (same for v1). I did not edit it; `route_c_turnaround.py` renders the real turnaround into the same filenames.

## Verdict
Strong on face expressiveness, eyes (iris, catchlight, lids that close fully) and low authoring cost for 52 shapes; weak on likeness to the stylised references and on hair. Scaling to 7 characters needs a per-character restyle field plus recipe tuning, and the heavy rig is the main cost. Licence: CC-BY, credit already in `ASSETS_CREDITS.md`.
