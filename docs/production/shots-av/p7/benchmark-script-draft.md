# P7 benchmark script (draft for the owner)

Original, in the owner's world (design, clients, late nights). It follows the reference's 20-shot timing table
(prompt section 2.3) line for line: same speakers, lengths sized to each slot, wides on lines 6, 13 and the closer.

| # | Who | Emotion | Line | Slot (s) |
|---|---|---|---|---|
| 1 | Me | neutral | Claude, the client wants the logo bigger. | 3.3 |
| 2 | Claude | happy | Love that for us! | 1.7 |
| 3 | Me | neutral | She said make it pop. | 2.3 |
| 4 | Claude | deadpan | Pop is not a size. I tried forty percent. | 4.2 |
| 5 | Me | neutral | Forty percent of... | 1.3 |
| 6 | Claude | smug (wide) | Of the entire homepage. | 2.2 |
| 7 | Me | neutral | That's a billboard, not a logo. | 1.9 |
| 8 | Claude | deadpan | Billboards close deals, apparently. | 1.8 |
| 9 | Me | surprised | Says who? | 1.2 |
| 10 | Claude | neutral | Every email you forwarded. | 1.8 |
| 11 | Me | surprised | You read my client emails? | 1.9 |
| 12 | Claude | happy | All of them. It's how I knew she'd say yes. | 3.9 |
| 13 | Me | neutral (wide) | ...Fair enough. | 1.3 |
| 14 | Claude | smug | So I also made it gold. | 3.1 |
| 15 | Me | confused | Why gold? | 1.9 |
| 16 | Claude | neutral | When they say make it pop, they mean make it feel expensive. | 4.6 |
| 17 | Me | happy | Okay. That's actually smart. | 1.9 |
| 18 | Claude | surprised | I'm always smart! | 1.4 |
| 19 | Me | deadpan | She just replied. | 2.2 |
| 20 | Me | deadpan (closing wide) | She wants the old logo back. | 4.9 |

Renders after approval: `av_studio_night` with Claude, once `grammar: "reference"` and once `"signature"`, then the
side-by-side and rubric scoring; one more in `av_studio_morning`. Voices: about 520 characters of ElevenLabs.
