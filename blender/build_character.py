"""Build a stylized-sculpt cast member → <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/build_character.py -- <out.blend> [char_id]
Contract: collection CHAR_base; empties CHAR_root, Head (nod pivot), FaceCtrl (52 ARKit custom
props), FaceAnchor (face centre, prop head_height in metres) and EyeFocus (eye plane).
Every face control is a driver from FaceCtrl, so the pipeline never touches meshes directly.

The head is sculpted by script: a dense cube-sphere is pushed around by smooth fields (jaw,
cheekbones, brow ridge, sockets, nose, lips) with a real mouth slit; face shapes are more fields.
Head-space units: chin ≈ -1.05, crown ≈ 1.15, face toward -Y; HeadGeo scales them to metres."""
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bl_common import ellipsoid, empty, material  # noqa: E402
from cast import CAST  # noqa: E402
from reelforge.arkit import ARKIT_NAMES  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(args[0])
C = CAST[args[1] if len(args) > 1 else "kai"]
C = {**C, **C.get("outfits", [{}])[int(args[2]) if len(args) > 2 else 0]}
RNG = np.random.default_rng(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
COLL = bpy.data.collections.new("CHAR_base")
bpy.context.scene.collection.children.link(COLL)

S = C["head_scale"]
SHOULDER_Z = 1.04
HEAD_C = SHOULDER_Z + C["neck_length"] + 0.72 * S  # chin underside sits at the top of the neck
PIVOT_Z = SHOULDER_Z + 0.6 * C["neck_length"]
JAW_MAX = 0.26  # rad at jawOpen = 1
FL, HW = C["face_length"], C["head_width"]
MZ = -0.56  # mouth line (head space)
EZ = -0.02  # eye line
PZ = MZ / FL  # same line on the unit sphere
ZT = -0.32 * C["nose_length"]  # nose tip height


# --- small field helpers (numpy, vectorised over vertices) --------------------
def sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def g2(X, cx, cz, sx, sz):
    return np.exp(-0.5 * ((X[:, 0] - cx) / sx) ** 2 - 0.5 * ((X[:, 2] - cz) / sz) ** 2)


def gm(X, cx, cz, sx, sz):
    """Mirrored pair of bumps at ±cx."""
    return np.exp(-0.5 * ((np.abs(X[:, 0]) - cx) / sx) ** 2 - 0.5 * ((X[:, 2] - cz) / sz) ** 2)


def gside(X, sx, cx, cz, sx_, sz):
    """One bump on side sx (+1 = character's left = +X)."""
    return g2(X, sx * cx, cz, sx_, sz)


def seg(X, a, b, s):
    """Mirrored soft line from a=(x, z) to b=(x, z): creases and folds."""
    P2 = np.stack([np.abs(X[:, 0]), X[:, 2]], 1)
    a, b = np.array(a), np.array(b)
    t = np.clip(((P2 - a) @ (b - a)) / ((b - a) @ (b - a)), 0, 1)
    d = np.linalg.norm(P2 - a - t[:, None] * (b - a), axis=1)
    return np.exp(-0.5 * (d / s) ** 2)


def front(X):
    return sm(-0.15, -0.55, X[:, 1])


# --- materials ---------------------------------------------------------------
def skin_material(name):
    m = material(name, C["skin"], rough=0.42, sss=0.12, coat=0.08)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Subsurface Scale"].default_value = 0.01
    b.inputs["Coat Roughness"].default_value = 0.35

    def attr(n):
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_name = n
        return a.outputs["Fac"]

    def mix(fac, a, b_):
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        nt.links.new(fac, mx.inputs[0])
        for sock, v in ((mx.inputs[6], a), (mx.inputs[7], b_)):
            if isinstance(v, tuple):
                sock.default_value = (*v, 1.0)
            else:
                nt.links.new(v, sock)
        return mx.outputs[2]

    sk = C["skin"]
    bl = C["blush"]
    warm = (sk[0] * (1.1 + 0.1 * bl), sk[1] * (0.8 - 0.15 * bl), sk[2] * (0.75 - 0.1 * bl))
    col = mix(attr("Warm"), sk, warm)
    if C["freckles"]:
        tcf = nt.nodes.new("ShaderNodeTexCoord")
        nf = nt.nodes.new("ShaderNodeTexNoise")
        nf.inputs["Scale"].default_value = 70.0
        nt.links.new(tcf.outputs["Object"], nf.inputs["Vector"])
        rf = nt.nodes.new("ShaderNodeValToRGB")
        rf.color_ramp.elements[0].position, rf.color_ramp.elements[1].position = 0.6, 0.64
        nt.links.new(nf.outputs["Fac"], rf.inputs["Fac"])
        mf = nt.nodes.new("ShaderNodeMath")
        mf.operation = "MULTIPLY"
        nt.links.new(rf.outputs["Color"], mf.inputs[0])
        nt.links.new(attr("Freckle"), mf.inputs[1])
        col = mix(mf.outputs[0], col, (sk[0] * 0.5, sk[1] * 0.35, sk[2] * 0.3))
    col = mix(attr("Lip"), col, C["lip"])
    col = mix(attr("Shade"), col, (sk[0] * 0.35, sk[1] * 0.25, sk[2] * 0.22))
    # stubble: fine noise dots masked by the Stubble attribute
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 420.0
    nz.inputs["Detail"].default_value = 1.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[1].position = 0.62
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    dots = nt.nodes.new("ShaderNodeMath")
    dots.operation = "MULTIPLY"
    nt.links.new(ramp.outputs["Color"], dots.inputs[0])
    nt.links.new(attr("Stubble"), dots.inputs[1])
    tint = nt.nodes.new("ShaderNodeMath")
    tint.operation = "MULTIPLY"
    nt.links.new(attr("Stubble"), tint.inputs[0])
    tint.inputs[1].default_value = 0.35  # even shadow under the dots
    both = nt.nodes.new("ShaderNodeMath")
    both.operation = "ADD"
    nt.links.new(dots.outputs[0], both.inputs[0])
    nt.links.new(tint.outputs[0], both.inputs[1])
    clamp = nt.nodes.new("ShaderNodeClamp")
    nt.links.new(both.outputs[0], clamp.inputs["Value"])
    hc = C["hair_color"]
    col = mix(clamp.outputs[0], col, (hc[0] * 2 + sk[0] * 0.25, hc[1] * 2 + sk[1] * 0.25,
                                      hc[2] * 2 + sk[2] * 0.25))
    geo = nt.nodes.new("ShaderNodeNewGeometry")  # the head's inside, seen through the lips, reads as mouth
    col = mix(geo.outputs["Backfacing"], col, (0.05, 0.008, 0.01))
    nt.links.new(col, b.inputs["Base Color"])
    return m


def eye_material():
    m = bpy.data.materials.new("Eye")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.02
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Z"])
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(comb.outputs[0], ln.inputs[0])
    back = nt.nodes.new("ShaderNodeMath")
    back.operation = "GREATER_THAN"
    nt.links.new(sep.outputs["Y"], back.inputs[0])
    back.inputs[1].default_value = 0.0
    r = nt.nodes.new("ShaderNodeMath")
    r.operation = "ADD"
    nt.links.new(ln.outputs["Value"], r.inputs[0])
    nt.links.new(back.outputs[0], r.inputs[1])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    ir = C["iris"]
    stops = [(0.0, (0.004, 0.004, 0.004)), (0.19, (0.004, 0.004, 0.004)),
             (0.21, tuple(c * 0.6 for c in ir)), (0.40, tuple(min(1, c * 2.2) for c in ir)),
             (0.46, (0.01, 0.008, 0.007)), (0.50, (0.75, 0.72, 0.68)), (1.0, (0.8, 0.78, 0.75))]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, c in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (*c, 1)
    nt.links.new(r.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


SKIN = skin_material("Skin")
_sb = SKIN.node_tree.nodes["Principled BSDF"]
_sb.inputs["Roughness"].default_value, _sb.inputs["Coat Weight"].default_value = 0.52, 0.03
EYE = eye_material()
LASH = material("Lash", (0.008, 0.006, 0.006), rough=0.7)
BROW = material("Brow", C["brow_color"], rough=0.55)
HAIR = material("Hair", C["hair_color"], rough=0.6)
HAIR.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.2
MOUTH = material("MouthInside", (0.09, 0.015, 0.018), rough=0.6)
TEETH = material("Teeth", (0.78, 0.74, 0.66), rough=0.3, coat=0.3)
TONGUE = material("Tongue", (0.45, 0.1, 0.1), rough=0.45, sss=0.2)
TOP = material("Top", C["top"], rough=0.78, sheen=0.15)
SILVER = material("Silver", (0.8, 0.8, 0.82), rough=0.18, metal=1.0)
GOLD = material("Gold", (1.0, 0.66, 0.25), rough=0.2, metal=1.0)
METAL = GOLD if C["metal"] == "gold" else SILVER
FRAME = material("Frame", C["frame_color"], rough=0.3, coat=0.5)
ACCENT = material("Accent", C["accent"], rough=0.6)
OW = C["outer"]  # None | blazer | cardigan | varsity | puffer | puffer_vest | trench | techwear | track | flannel | vest
OUTER = material("Outer", C["outer_color"], rough=0.35 if OW and "puffer" in OW else 0.75,
                 sheen=0.4 if OW in ("cardigan", "vest") else 0.1, coat=0.3 if OW and "puffer" in OW else 0.0)
OUTER2 = material("OuterAccent", C["outer_accent"], rough=0.7)


def fabric(m, knit=False):
    """Soft wrinkles (large distorted noise) plus, for knits, a fine rib — bump only, colour untouched."""
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Distortion"].default_value = 9.0, 2.5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    if knit:
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.inputs["Scale"].default_value = 160.0
        nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
        rib = nt.nodes.new("ShaderNodeBump")
        rib.inputs["Strength"].default_value = 0.35
        nt.links.new(wv.outputs["Fac"], rib.inputs["Height"])
        nt.links.new(rib.outputs["Normal"], bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])


fabric(TOP, knit=C["top_type"] == "turtle")
if OW and "puffer" not in OW:
    fabric(OUTER, knit=OW in ("cardigan", "vest"))
if OW == "flannel":  # plaid: two crossed stripes over the base colour
    _nt = OUTER.node_tree
    _tc = _nt.nodes.new("ShaderNodeTexCoord")
    _ck = _nt.nodes.new("ShaderNodeTexChecker")
    _ck.inputs["Scale"].default_value = 18.0
    _ck.inputs["Color1"].default_value = (*C["outer_color"], 1)
    _ck.inputs["Color2"].default_value = (*C["outer_accent"], 1)
    _nt.links.new(_tc.outputs["Object"], _ck.inputs["Vector"])
    _nt.links.new(_ck.outputs["Color"], _nt.nodes["Principled BSDF"].inputs["Base Color"])
FADE = material("Fade", tuple(0.35 * h + 0.39 * k for h, k in zip(C["hair_color"], C["skin"])), rough=0.6)

# --- rig empties ---------------------------------------------------------------
ROOT = empty("CHAR_root", (0, 0, 0), COLL)
HEAD = empty("Head", (0, 0, PIVOT_Z), COLL, parent=ROOT)
GEO = empty("HeadGeo", (0, 0, HEAD_C - PIVOT_Z), COLL, parent=HEAD)
GEO.scale = (S, S, S)
CTRL = empty("FaceCtrl", (0, 0, 2.0), COLL, parent=GEO)
for n in ARKIT_NAMES:
    CTRL[n] = 0.0


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


def link(o, parent=GEO):
    for c in o.users_collection:
        c.objects.unlink(o)
    COLL.objects.link(o)
    o.parent = parent
    return o


# --- head mesh: cube-sphere → mouth slit → sculpt -------------------------------
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=79, use_grid_fill=True)
for v in bm.verts:
    v.co.normalize()

