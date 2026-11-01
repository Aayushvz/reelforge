# Cast, sets and editor: production brief (2026-11-01)

**Status:** requirements from the owner. Each section becomes its own brainstorm → spec → plan → build sub-project, run by a fresh Claude session. Read `docs/HANDOFF.md` and `docs/superpowers/specs/2026-10-31-multi-style-engines.md` first.

---

## 1. Character roster: 7 original characters (4 male, 3 female)

### 1.1 Target look ("stylized-sculpt")
The owner's references (save copies into `references/characters/style/`) share these traits:
- **Stylized caricature proportions:** long necks, strong jaw or cheek planes, slightly oversized heads, expressive brows.
- **Sculpted "clay or vinyl-toy" hair:** big readable curl and swoop shapes, with chunky strands rather than fine strands. Some refs are **faceted, low-poly-ish** (hard-planar hair and hands); keep that as a variant.
- **Soft skin:** subtle subsurface scattering, painted pores or stubble, warm-cool skin variation.
- **Clean studio key light with a rim:** matte, slightly glossy materials; graphic and readable silhouettes.
- **Expression range shown in the refs:** laughing, smug or one-brow-raise, surprised or shocked. The face rig must hit these convincingly.

**Important:** some references depict real actors and TV characters. Use them as **style references only**. Every character we ship must be **original**, not a recognizable likeness of a real person or an existing IP character.

### 1.2 Roster (names and personalities are proposals; refine in brainstorm)
| # | Name | Vibe | Signature look | Gen-Z wardrobe (each needs at least 3 outfits) |
|---|---|---|---|---|
| M1 | **Kai** | chill creative, deadpan | tight black curls, thin chain, earring | boxy black shirt and chain · oversized hoodie and cargos · knit vest over a tee |
| M2 | **Rey** | loud and funny, big laugh | curly hair, full beard, glasses | grey sweatsuit and chunky chain · track jacket and joggers · puffer vest |
| M3 | **Dev** | confident coder, smirk | fade with swoop top, stubble, watch | camel tee and black jeans · techwear jacket · varsity jacket |
| M4 | **Mo** | anxious overthinker, comedic | messy hair, round glasses, slight slouch | baggy cardigan and wide pants · graphic tee and beanie · flannel over a hoodie |
| F1 | **Aria** | witty lead, sarcastic | long dark hair, hoop earrings | cropped knit and wide-leg jeans · oversized blazer and mini skirt · baby tee and cargos |
| F2 | **Zoe** | bubbly, dramatic reactions | high ponytail, freckles, blush | sporty zip-up and leggings · Y2K butterfly top · puffer jacket |
| F3 | **Noor** | calm, stylish, dry humour | sleek bob or braids, gold jewellery | trench coat and turtleneck · cargo set · oversized sweater and beret |

The **outfit system** has slots: `top`, `outer`, `bottom`, `shoes`, `accessories` (chains, earrings, glasses, caps, beanies, watches). Hair is swappable per character. Colour and material parameters let the editor recolour any item. The target is about **25+ wardrobe items** shared across the cast where body types allow.

### 1.3 Quality bar and acceptance
For each character:
- turnaround (front, ¾, side), and a full-body outfit sheet for each outfit;
- an **expression sheet**: neutral, laugh, smug, surprised, sad, angry, blink, talk "A/O/M";
- a 5-second talking test clip, using the pipeline's lip sync.

These are compared side by side with `references/characters/style/`, with an honest verdict.

### 1.4 Technical route (Style 1, Blender; free)
Image or prompt → open-source image-to-3D (Hunyuan3D-2 or similar) for a base mesh, **or** sculpt-by-script from a shared stylized base body when generation quality is poor. Then:
- add real eyes, eyelids, mouth cavity, teeth and tongue;
- generate the 52 ARKit face shapes and drive them from `FaceCtrl`;
- auto-rig the body (Rigify or UniRig);
- expose `FaceAnchor` and `EyeFocus` empties (see `m1-followups.md`).

For Style 2 (`cinematic-ai`), the same roster becomes **character sheets** that keep AI keyframes consistent.

---

## 2. Environment library: 10 high-quality sets

Each set ships with **3 lighting presets**, so at least 30 looks in all. Each set also keeps the environment contract:
- lights `Key`, `Rim`, `Fill`, `Glow`;
- materials `ScreenMat` and `HoloMat`, where relevant;
- marks `Mark_A` and `Mark_B`;
- a per-set LUT, ambience audio and camera anchors for wide, medium and close-up shots.

