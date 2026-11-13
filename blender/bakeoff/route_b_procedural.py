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
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bl_common import ellipsoid, empty, material  # noqa: E402
from cast import CAST  # noqa: E402
from reelforge.arkit import ARKIT_NAMES  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(args[0])
C = CAST["kai"]
C = {**C, **C["outfits"][0], "head_scale": 0.13, "neck_length": 0.0,
     "eye_size": 0.152, "eye_wide": 1.26, "eye_tall": 0.8, "lid_rest": -0.30, "brow_ridge": 0.16, "socket": 0.2,
     "planes": 0.012, "hollow": 0.03, "jaw_corner": 0.15, "chin": 0.30, "jaw_width": 0.86, "head_width": 0.72, "mouth_width": 0.38, "skin": (0.44, 0.205, 0.10), "lip": (0.34, 0.09, 0.07), "fold": 0.025,
     "nose_tip": 0.11, "cheekbone": 0.09, "lip_full": 1.3, "brow_thick": 1.15}
RNG = np.random.default_rng(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
COLL = bpy.data.collections.new("CHAR_base")
bpy.context.scene.collection.children.link(COLL)

S = C["head_scale"]
SHOULDER_Z = 1.43  # neck base (standing A-pose, ~1.80 m tall)
HEAD_C = 1.625  # head-space origin height (chin = HEAD_C - 1.05*S)
PIVOT_Z = 1.455
JAW_MAX = 0.26  # rad at jawOpen = 1
FL, HW = C["face_length"], C["head_width"]
MZ = -0.56  # mouth line (head space)
EZ = -0.02  # eye line
ZC, ZK = -0.40, 0.82  # the lower face is compressed (shorter chin) below ZC
PZ = (ZC + (MZ - ZC) / ZK) / FL  # mouth line on the unit sphere (pre-compression)
ER, ES = C["eye_size"], C["eye_spacing"]
ES_ = ES
EYE_HOLE = (1.10 * ER * C["eye_wide"], 1.10 * ER * C["eye_tall"])  # skin opening for the eyeball (head units)
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
BROW = material("Brow", (0.004, 0.003, 0.003), rough=0.9)
BROW.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.05
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
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=119, use_grid_fill=True)
for v in bm.verts:
    v.co.normalize()

MW = C["mouth_width"]
slit = [f for f in bm.faces
        if all(v.co.y < -0.5 for v in f.verts)
        and abs(f.calc_center_median().x) < MW
        and min(v.co.z for v in f.verts) < PZ < max(v.co.z for v in f.verts)]
slit_verts = {v for f in slit for v in f.verts}
bmesh.ops.delete(bm, geom=slit, context="FACES")
for sx_ in (1, -1):  # eye openings: the lids and the eyeball sit in real holes in the skin
    hole = [f for f in bm.faces if f.calc_center_median().y < -0.3
            and ((f.calc_center_median().x * HW - sx_ * ES) / EYE_HOLE[0]) ** 2
            + ((f.calc_center_median().z * FL - EZ) / EYE_HOLE[1]) ** 2 < 1.0]
    bmesh.ops.delete(bm, geom=hole, context="FACES")
for v in slit_verts:  # snap the lip edges onto the mouth line: closed mouth = dark seam
    v.co.z = PZ + (0.004 if v.co.z > PZ else -0.004)
bm.verts.ensure_lookup_table()
bm.verts.index_update()
P = np.array([v.co[:] for v in bm.verts])
EYE_RIM = {sx_: [v.index for v in bm.verts if any(e.is_boundary for e in v.link_edges)
                 and abs(v.co.z * FL - EZ) < 3 * EYE_HOLE[1] and abs(v.co.x * HW - sx_ * ES) < 1.5 * EYE_HOLE[0]]
           for sx_ in (1, -1)}


def sculpt(P):
    X = P * np.array([HW, 0.92, FL])
    x, z = X[:, 0], X[:, 2]
    X[:, 2] = np.where(X[:, 2] < ZC, ZC + (X[:, 2] - ZC) * ZK, X[:, 2])
    z = X[:, 2]
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
    X[:, 1] -= (0.04 + 0.065 * u) * ridge * F
    X[:, 1] -= C["nose_tip"] * g2(X, 0, ZT, 0.07 * NW, 0.065) * F
    wing = gm(X, 0.085 * NW, ZT - 0.03, 0.045 * NW, 0.04) * F
    X[:, 1] -= 0.075 * wing
    X[:, 0] += sx * 0.03 * wing
    X[:, 1] += C["fold"] * seg(X, (0.11, ZT - 0.04), (MW * HW * 0.8 + 0.06, MZ - 0.03), 0.018) * F  # nasolabial fold
    X[:, 1] -= 0.06 * g2(X, 0, -0.5, 0.28, 0.16) * F  # muzzle
    mwx = MW * HW * 0.8
    X[:, 1] -= 0.05 * C["lip_full"] * g2(X, 0, MZ + 0.035, mwx * 0.85, 0.03) * F
    X[:, 1] -= 0.06 * C["lip_full"] * g2(X, 0, MZ - 0.045, mwx * 0.8, 0.035) * F
    X[:, 1] += 0.035 * g2(X, 0, MZ - 0.14, 0.15, 0.035) * F  # groove under the lower lip
    # lips: vermilion border ridges (cupid's bow on top), upper-lip overhang, lower-lip pad, philtrum columns
    for a_, b_, wd, dp in (((0.0, MZ + 0.076), (0.05, MZ + 0.09), 0.007, 0.016), ((0.05, MZ + 0.09), (mwx * 0.92, MZ + 0.05), 0.008, 0.013),
                           ((0.0, MZ - 0.105), (mwx * 0.7, MZ - 0.09), 0.009, 0.01)):
        X[:, 1] -= dp * seg(X, a_, b_, wd) * F
    X[:, 1] -= 0.02 * g2(X, 0, MZ + 0.045, mwx * 0.6, 0.03) * F  # upper lip overhangs the lower
    X[:, 1] -= 0.012 * gm(X, 0.04, (ZT + MZ) / 2 + 0.03, 0.014, 0.06) * F  # philtrum columns
    X[:, 1] += 0.02 * gm(X, mwx, MZ, 0.02, 0.02) * F  # tucked mouth corners
    X[:, 1] += 0.006 * gm(X, ES_ + 0.0, EZ - 0.2, 0.2, 0.025) * F  # lower-lid / eye-bag groove
    X[:, 1] -= 0.006 * gm(X, ES_ + 0.0, EZ - 0.28, 0.17, 0.045) * F  # eye bag
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
head["face_part"] = "head"
sub = head.modifiers.new("Subd", "SUBSURF")
sub.levels, sub.render_levels = 0, 1
F = front(X)


_SURF = None


def surf_y(x, z, rebuild=False):
    """Y of the sculpted face surface at (x, z): ray cast onto the head mesh (smooth, not nearest-vertex)."""
    global _SURF
    if _SURF is None or rebuild:
        _SURF = BVHTree.FromPolygons([tuple(v) for v in X], [tuple(p.vertices) for p in me.polygons])
    hit = _SURF.ray_cast((x, -3.0, z), (0, 1, 0))
    return float(hit[0].y) if hit[0] is not None else 0.0


