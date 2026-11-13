// Shots-AV Animation: the editor's model of a two-speaker desk script (you + one AI buddy).
// performance.json stays the contract (reelforge/schema.py); these helpers only read and write it.
import type { Emotion, Performance, PerfLine, SubtitleStyle } from "./types";

export type AvSetup = "av_hero_34" | "av_hero_front" | "av_buddy" | "av_wide_34" | "av_wide_front";
export type AvShot = {
  index: number; kind: AvSetup; start: number; end: number; subject: "hero" | "buddy";
  speaker: "hero" | "buddy"; move: string; rack: boolean; line: string; angle?: string;
};
export type AvPano = { w: number; h: number; frame: { x: number; y: number; w: number; h: number }; pan_px: number; height_px: number };
export type AvPlan = { shots: AvShot[]; runtime: number; frames: number; split: Record<"hero" | "buddy" | "wide", number>;
  target: Record<"hero" | "buddy" | "wide", number> };
export type AvCatalog = {
  hero: Record<string, { default: unknown; options?: string[]; swatches?: string[]; min?: number; max?: number }>;
  skins: Record<string, string>; outfits: Record<string, string>; brand: Record<string, string>;
  buddies: { model: string; label: string; readsAs: string; shell: string; glow: string; signature: string }[];
  rooms: { id: string; label: string; tone: "dark" | "light"; look: string; gamer?: boolean; pano?: AvPano | null;
    spots?: { pan?: number; height?: number; turn?: number }[] }[];
  angles?: { id: string; role: "hero" | "buddy" | "wide"; label: string }[];
  actions: string[];
  built: { hero: boolean; buddies: Record<string, boolean>; rooms: Record<string, boolean> }; allBuilt: boolean;
  timing: { preview_still_s: number; draft_s_per_frame: number; final_s_per_frame: number; scene_load_s: number };
  target: Record<"hero" | "buddy" | "wide", number>;
};

