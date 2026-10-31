"""Render a front still of base.blend for visual review: -- <out.png> <prop=value>..."""
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_common import look_at  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
out, sets = args[0], dict(a.split("=") for a in args[1:])
sc = bpy.context.scene
ctrl = bpy.data.objects["FaceCtrl"]
for k, v in sets.items():
    ctrl[k] = float(v)
cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
sc.collection.objects.link(cam)
cam.location = (0.0, -1.2, 1.3)
cam.data.lens = 60
look_at(cam, (0, 0, 1.25))
sc.camera = cam
key = bpy.data.objects.new("PrevKey", bpy.data.lights.new("PrevKey", "AREA"))
key.data.energy, key.data.size = 120, 1.0
key.location = (0.6, -1.0, 1.8)
look_at(key, (0, 0, 1.3))
sc.collection.objects.link(key)
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 720, 900
sc.view_settings.view_transform = "AgX"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
