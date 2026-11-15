# PROMPT C: "Shots-AV Animation" (low-poly desk two-hander: you + an AI buddy)

Paste everything below the line into Claude Code opened in the reelforge repo, in a **fresh session**. It builds a new style and a new editor page called **Shots-AV Animation**: a male hero in Aayush Visuals purple talks to a small AI buddy (Claude, ChatGPT, Figma) on his desk, in dark and light rooms, shot and cut like the reference reel, and finished better than it.

Reference stills are already in `references/style/shots-av/` (five set-ups, cut strips, first/last frame of every shot, a 2 fps timeline). The source reel is the owner's download at `~/Downloads/reelsvideo.io_1794385605738.mp4` (720x1280, 30 fps, 48.85 s). It is someone else's work: use it for measurement and side-by-side comparison only. Never copy its script, character or exact buddy model into anything we publish.

---

# 0. How to work (read first)

1. Read `CLAUDE.md`, `docs/HANDOFF.md` (sections 7 and 8), `docs/prompts/01-cinema-real-pixar-level.md` (camera and director sections), then the code you will extend: `reelforge/engines/`, `reelforge/direct.py`, `reelforge/schema.py`, `reelforge/captions.py`, `reelforge/finish.py`, `blender/looks/`, `blender/camera_rig.py`, `blender/render_plan.py`, `blender/build_character.py`, `blender/build_set.py`, `editor/src/App.tsx`, `editor/src/components/Sidebar.tsx`, `editor/src/data/catalog.ts`, `editor/server/api.ts`.
2. The working tree has uncommitted edits (`camera_rig.py`, `direct.py`, `schema.py`, `render_plan.py`, `looks/cinema.py`, two tests and others). They are someone's in-progress cinema work. **Ask the owner to commit or stash them before you start.** Do not revert, reformat or fold them into your commits.
3. Branch `feat/shots-av` from `main`. Keep a ledger at `docs/production/shots-av/PROGRESS.md` (phase, status, commit, evidence), in the same shape as `docs/production/PROGRESS.md`.
4. Each phase: a 10-line spec, build, render the evidence listed, review it against the reference stills, show the owner, and **wait at the gate**.
5. Keep token use low: cheap subagent models for mechanical work (data tables, test scaffolds, UI wiring); keep art decisions, camera tuning and reviews for yourself.
6. Never say "done" without evidence: a render, a measured number or a passing test. Say plainly where a result falls short.

# 1. Mission

Add a third style, **Shots-AV Animation** (`style: "shots-av"`), and a page for it in the editor. Input: a two-speaker script (the hero and one buddy). Output: a 9:16 reel that looks like a polished low-poly 3D short: big-headed hero at a desk, a small buddy that answers him, shallow depth of field, city bokeh or soft daylight, one caption line at a time.

"Beat the reference" means: match its camera grammar and pacing exactly (section 5), then win on the points in section 6: character finish, background finish, lighting, acting, camera polish, captions, output quality.

# 2. What the reference actually does (measured frame by frame)

## 2.1 The headline finding
**The camera never travels from one actor to the other.** All 19 transitions are **hard cuts**, one frame, no pan, no whip, no dissolve (verified on the frame strips in `02_cuts_frame_by_frame.jpg`). It feels smooth for five reasons, and these are the rules to copy:
1. **Every shot is moving.** No shot is static: each one has a slow, linear drift (push-in, pull-out or sideways truck), so the cut lands on motion and leaves on motion.
2. **Cut on the line.** Each cut falls 2 to 4 frames before the speaker's first syllable. The caption fades in 3 to 4 frames after the cut and fades out about 3 frames before the next one.
3. **Shot / reverse shot on one side of the desk.** All five cameras stay on the viewer's side. The hero looks down and screen-right toward the buddy; in the buddy's shot the hero sits blurred behind it on the same side. Screen direction never flips.
4. **Stable eye heights.** The hero's eyes sit at 0.50 to 0.54 of frame height in every close-up; the buddy's eyes at about 0.62. The viewer's eye never has to hunt.
5. **One light scheme, one palette** across every shot, so a cut changes only size and subject.

