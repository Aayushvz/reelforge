// Left panel: the shot browser for generated reels, and the media bin for imported files.
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Copy, Film, Image as ImageIcon, MoreHorizontal, Music, Plus, RefreshCw, Replace, Trash2, Upload, Crosshair } from "lucide-react";
import type { Clip, EditorDoc, Performance, TrackKind } from "@/lib/types";
import * as T from "@/lib/timeline";
import { duration } from "@/lib/format";
import { environment, ENVIRONMENTS, character } from "@/data/catalog";
import { EnvThumb } from "@/components/Thumbs";
import { useMenu } from "@/components/ui/Overlay";
import { Empty, Badge } from "@/components/ui/Feedback";
import { useEditor, sortedOf, reorderShot } from "./store";
import { mediaDuration } from "./media";

const kindOf = (f: string): "video" | "audio" | "image" =>
  /\.(mp4|mov|webm)$/i.test(f) ? "video" : /\.(mp3|wav|m4a|ogg)$/i.test(f) ? "audio" : "image";

type Props = {
  editor: EditorDoc; performance: Performance | null; stills: string[]; media: string[];
  resolveSrc: (src: string) => string; onImport: (files: FileList) => Promise<string[]>; onRegenerate: () => void;
};

export function LeftPanel(props: Props) {
  const generated = props.editor.kind === "generated";
  const [tab, setTab] = useState<"shots" | "media">(generated ? "shots" : "media");
  return (
    <div className="lp">
      <div className="lp-tabs" role="tablist">
        {generated && <button role="tab" className="tab" aria-selected={tab === "shots"} onClick={() => setTab("shots")}>Shots</button>}
        <button role="tab" className="tab" aria-selected={tab === "media"} onClick={() => setTab("media")}>Media{props.media.length > 0 && <span className="count">{props.media.length}</span>}</button>
      </div>
      {tab === "shots" && generated ? <ShotList {...props} /> : <MediaBin {...props} />}
    </div>
  );
}

function ShotList({ editor, performance, stills, resolveSrc, onImport, onRegenerate }: Props) {
  const tl = useEditor((s) => s.tl)!;
  const selection = useEditor((s) => s.selection);
  const playhead = useEditor((s) => s.playhead);
  const { edit, select, seek } = useEditor.getState();
  const menu = useMenu();
  const replaceFor = useRef<Clip | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const shots = useMemo(() => sortedOf(tl, "shots"), [tl]);
  const dialogue = useMemo(() => sortedOf(tl, "dialogue"), [tl]);
  const env = environment(editor.environment.id) ?? ENVIRONMENTS[0];
  const preset = env.presets.find((p) => p.id === editor.environment.lighting) ?? env.presets[0];

  const replace = async (files: FileList) => {
    const shot = replaceFor.current;
    if (!shot) return;
    const [path] = await onImport(files);
    if (!path) return;
    const kind = kindOf(path);
    edit((t) => {
      let next = t;
      let track = next.tracks.find((x) => x.kind === "video" && !x.locked);
      if (!track) { next = T.addTrack(next, "video"); track = next.tracks.find((x) => x.kind === "video")!; }
      const clip: Clip = { id: `c${Date.now().toString(36)}`, trackId: track.id, start: shot.start, duration: shot.duration, label: path.split("/").pop()!, src: path, offset: 0, volume: kind === "video" ? 1 : undefined };
      return { ...next, clips: [...next.clips, clip] };
    });
  };

  if (!shots.length) return <Empty icon={<Film size={16} />} title="No shots yet">Write a script on Create. Shots are laid out from its lines.</Empty>;

  return (
    <div className="lp-scroll">
      {shots.map((s, i) => {
        const still = stills.find((f) => f === `shot_${String(i).padStart(2, "0")}.png`);
        const line = dialogue.find((d) => d.start < T.clipEnd(s) && T.clipEnd(d) > s.start);
        const lineText = performance?.lines.find((l) => l.id === line?.lineId)?.text ?? line?.text;
        const ch = character(editor.cast[s.subject ?? ""]?.characterId);
        const active = playhead >= s.start && playhead < T.clipEnd(s);
        return (
          <div key={s.id} className={`shot${selection.includes(s.id) ? " sel" : ""}${active ? " active" : ""}`} role="button" tabIndex={0}
            onClick={() => { select([s.id]); seek(s.start); }} onKeyDown={(e) => e.key === "Enter" && (select([s.id]), seek(s.start))}>
            <div className="shot-thumb">
              {still ? <img src={resolveSrc(`out/stills/${still}`)} alt="" /> : <EnvThumb env={env} preset={preset} />}
              <span className="shot-no mono">{String(i + 1).padStart(2, "0")}</span>
            </div>
            <div className="col grow" style={{ gap: 2, minWidth: 0 }}>
              <div className="row" style={{ gap: 6 }}>
                <span className="h3">{s.shotKind === "closeup" ? "Close-up" : s.shotKind === "wide" ? "Wide" : "Medium"}</span>
                <span className="meta mono">{s.lens}mm</span>
                <span className="meta mono" style={{ marginLeft: "auto" }}>{duration(s.duration)}</span>
              </div>
              <span className="meta ellipsis">{lineText ? lineText.replace(/\[[^\]]*\]\s*/g, "") : "No dialogue"}</span>
              <div className="row" style={{ gap: 4 }}>
                <span className="meta mono">{s.subject}{ch ? ` · ${ch.name}` : ""}</span>
                <span style={{ marginLeft: "auto" }}>{still ? <Badge tone="ok">Still</Badge> : <Badge>{s.status === "planned" ? "Planned" : "Estimated"}</Badge>}</span>
              </div>
            </div>
            <button className="icon-btn xs shot-more" aria-label="Shot actions" onClick={(e) => { e.stopPropagation(); menu.openAt(e.currentTarget.getBoundingClientRect(), [
              { label: "Go to shot", icon: <Crosshair size={14} />, onSelect: () => seek(s.start) },
              { label: "Regenerate stills", icon: <RefreshCw size={14} />, onSelect: onRegenerate },
              { label: "Replace with media…", icon: <Replace size={14} />, onSelect: () => { replaceFor.current = s; fileRef.current?.click(); } },
              { label: "Duplicate", icon: <Copy size={14} />, onSelect: () => { const r = T.duplicateClips(tl, [s.id]); edit(() => r.tl); } },
              { label: "Move earlier", icon: <ArrowUp size={14} />, disabled: i === 0, onSelect: () => edit((t) => reorderShot(t, s.id, -1)) },
              { label: "Move later", icon: <ArrowDown size={14} />, disabled: i === shots.length - 1, onSelect: () => edit((t) => reorderShot(t, s.id, 1)) },
              { separator: true },
              { label: "Delete shot", icon: <Trash2 size={14} />, danger: true, onSelect: () => { edit((t) => T.removeClips(t, [s.id])); select([]); } },
            ], "end"); }}><MoreHorizontal size={13} /></button>
          </div>
        );
      })}
      <input ref={fileRef} type="file" accept="video/*,image/*" hidden onChange={(e) => { if (e.target.files?.length) void replace(e.target.files); e.target.value = ""; }} />
      {menu.node}
    </div>
  );
}

