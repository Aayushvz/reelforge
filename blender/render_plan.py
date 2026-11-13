"""Render a reelforge render_plan.json inside an environment .blend.
Run: blender -b <env.blend> --factory-startup --python-exit-code 1 -P blender/render_plan.py -- <plan.json> <stills|full|profile>"""
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_rig as rig  # noqa: E402
import looks  # noqa: E402
from bl_common import look_at  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
plan = json.loads(Path(args[0]).read_text(encoding="utf-8"))
mode = args[1] if len(args) > 1 else "full"
sc = bpy.context.scene
fps, n = plan["fps"], plan["n_frames"]
LOOK = looks.get(plan.get("look"))
if plan.get("room_view") and bpy.data.objects.get("RoomPivot"):  # shots-av: the part of the room behind the desk
    from shotsav import rooms as _rooms
    _rooms.apply_view(plan.get("room_view"))

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
    others_x = [bpy.data.objects[c["mark"]].location.x for c in plan["characters"] if c is not char]
    if LOOK.BODY_CHEAT and others_x:  # open the body toward the other character (facing is -Y)
        root.rotation_euler.z = math.copysign(LOOK.BODY_CHEAT, others_x[0] - root.location.x)
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
                        "objects": list(coll.objects), "head_h": 0.43 * head_k,
                        "min_head": float(objs["FaceAnchor"].get("min_head", 0.0)) if "FaceAnchor" in objs else 0.0,
                        "elbows": {k: objs[k] for k in ("ElbowL", "ElbowR") if k in objs},
                        # shots-av: the framing height includes hair (the reference measures head with hair)
                        "frame_h": float(objs["FaceAnchor"].get("frame_height", 0.43 * head_k))
                        if "FaceAnchor" in objs else 0.43 * head_k,
                        "objs": objs, "props": char.get("props", {}), "stepped": set(char.get("stepped", [])),
                        "measure": char.get("measure", "")}


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
            return sh.get("speaker") or sh["subject"]
    return None


for name, c in CH.items():  # custom-prop tracks from the engine (shots-av: PoseCtrl, BuddyCtrl), one value a frame
    for obj_name, tracks in c["props"].items():
        obj = c["objs"].get(obj_name)
        if obj is None:
            continue
        for prop, values in tracks.items():
            key_track(obj, prop, values)
            if prop in c["stepped"] and obj.animation_data and obj.animation_data.action:
                for fc in obj.animation_data.action.fcurves:
                    if fc.data_path == f'["{prop}"]':
                        for k in fc.keyframe_points:
                            k.interpolation = "CONSTANT"


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
            yaw = math.copysign(LOOK.LISTEN_YAW, dx)
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
        tint = TINT * LOOK.MOOD_TINT[name]
        col = [b + (m - b) * tint for b, m in zip(base_c, p[ck])]
        d = LOOK.DESATURATE.get(name, 0.0)
        ld.color = [c + (max(col) - c) * d for c in col]
        ld.energy = base_w * p[wk] / calm[wk] * LOOK.LIGHT_SCALE[name]
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


def classic_camera(i, s):
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
    return cam, a, b


MAX_DIST = {"wide": 2.6, "two": 2.6, "medium": 2.4, "closeup": 2.2, "ecu": 2.0,  # stay inside the rooms
            "av_hero_34": 4.0, "av_hero_front": 4.0, "av_buddy": 4.0, "av_wide_34": 4.0, "av_wide_front": 4.0}


