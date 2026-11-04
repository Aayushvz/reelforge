# toon25d Remotion project

This is the Remotion and three.js renderer for the `toon25d` style. `src/videos/bridge/` is an unchanged copy of
`assets/styles/toon25d/upstream/templates/bridge/` (MIT, mromidev/claude-animated-shorts). For the plan and the spike results, see
`docs/superpowers/specs/2026-11-05-style-toon25d.md`.

```bash
cd engines/toon25d/remotion && npm install
export REMOTION_TMP=D:/remotion-tmp   # bundles copy public/ into temp: keep it on a big drive
node scripts/spike-render.mjs out 0,75,140,900 150 1   # stills plus the first 150 frames, with timings
CONC=3 node scripts/spike-render.mjs out "" 90 1       # concurrency test
npx remotion studio src/index.ts                        # interactive preview
```

Kenney CC0 props (Nature Kit, Fantasy Town Kit) go in `public/bridge/kenney/<name>.glb`. They're git-ignored, and the scene renders without them.
`scripts/bridge-stills.mjs` is upstream's still helper. It's kept for reference, and it hard-codes a Chrome path.
