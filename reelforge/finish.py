from __future__ import annotations

import subprocess
from pathlib import Path

# Halation/bloom: isolate highlights, blur, tint warm, screen back over the image.
FILTER = (
    "[0:v]format=gbrp,split=2[base][hi];"
    "[hi]curves=all='0/0 0.72/0 1/1',gblur=sigma=30,"
    "colorchannelmixer=rr=1:gg=0.45:bb=0.25[halo];"
    "[base][halo]blend=all_mode=screen:all_opacity=0.45,"
    "eq=contrast=1.04:saturation=1.06,"
    "vignette=angle=PI/5,"
    "noise=alls=5:allf=t,"
    "ass=captions.ass,"
    "format=yuv420p[v];"
    "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
)


def build_ffmpeg_cmd(fps: int, out_name: str) -> list[str]:
    return ["ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(fps), "-start_number", "1", "-i", "frames/%04d.png",
            "-i", "dialogue.wav",
            "-filter_complex", FILTER, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest",
            out_name]


def finish(workdir: Path, fps: int, out_name: str) -> Path:
    # Relative paths + cwd avoid Windows drive-letter escaping inside the ass= filter.
    subprocess.run(build_ffmpeg_cmd(fps, out_name), cwd=workdir, check=True)
    return Path(workdir) / out_name
