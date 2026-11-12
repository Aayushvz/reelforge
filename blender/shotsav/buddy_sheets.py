"""Evidence for gate P2 (the buddies). One Blender run per sheet:
  blender -b --factory-startup --python-exit-code 1 -P blender/shotsav/buddy_sheets.py -- <out_dir> lineup
  ... -- <out_dir> clips [buddy]        8 reaction clips at their peak frame (default claude)
  ... -- <out_dir> eyes                 eye shapes + signature pose, one row per buddy
  ... -- <out_dir> loop <buddy>         180 frames (6 s at 30 fps) of talking + one reaction -> <out>/_frames/<buddy>/
Sheets go to <out_dir>/*.jpg; encode the loops with ffmpeg afterwards (see PROGRESS.md)."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bl_common import EEVEE, look_at  # noqa: E402
from reelforge import buddy as acting  # noqa: E402
from shotsav import buddies, hero  # noqa: E402
from shotsav.geo import lin, mat, rbox  # noqa: E402
from shotsav.sheets import VIEW, grid, load, save  # noqa: E402

FPS = 30
DESK_Z = 0.74
MARK_B = Vector((-0.30, -0.36, DESK_Z))  # the buddy's mark: on the desk, to the hero's right, toward the viewer
ORDER = ("claude", "chatgpt", "figma", "nova")
LOOPS = {  # line 1 (with the reaction), line 2: original lines, not the reference's script
    "claude": (("That's great!", "hop"), ("Ship it tonight, then.", "")),
    "chatgpt": (("Okay, give me a second...", "think"), ("Try the second layout.", "")),
    "figma": (("Love the new spacing.", "happy"), ("Want a version in dark mode?", "")),
    "nova": (("Sure. That's one way.", "dry"), ("I'd keep the old one.", "")),
}


def reset(size, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = EEVEE
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_raytracing = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure = VIEW
    sc.render.image_settings.file_format = "PNG"
    sc.render.fps = FPS
    sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.012, 0.015, 0.03)
    return sc


def lamp(sc, name, loc, aim, energy, size, color):
    o = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    o.data.energy, o.data.size, o.data.color = energy, size, color
    o.location = Vector(loc)
    look_at(o, Vector(aim))
    sc.collection.objects.link(o)


def room(sc, with_hero):
    """Night-studio stand-in until P3: desk, backdrop, neutral-warm key from the monitor side, violet rim, navy fill."""
    rbox("PreviewDesk", (1.6, 0.75, 0.04), sc.collection, mat("PreviewDesk", "#3A2A22", rough=0.6), 0.006,
         (0, -0.40, DESK_Z - 0.02))
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 2.4, 0), rotation=(math.pi / 2, 0, 0))
    bpy.context.active_object.data.materials.append(mat("Wall", "#141A2E", rough=0.9))
    warm, violet, navy = (1.0, 0.85, 0.72), lin("#8B5CF6"), (0.55, 0.65, 1.0)
    b = MARK_B + Vector((0, 0, 0.07))
    lamp(sc, "BuddyKey", b + Vector((0.55, -0.75, 0.40)), b, 26, 0.6, warm)
    lamp(sc, "BuddyRim", b + Vector((-0.35, 0.55, 0.30)), b, 14, 0.3, violet)
    lamp(sc, "BuddyFill", b + Vector((-0.7, -0.6, 0.15)), b, 5, 1.0, navy)
    if with_hero:
        h = Vector((0, 0, 1.12))
        lamp(sc, "Key", h + Vector((1.15, -1.5, 0.35)), h, 95, 1.0, warm)
        lamp(sc, "Rim", h + Vector((-0.9, 1.3, 0.6)), h, 110, 0.6, violet)
        lamp(sc, "Fill", h + Vector((-1.5, -1.0, 0.2)), h, 16, 1.8, navy)
        coll = hero.build()
        bpy.data.objects["Head"].rotation_euler.z = -0.32  # the hero looks toward his buddy
        ctrl = bpy.data.objects["FaceCtrl"]
        ctrl["eyeLookDownLeft"] = ctrl["eyeLookDownRight"] = 0.45
        ctrl["eyeLookInLeft"] = ctrl["eyeLookOutRight"] = 0.5
        return coll


def place(buddy_id, at, yaw=0.0):
    coll = buddies.build(buddy_id)
    for o in coll.objects:  # one collection per buddy so several can share a scene
        o.name = f"{buddy_id}:{o.name.split('.')[0]}"
    coll.name = f"BUDDY_{buddy_id}"
    root = bpy.data.objects[f"{buddy_id}:CHAR_root"]
    root.location, root.rotation_euler.z = at, yaw
    return root, bpy.data.objects[f"{buddy_id}:BuddyCtrl"], bpy.data.objects[f"{buddy_id}:EyeFocus"]


def camera(sc, loc, aim, lens, fstop=None, focus=None):
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    cam.location, cam.data.lens = Vector(loc), lens
    look_at(cam, Vector(aim))
    if fstop:
        cam.data.dof.use_dof, cam.data.dof.aperture_fstop = True, fstop
        cam.data.dof.focus_object = focus
    sc.camera = cam
    return cam


def label(sc, cam, text):
    """Caption in the bottom-left corner, parented to the camera so every tile reads the same."""
    w, h = sc.render.resolution_x, sc.render.resolution_y
    vfov_half = math.atan(18.0 / cam.data.lens) if h >= w else math.atan(18.0 / cam.data.lens * h / w)
    d = 0.3
    if cam.data.dof.use_dof and cam.data.dof.focus_object:  # at the focus distance, so depth of field keeps it sharp
        bpy.context.view_layer.update()
        fwd = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
        d = (cam.data.dof.focus_object.matrix_world.translation - cam.matrix_world.translation).dot(fwd)
    half_h = d * math.tan(vfov_half)
    half_w = half_h * w / h
    t = bpy.data.objects.new("Label", bpy.data.curves.new("Label", "FONT"))
    t.data.body, t.data.size = text, half_h * 0.075
    t.data.materials.append(mat("LabelMat", "#FFFFFF", emit=1.0))
    sc.collection.objects.link(t)
    t.parent = cam
    t.location = (-half_w * 0.92, half_h * (0.92 - 0.075), -d)  # top-left: in focus and never behind the desk


def set_ctrl(ctrl, values):
    for k, v in values.items():
        ctrl[k] = float(v)
    ctrl.update_tag()


def buddy_cam(sc, at, focus, lens=100, size_h=0.40):
    """The av_buddy set-up: long lens at desk height, buddy about 0.4 of frame height, eyes near 0.62 from the top,
    the hero's blurred torso landing upper right."""
    d = 0.14 / (size_h * 36.0 / lens)
    aim = Vector((at.x + 0.012, at.y, at.z + 0.082 + 0.12 * 0.36 * d * 100 / lens))
    return camera(sc, aim + Vector((-0.05, -d, d * math.tan(math.radians(4)))), aim, lens, 2.0, focus)


