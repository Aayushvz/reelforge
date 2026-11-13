"""The Shots-AV rooms: six desk two-hander stages, three dark and three light. Top of the file is pure data;
build(room_id) runs inside Blender and adds the room to the current scene.

Contract (same as blender/sets.py, so render_plan.py needs no special case): lights Key, Rim, Fill, Glow, each with
custom props base_color/base_energy; material ScreenMat with a "Code" node (moods recolour it); empties Mark_A (the
hero's chair, at the origin) and Mark_B (on the desk, to the hero's right and toward the viewer). The scene keeps
scene["mood_tint"] and scene["av_exposure"] (the shotsav look's exposure for this room).
Metres; the hero faces -Y (toward the camera side of the desk); +X is his left.
"""
from __future__ import annotations

import math
import random

try:
    import bpy
    from mathutils import Vector
except ImportError:  # read as a data table outside Blender
    bpy = None

DESK_Z = 0.74
MARK_B = (-0.30, -0.36, DESK_Z)
DESK = {"size": (1.6, 0.75, 0.04), "centre": (0.0, -0.52)}  # its near edge (to the hero) is at y = -0.145
NEUTRAL_WARM = (1.0, 0.85, 0.72)  # about 4300 K, lightly desaturated: keeps the jacket #7C3AED

