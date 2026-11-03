# ReelForge editor

The local web app for ReelForge: the Create studio, projects, the timeline editor, the asset library, and the render, approval and export screens. It sits beside the pipeline and never changes it. It reads and writes each project's `performance.json` (the pipeline's contract) and keeps its own state in `editor.json` next to it.

## Run it

```bash
cd editor
npm install
npm run dev        # http://localhost:5190
```

Rendering needs the pipeline set up as described in the main README: `.venv` with reelforge installed, Blender 4.5 in `tools/`, and ffmpeg on PATH. Without these, everything except rendering still works, and Settings shows what's missing.

## How it's built

- **Frontend:** Vite, React and TypeScript, with Zustand for state and Lucide for icons. Every colour, size and duration comes from the tokens in `src/styles/tokens.css`.
- **Backend:** `server/api.ts`, a small Node middleware running inside the Vite dev server. It was picked over a Python server because it shares one process and one language with the UI.
  - Lists, creates and saves projects under `samples/` and `projects/`. Deleted projects move to `projects/.trash/`.
  - Saves uploads to `out/audio/` (voice lines) and `media/` (imported footage) only.
  - Serves project files with range support, so video scrubs.
  - Starts `reelforge run <project> --stage stills|full [--draft]` and streams its output over server-sent events.
- **Library:** favourites, saved outfits, lighting setups and subtitle styles live in `projects/library.json`.

## What's real and what's waiting on the pipeline

| Works today | Saved, but the renderer doesn't use it yet |
|---|---|
| Script, speakers, voices, ratio, fps and quality are written to `performance.json` | Character casting and outfits: renders use the M1 stand-in |
| Caption and highlight colours reach the render | Sets other than Night-city desk, lighting presets |
| Stills and full renders, live log, frame progress for the full render | Timeline edits, shot overrides, grade sliders, subtitle font and position |
| Voice-line import and reuse, waveforms, timeline editing with undo | Exporting blank edit projects (needs a timeline renderer) |

Every screen marks placeholder art and planned assets as such.
