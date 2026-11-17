"""The face-visibility check, run in real Blender (skipped when Blender isn't installed)."""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _blender():
    exe = os.environ.get("REELFORGE_BLENDER")
    if not exe:
        f = REPO / "tools" / "blender_path.txt"
        exe = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    return exe if exe and Path(exe).exists() else None


@pytest.mark.skipif(_blender() is None, reason="Blender not installed")
def test_blocked_face_is_detected_and_fixable(tmp_path):
    out = tmp_path / "cv.json"
    subprocess.run([_blender(), "-b", "--factory-startup", "--python", str(REPO / "blender" / "test_clear_view.py"),
                    "--", str(out)], check=True, capture_output=True, timeout=240)
    r = json.loads(out.read_text())
    assert r["clear"]["score"] >= 0.99 and not r["clear"]["blockers"]  # the room shell never blocks
    assert r["blocked"]["score"] < 0.5 and "DeskLamp" in r["blocked"]["blockers"]
    assert r["hideable"] == ["DeskLamp"]  # a small prop may be hidden for the shot
    assert r["monitor_hideable"] == []  # a set piece never is
    assert r["ignored"]["score"] >= 0.99  # hidden prop: the face is clear again
    assert r["caption"]["caption"] > 0.35  # face under the caption band is caught
    assert r["variants"][:2] == ["swing +8", "swing -8"] and "dolly in" in r["variants"]