// This style's own caption template (reelforge/captions.py build_ass_shotsav): whole lines at the top on a faint plate.
export const SHOTSAV_TOP_ID = "shotsav-top";
export const SHOTSAV_TOP_STYLE: SubtitleStyle = {
  templateId: SHOTSAV_TOP_ID, font: "Geist", size: 46, weight: 700, color: "#FFFFFF", highlight: "#FFFFFF",
  background: "rgba(31,31,31,0.45)", outline: 0, shadow: 0, position: "upper", align: "center", lineSpacing: 1.18,
  wordsPerLine: 8, animation: "fade", uppercase: false, italic: false,
};
export function parseRgba(v: string | null | undefined): { hex: string; a: number } {
  const m = v?.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const [r, g, b, a = "1"] = m[1].split(",").map((x) => x.trim());
    const h = (n: string) => Math.max(0, Math.min(255, Math.round(Number(n)))).toString(16).padStart(2, "0");
    return { hex: `#${h(r)}${h(g)}${h(b)}`.toUpperCase(), a: Number(a) };
  }
  return { hex: /^#[0-9a-f]{6}$/i.test(v ?? "") ? (v as string).toUpperCase() : "#1F1F1F", a: 1 };
}
export function toRgba(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${Math.round(a * 100) / 100})`;
}

// ElevenLabs voices (editor/src/data/catalog.ts VOICES, public premade ids): you, and each buddy's default.
export const HERO_VOICE = "TxGEqnHWrfWFTfGW9XjX"; // Josh: young, warm
export const BUDDY_VOICE: Record<string, string> = {
  buddy_claude: "cgSgspJ2msm6clMCkdW9", // Jessica: playful, warm
  buddy_chatgpt: "21m00Tcm4TlvDq8ikWAM", // Rachel: calm
  buddy_figma: "MF3mGyEYCl7XYWbV9V5h", // Elli: young, emotional
  buddy_nova: "AZnzlk1XvdvUeBnXmlld", // Domi: confident
};

export const HERO = "me";
export const BUDDY = "buddy";
export const PURPLE = "#7C3AED";

export const SETUP_LABEL: Record<AvSetup, string> = {
  av_hero_34: "You, three-quarter", av_hero_front: "You, frontal", av_buddy: "Buddy single",
  av_wide_34: "Wide, three-quarter", av_wide_front: "Wide, frontal",
};
export const SETUP_SHORT: Record<AvSetup, string> = {
  av_hero_34: "A", av_hero_front: "D", av_buddy: "B", av_wide_34: "C", av_wide_front: "E",
};
export const MOVES = ["push_in", "pull_out", "pull_truck", "slow_zoom", "orbit", "truck", "crane_down", "drift", "static"] as const;
export const MOVE_LABEL: Record<string, string> = {
  push_in: "Push in", pull_out: "Pull out", pull_truck: "Pull out + truck", drift: "Drift", static: "Hold still",
  slow_zoom: "Slow zoom", orbit: "Orbit", truck: "Truck sideways", crane_down: "Crane down",
};
export const ACTION_LABEL: Record<string, string> = {
  "": "Auto", hop: "Hop", tilt: "Tilt", dry: "Dry look", happy: "Happy", think: "Think", shrink: "Shrink",
  nod: "Nod", lookaway: "Look away",
};
export const LABELS: Record<string, string> = {
  puffer: "Puffer", hoodie: "Hoodie", overshirt: "Overshirt",
  fringe: "Fringe", soft_fringe: "Soft fringe", curtain: "Curtain", swept: "Swept", curly_top: "Curly top", buzz: "Buzz",
  bold: "Bold", round: "Round", rect: "Rectangle", none: "None", on: "On", neck: "Round the neck",
  light: "Light beard", stubble: "Stubble", wheat: "Wheat", porcelain: "Porcelain", tan: "Tan",
  warm_brown: "Warm brown", brown: "Brown", deep: "Deep",
};
export const label = (v: string) => LABELS[v] ?? v.replace(/_/g, " ");

// Our own starter scripts (original; never the reference reel's).
export const STARTERS: { id: string; name: string; buddy: string; room: string; lines: [string, string, Emotion?][] }[] = [
  { id: "deadline", name: "The 2 AM fix", buddy: "buddy_claude", room: "av_studio_night", lines: [
    [HERO, "Claude, the client wants one more change.", "neutral"],
    [BUDDY, "It's two in the morning.", "deadpan"],
    [HERO, "It's tiny. Just the logo.", "neutral"],
    [BUDDY, "Last time 'just the logo' took four hours...", "smug"],
    [HERO, "That was different.", "embarrassed"],
    [BUDDY, "You said that last time too.", "deadpan"],
    [HERO, "Okay. Fair.", "neutral"],
    [BUDDY, "Save it, sleep, and send it at nine.", "happy"],
    [HERO, "After one tiny fix.", "smug"],
  ] },
  { id: "portfolio", name: "Portfolio review", buddy: "buddy_figma", room: "av_studio_morning", lines: [
    [HERO, "Be honest. Is my portfolio ready?", "worried"],
    [BUDDY, "The work is great!", "happy"],
    [HERO, "But?", "confused"],
    [BUDDY, "Your best project is on page eleven.", "deadpan"],
    [HERO, "...Nobody gets to page eleven.", "sad"],
    [BUDDY, "Exactly. Move it to the top.", "happy"],
    [HERO, "Done. Anything else?", "neutral"],
    [BUDDY, "Delete the logo you made in 2019.", "smug"],
    [HERO, "Never.", "annoyed"],
  ] },
  { id: "rate", name: "Raising the rate", buddy: "buddy_chatgpt", room: "av_cafe_day", lines: [
    [HERO, "I'm raising my rates this month.", "neutral"],
    [BUDDY, "Finally! By how much?", "surprised"],
    [HERO, "Ten percent.", "worried"],
    [BUDDY, "You've doubled your skills since last year.", "thinking"],
    [HERO, "Fifteen?", "embarrassed"],
    [BUDDY, "Thirty. And send the email before you overthink it.", "happy"],
    [HERO, "Okay. Sending it now.", "neutral"],
    [BUDDY, "You're still typing the first line...", "smug"],
    [HERO, "It has to be perfect.", "deadpan"],
  ] },
];

export function makeLine(speaker: string, text: string, i: number, emotion: Emotion = "neutral"): PerfLine {
  return { id: `l${String(i + 1).padStart(2, "0")}`, speaker, text, emotion, intensity: 0.5, mood: "calm" };
}

export function renumber(lines: PerfLine[]): PerfLine[] {
  return lines.map((l, i) => ({ ...l, id: `l${String(i + 1).padStart(2, "0")}` }));
}

export function newPerformance(buddy = "buddy_claude", room = "av_studio_night", lines: PerfLine[] = []): Performance {
  return {
    version: 1, fps: 30, ratio: "9:16", environment: room, style: "shots-av", look: "shotsav", ambience: true,
    // voices are generated with ElevenLabs (the owner's key, from Settings); an out/audio/<line>.mp3 always wins
    characters: { [HERO]: { voice_id: HERO_VOICE, model: "av_hero", outfit: "puffer", outfit_color: PURPLE },
      [BUDDY]: { voice_id: BUDDY_VOICE[buddy] ?? BUDDY_VOICE.buddy_claude, model: buddy } },
    // a fresh seed per project: the director shoots every reel differently (Reroll angles picks another)
    camera: { grammar: "signature", seed: Math.floor(Math.random() * 1e6), rack: true, drift: 1, angles: "varied" },
    captions: { position: "top", plate: true, tint: true, style: { ...SHOTSAV_TOP_STYLE } }, sound: { foley: true },
    lines,
  };
}

// Paste a plain script: one line per row; "Name: text" picks the speaker (anything that is not you is the buddy).
// Rows without a prefix alternate, starting with you.
export function parseScript(text: string, heroNames: string[] = []): PerfLine[] {
  const rows = text.split(/\r?\n/).map((r) => r.trim()).filter(Boolean);
  const me = new Set(["me", "you", "i", "hero", "av", ...heroNames.map((n) => n.toLowerCase())]);
  const out: PerfLine[] = [];
  let next = HERO;
  for (const row of rows) {
    const m = row.match(/^([A-Za-z][\w .'-]{0,24}):\s*(.+)$/);
    let speaker = next, body = row;
    if (m) {
      speaker = me.has(m[1].trim().toLowerCase()) ? HERO : BUDDY;
      body = m[2].trim();
    }
    out.push(makeLine(speaker, body, out.length));
    next = speaker === HERO ? BUDDY : HERO;
  }
  return out;
}

// Mirrors reelforge/engines/shots_av.py estimate_timing(): seconds from word counts, for the footer.
export function estimateRuntime(lines: PerfLine[]): number {
  let t = 0.3;
  for (const l of lines) {
    const words = Math.max(1, l.text.split(/\s+/).filter(Boolean).length);
    t += Math.max(0.8, words / 2.9 + 0.25) + 0.35;
  }
  return lines.length ? t - 0.35 + 0.9 : 0;
}

export const fmtSec = (s: number) => (s >= 60 ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}` : `${s.toFixed(1)} s`);
export const fmtDur = (s: number) => (s < 60 ? `about ${Math.max(5, Math.round(s / 5) * 5)} s` : `about ${Math.round(s / 60)} min`);
