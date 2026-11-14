import json

import pytest

from reelforge.cli import main
from reelforge.cover import candidates, draft, headline, pick_frames

NAMES = {"claude"}


def test_reference_lines():
    assert headline("Claude, I asked you to fix the navbar. Why is the entire homepage broken?", NAMES) == ["FIX THE", "NAVBAR."]
    assert headline("Claude, the client wants the logo bigger.", NAMES) == ["LOGO", "BIGGER."]


def test_state_rule_with_link_verb_and_adjective():
    assert headline("The animations are gone. The spacing is messed up.") == ["ANIMATIONS", "GONE."]
    hs = [h for h, _ in candidates("Claude, I asked you to fix the navbar. Why is the entire homepage broken?", NAMES)]
    assert ["HOMEPAGE", "BROKEN."] in hs


def test_vocative_never_becomes_headline():
    for h, _ in candidates("Claude... make Claude happy", NAMES):
        assert "CLAUDE" not in " ".join(h)


def test_fallback_two_content_words_in_order():
    h = headline("Seriously, deployment happened overnight")
    assert h is not None and h[1].endswith(".") and len(h) == 2
    assert h == ["DEPLOYMENT", "OVERNIGHT."]


def test_source_sentence_is_kept_for_caption():
    (h, src), *_ = candidates("Claude, I asked you to fix the navbar. Why is it broken?", NAMES)
    assert src == "I asked you to fix the navbar."


PLAN = {"fps": 30, "resolution": [1080, 1920], "shots": [
    {"start_frame": 0, "end_frame": 60, "subject": "me", "speaker": "me", "framing": {"head": 0.42}, "move": "push_in", "move_params": {"amount": 0.04}},
    {"start_frame": 60, "end_frame": 100, "subject": "buddy", "speaker": "buddy", "framing": {"head": 0.9}},
    {"start_frame": 100, "end_frame": 150, "subject": "me", "speaker": "buddy", "framing": {"head": 0.9}},
    {"start_frame": 150, "end_frame": 200, "subject": "me", "speaker": "me", "framing": {"head": 0.25}},
    {"start_frame": 210, "end_frame": 260, "subject": "me", "speaker": "me", "angle": "hero_hands", "framing": {"head": 0.9, "eyes": -0.6}},
    {"start_frame": 200, "end_frame": 203, "subject": "me", "speaker": "me", "framing": {"head": 2.0}},
]}


def test_pick_frames_prefers_big_speaking_hero_face():
    picks = pick_frames(PLAN, 3)
    assert [p["shot"] for p in picks] == [2, 0, 3]  # 0.9 > 0.42+0.3+0.04; the buddy, the hands insert and the 3-frame shot never win
    assert picks[0]["frame"] == 100 + 20  # 40% into the shot


def _project(tmp_path, video=True):
    (tmp_path / "out").mkdir()
    (tmp_path / "performance.json").write_text(json.dumps({"fps": 30, "characters": {"me": {}, "buddy": {}}, "lines": [
        {"id": "l1", "speaker": "buddy", "text": "I made the logo bigger."},
        {"id": "l2", "speaker": "me", "text": "Claude, I asked you to fix the navbar."},
    ]}))
    (tmp_path / "out" / "render_plan.json").write_text(json.dumps(PLAN))
    if video:
        (tmp_path / "out" / "final_9x16.mp4").write_bytes(b"")
    return tmp_path


def test_draft_variants(tmp_path):
    d = draft(_project(tmp_path))
    assert d["video"] == "out/final_9x16.mp4" and d["width"] == 1080
    assert d["variants"][0]["headline"] == ["FIX THE", "NAVBAR."]  # the hero's line first
    assert d["variants"][1]["headline"] == ["LOGO", "BIGGER."]
    assert len({v["shot"] for v in d["variants"]}) == len(d["variants"])
    assert d["variants"][0]["time"] == pytest.approx(120 / 30)


def test_draft_needs_a_video(tmp_path):
    with pytest.raises(FileNotFoundError):
        draft(_project(tmp_path, video=False))


def test_cli_writes_cover_json(tmp_path, capsys):
    p = _project(tmp_path)
    main(["cover", str(p)])
    assert capsys.readouterr().out.startswith("SHOTSAV_JSON ")
    assert json.loads((p / "out" / "cover.json").read_text())["variants"]


def test_draft_points_at_clean_frames(tmp_path):
    p = _project(tmp_path)
    (p / "out" / "frames").mkdir()
    for n in (1, 121):
        (p / "out" / "frames" / f"{n:04d}.png").write_bytes(b"")
    d = draft(p)
    assert d["frames"] == "out/frames"
    assert d["variants"][0]["still"] == "out/frames/0121.png"  # frame 120, 1-based files
    assert "still" not in d["variants"][1]
