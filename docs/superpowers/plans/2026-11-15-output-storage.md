# Output storage fix (2026-11-15)

## What's wrong (measured)
- `projects/*/out` holds **21 GB**, and C: is 92% full (40 GB free).
- Almost all of it is `out/frames/`: Blender writes every frame as an 8-bit RGB PNG at 1080×1920, about **2.1 MB each**. A 68 s reel is 1,642 frames, or 3.1 GB. The finished `final_9x16.mp4` for the same reel is 77 MB.
- **Nothing ever deletes the frames.** They're kept for four reasons, but none of them needs PNGs:
  1. **Render cache:** `shots_av.render()` skips a re-render when `.render_key_full` matches and there are at least `n_frames` PNGs on disk.
  2. **Crash resume:** `render_plan.py` sets `use_overwrite=False`, so frames already on disk survive a crash.
  3. **Re-finish:** `finish.build_ffmpeg_cmd` reads `frames/%04d.png` for the grade, captions and mix, so a caption or grade change re-uses the frames.
  4. **Thumbnails:** `cover.py` and `ThumbnailGenerator.tsx` read clean stills from `out/frames/{N+1:04}.png`.
- Smaller sources of bloat:
  - `out/animatic/frames/` (up to 360 MB);
  - `final_*_share.mp4` duplicates (about 27 MB);
  - the intermediate WAVs: `dialogue_dry`, `foley`, `ambience` (about 15 MB each).

## Target
About **150–250 MB per reel**, made up of:
- `final_9x16.mp4`;
- `_share.mp4`;
- one clean master;
- the small JSON and audio files.

There's no quality loss and no extra render time.

## Plan
1. **Clean master instead of PNGs.** After Blender finishes and the frame count checks out, encode `out/frames` once into `out/clean_master.mp4`:
   - settings: x264 `-crf 8 -preset slow -pix_fmt yuv444p`, which is visually lossless and about 100–200 MB for 60 s;
   - then delete `out/frames/`;
   - write the render key next to the master.
2. **Cache check uses the master.** If the key matches and `clean_master.mp4` has `n_frames` frames (checked with ffprobe), skip the render. While a render is still in progress, frames stay on disk, so crash resume works as it does now.
3. **Finish reads the master.** `build_ffmpeg_cmd` takes the master as its input when the frames are gone. Re-captioning or re-grading still needs no re-render.
4. **Thumbnails from the master.** Add a `GET /api/projects/:id/frame/:n` endpoint that runs `ffmpeg -ss <t> -i clean_master.mp4 -frames:v 1` and caches the PNG under `out/stills_cache/`. `cover.py` sets `frames` to that endpoint, and `ThumbnailGenerator` changes only its URL builder.
5. **Animatic:** encode the animatic, then delete `out/animatic/frames`.
6. **Intermediates:** after the final mix, delete `dialogue_dry.wav`, `foley.wav` and `ambience.wav` (they're rebuilt from the plan on every run). Keep `dialogue.wav`.
7. **`reelforge clean <project>|--all [--dry-run]`:** converts any leftover `out/frames` into a master and then deletes it, removes animatic frames, and prints the bytes freed. Running it once over today's projects frees about **19 GB**.
8. **Editor:** show each project's disk size on the Projects page, plus a "Free space" action that runs `clean`.
9. **Tests:**
   - the render is skipped when the master and key match;
   - finish works from the master alone;
   - the frame endpoint returns the right frame;
   - `clean` with `--dry-run` deletes nothing.

## Separate decision (owner)
The `p7-bench-*` projects (morning, reference, signature, connect, draft) take up 11.6 GB. They're old benchmark runs. Once step 7 exists, they can be deleted outright or cleaned down to masters.

## Revision (owner, same day): keep only the final
The owner doesn't want a clean master either. Once `final_*.mp4` is written, `storage.finalize` deletes:
- `frames/`, `fonts/` and `stills_cache/`;
- the master, if there is one;
- the render key;
- every scratch WAV, including `dialogue.wav`.

What's kept:
- the final video;
- `out/audio` (the voice takes, which cost ElevenLabs credits);
- the small metadata: `render_plan.json`, `captions.ass`, `cover.json` and the preview stills.

What changes as a result:
- A caption, grade or shot change now means a full re-render.
- Cover stills come from the final video, which has captions burned in.
- `reelforge run --keep-master` keeps the old behaviour of packing a clean master.
- `reelforge clean` and the editor's **Free space** item apply the same rule to finished projects.
