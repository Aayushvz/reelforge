# Expressive voices, varied camera, new places, auto-posting (2026-11-17)

**Status:** built 2026-11-17, except auto-posting, which the owner skipped. As built:
- expressions in `reelforge/direction.py` (word table, script parser, auto-direct), notes as ElevenLabs tags, stability 0.3;
- face check in `blender/clear_view.py`;
- opening montage, 56 angles and the history file in `reelforge/direct.py` and `reelforge/angles.py`;
- places as render-time furniture kits in `blender/shotsav/places.py`. The hero keeps his seated pose; the sofa, bed or window bench sits at the chair's height and a laptop surface at the desk's, so the typing, the buddy and every angle carry over. Mid-line emotion switches are still to do.

The owner's four asks:
1. Every voice line should carry an expression, written in the script.
2. The opening needs 5–10 different face angles, and no object may ever cover the speaker's face.
3. Shoot in more places than the desk: a sofa, a bed, a window, and so on.
4. Post to Instagram and YouTube automatically, with captions, on a schedule.

---

## 1. Expressive voices

### Why every take sounds neutral today
The pipeline can already act. `reelforge/voice.py` turns a line's `emotion` and `intensity` into an ElevenLabs audio tag (`[excited]`, `[frustrated]`, `[on the verge of tears]` …), which the v3/v4 models perform. It also lowers `stability` for intense lines.

The gap is the script. A pasted script (`parseScript` in `editor/src/lib/shotsav.ts`) gives **every line emotion `neutral`, intensity 0.5, mood `calm`**. So no tag is sent, stability stays at "Natural", and the face animates neutral too.

Every recent reel shows it:
- `untitled-desk-reel-3`, `-6`, `-8`, `-10` to `-15` and `untitled-reel` are 100% neutral;
- only the hand-written P7 benchmarks and "i-just-asked-you-to-fix-one-thing" vary.

### The script format (what the owner writes)
One line per row: speaker, the expression note in square brackets, then the words. Sound cues can go anywhere in the line.

```
Me: [frustrated] Claude, I've been fixing this bug for two hours.
Claude: [cheerful, proud] Absolutely! I fixed it. Everything works perfectly.
Me: [deadpan] Then why is the screen blank?
Claude: [nervous laugh] Interesting... [clears throat] let me investigate.
Me: [very angry] I've shown you this exact error SIX times.
Claude: [whispering] ...have you tried turning it off and on again?
Me: [long sigh, defeated] I'm going to bed.
```

Rules:
- **`Name: [note] text`.** The note sits right after the colon. `( )` works as well as `[ ]`, and several notes can be separated by commas.
- **Strength comes from the words.** `very` / `really` / `super`, a trailing `!!` or CAPS make a line intense. `slightly` / `a bit` / `quietly` make it soft.
- **Notes inside the line are sound cues** (`[laughs]`, `[sighs]`, `[gasps]`, `[clears throat]`, `[pause]`). They are performed at that spot and never appear in the captions (the captions already drop bracketed text).
- **Lines without a note get one automatically** (see auto-direct below), so old scripts improve too.
- **Optional extras:**
  - `*` at the end of a line marks a punchline: the camera punches in and the music weights comedy.
  - `#beat` forces a wide shot.
  - A blank line between rows gives a longer pause.

### How a note is used (four places)
1. **Voice:** the note goes to ElevenLabs as written. v3/v4 accept free-form tags, so "nervous laugh" or "on the verge of tears" work as-is, and the owner's wording is respected. Directed lines use stability about 0.3. ElevenLabs' guidance is that lower stability follows tags better; today we use 0.5, which mutes them. Each line is generated on its own, so the energy resets every line.
2. **Face:** a word table maps about 120 expression words to the 11 face emotions plus intensity. For example, frustrated → annoyed 0.8, defeated → sad 0.6, cheerful → happy 0.6, smug/teasing → smug, panicking → worried 0.9. The face, blinks, nods and brows then match the voice. An unknown word keeps its voice tag, and the face falls back to the closest synonym, else neutral.
3. **Camera:** the emotion's mood (tense, comic, soft, warm) already steers the angle choice. Expressive scripts get expressive angles for free.
4. **Music:** already reads emotions, so the auto-pick improves too.

