# Shots-AV progress ledger

The source of truth for resuming `docs/prompts/03-shots-av-animation.md`. Branch: `feat/shots-av`, cut from `feat/cinema-real` (a58c4ce), because the look system, `camera_rig.py` and director v2 that this style builds on only exist there.
Machine: RTX 4060 Laptop (8 GB), Blender 4.5.15. Evidence: `docs/production/shots-av/p1/`.

Update this file after every task. A new session reads it and `git log`, and never redoes a row marked done.

## Status
| Phase | Task | Status | Commit | Evidence / notes |
|---|---|---|---|---|
| 0 | Working tree clean before branching | done | — | The cinema edits the prompt mentions were already committed on `feat/cinema-real` (a58c4ce), so there was nothing to commit or stash |
| 0 | Ledger and rubric | done | 222f99c | `PROGRESS.md`, `RUBRIC.md` (ten rows from section 6, scored 0 to 10; ship rule 8 of 10). **Rubric approved by the owner, 2026-11-12** |
| 0 | Engine stub `reelforge/engines/shots_av.py` (`shots-av`, "Shots-AV Animation") | done | 222f99c | Registered; `build_assets()` builds the hero; `render()` refuses with a clear message until P2-P4 exist |
| 0 | Look stub `blender/looks/shotsav.py` | done | 222f99c | Eevee, rig cameras, raytraced AO/contact shadows, Khronos PBR Neutral at -0.75 (see Decisions); `look_params` dials read and stored, wired in P3 |
| 0 | Schema fields (section 5.4) | done | 222f99c | `style: "shots-av"` defaults: `look` shotsav, `environment` av_studio_night; exactly one `av_hero` and one `buddy_*`; hero `outfit`/`outfit_color` (any hex, default `#7C3AED`)/`glasses`/`headphones`; line `beat` and `action`; `camera.grammar` and `camera.seed`. Chat-style lines (speaker and text only) get defaults. Other styles unchanged |
| 0 | Tests | done | 222f99c | `tests/test_shots_av.py`; full suite 152 pass after the gate change |
| 1 | Hero geometry, face, rig (`blender/shotsav/hero.py`, `geo.py`, `build_shotsav.py`) | done | 222f99c | See "P1 hero" below |
| 1 | Evidence sheets (`blender/shotsav/sheets.py`) | done | 222f99c | `turnaround.jpg`, `expressions.jpg`, `mouth_shapes.jpg`, `purple_check.jpg` + `.json`, `outfits_poses.jpg`, `options_skin_hair.jpg` |
| 1 | Gate P1: skin, hair, glasses | **passed** | 0c77508 | Glasses: round default. Skin and hair: **all kept as viewer choices** (see Decisions). Rubric approved |
| 1 | Skin, hair and stubble as per-project choices | done | 0c77508 | `skin` (6 tones), `hair` (3 presets), `stubble` (0-1) on the hero in `performance.json`; `shots_av.ensure_hero(options)` builds the picked combination on demand into `assets/build/shotsav/av_hero__<outfit>__<skin>__<hair>__<glasses>__<headphones>__<colour>__<stubble>.blend` and reuses it after (one build checked: hoodie, deep, curly_top) |
| 2 | Clip library `reelforge/buddy.py` (8 clips, pick rules, WAV envelope, talk squash, `animate()`) | done | P2 commit | `tests/test_buddy.py` (16 tests) |
| 2 | Four buddies `blender/shotsav/buddies.py` + shared rig; engine builds them | done | P2 commit | `assets/build/shotsav/buddy_<id>.blend`; table tests in `test_shots_av.py` |
| 2 | Evidence (`blender/shotsav/buddy_sheets.py`) | done | P2 commit | `p2/lineup.jpg`, `p2/clips_claude.jpg`, `p2/eyes_signature.jpg`, `p2/loop_<id>.mp4` (6 s each), `p2/loops_grid.mp4` |
| 1 | Likeness pass (owner's photos): hair, bold glasses, wheat skin, beard, oval-squarish face, directional key | done | 319b54e | `p1/likeness.jpg` (front, three-quarter, side) and every P1 sheet re-rendered |
| 2 | Robot redesign of the four buddies (display faces, waveform mouths) | done | 319b54e | `p2/lineup.jpg`, `p2/clips_claude.jpg`, `p2/eyes_signature.jpg`, `p2/loop_*.mp4`, `p2/loops_grid.mp4` re-rendered |
| 1 | Innocence pass + two soft hair designs | done | da4dd8b | `p1/hair_options.jpg`, `p1/expressions.jpg`. Hair: all six kept as editor options, default `fringe` (owner, 2026-11-12) |
| 2 | Gate P2: brand literalness | **passed** | 1fd68c9 | Recognisable as their products at the current robots' level; no traced logos (owner, 2026-11-12) |
| 3 | Six rooms (`blender/shotsav/rooms.py`), room builds, schema `AV_ROOMS`, engine `room_blend()`, tests | done | 116b164 | `p3/rooms.jpg` (a wide and a hero close-up per room, hero and the Claude robot in place), `p3/rooms.json` |
| 3 | Gate P3: the 12 room stills | **passed** | — | Owner approved, 2026-11-13 |
| 4 | Five set-ups in `camera_rig.FRAMING` + `pull_truck` | done | P4 commit | sign conversion recorded in the table's comment; `tests/test_director_av.py` checks it |
| 4 | `plan_shots_av` (reference + signature grammars), rack focus | done | P4 commit | 20-line fixture: 20 shots, same kinds in order, cuts within 2 frames, split 46/37/17 within 3 points |
| 4 | Engine render + acting (hero blink on cuts, think-to-rest pose change, buddy BuddyCtrl from loudness and `pick_action`), `reelforge animatic` | done | P4 commit | `samples/shots-av-fixture` |
| 4 | **Match pass** | **done, all within tolerance** | P4 commit | `p4/match_pass.jpg` (reference top, ours below), `p4/match_measure.json`; table below |
| 4 | Silent animatic (draft) | rendering | — | `samples/shots-av-fixture/out/animatic.mp4` |
| 4 | Connected move (arc from `av_hero_34` to `av_buddy`) | deferred | — | see Decisions |
| 5-8 | Captions and sound, editor page, benchmark, docs | not started | — | |

## P2 spec (buddies)
1. `blender/shotsav/buddies.py`: table `BUDDIES` (claude, chatgpt, figma, nova), built by `build_shotsav.py -- <out> buddy <id>`.
2. Shared size: body 0.13-0.15 m tall (about 0.4 of the hero's head), two black rectangle eyes 0.022 by 0.008, no mouth, 2-4 stub feet, a soft contact shadow that shrinks on a hop.
3. Shared rig: `CHAR_root` -> `Body` (render_plan's lean and breath) -> `Squash` (drivers) -> `Head` (render_plan's nod and listen-turn) -> geometry; `FaceAnchor` (head_height = body height), `EyeFocus`, `FaceCtrl` (52 ARKit props, so the existing blink and lip tracks drive it too).
4. `BuddyCtrl` props: `squash`, `lean_x`, `lean_y`, `hop`, `eye_h` (1 neutral, 0.35 dry, 0 closed), `eye_shape` (0 rect, 1 happy arcs, 2 sad tilt, 3 wide, 4 wink), `eye_look_x/y`, `glow`, `sig` (signature motion amount) and `phase` (its running angle).
5. Signature motion: claude's 8 lobes ripple outward; chatgpt's six petals turn a few degrees; figma's blocks spread and snap back into the grid; nova's ring spins faster. Each reads `sig` and `phase`.
6. Brand rule: colour and silhouette say the product, but nothing traces a logo. Claude is a puffy 8-lobe blob, ChatGPT a woven ring of six capsule petals, Figma a stack of five toy blocks, Nova a gem with a ring.
7. `reelforge/buddy.py` (stdlib): the 8 reaction clips (hop, tilt, dry, happy, think, shrink, nod, lookaway; 10-18 frames each), `pick_action()` (! -> hop, trailing ... -> think, intensity under 0.3 -> dry, else by emotion), the loudness envelope from a WAV, the talk squash (3-6%, 2-frame attack, 5-frame release), and `animate()` (idle breath, seeded blinks every 2.8-4.2 s, a glance at the hero, a lean toward the hero while talking).
8. Evidence: a line-up still with the hero for scale; a clip sheet (8 clips at their peak); an eye and signature sheet (5 eye shapes and the signature pose for each buddy); a 6 s loop of each buddy talking and reacting, plus a 2x2 grid of the four loops.
9. Tests: clip lengths and ranges, the pick rules, envelope attack and release, determinism, blink spacing.
10. Gate P2: **the owner decides how literal the brand shapes may be** (and whether real logos may appear, for example on the monitor).

## P3 measurements (`p3/rooms.json`; jacket ΔE is CIE76 against `#7C3AED`; desk-front luminance is display-referred)
| Room | Tone | Jacket, wide | Jacket, close-up | Desk front luminance (wide) |
|---|---|---|---|---|
| `av_studio_night` | dark | `#833DD0` ΔE 16.5 | `#8030D5` ΔE 9.6 | 7.7% |
| `av_neon_den` | dark | `#7545E8` ΔE 8.7 | `#743CEE` ΔE 2.2 | 9.4% |
| `av_late_office` | dark | `#8C49DE` ΔE 16.3 | `#893CE1` ΔE 8.2 | 8.8% |
| `av_studio_morning` | light | `#6F32D8` ΔE 7.4 | `#7135DB` ΔE 6.9 | 80.6% |
| `av_cafe_day` | light | `#793DD1` ΔE 15.8 | `#7D40DA` ΔE 12.5 | 85.7% |
| `av_cyc_lilac` | light | `#7A3AEA` ΔE 1.6 | `#7838E7` ΔE 2.2 | 93.1% |

Honest notes:
- **Purple holds best in the cyc (ΔE 2), the den and the morning studio (2-9).** The night studio and late office wides read 16 because the wide's sample point lands on the jacket's half-lit side; their close-ups are 8-10. The cafe runs 12-16: the hue is right but its warm bounce light desaturates the purple slightly. P5's purple-protecting grade (prompt section 7) is the planned fix; a per-room key tweak could also close it.
- **Desk front never crushes:** 7.7-9.4% in the dark rooms (target 8-12%), bright in the light rooms.
- **Framing is a first pass of `av_wide_34` and `av_hero_34`.** P4 owns the measured match pass against `01_five_setups.jpg`. The wide currently looks down on the desk a little more than the reference.
- **Bokeh is real depth of field** from emissive discs 30-120 m away (night city, office window band, cafe street, morning sky). The reference's square bokeh is not copied; ours is round.
- **Not built yet** (listed in the prompt, belong to P4/P5): an animated monitor (bubbles appearing per line), screen flicker on the chest, background life (aircraft light, headlight sweep, swaying leaves). The lamp sits just out of frame for the closing pull-out but nothing animates it in yet.

## P3 spec (rooms)
1. `blender/shotsav/rooms.py`: table `ROOMS` (av_studio_night, av_neon_den, av_late_office dark; av_studio_morning, av_cafe_day, av_cyc_lilac light), built by `build_shotsav.py -- <out> room <id>` into `assets/build/shotsav/<id>.blend`.
2. Same contract as `blender/sets.py`: lights `Key`, `Rim`, `Fill`, `Glow` with `base_color`/`base_energy`; `ScreenMat` with a "Code" node; `Mark_A` (the hero's chair, origin) and `Mark_B` (on the desk, to the hero's right and toward the viewer: (-0.30, -0.36, 0.74), as in P2).
3. Shared desk stage: desk 1.6 by 0.75 at 0.74 (bevelled, with legs), a chair behind the hero, monitor on the hero's left turned 25 degrees so its chat screen shows at screen-right in the wides, keyboard, pen, two sticky notes, a mug, and a desk lamp kept just out of frame for the closing pull-out.
4. Chat screen: the `ScreenMat` "Code" brick node draws staggered rounded bars (left and right), so the monitor reads as a chat; moods recolour it.
5. Depth: the background sits 2.2 m behind the hero; far lights are real emissive discs 30-120 m away, so bokeh comes from the camera's depth of field, not a painted plate. Thin haze per room.
6. Light: neutral-warm key (never the reference's orange), warmth in the background; violet or cool rims; each room stores its exposure (`av_exposure`) for the `shotsav` look.
7. Desk front never crushes: a low bounce keeps it at 8-12% luminance.
8. Evidence: per room one wide (about 50 mm, 15 degrees off axis, 8 degrees above the eyes) and one hero close-up (85 mm, 30 degrees round, 4 degrees above), hero and the Claude robot in place; measured jacket purple and desk-front luminance per room.
9. Tests: room table matches the schema's environments, every room has the contract.
10. Gate P3: the owner reviews the 12 stills.

## P4 match pass (`av_studio_night`, `samples/shots-av-fixture`, reference grammar)
| Set-up | Measure | Reference | Ours | Delta | Tolerance | Pass |
|---|---|---|---|---|---|---|
| A av_hero_34 | height (H) | 0.46 | 0.439 | -0.021 | 0.03 | yes |
| A av_hero_34 | eyes (H) | 0.52 | 0.537 | +0.017 | 0.03 | yes |
| A av_hero_34 | top (H) | 0.23 | 0.239 | +0.009 | 0.03 | yes |
| B av_buddy | height (H) | 0.38 | 0.373 | -0.007 | 0.03 | yes |
| B av_buddy | eyes (H) | 0.62 | 0.631 | +0.011 | 0.03 | yes |
| B av_buddy | centre x (W) | 0.50 | 0.488 | -0.012 | 0.05 | yes |
| C av_wide_34 | height (H) | 0.25 | 0.248 | -0.002 | 0.03 | yes |
| C av_wide_34 | eyes (H) | 0.36 | 0.361 | +0.001 | 0.03 | yes |
| D av_hero_front | height (H) | 0.46 | 0.432 | -0.028 | 0.03 | yes |
| D av_hero_front | eyes (H) | 0.54 | 0.545 | +0.005 | 0.03 | yes |
| E av_wide_front | height (H) | 0.25 | 0.244 | -0.006 | 0.03 | yes |
| E av_wide_front | eyes (H) | 0.35 | 0.350 | +0.000 | 0.03 | yes |
| E av_wide_front | top (H) | 0.22 | 0.193 | -0.027 | 0.03 | yes |
| E av_wide_front | width (W) | 0.40 | 0.353 | -0.047 | 0.05 | yes |
| C av_wide_34 | buddy centre (W) | 0.10-0.30 | 0.222 | - | inside | yes |

Honest notes: every value is inside tolerance, but three sit near the edge: D's head height (-0.028), E's hair top (-0.027) and E's head width (-0.047, our oval face is narrower than the reference's long-haired head). The buddy's eyes match (0.63 vs 0.62) while its body sits higher in frame than the reference's (centre 0.61 vs 0.69), because our robot carries its eyes lower on a taller body with an antenna. Bokeh is round-heptagonal (7 blades), not the reference's squares.

## P4 spec (camera, director, acting)
1. `camera_rig.FRAMING` gains `av_hero_34`, `av_hero_front`, `av_buddy`, `av_wide_34`, `av_wide_front` (prompt 5.1), plus a `pull_truck` move. Sign conversion: 5.1 measures azimuth "positive toward the monitor"; the rig measures it toward the other speaker. With the buddy on the hero's right, hero set-ups store the negated range (e.g. `av_hero_34` = -34..-28 so the camera lands +28..+34 on the monitor side); `av_buddy` keeps -8..-2.
2. Framing uses the hero's head **with hair** (`FaceAnchor["frame_height"]`, measured at build) because the reference's 0.46 H includes hair. Wides shift their aim toward the buddy so it lands lower left.
3. `reelforge/direct.py::plan_shots_av` (rules 1-8 of 5.2): one shot per line, cut 3 frames early, no establishing shot, wides on `beat` or a short hero line after 4+ singles (34 then front), last shot `av_wide_front` pulling out 25% for at least 4.5 s, hero angle A for the first third then toggling on questions, concessions, punchlines and emotion changes, 1.2-5.0 s with listener reactions splitting long lines, linear moves at the given rates, deterministic from the seed.
4. Grammars: `reference` exactly; `signature` adds a gentle ease-in, handheld 0.04 and one rack focus (inside the first wide where the buddy speaks, 10 frames).
5. Connected move (the 0.5 s arc from `av_hero_34` to `av_buddy`): **deferred** (see Decisions).
6. Acting: hero blinks on the first frames after a cut to his close-up; eyes on the buddy while listening; one pose change (think -> rest) across a cut. Buddy: `BuddyCtrl` tracks from `reelforge/buddy.py` (talk squash and waveform from the dialogue's loudness, reaction clips from `pick_action`).
7. `render_plan.py` gains: the av distance limits, `frame_height` framing, per-frame custom-prop tracks for characters (`props`), a rack focus, and a measurement dump in stills mode.
8. Engine: `shots_av.render()` builds the plan (hero blend from `ensure_hero`, buddy and room blends) and renders through `render_plan.py`; `cli.run` routes shots-av to `plan_shots_av` and holds 0.9 s after the last word. `shots_av.animatic()` renders silent previews from estimated timing (no voices needed).
9. Evidence: the match pass (each set-up as a still in `av_studio_night`, measured subject height, eye line and centre against the reference, tolerances 0.03 H / 0.03 H / 0.05 W); the 20-line fixture test; a silent animatic.
10. Tests: av framing maths, the fixture (20 shots, same kinds in order, cuts within 2 frames, screen-time split within 3 points of 46 / 37 / 17), both grammars, determinism.

## Decisions
| Date | Decision | Why |
|---|---|---|
| 2026-11-13 | **The connected move is deferred**; the signature grammar keeps the rack focus only | Prompt 11 allows dropping it if it cannot be made clean. It has to hide a 2.6x scale change (hero head to buddy body) in 0.5 s; doing it well needs its own camera path and a look at it in motion. Revisit after P5 with the owner |
| 2026-11-13 | Framing measures the hero's head **with hair** (`FaceAnchor["frame_height"]`, set at build) for the av set-ups | The reference's 0.46 H includes hair; the skull alone would make every close-up 15% too big |
| 2026-11-13 | The match pass is measured by projection (every vertex of the head and hair, or the buddy's body, through the shot camera), not by eye | Exact and repeatable; `render_plan.py` writes `measure.json` beside the stills when the plan asks |
| 2026-11-13 | The 20-line fixture uses our own placeholder lines on the reference's timing | The reference's script is someone else's work; the real benchmark script is written with the owner at P7 |
| 2026-11-13 | Gate P3 passed: the six rooms approved as rendered | Owner: "Approve, start P4" |
| 2026-11-12 | **Gate P2 passed: brand literalness stays at the current robots' level.** Viewers must be able to tell which product each buddy is (colour, shell, signature accessory), and the robots in `p2/` reach that. No logo is traced on the buddies. Real logos elsewhere (for example on the monitor in P3) were not asked for: default none, ask again at P3 if a shot needs one | Owner: "viewers should be able to understand that they are what they are, this much is fine" |
| 2026-11-12 | **All hair designs stay viewer choices in the editor** (fringe, soft_fringe, curtain, swept, curly_top, buzz); `fringe` stays the default as the closest to the owner's own hair. P6's Hero section shows them as a picker; `ensure_hero()` builds whichever is picked | Owner: "keep all the hairs as an option in editor" |
| 2026-11-12 | **Innocent yet serious**: bigger glossy eyes (0.029 by 0.047) with two catchlights, set a little lower for an open forehead; brows rest with the inner ends a touch high (earnest, not stern); the resting smile cut to 0.10 (calm, serious); face height up to 0.37. Two new soft hair designs, `soft_fringe` and `curtain` (smooth rounded locks that hang onto the forehead), beside `fringe`; `p1/hair_options.jpg` compares them. **Owner to pick the default hair** | Owner: "something users can relate with and share; innocent yet serious; shows emotions and innocence; try some other hair design; increase the height of the face a little" |
| 2026-11-12 | **Face is oval and squarish**: head 0.31 wide by 0.36 tall (was 0.36 by 0.35); the lower face's outline is a superellipse (power 3.4) so the cheeks run straight into defined jaw corners; the chin is flatter (`CHIN` 0.80) and the jaw turns in only near the bottom | Owner: "the animated face is very rounded, keep it oval squarish" (second photo) |
| 2026-11-12 | **The hero is the owner's likeness** (from his photo): new defaults `hair: fringe` (thick black textured hair, a choppy layered fringe to the brows, sides close over the ears), `glasses: bold` (black acetate rectangles with real depth), `skin: wheat` (`#D6A688`), `beard: light` (thin moustache + chin beard), an oval face narrowing to a defined chin, straight strong brows just above the frames, a soft closed smile at rest. The earlier looks stay selectable (`swept`, `round`, `warm_brown`, `stubble`...) | Owner: "make him like this guy, it's me... do it very properly". Supersedes the round-glasses default |
| 2026-11-12 | Hair volume halved (about 3.5 cm above the scalp at head scale) | Owner: "hair height is too long" |
| 2026-11-12 | Evidence lighting: a smaller, higher key (0.45 m area) from the monitor side, fill at 1:5, so fringe, frames and nose cast readable shadows; Eevee shadow rays 4, steps 12 (also in the `shotsav` look) so those thin shadows render clean | Owner: "there will be shadows on the face based on lighting". At 1 shadow ray the frames' shadows were grainy |
| 2026-11-12 | **Buddies are modern desk robots**: satin shells with a seam line, a recessed glossy display under a domed glass lens, glowing display eyes (all the expressions kept) and a **live waveform mouth** (9 bars driven by the new `voice` control; a row of dots when quiet, a small smile when happy and quiet). Claude: terracotta shell, cream bezel, spark antenna that spins and pulses. ChatGPT: white ceramic orb on a charging puck, rounded-hex screen, teal hex ring around the lower body. Figma: charcoal display head built from the five colour blocks (two on top, a block ear, a round knob ear, a block stand). Nova: a hovering pearl orb, pill visor, beaded orbit ring | Owner: "I need more realistic models, something like this [an orange robot head with a screen face and a waveform mouth] but not same, go more creative and modern". Supersedes the spark creature and the pinwheel |
| 2026-11-12 | (superseded by the robots) Claude is a spark creature, not a lumpy blob: a soft clay core, a cream face plate (`#F0EEE6`), eight chunky rays of uneven length; it stands on its two lower rays; its rays ripple outward in turn while it talks | Owner: "make the model more creative not the generic one" (about the faceted blob, which was close to the reference's buddy) |
| 2026-11-12 | (superseded by the robots) ChatGPT is a pinwheel of six twisted white petals around a hub, with a teal glow showing through the gaps | The prompt's "interlocked petals in a hexagonal knot" built as continuous arcs merged into one white ring (it read as a sheep, then a donut) |
| 2026-11-12 | Nova's ring orbits the gem (tilted 18 degrees), not stood upright behind it | Upright, it read as a halo or a portal |
| 2026-11-12 | Evidence loops use a stand-in loudness envelope from the text (`syllable_envelope`), not a voice | No buddy voices exist yet; the real pipeline reads the line's WAV with `wav_envelope` |
| 2026-11-12 | **Skin tone and hair stay user choices.** All six skin tones and all three hair presets are options; the editor's Hero section (P6) shows them as pickers and the video renders with whatever the viewer picks. Defaults stay warm_brown and swept | Owner: "keep all of them as option in editor so user will select and generate video accordingly" |
| 2026-11-12 | Rubric approved as written | Owner |
| 2026-11-12 | Glasses: **round** is the default (owner answered "Yes, glasses" to "Should the hero wear round glasses like the reference?") | Owner decision, relayed by the session that started this one |
| 2026-11-12 | The `shotsav` look uses **Khronos PBR Neutral at exposure -0.75**, not AgX Medium High Contrast (prompt 4.4) | Measured under the 4300 K key: AgX renders a lit matte `#7C3AED` card at ΔE 49-75 (pastel lilac) at every exposure from -1.5 to 0, and Punchy is no better. PBR Neutral at -0.75 keeps the jacket's lit side at ΔE 3-5 and its shadow side at 3-5 under all three keys (table below). P5's grade adds contrast back with a purple-protected curve |
| 2026-11-12 | Jacket sheen 0.06 (was 0.35), hair sheen 0.04 | Sheen added a white grazing layer that washed purple to lilac and made black hair read grey |
| 2026-11-12 | Brows sit at 0.040 above the head's midline, above the glasses rim | At 0.019 they hid behind the rim, and the brows carry most of the acting |
| 2026-11-12 | The mouth interior is a dish that follows the face 11-21 mm behind the skin | A cavity sphere poked out through the chin, which curves back faster than any sphere |
| 2026-11-12 | The preview desk in the sheets is a plain stand-in | The real desk and chair belong to the P3 rooms; the side view shows the hero seated on nothing |

## P1 hero (what was built)
- **Proportions:** head 0.36 tall by 0.31 wide, oval with a squarish jaw (the owner's), eyes at 1.18 m seated, desk top at 0.74, shoulders 0.46 wide over the sleeves, short thick arms, hands about 0.10.
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
| neutral warm 4300K | `#9649F1` ΔE 9.4 | `#8632E4` ΔE 4.6 | `#7A29DD` ΔE 5.3 |
| screen cool 7500K | `#835AF8` ΔE 15.0 | `#7442F3` ΔE 3.7 | `#6A37EE` ΔE 4.9 |
| daylight 5600K | `#9058F6` ΔE 14.1 | `#8240F1` ΔE 2.1 | `#7734EB` ΔE 2.3 |

ΔE is CIE76 against `#7C3AED`, measured on a 15 px patch (white ticks in `purple_check.jpg`; the top-right chip is the exact sRGB value). Re-measured with the final directional key. **The jacket passes** (lit side ΔE 2-5 under all three keys, against the P1 target of 10). **The card misses its target of 6** (ΔE 9-15): it faces the key head-on and catches about half a stop more light than the jacket, so it renders lighter. That's an exposure question for each room (P3), not a hue shift: every patch stays within 8° of the target hue (262°). Before this pass, AgX gave the same jacket ΔE 61.

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
