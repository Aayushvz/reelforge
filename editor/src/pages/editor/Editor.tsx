// The editing workspace. Same editor for generated reels, imported media and blank projects.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Undo2, Redo2, PanelLeft, PanelRight, Keyboard, Upload, Clapperboard, LayoutTemplate, Maximize2, RotateCcw, Minimize2,
} from "lucide-react";
import { useProject } from "@/stores/project";
import { useUI, toast } from "@/stores/ui";
import { api, fileUrl } from "@/lib/api";
import type { Performance, ProjectFiles, Ratio, Timeline as TL, EditorDoc } from "@/lib/types";
import { RATIOS } from "@/lib/types";
import * as T from "@/lib/timeline";
import { LogoMark } from "@/components/Sidebar";
import { SaveStatus } from "@/components/SaveStatus";
import { IconButton, Select } from "@/components/ui/Form";
import { useMenu } from "@/components/ui/Overlay";
import { Callout, Spinner } from "@/components/ui/Feedback";
import { useEditor } from "./store";
import { mediaDuration, useAudioSync, usePlaybackClock } from "./media";
import { Timeline } from "./Timeline";
import { Preview } from "./Preview";
import { Inspector } from "./Inspector";
import { LeftPanel } from "./LeftPanel";
import "./editor.css";

export async function buildTimeline(id: string, perf: Performance | null, files: ProjectFiles, ed: EditorDoc): Promise<TL> {
  if (!perf || !perf.lines.length) return T.blankTimeline();
  const durs: Record<string, number> = {};
  // each line's take: the imported mp3, else the generated ElevenLabs take
  const srcs: Record<string, string> = {};
  const voices = await api.voices(id).catch(() => []);
  for (const v of voices) if (v.file) srcs[v.line] = v.file;
  for (const l of perf.lines) if (!srcs[l.id] && files.audio.includes(`${l.id}.mp3`)) srcs[l.id] = `out/audio/${l.id}.mp3`;
  await Promise.all(perf.lines.filter((l) => srcs[l.id]).map(async (l) => {
    const d = await mediaDuration(fileUrl(id, srcs[l.id]));
    if (d > 0) durs[l.id] = d;
  }));
  let plan: Parameters<typeof T.buildFromScript>[3];
  if (files.renderPlan) {
    try { plan = await (await fetch(fileUrl(id, "out/render_plan.json"))).json(); } catch { plan = undefined; }
  }
  const tl = T.buildFromScript(perf, durs, ed.subtitles.wordsPerLine, plan, srcs);
  const final = files.finals[0];
  if (final) {
    const d = await mediaDuration(fileUrl(id, `out/${final}`), "video");
    const track = { id: "render", kind: "video" as const, name: "Final render", muted: false, locked: false, hidden: false };
    // the render already contains the dialogue mix, so the separate dialogue track starts muted
    return {
      ...tl, duration: Math.max(tl.duration, d),
      tracks: [track, ...tl.tracks.map((t) => (t.kind === "dialogue" ? { ...t, muted: true } : t))],
      clips: [...tl.clips, { id: "final", trackId: "render", start: 0, duration: d || tl.duration, label: final, src: `out/${final}`, offset: 0, volume: 1, status: "rendered" }],
    };
  }
  return tl;
}

