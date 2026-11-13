# PROMPT B: "Painted Toon" (a second art style in the same ReelForge editor)

Paste everything below the line into Claude Code (Fable 5.2) opened in the reelforge repo. Run it **after Prompt A's Phases 1 and 2** (the `blender/looks/` system and the new camera rig), because Painted Toon is a second "look" on the same pipeline, and it reuses the camera, the director, the export and the editor scaffolding. If Prompt A has not landed, do its Phase 1 (look system) and Phase 2 (camera) first, exactly as written there, then continue here.

---

# 0. How to work (read first)

1. Read `CLAUDE.md`, `docs/HANDOFF.md` (sections 7 and 8), `docs/prompts/01-cinema-real-pixar-level.md` (at least sections 3, 4, 7, 8, 14, 15), `reelforge/engines/`, `blender/render_plan.py`, `blender/looks/`, `reelforge/finish.py`.
2. Work on a branch `feat/painted-toon` cut from the branch that has Prompt A's look system. Keep a ledger at `docs/production/painted-toon/PROGRESS.md`.
3. Each phase: spec in 10 lines, build, render the evidence listed, review as an **illustrator and 2D animator**, show the owner, and wait at the gate.
4. Keep token and credit use low. Cheap subagent models for mechanical work; keep shader design, colour decisions and reviews for yourself.
5. Never claim "done" without evidence (a render, a number, a test). Report honestly where the result falls short of the references.

# 1. Mission

Add a second art style, **Painted Toon**, selectable next to **Cinema Real** in the editor's style picker. Same script, same voices, same characters (Matt, Freya, Mina, the procedural cast and any new characters from Prompt A), same rooms, same lip-sync, same shots, same captions and export. Only the rendering changes: instead of realistic light, the output looks like **animated illustration**: flat colour shapes with painted shading, inked or painted edges, brush texture, stylised light and colour shadows, and backgrounds that look painted.

Target quality: **Higgsfield-level / Spider-Verse-level stylised frames**. The owner's reference frames show four directions; support all of them as **look variants** of this style:
1. **"Ink & Cel 3D"** (man at the laptop): cel-shaded 3D characters with inked contours, painterly textures, soft warm lamp light, rich dark environment, small paper details. Rendered fully in 3D. **This is the primary variant.**
2. **"Gouache Illustration"** (the train frames): flat-colour shapes, big shadow shapes, visible brush edges, simplified faces, warm and cool light patches, painted backgrounds with motion blur streaks.
3. **"Pixar Painted"** (the kiss frame): soft, rounded, glowing painted 2D feel, warm rim light, blurred painted bokeh crowd, bright eyes with big highlights.
4. **"Flat Vector Paint"** (the office frame): bold shape-based shading, hard shadow shapes, almost no outlines, texture-rich flat colour, muted palette.
Implement variant 1 completely first. Variants 2 to 4 are presets over the same shader and compositor stack (different parameters), so they must not need new code paths.

Honesty clause: a free local Blender pipeline can reach convincing **stylised 3D** (variant 1 and 4 closely, 2 and 3 approximately). The painted-illustration feel of the train and kiss frames comes partly from hand painting or AI generation; match the *visual language* (shapes, colour, edges, texture, timing), and report the remaining gap in scores. Never inflate.

# 2. Ground truth

## 2.1 What exists (build on, do not rewrite)
Same repo map as Prompt A section 2.1. Reuse: the shared pipeline (`script > voice > timeline > faces > shots > moods > render_plan.json`), the `blender/looks/` module system, `blender/camera_rig.py`, `reelforge/direct.py`, `reelforge/finish.py`, `reelforge/engines/` registry and the editor's `STYLES`.
Assets built for realism (imported 4K textures, hair cards, SSS skin) are **kept as is** and **overridden at render time** by toon materials; never modify or degrade the source assets. The 52 ARKit face controls, shape keys and bone drivers keep working because the toon look only changes shading, lines and post-processing.

## 2.2 Why a toon look is easier and harder
Easier: faces forgive simplification; dark, shape-driven lighting hides model imperfection; painterly filters mask texture noise. Harder: **temporal stability**. Painterly filters and lines must not flicker, swim or crawl from frame to frame; this is the number-one failure mode and the first thing a viewer notices. Plan the whole stack around it (section 7).

