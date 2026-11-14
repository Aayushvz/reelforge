// The planned cast, wardrobe, sets, styles, subtitle templates and voices, taken from
// docs/superpowers/specs/2026-11-01-cast-sets-editor-brief.md. `status` says honestly
// what the pipeline can render today; the UI shows it on every card.
import type { Mood, StyleId, SubtitleStyle } from "@/lib/types";

export type AssetStatus = "available" | "stand-in" | "planned";

// ---------- wardrobe ----------

export type Slot = "top" | "outer" | "bottom" | "shoes" | "accessories";
export const SLOTS: { id: Slot; label: string }[] = [
  { id: "top", label: "Tops" }, { id: "outer", label: "Outerwear" }, { id: "bottom", label: "Bottoms" },
  { id: "shoes", label: "Shoes" }, { id: "accessories", label: "Accessories" },
];

export type WardrobeItem = { id: string; slot: Slot; name: string; color: string };
// The old cast's wardrobe moved to the Shots-AV hero (blender/shotsav/hero.py OUTFITS).
export const WARDROBE: WardrobeItem[] = [];
export const wardrobeItem = (id: string) => WARDROBE.find((w) => w.id === id);

// ---------- cast ----------

export type Outfit = { id: string; name: string; items: Partial<Record<Slot, string>>; colors?: Partial<Record<Slot, string>>; saved?: boolean };
export type Character = {
  id: string; name: string; gender: "male" | "female"; vibe: string; signature: string;
  personality: string; tone: string; status: AssetStatus; outfits: Outfit[]; suggestedVoice: string;
};

export const CHARACTERS: Character[] = [
  // Imported, full-detail models (blender/imported.py): realistic faces, standing, one authored outfit each.
  {
    id: "matt", name: "Matt", gender: "male", vibe: "Easy-going, sincere", tone: "#c89a70",
    signature: "Swept ginger hair, light-blue oxford shirt", status: "available", suggestedVoice: "Josh",
    personality: "Says the honest thing a beat too early. Full face rig: every ARKit shape.",
    outfits: [{ id: "matt-1", name: "Oxford & jeans", items: {} }],
  },
  {
    id: "freya", name: "Freya", gender: "female", vibe: "Cool, confident", tone: "#b08c78",
    signature: "Long two-tone hair, black corset top", status: "available", suggestedVoice: "Rachel",
    personality: "Never raises her voice. Doesn't need to.",
    outfits: [{ id: "freya-1", name: "All black", items: {} }],
  },
  {
    id: "cute_girl", name: "Mina", gender: "female", vibe: "Warm, playful", tone: "#d0a090",
    signature: "Bangs and a loose ponytail, tied white shirt", status: "available", suggestedVoice: "Elli",
    personality: "Laughs first, explains later.",
    outfits: [{ id: "cute_girl-1", name: "Tied shirt & denim", items: {} }],
  },
];
export const character = (id: string | null | undefined) => CHARACTERS.find((c) => c.id === id);

// ---------- environments ----------

export type LightingPreset = { id: string; name: string; key: string; rim: string; glow: string; sky: string };
export type Environment = {
  id: string; name: string; category: "Interior" | "Exterior" | "Transit" | "Work";
  description: string; status: AssetStatus; pipelineId?: string; presets: LightingPreset[];
};

const P = (id: string, name: string, key: string, rim: string, glow: string, sky: string): LightingPreset =>
  ({ id, name, key, rim, glow, sky });

// The ten sets and the three imported rooms moved to Shots-AV, where they are desk-reel backdrops ("Classic sets").
export const ENVIRONMENTS: Environment[] = [];
// What screens show when a project has no environment (this style has none of its own now)
export const NO_ENVIRONMENT: Environment = {
  id: "none", name: "No environment", category: "Interior", status: "planned",
  description: "Environments now live in Shots-AV desk reels.",
  presets: [P("default", "Default", "#e8e4dc", "#8a8a96", "#c0b8a8", "#161618")],
};
export const environment = (id: string | null | undefined) => ENVIRONMENTS.find((e) => e.id === id);

