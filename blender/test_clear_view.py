"""Headless check of clear_view.py (run by tests/test_clear_view.py): a face, a camera, a box in the way."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clear_view as cv  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 10

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0, 0, 1.2))
head = bpy.context.active_object
head.name = "AV_Head"
focus = bpy.data.objects.new("EyeFocus", None)
focus.location = (0, -0.1, 1.22)
sc.collection.objects.link(focus)
subj = {"objects": [head], "focus": focus, "frame_h": 0.3}

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam)
cam.location = (0, -2.0, 1.2)
cam.rotation_euler = (1.5708, 0, 0)

room = []  # a room shell around everything frames the shot; it must never count as a blocker
bpy.ops.mesh.primitive_cube_add(size=8, location=(0, 0, 1))
room.append(bpy.context.active_object)
room[0].name = "RoomShell"

out = {"clear": cv.score_shot(sc, cam, 1, 10, subj)}

bpy.ops.mesh.primitive_cube_add(size=0.25, location=(0, -1.0, 1.2))  # a lamp-sized prop between lens and face
prop = bpy.context.active_object
prop.name = "DeskLamp"
out["blocked"] = cv.score_shot(sc, cam, 1, 10, subj)
out["hideable"] = [o.name for o in cv.hideable(out["blocked"]["blockers"], [subj])]
out["ignored"] = cv.score_shot(sc, cam, 1, 10, subj, ignore=frozenset({"DeskLamp"}))

prop.name = "Monitor"  # a set piece is never hidden
out["monitor_hideable"] = [o.name for o in cv.hideable({"Monitor": 5}, [subj])]
prop.name = "DeskLamp"

cam.location = (0, -2.0, 1.2 + 0.25)  # captions across the top 0.08-0.17: aim so the face sits high in frame
cam.rotation_euler = (1.5708 - 0.12, 0, 0)
out["caption"] = cv.score_shot(sc, cam, 1, 10, subj, band=[0.4, 0.6], ignore=frozenset({"DeskLamp"}))
out["variants"] = [label for label, _ in cv.variants({"framing": {"az": [-30, -24], "el": 4, "head": 0.4, "eyes": 0.5}})]

Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(out), encoding="utf-8")
