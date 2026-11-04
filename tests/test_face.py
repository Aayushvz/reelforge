from pathlib import Path

from reelforge.alignment import Char
from reelforge.arkit import ARKIT_NAMES
from reelforge.face import blink_track, build_faces, spring
from reelforge.schema import Line, load_performance
from reelforge.timeline import Placed
from reelforge.voice import VoicedLine

PERF = load_performance(Path(__file__).parents[1] / "samples/look-test/performance.json")


def _placed(emotion="happy", intensity=0.9, text="mama mia", start=0.4):
    cs = [Char(c, i * 0.1, (i + 1) * 0.1) for i, c in enumerate(text)]
    line = Line("l01", "LEAD", text, emotion, intensity, "calm")
    return [Placed(line, VoicedLine("l01", Path("x.mp3"), cs), start, len(text) * 0.1)]


def test_spring_overshoots_then_settles():
    out = spring([0.0] * 5 + [1.0] * 60, 30)
    assert max(out) > 1.02
    assert abs(out[-1] - 1.0) < 0.01


def test_blinks_present_and_bounded():
    b = blink_track([], 30, 300)
    assert max(b) == 1.0 and min(b) == 0.0
    starts = sum(1 for i in range(1, 300) if b[i] > 0 and b[i - 1] == 0)
    assert starts >= 2


def test_build_faces_layers():
    faces = build_faces(PERF, _placed(), 30, 60)
    tr = faces["LEAD"]
    assert set(ARKIT_NAMES) <= set(tr) and "headNod" in tr
    assert all(len(v) == 60 for v in tr.values())
    assert tr["mouthSmileLeft"][30] > 0.3          # emotion layer
    assert max(tr["jawOpen"]) > 0.3                 # speech layer
    assert max(tr["mouthPressLeft"][12:20]) > 0.4   # 'm' at local 0.05s → global ~frame 13-14 (pressed closure)
    assert all(0.0 <= v <= 1.0 for n in ARKIT_NAMES for v in tr[n])


def test_lipsync_override_replaces_visemes():
    override = {"l01": {"jawOpen": [0.9] * 10}}
    tr = build_faces(PERF, _placed(emotion="neutral"), 30, 60, lipsync_override=override)["LEAD"]
    assert tr["jawOpen"][12] > 0.85
    assert max(tr["mouthClose"]) == 0.0
