"""The Shots-AV hero "AV": the owner's low-poly stand-in, seated at a desk, in Aayush Visuals purple.

Top of the file is pure data (the dial table the engine, the editor and the tests read without Blender).
build() runs inside Blender and makes the standard rig contract in a collection CHAR_base:
CHAR_root -> Body (hip pivot) -> Spine (Lean) -> torso, arms, Head -> HeadGeo -> face; ElbowL/ElbowR (talk
gestures, keyed by render_plan.py), FaceCtrl (52 ARKit props), FaceAnchor (head_height), EyeFocus, and
PoseCtrl with HandL / HandR (pose index into HAND_POSES, fractions blend) and Lean (-1..1).
Metres, facing -Y, character's left is +X. Every moving part is a driver, so the pipeline only keys props.
"""
from __future__ import annotations

import math

try:
    import bmesh
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector
except ImportError:  # read as a data table outside Blender
    bpy = None

# --- dials (pure data) ----------------------------------------------------------------------------------
BRAND = {"purple": "#7C3AED", "purple_mid": "#6D28D9", "purple_soft": "#A78BFA", "lilac": "#DDD6FE",
         "ink": "#1F1F1F", "cream": "#F4F2EE"}
SKINS = {"wheat": "#D6A688", "porcelain": "#F2D3BC", "light": "#E8BE9A", "tan": "#D3A074", "warm_brown": "#B9804F",
         "brown": "#8E5A39", "deep": "#5E3B28"}  # wheat: the owner's own tone, read from his photo
OUTFITS = {
    "puffer": {"label": "Purple puffer", "open": True, "bands": 4, "puff": 0.011, "shell": 0.012, "tee": "ink",
               "collar": "stand", "sleeve_bands": 2, "arm": 0.062},
    "hoodie": {"label": "Purple hoodie", "open": False, "bands": 0, "puff": 0.0, "shell": 0.007, "tee": "ink",
               "collar": "hood", "sleeve_bands": 0, "arm": 0.056},
    "overshirt": {"label": "Purple overshirt", "open": True, "bands": 0, "puff": 0.0, "shell": 0.005,
                  "tee": "cream", "collar": "shirt", "sleeve_bands": 0, "arm": 0.052},
}
HERO = {
    "outfit": {"default": "puffer", "options": list(OUTFITS)},
    "outfit_color": {"default": BRAND["purple"],
                     "swatches": [BRAND[k] for k in ("purple", "purple_mid", "purple_soft", "lilac", "ink")]},
    "hair": {"default": "fringe", "options": ["fringe", "soft_fringe", "curtain", "swept", "curly_top", "buzz"]},
    "hair_color": {"default": "#15110F"},
    "glasses": {"default": "bold", "options": ["bold", "round", "rect", "none"]},  # bold: his black acetate frames
    "headphones": {"default": "neck", "options": ["on", "neck", "none"]},
    "skin": {"default": "wheat", "options": list(SKINS)},
    "beard": {"default": "light", "options": ["light", "stubble", "none"]},  # light: thin moustache + chin beard
    "stubble": {"default": 0.3, "min": 0.0, "max": 1.0},
    "chest_mark": {"default": False},
}
MOUTH_SHAPES = ("rest", "MBP", "small", "wide", "O", "E", "FV", "smile")  # plus corner up/down and a side shift
HAND_POSES = ("rest", "fist_cheek", "point", "open", "type")
DEFAULTS = {k: v["default"] for k, v in HERO.items()}

# --- proportions (metres, seated; the desk top is at 0.74) ---------------------------------------------------
HC_Z = 1.20  # head centre; the eyes sit 0.02 below it, at 1.18
RX, RY, RZT, RZB = 0.152, 0.165, 0.190, 0.180  # head about 0.31 wide, 0.37 tall: an oval, taller than wide
JAW, TAPER, CHIN = 0.0, 0.16, 0.80  # straight cheeks into defined jaw corners and a flat chin: oval-squarish (the owner's)
SQUARE = 3.4  # superellipse power of the lower face's outline (2 = round)
SMILE_REST = 0.10  # calm and serious at rest; the smile is saved for when he means it
EYE_X, EYE_Z, EYE_R = 0.0570, -0.026, (0.0145, 0.0058, 0.0235)  # big glossy ovals 0.029 x 0.047: innocent,
# readable at phone size; set a little low so the face keeps an open forehead
BROW_Z = 0.034  # just above the frame top, as in his photo, so the brows still act
NECK_Z = 1.035
BODY_AT = (0.0, 0.03, 0.62)
SHOULDER = (0.165, 0.0, 0.955)  # shoulders 0.46 wide over the sleeves
LU, LF = 0.17, 0.17  # upper arm and forearm: short and thick
GAP = 0.0013  # the resting mouth is a thin dark line
LIP_DEPTH = 0.009
MOUTH_ROW, MOUTH_COLS, HEAD_CUTS = 5, 5, 63

# Hand poses for the left hand (+X); the right mirrors in X. wrist/hint/finger/palm are in root space.
# gain = how much of render_plan's talking-hand lift (ElbowL/R) the pose lets through.
POSES = {
    "rest": {"wrist": (0.085, -0.205, 0.792), "hint": (1.0, 0.4, -0.5), "finger": (-0.40, -1.0, -0.36),
             "palm": (0.0, 0.0, -1.0), "gain": 1.0, "curl": (0.25, 0.30), "thumb": (0.55, 0.15, 0.2)},
    "fist_cheek": {"wrist": (0.205, -0.125, 1.03), "hint": (0.5, -0.6, -0.8), "finger": (-0.55, 0.15, 0.85),
                   "palm": (-0.75, 0.55, -0.35), "gain": 0.0, "curl": (1.45, 1.50), "thumb": (0.25, 0.9, 0.8)},
    "point": {"wrist": (0.12, -0.30, 0.93), "hint": (1.0, 0.2, -0.6), "finger": (-0.22, -1.0, -0.08),
              "palm": (-0.5, 0.0, -0.85), "gain": 0.35, "curl": (1.45, 1.50), "index": (0.05, 0.05),
              "thumb": (0.25, 0.85, 0.7)},
    "open": {"wrist": (0.20, -0.24, 0.90), "hint": (1.0, 0.3, -0.7), "finger": (0.55, -0.8, 0.25),
             "palm": (0.0, -0.6, 0.8), "gain": 0.6, "curl": (0.08, 0.10), "thumb": (0.95, 0.0, 0.1)},
    "type": {"wrist": (0.085, -0.20, 0.80), "hint": (1.0, 0.4, -0.5), "finger": (-0.12, -1.0, -0.30),
             "palm": (0.0, 0.0, -1.0), "gain": 0.15, "curl": (0.55, 0.60), "thumb": (0.6, 0.25, 0.3)},
}

# Mouth shapes (metres): half-width a, upper/lower lip travel hu/hl, corner exponent n (2 = oval, higher =
# rounded rectangle), lift = corners up along a parabola, fwd = lips pushed forward, shift = whole mouth sideways.
MOUTH = {
    "MBP": {"a": 1.04, "hu": -GAP / 2, "hl": -GAP / 2},
    "small": {"a": 0.86, "hu": 0.0025, "hl": 0.0080, "n": 3.0},
    "wide": {"a": 1.08, "hu": 0.0060, "hl": 0.0220, "n": 2.6},
    "O": {"a": 0.54, "hu": 0.0085, "hl": 0.0115, "n": 2.0, "fwd": 0.004},
    "E": {"a": 1.50, "hu": 0.0030, "hl": 0.0050, "n": 3.5, "lift": 0.008},
    "FV": {"a": 0.95, "hu": 0.0060, "hl": -0.0030, "n": 3.0, "fwd_low": -0.0025},
    "smile": {"a": 1.62, "lift": 0.021},
    "cornerUpL": {"a_l": 1.34, "lift_l": 0.017},
    "cornerUpR": {"a_r": 1.34, "lift_r": 0.017},
    "cornerDownL": {"a_l": 1.12, "lift_l": -0.014},
    "cornerDownR": {"a_r": 1.12, "lift_r": -0.014},
    "side": {"shift": 0.006},
}
# The 52 ARKit channels mapped down to the mouth shapes (simple driver expressions; see _mouth_drivers).
MOUTH_DRIVERS = {
    "O": "clamp(max(fu,pu))",
    "small": "clamp(j*(1-0.5*clamp(max(fu,pu)))/0.3)*clamp(1-(j*(1-0.5*clamp(max(fu,pu)))-0.3)/0.5)",
    "wide": "clamp((j*(1-0.5*clamp(max(fu,pu)))-0.3)/0.5)",
    "MBP": "clamp(max(mc,(pl+pr)*0.72))*clamp(1-4*j)",
    "FV": "clamp(rl/0.6)*(1-clamp((pl+pr)*0.72))",
    "E": "clamp((sl+sr)*1.43)",
    "smile": "min(ml,mr)",
    "cornerUpL": "ml-min(ml,mr)",
    "cornerUpR": "mr-min(ml,mr)",
    "cornerDownL": "clamp(fl)",
    "cornerDownR": "clamp(fr)",
    "side": "clamp(xl-xr,-1,1)",
}
MOUTH_VARS = {"j": "jawOpen", "fu": "mouthFunnel", "pu": "mouthPucker", "mc": "mouthClose",
              "pl": "mouthPressLeft", "pr": "mouthPressRight", "rl": "mouthRollLower",
              "sl": "mouthStretchLeft", "sr": "mouthStretchRight", "ml": "mouthSmileLeft",
              "mr": "mouthSmileRight", "fl": "mouthFrownLeft", "fr": "mouthFrownRight",
              "xl": "mouthLeft", "xr": "mouthRight"}

