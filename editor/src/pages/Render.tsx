// Generation workspace: readiness checks, the stills → approve → full render flow, live job status.
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, Check, X, Cpu, Film, Image as ImageIcon, Play, RefreshCw, Square, ThumbsUp, MessageSquareWarning, Upload, Clock, Terminal, CircleDashed, CheckCircle2, AlertCircle,
} from "lucide-react";
import { api, fileUrl, jobEventsUrl } from "@/lib/api";
import type { Job } from "@/lib/types";
import { validate } from "@/lib/script";
import { duration, relativeTime } from "@/lib/format";
import { lineVoiced, useProject } from "@/stores/project";
import { pipelineReady, useSystem } from "@/stores/system";
import { Badge, Callout, Spinner } from "@/components/ui/Feedback";
import { Segmented } from "@/components/ui/Form";
import { toast } from "@/stores/ui";
import "./render.css";

// What the pipeline does, in order (reelforge/cli.py run()). The CLI only reports the
// Blender frame counter, so stages are inferred from that rather than timed.
const STAGES = [
  { id: "prep", label: "Preparing voice, timing and face tracks", detail: "Voice import, Whisper alignment, timeline, 52-channel face tracks" },
  { id: "direct", label: "Directing shots, moods and captions", detail: "Shot list, mood light keys, captions.ass, render_plan.json" },
  { id: "render", label: "Rendering in Blender", detail: "Character, set, mood lighting, depth-of-field cameras" },
  { id: "finish", label: "Compositing the final video", detail: "Halation, grade, vignette, grain, captions, −14 LUFS" },
] as const;

type Live = { job: Job | null; frame: number | null; nFrames: number | null; log: string[] };

