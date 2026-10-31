# Animated Reel Generator — Design Spec

**Date:** 2026-10-31
**Status:** Draft, awaiting user review

## 1. Goal

Upload a script, get back a cinematic, lip-synced, emotionally acted 3D animated video. The look is premium stylized 3D characters in refined, moody environments. The videos should be relatable and built for views: Instagram Reels first, other platforms second.

Success criteria:
- **Fully automated.** The only required input is `script.txt`. Everything else is optional overrides.
- **Lip sync is frame-accurate**, and emotion is clearly visible in the voice, face, body, lighting and edit.
- **Characters and sets stay identical across every video**, so they work as a recurring series.
- **Low token use.** One Claude call per video, about 1–2k tokens. Everything else runs locally and deterministically.
- **The output looks cinematic:** lens language, lighting, color grade, sound design.

Non-goals for version 1: cloud hosting, multiple users, hand-keyed animation tools, more than 2 speaking characters per video.

## 2. Key decisions

| Decision | Choice | Why |
|---|---|---|
| Render engine | Blender, headless (Cycles for close-ups, Eevee for wides and inserts) | Real lighting, depth of field and glare; consistency; ~$0 per video |
| Character style | Stylized-premium (toon proportions, realistic shading) | Most appealing, rigs well, avoids the uncanny valley |
| Characters | One modular base rig with **ARKit 52 blendshapes** plus swappable parts | Drives Audio2Face; reusable outfits |
| Voice | ElevenLabs v3 with emotion tags, timestamped output | Most expressive control; exact timings |
| Facial animation | NVIDIA Audio2Face-3D (local), timestamp mouth shapes as fallback | Emotion-aware face from the audio |
| Body animation | One-time mocap gesture library (about 30 clips), procedurally blended | Human motion, not canned |
| Editor | Local web app (localhost) plus a Node job server | Free GPU, nice UI |
| Aspect ratios | 9:16 default; 16:9, 3:4, 1:1 available | Multi-platform |
| Rejected | Three.js/browser rendering (quality ceiling); AI video such as Veo/Omni (drift, cost per clip, low control) | |

Taken from the NMXWZ reference reel: per-beat color moods, story-reactive glowing props, its caption system, and a stills approval gate before the final render.

## 3. Pipeline

```
script.txt (+ optional overrides)
  ① perform   Claude, one call            → performance.json
  ② voice     ElevenLabs v3                → audio/line_XX.mp3 + timestamps
  ③ analyze   Audio2Face, prosody, words   → analysis.json, face/line_XX.json
  ④ direct    deterministic rules          → shots.json
  ⑤ stills    Blender, one frame per shot  → stills/  (approval gate, auto-approve option)
  ⑥ render    Blender, image sequence      → frames/
  ⑦ finish    ffmpeg + caption renderer    → final_<ratio>.mp4
```

Each stage reads only the files from the stage before it, writes its own outputs, and is cached by a hash of its inputs. Re-running a stage redoes only what changed. For example, re-voicing line 4 re-runs ②–⑦ only for the shots that contain line 4.

### ① Perform (the only LLM step)
Input: the script, plus the asset catalog (names only). Output, `performance.json`:
- Per line: speaker, text with ElevenLabs emotion tags, emotion and intensity (0–1), mood (`calm | success | panic | awkward | reveal | sad`), gestures with the word they land on, pause before/after, a camera note, the props or screen content to show.
- Global: environment, outfits, music mood, hook line (for an optional cold open), loop-ending flag.
- Optional `notes`: script feedback (weak hook, slow setup).
- The output is checked against a fixed format. If it doesn't match, it's retried once with the error message, then the run fails with a clear message.

### ② Voice
- One fixed voice ID per character (stored in the character config).
- Uses ElevenLabs' endpoint that returns audio with per-character timestamps. Each line is a separate file, so a single line can be regenerated alone.
- Lines are joined into one dialogue track with the pauses from `performance.json`.

