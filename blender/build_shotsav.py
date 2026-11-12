"""Build a Shots-AV asset -> <out.blend>.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/build_shotsav.py -- <out.blend> hero [dial=value ...]
Hero dials (blender/shotsav/hero.py HERO): outfit, outfit_color, hair, hair_color, glasses, headphones, skin,
stubble, chest_mark. Example: ... -- hero.blend hero outfit=hoodie hair=buzz skin=tan
`buddy <id>` (P2) and `room <id>` (P3) are not built yet."""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shotsav import hero  # noqa: E402


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
    out, kind = Path(args[0]), args[1] if len(args) > 1 else "hero"
    if kind != "hero":
        raise SystemExit(f"shots-av {kind!r} is not built yet (buddies are P2, rooms are P3); only `hero` exists")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hero.build(**parse_dials(args[2:]))
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"saved {out}")
