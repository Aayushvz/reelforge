from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, replace

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
    # cinema look (director v2); empty/zero = the classic camera in render_plan.py
    move: str = ""
    move_params: dict = field(default_factory=dict)
    fstop: float = 0.0  # 0 = the framing table's default
    handheld: float = 0.0
    seed: int = 0
    az_pick: float = 0.5  # where inside the kind's azimuth range the camera stands
    ease: float = 0.35  # 0 = constant speed (cut into a travelling move), 1 = starts and lands at rest


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


# --- director v2 (cinema look): motivated moves, reaction shots, no repeated set-ups -----------------------
LENSES_V2 = {"wide": 32, "medium": 50, "closeup": 85, "ecu": 110}
MIN_SHOT_S = 0.9
ESTABLISH_S = 2.0
REACTION_S = (0.8, 1.2, 1.6)
CUT_LEAD_V2 = 3


def _hash(seed: int, i: int, salt: str) -> int:
    return int(hashlib.sha1(f"{seed}:{i}:{salt}".encode()).hexdigest()[:8], 16)


def _pick(seed: int, i: int, salt: str, options):
    """Deterministic choice: the editor preview and the render must agree, run after run."""
    return options[_hash(seed, i, salt) % len(options)]


def _move_for(kind: str, line, first: bool, two: bool, reaction: bool, seed: int, i: int, prev: str):
    """A camera move that means something for this beat: (move, params)."""
    if reaction:
        return "static", {}
    if kind == "wide":
        opts = [("crane_down", {}), ("drift", {})] if first else [("drift", {}), ("pull_out", {"amount": 0.06})]
        if line.mood == "sad":
            opts = [("pull_out", {"amount": 0.10})]
    elif kind in ("closeup", "ecu"):
        if line.punchline or line.mood == "reveal":
            opts = [("push_in", {"amount": 0.12 if line.mood == "reveal" else 0.10})]
        elif line.mood == "sad":
            opts = [("pull_out", {"amount": 0.05}), ("push_in", {"amount": 0.04})]
        elif line.mood == "panic":
            opts = [("push_in", {"amount": 0.09}), ("slow_zoom", {"amount": 0.10})]
        else:
            opts = [("push_in", {"amount": 0.05}), ("drift", {}), ("static", {})]
    else:
        opts = [("drift", {}), ("push_in", {"amount": 0.05}),
                ("orbit", {"degrees": 10.0}) if two else ("truck", {"metres": 0.12})]
    choice = _pick(seed, i, "move", opts)
    if choice[0] == prev and len(opts) > 1:  # never the same move twice running
        choice = next(o for o in opts if o[0] != prev)
    return choice


def plan_shots_v2(placed: list[Placed], fps: int, n_frames: int, speakers: list[str], seed: int = 0,
                  camera: dict | None = None) -> list[Shot]:
    """Shots for the cinema look. Rules: open on an establishing wide; punchlines and intense lines get a
    close-up that pushes in; long lines cut away to the listener; no two consecutive shots share kind and
    subject; nothing shorter than MIN_SHOT_S or longer than MAX_SHOT_S. camera: {"handheld": 0..1,
    "overrides": {"<shot index>": {kind, lens, move, intensity, fstop, handheld, subject}}}."""
    camera = camera or {}
    two = len(speakers) > 1
    limit, min_len = int(MAX_SHOT_S * fps), int(MIN_SHOT_S * fps)
    raw: list[tuple] = []  # (start, end, kind, subject, line, is_reaction)
    for i, p in enumerate(placed):
        start = 0 if i == 0 else max(0, int(round(p.start * fps)) - CUT_LEAD_V2)
        end = n_frames if i == len(placed) - 1 else int(round(placed[i + 1].start * fps)) - CUT_LEAD_V2
        line, who = p.line, p.line.speaker
        other = next((s for s in speakers if s != who), None)
        base = "closeup" if (line.punchline or line.intensity >= 0.7) else "medium"
        flip = "medium" if base == "closeup" else "closeup"
        if i == 0:  # establish the place first
            est = min(int(ESTABLISH_S * fps), int((end - start) * 0.45))
            if end - start < int(1.8 * fps) or est < min_len:
                raw.append((start, end, "wide", who, line, False))
                continue
            raw.append((start, start + est, "wide", who, line, False))
            start += est
        length = end - start
        n = max(1, math.ceil(length / limit))
        step = length // n
        for k in range(n):
            a = start + k * step
            b = end if k == n - 1 else a + step
            if k % 2 == 0:
                raw.append((a, b, base, who, line, False))
            elif other and line.intensity >= 0.5:  # cut away to the listener, then back
                r = min(b - a, int(_pick(seed, i * 10 + k, "react", REACTION_S) * fps))
                raw.append((a, a + r, "closeup", other, line, True))
                if b - (a + r) > 0:
                    raw.append((a + r, b, flip, who, line, False))
            else:
                raw.append((a, b, flip, who, line, False))
    merged: list[list] = []
    for r in raw:  # fold fragments into a neighbour
        if merged and r[1] - r[0] < min_len and r[1] - merged[-1][0] <= limit:
            merged[-1][1] = r[1]
        elif merged and merged[-1][1] - merged[-1][0] < min_len and r[1] - merged[-1][0] <= limit:
            merged[-1] = [merged[-1][0], r[1], *r[2:]]
        else:
            merged.append(list(r))
    shots: list[Shot] = []
    prev_move = ""
    for i, (a, b, kind, who, line, reaction) in enumerate(merged):
        if shots and shots[-1].kind == kind and shots[-1].subject == who:  # no repeated set-up
            kind = "medium" if kind == "closeup" else "closeup"
        move, params = _move_for(kind, line, i == 0, two, reaction, seed, i, prev_move)
        prev_move = move
        at_rest = kind == "wide" and (i == 0 or i == len(merged) - 1)
        shots.append(Shot(a, b, kind, LENSES_V2[kind], who, 0.0, move, dict(params), 0.0,
                          float(camera.get("handheld", 0.15)), (seed * 7919 + i * 104729) & 0x7FFFFFFF,
                          round(_hash(seed, i, "az") / 0xFFFFFFFF, 3), 1.0 if at_rest else 0.35))
    for key, o in (camera.get("overrides") or {}).items():
        i = int(key)
        if not 0 <= i < len(shots):
            continue
        s = shots[i]
        kind = o.get("kind", s.kind)
        params = dict(s.move_params) if o.get("move", s.move) == s.move else {}
        if "intensity" in o:
            params["intensity"] = float(o["intensity"])
        shots[i] = replace(s, kind=kind, lens=float(o.get("lens", LENSES_V2[kind] if "kind" in o else s.lens)),
                           subject=o.get("subject", s.subject), move=o.get("move", s.move), move_params=params,
                           fstop=float(o.get("fstop", s.fstop)), handheld=float(o.get("handheld", s.handheld)))
    return shots
