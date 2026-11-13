"""The Shots-AV angle library and the director that picks from it."""
from reelforge import angles
from reelforge.direct import plan_shots_av
from reelforge.schema import AV_ROOMS, PerformanceError, parse_performance
from reelforge.timeline import Placed
from reelforge.schema import Line
from reelforge.voice import VoicedLine
from pathlib import Path

import pytest

FPS = 30
SCRIPT = [("me", "Claude, the client signed off.", "happy", 0.6), ("bot", "That's great! What changed?", "excited", 0.6),
          ("me", "Nothing. I just asked you to fix one thing.", "frustrated", 0.8),
          ("bot", "I fixed it. And eleven other things.", "sheepish", 0.5),
          ("me", "Why would you do that?", "angry", 0.9), ("bot", "You seemed tired.", "sad", 0.4),
          ("me", "I am tired.", "tired", 0.4), ("bot", "Want me to undo it?", "hopeful", 0.5),
          ("me", "No. Ship it.", "calm", 0.5)]


def placed():
    out, t = [], 0.2
    for i, (who, text, emo, k) in enumerate(SCRIPT):
        d = 0.35 * len(text.split()) + 0.6
        out.append(Placed(Line(f"l{i}", who, text, emo, k, "calm"), VoicedLine(f"l{i}", Path("x.mp3"), []), t, d))
        t += d + 0.35
    return out, int((t + 4.0) * FPS)


def test_library_has_36_angles_in_three_roles():
    assert len(angles.ANGLES) == 36
    roles = [a["role"] for a in angles.ANGLES.values()]
    assert roles.count("hero") == 16 and roles.count("buddy") == 9 and roles.count("wide") == 11
    for aid, a in angles.ANGLES.items():
        assert 20 <= a["lens"] <= 150 and 0.1 < a["head"] < 1 and a["az"][0] <= a["az"][1], aid
        assert -15 <= a["el"] <= 40 and abs(a["roll"]) <= 10 and a["label"], aid


def test_mood_reads_the_line():
    assert angles.mood_of("angry", 0.5) == "tense" and angles.mood_of("calm", 0.9) == "tense"
    assert angles.mood_of("sad", 0.4) == "soft" and angles.mood_of("happy", 0.5) == "warm"
    assert angles.mood_of("sarcastic", 0.5) == "comic" and angles.mood_of("", 0.5) == "neutral"


def test_same_seed_same_reel_new_seed_new_reel():
    p, n = placed()
    a = [s.angle for s in plan_shots_av(p, FPS, n, "me", "bot", seed=1)]
    assert a == [s.angle for s in plan_shots_av(p, FPS, n, "me", "bot", seed=1)]
    others = {tuple(s.angle for s in plan_shots_av(p, FPS, n, "me", "bot", seed=k)) for k in range(2, 8)}
    assert len(others) >= 5  # six seeds, (nearly) six different reels


def test_director_varies_and_never_repeats_a_setup_back_to_back():
    p, n = placed()
    for seed in range(10):
        shots = plan_shots_av(p, FPS, n, "me", "bot", seed=seed)
        body = shots[:-1]
        assert len({s.angle for s in body}) >= min(len(body), 6)
        by_role = {}
        for s in body:
            role = angles.ANGLES[s.angle]["role"]
            assert by_role.get(role) != s.angle, (seed, s.angle)
            by_role[role] = s.angle
        assert shots[-1].angle == "wide_front" and shots[-1].move == "pull_out"  # the closing wide stays
        assert all(s.framing and s.lens == s.framing["lens"] for s in shots)
        assert all(angles.ANGLES[s.angle]["role"] == angles.ROLE_OF[s.kind] for s in shots)


def test_classic_mode_and_reference_grammar_keep_five_setups():
    p, n = placed()
    for kw in ({"camera": {"angles": "classic"}}, {"grammar": "reference"}):
        shots = plan_shots_av(p, FPS, n, "me", "bot", seed=3, **kw)
        assert {s.angle for s in shots} <= set(angles.CLASSIC.values())


def test_editor_can_pin_an_angle_on_a_shot():
    p, n = placed()
    shots = plan_shots_av(p, FPS, n, "me", "bot", seed=1, camera={"overrides": {"1": {"angle": "wide_overhead"}}})
    assert shots[1].angle == "wide_overhead" and shots[1].kind == "av_wide_34" and shots[1].lens == 35
    shots = plan_shots_av(p, FPS, n, "me", "bot", seed=1, camera={"overrides": {"0": {"angle": "buddy_low"}}})
    assert shots[0].subject == "bot" and shots[0].kind == "av_buddy"


def _perf(**extra):
    return {"style": "shots-av", "characters": {"me": {"model": "av_hero"}, "claude": {"model": "buddy_claude"}},
            "lines": [{"speaker": "me", "text": "hi"}], **extra}


def test_schema_takes_room_view_caption_place_and_angle_mode():
    p = parse_performance(_perf(environment="av_moon_window", room_view={"pan": 0.5, "turn": -1},
                                captions={"position": "custom", "x": 0.5, "y": 0.8, "size": 1.4},
                                camera={"angles": "classic", "overrides": {"0": {"angle": "hero_dutch"}}}))
    assert p.room_view == {"pan": 0.5, "turn": -1} and p.captions["size"] == 1.4 and len(AV_ROOMS) == 12
    for bad in ({"room_view": {"pan": 2}}, {"room_view": {"zoom": 0.1}}, {"captions": {"size": 3}},
                {"captions": {"y": -0.1}}, {"camera": {"angles": "wild"}},
                {"camera": {"overrides": {"0": {"angle": "nope"}}}}):
        with pytest.raises(PerformanceError):
            parse_performance(_perf(**bad))


def test_captions_can_be_placed_and_sized_by_hand():
    import re
    from reelforge import captions
    from reelforge.timeline import Placed as P
    perf = parse_performance(_perf())
    pl = [P(Line("l0", "me", "Claude, the client signed off.", "neutral", 0.5, "calm"),
            VoicedLine("l0", Path("x.mp3"), []), 0.1, 2.0)]
    base = captions.build_ass_shotsav(pl, perf, 1080, 1920, FPS, 3.0)
    big = captions.build_ass_shotsav(pl, perf, 1080, 1920, FPS, 3.0, place=(0.5, 0.7), scale=1.5)
    assert "Style: AV,Geist,46," in base and "Style: AV,Geist,69," in big
    y = int(re.search(r",AV,.*?pos\((\d+),(\d+)\)", big).group(2))
    assert 0.62 < y / 1920 < 0.70  # the text block (two lines) centres on 70% down
    styled = captions.build_ass_styled(pl, perf, 1080, 1920, {}, place=(0.3, 0.4), scale=0.75)
    style = next(l for l in styled.splitlines() if l.startswith("Style: AVS"))
    assert style.startswith("Style: AVS,Geist,48,") and style.split(",")[18] == "5"  # 64 px x 0.75, centred
