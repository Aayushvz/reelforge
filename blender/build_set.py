"""Build one environment in one lighting preset → <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/build_set.py -- <out.blend> <set_id> <preset>

Contract (render_plan.py relies on it): lights Key, Rim, Fill, Glow (each keeps its preset colour/energy in
custom props base_color/base_energy so moods tint rather than replace them, by scene["mood_tint"]);
empties Mark_A, Mark_B; a surface at desk height (z≈0.76) in front of Mark_A for the arms to rest on.
Optional: materials ScreenMat / HoloMat with a "Code" node recolour with the mood.
Sets are built from simple procedural pieces; looks come from lighting, emissive practicals and depth."""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_common import EEVEE, box, code_screen_material, ellipsoid, empty, look_at, material  # noqa: E402
from sets import SETS  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
OUT, SET_ID, PRESET = Path(args[0]), args[1], args[2]
PR = SETS[SET_ID]["presets"][PRESET]
rng = random.Random(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
COLL = bpy.data.collections.new(f"SET_{SET_ID}")
sc.collection.children.link(COLL)
HEAD = (0, 0.15, 1.35)
MARK_B = SETS[SET_ID].get("mark_b", (-0.9, 0.15, 0))  # second seat: left, away from monitors/registers


def E(group, default=1.0):
    """Emission strength of a group of practicals in this preset."""
    return PR.get("emit", {}).get(group, default)


def em(name, color, group, default=4.0):
    return material(name, color, emit=E(group, default))


def cyl(name, loc, r, depth, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    for c in o.users_collection:
        c.objects.unlink(o)
    COLL.objects.link(o)
    o.data.materials.append(mat)
    return o


def merged(name, mat, cubes):
    """Many boxes as one mesh: cubes = [(center, size)]."""
    bm = bmesh.new()
    for c, s in cubes:
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*s, 1.0)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    return o


def beads(name, pts, r, mat):
    bm = bmesh.new()
    for p in pts:
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r, matrix=Matrix.Translation(p))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    return o


def string_lights(name, a, b, sag, n, mat, r=0.03):
    pts = []
    for k in range(n):
        t = k / (n - 1)
        pts.append(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))
        pts[-1] = (pts[-1][0], pts[-1][1], pts[-1][2] - sag * 4 * t * (1 - t))
    return beads(name, pts, r, mat)


def skyline(y0, y1, n, wmats, bmat, xspan=24, hmax=26, density=0.45):
    """Dark blocks with lit windows; far away they turn into bokeh."""
    cubes, wins = [], [[] for _ in wmats]
    for _ in range(n):
        bx, by = rng.uniform(-xspan, xspan), rng.uniform(y0, y1)
        bw, bh, bd = rng.uniform(3, 7), rng.uniform(5, hmax), rng.uniform(3, 6)
        cubes.append(((bx, by, bh / 2), (bw, bd, bh)))
        for cx in range(int(bw / 0.9)):
            for rz in range(int(bh / 1.1)):
                if rng.random() < density:
                    k = rng.randrange(len(wmats))
                    wins[k].append(((bx - bw / 2 + 0.45 + cx * 0.9, by - bd / 2 - 0.05, 0.8 + rz * 1.1),
                                    (0.45, 0.05, 0.6)))
    merged("Skyline", bmat, cubes)
    for k, (m, w) in enumerate(zip(wmats, wins)):
        if w:
            merged(f"Windows{k}", m, w)


def backdrop(name, y, w, h, color, strength, z0=-2.0):
    """Far emissive card: sky, sea glow, street beyond a window."""
    m = material(name, color, emit=strength)
    return box(name, (0, y, z0 + h / 2), (w, 0.05, h), COLL, m)


def sky_gradient(name, y, w, h, top, bottom, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emn = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].color = (*top, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emn.inputs["Color"])
    emn.inputs["Strength"].default_value = strength
    nt.links.new(emn.outputs[0], out.inputs["Surface"])
    return box(name, (0, y, h / 2 - 3), (w, 0.05, h), COLL, m)


