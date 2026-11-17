"""Shots-AV camera angle library and the director that picks from it.

56 angles in three roles (hero singles, buddy singles, wides). Each is a framing: lens (mm), head (share of frame
height for the subject's framing height), eyes (eye line from the top), fstop, az (degree range; negative = the
hero's monitor side, positive = the buddy's side, the same convention as camera_rig.FRAMING), el (degrees above
the eye line), roll (dutch tilt, degrees) and the moods it suits. The renderer (blender/camera_rig.py base_pose)
reads the framing straight from the shot, so a new angle needs no Blender change.

The director "thinks" per shot: it reads the line's emotion and intensity, what came before and how often each
angle was used, scores every angle for the shot's role and picks the best with a little seeded chance. Same seed,
same reel; a new seed (a new project, or Reroll angles in the editor) gives a differently shot reel.
Pure standard library.
"""
from __future__ import annotations

import hashlib

# id: (role, lens, head, eyes, fstop, (az0, az1), el, roll, moods, label)
_T = {
    # --- hero singles --------------------------------------------------------------------------------------------
    "hero_34":          ("hero", 85, 0.46, 0.52, 1.8, (-34, -28), 4, 0, "neutral warm", "Three-quarter close-up"),
    "hero_front":       ("hero", 85, 0.46, 0.54, 2.0, (-3, 3), -4, 0, "neutral tense comic", "Straight on"),
    "hero_low":         ("hero", 70, 0.42, 0.50, 2.0, (-30, -24), -10, 0, "tense warm", "Low angle, heroic"),
    "hero_high":        ("hero", 70, 0.42, 0.52, 2.0, (-32, -26), 14, 0, "soft", "High angle, small"),
    "hero_profile":     ("hero", 85, 0.44, 0.50, 2.0, (-70, -62), 2, 0, "soft neutral", "Profile"),
    "hero_buddy_side":  ("hero", 85, 0.46, 0.52, 1.8, (18, 26), 3, 0, "neutral warm", "From the buddy's side"),
    "hero_tight":       ("hero", 110, 0.62, 0.46, 2.2, (-20, -14), 2, 0, "tense reaction", "Tight close-up"),
    "hero_ecu":         ("hero", 135, 0.85, 0.44, 2.8, (-10, -4), 0, 0, "tense", "Extreme close-up"),
    "hero_dutch":       ("hero", 70, 0.44, 0.52, 2.0, (-28, -22), 4, 8, "tense comic", "Dutch tilt"),
    "hero_wide_lens":   ("hero", 35, 0.40, 0.50, 2.8, (-26, -18), 6, 0, "comic", "Wide lens, close"),
    "hero_ots":         ("hero", 50, 0.30, 0.40, 2.0, (30, 40), 6, 0, "neutral warm", "Over the buddy"),
    "hero_monitor":     ("hero", 60, 0.40, 0.48, 2.0, (-46, -38), -2, 0, "neutral tense", "From the monitor"),
    "hero_top":         ("hero", 50, 0.34, 0.48, 2.8, (-20, -10), 32, 0, "soft comic", "Top down"),
    "hero_medium":      ("hero", 60, 0.34, 0.42, 2.4, (-22, -16), 5, 0, "neutral warm", "Waist-up medium"),
    "hero_hands":       ("hero", 85, 0.90, -0.60, 2.8, (-20, -10), 28, 0, "reaction", "Hands on the keys"),
    "hero_shallow":     ("hero", 50, 0.36, 0.48, 1.4, (30, 40), 4, 0, "soft warm", "Through the buddy, soft"),
    # added 2026-11: more faces for the opening montage and fewer repeats (every one shows the face)
    "hero_floor":       ("hero", 35, 0.36, 0.50, 2.8, (-24, -16), -14, 0, "tense comic", "Floor angle"),
    "hero_crash":       ("hero", 135, 0.70, 0.45, 2.4, (-6, 0), 0, 0, "comic tense reaction", "Crash zoom"),
    "hero_security":    ("hero", 35, 0.30, 0.45, 3.2, (-40, -32), 30, 0, "comic", "Security cam"),
    "hero_low_dutch":   ("hero", 50, 0.40, 0.52, 2.2, (-16, -8), -12, -8, "tense comic", "Low dutch"),
    "hero_far_profile": ("hero", 85, 0.44, 0.50, 2.0, (56, 66), 2, 0, "soft neutral", "Profile, far side"),
    "hero_slider":      ("hero", 60, 0.40, 0.50, 2.0, (-12, -6), 2, 0, "neutral warm", "Slider pass"),
    "hero_close_low":   ("hero", 85, 0.55, 0.48, 2.0, (-12, -6), -8, 0, "tense warm", "Close, low"),
    "hero_close_high":  ("hero", 85, 0.55, 0.50, 2.0, (-18, -12), 12, 0, "soft comic", "Close, high"),
    "hero_long_34":     ("hero", 110, 0.50, 0.50, 1.8, (-50, -44), 4, 0, "soft neutral", "Long-lens three-quarter"),
    "hero_orbit":       ("hero", 70, 0.44, 0.52, 2.0, (-40, -34), 3, 0, "warm neutral", "Orbit"),
    "hero_eye_level":   ("hero", 50, 0.38, 0.50, 2.2, (-8, -2), 0, 0, "neutral comic", "Eye level, wide lens"),
    "hero_near_side":   ("hero", 70, 0.46, 0.52, 2.0, (8, 14), 6, 0, "warm neutral", "Near the buddy, close"),
    # --- buddy singles -------------------------------------------------------------------------------------------
    "buddy_classic":    ("buddy", 100, 0.38, 0.62, 2.0, (-8, -2), 4, 0, "neutral warm", "Buddy close"),
    "buddy_low":        ("buddy", 85, 0.40, 0.60, 2.0, (-14, -6), -8, 0, "warm tense", "Buddy, low"),
    "buddy_34":         ("buddy", 85, 0.38, 0.60, 2.0, (-30, -22), 6, 0, "neutral", "Buddy three-quarter"),
    "buddy_tight":      ("buddy", 135, 0.55, 0.55, 2.4, (-6, 0), 3, 0, "tense reaction comic", "Buddy's face, tight"),
    "buddy_high":       ("buddy", 85, 0.36, 0.62, 2.2, (-12, -4), 20, 0, "soft comic", "Buddy from above"),
    "buddy_ots":        ("buddy", 60, 0.30, 0.55, 2.0, (-40, -32), 8, 0, "neutral warm", "Over the hero"),
    "buddy_profile":    ("buddy", 100, 0.38, 0.60, 2.0, (-70, -60), 3, 0, "soft", "Buddy profile"),
    "buddy_dutch":      ("buddy", 85, 0.38, 0.60, 2.0, (-12, -4), 4, -8, "comic tense", "Buddy, dutch"),
    "buddy_desk":       ("buddy", 50, 0.36, 0.66, 2.0, (-6, 2), -2, 0, "warm comic reaction", "Desk level"),
    "buddy_crash":      ("buddy", 135, 0.62, 0.55, 2.4, (-4, 2), 2, 0, "comic tense reaction", "Buddy crash zoom"),
    "buddy_floor":      ("buddy", 40, 0.36, 0.62, 2.8, (-16, -8), -14, 0, "comic warm", "Buddy from below"),
    "buddy_orbit":      ("buddy", 85, 0.38, 0.60, 2.0, (-26, -18), 4, 0, "warm neutral", "Buddy orbit"),
    "buddy_long":       ("buddy", 135, 0.45, 0.58, 1.8, (-20, -14), 4, 0, "soft neutral", "Buddy, long lens"),
    "buddy_security":   ("buddy", 35, 0.30, 0.60, 3.2, (-30, -22), 28, 0, "comic", "Buddy security cam"),
    # --- wides and two-shots -------------------------------------------------------------------------------------
    "wide_orbit":       ("wide", 40, 0.23, 0.36, 2.8, (-22, -14), 7, 0, "warm neutral", "Wide orbit"),
    "wide_floor":       ("wide", 28, 0.21, 0.38, 3.2, (-14, -6), -12, 0, "comic tense", "Wide from the floor"),
    "wide_doorway":     ("wide", 35, 0.20, 0.36, 3.2, (-44, -36), 10, 0, "neutral soft", "From the doorway"),
    "wide_34":          ("wide", 50, 0.25, 0.36, 2.8, (-18, -12), 8, 0, "neutral", "Wide three-quarter"),
    "wide_front":       ("wide", 50, 0.25, 0.35, 2.8, (-3, 3), 6, 0, "neutral warm", "Wide, front"),
    "wide_high":        ("wide", 35, 0.20, 0.38, 4.0, (-14, -6), 24, 0, "soft comic", "Wide from above"),
    "wide_low":         ("wide", 40, 0.22, 0.34, 2.8, (-12, -4), -6, 0, "tense warm", "Wide, low"),
    "wide_buddy_side":  ("wide", 50, 0.24, 0.36, 2.8, (14, 22), 8, 0, "neutral", "Wide from the buddy's side"),
    "wide_room":        ("wide", 28, 0.17, 0.36, 4.0, (-10, -2), 10, 0, "neutral warm", "Room reveal"),
    "wide_side":        ("wide", 50, 0.24, 0.36, 2.8, (-62, -54), 5, 0, "soft", "Side two-shot"),
    "wide_dutch":       ("wide", 40, 0.22, 0.36, 2.8, (-16, -10), 6, 6, "tense comic", "Wide, dutch"),
    "wide_tele":        ("wide", 85, 0.30, 0.40, 2.0, (-24, -18), 4, 0, "tense soft", "Compressed two-shot"),
    "wide_corner":      ("wide", 35, 0.21, 0.36, 3.2, (-34, -26), 16, 0, "comic neutral", "High corner"),
    "wide_overhead":    ("wide", 35, 0.20, 0.40, 4.0, (-6, 4), 38, 0, "comic soft", "Overhead desk"),
}
ANGLES = {k: {"role": v[0], "lens": v[1], "head": v[2], "eyes": v[3], "fstop": v[4], "az": v[5], "el": v[6],
              "roll": v[7], "moods": tuple(v[8].split()), "label": v[9]} for k, v in _T.items()}