ROOMS = {
    "av_studio_night": {
        "label": "Studio, night", "tone": "dark", "exposure": -0.95, "haze": 0.010, "tint": 0.3,
        "world": (0.006, 0.008, 0.02), "wall": "#151A2C", "floor": "#1A1716", "desk": "#3B2A21",
        "screen": (0.45, 0.65, 1.0),
        "key": (NEUTRAL_WARM, 50, (0.95, -0.95, 1.55), 0.45), "rim": ("#8B5CF6", 130, (-0.9, 0.85, 1.75), 0.6),
        "fill": ((0.45, 0.55, 1.0), 9, (-1.3, -1.4, 1.2), 2.0), "glow": ((1.0, 0.72, 0.42), 9, (0.72, -0.22, 1.2), 0.08),
        "look": "tall window onto an indigo night city: amber and soft-cyan bokeh, a few red tail-light dots"},
    "av_neon_den": {
        "label": "Neon den", "tone": "dark", "exposure": -0.75, "haze": 0.008, "tint": 0.3,
        "world": (0.004, 0.004, 0.01), "wall": "#191426", "floor": "#141218", "desk": "#2A2730",
        "screen": (0.6, 0.95, 1.0),
        "key": ((0.88, 0.95, 1.0), 46, (0.95, -0.95, 1.5), 0.45), "rim": ("#8B5CF6", 150, (-0.9, 0.8, 1.6), 0.8),
        "fill": ((0.25, 0.35, 0.9), 6, (-1.3, -1.4, 1.2), 2.0), "glow": ((0.3, 0.9, 1.0), 7, (-0.9, 1.6, 1.1), 0.3),
        "look": "windowless den: a shelf wall, violet and cyan LED strips, a plant, a poster grid; no magenta"},
    "av_late_office": {
        "label": "Late office", "tone": "dark", "exposure": -0.7, "haze": 0.012, "tint": 0.3,
        "world": (0.008, 0.01, 0.014), "wall": "#1C2024", "floor": "#202226", "desk": "#3A3836",
        "screen": (0.5, 0.75, 1.0),
        "key": ((1.0, 0.85, 0.70), 42, (0.85, -0.85, 1.5), 0.4), "rim": ((0.70, 0.80, 1.0), 90, (-0.6, 0.9, 2.2), 1.2),
        "fill": ((0.4, 0.5, 0.7), 8, (-1.3, -1.4, 1.2), 2.0), "glow": ((0.75, 1.0, 0.8), 6, (2.2, 6.0, 2.3), 0.3),
        "look": "empty open office at night: rows of sleeping monitors, one green exit sign as bokeh"},
    "av_studio_morning": {
        "label": "Studio, morning", "tone": "light", "exposure": -1.25, "haze": 0.002, "tint": 0.2,
        "world": (0.55, 0.62, 0.72), "wall": "#F4F2EE", "floor": "#C9B59A", "desk": "#D9BE98",
        "screen": (0.55, 0.7, 1.0),
        "key": ((1.0, 0.97, 0.93), 260, (-1.4, -0.9, 1.9), 2.2), "rim": ((1.0, 0.86, 0.70), 70, (0.9, 0.9, 1.8), 0.8),
        "fill": ((0.75, 0.85, 1.0), 60, (1.4, -1.5, 1.3), 2.5), "glow": ((1.0, 0.95, 0.85), 4, (0.72, -0.22, 1.2), 0.08),
        "look": "cream wall #F4F2EE, a big soft window, plants, a pale wood desk: the website's look in 3D"},
    "av_cafe_day": {
        "label": "Cafe, day", "tone": "light", "exposure": -0.25, "haze": 0.002, "tint": 0.2,
        "world": (0.6, 0.66, 0.75), "wall": "#E9E2D6", "floor": "#8C6E52", "desk": "#C8A47A",
        "screen": (0.55, 0.7, 1.0),
        "key": ((1.0, 0.96, 0.9), 300, (-1.5, -0.5, 1.6), 1.8), "rim": ((1.0, 0.92, 0.8), 90, (0.6, 1.6, 1.8), 1.5),
        "fill": ((1.0, 0.86, 0.7), 40, (0.0, -0.9, 0.55), 1.4), "glow": ((1.0, 0.9, 0.75), 4, (0.72, -0.22, 1.2), 0.08),
        "look": "window seat: the street outside as bright bokeh, light oak, a pastry plate"},
    "av_cyc_lilac": {
        "label": "Lilac cyc", "tone": "light", "exposure": -1.2, "haze": 0.0, "tint": 0.2,
        "world": (0.6, 0.58, 0.68), "wall": "#F4F2EE", "floor": "#F4F2EE", "desk": "#EDE7F7",
        "screen": (0.55, 0.65, 1.0), "cyc_top": "#DDD6FE",
        "key": ((1.0, 0.98, 0.96), 240, (0.2, -0.6, 3.0), 3.0), "rim": ("#A78BFA", 60, (0.0, 1.4, 1.6), 1.5),
        "fill": ((0.95, 0.94, 1.0), 70, (0.0, -1.4, 0.3), 3.0), "glow": ((0.75, 0.62, 1.0), 40, (0.0, 2.6, 0.8), 1.5),
        "look": "seamless sweep fading cream to lilac #DDD6FE, desk only: product-video clean"},
}


