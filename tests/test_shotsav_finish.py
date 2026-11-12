"""Shots-AV captions (shotsav_top), sound (beds, blip, keys, music) and the purple-safe finish."""
import colorsys
import re
import subprocess
from pathlib import Path

import pytest

from reelforge import ambience, captions, finish
from reelforge.engines import shots_av
from reelforge.schema import AV_ROOMS, Line, parse_performance
from reelforge.timeline import Placed
from reelforge.voice import VoicedLine

FPS = 30


def _perf():
    return parse_performance({"style": "shots-av", "characters": {"me": {"model": "av_hero"},
                                                                    "claude": {"model": "buddy_claude"}},
                              "lines": [{"speaker": "me", "text": "hi"}]})


def _placed(rows):
    v = lambda i: VoicedLine(i, Path("x.mp3"), [])  # noqa: E731
    return [Placed(Line(f"l{i}", who, text, "neutral", 0.5, "calm"), v(f"l{i}"), start, dur)
            for i, (who, text, start, dur) in enumerate(rows)]


def test_wrap_two_lines_of_22_and_split_longer():
    assert captions.wrap_av("That's great!") == [["That's great!"]]
    parts = captions.wrap_av("It is also why your deck shipped on time tonight and nobody noticed at all.")
    assert all(len(p) <= 2 for p in parts) and len(parts) == 2
    assert all(len(line) <= 22 for p in parts for line in p)


def test_caption_timing_follows_the_cuts():
    placed = _placed([("me", "Claude, the client signed off.", 0.1, 2.0), ("claude", "That's great!", 2.5, 1.2)])
    ev = captions.av_events(placed, FPS, 4.5)
    first, second = ev[0], ev[1]
    assert first[0] == pytest.approx(0.1 - 3 / FPS + 4 / FPS)  # 4 frames after the cut
    assert first[1] == pytest.approx(2.5 - 6 / FPS)  # 3 frames before the next cut
    assert second[0] == pytest.approx(2.5 + 1 / FPS) and second[1] <= 4.5


def test_ass_has_the_plate_the_dot_and_whole_lines():
    placed = _placed([("me", "Claude, the client signed off.", 0.1, 2.0), ("claude", "That's great!", 2.5, 1.2)])
    perf = _perf()
    ass = captions.build_ass_shotsav(placed, perf, 1080, 1920, FPS, 4.5, {"me": "#7C3AED", "claude": "#D97757"})
    assert "Style: AV,Geist,46," in ass
    dialogue = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    assert len(dialogue) == 6  # plate, dot and text per caption
    bs = chr(92)  # a backslash: ASS override tags start with one
    assert sum(bs + "p1" in l for l in dialogue) == 4
    assert bs + "alpha&H8C&" in ass  # the ink plate at 45%
    assert bs + "c&HED3A7C&" in ass and bs + "c&H5777D9&" in ass  # the hero's purple dot, the buddy's terracotta dot
    texts = [l.split("}", 1)[-1] for l in dialogue if ",AV," in l]
    assert texts == ["Claude, the client" + bs + "Nsigned off.", "That's great!"]  # whole lines, no highlight
    y = int(re.search(r"pos\((\d+),(\d+)\)", [l for l in dialogue if ",AV," in l][0]).group(2))
    assert 0.07 <= y / 1920 <= 0.09


def test_every_room_has_a_bed():
    assert all(r in ambience.BEDS for r in AV_ROOMS)


def test_foley_places_blips_and_keys_and_is_deterministic():
    s = ambience.foley_samples(3.0, [1.0], [(2.0, 2.9)], seed=3)
    assert s == ambience.foley_samples(3.0, [1.0], [(2.0, 2.9)], seed=3)
    rate = ambience.FOLEY_RATE
    peak = lambda a, b: max(abs(v) for v in s[int(a * rate):int(b * rate)])  # noqa: E731
    assert peak(0.0, 0.95) == 0.0 and 0.05 < peak(1.0, 1.06) <= ambience.BLIP_GAIN + 1e-9
    assert peak(1.07, 2.0) == 0.0 and peak(2.0, 2.95) > 0.02


