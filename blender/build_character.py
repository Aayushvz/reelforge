"""Build the stylized base character → <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/build_character.py -- <out.blend>
Contract: collection CHAR_base; empties CHAR_root, Head, FaceCtrl (52 ARKit custom props).
Everything on the face is driven from FaceCtrl so a pro ARKit head can replace this later."""
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bl_common import ellipsoid, empty, material  # noqa: E402
from reelforge.arkit import ARKIT_NAMES  # noqa: E402

OUT = Path(sys.argv[sys.argv.index("--") + 1])
HEAD_Z = 1.12  # neck pivot

bpy.ops.wm.read_factory_settings(use_empty=True)
COLL = bpy.data.collections.new("CHAR_base")
bpy.context.scene.collection.children.link(COLL)

SKIN = material("Skin", (0.95, 0.68, 0.55), rough=0.45, sss=0.35)
EYE = material("EyeBlack", (0.01, 0.01, 0.012), rough=0.15, coat=1.0)
CATCH = material("Catchlight", (1.0, 1.0, 1.0), emit=6.0)
BROW = material("Brow", (0.07, 0.04, 0.03), rough=0.6)
MOUTH = material("Mouth", (0.16, 0.04, 0.05), rough=0.5)
BLUSH = material("Blush", (0.95, 0.45, 0.42), rough=0.6, sss=0.2)
HAIR = material("Hair", (0.06, 0.035, 0.025), rough=0.4, coat=0.3)
HOODIE = material("Hoodie", (1.0, 0.68, 0.08), rough=0.75, sheen=0.6)
SHIRT = material("Shirt", (0.02, 0.02, 0.025), rough=0.8, sheen=0.3)
METAL = material("GlassesMetal", (0.03, 0.03, 0.035), rough=0.25, metal=0.9)

ROOT = empty("CHAR_root", (0, 0, 0), COLL)
HEAD = empty("Head", (0, 0, HEAD_Z), COLL, parent=ROOT)
CTRL = empty("FaceCtrl", (0, 0, 0.3), COLL, parent=HEAD)
for n in ARKIT_NAMES:
    CTRL[n] = 0.0


def on_head(o):
    o.location.z -= HEAD_Z
    o.parent = HEAD
    return o


def on_root(o):
    o.parent = ROOT
    return o


def drive(owner, path, expr, vars_, index=None):
    fc = owner.driver_add(path) if index is None else owner.driver_add(path, index)
    d = fc.driver
    d.type = "SCRIPTED"
    d.expression = expr
    for vname, prop in vars_.items():
        v = d.variables.new()
        v.name = vname
        v.type = "SINGLE_PROP"
        v.targets[0].id_type = "OBJECT"
        v.targets[0].id = CTRL
        v.targets[0].data_path = f'["{prop}"]'


# --- head ---------------------------------------------------------------
on_head(ellipsoid("HeadMesh", (0, 0, 1.30), (0.20, 0.19, 0.216), COLL, SKIN, subd=2))
on_head(ellipsoid("Nose", (0, -0.205, 1.28), (0.018, 0.016, 0.016), COLL, SKIN))
for side, sx in (("Left", 1), ("Right", -1)):
    on_head(ellipsoid(f"Blush{side}", (0.12 * sx, -0.155, 1.245), (0.035, 0.01, 0.022), COLL, BLUSH))
    eye = on_head(ellipsoid(f"Eye{side}", (0.07 * sx, -0.185, 1.31), (0.0224, 0.014, 0.035), COLL, EYE))
    drive(eye, "scale", "0.035*(1-0.95*b)*(1+0.25*w)*(1-0.3*s)",
          {"b": f"eyeBlink{side}", "w": f"eyeWide{side}", "s": f"eyeSquint{side}"}, index=2)
    cl = on_head(ellipsoid(f"Catch{side}", (0.07 * sx + 0.008, -0.2, 1.325), (0.007, 0.007, 0.007),
                           COLL, CATCH, subd=0))
    for axis in range(3):
        drive(cl, "scale", "0.007*(1-0.95*b)", {"b": f"eyeBlink{side}"}, index=axis)
    brow = on_head(ellipsoid(f"Brow{side}", (0.075 * sx, -0.19, 1.39), (0.032, 0.008, 0.007), COLL, BROW))
    drive(brow, "delta_location", "0.025*i+0.02*o-0.018*d",
          {"i": "browInnerUp", "o": f"browOuterUp{side}", "d": f"browDown{side}"}, index=2)
    # positive y-rotation on +X brow lifts its inner end; mirror for the right brow
    drive(brow, "rotation_euler", f"{sx}*(0.35*i-0.25*o+0.3*d)",
          {"i": "browInnerUp", "o": f"browOuterUp{side}", "d": f"browDown{side}"}, index=1)

# --- glasses --------------------------------------------------------------
for sx in (1, -1):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.052, minor_radius=0.004,
                                     location=(0.075 * sx, -0.208, 1.31), rotation=(math.pi / 2, 0, 0))
    ring = bpy.context.active_object
    bpy.context.scene.collection.objects.unlink(ring)
    COLL.objects.link(ring)
    ring.data.materials.append(METAL)
    on_head(ring)
bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=0.05, location=(0, -0.212, 1.315),
                                    rotation=(0, math.pi / 2, 0))
bridge = bpy.context.active_object
bpy.context.scene.collection.objects.unlink(bridge)
COLL.objects.link(bridge)
bridge.data.materials.append(METAL)
on_head(bridge)

