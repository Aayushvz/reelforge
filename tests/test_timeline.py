import subprocess

import pytest

from reelforge.schema import Line
from reelforge.timeline import mix_dialogue, place_lines, probe_duration
from reelforge.voice import VoicedLine

L1 = Line("l01", "LEAD", "a", "neutral", 0.5, "calm", pause_after=0.4)
L2 = Line("l02", "LEAD", "b", "happy", 0.9, "success", pause_after=0.6)


def _sine(path, seconds=1.0, freq=440):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency={freq}:duration={seconds}", "-c:a", "libmp3lame", str(path)],
                   check=True)
    return path


def test_place_lines_sequential(tmp_path):
    voiced = {"l01": VoicedLine("l01", tmp_path / "a.mp3", []),
              "l02": VoicedLine("l02", tmp_path / "b.mp3", [])}
    placed, total = place_lines([L1, L2], voiced, {"l01": 1.0, "l02": 2.0})
    assert [p.start for p in placed] == pytest.approx([0.4, 1.8])
    assert total == pytest.approx(1.8 + 2.0 + 0.6 + 0.8)


def test_mix_dialogue_has_expected_length(tmp_path):
    a, b = _sine(tmp_path / "a.mp3"), _sine(tmp_path / "b.mp3", freq=660)
    voiced = {"l01": VoicedLine("l01", a, []), "l02": VoicedLine("l02", b, [])}
    durs = {"l01": probe_duration(a), "l02": probe_duration(b)}
    placed, total = place_lines([L1, L2], voiced, durs)
    out = mix_dialogue(placed, total, tmp_path / "dialogue.wav")
    assert probe_duration(out) == pytest.approx(total, abs=0.05)
