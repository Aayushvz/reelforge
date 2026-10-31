from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .timeline import Placed

LENSES = {"wide": 35, "medium": 50, "closeup": 85}
MAX_SHOT_S = 3.0
CUT_LEAD_FRAMES = 4  # cut slightly before the line starts
MOOD_LEAD_S = 0.15


@dataclass(frozen=True)
class Shot:
    start_frame: int
    end_frame: int  # exclusive
    kind: str
    lens: float
    subject: str
    push: float


def plan_shots(placed: list[Placed], fps: int, n_frames: int) -> list[Shot]:
    shots: list[Shot] = []
    for i, p in enumerate(placed):
        start = 0 if i == 0 else max(0, int(round(p.start * fps)) - CUT_LEAD_FRAMES)
        end = n_frames if i == len(placed) - 1 else int(round(placed[i + 1].start * fps)) - CUT_LEAD_FRAMES
        close = p.line.punchline or p.line.intensity >= 0.7
        kind = "closeup" if close else ("wide" if i == 0 else "medium")
        push = 0.12 if kind == "wide" or p.line.mood in ("sad", "reveal") else 0.05
        shots.append(Shot(start, end, kind, LENSES[kind], p.line.speaker, push))
    return _split_long(shots, fps)


def _split_long(shots: list[Shot], fps: int) -> list[Shot]:
    out: list[Shot] = []
    limit = int(MAX_SHOT_S * fps)
    for s in shots:
        length = s.end_frame - s.start_frame
        if length <= limit:
            out.append(s)
            continue
        n = math.ceil(length / limit)
        step = length // n
        for k in range(n):
            a = s.start_frame + k * step
            b = s.end_frame if k == n - 1 else a + step
            kind = s.kind if k % 2 == 0 else ("medium" if s.kind == "closeup" else "closeup")
            out.append(replace(s, start_frame=a, end_frame=b, kind=kind, lens=LENSES[kind]))
    return out


def mood_keys(placed: list[Placed], fps: int) -> list[tuple[int, str]]:
    keys: list[tuple[int, str]] = []
    for i, p in enumerate(placed):
        f = 0 if i == 0 else int(round((p.start - MOOD_LEAD_S) * fps))
        if not keys or keys[-1][1] != p.line.mood:
            keys.append((f, p.line.mood))
    return keys
