"""Places: where in the room the hero sits, swapped in at render time (no room rebuild).

Every room is built around the desk: the hero's chair at the origin, the desk top at DESK_Z = 0.74, the buddy on
Mark_B (on the desk, to his right). A place keeps that geometry - the seat top at the chair's height and a work
surface at DESK_Z under the keyboard and the buddy - so the hero's seated pose, his typing, the buddy and every
camera angle carry over. What changes is everything the camera reads as "where": the desk, chair and monitor go;
a sofa, a bed or a window bench, a laptop (the room's own ScreenMat on its lid, so moods still recolour it) and the
furniture around them come in.

    sofa    a deep sofa with cushions and a throw, a C-table over his lap holding the laptop, a floor lamp
    bed     sitting on the edge of a made bed (duvet, pillows, headboard), a rolling laptop cart, a nightstand
    window  a cushioned window bench, a floating ledge desk, a big window frame with sheer curtains behind him
"""
import math

import bpy
from mathutils import Vector

PLACES = ("desk", "sofa", "bed", "window")
SEAT_TOP = 0.515  # the desk chair's seat top: the hero's hips rest here in every place
DESK_Z = 0.74
# the desk's own pieces (removed for any other place); props on the desk top that would float go too
DESK_PARTS = ("Desk", "DeskLeg", "DeskApron", "DeskPanel", "ChairSeat", "ChairBack", "ChairPost", "MonFoot", "MonNeck",
              "MonBezel", "MonScreen", "Pen", "Sticky", "LampArm", "LampShade", "LampBulb")


def _drop_desk():
    for o in list(bpy.data.objects):
        base = o.name.split(".")[0]
        if base == "DeskBounce":  # a light, not furniture
            continue
        if base in DESK_PARTS or base.startswith(("DeskLeg", "Sticky")):
            bpy.data.objects.remove(o, do_unlink=True)


def _palette(room):
    dark = room.get("tone") == "dark"
    return {"fabric": "#5E3B2E" if dark else "#CFC6B8", "cushion": "#6E4636" if dark else "#E6DED2",
            "accent": "#7C3AED", "wood": room.get("desk", "#3B2A21"), "metal": "#1E1F24" if dark else "#BDBDC2",
            "linen": "#B9B4CC" if dark else "#F1ECE4", "throw": "#5B4A8A" if dark else "#B9A6E3"}


def _laptop(coll, g, screen_mat):
    """A laptop under the room's keyboard: base, keys area, and a lid facing the hero with the room's ScreenMat."""
    body = g.mat("LaptopBody", "#2A2B31", rough=0.3, metal=0.6)
    # 13-inch scale next to the stylised hero, lid leaned well back: it must stay under his chin from low angles
    g.rbox("LaptopBase", (0.44, 0.28, 0.014), coll, body, 0.005, (0.06, -0.43, DESK_Z + 0.007))
    lid = g.empty("LaptopHinge", (0.06, -0.57, DESK_Z + 0.014), coll)
    lid.rotation_euler.x = math.radians(-32)  # leaned back, away from the hero
    g.rbox("LaptopLid", (0.42, 0.010, 0.21), coll, body, 0.005, (0, 0, 0.105), parent=lid)
    if screen_mat is not None:
        s = g.rbox("LaptopScreen", (0.38, 0.002, 0.18), coll, screen_mat, 0.0005, (0, 0.0062, 0.108), parent=lid)
        s.visible_shadow = False