### Auto-direct (lines without a note)
A rules engine with no AI call and no cost. It looks at:
- punctuation: `?!`, `...`, CAPS;
- keywords: "finally" / "again" / "why" / "sorry" / "love";
- position: the first line is a hook, the last a landing;
- the reply pattern: a short reply after a long complaint reads as deadpan.

The editor shows each line's expression as a chip (blue for chosen by you, grey for auto) that can be changed with a click. A **Direct all** button fills every empty line. When the owner is working in a Claude session, Claude can direct the whole script with the same chips, as a better-quality option.

### Retakes and cost
- A take is cached per voice, words and note. Changing a note makes a new take, which uses ElevenLabs credits. The editor shows the character count before generating ("12 lines, about 900 characters").
- **Retake** on a line asks for a fresh performance of the same note. The last 3 takes are kept, and the owner picks the best.
- Existing projects keep their old takes until a line's note changes, so nothing is regenerated by surprise.

### Phase 2 (after the first pass)
Mid-line emotion changes: `[calm] It's fine. [snapping] IT'S NOT FINE.` The face switches expression at the word where the tag sits, using the per-word timings we already get from ElevenLabs.

---

## 2. Camera: a varied opening, more angles, faces always clear

### What happens today
- `reelforge/direct.py` (`plan_shots_av`) assigns each line a role (hero single, buddy single, wide). `reelforge/angles.py` (`Director`) then picks one of 36 angles.
- The first line always opens on the hero three-quarter set-up. The director also avoids "punch" angles for the first two shots, so every reel starts the same way.
- One shot per line means a 6-second opening line is one static angle.
- Nothing remembers which angles earlier reels used, so reels look alike.
- **Nothing checks that the face is visible.** The monitor, the buddy, the mic or a lamp can sit between the camera and the face. The only ray-cast test (`blender/shotsav/imported_rooms.py`) runs once when an imported room is built, from fixed directions, and deletes blocking furniture. It doesn't know about each shot's real camera.

### 2a. The opening montage (first 4–7 s)
- **What it is:** the first one or two lines are cut into **5–10 quick shots (0.5–0.9 s each), every one a different face angle**: straight on, three-quarter, low, high, profile, extreme close-up, over the buddy, from the monitor, top-down, dutch, plus small push-ins. It's the "who is this, look at that face" hook these reels use.
- **Cut placement:** cuts land **between words**, using the per-word timings from ElevenLabs, so no word is chopped and the lip-sync stays continuous.
- **The buddy's reply** gets 2–3 fast angles too, then the reel settles into normal coverage.
- **Editor control:** Opening = **Montage** (default) / **Classic**, and the montage length (5–10 cuts).

### 2b. More angles (36 → about 60)
New families, all defined relative to the subject, the same way as today, so they work in every room and place:
- **Through-the-screen:** from inside the monitor or laptop, looking out at the face.
- **Phone point of view**, and a mirror or window reflection where the room has one.
- **Camera moves:**
  - slow orbits (a 20–40° arc around the face);
  - a slider pass;
  - a crash zoom on punchlines;
  - a snap zoom to an extreme close-up;
  - a handheld drift-in.
- **Floor-level low angle, behind-the-head reveal** (opening on the back of the head, then turning to the face), high corner security-cam (comic).
- **Two-up split screen:** both faces side by side for fast back-and-forth.

### 2c. No repeats
- **Within a reel:** no angle repeats until every suitable angle has been used, and no two neighbouring shots share a lens and side.
- **Across reels:** `projects/.angle_history.json` (like the music history) remembers the last 5 reels' angles, opening and place. The director penalises them, so consecutive reels open and look different.
- **Seed:** every reel already gets its own seed, and Reroll angles in the editor stays.

