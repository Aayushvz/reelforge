import { Check, CloudOff, Loader2 } from "lucide-react";
import { useProject } from "@/stores/project";
import { Tooltip } from "./ui/Overlay";

export function SaveStatus() {
  const state = useProject((s) => s.saveState);
  const err = useProject((s) => s.saveError);
  const id = useProject((s) => s.id);
  const retry = useProject((s) => s.saveNow);
  if (state === "error") return (
    <Tooltip label={err ?? "Save failed"}><button className="btn btn-sm btn-ghost" style={{ color: "var(--err)" }} onClick={() => void retry()}><CloudOff size={14} />Not saved · retry</button></Tooltip>
  );
  const label = state === "saving" || state === "pending" ? "Saving…" : state === "saved" ? "Saved" : id ? "All changes saved" : "Draft · saves on first edit";
  return (
    <span className="row meta" style={{ gap: 6 }} aria-live="polite">
      {state === "saving" || state === "pending" ? <Loader2 size={12} className="spin" /> : id ? <Check size={12} /> : null}{label}
    </span>
  );
}
