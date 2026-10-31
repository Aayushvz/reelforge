from __future__ import annotations

import math
import random

from .alignment import words_from_chars
from .arkit import ARKIT_NAMES
from .schema import Performance
from .timeline import Placed
from .visemes import sample_tracks, viseme_events

ANTICIPATION = 0.15  # emotion starts slightly before the line
NERVOUS = {"worried", "embarrassed"}
BLINK_SHAPE = (0.5, 1.0, 1.0, 0.6, 0.2)

EMOTION_POSES: dict[str, dict[str, float]] = {
    "neutral": {},
    "happy": {"mouthSmileLeft": 0.6, "mouthSmileRight": 0.6, "cheekSquintLeft": 0.35,
              "cheekSquintRight": 0.35, "browInnerUp": 0.1},
    "sad": {"browInnerUp": 0.7, "mouthFrownLeft": 0.5, "mouthFrownRight": 0.5,
            "eyeSquintLeft": 0.1, "eyeSquintRight": 0.1},
    "worried": {"browInnerUp": 0.6, "mouthStretchLeft": 0.2, "mouthStretchRight": 0.2,
                "mouthFrownLeft": 0.2, "mouthFrownRight": 0.2},
    "surprised": {"browOuterUpLeft": 0.8, "browOuterUpRight": 0.8, "browInnerUp": 0.6,
                  "eyeWideLeft": 0.7, "eyeWideRight": 0.7, "jawOpen": 0.15},
    "smug": {"mouthSmileLeft": 0.55, "mouthSmileRight": 0.1, "browDownRight": 0.3,
             "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3},
    "deadpan": {"eyeBlinkLeft": 0.35, "eyeBlinkRight": 0.35, "mouthPressLeft": 0.2,
                "mouthPressRight": 0.2},
    "confused": {"browDownLeft": 0.5, "browOuterUpRight": 0.6, "mouthLeft": 0.3},
    "annoyed": {"browDownLeft": 0.6, "browDownRight": 0.6, "mouthPressLeft": 0.4,
                "mouthPressRight": 0.4, "noseSneerLeft": 0.2, "noseSneerRight": 0.2},
    "thinking": {"browDownLeft": 0.3, "browInnerUp": 0.3, "mouthRight": 0.3,
                 "eyeLookUpLeft": 0.4, "eyeLookUpRight": 0.4},
    "embarrassed": {"mouthSmileLeft": 0.3, "mouthSmileRight": 0.3, "browInnerUp": 0.4,
                    "eyeLookDownLeft": 0.5, "eyeLookDownRight": 0.5},
}


def spring(values: list[float], fps: int, k: float = 180.0, c: float = 16.0) -> list[float]:
    """Damped spring follower (damping ratio ~0.6): gives anticipation-free overshoot + settle."""
    if not values:
        return []
    x, v, dt = values[0], 0.0, 1.0 / fps
    out = []
    for target in values:
        v += ((target - x) * k - v * c) * dt
        x += v * dt
        out.append(x)
    return out


def emotion_targets(placed: list[Placed], fps: int, n_frames: int) -> dict[str, list[float]]:
    t: dict[str, list[float]] = {}
    for i, p in enumerate(placed):
        a = max(0, int(round((p.start - ANTICIPATION) * fps)))
        b = n_frames if i == len(placed) - 1 else max(a, int(round((placed[i + 1].start - ANTICIPATION) * fps)))
        for ch, val in EMOTION_POSES[p.line.emotion].items():
            arr = t.setdefault(ch, [0.0] * n_frames)
            for f in range(a, min(b, n_frames)):
                arr[f] = val * p.line.intensity
    return t


def _emotion_at(placed: list[Placed], t: float) -> str:
    current = "neutral"
    for p in placed:
        if p.start - ANTICIPATION <= t:
            current = p.line.emotion
    return current


def blink_track(placed: list[Placed], fps: int, n_frames: int, seed: int = 7) -> list[float]:
    rng = random.Random(seed)
    out = [0.0] * n_frames
    t = rng.uniform(0.8, 2.0)
    while t * fps < n_frames:
        f = int(t * fps)
        for k, val in enumerate(BLINK_SHAPE):
            if f + k < n_frames:
                out[f + k] = max(out[f + k], val)
        nervous = _emotion_at(placed, t) in NERVOUS
        t += rng.uniform(1.5, 3.0) if nervous else rng.uniform(2.5, 5.0)
    return out


def nod_track(placed: list[Placed], fps: int, n_frames: int) -> list[float]:
    """Small head dips on the longest (≈stressed) words; scaled by intensity."""
    out = [0.0] * n_frames
    for p in placed:
        words = words_from_chars(p.voiced.chars)
        if not words:
            continue
        stressed = sorted(words, key=lambda w: w.end - w.start, reverse=True)[:max(1, len(words) // 4)]
        amp = 0.05 + 0.08 * p.line.intensity
        for w in stressed:
            f0 = int(round((p.start + w.start) * fps))
            for k in range(8):
                if 0 <= f0 + k < n_frames:
                    out[f0 + k] += amp * math.sin(math.pi * k / 8)
    return out


def build_faces(perf: Performance, placed: list[Placed], fps: int, n_frames: int,
                lipsync_override: dict[str, dict[str, list[float]]] | None = None
                ) -> dict[str, dict[str, list[float]]]:
    override = lipsync_override or {}
    faces: dict[str, dict[str, list[float]]] = {}
    for name in perf.characters:
        mine = [p for p in placed if p.line.speaker == name]
        tracks = {c: [0.0] * n_frames for c in ARKIT_NAMES}
        for ch, vals in emotion_targets(mine, fps, n_frames).items():
            tracks[ch] = spring(vals, fps)
        for p in mine:
            local = override.get(p.line.id)
            if local is None:
                n_local = int(math.ceil(p.duration * fps)) + 2
                local = sample_tracks(viseme_events(p.voiced.chars), fps, n_local)
            off = int(round(p.start * fps))
            for ch, vals in local.items():
                if ch not in tracks:
                    continue
                for k, v in enumerate(vals):
                    if 0 <= off + k < n_frames:
                        tracks[ch][off + k] += v
        blink = blink_track(mine, fps, n_frames, seed=sum(map(ord, name)))
        for side in ("eyeBlinkLeft", "eyeBlinkRight"):
            tracks[side] = [max(a, b) for a, b in zip(tracks[side], blink)]
        for ch in ARKIT_NAMES:
            tracks[ch] = [min(1.0, max(0.0, v)) for v in tracks[ch]]
        tracks["headNod"] = nod_track(mine, fps, n_frames)
        faces[name] = tracks
    return faces
