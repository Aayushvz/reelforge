# Phase 1 bake-off review: Kai, route (b) vs route (c)

Boards (rows: v1 baseline, route b, route c): `boards/board_faces.png` (neutral, laugh, smug, surprised, sad,
angry, viseme M, blink), `boards/board_ecu.png` (eyes, mouth), `boards/board_turn.png`, and `boards/board_refs.png`
(the style references). Per-route sheets and the face_check JSON are in `kai_b/` and `kai_c/`. Builder notes:
`route_b_notes.md`, `route_c_notes.md`. All renders use the same portrait rig and cameras (`face_sheet.py`).

## Automated gates
| | face_check (58 cases) | Tris (render) | Eevee s / 85 mm close-up | Build time |
|---|---|---|---|---|
| v1 | FAIL (tongueOut, gaze-down poke-through) | ~150k | ~1.5 | ~10 s |
| (b) procedural v2 | **PASS** | 945k (hair 631k) | ~2 | ~6 s |
| (c) Rain restyle | **PASS** (uses a collision pass + 6 corrective keys) | 345k (92k base) | ~2.2 | ~55 s |

## Scores, lead reviewer (Opus), 0–10
| Criterion (weight) | (b) | (c) | Why |
|---|---|---|---|
| Face likeness to the refs (40%) | 4.5 | **6.0** | (c) has real facial topology: a nose with bridge and tip, defined lips, a modelled ear. But the features read young and soft (Rain's lips and nose tip), and the jaw is weak. (b) is a doll: bulging eyes, a tube neck, a pointy lower face. Neither reaches the refs' hard sculpted planes. |
| Expressiveness (25%) | 5.0 | **8.0** | (c)'s laugh lifts the cheeks and narrows the eyes; surprised, sad and angry read at a glance. (b) reads for surprised and sad only. |
| Eye quality (15%) | 6.0 | **7.5** | (b) has more iris and lash detail, but the eyes bulge and the lower-lid rims look pink and sore. (c)'s eyes are clean and appealing, with clear catchlights, but are stylized-Disney rather than the refs' heavier lids. |
| Rig, lip-sync, scalability, cost, licence (20%) | 5.0 | **6.0** | (c) is a production rig (fingers, IK, correctives), but heavy: 2,166 bones and ~800 drivers, one female base body for all 7 characters. (b) scales by dials, but its ceiling is low and its hair is 8× over budget. Licences: (b) has none to worry about; (c) is CC-BY, credited. |
| **Weighted total** | **4.95** | **6.73** | |

## Defects that must be fixed whichever route wins
- **Hair (both):** (c)'s coils read as hexagonal chain links; (b)'s are a dense poodle mass at 631k tris. The refs need sculpted clay curl *clumps* (fewer, bigger, readable shapes).
- **Stubble (c):** a speckle shader that reads as dirt at 85 mm. Needs shell or card stubble, finer and softer.
- **Body (c):** Rain's female body under a boxy shirt with a torn-looking hem; slim hips. (b)'s body is cleaner but stiff and ball-jointed.
- **Mouth (both):** the M seal and funnel/pucker are weak. (c) shows a bulge under the chin on smile and laugh.
- **Likeness gap (both):** neither reaches the refs' adult caricature planes (heavy brow, cheekbone and jaw planes, long neck with strong jaw).

## Recommendation (for the owner)
**Route (c), as a hybrid:** keep Rain's head topology, face rig and eyes as the face base, because that is where the score difference comes from. Fix the gaps it can't solve on its own:
1. A per-character **head restyle pass** with much stronger adult caricature shapes (jaw, cheekbone and brow planes, nose and lips), so 7 characters don't read as one family.
2. A **new sculpted clay-curl hair system** with readable clumps (shared by both routes' learnings).
3. Replace the female base body with a **male base body** (masculinised Rain body, or route (b)'s body as a starting point) and real cloth.
4. Trim the rig cost: bake the face to shape keys (already done), and disable unneeded face bones for render.

**Still open:** route (a) image-to-3D (needs an 8 GB GPU) may beat both on likeness. It should get the same sheets before Phase 2 commits fully.

Independent review: see the section below once it runs.
