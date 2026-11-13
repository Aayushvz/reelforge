import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "blender"))
import camera_rig as rig  # noqa: E402

W, H = 1080, 1920
EYE, HEAD = (0.0, 0.0, 1.65), 0.25


def _poses(move, kind="closeup", n=90, **params):
    base = rig.base_pose(kind, EYE, HEAD, W, H, side=1.0)
    return base, [rig.pose(base, move, f / (n - 1), params) for f in range(n)]


@pytest.mark.parametrize("strength", [0.0, 0.35, 1.0])
def test_ease_is_exact_at_the_ends_and_monotonic(strength):
    vals = [rig.ease(i / 100, strength) for i in range(101)]
    assert vals[0] == 0.0 and vals[-1] == 1.0
    assert all(b >= a for a, b in zip(vals, vals[1:]))


@pytest.mark.parametrize("kind", list(rig.FRAMING))
def test_framing_puts_the_eyes_on_the_eye_line_with_the_right_head_size(kind):
    base = rig.base_pose(kind, EYE, HEAD, W, H, side=1.0)
    p = rig.pose(base, "static", 0.5)
    x, y = rig.screen_point(EYE, p["pos"], p["aim"], p["lens"], W, H)
    assert abs(y - rig.FRAMING[kind]["eyes"]) < 0.02 and abs(x - 0.5) < 0.02
    top = rig.screen_point((EYE[0], EYE[1], EYE[2] + HEAD / 2), p["pos"], p["aim"], p["lens"], W, H)[1]
    chin = rig.screen_point((EYE[0], EYE[1], EYE[2] - HEAD / 2), p["pos"], p["aim"], p["lens"], W, H)[1]
    assert abs((chin - top) - rig.FRAMING[kind]["head"]) < 0.03


def test_closeup_and_medium_eyes_stay_out_of_the_caption_bands():
    for kind in ("closeup", "medium", "wide"):
        base = rig.base_pose(kind, EYE, HEAD, W, H)
        p = rig.pose(base, "static", 0.5)
        y = rig.screen_point(EYE, p["pos"], p["aim"], p["lens"], W, H)[1]
        assert rig.SAFE_TOP < y < 1.0 - rig.SAFE_BOTTOM


def test_landscape_frames_use_the_same_head_fraction():
    base = rig.base_pose("closeup", EYE, HEAD, 1920, 1080)
    p = rig.pose(base, "static", 0.5)
    top = rig.screen_point((0, 0, EYE[2] + HEAD / 2), p["pos"], p["aim"], p["lens"], 1920, 1080)[1]
    chin = rig.screen_point((0, 0, EYE[2] - HEAD / 2), p["pos"], p["aim"], p["lens"], 1920, 1080)[1]
    assert abs((chin - top) - rig.FRAMING["closeup"]["head"]) < 0.03


def test_nothing_is_wider_than_waist_up():
    """Full-body shots expose stiff poses and bare floor: the hips must fall at or below the bottom edge."""
    for kind in rig.FRAMING:
        base = rig.base_pose(kind, EYE, HEAD, W, H)
        p = rig.pose(base, "static", 0.5)
        knees = rig.screen_point((EYE[0], EYE[1], 0.5), p["pos"], p["aim"], p["lens"], W, H)[1]
        assert knees > 1.0, kind


def test_min_head_keeps_a_character_from_being_framed_wide():
    for kind in ("wide", "medium"):
        base = rig.base_pose(kind, EYE, HEAD, W, H, min_head=0.45)
        p = rig.pose(base, "static", 0.5)
        top = rig.screen_point((0, 0, EYE[2] + HEAD / 2), p["pos"], p["aim"], p["lens"], W, H)[1]
        chin = rig.screen_point((0, 0, EYE[2] - HEAD / 2), p["pos"], p["aim"], p["lens"], W, H)[1]
        assert abs((chin - top) - 0.45) < 0.03 and top > 0.10
    close = rig.base_pose("closeup", EYE, HEAD, W, H, min_head=0.45)
    assert close["dist"] == rig.base_pose("closeup", EYE, HEAD, W, H)["dist"]  # already tighter: untouched


