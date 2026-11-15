# Background music for Shots-AV (2026-11-15)

**Status:** approved and built on 2026-11-15. Phases 1 and 2 plus the Viral now slots are done; beat-snapped cuts (phase 3) are not built.

## Revision (owner, same day): copyrighted and viral tracks are fine
The owner has the rights to use trending, copyrighted songs, so the viral tracks go **inside the video**. This replaces the "two layers" idea and most of the licensing caution below; the sections underneath still apply except where this section changes them.

**What changes**
- **The library is the owner's own audio files.** Drag in files or a whole folder (mp3, wav, m4a, flac). Each one is analysed and added to the library. Vocals are allowed.
- **I won't build a downloader.** Ripping audio from YouTube, Instagram, TikTok or Spotify breaks those services' terms and is not something this project will automate. The owner supplies the files from wherever they legitimately hold them.
- **"Viral now" becomes the shopping list.** The trending names (from the research) show as empty slots with an "Add file" button. Once a file is attached, that track is selectable and gets a Viral bonus in auto-pick.
- **A small free starter pack stays optional** (a handful of CC0 and Pixabay instrumentals), so the feature works on day one. It isn't required.
- **No credit lines or licence badges for the owner's own tracks.** CC-BY handling only applies to the optional starter pack.
- **The music-free export stays as an optional extra** (off by default now).

**What this adds to the build**
1. **Import and analysis** (`reelforge/music.py`, `ffmpeg` only):
   - duration, a loudness curve per second, and the loudest 15–45 s section;
   - `has_vocals` is set by the owner on import (default: yes for songs), since a reliable automatic check needs ML;
   - BPM is optional and manual for now.
2. **Hook window per track.** For songs, auto-pick plays the **hook or chorus, not the intro**: the loudest sustained section (or the section the owner marks in the editor) is used as `start`, and the reel is cut to fit it.
3. **Vocal-aware mixing.** Tracks with vocals get a deeper duck while someone is talking (about −14 dB instead of −9 dB), a lower base level (about −26 LUFS), and a high-shelf cut around 2–4 kHz under speech so lyrics don't fight the voice. In the pauses and on the end card they rise.
4. **Tagging.** After import, mood and energy tags are suggested from the loudness curve and the title, and the owner can fix them in one click. Tagged tracks feed the same script-based auto-pick as before; a track marked "viral" scores higher.
5. **Editor.** The Music card gets an "Add songs" drop zone and a Hook marker on the preview waveform. The Viral now list shows the empty slots and their state (file attached or not).

**Decision for you:** how will you add the tracks? The default is that you save the audio files into one folder (or drop them in the editor) and I take it from there.

## Revision 2 (owner, same day): I source the tracks, no credits, manual add stays
This replaces the "you supply the audio" and credit parts of the first revision.

- **I add the tracks.** The built-in library is filled by me from free sources that need **no attribution**: Pixabay Music and CC0 tracks (Free Music Archive CC0, plus similar public-domain libraries). About 40 instrumental tracks, 3–6 per genre, chosen by script mood.
- **No credit anywhere.** No credit line in the editor, no `music_credit.txt`, no Copy credit button, no licence badges. Because of that I will **not** include Creative Commons "BY" tracks: their licence legally requires credit. That includes Kevin MacLeod's meme staples ("Monkeys Spinning Monkeys", "Sneaky Snitch") unless the owner buys his no-credit licence. Tracks whose licence I can't confirm as no-credit are dropped.
- **Viral commercial songs can't be fetched by me.** There is no legitimate source I can download them from (and ripping from YouTube, Instagram, TikTok or Spotify is something I won't build). They stay as the **Viral now** slots. Each has an **Add file** button, and once the owner attaches a file it joins auto-pick with the viral bonus.
- **Manual add in the UI, for later use** (kept from the first revision):
  - drag in files or a whole folder, in the Music card and on the Library page's Music tab;
  - tags, hook marker and vocals flag per track, editable afterwards;
  - owner tracks are stored in `assets/music/mine/` (git-ignored) and never overwritten by the built-in pack.
- **Downloads:** the approval of this plan covers about 40 tracks (about 200 MB). The full list (title, source, licence page) goes into `assets/music/catalog.json` for the owner to see before anything is kept.

## Goal
Shots-AV reels get a background music bed that is **picked automatically from the script** and mixed under the voices the way viral animated and conversation videos do it: quiet, ducking while someone speaks, rising in the pauses, fading out on the end card. The owner can override the pick, upload their own track, or turn music off.

