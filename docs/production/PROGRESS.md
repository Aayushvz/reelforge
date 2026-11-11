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
| 1 | Bake-off harness: `blender/bakeoff/face_sheet.py`, `face_check.py`, `compare_board.py`; v1 Kai baseline | done | 2267b27, 5f7d694 | v1 check: tongueOut + gaze-down poke-through; turnaround framing fixed |
| 1 | Route (c) build: Rain v3 → Kai (`route_c_rain.py`) | done (subagent, Sonnet) | checkpoint | face_check PASS; 92k base / 345k render tris; ~2.2 s/close-up; see `route_c_notes.md` |
| 1 | Route (b) build: procedural v2 Kai (`route_b_procedural.py`) | done (subagent, Sonnet) | 2267b27 | face_check PASS; 945k tris (hair 631k); ~2 s/close-up; see `route_b_notes.md` |
| 1 | Usage checkpoint: WIP commit + push at 85% (user rule) | done | this commit | pushed to origin/prod/phase1-look-route |
| 1 | Boards + lead scoring (`phase1/REVIEW.md`) | done | 3739f08 | (c) 6.73 vs (b) 4.95; recommend (c) as a hybrid base |
| 1 | Independent review (Opus, blind) | done | this commit | (c) 6.2 vs (b) 3.8; agrees with the lead: route (c) |
| 1 | Fix pass on route (c): stubble mask (defined beard edge, fine soft dots) | done | this commit | reviewers' defect #2; hair is now the top defect |
| 1 | Owner side-by-side + route approval | done | this commit | **route (c) approved** by Dhairya 2026-11-08 |
| 1 | Fix pass on route (c): hair → matte clumped curls; caricature restyle; cloth cleanup; jaw pivot / blink seam | **next** | — | then re-board vs refs 1 and 3 |
| 1 | Bake-off on Kai: (a) image-to-3D, (b) procedural v2, (c) CC-BY base | not started | — | judged 40% face likeness, 25% expressiveness, 15% eyes |
| 2 | Cast production (7 × 3 looks) | not started | — | |
| 3 | Environments (10 × 3) + R1 AI plates | not started | — | |
| 4 | Performance + `reelforge bench` | not started | — | |
| 5 | Editor integration + `reelforge thumbnails` | not started | — | |
| 6 | Ship (docs, release asset) | not started | — | |

## Open questions for the owner
- Hardware: image-to-3D, FLUX/SDXL plates and the enhance pass need an 8 GB GPU (or a free cloud GPU) and multi-GB downloads.

## Decisions
- 2026-11-08 (Dhairya): **Route (c) approved** as the cast base (Rain v3 face rig + restyle), per `phase1/REVIEW.md`. Route (a) stays a later challenger.
- 2026-11-08 (Dhairya): Phase 1 bake-off runs routes **(b) procedural v2** and **(c) CC-BY base** on this laptop.
  Route **(a) image-to-3D** joins later on the owner's 8 GB machine or a free cloud GPU, scored on the same rubric.
- 2026-11-08 (Dhairya): OK to download one Blender Studio CC-BY character for route (c), size checked first, < 2 GB.
- Superpowers skills aren't installed in this environment; the same flow (spec → plan → subagent build →
  reviewer on a different model) is followed by hand.
