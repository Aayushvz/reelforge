// Voice studio: the voice library, speaker-to-voice casting, and per-line voices for the open project.
// Lines are voiced automatically through ElevenLabs after each script save; an imported mp3 wins.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AudioLines, Copy, ExternalLink, Pause, Play, Upload, Search, RefreshCw, Wand2 } from "lucide-react";
import { VOICES, voiceById } from "@/data/catalog";
import { lineVoiced, useProject } from "@/stores/project";
import { api, fileUrl } from "@/lib/api";
import { stripTags } from "@/lib/script";
import type { VoiceLine } from "@/lib/types";
import { Badge, Empty, Spinner } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Form";
import { toast } from "@/stores/ui";
import { usePeaks } from "./editor/media";

const recall = () => { try { return localStorage.getItem("rf.lastCreate"); } catch { return null; } };

export function VoicesPage() {
  const { id, performance, load, setPerformance, reloadFiles, voices, voiceNotice, generateVoices, refreshVoices } = useProject();
  const [q, setQ] = useState("");
  useEffect(() => { const last = recall(); if (!id && last) void load(last); }, [id, load]);
  useEffect(() => { if (id) void refreshVoices(); }, [id, refreshVoices]);
  const list = VOICES.filter((v) => (v.name + v.tags.join(" ")).toLowerCase().includes(q.toLowerCase()));
  const speakers = Object.keys(performance?.characters ?? {});
  const lines = performance?.lines ?? [];
  const voiced = lines.filter((l) => lineVoiced(voices[l.id])).length;
  const pending = lines.filter((l) => !lineVoiced(voices[l.id]) && voices[l.id]?.status !== "generating" && l.text.trim()).map((l) => l.id);

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Voices</h1><div className="muted">ElevenLabs voices, who speaks with which, and each line's take.</div></div>
          <a className="btn" href="https://elevenlabs.io/app/voice-library" target="_blank" rel="noreferrer"><ExternalLink size={14} />ElevenLabs voice library</a>
        </div>

        <div className="voices-grid">
          <section className="col" style={{ gap: 12 }}>
            <div className="row"><h2 className="h2 grow">Library</h2><div className="search"><Search size={14} /><input className="input sm" placeholder="Search voices" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 180 }} /></div></div>
            <div className="panel" style={{ overflow: "hidden" }}>
              {list.map((v) => (
                <div key={v.id} className="voice-row">
                  <span className="voice-icon"><AudioLines size={14} /></span>
                  <span className="col grow" style={{ gap: 0, minWidth: 0 }}><span className="h3">{v.name}</span><span className="meta ellipsis">{v.tags.join(" · ")}</span></span>
                  <button className="btn btn-sm btn-ghost mono" title="Copy voice ID" onClick={() => { void navigator.clipboard.writeText(v.id); toast("Voice ID copied"); }}><Copy size={12} />{v.id.slice(0, 8)}…</button>
                </div>
              ))}
            </div>
            <div className="hint">Generation uses your own ElevenLabs key from Settings and spends your ElevenLabs credits. Unchanged lines are cached and never regenerated.</div>
          </section>

          <section className="col" style={{ gap: 12 }}>
            <div className="row"><h2 className="h2 grow">This project</h2>
              {performance && <Badge tone={voiced === lines.length && lines.length ? "ok" : undefined}>{voiced}/{lines.length} voiced</Badge>}
              {performance && pending.length > 0 && <button className="btn btn-sm" onClick={() => void generateVoices(pending)}><Wand2 size={12} />Voice {pending.length} line{pending.length > 1 ? "s" : ""}</button>}</div>
            {!performance ? (
              <Empty icon={<AudioLines size={18} />} title="No reel open" action={<Link className="btn" to="/projects">Open a project</Link>}>Open a reel to cast voices and generate its lines.</Empty>
            ) : <>
              {voiceNotice && <div className="callout warn"><div>{voiceNotice} <Link to="/settings">Open Settings</Link></div></div>}
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
                {lines.map((l) => <LineAudio key={l.id} pid={id!} lineId={l.id} speaker={l.speaker} text={l.text} v={voices[l.id]}
                  onRegenerate={() => void generateVoices([l.id], true)}
                  onUploaded={() => { void reloadFiles(); void refreshVoices(); }} />)}
                {lines.length === 0 && <div className="meta" style={{ padding: 16 }}>The script has no lines yet.</div>}
              </div>
              <div className="hint">Changing a line's text or its speaker's voice voices it again automatically. Regenerate asks ElevenLabs for a new take of the same text. An imported mp3 always wins over the generated take.</div>
            </>}
          </section>
        </div>
      </div>
    </div>
  );
}