def test_raking_two_shot_holds_both_faces_with_the_listener_nearer():
    spk, lis = (0.0, 0.0, 1.65), (1.05, 0.0, 1.62)
    base = rig.base_pose("two", rig.two_shot_aim(spk, lis), HEAD, W, H, side=1.0)
    p = rig.pose(base, "static", 0.5)
    xs = [rig.screen_point(e, p["pos"], p["aim"], p["lens"], W, H)[0] for e in (spk, lis)]
    assert all(0.08 < x < 0.92 for x in xs) and abs(xs[0] - xs[1]) > 0.25
    assert math.dist(p["pos"], lis) < math.dist(p["pos"], spk)


@pytest.mark.parametrize("move", [m for m in rig.MOVES if m != "whip_pan"])
def test_moves_are_smooth_and_never_shake(move):
    _, poses = _poses(move)
    assert all(math.isfinite(v) for p in poses for v in (*p["pos"], *p["aim"], p["lens"]))
    assert rig.max_angular_accel(poses, 30) < 25.0  # deg/s^2; the old jitter measured in the hundreds


def test_push_in_closes_distance_by_its_amount_and_pull_out_opens_it():
    base, poses = _poses("push_in", amount=0.10)
    d = [math.dist(p["pos"], p["aim"]) for p in poses]
    assert all(b <= a + 1e-9 for a, b in zip(d, d[1:]))
    assert d[0] / d[-1] == pytest.approx(1.05 / 0.95, rel=1e-6)
    _, out = _poses("pull_out", amount=0.10)
    assert math.dist(out[-1]["pos"], out[-1]["aim"]) > math.dist(out[0]["pos"], out[0]["aim"])


def test_orbit_keeps_its_radius_and_sweeps_the_asked_angle():
    base, poses = _poses("orbit", degrees=12.0)
    d = [math.dist(p["pos"], p["aim"]) for p in poses]
    assert max(d) - min(d) < 1e-9
    yaw = [rig.aim_angles(p["pos"], p["aim"])[0] for p in poses]
    assert abs(math.degrees(abs(yaw[-1] - yaw[0])) - 12.0) < 0.5


def test_crane_lands_on_the_base_framing():
    base, poses = _poses("crane_down", kind="wide")
    assert poses[0]["pos"][2] > poses[-1]["pos"][2]
    assert poses[-1]["pos"] == pytest.approx(rig.pose(base, "static", 1.0)["pos"])


def test_intensity_scales_a_move():
    base = rig.base_pose("closeup", EYE, HEAD, W, H)
    a = rig.pose(base, "push_in", 0.0, {"amount": 0.1})
    b = rig.pose(base, "push_in", 0.0, {"amount": 0.1, "intensity": 2.0})
    assert math.dist(b["pos"], b["aim"]) > math.dist(a["pos"], a["aim"])


def test_handheld_is_deterministic_small_and_fades_at_the_cuts():
    a = [rig.handheld(f, 30, 7, 0.5, 90, 0) for f in range(90)]
    assert a == [rig.handheld(f, 30, 7, 0.5, 90, 0) for f in range(90)]
    assert a != [rig.handheld(f, 30, 8, 0.5, 90, 0) for f in range(90)]
    assert a[0] == ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)) and a[-1] == ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    assert max(abs(v) for _, rot in a for v in rot) <= math.radians(0.4) * 0.5 + 1e-9
    assert max(abs(v) for pos, _ in a for v in pos) <= 0.003 * 0.5 + 1e-9
    assert rig.handheld(10, 30, 7, 0.0) == ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def test_handheld_has_no_fast_component():
    yaw = [rig.handheld(f, 30, 3, 1.0)[1][1] for f in range(300)]
    steps = [abs(b - a) for a, b in zip(yaw, yaw[1:])]
    assert max(steps) < math.radians(0.4) * 2 * math.pi * 0.8 / 30 * 1.2  # bounded by the 0.8 Hz top band
