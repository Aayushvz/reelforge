// The configuration rail beside the script: style, cast, set, subtitles, voice, output, generate.
import { useState, type ReactNode } from "react";
import { ChevronRight, Cpu, Cloud, Check, AudioLines, Music, Wand2, Info, Clock } from "lucide-react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { lineVoiced, useProject } from "@/stores/project";
import {
  STYLES, ENVIRONMENTS, NO_ENVIRONMENT, VOICES, character, environment, pipelineCast, pipelineSet, subtitleTemplate, voiceById,
} from "@/data/catalog";
import { RATIOS, FPS_OPTIONS, type Ratio, type SubtitleStyle } from "@/lib/types";
import { estimateDuration, validate } from "@/lib/script";
import { duration } from "@/lib/format";
import { CharacterThumb, EnvThumb, SubtitleText } from "@/components/Thumbs";
import { CharacterDrawer, EnvironmentDrawer, SubtitleControls, SubtitleGrid } from "@/components/pickers";
import { Drawer } from "@/components/ui/Overlay";
import { Segmented, Select } from "@/components/ui/Form";
import { Badge } from "@/components/ui/Feedback";
import { speakerTone } from "./ScriptStudio";
import { useLibrary } from "@/stores/library";
import { outfitsFor } from "@/lib/outfits";

function Panel({ title, children, right, id }: { title: string; children: ReactNode; right?: ReactNode; id: string }) {
  return (
    <section className="rail-panel" id={`panel-${id}`} aria-label={title}>
      <header className="row"><h3 className="h3 grow">{title}</h3>{right}</header>
      {children}
    </section>
  );
}

export function StylePanel() {
  const style = useProject((s) => s.editor.style);
  const setEditor = useProject((s) => s.setEditor);
  return (
    <Panel id="style" title="Animation style">
      <div className="style-grid">
        {STYLES.map((st) => (
          <button key={st.id} className="style-card" aria-pressed={style === st.id} disabled={st.status !== "available"}
            onClick={() => setEditor((e) => ({ ...e, style: st.id }))} title={st.status !== "available" ? "Planned engine, not built yet" : st.summary}>
            <div className="row" style={{ gap: 6 }}>
              {st.processing === "local" ? <Cpu size={14} /> : <Cloud size={14} />}
              <span className="h3 grow" style={{ textAlign: "left" }}>{st.name}</span>
              {style === st.id && <Check size={14} style={{ color: "var(--accent)" }} />}
            </div>
            <span className="meta" style={{ textAlign: "left" }}>{st.summary}</span>
            <div className="row" style={{ gap: 6, marginTop: "auto" }}>
              <Badge tone={st.processing === "local" ? "ok" : "warn"}>{st.cost}</Badge>
              {st.status === "planned" && <Badge>Planned</Badge>}
            </div>
          </button>
        ))}
      </div>
    </Panel>
  );
}

export function CastPanel() {
  const perf = useProject((s) => s.performance);
  const cast = useProject((s) => s.editor.cast);
  const setEditor = useProject((s) => s.setEditor);
  const setPerf = useProject((s) => s.setPerformance);
  const [open, setOpen] = useState<string | null>(null);
  const lib = useLibrary((s) => s.lib);
  const speakers = Object.keys(perf?.characters ?? {});
  return (
    <Panel id="cast" title="Cast" right={<span className="meta">{speakers.length} {speakers.length === 1 ? "speaker" : "speakers"}</span>}>
      <div className="col" style={{ gap: 6 }}>
        {speakers.map((sp) => {
          const slot = cast[sp];
          const c = character(slot?.characterId);
          const outfit = c ? outfitsFor(c, lib).find((o) => o.id === slot?.outfitId) : undefined;
          return (
            <button key={sp} className="cast-row" onClick={() => setOpen(sp)}>
              <span className="cast-avatar">{c ? <CharacterThumb character={c} outfit={outfit} /> : <span className="mono">{sp.slice(0, 2)}</span>}</span>
              <span className="col grow" style={{ gap: 0, minWidth: 0, textAlign: "left" }}>
                <span className="row" style={{ gap: 6 }}><span className="mono meta" style={{ color: speakerTone(perf, sp) }}>{sp}</span>
                  <span className="h3 ellipsis">{c ? c.name : "No character"}</span></span>
                <span className="meta ellipsis">{c ? `${outfit?.name ?? c.outfits[0].name} · ${c.vibe}` : "Pick from the cast of seven"}</span>
              </span>
              <ChevronRight size={14} className="faint" />
            </button>
          );
        })}
      </div>
      {open && (
        <CharacterDrawer speaker={open} value={cast[open]?.characterId ?? null} outfit={cast[open]?.outfitId ?? null} onClose={() => setOpen(null)}
          onPick={(characterId, outfitId) => {
            setEditor((e) => ({ ...e, cast: { ...e.cast, [open]: { ...e.cast[open], characterId, outfitId } } }));
            // the pick reaches the render: cast member + wardrobe index in performance.json
            const pc = pipelineCast(characterId, outfitId);
            setPerf((p) => {
              const { model: _m, outfit: _o, ...rest } = p.characters[open] ?? { voice_id: VOICES[0].id };
              return { ...p, characters: { ...p.characters, [open]: pc ? { ...rest, ...pc } : rest } };
            });
          }} />
      )}
    </Panel>
  );
}

