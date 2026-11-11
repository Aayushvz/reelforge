from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

EMOTIONS = ("neutral", "happy", "sad", "worried", "surprised", "smug", "deadpan",
            "confused", "annoyed", "thinking", "embarrassed")
MOODS = ("calm", "success", "panic", "awkward", "reveal", "sad")
RATIOS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920), "16:9": (1920, 1080), "3:4": (1080, 1440), "1:1": (1080, 1080),
}
REQUIRED_LINE_KEYS = ("id", "speaker", "text", "emotion", "intensity", "mood")
MAX_CHARACTERS = 2  # one per mark (Mark_A, Mark_B)
LOOKS = ("classic", "cinema")  # classic = the original Eevee look; cinema = Cycles faces + the camera rig
QUALITIES = ("preview", "standard", "cinema")
CAMERA_MOVES = ("static", "push_in", "pull_out", "orbit", "truck", "drift", "crane_down", "crane_up",
                "slow_zoom", "whip_pan")
SHOT_KINDS = ("wide", "medium", "closeup", "ecu")


class PerformanceError(ValueError):
    pass


@dataclass(frozen=True)
class Character:
    name: str
    voice_id: str
    caption_color: str
    highlight_color: str
    model: str = "kai"  # cast member the engine renders
    outfit: int = 0  # index into that member's wardrobe


@dataclass(frozen=True)
class Line:
    id: str
    speaker: str
    text: str
    emotion: str
    intensity: float
    mood: str
    pause_after: float = 0.3
    punchline: bool = False


@dataclass(frozen=True)
class Performance:
    fps: int
    ratio: str
    environment: str
    characters: dict[str, Character]
    lines: list[Line]
    style: str = "blender3d"
    lighting: str = ""  # preset of the environment; empty = the set's default
    ambience: bool = True  # procedural room tone / weather bed under the dialogue
    look: str = "classic"  # render look of the blender3d engine (LOOKS)
    quality: str = "standard"  # preview | standard | cinema (cinema look only; --draft forces preview)
    camera: dict = field(default_factory=dict)  # cinema look: {seed, handheld, overrides: {"<shot>": {...}}}
    look_params: dict = field(default_factory=dict)  # per-look number dials, e.g. {"skin_glow": 1.0}


def load_performance(path: Path) -> Performance:
    return parse_performance(json.loads(Path(path).read_text(encoding="utf-8")))


def parse_performance(data: dict) -> Performance:
    errors: list[str] = []
    fps = data.get("fps", 30)
    if fps not in (24, 25, 30, 60):
        errors.append(f"fps must be 24/25/30/60, got {fps}")
    ratio = data.get("ratio", "9:16")
    if ratio not in RATIOS:
        errors.append(f"ratio must be one of {list(RATIOS)}, got {ratio}")

    chars: dict[str, Character] = {}
    for name, c in (data.get("characters") or {}).items():
        if "voice_id" not in c:
            errors.append(f"character {name}: missing voice_id")
            continue
        chars[name] = Character(name, c["voice_id"], c.get("caption_color", "#FFFFFF"),
                                c.get("highlight_color", "#FFD23F"), c.get("model", "kai"),
                                int(c.get("outfit", 0)))
    if not chars:
        errors.append("at least one character required")
    if len(chars) > MAX_CHARACTERS:
        errors.append(f"at most {MAX_CHARACTERS} characters (one per mark), got {len(chars)}")

    lines: list[Line] = []
    seen: set[str] = set()
    for i, raw in enumerate(data.get("lines") or []):
        where = f"lines[{i}]"
        missing = [k for k in REQUIRED_LINE_KEYS if k not in raw]
        if missing:
            errors.append(f"{where}: missing {missing}")
            continue
        if raw["id"] in seen:
            errors.append(f"{where}: duplicate id {raw['id']}")
        seen.add(raw["id"])
        if raw["speaker"] not in chars:
            errors.append(f"{where}: unknown speaker {raw['speaker']}")
        if raw["emotion"] not in EMOTIONS:
            errors.append(f"{where}: emotion must be one of {EMOTIONS}")
        if raw["mood"] not in MOODS:
            errors.append(f"{where}: mood must be one of {MOODS}")
        try:
            intensity, pause = float(raw["intensity"]), float(raw.get("pause_after", 0.3))
        except (TypeError, ValueError):
            errors.append(f"{where}: intensity and pause_after must be numbers")
            continue
        if not 0.0 <= intensity <= 1.0:
            errors.append(f"{where}: intensity must be 0..1")
        if pause < 0:
            errors.append(f"{where}: pause_after must be >= 0")
        lines.append(Line(raw["id"], raw["speaker"], raw["text"], raw["emotion"], intensity,
                          raw["mood"], pause, bool(raw.get("punchline", False))))
    if not lines:
        errors.append("at least one line required")
    look, quality = data.get("look", "classic"), data.get("quality", "standard")
    if look not in LOOKS:
        errors.append(f"look must be one of {LOOKS}, got {look}")
    if quality not in QUALITIES:
        errors.append(f"quality must be one of {QUALITIES}, got {quality}")
    camera, look_params = data.get("camera") or {}, data.get("look_params") or {}
    if not isinstance(camera, dict) or not isinstance(look_params, dict):
        errors.append("camera and look_params must be objects")
        camera, look_params = {}, {}
    handheld = camera.get("handheld", 0.15)
    if isinstance(handheld, bool) or not isinstance(handheld, (int, float)) or not 0.0 <= handheld <= 1.0:
        errors.append("camera.handheld must be a number 0..1")
    overrides = camera.get("overrides") or {}
    for key, o in (overrides.items() if isinstance(overrides, dict) else []):
        where = f"camera.overrides[{key}]"
        if not str(key).isdigit() or not isinstance(o, dict):
            errors.append(f"{where}: the key must be a shot index and the value an object")
            continue
        if "move" in o and o["move"] not in CAMERA_MOVES:
            errors.append(f"{where}: move must be one of {CAMERA_MOVES}")
        if "kind" in o and o["kind"] not in SHOT_KINDS:
            errors.append(f"{where}: kind must be one of {SHOT_KINDS}")
        if "subject" in o and o["subject"] not in chars:
            errors.append(f"{where}: unknown subject {o['subject']}")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in look_params.values()):
        errors.append("look_params values must be numbers")
    if errors:
        raise PerformanceError("; ".join(errors))
    return Performance(fps, ratio, data.get("environment", "night_city"), chars, lines,
                       data.get("style", "blender3d"), data.get("lighting", ""),
                       bool(data.get("ambience", True)), look, quality, camera, look_params)
