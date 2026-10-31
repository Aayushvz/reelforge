"""Render a reelforge render_plan.json inside an environment .blend.
Run: blender -b <env.blend> --factory-startup --python-exit-code 1 -P blender/render_plan.py -- <plan.json> <stills|full>"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_common import look_at  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
plan = json.loads(Path(args[0]).read_text(encoding="utf-8"))
mode = args[1] if len(args) > 1 else "full"
sc = bpy.context.scene
fps, n = plan["fps"], plan["n_frames"]

# shot kind -> (distance m, f-stop, azimuth rad, elevation rad)
SHOT = {"wide": (2.6, 1.2, math.radians(-15), math.radians(6)),
        "medium": (1.8, 1.8, math.radians(12), math.radians(4)),
        "closeup": (2.3, 2.0, math.radians(-6), math.radians(2))}

# --- character ------------------------------------------------------------
if len(plan["characters"]) > 1:
    print("WARNING: M1 renders only the first character")
char = plan["characters"][0]
with bpy.data.libraries.load(plan["character_blend"], link=False) as (src, dst):
    dst.collections = [c for c in src.collections if c == "CHAR_base"]
coll = dst.collections[0]
sc.collection.children.link(coll)
objs = {o.name.split(".")[0]: o for o in coll.objects}
root, head, ctrl = objs["CHAR_root"], objs["Head"], objs["FaceCtrl"]
root.location = bpy.data.objects[char["mark"]].location
bpy.context.view_layer.update()
face_pos = head.matrix_world.translation + Vector((0, 0, 0.18))
focus = bpy.data.objects.new("FocusFace", None)
sc.collection.objects.link(focus)
focus.location = face_pos + Vector((0, -0.19, 0))  # eye plane, not head centre


def key_track(obj, path, values, eps=0.002, index=-1):
    last = None
    for f, v in enumerate(values):
        if last is None or abs(v - last) > eps or f == len(values) - 1:
            if index >= 0:
                getattr(obj, path)[index] = v
                obj.keyframe_insert(path, index=index, frame=f + 1)
            else:
                obj[path[2:-2]] = v
                obj.keyframe_insert(path, frame=f + 1)
            last = v


for ch, values in char["face"].items():
    if ch == "headNod" or ch not in ctrl.keys() or max(values) == 0.0:
        continue
    key_track(ctrl, f'["{ch}"]', values)
nod = char["face"].get("headNod", [0.0] * n)
for f in range(0, n, 2):
    head.rotation_euler = (nod[f] + 0.02 * math.sin(f * 0.05), 0.015 * math.sin(f * 0.031), 0.0)
    head.keyframe_insert("rotation_euler", frame=f + 1)

# --- moods (10-frame crossfades) -------------------------------------------
presets = plan["mood_presets"]


def apply_mood(p, frame):
    for name, ck, wk in (("Key", "key", "key_w"), ("Rim", "rim", "rim_w"), ("Glow", "glow", "glow_w")):
        ld = bpy.data.objects[name].data
        ld.color, ld.energy = p[ck], p[wk]
        ld.keyframe_insert("color", frame=frame)
        ld.keyframe_insert("energy", frame=frame)
    c = p["screen"]
    for mname in ("ScreenMat", "HoloMat"):
        node = bpy.data.materials[mname].node_tree.nodes["Code"]
        node.inputs["Color1"].default_value = (*c, 1.0)
        node.inputs["Color2"].default_value = (c[0] * 0.5, c[1] * 0.5, c[2] * 0.5, 1.0)
        node.inputs["Color1"].keyframe_insert("default_value", frame=frame)
        node.inputs["Color2"].keyframe_insert("default_value", frame=frame)


moods = plan["moods"]
apply_mood(presets[moods[0][1]], 1)
for (f, m), (_, prev) in zip(moods[1:], moods[:-1]):
    apply_mood(presets[prev], max(1, f + 1 - 5))
    apply_mood(presets[m], f + 1 + 5)

# --- cameras per shot --------------------------------------------------------
cams = []
for i, s in enumerate(plan["shots"]):
    dist, fstop, az, el = SHOT[s["kind"]]
    cd = bpy.data.cameras.new(f"Cam{i}")
    cd.lens = s["lens"]
    cd.dof.use_dof = True
    cd.dof.focus_object = focus
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_ratio = 1.5  # oval, anamorphic-style bokeh
    cam = bpy.data.objects.new(f"Cam{i}", cd)
    sc.collection.objects.link(cam)
    fov = 2 * math.atan(18.0 / s["lens"])
    span = 2 * dist * math.tan(fov / 2)
    aim = face_pos + Vector((0, 0, 0.12 * span))  # face sits low → caption headroom on top
    dirv = Vector((math.sin(az), -math.cos(az), math.sin(el))).normalized()
    a, b = s["start_frame"] + 1, s["end_frame"]
    for f in list(range(a, b + 1, 2)) + [b]:
        u = (f - a) / max(1, b - a)
        d = dist * (1 - s["push"] * u)
        jitter = Vector((math.sin(f * 0.21) + 0.5 * math.sin(f * 0.53 + 1.0), 0.0,
                         math.sin(f * 0.17 + 2.0) + 0.5 * math.sin(f * 0.41))) * 0.003 * dist
        cam.location = aim + dirv * d + jitter
        look_at(cam, aim)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    marker = sc.timeline_markers.new(f"S{i}", frame=a)
    marker.camera = cam
    cams.append((cam, a, b))

# --- render settings ---------------------------------------------------------
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.eevee.taa_render_samples = plan["samples"]
sc.render.resolution_x, sc.render.resolution_y = plan["resolution"]
sc.render.resolution_percentage = 100
sc.render.fps = fps
sc.frame_start, sc.frame_end = 1, n
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "8"
sc.camera = cams[0][0]

if mode == "stills":
    Path(plan["out_stills"]).mkdir(parents=True, exist_ok=True)
    for i, (cam, a, b) in enumerate(cams):
        sc.camera = cam
        sc.frame_set((a + b) // 2)
        sc.render.filepath = str(Path(plan["out_stills"]) / f"shot_{i:02d}.png")
        bpy.ops.render.render(write_still=True)
else:
    Path(plan["out_frames"]).mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(Path(plan["out_frames"])) + "/"
    bpy.ops.render.render(animation=True)
print("render_plan done")
