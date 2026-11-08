# Route (b) notes: procedural v2 Kai

Script: `blender/bakeoff/route_b_procedural.py` (starts from a copy of `build_character.py`; Kai only, other cast branches removed).
Output: `assets/build/bakeoff/kai_b.blend`. Sheets: `docs/production/phase1/kai_b/`. Build takes about 6 s headless.

    "$(cat tools/blender_path.txt)" -b --factory-startup --python-exit-code 1 -P blender/bakeoff/route_b_procedural.py -- assets/build/bakeoff/kai_b.blend

**face_check: PASS** (0 failures, 58 cases, `kai_b/face_check.json`).

## What was built
Head and face
- Cube-sphere head at 120 cuts per cube edge (about 85k verts, 170k tris with the render subsurf). Sculpt fields were retuned: lower face compressed for a shorter chin, a firmer jaw angle and chin, brow ridge, sockets, nose bridge, tip and alae, and nasolabial folds.
- Real eye holes cut in the skin. The rim vertices are snapped onto the outer surface of the lid shells, so skin and lids meet without a seam.
- Lips: vermilion border ridges, cupid's bow, philtrum columns, upper-lip overhang, tucked corners. A curved lip-colour mask with a brighter border line. The mouth is 0.43 head units wide (the v1 mouth was 0.31).
- Ears are sculpted from a polar grid: helix rim, scapha groove, antihelix ridge, concha bowl, lobe, with thickness. They are tagged `head`. A silver hoop sits in the left lobe.
- Eye bags and the lower-lid groove are sculpted. The lid crease is a shading attribute plus the lid shell.

Eyes
- The eyeball is a 72x48 sphere with a recessed iris dish, which gives parallax.
- The iris material is procedural: radial fibres from noise on (cos a, sin a), pupil, collarette, limbal ring, and a sclera that gets pinker toward the corners.
- A cornea shell (bulged cap, tagged `eye`) uses transparent + Fresnel-weighted glossy, which gives the catchlight. It is not a true refractive/transmission shader (see defects).
- Lids have thickness, with a dark upper rim and a pink wet lower rim. Lids follow gaze: the upper lid goes +0.30 for look-down and -0.24 for look-up.
- Lashes are tapered geometry cards (30 upper, 10 lower per eye) parented to the lids, tagged `lash`.
- Blink: the upper lid overshoots the lower lid, so coverage is 100%.

Brows
- Each brow is a conformed ribbon (30x5 verts, floating 4-20 mm above the skin) plus 70 tapered hair strokes whose direction sweeps from rising at the inner end to out-and-down at the tail. Tagged `brow`.
- The brow carries its own shape keys (`browInnerUp`, `browOuterUp{L,R}`, `browDown{L,R}`). They use the same `brow_fields()` functions as the skin, so brow and skin move together.

ARKit
- All 52 properties on `FaceCtrl`, each driving a head shape key (or lid, eye, brow or jaw drivers).
- Changes from v1:
  - Stronger smile with a cheek lift. The cheek weight is faded near the eye hole.
  - Stronger frown.
  - `tongueOut` opens the jaw by 0.3 and moves the tongue forward and up.
  - `jawLeft`, `jawRight` and `jawForward` also move the lower teeth and tongue.
  - Upper teeth are narrower and sit deeper, to stay clear of the moving corners.

Body (standing A-pose, about 1.82 m with hair)
- Everything is built from ring sweeps and lofts, then skinned:
  - boxy black open-collar shirt (solidified, noise folds, V neckline cut, rolled collar, two lapel flaps, short sleeves);
  - dark trousers;
  - arms and legs;
  - sneakers (upper, sole, toe cap);
  - hands with 5 fingers (palm, 4 fingers with 3 joints, thumb), slightly curled and aligned to the forearm;
  - a 74-link thin silver chain.
- Armature: root, pelvis, spine, chest, neck, head, clavicle, upper_arm, forearm, hand (L/R), thigh, shin, foot (L/R). Every part is skinned rigidly to one bone through a vertex group at weight 1 and an Armature modifier.
- The neck mesh is weighted chest/neck/head by height.
- `Head` (the empty the pipeline keys) drives the `head` bone (100%) and the `neck` bone (35%) through drivers, so `Head.rotation_euler` nods the head mesh, neck and chain together.
- Auto-weights were NOT used. They are not needed for this rigid-part body.

