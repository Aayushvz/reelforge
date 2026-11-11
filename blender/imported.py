"""Imported asset library (data only): third-party characters and environments wired to the reelforge contract.

Sources are big and live outside the repo: SRC_ROOT (override with REELFORGE_IMPORTS). import_character.py and
import_set.py turn them into assets/build/<id>.blend. Characters are never decimated, texture-downscaled or
shape-key pruned: facial detail is the target. Optimizing = cleanup (rig widgets, stray lights/cameras, unused
armatures), contract wiring, packed textures.

Face specs map each ARKit channel to shape keys [(key, weight)] and/or bone moves
[(bone, "rot", world_axis, degrees) | (bone, "loc", world_offset_m) | (bone, "orbit", pivot_bone, world_axis, degrees)
— orbit slides the bone's head along the arc around the pivot, for controls that are tracked rather than rotated].
World axes assume the character faces -Y;
"L" is the character's left (+X)."""
import os
from pathlib import Path

SRC_ROOT = Path(os.environ.get("REELFORGE_IMPORTS", Path.home() / "Downloads" / "BLENDER FILES"))
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def _lr(fn):
    """{arkit_name: spec} for both sides from fn(side, s, cc) -> (arkitLeft spec); s=+1 left/-1 right."""
    out = {}
    for side, s, cc, ar in (("L", 1, "L", "Left"), ("R", -1, "R", "Right")):
        for k, v in fn(side, s, cc).items():
            out[k.replace("#", ar)] = v
    return out


# --- Character Creator 4 (Extended facial profile) shape keys -> ARKit -----------------------------------
CC4 = {
    **_lr(lambda side, s, c: {
        "eyeBlink#": [(f"Eye_Blink_{c}", 1.0)],
        "eyeSquint#": [(f"Eye_Squint_{c}", 1.0)],
        "eyeWide#": [(f"Eye_Wide_{c}", 1.0)],
        "eyeLookDown#": [(f"Eye_{c}_Look_Down", 1.0)],
        "eyeLookUp#": [(f"Eye_{c}_Look_Up", 1.0)],
        "eyeLookIn#": [(f"Eye_{c}_Look_{'R' if c == 'L' else 'L'}", 1.0)],
        "eyeLookOut#": [(f"Eye_{c}_Look_{c}", 1.0)],
        "mouthSmile#": [(f"Mouth_Smile_{c}", 1.0)],
        "mouthFrown#": [(f"Mouth_Frown_{c}", 1.0)],
        "mouthDimple#": [(f"Mouth_Dimple_{c}", 1.0)],
        "mouthStretch#": [(f"Mouth_Stretch_{c}", 1.0)],
        "mouthPress#": [(f"Mouth_Press_{c}", 1.0)],
        "mouthLowerDown#": [(f"Mouth_Down_Lower_{c}", 1.0)],
        "mouthUpperUp#": [(f"Mouth_Up_Upper_{c}", 1.0)],
        "browDown#": [(f"Brow_Drop_{c}", 1.0), (f"Brow_Compress_{c}", 0.5)],
        "browOuterUp#": [(f"Brow_Raise_Outer_{c}", 1.0)],
        "cheekSquint#": [(f"Cheek_Raise_{c}", 1.0)],
        "noseSneer#": [(f"Nose_Sneer_{c}", 1.0)],
    }),
    "jawOpen": [("Jaw_Open", 1.0)],
    "jawForward": [("Jaw_Forward", 1.0)],
    "jawLeft": [("Jaw_L", 1.0)],
    "jawRight": [("Jaw_R", 1.0)],
    "mouthClose": [("Mouth_Close", 1.0)],
    "mouthFunnel": [(f"Mouth_Funnel_{p}", 1.0) for p in ("Up_L", "Up_R", "Down_L", "Down_R")],
    "mouthPucker": [(f"Mouth_Pucker_{p}", 1.0) for p in ("Up_L", "Up_R", "Down_L", "Down_R")],
    "mouthLeft": [("Mouth_L", 1.0)],
    "mouthRight": [("Mouth_R", 1.0)],
    "mouthRollLower": [("Mouth_Roll_In_Lower_L", 1.0), ("Mouth_Roll_In_Lower_R", 1.0)],
    "mouthRollUpper": [("Mouth_Roll_In_Upper_L", 1.0), ("Mouth_Roll_In_Upper_R", 1.0)],
    "mouthShrugLower": [("Mouth_Shrug_Lower", 1.0)],
    "mouthShrugUpper": [("Mouth_Shrug_Upper", 1.0)],
    "browInnerUp": [("Brow_Raise_Inner_L", 1.0), ("Brow_Raise_Inner_R", 1.0)],
    "cheekPuff": [("Cheek_Puff_L", 1.0), ("Cheek_Puff_R", 1.0)],
    "tongueOut": [("Tongue_Out", 1.0)],
}

