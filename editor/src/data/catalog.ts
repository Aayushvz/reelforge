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
export const WARDROBE: WardrobeItem[] = [
  { id: "boxy-shirt", slot: "top", name: "Boxy shirt", color: "#1d1d1f" },
  { id: "knit-vest-tee", slot: "top", name: "Knit vest over tee", color: "#6f6553" },
  { id: "camel-tee", slot: "top", name: "Camel tee", color: "#b08a5a" },
  { id: "graphic-tee", slot: "top", name: "Graphic tee", color: "#e8e4dc" },
  { id: "cropped-knit", slot: "top", name: "Cropped knit", color: "#c9b8a3" },
  { id: "baby-tee", slot: "top", name: "Baby tee", color: "#e6d3d6" },
  { id: "butterfly-top", slot: "top", name: "Y2K butterfly top", color: "#9fc4d8" },
  { id: "turtleneck", slot: "top", name: "Turtleneck", color: "#2a2724" },
  { id: "oversized-sweater", slot: "top", name: "Oversized sweater", color: "#8c7f6c" },
  { id: "oversized-hoodie", slot: "outer", name: "Oversized hoodie", color: "#3b3d42" },
  { id: "track-jacket", slot: "outer", name: "Track jacket", color: "#24365a" },
  { id: "puffer-vest", slot: "outer", name: "Puffer vest", color: "#2f3a2f" },
  { id: "techwear-jacket", slot: "outer", name: "Techwear jacket", color: "#1f2124" },
  { id: "varsity-jacket", slot: "outer", name: "Varsity jacket", color: "#6b1f24" },
  { id: "baggy-cardigan", slot: "outer", name: "Baggy cardigan", color: "#7a6a58" },
  { id: "flannel", slot: "outer", name: "Flannel shirt", color: "#7b2f2a" },
  { id: "oversized-blazer", slot: "outer", name: "Oversized blazer", color: "#3a3631" },
  { id: "sporty-zip", slot: "outer", name: "Sporty zip-up", color: "#d8d4cc" },
  { id: "puffer-jacket", slot: "outer", name: "Puffer jacket", color: "#e0a65a" },
  { id: "trench-coat", slot: "outer", name: "Trench coat", color: "#a88e66" },
  { id: "sweatsuit", slot: "outer", name: "Sweatsuit top", color: "#8a8a8c" },
  { id: "cargos", slot: "bottom", name: "Cargo pants", color: "#4a4a3c" },
  { id: "black-jeans", slot: "bottom", name: "Black jeans", color: "#1a1a1c" },
  { id: "wide-pants", slot: "bottom", name: "Wide pants", color: "#5a544a" },
  { id: "wide-leg-jeans", slot: "bottom", name: "Wide-leg jeans", color: "#6d84a3" },
  { id: "mini-skirt", slot: "bottom", name: "Mini skirt", color: "#2a2a2c" },
  { id: "leggings", slot: "bottom", name: "Leggings", color: "#1e1e22" },
  { id: "joggers", slot: "bottom", name: "Joggers", color: "#8a8a8c" },
  { id: "chunky-sneakers", slot: "shoes", name: "Chunky sneakers", color: "#e8e6e1" },
  { id: "skate-shoes", slot: "shoes", name: "Skate shoes", color: "#232325" },
  { id: "boots", slot: "shoes", name: "Boots", color: "#3a2a1e" },
  { id: "loafers", slot: "shoes", name: "Loafers", color: "#2a1f18" },
  { id: "thin-chain", slot: "accessories", name: "Thin chain", color: "#d4b26a" },
  { id: "chunky-chain", slot: "accessories", name: "Chunky chain", color: "#d4b26a" },
  { id: "hoop-earrings", slot: "accessories", name: "Hoop earrings", color: "#d4b26a" },
  { id: "round-glasses", slot: "accessories", name: "Round glasses", color: "#3a3a3c" },
  { id: "beanie", slot: "accessories", name: "Beanie", color: "#4a5a4a" },
  { id: "beret", slot: "accessories", name: "Beret", color: "#2a2a2c" },
  { id: "watch", slot: "accessories", name: "Watch", color: "#9a9a9c" },
  { id: "cap", slot: "accessories", name: "Cap", color: "#1f2a3a" },
];
export const wardrobeItem = (id: string) => WARDROBE.find((w) => w.id === id);

