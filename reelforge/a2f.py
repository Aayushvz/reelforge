from __future__ import annotations

from .arkit import ARKIT_NAMES

_VALID = set(ARKIT_NAMES)


def _clamp(v: float) -> float:
    return min(1.0, max(0.0, v))


def frames_to_tracks(frames: list[dict], fps: int, n_frames: int) -> dict[str, list[float]]:
    frames = sorted(frames, key=lambda f: f["time"])
    names = sorted({k for f in frames for k in f["blendshapes"] if k in _VALID})
    tracks = {n: [0.0] * n_frames for n in names}
    if not frames:
        return tracks
    j = 0
    for i in range(n_frames):
        t = i / fps
        while j + 1 < len(frames) and frames[j + 1]["time"] <= t:
            j += 1
        a = frames[j]
        b = frames[j + 1] if j + 1 < len(frames) and t >= a["time"] else a
        span = b["time"] - a["time"]
        u = 0.0 if span <= 0 else min(1.0, max(0.0, (t - a["time"]) / span))
        for n in names:
            # clamp the source keys first so out-of-range values don't skew in-betweens
            v = _clamp(a["blendshapes"].get(n, 0.0)) * (1 - u) + _clamp(b["blendshapes"].get(n, 0.0)) * u
            tracks[n][i] = _clamp(v)
    return tracks
