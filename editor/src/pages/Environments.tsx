// Environment studio: browse the ten sets, compare lighting presets, preview full-screen, save setups.
import { useMemo, useState } from "react";
import { Search, Maximize2, Save, CheckCheck, X } from "lucide-react";
import { ENVIRONMENTS, MOOD_COLORS, environment } from "@/data/catalog";
import { MOODS } from "@/lib/types";
import { EnvThumb } from "@/components/Thumbs";
import { EnvTile, FavButton } from "@/components/pickers";
import { AssetBadge } from "@/components/ui/Feedback";
import { Segmented } from "@/components/ui/Form";
import { useLibrary } from "@/stores/library";
import { NONE } from "@/lib/format";
import { useProject } from "@/stores/project";
import { toast } from "@/stores/ui";
import { cap, uid } from "@/lib/format";
import { createPortal } from "react-dom";

export function EnvironmentsPage() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("All");
  const [sel, setSel] = useState(ENVIRONMENTS[0].id);
  const [preset, setPreset] = useState(ENVIRONMENTS[0].presets[0].id);
  const [full, setFull] = useState(false);
  const favs = useLibrary((s) => s.lib.favorites) ?? NONE;
  const savedLighting = useLibrary((s) => s.lib.lighting) ?? NONE;
  const update = useLibrary((s) => s.update);
  const projectId = useProject((s) => s.id);
  const projectName = useProject((s) => s.editor.name);
  const setEditor = useProject((s) => s.setEditor);
  const setPerf = useProject((s) => s.setPerformance);
  const hasPerf = useProject((s) => Boolean(s.performance));

  const list = useMemo(() => ENVIRONMENTS.filter((e) =>
    (cat === "All" || e.category === cat || (cat === "Favourites" && favs.includes(`env:${e.id}`))) &&
    (e.name + e.description).toLowerCase().includes(q.toLowerCase())), [q, cat, favs]);
  const env = environment(sel)!;
  const p = env.presets.find((x) => x.id === preset) ?? env.presets[0];

  const use = () => {
    setEditor((e) => ({ ...e, environment: { id: env.id, lighting: p.id } }));
    if (hasPerf) setPerf((x) => ({ ...x, environment: env.pipelineId ?? "night_city" }));
    toast(`${env.name} · ${p.name} set on ${projectName}`);
  };

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Environments</h1><div className="muted">Ten sets, three lighting presets each, all built in Blender. Previews are real renders of each set and preset.</div></div>
        </div>
        <div className="env-studio">
          <div className="env-big" onDoubleClick={() => setFull(true)}>
            <EnvThumb env={env} preset={p} />
            <div className="env-big-top"><AssetBadge status={env.status} /><span className="grow" /><FavButton k={`env:${env.id}`} />
              <button className="fav-btn" aria-label="Full-screen preview" onClick={() => setFull(true)}><Maximize2 size={13} /></button></div>
          </div>
          <div className="panel env-side">
            <div className="col" style={{ gap: 4 }}><span className="eyebrow">{env.category}</span><h2 className="h2">{env.name}</h2><p className="muted" style={{ margin: 0 }}>{env.description}</p></div>
            <div className="label">Lighting preset</div>
            <div className="col" style={{ gap: 6 }}>
              {env.presets.map((x) => (
                <button key={x.id} className="preset-row" aria-pressed={x.id === p.id} onClick={() => setPreset(x.id)}>
                  <span className="preset-swatches"><span style={{ background: x.key }} /><span style={{ background: x.rim }} /><span style={{ background: x.glow }} /></span>
                  <span className="grow" style={{ textAlign: "left" }}>{x.name}</span>
                </button>
              ))}
            </div>
            <div className="label">Moods on this set</div>
            <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>{MOODS.map((m) => <span key={m} className="badge"><span className="pip" style={{ color: MOOD_COLORS[m] }} />{cap(m)}</span>)}</div>
            <div className="hint">Line moods crossfade the Key, Rim, Fill and Glow lights during a shot. Every set keeps that contract.</div>
            <div className="row" style={{ marginTop: "auto", gap: 8 }}>
              <button className="btn grow" onClick={() => { update((l) => ({ ...l, lighting: [...(l.lighting ?? []), { id: uid("lt-"), environmentId: env.id, presetId: p.id, name: `${env.name} · ${p.name}` }] })); toast("Lighting setup saved to your library"); }}><Save size={14} />Save setup</button>
              {projectId && <button className="btn btn-primary grow" onClick={use}><CheckCheck size={14} />Use in project</button>}
            </div>
          </div>
        </div>

        {savedLighting.length > 0 && <>
          <h2 className="h2" style={{ margin: "28px 0 12px" }}>Saved setups</h2>
          <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
            {savedLighting.map((s) => {
              const e = environment(s.environmentId);
              const pr = e?.presets.find((x) => x.id === s.presetId);
              return <span key={s.id} className="chip" role="button" tabIndex={0} onClick={() => { setSel(s.environmentId); setPreset(s.presetId); }}><span className="dot" style={{ background: pr?.glow }} />{s.name}
                <button className="icon-btn xs" aria-label="Remove setup" onClick={(ev) => { ev.stopPropagation(); update((l) => ({ ...l, lighting: (l.lighting ?? []).filter((x) => x.id !== s.id) })); }}><X size={11} /></button></span>;
            })}
          </div>
        </>}

        <div className="toolbar" style={{ marginTop: 28 }}>
          <div className="search"><Search size={14} /><input className="input" placeholder="Search sets" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <Segmented value={cat} onChange={setCat} options={["All", "Interior", "Exterior", "Transit", "Work", "Favourites"].map((v) => ({ value: v, label: v }))} />
        </div>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
          {list.map((e) => <EnvTile key={e.id} env={e} selected={e.id === sel} presetId={e.id === sel ? p.id : undefined} onClick={() => { setSel(e.id); setPreset(e.presets[0].id); window.scrollTo?.(0, 0); document.querySelector(".page")?.scrollTo({ top: 0, behavior: "smooth" }); }} />)}
        </div>
        {list.length === 0 && <div className="meta" style={{ padding: 24, textAlign: "center" }}>No sets match.</div>}
      </div>
      {full && createPortal(
        <div className="fullscreen-preview" onClick={() => setFull(false)}>
          <EnvThumb env={env} preset={p} />
          <div className="fs-bar" onClick={(e) => e.stopPropagation()}>
            <span className="h3 grow">{env.name} · {p.name}</span>
            {env.presets.map((x) => <button key={x.id} className="chip" aria-pressed={x.id === p.id} onClick={() => setPreset(x.id)}>{x.name}</button>)}
            <button className="icon-btn" aria-label="Close" onClick={() => setFull(false)}><X size={16} /></button>
          </div>
        </div>, document.body)}
    </div>
  );
}