# --- Rigify face controls (Freya) -------------------------------------------------------------------------
RIGIFY_FACE = {
    **_lr(lambda side, s, c: {
        "eyeBlink#": [(f"lid.T.{side}.001", "loc", (0, -0.001, -0.007)), (f"lid.T.{side}.002", "loc", (0, -0.002, -0.009)),
                      (f"lid.T.{side}.003", "loc", (0, -0.001, -0.007)), (f"lid.B.{side}.002", "loc", (0, 0, 0.0015))],
        "eyeSquint#": [(f"lid.B.{side}.00{i}", "loc", (0, 0, 0.0025)) for i in (1, 2, 3)] + [(f"cheek.T.{side}.001", "loc", (0, 0, 0.002))],
        "eyeWide#": [(f"lid.T.{side}.002", "loc", (0, 0, 0.0025)), (f"lid.T.{side}.001", "loc", (0, 0, 0.0015)), (f"lid.T.{side}.003", "loc", (0, 0, 0.0015))],
        "mouthSmile#": [(f"lip_end.{side}.001", "loc", (s * 0.004, 0.003, 0.006)), (f"cheek.B.{side}.001", "loc", (s * 0.001, -0.001, 0.003))],
        "mouthFrown#": [(f"lip_end.{side}.001", "loc", (0, 0, -0.005))],
        "mouthDimple#": [(f"lip_end.{side}.001", "loc", (0, 0.003, 0))],
        "mouthStretch#": [(f"lip_end.{side}.001", "loc", (s * 0.005, 0, -0.002))],
        "mouthPress#": [(f"lip.T.{side}.001", "loc", (0, 0, -0.0012)), (f"lip.B.{side}.001", "loc", (0, 0, 0.0012))],
        "mouthLowerDown#": [(f"lip.B.{side}.001", "loc", (0, 0, -0.004))],
        "mouthUpperUp#": [(f"lip.T.{side}.001", "loc", (0, 0, 0.004))],
        "browDown#": [(f"brow.T.{side}.00{i}", "loc", (-s * 0.001, 0, -0.004)) for i in (1, 2, 3)],
        "browOuterUp#": [(f"brow.T.{side}.001", "loc", (0, 0, 0.006)), (f"brow.T.{side}.002", "loc", (0, 0, 0.003))],
        "cheekSquint#": [(f"cheek.T.{side}.001", "loc", (0, 0, 0.003)), (f"lid.B.{side}.002", "loc", (0, 0, 0.0015))],
        "noseSneer#": [(f"nose.{side}.001", "loc", (0, 0, 0.003))],
    }),
    "jawOpen": [("jaw_master", "rot", X, 20)],
    "jawForward": [("jaw_master", "loc", (0, -0.005, 0))],
    "jawLeft": [("jaw_master", "rot", Z, 5)],
    "jawRight": [("jaw_master", "rot", Z, -5)],
    "mouthClose": [("lip.B", "loc", (0, 0, 0.003))],
    "mouthFunnel": [("lip.T", "loc", (0, -0.003, 0.002)), ("lip.B", "loc", (0, -0.003, -0.002))]
                   + [(f"lip_end.{s_}.001", "loc", (-k * 0.004, 0, 0)) for s_, k in (("L", 1), ("R", -1))],
    "mouthPucker": [("lip.T", "loc", (0, -0.005, 0)), ("lip.B", "loc", (0, -0.005, 0))]
                   + [(f"lip_end.{s_}.001", "loc", (-k * 0.007, -0.002, 0)) for s_, k in (("L", 1), ("R", -1))],
    "mouthLeft": [(b, "loc", (0.004, 0, 0)) for b in ("lip.T", "lip.B", "lip_end.L.001", "lip_end.R.001")],
    "mouthRight": [(b, "loc", (-0.004, 0, 0)) for b in ("lip.T", "lip.B", "lip_end.L.001", "lip_end.R.001")],
    "mouthRollLower": [("lip.B", "loc", (0, 0.003, 0.002))],
    "mouthRollUpper": [("lip.T", "loc", (0, 0.003, -0.002))],
    "mouthShrugLower": [("lip.B", "loc", (0, -0.002, 0.003)), ("chin", "loc", (0, 0, 0.003))],
    "mouthShrugUpper": [("lip.T", "loc", (0, -0.001, 0.002))],
    "browInnerUp": [(f"brow.T.{s_}.003", "loc", (0, 0, 0.006)) for s_ in "LR"],
    "cheekPuff": [(f"cheek.B.{s_}.001", "loc", (k * 0.005, -0.002, 0)) for s_, k in (("L", 1), ("R", -1))],
}