## 2.2 The five camera set-ups (see `01_five_setups.jpg`; fractions are of the 9:16 frame)
| Id | Name | What is in frame | Size and placement | Camera |
|---|---|---|---|---|
| A | Hero close-up, three-quarter | Hero head and shoulders, raised fist at screen-right, bokeh behind | Head (with hair) 0.46 H tall and about 0.85 W wide; hair top at 0.23 H, eyes 0.52 H, chin 0.67 H; shoulders run off the bottom | Long lens (about 85 mm), about 30 degrees round to the hero's left-front (the monitor side), 3 to 6 degrees above his eye line, very shallow focus |
| B | Buddy single (the reverse) | Buddy on the desk, hero's torso and chin blurred behind it at upper right, a blurred pen in front | Buddy 0.38 H tall, 0.63 W wide, centred at 0.50 W and 0.69 H; desk fills the bottom 0.30 H; the top 0.45 H is bokeh and caption space | Long lens (85 to 100 mm), at desk height looking almost level (3 to 5 degrees down), in front of the desk, shifted so the hero lands upper right; foreground and background both out of focus |
| C | Wide, three-quarter | Hero, buddy, monitor, keyboard, sticky notes | Head 0.25 H tall, 0.40 W wide; eyes 0.36 H; desk edge 0.70 H; monitor cut by the right edge (0.73 to 1.0 W, 0.33 to 0.66 H); buddy at 0.10 to 0.30 W, 0.57 to 0.71 H; the bottom 0.28 H falls to near black | About 50 mm, 15 degrees off axis, 8 degrees above eye line |
| D | Hero close-up, frontal | Hero straight on, looking down at the lens (the buddy's point of view) | Same head size as A; eyes 0.54 H; both shoulders even | 85 mm, on the hero's axis, 3 to 5 degrees **below** his eye line |
| E | Wide, frontal | Same content as C, squarer, both hands on the desk | Head 0.40 W; hair top 0.22 H; eyes 0.35 H; desk edge 0.66 H; buddy lower left; monitor right | About 50 mm, on axis, 6 degrees above eye line |

The reel never shows the hero below the desk line, never shows a full body, and never opens on an establishing wide. It opens on set-up A mid-thought.

## 2.3 Shot list (20 shots, 48.85 s)
| # | In to out (s) | Length | Set-up | Speaker | Camera move inside the shot | Notes |
|---|---|---|---|---|---|---|
| 1 | 0.00 to 3.30 | 3.30 | A | hero | push-in about 5%, slight drift right | fist on cheek; first line names the buddy |
| 2 | 3.30 to 5.00 | 1.70 | B | buddy | slight truck | short cheerful reply |
| 3 | 5.00 to 7.33 | 2.33 | A | hero | push-in | |
| 4 | 7.33 to 11.53 | 4.20 | B | buddy | pull-out about 12% with a truck right | two sentences; eyes squash to small squares for the second (9.3 to 10.7 s) |
| 5 | 11.53 to 12.87 | 1.33 | A | hero | near static | trailing-off pause line |
| 6 | 12.87 to 15.07 | 2.20 | C | buddy | push-in about 4% | **first wide**, at 26% of the runtime; reveals the monitor and desk |
| 7 | 15.07 to 16.97 | 1.90 | A | hero | push-in | |
| 8 | 16.97 to 18.77 | 1.80 | B | buddy | drift | |
| 9 | 18.77 to 20.00 | 1.23 | D | hero | near static | **angle change** on a surprised question; shot opens on a blink; hands now down |
| 10 | 20.00 to 21.83 | 1.83 | B | buddy | drift | |
| 11 | 21.83 to 23.70 | 1.87 | D | hero | push-in | |
| 12 | 23.70 to 27.63 | 3.93 | B | buddy | slow pull-out | long line |
| 13 | 27.63 to 28.90 | 1.27 | E | hero | push-in about 3% | second wide, on a two-word concession |
| 14 | 28.90 to 32.00 | 3.10 | B | buddy | drift | |
| 15 | 32.00 to 33.90 | 1.90 | A | hero | push-in | back to the first angle |
| 16 | 33.90 to 38.47 | 4.57 | B | buddy | very slow drift | the thesis line; longest single, deliberately held |
| 17 | 38.47 to 40.33 | 1.87 | D | hero | near static | opens on a blink; ends on a small smile (40.0 s) |
| 18 | 40.33 to 41.73 | 1.40 | B | buddy | drift | excited: body tips about 8 degrees, a small hop |
| 19 | 41.73 to 43.93 | 2.20 | A | hero | push-in | smile drops to deadpan |
| 20 | 43.93 to 48.85 | 4.92 | E | buddy, then hero | **pull-out about 25%**, a lamp enters top right | slow blink at 46.0 s; closes on "Two pixels, Claude."; last 0.9 s is a silent hold |

Numbers to hold on to:
- Average shot 2.44 s; shortest 1.23 s; longest 4.92 s. Nothing over 5 s.
- Screen time: buddy singles 46% (8 shots, 22.5 s), hero close-ups 37% (9 shots, 17.9 s), wides 17% (3 shots, 8.4 s).
- One shot per line. The speaker is always on screen, except the three wides.
- Wides arrive every 6 to 7 shots, always on a short pause or concession line, and the reel ends on one.
- The hero's angle stays A for the first third, then alternates A and D on each emotional turn (question, concession, punchline).
- Pose continuity changes once: fist on cheek (shots 1 to 7), then both hands on the desk (shot 9 onward).

## 2.4 Characters, set, light and captions in the reference
- **Hero:** head about as tall as the seated torso; near-spherical head; eyes are black vertical ovals with one white highlight, set wide and low; thin round wire glasses; no eyebrows, no nose beyond a small wedge; mouth is a dark rounded rectangle that flaps open and closed, with one smile curve used twice. Long dark hair in faceted chunks, grey headphones, puffy yellow jacket with a lighter zip band, black tee, mitten hands. Shading is faceted (visible triangles on the cheeks).
- **Buddy:** a lumpy orange low-poly blob about 0.4 of the hero's head height, two black vertical rectangle eyes, no mouth, three small feet. It "talks" by bobbing and squashing; emotion is eye height (tall = neutral, short squares = dry or sceptical) and body tilt.
- **Set:** desk against a tall window, night city behind. Background is reduced to rounded-square bokeh in amber, cyan (about `#5EAAD5`) and red (about `#DB5347`) on deep navy, with dark window mullions. Dark brown desk, dark keyboard, one monitor at screen-right showing blue and white chat bars, yellow and orange sticky notes, a pen, a desk lamp that is only a sliver at the top-right corner until the last pull-out reveals it.
- **Light:** a strong warm orange-pink key on the face from low front-right, cool navy ambient everywhere else, the jacket pushed almost to glowing, mild bloom, heavy vignette along the bottom. The light never changes during the reel.
- **Captions:** top centre at 0.07 to 0.11 H, white bold grotesque, one or two lines of at most about 22 characters, the whole line at once (no word highlight), on a faint dark rounded plate. Faces never share space with text.
- **Sound:** a continuous bed under the dialogue (no gap below -38 dB for longer than 0.25 s), mean -19 dB, peaks at -0.1 dB. Levels were measured, the audio was not listened to: have the owner describe the music and voices before copying the mood.

# 3. Non-negotiable rules

- Everything in `CLAUDE.md` applies. No paid tools, no API keys, no accounts, no AI image or video services. Blender, ffmpeg and Python only.
- **Original assets only.** Our hero, buddies and rooms are our own designs. The reference's character and its exact buddy mesh are not to be traced or rebuilt one-to-one.
- **Brand buddies are "inspired by", not logos.** Each buddy reads as its product through colour and silhouette (section 4.2) but is an original creature; do not model the trademarked logo itself, and do not imply endorsement. If the owner wants literal logos on screen (for example on the monitor), that is his call at gate P2: record the decision in the ledger.
- **The "never reduce character quality" rule is untouched.** These are new assets authored low-poly on purpose. Never decimate, downscale or prune the existing cast (Matt, Freya, Mina, Kai and the rest) to fit this style; they are simply not part of it.
- Backwards compatible: `style` default stays `blender3d`, `look` default stays `classic`, every existing test keeps passing, the `reelforge/` core stays standard-library only.
- Deterministic: same `performance.json` and seed give identical frames.
- Blender path from `tools/blender_path.txt` (currently 4.5.15); keep 5.x working through `bl_common.EEVEE`. Never `setx`.

# 4. What to build: the art

## 4.1 The hero, "AV" (male, the owner's stand-in)
New module `blender/shotsav/hero.py`, built by `blender/build_shotsav.py -- <out.blend> hero`. Scripted geometry, no downloads.

Proportions (metres, seated at the desk): head 0.34 tall, 0.36 wide, slightly flattened sphere with a soft jaw 5% wider than the reference's to read male; neck hidden by the collar; torso 0.36 tall, shoulders 0.46 wide (broader than the reference's 0.40); upper arms short and thick; hands 0.10. Seated eye height 1.18 with the desk top at 0.74.

