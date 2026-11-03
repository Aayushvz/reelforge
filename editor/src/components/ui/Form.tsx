import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Tooltip } from "./Overlay";

export function IconButton({ label, kbd, onClick, children, size, on, disabled, bordered, side }: {
  label: string; kbd?: string; onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void; children: ReactNode;
  size?: "sm" | "xs"; on?: boolean; disabled?: boolean; bordered?: boolean; side?: "bottom" | "top" | "right";
}) {
  return (
    <Tooltip label={label} kbd={kbd} side={side}>
      <button className={`icon-btn${size ? ` ${size}` : ""}${on ? " on" : ""}${bordered ? " bordered" : ""}`} aria-label={label} aria-pressed={on} disabled={disabled} onClick={onClick}>
        {children}
      </button>
    </Tooltip>
  );
}

export function Segmented<T extends string | number>({ value, options, onChange, full, size }: {
  value: T; options: { value: T; label: ReactNode; title?: string }[]; onChange: (v: T) => void; full?: boolean; size?: "sm";
}) {
  return (
    <div className={`seg${full ? " full" : ""}`} role="group" style={size === "sm" ? { padding: 1 } : undefined}>
      {options.map((o) => (
        <button key={String(o.value)} type="button" aria-pressed={o.value === value} title={o.title} onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

export function Select<T extends string>({ value, options, onChange, size, ariaLabel, disabled }: {
  value: T; options: { value: T; label: string; disabled?: boolean }[]; onChange: (v: T) => void; size?: "sm"; ariaLabel?: string; disabled?: boolean;
}) {
  return (
    <select className={`select${size ? ` ${size}` : ""}`} value={value} aria-label={ariaLabel} disabled={disabled} onChange={(e) => onChange(e.target.value as T)}>
      {options.map((o) => <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>)}
    </select>
  );
}

export function Slider({ value, min = 0, max = 1, step = 0.01, onChange, ariaLabel, format, disabled }: {
  value: number; min?: number; max?: number; step?: number; onChange: (v: number) => void; ariaLabel: string; format?: (v: number) => string; disabled?: boolean;
}) {
  const fill = ((value - min) / (max - min)) * 100;
  return (
    <div className="row" style={{ gap: 10 }}>
      <input className="range grow" type="range" min={min} max={max} step={step} value={value} aria-label={ariaLabel} disabled={disabled}
        style={{ ["--fill" as string]: `${fill}%` }} onChange={(e) => onChange(Number(e.target.value))} />
      <span className="mono meta" style={{ width: 40, textAlign: "right" }}>{format ? format(value) : value.toFixed(2)}</span>
    </div>
  );
}

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return <button type="button" role="switch" className="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)} />;
}

export function ColorInput({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) {
  const [draft, setDraft] = useState<string | null>(null);
  const hex = /^#[0-9a-f]{6}$/i.test(value) ? value : "#ffffff";
  return (
    <span className="color-input">
      <input type="color" value={hex} aria-label={label} onChange={(e) => onChange(e.target.value.toUpperCase())} />
      <input type="text" value={draft ?? value} aria-label={`${label} hex`} spellCheck={false}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => { if (draft && /^#[0-9a-f]{6}$/i.test(draft)) onChange(draft.toUpperCase()); setDraft(null); }} />
    </span>
  );
}

export function FieldRow({ label, children }: { label: ReactNode; children: ReactNode }) {
  return <div className="field-row"><span className="label">{label}</span><div style={{ minWidth: 0 }}>{children}</div></div>;
}

export function Section({ title, children, defaultOpen = true, right }: { title: ReactNode; children: ReactNode; defaultOpen?: boolean; right?: ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="section">
      <div className="row" style={{ paddingRight: 8 }}>
        <button className="section-head grow" aria-expanded={open} onClick={() => setOpen(!open)}>
          <ChevronDown size={14} className="chev" />{title}
        </button>
        {right}
      </div>
      {open && <div className="section-body">{children}</div>}
    </div>
  );
}
