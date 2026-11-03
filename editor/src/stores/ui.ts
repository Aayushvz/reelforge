import { create } from "zustand";

type Toast = { id: number; kind: "ok" | "err" | "info"; text: string };
type State = {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebar: (collapsed: boolean) => void;
  toasts: Toast[];
  toast: (text: string, kind?: Toast["kind"]) => void;
  dismiss: (id: number) => void;
  shortcutsOpen: boolean;
  setShortcutsOpen: (open: boolean) => void;
};

const read = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const write = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } };
let seq = 0;

export const useUI = create<State>((set, get) => ({
  sidebarCollapsed: read("rf.sidebar") === "1",
  toggleSidebar: () => get().setSidebar(!get().sidebarCollapsed),
  setSidebar: (collapsed) => { write("rf.sidebar", collapsed ? "1" : "0"); set({ sidebarCollapsed: collapsed }); },
  toasts: [],
  toast: (text, kind = "ok") => {
    const id = ++seq;
    set({ toasts: [...get().toasts, { id, kind, text }] });
    setTimeout(() => get().dismiss(id), kind === "err" ? 6000 : 3200);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
  shortcutsOpen: false,
  setShortcutsOpen: (open) => set({ shortcutsOpen: open }),
}));

export const toast = (text: string, kind?: Toast["kind"]) => useUI.getState().toast(text, kind);