def _sofa(coll, g, P):
    fab, cush = g.mat("SofaFabric", P["fabric"], rough=0.85, sheen=0.4), g.mat("SofaCushion", P["cushion"], rough=0.9, sheen=0.5)
    g.rbox("SofaBase", (2.2, 0.95, 0.30), coll, fab, 0.05, (0.0, 0.25, 0.20))
    for k, x in enumerate((-0.52, 0.52)):
        g.rbox(f"SofaSeat{k}", (1.0, 0.82, 0.14), coll, cush, 0.06, (x, 0.18, SEAT_TOP - 0.07))
        g.rbox(f"SofaBackCushion{k}", (1.0, 0.24, 0.50), coll, cush, 0.08, (x, 0.60, 0.80))
    g.rbox("SofaBack", (2.2, 0.22, 0.62), coll, fab, 0.06, (0.0, 0.70, 0.66))
    for k, x in enumerate((-1.18, 1.18)):
        g.rbox(f"SofaArm{k}", (0.22, 0.95, 0.62), coll, fab, 0.07, (x, 0.25, 0.36))
    pil = g.mat("SofaPillow", P["accent"], rough=0.8, sheen=0.5)
    p = g.rbox("SofaPillow0", (0.42, 0.14, 0.40), coll, pil, 0.08, (-0.85, 0.48, 0.74))
    p.rotation_euler = (math.radians(-12), 0, math.radians(14))
    g.rbox("SofaThrow", (0.60, 0.70, 0.03), coll, g.mat("SofaThrow", P["throw"], rough=0.95, sheen=0.6), 0.015,
           (0.92, 0.25, SEAT_TOP + 0.015))
    # the C-table: its foot slides under the sofa, its top reaches over his lap
    met, wood = g.mat("CTableMetal", P["metal"], rough=0.3, metal=0.8), g.mat("CTableTop", P["wood"], rough=0.42, coat=0.15)
    g.rbox("CTableTop", (1.05, 0.46, 0.03), coll, wood, 0.008, (-0.10, -0.44, DESK_Z - 0.015))
    g.tube("CTablePost", [Vector((0.40, -0.60, 0.02)), Vector((0.40, -0.60, DESK_Z - 0.03))], 0.018, coll, met, k=12)
    g.rbox("CTableFoot", (0.10, 0.70, 0.02), coll, met, 0.004, (0.40, -0.35, 0.01))
    # a floor lamp at the sofa's end: a warm practical in the wides
    g.tube("FloorLampPole", [Vector((-1.45, 0.55, 0.0)), Vector((-1.45, 0.55, 1.55))], 0.014, coll, met, k=10)
    g.ball("FloorLampShade", (0.18, 0.18, 0.14), coll, g.mat("FloorLampShade", "#F3E7D3", rough=0.6, emit=1.5),
           (-1.45, 0.55, 1.60), segs=20)


def _bed(coll, g, P):
    linen, duvet = g.mat("BedLinen", P["linen"], rough=0.9, sheen=0.5), g.mat("BedDuvet", P["throw"], rough=0.95, sheen=0.6)
    wood = g.mat("BedFrame", P["wood"], rough=0.5)
    g.rbox("BedFrame", (1.70, 2.10, 0.26), coll, wood, 0.02, (0.0, 1.08, 0.17))
    g.rbox("BedMattress", (1.62, 2.02, 0.20), coll, linen, 0.05, (0.0, 1.08, SEAT_TOP - 0.10))
    g.rbox("BedDuvet", (1.66, 1.30, 0.06), coll, duvet, 0.03, (0.0, 1.40, SEAT_TOP + 0.02))
    g.rbox("BedHeadboard", (1.78, 0.08, 0.95), coll, wood, 0.02, (0.0, 2.16, 0.62))
    for k, x in enumerate((-0.42, 0.42)):
        g.rbox(f"BedPillow{k}", (0.62, 0.36, 0.14), coll, linen, 0.06, (x, 1.90, SEAT_TOP + 0.10))
    g.rbox("BedPillowAccent", (0.40, 0.14, 0.34), coll, g.mat("BedPillowAccent", P["accent"], rough=0.8, sheen=0.5),
           0.07, (0.0, 1.70, SEAT_TOP + 0.20))
    # a rolling laptop cart: top over his knees, one post, a wheeled base
    met, wood2 = g.mat("CartMetal", P["metal"], rough=0.3, metal=0.8), g.mat("CartTop", P["wood"], rough=0.42, coat=0.15)
    g.rbox("CartTop", (1.05, 0.46, 0.03), coll, wood2, 0.008, (-0.10, -0.44, DESK_Z - 0.015))
    for k, x in enumerate((-0.55, 0.35)):
        g.tube(f"CartPost{k}", [Vector((x, -0.44, 0.05)), Vector((x, -0.44, DESK_Z - 0.03))], 0.016, coll, met, k=12)
        g.rbox(f"CartFoot{k}", (0.06, 0.50, 0.02), coll, met, 0.004, (x, -0.44, 0.04))
    g.rbox("Nightstand", (0.48, 0.42, 0.55), coll, wood, 0.015, (1.15, 0.25, 0.275))
    g.ball("NightLamp", (0.11, 0.11, 0.13), coll, g.mat("NightLamp", "#F6E2C2", rough=0.6, emit=2.0), (1.15, 0.25, 0.70),
           segs=18)


