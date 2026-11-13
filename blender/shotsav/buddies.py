"""The Shots-AV desk buddies: four small, modern desk robots. Each has a premium satin shell, a recessed glossy display
behind a domed glass lens, glowing eyes on that display and a mouth that is a live audio waveform. Colour, shell shape
and one accessory say which product it stands for; nothing traces a logo (prompt section 3).
Top of the file is pure data; build() runs inside Blender.

Rig (shared by all four, so a script can swap buddies without re-timing):
CHAR_root -> Body (render_plan keys its lean and breath) -> Squash (BuddyCtrl drivers: squash, lean, hop) -> Head
(render_plan's nod and listen-turn) -> geometry. FaceAnchor (head_height = body height), EyeFocus, FaceCtrl (52 ARKit
props: eyeBlink closes the eyes, jawOpen drives the waveform and a little squash, mouthSmile gives happy arcs,
browInnerUp gives the sad tilt, eyeWide widens, eyeLook* moves the eyes), and BuddyCtrl with the props in
BUDDY_CONTROLS (see reelforge/buddy.py). Metres; the buddy stands on z = 0 and faces -Y; +X is its left.
"""
from __future__ import annotations

import math

try:
    import bmesh
    import bpy
    import numpy as np
    from mathutils import Vector
except ImportError:  # read as a data table outside Blender
    bpy = None

BUDDY_CONTROLS = {"squash": 0.0, "lean_x": 0.0, "lean_y": 0.0, "hop": 0.0, "eye_h": 1.0, "eye_shape": 0.0,
                  "eye_look_x": 0.0, "eye_look_y": 0.0, "glow": 0.0, "sig": 0.0, "phase": 0.0, "voice": 0.0}
EYE = (0.011, 0.019)  # width, height of a display eye
MOUTH_BARS = 9
SCREEN_BLACK = "#06070A"

BUDDIES = {
    "claude": {"label": "Claude", "reads_as": "Claude", "height": 0.144, "feet": 2,
               "shell": "#D97757", "shadow": "#B5553A", "trim": "#F0EEE6", "glow": "#FFE9CF",
               "shape": (0.058, 0.050, 0.054, 2.6), "centre_z": 0.066, "screen": ("circle", 0.039, 0.036),
               "signature": "a spark antenna on its head spins and pulses while it speaks"},
    "chatgpt": {"label": "ChatGPT", "reads_as": "ChatGPT", "height": 0.140, "feet": 0,
                "shell": "#F3F3F0", "shadow": "#D6D6CF", "trim": "#2A2B2F", "glow": "#10A37F",
                "shape": (0.056, 0.052, 0.056, 2.0), "centre_z": 0.070, "screen": ("hex", 0.040, 0.037),
                "signature": "a rounded hex ring around it turns while it thinks; it sits on a charging puck"},
    "figma": {"label": "Figma", "reads_as": "Figma", "height": 0.142, "feet": 0,
              "shell": "#2B2B30", "shadow": "#1B1B1F", "trim": "#3A3A40", "glow": "#F4F4F6",
              "shape": (0.054, 0.040, 0.047, 5.0), "centre_z": 0.074, "screen": ("squircle", 0.042, 0.034),
              "blocks": {"tl": "#F24E1E", "tr": "#FF7262", "ml": "#A259FF", "mr": "#1ABCFE", "bl": "#0ACF83"},
              "signature": "its five colour blocks pop out and snap back on emphasis"},
    "nova": {"label": "Nova", "reads_as": "any other assistant", "height": 0.136, "feet": 0,
             "shell": "#C9CCD6", "shadow": "#9EA2B0", "trim": "#E6E8EE", "glow": "#C4B5FD",
             "shape": (0.052, 0.050, 0.052, 2.0), "centre_z": 0.080, "screen": ("pill", 0.044, 0.024),
             "signature": "it hovers; its beaded orbit ring spins faster while it speaks"},
}


