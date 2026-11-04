"""Style 1: stylized 3D characters in moody sets, rendered headless in Blender."""
from __future__ import annotations

import hashlib
import json
import runpy
import shutil
from pathlib import Path

from ..blender_run import run_blender
from ..plan import build_render_plan

ID = "blender3d"
NAME = "Blender 3D"
DESCRIPTION = "Stylized 3D characters in moody, glowing sets"
CAPABILITIES = {
    "lipsync": "pipeline-visemes",
    "max_shot_seconds": None,
    "ratios": ["9:16", "16:9", "3:4", "1:1"],
    "cost": "free",
    "runs": "local",
}

REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "assets" / "build"
BLENDER_DIR = REPO / "blender"


def cast_outfits() -> dict[str, int]:
    return {k: len(v.get("outfits", [{}])) for k, v in runpy.run_path(str(BLENDER_DIR / "cast.py"))["CAST"].items()}


def cast_ids() -> list[str]:
    return list(cast_outfits())


def set_presets() -> dict[str, list[str]]:
    return {k: list(v["presets"]) for k, v in runpy.run_path(str(BLENDER_DIR / "sets.py"))["SETS"].items()}


def build_assets() -> None:
    for cid, n in cast_outfits().items():
        for o in range(n):
            name = f"{cid}__o{o}.blend" if o else f"{cid}.blend"
            run_blender(BLENDER_DIR / "build_character.py", [str(ASSETS / name), cid, str(o)])
    for sid, presets in set_presets().items():
        for preset in presets:
            run_blender(BLENDER_DIR / "build_set.py", [str(ASSETS / f"{sid}__{preset}.blend"), sid, preset])
        shutil.copyfile(ASSETS / f"{sid}__{presets[0]}.blend", ASSETS / f"{sid}.blend")  # default lighting


def render(perf, n_frames: int, faces: dict, shots: list, moods: list, out: Path,
           stage: str, draft: bool) -> None:
    plan = build_render_plan(perf, n_frames, faces, shots, moods, ASSETS, out, 16 if draft else 64)
    plan["resolution_percentage"] = 50 if draft else 100  # drafts: quarter the pixels, same framing
    missing = [b for b in [plan["environment_blend"]] + [c["blend"] for c in plan["characters"]]
               if not Path(b).exists()]
    if missing:
        raise SystemExit(f"missing assets {missing}: run `reelforge build-assets` "
                         f"(cast: {', '.join(cast_ids())}; sets: {set_presets()})")
    plan_path = out / "render_plan.json"
    plan_text = json.dumps(plan)
    plan_path.write_text(plan_text, encoding="utf-8")
    target = out / ("frames" if stage == "full" else "stills")
    want = plan["n_frames"] if stage == "full" else len(plan["shots"])
    key = render_key(plan_text, plan)
    key_file = out / f".render_key_{stage}"
    same = key_file.exists() and key_file.read_text() == key
    if same and target.exists() and len(list(target.glob("*.png"))) >= want:
        print(f"{stage}: up to date, skipping render")
        return
    if not same:  # inputs changed: start clean. Same inputs + partial output = a crash: resume.
        shutil.rmtree(target, ignore_errors=True)
        key_file.write_text(key)
    run_blender(BLENDER_DIR / "render_plan.py", [str(plan_path), stage],
                blend=Path(plan["environment_blend"]))


def render_key(plan_text: str, plan: dict) -> str:
    """Plan + the blend files and scripts it renders with (size + mtime: hashing blends is slow)."""
    h = hashlib.sha1(plan_text.encode())
    for f in [plan["environment_blend"], *(c["blend"] for c in plan["characters"]),
              BLENDER_DIR / "render_plan.py"]:
        st = Path(f).stat()
        h.update(f"{f}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()
