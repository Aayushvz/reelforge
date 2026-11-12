# Shots-AV progress ledger

The source of truth for resuming `docs/prompts/03-shots-av-animation.md`. Branch: `feat/shots-av`, cut from `feat/cinema-real` (a58c4ce), because the look system, `camera_rig.py` and director v2 that this style builds on only exist there.
Machine: RTX 4060 Laptop (8 GB), Blender 4.5.15. Evidence: `docs/production/shots-av/p1/`.

Update this file after every task. A new session reads it and `git log`, and never redoes a row marked done.

## Status
| Phase | Task | Status | Commit | Evidence / notes |
|---|---|---|---|---|
| 0 | Working tree clean before branching | done | — | The cinema edits the prompt mentions were already committed on `feat/cinema-real` (a58c4ce), so there was nothing to commit or stash |
| 0 | Ledger and rubric | done | P1 commit | `PROGRESS.md`, `RUBRIC.md` (ten rows from section 6, scored 0 to 10; ship rule 8 of 10). **Rubric awaits owner approval** |
| 0 | Engine stub `reelforge/engines/shots_av.py` (`shots-av`, "Shots-AV Animation") | done | P1 commit | Registered; `build_assets()` builds the hero; `render()` refuses with a clear message until P2-P4 exist |
| 0 | Look stub `blender/looks/shotsav.py` | done | P1 commit | Eevee, rig cameras, raytraced AO/contact shadows, Khronos PBR Neutral at -0.75 (see Decisions); `look_params` dials read and stored, wired in P3 |
| 0 | Schema fields (section 5.4) | done | P1 commit | `style: "shots-av"` defaults: `look` shotsav, `environment` av_studio_night; exactly one `av_hero` and one `buddy_*`; hero `outfit`/`outfit_color` (any hex, default `#7C3AED`)/`glasses`/`headphones`; line `beat` and `action`; `camera.grammar` and `camera.seed`. Chat-style lines (speaker and text only) get defaults. Other styles unchanged |
| 0 | Tests | done | P1 commit | `tests/test_shots_av.py` (19 tests); full suite 129 pass |
| 1 | Hero geometry, face, rig (`blender/shotsav/hero.py`, `geo.py`, `build_shotsav.py`) | done | P1 commit | See "P1 hero" below |
| 1 | Evidence sheets (`blender/shotsav/sheets.py`) | done | P1 commit | `turnaround.jpg`, `expressions.jpg`, `mouth_shapes.jpg`, `purple_check.jpg` + `.json`, `outfits_poses.jpg`, `options_skin_hair.jpg` |
| 1 | **Gate P1: owner picks skin tone and hair preset** | **waiting on owner** | — | Glasses already decided (round) |
| 2-8 | Buddies, rooms, camera and director, captions and sound, editor page, benchmark, docs | not started | — | Out of scope for this session |

## Decisions
| Date | Decision | Why |
|---|---|---|
| 2026-11-12 | Glasses: **round** is the default (owner answered "Yes, glasses" to "Should the hero wear round glasses like the reference?") | Owner decision, relayed by the session that started this one |
| 2026-11-12 | The `shotsav` look uses **Khronos PBR Neutral at exposure -0.75**, not AgX Medium High Contrast (prompt 4.4) | Measured under the 4300 K key: AgX renders a lit matte `#7C3AED` card at ΔE 49-75 (pastel lilac) at every exposure from -1.5 to 0, and Punchy is no better. PBR Neutral at -0.75 keeps the jacket's lit side at ΔE 3-5 and its shadow side at 3-5 under all three keys (table below). P5's grade adds contrast back with a purple-protected curve |
| 2026-11-12 | Jacket sheen 0.06 (was 0.35), hair sheen 0.04 | Sheen added a white grazing layer that washed purple to lilac and made black hair read grey |
| 2026-11-12 | Brows sit at 0.040 above the head's midline, above the glasses rim | At 0.019 they hid behind the rim, and the brows carry most of the acting |
| 2026-11-12 | The mouth interior is a dish that follows the face 11-21 mm behind the skin | A cavity sphere poked out through the chin, which curves back faster than any sphere |
| 2026-11-12 | The preview desk in the sheets is a plain stand-in | The real desk and chair belong to the P3 rooms; the side view shows the hero seated on nothing |

