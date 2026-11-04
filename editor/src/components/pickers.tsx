// Visual pickers shared by Create, the editor inspector and the asset pages.
import { useMemo, useState } from "react";
import { Check, Search, Star, X } from "lucide-react";
import {
  CHARACTERS, ENVIRONMENTS, SUBTITLE_TEMPLATES, CAPTION_FONTS, SLOTS, wardrobeItem,
  type Character, type Environment,
} from "@/data/catalog";
import type { SubtitleStyle } from "@/lib/types";
import { CharacterThumb, EnvThumb, SubtitleText } from "./Thumbs";
import { Drawer } from "./ui/Overlay";
import { AssetBadge } from "./ui/Feedback";
import { ColorInput, FieldRow, Segmented, Select, Slider } from "./ui/Form";
import { useFavorite, useLibrary } from "@/stores/library";
import { NONE } from "@/lib/format";
import { outfitsFor } from "@/lib/outfits";

export function FavButton({ k }: { k: string }) {
  const on = useFavorite(k);
  const toggle = useLibrary((s) => s.toggleFavorite);
  return (
    <button className="fav-btn fav" aria-pressed={on} aria-label={on ? "Remove from favourites" : "Add to favourites"}
      onClick={(e) => { e.stopPropagation(); toggle(k); }}>
      <Star size={13} fill={on ? "currentColor" : "none"} />
    </button>
  );
}

// ---------- characters ----------

export function CharacterDrawer({ speaker, value, outfit, onPick, onClose }: {
  speaker: string; value: string | null; outfit: string | null;
  onPick: (characterId: string | null, outfitId: string | null) => void; onClose: () => void;
}) {
  const [sel, setSel] = useState<string | null>(value);
  const [fit, setFit] = useState<string | null>(outfit);
  const c = CHARACTERS.find((x) => x.id === sel);
  return (
    <Drawer onClose={onClose} width={640}>
      <div className="drawer-head"><div className="col grow" style={{ gap: 2 }}><span className="eyebrow">Cast for {speaker}</span><h2 className="h2">Choose a character</h2></div>
        <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
      <div className="drawer-body">
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(132px, 1fr))", gap: 10 }}>
          {CHARACTERS.map((ch) => (
            <button key={ch.id} className="tile" aria-pressed={sel === ch.id} onClick={() => { setSel(ch.id); setFit(ch.outfits[0].id); }}>
              <div className="tile-media" style={{ aspectRatio: "1" }}><CharacterThumb character={ch} />{sel === ch.id && <span className="check"><Check size={12} /></span>}</div>
              <div className="tile-body"><span className="tile-name">{ch.name}</span><span className="meta ellipsis">{ch.vibe}</span></div>
            </button>
          ))}
        </div>
        {c && <CharacterDetail c={c} outfit={fit} onOutfit={setFit} />}
      </div>
      <div className="dialog-foot">
        {value && <button className="btn btn-ghost" onClick={() => { onPick(null, null); onClose(); }}>Clear</button>}
        <div className="grow" />
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={!sel} onClick={() => { onPick(sel, fit); onClose(); }}>Cast {c?.name ?? ""} as {speaker}</button>
      </div>
    </Drawer>
  );
}

export function CharacterDetail({ c, outfit, onOutfit }: { c: Character; outfit: string | null; onOutfit: (id: string) => void }) {
  const lib = useLibrary((s) => s.lib);
  const all = outfitsFor(c, lib);
  const o = all.find((x) => x.id === outfit) ?? all[0];
  return (
    <div className="panel" style={{ padding: 16, display: "grid", gridTemplateColumns: "120px 1fr", gap: 16 }}>
      <div style={{ borderRadius: 6, overflow: "hidden", aspectRatio: "10/16", position: "relative" }}><CharacterThumb character={c} outfit={o} pose="full" /></div>
      <div className="col" style={{ gap: 10 }}>
        <div className="row"><h3 className="h2 grow">{c.name}</h3><AssetBadge status={c.status} /></div>
        <p className="muted" style={{ margin: 0 }}>{c.personality}</p>
        <dl className="kv"><dt>Signature</dt><dd>{c.signature}</dd><dt>Voice</dt><dd>{c.suggestedVoice} (suggested)</dd></dl>
        <div className="label">Outfit</div>
        <div className="row" style={{ flexWrap: "wrap" }}>
          {all.map((x) => <button key={x.id} className="chip" aria-pressed={x.id === o.id} onClick={() => onOutfit(x.id)}>{x.name}{x.saved && <span className="faint">· saved</span>}</button>)}
        </div>
        <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
          {SLOTS.filter((s) => o.items[s.id]).map((s) => {
            const it = wardrobeItem(o.items[s.id]!);
            return <span key={s.id} className="badge"><span className="pip" style={{ color: it?.color }} />{it?.name}</span>;
          })}
        </div>
      </div>
    </div>
  );
}

