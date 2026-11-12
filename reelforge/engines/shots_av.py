"""Style 3: Shots-AV Animation. A low-poly hero in Aayush Visuals purple talks to a small AI buddy at a desk.

Built in phases (docs/production/shots-av/PROGRESS.md). The engine builds the hero (any picked combination), the
four buddies and the six rooms, plans shots with direct.plan_shots_av() and renders through blender/render_plan.py
with the shotsav look. It adds the acting the generic pipeline does not have: the buddy's BuddyCtrl tracks (talk
squash, waveform mouth, reaction clips), the hero's pose change and his blink on a cut to his close-up.
animatic() renders a silent preview from estimated timing, so a script can be checked before any voice exists.
"""
from __future__ import annotations

import json
import math
import re
import runpy
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from .. import buddy as acting
from ..blender_run import run_blender
from ..plan import build_render_plan
from ..schema import AV_HERO
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
PENDING = "captions, sound and grade (P5); the editor page (P6)"


def hero_tables() -> dict:
    """The hero's dials, read from blender/shotsav/hero.py (pure data at import; no bpy needed)."""
    return runpy.run_path(str(blender3d.BLENDER_DIR / "shotsav" / "hero.py"))


HERO_KEYS = ("outfit", "skin", "hair", "glasses", "headphones", "beard", "outfit_color", "stubble")  # the file-name order


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


def buddy_tables() -> dict:
    """The buddies' table, read from blender/shotsav/buddies.py (pure data at import; no bpy needed)."""
    return runpy.run_path(str(blender3d.BLENDER_DIR / "shotsav" / "buddies.py"))


def buddy_blend(model: str) -> Path:
    """`buddy_claude` (the schema's model name) -> assets/build/shotsav/buddy_claude.blend."""
    return ASSETS / f"{model}.blend"


def room_tables() -> dict:
    """The rooms' table, read from blender/shotsav/rooms.py (pure data at import; no bpy needed)."""
    return runpy.run_path(str(blender3d.BLENDER_DIR / "shotsav" / "rooms.py"))


def room_blend(room_id: str) -> Path:
    return ASSETS / f"{room_id}.blend"


def build_assets() -> None:
    """Prebuild each outfit with the default skin and hair (any other pick is built on demand by ensure_hero())
    and the four buddies."""
    for outfit in hero_tables()["OUTFITS"]:
        ensure_hero({"outfit": outfit})
    for bid in buddy_tables()["BUDDIES"]:
        run_blender(BUILD_SCRIPT, [str(buddy_blend(f"buddy_{bid}")), "buddy", bid])
    for rid in room_tables()["ROOMS"]:
        run_blender(BUILD_SCRIPT, [str(room_blend(rid)), "room", rid])
    print(f"shots-av: hero, buddies and rooms built into {ASSETS}")


WANTS_PLACED = True  # cli.run passes the placed lines: the buddy's acting reads them
HERO_CU = ("av_hero_34", "av_hero_front")
BLINK = (0.5, 1.0, 1.0, 0.6, 0.2)
POSES = {"rest": 0, "think": 1, "point": 2, "open": 3, "type": 4}  # PoseCtrl HandL/HandR indices (hero.HAND_POSES)


def cast(perf) -> tuple[str, str]:
    """(hero speaker name, buddy speaker name)."""
    hero = next(n for n, c in perf.characters.items() if c.model == AV_HERO)
    return hero, next(n for n in perf.characters if n != hero)


def hero_acting(faces: dict, shots: list, hero: str, n_frames: int, fps: int) -> dict:
    """Blink on the first frames after a cut to his close-up (5.3: it softens the cut), at most every 2.8 s; and
    one pose change across a cut: thinking (fist on cheek) for the first third, then both hands on the desk."""
    tracks = faces[hero]
    last = -10 ** 6
    for s in shots:
        if s.kind in HERO_CU and s.start_frame - last >= int(2.8 * fps) and s.start_frame > 0:
            for k, v in enumerate(BLINK):
                f = s.start_frame + k
                if f < n_frames:
                    for side in ("eyeBlinkLeft", "eyeBlinkRight"):
                        tracks[side][f] = max(tracks[side][f], v)
            last = s.start_frame
    switch = next((s.start_frame for s in shots if s.start_frame >= n_frames / 3), n_frames)
    hand_l = [float(POSES["think"]) if f < switch else float(POSES["rest"]) for f in range(n_frames)]
    return {"PoseCtrl": {"HandL": hand_l, "HandR": [0.0] * n_frames}}


def buddy_acting(placed: list, buddy: str, n_frames: int, fps: int, envelope: list | None, seed: int) -> dict:
    """BuddyCtrl tracks: loudness-driven talk and waveform on its lines, a reaction clip picked per line."""
    segs = []
    for p in placed:
        if p.line.speaker != buddy:
            continue
        a = int(round(p.start * fps))
        b = min(n_frames, a + int(math.ceil(p.duration * fps)))
        env = envelope[a:b] if envelope else acting.syllable_envelope(p.line.text, fps)[:b - a]
        segs.append({"start": a, "end": b, "speaking": True, "env": list(env),
                     "action": acting.pick_action(p.line.text, p.line.emotion, p.line.intensity, p.line.action)})
    return {"BuddyCtrl": acting.animate(n_frames, fps, segs, seed=seed, hero_side=1.0)}


