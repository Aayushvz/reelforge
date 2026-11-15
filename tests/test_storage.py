import json
import subprocess

import pytest

from reelforge import storage
from reelforge.engines import blender3d
from reelforge.finish import build_ffmpeg_cmd


def _frames(out, n=12, fps=12):
    """n tiny PNGs whose content changes every frame (testsrc2 draws a moving pattern)."""
    (out / "frames").mkdir(parents=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=s=96x160:r={fps}",
                    "-frames:v", str(n), "-start_number", "1", str(out / "frames" / "%04d.png")], check=True)


def _psnr(a, b) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b), "-lavfi",
                        "[0:v]format=rgb24[x];[1:v]format=rgb24[y];[x][y]psnr", "-f", "null", "-"],
                       capture_output=True, text=True)
    v = r.stderr.split("average:")[1].split()[0]
    return float("inf") if v == "inf" else float(v)


def test_pack_frames_makes_master_and_drops_pngs(tmp_path):
    _frames(tmp_path)
    freed = storage.pack_frames(tmp_path, 12, want=12)
    assert not (tmp_path / "frames").exists()
    assert storage.frame_count(tmp_path / storage.MASTER) == 12
    assert freed > 0
    assert storage.master_ok(tmp_path, 12) and not storage.master_ok(tmp_path, 13)


def test_pack_refuses_an_incomplete_render(tmp_path):
    _frames(tmp_path, n=5)
    with pytest.raises(RuntimeError):
        storage.pack_frames(tmp_path, 12, want=12)
    assert storage.png_count(tmp_path / "frames") == 5 and not (tmp_path / storage.MASTER).exists()


def test_still_from_master_is_the_same_frame(tmp_path):
    _frames(tmp_path)
    keep = tmp_path / "orig_0007.png"
    keep.write_bytes((tmp_path / "frames" / "0007.png").read_bytes())
    assert storage.still(tmp_path, 6, 12) == tmp_path / "frames" / "0007.png"  # PNGs still there: served as-is
    storage.pack_frames(tmp_path, 12)
    s = storage.still(tmp_path, 6, 12)
    assert s == tmp_path / storage.STILLS / "0007.png"
    assert _psnr(s, keep) > 40  # the right frame, visually lossless (a neighbour scores far lower)
    assert _psnr(s, tmp_path / "orig_0007.png") > _psnr(storage.still(tmp_path, 7, 12), keep)


def test_finish_input_switches_to_master(tmp_path):
    _frames(tmp_path, n=3)
    assert storage.video_input(tmp_path, 30)[-1] == "frames/%04d.png"
    storage.pack_frames(tmp_path, 30)
    src = storage.video_input(tmp_path, 30)
    assert src == ["-i", storage.MASTER]
    cmd = build_ffmpeg_cmd(30, "final.mp4", src=src)
    assert cmd[cmd.index("-i") + 1] == storage.MASTER and "frames/%04d.png" not in cmd
    (tmp_path / storage.MASTER).unlink()
    with pytest.raises(FileNotFoundError):
        storage.video_input(tmp_path, 30)


def test_clean_keeps_only_the_final_voices_and_metadata(tmp_path):
    out = tmp_path / "out"
    _frames(out)
    (out / "audio").mkdir()
    (out / "audio" / "l1.mp3").write_bytes(b"voice")
    (out / "fonts").mkdir()
    (out / "fonts" / "a.ttf").write_bytes(b"f")
    for f in ("render_plan.json", "captions.ass", "foley.wav", "dialogue.wav", ".render_key_full"):
        (out / f).write_bytes(b"x" * 100)
    r = storage.clean(tmp_path, dry_run=True)
    assert any("kept" in a for a in r["actions"]) and storage.png_count(out / "frames") == 12  # no final: untouched
    (out / "final_9x16.mp4").write_bytes(b"v")
    r = storage.clean(tmp_path, dry_run=True)
    assert r["freed"] > 0 and storage.png_count(out / "frames") == 12 and (out / "foley.wav").exists()
    r = storage.clean(tmp_path)
    left = sorted(p.relative_to(out).as_posix() for p in out.rglob("*"))
    assert left == ["audio", "audio/l1.mp3", "captions.ass", "final_9x16.mp4", "render_plan.json"]
    assert r["after"] < r["before"]


def test_a_render_newer_than_the_final_is_left_alone(tmp_path):
    import os
    out = tmp_path / "out"
    _frames(out)
    (out / "final_9x16.mp4").write_bytes(b"old")
    os.utime(out / "final_9x16.mp4", (1, 1))  # an older final, with a re-render in progress
    storage.clean(tmp_path)
    assert storage.png_count(out / "frames") == 12


def test_render_skips_when_the_master_matches(tmp_path, monkeypatch):
    env, char = tmp_path / "env.blend", tmp_path / "char.blend"
    env.write_bytes(b"e")
    char.write_bytes(b"c")
    plan = {"environment_blend": str(env), "characters": [{"blend": str(char)}], "n_frames": 3, "shots": [{}]}
    monkeypatch.setattr(blender3d, "build_render_plan", lambda *a, **k: dict(plan))
    calls = []
    monkeypatch.setattr(blender3d, "run_blender", lambda *a, **k: calls.append(a))
    out = tmp_path / "out"
    out.mkdir()
    blender3d.render(None, 3, {}, [], [], out, "full", False)
    assert len(calls) == 1  # nothing on disk: render
    _frames(out, n=3)
    storage.pack_frames(out, 30)
    blender3d.render(None, 3, {}, [], [], out, "full", False)
    assert len(calls) == 1  # same inputs, frames packed into the master: skip
    plan["shots"] = [{}, {}]
    blender3d.render(None, 3, {}, [], [], out, "full", False)
    assert len(calls) == 2 and not (out / storage.MASTER).exists()  # inputs changed: stale master dropped
