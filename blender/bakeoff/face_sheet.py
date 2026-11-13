"""Route-agnostic face sheets for the Phase 1 bake-off (and later the per-character face gate).

Run: blender -b <char.blend> --python-exit-code 1 -P blender/bakeoff/face_sheet.py -- <out_dir> [samples]

The .blend must meet the character contract: objects FaceCtrl (52 ARKit float props), FaceAnchor (prop
head_height, metres), EyeFocus. Renders, under one fixed portrait rig (key ~35 deg, soft fill, rim, hair light,
eye catchlight), at 85 mm:
  face_<pose>.png  neutral, 7 emotions, visemes A/E/O/M, blink, gaze L/R/U/D  -> face_sheet.png (6x3)
  ecu_eyes.png, ecu_mouth.png                                                    (extreme close-ups)
  turn_<front|three_q|side|back>.png at 50 mm, full height                     -> turnaround.png
Same lights and cameras for every route, so sheets are directly comparable."""
import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(args[0]).resolve()  # Blender resolves relative render paths against the .blend, not the cwd
SAMPLES = int(args[1]) if len(args) > 1 else 32
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
ctrl = bpy.data.objects["FaceCtrl"]
anchor = bpy.data.objects["FaceAnchor"]
focus = bpy.data.objects["EyeFocus"]
HH = float(anchor["head_height"])

# FaceCtrl values per pose. Emotions are deliberately strong: they must read at phone size.
POSES = {
    "neutral": {},
    "laugh": {"jawOpen": 0.45, "mouthSmileLeft": 1, "mouthSmileRight": 1, "cheekSquintLeft": 0.8,
              "cheekSquintRight": 0.8, "eyeSquintLeft": 0.6, "eyeSquintRight": 0.6, "browInnerUp": 0.2},
    "smug": {"mouthSmileLeft": 0.8, "mouthDimpleLeft": 0.4, "mouthPressRight": 0.4, "browOuterUpRight": 0.9,
             "browDownLeft": 0.5, "eyeSquintLeft": 0.35, "eyeBlinkLeft": 0.2, "eyeBlinkRight": 0.2},
    "surprised": {"jawOpen": 0.55, "mouthFunnel": 0.4, "eyeWideLeft": 1, "eyeWideRight": 1, "browInnerUp": 1,
                  "browOuterUpLeft": 1, "browOuterUpRight": 1},
    "sad": {"mouthFrownLeft": 1, "mouthFrownRight": 1, "mouthShrugLower": 0.5, "browInnerUp": 0.9,
            "eyeLookDownLeft": 0.4, "eyeLookDownRight": 0.4, "eyeBlinkLeft": 0.25, "eyeBlinkRight": 0.25},
    "angry": {"browDownLeft": 1, "browDownRight": 1, "noseSneerLeft": 0.7, "noseSneerRight": 0.7,
              "mouthFrownLeft": 0.5, "mouthFrownRight": 0.5, "mouthPressLeft": 0.6, "mouthPressRight": 0.6,
              "eyeSquintLeft": 0.5, "eyeSquintRight": 0.5},
    "worried": {"browInnerUp": 1, "browDownLeft": 0.2, "browDownRight": 0.2, "mouthStretchLeft": 0.4,
                "mouthStretchRight": 0.4, "mouthRollLower": 0.3, "eyeWideLeft": 0.3, "eyeWideRight": 0.3},
    "deadpan": {"eyeBlinkLeft": 0.4, "eyeBlinkRight": 0.4, "mouthPressLeft": 0.3, "mouthPressRight": 0.3},
    "viseme_A": {"jawOpen": 0.6},
    "viseme_E": {"jawOpen": 0.25, "mouthStretchLeft": 0.5, "mouthStretchRight": 0.5},
    "viseme_O": {"jawOpen": 0.35, "mouthFunnel": 0.8, "mouthPucker": 0.3},
    "viseme_M": {"mouthPressLeft": 0.7, "mouthPressRight": 0.7, "mouthRollLower": 0.45, "mouthRollUpper": 0.35},
    "blink": {"eyeBlinkLeft": 1, "eyeBlinkRight": 1},
    "gaze_left": {"eyeLookOutLeft": 1, "eyeLookInRight": 1},
    "gaze_right": {"eyeLookInLeft": 1, "eyeLookOutRight": 1},
    "gaze_up": {"eyeLookUpLeft": 1, "eyeLookUpRight": 1},
    "gaze_down": {"eyeLookDownLeft": 1, "eyeLookDownRight": 1},
}
ARKIT = [k for k in ctrl.keys() if k[0].islower()]


def set_pose(values):
    for k in ARKIT:
        ctrl[k] = float(values.get(k, 0.0))
    ctrl.update_tag()
    bpy.context.view_layer.update()


