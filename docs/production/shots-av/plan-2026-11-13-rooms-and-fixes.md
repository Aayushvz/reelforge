# Plan: hero proportions, mouth, and six gamer/editor rooms (2026-11-13)

Owner's request: hands and legs look odd, make them proportional; the mouth and its movement feel odd; build at
least 5-6 dark gamer/editor rooms from his references (images 4-11), use them as backgrounds, and let the editor pick
the room and the part of it that sits behind the hero.

## A. Hero fixes
| Problem (from the owner's screenshots) | Cause in `blender/shotsav/hero.py` | Fix |
|---|---|---|
| Hands look like small doll hands | palm 5.4 cm, fingers 1.2 cm boxes, on a 31 cm wide head | hands about 1.4x (palm 7.5 cm, about 10.5 cm long), fingers as rounded tapered capsules, a thumb pad, cuffs that meet the wrist |
| The "think" fist floats at the shoulder | the pose target sits beside the jaw, not on it, after the head got narrower | re-solve the pose so the fist rests on the jaw; check all five poses on a hands sheet |
| Legs are blobs under the desk | each leg is one tube tapering to a point | seated legs: thigh to the knee, shin down, knee, jeans with a crease, sneakers sized to the feet; a modesty panel on the desk front so wides don't show the lap |
| Mouth reads as a dark crack | a thin slit cut into the head, shallow inset | a cartoon mouth about as wide as the eye spacing, soft upper and lower lips in a slightly darker tone, teeth and tongue when open, a rounder O |
| Mouth movement feels odd | one pose per letter blends hard, so it flickers | smoother viseme transitions, the jaw opening follows the voice's loudness, M/B/P closures held 2-3 frames |

Evidence: a hands-and-legs sheet, a mouth sheet, and a 6 s lip-sync clip on a real ElevenLabs line.

## B. Six gamer/editor rooms (original 3D in Blender, inspired by references 4-11)
| Room | Inspired by | Key pieces |
|---|---|---|
| Editor Night | 4, 5 | wide window with blinds onto a purple city, three monitors, strong back glow |
| Streamer Den | 6, 8 | ring light, hexagon wall lights, mic arm, rainy city window, three curved monitors |
| Neon Shelf Room | 7 | pink neon strips, shelves with figures and plants, RGB PC tower, headphones |
| Moon Window | 11 | big window with moon and clouds, fairy lights, lava lamp, a cat on the sill, bedside corner |
| Retro Bedroom | 9 | CRT on a cabinet, shelves, a neon sign with our own word, rug and cushions, ceiling LED cove |
| Studio Apartment | 6 (photo) | curtains, warm lamp, speakers, plants, headphones on the wall, a sofa |

Every room keeps the desk two-hander contract (desk, monitor, `Mark_A`/`Mark_B`, Key/Rim/Fill/Glow), real LEDs and
practicals, and real depth of field. Risk: a purple jacket in purple rooms loses separation; keep backgrounds darker
and cooler behind the hero, use pink and cyan accents and a rim light, and measure jacket contrast per room.

## C. Pick the room and the part of it behind you (editor)
Each room gets a wide panorama still. In the Room section you pick the room, then drag a 9:16 window across the
panorama to choose what sits behind you (the window and moon, the shelves, the ring light). Saved as `room_view`
(pan and height) and applied in Blender by turning and shifting the room around the desk, so the light, depth of
field and bokeh stay real.

## D. Order and gates
1. Hero fixes + sheets, owner checks.
2. Rooms, two at a time, with stills, owner checks.
3. The frame picker in the editor.
4. Re-render "I just asked you to fix one thing" at full quality in a new room.

## Decision
Original 3D rooms modelled after the references (recommended): our own art, consistent with the characters, real
depth and lighting, safe to publish. The alternative, using the reference images themselves as flat backdrops, is
faster but those images are other people's art (some carry logos or text) and would look flat behind a 3D character.