export function EditorPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const project = useProject();
  const { performance, editor, files, loading, error } = project;
  const tl = useEditor((s) => s.tl);
  const layout = useEditor((s) => s.layout);
  const canUndo = useEditor((s) => s.past.length > 0);
  const canRedo = useEditor((s) => s.future.length > 0);
  const { init, undo, redo, setLayout, resetLayout } = useEditor.getState();
  const [ready, setReady] = useState(false);
  const menu = useMenu();
  const layoutBtn = useRef<HTMLButtonElement>(null);

  useEffect(() => { setReady(false); void project.load(id); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Build or restore the timeline once the project is loaded.
  useEffect(() => {
    if (loading || error || useProject.getState().id !== id) return;
    let live = true;
    const saved = editor.timeline;
    const go = saved ? Promise.resolve(saved) : buildTimeline(id, performance, files, editor);
    void go.then((t) => { if (live) { init(t); setReady(true); } });
    return () => { live = false; };
  }, [loading, error, id]); // eslint-disable-line react-hooks/exhaustive-deps

  const resolveSrc = useCallback((src: string) => fileUrl(id, src), [id]);
  usePlaybackClock();
  useAudioSync(tl, resolveSrc, editor.audio.dialogueVolume);
  useEffect(() => () => useEditor.getState().setPlaying(false), []);

  const rebuild = async () => {
    const fresh = await buildTimeline(id, performance, files, editor);
    useEditor.getState().edit(() => fresh);
    toast("Timeline rebuilt from the script");
  };

  const importMedia = async (list: FileList): Promise<string[]> => {
    const done: string[] = [];
    for (const f of Array.from(list)) {
      const safe = f.name.replace(/[^\w.\- ]+/g, "_");
      try { await api.upload(id, `media/${safe}`, f); done.push(`media/${safe}`); }
      catch (e) { toast(`${f.name}: ${(e as Error).message}`, "err"); }
    }
    if (done.length) { await project.reloadFiles(); toast(`${done.length} file${done.length > 1 ? "s" : ""} imported`); }
    return done;
  };

  const regenerate = async () => {
    const pid = await project.saveNow();
    if (pid) nav(`/projects/${encodeURIComponent(pid)}/render?start=stills`);
  };

  const setRatio = (ratio: Ratio) => {
    project.setEditor((e) => ({ ...e, output: { ...e.output, ratio, resolution: [...RATIOS[ratio]] as [number, number] } }));
    if (performance) project.setPerformance((p) => ({ ...p, ratio }));
  };

  useEditorKeys(editor.output.fps);

  if (error) return <div className="page" style={{ padding: 32 }}><Callout tone="err">Couldn't open this project: {error}. <Link to="/editor" className="btn btn-sm" style={{ marginLeft: 8 }}>Back to editor home</Link></Callout></div>;
  if (!ready || !tl) return <div className="ed-loading"><Spinner /><span className="muted">Preparing the timeline…</span></div>;

  const max = layout.maximized;
  const fps = editor.output.fps || 30;
  return (
    <div className="ed">
      <h1 className="sr-only">{editor.name}: timeline editor</h1>
      <header className="ed-bar">
        <IconButton label="Back" onClick={() => nav(editor.kind === "generated" ? `/?p=${encodeURIComponent(id)}` : "/editor")}><ArrowLeft size={16} /></IconButton>
        <span className="logo" style={{ gap: 8 }}><LogoMark /></span>
        <input className="ed-title" value={editor.name} aria-label="Project name" onChange={(e) => project.setEditor((x) => ({ ...x, name: e.target.value }))} />
        <SaveStatus />
        <span className="vdivider" style={{ margin: "10px 6px" }} />
        <IconButton label="Undo" kbd="Ctrl Z" disabled={!canUndo} onClick={undo}><Undo2 size={16} /></IconButton>
        <IconButton label="Redo" kbd="Ctrl Shift Z" disabled={!canRedo} onClick={redo}><Redo2 size={16} /></IconButton>
        <div className="grow" />
        <div style={{ width: 92 }}><Select size="sm" ariaLabel="Aspect ratio" value={editor.output.ratio} onChange={setRatio} options={(Object.keys(RATIOS) as Ratio[]).map((r) => ({ value: r, label: r }))} /></div>
        <IconButton label={layout.leftOpen ? "Hide left panel" : "Show left panel"} on={layout.leftOpen && !max} onClick={() => setLayout({ leftOpen: !layout.leftOpen, maximized: false })}><PanelLeft size={16} /></IconButton>
        <IconButton label={layout.rightOpen ? "Hide inspector" : "Show inspector"} on={layout.rightOpen && !max} onClick={() => setLayout({ rightOpen: !layout.rightOpen, maximized: false })}><PanelRight size={16} /></IconButton>
        <button ref={layoutBtn} className="icon-btn" aria-label="Layout" onClick={() => menu.openAt(layoutBtn.current!.getBoundingClientRect(), [
          { label: max ? "Restore panels" : "Maximise preview", icon: max ? <Minimize2 size={14} /> : <Maximize2 size={14} />, kbd: "F", onSelect: () => setLayout({ maximized: !max }) },
          { label: "Taller timeline", icon: <LayoutTemplate size={14} />, onSelect: () => setLayout({ timeline: Math.min(innerHeight * 0.6, layout.timeline + 80) }) },
          { label: "Shorter timeline", icon: <LayoutTemplate size={14} />, onSelect: () => setLayout({ timeline: Math.max(160, layout.timeline - 80) }) },
          { separator: true },
          { label: "Restore default layout", icon: <RotateCcw size={14} />, onSelect: resetLayout },
        ], "end")}><LayoutTemplate size={16} /></button>
        <IconButton label="Keyboard shortcuts" kbd="?" onClick={() => useUI.getState().setShortcutsOpen(true)}><Keyboard size={16} /></IconButton>
        <span className="vdivider" style={{ margin: "10px 6px" }} />
        {editor.kind === "generated" && <button className="btn btn-sm" onClick={() => void regenerate()}><Clapperboard size={14} />Render</button>}
        <button className="btn btn-sm btn-primary" onClick={async () => { const pid = await project.saveNow(); if (pid) nav(`/projects/${encodeURIComponent(pid)}/export`); }}><Upload size={14} />Export</button>
      </header>

      <div className="ed-work" style={{ gridTemplateColumns: `${layout.leftOpen && !max ? `${layout.left}px 1px` : ""} minmax(0, 1fr) ${layout.rightOpen && !max ? `1px ${layout.right}px` : ""}` }}>
        {layout.leftOpen && !max && <>
          <LeftPanel editor={editor} performance={performance} stills={files.stills} media={files.media} resolveSrc={resolveSrc} onImport={importMedia} onRegenerate={() => void regenerate()} />
          <Resizer axis="x" onDrag={(d) => setLayout({ left: Math.max(200, Math.min(440, layout.left + d)) })} />
        </>}
        <Preview editor={editor} stills={files.stills} resolveSrc={resolveSrc} fps={fps} punchlines={performance?.lines.filter((l) => l.punchline).map((l) => l.id) ?? []} />
        {layout.rightOpen && !max && <>
          <Resizer axis="x" onDrag={(d) => setLayout({ right: Math.max(240, Math.min(440, layout.right - d)) })} />
          <Inspector editor={editor} performance={performance} onRegenerate={() => void regenerate()} />
        </>}
      </div>
      {!max && <>
        <Resizer axis="y" onDrag={(d) => setLayout({ timeline: Math.max(140, Math.min(innerHeight - 260, layout.timeline - d)) })} />
        <div className="ed-tl" style={{ height: layout.timeline }}>
          <Timeline fps={fps} resolveSrc={resolveSrc} canRebuild={editor.kind === "generated"} onRebuild={() => void rebuild()}
            onShotAction={() => void regenerate()} />
        </div>
      </>}
      {menu.node}
    </div>
  );
}

function Resizer({ axis, onDrag }: { axis: "x" | "y"; onDrag: (delta: number) => void }) {
  const down = (e: React.PointerEvent) => {
    e.preventDefault();
    let last = axis === "x" ? e.clientX : e.clientY;
    const move = (ev: PointerEvent) => { const cur = axis === "x" ? ev.clientX : ev.clientY; onDrag(cur - last); last = cur; };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); document.body.style.cursor = ""; };
    document.body.style.cursor = axis === "x" ? "col-resize" : "row-resize";
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };
  return <div className={`resizer ${axis}`} role="separator" aria-orientation={axis === "x" ? "vertical" : "horizontal"} onPointerDown={down} />;
}

