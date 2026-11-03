// Voice studio: the voice library, speaker-to-voice casting, and per-line audio for the open project.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AudioLines, Copy, ExternalLink, Pause, Play, Upload, Search } from "lucide-react";
import { VOICES, voiceById } from "@/data/catalog";
import { useProject } from "@/stores/project";
import { api, fileUrl } from "@/lib/api";
import { stripTags } from "@/lib/script";
import { Badge, Empty } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Form";
import { toast } from "@/stores/ui";
import { usePeaks } from "./editor/media";

const recall = () => { try { return localStorage.getItem("rf.lastCreate"); } catch { return null; } };

export function VoicesPage() {
  const { id, performance, files, load, setPerformance, reloadFiles } = useProject();
  const [q, setQ] = useState("");
  useEffect(() => { const last = recall(); if (!id && last) void load(last); }, [id, load]);
  const voices = VOICES.filter((v) => (v.name + v.tags.join(" ")).toLowerCase().includes(q.toLowerCase()));
  const speakers = Object.keys(performance?.characters ?? {});
  const lines = performance?.lines ?? [];
  const cached = lines.filter((l) => files.audio.includes(`${l.id}.mp3`)).length;

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Voices</h1><div className="muted">ElevenLabs voices, who speaks with which, and the voice lines on disk.</div></div>
          <a className="btn" href="https://elevenlabs.io/app/speech-synthesis" target="_blank" rel="noreferrer"><ExternalLink size={14} />Open ElevenLabs</a>
        </div>

        <div className="voices-grid">
          <section className="col" style={{ gap: 12 }}>
            <div className="row"><h2 className="h2 grow">Library</h2><div className="search"><Search size={14} /><input className="input sm" placeholder="Search voices" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 180 }} /></div></div>
            <div className="panel" style={{ overflow: "hidden" }}>
              {voices.map((v) => (
                <div key={v.id} className="voice-row">
                  <span className="voice-icon"><AudioLines size={14} /></span>
                  <span className="col grow" style={{ gap: 0, minWidth: 0 }}><span className="h3">{v.name}</span><span className="meta ellipsis">{v.tags.join(" · ")}</span></span>
                  <button className="btn btn-sm btn-ghost mono" title="Copy voice ID" onClick={() => { void navigator.clipboard.writeText(v.id); toast("Voice ID copied"); }}><Copy size={12} />{v.id.slice(0, 8)}…</button>
                </div>
              ))}
            </div>
            <div className="hint">Previews play in ElevenLabs. ReelForge doesn't call the ElevenLabs API, so it never spends credits.</div>
          </section>

          <section className="col" style={{ gap: 12 }}>
            <div className="row"><h2 className="h2 grow">This project</h2>
              {performance && <Badge tone={cached === lines.length && lines.length ? "ok" : undefined}>{cached}/{lines.length} lines cached</Badge>}</div>
            {!performance ? (
              <Empty icon={<AudioLines size={18} />} title="No reel open" action={<Link className="btn" to="/projects">Open a project</Link>}>Open a reel to cast voices and import its lines.</Empty>
            ) : <>
              <div className="panel" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
                <span className="label">Speaker voices</span>
                {speakers.map((sp) => {
                  const v = performance.characters[sp].voice_id;
                  return (
                    <div key={sp} className="row">
                      <span className="mono" style={{ width: 72 }}>{sp}</span>
                      <Select size="sm" ariaLabel={`Voice for ${sp}`} value={voiceById(v) ? v : "custom"} onChange={(nv) => nv !== "custom" && setPerformance((p) => ({ ...p, characters: { ...p.characters, [sp]: { ...p.characters[sp], voice_id: nv } } }))}
                        options={[...VOICES.map((x) => ({ value: x.id, label: x.name })), ...(voiceById(v) ? [] : [{ value: "custom", label: `Custom ${v.slice(0, 8)}…` }])]} />
                    </div>
                  );
                })}
              </div>
              <div className="panel" style={{ overflow: "hidden" }}>
                {lines.map((l) => <LineAudio key={l.id} pid={id!} lineId={l.id} speaker={l.speaker} text={l.text} has={files.audio.includes(`${l.id}.mp3`)} onUploaded={() => void reloadFiles()} />)}
                {lines.length === 0 && <div className="meta" style={{ padding: 16 }}>The script has no lines yet.</div>}
              </div>
              <div className="hint">Generate each line in ElevenLabs with the delivery cue in brackets, download the mp3, then import it here. Imported lines are reused on every render; replace one and only that line changes.</div>
            </>}
          </section>
        </div>
      </div>
    </div>
  );
}

function LineAudio({ pid, lineId, speaker, text, has, onUploaded }: { pid: string; lineId: string; speaker: string; text: string; has: boolean; onUploaded: () => void }) {
  const [playing, setPlaying] = useState(false);
  const [v, setV] = useState(0);
  const audio = useRef<HTMLAudioElement | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const src = has ? fileUrl(pid, `out/audio/${lineId}.mp3`, v) : undefined;
  const peaks = usePeaks(src);
  const cue = text.match(/\[([^\]]+)\]/g)?.map((c) => c.slice(1, -1)) ?? [];
  const toggle = () => {
    if (!src) return;
    if (!audio.current) { audio.current = new Audio(src); audio.current.onended = () => setPlaying(false); }
    if (playing) { audio.current.pause(); setPlaying(false); } else { void audio.current.play(); setPlaying(true); }
  };
  const upload = async (f: File) => {
    try { await api.upload(pid, `out/audio/${lineId}.mp3`, f); audio.current = null; setV(Date.now()); onUploaded(); toast(`${lineId} imported`); }
    catch (e) { toast((e as Error).message, "err"); }
  };
  return (
    <div className="line-audio">
      <button className="icon-btn sm bordered" disabled={!has} aria-label={playing ? "Pause" : "Play"} onClick={toggle}>{playing ? <Pause size={14} /> : <Play size={14} />}</button>
      <div className="col grow" style={{ gap: 4, minWidth: 0 }}>
        <div className="row" style={{ gap: 6 }}><span className="mono meta">{lineId} · {speaker}</span>{cue.map((c) => <Badge key={c}>{c}</Badge>)}</div>
        <span className="ellipsis">{stripTags(text) || <span className="faint">Empty line</span>}</span>
        {peaks && <svg className="mini-wave" viewBox={`0 0 ${peaks.data.length} 20`} preserveAspectRatio="none">{Array.from(peaks.data).filter((_, i) => i % 2 === 0).map((p, i) => <rect key={i} x={i * 2} y={10 - p * 9} width="1.2" height={Math.max(0.5, p * 18)} />)}</svg>}
      </div>
      {has ? <Badge tone="ok">Cached</Badge> : <Badge>Missing</Badge>}
      <button className="btn btn-sm" onClick={() => input.current?.click()}><Upload size={12} />{has ? "Replace" : "Import mp3"}</button>
      <input ref={input} type="file" accept="audio/mpeg,.mp3" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ""; }} />
    </div>
  );
}
