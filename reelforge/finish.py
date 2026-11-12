from __future__ import annotations

import subprocess
from pathlib import Path

# Per-set grade (the set's "LUT"): a colour-balance push applied after the base look.
GRADES = {
    "night_city": "colorbalance=bs=0.05:bm=0.02:rh=0.03",
    "bedroom": "colorbalance=rm=0.02:bs=0.03",
    "rooftop": "colorbalance=rh=0.04:bs=0.04",
    "cafe": "colorbalance=rh=0.03:gm=0.01:bs=0.01",
    "lantern_street": "colorbalance=rh=0.06:gh=0.02:bs=-0.03",
    "subway": "colorbalance=gm=0.03:bs=0.02",
    "classroom": "colorbalance=rh=0.02:bh=-0.01",
    "office": "colorbalance=bs=0.03:bh=0.02",
    "night_mart": "colorbalance=gm=0.02:bh=0.03",
    "pier": "colorbalance=rh=0.05:bs=0.03",
}

# Halation/bloom: isolate highlights, blur, tint warm, screen back over the image.
FILTER = (
    "[0:v]format=gbrp,split=2[base][hi];"
    "[hi]curves=all='0/0 0.72/0 1/1',gblur=sigma=30,"
    "colorchannelmixer=rr=1:gg=0.45:bb=0.25[halo];"
    "[base][halo]blend=all_mode=screen:all_opacity=0.45,"
    "eq=contrast=1.04:saturation=1.06,GRADE"
    "vignette=angle=PI/5,"
    "noise=alls=5:allf=t,"
    "ass=captions.ass,"
    "format=yuv420p[v];"
    "[1:a]acompressor=threshold=0.1:ratio=4:attack=5:release=80:makeup=2,"  # tame speech peaks first
    "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
)


# Cinema look: the render already carries the light. Only a faint highlight halo (bright practicals, not skin
# tones), a soft vignette and fine grain; work in 16 bits and dither down so dark gradients don't band.
FILTER_CINEMA = (
    "[0:v]format=gbrp16le,split=2[base][hi];"
    "[hi]curves=all='0/0 0.86/0 1/1',gblur=sigma=22,"
    "colorchannelmixer=rr=1:gg=0.6:bb=0.4[halo];"
    "[base][halo]blend=all_mode=screen:all_opacity=0.16,"
    "GRADE"
    "vignette=angle=PI/7,"
    "noise=alls=2:allf=t,"
    "ass=captions.ass,"
    "scale=out_color_matrix=bt709:out_range=tv:sws_dither=ed,"
    "format=yuv420p[v];"
    "[1:a]acompressor=threshold=0.1:ratio=4:attack=5:release=80:makeup=2,"
    "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
)
BT709 = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]

# Shots-AV (prompt section 7): contrast back on top of PBR Neutral through a master curve (the same on every
# channel, so hues do not move), and no saturation push, so #7C3AED never clips; a mild warm halo on highlights
# only; a vignette that darkens the corners by at most 12%; fine grain; ~11 Mbps at 1080x1920.
AV_GRADES = {
    "shotsav_dark": "curves=master='0/0 0.06/0.042 0.5/0.5 0.86/0.9 1/0.985',",
    "shotsav_light": "curves=master='0/0.012 0.5/0.5 0.9/0.925 1/0.99',",
}
AV_ROOM_GRADE = {"av_studio_night": "shotsav_dark", "av_neon_den": "shotsav_dark", "av_late_office": "shotsav_dark",
                 "av_studio_morning": "shotsav_light", "av_cafe_day": "shotsav_light", "av_cyc_lilac": "shotsav_light"}
AV_VIGNETTE = 0.22  # radians: measured, the corners land at 0.89 of the centre (11% darker; the cap is 12%)
# The halo mask comes from brightness (one grey channel), not from each colour channel, and is added, not
# screened: ffmpeg's 16-bit `screen` blend shifts one channel even over a black layer (measured: a skin tone's blue
# 122 -> 153), which blotched faces pink and olive. `addition` is exact where the halo is black.
AV_HALO = ("[hi]format=gray16le,curves=all='0/0 0.86/0 1/1',gblur=sigma=18,format=gbrp16le,"
           "colorchannelmixer=rr=1:gg=0.72:bb=0.55[halo];"
           "[base][halo]blend=all_mode=addition:all_opacity=0.10,")
FILTER_SHOTSAV = (
    "[0:v]format=gbrp16le,split=2[base][hi];"
    + AV_HALO +
    "GRADE"
    f"vignette=angle={AV_VIGNETTE},"
    "noise=alls=3:allf=t,"
    "ass=captions.ass:fontsdir=fonts,"
    "scale=out_color_matrix=bt709:out_range=tv:sws_dither=ed,"
    "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv,"  # the scale leaves them unset
    "format=yuv420p[v];"
    "[1:a]acompressor=threshold=0.1:ratio=4:attack=5:release=80:makeup=2,"
    "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
)
AV_VIDEO = ["-b:v", "11M", "-maxrate", "12M", "-bufsize", "24M", "-profile:v", "high", "-level", "4.2"]


def build_ffmpeg_cmd(fps: int, out_name: str, environment: str = "", look: str = "classic") -> list[str]:
    if look == "shotsav":
        grade = AV_GRADES[AV_ROOM_GRADE.get(environment, "shotsav_dark")]
        return ["ffmpeg", "-y", "-loglevel", "error",
                "-framerate", str(fps), "-start_number", "1", "-i", "frames/%04d.png",
                "-i", "dialogue.wav",
                "-filter_complex", FILTER_SHOTSAV.replace("GRADE", grade), "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "slow", *AV_VIDEO, *BT709,
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out_name]
    grade = GRADES.get(environment)
    cinema = look == "cinema"
    graph = (FILTER_CINEMA if cinema else FILTER).replace("GRADE", f"{grade}," if grade else "")
    return ["ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(fps), "-start_number", "1", "-i", "frames/%04d.png",
            "-i", "dialogue.wav",
            "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "14" if cinema else "16",
            *(["-profile:v", "high", "-level", "4.2", *BT709] if cinema else []),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest",
            out_name]


TARGET_LUFS = -14.0


def measure_lufs(path: Path) -> float:
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    lines = [ln for ln in r.stderr.splitlines() if ln.strip().startswith("I:")]
    return float(lines[-1].split()[1])


def finish(workdir: Path, fps: int, out_name: str, environment: str = "", look: str = "classic") -> Path:
    # Relative paths + cwd avoid Windows drive-letter escaping inside the ass= filter.
    if look == "shotsav":  # the caption font travels with the job (fontsdir=fonts)
        font = Path(__file__).resolve().parents[1] / "tools" / "fonts" / "Geist-Bold.ttf"
        (Path(workdir) / "fonts").mkdir(exist_ok=True)
        if font.exists():
            import shutil
            shutil.copyfile(font, Path(workdir) / "fonts" / font.name)
    subprocess.run(build_ffmpeg_cmd(fps, out_name, environment, look), cwd=workdir, check=True)
    out = Path(workdir) / out_name
    # One-pass loudnorm undershoots on short clips: correct the residual gain. The peak limiter eats part
    # of each boost, so repeat a few times.
    for _ in range(4):
        gain = TARGET_LUFS - measure_lufs(out)
        if abs(gain) <= 0.5:
            break
        tmp = out.with_name("loud_" + out.name)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-c:v", "copy",
                        "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false", "-c:a", "aac",
                        "-b:a", "192k", "-movflags", "+faststart", str(tmp)], check=True)
        tmp.replace(out)
    return out
