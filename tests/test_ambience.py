import subprocess
import wave

from reelforge.ambience import BEDS, add_ambience, ambience_cmd


def test_every_set_has_a_bed_and_rain_adds_a_layer(tmp_path):
    for env in ("night_city", "bedroom", "rooftop", "cafe", "lantern_street", "subway", "classroom", "office",
                "night_mart", "pier"):
        assert env in BEDS
    dry, wet = ambience_cmd("cafe", "sunny_afternoon", 1, tmp_path / "a.wav"), ambience_cmd("cafe", "rainy_day", 1,
                                                                                                tmp_path / "a.wav")
    assert dry.count("-i") == 1 and wet.count("-i") == 2
    assert ambience_cmd("moon_base", "", 1, tmp_path / "a.wav") is None


def test_add_ambience_keeps_length_and_a_dry_copy(tmp_path):
    d = tmp_path / "dialogue.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=220:sample_rate=48000", "-t", "1.5",
                    "-ac", "1", str(d)], check=True)
    assert add_ambience(d, "pier", "sunset", 1.5)
    assert (tmp_path / "dialogue_dry.wav").exists()
    with wave.open(str(d)) as w:
        assert abs(w.getnframes() / w.getframerate() - 1.5) < 0.05
