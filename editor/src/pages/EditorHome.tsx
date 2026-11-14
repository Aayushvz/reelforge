// Editor entry point: open an existing project, start a blank one, or import media straight in.
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Film, Plus, Upload, Scissors, Clapperboard, FolderOpen } from "lucide-react";
import { api } from "@/lib/api";
import { defaultEditor } from "@/lib/defaults";
import { blankTimeline } from "@/lib/timeline";
import { RATIOS, FPS_OPTIONS, type ProjectSummary, type Ratio } from "@/lib/types";
import { relativeTime } from "@/lib/format";
import { Dialog } from "@/components/ui/Overlay";
import { Segmented, Select } from "@/components/ui/Form";
import { Badge, Callout, Empty } from "@/components/ui/Feedback";
import { toast } from "@/stores/ui";
import { ProjectThumb } from "./Projects";

export function EditorHome() {
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const [list, setList] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState<null | { importAfter: boolean }>(null);

  useEffect(() => { api.projects().then(setList).catch((e) => setError(e.message)); }, []);
  useEffect(() => { if (params.get("new") === "1") { setCreating({ importAfter: false }); setParams({}, { replace: true }); } }, [params, setParams]);

  const active = (list ?? []).filter((p) => !p.archived);
  const edits = active.filter((p) => p.kind === "blank");
  const reels = active.filter((p) => p.kind === "generated");

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Editor</h1><div className="muted">Edit a generated reel, keep working on a timeline, or start from your own footage.</div></div>
        </div>

        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12, marginBottom: 40 }}>
          <button className="start-card" onClick={() => setCreating({ importAfter: false })}>
            <span className="start-icon"><Plus size={18} /></span>
            <span className="col" style={{ gap: 2, textAlign: "left" }}><span className="h3">New blank project</span><span className="meta">Empty timeline. Pick canvas, resolution and frame rate.</span></span>
          </button>
          <button className="start-card" onClick={() => setCreating({ importAfter: true })}>
            <span className="start-icon"><Upload size={18} /></span>
            <span className="col" style={{ gap: 2, textAlign: "left" }}><span className="h3">Import media</span><span className="meta">Start a project from video, audio or images on disk.</span></span>
          </button>
          <Link to="/" className="start-card">
            <span className="start-icon"><Clapperboard size={18} /></span>
            <span className="col" style={{ gap: 2, textAlign: "left" }}><span className="h3">Generate a reel first</span><span className="meta">Write a script on Create, then edit what it produces.</span></span>
          </Link>
        </div>

        {error && <Callout tone="err">Couldn't load projects: {error}</Callout>}
        {!list && !error && <div className="skeleton" style={{ height: 180 }} />}
        {list && active.length === 0 && (
          <Empty icon={<Film size={18} />} title="No projects to edit yet" action={<button className="btn btn-primary" onClick={() => setCreating({ importAfter: false })}><Plus size={14} />New blank project</button>}>
            Blank projects and generated reels both open in the same editor.
          </Empty>
        )}
        {edits.length > 0 && <ProjectRow title="Continue editing" items={edits} onOpen={(p) => nav(`/editor/${encodeURIComponent(p.id)}`)} />}
        {reels.length > 0 && <ProjectRow title="Generated reels" items={reels} onOpen={(p) => nav(`/editor/${encodeURIComponent(p.id)}`)} />}
      </div>
      {creating && <NewProjectDialog importAfter={creating.importAfter} onClose={() => setCreating(null)} onCreated={(id) => nav(`/editor/${encodeURIComponent(id)}`)} />}
    </div>
  );
}