# 3. Non-negotiable rules
Everything in Prompt A section 3 applies. Plus:
- **No paid tools, no AI image/video APIs, no accounts.** Everything is Blender shaders, compositor nodes, Freestyle/Line Art and ffmpeg.
- **Do not alter source assets.** The toon look is a render-time material override and a post stack. Source blends stay as built.
- **Deterministic and flicker-free.** Same inputs give identical frames. No per-frame random seeds in textures; noise and brush textures are anchored to object or world space, or to a fixed screen texture that is *intentionally* static (like paper grain) and declared as such.
- **Backwards compatible:** `look` default stays `classic`; Painted Toon is `look: "toon"` plus `variant`. All 71+ tests keep passing.

# 4. Machine and budgets
RTX 4060 Laptop (8 GB), Blender 4.5.15 (also keep 5.x working). Painted Toon should be **much faster than Cinema Real** because it needs no Cycles: EEVEE plus compositor.
- Preview still: <= 4 s. Standard 20 s reel (600 frames at 1080x1920): <= 40 minutes. High: <= 90 minutes (more samples, higher-res line passes, heavier filters).
- Painterly compositor nodes (Kuwahara, filters) run on the GPU in Blender 4.2+; measure and prefer GPU-friendly settings. Keep VRAM < 6 GB.

# 5. Art direction bible (the look)

## 5.1 The toon image in one paragraph
Characters read as **simple, confident shapes**. Light is a **designed shadow shape**, not physics: one hard-edged terminator with a soft secondary transition, a **colour shadow** (cool, saturated, never grey), a **warm rim** where the story light kisses the edge, and a few deliberate highlights. Skin is a handful of tones with painterly variation, not pores. Eyes are **big, clear, glossy** with obvious highlights. Lines are **thin, slightly varying**, concentrated on silhouettes, folds and the face's key creases, fading at lit edges. Backgrounds are **painted**: simplified planes, rich palettes, atmospheric perspective, soft edges, a few crisp focal details, subtle paper/canvas texture over everything.

## 5.2 Colour and light rules (the colour script)
- **Palette per scene** of 5 to 8 hues: one dominant, one accent, a shadow family, a highlight family, and skin. Define it as data (`palette` in the set preset) and generate shader ramps from it so the look is consistent across cuts.
- **Colour shadows:** shadow colour = lit colour shifted toward the scene's shadow hue (e.g. lit warm orange skin becomes plum or teal-blue in shadow), saturation preserved. Never darken by multiplying toward black.
- **Dark and moody is welcome** (owner preference) but keep **readable value structure**: three values (light, mid, dark) clearly separated, the face always in the mid-to-light range on the shadow side lifted by 10 to 15%.
- **Warm key / cool shadow** is the default; invert for night (cool key, warm practicals).
- **Rim lights as shapes:** thin bright contour on the edge facing the light (use a fresnel/layer-weight driven ramp) in a hue brighter than the key.
- **Atmosphere as colour:** distant objects shift toward the scene's haze hue and lose contrast (use Mist pass with a ramp).
- **Light bleed and glow** around lamps and screens as soft painted halos (bloom with a wide, soft kernel and a warm tint), kept clear of faces.

## 5.3 Line language
- Line weight: 1.0 to 2.2 px at 1080 width for silhouettes, 0.6 to 1.2 px for interior creases and facial lines; thicker at the shadow side, thinner or broken at the lit side.
- Line colour: **never pure black**; use the darkest value of the local colour (dark brown on skin, deep blue on blue cloth, dark plum on hair). Provide `line_color_mode`: `local_dark` (default) or `ink_black`.
- Lines taper at ends; slight wobble amplitude 0.2 px, **frozen per object** (not per frame) to avoid boiling, unless "boil" is chosen (see 6.6).
- No lines on tiny details that clutter; fade lines by camera distance.

## 5.4 Texture language
Visible but gentle brush/paper character: a **canvas or paper grain** overlay (static, screen-space on purpose, 3 to 6% strength), **brush-stroke modulation** inside colour fills (object-space noise stretched along form, 5 to 12%), and **edge variation** where colour shapes meet (slightly irregular, like gouache). No photographic noise.