## P1 hero (what was built)
- **Proportions:** head 0.34 tall by 0.36 wide (lower half 5% wider, squarer chin), eyes at 1.18 m seated, desk top at 0.74, shoulders 0.46 wide over the sleeves, short thick arms, hands about 0.10.
- **Face:** black oval eyes (0.024 by 0.040, 0.115 apart) with one fixed highlight; upper and lower lids (blink, half-lid, squint, wide, cheek push); brows that raise, lower, angle and pinch; a small wedge nose; ears; per-vertex blush on cheeks, ears and nose tip; a stubble band (dial 0 to 1, default 0.3).
- **Mouth:** a real slit with an inner lip wall, dark warm interior, upper teeth and a tongue that drops with the jaw. Shape keys: rest, MBP, small, wide, O, E, FV, smile, plus corner up and down on each side and a sideways shift. All are driven from the 52 ARKit channels on `FaceCtrl` (the `MOUTH_DRIVERS` table), so the existing viseme and emotion tracks drive it unchanged.
- **Hair:** `swept` (12 faceted clumps over a thin cap, fringe lifted off the forehead, side part), `curly_top` (18 faceted curls), `buzz` (cap only).
- **Wardrobe:** `puffer` (4 quilted bands with seams as geometry, soft-purple zip bands, stand collar, banded sleeves with cuffs), `hoodie` (hood down, neck band, drawcords with lilac tips, kangaroo pocket), `overshirt` (collar points, lilac buttons, chest pocket, cream tee). Any `outfit_color`; brand purple uses the brand's own mid, soft and lilac tokens. Optional lilac slash-and-dot chest mark.
- **Accessories:** glasses `round`/`rect`/`none` (thin metal rim, a Fresnel lens glint that never covers the eyes); headphones `neck`/`on`/`none`.
- **Hands:** four two-segment fingers and a two-segment thumb, poses `rest`, `fist_cheek`, `point`, `open`, `type`, solved by two-bone IK at build time and stored as drivers.
- **Rig contract:** `CHAR_root` → `Body` (hip pivot) → `Spine` (driven by `Lean`) → torso, arms, `Head` → `HeadGeo` → face. Also `ElbowL`/`ElbowR` (render_plan's talking-hand lift, scaled by each pose's gain), `FaceCtrl` (52 ARKit props), `FaceAnchor` (head_height 0.34), `EyeFocus`, and `PoseCtrl` with `HandL`/`HandR` (pose index; fractions blend) and `Lean` (-1 to 1).
- **Rig check (measured):** contract complete; eye height 1.18 m; each pose's wrist lands within 5 mm of its target; `Lean` = 1 moves the head 8 cm; `jawOpen` 0.55 gives small 0.5 + wide 0.5; press 0.7 gives MBP 1.0; `ElbowR` -0.4 rad lifts the wrist 6.6 cm. 112 objects, about 59k triangles after one subdivision on the head.
- **Built files:** `assets/build/shotsav/av_hero__{puffer,hoodie,overshirt}.blend` (git-ignored; rebuild with `reelforge build-assets --style shots-av`).

## P1 purple check (neutral-warm 4300 K key; matte card of pure `#7C3AED` beside the jacket)
| Key | Card (faces the key) | Jacket, lit side | Jacket, shadow side |
|---|---|---|---|
| neutral warm 4300K | `#A05EF4` ΔE 19.2 | `#8636E8` ΔE 3.6 | `#772AE1` ΔE 4.5 |
| screen cool 7500K | `#8C6AF9` ΔE 25.0 | `#7545F3` ΔE 4.8 | `#6A37EF` ΔE 5.3 |
| daylight 5600K | `#9969F8` ΔE 24.4 | `#8243F2` ΔE 3.2 | `#7535ED` ΔE 3.0 |

