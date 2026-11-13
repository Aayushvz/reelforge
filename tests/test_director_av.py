"""Shots-AV director (plan_shots_av) and its five camera set-ups.

The fixture follows the reference reel's timing table (prompt 2.3) line for line: same speakers, same cut times, wides
in the same places. The words are our own placeholder lines (the real script is written with the owner at P7)."""
import importlib.util
import math
from pathlib import Path

import pytest

from reelforge.direct import AV_LENSES, Shot, is_turn, plan_shots_av, screen_time
from reelforge.schema import Line
from reelforge.timeline import Placed
from reelforge.voice import VoicedLine

FPS = 30
TOTAL = 48.85
SPEC = Path(__file__).parents[1] / "blender" / "camera_rig.py"
rig_spec = importlib.util.spec_from_file_location("camera_rig", SPEC)
rig = importlib.util.module_from_spec(rig_spec)
rig_spec.loader.exec_module(rig)

A, B, C, D, E = "av_hero_34", "av_buddy", "av_wide_34", "av_hero_front", "av_wide_front"
# (shot in, shot out, set-up, speaker, text, emotion, beat, punchline) from the reference's timing table
TABLE = [
    (0.00, 3.30, A, "me", "Claude, the client finally signed off.", "neutral", False, False),
    (3.30, 5.00, B, "bot", "That's great!", "happy", False, False),
    (5.00, 7.33, A, "me", "Took six rounds of feedback though.", "neutral", False, False),
    (7.33, 11.53, B, "bot", "Six rounds is normal. Two of them were yours.", "deadpan", False, False),
    (11.53, 12.87, A, "me", "I mean, that's mostly fair...", "neutral", False, False),
    (12.87, 15.07, C, "bot", "You also named the file final final.", "smug", True, False),
    (15.07, 16.97, A, "me", "It was a naming system.", "neutral", False, False),
    (16.97, 18.77, B, "bot", "It was a cry for help.", "deadpan", False, False),
    (18.77, 20.00, D, "me", "You counted my files?", "surprised", False, False),
    (20.00, 21.83, B, "bot", "I count everything.", "neutral", False, False),
    (21.83, 23.70, D, "me", "That is honestly unsettling to hear.", "surprised", False, False),
    (23.70, 27.63, B, "bot", "It is also why your deck shipped on time tonight.", "happy", False, False),
    (27.63, 28.90, E, "me", "...That's true.", "neutral", False, False),
    (28.90, 32.00, B, "bot", "So, who gets the credit this time?", "smug", False, False),
    (32.00, 33.90, A, "me", "Did you want credit?", "confused", False, False),
    (33.90, 38.47, B, "bot", "I want you asleep before two, for once in your life.", "neutral", False, False),
    (38.47, 40.33, D, "me", "Deal. Right after one tiny fix.", "happy", False, True),
    (40.33, 41.73, B, "bot", "There is no tiny fix!", "surprised", False, False),
    (41.73, 43.93, A, "me", "It is two pixels.", "deadpan", False, False),
    (43.93, 48.85, E, "me", "Two pixels, Claude.", "deadpan", False, False),
]


def fixture():
    placed = []
    for i, (t_in, t_out, _, who, text, emo, beat, punch) in enumerate(TABLE):
        start = t_in + AV_LEAD
        end = (TABLE[i + 1][0] if i + 1 < len(TABLE) else TOTAL - 0.9) - 0.15
        line = Line(f"l{i + 1:02d}", who, text, emo, 0.5, "calm", punchline=punch, beat=beat)
        placed.append(Placed(line, VoicedLine(line.id, Path("x.mp3"), []), start, end - start))
    return placed, int(round(TOTAL * FPS))


AV_LEAD = 3 / FPS  # each line starts 3 frames after its cut


@pytest.mark.parametrize("grammar", ["reference", "signature"])
def test_fixture_reproduces_the_reference_cut_list(grammar):
    placed, n = fixture()
    shots = plan_shots_av(placed, FPS, n, "me", "bot", seed=7, grammar=grammar, camera={"connect": False})
    assert len(shots) == 20
    assert [s.kind for s in shots] == [row[2] for row in TABLE]
    for s, row in zip(shots, TABLE):
        assert abs(s.start_frame - row[0] * FPS) <= 2, (row, s.start_frame)  # cut times within 2 frames
    assert shots[0].start_frame == 0 and shots[-1].end_frame == n
    assert all(a.end_frame == b.start_frame for a, b in zip(shots, shots[1:]))


