# Production progress ledger

Source of truth for resuming work on the v2 production push (`docs/NEXT_PROMPT_DHAIRYA.md`, plus the
"Realism upgrades" section on the owner's branch `feat/auto-voices-editor-flow`).
Update after every task. A new session reads this file and `git log`, and never redoes a row marked done.

## Machine (Dhairya's laptop; differs from the prompt's assumptions)
| Item | Prompt assumes | Actual |
|---|---|---|
| GPU | RTX 4060, 8 GB | **RTX 3050 Laptop, 4 GB** |
| Blender | 4.5 LTS | **5.2.3 LTS** (scripts handle both) |
| Free disk | — | **~15 GB** on C: |
| Python | 3.12+ | 3.13 venv |

Consequences: image-to-3D (Hunyuan3D-2 mini needs ~6 GB VRAM for shape, more for texture; TRELLIS ~16 GB) and
FLUX/SDXL plates (6–12 GB of weights) either don't fit or need heavy CPU offload, and the disk can't hold more
than one or two of them at once. Every such download also needs the owner's approval (>2 GB rule).

## Status
| Phase | Task | Status | Commit | Verdict / notes |
|---|---|---|---|---|
| 0 | Baseline: 63 tests pass on `main` (fdfc0ca) | done | — | |
| 0 | Baseline: `reelforge build-assets` | done | — | 61 blend files in 210 s, no errors |
| 1 | Brainstorm look route; route scope decided | done | — | (b) vs (c) here, (a) later; see Decisions |
| 1 | Download + inspect Rain v3 (CC-BY, 64 MB) | done | — | renders in Blender 5.2; bone-driven face; `phase1/rain_v3_lookcheck.jpg` |
| 1 | Phase 1 spec (`phase1-spec.md`) | done | f0fbf9f | approved by Dhairya 2026-11-08 |
| 1 | Bake-off harness: `blender/bakeoff/face_sheet.py`, `face_check.py`; v1 Kai baseline sheets | done | 5216eb6 | v1 check: tongueOut + gaze-down poke-through |
| 1 | Route (c) build: Rain v3 → Kai (`route_c_rain.py`) | in progress (subagent, Sonnet) | — | brief: `phase1/brief_route_c.md` |
| 1 | Route (b) build: procedural v2 Kai (`route_b_procedural.py`) | in progress (subagent, Sonnet) | — | brief: `phase1/brief_route_b.md` |
| 1 | Scoring + independent review + owner side-by-side | not started | — | |
| 1 | Bake-off on Kai: (a) image-to-3D, (b) procedural v2, (c) CC-BY base | not started | — | judged 40% face likeness, 25% expressiveness, 15% eyes |
| 2 | Cast production (7 × 3 looks) | not started | — | |
| 3 | Environments (10 × 3) + R1 AI plates | not started | — | |
| 4 | Performance + `reelforge bench` | not started | — | |
| 5 | Editor integration + `reelforge thumbnails` | not started | — | |
| 6 | Ship (docs, release asset) | not started | — | |

## Open questions for the owner
- Hardware: image-to-3D, FLUX/SDXL plates and the enhance pass need an 8 GB GPU (or a free cloud GPU) and multi-GB downloads.

## Decisions
- 2026-11-08 (Dhairya): Phase 1 bake-off runs routes **(b) procedural v2** and **(c) CC-BY base** on this laptop.
  Route **(a) image-to-3D** joins later on the owner's 8 GB machine or a free cloud GPU, scored on the same rubric.
- 2026-11-08 (Dhairya): OK to download one Blender Studio CC-BY character for route (c), size checked first, < 2 GB.
- Superpowers skills aren't installed in this environment; the same flow (spec → plan → subagent build →
  reviewer on a different model) is followed by hand.
