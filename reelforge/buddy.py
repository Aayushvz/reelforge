"""Acting for the Shots-AV desk buddies (stdlib only). Produces per-frame values for the BuddyCtrl props of
blender/shotsav/buddies.py: talk squash from the dialogue's loudness, idle breathing, blinks, glances at the hero,
and eight named reaction clips.

Sign convention: lean_x and eye_look_x are written "toward the hero = positive" in the clips and the idle life;
animate() multiplies them by hero_side (+1 if the hero is at the buddy's +X, else -1).
"""
from __future__ import annotations

import array
import math
import random
import wave
from pathlib import Path

CONTROLS = ("squash", "lean_x", "lean_y", "hop", "eye_h", "eye_shape", "eye_look_x", "eye_look_y", "glow", "sig",
            "phase")
REST = {c: 0.0 for c in CONTROLS} | {"eye_h": 1.0}
EYE_SHAPES = ("rect", "happy", "sad", "wide", "wink")
TOWARD_HERO = {"lean_x", "eye_look_x"}
STEPPED = {"eye_shape"}  # an index: blending 0 -> 2 would flash through 1, so it switches on a frame
MULTIPLY = {"eye_h"}  # clip values scale the idle value (so blinks still close a dry, half-shut eye)

# Reaction clips: keys per control as (frame, value); `hold` keeps the last values until the line ends, then they
# release over RELEASE frames. `peak` is the frame the evidence sheet shows.
CLIPS: dict[str, dict] = {
    "hop": {"len": 16, "hold": False, "peak": 8, "keys": {
        "squash": [(0, 0.0), (3, 0.18), (5, -0.08), (11, -0.04), (13, 0.15), (16, 0.0)],
        "hop": [(0, 0.0), (4, 0.0), (8, 1.0), (12, 0.0), (16, 0.0)],
        "lean_x": [(0, 0.0), (6, 0.35), (16, 0.15)],
        "eye_shape": [(0, 0), (4, 3), (13, 0)]}},
    "tilt": {"len": 14, "hold": True, "peak": 12, "keys": {
        "lean_x": [(0, 0.0), (6, 0.42), (14, 0.36)],
        "eye_look_y": [(0, 0.0), (8, 0.3)]}},
    "dry": {"len": 10, "hold": True, "peak": 8, "keys": {
        "eye_h": [(0, 1.0), (4, 0.35)],
        "squash": [(0, 0.0), (4, 0.03)]}},
    "happy": {"len": 14, "hold": True, "peak": 4, "keys": {
        "eye_shape": [(0, 0), (2, 1)],
        "hop": [(0, 0.0), (4, 0.25), (8, 0.0), (11, 0.12), (14, 0.0)],
        "squash": [(0, 0.0), (2, 0.1), (4, -0.05), (8, 0.08), (10, 0.0)],
        "glow": [(0, 0.0), (4, 0.6), (14, 0.3)]}},
    "think": {"len": 18, "hold": True, "peak": 14, "keys": {
        "eye_look_x": [(0, 0.0), (8, -0.6)],
        "eye_look_y": [(0, 0.0), (8, 0.7)],
        "lean_x": [(0, 0.0), (10, -0.18)],
        "eye_h": [(0, 1.0), (6, 0.8)],
        "sig": [(0, 0.0), (6, 1.0)]}},
    "shrink": {"len": 12, "hold": True, "peak": 10, "keys": {
        "squash": [(0, 0.0), (6, 0.22), (12, 0.17)],
        "eye_h": [(0, 1.0), (6, 0.75)],
        "eye_shape": [(0, 0), (5, 2)],
        "lean_y": [(0, 0.0), (8, -0.25)]}},
    "nod": {"len": 16, "hold": False, "peak": 4, "keys": {
        "lean_y": [(0, 0.0), (4, 0.4), (8, 0.0), (12, 0.28), (16, 0.0)],
        "squash": [(0, 0.0), (4, 0.06), (8, 0.0), (12, 0.04), (16, 0.0)]}},
    "lookaway": {"len": 14, "hold": True, "peak": 12, "keys": {
        "eye_look_x": [(0, 0.0), (6, -0.9)],
        "lean_x": [(0, 0.0), (10, -0.15)],
        "eye_h": [(0, 1.0), (6, 0.85)]}},
}
EMOTION_ACTIONS = {"happy": "happy", "surprised": "hop", "sad": "shrink", "worried": "shrink",
                   "embarrassed": "lookaway", "confused": "tilt", "thinking": "think", "annoyed": "dry",
                   "deadpan": "dry", "smug": "tilt", "neutral": "nod"}
