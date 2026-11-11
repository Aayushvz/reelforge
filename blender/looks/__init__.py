"""Render looks of the blender3d engine. A look owns the render settings, the per-shot engine choice and a few
staging dials; render_plan.py asks the look instead of hard-coding them.

Look module contract: NAME, USE_RIG (camera_rig.py cameras instead of the classic ones), PER_SHOT (render each
shot's frame range on its own, so shots can use different engines), MOOD_TINT (light name -> share of the mood
tint it takes), LIGHT_SCALE (light name -> energy multiplier), BODY_CHEAT (radians two characters turn toward each other), LISTEN_YAW (radians a listener's
head turns), apply_scene(sc, plan, characters), shot_settings(sc, plan, shot) -> engine id."""
from . import cinema, classic

LOOKS = {m.NAME: m for m in (classic, cinema)}


def get(name):
    return LOOKS.get(name or "classic", classic)
