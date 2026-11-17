"""Face-visibility guarantee for every shot: nothing may cover the speaker's face, and captions may not sit on it.

For a shot's camera, rays go from the lens to points on the subject's face (its mesh near the eye focus, the side
facing the camera) at the shot's first, middle and last frame, so the move is covered. A ray that first hits
something other than the subject is blocked. Score = the share of rays that reach the face.

render_plan.py builds each shot's camera, asks `score_shot`, and when the face is under MIN_CLEAR (or under the
caption band) re-builds the camera with small changes (`variants`), keeping the first that passes; failing that it
hides the small props that block for that shot's frames only (a film "cheat"), and failing that keeps the best.
Room shells, haze volumes and anything that surrounds the face frame the shot; they never count as blockers.
"""
import re

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

MIN_CLEAR = 0.9
MAX_POINTS = 64
SMALL_PROP = 0.9  # m: a blocker whose bounding box is smaller than this may be hidden for one shot
# set pieces (by the first word of the object's name) are never hidden, unless the name ends in a small prop's word:
# "MonNeck" stays (part of the monitor), "DeskLamp" may go (a lamp on the desk)
NEVER_HIDE = {"mon", "monitor", "screen", "desk", "table", "wall", "floor", "ceiling", "window", "sofa", "bed",
              "counter", "chair", "keyboard", "sky", "street", "shelf", "sill", "door", "exit", "transom",
              "laptop", "c", "cart", "ledge", "bench", "nightstand", "headboard"}
SMALL_PROPS = {"lamp", "plant", "mug", "cup", "pen", "mic", "microphone", "book", "books", "figure", "toy", "candle",
               "speaker", "vase", "frame", "poster", "bottle", "can", "phone", "headphones", "light", "pot", "cactus",
               "clock", "card", "cards", "note", "notes", "plushie", "cat", "lavalamp", "bulb", "stand", "jar"}


def _encloses(o, p):
    corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return all(min(v[i] for v in corners) - 0.05 < p[i] < max(v[i] for v in corners) + 0.05 for i in range(3))


def _size(o):
    corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return max((max(v[i] for v in corners) - min(v[i] for v in corners)) for i in range(3))


def face_points(subj, cam_pos, depsgraph):
    """World points on the subject's face that turn toward the camera (vertices near the eye focus)."""
    focus = subj["focus"].matrix_world.translation
    radius = 0.45 * subj.get("frame_h", 0.4)
    pts = []
    for o in subj["objects"]:
        if o.type != "MESH" or "shadow" in o.name.lower():
            continue
        ev = o.evaluated_get(depsgraph)
        me = ev.to_mesh()
        mw, nw = o.matrix_world, o.matrix_world.to_3x3()
        for v in me.vertices:
            p = mw @ v.co
            if (p - focus).length > radius:
                continue
            n = (nw @ v.normal).normalized()
            if n.dot((cam_pos - p).normalized()) > 0.25:
                pts.append(p.copy())
        ev.to_mesh_clear()
    if len(pts) > MAX_POINTS:
        step = len(pts) / MAX_POINTS
        pts = [pts[int(k * step)] for k in range(MAX_POINTS)]
    return pts or [focus.copy()]


def ray_visibility(sc, depsgraph, cam_pos, pts, own, ignore):
    """(share of points reached, {blocking object name: rays it blocked})."""
    seen, blockers = 0, {}
    for p in pts:
        ray = p - cam_pos
        dist = ray.length
        origin = cam_pos.copy()
        travelled = 0.0
        while True:  # step through ignored objects (room shells, haze, hidden props) to the first real hit
            ok, loc, _n, _i, ob, _m = sc.ray_cast(depsgraph, origin, ray.normalized(), distance=dist - travelled - 0.01)
            if not ok or ob is None:
                seen += 1
                break
            if ob.name in own:
                seen += 1  # the face itself (or its own hair/nose): visible
                break
            if ob.name in ignore or _encloses(ob, p):
                travelled += (loc - origin).length + 0.002
                origin = loc + ray.normalized() * 0.002
                if travelled >= dist - 0.01:
                    seen += 1
                    break
                continue
            blockers[ob.name] = blockers.get(ob.name, 0) + 1
            break
    return seen / max(1, len(pts)), blockers


