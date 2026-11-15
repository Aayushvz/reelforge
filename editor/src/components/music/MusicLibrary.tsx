import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, Pause, Play, Plus, Trash2, Upload } from "lucide-react";
import { api } from "@/lib/api";
import type { MusicLibrary as Lib, MusicSlot, MusicTrack } from "@/lib/types";
import { Badge, Callout, Spinner } from "@/components/ui/Feedback";
import { Switch } from "@/components/ui/Form";
import { toast } from "@/stores/ui";
import { fmtSecs, togglePreview, topMood, usePlaying } from "./preview";
import "./music.css";

/** The Library page's Music tab: Viral now slots, your tracks (editable), and the built-in pack. */
export function MusicLibrary({ query }: { query: string }) {
  const [lib, setLib] = useState<Lib | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [genre, setGenre] = useState<string>("all");
  const [busy, setBusy] = useState<string | null>(null);
  const load = useCallback(() => api.music().then((l) => { setLib(l); setErr(null); }).catch((e) => setErr((e as Error).message)), []);
  useEffect(() => { void load(); }, [load]);

  const q = query.trim().toLowerCase();
  const match = (t: { title: string; artist: string }) => !q || `${t.title} ${t.artist}`.toLowerCase().includes(q);
  const mine = useMemo(() => (lib?.tracks ?? []).filter((t) => t.source === "mine" && !t.viral && match(t)), [lib, q]);
  const builtin = useMemo(() => (lib?.tracks ?? []).filter((t) => t.source !== "mine" && match(t) && (genre === "all" || (t.moods[genre] ?? 0) >= 0.5)), [lib, q, genre]);
  const viralTracks = useMemo(() => new Map((lib?.tracks ?? []).filter((t) => t.viral).map((t) => [t.id, t])), [lib]);

  const importFiles = async (files: FileList | File[], viral?: string) => {
    setBusy(viral ?? "mine");
    try {
      for (const f of Array.from(files)) await api.musicImport(f, viral ? { viral } : {});
      toast(viral ? "Song attached: it can now be picked for reels" : `${Array.from(files).length} added to your tracks`);
      await load();
    } catch (e) { toast((e as Error).message, "err"); }
    finally { setBusy(null); }
  };

  if (err) return <Callout tone="err">Couldn't load the music library: {err}</Callout>;
  if (!lib) return <div className="row" style={{ gap: 8 }}><Spinner /><span className="muted">Loading music…</span></div>;
  return (
    <div className="col music-lib" style={{ gap: 20 }}>
      <section className="col" style={{ gap: 8 }}>
        <div className="row"><h2 className="h3 grow">Viral now</h2><span className="meta">Trending sounds. Attach the song file and auto-pick can use it.</span></div>
        <div className="music-list">
          {lib.trending.filter(match).map((s) => <SlotRow key={s.id} slot={s} track={viralTracks.get(s.id)} busy={busy === s.id}
            onFile={(f) => void importFiles([f], s.id)} onChanged={load} />)}
        </div>
      </section>

      <section className="col" style={{ gap: 8 }}>
        <div className="row"><h2 className="h3 grow">Your tracks</h2><AddButton busy={busy === "mine"} onFiles={(f) => void importFiles(f)} /></div>
        {mine.length === 0 ? <div className="hint">Add mp3, wav, m4a or flac files. Songs with vocals are fine: they sit lower and dip further under the voices.</div> : (
          <div className="music-list">{mine.map((t) => <TrackRow key={t.id} t={t} genres={lib.genres} editable onChanged={load} />)}</div>
        )}
      </section>

      <section className="col" style={{ gap: 8 }}>
        <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
          <h2 className="h3 grow">Built-in</h2>
          {["all", ...lib.genres].map((g) => <button key={g} className="chip" aria-pressed={genre === g} onClick={() => setGenre(g)}>{g}</button>)}
        </div>
        <div className="music-list">{builtin.map((t) => <TrackRow key={t.id} t={t} genres={lib.genres} onChanged={load} />)}</div>
        {builtin.some((t) => !t.available) && <div className="hint">Some built-in tracks aren't downloaded on this machine: run <span className="mono">reelforge music fetch</span>.</div>}
      </section>
    </div>
  );
}

function AddButton({ busy, onFiles }: { busy: boolean; onFiles: (f: FileList) => void }) {
  const ref = useRef<HTMLInputElement>(null);
  return <>
    <button className="btn btn-sm" disabled={busy} onClick={() => ref.current?.click()}><Plus size={12} />{busy ? "Adding…" : "Add tracks"}</button>
    <input ref={ref} type="file" multiple hidden accept=".mp3,.wav,.m4a,.flac,audio/*" onChange={(e) => { if (e.target.files?.length) onFiles(e.target.files); e.target.value = ""; }} />
  </>;
}

function PlayButton({ t }: { t: MusicTrack }) {
  const playing = usePlaying();
  return (
    <button className="icon-btn sm" disabled={!t.available} aria-label={playing === t.id ? `Stop ${t.title}` : `Play ${t.title}`} onClick={() => togglePreview(t.id, t.start)}>
      {playing === t.id ? <Pause size={13} /> : <Play size={13} />}
    </button>
  );
}

function TrackRow({ t, genres, editable, onChanged }: { t: MusicTrack; genres: string[]; editable?: boolean; onChanged: () => void }) {
  const patch = async (p: Parameters<typeof api.musicUpdate>[1]) => {
    try { await api.musicUpdate(t.id, p); onChanged(); } catch (e) { toast((e as Error).message, "err"); }
  };
  const toggleMood = (g: string) => {
    const m = { ...t.moods };
    if (m[g]) delete m[g]; else m[g] = 1;
    if (Object.keys(m).length) void patch({ moods: m });
  };
  return (
    <div className="music-row">
      <PlayButton t={t} />
      <div className="col grow" style={{ minWidth: 0, gap: 2 }}>
        <span className="ellipsis" style={{ fontWeight: 500 }}>{t.title}</span>
        <span className="meta ellipsis">{[t.artist, fmtSecs(t.duration), `hook ${fmtSecs(t.start)}`].filter(Boolean).join(" · ")}</span>
      </div>
      {editable ? (
        <div className="row music-edit">
          <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
            {genres.map((g) => <button key={g} className="chip sm" aria-pressed={Boolean(t.moods[g])} onClick={() => toggleMood(g)}>{g}</button>)}
          </div>
          <label className="row meta" style={{ gap: 4 }}>Hook
            <input className="input sm mono" type="number" min={0} max={Math.max(0, Math.floor(t.duration) - 15)} defaultValue={Math.round(t.start)} style={{ width: 56 }}
              onBlur={(e) => { const v = Number(e.target.value); if (Number.isFinite(v) && v !== t.start) void patch({ start: Math.max(0, v) }); }} />s</label>
          <Switch label="Vocals" checked={t.vocals} onChange={(v) => void patch({ vocals: v })} />
          <button className="icon-btn sm" aria-label={`Delete ${t.title}`} onClick={() => { if (confirm(`Delete “${t.title}” from your tracks?`)) void api.musicRemove(t.id).then(onChanged).catch((e) => toast(e.message, "err")); }}><Trash2 size={13} /></button>
        </div>
      ) : (
        <div className="row" style={{ gap: 4 }}>
          {Object.entries(t.moods).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([g]) => <Badge key={g}>{g}</Badge>)}
        </div>
      )}
    </div>
  );
}