// ---------- environments ----------

export function EnvironmentDrawer({ value, lighting, onPick, onClose }: {
  value: string; lighting: string; onPick: (envId: string, presetId: string) => void; onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<string>("All");
  const [sel, setSel] = useState(value);
  const [preset, setPreset] = useState(lighting);
  const favs = useLibrary((s) => s.lib.favorites) ?? NONE;
  const list = useMemo(() => ENVIRONMENTS.filter((e) =>
    (cat === "All" || e.category === cat || (cat === "Favourites" && favs.includes(`env:${e.id}`))) &&
    (e.name + e.description).toLowerCase().includes(q.toLowerCase())), [q, cat, favs]);
  const env = ENVIRONMENTS.find((e) => e.id === sel)!;
  const p = env.presets.find((x) => x.id === preset) ?? env.presets[0];
  return (
    <Drawer onClose={onClose} width={760}>
      <div className="drawer-head"><div className="col grow" style={{ gap: 2 }}><span className="eyebrow">Set</span><h2 className="h2">Choose an environment</h2></div>
        <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
      <div className="drawer-body">
        <div className="env-hero">
          <EnvThumb env={env} preset={p} />
          <div className="env-hero-meta">
            <div className="row"><span className="h2 grow">{env.name}</span><AssetBadge status={env.status} /></div>
            <span className="muted">{env.description}</span>
            <div className="row" style={{ flexWrap: "wrap", marginTop: 4 }}>
              {env.presets.map((x) => <button key={x.id} className="chip" aria-pressed={x.id === p.id} onClick={() => setPreset(x.id)}><span className="dot" style={{ background: x.glow }} />{x.name}</button>)}
            </div>
          </div>
        </div>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <div className="search grow"><Search size={14} /><input className="input sm" placeholder="Search sets" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: "100%" }} /></div>
          <Segmented value={cat} onChange={setCat} options={["All", "Interior", "Exterior", "Transit", "Work", "Favourites"].map((v) => ({ value: v, label: v }))} />
        </div>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))", gap: 10 }}>
          {list.map((e) => <EnvTile key={e.id} env={e} selected={e.id === sel} onClick={() => { setSel(e.id); setPreset(e.presets[0].id); }} />)}
          {list.length === 0 && <div className="meta" style={{ padding: 16 }}>No sets match.</div>}
        </div>
      </div>
      <div className="dialog-foot">
        <div className="grow" />
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={() => { onPick(sel, p.id); onClose(); }}>Use {env.name}</button>
      </div>
    </Drawer>
  );
}

export function EnvTile({ env, selected, onClick, presetId }: { env: Environment; selected?: boolean; onClick: () => void; presetId?: string }) {
  const p = env.presets.find((x) => x.id === presetId) ?? env.presets[0];
  return (
    <div role="button" tabIndex={0} className="tile" aria-pressed={selected} onClick={onClick} onKeyDown={(e) => e.key === "Enter" && onClick()}>
      <div className="tile-media"><EnvThumb env={env} preset={p} />
        <div style={{ position: "absolute", top: 6, right: 6 }}><FavButton k={`env:${env.id}`} /></div>
        {selected && <span className="check" style={{ right: "auto", left: 6 }}><Check size={12} /></span>}
      </div>
      <div className="tile-body">
        <div className="row"><span className="tile-name grow ellipsis">{env.name}</span></div>
        <div className="row" style={{ gap: 4 }}>{env.presets.map((x) => <span key={x.id} className="dot" title={x.name} style={{ width: 8, height: 8, borderRadius: 4, background: x.glow }} />)}
          <span className="meta" style={{ marginLeft: 4 }}>{env.status === "available" ? "Renders today" : "Planned"}</span></div>
      </div>
    </div>
  );
}

// ---------- subtitles ----------

export function SubtitleCard({ s, name, selected, onClick, note }: { s: SubtitleStyle; name: string; selected?: boolean; onClick: () => void; note?: string }) {
  return (
    <button className="tile" aria-pressed={selected} onClick={onClick}>
      <div className="tile-media sub-sample" style={{ aspectRatio: "16/9" }}>
        <SubtitleText s={s} text="They actually approved it" active={2} scale={0.32} />
        {selected && <span className="check"><Check size={12} /></span>}
      </div>
      <div className="tile-body"><span className="tile-name">{name}</span>{note && <span className="meta">{note}</span>}</div>
    </button>
  );
}

