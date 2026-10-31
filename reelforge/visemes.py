"""Grapheme-based visemes from ElevenLabs char timings. Fallback when Audio2Face is unavailable."""
from __future__ import annotations

from .alignment import Char

VISEME_POSES: dict[str, dict[str, float]] = {
    "sil": {},
    "AA": {"jawOpen": 0.55, "mouthFunnel": 0.1},
    "EE": {"jawOpen": 0.25, "mouthStretchLeft": 0.35, "mouthStretchRight": 0.35},
    "OH": {"jawOpen": 0.4, "mouthFunnel": 0.6},
    "OO": {"jawOpen": 0.12, "mouthPucker": 0.85},
    "MBP": {"mouthClose": 0.7, "mouthPressLeft": 0.4, "mouthPressRight": 0.4},
    "FV": {"jawOpen": 0.08, "mouthRollLower": 0.6},
    "TH": {"jawOpen": 0.2, "tongueOut": 0.3},
    "LNT": {"jawOpen": 0.22},
    "SZ": {"jawOpen": 0.08, "mouthStretchLeft": 0.25, "mouthStretchRight": 0.25},
    "CH": {"jawOpen": 0.15, "mouthFunnel": 0.35},
    "KG": {"jawOpen": 0.3},
    "R": {"jawOpen": 0.18, "mouthFunnel": 0.3},
}
VOWELS = {"AA", "EE", "OH", "OO"}
FULL_STRENGTH = {"MBP", "FV"}  # lip closures must hit fully or sync looks wrong
CONSONANT_SCALE = 0.75
GAP_SIL = 0.15

DIGRAPHS = {"th": "TH", "ch": "CH", "sh": "CH", "oo": "OO", "ee": "EE", "ph": "FV",
            "ck": "KG", "qu": "KG", "ou": "OH", "ow": "OH"}
LETTERS = {"a": "AA", "e": "EE", "i": "EE", "y": "EE", "o": "OH", "u": "OO", "w": "OO",
           "b": "MBP", "m": "MBP", "p": "MBP", "f": "FV", "v": "FV",
           "l": "LNT", "n": "LNT", "t": "LNT", "d": "LNT",
           "s": "SZ", "z": "SZ", "c": "SZ", "x": "SZ", "j": "CH",
           "k": "KG", "g": "KG", "q": "KG", "r": "R"}  # 'h' intentionally silent


def viseme_events(chars: list[Char]) -> list[tuple[float, str]]:
    events: list[tuple[float, str]] = []
    prev_end: float | None = None
    i, n = 0, len(chars)
    while i < n:
        c = chars[i]
        low = c.ch.lower()
        if not low.isalpha():
            i += 1
            continue
        if prev_end is not None and c.start - prev_end > GAP_SIL:
            events.append((prev_end + 0.06, "sil"))
            events.append((c.start - 0.06, "sil"))
        pair = low + chars[i + 1].ch.lower() if i + 1 < n else ""
        if pair in DIGRAPHS:
            v, s, e = DIGRAPHS[pair], c.start, chars[i + 1].end
            i += 2
        else:
            v, s, e = LETTERS.get(low), c.start, c.end
            i += 1
        prev_end = e
        if v:
            events.append(((s + e) / 2, v))
    if events:
        events.insert(0, (max(0.0, events[0][0] - 0.12), "sil"))
        events.append((prev_end + 0.08, "sil"))
    return events


def _pose(v: str) -> dict[str, float]:
    base = VISEME_POSES[v]
    if v in VOWELS or v in FULL_STRENGTH:
        return base
    return {k: x * CONSONANT_SCALE for k, x in base.items()}


def _smooth(x: float) -> float:
    return x * x * (3 - 2 * x)


def sample_tracks(events: list[tuple[float, str]], fps: int, n_frames: int) -> dict[str, list[float]]:
    channels = sorted({k for _, v in events for k in VISEME_POSES[v]})
    tracks = {c: [0.0] * n_frames for c in channels}
    if len(events) < 2:
        return tracks
    j = 0
    for f in range(n_frames):
        t = f / fps
        if t <= events[0][0] or t >= events[-1][0]:
            continue
        while j + 1 < len(events) and events[j + 1][0] <= t:
            j += 1
        t0, v0 = events[j]
        t1, v1 = events[j + 1]
        a = _smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
        p0, p1 = _pose(v0), _pose(v1)
        for c in channels:
            tracks[c][f] = p0.get(c, 0.0) * (1 - a) + p1.get(c, 0.0) * a
    return tracks
