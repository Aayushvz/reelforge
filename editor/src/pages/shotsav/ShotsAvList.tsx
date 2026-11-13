// Shots-AV Animation: the list of desk-reel projects, and New (blank or from one of our starter scripts).
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessagesSquare, Plus, RefreshCw } from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { relativeTime } from "@/lib/format";
import { Badge, Callout, Empty } from "@/components/ui/Feedback";
import { toast } from "@/stores/ui";
import { BUDDY, HERO, STARTERS, makeLine, newPerformance } from "@/lib/shotsav";
import "./shotsav.css";

export async function createAvProject(name: string, starter?: (typeof STARTERS)[number]) {
  const perf = starter
    ? newPerformance(starter.buddy, starter.room, starter.lines.map(([who, text, emo], i) => makeLine(who === HERO ? HERO : BUDDY, text, i, emo)))
    : newPerformance();
  const p = await api.create({ name, performance: perf, editor: { name, kind: "generated", style: "shots-av" } });
  return p.id;
}

export function ShotsAvListPage() {
  const [list, setList] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const refresh = () => { setError(null); api.projects().then(setList).catch((e) => setError(e.message)); };
  useEffect(refresh, []);
  const mine = useMemo(() => (list ?? []).filter((p) => p.style === "shots-av" && !p.archived), [list]);

  const make = async (name: string, starter?: (typeof STARTERS)[number]) => {
    setBusy(true);
    try { nav(`/shots-av/${encodeURIComponent(await createAvProject(name, starter))}`); }
    catch (e) { toast(`Couldn't create the project: ${(e as Error).message}`, "err"); }
    finally { setBusy(false); }
  };

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow">
            <h1 className="h1">Shots-AV Animation</h1>
            <div className="muted">You at your desk, talking to a small AI buddy. Two speakers, five camera set-ups, cut on the line.</div>
          </div>
          <button className="btn btn-primary" disabled={busy} onClick={() => void make("Untitled desk reel")}><Plus size={14} />New</button>
        </div>
        {error ? <Callout tone="err">Couldn't load projects: {error} <button className="btn btn-sm" style={{ marginLeft: 8 }} onClick={refresh}><RefreshCw size={12} />Retry</button></Callout> :
         !list ? <div className="grid grid-cards">{Array.from({ length: 3 }, (_, i) => <div key={i} className="skeleton" style={{ height: 240 }} />)}</div> :
         !mine.length ? (
          <Empty icon={<MessagesSquare size={20} />} title="No desk reels yet"
            action={<button className="btn btn-primary" disabled={busy} onClick={() => void make("Untitled desk reel")}><Plus size={14} />New blank script</button>}>
            Start from scratch, or pick one of the scripts below and change it.
          </Empty>
        ) : (
          <div className="grid grid-cards">
            {mine.map((p) => (
              <button key={p.id} className="card interactive av-proj" onClick={() => nav(`/shots-av/${encodeURIComponent(p.id)}`)}>
                <span className="av-proj-frame">
                  {p.thumb ? <img src={fileUrl(p.id, p.thumb)} alt="" /> : <MessagesSquare size={18} />}
                </span>
                <span className="av-proj-body">
                  <span className="h3 ellipsis">{p.name}</span>
                  <span className="meta">{p.lineCount} lines · {relativeTime(p.updatedAt)}</span>
                  {p.status === "rendered" && <Badge tone="ok">Rendered</Badge>}
                </span>
              </button>
            ))}
          </div>
        )}
        <h2 className="h2" style={{ margin: "32px 0 12px" }}>Start from a script</h2>
        <div className="av-starters">
          {STARTERS.map((s) => (
            <button key={s.id} className="card interactive av-starter" disabled={busy} onClick={() => void make(s.name, s)}>
              <span className="h3">{s.name}</span>
              <span className="meta">{s.lines.length} lines</span>
              <span className="av-starter-lines">
                {s.lines.slice(0, 3).map(([who, text], i) => (
                  <span key={i} className={`av-bubble ${who === HERO ? "me" : "buddy"}`}>{text}</span>
                ))}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