## What exists today
- `reelforge/ambience.py` `add_av_sound(..., music)` already mixes one music file under the dialogue: loops it, normalises it to −24 LUFS, 0.8 s fade-in, 1.2 s fade-out.
- `find_music(project)` only finds the owner's own `music.mp3|wav|m4a|flac` in the project's `media/`. The Shots-AV Sound section has an "Add your music" button for exactly that.
- Gaps:
  - the music level is fixed, so there's no ducking under speech;
  - there is no music library (`editor/src/data/catalog.ts` has `MUSIC = []` and the Library page's Music tab is empty);
  - nothing chooses a track;
  - nothing records a track's licence or attribution.
- Each line already carries `emotion`, `intensity` (0–1) and `mood` (`calm | success | panic | awkward | reveal | sad`), plus a `punchline` flag. That is enough to profile a script without any AI call.

## What the research found (read this first)
Searched on 2026-11-15. The trend roundups are general Reels and TikTok lists. **I found no ranked list specific to animated or conversation reels**, so the viral list below is a starting point to curate, not a verified top 10.

1. **Most viral Instagram and TikTok audio is commercial vocal songs**, for example:
   - Taylor Swift, "Patient Zero" (top Instagram audio the week of 28 Oct);
   - Tate McRae, "Housewife";
   - Cobra Starship, "Good Girls Go Bad";
   - Lipps Inc., "Funkytown".

   Vocals fight the voice-over, and none of these can be downloaded or bundled by us.
2. **Trends that fit conversation videos**:
   - "Comedy Corridor" by Finley Reed, used under funny, relatable and awkward clips (TikTok);
   - the "Do you wanna?" audio (Michael Jackson, "Human Nature"), a dramatic mini-conversation trend (Later, June 2026);
   - "Be Like a Woman" by Chris Rainbow;
   - viral spoken clips such as "This is private property", which are dialogue, not music.
3. **The classic meme-instrumental pool** is free-to-use library music. "Monkeys Spinning Monkeys" by Kevin MacLeod is repeatedly cited as one of the most-used sounds on TikTok, and MacLeod's catalogue is free under CC BY (credit required).
4. **Licensing facts that shape the design:**
   - Pixabay music: commercial use allowed, no credit required. A "free" licence still doesn't prevent a Content ID claim on the platforms.
   - Creative Commons tracks need a credit line in the caption.
   - Copyrighted trending songs play legitimately only when added **inside the Instagram app**; Instagram's rules for business accounts are stricter.

**Design consequence:** two layers.
- **Licensed music we can ship inside the video** (the auto-picked bed).
- **A "viral now" watchlist of names only, with no audio.** The reel is also exported without music so the owner can add the trending sound in Instagram itself.

## Design

### 1. Music library
- `assets/music/catalog.json` is committed. `assets/music/tracks/*.mp3` is git-ignored (about 3–6 MB each, so about 150–250 MB for 40 tracks), and `tools/fetch_music.py` re-downloads them from the recorded URLs and checks a sha256 for each.
- One entry per track:
  - `id`, `title`, `artist`, `source`, `url`;
  - `licence` (`CC0 | CC-BY-4.0 | Pixabay | owner`) and `credit` (the exact attribution line, required for CC-BY);
  - `bpm`, `duration`, `start` (seconds of silent intro to skip), `loopable`;
  - `energy` (0–1) and `moods` (a weight per genre);
  - `viral` (bool) and `viral_note`.
- Genres: `comedy`, `quirky`, `suspense`, `wholesome`, `hype`, `lofi`, `sad`, `romantic`, `reveal`, `drama`.
- Target about **40 tracks, 3–6 per genre**, all instrumental. Seed sources:
  - Kevin MacLeod, incompetech (CC BY 4.0), for the meme staples such as "Monkeys Spinning Monkeys" and "Sneaky Snitch";
  - Pixabay Music;
  - Free Music Archive (CC0 and CC BY only).

  Each track's licence page is read at download time and recorded; anything that is unclear is dropped.
- "My music": the owner's uploads join the same library with tags they choose (their responsibility, never downloaded by us). The existing `media/music.*` upload keeps working and always wins over an auto-pick.

### 2. Auto-select (`reelforge/music.py`, standard library only)
**Script profile** from the lines:
- an emotion histogram weighted by intensity;
- the mood mix;
- the punchline count;
- speaking pace (words per second);
- total length.

A genre vector comes out of that, for example:
- `comedy` ← deadpan, smug, awkward, punchlines;
- `suspense` ← panic, worried;
- `wholesome` ← happy, calm;
- `hype` ← success, high intensity;
- `sad` ← sad, worried at low intensity.

**Score per track** = genre match (cosine similarity) + energy match to the script's average intensity + length fit − a repeat penalty (the last N reels' picks are stored in `projects/.music_history.json`) + a small bonus for `viral` tracks. Voiced music with vocals is never picked.