function MediaBin({ media, resolveSrc, onImport }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const durs = useMediaDurations(media, resolveSrc);
  const { edit, select } = useEditor.getState();

  const importFiles = async (files: FileList) => { setBusy(true); try { await onImport(files); } finally { setBusy(false); } };

  const addAtPlayhead = (path: string) => {
    const kind = kindOf(path);
    const want: TrackKind[] = kind === "audio" ? ["audio", "music", "sfx"] : ["video"];
    const at = useEditor.getState().playhead;
    edit((t) => {
      let next = t;
      let track = next.tracks.find((x) => want.includes(x.kind) && !x.locked);
      if (!track) { next = T.addTrack(next, want[0]); track = next.tracks.find((x) => x.kind === want[0])!; }
      const clip: Clip = { id: `c${Date.now().toString(36)}`, trackId: track.id, start: at, duration: durs[path] || 5, label: path.split("/").pop()!, src: path, offset: 0, volume: 1 };
      select([clip.id]);
      return T.updateClip({ ...next, clips: [...next.clips, clip] }, clip.id, {});
    });
  };

  return (
    <div className={`lp-scroll media${drag ? " drag" : ""}`}
      onDragOver={(e) => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); setDrag(true); } }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files.length) void importFiles(e.dataTransfer.files); }}>
      <button className="btn btn-sm" style={{ width: "100%" }} disabled={busy} onClick={() => fileRef.current?.click()}><Upload size={14} />{busy ? "Importing…" : "Import media"}</button>
      {media.length === 0 ? (
        <div className="media-empty"><Upload size={16} className="faint" /><span className="meta">Drop video, audio or images here. Files are copied into the project's media folder.</span></div>
      ) : (
        <div className="media-grid">
          {media.map((m) => {
            const path = `media/${m}`;
            const kind = kindOf(m);
            return (
              <div key={m} className="media-item" draggable title="Drag onto the timeline, or double-click to add at the playhead"
                role="button" tabIndex={0} aria-label={`${m}: add at the playhead`}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); addAtPlayhead(path); } }}
                onDragStart={(e) => e.dataTransfer.setData("application/x-reelforge-media", JSON.stringify({ path, kind, duration: durs[path] ?? 5, name: m }))}
                onDoubleClick={() => addAtPlayhead(path)}>
                <div className="media-thumb">
                  {kind === "video" ? <video src={resolveSrc(path)} muted preload="metadata" /> : kind === "image" ? <img src={resolveSrc(path)} alt="" /> : <Music size={18} className="faint" />}
                  <span className="media-kind">{kind === "video" ? <Film size={11} /> : kind === "audio" ? <Music size={11} /> : <ImageIcon size={11} />}{durs[path] ? duration(durs[path]) : ""}</span>
                </div>
                <div className="row" style={{ gap: 4 }}><span className="meta ellipsis grow">{m}</span>
                  <button className="icon-btn xs" aria-label={`Add ${m} at playhead`} onClick={() => addAtPlayhead(path)}><Plus size={12} /></button></div>
              </div>
            );
          })}
        </div>
      )}
      <input ref={fileRef} type="file" multiple accept="video/*,audio/*,image/*" hidden onChange={(e) => { if (e.target.files?.length) void importFiles(e.target.files); e.target.value = ""; }} />
    </div>
  );
}

function useMediaDurations(media: string[], resolve: (s: string) => string) {
  const [d, setD] = useState<Record<string, number>>({});
  useEffect(() => {
    let live = true;
    for (const m of media) {
      const path = `media/${m}`;
      const k = kindOf(m);
      if (k === "image") { setD((x) => ({ ...x, [path]: 5 })); continue; }
      void mediaDuration(resolve(path), k).then((v) => live && setD((x) => ({ ...x, [path]: v })));
    }
    return () => { live = false; };
  }, [media, resolve]);
  return d;
}
