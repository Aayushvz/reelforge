// Editor session state: the timeline being edited, selection, playhead, zoom and undo history.
// The timeline itself persists to editor.json through the project store.
import { create } from "zustand";
import type { Clip, Timeline, TrackKind } from "@/lib/types";
import * as T from "@/lib/timeline";
import { useProject } from "@/stores/project";

const HISTORY_LIMIT = 100;
const COALESCE_MS = 500;

export type Layout = { left: number; right: number; timeline: number; leftOpen: boolean; rightOpen: boolean; maximized: boolean };
const DEFAULT_LAYOUT: Layout = { left: 280, right: 300, timeline: 300, leftOpen: true, rightOpen: true, maximized: false };
const readLayout = (): Layout => { try { return { ...DEFAULT_LAYOUT, ...JSON.parse(localStorage.getItem("rf.layout") ?? "{}"), maximized: false }; } catch { return DEFAULT_LAYOUT; } };

type State = {
  tl: Timeline | null;
  past: Timeline[];
  future: Timeline[];
  lastCommit: { key: string; at: number } | null;
  selection: string[];
  playhead: number;
  playing: boolean;
  pps: number;             // timeline zoom, pixels per second
  snapping: boolean;
  layout: Layout;
  previewZoom: "fit" | 0.5 | 1;
  guides: boolean;
  showSubs: boolean;
  quality: "full" | "half";

  init: (tl: Timeline) => void;
  // Apply an edit. `key` coalesces rapid edits (slider drags) into one undo step.
  edit: (fn: (tl: Timeline) => Timeline, key?: string) => void;
  // Live update without history (during a drag); call commitFrom() when the gesture ends.
  live: (tl: Timeline) => void;
  commitFrom: (before: Timeline) => void;
  undo: () => void;
  redo: () => void;
  select: (ids: string[]) => void;
  seek: (t: number) => void;
  setPlaying: (p: boolean) => void;
  setPps: (pps: number) => void;
  setLayout: (patch: Partial<Layout>) => void;
  resetLayout: () => void;
  set: (patch: Partial<Pick<State, "snapping" | "previewZoom" | "guides" | "showSubs" | "quality">>) => void;
};

const persist = (tl: Timeline) => useProject.getState().setEditor((e) => ({ ...e, timeline: tl }));

export const useEditor = create<State>((set, get) => ({
  tl: null, past: [], future: [], lastCommit: null, selection: [], playhead: 0, playing: false,
  pps: 60, snapping: true, layout: readLayout(), previewZoom: "fit", guides: false, showSubs: true, quality: "full",

  init: (tl) => set({ tl, past: [], future: [], selection: [], playhead: 0, playing: false, lastCommit: null }),

  edit(fn, key) {
    const { tl, past, lastCommit } = get();
    if (!tl) return;
    const next = fn(tl);
    if (next === tl) return;
    const now = Date.now();
    const coalesce = key && lastCommit?.key === key && now - lastCommit.at < COALESCE_MS;
    set({ tl: next, past: coalesce ? past : [...past.slice(-HISTORY_LIMIT + 1), tl], future: [], lastCommit: key ? { key, at: now } : null });
    persist(next);
  },

  live: (tl) => set({ tl }),

  commitFrom(before) {
    const { tl, past } = get();
    if (!tl || tl === before) return;
    set({ past: [...past.slice(-HISTORY_LIMIT + 1), before], future: [], lastCommit: null });
    persist(tl);
  },

  undo() {
    const { tl, past, future } = get();
    if (!tl || !past.length) return;
    const prev = past[past.length - 1];
    set({ tl: prev, past: past.slice(0, -1), future: [tl, ...future], lastCommit: null, selection: get().selection.filter((id) => prev.clips.some((c) => c.id === id)) });
    persist(prev);
  },

  redo() {
    const { tl, past, future } = get();
    if (!tl || !future.length) return;
    const next = future[0];
    set({ tl: next, past: [...past, tl], future: future.slice(1), lastCommit: null });
    persist(next);
  },

  select: (ids) => set({ selection: ids }),
  seek: (t) => { const tl = get().tl; set({ playhead: Math.max(0, Math.min(t, tl?.duration ?? t)) }); },
  setPlaying: (playing) => set({ playing }),
  setPps: (pps) => set({ pps: Math.max(4, Math.min(600, pps)) }),
  setLayout(patch) {
    const layout = { ...get().layout, ...patch };
    set({ layout });
    try { const { maximized: _m, ...keep } = layout; localStorage.setItem("rf.layout", JSON.stringify(keep)); } catch { /* ignore */ }
  },
  resetLayout: () => get().setLayout({ ...DEFAULT_LAYOUT }),
  set: (patch) => set(patch),
}));

// ---------- derived helpers ----------

export const selectedClips = (s: State): Clip[] => (s.tl ? s.tl.clips.filter((c) => s.selection.includes(c.id)) : []);
export const sortedOf = (tl: Timeline | null, kind: TrackKind) =>
  tl ? tl.clips.filter((c) => T.trackOf(tl, c).kind === kind).sort((a, b) => a.start - b.start) : [];

// Reorder shots: swap two shots and re-lay the shot track contiguously.
export function reorderShot(tl: Timeline, id: string, dir: -1 | 1): Timeline {
  const shots = sortedOf(tl, "shots");
  const i = shots.findIndex((c) => c.id === id);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= shots.length) return tl;
  const order = [...shots];
  [order[i], order[j]] = [order[j], order[i]];
  let t = shots[0].start;
  const placed = new Map<string, number>();
  for (const s of order) { placed.set(s.id, t); t += s.duration; }
  return { ...tl, clips: tl.clips.map((c) => (placed.has(c.id) ? { ...c, start: placed.get(c.id)! } : c)) };
}