Face:
- Eyes: black ovals 0.040 tall by 0.024 wide, 0.115 apart, centred 0.02 below the head's midline, each with one fixed highlight. Upper and lower lid meshes for blink, half-lid, squint and wide.
- **Eyebrows (the reference has none):** two short dark bars that raise, lower, angle and pinch. They carry most of the emotion.
- Nose: a single small wedge.
- **Mouth:** a real inset mouth with 8 shapes (rest, closed MBP, small open, wide open, O, E/smile-open, F/V, smile closed), plus corner up and corner down. Dark warm interior, never pure black. Drive it from the existing viseme tracks through `FaceCtrl` (map the 52 ARKit channels down to these shapes), so lip sync beats the reference's flap.
- Hair: short, male, in 9 to 14 faceted clumps: side part, a swept fringe lifted off the forehead, tapered sides. Three presets: `swept` (default), `curly_top`, `buzz`.
- Options as dials in a `HERO` table: `glasses` (`round` default, `rect`, `none`), `headphones` (`on`, `neck` default, `none`), `stubble` 0 to 1 (a darker jaw band, default 0.3), `skin` (six tones, default a warm medium brown; the owner picks at gate P1), `hair_color`.

Wardrobe, **Aayush Visuals purple** (values read from aayushvisuals.com):
| Token | Hex | Use |
|---|---|---|
| purple | `#7C3AED` | jacket body (default outfit) |
| purple-mid | `#6D28D9` | jacket shadow side, cuffs, hem |
| purple-soft | `#A78BFA` | zip band, hood lining, drawcord tips |
| lilac | `#DDD6FE` | tiny chest mark, highlights on trim |
| ink | `#1F1F1F` | tee under the jacket |
| cream | `#F4F2EE` | light-room walls, alternate tee |