ΔE is CIE76 against `#7C3AED`, measured on a 15 px patch (white ticks in `purple_check.jpg`; the top-right chip is the exact sRGB value). **The jacket passes** (lit side ΔE 3-5 under all three keys, against the P1 target of 10). **The card misses its target of 6** (ΔE 19-25): it faces the key head-on and catches about half a stop more light than the jacket, so it renders lighter. That's an exposure question for each room (P3), not a hue shift: every patch stays within 8° of the target hue (262°). Before this pass, AgX gave the same jacket ΔE 61.

## P1 review against `references/style/shots-av/01_five_setups.jpg` (honest)
Compared side by side with panels A (hero close-up) and C/E (wides) of the reference. Provisional rubric scores for the hero rows (the reference in brackets):

| Row | Ours | Ref | Notes |
|---|---|---|---|
| 1 Face shading | 7 | 4 | Smooth skin, blush, bevelled hands and seams, no triangles on the face. Lost points: the forehead under the fringe shows a grainy orange patch (Eevee raytraced shadow noise at 48 samples, worst under the fringe); the closed lids read as skin discs with a visible rim |
| 2 Expression | 7 | 3 | Brows carry the emotions: sad, worried, annoyed, confused and surprised are distinct at sheet size. Lost points: at head-shot distance the mouth shapes are small, so happy vs. smug and neutral vs. deadpan differ mostly in the brows; embarrassed reads as neutral |
| 3 Hands | 5 | 2 | Real fingers in five poses, and rest/type/fist-on-cheek read well. Lost points: hands are small for the big head (about 0.10 m against a 0.34 m head); point and open palm don't read at desk-shot distance (the pointing finger is lost, open palms are tiny); the fist-on-cheek elbow floats instead of resting on the desk |

What falls short of `01_five_setups.jpg`, plainly:
- **Head-to-body read.** The reference's head looks bigger against a narrower, rounder torso, and its jacket hugs the shoulders. Ours has a broader torso (0.46 m shoulders, as the prompt asks, to read male), which makes the head look slightly smaller in the wides. Worth a second look once the camera set-ups exist (P4); a 5-8% larger head is a one-line change (`RX`, `RY`, `RZT`, `RZB`).
- **Hair.** The swept clumps read as short male hair, but the back clumps flare into a crest in the side view, and the cap shows a faceted line at the nape. The reference's hair is softer and longer (it's a different character, so not a copy target).
- **Light.** The reference's warm orange key and glowing jacket aren't reproduced here on purpose (purple goes brown under orange, prompt 4.3). Under our neutral-warm key the image is darker and lower in contrast than the reference until the P5 grade.
- **Sitting.** No chair or legs worth showing; the side view reveals the hero floating at seat height. That's P3's chair.
- **Glasses.** The thin rims read in every view and the lens no longer hides the eyes. The rims also cast faint ring shadows on the cheeks, which reads as natural.
- **Not yet testable:** lip sync in motion, blink timing, how the pose change looks across a cut. Those need the director and animatic (P4).

## How to rebuild the evidence
```bash
B="$(cat tools/blender_path.txt)"
"$B" -b --factory-startup --python-exit-code 1 -P blender/shotsav/sheets.py -- docs/production/shots-av/p1            # all sheets
"$B" -b --factory-startup --python-exit-code 1 -P blender/shotsav/sheets.py -- docs/production/shots-av/p1 purple     # one sheet
"$B" -b --factory-startup --python-exit-code 1 -P blender/shotsav/sheets.py -- docs/production/shots-av/p1 one name=x view=34 shot=head hair=buzz jawOpen=0.5
```
