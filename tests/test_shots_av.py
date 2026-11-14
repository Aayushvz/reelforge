"""Shots-AV style: schema fields (prompt section 5.4), the engine and look stubs, and the hero's dial table."""
import ast
import json
from pathlib import Path

import pytest

from reelforge import schema
from reelforge.engines import DEFAULT, ENGINES, get_engine, shots_av
from reelforge.schema import PerformanceError, parse_performance

REPO = Path(__file__).parents[1]
SAMPLE = REPO / "tests" / "fixtures" / "blender3d_performance.json"


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
    assert me.options == {"outfit": "puffer", "outfit_color": "#7C3AED", "glasses": "round", "headphones": "neck",
                          "skin": "wheat", "hair": "fringe", "beard": "light", "stubble": 0.3}
    assert [l.id for l in p.lines] == ["l01", "l02", "l03"]
    assert [(l.beat, l.action) for l in p.lines] == [(False, ""), (False, "hop"), (True, "")]
    assert (p.lines[0].emotion, p.lines[0].intensity, p.lines[0].mood) == ("neutral", 0.5, "calm")
    assert p.camera == {"grammar": "signature", "seed": 7}


def test_hero_options_default_to_brand_purple_puffer():
    d = _av()
    d["characters"]["me"] = {"model": "av_hero"}
    assert parse_performance(d).characters["me"].options == {
        "outfit": "puffer", "outfit_color": schema.AV_PURPLE, "glasses": "bold", "headphones": "neck",
        "skin": "wheat", "hair": "fringe", "beard": "light", "stubble": 0.3}


@pytest.mark.parametrize("skin", schema.AV_SKINS)
@pytest.mark.parametrize("hair", schema.AV_HAIRS)
def test_every_skin_and_hair_is_a_user_choice(skin, hair):
    d = _av()
    d["characters"]["me"].update(skin=skin, hair=hair, stubble=0)
    o = parse_performance(d).characters["me"].options
    assert (o["skin"], o["hair"], o["stubble"]) == (skin, hair, 0.0)


def test_hero_blend_names_each_combination_once():
    a = shots_av.hero_blend({"outfit": "hoodie", "skin": "deep", "hair": "buzz", "outfit_color": "#22C55E"})
    assert a == shots_av.hero_blend({"hair": "buzz", "outfit_color": "#22c55e", "skin": "deep", "outfit": "hoodie"})
    assert a.name == "av_hero__hoodie__deep__buzz__bold__neck__light__22c55e__s030.blend"
    assert shots_av.hero_blend({}).name == "av_hero__puffer__wheat__fringe__bold__neck__light__7c3aed__s030.blend"
    assert shots_av.hero_blend({"skin": "tan"}) != shots_av.hero_blend({"skin": "light"})


def test_any_hex_jacket_colour_is_accepted_and_junk_is_not():
    d = _av()
    d["characters"]["me"]["outfit_color"] = "#22c55e"
    assert parse_performance(d).characters["me"].options["outfit_color"] == "#22c55e"
    for junk in ("purple", "#7C3AE", "7C3AED", 7):
        d["characters"]["me"]["outfit_color"] = junk
        with pytest.raises(PerformanceError, match="outfit_color"):
            parse_performance(d)


@pytest.mark.parametrize("key,value", [("outfit", "tuxedo"), ("outfit", 1), ("glasses", "monocle"),
                                       ("headphones", "ears"), ("skin", "green"), ("hair", "mohawk"),
                                       ("stubble", 2), ("stubble", "some"), ("beard", "full")])
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
    _bad("two speakers", characters=cast, lines=lines)


@pytest.mark.parametrize("me, other", [("matt", "buddy_claude"), ("av_hero", "freya"), ("cute_girl", "matt")])
def test_realistic_cast_in_either_slot(me, other):
    from reelforge.engines import shots_av
    d = _av()
    d["characters"] = {"me": {**d["characters"]["me"], "model": me}, "buddy": {**d["characters"]["buddy"], "model": other}}
    for k in ("outfit", "outfit_color", "glasses", "headphones", "skin", "hair", "beard", "stubble"):
        if me != "av_hero":
            d["characters"]["me"].pop(k, None)
    d["lines"] = [{k: v for k, v in l.items() if k != "action"} for l in d["lines"]]
    perf = parse_performance(d)
    assert shots_av.cast(perf) == ("me", "buddy")
    tints = shots_av.caption_tints(perf)
    assert set(tints) == {"me", "buddy"} and all(t.startswith("#") for t in tints.values())


def test_no_key_taps_or_blips_without_their_cast():
    from types import SimpleNamespace as NS
    from reelforge.engines import shots_av
    perf = NS(characters={"me": NS(model="matt"), "buddy": NS(model="freya")})
    placed = [NS(line=NS(speaker="buddy"), start=0.5, duration=1.0), NS(line=NS(speaker="me"), start=2.0, duration=1.0)]
    assert shots_av.sound_plan(placed, [], "me", "buddy", 120, 24, perf) == ([], [])
    perf.characters["buddy"].model = "buddy_claude"
    assert shots_av.sound_plan(placed, [], "me", "buddy", 120, 24, perf)[0] == [0.5]


