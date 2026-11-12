"""Style 3: Shots-AV Animation. A low-poly hero in Aayush Visuals purple talks to a small AI buddy at a desk.

Built in phases (docs/production/shots-av/PROGRESS.md). So far the engine builds the hero; the buddies (P2), the
rooms (P3) and the director with its five camera set-ups (P4) are not built, so render() refuses to run.
From P4 it reuses blender3d.render() with plan["look"] = LOOK and shots from direct.plan_shots_av().
"""
from __future__ import annotations

import runpy
from pathlib import Path

from ..blender_run import run_blender
from . import blender3d

ID = "shots-av"
NAME = "Shots-AV Animation"
DESCRIPTION = "Low-poly desk two-hander: you in brand purple and an AI buddy, cut like a polished 3D short"
CAPABILITIES = {
    "lipsync": "pipeline-visemes",
    "max_shot_seconds": 5.0,
    "ratios": ["9:16", "16:9", "3:4", "1:1"],
    "cost": "free",
    "runs": "local",
}
LOOK = "shotsav"
ASSETS = blender3d.ASSETS / "shotsav"
BUILD_SCRIPT = blender3d.BLENDER_DIR / "build_shotsav.py"
PENDING = "buddies (P2), rooms (P3), camera set-ups and director (P4)"


def hero_tables() -> dict:
    """The hero's dials, read from blender/shotsav/hero.py (pure data at import; no bpy needed)."""
    return runpy.run_path(str(blender3d.BLENDER_DIR / "shotsav" / "hero.py"))


def hero_blend(outfit: str) -> Path:
    return ASSETS / f"av_hero__{outfit}.blend"


def build_assets() -> None:
    for outfit in hero_tables()["OUTFITS"]:
        run_blender(BUILD_SCRIPT, [str(hero_blend(outfit)), "hero", f"outfit={outfit}"])
    print(f"shots-av: hero built into {ASSETS}; not built yet: {PENDING}")


def render(perf, n_frames: int, faces: dict, shots: list, moods: list, out: Path,
           stage: str, draft: bool) -> None:
    raise SystemExit(f"shots-av cannot render yet. Not built: {PENDING}. "
                     "See docs/production/shots-av/PROGRESS.md.")
