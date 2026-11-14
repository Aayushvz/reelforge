"""Wire an imported character (blender/imported.py) to the reelforge character contract → <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/import_character.py -- <out.blend> <char_id> [outfit]

Contract (render_plan.py / preview_*.py rely on it), all objects directly in collection CHAR_base:
CHAR_root (feet, on the mark) → Body (chest pivot: lean/breath) → Head (nods/turns), ElbowL/ElbowR (talk gestures);
FaceCtrl (52 ARKit custom props, drivers fan them out to shape keys and face bones);
FaceAnchor (+ "head_height") and EyeFocus, both riding the head bone.
The contract empties steer the rig through Copy Rotation (world) from pivot children that hold the posed bone
orientation, so a zero rotation on Body/Head/Elbow* leaves the relaxed pose untouched.
Quality is never reduced: no decimation, no texture resizing, all shape keys kept. Source scripts never run."""
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from reelforge.arkit import ARKIT_NAMES  # noqa: E402
from finish_character import finish  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
OUT, CID = Path(args[0]), args[1]
LIB = runpy.run_path(str(HERE / "imported.py"))
SPEC = LIB["CHARACTERS"][CID]
X, Z = LIB["X"], LIB["Z"]
SRC = LIB["SRC_ROOT"] / SPEC["src"]
if not SRC.exists():
    raise SystemExit(f"source missing: {SRC}")

# --- load (scripts stay off: use_scripts=False / factory startup) -------------------------------------
if SRC.suffix.lower() == ".blend":
    bpy.ops.wm.open_mainfile(filepath=str(SRC), load_ui=False, use_scripts=False)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SRC), automatic_bone_orientation=True)
sc = bpy.context.scene
for t in list(bpy.data.texts):  # embedded rig-UI scripts: never needed for rendering
    bpy.data.texts.remove(t)
ARM = bpy.data.objects[SPEC["rig"]]
keep_arms = {ARM.name, *SPEC.get("keep_armatures", [])}

# --- cleanup: lights, cameras, widgets, unused armatures --------------------------------------------
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name not in SPEC.get("delete", [])
          and any(m.type == "ARMATURE" and m.object and m.object.name in keep_arms for m in o.modifiers)]
keep = set(meshes) | {bpy.data.objects[n] for n in keep_arms}
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
COLL = bpy.data.collections.new("CHAR_base")
sc.collection.children.link(COLL)
for o in keep:
    for c in list(o.users_collection):
        c.objects.unlink(o)
    COLL.objects.link(o)
    o.hide_viewport = o.hide_render = False
    o.hide_set(False)
for o in meshes:  # the outfit's hidden pieces stay hidden
    o.hide_render = o.name in SPEC["outfits"][int(args[2]) if len(args) > 2 else 0].get("hide", [])
# prefix names: no clash with contract names (Freya has a mesh called "Body") and no "." (render_plan splits on it)
for o in keep:
    o.name = f"{CID}_{o.name}".replace(".", "_").replace(" ", "_")
bpy.context.view_layer.update()

for name, props in SPEC.get("props", {}).items():
    for k, v in props.items():
        ARM.pose.bones[name][k] = v
for pb in ARM.pose.bones:  # start from the rest pose, whatever the file was saved in
    pb.location = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.rotation_euler = (0, 0, 0)
if ARM.animation_data:
    ARM.animation_data.action = None
bpy.context.view_layer.update()

MW = ARM.matrix_world
BN = SPEC["bones"]


def pbone(name):
    if name not in ARM.pose.bones:
        raise SystemExit(f"{CID}: bone {name!r} not in {ARM.name}")
    return ARM.pose.bones[name]


def world_head(pb):
    return MW @ pb.head


def aim(name, child, target):
    """Rotate pose bone `name` (about its head) so its head→child direction points along world `target`."""
    pb, cb = pbone(name), pbone(child)
    cur = (world_head(cb) - world_head(pb)).normalized()
    q = cur.rotation_difference(Vector(target).normalized())
    m = MW @ pb.matrix
    t = Matrix.Translation(m.translation)
    pb.matrix = MW.inverted() @ (t @ q.to_matrix().to_4x4() @ t.inverted() @ m)
    bpy.context.view_layer.update()