### 2d. Face-visibility guarantee (the occlusion check)
A new step in Blender, before any frame is rendered, inside the existing shot-measure pass:
1. **Sample:** for every shot, at its first, middle and last frame (so the camera move is covered), cast rays from the camera to **14 points on the speaker's face**: eyes, brows, nose, mouth corners, chin, cheeks, forehead.
2. **Measure:** count the rays blocked by anything except the speaker's own head. Also check that the face lies inside the frame, clear of the edges, and **not under the caption box**: the top captions can cover a face on low angles today.
3. **Fix it if blocked**, trying in order, re-checking after each try:
   1. nudge the azimuth ±5–15°;
   2. raise or lower the camera;
   3. dolly in past the obstacle;
   4. change the lens;
   5. hide the small blocking prop for this shot only (a mic, a lamp or a plant). Films call this a "cheat"; the monitor and the buddy are never hidden;
   6. swap to the next-best angle.
4. **Record** the result per shot (`face_clear: 0.97`). The editor's shot strip shows a green or amber dot, and the render refuses any shot under 90% visible.

The check is cheap (ray casts, not rendering). It runs in the stills preview too, so problems show up before a 15-minute render.

---

## 3. More places to shoot (not always the desk)

### What exists
- Each room has 1–3 "view spots" (`VIEW_SPOTS` in `blender/shotsav/rooms.py`), but these only move **where the desk sits**. The hero is always seated at the desk (`blender/shotsav/seated.py`).
- Several rooms already have furniture in the background that could become places to shoot:
  - the record-player room has a sofa;
  - the moon window and old bedroom have a bed;
  - the cafe has a counter and a window seat.

### The idea: "places"
A **place** is where the hero is and what he is doing. Each place has its own pose, prop, buddy position, key light and camera-safe angles.

| Place | Hero | Buddy | Fits rooms |
|---|---|---|---|
| Desk (today) | seated, keyboard | on the desk | all |
| Sofa | slouched back, laptop on lap | floating beside, or on the armrest | record-player room, studio apartment, editor night, neon den |
| Bed | cross-legged, laptop on the duvet | on the pillow or the bedside table | moon window, retro bedroom, old bedroom |
| Window seat | sitting sideways, knees up, phone | hovering at the glass | moon window, cafe day, studio night |
| Kitchen counter | standing, leaning, mug in hand | on the counter | studio apartment, a new kitchen corner |
| Beanbag / floor | low slouch, controller or phone | on the floor | gaming den, streamer den |
| Standing desk | standing, typing | on the desk | late office, studio morning |

### Build work
1. **Poses:** new pose functions next to `seated.py` (sofa slouch, cross-legged, sideways sit, standing lean, floor slouch). Each comes with its own idle motion (laptop typing, phone thumbing, mug sips, gestures), so the body language changes too.
2. **Props:** low-poly sofa, bed, beanbag, counter, laptop, phone and mug, in the Shots-AV brand style and made procedurally like the rooms. Where a room already has the furniture, it's reused.
3. **Placement per room:** each room gets 2–4 places with exact positions. A place is only listed for a room once the occlusion check passes for a set of test angles there.
4. **Camera:** the angle library is relative to the subject's head, so it carries over. Each place has a small "forbidden zone" list (inside the sofa back, through the bed headboard) and its own two wide shots.
5. **Variety rule:** consecutive reels avoid the same place, using the same history file as the angles.
6. **Editor:** a **Place** picker (Auto, Desk, Sofa, Bed, Window, Counter, Floor) with thumbnails, next to the room picker. Auto picks a place the room supports that the last reels didn't use.

**Start with 3 places in 5 rooms** (sofa, bed, window seat), prove the look, then add counter, floor and standing desk.

---

## 4. Posting automatically to Instagram and YouTube

### Is it possible? Yes, with one-time setup by the owner
There are two routes. The recommended one is the official APIs. They are reliable, work unattended, and are supported by both platforms.

