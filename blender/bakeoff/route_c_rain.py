"""Phase 1 bake-off, route (c): restyle Blender Studio's CC-BY Rain v3 rig into Kai.

Run (from the repo root; the source is third-party, so auto-run scripts stay off):
  "$(cat tools/blender_path.txt)" -b --disable-autoexec "tools/third_party/rain_v3/Rain v3.3/rain_v3.2.blend" \
      --python-exit-code 1 -P blender/bakeoff/route_c_rain.py -- assets/build/bakeoff/kai_c.blend

Stages: clean up -> restyle the rest meshes with one smooth field -> pose recipes on Rain's bone-driven face are
baked into 52 ARKit shape keys per face part -> A-pose, long neck, Kai look (skin, stubble, hair, outfit, jewellery)
-> the character contract (CHAR_base, CHAR_root, Head, FaceCtrl, FaceAnchor, EyeFocus, face_part tags).
The source file is only read; this script saves a new file."""
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

T0 = time.time()
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(args[0]).resolve() if args else Path("kai_c.blend").resolve()
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from reelforge.arkit import ARKIT_NAMES  # noqa: E402  (stdlib-only module; read, not edited)

DEV = "--dev" in args  # dev: stop after the bake and skip the look (not used for deliverables)


def log(*a):
    print(f"[route_c {time.time() - T0:6.1f}s]", *a, flush=True)


# ===================================================================================================
# Pose recipes on Rain's face controls. bone -> (lx, ly, lz, rx, ry, rz); metres and degrees, bone-local.
# Local axes of the face controls: X lateral (+ = outward on .L), Y up, Z toward the viewer (-Y world).
# "{S}" in a name = Left/Right pair ("{s}" in a bone = .L/.R of that side); "{s}" in a centred name = both sides.
# ===================================================================================================
H = 0.5  # centre bones appear in both halves of a split shape at half weight
RECIPES = {
    "eyeBlink{S}": {"ACT-Eyelid_Upper{s}": (0, -0.03, 0), "ACT-Eyelid_Lower{s}": (0, 0.012, 0)},
    "eyeLookDown{S}": {"TGT-Eye{s}": (0, -0.22, 0)},
    "eyeLookUp{S}": {"TGT-Eye{s}": (0, 0.2, 0)},
    "eyeLookIn{S}": {"TGT-Eye{s}": (0, 0, -0.22)},
    "eyeLookOut{S}": {"TGT-Eye{s}": (0, 0, 0.26)},
    "eyeSquint{S}": {"ACT-Eyelid_Lower{s}": (0, 0.01, 0), "ACT-Cheek_Outer{s}": (0, 0.02, 0),
                     "ACT-Eyering_Lower{s}": (0, 0.008, 0)},
    "eyeWide{S}": {"ACT-Eyelid_Upper{s}": (0, 0.02, 0), "ACT-Eyelid_Lower{s}": (0, -0.01, 0)},
    "jawForward": {"MSTR-Jaw": (0, 0.019, -0.0094, 0, 0, 0)},
    "jawLeft": {"MSTR-Jaw": (0, 0, 0, 0, 0, -9)},
    "jawRight": {"MSTR-Jaw": (0, 0, 0, 0, 0, 9)},
    "jawOpen": {"MSTR-Jaw": (0, 0, 0, 22, 0, 0)},
    "mouthClose": {"MSTR-UpperLip": (0, -0.012, 0), "MSTR-LowerLip": (0, 0.03, 0)},
    "mouthFunnel": {"ACT-Lip_Roll_Upper": (0, 0, 0, -10, 0, 0), "ACT-Lip_Roll_Lower": (0, 0, 0, -10, 0, 0),
                    "ACT-Lips_Corner{s}": (-0.006, 0, -0.018), "SK-Lip_Puff_Upper": (0, 0.004, 0),
                    "SK-Lip_Puff_Lower": (0, 0.004, 0), "MSTR-UpperLip": (0, 0.004, 0.003),
                    "MSTR-LowerLip": (0, -0.004, 0.003), "MSTR-Jaw": (0, 0, 0, 6, 0, 0)},
    "mouthPucker": {"ACT-Lips_Corner{s}": (-0.006, 0, -0.02), "MSTR-UpperLip": (0, 0, 0.004),
                    "MSTR-LowerLip": (0, 0, 0.004), "ACT-Lip_Roll_Upper": (0, 0, 0, -5, 0, 0),
                    "ACT-Lip_Roll_Lower": (0, 0, 0, -5, 0, 0)},
    "mouthLeft": {"MSTR-Mouth": (0.012, 0, 0)},
    "mouthRight": {"MSTR-Mouth": (-0.012, 0, 0)},
    "mouthSmile{S}": {"ACT-Lips_Corner{s}": (0, 0.028, 0.004), "ACT-Cheek_Outer{s}": (0, 0.005, 0)},
    "mouthFrown{S}": {"ACT-Lips_Corner{s}": (0, -0.03, 0)},
    "mouthDimple{S}": {"ACT-Lips_Corner{s}": (0.011, 0.004, 0.003)},
    "mouthStretch{S}": {"ACT-Lips_Corner{s}": (0.005, -0.005, 0.04), "GRP-Lip_Bot_1{s}": (0, -0.004, 0)},
    "mouthRollLower": {"ACT-Lip_Roll_Lower": (0, 0, 0, 40, 0, 0)},
    "mouthRollUpper": {"ACT-Lip_Roll_Upper": (0, 0, 0, 40, 0, 0)},
    "mouthShrugLower": {"MSTR-LowerLip": (0, 0.012, 0.004)},
    "mouthShrugUpper": {"MSTR-UpperLip": (0, 0.008, 0)},
    "mouthPress{S}": {"GRP-Lip_Top_1{s}": (0, -0.003, 0), "GRP-Lip_Top_2{s}": (0, -0.003, 0),
                      "GRP-Lip_Bot_1{s}": (0, 0.003, 0), "GRP-Lip_Bot_2{s}": (0, 0.003, 0),
                      "GRP-Lip_Top.M": (0, -0.003 * H, 0), "GRP-Lip_Bot.M": (0, 0.003 * H, 0)},
    "mouthLowerDown{S}": {"GRP-Lip_Bot_1{s}": (0, -0.01, 0), "GRP-Lip_Bot_2{s}": (0, -0.01, 0),
                          "GRP-Lip_Bot.M": (0, -0.01 * H, 0)},
    "mouthUpperUp{S}": {"GRP-Lip_Top_1{s}": (0, 0.01, 0), "GRP-Lip_Top_2{s}": (0, 0.01, 0),
                        "GRP-Lip_Top.M": (0, 0.01 * H, 0)},
    "browDown{S}": {"MSTR-Eyebrow{s}": (-0.008, -0.02, 0)},
    "browInnerUp": {"GRP-Eyebrow_4{s}": (0, 0.02, 0), "GRP-Eyebrow_3{s}": (0, 0.012, 0)},
    "browOuterUp{S}": {"GRP-Eyebrow_1{s}": (0, 0.02, 0), "GRP-Eyebrow_2{s}": (0, 0.015, 0),
                       "GRP-Eyebrow_3{s}": (0, 0.006, 0)},
    "cheekPuff": {"SK-Cheek_Puff{s}": (0, 0.02, 0)},
    "cheekSquint{S}": {"ACT-Cheek_Outer{s}": (0, 0.03, 0), "ACT-Cheek_Inner{s}": (0, 0.01, 0)},
    "noseSneer{S}": {"ACT-Sneer{s}": (0, 0.02, 0)},
    "tongueOut": {"Tongue_Root": (0, 0, 0.02), "MSTR-Jaw": (0, 0, 0, 9, 0, 0)},
}
BASE = {"mouthClose": "jawOpen"}  # this shape is baked on top of the base shape's pose
# Kai's resting face (baked into the neutral mesh): heavy-lidded, brows low and level, mouth relaxed.
NEUTRAL = {"ACT-Eyelid_Upper{s}": (0, -0.004, 0), "MSTR-Eyebrow{s}": (-0.002, -0.003, 0)}


