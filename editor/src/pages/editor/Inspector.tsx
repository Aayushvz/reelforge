// Right panel. Adapts to the selected clip; with nothing selected it shows project-wide settings.
import { Info, RefreshCw, Trash2 } from "lucide-react";
import type { Clip, EditorDoc, Mood, Performance, ShotKind } from "@/lib/types";
import { EMOTIONS, MOODS } from "@/lib/types";
import * as T from "@/lib/timeline";
import { cap, duration } from "@/lib/format";
import { ENVIRONMENTS, MOOD_COLORS, SUBTITLE_TEMPLATES, character, environment } from "@/data/catalog";
import { useProject } from "@/stores/project";
import { FieldRow, Section, Segmented, Select, Slider, ColorInput } from "@/components/ui/Form";
import { SubtitleControls } from "@/components/pickers";
import { Badge } from "@/components/ui/Feedback";
import { useEditor } from "./store";

type Props = { editor: EditorDoc; performance: Performance | null; onRegenerate: () => void };

export function Inspector({ editor, performance, onRegenerate }: Props) {
  const tl = useEditor((s) => s.tl)!;
  const selection = useEditor((s) => s.selection);
  const sel = tl.clips.filter((c) => selection.includes(c.id));
  if (sel.length > 1) return (
    <div className="insp">
      <div className="insp-head"><span className="h3">{sel.length} clips selected</span></div>
      <div className="insp-pad col"><span className="meta">Total {duration(sel.reduce((n, c) => n + c.duration, 0))}. Drag to move them together, or press Delete.</span>
        <button className="btn btn-sm btn-danger" onClick={() => { useEditor.getState().edit((t) => T.removeClips(t, selection)); useEditor.getState().select([]); }}><Trash2 size={14} />Delete clips</button></div>
    </div>
  );
  if (sel.length === 1) return <ClipInspector clip={sel[0]} editor={editor} performance={performance} onRegenerate={onRegenerate} />;
  return <ProjectInspector editor={editor} />;
}