| | YouTube (Shorts) | Instagram (Reels) |
|---|---|---|
| How | YouTube Data API, `videos.insert`, uploaded straight from the file | Instagram API content publishing, a Reels container with a resumable upload of the file |
| Login | "Connect YouTube" in Settings opens Google's sign-in in your browser; the token is saved only on this PC | "Connect Instagram" opens Meta's sign-in the same way |
| Scheduling | **Native:** upload as private with a publish time, and YouTube releases it, so the PC can be off | **Not native.** Our scheduler posts at the chosen time, so the **PC must be on and online then**; the editor server already runs in the background from the desktop icon |
| Needs | A Google Cloud project with the YouTube API on and an OAuth client | A Business or Creator Instagram account, a Meta developer app with the publishing permission; in development mode it works for your own account |
| Limits (verify at build) | Google lifted the old "unverified apps upload as private" rule on 2 Nov 2026; daily upload quota is far above our needs | About 100 posts a day (third-party figure) |

**What I can't do, and why:** the project rule and safety policy say Claude doesn't create accounts or API keys. **You create the Google Cloud project and the Meta app once** (about 20 minutes each). I'll write a click-by-click guide with screenshots of every screen. After that, "Connect" in the editor is your normal login, and every post after that is automatic.

### The Publish page (new, in the editor)
- **Per video:**
  - a caption written from the script: a hook line, 2–3 lines of context and hashtags, different per platform (Instagram caption; YouTube title, description and tags);
  - the cover frame from the Thumbnail Generator;
  - every field editable.
- **Queue:**
  - a calendar or list of scheduled posts;
  - per-platform times;
  - "best times" presets you set once (for example 7 pm IST daily);
  - status: waiting / uploading / scheduled / posted / failed, with retry.
- **Approval gate:** nothing is posted until you press **Approve** on that item. You can approve a whole week in one go; the scheduler only touches approved items.
- **Log:** posted links, and the time each went live.
- **Command line:** `reelforge post queue|approve|run-due|status`.

### Route 2 (fallback, no developer setup): your logged-in Chrome
- **How it works:** I open YouTube Studio and Instagram (or Meta Business Suite, which can schedule Reels) in your Chrome, upload the file, paste the caption and set the schedule using their own scheduler.
- **Upside:** it needs no developer apps.
- **Downsides:** it needs a Claude session running each time and your OK on each post, so it's not unattended. It's also more fragile, because websites change.
- **Best use:** to start posting this week while the API setup is done.

### Later
- **TikTok:** its posting API needs an app audit before public posting. The same Publish page can add it.
- **Facebook Reels:** comes free with the Meta app.

---

## Build order
| # | Work | Result |
|---|---|---|
| 1 | Script format + note parser + word table + stability change + auto-direct + chips in the editor | Every line has an expression; voices and faces act |
| 2 | Occlusion check + caption-box check + auto-fix | No shot with a covered face |
| 3 | Opening montage + no-repeat history + about 24 new angles | Different openings, 5–10 face angles up front |
| 4 | Publish page + YouTube API + caption writer + queue | Shorts go out on a schedule |
| 5 | Instagram API + the background scheduler | Reels go out on a schedule |
| 6 | Places: sofa, bed, window seat in 5 rooms; Place picker | Reels move off the desk |
| 7 | More places, mid-line emotion switches, more angles | Polish |

Steps 1–3 are code-only and fast, and fix the most visible problems first. Step 6 is the biggest piece (poses, props, testing every room).

## Tests
- **Parser:** every format variant (`[ ]`, `( )`, several notes, inline sound cues, `*`, `#beat`, intensity words and `!!`), and captions never show tags.
- **Word table:** every word maps to a valid emotion; unknown words keep their voice tag.
- **Occlusion:** a test scene with a box between the camera and the face must be fixed by a nudge or a re-pick; a clear scene must pass untouched.
- **Montage:** cuts land only between words; no angle repeats in the first 10 shots; reel-to-reel history changes the opening.
- **Posting:** a dry-run mode that builds every API request without sending it; the token never leaves `.reelforge.local.json`; nothing posts without approval.

## Decisions for the owner
1. **Script format:** is `Name: [note] text` with inline `[laughs]` cues good?
2. **Re-voicing old reels:** changing notes makes new ElevenLabs takes, which cost credits. The default is to re-voice only when you change a note.
3. **Posting route:** the official APIs (you do the one-time setup with my guide) are the recommended route; the browser route is available now as a stopgap. For Instagram's scheduled posts, the PC must be on at the posting time.
4. **First places:** sofa, bed and window seat, or a different three?
