// Home: the creation studio. Script on the left, the whole video's configuration on the right.
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Film, ChevronDown, FolderOpen, Plus, Clapperboard } from "lucide-react";
import { useProject, setOnProjectCreated } from "@/stores/project";
import { api, fileUrl } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { relativeTime } from "@/lib/format";
import { ScriptStudio } from "./create/ScriptStudio";
import { CastPanel, GenerateBar, OutputPanel, SetPanel, StylePanel, SubtitlePanel, VoicePanel } from "./create/Rail";
import { SaveStatus } from "@/components/SaveStatus";
import { useMenu } from "@/components/ui/Overlay";
import { Callout, Spinner } from "@/components/ui/Feedback";
import "./create/create.css";

const LAST = "rf.lastCreate";
const remember = (id: string | null) => { try { if (id) localStorage.setItem(LAST, id); else localStorage.removeItem(LAST); } catch { /* ignore */ } };
const recall = () => { try { return localStorage.getItem(LAST); } catch { return null; } };

export function CreatePage() {
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const p = params.get("p");
  const isNew = params.get("new") === "1";
  const { id, loading, error, editor, performance, load, startDraft, setEditor, saveNow } = useProject();
  const deskReel = editor.style === "shots-av" || performance?.style === "shots-av";
  const [recent, setRecent] = useState<ProjectSummary[] | null>(null);
  const [busy, setBusy] = useState(false);
  const menu = useMenu();
  const switcher = useRef<HTMLButtonElement>(null);

  // Bind the page to a project: ?p=id, a fresh draft (?new=1), or the last one you worked on.
  useEffect(() => {
    if (isNew) { startDraft("generated"); remember(null); setParams({}, { replace: true }); return; }
    const target = p ?? recall();
    if (target) { if (target !== useProject.getState().id) void load(target).then(() => { if (useProject.getState().error) { remember(null); startDraft("generated"); setParams({}, { replace: true }); } }); }
    else if (useProject.getState().editor.kind !== "generated" || useProject.getState().id) startDraft("generated");
  }, [p, isNew]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setOnProjectCreated((newId) => { remember(newId); setParams({ p: newId }, { replace: true }); });
    return () => setOnProjectCreated(null);
  }, [setParams]);

  useEffect(() => {
    if (!id) return;
    if (deskReel) {  // a desk reel has its own workspace; this page is the blender3d flow
      remember(null);
      nav(`/shots-av/${encodeURIComponent(id)}`, { replace: true });
      return;
    }
    remember(id);
    if (p !== id) setParams({ p: id }, { replace: true });
  }, [id, deskReel]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { api.projects().then(setRecent).catch(() => setRecent([])); }, [id]);

  const generate = async () => {
    setBusy(true);
    const pid = await saveNow();
    setBusy(false);
    if (pid) nav(`/projects/${encodeURIComponent(pid)}/render?start=stills`);
  };
  const openEditor = async () => {
    const pid = await saveNow();
    if (pid) nav(`/editor/${encodeURIComponent(pid)}`);
  };

  const others = (recent ?? []).filter((r) => r.id !== id && !r.archived);
  if (id && deskReel) return <div className="page"><div className="page-inner"><Spinner /></div></div>;

  return (
    <div className="create">
      <h1 className="sr-only">Create a reel</h1>
      <header className="create-bar">
        <input className="title-input" value={editor.name} aria-label="Project name" spellCheck={false}
          onChange={(e) => setEditor((ed) => ({ ...ed, name: e.target.value }))} onBlur={() => void saveNow()} />
        <button ref={switcher} className="icon-btn sm" aria-label="Switch project" onClick={() => menu.openAt(switcher.current!.getBoundingClientRect(), [
          { label: "New reel", icon: <Plus size={14} />, onSelect: () => nav("/?new=1") },
          ...(others.length ? [{ separator: true } as const, { heading: "Recent" } as const] : []),
          ...others.slice(0, 8).map((r) => ({ label: r.name, icon: <Clapperboard size={14} />, onSelect: () => nav(`/?p=${encodeURIComponent(r.id)}`) })),
          { separator: true },
          { label: "All projects", icon: <FolderOpen size={14} />, onSelect: () => nav("/projects") },
        ])}><ChevronDown size={14} /></button>
        <SaveStatus />
        <div className="grow" />
        <button className="btn btn-sm" onClick={() => void openEditor()} disabled={!useProject.getState().performance?.lines.length && !id}><Film size={14} />Open in editor</button>
      </header>

      {loading ? <div className="row" style={{ padding: 32 }}><Spinner /><span className="muted">Opening project…</span></div> :
       error ? <div style={{ padding: 32 }}><Callout tone="err">Couldn't open this project: {error}</Callout></div> : (
        <div className="create-body">
          <div className="create-main">
            <ScriptStudio />
            {others.length > 0 && (
              <section className="recent">
                <div className="row"><h3 className="h3 grow">Continue a project</h3><Link to="/projects" className="btn btn-sm btn-ghost">All projects</Link></div>
                <div className="recent-grid">
                  {others.slice(0, 4).map((r) => (
                    <Link key={r.id} to={`/?p=${encodeURIComponent(r.id)}`} className="recent-card">
                      <span className="recent-thumb">{r.thumb ? <img src={fileUrl(r.id, r.thumb)} alt="" /> : <Clapperboard size={16} className="faint" />}</span>
                      <span className="col" style={{ gap: 0, minWidth: 0 }}><span className="h3 ellipsis">{r.name}</span><span className="meta">{r.lineCount} lines · {relativeTime(r.updatedAt)}</span></span>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>
          <aside className="rail" aria-label="Video configuration">
            <div className="rail-scroll">
              <StylePanel />
              <CastPanel />
              <SetPanel />
              <SubtitlePanel />
              <VoicePanel />
              <OutputPanel />
            </div>
            <GenerateBar onGenerate={() => void generate()} busy={busy} />
          </aside>
        </div>
      )}
      {menu.node}
    </div>
  );
}
