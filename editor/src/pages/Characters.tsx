// Character studio: the cast of seven, each with turnaround, expressions and a wardrobe builder.
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Save, UserCheck, Trash2, Info } from "lucide-react";
import { CHARACTERS, SLOTS, WARDROBE, character, wardrobeItem, type Character, type Outfit, type Slot } from "@/data/catalog";
import { CharacterThumb } from "@/components/Thumbs";
import { FavButton } from "@/components/pickers";
import { AssetBadge, Badge } from "@/components/ui/Feedback";
import { ColorInput, Select } from "@/components/ui/Form";
import { Dialog } from "@/components/ui/Overlay";
import { useLibrary } from "@/stores/library";
import { NONE } from "@/lib/format";
import { useProject } from "@/stores/project";
import { toast } from "@/stores/ui";
import { uid } from "@/lib/format";
import { outfitsFor } from "@/lib/outfits";

// The ARKit channels that carry each expression on the FaceCtrl rig.
const EXPRESSIONS: [string, string][] = [
  ["Neutral", "all channels at rest"], ["Laugh", "mouthSmile L/R · cheekSquint · jawOpen · eyeSquint"],
  ["Smug", "mouthSmile R · browOuterUp R · eyeSquint L"], ["Surprised", "eyeWide L/R · browInnerUp · jawOpen"],
  ["Sad", "mouthFrown L/R · browInnerUp · eyeLookDown"], ["Angry", "browDown L/R · noseSneer · mouthPress"],
  ["Blink", "eyeBlink L/R"], ["Talk A / O / M", "jawOpen · mouthFunnel · mouthPress + mouthRoll"],
];

export function CharactersPage() {
  const { cid } = useParams();
  const c = character(cid);
  return c ? <CharacterDetailPage c={c} /> : <CharacterGrid />;
}

function CharacterGrid() {
  const nav = useNavigate();
  const [filter, setFilter] = useState<"all" | "male" | "female" | "fav">("all");
  const favs = useLibrary((s) => s.lib.favorites) ?? NONE;
  const list = CHARACTERS.filter((c) => filter === "all" || c.gender === filter || (filter === "fav" && favs.includes(`char:${c.id}`)));
  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div className="grow"><h1 className="h1">Characters</h1><div className="muted">Seven original characters in a stylized-sculpt look, each with three outfits and a shared wardrobe.</div></div>
        </div>
        <div className="callout info" style={{ marginBottom: 16 }}><Info size={14} /><div>The cast is designed in the production brief but not built in Blender yet. These are concept cards drawn from each character's data. Renders use the M1 stand-in until a character lands; casting and outfits you choose now carry over.</div></div>
        <div className="tabs">
          {([["all", "All"], ["male", "Male"], ["female", "Female"], ["fav", "Favourites"]] as const).map(([k, l]) => <button key={k} className="tab" aria-selected={filter === k} onClick={() => setFilter(k)}>{l}</button>)}
        </div>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 14 }}>
          {list.map((c) => (
            <div key={c.id} className="card interactive asset-card" role="button" tabIndex={0} onClick={() => nav(`/characters/${c.id}`)} onKeyDown={(e) => e.key === "Enter" && nav(`/characters/${c.id}`)}>
              <div className="thumb portrait"><CharacterThumb character={c} pose="full" /><div className="over"><AssetBadge status={c.status} /><span className="fav"><FavButton k={`char:${c.id}`} /></span></div><span className="placeholder-tag">Concept</span></div>
              <div className="body"><span className="title">{c.name}</span><span className="meta">{c.vibe}</span><span className="meta faint ellipsis">{c.signature}</span></div>
            </div>
          ))}
        </div>
        {list.length === 0 && <div className="meta" style={{ padding: 24 }}>No favourite characters yet. Star one to pin it here.</div>}
      </div>
    </div>
  );
}

