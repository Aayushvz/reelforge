"""Build a Shots-AV asset -> <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/build_shotsav.py -- <out.blend> hero [dial=value ...]
     blender -b --factory-startup --python-exit-code 1 -P blender/build_shotsav.py -- <out.blend> buddy <id> [color=#hex]
Hero dials (blender/shotsav/hero.py HERO): outfit, outfit_color, hair, hair_color, glasses, headphones, skin,
stubble, chest_mark. Example: ... -- hero.blend hero outfit=hoodie hair=buzz skin=tan
Buddies (blender/shotsav/buddies.py BUDDIES): claude, chatgpt, figma, nova.
Rooms (blender/shotsav/rooms.py ROOMS): ... -- <out.blend> room av_studio_night"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shotsav import buddies, hero, rooms  # noqa: E402


def parse_dials(pairs):
    out = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        default = hero.DEFAULTS.get(key)
        if isinstance(default, bool):
            out[key] = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(default, float):
            out[key] = float(value)
        else:
            out[key] = value
    return out


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    out, kind = Path(args[0]).resolve(), args[1] if len(args) > 1 else "hero"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if kind == "hero":
        hero.build(**parse_dials(args[2:]))
    elif kind == "buddy":
        opts = dict(a.split("=", 1) for a in args[3:])
        buddies.build(args[2], color=opts.get("color"))
    elif kind == "room":
        rooms.build(args[2])
    else:
        raise SystemExit(f"unknown shots-av asset {kind!r}: use hero, buddy <id> or room <id>")
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"saved {out}")