def rain_sheet(name, y, w, h, z0, strength=0.6):
    """Streaky translucent rain in front of a window or the street."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    emn = nt.nodes.new("ShaderNodeEmission")
    emn.inputs["Color"].default_value = (0.7, 0.8, 1.0, 1)
    emn.inputs["Strength"].default_value = strength
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (140, 1, 1.0)  # thin and long: streaks, not dots
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.62, 0.7
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(emn.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return box(name, (0, y, z0 + h / 2), (w, 0.01, h), COLL, m)


def wall_with_window(y, x0, x1, z0, z1, mat, width=7.0, height=3.2, mull=None):
    """Back wall with a rectangular opening (x0..x1, z0..z1)."""
    half = width / 2
    box("WallBelow", (0, y, z0 / 2), (width, 0.12, z0), COLL, mat)
    box("WallAbove", (0, y, (z1 + height) / 2), (width, 0.12, height - z1), COLL, mat)
    box("WallLeft", ((-half + x0) / 2, y, (z0 + z1) / 2), (x0 + half, 0.12, z1 - z0), COLL, mat)
    box("WallRight", ((x1 + half) / 2, y, (z0 + z1) / 2), (half - x1, 0.12, z1 - z0), COLL, mat)
    if mull:
        cubes = [(((x0 + x1) / 2, y, z), (x1 - x0, 0.06, 0.04)) for z in (z0, (z0 + z1) / 2, z1)]
        n = max(1, int((x1 - x0) / 1.0))
        cubes += [((x0 + (x1 - x0) * k / n, y, (z0 + z1) / 2), (0.04, 0.06, z1 - z0)) for k in range(n + 1)]
        merged("Mullions", mull, cubes)


def desk(mat, top_z=0.74, w=2.2, d=0.65, legs=None):
    box("Desk", (0, -0.28, top_z), (w, d, 0.04), COLL, mat)
    if legs:
        for sx in (-1, 1):
            box(f"DeskLeg{sx}", (sx * (w / 2 - 0.06), -0.28, top_z / 2), (0.05, d * 0.9, top_z), COLL, legs)


def monitor(x, y, rz, screen_mat, frame):
    mon = box("Monitor", (0, 0, 0), (0.56, 0.03, 0.34), COLL, frame)
    scr = box("Screen", (0, -0.017, 0), (0.53, 0.002, 0.31), COLL, screen_mat)
    scr.parent = mon
    mon.location, mon.rotation_euler = (x, y, 1.0), (0, 0, math.radians(rz))
    box("Stand", (x, y + 0.02, 0.82), (0.05, 0.05, 0.12), COLL, frame)


def screen_material(name, color, strength):
    m = code_screen_material(name, color, strength=strength)
    c = m.node_tree.nodes["Code"]
    c.inputs["Scale"].default_value, c.inputs["Mortar Size"].default_value = 1.6, 0.01
    tc = m.node_tree.nodes.new("ShaderNodeTexCoord")
    mp = m.node_tree.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)  # screens face -Y: rows follow height
    m.node_tree.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    m.node_tree.links.new(mp.outputs["Vector"], c.inputs["Vector"])
    return m


def mug(x, y, color):
    m = material("Mug", color, rough=0.3, coat=0.5)
    cyl("Mug", (x, y, 0.81), 0.04, 0.1, m)


def plant(x, y, z=0.0, s=1.0):
    pot = material("Pot", (0.25, 0.1, 0.05), rough=0.7)
    leaf = material("Leaf", (0.03, 0.12, 0.03), rough=0.5, sheen=0.3)
    cyl("Pot", (x, y, z + 0.15 * s), 0.12 * s, 0.3 * s, pot)
    for k in range(7):
        a = k * 2.4
        ellipsoid("Leaf", (x + 0.12 * s * math.cos(a), y + 0.12 * s * math.sin(a), z + (0.42 + 0.05 * k % 3) * s),
                  (0.06 * s, 0.14 * s, 0.03 * s), COLL, leaf, segs=12, subd=0).rotation_euler = (0.6, 0, a)


def textured(m, kind, scale=1.0, vertical=False):
    """Procedural surface detail on an existing material: colour variation + bump.
    kind: wood | planks | tiles | brick | concrete | cobbles. vertical=True for walls facing -Y."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    base = tuple(b.inputs["Base Color"].default_value)[:3]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    if vertical:
        mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    if kind in ("tiles", "brick", "planks"):
        t = nt.nodes.new("ShaderNodeTexBrick")
        t.inputs["Color1"].default_value = (*base, 1)
        t.inputs["Color2"].default_value = (*(c * 0.82 for c in base), 1)
        mortar = (0.6, 0.6, 0.58) if kind == "tiles" else tuple(c * (0.45 if kind == "planks" else 1.4) for c in base)
        t.inputs["Mortar"].default_value = (*mortar, 1)
        t.inputs["Scale"].default_value = {"tiles": 2.5, "brick": 4.0, "planks": 1.2}[kind]
        t.inputs["Mortar Size"].default_value = 0.01 if kind == "planks" else 0.02
        if kind == "planks":
            t.inputs["Brick Width"].default_value, t.inputs["Row Height"].default_value = 2.5, 0.12
        elif kind == "tiles":
            t.inputs["Brick Width"].default_value, t.inputs["Row Height"].default_value = 0.4, 0.4
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        color, height = t.outputs["Color"], t.outputs["Fac"]
    else:
        if kind == "wood":
            t = nt.nodes.new("ShaderNodeTexWave")
            t.inputs["Scale"].default_value, t.inputs["Distortion"].default_value = 3.0, 6.0
            t.inputs["Detail"].default_value = 4.0
        elif kind == "cobbles":
            t = nt.nodes.new("ShaderNodeTexVoronoi")
            t.inputs["Scale"].default_value = 6.0
        else:  # concrete
            t = nt.nodes.new("ShaderNodeTexNoise")
            t.inputs["Scale"].default_value, t.inputs["Detail"].default_value = 6.0, 10.0
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        fac = t.outputs["Distance"] if kind == "cobbles" else t.outputs["Fac"]
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        lo, hi = (0.82, 1.12) if kind == "wood" else (0.6, 1.3)  # wood: subtle grain, not zebra stripes
        ramp.color_ramp.elements[0].color = (*(c * lo for c in base), 1)
        ramp.color_ramp.elements[1].color = (*(min(1, c * hi) for c in base), 1)
        nt.links.new(fac, ramp.inputs["Fac"])
        color, height = ramp.outputs["Color"], fac
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = {"cobbles": 0.6, "tiles": 0.25, "brick": 0.4, "planks": 0.3}.get(kind, 0.12)
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(color, b.inputs["Base Color"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def lamp_shade(name, loc, color, group, r=0.12):
    m = em(name, color, group, 6.0)
    return ellipsoid(name, loc, (r, r, r * 0.8), COLL, m, segs=16, subd=0)


# --- the ten sets -----------------------------------------------------------------------
def night_city():
    floor = textured(material("Floor", (0.03, 0.03, 0.035), rough=0.25 if PRESET == "rainy" else 0.6), "concrete")
    wall = material("Wall", (0.025, 0.028, 0.04), rough=0.8)
    wood = textured(material("Wood", (0.10, 0.055, 0.03), rough=0.55, coat=0.1), "wood")
    dark = material("DarkPlastic", (0.02, 0.02, 0.022), rough=0.4)
    box("Floor", (0, 0, -0.01), (10, 10, 0.02), COLL, floor)
    wall_with_window(1.3, -1.6, 1.6, 0.9, 2.8, wall, mull=dark)
    desk(wood)
    box("Keyboard", (0, -0.36, 0.77), (0.42, 0.14, 0.02), COLL, dark)
    mug(-0.5, -0.32, (0.95, 0.42, 0.12))
    monitor(0.55, -0.38, -35, screen_material("ScreenMat", PR["screen"], 1.4), dark)
    holo = screen_material("HoloMat", PR["screen"], 1.0)
    for i, (x, z, rz) in enumerate(((-0.95, 1.55, 20), (1.0, 1.75, -18), (-0.7, 2.1, 10))):
        p = box(f"Holo{i}", (x, 0.95, z), (0.5, 0.003, 0.32), COLL, holo)
        p.rotation_euler = (0, 0, math.radians(rz))
    wm = [em("WinWarm", (1.0, 0.5, 0.15), "windows"), em("WinCool", (0.2, 0.42, 1.0), "windows"),
          em("WinAccent", PR.get("accent", (1.0, 0.85, 0.65)), "windows")]
    skyline(9, 40, 26, wm, material("Building", (0.008, 0.01, 0.018), rough=0.7))
    if PRESET == "neon_pink":
        for i, (x, z, c) in enumerate(((-3, 4, (1.0, 0.1, 0.5)), (4, 6, (0.1, 0.6, 1.0)), (1.5, 9, (1.0, 0.2, 0.7)))):
            box(f"Neon{i}", (x, 9.5, z), (2.2, 0.1, 0.5), COLL, material(f"Neon{i}", c, emit=E("neon", 12)))
    if PRESET == "rainy":
        rain_sheet("Rain", 1.25, 3.2, 1.9, 0.9, 0.5)


def bedroom():
    wall = material("Wall", PR.get("wall", (0.12, 0.1, 0.14)), rough=0.85)
    floor = textured(material("Floor", (0.12, 0.07, 0.04), rough=0.5), "planks")
    wood = material("Desk", (0.03, 0.03, 0.035), rough=0.4)
    box("Floor", (0, 0, -0.01), (10, 10, 0.02), COLL, floor)
    wall_with_window(1.6, 0.5, 1.9, 1.0, 2.3, wall, mull=material("Frame", (0.8, 0.8, 0.8), rough=0.5))
    box("SideWall", (-2.2, 0, 1.6), (0.12, 5, 3.2), COLL, wall)
    sky_gradient("Outside", 6, 12, 8, PR["sky_top"], PR["sky_bottom"], E("sky", 1.0))
    desk(wood, legs=wood)
    dark = material("DarkPlastic", (0.02, 0.02, 0.022), rough=0.4)
    box("Keyboard", (0, -0.36, 0.77), (0.42, 0.14, 0.02), COLL, dark)
    monitor(0.5, -0.36, -30, screen_material("ScreenMat", PR["screen"], 1.4), dark)
    mug(-0.55, -0.3, (0.2, 0.5, 0.9))
    # bed with duvet and pillows, back-left
    duvet = material("Duvet", (0.45, 0.42, 0.55), rough=0.9, sheen=0.5)
    box("BedBase", (-1.3, 1.0, 0.2), (1.5, 1.1, 0.4), COLL, material("BedFrame", (0.08, 0.05, 0.03), rough=0.6))
    ellipsoid("Duvet", (-1.3, 0.95, 0.45), (0.75, 0.55, 0.12), COLL, duvet, segs=24)
    ellipsoid("Pillow", (-1.75, 1.3, 0.6), (0.25, 0.15, 0.08), COLL, material("Pillow", (0.85, 0.85, 0.82), rough=0.9))
    # LED strip along the wall top and behind the desk
    led = em("LED", PR["led"], "led", 6.0)
    box("LEDTop", (0, 1.53, 2.95), (5.5, 0.02, 0.025), COLL, led)
    box("LEDDesk", (0, 0.06, 0.73), (2.1, 0.02, 0.02), COLL, led)
    for i, (x, z, c) in enumerate(((-0.6, 1.9, (0.9, 0.3, 0.1)), (-0.05, 2.0, (0.1, 0.3, 0.8)))):
        box(f"Poster{i}", (x, 1.53, z), (0.42, 0.01, 0.6), COLL, material(f"Poster{i}", c, rough=0.7))
    lamp_shade("DeskLamp", (1.0, -0.1, 1.05), (1.0, 0.7, 0.35), "lamp", 0.09)  # right: Mark_B sits left
    box("Shelf", (1.2, 1.5, 1.4), (0.9, 0.2, 0.03), COLL, wood)
    for k in range(5):
        box(f"Figure{k}", (0.85 + k * 0.17, 1.5, 1.48), (0.06, 0.06, 0.13), COLL,
            material(f"Fig{k}", (rng.random(), rng.random() * 0.6, rng.random()), rough=0.4))


def rooftop():
    con = textured(material("Concrete", (0.12, 0.11, 0.1), rough=0.8), "concrete")
    box("Roof", (0, 3, -0.01), (12, 12, 0.02), COLL, con)
    desk(con, top_z=0.72, w=2.4, d=0.5)
    box("Parapet", (0, -0.28, 0.36), (2.4, 0.4, 0.72), COLL, con)
    sky_gradient("Sky", 120, 400, 160, PR["sky_top"], PR["sky_bottom"], E("sky", 1.0))
    wm = [em("WinWarm", (1.0, 0.55, 0.2), "windows", 3.0), em("WinCool", (0.4, 0.6, 1.0), "windows", 3.0)]
    skyline(25, 90, 60, wm, material("Building", PR.get("building", (0.02, 0.02, 0.03)), rough=0.7),
            xspan=60, hmax=45, density=PR.get("win_density", 0.4))
    box("Tank", (-2.2, 3.5, 1.2), (1.0, 1.0, 1.6), COLL, material("Tank", (0.15, 0.08, 0.05), rough=0.7))
    bulbs = em("Bulbs", (1.0, 0.75, 0.4), "string", 6.0)
    for i, (a, b) in enumerate((((-3, 0.8, 2.6), (3, 2.5, 2.4)), ((-3, 3.0, 2.5), (3, 1.2, 2.7)))):
        string_lights(f"String{i}", a, b, 0.35, 28, bulbs)
    for x in (-3, 3):
        cyl(f"Pole{x}", (x, 1.8, 1.3), 0.03, 2.6, material("Pole", (0.05, 0.05, 0.05), rough=0.5))
    plant(1.6, 1.2, 0, 1.3)


def cafe():
    floor = textured(material("Tiles", (0.15, 0.13, 0.11), rough=0.35), "tiles")
    wall = textured(material("Wall", (0.2, 0.13, 0.08), rough=0.8), "brick", vertical=True)
    box("Floor", (0, 0, -0.01), (10, 10, 0.02), COLL, floor)
    wall_with_window(1.5, -2.4, 2.0, 0.8, 2.7, wall, mull=material("Frame", (0.03, 0.04, 0.03), rough=0.4))
    top = material("Marble", (0.75, 0.72, 0.68), rough=0.2, coat=0.3)
    for x in (0, MARK_B[0]):  # one table per seat
        cyl("Table", (x, -0.25, 0.74), 0.45, 0.04, top, verts=48)
        cyl("Pedestal", (x, -0.25, 0.37), 0.04, 0.72, material("Iron", (0.02, 0.02, 0.02), rough=0.4))
    cup = material("Cup", (0.9, 0.88, 0.84), rough=0.25, coat=0.5)
    cyl("Saucer", (-0.15, -0.35, 0.765), 0.08, 0.01, cup, verts=32)
    cyl("Cup", (-0.15, -0.35, 0.8), 0.045, 0.07, cup, verts=32)
    # street across: shopfronts, awnings, sky
    sky_gradient("Sky", 30, 80, 40, PR["sky_top"], PR["sky_bottom"], E("sky", 1.0))
    for i in range(7):
        x = -9 + i * 3
        c = [(0.35, 0.2, 0.12), (0.18, 0.22, 0.25), (0.3, 0.28, 0.22)][i % 3]
        box(f"Facade{i}", (x, 9, 4), (2.9, 0.5, 8), COLL, material(f"Facade{i}", c, rough=0.8))
        box(f"Shop{i}", (x, 8.7, 1.2), (2.2, 0.1, 1.6), COLL,
            em(f"Shop{i}", [(1.0, 0.7, 0.4), (0.9, 0.85, 0.7), (1.0, 0.5, 0.3)][i % 3], "shops", 2.0))
        box(f"Awning{i}", (x, 8.3, 2.2), (2.6, 0.8, 0.05), COLL,
            material(f"Awning{i}", [(0.5, 0.05, 0.05), (0.05, 0.2, 0.1), (0.6, 0.4, 0.05)][i % 3], rough=0.7))
    box("Street", (0, 5, -0.05), (30, 7, 0.02), COLL, material("Asphalt", (0.03, 0.03, 0.035),
                                                              rough=0.15 if PRESET == "rainy_day" else 0.7))
    for x in (-1.2, 0.3, 1.6):
        cyl(f"Cord{x}", (x, 0.9, 2.75), 0.004, 0.7, material("Cord", (0.02, 0.02, 0.02)))
        lamp_shade(f"Pendant{x}", (x, 0.9, 2.35), (1.0, 0.72, 0.4), "pendants", 0.11)
    plant(-1.9, 1.1, 0, 1.4)
    if PRESET == "rainy_day":
        rain_sheet("Rain", 1.45, 4.4, 1.9, 0.8, 0.45)
    if PRESET == "evening_fairy":
        string_lights("Fairy", (-2.3, 1.42, 2.6), (1.9, 1.42, 2.6), 0.3, 40,
                      em("FairyBulbs", (1.0, 0.8, 0.45), "fairy", 8.0), r=0.018)


def lantern_street():
    cob = textured(material("Cobbles", (0.09, 0.08, 0.07), rough=0.5), "cobbles")
    box("Street", (0, 10, -0.01), (8, 30, 0.02), COLL, cob)
    table = material("BistroTop", (0.06, 0.15, 0.1), rough=0.4, coat=0.2)
    for x in (0, MARK_B[0]):
        cyl("Table", (x, -0.25, 0.74), 0.4, 0.03, table, verts=40)
        cyl("Pedestal", (x, -0.25, 0.37), 0.035, 0.72, material("Iron", (0.02, 0.02, 0.02), rough=0.4))
    mug(-0.15, -0.35, (0.85, 0.82, 0.75))
    sky_gradient("Sky", 45, 60, 40, PR["sky_top"], PR["sky_bottom"], E("sky", 1.0))
    lant = em("Lantern", (1.0, 0.55, 0.18), "lanterns", 8.0)
    win = em("ShopWin", (1.0, 0.6, 0.25), "windows", 2.5)
    plaster = [textured(material(f"Plaster{k}", c, rough=0.85), "concrete", 0.5) for k, c in
               enumerate(((0.35, 0.22, 0.12), (0.28, 0.25, 0.2), (0.4, 0.3, 0.18)))]
    lpts = []
    for side in (-1, 1):
        for k in range(8):
            y, h = 2 + k * 3.2, rng.uniform(5, 9)
            box(f"House{side}{k}", (side * 3.4, y, h / 2), (2.0, 3.1, h), COLL, plaster[(k + side) % 3])
            box(f"Roof{side}{k}", (side * 3.2, y, h + 0.3), (2.4, 3.2, 0.25), COLL,
                material("RoofTile", (0.2, 0.06, 0.03), rough=0.7))
            for z in (1.4, 3.6, 5.6):
                if z < h - 0.8 and rng.random() < 0.7:
                    box("Win", (side * 2.39, y + rng.uniform(-0.6, 0.6), z), (0.02, 0.6, 0.9), COLL, win)
            lpts.append((side * 2.2, y, 3.2))
    beads("Lanterns", lpts, 0.12, lant)
    for k in range(6):  # lantern strings across the street
        string_lights(f"Across{k}", (-2.35, 2 + k * 4, 4.2), (2.35, 3.5 + k * 4, 4.2), 0.6, 9, lant, r=0.07)


def subway():
    tile = textured(material("Tile", PR.get("tile", (0.6, 0.62, 0.6)), rough=0.25, coat=0.3), "tiles", 2.0, True)
    plat = textured(material("Platform", (0.15, 0.14, 0.13), rough=0.6), "concrete")
    box("Platform", (0, 0, -0.5), (14, 5, 1.0), COLL, plat)
    box("Edge", (0, 2.45, 0.005), (14, 0.25, 0.01), COLL, material("EdgeYellow", (0.8, 0.6, 0.02), rough=0.6))
    box("Track", (0, 3.6, -1.2), (14, 2.2, 0.1), COLL, material("Ballast", (0.04, 0.035, 0.03), rough=0.9))
    box("FarWall", (0, 4.9, 1.2), (14, 0.2, 4.4), COLL, tile)
    box("Band", (0, 4.78, 2.0), (14, 0.05, 0.35), COLL, material("Band", PR["band"], rough=0.4))
    for i, x in enumerate((-3.5, 0.5, 4.5)):
        box(f"Ad{i}", (x, 4.77, 1.0), (2.0, 0.03, 1.2), COLL,
            em(f"Ad{i}", [(0.9, 0.5, 0.2), (0.2, 0.6, 0.9), (0.9, 0.2, 0.4)][i], "ads", 2.0))
    for x in (-2.5, 2.5):
        box(f"Pillar{x}", (x, 1.2, 1.5), (0.45, 0.45, 3.0), COLL, tile)
    box("Ceiling", (0, 2, 3.1), (14, 7, 0.1), COLL, material("Ceiling", (0.05, 0.05, 0.05), rough=0.8))
    tube = em("Tube", PR["tube"], "tubes", 6.0)
    for k in range(-3, 4):
        if PRESET == "late_night" and k % 2:
            continue
        box(f"Tube{k}", (k * 2.0, 1.5, 3.0), (1.2, 0.06, 0.04), COLL, tube)
    desk(material("Steel", (0.4, 0.42, 0.45), rough=0.3, metal=0.8), top_z=0.74, w=2.4, d=0.4)
    box("Sign", (0, 0.9, 2.6), (1.6, 0.06, 0.3), COLL, em("SignPanel", (0.9, 0.9, 0.95), "sign", 3.0))


def classroom():
    wall = material("Wall", (0.5, 0.48, 0.42), rough=0.85)
    box("Floor", (0, 0, -0.01), (12, 12, 0.02), COLL, material("Lino", (0.25, 0.2, 0.15), rough=0.4))
    box("BackWall", (0, 2.6, 1.6), (8, 0.12, 3.2), COLL, wall)
    box("Board", (0, 2.52, 1.6), (3.2, 0.04, 1.2), COLL, material("Chalkboard", (0.03, 0.08, 0.05), rough=0.8))
    box("Tray", (0, 2.45, 0.98), (3.2, 0.1, 0.03), COLL, material("Tray", (0.3, 0.3, 0.3), rough=0.5))
    chalk = material("Chalk", (0.8, 0.8, 0.75), rough=0.9)
    for k in range(5):
        box(f"Scribble{k}", (-1.1 + k * 0.4, 2.49, 1.9 - 0.2 * (k % 3)), (0.3, 0.005, 0.02), COLL, chalk)
    wall_side = box("SideWall", (2.8, 0.5, 1.6), (0.12, 6, 3.2), COLL, wall)
    wall_side.hide_render = True  # windows are on the right: light only, the wall is implied
    sky_gradient("Outside", 6, 30, 10, PR["sky_top"], PR["sky_bottom"], E("sky", 1.0))
    wood = textured(material("DeskWood", (0.35, 0.22, 0.1), rough=0.5), "wood")
    legs = material("Legs", (0.1, 0.1, 0.1), rough=0.4, metal=0.6)
    desk(wood, w=2.3, d=0.55, legs=legs)  # a shared bench desk: room for Mark_B
    for k, (x, y) in enumerate(((-1.6, 1.2), (1.6, 1.2), (-1.6, -1.6), (1.7, -1.6))):
        box(f"OtherDesk{k}", (x, y, 0.74), (1.1, 0.55, 0.04), COLL, wood)
        box(f"OtherLegs{k}", (x, y, 0.37), (1.0, 0.45, 0.72), COLL, legs).display_type = "WIRE"
    box("Clock", (1.9, 2.53, 2.6), (0.35, 0.03, 0.35), COLL, material("Clock", (0.9, 0.9, 0.88), rough=0.5))
    box("Book", (-0.3, -0.35, 0.77), (0.22, 0.3, 0.025), COLL, material("Book", (0.6, 0.1, 0.08), rough=0.6))
    if PRESET == "after_hours":
        box("Exit", (-2.5, 2.52, 2.6), (0.4, 0.03, 0.15), COLL, em("Exit", (0.1, 1.0, 0.3), "exit", 6.0))
        lamp_shade("DeskLamp", (0.45, -0.15, 1.0), (1.0, 0.75, 0.4), "lamp", 0.08)


def office():
    box("Floor", (0, 0, -0.01), (12, 12, 0.02), COLL, textured(material("Concrete", (0.18, 0.18, 0.18), rough=0.35), "concrete"))
    glass = material("Glass", (0.6, 0.7, 0.75), rough=0.05)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
    wall_with_window(3.0, -3.5, 3.5, 0.0, 3.0, material("Wall", (0.3, 0.3, 0.3), rough=0.8),
                     width=12, mull=material("Frame", (0.05, 0.05, 0.05), rough=0.4))
    wm = [em("WinWarm", (1.0, 0.7, 0.4), "windows", 2.5), em("WinCool", (0.6, 0.75, 1.0), "windows", 2.5)]
    skyline(15, 70, 45, wm, material("Building", PR.get("building", (0.05, 0.06, 0.08)), rough=0.6),
            xspan=40, hmax=40, density=PR.get("win_density", 0.35))
    sky_gradient("Sky", 100, 300, 120, PR["sky_top"], PR["sky_bottom"], E("sky", 1.0))
    white = material("DeskWhite", (0.7, 0.7, 0.68), rough=0.35)
    desk(white, legs=material("Legs", (0.05, 0.05, 0.05), rough=0.4))
    lap = material("Laptop", (0.3, 0.3, 0.32), rough=0.3, metal=0.7)
    box("LaptopBase", (0.35, -0.38, 0.77), (0.34, 0.24, 0.015), COLL, lap)
    lid = box("LaptopLid", (0.35, -0.27, 0.88), (0.34, 0.01, 0.22), COLL, lap)
    lid.rotation_euler = (math.radians(-12), 0, 0)
    scr = box("Screen", (0.35, -0.278, 0.88), (0.32, 0.002, 0.2), COLL, screen_material("ScreenMat", PR["screen"], 1.4))
    scr.rotation_euler = (math.radians(-12), 0, 0)
    mug(-0.45, -0.3, (0.9, 0.9, 0.88))
    box("Whiteboard", (-2.0, 2.0, 1.5), (1.4, 0.05, 0.9), COLL, material("WB", (0.85, 0.85, 0.85), rough=0.2))
    plant(1.8, 1.4, 0, 1.6)
    plant(-1.4, 2.4, 0, 1.2)
    for x in (-1.5, 0, 1.5):
        lamp_shade(f"Pendant{x}", (x, 0.9, 2.6), (1.0, 0.85, 0.7), "pendants", 0.14)


def night_mart():
    box("Floor", (0, 0, -0.01), (12, 12, 0.02), COLL,
        textured(material("Floor", (0.4, 0.4, 0.42), rough=0.15 if PRESET == "rain_outside" else 0.3), "tiles"))
    counter = material("Counter", (0.08, 0.15, 0.35), rough=0.4)
    box("Counter", (0, -0.28, 0.37), (2.0, 0.6, 0.74), COLL, counter)
    box("CounterTop", (0, -0.28, 0.75), (2.1, 0.65, 0.03), COLL, material("Top", (0.7, 0.7, 0.7), rough=0.3))
    box("Register", (0.6, -0.3, 0.85), (0.3, 0.25, 0.18), COLL, material("Register", (0.05, 0.05, 0.05), rough=0.4))
    box("RegScreen", (0.6, -0.43, 0.9), (0.22, 0.01, 0.1), COLL, screen_material("ScreenMat", PR["screen"], 1.4))
    shelf = material("Shelf", (0.7, 0.7, 0.7), rough=0.5)
    palette = [(0.8, 0.1, 0.1), (0.1, 0.4, 0.8), (0.9, 0.7, 0.1), (0.1, 0.6, 0.2), (0.8, 0.4, 0.05), (0.6, 0.1, 0.5)]
    for row, y in enumerate((1.4, 2.6)):
        for z in (0.3, 0.75, 1.2, 1.65):
            box(f"Shelf{row}{z}", (0, y, z), (5.0, 0.4, 0.03), COLL, shelf)
            by_color = [[] for _ in palette]
            x = -2.4
            while x < 2.4:
                w_ = rng.uniform(0.08, 0.16)
                h_ = rng.uniform(0.15, 0.32)
                by_color[rng.randrange(len(palette))].append(((x + w_ / 2, y - 0.05, z + h_ / 2 + 0.015),
                                                              (w_ * 0.9, 0.12, h_)))
                x += w_
            for k, cubes in enumerate(by_color):
                if cubes:
                    merged(f"Goods{row}{z}{k}", material(f"Pack{k}", palette[k], rough=0.35), cubes)
    box("Fridges", (2.9, 1.9, 1.0), (0.1, 2.5, 2.0), COLL, em("FridgeGlow", (0.85, 0.95, 1.0), "fridge", 2.5))
    box("Ceiling", (0, 1.5, 3.0), (12, 8, 0.1), COLL, material("Ceiling", (0.6, 0.6, 0.6), rough=0.8))
    tube = em("Tube", PR["tube"], "tubes", 6.0)
    for x in (-2, 0, 2):
        for y in (0.6, 2.0):
            box(f"Tube{x}{y}", (x, y, 2.93), (1.2, 0.08, 0.04), COLL, tube)
    neon = em("Neon", PR.get("neon", (1.0, 0.1, 0.4)), "neon", 10.0)
    for k, (x, z, w_, h_) in enumerate(((-1.6, 2.4, 0.6, 0.06), (-1.6, 2.1, 0.06, 0.6), (-1.3, 2.25, 0.06, 0.36),
                                        (-0.9, 2.25, 0.5, 0.06), (-0.9, 2.45, 0.06, 0.4))):
        box(f"NeonBar{k}", (x, 3.2, z), (w_, 0.04, h_), COLL, neon)
    box("BackWall", (0, 3.3, 1.5), (12, 0.1, 3), COLL, material("BackWall", (0.15, 0.15, 0.17), rough=0.8))
    if PRESET == "rain_outside":
        rain_sheet("Rain", 3.15, 5, 2.4, 0.3, 0.35)


def pier():
    plank = textured(material("Planks", (0.18, 0.11, 0.06), rough=0.6), "planks")
    box("Boardwalk", (0, 0, -0.05), (8, 6, 0.1), COLL, plank)
    rail = textured(material("Rail", (0.22, 0.14, 0.08), rough=0.5), "wood")
    desk(rail, top_z=0.74, w=3.0, d=0.5)  # wide rail-top ledge the arms can rest on
    for x in (-1.4, -0.7, 0.7, 1.4):
        box(f"Post{x}", (x, -0.45, 0.37), (0.08, 0.08, 0.74), COLL, rail)
    for side in (-1, 1):  # side railings receding along the pier: depth cues
        box(f"SideRail{side}", (side * 2.4, 4, 0.95), (0.06, 10, 0.06), COLL, rail)
        merged(f"SidePosts{side}", rail, [((side * 2.4, -1 + k * 1.2, 0.5), (0.07, 0.07, 1.0)) for k in range(9)])
    sea = material("Sea", PR["sea"], rough=0.35, coat=0.2)
    _nt = sea.node_tree
    _wv = _nt.nodes.new("ShaderNodeTexWave")
    _wv.inputs["Scale"].default_value, _wv.inputs["Distortion"].default_value = 0.6, 4.0
    _bp = _nt.nodes.new("ShaderNodeBump")
    _bp.inputs["Strength"].default_value = 0.4
    _nt.links.new(_wv.outputs["Fac"], _bp.inputs["Height"])
    _nt.links.new(_bp.outputs["Normal"], _nt.nodes["Principled BSDF"].inputs["Normal"])
    box("Sea", (0, 60, -1.0), (300, 120, 0.02), COLL, sea)
    sky_gradient("Sky", 120, 500, 160, PR["sky_top"], PR["sky_bottom"], E("sky", 1.0))
    if PR.get("sun_disc"):
        ellipsoid("SunDisc", (8, 110, 6), (6, 0.1, 6), COLL, material("SunDisc", PR["sun_disc"], emit=E("sun", 8.0)))
    # ferris wheel far off, bulbs on the rim and spokes
    wheel = em("WheelBulbs", PR.get("bulbs", (1.0, 0.6, 0.3)), "carnival", 4.0)
    cx, cy, cz, R = -5, 28, 6, 5
    rim = [(cx + R * math.cos(t * math.pi / 24), cy, cz + R * math.sin(t * math.pi / 24)) for t in range(48)]
    spokes = [(cx + R * k / 6 * math.cos(a * math.pi / 6), cy, cz + R * k / 6 * math.sin(a * math.pi / 6))
              for a in range(12) for k in range(1, 6)]
    beads("Wheel", rim + spokes, 0.25, wheel)
    struct = material("Struct", (0.05, 0.05, 0.06), rough=0.5)
    box("WheelLegs", (cx, cy, cz / 2), (0.4, 0.4, cz), COLL, struct)
    bulbs = em("PierBulbs", (1.0, 0.8, 0.5), "string", 5.0)
    for side in (-1, 1):
        for k in range(4):
            cyl(f"Lamppost{side}{k}", (side * 3.5, -1 + k * 3, 1.5), 0.04, 3.0, struct)
        string_lights(f"PierString{side}", (side * 3.5, -1, 2.9), (side * 3.5, 8, 2.9), 0.4, 30, bulbs)


def torus(name, loc, R, r, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    for c in o.users_collection:
        c.objects.unlink(o)
    COLL.objects.link(o)
    o.data.materials.append(mat)
    return o


def props():
    """Small story props per set; kept clear of Mark_A's hands (x ±0.2, y -0.3..-0.5) and Mark_B (x -0.9)."""
    dark = material("PropDark", (0.02, 0.02, 0.025), rough=0.4)
    if SET_ID == "bedroom":
        torus("Headphones", (0.95, -0.5, 0.8), 0.07, 0.012, dark, rot=(math.radians(70), 0, 0.3))
        ellipsoid("Controller", (0.38, -0.52, 0.775), (0.07, 0.04, 0.015), COLL, dark, segs=16)
    elif SET_ID == "rooftop":
        for x in (1.3, 1.9):
            box(f"Chair{x}", (x, 1.4, 0.45), (0.45, 0.45, 0.05), COLL, material("ChairMetal", (0.3, 0.05, 0.03), rough=0.5))
        box("Speaker", (-1.5, 1.2, 0.3), (0.3, 0.25, 0.6), COLL, dark)
        box("SpeakerLED", (-1.5, 1.07, 0.5), (0.2, 0.01, 0.02), COLL, em("SpeakerLED", (0.2, 0.6, 1.0), "string", 4.0))
    elif SET_ID == "cafe":
        box("MenuBoard", (1.6, 1.42, 1.95), (0.8, 0.03, 0.55), COLL, material("Chalk", (0.03, 0.05, 0.04), rough=0.9))
        cyl("SugarJar", (0.22, -0.12, 0.8), 0.03, 0.08, material("Glass", (0.8, 0.8, 0.8), rough=0.1, coat=0.6))
        ellipsoid("Croissant", (0.2, -0.42, 0.785), (0.06, 0.03, 0.02), COLL,
                  material("Pastry", (0.6, 0.32, 0.08), rough=0.5), segs=16).rotation_euler = (0, 0, 0.4)
    elif SET_ID == "lantern_street":
        flower = material("Flowers", (0.7, 0.05, 0.08), rough=0.6)
        pot = material("Terracotta", (0.35, 0.12, 0.05), rough=0.8)
        for side in (-1, 1):
            for k in range(4):
                cyl(f"Pot{side}{k}", (side * 2.25, 3 + k * 3.5, 0.15), 0.15, 0.3, pot)
                ellipsoid(f"Bloom{side}{k}", (side * 2.25, 3 + k * 3.5, 0.38), (0.18, 0.18, 0.12), COLL, flower, segs=12)
    elif SET_ID == "subway":
        box("RouteMap", (2.5, 0.96, 1.6), (0.4, 0.02, 0.6), COLL, material("MapBase", (0.85, 0.85, 0.8), rough=0.6))
        for k, c in enumerate(((0.8, 0.1, 0.1), (0.1, 0.4, 0.8), (0.1, 0.6, 0.2))):
            box(f"Route{k}", (2.5, 0.945, 1.45 + k * 0.12), (0.34, 0.005, 0.02), COLL, material(f"Route{k}", c, rough=0.5))
        cyl("Bin", (-2.0, 1.0, 0.4), 0.2, 0.8, material("BinGrey", (0.2, 0.2, 0.22), rough=0.5, metal=0.5))
    elif SET_ID == "classroom":
        cyl("PencilCup", (0.55, -0.15, 0.82), 0.035, 0.1, material("Cup", (0.2, 0.3, 0.6), rough=0.4))
        for k in range(3):
            cyl(f"Pencil{k}", (0.54 + 0.01 * k, -0.15, 0.89), 0.005, 0.16, material(f"Pencil{k}", (0.9, 0.7, 0.1), rough=0.5),
                rot=(0.15 * (k - 1), 0.1, 0))
        ellipsoid("Globe", (2.3, 2.3, 1.25), (0.18, 0.18, 0.18), COLL, material("Globe", (0.1, 0.3, 0.6), rough=0.3))
    elif SET_ID == "office":
        box("Notebook", (-0.42, -0.42, 0.765), (0.16, 0.22, 0.012), COLL, material("Notebook", (0.1, 0.1, 0.12), rough=0.6))
        cyl("Pen", (-0.3, -0.42, 0.768), 0.005, 0.14, dark, rot=(math.radians(90), 0, 0.3))
        box("Monitor2", (-1.1, 0.0, 1.05), (0.5, 0.03, 0.3), COLL, dark)
    elif SET_ID == "night_mart":
        palette = [(0.9, 0.2, 0.1), (0.1, 0.5, 0.9), (0.9, 0.8, 0.1)]
        for k, c in enumerate(palette):
            box(f"Candy{k}", (-0.5 + k * 0.1, -0.45, 0.8), (0.07, 0.04, 0.09), COLL, material(f"Candy{k}", c, rough=0.4))
        box("GumRack", (0.95, -0.2, 0.9), (0.3, 0.08, 0.25), COLL, material("Rack", (0.6, 0.6, 0.6), rough=0.4, metal=0.6))
    elif SET_ID == "pier":
        torus("Lifebuoy", (1.45, -0.5, 0.45), 0.16, 0.05, material("Buoy", (0.9, 0.25, 0.05), rough=0.5),
              rot=(math.radians(90), 0, 0))
        box("Bench", (1.6, 2.2, 0.45), (1.4, 0.4, 0.06), COLL, material("BenchWood", (0.2, 0.12, 0.06), rough=0.6))


BUILDERS = {f.__name__: f for f in (night_city, bedroom, rooftop, cafe, lantern_street, subway, classroom, office,
                                    night_mart, pier)}
BUILDERS[SET_ID]()
props()

# --- world, haze, grade -------------------------------------------------------------
sc.render.engine = EEVEE
sc.eevee.use_raytracing = True
sc.eevee.volumetric_end = 60.0
sc.render.use_motion_blur = True
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
BRIGHT = bool(PR.get("sun")) or PR.get("world_s", 0) >= 0.6
sc.view_settings.exposure = PR.get("exposure", -0.4) - (0.45 if BRIGHT else 0.1)  # keep blacks black
w = bpy.data.worlds.new("World")
w.use_nodes = True
nt = w.node_tree
nt.nodes["Background"].inputs["Color"].default_value = (*PR["world"], 1)
nt.nodes["Background"].inputs["Strength"].default_value = PR.get("world_s", 1.0)
vol = nt.nodes.new("ShaderNodeVolumeScatter")
vol.inputs["Density"].default_value = PR.get("haze", 0.004) * 0.55
vol.inputs["Color"].default_value = (*PR.get("haze_color", (0.75, 0.82, 1.0)), 1)
nt.links.new(vol.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
sc.world = w
sc["mood_tint"] = PR.get("tint", 0.35)

# --- light rig (names are the mood contract) ---------------------------------------
RIG = {"Key": ("AREA", (0.75, -0.75, 1.45), 0.6), "Rim": ("AREA", (-0.85, 0.75, 1.75), 1.0),
       "Fill": ("AREA", (-1.3, -1.5, 1.2), 2.0), "Glow": ("POINT", (0.45, -0.3, 0.9), 0.1)}
for name, (kind, loc, size) in RIG.items():
    color, energy = PR[name.lower()]
    ld = bpy.data.lights.new(name, kind)
    ld.color, ld.energy = color, energy
    if kind == "AREA":
        ld.size = size
    else:
        ld.shadow_soft_size = size
    o = bpy.data.objects.new(name, ld)
    o.location = PR.get(f"{name.lower()}_pos", loc)
    o["base_color"], o["base_energy"] = list(color), energy
    COLL.objects.link(o)
    look_at(o, HEAD)
    if name in ("Key", "Rim"):
        ld.volume_factor = 0.5
if PR.get("sun"):
    color, strength, elev, azim = PR["sun"]
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.color, sd.energy, sd.angle = color, strength, math.radians(2)
    so = bpy.data.objects.new("Sun", sd)
    so.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim))
    COLL.objects.link(so)
for name, pos, color, energy in PR.get("extra", ()):  # practical lights: lamps, neon spill, lanterns
    ld = bpy.data.lights.new(name, "POINT")
    ld.color, ld.energy, ld.shadow_soft_size = color, energy, 0.2
    o = bpy.data.objects.new(name, ld)
    o.location = pos
    COLL.objects.link(o)

empty("Mark_A", (0, 0.15, 0), COLL)
empty("Mark_B", MARK_B, COLL)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(f"saved {OUT}")