function useEditorKeys(fps: number) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement | null)?.closest?.("input, textarea, select, [contenteditable]")) return;
      const s = useEditor.getState();
      if (!s.tl) return;
      const mod = e.ctrlKey || e.metaKey;
      const k = e.key.toLowerCase();
      const shots = s.tl.clips.filter((c) => T.trackOf(s.tl!, c).kind === "shots").sort((a, b) => a.start - b.start);
      const handled = () => { e.preventDefault(); e.stopPropagation(); };
      if (k === " " ) { handled(); if (!s.playing && s.playhead >= s.tl.duration - 0.01) s.seek(0); s.setPlaying(!s.playing); }
      else if (k === "k") { handled(); s.setPlaying(false); }
      else if (k === "j") { handled(); s.seek(s.playhead - 1); }
      else if (k === "l") { handled(); s.seek(s.playhead + 1); }
      else if (k === "arrowleft") { handled(); s.seek(s.playhead - (e.shiftKey ? 1 : 1 / fps)); }
      else if (k === "arrowright") { handled(); s.seek(s.playhead + (e.shiftKey ? 1 : 1 / fps)); }
      else if (k === "home") { handled(); s.seek(0); }
      else if (k === "end") { handled(); s.seek(s.tl.duration); }
      else if (k === "arrowup") { handled(); const prev = [...shots].reverse().find((c) => c.start < s.playhead - 0.01); if (prev) { s.seek(prev.start); s.select([prev.id]); } }
      else if (k === "arrowdown") { handled(); const next = shots.find((c) => c.start > s.playhead + 0.01); if (next) { s.seek(next.start); s.select([next.id]); } }
      else if (mod && k === "z") { handled(); if (e.shiftKey) s.redo(); else s.undo(); }
      else if (mod && k === "y") { handled(); s.redo(); }
      else if (mod && k === "s") { handled(); void useProject.getState().saveNow().then((id) => id && toast("Saved")); }
      else if (mod && k === "d") { handled(); if (s.selection.length) { const r = T.duplicateClips(s.tl, s.selection); s.edit(() => r.tl); s.select(r.ids); } }
      else if (mod && k === "a") { handled(); s.select(s.tl.clips.map((c) => c.id)); }
      else if (k === "s" && !mod) { handled(); s.edit((t) => T.splitAtPlayhead(t, s.selection, s.playhead)); }
      else if ((k === "delete" || k === "backspace") && s.selection.length) { handled(); s.edit((t) => T.removeClips(t, s.selection)); s.select([]); }
      else if (k === "escape") { s.select([]); }
      else if (k === "=" || k === "+") { handled(); s.setPps(s.pps * 1.4); }
      else if (k === "-") { handled(); s.setPps(s.pps / 1.4); }
      else if (k === "0" && !mod) { handled(); window.dispatchEvent(new Event("reelforge:fit-timeline")); }
      else if (k === "n" && !mod) { handled(); s.set({ snapping: !s.snapping }); }
      else if (k === "f" && !mod) { handled(); s.setLayout({ maximized: !s.layout.maximized }); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fps]);
}
