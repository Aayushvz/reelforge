"""Render a reelforge render_plan.json inside an environment .blend.
Run: blender -b <env.blend> --factory-startup --python-exit-code 1 -P blender/render_plan.py -- <plan.json> <stills|full>"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_common import EEVEE, look_at  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
plan = json.loads(Path(args[0]).read_text(encoding="utf-8"))
mode = args[1] if len(args) > 1 else "full"
sc = bpy.context.scene
fps, n = plan["fps"], plan["n_frames"]

# shot kind -> (distance m, f-stop, azimuth rad, elevation rad)
SHOT = {"wide": (2.6, 0.5, math.radians(-15), math.radians(6)),  # f/0.5 cheat: wide shots get bokeh too
        "medium": (1.8, 1.8, math.radians(12), math.radians(4)),
        "closeup": (2.3, 2.0, math.radians(-6), math.radians(2))}

# --- characters: each on its own mark ---------------------------------------------
CH = {}  # name -> dict(root, head, ctrl, face_pos, focus, head_k)
for char in plan["characters"]:
    with bpy.data.libraries.load(char["blend"], link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c == "CHAR_base"]
    coll = dst.collections[0]
    sc.collection.children.link(coll)
    objs = {o.name.split(".")[0]: o for o in coll.objects}
    root, head = objs["CHAR_root"], objs["Head"]
    root.location = bpy.data.objects[char["mark"]].location
    bpy.context.view_layer.update()
    if "FaceAnchor" in objs:  # sculpted cast: anchors + real head size
        face_pos = objs["FaceAnchor"].matrix_world.translation.copy()
        focus = objs["EyeFocus"]
        head_k = objs["FaceAnchor"]["head_height"] / 0.43  # framing was tuned on the 0.43 m stand-in head
    else:  # M1 stand-in
        face_pos = head.matrix_world.translation + Vector((0, 0, 0.18))
        focus = bpy.data.objects.new(f"Focus{char['name']}", None)
        sc.collection.objects.link(focus)
        focus.location = face_pos + Vector((0, -0.19, 0))  # eye plane, not head centre
        head_k = 1.0
    CH[char["name"]] = {"head": head, "ctrl": objs["FaceCtrl"], "face_pos": face_pos, "focus": focus,
                        "head_k": head_k, "face": char["face"], "body": objs.get("Body"),
                        "elbows": {k: objs[k] for k in ("ElbowL", "ElbowR") if k in objs}}


def key_track(obj, prop, values, eps=0.002):
    """Sparse keys on custom prop `prop`. Before a change that follows a skipped (flat) run,
    a hold key repeats the last value on the previous frame, so the value stays flat
    across the run and only moves where the track moves."""
    path = f'["{prop}"]'

    def put(f, v):
        obj[prop] = v
        obj.keyframe_insert(path, frame=f + 1)

    last, last_f = None, -1
    for f, v in enumerate(values):
        if last is None or abs(v - last) > eps or f == len(values) - 1:
            if last is not None and f - 1 > last_f:
                put(f - 1, last)  # hold
            put(f, v)
            last, last_f = v, f



def speaker_at(f):
    for sh in plan["shots"]:
        if sh["start_frame"] <= f < sh["end_frame"]:
            return sh["subject"]
    return None


for name, c in CH.items():
    others = [o for o in CH if o != name]
    if others:  # eyelines: a listener's eyes slide toward whoever is talking (on top of the head turn)
        target = {k: [0.0] * n for k in ("eyeLookOutLeft", "eyeLookInRight", "eyeLookInLeft", "eyeLookOutRight")}
        for f in range(n):
            spk = speaker_at(f)
            if spk in others:
                right = CH[spk]["face_pos"].x > c["face_pos"].x  # speaker on +X = this character's left
                for k in (("eyeLookOutLeft", "eyeLookInRight") if right else ("eyeLookInLeft", "eyeLookOutRight")):
                    target[k][f] = 0.45
        for k, vals in target.items():
            cur, out = 0.0, []
            for v in vals:
                cur += (v - cur) * 0.25  # ~4-frame ease, eyes lead the head
                out.append(cur)
            base = c["face"].get(k, [0.0] * n)
            c["face"][k] = [max(x, y) for x, y in zip(base, out)]
    for ch, values in c["face"].items():
        if ch == "headNod" or ch not in c["ctrl"].keys() or max(values) == 0.0:
            continue
        key_track(c["ctrl"], ch, values)
    nod = c["face"].get("headNod", [0.0] * n)
    others = [o for o in CH if o != name]
    for f in range(0, n, 2):
        yaw = 0.0
        spk = speaker_at(f)
        if spk in others:  # listening: turn toward whoever is talking
            dx = CH[spk]["face_pos"].x - c["face_pos"].x
            yaw = math.copysign(0.35, dx)
        c["head"].rotation_euler = (nod[f] + 0.02 * math.sin(f * 0.05), 0.015 * math.sin(f * 0.031), yaw)
        c["head"].keyframe_insert("rotation_euler", frame=f + 1)
    if c["body"] is not None:  # breathe (~3.5 s cycle) and lean in while talking
        jaw = c["face"].get("jawOpen", [0.0] * n)
        talk, lean = 0.0, []
        for f in range(n):
            talk += ((1.0 if jaw[f] > 0.05 else 0.0) - talk) * 0.06  # slow follow: no twitching
            lean.append(talk)
        for f in range(0, n, 3):
            breath = math.sin(2 * math.pi * f / (fps * 3.5) + len(name))
            c["body"].rotation_euler = (0.045 * lean[f] + 0.006 * breath, 0.0, 0.0)
            c["body"].scale = (1.0, 1.0, 1.0 + 0.006 * breath)
            c["body"].keyframe_insert("rotation_euler", frame=f + 1)
            c["body"].keyframe_insert("scale", frame=f + 1)
        # talking hands: the dominant (right) forearm lifts off the desk in a slow beat, the left one stirs
        for side, amp, phase in (("ElbowR", 1.0, 0.0), ("ElbowL", 0.3, 1.7)):
            e = c["elbows"].get(side)
            if e is None:
                continue
            for f in range(0, n, 3):
                beat = 0.5 + 0.5 * math.sin(2 * math.pi * f / (fps * 1.3) + phase)
                e.rotation_euler = (-lean[f] * amp * (0.3 + 0.4 * beat), 0.0, 0.0)
                e.keyframe_insert("rotation_euler", frame=f + 1)

# --- moods (10-frame crossfades) -------------------------------------------
presets = plan["mood_presets"]


TINT = sc.get("mood_tint", 1.0)  # 1 = mood colours replace the set's lights (night_city); less = tint them


def apply_mood(p, frame):
    calm = presets["calm"]
    for name, ck, wk in (("Key", "key", "key_w"), ("Rim", "rim", "rim_w"), ("Glow", "glow", "glow_w")):
        obj = bpy.data.objects[name]
        base_c, base_w = list(obj.get("base_color", calm[ck])), obj.get("base_energy", calm[wk])
        ld = obj.data
        ld.color = [b + (m - b) * TINT for b, m in zip(base_c, p[ck])]
        ld.energy = base_w * p[wk] / calm[wk]
        ld.keyframe_insert("color", frame=frame)
        ld.keyframe_insert("energy", frame=frame)
    c = p["screen"]
    for mname in ("ScreenMat", "HoloMat"):
        if mname not in bpy.data.materials:
            continue
        node = bpy.data.materials[mname].node_tree.nodes["Code"]
        node.inputs["Color1"].default_value = (*c, 1.0)
        node.inputs["Color2"].default_value = (c[0] * 0.5, c[1] * 0.5, c[2] * 0.5, 1.0)
        node.inputs["Color1"].keyframe_insert("default_value", frame=frame)
        node.inputs["Color2"].keyframe_insert("default_value", frame=frame)


moods = plan["moods"]
apply_mood(presets[moods[0][1]], 1)
for (f, m), (_, prev) in zip(moods[1:], moods[:-1]):
    apply_mood(presets[prev], max(1, f + 1 - 5))
    apply_mood(presets[m], f + 1 + 5)

# --- cameras per shot --------------------------------------------------------
cams = []
for i, s in enumerate(plan["shots"]):
    dist, fstop, az, el = SHOT[s["kind"]]
    subj = CH.get(s["subject"]) or next(iter(CH.values()))
    dist *= {"closeup": subj["head_k"], "medium": subj["head_k"] ** 0.5}.get(s["kind"], 1.0)
    face_pos, focus = subj["face_pos"], subj["focus"]
    if s["kind"] == "wide" and len(CH) > 1:  # two-shot: frame everyone, focus on the speaker
        xs = [c["face_pos"].x for c in CH.values()]
        face_pos = Vector((sum(xs) / len(xs), face_pos.y, face_pos.z))
        dist += 0.8 * (max(xs) - min(xs))
    cd = bpy.data.cameras.new(f"Cam{i}")
    cd.lens = s["lens"]
    cd.dof.use_dof = True
    cd.dof.focus_object = focus
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_ratio = 1.5  # oval, anamorphic-style bokeh
    cam = bpy.data.objects.new(f"Cam{i}", cd)
    sc.collection.objects.link(cam)
    fov = 2 * math.atan(18.0 / s["lens"])
    span = 2 * dist * math.tan(fov / 2)
    aim = face_pos + Vector((0, 0, 0.12 * span))  # face sits low → caption headroom on top
    dirv = Vector((math.sin(az), -math.cos(az), math.sin(el))).normalized()
    a, b = s["start_frame"] + 1, s["end_frame"]
    for f in list(range(a, b + 1, 2)) + [b]:
        u = (f - a) / max(1, b - a)
        d = dist * (1 - s["push"] * u)
        jitter = Vector((math.sin(f * 0.21) + 0.5 * math.sin(f * 0.53 + 1.0), 0.0,
                         math.sin(f * 0.17 + 2.0) + 0.5 * math.sin(f * 0.41))) * 0.003 * dist
        cam.location = aim + dirv * d + jitter
        look_at(cam, aim)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    marker = sc.timeline_markers.new(f"S{i}", frame=a)
    marker.camera = cam
    cams.append((cam, a, b))

# --- render settings ---------------------------------------------------------
sc.render.engine = EEVEE
sc.eevee.taa_render_samples = plan["samples"]
sc.render.resolution_x, sc.render.resolution_y = plan["resolution"]
sc.render.resolution_percentage = plan.get("resolution_percentage", 100)
sc.render.fps = fps
sc.frame_start, sc.frame_end = 1, n
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "8"
sc.camera = cams[0][0]

if mode == "stills":
    Path(plan["out_stills"]).mkdir(parents=True, exist_ok=True)
    for i, (cam, a, b) in enumerate(cams):
        sc.camera = cam
        sc.frame_set((a + b) // 2)
        sc.render.filepath = str(Path(plan["out_stills"]) / f"shot_{i:02d}.png")
        bpy.ops.render.render(write_still=True)
else:
    Path(plan["out_frames"]).mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(Path(plan["out_frames"])) + "/"
    sc.render.use_overwrite = False  # resume after a crash: keep frames already on disk
    bpy.ops.render.render(animation=True)
print("render_plan done")
