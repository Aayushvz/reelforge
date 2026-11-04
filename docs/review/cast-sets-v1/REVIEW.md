# Cast and sets v1: review (2026-11-04)

Built on Aman's machine (RTX 3050 4 GB, Blender 5.2.3). All renders are Eevee drafts. Reviewer: Claude, automated pass; the owner is the final gate.

## What exists
| Area | Brief asks for | Built |
|---|---|---|
| Cast | 4 male + 3 female original characters | kai, rey, dev, mo, aria, zoe, noor (`blender/cast.py`) |
| Wardrobe | ≥3 outfits each, 25+ items | 3 outfits each (21 total), 27 distinct items (tops, outer layers, hats, prints, jewellery, glasses, watch) |
| Face rig | ARKit 52 through `FaceCtrl`; laugh/smug/surprised/sad/angry/blink/A-O-M | Shape keys + lid/eye/brow/jaw drivers; all ten expressions render (`expr_*.jpg`) |
| Sets | 10 sets × 3 lighting presets | All 30 build (`blender/sets.py`, `build_set.py`); moods tint each preset |
| Contract | `FaceAnchor`/`EyeFocus`; lights Key/Rim/Fill/Glow; Mark_A/B | Yes. Shot distance follows head height |
| Pipeline | choose cast/outfit/set/lighting per reel | `"model"`, `"outfit"`, `"environment"`, `"lighting"` in `performance.json`; 63 tests pass |

## Sheets
- `sheet_outfits.jpg`: columns kai, rey, dev, mo, aria, zoe, noor; rows are outfits 0–2.
- `expr_aria.jpg`, `expr_rey.jpg`: neutral, laugh, smug, surprised, sad / angry, blink, A, O, M.
- `sheet_side.jpg`: profiles. `face_lineup.jpg`: the seven faces side by side.
- `sheet_sets.jpg`: columns night_city, bedroom, rooftop, cafe, lantern_street, subway, classroom, office, night_mart, pier; rows are the three presets in `sets.py` order. Wide shot with kai.

## Honest verdict against `references/characters/style/`
**Look: PARTIAL.** It reads as a coherent "clean vinyl-toy" cast with distinct silhouettes, hair and wardrobe. Each character is recognisable at reel size. It is clearly below the references:
- Faces are soft. The references have crisp sculpted planes, heavy lids and defined lips; ours are smoother and a little doll-like, and smiles are modest. Each character now has a distinct head shape, nose width, brow ridge and socket depth (`face_lineup.jpg`), plus cheek and jaw plane breaks for a more sculpted read. They still read as one family.
- Hair is tube locks. Curls (kai, rey) come closest to the clay-curl reference; straight styles read as noodles up close.
- Bodies are blobs and tubes. Hands have a palm, four fingers and a thumb; forearms lift in talking beats, but fingers never pose. Full-body shots won't hold up.
- Clothes are shells and panels. A wrinkle bump (plus a rib texture on knits) breaks up the plastic look, but there are no real folds, seams or hems.

**Sets: PASS for mood, PARTIAL for detail.** Every set and preset reads as its place and time of day, with good depth-of-field bokeh. Floors, walls and desks now carry procedural wood, planks, tiles, brick, concrete and cobbles, but the geometry is still blocky (boxes, cards). Wide shots show it; close and medium shots hide it.

## Known gaps / next quality pass
1. Face: nostrils, philtrum and a lid crease are in, but subtle. Eyes are now almond-stretched (eye + lids share a scaled rig). Still needed: crisper planes, a bigger smile range.
2. Hands: fingers exist; a pose per set and gestures do not.
3. Clothing: real folds, seams and hems. Puffer quilting is geometric rings.
4. Sets: more props per set. Ambience is procedural noise beds (no real recordings); the per-set "LUT" is an ffmpeg colour-balance grade. Round-table sets (cafe, lantern_street) give Mark_B its own table.
5. Body rig: a hip pivot breathes and leans in while talking, and the forearms pivot at the elbow for talking-hand beats. There are no wrist/finger poses and no Rigify/auto-rig yet.
6. Two characters now render (one per mark). Close and medium shots cut to the speaker, wide shots frame both, and the listener turns head and eyes toward the speaker. There are no over-the-shoulder shots yet.

## End-to-end reels (draft: half resolution, 16 samples, placeholder Windows TTS voice)
- `samples/cafe-test`: Aria (outfit 1, blazer) in cafe / rainy_day, rain + murmur bed, cafe grade, −14.5 LUFS. 273 frames in ~14 min on the RTX 3050 (while other jobs shared the GPU).
- `samples/duo-test`: Kai + Rey (outfit 1) in bedroom / rgb_leds. Wide two-shot, speaker cuts, per-character caption colours, −14.2 LUFS. ~4 min.
- `samples/talk-<name>` (7): a talking clip per character, each in a different set/preset. Joined as `samples/cast-showcase/out/cast_showcase_9x16.mp4` (36 s).
- Re-run any of them with `reelforge run samples/<name> --stage full --draft` after putting real ElevenLabs takes in `out/audio/<line_id>.mp3`.
