"""Style 3: Shots-AV Animation. A low-poly hero in Aayush Visuals purple talks to a small AI buddy at a desk.

Built in phases (docs/production/shots-av/PROGRESS.md). So far the engine builds the hero; the buddies (P2), the
rooms (P3) and the director with its five camera set-ups (P4) are not built, so render() refuses to run.
From P4 it reuses blender3d.render() with plan["look"] = LOOK and shots from direct.plan_shots_av().
"""
from __future__ import annotations

import re
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


HERO_KEYS = ("outfit", "skin", "hair", "glasses", "headphones", "outfit_color", "stubble")  # the file-name order


def _slug(value) -> str:
    if isinstance(value, float):
        return f"s{round(value * 100):03d}"
    return re.sub(r"[^0-9A-Za-z_]", "", str(value)).lower()


def hero_blend(options: dict) -> Path:
    """One .blend per combination the viewer picks (outfit, skin, hair, glasses, headphones, jacket colour,
    stubble), named from the options so a render reuses a build. Defaults fill anything missing."""
    opts = {**hero_tables()["DEFAULTS"], **{k: v for k, v in options.items() if k in HERO_KEYS}}
    opts["stubble"] = float(opts["stubble"])  # 0 and 0.0 must name the same build
    return ASSETS / ("av_hero__" + "__".join(_slug(opts[k]) for k in HERO_KEYS) + ".blend")


def ensure_hero(options: dict) -> Path:
    """Build the hero for these options unless that exact build is already on disk (a few seconds in Blender)."""
    out = hero_blend(options)
    if not out.exists():
        args = [f"{k}={v}" for k, v in options.items() if k in HERO_KEYS]
        run_blender(BUILD_SCRIPT, [str(out), "hero", *args])
    return out


def build_assets() -> None:
    """Prebuild each outfit with the default skin and hair; any other pick is built on demand by ensure_hero()."""
    for outfit in hero_tables()["OUTFITS"]:
        ensure_hero({"outfit": outfit})
    print(f"shots-av: hero built into {ASSETS}; not built yet: {PENDING}")


def render(perf, n_frames: int, faces: dict, shots: list, moods: list, out: Path,
           stage: str, draft: bool) -> None:
    raise SystemExit(f"shots-av cannot render yet. Not built: {PENDING}. "
                     "See docs/production/shots-av/PROGRESS.md.")
