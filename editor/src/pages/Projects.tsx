import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Search, LayoutGrid, List, MoreHorizontal, Film, Clapperboard, Copy, Archive, ArchiveRestore, Trash2, Pencil, Plus,
  FolderOpen, Scissors, FileText, RefreshCw,
} from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { relativeTime } from "@/lib/format";
import { Badge, Callout, Empty } from "@/components/ui/Feedback";
import { Confirm, Dialog, useMenu } from "@/components/ui/Overlay";
import { Segmented, Select } from "@/components/ui/Form";
import { toast } from "@/stores/ui";
import { useProject } from "@/stores/project";

type Tab = "all" | "drafts" | "rendered" | "edits" | "archived";
const TABS: { id: Tab; label: string; test: (p: ProjectSummary) => boolean }[] = [
  { id: "all", label: "All", test: (p) => !p.archived },
  { id: "drafts", label: "Drafts", test: (p) => !p.archived && p.kind === "generated" && p.status !== "rendered" },
  { id: "rendered", label: "Completed", test: (p) => !p.archived && p.status === "rendered" },
  { id: "edits", label: "Edit projects", test: (p) => !p.archived && p.kind === "blank" },
  { id: "archived", label: "Archived", test: (p) => p.archived },
];

const STATUS: Record<ProjectSummary["status"], { label: string; tone?: "info" | "ok" }> = { draft: { label: "Draft" }, stills: { label: "Stills ready", tone: "info" as const }, rendered: { label: "Rendered", tone: "ok" as const } };

export const openPath = (p: ProjectSummary) => (p.kind === "blank" ? `/editor/${encodeURIComponent(p.id)}` : `/?p=${encodeURIComponent(p.id)}`);

