// Subtitle template studio: browse templates, style one live over a frame, save or apply it.
import { useEffect, useState } from "react";
import { Save, CheckCheck, Trash2 } from "lucide-react";
import { ENVIRONMENTS, NO_ENVIRONMENT, SUBTITLE_TEMPLATES } from "@/data/catalog";
import type { SubtitleStyle } from "@/lib/types";
import { SubtitleGrid, SubtitleControls } from "@/components/pickers";
import { EnvThumb, SubtitleText } from "@/components/Thumbs";
import { Dialog } from "@/components/ui/Overlay";
import { Segmented } from "@/components/ui/Form";
import { useLibrary } from "@/stores/library";
import { NONE } from "@/lib/format";
import { useProject } from "@/stores/project";
import { toast } from "@/stores/ui";
import { uid } from "@/lib/format";

const SAMPLE = "Wait. They actually approved it";

export function SubtitlesPage() {
  const [s, setS] = useState<SubtitleStyle>({ ...SUBTITLE_TEMPLATES[0].style });
  const [word, setWord] = useState(0);
  const [frame, setFrame] = useState<"9:16" | "16:9">("9:16");
  const [saving, setSaving] = useState(false);
  const projectId = useProject((p) => p.id);
  const projectName = useProject((p) => p.editor.name);
  const setEditor = useProject((p) => p.setEditor);
  const setPerf = useProject((p) => p.setPerformance);
  const hasPerf = useProject((p) => Boolean(p.performance));
  const saved = useLibrary((l) => l.lib.subtitleTemplates) ?? NONE;
  const update = useLibrary((l) => l.update);

  // step through the words so the highlight style is visible
  useEffect(() => {
    const n = SAMPLE.split(" ").length;
    const t = setInterval(() => setWord((w) => (w + 1) % (n + 2)), 420);
    return () => clearInterval(t);
  }, []);

  const env = ENVIRONMENTS[0] ?? NO_ENVIRONMENT;
  const preset = env.presets[0];
  const W = frame === "9:16" ? 1080 : 1920;
  const H = frame === "9:16" ? 1920 : 1080;
  const scale = frame === "9:16" ? 300 / H : 520 / W;
  const isSaved = saved.some((t) => t.id === s.templateId);

  const apply = () => {
    setEditor((e) => ({ ...e, subtitles: { ...s } }));
    if (hasPerf) setPerf((p) => ({ ...p, characters: Object.fromEntries(Object.entries(p.characters).map(([k, c]) => [k, { ...c, caption_color: s.color, highlight_color: s.highlight }])) }));
    toast(`Applied to ${projectName}`);
  };

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Subtitle templates</h1><div className="muted">Typography for captions. Style one, save it, reuse it on any reel.</div></div>
          {isSaved && <button className="btn btn-danger" onClick={() => { update((l) => ({ ...l, subtitleTemplates: (l.subtitleTemplates ?? []).filter((t) => t.id !== s.templateId) })); setS({ ...SUBTITLE_TEMPLATES[0].style }); toast("Template deleted"); }}><Trash2 size={14} />Delete</button>}
          <button className="btn" onClick={() => setSaving(true)}><Save size={14} />Save as template</button>
          {projectId && <button className="btn btn-primary" onClick={apply}><CheckCheck size={14} />Apply to {projectName}</button>}
        </div>
        <div className="sub-studio">
          <div className="sub-stage">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="label">Live preview</span>
              <Segmented size="sm" value={frame} onChange={setFrame} options={[{ value: "9:16", label: "9:16" }, { value: "16:9", label: "16:9" }]} />
            </div>
            <div className="sub-frame" style={{ width: W * scale, height: H * scale }}>
              <EnvThumb env={env} preset={preset} style={{ position: "absolute", inset: 0 }} />
              <div className="sub-frame-text" style={{
                justifyContent: s.align === "left" ? "flex-start" : s.align === "right" ? "flex-end" : "center", textAlign: s.align,
                ...(s.position === "upper" ? { top: H * 0.16 * scale } : s.position === "middle" ? { top: "50%", transform: "translateY(-50%)" } : { bottom: H * 0.2 * scale }),
              }}>
                <SubtitleText s={s} text={SAMPLE.split(" ").slice(0, s.wordsPerLine >= 5 ? 5 : s.wordsPerLine + 1).join(" ")} active={word} scale={scale} />
              </div>
            </div>
          </div>
          <div className="panel sub-controls">
            <div className="h3">Customise</div>
            <SubtitleControls s={s} onChange={(p) => setS((x) => ({ ...x, ...p }))} />
          </div>
        </div>
        <h2 className="h2" style={{ margin: "32px 0 12px" }}>Templates</h2>
        <SubtitleGrid value={s.templateId} onPick={setS} columns={5} />
      </div>
      {saving && <SaveDialog onClose={() => setSaving(false)} onSave={(name) => {
        const id = uid("sub-");
        update((l) => ({ ...l, subtitleTemplates: [...(l.subtitleTemplates ?? []), { ...s, id, name, templateId: id }] }));
        setS((x) => ({ ...x, templateId: id }));
        toast(`Saved "${name}" to your library`);
      }} />}
    </div>
  );
}

function SaveDialog({ onClose, onSave }: { onClose: () => void; onSave: (name: string) => void }) {
  const [name, setName] = useState("My caption style");
  return (
    <Dialog title="Save subtitle template" onClose={onClose} footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={!name.trim()} onClick={() => { onSave(name.trim()); onClose(); }}>Save</button></>}>
      <input className="input" autoFocus value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && name.trim()) { onSave(name.trim()); onClose(); } }} />
      <div className="hint">Saved templates appear in the subtitle picker on every project.</div>
    </Dialog>
  );
}