export function SubtitleGrid({ value, onPick, columns = 3 }: { value: string; onPick: (s: SubtitleStyle) => void; columns?: number }) {
  const saved = useLibrary((s) => s.lib.subtitleTemplates) ?? NONE;
  return (
    <div className="grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`, gap: 10 }}>
      {SUBTITLE_TEMPLATES.map((t) => <SubtitleCard key={t.id} s={t.style} name={t.name} selected={value === t.id} note={t.pipeline ? "Pipeline default" : undefined} onClick={() => onPick({ ...t.style })} />)}
      {saved.map((t) => <SubtitleCard key={t.id} s={t} name={t.name} selected={value === t.id} note="Saved" onClick={() => onPick({ ...t, templateId: t.id })} />)}
    </div>
  );
}

export function SubtitleControls({ s, onChange, compact }: { s: SubtitleStyle; onChange: (patch: Partial<SubtitleStyle>) => void; compact?: boolean }) {
  return (
    <div className="col" style={{ gap: 10 }}>
      <FieldRow label="Font"><Select size="sm" value={s.font} onChange={(v) => onChange({ font: v })} options={CAPTION_FONTS.map((f) => ({ value: f, label: f }))} /></FieldRow>
      <FieldRow label="Size"><Slider ariaLabel="Size" value={s.size} min={28} max={110} step={1} onChange={(v) => onChange({ size: v })} format={(v) => `${v}`} /></FieldRow>
      <FieldRow label="Weight"><Segmented size="sm" value={s.weight} onChange={(v) => onChange({ weight: v })} options={[400, 500, 700].map((w) => ({ value: w, label: w === 400 ? "Reg" : w === 500 ? "Med" : "Bold" }))} /></FieldRow>
      <FieldRow label="Text"><ColorInput label="Text colour" value={s.color} onChange={(v) => onChange({ color: v })} /></FieldRow>
      <FieldRow label="Highlight"><ColorInput label="Highlight colour" value={s.highlight} onChange={(v) => onChange({ highlight: v })} /></FieldRow>
      <FieldRow label="Position"><Segmented size="sm" value={s.position} onChange={(v) => onChange({ position: v })} options={[{ value: "upper", label: "Upper" }, { value: "middle", label: "Middle" }, { value: "lower", label: "Lower" }]} /></FieldRow>
      {!compact && <>
        <FieldRow label="Align"><Segmented size="sm" value={s.align} onChange={(v) => onChange({ align: v })} options={[{ value: "left", label: "Left" }, { value: "center", label: "Centre" }, { value: "right", label: "Right" }]} /></FieldRow>
        <FieldRow label="Outline"><Slider ariaLabel="Outline" value={s.outline} min={0} max={10} step={1} onChange={(v) => onChange({ outline: v })} format={(v) => `${v}px`} /></FieldRow>
        <FieldRow label="Shadow"><Slider ariaLabel="Shadow" value={s.shadow} min={0} max={10} step={1} onChange={(v) => onChange({ shadow: v })} format={(v) => `${v}px`} /></FieldRow>
        <FieldRow label="Background"><Select size="sm" value={s.background ?? "none"} onChange={(v) => onChange({ background: v === "none" ? null : v })}
          options={[{ value: "none", label: "None" }, { value: "rgba(0,0,0,0.6)", label: "Dark bar" }, { value: "highlight", label: "Block on active word" }]} /></FieldRow>
        <FieldRow label="Line spacing"><Slider ariaLabel="Line spacing" value={s.lineSpacing} min={0.9} max={1.6} step={0.05} onChange={(v) => onChange({ lineSpacing: v })} format={(v) => v.toFixed(2)} /></FieldRow>
        <FieldRow label="Words / line"><Slider ariaLabel="Words per line" value={s.wordsPerLine} min={1} max={8} step={1} onChange={(v) => onChange({ wordsPerLine: v })} format={(v) => `${v}`} /></FieldRow>
        <FieldRow label="Animation"><Select size="sm" value={s.animation} onChange={(v) => onChange({ animation: v })}
          options={[{ value: "pop", label: "Pop" }, { value: "fade", label: "Fade" }, { value: "karaoke", label: "Karaoke fill" }, { value: "slide", label: "Slide up" }, { value: "none", label: "None" }]} /></FieldRow>
        <FieldRow label="Case"><Segmented size="sm" value={s.uppercase ? "up" : "as"} onChange={(v) => onChange({ uppercase: v === "up" })} options={[{ value: "as", label: "As written" }, { value: "up", label: "UPPER" }]} /></FieldRow>
      </>}
    </div>
  );
}