function CharacterDetailPage({ c }: { c: Character }) {
  const lib = useLibrary((s) => s.lib);
  const update = useLibrary((s) => s.update);
  const all = useMemo(() => outfitsFor(c, lib), [c, lib]);
  const [outfitId, setOutfitId] = useState(c.outfits[0].id);
  const base = all.find((o) => o.id === outfitId) ?? all[0];
  const [draft, setDraft] = useState<Outfit>(base);
  const [tab, setTab] = useState<"wardrobe" | "expressions" | "turnaround">("wardrobe");
  const [saveOpen, setSaveOpen] = useState(false);
  const [castOpen, setCastOpen] = useState(false);
  const pick = (o: Outfit) => { setOutfitId(o.id); setDraft(o); };
  const dirty = JSON.stringify(draft.items) !== JSON.stringify(base.items) || JSON.stringify(draft.colors ?? {}) !== JSON.stringify(base.colors ?? {});

  const setSlot = (slot: Slot, itemId: string | null) => setDraft((d) => {
    const items = { ...d.items };
    const colors = { ...(d.colors ?? {}) };
    if (itemId) items[slot] = itemId; else delete items[slot];
    delete colors[slot];
    return { ...d, items, colors };
  });

  const saveOutfit = (name: string) => {
    const id = uid("of-");
    const items = Object.fromEntries(Object.entries(draft.items).map(([slot, itemId]) => [slot, { itemId: itemId!, color: draft.colors?.[slot as Slot] ?? wardrobeItem(itemId!)?.color ?? "#888888" }]));
    update((l) => ({ ...l, outfits: [...(l.outfits ?? []), { id, characterId: c.id, name, items }] }));
    setOutfitId(id);
    toast(`Saved "${name}" to ${c.name}'s outfits`);
  };

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <Link to="/characters" className="icon-btn" aria-label="All characters"><ArrowLeft size={16} /></Link>
          <div className="grow"><div className="row"><h1 className="h1">{c.name}</h1><AssetBadge status={c.status} /><FavButton k={`char:${c.id}`} /></div><div className="muted">{c.vibe}</div></div>
          <button className="btn" onClick={() => setSaveOpen(true)}><Save size={14} />Save outfit to library</button>
          <button className="btn btn-primary" onClick={() => setCastOpen(true)}><UserCheck size={14} />Cast in project</button>
        </div>
        <div className="char-layout">
          <div className="char-stage"><CharacterThumb character={c} outfit={draft} pose="full" /><span className="placeholder-tag">Concept · Blender build pending</span></div>
          <div className="col" style={{ gap: 16, minWidth: 0 }}>
            <div className="panel" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
              <p style={{ margin: 0 }}>{c.personality}</p>
              <dl className="kv"><dt>Signature look</dt><dd>{c.signature}</dd><dt>Suggested voice</dt><dd>{c.suggestedVoice}</dd><dt>Rig</dt><dd>FaceCtrl · 52 ARKit channels, CHAR_root, Head</dd></dl>
            </div>
            <div className="tabs" style={{ marginBottom: 0 }}>
              {([["wardrobe", "Wardrobe"], ["expressions", "Expression sheet"], ["turnaround", "Turnaround"]] as const).map(([k, l]) => <button key={k} className="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{l}</button>)}
            </div>
            {tab === "wardrobe" && <>
              <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
                {all.map((o) => (
                  <span key={o.id} className="chip" role="button" tabIndex={0} aria-pressed={o.id === outfitId} onClick={() => pick(o)}>{o.name}{o.saved && <Badge>Saved</Badge>}
                    {o.saved && <button className="icon-btn xs" aria-label={`Delete ${o.name}`} onClick={(e) => { e.stopPropagation(); update((l) => ({ ...l, outfits: (l.outfits ?? []).filter((x) => x.id !== o.id) })); if (o.id === outfitId) pick(c.outfits[0]); }}><Trash2 size={11} /></button>}
                  </span>
                ))}
              </div>
              <div className="panel wardrobe">
                {SLOTS.map((s) => {
                  const itemId = draft.items[s.id];
                  const color = draft.colors?.[s.id] ?? wardrobeItem(itemId ?? "")?.color ?? "#888888";
                  return (
                    <div key={s.id} className="wardrobe-row">
                      <span className="label" style={{ width: 96 }}>{s.label}</span>
                      <div className="grow"><Select size="sm" ariaLabel={s.label} value={itemId ?? ""} onChange={(v) => setSlot(s.id, v || null)}
                        options={[{ value: "", label: "None" }, ...WARDROBE.filter((w) => w.slot === s.id).map((w) => ({ value: w.id, label: w.name }))]} /></div>
                      {itemId && <ColorInput label={`${s.label} colour`} value={color} onChange={(v) => setDraft((d) => ({ ...d, colors: { ...(d.colors ?? {}), [s.id]: v } }))} />}
                    </div>
                  );
                })}
              </div>
              <div className="hint">{dirty ? "Unsaved changes. Save to the library to reuse this outfit, or cast it straight into a project as a one-off." : "Recolour any item or swap pieces across the shared wardrobe."} Library outfits never change a project unless you pick them there.</div>
            </>}
            {tab === "expressions" && (
              <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
                {EXPRESSIONS.map(([name, channels]) => (
                  <div key={name} className="panel expr">
                    <div className="expr-face"><CharacterThumb character={c} outfit={draft} /><span className="placeholder-tag">Pending</span></div>
                    <div className="h3">{name}</div><div className="meta mono" style={{ fontSize: 10 }}>{channels}</div>
                  </div>
                ))}
              </div>
            )}
            {tab === "turnaround" && (
              <div className="grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
                {["Front", "Three-quarter", "Side"].map((v, i) => (
                  <div key={v} className="panel expr">
                    <div className="expr-face" style={{ aspectRatio: "10/16" }}>{i === 0 ? <CharacterThumb character={c} outfit={draft} pose="full" /> : <div className="pending-frame">Render pending</div>}</div>
                    <div className="h3">{v}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      {saveOpen && <NameDialog title={`Save ${c.name}'s outfit`} initial={`${draft.name}${dirty ? " (custom)" : ""}`} onClose={() => setSaveOpen(false)} onSave={saveOutfit} />}
      {castOpen && <CastDialog c={c} outfit={draft} dirty={dirty} onClose={() => setCastOpen(false)} />}
    </div>
  );
}

function NameDialog({ title, initial, onClose, onSave }: { title: string; initial: string; onClose: () => void; onSave: (n: string) => void }) {
  const [name, setName] = useState(initial);
  return (
    <Dialog title={title} onClose={onClose} footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={!name.trim()} onClick={() => { onSave(name.trim()); onClose(); }}>Save</button></>}>
      <input className="input" autoFocus value={name} onChange={(e) => setName(e.target.value)} />
    </Dialog>
  );
}

function CastDialog({ c, outfit, dirty, onClose }: { c: Character; outfit: Outfit; dirty: boolean; onClose: () => void }) {
  const { id, editor, performance, setEditor } = useProject();
  const update = useLibrary((s) => s.update);
  const speakers = Object.keys(performance?.characters ?? {});
  const [sp, setSp] = useState(speakers[0] ?? "");
  const cast = () => {
    let outfitId = outfit.id;
    if (dirty) {
      // a project-only variant is stored as a saved outfit so the project can reference it
      outfitId = uid("of-");
      const items = Object.fromEntries(Object.entries(outfit.items).map(([slot, itemId]) => [slot, { itemId: itemId!, color: outfit.colors?.[slot as Slot] ?? wardrobeItem(itemId!)?.color ?? "#888888" }]));
      update((l) => ({ ...l, outfits: [...(l.outfits ?? []), { id: outfitId, characterId: c.id, name: `${outfit.name} · ${editor.name}`, items }] }));
    }
    setEditor((e) => ({ ...e, cast: { ...e.cast, [sp]: { characterId: c.id, outfitId } } }));
    toast(`${c.name} cast as ${sp} in ${editor.name}`);
    onClose();
  };
  return (
    <Dialog title={`Cast ${c.name}`} onClose={onClose} footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={!id || !sp} onClick={cast}>Cast as {sp}</button></>}>
      {!id || !speakers.length ? <div className="muted">Open a reel on Create first. Casting is saved per project.</div> : <>
        <div className="field"><span className="label">Project</span><span>{editor.name}</span></div>
        <div className="field"><span className="label">Speaker</span><Select value={sp} onChange={setSp} options={speakers.map((s) => ({ value: s, label: s + (editor.cast[s]?.characterId ? ` (now ${character(editor.cast[s]?.characterId)?.name})` : "") }))} /></div>
        <div className="hint">Outfit: {outfit.name}{dirty ? " with your changes, saved as a project variant" : ""}. This only changes this project.</div>
      </>}
    </Dialog>
  );
}
