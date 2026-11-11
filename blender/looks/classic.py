"""The original look: Eevee everywhere, the SHOT-table cameras in render_plan.py. Settings are unchanged."""
import bpy

from bl_common import EEVEE

NAME = "classic"
USE_RIG = False
PER_SHOT = False
MOOD_TINT = {"Key": 1.0, "Rim": 1.0, "Glow": 1.0}
LIGHT_SCALE = {"Key": 1.0, "Rim": 1.0, "Glow": 1.0, "Fill": 1.0}
BODY_CHEAT = 0.0
LISTEN_YAW = 0.35


def apply_scene(sc, plan, characters):
    sc.render.engine = EEVEE
    sc.eevee.taa_render_samples = plan["samples"]
    sc.render.resolution_x, sc.render.resolution_y = plan["resolution"]
    sc.render.resolution_percentage = plan.get("resolution_percentage", 100)
    sc.render.fps = plan["fps"]
    sc.frame_start, sc.frame_end = 1, plan["n_frames"]
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"


def shot_settings(sc, plan, shot):
    return sc.render.engine
