import runpy

from reelforge import cli
from reelforge.arkit import ARKIT_NAMES
from reelforge.engines import blender3d

LIB = runpy.run_path(str(cli.REPO / "blender" / "imported.py"))


def test_imported_face_specs_use_arkit_channels_only():
    for cid, c in LIB["CHARACTERS"].items():
        channels = set(c.get("keys", {})) | set(c.get("bone_face", {}))
        assert channels <= set(ARKIT_NAMES), (cid, channels - set(ARKIT_NAMES))
        assert "jawOpen" in channels and "eyeBlinkLeft" in channels, cid
        for ch, moves in c.get("bone_face", {}).items():
            for m in moves:
                assert m[1] in ("rot", "loc", "orbit"), (cid, ch, m)


def test_imported_characters_define_the_body_contract_bones():
    for cid, c in LIB["CHARACTERS"].items():
        b = c["bones"]
        assert {"chest", "head", "head_def", "upperarm_l", "forearm_l", "upperarm_r", "forearm_r"} <= set(b), cid
        assert c["outfits"], cid


def test_imported_sets_have_the_light_contract_and_marks():
    for sid, s in LIB["SETS"].items():
        assert len(s["mark_a"]) == 3 and len(s["mark_b"]) == 3, sid
        for name, pr in s["presets"].items():
            assert all(k in pr for k in ("key", "rim", "fill", "glow", "world")), (sid, name)


def test_engine_lists_only_the_imported_cast():
    assert set(blender3d.cast_ids()) == {"matt", "freya", "cute_girl"}
    assert blender3d.set_presets() == {}  # the imported rooms are Shots-AV backdrops now
