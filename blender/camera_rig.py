"""Camera maths for the cinema look: framing from head size, a library of eased moves, seeded handheld sway.

Pure Python (math only): unit-tested without Blender; render_plan.py adapts the poses to camera objects.
Conventions: metres, radians, +Z up, characters face -Y, the camera sits on the -Y side. A pose is a dict
{"pos": (x, y, z), "aim": (x, y, z), "roll": rad, "lens": mm}. `u` is the 0..1 position inside the shot."""
import math

SENSOR = 36.0  # mm, Blender's default sensor; sensor fit AUTO puts it on the frame's larger side

# shot kind -> framing: lens (mm), head height as a fraction of frame height, eye line (fraction from the top),
# f-stop, azimuth range (deg, toward the other speaker), elevation (deg).
# Portrait-first: nothing is wider than waist-up. Full-body shots expose stiff standing poses, bare floor and
# hands; faces and shoulders are where these characters hold up. Azimuths sit at or just outside the
# subject's own axis, so a body opened toward the other speaker reads as a three-quarter face with looking
# room, not a passport photo. "two" is a raking two-shot down the line of both speakers; it is only used when
# asked for (a camera override): with side-by-side standing characters the near body takes over the frame.
FRAMING = {
    "wide":    {"lens": 40, "head": 0.26, "eyes": 0.32, "fstop": 3.5, "az": (-6, 4),   "el": 2.0},
    "two":     {"lens": 40, "head": 0.20, "eyes": 0.32, "fstop": 2.2, "az": (64, 72),  "el": 2.0},
    "medium":  {"lens": 60, "head": 0.38, "eyes": 0.38, "fstop": 3.2, "az": (-8, 2),   "el": 2.0},
    "closeup": {"lens": 85, "head": 0.55, "eyes": 0.42, "fstop": 3.2, "az": (-8, 2),   "el": 1.5},
    "ecu":     {"lens": 110, "head": 0.78, "eyes": 0.42, "fstop": 4.0, "az": (-6, 2),  "el": 0.5},
    # Shots-AV (docs/prompts/03-shots-av-animation.md 5.1): the desk two-hander's five set-ups. Prompt 5.1 gives
    # azimuth "positive toward the monitor" (the hero's left); this table measures it toward the other speaker.
    # With the buddy on the hero's right, the hero set-ups are negated (av_hero_34: 5.1 says +28..+34, here
    # -34..-28, and the rig's side = -1 for the hero lands the camera on +X, the monitor side). The buddy's
    # other speaker (the hero) is on its +X, so av_buddy keeps 5.1's -8..-2. "head" is the share of frame height
    # of the subject's framing height (the hero's head with hair; the buddy's whole body).
    "av_hero_34":    {"lens": 85, "head": 0.46, "eyes": 0.52, "fstop": 1.8, "az": (-34, -28), "el": 4.0},
    "av_hero_front": {"lens": 85, "head": 0.46, "eyes": 0.54, "fstop": 2.0, "az": (-3, 3),    "el": -4.0},
    "av_buddy":      {"lens": 100, "head": 0.38, "eyes": 0.62, "fstop": 2.0, "az": (-8, -2),  "el": 4.0},
    "av_wide_34":    {"lens": 50, "head": 0.25, "eyes": 0.36, "fstop": 2.8, "az": (-18, -12), "el": 8.0},
    "av_wide_front": {"lens": 50, "head": 0.25, "eyes": 0.35, "fstop": 2.8, "az": (-3, 3),    "el": 6.0},
}
AV_KINDS = ("av_hero_34", "av_hero_front", "av_buddy", "av_wide_34", "av_wide_front")
SAFE_TOP, SAFE_BOTTOM = 0.14, 0.20  # 9:16 platform UI / caption bands to keep faces out of

# move -> default parameters (fractions of subject distance, degrees, metres)
MOVES = {
    "static":     {},
    "push_in":    {"amount": 0.08},
    "pull_out":   {"amount": 0.10},
    "orbit":      {"degrees": 12.0},
    "truck":      {"metres": 0.20},
    "drift":      {"metres": 0.045, "degrees": 1.5},
    "crane_down": {"metres": 0.30},
    "crane_up":   {"metres": 0.30},
    "slow_zoom":  {"amount": 0.12},
    "whip_pan":   {"degrees": 55.0},
    "pull_truck": {"amount": 0.12, "metres": 0.004},  # Shots-AV buddy singles: pull out while trucking sideways
}