Outfits: `puffer` (default: purple puffer, soft-purple zip band, ink tee), `hoodie` (purple hoodie, hood down, drawcords), `overshirt` (purple overshirt over a cream tee). A small chest mark in lilac, modelled on the slash-and-dot mark of the owner's site, is optional and off by default.

Finish (this is where we beat the reference):
- Smooth-shade the skin and eyes; keep facets only where they are a style choice (hair clumps, jacket panels, buddy). No shading triangles on the face.
- 2 to 4 mm bevels on every hard edge so edges catch light.
- Skin with mild subsurface and a soft blush on cheeks, ears and nose tip; jacket with a matte nylon roughness break and stitched panel seams as geometry; glasses with a thin real rim and a faint lens glint that never hides the eyes.
- **Hands with four blocky fingers and a thumb**, posed (resting, fist-on-cheek, point, open palm, typing). No mittens.
- Rig contract identical to the cast: `CHAR_root`, `Body`, `Head`, `ElbowL`, `ElbowR`, `FaceCtrl`, `FaceAnchor`, `EyeFocus`, so `render_plan.py` needs no special case. Add `HandL`/`HandR` pose selectors and a `Lean` control.

## 4.2 The buddies (AI desk companions)
New module `blender/shotsav/buddies.py`, one table `BUDDIES`, built by `build_shotsav.py -- <out.blend> buddy <id>`. All share one rig and one animation set, so a script can swap buddies without re-timing.