def test_sound_plan_keys_only_while_the_hero_types_and_listens():
    from reelforge.direct import Shot
    placed = _placed([("me", "a", 0.1, 2.0), ("claude", "b", 2.5, 2.0), ("me", "c", 5.0, 2.0),
                      ("claude", "d", 7.5, 2.0)])
    shots = [Shot(0, 70, "av_hero_34", 85, "me", 0.0), Shot(70, 147, "av_buddy", 100, "claude", 0.0),
             Shot(147, 222, "av_hero_front", 85, "me", 0.0), Shot(222, 300, "av_buddy", 100, "claude", 0.0)]
    blips, keys = shots_av.sound_plan(placed, shots, "me", "claude", 300, FPS)
    assert blips == [2.5, 7.5]
    assert keys and all(a >= 147 / FPS - 1e-9 for a, _ in keys)
    assert not any(a < 7.0 and b > 5.0 for a, b in keys)  # never over his own line


def _solid(color, w=64, h=64):
    return ["-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d=0.04"]


def _px(cmd_args, vf):
    raw = subprocess.run(["ffmpeg", "-v", "error", *cmd_args, "-vf", vf + ",format=rgb24", "-frames:v", "1",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return raw


@pytest.mark.parametrize("grade", ["shotsav_dark", "shotsav_light"])
def test_the_grade_keeps_brand_purple(grade):
    raw = _px(_solid("0x7C3AED"), finish.AV_GRADES[grade].rstrip(","))
    r, g, b = raw[3 * (32 * 64 + 32):3 * (32 * 64 + 32) + 3]
    h0 = colorsys.rgb_to_hsv(0x7C / 255, 0x3A / 255, 0xED / 255)[0] * 360
    h1 = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[0] * 360
    assert abs(h1 - h0) <= 3.0 and max(r, g, b) < 255  # hue untouched, nothing clips


def test_vignette_darkens_corners_by_at_most_12_percent():
    raw = _px(_solid("0x808080", 108, 192), f"vignette=angle={finish.AV_VIGNETTE}")
    centre, corner = raw[3 * (96 * 108 + 54)], raw[0]
    assert 0.86 <= corner / centre <= 1.0


def test_shotsav_finish_command():
    cmd = finish.build_ffmpeg_cmd(30, "final_9x16.mp4", "av_studio_morning", "shotsav")
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "curves=master='0/0.012" in graph and "fontsdir=fonts" in graph and "loudnorm=I=-14" in graph
    assert "saturation" not in graph  # never push purple's saturation
    assert cmd[cmd.index("-b:v") + 1] == "11M" and cmd[cmd.index("-maxrate") + 1] == "12M"
    assert "bt709" in cmd and "setparams=color_primaries=bt709:color_trc=bt709" in graph
    night = finish.build_ffmpeg_cmd(30, "x.mp4", "av_studio_night", "shotsav")
    assert "0.06/0.042" in night[night.index("-filter_complex") + 1]


def test_caption_tints_use_the_jacket_and_the_shell():
    assert shots_av.caption_tints(_perf()) == {"me": "#7C3AED", "claude": "#D97757"}


@pytest.mark.parametrize("skin", ["0xF2B48C", "0xE8A07A", "0xD6A688"])
def test_halation_never_tints_skin(skin):
    """Bright skin (red over the halo threshold, green under it) must keep its hue through the halo."""
    graph = "format=gbrp16le,split=2[base][hi];" + finish.AV_HALO.rstrip(",")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=c={skin}:s=64x64:d=0.04",
                          "-filter_complex", graph + ",format=rgb24", "-frames:v", "1", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    r, g, b = raw[3 * (32 * 64 + 32):3 * (32 * 64 + 32) + 3]
    want = [int(skin[i:i + 2], 16) for i in (2, 4, 6)]
    h0 = colorsys.rgb_to_hsv(*(v / 255 for v in want))[0] * 360
    h1 = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[0] * 360
    assert abs(h1 - h0) <= 2.0 and max(abs(x - y) for x, y in zip((r, g, b), want)) <= 4