# --- mouth: flat ellipse with ARKit shape keys ------------------------------
N = 24
W, H = 0.035, 0.004


def mouth_shape(fn):
    """fn(c, s) -> (x, z) in mouth-local space for ring vertex at angle with cos=c, sin=s."""
    ring = [fn(math.cos(2 * math.pi * i / N), math.sin(2 * math.pi * i / N)) for i in range(N)]
    cx = sum(p[0] for p in ring) / N
    cz = sum(p[1] for p in ring) / N
    return [(cx, cz)] + ring


SHAPES = {
    "jawOpen": lambda c, s: (0.032 * c, 0.006 * s if s > 0 else 0.045 * s),
    "mouthFunnel": lambda c, s: (0.022 * c, 0.016 * s),
    "mouthPucker": lambda c, s: (0.012 * c, 0.010 * s),
    "mouthClose": lambda c, s: (W * c, 0.0015 * s),
    "mouthSmileLeft": lambda c, s: (W * c + 0.004 * max(0, c), H * s + 0.012 * max(0, c) ** 3),
    "mouthSmileRight": lambda c, s: (W * c - 0.004 * max(0, -c), H * s + 0.012 * max(0, -c) ** 3),
    "mouthFrownLeft": lambda c, s: (W * c, H * s - 0.010 * max(0, c) ** 3),
    "mouthFrownRight": lambda c, s: (W * c, H * s - 0.010 * max(0, -c) ** 3),
    "mouthStretchLeft": lambda c, s: (W * c + 0.008 * max(0, c), H * s),
    "mouthStretchRight": lambda c, s: (W * c - 0.008 * max(0, -c), H * s),
    "mouthPressLeft": lambda c, s: (W * c, H * s * (1 - 0.75 * max(0, c))),
    "mouthPressRight": lambda c, s: (W * c, H * s * (1 - 0.75 * max(0, -c))),
    "mouthRollLower": lambda c, s: (W * c, H * s if s > 0 else 0.25 * H * s),
    "mouthLeft": lambda c, s: (W * c + 0.01, H * s),
    "mouthRight": lambda c, s: (W * c - 0.01, H * s),
}
base_pts = mouth_shape(lambda c, s: (W * c, H * s))
bm = bmesh.new()
verts = [bm.verts.new((x, 0.0, z)) for x, z in base_pts]
for i in range(N):
    bm.faces.new((verts[0], verts[1 + i], verts[1 + (i + 1) % N]))
me = bpy.data.meshes.new("Mouth")
bm.to_mesh(me)
bm.free()
me.materials.append(MOUTH)
mouth = bpy.data.objects.new("Mouth", me)
COLL.objects.link(mouth)
mouth.location = (0, -0.186, 1.235)
on_head(mouth)
mouth.shape_key_add(name="Basis")
for name, fn in SHAPES.items():
    kb = mouth.shape_key_add(name=name, from_mix=False)
    for i, (x, z) in enumerate(mouth_shape(fn)):
        kb.data[i].co = (x, 0.0, z)
    drive(kb, "value", "v", {"v": name})

# --- hair (metaballs → mesh) -------------------------------------------------
mb = bpy.data.metaballs.new("HairMB")
mb.resolution = 0.02
mb.render_resolution = 0.012
for co, r, size in (((0, 0.02, 1.36), 0.25, (1.0, 1.0, 0.9)),
                    ((0.17, 0.03, 1.15), 0.12, (0.6, 0.8, 2.2)),
                    ((-0.17, 0.03, 1.15), 0.12, (0.6, 0.8, 2.2)),
                    ((0, 0.12, 1.12), 0.2, (1.0, 0.5, 1.6)),
                    ((0, -0.12, 1.47), 0.14, (1.2, 0.55, 0.45))):
    el = mb.elements.new()
    el.type = "ELLIPSOID"
    el.co = co
    el.radius = r
    el.size_x, el.size_y, el.size_z = size
hair_mb = bpy.data.objects.new("HairMB", mb)
bpy.context.scene.collection.objects.link(hair_mb)
bpy.context.view_layer.objects.active = hair_mb
hair_mb.select_set(True)
bpy.ops.object.convert(target="MESH")
hair = bpy.context.active_object
hair.name = "Hair"
bpy.context.scene.collection.objects.unlink(hair)
COLL.objects.link(hair)
hair.data.materials.clear()
hair.data.materials.append(HAIR)
for p in hair.data.polygons:
    p.use_smooth = True
on_head(hair)

# --- body ---------------------------------------------------------------
on_root(ellipsoid("Neck", (0, 0.0, 1.08), (0.05, 0.05, 0.08), COLL, SKIN))
on_root(ellipsoid("Torso", (0, 0.03, 0.88), (0.26, 0.18, 0.30), COLL, HOODIE, subd=2))
on_root(ellipsoid("Shirt", (0, -0.1, 0.96), (0.11, 0.09, 0.16), COLL, SHIRT))
for sx in (1, -1):
    on_root(ellipsoid(f"Arm{sx}", (0.22 * sx, -0.12, 0.84), (0.07, 0.2, 0.07), COLL, HOODIE, subd=2))
    on_root(ellipsoid(f"Hand{sx}", (0.18 * sx, -0.36, 0.8), (0.045, 0.05, 0.035), COLL, SKIN))

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(f"saved {OUT}")
