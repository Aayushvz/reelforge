"""Disk use of a rendered project.

Blender writes every frame as a 2 MB PNG. Once the final video is made, everything that only served to build it is
deleted (the owner's rule: keep the final output, nothing else big). Kept: final_*.mp4, the voice takes in out/audio
(they cost ElevenLabs credits), and small metadata (render_plan.json, captions.ass, cover.json, preview stills).
A later change (new captions, grade or shots) re-renders. `pack_frames` / MASTER remain as an opt-in way to keep a
clean master instead (`reelforge run --keep-master`).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

MASTER = "clean_master.mkv"
MASTER_CRF = 12  # ~50 dB PSNR against the PNGs; the final itself is 4:2:0 at 11 Mbps
SCRATCH = ("dialogue_dry.wav", "foley.wav", "ambience.wav", "music_bed.wav", "dialogue.wav")  # rebuilt every run
BUILD_DIRS = ("frames", "fonts", "stills_cache")  # fonts: copied in for the caption burn on every finish
BUILD_FILES = (MASTER, ".render_key_full")  # no frames left, so the render cache key means nothing


def master_cmd(fps: float, frames: Path, dest: Path) -> list[str]:
    return ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", "1",
            "-i", str(Path(frames) / "%04d.png"), "-c:v", "libx264rgb", "-preset", "slow",
            "-crf", str(MASTER_CRF), "-g", str(max(1, round(fps))),  # a keyframe a second: fast cover seeks
            "-an", str(dest)]


def frame_count(video: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    try:
        return int(r.stdout.strip().split(",")[0])
    except ValueError:
        return 0


def png_count(frames: Path) -> int:
    return sum(1 for _ in Path(frames).glob("*.png")) if Path(frames).is_dir() else 0


def master_ok(out: Path, want: int) -> bool:
    m = Path(out) / MASTER
    return m.exists() and frame_count(m) >= want


def drop_master(out: Path) -> None:
    (Path(out) / MASTER).unlink(missing_ok=True)


def video_input(out: Path, fps: float) -> list[str]:
    """ffmpeg input args for the clean picture, relative to out/: the PNGs while they exist, else the master."""
    if (Path(out) / "frames" / "0001.png").exists():
        return ["-framerate", str(fps), "-start_number", "1", "-i", "frames/%04d.png"]
    if (Path(out) / MASTER).exists():
        return ["-i", MASTER]
    raise FileNotFoundError(f"no rendered frames or {MASTER} in {out}")


STILLS = "stills_cache"
STILLS_KEEP = 24  # scrubbing in the thumbnail editor makes one still per frame looked at: keep the newest few


def still(out: Path, frame: int, fps: float) -> Path | None:
    """A clean still of frame `frame` (0-based): the PNG while it exists, else cut from the master and cached."""
    out = Path(out)
    png = out / "frames" / f"{frame + 1:04d}.png"
    if png.exists():
        return png
    master = out / MASTER
    if not master.exists() or frame < 0:
        return None
    cache = out / STILLS
    dest = cache / f"{frame + 1:04d}.png"
    if dest.exists() and dest.stat().st_mtime >= master.stat().st_mtime:
        return dest
    cache.mkdir(exist_ok=True)
    # -ss before -i lands on the first frame at or after t: aim a quarter frame early to get exactly this one
    t = max(0.0, (frame - 0.25) / fps)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", str(master), "-frames:v", "1",
                    str(dest)], check=True)
    if not dest.exists():
        return None  # past the end (the end card): the caller falls back to the final video
    old = sorted(cache.glob("*.png"), key=lambda f: f.stat().st_mtime)[:-STILLS_KEEP]
    for f in old:
        f.unlink(missing_ok=True)
    return dest


def dir_bytes(path: Path) -> int:
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) if path.exists() else 0


def pack_frames(out: Path, fps: float, want: int | None = None) -> int:
    """Pack out/frames into the master, check its frame count, then delete the PNGs. Returns bytes freed."""
    out, frames = Path(out), Path(out) / "frames"
    n = png_count(frames)
    if not n:
        return 0
    if want is not None and n < want:
        raise RuntimeError(f"{frames}: {n} of {want} frames, refusing to pack an incomplete render")
    before = dir_bytes(frames)
    tmp = out / ("packing_" + MASTER)
    subprocess.run(master_cmd(fps, frames, tmp), check=True)
    got = frame_count(tmp)
    if got != n:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{tmp.name}: {got} frames, expected {n}; the PNGs were kept")
    tmp.replace(out / MASTER)
    shutil.rmtree(frames)
    return before - (out / MASTER).stat().st_size


def drop_scratch(out: Path) -> int:
    freed = 0
    for name in SCRATCH:
        f = Path(out) / name
        if f.exists():
            freed += f.stat().st_size
            f.unlink()
    return freed


def plan_frames(out: Path) -> int:
    try:
        return int(json.loads((Path(out) / "render_plan.json").read_text(encoding="utf-8")).get("n_frames") or 0)
    except (OSError, ValueError):
        return 0


def project_fps(project: Path) -> float:
    for f in (Path(project) / "out" / "render_plan.json", Path(project) / "performance.json"):
        try:
            fps = json.loads(f.read_text(encoding="utf-8")).get("fps")
            if fps:
                return float(fps)
        except (OSError, ValueError):
            pass
    return 30.0


def finalize(out: Path) -> int:
    """The final is made: delete the frames, the master and the scratch audio. Returns bytes freed."""
    out = Path(out)
    freed = 0
    for d in BUILD_DIRS:
        if (out / d).is_dir():
            freed += dir_bytes(out / d)
            shutil.rmtree(out / d)
    for name in (*BUILD_FILES, *SCRATCH):
        f = out / name
        if f.exists():
            freed += f.stat().st_size
            f.unlink()
    anim = out / "animatic" / "frames"
    if anim.is_dir():
        freed += dir_bytes(anim)
        shutil.rmtree(anim)
    return freed


def finished(out: Path) -> bool:
    """A final video exists and is newer than any frame on disk (so no render is running or resumable)."""
    out = Path(out)
    finals = list(out.glob("final_*.mp4"))
    if not finals:
        return False
    pngs = list((out / "frames").glob("*.png")) if (out / "frames").is_dir() else []
    return not pngs or max(f.stat().st_mtime for f in finals) >= max(f.stat().st_mtime for f in pngs)


def clean(project: Path, dry_run: bool = False) -> dict:
    """Free a finished project's disk: keep the final video, voices and small metadata; delete everything else.
    An unfinished render is left alone (it may be running or resumable)."""
    out = Path(project) / "out"
    report = {"project": Path(project).name, "before": dir_bytes(out), "actions": [], "dry_run": dry_run}
    if not finished(out):
        anim = out / "animatic" / "frames"
        report["actions"].append("kept: no final video yet (a render may be running or resumable)")
        freed = 0
        if anim.is_dir():  # animatic frames are never needed once its mp4 exists
            freed = dir_bytes(anim)
            report["actions"].append("delete out/animatic/frames")
            if not dry_run:
                shutil.rmtree(anim)
    else:
        freed = 0
        for d in (*BUILD_DIRS, "animatic/frames"):
            if (out / d).is_dir():
                report["actions"].append(f"delete out/{d}")
                freed += dir_bytes(out / d)
        for name in (*BUILD_FILES, *SCRATCH):
            if (out / name).exists():
                report["actions"].append(f"delete out/{name}")
                freed += (out / name).stat().st_size
        if not dry_run:
            freed = finalize(out)
    report["freed"] = freed
    report["after"] = report["before"] - freed if dry_run else dir_bytes(out)
    return report