// Editor preset ids → blender/sets.py preset names, where they differ beyond "-" vs "_".
const PRESET_PIDS: Record<string, string> = {
  "subway/rush-hour": "rush_hour_warm", "cafe/fairy-lights": "evening_fairy", "office/late-crunch": "late_night_crunch",
  "office/spotlight": "presentation_spotlight", "pier/carnival": "night_carnival",
};
export const presetPid = (env: Environment, presetId: string) => PRESET_PIDS[`${env.id}/${presetId}`] ?? presetId.replace(/-/g, "_");

// What performance.json needs for a set pick: the built set and its lighting preset.
export function pipelineSet(envId: string, presetId: string) {
  const e = environment(envId) ?? NO_ENVIRONMENT;
  const p = e.presets.find((x) => x.id === presetId) ?? e.presets[0];
  return { environment: e.pipelineId ?? "night_city", lighting: presetPid(e, p.id) };
}

// What performance.json needs for a cast pick: the cast member and its wardrobe index.
export function pipelineCast(characterId: string | null | undefined, outfitId: string | null | undefined) {
  const c = character(characterId);
  if (!c) return null;
  const i = c.outfits.findIndex((o) => o.id === outfitId);
  return { model: c.id, outfit: Math.max(0, i) };
}

// Mood light colours from reelforge/moods.py (linear RGB → display hex, approximate).
export const MOOD_COLORS: Record<Mood, string> = {
  calm: "#f0a35a", success: "#5ad07a", panic: "#f0503c", awkward: "#a8a8a8", reveal: "#f5c060", sad: "#6a80e8",
};

// ---------- styles ----------

export type StyleEngine = {
  id: StyleId; name: string; summary: string; status: "available" | "planned";
  processing: "local" | "paid-api"; cost: string; renderTime: string; details: string[];
};
export const STYLES: StyleEngine[] = [
  { id: "blender3d", name: "Blender 3D", status: "available", processing: "local", cost: "Free",
    renderTime: "Minutes per reel on a GPU laptop",
    summary: "Stylized 3D characters in moody, glowing sets. Rendered on this machine.",
    details: ["Lip sync from 52 ARKit face channels", "Mood lighting crossfades", "Depth of field cameras", "Deterministic: same script, same result"] },
  { id: "shots-av", name: "Shots-AV Animation", status: "available", processing: "local", cost: "Free",
    renderTime: "About 20 min for 15 s at final quality; a draft is a few minutes",
    summary: "You, in brand purple, at a desk talking to a small AI buddy. Cut like a polished 3D short.",
    details: ["Two speakers: you and Claude, ChatGPT, Figma or Nova", "Five camera set-ups cut on the line",
      "Six rooms, three dark and three light", "Whole-line captions at the top"] },
  { id: "cinematic-ai", name: "Cinematic AI", status: "planned", processing: "paid-api", cost: "Paid, your own provider key",
    renderTime: "Depends on provider",
    summary: "Pixar-like shots from AI keyframes, image-to-video and lip sync.",
    details: ["Uses the same cast as character sheets", "Free Wan 2.2 fallback planned", "Cost shown before every render"] },
];

// ---------- subtitles ----------

const base: Omit<SubtitleStyle, "templateId"> = {
  font: "Geist", size: 64, weight: 700, color: "#FFFFFF", highlight: "#FFD23F", background: null,
  outline: 4, shadow: 2, position: "lower", align: "center", lineSpacing: 1.1, wordsPerLine: 4,
  animation: "pop", uppercase: false, italic: false,
};
export type SubtitleTemplate = { id: string; name: string; description: string; style: SubtitleStyle; pipeline?: boolean };
const T = (id: string, name: string, description: string, o: Partial<SubtitleStyle>, pipeline = false): SubtitleTemplate =>
  ({ id, name, description, pipeline, style: { ...base, ...o, templateId: id } });

