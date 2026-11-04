import { SUBTITLE_TEMPLATES, VOICES } from "@/data/catalog";
import type { EditorDoc, Performance, Ratio } from "./types";
import { RATIOS } from "./types";

export function defaultPerformance(): Performance {
  return {
    version: 1, fps: 30, ratio: "9:16", environment: "night_city", lighting: "blue_night",
    characters: { A: { voice_id: VOICES[0].id, caption_color: "#FFFFFF", highlight_color: "#FFD23F", model: "aria", outfit: 0 } },
    lines: [],
  };
}

export function defaultEditor(kind: EditorDoc["kind"] = "generated", ratio: Ratio = "9:16"): EditorDoc {
  return {
    name: "Untitled reel", kind, style: "blender3d",
    cast: kind === "generated" ? { A: { characterId: "aria", outfitId: "aria-1" } } : {},
    environment: { id: "night-city-desk", lighting: "blue-night" },
    subtitles: { ...SUBTITLE_TEMPLATES[0].style },
    output: { ratio, resolution: [...RATIOS[ratio]] as [number, number], fps: 30, quality: "final" },
    audio: { musicId: null, musicVolume: 0.35, duckMusic: true, dialogueVolume: 1 },
    grade: { brightness: 0, contrast: 0, saturation: 0, vignette: 0.35, grain: 0.2, glow: 0.3 },
    timeline: null, approvals: {}, history: [], exports: [],
  };
}

// Fill gaps in an editor.json written by an older version or by hand.
export function normalizeEditor(raw: Partial<EditorDoc>, perf: Performance | null): EditorDoc {
  const d = defaultEditor(raw.kind ?? (perf ? "generated" : "blank"), (raw.output?.ratio ?? perf?.ratio ?? "9:16") as Ratio);
  return {
    ...d, ...raw,
    subtitles: { ...d.subtitles, ...raw.subtitles },
    output: { ...d.output, ...raw.output },
    audio: { ...d.audio, ...raw.audio },
    grade: { ...d.grade, ...raw.grade },
    environment: { ...d.environment, ...raw.environment },
    cast: raw.cast ?? {}, approvals: raw.approvals ?? {}, history: raw.history ?? [], exports: raw.exports ?? [],
  };
}
