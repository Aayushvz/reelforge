"""Places (desk, sofa, bed, window bench): the script field, Auto's variety and imported rooms."""
import json
from types import SimpleNamespace

import pytest

from reelforge import angles
from reelforge.engines import shots_av
from reelforge.schema import PerformanceError, parse_performance

BASE = {"style": "shots-av", "characters": {"me": {"model": "av_hero"}, "claude": {"model": "buddy_claude"}},
        "lines": [{"speaker": "me", "text": "hi"}]}


def test_schema_place_defaults_to_desk_and_validates():
    assert parse_performance(BASE).place == "desk"  # old reels stay at the desk
    assert parse_performance({**BASE, "place": "sofa"}).place == "sofa"
    with pytest.raises(PerformanceError):
        parse_performance({**BASE, "place": "rooftop"})


def _perf(place, env="av_studio_night"):
    return SimpleNamespace(place=place, environment=env)


def test_auto_avoids_the_last_reels_places(tmp_path, monkeypatch):
    hist = tmp_path / ".angle_history.json"
    monkeypatch.setattr(angles, "_history_file", lambda: hist)
    hist.write_text(json.dumps([{"project": "a", "angles": [], "place": "sofa"},
                                {"project": "b", "angles": [], "place": "window"}]))
    picks = {shots_av.resolve_place(_perf("auto"), tmp_path / "c", seed) for seed in range(8)}
    assert picks and not picks & {"sofa", "window"}
    assert shots_av.resolve_place(_perf("bed"), tmp_path / "c", 0) == "bed"  # a chosen place is kept


def test_imported_rooms_keep_their_desk():
    imported = next(k for k, v in shots_av.room_tables()["ROOMS"].items() if v.get("imported"))
    assert shots_av.resolve_place(_perf("sofa", imported), None, 0) == "desk"


def test_history_records_the_place(tmp_path, monkeypatch):
    hist = tmp_path / ".angle_history.json"
    monkeypatch.setattr(angles, "_history_file", lambda: hist)
    shot = SimpleNamespace(angle="hero_34")
    angles.remember_angles(tmp_path / "reel1", [shot], "bed")
    assert angles.recent_places(tmp_path / "reel2") == ["bed"]
    assert angles.recent_places(tmp_path / "reel1") == []  # a reel never avoids itself