def expand(name, table):
    """Bones -> 6-tuple for ARKit `name` from a recipe table (centred names use both sides)."""
    for pat, bones in table.items():
        out = {}
        if "{S}" in pat:
            suf = {"Left": ".L", "Right": ".R"}
            hit = [s for k, s in suf.items() if pat.replace("{S}", k) == name]
            if not hit:
                continue
            for b, v in bones.items():
                out[b.replace("{s}", hit[0])] = tuple(v) + (0,) * (6 - len(v))
        elif pat == name:
            for b, v in bones.items():
                v = tuple(v) + (0,) * (6 - len(v))
                for suf in ((".L", ".R") if "{s}" in b else ("",)):
                    out[b.replace("{s}", suf)] = v
        else:
            continue
        return out
    raise KeyError(name)


# ===================================================================================================
# 1. clean up the source
# ===================================================================================================
rig = bpy.data.objects["RIG-rain"]
sc = bpy.context.scene
arm = rig.data


def kill(o):
    bpy.data.objects.remove(o, do_unlink=True)


for n in ("GEO-rain-hair_main", "GEO-rain-hair_ponytail", "GEO-rain-hair_strand", "GEO-rain-hairband", "GEO-rain-top",
          "GEO-rain-scarf", "GEO-rain-body_nomask", "GEO-rain-eyes_viewport"):
    kill(bpy.data.objects[n])
for pb in rig.pose.bones:  # widgets are only bone display shapes
    pb.custom_shape = None
for o in [o for o in bpy.data.objects if o.name.startswith("WGT")]:
    kill(o)
for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA")]:
    kill(o)
for pb in rig.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_euler = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.scale = (1, 1, 1)
for mod_owner in bpy.data.objects:
    for m in mod_owner.modifiers:
        if m.type == "SUBSURF":
            m.show_viewport = False  # viewport level is 0 anyway; keeps evaluations at base-mesh vertex counts
bpy.context.view_layer.update()


# ===================================================================================================
# 2. restyle the rest meshes with one smooth field (every face part gets the same field, so they stay fitted)
# ===================================================================================================
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def bump(x, c, w):
    """Smooth 0..1 bump centred on c, half-width w."""
    return sstep(c - w, c, x) * (1 - sstep(c, c + w, x))


EYE_C = np.array([0.047, -0.089, 1.474])  # eyeball centre of Rain (left; mirrored for the right)
EYE_K = 0.88                               # Kai's eyes are smaller than Rain's
CHIN_Z0, EYE_Z = 1.345, 1.47
LENGTHEN = 0.20                            # lower face gets 20% longer (below the eye line)
JAW_W, HEAD_X = 0.30, 0.92


def face_field(P):
    """Rain's cute round head -> an adult male's long, squarer one. P: (n,3) rest positions. Keeps x = 0 fixed."""
    x, y, z = P[:, 0].copy(), P[:, 1].copy(), P[:, 2].copy()
    ax = np.abs(x)
    X, Y, Z = x.copy(), y.copy(), z.copy()
    up = sstep(1.30, 1.40, z)                                   # 0 in the neck, 1 on the face
    # narrower cheeks, a wider chin and jaw angle: half-width multiplier by height (Rain's face is round and baby-cheeked)
    fx = np.interp(z, [1.30, 1.345, 1.38, 1.40, 1.42, 1.44, 1.46, 1.50, 1.55, 1.60],
                   [1.0, 1.22, 1.14, 1.08, 0.95, 0.88, 0.85, 0.87, 0.90, 0.93])
    X = x * fx
    # eye region: smaller, deeper-set eyes (uniform shrink about each eyeball centre, smooth falloff)
    for sgn in (1.0, -1.0):
        c = EYE_C * np.array([sgn, 1, 1])
        d = np.linalg.norm(P - c, axis=1)
        w = 1 - sstep(0.042, 0.10, d)
        k = 1 - w * (1 - EYE_K)
        X = X + (x - c[0]) * (k - 1) * (np.sign(x) == sgn)
        Y = Y + (y - c[1]) * (k - 1) * (np.sign(x) == sgn) * 0.85
        Z = Z + (z - c[2]) * (k - 1) * (np.sign(x) == sgn)
    # long lower face (monotonic: below the chin the neck just moves down rigidly)
    Z = Z - LENGTHEN * (EYE_Z - np.clip(z, CHIN_Z0, EYE_Z)) * (z < 1.55)
    # chin: forward and squarer
    Y = Y - 0.015 * bump(z, 1.352, 0.03) * sstep(-0.12, -0.15, y) * (1 - sstep(0.03, 0.07, ax))
    # cheekbones out, hollow under them
    cb = bump(z, 1.458, 0.035) * bump(ax, 0.10, 0.05) * sstep(-0.05, -0.12, y)
    X = X + np.sign(x) * 0.006 * cb
    Y = Y - 0.004 * cb
    hol = bump(z, 1.415, 0.03) * bump(ax, 0.095, 0.045) * sstep(-0.04, -0.11, y)
    X = X - np.sign(x) * 0.011 * hol
    # brow ridge shelf
    br = bump(z, 1.508, 0.022) * sstep(-0.12, -0.145, y) * (1 - sstep(0.07, 0.12, ax))
    Y = Y - 0.007 * br
    # nose: longer, broader, higher bridge
    nz = bump(z, 1.43, 0.04) * sstep(-0.14, -0.155, y) * (1 - sstep(0.035, 0.06, ax))
    X = X + x * 0.12 * nz
    tip = bump(z, 1.418, 0.02) * (1 - sstep(0.015, 0.03, ax)) * sstep(-0.15, -0.165, y)
    Y = Y - 0.007 * tip
    br2 = bump(z, 1.468, 0.022) * (1 - sstep(0.008, 0.02, ax)) * sstep(-0.145, -0.152, y)
    Y = Y - 0.004 * br2
    # wider, thinner-lipped mouth
    mw = bump(z, 1.392, 0.025) * sstep(-0.10, -0.13, y) * (1 - sstep(0.04, 0.07, ax))
    X = X + x * 0.10 * mw
    lp = bump(z, 1.392, 0.022) * sstep(-0.10, -0.125, y) * (1 - sstep(0.04, 0.065, ax))
    Z = Z - (z - 1.392) * 0.16 * lp
    # thicker neck (head-mesh neck piece), about the neck axis
    nk = (1 - sstep(1.335, 1.36, z)) * (1 - sstep(0.07, 0.10, np.hypot(x, y + 0.03)))
    X = X + x * 0.18 * nk
    Y = Y + (y + 0.03) * 0.18 * nk
    return np.stack([X, Y, Z], axis=1)


def apply_field(obj, fn):
    """Apply fn to the base mesh and to every shape-key block (shape keys are absolute positions)."""
    me = obj.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    me.vertices.foreach_set("co", fn(co.reshape(-1, 3).astype(np.float64)).astype(np.float32).ravel())
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            kb.data.foreach_get("co", co)
            kb.data.foreach_set("co", fn(co.reshape(-1, 3).astype(np.float64)).astype(np.float32).ravel())
    me.update()