# --- relaxed pose: arms down from the A/T pose, a soft elbow bend --------------------------------------
for side, s in (("l", 1), ("r", -1)):
    aim(*BN[f"upperarm_{side}"], (s * 0.16, 0.05, -1.0))
    aim(*BN[f"forearm_{side}"], (s * 0.10, -0.42, -1.0))


# --- contract empties ---------------------------------------------------------------------------------
def empty(name, loc, parent=None, size=0.05):
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = size
    COLL.objects.link(o)
    if parent is not None:
        o.parent = parent
    o.matrix_world = Matrix.Translation(loc)
    return o


ROOT = empty("CHAR_root", (0, 0, 0), size=0.3)
ARM.parent = ROOT
body_pb, head_pb = pbone(BN["chest"]), pbone(BN["head"])
BODY = empty("Body", world_head(body_pb), ROOT)
HEAD = empty("Head", world_head(head_pb), BODY)
ELBOWS = {"ElbowL": BN["forearm_l"][0], "ElbowR": BN["forearm_r"][0]}
for ename, bname in ELBOWS.items():
    empty(ename, world_head(pbone(bname)), BODY)
bpy.context.view_layer.update()


def steer(driver_empty, bone_name):
    """Pivot child holds the bone's current world orientation; the bone copies the pivot's world rotation."""
    pb = pbone(bone_name)
    piv = bpy.data.objects.new(f"{driver_empty.name}_pivot", None)
    piv.empty_display_size = 0.02
    COLL.objects.link(piv)
    piv.parent = driver_empty
    rot = (MW @ pb.matrix).to_quaternion().to_matrix().to_4x4()
    piv.matrix_world = Matrix.Translation(world_head(pb)) @ rot
    c = pb.constraints.new("COPY_ROTATION")
    c.name = "reelforge"
    c.target, c.target_space, c.owner_space = piv, "WORLD", "WORLD"
    c.mix_mode = "REPLACE"


steer(BODY, BN["chest"])
steer(HEAD, BN["head"])
for ename, bname in ELBOWS.items():
    steer(bpy.data.objects[ename], bname)
bpy.context.view_layer.update()

# --- FaceCtrl + drivers --------------------------------------------------------------------------------
CTRL = empty("FaceCtrl", (0, 0, 0), ROOT, 0.02)
for n in ARKIT_NAMES:
    CTRL[n] = 0.0
    CTRL.id_properties_ui(n).update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0)


def add_driver(id_owner, path, index, terms):
    """terms: [(arkit_channel, coefficient)] → one simple-expression driver (runs with Python autoexec off)."""
    fc = id_owner.driver_add(path, index) if index >= 0 else id_owner.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    used = {}
    for ch, k in terms:
        used[ch] = used.get(ch, 0.0) + k
    for ch in used:
        v = d.variables.new()
        v.name, v.type = ch, "SINGLE_PROP"
        v.targets[0].id_type, v.targets[0].id = "OBJECT", CTRL
        v.targets[0].data_path = f'["{ch}"]'
    d.expression = " + ".join(f"{ch}*({k:.6g})" for ch, k in used.items()) or "0"


n_keys = 0
key_terms = {}  # (shape_key datablock, key name) -> terms
for ch, entries in SPEC.get("keys", {}).items():
    for kname, w in entries:
        for o in meshes:
            sk = o.data.shape_keys
            if sk and kname in sk.key_blocks:
                key_terms.setdefault((sk, kname), []).append((ch, w))
for (sk, kname), terms in key_terms.items():
    add_driver(sk, f'key_blocks["{kname}"].value', -1, terms)
    n_keys += 1

bone_terms = {}  # (bone, prop, index) -> terms


