// Mirrors reelforge/schema.py. performance.json is the pipeline's contract: the editor
// reads and writes it in exactly this shape and keeps its own state in editor.json.

export const EMOTIONS = ["neutral", "happy", "sad", "worried", "surprised", "smug", "deadpan",
  "confused", "annoyed", "thinking", "embarrassed"] as const;
export const MOODS = ["calm", "success", "panic", "awkward", "reveal", "sad"] as const;
export const RATIOS = { "9:16": [1080, 1920], "16:9": [1920, 1080], "3:4": [1080, 1440], "1:1": [1080, 1080] } as const;
export const FPS_OPTIONS = [24, 25, 30, 60] as const;

export type Emotion = (typeof EMOTIONS)[number];
export type Mood = (typeof MOODS)[number];
export type Ratio = keyof typeof RATIOS;

export type PerfCharacter = {
  voice_id: string; caption_color?: string; highlight_color?: string; model?: string;
  outfit?: number | string;  // blender3d: a wardrobe index; shots-av hero: puffer | hoodie | overshirt
  // shots-av hero options (reelforge/schema.py _av_options)
  outfit_color?: string; glasses?: string; headphones?: string; skin?: string; hair?: string; beard?: string; stubble?: number;
};
export type PerfLine = {
  id: string; speaker: string; text: string; emotion: Emotion; intensity: number; mood: Mood;
  pause_after?: number; punchline?: boolean;
  beat?: boolean; action?: string;  // shots-av: force a wide; a buddy reaction clip
};
export type AvCamera = { grammar?: "signature" | "reference"; seed?: number; rack?: boolean; drift?: number;
  angles?: "varied" | "classic";  // the 36-angle library (reelforge/angles.py), or the reference's five set-ups
  overrides?: Record<string, { kind?: string; move?: string; fstop?: number; angle?: string; rack?: boolean }> };
// Where the desk sits in the room: each -1..1 (pan sideways, height, turn); empty = one of the room's good spots
export type RoomView = { pan?: number; height?: number; turn?: number };
export type Look = "classic" | "cinema" | "shotsav";  // reelforge/schema.py LOOKS
export type RenderQuality = "preview" | "standard" | "cinema";  // QUALITIES; Draft renders force preview
export type Performance = {
  version: 1; fps: number; ratio: Ratio; environment: string; lighting?: string; style?: string; ambience?: boolean;
  look?: Look; quality?: RenderQuality;
  characters: Record<string, PerfCharacter>; lines: PerfLine[];
  camera?: AvCamera; sound?: { foley?: boolean };
  captions?: { position?: "top" | "lower" | "custom"; plate?: boolean; tint?: boolean; style?: SubtitleStyle;
    x?: number; y?: number; size?: number };  // custom: the caption block's centre (frame fractions); size 0.5..2
  room_view?: RoomView; end_text?: string;
};

// ---------- editor.json ----------

export type ProjectKind = "generated" | "blank";
export type StyleId = "blender3d" | "cinematic-ai" | "shots-av";

export type CastSlot = { characterId: string | null; outfitId: string | null; voiceName?: string };

export type SubtitleStyle = {
  templateId: string;
  font: string; size: number; weight: number; color: string; highlight: string;
  background: string | null; outline: number; shadow: number;
  position: "lower" | "middle" | "upper"; align: "left" | "center" | "right";
  lineSpacing: number; wordsPerLine: number; animation: "none" | "pop" | "fade" | "karaoke" | "slide";
  uppercase: boolean; italic: boolean;
};

export type OutputSettings = { ratio: Ratio; resolution: [number, number]; fps: number; quality: "draft" | "final" };

export type TrackKind = "dialogue" | "shots" | "animation" | "mood" | "subtitles" | "music" | "sfx" | "video" | "audio" | "overlay";
export type Track = { id: string; kind: TrackKind; name: string; muted: boolean; locked: boolean; hidden: boolean };
export type ShotKind = "wide" | "medium" | "closeup";
export type Clip = {
  id: string; trackId: string; start: number; duration: number; label: string;
  // kind-specific data; optional so every clip shares one shape
  src?: string; offset?: number; lineId?: string; text?: string;
  shotKind?: ShotKind; lens?: number; push?: number; movement?: "static" | "push" | "pull" | "drift";
  subject?: string; mood?: Mood; emotion?: Emotion; intensity?: number;
  volume?: number; fadeIn?: number; fadeOut?: number; color?: string; transition?: "cut" | "fade" | "dip";
  status?: "estimated" | "planned" | "rendered";
};
export type Timeline = { duration: number; tracks: Track[]; clips: Clip[]; source: "script" | "render-plan" | "blank" };

export type Grade = { brightness: number; contrast: number; saturation: number; vignette: number; grain: number; glow: number };

export type HistoryEntry = { at: string; stage: "stills" | "full"; draft: boolean; status: string; ms: number };
export type ExportEntry = { at: string; file: string; ratio: Ratio; resolution: [number, number]; burnIn: boolean };

export type EditorDoc = {
  name: string; kind: ProjectKind; archived?: boolean; createdAt?: string; updatedAt?: string;
  style: StyleId;
  cast: Record<string, CastSlot>;
  environment: { id: string; lighting: string };
  subtitles: SubtitleStyle;
  output: OutputSettings;
  audio: { musicId: string | null; musicVolume: number; duckMusic: boolean; dialogueVolume: number };
  grade: Grade;
  timeline: Timeline | null;
  approvals: Record<string, "approved" | "changes">;
  history: HistoryEntry[];
  exports: ExportEntry[];
};

export type ProjectFiles = {
  audio: string[]; stills: string[]; media: string[]; finals: string[];
  dialogue: boolean; renderPlan: boolean; captions: boolean;
};

export type ProjectSummary = {
  id: string; folder: string; name: string; kind: ProjectKind; archived: boolean;
  status: "draft" | "stills" | "rendered"; ratio: Ratio; lineCount: number; words: number; style?: string;
  updatedAt: string; thumb: string | null; final: string | null;
};

export type ProjectData = ProjectSummary & {
  performance: Performance | null; editor: Partial<EditorDoc>; files: ProjectFiles;
};

export type SystemStatus = {
  repo: string; reelforge: boolean; blender: boolean; ffmpeg: boolean; assetsBuilt: boolean; elevenlabsKey: boolean;
};

export type LocalSettings = { elevenlabsKey: boolean; elevenlabsKeySource: "settings" | "environment" | null; elevenlabsKeyHint: string | null; elevenlabsModel: string };

export type VoiceState = "imported" | "ready" | "generating" | "error" | "missing" | "empty";
export type VoiceLine = { line: string; status: VoiceState; file?: string; error?: string };

export type Job = {
  id: string; projectId: string; stage: "stills" | "full"; draft: boolean; mode?: "run" | "animatic" | "assets";
  status: "running" | "done" | "failed" | "cancelled"; startedAt: number; endedAt?: number;
  log: string[]; error?: string;
};

export type Library = {
  favorites?: string[];
  outfits?: { id: string; characterId: string; name: string; items: Record<string, { itemId: string; color: string }> }[];
  lighting?: { id: string; environmentId: string; presetId: string; name: string }[];
  subtitleTemplates?: (SubtitleStyle & { id: string; name: string })[];
};