export function ProjectsPage() {
  const [list, setList] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("all");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<"updated" | "name">("updated");
  const [view, setView] = useState<"grid" | "list">(() => { try { return (localStorage.getItem("rf.projView") as "grid" | "list") ?? "grid"; } catch { return "grid"; } });
  const [renaming, setRenaming] = useState<ProjectSummary | null>(null);
  const [deleting, setDeleting] = useState<ProjectSummary | null>(null);
  const menu = useMenu();
  const nav = useNavigate();

  const refresh = () => { setError(null); api.projects().then(setList).catch((e) => setError(e.message)); };
  useEffect(refresh, []);
  useEffect(() => { try { localStorage.setItem("rf.projView", view); } catch { /* ignore */ } }, [view]);

  const shown = useMemo(() => {
    const t = TABS.find((x) => x.id === tab)!;
    const r = (list ?? []).filter(t.test).filter((p) => p.name.toLowerCase().includes(q.toLowerCase()));
    return sort === "name" ? [...r].sort((a, b) => a.name.localeCompare(b.name)) : r;
  }, [list, tab, q, sort]);

  const patchEditor = async (p: ProjectSummary, patch: Record<string, unknown>) => {
    const full = await api.project(p.id);
    await api.save(p.id, { editor: { ...full.editor, ...patch } });
    if (useProject.getState().id === p.id) await useProject.getState().load(p.id).catch(() => undefined);
  };

  const act = {
    rename: async (p: ProjectSummary, name: string) => { await patchEditor(p, { name }); toast("Renamed"); refresh(); },
    duplicate: async (p: ProjectSummary) => { const d = await api.duplicate(p.id); toast(`Duplicated as ${d.name}`); refresh(); },
    archive: async (p: ProjectSummary, archived: boolean) => { await patchEditor(p, { archived }); toast(archived ? "Archived" : "Restored"); refresh(); },
    remove: async (p: ProjectSummary) => {
      try { await api.remove(p.id); toast("Moved to projects/.trash"); refresh(); } catch (e) { toast((e as Error).message, "err"); }
    },
  };

  const openMenu = (p: ProjectSummary, rect: DOMRect | { x: number; y: number }) => menu.openAt(rect, [
    { label: "Open", icon: <FolderOpen size={14} />, onSelect: () => nav(openPath(p)) },
    { label: "Open in editor", icon: <Film size={14} />, onSelect: () => nav(`/editor/${encodeURIComponent(p.id)}`) },
    ...(p.kind === "generated" ? [{ label: "Render & approve", icon: <Clapperboard size={14} />, onSelect: () => nav(`/projects/${encodeURIComponent(p.id)}/render`) }] : []),
    { separator: true },
    { label: "Rename", icon: <Pencil size={14} />, onSelect: () => setRenaming(p) },
    { label: "Duplicate", icon: <Copy size={14} />, onSelect: () => void act.duplicate(p).catch((e) => toast(e.message, "err")) },
    p.archived
      ? { label: "Restore", icon: <ArchiveRestore size={14} />, onSelect: () => void act.archive(p, false) }
      : { label: "Archive", icon: <Archive size={14} />, onSelect: () => void act.archive(p, true) },
    { separator: true },
    { label: p.folder.startsWith("samples/") ? "Delete (sample, protected)" : "Delete", icon: <Trash2 size={14} />, danger: true, disabled: p.folder.startsWith("samples/"), onSelect: () => setDeleting(p) },
  ], "end");

  const counts = Object.fromEntries(TABS.map((t) => [t.id, (list ?? []).filter(t.test).length]));

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Projects</h1><div className="muted">Every reel and edit, saved in its project folder.</div></div>
          <Link to="/editor?new=1" className="btn"><Scissors size={14} />Blank edit</Link>
          <Link to="/?new=1" className="btn btn-primary"><Plus size={14} />New reel</Link>
        </div>
        <div className="tabs" role="tablist">
          {TABS.map((t) => <button key={t.id} role="tab" className="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>{t.label}{list && <span className="count">{counts[t.id]}</span>}</button>)}
        </div>
        <div className="toolbar">
          <div className="search"><Search size={14} /><input className="input" aria-label="Search projects" placeholder="Search projects" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <div className="grow" />
          <div style={{ width: 150 }}><Select value={sort} onChange={setSort} ariaLabel="Sort" options={[{ value: "updated", label: "Last edited" }, { value: "name", label: "Name" }]} /></div>
          <Segmented value={view} onChange={setView} options={[{ value: "grid", label: <LayoutGrid size={14} />, title: "Grid" }, { value: "list", label: <List size={14} />, title: "List" }]} />
        </div>

        {error ? <Callout tone="err">Couldn't load projects: {error} <button className="btn btn-sm" style={{ marginLeft: 8 }} onClick={refresh}><RefreshCw size={12} />Retry</button></Callout> :
         !list ? <div className="grid grid-cards">{Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton" style={{ height: 260 }} />)}</div> :
         shown.length === 0 ? (
          <Empty icon={<FolderOpen size={18} />} title={q ? "No projects match" : tab === "archived" ? "Nothing archived" : "No projects here yet"}
            action={!q && tab !== "archived" ? <><Link to="/?new=1" className="btn btn-primary"><Plus size={14} />New reel</Link><Link to="/editor?new=1" className="btn"><Scissors size={14} />Blank edit</Link></> : undefined}>
            {q ? "Try a different search." : "Projects you create appear here with their scripts, renders and edits."}
          </Empty>
        ) : view === "grid" ? (
          <div className="grid grid-cards">
            {shown.map((p) => (
              <div key={p.id} className="card interactive proj-card" onClick={() => nav(openPath(p))} onContextMenu={(e) => { e.preventDefault(); openMenu(p, { x: e.clientX, y: e.clientY }); }}>
                <div className="proj-thumb">
                  <ProjectThumb p={p} />
                  <div className="over"><Badge tone={STATUS[p.status].tone}>{STATUS[p.status].label}</Badge>
                    <button className="fav-btn" style={{ marginLeft: "auto" }} aria-label="Project actions" onClick={(e) => { e.stopPropagation(); openMenu(p, e.currentTarget.getBoundingClientRect()); }}><MoreHorizontal size={14} /></button></div>
                </div>
                <div className="body" style={{ padding: "10px 12px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
                  <span className="h3 ellipsis">{p.name}</span>
                  <span className="meta">{p.kind === "blank" ? "Edit project" : `${p.lineCount} lines · ${p.words} words`} · {p.ratio} · {relativeTime(p.updatedAt)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="panel" style={{ overflow: "hidden" }}>
            <div className="list-head"><span>Name</span><span>Type</span><span>Status</span><span>Format</span><span>Edited</span><span /></div>
            {shown.map((p) => (
              <div key={p.id} className="list-row" onClick={() => nav(openPath(p))} onContextMenu={(e) => { e.preventDefault(); openMenu(p, { x: e.clientX, y: e.clientY }); }}>
                <span className="row" style={{ minWidth: 0 }}><span className="list-thumb"><ProjectThumb p={p} /></span><span className="h3 ellipsis">{p.name}</span></span>
                <span className="muted">{p.kind === "blank" ? "Edit" : "Reel"}</span>
                <span><Badge tone={STATUS[p.status].tone}>{STATUS[p.status].label}</Badge></span>
                <span className="mono meta">{p.ratio}</span>
                <span className="meta">{relativeTime(p.updatedAt)}</span>
                <button className="icon-btn sm" aria-label="Project actions" onClick={(e) => { e.stopPropagation(); openMenu(p, e.currentTarget.getBoundingClientRect()); }}><MoreHorizontal size={14} /></button>
              </div>
            ))}
          </div>
        )}
      </div>
      {menu.node}
      {renaming && <RenameDialog p={renaming} onClose={() => setRenaming(null)} onSave={(n) => void act.rename(renaming, n)} />}
      {deleting && <Confirm title={`Delete ${deleting.name}?`} danger confirmLabel="Delete project" onClose={() => setDeleting(null)} onConfirm={() => void act.remove(deleting)}
        body={<>The folder moves to <span className="mono">projects/.trash</span>, so you can still recover it from disk.</>} />}
    </div>
  );
}

export function ProjectThumb({ p }: { p: ProjectSummary }) {
  if (p.thumb) return <img src={fileUrl(p.id, p.thumb)} alt="" loading="lazy" />;
  if (p.final) return <video src={fileUrl(p.id, p.final)} muted preload="metadata" />;
  const [w, h] = p.ratio.split(":").map(Number);
  return (
    <div className="proj-empty">
      <div className="proj-frame" style={{ aspectRatio: `${w}/${h}` }}>{p.kind === "blank" ? <Scissors size={16} /> : <FileText size={16} />}</div>
    </div>
  );
}

function RenameDialog({ p, onClose, onSave }: { p: ProjectSummary; onClose: () => void; onSave: (name: string) => void }) {
  const [name, setName] = useState(p.name);
  const ok = name.trim().length > 0;
  return (
    <Dialog title="Rename project" onClose={onClose} footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={!ok} onClick={() => { onSave(name.trim()); onClose(); }}>Rename</button></>}>
      <input className="input" autoFocus value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && ok) { onSave(name.trim()); onClose(); } }} />
      <div className="hint">The folder stays <span className="mono">{p.folder}</span>; only the display name changes.</div>
    </Dialog>
  );
}
