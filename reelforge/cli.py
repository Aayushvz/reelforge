from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from dataclasses import replace
from pathlib import Path

from .a2f import frames_to_tracks
from .ambience import add_ambience
from .captions import build_ass
from .direct import mood_keys, plan_shots, plan_shots_v2
from .engines import DEFAULT, ENGINES, get_engine
from .face import build_faces
from .finish import finish
from .schema import LOOKS, QUALITIES, RATIOS, load_performance
from .timeline import mix_dialogue, place_lines, probe_duration
from .voice import VoiceError, has_take, import_line, synthesize_line, take_path

REPO = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="reelforge")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-assets", help="build base character + environments")
    b.add_argument("--style", choices=list(ENGINES), default=DEFAULT)
    r = sub.add_parser("run", help="render a project folder containing performance.json")
    r.add_argument("project", type=Path)
    r.add_argument("--stage", choices=["stills", "full"], default="full")
    r.add_argument("--draft", action="store_true", help="16 samples instead of 64")
    r.add_argument("--style", choices=list(ENGINES), help="override the project's style")
    r.add_argument("--look", choices=list(LOOKS), help="override the project's look")
    r.add_argument("--quality", choices=list(QUALITIES), help="cinema look: preview | standard | cinema")
    bn = sub.add_parser("bench", help="time fixed stills for a look and quality (no voices needed)")
    bn.add_argument("--look", choices=list(LOOKS), default="cinema")
    bn.add_argument("--quality", choices=list(QUALITIES), default="standard")
    bn.add_argument("--room", help="only this room")
    bn.add_argument("--out", type=Path, default=REPO / "samples" / "_bench" / "out")
    v = sub.add_parser("voices", help="generate missing ElevenLabs takes (one JSON status line each)")
    v.add_argument("project", type=Path)
    v.add_argument("--line", action="append", default=[], help="only these line ids")
    v.add_argument("--force", action="store_true", help="drop the cached take and generate a new one")
    return p


def voices(project: Path, only: list[str], force: bool) -> int:
    """Generate API takes for lines without an imported mp3. Prints {"line", "status", ...} per line."""
    project = project.resolve()
    perf = load_performance(project / "performance.json")
    audio = project / "out" / "audio"
    key = os.environ.get("ELEVENLABS_API_KEY")
    failed = 0
    for l in perf.lines:
        if only and l.id not in only:
            continue
        voice_id = perf.characters[l.speaker].voice_id
        if (audio / f"{l.id}.mp3").exists():
            status = {"status": "imported"}
        elif not l.text.strip():
            status = {"status": "error", "error": "Empty line"}
        else:
            if force:
                for f in (take_path(l, voice_id, audio), take_path(l, voice_id, audio).with_suffix(".json")):
                    f.unlink(missing_ok=True)
            if has_take(l, voice_id, audio):
                status = {"status": "ready"}
            elif not key:
                status = {"status": "error", "error": "No ElevenLabs API key. Add it in Settings."}
            else:
                try:
                    synthesize_line(l, voice_id, audio, key)
                    status = {"status": "ready"}
                except VoiceError as e:
                    status = {"status": "error", "error": str(e)}
        failed += status["status"] == "error"
        print(json.dumps({"line": l.id, **status}), flush=True)
    return 1 if failed else 0


def run(project: Path, stage: str, draft: bool, style: str | None = None, look: str | None = None,
        quality: str | None = None) -> Path | None:
    project = project.resolve()
    perf = load_performance(project / "performance.json")
    perf = replace(perf, look=look or perf.look, quality="preview" if draft else (quality or perf.quality))
    engine = get_engine(style or perf.style)
    out = project / "out"
    key = os.environ.get("ELEVENLABS_API_KEY")
    audio = out / "audio"
    def voiced_ok(l):
        return (audio / f"{l.id}.mp3").exists() or has_take(l, perf.characters[l.speaker].voice_id, audio)
    if not key and not all(voiced_ok(l) for l in perf.lines):
        raise SystemExit(f"Set ELEVENLABS_API_KEY or put <line_id>.mp3 files in {audio}")
    out.mkdir(parents=True, exist_ok=True)

    voiced = {}
    for l in perf.lines:  # an imported take (e.g. from the ElevenLabs web app) always wins over the API
        if (audio / f"{l.id}.mp3").exists():
            voiced[l.id] = import_line(l, audio)
            print(f"voice {l.id}: imported mp3")
        else:
            voiced[l.id] = synthesize_line(l, perf.characters[l.speaker].voice_id, audio, key)
            print(f"voice {l.id}: ElevenLabs API")
    durations = {i: probe_duration(v.audio_path) for i, v in voiced.items()}
    placed, total = place_lines(perf.lines, voiced, durations)
    n_frames = math.ceil(total * perf.fps)
    mix_dialogue(placed, total, out / "dialogue.wav")
    if perf.ambience:
        add_ambience(out / "dialogue.wav", perf.environment, perf.lighting, total)

    overrides = {}
    for p in placed:
        f = out / "a2f" / f"{p.line.id}.json"
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            take = hashlib.sha1(voiced[p.line.id].audio_path.read_bytes()).hexdigest()
            if data.get("audio_sha1", take) != take:  # made from an older take: visemes are safer
                print(f"a2f {p.line.id}: stale (audio changed), using visemes")
                continue
            overrides[p.line.id] = frames_to_tracks(data["frames"], perf.fps,
                                                    math.ceil(p.duration * perf.fps) + 2)
    faces = build_faces(perf, placed, perf.fps, n_frames, lipsync_override=overrides)
    if perf.look == "classic":
        shots = plan_shots(placed, perf.fps, n_frames)
    else:  # seeded by the project so the editor preview and the render agree
        seed = int(perf.camera.get("seed", int(hashlib.sha1(project.name.encode()).hexdigest()[:6], 16)))
        shots = plan_shots_v2(placed, perf.fps, n_frames, list(perf.characters), seed, perf.camera)
    moods = mood_keys(placed, perf.fps)
    w, h = RATIOS[perf.ratio]
    (out / "captions.ass").write_text(build_ass(placed, perf, w, h), encoding="utf-8")
    engine.render(perf, n_frames, faces, shots, moods, out, stage, draft)
    if stage == "stills":
        print(f"stills: {out / 'stills'}")
        return None
    final = finish(out, perf.fps, f"final_{perf.ratio.replace(':', 'x')}.mp4", perf.environment, perf.look)
    print(f"final: {final}")
    return final


def main(argv: list[str] | None = None) -> None:
    ns = build_parser().parse_args(argv)
    if ns.cmd == "build-assets":
        get_engine(ns.style).build_assets()
    elif ns.cmd == "bench":
        from .bench import bench
        bench(ns.look, ns.quality, ns.out, only=ns.room)
    elif ns.cmd == "voices":
        raise SystemExit(voices(ns.project, ns.line, ns.force))
    else:
        run(ns.project, ns.stage, ns.draft, ns.style, ns.look, ns.quality)


if __name__ == "__main__":
    main()