CLASSIC = {"av_hero_34": "hero_34", "av_hero_front": "hero_front", "av_buddy": "buddy_classic",
           "av_wide_34": "wide_34", "av_wide_front": "wide_front"}  # the reference reel's five set-ups
ROLE_OF = {"av_hero_34": "hero", "av_hero_front": "hero", "av_buddy": "buddy", "av_wide_34": "wide",
           "av_wide_front": "wide"}
KIND_OF = {"hero": "av_hero_34", "buddy": "av_buddy", "wide": "av_wide_34"}

_TENSE = {"angry", "frustrated", "annoyed", "shocked", "scared", "panicked", "furious", "stressed", "urgent",
          "surprised", "shouting"}
_SOFT = {"sad", "quiet", "tired", "apologetic", "sheepish", "worried", "nervous", "calm", "thoughtful", "whisper"}
_WARM = {"happy", "cheerful", "excited", "proud", "relieved", "grateful", "hopeful", "warm", "playful"}
_COMIC = {"sarcastic", "deadpan", "confused", "smug", "teasing", "awkward", "embarrassed", "sheepish"}


_PUNCH = ("hero_ecu", "hero_tight", "buddy_tight", "hero_hands", "hero_dutch", "buddy_dutch", "hero_wide_lens")


def mood_of(emotion: str, intensity: float) -> str:
    e = (emotion or "").lower()
    if e in _TENSE or intensity >= 0.8:
        return "tense"
    if e in _COMIC:
        return "comic"
    if e in _SOFT:
        return "soft"
    if e in _WARM:
        return "warm"
    return "neutral"


