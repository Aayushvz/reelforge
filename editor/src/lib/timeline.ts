// Timeline model: building it from a script or a render plan, and the pure edit operations.
import type { Clip, Performance, ShotKind, Timeline, Track, TrackKind } from "./types";
import { LEAD_IN, TAIL, estimateLineSeconds, words } from "./script";
import { uid } from "./format";

const TRACK_NAMES: Record<TrackKind, string> = {
  dialogue: "Dialogue", shots: "Shots", animation: "Animation", mood: "Mood / Light", subtitles: "Subtitles",
  music: "Music", sfx: "SFX", video: "Video", audio: "Audio", overlay: "Text",
};
export const TRACK_COLOR: Record<TrackKind, string> = {
  dialogue: "var(--trk-dialogue)", shots: "var(--trk-shots)", animation: "var(--trk-anim)", mood: "var(--trk-mood)",
  subtitles: "var(--trk-subs)", music: "var(--trk-music)", sfx: "var(--trk-sfx)", video: "var(--trk-video)",
  audio: "var(--trk-audio)", overlay: "var(--trk-overlay)",
};
// Which tracks a clip may be dragged between.
export const COMPATIBLE: Record<TrackKind, TrackKind[]> = {
  dialogue: ["dialogue"], shots: ["shots"], animation: ["animation"], mood: ["mood"], subtitles: ["subtitles", "overlay"],
  music: ["music", "sfx", "audio"], sfx: ["sfx", "music", "audio"], audio: ["audio", "music", "sfx"],
  video: ["video"], overlay: ["overlay", "subtitles"],
};
export const AUDIO_KINDS: TrackKind[] = ["dialogue", "music", "sfx", "audio"];

const track = (kind: TrackKind, n = ""): Track =>
  ({ id: `${kind}${n}`, kind, name: TRACK_NAMES[kind] + (n ? ` ${n}` : ""), muted: false, locked: false, hidden: false });

export const LENSES: Record<ShotKind, number> = { wide: 35, medium: 50, closeup: 85 };
const MAX_SHOT_S = 3.0;
const CUT_LEAD_FRAMES = 4;
const MOOD_LEAD_S = 0.15;

type Placed = { lineId: string; start: number; duration: number };

// Mirrors reelforge/direct.py plan_shots() so the editor can show shots before a render.
// Once out/render_plan.json exists, buildFromRenderPlan() uses the director's real shots instead.
function estimateShots(p: Performance, placed: Placed[], fps: number, nFrames: number) {
  type S = { a: number; b: number; kind: ShotKind; subject: string; push: number };
  const shots: S[] = [];
  placed.forEach((pl, i) => {
    const line = p.lines[i];
    const a = i === 0 ? 0 : Math.max(0, Math.round(pl.start * fps) - CUT_LEAD_FRAMES);
    const b = i === placed.length - 1 ? nFrames : Math.round(placed[i + 1].start * fps) - CUT_LEAD_FRAMES;
    const close = line.punchline || line.intensity >= 0.7;
    const kind: ShotKind = close ? "closeup" : i === 0 ? "wide" : "medium";
    const push = kind === "wide" || line.mood === "sad" || line.mood === "reveal" ? 0.12 : 0.05;
    shots.push({ a, b, kind, subject: line.speaker, push });
  });
  const limit = Math.round(MAX_SHOT_S * fps);
  const out: S[] = [];
  for (const s of shots) {
    const len = s.b - s.a;
    if (len <= limit) { out.push(s); continue; }
    const n = Math.ceil(len / limit);
    const step = Math.floor(len / n);
    for (let k = 0; k < n; k++) {
      const a = s.a + k * step;
      const kind: ShotKind = k % 2 === 0 ? s.kind : s.kind === "closeup" ? "medium" : "closeup";
      out.push({ ...s, a, b: k === n - 1 ? s.b : a + step, kind });
    }
  }
  return out;
}

export type RenderPlanShot = { start_frame: number; end_frame: number; kind: ShotKind; lens: number; subject: string; push: number };

