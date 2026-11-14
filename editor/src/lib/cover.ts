// Cover images: one canvas renderer for the Thumbnail Generator preview, its exports and the auto-cover card.
// Layout is stored in fractions (positions of W and H, sizes of the short side), so a doc draws the same at any scale.

export type CoverLine = { text: string; color: string };
export type CoverDoc = {
  preset: string; width: number; height: number;
  lines: CoverLine[];
  font: string; weight: number;
  size: number;      // cap size, fraction of the short side
  tracking: number;  // letter spacing, em
  leading: number;   // line height, em
  x: number; y: number; // top-left of the headline block, fractions of W and H
  pill: { on: boolean; text: string; bg: string; color: string; size: number; x: number; y: number; maxWidth: number };
  focus: { x: number; y: number }; // which part of the frame survives a crop (0..1)
  zoom: number;
};
export type Layer = "headline" | "pill" | "frame";
export type Box = { x: number; y: number; w: number; h: number };
export type CoverDraft = {
  video: string; fps: number; width: number; height: number;
  frames?: string; // clean rendered frames: frame N is `${frames}/${N+1:04}.png`
  variants: { headline: string[]; caption: string; frame: number; time: number; shot: number | null; still?: string }[];
};
export const cleanFramePath = (dir: string, frame: number) => `${dir}/${String(frame + 1).padStart(4, "0")}.png`;

export const CREAM = "#F7F3EA";
export const PURPLE = "#B35CFF";

export const SIZE_PRESETS = [
  { id: "reel", label: "9:16 Reel / Short", w: 1080, h: 1920 },
  { id: "youtube", label: "16:9 YouTube", w: 1920, h: 1080 },
  { id: "post45", label: "4:5 Post", w: 1080, h: 1350 },
  { id: "square", label: "1:1 Square", w: 1080, h: 1080 },
  { id: "p34", label: "3:4 Portrait", w: 1080, h: 1440 },
  { id: "l43", label: "4:3 Landscape", w: 1440, h: 1080 },
  { id: "pin", label: "2:3 Pinterest", w: 1000, h: 1500 },
  { id: "x", label: "16:9 X / LinkedIn", w: 1600, h: 900 },
] as const;

export const FONTS = [
  { family: "Inter Tight", weight: 900, label: "Inter Tight Black" },
  { family: "Geist", weight: 900, label: "Geist Black" },
  { family: "Archivo Black", weight: 400, label: "Archivo Black" },
  { family: "Bricolage Grotesque", weight: 800, label: "Bricolage Extra Bold" },
  { family: "Anton", weight: 400, label: "Anton (condensed)" },
];

export const SAFE_ZONES = {
  none: { label: "Off", boxes: [] as Box[] },
  // fractions of the frame covered by app chrome (measured on 1080x1920 / 1920x1080 screenshots, rounded up)
  reels: { label: "Reels", boxes: [{ x: 0, y: 0, w: 1, h: 0.11 }, { x: 0, y: 0.78, w: 1, h: 0.22 }, { x: 0.87, y: 0.45, w: 0.13, h: 0.33 }] },
  shorts: { label: "Shorts", boxes: [{ x: 0, y: 0, w: 1, h: 0.1 }, { x: 0, y: 0.75, w: 1, h: 0.25 }, { x: 0.85, y: 0.42, w: 0.15, h: 0.33 }] },
  youtube: { label: "YouTube", boxes: [{ x: 0.86, y: 0.86, w: 0.12, h: 0.09 }] },
} satisfies Record<string, { label: string; boxes: Box[] }>;
export type SafeZone = keyof typeof SAFE_ZONES;

export function defaultDoc(): CoverDoc {
  return {
    preset: "reel", width: 1080, height: 1920,
    lines: [{ text: "FIX THE", color: CREAM }, { text: "NAVBAR.", color: PURPLE }],
    font: "Inter Tight", weight: 900, size: 0.125, tracking: -0.02, leading: 0.96,
    x: 0.065, y: 0.165,
    pill: { on: true, text: "Claude, I asked you to fix the navbar.", bg: "rgba(18,16,24,0.82)", color: "#FFFFFF", size: 0.033, x: 0.5, y: 0.07, maxWidth: 0.6 },
    focus: { x: 0.5, y: 0.4 }, zoom: 1,
  };
}