def look_at(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


set_pose({})
face = anchor.matrix_world.translation.copy()
eyes = focus.matrix_world.translation.copy()
S = HH / 0.3  # scale the rig to the head

# --- one fixed portrait rig ---------------------------------------------------------------------
for o in [o for o in sc.objects if o.type in ("LIGHT", "CAMERA")]:
    o.hide_render = True  # sheets light the character the same way for every route


def light(name, off, energy, size, color):
    lo = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    lo.data.energy, lo.data.size, lo.data.color = energy * S * S, size * S, color
    lo.location = face + Vector(off) * S
    look_at(lo, face)
    sc.collection.objects.link(lo)


light("SheetKey", (0.75, -0.95, 0.45), 90, 0.7, (1.0, 0.93, 0.86))   # ~35 deg off axis, above
light("SheetFill", (-1.1, -0.8, 0.0), 14, 1.6, (0.86, 0.9, 1.0))
light("SheetRim", (-0.6, 0.9, 0.5), 110, 0.5, (0.8, 0.88, 1.0))
light("SheetHair", (0.3, 0.6, 1.1), 50, 0.6, (1.0, 0.95, 0.9))
light("SheetCatch", (0.15, -1.6, 0.1), 6, 0.25, (1.0, 1.0, 1.0))      # small, frontal: eye catchlight
# Measure the character for the turnaround before adding the backdrop, which would otherwise dominate the bounds.
lo, hi = [], []
for o in sc.objects:
    if o.type == "MESH" and not o.hide_render and o.visible_get():
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo.append(min(v.z for v in bb))
        hi.append(max(v.z for v in bb))
bpy.ops.mesh.primitive_plane_add(size=40 * S, location=face + Vector((0, 2.5, 0)), rotation=(math.pi / 2, 0, 0))
backdrop = bpy.context.active_object
bd = bpy.data.materials.new("SheetBackdrop")
bd.use_nodes = True
bd.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.03, 0.035, 0.045, 1)
bpy.context.active_object.data.materials.append(bd)
sc.world = bpy.data.worlds.new("SheetWorld")
sc.world.color = (0.015, 0.017, 0.02)

cam = bpy.data.objects.new("SheetCam", bpy.data.cameras.new("SheetCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.dof.use_dof, cam.data.dof.focus_object = True, focus
sc.render.engine = "BLENDER_EEVEE" if bpy.app.version >= (5, 0, 0) else "BLENDER_EEVEE_NEXT"
sc.eevee.taa_render_samples = SAMPLES
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.render.image_settings.file_format = "PNG"


def shot(name, aim, dist, lens, fstop, yaw=-0.35, res=(720, 900), elev=0.05):
    cam.data.lens, cam.data.dof.aperture_fstop = lens, fstop
    cam.location = Vector(aim) + Vector((math.sin(yaw), -math.cos(yaw), elev)).normalized() * dist
    look_at(cam, aim)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


# --- face sheet (85 mm, head fills ~70% of frame height) --------------------------------------------
close = HH * 2.9
for pose, vals in POSES.items():
    set_pose(vals)
    shot(f"face_{pose}", face, close, 85, 2.8)
set_pose({})
shot("ecu_eyes", eyes, HH * 1.1, 85, 4.0, yaw=-0.15, res=(900, 450))
mouth = face - Vector((0, 0, HH * 0.28))
set_pose(POSES["viseme_A"])
shot("ecu_mouth", mouth, HH * 1.1, 85, 4.0, yaw=-0.15, res=(900, 450))
set_pose({})

# --- turnaround (full height if the character has legs; frames whatever is there) -------------------
backdrop.hide_render = True  # the camera circles the character; a plane behind it would block the back view
bottom, top = max(min(lo), 0.0), max(hi)
mid = Vector((face.x, face.y, (bottom + top) / 2))
tall = top - bottom
for name, yaw in (("front", 0.0), ("three_q", -0.75), ("side", -math.pi / 2), ("back", math.pi)):
    shot(f"turn_{name}", mid, tall * 2.0, 50, 8.0, yaw=yaw, res=(540, 960))


# --- contact sheets via ffmpeg -----------------------------------------------------------------------
def tile(files, cols, w, h, out):
    ins, f = [], ""
    for i, p in enumerate(files):
        ins += ["-i", str(p)]
        f += f"[{i}:v]scale={w}:{h}[v{i}];"
    lay = "|".join(f"{(i % cols) * w}_{(i // cols) * h}" for i in range(len(files)))
    f += "".join(f"[v{i}]" for i in range(len(files))) + f"xstack=inputs={len(files)}:layout={lay}:fill=black"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", f, "-frames:v", "1", str(out)],
                   check=True)


tile([OUT / f"face_{p}.png" for p in POSES], 6, 240, 300, OUT / "face_sheet.png")
tile([OUT / f"turn_{n}.png" for n in ("front", "three_q", "side", "back")], 4, 270, 480, OUT / "turnaround.png")
(OUT / "poses.json").write_text(json.dumps(POSES, indent=1), encoding="utf-8")
print("face_sheet done", OUT)
