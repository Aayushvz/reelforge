// Script helpers. Validation mirrors reelforge/schema.py so errors show before a render.
import { EMOTIONS, MOODS, RATIOS, FPS_OPTIONS, type Performance, type PerfLine } from "./types";

export const stripTags = (text: string) => text.replace(/\[[^\]]*\]/g, "").replace(/\s+/g, " ").trim();
export const words = (text: string) => stripTags(text).split(" ").filter(Boolean);
export const wordCount = (p: Performance | null) => (p ? p.lines.reduce((n, l) => n + words(l.text).length, 0) : 0);

// Rough speaking time until real audio exists: ~2.7 words/s plus a small onset.
export const estimateLineSeconds = (text: string) => Math.max(0.6, words(text).length * 0.37 + 0.25);

export const LEAD_IN = 0.4; // reelforge/timeline.py
export const TAIL = 0.8;

export function estimateDuration(p: Performance | null, audio: Record<string, number> = {}) {
  if (!p || !p.lines.length) return 0;
  return p.lines.reduce((t, l) => t + (audio[l.id] ?? estimateLineSeconds(l.text)) + (l.pause_after ?? 0.3), LEAD_IN) + TAIL;
}

export type Issue = { lineId?: string; field?: string; message: string };

export function validate(p: Performance | null): Issue[] {
  if (!p) return [{ message: "No script yet" }];
  const issues: Issue[] = [];
  if (!FPS_OPTIONS.includes(p.fps as 24)) issues.push({ field: "fps", message: `fps must be 24, 25, 30 or 60` });
  if (!(p.ratio in RATIOS)) issues.push({ field: "ratio", message: `Unsupported aspect ratio ${p.ratio}` });
  const speakers = Object.keys(p.characters ?? {});
  if (!speakers.length) issues.push({ message: "Add at least one speaker" });
  for (const [name, c] of Object.entries(p.characters ?? {})) {
    if (!c.voice_id) issues.push({ field: `characters.${name}`, message: `${name} has no voice` });
  }
  const seen = new Set<string>();
  p.lines.forEach((l, i) => {
    const where = `Line ${i + 1}`;
    if (seen.has(l.id)) issues.push({ lineId: l.id, message: `${where}: duplicate id ${l.id}` });
    seen.add(l.id);
    if (!stripTags(l.text)) issues.push({ lineId: l.id, field: "text", message: `${where} is empty` });
    if (!speakers.includes(l.speaker)) issues.push({ lineId: l.id, field: "speaker", message: `${where}: unknown speaker ${l.speaker}` });
    if (!EMOTIONS.includes(l.emotion)) issues.push({ lineId: l.id, field: "emotion", message: `${where}: unknown emotion` });
    if (!MOODS.includes(l.mood)) issues.push({ lineId: l.id, field: "mood", message: `${where}: unknown mood` });
    if (!(l.intensity >= 0 && l.intensity <= 1)) issues.push({ lineId: l.id, field: "intensity", message: `${where}: intensity must be 0 to 1` });
    if ((l.pause_after ?? 0) < 0) issues.push({ lineId: l.id, field: "pause_after", message: `${where}: pause can't be negative` });
  });
  if (!p.lines.length) issues.push({ message: "Write at least one line" });
  return issues;
}

export function nextLineId(lines: PerfLine[]) {
  const nums = lines.map((l) => Number(l.id.replace(/\D/g, ""))).filter((n) => !isNaN(n));
  const n = (nums.length ? Math.max(...nums) : 0) + 1;
  return `l${String(n).padStart(2, "0")}`;
}

// Parse pasted text like "KAI: line" or plain paragraphs into lines.
export function parsePasted(text: string, fallbackSpeaker: string): { speaker: string; text: string }[] {
  return text.split(/\n+/).map((s) => s.trim()).filter(Boolean).map((row) => {
    const m = row.match(/^([A-Za-z][\w ]{0,23}):\s*(.+)$/);
    return m ? { speaker: m[1].trim().toUpperCase().replace(/\s+/g, "_"), text: m[2] } : { speaker: fallbackSpeaker, text: row };
  });
}

// Optional, local, rule-based script notes. No AI call, no cost.
export function scriptNotes(p: Performance | null): { level: "tip" | "warn"; text: string }[] {
  if (!p || !p.lines.length) return [];
  const notes: { level: "tip" | "warn"; text: string }[] = [];
  const first = words(p.lines[0].text);
  if (first.length > 14) notes.push({ level: "warn", text: `The opening line runs ${first.length} words. Hooks land harder under 10.` });
  if (p.lines[0].intensity < 0.4 && p.lines.length > 2) notes.push({ level: "tip", text: "The first line is low intensity. A stronger first beat helps retention." });
  if (!p.lines.some((l) => l.punchline)) notes.push({ level: "tip", text: "No punchline marked. Marking one gets a close-up and a bigger caption pop." });
  const moods = new Set(p.lines.map((l) => l.mood));
  if (p.lines.length >= 4 && moods.size === 1) notes.push({ level: "tip", text: "Every line has the same mood. A shift gives the lighting something to do." });
  const est = estimateDuration(p);
  if (est > 60) notes.push({ level: "warn", text: `Estimated ${Math.round(est)}s. Reels under 60s hold attention better.` });
  const last = p.lines[p.lines.length - 1];
  if (p.lines.length > 2 && !last.punchline && p.lines.some((l) => l.punchline)) notes.push({ level: "tip", text: "The punchline isn't the last line. Ending on it usually lands better." });
  return notes;
}