MW = C["mouth_width"]
slit = [f for f in bm.faces
        if all(v.co.y < -0.5 for v in f.verts)
        and abs(f.calc_center_median().x) < MW
        and min(v.co.z for v in f.verts) < PZ < max(v.co.z for v in f.verts)]
slit_verts = {v for f in slit for v in f.verts}
bmesh.ops.delete(bm, geom=slit, context="FACES")
for v in slit_verts:  # snap the lip edges onto the mouth line: closed mouth = dark seam
    v.co.z = PZ + (0.004 if v.co.z > PZ else -0.004)
bm.verts.ensure_lookup_table()
bm.verts.index_update()
P = np.array([v.co[:] for v in bm.verts])


def sculpt(P):
    X = P * np.array([HW, 0.92, FL])
    x, z = X[:, 0], X[:, 2]
    sx = np.sign(x)
    X[:, 1] = np.where(X[:, 1] < 0, X[:, 1] * 0.86, X[:, 1])  # broad, flat face plane
    t = sm(-0.15, -1.0, z)
    X[:, 0] *= 1 - (1 - C["jaw_width"]) * t ** 1.4  # jaw taper to the chin
    X[:, 1] = np.where(X[:, 1] > 0, X[:, 1] * (1 - 0.35 * t), X[:, 1])  # slim jaw from behind
    X[:, 1] += 0.10 * sm(0.0, 0.6, X[:, 1]) * np.exp(-((z - 0.45) / 0.45) ** 2)  # occiput
    side = sm(0.3, -0.3, X[:, 1])
    X[:, 0] += sx * C["jaw_corner"] * gm(X, 0.52, -0.66, 0.16, 0.16) * side
    # flat underside of the jaw: a soft max against a floor that drops toward the chin
    floor = -0.68 - 0.3 * sm(-0.1, -0.7, X[:, 1])
    X[:, 2] = 0.5 * (z + floor + np.sqrt((z - floor) ** 2 + 0.04 ** 2))
    F = front(X)
    X[:, 1] -= C["chin"] * g2(X, 0, -0.95, 0.22, 0.15) * F
    X[:, 2] -= 0.04 * g2(X, 0, -1.0, 0.25, 0.15) * F
    cb = C["cheekbone"] * gm(X, 0.5, -0.2, 0.13, 0.11) * side
    X[:, 0] += sx * cb * 0.6
    X[:, 1] -= cb * 0.5
    hol = C["hollow"] * gm(X, 0.45, -0.45, 0.11, 0.12) * side
    X[:, 0] -= sx * hol
    X[:, 1] += hol * 0.5
    X[:, 0] -= sx * 0.04 * gm(X, 0.7, 0.4, 0.12, 0.18)  # temples
    X[:, 1] -= C["brow_ridge"] * g2(X, 0, EZ + 0.17, 0.42, 0.06) * F  # brow ridge
    X[:, 1] += C["socket"] * gm(X, C["eye_spacing"], EZ, 0.12, 0.09) * F  # sockets
    # nose: ridge that grows toward the tip, ball tip, wings
    u = np.clip((EZ + 0.08 - z) / (EZ + 0.08 - ZT), 0, 1)
    NW = C["nose_width"]
    ridge = np.exp(-0.5 * (x / ((0.045 + 0.04 * u) * NW)) ** 2) * sm(EZ + 0.16, EZ + 0.04, z) * sm(ZT - 0.12, ZT - 0.03, z)
    X[:, 1] -= (0.04 + 0.09 * u) * ridge * F
    X[:, 1] -= C["nose_tip"] * g2(X, 0, ZT, 0.07 * NW, 0.065) * F
    wing = gm(X, 0.085 * NW, ZT - 0.03, 0.045 * NW, 0.04) * F
    X[:, 1] -= 0.07 * wing
    X[:, 0] += sx * 0.03 * wing
    X[:, 1] += C["fold"] * seg(X, (0.11, ZT - 0.04), (MW * HW * 0.8 + 0.06, MZ - 0.03), 0.018) * F  # nasolabial fold
    X[:, 1] -= 0.06 * g2(X, 0, -0.5, 0.28, 0.16) * F  # muzzle
    mwx = MW * HW * 0.8
    X[:, 1] -= 0.05 * C["lip_full"] * g2(X, 0, MZ + 0.035, mwx * 0.85, 0.03) * F
    X[:, 1] -= 0.06 * C["lip_full"] * g2(X, 0, MZ - 0.045, mwx * 0.8, 0.035) * F
    X[:, 1] += 0.035 * g2(X, 0, MZ - 0.14, 0.15, 0.035) * F  # groove under the lower lip
    X[:, 1] += 0.012 * g2(X, 0, -0.98, 0.025, 0.06) * F  # chin cleft
    X[:, 1] += 0.035 * gm(X, 0.045 * NW, ZT - 0.065, 0.02 * NW, 0.013) * F  # nostrils
    # plane breaks (the references' sculpted look): under the cheekbone, and along the jaw
    X[:, 1] += C["planes"] * seg(X, (0.5, -0.32), (0.3, MZ + 0.02), 0.035) * F
    X[:, 0] -= np.sign(x) * C["planes"] * 0.6 * seg(X, (0.62, -0.5), (0.3, -0.92), 0.04) * side
    X[:, 1] += 0.012 * g2(X, 0, (ZT + MZ) / 2 - 0.02, 0.022, 0.06) * F  # philtrum groove
    X[:, 1] += 0.014 * seg(X, (C["eye_spacing"] - 0.12, EZ + 0.13), (C["eye_spacing"] + 0.13, EZ + 0.1), 0.012) * F
    return X