def local_frame(pb):
    return (MW.to_3x3() @ pb.bone.matrix_local.to_3x3())


missing = set()
for ch, entries in SPEC.get("bone_face", {}).items():
    for bname, kind, *val in entries:
        if bname not in ARM.pose.bones:
            missing.add(bname)
            continue
        pb = ARM.pose.bones[bname]
        if kind == "rot":
            axis, deg = Vector(val[0]), val[1]
            loc_axis = local_frame(pb).normalized().inverted() @ axis
            pb.rotation_mode = "XYZ"
            for i in range(3):
                if abs(loc_axis[i]) > 1e-3:
                    bone_terms.setdefault((bname, "rotation_euler", i), []).append((ch, loc_axis[i] * math.radians(deg)))
        else:
            world_off = Vector(val[0]) if kind == "loc" else None
            if kind == "orbit":  # chord of the arc around the pivot (linear in the channel: fine for ≤20°)
                p = world_head(pb) - world_head(pbone(val[0]))
                world_off = Matrix.Rotation(math.radians(val[2]), 3, Vector(val[1])) @ p - p
            off = local_frame(pb).inverted() @ world_off
            for i in range(3):
                if abs(off[i]) > 1e-9:
                    bone_terms.setdefault((bname, "location", i), []).append((ch, off[i]))

# eye look: rotate eyeballs, or slide each eye's look-target
eyes = SPEC.get("eyes")
if eyes:
    yaw, pitch = 24.0, 18.0
    for i, (side, s) in enumerate((("Left", 1), ("Right", -1))):
        bname = eyes["bones"][i]
        # (rotation axis, degrees, world look direction); "out" = toward the character's own side (+X for left)
        moves = {f"eyeLookOut{side}": (Z, s * yaw, (s, 0, 0)), f"eyeLookIn{side}": (Z, -s * yaw, (-s, 0, 0)),
                 f"eyeLookUp{side}": (X, -pitch, (0, 0, 1)), f"eyeLookDown{side}": (X, pitch, (0, 0, -1))}
        pb = pbone(bname)
        if eyes["mode"] == "rot":
            pb.rotation_mode = "XYZ"
            fr = local_frame(pb).normalized().inverted()
            for ch, (axis, deg, _) in moves.items():
                la = fr @ Vector(axis)
                for j in range(3):
                    if abs(la[j]) > 1e-3:
                        bone_terms.setdefault((bname, "rotation_euler", j), []).append((ch, la[j] * math.radians(deg)))
        else:  # target: slide the look-target by tan(angle) * its distance from the eye
            ctr = world_head(pbone(eyes["centers"][i]))
            dist = (world_head(pb) - ctr).length
            fr = local_frame(pb).inverted()
            for ch, (axis, deg, wdir) in moves.items():
                off = fr @ (Vector(wdir) * math.tan(math.radians(abs(deg))) * dist)
                for j in range(3):
                    if abs(off[j]) > 1e-9:
                        bone_terms.setdefault((bname, "location", j), []).append((ch, off[j]))

for (bname, prop, i), terms in bone_terms.items():
    add_driver(ARM.pose.bones[bname], prop, i, terms)
if missing:
    print(f"WARNING {CID}: face bones not in rig, skipped: {sorted(missing)}")

# --- anchors on the head bone --------------------------------------------------------------------------
hd = pbone(BN["head_def"]) if BN["head_def"] in ARM.pose.bones else None
if eyes:
    names = eyes.get("centers") or eyes["bones"]
    eye_pts = [world_head(pbone(n)) for n in names]
    eye_mid = (eye_pts[0] + eye_pts[1]) / 2
else:
    eye_mid = world_head(head_pb) + Vector((0, -0.08, 0.08))
body_mesh = next(o for o in meshes if o.name == f"{CID}_{SPEC['body_mesh']}".replace(".", "_").replace(" ", "_"))
mw = body_mesh.matrix_world
near = [mw @ v.co for v in body_mesh.data.vertices if abs((mw @ v.co).x - eye_mid.x) < 0.09
        and abs((mw @ v.co).y - eye_mid.y) < 0.14 and (mw @ v.co).z > eye_mid.z - 0.2]