| # | Set | Lighting presets |
|---|---|---|
| 1 | Night-city desk (rebuild of the M1 set) | blue night · neon pink · rainy |
| 2 | Cozy bedroom / gaming room | warm lamp · RGB LEDs · morning sun |
| 3 | Rooftop with skyline | golden hour · blue hour · night lights |
| 4 | Café by the window | rainy day · sunny afternoon · evening fairy lights |
| 5 | Lantern-lit old-town street (ink.industries mood) | sunset · lantern night · foggy dawn |
| 6 | Subway / metro platform | fluorescent · late-night empty · rush-hour warm |
| 7 | College campus / classroom | daylight · overcast · after-hours |
| 8 | Modern office / startup | daylight · late-night crunch · presentation spotlight |
| 9 | Convenience store / night mart | fluorescent night · neon sign · rain outside |
| 10 | Beach boardwalk / pier | sunset · pastel morning · night carnival lights |

**Technical route (Style 1):** depth-displaced 2.5D backdrop from a reference or generated image (Depth Anything V2) **plus** real 3D foreground props and lights, so the moods and shadows work. Fix the M1 gaps: wide-shot bokeh, a visible rim light, subtle haze, sculpted face light.

**Acceptance:** for each set, wide, medium and close-up stills in each lighting preset, with the cast present. They must read as deep, cinematic and high-end, never flat.

---

## 3. Editor UI: our own product, dark and minimal

### 3.1 Reference products (study them, don't copy them)
- **Higgsfield:** the polished, dark, cinematic creative-tool feel; the preset and style cards with motion previews; generous imagery.
- **InVideo:** a script-first flow, scene-by-scene editing, a simple timeline for non-editors.

Build **our own** design language. **Not "AI slop"**, which here means:
- no purple-blue gradients;
- no glassmorphism everywhere;
- no emoji icons;
- no generic hero sections;
- no random sparkles.

Aim for quiet, precise, professional, in the spirit of Linear, Figma and DaVinci Resolve.

### 3.2 Design system
- **Theme:** dark only to start.
  - Neutrals are near-black greys: about `#0B0B0C` for the background, then the panels, then elevated surfaces.
  - One accent colour, used sparingly (proposal: a warm amber that echoes the "glow" look). Semantic colours only for status.
- **Type:** one clean sans (Inter or Geist) with a tight scale, plus tabular numbers for timecodes.
- **Layout:** an 8-px grid, 1-px hairline borders, small radii (6–8 px), and no heavy shadows.
- **Icons:** one consistent line icon set (Lucide).
- **Motion:** subtle 120–200 ms transitions, and nothing bouncy.
- **Thumbnails:** real renders of our characters and sets. The UI is a frame for the imagery.

### 3.3 Screens
1. **Home / projects:** recent reels as a grid of video thumbnails; "New reel" opens a short flow: style, then script, then cast, then set.
2. **Style picker:** cards for each engine (`blender3d`, `cinematic-ai`, future ones), showing a looping sample, cost (free or paid) and render time.
3. **Script:** a clean writing view; each line has a speaker chip, an emotion and intensity control, a mood and a punchline toggle. Optionally, "Direct with Claude" runs the performance pass.
4. **Cast:** character cards → a wardrobe drawer with outfit slots, swatches and live 3D turntable thumbnails.
5. **Set:** environment cards → lighting preset chips with instant preview stills.
6. **Voice:** per-line voice takes, upload or import, waveform, re-align, play.
7. **Editor (the main workspace):**
   - centre: preview player at 9:16, 16:9 or other ratio;
   - left: a scenes/shots list in the InVideo style, with thumbnails and per-shot regenerate;
   - right: an inspector for the selected shot (camera kind and lens, mood, caption style, expression overrides);
   - bottom: a multi-track timeline (dialogue waveform, shots, moods, captions, music and SFX) with trim, split, drag and zoom.

   Keyboard-first: J/K/L, space, S to split, ⌘Z.
8. **Approve:** a grid of per-shot stills; approve or regenerate each.
9. **Render / export:** a queue with progress and an estimated finish time; choice of ratios, quality and caption burn-in; download and share.

### 3.4 Tech
- A local web app launched by `reelforge editor`.
- Frontend: Vite + React + TypeScript. Styling: Tailwind or CSS variables wired to design tokens. Timeline: a custom canvas or DOM implementation, kept performant.
- A Three.js viewport for the `blender3d` preview (glTF exports).
- The backend wraps the `reelforge` CLI and streams progress; state lives in the project folder.

### 3.5 Acceptance
- Every screen is built, then screenshotted in a real browser and checked against this brief, with no slop patterns present.
- One reel is made end to end, using only the UI.

---

## 4. Build order (supersedes earlier orders)
0. Engine refactor (`blender3d` behind the engine contract).
1. **Characters:** base body, face and rig pipeline, then the 7-character roster plus the wardrobe system.
2. **Environments:** the 10 sets × 3 lighting presets.
3. **Editor UI:** design system first, then the screens.
4. Style 2 `cinematic-ai` engine (it reuses the roster as character sheets).
5. Styles 3–6, from future owner references.

Each step uses the superpowers workflow (brainstorm → spec → plan → subagent build → reviews), runs on its own branch, and ends with an honest REVIEW.md that includes renders.