# --- Auto-Rig Pro face controls (cute girl) ---------------------------------------------------------------
ARP_FACE = {
    **_lr(lambda side, s, c: {
        "eyeBlink#": [(f"c_eyelid_top.{side.lower()}", "loc", (0, 0, -0.019)), (f"c_eyelid_bot.{side.lower()}", "loc", (0, 0, 0.003))],
        "eyeSquint#": [(f"c_eyelid_bot.{side.lower()}", "loc", (0, 0, 0.004)), (f"c_cheek_smile.{side.lower()}", "loc", (0, 0, 0.002))],
        "eyeWide#": [(f"c_eyelid_top.{side.lower()}", "loc", (0, 0, 0.003))],
        "mouthSmile#": [(f"c_lips_smile.{side.lower()}", "loc", (s * 0.004, 0.003, 0.006)), (f"c_cheek_smile.{side.lower()}", "loc", (0, -0.001, 0.003))],
        "mouthFrown#": [(f"c_lips_smile.{side.lower()}", "loc", (0, 0, -0.005))],
        "mouthDimple#": [(f"c_lips_smile.{side.lower()}", "loc", (0, 0.003, 0))],
        "mouthStretch#": [(f"c_lips_smile.{side.lower()}", "loc", (s * 0.005, 0, -0.002))],
        "mouthPress#": [(f"c_lips_top.{side.lower()}", "loc", (0, 0, -0.0012)), (f"c_lips_bot.{side.lower()}", "loc", (0, 0, 0.0012))],
        "mouthLowerDown#": [(f"c_lips_bot.{side.lower()}", "loc", (0, 0, -0.004)), (f"c_lips_bot_01.{side.lower()}", "loc", (0, 0, -0.003))],
        "mouthUpperUp#": [(f"c_lips_top.{side.lower()}", "loc", (0, 0, 0.004)), (f"c_lips_top_01.{side.lower()}", "loc", (0, 0, 0.003))],
        "browDown#": [(f"c_eyebrow_full.{side.lower()}", "loc", (-s * 0.001, 0, -0.004))],
        "browOuterUp#": [(f"c_eyebrow_03.{side.lower()}", "loc", (0, 0, 0.006)), (f"c_eyebrow_02.{side.lower()}", "loc", (0, 0, 0.003))],
        "cheekSquint#": [(f"c_cheek_smile.{side.lower()}", "loc", (0, 0, 0.003))],
        "noseSneer#": [(f"c_cheek_smile.{side.lower()}", "loc", (0, 0, 0.002))],
    }),
    "jawOpen": [("c_jawbone.x", "orbit", "jawbone.x", X, 18)],  # ARP: the jaw tracks the chin control's position
    "jawForward": [("c_jawbone.x", "loc", (0, -0.004, 0))],
    "jawLeft": [("c_jawbone.x", "rot", Z, 5)],
    "jawRight": [("c_jawbone.x", "rot", Z, -5)],
    "mouthClose": [("c_lips_bot.x", "loc", (0, 0, 0.003))],
    "mouthFunnel": [("c_lips_top.x", "loc", (0, -0.003, 0.002)), ("c_lips_bot.x", "loc", (0, -0.003, -0.002))]
                   + [(f"c_lips_smile.{s_}", "loc", (-k * 0.004, 0, 0)) for s_, k in (("l", 1), ("r", -1))],
    "mouthPucker": [("c_lips_top.x", "loc", (0, -0.005, 0)), ("c_lips_bot.x", "loc", (0, -0.005, 0))]
                   + [(f"c_lips_smile.{s_}", "loc", (-k * 0.007, -0.002, 0)) for s_, k in (("l", 1), ("r", -1))],
    "mouthLeft": [(b, "loc", (0.004, 0, 0)) for b in ("c_lips_top.x", "c_lips_bot.x", "c_lips_smile.l", "c_lips_smile.r")],
    "mouthRight": [(b, "loc", (-0.004, 0, 0)) for b in ("c_lips_top.x", "c_lips_bot.x", "c_lips_smile.l", "c_lips_smile.r")],
    "mouthRollLower": [("c_lips_bot.x", "loc", (0, 0.003, 0.002))],
    "mouthRollUpper": [("c_lips_top.x", "loc", (0, 0.003, -0.002))],
    "mouthShrugLower": [("c_lips_bot.x", "loc", (0, -0.002, 0.003))],
    "mouthShrugUpper": [("c_lips_top.x", "loc", (0, -0.001, 0.002))],
    "browInnerUp": [(f"c_eyebrow_01.{s_}", "loc", (0, 0, 0.006)) for s_ in "lr"],
    "cheekPuff": [(f"c_cheek_inflate.{s_}", "loc", (k * 0.005, -0.002, 0)) for s_, k in (("l", 1), ("r", -1))],
}