crown = max(p.z for p in near)
front = min(p.y for p in near if abs(p.z - eye_mid.z) < 0.02)
head_height = round(2.05 * (crown - eye_mid.z), 4)


def bone_child(name, loc, bone):
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = 0.02
    COLL.objects.link(o)
    o.parent, o.parent_type, o.parent_bone = ARM, "BONE", bone
    bpy.context.view_layer.update()
    o.matrix_world = Matrix.Translation(loc)
    return o


anchor_bone = hd.name if hd else BN["head"]
FA = bone_child("FaceAnchor", Vector((eye_mid.x, front + 0.01, eye_mid.z - 0.025)), anchor_bone)
FA["head_height"] = head_height
FA["min_head"] = float(SPEC.get("min_head", 0.0))  # the cinema camera never frames this character wider
bone_child("EyeFocus", Vector((eye_mid.x, front - 0.005, eye_mid.z)), anchor_bone)

# --- material fixes for known FBX-import mistakes (no resolution change) -------------------------------
for m in {m for o in meshes for m in o.data.materials if m and m.use_nodes}:
    nt = m.node_tree
    for l in nt.links:  # data maps read as sRGB tilt mirrored-UV halves in opposite directions (half-dark faces)
        if l.from_node.type == "TEX_IMAGE" and l.from_node.image and l.from_socket.name == "Color" and (
                l.to_node.type in ("NORMAL_MAP", "BUMP", "DISPLACEMENT")
                or l.to_socket.name in ("Roughness", "Metallic", "Alpha", "Specular IOR Level", "Normal")):
            l.from_node.image.colorspace_settings.name = "Non-Color"
    if any(n.type == "BSDF_PRINCIPLED" and n.inputs["Alpha"].is_linked for n in nt.nodes):
        m.use_transparent_shadow = True  # alpha hair cards: otherwise they shadow the face as solid shells
    for b in (n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"):
        for l in list(b.inputs["Metallic"].links):  # CC "Reflection" maps land on Metallic: dark blotches on cloth
            if l.from_node.type == "TEX_IMAGE" and "reflection" in (l.from_node.image.name if l.from_node.image else "").lower():
                nt.links.remove(l)
                b.inputs["Metallic"].default_value = 0.0
        if b.inputs["Alpha"].is_linked and not b.inputs["Roughness"].is_linked and b.inputs["Roughness"].default_value < 0.05:
            b.inputs["Roughness"].default_value = 0.6  # mirror-glossy alpha cards (scalp) sparkle white
            if not b.inputs["Specular IOR Level"].is_linked:
                b.inputs["Specular IOR Level"].default_value = 0.3

# --- pack textures, drop orphans, save -----------------------------------------------------------------
for im in bpy.data.images:
    if im.source == "FILE" and not im.packed_file and im.filepath:
        try:
            im.pack()
        except RuntimeError as e:
            print(f"WARNING {CID}: could not pack {im.name}: {e}")
print(f"FINISHED {CID}: {finish(CID)}")  # merge duplicate textures, the liveliness shading pass
# a fresh default scene: the source's render/shadow settings must not leak into previews (Freya's darkened half her face)
old = bpy.context.window.scene if bpy.context.window else sc
clean = bpy.data.scenes.new("Scene")
clean.collection.children.link(COLL)
if bpy.context.window:
    bpy.context.window.scene = clean
for s in list(bpy.data.scenes):
    if s != clean:
        bpy.data.scenes.remove(s)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0  # no .blend1 copies (matt.blend is 1.6 GB)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT.resolve()), compress=True)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
print(f"IMPORTED {CID}: {len(meshes)} meshes, {tris} tris, {n_keys} shape-key drivers, {len(bone_terms)} bone drivers, "
      f"head_height={head_height} -> {OUT}")
