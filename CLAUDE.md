# reelforge

A script-to-cinematic-3D-animated-reel generator, built on Blender, ElevenLabs and ffmpeg.

**Start every session by reading `docs/HANDOFF.md`.** It covers what's built, the user's decisions, how to run things, and what's next.

Ground rules:
- Current priority: `docs/superpowers/specs/2026-11-01-cast-sets-editor-brief.md`.
- No paid tools for the `blender3d` style. Paid AI-video providers are an opt-in only for the `cinematic-ai` style, using the owner's own key.
- No API keys or account creation by Claude.
- ElevenLabs voices are generated in the web app through the user's logged-in Chrome.
- Ask before large downloads (over 2 GB) or system-wide installs.
- Blender path: `export REELFORGE_BLENDER="$(cat tools/blender_path.txt)"`. Never use `setx`.
- Tests: `.venv/Scripts/python -m pytest -q`. Keep the `reelforge/` core standard-library only.
- **Never reduce character quality**: no decimation, no texture downscaling, no shape-key pruning on characters. Facial detail is the target. Optimizing a character means cleanup and wiring only.
- Keep token use low: fresh sessions, and cheaper subagent models for mechanical tasks.