def test_screen_time_split_matches_the_reference():
    placed, n = fixture()
    st = screen_time(plan_shots_av(placed, FPS, n, "me", "bot", grammar="reference"))
    for group, want in (("buddy", 0.46), ("hero", 0.37), ("wide", 0.17)):
        assert abs(st[group] - want) <= 0.03, (group, st)


def test_lengths_moves_and_the_closing_wide():
    placed, n = fixture()
    shots = plan_shots_av(placed, FPS, n, "me", "bot", grammar="reference")
    lengths = [(s.end_frame - s.start_frame) / FPS for s in shots]
    assert min(lengths) >= 1.2 - 1e-9 and max(lengths) <= 5.0 + 1e-9
    last = shots[-1]
    assert last.kind == "av_wide_front" and last.move == "pull_out" and last.move_params["amount"] == 0.25
    assert lengths[-1] >= 4.5
    assert all(s.handheld == 0.0 and s.ease == 0.0 for s in shots)  # reference: linear, no sway
    for s, L in zip(shots[:-1], lengths[:-1]):
        if L < 1.4:
            assert s.move == "drift"
        elif s.kind in ("av_hero_34", "av_hero_front"):
            assert s.move == "push_in" and s.move_params["amount"] == pytest.approx(min(0.06, 0.016 * L), abs=1e-3)
        elif s.kind == "av_buddy":
            assert s.move == "pull_truck" and s.move_params["amount"] == pytest.approx(min(0.12, 0.028 * L), abs=1e-3)
    assert all(s.lens == AV_LENSES[s.kind] for s in shots)
    assert [s.subject for s in shots].count("bot") == sum(1 for s in shots if s.kind == "av_buddy")


def test_signature_adds_one_rack_focus_and_a_little_life():
    placed, n = fixture()
    shots = plan_shots_av(placed, FPS, n, "me", "bot", grammar="signature")
    racks = [(i, s.rack) for i, s in enumerate(shots) if s.rack]
    assert len(racks) == 1
    i, rack = racks[0]
    assert shots[i].kind in ("av_wide_34", "av_wide_front") and rack["to"] == "bot" and rack["frames"] == 10
    assert all(s.handheld == 0.04 and s.ease == 0.15 for s in shots)
    assert plan_shots_av(placed, FPS, n, "me", "bot", seed=7) == plan_shots_av(placed, FPS, n, "me", "bot", seed=7)


def test_long_lines_split_by_a_listener_reaction():
    v = lambda i: VoicedLine(i, Path("x.mp3"), [])  # noqa: E731
    lines = [Line("l1", "me", "Hello there my friend.", "neutral", 0.5, "calm"),
             Line("l2", "bot", "A very long answer " * 8, "neutral", 0.5, "calm"),
             Line("l3", "me", "Okay then, thanks a lot.", "neutral", 0.5, "calm")]
    placed = [Placed(lines[0], v("l1"), 0.1, 2.0), Placed(lines[1], v("l2"), 2.3, 7.5),
              Placed(lines[2], v("l3"), 10.0, 5.5)]
    shots = plan_shots_av(placed, FPS, int(16 * FPS), "me", "bot", grammar="reference")
    kinds = [s.kind for s in shots]
    assert kinds[1:4] == ["av_buddy", "av_hero_34", "av_buddy"]  # the hero reacts in the middle of the long line
    assert 1.0 <= (shots[2].end_frame - shots[2].start_frame) / FPS <= 1.4
    assert shots[2].move == "static" and shots[2].subject == "me"


def test_is_turn():
    q = Line("a", "me", "You counted?", "neutral", 0.5, "calm")
    plain = Line("b", "me", "I see it now.", "neutral", 0.5, "calm")
    assert is_turn(q, None) and not is_turn(plain, plain)
    assert is_turn(Line("c", "me", "...That's true.", "neutral", 0.5, "calm"), plain)
    assert is_turn(Line("d", "me", "Fine, you win.", "neutral", 0.5, "calm"), plain)
    assert is_turn(Line("e", "me", "I see.", "happy", 0.5, "calm"), plain)  # an emotion change


