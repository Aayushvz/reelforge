"""Finish a built imported character: tidy it (cleanup only) and give it the liveliness shading pass.

Tidy never reduces quality (CLAUDE.md): no decimation, no texture resizing, every shape key kept. It only
- removes meshes the spec deletes (pieces no outfit shows, e.g. Matt's boxers under his jeans),
- merges textures that are byte-for-byte the same image (Mina's mouth maps were packed twice),
- purges data nothing uses.
import_character.py calls finish() before it saves; for an existing built file:
    blender -b assets/build/<id>.blend -P blender/finish_character.py -- <id>
"""
import hashlib
import runpy
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from liveliness import enliven  # noqa: E402


def dedupe_images() -> int:
    """Point every user of a duplicate image at the first copy and remove the copy. Returns how many went."""
    seen, gone = {}, 0
    for im in list(bpy.data.images):
        if not im.packed_file:
            continue
        key = (hashlib.sha1(im.packed_file.data).hexdigest(), im.colorspace_settings.name, im.alpha_mode)
        first = seen.setdefault(key, im)
        if first is not im:
            im.user_remap(first)
            bpy.data.images.remove(im)
            gone += 1
    return gone


def finish(cid: str, delete=()) -> dict:
    removed = 0
    for name in delete:
        o = bpy.data.objects.get(f"{cid}_{name}".replace(".", "_").replace(" ", "_")) or bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
            removed += 1
    report = {"removed_objects": removed, "merged_images": dedupe_images()}
    mats = {m for o in bpy.data.objects if o.type == "MESH" for m in o.data.materials if m}
    report["enlivened"] = enliven(mats)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    return report


if __name__ == "__main__":
    cid = sys.argv[sys.argv.index("--") + 1]
    spec = runpy.run_path(str(HERE / "imported.py"))["CHARACTERS"][cid]
    print("FINISHED", cid, finish(cid, spec.get("delete", [])))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(compress=True)
    print("SAVED", bpy.data.filepath)