export function SetPanel() {
  const env = useProject((s) => s.editor.environment);
  const setEditor = useProject((s) => s.setEditor);
  const setPerf = useProject((s) => s.setPerformance);
  const [open, setOpen] = useState(false);
  const e = environment(env.id) ?? NO_ENVIRONMENT;
  const preset = e.presets.find((p) => p.id === env.lighting) ?? e.presets[0];
  const pick = (id: string, lighting: string) => {
    setEditor((ed) => ({ ...ed, environment: { id, lighting } }));
    // the set and its lighting preset reach the render through performance.json
    setPerf((p) => ({ ...p, ...pipelineSet(id, lighting) }));
  };
  return (
    !ENVIRONMENTS.length ? (
      <Panel id="set" title="Set & lighting">
        <div className="meta">The environments moved to Shots-AV desk reels (Classic sets). <Link to="/shots-av">Open Shots-AV</Link></div>
      </Panel>
    ) :
    <Panel id="set" title="Set & lighting" right={<button className="btn btn-sm btn-ghost" onClick={() => setOpen(true)}>Browse<ChevronRight size={14} /></button>}>
      <button className="set-preview" onClick={() => setOpen(true)} aria-label={`Change set, currently ${e.name}`}>
        <EnvThumb env={e} preset={preset} />
        <span className="set-caption"><span className="h3">{e.name}</span><span className="meta">{preset.name}</span></span>
      </button>
      <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
        {e.presets.map((p) => (
          <button key={p.id} className="chip" aria-pressed={p.id === preset.id} onClick={() => pick(e.id, p.id)}><span className="dot" style={{ background: p.glow }} />{p.name}</button>
        ))}
      </div>
      {open && <EnvironmentDrawer value={e.id} lighting={preset.id} onPick={pick} onClose={() => setOpen(false)} />}
    </Panel>
  );
}

export function SubtitlePanel() {
  const subs = useProject((s) => s.editor.subtitles);
  const setEditor = useProject((s) => s.setEditor);
  const setPerf = useProject((s) => s.setPerformance);
  const [open, setOpen] = useState(false);
  const apply = (next: SubtitleStyle) => {
    setEditor((e) => ({ ...e, subtitles: next }));
    // caption and highlight colours are part of performance.json and do reach the render.
    setPerf((p) => ({ ...p, characters: Object.fromEntries(Object.entries(p.characters).map(([k, c]) => [k, { ...c, caption_color: next.color, highlight_color: next.highlight }])) }));
  };
  const t = subtitleTemplate(subs.templateId);
  return (
    <Panel id="subtitles" title="Subtitles" right={<button className="btn btn-sm btn-ghost" onClick={() => setOpen(true)}>Templates<ChevronRight size={14} /></button>}>
      <button className="sub-preview" onClick={() => setOpen(true)} aria-label="Change subtitle template">
        <SubtitleText s={subs} text="Wait. They actually approved it" active={3} scale={0.3} />
      </button>
      <div className="row"><span className="h3 grow">{t.name}{subs.templateId !== t.id ? " (custom)" : ""}</span><span className="meta">{subs.font} · {subs.size}px</span></div>
      {open && (
        <Drawer onClose={() => setOpen(false)} width={720}>
          <div className="drawer-head"><div className="col grow" style={{ gap: 2 }}><span className="eyebrow">Subtitles</span><h2 className="h2">Choose a template</h2></div></div>
          <div className="drawer-body">
            <SubtitleGrid value={subs.templateId} onPick={apply} />
            <div className="divider" />
            <div className="h3">Customise</div>
            <SubtitleControls s={subs} onChange={(patch) => apply({ ...subs, ...patch })} />
            <div className="callout"><Info size={14} /><div>Text and highlight colours reach the render today. Font, size, position and animation show in the editor preview and are saved for the caption renderer upgrade.</div></div>
          </div>
          <div className="dialog-foot"><button className="btn btn-primary" onClick={() => setOpen(false)}>Done</button></div>
        </Drawer>
      )}
    </Panel>
  );
}

