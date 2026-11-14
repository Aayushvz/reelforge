// The auto-cover after a render: the drafted cover, a download, and a way into the Thumbnail Generator.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, ImagePlay } from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import { applyVariant, download, drawCover, ensureFonts, fileSafe, grabFrame, loadImage, savedStyle, SIZE_PRESETS, renderCover, type CoverDoc, type CoverDraft } from "@/lib/cover";
import { toast } from "@/stores/ui";
import "@/pages/thumbnails/thumbnails.css";

export function CoverCard({ projectId, version }: { projectId: string; version?: string | number }) {
  const [state, setState] = useState<{ draft: CoverDraft; doc: CoverDoc; frame: HTMLCanvasElement | HTMLImageElement } | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const nav = useNavigate();

  useEffect(() => {
    let live = true;
    setState(null);
    (async () => {
      const draft = await api.cover(projectId);
      const v = draft.variants[0];
      if (!v) return;
      const base = savedStyle();
      const preset = SIZE_PRESETS.find((p) => p.w === draft.width && p.h === draft.height);
      const doc = applyVariant({ ...base, preset: preset?.id ?? "custom", width: draft.width, height: draft.height }, v);
      // a clean rendered frame when there is one (no burned-in captions), else the final video's frame
      const grab = () => grabFrame(fileUrl(projectId, draft.video, version), v.time);
      const [frame] = await Promise.all([
        v.still ? loadImage(fileUrl(projectId, v.still, version)).catch(grab) : grab(), ensureFonts(doc)]);
      if (live) setState({ draft, doc, frame });
    })().catch(() => undefined); // no draft: no card
    return () => { live = false; };
  }, [projectId, version]);

  useEffect(() => {
    const c = canvas.current;
    if (!c || !state) return;
    const W = 216, H = Math.round(W * state.doc.height / state.doc.width);
    c.width = W; c.height = H;
    drawCover(c.getContext("2d")!, state.doc, state.frame, W, H);
  }, [state]);

  if (!state) return null;
  const { doc, frame } = state;
  const title = doc.lines.map((l) => l.text).join(" ");
  const save = async () => {
    try { download(await renderCover(doc, frame, "image/png"), `${fileSafe(title)}-${doc.width}x${doc.height}.png`); }
    catch (e) { toast((e as Error).message, "err"); }
  };
  return (
    <div className="cover-card" role="group" aria-label="Drafted cover">
      <canvas ref={canvas} role="img" aria-label={`Drafted cover: ${title}`} />
      <div className="cover-body">
        <span className="label">Cover ready</span>
        <span className="meta">Drafted from the script: “{title}”, {doc.width}×{doc.height}. Download it, or open it to change the frame, text or size.</span>
        <div className="cover-actions">
          <button className="btn btn-sm btn-primary" onClick={() => void save()}><Download size={12} />Download PNG</button>
          <button className="btn btn-sm" onClick={() => nav(`/thumbnails?project=${encodeURIComponent(projectId)}`)}><ImagePlay size={12} />Edit in Thumbnail Generator</button>
        </div>
      </div>
    </div>
  );
}
