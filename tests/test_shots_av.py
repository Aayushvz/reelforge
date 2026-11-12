"""Shots-AV style: schema fields (prompt section 5.4), the engine and look stubs, and the hero's dial table."""
import ast
import json
from pathlib import Path

import pytest

from reelforge import schema
from reelforge.engines import DEFAULT, ENGINES, get_engine, shots_av
from reelforge.schema import PerformanceError, parse_performance

REPO = Path(__file__).parents[1]
SAMPLE = REPO / "samples" / "look-test" / "performance.json"


def _av(**over) -> dict:
    d = {
        "style": "shots-av",
        "characters": {
            "me": {"model": "av_hero", "outfit": "puffer", "outfit_color": "#7C3AED", "glasses": "round",
                   "headphones": "neck"},
            "buddy": {"model": "buddy_claude"},
        },
        "camera": {"grammar": "signature", "seed": 7},
        "lines": [{"speaker": "me", "text": "Claude. The deck is done.", "beat": False, "action": ""},
                  {"speaker": "buddy", "text": "Nice!", "emotion": "happy", "action": "hop"},
                  {"speaker": "me", "text": "...Thanks.", "beat": True}],
    }
    d.update(over)
    return d


def _bad(match, **over):
    with pytest.raises(PerformanceError, match=match):
        parse_performance(_av(**over))


def test_prompt_example_parses_with_defaults():
    p = parse_performance(_av())
    assert (p.style, p.environment, p.look) == ("shots-av", "av_studio_night", "shotsav")
    me, buddy = p.characters["me"], p.characters["buddy"]
    assert me.model == "av_hero" and buddy.model == "buddy_claude" and buddy.options == {}
    assert me.options == {"outfit": "puffer", "outfit_color": "#7C3AED", "glasses": "round", "headphones": "neck"}
    assert [l.id for l in p.lines] == ["l01", "l02", "l03"]
    assert [(l.beat, l.action) for l in p.lines] == [(False, ""), (False, "hop"), (True, "")]
    assert (p.lines[0].emotion, p.lines[0].intensity, p.lines[0].mood) == ("neutral", 0.5, "calm")
    assert p.camera == {"grammar": "signature", "seed": 7}


def test_hero_options_default_to_brand_purple_puffer():
    d = _av()
    d["characters"]["me"] = {"model": "av_hero"}
    assert parse_performance(d).characters["me"].options == {
        "outfit": "puffer", "outfit_color": schema.AV_PURPLE, "glasses": "round", "headphones": "neck"}


def test_any_hex_jacket_colour_is_accepted_and_junk_is_not():
    d = _av()
    d["characters"]["me"]["outfit_color"] = "#22c55e"
    assert parse_performance(d).characters["me"].options["outfit_color"] == "#22c55e"
    for junk in ("purple", "#7C3AE", "7C3AED", 7):
        d["characters"]["me"]["outfit_color"] = junk
        with pytest.raises(PerformanceError, match="outfit_color"):
            parse_performance(d)


@pytest.mark.parametrize("key,value", [("outfit", "tuxedo"), ("outfit", 1), ("glasses", "monocle"),
                                       ("headphones", "ears")])
def test_unknown_hero_options_are_rejected(key, value):
    d = _av()
    d["characters"]["me"][key] = value
    with pytest.raises(PerformanceError, match=key):
        parse_performance(d)


@pytest.mark.parametrize("cast", [
    {"me": {"model": "av_hero"}},                                             # no buddy
    {"a": {"model": "buddy_claude"}, "b": {"model": "buddy_figma"}},          # no hero
    {"a": {"model": "av_hero"}, "b": {"model": "av_hero"}},                   # two heroes
    {"me": {"model": "av_hero"}, "buddy": {"model": "kai"}},                  # a cast member is not a buddy
    {"me": {"model": "av_hero"}, "buddy": {}},                                # model missing
])
def test_exactly_one_hero_and_one_buddy(cast):
    lines = [{"speaker": next(iter(cast)), "text": "hi"}]
    _bad("exactly one hero", characters=cast, lines=lines)


def test_line_fields_are_validated():
    base = _av()["lines"]
    _bad("beat must be", lines=[{**base[0], "beat": "yes"}])
    _bad("action must be", lines=[{**base[1], "action": "backflip"}])
    _bad("buddy clip", lines=[{**base[0], "action": "hop"}])
    _bad("unknown speaker", lines=[{"speaker": "nobody", "text": "hi"}])
    _bad("emotion", lines=[{**base[0], "emotion": "calm"}])  # calm is a mood, not an emotion