def _window(coll, g, P):
    cush, fab = g.mat("BenchCushion", P["cushion"], rough=0.9, sheen=0.5), g.mat("BenchBox", P["wood"], rough=0.5)
    g.rbox("WindowBench", (1.9, 0.62, 0.42), coll, fab, 0.02, (0.0, 0.20, 0.21))
    g.rbox("WindowBenchCushion", (1.84, 0.58, 0.09), coll, cush, 0.04, (0.0, 0.20, SEAT_TOP - 0.045))
    for k, x in enumerate((-0.78, 0.78)):
        p = g.rbox(f"WindowPillow{k}", (0.40, 0.16, 0.36), coll, g.mat(f"WindowPillow{k}", P["accent"] if k else P["throw"],
                                                                         rough=0.8, sheen=0.5), 0.07, (x, 0.40, 0.72))
        p.rotation_euler.z = math.radians(10 if k else -10)
    g.rbox("LedgeDesk", (1.05, 0.46, 0.035), coll, g.mat("LedgeDesk", P["wood"], rough=0.42, coat=0.15), 0.008,
           (-0.10, -0.44, DESK_Z - 0.0175))
    for k, x in enumerate((-0.50, 0.30)):
        g.rbox(f"LedgeBracket{k}", (0.03, 0.30, 0.18), coll, g.mat("LedgeBracket", P["metal"], rough=0.3, metal=0.8),
               0.004, (x, -0.40, DESK_Z - 0.12))
    # the window behind him: frame and mullions only, so the room's own backdrop reads as the view outside
    frame_m = g.mat("WindowFrame", "#E8E4DC" if P["fabric"] != "#5E3B2E" else "#2A2B33", rough=0.4)
    y = 0.62
    g.rbox("WindowSill", (2.2, 0.26, 0.05), coll, frame_m, 0.01, (0.0, y, 0.70))
    for k, x in enumerate((-1.05, -0.35, 0.35, 1.05)):
        g.rbox(f"WindowMullion{k}", (0.05, 0.06, 1.55), coll, frame_m, 0.005, (x, y + 0.08, 1.48))
    g.rbox("WindowHead", (2.2, 0.08, 0.07), coll, frame_m, 0.005, (0.0, y + 0.08, 2.28))
    g.rbox("WindowTransom", (2.2, 0.06, 0.04), coll, frame_m, 0.005, (0.0, y + 0.08, 1.62))
    sheer = g.mat("WindowSheer", "#F2EEF8", rough=0.9, sheen=0.4)
    sheer.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.45  # a sheer: the room glows through
    for k, x in enumerate((-1.25, 1.25)):
        g.rbox(f"WindowCurtain{k}", (0.32, 0.05, 2.2), coll, sheer, 0.02, (x, y + 0.02, 1.15))


BUILD = {"sofa": _sofa, "bed": _bed, "window": _window}


def apply(place: str, room: dict) -> bool:
    """Swap the desk for `place` in the loaded room. Returns False (and does nothing) for the desk."""
    if place not in BUILD:
        return False
    from shotsav import geo as g
    screen = bpy.data.materials.get("ScreenMat")
    _drop_desk()
    coll = bpy.data.collections.new(f"PLACE_{place}")
    bpy.context.scene.collection.children.link(coll)
    BUILD[place](coll, g, _palette(room))
    _laptop(coll, g, screen)
    return True
