import json
import math
import subprocess
from pathlib import Path

import pytest

from reelforge import music
from reelforge.schema import Line, PerformanceError, parse_performance


def L(emotion="neutral", mood="calm", intensity=0.5, text="ok", punchline=False):
    return Line("l", "me", text, emotion, intensity, mood, punchline=punchline)


def T(tid, moods, energy=0.5, **kw):
    return music.Track(tid, tid, moods=moods, energy=energy, duration=120.0, **kw)


LIB = [T("fun", {"comedy": 1.0, "quirky": 0.5}, 0.55), T("cry", {"sad": 1.0}, 0.2), T("pump", {"hype": 1.0}, 0.9),
       T("chill", {"lofi": 1.0}, 0.25), T("tense", {"suspense": 1.0}, 0.5)]


def test_catalog_is_valid_and_no_credit():
    rows = json.loads((music.LIB / "catalog.json").read_text(encoding="utf-8"))
    assert len(rows) >= 30 and music.validate(rows) == []
    assert {g for r in rows for g in r["moods"]} == set(music.GENRES)  # every genre has tracks
    assert all(r["licence"] == "Mixkit Stock Music Free License" and not r["vocals"] for r in rows)


def test_validate_catches_bad_entries():
    errs = music.validate([{"id": "a", "title": "A", "file": "x.mp3", "moods": {"polka": 1}},
                           {"id": "a", "title": "B", "file": "y.mp3", "moods": {}, "source": "mixkit", "licence": "CC-BY"}])
    assert any("unknown genre" in e for e in errs) and any("duplicate" in e for e in errs)
    assert any("no-credit" in e for e in errs) and any("at least one genre" in e for e in errs)


@pytest.mark.parametrize("lines,want", [
    ([L("deadpan", "awkward", punchline=True), L("smug", "awkward"), L("embarrassed", "awkward", 0.7)], "fun"),
    ([L("sad", "sad", 0.8), L("sad", "sad", 0.6, "I miss how it was")], "cry"),
    ([L("happy", "success", 0.9, "We shipped it, let's go"), L("surprised", "success", 0.9)], "pump"),
    ([L("thinking", "calm", 0.3), L("neutral", "calm", 0.3)], "chill"),
    ([L("worried", "panic", 0.8, "the deadline is tonight"), L("worried", "panic", 0.7)], "tense"),
])
def test_script_picks_the_matching_genre(lines, want):
    assert music.rank(lines, 30, tracks=LIB)[0]["track"].id == want


def test_rank_is_deterministic_and_avoids_repeats():
    lines = [L("deadpan", "awkward", punchline=True)]
    a = music.rank(lines, 30, tracks=LIB)
    assert [r["track"].id for r in a] == [r["track"].id for r in music.rank(lines, 30, tracks=LIB)]
    alt = LIB + [T("fun2", {"comedy": 1.0}, 0.5)]
    assert music.rank(lines, 30, tracks=alt)[0]["track"].id == "fun"
    assert music.rank(lines, 30, recent=["fun"], tracks=alt)[0]["track"].id == "fun2"  # a near-equal fit wins
    assert music.rank(lines, 30, recent=["fun"], tracks=LIB)[0]["track"].id == "fun"  # never a bad fit instead
    viral = LIB + [T("v", {"comedy": 1.0, "quirky": 0.5}, 0.55, viral=True)]
    assert music.rank(lines, 30, tracks=viral)[0]["track"].id == "v"


def test_choose_modes(tmp_path, monkeypatch):
    monkeypatch.setattr(music, "library", lambda **k: LIB)
    monkeypatch.setattr(music, "HISTORY", tmp_path / "h.json")
    lines = [L("deadpan", "awkward", punchline=True)]
    assert music.choose(tmp_path, {}, lines, 30)[0] is None  # no music field: old projects stay silent
    assert music.choose(tmp_path, {"mode": "none"}, lines, 30)[0] is None
    assert music.choose(tmp_path, {"mode": "auto"}, lines, 30)[0].id == "fun"
    second = music.choose(tmp_path, {"mode": "auto", "pick": 1}, lines, 30)[0]
    assert second.id != "fun"  # shuffle walks the top 3
    assert music.choose(tmp_path, {"mode": "track", "id": "cry"}, lines, 30)[0].id == "cry"


