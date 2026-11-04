import json

from reelforge.engines import blender3d


def _plan(tmp_path):
    env, char = tmp_path / "env.blend", tmp_path / "char.blend"
    env.write_bytes(b"e")
    char.write_bytes(b"c")
    return {"environment_blend": str(env), "characters": [{"blend": str(char)}], "n_frames": 2,
            "shots": [{}], "x": 1}


def test_render_key_changes_with_plan_and_assets(tmp_path):
    plan = _plan(tmp_path)
    k1 = blender3d.render_key(json.dumps(plan), plan)
    assert k1 == blender3d.render_key(json.dumps(plan), plan)
    assert k1 != blender3d.render_key(json.dumps({**plan, "x": 2}), plan)
    (tmp_path / "char.blend").write_bytes(b"cc")  # rebuilt character
    assert k1 != blender3d.render_key(json.dumps(plan), plan)
