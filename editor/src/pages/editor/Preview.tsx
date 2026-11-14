// Video preview: plays rendered/imported video when present, otherwise an animatic built from
// rendered stills or the set and cast data. Subtitles, overlays, grade and safe areas on top.
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Play, Pause, SkipBack, SkipForward, ChevronLeft, ChevronRight, Maximize, Captions, Grid3x3, Repeat,
} from "lucide-react";
import type { Clip, EditorDoc, Ratio } from "@/lib/types";
import { RATIOS } from "@/lib/types";
import * as T from "@/lib/timeline";
import { timecode } from "@/lib/format";
import { MOOD_COLORS, character, environment, NO_ENVIRONMENT } from "@/data/catalog";
import { CharacterThumb, EnvThumb, SubtitleText } from "@/components/Thumbs";
import { IconButton, Select } from "@/components/ui/Form";
import { useEditor, sortedOf } from "./store";
import { useLibrary } from "@/stores/library";
import { outfitsFor } from "@/lib/outfits";

// reelforge/captions.py SAFE_ZONES: (top, bottom) px kept clear by the platform UI
const SAFE: Record<Ratio, [number, number]> = { "9:16": [220, 420], "16:9": [60, 60], "3:4": [80, 120], "1:1": [60, 60] };
const SHOT_SCALE = { wide: 0.42, medium: 0.68, closeup: 1.05 } as const;

type Props = { editor: EditorDoc; stills: string[]; resolveSrc: (src: string) => string; fps: number; punchlines: string[] };

