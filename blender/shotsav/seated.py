"""Sit an imported, realistic character (Matt, Freya, Mina) at the Shots-AV desk.

Pose only: no geometry, texture or shape key is touched (CLAUDE.md). Works in world space, so one routine serves the
three rigs; each character's bone names come from blender/imported.py ("seat"):
- hips: the control that carries the upper body (CC4 CC_Base_Hip, Rigify torso, Auto-Rig Pro c_root.x)
- legs: per side, ("fk", thigh, shin, foot) to aim plain bones, or ("ik", thigh, foot_control) where the rig's IK
  bends the knee toward its forward pole once the foot control is planted
sit(objs, seat, slot) runs in render_plan.py after the character is linked and placed. slot "you" takes the hero's
chair (Mark_A, the origin); slot "guest" brings its own chair, which rides along with CHAR_root.
"""
import bpy
from mathutils import Matrix, Vector

SEAT_TOP = 0.515  # the hero's chair (rooms.py: ChairSeat centre 0.48, 0.07 thick)
HIP_ABOVE_SEAT = 0.085  # the hip joint sits this far above the cushion
HIP_BACK = 0.11  # the hip joint's y: toward the backrest (the seat spans y -0.16..0.28; facing is -Y)
KNEE_DROP = 0.02
ANKLE_Z = 0.09
# Hands on the desk, in the character's own frame (x out to its side, -y forward, z up). HAND_IN: the hand's x as a
# share of the shoulder's (in from the shoulder, toward the keyboard); HAND_Y: how far forward of the hip joints.
HAND_IN, HAND_Y, HAND_Z = 0.75, -0.36, 0.775  # the desk top is 0.74; the near edge is at y -0.145
ELBOW_POLE = (0.55, 0.45, -1.0)  # elbows bend down, back and a little out
GUEST = {"loc": (-1.05, -0.32, 0.0), "rot_z": 0.40}  # a second chair past the desk's end, turned toward the hero


def _update():
    bpy.context.view_layer.update()


def _world(arm, v):
    return arm.matrix_world @ v


def _move(arm, pb, delta_world):
    """Translate a pose bone by a world-space offset."""
    d = arm.matrix_world.to_3x3().inverted() @ delta_world
    pb.matrix = Matrix.Translation(d) @ pb.matrix
    _update()


def _aim(arm, pb, target_world, ref=None):
    """Swing a pose bone about its head so the point ref (armature space; default its tail) heads for target."""
    inv = arm.matrix_world.inverted()
    h = pb.head.copy()
    ref = pb.tail.copy() if ref is None else ref
    q = (ref - h).normalized().rotation_difference(((inv @ target_world) - h).normalized())
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    _update()


def _chair(coll, root):
    """The guest's own chair, a twin of the hero's, parented to its CHAR_root."""
    mat = bpy.data.materials.get("Chair") or bpy.data.materials.new("GuestChair")
    for name, size, loc in (("GuestSeat", (0.46, 0.44, 0.07), (0, 0.06, 0.48)),
                            ("GuestBack", (0.44, 0.06, 0.46), (0, 0.27, 0.80)),
                            ("GuestPost", (0.05, 0.05, 0.44), (0, 0.06, 0.22))):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        o = bpy.context.active_object
        o.name, o.scale = name, size
        bpy.ops.object.transform_apply(scale=True)
        bev = o.modifiers.new("Soft", "BEVEL")
        bev.width, bev.segments = 0.02, 3
        o.data.materials.append(mat)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.parent = root