# --- skin attributes (lip tint, stubble, warmth) ---------------------------------
MWX = MW * HW * 0.8
lipzone = np.exp(-((X[:, 0] / (MWX * 1.05)) ** 4)) * np.exp(-((X[:, 2] - MZ) / 0.07) ** 2) * F
_ax, _z = np.abs(X[:, 0]), X[:, 2]
_zup = MZ + 0.07 + 0.016 * np.exp(-((_ax - 0.05) / 0.03) ** 2) - 0.03 * sm(0.05, MWX, _ax)
_xl = MWX * np.where(_z < MZ, 1 - 0.5 * np.clip((MZ - _z) / 0.1, 0, 1) ** 2, 1 - 0.25 * np.clip((_z - MZ) / 0.08, 0, 1) ** 2)
_zlo = MZ - 0.082 + 0.03 * np.clip(_ax / MWX, 0, 1) ** 2
lipmask = sm(_zup + 0.007, _zup - 0.007, _z) * sm(_zlo - 0.007, _zlo + 0.007, _z) * (1 - sm(_xl * 0.92, _xl * 1.02, _ax)) * F
vermil = np.clip(np.exp(-((_z - (_zup - 0.004)) / 0.012) ** 2) * (1 - sm(MWX * 0.9, MWX, _ax)) * F, 0, 1)
stub = C["stubble"] * sm(ZT - 0.02, ZT - 0.2, X[:, 2]) * sm(0.55, 0.15, X[:, 1]) * (1 - lipmask)
warm = np.clip((gm(X, 0.42, EZ - 0.25, 0.14, 0.12) * 0.6 + g2(X, 0, ZT, 0.08, 0.08) * 0.5) * (1 + 1.5 * C["blush"]),
               0, 1) * F
ES_ = C["eye_spacing"]
freck = np.clip(C["freckles"] * (gm(X, 0.28, EZ - 0.22, 0.15, 0.08) + g2(X, 0, ZT + 0.12, 0.07, 0.08)), 0, 1) * F
shade = np.clip(1.6 * gm(X, 0.045 * C["nose_width"], ZT - 0.065, 0.016 * C["nose_width"], 0.01)  # nostrils
                + 0.5 * seg(X, (ES_ - 0.11, EZ + 0.13), (ES_ + 0.12, EZ + 0.1), 0.01)  # lid crease
                + 0.6 * gm(X, MWX, MZ, 0.018, 0.014), 0, 1) * F  # mouth corners
for name, vals in (("Lip", np.clip(lipmask * 0.9 + 0.35 * vermil, 0, 1)), ("Stubble", stub), ("Warm", warm), ("Freckle", freck), ("Shade", shade)):
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


def brow_fields(Q, sx):
    """Skin/brow displacement for the brow shapes at arbitrary points Q (so brow cards ride the skin exactly)."""
    Fq, ax_ = front(Q), np.abs(Q[:, 0])
    inner = sm(0.5, 0.12, ax_)
    down = gside(Q, sx, 0.34, EZ + 0.19, 0.24, 0.1) * Fq
    outer = gside(Q, sx, 0.50, EZ + 0.22, 0.12, 0.1) * Fq
    inn = gside(Q, sx, 0.22, EZ + 0.21, 0.13, 0.1) * Fq
    return {"down": vec(down, (0, -0.012, -0.05)) + vec(down * inner, (0, -0.01, -0.04))
            - vec(down * (1 - inner) * 0.4, (0, 0, -0.03)),
            "outer": vec(outer, (0, 0.0, 0.065)) + vec(outer, (sx * 0.0, 0.0, 0.0)),
            "inner": vec(inn, (0, -0.004, 0.085))}


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
    cheek = gside(X, sx, 0.38, MZ + 0.2, 0.12, 0.1) * F * sm(EZ - 0.2, EZ - 0.34, X[:, 2])
    SHAPES.update({
        f"mouthSmile{side}": vec(K, (sx * 0.07, 0.035, 0.11)) + vec(cheek, (sx * 0.02, -0.05, 0.085)),
        f"mouthFrown{side}": vec(K, (sx * 0.01, 0.012, -0.1)),
        f"mouthStretch{side}": vec(K, (sx * 0.04, 0.01, -0.006)),
        f"mouthDimple{side}": vec(K, (sx * 0.01, 0.025, 0)),
        f"mouthPress{side}": vec(UP * Hh, (0, 0, -0.008)) + vec(LO * Hh, (0, 0, 0.008)),
        f"mouthLowerDown{side}": vec(LO * Hh, (0, 0, -0.03)),
        f"mouthUpperUp{side}": vec(UP * Hh, (0, 0, 0.03)),
        f"cheekSquint{side}": vec(gside(X, sx, 0.32, EZ - 0.15, 0.13, 0.08) * F, (0, -0.01, 0.035)),
        f"noseSneer{side}": vec(gside(X, sx, 0.1, ZT, 0.06, 0.06) * F, (0, -0.005, 0.03)),
        f"browDown{side}": brow_fields(X, sx)["down"],
        f"browOuterUp{side}": brow_fields(X, sx)["outer"],
    })
SHAPES["browInnerUp"] = brow_fields(X, 1)["inner"] + brow_fields(X, -1)["inner"]

def eye_surface_y(sx):
    pts = [surf_y(sx * ES + dx, EZ + dz) for dx, dz in ((1.5 * EYE_HOLE[0], 0), (-1.5 * EYE_HOLE[0], 0),
                                                         (0, 1.6 * EYE_HOLE[1]), (0, -1.6 * EYE_HOLE[1]))]
    return float(np.mean(pts))


EYE_RECESS = 0.75  # eyeball centre sits this many radii behind the skin plane
EYE_C = {sx_: (sx_ * ES, eye_surface_y(sx_) + ER * EYE_RECESS, EZ) for sx_ in (1, -1)}
SHELL = 1.28  # outer radius (in eyeball radii) of the lid shells: the skin opening is snapped onto it
for sx_, idx in EYE_RIM.items():  # skin opening rim -> exactly on the lid shell, so skin and lids meet cleanly
    c_ = np.array(EYE_C[sx_])
    d_ = X[idx] - c_
    qn = np.linalg.norm(d_ / np.array([C["eye_wide"], 1.0, C["eye_tall"]]) / ER, axis=1)
    X[idx] = c_ + d_ * (SHELL / qn)[:, None]
# resting mouth: a touch of smile baked into the base so neutral doesn't read as sulking
X = X + C["smile_rest"] * (SHAPES["mouthSmileLeft"] + SHAPES["mouthSmileRight"])
_SURF = None
me.vertices.foreach_set("co", X.astype(np.float32).ravel())
head.shape_key_add(name="Basis")
for name, D in SHAPES.items():
    kb = head.shape_key_add(name=name, from_mix=False)
    kb.data.foreach_set("co", (X + D).astype(np.float32).ravel())
    if name == "jawOpen":  # sticking the tongue out parts the jaw a little (the shape key and the jaw bone agree)
        drive(kb, "value", "min(1,v+0.3*t)", {"v": name, "t": "tongueOut"})
    else:
        drive(kb, "value", "v", {"v": name})

# --- mouth interior: cavity, teeth, tongue (lower parts ride the jaw) -------------
YS = surf_y(0, MZ + 0.03)
JAWP = empty("JawPivot", tuple(PIVOT), COLL, parent=GEO)
drive(JAWP, "rotation_euler", f"{JAW_MAX}*min(1,j+0.3*t)", {"j": "jawOpen", "t": "tongueOut"}, index=0)
drive(JAWP, "delta_location", "0.05*(l-r)", {"l": "jawLeft", "r": "jawRight"}, index=0)  # the lower teeth follow the skin
drive(JAWP, "delta_location", "-0.06*f", {"f": "jawForward"}, index=1)
link(ellipsoid("MouthCavity", (0, YS + 0.36, MZ - 0.03), (MWX * 1.2, 0.2, 0.11), COLL, MOUTH))


