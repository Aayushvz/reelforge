import type { Character, Outfit } from "@/data/catalog";
import type { Library } from "./types";

// A character's built-in outfits plus the ones saved to the library.
export function outfitsFor(c: Character, lib: Library): Outfit[] {
  const saved = (lib.outfits ?? []).filter((o) => o.characterId === c.id).map((o) => ({
    id: o.id, name: o.name, saved: true,
    items: Object.fromEntries(Object.entries(o.items).map(([k, v]) => [k, v.itemId])) as Outfit["items"],
    colors: Object.fromEntries(Object.entries(o.items).map(([k, v]) => [k, v.color])) as Outfit["colors"],
  }));
  return [...c.outfits, ...saved];
}
