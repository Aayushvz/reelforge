# Cinema Real scoring rubric

Score every deliverable from 1 to 10 against the reference board (`references/style/cinema-real/`).

| Criterion | Weight | What a 10 looks like |
|---|---|---|
| Face realism and appeal | 30% | Skin glows with light passing through it, pores hold at 100% crop, eyes are wet with a catchlight, mouth and hair hold up in close-up |
| Lighting | 20% | Motivated, low-key, sculpts the face, skin hue stays natural under coloured light |
| Background believability and depth | 15% | Reads as a real place with props, wear, atmosphere and legible soft focus |
| Camera | 10% | Smooth, motivated moves; correct headroom; faces clear of the caption bands |
| Performance | 15% | Living eyes, natural blinks, lip-sync within 2 frames, secondary motion |
| Finish | 10% | Graded, no banding, restrained bloom and grain that stay off the face |

A phase passes when the weighted score is 7.5 or more, no criterion is below 6, and the face criterion is 8 or more.

## Automated checks
| Check | Where | Pass |
|---|---|---|
| Camera never shakes | `tests/test_camera_rig.py` (`max_angular_accel`) | under 25 deg/s² for every move |
| Eyes on the eye line, head size on target | `tests/test_camera_rig.py` | within 2% and 3% of frame height |
| Eyes clear of the caption bands (top 14%, bottom 20%) | `tests/test_camera_rig.py` | always |
| Shot lengths, no repeated set-ups, deterministic plan | `tests/test_director_v2.py` | always |
| Schema defaults reproduce the classic look | `tests/test_director_v2.py` | always |

Checks still to build (later phases): skin hue shift, 52-shape face check, luma range, banding, flicker.

## Animator's viewing checklist (every video, at full speed and 25%)
Eyes alive? Blinks natural? Head ever frozen? Pops or jitter? Lip-sync within 2 frames? Noise crawl in the darks? Banding in dark gradients? Moves eased and motivated? Cuts on beats? Captions clear of faces? Colour consistent across cuts? Any shot you'd be embarrassed to post?
