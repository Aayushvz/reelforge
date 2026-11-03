export function timecode(sec: number, fps = 30, frames = true) {
  const s = Math.max(0, sec);
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60);
  const f = Math.floor((s - Math.floor(s)) * fps);
  const base = `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  return frames ? `${base}:${String(f).padStart(2, "0")}` : base;
}

export function duration(sec: number) {
  if (!isFinite(sec) || sec <= 0) return "0s";
  if (sec < 60) return `${sec < 10 ? sec.toFixed(1) : Math.round(sec)}s`;
  return `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`;
}

export function relativeTime(iso: string) {
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 45) return "just now";
  if (d < 3600) return `${Math.round(d / 60)} min ago`;
  if (d < 86400) return `${Math.round(d / 3600)} h ago`;
  if (d < 86400 * 7) return `${Math.round(d / 86400)} d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
export const uid = (p = "") => p + Math.random().toString(36).slice(2, 9);
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// Stable empty array for store selectors (a fresh [] would re-render forever).
export const NONE: never[] = [];