Shared anatomy: body 0.13 to 0.15 tall (about 0.4 of the hero's head), two black rectangle eyes 0.022 tall by 0.008 wide, no mouth, three or four stub feet, a soft contact shadow. Controls on a `BuddyCtrl` empty: `squash`, `lean_x`, `lean_y`, `hop`, `eye_h` (height: 1 neutral, 0.35 dry squares, 0 closed), `eye_shape` (rect, happy arcs, sad tilt, wide, wink), `eye_look_x/y`, `glow`.

| Id | Reads as | Body | Colours | Signature touch |
|---|---|---|---|---|
| `claude` | Claude | rounded starburst blob, 8 soft lobes | terracotta `#D97757`, shadow `#B5553A` | lobes ripple outward when it speaks |
| `chatgpt` | ChatGPT | six interlocked rounded petals in a hexagonal knot | off-white `#F3F3F0` body, `#0D0D0D` eyes, teal `#10A37F` inner glow | petals rotate a few degrees while "thinking" |
| `figma` | Figma | five rounded blocks stacked two-by-three with one missing, eyes on the top pair | `#F24E1E`, `#FF7262`, `#A259FF`, `#1ABCFE`, `#0ACF83` | blocks offset and snap back into a grid on emphasis |
| `nova` | any other assistant | a faceted gem with a floating ring | recolourable; default cool grey `#C9CCD6` with a lilac glow | ring speeds up when it speaks |

Acting (beat the reference's bob-only buddy): talk = squash driven by the dialogue's loudness envelope (3 to 6% scale, 2-frame attack, 5-frame release) plus a tiny lean toward the hero; idle = slow breathing and an occasional look at the hero; reactions as named clips of 8 to 20 frames: `hop`, `tilt`, `dry` (eyes to squares), `happy`, `think`, `shrink`, `nod`, `lookaway`. A line can name a clip with `"action"`; otherwise pick from emotion and punctuation ("!" gives `hop`, a trailing "..." gives `think`, intensity under 0.3 gives `dry`).

## 4.3 The rooms (three dark, three light)
New module `blender/shotsav/rooms.py`, table `ROOMS`, built by `build_shotsav.py -- <out.blend> room <id>`. Every room is a **desk two-hander stage** with the same contract as `blender/sets.py`: lights `Key`, `Rim`, `Fill`, `Glow`, `ScreenMat`, `Mark_A` (the hero's chair) and `Mark_B` (**on the desk**: 0.35 m to the hero's right, 0.25 m toward the viewer, at desk height), each with `base_color`/`base_energy` so moods keep working.

Shared layout: desk 1.6 by 0.75 m at 0.74 high; monitor 0.55 m to the hero's left, turned 25 degrees toward him, so it sits at screen-right in the wides; keyboard, pen, two sticky notes, a mug; a lamp placed so it enters frame only on the closing pull-out. The background wall or window is 2.2 m behind the hero; far lights are real emissive cards 30 to 120 m away so the bokeh comes from true depth of field, not a painted plate.

Because the jacket is purple, **do not copy the reference's orange key**: warm orange light turns purple to muddy brown. Use a neutral-warm key (about 4300 K, lightly desaturated) so the jacket stays `#7C3AED`, and put the warmth in the background: amber is purple's complement and makes it pop.

| Id | Tone | Look | Light |
|---|---|---|---|
| `av_studio_night` | dark | the reference's situation, upgraded: tall window, indigo night city, amber and soft-cyan bokeh, a few red tail-light dots | neutral-warm key from the monitor side, violet rim `#8B5CF6` from behind, navy fill, amber practical lamp |
| `av_neon_den` | dark | windowless den: shelf wall, violet and cyan LED strips, a plant, a poster grid | cyan-white screen key, violet strip rim, magenta-free palette |
| `av_late_office` | dark | empty open office at night: rows of sleeping monitors and one exit sign as bokeh | cool overhead spill, warm desk lamp key, green-white exit accent |
| `av_studio_morning` | light | cream wall `#F4F2EE`, big soft window, plants, pale wood desk; the website's look in 3D | large soft daylight key, sky-blue fill, thin warm rim |
| `av_cafe_day` | light | window seat, street outside as bright bokeh, light oak, a pastry plate | bright side window key, bounce fill from the table |
| `av_cyc_lilac` | light | seamless studio sweep fading cream to lilac `#DDD6FE`, desk only; product-video clean | broad top key, soft floor bounce, gentle violet back glow |

Finish to beat the reference: bevelled furniture; a monitor whose screen content animates (chat bubbles appear when the buddy speaks, a caret blinks when the hero does); screen light that flickers slightly on the hero's chest; thin haze for depth; round or hexagonal bokeh with a little chromatic edge; slow background life (a blinking aircraft light, a passing headlight sweep, swaying leaves in the light rooms); contact shadows and ambient occlusion under every object; no black crush at the bottom of the frame (the reference loses the lower quarter): keep desk-front detail at 8 to 12% luminance.

## 4.4 The look
`blender/looks/shotsav.py`, `NAME = "shotsav"`, registered in `blender/looks/__init__.py` and added to `LOOKS` in `reelforge/schema.py`. EEVEE only, `USE_RIG = True`. Soft shadows, AO, bloom on emissives only, real depth of field, AgX with a medium-high contrast look. `look_params` dials: `key_warmth`, `rim`, `haze`, `bokeh`, `screen_flicker`, `saturation`.

# 5. What to build: camera, direction and acting

## 5.1 Camera set-ups
Add five kinds to `camera_rig.FRAMING` without touching the existing ones:

| Kind | Lens | Head (or buddy) height | Eye line from top | f-stop | Azimuth | Elevation |
|---|---|---|---|---|---|---|
| `av_hero_34` | 85 | 0.46 | 0.52 | 1.8 | +28 to +34 (monitor side) | +4 |
| `av_hero_front` | 85 | 0.46 | 0.54 | 2.0 | -3 to +3 | -4 |
| `av_buddy` | 100 | buddy 0.38 | buddy eyes 0.62 | 2.0 | -8 to -2 | +4 |
| `av_wide_34` | 50 | 0.25 | 0.36 | 2.8 | +12 to +18 | +8 |
| `av_wide_front` | 50 | 0.25 | 0.35 | 2.8 | -3 to +3 | +6 |

Sign convention in this table: azimuth is measured from the desk's front axis, positive toward the monitor (the hero's left, away from the buddy). `camera_rig` measures azimuth toward the other speaker, so convert the sign when you add the rows, and prove it with the match pass below.

`av_buddy` frames `Mark_B`'s occupant by its own height and must place the hero's blurred torso in the upper-right third; add a foreground blur object (the pen or mug edge) within 0.25 m of the lens. For all five, keep the top 0.14 H clear for captions and never let the hero's eyes leave 0.33 to 0.56 H.

**Match pass (evidence required):** render each set-up as a still in `av_studio_night` and lay it beside the matching panel of `01_five_setups.jpg`. Tolerances: subject height within 0.03 H, eye line within 0.03 H, subject centre within 0.05 W. Write the measured values into the ledger.

## 5.2 The director: `plan_shots_av()` in `reelforge/direct.py`
A new function beside `plan_shots_v2` (do not change v2), chosen when `style == "shots-av"`. Rules, all taken from section 2:
1. One shot per line. Cut 3 frames before the line starts.
2. The speaker gets the shot: hero lines use a hero close-up, buddy lines use `av_buddy`.
3. **No establishing shot.** Open on `av_hero_34`.
4. Wides: a line marked `"beat": true`, or a hero line of three words or fewer after at least four singles, becomes a wide (alternate `av_wide_34` then `av_wide_front`). Target one wide per 6 or 7 shots, 15 to 20% of screen time. **The last shot is always `av_wide_front` with a 25% pull-out, at least 4.5 s long, holding 0.9 s after the final word.**
5. Hero angle: `av_hero_34` only for the first third of the runtime; after that switch between `av_hero_34` and `av_hero_front` whenever the line is a question, a concession, a punchline or a mood change.
6. Lengths: minimum 1.2 s, maximum 5.0 s. A line longer than 5 s is split by a 1.0 to 1.4 s listener reaction (the other character, silent, reacting).
7. Moves, linear so cuts land in motion (`ease = 0`): hero close-ups push in 1.6% per second (cap 6%); `av_buddy` pulls out 2.8% per second (cap 12%) with a 1 to 2% W truck; wides push in 1.5% per second; near-static (0.5% drift) on lines under 1.4 s. `handheld = 0`.
8. Deterministic from `camera.seed`; the editor preview and the render must agree.

Two presets in `camera.grammar`:
- `reference` reproduces the rules above exactly.
- `signature` (default, our upgrade) adds: gentle ease-in on the first frame of each move only; handheld 0.04; **one rack focus per reel** (inside a wide, focus pulls from the hero to the buddy as the buddy starts speaking, 10 frames); and **at most one connected move per reel** on the biggest turn of the script: a 0.5 s arc from `av_hero_34` down to `av_buddy` with focus following, used instead of a cut. This is the "camera glides to the second actor" moment the reference only implies. Never more than one; the cutting rhythm is the style.

Test with a fixture built from the timing table in 2.3 (20 lines with those durations and speakers): `plan_shots_av(..., grammar="reference")` must return 20 shots with the same kinds in the same order, cut times within 2 frames, and the screen-time split within 3 points of 46 / 37 / 17.

## 5.3 Acting
- **Hero:** visemes into the 8 mouth shapes; brows and lids from the line's emotion; blink every 2.8 to 4.2 s, **and prefer to place a blink on the first two frames after a cut to a hero close-up** (the reference does this three times and it softens the cut); eyes look at the buddy while listening, flick to the monitor on "work" words, and glance at the lens on a punchline; small head tilt per line; idle breathing. Pose sets: `think` (fist on cheek), `rest` (both hands on the desk), `type`, `point`, `shrug`. Change pose at most twice per reel, only across a cut.
- **Buddy:** section 4.2. It faces the camera in singles and turns 20 degrees toward the hero in wides.
- **Listener life:** whoever is not speaking still blinks, breathes and reacts once per long line.

## 5.4 Schema additions (`reelforge/schema.py`, validated, all optional)
```json
{
  "style": "shots-av",
  "environment": "av_studio_night",
  "characters": {
    "me":    {"model": "av_hero", "outfit": "puffer", "outfit_color": "#7C3AED", "glasses": "round", "headphones": "neck"},
    "buddy": {"model": "buddy_claude"}
  },
  "camera": {"grammar": "signature", "seed": 7},
  "lines": [{"speaker": "me", "text": "...", "emotion": "calm", "beat": false, "action": ""}]
}
```
Exactly one hero and one buddy; reject anything else with a clear error. `outfit_color` accepts any hex and defaults to brand purple.

# 6. How we beat the reference (score each row at the final gate)
| Area | Reference | Ours |
|---|---|---|
| Face shading | faceted, noisy triangles on cheeks | smooth skin, bevelled forms, blush, soft subsurface |
| Expression | eyes and a flapping rectangle | brows, lids, 8 mouth shapes, real lip sync |
| Hands | mittens | fingered hands, five poses |
| Buddy | bob, one squint | 8 reaction clips, eye shapes, per-brand signature motion |
| Light | one fixed warm key, crushed bottom quarter | rim separation, practicals, screen flicker, mood shifts per line, readable shadows |
| Background | flat square bokeh | true depth-of-field bokeh, haze, moving background life, animated monitor |
| Camera | cuts and linear drift only | the same grammar plus one rack focus and one connected move |
| Captions | plain white line | same placement, brand-clean type, speaker tint, safe-area aware |
| Sound | music bed and voices | bed plus keyboard foley, room tone, a soft tone for each buddy line start |
| Output | 720x1280, about 420 kbps | 1080x1920, 30 fps, 10 to 12 Mbps, graded, light grain |

# 7. Captions, sound and finish
- New caption template `shotsav_top` in `reelforge/captions.py`: top centre, baseline block at 0.08 to 0.12 H, bold grotesque (Geist 700, already in the editor's font list), 46 px at 1080 wide, white, at most two lines of 22 characters, whole line at once, fade in 4 frames after the cut and out 3 frames before the next. A faint ink plate (`#1F1F1F` at 45%, 10 px radius). Optional speaker tint: a 6 px dot before the line, purple for the hero and the buddy's body colour for the buddy. Word-by-word highlighting stays available but off by default for this style.
- `reelforge/ambience.py`: add `keys` (sparse keyboard taps while the hero is in a `type` pose), `room_night`, `room_day`, and a 60 ms soft blip at each buddy line start. Music is the owner's own file dropped into the project; never download music.
- `reelforge/finish.py`: grade `shotsav_dark` and `shotsav_light` (protect purple: no hue shift between 255 and 285 degrees, saturation ceiling so `#7C3AED` does not clip), mild halation, a soft vignette that stops at 12% darkening, fine grain, -14 LUFS.

# 8. The engine
`reelforge/engines/shots_av.py`, about 60 lines, registered in `reelforge/engines/__init__.py`: `ID = "shots-av"`, `NAME = "Shots-AV Animation"`, `DESCRIPTION`, `CAPABILITIES` (lipsync `pipeline-visemes`, ratios 9:16 first, cost free, runs local). It reuses `blender3d.render()` with `plan["look"] = "shotsav"`, routes shot planning to `plan_shots_av`, and its `build_assets()` builds the hero, the four buddies and the six rooms into `assets/build/shotsav/`. `reelforge build-assets --style shots-av` and `reelforge run <project> --style shots-av [--stage stills] [--draft]` must work.

Budgets on the RTX 4060 laptop (8 GB): preview still under 3 s; draft reel (50% size, 16 samples) under 6 minutes for 48 s; final 1080x1920 under 30 minutes for 48 s; VRAM under 5 GB. Measure with `reelforge bench` and record it.

# 9. The page: "Shots-AV Animation"

Route `/shots-av` (list of Shots-AV projects, plus "New") and `/shots-av/:id` (the workspace). Add it to `NAV` in `Sidebar.tsx` directly under "Create", label **Shots-AV Animation**, a lucide icon such as `MessagesSquare`. Add `"shots-av"` to `StyleId` in `editor/src/lib/types.ts` and a `STYLES` entry in `catalog.ts` (status `available`, local, free). Reuse the editor's tokens in `editor/src/styles/tokens.css` as they are: the editor keeps its own accent; purple is the hero's jacket, not a re-theme. Follow the brief's rule: dark, minimal, no AI-slop patterns (no gradient hero banners, no emoji, no glass cards).

Workspace layout, three columns that collapse to tabs under 1100 px:
1. **Script (left, 360 px).** A two-speaker chat-style editor: each line is a row with a speaker toggle (Me / Buddy), the text, an emotion chip, a "Beat" toggle (forces a wide) and a buddy action menu on buddy lines. Paste a plain script and it splits on line breaks and "Name:" prefixes. A footer shows line count, estimated runtime and the predicted shot mix (hero / buddy / wide percentages) against the 37 / 46 / 17 target.
2. **Stage (centre).** A 9:16 preview frame. Under it a **shot strip**: one tile per shot with its set-up icon, length and speaker colour; click a tile to render that shot's preview still; drag a tile's edge only if the line allows it; a tile menu overrides set-up, move and focus pull (writes `camera.overrides`). Above it: "Preview shot", "Draft reel", "Final render" with time estimates from the bench numbers.
3. **Look (right, 320 px).** Sections: **Hero** (outfit, jacket colour swatches starting with the five brand purples plus a custom hex, hair, glasses, headphones, skin, stubble); **Buddy** (four cards with rendered thumbnails); **Room** (six cards in two groups labelled Dark and Light); **Camera** (grammar: Reference or Signature, drift amount, rack focus on/off, connected move on/off); **Captions** (top or lower, plate on/off, speaker tint); **Sound** (ambience, foley, music file).

States to design, not skip: empty project (three starter scripts written by us, original), assets not built yet (one button that runs `build-assets --style shots-av` with a progress log), voices missing (per-line status with the existing ElevenLabs-in-Chrome flow from the Voices page), render running, render failed (show the last 20 log lines), render done (player, file path, "Open folder"). Keyboard: Enter adds a line, Tab switches speaker, Ctrl+Enter previews the current shot. Every control reachable by keyboard with a visible focus ring.

Server: extend `editor/server/api.ts` in its existing routing style with a Shots-AV catalog endpoint (hero options, buddies, rooms read from the Python tables so the UI never drifts from the pipeline), a shot-plan endpoint that returns `plan_shots_av` output for the current script, and a preview-still endpoint for one shot. Thumbnails for buddies and rooms are rendered by a `reelforge thumbnails --style shots-av` command into `assets/build/shotsav/thumbs/`.

# 10. Phases and gates
| Phase | Build | Evidence to show the owner |
|---|---|---|
| P0 | branch, ledger, rubric (`docs/production/shots-av/RUBRIC.md`, the ten rows of section 6 scored 0 to 10), engine and look stubs, schema fields with tests | tests pass; rubric approved |
| P1 | the hero: geometry, face, three outfits, hands, rig | turnaround sheet (front, three-quarter, side), an expression sheet of 12 faces, the purple checked beside `#7C3AED` under each room's key. **Owner picks skin, hair, glasses.** |
| P2 | four buddies and the clip set | line-up still, a 6 s loop of each buddy talking and one reaction. **Owner decides how literal the brand shapes may be.** |
| P3 | six rooms | one wide and one hero close-up still per room, hero and Claude buddy in place |
| P4 | five set-ups, `plan_shots_av`, hero and buddy acting | the match pass of 5.1 with measured numbers; the 20-line fixture test; a silent animatic |
| P5 | captions, ambience, grades | a 10 s graded clip with captions and sound in one dark and one light room |
| P6 | the editor page | a walkthrough from pasted script to a preview still and a draft reel |
| P7 | **the benchmark reel** | below |
| P8 | docs (`HANDOFF.md` section, README), bench numbers, final test run | ledger complete |

**P7, the benchmark.** Write an **original** 20-line script with the owner (his voice, his world: design, clients, late nights) that follows the timing table in 2.3 line for line: same speakers, same durations, wides in the same places. Voices come from the owner's ElevenLabs web app through his logged-in Chrome, as usual. Render it twice in `av_studio_night` with the Claude buddy: once with `grammar: "reference"`, once with `"signature"`. Then build `docs/production/shots-av/side_by_side.mp4` (reference on the left, ours on the right, internal use only) and score both on the rubric. Ship only when ours wins at least 8 of the 10 rows and loses none by more than a point; otherwise list the losing rows and fix them. Also render the same script once in `av_studio_morning` to prove the light rooms hold up.

# 11. Honest limits
- This is stylised low-poly 3D: it can clearly beat the reference on finish, but it will not look like the Cinema Real style, and should not try to.
- Purple is harder to light than yellow: it darkens fast and shifts under warm light. Expect two or three lighting passes at P1 and P3 before the jacket reads as brand purple in every room.
- The connected camera move has to hide a big change of scale between the hero and the buddy; if it cannot be made clean, drop it and keep the rack focus. Say so in the ledger.
- Audio quality depends on the owner's voice takes and music; the pipeline can only mix and level them.
