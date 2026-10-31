import pytest

from reelforge import blender_run


def test_find_blender_prefers_env(monkeypatch, tmp_path):
    exe = tmp_path / "blender.exe"; exe.write_text("")
    monkeypatch.setenv("REELFORGE_BLENDER", str(exe))
    assert blender_run.find_blender() == str(exe)


def test_find_blender_missing_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("REELFORGE_BLENDER", str(tmp_path / "nope.exe"))
    monkeypatch.setattr(blender_run.shutil, "which", lambda _: None)
    with pytest.raises(FileNotFoundError, match="REELFORGE_BLENDER"):
        blender_run.find_blender()


def test_run_blender_command(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(blender_run, "find_blender", lambda: "B")
    monkeypatch.setattr(blender_run.subprocess, "run", lambda cmd, check: seen.setdefault("cmd", cmd))
    blender_run.run_blender(tmp_path / "s.py", ["a", "b"], blend=tmp_path / "e.blend")
    assert seen["cmd"] == ["B", "-b", str(tmp_path / "e.blend"), "--factory-startup",
                           "--python-exit-code", "1", "-P", str(tmp_path / "s.py"), "--", "a", "b"]
