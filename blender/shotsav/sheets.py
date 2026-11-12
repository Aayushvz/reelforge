"""Evidence sheets for the Shots-AV hero (gate P1). Builds each variant in-process, renders tiles, and lays
them out with numpy, so one Blender run makes a whole sheet.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/shotsav/sheets.py -- <out_dir> [sheet ...]
Sheets: turnaround, expressions, mouth, purple, options, outfits (default: all). Also `one key=value ...` for a
single test still (view=front|34|side|back, shot=bust|head|desk, any hero dial, any FaceCtrl channel,
HandL/HandR/Lean)."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bl_common import EEVEE, look_at  # noqa: E402
from reelforge.face import EMOTION_POSES  # noqa: E402
from reelforge.visemes import VISEME_POSES  # noqa: E402
from shotsav import hero  # noqa: E402
from shotsav.geo import lin, mat, rbox  # noqa: E402

PURPLE = hero.BRAND["purple"]
# AgX turns a lit #7C3AED card pastel at every exposure (best dE 49); Khronos PBR Neutral keeps it (dE 2-9 on the
# jacket at -0.5 to -1.0). Measured with purple_sweep: see docs/production/shots-av/PROGRESS.md, Decisions.
VIEW = ("Khronos PBR Neutral", "None", -0.75)
# Key colours (linear RGB). The night key is the prompt's "about 4300 K, lightly desaturated".
KEYS = {"neutral_warm_4300K": (1.0, 0.85, 0.72), "screen_cool_7500K": (0.80, 0.90, 1.0),
        "daylight_5600K": (1.0, 0.96, 0.92)}
VIEWS = {"front": 0.0, "34": 32.0, "side": 90.0, "back": 180.0, "34r": -32.0}
SHOTS = {  # aim height, distance, lens
    "bust": (1.07, 2.25, 70), "head": (1.185, 1.55, 85), "desk": (0.99, 2.9, 60), "hands": (0.84, 1.3, 60),
    "mouth": (1.095, 0.62, 100)}


def scene(dials, face=None, pose=None, view="front", shot="bust", key="neutral_warm_4300K", size=(540, 800),
          label="", card=False, samples=48, desk=True, light="night"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    hero.build(**dials)
    ctrl, pc = bpy.data.objects["FaceCtrl"], bpy.data.objects["PoseCtrl"]
    for k, v in (face or {}).items():
        ctrl[k] = float(v)
    for k, v in (pose or {}).items():
        pc[k] = float(v)
    ctrl.update_tag()
    pc.update_tag()
    if desk:  # a plain stand-in desk so the hands have something to rest on (the real desk is P3's)
        rbox("PreviewDesk", (1.5, 0.75, 0.04), sc.collection, mat("PreviewDesk", "#3A2A22", rough=0.6), 0.006,
             (0, -0.52, 0.72))
    aim_z, dist, lens = SHOTS[shot]
    yaw = math.radians(VIEWS[view])
    aim = Vector((0, -0.04, aim_z))
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    cam.location = aim + Vector((math.sin(yaw), -math.cos(yaw), 0.07)) * dist
    cam.data.lens = lens
    look_at(cam, aim)
    sc.camera = cam

    def lamp(name, loc, energy, size_, color):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        o.data.energy, o.data.size, o.data.color = energy, size_, color
        o.location = Vector((0, 0, 1.15)) + Vector(loc)
        look_at(o, Vector((0, 0, 1.12)))
        sc.collection.objects.link(o)

    # key from the monitor side (the hero's left, screen right), low and in front; violet rim; navy fill
    lamp("Key", (1.15, -1.5, 0.35), 95, 1.0, KEYS[key])
    if light == "night":
        lamp("Rim", (-0.9, 1.3, 0.6), 110, 0.6, lin("#8B5CF6"))
        lamp("Fill", (-1.5, -1.0, 0.2), 16, 1.8, (0.55, 0.65, 1.0))
        lamp("Top", (0.2, 0.2, 1.4), 22, 1.2, (0.8, 0.85, 1.0))
        back, world = "#141A2E", (0.012, 0.015, 0.03)
    else:  # a plain bright studio, to judge form on the turnaround
        lamp("Rim", (-0.9, 1.3, 0.6), 80, 0.8, (1, 1, 1))
        lamp("Fill", (-1.5, -1.2, 0.3), 45, 2.0, (0.92, 0.95, 1.0))
        lamp("Top", (0.2, 0.0, 1.5), 40, 1.5, (1, 1, 1))
        back, world = "#8E8F96", (0.12, 0.12, 0.13)
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    bpy.context.active_object.data.materials.append(mat("Floor", back, rough=0.9))
    wall = bpy.data.objects.new("Backdrop", bpy.context.active_object.data.copy())
    sc.collection.objects.link(wall)
    wall.rotation_euler = (math.pi / 2, 0, yaw)
    wall.location = Vector((-math.sin(yaw), math.cos(yaw), 0)) * 2.4
    sc.world = bpy.data.worlds.new("W")
    sc.world.color = world
    marks = {}
    if card:  # a matte card of pure brand purple beside the jacket, lit by the same key
        c = rbox("PurpleCard", (0.16, 0.012, 0.16), sc.collection, mat("PurpleCard", PURPLE, rough=0.56), 0.004,
                 (0.36, -0.20, 0.96))
        c.rotation_euler = (0, 0, yaw * 0.9)
        marks = {"card": Vector((0.36, -0.215, 0.96)), "jacket_lit": Vector((0.105, -0.150, 0.86)),
                 "jacket_shadow": Vector((-0.120, -0.135, 0.86))}
    if label:
        txt = bpy.data.curves.new("Label", "FONT")
        txt.body, txt.size, txt.align_x = label, 0.0105, "LEFT"
        t = bpy.data.objects.new("Label", txt)
        t.data.materials.append(mat("LabelMat", "#FFFFFF", emit=1.0))
        sc.collection.objects.link(t)
        t.parent = cam
        aspect = size[1] / size[0]
        half_w = 0.5 * 36.0 / lens * 0.3 / max(1.0, aspect)
        t.location = (-half_w * 0.94, -half_w * aspect * 0.94, -0.3)
    sc.render.engine = EEVEE
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_raytracing = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure = VIEW
    sc.render.image_settings.file_format = "PNG"
    return sc, cam, marks


def render(path, **kw):
    sc, cam, marks = scene(**kw)
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    px = {}
    for name, p in marks.items():
        co = world_to_camera_view(sc, cam, p)
        px[name] = (co.x, co.y)
    return px


def load(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)  # bottom row first, display-referred values


def save(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new("sheet", w, h, alpha=False)
    img.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    img.filepath_raw, img.file_format = str(path), "JPEG"
    bpy.context.scene.render.image_settings.quality = 92
    img.save()
    bpy.data.images.remove(img)
    print(f"sheet {path} {w}x{h}")


def grid(tiles, cols, gap=6, bg=(0.035, 0.035, 0.045)):
    rows = math.ceil(len(tiles) / cols)
    h, w = tiles[0].shape[:2]
    out = np.ones((rows * h + (rows + 1) * gap, cols * w + (cols + 1) * gap, 4), np.float32)
    out[..., :3] = bg
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        y0 = out.shape[0] - (r + 1) * (h + gap)  # arrays are bottom-up; the first tile goes top-left
        out[y0:y0 + h, gap + c * (w + gap):gap + c * (w + gap) + w] = t
    return out


def tiles_of(out, name, specs):
    done = []
    for i, kw in enumerate(specs):
        p = out / "_tiles" / f"{name}_{i:02d}.png"
        render(p, **kw)
        done.append(load(p))
    return done


def lab(rgb):
    """sRGB (0..1, display-referred) -> CIE L*a*b* (D65)."""
    c = np.asarray(rgb, float)
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    x, y, z = (m @ c) / np.array([0.95047, 1.0, 1.08883])
    f = lambda t: np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)  # noqa: E731
    return np.array([116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))])


def hex_of(rgb):
    return "#" + "".join(f"{round(min(1, max(0, float(v))) * 255):02X}" for v in rgb[:3])


def sheet_turnaround(out):
    specs = [{"dials": {}, "view": v, "shot": "desk", "size": (600, 800), "label": lab, "light": light}
             for light in ("studio", "night")
             for v, lab in (("front", "FRONT"), ("34", "THREE-QUARTER"), ("side", "SIDE"))]
    save(grid(tiles_of(out, "turn", specs), 3), out / "turnaround.jpg")


EXPRESSIONS = [("neutral", {}), *[(k, EMOTION_POSES[k]) for k in (
    "happy", "sad", "worried", "surprised", "smug", "deadpan", "confused", "annoyed", "thinking", "embarrassed")],
    ("blink", {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0})]


def sheet_expressions(out):
    specs = [{"dials": {}, "face": ch, "view": "34" if i % 2 else "front", "shot": "head", "size": (480, 480),
              "label": name.upper()} for i, (name, ch) in enumerate(EXPRESSIONS)]
    save(grid(tiles_of(out, "expr", specs), 4), out / "expressions.jpg")


def sheet_mouth(out):
    names = [("rest", "sil"), ("closed MBP", "MBP"), ("small open (L, N, T)", "LNT"), ("wide open (AA)", "AA"),
             ("O (OH)", "OH"), ("E / smile-open (EE)", "EE"), ("F / V", "FV")]
    specs = [{"dials": {"glasses": "none"}, "face": VISEME_POSES[v], "shot": "mouth", "size": (400, 400),
              "label": n.upper()} for n, v in names]
    specs.append({"dials": {"glasses": "none"}, "face": {"mouthSmileLeft": 0.9, "mouthSmileRight": 0.9},
                  "shot": "mouth", "size": (400, 400), "label": "SMILE CLOSED"})
    save(grid(tiles_of(out, "mouth", specs), 4), out / "mouth_shapes.jpg")


def sheet_purple(out):
    tiles, report = [], {"target": PURPLE, "view": list(VIEW)}
    for key in KEYS:
        p = out / "_tiles" / f"purple_{key}.png"
        px = render(p, dials={}, view="34", shot="bust", key=key, size=(720, 960), card=True, samples=48,
                    label=key.replace("_", " ").upper())
        t = load(p)
        h, w = t.shape[:2]
        report[key] = {}
        for name, (u, v) in px.items():
            x, y = int(u * w), int(v * h)
            patch = t[max(0, y - 7):y + 8, max(0, x - 7):x + 8, :3].reshape(-1, 3).mean(0)
            target = np.array([int(PURPLE[i:i + 2], 16) / 255 for i in (1, 3, 5)])
            report[key][name] = {"hex": hex_of(patch), "dE76": round(float(np.linalg.norm(lab(patch) - lab(target))), 1)}
            t[max(0, y - 9):y + 10, max(0, x - 9), :3] = 1.0  # tick marks where the samples were read
            t[max(0, y - 9):y + 10, min(w - 1, x + 9), :3] = 1.0
        s = 120  # a flat chip of the exact sRGB value, top right
        t[h - 20 - s:h - 20, w - 20 - s:w - 20, :3] = [int(PURPLE[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        tiles.append(t)
    save(grid(tiles, 3), out / "purple_check.jpg")
    (out / "purple_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def sheet_options(out):
    specs = [{"dials": {"skin": s}, "shot": "head", "view": "34", "size": (400, 440), "label": f"SKIN: {s.upper()}"}
             for s in hero.SKINS]
    specs += [{"dials": {"hair": h}, "shot": "head", "view": v, "size": (400, 440), "label": f"HAIR: {h.upper()}"}
              for h in hero.HERO["hair"]["options"] for v in ("34", "34r")]
    save(grid(tiles_of(out, "opt", specs), 6), out / "options_skin_hair.jpg")


def sheet_outfits(out):
    specs = [
        {"dials": {"outfit": "puffer"}, "pose": {"HandL": 1}, "label": "PUFFER / THINK"},
        {"dials": {"outfit": "hoodie"}, "pose": {}, "label": "HOODIE / REST"},
        {"dials": {"outfit": "overshirt"}, "pose": {"HandR": 2}, "label": "OVERSHIRT / POINT"},
        {"dials": {"outfit": "puffer", "headphones": "on", "chest_mark": True}, "pose": {"HandL": 3, "HandR": 3},
         "label": "PUFFER / OPEN / PHONES ON"},
        {"dials": {"outfit": "hoodie", "glasses": "rect"}, "pose": {"HandL": 4, "HandR": 4},
         "label": "HOODIE / TYPE / RECT"},
        {"dials": {"outfit": "overshirt", "glasses": "none", "headphones": "none"}, "pose": {"HandL": 1},
         "label": "OVERSHIRT / NO GLASSES"},
    ]
    for s in specs:
        s.update(view="34", shot="desk", size=(600, 800))
    save(grid(tiles_of(out, "outfit", specs), 3), out / "outfits_poses.jpg")


SHEETS = {"turnaround": sheet_turnaround, "expressions": sheet_expressions, "mouth": sheet_mouth,
          "purple": sheet_purple, "options": sheet_options, "outfits": sheet_outfits}

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    out_dir = Path(args[0]).resolve()  # Blender reads a relative render path from the drive root
    (out_dir / "_tiles").mkdir(parents=True, exist_ok=True)
    if len(args) > 1 and args[1] == "one":
        kv = dict(a.split("=", 1) for a in args[2:])
        name = kv.pop("name", "one")
        opts = {k: kv.pop(k) for k in ("view", "shot", "key", "light") if k in kv}
        size = tuple(int(v) for v in kv.pop("size", "540x800").split("x"))
        pose = {k: float(kv.pop(k)) for k in ("HandL", "HandR", "Lean") if k in kv}
        dials = {k: kv.pop(k) for k in list(kv) if k in hero.DEFAULTS}
        for k, v in dials.items():
            if isinstance(hero.DEFAULTS[k], (bool, float)):
                dials[k] = type(hero.DEFAULTS[k])(float(v))
        render(out_dir / "_tiles" / f"{name}.png", dials=dials, face={k: float(v) for k, v in kv.items()},
               pose=pose, size=size, **opts)
    else:
        for name in args[1:] or list(SHEETS):
            SHEETS[name](out_dir)
