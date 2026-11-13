# P7 benchmark: scores (2026-11-13)

Script: `p7/benchmark-script-draft.md` (original, approved by the owner). 20 ElevenLabs takes (Josh for the hero,
Jessica for Claude), directed by emotion. Rendered at the **Balanced** tier (1080x1920, 24 samples; see PROGRESS).

| Render | Project | Length | Render time | Loudness |
|---|---|---|---|---|
| Reference grammar, Studio night | `projects/p7-bench-reference` | 54.7 s | 23.3 min | -14.4 LUFS |
| Signature (director angles), Studio night | `projects/p7-bench-signature` | 54.7 s | 24.1 min | -14.3 LUFS |
| Signature, Studio morning | `projects/p7-bench-morning` | 54.7 s | 25.3 min | -14.4 LUFS |

`docs/production/shots-av/side_by_side.mp4` (internal, not committed: 42 MB): reference grammar left, signature
right, same audio. The reel runs 6 s longer than the reference's 48.9 s because the takes speak a little slower; the
cut list is the reference's (wides on lines 6, 13 and the closer).

## Rubric (`RUBRIC.md`), 0-10
The reference reel is scored from its frame grabs (`references/style/shots-av/`) and the prompt's analysis: the
video itself is not in the repo. "Ours" is the signature render.

| # | Area | Reference | Ours | Why |
|---|---|---|---|---|
| 1 | Face shading | 6 | 7 | Smooth skin, blush on cheeks and nose, bevelled forms; hair facets are a style choice. Loses points: no visible subsurface at this size |
| 2 | Expression | 5 | 7 | Brows, lids, glossy eyes with two glints; visemes with lips, teeth and tongue; 12 emotions. Reference: eyes and a flapping mouth |
| 3 | Hands | 4 | 7 | Capsule fingers, five poses (think fist on the jaw, open palms, typing); reference: a fist and flat hands |
| 4 | Buddy | 5 | 8 | Talk squash from the loudness envelope, waveform mouth, 8 reaction clips, eye shapes, a brand signature move |
| 5 | Light | 6 | 7 | Rim separation, practicals, screen glow; desk front 8.5-11% luminance; jacket within the purple budget |
| 6 | Background | 6 | 7 | True bokeh from distant emissive cards, haze, a live screen; no moving background life yet |
| 7 | Camera | 7 | 8 | The reference's cutting, plus a rack focus and 36 mood-picked angles (low, high, ECU, OTS, room reveal). No connected move yet |
| 8 | Captions | 5 | 8 | Top centre, Geist, speaker-colour dot, faint plate, safe-area aware, timed to the cuts |
| 9 | Sound | 5 | 8 | Room bed, keyboard foley, buddy chime, room reflections on the voices, -14 LUFS |
| 10 | Output | 1 | 9 | 1080x1920, 30 fps, 11 Mbps, purple-safe grade, halo, vignette, light grain. Reference: 720x1280 at about 420 kbps |

**Result: ours wins 10 of 10 rows and loses none. Ship rule met.**

Honest gaps (none loses a row, all are next steps): no connected camera move (row 7's 10), no moving background life
such as passing cars or blinking signs (row 6), subsurface reads weakly at phone size (row 1). The signature's
over-the-shoulder buddy shots on the thesis line fill half the frame with the jacket: legible, but busy.
