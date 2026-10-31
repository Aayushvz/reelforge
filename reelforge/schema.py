from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

EMOTIONS = ("neutral", "happy", "sad", "worried", "surprised", "smug", "deadpan",
            "confused", "annoyed", "thinking", "embarrassed")
MOODS = ("calm", "success", "panic", "awkward", "reveal", "sad")
RATIOS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920), "16:9": (1920, 1080), "3:4": (1080, 1440), "1:1": (1080, 1080),
}
REQUIRED_LINE_KEYS = ("id", "speaker", "text", "emotion", "intensity", "mood")


class PerformanceError(ValueError):
    pass


@dataclass(frozen=True)
class Character:
    name: str
    voice_id: str
    caption_color: str
    highlight_color: str


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
                                c.get("highlight_color", "#FFD23F"))
    if not chars:
        errors.append("at least one character required")

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
        intensity = float(raw["intensity"])
        if not 0.0 <= intensity <= 1.0:
            errors.append(f"{where}: intensity must be 0..1")
        lines.append(Line(raw["id"], raw["speaker"], raw["text"], raw["emotion"], intensity,
                          raw["mood"], float(raw.get("pause_after", 0.3)),
                          bool(raw.get("punchline", False))))
    if not lines:
        errors.append("at least one line required")
    if errors:
        raise PerformanceError("; ".join(errors))
    return Performance(fps, ratio, data.get("environment", "night_city"), chars, lines)
