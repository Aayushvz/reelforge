from pathlib import Path

from reelforge.alignment import Char, Word
from reelforge.captions import ass_color, build_ass, group_words, ts
from reelforge.schema import load_performance
from reelforge.timeline import Placed
from reelforge.voice import VoicedLine

PERF = load_performance(Path(__file__).parent / "fixtures" / "blender3d_performance.json")


def _words(text, step=0.3):
    return [Word(w, i * step, i * step + 0.25) for i, w in enumerate(text.split())]


def test_ass_color_is_bgr():
    assert ass_color("#FFD23F") == "&H003FD2FF&"


def test_timestamp_format():
    assert ts(3.456) == "0:00:03.46" and ts(75.0) == "0:01:15.00"


def test_group_words_breaks_on_punctuation_and_size():
    groups = group_words(_words("Wait. They actually approved it right now"))
    assert [[w.text for w in g] for g in groups] == [
        ["Wait."], ["They", "actually", "approved", "it"], ["right", "now"]]


def test_build_ass_events_highlight_and_punchline():
    text = "Wait. They approved it!"
    cs = [Char(c, i * 0.06, (i + 1) * 0.06) for i, c in enumerate(text)]
    line = PERF.lines[1]  # punchline line
    placed = [Placed(line, VoicedLine("l02", Path("x.mp3"), cs), 1.0, len(text) * 0.06)]
    ass = build_ass(placed, PERF, 1080, 1920)
    assert "PlayResX: 1080" in ass and "PlayResY: 1920" in ass
    events = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    assert len(events) == 4  # one per word
    assert all("\\pos(540," in e for e in events)
    assert "&H003FD2FF&" in events[0]  # highlight color present
    assert any("\\frz" in e for e in events)  # punchline wobble
    assert "\\fscx" in events[0]  # pop-in on group start
