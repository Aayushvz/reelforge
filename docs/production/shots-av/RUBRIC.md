# Shots-AV scoring rubric

Score each row from 0 to 10 for the reference reel and for ours. Use the same frames side by side (`side_by_side.mp4` at P7; stills before that). The rows are the ten areas in section 6 of `docs/prompts/03-shots-av-animation.md`.

**Ship rule (P7):** ours wins at least 8 of the 10 rows and loses none by more than 1 point. Otherwise, list the losing rows and fix them before shipping.

| # | Area | 0 | 5 | 10 | Evidence |
|---|---|---|---|---|---|
| 1 | Face shading | Visible shading triangles, noisy cheeks, pasted-on features | Smooth, but flat: no blush, no form at the nose or ears | Smooth skin with soft subsurface, blush on cheeks, ears and nose tip; bevelled forms; facets only where they're a style choice | P1 turnaround and expressions |
| 2 | Expression | Static face | Eyes and a flapping mouth, one smile | Brows, lids and 8 mouth shapes read at phone size; 12 emotions you can tell apart without captions | P1 expression and mouth sheets; P4 animatic |
| 3 | Hands | Mittens | Fingers that never pose | Four fingers and a thumb in five readable poses (rest, think, point, open, type); no pops when the pose changes | P1 outfits and poses sheet |
| 4 | Buddy | A bobbing blob | Squash on speech, one eye change | Talk squash from the loudness envelope, 8 reaction clips, eye shapes, a signature move per brand | P2 line-up and loops |
| 5 | Light | One fixed key, crushed bottom quarter | Readable key and fill, no rim | Rim separation, practicals, screen flicker, mood shifts per line; desk front holds 8-12% luminance; the jacket stays `#7C3AED` | P1 purple check; P3 room stills |
| 6 | Background | Flat painted bokeh | Real depth of field on a static backdrop | True bokeh from distant emissive cards, haze, moving background life, a monitor that animates with the dialogue | P3 stills; P5 clips |
| 7 | Camera | Static shots, or moves that fight the cut | The reference grammar (cuts on the line, linear drift) | The same grammar, plus one rack focus and one connected move that hides the scale change | P4 match pass and animatic |
| 8 | Captions | Captions over faces | Top placement, plain white | Top centre, brand-clean type, speaker tint, safe-area aware, fades timed to the cut | P5 clips |
| 9 | Sound | Voices only | A music bed under the voices | Bed, room tone, keyboard foley, a soft tone at each buddy line; -14 LUFS | P5 clips |
| 10 | Output | 720x1280 at about 420 kbps | 1080x1920, ungraded | 1080x1920, 30 fps, 10-12 Mbps, graded (purple-safe), light grain | P7 final file |

The reference reel scores itself in the "0" to "5" columns on most rows. Its strongest rows are camera (7) and pacing, which we copy before we try to beat it.

## Per-phase quick checks
| Phase | Pass |
|---|---|
| P1 | Face row 7 or more; expression row 7 or more; hands row 7 or more; the jacket's lit side within ΔE 10 of `#7C3AED` under the night key, and the matching card within ΔE 6 |
| P2 | Buddy row 7 or more; every buddy reads as its product from colour and silhouette alone, with no logo shapes |
| P3 | Background and light rows 7 or more in every room; no black crush below 8% luminance on the desk front |
| P4 | Match pass within tolerance (subject height ±0.03 H, eye line ±0.03 H, centre ±0.05 W); the 20-line fixture test passes |
| P5 | Captions and sound rows 7 or more |

## Viewing checklist (every clip, at full speed and at 25%)
Eyes alive? Blink lands after the cut? Brows doing the acting? Mouth closes on M, B and P? Hands pop between poses? Jacket still purple in every shot? Captions clear of faces? Cuts 2-4 frames before the line? Every shot moving? Any shot you'd be embarrassed to post?