export function Preview({ editor, stills, resolveSrc, fps, punchlines }: Props) {
  const tl = useEditor((s) => s.tl)!;
  const playhead = useEditor((s) => s.playhead);
  const playing = useEditor((s) => s.playing);
  const zoom = useEditor((s) => s.previewZoom);
  const guides = useEditor((s) => s.guides);
  const showSubs = useEditor((s) => s.showSubs);
  const quality = useEditor((s) => s.quality);
  const lib = useLibrary((x) => x.lib);
  const { seek, setPlaying, set } = useEditor.getState();
  const [loop, setLoop] = useState(false);
  const stage = useRef<HTMLDivElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ w: 400, h: 600 });

  const ratio = editor.output.ratio;
  const [outW, outH] = editor.output.resolution ?? RATIOS[ratio];

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setBox({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => { if (loop && !playing && playhead >= tl.duration - 0.01 && tl.duration > 0) { seek(0); setPlaying(true); } }, [loop, playing, playhead, tl.duration, seek, setPlaying]);

  const fitScale = Math.min((box.w - 32) / outW, (box.h - 32) / outH);
  const scale = zoom === "fit" ? Math.max(0.05, fitScale) : zoom;
  const fw = outW * scale;
  const fh = outH * scale;

  const shots = useMemo(() => sortedOf(tl, "shots"), [tl]);
  const at = (kind: Parameters<typeof T.clipsAt>[2]) => T.clipsAt(tl, playhead, kind);
  const shot = at("shots")[0];
  const shotIdx = shot ? shots.indexOf(shot) : -1;
  const line = at("dialogue")[0];
  const anim = at("animation")[0];
  const mood = at("mood")[0]?.mood;
  const sub = at("subtitles")[0];
  const overlays = at("overlay");
  const videos = tl.tracks.filter((t) => t.kind === "video" && !t.hidden).flatMap((t) => tl.clips.filter((c) => c.trackId === t.id && c.start <= playhead && T.clipEnd(c) > playhead));
  const topVideo = videos[0];

  const env = environment(editor.environment.id) ?? NO_ENVIRONMENT;
  const preset = env.presets.find((p) => p.id === editor.environment.lighting) ?? env.presets[0];
  const subject = shot?.subject ?? line?.label.split(" ")[0] ?? Object.keys(editor.cast)[0];
  const ch = character(editor.cast[subject ?? ""]?.characterId);
  const outfit = ch ? outfitsFor(ch, lib).find((o) => o.id === editor.cast[subject ?? ""]?.outfitId) : undefined;
  const still = shotIdx >= 0 ? stills.find((s) => s === `shot_${String(shotIdx).padStart(2, "0")}.png`) : undefined;
  const progress = shot ? (playhead - shot.start) / shot.duration : 0;
  const push = 1 + (shot?.push ?? 0) * progress;
  const g = editor.grade;
  const filter = `brightness(${1 + g.brightness}) contrast(${1 + g.contrast}) saturate(${1 + g.saturation})`;

  let wordIdx = -1;
  if (sub) {
    const n = (sub.text ?? sub.label).split(" ").filter(Boolean).length;
    wordIdx = Math.min(n - 1, Math.floor(((playhead - sub.start) / sub.duration) * n));
  }
  const punch = Boolean(sub?.lineId && punchlines.includes(sub.lineId));
  const s = editor.subtitles;
  const [safeTop, safeBottom] = SAFE[ratio];
  const subPos: React.CSSProperties = s.position === "upper" ? { top: (safeTop + 40) * scale } : s.position === "middle" ? { top: "50%", transform: "translateY(-50%)" } : { bottom: (safeBottom + 20) * scale };

  return (
    <div className="pv">
      <div className={`pv-stage${zoom !== "fit" ? " scroll" : ""}`} ref={stage}>
        <div className="pv-frame" ref={wrap} style={{ width: fw, height: fh }} onDoubleClick={() => wrap.current?.requestFullscreen?.()}>
          <div className="pv-layer" style={{ filter }}>
            {topVideo ? <VideoLayer clip={topVideo} src={resolveSrc(topVideo.src!)} playhead={playhead} playing={playing} muted={tl.tracks.find((t) => t.id === topVideo.trackId)?.muted ?? false} />
            : still ? <img className="pv-img" src={resolveSrc(`out/stills/${still}`)} alt="" style={{ transform: `scale(${push})` }} draggable={false} />
            : tl.source === "blank" ? <div className="pv-black" />
            : (
              <div className="pv-animatic" style={{ transform: `scale(${push})` }}>
                <EnvThumb env={env} preset={preset} style={{ position: "absolute", inset: 0, filter: quality === "half" ? "blur(1px)" : undefined }} />
                {ch && shot && (
                  <div className="pv-subject" style={{ height: `${SHOT_SCALE[shot.shotKind ?? "medium"] * 70}%`, bottom: shot.shotKind === "closeup" ? "-18%" : "8%" }}>
                    <CharacterThumb character={ch} outfit={outfit} style={{ background: "transparent" }} />
                  </div>
                )}
                {!ch && shot && <div className="pv-standin" style={{ height: `${SHOT_SCALE[shot.shotKind ?? "medium"] * 55}%` }} />}
              </div>
            )}
            {mood && !topVideo && <div className="pv-mood" style={{ background: MOOD_COLORS[mood] }} />}
          </div>
          {g.vignette > 0 && <div className="pv-vignette" style={{ opacity: g.vignette }} />}
          {g.grain > 0 && <div className="pv-grain" style={{ opacity: g.grain * 0.5 }} />}

          {overlays.map((o) => (
            <div key={o.id} className="pv-overlay" style={{ top: `${(o.offset ?? 0.12) * 100}%`, fontSize: 56 * scale, color: o.color ?? "#fff" }}>{o.text ?? o.label}</div>
          ))}
          {showSubs && sub && (
            <div className="pv-subs" style={{ ...subPos, textAlign: s.align, justifyContent: s.align === "left" ? "flex-start" : s.align === "right" ? "flex-end" : "center", padding: `0 ${80 * scale}px` }}>
              <SubtitleText s={s} text={sub.text ?? sub.label} active={wordIdx} scale={scale} punch={punch && wordIdx >= 0} />
            </div>
          )}
          {guides && (
            <div className="pv-guides">
              <div className="safe" style={{ top: safeTop * scale, bottom: safeBottom * scale, left: 60 * scale, right: 60 * scale }} />
              <div className="thirds" />
            </div>
          )}
          {!topVideo && tl.source !== "blank" && (
            <div className="pv-badge">{still ? `Still · shot ${shotIdx + 1}` : "Animatic · no stills rendered"}{shot ? ` · ${shot.shotKind} ${shot.lens}mm` : ""}{anim ? ` · ${anim.emotion}` : ""}</div>
          )}
          {tl.source === "blank" && !topVideo && <div className="pv-empty">Drop video on the timeline to preview it here</div>}
        </div>
      </div>

      <div className="transport">
        <span className="tc" style={{ minWidth: 92 }}>{timecode(playhead, fps)}</span>
        <div className="grow" />
        <IconButton size="sm" label="Go to start" kbd="Home" onClick={() => seek(0)}><SkipBack size={15} /></IconButton>
        <IconButton size="sm" label="Previous frame" kbd="←" onClick={() => seek(playhead - 1 / fps)}><ChevronLeft size={16} /></IconButton>
        <button className="play-btn" aria-label={playing ? "Pause" : "Play"} onClick={() => { if (!playing && playhead >= tl.duration - 0.01) seek(0); setPlaying(!playing); }}>
          {playing ? <Pause size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" style={{ marginLeft: 2 }} />}
        </button>
        <IconButton size="sm" label="Next frame" kbd="→" onClick={() => seek(playhead + 1 / fps)}><ChevronRight size={16} /></IconButton>
        <IconButton size="sm" label="Go to end" kbd="End" onClick={() => seek(tl.duration)}><SkipForward size={15} /></IconButton>
        <IconButton size="sm" label={loop ? "Loop on" : "Loop off"} on={loop} onClick={() => setLoop(!loop)}><Repeat size={14} /></IconButton>
        <div className="grow" />
        <span className="tc faint" style={{ minWidth: 92, textAlign: "right" }}>{timecode(tl.duration, fps)}</span>
      </div>
      <div className="transport sub">
        <div style={{ width: 92 }}><Select size="sm" ariaLabel="Preview zoom" value={String(zoom)} onChange={(v) => set({ previewZoom: v === "fit" ? "fit" : (Number(v) as 0.5 | 1) })}
          options={[{ value: "fit", label: "Fit" }, { value: "0.5", label: "50%" }, { value: "1", label: "100%" }]} /></div>
        <div style={{ width: 104 }}><Select size="sm" ariaLabel="Preview quality" value={quality} onChange={(v) => set({ quality: v })}
          options={[{ value: "full", label: "Full quality" }, { value: "half", label: "Half quality" }]} /></div>
        <div className="grow" />
        <span className="meta mono">{ratio} · {outW}×{outH}</span>
        <IconButton size="sm" label={showSubs ? "Hide subtitles" : "Show subtitles"} on={showSubs} onClick={() => set({ showSubs: !showSubs })}><Captions size={15} /></IconButton>
        <IconButton size="sm" label={guides ? "Hide safe areas" : "Show safe areas"} on={guides} onClick={() => set({ guides: !guides })}><Grid3x3 size={15} /></IconButton>
        <IconButton size="sm" label="Fullscreen" onClick={() => wrap.current?.requestFullscreen?.()}><Maximize size={14} /></IconButton>
      </div>
    </div>
  );
}

function VideoLayer({ clip, src, playhead, playing, muted }: { clip: Clip; src: string; playhead: number; playing: boolean; muted: boolean }) {
  const ref = useRef<HTMLVideoElement>(null);
  const image = /\.(png|jpe?g|webp)$/i.test(clip.src ?? "");
  useEffect(() => {
    const v = ref.current;
    if (!v || image) return;
    const want = (clip.offset ?? 0) + (playhead - clip.start);
    if (!playing || Math.abs(v.currentTime - want) > 0.25) v.currentTime = Math.max(0, want);
    v.volume = Math.max(0, Math.min(1, clip.volume ?? 1));
    if (playing && v.paused) void v.play().catch(() => undefined);
    if (!playing && !v.paused) v.pause();
  }, [playhead, playing, clip, image]);
  if (image) return <img className="pv-img" src={src} alt="" draggable={false} />;
  return <video ref={ref} className="pv-img" src={src} muted={muted} playsInline preload="auto" />;
}