export function VoicePanel() {
  const perf = useProject((s) => s.performance);
  const voices = useProject((s) => s.voices);
  const notice = useProject((s) => s.voiceNotice);
  const generate = useProject((s) => s.generateVoices);
  const setPerf = useProject((s) => s.setPerformance);
  const speakers = Object.keys(perf?.characters ?? {});
  const lines = perf?.lines ?? [];
  const cached = lines.filter((l) => lineVoiced(voices[l.id])).length;
  const busy = lines.some((l) => voices[l.id]?.status === "generating");
  const failed = lines.filter((l) => voices[l.id]?.status === "error");
  return (
    <Panel id="voice" title="Voice & audio" right={lines.length > 0 ? <Badge tone={cached === lines.length ? "ok" : undefined}><AudioLines size={11} />{busy ? "Voicing…" : `${cached}/${lines.length} voiced`}</Badge> : undefined}>
      <div className="col" style={{ gap: 6 }}>
        {speakers.map((sp) => {
          const v = perf!.characters[sp]?.voice_id ?? "";  // older or imported projects may have no voice yet
          const known = voiceById(v);
          return (
            <div key={sp} className="row">
              <span className="mono meta" style={{ width: 56, color: speakerTone(perf, sp) }}>{sp}</span>
              <Select size="sm" ariaLabel={`Voice for ${sp}`} value={known ? v : "custom"}
                onChange={(id) => id !== "custom" && setPerf((p) => ({ ...p, characters: { ...p.characters, [sp]: { ...p.characters[sp], voice_id: id } } }))}
                options={[...VOICES.map((x) => ({ value: x.id, label: `${x.name} · ${x.tags.slice(1, 3).join(", ")}` })), ...(known ? [] : [{ value: "custom", label: v ? `Custom ID ${v.slice(0, 6)}…` : "No voice yet" }])]} />
            </div>
          );
        })}
      </div>
      {notice ? <div className="hint" style={{ color: "var(--warn)" }}>{notice} <Link to="/settings">Settings</Link></div>
        : failed.length > 0 ? <div className="row" style={{ gap: 6 }}><span className="hint grow" style={{ color: "var(--err)" }}>{failed.length} line{failed.length > 1 ? "s" : ""} failed: {voices[failed[0].id]?.error}</span>
          <button className="btn btn-sm" onClick={() => void generate(failed.map((l) => l.id))}><RefreshCw size={12} />Retry</button></div>
        : <div className="hint">Each line is voiced automatically with ElevenLabs a moment after you stop typing. An imported mp3 always wins.</div>}
      <div className="row muted" style={{ gap: 8 }}><Music size={14} className="faint" /><span className="meta grow">No music library bundled yet</span><Badge>Editor only</Badge></div>
    </Panel>
  );
}

