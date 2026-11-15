import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Music, Pause, Play, Plus, Shuffle } from "lucide-react";
import { api } from "@/lib/api";
import type { MusicConfig, MusicLibrary, MusicPick, MusicTrack } from "@/lib/types";
import { FieldRow, Segmented, Select, Slider, Switch } from "@/components/ui/Form";
import { Badge } from "@/components/ui/Feedback";
import { toast } from "@/stores/ui";
import { fmtSecs, togglePreview, topMood, usePlaying } from "./preview";
import "./music.css";

const label = (t: MusicTrack) => `${t.viral ? "Viral · " : t.source === "mine" ? "Yours · " : `${topMood(t.moods)} · `}${t.title}`;

/** The Shots-AV Sound section's music controls: Auto (picked from the script) / a chosen track / off. */
export function MusicPanel({ projectId, config, scriptKey, ownFile, onChange }: {
  projectId: string; config: MusicConfig | undefined; scriptKey: string; ownFile: string | null;
  onChange: (patch: MusicConfig) => void;
}) {
  const cfg: MusicConfig = { mode: "none", volume: 0.5, duck: true, ...(config ?? {}) };
  const [lib, setLib] = useState<MusicLibrary | null>(null);
  const [pick, setPick] = useState<MusicPick | null>(null);
  const [busy, setBusy] = useState(false);
  const playing = usePlaying();
  const fileRef = useRef<HTMLInputElement>(null);

  const loadLib = useCallback(() => api.music().then(setLib).catch(() => setLib(null)), []);
  useEffect(() => { void loadLib(); }, [loadLib]);
  // the pick reads the saved script: refresh shortly after the script or the music settings change
  useEffect(() => {
    let live = true;
    const t = setTimeout(() => api.musicPick(projectId).then((p) => { if (live) setPick(p); }).catch(() => {}), 1200);
    return () => { live = false; clearTimeout(t); };
  }, [projectId, scriptKey, cfg.mode, cfg.id, cfg.pick]);

  const tracks = useMemo(() => (lib?.tracks ?? []).filter((t) => t.available), [lib]);
  const current = cfg.mode === "track" ? tracks.find((t) => t.id === cfg.id) ?? null : cfg.mode === "auto" ? pick?.chosen ?? null : null;
  const reason = pick?.top.find((r) => r.track.id === current?.id)?.reason;

  const addSongs = async (files: FileList) => {
    setBusy(true);
    try {
      let last: MusicTrack | null = null;
      for (const f of Array.from(files)) last = await api.musicImport(f);
      toast(files.length > 1 ? `${files.length} songs added to your library` : `“${last?.title}” added to your library`);
      await loadLib();
      if (last && files.length === 1) onChange({ mode: "track", id: last.id });
    } catch (e) { toast((e as Error).message, "err"); }
    finally { setBusy(false); }
  };

  return (
    <div className="col music-panel" style={{ gap: 8 }}>
      <FieldRow label="Music">
        <Segmented ariaLabel="Music" size="sm" value={cfg.mode ?? "none"} onChange={(v) => onChange({ mode: v, ...(v === "track" && !cfg.id && current ? { id: current.id } : {}) })}
          options={[{ value: "auto", label: "Auto" }, { value: "track", label: "Pick" }, { value: "none", label: "Off" }]} />
      </FieldRow>
      {ownFile && <div className="hint">Your file <span className="mono">{ownFile}</span> in this reel's media folder is used instead. Remove it to use the library.</div>}
      {cfg.mode !== "none" && !ownFile && <>
        {cfg.mode === "track" && (
          <Select ariaLabel="Track" value={cfg.id ?? ""} onChange={(v) => onChange({ id: v })}
            options={[{ value: "", label: "Choose a track…" }, ...tracks.map((t) => ({ value: t.id, label: label(t) }))]} />
        )}
        {current ? (
          <div className="music-now">
            <button className="icon-btn sm" aria-label={playing === current.id ? "Stop preview" : "Preview"} onClick={() => togglePreview(current.id, current.start)}>
              {playing === current.id ? <Pause size={13} /> : <Play size={13} />}
            </button>
            <div className="col grow" style={{ minWidth: 0, gap: 2 }}>
              <span className="ellipsis" style={{ fontWeight: 500 }}>{current.title}</span>
              <span className="meta ellipsis">{reason ?? (current.artist || topMood(current.moods))} · from {fmtSecs(current.start)}</span>
            </div>
            {current.viral && <Badge tone="accent">Viral</Badge>}
            {current.vocals && <Badge>Vocals</Badge>}
            {cfg.mode === "auto" && (
              <button className="icon-btn sm" aria-label="Shuffle the pick" title="Next of the top 3" onClick={() => onChange({ pick: ((cfg.pick ?? 0) + 1) % 3 })}><Shuffle size={13} /></button>
            )}
          </div>
        ) : <div className="hint">{cfg.mode === "auto" ? "Picking from the script…" : "Choose a track."}</div>}
        {cfg.mode === "auto" && pick && pick.top.length > 1 && (
          <div className="row music-alts">
            {pick.top.filter((r) => r.track.id !== current?.id).map((r) => (
              <button key={r.track.id} className="chip" title={r.reason} onClick={() => onChange({ mode: "track", id: r.track.id })}>{r.track.title}</button>
            ))}
          </div>
        )}
        <FieldRow label="Volume"><Slider ariaLabel="Music volume" value={cfg.volume ?? 0.5} onChange={(v) => onChange({ volume: Math.round(v * 100) / 100 })} format={(v) => `${Math.round(v * 200)}%`} /></FieldRow>
        <FieldRow label="Duck"><Switch label="Duck under voices" checked={cfg.duck !== false} onChange={(v) => onChange({ duck: v })} /></FieldRow>
      </>}
      <div className="row" style={{ gap: 6 }}>
        <button className="btn btn-sm" disabled={busy} onClick={() => fileRef.current?.click()}><Plus size={12} />{busy ? "Adding…" : "Add songs"}</button>
        <Link className="btn btn-sm btn-ghost" to="/library?kind=music"><Music size={12} />Library</Link>
        <input ref={fileRef} type="file" multiple hidden accept=".mp3,.wav,.m4a,.flac,audio/*" onChange={(e) => { if (e.target.files?.length) void addSongs(e.target.files); e.target.value = ""; }} />
      </div>
    </div>
  );
}
