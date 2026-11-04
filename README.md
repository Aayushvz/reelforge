# reelforge

**Turn a script into a cinematic, lip-synced, animated short**, built for Instagram Reels and Shorts (9:16 by default; 16:9, 3:4 and 1:1 are planned).

You write the script and generate the voice lines. reelforge handles timing, facial animation and emotion, camera shots, mood lighting, rendering, captions and the final mix.

> Status: **Milestone 1 (pipeline) is done.** v1 of the 7-character cast (3 outfits each) and the 10 sets × 3 lighting presets are in; they get a quality pass next, then the editor UI. See [Roadmap](#roadmap).

## How it works
```
script → performance.json → voice (ElevenLabs) → timeline + lip-sync + emotions
       → shot list + mood lighting → STYLE ENGINE (Blender 3D today) → captions + grade + -14 LUFS → MP4
```
It's a multi-style platform. Each animation style is a pluggable "engine":

| Style | Look | Status |
|---|---|---|
| `blender3d` | Stylized 3D characters in moody, glowing sets | Works: 7-character cast, 10 sets × 3 lighting presets (v1 look) |
| `cinematic-ai` | Pixar-like cinematic AI video (opt-in, paid providers) | Planned |
| more | From future references | Planned |

## Requirements
- Windows 11, macOS or Linux, with an NVIDIA GPU recommended (developed on an RTX 4060 with 8 GB)
- **Python 3.12+**
- **ffmpeg / ffprobe** on PATH
- **Blender 4.5 LTS**. The portable build goes in `tools/blender-4.5/` (git-ignored); see the setup steps below.
- An ElevenLabs account. Generate voice lines in the web app, or set `ELEVENLABS_API_KEY` to use the API.

## Setup
```bash
git clone https://github.com/Aayushvz/reelforge.git
cd reelforge
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev,align]"     # macOS/Linux: .venv/bin/python
# Download the Blender 4.5 LTS portable build from https://download.blender.org/release/Blender4.5/
# and extract it into tools/blender-4.5/, then:
echo "<absolute path to blender.exe>" > tools/blender_path.txt
export REELFORGE_BLENDER="$(cat tools/blender_path.txt)"
.venv/Scripts/python -m pytest -q          # 63 tests should pass
```

## Make a reel
1. Create a project folder with a `performance.json`. Copy `samples/look-test/performance.json` as a template. It lists the lines, speaker, emotion, intensity, mood and punchline.
   - Cast: give each character `"model"` (kai, rey, dev, mo, aria, zoe, noor) and `"outfit"` (0–2). Dials live in `blender/cast.py`.
   - Set: `"environment"` (night_city, bedroom, rooftop, cafe, lantern_street, subway, classroom, office, night_mart, pier) and optional `"lighting"` (a preset name from `blender/sets.py`, e.g. `"cafe"` + `"rainy_day"`).
2. Put one mp3 per line in `<project>/out/audio/<line_id>.mp3`, or set `ELEVENLABS_API_KEY`.
3. Build and render:
```bash
.venv/Scripts/reelforge build-assets   # whole cast (21 outfits) + 30 set files, a few minutes
.venv/Scripts/reelforge run <project> --stage stills --draft   # quick per-shot preview (draft = 16 samples, half resolution)
.venv/Scripts/reelforge run <project> --stage full             # final video → <project>/out/final_9x16.mp4
```

## Repository layout
| Path | What's in it |
|---|---|
| `reelforge/` | Pipeline (Python, standard library only): schema, voice, alignment, timeline, visemes and face, director, captions, finish, CLI |
| `blender/` | Headless Blender scripts: character, set, render-plan executor |
| `tools/a2f_fetch.py` | Audio2Face ONNX experiment (optional) |
| `tests/` | pytest suite |
| `samples/` | Example projects: `look-test` (M1), `cafe-test` (one character), `duo-test` (two characters), `talk-<name>` (one per cast member) |
| `references/` | Style, character and environment reference images |
| `docs/` | Handoff, specs, plans, notes |

## Docs (start here if you're contributing)
- [docs/HANDOFF.md](docs/HANDOFF.md): current state, decisions, what's next
- [docs/COLLABORATOR_PROMPT.md](docs/COLLABORATOR_PROMPT.md): a ready-to-paste prompt for a Claude Code session
- [Production brief: cast, sets, editor](docs/superpowers/specs/2026-11-01-cast-sets-editor-brief.md)
- [Multi-style engine design](docs/superpowers/specs/2026-10-31-multi-style-engines.md)
- [Original design spec](docs/superpowers/specs/2026-10-31-animated-reel-generator-design.md)

## Roadmap
0. ~~Engine refactor (pluggable styles)~~ done
1. **Cast:** 4 male and 3 female original stylized characters, with a Gen-Z wardrobe system (25+ items): v1 done
2. **Sets:** 10 environments × 3 lighting presets: v1 done
3. **Editor:** a dark, minimal desktop-class web editor (script → cast → set → voice → timeline → approve → render)
4. `cinematic-ai` style engine
5. More styles

## License
Private project. All rights reserved.