def test_schema_music_field():
    base = {"style": "shots-av", "characters": {"me": {"model": "av_hero"}, "claude": {"model": "buddy_claude"}},
            "lines": [{"speaker": "me", "text": "hi"}]}
    assert parse_performance({**base, "music": {"mode": "auto", "volume": 0.7}}).music["volume"] == 0.7
    for bad in ({"mode": "loud"}, {"mode": "track"}, {"volume": 2}, {"duck": "yes"}):
        with pytest.raises(PerformanceError):
            parse_performance({**base, "music": bad})


def test_hook_finder():
    quiet_intro = [-40.0] * 10 + [-12.0] * 60
    assert music.find_hook(quiet_intro, -13.0, vocals=False) == 7.0
    chorus = [-20.0] * 30 + [-9.0] * 25 + [-20.0] * 30
    assert 25 <= music.find_hook(chorus, -15.0, vocals=True) <= 32
    assert music.find_hook([-12.0] * 10, -12.0, vocals=True) == 0.0  # short clip: from the top


def _tone(path, seconds, freq=440):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f={freq}:d={seconds}",
                    "-ar", "48000", str(path)], check=True)
    return path


def _rms_db(path, a, b):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(a), "-t", str(b - a), "-i", str(path), "-af",
                        "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    return float(r.stderr.split("mean_volume:")[1].split()[0])


def test_bed_ducks_under_speech_loops_and_has_length(tmp_path):
    src = _tone(tmp_path / "t.wav", 8)
    out = music.build_bed(music.Bed(src, start=0.0, duration=8.0), 20.0, [(5.0, 9.0)], 15.0, tmp_path / "bed.wav")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                       capture_output=True, text=True)
    assert abs(float(r.stdout) - 20.0) < 0.1  # 8 s source looped to the reel's 20 s
    pause, speech = _rms_db(out, 2.0, 4.0), _rms_db(out, 6.0, 8.5)
    assert pause - speech >= 6.0  # the duck
    assert _rms_db(out, 16.0, 18.0) > pause  # the end-card lift


def test_vocal_tracks_duck_deeper(tmp_path):
    src = _tone(tmp_path / "t.wav", 30)
    inst = music.build_bed(music.Bed(src, duration=30.0), 20.0, [(5.0, 10.0)], None, tmp_path / "a.wav")
    song = music.build_bed(music.Bed(src, duration=30.0, vocals=True), 20.0, [(5.0, 10.0)], None, tmp_path / "b.wav")
    d_inst = _rms_db(inst, 1.5, 4.0) - _rms_db(inst, 6.0, 9.5)
    d_song = _rms_db(song, 1.5, 4.0) - _rms_db(song, 6.0, 9.5)
    assert d_song > d_inst + 3.0


def test_import_update_remove_own_track(tmp_path):
    lib = tmp_path / "music"
    lib.mkdir()
    (lib / "trending.json").write_text(json.dumps([{"id": "viral_x", "title": "X Song", "artist": "Y",
                                                    "genres": {"hype": 1.0}}]))
    src = _tone(tmp_path / "upload.wav", 25)
    e = music.import_track(src, viral_id="viral_x", lib=lib)
    assert e["id"] == "viral_x" and e["viral"] and e["title"] == "X Song" and e["moods"] == {"hype": 1.0}
    assert music.trending(lib=lib)[0]["added"] is True
    assert [t.id for t in music.library(lib=lib)] == ["viral_x"]
    e2 = music.update_track("viral_x", {"moods": {"sad": 1.0}, "start": 4.0, "sha256": "nope"}, lib=lib)
    assert e2["start"] == 4.0 and e2["energy"] == music.GENRE_ENERGY["sad"] and e2["sha256"] != "nope"
    with pytest.raises(ValueError):
        music.update_track("viral_x", {"moods": {"polka": 1}}, lib=lib)
    with pytest.raises(KeyError):
        music.update_track("mixkit_1", {"start": 1}, lib=lib)  # built-ins are read-only
    music.remove_track("viral_x", lib=lib)
    assert music.library(lib=lib) == [] and not list((lib / "mine").glob("*.wav"))