def build_plan(perf, n_frames, faces, shots, moods, out, draft, placed, envelope=None, seed=0) -> dict:
    plan = build_render_plan(perf, n_frames, faces, shots, moods, ASSETS, out, 16 if draft else 64)
    plan["look"] = LOOK
    plan["resolution_percentage"] = 50 if draft else 100
    hero, buddy = cast(perf)
    plan["environment_blend"] = str(room_blend(perf.environment))
    for c in plan["characters"]:
        if c["name"] == hero:
            c["blend"] = str(ensure_hero(perf.characters[hero].options))
            c["props"] = hero_acting(faces, shots, hero, n_frames, perf.fps)
            c["face"] = faces[hero]
            c["stepped"] = ["HandL", "HandR"]
            c["measure"] = "head"
        else:
            c["blend"] = str(buddy_blend(perf.characters[buddy].model))
            c["props"] = buddy_acting(placed, buddy, n_frames, perf.fps, envelope, seed)
            c["stepped"] = ["eye_shape"]
            c["measure"] = "body"
    return plan


def render(perf, n_frames: int, faces: dict, shots: list, moods: list, out: Path,
           stage: str, draft: bool, placed: list | None = None) -> None:
    out = Path(out)
    env = None
    wav = out / "dialogue.wav"
    if wav.exists():
        try:
            env = acting.wav_envelope(wav, perf.fps)
        except (ValueError, OSError):
            env = None  # not 16-bit PCM: fall back to the text's syllables
    seed = int(perf.camera.get("seed", 0))
    plan = build_plan(perf, n_frames, faces, shots, moods, out, draft, placed or [], env, seed)
    plan["measure"] = stage == "stills"
    missing = [b for b in [plan["environment_blend"]] + [c["blend"] for c in plan["characters"]] if not Path(b).exists()]
    if missing:
        raise SystemExit(f"missing assets {missing}: run `reelforge build-assets --style shots-av`")
    plan_path = out / "render_plan.json"
    plan_text = json.dumps(plan)
    plan_path.write_text(plan_text, encoding="utf-8")
    target = out / ("frames" if stage == "full" else "stills")
    want = plan["n_frames"] if stage == "full" else len(plan["shots"])
    key = blender3d.render_key(plan_text, plan)
    key_file = out / f".render_key_{stage}"
    same = key_file.exists() and key_file.read_text() == key
    if same and target.exists() and len(list(target.glob("*.png"))) >= want:
        print(f"{stage}: up to date, skipping render")
        return
    if not same:
        shutil.rmtree(target, ignore_errors=True)
        key_file.write_text(key)
    run_blender(blender3d.BLENDER_DIR / "render_plan.py", [str(plan_path), stage], blend=Path(plan["environment_blend"]))


def estimate_timing(lines, rate_wps: float = 2.9, gap: float = 0.35, lead: float = 0.3) -> list[tuple[float, float]]:
    """(start, duration) per line from its word count: for animatics before any voice exists."""
    t, out = lead, []
    for l in lines:
        words = max(1, len(l.text.split()))
        d = max(0.8, words / rate_wps + 0.25)
        out.append((t, d))
        t += d + gap
    return out


def _fake_chars(text: str, start: float, duration: float):
    """Even character timings across the line, so visemes move the mouth in an animatic."""
    from ..alignment import Char
    n = max(1, len(text))
    step = duration / n
    return [Char(ch, start + i * step, start + (i + 1) * step) for i, ch in enumerate(text)]


def animatic(project: Path, draft: bool = True, stage: str = "full") -> Path:
    """A silent preview: estimated (or `timing.json`) line timing, synthetic lip timing, the real shot plan and
    acting, rendered to <project>/out/animatic.mp4. timing.json: {"<line id>": [start_s, duration_s], ...}."""
    from ..direct import mood_keys, plan_shots_av
    from ..face import build_faces
    from ..schema import load_performance
    from ..timeline import Placed
    from ..voice import VoicedLine
    project = Path(project).resolve()
    perf = load_performance(project / "performance.json")
    tfile = project / "timing.json"
    timing = json.loads(tfile.read_text(encoding="utf-8")) if tfile.exists() else {}
    est = estimate_timing(perf.lines)
    placed = []
    for l, (s0, d0) in zip(perf.lines, est):
        s0, d0 = timing.get(l.id, (s0, d0))
        placed.append(Placed(l, VoicedLine(l.id, project / "out" / "audio" / f"{l.id}.mp3",
                                           _fake_chars(l.text, 0.0, d0)), s0, d0))
    last = placed[-1]
    n_frames = math.ceil((last.start + last.duration + 0.9) * perf.fps)  # hold 0.9 s after the final word
    faces = build_faces(perf, placed, perf.fps, n_frames)
    hero, buddy = cast(perf)
    seed = int(perf.camera.get("seed", 0))
    shots = plan_shots_av(placed, perf.fps, n_frames, hero, buddy, seed, perf.camera.get("grammar", "signature"),
                          perf.camera)
    out = project / "out" / "animatic"
    out.mkdir(parents=True, exist_ok=True)
    (out / "shots.json").write_text(json.dumps([asdict(s) for s in shots], indent=1), encoding="utf-8")
    render(perf, n_frames, faces, shots, mood_keys(placed, perf.fps), out, stage, draft, placed)
    if stage != "full":
        return out / "stills"
    mp4 = project / "out" / "animatic.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(perf.fps), "-i",
                    str(out / "frames" / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-movflags", "+faststart", str(mp4)], check=True)
    print(f"animatic: {mp4}")
    return mp4