# --- environments ------------------------------------------------------------------------------------------
# xform: uniform scale, then rotation about Z (deg), so the characters face -Y toward reelforge's cameras; marks are
# in SOURCE coordinates (floor height). Lights keep their look under scale (energy x scale^2). Presets set the
# contract lights (colour, watts), how much of the authored lighting stays ("practicals"), exposure and haze.
WARM, COOL, WHITE = (1.0, 0.62, 0.35), (0.3, 0.5, 1.0), (1.0, 0.95, 0.9)
SETS = {
    # neon tunnel (one mirrored mesh, emission-lit): 2 m ceiling in the source, so x1.4
    "neon_tunnel": {"name": "Neon tunnel", "src": "745.blend", "xform": {"scale": 1.4, "rot_z": 0},
                    "mark_a": (0.0, 1.5, -1.03), "mark_b": (0.75, 1.5, -1.03),
                    "presets": {
                        "neon": {"key": ((1.0, 0.55, 0.8), 90), "rim": ((0.2, 0.9, 1.0), 260), "fill": ((0.5, 0.4, 1.0), 12),
                                 "glow": ((1.0, 0.3, 0.7), 40), "practicals": 1.0, "world": (0.004, 0.003, 0.008),
                                 "exposure": -0.2, "haze": 0.012, "haze_color": (0.9, 0.6, 1.0), "tint": 0.4},
                        "blackout": {"key": (WHITE, 140), "rim": ((0.2, 0.9, 1.0), 320), "fill": ((0.3, 0.4, 1.0), 6),
                                     "glow": ((1.0, 0.3, 0.7), 20), "practicals": 1.0, "world": (0.001, 0.001, 0.002),
                                     "exposure": -0.6, "haze": 0.02, "haze_color": (0.6, 0.8, 1.0), "tint": 0.3},
                    }},
    # real-scale room with LED coves and a PlayStation-symbol neon wall; desk on the back wall
    "gaming_den": {"name": "Gaming den", "src": "Gaming_Room(online).blend", "xform": {"scale": 1.0, "rot_z": -90},
                   "mark_a": (1.3, 0.2, 0.0), "mark_b": (1.3, 1.25, 0.0),
                   "presets": {
                       "rgb_night": {"key": ((1.0, 0.7, 0.5), 60), "rim": ((0.35, 0.45, 1.0), 160), "fill": ((0.5, 0.4, 0.9), 10),
                                     "glow": ((1.0, 0.5, 0.2), 25), "practicals": 0.7, "world": (0.003, 0.004, 0.008),
                                     "exposure": -0.8, "haze": 0.004, "haze_color": (0.7, 0.75, 1.0), "tint": 0.35},
                       "late_session": {"key": ((0.45, 0.6, 1.0), 45), "rim": ((0.9, 0.2, 0.8), 200), "fill": ((0.3, 0.3, 0.6), 6),
                                        "glow": ((0.3, 0.6, 1.0), 30), "practicals": 0.4, "world": (0.002, 0.002, 0.005),
                                        "exposure": -0.9, "haze": 0.008, "haze_color": (0.6, 0.5, 1.0), "tint": 0.4},
                   }},
    # stylised isometric room (sofas, coffee table, TV wall, gaming desk); modelled ~2.8x real size
    "cozy_gaming_room": {"name": "Cozy gaming room", "src": "gaming+room.blend", "xform": {"scale": 0.36, "rot_z": 0},
                         "mark_a": (-2.6, 1.7, 0.17), "mark_b": (0.3, 1.7, 0.17),
                         "presets": {
                             "purple_neon": {"key": ((1.0, 0.7, 0.55), 70), "rim": ((0.7, 0.3, 1.0), 200), "fill": ((0.4, 0.4, 1.0), 10),
                                             "glow": ((1.0, 0.3, 0.6), 30), "practicals": 1.0, "world": (0.004, 0.002, 0.01),
                                             "exposure": -0.1, "haze": 0.004, "haze_color": (0.8, 0.6, 1.0), "tint": 0.35},
                             "chill_evening": {"key": (WARM, 90), "rim": (COOL, 140), "fill": ((0.6, 0.5, 0.8), 12),
                                               "glow": (WARM, 40), "practicals": 0.45, "world": (0.006, 0.005, 0.008),
                                               "exposure": -0.2, "haze": 0.003, "haze_color": (1.0, 0.8, 0.7), "tint": 0.3},
                         }},
}