Hair: about 650 chunky clay ringlets (helix curves, bevelled) over a displaced scalp cap, with a temple notch in the hairline and the fringe lifted above the brows.

## Contract
`CHAR_base` holds everything. `CHAR_root` is at the floor. The character faces -Y. `Head`, `FaceCtrl` (52 props), `FaceAnchor` (head_height = 0.286 m) and `EyeFocus` follow the head.
`face_part` tags: head (skin and ears), teeth, tongue, eye (eyeballs and corneas), lid, lash, brow. The armature is `hide_render`.

## Measurements
Triangles, evaluated at render level:

| part | tris |
| --- | --- |
| head skin | 169,996 |
| ears | 26,496 |
| lids | 39,296 |
| eyes + corneas | 14,784 |
| teeth + tongue + cavity | 10,568 |
| brow cards | 1,304 |
| lash cards | 640 |
| hair (curls + cap) | 631,248 |
| body + clothes | 51,032 |
| total | 945,364 |

- Face parts without hair: 263k tris (28% of the total).
- Face is about 85% of the non-hair tris. The brief's "60% on the head" is met for the character without hair, but hair dominates the budget.
- Eevee (Blender 5.2, 4 GB GPU, 85 mm, 720x900, 24 samples): about 1.5 to 2.5 s per face frame. The 17-pose sheet plus 2 close-ups took about 30 s, and the whole sheet with the turnaround about 40 s.
- Textures: no image textures at all. Everything is procedural (shader nodes) plus mesh vertex colours. One `CLOUDS` texture drives the hair-cap lumps.
- Objects: 68.

## Shared-file problem (not edited, per the rules)
`face_sheet.py` frames the turnaround from the bounding boxes of all visible meshes, and its own 40*S backdrop plane is one of them. The turnaround is a speck for every route (v1 included).
I did not edit it. A temporary wrapper (`route_b_sheet.py`) worked around it. **Update (lead):** `face_sheet.py` was fixed to measure the character before adding the backdrop and to hide the backdrop for the turnaround, so the wrapper was removed and `kai_b/` was re-rendered with the shared script.
The "back" turnaround is black because the backdrop plane sits behind the character. The reviewer should know this is a sheet artifact, not the model.

## Known defects (honest)
- Likeness to the references is only partial.
  - The face reads as a stylized adult male, but it is soft.
  - The jaw and chin are still not as sculpted as the references.
  - Cheekbone planes are subtle. The lower face is still slightly pointy from the front.
  - The nose is plain.
- Expressions read weakly at phone size.
  - Laugh, smug and angry are subtle.
  - Sad and surprised are the clearest.
  - The smile's corner and cheek motion is a blob displacement, not a muscle-style rig.
  - Visemes A, E and O are distinct but small. M seals visually, with no gap in `viseme_M`.
- Eyes
  - They are large and slightly bulgy, because the lids are spherical caps over the eyeball.
  - Closed lids look like round bumps.
  - The cornea is not truly refractive: transparent + Fresnel gloss, which gives a catchlight but no real refraction.
  - Lower lashes are crude spikes. Upper lashes are fine at distance but spiky at an extreme close-up.
  - A faint seam between the lid shell and the skin is visible in the ecu.
- Neck is long and tube-like. The deep V shows chest skin, which is the same tube.
- Hair is dense, a bit "poodle", and carries 67% of the tris. Curls are random helices, not authored per-curl shapes.
- Shirt looks like a sack. Sleeves are boxy. The folds are procedural sine noise.
- Hands are readable but simple, and rigid (no finger bones). Sneakers are blob shapes with no laces.
- Armature has no IK, finger or toe bones, and no facial bones. The body is rigid-skinned, so elbows and knees would show gaps or crease if bent a lot (balls cover the joints).
- Scalability to 7 characters x 3 outfits: the head sculpt still takes the dials from `cast.py` (the head, eye and lip dials still work). The body, outfit and hair code is Kai-only, so every outfit and hair style would need re-authoring. The cost per character is higher than for v1.

## What a reviewer should look at
`kai_b/face_sheet.png`, `ecu_eyes.png` (eye quality, lash cards, iris), `ecu_mouth.png`, `turnaround.png`, and `face_check.json`.
