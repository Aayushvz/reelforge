"""Side-by-side judging boards for the bake-off (stdlib + ffmpeg, no Blender needed).

Run: .venv/Scripts/python blender/bakeoff/compare_board.py <out_dir> <label=sheet_dir> [<label=sheet_dir> ...]

Writes into <out_dir>:
  board_faces.png   one row per entry: neutral, laugh, smug, surprised, sad, angry, viseme M, blink
  board_ecu.png     one row per entry: eye ECU, mouth ECU
  board_turn.png    one row per entry: the turnaround
  board_refs.png    the style references in one row (same height), for the owner's side-by-side"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FACE_POSES = ("neutral", "laugh", "smug", "surprised", "sad", "angry", "viseme_M", "blink")


def grid(rows, w, h, out):
    """rows: list of lists of image paths (missing paths render black)."""
    ins, f, cells = [], "", []
    for r, row in enumerate(rows):
        for c, img in enumerate(row):
            k = len(cells)  # one ffmpeg input per cell, so the input index is the cell index
            if Path(img).exists():
                ins += ["-i", str(img)]
                f += f"[{k}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:-1:-1[c{k}];"
            else:
                ins += ["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}"]
                f += f"[{k}:v]null[c{k}];"
            cells.append(f"{c * w}_{r * h}")
    f += "".join(f"[c{i}]" for i in range(len(cells))) + f"xstack=inputs={len(cells)}:layout={'|'.join(cells)}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", f, "-frames:v", "1", str(out)],
                   check=True)


def main(argv):
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    entries = [(a.split("=", 1)[0], Path(a.split("=", 1)[1])) for a in argv[1:]]
    grid([[d / f"face_{p}.png" for p in FACE_POSES] for _, d in entries], 216, 270, out / "board_faces.png")
    grid([[d / "ecu_eyes.png", d / "ecu_mouth.png"] for _, d in entries], 480, 240, out / "board_ecu.png")
    grid([[d / "turnaround.png"] for _, d in entries], 1080, 480, out / "board_turn.png")
    refs = sorted((REPO / "references/characters/style").glob("*.png"))
    grid([refs], 300, 400, out / "board_refs.png")
    (out / "board_rows.txt").write_text("\n".join(label for label, _ in entries) + "\n", encoding="utf-8")
    print("boards ->", out, "rows:", [label for label, _ in entries])


if __name__ == "__main__":
    main(sys.argv[1:])