# ============================================================================================================
# Everything below runs inside Blender.
# ============================================================================================================
def build(room_id: str):
    """Add the room to the current scene in a collection SET_<room_id>; returns the collection."""
    from bl_common import EEVEE, code_screen_material, look_at

    from .geo import ball, empty, lin, mat, mesh, mix_hex, rbox, tube

    if room_id not in ROOMS:
        raise ValueError(f"unknown room {room_id!r}; known: {', '.join(ROOMS)}")
    R = ROOMS[room_id]
    rng = random.Random(room_id)
    sc = bpy.context.scene
    coll = bpy.data.collections.new(f"SET_{room_id}")
    sc.collection.children.link(coll)

    def emit(name, color, strength):
        return mat(name, color, rough=0.5, emit=strength)

    def disc(name, loc, r, m, face=(0, -1, 0)):
        """A flat emissive disc facing the camera side: far away, the lens turns it into a bokeh ball."""
        o = ball(name, (r, r * 0.08, r), coll, m, loc, segs=12)
        o.visible_shadow = False
        return o

    # --- light rig: the contract -------------------------------------------------------------------------------
    head = Vector((0, 0, 1.15))
    for name in ("Key", "Rim", "Fill", "Glow"):
        color, energy, pos, size = R[name.lower()]
        color = lin(color) if isinstance(color, str) else color
        kind = "POINT" if name == "Glow" else "AREA"
        ld = bpy.data.lights.new(name, kind)
        ld.color, ld.energy = color, energy
        if kind == "AREA":
            ld.size = size
        else:
            ld.shadow_soft_size = size
        o = bpy.data.objects.new(name, ld)
        o.location = pos
        o["base_color"], o["base_energy"] = list(color), energy
        coll.objects.link(o)
        look_at(o, head if name != "Fill" or R["tone"] == "dark" else head + Vector((0, 0, -0.3)))
        if name in ("Key", "Rim"):
            ld.volume_factor = 0.4
    bounce = bpy.data.lights.new("DeskBounce", "AREA")  # keeps the desk front out of the crush (8-12% luminance)
    bounce.size, bounce.color = 1.4, (1.0, 0.92, 0.85)
    bounce.energy = 8 if R["tone"] == "dark" else 25
    bo = bpy.data.objects.new("DeskBounce", bounce)
    bo.location = (0.0, -1.7, 0.35)
    coll.objects.link(bo)
    look_at(bo, Vector((0, -0.9, 0.66)))

    # --- floor, desk, chair -----------------------------------------------------------------------------------
    floor = rbox("Floor", (14, 14, 0.02), coll, mat("Floor", R["floor"], rough=0.6), 0.001, (0, 2.0, -0.01))
    floor.visible_shadow = False
    dw, dd, dt = DESK["size"]
    dx, dy = DESK["centre"]
    wood = mat("DeskTop", R["desk"], rough=0.42, coat=0.15)
    rbox("Desk", (dw, dd, dt), coll, wood, 0.008, (dx, dy, DESK_Z - dt / 2))
    leg_m = mat("DeskLeg", mix_hex(R["desk"], "#000000", 0.35), rough=0.5)
    for sx in (1, -1):
        for yy in (dy - dd / 2 + 0.06, dy + dd / 2 - 0.06):
            rbox(f"DeskLeg{sx}{yy:.1f}", (0.045, 0.045, DESK_Z - dt), coll, leg_m, 0.008,
                 (sx * (dw / 2 - 0.06), yy, (DESK_Z - dt) / 2))
    rbox("DeskApron", (dw - 0.12, 0.02, 0.07), coll, leg_m, 0.004, (dx, dy - dd / 2 + 0.04, DESK_Z - dt - 0.035))
    rbox("DeskPanel", (dw - 0.16, 0.018, 0.40), coll, leg_m, 0.004, (dx, dy - dd / 2 + 0.08, DESK_Z - dt - 0.20))
    seat_m = mat("Chair", "#24252B" if R["tone"] == "dark" else "#3A3B42", rough=0.7, sheen=0.3)
    rbox("ChairSeat", (0.46, 0.44, 0.07), coll, seat_m, 0.02, (0, 0.06, 0.48))
    rbox("ChairBack", (0.44, 0.06, 0.46), coll, seat_m, 0.025, (0, 0.27, 0.80))
    tube("ChairPost", [Vector((0, 0.06, 0.06)), Vector((0, 0.06, 0.44))], 0.022, coll, mat("ChairMetal", "#2F3036",
                                                                                           rough=0.3, metal=0.8), k=12)

    # --- desk props: monitor with a chat screen, keyboard, pen, sticky notes, mug, lamp ---------------------------
    scr = code_screen_material("ScreenMat", R["screen"], strength=2.2)
    br = scr.node_tree.nodes["Code"]  # staggered rounded rows: chat bubbles, alternating left and right
    br.inputs["Color1"].default_value = (*R["screen"], 1.0)
    br.inputs["Color2"].default_value = (0.95, 0.96, 1.0, 1.0)
    br.inputs["Mortar"].default_value = (0.015, 0.02, 0.035, 1.0)
    br.inputs["Scale"].default_value, br.inputs["Mortar Size"].default_value = 3.2, 0.06
    br.inputs["Brick Width"].default_value, br.inputs["Row Height"].default_value = 0.55, 0.16
    br.offset, br.offset_frequency, br.squash, br.squash_frequency = 0.62, 2, 0.65, 3
    tc = scr.node_tree.nodes.new("ShaderNodeTexCoord")
    mp = scr.node_tree.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    scr.node_tree.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    scr.node_tree.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    mon = empty("Monitor", (0.56, -0.40, DESK_Z), coll)
    mon.rotation_euler.z = math.radians(-25)  # turned toward the hero; its screen shows at screen-right in wides
    dark_plastic = mat("MonitorBody", "#17181C", rough=0.35, coat=0.3)
    rbox("MonFoot", (0.22, 0.16, 0.012), coll, dark_plastic, 0.004, (0, 0.02, 0.006), parent=mon)
    rbox("MonNeck", (0.04, 0.03, 0.22), coll, dark_plastic, 0.006, (0, 0.04, 0.12), parent=mon)
    rbox("MonBezel", (0.64, 0.028, 0.39), coll, dark_plastic, 0.008, (0, 0.03, 0.40), parent=mon)
    screen = rbox("MonScreen", (0.61, 0.002, 0.355), coll, scr, 0.0005, (0, 0.0145, 0.405), parent=mon)
    screen.visible_shadow = False
    kb = rbox("Keyboard", (0.42, 0.14, 0.018), coll, mat("Keyboard", "#1E1F24", rough=0.45), 0.004,
              (0.06, -0.42, DESK_Z + 0.009))
    kb.rotation_euler.x = math.radians(3)
    key_m = mat("Keys", "#2B2C33", rough=0.5)
    for r_ in range(4):
        for c_ in range(13):
            rbox(f"Key{r_}{c_}", (0.024, 0.024, 0.008), coll, key_m, 0.0025,
                 (0.06 - 0.18 + c_ * 0.03, -0.42 - 0.045 + r_ * 0.03, DESK_Z + 0.021))
    pen = tube("Pen", [Vector((-0.10, -0.68, DESK_Z + 0.006)), Vector((0.04, -0.70, DESK_Z + 0.006))], 0.005, coll,
               mat("Pen", "#C9CCD6", rough=0.25, metal=0.6), k=10)
    pen.name = "Pen"
    for i, (x, y, col, rot) in enumerate(((0.34, -0.66, "#F7D44C", 8), (0.44, -0.62, "#F6A04D", -11))):
        n = rbox(f"Sticky{i}", (0.075, 0.075, 0.003), coll, mat(f"Sticky{i}", col, rough=0.8), 0.001,
                 (x, y, DESK_Z + 0.0015))
        n.rotation_euler.z = math.radians(rot)
    mug_m = mat("Mug", "#F1EEE8" if R["tone"] == "dark" else "#7C3AED", rough=0.25, coat=0.6)
    tube("Mug", [Vector((0.30, -0.24, DESK_Z)), Vector((0.30, -0.24, DESK_Z + 0.095))], 0.038, coll, mug_m, k=24)
    tube("MugHandle", [Vector((0.338, -0.24, DESK_Z + 0.075)), Vector((0.365, -0.24, DESK_Z + 0.06)),
                       Vector((0.338, -0.24, DESK_Z + 0.025))], 0.006, coll, mug_m, k=8)
    lamp_m = mat("Lamp", "#1F2024" if R["tone"] == "dark" else "#E8E4DC", rough=0.35, metal=0.4)
    tube("LampArm", [Vector((0.78, -0.18, DESK_Z)), Vector((0.80, -0.16, DESK_Z + 0.42)),
                     Vector((0.70, -0.24, DESK_Z + 0.58))], 0.009, coll, lamp_m, k=10)
    shade = ball("LampShade", (0.07, 0.07, 0.05), coll, lamp_m, (0.68, -0.26, DESK_Z + 0.57), segs=20)
    shade.rotation_euler.x = math.radians(-20)
    ball("LampBulb", (0.025, 0.025, 0.015), coll, emit("LampBulb", "#FFD9A0", 12.0), (0.68, -0.26, DESK_Z + 0.535),
         segs=12)

    # --- the room behind --------------------------------------------------------------------------------------
    wall_m = mat("Wall", R["wall"], rough=0.85)
    Y = 2.2  # the back wall or window, 2.2 m behind the hero

    def wall_with_window(x0, x1, z0, z1, mullions=3):
        rbox("WallLeft", (x0 + 3, 0.12, 4.0), coll, wall_m, 0.004, ((x0 - 3) / 2, Y, 2.0))
        rbox("WallRight", (3 - x1, 0.12, 4.0), coll, wall_m, 0.004, ((3 + x1) / 2, Y, 2.0))
        rbox("WallLow", (x1 - x0, 0.12, z0), coll, wall_m, 0.004, ((x0 + x1) / 2, Y, z0 / 2))
        rbox("WallHigh", (x1 - x0, 0.12, 4.0 - z1), coll, wall_m, 0.004, ((x0 + x1) / 2, Y, (4.0 + z1) / 2))
        frame = mat("Mullion", "#0B0C10" if R["tone"] == "dark" else "#EDEAE4", rough=0.5)
        for i in range(mullions + 1):
            x = x0 + (x1 - x0) * i / mullions
            rbox(f"Mullion{i}", (0.05, 0.08, z1 - z0), coll, frame, 0.01, (x, Y - 0.02, (z0 + z1) / 2))
        rbox("Transom", (x1 - x0, 0.08, 0.05), coll, frame, 0.01, ((x0 + x1) / 2, Y - 0.02, z0 + (z1 - z0) * 0.72))
        rbox("Sill", (x1 - x0 + 0.1, 0.22, 0.04), coll, frame, 0.008, ((x0 + x1) / 2, Y - 0.09, z0))

    def bokeh_field(n, colors, dist, xs, zs, rads, strength):
        for i in range(n):
            d = rng.uniform(*dist)
            col = rng.choice(colors)
            disc(f"Far{i:03d}", (rng.uniform(*xs) * d / 30, Y + d, rng.uniform(*zs) * (0.6 + d / 60)),
                 rng.uniform(*rads), emit(f"FarM{i:03d}", col, strength * rng.uniform(0.6, 1.3)))

    if room_id == "av_studio_night":
        wall_with_window(-1.6, 1.6, 0.35, 2.9, mullions=4)
        rbox("Sky", (400, 1, 260), coll, emit("Sky", "#0B1236", 0.35), 0.0, (0, 160, 40)).visible_shadow = False
        bokeh_field(150, ["#FFB347", "#FFC56E", "#FFD08A", "#5EAAD5", "#8FC8E8"], (30, 120), (-26, 26), (-6, 24),
                    (0.3, 1.1), 14)
        bokeh_field(10, ["#DB5347"], (30, 70), (-18, 18), (-2.5, 1.0), (0.15, 0.3), 18)  # tail-lights, low down
        for i in range(5):  # dark tower silhouettes between the lights
            rbox(f"Tower{i}", (rng.uniform(6, 14), 4, rng.uniform(30, 70)), coll, mat("Tower", "#05070F", rough=0.9),
                 0.0, (rng.uniform(-40, 40), Y + rng.uniform(60, 110), 0))
    elif room_id == "av_neon_den":
        rbox("Wall", (8, 0.12, 4), coll, wall_m, 0.004, (0, Y, 2.0))
        shelf_m = mat("Shelf", "#2B2633", rough=0.6)
        strip_v = emit("LEDViolet", "#8B5CF6", 30.0)
        strip_c = emit("LEDCyan", "#5EE6F0", 24.0)
        for k, z in enumerate((1.05, 1.55)):
            rbox(f"Shelf{k}", (1.5, 0.28, 0.035), coll, shelf_m, 0.006, (-0.55, Y - 0.16, z))
            rbox(f"ShelfLED{k}", (1.45, 0.012, 0.008), coll, strip_v, 0.002, (-0.55, Y - 0.03, z - 0.022))
            for b in range(7):  # books and objects
                h = rng.uniform(0.12, 0.26)
                rbox(f"Book{k}{b}", (rng.uniform(0.03, 0.07), 0.18, h), coll,
                     mat(f"Book{k}{b}", rng.choice(["#3D3552", "#5A4B7C", "#2E4057", "#C9CCD6", "#7C3AED"]), rough=0.7),
                     0.004, (-1.2 + b * 0.19 + rng.uniform(-0.02, 0.02), Y - 0.16, z + 0.018 + h / 2))
        rbox("LEDCyanV", (0.02, 0.012, 2.2), coll, strip_c, 0.002, (0.45, Y - 0.07, 1.3))
        rbox("LEDCove", (5.0, 0.02, 0.02), coll, strip_v, 0.002, (0, Y - 0.07, 2.5))  # a violet cove line up high
        for k, (x, col) in enumerate(((-0.55, "#8B5CF6"), (0.45, "#5EE6F0"))):  # the strips light the wall
            ld = bpy.data.lights.new(f"Strip{k}", "AREA")
            ld.size, ld.color, ld.energy = 1.2, lin(col), 40
            so = bpy.data.objects.new(f"Strip{k}", ld)
            so.location = (x, Y - 0.35, 1.3)
            coll.objects.link(so)
            look_at(so, Vector((x, Y, 1.3)))
        for i in range(6):  # a poster grid
            px, pz = 0.95 + (i % 3) * 0.42, 1.05 + (i // 3) * 0.55
            rbox(f"Poster{i}", (0.36, 0.015, 0.46), coll, mat(f"PosterFrame{i}", "#0E0D12", rough=0.4), 0.004,
                 (px, Y - 0.08, pz))
            rbox(f"PosterArt{i}", (0.30, 0.01, 0.40), coll,
                 emit(f"PosterArt{i}", rng.choice(["#3B2A6B", "#1D4E6B", "#5B3FA0", "#24324F"]), 2.2), 0.002,
                 (px, Y - 0.09, pz))
        for k in range(9):  # a plant on the floor
            a = k * 2.4
            leaf = ball(f"Leaf{k}", (0.05, 0.015, 0.22), coll, mat("Leaf", "#1E3A2A", rough=0.5, sheen=0.3),
                        (-1.55 + 0.12 * math.cos(a), Y - 0.5 + 0.12 * math.sin(a), 0.9 + 0.1 * math.sin(k)), segs=12)
            leaf.rotation_euler = (0.35 * math.cos(a), 0.35 * math.sin(a), a)
        tube("Pot", [Vector((-1.55, Y - 0.5, 0.0)), Vector((-1.55, Y - 0.5, 0.55))], 0.16, coll,
             mat("Pot", "#2A2530", rough=0.6), k=20)
    elif room_id == "av_late_office":
        rbox("FarWallLow", (16, 0.2, 1.0), coll, wall_m, 0.0, (0, Y + 11, 0.5))  # a window band onto the city
        rbox("FarWallHigh", (16, 0.2, 1.4), coll, wall_m, 0.0, (0, Y + 11, 3.3))
        bokeh_field(60, ["#FFB347", "#FFD08A", "#8FC8E8", "#DCE6FF"], (30, 90), (-30, 30), (1.0, 6), (0.3, 0.9), 12)
        sleep_m = mat("SleepScreen", "#0A0C12", rough=0.25, coat=0.6, emit=0.0)
        saver = emit("ScreenSaver", "#20345E", 1.6)
        standby = emit("Standby", "#3E6AE0", 2.5)
        for row in range(4):
            yrow = Y + 1.0 + row * 2.4
            for col in range(6):
                x = -3.4 + col * 1.35 + (0.3 if row % 2 else 0)
                rbox(f"OffDesk{row}{col}", (1.2, 0.7, 0.04), coll, mat("OffDesk", "#2C2D30", rough=0.5), 0.006,
                     (x, yrow, 0.72))
                rbox(f"OffMon{row}{col}", (0.55, 0.03, 0.33), coll, saver if rng.random() < 0.35 else sleep_m, 0.006,
                     (x, yrow + 0.15, 1.03))
                if rng.random() < 0.5:
                    ball(f"StandbyDot{row}{col}", (0.008, 0.008, 0.008), coll, standby, (x + 0.24, yrow + 0.13, 0.875),
                         segs=8)
        for i in range(6):  # ceiling panels, mostly off; two still on far away
            on = i in (1, 2, 4, 5)
            rbox(f"Ceil{i}", (1.2, 0.6, 0.02), coll,
                 emit(f"Ceil{i}", "#DCE6FF", 6.0) if on else mat(f"CeilOff{i}", "#2A2D33", rough=0.6),
                 0.002, (-2.4 + (i % 3) * 2.4, Y + 2 + (i // 3) * 5, 2.9))
        rbox("Exit", (0.42, 0.03, 0.16), coll, emit("ExitSign", "#57F287", 30.0), 0.004, (1.4, Y + 10.7, 2.75))
        rbox("Ceiling", (16, 16, 0.05), coll, mat("Ceiling", "#15171B", rough=0.9), 0.0, (0, Y + 6, 3.0))
    elif room_id == "av_studio_morning":
        wall_with_window(-2.1, -0.15, 0.55, 2.7, mullions=2)
        rbox("SkyOut", (60, 1, 30), coll, emit("SkyOut", "#DCEBFF", 2.2), 0.0, (0, Y + 18, 5)).visible_shadow = False
        bokeh_field(14, ["#FFFFFF", "#E8F2FF", "#FFF4E0"], (20, 60), (-20, 6), (-1, 8), (0.6, 1.4), 2.6)
        for k in range(3):  # plants on the sill and the floor
            px = -1.8 + k * 0.7
            tube(f"SillPot{k}", [Vector((px, Y - 0.1, 0.57)), Vector((px, Y - 0.1, 0.70))], 0.06, coll,
                 mat("Terracotta", "#C9784E", rough=0.7), k=16)
            for j in range(6):
                a = j * 1.05 + k
                lf = ball(f"SillLeaf{k}{j}", (0.025, 0.008, 0.10), coll, mat("LeafLight", "#4F7A3A", rough=0.5, sheen=0.3),
                          (px + 0.04 * math.cos(a), Y - 0.1 + 0.04 * math.sin(a), 0.78), segs=10)
                lf.rotation_euler = (0.4 * math.cos(a), 0.4 * math.sin(a), a)
        rbox("Shelf", (0.9, 0.24, 0.03), coll, mat("ShelfOak", "#D9BE98", rough=0.5), 0.005, (1.1, Y - 0.13, 1.45))
        for b in range(5):
            rbox(f"ShelfBook{b}", (0.05, 0.16, 0.2 + 0.03 * (b % 2)), coll,
                 mat(f"ShelfBook{b}", ["#7C3AED", "#A78BFA", "#1F1F1F", "#DDD6FE", "#C9784E"][b], rough=0.7), 0.004,
                 (0.8 + b * 0.07, Y - 0.13, 1.57))
    elif room_id == "av_cafe_day":
        wall_with_window(-2.6, 2.6, 0.5, 2.8, mullions=3)
        rbox("SkyOut", (80, 1, 40), coll, emit("SkyOut", "#E6F0FF", 2.6), 0.0, (0, Y + 30, 8)).visible_shadow = False
        bokeh_field(22, ["#FFFFFF", "#FFF2DC", "#DDE8FF", "#FFE0C4"], (10, 40), (-26, 26), (-1.5, 4), (0.5, 1.6), 3.0)
        for i in range(6):  # storefronts across the street, daylit
            rbox(f"Store{i}", (rng.uniform(4, 7), 1, rng.uniform(4, 8)), coll,
                 emit(f"Store{i}", rng.choice(["#C9B6A0", "#9FB0C4", "#D8C3A5", "#B4A7C8"]), 1.6), 0.0,
                 (-15 + i * 6, Y + 14, 2.5))
        rbox("Street", (60, 12, 0.1), coll, emit("Street", "#9C968C", 1.0), 0.0, (0, Y + 7, 0.0))
        rbox("CafeWallLow", (6, 0.12, 0.5), coll, wall_m, 0.004, (0, Y, 0.25))
        plate = tube("Plate", [Vector((-0.55, -0.62, DESK_Z)), Vector((-0.55, -0.62, DESK_Z + 0.012))], 0.085, coll,
                     mat("Plate", "#F7F5F0", rough=0.3, coat=0.5), k=28)
        pastry = ball("Croissant", (0.06, 0.035, 0.028), coll, mat("Pastry", "#C98B4A", rough=0.6, sheen=0.2),
                      (-0.55, -0.62, DESK_Z + 0.04), segs=16)
        pastry.rotation_euler.z = 0.5
    elif room_id == "av_cyc_lilac":
        sweep = []  # a seamless cyclorama: floor curving up into the wall, fading cream to lilac
        for i in range(25):
            t = i / 24
            a = t * math.pi / 2
            y = Y - 1.2 + 1.2 * math.sin(a) if t < 1 else Y
            z = 1.2 - 1.2 * math.cos(a)
            sweep.append((y, z))
        sweep += [(Y, 1.2 + 0.4 * k) for k in range(1, 8)]
        verts, faces = [], []
        for i, (y, z) in enumerate(sweep):
            verts += [(-5, y, z), (5, y, z)]
            if i:
                faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
        cyc_m = mat("Cyc", R["wall"], rough=0.9)
        nt = cyc_m.node_tree
        tco = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.4, 3.2
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.inputs[6].default_value = (*lin(R["wall"]), 1)
        mx.inputs[7].default_value = (*lin(R["cyc_top"]), 1)
        nt.links.new(tco.outputs["Object"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], mx.inputs[0])
        nt.links.new(mx.outputs[2], nt.nodes["Principled BSDF"].inputs["Base Color"])
        cyc = mesh("Cyc", verts, faces, coll, cyc_m, smooth=True)
        cyc.location.y = 0.0

    # --- marks, world, haze, render defaults --------------------------------------------------------------------
    empty("Mark_A", (0, 0, 0), coll)
    empty("Mark_B", MARK_B, coll)
    w = bpy.data.worlds.new(f"World_{room_id}")
    w.use_nodes = True
    wn = w.node_tree
    wn.nodes["Background"].inputs["Color"].default_value = (*R["world"], 1)
    wn.nodes["Background"].inputs["Strength"].default_value = 1.0
    if R["haze"]:
        vol = wn.nodes.new("ShaderNodeVolumeScatter")
        vol.inputs["Density"].default_value = R["haze"]
        vol.inputs["Color"].default_value = (0.8, 0.84, 1.0, 1)
        wn.links.new(vol.outputs["Volume"], wn.nodes["World Output"].inputs["Volume"])
    sc.world = w
    sc["mood_tint"] = R["tint"]
    sc["av_exposure"] = R["exposure"]
    sc["av_room"] = room_id
    sc.render.engine = EEVEE
    sc.eevee.use_raytracing = True
    sc.eevee.volumetric_end = 40.0
    if hasattr(sc.eevee, "shadow_ray_count"):
        sc.eevee.shadow_ray_count, sc.eevee.shadow_step_count = 4, 12
    sc.view_settings.view_transform, sc.view_settings.look = "Khronos PBR Neutral", "None"
    sc.view_settings.exposure = R["exposure"]
    return coll
