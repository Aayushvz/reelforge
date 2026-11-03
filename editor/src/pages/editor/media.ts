// Media helpers for the editor: durations, waveform peaks, the playback clock and audio sync.
import { useEffect, useRef, useState } from "react";
import type { Clip, Timeline } from "@/lib/types";
import { AUDIO_KINDS, clipEnd, trackOf } from "@/lib/timeline";
import { useEditor } from "./store";

const durations = new Map<string, Promise<number>>();
export function mediaDuration(url: string, kind: "audio" | "video" = "audio"): Promise<number> {
  if (!durations.has(url)) {
    durations.set(url, new Promise((resolve) => {
      const el = document.createElement(kind);
      el.preload = "metadata";
      el.onloadedmetadata = () => resolve(isFinite(el.duration) ? el.duration : 0);
      el.onerror = () => resolve(0);
      el.src = url;
    }));
  }
  return durations.get(url)!;
}

export type Peaks = { data: Float32Array; perSec: number; duration: number };
const peaks = new Map<string, Promise<Peaks | null>>();
let ctx: AudioContext | null = null;
const PER_SEC = 120;

function loadPeaks(url: string) {
  if (!peaks.has(url)) {
    peaks.set(url, (async () => {
      try {
        const buf = await (await fetch(url)).arrayBuffer();
        ctx ??= new AudioContext();
        const audio = await ctx.decodeAudioData(buf);
        const ch = audio.getChannelData(0);
        const n = Math.ceil(audio.duration * PER_SEC);
        const step = Math.max(1, Math.floor(ch.length / n));
        const data = new Float32Array(n);
        let max = 0;
        for (let i = 0; i < n; i++) {
          let m = 0;
          for (let j = i * step; j < Math.min(ch.length, (i + 1) * step); j += 4) m = Math.max(m, Math.abs(ch[j]));
          data[i] = m;
          max = Math.max(max, m);
        }
        if (max > 0) for (let i = 0; i < n; i++) data[i] /= max;
        return { data, perSec: PER_SEC, duration: audio.duration };
      } catch { return null; }
    })());
  }
  return peaks.get(url)!;
}

export function usePeaks(url: string | undefined) {
  const [p, setP] = useState<Peaks | null>(null);
  useEffect(() => { let live = true; if (url) void loadPeaks(url).then((x) => live && setP(x)); return () => { live = false; }; }, [url]);
  return p;
}

// Advances the playhead while playing. One clock for the whole editor.
export function usePlaybackClock() {
  const playing = useEditor((s) => s.playing);
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const { playhead, tl, seek, setPlaying } = useEditor.getState();
      const t = playhead + (now - last) / 1000;
      last = now;
      if (!tl || t >= tl.duration) { seek(tl?.duration ?? 0); setPlaying(false); return; }
      seek(t);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);
}

const gainAt = (c: Clip, t: number) => {
  const local = t - c.start;
  const fin = c.fadeIn ? Math.min(1, local / c.fadeIn) : 1;
  const fout = c.fadeOut ? Math.min(1, (clipEnd(c) - t) / c.fadeOut) : 1;
  return Math.max(0, Math.min(1, (c.volume ?? 1) * fin * fout));
};

// Keeps one <audio> per audio clip in step with the playhead.
export function useAudioSync(tl: Timeline | null, resolve: (src: string) => string, master: number) {
  const els = useRef(new Map<string, HTMLAudioElement>());
  useEffect(() => {
    const unsub = useEditor.subscribe((s, prev) => {
      if (!tl) return;
      const t = s.playhead;
      const seeked = Math.abs(t - prev.playhead) > 0.25 || s.playing !== prev.playing;
      const live = new Set<string>();
      for (const c of tl.clips) {
        const tr = trackOf(tl, c);
        if (!c.src || !AUDIO_KINDS.includes(tr.kind) || tr.muted || tr.hidden) continue;
        const active = s.playing && t >= c.start && t < clipEnd(c);
        let el = els.current.get(c.id);
        if (!active) { if (el && !el.paused) el.pause(); continue; }
        live.add(c.id);
        if (!el) { el = new Audio(resolve(c.src)); el.preload = "auto"; els.current.set(c.id, el); }
        const want = (c.offset ?? 0) + (t - c.start);
        if (seeked || Math.abs(el.currentTime - want) > 0.2) el.currentTime = want;
        el.volume = gainAt(c, t) * master;
        if (el.paused) void el.play().catch(() => undefined);
      }
      for (const [id, el] of els.current) if (!live.has(id) && !el.paused) el.pause();
    });
    return () => { unsub(); for (const el of els.current.values()) el.pause(); };
  }, [tl, resolve, master]);
  useEffect(() => () => { for (const el of els.current.values()) { el.pause(); el.src = ""; } els.current.clear(); }, []);
}
