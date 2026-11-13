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
    rack: dict = field(default_factory=dict)  # shots-av: {"at": frame in shot, "frames": n, "from": name, "to": name}
    speaker: str = ""  # who is talking, when it is not the subject (shots-av wides); empty = the subject


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
LENSES_V2 = {"wide": 40, "two": 40, "medium": 60, "closeup": 85, "ecu": 110}  # "wide" is waist-up, never full body
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
    if kind in ("wide", "two"):
        opts = [("push_in", {"amount": 0.06}), ("drift", {})] if first else [("drift", {}), ("pull_out", {"amount": 0.06})]
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
    """Shots for the cinema look. Rules: open on the speaker from the waist up (never full body); punchlines and intense lines get a
    close-up that pushes in; long lines cut away to the listener; no two consecutive shots share kind and
    subject; nothing shorter than MIN_SHOT_S or longer than MAX_SHOT_S. camera: {"handheld": 0..1,
    "overrides": {"<shot index>": {kind, lens, move, intensity, fstop, handheld, subject}}}."""
    camera = camera or {}
    two = len(speakers) > 1
    limit, min_len = int(MAX_SHOT_S * fps), int(MIN_SHOT_S * fps)
    raw: list[tuple] = []  # (start, end, kind, subject, line, is_reaction)
    opener = "wide"  # the speaker from the waist up, the room behind: never full body
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
                raw.append((start, end, opener, who, line, False))
                continue
            raw.append((start, start + est, opener, who, line, False))
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
        at_rest = kind in ("wide", "two") and (i == 0 or i == len(merged) - 1)
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


# --- the Shots-AV director (docs/prompts/03-shots-av-animation.md 5.2) -------------------------------------------
# Hard cuts on the line, every shot moving, shot/reverse shot on one side of the desk, one wide every 6-7 shots.
AV_LENSES = {"av_hero_34": 85, "av_hero_front": 85, "av_buddy": 100, "av_wide_34": 50, "av_wide_front": 50}
AV_HERO_KINDS = ("av_hero_34", "av_hero_front")
AV_WIDES = ("av_wide_34", "av_wide_front")
AV_MIN_S, AV_MAX_S, AV_LAST_MIN_S = 1.2, 5.0, 4.5
AV_CUT_LEAD = 3
AV_REACTION_S = (1.0, 1.2, 1.4)
AV_CONCESSIONS = ("fine", "okay", "ok", "true", "alright", "sure", "yeah", "fair", "right", "deal")
AV_GRAMMARS = ("signature", "reference")


def _words(text: str) -> list[str]:
    return [w for w in text.replace("\u2026", " ").replace("...", " ").split() if w.strip(".,!?;:")]


def is_turn(line, prev_hero_line) -> bool:
    """A beat that turns the hero's angle (5.2 rule 5): a question, a concession, a punchline, or a change of
    emotion or mood from his previous line."""
    t = line.text.strip()
    words = _words(t)
    first = words[0].strip(".,!?;:").lower() if words else ""
    concession = t.startswith(("...", "\u2026")) or first in AV_CONCESSIONS
    changed = prev_hero_line is not None and (line.emotion != prev_hero_line.emotion
                                              or line.mood != prev_hero_line.mood)
    return "?" in t or concession or line.punchline or changed


def _av_move(kind: str, dur: float, last: bool) -> tuple[str, dict]:
    """5.2 rule 7: linear moves at fixed rates, so every cut lands in motion."""
    if last:
        return "pull_out", {"amount": 0.25}
    if dur < 1.4:
        return "drift", {"metres": 0.004, "degrees": 0.15}  # near static (about 0.5%)
    if kind in AV_HERO_KINDS:
        return "push_in", {"amount": round(min(0.06, 0.016 * dur), 4)}
    if kind == "av_buddy":
        return "pull_truck", {"amount": round(min(0.12, 0.028 * dur), 4), "metres": 0.004}
    return "push_in", {"amount": round(min(0.08, 0.015 * dur), 4)}