function ProjectRow({ title, items, onOpen }: { title: string; items: ProjectSummary[]; onOpen: (p: ProjectSummary) => void }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <div className="row" style={{ marginBottom: 12 }}><h2 className="h2 grow">{title}</h2><Link to="/projects" className="btn btn-sm btn-ghost"><FolderOpen size={14} />All projects</Link></div>
      <div className="grid grid-cards">
        {items.slice(0, 8).map((p) => (
          <div key={p.id} className="card interactive proj-card" role="button" tabIndex={0} onClick={() => onOpen(p)} onKeyDown={(e) => e.key === "Enter" && onOpen(p)}>
            <div className="proj-thumb"><ProjectThumb p={p} /><div className="over">{p.status === "rendered" && <Badge tone="ok">Rendered</Badge>}</div></div>
            <div style={{ padding: "10px 12px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
              <span className="h3 ellipsis">{p.name}</span>
              <span className="meta">{p.kind === "blank" ? "Edit project" : `${p.lineCount} lines`} · {p.ratio} · {relativeTime(p.updatedAt)}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function NewProjectDialog({ importAfter, onClose, onCreated }: { importAfter: boolean; onClose: () => void; onCreated: (id: string) => void }) {
  const [name, setName] = useState("Untitled edit");
  const [ratio, setRatio] = useState<Ratio>("9:16");
  const [fps, setFps] = useState(30);
  const [scale, setScale] = useState<"1080" | "720" | "2160">("1080");
  const [files, setFiles] = useState<FileList | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [bw, bh] = RATIOS[ratio];
  const k = scale === "720" ? 2 / 3 : scale === "2160" ? 2 : 1;
  const res: [number, number] = [Math.round(bw * k), Math.round(bh * k)];

  const create = async () => {
    setBusy(true);
    try {
      const ed = defaultEditor("blank", ratio);
      const p = await api.create({ name, editor: { ...ed, name, output: { ...ed.output, ratio, resolution: res, fps }, timeline: { ...blankTimeline() } } });
      if (files?.length) {
        for (const f of Array.from(files)) await api.upload(p.id, `media/${f.name.replace(/[^\w.\- ]+/g, "_")}`, f);
        toast(`${files.length} file${files.length > 1 ? "s" : ""} imported`);
      }
      onCreated(p.id);
    } catch (e) { toast((e as Error).message, "err"); setBusy(false); }
  };

  return (
    <Dialog title={importAfter ? "Import media into a new project" : "New blank project"} icon={<Scissors size={16} className="faint" />} onClose={onClose}
      footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy || !name.trim() || (importAfter && !files?.length)} onClick={() => void create()}>{busy ? "Creating…" : "Create and open"}</button></>}>
      <div className="field"><span className="label">Project name</span><input className="input" autoFocus value={name} onChange={(e) => setName(e.target.value)} /></div>
      <div className="field"><span className="label">Canvas</span>
        <Segmented full value={ratio} onChange={setRatio} options={(Object.keys(RATIOS) as Ratio[]).map((r) => ({ value: r, label: <><span className={`ratio-icon r${r.replace(":", "x")}`} />{r}</> }))} /></div>
      <div className="row" style={{ gap: 12 }}>
        <div className="field grow"><span className="label">Resolution</span>
          <Select ariaLabel="Resolution" value={scale} onChange={setScale} options={[{ value: "720", label: `${Math.round(bw * 2 / 3)} × ${Math.round(bh * 2 / 3)}` }, { value: "1080", label: `${bw} × ${bh}` }, { value: "2160", label: `${bw * 2} × ${bh * 2}` }]} /></div>
        <div className="field" style={{ width: 120 }}><span className="label">Frame rate</span>
          <Select ariaLabel="Frame rate" value={String(fps)} onChange={(v) => setFps(Number(v))} options={FPS_OPTIONS.map((f) => ({ value: String(f), label: `${f} fps` }))} /></div>
      </div>
      <div className="field"><span className="label">Media{importAfter ? "" : " (optional)"}</span>
        <button className="btn" onClick={() => fileRef.current?.click()}><Upload size={14} />{files?.length ? `${files.length} file${files.length > 1 ? "s" : ""} selected` : "Choose files"}</button>
        <input ref={fileRef} type="file" multiple accept="video/*,audio/*,image/*" hidden onChange={(e) => setFiles(e.target.files)} />
      </div>
    </Dialog>
  );
}