RELEASE = 6
TALK_ATTACK, TALK_RELEASE = 2.0, 5.0  # frames
TALK_MIN, TALK_MAX = 0.03, 0.06  # body squash while speaking: 3-6% of its height


def pick_action(text: str, emotion: str = "neutral", intensity: float = 0.5, action: str = "") -> str:
    """The reaction clip for a buddy line: an explicit action wins, then punctuation, then intensity, then emotion."""
    if action:
        if action not in CLIPS:
            raise ValueError(f"unknown buddy action {action!r}; known: {', '.join(CLIPS)}")
        return action
    t = text.strip()
    if t.endswith("!"):
        return "hop"
    if t.endswith("...") or t.endswith("…"):
        return "think"
    if intensity < 0.3:
        return "dry"
    return EMOTION_ACTIONS.get(emotion, "")


def clip_value(name: str, control: str, f: float) -> float | None:
    """A clip's value for one control at frame f (from the clip's start), or None if the clip leaves it alone.
    Past the last key the last value holds; callers decide when a held clip releases."""
    keys = CLIPS[name]["keys"].get(control)
    if not keys:
        return None
    if f <= keys[0][0]:
        return float(keys[0][1])
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f < f1:
            if control in STEPPED:
                return float(v0)
            a = (f - f0) / (f1 - f0)
            a = a * a * (3 - 2 * a)  # eased between keys: clips are poses, not linear drifts
            return v0 + (v1 - v0) * a
    return float(keys[-1][1])


def wav_envelope(path: str | Path, fps: int) -> list[float]:
    """RMS loudness per video frame of a 16-bit PCM WAV, normalised so the loudest frame is 1."""
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"{path}: expected 16-bit PCM")
        ch, rate, n = w.getnchannels(), w.getframerate(), w.getnframes()
        data = array.array("h", w.readframes(n))
    mono = data[::ch] if ch > 1 else data
    hop = rate / fps
    out = []
    for i in range(math.ceil(len(mono) / hop - 1e-6)):  # float hop: 16000/30 must still give 30 frames
        chunk = mono[int(i * hop):int((i + 1) * hop)]
        out.append(math.sqrt(sum(s * s for s in chunk) / max(1, len(chunk))))
    top = max(out, default=0.0)
    return [v / top for v in out] if top > 0 else out


def syllable_envelope(text: str, fps: int, syllables_per_s: float = 4.6, seed: int = 7) -> list[float]:
    """A deterministic stand-in loudness envelope for a line with no audio yet (previews and evidence only):
    one bump per vowel group, louder on stressed-looking syllables, small gaps at spaces and commas."""
    rng = random.Random(f"{seed}:{text}")
    groups, prev_vowel = [], False
    for ch in text.lower():
        vowel = ch in "aeiouy"
        if vowel and not prev_vowel:
            groups.append("v")
        elif ch in ",.;:!?" and groups:
            groups.append("pause")
        prev_vowel = vowel
    env: list[float] = []
    step = fps / syllables_per_s
    for g in groups:
        n = max(2, round(step * (1.6 if g == "pause" else rng.uniform(0.8, 1.2))))
        peak = 0.0 if g == "pause" else rng.uniform(0.55, 1.0)
        env += [peak * math.sin(math.pi * (i + 0.5) / n) ** 0.7 for i in range(n)]
    return env


def follow(values: list[float], attack: float = TALK_ATTACK, release: float = TALK_RELEASE) -> list[float]:
    """One-pole follower: rises with time constant `attack` frames, falls with `release` frames."""
    ka, kr = 1 - math.exp(-1 / attack), 1 - math.exp(-1 / release)
    x, out = 0.0, []
    for v in values:
        x += (v - x) * (ka if v > x else kr)
        out.append(x)
    return out


