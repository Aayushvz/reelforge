// Thumbnail Generator: pick any frame of any video and make a cover from it at any size.
// The canvas preview and the export share one renderer (lib/cover.ts), so what you see is what you download.
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Download, FileVideo, ImageIcon, Sparkles } from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import {
  applyVariant, cleanFramePath, download, loadImage, saveStyle, savedStyle, drawCover, ensureFonts, fileSafe, FONTS, renderCover, SAFE_ZONES, SIZE_PRESETS,
  SNAPS, snapTo, type Box, type CoverDoc, type CoverDraft, type Layer, type SafeZone, type Snap,
} from "@/lib/cover";
import { ColorInput, FieldRow, Section, Segmented, Select, Slider, Switch } from "@/components/ui/Form";
import { Callout, Empty, Spinner } from "@/components/ui/Feedback";
import { toast } from "@/stores/ui";
import "./thumbnails.css";

const SNAP_LABELS: Record<Snap, string> = {
  tl: "Top left", tc: "Top centre", tr: "Top right", ml: "Middle left", mc: "Centre", mr: "Middle right",
  bl: "Bottom left", bc: "Bottom centre", br: "Bottom right",
};
const LAYERS: { value: Layer; label: string }[] = [
  { value: "headline", label: "Headline" }, { value: "pill", label: "Caption" }, { value: "frame", label: "Frame" },
];

const fmtTime = (t: number) => `${Math.floor(t / 60)}:${(t % 60).toFixed(2).padStart(5, "0")}`;

