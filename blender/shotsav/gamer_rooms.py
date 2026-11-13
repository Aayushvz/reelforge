"""Six dark gamer/editor rooms for Shots-AV, modelled in 3D in Blender. They are our own sets, inspired by the
owner's reference boards (a purple-city editing den, a streamer corner, a neon shelf room, a moonlit window, a
retro bedroom, a lived-in studio apartment) and not copies of them. No images are used as backdrops.

rooms.build() calls backdrop(room_id, ...) for the room behind the desk; everything made here hangs off the room's
pivot, so the editor's "frame to keep" can slide the room behind the hero without touching the desk or lights.
Layout: the back wall's face is at y = Y - 0.06, the hero sits at the origin facing -Y, and +X is image right.
At the default framing the wide shot sees about x -0.9..0.9 on the wall; the pan reaches about x -2.4..2.4.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

from bl_common import look_at

from .geo import ball, lin, mat, mesh, rbox, tube

Y = 2.2
WALL = Y - 0.06  # the wall's face
X0, X1 = -3.8, 3.8  # wall extent: the pan never runs off it


class Kit:
    """Small modelling kit with cached materials, so a room is a short list of calls."""

    def __init__(self, coll, rng):
        self.coll, self.rng, self._m, self.n = coll, rng, {}, 0

    def nm(self, base):
        self.n += 1
        return f"{base}.{self.n:03d}"

    def m(self, color, rough=0.6, **kw):
        key = (color, rough, tuple(sorted(kw.items())))
        if key not in self._m:
            self._m[key] = mat(f"M_{color}_{len(self._m)}", color, rough=rough, **kw)
        return self._m[key]

    def e(self, color, strength):
        return self.m(color, 0.5, emit=strength)

    def box(self, base, size, m, loc, bevel=0.004, rot=None):
        o = rbox(self.nm(base), size, self.coll, m if not isinstance(m, str) else self.m(m), bevel, loc)
        if rot:
            o.rotation_euler = rot
        return o

    def glow(self, base, size, color, strength, loc, rot=None):
        o = self.box(base, size, self.e(color, strength), loc, 0.001, rot)
        o.visible_shadow = False
        return o

    def area(self, base, color, energy, loc, target, size=1.0):
        ld = bpy.data.lights.new(self.nm(base), "AREA")
        ld.size, ld.color, ld.energy = size, lin(color), energy
        o = bpy.data.objects.new(ld.name, ld)
        o.location = loc
        self.coll.objects.link(o)
        look_at(o, Vector(target))
        return o

    def point(self, base, color, energy, loc, radius=0.1):
        ld = bpy.data.lights.new(self.nm(base), "POINT")
        ld.color, ld.energy, ld.shadow_soft_size = lin(color), energy, radius
        o = bpy.data.objects.new(ld.name, ld)
        o.location = loc
        self.coll.objects.link(o)
        return o

    def wash(self, color, energy, x, z, size=1.4):
        """An accent light that washes the wall: the colour a strip or a sign throws around itself."""
        return self.area("Wash", color, energy, (x, WALL - 0.45, z), (x, Y, z), size)

    # --- architecture ------------------------------------------------------------------------------------------
    def wall(self, color, window=None, frame="#0B0C10", mullions=3, top=3.0):
        """The back wall, with an optional window (x0, x1, z0, z1) cut into it; also a ceiling."""
        wm = self.m(color, 0.85)
        if not window:
            self.box("Wall", (X1 - X0, 0.12, top), wm, ((X0 + X1) / 2, Y, top / 2))
        else:
            x0, x1, z0, z1 = window
            self.box("Wall", (x0 - X0, 0.12, top), wm, ((X0 + x0) / 2, Y, top / 2))
            self.box("Wall", (X1 - x1, 0.12, top), wm, ((x1 + X1) / 2, Y, top / 2))
            self.box("Wall", (x1 - x0, 0.12, z0), wm, ((x0 + x1) / 2, Y, z0 / 2))
            self.box("Wall", (x1 - x0, 0.12, top - z1), wm, ((x0 + x1) / 2, Y, (top + z1) / 2))
            fm = self.m(frame, 0.45)
            for i in range(mullions + 1):
                self.box("Mullion", (0.045, 0.07, z1 - z0), fm, (x0 + (x1 - x0) * i / mullions, Y - 0.02, (z0 + z1) / 2))
            self.box("Sill", (x1 - x0 + 0.12, 0.24, 0.035), fm, ((x0 + x1) / 2, Y - 0.1, z0))
            self.box("Head", (x1 - x0 + 0.06, 0.08, 0.05), fm, ((x0 + x1) / 2, Y - 0.02, z1))
        self.box("Ceiling", (X1 - X0, 4.2, 0.05), self.m(color, 0.9), ((X0 + X1) / 2, Y - 2.0, top + 0.025))
        self.box("Skirting", (X1 - X0, 0.02, 0.08), self.m(color, 0.5), ((X0 + X1) / 2, WALL - 0.01, 0.04))

    def sky(self, top, low, strength=0.6, dist=70):
        """A night sky: a far plane fading from the horizon colour up to the top colour."""
        m = self.m(top, 0.5, emit=strength)
        nt = m.node_tree
        tco, sep = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ")
        mr, mx = nt.nodes.new("ShaderNodeMapRange"), nt.nodes.new("ShaderNodeMix")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -0.35, 0.25
        mx.data_type = "RGBA"
        mx.inputs[6].default_value, mx.inputs[7].default_value = (*lin(low), 1), (*lin(top), 1)
        nt.links.new(tco.outputs["Object"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], mx.inputs[0])
        b = nt.nodes["Principled BSDF"]
        nt.links.new(mx.outputs[2], b.inputs["Emission Color"])
        nt.links.new(mx.outputs[2], b.inputs["Base Color"])
        s = self.box("Sky", (500, 1, 200), m, (0, Y + dist, 20), 0.0)
        s.visible_shadow = False

    def tower_mat(self, lit, strength=3.0):
        """Tower faces with a grid of windows, some lit, most dark (a brick texture read as windows)."""
        key = ("tower", lit, strength)
        if key in self._m:
            return self._m[key]
        m = bpy.data.materials.new(f"Tower_{lit}")
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.006, 0.007, 0.012, 1)
        b.inputs["Roughness"].default_value = 0.8
        br = nt.nodes.new("ShaderNodeTexBrick")
        br.inputs["Color1"].default_value = (*lin(lit), 1)
        br.inputs["Color2"].default_value = (*(v * 0.06 for v in lin(lit)), 1)
        br.inputs["Mortar"].default_value = (0.002, 0.002, 0.004, 1)
        br.inputs["Bias"].default_value = 0.0  # each window a random mix of lit and dim
        br.inputs["Scale"].default_value, br.inputs["Mortar Size"].default_value = 1.5, 0.16
        br.inputs["Brick Width"].default_value, br.inputs["Row Height"].default_value = 0.5, 0.42
        br.offset = 0.0
        tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
        nt.links.new(br.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = strength * 1.8  # through the haze, windows need the punch of bokeh
        self._m[key] = m
        return m

    def city(self, lits, n=12, near=38, far=88, spread=50, strength=3.0):
        r = self.rng
        for i in range(n):
            d = r.uniform(near, far)
            w, h = r.uniform(4, 9), r.uniform(8, 26) * (0.6 + d / far)
            self.box("Tower", (w, w * 0.8, h), self.tower_mat(r.choice(lits), strength),
                     (r.uniform(-spread, spread), Y + d, h / 2 - 6), 0.0)

    def bokeh(self, n, colors, dist, xs, zs, rads, strength):
        r = self.rng
        for i in range(n):
            d = r.uniform(*dist)
            rad = r.uniform(*rads)
            o = ball(self.nm("Far"), (rad, rad * 0.08, rad), self.coll,
                     self.e(r.choice(colors), round(strength * r.uniform(0.6, 1.3), 1)),
                     (r.uniform(*xs) * d / 30, Y + d, r.uniform(*zs) * (0.6 + d / 60)), segs=12)
            o.visible_shadow = False

    def stars(self, n, dist=(80, 120)):
        r = self.rng
        for i in range(n):
            d = r.uniform(*dist)
            o = ball(self.nm("Star"), (0.08,) * 3, self.coll, self.e("#DCE6FF", round(r.uniform(4, 12))),
                     (r.uniform(-60, 60), Y + d, r.uniform(4, 45)), segs=6)
            o.visible_shadow = False

    def blinds(self, x0, x1, z0, z1, tilt=35, color="#1E2130"):
        m = self.m(color, 0.45, metal=0.2)
        z = z1 - 0.03
        while z > z0:
            self.box("Slat", (x1 - x0, 0.05, 0.004), m, ((x0 + x1) / 2, Y - 0.1, z), 0.001,
                     (math.radians(tilt), 0, 0))
            z -= 0.042
        self.box("BlindRail", (x1 - x0 + 0.04, 0.06, 0.04), m, ((x0 + x1) / 2, Y - 0.1, z1 + 0.01))

    def rain(self, x0, x1, z0, z1, n=140):
        r, m = self.rng, self.m("#9FB6D8", 0.05, coat=1.0)
        for i in range(n):
            s = r.uniform(0.6, 1.4)
            o = ball(self.nm("Drop"), (0.004 * s, 0.002, 0.007 * s * r.choice((1, 1, 2.5))), self.coll, m,
                     (r.uniform(x0, x1), Y - 0.035, r.uniform(z0, z1)), segs=6)
            o.visible_shadow = False

    def curtain(self, x0, x1, z0, z1, color, y=None, folds=0.9):
        y = WALL - 0.1 if y is None else y
        nx = max(8, int((x1 - x0) / 0.025))
        verts, faces = [], []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            dy = 0.035 * math.sin(i * folds) + 0.012 * math.sin(i * 2.3)
            verts += [(x, y + dy, z0), (x, y + dy, z1)]
            if i:
                faces.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
        mesh(self.nm("Curtain"), verts, faces, self.coll, self.m(color, 0.85, sheen=0.6), smooth=True)
        self.box("CurtainRod", (x1 - x0 + 0.1, 0.02, 0.02), self.m("#2A2A30", 0.3, metal=0.8),
                 ((x0 + x1) / 2, y, z1 + 0.03))

    # --- light pieces ------------------------------------------------------------------------------------------
    def neon(self, pts, color, strength=28, r=0.008):
        o = tube(self.nm("Neon"), [Vector(p) for p in pts], r, self.coll, self.e(color, strength), k=10)
        o.visible_shadow = False
        return o

    def neon_text(self, text, loc, size, color, strength=26, plate="#0C0D12"):
        cu = bpy.data.curves.new(self.nm("Sign"), "FONT")
        cu.body, cu.size, cu.align_x, cu.align_y = text, size, "CENTER", "CENTER"
        cu.extrude, cu.bevel_depth, cu.bevel_resolution = 0.004, 0.003, 2
        o = bpy.data.objects.new(cu.name, cu)
        o.data.materials.append(self.e(color, strength))
        o.location, o.rotation_euler = loc, (math.radians(90), 0, 0)
        o.visible_shadow = False
        self.coll.objects.link(o)
        w = size * 0.62 * len(text) + 0.12
        self.box("SignPlate", (w, 0.012, size * 1.35), self.m(plate, 0.25, coat=0.8), (loc[0], loc[1] + 0.02, loc[2]))
        return o

    def fairy(self, x0, x1, z, sag, swags=3, color="#FFC873", y=None):
        y = WALL - 0.12 if y is None else y
        wire, bulb = self.m("#202020", 0.5), self.e(color, 30)
        n = 22 * swags
        pts = []
        for i in range(n + 1):
            t = i / n
            u = (t * swags) % 1.0
            pts.append(Vector((x0 + (x1 - x0) * t, y, z - sag * 4 * u * (1 - u))))
        tube(self.nm("FairyWire"), pts, 0.0015, self.coll, wire, k=6)
        for p in pts[1:-1:2]:
            o = ball(self.nm("Fairy"), (0.011, 0.011, 0.013), self.coll, bulb, p - Vector((0, 0, 0.012)), segs=8)
            o.visible_shadow = False

    def hexes(self, cx, cz, cells, colors, r=0.13, strength=16):
        """Wall hexagon light panels: a dark frame and a glowing face per cell, honeycomb spacing."""
        frame = self.m("#14151B", 0.4)
        for k, (q, s) in enumerate(cells):
            x = cx + r * 1.78 * (q + 0.5 * (s % 2))
            z = cz + r * 1.55 * s
            for rr, m, y in ((r, frame, WALL - 0.01), (r * 0.86, self.e(colors[k % len(colors)], strength), WALL - 0.02)):
                verts = [(x + rr * math.cos(math.radians(30 + 60 * i)), y, z + rr * math.sin(math.radians(30 + 60 * i)))
                         for i in range(6)]
                o = mesh(self.nm("Hex"), verts, [(0, 1, 2, 3, 4, 5)], self.coll, m)
                o.visible_shadow = False

    def ring_light(self, x, z, r=0.27):
        steel = self.m("#1A1B20", 0.3, metal=0.7)
        pts = [Vector((x + r * math.cos(a), WALL - 0.55, z + r * math.sin(a)))
               for a in (2 * math.pi * i / 48 for i in range(48))]
        o = tube(self.nm("Ring"), pts, 0.022, self.coll, self.e("#F5F7FF", 9), k=12, closed=True)
        o.visible_shadow = False
        tube(self.nm("RingBack"), [p + Vector((0, 0.025, 0)) for p in pts], 0.026, self.coll, steel, k=10, closed=True)
        tube(self.nm("RingPole"), [Vector((x, WALL - 0.53, 0)), Vector((x, WALL - 0.53, z - r))], 0.012, self.coll, steel)
        for a in (0, 2.1, 4.2):
            tube(self.nm("RingLeg"), [Vector((x, WALL - 0.53, 0.35)),
                                      Vector((x + 0.28 * math.cos(a), WALL - 0.53 + 0.28 * math.sin(a), 0.0))],
                 0.008, self.coll, steel)
        self.area("RingGlow", "#F5F7FF", 28, (x, WALL - 0.6, z), (x, -1.0, z), 0.4)

    def pc_tower(self, x, z, y=None, fans=("#FF4FA3", "#22D3EE", "#A78BFA")):
        y = WALL - 0.3 if y is None else y
        case = self.m("#0E0F14", 0.3, coat=0.6)
        self.box("PCCase", (0.22, 0.46, 0.48), case, (x, y, z + 0.24), 0.01)
        self.box("PCGlass", (0.2, 0.004, 0.44), self.m("#10121A", 0.05, coat=1.0), (x, y - 0.232, z + 0.24), 0.002)
        for i, col in enumerate(fans):
            fz = z + 0.09 + i * 0.14
            pts = [Vector((x + 0.055 * math.cos(a), y - 0.215, fz + 0.055 * math.sin(a)))
                   for a in (2 * math.pi * k / 28 for k in range(28))]
            o = tube(self.nm("Fan"), pts, 0.006, self.coll, self.e(col, 22), k=8, closed=True)
            o.visible_shadow = False
            ball(self.nm("Hub"), (0.016, 0.004, 0.016), self.coll, case, (x, y - 0.214, fz), segs=10)
        self.glow("PCStrip", (0.004, 0.004, 0.44), fans[0], 18, (x - 0.1, y - 0.234, z + 0.24))
        self.point("PCGlow", fans[1], 6, (x, y - 0.3, z + 0.25), 0.15)

    # --- props -------------------------------------------------------------------------------------------------
    def plant(self, x, z, s=1.0, y=None, leaf="#2F5A3A", pot="#2A2530", n=9):
        y = WALL - 0.16 if y is None else y
        tube(self.nm("Pot"), [Vector((x, y, z)), Vector((x, y, z + 0.13 * s))], [0.055 * s, 0.07 * s], self.coll,
             self.m(pot, 0.6), k=18)
        lm = self.m(leaf, 0.5, sheen=0.3)
        for k in range(n):
            a = k * 2.4
            o = ball(self.nm("Leaf"), (0.022 * s, 0.006 * s, 0.085 * s), self.coll, lm,
                     (x + 0.05 * s * math.cos(a), y + 0.05 * s * math.sin(a), z + (0.2 + 0.05 * math.sin(k)) * s), segs=10)
            o.rotation_euler = (0.55 * math.cos(a), 0.55 * math.sin(a), a)

    def tall_plant(self, x, y, s=1.0, leaf="#2E5B34"):
        tube(self.nm("BigPot"), [Vector((x, y, 0)), Vector((x, y, 0.38 * s))], [0.15 * s, 0.17 * s], self.coll,
             self.m("#3A3634", 0.7), k=22)
        stem, lm = self.m("#4A3B2A", 0.7), self.m(leaf, 0.45, sheen=0.3)
        r = self.rng
        for k in range(14):
            a, h = k * 2.4, (0.7 + 0.08 * k) * s
            tip = Vector((x + 0.22 * s * math.cos(a), y + 0.16 * s * math.sin(a), h))
            tube(self.nm("Stem"), [Vector((x, y, 0.36 * s)), tip], 0.006 * s, self.coll, stem, k=6)
            o = ball(self.nm("BigLeaf"), (0.09 * s, 0.012 * s, 0.13 * s), self.coll, lm, tip + Vector((0, 0, 0.08 * s)),
                     segs=12)
            o.rotation_euler = (r.uniform(-0.4, 0.4), r.uniform(-0.5, 0.5), a)

    def shelf(self, x0, x1, z, items, depth=0.24, color="#1E1B26", led=None):
        """A floating shelf with props. items: a string of codes, one per slot: b book, B tall book, f figure,
        p plant, x box, c console, h headphones, '.' gap."""
        y = WALL - depth / 2
        self.box("Shelf", (x1 - x0, depth, 0.03), self.m(color, 0.55), ((x0 + x1) / 2, y, z))
        if led:
            self.glow("ShelfLED", (x1 - x0 - 0.04, 0.008, 0.006), led, 26, ((x0 + x1) / 2, y - depth / 2 + 0.01, z - 0.02))
        r = self.rng
        step = (x1 - x0) / max(1, len(items))
        top = z + 0.015
        books = ["#2E2A44", "#4B3F72", "#1F3B57", "#C9CCD6", "#8A2F5C", "#24324F", "#E3B54A"]
        for i, code in enumerate(items):
            x = x0 + step * (i + 0.5)
            if code in "bB":
                for k in range(r.randint(3, 5)):
                    h = r.uniform(0.15, 0.24) * (1.25 if code == "B" else 1.0)
                    self.box("Book", (0.03, 0.16, h), self.m(r.choice(books), 0.7), (x - 0.06 + k * 0.034, y, top + h / 2))
            elif code == "f":
                self.figure(x, top, y, r.choice(["#FF4FA3", "#22D3EE", "#F5F5F5", "#FFB347", "#A78BFA"]))
            elif code == "p":
                self.plant(x, top, 0.8, y)
            elif code == "x":
                h = r.uniform(0.08, 0.16)
                self.box("Box", (0.14, 0.14, h), self.m(r.choice(["#2B2F3A", "#3A2F45", "#ECE6DA"]), 0.6), (x, y, top + h / 2))
            elif code == "c":
                self.box("Console", (0.2, 0.15, 0.05), self.m("#ECECEC", 0.3), (x, y, top + 0.025), 0.01)
                self.glow("ConsoleLED", (0.03, 0.004, 0.004), "#22D3EE", 20, (x + 0.06, y - 0.076, top + 0.03))
            elif code == "h":
                self.headphones(x, top + 0.11, y, stand=True)

    def figure(self, x, z, y, color):
        """A small vinyl toy: a big head, a little body, two dot eyes."""
        m, eye = self.m(color, 0.35, coat=0.6), self.m("#101010", 0.2)
        ball(self.nm("ToyBody"), (0.028, 0.024, 0.032), self.coll, m, (x, y, z + 0.032), segs=14)
        ball(self.nm("ToyHead"), (0.04, 0.036, 0.036), self.coll, m, (x, y, z + 0.095), segs=16)
        for s in (-1, 1):
            ball(self.nm("ToyEye"), (0.006, 0.004, 0.008), self.coll, eye, (x + s * 0.014, y - 0.035, z + 0.097), segs=8)
            ball(self.nm("ToyEar"), (0.012, 0.01, 0.016), self.coll, m, (x + s * 0.03, y, z + 0.13), segs=10)

    def headphones(self, x, z, y, stand=False, color="#1B1C22"):
        m = self.m(color, 0.4, sheen=0.3)
        arc = [Vector((x + 0.075 * math.cos(a), y, z + 0.075 * math.sin(a))) for a in
               (math.pi * i / 16 for i in range(17))]
        tube(self.nm("Band"), arc, 0.008, self.coll, m, k=8)
        for s in (-1, 1):
            o = ball(self.nm("Cup"), (0.022, 0.036, 0.042), self.coll, m, (x + s * 0.078, y, z - 0.02), segs=14)
            self.glow("CupRing", (0.004, 0.026, 0.004), "#A78BFA", 12, (x + s * 0.1, y, z - 0.02))
        if stand:
            tube(self.nm("HPStand"), [Vector((x, y, z - 0.11)), Vector((x, y, z + 0.07))], 0.006, self.coll,
                 self.m("#2A2B30", 0.3, metal=0.7))

    def speaker(self, x, z, h=0.32, y=None, color="#17181D"):
        y = WALL - 0.2 if y is None else y
        w = h * 0.62
        self.box("Speaker", (w, 0.2, h), self.m(color, 0.5), (x, y, z + h / 2), 0.008)
        cone = self.m("#0A0A0C", 0.7)
        for zz, rr in ((z + h * 0.33, w * 0.36), (z + h * 0.76, w * 0.15)):
            tube(self.nm("Cone"), [Vector((x, y - 0.1, zz)), Vector((x, y - 0.106, zz))], rr, self.coll, cone, k=20)

    def poster(self, x, z, w, h, colors, y=None):
        y = WALL - 0.015 if y is None else y
        self.box("Frame", (w, 0.02, h), self.m("#0D0E12", 0.4), (x, y, z))
        self.glow("PosterBG", (w - 0.04, 0.004, h - 0.04), colors[0], 1.2, (x, y - 0.012, z))
        r = self.rng
        for k, c in enumerate(colors[1:]):  # a simple abstract print: a sun and two bands
            if k == 0:
                o = ball(self.nm("PosterSun"), (w * 0.2, 0.002, w * 0.2), self.coll, self.e(c, 2.0),
                         (x + r.uniform(-0.05, 0.05) * w, y - 0.016, z + h * 0.12), segs=16)
                o.visible_shadow = False
            else:
                self.glow("PosterBand", (w - 0.06, 0.003, h * 0.09), c, 1.6, (x, y - 0.017, z - h * (0.08 + 0.12 * k)))

    def timeline_screen(self, x, z, w=1.0, h=0.58):
        """A wall monitor showing a video editor: a preview window, a dark UI and coloured clips on tracks."""
        self.box("TVBezel", (w + 0.04, 0.05, h + 0.04), self.m("#0B0B0E", 0.35, coat=0.5), (x, WALL - 0.04, z), 0.01)
        self.glow("TVUI", (w, 0.004, h), "#161824", 1.2, (x, WALL - 0.068, z))
        self.glow("TVPreview", (w * 0.42, 0.003, h * 0.4), "#3B2F6B", 2.2, (x - w * 0.12, WALL - 0.071, z + h * 0.24))
        self.glow("TVPreviewSun", (w * 0.1, 0.002, h * 0.12), "#FF9F6E", 3.0, (x - w * 0.08, WALL - 0.073, z + h * 0.22))
        r = self.rng
        clips = ["#6D5BD0", "#2BB5C9", "#E0569B", "#E8A33D", "#4FB37A"]
        for row in range(4):
            zz = z - h * 0.08 - row * h * 0.1
            xx = x - w * 0.46
            while xx < x + w * 0.42:
                cw = r.uniform(0.06, 0.2) * w
                self.glow("Clip", (cw - 0.006, 0.003, h * 0.07), clips[(row + int(xx * 7)) % 5], 2.6,
                          (xx + cw / 2, WALL - 0.071, zz))
                xx += cw + r.uniform(0.0, 0.03)
        self.glow("Playhead", (0.004, 0.002, h * 0.5), "#FFFFFF", 5, (x + w * 0.08, WALL - 0.074, z - h * 0.2))
        self.point("TVSpill", "#7A73FF", 5, (x, WALL - 0.4, z), 0.3)

    def credenza(self, x0, x1, h=0.6, color="#1B1A20", led=None):
        self.box("Credenza", (x1 - x0, 0.42, h), self.m(color, 0.5), ((x0 + x1) / 2, WALL - 0.21, h / 2), 0.008)
        if led:
            self.glow("UnderLED", (x1 - x0 - 0.06, 0.006, 0.006), led, 24, ((x0 + x1) / 2, WALL - 0.43, 0.06))
        return h

    def cat(self, x, z, y, color="#0D0D11", turn=180):
        """A cat sitting with its back to us: body, head, ears, a curled tail. A silhouette against the moon."""
        m = self.m(color, 0.8, sheen=0.5)
        rot = math.radians(turn)
        def at(dx, dy, dz):  # noqa: E306
            c, s = math.cos(rot), math.sin(rot)
            return (x + dx * c - dy * s, y + dx * s + dy * c, z + dz)
        ball(self.nm("CatBody"), (0.085, 0.075, 0.12), self.coll, m, at(0, 0, 0.11), segs=18)
        ball(self.nm("CatHaunch"), (0.1, 0.09, 0.06), self.coll, m, at(0, 0.01, 0.05), segs=16)
        ball(self.nm("CatHead"), (0.06, 0.055, 0.052), self.coll, m, at(0, -0.035, 0.26), segs=16)
        for s in (-1, 1):
            tube(self.nm("CatEar"), [Vector(at(s * 0.032, -0.035, 0.29)), Vector(at(s * 0.042, -0.04, 0.34))],
                 [0.02, 0.002], self.coll, m, k=8)
        tail = [Vector(at(0.05 * math.sin(t * 2.4), 0.08 + 0.05 * t, 0.015 + 0.02 * t)) for t in
                (i / 8 for i in range(9))]
        tube(self.nm("CatTail"), tail, [0.017] * 8 + [0.008], self.coll, m, k=8)

    def lava_lamp(self, x, z, y=None, color="#FF5E8A"):
        y = WALL - 0.12 if y is None else y
        metal = self.m("#B8BCC8", 0.25, metal=0.9)
        tube(self.nm("LavaBase"), [Vector((x, y, z)), Vector((x, y, z + 0.12))], [0.06, 0.035], self.coll, metal, k=18)
        glass = self.m("#FF8FA8", 0.1, emit=1.2)
        tube(self.nm("LavaGlass"), [Vector((x, y, z + 0.12)), Vector((x, y, z + 0.26)), Vector((x, y, z + 0.34))],
             [0.035, 0.045, 0.022], self.coll, glass, k=18)
        for k, (dz, rr) in enumerate(((0.16, 0.022), (0.23, 0.016), (0.29, 0.012))):
            o = ball(self.nm("Blob"), (rr, rr, rr * 1.3), self.coll, self.e("#FFB04A", 8), (x, y - 0.012, z + dz), segs=10)
            o.visible_shadow = False
        tube(self.nm("LavaCap"), [Vector((x, y, z + 0.34)), Vector((x, y, z + 0.39))], [0.022, 0.01], self.coll, metal,
             k=14)
        self.point("LavaGlow", color, 3, (x, y - 0.1, z + 0.25), 0.05)

    def moon(self, cam, aim, dist=40, r=2.1):
        """The moon, placed along the line from a wide camera through a point in the window, `dist` m out."""
        d = (Vector(aim) - Vector(cam)).normalized()
        p = Vector(cam) + d * dist
        o = ball("Moon", (r, r * 0.3, r), self.coll, self.e("#F4EED8", 7), p, segs=32)
        o.visible_shadow = False
        halo = ball("MoonHalo", (r * 2.2, 0.1, r * 2.2), self.coll, self.e("#3A4C8C", 0.35), p + Vector((0, 3, 0)), segs=24)
        halo.visible_shadow = False
        r_ = self.rng
        for i in range(9):
            c = p + Vector((r_.uniform(-9, 9), r_.uniform(1.5, 5), r_.uniform(-5, 1.5)))  # behind the moon
            near = max(0.0, 1 - (c - p).length / 9)
            o = ball(self.nm("Cloud"), (r_.uniform(2.5, 5), 0.6, r_.uniform(0.5, 1.0)), self.coll,
                     self.e(r_.choice(["#26345E", "#2E3D6B", "#3A4A7A"]), round(0.4 + 1.2 * near, 2)), c, segs=16)
            o.visible_shadow = False
        return p

    def crt(self, x, z, y=None):
        y = WALL - 0.32 if y is None else y
        body = self.m("#B9B2A3", 0.5)
        self.box("CRT", (0.52, 0.46, 0.44), body, (x, y, z + 0.22), 0.04)
        self.box("CRTBezel", (0.46, 0.02, 0.36), self.m("#2A2A2E", 0.4), (x, y - 0.235, z + 0.23), 0.02)
        scr = ball("CRTScreen", (0.2, 0.02, 0.155), self.coll, self.e("#4CC3FF", 3.5), (x, y - 0.245, z + 0.23), segs=20)
        scr.visible_shadow = False
        self.glow("CRTLED", (0.012, 0.004, 0.012), "#FF3B3B", 20, (x + 0.2, y - 0.232, z + 0.04))
        self.point("CRTSpill", "#4CC3FF", 8, (x, y - 0.5, z + 0.25), 0.2)

    def bed(self, x0, x1, y0, y1):
        """A bed in the corner, headboard against the back wall: base, mattress, a rumpled duvet and pillows."""
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.box("BedBase", (x1 - x0, y1 - y0, 0.28), self.m("#1F1D24", 0.6), (cx, cy, 0.14), 0.01)
        self.box("Headboard", (x1 - x0, 0.08, 0.9), self.m("#2A2638", 0.7, sheen=0.4), (cx, y1 - 0.04, 0.45), 0.03)
        self.box("Mattress", (x1 - x0 - 0.04, y1 - y0 - 0.1, 0.2), self.m("#D8D6E6", 0.8), (cx, cy - 0.03, 0.38), 0.04)
        self.box("Duvet", (x1 - x0 + 0.04, (y1 - y0) * 0.7, 0.1), self.m("#3B4170", 0.85, sheen=0.6),
                 (cx, y0 + (y1 - y0) * 0.35, 0.52), 0.05)
        for s in (-1, 1):
            o = ball(self.nm("Pillow"), (0.28, 0.14, 0.07), self.coll, self.m("#C9CCE8", 0.85, sheen=0.5),
                     (cx + s * (x1 - x0) * 0.24, y1 - 0.25, 0.55), segs=16)
            o.rotation_euler.x = math.radians(-25)

    def sofa(self, x0, x1, color="#2E3346"):
        m = self.m(color, 0.8, sheen=0.6)
        cx, y = (x0 + x1) / 2, WALL - 0.45
        self.box("SofaBase", (x1 - x0, 0.85, 0.42), m, (cx, y, 0.21), 0.05)
        self.box("SofaBack", (x1 - x0, 0.22, 0.42), m, (cx, WALL - 0.13, 0.62), 0.07)
        for s in (-1, 1):
            self.box("SofaArm", (0.18, 0.85, 0.24), m, (cx + s * ((x1 - x0) / 2 - 0.09), y, 0.54), 0.06)
        for k, c in enumerate(("#C9784E", "#DDD6FE")):
            o = ball(self.nm("Cushion"), (0.18, 0.08, 0.16), self.coll, self.m(c, 0.85, sheen=0.5),
                     (cx + (k - 0.5) * (x1 - x0) * 0.5, WALL - 0.28, 0.6), segs=14)
            o.rotation_euler.x = math.radians(-15)

    def floor_lamp(self, x, y, h=1.55, color="#FFB873"):
        steel = self.m("#1C1C20", 0.3, metal=0.8)
        tube(self.nm("LampBase"), [Vector((x, y, 0)), Vector((x, y, 0.02))], 0.14, self.coll, steel, k=20)
        tube(self.nm("LampPole"), [Vector((x, y, 0)), Vector((x, y, h))], 0.01, self.coll, steel)
        tube(self.nm("LampShade"), [Vector((x, y, h - 0.06)), Vector((x, y, h + 0.2))], [0.2, 0.14], self.coll,
             self.m("#EADBC4", 0.8, emit=1.4), k=24)
        self.point("LampWarm", color, 45, (x, y, h + 0.05), 0.12)


# ============================================================================================================
# The six rooms. Each draws only the room behind the desk; rooms.build() adds the desk, the light rig and marks.
# ============================================================================================================
WIDE_CAM = (0.55, -2.0, 1.45)  # roughly where the wide camera sits: the moon is aimed from here


def editor_night(k):
    """Editor's den at night: a wide window onto a violet-and-cyan city, blinds half down, a wall monitor with an
    edit timeline, a credenza with a glowing PC and speakers, a pink strip under the sill."""
    win = (-1.8, 1.0, 0.85, 2.7)
    k.wall("#141626", win, mullions=3)
    k.sky("#0A0A22", "#3A1748", 0.7)
    k.city(["#FFC56E", "#7DD3FC", "#FF7AC6", "#B9A4FF"], n=16, strength=2.6)
    k.bokeh(70, ["#FFB347", "#7DD3FC", "#FF7AC6", "#FFD08A"], (25, 90), (-26, 26), (-4, 14), (0.3, 0.9), 12)
    k.blinds(win[0], win[1], 2.25, win[3])
    k.glow("SillLED", (win[1] - win[0], 0.008, 0.008), "#FF4FA3", 22, ((win[0] + win[1]) / 2, Y - 0.2, win[2] - 0.03))
    k.wash("#FF4FA3", 30, -0.6, 0.5, 2.5)
    k.timeline_screen(1.85, 1.62, 0.9, 0.52)
    k.credenza(1.15, 3.0, 0.6, led="#7DD3FC")
    k.pc_tower(2.7, 0.6, y=WALL - 0.24)
    k.speaker(1.35, 0.6, 0.3)
    k.plant(2.25, 0.6, 1.0)
    k.tall_plant(-2.55, WALL - 0.35)
    k.wash("#7DD3FC", 18, 1.9, 1.2, 1.6)


def streamer_den(k):
    """Streamer corner: acoustic foam behind the chair, hexagon light panels, a ring light on a stand, a rainy
    window onto a blue city, a little figure shelf."""
    win = (-3.1, -1.95, 0.9, 2.55)
    k.wall("#111318", win, mullions=1)
    k.sky("#070B1C", "#13284A", 0.6)
    k.city(["#7DD3FC", "#DCE6FF", "#FFC56E"], n=10, spread=30, strength=2.2)
    k.bokeh(40, ["#7DD3FC", "#DCE6FF", "#FFB347"], (20, 70), (-30, -6), (-3, 10), (0.3, 0.9), 10)
    k.rain(win[0], win[1], win[2], win[3])
    foam = k.m("#1A1C24", 0.95)
    for i in range(6):  # 6 x 5 tiles of wedge foam, alternating direction
        for j in range(5):
            x, z = -0.75 + i * 0.3, 1.0 + j * 0.3
            for w in range(4):
                if (i + j) % 2:
                    k.box("Foam", (0.07, 0.045, 0.27), foam, (x - 0.105 + w * 0.07, WALL - 0.03, z), 0.012)
                else:
                    k.box("Foam", (0.27, 0.045, 0.07), foam, (x, WALL - 0.03, z - 0.105 + w * 0.07), 0.012)
    k.hexes(-1.45, 1.75, [(0, 0), (1, 0), (-1, 0), (0, 1), (-1, 1), (0, -1), (-1, -1)], ["#22D3EE", "#F472B6"])
    k.wash("#22D3EE", 22, -1.4, 1.8, 1.0)
    k.shelf(-1.75, -1.0, 1.2, "fpf")
    k.ring_light(1.45, 1.55)
    k.shelf(2.0, 2.9, 1.5, "xbf", led="#F472B6")
    k.speaker(2.1, 0.0, 0.9, y=WALL - 0.2)
    k.wash("#F472B6", 18, 2.4, 1.2, 1.2)


def neon_shelf(k):
    """Neon shelf room: a long shelf wall with pink strips under each shelf, figures and plants, a vertical neon
    tube, a glass-sided RGB PC and headphones on a cabinet, two prints."""
    k.wall("#15121D")
    for z, items in ((1.0, "bfpxbcf"), (1.45, "fbpfbxb"), (1.9, "pbfxfbp")):
        k.shelf(-2.6, -0.55, z, items, led="#FF4FA3", color="#221D2C")
    k.wash("#FF4FA3", 28, -1.6, 1.45, 1.6)
    k.neon([(0.6, WALL - 0.05, 0.95), (0.6, WALL - 0.05, 2.4)], "#FF4FA3", 26)
    k.neon([(2.75, WALL - 0.05, 0.95), (2.75, WALL - 0.05, 2.4)], "#22D3EE", 22)
    k.credenza(0.95, 2.55, 0.72, color="#1C1924")
    k.pc_tower(1.25, 0.72, y=WALL - 0.24)
    k.headphones(1.8, 0.72 + 0.12, WALL - 0.2, stand=True)
    k.plant(2.25, 0.72, 0.9)
    k.poster(1.35, 1.8, 0.42, 0.56, ["#2A1E4A", "#FF8FB8", "#22D3EE", "#7C5CFF"])
    k.poster(2.05, 1.85, 0.36, 0.48, ["#132A3A", "#FFC56E", "#FF4FA3"])
    k.wash("#22D3EE", 14, 2.4, 1.4, 1.0)


def moon_window(k):
    """Moonlit bedroom window: a big window with the moon and clouds, fairy lights across the top, curtains, a cat
    on the sill watching the moon, a lava lamp, and the corner of a bed."""
    win = (-2.0, 0.9, 0.78, 2.72)
    k.wall("#0F1424", win, frame="#141A2C", mullions=2)
    k.sky("#0B1640", "#1B2A5C", 1.1)
    k.stars(90)
    k.moon(WIDE_CAM, (-0.8, Y, 1.68))
    k.city(["#FFC873", "#9CC3FF"], n=8, near=50, spread=50, strength=1.6)
    k.curtain(-2.55, -1.92, 0.3, 2.85, "#2A3350")
    k.curtain(0.82, 1.35, 0.3, 2.85, "#2A3350")
    k.fairy(win[0] - 0.4, win[1] + 0.4, 2.12, 0.16, swags=5, y=Y - 0.16)
    k.wash("#FFC873", 22, -0.5, 2.0, 2.4)
    k.cat(-1.3, win[2] + 0.02, Y - 0.13)
    k.lava_lamp(0.55, win[2] + 0.02, Y - 0.12)
    k.plant(-0.2, win[2] + 0.02, 0.8, Y - 0.12)
    k.bed(1.55, 3.4, WALL - 1.9, WALL)
    k.poster(2.45, 1.75, 0.5, 0.36, ["#1B2244", "#F4EED8", "#3A4C8C"])
    k.area("MoonKey", "#9CC3FF", 40, (-1.2, Y + 0.8, 2.4), (-0.6, Y - 1.2, 1.0), 1.5)  # moonlight falls into the room


def retro_bedroom(k):
    """Retro gamer bedroom: a CRT on a wooden cabinet, shelves of game boxes, a pink LED cove at the ceiling, a
    neon sign that says LEVEL UP, a bean bag and posters."""
    k.wall("#101A26", top=2.75)
    k.glow("Cove", (X1 - X0, 0.02, 0.02), "#FF4FA3", 26, (0, WALL - 0.05, 2.68))
    k.area("CoveWash", "#FF4FA3", 60, (0, WALL - 0.3, 2.65), (0, Y, 1.6), 3.0)
    k.box("Cabinet", (0.95, 0.45, 0.62), k.m("#3B2B24", 0.55), (-1.55, WALL - 0.23, 0.31), 0.01)
    k.crt(-1.55, 0.62)
    k.box("GameBox", (0.22, 0.16, 0.05), k.m("#2B2B30", 0.4), (-1.15, WALL - 0.3, 0.645), 0.01)
    k.shelf(-2.25, -1.15, 1.62, "bBxb", color="#2E2420")
    k.shelf(-2.25, -1.15, 2.05, "fxfp", color="#2E2420")
    k.neon_text("LEVEL UP", (-0.62, WALL - 0.04, 1.72), 0.14, "#5EF2FF")
    k.wash("#5EF2FF", 16, -0.62, 1.72, 1.0)
    k.neon([(1.0, WALL - 0.05, 1.0), (1.0, WALL - 0.05, 2.3)], "#FF4FA3", 22)
    k.poster(2.3, 1.45, 0.42, 0.58, ["#2A1A3A", "#FFB347", "#FF4FA3", "#22D3EE"])
    k.poster(0.62, 2.05, 0.3, 0.4, ["#0F2A2A", "#5EF2FF", "#F5F5F5"])
    bb = ball("BeanBag", (0.42, 0.38, 0.28), k.coll, k.m("#3A2A5A", 0.85, sheen=0.6), (1.55, WALL - 0.6, 0.26), segs=24)
    bb.rotation_euler.z = 0.3
    tube(k.nm("Rug"), [Vector((1.0, WALL - 1.2, 0.0)), Vector((1.0, WALL - 1.2, 0.012))], 0.9, k.coll,
         k.m("#26304A", 0.95, sheen=0.4), k=40)


def studio_apartment(k):
    """A lived-in studio flat at night: a window with half-drawn curtains, a warm floor lamp, speakers on a low
    console under a floating shelf, a big plant, headphones on a wall hook, a sofa under the window."""
    win = (-2.7, -0.95, 0.95, 2.6)
    k.wall("#1A1A1F", win, frame="#202024", mullions=2)
    k.sky("#0B0D1A", "#2A2238", 0.55)
    k.bokeh(40, ["#FFB347", "#FFD08A", "#9CC3FF"], (25, 80), (-30, -4), (-3, 10), (0.3, 0.9), 9)
    k.city(["#FFC56E", "#FFD9A0"], n=8, spread=30, strength=1.8)
    k.curtain(-3.2, -2.25, 0.25, 2.8, "#3A4256")
    k.curtain(-1.25, -0.75, 0.25, 2.8, "#3A4256")
    k.sofa(-2.6, -1.05)
    k.tall_plant(-0.45, WALL - 0.4, 1.0)
    k.credenza(0.55, 2.7, 0.5, color="#2A221D")
    k.speaker(0.8, 0.5, 0.34)
    k.speaker(2.45, 0.5, 0.34)
    k.box("Record", (0.34, 0.3, 0.08), k.m("#151517", 0.4), (1.6, WALL - 0.2, 0.54), 0.01)
    tube(k.nm("Vinyl"), [Vector((1.6, WALL - 0.2, 0.58)), Vector((1.6, WALL - 0.2, 0.585))], 0.13, k.coll,
         k.m("#0A0A0A", 0.25, coat=0.8), k=32)
    k.shelf(0.75, 2.45, 1.55, "pbxpb", color="#2A221D")
    k.box("HookPlate", (0.04, 0.02, 0.06), k.m("#2A2B30", 0.3, metal=0.7), (1.05, WALL - 0.01, 1.2))
    k.headphones(1.05, 1.12, WALL - 0.05)
    k.poster(1.75, 2.05, 0.5, 0.34, ["#3A2418", "#FFB873", "#C9784E"])
    k.floor_lamp(2.95, WALL - 0.35)


BUILDERS = {"av_editor_night": editor_night, "av_streamer_den": streamer_den, "av_neon_shelf": neon_shelf,
            "av_moon_window": moon_window, "av_retro_bedroom": retro_bedroom, "av_studio_apartment": studio_apartment}


def backdrop(room_id, coll, rng):
    BUILDERS[room_id](Kit(coll, rng))
