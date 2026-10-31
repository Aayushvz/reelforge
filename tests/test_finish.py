import json
import subprocess

from reelforge.captions import ass_header
from reelforge.finish import build_ffmpeg_cmd, finish


def test_cmd_contains_look_and_loudness():
    cmd = build_ffmpeg_cmd(30, "final.mp4")
    fc = cmd[cmd.index("-filter_complex") + 1]
    for token in ("gblur", "blend=all_mode=screen", "vignette", "noise=alls",
                  "ass=captions.ass", "loudnorm=I=-14:TP=-1.5"):
        assert token in fc
    assert cmd[-1] == "final.mp4" and "libx264" in cmd


def test_finish_produces_video_with_audio(tmp_path):
    (tmp_path / "frames").mkdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=navy:s=108x192:d=1:r=30", "-start_number", "1",
                    str(tmp_path / "frames" / "%04d.png")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=1", str(tmp_path / "dialogue.wav")], check=True)
    (tmp_path / "captions.ass").write_text(ass_header(108, 192), encoding="utf-8")
    out = finish(tmp_path, 30, "final.mp4")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                        "-of", "json", str(out)], capture_output=True, text=True, check=True)
    kinds = {s["codec_type"] for s in json.loads(r.stdout)["streams"]}
    assert kinds == {"video", "audio"}
