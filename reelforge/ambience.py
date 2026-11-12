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
# Shots-AV rooms: room_night (a quiet room with the city far below), room_day (a brighter, airier room tone)
ROOM_NIGHT = "anoisesrc=color=brown:amplitude=0.32,lowpass=f=320,equalizer=f=90:t=q:w=1.5:g=4"
ROOM_DAY = "anoisesrc=color=pink:amplitude=0.14,highpass=f=120,lowpass=f=2400"
BEDS.update({
    "av_studio_night": ROOM_NIGHT,
    "av_neon_den": ROOM_NIGHT + ",equalizer=f=120:t=q:w=2:g=8",  # a mains hum from the LED drivers
    "av_late_office": "anoisesrc=color=brown:amplitude=0.36,lowpass=f=260",  # HVAC in an empty floor
    "av_studio_morning": ROOM_DAY,
    "av_cafe_day": "anoisesrc=color=pink:amplitude=0.3,bandpass=f=900:width_type=h:w=1200,tremolo=f=3:d=0.3",
    "av_cyc_lilac": "anoisesrc=color=pink:amplitude=0.07,highpass=f=150,lowpass=f=1800",
})
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


# --- Shots-AV foley: a soft blip at each buddy line, sparse keyboard taps, the owner's music ---------------------
FOLEY_RATE = 48000
BLIP_S = 0.06
BLIP_GAIN = 0.10  # about -20 dBFS peak: heard, never in the way
KEY_GAIN = 0.07


def foley_samples(seconds: float, blips: list[float], keys: list[tuple[float, float]], seed: int = 7) -> list[float]:
    """Mono samples (-1..1): a 60 ms rising blip at each time in `blips`, and sparse key taps (one every 0.12-0.4 s,
    in little runs) inside each (start, end) of `keys`. Deterministic for a seed."""
    import math
    import random
    n = int(seconds * FOLEY_RATE)
    out = [0.0] * n
    for t0 in blips:
        a = int(t0 * FOLEY_RATE)
        m = int(BLIP_S * FOLEY_RATE)
        for k in range(m):
            if 0 <= a + k < n:
                u = k / m
                f = 880 + 660 * u  # a quick upward glide
                env = math.sin(math.pi * u) ** 2
                out[a + k] += BLIP_GAIN * env * math.sin(2 * math.pi * f * k / FOLEY_RATE)
    rng = random.Random(seed)
    for s0, s1 in keys:
        t = s0 + rng.uniform(0.05, 0.3)
        while t < s1:
            a = int(t * FOLEY_RATE)
            m = int(0.018 * FOLEY_RATE)  # an 18 ms click: noise through a fast decay
            g = KEY_GAIN * rng.uniform(0.6, 1.0)
            prev = 0.0
            for k in range(m):
                if 0 <= a + k < n:
                    x = rng.uniform(-1, 1)
                    prev = 0.55 * prev + 0.45 * x  # a little low-pass: plastic, not hiss
                    out[a + k] += g * prev * math.exp(-k / (0.004 * FOLEY_RATE))
            t += rng.uniform(0.12, 0.4) if rng.random() > 0.2 else rng.uniform(0.6, 1.2)  # runs and pauses
    return out


def write_wav(path: Path, samples: list[float], rate: int = FOLEY_RATE) -> Path:
    import array
    import wave
    data = array.array("h", (int(max(-1.0, min(1.0, v)) * 32767) for v in samples))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())
    return Path(path)


def find_music(project: Path) -> Path | None:
    """The owner's own music file in the project folder (never downloaded)."""
    for name in ("music.wav", "music.mp3", "music.m4a", "music.flac"):
        if (Path(project) / name).exists():
            return Path(project) / name
    return None


MUSIC_LUFS = -24  # under speech, over the room


def add_av_sound(dialogue: Path, environment: str, seconds: float, blips: list[float],
                 keys: list[tuple[float, float]], music: Path | None = None, seed: int = 7) -> bool:
    """Mix the room bed, the foley and (if given) the owner's music under dialogue.wav, in place; the dry copy is
    kept as dialogue_dry.wav."""
    out = Path(dialogue)
    layers = []
    bed = out.with_name("ambience.wav")
    cmd = ambience_cmd(environment, "", seconds, bed)
    if cmd is not None:
        subprocess.run(cmd, check=True)
        layers.append(bed)
    foley = write_wav(out.with_name("foley.wav"), foley_samples(seconds, blips, keys, seed))
    layers.append(foley)
    if music is not None:
        mus = out.with_name("music_bed.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(music), "-t",
                        f"{seconds:.3f}", "-af", f"loudnorm=I={MUSIC_LUFS}:TP=-6,aresample=48000,afade=t=in:d=0.8,"
                        f"afade=t=out:st={max(0.0, seconds - 1.2):.3f}:d=1.2", "-ac", "1", str(mus)], check=True)
        layers.append(mus)
    dry = out.with_name("dialogue_dry.wav")
    shutil.copyfile(out, dry)
    ins = ["-i", str(dry)] + [a for p in layers for a in ("-i", str(p))]
    mix = "".join(f"[{i}:a]" for i in range(len(layers) + 1))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex",
                    f"{mix}amix=inputs={len(layers) + 1}:duration=first:normalize=0[a]", "-map", "[a]", str(out)],
                   check=True)
    return True