**Output:** the top 3, each with a one-line reason ("comedy 0.91: deadpan and punchline-heavy"). The top one is picked deterministically per project (seeded), so the preview and the render agree. Shuffle moves to the next one.

**Project field** in `performance.json`:
```json
"music": {"mode": "auto|track|none", "id": "sneaky_snitch", "volume": 0.5, "duck": true}
```
Missing means `auto` for new reels and `none` for old projects, so existing reels don't change.

### 3. Mixing (`ambience.add_av_sound`)
- **Sidechain ducking:** `sidechaincompress` keyed on the dialogue pulls the music down by about 9 dB while someone speaks and releases within about 400 ms. It sits at about −22 LUFS in the pauses.
- **Start and trim:** begin at the track's `start`, loop with a 1.5 s crossfade when it's shorter than the reel, and fade out over the end card (with a +2 dB lift as the end card appears).
- **Two mixes from one render**, because the final keeps only the finished video:
  - `final_9x16.mp4`, with music;
  - `final_9x16_nomusic.mp4`, with the voices, room tone and foley but no music. The video stream is copied, so it takes seconds and about 75 MB. This is the one for adding a trending Instagram sound. It is on by default and can be turned off.
- **Credits:** for CC-BY tracks, `out/music_credit.txt` holds the exact caption line, and the editor shows a "Copy credit" button.

### 4. Editor
- **Shots-AV, Sound section:** replace "Add your music" with a Music card:
  - a mode switch (Auto / Library / My upload / None);
  - the auto pick with its reason and the two runners-up, plus Shuffle;
  - a volume slider and a "Duck under voices" switch;
  - the licence badge, and "Copy credit" when one is needed.
- **Library page, Music tab:** fill the empty tab.
  - Cards with a 30 s preview player, mood chips, BPM, a licence badge and a **Viral** badge.
  - Filters by mood and by licence.
  - A **Viral now** tab: a name-only list of trending sounds (title, artist, where it's trending, a date, the source link, "add in the Instagram app"), shown with the reminder to export the music-free version.
- **Preview:** the animatic includes the music, so the owner hears the pick before the long render.

### 5. Trend watchlist
- `assets/music/trending.json` holds metadata only: title, artist, platform, genre guess, note, date and source URL. It is seeded from the research above.
- It is refreshed by asking Claude to re-run the research (a scheduled weekly task is optional). I don't scrape social sites automatically: it's brittle and runs against their terms.
- When a licensed track in the library matches a trending name, it gets the Viral badge.

### 6. Storage and rules
- No change to the "keep only the final" rule. `music_bed.wav` is already deleted after each render. The only new kept file is the small `music_credit.txt`.
- The music downloads are the one-off ~200 MB step, covered by your approval of this plan.
- No paid tools and no accounts: every source is free and no sign-up is needed. If a source requires an account, that track is skipped.

## Build order
| Phase | What | Done when |
|---|---|---|
| 1. Core | `catalog.json` schema and validator; `fetch_music.py`; `music.py` profile and scoring; sidechain ducking and trim/loop in `add_av_sound`; `performance.json` field; CLI `reelforge music pick <project>`; credit file; tests | `reelforge run` on a sample picks and mixes a track, ducked under the voices |
| 2. Editor | Music card in the Sound section; Library Music tab with previews; music-free export; animatic with music | You can hear, change and shuffle the pick, and copy the credit |
| 3. Trends and polish | `trending.json`, the Viral badge and Viral now tab; optional snap of shot cuts to the beat (within ±3 frames, never breaking the existing cut rules) | Watchlist visible; beat-snap behind a switch |

## Tests
- Catalog validator: a CC-BY track without a `credit` fails; an unknown genre fails; no vocals allowed.
- Selector: a deadpan, punchline-heavy script picks comedy; a sad script picks sad; deterministic for a given seed; the repeat penalty works; a script that is too short or long still returns a valid track.
- Mixing: measured music level during speech is at least 6 dB below the level in pauses; the output length equals the reel's length; looping has no click (the crossfade holds).
- The music-free file has an identical video stream and no music energy.
- Editor typecheck, plus a browser check of the Music card and the Library tab.

## Decisions for you
1. **Approve the two-layer approach** (licensed bed inside the video, trending songs as names plus a music-free export). This is the recommended default. Putting the actual trending songs inside the video isn't something we can legally download or bundle.
2. **OK to download about 40 tracks (about 200 MB)** from the free sources above. I will list every title, source and licence for you to see in the first commit's `catalog.json` before anything is kept.
3. **Attribution:** CC-BY tracks need the credit line in the caption. The default is to include them in the library with a badge and a Copy credit button. If you'd rather avoid any credit requirement, I'll restrict the library to Pixabay and CC0 tracks.
