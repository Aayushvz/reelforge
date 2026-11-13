// The open project: performance.json + editor.json + the files on disk. Edits autosave.
import { create } from "zustand";
import { api } from "@/lib/api";
import { defaultEditor, defaultPerformance, normalizeEditor } from "@/lib/defaults";
import type { EditorDoc, Performance, ProjectData, ProjectFiles, ProjectKind, VoiceLine } from "@/lib/types";

export type SaveState = "idle" | "pending" | "saving" | "saved" | "error";

type State = {
  id: string | null;
  loading: boolean;
  error: string | null;
  performance: Performance | null;
  editor: EditorDoc;
  files: ProjectFiles;
  saveState: SaveState;
  savedAt: string | null;
  saveError: string | null;
  // ElevenLabs takes per line, generated automatically after the script is saved
  voices: Record<string, VoiceLine>;
  voiceNotice: string | null;
  refreshVoices: () => Promise<void>;
  generateVoices: (lines?: string[], force?: boolean) => Promise<void>;
  load: (id: string) => Promise<void>;
  reloadFiles: () => Promise<void>;
  startDraft: (kind?: ProjectKind) => void;
  setPerformance: (fn: (p: Performance) => Performance) => void;
  setEditor: (fn: (e: EditorDoc) => EditorDoc) => void;
  saveNow: () => Promise<string | null>;
};

const EMPTY_FILES: ProjectFiles = { audio: [], stills: [], media: [], finals: [], dialogue: false, renderPlan: false, captions: false };
const SAVE_DELAY = 700;
let timer: ReturnType<typeof setTimeout> | null = null;
let dirty = { performance: false, editor: false };
let inflight: Promise<string | null> | null = null;
// Called when a draft gets its folder on first save, so the page can update its URL.
let onCreated: ((id: string) => void) | null = null;
export const setOnProjectCreated = (fn: ((id: string) => void) | null) => { onCreated = fn; };
// Voices wait until typing settles, so a half-typed line never spends ElevenLabs credits.
const VOICE_DELAY = 2500;
let voiceTimer: ReturnType<typeof setTimeout> | null = null;
let pollTimer: ReturnType<typeof setTimeout> | null = null;

// A line counts as voiced when it has an imported mp3 or a generated take for its current text.
export const lineVoiced = (v?: VoiceLine) => v?.status === "imported" || v?.status === "ready";

export const useProject = create<State>((set, get) => {
  const schedule = () => {
    set({ saveState: "pending" });
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void get().saveNow(), SAVE_DELAY);
  };

  const applyVoices = (id: string, rows: VoiceLine[]) => {
    if (get().id !== id) return;
    set({ voices: Object.fromEntries(rows.map((r) => [r.line, r])) });
    if (pollTimer) clearTimeout(pollTimer);
    if (rows.some((r) => r.status === "generating")) pollTimer = setTimeout(() => void get().refreshVoices(), 1500);
    else void get().reloadFiles();
  };
  const scheduleVoices = () => {
    if (voiceTimer) clearTimeout(voiceTimer);
    voiceTimer = setTimeout(() => void get().generateVoices(), VOICE_DELAY);
  };

  return {
    id: null, loading: false, error: null,
    performance: null, editor: defaultEditor(), files: EMPTY_FILES,
    saveState: "idle", savedAt: null, saveError: null,
    voices: {}, voiceNotice: null,

    async refreshVoices() {
      const id = get().id;
      if (!id) return;
      try { applyVoices(id, await api.voices(id)); } catch { /* keep the last known state */ }
    },

    async generateVoices(lines, force = false) {
      const id = get().id;
      if (!id) return;
      if (lines) set({ voices: { ...get().voices, ...Object.fromEntries(lines.map((l) => [l, { line: l, status: "generating" as const }])) } });
      try {
        applyVoices(id, await api.generateVoices(id, lines, force));
        set({ voiceNotice: null });
      } catch (e) {
        set({ voiceNotice: (e as Error).message });
        await get().refreshVoices();
      }
    },

    async load(id) {
      if (get().id === id && !get().error && !get().loading) return;
      await get().saveNow();
      set({ loading: true, error: null, id });
      try {
        const d: ProjectData = await api.project(id);
        set({ performance: d.performance, editor: normalizeEditor({ ...d.editor, name: d.name }, d.performance),
          files: d.files, loading: false, saveState: "idle", savedAt: null, voices: {}, voiceNotice: null });
        void get().refreshVoices();
      } catch (e) {
        set({ loading: false, error: (e as Error).message });
      }
    },

    async reloadFiles() {
      const id = get().id;
      if (!id) return;
      const d = await api.project(id);
      set({ files: d.files });
    },

    startDraft(kind = "generated") {
      if (timer) clearTimeout(timer);
      dirty = { performance: false, editor: false };
      set({ id: null, error: null, loading: false, performance: kind === "generated" ? defaultPerformance() : null,
        editor: defaultEditor(kind), files: EMPTY_FILES, saveState: "idle", savedAt: null, voices: {}, voiceNotice: null });
    },

    setPerformance(fn) {
      set({ performance: fn(get().performance ?? defaultPerformance()) });
      dirty.performance = true;
      schedule();
    },

    setEditor(fn) {
      set({ editor: fn(get().editor) });
      dirty.editor = true;
      schedule();
    },

    async saveNow() {
      if (timer) { clearTimeout(timer); timer = null; }
      if (inflight) await inflight;
      if (!dirty.performance && !dirty.editor) return get().id;
      const { id, performance, editor } = get();
      const body = { performance: dirty.performance ? performance : undefined, editor: dirty.editor ? editor : undefined };
      dirty = { performance: false, editor: false };
      set({ saveState: "saving" });
      inflight = (async () => {
        try {
          if (!id) {
            const created = await api.create({ name: editor.name, performance: performance ?? undefined, editor });
            set({ id: created.id, files: created.files, saveState: "saved", savedAt: new Date().toISOString(), saveError: null });
            onCreated?.(created.id);
            if (body.performance) scheduleVoices();
            return created.id;
          }
          const r = await api.save(id, body);
          set({ saveState: "saved", savedAt: r.savedAt, saveError: null });
          if (body.performance) { void get().refreshVoices(); scheduleVoices(); }
          return id;
        } catch (e) {
          dirty = { performance: dirty.performance || body.performance !== undefined, editor: dirty.editor || body.editor !== undefined };
          set({ saveState: "error", saveError: (e as Error).message });
          return null;
        } finally {
          inflight = null;
        }
      })();
      return inflight;
    },
  };
});

// Save before the tab closes.
window.addEventListener("beforeunload", () => { void useProject.getState().saveNow(); });
