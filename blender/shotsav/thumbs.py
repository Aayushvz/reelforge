"""Editor card thumbnails for Shots-AV: a buddy close single, or a room wide with the hero and the Claude robot.
Run: blender -b --factory-startup --python-exit-code 1 -P blender/shotsav/thumbs.py -- <out_dir> <id> [<id> ...]
Ids: buddy_claude, buddy_chatgpt, buddy_figma, buddy_nova, or a room id (av_studio_night, ...). Writes <id>.jpg."""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shotsav import buddy_sheets, room_sheets, rooms  # noqa: E402
from shotsav.sheets import load, save  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
out = Path(args[0]).resolve()
out.mkdir(parents=True, exist_ok=True)
for item in args[1:]:
    png = out / f".{item}.png"
    if item.startswith("buddy_"):
        sc = buddy_sheets.reset((360, 480), 24)
        buddy_sheets.room(sc, False)
        _, _, eye = buddy_sheets.place(item[len("buddy_"):], buddy_sheets.MARK_B)
        buddy_sheets.buddy_cam(sc, buddy_sheets.MARK_B, eye, size_h=0.55)
    elif item in rooms.ROOMS:
        sc = room_sheets.setup_scene(item, (360, 640))
        sc.eevee.taa_render_samples = 24
        room_sheets.place_camera(sc, "wide")
    else:
        raise SystemExit(f"unknown thumbnail id {item!r}")
    sc.render.filepath = str(png)
    bpy.ops.render.render(write_still=True)
    save(load(png), out / f"{item}.jpg")
    png.unlink()
    print(f"THUMB {item}")
