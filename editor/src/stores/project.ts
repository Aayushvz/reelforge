// The open project: performance.json + editor.json + the files on disk. Edits autosave.
import { create } from "zustand";
import { api } from "@/lib/api";
import { defaultEditor, defaultPerformance, normalizeEditor } from "@/lib/defaults";
import type { EditorDoc, Performance, ProjectData, ProjectFiles, ProjectKind } from "@/lib/types";

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

export const useProject = create<State>((set, get) => {
  const schedule = () => {
    set({ saveState: "pending" });
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void get().saveNow(), SAVE_DELAY);
  };

  return {
    id: null, loading: false, error: null,
    performance: null, editor: defaultEditor(), files: EMPTY_FILES,
    saveState: "idle", savedAt: null, saveError: null,

    async load(id) {
      if (get().id === id && !get().error && !get().loading) return;
      await get().saveNow();
      set({ loading: true, error: null, id });
      try {
        const d: ProjectData = await api.project(id);
        set({ performance: d.performance, editor: normalizeEditor({ ...d.editor, name: d.name }, d.performance),
          files: d.files, loading: false, saveState: "idle", savedAt: null });
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
        editor: defaultEditor(kind), files: EMPTY_FILES, saveState: "idle", savedAt: null });
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
            return created.id;
          }
          const r = await api.save(id, body);
          set({ saveState: "saved", savedAt: r.savedAt, saveError: null });
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