def render_to(sc, path):
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return load(path)


def sheet_lineup(out):
    sc = reset((1600, 900), 64)
    room(sc, True)
    for i, bid in enumerate(ORDER):
        place(bid, Vector((-0.42 + 0.28 * i, -0.44, DESK_Z)), yaw=0.0)
    focus = bpy.data.objects.new("Focus", None)
    sc.collection.objects.link(focus)
    focus.location = (0, -0.50, 0.82)
    cam = camera(sc, (0.0, -2.35, 1.05), (0, -0.30, 0.97), 50, 5.6, focus)
    label(sc, cam, "CLAUDE  /  CHATGPT  /  FIGMA  /  NOVA   (hero for scale)")
    save(render_to(sc, out / "_tiles" / "lineup.png"), out / "lineup.jpg")


def clip_pose(name):
    v = dict(acting.REST)
    peak = acting.CLIPS[name]["peak"]
    for c in acting.CLIPS[name]["keys"]:
        x = acting.clip_value(name, c, peak)
        v[c] = x if c in acting.STEPPED else (v[c] * x if c in acting.MULTIPLY else v[c] + x)
    v["phase"] = 1.0
    return v


def sheet_clips(out, bid="claude"):
    tiles = []
    for name in acting.CLIPS:
        sc = reset((420, 560), 48)
        room(sc, False)
        _, ctrl, eye = place(bid, MARK_B)
        set_ctrl(ctrl, clip_pose(name))
        cam = buddy_cam(sc, MARK_B, eye, size_h=0.42)
        label(sc, cam, name.upper())
        tiles.append(render_to(sc, out / "_tiles" / f"clip_{bid}_{name}.png"))
    save(grid(tiles, 4), out / f"clips_{bid}.jpg")


