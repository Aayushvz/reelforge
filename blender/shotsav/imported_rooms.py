"""The three imported rooms (Cozy gaming room, Gaming den, Neon tunnel) as Shots-AV backdrops.

The authored models come from the owner's source files (blender/imported.py SETS: SRC_ROOT, override with
REELFORGE_IMPORTS). backdrop(set_id, preset, coll) appends a room into the current scene, scales and turns it to
real-world metres facing -Y as blender/import_set.py did, moves its standing mark to just behind the hero's chair,
clears whatever sits where the desk and the hero go, scales the authored practical lights, and packs the textures
so the built room file stands on its own. Returns the preset (world, haze, exposure). Source scripts never run.
"""
import math
import runpy
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

LIB = runpy.run_path(str(Path(__file__).resolve().parents[1] / "imported.py"))
SETS = LIB["SETS"]
BEHIND = 1.2  # the room's standing mark lands this far behind the hero, so its furniture frames him
DESK_ZONE = ((-1.3, 1.3), (-1.2, 0.7), (-0.1, 1.9))  # Shots-AV coordinates: the desk, the chair and the hero
CAMERA_SIDE = ((-1.6, 1.6), (-4.0, 0.7), (-0.1, 3.0))  # where the cameras stand and look from: keep it clear
TURN = {"neon_tunnel": 90.0}  # degrees: the tunnel's corridor runs away from the camera, not across it


def _inside(o, zone):
    corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return all(lo <= min(v[i] for v in corners) and max(v[i] for v in corners) <= hi for i, (lo, hi) in enumerate(zone))


def _blocks_view(o):
    """A movable piece (under 4 m on every side) touching the camera side of the desk: it would hide the hero."""
    corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = [min(v[i] for v in corners) for i in range(3)]
    hi = [max(v[i] for v in corners) for i in range(3)]
    small = max(h - l for l, h in zip(lo, hi)) < 4.0
    return small and all(lo[i] < CAMERA_SIDE[i][1] and hi[i] > CAMERA_SIDE[i][0] for i in range(3))


def _clear_sightlines(pieces):
    """Remove every piece a camera would see in front of the hero or the buddy: rays from the camera positions the
    angle library uses (around the desk, 1-3.5 m out, from below to well above) to the faces and the chest."""
    targets = [Vector((0, 0, 1.18)), Vector((0, -0.1, 0.92)), Vector((-0.3, -0.36, 0.86))]
    def encloses(o):  # a room shell or a tunnel surrounds the hero: it frames him, it never blocks him
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return all(min(v[i] for v in corners) < targets[0][i] < max(v[i] for v in corners) for i in range(3))
    keep = {o.name for o in pieces if not encloses(o)}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    removed = 0
    for _ in range(4):  # a removal can uncover the next piece behind it
        hit_names = set()
        for az in range(-80, 50, 10):
            for el in (-8, 6, 20, 38):
                for d in (1.2, 2.2, 3.5):
                    for t in targets:
                        a, e = math.radians(az), math.radians(el)
                        cam = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
                        ray = t - cam
                        ok, _loc, _n, _i, ob, _m = sc.ray_cast(depsgraph, cam, ray.normalized(), distance=ray.length - 0.05)
                        if ok and ob is not None and ob.name in keep:
                            hit_names.add(ob.name)
        if not hit_names:
            break
        for n in hit_names:
            o = bpy.data.objects.get(n)
            if o is not None:
                bpy.data.objects.remove(o, do_unlink=True)
                removed += 1
        depsgraph = bpy.context.evaluated_depsgraph_get()
    return removed


def backdrop(set_id, preset, coll):
    spec = SETS[set_id]
    pr = spec["presets"][preset or next(iter(spec["presets"]))]
    src = LIB["SRC_ROOT"] / spec["src"]
    if not src.exists():
        raise FileNotFoundError(f"{set_id}: source file missing: {src} (set REELFORGE_IMPORTS to its folder)")
    with bpy.data.libraries.load(str(src), link=False) as (data_from, data_to):  # the file's scene, as authored
        data_to.scenes = [data_from.scenes[0]]
    src_scene = data_to.scenes[0]
    scene_objs = list(src_scene.objects)  # only what the source scene shows (files also hold unused objects)
    objs = []
    for o in scene_objs:
        if o.type == "CAMERA" or (o.hide_render and o.type != "EMPTY"):
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        coll.objects.link(o)
        if o.animation_data:
            o.animation_data_clear()
        objs.append(o)
    bpy.data.scenes.remove(src_scene)  # its objects now live in the room's collection
    xf = spec["xform"]
    s, rz = xf["scale"], math.radians(xf["rot_z"] + TURN.get(set_id, 0.0))
    m = Matrix.Rotation(rz, 4, "Z") @ Matrix.Scale(s, 4)
    mark = m @ Vector(spec["mark_a"])
    root = bpy.data.objects.new(f"Imported_{set_id}", None)
    coll.objects.link(root)
    for o in objs:
        if o.parent is None:  # top-level: its local transform is its placement (matrix_world isn't evaluated yet)
            mw = o.matrix_basis.copy()
            o.parent = root
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_world = mw
    root.matrix_world = Matrix.Translation(Vector((-mark.x, -mark.y + BEHIND, -mark.z))) @ m  # mark on the floor
    bpy.context.view_layer.update()
    for o in list(root.children_recursive):
        if o.type == "LIGHT":
            o.data.energy *= (s * s if o.data.type != "SUN" else 1.0) * pr.get("practicals", 1.0)
        elif o.type == "MESH" and _inside(o, DESK_ZONE):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    print(f"imported room {set_id}: cleared {_clear_sightlines([o for o in root.children_recursive if o.type == 'MESH'])}"
          " pieces from the cameras' sightlines")
    for im in bpy.data.images:  # the built room file must not depend on the source folder
        if im.source == "FILE" and not im.packed_file and im.filepath:
            try:
                im.pack()
            except RuntimeError as e:
                print(f"WARNING {set_id}: could not pack {im.name}: {e}")
    return pr
