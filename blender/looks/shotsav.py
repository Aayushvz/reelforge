"""The Shots-AV look: Eevee only, camera_rig cameras, soft shadows, real depth of field, Khronos PBR Neutral.

Not AgX (the prompt's first choice): AgX renders a lit #7C3AED card pastel at every exposure (best dE 49), while
PBR Neutral at -0.75 keeps the jacket within dE 2-9 (P1 purple check). Contrast comes back in P5's grade.

P0 stub: the render settings are real; the look_params dials are read, clamped and stored on the scene, and
none of them acts until the rooms exist (P3 wires them to the room's lights and world; P5's grade owns
saturation).
The key stays neutral-warm and takes no mood tint, so the jacket holds brand purple (#7C3AED) on every line."""
import bpy

from bl_common import EEVEE

NAME = "shotsav"
USE_RIG = True
PER_SHOT = False
MOOD_TINT = {"Key": 0.0, "Rim": 0.6, "Glow": 1.0}  # moods colour the room, never the light on the jacket
LIGHT_SCALE = {"Key": 1.0, "Rim": 1.0, "Glow": 1.0, "Fill": 1.0}
DESATURATE = {"Key": 0.25}
EXPOSURE = -0.75  # brand purple holds here under the neutral-warm key
BODY_CHEAT = 0.0  # the hero faces the desk; the buddy turns by itself
LISTEN_YAW = 0.22
DIALS = {"key_warmth": 1.0, "rim": 1.0, "haze": 1.0, "bokeh": 1.0, "screen_flicker": 1.0, "saturation": 1.0}


def dials(plan):
    lp = plan.get("look_params", {})
    return {k: min(2.0, max(0.0, float(lp.get(k, v)))) for k, v in DIALS.items()}


def apply_scene(sc, plan, characters):
    d = dials(plan)
    sc.render.engine = EEVEE
    sc.eevee.taa_render_samples = plan["samples"]
    sc.render.resolution_x, sc.render.resolution_y = plan["resolution"]
    sc.render.resolution_percentage = plan.get("resolution_percentage", 100)
    sc.render.fps = plan["fps"]
    sc.frame_start, sc.frame_end = 1, plan["n_frames"]
    im = sc.render.image_settings
    im.file_format, im.color_depth, im.color_mode, im.compression = "PNG", "8", "RGB", 15
    sc.render.dither_intensity = 1.0
    sc.eevee.use_raytracing = True  # contact shadows and ambient occlusion under every object
    if hasattr(sc.eevee, "shadow_ray_count"):  # glasses and hair tips cast thin soft shadows: 1 ray is grainy
        sc.eevee.shadow_ray_count, sc.eevee.shadow_step_count = 4, 12
    if hasattr(sc.eevee, "shadow_pool_size"):
        sc.eevee.shadow_pool_size = "1024"
    sc.view_settings.view_transform, sc.view_settings.look = "Khronos PBR Neutral", "None"
    sc.view_settings.exposure = float(sc.get("av_exposure", EXPOSURE))  # each room stores its own
    sc.view_settings.gamma = 1.0
    sc["shotsav_dials"] = d
    print(f"shotsav look: dials={d}")


def shot_settings(sc, plan, shot):
    return sc.render.engine
