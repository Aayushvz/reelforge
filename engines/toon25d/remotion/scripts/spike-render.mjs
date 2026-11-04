// toon25d spike: bundle once, render a few stills and the first N frames, print timings.
// usage: node scripts/spike-render.mjs <outDir> <stillFrames,comma> <clipFrames> [scale]
import fs from "node:fs";
if (process.env.REMOTION_TMP) { fs.mkdirSync(process.env.REMOTION_TMP, { recursive: true }); process.env.TEMP = process.env.TMP = process.env.REMOTION_TMP; }
const { bundle } = await import("@remotion/bundler");
const { renderStill, renderMedia, selectComposition } = await import("@remotion/renderer");
const path = await import("node:path");
const [outDir = "out", stills = "0,60,120", clipFrames = "150", scale = "1"] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const browserExecutable = process.env.REMOTION_CHROME || null;
const chromiumOptions = { gl: process.env.GL || "angle" };
const onBrowserLog = (l) => { if (l.type === "error" || l.type === "warning") console.log(`[${l.type}]`, l.text.slice(0, 300)); };
let t = Date.now();
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve("public") });
console.log("bundle", ((Date.now() - t) / 1000).toFixed(1) + "s");
const composition = await selectComposition({ serveUrl, id: "BridgeShort", browserExecutable, chromiumOptions, onBrowserLog });
for (const f of stills.split(",").filter(Boolean).map(Number)) {
  t = Date.now();
  await renderStill({ composition, serveUrl, frame: f, output: `${outDir}/still_${f}.jpg`, imageFormat: "jpeg", jpegQuality: 90, scale: Number(scale),
    browserExecutable, chromiumOptions, timeoutInMilliseconds: 240000, onBrowserLog });
  console.log("still", f, ((Date.now() - t) / 1000).toFixed(1) + "s");
}
const n = Number(clipFrames);
if (n > 0) {
  t = Date.now();
  await renderMedia({ composition, serveUrl, codec: "h264", crf: 16, frameRange: [0, n - 1], outputLocation: `${outDir}/clip_${n}f.mp4`, scale: Number(scale),
    browserExecutable, chromiumOptions, concurrency: Number(process.env.CONC || 1), timeoutInMilliseconds: 240000, onBrowserLog,
    onProgress: ({ renderedFrames }) => { if (renderedFrames % 30 === 0) console.log("frames", renderedFrames, ((Date.now() - t) / 1000).toFixed(1) + "s"); } });
  const s = (Date.now() - t) / 1000;
  console.log(`clip ${n} frames ${s.toFixed(1)}s = ${(s / n).toFixed(2)} s/frame = ${(s / (n / 30)).toFixed(1)} s per video-second`);
}