# Hair: clumps as (theta0, theta1, f0, f1, (root lift, mid bump, tip lift), width). theta runs over the top of
# the head from the character's right (-90) to the left (+90); f runs front (-1) to back (+1).
_BACK = [(0, 0.66, 0.006), (0, 0.86, 0.018), (0, 0.985, 0.016), (180, 0.93, 0.012), (180, 0.80, 0.003)]
_BACK_CLOSE = [(0, 0.66, 0.004), (0, 0.86, 0.008), (0, 0.985, 0.007), (180, 0.93, 0.005), (180, 0.80, 0.002)]
HAIR = {
    # The owner's hair: thick, black and textured, a heavy choppy fringe falling to the brows, volume on top, full
    # sides over the tops of the ears. Clumps run from the crown forward; tips land just above the brow line.
    # A soft fringe swept gently to his left: big rounded locks, smooth-shaded, tips resting above the brows.
    "soft_fringe": {"cap": 0.006, "band": 0.036, "thick": 0.40, "smooth": True, "ease": 0.55,
                    "hairline": [(0, 26), (30, 23), (52, 15), (68, 4), (79, -3), (88, 10), (100, 10), (112, -14),
                                 (180, -27)], "clumps": [
        (-34, -16, 0.30, -0.955, (0.010, 0.016, 0.008), 0.060),
        (-14, 8, 0.32, -0.968, (0.010, 0.017, 0.007), 0.064),
        (4, 28, 0.30, -0.962, (0.010, 0.017, 0.007), 0.062),
        (20, 50, 0.24, -0.93, (0.010, 0.016, 0.009), 0.058),
        (-50, -46, 0.20, -0.86, (0.010, 0.014, 0.009), 0.054),
        (-22, 10, 0.72, 0.00, (0.010, 0.016, 0.012), 0.066),  # top
        (24, 2, 0.72, 0.06, (0.010, 0.015, 0.012), 0.066),
        (-56, -96, -0.45, -0.36, (0.006, 0.012, 0.004), 0.050),  # sides: soft and close
        (-58, -100, -0.02, 0.04, (0.006, 0.012, 0.004), 0.052),
        (56, 96, -0.45, -0.36, (0.006, 0.012, 0.004), 0.050),
        (58, 100, -0.02, 0.04, (0.006, 0.012, 0.004), 0.052),
        (-40, -126, 0.62, 0.70, (0.006, 0.014, 0.004), 0.052),  # back
        (40, 126, 0.62, 0.70, (0.006, 0.014, 0.004), 0.052),
        _BACK_CLOSE,
    ]},
    # Curtains: a soft middle part, two rounded curtains framing an open forehead.
    "curtain": {"cap": 0.006, "band": 0.036, "thick": 0.40, "smooth": True, "ease": 0.55,
                "hairline": [(0, 30), (30, 24), (52, 15), (68, 4), (79, -3), (88, 10), (100, 10), (112, -14),
                             (180, -27)], "clumps": [
        (4, 26, 0.32, -0.962, (0.010, 0.017, 0.007), 0.052),
        (6, 50, 0.26, -0.945, (0.010, 0.017, 0.008), 0.056),
        (8, 74, 0.16, -0.86, (0.010, 0.015, 0.009), 0.056),
        (-4, -26, 0.32, -0.962, (0.010, 0.017, 0.007), 0.052),
        (-6, -50, 0.26, -0.945, (0.010, 0.017, 0.008), 0.056),
        (-8, -74, 0.16, -0.86, (0.010, 0.015, 0.009), 0.056),
        (-12, -4, 0.76, -0.20, (0.010, 0.015, 0.011), 0.054),  # top, either side of the part
        (12, 4, 0.76, -0.20, (0.010, 0.015, 0.011), 0.054),
        (-56, -96, -0.45, -0.36, (0.006, 0.012, 0.004), 0.050),  # sides: soft and close
        (-58, -100, -0.02, 0.04, (0.006, 0.012, 0.004), 0.052),
        (56, 96, -0.45, -0.36, (0.006, 0.012, 0.004), 0.050),
        (58, 100, -0.02, 0.04, (0.006, 0.012, 0.004), 0.052),
        (-40, -126, 0.62, 0.70, (0.006, 0.014, 0.004), 0.052),  # back
        (40, 126, 0.62, 0.70, (0.006, 0.014, 0.004), 0.052),
        _BACK_CLOSE,
    ]},
    "fringe": {"cap": 0.006, "band": 0.036, "thick": 0.34, "hairline": [(0, 22), (30, 20), (52, 14), (68, 4), (79, -3), (88, 10),
                                                         (100, 10), (112, -14), (180, -27)], "clumps": [
        (-6, -48, 0.22, -0.90, (0.010, 0.020, 0.010), 0.050),  # fringe: pieces of uneven width, tips turned apart
        (-3, -27, 0.26, -0.945, (0.012, 0.022, 0.008), 0.046),
        (0, -9, 0.30, -0.955, (0.012, 0.023, 0.007), 0.052),
        (3, 9, 0.30, -0.94, (0.012, 0.023, 0.008), 0.044),
        (6, 25, 0.26, -0.955, (0.012, 0.022, 0.007), 0.050),
        (9, 43, 0.22, -0.92, (0.010, 0.020, 0.010), 0.046),
        (12, 60, 0.16, -0.85, (0.010, 0.017, 0.010), 0.044),
        (-16, -63, 0.10, -0.84, (0.010, 0.016, 0.010), 0.044),
        (-20, -36, -0.50, -0.935, (0.024, 0.015, 0.011), 0.034),  # a short top layer: choppy, not combed
        (-4, -16, -0.46, -0.965, (0.026, 0.016, 0.010), 0.032),
        (12, 30, -0.48, -0.93, (0.024, 0.015, 0.011), 0.034),
        (28, 52, -0.40, -0.88, (0.022, 0.014, 0.011), 0.030),
        (-22, 18, 0.62, 0.02, (0.014, 0.021, 0.013), 0.050),  # volume on top
        (20, -14, 0.64, 0.06, (0.014, 0.020, 0.013), 0.050),
        (-46, 34, 0.50, -0.30, (0.012, 0.018, 0.014), 0.048),
        (-54, -96, -0.48, -0.40, (0.006, 0.006, 0.003), 0.038),  # sides: full but close, the ears show
        (-54, -98, -0.16, -0.10, (0.006, 0.006, 0.003), 0.040),
        (-56, -100, 0.18, 0.22, (0.006, 0.006, 0.003), 0.040),
        (54, 96, -0.48, -0.40, (0.006, 0.006, 0.003), 0.038),
        (54, 98, -0.16, -0.10, (0.006, 0.006, 0.003), 0.040),
        (56, 100, 0.18, 0.22, (0.006, 0.006, 0.003), 0.040),
        (-40, -126, 0.62, 0.70, (0.006, 0.008, 0.003), 0.040),  # back
        (40, 126, 0.62, 0.70, (0.006, 0.008, 0.003), 0.040),
        _BACK_CLOSE,  # close at the crown: no bun at the back
    ]},
    "swept": {"cap": 0.006, "band": 0.050, "clumps": [
        (-42, 64, -0.80, -0.70, (0.004, 0.040, 0.006), 0.034),  # fringe, lifted off the forehead
        (-40, 76, -0.60, -0.52, (0.006, 0.044, 0.004), 0.037),
        (-38, 86, -0.36, -0.28, (0.006, 0.038, 0.004), 0.039),
        (-38, 92, -0.10, -0.04, (0.006, 0.032, 0.004), 0.039),
        (-38, 98, 0.18, 0.22, (0.006, 0.027, 0.004), 0.039),
        (-40, 104, 0.46, 0.48, (0.006, 0.022, 0.004), 0.037),
        (-46, -96, -0.56, -0.44, (0.004, 0.010, 0.002), 0.030),  # the short side of the part
        (-46, -102, -0.18, -0.10, (0.004, 0.010, 0.002), 0.033),
        (-46, -108, 0.22, 0.26, (0.004, 0.010, 0.002), 0.033),
        (-50, -128, 0.72, 0.62, (0.004, 0.012, 0.002), 0.035),  # back
        (44, 128, 0.72, 0.62, (0.004, 0.014, 0.002), 0.035),
        _BACK,
    ]},
    "curly_top": {"cap": 0.006, "band": 0.075, "curls": [(t, f) for f in (-0.72, -0.38, 0.0, 0.38, 0.7) for t in (-42, -14, 14, 42)
                                           if not (f == 0.7 and abs(t) > 20)]},
    "buzz": {"cap": 0.0045, "band": 0.012, "clumps": []},
}
# Hairline: (|azimuth| from the front in degrees, elevation of the hair's lower edge).
HAIRLINE = [(0, 40), (35, 38), (55, 27), (70, 6), (79, -2), (88, 13), (100, 13), (112, -14), (180, -27)]