@pytest.mark.parametrize("kind", ["av_hero_34", "av_hero_front", "av_buddy", "av_wide_34", "av_wide_front"])
def test_av_framing_lands_eyes_and_head_size_where_the_table_says(kind):
    """The rig's own projection: subject height and eye line on target, eyes inside 0.33-0.56 H (hero) and the top
    0.14 H clear for captions."""
    fr = rig.FRAMING[kind]
    w, h = 1080, 1920
    buddy = kind == "av_buddy"
    height = 0.144 if buddy else 0.44  # the buddy's body; the hero's head with hair
    eye = (-0.30, -0.40, 0.82) if buddy else (0.0, -0.16, 1.174)
    side = 1.0 if buddy else -1.0
    base = rig.base_pose(kind, eye, height, w, h, side)
    pose = rig.pose(base, "static", 0.5)
    _, ey = rig.screen_point(eye, pose["pos"], pose["aim"], pose["lens"], w, h)
    assert ey == pytest.approx(fr["eyes"], abs=0.02)
    assert 2 * base["dist"] * rig.half_fov_tan(pose["lens"], w, h)[1] * fr["head"] == pytest.approx(height, rel=0.01)
    if not buddy:
        assert 0.33 <= ey <= 0.56
    assert ey > rig.SAFE_TOP  # eyes stay below the caption band
    x, _ = rig.screen_point(eye, pose["pos"], pose["aim"], pose["lens"], w, h)
    az_deg = math.degrees(math.atan2(pose["pos"][0] - eye[0], -(pose["pos"][1] - eye[1])))
    lo, hi = fr["az"]
    want = sorted((lo * side, hi * side))
    assert want[0] - 0.5 <= az_deg <= want[1] + 0.5  # the sign conversion of 5.1
    if kind in ("av_hero_34", "av_wide_34"):
        assert az_deg > 0  # hero set-ups stand on the monitor side (+X)


def test_shot_rack_field_defaults_empty():
    assert Shot(0, 10, "wide", 40, "a", 0.0).rack == {}


def test_editor_camera_options_rack_off_and_drift_scale():
    placed, n = fixture()
    base = plan_shots_av(placed, FPS, n, "me", "bot", grammar="signature")
    off = plan_shots_av(placed, FPS, n, "me", "bot", grammar="signature", camera={"rack": False})
    assert any(s.rack for s in base) and not any(s.rack for s in off)
    half = plan_shots_av(placed, FPS, n, "me", "bot", grammar="reference", camera={"drift": 0.5})
    full = plan_shots_av(placed, FPS, n, "me", "bot", grammar="reference")
    for a, b in zip(half, full):
        for k in ("amount", "metres", "degrees"):
            if k in b.move_params:
                assert a.move_params[k] == pytest.approx(b.move_params[k] * 0.5, abs=1e-4)


def test_overrides_from_the_shot_strip():
    placed, n = fixture()
    shots = plan_shots_av(placed, FPS, n, "me", "bot", grammar="reference",
                          camera={"overrides": {"1": {"kind": "av_wide_front", "move": "drift"}, "5": {"rack": True},
                                                "12": {"rack": False}}})
    assert shots[1].kind == "av_wide_front" and shots[1].lens == 50 and shots[1].move == "drift"
    assert shots[5].rack["to"] == "bot" and shots[12].rack == {}


def test_signature_folds_one_hero_to_buddy_cut_into_a_connected_move():
    placed, n = fixture()
    plain = plan_shots_av(placed, FPS, n, "me", "bot", seed=7, camera={"connect": False})
    shots = plan_shots_av(placed, FPS, n, "me", "bot", seed=7)
    joined = [s for s in shots if s.connect]
    assert len(joined) == 1 and len(shots) == len(plain) - 1
    j = joined[0]
    assert j.kind in ("av_hero_34", "av_hero_front") and j.subject == "me" and j.connect["to"] == "bot"
    assert j.start_frame >= n / 3 and j.connect["frames"] == 18 and j.connect["framing"]["lens"] > 0
    buddy_cut = next(s.start_frame for s in plain if s.start_frame > j.start_frame)
    assert j.start_frame + j.connect["at"] == buddy_cut - 6  # the arc starts 0.2 s before the reply
    assert all(a.end_frame == b.start_frame for a, b in zip(shots, shots[1:])) and shots[-1].end_frame == n
    assert not any(s.connect for s in plan_shots_av(placed, FPS, n, "me", "bot", seed=7, grammar="reference"))
