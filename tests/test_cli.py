import shutil
import subprocess

import pytest

from reelforge import cli


def test_parser_run_defaults(tmp_path):
    ns = cli.build_parser().parse_args(["run", str(tmp_path)])
    assert ns.cmd == "run" and ns.stage == "full" and ns.draft is False


def test_missing_api_key_exits(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    shutil.copy(cli.REPO / "tests" / "fixtures" / "blender3d_performance.json", tmp_path / "performance.json")
    with pytest.raises(SystemExit) as e:
        cli.main(["run", str(tmp_path), "--stage", "stills"])
    assert "ELEVENLABS_API_KEY" in str(e.value.code)


def test_imported_audio_used_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    shutil.copy(cli.REPO / "tests" / "fixtures" / "blender3d_performance.json", tmp_path / "performance.json")
    audio = tmp_path / "out" / "audio"
    audio.mkdir(parents=True)
    for lid in ("l01", "l02"):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
             "-t", "1", "-c:a", "libmp3lame", str(audio / f"{lid}.mp3")], check=True)
    used = []
    real_import = cli.import_line

    def fake_import(line, audio_dir, transcribe=None):
        used.append(line.id)
        return real_import(line, audio_dir, transcribe=lambda p: [("hi", 0.1, 0.4)])

    monkeypatch.setattr(cli, "import_line", fake_import)

    class Stop(Exception):
        pass

    def stop(*a, **k):
        raise Stop

    monkeypatch.setattr(cli.ENGINES["blender3d"], "render", stop)
    with pytest.raises(Stop):
        cli.main(["run", str(tmp_path), "--stage", "stills"])
    assert used == ["l01", "l02"]


def test_style_defaults_to_blender3d_and_unknown_style_exits(tmp_path):
    from reelforge.schema import load_performance
    from reelforge.engines import get_engine
    perf = load_performance(cli.REPO / "tests" / "fixtures" / "blender3d_performance.json")
    assert perf.style == "blender3d" and get_engine(perf.style).ID == "blender3d"
    with pytest.raises(SystemExit) as e:
        get_engine("nope")
    assert "blender3d" in str(e.value.code)


def test_character_model_defaults_to_matt_and_reaches_the_plan(tmp_path):
    from reelforge.plan import build_render_plan
    from reelforge.schema import parse_performance
    perf = parse_performance({"characters": {"A": {"voice_id": "v", "model": "freya"}, "B": {"voice_id": "w"}},
                              "lines": [{"id": "l1", "speaker": "A", "text": "hi", "emotion": "happy",
                                         "intensity": 0.5, "mood": "calm"}]})
    plan = build_render_plan(perf, 1, {"A": {}, "B": {}}, [], [], tmp_path, tmp_path, 16)
    assert [c["blend"] for c in plan["characters"]] == [str(tmp_path / "freya.blend"), str(tmp_path / "matt.blend")]


def test_old_cast_and_sets_are_gone():
    from reelforge.engines import blender3d
    assert set(blender3d.cast_ids()) == {"matt", "freya", "cute_girl"} and blender3d.set_presets() == {}
    for gone in ("cast.py", "build_character.py", "build_set.py", "sets.py", "import_set.py"):
        assert not (cli.REPO / "blender" / gone).exists(), gone


def test_voices_command_reports_each_line(monkeypatch, tmp_path, capsys):
    import json as _json
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    shutil.copy(cli.REPO / "tests" / "fixtures" / "blender3d_performance.json", tmp_path / "performance.json")
    with pytest.raises(SystemExit) as e:
        cli.main(["voices", str(tmp_path)])
    assert e.value.code == 1
    rows = [_json.loads(x) for x in capsys.readouterr().out.splitlines()]
    assert [r["line"] for r in rows] == ["l01", "l02"] and all(r["status"] == "error" for r in rows)


def test_cached_api_take_runs_without_key(monkeypatch, tmp_path):
    from reelforge.schema import load_performance
    from reelforge.voice import take_path
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    shutil.copy(cli.REPO / "tests" / "fixtures" / "blender3d_performance.json", tmp_path / "performance.json")
    perf = load_performance(tmp_path / "performance.json")
    audio = tmp_path / "out" / "audio"
    audio.mkdir(parents=True)
    for l in perf.lines:
        mp3 = take_path(l, perf.characters[l.speaker].voice_id, audio)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-t", "1", "-c:a", "libmp3lame", str(mp3)], check=True)
        mp3.with_suffix(".json").write_text(_align(l.text), encoding="utf-8")

    class Stop(Exception):
        pass

    def stop(*a, **k):
        raise Stop

    monkeypatch.setattr(cli.ENGINES["blender3d"], "render", stop)
    with pytest.raises(Stop):
        cli.main(["run", str(tmp_path), "--stage", "stills"])


def _align(text):
    import json as _json
    st = [i * 0.05 for i in range(len(text))]
    return _json.dumps({"characters": list(text), "character_start_times_seconds": st,
                        "character_end_times_seconds": [s + 0.05 for s in st]})
