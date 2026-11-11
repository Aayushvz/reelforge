from pathlib import Path

import pytest

from reelforge.bench import bench_plan, parse_still_lines
from reelforge.direct import LENSES_V2, MAX_SHOT_S, MIN_SHOT_S, plan_shots_v2
from reelforge.finish import build_ffmpeg_cmd
from reelforge.schema import CAMERA_MOVES, Line, PerformanceError, parse_performance
from reelforge.timeline import Placed
from reelforge.voice import VoicedLine

FPS = 30


def _placed(two=True):
    rows = [("l1", "A", "calm", 0.5, False, 0.3, 2.6), ("l2", "B" if two else "A", "awkward", 0.6, False, 3.2, 7.4),
            ("l3", "A", "reveal", 0.9, True, 11.0, 2.4), ("l4", "B" if two else "A", "sad", 0.4, False, 13.8, 1.6)]
    v = lambda i: VoicedLine(i, Path("x.mp3"), [])  # noqa: E731
    return [Placed(Line(i, who, "t", "neutral", inten, mood, punchline=punch), v(i), start, dur)
            for i, who, mood, inten, punch, start, dur in rows], int(16.0 * FPS)


@pytest.mark.parametrize("two", [True, False])
def test_shots_cover_the_timeline_within_length_limits(two):
    placed, n = _placed(two)
    shots = plan_shots_v2(placed, FPS, n, ["A", "B"] if two else ["A"], seed=5)
    assert shots[0].start_frame == 0 and shots[-1].end_frame == n
    assert all(a.end_frame == b.start_frame for a, b in zip(shots, shots[1:]))
    assert all(s.end_frame - s.start_frame <= MAX_SHOT_S * FPS for s in shots)
    assert all(s.end_frame - s.start_frame >= MIN_SHOT_S * FPS for s in shots)


def test_grammar_establishing_wide_punchline_push_in_and_no_repeats():
    placed, n = _placed()
    shots = plan_shots_v2(placed, FPS, n, ["A", "B"], seed=5)
    assert shots[0].kind == "wide" and shots[0].ease == 1.0
    punch = next(s for s in shots if s.start_frame >= 11.0 * FPS - 4 and s.subject == "A")
    assert punch.kind == "closeup" and punch.move == "push_in" and punch.move_params["amount"] >= 0.10
    assert all(not (a.kind == b.kind and a.subject == b.subject) for a, b in zip(shots, shots[1:]))
    assert all(a.move != b.move or a.move == "static" for a, b in zip(shots, shots[1:]))
    assert all(s.move in CAMERA_MOVES and s.lens == LENSES_V2[s.kind] for s in shots)


def test_long_line_cuts_away_to_the_listener():
    placed, n = _placed()
    shots = plan_shots_v2(placed, FPS, n, ["A", "B"], seed=5)
    during_b = [s for s in shots if 3.2 * FPS <= s.start_frame < 10.5 * FPS]
    assert any(s.subject == "A" and s.move == "static" for s in during_b)  # A listens while B talks


def test_plan_is_deterministic_and_seed_changes_it():
    placed, n = _placed()
    a = plan_shots_v2(placed, FPS, n, ["A", "B"], seed=5)
    assert a == plan_shots_v2(placed, FPS, n, ["A", "B"], seed=5)
    assert any(a != plan_shots_v2(placed, FPS, n, ["A", "B"], seed=s) for s in (6, 7, 8))


def test_overrides_and_handheld_reach_the_shots():
    placed, n = _placed()
    cam = {"handheld": 0.4, "overrides": {"1": {"move": "orbit", "intensity": 1.5, "kind": "ecu", "fstop": 5.6}}}
    shots = plan_shots_v2(placed, FPS, n, ["A", "B"], seed=5, camera=cam)
    assert shots[1].move == "orbit" and shots[1].kind == "ecu" and shots[1].lens == LENSES_V2["ecu"]
    assert shots[1].move_params == {"intensity": 1.5} and shots[1].fstop == 5.6
    assert all(s.handheld == 0.4 for s in shots)


BASE = {"characters": {"A": {"voice_id": "v"}},
        "lines": [{"id": "l", "speaker": "A", "text": "t", "emotion": "happy", "intensity": 0.5, "mood": "calm"}]}


def test_schema_defaults_keep_the_classic_look():
    p = parse_performance(BASE)
    assert (p.look, p.quality, p.camera, p.look_params) == ("classic", "standard", {}, {})


def test_schema_accepts_the_cinema_look_and_rejects_bad_values():
    p = parse_performance({**BASE, "look": "cinema", "quality": "cinema", "look_params": {"skin_glow": 1.2},
                           "camera": {"seed": 3, "handheld": 0.2, "overrides": {"0": {"move": "orbit"}}}})
    assert p.look == "cinema" and p.camera["overrides"]["0"]["move"] == "orbit"
    for bad in ({"look": "toon"}, {"quality": "ultra"}, {"camera": {"handheld": 2}},
                {"camera": {"overrides": {"x": {}}}}, {"camera": {"overrides": {"0": {"move": "spin"}}}},
                {"camera": {"overrides": {"0": {"kind": "macro"}}}}, {"camera": {"overrides": {"0": {"subject": "Z"}}}},
                {"look_params": {"skin_glow": "high"}}):
        with pytest.raises(PerformanceError):
            parse_performance({**BASE, **bad})


def test_bench_plan_carries_look_and_quality(tmp_path):
    plan = bench_plan("neon_tunnel", "neon", "cinema", "preview", tmp_path)
    assert plan["look"] == "cinema" and plan["quality"] == "preview" and plan["resolution_percentage"] == 50
    assert [s["kind"] for s in plan["shots"]] == ["wide", "closeup", "closeup"]
    assert plan["shots"][1]["move"] == "push_in" and len(plan["characters"]) == 2


def test_bench_reads_still_timings():
    rows = parse_still_lines(["Fra:1 Mem:1", "STILL 1 closeup CYCLES 8.31s", "STILL x"])
    assert rows == [{"shot": 1, "kind": "closeup", "engine": "CYCLES", "seconds": 8.31}]


def test_cinema_finish_is_lighter_tagged_and_classic_is_unchanged():
    arg = lambda c, k: c[c.index(k) + 1]  # noqa: E731
    classic, cinema = build_ffmpeg_cmd(30, "f.mp4", "cafe"), build_ffmpeg_cmd(30, "f.mp4", "cafe", "cinema")
    assert arg(classic, "-crf") == "16" and "-colorspace" not in classic and "noise=alls=5" in arg(classic, "-filter_complex")
    g = arg(cinema, "-filter_complex")
    assert arg(cinema, "-crf") == "14" and arg(cinema, "-colorspace") == "bt709"
    assert "noise=alls=2" in g and "all_opacity=0.16" in g and "sws_dither=ed" in g and "colorbalance" in g