def brow_field(P):
    """Thicker, straighter, lower brows (the half-brow mesh is mirrored, so x = 0 stays put)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    zc = 1.508
    Z = zc + (z - zc) * 1.30 - 0.0030
    Z = Z - 0.35 * np.clip(z - 1.512, 0, None) * sstep(0.03, 0.07, np.abs(x))  # flatten the arch
    return np.stack([x, y, Z], axis=1)


FACE_OBJS = ["GEO-rain-head", "GEO-rain-eyes", "GEO-rain-eye_cornea", "GEO-rain-eye_dots", "GEO-rain-eyebrows",
             "GEO-rain-eyelashes", "GEO-rain-gums_upper", "GEO-rain-gums_lower", "GEO-rain-tongue"]
for n in FACE_OBJS:
    o = bpy.data.objects[n]
    assert o.matrix_world == Matrix.Identity(4) or (o.matrix_world - Matrix.Identity(4)).median_scale < 1e-6, n
    apply_field(o, face_field)
apply_field(bpy.data.objects["GEO-rain-eyebrows"], brow_field)
bpy.context.view_layer.update()
log("restyled face parts")

# ===================================================================================================
# 3. bake the 52 ARKit shapes from the bone-driven face
# ===================================================================================================
TOUCHED = set()


def set_pose(*stack):
    """Reset every bone we ever touched, then add each recipe (dict bone -> 6-tuple, with weight)."""
    for b in TOUCHED:
        pb = rig.pose.bones[b]
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
    for recipe, w in stack:
        for b, v in recipe.items():
            pb = rig.pose.bones[b]
            TOUCHED.add(b)
            pb.location = [pb.location[i] + v[i] * w for i in range(3)]
            pb.rotation_euler = [pb.rotation_euler[i] + math.radians(v[3 + i]) * w for i in range(3)]
    bpy.context.view_layer.update()


def eval_pos(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    a = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", a)
    ev.to_mesh_clear()
    return a.reshape(-1, 3)


def neutral_stack():
    nr = {}
    for b, v in NEUTRAL.items():
        for suf in ((".L", ".R") if "{s}" in b else ("",)):
            nr[b.replace("{s}", suf)] = tuple(v) + (0,) * (6 - len(v))
    return nr


NEUT = neutral_stack()
BAKE_PARTS = {"GEO-rain-head": "head", "GEO-rain-eyebrows": "brow", "GEO-rain-eyelashes": "lash",
              "GEO-rain-gums_upper": "teeth", "GEO-rain-gums_lower": "teeth", "GEO-rain-tongue": "tongue"}
SHORT = {"GEO-rain-head": "Head_geo", "GEO-rain-eyebrows": "Brows", "GEO-rain-eyelashes": "Lashes",
         "GEO-rain-gums_upper": "Teeth_upper", "GEO-rain-gums_lower": "Teeth_lower", "GEO-rain-tongue": "Tongue"}
EYE_PARTS = ["GEO-rain-eyes", "GEO-rain-eye_cornea"]
INNER = {"teeth": ["GEO-rain-gums_upper", "GEO-rain-gums_lower"], "tongue": ["GEO-rain-tongue"]}
# mouthClose is "lips sealed relative to the jaw": it needs the jaw open to show (a little shows without)
CLOSE_FLOOR = 0.0
# the combinations face_check tries (value 1 each); we add corrective shape keys where they would poke through
COMBOS = {
    "smile_jawOpen": ["mouthSmileLeft", "mouthSmileRight", "jawOpen"],
    "blink_squint": ["eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "eyeSquintRight"],
    "pucker_jawOpen": ["mouthPucker", "jawOpen"],
    "funnel_jawOpen": ["mouthFunnel", "jawOpen"],
    "smile_blink": ["mouthSmileLeft", "mouthSmileRight", "eyeBlinkLeft", "eyeBlinkRight"],
    "press_close": ["mouthPressLeft", "mouthPressRight", "mouthClose"],
}


def eff_weight(name, vals):
    if name == "mouthClose":
        return vals[name] * (CLOSE_FLOOR + (1 - CLOSE_FLOOR) * vals.get("jawOpen", 0.0))
    return vals[name]


set_pose((NEUT, 1.0))
dg0 = bpy.context.evaluated_depsgraph_get()
baked = {}
polys = {}
for n, part in BAKE_PARTS.items():
    src = bpy.data.objects[n]
    ev = src.evaluated_get(dg0)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg0)
    me.name = SHORT[n]
    ob = bpy.data.objects.new(SHORT[n], me)
    sc.collection.objects.link(ob)
    if not ob.vertex_groups:  # (usually the names travel with the mesh)
        for vg in src.vertex_groups:
            ob.vertex_groups.new(name=vg.name)
    ob["face_part"] = part
    ob.parent = rig
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = rig
    baked[n] = (ob, {})
    polys[n] = [tuple(p.vertices) for p in me.polygons]
for n in EYE_PARTS:
    ev = bpy.data.objects[n].evaluated_get(dg0)
    me = ev.to_mesh()
    polys[n] = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
neutral_pos = {n: eval_pos(bpy.data.objects[n]) for n in BAKE_PARTS}
# the eyeballs stay bone-driven in the finished file, where every face bone but the eye targets rests: so their
# positions come from the rest pose, not from the neutral face
set_pose()
neutral_pos.update({n: eval_pos(bpy.data.objects[n]) for n in EYE_PARTS})
set_pose((NEUT, 1.0))
log("neutral baked")


class PM:
    """Polygon soup with the same BVH construction face_check uses, so overlap counts agree exactly."""

    def __init__(self, pl):
        self.polys = pl

    def bvh(self, pos):
        return BVHTree.FromPolygons(pos.tolist(), self.polys, epsilon=0.0)

    def normals_centres(self, pos):
        t = np.array([p[:3] for p in self.polys])
        a, b, c = pos[t[:, 0]], pos[t[:, 1]], pos[t[:, 2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
        return n, (a + b + c) / 3


PMS = {n: PM(polys[n]) for n in polys}
HEAD = "GEO-rain-head"


def overlaps(inner, ipos, skin, spos):
    return {(int(i), int(j)) for i, j in PMS[inner].bvh(ipos).overlap(PMS[skin].bvh(spos))}


EYE_CEN = {}      # filled in by the collision pass (needs the finished pose)
BASE_PAIRS = {}
STEP = 0.00035   # metres per push


KINDS = {"teeth": INNER["teeth"], "tongue": INNER["tongue"], "eye": EYE_PARTS}


def resolve(pos, eye_pos, max_it=45):
    """pos: part -> (n,3) positions of the baked parts under one pose. The skin (head) is the soft thing: wherever teeth,
    tongue or eyeballs overlap it in more triangle pairs than at neutral, skin vertices are pushed off them (along the
    inner surface normal, or radially off an eyeball) until the count is back at neutral. Returns (positions, iterations)."""
    pos = {k: v.copy() for k, v in pos.items()}
    it = 0
    for it in range(max_it):
        moved = False
        disp = np.zeros_like(pos[HEAD])
        for kind, parts in KINDS.items():
            src = eye_pos if kind == "eye" else pos
            prs = {n: overlaps(n, src[n], HEAD, pos[HEAD]) for n in parts}
            tot, base = sum(len(v) for v in prs.values()), sum(len(BASE_PAIRS[n]) for n in parts)
            if tot <= base - (8 + int(0.06 * base) + (30 if kind == 'tongue' else 0)) or not any(prs[n] - BASE_PAIRS[n] for n in parts):
                continue
            for n in parts:
                new = prs[n] - BASE_PAIRS[n]
                if kind != "eye":
                    inn, _ = PMS[n].normals_centres(src[n])
                for ipoly, spoly in new:
                    for v in PMS[HEAD].polys[spoly]:
                        if kind == "eye":
                            c = EYE_CEN[1] if pos[HEAD][v][0] > 0 else EYE_CEN[-1]
                            d = pos[HEAD][v] - c
                            disp[v] += d / (np.linalg.norm(d) + 1e-9)
                        else:
                            disp[v] += inn[ipoly]
            moved = True
        if not moved:
            break
        m = np.linalg.norm(disp, axis=1) > 0
        disp[m] /= np.linalg.norm(disp[m], axis=1)[:, None]
        pos[HEAD] = pos[HEAD] + STEP * (1 + it / 15) * disp  # the step grows if the contact is stubborn
    return pos, it


def excess(pos, eye_pos):
    out = {}
    for kind, parts in KINDS.items():
        src = eye_pos if kind == "eye" else pos
        out[kind] = sum(len(overlaps(n, src[n], HEAD, pos[HEAD])) - len(BASE_PAIRS[n]) for n in parts)
    return {k: v for k, v in out.items() if v > 0}


deltas = {n: {} for n in BAKE_PARTS}
SOLVE_PARTS = [HEAD] + sum(INNER.values(), [])
EYELOOK = [n for n in ARKIT_NAMES if n.startswith("eyeLook")]   # gaze stays bone-driven (the rig's sticky lids follow)
for name in ARKIT_NAMES:
    if name in EYELOOK:
        continue
    chain, cur = [name], name
    while cur in BASE:
        cur = BASE[cur]
        chain.append(cur)
    stack = [(NEUT, 1.0)] + [(expand(c, RECIPES), 1.0) for c in reversed(chain)]
    ref_stack = [(NEUT, 1.0)] + [(expand(c, RECIPES), 1.0) for c in reversed(chain[1:])]
    set_pose(*ref_stack)
    ref = {n: eval_pos(bpy.data.objects[n]) for n in BAKE_PARTS}
    set_pose(*stack)
    for n in BAKE_PARTS:
        deltas[n][name] = eval_pos(bpy.data.objects[n]) - ref[n]
set_pose()
log("evaluated all recipes")

# the baked meshes: basis = evaluated neutral; one shape key per ARKit name with real deformation
for n, (ob, _) in baked.items():
    me = ob.data
    ob.shape_key_add(name="Basis", from_mix=False)
    basis = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", basis)
    basis = basis.reshape(-1, 3)
    assert len(basis) == len(neutral_pos[n]), (n, len(basis), len(neutral_pos[n]))
    for name in ARKIT_NAMES:
        d = deltas[n].get(name)
        if d is None or np.abs(d).max() < 2e-5:
            continue
        kb = ob.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", (basis + d).astype(np.float32).ravel())
        kb.slider_min, kb.slider_max = 0.0, 1.0
    log(f"  {n}: {len(me.vertices)} verts, {len(me.shape_keys.key_blocks) - 1} keys")
for n in BAKE_PARTS:
    kill(bpy.data.objects[n])
bpy.context.view_layer.update()

# ===================================================================================================
# 4. neutral pose: A-pose, long neck
# ===================================================================================================
LIFT = 0.06          # head lifted on the neck (the neck bone stretches with it): the references' long neck
RIG_SCALE = 1.07     # Rain is ~1.65 m; Kai is ~1.8 m
P = rig.pose.bones
ikfk = P["Properties_IKFK"]
for k in ("ik_arm_left", "ik_arm_right", "ik_spine"):
    ikfk[k] = 0.0     # FK arms and spine: the A-pose and the body lean are plain bone rotations
ARM_DOWN = math.radians(52)        # the .R bones are mirrored: same local axis, opposite sign
P["FK-Upperarm.L"].rotation_euler = (0, 0, -ARM_DOWN)
P["FK-Upperarm.R"].rotation_euler = (0, 0, ARM_DOWN)
P["FK-Forearm.L"].rotation_euler = (0, 0, math.radians(-8))
P["FK-Forearm.R"].rotation_euler = (0, 0, math.radians(8))
P["FK-Head"].location = (0, LIFT, 0)
bpy.context.view_layer.update()

# ===================================================================================================
# 5. the contract
# ===================================================================================================
COLL = bpy.data.collections.new("CHAR_base")
sc.collection.children.link(COLL)


def link_all(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    COLL.objects.link(o)


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = "PLAIN_AXES", 0.05
    e.location = loc
    link_all(e)
    if parent:
        e.parent = parent
    return e


ROOT = empty("CHAR_root")
rig.parent = ROOT
rig.scale = (RIG_SCALE,) * 3
rig.name = "Rig"
HEADE = empty("Head", (0, -0.016 * RIG_SCALE, (1.392 + LIFT) * RIG_SCALE), ROOT)
con = P["FK-Head"].constraints.new("COPY_ROTATION")
con.target, con.mix_mode, con.target_space, con.owner_space = HEADE, "AFTER", "WORLD", "WORLD"
con.name = "Head nod"
BODYE = empty("Body", (0, -0.029 * RIG_SCALE, 0.911 * RIG_SCALE), ROOT)  # render_plan leans/breathes this
con = P["FK-Spine"].constraints.new("COPY_ROTATION")
con.target, con.mix_mode, con.target_space, con.owner_space = BODYE, "AFTER", "WORLD", "WORLD"
con.name = "Body lean"
FACECTRL = empty("FaceCtrl", (0, 0, 0), ROOT)
for n in ARKIT_NAMES:
    FACECTRL[n] = 0.0
    FACECTRL.id_properties_ui(n).update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0)
FACECTRL.hide_render = True
for o in (ROOT, HEADE, BODYE):
    o.hide_render = True
for o in [o for o in bpy.data.objects if o.type != "EMPTY"] + [rig]:
    link_all(o)
for c in [c for c in bpy.data.collections if c != COLL and c.name != "Collection"]:
    bpy.data.collections.remove(c)
lat = bpy.data.objects.get("HLP-rain-lattice-head")
if lat:
    lat.hide_render = True


def drive(owner, path, expr, vars_, index=-1, dtype="SCRIPTED"):
    fc = owner.driver_add(path) if index < 0 else owner.driver_add(path, index)
    d = fc.driver
    d.type = dtype
    if dtype == "SCRIPTED":
        d.expression = expr
    for vname, prop in vars_.items():
        v = d.variables.new()
        v.name = vname
        v.type = "SINGLE_PROP"
        v.targets[0].id_type = "OBJECT"
        v.targets[0].id = FACECTRL
        v.targets[0].data_path = f'["{prop}"]'
    return fc


# shape keys of every baked face part follow FaceCtrl one to one (mouthClose is relative to the jaw; fix_* correctives
# fire only when all their members do)
for n, (ob, _) in baked.items():
    ks = ob.data.shape_keys
    for kb in ks.key_blocks[1:]:
        path = f'key_blocks["{kb.name}"].value'
        if kb.name == "mouthClose":
            drive(ks, path, f"v*({CLOSE_FLOOR}+{1 - CLOSE_FLOOR}*j)", {"v": "mouthClose", "j": "jawOpen"})
        elif kb.name.startswith("fix_"):
            mem = COMBOS[kb.name[4:]]
            drive(ks, path, "*".join(f"m{i}" for i in range(len(mem))), {f"m{i}": m for i, m in enumerate(mem)})
        else:
            drive(ks, path, "", {"v": kb.name}, dtype="SUM")
# eye gaze stays bone-driven: the eye target bones follow FaceCtrl (Rain's own sticky lids ride along in the bake)
LOOK = {"Down": 0.22, "Up": 0.20, "In": 0.22, "Out": 0.26}
for side, sn in ((".L", "Left"), (".R", "Right")):
    pth = f'pose.bones["TGT-Eye{side}"].location'
    drive(rig, pth, f"{LOOK['Up']}*u-{LOOK['Down']}*d", {"u": f"eyeLookUp{sn}", "d": f"eyeLookDown{sn}"}, index=1)
    drive(rig, pth, f"{LOOK['Out']}*o-{LOOK['In']}*i", {"o": f"eyeLookOut{sn}", "i": f"eyeLookIn{sn}"}, index=2)
bpy.context.view_layer.update()


def bone_parent(obj, bone, world):
    """Parent obj to a bone of the rig, keeping `world` as its transform at the neutral pose."""
    bpy.context.view_layer.update()
    rev = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pb = rev.pose.bones[bone]
    m = pb.matrix.copy()
    m.translation = pb.tail
    obj.parent, obj.parent_type, obj.parent_bone = rig, "BONE", bone
    obj.matrix_parent_inverse = (rev.matrix_world @ m).inverted()
    obj.matrix_basis = world


# head bounds at the neutral pose -> anchors
dgr = bpy.context.evaluated_depsgraph_get()
hob = baked["GEO-rain-head"][0]
hev = hob.evaluated_get(dgr)
hm = hev.to_mesh()
hv = np.array([(hob.matrix_world @ v.co)[:] for v in hm.vertices])
hev.to_mesh_clear()
front = hv[hv[:, 1] < -0.10 * RIG_SCALE]
chin_z, crown_z = float(front[:, 2].min()), float(hv[:, 2].max())
HEAD_H = crown_z - chin_z
log(f"head: chin {chin_z:.3f} crown {crown_z:.3f} -> head_height {HEAD_H:.3f} m")
FACEA = empty("FaceAnchor")
FACEA["head_height"] = HEAD_H
FOCUS = empty("EyeFocus")
EYE_Y = -0.125 * RIG_SCALE
bone_parent(FACEA, "DEF-Head", Matrix.Translation((0, -0.09 * RIG_SCALE, (chin_z + crown_z) / 2)))
bone_parent(FOCUS, "DEF-Head", Matrix.Translation((0, EYE_Y, (1.474 + LIFT * 0.94) * RIG_SCALE)))
for o in (FACEA, FOCUS):
    o.hide_render = True

# ===================================================================================================
# 5b. collision pass, in the finished pose: skin is pushed off teeth, tongue and eyeballs where a shape would
#     make them poke through (the same overlap test face_check runs)
# ===================================================================================================
bpy.context.view_layer.update()
P0 = {n: eval_pos(baked[n][0]) for n in BAKE_PARTS}
E0 = {n: eval_pos(bpy.data.objects[n]) for n in EYE_PARTS}
for sgn in (1, -1):
    _s = E0["GEO-rain-eyes"][np.sign(E0["GEO-rain-eyes"][:, 0]) == sgn]
    EYE_CEN[sgn] = (_s.min(0) + _s.max(0)) / 2
for n in sum(INNER.values(), []):
    BASE_PAIRS[n] = overlaps(n, P0[n], HEAD, P0[HEAD])
for n in EYE_PARTS:
    BASE_PAIRS[n] = overlaps(n, E0[n], HEAD, P0[HEAD])
log("neutral overlap pairs (finished pose):", {n[9:]: len(v) for n, v in BASE_PAIRS.items()})


def eyes_looking(name):
    FACECTRL[name] = 1.0
    bpy.context.view_layer.update()
    out = {n: eval_pos(bpy.data.objects[n]) for n in EYE_PARTS}
    FACECTRL[name] = 0.0
    bpy.context.view_layer.update()
    return out


for name in ARKIT_NAMES:
    base_name = BASE.get(name)
    if name in EYELOOK:     # the rig moves the eyeballs and the lids; only the leftover poke-through is baked
        FACECTRL[name] = 1.0
        FACECTRL.update_tag()
        bpy.context.view_layer.update()
        ref = {n: eval_pos(baked[n][0]) for n in BAKE_PARTS}
        eye_pos = {n: eval_pos(bpy.data.objects[n]) for n in EYE_PARTS}
        FACECTRL[name] = 0.0
        FACECTRL.update_tag()
        bpy.context.view_layer.update()
        base_d = {n: 0 for n in BAKE_PARTS}
    else:
        ref = P0
        base_d = {n: (deltas[n][base_name] if base_name else 0) for n in BAKE_PARTS}
        eye_pos = E0
    cur_pos = {n: ref[n] + base_d[n] + deltas[n].get(name, 0) for n in SOLVE_PARTS}
    fixed, its = resolve(cur_pos, eye_pos)
    left = excess(fixed, eye_pos)
    if left:
        log(f"  {name}: unresolved after {its} iterations: {left}")
    for n in SOLVE_PARTS:
        deltas[n][name] = fixed[n] - ref[n] - base_d[n]
log("collision pass done")
FIX = {}  # combo -> {part: delta}
for cname, members in COMBOS.items():
    vals = {m: 1.0 for m in members}
    pos = {n: P0[n] + sum(eff_weight(m, vals) * deltas[n][m] for m in members) for n in BAKE_PARTS}
    fixed, its = resolve({n: pos[n] for n in SOLVE_PARTS}, E0)
    FIX[cname] = {n: fixed[n] - pos[n] for n in SOLVE_PARTS if np.abs(fixed[n] - pos[n]).max() > 1e-6}
    left = excess(fixed, E0)
    log(f"  combo {cname}: {len(FIX[cname])} parts corrected in {its} iterations" + (f", unresolved {left}" if left else ""))
for n, (ob, _) in baked.items():
    ks = ob.data.shape_keys
    basis = np.empty(len(ob.data.vertices) * 3, np.float32)
    ks.key_blocks[0].data.foreach_get("co", basis)
    basis = basis.reshape(-1, 3)
    for kb in list(ks.key_blocks)[1:]:
        kb.data.foreach_set("co", (basis + deltas[n][kb.name]).astype(np.float32).ravel())
    for name in EYELOOK:
        d = deltas[n].get(name)
        if d is not None and np.abs(d).max() > 2e-5:
            kb = ob.shape_key_add(name=name, from_mix=False)
            kb.data.foreach_set("co", (basis + d).astype(np.float32).ravel())
            kb.slider_min, kb.slider_max = 0.0, 1.0
            drive(ks, f'key_blocks["{name}"].value', "", {"v": name}, dtype="SUM")
    for cname, parts in FIX.items():
        if n in parts:
            kb = ob.shape_key_add(name="fix_" + cname, from_mix=False)
            kb.data.foreach_set("co", (basis + parts[n]).astype(np.float32).ravel())
            kb.slider_min, kb.slider_max = 0.0, 1.0
            mem = COMBOS[cname]
            drive(ks, f'key_blocks["{kb.name}"].value', "*".join(f"m{i}" for i in range(len(mem))),
                  {f"m{i}": m for i, m in enumerate(mem)})
# verification: re-measure every shape on the real, driven objects and fix whatever still pokes through
for name in ARKIT_NAMES:
    FACECTRL[name] = 1.0
    FACECTRL.update_tag()
    bpy.context.view_layer.update()
    real = {n: eval_pos(baked[n][0]) for n in SOLVE_PARTS}
    eyes_real = {n: eval_pos(bpy.data.objects[n]) for n in EYE_PARTS}
    FACECTRL[name] = 0.0
    FACECTRL.update_tag()
    if not excess(real, eyes_real):
        continue
    fixed, its = resolve(real, eyes_real)
    log(f"  verify {name}: extra fix, left {excess(fixed, eyes_real)}")
    for n in SOLVE_PARTS:
        d = fixed[n] - real[n]
        if np.abs(d).max() < 1e-6:
            continue
        ks = baked[n][0].data.shape_keys
        kb = ks.key_blocks.get(name)
        if kb is None:
            kb = baked[n][0].shape_key_add(name=name, from_mix=False)
            kb.slider_min, kb.slider_max = 0.0, 1.0
            drive(ks, f'key_blocks["{name}"].value', "", {"v": name}, dtype="SUM")
        arr = np.empty(len(kb.data) * 3, np.float32)
        kb.data.foreach_get("co", arr)
        kb.data.foreach_set("co", (arr.reshape(-1, 3) + d).astype(np.float32).ravel())
FACECTRL.update_tag()
bpy.context.view_layer.update()

# face_part tags and subdivision
TAGS = {"GEO-rain-eyes": "eye", "GEO-rain-eye_cornea": "eye"}
for n, t in TAGS.items():
    bpy.data.objects[n]["face_part"] = t
for n, (ob, _) in baked.items():
    sm = ob.modifiers.new("Subsurf", "SUBSURF")
    sm.levels, sm.render_levels = 0, 2 if ob["face_part"] == "head" else 1
    for poly in ob.data.polygons:
        poly.use_smooth = True
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith("GEO"):
        o.name = o.name.replace("GEO-rain-", "Kai_")

if DEV:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
    log("dev save", OUT)
    sys.exit(0)

# ===================================================================================================
# 6. Kai: skin + stubble, eyes, hair, outfit, jewellery
# ===================================================================================================
S_ = RIG_SCALE
SKIN = (0.47, 0.205, 0.100)       # cast.py base skin, warm tan (linear)
LIPC = (0.27, 0.085, 0.070)
HAIRC = (0.011, 0.009, 0.009)
SILVER = (0.80, 0.80, 0.83)


def nodes_of(m):
    m.use_nodes = True
    return m.node_tree, m.node_tree.nodes["Principled BSDF"]


def plain_mat(name, color, rough=0.6, metal=0.0, coat=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    nt, b = nodes_of(m)
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Specular IOR Level"].default_value = spec
    return m


def mixrgb(nt, fac, a, b):
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    if isinstance(fac, (int, float)):
        mx.inputs[0].default_value = fac
    else:
        nt.links.new(fac, mx.inputs[0])
    for sock, v in ((mx.inputs[6], a), (mx.inputs[7], b)):
        if isinstance(v, tuple):
            sock.default_value = (*v, 1.0)
        else:
            nt.links.new(v, sock)
    return mx.outputs[2]


def attr_node(nt, name):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = name
    return a.outputs["Fac"]


# --- skin: tan, vermilion lips by attribute, stubble dots on the jaw/chin/upper lip ------------------------------
skin = bpy.data.materials.new("Kai_skin")
nt, b = nodes_of(skin)
b.inputs["Roughness"].default_value = 0.46
b.inputs["Specular IOR Level"].default_value = 0.45
b.inputs["Subsurface Weight"].default_value = 0.22
b.inputs["Subsurface Radius"].default_value = (0.55, 0.22, 0.11)
b.inputs["Subsurface Scale"].default_value = 0.012
b.inputs["Coat Weight"].default_value = 0.04
col = mixrgb(nt, attr_node(nt, "lip"), SKIN, LIPC)
tc = nt.nodes.new("ShaderNodeTexCoord")
nz = nt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 1100.0
nz.inputs["Detail"].default_value = 1.0
nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.50, 0.66
nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
dots = nt.nodes.new("ShaderNodeMath")
dots.operation = "MULTIPLY"
nt.links.new(ramp.outputs["Color"], dots.inputs[0])
nt.links.new(attr_node(nt, "stub"), dots.inputs[1])
shade = nt.nodes.new("ShaderNodeMath")
shade.operation = "MULTIPLY"
nt.links.new(attr_node(nt, "stub"), shade.inputs[0])
shade.inputs[1].default_value = 0.22
both = nt.nodes.new("ShaderNodeMath")
both.operation, both.use_clamp = "ADD", True
nt.links.new(dots.outputs[0], both.inputs[0])
nt.links.new(shade.outputs[0], both.inputs[1])
col = mixrgb(nt, both.outputs[0], col, (0.030, 0.018, 0.014))
nt.links.new(col, b.inputs["Base Color"])
bumpn = nt.nodes.new("ShaderNodeBump")
bumpn.inputs["Strength"].default_value = 0.25
bumpn.inputs["Distance"].default_value = 0.0006
nt.links.new(dots.outputs[0], bumpn.inputs["Height"])
nt.links.new(bumpn.outputs["Normal"], b.inputs["Normal"])

for o in bpy.data.objects:
    if o.type == "MESH":
        for slot in o.material_slots:
            if slot.material and slot.material.name in ("MAT-rain.body", "MAT-rain.hands"):
                slot.material = skin

# --- head attributes: lip mask (vertex groups of the lip bones) and stubble mask ---------------------------------
hob = baked["GEO-rain-head"][0]
hme = hob.data
vgn = [g.name for g in hob.vertex_groups]
lip_idx = {i for i, n in enumerate(vgn) if n.startswith(("DEF-Lip_Top_Top", "DEF-Lip_Top_Bot", "DEF-Lip_Bot_Top",
                                                         "DEF-Lip_Bot_Bot", "DEF-Lip_Top_Across", "DEF-Lip_Bot_Across"))}
lip = np.zeros(len(hme.vertices), np.float32)
for v in hme.vertices:
    lip[v.index] = min(1.0, sum(g.weight for g in v.groups if g.group in lip_idx))
Pn = neutral_pos["GEO-rain-head"]
ax_, ay_, az_ = np.abs(Pn[:, 0]), Pn[:, 1], Pn[:, 2]
# jaw, chin, upper lip, sideburns and the underside of the neck; fades up the cheek, away from nostrils and lips
stub = sstep(1.455, 1.425, az_) * sstep(-0.02, -0.07, ay_)
stub = np.maximum(stub, 0.85 * sstep(1.50, 1.47, az_) * sstep(0.095, 0.115, ax_) * sstep(0.0, -0.05, ay_))
stub *= 1 - 0.9 * sstep(0.5, 0.9, lip)
nose = sstep(1.46, 1.43, az_) * (1 - sstep(0.012, 0.03, ax_)) * sstep(1.40, 1.425, az_)  # keep the philtrum light
stub = stub * (1 - 0.6 * nose)
stub *= sstep(1.28, 1.34, az_)
for nm, arr in (("lip", lip), ("stub", stub.astype(np.float32))):
    at = hme.attributes.new(nm, "FLOAT", "POINT")
    at.data.foreach_set("value", arr)

# --- eyes: brown iris on Rain's texture, keep its catchlight/wet look ---------------------------------------------
em = bpy.data.materials["MAT-rain.eyes"]
ent = em.node_tree
mixn = ent.nodes["Mix"]            # A: iris/sclera texture, B: vertex colour
hook = mixn.outputs["Result"]
tgt = [lk.to_socket for lk in list(hook.links)]
sep = ent.nodes.new("ShaderNodeSeparateColor")
sep.mode = "HSV"
ent.links.new(hook, sep.inputs["Color"])
satm = ent.nodes.new("ShaderNodeMath")
satm.operation, satm.use_clamp = "MULTIPLY", True
satm.inputs[1].default_value = 2.2
ent.links.new(sep.outputs["Green"], satm.inputs[0])
bw = ent.nodes.new("ShaderNodeRGBToBW")
ent.links.new(hook, bw.inputs["Color"])
brown = ent.nodes.new("ShaderNodeMix")
brown.data_type, brown.blend_type = "RGBA", "MULTIPLY"
brown.inputs[0].default_value = 1.0
ent.links.new(bw.outputs["Val"], brown.inputs[6])
brown.inputs[7].default_value = (1.9, 0.95, 0.40, 1.0)
iris = ent.nodes.new("ShaderNodeMix")
iris.data_type = "RGBA"
ent.links.new(satm.outputs[0], iris.inputs[0])
ent.links.new(hook, iris.inputs[6])
ent.links.new(brown.outputs[2], iris.inputs[7])
for sk in tgt:
    ent.links.new(iris.outputs[2], sk)
em.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.0
for img in bpy.data.images:
    if img.name.startswith("TEX-rain_eyes"):
        img.pack()   # self-contained: the output .blend must not depend on the third-party folder

# --- brows, lashes: Kai's black --------------------------------------------------------------------------------
for mn, colr, rough in (("MAT-rain.eyebrows", (0.012, 0.009, 0.008), 0.55), ("MAT-rain.eyelashes", (0.006, 0.005, 0.005), 0.6)):
    m = bpy.data.materials[mn]
    nt, pb_ = nodes_of(m)
    for lk in list(pb_.inputs["Base Color"].links):
        nt.links.remove(lk)
    pb_.inputs["Base Color"].default_value = (*colr, 1.0)
    pb_.inputs["Roughness"].default_value = rough

# --- hair: scalp cap + clay curls, built in world space and parented to the head bone ----------------------------
rng = np.random.default_rng(7)
dgr = bpy.context.evaluated_depsgraph_get()
hev = hob.evaluated_get(dgr)
hm = hev.to_mesh()
HW_ = np.array([(hob.matrix_world @ v.co)[:] for v in hm.vertices])          # world positions at the neutral pose
HN_ = np.empty(len(hm.vertices) * 3, np.float32)
hm.vertex_normals.foreach_get("vector", HN_)
HN_ = HN_.reshape(-1, 3)
HPOLY = [tuple(p.vertices) for p in hm.polygons]
hev.to_mesh_clear()
yf, yb = float(HW_[:, 1].min()), float(HW_[:, 1].max())
tt = (HW_[:, 1] - yf) / (yb - yf)                                              # 0 front .. 1 back
drop = np.interp(tt, [0, 0.22, 0.45, 0.7, 1.0], [0.19, 0.25, 0.43, 0.62, 0.74]) * HEAD_H
drop = np.where((np.abs(HW_[:, 0]) > 0.07 * S_) & (tt < 0.4), np.maximum(drop, 0.30 * HEAD_H), drop)
scalp = (HW_[:, 2] > crown_z - drop)
ear = (np.abs(HW_[:, 0]) > 0.100 * S_) & (HW_[:, 2] < crown_z - 0.24 * HEAD_H) & (tt > 0.3) & (tt < 0.78)
scalp &= ~ear
log(f"scalp verts {int(scalp.sum())}")


def mesh_obj(name, verts, faces, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = smooth
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    return ob


hair_mat = plain_mat("Kai_hair", HAIRC, rough=0.52, coat=0.15, spec=0.45)
# cap: the head's own scalp polygons, lifted a few millimetres
cap_faces = [p for p in HPOLY if all(scalp[i] for i in p)]
used = sorted({i for p in cap_faces for i in p})
remap = {v: k for k, v in enumerate(used)}
cap_v = HW_[used] + HN_[used] * 0.0035 * S_
cap = mesh_obj("Kai_hair_cap", cap_v, [[remap[i] for i in p] for p in cap_faces], hair_mat)


def helix_tube(root, n, down, scale, sides=5, pts=12):
    """One clay curl: a fat tapering coil standing off the scalp at `root`, leaning along `down`."""
    n = n / np.linalg.norm(n)
    dn = down - (down @ n) * n
    dn = dn / (np.linalg.norm(dn) + 1e-9)
    a = 0.60 * n + 0.55 * dn + rng.normal(0, 0.30, 3)
    a /= np.linalg.norm(a)
    e1 = np.cross(a, [1.0, 0.0, 0.0] if abs(a[0]) < 0.9 else [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    turns = rng.uniform(1.3, 1.8)
    r = scale * rng.uniform(0.0140, 0.0175)
    h = scale * rng.uniform(0.036, 0.050)
    rt = scale * rng.uniform(0.0078, 0.0090)
    ph = rng.uniform(0, 2 * math.pi)
    base = root + n * 0.002 * S_
    c = []
    for j in range(pts):
        u = j / (pts - 1)
        th = ph + 2 * math.pi * turns * u
        c.append(base + a * h * u + r * min(1.0, 3 * u + 0.4) * (math.cos(th) * e1 + math.sin(th) * e2))
    c = np.array(c)
    rad = rt * (1 - 0.45 * np.linspace(0, 1, pts) ** 2)
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    nrm = np.cross(T[0], e1 if abs(T[0] @ e1) < 0.9 else e2)
    nrm /= np.linalg.norm(nrm)
    ring = []
    for j in range(pts):
        nrm = nrm - (nrm @ T[j]) * T[j]
        nrm /= np.linalg.norm(nrm)
        bn = np.cross(T[j], nrm)
        ring.append([c[j] + rad[j] * (math.cos(2 * math.pi * k / sides) * nrm + math.sin(2 * math.pi * k / sides) * bn)
                     for k in range(sides)])
    return np.array(ring)


# roots: dart throwing on the scalp, denser toward the front hairline
roots_p = [HW_[i] for i in np.where(scalp)[0]] + [np.mean(HW_[list(p)], axis=0) for p in cap_faces]
roots_n = [HN_[i] for i in np.where(scalp)[0]] + [np.mean(HN_[list(p)], axis=0) for p in cap_faces]
cand = np.arange(len(roots_p))
rng.shuffle(cand)
chosen = []
dmin = 0.0235 * S_
for i in cand:
    if all(np.linalg.norm(roots_p[i] - roots_p[j]) > dmin for j in chosen):
        chosen.append(i)
log(f"curls: {len(chosen)}")
all_v, all_f = [], []
for i in chosen:
    front_ = roots_p[i][1] < yf + 0.4 * (yb - yf)
    down = np.array([0.0, 0.45 if front_ else 0.15, -1.0])
    ring = helix_tube(roots_p[i], roots_n[i], down, S_ * 1.15)
    pts_, sides_ = ring.shape[:2]
    base_i = len(all_v)
    all_v.extend(ring.reshape(-1, 3))
    for j in range(pts_ - 1):
        for k in range(sides_):
            k2 = (k + 1) % sides_
            all_f.append([base_i + j * sides_ + k, base_i + j * sides_ + k2, base_i + (j + 1) * sides_ + k2,
                          base_i + (j + 1) * sides_ + k])
curls = mesh_obj("Kai_hair_curls", all_v, all_f, hair_mat)
for hobj in (cap, curls):
    bone_parent(hobj, "DEF-Head", Matrix.Identity(4))

# --- jewellery -----------------------------------------------------------------------------------------------------
silver = plain_mat("Kai_silver", SILVER, rough=0.16, metal=1.0, spec=0.6)
lobe_idx = {i for i, n in enumerate(vgn) if n in ("DEF-Ear_Bot.L",)}
lw = np.array([sum(g.weight for g in v.groups if g.group in lobe_idx) for v in hme.vertices])
lobe_cand = np.where(lw > 0.5)[0]
lobe = HW_[lobe_cand[np.argmin(HW_[lobe_cand, 2])]] if len(lobe_cand) else np.array([0.13, -0.03, crown_z - 0.4 * HEAD_H]) * 1
log("earlobe (world)", np.round(lobe, 3))
R_h, r_h = 0.0105 * S_, 0.0017 * S_
tv, tf = [], []
NS, NT = 28, 6
cen_h = lobe + np.array([0.0035 * S_, 0.001 * S_, -0.0035 * S_])
for i in range(NS):
    th = 2 * math.pi * i / NS
    c = cen_h + R_h * np.array([0.0, math.cos(th), math.sin(th)]) + np.array([0, 0, -R_h * 0.62])
    # ring in the Y-Z plane, hanging below the lobe's hole
    radial = np.array([0.0, math.cos(th), math.sin(th)])
    for k in range(NT):
        ph = 2 * math.pi * k / NT
        tv.append(c + r_h * (math.cos(ph) * radial + math.sin(ph) * np.array([1.0, 0, 0])))
for i in range(NS):
    for k in range(NT):
        tf.append([i * NT + k, i * NT + (k + 1) % NT, ((i + 1) % NS) * NT + (k + 1) % NT, ((i + 1) % NS) * NT + k])
hoop = mesh_obj("Kai_hoop", tv, tf, silver)
bone_parent(hoop, "DEF-Head", Matrix.Identity(4))

# chain: a thin loop that rests on the collar bones and hangs into the open collar
body_o = bpy.data.objects["Kai_body"]
bev = body_o.evaluated_get(bpy.context.evaluated_depsgraph_get())
bm_ = bev.to_mesh()
bw_ = [(body_o.matrix_world @ v.co)[:] for v in bm_.vertices]
bpoly = [tuple(p.vertices) for p in bm_.polygons]
bev.to_mesh_clear()
bvh_body = BVHTree.FromPolygons(bw_, bpoly)
axis_c = np.array([0.0, -0.03 * S_, 0.0])
z_n = 1.265 * S_
cpts = []
for i in range(64):
    ph = 2 * math.pi * i / 64
    d = np.array([math.cos(ph), math.sin(ph), 0.0])
    front_k = max(0.0, -math.sin(ph)) ** 1.6
    z = z_n - 0.095 * S_ * front_k
    o_ = axis_c + d * 0.25 * S_
    o_[2] = z
    hit = bvh_body.ray_cast(Vector(o_), Vector(-d), 0.25 * S_)
    if hit[0] is None:
        p_ = axis_c + d * 0.065 * S_
        p_[2] = z
    else:
        p_ = np.array(hit[0]) + d * 0.0035 * S_
    cpts.append(p_)
cpts = np.array(cpts)
cv, cf = [], []
for i, p_ in enumerate(cpts):
    t_ = cpts[(i + 1) % len(cpts)] - cpts[i - 1]
    t_ /= np.linalg.norm(t_)
    e_a = np.cross(t_, [0, 0, 1.0])
    e_a /= np.linalg.norm(e_a)
    e_b = np.cross(t_, e_a)
    for k in range(4):
        ph = 2 * math.pi * k / 4
        cv.append(p_ + 0.0016 * S_ * (math.cos(ph) * e_a + math.sin(ph) * e_b))
for i in range(len(cpts)):
    for k in range(4):
        cf.append([i * 4 + k, i * 4 + (k + 1) % 4, ((i + 1) % len(cpts)) * 4 + (k + 1) % 4, ((i + 1) % len(cpts)) * 4 + k])
chain = mesh_obj("Kai_chain", cv, cf, silver)
bone_parent(chain, "DEF-Spine3", Matrix.Identity(4))

# --- outfit 0: boxy black open-collar shirt (cut from a copy of the body, so it inherits the skin weights),
#     dark trousers (Rain's jeans, inflated), sneakers ---------------------------------------------------------------
def sstep_s(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


body_o = bpy.data.objects["Kai_body"]
shirt = body_o.copy()
shirt.data = body_o.data.copy()
shirt.name = shirt.data.name = "Kai_shirt"
COLL.objects.link(shirt)
shirt.shape_key_clear()
shirt.modifiers.clear()
bm = bmesh.new()
bm.from_mesh(shirt.data)
bm.faces.ensure_lookup_table()


def keep_face(f):
    c = f.calc_center_median()
    ax = abs(c.x)
    if c.z < 0.88 or ax > 0.285 or c.z > 1.33:
        return False
    zc = (1.285 - 0.100 * max(0.0, 1.0 - ax / 0.075)) if c.y < -0.03 else 1.272
    return c.z <= (zc if ax < 0.075 else 1.32)


bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep_face(f)], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.normal_update()
SH_A = ([0.86, 1.00, 1.12, 1.22, 1.27, 1.31], [0.196, 0.196, 0.182, 0.168, 0.135, 0.085])   # half-width by height
SH_B = ([0.86, 1.00, 1.12, 1.22, 1.27, 1.31], [0.114, 0.114, 0.110, 0.100, 0.085, 0.07])    # half-depth by height
for v in bm.verts:
    x, y, z = v.co
    n = v.normal
    ax = abs(x)
    co = v.co + n * 0.004
    wt = 1 - sstep_s(0.10, 0.17, ax)                       # torso: a boxy rounded-rectangle tube, no bust, no waist
    dx, dy = co.x, co.y + 0.03
    r = math.hypot(dx, dy)
    if r > 1e-5 and wt > 0:
        a_, b_ = np.interp(z, *SH_A), np.interp(z, *SH_B)
        R = ((abs(dx / r) / a_) ** 3.2 + (abs(dy / r) / b_) ** 3.2) ** (-1 / 3.2)
        k = (r + wt * (R - r)) / r
        co.x, co.y = dx * k, dy * k - 0.03
    ws = sstep_s(0.10, 0.17, ax)                           # sleeves: loose tubes about the arm axis
    za, ya = 1.25 - 0.05 * max(0.0, ax - 0.11), 0.004
    k = 1 + ws * (0.26 + 0.2 * sstep_s(0.12, 0.28, ax))
    co.y = ya + (co.y - ya) * k
    co.z = za + (co.z - za) * k
    v.co = co
# the open collar: a standing band along the neckline edge, folded out
neck_edges = [e for e in bm.edges if e.is_boundary and abs(e.verts[0].co.x) < 0.11 and abs(e.verts[1].co.x) < 0.11
              and e.verts[0].co.z > 1.1 and e.verts[1].co.z > 1.1]
ex = bmesh.ops.extrude_edge_only(bm, edges=neck_edges)
for v in [g for g in ex["geom"] if isinstance(g, bmesh.types.BMVert)]:
    d = Vector((v.co.x, v.co.y + 0.03, 0.0))
    d = d.normalized() if d.length > 1e-6 else Vector((0, -1, 0))
    v.co = v.co + d * 0.016 + Vector((0, 0, 0.018))
bm.to_mesh(shirt.data)
bm.free()
for p in shirt.data.polygons:
    p.use_smooth = True
shirt_mat = plain_mat("Kai_shirt", (0.016, 0.016, 0.019), rough=0.82, spec=0.3)
shirt.data.materials.clear()
shirt.data.materials.append(shirt_mat)
shirt.parent = rig
am_ = shirt.modifiers.new("Armature", "ARMATURE")
am_.object = rig
sol = shirt.modifiers.new("Thickness", "SOLIDIFY")
sol.thickness, sol.offset = 0.007, -1.0
ss = shirt.modifiers.new("Subsurf", "SUBSURF")
ss.levels, ss.render_levels = 0, 1
log("shirt verts", len(shirt.data.vertices))

# trousers: Rain's jeans, inflated a little and dyed; sneakers: dyed
jeans = bpy.data.objects["Kai_jeans"]
jeans.name = "Kai_trousers"
jme = jeans.data
nrm = np.empty(len(jme.vertices) * 3, np.float32)
jme.vertex_normals.foreach_get("vector", nrm)
nrm = nrm.reshape(-1, 3)
cur = np.empty(len(jme.vertices) * 3, np.float32)
jme.vertices.foreach_get("co", cur)
zz = cur.reshape(-1, 3)[:, 2]
disp = nrm * (0.008 * sstep(0.10, 0.55, zz))[:, None]


def jeans_field(P):
    """Rain's skinny jeans -> straighter, narrower-hipped trousers."""
    Q = P + disp
    hip = sstep(0.55, 0.85, P[:, 2])
    Q[:, 0] = Q[:, 0] * (1 - 0.13 * hip)
    Q[:, 1] = -0.012 + (Q[:, 1] + 0.012) * (1 - 0.06 * hip)
    return Q