def teeth(name, z, parent, offset, back=0.0):
    cd = bpy.data.curves.new(name, "CURVE")
    cd.dimensions = "3D"
    cd.extrude, cd.bevel_depth, cd.bevel_resolution = 0.034, 0.011, 2
    sp = cd.splines.new("NURBS")
    y = YS + back
    pts = [(-MWX * 0.66, y + 0.2, z), (-MWX * 0.45, y + 0.13, z), (0, y + 0.1, z),
           (MWX * 0.45, y + 0.13, z), (MWX * 0.66, y + 0.2, z)]
    sp.points.add(len(pts) - 1)
    for p, co in zip(sp.points, pts):
        p.co = (co[0] - offset[0], co[1] - offset[1], co[2] - offset[2], 1)
    sp.order_u, sp.use_endpoint_u = 3, True
    o = bpy.data.objects.new(name, cd)
    COLL.objects.link(o)
    o.data.materials.append(TEETH)
    o.parent = parent
    o["face_part"] = "teeth"
    return o


teeth("TeethUpper", MZ + 0.03, GEO, (0, 0, 0))
teeth("TeethLower", MZ - 0.045, JAWP, tuple(PIVOT), back=0.1)
tongue = ellipsoid("Tongue", (0, YS + 0.3 - PIVOT[1], MZ - 0.07 - PIVOT[2]), (MWX * 0.7, 0.11, 0.035),
                   COLL, TONGUE)
tongue.parent = JAWP
tongue["face_part"] = "tongue"
drive(tongue, "delta_location", "-0.14*t", {"t": "tongueOut"}, index=1)
drive(tongue, "delta_location", "0.06*t", {"t": "tongueOut"}, index=2)



