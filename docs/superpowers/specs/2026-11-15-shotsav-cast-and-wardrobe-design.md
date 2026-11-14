# Shots-AV: pick the cast, see the wardrobe (2026-11-15)

## Problem
In the Shots-AV editor:
- The "You" speaker is always the low-poly hero.
- Matt, Freya and Mina, the realistic imported characters, cannot be picked in Shots-AV.
- The Hero panel is a column of dropdowns with no picture.
- The stage stays empty until a shot is clicked, so changing the outfit shows nothing.

## Decisions (owner, 2026-11-15)
- Both speaker slots (You and Buddy) can be any of these:
  - the low-poly hero ("AV hero");
  - Matt, Freya or Mina;
  - one of the four bots.
- Matt, Freya and Mina **sit** at the desk, with a seated pose made for each of their rigs (CC4, Rigify, ARP).
- The outfit becomes a grid of visual cards.
- A live look preview shows the current cast in the current room.

## 1. Cast model (engine, `reelforge/engines/shots_av.py`)
- **Slots.** The "You" slot is the character named `me` (the editor's `HERO`); the other speaker is the buddy slot. Today `cast()` finds the hero by `model == AV_HERO`. It changes to:
  - the `AV_HERO` character, else `me`, else the first character;
  - the other character is the buddy.
- **Kinds.** Each slot's model is one of three kinds:
  - `av_hero`: `ensure_hero(options)`, as today;
  - `buddy_*`: `buddy_blend(model)`, as today;
  - an imported id (`matt`, `freya`, `cute_girl`): `ensure_seated(id, slot)`, below.
- **Acting by kind.**
  - AV hero: `hero_acting` (blink on cuts, think → type pose, `HandL`/`HandR` stepped), `measure: head`.
  - Bot: `buddy_acting` (`BuddyCtrl`), `measure: body`.
  - Imported: the shared acting `render_plan.py` already does for every contract character:
    - ARKit face tracks (lip sync, eyelines);
    - head turns toward the speaker;
    - `Body` breathing and lean;
    - `ElbowL`/`ElbowR` talk beats.
    - On top of that: `smooth_mouth` on its lines, and blinks on cuts to it. It uses `measure: head`.
- **Sound plan.** Key taps play only while an AV hero is cast and in his typing pose. Buddy blips play only for a bot.
- **Caption tints.** The AV hero uses his jacket colour; a bot uses its shell colour; an imported character uses its catalog accent (`ACCENTS` in the engine: Matt `#6E8FB8`, Freya `#C9A27A`, Mina `#7FA36B`).
- **Schema.** `schema.py` accepts these models for `shots-av` characters. A project with two bots or two AV heroes is allowed; it is the user's choice.

## 2. Seated imported characters (`blender/shotsav/seated.py`, run through `build_shotsav.py`)
- `ensure_seated(id, slot)` builds `assets/build/shotsav/seated_<id>__<slot>.blend` from `assets/build/<id>.blend`, once, and caches it like the hero builds.
  - Slot `you`: the hero's chair (`Mark_A`), facing −Y.
  - Slot `guest`: a second chair at the desk's left end (seen from the camera), turned toward the hero and the camera. The build adds its own guest chair to the character file, so rooms need no rebuild.
- **The pose.** It is set in world space, so it works for any rig, using bone names per character from `imported.py`. New keys:
  - `legs`: thigh, shin and foot for each side;
  - `fk`: the property flips that put Rigify and ARP legs into FK;
  - `seat_drop`.
  - Steps:
    1. Switch the leg IK to FK (Rigify `IK_FK`, ARP `ik_fk_switch`).
    2. Rotate each thigh so it points forward (−Y) and slightly down.
    3. Point each shin down.
    4. Lower and move back the armature (a child of `CHAR_root`) so the pelvis sits on the seat (top 0.515 m) with the feet on the floor.
    5. Rest the forearms forward on the desk through `delta_rotation_euler` on `ElbowL`/`ElbowR`. `render_plan.py` keys only `rotation_euler`, so the talk beats ride on top.
- **Quality.** Pose only. No geometry, texture or shape-key change (CLAUDE.md).
- **Check.** One still for each character in each slot, rendered in a room and looked at:
  - no knees through the desk;
  - hands on or above the desktop;
  - face framed by `av_hero_34` / `av_buddy`.

## 3. Editor (`editor/src/pages/shotsav/ShotsAvWorkspace.tsx`)
- **Cast section** at the top of the Look column, with two rows: **You** and **Buddy**.
  - Each row is a strip of cards: AV hero, Matt, Freya, Mina, Claude, ChatGPT, Figma, Nova.
  - The images are the existing thumbnails: `AvThumb` for the hero and bots; the editor's `char_<id>_o0.jpg` for the imported three.
  - Picking a card sets `characters[slot].model` and the default voice for that model. A voice the user chose by hand is kept.
- **Hero dials** (outfit, jacket, hair, glasses, headphones, skin, beard, stubble) show only for the slot cast as the AV hero. Imported characters show a one-line note: "Realistic model, its own outfit."
- **Outfit cards.** The Outfit select becomes a 3-column grid of cards, one per outfit, each with a thumbnail (`outfit_<id>`).
  - The thumbnails are built by `reelforge thumbnails --style shots-av` (new kind `outfit_<id>`: a bust of the default hero in that outfit, 480 px).
  - They are built lazily through the existing `shotsavThumb` endpoint.
  - The jacket swatches stay under the grid.
- **Look preview.** When no shot is selected, the stage shows a "Look" still.
  - It is a draft render of the "You" slot from `av_hero_34`, in the current room, with the buddy in frame where the angle shows it.
  - It re-renders about 1.2 s after the last change to the cast, outfit, look dials or room.
  - A spinner shows while it works; the previous still stays until the new one lands. Only the newest request's result is shown.
  - Server: `POST /api/projects/:id/shotsav/look`, which runs `reelforge shots-av look <dir>` and returns `{still}`.
  - Engine: `look()` builds a one-shot plan from the project's estimated timing (like `animatic()`) and renders a single still.
  - Renders run one at a time; a request made while one is running waits and only the latest runs.
- **Names.** Speaker labels, caption dots and shot tiles use the cast: "Matt", not "You", when Matt is cast. The "me"/"buddy" keys stay.

## Errors
- A missing imported build (`assets/build/<id>.blend`) shows the card disabled, with "Not built yet". Nothing else breaks.
- A failed look render shows the error line under the stage and keeps the last still.

## Tests
- Engine (pytest):
  - `cast()` for all combinations;
  - asset routing (hero, bot, imported) in `build_plan`;
  - `caption_tints` for an imported character;
  - `sound_plan` with no AV hero;
  - schema accepts imported models in shots-av.
- Seated: the `imported.py` leg tables name real bones (a data test against the names recorded in the spec tables).
- Editor: `npm run build` passes. Browser check:
  - cast Matt as You and Freya as the buddy, and see the look preview update;
  - pick an outfit card on the AV hero, and see the preview update.

## Out of scope
- New outfits for Matt, Freya or Mina.
- Typing hands for the imported characters.
- Rebuilding the rooms.