apply_field(jeans, jeans_field)
trous_mat = plain_mat("Kai_trousers", (0.020, 0.020, 0.024), rough=0.78, spec=0.3)
for slot in jeans.material_slots:
    slot.material = trous_mat
shoes = bpy.data.objects["Kai_shoes"]
repl = {"MAT-rain.shoes": plain_mat("Kai_sneaker", (0.022, 0.022, 0.026), rough=0.55),
        "MAT-rain.metal": silver, "MAT-rain.socks": plain_mat("Kai_sock", (0.03, 0.03, 0.034), rough=0.9),
        "MAT-rain.laces": plain_mat("Kai_laces", (0.75, 0.75, 0.75), rough=0.8)}
for slot in shoes.material_slots:
    if slot.material and slot.material.name in repl:
        slot.material = repl[slot.material.name]

# ===================================================================================================
# 7. finish: tags, visibility, cost numbers, save
# ===================================================================================================
for o in (hoop, chain, cap, curls, shirt):
    link_all(o)
for o in bpy.data.objects:
    if o.type == "ARMATURE":
        o.hide_render = False
        o.data.display_type = "STICK"
for o in bpy.data.objects:
    if o.type == "MESH" and o.parent == rig:
        pass
for c in rig.data.collections_all:
    c.is_visible = False
bpy.context.view_layer.update()

stats = {}
for o in bpy.data.objects:
    if o.type != "MESH" or o.hide_render:
        continue
    base_t = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mods = [(m, m.levels) for m in o.modifiers if m.type == "SUBSURF"]
    for m, _ in mods:
        m.show_viewport, m.levels = True, m.render_levels
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me_ = ev.to_mesh()
    ren_t = sum(len(p.vertices) - 2 for p in me_.polygons)
    ev.to_mesh_clear()
    for m, lv in mods:
        m.levels = lv
        m.show_viewport = False
    stats[o.name] = (base_t, ren_t)
log("tris (base / at render subdivision):")
for k, (a_, b_) in sorted(stats.items()):
    log(f"  {k:22s} {a_:7d} {b_:8d}")
log(f"  TOTAL                  {sum(a for a, _ in stats.values()):7d} {sum(b for _, b in stats.values()):8d}")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT), compress=True)
log("saved", OUT)