def smoothstep(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def ease(u, strength=0.35):
    """0..1 -> 0..1, monotonic, exact at both ends. strength 0 = constant speed (cutting into a move that is
    already travelling), 1 = full ease-in-out (a move that starts and lands at rest)."""
    u = min(1.0, max(0.0, u))
    return (1.0 - strength) * u + strength * smoothstep(u)


def half_fov_tan(lens, width, height):
    """(tan of half the horizontal fov, tan of half the vertical fov) for a frame of width x height pixels."""
    big = (SENSOR / 2.0) / lens
    return (big, big * height / width) if width >= height else (big * width / height, big)


def distance_for(head_height, lens, head_fraction, width, height):
    """Camera distance at which a head of `head_height` metres fills `head_fraction` of the frame height."""
    _, tv = half_fov_tan(lens, width, height)
    return head_height / (2.0 * tv * head_fraction)


def frame_size(distance, lens, width, height):
    th, tv = half_fov_tan(lens, width, height)
    return 2.0 * distance * th, 2.0 * distance * tv


def base_pose(kind, eye_pos, head_height, width, height, side=1.0, az_pick=0.5, look_room=0.0,
              lens=None, min_head=0.0):
    """Framing for one shot: where the camera stands and what it aims at before any move.

    eye_pos: the subject's eye point. side: +1 puts the camera on the +X side of the subject (use the side of
    the other speaker, so the subject is seen from "inside" the conversation). az_pick 0..1 picks inside the
    kind's azimuth range. look_room: fraction of the frame width to leave in front of the subject's gaze
    (sign = gaze direction on X). For "two", pass eye_pos between the two faces (see two_shot_aim).
    min_head: the smallest head fraction this character may be framed at (its widest flattering shot);
    the eye line drops with it so the head keeps its headroom."""
    fr = FRAMING[kind]
    lens = lens or fr["lens"]
    head = max(fr["head"], min_head)
    eyes = max(fr["eyes"], min(0.42, 0.30 + 0.24 * head)) if head > fr["head"] else fr["eyes"]
    dist = distance_for(head_height, lens, head, width, height)
    ex, ey, ez = eye_pos
    fw, fh = frame_size(dist, lens, width, height)
    # eyes sit `eyes` from the top: aim below them by the distance from the eye line to the frame centre
    aim = (ex + look_room * fw, ey, ez - (0.5 - eyes) * fh)
    az = math.radians(fr["az"][0] + (fr["az"][1] - fr["az"][0]) * az_pick) * side
    el = math.radians(fr["el"])
    return {"aim": aim, "dist": dist, "az": az, "el": el, "lens": float(lens), "fstop": fr["fstop"], "kind": kind}


def two_shot_aim(speaker_eye, listener_eye, bias=0.35):
    """Aim point for the raking two-shot: between the faces, nearer the listener, which from the raking camera
    puts the two faces evenly left and right of centre."""
    return tuple(s * bias + l * (1.0 - bias) for s, l in zip(speaker_eye, listener_eye))


def _place(aim, dist, az, el):
    ce = math.cos(el)
    return (aim[0] + dist * math.sin(az) * ce, aim[1] - dist * math.cos(az) * ce, aim[2] + dist * math.sin(el))


def pose(base, move, u, params=None, ease_strength=0.35):
    """Camera pose at shot position u (0..1) for `move` applied to `base` (from base_pose)."""
    p = dict(MOVES.get(move, {}))
    p.update(params or {})
    k = float(p.get("intensity", 1.0))
    e = ease(u, ease_strength)
    c = e - 0.5  # centred: the framing in base_pose is the middle of the move
    aim, dist, az, el, lens, roll = list(base["aim"]), base["dist"], base["az"], base["el"], base["lens"], 0.0
    if move == "push_in":
        dist = base["dist"] * (1.0 + p["amount"] * k * (0.5 - e))
    elif move == "pull_out":
        dist = base["dist"] * (1.0 + p["amount"] * k * c)
    elif move == "pull_truck":
        dist = base["dist"] * (1.0 + p["amount"] * k * c)
        aim[0] += p["metres"] * k * c * (1.0 if base["az"] >= 0 else -1.0)
    elif move == "orbit":
        az += math.radians(p["degrees"]) * k * c * (1.0 if base["az"] >= 0 else -1.0)
    elif move == "truck":
        aim[0] += p["metres"] * k * c * (1.0 if base["az"] >= 0 else -1.0)
    elif move == "drift":
        aim[0] += p["metres"] * k * c
        aim[2] += p["metres"] * 0.35 * k * c
        az += math.radians(p["degrees"]) * k * c
    elif move in ("crane_down", "crane_up"):
        sign = 1.0 if move == "crane_down" else -1.0
        lift = p["metres"] * k * (1.0 - e) * sign  # ends on the base framing
        pos = _place(aim, dist, az, el)
        return {"pos": (pos[0], pos[1], pos[2] + lift), "aim": tuple(aim), "roll": 0.0, "lens": lens}
    elif move == "slow_zoom":
        lens = base["lens"] * (1.0 + p["amount"] * k * c)
    elif move == "whip_pan":  # a transition: the aim sweeps in from the side and lands on the subject
        fw = 2.0 * dist * math.tan(math.radians(p["degrees"]) * (1.0 - smoothstep(u)))
        aim[0] -= fw * 0.5 * (1.0 if base["az"] >= 0 else -1.0)
    return {"pos": _place(aim, dist, az, el), "aim": tuple(aim), "roll": roll, "lens": lens}


def _phases(seed, n):
    """n deterministic phases in 0..2pi from an integer seed (a small LCG: no random module state)."""
    x, out = (int(seed) * 2654435761 + 12345) & 0xFFFFFFFF, []
    for _ in range(n):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        out.append(x / 0xFFFFFFFF * 2.0 * math.pi)
    return out


def handheld(frame, fps, seed, amount, n_frames=None, start=0):
    """Low-frequency operator sway: ((dx, dy, dz) metres, (pitch, yaw, roll) radians).

    Band-limited (0.3-0.8 Hz), seeded, fades in/out over 0.4 s inside the shot. amount 0..1; at 1 the swing
    is about 0.4 degrees and 3 mm."""
    if amount <= 0.0:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    t = frame / float(fps)
    ph = _phases(seed, 12)
    freqs = (0.31, 0.47, 0.62, 0.79)

    def wave(o):
        return sum(math.sin(2.0 * math.pi * f * t + ph[o + i]) / (1.0 + i) for i, f in enumerate(freqs[:3])) / 1.83

    fade = 1.0
    if n_frames:
        edge = max(1.0, 0.4 * fps)
        fade = smoothstep(min(frame - start, start + n_frames - 1 - frame) / edge)
    a = amount * fade
    rot, mm = math.radians(0.4) * a, 0.003 * a
    return ((wave(0) * mm, wave(3) * mm * 0.5, wave(6) * mm), (wave(1) * rot, wave(4) * rot, wave(7) * rot * 0.5))


def screen_point(point, pos, aim, lens, width, height):
    """Where `point` lands in the frame: (x, y) as fractions, origin top-left. For framing checks."""
    fwd = [a - b for a, b in zip(aim, pos)]
    n = math.sqrt(sum(v * v for v in fwd))
    fwd = [v / n for v in fwd]
    rx, ry = fwd[1], -fwd[0]  # right = forward x up(0,0,1), in the XY plane
    rn = math.hypot(rx, ry) or 1.0
    right = (rx / rn, ry / rn, 0.0)
    up = (right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2],
          right[0] * fwd[1] - right[1] * fwd[0])
    d = [a - b for a, b in zip(point, pos)]
    z = sum(a * b for a, b in zip(d, fwd))
    x = sum(a * b for a, b in zip(d, right)) / z
    y = sum(a * b for a, b in zip(d, up)) / z
    th, tv = half_fov_tan(lens, width, height)
    return 0.5 + x / (2.0 * th), 0.5 - y / (2.0 * tv)


def aim_angles(pos, aim):
    """(yaw, pitch) of the view direction, for smoothness checks."""
    d = [a - b for a, b in zip(aim, pos)]
    return math.atan2(d[0], d[1]), math.atan2(d[2], math.hypot(d[0], d[1]))


def max_angular_accel(poses, fps):
    """Largest frame-to-frame change of angular velocity (deg/s^2) over a list of poses: the shake detector."""
    ang = [aim_angles(p["pos"], p["aim"]) for p in poses]
    vel = [((b[0] - a[0]) * fps, (b[1] - a[1]) * fps) for a, b in zip(ang, ang[1:])]
    acc = [math.hypot(b[0] - a[0], b[1] - a[1]) * fps for a, b in zip(vel, vel[1:])]
    return math.degrees(max(acc)) if acc else 0.0
