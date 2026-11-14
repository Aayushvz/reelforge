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


def imported() -> dict:
    """Third-party characters wired by import_character.py (blender/imported.py). Its SETS (the imported rooms) are
    Shots-AV backdrops now (blender/shotsav/imported_rooms.py)."""
    return runpy.run_path(str(BLENDER_DIR / "imported.py"))


def cast_outfits() -> dict[str, int]:
    """The cast of this style: the imported, full-detail models (Matt, Freya, Mina). The old procedural cast is gone;
    its wardrobe lives on as Shots-AV hero outfits."""
    return {k: len(v.get("outfits", [{}])) for k, v in imported()["CHARACTERS"].items()}


def cast_ids() -> list[str]:
    return list(cast_outfits())


def set_presets() -> dict[str, list[str]]:
    """This style has no environments of its own: the ten sets and the imported rooms moved to Shots-AV
    ("Classic sets": blender/shotsav/legacy_sets.py and imported_rooms.py)."""
    return {}


def _out_name(cid: str, o: int) -> str:
    return f"{cid}__o{o}.blend" if o else f"{cid}.blend"


def build_assets() -> None:
    imp = imported()
    for cid, n in cast_outfits().items():
        spec = imp["CHARACTERS"].get(cid)
        if spec and not (imp["SRC_ROOT"] / spec["src"]).exists():
            print(f"skip {cid}: source not found under {imp['SRC_ROOT']} (set REELFORGE_IMPORTS)")
            continue
        for o in range(n):
            run_blender(BLENDER_DIR / "import_character.py", [str(ASSETS / _out_name(cid, o)), cid, str(o)])


def render(perf, n_frames: int, faces: dict, shots: list, moods: list, out: Path,
           stage: str, draft: bool) -> None:
    plan = build_render_plan(perf, n_frames, faces, shots, moods, ASSETS, out, 16 if draft else 64)
    plan["resolution_percentage"] = 50 if draft else 100  # drafts: quarter the pixels, same framing
    missing = [b for b in [plan["environment_blend"]] + [c["blend"] for c in plan["characters"]]
               if not Path(b).exists()]
    if missing:
        if not set_presets():
            raise SystemExit(f"this style has no environments now (they moved to Shots-AV desk reels); missing {missing}")
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
              BLENDER_DIR / "render_plan.py", BLENDER_DIR / "camera_rig.py",
              *sorted((BLENDER_DIR / "looks").glob("*.py"))]:
        st = Path(f).stat()
        h.update(f"{f}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()
