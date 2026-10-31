import json
from pathlib import Path

import pytest

from reelforge.arkit import ARKIT_NAMES
from reelforge.schema import PerformanceError, load_performance, parse_performance

SAMPLE = Path(__file__).parents[1] / "samples" / "look-test" / "performance.json"


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