export function buildFromScript(
  p: Performance, audioDur: Record<string, number>, wordsPerLine: number,
  plan?: { fps: number; n_frames: number; shots: RenderPlanShot[] },
): Timeline {
  const fps = p.fps || 30;
  let t = LEAD_IN;
  const placed: Placed[] = p.lines.map((l) => {
    const d = audioDur[l.id] ?? estimateLineSeconds(l.text);
    const pl = { lineId: l.id, start: t, duration: d };
    t += d + (l.pause_after ?? 0.3);
    return pl;
  });
  const total = plan ? plan.n_frames / plan.fps : t + TAIL;
  const nFrames = Math.ceil(total * fps);
  const tracks = [track("shots"), track("dialogue"), track("animation"), track("mood"), track("subtitles"), track("music"), track("sfx")];
  const clips: Clip[] = [];

  placed.forEach((pl, i) => {
    const l = p.lines[i];
    const hasAudio = l.id in audioDur;
    clips.push({ id: uid("c"), trackId: "dialogue", start: pl.start, duration: pl.duration, label: `${l.speaker} · ${l.id}`,
      lineId: l.id, text: l.text, src: hasAudio ? `out/audio/${l.id}.mp3` : undefined, offset: 0, volume: 1,
      status: hasAudio ? "rendered" : "estimated" });
    clips.push({ id: uid("c"), trackId: "animation", start: pl.start, duration: pl.duration, label: l.emotion,
      lineId: l.id, emotion: l.emotion, intensity: l.intensity, subject: l.speaker });
    // caption chunks: words spread across the line by length
    const ws = words(l.text);
    const chars = ws.reduce((n, w) => n + w.length + 1, 0) || 1;
    let cursor = pl.start;
    for (let k = 0; k < ws.length; k += wordsPerLine) {
      const chunk = ws.slice(k, k + wordsPerLine);
      const d = (chunk.reduce((n, w) => n + w.length + 1, 0) / chars) * pl.duration;
      clips.push({ id: uid("c"), trackId: "subtitles", start: cursor, duration: d, label: chunk.join(" "), text: chunk.join(" "), lineId: l.id });
      cursor += d;
    }
  });

  const shots = plan
    ? plan.shots.map((s) => ({ a: s.start_frame, b: s.end_frame, kind: s.kind, subject: s.subject, push: s.push }))
    : estimateShots(p, placed, fps, nFrames);
  shots.forEach((s, i) => clips.push({
    id: uid("c"), trackId: "shots", start: s.a / fps, duration: (s.b - s.a) / fps, label: `Shot ${i + 1}`,
    shotKind: s.kind, lens: LENSES[s.kind], push: s.push, subject: s.subject, movement: "push", transition: "cut",
    status: plan ? "planned" : "estimated",
  }));

  // mood segments (reelforge/direct.py mood_keys)
  const keys: { at: number; mood: Performance["lines"][number]["mood"] }[] = [];
  placed.forEach((pl, i) => {
    const at = i === 0 ? 0 : pl.start - MOOD_LEAD_S;
    if (!keys.length || keys[keys.length - 1].mood !== p.lines[i].mood) keys.push({ at, mood: p.lines[i].mood });
  });
  keys.forEach((k, i) => {
    const end = i + 1 < keys.length ? keys[i + 1].at : total;
    clips.push({ id: uid("c"), trackId: "mood", start: k.at, duration: end - k.at, label: k.mood, mood: k.mood });
  });

  return { duration: total, tracks, clips, source: plan ? "render-plan" : "script" };
}

export function blankTimeline(): Timeline {
  return { duration: 30, tracks: [track("overlay"), track("video", "1"), track("audio", "1"), track("music")], clips: [], source: "blank" };
}

// ---------- operations (pure) ----------

export const MIN_CLIP = 1 / 30;
export const clipEnd = (c: Clip) => c.start + c.duration;
export const trackOf = (tl: Timeline, c: Clip) => tl.tracks.find((t) => t.id === c.trackId)!;

