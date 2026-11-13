"""Style engine registry. An engine turns the shared timeline (faces, shots, moods) into frames.

Engine module contract: ID, NAME, DESCRIPTION, CAPABILITIES, build_assets(),
render(perf, n_frames, faces, shots, moods, out, stage, draft) -> None (frames in out/frames,
stills in out/stills).
"""
from __future__ import annotations

from types import ModuleType

from . import blender3d, shots_av

# ponytail: whole-reel render() only; add per-shot render_shot/preview_shot with cinematic-ai.
ENGINES: dict[str, ModuleType] = {e.ID: e for e in (blender3d, shots_av)}
DEFAULT = blender3d.ID


def get_engine(style: str) -> ModuleType:
    if style not in ENGINES:
        raise SystemExit(f"unknown style {style!r}; available: {', '.join(ENGINES)}")
    return ENGINES[style]