function LineAudio({ pid, lineId, speaker, text, v, onRegenerate, onUploaded }: {
  pid: string; lineId: string; speaker: string; text: string; v?: VoiceLine; onRegenerate: () => void; onUploaded: () => void;
}) {
  const [playing, setPlaying] = useState(false);
  const [bust, setBust] = useState(0);
  const audio = useRef<HTMLAudioElement | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const src = v?.file ? fileUrl(pid, v.file, bust || undefined) : undefined;
  const peaks = usePeaks(src);
  useEffect(() => { audio.current?.pause(); audio.current = null; setPlaying(false); }, [src]);
  const cue = text.match(/\[([^\]]+)\]/g)?.map((c) => c.slice(1, -1)) ?? [];
  const toggle = () => {
    if (!src) return;
    if (!audio.current) { audio.current = new Audio(src); audio.current.onended = () => setPlaying(false); }
    if (playing) { audio.current.pause(); setPlaying(false); } else { void audio.current.play(); setPlaying(true); }
  };
  const upload = async (f: File) => {
    try { await api.upload(pid, `out/audio/${lineId}.mp3`, f); setBust(Date.now()); onUploaded(); toast(`${lineId} imported`); }
    catch (e) { toast((e as Error).message, "err"); }
  };
  const s = v?.status;
  return (
    <div className="line-audio">
      <button className="icon-btn sm bordered" disabled={!src} aria-label={playing ? "Pause" : "Play"} onClick={toggle}>{playing ? <Pause size={14} /> : <Play size={14} />}</button>
      <div className="col grow" style={{ gap: 4, minWidth: 0 }}>
        <div className="row" style={{ gap: 6 }}><span className="mono meta">{lineId} · {speaker}</span>{cue.map((c) => <Badge key={c}>{c}</Badge>)}</div>
        <span className="ellipsis">{stripTags(text) || <span className="faint">Empty line</span>}</span>
        {s === "error" && <span className="meta" style={{ color: "var(--err)" }}>{v?.error}</span>}
        {peaks && <svg className="mini-wave" viewBox={`0 0 ${peaks.data.length} 20`} preserveAspectRatio="none">{Array.from(peaks.data).filter((_, i) => i % 2 === 0).map((p, i) => <rect key={i} x={i * 2} y={10 - p * 9} width="1.2" height={Math.max(0.5, p * 18)} />)}</svg>}
      </div>
      {s === "generating" ? <Badge><Spinner />Generating</Badge> : s === "ready" ? <Badge tone="ok">Ready</Badge> : s === "imported" ? <Badge tone="ok">Imported</Badge>
        : s === "error" ? <Badge tone="err">Error</Badge> : <Badge>Not voiced</Badge>}
      {s !== "imported" && <button className="btn btn-sm" disabled={s === "generating" || !text.trim()} onClick={onRegenerate} title="Ask ElevenLabs for a new take"><RefreshCw size={12} />{s === "ready" ? "Regenerate" : "Generate"}</button>}
      <button className="btn btn-sm btn-ghost" onClick={() => input.current?.click()} title="Use your own mp3 for this line"><Upload size={12} />{s === "imported" ? "Replace" : "Import"}</button>
      <input ref={input} type="file" accept="audio/mpeg,.mp3" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ""; }} />
    </div>
  );
}