## 5.5 Faces in toon
Simplify the face in shading, not in geometry: soft, large skin tone patches, defined eye shapes, strong brow shapes, a clear mouth shape, blush on cheeks, and expressive highlights. Eye whites warm off-white, iris saturated with a lighter lower edge, **two highlights per eye** (one big, one small) fixed in screen space relative to the face (so they don't slide). Teeth as flat off-white with one shade step; tongue as one shade step; mouth interior a deep saturated colour (not black).

# 6. PHASE T0: setup, references, bake-off harness (small)

T0.1 Ask the owner to place 8 to 15 reference frames in `references/style/painted-toon/` grouped by variant folder (`ink_cel/`, `gouache/`, `pixar_painted/`, `flat_vector/`). If empty, **stop and ask**. Build `docs/production/painted-toon/refboard.png`.
T0.2 Add `docs/production/painted-toon/RUBRIC.md` (section 14).
T0.3 Build **`blender/looks/toon/__init__.py`** and the registry entry (`looks.get("toon")`), with `variant` presets (`ink_cel`, `gouache`, `pixar_painted`, `flat_vector`). Add the engine registry entry (or keep it as a look of the `blender3d` engine, see T0.4).
T0.4 **Decision (document it in the ledger):** keep a single engine (`blender3d`) with `look: "classic"|"cinema"|"toon"`, **or** register a second engine id `blender-toon` that wraps `blender3d`. Recommended: **second engine id** so the editor's style picker, thumbnails and cost labels stay clean and a style has its own capability record; the module reuses `blender3d.render()` with `plan["look"] = "toon"`. Implement it as `reelforge/engines/blender_toon.py` (about 40 lines).
T0.5 Build the **bake-off harness** `blender/toon/bakeoff.py` that renders the same frame (Mina close-up, Matt medium, one wide of `gaming_den`) with N toon technique combinations and produces a contact sheet. Used in T1 and T2 to choose techniques by evidence.
Gate T0: reference board and rubric approved.

# 7. PHASE T1: the toon shading stack

## 7.1 Material override system (`blender/looks/toon/materials.py`)
At render time (inside `render_plan.py`, before rendering), replace every material on every mesh with a **toon material built from the original**: read the original Principled BSDF's base colour (texture or value), alpha, emission and normal; build a new node tree; keep the original materials stored so the override is reversible; skip meshes tagged `toon_keep` (emissive screens, neon tubes keep their emission).
Categories (detected from the object name or the `face_part` / material name; keep the mapping table in `imported.py`-style data so new assets can opt in):
`skin`, `hair`, `eye`, `teeth_mouth`, `cloth`, `leather_hard` (hard glossy), `metal_glass` (simplified spec), `emissive`, `environment_diffuse`, `foliage`.

## 7.2 The toon shader core (one reusable node group `ToonShade`)
Inputs: base colour (texture-based), light mask, shadow colour, highlight colour, steps (2 to 4), step softness (0.01 to 0.25), rim strength, spec strength/size, ambient colour, texture scale, brush strength.
Approach (check what works on Blender 4.5 EEVEE and 5.x; **verify `Shader to RGB` availability and behaviour first**, since EEVEE Next changed it; if it misbehaves, compute lighting yourself):
- **Lighting term:** a Diffuse BSDF into **Shader to RGB** gives per-pixel light intensity from all lights (including practicals and the mood rig). Feed it through a **Color Ramp with `CONSTANT` or small-softness `LINEAR` interpolation** to create 2 to 4 tone steps. Multiply stepped value by (or lookup) a **palette ramp** that maps shade levels to colours (lit colour, mid, shadow colour) so shadows get *colour*, not just darkness.
- **Fallback if Shader to RGB is unavailable or unstable:** drive the ramp from a **custom light model** using Light Path, the face normal and the key light direction (a single-light N·L) plus an ambient term. Document the loss (no practical light colours) and prefer a hybrid.
- **Shadow shapes cleanly:** enable soft shadows with a small light radius (hard edges), raise shadow resolution, and bias to avoid acne. Add a **shadow tint** by multiplying the shadow ramp colour.
- **Rim:** Layer Weight (fresnel) through a narrow ramp, tinted by the scene's rim colour, multiplied by the facing-away-from-camera test and the light direction so it appears only on the lit side.
- **Specular accent:** a hard-edged highlight blob via a glossy BSDF through a constant ramp: size and strength per category (hair gets a banded highlight; skin a tiny one on nose and lips; eyes the fixed highlights).
- **Texture handling:** sample the original albedo, then **posterise and smooth** it gently (Colour Ramp or Math, not a hard threshold) and apply a slight saturation boost (1.05 to 1.15) and a hue shift toward the palette. Skin textures lose pores and fine noise: blur the sampled texture via mip bias or a pre-blurred copy (generate a 1/4-res blurred copy per texture at override time; do **not** modify source images).
- **Brush modulation:** multiply the lit and shadow colour by a low-contrast **object-space** noise stretched along the object's form (use `Texture Coordinate: Object` + Noise with scale 30 to 80 and anisotropic mapping), strength 5 to 12%.

## 7.3 Per-category recipes
- **Skin:** 3 steps (light, mid, shadow); shadow hue shifted toward warm plum or cool blue per variant; large smooth blush patch with a soft edge on cheeks and nose (a mask from the UV or from a vertex group; for imported meshes without one, use a procedural gradient anchored to `FaceAnchor`); a soft **subsurface fake** (a warmer band along the terminator: extra red at the shadow edge) which sells skin without real SSS.
- **Hair:** 3 steps, **banded highlights** (hard bright band along the strand direction), colour variation by clump (per-object-index noise), dark but saturated shadow tone (never black), a thin rim. Alpha-cards keep their alpha; set `use_transparent_shadow` so hair doesn't cast solid shadows; outline only the outer silhouette.
- **Eyes:** unlit-ish: emissive-like base so they stay bright in dark scenes (0.15 to 0.3 emission), big fixed highlights (a white blob and a small second one) in screen space relative to the eye, limbal ring, saturated iris with a lighter lower rim, soft eyelid shadow on the top of the eye.
- **Teeth/mouth:** flat off-white with one shadow step; tongue one step; cavity deep saturated red-brown, never black.
- **Cloth:** 2 to 3 steps, fabric texture is kept as a **low-frequency** pattern (denim twill becomes soft, large); fold shading comes from the geometry normals, with an optional **wrinkle line** pass (see lines).
- **Hard/leather/metal/glass:** 2 steps and a bright rim highlight, glass transparent with a tinted soft reflection shape.
- **Environment:** walls and floors are painted planes: 3 steps, brush modulation 10 to 20%, a large-scale colour gradient toward the haze hue with distance, **edge darkening** (curvature/AO-based) in corners, props with simple dark outlines.
- **Emissive** (monitors, neon, lamps): keep emission; add a soft wide **glow halo** in the compositor and a tinted **light spill** onto nearby surfaces through real lights (the practical lights stay in the scene).

## 7.4 Lighting for toon (build once in `blender/looks/toon/lighting.py`)
- Keep the rig (`Key`, `Rim`, `Fill`, `Glow`) and the practicals. The toon look **re-aims** them for shape clarity: key from 35 to 55 degrees to one side and above (a clear terminator across the face), fill reduced (so shadows hold colour), rim stronger (+30%).
- **Shadow shape control:** per shot a small helper nudges the key azimuth so the terminator falls along the nose and cheek (a "triangle of light" on the shadow-side cheek is a classic toon/Rembrandt cue); expose `light_angle` and `shadow_hardness`.
- **Dark scenes:** lower the key energy and let practicals and rims carry the shapes; preserve a lifted shadow tone (value floor 0.12 on faces).
- **Colour shadows:** a global **Colour Balance in the compositor** pushes shadows toward the shadow hue and highlights toward the light hue per palette.

## 7.5 Evidence for T1
For Mina, Matt and Freya: close-up, medium and one wide, in all four variants, **side by side** with the reference frames; plus a **step-count/softness matrix** (2/3/4 steps x 0.02/0.08/0.2 softness) on Mina. Gate T1: the owner chooses the primary variant's settings.

# 8. PHASE T2: lines (outlines and creases)

## 8.1 Choose by evidence (use the bake-off)
Candidates, evaluated on silhouette quality, weight control, flicker and render time:
- **A. Inverted hull** (a back-face-culled, slightly scaled/pushed-out copy with an emission-colour material, thickness from a vertex group or a distance ramp). Robust and flicker-free; weight control by vertex groups; weak for interior creases.
- **B. Freestyle** (Blender's line renderer): good silhouette/crease lines with thickness modifiers; works in EEVEE and Cycles; can flicker on noisy geometry; slower.
- **C. Grease Pencil Line Art modifier** (4.3+/5.x, GPv3): flexible, can be baked; verify it works headless and with armature deformation and shape keys.
- **D. Screen-space edge detection in the compositor** (Normal/Depth/Object Index passes through Sobel/Laplace and filters): cheap and stable, but resolution-dependent and lower quality; good for interior lines and for **cheap hybrids**.
Recommended hybrid: **A for silhouettes** (thick, tapered, colour from the local dark) + **D or C for interior creases** (nose, lip line, eyelid fold, cloth folds, hair clumps). Document the choice.

## 8.2 Specification
- **Silhouette lines:** thickness 1.2 to 2.2 px at 1080 width; vary by a ramp so the line is thicker where the shape faces away from the light (the shadow side) and thin to nothing where the rim light lights the edge; taper at silhouette ends.
- **Interior lines:** face: upper eyelid fold, lower lid line, nose side, lip line, nasolabial hint (very thin), brow edge; body: clothing fold lines and seams, hand knuckles, collars; hair: only major clump edges.
- **Line colour:** local dark (default). For the inverted hull, sample the object's **base colour at the vertex, darkened and hue-shifted** to the shadow hue (bake into a vertex colour attribute at override time).
- **Lines follow deformation:** inverted hull on skinned meshes must deform with the armature and shape keys; verify blink, mouth shapes and head turns don't tear or flicker lines.
- **Distance fade:** lines thin with camera distance and vanish on tiny details.
- **Wobble:** deterministic, per-object, low amplitude. Optional **boil** mode for the "hand-drawn" feel: change wobble every 2 frames on twos (see timing), off by default.

## 8.3 Evidence and gate
Line bake-off sheet (A, B, C, D, hybrid) at 100% crop, plus a **flicker test**: a 2-second head-turn clip per technique and the `qa/flicker_check.py` metric. Gate T2: the owner picks the line technique.

# 9. PHASE T3: the painterly compositor stack

## 9.1 Node graph (build in `blender/looks/toon/compositor.py`; reusable and parameterised by variant)
Inputs: Combined (toon-shaded), Object Index, Normal, Depth/Mist, optional line pass, emissive pass.
1. **Edge-preserving smoothing:** the **Kuwahara node** (anisotropic, Blender 4.1+; GPU) with size 2 to 5 px (at 1080 wide) and sharpness 0.5 to 1.0 to create the painted look while keeping edges. Fall back to a bilateral-like blur (Denoise node on albedo and normal, or a filtered mix) if Kuwahara is missing. Mask it so **eyes, mouth, brows and the line pass stay sharp** (use Object Index masks and the `face_part` tags).
2. **Colour simplification:** gentle posterise via a Colour Ramp on luminance (keeping chroma), then restore chroma with the original hue to avoid banding.
3. **Brush texture overlay:** a stroke-direction texture (from the normal pass or object-space flow) multiplied at 4 to 9% over mid-tones; **paper/canvas grain** overlay (a static, screen-space image generated at build time, tileable, 2048 px, 3 to 6%).
4. **Edge variation:** use a small, static **displace** (0.5 to 1.2 px) driven by a fixed noise so colour-shape edges look painted. Keep the displace field static to avoid swimming.
5. **Lines composite:** multiply the line pass over the image, line colour from the pass (local dark), with a slight blur (0.3 px) to remove aliasing, plus an optional paper-fibre erosion mask for hand-inked edges.
6. **Glow and light bleed:** a wide, soft bloom on the emissive pass only (never on skin), tinted by the palette's highlight hue.
7. **Atmosphere:** blend toward the haze hue by the Mist pass; add a subtle vertical gradient to ground the scene.
8. **Grade:** Colour Balance (shadow hue, highlight hue), saturation 1.05 to 1.2, a gentle S-curve, a soft vignette (6 to 12%), and **no film grain** (this is a painted look); optional **halftone** or **risograph misregistration** (0.5 px RGB offset on the lines) as a style option for the Spider-Verse feel.
9. **Dithering and banding control:** dark gradients dithered before the 8-bit encode (see Prompt A section 7.5).
Run the compositor in Blender (`sc.use_nodes = True`, `render.use_compositing = True`) so the frames written are final. Keep a `compositor_off` debug flag.

## 9.2 Variant parameters (data, not code branches)
| Parameter | ink_cel | gouache | pixar_painted | flat_vector |
|---|---|---|---|---|
| Shading steps | 3 | 2 | 4 (soft) | 2 |
| Step softness | 0.06 | 0.03 | 0.22 | 0.02 |
| Lines | hull + creases, 1.6 px | thin broken lines, 0.9 px | almost none (rim only) | none or 0.6 px local dark |
| Kuwahara size | 3 | 5 | 2 | 4 |
| Brush overlay | 8% | 12% | 4% | 10% |
| Paper grain | 4% | 6% | 2% | 5% |
| Saturation | 1.10 | 1.05 | 1.20 | 0.92 |
| Shadow colour | cool plum/blue | warm brown | rosy magenta | muted blue-grey |
| Glow | medium | low | high (warm) | low |
| DOF | moderate | strong painted blur | strong soft bokeh | minimal |

# 10. PHASE T4: backgrounds (painted environments)

- **Per-room painted pass** (`blender/looks/toon/sets.py`): simplify materials with the environment category recipe; set a **palette** per room and preset in data; light the room with 3 to 5 designed lights (a key window or lamp, 1 to 2 coloured practicals, 1 fill, 1 rim) so the shadow shapes are clear; add **atmospheric depth** (mist ramp), **contact shadows** under objects (AO shaded as a soft dark shape), and **edge darkening** in corners; **blurred painted bokeh** for out-of-focus areas (a larger-aperture DOF in toon, f/1.8 to f/2.8, with polygonal highlights softened) so the backgrounds read as painted washes behind sharp characters.
- **Prop simplification:** hide or flatten micro-clutter (cables, tiny text, fine grids) with a distance-based visibility rule or a material that flattens texture detail; keep story props crisp.
- **Window/outside views:** a painted gradient sky or a flat-shaded skyline silhouette plate (build procedurally with 3 or 4 layered shapes with atmospheric tint), warm sunset, blue night, rainy blur.
- **Reference-driven room styling:** for each of the owner's references, a room preset recreates its palette and light logic (for example "Train compartment" daylight patches through windows with strong cool/warm patches; "Office late afternoon" warm key through blinds with strong shadow shapes). Add 2 to 3 presets per room: dark mood first.
- **Painted texture overlay** on environment surfaces: object-space brush noise at 10 to 20%, edges slightly irregular.
- **Motion streaks** (train-window style): optional **speed-line blur** layer driven by an animated horizontal gradient on exterior planes (set-specific).
Evidence: each room (all 3 imported plus 3 procedural sets chosen with the owner) in wide, medium and close-up, in at least the primary variant. Gate T4: owner approval room by room.

# 11. PHASE T5: animation timing and cinematography for toon (animator's pass)

Toon looks wrong if it moves like realistic CG. Apply 2D-animation sensibilities.

## 11.1 Timing
- **On twos for characters, on ones for the camera** (the Spider-Verse trick): evaluate character animation at 15 fps (hold each pose for 2 frames) while the camera moves smoothly at 30 fps. Implement as a per-look option `character_hold: 2` by holding the face and body keys on even frames only (constant interpolation in the key tracks) in `render_plan.py`'s `key_track`. Keep lips in sync by keying visemes on the exact frame; let the owner pick `1` (smooth) or `2` (stylised).
- **Holds and timing beats:** hold the **key poses** of a performance for 4 to 8 frames (the last word of a punchline, a reaction). Snap in with 1 to 2 frame overshoots on strong emotions (a hint of **smear** via slight stretch of the head on a fast turn, deformation limited to 3 to 6%; optional).
- **Eyes:** quick, graphic blinks (4 to 6 frames), eyes **hold on a key look** for 6+ frames, and a big highlight snap on an emotional beat.
- **Anticipation and overshoot** more pronounced than in Cinema Real (head dip before a nod, small squash on a laugh: scale the head by 1.02 vertically/0.98 horizontally for 3 frames).
- **Secondary motion** (hair, clothing) on twos too, with a delay.

## 11.2 Camera and cuts
Reuse Prompt A's camera rig. Toon-specific tweaks: more **static or drifting** shots, **slower** moves, **dramatic angle shots** (low angle, slight Dutch tilt 2 to 4 degrees on tension), strong **foreground silhouettes** (a plant or a lamp as a dark shape on the frame edge), **whip-pans with painted smear** (a horizontal Kuwahara-with-motion-blur composite), **close-up inserts** (hands on keyboard, a sticky note, a cup), and **match cuts**. Lens language stays film-like; DOF is more painterly.

## 11.3 Evidence
A 12 to 15 s dialogue clip in the primary variant, watched at full speed and 25%, scored for flicker, line stability, timing, eye life, lip-sync and camera.

# 12. PHASE T6: finish, export and sound for toon
- `reelforge/finish.py` gets a `toon` finishing path: **no halation, no film grain**; soft vignette; paper-grain overlay if not done in Blender; a gentle sharpening (unsharp 0.3 px) on lines; the same **loudness**, **ambience** and **caption** logic as Cinema Real. Provide a **caption style** option matching the look (rounded hand-lettered font with a coloured outline: pick an open-licence font already in the project or a Google Fonts open font; ask if a download is needed).
- Export presets as in Prompt A section 7.5. Check that Instagram's re-encode does not band the flat colour areas: use a **dithered** final encode and verify on a flat-gradient test.
- Add `reelforge/engines/blender_toon.py` capabilities: `cost: "free"`, `runs: "local"`, `ratios`, `lipsync: "pipeline-visemes"`, and expose `variants` for the editor.

# 13. PHASE T7: editor integration (product designer)

Use the existing editor (`editor/`, Vite + React + TS + Zustand, tokens in `src/styles/tokens.css`). Dark, minimal, no AI-slop. Each control has a default, a tooltip and empty/loading/error states.

## 13.1 Style picker
Add the **Painted Toon** card beside **Cinema Real** and **Classic 3D**: a real rendered thumbnail (cached), a one-line description, badges `Free` and `Local`, and an estimated render time per 10 s (from `reelforge bench --style blender-toon`). Selecting it reveals the **Variant** row: four tiles (Ink & Cel, Gouache, Pixar Painted, Flat Vector) each with a thumbnail rendered from the user's current project frame.

## 13.2 Look panel (Painted Toon)
Controls (saved into `performance.json` under `look_params`, all optional): **Variant**; **Quality** (Preview / Standard / High); **Line weight** (0 to 2x) and **Line colour** (Local dark / Ink black); **Shading steps** (2 / 3 / 4); **Shadow hardness**; **Shadow hue** swatch; **Light angle** (rotates the key's side); **Painterly** (Kuwahara strength); **Brush texture**; **Paper grain**; **Glow**; **Saturation**; **Character timing** (Smooth 30 fps / Stylised on twos); **Smear frames** toggle; **Boil lines** toggle. A **Compare** toggle flips between Cinema Real and Painted Toon on the selected shot.

## 13.3 Shot and camera controls
Same camera panel as Prompt A section 14.3, with toon-specific presets (**Dutch tilt**, **Silhouette foreground**, **Whip with smear**), plus the per-shot **variant override** (rare, but useful for a flashback in Gouache inside an Ink & Cel reel).

## 13.4 Palette editor
A small **colour script** panel per scene: shows the 5 to 8 hue swatches, lets the user adjust the dominant, accent and shadow hue with a colour picker, shows a live preview still, and a **Lock palette across scenes** switch. Palettes save into the preset data in `performance.json` (`palette`). Defaults come from the room preset.

## 13.5 Render screen, export, library
As in Prompt A sections 14.5 and 14.6. The Library saves **look presets** (named combinations) for reuse across reels.

## 13.6 Server, schema, tests
- `editor/server/api.ts`: pass `--style blender-toon` and `--variant`, stream progress, and serve thumbnails.
- `reelforge/schema.py`: add `variant`, `look_params`, `palette`, `character_hold`; validate; defaults reproduce current behaviour.
- Tests: `tests/test_toon_schema.py`, `tests/test_toon_palette.py` (palette to ramp mapping, pure python), `tests/test_blender_toon_engine.py` (plan contains `look: "toon"`), `tests/test_engine_registry.py`.
- Verify in the browser pane: the picker, variant tiles, look panel, palette editor and render screen; console clean; screenshots of each screen.

# 14. QA, rubric and review

## 14.1 Rubric (score 1 to 10 against the reference board)
| Criterion | Weight |
|---|---|
| Overall painted/illustrated look and fidelity to the references | 25% |
| Faces: shape clarity, expressiveness, eyes, appeal | 20% |
| Light and colour (shadow shapes, palette discipline, mood, readability) | 15% |
| Line quality (weight, taper, colour, stability) | 10% |
| **Temporal stability** (no flicker, swim, boil unless chosen) | 15% |
| Backgrounds (painted feel, depth, simplification) | 10% |
| Animation timing and camera | 5% |
A phase passes at a weighted score >= 7.5, no criterion below 6, **temporal stability >= 8**.

## 14.2 Automated checks (`qa/`)
`qa/flicker_check.py` (frame-to-frame difference in static regions and on lines), `qa/line_stability_check.py` (line pixel count variance over a still camera and a slow head turn), `qa/palette_check.py` (counts distinct dominant hues per frame vs the palette, flags off-palette colours), `qa/value_check.py` (three-value structure, face value floor), `qa/banding_check.py`, `qa/safe_zone_check.py`, plus unit tests. Run before each gate.

## 14.3 Independent review
After each phase, run a reviewer subagent on a different model: give only the evidence images, the rubric and the references; score blind; compare with your scores; fix the top three defects; log both.

## 14.4 Illustrator's and animator's checklist (every video, full speed and 25%)
Do the shapes read at thumbnail size? Is the light a designed shape? Do shadows carry colour? Are lines clean, varied and stable? Any edge crawl, texture swim or flicker? Do the eyes sparkle? Do holds and timing feel intentional? Is the palette consistent across cuts? Do backgrounds look painted rather than blurred 3D? Would I post this?

# 15. Deliverables, ledger, stop conditions
- Order: T0 (refs, rubric, harness) > T1 (shading) > T2 (lines) > T3 (compositor) > T4 (backgrounds) > T5 (timing/camera) > T6 (finish/export) > T7 (editor). T1 to T3 together produce the first complete frame, so do them back to back and **show the owner a first full frame as early as possible**.
- Ledger at `docs/production/painted-toon/PROGRESS.md`; small commits on `feat/painted-toon`; credits for every third-party asset in `ASSETS_CREDITS.md` (fonts, textures).
- Stop and ask the owner when: a download exceeds 2 GB or needs an install; the reference folders are empty; the line technique ties; a licence is unclear; a phase fails its gate twice; Kuwahara or Shader-to-RGB behaves differently between Blender 4.5 and 5.x in a way that forces a different design.
- End with `docs/production/painted-toon/FINAL_REPORT.md`: what changed, evidence frames for every variant, the benchmark table, scores, known gaps (especially vs the hand-painted train and kiss frames) and a one-command rebuild.

# Appendix: default numbers (starting points)
- Shading steps 3, softness 0.06, key 35 to 55 degrees to the side, fill -40% vs Cinema, rim +30%, shadow value floor 0.12 on faces.
- Lines: silhouette 1.2 to 2.2 px, creases 0.6 to 1.2 px at 1080 width, local-dark colour, wobble 0.2 px frozen.
- Kuwahara 2 to 5 px, sharpness 0.5 to 1.0; brush overlay 4 to 12%; paper grain 2 to 6%; displace 0.5 to 1.2 px static; vignette 6 to 12%; saturation 0.92 to 1.2.
- Timing: characters on twos (15 fps holds), camera on ones (30 fps); blink 4 to 6 frames; key-pose holds 4 to 8 frames; squash 2% for 3 frames.
- Budgets: preview still <= 4 s, standard 20 s reel <= 40 min, high <= 90 min, VRAM < 6 GB.
