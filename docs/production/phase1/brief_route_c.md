# Route (c): restyle Blender Studio's Rain v3 into Kai

Read `brief_common.md` first. Your script: **`blender/bakeoff/route_c_rain.py`**. Output: `assets/build/bakeoff/kai_c.blend`.

## Source (CC-BY; credit already in `ASSETS_CREDITS.md`)
`tools/third_party/rain_v3/Rain v3.3/rain_v3.2.blend` (+ `textures/`). Open it **only** with `--disable-autoexec`.
Never modify the source; your script opens it and saves a new file.

What's known (from inspection):
- It's about 103k tris. Meshes: `GEO-rain-head` (12.6k tris, 25 shape keys), `-body` (masked by the clothes), `-eyes`, `-eye_cornea`, `-eye_dots`, `-eyebrows`, `-eyelashes`, `-gums_upper/lower`, `-tongue`, `-hair_main/_ponytail/_strand`, `-hairband`, `-top`, `-jeans`, `-shoes`, `-scarf`. Most have an ARMATURE → LATTICE → (CORRECTIVE_SMOOTH) → SUBSURF stack.
- Armature `RIG-rain` (CloudRig, 2,166 bones). Its face is **bone-driven** (many controls use action constraints). Animator face controls (collection "Face Main"): `MSTR-Jaw`, `MSTR-Mouth`, `MSTR-UpperLip`, `MSTR-LowerLip`, `ACT-Lips_Corner.L/.R`, `ACT-Lip_Roll_Upper/_Lower`, `SK-Lip_Puff_Upper/_Lower`, `ACT-Cheek_Outer.L/.R`, `ACT-Cheek_Inner.L/.R`, `SK-Cheek_Puff.L/.R`, `ACT-Sneer.L/.R`, `CTR-Nose_Bottom`, `MSTR-Eyebrow.L/.R`, `ACT-Eyelid_Upper.L/.R`, `ACT-Eyelid_Lower.L/.R`, `ACT-Eyering_Upper/_Lower.L/.R`, `MSTR-Eyering_*`, `BB-Eye.L/.R`, `EyeDot.L/.R`. Eye aim: `TGT-Eyes`, `TGT-Eye.L/.R`. Tongue: `Tongue_Root`, `BB-Tongue1-3`. Properties bone `Properties_Face` (`sticky_eyelids`, `teeth_follow_mouth`, ...). Head is near z = 1.45 m, about 0.34 m tall.
- `cloudrig.py` is a UI script; rendering doesn't need it.

## What to build
1. **ARKit bake (approach c1, approved):** for each of the 52 ARKit names, write a pose recipe on Rain's face controls (bone loc/rot), evaluate, and capture the deformed result of each face mesh (head, brows, lashes, gums/teeth, tongue, lids if separate) as a **shape key**: delta between posed and rest evaluation, with SUBSURF temporarily off so vertex counts match. Then return the face controls to rest and drive each shape key from `FaceCtrl["<name>"]`.
   - `eyeLook*` can stay bone-driven: drive the eye-target bones from `FaceCtrl` with drivers.
   - Tune each recipe by eye on the face sheets. Use ARKit semantics: `jawOpen` drops the jaw; `mouthClose` closes the lips while the jaw is open; `mouthPress` presses the lips; `mouthFunnel` and `mouthPucker` round the lips; `eyeBlink` fully closes; `cheekSquint` lifts the cheeks; `browInnerUp` makes the worried brow; and so on.
2. **Restyle Rain into Kai (must not read as Rain):**
   - Adult male head proportions: a longer face, a stronger jaw and chin, cheekbone planes, a slightly smaller eye scale (Rain's eyes are childlike), thicker straighter brows, and a slightly broader nose. Use a lattice or a sculpt-field "restyle" shape key, applied before the ARKit bake so the bake uses the new shape.
   - Male body: broader shoulders, a flatter chest, a thicker neck. Keep the long-neck caricature from the references.
   - Skin: warm tan (see `cast.py`), with a light stubble mask (shader or shell) on the jaw, chin and upper lip.
   - Hair: remove Rain's hair objects. Build Kai's tight black clay curls on the scalp (study the curl generator in `blender/build_character.py` for the look, but write your own in your script). No clipping.
   - Outfit 0: a boxy black open-collar shirt (the top can be restyled), black/dark trousers (restyle the jeans), sneakers; remove the scarf. Add a thin silver chain and a silver hoop in the left ear.
3. **Contract:** add `CHAR_root` (parent of the rig), `Head` (its rotation drives the head/neck control: a constraint or drivers), `FaceAnchor` and `EyeFocus` (bone-parented to the head deform bone), `head_height`, `face_part` tags, all in `CHAR_base`.
4. Measure and record: tris per part, and Eevee seconds per 85 mm close-up frame.

Expected difficulty: the bake recipes need many render-and-look iterations. Prioritize, in order: jawOpen, blink, smile, frown, browInnerUp/Down/OuterUp, press/roll/funnel/pucker, squints, then the rest.
