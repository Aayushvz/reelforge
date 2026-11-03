import { createPortal } from "react-dom";
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { useUI } from "@/stores/ui";

// ---------- Tooltip ----------

export function Tooltip({ label, kbd, children, side = "bottom" }: { label: ReactNode; kbd?: string; children: ReactNode; side?: "bottom" | "top" | "right" }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const show = () => {
    timer.current = setTimeout(() => {
      const r = ref.current?.firstElementChild?.getBoundingClientRect() ?? ref.current?.getBoundingClientRect();
      if (!r) return;
      setPos(side === "right" ? { x: r.right + 8, y: r.top + r.height / 2 } : side === "top" ? { x: r.left + r.width / 2, y: r.top - 8 } : { x: r.left + r.width / 2, y: r.bottom + 8 });
    }, 350);
  };
  const hide = () => { clearTimeout(timer.current); setPos(null); };
  useEffect(() => () => clearTimeout(timer.current), []);
  const transform = side === "right" ? "translateY(-50%)" : side === "top" ? "translate(-50%, -100%)" : "translateX(-50%)";
  return (
    <span ref={ref} onMouseEnter={show} onMouseLeave={hide} onMouseDown={hide} style={{ display: "contents" }}>
      {children}
      {pos && createPortal(
        <div className="tooltip" role="tooltip" style={{ left: pos.x, top: pos.y, transform }}>
          {label}{kbd && <span className="kbd">{kbd}</span>}
        </div>, document.body)}
    </span>
  );
}

// ---------- Menu ----------

export type MenuItem =
  | { label: string; icon?: ReactNode; onSelect: () => void; danger?: boolean; disabled?: boolean; kbd?: string; active?: boolean }
  | { separator: true }
  | { heading: string };

export function Menu({ anchor, items, onClose, align = "start" }: { anchor: DOMRect | { x: number; y: number }; items: MenuItem[]; onClose: () => void; align?: "start" | "end" }) {
  const ref = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<React.CSSProperties>({ visibility: "hidden" });
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    let x: number, y: number;
    if ("width" in anchor) { x = align === "end" ? anchor.right - w : anchor.left; y = anchor.bottom + 4; if (y + h > innerHeight - 8) y = anchor.top - h - 4; }
    else { x = anchor.x; y = anchor.y; if (y + h > innerHeight - 8) y = innerHeight - h - 8; }
    x = Math.max(8, Math.min(x, innerWidth - w - 8));
    setStyle({ left: x, top: Math.max(8, y) });
  }, [anchor, align]);
  useEffect(() => {
    const down = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) onClose(); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } };
    window.addEventListener("mousedown", down, true);
    window.addEventListener("keydown", key, true);
    window.addEventListener("blur", onClose);
    return () => { window.removeEventListener("mousedown", down, true); window.removeEventListener("keydown", key, true); window.removeEventListener("blur", onClose); };
  }, [onClose]);
  return createPortal(
    <div ref={ref} className="menu" role="menu" style={style}>
      {items.map((it, i) =>
        "separator" in it ? <div key={i} className="menu-sep" /> :
        "heading" in it ? <div key={i} className="menu-label">{it.heading}</div> :
        <button key={i} role="menuitem" className={`menu-item${it.danger ? " danger" : ""}${it.active ? " active" : ""}`} disabled={it.disabled}
          onClick={() => { onClose(); it.onSelect(); }}>
          {it.icon}<span className="ellipsis">{it.label}</span>{it.kbd && <span className="kbd-hint">{it.kbd}</span>}
        </button>)}
    </div>, document.body);
}

export function useMenu() {
  const [state, setState] = useState<{ anchor: DOMRect | { x: number; y: number }; items: MenuItem[]; align?: "start" | "end" } | null>(null);
  const close = () => setState(null);
  return {
    openAt: (anchor: DOMRect | { x: number; y: number }, items: MenuItem[], align?: "start" | "end") => setState({ anchor, items, align }),
    node: state ? <Menu anchor={state.anchor} items={state.items} align={state.align} onClose={close} /> : null,
  };
}

// ---------- Dialog / Drawer ----------

function useEscape(onClose: () => void) {
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
}

export function Dialog({ title, onClose, children, footer, wide, icon }: { title: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean; icon?: ReactNode }) {
  useEscape(onClose);
  return createPortal(
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`dialog${wide ? " wide" : ""}`} role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : undefined}>
        <div className="dialog-head">{icon}<h2 className="h2 grow">{title}</h2><button className="icon-btn sm" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
        <div className="dialog-body">{children}</div>
        {footer && <div className="dialog-foot">{footer}</div>}
      </div>
    </div>, document.body);
}

export function Confirm({ title, body, confirmLabel = "Confirm", danger, onConfirm, onClose }: { title: string; body: ReactNode; confirmLabel?: string; danger?: boolean; onConfirm: () => void; onClose: () => void }) {
  return (
    <Dialog title={title} onClose={onClose} footer={<>
      <button className="btn" onClick={onClose}>Cancel</button>
      <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} autoFocus onClick={() => { onConfirm(); onClose(); }}>{confirmLabel}</button>
    </>}>
      <div className="muted">{body}</div>
    </Dialog>
  );
}

export function Drawer({ onClose, children, width }: { onClose: () => void; children: ReactNode; width?: number }) {
  useEscape(onClose);
  return createPortal(<>
    <div className="drawer-scrim" onMouseDown={onClose} />
    <aside className="drawer" style={width ? { width: `min(${width}px, 100vw)` } : undefined}>{children}</aside>
  </>, document.body);
}

// ---------- Toasts ----------

export function Toasts() {
  const toasts = useUI((s) => s.toasts);
  const dismiss = useUI((s) => s.dismiss);
  return createPortal(
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.kind}`}>
          {t.kind === "ok" ? <CheckCircle2 size={16} /> : t.kind === "err" ? <AlertCircle size={16} /> : <Info size={16} />}
          <span className="grow">{t.text}</span>
          <button className="icon-btn xs" onClick={() => dismiss(t.id)} aria-label="Dismiss"><X size={12} /></button>
        </div>
      ))}
    </div>, document.body);
}