function ClipInspector({ clip, editor, performance, onRegenerate }: { clip: Clip; editor: EditorDoc; performance: Performance | null; onRegenerate: () => void }) {
  const tl = useEditor((s) => s.tl)!;
  const edit = useEditor((s) => s.edit);
  const track = T.trackOf(tl, clip);
  const patch = (p: Partial<Clip>, key?: string) => edit((t) => T.updateClip(t, clip.id, p), key ? `${clip.id}:${key}` : undefined);
  const line = performance?.lines.find((l) => l.id === clip.lineId);
  const setPerf = useProject((s) => s.setPerformance);
  const patchLine = (p: Partial<NonNullable<typeof line>>) => line && setPerf((perf) => ({ ...perf, lines: perf.lines.map((l) => (l.id === line.id ? { ...l, ...p } : l)) }));

  const timing = (
    <Section title="Timing">
      <FieldRow label="Start"><NumberField value={clip.start} onChange={(v) => patch({ start: Math.max(0, v) }, "start")} suffix="s" /></FieldRow>
      <FieldRow label="Duration"><NumberField value={clip.duration} onChange={(v) => patch({ duration: Math.max(T.MIN_CLIP, v) }, "dur")} suffix="s" /></FieldRow>
      {track.locked && <div className="hint">Track is locked.</div>}
    </Section>
  );

  return (
    <div className="insp">
      <div className="insp-head">
        <span className="tl-swatch" style={{ background: T.TRACK_COLOR[track.kind] }} />
        <span className="h3 grow ellipsis">{track.kind === "shots" ? "Shot" : track.name}</span>
        {clip.status === "estimated" && <Badge title="Estimated from the script until voice lines and a render plan exist">Estimated</Badge>}
        {clip.status === "planned" && <Badge tone="info">Render plan</Badge>}
      </div>
      <div className="insp-scroll">
        {track.kind === "shots" && <>
          <Section title="Camera">
            <FieldRow label="Framing"><Segmented size="sm" value={clip.shotKind ?? "medium"} onChange={(k: ShotKind) => patch({ shotKind: k, lens: T.LENSES[k] })}
              options={[{ value: "wide", label: "Wide" }, { value: "medium", label: "Medium" }, { value: "closeup", label: "Close-up" }]} /></FieldRow>
            <FieldRow label="Lens"><Select size="sm" value={String(clip.lens ?? 50)} onChange={(v) => patch({ lens: Number(v) })} options={[24, 35, 50, 85, 105].map((l) => ({ value: String(l), label: `${l} mm` }))} /></FieldRow>
            <FieldRow label="Movement"><Select size="sm" value={clip.movement ?? "push"} onChange={(v) => patch({ movement: v })}
              options={[{ value: "static", label: "Static" }, { value: "push", label: "Push in" }, { value: "pull", label: "Pull out" }, { value: "drift", label: "Drift" }]} /></FieldRow>
            <FieldRow label="Push"><Slider ariaLabel="Push amount" value={clip.push ?? 0.05} max={0.3} onChange={(v) => patch({ push: v }, "push")} /></FieldRow>
            <FieldRow label="Subject"><span className="mono meta">{clip.subject ?? "—"}{clip.subject && character(editor.cast[clip.subject]?.characterId) ? ` · ${character(editor.cast[clip.subject]?.characterId)!.name}` : ""}</span></FieldRow>
            <FieldRow label="Transition in"><Segmented size="sm" value={clip.transition ?? "cut"} onChange={(v) => patch({ transition: v })} options={[{ value: "cut", label: "Cut" }, { value: "fade", label: "Fade" }, { value: "dip", label: "Dip" }]} /></FieldRow>
          </Section>
          {timing}
          <Section title="Generation">
            <div className="callout"><Info size={14} /><div>Shot edits are saved to the project. The director in the pipeline doesn't read overrides yet, so a render re-plans shots from the script.</div></div>
            <button className="btn btn-sm" onClick={onRegenerate}><RefreshCw size={14} />Regenerate stills</button>
          </Section>
        </>}

        {track.kind === "dialogue" && <>
          <Section title="Line">
            {line ? <>
              <textarea className="textarea" rows={3} value={line.text} onChange={(e) => patchLine({ text: e.target.value })} aria-label="Line text" />
              <FieldRow label="Speaker"><span className="mono">{line.speaker}</span></FieldRow>
              <FieldRow label="Emotion"><Select size="sm" value={line.emotion} onChange={(v) => patchLine({ emotion: v })} options={EMOTIONS.map((e) => ({ value: e, label: cap(e) }))} /></FieldRow>
              <FieldRow label="Intensity"><Slider ariaLabel="Intensity" value={line.intensity} onChange={(v) => patchLine({ intensity: v })} /></FieldRow>
              <div className="hint">Edits here change the script (performance.json).</div>
            </> : <span className="meta">This clip isn't linked to a script line.</span>}
          </Section>
          <AudioSection clip={clip} patch={patch} />
          {timing}
        </>}

        {track.kind === "animation" && <>
          <Section title="Performance">
            <FieldRow label="Emotion"><Select size="sm" value={clip.emotion ?? "neutral"} onChange={(v) => { patch({ emotion: v, label: v }); patchLine({ emotion: v }); }} options={EMOTIONS.map((e) => ({ value: e, label: cap(e) }))} /></FieldRow>
            <FieldRow label="Intensity"><Slider ariaLabel="Intensity" value={clip.intensity ?? 0.5} onChange={(v) => { patch({ intensity: v }, "int"); patchLine({ intensity: v }); }} /></FieldRow>
            <FieldRow label="Character"><span className="meta">{clip.subject}{character(editor.cast[clip.subject ?? ""]?.characterId) ? ` · ${character(editor.cast[clip.subject ?? ""]?.characterId)!.name}` : " · stand-in"}</span></FieldRow>
            <div className="hint">Emotion and intensity write back to the script line, so the face tracks pick them up on the next render.</div>
          </Section>
          {timing}
        </>}

        {track.kind === "mood" && <>
          <Section title="Lighting mood">
            <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
              {MOODS.map((m) => <button key={m} className="chip" aria-pressed={clip.mood === m} onClick={() => patch({ mood: m as Mood, label: m })}><span className="dot" style={{ background: MOOD_COLORS[m] }} />{cap(m)}</button>)}
            </div>
            <div className="hint">The renderer crossfades lights per line mood from the script. Edit a line's mood in the script to change the render.</div>
          </Section>
          {timing}
        </>}

        {(track.kind === "subtitles" || track.kind === "overlay") && <>
          <Section title={track.kind === "overlay" ? "Text" : "Caption"}>
            <textarea className="textarea" rows={2} value={clip.text ?? clip.label} onChange={(e) => patch({ text: e.target.value, label: e.target.value }, "text")} aria-label="Text" />
            {track.kind === "overlay" && <>
              <FieldRow label="Colour"><ColorInput label="Text colour" value={clip.color ?? "#FFFFFF"} onChange={(v) => patch({ color: v })} /></FieldRow>
              <FieldRow label="Height"><Slider ariaLabel="Vertical position" value={clip.offset ?? 0.12} max={0.9} onChange={(v) => patch({ offset: v }, "y")} format={(v) => `${Math.round(v * 100)}%`} /></FieldRow>
            </>}
          </Section>
          {track.kind === "subtitles" && <Section title="Style (all captions)"><SubtitleStyleEditor /></Section>}
          {timing}
        </>}

        {(track.kind === "music" || track.kind === "sfx" || track.kind === "audio") && <><AudioSection clip={clip} patch={patch} />{timing}</>}

        {track.kind === "video" && <>
          <Section title="Clip">
            <FieldRow label="Source"><span className="meta ellipsis" title={clip.src}>{clip.src}</span></FieldRow>
            <FieldRow label="In point"><NumberField value={clip.offset ?? 0} onChange={(v) => patch({ offset: Math.max(0, v) }, "off")} suffix="s" /></FieldRow>
            <FieldRow label="Volume"><Slider ariaLabel="Volume" value={clip.volume ?? 1} onChange={(v) => patch({ volume: v }, "vol")} format={(v) => `${Math.round(v * 100)}%`} /></FieldRow>
            <FieldRow label="Transition in"><Segmented size="sm" value={clip.transition ?? "cut"} onChange={(v) => patch({ transition: v })} options={[{ value: "cut", label: "Cut" }, { value: "fade", label: "Fade" }, { value: "dip", label: "Dip" }]} /></FieldRow>
          </Section>
          {timing}
        </>}
      </div>
    </div>
  );
}

function AudioSection({ clip, patch }: { clip: Clip; patch: (p: Partial<Clip>, key?: string) => void }) {
  return (
    <Section title="Audio">
      <FieldRow label="Volume"><Slider ariaLabel="Volume" value={clip.volume ?? 1} onChange={(v) => patch({ volume: v }, "vol")} format={(v) => `${Math.round(v * 100)}%`} /></FieldRow>
      <FieldRow label="Fade in"><Slider ariaLabel="Fade in" value={clip.fadeIn ?? 0} max={Math.min(3, clip.duration / 2)} step={0.05} onChange={(v) => patch({ fadeIn: v }, "fi")} format={(v) => `${v.toFixed(1)}s`} /></FieldRow>
      <FieldRow label="Fade out"><Slider ariaLabel="Fade out" value={clip.fadeOut ?? 0} max={Math.min(3, clip.duration / 2)} step={0.05} onChange={(v) => patch({ fadeOut: v }, "fo")} format={(v) => `${v.toFixed(1)}s`} /></FieldRow>
      {!clip.src && <div className="hint">No audio file yet. Import the line's mp3 in Voices or from the script.</div>}
    </Section>
  );
}

function SubtitleStyleEditor() {
  const subs = useProject((s) => s.editor.subtitles);
  const setEditor = useProject((s) => s.setEditor);
  return <>
    <FieldRow label="Template"><Select size="sm" value={subs.templateId} onChange={(id) => setEditor((e) => ({ ...e, subtitles: { ...SUBTITLE_TEMPLATES.find((t) => t.id === id)!.style } }))}
      options={SUBTITLE_TEMPLATES.map((t) => ({ value: t.id, label: t.name }))} /></FieldRow>
    <SubtitleControls s={subs} compact onChange={(p) => setEditor((e) => ({ ...e, subtitles: { ...e.subtitles, ...p } }))} />
  </>;
}

function ProjectInspector({ editor }: { editor: EditorDoc }) {
  const setEditor = useProject((s) => s.setEditor);
  const env = environment(editor.environment.id) ?? ENVIRONMENTS[0];
  const g = editor.grade;
  const setGrade = (k: keyof typeof g, v: number) => setEditor((e) => ({ ...e, grade: { ...e.grade, [k]: v } }));
  return (
    <div className="insp">
      <div className="insp-head"><span className="h3 grow">Project</span><span className="meta">Nothing selected</span></div>
      <div className="insp-scroll">
        {editor.kind === "generated" && (
          <Section title="Environment">
            <FieldRow label="Set"><Select size="sm" value={env.id} onChange={(id) => setEditor((e) => ({ ...e, environment: { id, lighting: environment(id)!.presets[0].id } }))}
              options={ENVIRONMENTS.map((x) => ({ value: x.id, label: x.name + (x.status === "available" ? "" : " (planned)") }))} /></FieldRow>
            <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
              {env.presets.map((p) => <button key={p.id} className="chip" aria-pressed={editor.environment.lighting === p.id} onClick={() => setEditor((e) => ({ ...e, environment: { ...e.environment, lighting: p.id } }))}><span className="dot" style={{ background: p.glow }} />{p.name}</button>)}
            </div>
          </Section>
        )}
        <Section title="Subtitles"><SubtitleStyleEditor /></Section>
        <Section title="Colour & finish">
          <FieldRow label="Brightness"><Slider ariaLabel="Brightness" value={g.brightness} min={-0.5} max={0.5} onChange={(v) => setGrade("brightness", v)} /></FieldRow>
          <FieldRow label="Contrast"><Slider ariaLabel="Contrast" value={g.contrast} min={-0.5} max={0.5} onChange={(v) => setGrade("contrast", v)} /></FieldRow>
          <FieldRow label="Saturation"><Slider ariaLabel="Saturation" value={g.saturation} min={-1} max={1} onChange={(v) => setGrade("saturation", v)} /></FieldRow>
          <FieldRow label="Vignette"><Slider ariaLabel="Vignette" value={g.vignette} onChange={(v) => setGrade("vignette", v)} /></FieldRow>
          <FieldRow label="Film grain"><Slider ariaLabel="Film grain" value={g.grain} onChange={(v) => setGrade("grain", v)} /></FieldRow>
          <FieldRow label="Highlight glow"><Slider ariaLabel="Highlight glow" value={g.glow} onChange={(v) => setGrade("glow", v)} /></FieldRow>
          <div className="hint">Previewed here. The render's finishing pass (halation, grade, vignette, grain) uses its built-in values until these settings are wired into it.</div>
        </Section>
        <Section title="Audio mix">
          <FieldRow label="Dialogue"><Slider ariaLabel="Dialogue volume" value={editor.audio.dialogueVolume} onChange={(v) => setEditor((e) => ({ ...e, audio: { ...e.audio, dialogueVolume: v } }))} format={(v) => `${Math.round(v * 100)}%`} /></FieldRow>
          <FieldRow label="Music"><Slider ariaLabel="Music volume" value={editor.audio.musicVolume} onChange={(v) => setEditor((e) => ({ ...e, audio: { ...e.audio, musicVolume: v } }))} format={(v) => `${Math.round(v * 100)}%`} /></FieldRow>
          <FieldRow label="Ducking"><Segmented size="sm" value={editor.audio.duckMusic ? "on" : "off"} onChange={(v) => setEditor((e) => ({ ...e, audio: { ...e.audio, duckMusic: v === "on" } }))} options={[{ value: "on", label: "Duck under dialogue" }, { value: "off", label: "Off" }]} /></FieldRow>
        </Section>
        <Section title="Canvas" defaultOpen={false}>
          <dl className="kv"><dt>Aspect</dt><dd className="mono">{editor.output.ratio}</dd><dt>Resolution</dt><dd className="mono">{editor.output.resolution.join(" × ")}</dd><dt>Frame rate</dt><dd className="mono">{editor.output.fps} fps</dd></dl>
          <div className="hint">Change the aspect ratio from the toolbar.</div>
        </Section>
      </div>
    </div>
  );
}

function NumberField({ value, onChange, suffix }: { value: number; onChange: (v: number) => void; suffix?: string }) {
  return (
    <span className="row" style={{ gap: 6 }}>
      <input className="input sm mono" type="number" step={0.01} value={Number(value.toFixed(2))} onChange={(e) => onChange(Number(e.target.value))} style={{ width: 96 }} />
      {suffix && <span className="faint">{suffix}</span>}
    </span>
  );
}
