// Multi-track timeline: ruler, track headers, clips with move/trim/split, snapping, zoom and drops.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  Scissors, Trash2, Copy, Magnet, ZoomIn, ZoomOut, Maximize2, Plus, Volume2, VolumeX, Lock, Unlock, Eye, EyeOff,
  RotateCcw, Film, Type, Music, AudioLines, RefreshCw,
} from "lucide-react";
import type { Clip, Track, TrackKind } from "@/lib/types";
import * as T from "@/lib/timeline";
import { timecode } from "@/lib/format";
import { MOOD_COLORS } from "@/data/catalog";
import { useMenu, Confirm } from "@/components/ui/Overlay";
import { IconButton } from "@/components/ui/Form";
import { useEditor } from "./store";
import { usePeaks } from "./media";

const HEADER_W = 176;
const RULER_H = 28;
const rowHeight = (k: TrackKind) => (["dialogue", "music", "sfx", "audio", "video", "shots"].includes(k) ? 46 : 32);
const SHOT_ABBR = { wide: "WS", medium: "MS", closeup: "CU" } as const;

type Props = { fps: number; resolveSrc: (src: string) => string; onRebuild?: () => void; canRebuild: boolean; onShotAction: (clip: Clip, action: "regenerate") => void };

export function Timeline({ fps, resolveSrc, onRebuild, canRebuild, onShotAction }: Props) {
  const tl = useEditor((s) => s.tl)!;
  const pps = useEditor((s) => s.pps);
  const playhead = useEditor((s) => s.playhead);
  const playing = useEditor((s) => s.playing);
  const selection = useEditor((s) => s.selection);
  const snapping = useEditor((s) => s.snapping);
  const { edit, live, commitFrom, select, seek, setPps, set } = useEditor.getState();
  const scroller = useRef<HTMLDivElement>(null);
  const menu = useMenu();
  const [snapAt, setSnapAt] = useState<number | null>(null);
  const [dropHint, setDropHint] = useState<string | null>(null);
  const [confirmRebuild, setConfirmRebuild] = useState(false);

  const width = Math.max(tl.duration, T.contentEnd(tl)) * pps + 240;

  const fit = () => {
    const el = scroller.current;
    if (!el) return;
    setPps((el.clientWidth - HEADER_W - 32) / Math.max(1, Math.max(tl.duration, T.contentEnd(tl))));
  };
  useLayoutEffect(fit, [tl.source]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    window.addEventListener("reelforge:fit-timeline", fit);
    return () => window.removeEventListener("reelforge:fit-timeline", fit);
  });

  // keep the playhead visible during playback
  useEffect(() => {
    const el = scroller.current;
    if (!el || !playing) return;
    const x = playhead * pps + HEADER_W;
    if (x > el.scrollLeft + el.clientWidth - 40 || x < el.scrollLeft + HEADER_W) el.scrollLeft = x - HEADER_W - 40;
  }, [playhead, playing, pps]);

  // ctrl/cmd + wheel zooms around the pointer
  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      const { pps: cur } = useEditor.getState();
      const rect = el.getBoundingClientRect();
      const t = (e.clientX - rect.left + el.scrollLeft - HEADER_W) / cur;
      const next = Math.max(4, Math.min(600, cur * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
      setPps(next);
      requestAnimationFrame(() => { el.scrollLeft = t * next - (e.clientX - rect.left - HEADER_W); });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [setPps]);

  const timeAt = (clientX: number) => {
    const el = scroller.current!;
    return Math.max(0, (clientX - el.getBoundingClientRect().left + el.scrollLeft - HEADER_W) / pps);
  };

  // ---------- scrubbing ----------
  const scrub = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    seek(timeAt(e.clientX));
    const move = (ev: PointerEvent) => seek(timeAt(ev.clientX));
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  // ---------- clip gestures ----------
  const startGesture = (e: React.PointerEvent, clip: Clip, mode: "move" | "trim-l" | "trim-r") => {
    if (e.button !== 0) return;
    e.stopPropagation();
    const track = T.trackOf(tl, clip);
    let ids = selection;
    if (e.shiftKey || e.ctrlKey || e.metaKey) {
      ids = selection.includes(clip.id) ? selection.filter((x) => x !== clip.id) : [...selection, clip.id];
      select(ids);
      return;
    }
    if (!selection.includes(clip.id)) { ids = [clip.id]; select(ids); }
    if (track.locked) return;
    const before = tl;
    const x0 = e.clientX;
    const originals = new Map(before.clips.filter((c) => ids.includes(c.id)).map((c) => [c.id, c]));
    const points = T.snapPoints(before, useEditor.getState().playhead, [...originals.keys()]);
    const tol = 8 / pps;
    let moved = false;

    const move = (ev: PointerEvent) => {
      const dx = (ev.clientX - x0) / pps;
      if (!moved && Math.abs(ev.clientX - x0) < 3) return;
      moved = true;
      let snapped: number | null = null;
      const doSnap = (t: number) => {
        if (!useEditor.getState().snapping || ev.altKey) return t;
        const s = T.snap(t, points, tol);
        if (s !== t) snapped = s;
        return s;
      };
      let clips = before.clips;
      if (mode === "move") {
        let d = dx;
        const start = clip.start + dx;
        const sStart = doSnap(start);
        if (sStart !== start) d = sStart - clip.start;
        else { const end = start + clip.duration; const sEnd = doSnap(end); if (sEnd !== end) d = sEnd - T.clipEnd(clip); }
        const minStart = Math.min(...[...originals.values()].map((c) => c.start));
        d = Math.max(d, -minStart);
        // vertical: move a single clip to a compatible track under the pointer
        let targetTrack = clip.trackId;
        if (originals.size === 1) {
          const row = (document.elementFromPoint(ev.clientX, ev.clientY) as HTMLElement | null)?.closest<HTMLElement>("[data-track]");
          const t = row && before.tracks.find((x) => x.id === row.dataset.track);
          if (t && !t.locked && T.COMPATIBLE[track.kind].includes(t.kind)) targetTrack = t.id;
        }
        clips = before.clips.map((c) => {
          const o = originals.get(c.id);
          return o ? { ...c, start: o.start + d, trackId: originals.size === 1 ? targetTrack : c.trackId } : c;
        });
      } else if (mode === "trim-l") {
        let start = doSnap(clip.start + dx);
        start = Math.max(0, Math.min(start, T.clipEnd(clip) - T.MIN_CLIP));
        if (clip.src && clip.offset !== undefined) start = Math.max(start, clip.start - clip.offset);
        const d = start - clip.start;
        clips = before.clips.map((c) => (c.id === clip.id ? { ...c, start, duration: clip.duration - d, offset: clip.offset !== undefined ? clip.offset + d : undefined } : c));
      } else {
        const end = Math.max(clip.start + T.MIN_CLIP, doSnap(T.clipEnd(clip) + dx));
        clips = before.clips.map((c) => (c.id === clip.id ? { ...c, duration: end - clip.start } : c));
      }
      setSnapAt(snapped);
      const next = { ...before, clips };
      live({ ...next, duration: Math.max(before.duration, T.contentEnd(next)) });
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      setSnapAt(null);
      if (moved) commitFrom(before);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const clipMenu = (e: React.MouseEvent, clip: Clip) => {
    e.preventDefault();
    if (!selection.includes(clip.id)) select([clip.id]);
    const ids = selection.includes(clip.id) ? selection : [clip.id];
    const track = T.trackOf(tl, clip);
    const compatible = tl.tracks.filter((t) => t.id !== clip.trackId && T.COMPATIBLE[track.kind].includes(t.kind));
    menu.openAt({ x: e.clientX, y: e.clientY }, [
      { label: "Split at playhead", icon: <Scissors size={14} />, kbd: "S", disabled: track.locked, onSelect: () => edit((t) => T.splitAtPlayhead(t, ids, useEditor.getState().playhead)) },
      { label: "Duplicate", icon: <Copy size={14} />, kbd: "Ctrl D", disabled: track.locked, onSelect: () => { const r = T.duplicateClips(tl, ids); edit(() => r.tl); select(r.ids); } },
      ...(track.kind === "shots" ? [{ label: "Regenerate still", icon: <RefreshCw size={14} />, onSelect: () => onShotAction(clip, "regenerate") }] : []),
      ...compatible.map((t) => ({ label: `Move to ${t.name}`, icon: <Film size={14} />, disabled: track.locked || t.locked, onSelect: () => edit((x) => T.updateClip(x, clip.id, { trackId: t.id })) })),
      { separator: true },
      { label: "Delete", icon: <Trash2 size={14} />, kbd: "Del", danger: true, disabled: track.locked, onSelect: () => { edit((t) => T.removeClips(t, ids)); select([]); } },
    ]);
  };

  // ---------- drops from the media panel ----------
  const onDrop = (e: React.DragEvent, track: Track) => {
    const raw = e.dataTransfer.getData("application/x-reelforge-media");
    setDropHint(null);
    if (!raw) return;
    e.preventDefault();
    const m = JSON.parse(raw) as { path: string; kind: "video" | "audio" | "image"; duration: number; name: string };
    const want: TrackKind[] = m.kind === "audio" ? ["audio", "music", "sfx"] : ["video"];
    let target = want.includes(track.kind) && !track.locked ? track : tl.tracks.find((t) => want.includes(t.kind) && !t.locked);
    let next = tl;
    if (!target) { next = T.addTrack(tl, want[0]); target = next.tracks.find((t) => t.kind === want[0])!; }
    const clip: Clip = { id: `c${Date.now().toString(36)}`, trackId: target.id, start: timeAt(e.clientX), duration: m.duration || 5, label: m.name, src: m.path, offset: 0, volume: 1 };
    edit(() => T.updateClip({ ...next, clips: [...next.clips, clip] }, clip.id, {}));
    select([clip.id]);
  };

  const addTrackMenu = (e: React.MouseEvent<HTMLButtonElement>) => menu.openAt(e.currentTarget.getBoundingClientRect(), [
    { heading: "Add track" },
    { label: "Video", icon: <Film size={14} />, onSelect: () => edit((t) => T.addTrack(t, "video")) },
    { label: "Text overlay", icon: <Type size={14} />, onSelect: () => edit((t) => T.addTrack(t, "overlay")) },
    { label: "Audio", icon: <AudioLines size={14} />, onSelect: () => edit((t) => T.addTrack(t, "audio")) },
    { label: "Music", icon: <Music size={14} />, onSelect: () => edit((t) => T.addTrack(t, "music")) },
    { label: "Sound effects", icon: <Volume2 size={14} />, onSelect: () => edit((t) => T.addTrack(t, "sfx")) },
  ]);

  const shotIndex = useMemo(() => {
    const m = new Map<string, number>();
    tl.clips.filter((c) => T.trackOf(tl, c).kind === "shots").sort((a, b) => a.start - b.start).forEach((c, i) => m.set(c.id, i + 1));
    return m;
  }, [tl]);

  const hasSel = selection.length > 0;
  return (
    <div className="tl">
      <div className="tl-toolbar">
        <IconButton label="Split at playhead" kbd="S" size="sm" onClick={() => edit((t) => T.splitAtPlayhead(t, selection, useEditor.getState().playhead))}><Scissors size={15} /></IconButton>
        <IconButton label="Duplicate" kbd="Ctrl D" size="sm" disabled={!hasSel} onClick={() => { const r = T.duplicateClips(tl, selection); edit(() => r.tl); select(r.ids); }}><Copy size={15} /></IconButton>
        <IconButton label="Delete" kbd="Del" size="sm" disabled={!hasSel} onClick={() => { edit((t) => T.removeClips(t, selection)); select([]); }}><Trash2 size={15} /></IconButton>
        <span className="vdivider" style={{ margin: "6px 4px" }} />
        <IconButton label={snapping ? "Snapping on" : "Snapping off"} kbd="N" size="sm" on={snapping} onClick={() => set({ snapping: !snapping })}><Magnet size={15} /></IconButton>
        <IconButton label="Add track" size="sm" onClick={addTrackMenu}><Plus size={15} /></IconButton>
        <IconButton label="Add text at playhead" size="sm" onClick={() => {
          let next = tl;
          let track = next.tracks.find((t) => t.kind === "overlay" && !t.locked);
          if (!track) { next = T.addTrack(next, "overlay"); track = next.tracks.find((t) => t.kind === "overlay")!; }
          const clip: Clip = { id: `c${Date.now().toString(36)}`, trackId: track.id, start: useEditor.getState().playhead, duration: 3, label: "Your text", text: "Your text", color: "#FFFFFF", offset: 0.12 };
          edit(() => T.updateClip({ ...next, clips: [...next.clips, clip] }, clip.id, {}));
          select([clip.id]);
        }}><Type size={15} /></IconButton>
        {canRebuild && <IconButton label="Rebuild from script" size="sm" onClick={() => setConfirmRebuild(true)}><RotateCcw size={15} /></IconButton>}
        <span className="meta" style={{ marginLeft: 8 }}>{hasSel ? `${selection.length} selected` : tl.source === "script" ? "Shots estimated from the script" : tl.source === "render-plan" ? "Shots from the director's render plan" : ""}</span>
        <div className="grow" />
        <span className="tc meta">{timecode(playhead, fps)} <span className="faint">/ {timecode(tl.duration, fps)}</span></span>
        <span className="vdivider" style={{ margin: "6px 4px" }} />
        <IconButton label="Zoom out" kbd="-" size="sm" onClick={() => setPps(pps / 1.4)}><ZoomOut size={15} /></IconButton>
        <input className="range" type="range" min={0} max={1} step={0.001} aria-label="Timeline zoom" style={{ width: 96, ["--fill" as string]: `${(Math.log(pps / 4) / Math.log(150)) * 100}%` }}
          value={Math.log(pps / 4) / Math.log(150)} onChange={(e) => setPps(4 * Math.pow(150, Number(e.target.value)))} />
        <IconButton label="Zoom in" kbd="=" size="sm" onClick={() => setPps(pps * 1.4)}><ZoomIn size={15} /></IconButton>
        <IconButton label="Zoom to fit" kbd="0" size="sm" onClick={fit}><Maximize2 size={14} /></IconButton>
      </div>

      <div className="tl-scroll" ref={scroller} onPointerDown={(e) => { if ((e.target as HTMLElement).classList.contains("tl-lane")) { select([]); scrub(e); } }}>
        <div className="tl-content" style={{ width: width + HEADER_W }}>
          <div className="tl-row tl-ruler-row" style={{ height: RULER_H }}>
            <div className="tl-corner" style={{ width: HEADER_W }} />
            <Ruler pps={pps} width={width} fps={fps} onPointerDown={scrub} />
          </div>
          {tl.tracks.map((track) => (
            <div key={track.id} className={`tl-row${track.hidden ? " hidden" : ""}${dropHint === track.id ? " drop" : ""}`} data-track={track.id} style={{ height: rowHeight(track.kind) }}
              onDragOver={(e) => { if (e.dataTransfer.types.includes("application/x-reelforge-media")) { e.preventDefault(); setDropHint(track.id); } }}
              onDragLeave={() => setDropHint(null)} onDrop={(e) => onDrop(e, track)}>
              <TrackHeader track={track} width={HEADER_W} onChange={(patch) => edit((t) => T.updateTrack(t, track.id, patch))}
                onRemove={tl.tracks.length > 1 && !tl.clips.some((c) => c.trackId === track.id) ? () => edit((t) => ({ ...t, tracks: t.tracks.filter((x) => x.id !== track.id) })) : undefined} />
              <div className={`tl-lane${track.locked ? " locked" : ""}`} style={{ width }}>
                {tl.clips.filter((c) => c.trackId === track.id).map((c) => (
                  <ClipView key={c.id} clip={c} track={track} pps={pps} selected={selection.includes(c.id)} shotNo={shotIndex.get(c.id)} resolveSrc={resolveSrc}
                    onPointerDown={startGesture} onContextMenu={clipMenu} onDoubleClick={() => seek(c.start)}
                    onSelect={() => { select([c.id]); seek(c.start); }} />
                ))}
              </div>
            </div>
          ))}
          <div className="tl-playhead" style={{ left: HEADER_W + playhead * pps }}><span /></div>
          {snapAt !== null && <div className="tl-snapline" style={{ left: HEADER_W + snapAt * pps }} />}
        </div>
      </div>
      {menu.node}
      {confirmRebuild && onRebuild && <Confirm title="Rebuild the timeline from the script?" confirmLabel="Rebuild" onClose={() => setConfirmRebuild(false)} onConfirm={onRebuild}
        body="Shots, dialogue, moods and captions are laid out again from the current script and any render plan. Imported media and manual edits on the generated tracks are replaced. You can undo this." />}
    </div>
  );
}

function Ruler({ pps, width, fps, onPointerDown }: { pps: number; width: number; fps: number; onPointerDown: (e: React.PointerEvent) => void }) {
  const steps = [1 / fps, 2 / fps, 5 / fps, 10 / fps, 0.5, 1, 2, 5, 10, 15, 30, 60, 120];
  const major = steps.find((s) => s * pps >= 80) ?? 120;
  const minor = major / (major >= 1 ? 5 : 2);
  const ticks: JSX.Element[] = [];
  const end = width / pps;
  for (let t = 0, i = 0; t <= end; t = ++i * minor) {
    const isMajor = Math.abs(t / major - Math.round(t / major)) < 1e-6;
    ticks.push(<div key={i} className={`tick${isMajor ? " major" : ""}`} style={{ left: t * pps }}>{isMajor && <span>{major < 1 ? timecode(t, fps) : timecode(t, fps, false)}</span>}</div>);
  }
  return <div className="tl-ruler" style={{ width }} onPointerDown={onPointerDown}>{ticks}</div>;
}

function TrackHeader({ track, width, onChange, onRemove }: { track: Track; width: number; onChange: (p: Partial<Track>) => void; onRemove?: () => void }) {
  const audio = T.AUDIO_KINDS.includes(track.kind);
  return (
    <div className="tl-head" style={{ width }}>
      <span className="tl-swatch" style={{ background: T.TRACK_COLOR[track.kind] }} />
      <span className="ellipsis grow" title={track.name}>{track.name}</span>
      {audio && <IconButton size="xs" label={track.muted ? "Unmute" : "Mute"} on={track.muted} onClick={() => onChange({ muted: !track.muted })}>{track.muted ? <VolumeX size={12} /> : <Volume2 size={12} />}</IconButton>}
      <IconButton size="xs" label={track.locked ? "Unlock" : "Lock"} on={track.locked} onClick={() => onChange({ locked: !track.locked })}>{track.locked ? <Lock size={12} /> : <Unlock size={12} />}</IconButton>
      <IconButton size="xs" label={track.hidden ? "Show" : "Hide"} on={track.hidden} onClick={() => onChange({ hidden: !track.hidden })}>{track.hidden ? <EyeOff size={12} /> : <Eye size={12} />}</IconButton>
      {onRemove && <IconButton size="xs" label="Remove empty track" onClick={onRemove}><Trash2 size={11} /></IconButton>}
    </div>
  );
}

function ClipView({ clip, track, pps, selected, shotNo, resolveSrc, onPointerDown, onContextMenu, onDoubleClick, onSelect }: {
  clip: Clip; track: Track; pps: number; selected: boolean; shotNo?: number; resolveSrc: (s: string) => string;
  onPointerDown: (e: React.PointerEvent, c: Clip, mode: "move" | "trim-l" | "trim-r") => void;
  onContextMenu: (e: React.MouseEvent, c: Clip) => void; onDoubleClick: () => void; onSelect: () => void;
}) {
  const w = Math.max(2, clip.duration * pps);
  const color = track.kind === "mood" && clip.mood ? MOOD_COLORS[clip.mood] : T.TRACK_COLOR[track.kind];
  const audio = T.AUDIO_KINDS.includes(track.kind) && clip.src;
  let label = clip.label;
  if (track.kind === "shots" && clip.shotKind) label = `${shotNo ?? ""} · ${SHOT_ABBR[clip.shotKind]} ${clip.lens ?? ""}mm`;
  if (track.kind === "animation") label = `${clip.emotion ?? clip.label} ${clip.intensity !== undefined ? clip.intensity.toFixed(1) : ""}`;
  return (
    <div className={`clip k-${track.kind}${selected ? " sel" : ""}${clip.status === "estimated" ? " est" : ""}`} role="button" tabIndex={0} aria-label={label} aria-pressed={selected}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); } }}
      style={{ left: clip.start * pps, width: w, ["--c" as string]: color }}
      onPointerDown={(e) => onPointerDown(e, clip, "move")} onContextMenu={(e) => onContextMenu(e, clip)} onDoubleClick={onDoubleClick}>
      {audio && <Waveform url={resolveSrc(clip.src!)} offset={clip.offset ?? 0} duration={clip.duration} width={w} />}
      {w > 24 && <span className="clip-label">{label}</span>}
      {track.kind === "dialogue" && !clip.src && w > 90 && <span className="clip-tag">no audio</span>}
      {w > 12 && <>
        <span className="clip-handle l" onPointerDown={(e) => onPointerDown(e, clip, "trim-l")} />
        <span className="clip-handle r" onPointerDown={(e) => onPointerDown(e, clip, "trim-r")} />
      </>}
      {(clip.fadeIn ?? 0) > 0 && <span className="fade in" style={{ width: clip.fadeIn! * pps }} />}
      {(clip.fadeOut ?? 0) > 0 && <span className="fade out" style={{ width: clip.fadeOut! * pps }} />}
    </div>
  );
}

function Waveform({ url, offset, duration, width }: { url: string; offset: number; duration: number; width: number }) {
  const peaks = usePeaks(url);
  const ref = useRef<HTMLCanvasElement>(null);
  const w = Math.min(4000, Math.ceil(width));
  useEffect(() => {
    const c = ref.current;
    if (!c || !peaks) return;
    const h = c.height;
    const g = c.getContext("2d")!;
    g.clearRect(0, 0, c.width, h);
    g.fillStyle = "rgba(255,255,255,0.38)";
    for (let x = 0; x < c.width; x++) {
      const t = offset + (x / c.width) * duration;
      const v = peaks.data[Math.floor(t * peaks.perSec)] ?? 0;
      const bar = Math.max(1, v * (h - 4));
      g.fillRect(x, (h - bar) / 2, 1, bar);
    }
  }, [peaks, offset, duration, w]);
  return <canvas ref={ref} className="clip-wave" width={w} height={30} style={{ width }} />;
}