X = sculpt(P)
for v, co in zip(bm.verts, X):
    v.co = co
bm.normal_update()
NRM = np.array([v.normal[:] for v in bm.verts])
me = bpy.data.meshes.new("HeadMesh")
bm.to_mesh(me)
bm.free()
for p in me.polygons:
    p.use_smooth = True
me.materials.append(SKIN)
head = link(bpy.data.objects.new("HeadMesh", me))
sub = head.modifiers.new("Subd", "SUBSURF")
sub.levels, sub.render_levels = 0, 1
F = front(X)


def surf_y(x, z):
    """Y of the sculpted face surface nearest (x, z)."""
    d = (X[:, 0] - x) ** 2 + (X[:, 2] - z) ** 2 + 10.0 * (X[:, 1] > -0.2)
    return float(X[np.argmin(d), 1])


# --- skin attributes (lip tint, stubble, warmth) ---------------------------------
MWX = MW * HW * 0.8
lipzone = np.exp(-((X[:, 0] / (MWX * 1.05)) ** 4)) * np.exp(-((X[:, 2] - MZ) / 0.07) ** 2) * F
lipmask = sm(0.4, 0.75, lipzone)
stub = C["stubble"] * sm(ZT - 0.02, ZT - 0.2, X[:, 2]) * sm(0.55, 0.15, X[:, 1]) * (1 - lipmask)
warm = np.clip((gm(X, 0.42, EZ - 0.25, 0.14, 0.12) * 0.6 + g2(X, 0, ZT, 0.08, 0.08) * 0.5) * (1 + 1.5 * C["blush"]),
               0, 1) * F
ES_ = C["eye_spacing"]
freck = np.clip(C["freckles"] * (gm(X, 0.28, EZ - 0.22, 0.15, 0.08) + g2(X, 0, ZT + 0.12, 0.07, 0.08)), 0, 1) * F
shade = np.clip(1.6 * gm(X, 0.045 * C["nose_width"], ZT - 0.065, 0.016 * C["nose_width"], 0.01)  # nostrils
                + 0.5 * seg(X, (ES_ - 0.11, EZ + 0.13), (ES_ + 0.12, EZ + 0.1), 0.01)  # lid crease
                + 0.6 * gm(X, MWX, MZ, 0.018, 0.014), 0, 1) * F  # mouth corners
for name, vals in (("Lip", lipmask), ("Stubble", stub), ("Warm", warm), ("Freckle", freck), ("Shade", shade)):
    ca = me.color_attributes.new(name, "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", np.repeat(vals.astype(np.float32), 4))

# --- face shapes ------------------------------------------------------------------
PIVOT = np.array([0.0, 0.15, 0.0])
ax = np.abs(X[:, 0])
w = 0.006 + 0.25 * sm(MWX * 0.9, MWX * 1.8, ax)
JAW = sm(MZ + 0.3 * w, MZ - w, X[:, 2]) * sm(0.45, 0.0, X[:, 1])
UP = lipzone * (X[:, 2] > MZ)
LO = lipzone * (X[:, 2] < MZ)
cen = np.clip(1 - (X[:, 0] / MWX) ** 2, 0, 1)


def rot_x(V, a):
    c, s = math.cos(a), math.sin(a)
    R = V - PIVOT
    return np.stack([R[:, 0], R[:, 1] * c - R[:, 2] * s, R[:, 1] * s + R[:, 2] * c], 1) + PIVOT


def vec(W, d):
    return W[:, None] * np.array(d)[None, :]


def corner(sx):
    return gside(X, sx, MWX, MZ, 0.08, 0.07) * F


def half(sx):
    return sm(-0.02, 0.05, sx * X[:, 0])


D_JAW = (rot_x(X, JAW_MAX) - X) * JAW[:, None]
SHAPES = {
    "jawOpen": D_JAW,
    "jawForward": vec(JAW, (0, -0.06, 0)),
    "jawLeft": vec(JAW, (0.05, 0, 0)),
    "jawRight": vec(JAW, (-0.05, 0, 0)),
    "mouthClose": -D_JAW * sm(0.1, 0.5, LO)[:, None] + vec(UP, (0, 0, -0.01)),
    "mouthFunnel": vec(UP * cen, (0, -0.04, 0.035)) + vec(LO * cen, (0, -0.04, -0.045))
    + np.stack([-0.25 * X[:, 0] * lipzone, 0 * ax, 0 * ax], 1),
    "mouthPucker": np.stack([-0.35 * X[:, 0] * lipzone, -0.06 * lipzone, 0 * ax], 1),
    "mouthLeft": vec(lipzone, (0.04, 0, 0)),
    "mouthRight": vec(lipzone, (-0.04, 0, 0)),
    "mouthRollLower": vec(LO, (0, 0.03, 0.012)),
    "mouthRollUpper": vec(UP, (0, 0.03, -0.012)),
    "mouthShrugLower": vec(LO, (0, -0.02, 0.015)) + vec(g2(X, 0, -0.9, 0.2, 0.15) * F, (0, -0.01, 0.03)),
    "mouthShrugUpper": vec(UP, (0, -0.01, 0.015)),
    "cheekPuff": np.stack([np.sign(X[:, 0]) * 0.05, -0.03 * ax ** 0, 0 * ax], 1)
    * gm(X, 0.4, MZ + 0.05, 0.13, 0.13)[:, None] * F[:, None],
}
for side, sx in (("Left", 1), ("Right", -1)):
    K, Hh = corner(sx), half(sx)
    cheek = gside(X, sx, 0.38, MZ + 0.2, 0.12, 0.1) * F
    SHAPES.update({
        f"mouthSmile{side}": vec(K, (sx * 0.045, 0.03, 0.075)) + vec(cheek, (sx * 0.015, -0.04, 0.045)),
        f"mouthFrown{side}": vec(K, (sx * 0.01, 0.01, -0.075)),
        f"mouthStretch{side}": vec(K, (sx * 0.04, 0.01, -0.006)),
        f"mouthDimple{side}": vec(K, (sx * 0.01, 0.025, 0)),
        f"mouthPress{side}": vec(UP * Hh, (0, 0, -0.008)) + vec(LO * Hh, (0, 0, 0.008)),
        f"mouthLowerDown{side}": vec(LO * Hh, (0, 0, -0.03)),
        f"mouthUpperUp{side}": vec(UP * Hh, (0, 0, 0.03)),
        f"cheekSquint{side}": vec(gside(X, sx, 0.32, EZ - 0.15, 0.13, 0.08) * F, (0, -0.01, 0.035)),
        f"noseSneer{side}": vec(gside(X, sx, 0.1, ZT, 0.06, 0.06) * F, (0, -0.005, 0.03)),
        f"browDown{side}": vec(gside(X, sx, 0.25, EZ + 0.2, 0.15, 0.08) * F, (0, -0.02, -0.05)),
        f"browOuterUp{side}": vec(gside(X, sx, 0.42, EZ + 0.22, 0.12, 0.08) * F, (0, 0, 0.03)),
    })
