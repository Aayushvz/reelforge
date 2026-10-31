# Audio2Face-3D spike (Task 14)

Date: 2026-10-31. Time spent: about 1.5 h of the 3 h box. Outcome: **real A2F output running locally
with no system installs**. It plugs in through `out/a2f/<line_id>.json`. On the current chibi rig the
stills are **not visibly better** than the viseme lip sync.

## What was tried

Hosted NIM (build.nvidia.com) was **skipped by decision**: the user does not want an NVIDIA account
or API key.

### Option 2a: build `NVIDIA/Audio2Face-3D-SDK` (C++) as documented. Blocked, not attempted

The README requires:

| Need | Required | This machine |
|---|---|---|
| CUDA Toolkit | >= 12.8, < 13.0 (12.9 recommended), about 3 GB installer | not installed (driver 592.82 / CUDA 13.1 runtime only) |
| TensorRT | >= 10.13, < 11.0, about 2-3 GB zip; the C++ SDK zip download needs an NVIDIA developer login | not installed |
| Compiler | MSBuild with VS 2022+ | **present**: VS Build Tools 2026 (18.8), MSVC 14.51 |
| Python (scripts) | 3.8-3.10 | the venv is 3.14 |
| Models | `download_models.bat` via `hf auth login`; Audio2Emotion is gated (accept the licence) | — |
| Disk | 10 GB+ | — |

Both CUDA 12.9 and TensorRT are system installs above the 2 GB line, so this route stopped by rule.
If it's ever wanted: install CUDA 12.9 (about 3 GB, 20 min), unzip TensorRT 10.13 for CUDA 12.x
(about 2.5 GB, needs an NVIDIA dev account), create a Python 3.10 venv for `gen_testdata`, then run
`fetch_deps.bat`, `build.bat` and `gen_testdata.bat`, which builds the TRT engines. Estimate 2-4 h
including debugging. Not worth it given option 2b.

### Option 2b: open ONNX weights + onnxruntime on CPU, SDK post-processing ported to numpy. **Worked**

- `huggingface.co/nvidia/Audio2Face-3D-v2.3-Mark` is **not gated**. It ships `network.onnx`
  (76 MB) plus `model_data.npz` (204 MB), `bs_skin.npz` (39 MB), the 52 ARKit delta shapes and a
  frontal mask, `implicit_emo_db.npz` and the configs. The total is about 320 MB, in
  `tools/a2f/models/v2.3-Mark/`, which is git-ignored. v3.0 is also ungated (725 MB ONNX) but
  wasn't needed.
- `pip install onnxruntime` (1.31.1, cp314 wheel) and `scipy` into `.venv` was the only install;
  scipy is not actually used by the final script. `onnxruntime-directml` also has a cp314 wheel
  if GPU speed is ever needed.
- `tools/a2f_fetch.py <audio> <out.json> [--emotion joy=0.6]` reimplements, from the SDK source:
  - windowing: an 8320-sample window at 16 kHz centred on each 30 fps frame, times
    `input_strength`, from `executor_regression_core.cpp`
  - the emotion input: 16 implicit dims from `g2a_neutral` frame 33, then 10 explicit dims
  - PCA reconstruction (output 301 = skin 272 + tongue 10 + jaw 15 + eyes 4)
  - skin compose: skin strength, eyelid and lip offsets, sigmoid upper/lower face mask, from
    `animator_cuda.cu`
  - the blendshape solve: `A = D'D + L1/L2/temporal/symmetry` regularisers with the SDK's scale
    constants, a temporal term in `b`, a [0, 1] box-constrained QP and active-pose masking, from
    `blendshape_solver_base.cpp` / `blendshape_solver.cpp`
- Not ported: procedural blinks and saccades (reelforge adds its own blinks), tongue, jaw-bone and
  eye-rotation outputs, and the upper/lower smoothing filters (1-2 ms constants, no-ops at 30 fps).
- One deliberate deviation: the SDK solves against `shapes_mean_skin + delta - bs_skin.neutral`.
  Those two neutrals differ slightly, and the solver turned the difference into a constant
  jawRight of about 0.15 even in silence. The script solves the animated delta only.
- This is **not validated against SDK output**; we have no SDK build to diff against. The tracks are
  plausible: jaw, pucker, funnel, roll and close follow the syllables.

## Latency (CPU onnxruntime, RTX not used)

| line | audio | model load | inference | solve | total |
|---|---|---|---|---|---|
| l01 | 2.93 s | 0.06 s (0.7 s cold) | 1.3-1.5 s | 0.8 s | 2.2-3.0 s |
| l02 | 2.59 s | 0.05 s | 1.2-1.3 s | 0.7 s | 2.0 s |

That's about 0.75x real time on CPU. Cost: free, local, no account. Licence: NVIDIA Open Model
License (see the HF model card); the SDK is MIT.

## Before/after (draft stills, `--stage stills --draft`)

Data (render_plan face tracks): 35 channels exceed 0.05, against 17 before. Mouth motion (sum of
per-channel stdev) is 1.27 before and 1.74 after; upper face 0.67 before and 0.80 after.

Visual verdict, honest: **no visible win on stills; one is arguably worse.**
- Shots 00, 01 and 03 are essentially identical. Shot 03 is mid-silence, where both use the same
  script-emotion pose.
- Shot 02 (frame 142, "Wait. They actually approved it!"): the viseme version shows an open, talking
  smile. The A2F version lands on a closed-lip frame (mouthClose 0.11, no jawOpen) and shows a thin,
  slightly lopsided smile, from a residual jawRight of about 0.13.
- Brows, eyes and cheeks are unchanged to the eye. With neutral explicit emotion, A2F's upper-face
  output is tiny (brows at most 0.08). The rig's mouth is a simple stylised shape that cannot express
  the subtle pucker, funnel, roll and shrug channels A2F produces.
- A single still per shot can't judge lip-sync *timing*, which is where A2F should actually win; a
  `--stage full` A/B video is the real test and wasn't run in this spike.

Emotion: v2.3 does **not** infer emotion from audio by itself. Emotion comes from the 10 explicit
inputs. `--emotion joy=0.8` on l02 gave mouthSmile 0.6, browInnerUp 0.21, cheekSquint 0.17,
eyeSquint 0.11 and noseSneer 0.23, so the model is emotion-aware when told. Automatic "emotion from
voice" needs **Audio2Emotion-v2.2**: gated (accept licence and log in to an HF account),
1.27 GB ONNX. Not attempted, because it needs an account.

## Recommendation for Milestone 2

1. Keep the viseme path as the default. Keep the adapter and `tools/a2f_fetch.py`; they cost nothing
   and need no account.
2. Before any further A2F investment, do a **motion** A/B (`--stage full` with and without
   `out/a2f/`) and watch it. Decide on timing and naturalness, not stills.
3. If A2F stays: (a) drive the explicit emotion vector from the script's `emotion`/`intensity`
   (happy to joy, sad to sadness, surprised to amazement, ...) and drop reelforge's static
   `EMOTION_POSES` for A2F lines, to avoid double smiles; (b) add per-channel gain and remapping
   for the chibi rig (boost jawOpen, damp jawRight/jawForward/mouthRoll*); (c) suppress the jawRight
   drift. A symmetric solve or zeroing jawLeft/jawRight is enough.
4. Only consider the C++ SDK build, or Audio2Emotion, if the motion A/B is clearly positive. The SDK
   needs CUDA 12.9 + TensorRT 10.13 system installs; A2E needs an HF account.
5. The rig is the real ceiling: richer A2F data only pays off with a face that has more expressive
   blendshape sculpts (cheeks, brows, lip roll).