export function ThumbnailGenerator() {
  const [params, setParams] = useSearchParams();
  const projectId = params.get("project");
  const [doc, setDoc] = useState<CoverDoc>(savedStyle);
  const [sel, setSel] = useState<Layer>("headline");
  const [safe, setSafe] = useState<SafeZone>("none");
  const [fmt, setFmt] = useState<"png" | "jpg">("png");
  const [video, setVideo] = useState<{ url: string; name: string } | null>(null);
  const [duration, setDuration] = useState(0);
  const [time, setTime] = useState(0);
  const [fps, setFps] = useState(30);
  const [draft, setDraft] = useState<CoverDraft | null>(null);
  const [draftErr, setDraftErr] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [tick, setTick] = useState(0); // bumps when a new frame or font is ready
  const [busy, setBusy] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const boxes = useRef<Record<"headline" | "pill", Box | null>>({ headline: null, pill: null });
  const drag = useRef<{ layer: Layer; x: number; y: number; doc: CoverDoc } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const pendingSeek = useRef<number | null>(null);
  const [view, setView] = useState({ w: 360, h: 640 });
  const [clean, setClean] = useState(true);
  const [still, setStill] = useState<HTMLImageElement | null>(null);
  const cleanDir = projectId && draft?.frames ? draft.frames : null;

  useEffect(() => { void api.projects().then((p) => setProjects(p.filter((x) => x.final))).catch(() => undefined); }, []);
  useEffect(() => {
    saveStyle(doc);
  }, [doc]);
  useEffect(() => { void ensureFonts(doc).then(() => setTick((t) => t + 1)); }, [doc.font, doc.weight]);

  // a project link: load its final video and drafted cover
  useEffect(() => {
    if (!projectId) return;
    setDraft(null); setDraftErr(null);
    api.cover(projectId).then((d) => {
      setDraft(d); setFps(d.fps || 30);
      setVideo({ url: fileUrl(projectId, d.video, Date.now()), name: projects.find((p) => p.id === projectId)?.name ?? projectId });
      const preset = SIZE_PRESETS.find((p) => p.w === d.width && p.h === d.height);
      const v = d.variants[Number(params.get("variant") ?? 0)] ?? d.variants[0];
      setDoc((cur) => {
        const sized = preset ? { ...cur, preset: preset.id, width: preset.w, height: preset.h } : cur;
        return v ? applyVariant(sized, v) : sized;
      });
      if (v) pendingSeek.current = v.time;
    }).catch((e: Error) => setDraftErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // fit the preview to the stage
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const fit = () => {
      const r = el.getBoundingClientRect();
      const maxW = Math.max(160, r.width - 32), maxH = Math.max(200, Math.min(window.innerHeight * 0.72, 900));
      const s = Math.min(maxW / doc.width, maxH / doc.height);
      setView({ w: Math.round(doc.width * s), h: Math.round(doc.height * s) });
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [doc.width, doc.height]);

  // the clean rendered frame when the project has one, else the video itself
  const source = () => {
    const v = videoRef.current;
    return still ?? (v && v.readyState >= 2 ? v : null);
  };
  const draw = useCallback(() => {
    const c = canvasRef.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const W = Math.round(view.w * dpr), H = Math.round(view.h * dpr);
    if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
    boxes.current = drawCover(c.getContext("2d")!, doc, source(), W, H, { safeZone: safe, selected: sel === "frame" ? null : sel });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc, view, safe, sel, still]);
  useEffect(() => { draw(); }, [draw, tick]);

  const seek = (t: number) => {
    const v = videoRef.current;
    if (!v || !duration) return;
    v.currentTime = Math.min(Math.max(0, t), Math.max(0, duration - 0.01));
  };
  const step = (n: number) => seek(time + n / fps);

  const openFile = (f: File | undefined) => {
    if (!f) return;
    if (!f.type.startsWith("video/")) { toast("That isn't a video file", "err"); return; }
    if (video?.url.startsWith("blob:")) URL.revokeObjectURL(video.url);
    setVideo({ url: URL.createObjectURL(f), name: f.name });
    setDraft(null); setDraftErr(null);
    if (projectId) setParams({}, { replace: true });
  };

  // ---------- pointer: drag the headline, the caption, or the frame's crop ----------
  const toCanvas = (e: PointerEvent<HTMLCanvasElement>) => {
    const c = canvasRef.current!, r = c.getBoundingClientRect();
    return { x: (e.clientX - r.left) * (c.width / r.width), y: (e.clientY - r.top) * (c.height / r.height) };
  };
  const hit = (p: { x: number; y: number }): Layer => {
    const pad = 10;
    for (const k of ["pill", "headline"] as const) {
      const b = boxes.current[k];
      if (b && p.x >= b.x - pad && p.x <= b.x + b.w + pad && p.y >= b.y - pad && p.y <= b.y + b.h + pad) return k;
    }
    return "frame";
  };
  const onDown = (e: PointerEvent<HTMLCanvasElement>) => {
    const p = toCanvas(e);
    const layer = hit(p);
    setSel(layer);
    drag.current = { layer, x: p.x, y: p.y, doc };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const move = (layer: Layer, dxF: number, dyF: number, from: CoverDoc): CoverDoc => {
    if (layer === "headline") return { ...from, x: from.x + dxF, y: from.y + dyF };
    if (layer === "pill") return { ...from, pill: { ...from.pill, x: from.pill.x + dxF, y: from.pill.y + dyF } };
    // frame: moving the picture right shows more of its left side
    const v = videoRef.current;
    const vw = v?.videoWidth || from.width, vh = v?.videoHeight || from.height;
    const s = Math.max(from.width / vw, from.height / vh) * from.zoom;
    const ox = vw * s / from.width - 1, oy = vh * s / from.height - 1;
    const clamp = (n: number) => Math.min(1, Math.max(0, n));
    return { ...from, focus: { x: ox > 0.001 ? clamp(from.focus.x - dxF / ox) : from.focus.x, y: oy > 0.001 ? clamp(from.focus.y - dyF / oy) : from.focus.y } };
  };
  const onMove = (e: PointerEvent<HTMLCanvasElement>) => {
    const d = drag.current;
    const c = canvasRef.current;
    if (!d || !c) return;
    const p = toCanvas(e);
    setDoc(move(d.layer, (p.x - d.x) / c.width, (p.y - d.y) / c.height, d.doc));
  };
  const onUp = () => { drag.current = null; };
  // keyboard alternative to dragging (WCAG 2.5.7)
  const onKey = (e: KeyboardEvent<HTMLCanvasElement>) => {
    const k = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
    if (!k) return;
    e.preventDefault();
    const n = e.shiftKey ? 0.02 : 0.004;
    setDoc((d) => move(sel, k[0] * n, k[1] * n, d));
  };
  const snap = (s: Snap) => {
    const c = canvasRef.current;
    const b = sel === "pill" ? boxes.current.pill : boxes.current.headline;
    if (!c || !b) return;
    const p = snapTo(s, b, c.width, c.height);
    if (sel === "pill") setDoc((d) => ({ ...d, pill: { ...d.pill, x: p.x + b.w / c.width / 2, y: p.y } }));
    else setDoc((d) => ({ ...d, x: p.x, y: p.y }));
  };

  // page shortcuts: , and . step one frame
  useEffect(() => {
    const k = (e: globalThis.KeyboardEvent) => {
      if ((e.target as HTMLElement | null)?.closest?.("input, textarea, select, [contenteditable]")) return;
      if (e.key === ",") step(-1);
      if (e.key === ".") step(1);
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });

  const exportNow = async () => {
    setBusy(true);
    try {
      const blob = await renderCover(doc, source(), fmt === "png" ? "image/png" : "image/jpeg");
      download(blob, `${fileSafe(doc.lines.map((l) => l.text).join(" "))}-${doc.width}x${doc.height}.${fmt}`);
      toast(`Exported ${doc.width}×${doc.height} ${fmt.toUpperCase()}`);
    } catch (e) { toast((e as Error).message, "err"); }
    finally { setBusy(false); }
  };

  const setPreset = (id: string) => {
    const p = SIZE_PRESETS.find((x) => x.id === id);
    setDoc((d) => p ? { ...d, preset: id, width: p.w, height: p.h } : { ...d, preset: "custom" });
  };
  const patch = (p: Partial<CoverDoc>) => setDoc((d) => ({ ...d, ...p }));
  const patchPill = (p: Partial<CoverDoc["pill"]>) => setDoc((d) => ({ ...d, pill: { ...d.pill, ...p } }));
  const setLine = (i: number, p: Partial<CoverDoc["lines"][number]>) => setDoc((d) => ({ ...d, lines: d.lines.map((l, j) => j === i ? { ...l, ...p } : l) }));
  const fontValue = `${doc.font}|${doc.weight}`;
  const frameNo = Math.round(time * fps);
  useEffect(() => {
    if (!clean || !cleanDir || !projectId) { setStill(null); return; }
    let live = true;
    const t = setTimeout(() => {
      loadImage(fileUrl(projectId, cleanFramePath(cleanDir, frameNo)))
        .then((im) => { if (live) setStill(im); })
        .catch(() => { if (live) setStill(null); }); // past the rendered frames (the end card): use the video
    }, 60);
    return () => { live = false; clearTimeout(t); };
  }, [clean, cleanDir, projectId, frameNo]);
  const totalFrames = Math.max(1, Math.round(duration * fps));

  const projectOptions = useMemo(() => [{ value: "", label: "Open a rendered project…" },
    ...projects.map((p) => ({ value: p.id, label: p.name }))], [projects]);

  return (
    <div className="page">
      <div className="page-inner tg">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Thumbnail Generator</h1>
            <div className="muted">Pick any frame of a video, set the headline, and export a cover at the exact size.</div></div>
          <Select value={projectId ?? ""} options={projectOptions} ariaLabel="Open a rendered project"
            onChange={(v) => setParams(v ? { project: v } : {})} />
          <button className="btn" onClick={() => fileInput.current?.click()}><FileVideo size={14} />Import video</button>
          <input ref={fileInput} type="file" accept="video/*" hidden onChange={(e) => { openFile(e.target.files?.[0]); e.target.value = ""; }} />
        </div>

        <div className="tg-layout">
          <div className="tg-main">
            <div className="tg-stage" ref={stageRef}
              onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); openFile(e.dataTransfer.files[0]); }}>
              {video ? (
                <canvas ref={canvasRef} className="tg-canvas" style={{ width: view.w, height: view.h }} tabIndex={0}
                  role="img" aria-label={`Cover preview, ${doc.width} by ${doc.height}. ${doc.lines.map((l) => l.text).join(" ")}. Selected layer: ${sel}. Arrow keys move it, Shift for bigger steps.`}
                  onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp} onKeyDown={onKey} />
              ) : (
                <Empty icon={<ImageIcon size={20} />} title="No video yet"
                  action={<button className="btn btn-primary" onClick={() => fileInput.current?.click()}><FileVideo size={14} />Import video</button>}>
                  Import any video or drop it here, or open a rendered project from the menu above.
                </Empty>
              )}
              {video && <video ref={videoRef} src={video.url} className="tg-video" muted playsInline preload="auto" crossOrigin="anonymous"
                onLoadedMetadata={(e) => { setDuration(e.currentTarget.duration || 0); if (pendingSeek.current != null) { e.currentTarget.currentTime = pendingSeek.current; pendingSeek.current = null; } }}
                onLoadedData={() => setTick((t) => t + 1)}
                onSeeked={(e) => { setTime(e.currentTarget.currentTime); setTick((t) => t + 1); }} />}
            </div>

            {video && (
              <div className="tg-scrub">
                <button className="icon-btn sm bordered" aria-label="Previous frame (,)" onClick={() => step(-1)}><ChevronLeft size={14} /></button>
                <input className="range grow" type="range" min={0} max={totalFrames} step={1} value={frameNo} aria-label="Frame"
                  aria-valuetext={`Frame ${frameNo} of ${totalFrames}, ${fmtTime(time)}`}
                  style={{ ["--fill" as string]: `${(frameNo / totalFrames) * 100}%` }}
                  onChange={(e) => { const f = Number(e.target.value); setTime(f / fps); seek(f / fps); }} />
                <button className="icon-btn sm bordered" aria-label="Next frame (.)" onClick={() => step(1)}><ChevronRight size={14} /></button>
                <span className="mono meta tg-tc">{fmtTime(time)} · f{frameNo}</span>
              </div>
            )}
            {cleanDir && (
              <label className="row tg-clean">
                <Switch checked={clean} onChange={setClean} label="Use the clean rendered frame" />
                <span className="meta">Clean frame: no burned-in captions (before the final grade)</span>
              </label>
            )}
            {video && <div className="meta tg-hint">Drag the text or the picture to move it. Click the canvas, then use the arrow keys (Shift for bigger steps). <span className="kbd">,</span> <span className="kbd">.</span> step a frame.</div>}

            {draftErr && <Callout tone="warn">No drafted cover for this project: {draftErr}</Callout>}
            {draft && draft.variants.length > 0 && (
              <div className="tg-variants">
                <div className="label row"><Sparkles size={13} />Drafted from the script</div>
                <div className="tg-variant-row">
                  {draft.variants.map((v, i) => (
                    <button key={i} className="chip tg-variant" aria-label={`Use variant ${v.headline.join(" ")} at ${fmtTime(v.time)}`} onClick={() => { setDoc((d) => applyVariant(d, v)); seek(v.time); }}>
                      <span className="tg-v1">{v.headline[0]}</span> <span className="tg-v2">{v.headline.slice(1).join(" ")}</span>
                      <span className="meta">{fmtTime(v.time)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <aside className="tg-inspector" aria-label="Cover settings">
            <Section title="Size">
              <FieldRow label="Preset">
                <Select value={doc.preset} onChange={setPreset}
                  options={[...SIZE_PRESETS.map((p) => ({ value: p.id as string, label: `${p.label} · ${p.w}×${p.h}` })), { value: "custom", label: "Custom size" }]} />
              </FieldRow>
              {doc.preset === "custom" && (
                <FieldRow label="Width × height">
                  <div className="row" style={{ gap: 6 }}>
                    <input className="input sm tg-num" type="number" min={64} max={8000} value={doc.width} aria-label="Width in pixels"
                      onChange={(e) => patch({ width: Math.min(8000, Math.max(64, Number(e.target.value) || 64)) })} />
                    <span className="meta">×</span>
                    <input className="input sm tg-num" type="number" min={64} max={8000} value={doc.height} aria-label="Height in pixels"
                      onChange={(e) => patch({ height: Math.min(8000, Math.max(64, Number(e.target.value) || 64)) })} />
                  </div>
                </FieldRow>
              )}
              <FieldRow label="Safe zone">
                <Segmented value={safe} onChange={setSafe} size="sm"
                  options={(Object.keys(SAFE_ZONES) as SafeZone[]).map((k) => ({ value: k, label: SAFE_ZONES[k].label }))} />
              </FieldRow>
            </Section>

            <Section title="Headline">
              {doc.lines.map((l, i) => (
                <FieldRow key={i} label={`Line ${i + 1}`}>
                  <div className="row" style={{ gap: 6 }}>
                    <input className="input sm grow" value={l.text} aria-label={`Headline line ${i + 1}`} onChange={(e) => setLine(i, { text: e.target.value })} />
                    <ColorInput value={l.color} label={`Line ${i + 1} colour`} onChange={(c) => setLine(i, { color: c })} />
                  </div>
                </FieldRow>
              ))}
              <FieldRow label="Font">
                <Select value={fontValue} onChange={(v) => { const [font, w] = v.split("|"); patch({ font, weight: Number(w) }); }}
                  options={FONTS.map((f) => ({ value: `${f.family}|${f.weight}`, label: f.label }))} />
              </FieldRow>
              <FieldRow label="Size"><Slider value={doc.size} min={0.04} max={0.3} step={0.005} onChange={(v) => patch({ size: v })} ariaLabel="Headline size" format={(v) => `${Math.round(v * Math.min(doc.width, doc.height))}`} /></FieldRow>
              <FieldRow label="Letter spacing"><Slider value={doc.tracking} min={-0.1} max={0.2} step={0.005} onChange={(v) => patch({ tracking: v })} ariaLabel="Letter spacing" format={(v) => v.toFixed(2)} /></FieldRow>
              <FieldRow label="Line spacing"><Slider value={doc.leading} min={0.7} max={1.6} step={0.01} onChange={(v) => patch({ leading: v })} ariaLabel="Line spacing" format={(v) => v.toFixed(2)} /></FieldRow>
            </Section>

            <Section title="Caption pill">
              <FieldRow label="Show"><Switch checked={doc.pill.on} onChange={(on) => patchPill({ on })} label="Show caption pill" /></FieldRow>
              <FieldRow label="Text">
                <textarea className="textarea tg-pill-text" rows={2} value={doc.pill.text} aria-label="Caption text" disabled={!doc.pill.on}
                  onChange={(e) => patchPill({ text: e.target.value })} />
              </FieldRow>
              <FieldRow label="Text colour"><ColorInput value={doc.pill.color} label="Caption text colour" onChange={(color) => patchPill({ color })} /></FieldRow>
              <FieldRow label="Size"><Slider value={doc.pill.size} min={0.015} max={0.07} step={0.001} onChange={(size) => patchPill({ size })} ariaLabel="Caption size" format={(v) => `${Math.round(v * Math.min(doc.width, doc.height))}`} /></FieldRow>
            </Section>

            <Section title="Position">
              <FieldRow label="Layer"><Segmented value={sel} onChange={setSel} size="sm" options={LAYERS} /></FieldRow>
              {sel === "frame" ? (
                <FieldRow label="Zoom"><Slider value={doc.zoom} min={1} max={3} step={0.01} onChange={(zoom) => patch({ zoom })} ariaLabel="Frame zoom" format={(v) => `${v.toFixed(2)}×`} /></FieldRow>
              ) : (
                <FieldRow label="Snap">
                  <div className="tg-snaps" role="group" aria-label={`Snap the ${sel === "pill" ? "caption" : "headline"}`}>
                    {SNAPS.map((s) => <button key={s} type="button" className="tg-snap" aria-label={SNAP_LABELS[s]} title={SNAP_LABELS[s]} onClick={() => snap(s)}><span /></button>)}
                  </div>
                </FieldRow>
              )}
            </Section>

            <div className="tg-export">
              <Segmented value={fmt} onChange={setFmt} ariaLabel="File format" options={[{ value: "png", label: "PNG" }, { value: "jpg", label: "JPG" }]} />
              <button className="btn btn-primary grow" disabled={!video || busy} onClick={() => void exportNow()}>
                {busy ? <Spinner /> : <Download size={14} />}Export {doc.width}×{doc.height}
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
