from __future__ import annotations

import argparse
import json
import math
import os
import shutil
from pathlib import Path

from .blender_run import run_blender
from .captions import build_ass
from .direct import mood_keys, plan_shots
from .face import build_faces
from .finish import finish
from .plan import build_render_plan
from .schema import RATIOS, load_performance
from .timeline import mix_dialogue, place_lines, probe_duration
from .voice import import_line, synthesize_line

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "assets" / "build"
BLENDER_DIR = REPO / "blender"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="reelforge")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build-assets", help="build base character + environments")
    r = sub.add_parser("run", help="render a project folder containing performance.json")
    r.add_argument("project", type=Path)
    r.add_argument("--stage", choices=["stills", "full"], default="full")
    r.add_argument("--draft", action="store_true", help="16 samples instead of 64")
    return p


def build_assets() -> None:
    run_blender(BLENDER_DIR / "build_character.py", [str(ASSETS / "base.blend")])
    run_blender(BLENDER_DIR / "build_night_city.py", [str(ASSETS / "night_city.blend")])


def run(project: Path, stage: str, draft: bool) -> Path | None:
    project = project.resolve()
    perf = load_performance(project / "performance.json")
    out = project / "out"
    key = os.environ.get("ELEVENLABS_API_KEY")
    audio = out / "audio"
    if not key and not all((audio / f"{l.id}.mp3").exists() for l in perf.lines):
        raise SystemExit(f"Set ELEVENLABS_API_KEY or put <line_id>.mp3 files in {audio}")
    out.mkdir(parents=True, exist_ok=True)

    if key:
        voiced = {l.id: synthesize_line(l, perf.characters[l.speaker].voice_id, audio, key)
                  for l in perf.lines}
    else:
        voiced = {l.id: import_line(l, audio) for l in perf.lines}
    durations = {i: probe_duration(v.audio_path) for i, v in voiced.items()}
    placed, total = place_lines(perf.lines, voiced, durations)
    n_frames = math.ceil(total * perf.fps)
    mix_dialogue(placed, total, out / "dialogue.wav")

    faces = build_faces(perf, placed, perf.fps, n_frames)
    shots = plan_shots(placed, perf.fps, n_frames)
    moods = mood_keys(placed, perf.fps)
    w, h = RATIOS[perf.ratio]
    (out / "captions.ass").write_text(build_ass(placed, perf, w, h), encoding="utf-8")
    plan = build_render_plan(perf, n_frames, faces, shots, moods, ASSETS, out, 16 if draft else 64)
    plan_path = out / "render_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    if stage == "full":
        shutil.rmtree(out / "frames", ignore_errors=True)
    run_blender(BLENDER_DIR / "render_plan.py", [str(plan_path), stage],
                blend=Path(plan["environment_blend"]))
    if stage == "stills":
        print(f"stills: {out / 'stills'}")
        return None
    final = finish(out, perf.fps, f"final_{perf.ratio.replace(':', 'x')}.mp4")
    print(f"final: {final}")
    return final


def main(argv: list[str] | None = None) -> None:
    ns = build_parser().parse_args(argv)
    if ns.cmd == "build-assets":
        build_assets()
    else:
        run(ns.project, ns.stage, ns.draft)


if __name__ == "__main__":
    main()