### ③ Analyze
- **Audio2Face-3D**: audio → per-frame values for the ARKit 52 facial controls, including emotion it infers from the voice.
- **Fallback lip sync**: ElevenLabs character timestamps → phonemes → about 12 mouth shapes with blending between sounds, plus jaw opening from loudness.
- **Prosody**: pitch and loudness per word, used to find stressed words.
- Word timings come from the ElevenLabs timestamps. Whisper is used only for uploaded or recorded audio.

### ④ Direct (rule-based, no tokens)
Shot vocabulary: establishing wide (24 mm), over-the-shoulder (35 mm), close-up (85 mm), insert (screen, hands, prop), reaction close-up, rack focus, snap zoom, whip pan, slow motion (0.5×).

Rules:
- Cut every 1.5–3 s, and cut on motion.
- Respect the 180° rule.
- After a high-intensity line, show the listener's reaction.
- A slow push-in on serious beats; a snap zoom on surprise; a held two-shot on awkward beats.
- Hook first: if a cold open is enabled, the hook shot plays first.
- Loop ending: the last shot's framing matches the first.

Framing adapts to the aspect ratio (see §6).

### ⑤–⑥ Animate and render
Animation is built up in layers, per character:
1. **Face:** Audio2Face output (or the fallback), then the emotion intensity from the script scales the expression, then anticipation and overshoot on expression changes, with asymmetric variants.
2. **Life:** blinks (rate depends on emotion), small eye movements, glances at the other character, breathing.
3. **Body:** mocap gesture clips placed on the stressed word, blended over an idle loop, with ±10% random variation in timing and amplitude. Listening characters get reaction clips (nod, eye-roll, side-eye, slump).
4. **Sidekick blob:** squash and stretch, hops, eye-shape emotions.

The look:
- **Mood presets:** key and glow color plus a grade, crossfading over about 10 frames between beats.
  - calm: warm amber key with a cool blue rim
  - success: green
  - panic: red with flicker
  - awkward: desaturated
  - reveal: gold with a bloom spike
  - sad: cool blue, low key
- **Story-reactive props:** glowing holographic screens show textures picked by beat tag (code, check, warning, progress, chat).
- **Lighting and atmosphere:** lights that exist in the scene, volumetric haze.
- **Lens:** depth of field at f/1.8–2.8 with oval bokeh and focus following the speaker; handheld camera drift; motion blur.
- **Shading:** subsurface skin, fuzzy cloth shading, eye catchlights, hair highlights.
- **Color:** AgX color management, plus Blender compositor glare.
- **Rendering:** close-ups in Cycles (GPU, denoised); wides and inserts in Eevee. Output is an EXR/PNG frame sequence, so a crash resumes from the last finished frame.

### ⑦ Finish
- Per-set LUT, halation, vignette, slight chromatic aberration at the edges, fine grain.
- **Captions:**
  - 1–4 words at a time, with the spoken word highlighted.
  - A color per character (main: white with a yellow highlight; sidekick: orange with a white highlight).
  - Pop-in bounce, plus a bigger pop and wobble on the punchline.
  - Very bold font with an outline and shadow.
  - Placed around faces using face positions taken from Blender's cameras, not detected from pixels.
  - Kept inside each platform's safe zone.
- **Audio:**
  - Dialogue with light room reverb, ambience bed, music bed that ducks under dialogue.
  - Foley triggered by the animation (keys, chair, mug, robot blips), whooshes on fast cuts, a stinger on the punchline, silence before it.
  - Loudness normalized to -14 LUFS.
- Export: H.264 + AAC.

## 4. Asset library (built once)

```
assets/
  characters/base.blend        ARKit-52 face, rig, slots: hair, top, outerwear, glasses, accessory
  characters/parts/*.blend      swappable parts; skin tone and eye color as material params
  characters/<name>.json        preset: parts, colors, ElevenLabs voice ID
  companions/blob.blend         sidekick rig
  environments/<set>.blend      night-city desk, rainy café, sunset loft, cozy bedroom
  environments/<set>.json       camera anchors, character marks, LUT, ambience, prop slots
  moods/*.json                  light and grade presets
  gestures/*.fbx                ~30 mocap clips + idle + listening reactions
  props/screens/*.png           holographic screen textures by beat tag
  sfx/, music/, luts/, fonts/
```