export function contentEnd(tl: Timeline) {
  return tl.clips.reduce((m, c) => Math.max(m, clipEnd(c)), 0);
}

export function splitClip(tl: Timeline, id: string, at: number): Timeline {
  const c = tl.clips.find((x) => x.id === id);
  if (!c || at <= c.start + MIN_CLIP || at >= clipEnd(c) - MIN_CLIP) return tl;
  const left = { ...c, duration: at - c.start };
  const right = { ...c, id: uid("c"), start: at, duration: clipEnd(c) - at, offset: (c.offset ?? 0) + (at - c.start), label: c.label };
  return { ...tl, clips: tl.clips.flatMap((x) => (x.id === id ? [left, right] : [x])) };
}

export function splitAtPlayhead(tl: Timeline, ids: string[], at: number): Timeline {
  const targets = ids.length ? ids : tl.clips.filter((c) => c.start < at && clipEnd(c) > at && !trackOf(tl, c).locked).map((c) => c.id);
  return targets.reduce((acc, id) => splitClip(acc, id, at), tl);
}

export function removeClips(tl: Timeline, ids: string[]): Timeline {
  return { ...tl, clips: tl.clips.filter((c) => !ids.includes(c.id) || trackOf(tl, c).locked) };
}

export function duplicateClips(tl: Timeline, ids: string[]): { tl: Timeline; ids: string[] } {
  const newIds: string[] = [];
  const copies = tl.clips.filter((c) => ids.includes(c.id) && !trackOf(tl, c).locked).map((c) => {
    // place the copy right after the last clip on the same track that starts at or after it
    const after = tl.clips.filter((x) => x.trackId === c.trackId && x.start >= c.start).reduce((m, x) => Math.max(m, clipEnd(x)), clipEnd(c));
    const copy = { ...c, id: uid("c"), start: after };
    newIds.push(copy.id);
    return copy;
  });
  const next = { ...tl, clips: [...tl.clips, ...copies] };
  return { tl: { ...next, duration: Math.max(next.duration, contentEnd(next)) }, ids: newIds };
}

export function updateClip(tl: Timeline, id: string, patch: Partial<Clip>): Timeline {
  const next = { ...tl, clips: tl.clips.map((c) => (c.id === id ? { ...c, ...patch } : c)) };
  return { ...next, duration: Math.max(next.duration, contentEnd(next)) };
}

export function updateTrack(tl: Timeline, id: string, patch: Partial<Track>): Timeline {
  return { ...tl, tracks: tl.tracks.map((t) => (t.id === id ? { ...t, ...patch } : t)) };
}

export function addTrack(tl: Timeline, kind: TrackKind): Timeline {
  const n = tl.tracks.filter((t) => t.kind === kind).length + 1;
  const t = track(kind, String(n));
  const idx = AUDIO_KINDS.includes(kind) ? tl.tracks.length : 0;
  const tracks = [...tl.tracks];
  tracks.splice(idx, 0, { ...t, id: `${kind}${n}-${uid()}` });
  return { ...tl, tracks };
}

// Snap a time to nearby edges (playhead, other clip edges, zero) within `tol` seconds.
export function snap(t: number, points: number[], tol: number) {
  let best = t;
  let dist = tol;
  for (const p of points) {
    const d = Math.abs(p - t);
    if (d < dist) { dist = d; best = p; }
  }
  return best;
}

export function snapPoints(tl: Timeline, playhead: number, exclude: string[]) {
  const pts = [0, playhead];
  for (const c of tl.clips) if (!exclude.includes(c.id)) pts.push(c.start, clipEnd(c));
  return pts;
}

export function clipsAt(tl: Timeline, t: number, kind?: TrackKind) {
  return tl.clips.filter((c) => c.start <= t && clipEnd(c) > t && (!kind || trackOf(tl, c).kind === kind) && !trackOf(tl, c).hidden);
}
