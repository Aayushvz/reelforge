import { useEffect, useState } from "react";
import { musicFileUrl } from "@/lib/api";

// One shared player: starting a preview stops the last one. Previews start at the track's hook and play 20 s.
const audio = typeof Audio !== "undefined" ? new Audio() : null;
let playing: string | null = null;
let stopTimer: ReturnType<typeof setTimeout> | null = null;
const listeners = new Set<(id: string | null) => void>();
const emit = () => listeners.forEach((f) => f(playing));

export function stopPreview() {
  audio?.pause();
  if (stopTimer) clearTimeout(stopTimer);
  playing = null;
  emit();
}

export function togglePreview(trackId: string, start = 0) {
  if (!audio) return;
  if (playing === trackId) return stopPreview();
  stopPreview();
  audio.src = musicFileUrl(trackId);
  audio.currentTime = start;
  audio.volume = 0.8;
  void audio.play().catch(() => stopPreview());
  playing = trackId;
  stopTimer = setTimeout(stopPreview, 20_000);
  audio.onended = stopPreview;
  emit();
}

export function usePlaying() {
  const [id, setId] = useState<string | null>(playing);
  useEffect(() => {
    listeners.add(setId);
    return () => { listeners.delete(setId); };
  }, []);
  return id;
}

export const fmtSecs = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
export const topMood = (m: Record<string, number>) => Object.entries(m).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