Note: the quality of the character's face is the biggest single factor in the result. The plan is to build it procedurally from CC0 bases first. Commissioning a professional stylized head with ARKit blendshapes (~$100–300) is the recommended upgrade.

## 5. Editor (local web app)

The steps are optional; the default is upload and render.
1. **Script:** paste or upload. Run the performance pass and show its annotations, which you can edit inline.
2. **Cast:** character presets plus pickers for outfit, hair, glasses and colors. Overrides lock the performance-pass choices.
3. **Set:** environment and default mood.
4. **Voice:** play each line, regenerate one line, or swap in an uploaded take.
5. **Shots:** a timeline of automatic shots with thumbnails. Change a shot type or lens, or move a cut.
6. **Stills gate:** approve or reject each shot (or turn on auto-approve).
7. **Render:** pick aspect ratios and quality (draft Eevee / final Cycles). Shows progress and an estimated finish time, then download.

Stack: a Vite + React frontend; a Node (Express) job server that runs Python/Blender/ffmpeg steps as background processes and streams their progress to the page.
The project state is the `project/` folder, so there's no database.

## 6. Aspect ratios

| Ratio | Resolution | Notes |
|---|---|---|
| 9:16 (default) | 1080×1920 | Instagram/TikTok/Shorts safe zone: top 220 px, bottom 420 px |
| 16:9 | 1920×1080 | YouTube. Favor two-shots and over-the-shoulder shots; wider lens. |
| 3:4 | 1080×1440 | Instagram feed. |
| 1:1 | 1080×1080 | Feed/LinkedIn. |

- Each ratio is a **separate camera render, not a crop.**
  - The director re-frames each shot for each ratio, using that ratio's composition guides and safe zones.
  - Environments define enough set width for 16:9.
  - Caption layout and safe zones are set per ratio.
- Multi-ratio export re-uses all stages up to ⑤ and renders ⑥–⑦ once per ratio.

## 7. Error handling

| Failure | Behavior |
|---|---|
| Claude output doesn't match the format | Retry once with the error, then stop with a message |
| ElevenLabs error or rate limit | Exponential backoff, 3 tries, then stop. Nothing runs on missing audio. |
| Audio2Face fails on a line | Fall back to timestamp mouth shapes; log a warning in the UI |
| Blender crash | Resume from the last finished frame |
| A missing asset is referenced | Fail at the ① format check, listing the valid names |
| A caption can't avoid a face | Put it in the lower safe zone with a stronger shadow; log a warning |

All errors appear in the editor job log, and the CLI exits with an error code.

## 8. Testing

- **Standard sample:** `samples/look-test.txt`, two lines, about 6 seconds, run as the end-to-end test.
- Each stage has a check that its output files match the expected format.
- **Director:** unit tests on its rules (cut length, 180° rule, reaction after high intensity, cold open, loop).
- **Visual:** reference stills per set and mood, reviewed by eye. Optionally, an image-difference check against approved stills catches look regressions.

## 9. Milestones

1. **Look test (de-risk).** One 6-second shot: base character in the night-city set, one ElevenLabs line, Audio2Face lip sync, one mood change, full finish. The quality bar has to pass before anything else is built.
2. **Command-line pipeline:** ①–⑦ end to end for 9:16, two characters, one set.
3. **Asset expansion:** outfits and parts, 3 more sets, mocap gesture library, mood presets, screen props.
4. **Editor web app.**
5. **Multi-ratio export:** 16:9, 3:4, 1:1.

## 10. Requirements and setup

- Windows 11, RTX 4060 laptop GPU (8 GB). ffmpeg and Node are already installed. To install: Blender 4.x, Python environment, Audio2Face-3D, faster-whisper (only for uploaded audio).
- ElevenLabs API key (paid plan for v3 and voice cloning).
- Anthropic API key for the performance pass.
- Render time estimate: about 1–2 hours per 45-second reel at final quality; about 15–25 minutes as a draft (Eevee only).
