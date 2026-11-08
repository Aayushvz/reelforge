"""Route (c) turnaround + full-body check. face_sheet.py's turnaround frames every visible mesh, including its own 40 m
backdrop plane, so the figure comes out as a speck; this copy frames only the character (the shared file is not edited).

Run: blender -b <char.blend> --python-exit-code 1 -P blender/bakeoff/route_c_turnaround.py -- <out_dir> [samples]
Writes turn_<front|three_q|side|back>.png at 50 mm, full height, same lights as the face sheets, and turnaround.png."""
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(args[0]).resolve()
SAMPLES = int(args[1]) if len(args) > 1 else 24
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
anchor = bpy.data.objects["FaceAnchor"]
HH = float(anchor["head_height"])
face = anchor.matrix_world.translation.copy()
S = HH / 0.3
lo, hi = [], []
for o in sc.objects:
    if o.type == "MESH" and not o.hide_render and o.visible_get():
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo.append(min(v.z for v in bb))
        hi.append(max(v.z for v in bb))
bottom, top = max(min(lo), 0.0), max(hi)
mid = Vector((0, face.y, (bottom + top) / 2))
tall = top - bottom
print("character height", round(tall, 3), "m")


def look_at(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


def light(name, off, energy, size, color):
    lo_ = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    lo_.data.energy, lo_.data.size, lo_.data.color = energy * S * S * 6, size * S * 3, color
    lo_.location = mid + Vector(off) * S * 3
    look_at(lo_, mid)
    sc.collection.objects.link(lo_)


for o in [o for o in sc.objects if o.type in ("LIGHT", "CAMERA")]:
    o.hide_render = True
light("Key", (0.75, -0.95, 0.45), 90, 0.7, (1.0, 0.93, 0.86))
light("Fill", (-1.1, -0.8, 0.0), 14, 1.6, (0.86, 0.9, 1.0))
light("Rim", (-0.6, 0.9, 0.5), 110, 0.5, (0.8, 0.88, 1.0))
light("Back", (0.6, 0.9, 0.3), 60, 0.6, (1.0, 0.95, 0.9))
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 4, mid.z), rotation=(math.pi / 2, 0, 0))
bd = bpy.data.materials.new("Backdrop")
bd.use_nodes = True
bd.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.055, 0.065, 1)
bpy.context.active_object.data.materials.append(bd)
sc.world = bpy.data.worlds.new("W")
sc.world.color = (0.02, 0.022, 0.026)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "BLENDER_EEVEE"
sc.eevee.taa_render_samples = SAMPLES
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
files = []
for name, yaw in (("front", 0.0), ("three_q", -0.75), ("side", -math.pi / 2), ("back", math.pi)):
    cam.data.lens = 50
    cam.location = mid + Vector((math.sin(yaw), -math.cos(yaw), 0.03)).normalized() * tall * 1.9
    look_at(cam, mid)
    sc.render.resolution_x, sc.render.resolution_y = 540, 960
    sc.render.filepath = str(OUT / f"turn_{name}.png")
    bpy.ops.render.render(write_still=True)
    files.append(OUT / f"turn_{name}.png")
ins, f = [], ""
for i, p in enumerate(files):
    ins += ["-i", str(p)]
    f += f"[{i}:v]scale=270:480[v{i}];"
f += "".join(f"[v{i}]" for i in range(4)) + "xstack=inputs=4:layout=0_0|270_0|540_0|810_0:fill=black"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", f, "-frames:v", "1",
                str(OUT / "turnaround.png")], check=True)
print("turnaround done", OUT)