# ============================================================================================================
# Everything below runs inside Blender.
# ============================================================================================================
def outline(kind, ax, az, n=64):
    """Screen outline in the XZ plane (centred at 0)."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        if kind == "hex":  # a hexagon with generously rounded corners
            k = math.pi / 3
            r = math.cos(k / 2) / math.cos((t % k) - k / 2)
            r = 0.72 * r + 0.28
            pts.append((ax * r * c, az * r * s))
        else:
            e = {"circle": 2.0, "squircle": 4.5, "pill": 3.4}[kind]
            pts.append((ax * math.copysign(abs(c) ** (2 / e), c), az * math.copysign(abs(s) ** (2 / e), s)))
    return pts


def build(buddy_id: str, color: str | None = None):
    """Build one buddy into a new collection CHAR_base. `color` recolours the shell (nova is meant for this)."""
    from reelforge.arkit import ARKIT_NAMES

    from .geo import ball, drive, empty, loft, mat, mesh, mix_hex, rbox, soften, tube

    if buddy_id not in BUDDIES:
        raise ValueError(f"unknown buddy {buddy_id!r}; known: {', '.join(BUDDIES)}")
    B = dict(BUDDIES[buddy_id])
    if color:
        B.update(shell=color, shadow=mix_hex(color, "#000000", 0.2))
    H = B["height"]
    coll = bpy.data.collections.new("CHAR_base")
    bpy.context.scene.collection.children.link(coll)

    root = empty("CHAR_root", (0, 0, 0), coll)
    body = empty("Body", (0, 0, 0), coll, root)
    squash = empty("Squash", (0, 0, 0), coll, body)
    head = empty("Head", (0, 0, H / 2), coll, squash)
    ctrl = empty("BuddyCtrl", (0, 0, H + 0.06), coll, root)
    for k, v in BUDDY_CONTROLS.items():
        ctrl[k] = v
    ctrl["buddy"] = buddy_id
    face = empty("FaceCtrl", (0, 0, H + 0.09), coll, head)
    for n in ARKIT_NAMES:
        face[n] = 0.0

    def V(**names):  # driver variables: BuddyCtrl props by default, "f:" prefix for FaceCtrl
        return {k: ((face, p[2:]) if p.startswith("f:") else (ctrl, p)) for k, p in names.items()}

    sq = V(s="squash", j="f:jawOpen", h="hop", lx="lean_x", ly="lean_y")
    total = "(0.6*s+0.03*clamp(j*2))"  # robots squash less than a blob would
    drive(squash, "scale", f"1+0.5*{total}", sq, 0)
    drive(squash, "scale", f"1+0.5*{total}", sq, 1)
    drive(squash, "scale", f"1-{total}", sq, 2)
    drive(squash, "location", "0.06*h", sq, 2)
    drive(squash, "rotation_euler", "0.35*ly", sq, 0)  # forward (toward the camera) is positive
    drive(squash, "rotation_euler", "0.40*lx", sq, 1)  # toward +X is positive

    def local(o, parent=head):  # authored in buddy space (z up from the desk), parented under Head
        o.parent = parent
        o.location = Vector(o.location) - Vector((0, 0, H / 2))
        return o

    def satin(name, color, rough=0.38, coat=0.35, metal=0.0, sheen=0.0):
        return mat(name, color, rough=rough, coat=coat, metal=metal, sheen=sheen)

    def glow_mat(name, color, base, gain=3.0):
        m = mat(name, color, rough=0.5, emit=base)
        drive(m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"], "default_value",
              f"{base}*(1+0.5*g)+{gain}*sg*0.3", V(g="glow", sg="sig"))
        return m

    def superball(name, radii, e, m, loc, segs=48):
        """A superellipsoid shell (e = 2 is a sphere, higher is squarer), smooth with weighted normals."""
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=1.0)
        for v in bm.verts:
            v.co = Vector(tuple(math.copysign(abs(c) ** (2 / e), c) * r for c, r in zip(v.co, radii)))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        o.location = loc
        local(o)
        o.modifiers.new("Normals", "WEIGHTED_NORMAL")
        return o

    def plate(name, pts2d, y, depth, m, z0, bevel=0.0015):
        """A flat extruded shape in the XZ plane (front face at y), bevelled so its edge catches light."""
        front = [Vector((x, y, z0 + z)) for x, z in pts2d]
        back = [Vector((x, y + depth, z0 + z)) for x, z in pts2d]
        o = loft(name, [front, back], coll, m, closed=True, caps=(True, True), smooth=False)
        local(o)
        return soften(o, bevel, 2, 40)

    rx, ry, rz, e = B["shape"]
    cz = B["centre_z"]
    M_shell = satin("BD_Shell", B["shell"])
    M_trim = satin("BD_Trim", B["trim"], rough=0.3, coat=0.6)
    M_dark = satin("BD_Dark", "#1A1B1F", rough=0.45)
    M_glow = glow_mat("BD_Glow", B["glow"], 6.0)
    M_screen = mat("BD_Screen", SCREEN_BLACK, rough=0.18, coat=1.0)
    glass = bpy.data.materials.new("BD_Glass")  # a domed lens over the display: reflections, never a veil
    glass.use_nodes = True
    nt = glass.node_tree
    nt.nodes.clear()
    out, mix = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeMixShader")
    tr, gl, fr = (nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeBsdfGlossy"),
                  nt.nodes.new("ShaderNodeFresnel"))
    gl.inputs["Roughness"].default_value = 0.04
    fr.inputs["IOR"].default_value = 1.45
    nt.links.new(fr.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(glass, "surface_render_method"):
        glass.surface_render_method = "BLENDED"

    # --- shell ---------------------------------------------------------------------------------------------
    kind, sax, saz = B["screen"]
    sz = cz + 0.003  # the display sits a touch above the shell's centre
    if buddy_id == "figma":
        local(rbox("BD_Shell", (2 * rx, 2 * ry, 2 * rz), coll, M_shell, 0.016, (0, 0, cz), segs=4))
    else:
        superball("BD_Shell", (rx, ry, rz), e, M_shell, (0, 0, cz))
        zz = cz - rz * 0.62  # a fine seam line around the shell: product detail
        k_ = (1 - ((zz - cz) / rz) ** 2) ** 0.5
        seam = [Vector((rx * 1.004 * k_ * math.cos(2 * math.pi * i / 64), ry * 1.004 * k_ * math.sin(2 * math.pi * i / 64),
                        zz)) for i in range(64)]
        local(tube("BD_Seam", seam, 0.0011, coll, M_dark, k=6, closed=True))
    shell_front = -ry

    # --- display: bezel, recessed black screen, emissive face, glass dome ---------------------------------------
    fy = shell_front - 0.004  # the bezel's front plane, just proud of the shell
    plate("BD_Bezel", outline(kind, sax + 0.0055, saz + 0.0055), fy, 0.014, M_trim, sz)
    plate("BD_Screen", outline(kind, sax, saz), fy - 0.0006, 0.010, M_screen, sz, bevel=0.0008)
    gy = fy - 0.0016  # face graphics float just in front of the screen, behind the glass
    dome = ball("BD_Glass", (sax * 0.99, 0.0045, saz * 0.99), coll, glass, (0, fy - 0.0008, sz), segs=40)
    local(dome)
    dome.visible_shadow = False

    # eyes: rect, happy arcs, sad tilt, wide, wink (glowing on the display)
    ex, ez = sax * 0.36, sz + saz * 0.18
    eye_w, eye_h = EYE
    if kind == "pill":
        eye_w, eye_h, ex, ez = 0.010, 0.013, sax * 0.40, sz + 0.002
    w = {k: f"max(0,1-abs(es-{i}))" for i, k in enumerate(("rect", "happy", "sad", "wide", "wink"))}
    ev = V(es="eye_shape", eh="eye_h", lx="eye_look_x", ly="eye_look_y", sm="f:mouthSmileLeft", bu="f:browInnerUp",
           wd="f:eyeWideLeft", flx="f:eyeLookOutLeft", fly="f:eyeLookUpLeft", fdn="f:eyeLookDownLeft")
    for tag, sx in (("L", 1), ("R", -1)):
        ev_side = {**ev, "b": (face, f"eyeBlink{'Left' if sx > 0 else 'Right'}")}
        piv = empty(f"BuddyEye{tag}", (sx * ex, gy, ez), coll)
        local(piv)
        drive(piv, "location", f"{sx * ex:.5f}+0.006*(lx+flx*{sx})", ev_side, 0)
        drive(piv, "location", f"{ez - H / 2:.5f}+0.005*(ly+fly-fdn)", ev_side, 2)
        rect = rbox(f"BD_Eye{tag}", (eye_w, 0.0012, eye_h), coll, M_glow, eye_w * 0.42, parent=piv, segs=3)
        happy_w = f"clamp({w['happy']}+0.8*sm)" + (f"+{w['wink']}" if sx < 0 else "")
        shown = f"clamp(1-{happy_w})"
        wink_closed = f"{w['wink']}" if sx > 0 else "0"
        open_h = f"eh*(1-b)*({w['rect']}+0.75*{w['sad']}+1.25*{w['wide']})*(1+0.25*wd)*(1-{wink_closed})"
        drive(rect, "scale", f"{shown}*(1+0.35*{w['wide']}+0.25*wd)*(1+0.5*({wink_closed}))", ev_side, 0)
        drive(rect, "scale", f"{shown}*max(0.14,{open_h})", ev_side, 2)
        drive(rect, "rotation_euler", f"{sx}*0.40*clamp({w['sad']}+0.6*bu)", ev_side, 1)
        arc = [Vector((eye_w * 0.9 * math.sin(a), 0.0, eye_h * 0.42 * math.cos(a) - eye_h * 0.12))
               for a in np.linspace(-1.3, 1.3, 9)]
        happy = tube(f"BD_EyeHappy{tag}", arc, 0.0019, coll, M_glow, k=8, parent=piv, up=(0, 1, 0))
        for axis in (0, 1, 2):
            drive(happy, "scale", happy_w, ev_side, axis)

    # mouth: a live waveform; silent, it rests as a row of dots; happy and quiet, it turns into a small smile
    mz = sz - saz * 0.42 if kind != "pill" else sz - 0.0115
    span = sax * (0.95 if kind != "pill" else 0.75)
    bar_h = saz * 0.42 if kind != "pill" else 0.010
    mv = V(v="voice", j="f:jawOpen", ph="phase", es="eye_shape")
    talk = "clamp(v+0.8*j)"
    quiet_happy = f"max(0,1-abs(es-1))*(1-clamp(3*{talk}))"
    for i in range(MOUTH_BARS):
        u = i / (MOUTH_BARS - 1) * 2 - 1
        shape_i = 1 - 0.75 * u * u
        bar = rbox(f"BD_Wave{i}", (0.0024, 0.0012, bar_h), coll, M_glow, 0.0011, (u * span * 0.5, gy, mz), segs=2)
        local(bar)
        drive(bar, "scale", f"(0.10+{shape_i:.3f}*{talk}*(0.35+0.65*abs(sin(2.6*ph+{i * 1.93:.2f}))))"
                            f"*(1-{quiet_happy})", mv, 2)
        drive(bar, "scale", f"1-{quiet_happy}", mv, 0)
    smile = [Vector((span * 0.36 * math.sin(a), gy, mz + 0.006 - span * 0.20 * math.cos(a)))
             for a in np.linspace(-1.1, 1.1, 11)]
    sm_o = tube("BD_Smile", smile, 0.0016, coll, M_glow, k=8, up=(0, 1, 0))
    local(sm_o)
    for axis in (0, 1, 2):
        drive(sm_o, "scale", quiet_happy, mv, axis)

    # --- accessories (the signature) --------------------------------------------------------------------------
    top = cz + rz
    if buddy_id == "claude":
        local(tube("BD_Stalk", [Vector((0, 0.004, top - 0.004)), Vector((0, 0.004, top + 0.014))], 0.0022, coll,
                   M_dark, k=8))
        spark_piv = empty("Spark", (0, 0.004, top + 0.020), coll)
        local(spark_piv)
        drive(spark_piv, "rotation_euler", "0.8*ph", V(ph="phase"), 1)
        drive(spark_piv, "scale", "1+0.18*sg*abs(sin(2*ph))", V(sg="sig", ph="phase"), 0)
        drive(spark_piv, "scale", "1+0.18*sg*abs(sin(2*ph))", V(sg="sig", ph="phase"), 2)
        M_spark = glow_mat("BD_Spark", "#F28A62", 2.5)
        for i in range(8):
            a = 2 * math.pi * i / 8
            L = 0.011 if i % 2 == 0 else 0.008
            ray = [Vector((0.002 * math.cos(a), 0, 0.002 * math.sin(a))), Vector((L * math.cos(a), 0, L * math.sin(a)))]
            tube(f"BD_SparkRay{i}", ray, [0.0026, 0.0015], coll, M_spark, k=8, parent=spark_piv)
        ball("BD_SparkCore", (0.0034, 0.0034, 0.0034), coll, M_spark, (0, 0, 0), segs=12, parent=spark_piv)
        for sx in (1, -1):  # two small rounded feet
            foot = rbox(f"BD_Foot{sx}", (0.022, 0.030, 0.014), coll, satin("BD_Foot", B["shadow"]), 0.006,
                        (sx * 0.024, -0.004, 0.007))
            local(foot, squash)
            foot.location.z = 0.007
        for sx in (1, -1):  # little ear dials
            local(tube(f"BD_Ear{sx}", [Vector((sx * (rx - 0.004), 0, cz + 0.004)), Vector((sx * (rx + 0.006), 0, cz + 0.004))],
                       0.010, coll, M_trim, k=20))
    elif buddy_id == "chatgpt":
        p_o = tube("BD_Puck", [Vector((0, 0, 0.0)), Vector((0, 0, 0.012))], 0.036, coll,
                   satin("BD_Puck", "#2A2B2F", rough=0.35), k=48)
        local(p_o, squash)
        p_o.location = (0, 0, 0)
        strip = [Vector((0.0362 * math.cos(2 * math.pi * i / 64), 0.0362 * math.sin(2 * math.pi * i / 64), 0.004))
                 for i in range(64)]
        s_o = tube("BD_PuckLight", strip, 0.0012, coll, glow_mat("BD_PuckGlow", B["glow"], 3.0), k=6, closed=True)
        local(s_o, squash)
        s_o.location = (0, 0, 0)
        ring_tilt = empty("RingTilt", (0, 0, cz - 0.040), coll)  # orbits the lower body, never across the face
        local(ring_tilt)
        ring_tilt.rotation_euler = (math.radians(8), math.radians(-6), 0)
        ring_spin = empty("RingSpin", (0, 0, 0), coll, ring_tilt)
        drive(ring_spin, "rotation_euler", "0.12*sin(0.5*ph)+0.18*sg*ph", V(ph="phase", sg="sig"), 2)
        hexring = [Vector((x, z, 0)) for x, z in outline("hex", 0.066, 0.066, n=72)]
        tube("BD_HexRing", hexring, 0.0030, coll, M_trim, k=10, closed=True, parent=ring_spin, up=(0, 0, 1))
        tube("BD_HexGlow", [Vector((x, z, 0.0026)) for x, z in outline("hex", 0.066, 0.066, n=72)], 0.0011, coll,
             glow_mat("BD_RingGlow", B["glow"], 2.5), k=6, closed=True, parent=ring_spin, up=(0, 0, 1))
    elif buddy_id == "figma":
        cells = {"tl": (-0.024, top + 0.011, "box"), "tr": (0.006, top + 0.009, "box"),
                 "ml": (-rx - 0.009, cz, "box"), "mr": (rx + 0.011, cz, "ball"), "bl": (0.0, 0.013, "stand")}
        for name, (x, z, what) in cells.items():
            piv = empty(f"Block_{name}", (x, 0.0, z), coll)
            local(piv)
            out_v = Vector((x, 0, z - cz)).normalized()
            for axis, comp in ((0, out_v.x), (2, out_v.z)):  # pop out on emphasis, snap back
                if abs(comp) > 0.1:
                    drive(piv, "location", f"{float(piv.location[axis]):.5f}+{0.008 * comp:.4f}*sg*max(0,sin(2*ph))",
                          V(sg="sig", ph="phase"), axis)
            col = satin(f"BD_{name}", B["blocks"][name], rough=0.32, coat=0.5)
            if what == "ball":
                ball(f"BD_{name}", (0.013, 0.013, 0.013), coll, col, (0, 0, 0), segs=24, parent=piv)
            elif what == "stand":
                rbox(f"BD_{name}", (0.040, 0.034, 0.026), coll, col, 0.008, parent=piv, segs=3)
            else:
                rbox(f"BD_{name}", (0.016 if name == "ml" else 0.024, 0.024, 0.024), coll, col, 0.006, parent=piv,
                     segs=3)
    else:  # nova: hovers; a beaded orbit ring
        ring_tilt = empty("RingTilt", (0, 0, cz), coll)
        local(ring_tilt)
        ring_tilt.rotation_euler = (math.radians(18), math.radians(-12), 0)
        spin = empty("RingSpin", (0, 0, 0), coll, ring_tilt)
        drive(spin, "rotation_euler", "ph", V(ph="phase"), 2)
        ring = [Vector((0.078 * math.cos(2 * math.pi * i / 64), 0.078 * math.sin(2 * math.pi * i / 64), 0))
                for i in range(64)]
        tube("BD_Ring", ring, 0.0016, coll, M_trim, k=8, closed=True, parent=spin)
        M_bead = glow_mat("BD_Bead", B["glow"], 4.0)
        for i in range(3):
            a = 2 * math.pi * i / 3
            ball(f"BD_Bead{i}", (0.0045, 0.0045, 0.0045), coll, M_bead, (0.078 * math.cos(a), 0.078 * math.sin(a), 0),
                 parent=spin, segs=12)
        drive(head, "location", f"{H / 2:.4f}+0.004*sin(0.35*ph)", V(ph="phase"), 2)  # a gentle hover bob
        under = ball("BD_HoverGlow", (0.020, 0.020, 0.002), coll, glow_mat("BD_Under", B["glow"], 1.5), (0, 0, 0.004),
                     segs=20)
        local(under, squash)
        under.location = (0, 0, 0.004)

    # --- contact shadow ---------------------------------------------------------------------------------------
    sh = bpy.data.materials.new("BD_Shadow")
    sh.use_nodes = True
    nt = sh.node_tree
    nt.nodes.clear()
    out_n, mix = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeMixShader")
    tr_n, df = nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeBsdfDiffuse")
    df.inputs["Color"].default_value = (0, 0, 0, 1)
    tc, gr, ramp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeTexGradient"), nt.nodes.new("ShaderNodeValToRGB")
    gr.gradient_type = "SPHERICAL"
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.95, (0.55, 0.55, 0.55, 1)
    nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
    nt.links.new(gr.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs[0])
    nt.links.new(tr_n.outputs[0], mix.inputs[1])
    nt.links.new(df.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out_n.inputs["Surface"])
    if hasattr(sh, "surface_render_method"):
        sh.surface_render_method = "BLENDED"
    disc = mesh("BD_ContactShadow", [(math.cos(2 * math.pi * i / 24), math.sin(2 * math.pi * i / 24), 0)
                                     for i in range(24)], [tuple(range(24))], coll, sh, parent=root)
    disc.location.z = 0.0008
    disc.visible_shadow = False
    for axis in (0, 1):
        drive(disc, "scale", "0.07*(1-0.45*clamp(h))", V(h="hop"), axis)

    anchor = empty("FaceAnchor", (0, gy, sz), coll)
    local(anchor)
    anchor["head_height"] = H
    anchor["min_head"] = 0.0
    focus = empty("EyeFocus", (0, gy - 0.002, ez), coll)
    local(focus)
    root["buddy"] = buddy_id
    return coll
