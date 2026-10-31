import json

import pytest

from reelforge.align_local import chars_from_words
from reelforge.schema import Line
from reelforge.voice import VoiceError, import_line

LINE = Line("l01", "LEAD", "[sighs] Hi yo", "deadpan", 0.5, "calm")


def test_chars_spread_evenly_with_spaces():
    cs = chars_from_words([(" Hi", 0.0, 0.2), (" yo.", 0.5, 0.8)])
    assert "".join(c.ch for c in cs) == "Hi yo."
    assert cs[0].start == pytest.approx(0.0) and cs[1].end == pytest.approx(0.2)
    assert cs[2].ch == " " and cs[2].start == pytest.approx(0.2) and cs[2].end == pytest.approx(0.5)
    assert cs[3].start == pytest.approx(0.5) and cs[-1].end == pytest.approx(0.8)


def test_import_line_aligns_and_caches(tmp_path):
    (tmp_path / "l01.mp3").write_bytes(b"ID3")
    calls = []

    def fake(path):
        calls.append(path)
        return [(" Hi", 0.1, 0.3), (" yo", 0.4, 0.6)]

    v = import_line(LINE, tmp_path, transcribe=fake)
    assert "".join(c.ch for c in v.chars) == "Hi yo" and v.audio_path == tmp_path / "l01.mp3"
    assert json.loads((tmp_path / "l01.align.json").read_text())[0][0] == " Hi"
    import_line(LINE, tmp_path, transcribe=fake)
    assert len(calls) == 1


def test_import_line_missing_audio(tmp_path):
    with pytest.raises(VoiceError, match="l01.mp3"):
        import_line(LINE, tmp_path, transcribe=lambda p: [])