def caption_overlap(sc, cam, pts, band):
    """Share of the face's height (in frame) that falls inside the caption band (fractions from the top)."""
    if not band:
        return 0.0
    ys = [1.0 - world_to_camera_view(sc, cam, p).y for p in pts]
    top, bottom = min(ys), max(ys)
    h = max(1e-6, bottom - top)
    inter = max(0.0, min(bottom, band[1]) - max(top, band[0]))
    return inter / h


def score_shot(sc, cam, a, b, subj, band=None, ignore=frozenset()):
    """Worst visibility over the shot's first, middle and last frame, the blockers, and the caption overlap."""
    own = {o.name for o in subj["objects"]}
    worst, blockers, cap = 1.0, {}, 0.0
    for f in sorted({a, (a + b) // 2, b}):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        cam_pos = cam.matrix_world.translation.copy()
        pts = face_points(subj, cam_pos, dg)
        vis, blk = ray_visibility(sc, dg, cam_pos, pts, own, ignore)
        worst = min(worst, vis)
        for k, v in blk.items():
            blockers[k] = blockers.get(k, 0) + v
        cap = max(cap, caption_overlap(sc, cam, pts, band))
    return {"score": round(worst, 3), "blockers": blockers, "caption": round(cap, 3)}


def passes(r):
    return r["score"] >= MIN_CLEAR and r["caption"] <= 0.35


def variants(s):
    """Small changes to try, in order: swing round the subject, raise or drop the camera, dolly in, and for a
    caption clash move the face away from the caption band."""
    fr = dict(s.get("framing") or {})
    out = []
    if fr.get("az"):
        a0, a1 = fr["az"]
        for d in (8, -8, 16, -16, 26):
            out.append(("swing %+d" % d, {**s, "framing": {**fr, "az": [a0 + d, a1 + d]}}))
        if "el" in fr:
            for d in (9, -7):
                out.append(("raise %+d" % d, {**s, "framing": {**fr, "el": fr["el"] + d}}))
        if "head" in fr:
            out.append(("dolly in", {**s, "framing": {**fr, "head": min(0.9, fr["head"] * 1.2)}}))
        if "eyes" in fr:
            out.append(("face lower", {**s, "framing": {**fr, "eyes": min(0.62, fr["eyes"] + 0.09)}}))
            out.append(("face higher", {**s, "framing": {**fr, "eyes": max(0.3, fr["eyes"] - 0.09)}}))
    else:
        for pick in (0.0, 1.0):
            out.append((f"az pick {pick}", {**s, "az_pick": pick}))
    return out


def hideable(names, characters):
    """Blockers small enough to hide for one shot; characters and set pieces (monitor, desk, walls) never are."""
    char_objs = {o.name for c in characters for o in c["objects"]}
    out = []
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None or n in char_objs:
            continue
        words = [w.lower() for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", n.split(".")[0]) if not w.isdigit()]
        if words and words[0] in NEVER_HIDE and words[-1] not in SMALL_PROPS:
            continue
        if _size(o) <= SMALL_PROP:
            out.append(o)
    return out


def hide_for_shot(objs, a, b):
    """Hide props in render for frames a..b only (keyed, so the rest of the reel keeps them)."""
    for o in objs:
        for f, v in ((a - 1, False), (a, True), (b, True), (b + 1, False)):
            o.hide_render = v
            o.keyframe_insert("hide_render", frame=max(0, f))
        o.hide_render = False


def remove_camera(cam):
    data = cam.data
    bpy.data.objects.remove(cam, do_unlink=True)
    if data.users == 0:
        bpy.data.cameras.remove(data)
