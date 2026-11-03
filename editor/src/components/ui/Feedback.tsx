import type { ReactNode } from "react";
import { AlertTriangle, Info, OctagonAlert } from "lucide-react";
import type { AssetStatus } from "@/data/catalog";

export function Badge({ tone, children, pip, title }: { tone?: "ok" | "warn" | "err" | "info" | "accent"; children: ReactNode; pip?: boolean; title?: string }) {
  return <span className={`badge${tone ? ` ${tone}` : ""}`} title={title}>{pip && <span className="pip" />}{children}</span>;
}

const STATUS: Record<AssetStatus, { tone?: "ok" | "info"; label: string; title: string }> = {
  available: { tone: "ok", label: "Renders today", title: "The pipeline can render this now" },
  "stand-in": { tone: "info", label: "Stand-in", title: "Rendered with the M1 stand-in for now" },
  planned: { label: "Planned", title: "Designed in the brief; not built in Blender yet. Renders use the stand-in." },
};
export function AssetBadge({ status }: { status: AssetStatus }) {
  const s = STATUS[status];
  return <Badge tone={s.tone} pip title={s.title}>{s.label}</Badge>;
}

export function Empty({ icon, title, children, action }: { icon: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <div className="h3" style={{ color: "var(--text-1)" }}>{title}</div>
      {children && <p>{children}</p>}
      {action && <div className="row" style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
}

export function Callout({ tone, children }: { tone?: "warn" | "err" | "info"; children: ReactNode }) {
  const Icon = tone === "err" ? OctagonAlert : tone === "warn" ? AlertTriangle : Info;
  return <div className={`callout${tone ? ` ${tone}` : ""}`}><Icon size={14} /><div>{children}</div></div>;
}

export const Spinner = () => <span className="spinner" aria-label="Loading" />;
