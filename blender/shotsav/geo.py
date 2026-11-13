"""Small mesh helpers for the Shots-AV assets (runs inside Blender). Low-poly on purpose: lofts and bevelled boxes,
flat-shaded where facets are the style (hair, jacket panels) and smooth with weighted normals elsewhere."""
import math

import bmesh
import bpy
from mathutils import Vector

from bl_common import material


def lin(color):
    """'#RRGGBB' (sRGB) or an RGB tuple (already linear) -> linear RGB tuple for Blender."""
    if not isinstance(color, str):
        return tuple(color)
    c = [int(color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def mix_hex(a, b, t):
    """Blend two sRGB hex colours in sRGB (what a designer's colour picker does)."""
    ca, cb = (int(a[i:i + 2], 16) for i in (1, 3, 5)), (int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def mat(name, color, rough=0.5, **kw):
    return material(name, lin(color), rough=rough, **kw)


def mesh(name, verts, faces, coll, m=None, smooth=False, parent=None):
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    for f in faces:
        try:
            bm.faces.new([bv[i] for i in f])
        except ValueError:  # a degenerate face from a collapsed ring
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    if m:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def loft(name, rings, coll, m=None, closed=True, caps=(True, True), smooth=False, parent=None):
    """Skin a list of rings (each a list of points, all the same length). closed=False lofts an open arc."""
    k = len(rings[0])
    verts = [tuple(p) for r in rings for p in r]
    faces = []
    for a in range(len(rings) - 1):
        for j in range(k if closed else k - 1):
            j2 = (j + 1) % k
            faces.append((a * k + j, a * k + j2, (a + 1) * k + j2, (a + 1) * k + j))
    if closed and caps[0]:
        faces.append(tuple(range(k)))
    if closed and caps[1]:
        faces.append(tuple((len(rings) - 1) * k + j for j in range(k)))
    return mesh(name, verts, faces, coll, m, smooth, parent)


def soften(o, width=0.003, segs=2, angle=30.0):
    """Bevel the hard edges so they catch light, and keep the flats flat (weighted normals)."""
    b = o.modifiers.new("Bevel", "BEVEL")
    b.width, b.segments, b.limit_method, b.angle_limit = width, segs, "ANGLE", math.radians(angle)
    if any(p.use_smooth for p in o.data.polygons):
        w = o.modifiers.new("Normals", "WEIGHTED_NORMAL")
        w.keep_sharp = True
    return o


def rbox(name, size, coll, m=None, bevel=0.003, loc=(0, 0, 0), origin=(0, 0, 0), parent=None, segs=2):
    """Bevelled box. `origin` shifts the mesh inside its object (in half-size units), so a finger segment can
    pivot at its knuckle: origin=(0, 1, 0) puts the +Y face at the object's origin."""
    sx, sy, sz = (s / 2 for s in size)
    ox, oy, oz = origin[0] * sx, origin[1] * sy, origin[2] * sz
    v = [(x * sx - ox, y * sy - oy, z * sz - oz) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    o = mesh(name, v, f, coll, m, smooth=True, parent=parent)
    o.location = loc
    return soften(o, min(bevel, 0.45 * min(size)), segs)


def frame(points, i, up):
    """Tangent, side and up vectors at point i of a path (up is a hint, e.g. the surface normal)."""
    a, b = points[max(i - 1, 0)], points[min(i + 1, len(points) - 1)]
    t = (Vector(b) - Vector(a)).normalized()
    side = t.cross(Vector(up))
    side = side.normalized() if side.length > 1e-6 else t.orthogonal().normalized()
    return t, side, side.cross(t).normalized()


def tube(name, pts, radius, coll, m=None, k=8, closed=False, smooth=True, parent=None, up=(0, 0, 1)):
    """Sweep a k-gon along a path. radius is a number or one per point."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    for i in range(n):
        if closed:
            t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
            side = t.cross(Vector(up)).normalized()
            upv = side.cross(t).normalized()
        else:
            t, side, upv = frame(pts, i, up)
        r = radius[i] if isinstance(radius, (list, tuple)) else radius
        rings.append([pts[i] + side * (r * math.cos(2 * math.pi * j / k)) + upv * (r * math.sin(2 * math.pi * j / k))
                      for j in range(k)])
    if closed:
        rings.append(rings[0])
    return loft(name, rings, coll, m, closed=True, caps=(not closed, not closed), smooth=smooth, parent=parent)


def ball(name, radii, coll, m=None, loc=(0, 0, 0), segs=20, smooth=True, parent=None, ico=0):
    """Ellipsoid as a unit sphere scaled on the object (drivers can scale it). ico>0 = faceted icosphere."""
    bm = bmesh.new()
    if ico:
        bmesh.ops.create_icosphere(bm, subdivisions=ico, radius=1.0)
    else:
        bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(6, segs // 2), radius=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    if m:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o.location, o.scale = loc, radii
    if parent is not None:
        o.parent = parent
    return o


def empty(name, loc, coll, parent=None):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type, o.empty_display_size = "PLAIN_AXES", 0.05
    o.location = loc
    coll.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def drive(owner, path, expr, variables, index=-1):
    """Scripted driver from custom properties. variables: {name: (object, property)}. Expressions stay inside
    Blender's simple-expression subset (min, max, abs, clamp, arithmetic) so they run without autoexec."""
    fc = owner.driver_add(path, index) if index >= 0 else owner.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    d.expression = expr
    for vname, (obj, prop) in variables.items():
        v = d.variables.new()
        v.name, v.type = vname, "SINGLE_PROP"
        v.targets[0].id = obj
        v.targets[0].data_path = f'["{prop}"]'
    return fc