def sit(objs: dict, seat: dict, slot: str = "you", coll=None) -> None:
    root = objs["CHAR_root"]
    arm = next(o for o in objs.values() if o.type == "ARMATURE" and seat["hips"] in o.pose.bones)
    if slot == "guest":
        root.location = Vector(GUEST["loc"])
        root.rotation_euler = (0.0, 0.0, GUEST["rot_z"])
        if coll is not None:
            _chair(coll, root)
    _update()
    for owner, prop, value in seat.get("switches", []):  # e.g. IK on the legs
        arm.pose.bones[owner][prop] = value
    # 1. the upper body down onto the seat: measured at the hip joints (the thighs' heads)
    sides = seat["legs"]
    hip_w = sum((_world(arm, arm.pose.bones[s[1]].head) for s in sides), Vector()) / len(sides)
    target = root.matrix_world @ Vector((0.0, HIP_BACK, SEAT_TOP + HIP_ABOVE_SEAT))
    _move(arm, arm.pose.bones[seat["hips"]], Vector((target.x - hip_w.x, target.y - hip_w.y, target.z - hip_w.z)))
    # 2. legs: thighs forward, shins down, feet flat
    fwd = root.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))
    floor = root.matrix_world.translation.z
    for s in sides:
        thigh = arm.pose.bones[s[1]]
        h = _world(arm, thigh.head)
        if s[0] == "fk":  # aim joint to joint: CC4 thigh and calf bones stop short (twist bones fill the rest)
            _, th, sh, ft = s
            shin, foot = arm.pose.bones[sh], arm.pose.bones[ft]
            l1, l2 = (shin.head - thigh.head).length, (foot.head - shin.head).length
            l1, l2 = l1 * arm.matrix_world.to_scale().z, l2 * arm.matrix_world.to_scale().z
            knee = h + fwd * l1 - Vector((0, 0, KNEE_DROP))
            ankle = knee + fwd * 0.05 - Vector((0, 0, max(0.1, (l2 * l2 - 0.0025) ** 0.5)))
            _aim(arm, thigh, knee, shin.head.copy())
            _aim(arm, shin, ankle, foot.head.copy())
            toe = _world(arm, foot.head) + fwd * 0.14 - Vector((0, 0, 0.05))
            _aim(arm, foot, toe)
        else:  # IK legs: plant the foot control; the knee bends toward the rig's forward pole
            _, th, ctl = s
            ankle = h + fwd * (thigh.length * arm.matrix_world.to_scale().z + 0.05)
            ankle.z = floor + ANKLE_Z
            pb = arm.pose.bones[ctl]
            _move(arm, pb, ankle - _world(arm, pb.head))
    # 3. arms: upper arms down by the sides, forearms forward, hands resting on the desk
    for side, (upper, fore, hand) in (seat.get("arms") or {}).items():
        _rest_arm(arm, objs, root, side, upper, fore, hand)
    _update()


def _rest_arm(arm, objs, root, side, upper, fore, hand):
    """Two-bone reach: aim the upper arm at the solved elbow; turn the forearm (steered by ElbowL/ElbowR through Copy
    Rotation) onto the hand target by rotating that empty, as a delta so render_plan's talk beats ride on top."""
    pu, pf, ph = arm.pose.bones[upper], arm.pose.bones[fore], arm.pose.bones[hand]
    s = _world(arm, pu.head)
    l1 = (_world(arm, pf.head) - s).length
    l2 = (_world(arm, ph.head) - _world(arm, pf.head)).length
    rw = root.matrix_world
    rot = rw.to_3x3().normalized()
    local_s = rw.inverted() @ s
    hip_y = HIP_BACK
    sign = 1.0 if side == "l" else -1.0  # the character's left is +x in its own frame
    target = rw @ Vector((local_s.x * HAND_IN, hip_y + HAND_Y, HAND_Z))
    d = target - s
    dist = min(d.length, (l1 + l2) * 0.995)
    dn = d.normalized()
    pole = rot @ Vector((ELBOW_POLE[0] * sign, ELBOW_POLE[1], ELBOW_POLE[2]))
    pole = (pole - dn * pole.dot(dn)).normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = max(0.0, l1 * l1 - a * a) ** 0.5
    elbow = s + dn * a + pole * h
    hand_at = s + dn * dist
    _aim(arm, pu, elbow, pf.head.copy())
    e = objs.get("ElbowL" if side == "l" else "ElbowR")
    if e is None:  # no forearm steering: aim the bone itself
        _aim(arm, pf, hand_at, ph.head.copy())
        return
    cur = _world(arm, ph.head) - _world(arm, pf.head)
    q = cur.normalized().rotation_difference((hand_at - elbow).normalized())
    pm = e.parent.matrix_world.to_3x3().normalized() if e.parent else Matrix.Identity(3)
    ql = (pm.inverted() @ q.to_matrix() @ pm).to_quaternion()  # the world turn, in the empty's parent frame
    cur_local = (e.delta_rotation_euler.to_quaternion() @ e.rotation_euler.to_quaternion())
    e.delta_rotation_euler = (ql @ cur_local).to_euler()
    e.rotation_euler = (0.0, 0.0, 0.0)
    _update()