def framing(angle_id: str) -> dict:
    a = ANGLES[angle_id]
    return {k: a[k] for k in ("lens", "head", "eyes", "fstop", "az", "el", "roll")}


def _noise(seed: int, i: int, salt: str) -> float:
    return int(hashlib.sha1(f"{seed}:{i}:{salt}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


class Director:
    """Picks an angle per shot. One instance per reel: it remembers what it used."""

    def __init__(self, seed: int, avoid=()):
        """avoid: angles the last few reels used (projects/.angle_history.json); they lose a little score so
        consecutive reels look different."""
        self.seed, self.used, self.prev, self.prev_side = seed, {}, {}, 0
        self.avoid = set(avoid or ())

    def pick(self, i: int, role: str, mood: str, reaction: bool = False, montage: bool = False) -> str:
        """montage: the opening's quick face cuts - never an angle already used, punch-ins allowed, always a face."""
        best, best_score = None, -1e9
        for aid, a in ANGLES.items():
            if a["role"] != role:
                continue
            if aid == "hero_hands" and (not reaction or montage):  # an insert only cuts in while he listens
                continue
            if montage and self.used.get(aid):
                continue
            if i < 2 and aid in _PUNCH and not montage:  # open on a set-up that shows who is where; punch in later
                continue
            score = 1.0
            if mood in a["moods"]:
                score += 2.0
            if reaction and "reaction" in a["moods"]:
                score += 2.5
            if a["roll"] and mood not in ("tense", "comic"):
                score -= 2.0  # a dutch tilt needs a reason
            if self.prev.get(role) == aid:
                score -= 4.0  # never the same set-up twice in a row
            score -= 6.0 * self.used.get(aid, 0)  # no repeats until the role's angles run out
            if aid in self.avoid:
                score -= 2.0  # the last reels used it
            side = 1 if a["az"][0] + a["az"][1] > 0 else -1
            if role != "wide" and side == self.prev_side:
                score -= 0.4  # alternate sides a little
            score += 3.0 * _noise(self.seed, i, aid)  # the director's taste: differs per seed
            if score > best_score:
                best, best_score = aid, score
        if best is None:  # a montage that used every angle of the role: allow repeats
            return self.pick(i, role, mood, reaction, montage=False)
        self.used[best] = self.used.get(best, 0) + 1
        self.prev[role] = best
        a = ANGLES[best]
        self.prev_side = 1 if a["az"][0] + a["az"][1] > 0 else -1
        return best


def move_for(angle_id: str, dur: float, seed: int, i: int) -> tuple[str, dict]:
    """A move that suits the angle: tight angles creep in, profiles orbit, high wides crane, telephotos truck."""
    if "crash" in angle_id:  # a fast punch-in on the punchline (and in the opening montage)
        return "push_in", {"amount": round(min(0.16, 0.08 * max(dur, 0.6)), 4)}
    if dur < 1.4:
        return "drift", {"metres": 0.004, "degrees": 0.15}
    a = ANGLES[angle_id]
    r = _noise(seed, i, "move")
    if "orbit" in angle_id:
        return "orbit", {"degrees": round(min(12.0, 3.0 * dur), 2)}
    if "slider" in angle_id:
        return "truck", {"metres": round(min(0.18, 0.05 * dur), 3)}
    if angle_id in ("hero_ecu", "hero_tight", "buddy_tight"):
        return "slow_zoom", {"amount": round(min(0.08, 0.02 * dur), 4)}
    if "profile" in angle_id or angle_id == "wide_side":
        return "orbit", {"degrees": round(min(8.0, 1.6 * dur), 2)}
    if a["role"] == "wide" and a["el"] >= 16:
        return "crane_down", {"metres": round(min(0.25, 0.05 * dur), 3)}
    if angle_id in ("wide_tele", "hero_ots", "buddy_ots", "hero_shallow"):
        return "truck", {"metres": round(min(0.12, 0.025 * dur), 3)}
    if angle_id == "hero_hands":
        return "drift", {"metres": 0.01, "degrees": 0.4}
    if a["role"] == "buddy":
        return ("pull_truck", {"amount": round(min(0.12, 0.028 * dur), 4), "metres": 0.004}) if r < 0.6 else \
               ("push_in", {"amount": round(min(0.07, 0.016 * dur), 4)})
    if r < 0.25:
        return "drift", {"metres": 0.03, "degrees": 1.0}
    return "push_in", {"amount": round(min(0.07, 0.016 * dur), 4)}


# --- reel-to-reel variety: the angles the last few reels used (projects/.angle_history.json) ---------------------
def _history_file():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "projects" / ".angle_history.json"


def recent_angles(project, keep: int = 5) -> list[str]:
    """Angles other projects' last renders used (most recent `keep` reels); this project's own entry is skipped, so
    re-rendering a reel doesn't push it away from itself."""
    import json
    from pathlib import Path
    try:
        rows = json.loads(_history_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = [r for r in rows if r.get("project") != Path(project).name][-keep:]
    return sorted({a for r in rows for a in r.get("angles", [])})


def recent_places(project, keep: int = 2) -> list[str]:
    """Places the last `keep` other reels were shot in (the Auto place avoids them)."""
    import json
    from pathlib import Path
    try:
        rows = json.loads(_history_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = [r for r in rows if r.get("project") != Path(project).name and r.get("place")][-keep:]
    return [r["place"] for r in rows]


def remember_angles(project, shots, place: str = "") -> None:
    import json
    from pathlib import Path
    f = _history_file()
    try:
        rows = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    rows = [r for r in rows if r.get("project") != Path(project).name]
    rows.append({"project": Path(project).name, "angles": [s.angle for s in shots if getattr(s, "angle", "")][:12],
                 "place": place})
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rows[-30:], indent=1), encoding="utf-8")