def test_build_plan_routes_each_kind(tmp_path, monkeypatch):
    from types import SimpleNamespace as NS
    from reelforge.engines import shots_av
    monkeypatch.setattr(shots_av, "build_render_plan", lambda *a, **k: {"characters": [
        {"name": "me", "mark": "Mark_B"}, {"name": "buddy", "mark": "Mark_A"}], "shots": [
        {"subject": "buddy", "framing": {"eyes": 0.62, "head": 0.38}}]})
    monkeypatch.setattr(shots_av, "room_view", lambda perf, seed: {})
    perf = NS(characters={"me": NS(model="freya", options={}), "buddy": NS(model="matt", options={})},
              environment="av_studio_night", quality="standard", fps=24)
    faces = {"me": {"jawOpen": [0.0] * 4}, "buddy": {"jawOpen": [0.0] * 4}}
    plan = shots_av.build_plan(perf, 4, faces, [], [], tmp_path, True, [])
    me, bud = plan["characters"]
    assert (me["mark"], me["seat"]["slot"], Path(me["blend"]).name) == ("Mark_A", "you", "freya.blend")
    assert (bud["mark"], bud["seat"]["slot"], Path(bud["blend"]).name) == ("Mark_B", "guest", "matt.blend")
    assert me["seat"]["legs"] and "props" not in me
    assert plan["shots"][0]["framing"] == {"eyes": 0.52, "head": 0.38}  # a person in the guest seat: eyes up


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


def test_buddy_table_matches_the_schema_and_the_acting_controls():
    from reelforge import buddy as acting
    t = shots_av.buddy_tables()
    assert tuple(f"buddy_{b}" for b in t["BUDDIES"]) == schema.AV_BUDDIES
    assert tuple(t["BUDDY_CONTROLS"]) == acting.CONTROLS
    assert {k: v for k, v in t["BUDDY_CONTROLS"].items() if v} == {"eye_h": 1.0} == {
        k: v for k, v in acting.REST.items() if v}
    for bid, b in t["BUDDIES"].items():
        assert 0.13 <= b["height"] <= 0.15, bid  # about 0.4 of the hero's 0.34 m head
        assert 0 <= b["feet"] <= 4 and b["signature"], bid  # robots stand on feet, a puck, a stand block or hover
    assert t["EYE"] == (0.011, 0.019) and t["MOUTH_BARS"] == 9
    assert t["BUDDIES"]["claude"]["shell"] == "#D97757" and t["BUDDIES"]["chatgpt"]["glow"] == "#10A37F"
    assert set(t["BUDDIES"]["figma"]["blocks"].values()) == {"#F24E1E", "#FF7262", "#A259FF", "#1ABCFE", "#0ACF83"}
    assert shots_av.buddy_blend("buddy_nova").name == "buddy_nova.blend"


def test_room_table_matches_the_schema_and_the_contract():
    t = shots_av.room_tables()
    assert tuple(t["ROOMS"]) == schema.AV_ROOMS and schema.AV_ROOM in t["ROOMS"]
    tones = [r["tone"] for r in t["ROOMS"].values()]
    assert tones.count("dark") == 16 and tones.count("light") == 9
    assert [k for k, r in t["ROOMS"].items() if r.get("gamer")] == list(schema.AV_ROOMS[6:12])  # the 3D gamer rooms
    old = [k for k, r in t["ROOMS"].items() if r.get("legacy")]
    imp = [k for k, r in t["ROOMS"].items() if r.get("imported")]
    assert len(old) == 10 and len(imp) == 3 and list(schema.AV_ROOMS[12:]) == old + imp  # the old library's rooms
    assert t["VIEW_PAN_M"] > 1.0 and 0 < t["VIEW_HEIGHT_M"] < 0.5
    for rid, r in t["ROOMS"].items():
        for light in ("key", "rim", "fill", "glow"):
            color, energy, pos, size = r[light]
            assert energy > 0 and len(pos) == 3 and size > 0, (rid, light)
        assert -2.5 < r["exposure"] < 0 and r["look"], rid
    assert t["MARK_B"] == (-0.30, -0.36, 0.74) and t["DESK_Z"] == 0.74
    assert t["NEUTRAL_WARM"] == (1.0, 0.85, 0.72)  # never the reference's orange: it turns purple brown
    assert shots_av.room_blend("av_cafe_day").name == "av_cafe_day.blend"


def test_shots_av_environment_must_be_one_of_the_rooms():
    assert parse_performance(_av(environment="av_cyc_lilac")).environment == "av_cyc_lilac"
    _bad("environment must be one of", environment="night_city")


