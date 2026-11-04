from __future__ import annotations

import os
import shutil
import subprocess
from collections import deque
from pathlib import Path


def find_blender() -> str:
    env = os.environ.get("REELFORGE_BLENDER")
    if env and Path(env).exists():
        return env
    found = shutil.which("blender")
    if found:
        return found
    raise FileNotFoundError("Blender 4.5 not found: set REELFORGE_BLENDER to blender.exe")


class BlenderError(RuntimeError):
    pass


def blender_cmd(script: Path, args: list[str], blend: Path | None = None) -> list[str]:
    cmd = [find_blender(), "-b"]
    if blend is not None:
        cmd.append(str(blend))
    return cmd + ["--factory-startup", "--python-exit-code", "1", "-P", str(script), "--", *args]


def run_blender(script: Path, args: list[str], blend: Path | None = None) -> None:
    """Stream Blender's output live; on failure raise with its last lines (the traceback)."""
    tail: deque[str] = deque(maxlen=25)
    with subprocess.Popen(blender_cmd(script, args, blend), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace") as proc:
        for line in proc.stdout:
            print(line, end="")
            tail.append(line)
    if proc.returncode:
        raise BlenderError(f"{Path(script).name} failed (exit {proc.returncode}):\n{''.join(tail)}")