def test_camera_grammar_and_seed_are_validated():
    assert parse_performance(_av(camera={"grammar": "reference"})).camera["grammar"] == "reference"
    _bad("grammar", camera={"grammar": "handheld-doc"})
    _bad("seed", camera={"seed": "seven"})
    _bad("seed", camera={"seed": 1.5})


def test_other_styles_are_untouched():
    d = json.loads(SAMPLE.read_text(encoding="utf-8"))
    p = parse_performance(d)
    assert (p.style, p.look, p.environment) == ("blender3d", "classic", "night_city")
    assert all(c.options == {} for c in p.characters.values())
    assert all((l.beat, l.action) == (False, "") for l in p.lines)
    d["lines"][0]["beat"] = True  # the new line fields are optional everywhere
    assert parse_performance(d).lines[0].beat is True
    d["characters"]["LEAD"]["outfit"] = "puffer"  # a named outfit belongs to shots-av only
    with pytest.raises(PerformanceError, match="wardrobe index"):
        parse_performance(d)
    del d["characters"]["LEAD"]["outfit"], d["characters"]["LEAD"]["voice_id"]
    with pytest.raises(PerformanceError, match="voice_id"):
        parse_performance(d)


def test_engine_is_registered_and_default_is_unchanged():
    assert DEFAULT == "blender3d" and list(ENGINES)[0] == "blender3d"
    e = get_engine("shots-av")
    assert e is shots_av and e.NAME == "Shots-AV Animation" and e.LOOK in schema.LOOKS
    assert e.CAPABILITIES["ratios"][0] == "9:16" and e.CAPABILITIES["cost"] == "free"
    assert e.CAPABILITIES["runs"] == "local" and e.CAPABILITIES["lipsync"] == "pipeline-visemes"
    for name in ("ID", "NAME", "DESCRIPTION", "CAPABILITIES", "build_assets", "render"):
        assert hasattr(e, name)


def test_render_refuses_until_the_later_phases_exist(tmp_path):
    with pytest.raises(SystemExit, match="cannot render yet"):
        shots_av.render(None, 0, {}, [], [], tmp_path, "stills", True)


def test_look_stub_follows_the_look_contract():
    src = (REPO / "blender" / "looks" / "shotsav.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    consts = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              for t in n.targets if isinstance(t, ast.Name)}
    assert consts["NAME"] == "shotsav" and consts["USE_RIG"] is True and consts["PER_SHOT"] is False
    assert consts["MOOD_TINT"]["Key"] == 0.0  # mood tints must never reach the light on the purple jacket
    assert set(consts["DIALS"]) == {"key_warmth", "rim", "haze", "bokeh", "screen_flicker", "saturation"}
    for name in ("MOOD_TINT", "LIGHT_SCALE", "DESATURATE", "BODY_CHEAT", "LISTEN_YAW"):
        assert name in consts
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {"apply_scene", "shot_settings"} <= funcs
    assert "shotsav" in (REPO / "blender" / "looks" / "__init__.py").read_text(encoding="utf-8")


def test_hero_table_matches_the_schema_and_the_brand():
    t = shots_av.hero_tables()  # hero.py must import without Blender
    hero = t["HERO"]
    assert tuple(t["OUTFITS"]) == schema.AV_OUTFITS
    assert tuple(hero["glasses"]["options"]) == schema.AV_GLASSES and hero["glasses"]["default"] == "round"
    assert set(hero["headphones"]["options"]) == set(schema.AV_HEADPHONES) and hero["headphones"]["default"] == "neck"
    assert tuple(hero["hair"]["options"]) == ("swept", "curly_top", "buzz") and hero["hair"]["default"] == "swept"
    assert len(t["SKINS"]) == 6 and hero["skin"]["default"] in t["SKINS"]
    assert hero["stubble"]["default"] == 0.3 and hero["outfit"]["default"] == "puffer"
    assert t["BRAND"] == {"purple": "#7C3AED", "purple_mid": "#6D28D9", "purple_soft": "#A78BFA",
                          "lilac": "#DDD6FE", "ink": "#1F1F1F", "cream": "#F4F2EE"}
    assert hero["outfit_color"]["default"] == schema.AV_PURPLE
    assert len(t["MOUTH_SHAPES"]) == 8 and t["MOUTH_SHAPES"][0] == "rest"
    assert tuple(t["HAND_POSES"]) == ("rest", "fist_cheek", "point", "open", "type")
    assert shots_av.hero_blend("puffer").name == "av_hero__puffer.blend"