def rig_camera(i, s):
    """camera_rig.py: framing from the head size, an eased move, seeded sway, a key on every frame."""
    w, h = plan["resolution"]
    subj = CH.get(s["subject"]) or next(iter(CH.values()))
    others = [c for c in CH.values() if c is not subj]
    kind = s["kind"] if s["kind"] in rig.FRAMING else "medium"
    if kind == "two" and not others:
        kind = "wide"
    eye = subj["focus"].matrix_world.translation.copy()
    if others:  # stand on the other speaker's side; leave looking room in front of the subject
        side = 1.0 if others[0]["face_pos"].x > subj["face_pos"].x else -1.0
    else:
        side = 1.0 if s.get("seed", 0) % 2 else -1.0
    room = 0.05 * side if others and kind in ("closeup", "medium", "wide") else 0.0
    if others and kind in ("av_wide_34", "av_wide_front"):  # the buddy lands lower left, the monitor cut at the right
        room = 0.09 * side
    av = kind in rig.AV_KINDS
    height = subj["frame_h"] if av else subj["head_h"]
    if kind == "two":  # look down the line of both speakers: listener near and soft, speaker sharp
        eye = Vector(rig.two_shot_aim(tuple(eye), tuple(others[0]["focus"].matrix_world.translation)))
    base = rig.base_pose(kind, tuple(eye), height, w, h, side, s.get("az_pick", 0.5), room,
                         s.get("lens") or None, 0.0 if kind == "two" or av else subj["min_head"], s.get("framing") or None)
    base["dist"] = min(base["dist"], MAX_DIST[kind])
    con, base2 = s.get("connect") or {}, None
    if con.get("to") in CH:  # shots-av connected move: the second framing the camera arcs into
        o = CH[con["to"]]
        side2 = 1.0 if subj["face_pos"].x > o["face_pos"].x else -1.0
        base2 = rig.base_pose("av_buddy", tuple(o["focus"].matrix_world.translation), o["frame_h"], w, h, side2, 0.5,
                              0.0, None, 0.0, con.get("framing") or None)
        base2["dist"] = min(base2["dist"], MAX_DIST["av_buddy"])
    cd = bpy.data.cameras.new(f"Cam{i}")
    cd.lens = base["lens"]
    cd.dof.use_dof = True
    cd.dof.focus_object = subj["focus"]
    cd.dof.aperture_fstop = s.get("fstop") or base["fstop"]
    cd.dof.aperture_blades, cd.dof.aperture_ratio = 7, 1.0
    cam = bpy.data.objects.new(f"Cam{i}", cd)
    sc.collection.objects.link(cam)
    a, b = s["start_frame"] + 1, s["end_frame"]
    move, prev = s.get("move") or "static", None
    for f in range(a, b + 1):
        u = (f - a) / max(1, b - a)
        p = rig.pose(base, move, u, s.get("move_params"), s.get("ease", 0.35))
        tc = rig.smoothstep((f - a - con.get("at", 0)) / max(1, con.get("frames", 18))) if base2 else 0.0
        if base2:
            p = rig.connect_pose(p, rig.pose(base2, "static", 0.0), tc)
        (dx, dy, dz), (pitch, yaw, roll) = rig.handheld(f, fps, s.get("seed", 0), s.get("handheld", 0.0), b - a + 1, a)
        cam.location = Vector(p["pos"]) + Vector((dx, dy, dz))
        q = (Vector(p["aim"]) - cam.location).to_track_quat("-Z", "Y")
        q = q @ Euler((pitch, yaw, roll + p["roll"])).to_quaternion()  # sway in the camera's own axes
        cam.rotation_euler = q.to_euler("XYZ", prev) if prev else q.to_euler("XYZ")
        prev = cam.rotation_euler.copy()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        if base2:  # focus travels with the move, from the subject to the buddy
            fwd = q @ Vector((0.0, 0.0, -1.0))
            d0 = (subj["focus"].matrix_world.translation - cam.location).dot(fwd)
            d1 = (CH[con["to"]]["focus"].matrix_world.translation - cam.location).dot(fwd)
            cd.dof.focus_object = None
            cd.dof.focus_distance = d0 + (d1 - d0) * tc
            cd.dof.keyframe_insert("focus_distance", frame=f)
            cd.lens = p["lens"]
            cd.keyframe_insert("lens", frame=f)
        rack = s.get("rack") or {}
        if rack and rack.get("from") in CH and rack.get("to") in CH:  # pull focus from one character to the other
            fwd = q @ Vector((0.0, 0.0, -1.0))
            d0 = (CH[rack["from"]]["focus"].matrix_world.translation - cam.location).dot(fwd)
            d1 = (CH[rack["to"]]["focus"].matrix_world.translation - cam.location).dot(fwd)
            t = rig.smoothstep((f - a - rack.get("at", 0)) / max(1, rack.get("frames", 10)))
            cd.dof.focus_object = None
            cd.dof.focus_distance = d0 + (d1 - d0) * t
            cd.dof.keyframe_insert("focus_distance", frame=f)
        if move == "slow_zoom":
            cd.lens = p["lens"]
            cd.keyframe_insert("lens", frame=f)
    return cam, a, b