SHAPES["browInnerUp"] = vec(g2(X, 0, EZ + 0.24, 0.18, 0.1) * F, (0, 0, 0.05))

# resting mouth: a touch of smile baked into the base so neutral doesn't read as sulking
X = X + C["smile_rest"] * (SHAPES["mouthSmileLeft"] + SHAPES["mouthSmileRight"])
me.vertices.foreach_set("co", X.astype(np.float32).ravel())
head.shape_key_add(name="Basis")
for name, D in SHAPES.items():
    kb = head.shape_key_add(name=name, from_mix=False)
    kb.data.foreach_set("co", (X + D).astype(np.float32).ravel())
    drive(kb, "value", "v", {"v": name})

# --- mouth interior: cavity, teeth, tongue (lower parts ride the jaw) -------------
YS = surf_y(0, MZ)
JAWP = empty("JawPivot", tuple(PIVOT), COLL, parent=GEO)
drive(JAWP, "rotation_euler", f"{JAW_MAX}*j", {"j": "jawOpen"}, index=0)
link(ellipsoid("MouthCavity", (0, YS + 0.36, MZ - 0.03), (MWX * 1.5, 0.2, 0.12), COLL, MOUTH))


def teeth(name, z, parent, offset, back=0.0):
    cd = bpy.data.curves.new(name, "CURVE")
    cd.dimensions = "3D"
    cd.extrude, cd.bevel_depth, cd.bevel_resolution = 0.028, 0.012, 2
    sp = cd.splines.new("NURBS")
    y = YS + back
    pts = [(-MWX * 0.8, y + 0.17, z), (-MWX * 0.55, y + 0.1, z), (0, y + 0.08, z),
           (MWX * 0.55, y + 0.1, z), (MWX * 0.8, y + 0.17, z)]
    sp.points.add(len(pts) - 1)
    for p, co in zip(sp.points, pts):
        p.co = (co[0] - offset[0], co[1] - offset[1], co[2] - offset[2], 1)
    sp.order_u, sp.use_endpoint_u = 3, True
    o = bpy.data.objects.new(name, cd)
    COLL.objects.link(o)
    o.data.materials.append(TEETH)
    o.parent = parent
    return o


teeth("TeethUpper", MZ + 0.05, GEO, (0, 0, 0))
teeth("TeethLower", MZ - 0.05, JAWP, tuple(PIVOT), back=0.1)
tongue = ellipsoid("Tongue", (0, YS + 0.3 - PIVOT[1], MZ - 0.07 - PIVOT[2]), (MWX * 0.7, 0.11, 0.035),
                   COLL, TONGUE)
tongue.parent = JAWP
drive(tongue, "delta_location", "-0.2*t", {"t": "tongueOut"}, index=1)

# --- eyes + lids --------------------------------------------------------------------
ER, ES = C["eye_size"], C["eye_spacing"]


def cap(name, keep, mats, thick=0.13):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v.co)], context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    sol = o.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness, sol.offset, sol.material_offset_rim = thick, 1.0, 1
    o.modifiers.new("Subd", "SUBSURF").render_levels = 1
    return o