CHARACTERS = {
    # CC4 realistic male, 140 facial morphs: the full ARKit set maps 1:1. Jaw opens with bone + morph.
    "matt": {"name": "Matt", "gender": "male", "src": "extracted/Blender/Blender/Matt.Fbx",
             "rig": "Armature", "body_mesh": "CC_Base_Body", "delete": ["Cube"],
             "bones": {"chest": "CC_Base_Spine02", "head": "CC_Base_Head", "head_def": "CC_Base_Head",
                       "upperarm_l": ("CC_Base_L_Upperarm", "CC_Base_L_Forearm"),
                       "forearm_l": ("CC_Base_L_Forearm", "CC_Base_L_Hand"),
                       "upperarm_r": ("CC_Base_R_Upperarm", "CC_Base_R_Forearm"),
                       "forearm_r": ("CC_Base_R_Forearm", "CC_Base_R_Hand")},
             "eyes": {"mode": "rot", "bones": ("CC_Base_L_Eye", "CC_Base_R_Eye")},
             "keys": CC4, "bone_face": {"jawOpen": [("CC_Base_JawRoot", "rot", X, 22)]},
             "outfits": [{"hide": ["Boxers"]}]},  # boxers poke through the jeans
    # Rigify control rig ("rig") drives the Unity export skeleton the meshes are bound to. Bone-based face.
    "freya": {"name": "Freya", "gender": "female", "src": "extracted/Blend/Blend/Freya.blend",
              "rig": "rig", "keep_armatures": ["Unity_Rig"], "delete_armatures": ["metarig"], "body_mesh": "Body",
              "props": {"upper_arm_parent.L": {"IK_FK": 1.0}, "upper_arm_parent.R": {"IK_FK": 1.0}},
              "bones": {"chest": "chest", "head": "head", "head_def": "DEF-spine.006",
                        "upperarm_l": ("upper_arm_fk.L", "forearm_fk.L"), "forearm_l": ("forearm_fk.L", "hand_fk.L"),
                        "upperarm_r": ("upper_arm_fk.R", "forearm_fk.R"), "forearm_r": ("forearm_fk.R", "hand_fk.R")},
              "eyes": {"mode": "target", "bones": ("eye.L", "eye.R"), "centers": ("DEF-eye.L", "DEF-eye.R")},
              "bone_face": RIGIFY_FACE, "outfits": [{}],
              "min_head": 0.34},  # widest flattering shot: shoulders up (head = 34% of the frame height)
    # Auto-Rig Pro rig ("rig"); an unused Rigify copy is dropped. Bone-based face.
    "cute_girl": {"name": "Cute girl", "gender": "female", "src": "extracted/cute+girl/cute girl/cute girl 4.5.blend",
                  "rig": "rig", "delete_armatures": ["sexy girl_Rigify"], "body_mesh": "body",
                  "props": {"c_hand_ik.l": {"ik_fk_switch": 1.0}, "c_hand_ik.r": {"ik_fk_switch": 1.0}},
                  "bones": {"chest": "c_spine_03.x", "head": "c_head.x", "head_def": "head.x",
                            "upperarm_l": ("c_arm_fk.l", "c_forearm_fk.l"), "forearm_l": ("c_forearm_fk.l", "c_hand_fk.l"),
                            "upperarm_r": ("c_arm_fk.r", "c_forearm_fk.r"), "forearm_r": ("c_forearm_fk.r", "c_hand_fk.r")},
                  "eyes": {"mode": "target", "bones": ("c_eye_target.l", "c_eye_target.r"), "centers": ("c_eye.l", "c_eye.r")},
                  "bone_face": ARP_FACE, "outfits": [{}], "min_head": 0.50},
}
