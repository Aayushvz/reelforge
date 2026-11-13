"""Background life for the Shots-AV rooms: small, slow motion behind the desk so a held shot never looks frozen.

Every motion is a driver with a *simple* expression (sin, fmod, frame), which Blender evaluates without running
Python, so it works in a factory-startup render with scripts off. Bases are written into the expressions, so the
motion stays put when the room slides (the objects hang off RoomPivot, and their location is local to it).

What moves (when the room has it): code scrolling on the desk monitor; distant bokeh breathing; traffic lights
gliding across the city; stars and fairy lights twinkling; clouds drifting past the moon; rain sliding down the glass;
lava-lamp blobs rising and falling; the edit timeline's playhead; a faint buzz in the neon.
"""
from __future__ import annotations

import math
import random

import bpy


# rooms with a night city outside: traffic glides across it
TRAFFIC = {"av_studio_night", "av_late_office", "av_editor_night", "av_streamer_den", "av_studio_apartment"}
GLOW_PARTS = ("Neon", "Sign", "Cove", "ShelfLED", "SillLED", "UnderLED", "LEDCove", "LEDCyanV", "ShelfLED0", "ShelfLED1")


def _drive(owner, path, index, expr):
    fc = owner.driver_add(path, index) if index is not None else owner.driver_add(path)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr
    for m in list(fc.modifiers):  # driver_add may add a generator modifier; keep the expression alone
        fc.modifiers.remove(m)
    return fc


def _f(x):
    return f"{x:.5f}"


def _breathe(o, rng, amount, speed):
    """Scale an emissive disc or bulb a little in and out (its object scale holds its radii)."""
    w, ph = rng.uniform(*speed), rng.uniform(0, 6.283)
    for k in (0, 2):
        s = o.scale[k]
        _drive(o, "scale", k, f"{_f(s)}*(1+{amount}*sin(frame*{_f(w)}+{_f(ph)}))")


def _traffic(coll, rng, y0):
    """Pairs of headlights (warm white, one way) and tail lights (red, the other) gliding along a far road."""
    from .geo import ball, mat
    head = mat("TrafficHead", "#FFE2B0", rough=0.5, emit=16.0)
    tail = mat("TrafficTail", "#FF3B30", rough=0.5, emit=14.0)
    for i in range(14):
        d = rng.uniform(26, 48)
        lane = 1 if i % 2 else -1
        m = head if lane > 0 else tail
        span = 70.0 * d / 30.0
        v = rng.uniform(0.10, 0.22) * lane  # metres per frame, far away: a slow glide on screen
        off = rng.uniform(0, span)
        z = rng.uniform(-0.6, 0.7) * (0.6 + d / 60)
        for k, dx in enumerate((-0.9, 0.9)):  # two lamps per car
            o = ball(f"Traffic{i:02d}{k}", (0.32, 0.03, 0.22), coll, m, (0, y0 + d, z), segs=10)
            o.visible_shadow = False
            _drive(o, "location", 0, f"fmod(frame*{_f(v)}+{_f(off)}+{span:.1f}*8,{span:.1f})-{span / 2:.1f}+{dx}")


def add(room_id: str, coll, Y: float):
    """Add the room's background life. Call after the room is built and before its objects are parented to the pivot
    (new objects made here are parented with the rest)."""
    rng = random.Random(f"life:{room_id}")
    objs = list(coll.objects)
    by = lambda prefix: [o for o in objs if o.name.split(".")[0].startswith(prefix)]  # noqa: E731

    # the desk monitor: its chat rows scroll up, about one row every 2 s
    scr = bpy.data.materials.get("ScreenMat")
    if scr and scr.node_tree:
        mp = next((n for n in scr.node_tree.nodes if n.type == "MAPPING"), None)
        if mp:
            _drive(mp.inputs["Location"], "default_value", 1, "frame*0.0045")

    for o in by("Far"):  # distant bokeh breathes, each on its own slow cycle
        if o.type == "MESH":
            _breathe(o, rng, 0.07, (0.02, 0.06))
    for o in by("Star"):
        _breathe(o, rng, 0.35, (0.08, 0.2))
    for o in by("Fairy"):
        if o.type == "MESH" and not o.name.startswith("FairyWire"):
            _breathe(o, rng, 0.18, (0.05, 0.14))
    for o in by("Cloud"):  # clouds drift past the moon
        _drive(o, "location", 0, f"{_f(o.location.x)}+frame*{_f(rng.uniform(0.004, 0.009))}")
    for o in by("Blob"):  # lava-lamp blobs rise and sink
        _drive(o, "location", 2, f"{_f(o.location.z)}+0.025*sin(frame*{_f(rng.uniform(0.025, 0.05))}+{_f(rng.uniform(0, 6.3))})")
    drops = by("Drop")
    if drops:  # rain slides down the glass and starts again at the top
        z0, z1 = min(o.location.z for o in drops), max(o.location.z for o in drops)
        h = max(0.2, z1 - z0)
        for o in drops:
            v, ph = rng.uniform(0.004, 0.012), (z1 - o.location.z)
            _drive(o, "location", 2, f"{_f(z1)}-fmod(frame*{_f(v)}+{_f(ph)},{_f(h)})")
    for o in by("Playhead"):  # the edit timeline plays
        _drive(o, "location", 0, f"{_f(o.location.x - 0.2)}+fmod(frame*0.0016,0.4)")

    for o in objs:  # plants sway a little, as if a fan were on
        if o.type == "MESH" and o.name.split(".")[0].startswith(("Leaf", "BigLeaf", "SillLeaf")):
            r = o.rotation_euler[1]
            _drive(o, "rotation_euler", 1, f"{_f(r)}+0.045*sin(frame*{_f(rng.uniform(0.03, 0.06))}+{_f(rng.uniform(0, 6.3))})")

    seen = set()

    def glow(prefixes, expr):
        """Drive the emission strength of every material on objects named with these prefixes; expr uses {s}, {ph}."""
        for o in objs:
            if o.type not in ("MESH", "FONT") or not o.name.split(".")[0].startswith(prefixes):
                continue
            for m in o.data.materials:
                if not m or m.name in seen or not m.node_tree:
                    continue
                b = m.node_tree.nodes.get("Principled BSDF")
                if b is None or b.inputs["Emission Strength"].default_value <= 0:
                    continue
                seen.add(m.name)
                s = b.inputs["Emission Strength"].default_value
                _drive(b.inputs["Emission Strength"], "default_value", None,
                       expr.format(s=_f(s), ph=_f(rng.uniform(0, 6.3))))

    # a CRT playing a game: its brightness flickers with the action
    glow(("CRTScreen",), "{s}*(0.82+0.12*sin(frame*0.7+{ph})*sin(frame*0.13)+0.06*sin(frame*2.9))")
    # PC fans breathe their RGB
    glow(("Fan", "PCStrip"), "{s}*(0.72+0.28*sin(frame*0.06+{ph}))")
    # a neon sign glitches now and then: a brief dip every couple of seconds, on top of its hum
    glow(("Sign",), "{s}*(0.95+0.05*sin(frame*1.3+{ph}))*(0.1 if sin(frame*0.083+{ph})>0.985 else 1)")
    # neon, signs and LED strips hum: a faint, uneven buzz in their brightness
    glow(GLOW_PARTS, "{s}*(0.95+0.05*sin(frame*1.3+{ph})*sin(frame*0.21+{ph}))")

    if room_id in TRAFFIC:
        _traffic(coll, rng, Y)
