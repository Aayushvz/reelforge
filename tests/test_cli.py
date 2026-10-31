import shutil

import pytest

from reelforge import cli


def test_parser_run_defaults(tmp_path):
    ns = cli.build_parser().parse_args(["run", str(tmp_path)])
    assert ns.cmd == "run" and ns.stage == "full" and ns.draft is False


def test_missing_api_key_exits(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    shutil.copy(cli.REPO / "samples" / "look-test" / "performance.json", tmp_path / "performance.json")
    with pytest.raises(SystemExit) as e:
        cli.main(["run", str(tmp_path), "--stage", "stills"])
    assert "ELEVENLABS_API_KEY" in str(e.value.code)


def test_imported_audio_used_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    src = cli.REPO / "samples" / "look-test"
    shutil.copy(src / "performance.json", tmp_path / "performance.json")
    (tmp_path / "out" / "audio").mkdir(parents=True)
    for mp3 in (src / "out" / "audio").glob("*.mp3"):
        shutil.copy(mp3, tmp_path / "out" / "audio" / mp3.name)
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

    monkeypatch.setattr(cli, "run_blender", stop)
    with pytest.raises(Stop):
        cli.main(["run", str(tmp_path), "--stage", "stills"])
    assert used == ["l01", "l02"]
