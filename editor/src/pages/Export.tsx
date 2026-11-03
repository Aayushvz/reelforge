// Export studio: output settings, the rendered file, download and export history.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Film, Info, Play, FileVideo } from "lucide-react";
import { fileUrl } from "@/lib/api";
import { RATIOS, FPS_OPTIONS, type Ratio } from "@/lib/types";
import { duration, relativeTime } from "@/lib/format";
import { useProject } from "@/stores/project";
import { FieldRow, Segmented, Select } from "@/components/ui/Form";
import { Badge, Callout } from "@/components/ui/Feedback";
import "./render.css";

export function ExportPage() {
  const { id = "" } = useParams();
  const { load, editor, files, setEditor, setPerformance, performance, error } = useProject();
  const [meta, setMeta] = useState<{ duration: number; w: number; h: number; size: number | null } | null>(null);
  useEffect(() => { void load(id); }, [id, load]);
  const final = files.finals[0];
  const url = final ? fileUrl(id, `out/${final}`) : null;

  useEffect(() => {
    if (!url) { setMeta(null); return; }
    const v = document.createElement("video");
    v.preload = "metadata";
    v.onloadedmetadata = async () => {
      let size: number | null = null;
      try { size = Number((await fetch(url, { method: "HEAD" })).headers.get("content-length")) || null; } catch { /* size unknown */ }
      setMeta({ duration: v.duration, w: v.videoWidth, h: v.videoHeight, size });
    };
    v.src = url;
  }, [url]);

  const out = editor.output;
  const setRatio = (ratio: Ratio) => {
    setEditor((e) => ({ ...e, output: { ...e.output, ratio, resolution: [...RATIOS[ratio]] as [number, number] } }));
    if (performance) setPerformance((p) => ({ ...p, ratio }));
  };
  const stale = final && !final.includes(out.ratio.replace(":", "x"));

  if (error) return <div className="page"><div className="page-inner"><Callout tone="err">Couldn't open this project: {error}</Callout></div></div>;
  return (
    <div className="page">
      <div className="page-inner" style={{ maxWidth: 1100 }}>
        <div className="page-head">
          <Link to={editor.kind === "blank" ? `/editor/${encodeURIComponent(id)}` : `/?p=${encodeURIComponent(id)}`} className="icon-btn" aria-label="Back"><ArrowLeft size={16} /></Link>
          <div className="grow"><div className="eyebrow">Export</div><h1 className="h1">{editor.name}</h1></div>
          <Link className="btn" to={`/editor/${encodeURIComponent(id)}`}><Film size={14} />Back to editor</Link>
        </div>
        <div className="render-grid" style={{ gridTemplateColumns: "360px minmax(0, 1fr)" }}>
          <section className="panel rp">
            <h2 className="h3">Settings</h2>
            <FieldRow label="Aspect"><Segmented value={out.ratio} onChange={setRatio} options={(Object.keys(RATIOS) as Ratio[]).map((r) => ({ value: r, label: r }))} /></FieldRow>
            <FieldRow label="Resolution"><span className="mono">{out.resolution[0]} × {out.resolution[1]}</span></FieldRow>
            <FieldRow label="Frame rate"><Select size="sm" value={String(out.fps)} onChange={(v) => { setEditor((e) => ({ ...e, output: { ...e.output, fps: Number(v) } })); if (performance) setPerformance((p) => ({ ...p, fps: Number(v) })); }}
              options={FPS_OPTIONS.map((f) => ({ value: String(f), label: `${f} fps` }))} /></FieldRow>
            <FieldRow label="Format"><span className="mono">MP4 · H.264 + AAC</span></FieldRow>
            <FieldRow label="Quality"><Segmented value={out.quality} onChange={(q) => setEditor((e) => ({ ...e, output: { ...e.output, quality: q } }))} options={[{ value: "draft", label: "Draft" }, { value: "final", label: "Final" }]} /></FieldRow>
            <FieldRow label="Captions"><span className="row"><Badge tone="ok">Burned in</Badge><span className="meta">The pipeline always burns them in</span></span></FieldRow>
            <FieldRow label="Audio"><span className="meta">Dialogue mix, loudness normalised to −14 LUFS</span></FieldRow>
            <div className="callout"><Info size={14} /><div>The export is the pipeline's final render. Timeline edits in the editor are saved with the project but aren't applied by the renderer yet.</div></div>
            {editor.kind === "generated" && (
              <Link className="btn btn-primary" to={`/projects/${encodeURIComponent(id)}/render?start=full`}><Play size={14} />{final ? "Render again with these settings" : "Render final video"}</Link>
            )}
          </section>

          <section className="panel rp">
            <h2 className="h3">Output</h2>
            {final && url ? <>
              <div className="row" style={{ alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
                <video src={url} controls preload="metadata" style={{ width: 260, maxHeight: 460, borderRadius: 6, background: "#000" }} />
                <div className="col grow" style={{ gap: 12, minWidth: 220 }}>
                  <div className="row"><FileVideo size={16} className="faint" /><span className="h3 mono">{final}</span>{stale && <Badge tone="warn">Older aspect ratio</Badge>}</div>
                  <dl className="kv">
                    <dt>Duration</dt><dd className="mono">{meta ? duration(meta.duration) : "…"}</dd>
                    <dt>Resolution</dt><dd className="mono">{meta ? `${meta.w} × ${meta.h}` : "…"}</dd>
                    <dt>File size</dt><dd className="mono">{meta?.size ? `${(meta.size / 1048576).toFixed(1)} MB` : "…"}</dd>
                    <dt>Location</dt><dd className="mono meta" style={{ wordBreak: "break-all" }}>{id.replace("~", "/")}/out/{final}</dd>
                  </dl>
                  <a className="btn btn-primary" href={url} download={`${editor.name.replace(/[^\w\- ]+/g, "")}.mp4`}
                    onClick={() => setEditor((e) => ({ ...e, exports: [...e.exports, { at: new Date().toISOString(), file: final, ratio: out.ratio, resolution: out.resolution, burnIn: true }].slice(-30) }))}>
                    <Download size={14} />Download MP4</a>
                </div>
              </div>
            </> : (
              <div className="result-empty"><Film size={18} className="faint" /><span className="meta">{editor.kind === "blank" ? "Exporting edit projects needs a timeline renderer, which isn't built yet. Your edit is saved." : "No final render yet. Render the video, then download it here."}</span></div>
            )}
            {editor.exports.length > 0 && <>
              <div className="divider" />
              <h3 className="h3">Export history</h3>
              <ul className="history">{[...editor.exports].reverse().map((x, i) => <li key={i} className="row"><Download size={12} className="faint" /><span className="grow mono">{x.file}</span><span className="meta">{x.ratio}</span><span className="meta">{relativeTime(x.at)}</span></li>)}</ul>
            </>}
          </section>
        </div>
      </div>
    </div>
  );
}
