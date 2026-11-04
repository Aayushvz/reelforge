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


light("Key", (0.9, -1.0, 0.6), 70, 0.9, (1.0, 0.93, 0.85))
light("Fill", (-1.2, -0.9, 0.1), 12, 1.5, (0.85, 0.9, 1.0))
light("Rim", (-0.6, 1.0, 0.5), 90, 0.6, (0.8, 0.88, 1.0))
light("Rim2", (0.7, 0.9, 0.3), 50, 0.6, (1.0, 0.9, 0.8))
bpy.ops.mesh.primitive_plane_add(size=8, location=face + Vector((0, 2.0, 0)), rotation=(math.pi / 2, 0, 0))
bpy.context.active_object.data.materials.append(material("Backdrop", (0.035, 0.04, 0.05), rough=0.9))
sc.world = bpy.data.worlds.new("W")
sc.world.color = (0.02, 0.022, 0.026)
sc.render.engine = EEVEE
sc.eevee.taa_render_samples = 32
sc.render.resolution_x, sc.render.resolution_y = 720, 900
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
