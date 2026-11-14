"""Studio still of a character .blend for review: -- <out.png> [yaw=deg] [shot=head|bust|body|hands] <prop=value>...
Clean key + rim + fill on a dark gradient backdrop, framed from FaceAnchor."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_common import EEVEE, look_at, material  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
out, sets = args[0], dict(a.split("=") for a in args[1:])
yaw = math.radians(float(sets.pop("yaw", 0)))
shot = sets.pop("shot", "head")
if sets.pop("enliven", "0") == "1":  # try the liveliness pass without saving the file
    from liveliness import enliven
    print("ENLIVENED", enliven({m for o in bpy.data.objects if o.type == "MESH" for m in o.data.materials if m}))
sc = bpy.context.scene
ctrl = bpy.data.objects["FaceCtrl"]
for k, v in sets.items():
    ctrl[k] = float(v)
bpy.context.view_layer.update()
face = bpy.data.objects["FaceAnchor"].matrix_world.translation.copy()
dist, lens, lift = {"head": (0.9, 85, 0.0), "bust": (1.3, 70, -0.12), "body": (2.4, 50, -0.35),
                    "hands": (0.9, 60, -0.55)}[shot]
aim = face + Vector((0, 0, lift))
cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
sc.collection.objects.link(cam)
cam.location = aim + Vector((math.sin(yaw), -math.cos(yaw), 0.05)) * dist
cam.data.lens = lens
look_at(cam, aim)
sc.camera = cam


def light(name, loc, energy, size, color=(1, 1, 1)):
    o = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    o.data.energy, o.data.size, o.data.color = energy, size, color
    o.location = face + Vector(loc)
    look_at(o, face)
    sc.collection.objects.link(o)


# Portrait lighting: a big warm key, a soft cool fill, two rims, and a small light by the lens that puts a catchlight
# in each eye (eyes with no catchlight read as dead).
light("Key", (0.9, -1.0, 0.55), 55, 1.2, (1.0, 0.91, 0.82))
light("Fill", (-1.2, -0.9, 0.1), 9, 1.8, (0.9, 0.94, 1.0))
light("Rim", (-0.7, 0.9, 0.6), 55, 0.6, (0.85, 0.9, 1.0))
light("Rim2", (0.8, 0.8, 0.4), 30, 0.6, (1.0, 0.85, 0.7))
eye_light = bpy.data.objects.new("EyeLight", bpy.data.lights.new("EyeLight", "AREA"))
eye_light.data.energy, eye_light.data.size, eye_light.data.color = 2.5, 0.25, (1.0, 0.97, 0.94)
eye_light.location = cam.location + Vector((0.0, 0.0, 0.18))
look_at(eye_light, face)
sc.collection.objects.link(eye_light)
bpy.ops.mesh.primitive_plane_add(size=8, location=face + Vector((0, 2.0, 0)), rotation=(math.pi / 2, 0, 0))
bpy.context.active_object.data.materials.append(material("Backdrop", (0.07, 0.062, 0.058), rough=0.9))
sc.world = bpy.data.worlds.new("W")
sc.world.color = (0.03, 0.028, 0.026)
sc.render.engine = EEVEE
sc.eevee.use_raytracing = True  # subsurface and the glossy corneas need it
sc.eevee.taa_render_samples = 64
sc.render.resolution_x, sc.render.resolution_y = 720, 900
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