const STYLE_KEY = "thumbgen.style.v2";
// what "the look" means: type and colour, never size, position or crop (those belong to one cover)
const LOOK = ["font", "weight", "size", "tracking", "leading"] as const;
type LookKey = typeof LOOK[number];
const PILL_LOOK = ["on", "bg", "color", "size"] as const;
/** The last look used in the Thumbnail Generator (fonts, colours, sizes, positions); never the words. */
export function savedStyle(): CoverDoc {
  const base = defaultDoc();
  try {
    const raw = localStorage.getItem(STYLE_KEY);
    if (!raw) return base;
    const { colors, pill, ...look } = JSON.parse(raw) as Partial<Pick<CoverDoc, LookKey>> & { colors?: string[]; pill?: Partial<CoverDoc["pill"]> };
    const keep = <T extends object>(o: T | undefined, keys: readonly string[]) =>
      Object.fromEntries(Object.entries(o ?? {}).filter(([k]) => keys.includes(k))) as Partial<T>;
    return { ...base, ...keep(look, LOOK), pill: { ...base.pill, ...keep(pill, PILL_LOOK) },
      lines: base.lines.map((l, i) => ({ ...l, color: colors?.[i] ?? l.color })) };
  } catch { return base; }
}
export function saveStyle(doc: CoverDoc) {
  try {
    const look = Object.fromEntries(LOOK.map((k) => [k, doc[k]]));
    const pill = Object.fromEntries(PILL_LOOK.map((k) => [k, doc.pill[k]]));
    localStorage.setItem(STYLE_KEY, JSON.stringify({ ...look, colors: doc.lines.map((l) => l.color), pill }));
  } catch { /* storage unavailable */ }
}

/** Apply a drafted variant (headline + caption) to a doc, keeping its style. */
export function applyVariant(doc: CoverDoc, v: CoverDraft["variants"][number]): CoverDoc {
  const lines = v.headline.map((text, i) => ({ text, color: doc.lines[i]?.color ?? (i === v.headline.length - 1 ? PURPLE : CREAM) }));
  return { ...doc, lines, pill: { ...doc.pill, text: v.caption || doc.pill.text, on: Boolean(v.caption) && doc.pill.on } };
}

export async function ensureFonts(doc: CoverDoc) {
  if (!("fonts" in document)) return;
  const unit = 100;
  await Promise.all([
    document.fonts.load(`${doc.weight} ${unit}px "${doc.font}"`),
    document.fonts.load(`700 ${unit}px "Geist"`),
  ]).catch(() => undefined);
}

type Source = CanvasImageSource & { videoWidth?: number; videoHeight?: number; width?: number; height?: number };
function srcSize(s: Source) {
  const w = (s as HTMLVideoElement).videoWidth || (s as HTMLImageElement).naturalWidth || (s as HTMLCanvasElement).width || 0;
  const h = (s as HTMLVideoElement).videoHeight || (s as HTMLImageElement).naturalHeight || (s as HTMLCanvasElement).height || 0;
  return { w: Number(w), h: Number(h) };
}