for i, s in enumerate(plan["shots"]):
    cam, a, b = (rig_camera if LOOK.USE_RIG else classic_camera)(i, s)
    marker = sc.timeline_markers.new(f"S{i}", frame=a)
    marker.camera = cam
    cams.append((cam, a, b))

MEASURE = []


def measure_shot(i, cam):
    """Frame fractions (origin top-left) of each character's measured part and eyes, for the match pass."""
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    out = {"shot": i, "kind": plan["shots"][i]["kind"], "chars": {}}
    for name, c in CH.items():
        part = c["measure"]
        if not part:
            continue
        pts = []
        for o in c["objects"]:
            if o.type != "MESH" or (part == "head" and not o.name.split(":")[-1].startswith(("AV_Head", "AV_Hair",
                                                                                              "AV_Ear", "AV_Curl"))):
                continue
            if part == "body" and "Shadow" in o.name:
                continue
            ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
            for v in ev.to_mesh().vertices:
                pts.append(world_to_camera_view(sc, cam, o.matrix_world @ v.co))
            ev.to_mesh_clear()
        if not pts:
            continue
        eye = world_to_camera_view(sc, cam, c["focus"].matrix_world.translation)
        xs, ys = [p.x for p in pts], [1.0 - p.y for p in pts]
        out["chars"][name] = {"top": round(min(ys), 4), "bottom": round(max(ys), 4),
                              "height": round(max(ys) - min(ys), 4), "left": round(min(xs), 4),
                              "right": round(max(xs), 4), "centre_x": round((min(xs) + max(xs)) / 2, 4),
                              "centre_y": round((min(ys) + max(ys)) / 2, 4), "eyes": round(1.0 - eye.y, 4),
                              "width": round(max(xs) - min(xs), 4)}
    return out


# --- render settings (owned by the look) ---------------------------------------
LOOK.apply_scene(sc, plan, list(CH.values()))
sc.camera = cams[0][0]

if mode == "profile":  # where a frame's time goes before any pixel is rendered: animation + mesh evaluation
    for f in (10, 11, 12, 13, 14, 15):
        t0 = time.time()
        sc.frame_set(f)
        bpy.context.view_layer.update()
        print(f"EVAL frame {f} {time.time() - t0:.2f}s")
elif mode == "bench":  # time chosen frames of the real reel: the plan's bench_frames -> out_frames/bench_NNNN.png
    Path(plan["out_frames"]).mkdir(parents=True, exist_ok=True)
    for f in plan.get("bench_frames", []):
        t0 = time.time()
        sc.frame_set(f)
        sc.camera = next(c for c, a, b in cams if a <= f <= b) if cams else sc.camera
        sc.render.filepath = str(Path(plan["out_frames"]) / f"bench_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"BENCH {f} {time.time() - t0:.2f}s")
elif mode == "stills":
    Path(plan["out_stills"]).mkdir(parents=True, exist_ok=True)
    only = plan.get("only_shots")
    for i, (cam, a, b) in enumerate(cams):
        if only is not None and i not in only:
            continue
        t0 = time.time()
        engine = LOOK.shot_settings(sc, plan, plan["shots"][i])
        sc.camera = cam
        sc.frame_set((a + b) // 2)
        sc.render.filepath = str(Path(plan["out_stills"]) / f"shot_{i:02d}.png")
        bpy.ops.render.render(write_still=True)
        if plan.get("measure"):
            MEASURE.append(measure_shot(i, cam))
        print(f"STILL {i} {plan['shots'][i]['kind']} {engine} {time.time() - t0:.2f}s")
else:
    Path(plan["out_frames"]).mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(Path(plan["out_frames"])) + "/"
    sc.render.use_overwrite = False  # resume after a crash: keep frames already on disk
    if LOOK.PER_SHOT:  # each shot on its own: close-ups and wides may use different engines
        for i, (cam, a, b) in enumerate(cams):
            t0 = time.time()
            engine = LOOK.shot_settings(sc, plan, plan["shots"][i])
            sc.frame_start, sc.frame_end = a, b
            bpy.ops.render.render(animation=True)
            print(f"SHOT {i} {plan['shots'][i]['kind']} {engine} frames {a}-{b} {time.time() - t0:.1f}s")
        sc.frame_start, sc.frame_end = 1, n
    else:
        bpy.ops.render.render(animation=True)
if MEASURE:
    (Path(plan["out_stills"]) / "measure.json").write_text(json.dumps(MEASURE, indent=1), encoding="utf-8")
print("render_plan done")
