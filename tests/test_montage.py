"""The Shots-AV opening montage: quick face cuts at word gaps, every one a different angle, and reel-to-reel variety."""
from pathlib import Path

from reelforge import angles
from reelforge.alignment import Char
from reelforge.direct import AV_WIDES, plan_shots_av
from reelforge.schema import Line
from reelforge.timeline import Placed
from reelforge.voice import VoicedLine

FPS = 30
SCRIPT = [("me", "Claude, I have been fixing this login bug for two whole hours now, is it finally working?", "annoyed"),
          ("bot", "Absolutely! I fixed the issue and everything is working exactly as expected.", "happy"),
          ("me", "Then why am I still staring at a blank screen?", "annoyed"),
          ("bot", "Interesting. Let me investigate.", "thinking"),
          ("me", "I am going to bed.", "sad")]


def _chars(text, dur):
    step = dur / len(text)
    return [Char(ch, k * step, (k + 1) * step) for k, ch in enumerate(text)]


def _placed():
    out, t = [], 0.3
    for i, (who, text, emo) in enumerate(SCRIPT):
        d = len(text.split()) / 2.9 + 0.3
        out.append(Placed(Line(f"l{i}", who, text, emo, 0.6, "calm"), VoicedLine(f"l{i}", Path("x.mp3"), _chars(text, d)),
                          t, d))
        t += d + 0.35
    return out, int((t + 1.0) * FPS)


def _word_spans(p):
    spans, s, in_word = [], None, False
    for c in p.voiced.chars:
        if c.ch.isspace():
            if in_word:
                spans.append((p.start + s, p.start + prev))
            in_word = False
            continue
        if not in_word:
            s = c.start
        prev, in_word = c.end, True
    spans.append((p.start + s, p.start + prev))
    return spans


def test_opening_is_a_montage_of_distinct_face_angles():
    placed, n = _placed()
    shots = plan_shots_av(placed, FPS, n, "me", "bot", seed=3)
    opening = [s for s in shots if s.start_frame < 7 * FPS][:7]
    assert len(opening) >= 6  # quick cuts, not one long hold
    assert len({s.angle for s in opening}) == len(opening)  # every cut a new angle
    assert all(s.kind not in AV_WIDES for s in opening)  # faces, not wides
    assert all(angles.ANGLES[s.angle]["role"] in ("hero", "buddy") and s.angle != "hero_hands" for s in opening)
    for s in opening:
        assert 0.4 * FPS <= s.end_frame - s.start_frame  # nothing flickers
    # montage cuts (same speaker either side) land between words; a cutaway to the listener may cut anywhere
    cuts = [shots[k].start_frame / FPS for k in range(1, 8) if shots[k].subject == shots[k - 1].subject]
    assert len(cuts) >= 4
    words = [w for p in placed for w in _word_spans(p)]
    for c in cuts:
        assert not any(a + 0.02 < c < b - 0.02 for a, b in words), c  # never in the middle of a word


def test_classic_opening_and_cut_count_are_settings():
    placed, n = _placed()
    classic = plan_shots_av(placed, FPS, n, "me", "bot", seed=3, camera={"opening": "classic"})
    assert classic[0].end_frame - classic[0].start_frame > 2 * FPS
    five = plan_shots_av(placed, FPS, n, "me", "bot", seed=3, camera={"opening_cuts": 5})
    ten = plan_shots_av(placed, FPS, n, "me", "bot", seed=3, camera={"opening_cuts": 10})
    assert len(ten) > len(five)


def test_history_makes_consecutive_reels_open_differently():
    placed, n = _placed()
    first = plan_shots_av(placed, FPS, n, "me", "bot", seed=3)
    used = [s.angle for s in first[:7]]
    again = plan_shots_av(placed, FPS, n, "me", "bot", seed=3, camera={"avoid": used})
    assert [s.angle for s in again[:7]] != used
    assert len(set(s.angle for s in again[:7]) & set(used)) < len(used)


def test_no_angle_repeats_while_unused_ones_remain():
    placed, n = _placed()
    shots = plan_shots_av(placed, FPS, n, "me", "bot", seed=11)
    heroes = [s.angle for s in shots if s.angle and angles.ANGLES.get(s.angle, {}).get("role") == "hero"]
    assert len(heroes) == len(set(heroes))