// ---------- cast ----------

export type Outfit = { id: string; name: string; items: Partial<Record<Slot, string>>; colors?: Partial<Record<Slot, string>>; saved?: boolean };
export type Character = {
  id: string; name: string; gender: "male" | "female"; vibe: string; signature: string;
  personality: string; tone: string; status: AssetStatus; outfits: Outfit[]; suggestedVoice: string;
};

export const CHARACTERS: Character[] = [
  {
    id: "kai", name: "Kai", gender: "male", vibe: "Chill creative, deadpan", tone: "#7c8a9a",
    signature: "Tight black curls, thin chain, earring", status: "planned", suggestedVoice: "Josh",
    personality: "Says the funniest thing in the room without changing his face. Never in a hurry.",
    outfits: [
      { id: "kai-1", name: "Boxy black", items: { top: "boxy-shirt", bottom: "black-jeans", shoes: "skate-shoes", accessories: "thin-chain" } },
      { id: "kai-2", name: "Hoodie & cargos", items: { top: "graphic-tee", outer: "oversized-hoodie", bottom: "cargos", shoes: "chunky-sneakers" } },
      { id: "kai-3", name: "Knit vest", items: { top: "knit-vest-tee", bottom: "wide-pants", shoes: "loafers", accessories: "thin-chain" } },
    ],
  },
  {
    id: "rey", name: "Rey", gender: "male", vibe: "Loud and funny, big laugh", tone: "#a08a6a",
    signature: "Curly hair, full beard, glasses", status: "planned", suggestedVoice: "Adam",
    personality: "Laughs before the punchline lands. Turns small inconveniences into epics.",
    outfits: [
      { id: "rey-1", name: "Grey sweats", items: { outer: "sweatsuit", bottom: "joggers", shoes: "chunky-sneakers", accessories: "chunky-chain" } },
      { id: "rey-2", name: "Track jacket", items: { top: "graphic-tee", outer: "track-jacket", bottom: "joggers", shoes: "chunky-sneakers" } },
      { id: "rey-3", name: "Puffer vest", items: { top: "graphic-tee", outer: "puffer-vest", bottom: "cargos", shoes: "boots" } },
    ],
  },
  {
    id: "dev", name: "Dev", gender: "male", vibe: "Confident coder, smirk", tone: "#b08a5a",
    signature: "Fade with swoop top, stubble, watch", status: "planned", suggestedVoice: "Antoni",
    personality: "Ships on Friday at 4:59 and is somehow right about it.",
    outfits: [
      { id: "dev-1", name: "Camel & black", items: { top: "camel-tee", bottom: "black-jeans", shoes: "chunky-sneakers", accessories: "watch" } },
      { id: "dev-2", name: "Techwear", items: { top: "turtleneck", outer: "techwear-jacket", bottom: "cargos", shoes: "boots" } },
      { id: "dev-3", name: "Varsity", items: { top: "graphic-tee", outer: "varsity-jacket", bottom: "black-jeans", shoes: "skate-shoes" } },
    ],
  },
  {
    id: "mo", name: "Mo", gender: "male", vibe: "Anxious overthinker", tone: "#7a6a58",
    signature: "Messy hair, round glasses, slight slouch", status: "planned", suggestedVoice: "Sam",
    personality: "Has already imagined eleven ways this goes wrong. Two of them happen.",
    outfits: [
      { id: "mo-1", name: "Cardigan", items: { top: "graphic-tee", outer: "baggy-cardigan", bottom: "wide-pants", accessories: "round-glasses" } },
      { id: "mo-2", name: "Tee & beanie", items: { top: "graphic-tee", bottom: "cargos", shoes: "skate-shoes", accessories: "beanie" } },
      { id: "mo-3", name: "Flannel layers", items: { outer: "flannel", top: "graphic-tee", bottom: "black-jeans", accessories: "round-glasses" } },
    ],
  },
  {
    id: "aria", name: "Aria", gender: "female", vibe: "Witty lead, sarcastic", tone: "#8a6a7a",
    signature: "Long dark hair, hoop earrings", status: "planned", suggestedVoice: "Jessica",
    personality: "Runs the scene. Every reply is a closing argument.",
    outfits: [
      { id: "aria-1", name: "Cropped knit", items: { top: "cropped-knit", bottom: "wide-leg-jeans", shoes: "chunky-sneakers", accessories: "hoop-earrings" } },
      { id: "aria-2", name: "Blazer & mini", items: { top: "baby-tee", outer: "oversized-blazer", bottom: "mini-skirt", shoes: "boots" } },
      { id: "aria-3", name: "Baby tee & cargos", items: { top: "baby-tee", bottom: "cargos", shoes: "skate-shoes", accessories: "hoop-earrings" } },
    ],
  },
  {
    id: "zoe", name: "Zoe", gender: "female", vibe: "Bubbly, dramatic reactions", tone: "#c08a6a",
    signature: "High ponytail, freckles, blush", status: "planned", suggestedVoice: "Elli",
    personality: "Reacts at full volume. Means every word of it.",
    outfits: [
      { id: "zoe-1", name: "Sporty zip", items: { outer: "sporty-zip", bottom: "leggings", shoes: "chunky-sneakers" } },
      { id: "zoe-2", name: "Butterfly top", items: { top: "butterfly-top", bottom: "wide-leg-jeans", shoes: "chunky-sneakers" } },
      { id: "zoe-3", name: "Puffer", items: { top: "baby-tee", outer: "puffer-jacket", bottom: "leggings", shoes: "boots" } },
    ],
  },
  {
    id: "noor", name: "Noor", gender: "female", vibe: "Calm, stylish, dry humour", tone: "#9a8a6a",
    signature: "Sleek bob or braids, gold jewellery", status: "planned", suggestedVoice: "Rachel",
    personality: "Unbothered. Delivers the line everyone repeats later.",
    outfits: [
      { id: "noor-1", name: "Trench", items: { top: "turtleneck", outer: "trench-coat", bottom: "wide-pants", shoes: "loafers" } },
      { id: "noor-2", name: "Cargo set", items: { top: "baby-tee", bottom: "cargos", shoes: "chunky-sneakers", accessories: "hoop-earrings" } },
      { id: "noor-3", name: "Sweater & beret", items: { top: "oversized-sweater", bottom: "wide-leg-jeans", shoes: "boots", accessories: "beret" } },
    ],
  },
];
export const character = (id: string | null | undefined) => CHARACTERS.find((c) => c.id === id);

