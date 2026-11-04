# Multi-style platform: design addendum (2026-10-31)

**Status:** direction approved by the owner. The detailed spec for each style still needs brainstorming.

## Goal
reelforge becomes a **platform with several animation styles**, eventually 5–6 of them; the owner will add references for more over time. A user picks a style per project. The script, voice, captions, edit and editor stay the same; only the "make the pictures" stage differs.

## Architecture: shared spine plus pluggable style engines
```
script ─► performance pass (Claude) ─► performance.json   (shared, style-agnostic)
        ─► voice (ElevenLabs web/API) + alignment            (shared)
        ─► timeline + shot list + moods                      (shared)
        ─► STYLE ENGINE  ◄── project.style = "<engine id>"   (pluggable)
              produces: one video clip or frame sequence per shot, plus optional per-shot audio
        ─► finish: cut/assemble, captions, sound, grade, -14 LUFS (shared)
        ─► final_<ratio>.mp4
```

**The engine contract** (each engine lives in `reelforge/engines/<id>/`):
- `id`, `name`, `description`, and a thumbnail or sample reel for the editor's style picker.
- `capabilities`: lip-sync source (engine-native or pipeline visemes), max shot length, supported aspect ratios, cost per shot (free or paid), local or cloud.
- `prepare(project) -> assets`: build or select characters and environments for this style, using the style's own asset library.
- `render_shot(shot, context) -> clip path`: one shot. Must be retryable and cached by input hash.
- `preview_shot(shot, context) -> still path`: feeds the editor's approval step.
- The engine registry is `reelforge/engines/__init__.py`. The CLI and editor use `--style <id>` and `project.style`.
- Every engine respects the shared constraints: no account or key handling by Claude, ask before large downloads, and every paid action is clearly labelled with its cost in the UI before it runs.

## Styles
| # | id | Look | Engine | Cost | Status |
|---|---|---|---|---|---|
| 1 | `blender3d` | @canwebuildthis / NMXWZ: stylized 3D characters at a desk, glowing moody sets | Blender 4.5 headless (Milestone 1) | Free, local | **Built** (stand-in character); characters and environments from references are next |
| 2 | `cinematic-ai` | ink.industries "First kiss effect V2": Pixar-like faces, strand hair, knit fabric, lantern and sunset streets, aerial and VFX shots | AI image keyframes (consistent character sheets) → AI image-to-video → lip sync | **Paid** for top quality (Kling, Veo, Seedance or similar, about $10–30 a month); free option is open-source Wan 2.2 (lower quality, slow on 8 GB) | Planned |
| 4–6 | TBD | The owner will supply references | TBD | TBD | Future |

### Style 2 (`cinematic-ai`) notes
- **Consistency:** generate a character sheet per character from the owner's references, and reuse it as a reference image in every keyframe prompt. Lock a style line and a voice or performance line per character, the way the NMXWZ guide does. Add an automatic consistency check that compares each keyframe with the sheet (face embedding or a vision check), and regenerate when a keyframe drifts.
- **Per shot:** keyframe still → owner approval in the editor's stills step → image-to-video clip of about 5–8 s → lip sync (the model's own, or a dedicated lip-sync model driven by the ElevenLabs line).
- **Cinematic shot types:** aerial, top-down, VFX moments and walking shots, picked by the shot director from the script's beats. The Blender style can't do these.
- **Provider abstraction:** a `VideoProvider` interface lets a free local model (Wan 2.2) and paid APIs swap. Paid providers need the owner's own API key in an environment variable. Claude never handles the key.
- **Cost guard:** show an estimated cost per reel before rendering; regenerating a single shot is the default action.

## Build order (revised)
1. **Engine refactor (small):** move the existing Blender render path behind the engine contract as `blender3d`, add the registry and `--style`, with no behaviour change.
2. **Style 1, characters and environments** (Sub-projects A and B in `docs/COLLABORATOR_PROMPT.md`).
3. **Style 2, `cinematic-ai` engine:** provider abstraction, character sheets, keyframes, image-to-video, lip sync, consistency check, cost guard.
4. **Editor:** a style picker with sample thumbnails; panels adapt to the engine's capabilities (for example, no 3D viewport for AI styles, but a per-shot regenerate button).
5. **Styles 3–6** as the owner supplies references. Each one gets its own brainstorm → spec → plan.
