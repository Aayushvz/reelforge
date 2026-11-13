"""A panorama of a room's back wall for the editor's "frame to keep" picker.
  blender -b --factory-startup --python-exit-code 1 -P blender/shotsav/room_pano.py -- <out_dir> <room> [...]
Writes <out_dir>/<room>_pano.jpg and <room>_pano.json. The camera stands where the front wide does, level, and
sees the whole range the room can slide (rooms.VIEW_PAN_M, VIEW_HEIGHT_M) around the default 9:16 frame. The desk,
chair and props are hidden so the picker shows the room itself.
JSON: {"w", "h", "frame": {"x", "y", "w", "h"} (the default 9:16 window, pixels), "pan_px", "height_px"}: moving the
window right by pan_px is room_view.pan +1, up by height_px is room_view.height +1."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bl_common import look_at  # noqa: E402
from shotsav import hero, rooms  # noqa: E402

PX_PER_M = 150
LENS = 50
EYE_Z = 1.174


def render(room_id, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    rooms.build(room_id)
    pivot = bpy.data.objects["RoomPivot"]
    keep = {o for o in bpy.data.objects if o.parent == pivot or o.name in ("Floor", "RoomPivot")}
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in keep:
            o.hide_render = True  # the desk, chair and props
    frame_h = (hero.RZT + hero.RZB) / 0.25  # the wide's framing at the hero
    d = frame_h * LENS / 36.0
    depth = d + 2.2 - 0.06  # camera to the back wall's face
    wall_h = depth * 36.0 / LENS  # the default frame's height on the wall, metres
    fh = round(wall_h * PX_PER_M)
    fw = round(fh * 9 / 16)
    pan_px, height_px = round(rooms.VIEW_PAN_M * PX_PER_M), round(rooms.VIEW_HEIGHT_M * PX_PER_M)
    w, h = fw + 2 * pan_px, fh + 2 * height_px
    centre_z = EYE_Z + (0.5 - 0.36) * frame_h * depth / d  # the wide's eye line sits 36% from the top
    cam = bpy.data.objects.new("PanoCam", bpy.data.cameras.new("PanoCam"))
    sc.collection.objects.link(cam)
    cam.location = (0.0, -d, centre_z)
    look_at(cam, Vector((0.0, 2.0, centre_z)))
    cam.data.lens, cam.data.sensor_fit = LENS, "VERTICAL"
    cam.data.sensor_height = 36.0 * h / fh
    cam.data.clip_end = 300
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.eevee.taa_render_samples = 32
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 88
    sc.render.filepath = str(out / f"{room_id}_pano.jpg")
    bpy.ops.render.render(write_still=True)
    meta = {"w": w, "h": h, "frame": {"x": pan_px, "y": height_px, "w": fw, "h": fh}, "pan_px": pan_px,
            "height_px": height_px}
    (out / f"{room_id}_pano.json").write_text(json.dumps(meta), encoding="utf-8")
    print("pano", room_id, meta)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(args[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for rid in args[1:] or list(rooms.ROOMS):
        render(rid, out)
