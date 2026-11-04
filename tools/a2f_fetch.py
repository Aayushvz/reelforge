"""Run NVIDIA Audio2Face-3D (v2.3 regression model) locally on CPU and write ARKit frames.

usage: python tools/a2f_fetch.py <audio.(wav|mp3)> <out.json> [--model DIR] [--emotion joy=0.5 ...]

No CUDA/TensorRT: the open ONNX weights (huggingface.co/nvidia/Audio2Face-3D-v2.3-Mark) run under
onnxruntime, and the SDK's post-processing (PCA reconstruct -> skin compose -> regularised bounded
blendshape solve) is re-implemented in numpy following NVIDIA/Audio2Face-3D-SDK source:
  executor_regression_core.cpp (windowing), animator_cuda.cu (skin compose, face mask),
  blendshape_solver_base.cpp / blendshape_solver.cpp (A matrix, regularisers, temporal term).
Omitted vs. the SDK: procedural blinks/saccades (reelforge adds its own blinks), tongue, jaw and
eye-rotation outputs, and the ~1 ms upper/lower smoothing filters (no-ops at 30 fps).
Writes {"frames": [{"time": t, "blendshapes": {arkitName: w}}]} at 30 fps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort

DEFAULT_MODEL = Path(__file__).resolve().parent / "a2f" / "models" / "v2.3-Mark"
FPS = 30


def load_audio(path: Path, sr: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def solve_box_qp(A: np.ndarray, b: np.ndarray, x0: np.ndarray, iters: int = 200,
                 tol: float = 1e-6) -> np.ndarray:
    """min 0.5 x'Ax - b'x  s.t. 0 <= x <= 1 (projected coordinate descent; exact for box QPs)."""
    x = x0.copy()
    diag = np.diag(A)
    for _ in range(iters):
        delta = 0.0
        for i in range(len(x)):
            g = A[i] @ x - b[i]
            new = min(1.0, max(0.0, x[i] - g / diag[i]))
            delta = max(delta, abs(new - x[i]))
            x[i] = new
        if delta < tol:
            break
    return x


def run(audio_path: Path, model: Path, explicit: dict[str, float]) -> tuple[list[dict], dict]:
    t0 = time.perf_counter()
    info = json.loads((model / "network_info.json").read_text())
    cfg = json.loads((model / "model_config.json").read_text())["config"]
    bscfg = json.loads((model / "bs_skin_config.json").read_text())["blendshape_params"]
    p, ap = info["params"], info["audio_params"]
    sr, blen, bofs = ap["samplerate"], ap["buffer_len"], ap["buffer_ofs"]
    n_skin, n_tongue = p["num_shapes_skin"], p["num_shapes_tongue"]

    md = np.load(model / "model_data.npz")
    bs = np.load(model / "bs_skin.npz")
    emo = np.load(model / "implicit_emo_db.npz")

    # implicit emotion from the configured source shot/frame, explicit from the CLI (default 0)
    names = [n.decode() for n in emo["emo_spec_names"]]
    k = names.index(cfg["source_shot"])
    implicit = emo["emo_db"][emo["emo_spec_start"][k] + cfg["source_frame"]]
    exp = np.array(p["default_emotion"], dtype=np.float32)
    for name, v in explicit.items():
        exp[p["explicit_emotions"].index(name)] = v
    emotion = np.concatenate([implicit, exp]).astype(np.float32)

    audio = load_audio(audio_path, sr)
    duration = len(audio) / sr
    n_frames = int(np.ceil(duration * FPS)) + 1
    padded = np.concatenate([np.zeros(bofs, np.float32), audio, np.zeros(blen, np.float32)])
    windows = np.stack([padded[int(round(i / FPS * sr)):][:blen] for i in range(n_frames)])
    windows = (windows * cfg["input_strength"])[:, None, :].astype(np.float32)
    t_load = time.perf_counter()

    sess = ort.InferenceSession(str(model / "network.onnx"), providers=["CPUExecutionProvider"])
    outs = []
    for s in range(0, n_frames, 32):
        w = windows[s:s + 32]
        e = np.broadcast_to(emotion, (len(w), 1, len(emotion))).copy()
        outs.append(sess.run(["result"], {"input": w, "emotion": e})[0][:, 0, :])
    result = np.concatenate(outs)
    t_infer = time.perf_counter()

    # restrict all vertex math to the solver's frontal mask
    pose_names = [n.decode() for n in bs["poseNames"]][1:]  # [0] is "neutral"
    mask_v = bs["frontalMask"]
    mean = md["shapes_mean_skin"]  # animator neutral pose (n_verts, 3)
    pca = md["shapes_matrix_skin"][:, mask_v, :].reshape(n_skin, -1)
    eye_close = md["eye_close_pose_delta"][mask_v].reshape(-1)
    lip_open = md["lip_open_pose_delta"][mask_v].reshape(-1)

    y = mean[:, 1]
    lower = 1.0 / (1.0 + np.exp(-(cfg["face_mask_level"] - (y - y.min()) / (y.max() - y.min()))
                                / cfg["face_mask_softness"]))
    lower = np.repeat(lower[mask_v], 3)
    region = cfg["upper_face_strength"] * (1 - lower) + cfg["lower_face_strength"] * lower

    delta = result[:, :n_skin] @ pca  # (frames, masked xyz)
    delta = (cfg["skin_strength"] * delta - eye_close * cfg["eyelid_open_offset"]
             + lip_open * cfg["lip_open_offset"]) * region
    # The SDK solves (shapes_mean_skin + delta) - bs_skin.neutral; those two neutrals differ by a
    # small static offset that the solver explains as a constant ~0.15 jawRight even in silence.
    # Our rig has its own rest pose, so solve the animated delta only.
    target = delta

    active = [i for i, a in enumerate(bscfg["bsSolveActivePoses"]) if a]
    D = np.stack([bs[pose_names[i]][mask_v].reshape(-1) for i in active], axis=1)
    nb = len(active)
    neutral_full = bs["neutral"]
    sf = float((np.linalg.norm(neutral_full.max(0) - neutral_full.min(0)) / bscfg["templateBBSize"]) ** 2)
    sym = [bscfg["bsSolveSymmetryPoses"][i] for i in active]
    S = []
    for pid in set(s for s in sym if s >= 0):
        idx = [j for j, s in enumerate(sym) if s == pid]
        if len(idx) == 2:
            row = np.zeros(nb)
            row[idx[0]], row[idx[1]] = 1.0, -1.0
            S.append(row)
    S = np.array(S) if S else np.zeros((0, nb))
    l1, l2 = bscfg["strengthL1regularization"], bscfg["strengthL2regularization"]
    tr, sr_ = bscfg["strengthTemporalSmoothing"], bscfg["strengthSymmetry"]
    A = (D.T @ D + l1 * l1 * 0.25 * sf * np.ones((nb, nb)) + l2 * 10 * sf * np.eye(nb)
         + tr * 100 * sf * np.eye(nb) + sr_ * 10 * sf * S.T @ S)
    ATb = target @ D  # (frames, nb)

    mult = np.array(bscfg["bsWeightMultipliers"])
    offs = np.array(bscfg["bsWeightOffsets"])
    prev = np.zeros(nb)
    frames = []
    for i in range(n_frames):
        # SDK: b = A'b + temporalReg * scaleFactor * prevWeights
        x = solve_box_qp(A, ATb[i] + tr * sf * prev, prev)
        prev = x
        w = np.zeros(len(pose_names))
        w[active] = x
        w = w * mult + offs
        frames.append({"time": round(i / FPS, 5),
                       "blendshapes": {n: round(float(v), 4) for n, v in zip(pose_names, w)
                                       if v > 1e-4}})
    t_end = time.perf_counter()
    stats = {"audio_s": round(duration, 3), "frames": n_frames,
             "load_s": round(t_load - t0, 2), "infer_s": round(t_infer - t_load, 2),
             "solve_s": round(t_end - t_infer, 2), "total_s": round(t_end - t0, 2)}
    return frames, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("audio", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--emotion", action="append", default=[], metavar="NAME=V",
                    help="explicit emotion, e.g. joy=0.6 (amazement anger cheekiness disgust fear "
                         "grief joy outofbreath pain sadness)")
    a = ap.parse_args(argv)
    explicit = {k: float(v) for k, v in (e.split("=") for e in a.emotion)}
    frames, stats = run(a.audio, a.model, explicit)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"frames": frames, "source": "audio2face-3d-v2.3-mark-onnx-cpu",
                                 "audio_sha1": hashlib.sha1(a.audio.read_bytes()).hexdigest(),
                                 "stats": stats}), encoding="utf-8")
    print(json.dumps(stats), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
