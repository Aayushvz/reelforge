from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .direct import Shot
from .moods import MOOD_PRESETS
from .schema import RATIOS, Performance

MARKS = ("Mark_A", "Mark_B")


def build_render_plan(perf: Performance, n_frames: int, faces: dict, shots: list[Shot],
                      moods: list[tuple[int, str]], assets_dir: Path, out_dir: Path,
                      samples: int) -> dict:
    return {
        "fps": perf.fps,
        "n_frames": n_frames,
        "resolution": list(RATIOS[perf.ratio]),
        "samples": samples,
        "environment_blend": str(Path(assets_dir) / (f"{perf.environment}__{perf.lighting}.blend" if perf.lighting
                                                     else f"{perf.environment}.blend")),
        "characters": [{"name": n, "mark": MARKS[i], "face": faces[n],
                        "blend": str(Path(assets_dir) / (f"{c.model}__o{c.outfit}.blend" if c.outfit
                                                          else f"{c.model}.blend"))}
                       for i, (n, c) in enumerate(perf.characters.items())],
        "shots": [asdict(s) for s in shots],
        "moods": [[f, m] for f, m in moods],
        "mood_presets": MOOD_PRESETS,
        "out_frames": str(Path(out_dir) / "frames"),
        "out_stills": str(Path(out_dir) / "stills"),
    }
