"""The Shots-AV desk buddies: small AI companions that read as their product through colour and silhouette, never
through a traced logo (prompt section 3). Top of the file is pure data; build() runs inside Blender.

Rig (shared by all four, so a script can swap buddies without re-timing):
CHAR_root -> Body (render_plan keys its lean and breath) -> Squash (BuddyCtrl drivers: squash, lean, hop) -> Head
(render_plan's nod and listen-turn) -> geometry. FaceAnchor (head_height = body height), EyeFocus, FaceCtrl (52 ARKit
props: eyeBlink closes the eyes, jawOpen adds talk squash, mouthSmile gives happy arcs, browInnerUp gives the sad tilt,
eyeWide widens, eyeLook* moves the eyes), and BuddyCtrl with the props in BUDDY_CONTROLS (see reelforge/buddy.py).
Metres; the buddy stands on z = 0 and faces -Y; +X is its left (screen right from the front).
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
                  "eye_look_x": 0.0, "eye_look_y": 0.0, "glow": 0.0, "sig": 0.0, "phase": 0.0}
EYE = (0.008, 0.022)  # width, height
FOOT_Z = 0.012

BUDDIES = {
    "claude": {"label": "Claude", "reads_as": "Claude", "height": 0.140,
               "body": "#D97757", "shadow": "#B5553A", "glow": "#F2A383", "face": "#F0EEE6", "eyes_at": (0.013, 0.074),
               "feet": 2, "ray_legs": True,
               "signature": "a little spark creature: its rays ripple outward in turn while it speaks; it stands on "
                            "its two lower rays"},
    "chatgpt": {"label": "ChatGPT", "reads_as": "ChatGPT", "height": 0.140,
                "body": "#F3F3F0", "shadow": "#D9D9D2", "glow": "#10A37F", "eyes_at": (0.012, 0.076), "feet": 3,
                "signature": "its six petals turn a few degrees while it thinks"},
    "figma": {"label": "Figma", "reads_as": "Figma", "height": 0.144,
              "body": "#F24E1E", "shadow": "#C83A12", "glow": "#FF7262", "eyes_at": (0.0223, 0.1225), "feet": 3,
              "blocks": {"tl": "#F24E1E", "tr": "#FF7262", "ml": "#A259FF", "mr": "#1ABCFE", "bl": "#0ACF83"},
              "foot": "#07A56A",
              "signature": "its blocks spread out and snap back into the grid on emphasis"},
    "nova": {"label": "Nova", "reads_as": "any other assistant", "height": 0.136,
             "body": "#C9CCD6", "shadow": "#9EA2B0", "glow": "#C4B5FD", "eyes_at": (0.014, 0.076), "feet": 3,
             "signature": "its ring spins faster while it speaks"},
}
EYE_COLOR = "#0D0D0D"


# ============================================================================================================
# Everything below runs inside Blender.
# ============================================================================================================
def build(buddy_id: str, color: str | None = None):
    """Build one buddy into a new collection CHAR_base. `color` recolours the body (nova is meant for this)."""
    from reelforge.arkit import ARKIT_NAMES

    from .geo import ball, drive, empty, lin, mat, mesh, mix_hex, rbox, soften, tube

    if buddy_id not in BUDDIES:
        raise ValueError(f"unknown buddy {buddy_id!r}; known: {', '.join(BUDDIES)}")
    B = dict(BUDDIES[buddy_id])
    if color:
        B.update(body=color, shadow=mix_hex(color, "#000000", 0.2))
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
    total = "(s+0.06*clamp(j*2))"
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

    def gradient_mat(name, top, bottom, rough=0.55, sheen=0.0, coat=0.0):
        """Body colour fading to its shadow shade toward the feet (a painted ambient, as the reference does)."""
        m = mat(name, top, rough=rough, sheen=sheen, coat=coat)
        nt = m.node_tree
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -H * 0.45, H * 0.15
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[6].default_value = (*lin(bottom), 1.0)
        mix.inputs[7].default_value = (*lin(top), 1.0)
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], mix.inputs[0])
        nt.links.new(mix.outputs[2], nt.nodes["Principled BSDF"].inputs["Base Color"])
        return m

    def glow_mat(name, color, base, gain):
        m = mat(name, color, rough=0.4, emit=base)
        drive(m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"], "default_value",
              f"{base}+{gain}*g+{0.6 * gain}*sg", V(g="glow", sg="sig"))
        return m

    M_eye = mat("BD_Eye", EYE_COLOR, rough=0.25, coat=0.4)
    M_foot = mat("BD_Foot", B.get("foot", B["shadow"]), rough=0.6)

    # --- bodies ---------------------------------------------------------------------------------------------
    front_y = {}  # buddy-space y of the body's front surface at the eye height, per eye x (for eye placement)

    if buddy_id == "claude":
        # A spark creature: a soft clay core with a cream face plate and eight chunky rounded rays of uneven length.
        # The two lower rays are its legs, the top pair read as ears, the side rays as stubby arms.
        K = 1.15  # overall size; the lowest leg tip touches the desk
        cz = 0.068
        M_body = gradient_mat("BD_Body", B["body"], B["shadow"], rough=0.5, sheen=0.25)
        M_ray = mat("BD_Ray", B["body"], rough=0.5, sheen=0.25)
        core = ball("BD_Body", (0.040 * K, 0.034 * K, 0.038 * K), coll, M_body, (0, 0, cz), segs=32)
        local(core)
        plate = ball("BD_Face", (0.027 * K, 0.008 * K, 0.025 * K), coll, mat("BD_Face", B["face"], rough=0.55),
                     (0, -0.029 * K, cz + 0.005),
                     segs=28)
        local(plate)
        lengths = (1.00, 0.86, 1.08, 0.92, 1.0, 1.0, 0.95, 1.06)  # hand-made: no two rays quite the same
        jitter = (4, -6, 3, -2, 0, 0, 5, -4)  # degrees
        for i in range(8):
            ang = math.radians(22.5 + 45 * i + jitter[i])
            leg = i in (5, 6)  # the rays at about 247 and 292 degrees reach the desk
            piv = empty(f"Ray{i}", (0, 0, cz), coll)
            local(piv)
            piv.rotation_euler = (0, -ang, 0)  # local +X points along the ray, in the face plane
            L = (0.036 if leg else 0.031 * lengths[i]) * K
            n_pts = 9
            pts, rads = [], []
            for k in range(n_pts):
                t = k / (n_pts - 1)
                x = 0.028 * K + L * (1 - (1 - t) ** 1.35)  # points bunch up at the tip so it rounds off
                bend = (0.0 if leg else -0.006) * math.sin(math.pi * 0.5 * t)  # rays curl a little toward the camera
                pts.append(Vector((x, bend, 0.0)))
                rads.append(max(0.0006, K * (0.0165 if leg else 0.0150) * (1 - t ** 2.2) ** 0.55))
            ray = tube(f"BD_Ray{i}", pts, rads, coll, M_ray, k=14, parent=piv, up=(0, 1, 0))
            if not leg:  # the signature: each ray swells outward in turn (legs stay planted)
                drive(piv, "scale", f"1+0.28*sg*max(0,sin(ph-{i * math.pi / 4:.4f}))", V(sg="sig", ph="phase"), 0)
        front_y = {"y": -0.037 * K}
        glow = None

    elif buddy_id == "chatgpt":
        cz = FOOT_Z + 0.064
        petals = empty("Petals", (0, 0, cz), coll, head)
        petals.location = (0, 0, cz - H / 2)
        drive(petals, "rotation_euler", "0.10*sg*sin(0.6*ph)+0.06*sg", V(sg="sig", ph="phase"), 1)
        M_body = gradient_mat("BD_Body", B["body"], B["shadow"], rough=0.35, coat=0.3)
        for k in range(6):  # six rounded petals in a twisted pinwheel; the gaps between them show the inner glow
            a = math.radians(60 * k + 90)
            pet = ball(f"BD_Petal{k}", (0.031, 0.013, 0.0165), coll, M_body,
                       (0.031 * math.cos(a), 0.003 * (1 if k % 2 else -1), 0.031 * math.sin(a)), segs=20, parent=petals)
            pet.rotation_euler = (0, -(a + math.radians(28)), 0)
        hub = ball("BD_Hub", (0.024, 0.012, 0.024), coll, M_body, (0, -0.010, cz), segs=24)
        local(hub)
        glow = ball("BD_Core", (0.043, 0.008, 0.043), coll, glow_mat("BD_Glow", B["glow"], 1.4, 5.0), (0, 0.008, cz),
                    segs=24)
        local(glow)
        front_y = {"y": -0.014 - 0.016 * 0.98}

    elif buddy_id == "figma":
        s, gap = 0.043, 0.0015
        cells = {"tl": (-1, 2), "tr": (1, 2), "ml": (-1, 1), "mr": (1, 1), "bl": (-1, 0)}
        for name, (cx, row) in cells.items():
            centre = Vector((cx * (s / 2 + gap / 2), 0, FOOT_Z + s / 2 + row * (s + gap)))
            piv = empty(f"Block_{name}", centre, coll)
            local(piv)
            out = Vector((cx, 0, row - 1)).normalized() if (cx, row - 1) != (0, 0) else Vector((0, 0, 1))
            for axis, comp in ((0, out.x), (2, out.z)):  # spread on emphasis, snap back
                if comp:
                    drive(piv, "location", f"{float(piv.location[axis]):.5f}+{0.010 * comp:.4f}*sg*max(0,sin(2*ph))",
                          V(sg="sig", ph="phase"), axis)
            col = B["blocks"][name]
            rbox(f"BD_{name}", (s, s * 0.86, s), coll, gradient_mat(f"BD_{name}", col, mix_hex(col, "#000000", 0.18),
                                                                     rough=0.45, coat=0.2), 0.011, parent=piv, segs=3)
        front_y = {"y": -s * 0.43}
        glow = None

    else:  # nova: a faceted gem with a floating ring
        cz = FOOT_Z + 0.066
        gem = ball("BD_Body", (0.050, 0.042, 0.066), coll, gradient_mat("BD_Body", B["body"], B["shadow"], rough=0.25,
                                                                         coat=0.8), (0, 0, cz), ico=1, smooth=False)
        local(gem)
        ring_piv = empty("RingTilt", (0, 0, cz), coll)
        local(ring_piv)
        ring_piv.rotation_euler = (math.radians(18), math.radians(-12), 0)  # orbits the gem, not a halo behind it
        spin = empty("RingSpin", (0, 0, 0), coll, ring_piv)
        drive(spin, "rotation_euler", "ph", V(ph="phase"), 2)
        ring = [Vector((0.078 * math.cos(2 * math.pi * i / 48), 0.078 * math.sin(2 * math.pi * i / 48), 0))
                for i in range(48)]
        tube("BD_Ring", ring, 0.0045, coll, glow_mat("BD_Glow", B["glow"], 3.0, 6.0), k=8, closed=True, parent=spin)
        for i in range(3):  # three beads ride the ring so its spin reads
            a = 2 * math.pi * i / 3
            ball(f"BD_Bead{i}", (0.008, 0.008, 0.008), coll, mat("BD_Bead", B["glow"], emit=4.0),
                 (0.078 * math.cos(a), 0.078 * math.sin(a), 0), parent=spin, segs=12)
        front_y = {"y": -0.042 * 0.93}
        glow = None

    # --- feet and contact shadow ------------------------------------------------------------------------------
    nf = 0 if B.get("ray_legs") else B["feet"]  # the spark stands on its own rays
    for i in range(nf):
        a = math.pi * (1.5 + (i - (nf - 1) / 2) * 0.55) if nf == 3 else math.pi * (0.25 + 0.5 * i)
        r = 0.024 if buddy_id != "figma" else 0.014
        fx = r * math.cos(a) - (0.0225 if buddy_id == "figma" else 0)
        foot = ball(f"BD_Foot{i}", (0.0105, 0.012, 0.0085), coll, M_foot, (fx, r * math.sin(a), FOOT_Z * 0.72), segs=12)
        local(foot, squash)
        foot.location.z = FOOT_Z * 0.72  # feet stay planted while the body squashes and hops
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
    rad = 0.075 if buddy_id != "nova" else 0.07
    for axis in (0, 1):
        drive(disc, "scale", f"{rad}*(1-0.45*clamp(h))", V(h="hop"), axis)

    # --- eyes: rect, happy arcs, sad tilt, wide, wink -----------------------------------------------------------
    ex, ez = B["eyes_at"]
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ys = []
    for sx in (1, -1):  # sit the eyes 1.5 mm proud of the real (lumpy) front surface
        hit, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((sx * ex, -1.0, ez)), Vector((0, 1, 0)))
        ys.append(loc.y if hit else front_y["y"])
    front_y = {"y": min(ys)}
    w = {k: f"max(0,1-abs(es-{i}))" for i, k in enumerate(("rect", "happy", "sad", "wide", "wink"))}
    ev = V(es="eye_shape", eh="eye_h", lx="eye_look_x", ly="eye_look_y", sm="f:mouthSmileLeft", bu="f:browInnerUp",
           wd="f:eyeWideLeft", flx="f:eyeLookOutLeft", fly="f:eyeLookUpLeft", fdn="f:eyeLookDownLeft")
    for tag, sx in (("L", 1), ("R", -1)):
        ev_side = {**ev, "b": (face, f"eyeBlink{'Left' if sx > 0 else 'Right'}")}
        piv = empty(f"BuddyEye{tag}", (sx * ex, front_y["y"] - 0.0028, ez), coll)  # proud enough to ride a curved face
        local(piv)
        drive(piv, "location", f"{sx * ex:.5f}+0.005*(lx+flx*{sx})", ev_side, 0)
        drive(piv, "location", f"{ez - H / 2:.5f}+0.004*(ly+fly-fdn)", ev_side, 2)
        rect = rbox(f"BD_Eye{tag}", (EYE[0], 0.004, EYE[1]), coll, M_eye, 0.0025, parent=piv, segs=3)
        happy_w = f"clamp({w['happy']}+0.8*sm)" + (f"+{w['wink']}" if sx < 0 else "")
        shown = f"clamp(1-{happy_w})"
        wink_closed = f"{w['wink']}" if sx > 0 else "0"
        open_h = f"eh*(1-b)*({w['rect']}+0.75*{w['sad']}+1.25*{w['wide']})*(1+0.25*wd)*(1-{wink_closed})"
        drive(rect, "scale", f"{shown}*(1+0.45*{w['wide']}+0.25*wd)*(1+0.6*({wink_closed}))", ev_side, 0)
        drive(rect, "scale", f"{shown}*max(0.12,{open_h})", ev_side, 2)
        drive(rect, "rotation_euler", f"{sx}*0.42*clamp({w['sad']}+0.6*bu)", ev_side, 1)
        arc = [Vector((0.0075 * math.sin(a), -0.001, 0.0065 * math.cos(a) - 0.002))
               for a in np.linspace(-1.25, 1.25, 7)]
        happy = tube(f"BD_EyeHappy{tag}", arc, 0.0018, coll, M_eye, k=8, parent=piv, up=(0, 1, 0))
        for axis in (0, 1, 2):
            drive(happy, "scale", happy_w, ev_side, axis)
    anchor = empty("FaceAnchor", (0, front_y["y"], ez), coll)
    local(anchor)
    anchor["head_height"] = H
    anchor["min_head"] = 0.0
    focus = empty("EyeFocus", (0, front_y["y"] - 0.002, ez), coll)
    local(focus)
    root["buddy"] = buddy_id
    return coll
