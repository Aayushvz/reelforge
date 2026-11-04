"""Quick still of a set with a cast member at Mark_A: blender -b <set.blend> -P preview_set.py -- <out.png> <char.blend> [wide|medium]
Same camera recipe as render_plan.py (distance, f-stop, azimuth), half resolution, low samples."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_common import look_at  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
out, char_blend, kind = args[0], args[1], (args[2] if len(args) > 2 else "medium")
sc = bpy.context.scene
with bpy.data.libraries.load(char_blend, link=False) as (src, dst):
    dst.collections = [c for c in src.collections if c == "CHAR_base"]
coll = dst.collections[0]
sc.collection.children.link(coll)
objs = {o.name.split(".")[0]: o for o in coll.objects}
objs["CHAR_root"].location = bpy.data.objects["Mark_A"].location
bpy.context.view_layer.update()
face = objs["FaceAnchor"].matrix_world.translation.copy()
k = objs["FaceAnchor"]["head_height"] / 0.43
dist, fstop, az, el, lens = {"wide": (2.6, 0.5, -15, 6, 35), "medium": (1.8 * k ** 0.5, 1.8, 12, 4, 50)}[kind]
az, el = math.radians(az), math.radians(el)
cd = bpy.data.cameras.new("Cam")
cd.lens, cd.dof.use_dof, cd.dof.focus_object, cd.dof.aperture_fstop = lens, True, objs["EyeFocus"], fstop
cam = bpy.data.objects.new("Cam", cd)
sc.collection.objects.link(cam)
span = 2 * dist * math.tan(math.atan(18.0 / lens))
aim = face + Vector((0, 0, 0.12 * span))
cam.location = aim + Vector((math.sin(az), -math.cos(az), math.sin(el))).normalized() * dist
look_at(cam, aim)
sc.camera = cam
sc.eevee.taa_render_samples = 24
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, 50
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