function wrap(ctx: CanvasRenderingContext2D, text: string, max: number, maxLines: number) {
  const words = text.split(/\s+/).filter(Boolean);
  const out: string[] = [];
  let cur = "";
  for (const w of words) {
    const t = cur ? `${cur} ${w}` : w;
    if (ctx.measureText(t).width <= max || !cur) cur = t;
    else { out.push(cur); cur = w; }
  }
  if (cur) out.push(cur);
  if (out.length > maxLines) {
    const kept = out.slice(0, maxLines);
    let last = kept[maxLines - 1];
    while (last && ctx.measureText(`${last}…`).width > max) last = last.replace(/\s*\S+$/, "");
    kept[maxLines - 1] = `${last}…`;
    return kept;
  }
  return out;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** Draw the cover at W x H. Returns the layer boxes (canvas pixels) for hit-testing and snapping. */
export function drawCover(ctx: CanvasRenderingContext2D, doc: CoverDoc, frame: Source | null, W: number, H: number,
  opts: { safeZone?: SafeZone; selected?: Layer | null } = {}): Record<"headline" | "pill", Box | null> {
  const short = Math.min(W, H);
  ctx.save();
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#120d1f";
  ctx.fillRect(0, 0, W, H);

  // frame: cover-fit, zoom, crop around the focus point
  const fs = frame ? srcSize(frame) : { w: 0, h: 0 };
  if (frame && fs.w && fs.h) {
    const s = Math.max(W / fs.w, H / fs.h) * Math.max(1, doc.zoom);
    const dw = fs.w * s, dh = fs.h * s;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(frame, (W - dw) * doc.focus.x, (H - dh) * doc.focus.y, dw, dh);
  }

  // caption pill
  let pillBox: Box | null = null;
  if (doc.pill.on && doc.pill.text.trim()) {
    const fsz = doc.pill.size * short;
    ctx.font = `700 ${fsz}px "Geist", "Inter", sans-serif`;
    (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = "0px";
    const padX = fsz * 1.6, padY = fsz * 0.95, lh = fsz * 1.32;
    const rows = wrap(ctx, doc.pill.text, doc.pill.maxWidth * W - padX * 2, 2);
    const textW = Math.max(...rows.map((r) => ctx.measureText(r).width));
    const w = Math.min(doc.pill.maxWidth * W, textW + padX * 2), h = rows.length * lh + padY * 2;
    const x = doc.pill.x * W - w / 2, y = doc.pill.y * H;
    ctx.fillStyle = doc.pill.bg;
    roundRect(ctx, x, y, w, h, fsz * 0.55);
    ctx.fill();
    // the small accent dot from the reference covers
    ctx.fillStyle = doc.lines[doc.lines.length - 1]?.color ?? PURPLE;
    ctx.beginPath(); ctx.arc(x + fsz * 0.75, y + padY + lh / 2, fsz * 0.14, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = doc.pill.color;
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    rows.forEach((r, i) => ctx.fillText(r, x + w / 2, y + padY + lh * (i + 0.5)));
    pillBox = { x, y, w, h };
  }

  // headline
  let headBox: Box | null = null;
  const lines = doc.lines.filter((l) => l.text.trim());
  if (lines.length) {
    const setFont = (size: number) => {
      ctx.font = `${doc.weight} ${size}px "${doc.font}", "Geist", sans-serif`;
      (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = `${doc.tracking * size}px`;
    };
    let px = doc.size * short / 0.72; // cap height of these faces is about 0.72 em
    setFont(px);
    // long words shrink to fit the frame instead of running off its edge
    const avail = W - doc.x * W - 0.04 * short;
    const widest = Math.max(...lines.map((l) => ctx.measureText(l.text).width));
    if (widest > avail && avail > 0) { px *= Math.max(0.35, avail / widest); setFont(px); }
    const cap = px * 0.72;
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    const x = doc.x * W, top = doc.y * H, lh = px * doc.leading;
    let w = 0;
    lines.forEach((l, i) => {
      ctx.fillStyle = l.color;
      ctx.fillText(l.text, x, top + cap + lh * i);
      w = Math.max(w, ctx.measureText(l.text).width);
    });
    headBox = { x, y: top, w, h: cap + lh * (lines.length - 1) + px * 0.06 };
  }

  // preview-only overlays
  if (opts.safeZone && opts.safeZone !== "none") {
    ctx.fillStyle = "rgba(229,72,77,0.22)";
    ctx.strokeStyle = "rgba(255,120,120,0.85)";
    ctx.lineWidth = Math.max(1, short / 400);
    ctx.setLineDash([short / 90, short / 120]);
    for (const b of SAFE_ZONES[opts.safeZone].boxes) {
      ctx.fillRect(b.x * W, b.y * H, b.w * W, b.h * H);
      ctx.strokeRect(b.x * W, b.y * H, b.w * W, b.h * H);
    }
    ctx.setLineDash([]);
  }
  const sel = opts.selected === "headline" ? headBox : opts.selected === "pill" ? pillBox : null;
  if (sel) {
    const pad = short / 90;
    ctx.strokeStyle = "rgba(255,255,255,0.9)";
    ctx.lineWidth = Math.max(1, short / 500);
    ctx.setLineDash([short / 120, short / 160]);
    ctx.strokeRect(sel.x - pad, sel.y - pad, sel.w + pad * 2, sel.h + pad * 2);
    ctx.setLineDash([]);
  }
  ctx.restore();
  return { headline: headBox, pill: pillBox };
}

/** Render the doc at its exact pixel size and hand back an image file. */
export async function renderCover(doc: CoverDoc, frame: Source | null, type: "image/png" | "image/jpeg") {
  await ensureFonts(doc);
  const c = document.createElement("canvas");
  c.width = doc.width; c.height = doc.height;
  drawCover(c.getContext("2d")!, doc, frame, doc.width, doc.height);
  return new Promise<Blob>((resolve, reject) => c.toBlob((b) => (b ? resolve(b) : reject(new Error("Export failed"))), type, 0.93));
}

export function download(blob: Blob, name: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/** Copy one video frame into a canvas (seeks a throwaway video element). */
export function grabFrame(url: string, time: number): Promise<HTMLCanvasElement> {
  return new Promise((resolve, reject) => {
    const v = document.createElement("video");
    v.muted = true; v.preload = "auto"; v.src = url;
    const fail = () => reject(new Error("Couldn't read the video"));
    v.onerror = fail;
    v.onloadedmetadata = () => { v.currentTime = Math.min(Math.max(0, time), Math.max(0, v.duration - 0.05)); };
    v.onseeked = () => {
      const c = document.createElement("canvas");
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext("2d")!.drawImage(v, 0, 0);
      v.removeAttribute("src"); v.load();
      resolve(c);
    };
  });
}

export function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const im = new Image();
    im.decoding = "async";
    im.onload = () => resolve(im);
    im.onerror = () => reject(new Error("Couldn't load the frame"));
    im.src = url;
  });
}

/** Snap positions for a layer: returns the new top-left (headline) or top-centre (pill) in fractions. */
export const SNAPS = ["tl", "tc", "tr", "ml", "mc", "mr", "bl", "bc", "br"] as const;
export type Snap = typeof SNAPS[number];
export function snapTo(snap: Snap, box: Box, W: number, H: number, margin = 0.065) {
  const m = margin * Math.min(W, H);
  const col = snap[1], row = snap[0];
  const x = col === "l" ? m : col === "c" ? (W - box.w) / 2 : W - m - box.w;
  const y = row === "t" ? H * 0.12 : row === "m" ? (H - box.h) / 2 : H - H * 0.12 - box.h;
  return { x: x / W, y: y / H };
}

export function fileSafe(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "cover";
}
