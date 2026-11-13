from __future__ import annotations

import json
import re
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
LOOKS = ("classic", "cinema", "shotsav")  # classic = the original Eevee look; cinema = Cycles faces + the
# camera rig; shotsav = the low-poly desk two-hander of the shots-av style
QUALITIES = ("preview", "standard", "cinema")
CAMERA_MOVES = ("static", "push_in", "pull_out", "pull_truck", "orbit", "truck", "drift", "crane_down", "crane_up",
                "slow_zoom", "whip_pan")
SHOT_KINDS = ("wide", "two", "medium", "closeup", "ecu",
              "av_hero_34", "av_hero_front", "av_buddy", "av_wide_34", "av_wide_front")  # av_*: the shots-av set-ups
# --- the shots-av style (docs/prompts/03-shots-av-animation.md): one hero and one desk buddy ---
AV_STYLE = "shots-av"
AV_HERO = "av_hero"
AV_BUDDIES = ("buddy_claude", "buddy_chatgpt", "buddy_figma", "buddy_nova")
AV_OUTFITS = ("puffer", "hoodie", "overshirt")
AV_GLASSES = ("bold", "round", "rect", "none")  # bold: the owner's black acetate frames
AV_HEADPHONES = ("on", "neck", "none")
# Skin and hair are the viewer's pick in the editor (owner decision, gate P1); the first entry is the default.
AV_SKINS = ("wheat", "porcelain", "light", "tan", "warm_brown", "brown", "deep")  # wheat: the owner's tone
AV_HAIRS = ("fringe", "soft_fringe", "curtain", "swept", "curly_top", "buzz")  # fringe: the owner's hair
AV_BEARDS = ("light", "stubble", "none")  # light: thin moustache and chin beard
AV_GRAMMARS = ("signature", "reference")  # signature (default) = the reference grammar plus our upgrades
AV_ACTIONS = ("hop", "tilt", "dry", "happy", "think", "shrink", "nod", "lookaway")  # buddy reaction clips
AV_PURPLE = "#7C3AED"  # Aayush Visuals brand purple: the default jacket
AV_ROOM = "av_studio_night"
AV_ROOMS = ("av_studio_night", "av_neon_den", "av_late_office", "av_studio_morning", "av_cafe_day", "av_cyc_lilac")
_HEX = re.compile(r"#[0-9a-fA-F]{6}")


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
    options: dict = field(default_factory=dict)  # shots-av hero: outfit (name), outfit_color, glasses, headphones


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
    beat: bool = False  # shots-av: force a wide on this line
    action: str = ""  # shots-av: a buddy reaction clip (AV_ACTIONS); empty = picked from the line


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
    captions: dict = field(default_factory=dict)  # shots-av: {"position": "top"|"lower", "plate": bool, "tint": bool}
    sound: dict = field(default_factory=dict)  # shots-av: {"foley": bool}


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

    style = data.get("style", "blender3d")
    av = style == AV_STYLE
    chars: dict[str, Character] = {}
    for name, c in (data.get("characters") or {}).items():
        if av:  # voices come from the web app, so voice_id is optional; the hero's wardrobe is named, not indexed
            chars[name] = Character(name, c.get("voice_id", ""), c.get("caption_color", "#FFFFFF"),
                                    c.get("highlight_color", "#FFD23F"), c.get("model", ""), 0,
                                    _av_options(name, c, errors))
            continue
        if "voice_id" not in c:
            errors.append(f"character {name}: missing voice_id")
            continue
        try:
            outfit = int(c.get("outfit", 0))
        except (TypeError, ValueError):
            errors.append(f"character {name}: outfit must be a wardrobe index, got {c.get('outfit')!r}")
            continue
        chars[name] = Character(name, c["voice_id"], c.get("caption_color", "#FFFFFF"),
                                c.get("highlight_color", "#FFD23F"), c.get("model", "kai"), outfit)
    if not chars:
        errors.append("at least one character required")
    if len(chars) > MAX_CHARACTERS:
        errors.append(f"at most {MAX_CHARACTERS} characters (one per mark), got {len(chars)}")
    if av and data.get("environment", AV_ROOM) not in AV_ROOMS:
        errors.append(f"shots-av environment must be one of {AV_ROOMS}, got {data.get('environment')!r}")
    if av:
        models = sorted(c.model for c in chars.values())
        if len(models) != 2 or models[0] != AV_HERO or models[1] not in AV_BUDDIES:
            errors.append(f"shots-av needs exactly one hero (model {AV_HERO!r}) and one buddy "
                          f"(model one of {AV_BUDDIES}), got models {models}")

    lines: list[Line] = []
    seen: set[str] = set()
    for i, raw in enumerate(data.get("lines") or []):
        where = f"lines[{i}]"
        if av and isinstance(raw, dict):  # a chat-style script: only speaker and text are required
            raw = {"id": f"l{i + 1:02d}", "emotion": "neutral", "intensity": 0.5, "mood": "calm", **raw}
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
        beat, action = raw.get("beat", False), raw.get("action", "")
        if not isinstance(beat, bool):
            errors.append(f"{where}: beat must be true or false")
        if action not in ("", *AV_ACTIONS):
            errors.append(f"{where}: action must be empty or one of {AV_ACTIONS}")
        elif action and av and raw["speaker"] in chars and chars[raw["speaker"]].model == AV_HERO:
            errors.append(f"{where}: action is a buddy clip; the hero's line cannot carry one")
        lines.append(Line(raw["id"], raw["speaker"], raw["text"], raw["emotion"], intensity,
                          raw["mood"], pause, bool(raw.get("punchline", False)), beat is True, action))
    if not lines:
        errors.append("at least one line required")
    look, quality = data.get("look", "shotsav" if av else "classic"), data.get("quality", "standard")
    if look not in LOOKS:
        errors.append(f"look must be one of {LOOKS}, got {look}")
    if quality not in QUALITIES:
        errors.append(f"quality must be one of {QUALITIES}, got {quality}")
    camera, look_params = data.get("camera") or {}, data.get("look_params") or {}
    if not isinstance(camera, dict) or not isinstance(look_params, dict):
        errors.append("camera and look_params must be objects")
        camera, look_params = {}, {}
    if "rack" in camera and not isinstance(camera["rack"], bool):
        errors.append("camera.rack must be true or false")
    drift = camera.get("drift", 1.0)
    if isinstance(drift, bool) or not isinstance(drift, (int, float)) or not 0.0 <= drift <= 2.0:
        errors.append("camera.drift must be a number 0..2")
    captions, sound = data.get("captions") or {}, data.get("sound") or {}
    if not isinstance(captions, dict) or not isinstance(sound, dict):
        errors.append("captions and sound must be objects")
        captions, sound = {}, {}
    if "style" in captions and not isinstance(captions["style"], dict):
        errors.append("captions.style must be an object (the editor's subtitle style)")
    if captions.get("position", "top") not in ("top", "lower"):
        errors.append("captions.position must be top or lower")
    for key, val in (("captions.plate", captions.get("plate", True)), ("captions.tint", captions.get("tint", True)),
                     ("sound.foley", sound.get("foley", True))):
        if not isinstance(val, bool):
            errors.append(f"{key} must be true or false")
    handheld = camera.get("handheld", 0.15)
    if isinstance(handheld, bool) or not isinstance(handheld, (int, float)) or not 0.0 <= handheld <= 1.0:
        errors.append("camera.handheld must be a number 0..1")
    if "grammar" in camera and camera["grammar"] not in AV_GRAMMARS:
        errors.append(f"camera.grammar must be one of {AV_GRAMMARS}")
    if av and "seed" in camera and (isinstance(camera["seed"], bool) or not isinstance(camera["seed"], int)):
        errors.append("camera.seed must be a whole number")
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
    return Performance(fps, ratio, data.get("environment", AV_ROOM if av else "night_city"), chars, lines,
                       style, data.get("lighting", ""),
                       bool(data.get("ambience", True)), look, quality, camera, look_params, captions, sound)


