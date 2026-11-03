import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useRef } from "react";
import {
  Clapperboard, FolderOpen, Film, Library, Users, Mountain, Captions, AudioLines, Settings, Plus,
  PanelLeftClose, PanelLeftOpen, FilePlus2, Scissors,
} from "lucide-react";
import { useUI } from "@/stores/ui";
import { pipelineReady, useSystem } from "@/stores/system";
import { useMenu } from "./ui/Overlay";
import { Tooltip } from "./ui/Overlay";

export function LogoMark() {
  return (
    <svg className="logo-mark" viewBox="0 0 22 22" aria-hidden>
      <rect x="5.5" y="1.5" width="11" height="19" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <rect x="7.5" y="13" width="7" height="2.4" rx="1" fill="var(--accent)" />
      <rect x="9" y="16.6" width="4" height="1.4" rx=".7" fill="currentColor" opacity=".5" />
    </svg>
  );
}

const NAV = [
  { to: "/", label: "Create", icon: Clapperboard, end: true },
  { to: "/projects", label: "Projects", icon: FolderOpen },
  { to: "/editor", label: "Editor", icon: Film },
];
const ASSETS = [
  { to: "/library", label: "Asset Library", icon: Library },
  { to: "/characters", label: "Characters", icon: Users },
  { to: "/environments", label: "Environments", icon: Mountain },
  { to: "/subtitles", label: "Subtitle Templates", icon: Captions },
  { to: "/voices", label: "Voices", icon: AudioLines },
];

export function Sidebar() {
  const collapsed = useUI((s) => s.sidebarCollapsed);
  const toggle = useUI((s) => s.toggleSidebar);
  const status = useSystem((s) => s.status);
  const load = useSystem((s) => s.load);
  const nav = useNavigate();
  const menu = useMenu();
  const newBtn = useRef<HTMLButtonElement>(null);
  useEffect(() => { void load(); }, [load]);

  const ready = pipelineReady(status);
  const link = (l: { to: string; label: string; icon: typeof Film; end?: boolean }) => {
    const el = (
      <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => `sb-link${isActive ? " active" : ""}`}>
        <l.icon size={16} /><span>{l.label}</span>
      </NavLink>
    );
    return collapsed ? <Tooltip key={l.to} label={l.label} side="right">{el}</Tooltip> : el;
  };

  return (
    <aside className={`sidebar${collapsed ? " collapsed" : ""}`} aria-label="Main navigation">
      <div className="sb-top">
        {!collapsed && <div className="logo grow"><LogoMark /><span>ReelForge</span></div>}
        <Tooltip label={collapsed ? "Expand sidebar" : "Collapse sidebar"} kbd="[" side="right">
          <button className="icon-btn sm" onClick={toggle} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </Tooltip>
      </div>
      <button ref={newBtn} className={`btn ${collapsed ? "" : "btn-primary"} sb-new`} aria-label="New project"
        onClick={() => menu.openAt(newBtn.current!.getBoundingClientRect(), [
          { heading: "New project" },
          { label: "Reel from a script", icon: <FilePlus2 size={14} />, onSelect: () => nav("/?new=1") },
          { label: "Blank edit project", icon: <Scissors size={14} />, onSelect: () => nav("/editor?new=1") },
        ])}>
        <Plus size={16} />{!collapsed && "New project"}
      </button>
      <nav className="sb-nav">
        {NAV.map(link)}
        <div className="sb-group">Assets</div>
        {ASSETS.map(link)}
      </nav>
      <div className="sb-foot">
        {link({ to: "/settings", label: "Settings", icon: Settings })}
        <Tooltip label={status ? (ready ? "Pipeline ready: Blender, ffmpeg and reelforge found" : "Pipeline not set up. See Settings.") : "Checking pipeline"} side="right">
          <NavLink to="/settings" className="sb-link" style={{ height: 28 }}>
            <span className="sys-dot" style={{ background: !status ? "var(--text-4)" : ready ? "var(--ok)" : "var(--warn)", display: "block" }} />
            {!collapsed && <span className="meta">{!status ? "Checking…" : ready ? "Render engine ready" : "Render engine not set up"}</span>}
          </NavLink>
        </Tooltip>
      </div>
      {menu.node}
    </aside>
  );
}