export const SUBTITLE_TEMPLATES: SubtitleTemplate[] = [
  T("punchline-pop", "Punchline Pop", "Word highlight with a bigger pop on punchlines. What the pipeline renders today.", {}, true),
  T("minimal-clean", "Minimal Clean", "Quiet sentence case, no highlight.", { weight: 500, size: 52, outline: 0, shadow: 3, highlight: "#FFFFFF", animation: "fade" }),
  T("bold-creator", "Bold Creator", "Heavy uppercase, thick outline.", { font: "Archivo Black", weight: 400, size: 70, uppercase: true, outline: 6, wordsPerLine: 3 }),
  T("cinematic", "Cinematic", "Small serif, letterboxed low.", { font: "DM Serif Display", weight: 400, size: 46, outline: 0, shadow: 4, highlight: "#FFFFFF", animation: "fade", italic: true, wordsPerLine: 7 }),
  T("documentary", "Documentary", "Neutral sans on a soft bar.", { weight: 500, size: 44, outline: 0, shadow: 0, background: "rgba(0,0,0,0.6)", highlight: "#FFFFFF", animation: "none", wordsPerLine: 8 }),
  T("editorial", "Editorial", "Grotesk, left aligned, upper third.", { font: "Space Grotesk", weight: 700, size: 58, align: "left", position: "upper", outline: 0, shadow: 2, animation: "slide" }),
  T("highlight-words", "Highlight Words", "Active word sits on an amber block.", { weight: 700, size: 60, outline: 0, shadow: 0, highlight: "#F0A43A", background: "highlight", wordsPerLine: 3 }),
  T("karaoke", "Karaoke", "Words fill in as they are spoken.", { weight: 700, size: 60, color: "#8A8A8A", highlight: "#FFFFFF", outline: 3, animation: "karaoke", wordsPerLine: 5 }),
  T("lower-third", "Minimal Lower Third", "Small left-aligned caption with speaker.", { weight: 500, size: 38, align: "left", outline: 0, shadow: 2, highlight: "#FFFFFF", animation: "fade", wordsPerLine: 8 }),
  T("modern-social", "Modern Social", "Condensed uppercase, one or two words at a time.", { font: "Anton", weight: 400, size: 84, uppercase: true, outline: 5, wordsPerLine: 2, position: "middle" }),
];
export const subtitleTemplate = (id: string) => SUBTITLE_TEMPLATES.find((t) => t.id === id) ?? SUBTITLE_TEMPLATES[0];
export const CAPTION_FONTS = ["Geist", "Anton", "Archivo Black", "DM Serif Display", "Space Grotesk", "IBM Plex Mono"];

// ---------- voices (ElevenLabs premade library; IDs are public) ----------

export type Voice = { name: string; id: string; tags: string[] };
export const VOICES: Voice[] = [
  { name: "Jessica", id: "cgSgspJ2msm6clMCkdW9", tags: ["female", "playful", "bright", "warm"] },
  { name: "Rachel", id: "21m00Tcm4TlvDq8ikWAM", tags: ["female", "calm", "narration"] },
  { name: "Elli", id: "MF3mGyEYCl7XYWbV9V5h", tags: ["female", "young", "emotional"] },
  { name: "Domi", id: "AZnzlk1XvdvUeBnXmlld", tags: ["female", "strong", "confident"] },
  { name: "Josh", id: "TxGEqnHWrfWFTfGW9XjX", tags: ["male", "deep", "young"] },
  { name: "Adam", id: "pNInz6obpgDQGcFmaJgB", tags: ["male", "deep", "narration"] },
  { name: "Antoni", id: "ErXwobaYiN019PkySvjV", tags: ["male", "well-rounded"] },
  { name: "Sam", id: "yoZ06aMxZJJ28mfd3POQ", tags: ["male", "raspy", "young"] },
  { name: "Arnold", id: "VR6AewLTigWG4xSOukaG", tags: ["male", "crisp"] },
];
export const voiceById = (id: string) => VOICES.find((v) => v.id === id);

// A new speaker gets the next cast member nobody plays yet, in that member's suggested voice.
const CAST_ORDER = ["matt", "cute_girl", "freya"];
export function autoCast(taken: (string | undefined)[], speaker = "") {
  // a speaker named after a cast member ("KAI") gets that member
  const named = character(speaker.toLowerCase());
  const c = named && !taken.includes(named.id) ? named
    : character(CAST_ORDER.find((id) => !taken.includes(id)) ?? CAST_ORDER[taken.length % CAST_ORDER.length])!;
  const voice = VOICES.find((v) => v.name === c.suggestedVoice) ?? VOICES[0];
  return {
    perf: { voice_id: voice.id, caption_color: "#FFFFFF", highlight_color: "#FFD23F", model: c.id, outfit: 0 },
    slot: { characterId: c.id, outfitId: c.outfits[0].id },
  };
}
export const voiceByName = (name: string) => VOICES.find((v) => v.name === name);

// ---------- music (none bundled yet) ----------
export const MUSIC: { id: string; name: string }[] = [];