def plan_shots_av(placed: list[Placed], fps: int, n_frames: int, hero: str, buddy: str, seed: int = 0,
                  grammar: str = "signature", camera: dict | None = None) -> list[Shot]:
    """Shots for the shots-av style. `hero` and `buddy` are the speaker names. grammar "reference" reproduces the
    reference reel's rules exactly; "signature" (default) adds a gentle ease-in, a little handheld and one rack
    focus. camera: {"overrides": {"<shot index>": {kind, move, fstop}}}."""
    if grammar not in AV_GRAMMARS:
        raise ValueError(f"grammar must be one of {AV_GRAMMARS}")
    camera = camera or {}
    total = n_frames / fps
    sig = grammar == "signature"
    raw = []  # [start, end, kind, subject, line, reaction]
    angle, prev_hero, singles, wides_done = "av_hero_34", None, 0, 0
    for i, p in enumerate(placed):
        line, last = p.line, i == len(placed) - 1
        start = 0 if i == 0 else max(0, int(round(p.start * fps)) - AV_CUT_LEAD)
        end = n_frames if last else int(round(placed[i + 1].start * fps)) - AV_CUT_LEAD
        is_hero = line.speaker == hero
        short_hero = is_hero and len(_words(line.text)) <= 3 and singles >= 4
        if last:
            kind = "av_wide_front"
        elif line.beat or short_hero:
            kind = AV_WIDES[wides_done % 2]
            wides_done += 1
        elif is_hero:
            if p.start >= total / 3 and is_turn(line, prev_hero):
                angle = "av_hero_front" if angle == "av_hero_34" else "av_hero_34"
            kind = angle
        else:
            kind = "av_buddy"
        if is_hero:
            prev_hero = line
        singles = 0 if kind in AV_WIDES else singles + 1
        subject = buddy if kind == "av_buddy" else hero
        length = end - start
        if not last and kind not in AV_WIDES and length > AV_MAX_S * fps:  # rule 6: split by a listener reaction
            r = int(_pick(seed, i, "react", AV_REACTION_S) * fps)
            mid = start + (length - r) // 2
            other_kind = "av_buddy" if is_hero else angle
            other = hero if subject == buddy else buddy
            raw += [[start, mid, kind, subject, line, False], [mid, mid + r, other_kind, other, line, True],
                    [mid + r, end, kind, subject, line, False]]
        else:
            raw.append([start, end, kind, subject, line, False])
    merged = []  # rule 6: nothing under AV_MIN_S; fold a short shot into the one before it
    for k, r in enumerate(raw):
        if merged and r[1] - r[0] < AV_MIN_S * fps and k < len(raw) - 1:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    while len(merged) > 1 and merged[-1][1] - merged[-1][0] < AV_LAST_MIN_S * fps:  # the closing wide is long
        need = merged[-1][1] - int(AV_LAST_MIN_S * fps)
        if need - merged[-2][0] < AV_MIN_S * fps:
            merged[-1][0] = merged.pop(-2)[0]
        else:
            merged[-2][1] = merged[-1][0] = need
    rack_done = not sig or camera.get("rack", True) is False
    drift = float(camera.get("drift", 1.0))  # the editor's drift dial scales every move
    shots: list[Shot] = []
    for i, (a, b, kind, subject, line, reaction) in enumerate(merged):
        last = i == len(merged) - 1
        move, params = ("static", {}) if reaction else _av_move(kind, (b - a) / fps, last)
        params = {k: (round(v * drift, 4) if k in ("amount", "metres", "degrees") else v) for k, v in params.items()}
        rack = {}
        if not rack_done and kind in AV_WIDES and line.speaker == buddy:  # one rack focus: hero -> buddy
            line_start = next((int(round(p.start * fps)) for p in placed if p.line is line), a)
            rack = {"at": max(0, line_start - a), "frames": 10, "from": hero, "to": buddy}
            rack_done = True
        shots.append(Shot(a, b, kind, float(AV_LENSES[kind]), subject, 0.0, move, params, 0.0,
                          0.04 if sig else 0.0, (seed * 7919 + i * 104729) & 0x7FFFFFFF,
                          round(_hash(seed, i, "az") / 0xFFFFFFFF, 3), 0.15 if sig else 0.0, rack,
                          line.speaker))
    for key, o in (camera.get("overrides") or {}).items():
        i = int(key)
        if 0 <= i < len(shots):
            s = shots[i]
            kind = o.get("kind", s.kind)
            new_move = o.get("move", s.move)
            rack = s.rack
            if o.get("rack") is True and not rack and kind in AV_WIDES:  # the editor's per-shot focus pull
                rack = {"at": 0, "frames": 10, "from": hero, "to": buddy}
            elif o.get("rack") is False:
                rack = {}
            shots[i] = replace(s, kind=kind, lens=float(AV_LENSES.get(kind, s.lens)), move=new_move,
                               move_params=s.move_params if new_move == s.move else {},
                               fstop=float(o.get("fstop", s.fstop)), rack=rack)
    return shots


def screen_time(shots: list[Shot]) -> dict[str, float]:
    """Share of the runtime per group: hero close-ups, buddy singles, wides (the reference: 37 / 46 / 17)."""
    total = sum(s.end_frame - s.start_frame for s in shots) or 1
    group = {"hero": AV_HERO_KINDS, "buddy": ("av_buddy",), "wide": AV_WIDES}
    return {g: round(sum(s.end_frame - s.start_frame for s in shots if s.kind in k) / total, 4)
            for g, k in group.items()}
