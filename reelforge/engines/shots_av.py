"""Style 3: Shots-AV Animation. A low-poly hero in Aayush Visuals purple talks to a small AI buddy at a desk.

Built in phases (docs/production/shots-av/PROGRESS.md). The engine builds the hero (any picked combination), the
four buddies and the six rooms, plans shots with direct.plan_shots_av() and renders through blender/render_plan.py
with the shotsav look. It adds the acting the generic pipeline does not have: the buddy's BuddyCtrl tracks (talk
squash, waveform mouth, reaction clips), the hero's pose change and his blink on a cut to his close-up.
animatic() renders a silent preview from estimated timing, so a script can be checked before any voice exists.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import runpy
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from ..angles import ANGLES
from .. import buddy as acting
from ..blender_run import run_blender
from ..plan import build_render_plan
from ..schema import AV_BUDDIES, AV_HERO
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
    """Prebuild the three brand outfits with the default skin and hair (any other outfit or pick is built on demand
    by ensure_hero()), the four buddies and the rooms."""
    for outfit in ("puffer", "hoodie", "overshirt"):
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


ACCENTS = {"matt": "#6E8FB8", "freya": "#C9A27A", "cute_girl": "#7FA36B"}  # caption dots for the realistic cast


def cast(perf) -> tuple[str, str]:
    """(speaker at the desk, the other speaker). The desk chair goes to the low-poly hero if one is cast, else to
    "me" (the editor's name for you), else to whoever is not a bot, else to the first character."""
    names = list(perf.characters)
    model = {n: perf.characters[n].model for n in names}
    hero = (next((n for n in names if model[n] == AV_HERO), None)
            or ("me" if "me" in model and model["me"] not in AV_BUDDIES else None)
            or next((n for n in names if model[n] not in AV_BUDDIES), names[0]))
    return hero, next(n for n in names if n != hero)


def kind(model: str) -> str:
    """av_hero | bot | person (Matt, Freya, Mina: imported, seated by blender/shotsav/seated.py)."""
    return "av_hero" if model == AV_HERO else "bot" if model in AV_BUDDIES else "person"


def person_blend(model: str) -> Path:
    return blender3d.ASSETS / f"{model}.blend"


def person_acting(faces: dict, shots: list, name: str, close_kinds: tuple, n_frames: int, fps: int,
                  env: list | None, ranges: list) -> None:
    """A realistic speaker: smoothed mouth (loudness on its lines) and a blink on cuts to its close-up.
    render_plan.py adds what every contract character gets: eyelines, head turns, breathing, talk beats."""
    tracks = faces[name]
    smooth_mouth(tracks, fps, env, ranges)
    last = -10 ** 6
    for s in shots:
        if s.kind in close_kinds and s.start_frame - last >= int(2.8 * fps) and s.start_frame > 0:
            for k, v in enumerate(BLINK):
                f = s.start_frame + k
                if f < n_frames:
                    for side in ("eyeBlinkLeft", "eyeBlinkRight"):
                        if side in tracks:
                            tracks[side][f] = max(tracks[side][f], v)
            last = s.start_frame


MOUTH_SMOOTH = {"jawOpen": (1.6, 3.2), "mouthFunnel": (1.8, 3.5), "mouthPucker": (1.8, 3.5),
                "mouthStretchLeft": (1.8, 3.5), "mouthStretchRight": (1.8, 3.5), "mouthPressLeft": (1.0, 2.4),
                "mouthPressRight": (1.0, 2.4), "mouthRollLower": (1.0, 2.4), "mouthRollUpper": (1.0, 2.4),
                "mouthClose": (1.0, 2.4)}


def smooth_mouth(tracks: dict, fps: int, env: list | None, ranges: list) -> None:
    """Per-letter visemes flicker. Smooth every mouth channel (fast in, slower out; closures stay quick) and, while
    the hero speaks, mix the jaw with the voice's loudness so the mouth opens on the loud syllables."""
    for ch, (att, rel) in MOUTH_SMOOTH.items():
        if ch in tracks:
            tracks[ch] = [round(v, 4) for v in acting.follow(tracks[ch], att, rel)]
    if not env or "jawOpen" not in tracks:
        return
    loud = acting.follow(env, 1.3, 3.0)
    jaw = tracks["jawOpen"]
    for a, b in ranges:
        for f in range(max(0, a), min(len(jaw), b, len(loud))):
            jaw[f] = round(min(0.75, 0.5 * jaw[f] + 0.45 * min(1.0, loud[f] * 1.15)), 4)


def hero_acting(faces: dict, shots: list, hero: str, n_frames: int, fps: int, env: list | None = None,
                ranges: list | None = None) -> dict:
    """Blink on the first frames after a cut to his close-up (5.3: it softens the cut), at most every 2.8 s; and
    one pose change across a cut: thinking (fist on cheek) for the first third, then both hands on the desk."""
    tracks = faces[hero]
    smooth_mouth(tracks, fps, env, ranges or [])
    last = -10 ** 6
    for s in shots:
        if s.kind in HERO_CU and s.start_frame - last >= int(2.8 * fps) and s.start_frame > 0:
            for k, v in enumerate(BLINK):
                f = s.start_frame + k
                if f < n_frames:
                    for side in ("eyeBlinkLeft", "eyeBlinkRight"):
                        tracks[side][f] = max(tracks[side][f], v)
            last = s.start_frame
    switch = pose_switch(shots, n_frames)
    hand_l = [float(POSES["think"]) if f < switch else float(POSES["type"]) for f in range(n_frames)]
    hand_r = [float(POSES["rest"]) if f < switch else float(POSES["type"]) for f in range(n_frames)]
    return {"PoseCtrl": {"HandL": hand_l, "HandR": hand_r}}


def pose_switch(shots: list, n_frames: int) -> int:
    """The frame of the one pose change (think -> type): the first cut after a third of the runtime."""
    return next((s.start_frame for s in shots if s.start_frame >= n_frames / 3), n_frames)


def sound_plan(placed: list, shots: list, hero: str, buddy: str, n_frames: int, fps: int, perf=None):
    """(buddy line starts, keyboard intervals) in seconds: a blip as each bot buddy line starts; key taps while the
    low-poly hero is in his typing pose and not talking. With perf, only the cast that has them gets them."""
    bot = perf is None or kind(perf.characters[buddy].model) == "bot"
    types = perf is None or kind(perf.characters[hero].model) == "av_hero"
    blips = [p.start for p in placed if p.line.speaker == buddy] if bot else []
    if not types:
        return blips, []
    t0, t1 = pose_switch(shots, n_frames) / fps, n_frames / fps
    talk = sorted((p.start, p.start + p.duration) for p in placed if p.line.speaker == hero)
    keys, t = [], t0
    for a, b in talk:
        if b <= t:
            continue
        if a > t:
            keys.append((t, min(a, t1)))
        t = max(t, b + 0.3)
    if t < t1:
        keys.append((t, t1))
    return blips, [(a, b) for a, b in keys if b - a > 0.4]


def caption_tints(perf) -> dict:
    """Speaker dot colours: the low-poly hero's jacket, a bot's shell, a realistic character's accent."""
    return {n: tint(c) for n, c in perf.characters.items()}


def tint(c) -> str:
    k = kind(c.model)
    if k == "av_hero":
        return c.options.get("outfit_color", "#7C3AED")
    if k == "bot":
        return buddy_tables()["BUDDIES"][c.model.replace("buddy_", "")]["shell"]
    return ACCENTS.get(c.model, "#B8B8C0")


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


def room_view(perf, seed: int) -> dict:
    """Where the desk sits in the room: the project's room_view, else one of the room's good spots, picked by the
    reel's seed so two projects in the same room are not staged the same way."""
    if perf.room_view:
        return dict(perf.room_view)
    spots = room_tables().get("VIEW_SPOTS", {}).get(perf.environment) or [{}]
    return dict(spots[seed % len(spots)])


def build_plan(perf, n_frames, faces, shots, moods, out, draft, placed, envelope=None, seed=0) -> dict:
    plan = build_render_plan(perf, n_frames, faces, shots, moods, ASSETS, out, 16 if draft else 64)
    plan["look"] = LOOK
    plan["resolution_percentage"] = 50 if draft else 100
    if draft:  # Draft: half size, 8 samples, coarser haze (see TIERS)
        plan["tier"] = dict(TIERS["draft"])
    elif perf.quality != "cinema":  # Balanced: full size, about 3x faster than Final (see TIERS)
        plan["tier"] = dict(TIERS["balanced"])
    hero, buddy = cast(perf)
    plan["environment_blend"] = str(room_blend(perf.environment))
    plan["room_view"] = room_view(perf, seed)
    seats = None
    for c in plan["characters"]:
        name = c["name"]
        model = perf.characters[name].model
        at_desk = name == hero
        c["mark"] = "Mark_A" if at_desk else "Mark_B"
        ranges = [(int(round(p.start * perf.fps)), int(round((p.start + p.duration) * perf.fps)))
                  for p in placed if p.line.speaker == name]
        k = kind(model)
        if k == "av_hero":
            c["blend"] = str(ensure_hero(perf.characters[name].options))
            c["props"] = hero_acting(faces, shots, name, n_frames, perf.fps, envelope, ranges)
            c["face"] = faces[name]
            c["stepped"] = ["HandL", "HandR"]
            c["measure"] = "head"
        elif k == "bot":
            c["blend"] = str(buddy_blend(model))
            c["props"] = buddy_acting(placed, name, n_frames, perf.fps, envelope, seed)
            c["stepped"] = ["eye_shape"]
            c["measure"] = "body"
        else:  # Matt, Freya, Mina: the built full-detail file, seated at render time
            seats = seats or imported_seats()
            c["blend"] = str(person_blend(model))
            c["seat"] = {**seats[model], "slot": "you" if at_desk else "guest"}
            person_acting(faces, shots, name, HERO_CU if at_desk else ("av_buddy",), n_frames, perf.fps, envelope,
                          ranges)
            c["face"] = faces[name]
            c["measure"] = "head"
            if not at_desk:
                person_framing(plan["shots"], name)
    return plan


def person_framing(shots: list, name: str) -> None:
    """The buddy angles frame a small robot (eyes 62% down the frame). A person in that seat keeps each angle's
    lens and direction but gets the hero close-up's eye line and head size."""
    def fix(fr):
        if fr:
            fr["eyes"] = min(fr.get("eyes", 0.52), 0.52)
            fr["head"] = min(fr.get("head", 0.46), 0.46)
    for s in shots:
        if s.get("subject") == name:
            fix(s.get("framing"))
        con = s.get("connect") or {}
        if con.get("to") == name:
            fix(con.get("framing"))


def imported_seats() -> dict:
    """{id: seat table} for the realistic cast (blender/imported.py "seat")."""
    return {k: v["seat"] for k, v in blender3d.imported()["CHARACTERS"].items() if "seat" in v}


def render(perf, n_frames: int, faces: dict, shots: list, moods: list, out: Path,
           stage: str, draft: bool, placed: list | None = None, only: list | None = None) -> None:
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
    if only is not None:
        plan["only_shots"] = list(only)
    missing = [b for b in [plan["environment_blend"]] + [c["blend"] for c in plan["characters"]] if not Path(b).exists()]
    if missing:
        raise SystemExit(f"missing assets {missing}: run `reelforge build-assets --style shots-av`")
    plan_path = out / "render_plan.json"
    plan_text = json.dumps(plan)
    plan_path.write_text(plan_text, encoding="utf-8")
    target = out / ("frames" if stage == "full" else "stills")
    want = plan["n_frames"] if stage == "full" else len(only if only is not None else plan["shots"])
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


def _estimated(project: Path):
    """(perf, placed, n_frames, shots) from estimated timing (or timing.json): no voices needed."""
    from ..direct import plan_shots_av
    from ..schema import load_performance
    from ..timeline import Placed
    from ..voice import VoicedLine
    project = Path(project).resolve()
    perf = load_performance(project / "performance.json")
    tfile = project / "timing.json"
    timing = json.loads(tfile.read_text(encoding="utf-8")) if tfile.exists() else {}
    placed = []
    for l, (s0, d0) in zip(perf.lines, estimate_timing(perf.lines)):
        s0, d0 = timing.get(l.id, (s0, d0))
        placed.append(Placed(l, VoicedLine(l.id, project / "out" / "audio" / f"{l.id}.mp3",
                                           _fake_chars(l.text, 0.0, d0)), s0, d0))
    last = placed[-1]
    n_frames = math.ceil((last.start + last.duration + (3.0 if perf.end_text else 0.9)) * perf.fps)
    hero, buddy = cast(perf)
    shots = plan_shots_av(placed, perf.fps, n_frames, hero, buddy, reel_seed(perf, project),
                          perf.camera.get("grammar", "signature"), perf.camera)
    return perf, placed, n_frames, shots


# Render-time estimates for the editor, measured on the RTX 4060 laptop (P4/P5): seconds.
# Render cost tiers (render settings only, never the characters' geometry or textures). Measured 2026-11-13 on six
# frames of the owner's reel in av_editor_night, RTX 4060, against the 64-sample frames: Final 3.3 s/frame;
# Balanced 1.0 s/frame at SSIM 0.987 / PSNR 40 dB (faces match by eye; the lighter shadow sampling is the
# main saving, the coarser haze grid the second); 32 samples alone is 1.9 s/frame at SSIM 0.998.
# Draft (2026-11-14, eight frames of the P7 reel against the 16-sample draft): 8 samples and a coarser haze grid cut
# the per-frame time about 27% at SSIM 0.985; lighter shadow sampling was faster still but speckled the soft shadows
# (grain no denoise removed), so draft keeps full shadow quality.
TIERS = {"balanced": {"samples": 24, "shadow_rays": 2, "shadow_steps": 6, "vol_tile": 16, "vol_samples": 32},
         "draft": {"samples": 8, "vol_tile": 16, "vol_samples": 16}}
TIMING = {"preview_still_s": 15.0, "draft_s_per_frame": 0.27, "balanced_s_per_frame": 1.05, "final_s_per_frame": 3.3,
          "scene_load_s": 20.0}


def catalog() -> dict:
    """Everything the editor's Look column shows, read from the Blender tables (so the UI never drifts)."""
    h, b, r = hero_tables(), buddy_tables(), room_tables()
    hero = {k: {kk: vv for kk, vv in v.items()} for k, v in h["HERO"].items()}
    built = {"hero": any(ASSETS.glob("av_hero__*.blend")),
             "buddies": {f"buddy_{k}": buddy_blend(f"buddy_{k}").exists() for k in b["BUDDIES"]},
             "rooms": {k: room_blend(k).exists() for k in r["ROOMS"]},
             "people": {k: person_blend(k).exists() for k in imported_seats()}}
    return {
        "hero": hero, "skins": h["SKINS"], "outfits": {k: v["label"] for k, v in h["OUTFITS"].items()}, "outfitColors": h["OUTFIT_COLORS"],
        "brand": h["BRAND"],
        "buddies": [{"model": f"buddy_{k}", "label": v["label"], "readsAs": v["reads_as"], "shell": v["shell"],
                     "glow": v["glow"], "signature": v["signature"]} for k, v in b["BUDDIES"].items()],
        "rooms": [{"id": k, "label": v["label"], "tone": v["tone"], "look": v["look"], "gamer": bool(v.get("gamer")),
                   "classic": bool(v.get("legacy") or v.get("imported")),
                   "pano": _pano(k), "spots": r.get("VIEW_SPOTS", {}).get(k, [])} for k, v in r["ROOMS"].items()],
        "angles": [{"id": k, "role": a["role"], "label": a["label"]} for k, a in ANGLES.items()],
        "actions": list(acting.CLIPS), "built": built,
        "allBuilt": built["hero"] and all(built["buddies"].values()) and all(built["rooms"].values()),
        "timing": TIMING, "target": {"hero": 0.37, "buddy": 0.46, "wide": 0.17},
    }


def plan_for(project: Path) -> dict:
    from ..direct import screen_time
    perf, placed, n_frames, shots = _estimated(project)
    hero, buddy = cast(perf)
    line_of = {}
    for p in placed:
        line_of[p.line.id] = p
    out = []
    for i, s in enumerate(shots):
        lid = next((p.line.id for p in placed if int(round(p.start * perf.fps)) >= s.start_frame - 4
                    and int(round(p.start * perf.fps)) < s.end_frame), "")
        out.append({"index": i, "kind": s.kind, "start": s.start_frame / perf.fps, "end": s.end_frame / perf.fps,
                    "subject": "hero" if s.subject == hero else "buddy",
                    "speaker": "hero" if (s.speaker or s.subject) == hero else "buddy",
                    "move": s.move, "rack": bool(s.rack), "line": lid, "angle": s.angle})
    return {"shots": out, "runtime": n_frames / perf.fps, "frames": n_frames, "split": screen_time(shots),
            "target": {"hero": 0.37, "buddy": 0.46, "wide": 0.17}}


def preview_still(project: Path, index: int, draft: bool = True) -> Path:
    """One shot's still through the real render path, into <project>/out/preview/stills/shot_NN.png."""
    from ..direct import mood_keys
    from ..face import build_faces
    perf, placed, n_frames, shots = _estimated(project)
    if not 0 <= index < len(shots):
        raise SystemExit(f"shot {index} does not exist (the plan has {len(shots)} shots)")
    faces = build_faces(perf, placed, perf.fps, n_frames)
    out = Path(project).resolve() / "out" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    render(perf, n_frames, faces, shots, mood_keys(placed, perf.fps), out, "stills", draft, placed, only=[index])
    return out / "stills" / f"shot_{index:02d}.png"


LOOK_ANGLE = "hero_medium"  # waist-up: the face, the outfit and the room behind


def look_still(project: Path) -> Path:
    """The editor's look preview: a draft, waist-up still of whoever sits at the desk, in the project's room, with
    the current cast and outfit, through the real render path. Into <project>/out/look/stills/."""
    from dataclasses import replace as _replace
    from ..angles import framing as _framing
    from ..direct import mood_keys
    from ..face import build_faces
    from ..schema import load_performance
    if not load_performance(Path(project) / "performance.json").lines:
        raise SystemExit("Add a line to the script to preview the look.")
    perf, placed, n_frames, shots = _estimated(project)
    hero, _ = cast(perf)
    i = next((k for k, s in enumerate(shots) if s.subject == hero and s.kind in HERO_CU), 0)
    shots[i] = _replace(shots[i], kind="av_hero_34", subject=hero, speaker="", angle=LOOK_ANGLE,
                        framing=_framing(LOOK_ANGLE), move="static", connect={}, rack={}, handheld=0.0)
    faces = build_faces(perf, placed, perf.fps, n_frames)
    out = Path(project).resolve() / "out" / "look"
    out.mkdir(parents=True, exist_ok=True)
    render(perf, n_frames, faces, shots, mood_keys(placed, perf.fps), out, "stills", True, placed, only=[i])
    return out / "stills" / f"shot_{i:02d}.png"


THUMBS = ASSETS / "thumbs"


def _pano(room_id: str) -> dict | None:
    """The room's panorama for the editor's frame picker (blender/shotsav/room_pano.py), when it is rendered."""
    f = THUMBS / f"{room_id}_pano.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def reel_seed(perf, project) -> int:
    """camera.seed when the editor set one (Reroll angles), else one from the project folder's name: every project
    is shot differently, and the preview, the animatic and the render agree."""
    if "seed" in perf.camera:
        return int(perf.camera["seed"])
    return int(hashlib.sha1(Path(project).name.encode()).hexdigest()[:6], 16)


def thumbnails(only: list | None = None) -> list[str]:
    """Card images for the editor: one per buddy (a close single) and per room (a wide with the hero and Claude);
    outfit_<id>: the low-poly hero in that outfit; person_<id>: Matt, Freya or Mina. The last two are busts made by
    blender/preview_character.py and are only built when asked for (--only), not in a full pass."""
    ids = [f"buddy_{k}" for k in buddy_tables()["BUDDIES"]] + list(room_tables()["ROOMS"])
    ids = [i for i in ids if not only or i in only]
    THUMBS.mkdir(parents=True, exist_ok=True)
    if ids:
        run_blender(blender3d.BLENDER_DIR / "shotsav" / "thumbs.py", [str(THUMBS), *ids])
    made = [str(THUMBS / f"{i}.jpg") for i in ids]
    for i in only or []:
        blend = None
        if i.startswith("outfit_") and i[len("outfit_"):] in hero_tables()["OUTFITS"]:
            o = i[len("outfit_"):]
            blend = ensure_hero({"outfit": o, "outfit_color": hero_tables()["OUTFIT_COLORS"].get(o, "#7C3AED")})
        elif i.startswith("person_") and person_blend(i[len("person_"):]).exists():
            blend = person_blend(i[len("person_"):])
        if blend is None:
            continue
        png, jpg = THUMBS / f".{i}.png", THUMBS / f"{i}.jpg"
        run_blender(blender3d.BLENDER_DIR / "preview_character.py", [str(png), "yaw=20", "shot=bust"], blend=blend)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-vf", "scale=360:-2", "-q:v", "4", str(jpg)],
                       check=True)
        png.unlink(missing_ok=True)
        made.append(str(jpg))
    return made


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
    n_frames = math.ceil((last.start + last.duration + (3.0 if perf.end_text else 0.9)) * perf.fps)  # hold 0.9 s after the final word
    faces = build_faces(perf, placed, perf.fps, n_frames)
    hero, buddy = cast(perf)
    seed = reel_seed(perf, project)
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
