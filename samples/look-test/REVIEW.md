# Look-test review (Task 13)

Final: `samples/look-test/out/final_9x16.mp4` (7.93 s). Voice: ElevenLabs web-app mp3s, aligned locally with faster-whisper.
Reviewer: automated/evidence-based pass. The user is the final gate.

| Check | Result | Evidence |
|---|---|---|
| Loudness -15..-13 LUFS | PASS | ebur128 integrated -14.9 LUFS, LRA 1.6 LU (single-pass loudnorm landed in range, near the lower edge) |
| 1080x1920, 30 fps, H.264 + AAC | PASS | ffprobe: h264 1080x1920 30/1; aac 48 kHz, mono (stereo not required) |
| Lip closures on m/b/p | PASS (weak) | "approved" pp at ~5.33-5.40 s (frames 160-162): mouthClose 0.70, jawOpen 0.00; the frame shows a thin closed line. Vowel "a" at frame 158: jawOpen 0.55, mouth clearly open. Closure peaks at only 0.70, so it still reads as a slight smile line rather than pressed lips |
| No mouth movement in silence | PASS | no frame with jawOpen > 0.08 outside speech windows (+/-0.1 s); silence frame 100 shows a closed neutral mouth |
| Deadpan -> happy visible, overshoot settles | PASS | 1.5 s: flat neutral mouth/brows; 5.0 s and 7.3 s: smile, raised cheeks, wider eyes; tail holds a relaxed smile without jitter |
| Calm -> success mood crossfade (rim, screens, panels) | PASS (subtle) | grade shifts from cool blue/amber (1.5 s) to green-teal (5.0 s, 7.3 s); screens go green. Rim light itself is hard to see (see open items) |
| Bokeh city, haze, halation, not flat | PARTIAL | close-ups have good rounded bokeh windows and glow; haze present. The wide shot (1.5 s) has sharp-edged window rectangles and a flat dark wall, so it is less cinematic than the close-ups |
| Captions above head, in safe zone, active word highlighted, punchline pops | PASS | caption at y=296 in all sampled frames, above the head; yellow highlight follows the spoken word; punchline is larger (scale 118) with a rotate wobble (in the ASS events) |
| Caption text accuracy (Whisper) | PASS | Whisper transcripts: "The client said it's great." and "Wait! They actually approved it!" Audio tags ([sighs], [excited]) are correctly absent. No misrecognised words |

## Observations
- Line 1 caption chunking: "The client said it's" is shown, then "great." alone with a fresh pop (words 1-4 and 5 are split into two chunks). Acceptable but "great." orphaned.
- Punchline "They actually approved it!" at scale 118 spans about x=80..1000 of 1080. It fits on one line but only just; a longer word would wrap.
- Mood change lands at frame 110 (3.67 s), at the start of the punchline cut; the 3.7 s frame already shows the new teal grade with a neutral face.

## Known open items (not fixed here)
- Rim light is weak: barely visible on the head edge in the close-ups.
- Face is lit flat: soft fill, little modelling; the glasses show a flat ghost shadow.
- Wide-shot windows are not bokeh (hard rectangles with a grid texture).
- Lip closures peak at 0.70 (confirmed above).
- Single-pass loudnorm can miss -14 LUFS in general; this clip measured -14.9 (in range).
- Long words at punchline scale may wrap (this clip fits, narrowly).
- The stand-in character will be replaced by a Pixar-style one later.
- Voice delivery: line 1 and 2 pacing is taken from the web-app audio; the 0.86 s pause inside line 2 after "Wait!" is part of the audio.