export function OutputPanel() {
  const out = useProject((s) => s.editor.output);
  const look = useProject((s) => s.performance?.look ?? "classic");
  const finalQuality = useProject((s) => (s.performance?.quality === "cinema" ? "cinema" : "standard"));
  const setEditor = useProject((s) => s.setEditor);
  const setPerf = useProject((s) => s.setPerformance);
  const setRatio = (ratio: Ratio) => {
    setEditor((e) => ({ ...e, output: { ...e.output, ratio, resolution: [...RATIOS[ratio]] as [number, number] } }));
    setPerf((p) => ({ ...p, ratio }));
  };
  return (
    <Panel id="output" title="Output">
      <Segmented full value={out.ratio} onChange={setRatio} options={(Object.keys(RATIOS) as Ratio[]).map((r) => ({ value: r, label: <><span className={`ratio-icon r${r.replace(":", "x")}`} />{r}</> }))} />
      <div className="row" style={{ gap: 8 }}>
        <div className="field grow"><span className="label">Resolution</span><div className="input sm mono" style={{ display: "flex", alignItems: "center", color: "var(--text-2)" }}>{out.resolution[0]} × {out.resolution[1]}</div></div>
        <div className="field" style={{ width: 84 }}><span className="label">Frame rate</span>
          <Select size="sm" ariaLabel="Frame rate" value={String(out.fps)} onChange={(v) => { setEditor((e) => ({ ...e, output: { ...e.output, fps: Number(v) } })); setPerf((p) => ({ ...p, fps: Number(v) })); }}
            options={FPS_OPTIONS.map((f) => ({ value: String(f), label: `${f} fps` }))} /></div>
        <div className="field" style={{ width: 124 }}><span className="label">Quality</span>
          <Segmented full size="sm" value={out.quality} onChange={(q) => setEditor((e) => ({ ...e, output: { ...e.output, quality: q } }))}
            options={look === "cinema"
              ? [{ value: "draft", label: "Draft", title: "Half size, fast preview" }, { value: "final", label: "Final", title: "Full size, ray-traced" }]
              : [{ value: "draft", label: "Draft", title: "16 samples, faster" }, { value: "final", label: "Final", title: "64 samples" }]} /></div>
      </div>
      <div className="row" style={{ gap: 8 }}>
        <div className="field grow"><span className="label">Look</span>
          <Segmented full size="sm" value={look} onChange={(l) => setPerf((p) => ({ ...p, look: l }))}
            options={[{ value: "classic", label: "Classic", title: "The original look. Fastest." },
              { value: "cinema", label: "Cinema", title: "Ray-traced faces, a film camera, a darker room. Slower." }]} /></div>
        {look === "cinema" && (
          <div className="field" style={{ width: 168 }}><span className="label">Final render</span>
            <Segmented full size="sm" value={finalQuality} onChange={(q) => setPerf((p) => ({ ...p, quality: q }))}
              options={[{ value: "standard", label: "Standard", title: "About 10 to 25 seconds a frame" },
                { value: "cinema", label: "Max", title: "More samples, 16-bit frames. Roughly twice as slow." }]} /></div>
        )}
      </div>
    </Panel>
  );
}

export function GenerateBar({ onGenerate, busy }: { onGenerate: () => void; busy: boolean }) {
  const perf = useProject((s) => s.performance);
  const ed = useProject((s) => s.editor);
  const voices = useProject((s) => s.voices);
  const issues = validate(perf);
  const lines = perf?.lines ?? [];
  const env = environment(ed.environment.id);
  const preset = env?.presets.find((p) => p.id === ed.environment.lighting);
  const castNames = Object.keys(perf?.characters ?? {}).map((sp) => character(ed.cast[sp]?.characterId)?.name ?? sp).join(", ");
  const missingAudio = lines.filter((l) => !lineVoiced(voices[l.id])).length;
  const go = (id: string) => document.getElementById(`panel-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  const rows: [string, string, string][] = [
    ["Script", lines.length ? `${lines.length} lines · ≈ ${duration(estimateDuration(perf))}` : "Empty", "script"],
    ["Cast", castNames || "None", "cast"],
    ["Set", env ? `${env.name} · ${preset?.name ?? ""}` : "None", "set"],
    ["Style", STYLES.find((s) => s.id === ed.style)?.name ?? ed.style, "style"],
    ["Subtitles", subtitleTemplate(ed.subtitles.templateId).name, "subtitles"],
    ["Voice", lines.length ? (missingAudio ? `${missingAudio} line${missingAudio > 1 ? "s" : ""} not voiced yet` : "All lines voiced") : "—", "voice"],
    ["Output", `${ed.output.ratio} · ${ed.output.resolution.join("×")} · ${ed.output.fps} fps · ${ed.output.quality}`, "output"],
  ];
  const blocking = issues.length > 0 ? issues[0].message : missingAudio > 0 ? `${missingAudio} voice line${missingAudio > 1 ? "s" : ""} missing` : null;
  return (
    <div className="generate">
      <dl className="summary">
        {rows.map(([k, v, target]) => (
          <div key={k} className="summary-row" role="button" tabIndex={0} onClick={() => target === "script" ? document.querySelector<HTMLTextAreaElement>(".line-text")?.focus() : go(target)}
            onKeyDown={(e) => e.key === "Enter" && go(target)}>
            <dt>{k}</dt><dd className="ellipsis" style={k === "Voice" && missingAudio ? { color: "var(--warn)" } : undefined}>{v}</dd>
          </div>
        ))}
      </dl>
      <button className="btn btn-primary btn-lg generate-btn" disabled={busy || lines.length === 0} onClick={onGenerate}>
        <Wand2 size={16} />Generate video
      </button>
      <div className="row meta" style={{ gap: 6, justifyContent: "center" }}>
        <Cpu size={12} />Local Blender render · free<span className="faint">·</span><Clock size={12} />Stills first, for approval
      </div>
      {blocking && lines.length > 0 && <div className="hint" style={{ textAlign: "center", color: "var(--warn)" }}>{blocking}</div>}
    </div>
  );
}
