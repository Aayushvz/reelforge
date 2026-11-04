import shutil
import subprocess

import pytest

from reelforge import cli


def test_parser_run_defaults(tmp_path):
    ns = cli.build_parser().parse_args(["run", str(tmp_path)])
    assert ns.cmd == "run" and ns.stage == "full" and ns.draft is False


def test_missing_api_key_exits(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    shutil.copy(cli.REPO / "samples" / "look-test" / "performance.json", tmp_path / "performance.json")
    with pytest.raises(SystemExit) as e:
        cli.main(["run", str(tmp_path), "--stage", "stills"])
    assert "ELEVENLABS_API_KEY" in str(e.value.code)


def test_imported_audio_used_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    src = cli.REPO / "samples" / "look-test"
    shutil.copy(src / "performance.json", tmp_path / "performance.json")
    audio = tmp_path / "out" / "audio"
    audio.mkdir(parents=True)
    for lid in ("l01", "l02"):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
             "-t", "1", "-c:a", "libmp3lame", str(audio / f"{lid}.mp3")], check=True)
    used = []
    real_import = cli.import_line

    def fake_import(line, audio_dir, transcribe=None):
        used.append(line.id)
        return real_import(line, audio_dir, transcribe=lambda p: [("hi", 0.1, 0.4)])

    monkeypatch.setattr(cli, "import_line", fake_import)

    class Stop(Exception):
        pass

    def stop(*a, **k):
        raise Stop

    monkeypatch.setattr(cli.ENGINES["blender3d"], "render", stop)
    with pytest.raises(Stop):
        cli.main(["run", str(tmp_path), "--stage", "stills"])
    assert used == ["l01", "l02"]


def test_style_defaults_to_blender3d_and_unknown_style_exits(tmp_path):
    from reelforge.schema import load_performance
    from reelforge.engines import get_engine
    perf = load_performance(cli.REPO / "samples" / "look-test" / "performance.json")
    assert perf.style == "blender3d" and get_engine(perf.style).ID == "blender3d"
    with pytest.raises(SystemExit) as e:
        get_engine("nope")
    assert "blender3d" in str(e.value.code)


def test_character_model_defaults_to_kai_and_reaches_the_plan(tmp_path):
    from reelforge.plan import build_render_plan
    from reelforge.schema import parse_performance
    perf = parse_performance({"characters": {"A": {"voice_id": "v", "model": "noor", "outfit": 2},
                                             "B": {"voice_id": "w"}},
                              "lines": [{"id": "l1", "speaker": "A", "text": "hi", "emotion": "happy",
                                         "intensity": 0.5, "mood": "calm"}]})
    plan = build_render_plan(perf, 1, {"A": {}, "B": {}}, [], [], tmp_path, tmp_path, 16)
    assert [c["blend"] for c in plan["characters"]] == [str(tmp_path / "noor__o2.blend"), str(tmp_path / "kai.blend")]


def test_lighting_picks_the_preset_blend(tmp_path):
    from reelforge.plan import build_render_plan
    from reelforge.schema import parse_performance
    base = {"characters": {"A": {"voice_id": "v"}}, "environment": "cafe",
            "lines": [{"id": "l1", "speaker": "A", "text": "hi", "emotion": "happy", "intensity": 0.5, "mood": "calm"}]}
    plain = build_render_plan(parse_performance(base), 1, {"A": {}}, [], [], tmp_path, tmp_path, 16)
    lit = build_render_plan(parse_performance({**base, "lighting": "rainy_day"}), 1, {"A": {}}, [], [], tmp_path,
                            tmp_path, 16)
    assert plain["environment_blend"] == str(tmp_path / "cafe.blend")
    assert lit["environment_blend"] == str(tmp_path / "cafe__rainy_day.blend")


def test_every_set_has_three_presets_with_the_light_contract():
    import runpy
    sets = runpy.run_path(str(cli.REPO / "blender" / "sets.py"))["SETS"]
    assert len(sets) == 10
    for sid, s in sets.items():
        assert len(s["presets"]) == 3, sid
        for name, pr in s["presets"].items():
            assert all(k in pr for k in ("key", "rim", "fill", "glow", "world")), (sid, name)


def test_every_cast_member_has_three_outfits_and_the_wardrobe_has_25_items():
    import runpy
    cast = runpy.run_path(str(cli.REPO / "blender" / "cast.py"))["CAST"]
    assert len(cast) == 7
    items = set()
    for cid, c in cast.items():
        assert len(c["outfits"]) == 3, cid
        for o in c["outfits"]:
            m = {**c, **o}
            items |= {m["top_type"], m["outer"], m["hat"], m["print_shape"] or ("print" if m["print"] else None),
                      m["earring"], m["chain"], m["glasses"], "watch" if m["watch"] else None}
    items.discard(None)
    assert len(items) >= 25, sorted(items)