def talk_squash(env: list[float]) -> list[float]:
    """Body squash from loudness: 3% on quiet syllables up to 6% on the loudest, nothing in silence."""
    out = []
    for x in follow(env):
        out.append(0.0 if x < 0.04 else TALK_MIN + (TALK_MAX - TALK_MIN) * min(1.0, x))
    return out


def blink_frames(n_frames: int, fps: int, seed: int = 7) -> list[int]:
    """Blink start frames every 2.8-4.2 s (seeded)."""
    rng, out = random.Random(seed), []
    f = rng.uniform(0.6, 2.0) * fps
    while f < n_frames:
        out.append(int(f))
        f += rng.uniform(2.8, 4.2) * fps
    return out


BLINK = (1.0, 0.45, 0.0, 0.0, 0.45, 1.0)  # eye_h multiplier over 6 frames


def animate(n_frames: int, fps: int, segments: list[dict], seed: int = 7, hero_side: float = 1.0) -> dict:
    """Per-frame BuddyCtrl values.

    segments: [{"start": frame, "end": frame, "speaking": bool, "env": [loudness per frame] or None,
                "action": clip name or ""}], in time order. A speaking segment without env is silent squash-wise.
    """
    tr = {c: [REST[c]] * n_frames for c in CONTROLS}
    talk = [0.0] * n_frames
    loud = [0.0] * n_frames
    for s in segments:
        if s.get("speaking") and s.get("env"):
            for i, v in enumerate(s["env"]):
                if s["start"] + i < min(s["end"], n_frames):
                    loud[s["start"] + i] = v
    squash_talk = talk_squash(loud)
    level = follow([1.0 if v > 0.08 else 0.0 for v in follow(loud, 2, 8)], 6, 14)  # talking at all, smoothed
    glance_rng = random.Random(seed + 1)
    glances = []  # idle looks at the hero: (start, length)
    f = glance_rng.uniform(1.5, 2.5) * fps
    while f < n_frames:
        glances.append((int(f), int(glance_rng.uniform(0.8, 1.3) * fps)))
        f += glance_rng.uniform(3.5, 5.0) * fps
    for f in range(n_frames):
        breath = math.sin(2 * math.pi * f / (fps * 3.0) + seed)
        talk[f] = level[f]
        tr["squash"][f] = 0.008 * breath + squash_talk[f]
        tr["lean_x"][f] = 0.10 * level[f]  # lean toward the hero while talking
        tr["sig"][f] = level[f]
        tr["glow"][f] = 0.25 * level[f]
        for g0, gl in glances:
            if g0 <= f < g0 + gl:
                x = (f - g0) / gl
                tr["eye_look_x"][f] = 0.7 * math.sin(math.pi * min(1.0, x * 1.6)) ** 0.5 * (1 - level[f])
    for s in segments:  # reaction clips
        name = s.get("action") or ""
        if not name:
            continue
        clip = CLIPS[name]
        end = min(n_frames, s["end"] + (RELEASE if clip["hold"] else 0))
        for f in range(s["start"], end):
            local = f - s["start"]
            if not clip["hold"] and local > clip["len"]:
                break
            fade = 1.0
            if clip["hold"] and f >= s["end"]:
                fade = 1 - (f - s["end"] + 1) / (RELEASE + 1)
            for c in clip["keys"]:
                v = clip_value(name, c, local)
                if c in STEPPED:
                    tr[c][f] = v if fade > 0.5 else REST[c]
                elif c in MULTIPLY:
                    tr[c][f] *= 1 + (v - 1) * fade
                else:
                    tr[c][f] += v * fade
    for b in blink_frames(n_frames, fps, seed):
        for i, m in enumerate(BLINK):
            if b + i < n_frames:
                tr["eye_h"][b + i] *= m
    phase = 0.0
    for f in range(n_frames):  # the signature motion's running angle: faster while talking or thinking
        phase += 0.04 + 0.22 * min(1.0, tr["sig"][f])
        tr["phase"][f] = phase
    for c in TOWARD_HERO:
        tr[c] = [v * hero_side for v in tr[c]]
    for c in CONTROLS:
        tr[c] = [round(v, 5) for v in tr[c]]
    return tr