# ============================================================================================================
# Everything below runs inside Blender.
# ============================================================================================================
def wfac(low):
    """Width of the head at a depth `low` (0 at the midline, 1 at the chin) relative to RX."""
    jaw = np.clip((low - 0.45) / 0.55, 0.0, 1.0) ** 1.6  # the sides stay straight, then turn in at the jaw
    return 1 + JAW * np.sin(np.pi * low) - TAPER * jaw


def head_map(n):
    """Unit directions (N, 3) -> points on the head, head-centred."""
    low = np.clip(-n[:, 2], 0.0, 1.0)
    a, b = np.abs(n[:, 0]), np.abs(n[:, 2])  # the lower half's silhouette leans toward a rounded square:
    g = np.sqrt(a * a + b * b) / np.maximum((a ** SQUARE + b ** SQUARE) ** (1 / SQUARE), 1e-6)  # straight cheeks,
    g = 1 + (g - 1) * np.clip(low * 2.0, 0.0, 1.0)  # defined jaw corners; the cranium stays round
    return np.stack([RX * n[:, 0] * wfac(low) * g, RY * n[:, 1],
                     np.where(n[:, 2] >= 0, RZT * n[:, 2], -RZB * low ** CHIN * g)], 1)


def surf_y(x, z):
    """Front surface of the head at (x, z), head-centred."""
    x, z = np.asarray(x, float), np.asarray(z, float)
    nz = np.where(z >= 0, z / RZT, -(np.clip(-z, 0.0, RZB) / RZB) ** (1 / CHIN))
    low = np.clip(-nz, 0.0, 1.0)
    nx = x / (RX * wfac(low))
    return -RY * np.sqrt(np.clip(1 - nx * nx - nz * nz, 1e-5, 1.0))


def on_face(x, z, out=0.0):
    """Point on the face at (x, z) pushed `out` along the normal, and the rotation that turns -Y to the normal."""
    e = 1e-4
    y = float(surf_y(x, z))
    nrm = Vector((float(surf_y(x + e, z) - surf_y(x - e, z)) / (2 * e), -1.0,
                  float(surf_y(x, z + e) - surf_y(x, z - e)) / (2 * e))).normalized()
    return Vector((x, y, z)) + nrm * out, nrm.to_track_quat("-Y", "Z").to_euler()


def hdir(theta, f):
    t, c = math.radians(theta), math.sqrt(max(0.0, 1 - f * f))
    return Vector((math.sin(t) * c, f, math.cos(t) * c))


def hpt(d, lift=0.0):
    return Vector(head_map(np.array([d[:]]))[0]) + Vector(d) * lift


def palette(color):
    """Body, shadow-side, trim and highlight shades of the jacket. Brand purple uses the brand's own tokens."""
    from .geo import mix_hex
    if color.upper() == BRAND["purple"]:
        return BRAND["purple"], BRAND["purple_mid"], BRAND["purple_soft"], BRAND["lilac"]
    return color, mix_hex(color, "#000000", 0.14), mix_hex(color, "#FFFFFF", 0.42), mix_hex(color, "#FFFFFF", 0.75)


