from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def find_blender() -> str:
    env = os.environ.get("REELFORGE_BLENDER")
    if env and Path(env).exists():
        return env
    found = shutil.which("blender")
    if found:
        return found
    raise FileNotFoundError("Blender 4.5 not found: set REELFORGE_BLENDER to blender.exe")


def run_blender(script: Path, args: list[str], blend: Path | None = None) -> None:
    cmd = [find_blender(), "-b"]
    if blend is not None:
        cmd.append(str(blend))
    cmd += ["--factory-startup", "--python-exit-code", "1", "-P", str(script), "--", *args]
    subprocess.run(cmd, check=True)
