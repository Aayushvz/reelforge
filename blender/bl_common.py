"""Blender-side helpers (runs inside Blender's Python; stdlib + bpy only)."""
import bmesh
import bpy
from mathutils import Vector


def material(name, color, rough=0.5, sss=0.0, sheen=0.0, coat=0.0, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    b.inputs["Subsurface Scale"].default_value = 0.02
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1.0)
        b.inputs["Emission Strength"].default_value = emit
    return m


def code_screen_material(name, color, strength=3.0):
    """Emissive 'code lines' screen: Brick Texture rows read as lines of code. Node named 'Code'."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.name = "Code"
    br.inputs["Color1"].default_value = (*color, 1.0)
    br.inputs["Color2"].default_value = (color[0] * 0.5, color[1] * 0.5, color[2] * 0.5, 1.0)
    br.inputs["Mortar"].default_value = (0.01, 0.012, 0.02, 1.0)
    br.inputs["Scale"].default_value = 6.0
    br.inputs["Mortar Size"].default_value = 0.03
    br.inputs["Brick Width"].default_value = 0.35
    br.inputs["Row Height"].default_value = 0.08
    em.inputs["Strength"].default_value = strength
    nt.links.new(br.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


def _finish(name, bm, coll, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if mat:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def box(name, center, size, coll, mat=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _finish(name, bm, coll, mat, smooth=False)


def ellipsoid(name, center, radii, coll, mat=None, segs=32, subd=1):
    """Unit sphere mesh; position/size live on the object so drivers can scale it."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=1.0)
    o = _finish(name, bm, coll, mat)
    o.location = center
    o.scale = radii
    if subd:
        mod = o.modifiers.new("Subd", "SUBSURF")
        mod.levels = mod.render_levels = subd
    return o


def empty(name, loc, coll, parent=None):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "PLAIN_AXES"
    o.location = loc
    coll.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
