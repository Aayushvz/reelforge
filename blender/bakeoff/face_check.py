"""Automated face check (Phase 1 bake-off, later the per-character face gate).

Run: blender -b <char.blend> --python-exit-code 1 -P blender/bakeoff/face_check.py -- <out.json> [--strict]

Meshes are found by the custom property face_part on each object (head | teeth | tongue | eye | lid | lash |
brow); v1 characters without tags fall back to their object names. For every ARKit shape at 1.0, and the common
combinations, it measures in world space:
  * new intersections (vs. neutral) between teeth/tongue/eyes and the skin (head + lids): poke-through;
  * at eyeBlink = 1: the fraction of the eyeball's front surface covered by lids/skin (must be >= 0.98).
--strict exits 1 if anything fails."""
import json
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
OUT, STRICT = args[0], "--strict" in args
ctrl = bpy.data.objects["FaceCtrl"]
HH = float(bpy.data.objects["FaceAnchor"]["head_height"])
ARKIT = [k for k in ctrl.keys() if k[0].islower()]
V1_NAMES = {"HeadMesh": "head", "TeethUpper": "teeth", "TeethLower": "teeth", "Tongue": "tongue",
            "EyeLeft": "eye", "EyeRight": "eye", "LidUpperLeft": "lid", "LidUpperRight": "lid",
            "LidLowerLeft": "lid", "LidLowerRight": "lid"}


def part(o):
    return o.get("face_part") or V1_NAMES.get(o.name.split(".")[0])


PARTS = {}
for o in bpy.data.objects:
    if o.type in ("MESH", "CURVE") and not o.hide_render and part(o):
        PARTS.setdefault(part(o), []).append(o)
assert PARTS.get("head") and PARTS.get("eye"), f"need tagged head + eye meshes, found {list(PARTS)}"


def set_pose(values):
    for k in ARKIT:
        ctrl[k] = float(values.get(k, 0.0))
    ctrl.update_tag()
    bpy.context.view_layer.update()


def world_bvh(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0), verts


def hits(a, b):
    if not a or not b:
        return 0
    return len(world_bvh(a)[0].overlap(world_bvh(b)[0]))


def lid_coverage():
    """Share of forward-facing eyeball points whose ray toward the viewer (-Y) hits skin within reach."""
    skin, _ = world_bvh(PARTS["head"] + PARTS.get("lid", []))
    _, pts = world_bvh(PARTS["eye"])
    centre = sum(pts, Vector()) / len(pts)
    front = [p for p in pts if p.y < centre.y - 0.25 * (centre.y - min(q.y for q in pts))]
    covered = 0
    for p in front:
        hit = skin.ray_cast(p + Vector((0, -1e-4, 0)), Vector((0, -1, 0)), HH * 0.15)
        covered += hit[0] is not None
    return covered / max(1, len(front))


skin_parts = PARTS["head"] + PARTS.get("lid", [])
inner = {k: PARTS.get(k, []) for k in ("teeth", "tongue", "eye")}
set_pose({})
base = {k: hits(v, skin_parts) for k, v in inner.items()}

PAIRS = {
    "smile+jawOpen": {"mouthSmileLeft": 1, "mouthSmileRight": 1, "jawOpen": 1},
    "blink+squint": {"eyeBlinkLeft": 1, "eyeBlinkRight": 1, "eyeSquintLeft": 1, "eyeSquintRight": 1},
    "pucker+jawOpen": {"mouthPucker": 1, "jawOpen": 1},
    "funnel+jawOpen": {"mouthFunnel": 1, "jawOpen": 1},
    "smile+blink": {"mouthSmileLeft": 1, "mouthSmileRight": 1, "eyeBlinkLeft": 1, "eyeBlinkRight": 1},
    "press+close": {"mouthPressLeft": 1, "mouthPressRight": 1, "mouthClose": 1},
}
cases = {k: {k: 1.0} for k in ARKIT}
cases.update(PAIRS)
report, failures = {"baseline": base, "cases": {}}, []
for name, vals in cases.items():
    set_pose(vals)
    new = {k: max(0, hits(v, skin_parts) - base[k]) for k, v in inner.items() if v}
    row = {"poke_through": new}
    if vals.get("eyeBlinkLeft") == 1 and vals.get("eyeBlinkRight") == 1:
        row["lid_coverage"] = round(lid_coverage(), 3)
        if row["lid_coverage"] < 0.98:
            failures.append(f"{name}: lids cover {row['lid_coverage']:.0%} of the eye")
    bad = {k: n for k, n in new.items() if n > 0}
    if bad:
        failures.append(f"{name}: poke-through {bad}")
    report["cases"][name] = row
set_pose({})
report["failures"] = failures
report["verdict"] = "PASS" if not failures else "FAIL"
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print(f"face_check {report['verdict']}: {len(failures)} failures, {len(cases)} cases -> {OUT}")
for f in failures[:20]:
    print("  ", f)
if STRICT and failures:
    sys.exit(1)