def test_acting_tracks_and_animatic_timing():
    from reelforge.direct import Shot
    n, fps = 300, 30
    faces = {"me": {"eyeBlinkLeft": [0.0] * n, "eyeBlinkRight": [0.0] * n}}
    shots = [Shot(0, 90, "av_hero_34", 85, "me", 0.0), Shot(90, 150, "av_buddy", 100, "bot", 0.0),
             Shot(150, 300, "av_hero_front", 85, "me", 0.0)]
    props = shots_av.hero_acting(faces, shots, "me", n, fps)
    assert faces["me"]["eyeBlinkLeft"][151] == 1.0 and faces["me"]["eyeBlinkLeft"][1] == 0.0  # a blink on the cut
    hand = props["PoseCtrl"]["HandL"]
    assert hand[0] == 1.0 and hand[-1] == 4.0 and sum(a != b for a, b in zip(hand, hand[1:])) == 1  # think -> type
    assert hand.index(4.0) == 150  # ...once, and it lands on a cut
    p = parse_performance(_av())
    timing = shots_av.estimate_timing(p.lines)
    assert all(b[0] >= a[0] + a[1] for a, b in zip(timing, timing[1:]))
    assert shots_av.WANTS_PLACED and shots_av.cast(p) == ("me", "buddy")


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
    assert tuple(hero["glasses"]["options"]) == schema.AV_GLASSES and hero["glasses"]["default"] == "bold"
    assert tuple(hero["beard"]["options"]) == schema.AV_BEARDS and hero["beard"]["default"] == "light"
    assert set(hero["headphones"]["options"]) == set(schema.AV_HEADPHONES) and hero["headphones"]["default"] == "neck"
    assert tuple(hero["hair"]["options"]) == schema.AV_HAIRS and hero["hair"]["default"] == "fringe"
    assert set(t["SKINS"]) == set(schema.AV_SKINS) and hero["skin"]["default"] == schema.AV_SKINS[0]
    assert tuple(hero["hair"]["options"]) == tuple(schema.AV_HAIRS)
    assert hero["stubble"]["default"] == 0.3 and hero["outfit"]["default"] == "puffer"
    assert t["BRAND"] == {"purple": "#7C3AED", "purple_mid": "#6D28D9", "purple_soft": "#A78BFA",
                          "lilac": "#DDD6FE", "ink": "#1F1F1F", "cream": "#F4F2EE"}
    assert hero["outfit_color"]["default"] == schema.AV_PURPLE
    assert len(t["MOUTH_SHAPES"]) == 8 and t["MOUTH_SHAPES"][0] == "rest"
    assert tuple(t["HAND_POSES"]) == ("rest", "fist_cheek", "point", "open", "type")


def test_editor_options_in_the_schema():
    p = parse_performance(_av(camera={"rack": False, "drift": 1.5}, captions={"position": "lower", "plate": False},
                              sound={"foley": False}))
    assert p.camera["rack"] is False and p.captions["position"] == "lower" and p.sound == {"foley": False}
    assert parse_performance(_av()).captions == {} and parse_performance(_av()).sound == {}
    _bad("camera.rack", camera={"rack": "no"})
    _bad("camera.drift", camera={"drift": 3})
    _bad("captions.position", captions={"position": "middle"})
    _bad("sound.foley", sound={"foley": 1})


def test_catalog_and_plan_for_the_editor(tmp_path):
    cat = shots_av.catalog()
    assert [b["model"] for b in cat["buddies"]] == list(schema.AV_BUDDIES)
    assert [r["id"] for r in cat["rooms"]] == list(schema.AV_ROOMS)
    assert cat["hero"]["hair"]["options"] == list(schema.AV_HAIRS) and cat["target"]["buddy"] == 0.46
    assert set(cat["timing"]) >= {"preview_still_s", "draft_s_per_frame", "final_s_per_frame"}
    (tmp_path / "performance.json").write_text(json.dumps(_av()), encoding="utf-8")
    plan = shots_av.plan_for(tmp_path)
    assert plan["shots"][-1]["kind"] == "av_wide_front"  # (a 3-line script folds into the 4.5 s closing wide)
    assert plan["shots"][0]["start"] == 0 and plan["shots"][-1]["end"] == pytest.approx(plan["runtime"])
    assert abs(sum(plan["split"].values()) - 1.0) < 1e-3 and plan["runtime"] > 0


def test_ported_wardrobe_matches_the_hero_table():
    t = shots_av.hero_tables()
    assert tuple(t["OUTFITS"]) == schema.AV_OUTFITS and len(schema.AV_OUTFITS) == 24
    for k, c in schema.AV_OUTFIT_COLORS.items():
        assert t["OUTFIT_COLORS"][k] == c, k
    p = schema.parse_performance({"style": "shots-av", "characters": {
        "me": {"model": "av_hero", "outfit": "varsity"}, "b": {"model": "buddy_claude"}}, "lines": [{"speaker": "me", "text": "hi"}]})
    assert p.characters["me"].options["outfit_color"] == "#1C2F68"  # a ported outfit keeps its own colour
