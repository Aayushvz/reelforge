"""Procedural ambience beds per set (ffmpeg lavfi), mixed quietly under the dialogue."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

BEDS = {
    "night_city": "anoisesrc=color=brown:amplitude=0.5,lowpass=f=400",  # distant traffic
    "bedroom": "anoisesrc=color=pink:amplitude=0.12,lowpass=f=1200",  # room tone + PC fan
    "rooftop": "anoisesrc=color=pink:amplitude=0.5,bandpass=f=500:width_type=h:w=600,tremolo=f=0.15:d=0.6",  # wind
    "cafe": "anoisesrc=color=pink:amplitude=0.35,bandpass=f=900:width_type=h:w=1200,tremolo=f=3:d=0.3",  # murmur
    "lantern_street": "anoisesrc=color=pink:amplitude=0.25,lowpass=f=900,tremolo=f=0.2:d=0.4",
    "subway": "anoisesrc=color=brown:amplitude=0.7,lowpass=f=250",  # platform rumble
    "classroom": "anoisesrc=color=pink:amplitude=0.08,lowpass=f=800",
    "office": "anoisesrc=color=brown:amplitude=0.3,lowpass=f=300",  # HVAC
    "night_mart": "anoisesrc=color=brown:amplitude=0.25,lowpass=f=200,equalizer=f=120:t=q:w=2:g=12",  # fridge hum
    "pier": "anoisesrc=color=pink:amplitude=0.6,lowpass=f=700,tremolo=f=0.12:d=0.8",  # waves
}
RAIN = "anoisesrc=color=white:amplitude=0.2,highpass=f=1500,lowpass=f=7000"
BED_LUFS = -38  # bed sits well under speech (-14 LUFS) after the mix


def ambience_cmd(environment: str, lighting: str, seconds: float, out: Path) -> list[str] | None:
    bed = BEDS.get(environment)
    if bed is None:
        return None
    layers = [bed] + ([RAIN] if "rain" in lighting else [])
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for layer in layers:
        cmd += ["-f", "lavfi", "-t", f"{seconds:.3f}", "-i", f"{layer},aresample=48000"]
    mix = "".join(f"[{i}:a]" for i in range(len(layers)))
    graph = f"{mix}amix=inputs={len(layers)}:normalize=0,loudnorm=I={BED_LUFS}:TP=-9,aresample=48000,afade=t=in:d=0.5[a]"
    return cmd + ["-filter_complex", graph, "-map", "[a]", "-ac", "1", str(out)]


def add_ambience(dialogue: Path, environment: str, lighting: str, seconds: float) -> bool:
    """Mix the set's bed under dialogue.wav in place (dry copy kept as dialogue_dry.wav)."""
    out = Path(dialogue)
    bed = out.with_name("ambience.wav")
    cmd = ambience_cmd(environment, lighting, seconds, bed)
    if cmd is None:
        return False
    subprocess.run(cmd, check=True)
    dry = out.with_name("dialogue_dry.wav")
    shutil.copyfile(out, dry)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(dry), "-i", str(bed), "-filter_complex",
                    "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[a]", str(out)], check=True)
    return True
