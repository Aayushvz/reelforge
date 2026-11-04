import re
from pathlib import Path

from reelforge.direct import Shot
from reelforge.plan import build_render_plan
from reelforge.schema import parse_performance

SRC = (Path(__file__).resolve().parents[1] / "blender" / "render_plan.py").read_text(encoding="utf-8")


def test_plan_has_every_key_the_blender_side_reads(tmp_path):
    perf = parse_performance({"characters": {"A": {"voice_id": "v"}},
                              "lines": [{"id": "l1", "speaker": "A", "text": "hi", "emotion": "happy",
                                         "intensity": 0.5, "mood": "calm"}]})
    shot = Shot(0, 10, "wide", 35, "A", 0.1)
    plan = build_render_plan(perf, 10, {"A": {"jawOpen": [0.0] * 10}}, [shot], [(0, "calm")], tmp_path, tmp_path, 16)
    required = set(re.findall(r'plan\["(\w+)"\]', SRC))  # plan.get(...) keys are optional by design
    assert required and required <= set(plan), required - set(plan)
    for key in set(re.findall(r'char\["(\w+)"\]', SRC)):
        assert key in plan["characters"][0], key
    for key in set(re.findall(r'\b(?:s|sh)\["(\w+)"\]', SRC)):
        assert key in plan["shots"][0], key