EYE_COLS = [("RECT", {}), ("HAPPY", {"eye_shape": 1}), ("SAD", {"eye_shape": 2}), ("WIDE", {"eye_shape": 3}),
            ("WINK", {"eye_shape": 4}), ("DRY", {"eye_h": 0.35}), ("BLINK", {"eye_h": 0.0}),
            ("SIGNATURE", {"sig": 1.0, "phase": 1.3})]


def sheet_eyes(out):
    tiles = []
    for bid in ORDER:
        for col, values in EYE_COLS:
            sc = reset((300, 360), 32)
            room(sc, False)
            _, ctrl, eye = place(bid, MARK_B)
            set_ctrl(ctrl, values)
            cam = buddy_cam(sc, MARK_B, eye, size_h=0.5)
            label(sc, cam, f"{bid.upper()} {col}")
            tiles.append(render_to(sc, out / "_tiles" / f"eyes_{bid}_{col.lower()}.png"))
    save(grid(tiles, len(EYE_COLS)), out / "eyes_signature.jpg")


def segments_for(bid):
    (t1, a1), (t2, a2) = LOOPS[bid]
    e1, e2 = acting.syllable_envelope(t1, FPS), acting.syllable_envelope(t2, FPS)
    s1 = 15
    s2 = s1 + len(e1) + 18
    return [{"start": s1, "end": s1 + len(e1), "speaking": True, "env": e1, "action": a1},
            {"start": s2, "end": min(180, s2 + len(e2)), "speaking": True, "env": e2, "action": a2}]


def loop(out, bid):
    sc = reset((540, 960), 24)
    room(sc, True)
    _, ctrl, eye = place(bid, MARK_B)
    tracks = acting.animate(180, FPS, segments_for(bid), seed=7, hero_side=1.0)
    for f in range(180):
        for c, vals in tracks.items():
            ctrl[c] = vals[f]
            ctrl.keyframe_insert(f'["{c}"]', frame=f + 1)
    for fc in ctrl.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT" if "eye_shape" in fc.data_path else "LINEAR"
    buddy_cam(sc, MARK_B, eye)
    sc.frame_start, sc.frame_end = 1, 180
    frames = out / "_frames" / bid
    frames.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(frames / "f_")
    bpy.ops.render.render(animation=True)
    print(f"loop {bid}: {frames}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(args[0]).resolve()
    (out / "_tiles").mkdir(parents=True, exist_ok=True)
    what = args[1] if len(args) > 1 else "lineup"
    if what == "lineup":
        sheet_lineup(out)
    elif what == "clips":
        sheet_clips(out, args[2] if len(args) > 2 else "claude")
    elif what == "eyes":
        sheet_eyes(out)
    elif what == "solo":  # quick close-up of one buddy for iteration: solo <id> [prop=value ...]
        sc = reset((420, 560), 32)
        room(sc, False)
        _, ctrl, eye = place(args[2], MARK_B)
        set_ctrl(ctrl, {k: float(v) for k, v in (x.split("=") for x in args[3:])})
        buddy_cam(sc, MARK_B, eye, size_h=0.55)
        render_to(sc, out / "_tiles" / f"solo_{args[2]}.png")
    elif what == "loop":
        loop(out, args[2])
    else:
        raise SystemExit(f"unknown sheet {what!r}")
