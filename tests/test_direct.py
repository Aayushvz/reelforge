from pathlib import Path

from reelforge.direct import mood_keys, plan_shots
from reelforge.moods import MOOD_PRESETS
from reelforge.plan import build_render_plan
from reelforge.schema import MOODS, Line, load_performance
from reelforge.timeline import Placed
from reelforge.voice import VoicedLine

FPS, N = 30, 216


def _placed():
    l1 = Line("l01", "LEAD", "a", "deadpan", 0.5, "calm")
    l2 = Line("l02", "LEAD", "b", "happy", 0.9, "success", punchline=True)
    v = lambda i: VoicedLine(i, Path("x.mp3"), [])  # noqa: E731
    return [Placed(l1, v("l01"), 0.4, 1.0), Placed(l2, v("l02"), 1.8, 4.0)]


def test_shots_cover_timeline_contiguously():
    s = plan_shots(_placed(), FPS, N)
    assert s[0].start_frame == 0 and s[-1].end_frame == N
    assert all(a.end_frame == b.start_frame for a, b in zip(s, s[1:]))


def test_no_shot_longer_than_three_seconds():
    assert all(sh.end_frame - sh.start_frame <= 3 * FPS for sh in plan_shots(_placed(), FPS, N))


def test_first_shot_wide_punchline_closeup():
    s = plan_shots(_placed(), FPS, N)
    assert s[0].kind == "wide" and s[0].lens == 35
    punch = next(sh for sh in s if sh.start_frame >= 50)
    assert punch.kind == "closeup" and punch.lens == 85


def test_mood_keys():
    assert mood_keys(_placed(), FPS) == [(0, "calm"), (50, "success")]


def test_every_mood_has_preset():
    assert set(MOODS) == set(MOOD_PRESETS)


def test_render_plan_shape(tmp_path):
    perf = load_performance(Path(__file__).parents[1] / "samples/look-test/performance.json")
    faces = {"LEAD": {"jawOpen": [0.0] * N, "headNod": [0.0] * N}}
    plan = build_render_plan(perf, N, faces, plan_shots(_placed(), FPS, N),
                             mood_keys(_placed(), FPS), tmp_path / "assets", tmp_path / "out", 16)
    assert plan["resolution"] == [1080, 1920] and plan["n_frames"] == N
    assert plan["characters"][0]["name"] == "LEAD" and plan["characters"][0]["mark"] == "Mark_A"
    assert plan["shots"][0]["kind"] == "wide"
    assert plan["environment_blend"].endswith("night_city.blend")
