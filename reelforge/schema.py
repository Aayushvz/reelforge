from __future__ import annotations

import json
import re
from .angles import ANGLES
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
AV_PEOPLE = ("matt", "freya", "cute_girl")  # the realistic imported cast, seated at the desk in either slot
AV_YOU = (AV_HERO, *AV_PEOPLE)  # who can take the desk chair
AV_OTHER = (*AV_BUDDIES, *AV_PEOPLE)  # who can be the other speaker
AV_OUTFITS = ("puffer", "hoodie", "overshirt", "boxy_black", "hoodie_cargos", "knit_vest", "grey_sweats", "track_jacket", "puffer_vest", "camel_black", "techwear", "varsity", "cardigan", "tee_beanie", "flannel_layers", "cropped_knit", "blazer_mini", "baby_tee", "sporty_zip", "butterfly_top", "puffer_cream", "trench", "cargo_set", "sweater_beret")
# each ported outfit's own colour (blender/shotsav/hero.py OUTFIT_COLORS); the brand three default to purple
AV_OUTFIT_COLORS = {
    "boxy_black": "#1D1D22",
    "hoodie_cargos": "#56603F",
    "knit_vest": "#5C3B22",
    "grey_sweats": "#8D8D94",
    "track_jacket": "#1B2A57",
    "puffer_vest": "#141416",
    "camel_black": "#B08A5E",
    "techwear": "#2A2E28",
    "varsity": "#1C2F68",
    "cardigan": "#6B4426",
    "tee_beanie": "#1E2A3B",
    "flannel_layers": "#A6372F",
    "cropped_knit": "#E7DECF",
    "blazer_mini": "#4E4844",
    "baby_tee": "#C27A93",
    "sporty_zip": "#D96C8F",
    "butterfly_top": "#8B73C4",
    "puffer_cream": "#DCD3C0",
    "trench": "#8C6A44",
    "cargo_set": "#4A4F2C",
    "sweater_beret": "#CDBF9E",
}
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
AV_ROOMS = ("av_studio_night", "av_neon_den", "av_late_office", "av_studio_morning", "av_cafe_day", "av_cyc_lilac",
            "av_editor_night", "av_streamer_den", "av_neon_shelf", "av_moon_window", "av_retro_bedroom",
            "av_studio_apartment",
            # the old library's environments, now Shots-AV backdrops
            "av_old_night_city", "av_old_bedroom", "av_old_rooftop", "av_old_cafe", "av_old_lantern_street", "av_old_subway", "av_old_classroom", "av_old_office", "av_old_night_mart", "av_old_pier", "av_imp_neon_tunnel", "av_imp_gaming_den", "av_imp_cozy_gaming_room")
AV_ANGLE_MODES = ("varied", "classic")  # camera.angles: the 36-angle library, or the reference reel's five set-ups
_HEX = re.compile(r"#[0-9a-fA-F]{6}")


class PerformanceError(ValueError):
    pass


@dataclass(frozen=True)
class Character:
    name: str
    voice_id: str
    caption_color: str
    highlight_color: str
    model: str = "matt"  # cast member the engine renders
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
    end_text: str = ""  # shots-av: an end card over the closing wide ("Every designer's relationship with AI.")
    room_view: dict = field(default_factory=dict)  # shots-av: {"pan", "height", "turn"} each -1..1; empty = picked


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
                                c.get("highlight_color", "#FFD23F"), c.get("model", "matt"), outfit)
    if not chars:
        errors.append("at least one character required")
    if len(chars) > MAX_CHARACTERS:
        errors.append(f"at most {MAX_CHARACTERS} characters (one per mark), got {len(chars)}")
    if av and data.get("environment", AV_ROOM) not in AV_ROOMS:
        errors.append(f"shots-av environment must be one of {AV_ROOMS}, got {data.get('environment')!r}")
    if av:
        models = [c.model for c in chars.values()]
        ok = len(models) == 2 and ((models[0] in AV_YOU and models[1] in AV_OTHER)
                                    or (models[1] in AV_YOU and models[0] in AV_OTHER))
        if not ok:
            errors.append(f"shots-av needs two speakers: one at the desk (model one of {AV_YOU}) and one more "
                          f"(model one of {AV_OTHER}), got models {sorted(models)}")

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
        elif action and av and raw["speaker"] in chars and chars[raw["speaker"]].model not in AV_BUDDIES:
            errors.append(f"{where}: action is a buddy clip; only a bot buddy's line can carry one")
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
    if "connect" in camera and not isinstance(camera["connect"], bool):
        errors.append("camera.connect must be true or false")
    drift = camera.get("drift", 1.0)
    if isinstance(drift, bool) or not isinstance(drift, (int, float)) or not 0.0 <= drift <= 2.0:
        errors.append("camera.drift must be a number 0..2")
    captions, sound = data.get("captions") or {}, data.get("sound") or {}
    if not isinstance(captions, dict) or not isinstance(sound, dict):
        errors.append("captions and sound must be objects")
        captions, sound = {}, {}
    if "style" in captions and not isinstance(captions["style"], dict):
        errors.append("captions.style must be an object (the editor's subtitle style)")
    if captions.get("position", "top") not in ("top", "lower", "custom"):
        errors.append("captions.position must be top, lower or custom")
    for key, lo, hi in (("x", 0.0, 1.0), ("y", 0.0, 1.0), ("size", 0.5, 2.0)):
        v = captions.get(key)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi):
            errors.append(f"captions.{key} must be a number {lo}..{hi}")
    if camera.get("angles", "varied") not in AV_ANGLE_MODES:
        errors.append(f"camera.angles must be one of {AV_ANGLE_MODES}")
    room_view = data.get("room_view") or {}
    if not isinstance(room_view, dict):
        errors.append("room_view must be an object")
        room_view = {}
    for key, v in room_view.items():
        if key not in ("pan", "height", "turn") or isinstance(v, bool) or not isinstance(v, (int, float))                 or not -1.0 <= v <= 1.0:
            errors.append(f"room_view.{key}: only pan, height and turn, each a number -1..1")
    for key, val in (("captions.plate", captions.get("plate", True)), ("captions.tint", captions.get("tint", True)),
                     ("sound.foley", sound.get("foley", True))):
        if not isinstance(val, bool):
            errors.append(f"{key} must be true or false")
    end_text = data.get("end_text", "")
    if not isinstance(end_text, str) or len(end_text) > 120:
        errors.append("end_text must be text of at most 120 characters")
        end_text = ""
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
        if "angle" in o and o["angle"] not in ANGLES:
            errors.append(f"{where}: angle must be one of the library's {len(ANGLES)} angles")
        if "subject" in o and o["subject"] not in chars:
            errors.append(f"{where}: unknown subject {o['subject']}")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in look_params.values()):
        errors.append("look_params values must be numbers")
    if errors:
        raise PerformanceError("; ".join(errors))
    return Performance(fps, ratio, data.get("environment", AV_ROOM if av else "night_city"), chars, lines,
                       style, data.get("lighting", ""),
                       bool(data.get("ambience", True)), look, quality, camera, look_params, captions, sound,
                       end_text.strip(), room_view)


def _av_options(name: str, c: dict, errors: list[str]) -> dict:
    """The shots-av hero's named wardrobe and accessories; a buddy has none."""
    if c.get("model") != AV_HERO:
        return {}
    outfit = c.get("outfit", AV_OUTFITS[0])
    opts = {"outfit": outfit, "outfit_color": c.get("outfit_color", AV_OUTFIT_COLORS.get(outfit, AV_PURPLE)),
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
