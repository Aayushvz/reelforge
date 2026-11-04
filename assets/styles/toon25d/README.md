# Style asset pack: `toon25d` (2D cartoon characters in a 3D world)

This folder holds code and docs vendored from [mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts) (MIT). The pinned commit is in `upstream/UPSTREAM_COMMIT`.

- `upstream/SKILL.md`: the full pipeline and look values.
- `upstream/templates/bridge/`: three.js and Remotion source for the look: world, toon characters, ink, lens blur, grade, story and camera.
- `upstream/templates/audio/`: synthesized SFX, music and mix.
- `upstream/templates/scripts/`: stills, side-by-side and QA helpers.
- `upstream/references/STYLE_BIBLE.md` and `reports/`: measured look targets.

**Not included, on purpose:** `references/frames` and `references/sheets`. Those are frames from a privately studied channel, licensed for style study only. Fetch them locally from upstream when you need them for look QA. Never commit or publish them.

Plan and integration design: [`docs/superpowers/specs/2026-11-05-style-toon25d.md`](../../../docs/superpowers/specs/2026-11-05-style-toon25d.md).