function SlotRow({ slot, track, busy, onFile, onChanged }: { slot: MusicSlot; track?: MusicTrack; busy: boolean; onFile: (f: File) => void; onChanged: () => void }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div className="music-row">
      {track ? <PlayButton t={track} /> : <span className="music-slot-dot" aria-hidden />}
      <div className="col grow" style={{ minWidth: 0, gap: 2 }}>
        <span className="ellipsis" style={{ fontWeight: 500 }}>{slot.title}{slot.artist ? <span className="muted"> · {slot.artist}</span> : null}</span>
        <span className="meta ellipsis">{slot.platform} · {slot.date} · {slot.note}</span>
      </div>
      <Badge>{topMood(slot.genres)}</Badge>
      {slot.added && track ? (
        <>
          <Badge tone="ok">Ready</Badge>
          <button className="icon-btn sm" aria-label={`Remove the file for ${slot.title}`} onClick={() => void api.musicRemove(slot.id).then(onChanged).catch((e) => toast(e.message, "err"))}><Trash2 size={13} /></button>
        </>
      ) : (
        <button className="btn btn-sm" disabled={busy} onClick={() => ref.current?.click()}><Upload size={12} />{busy ? "Adding…" : "Add file"}</button>
      )}
      {slot.source_url && <a className="icon-btn sm" href={slot.source_url} target="_blank" rel="noreferrer" aria-label="Where it's trending"><ExternalLink size={13} /></a>}
      <input ref={ref} type="file" hidden accept=".mp3,.wav,.m4a,.flac,audio/*" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
    </div>
  );
}
