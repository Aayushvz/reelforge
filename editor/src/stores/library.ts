// Reusable library (favourites, saved outfits, lighting and subtitle templates) in projects/library.json.
import { create } from "zustand";
import { api } from "@/lib/api";
import type { Library } from "@/lib/types";

type State = {
  lib: Library; loaded: boolean;
  load: () => Promise<void>;
  update: (fn: (l: Library) => Library) => void;
  toggleFavorite: (key: string) => void;
};

export const useLibrary = create<State>((set, get) => ({
  lib: {}, loaded: false,
  async load() {
    if (get().loaded) return;
    try { set({ lib: await api.library(), loaded: true }); } catch { set({ loaded: true }); }
  },
  update(fn) {
    const lib = fn(get().lib);
    set({ lib });
    void api.saveLibrary(lib);
  },
  toggleFavorite(key) {
    get().update((l) => {
      const f = new Set(l.favorites ?? []);
      if (f.has(key)) f.delete(key); else f.add(key);
      return { ...l, favorites: [...f] };
    });
  },
}));

export const useFavorite = (key: string) => useLibrary((s) => (s.lib.favorites ?? []).includes(key));