def _av_options(name: str, c: dict, errors: list[str]) -> dict:
    """The shots-av hero's named wardrobe and accessories; a buddy has none."""
    if c.get("model") != AV_HERO:
        return {}
    opts = {"outfit": c.get("outfit", AV_OUTFITS[0]), "outfit_color": c.get("outfit_color", AV_PURPLE),
            "glasses": c.get("glasses", AV_GLASSES[0]), "headphones": c.get("headphones", "neck"),
            "skin": c.get("skin", AV_SKINS[0]), "hair": c.get("hair", AV_HAIRS[0]), "beard": c.get("beard", AV_BEARDS[0]),
            "stubble": c.get("stubble", 0.3)}
    for key, allowed in (("outfit", AV_OUTFITS), ("glasses", AV_GLASSES), ("headphones", AV_HEADPHONES),
                         ("skin", AV_SKINS), ("hair", AV_HAIRS), ("beard", AV_BEARDS)):
        if opts[key] not in allowed:
            errors.append(f"character {name}: {key} must be one of {allowed}, got {opts[key]!r}")
    if not isinstance(opts["outfit_color"], str) or not _HEX.fullmatch(opts["outfit_color"]):
        errors.append(f"character {name}: outfit_color must be a hex colour like {AV_PURPLE}")
    s = opts["stubble"]
    if isinstance(s, bool) or not isinstance(s, (int, float)) or not 0.0 <= s <= 1.0:
        errors.append(f"character {name}: stubble must be a number 0..1")
    else:
        opts["stubble"] = float(s)
    return opts
