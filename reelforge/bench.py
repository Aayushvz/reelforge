"""`reelforge bench`: time a fixed set of stills (a wide and two close-ups in each room) for a look and quality.

Needs no voices: a synthetic two-character plan goes straight to blender/render_plan.py. Prints seconds per
still and the peak GPU memory (when nvidia-smi is present), and writes bench.json next to the stills."""
from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path

from .blender_run import run_blender
from .direct import Shot
from .engines import blender3d
from .plan import build_render_plan
from .schema import parse_performance

ROOMS = (("neon_tunnel", "neon"), ("gaming_den", "rgb_night"), ("cozy_gaming_room", "purple_neon"))
N_FRAMES = 90
# A light smile mid-word: enough to judge skin, eyes, teeth and lips.
POSE = {"jawOpen": 0.18, "mouthSmileLeft": 0.35, "mouthSmileRight": 0.35, "cheekSquintLeft": 0.2,
        "cheekSquintRight": 0.2, "browInnerUp": 0.15}


def bench_perf(room: str, lighting: str, look: str, quality: str, cast: tuple[str, str] = ("matt", "cute_girl")):
    chars = {n: {"voice_id": "bench", "model": m} for n, m in zip(("A", "B"), cast)}
    line = {"id": "l1", "speaker": "A", "text": "bench", "emotion": "happy", "intensity": 0.5, "mood": "calm"}
    return parse_performance({"environment": room, "lighting": lighting, "look": look, "quality": quality,
                              "characters": chars, "lines": [line]})


def bench_shots() -> list[Shot]:
    return [Shot(0, 30, "wide", 32, "A", 0.05, "drift", {}, 0.0, 0.15, 11, 0.5, 1.0),
            Shot(30, 60, "closeup", 85, "A", 0.05, "push_in", {"amount": 0.08}, 0.0, 0.15, 12, 0.5),
            Shot(60, 90, "closeup", 85, "B", 0.05, "static", {}, 0.0, 0.15, 13, 0.5)]


def bench_plan(room: str, lighting: str, look: str, quality: str, out: Path) -> dict:
    perf = bench_perf(room, lighting, look, quality)
    faces = {n: {k: [v] * N_FRAMES for k, v in POSE.items()} | {"headNod": [0.0] * N_FRAMES} for n in perf.characters}
    draft = quality == "preview"
    plan = build_render_plan(perf, N_FRAMES, faces, bench_shots(), [(0, "calm")], blender3d.ASSETS, out,
                             16 if draft else 64)
    plan["resolution_percentage"] = 50 if draft else 100
    return plan


def parse_still_lines(lines: list[str]) -> list[dict]:
    """'STILL 1 closeup CYCLES 8.31s' -> {"shot": 1, "kind": "closeup", "engine": "CYCLES", "seconds": 8.31}"""
    rows = []
    for ln in lines:
        p = ln.split()
        if len(p) == 5 and p[0] == "STILL" and p[4].endswith("s"):
            rows.append({"shot": int(p[1]), "kind": p[2], "engine": p[3], "seconds": float(p[4][:-1])})
    return rows


class _VramPoll(threading.Thread):
    """Peak GPU memory in MiB while Blender runs; None when nvidia-smi isn't available."""

    def __init__(self):
        super().__init__(daemon=True)
        self.peak, self._stop = None, threading.Event()

    def run(self):
        while not self._stop.is_set():
            try:
                r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=5)
                self.peak = max(self.peak or 0, int(r.stdout.split()[0]))
            except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
                return
            self._stop.wait(1.0)

    def stop(self):
        self._stop.set()


def bench(look: str, quality: str, out_root: Path, rooms=ROOMS, only: str | None = None) -> dict:
    out_root = Path(out_root)
    rooms = [r for r in rooms if only in (None, r[0])]
    results = {"look": look, "quality": quality, "stills": [], "peak_vram_mib": None}
    for room, lighting in rooms:
        env = blender3d.ASSETS / f"{room}__{lighting}.blend"
        if not env.exists():
            print(f"skip {room}: {env.name} not built (run `reelforge build-assets`)")
            continue
        out = out_root / f"{look}-{quality}" / room
        out.mkdir(parents=True, exist_ok=True)
        plan = bench_plan(room, lighting, look, quality, out)
        (out / "render_plan.json").write_text(json.dumps(plan), encoding="utf-8")
        lines: list[str] = []
        poll = _VramPoll()
        poll.start()
        t0 = time.time()
        run_blender(blender3d.BLENDER_DIR / "render_plan.py", [str(out / "render_plan.json"), "stills"],
                    blend=env, on_line=lines.append)
        poll.stop()
        for row in parse_still_lines(lines):
            results["stills"].append({"room": room, **row})
        results["stills"].append({"room": room, "kind": "total incl. load", "engine": "-",
                                  "seconds": round(time.time() - t0, 1)})
        if poll.peak is not None:
            results["peak_vram_mib"] = max(results["peak_vram_mib"] or 0, poll.peak)
    (out_root / f"{look}-{quality}" / "bench.json").parent.mkdir(parents=True, exist_ok=True)
    (out_root / f"{look}-{quality}" / "bench.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    for r in results["stills"]:
        print(f"bench {look}/{quality} {r['room']:18} {r['kind']:18} {r['engine']:20} {r['seconds']:7.2f}s")
    print(f"bench peak VRAM: {results['peak_vram_mib']} MiB")
    return results
