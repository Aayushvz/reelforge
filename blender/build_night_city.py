"""Night-city desk set → <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/build_night_city.py -- <out.blend>"""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_common import box, code_screen_material, empty, look_at, material  # noqa: E402

OUT = Path(sys.argv[sys.argv.index("--") + 1])
rng = random.Random(42)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
COLL = bpy.data.collections.new("SET_night_city")
sc.collection.children.link(COLL)
HEAD_TARGET = (0, 0.15, 1.3)

# --- render + color management ---------------------------------------------
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.eevee.use_raytracing = True
sc.eevee.volumetric_end = 60.0
sc.render.use_motion_blur = True
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

# --- world: deep night + volumetric haze ------------------------------------
w = bpy.data.worlds.new("NightWorld")
w.use_nodes = True
nt = w.node_tree
nt.nodes["Background"].inputs["Color"].default_value = (0.004, 0.006, 0.015, 1)
vol = nt.nodes.new("ShaderNodeVolumeScatter")
vol.inputs["Density"].default_value = 0.012
vol.inputs["Color"].default_value = (0.7, 0.8, 1.0, 1)
nt.links.new(vol.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
sc.world = w

# --- room ---------------------------------------------------------------
FLOOR = material("Floor", (0.03, 0.03, 0.035), rough=0.6)
WALL = material("Wall", (0.025, 0.028, 0.04), rough=0.8)
WOOD = material("Wood", (0.18, 0.10, 0.06), rough=0.45, coat=0.2)
DARK = material("DarkPlastic", (0.02, 0.02, 0.022), rough=0.4)
MUG = material("Mug", (0.95, 0.42, 0.12), rough=0.3, coat=0.5)
NOTE_Y = material("NoteYellow", (1.0, 0.85, 0.2), rough=0.8)
NOTE_O = material("NoteOrange", (1.0, 0.5, 0.15), rough=0.8)
box("Floor", (0, 0, -0.01), (10, 10, 0.02), COLL, FLOOR)
box("WallLow", (0, 1.3, 0.45), (6, 0.1, 0.9), COLL, WALL)
box("WallHigh", (0, 1.3, 3.0), (6, 0.1, 0.4), COLL, WALL)
box("WallL", (-2.3, 1.3, 1.85), (1.4, 0.1, 1.9), COLL, WALL)
box("WallR", (2.3, 1.3, 1.85), (1.4, 0.1, 1.9), COLL, WALL)
box("MullionV", (0, 1.3, 1.85), (0.05, 0.08, 1.9), COLL, DARK)
box("MullionH", (0, 1.3, 1.85), (3.2, 0.08, 0.05), COLL, DARK)

# --- desk + props ---------------------------------------------------------
box("Desk", (0, -0.28, 0.74), (2.2, 0.65, 0.04), COLL, WOOD)
box("Keyboard", (0, -0.36, 0.77), (0.42, 0.14, 0.02), COLL, DARK)
box("NoteA", (-0.25, -0.5, 0.762), (0.08, 0.08, 0.002), COLL, NOTE_Y)
box("NoteB", (0.18, -0.52, 0.762), (0.08, 0.06, 0.002), COLL, NOTE_O)
mug = box("Mug", (-0.5, -0.32, 0.81), (0.08, 0.08, 0.1), COLL, MUG)
screen_mat = code_screen_material("ScreenMat", (0.35, 0.6, 1.0), strength=3.0)
monitor = box("Monitor", (0, 0, 0), (0.56, 0.03, 0.34), COLL, DARK)
screen = box("Screen", (0, -0.017, 0), (0.53, 0.002, 0.31), COLL, screen_mat)
screen.parent = monitor
monitor.location = (0.55, -0.38, 1.0)
monitor.rotation_euler = (0, 0, math.radians(-35))
box("Stand", (0.55, -0.36, 0.82), (0.05, 0.05, 0.12), COLL, DARK)

# --- holographic panels (story-reactive props) -------------------------------
holo = code_screen_material("HoloMat", (0.35, 0.6, 1.0), strength=2.0)
for i, (x, z, rz) in enumerate(((-0.95, 1.55, 20), (1.0, 1.75, -18), (-0.7, 2.1, 10))):
    p = box(f"Holo{i}", (0, 0, 0), (0.5, 0.003, 0.32), COLL, holo)
    p.location = (x, 0.95, z)
    p.rotation_euler = (0, 0, math.radians(rz))

# --- city: dark buildings with lit windows (becomes bokeh) --------------------
BUILD = material("Building", (0.008, 0.01, 0.018), rough=0.7)
win_mats = [material("WinWarm", (1.0, 0.7, 0.35), emit=14.0),
            material("WinCool", (0.4, 0.6, 1.0), emit=12.0),
            material("WinWhite", (1.0, 0.95, 0.9), emit=10.0)]
win_bms = [bmesh.new() for _ in win_mats]
for _ in range(26):
    bx, by = rng.uniform(-22, 22), rng.uniform(9, 40)
    bw, bh, bd = rng.uniform(3, 7), rng.uniform(6, 26), rng.uniform(3, 6)
    box("Bldg", (bx, by, bh / 2), (bw, bd, bh), COLL, BUILD)
    face_y = by - bd / 2 - 0.05
    cols, rows = int(bw / 0.9), int(bh / 1.1)
    for cxi in range(cols):
        for ryi in range(rows):
            if rng.random() > 0.35:
                continue
            k = rng.choices((0, 1, 2), weights=(70, 20, 10))[0]
            m = (Matrix.Translation((bx - bw / 2 + 0.45 + cxi * 0.9, face_y, 0.8 + ryi * 1.1))
                 @ Matrix.Diagonal((0.45, 0.05, 0.6, 1.0)))
            bmesh.ops.create_cube(win_bms[k], size=1.0, matrix=m)
for bm_, m_, n_ in zip(win_bms, win_mats, ("WinsWarm", "WinsCool", "WinsWhite")):
    me = bpy.data.meshes.new(n_)
    bm_.to_mesh(me)
    bm_.free()
    me.materials.append(m_)
    COLL.objects.link(bpy.data.objects.new(n_, me))

# --- lights ---------------------------------------------------------------
def light(name, kind, loc, color, energy, size=0.5):
    ld = bpy.data.lights.new(name, kind)
    ld.color, ld.energy = color, energy
    if kind == "AREA":
        ld.size = size
    else:
        ld.shadow_soft_size = size
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    COLL.objects.link(o)
    look_at(o, HEAD_TARGET)
    return o

light("Key", "AREA", (0.75, -0.75, 1.45), (1.0, 0.62, 0.35), 180, 0.6)
light("Rim", "AREA", (-0.6, 0.95, 1.9), (0.25, 0.45, 1.0), 220, 1.0)
light("Fill", "AREA", (-1.3, -1.5, 1.2), (0.5, 0.6, 1.0), 15, 2.0)
light("Glow", "POINT", (0.45, -0.3, 0.9), (1.0, 0.55, 0.2), 60, 0.1)

empty("Mark_A", (0, 0.15, 0), COLL)
empty("Mark_B", (0.9, 0.15, 0), COLL)

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(f"saved {OUT}")
