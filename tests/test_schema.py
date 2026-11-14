import json
from pathlib import Path

import pytest

from reelforge.arkit import ARKIT_NAMES
from reelforge.schema import PerformanceError, load_performance, parse_performance

SAMPLE = Path(__file__).parent / "fixtures" / "blender3d_performance.json"


def _base() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_arkit_has_52_unique_names():
    assert len(ARKIT_NAMES) == 52 and len(set(ARKIT_NAMES)) == 52


def test_sample_loads():
    p = load_performance(SAMPLE)
    assert p.fps == 30 and p.ratio == "9:16" and p.environment == "night_city"
    assert [l.id for l in p.lines] == ["l01", "l02"]
    assert p.lines[1].punchline is True
    assert p.characters["LEAD"].highlight_color == "#FFD23F"


def test_unknown_emotion_rejected():
    d = _base(); d["lines"][0]["emotion"] = "angry-ish"
    with pytest.raises(PerformanceError, match="emotion"):
        parse_performance(d)


def test_unknown_speaker_rejected():
    d = _base(); d["lines"][0]["speaker"] = "NOBODY"
    with pytest.raises(PerformanceError, match="unknown speaker"):
        parse_performance(d)


def test_intensity_range_enforced():
    d = _base(); d["lines"][0]["intensity"] = 1.5
    with pytest.raises(PerformanceError, match="intensity"):
        parse_performance(d)


def test_bad_ratio_rejected():
    d = _base(); d["ratio"] = "4:5"
    with pytest.raises(PerformanceError, match="ratio"):
        parse_performance(d)


def _perf(**line):
    base = {"id": "l1", "speaker": "A", "text": "hi", "emotion": "happy", "intensity": 0.5, "mood": "calm"}
    return {"characters": {"A": {"voice_id": "v"}}, "lines": [{**base, **line}]}


def test_bad_numbers_and_negative_pause_are_performance_errors():
    import pytest
    from reelforge.schema import PerformanceError, parse_performance
    for bad in ({"intensity": "loud"}, {"pause_after": "long"}, {"pause_after": -0.2}):
        with pytest.raises(PerformanceError):
            parse_performance(_perf(**bad))


def test_more_characters_than_marks_is_rejected():
    import pytest
    from reelforge.schema import PerformanceError, parse_performance
    data = _perf()
    data["characters"] = {k: {"voice_id": "v"} for k in ("A", "B", "C")}
    with pytest.raises(PerformanceError, match="at most 2"):
        parse_performance(data)
