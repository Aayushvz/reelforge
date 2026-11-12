"""Evidence for gate P3 (the rooms): per room one wide and one hero close-up, with the hero and the Claude robot in place.
  blender -b --factory-startup --python-exit-code 1 -P blender/shotsav/room_sheets.py -- <out_dir> [room ...]
Writes <out_dir>/_tiles/<room>_{wide,close}.png, <out_dir>/rooms.jpg (contact sheet) and <out_dir>/rooms.json
(jacket purple and desk-front luminance per still)."""
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bl_common import look_at  # noqa: E402
from shotsav import buddies, hero, rooms  # noqa: E402
from shotsav.sheets import PURPLE, grid, hex_of, lab, load, save  # noqa: E402

import numpy as np  # noqa: E402

EYE_Z = 1.174  # the hero's eye height (HC_Z + EYE_Z)
SETUPS = {  # lens, azimuth (deg, + = toward the monitor side), elevation above the eye line (deg), head height share,
    # eye line from the top, f-stop (a first pass of prompt 5.1's av_wide_34 and av_hero_34; P4 measures them)
    "wide": (50, 15, 8, 0.25, 0.36, 2.8, -0.12),  # the last value shifts the aim sideways so the buddy fits
    "close": (85, 30, 4, 0.46, 0.52, 1.8, 0.0),
}


def setup_scene(room_id, size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    rooms.build(room_id)
    hero.build()
    head = bpy.data.objects["Head"]
    head.rotation_euler.z = -0.12  # a slight turn toward his buddy; the eyes do the rest
    ctrl = bpy.data.objects["FaceCtrl"]
    ctrl["eyeLookDownLeft"] = ctrl["eyeLookDownRight"] = 0.35
    ctrl["eyeLookInLeft"] = ctrl["eyeLookOutRight"] = 0.45
    coll = buddies.build("claude")
    for o in coll.objects:
        o.name = f"claude:{o.name.split('.')[0]}"
    bpy.data.objects["claude:CHAR_root"].location = Vector(rooms.MARK_B)
    bpy.data.objects["claude:CHAR_root"].rotation_euler.z = math.radians(-20)  # turned a little toward the hero
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.eevee.taa_render_samples = 64
    sc.render.image_settings.file_format = "PNG"
    return sc


def place_camera(sc, kind):
    lens, az, el, head_share, eye_top, fstop, shift = SETUPS[kind]
    head_h = hero.RZT + hero.RZB
    frame_h = head_h / head_share
    d = frame_h * lens / 36.0  # portrait: the 36 mm sensor spans the height
    aim = Vector((shift, 0.0, EYE_Z + (eye_top - 0.5) * frame_h))  # eyes above centre when eye_top < 0.5
    a, e = math.radians(az), math.radians(el)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    cam.location = Vector((shift, 0, EYE_Z)) + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
    cam.data.lens = lens
    look_at(cam, aim)
    cam.data.dof.use_dof, cam.data.dof.aperture_fstop = True, fstop
    cam.data.dof.focus_object = bpy.data.objects["EyeFocus"]
    cam.data.dof.aperture_blades = 0
    sc.camera = cam
    return cam


def measure(sc, cam, img):
    h, w = img.shape[:2]

    def at(p, r=6):
        co = world_to_camera_view(sc, cam, Vector(p))
        x, y = int(co.x * w), int(co.y * h)
        if not (r <= x < w - r and r <= y < h - r) or co.z <= 0:
            return None
        return img[y - r:y + r + 1, x - r:x + r + 1, :3].reshape(-1, 3).mean(0)

    out = {}
    jacket = at((0.11, -0.15, 0.86))
    if jacket is not None:
        target = np.array([int(PURPLE[i:i + 2], 16) / 255 for i in (1, 3, 5)])
        out["jacket"] = {"hex": hex_of(jacket), "dE76": round(float(np.linalg.norm(lab(jacket) - lab(target))), 1)}
    front = at((0.0, -0.88, rooms.DESK_Z - 0.03), 4)
    if front is not None:
        lum = float(0.2126 * front[0] + 0.7152 * front[1] + 0.0722 * front[2])
        out["desk_front_luma"] = round(lum, 3)
    return out


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(args[0]).resolve()
    (out / "_tiles").mkdir(parents=True, exist_ok=True)
    ids = args[1:] or list(rooms.ROOMS)
    report, tiles = {}, []
    report_path = out / "rooms.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    for rid in ids:
        report[rid] = {}
        for kind in ("wide", "close"):
            sc = setup_scene(rid, (540, 960))
            cam = place_camera(sc, kind)
            path = out / "_tiles" / f"{rid}_{kind}.png"
            sc.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            report[rid][kind] = measure(sc, cam, load(path))
            print(f"room {rid} {kind}: {report[rid][kind]}")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for rid in rooms.ROOMS:  # the sheet always shows all six, in table order, two stills each
        for kind in ("wide", "close"):
            p = out / "_tiles" / f"{rid}_{kind}.png"
            if p.exists():
                tiles.append(load(p))
    if tiles:
        save(grid(tiles, 4), out / "rooms.jpg")
