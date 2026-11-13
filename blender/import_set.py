"""Wire an imported environment (blender/imported.py SETS) to the reelforge set contract → <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/import_set.py -- <out.blend> <set_id> <preset>

Contract (render_plan.py relies on it): lights Key, Rim, Fill, Glow (custom props base_color/base_energy; moods
tint them by scene["mood_tint"]); empties Mark_A, Mark_B on the floor, characters facing -Y.
The authored model and practical lights are kept; the set is scaled/turned to real-world metres facing -Y,
cameras and leftover animation are dropped, textures packed, EEVEE + AgX set. Source scripts never run."""
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bl_common import EEVEE, look_at  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
OUT, SID = Path(args[0]), args[1]
LIB = runpy.run_path(str(HERE / "imported.py"))
SPEC = LIB["SETS"][SID]
PRESET = args[2] if len(args) > 2 else next(iter(SPEC["presets"]))
PR = SPEC["presets"][PRESET]
SRC = LIB["SRC_ROOT"] / SPEC["src"]
if not SRC.exists():
    raise SystemExit(f"source missing: {SRC}")
bpy.ops.wm.open_mainfile(filepath=str(SRC), load_ui=False, use_scripts=False)
sc = bpy.context.scene
for t in list(bpy.data.texts):
    bpy.data.texts.remove(t)

# --- cleanup: cameras, animation, objects nobody renders --------------------------------------------------
for o in list(bpy.data.objects):
    if o.type in ("CAMERA",) or o.name not in sc.objects or (o.hide_render and o.type != "EMPTY"):
        bpy.data.objects.remove(o, do_unlink=True)
for o in sc.objects:
    if o.animation_data:
        o.animation_data_clear()
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)

# --- real-world scale, facing -Y -------------------------------------------------------------------------
xf = SPEC["xform"]
s, rz = xf["scale"], math.radians(xf["rot_z"])
M = Matrix.Rotation(rz, 4, "Z") @ Matrix.Scale(s, 4)
ROOT = bpy.data.objects.new("SET_root", None)
sc.collection.objects.link(ROOT)
for o in list(sc.objects):
    if o is not ROOT and o.parent is None:
        mw = o.matrix_world.copy()
        o.parent = ROOT
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = mw
ROOT.matrix_world = M
for o in sc.objects:  # authored lights: same look at the new scale, then the preset's share of them
    if o.type == "LIGHT":
        o.data.energy *= (s * s if o.data.type != "SUN" else 1.0) * PR.get("practicals", 1.0)
bpy.context.view_layer.update()


def to_set(p):
    return M @ Vector(p)


COLL = bpy.data.collections.new("SET_contract")
sc.collection.children.link(COLL)
mark_a, mark_b = to_set(SPEC["mark_a"]), to_set(SPEC["mark_b"])
for name, loc in (("Mark_A", mark_a), ("Mark_B", mark_b)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    COLL.objects.link(e)
HEAD = mark_a + Vector((0, 0, 1.6))  # standing imported cast

# --- world, haze, grade -----------------------------------------------------------------------------------
sc.render.engine = EEVEE
sc.eevee.use_raytracing = True
sc.eevee.volumetric_end = 40.0
sc.render.use_motion_blur = True
sc.render.image_settings.file_format = "PNG"  # some sources were saved with a movie output format
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = PR.get("exposure", 0.0)
sc.view_settings.gamma = 1.0
w = bpy.data.worlds.new("World")  # authored worlds can point at missing HDRIs (magenta)
w.use_nodes = True
nt = w.node_tree
nt.nodes["Background"].inputs["Color"].default_value = (*PR["world"], 1)
nt.nodes["Background"].inputs["Strength"].default_value = 1.0
if PR.get("haze"):
    vol = nt.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Density"].default_value = PR["haze"] * 0.55
    vol.inputs["Color"].default_value = (*PR.get("haze_color", (0.75, 0.82, 1.0)), 1)
    nt.links.new(vol.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
sc.world = w
sc["mood_tint"] = PR.get("tint", 0.35)

# --- contract light rig around Mark_A ---------------------------------------------------------------------
RIG = {"Key": ("AREA", (0.8, -0.9, 2.0), 0.6), "Rim": ("AREA", (-0.9, 0.8, 2.1), 1.0),
       "Fill": ("AREA", (-1.3, -1.5, 1.6), 2.0), "Glow": ("POINT", (0.5, -0.4, 1.3), 0.1)}
for name, (kind, off, size) in RIG.items():
    color, energy = PR[name.lower()]
    ld = bpy.data.lights.new(name, kind)
    ld.color, ld.energy = color, energy
    if kind == "AREA":
        ld.size = size
    else:
        ld.shadow_soft_size = size
    o = bpy.data.objects.new(name, ld)
    o.location = mark_a + Vector(off)
    o["base_color"], o["base_energy"] = list(color), energy
    COLL.objects.link(o)
    look_at(o, HEAD)
    if name in ("Key", "Rim"):
        ld.volume_factor = 0.5

# --- pack, purge, save --------------------------------------------------------------------------------------
for im in bpy.data.images:
    if im.source == "FILE" and not im.packed_file and im.filepath:
        try:
            im.pack()
        except RuntimeError as e:
            print(f"WARNING {SID}: could not pack {im.name}: {e}")
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0  # no .blend1 copies (matt.blend is 1.6 GB)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT.resolve()), compress=True)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in sc.objects if o.type == "MESH")
print(f"IMPORTED SET {SID}/{PRESET}: {tris} tris, Mark_A={tuple(round(v, 2) for v in mark_a)} -> {OUT}")