def build(**dials):
    """Build the hero into a new collection CHAR_base of the current scene. Unknown dials are an error."""
    from . import geo
    from .geo import ball, drive, empty, lin, loft, mat, mesh, mix_hex, rbox, soften, tube
    from reelforge.arkit import ARKIT_NAMES

    bad = set(dials) - set(DEFAULTS)
    if bad:
        raise ValueError(f"unknown hero dials {sorted(bad)}; known: {sorted(DEFAULTS)}")
    D = {**DEFAULTS, **dials}
    for key in ("outfit", "hair", "glasses", "headphones", "skin", "beard"):
        if D[key] not in HERO[key]["options"]:
            raise ValueError(f"{key} must be one of {HERO[key]['options']}, got {D[key]!r}")
    OF = OUTFITS[D["outfit"]]
    stubble = min(1.0, max(0.0, float(D["stubble"])))
    skin_hex = SKINS[D["skin"]]
    c_body, c_mid, c_soft, c_lilac = palette(D["outfit_color"])

    coll = bpy.data.collections.new("CHAR_base")
    bpy.context.scene.collection.children.link(coll)

    # --- materials --------------------------------------------------------------------------------------
    def skin_material(name, masked):
        m = mat(name, skin_hex, rough=0.52, sss=0.22)
        m.node_tree.nodes["Principled BSDF"].inputs["Subsurface Scale"].default_value = 0.012
        if not masked:
            return m
        nt = m.node_tree
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = "Mask"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(attr.outputs["Color"], sep.inputs["Color"])
        prev = None
        for chan, col, amount in (("Red", mix_hex(skin_hex, "#D4483F", 0.55), 0.55),
                                  ("Green", mix_hex(skin_hex, D["hair_color"], 0.85), min(1.0, 0.6 + stubble))):
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = amount
            nt.links.new(sep.outputs[chan], mul.inputs[0])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.inputs[6].default_value = (*lin(skin_hex), 1.0)
            mix.inputs[7].default_value = (*lin(col), 1.0)
            nt.links.new(mul.outputs[0], mix.inputs[0])
            if prev is not None:
                nt.links.new(prev.outputs[2], mix.inputs[6])
            prev = mix
        nt.links.new(prev.outputs[2], nt.nodes["Principled BSDF"].inputs["Base Color"])
        return m

    M = {
        "skin": skin_material("AV_Skin", True),
        "skin_plain": skin_material("AV_SkinPlain", False),
        "blush": mat("AV_SkinBlush", mix_hex(skin_hex, "#D4483F", 0.28), rough=0.52, sss=0.22),
        "eye": mat("AV_Eye", "#0B0B0E", rough=0.12, coat=0.6),
        "glint": mat("AV_EyeGlint", "#FFFFFF", rough=0.3, emit=1.6),
        "brow": mat("AV_Brow", D["hair_color"], rough=0.75),
        "hair": mat("AV_Hair", D["hair_color"], rough=0.72, sheen=0.04),
        "mouth": mat("AV_MouthIn", "#4A1C1A", rough=0.8),  # dark warm, never pure black
        "teeth": mat("AV_Teeth", "#F1ECE2", rough=0.35),
        "tongue": mat("AV_Tongue", "#C4605C", rough=0.5),
        "jacket": mat("AV_Jacket", c_body, rough=0.6, sheen=0.06),  # matte nylon; more sheen washes purple to lilac
        "jacket_mid": mat("AV_JacketMid", c_mid, rough=0.78),  # seams, cuffs, hem: the roughness break
        "trim": mat("AV_JacketTrim", c_soft, rough=0.45, sheen=0.2),
        "lilac": mat("AV_Lilac", c_lilac, rough=0.4),
        "tee": mat("AV_Tee", BRAND[OF["tee"]], rough=0.85),
        "ink": mat("AV_Ink", BRAND["ink"], rough=0.8),
        "metal": mat("AV_Frame", "#26262C", rough=0.3, metal=0.8),
        "phones": mat("AV_Phones", "#8E9099", rough=0.45),
        "phones_dark": mat("AV_PhonesPad", "#3A3B42", rough=0.7),
    }
    lens = bpy.data.materials.new("AV_Lens")
    lens.use_nodes = True
    nt = lens.node_tree
    nt.nodes.clear()
    out, mixs = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeMixShader")
    tr, gl = nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.06
    fres = nt.nodes.new("ShaderNodeFresnel")  # reflects only at grazing angles: a glint that never hides the eyes
    fres.inputs["IOR"].default_value = 1.12
    nt.links.new(fres.outputs[0], mixs.inputs[0])
    nt.links.new(tr.outputs[0], mixs.inputs[1])
    nt.links.new(gl.outputs[0], mixs.inputs[2])
    nt.links.new(mixs.outputs[0], out.inputs["Surface"])
    if hasattr(lens, "surface_render_method"):
        lens.surface_render_method = "BLENDED"
    M["lens"] = lens

    # --- rig empties ----------------------------------------------------------------------------------
    root = empty("CHAR_root", (0, 0, 0), coll)
    body = empty("Body", BODY_AT, coll, root)
    spine = empty("Spine", (0, 0, 0), coll, body)
    b_at = Vector(BODY_AT)
    head = empty("Head", Vector((0, 0, NECK_Z)) - b_at, coll, spine)
    hgeo = empty("HeadGeo", (0, 0, HC_Z - NECK_Z), coll, head)
    ctrl = empty("FaceCtrl", (0, 0, 0.45), coll, hgeo)
    for n in ARKIT_NAMES:
        ctrl[n] = 0.0
    pose = empty("PoseCtrl", (0, 0, 0.55), coll, hgeo)
    pose["HandL"], pose["HandR"], pose["Lean"] = 0.0, 0.0, 0.0
    drive(spine, "rotation_euler", "0.2*lean", {"lean": (pose, "Lean")}, 0)
    fa = empty("FaceAnchor", (0, -RY + 0.01, 0.0), coll, hgeo)
    fa["head_height"] = RZT + RZB
    empty("EyeFocus", (0, float(surf_y(0, EYE_Z)), EYE_Z), coll, hgeo)

    def face(vars_):  # driver variables read from FaceCtrl
        return {k: (ctrl, v) for k, v in vars_.items()}

    def on_spine(o):  # the object was authored in root space
        o.parent = spine
        o.location = Vector(o.location) - b_at
        return o

    # --- head: cube-sphere, a real mouth slit with an inner lip wall, shape keys --------------------------
    cell = 2.0 / (HEAD_CUTS + 1)
    v_lo, v_hi = -1 + MOUTH_ROW * cell, -1 + (MOUTH_ROW + 1) * cell
    v_mid, u_w = (v_lo + v_hi) / 2, MOUTH_COLS * cell + 1e-4
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=HEAD_CUTS, use_grid_fill=True)
    l_side, l_rim = bm.verts.layers.float.new("side"), bm.verts.layers.float.new("rim")
    for v in bm.verts:
        v[l_side] = (1.0 if v.co.z > v_mid else -1.0) if v.co.y < -1 + 1e-5 else 0.0
    slit = [f for f in bm.faces if all(v.co.y < -1 + 1e-5 for v in f.verts)
            and v_lo < f.calc_center_median().z < v_hi and abs(f.calc_center_median().x) < u_w]
    assert len(slit) == 2 * MOUTH_COLS, len(slit)
    for f in slit:
        for v in f.verts:
            v[l_rim] = 1.0
    bmesh.ops.delete(bm, geom=slit, context="FACES")
    bm.verts.ensure_lookup_table()

    def unit(p):
        p = np.asarray(p, float).reshape(-1, 3)
        return p / np.linalg.norm(p, axis=1)[:, None]

    P = head_map(unit([v.co[:] for v in bm.verts]))
    side = np.array([v[l_side] for v in bm.verts])
    rim = np.array([v[l_rim] for v in bm.verts]) > 0.5
    zm = float(head_map(unit((0, -1, v_mid)))[0, 2])
    half = float(head_map(unit((0, -1, v_hi)))[0, 2] - head_map(unit((0, -1, v_lo)))[0, 2]) / 2
    side = np.where(side == 0, np.where(P[:, 2] > zm, 1.0, -1.0), side)
    w0 = float(np.abs(P[rim, 0]).max())
    fall = np.exp(-(np.maximum(0, np.abs(P[:, 2] - zm) - half) / 0.006) ** 2
                  - (np.maximum(0, np.abs(P[:, 0]) - w0) / 0.006) ** 2) * (P[:, 1] < 0)
    new_z = P[:, 2] - side * (half - GAP / 2) * fall  # close the slit to a thin line
    new_z[rim] = zm + side[rim] * GAP / 2
    P[:, 1] += surf_y(P[:, 0], new_z) - surf_y(P[:, 0], P[:, 2])
    P[:, 2] = new_z
    for v, p in zip(bm.verts, P):
        v.co = p
    wall = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
    for g in wall["geom"]:
        if isinstance(g, bmesh.types.BMVert):
            g.co.y += LIP_DEPTH  # the lip's inner wall, so the mouth reads as inset
            g.co.x *= 0.96
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("AV_Head")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(M["skin"])
    hd = bpy.data.objects.new("AV_Head", me)
    coll.objects.link(hd)
    hd.parent = hgeo
    P0 = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", P0)
    P0 = P0.reshape(-1, 3)
    side = np.where(P0[:, 2] > zm, 1.0, -1.0)  # after closing, every vertex is on its own side of the line
    xr, zr = P0[:, 0], P0[:, 2] - zm
    t = np.clip(xr / w0, -1.0, 1.0)

    def mouth_key(a=1.0, hu=0.0, hl=0.0, n=2.5, lift=0.0, fwd=0.0, fwd_low=0.0, shift=0.0,
                  a_l=None, a_r=None, lift_l=None, lift_r=None):
        a_arr = np.where(xr > 0, a if a_l is None else a_l, a if a_r is None else a_r) * w0  # per corner
        lift_arr = np.where(xr > 0, lift if lift_l is None else lift_l, lift if lift_r is None else lift_r)
        prof = (1 - np.abs(t) ** n) ** (1 / n)
        travel = np.where(side > 0, hu, -hl)
        sig = 0.007 + 0.8 * np.abs(travel) + 0.5 * np.abs(lift_arr)
        f = np.exp(-(np.abs(zr) / sig) ** 2
                   - (np.maximum(0, np.abs(xr) - w0) / (0.008 + 0.6 * np.abs(a_arr - w0))) ** 2) * (P0[:, 1] < 0.02)
        dx = (t * (a_arr - w0) + shift) * f
        dz = (travel * prof + lift_arr * t * t) * f
        out_y = fwd + np.where(side < 0, fwd_low, 0.0)
        Q = P0.copy()
        Q[:, 0] += dx
        Q[:, 2] += dz
        Q[:, 1] += surf_y(xr + dx, P0[:, 2] + dz) - surf_y(xr, P0[:, 2]) - out_y * f
        return Q

    if SMILE_REST:  # his resting face: the closed smile at SMILE_REST, baked into the basis
        sm_spec = MOUTH["smile"]
        P0 = mouth_key(a=1 + (sm_spec["a"] - 1) * SMILE_REST, lift=sm_spec["lift"] * SMILE_REST)
        me.vertices.foreach_set("co", P0.ravel())
        side = np.where(P0[:, 2] > zm, 1.0, -1.0)
        xr, zr = P0[:, 0], P0[:, 2] - zm
        t = np.clip(xr / w0, -1.0, 1.0)
    hd.shape_key_add(name="Basis")
    for name, spec in MOUTH.items():
        kb = hd.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", mouth_key(**spec).ravel())
        if name == "side":
            kb.slider_min = -1.0
        drive(kb, "value", MOUTH_DRIVERS[name], face(MOUTH_VARS))

    # blush (red) and stubble (green) masks, painted per vertex so they move with the face
    x, y, z = P0[:, 0], P0[:, 1], P0[:, 2]
    blush = np.exp(-(((np.abs(x) - 0.090) / 0.030) ** 2 + ((z + 0.066) / 0.026) ** 2)) * (y < 0)
    sm = lambda e0, e1, v: np.clip((v - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((v - e0) / (e1 - e0), 0, 1))  # noqa: E731
    band = sm(-0.058, -0.088, z) * sm(0.085, 0.015, y)  # the jaw-and-chin stubble band
    band *= 1 - 0.85 * np.exp(-((x / (w0 * 1.25)) ** 2 + ((z - zm) / 0.010) ** 2))  # lips stay clean
    front = (y < 0).astype(float)
    tache = (np.exp(-((z - (zm + 0.0090 - 0.006 * (x / w0) ** 2)) / 0.0042) ** 2)  # thin, drooping at the corners
             * np.exp(-np.maximum(0, np.abs(x) - 1.12 * w0) ** 2 / 0.003 ** 2)
             * (1 - 0.45 * np.exp(-(x / 0.005) ** 2)) * front)  # lighter at the philtrum
    chin = np.exp(-(x / 0.021) ** 2) * sm(zm - 0.009, zm - 0.022, z) * front  # the chin beard, below the lower lip
    stub = {"light": np.maximum(np.maximum(tache, chin), 0.10 * band), "stubble": band,  # jaw shadow kept faint: more reads as grime under coloured light
            "none": np.zeros_like(band)}[D["beard"]]
    mask = np.stack([blush, stub, np.zeros_like(x), np.ones_like(x)], 1)
    me.color_attributes.new("Mask", "FLOAT_COLOR", "POINT").data.foreach_set("color", mask.ravel())
    sub = hd.modifiers.new("Subd", "SUBSURF")
    sub.levels = sub.render_levels = 1

    # mouth interior: dark warm cavity, upper teeth, a tongue that drops with the jaw
    my = float(surf_y(0, zm))
    # The cavity is a dish that follows the face 11-21 mm behind the skin, so it stays inside the chin, which
    # curves back faster than any sphere would.
    xw, z_lo, z_hi = w0 * 1.75, zm - 0.034, zm + 0.014
    gx_, gz_ = np.linspace(-xw, xw, 13), np.linspace(z_lo, z_hi, 9)
    dish = []
    for zz in gz_:
        for xx in gx_:
            bow = (1 - (xx / xw) ** 2) * (1 - ((zz - (z_lo + z_hi) / 2) / ((z_hi - z_lo) / 2)) ** 2)
            dish.append((xx, float(surf_y(xx, zz)) + 0.011 + 0.010 * bow, zz))
    nx_ = len(gx_)
    mesh("AV_MouthIn", dish, [(r * nx_ + c, r * nx_ + c + 1, (r + 1) * nx_ + c + 1, (r + 1) * nx_ + c)
                              for r in range(len(gz_) - 1) for c in range(nx_ - 1)], coll, M["mouth"], smooth=True,
         parent=hgeo)
    rbox("AV_Teeth", (0.036, 0.004, 0.008), coll, M["teeth"], 0.0015, (0, my + 0.0048, zm + 0.0052), parent=hgeo)
    tz = zm - 0.008
    ty = float(surf_y(0, tz)) + 0.016
    tongue = ball("AV_Tongue", (0.014, 0.007, 0.0045), coll, M["tongue"], (0, ty, tz), parent=hgeo)
    drive(tongue, "location", f"{tz:.5f}-0.010*clamp(j)", face({"j": "jawOpen"}), 2)
    drive(tongue, "location", f"{ty:.5f}+0.004*clamp(j)", face({"j": "jawOpen"}), 1)

    # nose: one small wedge
    np_, nrot = on_face(0, -0.060, -0.002)
    nose = soften(mesh("AV_Nose", [(0, 0, 0.016), (-0.0095, 0, -0.009), (0.0095, 0, -0.009), (0, -0.016, -0.007)],
                       [(0, 1, 3), (0, 3, 2), (1, 2, 3), (0, 2, 1)], coll, M["blush"], smooth=True, parent=hgeo),
                  0.0025, 2)
    nose.location, nose.rotation_euler = np_, nrot
    drive(nose, "scale", "1+0.12*max(a,b)", face({"a": "noseSneerLeft", "b": "noseSneerRight"}), 2)

    for sname, sx in (("Left", 1), ("Right", -1)):
        tag = sname[0]
        # eyes: black ovals with one fixed highlight; upper and lower lids slide over them
        ep, erot = on_face(sx * EYE_X, EYE_Z, -0.0008)
        piv = empty(f"Eye{tag}", ep, coll, hgeo)
        piv.rotation_euler = erot
        eye = ball(f"AV_Eye{tag}", EYE_R, coll, M["eye"], parent=piv, segs=24)
        ball(f"AV_EyeGlint{tag}", (0.27, 0.42, 0.17), coll, M["glint"], (0.30, -0.86, 0.38), parent=eye, segs=12)
        ball(f"AV_EyeGlint2{tag}", (0.11, 0.42, 0.07), coll, M["glint"], (-0.30, -0.88, -0.42), parent=eye, segs=10)
        ev = face({"w": f"eyeWide{sname}", "o": f"eyeLookOut{sname}", "i": f"eyeLookIn{sname}",
                   "u": f"eyeLookUp{sname}", "d": f"eyeLookDown{sname}"})
        drive(eye, "location", f"{sx}*0.006*(o-i)", ev, 0)
        drive(eye, "location", "0.005*(u-d)", ev, 2)
        drive(eye, "scale", f"{EYE_R[0]}*(1+0.10*w)", ev, 0)
        drive(eye, "scale", f"{EYE_R[2]}*(1+0.16*w)", ev, 2)
        lv = face({"b": f"eyeBlink{sname}", "s": f"eyeSquint{sname}", "c": f"cheekSquint{sname}",
                   "w": f"eyeWide{sname}"})
        for lname, sign, expr in (("Up", 1, "max(0.02,clamp(0.90*b+0.30*s-0.2*w))"),
                                  ("Low", -1, "max(0.02,clamp(0.16*b+0.42*s+0.34*c))")):
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
            bmesh.ops.translate(bm, vec=(0, 0, -sign), verts=bm.verts)  # hinge at the lid's outer edge
            lme = bpy.data.meshes.new(f"AV_Lid{lname}{tag}")
            bm.to_mesh(lme)
            bm.free()
            for p in lme.polygons:
                p.use_smooth = True
            lme.materials.append(M["skin_plain"])
            lid = bpy.data.objects.new(lme.name, lme)
            coll.objects.link(lid)
            lid.parent = piv
            lid.location = (0, 0, sign * (EYE_R[2] + 0.003))
            lid.scale = (EYE_R[0] * 1.32, EYE_R[1] * 1.45, 0.0004)
            drive(lid, "scale", f"{EYE_R[2] + 0.003:.5f}*({expr})", lv, 2)
        # brows: short dark bars that raise, lower, angle and pinch. They carry most of the emotion.
        bp, brot = on_face(sx * (EYE_X + 0.002), BROW_Z, 0.0005)
        bpiv = empty(f"Brow{tag}", bp, coll, hgeo)
        bpiv.rotation_euler = brot
        brow = rbox(f"AV_Brow{tag}", (0.046, 0.009, 0.0115), coll, M["brow"], 0.0045, parent=bpiv)
        bv = face({"u": "browInnerUp", "d": f"browDown{sname}", "o": f"browOuterUp{sname}"})
        drive(brow, "location", f"{-sx}*0.004*d", bv, 0)
        drive(brow, "location", "0.010*u+0.013*o-0.008*d", bv, 2)
        drive(brow, "rotation_euler", f"{sx}*(0.035+0.42*u-0.46*d-0.16*o)", bv, 1)  # inner ends a touch high: earnest
        # ears
        ear = ball(f"AV_Ear{tag}", (0.011, 0.022, 0.030), coll, M["blush"], (sx * (RX - 0.002), 0.012, -0.022),
                   parent=hgeo, segs=16)
        ear.rotation_euler = (0, 0, sx * 0.25)

    # --- hair: faceted clumps over a thin cap ----------------------------------------------------------
    preset = HAIR[D["hair"]]

    def hairline(az):
        a = abs((az + 180) % 360 - 180)
        line = preset.get("hairline", HAIRLINE)
        return float(np.interp(a, [h[0] for h in line], [h[1] for h in line]))

    cols, rows = 44, 10  # dense enough that the flat facets never dip under the skin
    cap_v, cap_f = [], []
    for i in range(cols):
        az = 360.0 * i / cols
        lo = hairline(az)
        for r in range(rows):
            el = math.radians(lo + (88 - lo) * r / (rows - 1))
            a = math.radians(az)
            d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
            cap_v.append(hpt(d, preset["cap"] + 0.002))  # + the chord sag of one facet
    cap_v.append(hpt(Vector((0, 0, 1)), preset["cap"]))
    for i in range(cols):
        j = (i + 1) % cols
        for r in range(rows - 1):
            cap_f.append((i * rows + r, j * rows + r, j * rows + r + 1, i * rows + r + 1))
        cap_f.append((i * rows + rows - 1, j * rows + rows - 1, len(cap_v) - 1))
    soft = bool(preset.get("smooth"))  # soft presets: smooth, rounded locks instead of faceted clumps
    cap = mesh("AV_HairCap", cap_v, cap_f, coll, M["hair"], smooth=soft, parent=hgeo)
    sol = cap.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness, sol.offset = preset["cap"] + 0.004, -1.0

    def clump(name, path, width, k=8 if soft else 5):
        pts = [hpt(d, lift) for d, lift in path]
        rings = []
        for i, (d, _) in enumerate(path):
            s = i / (len(path) - 1)
            prof = [0.6, 0.95, 1.0, 0.92, 0.38] if soft else [0.55, 0.9, 1.0, 0.62, 0.07]  # soft locks: rounded tips
            w = width * float(np.interp(s, [0, 0.15, 0.45, 0.8, 1], prof))
            th = preset.get("thick", 0.44) * w  # flatter clumps keep a short cut close to the head
            _, sd, up = geo.frame(pts, i, d)
            c = pts[i] + up * th * 0.3
            rings.append([c + sd * (w * math.cos(2 * math.pi * j / k + math.pi / 2))
                          + up * (th * math.sin(2 * math.pi * j / k + math.pi / 2)) for j in range(k)])
        o = loft(name, rings, coll, M["hair"], smooth=soft, parent=hgeo)
        if soft:
            sub = o.modifiers.new("Subd", "SUBSURF")
            sub.levels = sub.render_levels = 1
        return o

    for ci, spec in enumerate(preset.get("clumps", [])):
        if isinstance(spec, list):
            path = [(hdir(th, f), lift) for th, f, lift in spec]
        else:
            th0, th1, f0, f1, (l0, lm, l1), width = spec
            wob = (0.012 if D["hair"] == "fringe" else 0.004) * math.sin(ci * 12.9898)  # irregular, same every build
            ease = preset.get("ease", 1.0)  # < 1: the lock crosses the crown fast, then hangs down the forehead
            path = [(hdir(th0 + (th1 - th0) * s, f0 + (f1 - f0) * s ** ease + wob * math.sin(math.pi * s)),
                     l0 + (l1 - l0) * s + lm * math.sin(math.pi * s) ** 0.8) for s in (i / 9 for i in range(10))]
        clump(f"AV_Hair{ci:02d}", path, spec[5] if not isinstance(spec, list) else 0.036)
    for ci, (th, f) in enumerate(preset.get("curls", [])):
        r = 0.050 + 0.008 * math.sin(ci * 7.3)
        curl = ball(f"AV_Curl{ci:02d}", (r, r, r * 0.86), coll, M["hair"], hpt(hdir(th + 5 * math.sin(ci * 3.1), f), 0.018),
                    parent=hgeo, ico=1, smooth=False)
        curl.rotation_euler = (ci * 0.9, ci * 1.7, ci * 0.5)

    # --- glasses: bold acetate (default) or a thin wire rim, with a faint lens ----------------------------
    if D["glasses"] == "bold":
        gx, gz = EYE_X + 0.002, EYE_Z + 0.002
        gy = float(surf_y(gx, gz)) - 0.019
        acetate = mat("AV_Acetate", "#0E0D0F", rough=0.22, coat=0.6)
        ao, bo, band_w, n_r = 0.054, 0.040, 0.0068, 4.2  # each lens: outer half-width/height, rim band, squareness

        def sup_ring(a_, b_, centre, rot, n=48, droop=0.0):
            pts = []
            for i in range(n):
                t = 2 * math.pi * i / n
                c, s_ = math.cos(t), math.sin(t)
                x_ = a_ * math.copysign(abs(c) ** (2 / n_r), c)
                z_ = b_ * math.copysign(abs(s_) ** (2 / n_r), s_)
                if z_ < 0:  # the lower edge curves a little, like real frames
                    z_ -= droop * (1 - (x_ / a_) ** 2)
                pts.append(centre + rot @ Vector((x_, 0, z_)))
            return pts

        for sx in (1, -1):
            rot = Matrix.Rotation(sx * math.radians(12), 4, "Z")
            centre = Vector((sx * gx, gy, gz))
            outer = sup_ring(ao, bo, centre, rot, droop=0.004)
            inner = sup_ring(ao - band_w, bo - band_w * 1.05, centre, rot, droop=0.004)
            front = loft(f"AV_Frame{'L' if sx > 0 else 'R'}", [outer, inner], coll, acetate, closed=True,
                         caps=(False, False), smooth=True, parent=hgeo)
            so = front.modifiers.new("Solid", "SOLIDIFY")
            so.thickness, so.offset = 0.0055, 0.0
            soften(front, 0.0016, 2, 35)
            glass = mesh(f"AV_Lens{'L' if sx > 0 else 'R'}", [centre] + inner,
                         [(0, i + 1, (i + 1) % 48 + 1) for i in range(48)], coll, M["lens"], smooth=True, parent=hgeo)
            glass.visible_shadow = False
            hinge = centre + rot @ Vector((sx * (ao - 0.002), 0.003, bo - 0.012))
            tube(f"AV_Temple{'L' if sx > 0 else 'R'}",
                 [hinge, hinge + Vector((sx * 0.012, 0.010, 0.0)), Vector((sx * (RX + 0.006), -0.04, gz + 0.016)),
                  Vector((sx * (RX + 0.004), 0.03, gz + 0.010))], 0.0028, coll, acetate, k=8, parent=hgeo)
        inner_x = gx - ao * math.cos(math.radians(12))
        tube("AV_Bridge", [Vector((-inner_x - 0.002, gy - 0.002, gz + 0.012)), Vector((0, gy - 0.006, gz + 0.016)),
                           Vector((inner_x + 0.002, gy - 0.002, gz + 0.012))], 0.0034, coll, acetate, k=8,
             parent=hgeo)
    elif D["glasses"] != "none":
        gx, gz = EYE_X + 0.001, EYE_Z + 0.002
        gy = float(surf_y(gx, gz)) - 0.017
        a_r, b_r, n_r = (0.046, 0.046, 2.0) if D["glasses"] == "round" else (0.047, 0.034, 5.0)
        for sx in (1, -1):
            yaw = sx * math.radians(11)
            rot = Matrix.Rotation(yaw, 4, "Z")
            centre = Vector((sx * gx, gy, gz))
            ring = []
            for i in range(40):
                a = 2 * math.pi * i / 40
                c, s = math.cos(a), math.sin(a)
                ring.append(centre + rot @ Vector((a_r * math.copysign(abs(c) ** (2 / n_r), c), 0,
                                                   b_r * math.copysign(abs(s) ** (2 / n_r), s))))
            tube(f"AV_Rim{'L' if sx > 0 else 'R'}", ring, 0.0017, coll, M["metal"], k=6, closed=True, parent=hgeo,
                 up=(0, 1, 0))
            glass = mesh(f"AV_Lens{'L' if sx > 0 else 'R'}", [centre] + ring,
                         [(0, i + 1, (i + 1) % 40 + 1) for i in range(40)], coll, M["lens"], smooth=True, parent=hgeo)
            glass.visible_shadow = False
            hinge = centre + rot @ Vector((sx * a_r, 0, 0.004))
            tube(f"AV_Temple{'L' if sx > 0 else 'R'}",
                 [hinge, Vector((sx * (RX + 0.004), -0.06, gz + 0.006)), Vector((sx * (RX + 0.003), 0.02, gz + 0.004))],
                 0.0016, coll, M["metal"], k=6, parent=hgeo)
        inner = a_r * math.cos(math.radians(11))
        tube("AV_Bridge", [Vector((-(gx - inner) - 0.001, gy - 0.004, gz + 0.008)), Vector((0, gy - 0.008, gz + 0.013)),
                           Vector((gx - inner + 0.001, gy - 0.004, gz + 0.008))], 0.0017, coll, M["metal"], k=6,
             parent=hgeo)

    # --- torso: tee, jacket shell with panel seams, collar -----------------------------------------------
    PROFILE = [(0.60, 0.150, 0.108), (0.66, 0.164, 0.120), (0.78, 0.176, 0.126), (0.90, 0.174, 0.124),
               (0.955, 0.158, 0.114), (1.000, 0.118, 0.098), (1.030, 0.086, 0.084)]

    def half_axes(zz, grow=0.0):
        return (float(np.interp(zz, [p[0] for p in PROFILE], [p[1] for p in PROFILE])) + grow,
                float(np.interp(zz, [p[0] for p in PROFILE], [p[2] for p in PROFILE])) + grow)

    def sup(a, b, ang, zz, n=2.7):  # superellipse; ang = 0 is the front (-Y), pi/2 the character's left
        c, s = math.cos(ang), math.sin(ang)
        return Vector((a * math.copysign(abs(s) ** (2 / n), s), -b * math.copysign(abs(c) ** (2 / n), c) + 0.01, zz))

    def opening(zz, a):  # half-angle of the open front: a V that widens toward the collar
        hw = float(np.interp(zz, [0.60, 0.90, 1.03, 1.09], [0.030, 0.042, 0.058, 0.066]))
        return math.asin(min(0.95, (hw / a) ** (2.7 / 2)))

    def ring(zz, grow, k=22, arc=OF["open"]):
        a, b = half_axes(zz, grow)
        if not arc:
            return [sup(a, b, 2 * math.pi * j / k, zz) for j in range(k)]
        o = opening(zz, a)
        return [sup(a, b, o + (2 * math.pi - 2 * o) * j / (k - 1), zz) for j in range(k)]

    tee = on_spine(loft("AV_Tee", [ring(zz, -0.004, 24, False) for zz in (0.60, 0.70, 0.82, 0.92, 0.965, 1.005, 1.035)]
                        + [[Vector((0.062 * math.sin(2 * math.pi * j / 24), -0.058 * math.cos(2 * math.pi * j / 24) + 0.012,
                                    1.045)) for j in range(24)]], coll, M["tee"], smooth=True))
    on_spine(loft("AV_Neck", [[Vector((0.056 * math.sin(2 * math.pi * j / 16), -0.052 * math.cos(2 * math.pi * j / 16) + 0.012,
                                       zz)) for j in range(16)] for zz in (1.03, 1.075)], coll, M["skin_plain"], smooth=True))
    tee.modifiers.new("Subd", "SUBSURF").levels = 1

    zs, grooves = [], []
    if OF["bands"]:
        edges = np.linspace(0.615, 0.962, OF["bands"] + 1)
        for i in range(OF["bands"]):
            zs += [(float(edges[i]), -0.4), (float((edges[i] + edges[i + 1]) / 2), 1.0)]
        zs.append((float(edges[-1]), -0.4))
        grooves = [float(e) for e in edges[1:]]
    else:
        zs = [(zz, 0.0) for zz in (0.615, 0.70, 0.80, 0.90, 0.958)]
    zs += [(0.985, 0.4), (1.012, 0.2), (1.032, 0.0)]
    shell = on_spine(loft("AV_Jacket", [ring(zz, OF["shell"] + OF["puff"] * p) for zz, p in zs], coll, M["jacket"],
                          closed=not OF["open"], caps=(True, False), smooth=False))
    sol = shell.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness, sol.offset = 0.012 + OF["puff"], -1.0
    soften(shell, 0.003, 1, 24)
    for gi, gz_ in enumerate(grooves):  # stitched panel seams, as geometry
        on_spine(tube(f"AV_Seam{gi}", ring(gz_, OF["shell"] - 0.4 * OF["puff"] + 0.0025), 0.003, coll, M["jacket_mid"],
                      k=5, closed=not OF["open"], smooth=False))
    on_spine(tube("AV_Hem", ring(0.612, OF["shell"] + 0.004), 0.011, coll, M["jacket_mid"], k=6,
                  closed=not OF["open"], smooth=False))
    if OF["open"]:  # the zip band (or placket) down both front edges
        band_m = M["trim"] if D["outfit"] == "puffer" else M["jacket_mid"]
        for sx in (1, -1):
            strip = []
            for zz, p in zs:
                a, b = half_axes(zz, OF["shell"] + OF["puff"] * max(p, 0.0) + 0.004)
                o = opening(zz, a)
                strip.append([sup(a, b, sx * (o - 0.03), zz), sup(a, b, sx * (o + 0.115), zz)])
            band = on_spine(loft(f"AV_Zip{'L' if sx > 0 else 'R'}", strip, coll, band_m, closed=False, smooth=False))
            bs = band.modifiers.new("Solid", "SOLIDIFY")
            bs.thickness, bs.offset = 0.007, 1.0 if sx > 0 else -1.0
            soften(band, 0.002, 1, 24)
    if OF["collar"] == "stand":  # puffer: a padded stand collar hides the neck
        col = on_spine(loft("AV_Collar", [ring(1.022, 0.012), ring(1.052, 0.030), ring(1.082, 0.016)], coll, M["jacket"],
                            closed=False, smooth=False))
        cs = col.modifiers.new("Solid", "SOLIDIFY")
        cs.thickness, cs.offset = 0.02, -1.0
        soften(col, 0.003, 1, 24)
        on_spine(tube("AV_CollarSeam", ring(1.022, 0.016), 0.003, coll, M["jacket_mid"], k=5, smooth=False))
    elif OF["collar"] == "hood":  # hoodie: hood down behind the neck, a thick neck band, drawcords
        hood = on_spine(ball("AV_Hood", (0.135, 0.075, 0.072), coll, M["jacket"], (0, 0.118, 1.025), ico=2, smooth=False))
        hood.rotation_euler = (0.35, 0, 0)
        on_spine(tube("AV_NeckBand", ring(1.040, 0.020, 18, False), 0.021, coll, M["jacket"], k=6, closed=True,
                      smooth=False))
        for sx in (1, -1):
            on_spine(tube(f"AV_Cord{sx}", [Vector((sx * 0.034, -0.098, 1.03)), Vector((sx * 0.038, -0.128, 0.97)),
                                           Vector((sx * 0.036, -0.134, 0.885))], 0.0035, coll, M["trim"], k=6))
            on_spine(rbox(f"AV_CordTip{sx}", (0.010, 0.010, 0.022), coll, M["lilac"], 0.003, (sx * 0.036, -0.134, 0.875)))
        on_spine(rbox("AV_Pocket", (0.21, 0.016, 0.085), coll, M["jacket_mid"], 0.006, (0, -0.118, 0.725)))
    else:  # overshirt: two collar points, buttons, a chest pocket
        for sx in (1, -1):
            pts = [(sx * 0.050, -0.070, 1.062), (sx * 0.118, -0.020, 1.040), (sx * 0.098, -0.104, 0.985),
                   (sx * 0.052, -0.098, 1.010)]
            flap = on_spine(mesh(f"AV_CollarPt{sx}", pts, [(0, 1, 2, 3)], coll, M["jacket"], smooth=False))
            fs = flap.modifiers.new("Solid", "SOLIDIFY")
            fs.thickness = 0.008
            soften(flap, 0.002, 1, 24)
        on_spine(tube("AV_CollarBand", ring(1.040, 0.012), 0.012, coll, M["jacket"], k=6, smooth=False))
        for i in range(3):
            a, b = half_axes(0.93 - 0.075 * i, OF["shell"] + 0.004)
            o = opening(0.93 - 0.075 * i, a)
            on_spine(ball(f"AV_Button{i}", (0.006, 0.003, 0.006), coll, M["lilac"],
                          sup(a, b, o + 0.045, 0.93 - 0.075 * i) + Vector((0, -0.008, 0)), segs=12))
        on_spine(rbox("AV_ChestPocket", (0.058, 0.006, 0.052), coll, M["jacket_mid"], 0.003, (0.094, -0.124, 0.905)))
    if D["chest_mark"]:  # optional slash-and-dot mark in lilac, on the wearer's left chest
        slash = on_spine(rbox("AV_MarkSlash", (0.007, 0.004, 0.030), coll, M["lilac"], 0.002, (0.100, -0.131, 0.905)))
        slash.rotation_euler = (0.05, -0.45, -0.25)
        on_spine(ball("AV_MarkDot", (0.0045, 0.003, 0.0045), coll, M["lilac"], (0.116, -0.127, 0.894), segs=12))

    # --- headphones ------------------------------------------------------------------------------------
    if D["headphones"] == "neck":
        arc = [Vector((0.118 * math.sin(a), 0.118 * math.cos(a) * 0.95 + 0.02, 1.045 + 0.02 * math.cos(a)))
               for a in (math.radians(-118 + 236 * i / 12) for i in range(13))]
        on_spine(tube("AV_PhoneBand", arc, 0.008, coll, M["phones"], k=6))
        for sx in (1, -1):
            cup = on_spine(rbox(f"AV_PhoneCup{sx}", (0.030, 0.064, 0.070), coll, M["phones"], 0.010,
                                (sx * 0.108, -0.050, 1.030)))
            cup.rotation_euler = (0.25, 0, sx * 0.5)
            pad = on_spine(rbox(f"AV_PhonePad{sx}", (0.014, 0.056, 0.062), coll, M["phones_dark"], 0.006,
                                (sx * 0.095, -0.056, 1.030)))
            pad.rotation_euler = cup.rotation_euler
    elif D["headphones"] == "on":
        arc = [Vector(((RX + 0.020) * math.sin(a), 0.012, (RZT + preset["band"]) * math.cos(a)))
               for a in (math.radians(-90 + 180 * i / 14) for i in range(15))]
        tube("AV_PhoneBand", arc, 0.008, coll, M["phones"], k=6, parent=hgeo, up=(0, 1, 0))
        for sx in (1, -1):
            rbox(f"AV_PhoneCup{sx}", (0.034, 0.066, 0.078), coll, M["phones"], 0.011, (sx * (RX + 0.016), 0.012, -0.020),
                 parent=hgeo)
            rbox(f"AV_PhonePad{sx}", (0.012, 0.058, 0.068), coll, M["phones_dark"], 0.006, (sx * (RX + 0.001), 0.012, -0.020),
                 parent=hgeo)

    # --- arms and fingered hands: every pose is solved here and stored as driver tables -----------------
    def sleeve(name, length, r0, r1, bands, cuff):
        k, rings = 10, []

        def circ(yy, r):
            return [Vector((r * math.cos(2 * math.pi * j / k), yy, r * math.sin(2 * math.pi * j / k))) for j in range(k)]

        rings += [circ(0.62 * r0, 0.5 * r0), circ(0.32 * r0, 0.86 * r0)]
        body_len = length * (0.84 if cuff else 1.0)
        steps = max(2, bands * 2)
        for i in range(steps + 1):
            s = i / steps
            puff = (OF["puff"] * 0.8 if i % 2 else -OF["puff"] * 0.3) if bands else 0.0
            rings.append(circ(-s * body_len, r0 + (r1 - r0) * s + puff))
        if not cuff:
            rings.append(circ(-length - 0.4 * r1, 0.55 * r1))
        o = loft(name, rings, coll, M["jacket"], smooth=False)
        soften(o, 0.003, 1, 24)
        extra = []
        if bands:
            for i in range(2, steps, 2):
                s = i / steps
                extra.append(tube(f"{name}Seam{i}", circ(-s * body_len, r0 + (r1 - r0) * s - OF["puff"] * 0.3 + 0.002),
                                  0.003, coll, M["jacket_mid"], k=5, closed=True, smooth=False, up=(0, 1, 0)))
        if cuff:
            c = loft(f"{name}Cuff", [circ(-length * 0.82, r1 * 1.04), circ(-length * 0.9, r1 * 1.08),
                                     circ(-length, r1 * 1.0)], coll, M["jacket_mid"], smooth=False)
            extra.append(soften(c, 0.003, 1, 24))
        for e in extra:
            e.parent = o
        return o

    def pose_expr(values):  # piecewise-linear over the pose index, inside the simple-expression subset
        terms = [f"{v:.4f}*max(0,1-abs(s-{k}))" for k, v in enumerate(values) if abs(v) > 1e-5]
        return "+".join(terms) or "0"

    for tag, sx in (("L", 1), ("R", -1)):
        sel = {"s": (pose, f"Hand{tag}")}
        S = Vector((sx * SHOULDER[0], SHOULDER[1], SHOULDER[2]))
        solved = []
        for pname in HAND_POSES:
            ps = POSES[pname]
            mir = lambda v: Vector((sx * v[0], v[1], v[2]))  # noqa: E731
            d = mir(ps["wrist"]) - S
            dist = min(max(d.length, 0.03), LU + LF - 0.002)
            u = d.normalized()
            along = (LU * LU - LF * LF + dist * dist) / (2 * dist)
            hint = mir(ps["hint"])
            perp = (hint - u * hint.dot(u)).normalized()
            E = S + u * along + perp * math.sqrt(max(LU * LU - along * along, 0.0))
            W = S + u * dist
            q_up, q_fore = (E - S).to_track_quat("-Y", "Z"), (W - E).to_track_quat("-Y", "Z")
            f = mir(ps["finger"]).normalized()
            pn = mir(ps["palm"])
            pn = (pn - f * pn.dot(f)).normalized()
            yv, zv = -f, -pn
            q_hand = Matrix((yv.cross(zv), yv, zv)).transposed().to_quaternion()
            solved.append({"E": E - b_at, "up": q_up.to_euler(), "fore": q_fore.to_euler(),
                           "hand": (q_fore.inverted() @ q_hand).to_euler(), **ps})
        upper = sleeve(f"AV_UpperArm{tag}", LU, OF["arm"] + 0.006, OF["arm"], OF["sleeve_bands"], False)
        upper.parent, upper.location = spine, S - b_at
        fore_pose = empty(f"ForePose{tag}", solved[0]["E"], coll, spine)
        for i in range(3):
            drive(upper, "rotation_euler", pose_expr([p["up"][i] for p in solved]), sel, i)
            drive(fore_pose, "location", pose_expr([p["E"][i] for p in solved]), sel, i)
            drive(fore_pose, "rotation_euler", pose_expr([p["fore"][i] for p in solved]), sel, i)
        elbow = empty(f"Elbow{tag}", solved[0]["E"], coll, spine)  # the contract's talking-hand control
        fore = empty(f"Fore{tag}", (0, 0, 0), coll, fore_pose)
        fc = fore.driver_add("rotation_euler", 0)
        fc.driver.type = "SCRIPTED"
        fc.driver.expression = f"e*({pose_expr([p['gain'] for p in solved])})"
        for vname, target in (("e", None), ("s", (pose, f"Hand{tag}"))):
            v = fc.driver.variables.new()
            v.name = vname
            if target is None:
                v.type = "TRANSFORMS"
                v.targets[0].id, v.targets[0].transform_type, v.targets[0].transform_space = elbow, "ROT_X", "LOCAL_SPACE"
            else:
                v.type = "SINGLE_PROP"
                v.targets[0].id, v.targets[0].data_path = target[0], f'["{target[1]}"]'
        arm = sleeve(f"AV_Forearm{tag}", LF, OF["arm"] + 0.002, OF["arm"] - 0.012, OF["sleeve_bands"], True)
        arm.parent = fore
        wrist = empty(f"Wrist{tag}", (0, -LF + 0.004, 0), coll, fore)
        for i in range(3):
            drive(wrist, "rotation_euler", pose_expr([p["hand"][i] for p in solved]), sel, i)
        rbox(f"AV_Palm{tag}", (0.054, 0.052, 0.023), coll, M["skin_plain"], 0.006, origin=(0, 1, 0), parent=wrist)
        for fi, (lp, ld) in enumerate(((0.026, 0.021), (0.028, 0.023), (0.026, 0.021), (0.021, 0.018))):
            prox = rbox(f"AV_Finger{tag}{fi}a", (0.0118, lp, 0.0125), coll, M["skin_plain"], 0.0035,
                        (-sx * (1.5 - fi) * 0.0132, -0.050, 0.0), (0, 1, 0), wrist)
            dist_ = rbox(f"AV_Finger{tag}{fi}b", (0.0112, ld, 0.0118), coll, M["skin_plain"], 0.0035,
                         (0, -lp + 0.002, 0), (0, 1, 0), prox)
            for seg, j in ((prox, 0), (dist_, 1)):
                drive(seg, "rotation_euler",
                      pose_expr([(p.get("index", p["curl"]) if fi == 0 else p["curl"])[j] for p in solved]), sel, 0)
        th_a = rbox(f"AV_Thumb{tag}a", (0.0135, 0.024, 0.0135), coll, M["skin_plain"], 0.004,
                    (-sx * 0.026, -0.012, -0.001), (0, 1, 0), wrist)
        th_b = rbox(f"AV_Thumb{tag}b", (0.0125, 0.020, 0.0125), coll, M["skin_plain"], 0.004, (0, -0.022, 0), (0, 1, 0), th_a)
        drive(th_a, "rotation_euler", pose_expr([-sx * p["thumb"][0] for p in solved]), sel, 2)
        drive(th_a, "rotation_euler", pose_expr([p["thumb"][1] for p in solved]), sel, 0)
        drive(th_b, "rotation_euler", pose_expr([p["thumb"][2] for p in solved]), sel, 0)

    # --- framing height with hair (the reference's head size includes hair) --------------------------------
    bpy.context.view_layer.update()
    hair_top = max(((o.matrix_world @ Vector(c)).z for o in coll.objects
                    if o.name.startswith(("AV_Hair", "AV_Curl")) for c in o.bound_box), default=HC_Z + RZT)
    fa["frame_height"] = round(hair_top - (HC_Z - RZB), 4)

    # --- lap and legs (never framed, but the side view should not show a floating torso) -----------------
    ball("AV_Hips", (0.165, 0.125, 0.085), coll, M["ink"], (0, 0.025, 0.60), parent=root, ico=2, smooth=False)
    for sx in (1, -1):
        tube(f"AV_Leg{sx}", [Vector((sx * 0.085, 0.02, 0.585)), Vector((sx * 0.100, -0.30, 0.575)),
                             Vector((sx * 0.100, -0.33, 0.50)), Vector((sx * 0.100, -0.32, 0.10))],
             [0.074, 0.066, 0.060, 0.048], coll, M["ink"], k=8, smooth=False, parent=root)
        rbox(f"AV_Shoe{sx}", (0.090, 0.21, 0.075), coll, M["lilac"], 0.02, (sx * 0.100, -0.37, 0.04), parent=root)
    return coll