# --- eyes: sclera + recessed iris (procedural fibres) + glossy cornea shell, lids with thickness, lash cards ---------
def N_(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


IRIS_R = 0.56  # iris radius as a share of the eyeball radius (stylised: big, readable iris)
IRIS_A = math.asin(IRIS_R)


def eye_material2():
    m = bpy.data.materials.new("Eye")
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.3
    b.inputs["Specular IOR Level"].default_value = 0.3
    tc = N_(nt, "ShaderNodeTexCoord")
    sep = N_(nt, "ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])
    flat = N_(nt, "ShaderNodeCombineXYZ")
    L.new(sep.outputs["X"], flat.inputs["X"])
    L.new(sep.outputs["Z"], flat.inputs["Z"])
    ln = N_(nt, "ShaderNodeVectorMath", operation="LENGTH")
    L.new(flat.outputs[0], ln.inputs[0])
    nrm = N_(nt, "ShaderNodeVectorMath", operation="NORMALIZE")
    L.new(flat.outputs[0], nrm.inputs[0])
    sn = N_(nt, "ShaderNodeSeparateXYZ")
    L.new(nrm.outputs[0], sn.inputs[0])
    back = N_(nt, "ShaderNodeMath", operation="GREATER_THAN")
    L.new(sep.outputs["Y"], back.inputs[0])
    back.inputs[1].default_value = 0.0
    bk10 = N_(nt, "ShaderNodeMath", operation="MULTIPLY")
    L.new(back.outputs[0], bk10.inputs[0])
    bk10.inputs[1].default_value = 10.0
    rr = N_(nt, "ShaderNodeMath", operation="DIVIDE")
    L.new(ln.outputs["Value"], rr.inputs[0])
    rr.inputs[1].default_value = IRIS_R
    r = N_(nt, "ShaderNodeMath", operation="ADD")
    L.new(rr.outputs[0], r.inputs[0])
    L.new(bk10.outputs[0], r.inputs[1])
    # radial fibres: noise on (cos a, sin a) * K plus a slow radial coordinate
    ka = []
    for ch in ("X", "Z"):
        mk = N_(nt, "ShaderNodeMath", operation="MULTIPLY")
        L.new(sn.outputs[ch], mk.inputs[0])
        mk.inputs[1].default_value = 9.0
        ka.append(mk)
    kr = N_(nt, "ShaderNodeMath", operation="MULTIPLY")
    L.new(r.outputs[0], kr.inputs[0])
    kr.inputs[1].default_value = 1.6
    vv = N_(nt, "ShaderNodeCombineXYZ")
    L.new(ka[0].outputs[0], vv.inputs["X"])
    L.new(ka[1].outputs[0], vv.inputs["Y"])
    L.new(kr.outputs[0], vv.inputs["Z"])
    nz = N_(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 1.0, 6.0
    nz.inputs["Roughness"].default_value = 0.65
    L.new(vv.outputs[0], nz.inputs["Vector"])
    fib = N_(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    L.new(nz.outputs["Fac"], fib.inputs[0])
    fib.inputs[1].default_value = 2.4
    fib.inputs[2].default_value = -0.5
    ramp = N_(nt, "ShaderNodeValToRGB")
    cr = ramp.color_ramp
    ir = C["iris"]
    amber = tuple(min(1.0, c * 3.2 + a) for c, a in zip(ir, (0.04, 0.012, 0.0)))
    stops = [(0.0, (0.002, 0.002, 0.002)), (0.30, (0.002, 0.002, 0.002)), (0.34, tuple(c * 0.7 for c in ir)),
             (0.46, tuple(c * 1.6 + 0.01 for c in ir)), (0.62, amber), (0.82, tuple(c * 1.3 for c in ir)),
             (0.93, tuple(c * 0.35 for c in ir)), (0.975, (0.004, 0.003, 0.003)), (0.995, (0.55, 0.5, 0.46)),
             (1.0, (0.78, 0.74, 0.70))]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, c in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (*c, 1)
    L.new(r.outputs[0], ramp.inputs["Fac"])
    inside = N_(nt, "ShaderNodeMath", operation="LESS_THAN")  # fibres only inside the iris ring
    L.new(r.outputs[0], inside.inputs[0])
    inside.inputs[1].default_value = 0.96
    fm = N_(nt, "ShaderNodeMath", operation="MULTIPLY")
    L.new(inside.outputs[0], fm.inputs[0])
    fm.inputs[1].default_value = 0.85
    mx = N_(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    L.new(fm.outputs[0], mx.inputs[0])
    L.new(ramp.outputs["Color"], mx.inputs[6])
    L.new(fib.outputs[0], mx.inputs[7])
    ax = N_(nt, "ShaderNodeMath", operation="ABSOLUTE")  # sclera: pinker toward the corners
    L.new(sep.outputs["X"], ax.inputs[0])
    x4 = N_(nt, "ShaderNodeMath", operation="POWER")
    L.new(ax.outputs[0], x4.inputs[0])
    x4.inputs[1].default_value = 3.0
    out = N_(nt, "ShaderNodeMath", operation="GREATER_THAN")
    L.new(r.outputs[0], out.inputs[0])
    out.inputs[1].default_value = 0.999
    tf = N_(nt, "ShaderNodeMath", operation="MULTIPLY")
    L.new(out.outputs[0], tf.inputs[0])
    L.new(x4.outputs[0], tf.inputs[1])
    tint = N_(nt, "ShaderNodeMix", data_type="RGBA")
    L.new(tf.outputs[0], tint.inputs[0])
    L.new(mx.outputs[2], tint.inputs[6])
    tint.inputs[7].default_value = (0.62, 0.36, 0.32, 1.0)
    L.new(tint.outputs[2], b.inputs["Base Color"])
    return m


def cornea_material():
    m = bpy.data.materials.new("Cornea")
    m.use_nodes = True
    nt = m.node_tree
    m.surface_render_method = "BLENDED"
    nt.nodes.clear()
    L = nt.links
    out = N_(nt, "ShaderNodeOutputMaterial")
    tr = N_(nt, "ShaderNodeBsdfTransparent")
    gl = N_(nt, "ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.02
    fr = N_(nt, "ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.376
    ma = N_(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    L.new(fr.outputs[0], ma.inputs[0])
    ma.inputs[1].default_value = 0.9
    ma.inputs[2].default_value = 0.1
    mx = N_(nt, "ShaderNodeMixShader")
    L.new(ma.outputs[0], mx.inputs[0])
    L.new(tr.outputs[0], mx.inputs[1])
    L.new(gl.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs["Surface"])
    return m


EYE2 = eye_material2()
CORNEA = cornea_material()
RIM_UP = material("LidRimUpper", (0.006, 0.004, 0.004), rough=0.35)
RIM_LO = material("LidRimLower", (0.30, 0.07, 0.06), rough=0.2)


def _ang(v):
    return math.acos(max(-1.0, min(1.0, -v.co.y)))


def eyeball(name):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=72, v_segments=48, radius=1.0)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"), verts=bm.verts)
    for v in bm.verts:  # recessed iris dish: parallax under the cornea
        a = _ang(v)
        if a < IRIS_A * 1.02:
            t = a / (IRIS_A * 1.02)
            v.co *= 1.0 - 0.085 * (1 - t * t) ** 1.2
    me_ = bpy.data.meshes.new(name)
    bm.to_mesh(me_)
    bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    me_.materials.append(EYE2)
    return me_


def cornea_mesh(name):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=1.0)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"), verts=bm.verts)
    AC = IRIS_A * 1.25
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if _ang(v) > AC], context="VERTS")
    for v in bm.verts:
        a = _ang(v)
        v.co *= 1.006 + 0.036 * (1 - (a / AC) ** 2)
    me_ = bpy.data.meshes.new(name)
    bm.to_mesh(me_)
    bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    me_.materials.append(CORNEA)
    return me_


def cap(name, keep, mats, thick=0.13):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v.co)], context="VERTS")
    me_ = bpy.data.meshes.new(name)
    bm.to_mesh(me_)
    bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    for m in mats:
        me_.materials.append(m)
    o = bpy.data.objects.new(name, me_)
    COLL.objects.link(o)
    sol = o.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness, sol.offset, sol.material_offset_rim = thick, 1.0, 1
    o.modifiers.new("Subd", "SUBSURF").render_levels = 1
    return o


def lash_cards(name, upper, side_sx, n, mat, parent):
    """Tapered lash cards (flat strips with hair-direction curl) rooted on the lid margin, in lid-local units."""
    rng = np.random.default_rng(11 if upper else 13)
    bm = bmesh.new()
    for k in range(n):
        t = math.pi * (0.10 + 0.80 * (k + rng.uniform(-0.3, 0.3)) / (n - 1))
        cx, cy = math.cos(t), -math.sin(t)
        outer = max(0.0, cx * side_sx)  # 1 at the outer corner
        ln = (0.14 + 0.22 * outer) * (1.0 if upper else 0.5) * rng.uniform(0.8, 1.15)
        rad = 1.07 if upper else 1.04
        root = np.array([cx * rad, cy * rad, 0.0])
        out_d = np.array([cx * 0.55 + side_sx * 0.35 * outer, cy * 0.85, 0.0])
        out_d /= np.linalg.norm(out_d)
        up = np.array([0.0, 0.0, 1.0 if upper else -1.0])
        tang = np.array([-cy, cx, 0.0])
        w0 = (0.050 if upper else 0.02) * rng.uniform(0.8, 1.1)
        prev = None
        for s in np.linspace(0, 1, 5):
            p = root + ln * (out_d * (0.55 * s) + up * (0.95 * s ** 1.7))
            w = w0 * (1 - s) ** 0.9 + 0.003
            a, b_ = bm.verts.new(p + tang * w), bm.verts.new(p - tang * w)
            if prev:
                bm.faces.new((prev[0], prev[1], b_, a))
            prev = (a, b_)
    me_ = bpy.data.meshes.new(name)
    bm.to_mesh(me_)
    bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    me_.materials.append(mat)
    o = bpy.data.objects.new(name, me_)
    COLL.objects.link(o)
    o.parent = parent
    o["face_part"] = "lash"
    return o


for side, sx in (("Left", 1), ("Right", -1)):
    ec = EYE_C[sx]
    rig = link(empty(f"EyeRig{side}", ec, COLL))
    rig.scale = (C["eye_wide"], 1.0, C["eye_tall"])
    eye = link(bpy.data.objects.new(f"Eye{side}", eyeball(f"Eye{side}")), rig)
    eye.scale = (ER,) * 3
    eye["face_part"] = "eye"
    cor = link(bpy.data.objects.new(f"Cornea{side}", cornea_mesh(f"Cornea{side}")), eye)
    cor["face_part"] = "eye"
    cor.visible_shadow = False
    drive(eye, "rotation_euler", "0.35*(d-u)", {"d": f"eyeLookDown{side}", "u": f"eyeLookUp{side}"}, index=0)
    drive(eye, "rotation_euler", f"{0.4 * sx}*(o-i)", {"o": f"eyeLookOut{side}", "i": f"eyeLookIn{side}"}, index=2)
    rest = C["lid_rest"]
    up = link(cap(f"LidUpper{side}", lambda c: c.z > 0 and c.y < 0.55, (SKIN, RIM_UP), 0.2), rig)
    up.location, up.scale = (0, 0, 0), (ER * 1.09,) * 3
    up["face_part"] = "lid"
    drive(up, "rotation_euler", f"{rest}+b*({0.74 - rest})-0.75*w+0.22*s+0.30*d-0.24*u",
          {"b": f"eyeBlink{side}", "w": f"eyeWide{side}", "s": f"eyeSquint{side}", "d": f"eyeLookDown{side}",
           "u": f"eyeLookUp{side}"}, index=0)
    lo = link(cap(f"LidLower{side}", lambda c: c.z < 0 and c.y < 0.55, (SKIN, RIM_LO), 0.16), rig)
    lo.location, lo.scale = (0, 0, 0), (ER * 1.085,) * 3
    lo["face_part"] = "lid"
    drive(lo, "rotation_euler", "0.66-0.3*s-0.15*c-0.1*b+0.06*d-0.09*u",
          {"s": f"eyeSquint{side}", "c": f"cheekSquint{side}", "b": f"eyeBlink{side}", "d": f"eyeLookDown{side}",
           "u": f"eyeLookUp{side}"}, index=0)
    lash_cards(f"LashUpper{side}", True, sx, 30, LASH, up)
    lash_cards(f"LashLower{side}", False, sx, 10, LASH, lo)

EYE_Y = surf_y(0, EZ + 0.02)
link(empty("FaceAnchor", (0, EYE_Y, 0.0), COLL))
link(empty("EyeFocus", (0, EYE_C[1][1] - ER, EZ), COLL))
bpy.data.objects["FaceAnchor"]["head_height"] = 2.2 * S


# --- brows: hair-direction cards on the brow ridge, riding the skin through the same displacement fields ----------
def brow_card(side, sx):
    rng = np.random.default_rng(21 + sx)
    bm = bmesh.new()
    ba = C["brow_angle"]
    NX, NJ = 30, 5
    x0, x1 = 0.075, 0.60

    def cz(u):  # centreline height: low inner end, soft arch, tail falls a touch
        return EZ + 0.155 + 0.07 * math.sin(math.pi * min(1, u ** 0.8) * 0.88) - 0.02 * u + 0.03 * ba * u

    def hh(u):
        return (0.085 - 0.04 * u ** 1.3) * C["brow_thick"]

    grid = []
    for i in range(NX):
        u = i / (NX - 1)
        x = sx * (x0 + (x1 - x0) * u)
        row = []
        for j in range(NJ):
            v = j / (NJ - 1)
            z = cz(u) + (v - 0.5) * hh(u) * (1.0 if v > 0.5 else 0.9)
            edge = 1 - (2 * v - 1) ** 4
            d = 0.004 + 0.016 * edge * (1 - 0.5 * u)
            row.append(bm.verts.new((x, surf_y(x, z) - d, z)))
        grid.append(row)
    for i in range(NX - 1):
        for j in range(NJ - 1):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    # hair strokes: inner hairs rise, the middle follows the arch, the tail sweeps out and down
    for k in range(70):
        u = rng.uniform(0.0, 1.0) ** 0.9
        v = rng.uniform(0.15, 0.95)
        x = sx * (x0 + (x1 - x0) * u)
        z = cz(u) + (v - 0.5) * hh(u)
        ang = math.radians(78 - 105 * u ** 0.85) + rng.normal(0, 0.12)
        dx, dz = sx * math.cos(ang), math.sin(ang)
        ln = rng.uniform(0.06, 0.1) * (1.1 - 0.4 * u)
        w0 = 0.011 * rng.uniform(0.8, 1.2)
        prev = None
        for s in np.linspace(0, 1, 4):
            px = x + dx * ln * s
            pz = z + dz * ln * s - 0.012 * s * s
            py = surf_y(px, pz) - 0.017 - 0.004 * s
            w = w0 * (1 - s) ** 0.8 + 0.0015
            a = bm.verts.new((px - dz * sx * w, py, pz + dx * sx * w))
            b_ = bm.verts.new((px + dz * sx * w, py, pz - dx * sx * w))
            if prev:
                bm.faces.new((prev[0], prev[1], b_, a))
            prev = (a, b_)
    me_ = bpy.data.meshes.new(f"Brow{side}")
    bm.to_mesh(me_)
    bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    me_.materials.append(BROW)
    o = link(bpy.data.objects.new(f"Brow{side}", me_))
    o["face_part"] = "brow"
    Q = np.array([v.co[:] for v in me_.vertices])
    fl = brow_fields(Q, sx)
    o.shape_key_add(name="Basis")
    for key, name in (("down", f"browDown{side}"), ("outer", f"browOuterUp{side}"), ("inner", "browInnerUp")):
        kb = o.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", (Q + fl[key]).astype(np.float32).ravel())
        drive(kb, "value", "v", {"v": name})
    return o


for side, sx in (("Left", 1), ("Right", -1)):
    brow_card(side, sx)


# --- ears: sculpted from a polar grid (helix rim, antihelix ridge, concha bowl, lobe), thin solid -----------------
def ear(side, sx):
    a_, b_ = 0.115, 0.255
    yc, zc = 0.16, EZ - 0.07
    R, M = 18, 44
    surf_y(0, 0)
    hit = _SURF.ray_cast((sx * 3.0, yc, zc), (-sx, 0, 0))
    xs = abs(hit[0].x) if hit[0] is not None else HW * 0.95
    bm = bmesh.new()
    vs = [[bm.verts.new((0, 0, 0))]]
    for k in range(1, R + 1):
        vs.append([bm.verts.new((k / R, 2 * math.pi * m / M, 0)) for m in range(M)])
    for m in range(M):
        bm.faces.new((vs[0][0], vs[1][m], vs[1][(m + 1) % M]))
    for k in range(1, R):
        for m in range(M):
            bm.faces.new((vs[k][m], vs[k + 1][m], vs[k + 1][(m + 1) % M], vs[k][(m + 1) % M]))
    S1 = lambda e0, e1, x: float(sm(e0, e1, np.array(x)))  # noqa: E731
    for k, ring in enumerate(vs):
        for v in ring:
            rho, phi = (v.co.x, v.co.y) if k else (0.0, 0.0)
            un, vn = rho * math.cos(phi), rho * math.sin(phi)  # un: +back, vn: +up (both -1..1)
            u = un * a_ * (1.0 - 0.28 * S1(-0.2, -1.0, vn))
            w = vn * b_
            top = S1(-0.55, -0.1, vn)
            h = 0.020 + 0.022 * (1 - rho ** 2)
            h += 0.034 * math.exp(-((rho - 0.9) / 0.085) ** 2) * top  # helix rim
            h -= 0.012 * math.exp(-((rho - 0.72) / 0.07) ** 2) * top  # scapha groove
            ar = math.hypot((un + 0.32) / 0.5, (vn - 0.02) / 0.62)
            h += 0.026 * math.exp(-((ar - 1.0) / 0.2) ** 2) * S1(-0.3, 0.2, un + 0.2)  # antihelix
            h -= 0.034 * math.exp(-(((un + 0.05) / 0.3) ** 2 + ((vn + 0.22) / 0.26) ** 2))  # concha bowl
            lobe = S1(-0.45, -0.85, vn)
            h = h * (1 - lobe) + (0.026 + 0.012 * (1 - rho ** 2)) * lobe
            h *= 0.45 + 0.55 * S1(1.0, 0.82, rho)
            y = yc + u + 0.2 * vn * a_  # the top leans back
            x = sx * (xs - 0.035 + h) + sx * 0.55 * (u + a_)  # trailing edge flares out
            v.co = (x, y, zc + w)
    bm.normal_update()
    if sum(f.normal.x for f in bm.faces) * sx < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me_ = bpy.data.meshes.new(f"Ear{side}")
    bm.to_mesh(me_)
    bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    me_.materials.append(SKIN)
    ca = me_.color_attributes.new("Warm", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", np.full(len(me_.vertices) * 4, 0.7, np.float32))
    o = link(bpy.data.objects.new(f"Ear{side}", me_))
    o["face_part"] = "head"
    sol = o.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness, sol.offset = 0.022, -1.0
    o.modifiers.new("Subd", "SUBSURF").render_levels = 1
    if sx > 0 and C["earring"]:  # thin silver hoop through the left lobe
        bpy.ops.mesh.primitive_torus_add(major_radius=0.062, minor_radius=0.0085,
                                         location=(sx * (xs + 0.015), yc + 0.02, zc - b_ * 0.72),
                                         rotation=(0, math.pi / 2, 0), major_segments=40, minor_segments=10)
        rg = link(bpy.context.active_object)
        rg.name = "EarHoop"
        rg.data.materials.append(SILVER)
        for p in rg.data.polygons:
            p.use_smooth = True
    return o


for side, sx in (("Left", 1), ("Right", -1)):
    ear(side, sx)

# --- hair: scalp cap + clay locks in the character's style ---------------------------
HS = "curls"
HL_FRONT, HL_BACK = 0.47, -0.55
hairline = HL_FRONT + (HL_BACK - HL_FRONT) * (P[:, 1] + 1) / 2
hairline = hairline - 0.22 * np.exp(-((np.abs(P[:, 0]) - 0.9) / 0.16) ** 2) * sm(0.2, -0.3, P[:, 1])  # temple notch

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

# clay curls: chunky open ringlets (1-1.8 turns) that lie along the scalp and hang, thick enough to read as sculpted mass
cd = bpy.data.curves.new("Curls", "CURVE")
cd.dimensions = "3D"
cd.bevel_depth, cd.bevel_resolution, cd.resolution_u = 1.0, 2, 3  # light curve tessellation: ~0.6M tris, not 3M
near_line = P[:, 2] < hairline + 0.25
wts = np.where(P[:, 2] > hairline + 0.02, 1.0, 0.0) * np.where(near_line, 2.2, 1.0) * (0.35 + sm(-0.6, 0.6, P[:, 2]))
wts = wts * (0.6 + 0.4 * sm(0.0, 0.8, P[:, 2]))
N_CURLS = 650
for i in RNG.choice(len(P), size=N_CURLS, replace=False, p=wts / wts.sum()):
    n = NRM[i]
    top = P[i, 2] > 0.55
    down = np.array([0.0, 0.3, 0.7]) if (P[i, 1] < -0.2 and P[i, 2] > 0.3) else np.array([0.0, -0.45 if P[i, 1] < -0.2 else 0.25, -1.0])
    down -= (down @ n) * n
    a = (0.55 if top else 0.25) * n + down / (np.linalg.norm(down) + 1e-6) + RNG.normal(0, 0.35, 3)
    a /= np.linalg.norm(a)
    e1 = np.cross(a, [1.0, 0.0, 0.0] if abs(a[0]) < 0.9 else [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    base = X[i] + n * 0.07
    cs = C["curl_scale"] * (1.1 if top else 0.85)
    turns, r, h = RNG.uniform(1.0, 1.7), cs * RNG.uniform(0.058, 0.08), cs * RNG.uniform(0.1, 0.17)
    tube, ph = cs * RNG.uniform(0.038, 0.048), RNG.uniform(0, 2 * math.pi)
    k = int(turns * 12) + 3
    sp = cd.splines.new("NURBS")
    sp.points.add(k - 1)
    for j, p in enumerate(sp.points):
        u = j / (k - 1)
        th = ph + 2 * math.pi * turns * u
        co = base + a * h * u + r * min(1, 3 * u + 0.3) * (math.cos(th) * e1 + math.sin(th) * e2)
        p.co, p.radius = (*co, 1), tube * (1 - 0.7 * u ** 2.2)
    sp.order_u, sp.use_endpoint_u = 4, True
curls = link(bpy.data.objects.new("Curls", cd))
curls.data.materials.append(HAIR)
HAIR.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.42




# =====================================================================================================================
# BODY: standing A-pose, ~1.8 m. Every part is a mesh built by script from ring sweeps / lofts, skinned to a simple
# armature (each part rigid to one bone; the neck is blended chest/neck/head by height).
# =====================================================================================================================
SHIRT = TOP
TROUSER = material("Trousers", (0.022, 0.024, 0.03), rough=0.85, sheen=0.1)
SNEAK = material("Sneaker", (0.62, 0.62, 0.6), rough=0.55, coat=0.15)
SOLE = material("Sole", (0.78, 0.77, 0.72), rough=0.6)
SHOEDARK = material("SneakerTrim", (0.03, 0.03, 0.035), rough=0.5)
fabric(TROUSER)

# --- armature ----------------------------------------------------------------------------------------------------
ARM = bpy.data.objects.new("Armature", bpy.data.armatures.new("KaiArm"))
COLL.objects.link(ARM)
ARM.parent = ROOT
ARM.hide_render = True
ARM.data.display_type = "OCTAHEDRAL"
ARM.show_in_front = True
BONES = {  # name: (parent, head, tail)
    "root": (None, (0, 0, 0), (0, 0, 0.12)),
    "pelvis": ("root", (0, 0, 0.95), (0, 0, 1.03)),
    "spine": ("pelvis", (0, 0, 1.03), (0, 0, 1.26)),
    "chest": ("spine", (0, 0, 1.26), (0, 0, 1.40)),
    "neck": ("chest", (0, 0.01, 1.40), (0, 0.01, 1.47)),
    "head": ("neck", (0, 0, 1.47), (0, 0, 1.76)),
}
for sx_, sd in ((1, "L"), (-1, "R")):
    BONES.update({
        f"clavicle.{sd}": ("chest", (sx_ * 0.03, 0, 1.38), (sx_ * 0.19, 0, 1.385)),
        f"upper_arm.{sd}": (f"clavicle.{sd}", (sx_ * 0.19, 0, 1.385), (sx_ * 0.30, 0.01, 1.115)),
        f"forearm.{sd}": (f"upper_arm.{sd}", (sx_ * 0.30, 0.01, 1.115), (sx_ * 0.385, -0.03, 0.885)),
        f"hand.{sd}": (f"forearm.{sd}", (sx_ * 0.385, -0.03, 0.885), (sx_ * 0.42, -0.045, 0.73)),
        f"thigh.{sd}": ("pelvis", (sx_ * 0.09, 0, 0.92), (sx_ * 0.097, -0.01, 0.50)),
        f"shin.{sd}": (f"thigh.{sd}", (sx_ * 0.097, -0.01, 0.50), (sx_ * 0.10, 0.015, 0.09)),
        f"foot.{sd}": (f"shin.{sd}", (sx_ * 0.10, 0.015, 0.09), (sx_ * 0.10, -0.2, 0.04)),
    })
bpy.context.view_layer.objects.active = ARM
ARM.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for nm, (par, h_, t_) in BONES.items():
    eb = ARM.data.edit_bones.new(nm)
    eb.head, eb.tail = h_, t_
    if par:
        eb.parent = ARM.data.edit_bones[par]
bpy.ops.object.mode_set(mode="OBJECT")
for nm, infl in (("head", 1.0), ("neck", 0.35)):  # the Head empty (what the pipeline keys) nods head and neck
    pb = ARM.pose.bones[nm]
    pb.rotation_mode = "XYZ"
    # bone axes for a +Z bone: local X = world X, local Y = world Z, local Z = -world Y
    for idx, (ch, sgn) in enumerate((("0", 1.0), ("2", 1.0), ("1", -1.0))):
        fc = pb.driver_add("rotation_euler", idx)
        d = fc.driver
        d.type = "SCRIPTED"
        d.expression = f"{sgn * infl}*r"
        v = d.variables.new()
        v.name, v.type = "r", "SINGLE_PROP"
        v.targets[0].id_type, v.targets[0].id = "OBJECT", HEAD
        v.targets[0].data_path = f"rotation_euler[{ch}]"


def bind(o, bone, weights=None):
    """Skin a part to the armature: one bone at weight 1 (or a dict of bone -> per-vertex weights)."""
    nv = len(o.data.vertices)
    for b_, w_ in (weights or {bone: np.ones(nv)}).items():
        vg = o.vertex_groups.new(name=b_)
        for k in np.nonzero(w_ > 0.001)[0]:
            vg.add([int(k)], float(w_[k]), "REPLACE")
    o.parent = ARM
    m_ = o.modifiers.new("Armature", "ARMATURE")
    m_.object = ARM
    return o


# --- mesh helpers ----------------------------------------------------------------------------------------------
def catmull(pts, per=3):
    pts = np.asarray(pts, float)
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for t in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return np.array(out)


def limb_into(bm, path, rx, ry, n=14, per=3, caps=True, expo=2.0):
    path = np.asarray(path, float)
    sm_ = catmull(np.column_stack([path, rx, ry]), per)
    P_, RX, RY = sm_[:, :3], sm_[:, 3], sm_[:, 4]
    T = np.gradient(P_, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-9
    rings = []
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    cx = np.sign(np.cos(th)) * np.abs(np.cos(th)) ** (2 / expo)
    sy = np.sign(np.sin(th)) * np.abs(np.sin(th)) ** (2 / expo)

    def ring(c, t, a, b):
        ref = np.array([0.0, -1.0, 0.0]) if abs(t[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        s_ = np.cross(t, ref)
        s_ /= np.linalg.norm(s_)
        b_ = np.cross(t, s_)
        return [bm.verts.new(c + a * cx[k] * s_ + b * sy[k] * b_) for k in range(n)]

    first = [ring(P_[0] - T[0] * RX[0] * 0.55, T[0], RX[0] * 0.5, RY[0] * 0.5),
             ring(P_[0] - T[0] * RX[0] * 0.22, T[0], RX[0] * 0.86, RY[0] * 0.86)] if caps else []
    last = [ring(P_[-1] + T[-1] * RX[-1] * 0.22, T[-1], RX[-1] * 0.86, RY[-1] * 0.86),
            ring(P_[-1] + T[-1] * RX[-1] * 0.55, T[-1], RX[-1] * 0.5, RY[-1] * 0.5)] if caps else []
    rings = first + [ring(P_[i], T[i], RX[i], RY[i]) for i in range(len(P_))] + last
    made = []
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(n):
            made.append(bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])))
    if caps:
        for ringv, c in ((rings[0], P_[0] - T[0] * RX[0] * 0.7), (rings[-1], P_[-1] + T[-1] * RX[-1] * 0.7)):
            cv = bm.verts.new(c)
            for k in range(n):
                made.append(bm.faces.new((ringv[(k + 1) % n], ringv[k], cv) if ringv is rings[0] else (ringv[k], ringv[(k + 1) % n], cv)))
    bm.normal_update()
    mid = made[len(made) // 2]  # orient this sweep outward (away from its own axis)
    j = (len(made) // 2 // n) * n
    cen = sum((v.co for f in made[j:j + n] for v in f.verts[:1]), Vector()) / n
    if mid.normal.dot(mid.calc_center_median() - cen) < 0:
        bmesh.ops.reverse_faces(bm, faces=made)
    return bm


def finish(name, bm, mat, bone, smooth=True, subd=1, weights=None, outward=False):
    if outward:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me_ = bpy.data.meshes.new(name)
    bm.to_mesh(me_)
    bm.free()
    for p in me_.polygons:
        p.use_smooth = smooth
    me_.materials.append(mat)
    o = bpy.data.objects.new(name, me_)
    COLL.objects.link(o)
    bind(o, bone, weights)
    if subd:
        o.modifiers.new("Subd", "SUBSURF").render_levels = subd
        o.modifiers["Subd"].levels = 0
    return o


def limb(name, path, rx, ry, mat, bone, **kw):
    bm = bmesh.new()
    limb_into(bm, path, rx, ry, **kw)
    return finish(name, bm, mat, bone)


def loft(name, rings, mat, bone, expo=2.6, n=56, cy=0.0, thick=0.0, fold=None, delete=None, subd=1):
    bm = bmesh.new()
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    cxs = np.sign(np.cos(th)) * np.abs(np.cos(th)) ** (2 / expo)
    sys_ = np.sign(np.sin(th)) * np.abs(np.sin(th)) ** (2 / expo)
    rv = []
    for z, hx, hy, *cc in rings:
        yc = cy + (cc[0] if cc else 0.0)
        pts = [np.array([hx * cxs[k], yc + hy * sys_[k], z]) for k in range(n)]
        if fold is not None:
            pts = [p + fold(p) for p in pts]
        rv.append([bm.verts.new(p) for p in pts])
    for a, b in zip(rv[:-1], rv[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    # outward check on one face
    f0 = bm.faces[len(bm.faces) // 2]
    c0 = f0.calc_center_median()
    if f0.normal.dot(Vector((c0.x, c0.y - cy, 0))) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    if delete is not None:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if delete(f.calc_center_median())], context="FACES")
    o = finish(name, bm, mat, bone, subd=subd, outward=False)
    if thick:
        sol = o.modifiers.new("Thick", "SOLIDIFY")
        sol.thickness, sol.offset = thick, 0.0
        o.modifiers.move(o.modifiers.find("Thick"), 1)
    return o


def blobm(name, center, radii, mat, bone, power=1.0, rot=0.0, res=16):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=res, use_grid_fill=True)
    cr, sr = math.cos(rot), math.sin(rot)
    for v in bm.verts:
        v.co.normalize()
        x_, y_, z_ = [math.copysign(abs(c) ** power, c) * r for c, r in zip(v.co, radii)]
        v.co = (center[0] + x_ * cr - y_ * sr, center[1] + x_ * sr + y_ * cr, center[2] + z_)
    return finish(name, bm, mat, bone, outward=True)


def tubem(name, pts, rad, mat, bone, cyclic=False, n=8, per=3, weights=None):
    """Thin round wire/strip along points (real mesh so it can be skinned)."""
    bm = bmesh.new()
    P_ = catmull(pts + ([pts[0], pts[1]] if cyclic else []), per) if False else catmull(pts, per)
    limb_into(bm, P_, [rad] * len(P_), [rad] * len(P_), n=n, per=1, caps=not cyclic)
    return finish(name, bm, mat, bone, subd=0, weights=weights)


# --- torso: boxy open-collar black shirt (thickness, folds, V neckline, collar) ----------------------------------
def folds(p):
    x, y, z = p
    a = 0.0035 * math.sin(26 * x + 4.5 * z + 1.3 * math.sin(9 * z)) * (1.0 if y < 0 else 0.6)
    b = 0.004 * math.sin(7 * z + 2.0 * x) * math.exp(-((z - 0.9) / 0.25) ** 2)  # soft belly fold above the hem
    h = 0.007 * math.sin(14 * x + 3) * max(0.0, (0.88 - z) / 0.1)  # hem waves
    n_ = np.array([x * 4.0, (y + 0.01) * 6.0, 0.0])
    n_ /= np.linalg.norm(n_) + 1e-9
    return n_ * (a + b + h) * 1.0


def vcut(c):
    return c.y < 0.0 and c.z > 1.27 + 1.7 * abs(c.x)


torso_rings = [(0.86, 0.228, 0.138), (0.95, 0.228, 0.136), (1.06, 0.216, 0.125), (1.20, 0.225, 0.13),
               (1.31, 0.24, 0.124), (1.375, 0.225, 0.108), (1.415, 0.17, 0.088), (1.442, 0.108, 0.076), (1.452, 0.095, 0.072)]
shirt = loft("Shirt", torso_rings, SHIRT, "chest", expo=2.7, cy=0.012, thick=0.013, fold=folds, delete=vcut)
# collar: a fat rolled band along the V and round the back of the neck, plus two flat lapel flaps
cpts = [(0.0, -0.118, 1.28), (0.04, -0.113, 1.34), (0.083, -0.09, 1.405), (0.097, -0.02, 1.447),
        (0.066, 0.058, 1.455), (0.0, 0.077, 1.457)]
for sx_ in (1, -1):
    tubem(f"Collar{sx_}", [(sx_ * p[0], p[1], p[2]) for p in cpts], 0.0105, SHIRT, "chest", n=8)
    bm = bmesh.new()
    flap = [(sx_ * 0.012, -0.128, 1.285), (sx_ * 0.09, -0.108, 1.43), (sx_ * 0.17, -0.1, 1.36), (sx_ * 0.075, -0.133, 1.285)]
    vv = [bm.verts.new(p) for p in flap]
    bm.faces.new(vv)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    fl = finish(f"Lapel{sx_}", bm, SHIRT, "chest", subd=1, outward=False)
    so = fl.modifiers.new("Thick", "SOLIDIFY")
    so.thickness = 0.008
    fl.modifiers.move(fl.modifiers.find("Thick"), 1)

# --- neck + chest skin (blended chest/neck/head weights by height) -------------------------------------------------
bm = bmesh.new()
limb_into(bm, [(0, 0.012, 1.10), (0, 0.012, 1.26), (0, 0.014, 1.38), (0, 0.016, 1.47), (0, 0.02, 1.56)],
          [0.15, 0.14, 0.088, 0.058, 0.055], [0.09, 0.098, 0.07, 0.056, 0.053], n=24, per=5, caps=False)
neck = finish("Neck", bm, SKIN, "chest", subd=1)
zs = np.array([v.co.z for v in neck.data.vertices])
wh = sm(1.44, 1.53, zs)
wn = sm(1.33, 1.42, zs) * (1 - wh)
for o_ in (neck,):
    o_.vertex_groups.clear()
    for nm, w_ in (("head", wh), ("neck", wn), ("chest", 1 - wh - wn)):
        vg = o_.vertex_groups.new(name=nm)
        for k in np.nonzero(w_ > 0.001)[0]:
            vg.add([int(k)], float(w_[k]), "REPLACE")

# --- arms ---------------------------------------------------------------------------------------------------------
HANDS = {}
for sx_, sd in ((1, "L"), (-1, "R")):
    Sh, El, Wr = (np.array(BONES[f"upper_arm.{sd}"][1]), np.array(BONES[f"forearm.{sd}"][1]),
                  np.array(BONES[f"hand.{sd}"][1]))
    limb(f"UpperArm.{sd}", [Sh - (Sh - El) * 0.05, (Sh + El) / 2, El], [0.056, 0.05, 0.041], [0.056, 0.05, 0.041],
         SKIN, f"upper_arm.{sd}")
    blobm(f"Elbow.{sd}", tuple(El), (0.042, 0.042, 0.042), SKIN, f"forearm.{sd}")
    limb(f"Forearm.{sd}", [El, El + (Wr - El) * 0.4, Wr], [0.041, 0.039, 0.027], [0.044, 0.038, 0.023], SKIN,
         f"forearm.{sd}")
    sl = limb(f"Sleeve.{sd}", [Sh + np.array([-sx_ * 0.05, 0, 0.02]), Sh + (El - Sh) * 0.3, Sh + (El - Sh) * 0.62],
              [0.075, 0.078, 0.086], [0.07, 0.074, 0.08], SHIRT, f"upper_arm.{sd}", caps=False, expo=2.4)
    so = sl.modifiers.new("Thick", "SOLIDIFY")
    so.thickness = 0.01
    sl.modifiers.move(sl.modifiers.find("Thick"), 1)
    # --- hand: palm + 4 fingers + thumb, relaxed, slightly curled, aligned to the forearm ---
    d_ = (Wr - El) / np.linalg.norm(Wr - El)
    R_ = Vector((0, 0, -1)).rotation_difference(Vector(d_)).to_matrix()
    inward = -sx_  # palm faces the thigh

    def W(p):
        return Wr + np.array(R_ @ Vector(p))

    bm = bmesh.new()
    limb_into(bm, [W((0, 0, -0.005)), W((0, 0, -0.045)), W((0, 0, -0.088))], [0.016, 0.0165, 0.014],
              [0.032, 0.039, 0.041], n=12, per=3)
    fingers = [(-0.027, (0.043, 0.026, 0.02), 0.0088), (-0.009, (0.048, 0.03, 0.022), 0.0092),
               (0.009, (0.045, 0.028, 0.021), 0.0088), (0.027, (0.035, 0.022, 0.017), 0.0078)]
    for k, (yy, (l1, l2, l3), rr) in enumerate(fingers):
        z0 = -0.085
        c1 = 0.012 + 0.003 * k
        pts_ = [(0, yy, z0), (inward * 0.002, yy, z0 - l1), (inward * (0.002 + c1 * 0.5), yy - 0.001, z0 - l1 - l2 * 0.92),
                (inward * (0.002 + c1 * 1.9), yy - 0.002, z0 - l1 - l2 * 0.92 - l3 * 0.75)]
        limb_into(bm, [W(p) for p in pts_], [rr, rr * 0.95, rr * 0.88, rr * 0.8], [rr, rr * 0.95, rr * 0.88, rr * 0.8],
                  n=8, per=3)
    th_ = [(inward * 0.004, -0.028, -0.025), (inward * 0.002, -0.048, -0.052), (inward * 0.006, -0.062, -0.082),
           (inward * 0.012, -0.066, -0.106)]
    limb_into(bm, [W(p) for p in th_], [0.0125, 0.0115, 0.0105, 0.0095], [0.0125, 0.0115, 0.0105, 0.0095], n=8, per=3)
    HANDS[sd] = finish(f"Hand.{sd}", bm, SKIN, f"hand.{sd}", subd=1)

# --- legs, trousers, sneakers --------------------------------------------------------------------------------------
loft("TrouserPelvis", [(1.06, 0.195, 0.118), (0.97, 0.208, 0.128), (0.88, 0.205, 0.126), (0.80, 0.2, 0.12)],
     TROUSER, "pelvis", expo=2.4, cy=0.005, thick=0.0)
for sx_, sd in ((1, "L"), (-1, "R")):
    H, K, A = (np.array(BONES[f"thigh.{sd}"][1]), np.array(BONES[f"shin.{sd}"][1]), np.array(BONES[f"foot.{sd}"][1]))
    limb(f"Thigh.{sd}", [H + (0, 0, 0.04), (H + K) / 2 + (0.0, 0.004, 0), K], [0.108, 0.092, 0.07], [0.108, 0.094, 0.07],
         TROUSER, f"thigh.{sd}", caps=False)
    blobm(f"Knee.{sd}", tuple(K), (0.07, 0.07, 0.07), TROUSER, f"shin.{sd}")
    limb(f"Shin.{sd}", [K, K + (A - K) * 0.45, A + (0, 0, 0.04)], [0.07, 0.06, 0.054], [0.07, 0.06, 0.054], TROUSER,
         f"shin.{sd}", caps=False)
    limb(f"Ankle.{sd}", [A + (0, 0, 0.1), A + (0, 0.0, 0.02)], [0.032, 0.03], [0.034, 0.032], SKIN, f"foot.{sd}")
    rot = sx_ * 0.1
    ctr = (A[0] + sx_ * 0.0, -0.065, 0.058)
    blobm(f"Sneaker.{sd}", ctr, (0.052, 0.14, 0.05), SNEAK, f"foot.{sd}", power=0.8, rot=rot)
    blobm(f"Sole.{sd}", (ctr[0], -0.065, 0.016), (0.056, 0.15, 0.019), SOLE, f"foot.{sd}", power=0.5, rot=rot)
    blobm(f"ToeCap.{sd}", (ctr[0] - sx_ * 0.0, -0.165, 0.045), (0.048, 0.06, 0.04), SHOEDARK, f"foot.{sd}", power=0.9, rot=rot)
    tubem(f"Collar_shoe.{sd}", [(A[0] - 0.034, 0.02, 0.1), (A[0], 0.06, 0.1), (A[0] + 0.034, 0.02, 0.1),
                                (A[0], -0.02, 0.105), (A[0] - 0.034, 0.02, 0.1)], 0.011, SHOEDARK, f"foot.{sd}", n=8)

# --- thin silver chain: little interlocking links on a path round the neck, hanging in a V on the chest ---------------
bm = bmesh.new()
NL = 74
links = []
for k in range(NL):
    t = 2 * math.pi * k / NL
    sy_ = math.sin(t)
    dr_ = max(0.0, -sy_) ** 1.6
    z_ = 1.41 - 0.14 * dr_
    c_ = np.array([0.088 * math.cos(t) * (1 - 0.55 * dr_), 0.016 + sy_ * (0.075 + 0.033 * dr_), z_])
    links.append(c_)
for k in range(NL):
    c0, c1 = links[k], links[(k + 1) % NL]
    t_ = c1 - c0
    t_ /= np.linalg.norm(t_)
    s_ = np.cross(t_, [0, 0, 1.0] if abs(t_[2]) < 0.9 else [1.0, 0, 0])
    s_ /= np.linalg.norm(s_)
    if k % 2:
        s_ = np.cross(t_, s_)
    Rl, rl = 0.0052, 0.0012
    ringp = [c0 + t_ * 0.8 * Rl * math.cos(a) + s_ * 0.55 * Rl * math.sin(a) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
    vr = []
    for q in range(10):
        pc = ringp[q]
        tt = ringp[(q + 1) % 10] - ringp[q - 1]
        tt /= np.linalg.norm(tt)
        bb = np.cross(t_, s_)
        bb /= np.linalg.norm(bb)
        nn = np.cross(tt, bb)
        nn /= np.linalg.norm(nn)
        vr.append([bm.verts.new(pc + rl * (math.cos(a) * nn + math.sin(a) * bb)) for a in np.linspace(0, 2 * math.pi, 4, endpoint=False)])
    for q in range(10):
        for a in range(4):
            bm.faces.new((vr[q][a], vr[q][(a + 1) % 4], vr[(q + 1) % 10][(a + 1) % 4], vr[(q + 1) % 10][a]))
chain = finish("Chain", bm, SILVER, "chest", subd=0)


# --- save -------------------------------------------------------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(f"saved {OUT}")
