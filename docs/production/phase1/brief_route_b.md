# Route (b): procedural v2 Kai (hand-built by script)

Read `brief_common.md` first. Your script: **`blender/bakeoff/route_b_procedural.py`** (no source file; it builds from
scratch). Output: `assets/build/bakeoff/kai_b.blend`.

Start by copying `blender/build_character.py` into your script (don't edit the original). It already has a
sculpt-by-script head with a real mouth slit, teeth, tongue, cavity, eyeball + lid caps, brows, ARKit shape keys
driven from FaceCtrl, curls, and a v1 bust-only body. Its weaknesses are what you're fixing, face first.

## What to build
1. **Head and face (60% of your effort):**
   - Raise the face density around the eyes, mouth and nasolabial area. Keep the cube-sphere, or move to a better head base built in your script.
   - Sculpted planes: brow ridge, cheekbones, jaw angle, chin; a nose with bridge, tip, alae and nostrils; ears with helix, antihelix and lobe (not an ellipsoid).
   - Lips: a vermilion border with a lip-colour mask, a philtrum, a slight upper-lip overhang, corners; an M seal with no gap.
   - Eye bags and a lid crease.
2. **Eyes (15% of the score):**
   - Separate sclera, an iris with radial fibres (procedural is fine) and depth or parallax, a pupil, and a **cornea** shell (transmissive/refractive, glossy) for catchlights.
   - A wet-line; lids with real thickness that conform to the eyeball; **lash cards**.
   - Gaze moves the eyeballs, and the lids follow gaze slightly.
3. **Brows:** cards or strips with hair direction (not tubes). Brow shapes drive emotion: inner-up, down, outer-up per side.
4. **ARKit shapes:** keep all 52 and improve them, especially smile (cheek lift, nasolabial deepening), frown, funnel/pucker, press/roll (an M seal), and squint (lower lid up, cheek up). No intersections (face_check).
5. **Body:** a real stylized base body. Legs, feet in sneakers, torso with chest and shoulders, a long neck, arms in a relaxed A-pose, hands with 5 fingers. Add a simple armature (root, spine, neck, head, shoulders, arms, forearms, hands, thighs, shins, feet), skin with automatic weights where it works headless, otherwise rigid parenting per part. `Head` must nod the head and neck.
6. **Kai's look:** tight black clay curls (improve on v1), light stubble, a boxy black open-collar shirt with thickness and a few sculpted folds, dark trousers, sneakers, a thin silver chain, and a silver hoop in the left ear.
7. Measure and record: tris per part (aim for about 60% on the head), and Eevee seconds per 85 mm close-up frame.

Expected difficulty: the face is where this route wins or loses. Iterate on the face sheet many times; the body only needs to be clean and believable.
