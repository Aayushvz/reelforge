# Aayush's Editor

The codebase and its Python package are still called `reelforge`.

**Turn a script into a cinematic, lip-synced, animated short**, built for Instagram Reels and Shorts (9:16 by default; 16:9, 3:4 and 1:1 are planned).

You write the script and generate the voice lines. reelforge handles timing, facial animation and emotion, camera shots, mood lighting, rendering, captions and the final mix.

> Status: **Shots-AV** (you + an AI buddy at a desk) is the main style: 24 outfits, 25 rooms, a 36-angle director, ElevenLabs voices, and the editor. See [docs/HANDOFF.md](docs/HANDOFF.md).

## How it works
```
script → performance.json → voice (ElevenLabs) → timeline + lip-sync + emotions
       → shot list + mood lighting → STYLE ENGINE (Blender 3D today) → captions + grade + -14 LUFS → MP4
```
It's a multi-style platform. Each animation style is a pluggable "engine":

| Style | Look | Status |
|---|---|---|
| `blender3d` | Realistic imported characters (Matt, Freya, Mina) | Cast only: its sets moved to Shots-AV |
| `shots-av` | Shots-AV Animation: you and an AI buddy robot at a desk, low-poly 3D in brand purple, 12 rooms, 36 camera angles | **Works**: editor page, ElevenLabs voices, benchmark passed (see below) |
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
.venv/Scripts/python -m pytest -q          # 246 tests should pass
```

## Make a reel
Shots-AV is the main style: see "Make a Shots-AV reel" below. Its hero has 24 outfits and there are 25 rooms,
including the old library's ten sets and three imported rooms ("Classic sets").

The Blender 3D style keeps the imported cast (Matt, Freya, Mina: `"model": "matt" | "freya" | "cute_girl"` in
`performance.json`) but has no environments of its own now; they moved to Shots-AV.

## Open it like an app (Windows)
Run `powershell -ExecutionPolicy Bypass -File tools/launcher/Install-Shortcut.ps1` once (add `-StartMenu` for the
Start menu too). The **Aayush's Editor** desktop icon starts the editor's server in the background, out of sight, and opens the
editor in its own Chrome (or Edge) app window. Closing the window leaves the server running, so renders carry on;
`tools/launcher/Stop-Aayushs-Editor.ps1` stops it. If it doesn't open, the server's log is `%TEMP%\reelforge-editor.log`.

## Make a Shots-AV reel (you + an AI buddy)
The easy way is the editor: `cd editor && npm install && npm run dev`, open `http://localhost:5190/shots-av`, paste a
script (`Me: ...` / `Claude: ...`), pick the buddy (Claude, ChatGPT, Figma, Nova), the room and your spot in it, the
camera angles and the captions, and press **Generate reel**. Voices come from ElevenLabs with your own key (Settings);
each line's emotion is performed. Quality: Draft (about 6 min for 30 s), Balanced (default, about 15 min for 30 s at
1080x1920), Final (about 3x Balanced).
From the command line:
```bash
.venv/Scripts/reelforge build-assets --style shots-av                 # hero, 4 buddies, 12 rooms
.venv/Scripts/reelforge animatic <project>                             # silent preview, estimated timing
.venv/Scripts/reelforge run <project> --stage full                     # Balanced, 1080x1920
.venv/Scripts/reelforge run <project> --stage full --quality cinema    # Final
```
Details: [docs/HANDOFF.md section 9](docs/HANDOFF.md) and [docs/production/shots-av/PROGRESS.md](docs/production/shots-av/PROGRESS.md).

## Repository layout
| Path | What's in it |
|---|---|
| `reelforge/` | Pipeline (Python, standard library only): schema, voice, alignment, timeline, visemes and face, director, captions, finish, CLI |
| `blender/` | Headless Blender scripts: character, set, render-plan executor; `blender/shotsav/` holds the Shots-AV hero, buddies and rooms |
| `editor/` | The web editor (React + Vite), including the Shots-AV page |
| `tools/a2f_fetch.py` | Audio2Face ONNX experiment (optional) |
| `tests/` | pytest suite |
| `samples/` | Example projects: `shots-av-fixture` (the 20-line reference timing), `shots-av-p5-night`, `shots-av-p5-day`, `imported-test` |
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
