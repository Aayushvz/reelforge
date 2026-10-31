from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .schema import Line
from .voice import VoicedLine

LEAD_IN = 0.4
TAIL = 0.8


@dataclass(frozen=True)
class Placed:
    line: Line
    voiced: VoicedLine
    start: float
    duration: float


def probe_duration(path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def place_lines(lines: list[Line], voiced: dict[str, VoicedLine],
                durations: dict[str, float]) -> tuple[list[Placed], float]:
    t = LEAD_IN
    placed: list[Placed] = []
    for line in lines:
        d = durations[line.id]
        placed.append(Placed(line, voiced[line.id], t, d))
        t += d + line.pause_after
    return placed, t + TAIL


def mix_dialogue(placed: list[Placed], total: float, out_wav: Path) -> Path:
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p in placed:
        cmd += ["-i", str(p.voiced.audio_path)]
    parts = []
    for i, p in enumerate(placed):
        ms = int(round(p.start * 1000))
        parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,"
                     f"adelay={ms}:all=1[a{i}]")
    ins = "".join(f"[a{i}]" for i in range(len(placed)))
    parts.append(f"{ins}amix=inputs={len(placed)}:normalize=0:duration=longest,"
                 f"apad=whole_dur={total:.3f}[out]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[out]", "-t", f"{total:.3f}",
            "-ar", "48000", str(out_wav)]
    subprocess.run(cmd, check=True)
    return Path(out_wav)