// The only character the pipeline renders today is the M1 procedural stand-in.
export const STAND_IN = { id: "stand-in", name: "Stand-in", note: "M1 procedural character. Rendered for every speaker until the cast is built." };

// ---------- environments ----------

export type LightingPreset = { id: string; name: string; key: string; rim: string; glow: string; sky: string };
export type Environment = {
  id: string; name: string; category: "Interior" | "Exterior" | "Transit" | "Work";
  description: string; status: AssetStatus; pipelineId?: string; presets: LightingPreset[];
};

const P = (id: string, name: string, key: string, rim: string, glow: string, sky: string): LightingPreset =>
  ({ id, name, key, rim, glow, sky });

export const ENVIRONMENTS: Environment[] = [
  { id: "night-city-desk", name: "Night-city desk", category: "Interior", status: "available", pipelineId: "night_city",
    description: "Desk by a window over a city at night. Glowing screens, holo panel, haze.",
    presets: [P("blue-night", "Blue night", "#e8a060", "#4070ff", "#ff8c33", "#0a1428"), P("neon-pink", "Neon pink", "#f0a0c0", "#ff3c8c", "#ff5ab4", "#1a0a1e"), P("rainy", "Rainy", "#a0b4c8", "#5a7a9a", "#8ab4d8", "#0c1218")] },
  { id: "bedroom", name: "Bedroom / gaming room", category: "Interior", status: "planned",
    description: "Lived-in bedroom with a gaming setup, shelves and soft practicals.",
    presets: [P("warm-lamp", "Warm lamp", "#f0b070", "#c08050", "#ffb060", "#1a120a"), P("rgb-leds", "RGB LEDs", "#c0a0e0", "#40d0ff", "#ff40a0", "#0e0a18"), P("morning-sun", "Morning sun", "#fff0d0", "#ffd8a0", "#ffe0b0", "#3a3020")] },
  { id: "rooftop", name: "Rooftop skyline", category: "Exterior", status: "planned",
    description: "Rooftop ledge with a skyline behind, string lights and water tanks.",
    presets: [P("golden-hour", "Golden hour", "#ffc070", "#ff9040", "#ffb050", "#4a2a14"), P("blue-hour", "Blue hour", "#a0b0e0", "#6080d0", "#ffb070", "#141a30"), P("night-lights", "Night lights", "#e0b080", "#5070c0", "#ffd080", "#0a0c16")] },
  { id: "cafe", name: "Café window", category: "Interior", status: "planned",
    description: "Window seat in a small café. Steam, wood, a street outside the glass.",
    presets: [P("rainy-day", "Rainy day", "#b0c0d0", "#7090b0", "#e0b080", "#141a20"), P("sunny-afternoon", "Sunny afternoon", "#ffe0b0", "#ffc080", "#ffd090", "#3a2c1a"), P("fairy-lights", "Evening fairy lights", "#f0c080", "#a07040", "#ffd070", "#140e08")] },
  { id: "lantern-street", name: "Lantern old-town street", category: "Exterior", status: "planned",
    description: "Narrow old-town street strung with paper lanterns. The ink.industries mood.",
    presets: [P("sunset", "Sunset", "#ffb070", "#ff7040", "#ffa050", "#3a1a10"), P("lantern-night", "Lantern night", "#ffb060", "#c05020", "#ff9040", "#100a08"), P("foggy-dawn", "Foggy dawn", "#c8ccd0", "#a0a8b0", "#e0c8a0", "#2a2c30")] },
  { id: "subway", name: "Subway platform", category: "Transit", status: "planned",
    description: "Tiled metro platform, tunnel mouth, signage and a waiting bench.",
    presets: [P("fluorescent", "Fluorescent", "#d8f0e0", "#a0d0b0", "#e0ffe8", "#141a16"), P("late-night", "Late-night empty", "#90a0b0", "#4060a0", "#c0d0e0", "#080a10"), P("rush-hour", "Rush-hour warm", "#f0c890", "#c09060", "#ffd8a0", "#1a1410")] },
  { id: "campus", name: "Campus / classroom", category: "Work", status: "planned",
    description: "Lecture room with tall windows, desks and a chalkboard.",
    presets: [P("daylight", "Daylight", "#fff4e0", "#d0e0f0", "#ffffff", "#30363c"), P("overcast", "Overcast", "#c8d0d8", "#909aa4", "#d8dde2", "#22262a"), P("after-hours", "After-hours", "#e0a870", "#405880", "#ffc080", "#0c0e14")] },
  { id: "office", name: "Startup office", category: "Work", status: "planned",
    description: "Open-plan office with glass walls, monitors and a whiteboard.",
    presets: [P("daylight", "Daylight", "#f8f4ec", "#c0d4e8", "#ffffff", "#2a3038"), P("late-crunch", "Late-night crunch", "#90b0e0", "#4070d0", "#80c0ff", "#080c14"), P("spotlight", "Presentation spotlight", "#fff0d0", "#806040", "#ffe0a0", "#060606")] },
  { id: "night-mart", name: "Night convenience store", category: "Interior", status: "planned",
    description: "Late-night convenience store aisle, fridges humming, a sign outside.",
    presets: [P("fluorescent-night", "Fluorescent night", "#e0f0f0", "#80c0c0", "#f0ffff", "#0a1010"), P("neon-sign", "Neon sign", "#f0a0b0", "#ff4060", "#ff6080", "#100808"), P("rain-outside", "Rain outside", "#a0b8c8", "#5080a0", "#c0e0f0", "#080c10")] },
  { id: "pier", name: "Beach pier", category: "Exterior", status: "planned",
    description: "Boardwalk pier over the water, railings and a ferris wheel far off.",
    presets: [P("sunset", "Sunset", "#ffa868", "#ff6848", "#ffb070", "#3a1a20"), P("pastel-morning", "Pastel morning", "#f8e0e0", "#c0d8f0", "#ffe8d8", "#3a3440"), P("carnival", "Night carnival lights", "#f0b080", "#4060ff", "#ff60a0", "#08080e")] },
];
export const environment = (id: string | null | undefined) => ENVIRONMENTS.find((e) => e.id === id);

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
export const voiceByName = (name: string) => VOICES.find((v) => v.name === name);

// ---------- music (none bundled yet) ----------
export const MUSIC: { id: string; name: string }[] = [];