export function RenderPage() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const { load, performance, editor, files, reloadFiles, setEditor, loading, error } = useProject();
  const system = useSystem((s) => s.status);
  const loadSystem = useSystem((s) => s.load);
  const [live, setLive] = useState<Live>({ job: null, frame: null, nFrames: null, log: [] });
  const [draft, setDraft] = useState(true);
  const cinema = useProject((st) => st.performance?.look === "cinema");
  // follow the quality chosen on Create once the project is loaded
  useEffect(() => { if (!loading) setDraft(editor.output.quality !== "final"); }, [loading, editor.output.quality]);
  const [now, setNow] = useState(Date.now());
  const [showLog, setShowLog] = useState(false);
  const started = useRef(false);
  // "Generate video" may arrive while voices are still being generated: start once they're ready.
  const [pending, setPending] = useState<"stills" | "full" | null>(null);

  useEffect(() => { void load(id); void loadSystem(); }, [id, load, loadSystem]);
  useEffect(() => { if (!live.job || live.job.status !== "running") return; const t = setInterval(() => setNow(Date.now()), 500); return () => clearInterval(t); }, [live.job]);

  // Re-attach to a job that's still running for this project.
  useEffect(() => { api.jobs(id).then((js) => { const r = js.find((j) => j.status === "running"); if (r) follow(r); }).catch(() => undefined); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const issues = validate(performance);
  const lines = performance?.lines ?? [];
  const voices = useProject((s) => s.voices);
  const missing = lines.filter((l) => !lineVoiced(voices[l.id]));
  const ready = pipelineReady(system) && issues.length === 0 && missing.length === 0 && lines.length > 0;
  const running = live.job?.status === "running";

  function follow(job: Job) {
    setLive({ job, frame: null, nFrames: null, log: job.log ?? [] });
    const es = new EventSource(jobEventsUrl(job.id));
    es.addEventListener("log", (e) => {
      const line = JSON.parse((e as MessageEvent).data) as string;
      const fra = line.match(/Fra:\s*(\d+)/);
      setLive((s) => ({ ...s, log: [...s.log.slice(-400), line], frame: fra ? Number(fra[1]) : s.frame }));
    });
    es.addEventListener("status", (e) => {
      const j = JSON.parse((e as MessageEvent).data) as Job;
      setLive((s) => ({ ...s, job: j }));
      if (j.status !== "running") {
        es.close();
        void reloadFiles();
        void load(id).catch(() => undefined);
        if (j.status === "done") toast(j.stage === "stills" ? "Stills rendered. Review them below." : "Final video rendered");
        if (j.status === "failed") toast("Render failed. See the log.", "err");
      }
    });
    es.onerror = () => es.close();
    // shot count / frame count, once the plan is written
    const poll = setInterval(async () => {
      try {
        const r = await fetch(fileUrl(id, "out/render_plan.json"), { cache: "no-store" });
        if (r.ok) { const p = await r.json(); setLive((s) => ({ ...s, nFrames: job.stage === "stills" ? p.shots.length : p.n_frames })); clearInterval(poll); }
      } catch { /* not written yet */ }
    }, 1500);
    setTimeout(() => clearInterval(poll), 120_000);
  }

  const start = async (stage: "stills" | "full") => {
    try { follow(await api.run(id, stage, draft)); }
    catch (e) { toast((e as Error).message, "err"); }
  };

  useEffect(() => {
    const want = params.get("start");
    if (!want || started.current || loading || !system) return;
    started.current = true;
    setParams({}, { replace: true });
    setPending(want === "full" ? "full" : "stills");
  }, [params, loading, system, ready]); // eslint-disable-line react-hooks/exhaustive-deps

  const voicing = lines.some((l) => voices[l.id]?.status === "generating");
  const voiceFailed = lines.some((l) => voices[l.id]?.status === "error");
  useEffect(() => {
    if (!pending) return;
    if (ready && !running) { setPending(null); void start(pending); return; }
    if (!voicing && (voiceFailed || issues.length > 0 || (system && !pipelineReady(system)))) setPending(null);
  }, [pending, ready, running, voicing, voiceFailed]); // eslint-disable-line react-hooks/exhaustive-deps

  // Stage inference: honest, from what the process has actually printed.
  const stageIdx = useMemo(() => {
    const j = live.job;
    if (!j) return -1;
    if (j.status === "done") return STAGES.length;
    if (live.log.some((l) => /Fra:/.test(l)) || live.frame !== null) {
      if (j.stage === "full" && live.nFrames && live.frame !== null && live.frame >= live.nFrames) return 3;
      return 2;
    }
    if (live.nFrames) return 2;
    return 0;
  }, [live]);

  const approvals = editor.approvals;
  const setApproval = (shot: string, v: "approved" | "changes" | null) =>
    setEditor((e) => { const a = { ...e.approvals }; if (v) a[shot] = v; else delete a[shot]; return { ...e, approvals: a }; });
  const approvedCount = files.stills.filter((s) => approvals[s] === "approved").length;
  const final = files.finals[0];

  if (error) return <div className="page"><div className="page-inner"><Callout tone="err">Couldn't open this project: {error}</Callout></div></div>;

  return (
    <div className="page">
      <div className="page-inner" style={{ maxWidth: 1180 }}>
        <div className="page-head">
          <Link to={`/?p=${encodeURIComponent(id)}`} className="icon-btn" aria-label="Back to project"><ArrowLeft size={16} /></Link>
          <div className="grow"><div className="eyebrow">Generate</div><h1 className="h1">{editor.name}</h1></div>
          <Link className="btn" to={`/editor/${encodeURIComponent(id)}`}><Film size={14} />Open in editor</Link>
        </div>

        <div className="render-grid">
          <div className="col" style={{ gap: 16 }}>
            {/* readiness */}
            <section className="panel rp">
              <h2 className="h3">Before rendering</h2>
              <ul className="checks">
                <Check2 ok={Boolean(system?.reelforge)} label="reelforge pipeline installed" fix={<>Run <span className="mono">pip install -e ".[dev,align]"</span> in the repo's <span className="mono">.venv</span>. See Settings.</>} />
                <Check2 ok={Boolean(system?.blender)} label="Blender 4.5 found" fix={<>Put the portable build in <span className="mono">tools/blender-4.5/</span> and its path in <span className="mono">tools/blender_path.txt</span>.</>} />
                <Check2 ok={Boolean(system?.ffmpeg)} label="ffmpeg on PATH" fix="Install ffmpeg and make sure ffmpeg and ffprobe run in a terminal." />
                <Check2 ok={issues.length === 0 && lines.length > 0} label={lines.length ? "Script is valid" : "Script has lines"} fix={issues[0]?.message ?? "Write the script on Create."} />
                <Check2 ok={missing.length === 0 && lines.length > 0} label={`Voice lines ready (${lines.length - missing.length}/${lines.length})`}
                  fix={voicing ? <>Generating {missing.map((l) => l.id).join(", ")} with ElevenLabs…{pending ? " The render starts when they're ready." : ""}</>
                    : <>Not voiced: {missing.map((l) => l.id).join(", ")}. Check the key in <Link className="link" to="/settings">Settings</Link> and retry on <Link className="link" to="/voices">Voices</Link>.</>} />
              </ul>
              {!system && <div className="row meta"><Spinner />Checking the render engine…</div>}
            </section>

            {/* stages */}
            <section className="panel rp">
              <div className="row">
                <h2 className="h3 grow">Render</h2>
                <Badge tone="ok"><Cpu size={11} />Local · free</Badge>
              </div>
              <div className="row" style={{ gap: 10 }}>
                <span className="label">Quality</span>
                <Segmented value={draft ? "draft" : "final"} onChange={(v) => setDraft(v === "draft")} options={cinema
                  ? [{ value: "draft", label: "Draft · half size" }, { value: "final", label: "Final · ray-traced" }]
                  : [{ value: "draft", label: "Draft · 16 samples" }, { value: "final", label: "Final · 64 samples" }]} />
              </div>
              <div className="stage-cards">
                <div className="stage-card">
                  <div className="row"><ImageIcon size={16} className="faint" /><span className="h3 grow">1 · Stills</span>{files.stills.length > 0 && <Badge tone="ok">{files.stills.length} rendered</Badge>}</div>
                  <span className="meta">One frame per shot, to check framing, light and mood before spending time on the full render.</span>
                  <button className="btn btn-primary" disabled={!ready || running} onClick={() => void start("stills")}><Play size={14} />{files.stills.length ? "Re-render stills" : "Render stills"}</button>
                </div>
                <div className="stage-card">
                  <div className="row"><Film size={16} className="faint" /><span className="h3 grow">2 · Full video</span>{final && <Badge tone="ok">Rendered</Badge>}</div>
                  <span className="meta">Every frame, then the finishing pass and captions. {files.stills.length > 0 && approvedCount < files.stills.length ? `${approvedCount}/${files.stills.length} stills approved.` : ""}</span>
                  <button className={`btn ${files.stills.length ? "btn-primary" : ""}`} disabled={!ready || running} onClick={() => void start("full")}><Play size={14} />{final ? "Re-render video" : "Render video"}</button>
                </div>
              </div>

              {live.job && (
                <div className="job">
                  <div className="row">
                    {running ? <Spinner /> : live.job.status === "done" ? <CheckCircle2 size={16} style={{ color: "var(--ok)" }} /> : <AlertCircle size={16} style={{ color: "var(--err)" }} />}
                    <span className="h3 grow">{live.job.stage === "stills" ? "Rendering stills" : "Rendering full video"} · {live.job.draft ? "draft" : "final"}
                      {live.job.status !== "running" && ` · ${live.job.status}`}</span>
                    <span className="meta mono"><Clock size={12} style={{ verticalAlign: -2 }} /> {duration(((live.job.endedAt ?? now) - live.job.startedAt) / 1000)}</span>
                    {running && <button className="btn btn-sm btn-danger" onClick={() => void api.cancel(live.job!.id)}><Square size={12} />Cancel</button>}
                    {live.job.status === "failed" && <button className="btn btn-sm" onClick={() => void start(live.job!.stage)}><RefreshCw size={12} />Retry</button>}
                  </div>
                  <ol className="stages">
                    {STAGES.filter((s) => live.job!.stage === "full" || s.id !== "finish").map((s, i) => {
                      const state = live.job!.status === "failed" || live.job!.status === "cancelled" ? (i < stageIdx ? "done" : i === stageIdx ? "failed" : "todo")
                        : i < stageIdx ? "done" : i === stageIdx ? "now" : "todo";
                      return (
                        <li key={s.id} className={`stage ${state}`}>
                          <span className="stage-icon">{state === "done" ? <Check size={12} /> : state === "now" ? <Spinner /> : state === "failed" ? <X size={12} /> : <CircleDashed size={12} />}</span>
                          <span className="col grow" style={{ gap: 0 }}><span>{s.label}</span><span className="meta">{s.detail}</span></span>
                          {s.id === "render" && state === "now" && live.nFrames && live.frame !== null && (
                            <span className="meta mono">{live.job!.stage === "stills" ? "" : `frame ${live.frame} / ${live.nFrames}`}</span>
                          )}
                        </li>
                      );
                    })}
                  </ol>
                  {live.job.stage === "full" && stageIdx === 2 && live.nFrames && live.frame !== null && (
                    <div className="bar"><span style={{ transform: `scaleX(${Math.min(1, live.frame / live.nFrames)})` }} /></div>
                  )}
                  {live.job.error && <Callout tone="err"><span className="mono" style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>{live.job.error}</span></Callout>}
                  <button className="btn btn-sm btn-ghost" onClick={() => setShowLog(!showLog)}><Terminal size={12} />{showLog ? "Hide" : "Show"} log ({live.log.length} lines)</button>
                  {showLog && <pre className="log">{live.log.slice(-200).join("\n") || "No output yet."}</pre>}
                </div>
              )}
            </section>

            {/* approval */}
            <section className="panel rp">
              <div className="row">
                <h2 className="h3 grow">Approve stills</h2>
                {files.stills.length > 0 && <span className="meta">{approvedCount} of {files.stills.length} approved</span>}
                {files.stills.length > 0 && <button className="btn btn-sm" onClick={() => setEditor((e) => ({ ...e, approvals: Object.fromEntries(files.stills.map((s) => [s, "approved" as const])) }))}><ThumbsUp size={12} />Approve all</button>}
              </div>
              {files.stills.length === 0 ? <div className="meta">Stills appear here after the first stills render. Approve each shot, or flag it for changes.</div> : (
                <div className="stills">
                  {files.stills.map((s, i) => {
                    const v = approvals[s];
                    return (
                      <figure key={s} className={`still ${v ?? ""}`}>
                        <img src={fileUrl(id, `out/stills/${s}`, live.job?.endedAt)} alt={`Shot ${i + 1}`} />
                        <figcaption className="row">
                          <span className="mono meta grow">Shot {i + 1}</span>
                          <button className="icon-btn xs" aria-pressed={v === "approved"} title="Approve" onClick={() => setApproval(s, v === "approved" ? null : "approved")} style={v === "approved" ? { color: "var(--ok)" } : undefined}><ThumbsUp size={12} /></button>
                          <button className="icon-btn xs" aria-pressed={v === "changes"} title="Request changes" onClick={() => setApproval(s, v === "changes" ? null : "changes")} style={v === "changes" ? { color: "var(--warn)" } : undefined}><MessageSquareWarning size={12} /></button>
                        </figcaption>
                      </figure>
                    );
                  })}
                </div>
              )}
              {files.stills.length > 0 && <div className="hint">Shots flagged for changes: adjust the script lines, moods or shot framing, then re-render stills. The pipeline re-renders every still in one pass; single-shot regeneration needs a pipeline change.</div>}
            </section>
          </div>

          {/* result + history */}
          <aside className="col" style={{ gap: 16 }}>
            <section className="panel rp">
              <h2 className="h3">Result</h2>
              {final ? <>
                <video className="result-video" src={fileUrl(id, `out/${final}`, live.job?.endedAt)} controls preload="metadata" />
                <div className="col" style={{ gap: 6 }}>
                  <Link className="btn btn-primary" to={`/editor/${encodeURIComponent(id)}`}><Film size={14} />Edit video</Link>
                  <Link className="btn" to={`/projects/${encodeURIComponent(id)}/export`}><Upload size={14} />Export</Link>
                  <button className="btn btn-ghost" onClick={() => nav(`/?p=${encodeURIComponent(id)}`)}>Return to project</button>
                </div>
              </> : <div className="result-empty"><Film size={18} className="faint" /><span className="meta">The final video shows here after the full render.</span></div>}
            </section>
            <section className="panel rp">
              <h2 className="h3">History</h2>
              {editor.history.length === 0 ? <span className="meta">No renders yet.</span> : (
                <ul className="history">
                  {[...editor.history].reverse().slice(0, 12).map((h, i) => (
                    <li key={i} className="row">
                      {h.status === "done" ? <Check size={12} style={{ color: "var(--ok)" }} /> : <X size={12} style={{ color: "var(--err)" }} />}
                      <span className="grow">{h.stage === "stills" ? "Stills" : "Full video"} · {h.draft ? "draft" : "final"}</span>
                      <span className="meta mono">{duration(h.ms / 1000)}</span>
                      <span className="meta">{relativeTime(h.at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

function Check2({ ok, label, fix }: { ok: boolean; label: string; fix: React.ReactNode }) {
  return (
    <li className={`check ${ok ? "ok" : "no"}`}>
      <span className="check-icon">{ok ? <Check size={12} /> : <X size={12} />}</span>
      <span className="col" style={{ gap: 0 }}><span>{label}</span>{!ok && <span className="meta">{fix}</span>}</span>
    </li>
  );
}
