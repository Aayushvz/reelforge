// Drag-to-place controls for Shots-AV: where the desk sits in the room, and where the captions sit in the frame.
import { useEffect, useRef, useState, type PointerEvent as RPointerEvent } from "react";
import { Crosshair, Shuffle } from "lucide-react";
import type { RoomView } from "@/lib/types";
import type { AvPano } from "@/lib/shotsav";
import { avThumbUrl } from "@/lib/api";
import { FieldRow, Slider } from "@/components/ui/Form";

// "a little right of centre, level": what the frame shows, in words (screen readers read it out)
function describeView(pan: number, height: number) {
  const side = Math.abs(pan) < 0.05 ? "centred" : `${Math.round(Math.abs(pan) * 100)}% to the ${pan > 0 ? "right" : "left"}`;
  const up = Math.abs(height) < 0.05 ? "level" : `${Math.round(Math.abs(height) * 100)}% ${height > 0 ? "higher" : "lower"}`;
  return `${side}, ${up}`;
}

const clamp = (v: number, lo = -1, hi = 1) => Math.min(hi, Math.max(lo, v));
const r2 = (v: number) => Math.round(v * 100) / 100;
const capture = (e: RPointerEvent) => { try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch { /* not a live pointer */ } };

// ---------- the room: drag the 9:16 frame across the room's panorama ----------
export function RoomFramePicker({ roomId, label, pano, view, spots, onChange }: {
  roomId: string; label: string; pano: AvPano | null | undefined; view: RoomView | undefined;
  spots: RoomView[]; onChange: (v: RoomView | null) => void;
}) {
  const [live, setLive] = useState<RoomView>(view ?? {});
  const box = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; pan: number; height: number } | null>(null);
  const latest = useRef<RoomView>(live);
  latest.current = live;
  useEffect(() => setLive(view ?? {}), [view, roomId]);
  if (!pano) return <div className="meta">The panorama for {label} isn't rendered yet; the room uses its default view.</div>;

  const pan = live.pan ?? 0, height = live.height ?? 0;
  const f = pano.frame;
  const left = (f.x + pan * pano.pan_px) / pano.w, top = (f.y - height * pano.height_px) / pano.h;
  const scale = () => (box.current?.clientWidth ?? pano.w) / pano.w;
  const commit = (v: RoomView) => onChange({ ...v, pan: r2(v.pan ?? 0), height: r2(v.height ?? 0), turn: r2(v.turn ?? 0) });

  const down = (e: RPointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    capture(e);
    drag.current = { x: e.clientX, y: e.clientY, pan, height };
  };
  const move = (e: RPointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d) return;
    const k = scale();
    const next = { ...latest.current, pan: clamp(d.pan + (e.clientX - d.x) / k / pano.pan_px),
      height: clamp(d.height - (e.clientY - d.y) / k / pano.height_px) };
    latest.current = next;  // the release may arrive before React re-renders
    setLive(next);
  };
  const up = () => { if (drag.current) { drag.current = null; commit(latest.current); } };
  const jump = (e: RPointerEvent<HTMLDivElement>) => {  // click on the room: centre the frame there
    if (e.target !== e.currentTarget && !(e.target as HTMLElement).classList.contains("av-pano-img")) return;
    const rect = box.current!.getBoundingClientRect(), k = scale();
    const px = (e.clientX - rect.left) / k, py = (e.clientY - rect.top) / k;
    const v = { ...live, pan: clamp((px - f.w / 2 - f.x) / pano.pan_px), height: clamp(-(py - f.h / 2 - f.y) / pano.height_px) };
    setLive(v); commit(v);
  };
  const spotIndex = spots.findIndex((s) => r2(s.pan ?? 0) === r2(pan) && r2(s.height ?? 0) === r2(height));
  return (
    <div className="col" style={{ gap: 8 }}>
      <div ref={box} className="av-pano" style={{ aspectRatio: `${pano.w} / ${pano.h}` }} onPointerDown={jump}>
        <img className="av-pano-img" src={avThumbUrl(`${roomId}_pano`)} alt={`${label}, the whole back wall`} draggable={false} />
        <div className="av-pano-frame" role="slider" tabIndex={0} aria-label="The part of the room behind you"
          aria-valuemin={-100} aria-valuemax={100} aria-valuenow={Math.round(pan * 100)} aria-valuetext={describeView(pan, height)}
          aria-description="Arrow keys move the frame; Shift moves it further"
          style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${(f.w / pano.w) * 100}%`, height: `${(f.h / pano.h) * 100}%` }}
          onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
          onKeyDown={(e) => {
            const step = e.shiftKey ? 0.2 : 0.05;
            const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }[e.key];
            if (!d) return;
            e.preventDefault();
            const v = { ...live, pan: clamp(pan + d[0]), height: clamp(height + d[1]) };
            setLive(v); commit(v);
          }}>
          <svg className="av-pano-desk" viewBox="0 0 90 160" preserveAspectRatio="none" aria-hidden>
            <ellipse cx="45" cy="92" rx="11" ry="12" />
            <path d="M24 128 Q45 100 66 128 Z" />
            <rect x="0" y="126" width="90" height="34" rx="2" />
          </svg>
        </div>
      </div>
      <div className="row" style={{ gap: 6 }}>
        <span className="meta grow">Drag the frame (or click the room) to choose what sits behind you.</span>
        {spots.length > 1 && <button className="btn btn-sm" title="One of this room's good views"
          onClick={() => { const s = spots[(spotIndex + 1) % spots.length]; setLive(s); commit(s); }}><Shuffle size={12} />Next view</button>}
        <button className="btn btn-sm" title="Let each project pick one of the room's good views" disabled={!view}
          onClick={() => onChange(null)}><Crosshair size={12} />Auto</button>
      </div>
      <FieldRow label="Turn"><Slider ariaLabel="Turn the room" min={-1} max={1} step={0.05} value={live.turn ?? 0}
        format={(v) => `${Math.round(v * 12)}°`} onChange={(v) => { const n = { ...live, turn: v }; setLive(n); commit(n); }} /></FieldRow>
    </div>
  );
}

// ---------- captions: drag the caption around a 9:16 frame ----------
export function CaptionPlacer({ x, y, size, still, sample, onChange }: {
  x: number; y: number; size: number; still?: string; sample: string; onChange: (p: { x: number; y: number }) => void;
}) {
  const [pos, setPos] = useState({ x, y });
  const box = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const last = useRef(pos);
  useEffect(() => setPos({ x, y }), [x, y]);
  const at = (e: RPointerEvent) => {
    const r = box.current!.getBoundingClientRect();
    return { x: r2(clamp((e.clientX - r.left) / r.width, 0.05, 0.95)), y: r2(clamp((e.clientY - r.top) / r.height, 0.04, 0.96)) };
  };
  return (
    <div ref={box} className="av-cap-frame" style={still ? { backgroundImage: `url(${still})` } : undefined}
      onPointerDown={(e) => { e.preventDefault(); capture(e); dragging.current = true; last.current = at(e); setPos(last.current); }}
      onPointerMove={(e) => { if (dragging.current) { last.current = at(e); setPos(last.current); } }}
      onPointerUp={() => { if (dragging.current) { dragging.current = false; onChange(last.current); } }}
      onPointerCancel={() => { dragging.current = false; }}>
      <div className="av-cap-safe top" title="Platform UI: keep faces and text out" />
      <div className="av-cap-safe bottom" />
      <div className="av-cap-chip" role="slider" tabIndex={0} aria-label="Caption position"
        aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pos.y * 100)}
        aria-valuetext={`${Math.round(pos.x * 100)}% across, ${Math.round(pos.y * 100)}% down`}
        aria-description="Arrow keys move the caption"
        style={{ left: `${pos.x * 100}%`, top: `${pos.y * 100}%`, fontSize: `${Math.round(7.5 * size)}px` }}
        onKeyDown={(e) => {
          const d = { ArrowLeft: [-0.02, 0], ArrowRight: [0.02, 0], ArrowUp: [0, -0.02], ArrowDown: [0, 0.02] }[e.key];
          if (!d) return;
          e.preventDefault();
          const n = { x: r2(clamp(pos.x + d[0], 0.05, 0.95)), y: r2(clamp(pos.y + d[1], 0.04, 0.96)) };
          setPos(n); onChange(n);
        }}>{sample}</div>
    </div>
  );
}
