"""The liveliness pass sorts materials by name; a wrong bucket would, say, make eyelashes glassy."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("liveliness", Path(__file__).resolve().parents[1] / "blender" / "liveliness.py")
liveliness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(liveliness)


def test_material_buckets():
    expect = {
        # Matt (Character Creator)
        "Std_Skin_Head": "skin", "Std_Skin_Leg": "skin", "Std_Nails": "other", "Std_Eyelash": "hair",
        "Std_Cornea_L": "cornea", "Std_Eye_R": "eye", "Std_Eye_Occlusion_L": "other", "Std_Tearline_R": "other",
        "Std_Upper_Teeth": "wet", "Std_Tongue": "wet", "Hair_Transparency": "hair", "Scalp_Transparency": "hair",
        "Fit_shirts": "other", "Slim_Jeans": "other",
        # Freya
        "Body": "skin", "Eyes": "eye", "Glass": "cornea", "Eyebrows": "hair", "Eyelashes": "hair", "Hair": "hair",
        "Cap": "hair", "Mouth": "wet", "Top": "other", "Stockings": "other",
        # Mina
        "body": "skin", "eyes": "eye", "hair": "hair", "teeth": "wet", "teeth.001": "wet", "jean": "other",
    }
    assert {n: liveliness.kind(n) for n in expect} == expect


def test_bodysuit_is_not_skin():
    assert liveliness.kind("Bodysuit") == "other"
