import pytest

from reelforge.a2f import frames_to_tracks


def test_resamples_to_fps_and_clamps():
    frames = [{"time": 0.0, "blendshapes": {"jawOpen": 0.0}},
              {"time": 0.1, "blendshapes": {"jawOpen": 1.2}}]
    tr = frames_to_tracks(frames, 30, 5)
    assert tr["jawOpen"][0] == 0.0
    assert tr["jawOpen"][1] == pytest.approx(1 / 3, abs=0.02)
    assert tr["jawOpen"][3] == 1.0 and tr["jawOpen"][4] == 1.0  # clamped, held after end


def test_ignores_unknown_names():
    tr = frames_to_tracks([{"time": 0.0, "blendshapes": {"notARKit": 1.0}}], 30, 2)
    assert "notARKit" not in tr
