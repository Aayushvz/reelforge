"""Shots-AV buddy acting (reelforge/buddy.py): clips, action picking, loudness envelope, talk squash, animate()."""
import array
import math
import wave

import pytest

from reelforge import buddy
from reelforge.schema import AV_ACTIONS

FPS = 30


def test_the_eight_clips_match_the_schema_and_the_spec():
    assert tuple(buddy.CLIPS) == AV_ACTIONS
    for name, clip in buddy.CLIPS.items():
        assert 8 <= clip["len"] <= 20, name
        assert 0 <= clip["peak"] <= clip["len"], name
        for control, keys in clip["keys"].items():
            assert control in buddy.CONTROLS, (name, control)
            frames = [f for f, _ in keys]
            assert frames == sorted(frames) and frames[-1] <= clip["len"], (name, control)
        if not clip["hold"]:  # a one-shot clip lands back at rest
            for control, keys in clip["keys"].items():
                assert keys[-1][1] == buddy.REST[control] or control == "lean_x", (name, control)


def test_dry_squeezes_the_eyes_to_squares_and_happy_switches_to_arcs():
    assert buddy.clip_value("dry", "eye_h", 10) == pytest.approx(0.35)
    assert buddy.clip_value("happy", "eye_shape", 1) == 0  # stepped, never blended through other shapes
    assert buddy.clip_value("happy", "eye_shape", 2) == 1
    assert buddy.clip_value("shrink", "eye_shape", 6) == buddy.EYE_SHAPES.index("sad")
    assert buddy.clip_value("nod", "hop", 3) is None


@pytest.mark.parametrize("text,emotion,intensity,action,want", [
    ("That's great!", "neutral", 0.5, "", "hop"),
    ("Well...", "happy", 0.9, "", "think"),
    ("Sure.", "happy", 0.2, "", "dry"),
    ("Sure.", "happy", 0.6, "", "happy"),
    ("Hmm.", "confused", 0.5, "", "tilt"),
    ("Okay.", "neutral", 0.5, "", "nod"),
    ("Wow!", "sad", 0.1, "nod", "nod"),  # an explicit action always wins
])
def test_pick_action(text, emotion, intensity, action, want):
    assert buddy.pick_action(text, emotion, intensity, action) == want


def test_pick_action_rejects_unknown_clips():
    with pytest.raises(ValueError, match="unknown buddy action"):
        buddy.pick_action("hi", action="backflip")


def test_wav_envelope_tracks_loudness(tmp_path):
    rate, path = 16000, tmp_path / "line.wav"
    samples = array.array("h")
    for i in range(rate):  # 0.5 s of tone at full scale, then 0.5 s at a quarter
        amp = 30000 if i < rate // 2 else 7500
        samples.append(int(amp * math.sin(2 * math.pi * 220 * i / rate)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(samples.tobytes())
    env = buddy.wav_envelope(path, FPS)
    assert len(env) == FPS
    assert max(env) == pytest.approx(1.0)
    assert env[5] == pytest.approx(1.0, abs=0.02) and env[25] == pytest.approx(0.25, abs=0.02)


def test_talk_squash_is_3_to_6_percent_with_fast_attack_and_slower_release():
    env = [0.0] * 5 + [1.0] * 15 + [0.0] * 20
    sq = buddy.talk_squash(env)
    assert sq[4] == 0.0 and max(sq) <= buddy.TALK_MAX + 1e-9
    assert sq[6] >= buddy.TALK_MIN  # within 2 frames of the sound
    assert sq[19] == pytest.approx(buddy.TALK_MAX, abs=0.003)
    fall = next(i for i in range(20, 40) if sq[i] == 0.0) - 20
    assert 8 <= fall <= 20  # release: a 5-frame time constant takes ~15 frames to reach silence
    assert buddy.talk_squash([0.3] * 30)[-1] == pytest.approx(0.039, abs=0.002)


def test_syllable_envelope_is_deterministic_and_pauses_at_punctuation():
    a = buddy.syllable_envelope("That's great, honestly!", FPS)
    assert a == buddy.syllable_envelope("That's great, honestly!", FPS)
    assert 0.0 in a and max(a) <= 1.0 and 0.4 * FPS < len(a) < 2.0 * FPS


def test_blinks_are_2_8_to_4_2_seconds_apart():
    b = buddy.blink_frames(30 * FPS, FPS, seed=3)
    gaps = [(y - x) / FPS for x, y in zip(b, b[1:])]
    assert len(b) >= 6 and all(2.8 <= g <= 4.2 + 1 / FPS for g in gaps)


def _segments():
    env = buddy.syllable_envelope("Nice! That's great.", FPS)
    return [{"start": 0, "end": 18, "speaking": False, "env": None, "action": ""},
            {"start": 18, "end": 18 + len(env), "speaking": True, "env": env, "action": "hop"},
            {"start": 18 + len(env), "end": 180, "speaking": False, "env": None, "action": "dry"}]


def test_animate_is_deterministic_bounded_and_mirrors_toward_the_hero():
    a = buddy.animate(180, FPS, _segments(), seed=7, hero_side=1)
    assert a == buddy.animate(180, FPS, _segments(), seed=7, hero_side=1)
    assert set(a) == set(buddy.CONTROLS) and all(len(v) == 180 for v in a.values())
    assert all(-0.15 <= v <= 0.3 for v in a["squash"])
    assert all(0.0 <= v <= 1.0 for v in a["eye_h"]) and min(a["eye_h"]) == 0.0  # it blinks
    assert max(a["hop"]) == pytest.approx(1.0, abs=0.01)
    assert all(0.0 <= v <= 1.0 for v in a["voice"]) and max(a["voice"]) > 0.5 and max(a["voice"][:18]) == 0.0
    assert set(a["eye_shape"]) <= {0.0, 1.0, 2.0, 3.0, 4.0}
    assert all(y > x for x, y in zip(a["phase"], a["phase"][1:]))  # the signature angle only moves forward
    b = buddy.animate(180, FPS, _segments(), seed=7, hero_side=-1)
    assert b["lean_x"] == [-v for v in a["lean_x"]] and b["squash"] == a["squash"]


def test_animate_talks_only_while_speaking_and_holds_dry_to_the_end():
    a = buddy.animate(180, FPS, _segments(), seed=7)
    assert max(a["squash"][:18]) < 0.01  # idle breath only
    talk_end = 18 + len(buddy.syllable_envelope("Nice! That's great.", FPS))
    assert max(a["squash"][20:talk_end]) >= buddy.TALK_MAX - 0.005
    assert max(a["sig"][20:talk_end]) > 0.5 and a["sig"][5] < 0.05
    eyes = [v for f, v in enumerate(a["eye_h"]) if talk_end + 10 < f < 178]
    assert max(eyes) == pytest.approx(0.35, abs=0.01)  # dry holds (blinks dip below it)