for side, sx in (("Left", 1), ("Right", -1)):
    ec = (sx * ES, surf_y(sx * ES, EZ) + ER * 0.7, EZ)
    rig = link(empty(f"EyeRig{side}", ec, COLL))  # stretches eye + lids together: almond, not bead
    rig.scale = (C["eye_wide"], 1.0, C["eye_tall"])
    eye = link(ellipsoid(f"Eye{side}", (0, 0, 0), (ER, ER, ER), COLL, EYE, segs=48), rig)
    drive(eye, "rotation_euler", "0.35*(d-u)", {"d": f"eyeLookDown{side}", "u": f"eyeLookUp{side}"}, index=0)
    drive(eye, "rotation_euler", f"{0.4 * sx}*(o-i)", {"o": f"eyeLookOut{side}", "i": f"eyeLookIn{side}"},
          index=2)
    rest = C["lid_rest"]
    up = link(cap(f"LidUpper{side}", lambda c: c.z > 0 and c.y < 0.55, (SKIN, LASH),
                  0.26 if C["lashes"] else 0.13))
    up.parent, up.location, up.scale = rig, (0, 0, 0), (ER * 1.06,) * 3
    drive(up, "rotation_euler", f"{rest}+b*({0.62 - rest})-0.75*w+0.22*s",
          {"b": f"eyeBlink{side}", "w": f"eyeWide{side}", "s": f"eyeSquint{side}"}, index=0)
    lo = link(cap(f"LidLower{side}", lambda c: c.z < 0 and c.y < 0.55, (SKIN, LASH)))
    lo.parent, lo.location, lo.scale = rig, (0, 0, 0), (ER * 1.05,) * 3
    drive(lo, "rotation_euler", "0.66-0.3*s-0.15*c-0.04*b",
          {"s": f"eyeSquint{side}", "c": f"cheekSquint{side}", "b": f"eyeBlink{side}"}, index=0)

    # brow: tapered chunky stroke on the ridge, pivoting about its centre
    bc = (sx * 0.30, surf_y(sx * 0.30, EZ + 0.19) + 0.02, EZ + 0.19)
    cd = bpy.data.curves.new(f"Brow{side}", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth, cd.bevel_resolution = 0.055 * C["brow_thick"], 3
    cd.use_fill_caps = True
    sp = cd.splines.new("NURBS")
    ba = C["brow_angle"]
    pts = [(-0.18, -0.01, -0.03 - 0.25 * ba, 0.9), (-0.06, 0.0, 0.012, 1.0),
           (0.08, 0.025, 0.014, 0.8), (0.19, 0.075, -0.03, 0.3)]
    sp.points.add(len(pts) - 1)
    for p, (px, py, pz, r) in zip(sp.points, pts):
        p.co, p.radius = (sx * px, py, pz, 1), r
    sp.order_u, sp.use_endpoint_u = 3, True
    brow = link(bpy.data.objects.new(f"Brow{side}", cd))
    brow.data.materials.append(BROW)
    brow.location, brow.scale = bc, (1.0, 0.55, 1.0)
    drive(brow, "delta_location", "0.1*i+0.08*o-0.08*d",
          {"i": "browInnerUp", "o": f"browOuterUp{side}", "d": f"browDown{side}"}, index=2)
    drive(brow, "rotation_euler", f"{sx}*(0.35*i-0.25*o+0.3*d)",
          {"i": "browInnerUp", "o": f"browOuterUp{side}", "d": f"browDown{side}"}, index=1)

    ear = link(ellipsoid(f"Ear{side}", (sx * HW * 1.0, 0.12, EZ - 0.1), (0.08, 0.16, 0.25), COLL, SKIN))
    ear.rotation_euler = (0.1, 0, sx * 0.3)
    er = C["earring"]  # None | "hoop_left" | "hoops" | "studs"
    if er == "studs":
        link(ellipsoid(f"Stud{side}", (sx * HW * 1.07, 0.07, EZ - 0.3), (0.026,) * 3, COLL, METAL, subd=0))
    elif er == "hoops" or (er == "hoop_left" and sx == 1):
        big = er == "hoops"
        bpy.ops.mesh.primitive_torus_add(major_radius=0.1 if big else 0.045, minor_radius=0.012 if big else 0.009,
                                         location=(sx * HW * 1.08, 0.08, EZ - (0.42 if big else 0.33)),
                                         rotation=(0, math.pi / 2, 0))
        ring = link(bpy.context.active_object)
        ring.data.materials.append(METAL)

EYE_Y = surf_y(0, EZ)
link(empty("FaceAnchor", (0, EYE_Y, 0.0), COLL))
link(empty("EyeFocus", (0, surf_y(ES, EZ) - 0.02, EZ), COLL))
bpy.data.objects["FaceAnchor"]["head_height"] = 2.2 * S

# --- hair: scalp cap + clay locks in the character's style ---------------------------
HS = C["hair"]  # curls | swoop | messy | long | bob | ponytail
HL_FRONT = {"swoop": 0.42, "ponytail": 0.42, "messy": 0.33}.get(HS, 0.36)
HL_BACK = {"long": -0.8, "bob": -0.75}.get(HS, -0.54)
hairline = HL_FRONT + (HL_BACK - HL_FRONT) * (P[:, 1] + 1) / 2
in_hair = P[:, 2] > hairline
SLEEK = HS in ("swoop", "long", "bob", "ponytail")
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
CAP_OFF = 0.03 if SLEEK else 0.06
for v in bm.verts:
    v.co = v.co + v.normal * CAP_OFF
keep = {f for f in bm.faces if all(in_hair[v.index] for v in f.verts)}
edge = [v for v in {v for f in keep for v in f.verts} if any(g not in keep for g in v.link_faces)]
ei = np.array([v.index for v in edge])
Pe = P[ei].copy()  # slide the cap's edge onto the exact hairline curve: smooth, not stair-stepped
Pe[:, 2] = hairline[ei]
Pe[:, :2] *= (np.sqrt(np.clip(1 - Pe[:, 2] ** 2, 0, 1)) / np.linalg.norm(Pe[:, :2], axis=1))[:, None]
for v, co, k in zip(edge, sculpt(Pe), ei):
    v.co = co + NRM[k] * CAP_OFF
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES")
cme = bpy.data.meshes.new("HairCap")
bm.to_mesh(cme)
bm.free()
for p in cme.polygons:
    p.use_smooth = True
cme.materials.append(FADE if HS == "swoop" else HAIR)
cap_o = link(bpy.data.objects.new("HairCap", cme))
tex = bpy.data.textures.new("HairLumps", "CLOUDS")
tex.noise_scale = 0.12
disp = cap_o.modifiers.new("Lumps", "DISPLACE")
disp.texture, disp.strength, disp.mid_level = tex, 0.015 if SLEEK else 0.06, 0.5

E_FRONT, E_BACK = np.array([HW, 0.8, FL]), np.array([HW, 1.02, FL])


def outside(p, off):
    """Push a point out of the skull (two half-ellipsoids) plus an offset."""
    q = np.linalg.norm(p / (E_BACK if p[1] > 0 else E_FRONT))
    return p * (1 + off) / q if q < 1 + off else p


def grow(p, d, n, step, g, off=0.07, pull=None, stop=None, frame=False):
    """March a lock: bend by g (and toward pull), never sinking into the head."""
    pts, d = [p], d / np.linalg.norm(d)
    for _ in range(n):
        if pull is not None:
            d = d + 0.5 * (pull - p) / (np.linalg.norm(pull - p) + 1e-6)
        d = d + g
        d = d / np.linalg.norm(d)
        p = outside(p + d * step, off)
        if frame and p[1] < 0.3:  # curtain: ease out beside the face, never across it
            k = float(sm(0.55, 0.15, p[2]))
            ax_ = abs(p[0]) + k * max(0.0, HW * 1.06 - abs(p[0]))
            p = np.array([math.copysign(ax_, p[0] or 1.0), p[1], p[2]])
        pts.append(p)
        if stop is not None and stop(p):
            break
    return pts


def tangent(n, v):
    v = np.asarray(v, float)
    v = v - (v @ n) * n
    return v / (np.linalg.norm(v) + 1e-6)


def roots(count, line_bias=2.0, above=-9.0):
    w = (P[:, 2] > hairline + 0.02) * (P[:, 2] > above) * np.where(P[:, 2] < hairline + 0.25, line_bias, 1.0)
    return RNG.choice(len(P), size=count, replace=False, p=w / w.sum())


def locks(name, strands, mat=HAIR):
    cd = bpy.data.curves.new(name, "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth, cd.bevel_resolution = 1.0, 3
    for pts, r0, r1 in strands:
        sp = cd.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        for j, (pt, co) in enumerate(zip(sp.points, pts)):
            u = j / (len(pts) - 1)
            pt.co, pt.radius = (*co, 1), r0 + (r1 - r0) * u ** 1.5
        sp.order_u, sp.use_endpoint_u = min(4, len(pts)), True
    o = link(bpy.data.objects.new(name, cd))
    o.data.materials.append(mat)
    return o


strands = []
if HS == "swoop":  # short faded sides, top swept up and back
    for i in roots(170, line_bias=3.0, above=0.2):
        n, fwd = NRM[i], P[i, 1] < -0.3
        d = tangent(n, (0.15 * np.sign(X[i, 0]) + RNG.normal(0, 0.15), 0.6, 1.0 if fwd else 0.3))
        pts = grow(X[i] + n * 0.03, d, int(RNG.integers(7, 11)), 0.055, np.array([0, 0.05, -0.035]),
                   off=0.09 + 0.05 * fwd)
        strands.append((pts, RNG.uniform(0.04, 0.055), 0.01))
elif HS == "messy":  # short tufts every which way, fringe falling forward
    for i in roots(280):
        n = NRM[i]
        d = tangent(n, RNG.normal(0, 1, 3) + np.array([0, -0.6 if P[i, 1] < -0.2 else 0.3, -0.8]))
        pts = grow(X[i] + n * 0.04, d + 0.4 * n, int(RNG.integers(4, 7)), 0.05, np.array([0, 0, -0.05]), off=0.1)
        strands.append((pts, RNG.uniform(0.04, 0.055), 0.008))
elif HS in ("long", "bob"):  # centre part, falling past the jaw (bob) or the shoulders (long)
    floor_z = -1.9 if HS == "long" else -0.85
    for i in roots(520, line_bias=1.5):
        n, side = NRM[i], (1.0 if X[i, 0] >= 0 else -1.0)
        pts = grow(X[i] + n * 0.03, tangent(n, (side * 0.8, 0.15, -0.6)), 70, 0.05,
                   np.array([0, 0.005, -0.09]), off=0.08, stop=lambda p: p[2] < floor_z, frame=True)
        if HS == "bob":  # ends tuck toward the jaw
            pts.append(pts[-1] + np.array([-side * 0.05, -0.02, -0.03]))
        strands.append((pts, RNG.uniform(0.05, 0.062), 0.028 if HS == "bob" else 0.018))
elif HS == "ponytail":  # everything pulled to a high tie, tail swinging down the back
    T = np.array([0.0, 0.85, 0.75])
    for i in roots(360, line_bias=1.5):
        n = NRM[i]
        pts = grow(X[i] + n * 0.02, tangent(n, T - X[i]), 40, 0.05, np.zeros(3), off=0.045, pull=T,
                   stop=lambda p: np.linalg.norm(p - T) < 0.1)
        strands.append((pts, 0.05, 0.042))
    for _ in range(40):
        pts = grow(T + RNG.normal(0, 0.03, 3), np.array([0, 0.8, 0.1]) + RNG.normal(0, 0.2, 3), 16, 0.07,
                   np.array([0, 0.01, -0.18]), off=0.12)
        strands.append((pts, 0.05, 0.008))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.08, minor_radius=0.035, location=tuple(T),
                                     rotation=(math.pi / 2 - 0.6, 0, 0))
    link(bpy.context.active_object).data.materials.append(ACCENT)
if strands:
    locks("Locks", [st for st in strands if len(st[0]) > 1])

if HS == "curls":
    cd = bpy.data.curves.new("Curls", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth, cd.bevel_resolution = 1.0, 3
    near_line = P[:, 2] < hairline + 0.25
    wts = np.where(P[:, 2] > hairline + 0.02, 1.0, 0.0) * np.where(near_line, 2.5, 1.0)
    for i in RNG.choice(len(P), size=360, replace=False, p=wts / wts.sum()):
        n = NRM[i]
        down = np.array([0.0, -0.5 if P[i, 1] < -0.2 else 0.2, -1.0])
        down -= (down @ n) * n  # coils lie along the scalp and hang, so they show their spiral side
        a = 0.25 * n + down / (np.linalg.norm(down) + 1e-6) + RNG.normal(0, 0.3, 3)
        a /= np.linalg.norm(a)
        e1 = np.cross(a, [1.0, 0.0, 0.0] if abs(a[0]) < 0.9 else [0.0, 1.0, 0.0])
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(a, e1)
        base = X[i] + n * 0.1
        cs = C["curl_scale"]
        turns, r, h = RNG.uniform(1.3, 2.0), cs * RNG.uniform(0.045, 0.06), cs * RNG.uniform(0.1, 0.17)
        tube, ph = cs * RNG.uniform(0.03, 0.038), RNG.uniform(0, 2 * math.pi)
        k = int(turns * 10) + 2
        sp = cd.splines.new("NURBS")
        sp.points.add(k - 1)
        for j, p in enumerate(sp.points):
            u = j / (k - 1)
            th = ph + 2 * math.pi * turns * u
            co = base + a * h * u + r * min(1, 3 * u + 0.3) * (math.cos(th) * e1 + math.sin(th) * e2)
            p.co, p.radius = (*co, 1), tube * (1 - 0.6 * u ** 2)
        sp.order_u, sp.use_endpoint_u = 4, True
    curls = link(bpy.data.objects.new("Curls", cd))
    curls.data.materials.append(HAIR)


# --- facial hair: a masked, displaced twin of the head (shares shape keys → rides the jaw) ---
if C["beard"]:
    gap = np.exp(-((X[:, 0] / (MWX * 1.35)) ** 4)) * np.exp(-((X[:, 2] - MZ) / 0.06) ** 2)
    wb = C["beard"] * sm(ZT - 0.03, ZT - 0.12, X[:, 2]) * sm(0.62, 0.25, X[:, 1]) * (1 - sm(0.3, 0.7, gap))
    vg = head.vertex_groups.new(name="Beard")
    for k in np.where(wb > 0.02)[0]:
        vg.add([int(k)], float(wb[k]), "REPLACE")
    beard = link(head.copy())
    beard.name = "Beard"
    beard.modifiers.clear()
    mk = beard.modifiers.new("Mask", "MASK")
    mk.vertex_group, mk.threshold = "Beard", 0.25
    dp = beard.modifiers.new("Fluff", "DISPLACE")
    dp.direction, dp.vertex_group, dp.texture, dp.strength, dp.mid_level = "NORMAL", "Beard", tex, 0.12, 0.15
    beard.modifiers.new("Subd", "SUBSURF").render_levels = 1
    beard.material_slots[0].link = "OBJECT"
    beard.material_slots[0].material = HAIR

# --- glasses -------------------------------------------------------------------------------
if C["glasses"]:
    e = 2.0 if C["glasses"] == "round" else 5.0  # superellipse exponent: circle vs soft rectangle
    gy = surf_y(ES, EZ) - ER * 0.3 - 0.07
    rw, rh = ER * 1.3, ER * (1.3 if C["glasses"] == "round" else 0.95)
    cd = bpy.data.curves.new("Glasses", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth, cd.bevel_resolution = 0.02, 2
    for sx in (1, -1):
        sp = cd.splines.new("NURBS")
        sp.points.add(31)
        for k, pt in enumerate(sp.points):
            t = 2 * math.pi * k / 32
            c, s_ = math.cos(t), math.sin(t)
            pt.co = (sx * ES + rw * math.copysign(abs(c) ** (2 / e), c), gy,
                     EZ + rh * math.copysign(abs(s_) ** (2 / e), s_), 1)
        sp.use_cyclic_u, sp.order_u = True, 4
        tp = cd.splines.new("NURBS")  # temple arm back to the ear
        tp.points.add(2)
        for pt, co in zip(tp.points, ((sx * (ES + rw), gy, EZ + 0.03), (sx * HW * 1.02, 0.0, EZ + 0.05),
                                      (sx * HW * 0.98, 0.25, EZ - 0.05))):
            pt.co = (*co, 1)
        tp.order_u, tp.use_endpoint_u = 3, True
    br = cd.splines.new("NURBS")
    br.points.add(2)
    for pt, co in zip(br.points, ((ES - rw, gy, EZ + 0.03), (0, gy - 0.01, EZ + 0.07), (-(ES - rw), gy, EZ + 0.03))):
        pt.co = (*co, 1)
    br.order_u, br.use_endpoint_u = 3, True
    link(bpy.data.objects.new("Glasses", cd)).data.materials.append(FRAME)

# --- neck + body (metres, on the root) -------------------------------------------------
NECK_TOP = HEAD_C - 0.6 * S
bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=C["neck_radius"] * 1.25, radius2=C["neck_radius"] * 0.85,
                                depth=NECK_TOP - SHOULDER_Z + 0.06,
                                location=(0, 0.01, (NECK_TOP + SHOULDER_Z - 0.06) / 2))
neck = link(bpy.context.active_object, ROOT)
neck.name = "Neck"
neck.data.materials.append(SKIN)
for p in neck.data.polygons:
    p.use_smooth = True


def blob(name, center, radii, mat, power=0.75, res=20, slope=0.0):
    """Superellipsoid: power < 1 squares it off (boxy shirt); slope drops the top corners (shoulders)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=res, use_grid_fill=True)
    for v in bm.verts:
        v.co.normalize()
        v.co = [math.copysign(abs(c) ** power, c) * r for c, r in zip(v.co, radii)]
        if v.co.z > 0:
            v.co.z -= slope * radii[2] * (v.co.x / radii[0]) ** 2 * (v.co.z / radii[2])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.location, o.parent = center, ROOT
    o.modifiers.new("Subd", "SUBSURF").render_levels = 1
    return o


TW = C["torso_w"]
KW = TW / 0.205
blob("Torso", (0, 0.03, 0.84), (TW, 0.115, 0.23), TOP, power=0.62, slope=0.3)


def plate(name, pts, mat, thick=0.006):
    """Flat rounded polygon with thickness: lapels, the open-collar V."""
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in pts])
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.parent = ROOT
    o.modifiers.new("Thick", "SOLIDIFY").thickness = thick
    o.modifiers.new("Subd", "SUBSURF").render_levels = 2
    return o


def tube(name, pts, mat, cyclic=False):
    cd = bpy.data.curves.new(name, "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth, cd.bevel_resolution, cd.use_fill_caps = 1.0, 4, True
    sp = cd.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, (co, r) in zip(sp.points, pts):
        p.co, p.radius = (*co, 1), r
    sp.order_u, sp.use_endpoint_u, sp.use_cyclic_u = min(4, len(pts)), not cyclic, cyclic
    o = bpy.data.objects.new(name, cd)
    COLL.objects.link(o)
    o.parent = ROOT
    o.data.materials.append(mat)
    return o


def beads(name, pts, r, mat):
    bm = bmesh.new()
    for p_ in pts:
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r, matrix=Matrix.Translation(p_))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.parent = ROOT
    return o


def ring(name, center, rx, ry, r, mat, n=16, tilt=0.0):
    pts = [((center[0] + rx * math.cos(2 * math.pi * k / n),
             center[1] + ry * math.sin(2 * math.pi * k / n) * math.cos(tilt),
             center[2] + ry * math.sin(2 * math.pi * k / n) * math.sin(tilt)), r) for k in range(n)]
    return tube(name, pts, mat, cyclic=True)


SLEEVED = OW not in (None, "vest", "puffer_vest")
PUFF = 0.022 if OW == "puffer" else (0.008 if SLEEVED else 0.0)
ARM_PATH = [((0.09 * KW, 0.03, 0.95), 0.05), ((0.17 * KW, 0.03, 0.955), 0.058 * KW ** 0.5),
            ((0.225 * KW, -0.02, 0.82), 0.048 * KW ** 0.5), ((0.19, -0.26, 0.80), 0.045), ((0.17, -0.33, 0.795), 0.04)]
for sx in (1, -1):
    arm = [((sx * x, y, z), r + PUFF) for (x, y, z), r in ARM_PATH]
    sleeve = OUTER2 if OW == "varsity" else (OUTER if SLEEVED else TOP)
    tube(f"Arm{sx}", arm[:3], sleeve)  # upper arm to the elbow
    tube(f"Forearm{sx}", arm[2:], sleeve)  # elbow to wrist: pivots for gestures
    ellipsoid(f"ElbowBall{sx}", arm[2][0], (arm[2][1],) * 3, COLL, sleeve, segs=16).parent = ROOT
    empty(f"Elbow{'L' if sx == 1 else 'R'}", arm[2][0], COLL, parent=ROOT)
    if OW == "track":  # stripes down the outside of each upper sleeve
        tube(f"Stripe{sx}", [((sx * (x + r * 0.95), y, z + 0.01), 0.006) for (x, y, z), r in ARM_PATH[1:3]], ACCENT)
    # resting hand: palm, four fingers curling onto the desk, thumb tucked along the inside
    hk = 0.9 if TW < 0.19 else 1.0
    ellipsoid(f"Palm{sx}", (sx * 0.162, -0.375, 0.785), (0.033 * hk, 0.045 * hk, 0.016 * hk), COLL, SKIN,
              segs=16).parent = ROOT
    for f_ in range(4):
        fx = sx * (0.162 + (f_ - 1.5) * 0.0165 * hk)
        ln = (0.05 - 0.008 * abs(f_ - 1.3)) * hk
        tube(f"Finger{sx}{f_}", [((fx, -0.41, 0.789), 0.0085 * hk), ((fx, -0.41 - ln * 0.7, 0.787), 0.0078 * hk),
                                 ((fx, -0.41 - ln, 0.776), 0.007 * hk)], SKIN)
    tube(f"Thumb{sx}", [((sx * 0.14, -0.355, 0.792), 0.011 * hk), ((sx * 0.128, -0.39, 0.792), 0.009 * hk),
                        ((sx * 0.125, -0.415, 0.786), 0.008 * hk)], SKIN)

NR = C["neck_radius"] * 1.25  # neck radius at the base
TT = C["top_type"]  # shirt | tee | hoodie | turtle | zip
if TT == "shirt":  # open camp collar
    plate("ChestV", [(-0.035, -0.07, 1.05), (0.035, -0.07, 1.05), (0, -0.088, 0.94)], SKIN, thick=0.004)
    for sx in (1, -1):
        plate(f"Lapel{sx}", [(sx * 0.045, -0.075, 1.045), (sx * 0.004, -0.098, 0.935), (sx * 0.095, -0.098, 0.965)],
              TOP)
    tube("Collar", [((0.04, -0.09, 0.985), 0.011), ((0.062, -0.05, 1.035), 0.013),
                    ((0.048, 0.02, 1.06), 0.013), ((0, 0.05, 1.068), 0.013), ((-0.048, 0.02, 1.06), 0.013),
                    ((-0.062, -0.05, 1.035), 0.013), ((-0.04, -0.09, 0.985), 0.011)], TOP)
elif TT in ("tee", "hoodie"):
    ring("Neckband", (0, 0.005, SHOULDER_Z - 0.005), NR + 0.012, NR + 0.018, 0.011, TOP, tilt=0.25)
    if TT == "hoodie":
        tube("Hood", [((0.1, -0.04, 1.0), 0.03), ((0.115, 0.05, 1.05), 0.05), ((0, 0.11, 1.09), 0.06),
                      ((-0.115, 0.05, 1.05), 0.05), ((-0.1, -0.04, 1.0), 0.03)], TOP)
        for sx in (1, -1):
            tube(f"Drawstring{sx}", [((sx * 0.03, -0.095, 1.02), 0.0045), ((sx * 0.034, -0.11, 0.95), 0.0045),
                                     ((sx * 0.036, -0.112, 0.9), 0.0065)], ACCENT)
elif TT == "turtle":
    tube("Turtleneck", [((0, 0.01, SHOULDER_Z - 0.04), NR * 1.5), ((0, 0.01, SHOULDER_Z + 0.03), NR * 1.3),
                        ((0, 0.01, SHOULDER_Z + 0.075), NR * 1.3)], TOP)
    ring("TurtleFold", (0, 0.01, SHOULDER_Z + 0.06), NR * 1.32, NR * 1.32, 0.012, TOP)
elif TT == "zip":
    tube("StandCollar", [((0.025, -0.08, 1.07), 0.014), ((0.06, -0.04, 1.075), 0.016), ((0.05, 0.04, 1.08), 0.016),
                         ((0, 0.06, 1.082), 0.016), ((-0.05, 0.04, 1.08), 0.016), ((-0.06, -0.04, 1.075), 0.016),
                         ((-0.025, -0.08, 1.07), 0.014)], TOP)
    tube("Zipper", [((0, -0.083, 1.06), 0.005), ((0, -0.112, 0.95), 0.005), ((0, -0.118, 0.8), 0.005),
                    ((0, -0.1, 0.63), 0.005)], ACCENT)

# --- outer layer: open front panels (jackets) or a closed shell (puffer, vest) -------------------
if OW:
    closed = OW in ("puffer", "puffer_vest", "vest")
    if closed:
        grow_ = 1.1 if "puffer" in OW else 1.05
        blob("OuterShell", (0, 0.03, 0.84), (TW * grow_, 0.115 * grow_, 0.235), OUTER, power=0.62, slope=0.3)
    else:
        for sx in (1, -1):
            blob(f"Panel{sx}", (sx * TW * 0.6, 0.03, 0.84), (TW * 0.52, 0.125, 0.24), OUTER, power=0.62, slope=0.3)
    if OW in ("blazer", "trench"):
        wide = 1.4 if OW == "trench" else 1.0
        for sx in (1, -1):
            plate(f"OuterLapel{sx}", [(sx * 0.05, -0.085, 1.05), (sx * 0.035, -0.128, 0.86),
                                      (sx * (0.035 + 0.075 * wide), -0.125, 0.97)], OUTER, thick=0.008)
    if OW in ("puffer", "puffer_vest"):
        for k, z in enumerate((0.68, 0.76, 0.84, 0.92)):
            ring(f"Quilt{k}", (0, 0.03, z), TW * 1.03, 0.118, 0.012, OUTER, n=24)
        ring("PufferCollar", (0, 0.0, SHOULDER_Z + 0.02), NR + 0.02, NR + 0.025, 0.02, OUTER)
    if OW == "vest":
        plate("VestV", [(-0.05, -0.11, 1.03), (0.05, -0.11, 1.03), (0, -0.125, 0.88)], TOP, thick=0.004)
    if OW == "varsity":
        ring("RibCollar", (0, 0.005, SHOULDER_Z), NR + 0.02, NR + 0.026, 0.014, OUTER2, tilt=0.25)
        beads("Snaps", [(0.032, -0.128, z) for z in (0.75, 0.83, 0.91, 0.99)], 0.008, ACCENT)
    if OW == "cardigan":
        beads("Buttons", [(0.03, -0.13, z) for z in (0.72, 0.8, 0.88, 0.96)], 0.009, ACCENT)
    if OW == "techwear":
        for sx in (1, -1):
            tube(f"Strap{sx}", [((sx * 0.13, -0.03, 1.02), 0.009), ((0, -0.135, 0.86), 0.009),
                                ((-sx * 0.15, -0.09, 0.7), 0.009)], OUTER2)
        ellipsoid("Buckle", (0, -0.14, 0.86), (0.022, 0.01, 0.022), COLL, SILVER, subd=0).parent = ROOT
    if OW in ("flannel", "trench", "blazer", "track"):
        tube("OuterCollar", [((0.045, -0.1, 1.0), 0.012), ((0.07, -0.04, 1.05), 0.015), ((0.05, 0.03, 1.075), 0.015),
                             ((0, 0.055, 1.08), 0.015), ((-0.05, 0.03, 1.075), 0.015), ((-0.07, -0.04, 1.05), 0.015),
                             ((-0.045, -0.1, 1.0), 0.012)], OUTER)
if C["print"]:  # graphic tee / Y2K print on the chest
    plate("Print", [(-0.07, -0.098, 0.97), (0.07, -0.098, 0.97), (0.07, -0.105, 0.82), (-0.07, -0.105, 0.82)],
          material("Print", C["print"], rough=0.6), thick=0.002)
    if C["print_shape"] == "butterfly":
        for sx in (1, -1):
            plate(f"Wing{sx}", [(0, -0.108, 0.9), (sx * 0.06, -0.108, 0.96), (sx * 0.065, -0.11, 0.86)],
                  material(f"WingInk{sx}", C["accent"], rough=0.5), thick=0.002)

# --- headwear (head space, rides the nods) ------------------------------------------------
HAT = C["hat"]  # None | beanie | cap | beret
if HAT:
    hv = 1.0 + 0.6 * C["hair_volume"]
    knit = material("Hat", C["hat_color"], rough=0.85, sheen=0.4)
    fabric(knit, knit=HAT == "beanie")
    if HAT == "beanie":
        link(ellipsoid("Beanie", (0, 0.16, 0.66), (HW * hv * 1.08, 0.94 + 0.2 * C["hair_volume"], 0.75 * hv), COLL, knit,
                       segs=40))
        link(ellipsoid("BeanieCuff", (0, 0.12, 0.47 + 0.1 * C["hair_volume"]),
                       (HW * hv * 1.1, 0.98 + 0.2 * C["hair_volume"], 0.14), COLL, knit, segs=40))
    elif HAT == "cap":
        link(ellipsoid("CapDome", (0, 0.05, 0.6), (HW * hv * 1.05, 1.0 * hv, 0.62 * hv), COLL, knit, segs=40))
        brim = link(ellipsoid("CapBrim", (0, -0.85 * hv, 0.5), (0.5, 0.45, 0.03), COLL, knit, segs=32))
        brim.rotation_euler = (-0.15, 0, 0)
    elif HAT == "beret":
        b_ = link(ellipsoid("Beret", (0.12, 0.12, 0.82 + 0.2 * C["hair_volume"]), (HW * hv * 1.25, 1.12 * hv, 0.26),
                            COLL, knit, segs=40))
        b_.rotation_euler = (0.15, 0.3, 0)

if C["chain"]:
    chunky = C["chain"] == "chunky"
    n_beads = 40 if chunky else 64
    bm = bmesh.new()
    for k in range(n_beads):
        t = 2 * math.pi * k / n_beads
        y0, a = 0.075 * math.sin(t), 0.55
        pos = (0.062 * math.cos(t), -0.005 + y0 * math.cos(a), SHOULDER_Z - 0.005 + y0 * math.sin(a))
        bmesh.ops.create_icosphere(bm, subdivisions=1 + chunky, radius=0.006 if chunky else 0.0032,
                                   matrix=Matrix.Translation(pos))
    cme = bpy.data.meshes.new("Chain")
    bm.to_mesh(cme)
    bm.free()
    cme.materials.append(METAL)
    ch = bpy.data.objects.new("Chain", cme)
    COLL.objects.link(ch)
    ch.parent = ROOT

if C["watch"]:
    bpy.ops.mesh.primitive_torus_add(major_radius=0.043, minor_radius=0.008, location=(0.172, -0.315, 0.797),
                                     rotation=(math.pi / 2, 0, 0))
    w_ = link(bpy.context.active_object, ROOT)
    w_.name = "Watch"
    w_.data.materials.append(SILVER)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.018, depth=0.008, location=(0.172, -0.315, 0.84))
    w_ = link(bpy.context.active_object, ROOT)
    w_.name = "WatchFace"
    w_.data.materials.append(FRAME)

# --- elbows carry forearm + hand (+ watch on the left wrist) -------------------------------------
bpy.context.view_layer.update()
for sx, side in ((1, "L"), (-1, "R")):
    elbow = bpy.data.objects[f"Elbow{side}"]
    names = (f"Forearm{sx}", f"Palm{sx}", f"Finger{sx}", f"Thumb{sx}") + (("Watch",) if sx == 1 else ())
    for o in [o for o in ROOT.children if o.name.startswith(names)]:
        mw = o.matrix_world.copy()
        o.parent = elbow
        o.matrix_parent_inverse = elbow.matrix_world.inverted()
        o.matrix_world = mw

# --- body pivot at the hips: breathing and leaning move torso, arms and head together ---------------
BODY = empty("Body", (0, 0.03, 0.62), COLL, parent=ROOT)
bpy.context.view_layer.update()
for o in list(ROOT.children):
    if o is not BODY:
        mw = o.matrix_world.copy()
        o.parent = BODY
        o.matrix_parent_inverse = BODY.matrix_world.inverted()
        o.matrix_world = mw

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(f"saved {OUT}")
